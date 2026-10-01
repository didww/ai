# DIDWW to OpenAI Realtime skill

Use the **didww-to-openai-realtime** skill with **Claude Code** to point a DIDWW phone number directly at the **OpenAI Realtime API** over SIP. There is no voice platform in between and no agent object to configure: every incoming call fires a webhook, and your code accepts the call with instructions. The skill generates that backend instead of pretending a configuration exists.

- Build the DIDWW inbound trunk against OpenAI's SIP endpoint with TLS and SRTP.
- Generate a small webhook backend that verifies signatures, accepts calls to known numbers with your instructions, and rejects everything else.
- Expose call transfer through the Realtime refer endpoint.

> [!IMPORTANT]
> This is a developer-grade pairing, not a no-code one. You need somewhere to run a small public HTTPS endpoint: a small VPS, a serverless function, or a tunnel while testing. If that is not an option, the hosted platforms covered by the other skills are the better fit.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: trunk, number, spend limits | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| OpenAI: project webhook for `realtime.call.incoming` | Platform settings (manual) | Your OpenAI sign-in |
| Call control: accept, reject, transfer | `scripts/webhook_server.py` | `OPENAI_API_KEY`, `OPENAI_WEBHOOK_SECRET` |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage trunks and numbers under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- An OpenAI platform account with a project. The project ID (`proj_...`) becomes the SIP address.
- An API key from `platform.openai.com/api-keys`.
- A host for the webhook backend that serves public HTTPS.

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-openai-realtime
```

It copies the skill into `~/.claude/skills/didww-to-openai-realtime/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-openai-realtime
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Answer my DIDWW number +33 1 44 55 66 77 with gpt-realtime. It should take restaurant bookings and transfer to +33 6 12 34 56 78 on request. The backend will run on my VPS.
```

The skill confirms the number (or country to buy one in), what the agent should do (this becomes the instructions), the transfer target, and where the backend will run.

## Step 3. What gets configured

### OpenAI side

In the platform settings at `platform.openai.com/settings/project/webhooks`, create a project webhook for the `realtime.call.incoming` event pointing at the backend URL. Copy the signing secret at creation.

### DIDWW side

All DIDWW changes go through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool.

- **Inbound SIP trunk.** Destination `sip:{project_id}@sip.api.openai.com;transport=tls`, port 5061, TLS signaling and SRTP media, both required. For EU data residency the host is `sip-eu.api.openai.com`. The DID is assigned to this trunk.
- **Spend controls.** A 24-hour spend limit of 10 to 50 USD and channel limits matching the expected concurrency are set before the first call. The defaults are too high for a test agent.

> [!NOTE]
> OpenAI's SIP endpoint has no digest authentication. The webhook's accept or reject decision is the authentication gate, which is why the generated backend rejects calls to unknown numbers by default. Anyone can send an INVITE to the URI; keep that rejection in place.

### Backend

`scripts/webhook_server.py` is a stdlib-only starting point. It verifies the webhook signature, accepts calls to the numbers listed in its `AGENTS` table with the model and your instructions, rejects other numbers, and exposes transfer through `POST /v1/realtime/calls/{call_id}/refer` with a `tel:` target. Edit `AGENTS` (number to instructions and transfer target), deploy it behind your HTTPS front, and set its environment:

```bash
OPENAI_API_KEY=... OPENAI_WEBHOOK_SECRET=... PORT=8080 python3 webhook_server.py
```

> [!NOTE]
> Outbound calls are not part of OpenAI's SIP interface as of August 2026. Originate outbound calls from the DIDWW side or from a platform if you need them.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone; the server log shows the call accepted.
2. The transfer phrase hands the call to the configured destination.
3. A call to a number not in `AGENTS` is rejected.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Call rings once and dies | TLS or SRTP not set on the DIDWW trunk, or the project ID in the SIP address is wrong | Enable both; check the `proj_` ID |
| Webhook never fires | No webhook configured for the project, or the backend URL is not publicly reachable HTTPS | Create the webhook; test the URL from outside |
| Call connects, then silence | The accept API call failed | Check the server log, the API key, and that the accept happens within seconds |
| Strangers can ring the SIP URI | Expected: there is no digest on OpenAI's ingress | Keep the unknown-number rejection in the server |

## Keys, billing and safety

- **OpenAI credentials.** API keys are at `platform.openai.com/api-keys`, webhooks at `platform.openai.com/settings/project/webhooks`; the signing secret is shown once. Billing is prepaid credits under Settings, Billing; check the auto-recharge setting and the credit expiry terms. Realtime bills in audio tokens, not minutes, so the per-minute cost depends on how much of the call is speech.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [DIDWW to xAI Grok](didww-to-xai.md): a near-identical SIP interface with digest authentication at the number level.
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-openai-realtime`](https://github.com/didww/ai/tree/main/skills/didww-to-openai-realtime) in the didww/ai repository. Package: [npmjs.com/package/didww-to-openai-realtime](https://www.npmjs.com/package/didww-to-openai-realtime).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
