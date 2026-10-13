#!/usr/bin/env python3
"""Runs scripts/monitor.py against a mock DIDWW API (tests/mock_didww.py) in several account states."""
import os, socket, subprocess, sys, time
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "scripts", "monitor.py")
results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def monitor(scen, *args, base=None):
    p = free_port(); srv = subprocess.Popen([sys.executable, os.path.join(HERE, "mock_didww.py"), scen, str(p)])
    try:
        for _ in range(50):
            s = socket.socket(); s.settimeout(0.2)
            if s.connect_ex(("127.0.0.1", p)) == 0: s.close(); break
            time.sleep(0.1)
        r = subprocess.run([sys.executable, P, *args], env={**os.environ, "DIDWW_API_KEY": "fake", "DIDWW_API_BASE": base or f"http://127.0.0.1:{p}"}, capture_output=True, text=True, timeout=60)
    finally: srv.terminate(); srv.wait()
    return r.returncode, r.stdout + r.stderr
c, o = monitor("ok"); check("healthy account exits 0", c == 0 and "OK" in o)
c, o = monitor("creditline"); check("credit-line account (balance -37723, available 12276) exits 0", c == 0, o.strip().splitlines()[0] if o else "")
c, o = monitor("terminated"); check("terminated DID is listed but never warned about", c == 0 and "WARN" not in o and "terminated" in o, [l for l in o.splitlines() if "WARN" in l][:1])
c, o = monitor("lowbal"); check("low balance warns (exit 1)", c == 1 and "WARN: balance" in o)
c, o = monitor("blocked"); check("blocked DID warns (exit 1)", c == 1 and "not serving" in o)
c, o = monitor("notrunk"); check("no inbound trunks warns (exit 1)", c == 1 and "no inbound trunks" in o)
c, o = monitor("ok", base="http://127.0.0.1:1"); check("unreachable API -> WARN line, no traceback, exit 1", c == 1 and "WARN" in o and "Traceback" not in o)
c, o = monitor("ok", base="https://no-such-host.invalid"); check("DNS failure -> WARN line, no traceback, exit 1", c == 1 and "WARN" in o and "Traceback" not in o)
c, o = monitor("many"); check("pagination: follows links.next at page size 100 and sees all 150 DIDs (a blocked one on page 2 warns)", c == 1 and "dids: 150" in o and "+33144000149: BLOCKED" in o, [l for l in o.splitlines() if l.startswith(("dids", "WARN"))])
c, o = monitor("offhost"); check("pagination: refuses to follow links.next to another host (API key stays home)", c == 1 and "another host" in o)
c, o = monitor("dids500"); check("DIDs endpoint failure counts as a warning (no false OK)", c == 1 and "DID check could not run" in o and "\nOK" not in o)
c, o = monitor("trunks500"); check("trunks endpoint failure counts as a warning (no false OK)", c == 1 and "trunk check could not run" in o)
c, o = monitor("ok", "--number", "+33 1 44 55 66 77"); check("--number: exact match after normalising, exit 0", c == 0 and "+33144556677: active" in o and "441234567890" not in o)
c, o = monitor("ok", "--number", "+3314455667"); check("--number: a prefix of a real DID is NOT a match -> not on account, exit 1", c == 1 and "is not on this account" in o)
c, o = monitor("terminated", "--number", "+13614157804"); check("--number: only a terminated entry -> warns terminated", c == 1 and "is terminated" in o)
c, o = monitor("ok", base="http://api.example.com/v3"); check("DIDWW_API_BASE over plain http (non-loopback) refused", c != 0 and "https" in o)
c, o = monitor("ok", "--min-balance"); check("flag without a value refused cleanly", c != 0 and "Traceback" not in o)
c, o = monitor("ok", "--numbr", "+1"); check("misspelt flag refused instead of ignored", c != 0 and "Bad argument" in o)
print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
