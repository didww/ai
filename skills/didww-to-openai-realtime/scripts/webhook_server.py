#!/usr/bin/env python3
"""Minimal call-control backend for DIDWW -> OpenAI Realtime SIP.

Receives realtime.call.incoming webhooks, accepts known DIDs with your
instructions, rejects everything else. Stdlib only; run behind any HTTPS
front (reverse proxy, serverless wrapper, or a tunnel while testing).

Env: OPENAI_API_KEY, OPENAI_WEBHOOK_SECRET, PORT (default 8080).
Edit AGENTS below: DID -> instructions and transfer target.
"""
import base64, hashlib, hmac, json, os, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

API_KEY = os.environ.get("OPENAI_API_KEY", "")
SECRET = os.environ.get("OPENAI_WEBHOOK_SECRET", "")
MODEL = os.environ.get("REALTIME_MODEL", "gpt-realtime")

AGENTS = {
    # "+33144556677": {
    #   "instructions": "You are the receptionist for ... Collect the "
    #                   "caller's name and confirm their callback number. "
    #                   "If they ask for a human, call the transfer tool.",
    #   "transfer_to": "tel:+33600000000",
    # },
}

def verify(body, headers):
    """Standard Webhooks style signature check; adapt if SDK available."""
    if not SECRET:
        return True  # testing only; never run open in production
    sig = headers.get("webhook-signature", "")
    wid = headers.get("webhook-id", "")
    ts = headers.get("webhook-timestamp", "")
    try:  # a captured event must not be replayable later
        if abs(time.time() - int(ts)) > 300:
            return False
    except ValueError:
        return False
    secret = SECRET.split("_", 1)[-1]
    mac = hmac.new(base64.b64decode(secret),
                   f"{wid}.{ts}.{body.decode()}".encode(), hashlib.sha256)
    expect = "v1," + base64.b64encode(mac.digest()).decode()
    return any(hmac.compare_digest(expect, s) for s in sig.split())

def api(path, payload):
    req = urllib.request.Request(
        "https://api.openai.com" + path, method="POST",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + API_KEY,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if not verify(body, self.headers):
            self.send_response(401); self.end_headers(); return
        event = json.loads(body)
        if event.get("type") == "realtime.call.incoming":
            call_id = event["data"]["call_id"]
            headers = {h["name"].lower(): h["value"]
                       for h in event["data"].get("sip_headers", [])}
            to = headers.get("to", "")
            did = next((d for d in AGENTS if d.lstrip("+") in to), None)
            try:
                if did:
                    api(f"/v1/realtime/calls/{call_id}/accept",
                        {"type": "realtime", "model": MODEL,
                         "instructions": AGENTS[did]["instructions"]})
                    print(f"accepted {call_id} for {did}")
                else:
                    api(f"/v1/realtime/calls/{call_id}/reject",
                        {"status_code": 603})
                    print(f"rejected {call_id}: unknown DID in {to!r}")
            except urllib.error.HTTPError as e:
                # Answer 500 so OpenAI retries, instead of dropping the
                # connection with a traceback; the body says why.
                print(f"ERROR: OpenAI API {e.code} for {call_id}: "
                      f"{e.read().decode()[:500]}")
                self.send_response(500); self.end_headers(); return
            except urllib.error.URLError as e:
                print(f"ERROR: OpenAI API unreachable for {call_id}: {e.reason}")
                self.send_response(500); self.end_headers(); return
        self.send_response(200); self.end_headers()
    def log_message(self, *a):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"listening on :{port}; DIDs configured: {list(AGENTS) or 'NONE, edit AGENTS'}")
    HTTPServer(("", port), H).serve_forever()
