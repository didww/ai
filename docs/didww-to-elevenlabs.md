# DIDWW to ElevenLabs skill

Use the **didww-to-elevenlabs** skill with **Claude Code** to connect a DIDWW phone number to an **ElevenAgents** voice agent over SIP. The connection is one SIP trunk pair on the DIDWW side plus one number import on the ElevenLabs side; the skill drives both from a conversation.

- Route incoming calls from a DIDWW number to an ElevenLabs agent.
- Place outbound calls from the agent through DIDWW with the DIDWW number as caller ID.
- Import the number into ElevenLabs with matching digest credentials, and assign the agent.

This skill automates the steps described in the [ElevenLabs integration guide](https://doc.didww.com/integrations/elevenlabs/index.html). Read that guide for the manual path and screenshots.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: trunks, number, spend limits | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| ElevenLabs: agent creation and configuration, number-to-agent assignment | ElevenLabs hosted MCP `https://api.elevenlabs.io/v1/mcp` | OAuth sign-in, no keys |
| ElevenLabs: number import (not available in their MCP) | REST `POST /v1/convai/phone-numbers` via `scripts/import_number.py` | One `xi-api-key`, or a guided dashboard step |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage trunks and numbers under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- An ElevenLabs account with an agent, or a description of the agent you want created.
- The ElevenLabs MCP connected in Claude Code (`claude mcp add --scope user --transport http elevenlabs https://api.elevenlabs.io/v1/mcp`, then `/mcp` to sign in), or an ElevenLabs API key for the import script only.

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-elevenlabs
```

It copies the skill into `~/.claude/skills/didww-to-elevenlabs/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-elevenlabs
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Connect my DIDWW number +33 1 44 55 66 77 to my ElevenLabs agent "Reception". Transfer to +33 6 12 34 56 78 when the caller asks for a human.
```

The skill confirms three things in one message: which DIDWW number (or which country to buy one in), which agent (existing, or created from your description), and the transfer destination if any. Then it works through the steps below.

## Step 3. What gets configured

### DIDWW side

All DIDWW changes go through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool.

- **Inbound SIP trunk.** Host `sip.rtc.elevenlabs.io`, port 5060, transport TCP (TLS is supported; media encryption must then match on both sides). Digest authentication with a generated username and password. Digest is preferred over IP filtering because ElevenLabs sends from distributed addresses and static IPs are an enterprise feature. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Created for this connection. DIDWW generates the username and password; the host is the one nearest to the platform's region: `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `nyc.us.out.didww.com` or `sg.out.didww.com`. The agent passes these credentials to the platform side.
- **Spend controls.** A 24-hour spend limit of 10 to 50 USD and channel limits matching the expected concurrency are set before the first call. The defaults are too high for a test agent.

### ElevenLabs side

- **Agent.** Created or selected through the ElevenLabs MCP: voice, language and prompt.
- **Number import.** `scripts/import_number.py` calls the phone-numbers API. The inbound authentication is a `credentials` object that must match the DIDWW inbound trunk's digest pair exactly. The outbound address is the DIDWW outbound host as a bare hostname, no `sip:` prefix and no port, with the transport in lower case (`tcp` or `tls`) and the DIDWW outbound trunk credentials.
- **Agent assignment.** Through the MCP (`agents_update_phone_number`) or the script's `--agent` flag.

To run the import by hand:

```bash
ELEVENLABS_API_KEY=... python3 ~/.claude/skills/didww-to-elevenlabs/scripts/import_number.py \
  --number +33144556677 --label "Paris line" \
  --inbound-user USER --inbound-pass PASS \
  --outbound-host fra.eu.out.didww.com --outbound-user OUSER --outbound-pass OPASS \
  --transport tcp --agent AGENT_ID
```

> [!IMPORTANT]
> The number must be imported exactly as it appears on the DIDWW trunk. A missing or extra `+` is enough for ElevenLabs to reject the call.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone reaches the agent.
2. One outbound call from the agent shows the DIDWW number as caller ID.
3. One transfer, if configured. Call detail records appear on the DIDWW side.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Inbound call rejected or silent | Digest mismatch between the DIDWW trunk and the import's inbound credentials, or the number's `+` differs from how it was imported | Re-enter the same username and password on both sides; import the number in E.164 as DIDWW shows it |
| SIP 488, or one-way audio | Media encryption enabled on one side only | Match SRTP on the DIDWW trunk and the ElevenLabs import |
| Outbound calls fail | A `sip:` prefix or a port pasted into the Address field, or the wrong region host | Use the bare DIDWW host, for example `fra.eu.out.didww.com` |
| Everything works but spend is higher than expected | Default spend limits were kept | Set the 24-hour spend limit and channel limits on the DIDWW trunks |

## Keys, billing and safety

- **ElevenLabs credentials.** API keys live at `elevenlabs.io/app/settings/api-keys` (workspace keys: profile icon, Workspace settings, Service Accounts). A key is needed only for the import script; everything else uses the OAuth MCP. Agent minutes draw from the same credit pool as text-to-speech, and LLM and telephony are billed on top of the subscription.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [ElevenLabs integration guide](https://doc.didww.com/integrations/elevenlabs/index.html): the same connection configured by hand.
- [ElevenLabs SIP trunking documentation](https://elevenlabs.io/docs/agents-platform/phone-numbers/sip-trunking).
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-elevenlabs`](https://github.com/didww/ai/tree/main/skills/didww-to-elevenlabs) in the didww/ai repository. Package: [npmjs.com/package/didww-to-elevenlabs](https://www.npmjs.com/package/didww-to-elevenlabs).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
