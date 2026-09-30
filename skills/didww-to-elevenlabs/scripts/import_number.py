#!/usr/bin/env python3
"""Import a DIDWW number into ElevenLabs over SIP and assign an agent.

Usage:
  ELEVENLABS_API_KEY=... python3 scripts/import_number.py \
    --number +33144556677 --label "Paris line" \
    --inbound-user USER --inbound-pass PASS \
    --outbound-host fra.eu.out.didww.com \
    --outbound-user OUSER --outbound-pass OPASS \
    [--transport tcp] [--agent AGENT_ID]

--transport is one of auto, udp, tcp, tls (ElevenLabs' enum is lowercase).

This is the one step ElevenLabs' hosted MCP cannot do (no import tool).
Stdlib only; sends nothing anywhere except api.elevenlabs.io. On an API
shape error the response body prints verbatim: check the phone-numbers
API reference and adjust.
"""
import json, os, sys, urllib.request

KEY = os.environ.get("ELEVENLABS_API_KEY", "")
if not KEY:
    sys.exit("Set ELEVENLABS_API_KEY (dashboard: API Keys).")

a = sys.argv[1:]
def opt(n, d=None):
    return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
need = ["--number", "--inbound-user", "--inbound-pass",
        "--outbound-host", "--outbound-user", "--outbound-pass"]
if any(opt(n) is None for n in need):
    sys.exit(__doc__)

TRANSPORTS = ("auto", "udp", "tcp", "tls")
transport = opt("--transport", "tcp").lower()
if transport not in TRANSPORTS:
    sys.exit(f"--transport must be one of {', '.join(TRANSPORTS)}.")

payload = {
    "provider_type": "sip_trunk",
    "phone_number": opt("--number"),
    "label": opt("--label", "DIDWW " + opt("--number")),
    "inbound_trunk_config": {
        # Digest auth for calls DIDWW sends in: the API takes a
        # credentials object, not auth_username/auth_password.
        "credentials": {"username": opt("--inbound-user"),
                        "password": opt("--inbound-pass")},
        "media_encryption": "allowed",
    },
    "outbound_trunk_config": {
        "address": opt("--outbound-host"),
        "transport": transport,
        "credentials": {"username": opt("--outbound-user"),
                        "password": opt("--outbound-pass")},
        "media_encryption": "allowed",
    },
}

def call(method, path, body=None):
    req = urllib.request.Request(
        "https://api.elevenlabs.io" + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"xi-api-key": KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs API {e.code} on {path}:\n{e.read().decode()[:2000]}")

out = call("POST", "/v1/convai/phone-numbers", payload)
pid = out.get("phone_number_id") or out.get("id")
print(f"Imported: phone_number_id={pid}")
agent = opt("--agent")
if agent and pid:
    call("PATCH", f"/v1/convai/phone-numbers/{pid}", {"agent_id": agent})
    print(f"Assigned agent {agent}.")
else:
    print("Assign the agent via the ElevenLabs MCP (agents_update_phone_number) or dashboard.")
print("Now place the test calls, both directions.")
