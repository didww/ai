# DIDWW to Retell skill

Use the **didww-to-retell** skill with **Claude Code** to connect a DIDWW phone number to a **Retell AI** agent over Retell's custom telephony. This is the most automatable pairing in the family: Retell's official MCP creates agents and imports numbers, and the DIDWW MCP covers the carrier side, so with both connected the whole setup is tool calls with no scripts and no dashboards.

- Import the DIDWW number into Retell with the DIDWW outbound host and credentials in one call.
- Bind an agent for inbound and outbound calls in that same call.
- Fall back to a script when the Retell MCP is not available.

This skill automates the steps described in the [Retell AI integration guide](https://doc.didww.com/integrations/retell-ai/index.html).

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: trunks, number, spend limits | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| Retell: agent, number import, agent binding | Retell MCP `https://mcp.retellai.com` | Bearer API key, entered once at MCP setup |
| Retell, when its MCP is not connected | `scripts/connect.py` | `RETELL_API_KEY` |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage trunks and numbers under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- A Retell account and an API key from the dashboard's API Keys tab. The same key powers the Retell MCP.
- Optionally, the Retell MCP connected in Claude Code (`claude mcp add --scope user --transport http retell https://mcp.retellai.com` with your Bearer key).

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-retell
```

It copies the skill into `~/.claude/skills/didww-to-retell/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-retell
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Import my DIDWW number +33 1 44 55 66 77 into Retell and bind it to agent agent_abc, inbound and outbound.
```

The skill confirms the number (or country to buy one in), the agent (existing or created from your description), the transfer target, and any country allowlists you want on calls.

## Step 3. What gets configured

### DIDWW side

All DIDWW changes go through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool.

- **Inbound SIP trunk.** Host `sip.retellai.com`, transport TCP, which is Retell's recommendation because UDP packets can be dropped. Digest authentication is preferred because Retell has no single stable inbound IP. If IP filtering is used for the outbound leg, Retell's egress ranges are `18.98.16.120/30`, `3.42.144.0/23` and `153.57.128.0/18`, plus `143.223.88.0/21` and `161.115.160.0/19` for some US traffic. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Created for this connection. DIDWW generates the username and password; the host is the one nearest to the platform's region: `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `nyc.us.out.didww.com` or `sg.out.didww.com`. The agent passes these credentials to the platform side.
- **Spend controls.** A 24-hour spend limit of 10 to 50 USD and channel limits matching the expected concurrency are set before the first call. The defaults are too high for a test agent.

### Retell side

One import call does everything: `phone_number` in E.164, `termination_uri` set to the DIDWW outbound host, `sip_trunk_auth_username` and `sip_trunk_auth_password` from the DIDWW outbound trunk, `transport`, and the agent binding inline through `inbound_agents` and `outbound_agents`. There is no separate trunk object in Retell.

Without the Retell MCP:

```bash
RETELL_API_KEY=... python3 ~/.claude/skills/didww-to-retell/scripts/connect.py \
  --number +33144556677 --didww-host fra.eu.out.didww.com \
  --didww-user USER --didww-pass PASS --agent AGENT_ID --transport TCP --nickname "Paris line"
```

> [!NOTE]
> Later changes to the trunk, such as a new DIDWW host or new credentials, require deleting and re-importing the number in Retell. The number cannot be edited in place. The agent is re-bound in the same import call.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone reaches the agent.
2. One outbound call shows the DIDWW number as caller ID.
3. One transfer, if configured. Retell's MCP reads call logs for verification.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Inbound silent or rejected | Digest mismatch, or the DIDWW trunk uses UDP where TCP was expected | Match the credentials; set `;transport=tcp` on the destination |
| Changes to the trunk do not take effect | Retell does not edit imported numbers | Delete and re-import the number with the new values and the agent binding |
| Test calls blocked by country | `allowed_inbound_country_list` or `allowed_outbound_country_list` set at import | Adjust the lists and re-import |

## Keys, billing and safety

- **Retell credentials.** API keys are in the dashboard's API Keys tab. Billing is prepaid credits with optional auto-recharge, and subscription items such as numbers, knowledge bases and concurrency bill the card separately at cycle end. Calls hard-block at zero credits. Calls carried over your own DIDWW trunk are not billed Retell's telephony line item.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [Retell AI integration guide](https://doc.didww.com/integrations/retell-ai/index.html): the same connection configured by hand.
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-retell`](https://github.com/didww/ai/tree/main/skills/didww-to-retell) in the didww/ai repository. Package: [npmjs.com/package/didww-to-retell](https://www.npmjs.com/package/didww-to-retell).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
