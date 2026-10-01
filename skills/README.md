# Skills

Claude Code skills that put an AI voice agent on a DIDWW phone number. One hub skill picks
the platform and does the universal DIDWW wiring (number, inbound and outbound SIP trunks,
digest auth, spend limits, verification calls); eight pairing skills cover one voice platform
each, as automatically as that platform's API and MCP allow.

| Skill | Platform | Install | What it does |
|---|---|---|---|
| [didww-connect](didww-connect) | any platform (hub) | `npx didww-connect` | Connect a DIDWW phone number to ANY AI voice platform: helps choose the platform, then wires the SIP trunk pair and number. |
| [didww-to-elevenlabs](didww-to-elevenlabs) | ElevenLabs | `npx didww-to-elevenlabs` | Connect a DIDWW phone number to an ElevenLabs voice agent over SIP, as automatically as both platforms allow. |
| [didww-to-vapi](didww-to-vapi) | Vapi | `npx didww-to-vapi` | Connect a DIDWW phone number to a Vapi assistant over BYO SIP trunking, as automatically as Vapi allows. |
| [didww-to-retell](didww-to-retell) | Retell | `npx didww-to-retell` | Connect a DIDWW phone number to a Retell AI agent over custom telephony, with full MCP automation: Retell's official MCP can create agents AND import numbers. |
| [didww-to-ultravox](didww-to-ultravox) | Ultravox | `npx didww-to-ultravox` | Connect a DIDWW phone number to an Ultravox Realtime voice agent over SIP. |
| [didww-to-vogent](didww-to-vogent) | Vogent | `npx didww-to-vogent` | Connect a DIDWW phone number to a Vogent voice agent over SIP import. |
| [didww-to-openai-realtime](didww-to-openai-realtime) | OpenAI Realtime | `npx didww-to-openai-realtime` | Point a DIDWW phone number directly at OpenAI's Realtime API over SIP, with a generated webhook backend for call control. |
| [didww-to-xai](didww-to-xai) | xAI Grok | `npx didww-to-xai` | Point a DIDWW phone number at xAI's Grok voice over SIP. |
| [didww-to-livekit](didww-to-livekit) | LiveKit | `npx didww-to-livekit` | Connect a DIDWW phone number to a LiveKit Agents worker over SIP, on LiveKit Cloud or self-hosted: inbound trunk, dispatch rule to a named agent, optional outbound trunk. |

## Install

Each skill is its own npm package and installs into `~/.claude/skills/<name>/`:

```bash
npx didww-connect
npx didww-to-livekit
```

Straight from GitHub, no registry: `npx skills add didww/ai --skill didww-to-livekit`
(or `npx skills add didww/ai --list` to see all nine). From a clone: `./skills/<name>/install.sh`,
or copy `skills/<name>` to `~/.claude/skills/<name>`. Restart Claude Code afterwards; the skills
trigger on their own when you mention DIDWW together with a platform.

Every installer copies files and nothing else; an existing install is moved to
`~/.claude/skill-backups/`, never overwritten. Carrier-side automation uses the DIDWW MCP
(`https://api.didww.com/mcp`, OAuth sign-in); nothing here stores credentials.

## Layout

```
skills/<name>/
  SKILL.md          the skill (frontmatter description drives triggering)
  scripts/          one stdlib Python script per REST gap; --help on each
  references/       hub only: where keys and billing live per provider
  bin/install.js    npx installer (--dry-run, --dest DIR, --help)
  install.sh        same thing for a clone
  tests/            request-shape tests against stubbed HTTP, no keys
  package.json      npm name = skill name
```

## Tests

From the repo root, `bash test.sh` runs every skill's checks (stdlib Python plus node, no network, no keys).
GitHub Actions runs the same on every push.

## Publishing

`npm login` once, then from the repo root `bash publish.sh` for all nine or `bash publish.sh didww-to-vapi`
for one. Bump the `version` in that skill's `package.json` first; npm refuses to overwrite
a published version.

Companion skill for building the agent itself: voice-agent-telephony.

License: MIT
