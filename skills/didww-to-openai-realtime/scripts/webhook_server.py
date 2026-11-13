#!/usr/bin/env python3
"""Minimal call-control backend for DIDWW -> OpenAI Realtime SIP (incoming).

Receives realtime.call.incoming webhooks, reads the called DIDWW number
from the Diversion header (DIDWW puts the project ID in To), accepts known
DIDs with your instructions and rejects everything else. After accepting,
it opens the call's websocket and asks the agent to greet the caller. When
a DID has a transfer target, the agent gets a transfer_call tool; when the
model calls it, the server hands the call to the target through the refer
endpoint, and DIDWW places the transfer leg through your outbound trunk.
Stdlib only; run behind any HTTPS front (reverse proxy, serverless
wrapper, or a tunnel while testing).

Env: OPENAI_API_KEY, OPENAI_WEBHOOK_SECRET (both required; or pass
--env-file PATH with KEY=VALUE lines), REALTIME_MODEL (default
gpt-realtime), PORT (default 8080), LOG_TRANSCRIPT=1 to log what the agent
says. Edit AGENTS below: DID -> instructions, greeting, transfer target.
"""
import base64, hashlib, hmac, json, os, re, socket, ssl, struct, sys
import threading, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 1 << 20      # webhook events are small; refuse anything larger
TOLERANCE = 300         # seconds a signed event stays valid

AGENTS = {
    # "+15105550100": {
    #   "instructions": "You are the receptionist for Example Corp. Keep "
    #                   "answers short. Only if the caller explicitly asks "
    #                   "for a person, say you will connect them, then call "
    #                   "the transfer_call tool.",
    #   "greeting": "Hello, thank you for calling Example Corp. How can I "
    #               "help you?",
    #   # sip: URI at a DIDWW outbound gateway; DIDWW rejects tel: targets
    #   # (603 Unconfigured xfer for tel URIs). Never a DID routed to this
    #   # inbound trunk, or the call loops back to the agent.
    #   "transfer_to": "sip:+15105550199@fra.eu.out.didww.com",
    # },
}

TRANSFER_TOOL = {
    "type": "function", "name": "transfer_call",
    "description": "Transfer the caller to a human colleague. Call this ONLY "
                   "after the caller has explicitly asked to speak to a person, "
                   "a human, a live agent or an operator. Never call it on "
                   "your own initiative.",
    "parameters": {"type": "object", "properties": {}},
}

API_KEY = os.environ.get("OPENAI_API_KEY", "")
SECRET = os.environ.get("OPENAI_WEBHOOK_SECRET", "")
MODEL = os.environ.get("REALTIME_MODEL", "gpt-realtime")
LOG_TRANSCRIPT = os.environ.get("LOG_TRANSCRIPT") == "1"

_seen = {}               # webhook-id -> time handled (duplicate/replay guard)
_seen_lock = threading.Lock()

def verify(body, headers):
    """Standard Webhooks signature check (webhook-id/-timestamp/-signature)."""
    sig = headers.get("webhook-signature", "")
    wid = headers.get("webhook-id", "")
    ts = headers.get("webhook-timestamp", "")
    try:  # a captured event must not be replayable later
        if abs(time.time() - int(ts)) > TOLERANCE:
            return False
    except ValueError:
        return False
    secret = SECRET.split("_", 1)[-1]
    mac = hmac.new(base64.b64decode(secret),
                   f"{wid}.{ts}.".encode() + body, hashlib.sha256)
    expect = "v1," + base64.b64encode(mac.digest()).decode()
    return any(hmac.compare_digest(expect, s) for s in sig.split())

def already_handled(wid):
    now = time.time()
    with _seen_lock:
        for k in [k for k, t in _seen.items() if now - t > TOLERANCE]:
            del _seen[k]
        return wid in _seen

def mark_handled(wid):
    with _seen_lock:
        _seen[wid] = time.time()

def digits(s):
    return re.sub(r"\D", "", s)

def match_did(header):
    """Exact match of a SIP URI's user part against AGENTS. This is
    routing, not authentication: the caller controls these headers."""
    m = re.search(r"sips?:([^@;>]+)@", header)
    if not m:
        return None
    user = digits(m.group(1))
    return next((d for d in AGENTS if user and digits(d) == user), None)

