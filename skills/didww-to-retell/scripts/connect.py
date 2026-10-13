#!/usr/bin/env python3
"""Import a DIDWW number into Retell and bind an agent. MCP fallback.

Prefer the official Retell MCP (https://mcp.retellai.com) when connected;
this script is for sessions without it.

Usage:
  RETELL_API_KEY=... python3 scripts/connect.py \
    --number +33144556677 --didww-host fra.eu.out.didww.com \
    --didww-user USER --didww-pass PASS \
    [--agent AGENT_ID] [--transport TCP|UDP|TLS] [--nickname "Paris line"]

--didww-user and --didww-pass go together; DIDWW_TRUNK_PASS in the
environment may replace --didww-pass to keep it out of shell history.
Request shape per Retell's OpenAPI (POST /import-phone-number, flat SIP
trunk fields).
"""
import json, os, re, sys, urllib.error, urllib.request

VALUE = {"--number", "--didww-host", "--didww-user", "--didww-pass",
         "--agent", "--transport", "--nickname"}
a, opts, i = sys.argv[1:], {}, 0
while i < len(a):
    if a[i] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    if a[i] in VALUE and i + 1 < len(a) and not a[i + 1].startswith("--"):
        opts[a[i]] = a[i + 1]; i += 2
    else:
        sys.exit(f"Bad argument {a[i]!r}; usage:\n{__doc__}")

KEY = os.environ.get("RETELL_API_KEY", "")
if not KEY:
    sys.exit("Set RETELL_API_KEY (dashboard: API Keys).")
number, host = opts.get("--number", ""), opts.get("--didww-host")
if not re.fullmatch(r"\+[1-9]\d{6,14}", number) or not host:
    sys.exit("Need --number (E.164 with +) and --didww-host.\n" + __doc__)
user = opts.get("--didww-user")
password = opts.get("--didww-pass") or os.environ.get("DIDWW_TRUNK_PASS", "")
if bool(user) != bool(password):
    sys.exit("--didww-user and --didww-pass (or DIDWW_TRUNK_PASS) go together.")
transport = opts.get("--transport", "TCP").upper()
if transport not in ("TCP", "UDP", "TLS"):
    sys.exit("--transport must be TCP, UDP or TLS.")

body = {
    "phone_number": number,
    "termination_uri": host,
    "transport": transport,
    "nickname": opts.get("--nickname", "DIDWW " + number),
}
if user:
    body["sip_trunk_auth_username"] = user
    body["sip_trunk_auth_password"] = password
if opts.get("--agent"):
    body["inbound_agents"] = [{"agent_id": opts["--agent"], "weight": 1}]
    body["outbound_agents"] = [{"agent_id": opts["--agent"], "weight": 1}]

def redact(v):
    if isinstance(v, dict):
        return {k: "***" if "password" in k.lower() else redact(x) for k, x in v.items()}
    return [redact(x) for x in v] if isinstance(v, list) else v

req = urllib.request.Request(
    "https://api.retellai.com/import-phone-number", method="POST",
    data=json.dumps(body).encode(),
    headers={"Authorization": "Bearer " + KEY,
             "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"Retell API {e.code}:\n{e.read().decode()[:2000]}")

print(json.dumps(redact(out), indent=1))
print("\nDIDWW inbound trunk must point at sip.retellai.com (TCP), digest "
      "auth matching what the agent expects. Place test calls both ways.")
