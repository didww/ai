#!/usr/bin/env python3
"""Read and configure Ultravox account SIP settings for a DIDWW trunk.

Usage:
  ULTRAVOX_API_KEY=... python3 scripts/connect.py --show [--show-secrets]
  ULTRAVOX_API_KEY=... python3 scripts/connect.py \
    [--allow-didww] [--allow-cidr 1.2.3.0/24 ...] \
    [--allow-agent AGENT_UUID[=TO_USER_REGEX] ...] [--allow-all-agents] \
    [--fallback-url https://your.host/route]

--show prints the account SIP domain (read-only, needed for the DIDWW
trunk destination) and current settings, with the fallback handler's
signing secrets redacted unless --show-secrets is given. Other flags
PATCH /api/sip:
  --allow-didww    allowedCidrRanges += DIDWW's ranges (46.19.208.0/21,
                   185.238.172.0/22: every DIDWW signaling location)
  --allow-cidr     allowedCidrRanges += one IPv4 CIDR (repeatable)
  --allow-agent    allowedAgents += {agentId, toUserPattern?} (repeatable,
                   max 20; the pattern defaults to ^agent_<agent_id>$)
  --allow-all-agents  accept agent_<id>@ for any agent on the account
  --fallback-url   fallbackHandler {url}; Ultravox generates the secret
List flags replace the account's current list. Stdlib only; API errors
print verbatim.
"""
import ipaddress, json, os, re, sys, urllib.error, urllib.request

DIDWW_CIDRS = ["46.19.208.0/21", "185.238.172.0/22"]
UUID = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
VALUE_FLAGS = {"--allow-cidr", "--allow-agent", "--fallback-url"}
BOOL_FLAGS = {"--show", "--show-secrets", "--allow-didww", "--allow-all-agents",
              "--help", "-h"}

def parse(argv):
    flags, vals, i = set(), {k: [] for k in VALUE_FLAGS}, 0
    while i < len(argv):
        x = argv[i]
        if x in BOOL_FLAGS:
            flags.add(x)
        elif x in VALUE_FLAGS:
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                sys.exit(f"{x} needs a value; run with --help.")
            vals[x].append(argv[i + 1]); i += 1
        else:
            sys.exit(f"Unknown argument {x!r}; run with --help.")
        i += 1
    return flags, vals

flags, vals = parse(sys.argv[1:])
if "--help" in flags or "-h" in flags:
    print(__doc__)
    sys.exit(0)
KEY = os.environ.get("ULTRAVOX_API_KEY", "")
if not KEY:
    sys.exit("Set ULTRAVOX_API_KEY (app.ultravox.ai: Settings, API Keys).")

def redact(cfg):
    cfg = json.loads(json.dumps(cfg))
    fh = cfg.get("fallbackHandler")
    if isinstance(fh, dict) and fh.get("secrets") and "--show-secrets" not in flags:
        fh["secrets"] = ["***"] * len(fh["secrets"])
    return cfg

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

# validate everything before touching the account
cidrs = (DIDWW_CIDRS if "--allow-didww" in flags else []) + vals["--allow-cidr"]
for c in cidrs:
    try:
        net = ipaddress.IPv4Network(c)
    except ValueError:
        sys.exit(f"--allow-cidr {c!r} is not an IPv4 CIDR (Ultravox accepts IPv4 only).")
    if net.prefixlen == 0:
        sys.exit("--allow-cidr 0.0.0.0/0 would accept INVITEs from any address; "
                 "use --allow-didww.")
agents = []
for v in vals["--allow-agent"]:
    aid, _, pattern = v.partition("=")
    if not UUID.match(aid):
        sys.exit(f"--allow-agent {v!r}: the agent ID must be the agent's UUID "
                 "(optionally followed by =TO_USER_REGEX).")
    agents.append({"agentId": aid, **({"toUserPattern": pattern} if pattern else {})})
if len(agents) > 20:
    sys.exit("Ultravox allows at most 20 --allow-agent entries; use --fallback-url for more.")
fb = vals["--fallback-url"][-1] if vals["--fallback-url"] else None
if fb and not fb.startswith("https://"):
    sys.exit("--fallback-url must be https://.")

current = call("GET", "/api/sip")
print("Account SIP domain (point the DIDWW trunk here): "
      + str(current.get("domain")))
if "--show" in flags:
    print(json.dumps(redact(current), indent=1))
    if not current.get("allowedCidrRanges"):
        print("WARNING: allowedCidrRanges is empty, so DIDWW's calls are not "
              "accepted yet; add DIDWW's ranges with --allow-didww.")
    sys.exit(0)

patch = {}
if cidrs:
    patch["allowedCidrRanges"] = list(dict.fromkeys(cidrs))
if agents:
    patch["allowedAgents"] = agents
if "--allow-all-agents" in flags:
    patch["allowAllAgents"] = True
if fb:
    patch["fallbackHandler"] = {"url": fb}
if not patch:
    sys.exit("Nothing to change; run with --help for the flags.")
out = call("PATCH", "/api/sip", patch)
print("Updated:", json.dumps({k: v for k, v in redact(out).items() if k in patch}, indent=1))
ranges = out.get("allowedCidrRanges") or []
if not ranges:
    print("WARNING: allowedCidrRanges is empty, so DIDWW's calls are not "
          "accepted yet; add DIDWW's ranges with --allow-didww.")
elif any(ipaddress.IPv4Network(r, strict=False).prefixlen == 0 for r in ranges):
    print("WARNING: allowedCidrRanges contains 0.0.0.0/0, which accepts INVITEs "
          "from any address; replace it with --allow-didww.")
if fb:
    print("The fallback handler's signing secret was generated by Ultravox; read it "
          "with --show --show-secrets when you configure the handler.")
print("Inbound address shape: agent_{agent_id}@" + str(out.get("domain")))
print("Outbound: POST /api/calls with medium.sip.outgoing "
      "{to, from, username, password} using the DIDWW outbound trunk.")
