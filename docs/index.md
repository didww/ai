# AI agent skills

DIDWW publishes a family of **agent skills** for **Claude Code** that put an AI voice agent on a DIDWW phone number. A skill is a folder with a `SKILL.md` instruction file and a small script. Claude Code reads it when your request matches the skill's description, and then does the work: the DIDWW side through the [DIDWW MCP](https://doc.didww.com/mcp/index.html) under your own account, the voice platform side through that platform's MCP or API.

- One hub skill compares the supported platforms and performs the DIDWW wiring that is the same for all of them.
- Eight pairing skills each cover one platform end to end, with the platform's exact API calls and a failure map for that pairing.
- Everything is open source under the MIT licence in the [didww/ai](https://github.com/didww/ai) repository.

| Skill | Platform | Install | What it automates |
|---|---|---|---|
| [didww-connect](didww-connect.md) | Any (hub) | `npx didww-connect` | Platform choice, universal DIDWW wiring, health monitor |
| [didww-to-elevenlabs](didww-to-elevenlabs.md) | ElevenLabs | `npx didww-to-elevenlabs` | MCP on both sides plus one import call |
| [didww-to-vapi](didww-to-vapi.md) | Vapi | `npx didww-to-vapi` | REST script; credential before trunk |
| [didww-to-retell](didww-to-retell.md) | Retell AI | `npx didww-to-retell` | Fully MCP-driven when Retell's MCP is connected |
| [didww-to-ultravox](didww-to-ultravox.md) | Ultravox | `npx didww-to-ultravox` | Address-based routing; no number import |
| [didww-to-vogent](didww-to-vogent.md) | Vogent | `npx didww-to-vogent` | REST import plus one dashboard click |
| [didww-to-openai-realtime](didww-to-openai-realtime.md) | OpenAI Realtime | `npx didww-to-openai-realtime` | Direct SIP; you run a webhook backend |
| [didww-to-xai](didww-to-xai.md) | xAI Grok | `npx didww-to-xai` | Direct SIP with number registration; you run a backend |
| [didww-to-livekit](didww-to-livekit.md) | LiveKit | `npx didww-to-livekit` | Trunk and dispatch rule; you run the worker |

## Before you begin

- An active DIDWW account with a DID number or a balance to buy one.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in. Node.js 16.7 or later for the installer; Python 3 for the scripts, which use the standard library only.
- The DIDWW MCP connected in Claude Code:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).

- An account on the voice platform you intend to use. Each skill page lists what it needs.

## Install a skill

```bash
npx didww-to-elevenlabs
```

The installer copies the skill into `~/.claude/skills/<name>/` and does nothing else. An existing copy is moved to `~/.claude/skill-backups/` first. Restart Claude Code; the skill then triggers on its own when you mention DIDWW together with its platform. Without the npm registry, `npx skills add didww/ai --skill <name>` installs the same files from GitHub, and `npx skills add didww/ai --list` shows all nine.

## What every skill does on the DIDWW side

The carrier-side wiring is identical for every platform and always runs through the DIDWW MCP:

1. **Number.** Buy or confirm the DID. Registration-required countries add a verification wait.
2. **Inbound trunk.** Host set to the platform's SIP ingress, digest authentication preferred, media encryption matched to the platform. The DID is assigned to the trunk.
3. **Outbound trunk.** Created per connection; DIDWW generates the credentials. The host nearest the platform's region is used: `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `nyc.us.out.didww.com` or `sg.out.didww.com`.
4. **Spend controls.** A 24-hour spend limit of 10 to 50 USD and channel limits set before the first call.
5. **Verification.** One inbound call from a mobile phone, one outbound call checking caller ID, one transfer if configured.

> [!NOTE]
> Claude Code asks for confirmation before each MCP tool call unless you have allowed that tool, and the DIDWW MCP acts only within the permissions of the account you signed in with. The skills store no credentials; platform API keys are read from environment variables when a script runs.

> [!IMPORTANT]
> Two prepaid balances are involved, DIDWW's and the platform's, and either reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** and switch on the **Low Balance Notification**, which is off by default, and consider **Auto-charge**.

## Choosing a platform

| What matters most | Skill |
|---|---|
| Easiest overall, best voices, OAuth on both sides | [didww-to-elevenlabs](didww-to-elevenlabs.md) |
| API-first, EU region, bring your own model keys | [didww-to-vapi](didww-to-vapi.md) |
| Maximum MCP automation | [didww-to-retell](didww-to-retell.md) |
| Richest call transfers, own speech model | [didww-to-ultravox](didww-to-ultravox.md) |
| Small and simple | [didww-to-vogent](didww-to-vogent.md) |
| You own the agent code, minimal stack | [didww-to-openai-realtime](didww-to-openai-realtime.md) or [didww-to-xai](didww-to-xai.md) |
| Any STT, LLM and TTS combination, including Claude as the model | [didww-to-livekit](didww-to-livekit.md) |
| Not sure yet | [didww-connect](didww-connect.md) |

## Additional resources

- [Integrations](https://doc.didww.com/integrations/index.html): manual guides for ElevenLabs, Retell AI, Vapi and other platforms.
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html).
- [DIDWW MCP](https://doc.didww.com/mcp/index.html).
- Source, tests and issue tracker: [github.com/didww/ai](https://github.com/didww/ai).

Platform details in these skills were verified in August 2026 (LiveKit: September 2026).
