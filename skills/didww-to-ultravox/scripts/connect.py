#!/usr/bin/env python3
"""Read and configure Ultravox account SIP settings for a DIDWW trunk.

Usage:
  ULTRAVOX_API_KEY=... python3 scripts/connect.py --show
  ULTRAVOX_API_KEY=... python3 scripts/connect.py \
    [--allow-cidr 1.2.3.0/24 ...] [--allow-agent 'agent_.*'] \
    [--fallback-url https://your.host/route] [--allow-all-agents]

--show prints the account SIP domain (read-only, needed for the DIDWW
trunk destination) and current settings. Other flags PATCH /api/sip.
Stdlib only; API errors print verbatim.
"""
import json, os, sys, urllib.request

a = sys.argv[1:]
if "--help" in a or "-h" in a:
    print(__doc__)
    sys.exit(0)
KEY = os.environ.get("ULTRAVOX_API_KEY", "")
if not KEY:
    sys.exit("Set ULTRAVOX_API_KEY (app.ultravox.ai: Settings, API Keys).")

def call(method, path, body=None):
    req = urllib.request.Request(
        "https://api.ultravox.ai" + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"X-API-Key": KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Ultravox API {e.code} on {path}:\n{e.read().decode()[:2000]}")

current = call("GET", "/api/sip")
print("Account SIP domain (point the DIDWW trunk here): "
      + str(current.get("domain")))
if "--show" in a:
    print(json.dumps(current, indent=1)[:1500])
    sys.exit(0)

patch = {}
cidrs = [a[i + 1] for i, x in enumerate(a) if x == "--allow-cidr"]
agents = [a[i + 1] for i, x in enumerate(a) if x == "--allow-agent"]
if cidrs:
    patch["allowedCidrRanges"] = cidrs
if agents:
    patch["allowedAgents"] = agents
if "--allow-all-agents" in a:
    patch["allowAllAgents"] = True
fb = a[a.index("--fallback-url") + 1] if "--fallback-url" in a else None
if fb:
    patch["fallbackHandler"] = {"url": fb}
if not patch:
    sys.exit("Nothing to change; run with --help for the flags.")
out = call("PATCH", "/api/sip", patch)
print("Updated:", json.dumps({k: out.get(k) for k in patch}, indent=1))
print("Inbound address shape: agent_{agent_id}@" + str(out.get("domain")))
print("Outbound: POST /api/calls with medium.sip.outgoing "
      "{to, from, username, password} using the DIDWW outbound trunk.")
