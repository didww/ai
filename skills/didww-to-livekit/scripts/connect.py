#!/usr/bin/env python3
"""Connect a DIDWW number to a LiveKit agent: inbound trunk + dispatch rule,
plus an optional outbound trunk back to DIDWW, through the LiveKit SIP API.

Usage:
  LIVEKIT_URL=https://<project>.livekit.cloud LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... \\
  python3 scripts/connect.py --number +33144556677 --agent my-agent \\
      --inbound-user USER --inbound-pass PASS [--allow-ip CIDR ...] \\
      [--outbound-host fra.eu.out.didww.com --outbound-user U --outbound-pass P] \\
      [--transport tcp|tls|udp|auto] [--srtp allow|require|disable] \\
      [--room-prefix didww-]
  python3 scripts/connect.py --show     # list trunks and rules, print the SIP URI

--inbound-user/--inbound-pass: the digest pair the DIDWW inbound trunk sends.
--allow-ip: CIDR/IP allowlist. LiveKit Cloud enables allowed_addresses per
  project on request to support; digest auth needs no enablement.
--agent: must equal the agent_name the worker registers (explicit dispatch).
--transport applies to the outbound trunk and is echoed as the port hint for
  the DIDWW side; --srtp is set on both trunks (default allow).
LIVEKIT_URL accepts the wss:// project URL or the https:// API host.
"""
import base64, hashlib, hmac, json, os, sys, time, urllib.error, urllib.request

a = sys.argv[1:]
if "--help" in a or "-h" in a:
    print(__doc__); sys.exit(0)
def opt(n, d=None):
    return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
def multi(n):
    return [a[i + 1] for i, x in enumerate(a) if x == n and i + 1 < len(a)]
def g(d, *keys):  # Twirp answers camelCase; accept snake_case too
    return next((d[k] for k in keys if k in d), None)

URL = os.environ.get("LIVEKIT_URL", "").strip().rstrip("/")
KEY = os.environ.get("LIVEKIT_API_KEY", "")
SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
if not (URL and KEY and SECRET):
    sys.exit("Set LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET "
             "(LiveKit Cloud: project Settings, Keys; the secret is shown once).")
for p in ("wss://", "ws://"):
    if URL.startswith(p):
        URL = "https://" + URL[len(p):]
if not URL.startswith("http"):
    URL = "https://" + URL
HOST = URL.split("://", 1)[1].split("/", 1)[0]
SIP_URI = ("sip:" + HOST.split(".")[0] + ".sip.livekit.cloud"
           if HOST.endswith(".livekit.cloud") else "sip:<your SIP service host>")
REGIONS = "eu|us|uk|india|japan|aus|canada|sa"

