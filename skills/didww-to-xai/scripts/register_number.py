#!/usr/bin/env python3
"""Add a DIDWW number to xAI (SpaceXSI) as a Direct SIP number.

Usage:
  python3 scripts/register_number.py --number +15105550100 --agent agent_XXXX \
    (--digest | --sip-user USER | --allow-didww | --allow-ip CIDR ...) \
    [--name NAME] [--env-file FILE ...]
  python3 scripts/register_number.py --number +15105550100 \
    --webhook https://your.host/xai (auth flags as above) [--out FILE]
  python3 scripts/register_number.py --list [--env-file FILE]
  python3 scripts/register_number.py --delete PHONE_NUMBER_ID [--env-file FILE]

Routing (exactly one):
  --agent ID     a voice agent built in the xAI console (DIDWW's xAI guide;
                 no server). The ID starts with agent_ and is in the console
                 address bar when the agent is open.
  --webhook URL  your own backend (https), which receives
                 realtime.call.incoming and joins each call over a websocket.
SIP authentication (at least one):
  --digest       digest pair from the environment: XAI_SIP_USER and
                 XAI_SIP_PASS, or DIDWW_SIP_USERNAME and DIDWW_SIP_PASSWORD
                 (the DIDWW outbound trunk's pair, which call transfers need
                 on the DIDWW inbound trunk anyway)
  --sip-user U   digest with this username; the password comes from
                 --sip-pass, XAI_SIP_PASS or DIDWW_SIP_PASSWORD
  --allow-didww  allowed_addresses += DIDWW's seven inbound signaling IPs
  --allow-ip     allowed_addresses += one IPv4 CIDR (repeatable)
--env-file reads KEY=VALUE lines (XAI_API_KEY and the SIP pair) without
overriding the environment, so no secret passes through argv or the chat.
xAI never returns the SIP password. With --webhook the response carries
the webhook signing secret exactly once: the full response is written to
--out (default xai-<number>.json, mode 0600, never overwritten) and the
screen shows a redacted copy. Stdlib only; API errors print verbatim.
"""
import ipaddress, json, os, re, sys, urllib.error, urllib.request

DIDWW_SIGNALING = ["46.19.209.14/32", "46.19.210.14/32", "46.19.212.14/32",
                   "46.19.213.14/32", "46.19.214.14/32", "46.19.215.14/32",
                   "185.238.173.14/32"]
VALUE = {"--number", "--agent", "--webhook", "--sip-user", "--sip-pass",
         "--allow-ip", "--name", "--out", "--env-file", "--delete"}
BOOL = {"--digest", "--allow-didww", "--list", "--help", "-h"}


def parse(argv):
    flags, vals, i = set(), {k: [] for k in VALUE}, 0
    while i < len(argv):
        x = argv[i]
        if x in BOOL:
            flags.add(x)
        elif x in VALUE:
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                sys.exit(f"{x} needs a value; run with --help.")
            vals[x].append(argv[i + 1]); i += 1
        else:
            sys.exit(f"Unknown argument {x!r}; run with --help.")
        i += 1
    return flags, vals


flags, vals = parse(sys.argv[1:])
if "--help" in flags or "-h" in flags or not sys.argv[1:]:
    print(__doc__)
    sys.exit(0)
one = lambda k: vals[k][-1] if vals[k] else None

for path in vals["--env-file"]:
    try:
        lines = open(os.path.expanduser(path), encoding="utf-8").read().splitlines()
    except OSError as e:
        sys.exit(f"--env-file {path}: {e.strerror}")
    for line in lines:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if v:
                os.environ.setdefault(k.strip(), v)

KEY = os.environ.get("XAI_API_KEY", "")
if not KEY:
    sys.exit("Set XAI_API_KEY (console.x.ai, API Keys, key type Grok API), "
             "or pass --env-file with it.")


def redact(v):
    if isinstance(v, dict):
        return {k: "***" if any(w in k.lower() for w in ("secret", "password", "token"))
                else redact(x) for k, x in v.items()}
    if isinstance(v, list):
        return [redact(x) for x in v]
    return v


