# DIDWW to xAI Grok skill

Use the **didww-to-xai** skill with **Claude Code** to connect a DIDWW phone number to an **xAI Grok Voice** agent over SIP. It follows DIDWW's [xAI integration guide](https://doc.didww.com/integrations/xai/index.html). xAI's documentation and console now use the name SpaceXSI.

- Answer incoming calls on a DIDWW number with a voice agent built in the xAI console, with no server of your own.
- Transfer callers to a live person by SIP REFER through a DIDWW outbound trunk.
- Or route the number to your own backend, which configures each call over a websocket.

> [!NOTE]
> xAI answers incoming calls only. It has no API to place calls and publishes no SIP source addresses, so outbound calls from Grok through DIDWW are not possible.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: inbound trunk, number, capacity limit | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| DIDWW: outbound trunk for transfers, inbound trunk Authorization | You, in the DIDWW User Panel. The MCP has no outbound trunk tools, and passwords stay out of the chat | Your panel login |
| xAI: voice agent and transfer tool | You, in the xAI console under **Voice Agents** | Your console login |
| xAI: adding the number to the agent | The console's **Deployment** tab, or `POST https://api.x.ai/v2/phone-numbers` via `scripts/register_number.py` | `XAI_API_KEY` (key type **Grok API**) |

The skill asks first which setup you want:

