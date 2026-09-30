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

reqs, out, code = run_script(["--number", "+33144556677", "--didww-host", "fra.eu.out.didww.com", "--didww-user", "u", "--didww-pass", "p", "--assistant", "asst_1"], {"VAPI_API_KEY": "k"}, {"id": "cred_1"})
h = reqs[0]["headers"] if reqs else {}
check("sends a non-Python User-Agent (Cloudflare 1010 blocks urllib's default)", "user-agent" in h and not h["user-agent"].lower().startswith("python"), h.get("user-agent"))
check("credential then number, bodies intact", len(reqs) == 2 and reqs[0]["body"]["provider"] == "byo-sip-trunk" and reqs[0]["body"]["outboundAuthenticationPlan"]["authPassword"] == "p" and reqs[1]["body"]["credentialId"] == "cred_1" and reqs[1]["body"]["number"] == "33144556677" and reqs[1]["body"]["assistantId"] == "asst_1", [r["url"] for r in reqs])
reqs, out, code = run_script(["--number", "+33144556677", "--didww-host", "h", "--didww-user", "u"], {"VAPI_API_KEY": "k"}, {"id": "c"})
check("refuses to run without --didww-pass", code != 0 and not reqs)
reqs, out, code = run_script(["--number", "+33144556677", "--didww-host", "h", "--didww-user", "u", "--didww-pass", "p"], {"VAPI_API_KEY": "k"}, {"id": "c"}, fail=401)
check("API error exits nonzero with the status, no traceback", code != 0 and "401" in out and "Traceback" not in out, out[-120:])

print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
