#!/usr/bin/env python3
"""Request-shape tests for scripts/register_number.py (stubbed HTTP)."""
import contextlib, io, json, os, runpy, stat, sys, tempfile, urllib.error, urllib.request
sys.dont_write_bytecode = True
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "register_number.py")
results = []
TMP = tempfile.mkdtemp(); n_out = [0]
def out_file():
    n_out[0] += 1; return os.path.join(TMP, f"resp{n_out[0]}.json")
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

reqs, out, code = run_script(["--number", "+33144556677", "--webhook", "https://h.example/xai", "--sip-user", "u", "--sip-pass", "p", "--allow-ip", "1.2.3.4", "--out", (F1 := out_file())], {"XAI_API_KEY": "k"}, {"id": "pn_1", "webhook": {"url": "https://h.example/xai", "secret": "whsec_TOPSECRET"}, "notes": "n" * 2000})
b = reqs[0]["body"] if reqs else {}; sa = b.get("sip_auth", {})
check("origin byo_trunk", b.get("origin") == "byo_trunk", repr(b.get("origin")))
check("webhook is an object with url", isinstance(b.get("webhook"), dict) and b["webhook"].get("url") == "https://h.example/xai", repr(b.get("webhook")))
check("sip_auth uses auth_username/auth_password and keeps allowed_addresses", sa.get("auth_username") == "u" and sa.get("auth_password") == "p" and sa.get("allowed_addresses") == ["1.2.3.4"], json.dumps(sa))
check("tells the user the signing secret is shown only once", "only once" in out.lower())
check("secret is not printed; the screen shows a redacted copy", "whsec_TOPSECRET" not in out and '"secret": "***"' in out, out[:200])
saved = json.load(open(F1)) if os.path.exists(F1) else {}
check("full response saved untruncated with the secret", saved.get("webhook", {}).get("secret") == "whsec_TOPSECRET" and len(saved.get("notes", "")) == 2000)
check("response file is mode 0600", os.path.exists(F1) and stat.S_IMODE(os.stat(F1).st_mode) == 0o600, oct(os.stat(F1).st_mode) if os.path.exists(F1) else "missing")
reqs, out, code = run_script(["--number", "+1", "--webhook", "https://h.example/x", "--sip-user", "u", "--sip-pass", "p", "--out", F1], {"XAI_API_KEY": "k"}, {})
check("refuses to overwrite an existing response file", code != 0 and not reqs and "exists" in out, out[-120:])
reqs, out, code = run_script(["--number", "+1", "--webhook", "https://h.example/x", "--sip-user", "u", "--out", out_file()], {"XAI_API_KEY": "k", "XAI_SIP_PASS": "envpass"}, {})
check("SIP password can come from XAI_SIP_PASS", code == 0 and reqs and reqs[0]["body"]["sip_auth"].get("auth_password") == "envpass", out[-120:])
reqs, out, code = run_script(["--number", "+1", "--webhook", "http://h.example/x", "--sip-user", "u", "--sip-pass", "p", "--out", out_file()], {"XAI_API_KEY": "k"}, {})
check("refuses a plain http:// webhook URL", code != 0 and not reqs, out[-120:])
reqs, out, code = run_script(["--number", "+1", "--webhook", "https://h.example/x", "--sip-user", "u", "--out", out_file()], {"XAI_API_KEY": "k"}, {})
check("refuses --sip-user without --sip-pass", code != 0 and not reqs)
reqs, out, code = run_script(["--number", "+1", "--webhook", "https://h.example/x", "--out", out_file()], {"XAI_API_KEY": "k"}, {})
check("refuses to register with no SIP auth at all", code != 0 and not reqs)
reqs, out, code = run_script(["--number", "+1", "--webhook", "https://h.example/x", "--sip-user", "u", "--sip-pass", "p", "--out", out_file()], {"XAI_API_KEY": "k"}, {}, fail=422)
check("API error exits nonzero with the status, no traceback", code != 0 and "422" in out and "Traceback" not in out, out[-120:])

import shutil; shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
