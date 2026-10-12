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
| DIDWW: number, inbound trunk | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| DIDWW: outbound trunk, spend limits | You, in the DIDWW User Panel. The MCP has no outbound trunk tools | Your panel login |
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
- An API key and secret from the Cloud project's **Settings**, **API keys**. The secret is shown once. Note the **Project URL** (`wss://<project>.livekit.cloud`) and the **SIP URI** (`sip:<sip-subdomain>.sip.livekit.cloud`) on the same settings page. Their subdomains differ, so copy each value; do not derive one from the other.
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
LIVEKIT_URL=wss://<project>.livekit.cloud LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... \
  python3 ~/.claude/skills/didww-to-livekit/scripts/connect.py --show
```

Then one run creates the inbound trunk (the number in E.164 with the `+`, digest `auth_username` and `auth_password`, codecs limited to PCMA and PCMU, SRTP required) and the dispatch rule (one room per call, `room_config.agents[0].agent_name` set to your worker's name, bound to that trunk only). Add the outbound flags to also create the outbound trunk from the DIDWW outbound trunk's credentials. The trunks are secure by default: TLS for signaling on the outbound trunk and SRTP required on both. `--sip-uri` only makes the script print the host to enter on the DIDWW trunk; it is not sent to LiveKit.

```bash
LIVEKIT_URL=wss://<project>.livekit.cloud LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... \
  python3 ~/.claude/skills/didww-to-livekit/scripts/connect.py \
  --number +33144556677 --agent front-desk --inbound-user USER --inbound-pass PASS \
  --outbound-host fra.eu.out.didww.com --outbound-user OUSER --outbound-pass OPASS \
  --sip-uri sip:<sip-subdomain>.sip.livekit.cloud
```

If the inbound side already exists, add the outbound trunk alone. Running the full command again would create a second inbound trunk:

```bash
LIVEKIT_URL=wss://<project>.livekit.cloud LIVEKIT_API_KEY=... LIVEKIT_API_SECRET=... \
  python3 ~/.claude/skills/didww-to-livekit/scripts/connect.py --outbound-only \
  --number +33144556677 \
  --outbound-host fra.eu.out.didww.com --outbound-user OUSER --outbound-pass OPASS
