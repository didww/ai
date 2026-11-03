# didww-to-elevenlabs

Agent skill: connect a DIDWW phone number to ElevenLabs over SIP, as
automatically as the platform allows. MCP-first where MCPs exist
(DIDWW's is OAuth, no keys), stdlib-only scripts where they do not, and
every irreversible or spending action is confirmation-gated. No
telemetry; plain markdown plus readable Python.

## Install

```bash
npx didww-to-elevenlabs
```

Straight from GitHub, no registry: `npx skills add didww/ai --skill didww-to-elevenlabs`.
From a clone of this repo: `./skills/didww-to-elevenlabs/install.sh`, or copy this folder to
`~/.claude/skills/didww-to-elevenlabs`. Restart Claude Code afterwards; the skill triggers on its own
when you mention DIDWW together with ElevenLabs.

Every installer copies files and nothing else; an existing install is moved to
`~/.claude/skill-backups/`, never overwritten.

## Connect the MCPs

```bash
claude mcp add --scope user --transport http didww https://api.didww.com/mcp
claude mcp add --scope user --transport http elevenlabs https://api.us.elevenlabs.io/v1/mcp
```

Then sign in to both with `/mcp`. Use the `api.us.elevenlabs.io` host: `api.elevenlabs.io/v1/mcp`
names it as the resource in its OAuth metadata, and Claude Code then refuses to start sign-in.

## Importing the number

The one step the ElevenLabs MCP cannot do. The skill runs it for you; by hand:

```bash
ELEVENLABS_INBOUND_PASS=... ELEVENLABS_API_KEY=... \
python3 ~/.claude/skills/didww-to-elevenlabs/scripts/import_number.py \
  --number 33144556677 --inbound-user USER --media-encryption disabled --agent AGENT_ID
```

> [!IMPORTANT]
> Import the number in E.164 **without** the `+`, as DIDWW's
> [ElevenLabs guide](https://doc.didww.com/integrations/elevenlabs/index.html) says: the DIDWW inbound
> trunk sends the called number as `{DID}`, which has no plus. The script accepts either form and
> drops the `+`. `--media-encryption` matches the DIDWW trunks (`disabled` when SRTP is off).

Live-agent transfers (SIP REFER) follow DIDWW's
[AI-to-Live Agent guide](https://doc.didww.com/integrations/elevenlabs/ai-to-liveagent-call-transfers.html):
the outbound trunk allows DIDWW's seven inbound signaling IPs, the DIDWW inbound trunk and the
ElevenLabs number both use the outbound trunk's username and password (`import_number.py --update
PHONE_NUMBER_ID` switches an imported number), Max Transfers is 1 or more, and the agent's Transfer
to number tool uses SIP REFER to a SIP URI such as `sip:+33612345678@fra.eu.out.didww.com`.

| Symptom | Fix |
|---|---|
| "Couldn't start sign-in for elevenlabs" | Re-add the MCP at `https://api.us.elevenlabs.io/v1/mcp` |
| Inbound call rejected or silent | Same digest pair on both sides; number imported without the `+` |
| Transfer announced, then nothing | Max Transfers >= 1; inbound trunk Authorization = the outbound trunk's pair |
| Transfer starts, destination never rings | DIDWW's signaling IPs on the outbound trunk; inbound Network Protocol matches it |

Full walkthrough and troubleshooting: [docs/didww-to-elevenlabs.md](https://github.com/didww/ai/blob/main/docs/didww-to-elevenlabs.md).

## Tests

`bash test.sh` in this folder: stdlib Python plus node, no network, no keys.

## Family

Hub: [didww-connect](https://github.com/didww/ai/tree/main/skills/didww-connect) picks the platform, does the universal DIDWW
wiring and ships the health monitor. All nine skills live in [didww/ai](https://github.com/didww/ai) under
`skills/`, each installable with `npx didww-to-<platform>`.
Companion for building the agent itself: voice-agent-telephony.

License: MIT
