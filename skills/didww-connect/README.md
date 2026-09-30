# didww-connect

Agent skill: connect a DIDWW phone number to any AI voice platform over SIP, as
automatically as the platform allows. MCP-first where MCPs exist
(DIDWW's is OAuth, no keys), stdlib-only scripts where they do not, and
every irreversible or spending action is confirmation-gated. No
telemetry; plain markdown plus readable Python.

## Install

```bash
npx didww-connect
```

Straight from GitHub, no registry: `npx skills add didww/ai --skill didww-connect`.
From a clone of this repo: `./skills/didww-connect/install.sh`, or copy this folder to
`~/.claude/skills/didww-connect`. Restart Claude Code afterwards; the skill triggers on its own
when you want a voice agent on a DIDWW number and have not picked a platform yet.

Every installer copies files and nothing else; an existing install is moved to
`~/.claude/skill-backups/`, never overwritten.

## Tests

`bash test.sh` in this folder: stdlib Python plus node, no network, no keys.

## Family

| Skill | Platform | Install |
|---|---|---|
| [didww-connect](https://github.com/didww/ai/tree/main/skills/didww-connect) | any platform (hub) | `npx didww-connect` |
| [didww-to-elevenlabs](https://github.com/didww/ai/tree/main/skills/didww-to-elevenlabs) | ElevenLabs | `npx didww-to-elevenlabs` |
| [didww-to-vapi](https://github.com/didww/ai/tree/main/skills/didww-to-vapi) | Vapi | `npx didww-to-vapi` |
| [didww-to-retell](https://github.com/didww/ai/tree/main/skills/didww-to-retell) | Retell | `npx didww-to-retell` |
| [didww-to-ultravox](https://github.com/didww/ai/tree/main/skills/didww-to-ultravox) | Ultravox | `npx didww-to-ultravox` |
| [didww-to-vogent](https://github.com/didww/ai/tree/main/skills/didww-to-vogent) | Vogent | `npx didww-to-vogent` |
| [didww-to-openai-realtime](https://github.com/didww/ai/tree/main/skills/didww-to-openai-realtime) | OpenAI Realtime | `npx didww-to-openai-realtime` |
| [didww-to-xai](https://github.com/didww/ai/tree/main/skills/didww-to-xai) | xAI Grok | `npx didww-to-xai` |
| [didww-to-livekit](https://github.com/didww/ai/tree/main/skills/didww-to-livekit) | LiveKit | `npx didww-to-livekit` |

All nine live in [didww/ai](https://github.com/didww/ai). Companion for building the agent itself: voice-agent-telephony.

License: MIT
