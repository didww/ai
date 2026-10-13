#!/usr/bin/env python3
"""Register a DIDWW number with xAI Grok voice SIP.

Usage:
  XAI_API_KEY=... python3 scripts/register_number.py \
    --number +33144556677 --webhook https://your.host/xai \
    [--sip-user USER --sip-pass PASS] [--allow-ip 1.2.3.4 ...] [--out FILE]

Digest credentials are preferred; the password is never returned after
creation, so configure the DIDWW trunk with it immediately (pass it as
XAI_SIP_PASS in the environment to keep it out of shell history and the
process list). The response carries the webhook signing secret exactly
once: the full response is written to --out (default
xai-<number>.json, mode 0600, never overwritten) and the screen shows a
redacted copy. Both flag groups may be combined (digest plus an IP
allowlist).
"""
import json, os, sys, urllib.error, urllib.request

KEY = os.environ.get("XAI_API_KEY", "")
if not KEY:
    sys.exit("Set XAI_API_KEY (console.x.ai).")
a = sys.argv[1:]
def opt(n, d=None):
    return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
if not opt("--number") or not opt("--webhook"):
    sys.exit(__doc__)
if not opt("--webhook").startswith("https://"):
    sys.exit("--webhook must be an https:// URL (xAI signs, but does not "
             "encrypt, what it sends there).")
OUT = opt("--out") or f"xai-{opt('--number').lstrip('+')}.json"
if os.path.exists(OUT):
    sys.exit(f"{OUT} exists; pass --out with a new file name (it will hold "
             "the one-time webhook secret).")
SIP_PASS = opt("--sip-pass") or os.environ.get("XAI_SIP_PASS", "")

def redact(v):
    if isinstance(v, dict):
        return {k: "***" if any(w in k.lower() for w in ("secret", "password", "token"))
                else redact(x) for k, x in v.items()}
    if isinstance(v, list):
        return [redact(x) for x in v]
    return v

sip_auth = {}
if opt("--sip-user"):
    if not SIP_PASS:
        sys.exit("--sip-user needs --sip-pass or XAI_SIP_PASS.")
    sip_auth.update({"auth_username": opt("--sip-user"),
                     "auth_password": SIP_PASS})
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
        resp = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"xAI API {e.code}:\n{e.read().decode()[:2000]}")
fd = os.open(OUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(resp, f, indent=1)
print(json.dumps(redact(resp), indent=1))
print(f"\nFull response, including the webhook signing secret, saved to {OUT} "
      "(mode 0600). xAI returns that secret only once: move it into the "
      "backend's secret store, then delete the file. The SIP password is "
      "never returned at all.")
print("DIDWW inbound trunk destination: "
      f"sip:{opt('--number')}@sip.voice.x.ai;transport=tls (digest from above).")
print("Wire the webhook backend next; see the skill's step 4.")
