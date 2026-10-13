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

DIDWW_IPS = ["46.19.209.14", "46.19.210.14", "46.19.212.14", "46.19.213.14", "46.19.214.14", "46.19.215.14", "185.238.173.14"]
reqs, out, code = run_script(["--number", "+33144556677", "--didww-host", "fra.eu.out.didww.com", "--didww-user", "u", "--didww-pass", "p", "--assistant", "asst_1"], {"VAPI_API_KEY": "k"}, {"id": "cred_1"})
h = reqs[0]["headers"] if reqs else {}
check("sends a non-Python User-Agent (Cloudflare 1010 blocks urllib's default)", "user-agent" in h and not h["user-agent"].lower().startswith("python"), h.get("user-agent"))
check("three calls: outbound credential, inbound credential, phone number (US API)", [(r["method"], r["url"]) for r in reqs] == [("POST", "https://api.vapi.ai/credential"), ("POST", "https://api.vapi.ai/credential"), ("POST", "https://api.vapi.ai/phone-number")], [(r["method"], r["url"]) for r in reqs])
ob, ib, nb = (reqs[0]["body"], reqs[1]["body"], reqs[2]["body"]) if len(reqs) == 3 else ({}, {}, {})
check("outbound credential: DIDWW endpoint gateway, outbound only, digest auth", ob.get("gateways") == [{"ip": "fra.eu.out.didww.com", "port": 5060, "inboundEnabled": False, "outboundEnabled": True, "outboundProtocol": "udp"}] and ob.get("outboundAuthenticationPlan") == {"authUsername": "u", "authPassword": "p"}, json.dumps(ob)[:300])
check("inbound credential: one inbound-only /32 gateway per DIDWW signaling IP (Vapi + DIDWW guides)", [g["ip"] for g in ib.get("gateways", [])] == DIDWW_IPS and all(g["inboundEnabled"] and not g["outboundEnabled"] and g["netmask"] == 32 and g["port"] == 5060 for g in ib.get("gateways", [])) and ib.get("outboundAuthenticationPlan", {}).get("authUsername") == "u", json.dumps(ib)[:300])
check("number: byo-phone-number, E.164 WITH +, E164 check on, bound to the inbound credential + assistant", nb == {"provider": "byo-phone-number", "name": "DIDWW +33144556677", "number": "+33144556677", "numberE164CheckEnabled": True, "credentialId": "cred_1", "assistantId": "asst_1"}, json.dumps(nb))
check("prints DIDWW inbound trunk settings: sip.vapi.ai, max_transfers, Authorization", "host sip.vapi.ai, port 5060" in out and "max_transfers 1" in out and "auth_enabled true" in out)
check("prints outbound Allowed SIP IPs: Vapi US + DIDWW's own", "44.229.228.186/32, 44.238.177.138/32, 46.19.209.14/32" in out and "185.238.173.14/32" in out)
reqs, out, code = run_script(["--number", "+33144556677", "--eu", "--transport", "tls"], {"VAPI_API_KEY": "k"}, {"id": "cred_2"})
check("--eu calls api.eu.vapi.ai and points DIDWW at sip.eu.vapi.ai", reqs and all(r["url"].startswith("https://api.eu.vapi.ai/") for r in reqs) and "host sip.eu.vapi.ai, port 5061, transport_protocol TLS" in out, [r["url"] for r in reqs])
check("inbound only: no outbound credential, no auth plan, gateways on 5061 for TLS", len(reqs) == 2 and "outboundAuthenticationPlan" not in reqs[0]["body"] and reqs[0]["body"]["gateways"][0]["port"] == 5061 and "auth_enabled" not in out and "Inbound only" in out)
reqs, out, code = run_script(["--number", "+33144556677", "--didww-host", "h", "--didww-user", "u"], {"VAPI_API_KEY": "k"}, {"id": "c"})
check("partial outbound flags refused before any API call", code != 0 and not reqs and "all of --didww-host" in out)
reqs, out, code = run_script(["--number", "+33144556677", "--didww-host", "h", "--didww-user", "u"], {"VAPI_API_KEY": "k", "DIDWW_TRUNK_PASS": "envp"}, {"id": "c"})
check("password can come from DIDWW_TRUNK_PASS", code == 0 and reqs and reqs[0]["body"]["outboundAuthenticationPlan"]["authPassword"] == "envp")
reqs, out, code = run_script(["--number", "33144556677"], {"VAPI_API_KEY": "k"}, {"id": "c"})
check("number without + refused (Vapi's guide imports E.164 with +)", code != 0 and not reqs)
reqs, out, code = run_script(["--rotate", "cred_A", "--rotate", "cred_B", "--didww-user", "u2", "--didww-pass", "p2"], {"VAPI_API_KEY": "k"}, {"id": "cred_A"})
check("--rotate PATCHes /credential/{id} outboundAuthenticationPlan for each id", [(r["method"], r["url"]) for r in reqs] == [("PATCH", "https://api.vapi.ai/credential/cred_A"), ("PATCH", "https://api.vapi.ai/credential/cred_B")] and all(r["body"] == {"provider": "byo-sip-trunk", "outboundAuthenticationPlan": {"authUsername": "u2", "authPassword": "p2"}} for r in reqs), [(r["method"], r["url"]) for r in reqs])
reqs, out, code = run_script(["--rotate", "cred_A"], {"VAPI_API_KEY": "k"}, {})
check("--rotate without credentials refused", code != 0 and not reqs)
reqs, out, code = run_script(["--number", "+33144556677", "--updte"], {"VAPI_API_KEY": "k"}, {})
check("unknown flag refused instead of ignored", code != 0 and not reqs and "Bad argument" in out)
reqs, out, code = run_script(["--number", "+33144556677", "--didww-host", "h", "--didww-user", "u", "--didww-pass", "p"], {"VAPI_API_KEY": "k"}, {"id": "c"}, fail=401)
check("API error exits nonzero with the status, no traceback", code != 0 and "401" in out and "Traceback" not in out, out[-120:])

print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
