# DIDWW to Vogent skill

Use the **didww-to-vogent** skill with **Claude Code** to connect a DIDWW phone number to a **Vogent** voice agent. Vogent imports the number in one API call; the one step its API does not cover, attaching the agent to the number, is a single click that the skill walks you through.

- Import the DIDWW number into Vogent as a `sip_import` number with the DIDWW outbound host and credentials.
- Build the DIDWW inbound trunk against `sip.vogent.ai` with digest authentication.
- Finish with the one documented dashboard step and a verification call.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: number, inbound trunk | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| DIDWW: outbound trunk, spend limits | You, in the DIDWW User Panel. The MCP has no outbound trunk tools | Your panel login |
| Vogent: number import | REST `POST /api/phone_numbers` via `scripts/connect.py` | `VOGENT_API_KEY` (Bearer) |
| Vogent: agent-to-number binding | Dashboard, one step | Your Vogent sign-in |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage numbers and inbound trunks under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- For outbound calls, access to DIDWW outbound trunks on the account. If **Voice**, **Outbound Trunks** in the DIDWW User Panel shows **Get Access**, apply there first ([Get access to outbound trunks](https://doc.didww.com/voice/outbound-trunks/get-access.html)): it needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. Inbound calls work without it.
- A Vogent account with an agent, and an API key from the API Keys page in the `app.vogent.ai` sidebar.

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-vogent
```

It copies the skill into `~/.claude/skills/didww-to-vogent/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-vogent
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Connect my DIDWW number +33 1 44 55 66 77 to my Vogent agent.
```

The skill confirms the number (or country to buy one in), the agent, and a transfer target if any.

## Step 3. What gets configured

### DIDWW side

The number and the inbound trunk are configured through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool. The outbound trunk is created by you in the DIDWW User Panel, because the MCP has no outbound trunk tools.

- **Inbound SIP trunk.** Host `sip.vogent.ai`, digest authentication with a generated username and password. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Needed only for calls the agent places. You create it in the DIDWW User Panel under **Voice**, **Outbound Trunks**, **Create New**, because the DIDWW MCP has no outbound trunk tools. If that page shows **Get Access**, the account is not approved for outbound calling yet: the application needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. The inbound side can go live meanwhile. Choose the **Credentials & IP-Based** authentication method. It needs at least one **Allowed SIP IP address**: Vogent has no static SIP source range outside its enterprise plan; enterprise customers get the range from Vogent, anyone else contacts DIDWW support (support@didww.com). Do not enter `0.0.0.0/0`; DIDWW advises against open ranges. Set **Media encryption mode** to match the platform side. DIDWW generates the username and password; give them to the agent in a file or environment variables rather than pasting them into the chat, and it passes them to the platform side. Enable the trunk if it shows **Disabled**. The host is the one nearest to the platform's region: `nyc.us.out.didww.com`, `lac.us.out.didww.com`, `mia.us.out.didww.com`, `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com` or `hk.out.didww.com`.
- **Spend controls.** On the outbound trunk, under **Termination**: **24 Hour Limit (USD)** at its minimum of 50 (the default is 3000, and DIDWW disables the trunk when the limit is reached), **Capacity limit** matching the expected concurrency, and the usage limit notification on. Under **CLI Settings**, allow only the connected number as caller ID; under **Destination Dialing Settings**, reject all destinations except the countries the agent calls. On the inbound trunk the skill sets a capacity limit through the MCP.

### Vogent side

One call to the phone numbers API with `type: "sip_import"` carrying the E.164 number, the `terminationUri` set to the DIDWW outbound host, and the DIDWW outbound trunk credentials:

```bash
VOGENT_API_KEY=... python3 ~/.claude/skills/didww-to-vogent/scripts/connect.py \
  --number +33144556677 --didww-host fra.eu.out.didww.com --didww-user USER --didww-pass PASS
```

> [!IMPORTANT]
> The agent binding is not in the API response. Open the agent in the Vogent dashboard, go to the **Numbers** tab and attach the imported number. The skill tells you exactly this and waits for your confirmation before the verification call.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone reaches the agent.
2. One outbound call shows the DIDWW number as caller ID.
3. One transfer, if configured.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Inbound rejected | Digest pair mismatch between the DIDWW trunk and what Vogent expects for the imported number | Re-enter the same username and password on both sides |
| Import accepted but calls fail | `terminationUri` has a `sip:` prefix or is not the region-nearest DIDWW host | Use the bare host, for example `fra.eu.out.didww.com` |
| Agent does not answer | The dashboard binding step was skipped | Attach the number in the agent's Numbers tab |
| Outbound call rejected by DIDWW | Source IP not in the outbound trunk's Allowed SIP IP addresses, caller ID not allowed in its CLI settings, destination not allowed, or the 24-hour limit reached, which disables the trunk | Check the outbound trunk in the DIDWW User Panel and re-enable it |

## Keys, billing and safety

- **Vogent credentials.** API keys are on the API Keys page in the `app.vogent.ai` sidebar. Vogent publishes no pricing page; confirm the per-minute rate inside the panel before scaling.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-vogent`](https://github.com/didww/ai/tree/main/skills/didww-to-vogent) in the didww/ai repository. Package: [npmjs.com/package/didww-to-vogent](https://www.npmjs.com/package/didww-to-vogent).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
