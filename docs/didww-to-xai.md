# DIDWW to xAI Grok skill

Use the **didww-to-xai** skill with **Claude Code** to point a DIDWW phone number at **xAI's Grok voice** over SIP. The interface mirrors OpenAI's with one improvement: the number is registered with xAI first as an API object that carries its own SIP authentication, so inbound calls are gated by digest credentials or an IP allowlist rather than by a webhook alone. As with OpenAI, there is no stored agent: on each call a webhook fires and your code configures the session over a websocket.

- Register the DIDWW number with xAI, with digest credentials and the incoming-call webhook URL.
- Build the DIDWW inbound trunk against `sip.voice.x.ai` over TLS with those credentials.
- Configure voice, instructions and turn detection per call from your backend.

> [!IMPORTANT]
> Developer-grade pairing: you run a small backend that handles the webhook and the websocket. If you want no-code, use one of the hosted platforms.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: trunk, number, spend limits | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| xAI: number registration | REST `POST https://api.x.ai/v2/phone-numbers` via `scripts/register_number.py` | `XAI_API_KEY` |
| Per-call session control | Your backend: webhook, then `wss://api.x.ai/v1/realtime?call_id=...` | `XAI_API_KEY`, webhook signing secret |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage trunks and numbers under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- An xAI account and an API key from `console.x.ai`, API Keys.
- A host for the webhook backend that serves public HTTPS.

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-xai
```

It copies the skill into `~/.claude/skills/didww-to-xai/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-xai
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Answer my DIDWW number +33 1 44 55 66 77 with Grok voice. The backend runs at https://voice.example.com/xai.
```

The skill confirms the number (or country to buy one in), the agent behaviour (it becomes the per-call session configuration), the transfer target, and where the backend runs.

## Step 3. What gets configured

### xAI side

`scripts/register_number.py` registers the number with `origin: "byo_trunk"`, the webhook URL as an object, and `sip_auth` with digest credentials (`auth_username`, `auth_password`) and optionally `allowed_addresses` with DIDWW's signaling IPs:

```bash
XAI_API_KEY=... python3 ~/.claude/skills/didww-to-xai/scripts/register_number.py \
  --number +33144556677 --webhook https://voice.example.com/xai --sip-user USER --sip-pass PASS
```

> [!WARNING]
> The response carries the webhook signing secret exactly once, and the SIP password is never returned again. Store both immediately: the password goes into the DIDWW trunk, the secret into the backend's environment.

### DIDWW side

All DIDWW changes go through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool.

- **Inbound SIP trunk.** Destination `sip:{number}@sip.voice.x.ai;transport=tls`, digest authentication with the username and password from the registration. The DID is assigned to this trunk.
- **Spend controls.** A 24-hour spend limit of 10 to 50 USD and channel limits matching the expected concurrency are set before the first call. The defaults are too high for a test agent.

### Backend

On the incoming-call webhook, which carries a `call_id`, the backend connects to `wss://api.x.ai/v1/realtime?call_id={call_id}` and sends `session.update` with voice, instructions and turn detection. Transfers use `POST /v1/realtime/calls/{call_id}/refer` with a `tel:` target, `/hangup` ends the call, and DTMF arrives as `input_audio_buffer.dtmf_event_received` events. The webhook server shipped with the [OpenAI Realtime skill](didww-to-openai-realtime.md) is the closest template; the skill adapts its accept step to the websocket model.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone; the backend log shows the websocket connect and `session.update`.
2. The transfer phrase hands the call to the configured destination.
3. Hanging up on either side is handled cleanly.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Call never reaches xAI | TLS missing on the trunk, or the digest pair differs from the registration | Enable TLS; re-enter the same credentials on both sides |
| Webhook fires, then silence | The websocket connect or `session.update` failed | Log both; check the API key |
| Lost the SIP password | It is unreadable after creation | Update the registration and the DIDWW trunk together with a new pair |
| Lost the webhook signing secret | Also shown only at registration | Re-register the number and update the backend's environment |
| 422 on registration | Field names drifted | The error names the accepted fields (`auth_username`, `webhook.url`, ...); adjust and rerun |

## Keys, billing and safety

- **xAI credentials.** API keys are at `console.x.ai`, API Keys. Billing is prepaid credits under Billing, API spend management, with a minimum top-up and no documented free credits. Calls fail the instant credits reach zero, so configure auto top-up with a threshold, an amount and a monthly cap at setup.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [DIDWW to OpenAI Realtime](didww-to-openai-realtime.md): the sibling pairing and the template for the backend.
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-xai`](https://github.com/didww/ai/tree/main/skills/didww-to-xai) in the didww/ai repository. Package: [npmjs.com/package/didww-to-xai](https://www.npmjs.com/package/didww-to-xai).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
