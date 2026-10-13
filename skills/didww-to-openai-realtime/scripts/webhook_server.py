#!/usr/bin/env python3
"""Minimal call-control backend for DIDWW -> OpenAI Realtime SIP.

Receives realtime.call.incoming webhooks, accepts known DIDs with your
instructions, rejects everything else. When a DID has a transfer
target, the agent gets a transfer_call tool; the server watches the
call's websocket and, when the model calls the tool, hands the call to
the target through the refer endpoint. Stdlib only; run behind any
HTTPS front (reverse proxy, serverless wrapper, or a tunnel while
testing).

Env: OPENAI_API_KEY, OPENAI_WEBHOOK_SECRET (both required),
REALTIME_MODEL (default gpt-realtime), PORT (default 8080).
Edit AGENTS below: DID -> instructions and transfer target.
"""
import base64, hashlib, hmac, json, os, re, socket, ssl, struct, sys
import threading, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

API_KEY = os.environ.get("OPENAI_API_KEY", "")
SECRET = os.environ.get("OPENAI_WEBHOOK_SECRET", "")
MODEL = os.environ.get("REALTIME_MODEL", "gpt-realtime")
MAX_BODY = 1 << 20      # webhook events are small; refuse anything larger
TOLERANCE = 300         # seconds a signed event stays valid

AGENTS = {
    # "+33144556677": {
    #   "instructions": "You are the receptionist for ... Collect the "
    #                   "caller's name and confirm their callback number. "
    #                   "If they ask for a human, call the transfer_call tool.",
    #   "transfer_to": "tel:+33600000000",
    # },
}

TRANSFER_TOOL = {
    "type": "function", "name": "transfer_call",
    "description": "Transfer the caller to a human. Call this when the "
                   "caller asks for a person or you cannot help.",
    "parameters": {"type": "object", "properties": {}},
}

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

def match_did(to_header):
    """Exact match of the To URI's user part against AGENTS. This is
    routing, not authentication: the caller controls the To header."""
    m = re.search(r"sips?:([^@;>]+)@", to_header)
    if not m:
        return None
    user = digits(m.group(1))
    return next((d for d in AGENTS if user and digits(d) == user), None)

def api(path, payload):
    req = urllib.request.Request(
        "https://api.openai.com" + path, method="POST",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + API_KEY,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()

# --- call websocket (receive-only: the tool is set in the accept body) ---

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

def watch_call(call_id, target):
    """Refer the call to target when the model calls transfer_call."""
    try:
        s = ws_connect(call_id)
    except (OSError, ConnectionError) as e:
        print(f"ERROR: websocket for {call_id}: {e}; transfer unavailable")
        return
    try:
        for msg in ws_messages(s):
            if wants_transfer(json.loads(msg)):
                try:
                    api(f"/v1/realtime/calls/{call_id}/refer",
                        {"target_uri": target})
                    print(f"transferred {call_id} to {target}")
                except urllib.error.URLError as e:
                    print(f"ERROR: refer for {call_id} failed: {e}")
                return
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
            to = headers.get("to", "")
            did = match_did(to)
            try:
                if did:
                    agent = AGENTS[did]
                    session = {"type": "realtime", "model": MODEL,
                               "instructions": agent["instructions"]}
                    if agent.get("transfer_to"):
                        session["tools"] = [TRANSFER_TOOL]
                    api(f"/v1/realtime/calls/{call_id}/accept", session)
                    print(f"accepted {call_id} for {did}")
                    if agent.get("transfer_to"):
                        threading.Thread(target=watch_call, daemon=True,
                                         args=(call_id, agent["transfer_to"])).start()
                else:
                    api(f"/v1/realtime/calls/{call_id}/reject",
                        {"status_code": 603})
                    print(f"rejected {call_id}: unknown DID in {to!r}")
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

    def log_message(self, *a):
        pass

def main():
    missing = [n for n, v in (("OPENAI_API_KEY", API_KEY),
                              ("OPENAI_WEBHOOK_SECRET", SECRET)) if not v]
    if missing:
        sys.exit(f"refusing to start: set {', '.join(missing)} "
                 "(without the secret anyone could make this server accept calls)")
    port = int(os.environ.get("PORT", "8080"))
    print(f"listening on :{port}; DIDs configured: {list(AGENTS) or 'NONE, edit AGENTS'}")
    ThreadingHTTPServer(("", port), H).serve_forever()

if __name__ == "__main__":
    main()
