#!/usr/bin/env python3
"""Checks on the instructions themselves: facts confirmed on real calls that must not regress."""
import os, re, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..")
DOC = os.path.join(SKILL, "..", "..", "docs", "didww-to-elevenlabs.md")  # absent in the npm package
results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
texts = {f: open(os.path.join(SKILL, f)).read() for f in ("SKILL.md", "README.md")}
if os.path.exists(DOC):
    texts["docs/didww-to-elevenlabs.md"] = open(DOC).read()

# `claude mcp add` may wrap across lines in SKILL.md; join whitespace before matching.
adds = [(f, m.group(1)) for f, t in texts.items()
        for m in re.finditer(r"claude mcp add [^`]*?\belevenlabs (https?://[^\s`)]+)", re.sub(r"\s+", " ", t))]
check("every `claude mcp add ... elevenlabs` uses https://api.us.elevenlabs.io/v1/mcp (api.elevenlabs.io breaks OAuth sign-in)",
      adds and all(u == "https://api.us.elevenlabs.io/v1/mcp" for _, u in adds), adds)
skill = texts["SKILL.md"]
ips = ["46.19.209.14", "46.19.210.14", "46.19.212.14", "46.19.213.14", "46.19.214.14", "46.19.215.14", "185.238.173.14"]
check("SKILL.md lists DIDWW's seven inbound signaling IPs for the outbound trunk (transfers)", all(ip in skill for ip in ips), [ip for ip in ips if ip not in skill])
check("SKILL.md transfer steps: sip_refer, sip_uri, max_transfers, network protocol, --update",
      all(k in skill for k in ("sip_refer", "sip_uri", "max_transfers", "network_protocol_priority", "--update", "agents_update_transfer_to_number_tool")))
check("SKILL.md imports the number without the plus (DIDWW sends {DID})", "E.164 without the `+`" in re.sub(r"\s+", " ", skill))

print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)
