# DIDWW to OpenAI skill (Realtime and GPT-Live)

Use the **didww-to-openai-realtime** skill with **Claude Code** to connect DIDWW phone numbers directly to OpenAI over SIP, with no voice platform in between. It covers two separate setups and asks which one you want first:

- **Incoming calls with the OpenAI Realtime API.** Callers dial your DIDWW number, `gpt-realtime` answers, and optionally hands the caller to a live person. Every call fires a webhook, and your server accepts it with instructions.
- **Outbound calls with GPT-Live.** Your server asks OpenAI to call a number, and OpenAI dials it through your DIDWW outbound trunk. No webhook or public URL is needed.

OpenAI stores no agent: your code defines it on every call. The skill follows DIDWW's [OpenAI integration guide](https://doc.didww.com/integrations/openai/index.html) and ships the code for both setups.

> [!IMPORTANT]
> This is a developer-grade pairing, not a no-code one. Incoming calls need somewhere to run a small public HTTPS endpoint: a small VPS, a container, or a tunnel while testing. If that is not an option, the hosted platforms covered by the other skills are the better fit.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: inbound trunk, number, capacity limit | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| DIDWW: outbound trunk (transfers and GPT-Live) | DIDWW User Panel (manual; the MCP has no outbound trunk tools) | Your DIDWW sign-in |
| OpenAI: project webhook for `realtime.call.incoming` (incoming only) | Platform settings (manual) | Your OpenAI sign-in |
| Incoming call control: accept, reject, greeting, transfer | `scripts/webhook_server.py` | `OPENAI_API_KEY`, `OPENAI_WEBHOOK_SECRET` |
| Outbound calls: create, monitor, delegation, hang up | `scripts/gptlive_call.py` | `OPENAI_API_KEY`, `DIDWW_SIP_USERNAME`, `DIDWW_SIP_PASSWORD` |

## Choose the setup

| Option | DIDWW side | OpenAI side | You run |
|---|---|---|---|
| Incoming calls | Inbound SIP trunk to OpenAI | API key, webhook | `webhook_server.py` on public HTTPS |
| Incoming calls with transfer to a person | As above, plus an outbound trunk whose credentials go on the inbound trunk | As above, plus a transfer tool | The same server with a transfer target |
| Outbound calls (GPT-Live) | Outbound trunk with SRTP and OpenAI's IP ranges | API key; outbound SIP enabled for your organization | `gptlive_call.py` |
| Both | One outbound trunk serves transfers and GPT-Live | Both | Both scripts |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- For transfers or outbound calls: access to DIDWW outbound trunks. If **Voice**, **Outbound Trunks** shows **Get Access**, apply first; DIDWW answers within 48 business hours.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage numbers and inbound trunks under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- An OpenAI platform project with API billing and a positive prepaid balance. For incoming calls, its project ID (`proj_...`) becomes the SIP address.
- An API key from `platform.openai.com/api-keys`. A **Restricted** key with only **Realtime (/v1/realtime)** set to **Request** was enough for incoming calls, transfers and GPT-Live outbound calls in testing.
- Incoming calls: a host for the webhook backend that serves public HTTPS, and permission to create webhooks in the OpenAI project (`api.webhooks.write`).
- Outbound calls: outbound SIP calling enabled for your OpenAI organization and access to `gpt-live-1`.

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
> The installer needs Node.js 16.7 or later. The skill's scripts need Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Answer my DIDWW number +1 510 555 0100 with gpt-realtime. It should take restaurant bookings and transfer to +1 510 555 0199 on request. The backend will run on my VPS.
```

```text
Use GPT-Live to call +1 510 555 0199 from my DIDWW number +1 510 555 0100 through my DIDWW outbound trunk.
```

The skill first asks which setup you want, then only the questions that setup needs. For incoming calls: the number, what the agent should do and say first, the project ID, where the backend runs, and the transfer target. For outbound calls: the number to call, the caller ID, and what the agent should say.

> [!NOTE]
> The skill never asks you to paste the API key, the webhook secret or the outbound trunk password into the chat. It creates a private file (mode 600) and opens it for you to fill in; both scripts read it and redact the values from their logs.

## Step 3. What gets configured

### Incoming calls

All DIDWW inbound changes go through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool.

- **Inbound SIP trunk.** Host `sip.api.openai.com` (EU data residency: `sip-eu.api.openai.com`), port 5061, User Part of R-URI = your project ID, TLS signaling, SRTP SDES media, codecs PCMU, PCMA and telephone-event, IPv4, and a capacity limit matching the expected concurrency. The default Diversion setting stays: DIDWW sends the called number in the `Diversion` header, while `To` carries the project ID. The DID is assigned to this trunk.
- **OpenAI webhook.** Start the server first, then create a project webhook for `realtime.call.incoming` with the full HTTPS URL, including the path (for example `https://voice.example.com/webhook`). Copy the signing secret at creation. The project in the trunk and the webhook must be the same, or calls fail with 400 Bad Request after about 15 seconds.
- **Backend.** `scripts/webhook_server.py` is a stdlib-only starting point. It verifies the webhook signature, ignores duplicate deliveries, reads the called number from `Diversion`, accepts calls to numbers in its `AGENTS` table with your instructions, and rejects other numbers with 603. After accepting, it opens the call WebSocket and asks the agent to greet the caller, with tools disabled for that first turn; without this the agent waits silently.

  ```bash
  python3 webhook_server.py --env-file ~/.didww-openai.env
  ```

  It refuses to start without both secrets, with a `tel:` transfer target, or with a target that would route back to the agent.

