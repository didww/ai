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
        status = 201
        def __init__(s, d): s.d = json.dumps(d).encode()
        def read(s): return s.d
        def __enter__(s): return s
        def __exit__(s, *a): pass
    def fake_urlopen(req, timeout=None):
        reqs.append({"url": req.full_url, "method": req.get_method(), "headers": {k.lower(): v for k, v in req.header_items()}, "body": json.loads(req.data) if req.data else None})
        if fail: raise urllib.error.HTTPError(req.full_url, fail, "err", {}, io.BytesIO(b'{"error":"stubbed failure"}'))
        return R(canned)
    old_env, old_argv, old_open = dict(os.environ), sys.argv, urllib.request.urlopen
    for k in ("XAI_API_KEY", "XAI_SIP_USER", "XAI_SIP_PASS", "DIDWW_SIP_USERNAME", "DIDWW_SIP_PASSWORD"):
        os.environ.pop(k, None)
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

K = {"XAI_API_KEY": "k"}
NUM = "+15105550100"
DIDWW7 = ["46.19.209.14/32", "46.19.210.14/32", "46.19.212.14/32", "46.19.213.14/32", "46.19.214.14/32", "46.19.215.14/32", "185.238.173.14/32"]

# --- webhook path (own backend) ---
reqs, out, code = run_script(["--number", "+33144556677", "--webhook", "https://h.example/xai", "--sip-user", "u", "--sip-pass", "p", "--allow-ip", "1.2.3.4", "--out", (F1 := out_file())], K, {"phone_number": {"phone_number_id": "phone_1"}, "webhook": {"webhook_id": "w", "dispatch_signing_secret": "whsec_TOPSECRET"}, "notes": "n" * 2000})
b = reqs[0]["body"] if reqs else {}; sa = b.get("sip_auth", {})
check("POST /v2/phone-numbers with Bearer key", reqs and reqs[0]["method"] == "POST" and reqs[0]["url"] == "https://api.x.ai/v2/phone-numbers" and reqs[0]["headers"].get("authorization") == "Bearer k")
check("origin byo_trunk", b.get("origin") == "byo_trunk", repr(b.get("origin")))
check("webhook is an object with url, no agent_id", isinstance(b.get("webhook"), dict) and b["webhook"].get("url") == "https://h.example/xai" and "agent_id" not in b, repr(b.get("webhook")))
check("sip_auth uses auth_username/auth_password and keeps allowed_addresses", sa.get("auth_username") == "u" and sa.get("auth_password") == "p" and sa.get("allowed_addresses") == ["1.2.3.4"], json.dumps(sa))
check("tells the user the signing secret is shown only once", "only once" in out.lower())
check("secret is not printed; the screen shows a redacted copy", "whsec_TOPSECRET" not in out and '"dispatch_signing_secret": "***"' in out, out[:200])
saved = json.load(open(F1)) if os.path.exists(F1) else {}
check("full response saved untruncated with the secret", saved.get("webhook", {}).get("dispatch_signing_secret") == "whsec_TOPSECRET" and len(saved.get("notes", "")) == 2000)
check("response file is mode 0600", os.path.exists(F1) and stat.S_IMODE(os.stat(F1).st_mode) == 0o600, oct(os.stat(F1).st_mode) if os.path.exists(F1) else "missing")
reqs, out, code = run_script(["--number", NUM, "--webhook", "https://h.example/x", "--sip-user", "u", "--sip-pass", "p", "--out", F1], K, {})
check("refuses to overwrite an existing response file", code != 0 and not reqs and "exists" in out, out[-120:])
reqs, out, code = run_script(["--number", NUM, "--webhook", "https://h.example/x", "--sip-user", "u", "--out", out_file()], dict(K, XAI_SIP_PASS="envpass"), {})
check("SIP password can come from XAI_SIP_PASS", code == 0 and reqs and reqs[0]["body"]["sip_auth"].get("auth_password") == "envpass", out[-120:])
reqs, out, code = run_script(["--number", NUM, "--webhook", "http://h.example/x", "--sip-user", "u", "--sip-pass", "p", "--out", out_file()], K, {})
check("refuses a plain http:// webhook URL", code != 0 and not reqs, out[-120:])

