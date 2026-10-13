import json, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
SCEN, PORT = sys.argv[1], int(sys.argv[2])
def data():
    bal = 5.0 if SCEN == "lowbal" else 42.5
    credit = 0.0
    if SCEN == "creditline":
        bal, credit = -37723.54, 50000.00
    dids = [{"id":"d1","type":"dids","attributes":{"number":"33144556677","blocked": SCEN=="blocked","awaiting_registration":False}},
            {"id":"d2","type":"dids","attributes":{"number":"441234567890","blocked":False,"awaiting_registration": SCEN=="awaiting"}}]
    if SCEN in ("many", "offhost"):  # 150 DIDs: two pages at the 100 maximum
        dids = [{"id": f"m{i}", "type": "dids", "attributes": {"number": f"3314400{i:04d}", "blocked": SCEN == "many" and i == 149, "awaiting_registration": False}} for i in range(150)]
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
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        size = int(q.get("page[size]", ["50"])[0]); num = int(q.get("page[number]", ["1"])[0])
        if size > 100:  # DIDWW's documented maximum page size
            self.send_response(400); self.end_headers(); self.wfile.write(b'{"errors":[{"title":"page size too large"}]}'); return
        if (SCEN == "dids500" and path == "/dids") or (SCEN == "trunks500" and path == "/trunks"):
            self.send_response(500); self.end_headers(); self.wfile.write(b'{"errors":[{"title":"boom"}]}'); return
        full = data().get(path, {"data": []})
        if isinstance(full.get("data"), list):
            items = full["data"]; page = {"data": items[(num - 1) * size: num * size], "links": {}}
            if num * size < len(items):
                host = "https://evil.example" if SCEN == "offhost" else f"http://127.0.0.1:{PORT}"
                page["links"]["next"] = f"{host}{path}?page[number]={num + 1}&page[size]={size}"
            full = page
        body = json.dumps(full).encode()
        self.send_response(200); self.send_header("Content-Type","application/vnd.api+json"); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", PORT), H).serve_forever()
