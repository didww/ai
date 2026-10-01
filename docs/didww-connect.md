# DIDWW Connect skill

Use the **didww-connect** skill with **Claude Code** to put an AI voice agent on a DIDWW phone number when you have not yet chosen a voice platform. The skill compares the supported platforms against what matters to you, performs the DIDWW-side wiring that is identical for every platform, and hands over to the dedicated `didww-to-<platform>` skill once a platform is chosen.

- Choose between ElevenLabs, Vapi, Retell, Ultravox, Vogent, OpenAI Realtime, xAI Grok and LiveKit in one question.
- Configure the DIDWW number, inbound and outbound SIP trunks, digest authentication and spend controls through the DIDWW MCP.
- Monitor the finished connection with a read-only health check that runs from cron.

## How the skill works

A skill is a folder of instructions and scripts that Claude Code reads when the conversation matches its description. This one triggers when you ask for a voice agent on a DIDWW number without naming a platform, ask which platform to use, or name a platform that has no dedicated skill installed.

| Part | What it holds |
|---|---|
| `SKILL.md` | The platform comparison, the universal DIDWW wiring, the SIP ingress address of every platform, and when to hand over to a dedicated skill. |
| `references/panels-and-billing.md` | Where each provider keeps API keys and billing, which free tiers exist, and the billing behaviour that catches people out. Read before the agent sends you into any dashboard. |
| `scripts/monitor.py` | Read-only health check: DIDWW balance against a threshold, DID status, trunk presence. Exit code 1 on any warning. |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage trunks and numbers under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- An idea of what the agent should do and what matters most: ease of setup, voice quality, EU region, bring-your-own model, developer control, or enterprise procurement.

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-connect
```

It copies the skill into `~/.claude/skills/didww-connect/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-connect
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

Describe the goal without naming a platform, for example:

```text
I want an AI receptionist on my DIDWW number +33 1 44 55 66 77. Which platform should I use?
```

The skill asks one question, maps the answer to a platform, and tells you the automation ceiling of that choice before anything is configured.

| What matters most | Platform | Automation ceiling |
|---|---|---|
| Easiest overall, best voices, OAuth on both sides | ElevenLabs | MCP on both sides; one REST import call |
| API-first, EU region, bring your own model keys | Vapi | REST script; Vapi's MCP is read-only for numbers |
| Maximum MCP automation, one-call setup | Retell | Retell's MCP imports numbers and creates agents |
| Richest call transfers, own speech model | Ultravox | REST; address-based routing, no number import |
| Small and simple | Vogent | REST import; agent binding is one dashboard click |
| You own the agent code, minimal stack | OpenAI Realtime or xAI Grok | A webhook backend is required; not no-code |
| Any STT, LLM and TTS combination, open source | LiveKit | REST script creates trunk and dispatch rule; the worker is your code |
| Data control, own servers | LiveKit self-hosted | Same skill; you run the SIP service |
| Enterprise procurement | Bland, Synthflow, Regal | Sales-gated; no same-day setup |

> [!NOTE]
> When the dedicated skill for the chosen platform is installed, the hub hands over to it. The dedicated skills carry the platform's connect script, exact API request shapes and a failure map for that pairing. Install them with `npx didww-to-<platform>`.

## Step 3. What gets configured

### DIDWW side

All DIDWW changes go through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool.

- **Inbound SIP trunk.** Host and port are the chosen platform's SIP ingress (see the table below), digest authentication is preferred over IP filtering, and media encryption matches the platform's setting. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Created for this connection. DIDWW generates the username and password; the host is the one nearest to the platform's region: `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `nyc.us.out.didww.com` or `sg.out.didww.com`. The agent passes these credentials to the platform side.
- **Spend controls.** A 24-hour spend limit of 10 to 50 USD and channel limits matching the expected concurrency are set before the first call. The defaults are too high for a test agent.
- **Number.** An existing DID is confirmed, or one is bought. For registration-required countries the skill says so before promising a date.

### Platform SIP ingress addresses

| Platform | DIDWW inbound trunk destination | Notes |
|---|---|---|
| ElevenLabs | `sip.rtc.elevenlabs.io`, port 5060 | TCP or TLS, digest auth |
| Vapi | `{credential_id}.sip.vapi.ai` (EU: `.sip.eu.vapi.ai`) | Create the Vapi credential first; allow Vapi's signaling IPs |
| Retell | `sip.retellai.com` | TCP |
| Ultravox | The account's own SIP domain from `GET /api/sip` | Address-based routing to `agent_<id>@<domain>` |
| Vogent | `sip.vogent.ai` | Digest auth |
| OpenAI Realtime | `sip:{project_id}@sip.api.openai.com;transport=tls` | TLS and SRTP mandatory; EU host `sip-eu.api.openai.com` |
| xAI Grok | `sip:{number}@sip.voice.x.ai;transport=tls` | Digest auth set when the number is registered with xAI |
| LiveKit | `sip:{subdomain}.sip.livekit.cloud` | 5060 TCP/UDP or 5061 TLS; region-pinned `{subdomain}.{eu|us|uk|india|japan|aus|canada|sa}.sip.livekit.cloud`; numbers carry the `+` |

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone reaches the agent.
2. One outbound call shows the DID as caller ID.
3. One transfer, if a transfer destination was configured.

## Step 5. Monitor the connection

The skill offers monitoring at the end of every build. `scripts/monitor.py` is read-only and uses a DIDWW API key:

```bash
DIDWW_API_KEY=... python3 ~/.claude/skills/didww-connect/scripts/monitor.py --min-balance 20 --number +33144556677
```

It checks the balance against the threshold, lists DIDs and warns about blocked or awaiting-registration numbers, and warns when no inbound trunk exists. The exit code is 1 on any warning, so it fits cron, CI or a scheduled task; daily is the right cadence. A warning is almost always fixed by one of: top up a balance, complete a registration document, or re-enable a cancelled add-on.

> [!NOTE]
> With the DIDWW MCP connected, the same checks run as tool calls (`get_balance`, `list_dids`, `list_trunks`) inside a conversation, without the script or an API key.

## Keys, billing and safety

- **Platform credentials.** Each platform's key location and billing page are in `references/panels-and-billing.md`. Where a platform offers an OAuth MCP, the skill prefers it over API keys.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- Dedicated pairing skills: [ElevenLabs](didww-to-elevenlabs.md), [Vapi](didww-to-vapi.md), [Retell](didww-to-retell.md), [Ultravox](didww-to-ultravox.md), [Vogent](didww-to-vogent.md), [OpenAI Realtime](didww-to-openai-realtime.md), [xAI Grok](didww-to-xai.md), [LiveKit](didww-to-livekit.md).
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-connect`](https://github.com/didww/ai/tree/main/skills/didww-connect) in the didww/ai repository. Package: [npmjs.com/package/didww-connect](https://www.npmjs.com/package/didww-connect).
- [DIDWW Connect](index.md): the hub skill that compares all supported platforms.
