#!/usr/bin/env python3
"""Import a DIDWW number into ElevenLabs over SIP and assign an agent.

Usage:
  ELEVENLABS_API_KEY=... python3 scripts/import_number.py \
    --number 33144556677 [--label "Paris line"] \
    --inbound-user USER --inbound-pass PASS \
    [--outbound-host fra.eu.out.didww.com \
     --outbound-user OUSER --outbound-pass OPASS [--transport tcp]] \
    [--media-encryption disabled] [--agent AGENT_ID]

  ELEVENLABS_API_KEY=... ELEVENLABS_INBOUND_PASS=... \
  python3 scripts/import_number.py --update PHONE_NUMBER_ID \
    --inbound-user USER [--media-encryption disabled] [--outbound-* ...]

--update changes a number that is already imported (PATCH
/v1/convai/phone-numbers/{id}) instead of importing it: it replaces the
inbound credentials, which is how an inbound-only line is switched to the
outbound trunk's pair for transfers. It sends the inbound config whole,
so give --media-encryption matching the trunk again; --number is not used.
(The MCP's agents_update_phone_number can do the same, but the password
would then pass through the chat.)

--number is E.164 with or without the +; it is imported WITHOUT the +,
because the DIDWW inbound trunk sends the called number as {DID}, which
has no plus (DIDWW's ElevenLabs guide, Step 2: Enter Your Phone Number).

The three --outbound-* values go together, or are all left out to import
the number for inbound calls only (add outbound later in the dashboard
or with agents_update_phone_number once the DIDWW outbound trunk
exists). Passwords may come from the environment instead of the command
line: ELEVENLABS_INBOUND_PASS and DIDWW_TRUNK_PASS (outbound).
With an outbound trunk or live-agent transfers, the inbound pair is the
DIDWW OUTBOUND trunk's username and password, the same pair the DIDWW
inbound trunk's Authorization uses: DIDWW authenticates the REFER with it.
--transport (outbound) is one of auto, udp, tcp, tls (lowercase enum).
--media-encryption (both directions) is one of disabled, allowed,
required; match the DIDWW trunks: disabled when their SRTP mode is
Disable (the DIDWW default), required for SRTP. Default: allowed.

This is the one step ElevenLabs' hosted MCP cannot do (no import tool).
Stdlib only; sends nothing anywhere except api.elevenlabs.io. Request
shape per ElevenLabs' OpenAPI (CreateSIPTrunkPhoneNumberRequestV2). On an
API error the response body prints verbatim.
"""
import json, os, re, sys, urllib.error, urllib.request

VALUE = {"--number", "--label", "--inbound-user", "--inbound-pass",
         "--outbound-host", "--outbound-user", "--outbound-pass",
         "--transport", "--media-encryption", "--agent", "--update"}
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

update = opts.get("--update")
number = opts.get("--number", "")
in_user = opts.get("--inbound-user")
in_pass = opts.get("--inbound-pass") or os.environ.get("ELEVENLABS_INBOUND_PASS", "")
if update is not None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", update):
        sys.exit("--update takes the phone_number_id the import printed (letters, digits, _ and -).")
    if number:
        sys.exit("--update changes an imported number; leave out --number.")
bad_number = update is None and not re.fullmatch(r"\+?[1-9]\d{6,14}", number)
if bad_number or not in_user or not in_pass:
    sys.exit("Need --number (E.164, with or without +) or --update, and the inbound "
             "digest pair (--inbound-user, --inbound-pass or ELEVENLABS_INBOUND_PASS).\n" + __doc__)
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
ENCRYPTIONS = ("disabled", "allowed", "required")
encryption = opts.get("--media-encryption", "allowed").lower()
if encryption not in ENCRYPTIONS:
    sys.exit(f"--media-encryption must be one of {', '.join(ENCRYPTIONS)}.")
# DIDWW delivers the called number as {DID}: E.164 digits, no plus.
number = number.lstrip("+")

payload = {
    "inbound_trunk_config": {
        # Digest auth for calls DIDWW sends in: the API takes a
        # credentials object, not auth_username/auth_password.
        "credentials": {"username": in_user, "password": in_pass},
        "media_encryption": encryption,
    },
}
if update is None:
    payload.update(provider="sip_trunk", phone_number=number,
                   label=opts.get("--label", "DIDWW +" + number))
elif opts.get("--label"):
    payload["label"] = opts["--label"]
if all(given):
    payload["outbound_trunk_config"] = {
        "address": out_host,
        "transport": transport,
        "credentials": {"username": out_user, "password": out_pass},
        "media_encryption": encryption,
    }
if opts.get("--agent"):
    payload["agent_id"] = opts["--agent"]

url = "https://api.elevenlabs.io/v1/convai/phone-numbers"
req = urllib.request.Request(
    url + (f"/{update}" if update else ""), method="PATCH" if update else "POST",
    data=json.dumps(payload).encode(),
    headers={"xi-api-key": KEY, "Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"ElevenLabs API {e.code}:\n{e.read().decode()[:2000]}")
pid = out.get("phone_number_id") or out.get("id")
if update:
    print(f"Updated phone_number_id={update}: inbound credentials now user {in_user}.")
    print("The DIDWW inbound trunk's Authorization must carry the same pair.")
    sys.exit(0)
print(f"Imported {number} (no plus, as DIDWW sends it): phone_number_id={pid}")
if opts.get("--agent"):
    print(f"Assigned agent {opts['--agent']}.")
else:
    print("Assign the agent via the ElevenLabs MCP (agents_update_phone_number) or dashboard.")
if not all(given):
    print("Inbound only: add the outbound trunk once the DIDWW outbound trunk exists.")
print("Now place the test calls" + (", both directions." if all(given) else "."))
