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

SIP = {"domain": "acct.sip.ultravox.ai", "allowedCidrRanges": ["1.2.3.0/24"], "fallbackHandler": {"url": "https://h/route"}}
reqs, out, code = run_script(["--help"], {"ULTRAVOX_API_KEY": "k"}, SIP)
check("--help exits 0 without calling the API", code == 0 and not reqs and "Usage" in out)
reqs, out, code = run_script(["--show"], {"ULTRAVOX_API_KEY": "k"}, SIP)
check("--show: one GET /api/sip with X-API-Key, prints the SIP domain, no PATCH", [(r["method"], r["url"]) for r in reqs] == [("GET", "https://api.ultravox.ai/api/sip")] and reqs[0]["headers"].get("x-api-key") == "k" and "acct.sip.ultravox.ai" in out and code == 0, [(r["method"], r["url"]) for r in reqs])
reqs, out, code = run_script(["--allow-cidr", "1.2.3.0/24", "--allow-cidr", "5.6.7.8/32", "--fallback-url", "https://h/route", "--allow-all-agents"], {"ULTRAVOX_API_KEY": "k"}, SIP)
p = reqs[1]["body"] if len(reqs) > 1 else {}
check("flags become one PATCH /api/sip with allowedCidrRanges, fallbackHandler{url}, allowAllAgents", len(reqs) == 2 and reqs[1]["method"] == "PATCH" and p.get("allowedCidrRanges") == ["1.2.3.0/24", "5.6.7.8/32"] and p.get("fallbackHandler") == {"url": "https://h/route"} and p.get("allowAllAgents") is True, json.dumps(p))
check("prints the agent_<id>@domain address shape", "agent_{agent_id}@acct.sip.ultravox.ai" in out)
reqs, out, code = run_script([], {"ULTRAVOX_API_KEY": "k"}, SIP)
check("no flags: reads, then refuses to PATCH nothing", code != 0 and len(reqs) == 1 and "Nothing to change" in out)
reqs, out, code = run_script(["--show"], {}, SIP)
check("refuses without ULTRAVOX_API_KEY", code != 0 and not reqs)

print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
