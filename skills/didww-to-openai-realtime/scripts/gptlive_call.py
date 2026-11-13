#!/usr/bin/env python3
"""Place one GPT-Live outbound call through a DIDWW outbound SIP trunk.

OpenAI dials the number through your DIDWW outbound trunk. This script
creates the call (POST /v1/live/sessions), attaches to it at once over the
sideband WebSocket, logs call progress and the transcript, answers the
agent's delegated tasks, and hangs up at --max-seconds or on Ctrl-C.
Each run places exactly ONE call and never retries: a retry would dial the
destination again. Stdlib only.

Credentials come from the environment or from --env-file (KEY=VALUE lines):
OPENAI_API_KEY, DIDWW_SIP_USERNAME, DIDWW_SIP_PASSWORD (the outbound trunk
Username and Password). They are redacted from every printed line. Create
a private template with --init-env and let the user fill it in; never put
credentials on the command line or in chat.

  gptlive_call.py --init-env ~/.didww-openai.env
  gptlive_call.py --env-file ~/.didww-openai.env --to +15105550199 \\
      --from +15105550100 --instructions-file agent.txt --check
  gptlive_call.py --env-file ~/.didww-openai.env --to +15105550199 \\
      --from +15105550100 --instructions-file agent.txt
"""
import argparse, base64, json, os, re, select, socket, ssl, stat, struct, sys
import time, urllib.error, urllib.request

API_HOST = "api.openai.com"
MODEL = os.environ.get("LIVE_MODEL", "gpt-live-1")
KEYS = ("OPENAI_API_KEY", "DIDWW_SIP_USERNAME", "DIDWW_SIP_PASSWORD")
E164 = re.compile(r"^\+[1-9]\d{6,14}$")
HOST = re.compile(r"^[A-Za-z0-9.-]+$")
QUIET = ("session.input_audio.append", "session.usage.updated")

DEFAULT_INSTRUCTIONS = (
    "You are calling on behalf of Example Corp. The person did not call you. "
    "Introduce yourself when the person answers, say that you are an AI "
    "assistant, and keep answers short.")

# Spoken result for a delegated task while no backend is connected; GPT-Live
# paraphrases it. Replace handle_delegation() with your real backend.
NO_BACKEND_REPLY = (
    "Nothing can be looked up, booked or sent during this call. Continue the "
    "conversation from your instructions and what the person has said, and "
    "do not promise any follow-up.")

API_KEY = ""
SECRETS = []
T0 = time.time()


def log(*parts):
    msg = " ".join(str(p) for p in parts)
    for s in SECRETS:
        msg = msg.replace(s, "***")
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# --- credentials ---

def init_env(path):
    path = os.path.expanduser(path)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        sys.exit(f"{path} already exists; not overwritten")
    with os.fdopen(fd, "w") as f:
        f.write("# DIDWW + OpenAI. Fill in the values and save; keep this file private.\n"
                "# OpenAI API key (platform.openai.com/api-keys)\n"
                "OPENAI_API_KEY=\n"
                "# DIDWW outbound trunk Username and Password\n"
                "# (Voice > Outbound Trunks, key icon in the Credentials column)\n"
                "DIDWW_SIP_USERNAME=\n"
                "DIDWW_SIP_PASSWORD=\n"
                "# Incoming calls only: the webhook signing secret (whsec_...)\n"
                "OPENAI_WEBHOOK_SECRET=\n")
    print(f"created {path} (mode 600); fill it in, then run with --env-file {path} --check")


