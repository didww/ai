#!/usr/bin/env python3
"""Import a DIDWW number into Vogent via sip_import.

Usage:
  VOGENT_API_KEY=... python3 scripts/connect.py \
    --number +33144556677 --didww-host fra.eu.out.didww.com \
    --didww-user USER --didww-pass PASS

All four values are required (Vogent's CreatePhoneNumberSIPImportInput
marks username and password required, non-null). DIDWW_TRUNK_PASS in the
environment may replace --didww-pass to keep it out of shell history.
"""
import json, os, re, sys, urllib.error, urllib.request

VALUE = {"--number", "--didww-host", "--didww-user", "--didww-pass"}
a, opts, i = sys.argv[1:], {}, 0
while i < len(a):
    if a[i] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    if a[i] in VALUE and i + 1 < len(a) and not a[i + 1].startswith("--"):
        opts[a[i]] = a[i + 1]; i += 2
    else:
        sys.exit(f"Bad argument {a[i]!r}; usage:\n{__doc__}")

KEY = os.environ.get("VOGENT_API_KEY", "")
if not KEY:
    sys.exit("Set VOGENT_API_KEY (app.vogent.ai: API Keys).")
number = opts.get("--number", "")
password = opts.get("--didww-pass") or os.environ.get("DIDWW_TRUNK_PASS", "")
if (not re.fullmatch(r"\+[1-9]\d{6,14}", number) or not opts.get("--didww-host")
        or not opts.get("--didww-user") or not password):
    sys.exit("Need --number (E.164 with +), --didww-host, --didww-user and "
             "--didww-pass (or DIDWW_TRUNK_PASS).\n" + __doc__)

body = {"type": "sip_import", "sipImport": {
    "phoneNumber": number,
    "terminationUri": opts["--didww-host"],
    "username": opts["--didww-user"],
    "password": password,
}}

def redact(v):
    if isinstance(v, dict):
        return {k: "***" if "password" in k.lower() else redact(x) for k, x in v.items()}
    return [redact(x) for x in v] if isinstance(v, list) else v

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
print(json.dumps(redact(out), indent=1))
print("\nDIDWW inbound trunk host: sip.vogent.ai (digest auth).")
print("MANUAL STEP: bind the agent in the dashboard "
      "(agent, Numbers tab, attach this number), then test both directions.")
