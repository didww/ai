#!/usr/bin/env python3
"""Connect a DIDWW number to a LiveKit agent: inbound trunk + dispatch rule,
plus an optional outbound trunk back to DIDWW, through the LiveKit SIP API.

Usage:
  LIVEKIT_URL=https://<project>.livekit.cloud LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... \\
  python3 scripts/connect.py --number +33144556677 --agent my-agent \\
      --inbound-user USER --inbound-pass PASS [--allow-ip CIDR ...] \\
      [--outbound-host fra.eu.out.didww.com --outbound-user U --outbound-pass P] \\
      [--transport tls|tcp|udp|auto] [--srtp require|disable|allow] \\
      [--room-prefix didww-]
  python3 scripts/connect.py --outbound-only --number +33144556677 \\
      --outbound-host fra.eu.out.didww.com --outbound-user U --outbound-pass P
  python3 scripts/connect.py --show     # list trunks and rules, print the SIP URI

--outbound-only: add just the outbound trunk to a project that already has the
  inbound trunk and dispatch rule (no --agent or inbound flags needed). The
  DIDWW outbound trunk is created in the DIDWW panel first, since the DIDWW
  MCP has no outbound trunk tools; its generated credentials go here.

--sip-uri (or LIVEKIT_SIP_URI): the SIP URI from the LiveKit Cloud Project
  settings, e.g. sip:vjnxecm0tjk.sip.livekit.cloud. Its subdomain differs from
  the project URL's, so it cannot be derived; it is only echoed back for the
  DIDWW trunk, and never sent to LiveKit.

--inbound-user/--inbound-pass: the digest pair the DIDWW inbound trunk sends.
--allow-ip: CIDR/IP allowlist. LiveKit Cloud enables allowed_addresses per
  project on request to support; digest auth needs no enablement.
--agent: must equal the agent_name the worker registers (explicit dispatch).
Secure by default: --transport tls and --srtp require, so signaling uses TLS
  and audio uses SRTP. The DIDWW trunks MUST be set to match (inbound trunk:
  Transport TLS, Port 5061, SRTP Mode SRTP SDES; outbound trunk: SRTP SDES in
  its media settings), otherwise calls fail: inbound "400 Bad Request",
  outbound "500 No suitable media". For plain trunks pass
  --transport tcp --srtp disable and leave SRTP Mode Disabled on DIDWW.
--transport applies to the outbound trunk and is echoed as the port hint for
  the DIDWW side. --srtp is set on both trunks as media.encryption. On an
  outbound trunk allow and require both offer encrypted media only.
Both trunks are limited to PCMA and PCMU, the only codecs DIDWW and LiveKit
  SIP share.
LIVEKIT_URL accepts the wss:// project URL or the https:// API host (plain
  ws:// or http:// only for localhost).
LIVEKIT_INBOUND_PASS and DIDWW_TRUNK_PASS in the environment may replace
  --inbound-pass and --outbound-pass, keeping them out of shell history.
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
             "(LiveKit Cloud: project Settings, API keys; the secret is shown once).")
if URL.startswith("wss://"):
    URL = "https://" + URL[len("wss://"):]
elif URL.startswith("ws://"):
    URL = "http://" + URL[len("ws://"):]
elif not URL.startswith(("https://", "http://")):
    URL = "https://" + URL
HOST = URL.split("://", 1)[1].split("/", 1)[0]
_hostname = HOST.rsplit(":", 1)[0].strip("[]") if HOST.count(":") <= 1 or HOST.startswith("[") else HOST
if URL.startswith("http://") and _hostname not in ("localhost", "127.0.0.1", "::1"):
    sys.exit("LIVEKIT_URL must be https:// or wss:// (the signed API token travels "
             "with every request); plain http/ws is accepted only for localhost.")
# The SIP URI subdomain is NOT the project URL subdomain (e.g. project
# my-project-ab12cd34, SIP URI sip:vjnxecm0tjk.sip.livekit.cloud), so it is
# never derived: it is copied from Project settings.
SIP_URI = (opt("--sip-uri") or os.environ.get("LIVEKIT_SIP_URI", "")).strip()
if SIP_URI:
    SIP_URI = SIP_URI.split(";", 1)[0]
    SIP_URI = SIP_URI[4:] if SIP_URI.startswith("sip:") else SIP_URI
    SIP_HOST = SIP_URI
    SIP_URI = "sip:" + SIP_HOST
else:
    SIP_HOST = "<SIP URI host from Project settings>"
    SIP_URI = "sip:" + SIP_HOST
SIP_LABEL = SIP_HOST.split(".")[0] if not SIP_HOST.startswith("<") else "<sip-subdomain>"
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
    print(f"  region-pinned form: sip:{SIP_LABEL}.<{REGIONS}>.sip.livekit.cloud")
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
ONLY_OUT = "--outbound-only" in a
if not number or (not agent and not ONLY_OUT):
    sys.exit(__doc__)
if ONLY_OUT and not opt("--outbound-host"):
    sys.exit("--outbound-only needs --outbound-host, --outbound-user and --outbound-pass.")
if not number.startswith("+"):
    sys.exit("--number must be E.164 with the + prefix (LiveKit matches it exactly), e.g. +33144556677.")
TRANSPORTS = {"auto": "SIP_TRANSPORT_AUTO", "udp": "SIP_TRANSPORT_UDP",
              "tcp": "SIP_TRANSPORT_TCP", "tls": "SIP_TRANSPORT_TLS"}
SRTP = {"disable": "SIP_MEDIA_ENCRYPT_DISABLE", "allow": "SIP_MEDIA_ENCRYPT_ALLOW",
        "require": "SIP_MEDIA_ENCRYPT_REQUIRE"}
transport = opt("--transport", "tls").lower()
srtp = opt("--srtp", "require").lower()
if transport not in TRANSPORTS:
    sys.exit(f"--transport must be one of {', '.join(TRANSPORTS)}.")
if srtp not in SRTP:
    sys.exit(f"--srtp must be one of {', '.join(SRTP)}.")
user, ips = opt("--inbound-user"), multi("--allow-ip")
pw = opt("--inbound-pass") or os.environ.get("LIVEKIT_INBOUND_PASS", "")
out_pw = opt("--outbound-pass") or os.environ.get("DIDWW_TRUNK_PASS", "")
if (user and not pw) or (pw and not user):
    sys.exit("--inbound-user and --inbound-pass go together.")
if not ONLY_OUT and not user and not ips:
    sys.exit("Give --inbound-user/--inbound-pass (digest, works everywhere) and/or "
             "--allow-ip; a trunk with neither answers INVITEs from anyone who knows the number.")
if opt("--outbound-host") and not (opt("--outbound-user") and out_pw):
    sys.exit("--outbound-host needs --outbound-user and --outbound-pass "
             "(the credentials of the DIDWW outbound trunk).")
if ips and not user and not ONLY_OUT:
    print("NOTE: allowed_addresses on LiveKit Cloud must be enabled for the project by "
          "LiveKit support; until then the API may reject or ignore it. Digest auth "
          "needs no enablement.")

def media():
    # G.711 is the whole overlap between DIDWW and LiveKit SIP (PCMU, PCMA, G.722).
    m = {"only_listed_codecs": True,
         "codecs": [{"name": "PCMA", "rate": 8000}, {"name": "PCMU", "rate": 8000}]}
    if srtp != "disable":
        m["encryption"] = SRTP[srtp]
    return m

if not ONLY_OUT:
    trunk = {"name": f"DIDWW {number}", "numbers": [number], "media": media()}
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
           "auth_username": opt("--outbound-user"), "auth_password": out_pw,
           "media": media()}
    oid = g(call("CreateSIPOutboundTrunk", {"trunk": out}), "sipTrunkId", "sip_trunk_id")
    print(f"outbound trunk: {oid}  -> {out['address']} ({transport}); the worker dials "
          f"through it with CreateSIPParticipant")
srtp_mode = "Disabled" if srtp == "disable" else "SRTP SDES"
if not ONLY_OUT:
    port = "5061, Transport TLS" if transport == "tls" else f"5060, Transport {transport.upper()}"
    print(f"\nDIDWW inbound trunk (Voice, Inbound Trunks, Create New, SIP Trunk):")
    print(f"  Type Static Endpoint, User Part of R-URI {{DID}}, Host {SIP_HOST}")
    print(f"    (the SIP URI {SIP_URI} without the sip: prefix), Port {port}")
    print(f"  Authorization: {'Auth User ' + user + ', same password as above' if user else 'off'}")
    print(f"  Media & DTMF: Codecs PCMA and PCMU only, SRTP Mode {srtp_mode}, DTMF RFC 2833")
if opt("--outbound-host"):
    print("DIDWW outbound trunk (created in the DIDWW panel: Voice, Outbound Trunks, Create New):")
    print("  Credentials & IP-Based needs an Allowed SIP IP. LiveKit Cloud")
    print("  (Canada, EU, India, Japan, US): 143.223.88.0/21 161.115.160.0/19 153.57.128.0/18;")
    print("  self-hosted: the SIP service's public IP."
          + ("" if srtp == "disable" else " Enable SRTP SDES in its media settings."))
if srtp != "disable":
    print("NOTE for the DIDWW trunks: these LiveKit trunks use SRTP, so set the DIDWW inbound")
    print("  trunk to SRTP Mode SRTP SDES" + (", Transport TLS, Port 5061" if transport == "tls" else "")
          + " and enable SRTP SDES on the DIDWW outbound")
    print("  trunk. A DIDWW trunk left without SRTP fails: inbound 400 Bad Request, outbound")
    print("  500 No suitable media. For plain trunks re-create these with")
    print("  --transport tcp --srtp disable.")
    if transport != "tls":
        print("NOTE: SRTP was only verified together with --transport tls (DIDWW port 5061).")
else:
    print("NOTE: these trunks are NOT encrypted (no SRTP"
          + ("" if transport == "tls" else ", no TLS") + "). Keep SRTP Mode Disabled on the")
    print("  DIDWW trunks. The secure default is --transport tls --srtp require.")
if not ONLY_OUT:
    print(f"Region pinning: sip:{SIP_LABEL}.<{REGIONS}>.sip.livekit.cloud")
print("Trunks are not deduplicated: run --show before re-running this.")
