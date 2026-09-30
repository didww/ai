#!/usr/bin/env python3
"""Request-shape tests for scripts/import_number.py (stubbed HTTP)."""
import contextlib, io, json, os, runpy, sys, urllib.error, urllib.request
sys.dont_write_bytecode = True
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "import_number.py")
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

base = ["--number", "+33144556677", "--inbound-user", "iu", "--inbound-pass", "ip", "--outbound-host", "fra.eu.out.didww.com", "--outbound-user", "ou", "--outbound-pass", "op"]
reqs, out, code = run_script(base + ["--agent", "agent_x"], {"ELEVENLABS_API_KEY": "k"}, {"phone_number_id": "phnum_1"})
b = reqs[0]["body"] if reqs else {}; ib = b.get("inbound_trunk_config", {}); ob = b.get("outbound_trunk_config", {})
check("inbound auth sent as credentials{username,password}", ib.get("credentials", {}).get("username") == "iu" and ib.get("credentials", {}).get("password") == "ip" and "auth_username" not in ib, json.dumps(ib))
check("transport is a lowercase enum value", ob.get("transport") in ("auto", "udp", "tcp", "tls"), repr(ob.get("transport")))
check("outbound credentials + agent PATCH with agent_id", ob.get("credentials", {}).get("username") == "ou" and len(reqs) == 2 and reqs[1]["method"] == "PATCH" and reqs[1]["body"] == {"agent_id": "agent_x"})
check("xi-api-key header on the import call", reqs[0]["headers"].get("xi-api-key") == "k" if reqs else False)
reqs, out, code = run_script(base + ["--transport", "TLS"], {"ELEVENLABS_API_KEY": "k"}, {"phone_number_id": "p"})
check("--transport TLS normalised to tls", bool(reqs) and reqs[0]["body"]["outbound_trunk_config"]["transport"] == "tls")
reqs, out, code = run_script(base + ["--transport", "sctp"], {"ELEVENLABS_API_KEY": "k"}, {})
check("unknown transport refused before any API call", code != 0 and not reqs)
reqs, out, code = run_script(["--number", "+33144556677"], {"ELEVENLABS_API_KEY": "k"}, {})
check("missing arguments print usage, no API call", code != 0 and not reqs and "Usage" in out)

print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
