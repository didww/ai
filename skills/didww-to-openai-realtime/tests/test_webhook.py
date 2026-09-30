#!/usr/bin/env python3
"""Signed-webhook tests for didww-to-openai-realtime/scripts/webhook_server.py.
Starts the real handler on a local port, stubs only the OpenAI HTTP call."""
import base64, contextlib, hashlib, hmac, http.client, importlib.util, io, json, os, socket, sys, threading, time, urllib.error, urllib.request
from http.server import HTTPServer
sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folders
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "webhook_server.py"); results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
KEY = base64.b64encode(b"k" * 32).decode()
os.environ.update({"OPENAI_API_KEY": "sk-test", "OPENAI_WEBHOOK_SECRET": "whsec_" + KEY})
spec = importlib.util.spec_from_file_location("webhook_server", P); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.AGENTS = {"+33144556677": {"instructions": "Be helpful.", "transfer_to": "tel:+33600000000"}}
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
srv = HTTPServer(("127.0.0.1", port), mod.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
log = io.StringIO()
def post(event, ts=None, sig=None, wid="msg_1"):
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
def incoming(to):
    return {"type": "realtime.call.incoming", "data": {"call_id": "rtc_1", "sip_headers": [{"name": "To", "value": f"sip:{to}@sip.api.openai.com"}, {"name": "From", "value": "sip:+441234567890@carrier"}]}}
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
srv.shutdown()
print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
