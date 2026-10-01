# DIDWW to Ultravox skill

Use the **didww-to-ultravox** skill with **Claude Code** to connect a DIDWW phone number to an **Ultravox Realtime** voice agent over SIP. Ultravox is different from every number-import platform: there is no number object. Inbound routing is address-based. Calls arrive at `agent_{agent_id}@{account_sip_domain}` and the account's SIP settings decide what is accepted. The skill points the DIDWW trunk at the right address and configures those settings.

- Read the account's SIP domain, which is per account and cannot be guessed.
- Configure the allowed source ranges, the accepted agents or a fallback webhook that maps numbers to agents.
- Place outbound calls through DIDWW per call via the Ultravox calls API.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: trunks, number, spend limits | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| Ultravox: account SIP settings (`GET` and `PATCH /api/sip`) | REST via `scripts/connect.py` | `ULTRAVOX_API_KEY` (`X-API-Key` header) |

Ultravox has no official MCP. Two routing shapes exist, and the skill asks which one you need:

- **One agent per number.** The DIDWW inbound trunk's destination is the agent's own SIP address. This works when the trunk can carry a custom destination user part.
- **Fallback webhook.** Calls that match no agent address hit the account's `fallbackHandler` URL, which receives the dialed number as `toUri` and answers `startAgentCall` with the chosen agent, or `reject`. A small public HTTPS endpoint maps numbers to agents. This is the general answer for several numbers on one account.

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage trunks and numbers under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- An Ultravox account with an agent, and an API key from `app.ultravox.ai`, Settings, API Keys, Generate New Key.
- For the fallback shape, somewhere to run a small public HTTPS endpoint.

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-ultravox
```

It copies the skill into `~/.claude/skills/didww-to-ultravox/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-ultravox
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Route my DIDWW number +33 1 44 55 66 77 to my Ultravox agent. One agent on this number is enough.
```

The skill confirms the number (or country to buy one in), the agent, the routing shape, and a transfer target if any.

## Step 3. What gets configured

### Ultravox side

Read the SIP domain first; the `domain` field of `GET /api/sip` is read-only and per account:

```bash
ULTRAVOX_API_KEY=... python3 ~/.claude/skills/didww-to-ultravox/scripts/connect.py --show
```

Then patch the account settings as needed:

```bash
ULTRAVOX_API_KEY=... python3 ~/.claude/skills/didww-to-ultravox/scripts/connect.py \
  --allow-cidr <DIDWW signaling range> --allow-agent 'agent_.*' \
  --fallback-url https://your.host/route
```

`--allow-cidr` (repeatable) sets `allowedCidrRanges`, `--allow-agent` sets `allowedAgents`, `--allow-all-agents` accepts every agent, and `--fallback-url` sets the `fallbackHandler`. Outbound calls are placed per call with `POST /api/calls` and `medium.sip.outgoing` carrying the DIDWW outbound host and the DIDWW outbound trunk credentials.

### DIDWW side

All DIDWW changes go through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool.

- **Inbound SIP trunk.** Destination is the account SIP domain, with the destination user part chosen per the routing shape: the agent address for one agent per number, or the dialed number for the fallback shape. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Created for this connection. DIDWW generates the username and password; the host is the one nearest to the platform's region: `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `nyc.us.out.didww.com` or `sg.out.didww.com`. The agent passes these credentials to the platform side.
- **Spend controls.** A 24-hour spend limit of 10 to 50 USD and channel limits matching the expected concurrency are set before the first call. The defaults are too high for a test agent.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone reaches the agent.
2. One outbound call placed with a test `POST /api/calls` shows the DIDWW number as caller ID.
3. Transfers, if configured. Ultravox offers cold (REFER), warm and bridged transfers.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Inbound 603 rejected | The To address matches no allowed agent and no fallback handler is set | Fix the `allowedAgents` pattern or add the fallback URL |
| Inbound never arrives | The CIDR allowlist is missing DIDWW's signaling range, or the trunk sends the dialed number as user part while routing expected an agent address | Add the range; switch to the fallback shape |
| Outbound authentication failures | Credentials in `medium.sip.outgoing` do not match the DIDWW outbound trunk | Use the DIDWW outbound trunk's generated username and password |

## Keys, billing and safety

- **Ultravox credentials.** API keys are at `app.ultravox.ai`, Settings, API Keys. Ultravox bills two meters per call: agent time and SIP minutes. Pay-as-you-go has concurrency caps that only the paid plan removes.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-ultravox`](https://github.com/didww/ai/tree/main/skills/didww-to-ultravox) in the didww/ai repository. Package: [npmjs.com/package/didww-to-ultravox](https://www.npmjs.com/package/didww-to-ultravox).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
