#!/usr/bin/env python3
"""Import a DIDWW number into ElevenLabs over SIP and assign an agent.

Usage:
  ELEVENLABS_API_KEY=... python3 scripts/import_number.py \
    --number +33144556677 [--label "Paris line"] \
    --inbound-user USER --inbound-pass PASS \
    [--outbound-host fra.eu.out.didww.com \
     --outbound-user OUSER --outbound-pass OPASS [--transport tcp]] \
    [--agent AGENT_ID]

The three --outbound-* values go together, or are all left out to import
the number for inbound calls only (add outbound later in the dashboard
or with agents_update_phone_number once the DIDWW outbound trunk
exists). Passwords may come from the environment instead of the command
line: ELEVENLABS_INBOUND_PASS and DIDWW_TRUNK_PASS (outbound).
--transport (outbound) is one of auto, udp, tcp, tls (lowercase enum).

This is the one step ElevenLabs' hosted MCP cannot do (no import tool).
Stdlib only; sends nothing anywhere except api.elevenlabs.io. Request
shape per ElevenLabs' OpenAPI (CreateSIPTrunkPhoneNumberRequestV2). On an
API error the response body prints verbatim.
"""
import json, os, re, sys, urllib.error, urllib.request

VALUE = {"--number", "--label", "--inbound-user", "--inbound-pass",
         "--outbound-host", "--outbound-user", "--outbound-pass",
         "--transport", "--agent"}
a, opts, i = sys.argv[1:], {}, 0
while i < len(a):
    if a[i] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    if a[i] in VALUE and i + 1 < len(a) and not a[i + 1].startswith("--"):
        opts[a[i]] = a[i + 1]; i += 2
    else:
        sys.exit(f"Bad argument {a[i]!r}; usage:\n{__doc__}")

KEY = os.environ.get("ELEVENLABS_API_KEY", "")
if not KEY:
    sys.exit("Set ELEVENLABS_API_KEY (dashboard: API Keys).")

number = opts.get("--number", "")
in_user = opts.get("--inbound-user")
in_pass = opts.get("--inbound-pass") or os.environ.get("ELEVENLABS_INBOUND_PASS", "")
if not re.fullmatch(r"\+[1-9]\d{6,14}", number) or not in_user or not in_pass:
    sys.exit("Need --number (E.164 with +) and the inbound digest pair "
             "(--inbound-user, --inbound-pass or ELEVENLABS_INBOUND_PASS).\n" + __doc__)
out_host, out_user = opts.get("--outbound-host"), opts.get("--outbound-user")
out_pass = opts.get("--outbound-pass") or os.environ.get("DIDWW_TRUNK_PASS", "")
given = [bool(out_host), bool(out_user), bool(out_pass)]
if any(given) and not all(given):
    sys.exit("Give all of --outbound-host, --outbound-user and --outbound-pass "
             "(or DIDWW_TRUNK_PASS), or none of them for an inbound-only import.")

TRANSPORTS = ("auto", "udp", "tcp", "tls")
transport = opts.get("--transport", "tcp").lower()
if transport not in TRANSPORTS:
    sys.exit(f"--transport must be one of {', '.join(TRANSPORTS)}.")

payload = {
    "provider": "sip_trunk",
    "phone_number": number,
    "label": opts.get("--label", "DIDWW " + number),
    "inbound_trunk_config": {
        # Digest auth for calls DIDWW sends in: the API takes a
        # credentials object, not auth_username/auth_password.
        "credentials": {"username": in_user, "password": in_pass},
        "media_encryption": "allowed",
    },
}
if all(given):
    payload["outbound_trunk_config"] = {
        "address": out_host,
        "transport": transport,
        "credentials": {"username": out_user, "password": out_pass},
        "media_encryption": "allowed",
    }
if opts.get("--agent"):
    payload["agent_id"] = opts["--agent"]

req = urllib.request.Request(
    "https://api.elevenlabs.io/v1/convai/phone-numbers", method="POST",
    data=json.dumps(payload).encode(),
    headers={"xi-api-key": KEY, "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"ElevenLabs API {e.code}:\n{e.read().decode()[:2000]}")
pid = out.get("phone_number_id") or out.get("id")
print(f"Imported: phone_number_id={pid}")
if opts.get("--agent"):
    print(f"Assigned agent {opts['--agent']}.")
else:
    print("Assign the agent via the ElevenLabs MCP (agents_update_phone_number) or dashboard.")
if not all(given):
    print("Inbound only: add the outbound trunk once the DIDWW outbound trunk exists.")
print("Now place the test calls" + (", both directions." if all(given) else "."))
