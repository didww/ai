#!/usr/bin/env python3
"""Import a DIDWW number into Vogent via sip_import.

Usage:
  VOGENT_API_KEY=... python3 scripts/connect.py \
    --number +33144556677 --didww-host fra.eu.out.didww.com \
    --didww-user USER --didww-pass PASS
"""
import json, os, sys, urllib.request

KEY = os.environ.get("VOGENT_API_KEY", "")
if not KEY:
    sys.exit("Set VOGENT_API_KEY (app.vogent.ai: API Keys).")
a = sys.argv[1:]
def opt(n, d=None):
    return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
if not opt("--number") or not opt("--didww-host"):
    sys.exit(__doc__)

body = {"type": "sip_import", "sipImport": {
    "phoneNumber": opt("--number"),
    "terminationUri": opt("--didww-host"),
    "username": opt("--didww-user"),
    "password": opt("--didww-pass"),
}}
req = urllib.request.Request(
    "https://api.vogent.ai/api/phone_numbers", method="POST",
    data=json.dumps(body).encode(),
    headers={"Authorization": "Bearer " + KEY,
             "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"Vogent API {e.code}:\n{e.read().decode()[:2000]}")
print(json.dumps(out, indent=1)[:800])
print("\nDIDWW inbound trunk host: sip.vogent.ai (digest auth).")
print("MANUAL STEP: bind the agent in the dashboard "
      "(agent, Numbers tab, attach this number), then test both directions.")
