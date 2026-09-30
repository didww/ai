#!/usr/bin/env python3
"""Request-shape tests for scripts/connect.py (stubbed HTTP)."""
import contextlib, io, json, os, runpy, sys, urllib.error, urllib.request
sys.dont_write_bytecode = True
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "connect.py")
results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
def run_script(argv, env, canned, fail=None):
    """Run the script with stubbed HTTP; return (captured requests, output, exit code)."""
    reqs = []
    class R:
        def __init__(s, d): s.d = json.dumps(d).encode()
        def read(s): return s.d
        def __enter__(s): return s
        def __exit__(s, *a): pass
    def fake_urlopen(req, timeout=None):
        reqs.append({"url": req.full_url, "method": req.get_method(), "headers": {k.lower(): v for k, v in req.header_items()}, "body": json.loads(req.data) if req.data else None})
        if fail: raise urllib.error.HTTPError(req.full_url, fail, "err", {}, io.BytesIO(b'{"error":"stubbed failure"}'))
        return R(canned)
    old_env, old_argv, old_open = dict(os.environ), sys.argv, urllib.request.urlopen
    os.environ.update(env); sys.argv = [P] + argv; urllib.request.urlopen = fake_urlopen
    out = io.StringIO(); code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out): runpy.run_path(P, run_name="__main__")
    except SystemExit as e:  # sys.exit("msg") prints msg only at interpreter exit; mirror that
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        if isinstance(e.code, str): out.write(e.code + "\n")
    finally:
        urllib.request.urlopen = old_open; sys.argv = old_argv; os.environ.clear(); os.environ.update(old_env)
    return reqs, out.getvalue(), code

full = ["--number", "+33144556677", "--didww-host", "fra.eu.out.didww.com", "--didww-user", "u", "--didww-pass", "p", "--agent", "agent_1"]
reqs, out, code = run_script(full, {"RETELL_API_KEY": "k"}, {"phone_number": "+33144556677"})
b = reqs[0]["body"] if reqs else {}
check("one POST to /import-phone-number with a Bearer key", len(reqs) == 1 and reqs[0]["url"].endswith("/import-phone-number") and reqs[0]["headers"].get("authorization") == "Bearer k", [r["url"] for r in reqs])
check("E.164 number kept, termination_uri is the bare DIDWW host, transport TCP by default", b.get("phone_number") == "+33144556677" and b.get("termination_uri") == "fra.eu.out.didww.com" and b.get("transport") == "TCP", json.dumps(b))
check("digest pair as sip_trunk_auth_username/password", b.get("sip_trunk_auth_username") == "u" and b.get("sip_trunk_auth_password") == "p")
check("agent bound inbound and outbound as [{agent_id, weight}]", b.get("inbound_agents") == [{"agent_id": "agent_1", "weight": 1}] and b.get("outbound_agents") == [{"agent_id": "agent_1", "weight": 1}])
check("points the user at sip.retellai.com for the DIDWW trunk", "sip.retellai.com" in out)
reqs, out, code = run_script(full[:6] + ["--transport", "TLS"], {"RETELL_API_KEY": "k"}, {})
b = reqs[0]["body"] if reqs else {}
check("without --agent no agent keys are sent; --transport passes through", "inbound_agents" not in b and b.get("transport") == "TLS", json.dumps(b))
reqs, out, code = run_script(["--number", "+33144556677"], {"RETELL_API_KEY": "k"}, {})
check("missing --didww-host prints usage, no API call", code != 0 and not reqs and "Usage" in out)
reqs, out, code = run_script(full, {}, {})
check("refuses without RETELL_API_KEY", code != 0 and not reqs)

print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