```

`--allow-ip` adds a CIDR allowlist; on LiveKit Cloud, `allowed_addresses` is enabled per project by LiveKit support, while digest authentication needs no enablement.

To create the trunks by hand instead, use `lk sip inbound create`, `lk sip dispatch create` and `lk sip outbound create`, or the LiveKit Cloud dashboard: **Telephony**, **SIP trunks**, **Create new trunk**, **JSON editor** tab. The digest fields are available in the JSON editor.

### DIDWW side

The number and the inbound trunk are configured through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool. The outbound trunk is created by you in the DIDWW User Panel, because the MCP has no outbound trunk tools.

- **Inbound SIP trunk.** Created under **Voice**, **Inbound Trunks**, **Create New**, **SIP Trunk**:

  | Field | Value |
  |---|---|
  | Type | `Static Endpoint` |
  | User Part of R-URI | `{DID}`, which is what LiveKit matches against the trunk's `numbers` |
  | Host | `<sip-subdomain>.sip.livekit.cloud` (the SIP URI without `sip:`), or the region-pinned `<sip-subdomain>.<eu\|us\|uk\|india\|japan\|aus\|canada\|sa>.sip.livekit.cloud` |
  | Port and Transport | `5061` and `TLS` |
  | Authorization | **Enable Authorization**, with the same username and password given to the script |
  | Codecs | `PCMA` and `PCMU` only. LiveKit SIP supports PCMU, PCMA and G.722, and DIDWW has no G.722 |
  | SRTP Mode | `SRTP SDES` |

  The DID is assigned to this trunk.
- **Outbound SIP trunk.** You create it under **Voice**, **Outbound Trunks**, **Create New**, with the **Credentials & IP-Based** authentication method. DIDWW generates the username and password. Give them to the agent in a file or environment variables, and it passes them to the script. This method needs at least one **Allowed SIP IP address**: for LiveKit Cloud in the Canada, EU, India, Japan and US regions, `143.223.88.0/21`, `161.115.160.0/19` and `153.57.128.0/18`; for a self-hosted SIP service, its public IP address. SRTP with SDES is enabled in the trunk's media settings. If that page shows **Get Access**, the account is not approved for outbound calling yet: the application needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. The inbound side can go live meanwhile. Enable the trunk if it shows **Disabled**. The host is the one nearest to the platform's region: `nyc.us.out.didww.com`, `lac.us.out.didww.com`, `mia.us.out.didww.com`, `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com` or `hk.out.didww.com`.
- **Spend controls.** On the outbound trunk, under **Termination**: **24 Hour Limit (USD)** at its minimum of 50 (the default is 3000, and DIDWW disables the trunk when the limit is reached), **Capacity limit** matching the expected concurrency, and the usage limit notification on. Under **CLI Settings**, allow only the connected number as caller ID; under **Destination Dialing Settings**, reject all destinations except the countries the agent calls. On the inbound trunk the skill sets a capacity limit through the MCP.

> [!IMPORTANT]
> The script creates secure LiveKit trunks by default, so the DIDWW trunks must be set to match: **Transport** `TLS`, **Port** `5061` and **SRTP Mode** `SRTP SDES` on the inbound trunk, and SRTP with SDES on the outbound trunk. A DIDWW trunk left on TCP with SRTP disabled does not fall back to plain audio. The call fails with `400 Bad Request` inbound or `500 No suitable media` outbound.

### Plain trunks

Optional. To use unencrypted signaling and media, run the script with `--transport tcp --srtp disable` and set the DIDWW side to match:

| | DIDWW | LiveKit |
|---|---|---|
| Inbound | **Transport** `TCP`, **Port** `5060`, **SRTP Mode** `Disabled` | Inbound trunk without `media.encryption` |
| Outbound | No SRTP in the outbound trunk's media settings | Outbound trunk with `SIP_TRANSPORT_TCP` and no `media.encryption` |

On an outbound trunk, `--srtp allow` and `--srtp require` both offer encrypted media only, so `allow` is not a way to make encryption optional there.

### Worker

The agent code registers `agent_name` in its worker options and must be running when the call arrives. Only a LiveKit Agents worker is started by `agent_name`; any other bot has to join the room by itself. The dialed number is available as `sip.trunkPhoneNumber` and the caller as `sip.phoneNumber` on the SIP participant, so one worker can serve many numbers. Outbound calls are the worker's `CreateSIPParticipant` through the outbound trunk; the token needs the `sip.call` grant.

## Step 4. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone; the worker log shows the job picked up.
2. One outbound call from the worker shows the DIDWW number as caller ID.
3. One transfer, if configured.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| 407, then 401 on the INVITE | Digest pair differs between the DIDWW trunk and the LiveKit trunk. A single 407 is the normal challenge | Enter the same credentials on both sides |
| 404 on the INVITE | No inbound trunk or dispatch rule matched the call | Check that **User Part of R-URI** is `{DID}`, the DID is in the trunk's `numbers`, the rule's `trunk_ids` includes the trunk, and the source is inside `allowed_addresses` if set. A missing `+` is not the cause |
| 400 Bad Request on the INVITE | LiveKit could not agree on media: other codecs on the DIDWW trunk, or SRTP settings that disagree | Limit the DIDWW trunk to PCMA and PCMU; match SRTP on both trunks |
| Outbound 500 No suitable media, from DIDWW | The LiveKit outbound trunk offers SRTP and the DIDWW outbound trunk has none | Enable SRTP with SDES on the DIDWW trunk, or re-create the LiveKit trunks with `--srtp disable` |
| Rings then 486, or nobody answers | `agent_name` in the dispatch rule differs from the worker's, or the worker is not running | Match the names; start the worker |
| Answered, then dead after about 30 seconds | Media timeout: no RTP reaches LiveKit | Match SRTP on both trunks; on self-hosted, open UDP 10000 to 20000 |
| No audio or one-way audio, self-hosted | The SIP service advertises a private IP | Set `use_external_ip` or `nat_1_to_1_ip` on the SIP service |
| Outbound trunk refused when created | The outbound trunk address is not a bare host | Use `fra.eu.out.didww.com` with no `sip:` and no `;transport=` |
| Outbound 401, 403 or 407 from DIDWW | Wrong credentials, or the source is not in the **Allowed SIP IP address** list | Re-copy the credentials; add the LiveKit Cloud ranges or the SIP service's public IP |
| Outbound 484 | The dialed number is incomplete | Dial the full number in E.164 with the `+` |
| 405 when something tries to REGISTER | LiveKit never accepts registration | Set the DIDWW trunk **Type** to `Static Endpoint`; otherwise this only appears if a PBX was pointed at the URI |
| IP allowlist ignored on Cloud | `allowed_addresses` is enabled per project by LiveKit support | Use digest authentication, which needs no enablement |

## Keys, billing and safety

- **LiveKit credentials.** Keys are in the Cloud project's **Settings**, **API keys**, and the secret is shown once. LiveKit Cloud has a free tier with included agent-session and SIP minutes and a concurrency cap; paid tiers raise both. The model bill is separate: the STT, LLM and TTS providers your worker uses, or LiveKit Inference credits. LiveKit Cloud's static ranges, for the DIDWW outbound trunk's allowed IP list and for firewalls, are `143.223.88.0/21`, `161.115.160.0/19` and `153.57.128.0/18` (Canada, EU, India, Japan and US regions).
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-livekit`](https://github.com/didww/ai/tree/main/skills/didww-to-livekit) in the didww/ai repository. Package: [npmjs.com/package/didww-to-livekit](https://www.npmjs.com/package/didww-to-livekit).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
