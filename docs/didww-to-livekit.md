# DIDWW to LiveKit skill

Use the **didww-to-livekit** skill with **Claude Code** to connect a DIDWW phone number to a **LiveKit Agents** worker over SIP, on LiveKit Cloud or self-hosted. LiveKit is the SIP-to-WebRTC bridge and the agent runtime; the speech-to-text, language model and text-to-speech are whatever your worker code plugs in. This is the pairing for a bring-your-own-brain agent, including Claude as the model, with no hosted voice platform in between.

- Create the LiveKit inbound trunk for the DIDWW number with digest authentication.
- Create the dispatch rule that sends each call to a named agent in its own room.
- Optionally create the outbound trunk back to DIDWW for calls the worker places.

> [!IMPORTANT]
> A worker process must be running when the call arrives, either as a LiveKit Cloud agent deployment or on your own machine. No worker, no answer. For a no-code agent, use ElevenLabs, Vapi or Retell instead.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: trunks, number, spend limits | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| LiveKit: inbound trunk, dispatch rule, outbound trunk | LiveKit SIP API (Twirp over HTTPS) via `scripts/connect.py` | `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`; the script signs the requests |

LiveKit has no MCP; the script covers the whole SIP API in one run.

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage trunks and numbers under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- A LiveKit Cloud project, or a self-hosted LiveKit server with the SIP service.
- An API key and secret from the Cloud project's Settings, Keys. The secret is shown once. Note the project URL (`wss://<subdomain>.livekit.cloud`); the SIP URI on the same page is `sip:<subdomain>.sip.livekit.cloud`.
- The `agent_name` your worker registers in its worker options (explicit dispatch).

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-livekit
```

It copies the skill into `~/.claude/skills/didww-to-livekit/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-livekit
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Connect my DIDWW number +33 1 44 55 66 77 to my LiveKit agent "front-desk" on LiveKit Cloud, EU region, with outbound calling.
```

The skill confirms the number (or country to buy one in), the worker's `agent_name`, Cloud or self-hosted, the region, and whether outbound calls are needed.

## Step 3. What gets configured

### LiveKit side

List what exists first; the script does not deduplicate trunks:

```bash
LIVEKIT_URL=wss://<subdomain>.livekit.cloud LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... \
  python3 ~/.claude/skills/didww-to-livekit/scripts/connect.py --show
```

Then one run creates the inbound trunk (the number in E.164 with the `+`, digest `auth_username` and `auth_password`, SRTP allowed) and the dispatch rule (one room per call, `room_config.agents[0].agent_name` set to your worker's name, bound to that trunk only). Add the outbound flags to also create the outbound trunk from the DIDWW outbound trunk's credentials:

```bash
LIVEKIT_URL=wss://<subdomain>.livekit.cloud LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... \
  python3 ~/.claude/skills/didww-to-livekit/scripts/connect.py \
  --number +33144556677 --agent front-desk --inbound-user USER --inbound-pass PASS \
  --outbound-host fra.eu.out.didww.com --outbound-user OUSER --outbound-pass OPASS \
  --transport tcp --srtp allow
```

`--allow-ip` adds a CIDR allowlist; on LiveKit Cloud, `allowed_addresses` is enabled per project by LiveKit support, while digest authentication needs no enablement.

### DIDWW side

All DIDWW changes go through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool.

- **Inbound SIP trunk.** Host `<subdomain>.sip.livekit.cloud`, or the region-pinned `<subdomain>.<eu|us|uk|india|japan|aus|canada|sa>.sip.livekit.cloud`. Port 5060 for TCP or UDP, 5061 for TLS. Digest authentication with the same username and password given to the script, and SRTP matching the script's `--srtp` setting. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Created for this connection. DIDWW generates the username and password; the host is the one nearest to the platform's region: `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `nyc.us.out.didww.com` or `sg.out.didww.com`. The agent passes these credentials to the platform side.
- **Spend controls.** A 24-hour spend limit of 10 to 50 USD and channel limits matching the expected concurrency are set before the first call. The defaults are too high for a test agent.

### Worker

The agent code registers `agent_name` in its worker options and must be running when the call arrives. The dialed number is available as `sip.trunkPhoneNumber` and the caller as `sip.phoneNumber` on the SIP participant, so one worker can serve many numbers. Outbound calls are the worker's `CreateSIPParticipant` through the outbound trunk; the token needs the `sip.call` grant.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone; the worker log shows the job picked up.
2. One outbound call from the worker shows the DIDWW number as caller ID.
3. One transfer, if configured.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| 403 on the INVITE | Digest pair differs between the DIDWW trunk and the LiveKit trunk, or a region-pinned endpoint refused a call that local rules keep in-country | Re-enter the same credentials; try the unpinned host |
| 404 on the INVITE | The dialed number is on no inbound trunk, almost always a missing `+` | DIDWW shows numbers without the `+`; the LiveKit trunk needs it |
| Rings then 486, or nobody answers | `agent_name` in the dispatch rule differs from the worker's, or the worker is not running | Match the names; start the worker |
| Answered, then dead after about 30 seconds | Media timeout: no RTP reaches LiveKit | Match SRTP on both trunks; on self-hosted, open UDP 10000 to 20000 |
| One-way audio, self-hosted | The SIP service advertises a private IP | Set `use_external_ip` on the SIP service |
| Outbound 503 | The outbound trunk address is not a bare host | Use `fra.eu.out.didww.com` with no `sip:` and no port |
| 405 when something tries to REGISTER | LiveKit never accepts registration | DIDWW does not register; this only appears if a PBX was pointed at the URI |
| IP allowlist ignored on Cloud | `allowed_addresses` is enabled per project by LiveKit support | Use digest authentication, which needs no enablement |

## Keys, billing and safety

- **LiveKit credentials.** Keys are in the Cloud project's Settings, Keys, and the secret is shown once. LiveKit Cloud has a free tier with included agent-session and SIP minutes and a concurrency cap; paid tiers raise both. The model bill is separate: the STT, LLM and TTS providers your worker uses, or LiveKit Inference credits. For firewalls, LiveKit Cloud's static ranges are `143.223.88.0/21`, `161.115.160.0/19` and `153.57.128.0/18`.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-livekit`](https://github.com/didww/ai/tree/main/skills/didww-to-livekit) in the didww/ai repository. Package: [npmjs.com/package/didww-to-livekit](https://www.npmjs.com/package/didww-to-livekit).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