- **Console voice agent** (the default, as in DIDWW's guide). The number is added to an agent you build in the console. No backend.
- **Your own backend.** The number points at your webhook. For each call your code joins `wss://api.x.ai/v1/realtime?call_id=...` and sends the session configuration. Use it only when you need per-call logic the console cannot do.

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage numbers and inbound trunks under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- An [xAI console](https://console.x.ai/) account with prepaid credits. xAI creates **Grok API** keys only after a payment method is on file, and rejects calls when the credit balance reaches zero.
- For call transfers, access to DIDWW outbound trunks. If **Voice**, **Outbound Trunks** in the DIDWW User Panel shows **Get Access**, apply there first ([Get access to outbound trunks](https://doc.didww.com/voice/outbound-trunks/get-access.html)). Incoming calls work without it.
- For the backend setup only, somewhere to run a small public HTTPS endpoint.

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
Answer my DIDWW number +33 1 44 55 66 77 with a Grok voice agent from the xAI console, and transfer callers who ask for a person to +33 1 44 55 66 78.
```

The skill confirms the number (or the country to buy one in), what the agent should do, the transfer target and which setup you want.
It creates private files for the xAI API key and the outbound trunk's credentials, which you fill in yourself, so no secret passes through the chat.

## Step 3. What gets configured

### DIDWW side

- **Inbound SIP trunk.** Created through the MCP with these settings:
  - **Host** `sip.voice.x.ai`, **Port** `5061`, **Transport** TLS, **Network Protocol** IPv4;
  - **User Part of R-URI** `+{DID}`, because xAI matches the number in E.164 with the `+`;
  - codecs PCMU, PCMA and telephone-event, with **SRTP Mode** Disable;
  - **Max Transfers** `1` for transfers, and a capacity limit.

  The DID is assigned to it. If the number was routed elsewhere, the skill says what stops and asks first.
- **Authorization on the inbound trunk.** You enter it in the User Panel. For transfers, use the outbound trunk's **Username** and **Password**: DIDWW authenticates each transferred call with them. If the xAI number uses digest authentication, the same pair goes there.
- **Outbound SIP trunk, for transfers only.** You create it in the User Panel under **Voice**, **Outbound Trunks**, **Create New**:
  - **Credentials & IP-Based** authentication;
  - **Allowed SIP IP addresses**: DIDWW's seven inbound signaling IPs `46.19.209.14`, `46.19.210.14`, `46.19.212.14`, `46.19.213.14`, `46.19.214.14`, `46.19.215.14` and `185.238.173.14`. xAI sends nothing to this trunk;
  - **Media encryption mode** Disabled;
  - a **24 Hour Limit (USD)** of 50, and only the destinations transfers go to. A transfer to a destination the trunk does not allow is declined;
  - **CLI Settings** that allow the original caller's number.

### xAI side

- **Voice agent.** In the console, open **Voice Agents**, click **Create agent**, and enter the instructions. Turn on **Welcome message** with a greeting; without one the agent waits for the caller to speak. Then **Publish**.
- **The number.** On the agent's **Deployment** tab, under **Phone numbers**, click **Add number** and choose **Direct SIP**.
  - Enter the number in E.164 with the `+`.
  - For authentication, use **Username** and **Password** equal to the inbound trunk's Authorization. Alternatively, put DIDWW's seven signaling IPs in **Allowed addresses**. Never leave both empty.

  The same step with the script, reading the key and the digest pair from the private files:

  ```bash
  python3 ~/.claude/skills/didww-to-xai/scripts/register_number.py \
    --number +33144556677 --agent agent_XXXX --digest \
    --env-file ~/.xai.env --env-file ~/.didww-xai-outbound-trunk.env
  ```

  The agent ID is in the console address bar when the agent is open, or in the **Code integration** example on the **Deployment** tab. `--allow-didww` sets the IP list instead, `--list` shows the registered numbers, and `--delete` removes one.
- **Transfers.** Under **Tools**, add **Transfer call**, choose a **Custom** destination, and enter `sip:+{number}@{DIDWW outbound host}`, for example `sip:+33144556678@fra.eu.out.didww.com`. Never use `tel:`, and never the agent's own DIDWW number. Put the same rule ("transfer only after the caller asks for a person") in the tool's description and in the instructions.

### Your own backend instead

`register_number.py --webhook https://...` routes the number to your webhook and saves the one-time signing secret to an owner-only file.

On each `realtime.call.incoming` event, your backend does the following:
1. Verifies the signature.
2. Opens `wss://api.x.ai/v1/realtime?call_id={call_id}`.
3. Sends `session.update`, then `response.create`.

Transfers use `POST /v1/realtime/calls/{call_id}/refer` with a `sip:` target at the DIDWW outbound host. The webhook server in the [OpenAI skill](didww-to-openai-realtime.md) is the closest template.

## Step 4. Verify the connection

The skill ends every build with the same checks:

1. One incoming call from a mobile phone: the agent greets you, and the call appears on the agent's **Conversations** tab.
2. A short chat without asking for a person does not transfer the call.
3. Asking for a person transfers the call, and the destination answers.

The console's **Try it live** cannot test transfers; call the number.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| The call never reaches the agent | Host, port 5061 or TLS wrong; the R-URI is not `+{DID}`, or the number in xAI differs; the digest pair differs; xAI credits at zero | Compare the trunk with the settings above; enter the same pair on both sides; add credits |
| Silence when the call connects | **Welcome message** is off | Turn it on with a greeting and publish |
| No audio | Codecs other than G.711, or SRTP on the inbound trunk | Keep PCMU, PCMA and telephone-event; SRTP Disable |
| Transfer result `the call was declined` | Destination not allowed on the outbound trunk, Max Transfers 0, Authorization not the outbound pair, a `tel:` target, DIDWW's IPs missing, caller ID not allowed, or the 24-hour limit | Check the outbound trunk and the inbound trunk's Authorization |
| The transfer reaches voicemail | The destination did not answer; the transfer itself worked | Check the destination's forwarding and voicemail |
| The transferred call returns to the agent | The destination is the agent's own DIDWW number | Use the live person's number |
| No API key can be created | No payment method, or the **Cursor** key type was chosen | Add credits, then create a **Grok API** key |

## Keys, billing and safety

- **xAI credentials.** API keys are at `console.x.ai`, **API Keys**, with the key type **Grok API**. Credits are prepaid under **Billing**, **API spend management**, and xAI does not refund them. Voice costs 0.08 USD per minute. Optional auto top-up buys at least 5 USD at a time, up to a monthly cap. Invoiced billing is off by default, so calls fail once credits run out.
- **Two balances.** DIDWW is prepaid, and so is xAI. Either one reaching zero stops calls. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Transfers cost extra.** Each transfer is a new DIDWW outbound call, billed at the destination's rate on top of the incoming call.

## Additional resources

- [DIDWW's xAI integration guide](https://doc.didww.com/integrations/xai/index.html): every panel and console step, with screenshots.
- [DIDWW to OpenAI (Realtime and GPT-Live)](didww-to-openai-realtime.md): the sibling pairing and the template for the backend setup.
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-xai`](https://github.com/didww/ai/tree/main/skills/didww-to-xai) in the didww/ai repository. Package: [npmjs.com/package/didww-to-xai](https://www.npmjs.com/package/didww-to-xai).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
