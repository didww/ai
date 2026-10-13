#!/usr/bin/env python3
"""Signed-webhook tests for didww-to-openai-realtime/scripts/webhook_server.py.
Starts the real handler on a local port, stubs only the OpenAI HTTP call."""
import base64, contextlib, hashlib, hmac, http.client, importlib.util, io, itertools, json, os, socket, struct, subprocess, sys, threading, time, urllib.error, urllib.request
from http.server import ThreadingHTTPServer
sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folders
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "webhook_server.py"); results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
KEY = base64.b64encode(b"k" * 32).decode()
os.environ.update({"OPENAI_API_KEY": "sk-test", "OPENAI_WEBHOOK_SECRET": "whsec_" + KEY})
spec = importlib.util.spec_from_file_location("webhook_server", P); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.AGENTS = {"+33144556677": {"instructions": "Be helpful.", "transfer_to": "tel:+33600000000"},
              "+33155667788": {"instructions": "No transfer here."}}
ws = {"peer": None, "opened": []}
def fake_ws_connect(call_id):  # hand the watcher one end of a local socket pair
    a, b = socket.socketpair(); ws["peer"] = b; ws["opened"].append(call_id); return a
mod.ws_connect = fake_ws_connect
calls = []; fail = {"code": None}
class R:
    def __enter__(s): return s
    def __exit__(s, *a): pass
    def read(s): return b"{}"
def fake_urlopen(req, timeout=None):
    calls.append({"url": req.full_url, "body": json.loads(req.data)})
    if fail["code"]: raise urllib.error.HTTPError(req.full_url, fail["code"], "err", {}, io.BytesIO(b'{"error":"boom"}'))
    return R()
