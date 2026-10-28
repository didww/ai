#!/usr/bin/env python3
"""Request-shape tests for scripts/connect.py (stubbed HTTP)."""
import contextlib, io, json, os, runpy, sys, urllib.error, urllib.request
sys.dont_write_bytecode = True
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "connect.py")
results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
def run_script(argv, env, canned, fail=None, fail_method=None):
    """Run the script with stubbed HTTP; return (captured requests, output, exit code)."""
    reqs = []
    class R:
        def __init__(s, d): s.d = json.dumps(d).encode()
        def read(s): return s.d
        def __enter__(s): return s
        def __exit__(s, *a): pass
    def fake_urlopen(req, timeout=None):
        reqs.append({"url": req.full_url, "method": req.get_method(), "headers": {k.lower(): v for k, v in req.header_items()}, "body": json.loads(req.data) if req.data else None})
        if fail and fail_method in (None, req.get_method()): raise urllib.error.HTTPError(req.full_url, fail, "err", {}, io.BytesIO(b'{"error":"stubbed failure"}'))
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

full = ["--number", "+33144556677", "--didww-host", "fra.eu.out.didww.com", "--didww-user", "u", "--didww-pass", "p"]
reqs, out, code = run_script(full, {"VOGENT_API_KEY": "k"}, {"id": "pn_1"})
b = reqs[0]["body"] if reqs else {}
check("one POST to /api/phone_numbers with a Bearer key", len(reqs) == 1 and reqs[0]["url"].endswith("/api/phone_numbers") and reqs[0]["headers"].get("authorization") == "Bearer k", [r["url"] for r in reqs])
check("type sip_import with sipImport{phoneNumber, terminationUri, username, password}", b.get("type") == "sip_import" and b.get("sipImport") == {"phoneNumber": "+33144556677", "terminationUri": "fra.eu.out.didww.com", "username": "u", "password": "p"}, json.dumps(b))
check("prints the DIDWW inbound trunk (sip.vogent.ai, {DID}, outbound pair as Authorization) and how to link the agent", "sip.vogent.ai" in out and "{DID}" in out and "Authorization" in out and "--phone-id pn_1 --agent" in out and "MANUAL STEP" not in out, out[-200:])
reqs, out, code = run_script(full + ["--agent", "ag_1"], {"VOGENT_API_KEY": "k"}, {"id": "pn_1"})
check("--agent: POST import, then PUT /api/phone_numbers/{id} {agentId} (linking is not dashboard-only)", code == 0 and [r["method"] for r in reqs] == ["POST", "PUT"] and reqs[1]["url"].endswith("/api/phone_numbers/pn_1") and reqs[1]["body"] == {"agentId": "ag_1"} and reqs[1]["headers"].get("authorization") == "Bearer k", [(r["method"], r["url"]) for r in reqs])
reqs, out, code = run_script(full + ["--agent", "ag_1"], {"VOGENT_API_KEY": "k"}, {"id": "pn_1"}, fail=404, fail_method="PUT")
check("linking failure after a good import exits nonzero and names the step", code != 0 and len(reqs) == 2 and "linking phone number" in out, out[-150:])
reqs, out, code = run_script(full + ["--agent", "ag_1"], {"VOGENT_API_KEY": "k"}, {"status": "ok"})
check("import response without an id: no PUT guessed, exits nonzero", code != 0 and [r["method"] for r in reqs] == ["POST"])
reqs, out, code = run_script(["--phone-id", "pn_9", "--agent", "ag_1"], {"VOGENT_API_KEY": "k"}, {"id": "pn_9"})
check("--phone-id + --agent links an imported number: one PUT, no import", code == 0 and [(r["method"], r["url"].rsplit("/", 1)[-1]) for r in reqs] == [("PUT", "pn_9")] and reqs[0]["body"] == {"agentId": "ag_1"})
for argv in (["--phone-id", "pn_9"], ["--phone-id", "pn_9", "--agent", "ag_1", "--number", "+33144556677"], ["--phone-id", "../agents", "--agent", "ag_1"]):
    reqs, out, code = run_script(argv, {"VOGENT_API_KEY": "k"}, {})
    check(f"refused before any API call: {' '.join(argv)}", code != 0 and not reqs)
reqs, out, code = run_script(["--number", "+33144556677"], {"VOGENT_API_KEY": "k"}, {})
check("missing --didww-host prints usage, no API call", code != 0 and not reqs and "Usage" in out)
reqs, out, code = run_script(full[:6], {"VOGENT_API_KEY": "k"}, {})
check("missing password refused before any API call (Vogent requires it, non-null)", code != 0 and not reqs)
reqs, out, code = run_script(full[:6], {"VOGENT_API_KEY": "k", "DIDWW_TRUNK_PASS": "envp"}, {"id": "pn_2"})
check("password can come from DIDWW_TRUNK_PASS", code == 0 and reqs and reqs[0]["body"]["sipImport"]["password"] == "envp")
reqs, out, code = run_script(full, {"VOGENT_API_KEY": "k"}, {"id": "pn_3", "sipImport": {"password": "SECRETPW"}})
check("echoed response redacts the password", "SECRETPW" not in out and "***" in out)
reqs, out, code = run_script(full + ["--agnet", "x"], {"VOGENT_API_KEY": "k"}, {})
check("unknown flag refused instead of ignored", code != 0 and not reqs and "Bad argument" in out)
reqs, out, code = run_script(full, {"VOGENT_API_KEY": "k"}, {}, fail=500)
check("API error exits nonzero with the status, no traceback", code != 0 and "500" in out and "Traceback" not in out, out[-120:])

print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
