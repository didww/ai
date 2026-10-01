# DIDWW to Vapi skill

Use the **didww-to-vapi** skill with **Claude Code** to connect a DIDWW phone number to a **Vapi** assistant over Vapi's bring-your-own SIP trunking. Vapi is API-first for this connection, and the skill wraps the write calls in a script because Vapi's MCP can list trunks and numbers but cannot create them.

- Create the Vapi SIP trunk credential and the imported number, bound to an assistant, in one run.
- Build the DIDWW inbound trunk against the per-credential ingress host that Vapi assigns.
- Verify calls through Vapi's MCP without leaving the conversation.

This skill automates the steps described in the [Vapi integration guide](https://doc.didww.com/integrations/vapi/index.html).

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: trunks, number, spend limits | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| Vapi: credential and number creation, assistant binding | REST via `scripts/connect.py` | `VAPI_API_KEY` |
| Vapi: verification (`list_phone_numbers`, `get_call`) | Vapi MCP `https://mcp.vapi.ai/mcp` | Bearer API key; read-only for trunks and numbers |

> [!IMPORTANT]
> Vapi's inbound address embeds the credential: `{number}@{credential_id}.sip.vapi.ai` (EU: `.sip.eu.vapi.ai`). The credential must exist before the DIDWW inbound trunk can be created, because the trunk's destination host is that per-credential hostname. The skill follows this order. Never copy an ingress host from someone else's setup.

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage trunks and numbers under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- A Vapi account with an assistant, or its ID, and a Vapi API key from `dashboard.vapi.ai/org/api-keys` (shown once at creation).
- A decision on region: US or EU.

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-vapi
```

It copies the skill into `~/.claude/skills/didww-to-vapi/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-vapi
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Put my Vapi assistant asst_123 on my DIDWW number +33 1 44 55 66 77, EU region.
```

The skill confirms the number (or country to buy one in), the assistant (existing ID or one to create), the region, and a transfer target if any.

## Step 3. What gets configured

The order matters, so the skill does the DIDWW outbound trunk first, then Vapi, then the DIDWW inbound trunk.

### DIDWW side

All DIDWW changes go through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool.

- **Inbound SIP trunk.** Created last. Host is the per-credential hostname printed by the script in the Vapi step, port 5060. Vapi's signaling IPs are allowed on the trunk: US `44.229.228.186` and `44.238.177.138`, EU `63.182.83.170`. Missing IPs show up as 401 responses on inbound calls. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Created for this connection. DIDWW generates the username and password; the host is the one nearest to the platform's region: `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `nyc.us.out.didww.com` or `sg.out.didww.com`. The agent passes these credentials to the platform side.
- **Spend controls.** A 24-hour spend limit of 10 to 50 USD and channel limits matching the expected concurrency are set before the first call. The defaults are too high for a test agent.

### Vapi side

One run of `scripts/connect.py` creates the `byo-sip-trunk` credential (gateway is the DIDWW outbound host, the outbound authentication plan is the DIDWW outbound trunk's username and password) and the `byo-phone-number` bound to the assistant. It prints the exact ingress host for the DIDWW inbound trunk.

```bash
VAPI_API_KEY=... python3 ~/.claude/skills/didww-to-vapi/scripts/connect.py \
  --number +33144556677 --didww-host fra.eu.out.didww.com \
  --didww-user USER --didww-pass PASS --assistant ASSISTANT_ID --eu
```

Drop `--eu` for the US region. The script sets `numberE164CheckEnabled` to false so that DIDWW numbers import without format rejections.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone reaches the assistant.
2. One outbound call shows the DIDWW number as caller ID.
3. One transfer, if configured. Vapi's MCP `get_call` shows the outcome of each test call.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Inbound 401 | Vapi's signaling IPs are not allowed on the DIDWW trunk, or the trunk points at bare `sip.vapi.ai` instead of the per-credential host | Add the IPs; set the host to `<credential_id>.sip.vapi.ai` |
| Outbound authentication failures | The credential's outbound authentication plan does not match the DIDWW outbound trunk | Regenerate the DIDWW credentials and re-run the script with `--update` |
| Number rejected on create | Format check | The script disables the E.164 check; try the number without the `+` |

## Keys, billing and safety

- **Vapi credentials.** API keys are at `dashboard.vapi.ai/org/api-keys` and are shown once at creation. Billing is prepaid credits with optional card auto-reload; per-minute cost is Vapi's platform fee plus the pass-through cost of the model, voice and transcription providers you pick.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

> [!WARNING]
> A negative Vapi balance freezes the wallet and auto-cancels add-ons, including imported phone numbers. Enable auto-reload on day one.

## Additional resources

- [Vapi integration guide](https://doc.didww.com/integrations/vapi/index.html): the same connection configured by hand.
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-vapi`](https://github.com/didww/ai/tree/main/skills/didww-to-vapi) in the didww/ai repository. Package: [npmjs.com/package/didww-to-vapi](https://www.npmjs.com/package/didww-to-vapi).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