> [!NOTE]
> OpenAI's SIP endpoint has no digest authentication. Anyone who knows your project ID can send an INVITE to it, so the backend's number match is routing, not authentication. Keep the project ID private, keep the signed webhook check, and keep the rejection of unknown numbers in place.

### Transfers to a live person

DIDWW supports cold transfers by SIP REFER on incoming calls. The server calls OpenAI's `refer` endpoint, OpenAI sends REFER to DIDWW, and DIDWW places the new call through your outbound trunk.

- **Outbound trunk** (DIDWW User Panel): **Credentials & IP-based** authentication, DIDWW's seven inbound signaling IPs in **Allowed SIP IP addresses** (`46.19.209.14`, `46.19.210.14`, `46.19.212.14`, `46.19.213.14`, `46.19.214.14`, `46.19.215.14`, `185.238.173.14`), **Media encryption mode** SRTP SDES, a low **24 hour limit (USD)** and only the destinations you need.
- **Inbound trunk:** **Max Transfers** 1 or higher, and the outbound trunk's username and password on its **Authorization** tab. You enter them in the panel yourself.
- **Server:** the transfer target is `sip:+{number}@{DIDWW outbound host}`, for example `sip:+15105550199@fra.eu.out.didww.com`. DIDWW does not accept `tel:` targets. The tool description and the instructions say the agent may transfer only after the caller asks for a person.

### Outbound calls with GPT-Live

- **Outbound trunk:** as for transfers, SRTP SDES is required, and OpenAI's ranges `13.79.45.80/28`, `23.98.140.64/28`, `40.67.149.176/28` and `40.83.204.240/28` are added to **Allowed SIP IP addresses**. OpenAI publishes them as SRTP media ranges; they are shared by all OpenAI customers, so keep the trunk's credential authentication. The caller ID must be allowed by the trunk's **CLI Settings**.
- **Calls:** `scripts/gptlive_call.py` creates one call per run with `POST /v1/live/sessions`, sending your instructions and the outbound trunk's username and password. It attaches to the call at once, logs ringing, answer or failure (with DIDWW's SIP response) and the transcript, and hangs up at a time limit or on Ctrl-C. It never retries, because every request dials the number again.

  ```bash
  python3 gptlive_call.py --env-file ~/.didww-openai.env --to +15105550199 \
    --from +15105550100 --instructions-file agent.txt --check
  python3 gptlive_call.py --env-file ~/.didww-openai.env --to +15105550199 \
    --from +15105550100 --instructions-file agent.txt
  ```

  `--check` validates everything without placing a call.
