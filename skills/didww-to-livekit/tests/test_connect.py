#!/usr/bin/env python3
"""Tests for didww-to-livekit/scripts/connect.py with stubbed HTTP."""
import base64, contextlib, hashlib, hmac, io, json, os, runpy, sys, urllib.error, urllib.request
sys.dont_write_bytecode = True
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "connect.py"); results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
ENV = {"LIVEKIT_URL": "https://myproj.livekit.cloud", "LIVEKIT_API_KEY": "APIkey123", "LIVEKIT_API_SECRET": "s3cret"}
def canned_for(url):
    m = url.rsplit("/", 1)[-1]
    return {"CreateSIPInboundTrunk": {"sipTrunkId": "ST_in1", "name": "n"},
            "CreateSIPDispatchRule": {"sipDispatchRuleId": "SDR_1"},
            "CreateSIPOutboundTrunk": {"sipTrunkId": "ST_out1"},
            "ListSIPInboundTrunk": {"items": [{"sipTrunkId": "ST_in1", "name": "DIDWW +33144556677", "numbers": ["+33144556677"], "authUsername": "u"}]},
            "ListSIPDispatchRule": {"items": [{"sipDispatchRuleId": "SDR_1", "name": "DIDWW +33144556677", "trunkIds": ["ST_in1"], "roomConfig": {"agents": [{"agentName": "my-agent"}]}}]},
            "ListSIPOutboundTrunk": {"items": [{"sipTrunkId": "ST_out1", "address": "fra.eu.out.didww.com", "numbers": ["+33144556677"]}]}}.get(m, {})
def run(argv, env=ENV, fail=None):
    reqs = []
    class R:
        def __init__(s, d): s.d = json.dumps(d).encode()
        def read(s): return s.d
        def __enter__(s): return s
        def __exit__(s, *a): pass
    def fake_urlopen(req, timeout=None):
        reqs.append({"url": req.full_url, "method": req.get_method(), "headers": {k.lower(): v for k, v in req.header_items()}, "body": json.loads(req.data) if req.data else None})
        if fail: raise urllib.error.HTTPError(req.full_url, fail, "err", {}, io.BytesIO(b'{"msg":"invalid token"}'))
        return R(canned_for(req.full_url))
    old_env, old_argv, old_open = dict(os.environ), sys.argv, urllib.request.urlopen
    for k in ENV: os.environ.pop(k, None)
    os.environ.update(env); sys.argv = [P] + argv; urllib.request.urlopen = fake_urlopen
    out = io.StringIO(); code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out): runpy.run_path(P, run_name="__main__")
    except SystemExit as e:  # sys.exit("msg") prints msg to stderr only at interpreter exit; mirror that here
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        if isinstance(e.code, str): out.write(e.code + "\n")
    finally:
        urllib.request.urlopen = old_open; sys.argv = old_argv; os.environ.clear(); os.environ.update(old_env)
    return reqs, out.getvalue(), code