# --- agent path (console voice agent, DIDWW's guide) ---
reqs, out, code = run_script(["--number", NUM, "--agent", "agent_AbC123", "--sip-user", "trunkuser", "--sip-pass", "S3cretPass"], K, {"phone_number": {"phone_number_id": "phone_X", "sip_host": "sip.voice.x.ai", "agent_id": "agent_AbC123"}})
b = reqs[0]["body"] if reqs else {}
check("--agent sends agent_id and no webhook", b.get("agent_id") == "agent_AbC123" and "webhook" not in b and b.get("phone_number") == NUM, json.dumps(b))
check("--agent writes no response file (no one-time secret)", not os.path.exists(os.path.join(os.getcwd(), "xai-15105550100.json")))
check("password never printed; output names the DIDWW trunk settings", "S3cretPass" not in out and "sip.voice.x.ai" in out and "+{DID}" in out and "5061" in out and "TLS" in out, out[-300:])
check("digest reminds to set the same pair on the inbound trunk's Authorization", "Authorization" in out)
envf = os.path.join(TMP, "trunk.env")
with open(envf, "w") as f:
    f.write("# outbound trunk\nDIDWW_SIP_USERNAME=fileuser\nDIDWW_SIP_PASSWORD=filepass\nXAI_API_KEY=filekey\n")
reqs, out, code = run_script(["--number", NUM, "--agent", "agent_AbC123", "--digest", "--env-file", envf], {}, {"phone_number": {}})
sa = reqs[0]["body"]["sip_auth"] if reqs else {}
check("--digest --env-file reads the outbound trunk pair and the key from the file", sa == {"auth_username": "fileuser", "auth_password": "filepass"} and reqs[0]["headers"].get("authorization") == "Bearer filekey", json.dumps(sa))
check("file password not printed", "filepass" not in out and "filekey" not in out)
reqs, out, code = run_script(["--number", NUM, "--agent", "agent_AbC123", "--digest", "--env-file", envf], {"XAI_API_KEY": "envkey"}, {"phone_number": {}})
check("--env-file does not override the environment", reqs and reqs[0]["headers"].get("authorization") == "Bearer envkey")
reqs, out, code = run_script(["--number", NUM, "--agent", "agent_AbC123", "--allow-didww"], K, {"phone_number": {}})
check("--allow-didww sets DIDWW's seven signaling IPs", reqs and reqs[0]["body"]["sip_auth"] == {"allowed_addresses": DIDWW7}, json.dumps(reqs[0]["body"]["sip_auth"]) if reqs else "")

# --- refusals before any API call ---
for name, argv, env in [
    ("refuses both --agent and --webhook", ["--number", NUM, "--agent", "agent_A", "--webhook", "https://h/x", "--allow-didww"], K),
    ("refuses neither --agent nor --webhook", ["--number", NUM, "--allow-didww"], K),
    ("refuses an agent ID without the agent_ prefix", ["--number", NUM, "--agent", "abc123", "--allow-didww"], K),
    ("refuses a number without the + sign", ["--number", "15105550100", "--agent", "agent_A", "--allow-didww"], K),
    ("refuses --sip-user without a password", ["--number", NUM, "--agent", "agent_A", "--sip-user", "u"], K),
    ("refuses --digest without a username in the environment", ["--number", NUM, "--agent", "agent_A", "--digest"], K),
    ("refuses to register with no SIP auth at all", ["--number", NUM, "--agent", "agent_A"], K),
    ("refuses --allow-ip 0.0.0.0/0", ["--number", NUM, "--agent", "agent_A", "--allow-ip", "0.0.0.0/0"], K),
    ("refuses a malformed --allow-ip", ["--number", NUM, "--agent", "agent_A", "--allow-ip", "not-an-ip"], K),
    ("refuses a misspelt flag", ["--number", NUM, "--agnet", "agent_A", "--allow-didww"], K),
    ("refuses without XAI_API_KEY", ["--number", NUM, "--agent", "agent_A", "--allow-didww"], {}),
]:
    reqs, out, code = run_script(argv, env, {})
    check(name, code != 0 and not reqs and "Traceback" not in out, out[-120:].strip())

# --- list, delete, help, errors ---
reqs, out, code = run_script(["--list"], K, {"phone_numbers": [{"phone_number_id": "phone_1", "phone_number": NUM}]})
check("--list: one GET /v2/phone-numbers", code == 0 and [(r["method"], r["url"]) for r in reqs] == [("GET", "https://api.x.ai/v2/phone-numbers")] and "phone_1" in out)
reqs, out, code = run_script(["--delete", "phone_1"], K, {})
check("--delete: one DELETE /v2/phone-numbers/<id>", code == 0 and [(r["method"], r["url"]) for r in reqs] == [("DELETE", "https://api.x.ai/v2/phone-numbers/phone_1")])
reqs, out, code = run_script(["--delete", "../x"], K, {})
check("--delete refuses an ID with path characters", code != 0 and not reqs)
reqs, out, code = run_script(["--help"], {}, {})
check("--help exits 0 without calling the API", code == 0 and not reqs and "Usage" in out)
reqs, out, code = run_script(["--number", NUM, "--agent", "agent_A", "--allow-didww"], K, {}, fail=422)
check("API error exits nonzero with the status, no traceback", code != 0 and "422" in out and "Traceback" not in out, out[-120:])

import shutil; shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