def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def token():
    now = int(time.time())
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(json.dumps({"iss": KEY, "nbf": now - 10, "exp": now + 600,
                           "video": {}, "sip": {"admin": True}},
                          separators=(",", ":")).encode())
    sig = b64(hmac.new(SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"
def call(method, body):
    req = urllib.request.Request(
        f"{URL}/twirp/livekit.SIP/{method}", method="POST",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token(),
                 "Content-Type": "application/json",
                 "User-Agent": "didww-to-livekit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"LiveKit API {e.code} on {method}:\n{e.read().decode()[:2000]}")
    except urllib.error.URLError as e:
        sys.exit(f"LiveKit API unreachable at {URL}: {e.reason}")

if "--show" in a:
    print(f"SIP URI for the DIDWW inbound trunk: {SIP_URI}")
    print(f"  region-pinned form: sip:<subdomain>.<{REGIONS}>.sip.livekit.cloud")
    print("Inbound trunks:")
    for t in call("ListSIPInboundTrunk", {}).get("items", []):
        print(f"  {g(t, 'sipTrunkId', 'sip_trunk_id')}  {t.get('name', '')}  "
              f"numbers={t.get('numbers', [])}  "
              f"digest={'yes' if g(t, 'authUsername', 'auth_username') else 'NO'}  "
              f"allowed_addresses={g(t, 'allowedAddresses', 'allowed_addresses') or []}")
    print("Dispatch rules:")
    for r in call("ListSIPDispatchRule", {}).get("items", []):
        agents = [g(x, "agentName", "agent_name")
                  for x in (g(r, "roomConfig", "room_config") or {}).get("agents", [])]
        print(f"  {g(r, 'sipDispatchRuleId', 'sip_dispatch_rule_id')}  {r.get('name', '')}  "
              f"trunks={g(r, 'trunkIds', 'trunk_ids') or ['*']}  agents={agents}")
    print("Outbound trunks:")
    for t in call("ListSIPOutboundTrunk", {}).get("items", []):
        print(f"  {g(t, 'sipTrunkId', 'sip_trunk_id')}  {t.get('name', '')}  "
              f"{t.get('address')}  numbers={t.get('numbers', [])}")
    sys.exit(0)

number, agent = opt("--number"), opt("--agent")
if not number or not agent:
    sys.exit(__doc__)
if not number.startswith("+"):
    sys.exit("--number must be E.164 with the + prefix (LiveKit matches it exactly), e.g. +33144556677.")
TRANSPORTS = {"auto": "SIP_TRANSPORT_AUTO", "udp": "SIP_TRANSPORT_UDP",
              "tcp": "SIP_TRANSPORT_TCP", "tls": "SIP_TRANSPORT_TLS"}
SRTP = {"disable": "SIP_MEDIA_ENCRYPT_DISABLE", "allow": "SIP_MEDIA_ENCRYPT_ALLOW",
        "require": "SIP_MEDIA_ENCRYPT_REQUIRE"}
transport = opt("--transport", "tcp").lower()
srtp = opt("--srtp", "allow").lower()
if transport not in TRANSPORTS:
    sys.exit(f"--transport must be one of {', '.join(TRANSPORTS)}.")
if srtp not in SRTP:
    sys.exit(f"--srtp must be one of {', '.join(SRTP)}.")
user, pw, ips = opt("--inbound-user"), opt("--inbound-pass"), multi("--allow-ip")
if (user and not pw) or (pw and not user):
    sys.exit("--inbound-user and --inbound-pass go together.")
if not user and not ips:
    sys.exit("Give --inbound-user/--inbound-pass (digest, works everywhere) and/or "
             "--allow-ip; a trunk with neither answers INVITEs from anyone who knows the number.")
if opt("--outbound-host") and not (opt("--outbound-user") and opt("--outbound-pass")):
    sys.exit("--outbound-host needs --outbound-user and --outbound-pass "
             "(the credentials of the DIDWW outbound trunk).")
if ips and not user:
    print("NOTE: allowed_addresses on LiveKit Cloud must be enabled for the project by "
          "LiveKit support; until then the API may reject or ignore it. Digest auth "
          "needs no enablement.")

trunk = {"name": f"DIDWW {number}", "numbers": [number], "media_encryption": SRTP[srtp]}
if user:
    trunk.update({"auth_username": user, "auth_password": pw})
if ips:
    trunk["allowed_addresses"] = ips
tid = g(call("CreateSIPInboundTrunk", {"trunk": trunk}), "sipTrunkId", "sip_trunk_id")
rule = {"name": f"DIDWW {number}", "trunk_ids": [tid],
        "rule": {"dispatch_rule_individual": {"room_prefix": opt("--room-prefix", "didww-")}},
        "room_config": {"agents": [{"agent_name": agent}]}}
rid = g(call("CreateSIPDispatchRule", {"dispatch_rule": rule}),
        "sipDispatchRuleId", "sip_dispatch_rule_id")
print(f"inbound trunk:  {tid}  ({number}; digest={'yes' if user else 'no'}; "
      f"allowlist={ips or 'none'}; srtp={srtp})")
print(f"dispatch rule:  {rid}  -> agent '{agent}' (explicit dispatch: the worker must "
      f"register exactly this agent_name)")
if opt("--outbound-host"):
    out = {"name": f"DIDWW {number} out", "address": opt("--outbound-host"),
           "transport": TRANSPORTS[transport], "numbers": [number],
           "auth_username": opt("--outbound-user"), "auth_password": opt("--outbound-pass"),
           "media_encryption": SRTP[srtp]}
    oid = g(call("CreateSIPOutboundTrunk", {"trunk": out}), "sipTrunkId", "sip_trunk_id")
    print(f"outbound trunk: {oid}  -> {out['address']} ({transport}); the worker dials "
          f"through it with CreateSIPParticipant")
port = "5061 TLS" if transport == "tls" else f"5060 {transport.upper()}"
print(f"\nDIDWW inbound trunk: host {SIP_URI}, port {port}, SRTP {srtp}, "
      f"digest user {user or '-'} (same pair as above).")
print(f"Region pinning: sip:<subdomain>.<{REGIONS}>.sip.livekit.cloud")
print("Trunks are not deduplicated: run --show before re-running this.")
