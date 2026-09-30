#!/usr/bin/env python3
"""Create the Vapi credential + number for a DIDWW trunk, bind assistant.

Usage:
  VAPI_API_KEY=... python3 scripts/connect.py \
    --number +33144556677 --didww-host fra.eu.out.didww.com \
    --didww-user USER --didww-pass PASS [--assistant ASSISTANT_ID] [--eu]

Prints the per-credential ingress host the DIDWW inbound trunk must point
at. Stdlib only; API errors print verbatim for self-correction.
"""
import json, os, sys, urllib.request

KEY = os.environ.get("VAPI_API_KEY", "")
if not KEY:
    sys.exit("Set VAPI_API_KEY (dashboard: Organization Settings, API Keys).")
a = sys.argv[1:]
def opt(n, d=None):
    return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
if any(opt(n) is None for n in
       ("--number", "--didww-host", "--didww-user", "--didww-pass")):
    sys.exit(__doc__)

def call(method, path, body=None):
    req = urllib.request.Request(
        "https://api.vapi.ai" + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json",
                 # api.vapi.ai sits behind Cloudflare, which rejects
                 # Python's default User-Agent (error 1010) before auth.
                 "User-Agent": "didww-to-vapi/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Vapi API {e.code} on {path}:\n{e.read().decode()[:2000]}")

cred = call("POST", "/credential", {
    "provider": "byo-sip-trunk",
    "name": "DIDWW " + opt("--didww-host"),
    "gateways": [{"ip": opt("--didww-host"), "inboundEnabled": False}],
    "outboundLeadingPlusEnabled": True,
    "outboundAuthenticationPlan": {
        "authUsername": opt("--didww-user"),
        "authPassword": opt("--didww-pass"),
    },
})
cid = cred.get("id")
print(f"Credential created: {cid}")

num_body = {
    "provider": "byo-phone-number",
    "name": "DIDWW " + opt("--number"),
    "number": opt("--number").lstrip("+"),
    "numberE164CheckEnabled": False,
    "credentialId": cid,
}
if opt("--assistant"):
    num_body["assistantId"] = opt("--assistant")
num = call("POST", "/phone-number", num_body)
print(f"Number object created: {num.get('id')}")

domain = "sip.eu.vapi.ai" if "--eu" in a else "sip.vapi.ai"
print("\nNOW BUILD THE DIDWW INBOUND TRUNK:")
print(f"  host: {cid}.{domain}   port 5060")
ips = "63.182.83.170" if "--eu" in a else "44.229.228.186 and 44.238.177.138"
print(f"  allow Vapi signaling IPs on the trunk: {ips}")
print("  attach the DID, then place test calls both directions.")
if not opt("--assistant"):
    print("Bind an assistant: PATCH /phone-number/{id} with assistantId, "
          "or via the Vapi dashboard.")
