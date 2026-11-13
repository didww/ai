# DIDWW to ElevenLabs skill

Use the **didww-to-elevenlabs** skill with **Claude Code** to connect a DIDWW phone number to an **ElevenAgents** voice agent over SIP. The connection is one SIP trunk pair on the DIDWW side plus one number import on the ElevenLabs side; the skill drives both from a conversation.

- Route incoming calls from a DIDWW number to an ElevenLabs agent.
- Place outbound calls from the agent through DIDWW with the DIDWW number as caller ID.
- Import the number into ElevenLabs with matching digest credentials, and assign the agent.
- Transfer calls from the agent to a live person with SIP REFER through DIDWW.

This skill automates the steps described in the [ElevenLabs integration guide](https://doc.didww.com/integrations/elevenlabs/index.html) and the [AI-to-Live Agent call transfer guide](https://doc.didww.com/integrations/elevenlabs/ai-to-liveagent-call-transfers.html). Read those guides for the manual path and screenshots.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: number, inbound trunk | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| DIDWW: outbound trunk, spend limits | You, in the DIDWW User Panel. The MCP has no outbound trunk tools | Your panel login |
| ElevenLabs: agent creation and configuration, number-to-agent assignment | ElevenLabs hosted MCP `https://api.us.elevenlabs.io/v1/mcp` | OAuth sign-in, no keys |
| ElevenLabs: number import (not available in their MCP), and the credential change for transfers | REST `POST /v1/convai/phone-numbers`, or `PATCH /v1/convai/phone-numbers/{id}` with `--update`, via `scripts/import_number.py` | One `xi-api-key`, or a guided dashboard step |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage numbers and inbound trunks under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- For outbound calls, access to DIDWW outbound trunks on the account. If **Voice**, **Outbound Trunks** in the DIDWW User Panel shows **Get Access**, apply there first ([Get access to outbound trunks](https://doc.didww.com/voice/outbound-trunks/get-access.html)): it needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. Inbound calls work without it.
- An ElevenLabs account with an agent, or a description of the agent you want created.
- The ElevenLabs MCP connected in Claude Code, or an ElevenLabs API key for the import script only:

  ```bash
  claude mcp add --scope user --transport http elevenlabs https://api.us.elevenlabs.io/v1/mcp
  ```

  Then run `/mcp` and sign in to ElevenLabs. Use the `api.us.elevenlabs.io` host: the `api.elevenlabs.io/v1/mcp` endpoint names `https://api.us.elevenlabs.io/v1/mcp` as its resource in its OAuth metadata, and Claude Code then stops with "Couldn't start sign-in for elevenlabs".

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-elevenlabs
```

It copies the skill into `~/.claude/skills/didww-to-elevenlabs/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-elevenlabs
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Connect my DIDWW number +33 1 44 55 66 77 to my ElevenLabs agent "Reception". Transfer to +33 6 12 34 56 78 when the caller asks for a human.
```

The skill confirms in one message: which DIDWW number (or which country to buy one in), which agent (existing, or created from your description), whether the agent places calls, and the transfer destination if any. Outbound calls and transfers both need a DIDWW outbound trunk, whose username and password are then used on the inbound side too, so the skill settles this before it creates anything. Then it works through the steps below.

## Step 3. What gets configured

### DIDWW side

The number and the inbound trunk are configured through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool. The outbound trunk is created by you in the DIDWW User Panel, because the MCP has no outbound trunk tools.

- **Inbound SIP trunk.** Host `sip.rtc.elevenlabs.io`, port 5060, transport TCP (TLS is supported; media encryption must then match on both sides), R-URI username `{DID}`, which DIDWW fills with the called number in E.164 without the `+`. Digest authentication is preferred over IP filtering because ElevenLabs sends from distributed addresses and static IPs are an enterprise feature. For an inbound-only line the skill generates the username and password. When the agent places calls or transfers them, the inbound trunk uses the **outbound trunk's** username and password instead, which you enter under **Authorization**, **Enable Authorization** in the DIDWW User Panel so the password stays out of the chat; a separately generated pair breaks transfers. For transfers the skill also sets **Max Transfers** to 1 and the network protocol to match the outbound trunk. The DID is assigned to this trunk.
- **Outbound SIP trunk.** Needed for calls the agent places and for transfers, and created first when either is planned. You create it in the DIDWW User Panel under **Voice**, **Outbound Trunks**, **Create New**, because the DIDWW MCP has no outbound trunk tools. If that page shows **Get Access**, the account is not approved for outbound calling yet: the application needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours. The inbound side can go live meanwhile. Choose the **Credentials & IP-Based** authentication method. It needs at least one **Allowed SIP IP address**. For transfers, list DIDWW's own inbound signaling IPs (see [Step 4](#step-4-set-up-live-agent-transfers)). For calls the agent places, ElevenLabs' addresses are needed as well, and ElevenLabs publishes no SIP source range for its standard endpoint. With ElevenLabs Enterprise static SIP (`sip-static.rtc.elevenlabs.io`), list the /24 block ElevenLabs gives you; otherwise contact DIDWW support (support@didww.com) before enabling outbound calls. Do not enter `0.0.0.0/0`; DIDWW advises against open ranges. Set **Media encryption mode** to match the platform side. DIDWW generates the username and password; give them to the agent in a file or environment variables rather than pasting them into the chat, and it passes them to the platform side. Enable the trunk if it shows **Disabled**. The host is the one nearest to the platform's region: `nyc.us.out.didww.com`, `lac.us.out.didww.com`, `mia.us.out.didww.com`, `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com` or `hk.out.didww.com`.
- **Spend controls.** On the outbound trunk, under **Termination**: **24 Hour Limit (USD)** at its minimum of 50 (the default is 3000, and DIDWW disables the trunk when the limit is reached), **Capacity limit** matching the expected concurrency, and the usage limit notification on. Under **CLI Settings**, allow only the connected number as caller ID; under **Destination Dialing Settings**, reject all destinations except the countries the agent calls. On the inbound trunk the skill sets a capacity limit through the MCP.

### ElevenLabs side

- **Agent.** Created or selected through the ElevenLabs MCP: voice, language and prompt.
- **Number import.** `scripts/import_number.py` calls the phone-numbers API. The number is imported in E.164 without the `+`, as DIDWW sends it. The inbound authentication is a `credentials` object that must match the DIDWW inbound trunk's digest pair exactly. `--media-encryption` matches the DIDWW trunks: `disabled` when their SRTP mode is **Disable** (the DIDWW default), `required` for SRTP; without it the script sends ElevenLabs' default, `allowed`. The outbound address is the DIDWW outbound host as a bare hostname, no `sip:` prefix and no port, with the transport in lower case (`tcp` or `tls`) and the DIDWW outbound trunk credentials.
- **Agent assignment.** Through the MCP (`agents_update_phone_number`) or the script's `--agent` flag.

To run the import by hand:

```bash
ELEVENLABS_INBOUND_PASS=... DIDWW_TRUNK_PASS=... ELEVENLABS_API_KEY=... \
python3 ~/.claude/skills/didww-to-elevenlabs/scripts/import_number.py \
  --number 33144556677 --label "Paris line" --inbound-user USER \
  --outbound-host fra.eu.out.didww.com --outbound-user OUSER \
  --transport tcp --media-encryption disabled --agent AGENT_ID
```

The passwords can also be passed as `--inbound-pass` and `--outbound-pass`; the environment keeps them out of shell history. If the DIDWW outbound trunk does not exist yet, leave out the three outbound values: the number is imported for inbound calls only, and the outbound trunk can be added later.

With an outbound trunk, `USER` and the inbound password are the outbound trunk's username and password, the same as `OUSER` and its password.

> [!IMPORTANT]
> Import the number in E.164 format **without** the `+`, for example `33144556677`, as the [ElevenLabs integration guide](https://doc.didww.com/integrations/elevenlabs/index.html) says in Step 2: Enter Your Phone Number. The DIDWW inbound trunk sends the called number as `{DID}`, which has no `+`, and a number imported with the `+` does not match it. The script accepts the number either way and drops a leading `+`.

## Step 4. Set up live-agent transfers

The skill follows the [AI-to-Live Agent call transfer guide](https://doc.didww.com/integrations/elevenlabs/ai-to-liveagent-call-transfers.html). The ElevenLabs agent transfers with an in-dialog SIP REFER. DIDWW authenticates the REFER with the inbound trunk's credentials, then places the new call to the live person through your **outbound** trunk, from DIDWW's own signaling addresses. Every item below is needed:

- **Outbound trunk.** Under **Allowed SIP IP addresses**, add DIDWW's inbound signaling IPs: `46.19.209.14`, `46.19.210.14`, `46.19.212.14`, `46.19.213.14`, `46.19.214.14`, `46.19.215.14` and `185.238.173.14`. Allow the transfer destination's country under **Destination Dialing Settings**.
- **Inbound trunk.** **Authorization** carries the outbound trunk's username and password. **Max Transfers** (Signalling tab) is 1 or more; 0, the default, disables transfers. **Network Protocol** matches the IP version of the outbound trunk's allowed addresses, for example **force IPv4** for the IPv4 list above.
- **ElevenLabs number.** Its inbound credentials are the same outbound trunk pair. For a number already imported with another pair, the skill runs:

  ```bash
  ELEVENLABS_INBOUND_PASS=... ELEVENLABS_API_KEY=... \
  python3 ~/.claude/skills/didww-to-elevenlabs/scripts/import_number.py \
    --update PHONE_NUMBER_ID --inbound-user OUSER --media-encryption disabled
  ```

  This sends `PATCH /v1/convai/phone-numbers/{id}` with an `inbound_trunk_config.credentials` object. Inbound calls fail while the DIDWW inbound trunk and the ElevenLabs number carry different pairs, so the two are changed back to back.
- **Agent.** The skill enables the **Transfer to number** system tool through the ElevenLabs MCP (`agents_update_transfer_to_number_tool`) with transfer type **SIP REFER**, destination type **SIP URI**, a destination such as `sip:+33612345678@fra.eu.out.didww.com` (the number in E.164 with the `+`, at your outbound trunk's DIDWW host) and a condition such as "the caller asks for a person". The agent must be published and live.

> [!NOTE]
> If the DIDWW outbound trunk is not available yet, the inbound side can go live first with a generated pair. Adding transfers later switches both the DIDWW inbound trunk and the ElevenLabs number to the outbound trunk's pair.

## Step 5. Verify the connection

The skill ends every build with the same checks. Do them before real traffic:

1. One inbound call from a mobile phone reaches the agent.
2. One outbound call from the agent shows the DIDWW number as caller ID.
3. One transfer, if configured: ask the agent for a person; the destination rings and audio flows both ways. Call detail records appear on the DIDWW side, an outbound one for the transferred leg.

## Troubleshooting

The skill carries this failure map and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| Claude Code shows "Couldn't start sign-in for elevenlabs" | The ElevenLabs MCP was added at `https://api.elevenlabs.io/v1/mcp`, whose OAuth metadata names the `api.us` host | Remove it and add `https://api.us.elevenlabs.io/v1/mcp` |
| Import fails with 409 `phone_number_conflict` | ElevenLabs numbers are unique across all workspaces, and this number is registered in another one | Remove it from the other ElevenLabs workspace first; DIDWW cannot do this |
| Inbound call rejected or silent | Digest mismatch between the DIDWW trunk and the import's inbound credentials, or the number was imported with a `+` while DIDWW sends it without one | Re-enter the same username and password on both sides; import the number in E.164 without the `+`, for example `33144556677` |
| SIP 488, or one-way audio | Media encryption enabled on one side only | Match SRTP on the DIDWW trunk and the ElevenLabs import |
| Outbound calls fail | A `sip:` prefix or a port pasted into the Address field, or the wrong region host | Use the bare DIDWW host, for example `fra.eu.out.didww.com` |
| Everything works but spend is higher than expected | The outbound trunk kept its default 24-hour limit of 3000 USD | Lower **24 Hour Limit (USD)** to 50 in the DIDWW User Panel and set the capacity limits |
| Outbound call rejected by DIDWW | Source IP not in the outbound trunk's Allowed SIP IP addresses, caller ID not allowed in its CLI settings, destination not allowed, or the 24-hour limit reached, which disables the trunk | Check the outbound trunk in the DIDWW User Panel and re-enable it |
| The agent announces a transfer, then nothing happens or the call drops | DIDWW refused the REFER: **Max Transfers** is 0, or the inbound trunk's Authorization is not the outbound trunk's username and password | Set **Max Transfers** to 1 or more and put the outbound trunk's pair on the inbound trunk and the ElevenLabs number |
| The transfer starts but the destination never rings | DIDWW's inbound signaling IPs are missing from the outbound trunk's allowed addresses, the destination country is not allowed, the 24-hour limit disabled the trunk, or the inbound and outbound trunks use different IP versions | Add the seven DIDWW IPs, allow the destination, re-enable the trunk, and match **Network Protocol** on the inbound trunk |
| The agent never transfers | The agent is not published, or the Transfer to number tool is missing or not set to SIP REFER with a SIP URI destination | Publish the agent and check the tool's Human Transfer Rules |
| Inbound calls stop after transfers were set up | Only one of the DIDWW inbound trunk and the ElevenLabs number was switched to the outbound trunk's pair | Put the same pair on both |

## Keys, billing and safety

- **ElevenLabs credentials.** API keys live at `elevenlabs.io/app/settings/api-keys` (workspace keys: profile icon, Workspace settings, Service Accounts). A key is needed only for the import script; everything else uses the OAuth MCP. Agent minutes draw from the same credit pool as text-to-speech, and LLM and telephony are billed on top of the subscription.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [ElevenLabs integration guide](https://doc.didww.com/integrations/elevenlabs/index.html): the same connection configured by hand.
- [Configure AI-to-Live Agent call transfers](https://doc.didww.com/integrations/elevenlabs/ai-to-liveagent-call-transfers.html): the transfer setup configured by hand.
- [ElevenLabs SIP trunking documentation](https://elevenlabs.io/docs/agents-platform/phone-numbers/sip-trunking).
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-elevenlabs`](https://github.com/didww/ai/tree/main/skills/didww-to-elevenlabs) in the didww/ai repository. Package: [npmjs.com/package/didww-to-elevenlabs](https://www.npmjs.com/package/didww-to-elevenlabs).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
