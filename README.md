# DIDWW AI

[![test](https://github.com/didww/ai/actions/workflows/test.yml/badge.svg)](https://github.com/didww/ai/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Open-source tools from [DIDWW](https://www.didww.com/) for building AI voice agents on real phone numbers: agent skills, documentation and the scripts that keep them tested and published.

| Directory | Contents |
|---|---|
| [`skills/`](skills/) | Nine Claude Code agent skills that connect a DIDWW number to an AI voice platform. Each is its own npm package. |
| [`docs/`](docs/) | Documentation pages for the skills, written for [doc.didww.com](https://doc.didww.com/). |
| [`scripts/`](scripts/) | Family-wide test and publish runners used by maintainers and CI. |

## Skills

| Skill | Platform | npm | What it automates |
|---|---|---|---|
| [didww-connect](skills/didww-connect) | Any (hub) | [![npm](https://img.shields.io/npm/v/didww-connect?label=)](https://www.npmjs.com/package/didww-connect) | Picks the platform, does the universal DIDWW wiring, ships the health monitor |
| [didww-to-elevenlabs](skills/didww-to-elevenlabs) | ElevenLabs | [![npm](https://img.shields.io/npm/v/didww-to-elevenlabs?label=)](https://www.npmjs.com/package/didww-to-elevenlabs) | MCP on both sides plus one number-import call |
| [didww-to-vapi](skills/didww-to-vapi) | Vapi | [![npm](https://img.shields.io/npm/v/didww-to-vapi?label=)](https://www.npmjs.com/package/didww-to-vapi) | BYO SIP trunk credential, number and assistant binding |
| [didww-to-retell](skills/didww-to-retell) | Retell AI | [![npm](https://img.shields.io/npm/v/didww-to-retell?label=)](https://www.npmjs.com/package/didww-to-retell) | Fully MCP-driven: agent, number import and binding in one call |
| [didww-to-ultravox](skills/didww-to-ultravox) | Ultravox | [![npm](https://img.shields.io/npm/v/didww-to-ultravox?label=)](https://www.npmjs.com/package/didww-to-ultravox) | Address-based routing and account SIP settings |
| [didww-to-vogent](skills/didww-to-vogent) | Vogent | [![npm](https://img.shields.io/npm/v/didww-to-vogent?label=)](https://www.npmjs.com/package/didww-to-vogent) | SIP import plus one documented dashboard step |
| [didww-to-openai-realtime](skills/didww-to-openai-realtime) | OpenAI Realtime | [![npm](https://img.shields.io/npm/v/didww-to-openai-realtime?label=)](https://www.npmjs.com/package/didww-to-openai-realtime) | Direct SIP to the Realtime API with a generated webhook backend |
| [didww-to-xai](skills/didww-to-xai) | xAI Grok | [![npm](https://img.shields.io/npm/v/didww-to-xai?label=)](https://www.npmjs.com/package/didww-to-xai) | Number registration with digest auth, per-call session control |
| [didww-to-livekit](skills/didww-to-livekit) | LiveKit | [![npm](https://img.shields.io/npm/v/didww-to-livekit?label=)](https://www.npmjs.com/package/didww-to-livekit) | Inbound trunk, dispatch rule and optional outbound trunk for a LiveKit worker |

### Install

Each skill installs into `~/.claude/skills/<name>/` with one command, then triggers on its own when you mention DIDWW together with its platform:

```bash
npx didww-connect
npx didww-to-livekit
```

Straight from this repository, without the npm registry: `npx skills add didww/ai --skill <name>`, or `npx skills add didww/ai --list` to see all nine. Restart Claude Code after installing.

### Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code) with the [DIDWW MCP](https://doc.didww.com/mcp/index.html) connected (`claude mcp add --scope user --transport http didww https://api.didww.com/mcp`, then `/mcp` to sign in). The skills do all carrier-side work through it, under your own account permissions.
- Node.js 16.7 or later for the installer; Python 3 for the skill scripts, which use the standard library only.
- An account on the voice platform you pair with. Each skill's README lists what it needs.

The installers copy files and nothing else. The skills store no credentials; platform API keys are read from environment variables when a script runs.

## Development

```bash
bash scripts/test.sh            # every skill's checks: stdlib Python plus node, no network, no keys
bash scripts/publish.sh         # publish all nine to npm (after npm login)
bash scripts/publish.sh didww-to-vapi   # publish one
```

GitHub Actions runs the same tests on every push and pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for the skill layout, versioning and how to add a platform, and [CHANGELOG.md](CHANGELOG.md) for releases.

## Related

- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector for Claude, ChatGPT and other agents, at `https://api.didww.com/mcp`.
- [DIDWW documentation](https://doc.didww.com/): SIP trunking, phone numbers, integrations and the API.
- [DIDWW API SDKs](https://github.com/didww): the other repositories in this organization.

## License

[MIT](LICENSE).
