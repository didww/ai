# DIDWW AI

AI development at DIDWW, in the open. MIT licensed.

## Skills

[`skills/`](skills/) holds Claude Code agent skills that put an AI voice agent on a DIDWW
phone number: a hub that picks the platform and does the universal DIDWW wiring, plus one
pairing skill per voice platform (ElevenLabs, Vapi, Retell, Ultravox, Vogent, OpenAI
Realtime, xAI Grok, LiveKit). Each skill is its own npm package:

```bash
npx didww-connect
npx didww-to-livekit
```

Straight from this repo: `npx skills add didww/ai --skill <name>`. The full table, folder
layout, tests and publishing notes are in [skills/README.md](skills/README.md).

## Related

- DIDWW MCP server for Claude and other agents: `https://api.didww.com/mcp` (OAuth sign-in).
- DIDWW API SDKs, OpenAPI specs and samples: the other repositories under [github.com/didww](https://github.com/didww).

License: MIT
