import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
SCEN, PORT = sys.argv[1], int(sys.argv[2])
def data():
    bal = 5.0 if SCEN == "lowbal" else 42.5
    credit = 0.0
    if SCEN == "creditline":
        bal, credit = -37723.54, 50000.00
    dids = [{"id":"d1","type":"dids","attributes":{"number":"33144556677","blocked": SCEN=="blocked","awaiting_registration":False}},
            {"id":"d2","type":"dids","attributes":{"number":"441234567890","blocked":False,"awaiting_registration": SCEN=="awaiting"}}]
    if SCEN == "terminated":
        dids.append({"id":"d3","type":"dids","attributes":{"number":"13614157804","blocked":True,"terminated":True,"awaiting_registration":False}})
    trunks = [] if SCEN == "notrunk" else [{"id":"t1","type":"trunks","attributes":{"name":"in-elevenlabs"}}]
    return {"/balance":{"data":{"id":"b","type":"balances","attributes":{"balance":str(bal),"credit":str(credit),"total_balance":str(round(bal+credit,2))}}},
            "/dids":{"data":dids}, "/trunks":{"data":trunks}}
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if SCEN == "http500" and path == "/balance":
            self.send_response(500); self.end_headers(); self.wfile.write(b'{"errors":[{"title":"boom"}]}'); return
        if self.headers.get("Api-Key") != "fake" or "vnd.api+json" not in self.headers.get("Accept",""):
            self.send_response(401); self.end_headers(); self.wfile.write(b'{"errors":[{"title":"bad headers"}]}'); return
        body = json.dumps(data().get(path, {"data": []})).encode()
        self.send_response(200); self.send_header("Content-Type","application/vnd.api+json"); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", PORT), H).serve_forever()
