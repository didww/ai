#!/usr/bin/env python3
"""Health check for a DIDWW-backed voice agent connection. READ-ONLY.

Usage:
  DIDWW_API_KEY=... python3 scripts/monitor.py [--min-balance 20] [--number +336...]

Checks: DIDWW balance against the threshold, DIDs present and active
(all pages), trunks present; with --number, that exact number must exist
and be active. A check that cannot run (API error, unreachable) counts
as a warning too. Exit code 1 when anything warns, so it slots into cron,
CI or a scheduled task and alerts on failure. With the DIDWW MCP
connected, an agent can run the same checks as tool calls (get_balance,
list_dids, list_trunks) instead of this script.

Suggested cadence: daily. What to do on warnings is in the skill text.
"""
import ipaddress, json, os, re, sys, urllib.error, urllib.parse, urllib.request

KEY = os.environ.get("DIDWW_API_KEY", "")
BASE = os.environ.get("DIDWW_API_BASE", "https://api.didww.com/v3").rstrip("/")
if not KEY:
    sys.exit("Set DIDWW_API_KEY (panel: API, DIDWW API 3), or use the DIDWW MCP.")

def loopback(host):
    try:
        return host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
_b = urllib.parse.urlsplit(BASE)
if _b.scheme != "https" and not (_b.scheme == "http" and loopback(_b.hostname or "")):
    sys.exit("DIDWW_API_BASE must be https:// (the API key travels in a header).")

a = sys.argv[1:]
VALUE = {"--min-balance", "--number"}
opts, i = {}, 0
while i < len(a):
    if a[i] in VALUE and i + 1 < len(a) and not a[i + 1].startswith("--"):
        opts[a[i]] = a[i + 1]; i += 2
    elif a[i] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    else:
        sys.exit(f"Bad argument {a[i]!r}; usage:\n{__doc__}")
try:
    MIN_BAL = float(opts.get("--min-balance", "10"))
except ValueError:
    sys.exit("--min-balance must be a number.")
WANT = re.sub(r"\D", "", opts.get("--number", ""))
if "--number" in opts and not WANT:
    sys.exit("--number must contain digits, e.g. +33144556677.")

def get(url):
    if not url.startswith(("http://", "https://")):
        url = BASE + url
    req = urllib.request.Request(url, headers={
        "Api-Key": KEY, "Accept": "application/vnd.api+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"WARN: DIDWW API {e.code} on {url}: {e.read().decode()[:300]}")
    except (urllib.error.URLError, OSError) as e:
        print(f"WARN: DIDWW API unreachable on {url}: {getattr(e, 'reason', e)}")
    except ValueError:
        print(f"WARN: DIDWW API returned non-JSON on {url}")
    return None

def get_all(path):
    """Every page of a list endpoint (page size max 100, follow links.next);
    None when any page fails, so a partial list never passes as complete."""
    items, url = [], path
    for _ in range(1000):
        page = get(url)
        if page is None:
            return None
        items += page.get("data") or []
        nxt = (page.get("links") or {}).get("next")
        if not nxt:
            return items
        n = urllib.parse.urlsplit(urllib.parse.urljoin(BASE + "/", nxt))
        if (n.scheme, n.netloc) != (_b.scheme, _b.netloc):
            print(f"WARN: refusing to follow pagination to another host: {nxt}")
            return None
        url = urllib.parse.urlunsplit(n)
    print(f"WARN: more than 1000 pages on {path}; stopped")
    return None

warns = 0
bal = get("/balance")
if bal:
    attrs = bal.get("data", {}).get("attributes", {})
    balance = float(attrs.get("balance", 0))
    # total_balance = balance + credit line, the funds actually available
    # for service. Accounts with a credit line run a negative balance by
    # design, so the threshold must apply to the total, not the balance.
    available = float(attrs.get("total_balance",
                                balance + float(attrs.get("credit", 0))))
    print(f"balance: {balance} (available incl. credit: {available})")
    if available < MIN_BAL:
        print(f"WARN: balance {available} (incl. credit) below threshold {MIN_BAL}. "
              "Top up: panel Billing, Payment Methods (and enable "
              "Low Balance Notification + Auto-charge).")
        warns += 1
else:
    print("WARN: balance check could not run")
    warns += 1

dids = get_all("/dids?page[size]=100")
if dids is None:
    print("WARN: DID check could not run")
    warns += 1
else:
    print(f"dids: {len(dids)}")
    found_any = found_active = found_blocked = False
    for d in dids:
        at = d.get("attributes", {})
        num = str(at.get("number", "?"))
        if WANT and re.sub(r"\D", "", num) != WANT:
            continue
        found_any = True
        if at.get("terminated"):
            print(f"  +{num}: terminated (ignored)")
            continue
        blocked = at.get("blocked") or at.get("awaiting_registration")
        print(f"  +{num}: {'BLOCKED/AWAITING' if blocked else 'active'}")
        if blocked:
            print(f"WARN: +{num} not serving calls; check panel for "
                  "registration or blocking reasons.")
            warns += 1
            found_blocked = True
        else:
            found_active = True
    if WANT and not found_any:
        print(f"WARN: +{WANT} is not on this account.")
        warns += 1
    elif WANT and not (found_active or found_blocked):
        print(f"WARN: +{WANT} is terminated on this account.")
        warns += 1

trunks = get_all("/trunks?page[size]=100")
if trunks is None:
    print("WARN: trunk check could not run")
    warns += 1
else:
    print(f"voice-in trunks: {len(trunks)}")
    if not trunks:
        print("WARN: no inbound trunks exist; inbound calls have nowhere to go.")
        warns += 1

print(f"\n{'OK' if warns == 0 else f'{warns} warning(s)'}")
sys.exit(1 if warns else 0)