urllib.request.urlopen = fake_urlopen
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
srv = ThreadingHTTPServer(("127.0.0.1", port), mod.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
log = io.StringIO()
ids = itertools.count()
def post(event, ts=None, sig=None, wid=None):
    wid = wid or f"msg_{next(ids)}"
    body = json.dumps(event).encode(); ts = str(int(time.time())) if ts is None else ts
    if sig is None:
        mac = hmac.new(base64.b64decode(KEY), f"{wid}.{ts}.{body.decode()}".encode(), hashlib.sha256)
        sig = "v1," + base64.b64encode(mac.digest()).decode()
    calls.clear(); log.truncate(0); log.seek(0)
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    with contextlib.redirect_stdout(log):
        c.request("POST", "/", body=body, headers={"Content-Type": "application/json", "webhook-id": wid, "webhook-timestamp": ts, "webhook-signature": sig})
        r = c.getresponse(); r.read()
    return r.status
def incoming(to, raw=None):
    return {"type": "realtime.call.incoming", "data": {"call_id": "rtc_1", "sip_headers": [{"name": "To", "value": raw or f"sip:{to}@sip.api.openai.com"}, {"name": "From", "value": "sip:+441234567890@carrier"}]}}
st = post(incoming("+33144556677"))
check("webhook: known DID -> accept with model + instructions, 200", st == 200 and len(calls) == 1 and calls[0]["url"].endswith("/v1/realtime/calls/rtc_1/accept") and calls[0]["body"].get("type") == "realtime" and calls[0]["body"].get("instructions") == "Be helpful." and bool(calls[0]["body"].get("model")), (st, calls))
st = post(incoming("+15550001111"))
check("webhook: unknown DID -> reject 603, 200", st == 200 and len(calls) == 1 and calls[0]["url"].endswith("/reject") and calls[0]["body"] == {"status_code": 603}, (st, calls))
st = post(incoming("+33144556677"), sig="v1,AAAA")
check("webhook: bad signature -> 401, no API call", st == 401 and not calls, st)
st = post(incoming("+33144556677"), ts=str(int(time.time()) - 600))
check("webhook: valid signature but 10 minutes old -> 401 (5-minute replay window)", st == 401 and not calls, st)
st = post(incoming("+33144556677"), ts="garbage")
check("webhook: non-numeric timestamp -> 401", st == 401 and not calls, st)
st = post({"type": "realtime.call.ended", "data": {"call_id": "rtc_1"}})
check("webhook: other event types -> 200 without API calls", st == 200 and not calls, st)
fail["code"] = 500
st = post(incoming("+33144556677"))
check("webhook: accept API failure -> HTTP 500 response, logged, no traceback", st == 500 and "ERROR: OpenAI API 500" in log.getvalue() and "Traceback" not in log.getvalue(), f"got {st}")
fail["code"] = None
st = post(incoming("+33144556677"), wid="msg_retry")
check("webhook: retry with the same webhook-id after a 500 is processed", st == 200 and len(calls) == 1 and calls[0]["url"].endswith("/accept"), (st, calls))
st = post(incoming("+33144556677"), wid="msg_retry")
check("webhook: duplicate delivery of a handled webhook-id -> 200, no second API call", st == 200 and not calls, (st, calls))
for label, to in (("prefix of a known DID", "+3314455667"), ("known DID inside a longer number", "+133144556677"), ("known DID in the host part", "+15550001111@33144556677.example.com;x=")):
    st = post(incoming(to))
    check(f"webhook: exact DID match, {label} -> reject", st == 200 and len(calls) == 1 and calls[0]["url"].endswith("/reject"), (st, calls))
st = post(incoming(None, raw='"Front desk" <sip:33144556677@sip.api.openai.com>;tag=abc'))
check("webhook: name-addr To header without + still matches exactly", st == 200 and calls and calls[0]["url"].endswith("/accept"), (st, calls))
st = post(incoming("+33155667788"))
check("webhook: DID without transfer_to -> accept without tools", st == 200 and calls and "tools" not in calls[0]["body"], calls)
def raw_post(head):
    c = socket.create_connection(("127.0.0.1", port), timeout=5); c.sendall(head)
    data = c.recv(100); c.close(); return data.split(b" ")[1] if data else b""
check("webhook: Content-Length over 1 MB -> 413 before reading the body", raw_post(b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 999999999\r\n\r\n") == b"413")
check("webhook: missing Content-Length -> 411", raw_post(b"POST / HTTP/1.1\r\nHost: x\r\n\r\n") == b"411")
check("webhook: negative Content-Length -> 413", raw_post(b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: -5\r\n\r\n") == b"413")
# transfer: accept carries the tool, the watcher answers pings and refers on the tool call
ws["opened"].clear()
st = post(incoming("+33144556677"))
tools = calls[0]["body"].get("tools", []) if calls else []
check("transfer: accept body carries the transfer_call function tool", st == 200 and [t.get("name") for t in tools] == ["transfer_call"] and tools[0].get("type") == "function", calls)
for _ in range(50):
    if ws["opened"]: break
    time.sleep(0.05)
check("transfer: watcher opens the call websocket for that call_id", ws["opened"] == ["rtc_1"], ws["opened"])
def frame(op, payload):  # server frames are unmasked
    n = len(payload); return bytes([0x80 | op]) + (bytes([n]) if n < 126 else bytes([126]) + struct.pack(">H", n)) + payload
peer = ws["peer"]; peer.settimeout(5); calls.clear()
peer.sendall(frame(0x9, b"hi"))
pong = peer.recv(2 + 4 + 2)
check("transfer: ping is answered with a masked pong", pong[0] == 0x8A and pong[1] == 0x82 and bytes(b ^ pong[2 + i % 4] for i, b in enumerate(pong[6:])) == b"hi", pong)
peer.sendall(frame(0x1, json.dumps({"type": "response.output_audio.delta", "delta": "x" * 300}).encode()))
with contextlib.redirect_stdout(log):
    peer.sendall(frame(0x1, json.dumps({"type": "response.function_call_arguments.done", "name": "transfer_call", "call_id": "fc_1", "arguments": "{}"}).encode()))
    for _ in range(50):
        if calls: break
        time.sleep(0.05)
check("transfer: tool call -> POST /refer with the configured target_uri", len(calls) == 1 and calls[0]["url"].endswith("/v1/realtime/calls/rtc_1/refer") and calls[0]["body"] == {"target_uri": "tel:+33600000000"}, calls)
peer.close()
check("transfer: response.done with a transfer_call output item is recognised", mod.wants_transfer({"type": "response.done", "response": {"output": [{"type": "message"}, {"type": "function_call", "name": "transfer_call", "call_id": "fc_2", "arguments": "{}"}]}}))
check("transfer: response.done without the tool call is ignored", not mod.wants_transfer({"type": "response.done", "response": {"output": [{"type": "function_call", "name": "lookup"}]}}) and not mod.wants_transfer({"type": "response.done", "response": None}))
srv.shutdown()
env = {k: v for k, v in os.environ.items() if k not in ("OPENAI_WEBHOOK_SECRET",)}
r = subprocess.run([sys.executable, "-B", P], env=env, capture_output=True, text=True, timeout=10)
check("startup: refuses to run without OPENAI_WEBHOOK_SECRET", r.returncode != 0 and "OPENAI_WEBHOOK_SECRET" in r.stderr, (r.returncode, r.stderr[-200:]))
print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
