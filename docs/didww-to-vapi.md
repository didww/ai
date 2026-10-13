# DIDWW to Vapi skill

Use the **didww-to-vapi** skill with **Claude Code** to connect a DIDWW phone number to a **Vapi** assistant over Vapi's bring-your-own SIP trunking. Vapi is API-first for this connection, and the skill wraps the write calls in a script because Vapi's MCP can list trunks and numbers but cannot create them.

- Create the Vapi inbound and outbound SIP trunk credentials and the imported number, bound to an assistant, in one run.
- Build the DIDWW inbound trunk pointed at Vapi's regional SIP host, with SIP REFER transfers allowed and authenticated.
- Verify calls through Vapi's MCP without leaving the conversation.

This skill automates the steps described in the [Vapi integration guide](https://doc.didww.com/integrations/vapi/index.html).

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: number, inbound trunk | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| DIDWW: outbound trunk, spend limits | You, in the DIDWW User Panel. The MCP has no outbound trunk tools | Your panel login |
| Vapi: credential and number creation, assistant binding | REST via `scripts/connect.py` | `VAPI_API_KEY` |
| Vapi: verification (`list_phone_numbers`, `get_call`) | Vapi MCP `https://mcp.vapi.ai/mcp` | Bearer API key; read-only for trunks and numbers |

> [!IMPORTANT]
> The DIDWW inbound trunk points at `sip.vapi.ai` (EU organizations: `sip.eu.vapi.ai`). Vapi recognises DIDWW's calls by their source: the Vapi inbound credential lists DIDWW's seven inbound signaling IPs (`46.19.209.14`, `46.19.210.14`, `46.19.212.14`, `46.19.213.14`, `46.19.214.14`, `46.19.215.14`, `185.238.173.14`) as inbound gateways, and the number is imported on that credential. This matches Vapi's [DIDWW SIP integration](https://docs.vapi.ai/advanced/sip/didww) guide.

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage numbers and inbound trunks under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- For outbound calls and call transfers, access to DIDWW outbound trunks. Inbound calls work without it. If **Voice**, **Outbound Trunks** in the DIDWW User Panel shows **Get Access**, apply there ([Get access to outbound trunks](https://doc.didww.com/voice/outbound-trunks/get-access.html)): it needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours.
- A Vapi account with an assistant, or its ID, and a Vapi API key from `dashboard.vapi.ai/org/api-keys` (shown once at creation).
- The region your Vapi organization is hosted in: US or EU.

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

The DIDWW outbound trunk comes first when you want outbound calls or transfers (you create it in the DIDWW User Panel), then Vapi, then the DIDWW inbound trunk. Without outbound access, the skill sets up inbound calls alone and adds the rest later.

### DIDWW side

The number and the inbound trunk are configured through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool. The outbound trunk is created by you in the DIDWW User Panel, because the MCP has no outbound trunk tools.

- **Inbound SIP trunk.** Created last. Host `sip.vapi.ai` (EU: `sip.eu.vapi.ai`), port 5060 for UDP or TCP or 5061 for TLS, with the same transport as the Vapi gateways. **Max transfers** is 1, which allows the SIP REFER requests Vapi sends to transfer a call. For transfers, **Authorization** is on, with the outbound trunk's username and password as auth user and password. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Needed only for calls the agent places. You create it in the DIDWW User Panel under **Voice**, **Outbound Trunks**, **Create New**, because the DIDWW MCP has no outbound trunk tools. If that page shows **Get Access**, the account is not approved for outbound calling yet: the application needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. The inbound side can go live meanwhile. Choose the **Credentials & IP-Based** authentication method. It needs at least one **Allowed SIP IP address**: Vapi's signaling IPs, US `44.229.228.186/32` and `44.238.177.138/32`, EU `63.182.83.170/32` (per [Vapi's SIP networking page](https://docs.vapi.ai/advanced/sip/sip-networking)), plus DIDWW's seven inbound signaling IPs listed above, which transfers need. Never use `0.0.0.0/0`. Set **Media encryption mode** to match the platform side. DIDWW generates the username and password; give them to the agent in a file or environment variables rather than pasting them into the chat, and it passes them to the platform side. Enable the trunk if it shows **Disabled**. The host is the one nearest to the platform's region: `nyc.us.out.didww.com`, `lac.us.out.didww.com`, `mia.us.out.didww.com`, `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com` or `hk.out.didww.com`.
- **Spend controls.** On the outbound trunk, under **Termination**: **24 Hour Limit (USD)** at its minimum of 50 (the default is 3000, and DIDWW disables the trunk when the limit is reached), **Capacity limit** matching the expected concurrency, and the usage limit notification on. Under **CLI Settings**, allow only the connected number as caller ID; under **Destination Dialing Settings**, reject all destinations except the countries the agent calls. On the inbound trunk the skill sets a capacity limit through the MCP.

### Vapi side

One run of `scripts/connect.py` creates:

1. The **DIDWW Outbound Trunk** credential: one outbound-only gateway at the DIDWW outbound host, with the DIDWW outbound trunk's username and password.
2. The **DIDWW Inbound Trunk** credential: one inbound-only gateway per DIDWW signaling IP, carrying the same username and password so that transfers authenticate.
3. The `byo-phone-number`, in E.164 with the `+`, on the inbound credential and bound to the assistant.

It then prints the values for the DIDWW inbound and outbound trunks.

```bash
DIDWW_TRUNK_PASS=... VAPI_API_KEY=... python3 ~/.claude/skills/didww-to-vapi/scripts/connect.py \
  --number +33144556677 --didww-host fra.eu.out.didww.com \
  --didww-user USER --assistant ASSISTANT_ID --eu
```

`--eu` sends the API calls to `api.eu.vapi.ai` and points DIDWW at `sip.eu.vapi.ai`; drop it for a US organization. `--transport tcp` or `--transport tls` changes the transport (TLS uses port 5061). Leave out the three `--didww-*` values for an inbound-only setup. The password can be given as `--didww-pass` or, better, in `DIDWW_TRUNK_PASS`, so it stays out of shell history.

For transfers, the assistant needs a Vapi **Transfer Call** tool with a SIP destination `sip:+E164@<DIDWW outbound host>` (for example `sip:+447700900123@fra.eu.out.didww.com`), blind transfer and SIP verb REFER, as in Vapi's guide.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone reaches the assistant.
2. One outbound call shows the DIDWW number as caller ID.
3. One transfer, if configured. Vapi's MCP `get_call` shows the outcome of each test call.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Inbound calls never reach the assistant | The number is not on the inbound credential, a DIDWW signaling IP is missing from its gateways, the trunk points at the other region's host, or the transport and port differ between the two sides | Re-run the script, or fix the gateways and host |
| Outbound authentication failures | The credentials in Vapi do not match the DIDWW outbound trunk | After regenerating them, run the script with `--rotate <outbound credential id> --rotate <inbound credential id> --didww-user USER` (password in `DIDWW_TRUNK_PASS`), and put the same pair in the inbound trunk's Authorization |
| Transfer fails | **Max transfers** is 0, the inbound trunk's Authorization is off or stale, or DIDWW's signaling IPs are missing from the outbound trunk's Allowed SIP IP addresses | Fix the trunk settings in the DIDWW User Panel |
| Outbound call rejected by DIDWW | Source IP not in the outbound trunk's Allowed SIP IP addresses, caller ID not allowed in its CLI settings, destination not allowed, or the 24-hour limit reached, which disables the trunk | Check the outbound trunk in the DIDWW User Panel and re-enable it |

## Keys, billing and safety

- **Vapi credentials.** API keys are at `dashboard.vapi.ai/org/api-keys` and are shown once at creation. Billing is prepaid credits with optional card auto-reload; per-minute cost is Vapi's platform fee plus the pass-through cost of the model, voice and transcription providers you pick.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

> [!WARNING]
> A negative Vapi balance freezes the wallet and auto-cancels add-ons, including imported phone numbers. Enable auto-reload on day one.

## Additional resources

- [Vapi integration guide](https://doc.didww.com/integrations/vapi/index.html): the same connection configured by hand. Vapi's own version: [DIDWW SIP integration](https://docs.vapi.ai/advanced/sip/didww).
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-vapi`](https://github.com/didww/ai/tree/main/skills/didww-to-vapi) in the didww/ai repository. Package: [npmjs.com/package/didww-to-vapi](https://www.npmjs.com/package/didww-to-vapi).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
