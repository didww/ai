# DIDWW to Retell skill

Use the **didww-to-retell** skill with **Claude Code** to connect a DIDWW phone number to a **Retell AI** agent over Retell's custom telephony. This is the most automatable pairing in the family: Retell's official MCP creates agents and imports numbers, and the DIDWW MCP covers the carrier side, so with both connected the whole setup is tool calls with no scripts and no dashboards.

- Import the DIDWW number into Retell with the DIDWW outbound host and credentials in one call.
- Bind an agent for inbound and outbound calls in that same call.
- Fall back to a script when the Retell MCP is not available.

This skill automates the steps described in the [Retell AI integration guide](https://doc.didww.com/integrations/retell-ai/index.html).

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: number, inbound trunk | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| DIDWW: outbound trunk, spend limits | You, in the DIDWW User Panel. The MCP has no outbound trunk tools | Your panel login |
| Retell: agent, number import, agent binding | Retell MCP `https://mcp.retellai.com` | Bearer API key, entered once at MCP setup |
| Retell, when its MCP is not connected | `scripts/connect.py` | `RETELL_API_KEY` |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage numbers and inbound trunks under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- For outbound calls, access to DIDWW outbound trunks on the account. If **Voice**, **Outbound Trunks** in the DIDWW User Panel shows **Get Access**, apply there first ([Get access to outbound trunks](https://doc.didww.com/voice/outbound-trunks/get-access.html)): it needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. Inbound calls work without it.
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

The number and the inbound trunk are configured through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool. The outbound trunk is created by you in the DIDWW User Panel, because the MCP has no outbound trunk tools.

- **Inbound SIP trunk.** Host `sip.retellai.com`, transport TCP, which is Retell's recommendation because UDP packets can be dropped. Digest authentication is preferred because Retell has no single stable inbound IP. If IP filtering is used for the outbound leg, Retell's egress ranges are `18.98.16.120/30`, `3.42.144.0/23` and `153.57.128.0/18`, plus `143.223.88.0/21` and `161.115.160.0/19` for some US traffic. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Needed only for calls the agent places. You create it in the DIDWW User Panel under **Voice**, **Outbound Trunks**, **Create New**, because the DIDWW MCP has no outbound trunk tools. If that page shows **Get Access**, the account is not approved for outbound calling yet: the application needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. The inbound side can go live meanwhile. Choose the **Credentials & IP-Based** authentication method. It needs at least one **Allowed SIP IP address**: Retell's egress ranges `18.98.16.120/30`, `3.42.144.0/23` and `153.57.128.0/18`, plus `143.223.88.0/21` and `161.115.160.0/19` for some US traffic. Set **Media encryption mode** to match the platform side. DIDWW generates the username and password; give them to the agent in a file or environment variables rather than pasting them into the chat, and it passes them to the platform side. Enable the trunk if it shows **Disabled**. The host is the one nearest to the platform's region: `nyc.us.out.didww.com`, `lac.us.out.didww.com`, `mia.us.out.didww.com`, `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com` or `hk.out.didww.com`.
- **Spend controls.** On the outbound trunk, under **Termination**: **24 Hour Limit (USD)** at its minimum of 50 (the default is 3000, and DIDWW disables the trunk when the limit is reached), **Capacity limit** matching the expected concurrency, and the usage limit notification on. Under **CLI Settings**, allow only the connected number as caller ID; under **Destination Dialing Settings**, reject all destinations except the countries the agent calls. On the inbound trunk the skill sets a capacity limit through the MCP.

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
| Outbound call rejected by DIDWW | Source IP not in the outbound trunk's Allowed SIP IP addresses, caller ID not allowed in its CLI settings, destination not allowed, or the 24-hour limit reached, which disables the trunk | Check the outbound trunk in the DIDWW User Panel and re-enable it |

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
