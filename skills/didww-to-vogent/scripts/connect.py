#!/usr/bin/env python3
"""Import a DIDWW number into Vogent via sip_import and link the agent.

Usage:
  VOGENT_API_KEY=... python3 scripts/connect.py \
    --number +33144556677 --didww-host fra.eu.out.didww.com \
    --didww-user USER --didww-pass PASS [--agent AGENT_ID]
  VOGENT_API_KEY=... python3 scripts/connect.py --phone-id ID --agent AGENT_ID

The four import values are required (Vogent's
CreatePhoneNumberSIPImportInput marks username and password required,
non-null): the DIDWW outbound trunk's host and credentials, so that
trunk must exist even for an inbound-only line. DIDWW_TRUNK_PASS in the
environment may replace --didww-pass to keep it out of shell history.
--agent links the agent with PUT /api/phone_numbers/{id} {"agentId"}
right after the import; --phone-id with --agent links a number imported
earlier, without importing. GET /api/agents lists agent ids. Steps per
DIDWW's Vogent guide (doc.didww.com/integrations/vogent/), section 3.

VOGENT_API_KEY is the secret key (app.vogent.ai, API, Keys, New Key,
shown once), not the UUID-shaped key ID, which gets "unauthorized".
"""
import json, os, re, sys, urllib.error, urllib.request

VALUE = {"--number", "--didww-host", "--didww-user", "--didww-pass",
         "--agent", "--phone-id"}
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
    sys.exit("Set VOGENT_API_KEY to the secret key (app.vogent.ai: API, Keys, New Key).")
API = "https://api.vogent.ai/api/phone_numbers"
HEADERS = {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
agent, phone_id = opts.get("--agent"), opts.get("--phone-id")

def call(url, method, body):
    req = urllib.request.Request(url, method=method,
                                 data=json.dumps(body).encode(), headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def bind(pid):
    """Link the number to the agent; the agent's Numbers tab, Link Number does the same."""
    try:
        call(f"{API}/{pid}", "PUT", {"agentId": agent})
    except urllib.error.HTTPError as e:
        sys.exit(f"Vogent API {e.code} linking phone number {pid} to agent {agent}:\n{e.read().decode()[:2000]}")
    print(f"Phone number {pid} linked to agent {agent}.")

if phone_id is not None:
    if not agent or set(opts) != {"--phone-id", "--agent"}:
        sys.exit("--phone-id links an imported number: give it with --agent only.\n" + __doc__)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", phone_id):
        sys.exit("--phone-id takes the id the import returned (letters, digits, _ and -).")
    bind(phone_id)
    print("Set an opening line (Inbound calls Only) or the agent waits for the caller; then call the number.")
    sys.exit(0)

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

try:
    out = call(API, "POST", body)
except urllib.error.HTTPError as e:
    sys.exit(f"Vogent API {e.code}:\n{e.read().decode()[:2000]}")
print(json.dumps(redact(out), indent=1))
pid = str(out.get("id") or "")
print("\nDIDWW inbound trunk: host sip.vogent.ai, UDP 5060, User Part of R-URI {DID} "
      "(or +{DID}); Authorization = this outbound trunk's username and password.")
if agent and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", pid):
    bind(pid)
elif agent:
    sys.exit(f"Imported, but the response has no usable id ({pid!r}); link the number "
             "in the dashboard (agent, Numbers, Link Number).")
else:
    print(f"Next: link the agent with --phone-id {pid or '<id>'} --agent <agent id>, "
          "or in the dashboard (agent, Numbers, Link Number).")
print("Set an opening line (Inbound calls Only) or the agent waits for the caller; then call the number.")