- **Delegation:** GPT-Live hands reasoning and tool work to your server. If nothing answers, the agent says it needs a moment and then stays silent. The script answers every delegated task with a short result, so the agent continues; replace that function with your real lookups or actions.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. Incoming: one call from a mobile phone; the server log shows the call accepted and the agent greets you.
2. Transfer: a short conversation without asking for a person (no transfer), then ask for one; the destination rings and shows the original caller's number.
3. A call to a number not in `AGENTS` is rejected.
4. Outbound: one call to a phone you can answer; the log shows ringing and answered, and the DIDWW **Outbound Call Logs** show the call with Success on your trunk.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Incoming call fails with 400 Bad Request after about 15 seconds | The project ID on the trunk is not the webhook's project, the event type is not selected, or the webhook URL is unreachable | Match the project; select `realtime.call.incoming`; test the URL from outside |
| The server rejects every call | It matched the `To` header, which carries the project ID | Read the called number from `Diversion` |
| Call connects, agent silent | No greeting request after accepting, or the accept failed | Send `response.create`; check the server log and the API key |
| OpenAI shows "bad url" when you create the webhook | The server is not running or not public, or the URL lacks the path | Start the server first; use the full URL |
| The agent transfers callers who did not ask | Greeting with tools enabled, or a vague tool description | Greet with `tool_choice: "none"`; transfer only on explicit request |
| Transfer Failed: 401/Unauthorized | No Authorization on the inbound trunk | Add the outbound trunk's credentials |
| Transfer Failed: 500/No suitable media | Outbound trunk media is not SRTP SDES | Set SRTP SDES |
| 603 Unconfigured xfer for tel URIs | `tel:` transfer target | Use `sip:+{number}@{DIDWW outbound host}` |
| GPT-Live call fails with 403 Forbidden and no DIDWW call record | OpenAI's ranges are missing from Allowed SIP IP addresses | Add the four ranges |
| GPT-Live call fails with 500 No suitable media | Outbound trunk media is not SRTP SDES | Set SRTP SDES |
| `outbound_sip_not_enabled` | Outbound SIP is not enabled for your OpenAI organization | Ask OpenAI to enable it |
| GPT-Live agent says it needs a moment, then stays silent | An unanswered delegation | Answer every `session.delegation.created` |
| Incoming calls stop after the test computer slept | A temporary tunnel was deleted and its address changed | Start a new tunnel and update the webhook URL; use a permanent host for real calls |

## Keys, billing and safety

- **OpenAI credentials.** API keys are at `platform.openai.com/api-keys`, webhooks at `platform.openai.com/settings/project/webhooks`; the signing secret is shown once. Billing is prepaid credits under Settings, Billing; check the auto-recharge setting and the credit expiry terms. Realtime bills in audio tokens, not minutes, so the per-minute cost depends on how much of the call is speech.
- **Two balances.** DIDWW is prepaid, and so is OpenAI. Either one reaching zero stops calls. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Outbound charges.** Outbound calls and every transfer leg are billed per minute at the DIDWW outbound rate for the destination, on top of the inbound call and OpenAI usage. Set a low **24 hour limit (USD)** on the outbound trunk.

## Additional resources

- [DIDWW OpenAI integration guide](https://doc.didww.com/integrations/openai/index.html): the full step-by-step setup this skill follows.
- [DIDWW to xAI Grok](didww-to-xai.md): a near-identical SIP interface for incoming calls, with digest authentication at the number level.
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-openai-realtime`](https://github.com/didww/ai/tree/main/skills/didww-to-openai-realtime) in the didww/ai repository. Package: [npmjs.com/package/didww-to-openai-realtime](https://www.npmjs.com/package/didww-to-openai-realtime).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