def called_did(headers):
    """DIDWW sends the called DID as Diversion (the trunk's default 'Add
    Diversion as +DID number'); To carries the project ID from the R-URI."""
    return match_did(headers.get("diversion", "")) or match_did(headers.get("to", ""))

def api(path, payload):
    req = urllib.request.Request(
        "https://api.openai.com" + path, method="POST",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + API_KEY,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()

# --- call websocket: greeting, transcript log, transfer tool calls ---

def ws_connect(call_id):
    host = "api.openai.com"
    raw = socket.create_connection((host, 443), timeout=30)
    s = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall((f"GET /v1/realtime?call_id={call_id} HTTP/1.1\r\n"
               f"Host: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
               f"Authorization: Bearer {API_KEY}\r\n\r\n").encode())
    head = b""
    while b"\r\n\r\n" not in head:
        chunk = s.recv(1)
        if not chunk:
            raise ConnectionError("websocket handshake closed")
        head += chunk
    status = head.split(b"\r\n", 1)[0]
    if b" 101 " not in status + b" ":
        raise ConnectionError(status.decode(errors="replace"))
    s.settimeout(None)  # calls can be long and quiet
    return s

def _recv(s, n):
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("websocket closed")
        buf += chunk
    return buf

def _send(s, opcode, payload=b""):
    mask = os.urandom(4)  # client frames must be masked
    n = len(payload)
    head = bytes([0x80 | opcode])
    if n < 126:
        head += bytes([0x80 | n])
    elif n < 65536:
        head += bytes([0x80 | 126]) + struct.pack(">H", n)
    else:
        head += bytes([0x80 | 127]) + struct.pack(">Q", n)
    s.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

def ws_messages(s):
    """Yield text messages; answer pings; stop on close."""
    parts = []
    while True:
        b1, b2 = _recv(s, 2)
        opcode, n = b1 & 0x0F, b2 & 0x7F
        if n == 126:
            n = struct.unpack(">H", _recv(s, 2))[0]
        elif n == 127:
            n = struct.unpack(">Q", _recv(s, 8))[0]
        mask = _recv(s, 4) if b2 & 0x80 else None
        data = _recv(s, n)
        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        if opcode == 0x8:
            return
        if opcode == 0x9:
            _send(s, 0xA, data)
        elif opcode in (0x0, 0x1):
            parts.append(data)
            if b1 & 0x80:
                yield b"".join(parts).decode()
                parts = []

def wants_transfer(ev):
    """True when the model called transfer_call: in response.done's output
    items (the documented signal) or the per-call arguments.done event."""
    if ev.get("type") == "response.done":
        return any(i.get("type") == "function_call" and i.get("name") == "transfer_call"
                   for i in (ev.get("response") or {}).get("output") or [])
    return (ev.get("type") == "response.function_call_arguments.done"
            and ev.get("name") == "transfer_call")

def watch_call(call_id, agent):
    """Greet the caller, then refer the call when the model calls transfer_call."""
    try:
        s = ws_connect(call_id)
    except (OSError, ConnectionError) as e:
        print(f"ERROR: websocket for {call_id}: {e}; no greeting or transfer")
        return
    target = agent.get("transfer_to")
    try:
        # Accepting alone does not make the agent speak. The greeting turn
        # may not use tools, so it can never start a transfer.
        _send(s, 0x1, json.dumps({"type": "response.create", "response": {
            "tool_choice": "none",
            "instructions": "Greet the caller with: " + agent.get(
                "greeting", "Hello, how can I help you?")}}).encode())
        t0 = time.time()
        for msg in ws_messages(s):
            ev = json.loads(msg)
            if LOG_TRANSCRIPT and ev.get("type") == "response.output_audio_transcript.done":
                print(f"  [{time.time() - t0:5.1f}s] agent said: {ev.get('transcript', '')!r}")
            if target and wants_transfer(ev):
                print(f"  [{time.time() - t0:5.1f}s] model called transfer_call")
                try:
                    api(f"/v1/realtime/calls/{call_id}/refer", {"target_uri": target})
                    # 200 means OpenAI relayed the REFER, not that anyone answered.
                    print(f"transferred {call_id} to {target}")
                except urllib.error.HTTPError as e:
                    print(f"ERROR: refer for {call_id} failed: {e.code} "
                          f"{e.read().decode()[:500]}")
                except urllib.error.URLError as e:
                    print(f"ERROR: refer for {call_id} failed: {e}")
                return  # one transfer per call, even if events repeat
    except (OSError, ConnectionError, ValueError):
        pass  # call ended or the socket dropped
    finally:
        s.close()

class H(BaseHTTPRequestHandler):
    timeout = 10  # a slow or stalled client cannot hold a worker

    def reply(self, code):
        self.send_response(code); self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self.reply(411)
        if length < 0 or length > MAX_BODY:
            return self.reply(413)
        body = self.rfile.read(length)
        if not verify(body, self.headers):
            print("rejected a webhook: bad signature (wrong OPENAI_WEBHOOK_SECRET "
                  "for this webhook, or a stale timestamp)")
            return self.reply(401)
        wid = self.headers.get("webhook-id", "")
        if already_handled(wid):
            return self.reply(200)  # duplicate delivery or replay
        try:
            event = json.loads(body)
        except ValueError:
            return self.reply(400)
        if event.get("type") == "realtime.call.incoming":
            call_id = event["data"]["call_id"]
            headers = {h["name"].lower(): h["value"]
                       for h in event["data"].get("sip_headers", [])}
            did = called_did(headers)
            try:
                if did:
                    agent = AGENTS[did]
                    session = {"type": "realtime", "model": MODEL,
                               "instructions": agent["instructions"]}
                    if agent.get("transfer_to"):
                        session["tools"] = [TRANSFER_TOOL]
                    api(f"/v1/realtime/calls/{call_id}/accept", session)
                    print(f"accepted {call_id} for {did}")
                    threading.Thread(target=watch_call, daemon=True,
                                     args=(call_id, agent)).start()
                else:
                    api(f"/v1/realtime/calls/{call_id}/reject",
                        {"status_code": 603})
                    print(f"rejected {call_id}: unknown DID (Diversion="
                          f"{headers.get('diversion', '')!r}, To={headers.get('to', '')!r})")
            except urllib.error.HTTPError as e:
                # Answer 500 so OpenAI retries, instead of dropping the
                # connection with a traceback; the body says why.
                print(f"ERROR: OpenAI API {e.code} for {call_id}: "
                      f"{e.read().decode()[:500]}")
                return self.reply(500)
            except urllib.error.URLError as e:
                print(f"ERROR: OpenAI API unreachable for {call_id}: {e.reason}")
                return self.reply(500)
        mark_handled(wid)  # only after success, so OpenAI's retries still run
        self.reply(200)

    def _other(self):
        self.reply(405)  # only POST webhooks are handled

    do_GET = do_HEAD = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _other

    def log_message(self, *a):
        pass

def load_env_file(path):
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v and not os.environ.get(k.strip()):
                    os.environ[k.strip()] = v

def check_agents():
    """Refuse transfer targets that DIDWW rejects or that loop back."""
    problems = []
    for did, agent in AGENTS.items():
        target = agent.get("transfer_to") or ""
        if not target:
            continue
        m = re.match(r"sips?:\+?(\d+)@[A-Za-z0-9.-]+$", target)
        if not m:
            problems.append(f"{did}: transfer_to must look like "
                            f"sip:+NUMBER@fra.eu.out.didww.com, not {target!r}")
        elif any(digits(d) == m.group(1) for d in AGENTS):
            problems.append(f"{did}: transfer_to is a DID served by this agent "
                            "and would loop back")
    return problems

def main():
    global API_KEY, SECRET
    if sys.argv[1:2] == ["--env-file"] and len(sys.argv) > 2:
        load_env_file(sys.argv[2])  # fills only variables not already set
        API_KEY = os.environ.get("OPENAI_API_KEY", "")
        SECRET = os.environ.get("OPENAI_WEBHOOK_SECRET", "")
    missing = [n for n, v in (("OPENAI_API_KEY", API_KEY),
                              ("OPENAI_WEBHOOK_SECRET", SECRET)) if not v]
    if missing:
        sys.exit(f"refusing to start: set {', '.join(missing)} "
                 "(without the secret anyone could make this server accept calls)")
    problems = check_agents()
    if problems:
        sys.exit("refusing to start:\n  " + "\n  ".join(problems))
    port = int(os.environ.get("PORT", "8080"))
    print(f"listening on :{port}; DIDs configured: {list(AGENTS) or 'NONE, edit AGENTS'}")
    ThreadingHTTPServer(("", port), H).serve_forever()

if __name__ == "__main__":
    main()