def load_env_file(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_credentials(env_file):
    creds = {}
    if env_file:
        path = os.path.expanduser(env_file)
        if os.stat(path).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            print(f"warning: other users can read {path}; run: chmod 600 {path}")
        creds.update(load_env_file(path))
    for k in KEYS:  # the environment wins over the file
        if os.environ.get(k):
            creds[k] = os.environ[k]
    missing = [k for k in KEYS if not creds.get(k)]
    if missing:
        where = f" in {env_file}" if env_file else " (set them, or use --env-file)"
        sys.exit("missing " + ", ".join(missing) + where)
    return creds


# --- OpenAI API ---

def post(path, payload=None):
    req = urllib.request.Request(
        f"https://{API_HOST}{path}", method="POST",
        data=json.dumps(payload).encode() if payload is not None else b"",
        headers={"Authorization": "Bearer " + API_KEY,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


class Sideband:
    """Client WebSocket to /v1/live/sessions/{id}/attach."""

    def __init__(self, session_id):
        raw = socket.create_connection((API_HOST, 443), timeout=30)
        self.s = ssl.create_default_context().wrap_socket(raw, server_hostname=API_HOST)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /v1/live/sessions/{session_id}/attach HTTP/1.1\r\n"
                        f"Host: {API_HOST}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
                        f"Authorization: Bearer {API_KEY}\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.s.recv(1)
            if not chunk:
                raise ConnectionError("websocket handshake closed")
            head += chunk
        status = head.split(b"\r\n", 1)[0]
        if b" 101 " not in status + b" ":
            raise ConnectionError(status.decode(errors="replace"))
        self.parts = []

    def _recv(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("websocket closed")
            buf += chunk
        return buf

    def _send(self, opcode, payload=b""):
        mask = os.urandom(4)  # client frames must be masked
        n = len(payload)
        head = bytes([0x80 | opcode])
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.s.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def send(self, event):
        self._send(0x1, json.dumps(event).encode())

    def recv(self, wait):
        """Next text message, or None if nothing arrived within wait seconds.
        Waits before reading, so a timeout never cuts a frame in half."""
        while True:
            if not self.s.pending() and not select.select([self.s], [], [], wait)[0]:
                return None
            b1, b2 = self._recv(2)
            opcode, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._recv(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._recv(8))[0]
            mask = self._recv(4) if b2 & 0x80 else None
            data = self._recv(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x8:
                raise ConnectionError("closed by OpenAI")
            if opcode == 0x9:
                self._send(0xA, data)
            elif opcode in (0x0, 0x1):
                self.parts.append(data)
                if b1 & 0x80:
                    msg, self.parts = b"".join(self.parts).decode(), []
                    return msg

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


# --- conversation and delegation ---

class Transcript:
    """Joins transcript deltas into lines. A delegation carries no task
    text, so the backend works out the task from these lines."""

    def __init__(self):
        self.lines, self.role, self.buf = [], None, []

    def add(self, role, text):
        if role != self.role:
            self.flush()
            self.role = role
        self.buf.append(text)

    def flush(self):
        text = "".join(self.buf).strip()
        if self.role and text:
            self.lines.append((self.role, text))
            log(f"{self.role}: {text}")
        self.role, self.buf = None, []


def handle_delegation(delegation, transcript):
    """Return (event_type, content) for one delegated task.

    Replace this with your backend: work out the task from
    transcript.lines, run the lookup or action, and return what happened.
    session.commentary.append is spoken (paraphrased), session.thinking.append
    is silent context; content is limited to 500 tokens. Report an action as
    done only after it really succeeded."""
    return "session.commentary.append", NO_BACKEND_REPLY


# --- main ---

def parse_args():
    p = argparse.ArgumentParser(description="Place one GPT-Live outbound call through DIDWW.")
    p.add_argument("--init-env", metavar="PATH", help="create a private credentials template and exit")
    p.add_argument("--env-file", metavar="PATH", help="KEY=VALUE file with the credentials")
    p.add_argument("--to", help="number to call, E.164 (e.g. +15105550199)")
    p.add_argument("--from", dest="caller", help="DIDWW number shown as caller ID, E.164")
    p.add_argument("--gateway", default="fra.eu.out.didww.com",
                   help="DIDWW outbound signaling endpoint (default fra.eu.out.didww.com)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--instructions", help="agent instructions")
    g.add_argument("--instructions-file", metavar="PATH", help="file with the agent instructions")
    p.add_argument("--voice", default="marin")
    p.add_argument("--max-seconds", type=int, default=300,
                   help="hang up after this many seconds (default 300)")
    p.add_argument("--check", action="store_true", help="validate everything and exit without calling")
    return p.parse_args()


def main():
    global API_KEY
    args = parse_args()
    if args.init_env:
        return init_env(args.init_env)
    for name, value in (("--to", args.to), ("--from", args.caller)):
        if not value or not E164.match(value):
            sys.exit(f"{name} must be an E.164 number such as +15105550199")
    if args.to == args.caller:
        sys.exit("--to and --from are the same number")
    if not HOST.match(args.gateway):
        sys.exit("--gateway must be a host name such as fra.eu.out.didww.com")
    if not 10 <= args.max_seconds <= 7200:
        sys.exit("--max-seconds must be between 10 and 7200")
    if args.instructions_file:
        with open(os.path.expanduser(args.instructions_file), encoding="utf-8") as f:
            instructions = f.read().strip()
    else:
        instructions = (args.instructions or DEFAULT_INSTRUCTIONS).strip()
    if not instructions:
        sys.exit("the instructions are empty")

    creds = load_credentials(args.env_file)
    API_KEY = creds["OPENAI_API_KEY"]
    SECRETS.extend(creds[k] for k in KEYS)
    provider_url = f"sips:{args.gateway}:5061"  # OpenAI requires TLS signaling
    payload = {
        "session": {
            "model": MODEL,
            "instructions": instructions,
            "audio": {"output": {"voice": args.voice}},
            "delegation": {"type": "client"},
        },
        "transport": {
            "type": "sip",
            "destination": args.to,
            "trunk": {
                "provider_url": provider_url,
                "auth": {"type": "digest",
                         "username": creds["DIDWW_SIP_USERNAME"],
                         "password": creds["DIDWW_SIP_PASSWORD"]},
                "caller_number": args.caller,
            },
        },
    }
    summary = (f"destination={args.to} caller={args.caller} trunk={provider_url} "
               f"model={MODEL} voice={args.voice} max={args.max_seconds}s "
               f"instructions={len(instructions)} chars")
    if args.check:
        log("check OK, no call placed:", summary, "| credentials: all 3 set")
        return 0

    log("placing ONE call:", summary)
    try:
        status, body = post("/v1/live/sessions", payload)
    except (urllib.error.URLError, OSError) as e:
        log(f"create request failed ({e}); the call may still have been placed. "
            "Check the DIDWW Outbound Call Logs before trying again.")
        return 1
    log("create ->", status, body[:500])
    if status not in (200, 201):
        return 1
    sid = json.loads(body)["session"]["id"]

    try:
        sb = Sideband(sid)
    except (OSError, ConnectionError) as e:
        log("attach failed:", e, "- hanging up so the call does not run unattended")
        log("hangup ->", *post(f"/v1/live/sessions/{sid}/hangup"))
        return 2
    log("attached to", sid)

    transcript, seen, streams = Transcript(), set(), set()
    answered = closed = False
    deadline, n = time.time() + args.max_seconds, 0
    try:
        while time.time() < deadline:
            try:
                msg = sb.recv(min(1.0, max(0.0, deadline - time.time())))
            except (OSError, ConnectionError) as e:
                log("sideband ended:", e)
                break
            if msg is None:
                continue
            try:
                ev = json.loads(msg)
            except ValueError:
                continue
            eid = ev.get("event_id")
            if eid in seen:
                continue
            if eid:
                seen.add(eid)
            t = ev.get("type", "")
            if t == "session.input_transcript.delta":
                transcript.add("person", ev.get("delta", ""))
                continue
            if t == "session.output_transcript.delta":
                transcript.add("agent", ev.get("delta", ""))
                continue
            if t in QUIET or t.endswith(".delta"):
                if t not in streams:  # e.g. output audio proves the agent spoke
                    streams.add(t)
                    log(f"{t} (first one; further ones not shown)")
                continue
            transcript.flush()
            if t == "transport.ringing":
                log("ringing")
            elif t == "transport.answered":
                answered = True
                log("answered")
            elif t == "transport.failed":
                log("call failed:", json.dumps(ev.get("error") or ev)[:500])
                deadline = min(deadline, time.time() + 10)  # wait for session.closed
            elif t == "session.delegation.created":
                did = (ev.get("delegation") or {}).get("id")
                kind, content = handle_delegation(ev.get("delegation") or {}, transcript)
                n += 1
                sb.send({"type": kind, "event_id": f"result_{n}_{int(time.time() * 1000)}",
                         "delegation_id": did, "content": content})
                log(f"delegation {did}: answered with {kind}")
            elif t == "session.closed":
                closed = True
                log("session closed:", ev.get("reason"))
                break
            elif t == "error":
                log("error:", json.dumps(ev.get("error") or ev)[:400])
            else:
                log(t)
    except KeyboardInterrupt:
        log("interrupted")
    transcript.flush()
    if not closed:
        log("hanging up")
        log("hangup ->", *post(f"/v1/live/sessions/{sid}/hangup"))
    sb.close()
    log("done; answered =", answered)
    return 0 if answered else 2


if __name__ == "__main__":
    sys.exit(main())