def b64d(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
def jwt(auth):
    tok = auth.split(" ", 1)[1]; h, p, sig = tok.split(".")
    ok = hmac.compare_digest(b64d(sig), hmac.new(b"s3cret", f"{h}.{p}".encode(), hashlib.sha256).digest())
    return ok, json.loads(b64d(h)), json.loads(b64d(p))
FULL = ["--number", "+33144556677", "--agent", "my-agent", "--inbound-user", "iu", "--inbound-pass", "ip",
        "--outbound-host", "fra.eu.out.didww.com", "--outbound-user", "ou", "--outbound-pass", "op"]
M = "https://myproj.livekit.cloud/twirp/livekit.SIP/"

reqs, out, code = run(["--help"], env={})
check("--help exits 0 without env or API calls", code == 0 and not reqs and "Usage" in out)
reqs, out, code = run(FULL, env={})
check("refuses without LIVEKIT_URL/KEY/SECRET", code != 0 and not reqs)
reqs, out, code = run(FULL)
check("three Twirp POSTs in order: inbound trunk, dispatch rule, outbound trunk",
      [r["url"] for r in reqs] == [M + m for m in ("CreateSIPInboundTrunk", "CreateSIPDispatchRule", "CreateSIPOutboundTrunk")], [r["url"] for r in reqs])
t = reqs[0]["body"].get("trunk", {}) if reqs else {}
check("inbound trunk: E.164 number + digest auth_username/auth_password", t.get("numbers") == ["+33144556677"] and t.get("auth_username") == "iu" and t.get("auth_password") == "ip", json.dumps(t))
check("inbound trunk: SRTP allowed by default", t.get("media_encryption") == "SIP_MEDIA_ENCRYPT_ALLOW", repr(t.get("media_encryption")))
d = reqs[1]["body"].get("dispatch_rule", {}) if len(reqs) > 1 else {}
check("dispatch rule: bound to the new trunk id, one room per call, agent by name",
      d.get("trunk_ids") == ["ST_in1"] and "room_prefix" in d.get("rule", {}).get("dispatch_rule_individual", {}) and d.get("room_config", {}).get("agents", [{}])[0].get("agent_name") == "my-agent", json.dumps(d))
o = reqs[2]["body"].get("trunk", {}) if len(reqs) > 2 else {}
check("outbound trunk: DIDWW host only, TCP by default, DIDWW auth pair, number",
      o.get("address") == "fra.eu.out.didww.com" and o.get("transport") == "SIP_TRANSPORT_TCP" and o.get("auth_username") == "ou" and o.get("auth_password") == "op" and o.get("numbers") == ["+33144556677"], json.dumps(o))
ok, h, p = jwt(reqs[0]["headers"]["authorization"]) if reqs else (False, {}, {})
check("JWT: HS256 signed with the API secret, iss = key, sip.admin grant, short expiry",
      ok and h.get("alg") == "HS256" and p.get("iss") == "APIkey123" and p.get("sip", {}).get("admin") is True and 0 < p.get("exp", 0) - p.get("nbf", 0) <= 3600, json.dumps(p))
check("all requests: JSON body, non-Python User-Agent",
      bool(reqs) and all("json" in r["headers"].get("content-type", "") and not r["headers"].get("user-agent", "python").lower().startswith("python") for r in reqs))
check("prints the ids and the LiveKit SIP URI for the DIDWW trunk", "ST_in1" in out and "SDR_1" in out and "ST_out1" in out and "sip:myproj.sip.livekit.cloud" in out, out[-300:])
reqs, out, code = run(FULL, env={**ENV, "LIVEKIT_URL": "wss://myproj.livekit.cloud/"})
check("wss:// project URL becomes the https API host", bool(reqs) and reqs[0]["url"].startswith("https://myproj.livekit.cloud/twirp"))
reqs, out, code = run(FULL + ["--transport", "TLS", "--srtp", "require"])
check("--transport TLS + --srtp require map to the LiveKit enums on both trunks",
      len(reqs) == 3 and reqs[2]["body"]["trunk"]["transport"] == "SIP_TRANSPORT_TLS" and reqs[0]["body"]["trunk"]["media_encryption"] == "SIP_MEDIA_ENCRYPT_REQUIRE" and reqs[2]["body"]["trunk"]["media_encryption"] == "SIP_MEDIA_ENCRYPT_REQUIRE" and "5061" in out)
reqs, out, code = run(FULL + ["--transport", "sctp"])
check("unknown transport is rejected before any API call", code != 0 and not reqs)
reqs, out, code = run(FULL[:8])
check("without outbound flags only the inbound trunk and the rule are created", len(reqs) == 2 and code == 0)
reqs, out, code = run(FULL[:8] + ["--outbound-host", "fra.eu.out.didww.com"])
check("--outbound-host without credentials is refused", code != 0 and not reqs)
reqs, out, code = run(["--number", "+33144556677", "--agent", "a"])
check("refuses an inbound trunk with neither digest nor allowlist", code != 0 and not reqs)
reqs, out, code = run(["--number", "+33144556677", "--agent", "a", "--inbound-user", "u"])
check("refuses --inbound-user without --inbound-pass", code != 0 and not reqs)
reqs, out, code = run(["--number", "33144556677", "--agent", "a", "--inbound-user", "u", "--inbound-pass", "p"])
check("refuses a number without the + prefix (LiveKit matches E.164 exactly)", code != 0 and not reqs)
reqs, out, code = run(["--number", "+33144556677", "--inbound-user", "u", "--inbound-pass", "p"])
check("refuses without --agent", code != 0 and not reqs)
reqs, out, code = run(["--number", "+33144556677", "--agent", "a", "--allow-ip", "1.2.3.0/24", "--allow-ip", "5.6.7.8"])
t = reqs[0]["body"]["trunk"] if reqs else {}
check("--allow-ip alone: allowed_addresses sent, warns that Cloud enables it via support",
      t.get("allowed_addresses") == ["1.2.3.0/24", "5.6.7.8"] and "auth_username" not in t and "support" in out.lower(), out[-200:])
reqs, out, code = run(["--number", "+33144556677", "--agent", "a", "--inbound-user", "u", "--inbound-pass", "p", "--allow-ip", "1.2.3.4"])
t = reqs[0]["body"]["trunk"] if reqs else {}
check("digest and allowlist can be combined", t.get("auth_username") == "u" and t.get("allowed_addresses") == ["1.2.3.4"])
reqs, out, code = run(["--show"])
check("--show lists trunks and rules, creates nothing, prints the SIP URI",
      [r["url"].rsplit("/", 1)[-1] for r in reqs] == ["ListSIPInboundTrunk", "ListSIPDispatchRule", "ListSIPOutboundTrunk"] and code == 0 and "sip:myproj.sip.livekit.cloud" in out and "ST_in1" in out and "my-agent" in out and "fra.eu.out.didww.com" in out, out[-300:])
reqs, out, code = run(FULL, fail=401)
check("API error exits nonzero with status and body, no traceback", code != 0 and "401" in out and "invalid token" in out and "Traceback" not in out, out[-200:])
reqs, out, code = run([])
check("no args prints usage and exits nonzero", code != 0 and not reqs and "Usage" in out)
print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
