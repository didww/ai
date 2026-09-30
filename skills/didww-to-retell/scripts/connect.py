#!/usr/bin/env python3
"""Import a DIDWW number into Retell and bind an agent. MCP fallback.

Prefer the official Retell MCP (https://mcp.retellai.com) when connected;
this script is for sessions without it.

Usage:
  RETELL_API_KEY=... python3 scripts/connect.py \
    --number +33144556677 --didww-host fra.eu.out.didww.com \
    --didww-user USER --didww-pass PASS \
    [--agent AGENT_ID] [--transport TCP] [--nickname "Paris line"]
"""
import json, os, sys, urllib.request

KEY = os.environ.get("RETELL_API_KEY", "")
if not KEY:
    sys.exit("Set RETELL_API_KEY (dashboard: API Keys).")
a = sys.argv[1:]
def opt(n, d=None):
    return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
if not opt("--number") or not opt("--didww-host"):
    sys.exit(__doc__)

body = {
    "phone_number": opt("--number"),
    "termination_uri": opt("--didww-host"),
    "transport": opt("--transport", "TCP"),
    "nickname": opt("--nickname", "DIDWW " + opt("--number")),
}
if opt("--didww-user"):
    body["sip_trunk_auth_username"] = opt("--didww-user")
    body["sip_trunk_auth_password"] = opt("--didww-pass")
if opt("--agent"):
    body["inbound_agents"] = [{"agent_id": opt("--agent"), "weight": 1}]
    body["outbound_agents"] = [{"agent_id": opt("--agent"), "weight": 1}]

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

print(json.dumps(out, indent=1)[:1200])
print("\nDIDWW inbound trunk must point at sip.retellai.com (TCP), digest "
      "auth matching what the agent expects. Place test calls both ways.")
