#!/usr/bin/env python3
"""Health check for a DIDWW-backed voice agent connection. READ-ONLY.

Usage:
  DIDWW_API_KEY=... python3 scripts/monitor.py [--min-balance 20] [--number +336...]

Checks: DIDWW balance against the threshold, DIDs present and active,
trunks present. Exit code 1 when anything warns, so it slots into cron,
CI or a scheduled task and alerts on failure. With the DIDWW MCP
connected, an agent can run the same checks as tool calls (get_balance,
list_dids, list_trunks) instead of this script.

Suggested cadence: daily. What to do on warnings is in the skill text.
"""
import json, os, sys, urllib.request

KEY = os.environ.get("DIDWW_API_KEY", "")
BASE = os.environ.get("DIDWW_API_BASE", "https://api.didww.com/v3")
if not KEY:
    sys.exit("Set DIDWW_API_KEY (panel: API, DIDWW API 3), or use the DIDWW MCP.")
a = sys.argv[1:]
def opt(n, d=None):
    return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
MIN_BAL = float(opt("--min-balance", "10"))

def get(path):
    req = urllib.request.Request(BASE + path, headers={
        "Api-Key": KEY, "Accept": "application/vnd.api+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"WARN: DIDWW API {e.code} on {path}: {e.read().decode()[:300]}")
        return None
    except (urllib.error.URLError, OSError) as e:
        print(f"WARN: DIDWW API unreachable on {path}: {getattr(e, 'reason', e)}")
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
    warns += 1

dids = get("/dids?page[size]=200")
if dids is not None:
    items = dids.get("data", [])
    print(f"dids: {len(items)}")
    number_filter = (opt("--number") or "").lstrip("+")
    for d in items:
        at = d.get("attributes", {})
        num = at.get("number", "?")
        if number_filter and number_filter not in num:
            continue
        if at.get("terminated"):
            print(f"  +{num}: terminated (ignored)")
            continue
        blocked = at.get("blocked") or at.get("awaiting_registration")
        status = "BLOCKED/AWAITING" if blocked else "active"
        line = f"  +{num}: {status}"
        print(line)
        if blocked:
            print(f"WARN: +{num} not serving calls; check panel for "
                  "registration or blocking reasons.")
            warns += 1

trunks = get("/trunks?page[size]=100")
if trunks is not None:
    print(f"voice-in trunks: {len(trunks.get('data', []))}")
    if not trunks.get("data"):
        print("WARN: no inbound trunks exist; inbound calls have nowhere to go.")
        warns += 1

print(f"\n{'OK' if warns == 0 else f'{warns} warning(s)'}")
sys.exit(1 if warns else 0)
