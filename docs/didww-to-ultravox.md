# DIDWW to Ultravox skill

Use the **didww-to-ultravox** skill with **Claude Code** to connect a DIDWW phone number to an **Ultravox Realtime** voice agent over SIP. Ultravox is different from every number-import platform: there is no number object. Inbound routing is address-based. Calls arrive at the account's SIP domain, and its SIP settings decide what is accepted and which agent answers, by a pattern on the called user part (with DIDWW, the dialed number). The skill points the DIDWW trunk at that domain and configures those settings. It follows DIDWW's [Ultravox integration guide](https://doc.didww.com/integrations/ultravox/index.html).

- Read the account's SIP domain, which is per account and cannot be guessed.
- Configure the allowed source ranges, the accepted agents or a fallback webhook that maps numbers to agents.
- Transfer callers to a live person by SIP REFER through a DIDWW outbound trunk.
- Place outbound calls through DIDWW per call via the Ultravox calls API.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: number, inbound trunk | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| DIDWW: outbound trunk, spend limits | You, in the DIDWW User Panel. The MCP has no outbound trunk tools | Your panel login |
| Ultravox: account SIP settings (`GET` and `PATCH /api/sip`) | REST via `scripts/connect.py` | `ULTRAVOX_API_KEY` (`X-API-Key` header) |

Ultravox has no official MCP. Two routing shapes exist, and the skill asks which one you need:

- **Number patterns.** The DIDWW inbound trunk sends the dialed number as the user part (`{DID}`, the default) to the account SIP domain, and an `allowedAgents` entry with a pattern such as `^\+?33144556677$` sends it to the agent. Ultravox allows up to 20 entries, and one pattern can list several numbers. This is the setup in DIDWW's guide.
- **Fallback webhook.** Calls that match no allowed agent hit the account's `fallbackHandler` URL, which receives the dialed number as `toUri` and answers `startAgentCall` with the chosen agent, or `reject`. A small public HTTPS endpoint maps numbers to agents. Use it for more than 20 agents or for routing decided at call time.

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage numbers and inbound trunks under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- For outbound calls, access to DIDWW outbound trunks on the account. If **Voice**, **Outbound Trunks** in the DIDWW User Panel shows **Get Access**, apply there first ([Get access to outbound trunks](https://doc.didww.com/voice/outbound-trunks/get-access.html)): it needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. Inbound calls work without it.
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
  --allow-didww --allow-agent '3f2b6c1e-8a4d-4e2f-9b7a-1c2d3e4f5a6b=^\+?33144556677$'
```

`--allow-didww` restricts `allowedCidrRanges` to DIDWW's address ranges, `46.19.208.0/21` and `185.238.172.0/22`, which cover every DIDWW signaling location listed in [General SIP Information](https://doc.didww.com/voice/inbound-trunks/technical-data/sip.html). The allowlist is Ultravox's authentication for incoming calls: DIDWW's calls are accepted only once its ranges are on the list. Never use `0.0.0.0/0`, which accepts INVITEs from any address and which Ultravox itself advises against. `--allow-cidr` (repeatable, IPv4 only) adds other ranges. `--allow-agent AGENT_UUID[=TO_USER_REGEX]` (repeatable, up to 20) adds an entry to `allowedAgents`; without a pattern, the agent answers `agent_<agent_id>` addresses, and with one, for example `^\+?33144556677$`, it answers the DID itself. `--allow-all-agents` accepts every agent, and `--fallback-url` (https) sets the `fallbackHandler`. Ultravox generates the handler's signing secret; the script redacts it, and `--show --show-secrets` prints it when you configure the handler, which should verify every request.

Outbound calls are placed one per request with `POST /api/agents/{agent_id}/calls` and `medium.sip.outgoing` `{to, from, username, password}`. `to` must be a SIP URI at the DIDWW outbound host, for example `sip:+15105550199@fra.eu.out.didww.com`; a plain number is rejected with 400. `from` is the DIDWW number and `username` and `password` are the DIDWW outbound trunk's credentials. Do not retry a request automatically: each one dials again.

For transfers, the agent gets Ultravox's built-in `coldTransfer` tool with the `target` override `sip:+{number}@{DIDWW outbound host}` (not `tel:`, which DIDWW rejects with 603) and `sipVerb` `REFER`, plus a prompt rule to transfer only when the caller asks for a person. Ultravox sends the REFER to DIDWW, which dials the target through the outbound trunk.

### DIDWW side

The number and the inbound trunk are configured through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool. The outbound trunk is created by you in the DIDWW User Panel, because the MCP has no outbound trunk tools.

- **Inbound SIP trunk.** Host is the account SIP domain, port 5060, UDP, **User Part of R-URI** `{DID}`, IPv4 only. Codecs PCMU, PCMA and telephone-event only: Ultravox does not take G.729 or G.723 from DIDWW's default list. SRTP disabled. For transfers, **Max Transfers** 1 (the default 0 rejects REFER), and you turn on the trunk's **Authorization** in the DIDWW User Panel with the outbound trunk's username and password: DIDWW places the transferred call through the outbound trunk with them, and without them the transfer fails with `10020 error - Unauthorized`. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Needed for calls the agent places and for transfers. You create it in the DIDWW User Panel under **Voice**, **Outbound Trunks**, **Create New**, because the DIDWW MCP has no outbound trunk tools. If that page shows **Get Access**, the account is not approved for outbound calling yet: the application needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. The inbound side can go live meanwhile. Choose the **Credentials & IP-Based** authentication method and keep the credentials, because the Voximplant addresses below are shared by many customers. **Allowed SIP IP addresses**: for transfers, DIDWW's seven inbound signaling IPs `46.19.209.14`, `46.19.210.14`, `46.19.212.14`, `46.19.213.14`, `46.19.214.14`, `46.19.215.14` and `185.238.173.14`; for outbound calls, also Voximplant's published US and EU SIP servers (Ultravox's SIP runs on Voximplant) `69.167.178.6`, `69.167.178.14`, `3.147.160.14`, `78.13.219.90`, `3.123.246.217` and `143.244.45.166`. Check Voximplant's [current list](https://api.voximplant.com/getMediaResources?with_sbcs) and confirm your account's region with Ultravox. Do not enter `0.0.0.0/0`; DIDWW advises against open ranges. Keep **Media encryption mode** at **Disabled**: Ultravox offers unencrypted media, and with SRTP SDES its outbound calls fail with 500 No suitable media before ringing. DIDWW generates the username and password; give them to the agent in a file or environment variables rather than pasting them into the chat, and it passes them to the platform side. Enable the trunk if it shows **Disabled**. The host is the one nearest to the platform's region: `nyc.us.out.didww.com`, `lac.us.out.didww.com`, `mia.us.out.didww.com`, `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com` or `hk.out.didww.com`.
- **Spend controls.** On the outbound trunk, under **Termination**: **24 Hour Limit (USD)** at its minimum of 50 (the default is 3000, and DIDWW disables the trunk when the limit is reached), **Capacity limit** matching the expected concurrency, and the usage limit notification on. Under **CLI Settings**, allow only the connected number as caller ID; under **Destination Dialing Settings**, reject all destinations except the countries the agent calls. On the inbound trunk the skill sets a capacity limit through the MCP.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone reaches the agent.
2. One outbound call placed with a test `POST /api/agents/{agent_id}/calls` shows the DIDWW number as caller ID.
3. One transfer, if configured: the destination rings and the tool result reads Transfer succeeded.

After a call, `GET /api/calls/{call_id}/sip_logs` returns a link to its SIP log, which shows the source address and DIDWW's responses.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Inbound 603 rejected | The To address matches no allowed agent and no fallback handler is set | Fix the `allowedAgents` pattern or add the fallback URL |
| Inbound never arrives | The CIDR allowlist is missing DIDWW's ranges (`--allow-didww`), or no agent pattern matches the dialed number | Add the range; add a pattern for the number |
| Call drops at once or has no audio | A codec Ultravox does not take | Keep PCMU, PCMA and telephone-event on the inbound trunk |
| Transfer fails with `10020 error - Unauthorized` | The inbound trunk's Authorization is off or does not hold the outbound trunk's credentials | Turn it on with the outbound trunk's username and password |
| Transfer rejected | Max Transfers is 0, the target is `tel:` (603), DIDWW's seven IPs are missing on the outbound trunk, or SRTP is on there (500 No suitable media) | Fix the setting on the DIDWW trunk or the tool's target |
| Outbound call ends at once, SIP log shows 500 No suitable media | SRTP SDES on the outbound trunk | Set Media encryption mode to Disabled |
| Outbound call request returns 400 | `to` is not a SIP URI | Use `sip:+{number}@{DIDWW outbound host}` |
| Outbound authentication failures | Credentials in `medium.sip.outgoing` do not match the DIDWW outbound trunk | Use the DIDWW outbound trunk's generated username and password |
| Outbound call rejected by DIDWW | Source IP not in the outbound trunk's Allowed SIP IP addresses (the call's SIP log shows it), caller ID not allowed in its CLI settings, destination not allowed, or the 24-hour limit reached, which disables the trunk | Check the outbound trunk in the DIDWW User Panel and re-enable it |

## Keys, billing and safety

- **Ultravox credentials.** API keys are at `app.ultravox.ai`, Settings, API Keys. Ultravox bills two meters per call: agent time and SIP minutes. Pay-as-you-go has concurrency caps that only the paid plan removes.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [Ultravox integration guide](https://doc.didww.com/integrations/ultravox/index.html) in the DIDWW documentation: every panel step, with screenshots.
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-ultravox`](https://github.com/didww/ai/tree/main/skills/didww-to-ultravox) in the didww/ai repository. Package: [npmjs.com/package/didww-to-ultravox](https://www.npmjs.com/package/didww-to-ultravox).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
