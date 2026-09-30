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
print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
