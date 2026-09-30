#!/usr/bin/env python3
"""Register a DIDWW number with xAI Grok voice SIP.

Usage:
  XAI_API_KEY=... python3 scripts/register_number.py \
    --number +33144556677 --webhook https://your.host/xai \
    [--sip-user USER --sip-pass PASS] [--allow-ip 1.2.3.4 ...]

Digest credentials are preferred; the password is never returned after
creation, so configure the DIDWW trunk with it immediately. The response
also carries the webhook signing secret exactly once: store it for the
backend. Both flag groups may be combined (digest plus an IP allowlist).
"""
import json, os, sys, urllib.request

KEY = os.environ.get("XAI_API_KEY", "")
if not KEY:
    sys.exit("Set XAI_API_KEY (console.x.ai).")
a = sys.argv[1:]
def opt(n, d=None):
    return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
if not opt("--number") or not opt("--webhook"):
    sys.exit(__doc__)

sip_auth = {}
if opt("--sip-user"):
    if not opt("--sip-pass"):
        sys.exit("--sip-user needs --sip-pass.")
    sip_auth.update({"auth_username": opt("--sip-user"),
                     "auth_password": opt("--sip-pass")})
ips = [a[i + 1] for i, x in enumerate(a) if x == "--allow-ip"]
if ips:
    sip_auth["allowed_addresses"] = ips
if not sip_auth:
    sys.exit("Give --sip-user/--sip-pass (digest, preferred) and/or "
             "--allow-ip; an unauthenticated ingress accepts anyone's calls.")
# Field names per xAI's API: origin byo_trunk = customer-owned number;
# webhook is an object {url, name?, auth_url?, auth_token?}.
body = {"origin": "byo_trunk", "name": "DIDWW " + opt("--number"),
        "phone_number": opt("--number"),
        "webhook": {"url": opt("--webhook")},
        "sip_auth": sip_auth}
req = urllib.request.Request(
    "https://api.x.ai/v2/phone-numbers", method="POST",
    data=json.dumps(body).encode(),
    headers={"Authorization": "Bearer " + KEY,
             "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(json.dumps(json.load(r), indent=1)[:1000])
except urllib.error.HTTPError as e:
    sys.exit(f"xAI API {e.code}:\n{e.read().decode()[:2000]}")
print("\nSTORE the webhook signing secret from the response now: xAI "
      "returns it only once (the SIP password is never returned at all).")
print("DIDWW inbound trunk destination: "
      f"sip:{opt('--number')}@sip.voice.x.ai;transport=tls (digest from above).")
print("Wire the webhook backend next; see the skill's step 4.")
