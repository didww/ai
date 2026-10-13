#!/usr/bin/env python3
"""Create the Vapi side of a DIDWW connection, per Vapi's and DIDWW's guides.

Usage:
  VAPI_API_KEY=... python3 scripts/connect.py --number +33144556677 \
    [--didww-host fra.eu.out.didww.com --didww-user USER --didww-pass PASS] \
    [--assistant ASSISTANT_ID] [--eu] [--transport udp|tcp|tls]
  VAPI_API_KEY=... python3 scripts/connect.py --rotate CREDENTIAL_ID \
    [--rotate CREDENTIAL_ID ...] --didww-user USER --didww-pass PASS [--eu]

Creates:
  1. "DIDWW Outbound Trunk" credential (only with the --didww-* flags):
     gateway = the DIDWW outbound endpoint, outbound only, digest auth.
  2. "DIDWW Inbound Trunk" credential: one inbound-only gateway per DIDWW
     signaling IP (doc.didww.com, General SIP Information), plus the
     DIDWW outbound credentials for authenticated SIP REFER transfers.
  3. The phone number (byo-phone-number, E.164 with +) on credential 2,
     bound to --assistant when given.
Then prints the DIDWW-side settings. --rotate replaces the outbound
authentication on existing credentials after the DIDWW password changes.

The three --didww-* flags go together, or not at all for an inbound-only
setup (no transfers or outbound calls until the DIDWW outbound trunk
exists). DIDWW_TRUNK_PASS in the environment may replace --didww-pass so
the password stays out of shell history and the process list. --eu
targets an EU-hosted Vapi organization (api.eu.vapi.ai, sip.eu.vapi.ai).
Stdlib only; API errors print verbatim for self-correction.
"""
import json, os, re, sys, urllib.error, urllib.request

# DIDWW inbound signaling IPs (doc.didww.com/voice/inbound-trunks/technical-data/sip.html):
# New York, Frankfurt, Los Angeles, Miami, Singapore, Hong Kong, Amsterdam.
DIDWW_SIGNALING = ["46.19.209.14", "46.19.210.14", "46.19.212.14", "46.19.213.14",
                   "46.19.214.14", "46.19.215.14", "185.238.173.14"]
# Vapi SIP signaling IPs (docs.vapi.ai/advanced/sip/sip-networking).
VAPI_SIGNALING = {"us": ["44.229.228.186/32", "44.238.177.138/32"],
                  "eu": ["63.182.83.170/32"]}

VALUE = {"--number", "--didww-host", "--didww-user", "--didww-pass",
         "--assistant", "--transport", "--rotate"}
FLAGS = {"--eu", "--help", "-h"}
a, opts, rotate, i = sys.argv[1:], {}, [], 0
while i < len(a):
    if a[i] in FLAGS:
        opts[a[i]] = True; i += 1
    elif a[i] in VALUE and i + 1 < len(a) and not a[i + 1].startswith("--"):
        if a[i] == "--rotate":
            rotate.append(a[i + 1])
        else:
            opts[a[i]] = a[i + 1]
        i += 2
    else:
        sys.exit(f"Bad argument {a[i]!r}; usage:\n{__doc__}")
if opts.get("--help") or opts.get("-h"):
    print(__doc__); sys.exit(0)

KEY = os.environ.get("VAPI_API_KEY", "")
if not KEY:
    sys.exit("Set VAPI_API_KEY (dashboard: Organization Settings, API Keys).")
REGION = "eu" if opts.get("--eu") else "us"
API = "https://api.eu.vapi.ai" if REGION == "eu" else "https://api.vapi.ai"
SIP_HOST = "sip.eu.vapi.ai" if REGION == "eu" else "sip.vapi.ai"
TRANSPORT = opts.get("--transport", "udp").lower()
if TRANSPORT not in ("udp", "tcp", "tls"):
    sys.exit("--transport must be udp, tcp or tls.")
PORT = 5061 if TRANSPORT == "tls" else 5060

