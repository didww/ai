# didww-to-openai-realtime

Agent skill: connect DIDWW phone numbers directly to OpenAI over SIP, as
automatically as the platform allows: incoming calls with the Realtime API
(with live-agent transfers) and outbound calls with GPT-Live. It asks which
setup you want first, because they share almost nothing. MCP-first where MCPs exist
(DIDWW's is OAuth, no keys), stdlib-only scripts where they do not, and
every irreversible or spending action is confirmation-gated. No
telemetry; plain markdown plus readable Python.

## Install

```bash
npx didww-to-openai-realtime
```

Straight from GitHub, no registry: `npx skills add didww/ai --skill didww-to-openai-realtime`.
From a clone of this repo: `./skills/didww-to-openai-realtime/install.sh`, or copy this folder to
`~/.claude/skills/didww-to-openai-realtime`. Restart Claude Code afterwards; the skill triggers on its own
when you mention DIDWW together with OpenAI Realtime or GPT-Live.

Every installer copies files and nothing else; an existing install is moved to
`~/.claude/skill-backups/`, never overwritten.

## Tests

`bash test.sh` in this folder: stdlib Python plus node, no network, no keys.

## Family

Hub: [didww-connect](https://github.com/didww/ai/tree/main/skills/didww-connect) picks the platform, does the universal DIDWW
wiring and ships the health monitor. All nine skills live in [didww/ai](https://github.com/didww/ai) under
`skills/`, each installable with `npx didww-to-<platform>`.
Companion for building the agent itself: voice-agent-telephony.

License: MIT