def call(method, path, body=None):
    req = urllib.request.Request(
        "https://api.x.ai" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode(errors="replace")
            return r.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        sys.exit(f"xAI API {e.code} on {method} {path}:\n{e.read().decode(errors='replace')[:2000]}")


if "--list" in flags:
    status, resp = call("GET", "/v2/phone-numbers")
    print(json.dumps(redact(resp), indent=1))
    sys.exit(0)
if vals["--delete"]:
    pid = one("--delete")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", pid):
        sys.exit("--delete needs a phone_number_id from --list.")
    status, _ = call("DELETE", f"/v2/phone-numbers/{pid}")
    print(f"Deleted {pid} (HTTP {status}). The number stays on your DIDWW "
          "account; route it elsewhere or add it to xAI again.")
    sys.exit(0)

# validate everything before calling the API
number = one("--number") or ""
if not re.fullmatch(r"\+[1-9]\d{6,14}", number):
    sys.exit("--number must be the DIDWW number in E.164 with the + sign "
             "(e.g. +15105550100); the DIDWW trunk sends it as +{DID}.")
agent, webhook = one("--agent"), one("--webhook")
if bool(agent) == bool(webhook):
    sys.exit("Give exactly one of --agent (console voice agent) or --webhook "
             "(your own backend).")
if agent and not re.fullmatch(r"agent_[A-Za-z0-9]+", agent):
    sys.exit("--agent must be the console agent ID, which starts with agent_.")
if webhook and not webhook.startswith("https://"):
    sys.exit("--webhook must be an https:// URL (xAI signs, but does not "
             "encrypt, what it sends there).")
OUT = one("--out") or f"xai-{number.lstrip('+')}.json"
if webhook and os.path.exists(OUT):
    sys.exit(f"{OUT} exists; pass --out with a new file name (it will hold "
             "the one-time webhook secret).")

sip_auth = {}
user = one("--sip-user")
if "--digest" in flags and not user:
    user = os.environ.get("XAI_SIP_USER") or os.environ.get("DIDWW_SIP_USERNAME", "")
    if not user:
        sys.exit("--digest needs XAI_SIP_USER or DIDWW_SIP_USERNAME "
                 "(pass the credentials file with --env-file).")
if user:
    pw = one("--sip-pass") or os.environ.get("XAI_SIP_PASS") or os.environ.get("DIDWW_SIP_PASSWORD", "")
    if not pw:
        sys.exit("The digest username needs a password: --sip-pass, XAI_SIP_PASS "
                 "or DIDWW_SIP_PASSWORD.")
    sip_auth.update({"auth_username": user, "auth_password": pw})
cidrs = (DIDWW_SIGNALING if "--allow-didww" in flags else []) + vals["--allow-ip"]
for c in cidrs:
    try:
        net = ipaddress.IPv4Network(c, strict=False)
    except ValueError:
        sys.exit(f"--allow-ip {c!r} is not an IPv4 address or CIDR.")
    if net.prefixlen == 0:
        sys.exit("--allow-ip 0.0.0.0/0 would accept INVITEs from any address.")
if cidrs:
    sip_auth["allowed_addresses"] = list(dict.fromkeys(cidrs))
if not sip_auth:
    sys.exit("Give --digest or --sip-user (digest, preferred) and/or "
             "--allow-didww; without either, anyone who knows the number "
             "can call the agent on your xAI credits.")

body = {"origin": "byo_trunk", "name": one("--name") or "DIDWW " + number,
        "phone_number": number, "sip_auth": sip_auth}
if agent:
    body["agent_id"] = agent
else:
    body["webhook"] = {"url": webhook}
status, resp = call("POST", "/v2/phone-numbers", body)
if webhook:
    fd = os.open(OUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(resp, f, indent=1)
print(f"HTTP {status}")
print(json.dumps(redact(resp), indent=1))
if webhook:
    print(f"\nFull response, including the webhook signing secret, saved to {OUT} "
          "(mode 0600). xAI returns that secret only once: move it into the "
          "backend's secret store, then delete the file.")
print("\nDIDWW inbound trunk: host sip.voice.x.ai, port 5061, transport TLS, "
      "User Part of R-URI +{DID}, IPv4, codecs PCMU/PCMA/telephone-event, "
      "SRTP Disable; Max Transfers 1 for transfers.")
if "auth_username" in sip_auth:
    print("Turn on the inbound trunk's Authorization with the same username and "
          "password (Inbound Trunks, Edit, Authorization). xAI never returns "
          "the password; rotate it on both sides together.")
print("Transfers: a sip:+NUMBER@<DIDWW outbound host> destination through a "
      "DIDWW outbound trunk whose pair is on the inbound trunk's Authorization. "
      "xAI places no outbound calls.")
if webhook:
    print("Wire the webhook backend next; see the skill's section 5B.")