host, user = opts.get("--didww-host"), opts.get("--didww-user")
password = opts.get("--didww-pass") or os.environ.get("DIDWW_TRUNK_PASS", "")
auth = {"authUsername": user, "authPassword": password} if user and password else None

def call(method, path, body=None):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json",
                 # api.vapi.ai sits behind Cloudflare, which rejects
                 # Python's default User-Agent (error 1010) before auth.
                 "User-Agent": "didww-to-vapi/1.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Vapi API {e.code} on {method} {path}:\n{e.read().decode()[:2000]}")

if rotate:
    if not auth:
        sys.exit("--rotate needs --didww-user and --didww-pass (or DIDWW_TRUNK_PASS).")
    for cid in rotate:
        call("PATCH", f"/credential/{cid}",
             {"provider": "byo-sip-trunk", "outboundAuthenticationPlan": auth})
        print(f"Credential {cid}: outbound authentication updated.")
    print("Also set the DIDWW inbound trunk's auth_user/auth_password to the "
          "same pair (it authenticates Vapi's transfers).")
    sys.exit(0)

number = opts.get("--number", "")
if not re.fullmatch(r"\+[1-9]\d{6,14}", number):
    sys.exit("--number must be E.164 with the +, e.g. +33144556677.\n" + __doc__)
given = [bool(host), bool(user), bool(password)]
if any(given) and not all(given):
    sys.exit("Give all of --didww-host, --didww-user and --didww-pass (or "
             "DIDWW_TRUNK_PASS), or none of them for an inbound-only setup.")

if auth:
    out_cid = call("POST", "/credential", {
        "provider": "byo-sip-trunk", "name": "DIDWW Outbound Trunk",
        "gateways": [{"ip": host, "port": PORT, "inboundEnabled": False,
                      "outboundEnabled": True, "outboundProtocol": TRANSPORT}],
        "outboundLeadingPlusEnabled": True,
        "outboundAuthenticationPlan": auth,
    }).get("id")
    print(f"Outbound credential created: {out_cid}")

in_body = {
    "provider": "byo-sip-trunk", "name": "DIDWW Inbound Trunk",
    "gateways": [{"ip": ip, "port": PORT, "netmask": 32, "inboundEnabled": True,
                  "outboundEnabled": False} for ip in DIDWW_SIGNALING],
}
if auth:
    in_body["outboundAuthenticationPlan"] = auth  # authenticated REFER transfers
in_cid = call("POST", "/credential", in_body).get("id")
print(f"Inbound credential created: {in_cid}")

num_body = {"provider": "byo-phone-number", "name": "DIDWW " + number,
            "number": number, "numberE164CheckEnabled": True,
            "credentialId": in_cid}
if opts.get("--assistant"):
    num_body["assistantId"] = opts["--assistant"]
num = call("POST", "/phone-number", num_body)
print(f"Phone number created: {num.get('id')}")

print("\nDIDWW INBOUND TRUNK (MCP create_sip_trunk):")
print(f"  host {SIP_HOST}, port {PORT}, transport_protocol {TRANSPORT.upper()}, "
      "network_protocol_priority 'force IPv4'")
print("  max_transfers 1 (lets Vapi transfer calls with SIP REFER)")
if auth:
    print("  auth_enabled true, auth_user/auth_password = the DIDWW outbound "
          "trunk's username and password")
print(f"  then assign {number} to it.")
if auth:
    ips = VAPI_SIGNALING[REGION] + [ip + "/32" for ip in DIDWW_SIGNALING]
    print("\nDIDWW OUTBOUND TRUNK (panel) Allowed SIP IP addresses:")
    print("  " + ", ".join(ips))
    print("  (Vapi's signaling IPs for outbound calls, DIDWW's own for transfers)")
else:
    print("\nInbound only. Once the DIDWW outbound trunk exists, create the "
          f"outbound credential in Vapi and run --rotate {in_cid} with its "
          "username and password to enable transfers.")
if not opts.get("--assistant"):
    print("Bind an assistant: PATCH /phone-number/{id} with assistantId, "
          "or in the Vapi dashboard.")
