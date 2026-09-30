---
name: didww-connect
description: >
  Connect a DIDWW phone number to ANY AI voice platform: helps choose the
  platform, then wires the SIP trunk pair and number. Use whenever the
  user wants a voice AI agent on a DIDWW number and has not committed to
  a platform, asks which AI platform to use with DIDWW, or names a
  platform that has no dedicated didww-to-X skill installed. Covers
  ElevenLabs, Vapi, Retell, Ultravox, Vogent, OpenAI Realtime, xAI,
  LiveKit and the enterprise-gated platforms.
---

# DIDWW Connect (any platform)

DIDWW is the constant: number, two-way SIP trunk, spend controls. The AI
side is a menu. This skill picks from the menu and executes the
universal wiring; when a dedicated `didww-to-<platform>` skill is
installed for the chosen platform, hand over to it, since it carries the
platform's connect script and failure map.

## Choosing, in one question

Ask what matters most and map:

| User signal | Platform | Automation ceiling |
|---|---|---|
| Easiest overall, best voices, OAuth everywhere | ElevenLabs | MCP OAuth both sides; one REST import call |
| API-first, EU region, BYO model keys | Vapi | REST scripts (their MCP is read-only for numbers) |
| Max MCP automation, one-call setup | Retell | Their MCP imports numbers and creates agents |
| Richest transfers, own speech model | Ultravox | REST; address-based routing, no number import |
| Small and simple | Vogent | REST import; agent binding is one dashboard click |
| Developer owns the brain, minimal stack | OpenAI Realtime or xAI | Webhook backend required, not no-code |
| Any STT/LLM/TTS combination (Claude as the brain), open source | LiveKit | REST script creates trunk + dispatch rule; the worker is code |
| Enterprise procurement in play | Bland, Synthflow, Regal | Sales-gated; never promise same-day |
| Data control, own servers | LiveKit self-hosted | didww-to-livekit for the wiring; voice-agent-telephony for the agent |

## Universal DIDWW-side wiring (identical for every platform)

Prefer the DIDWW MCP (`https://api.didww.com/mcp`, OAuth sign-in, no
keys) for all of it:

1. Number: buy or confirm the DID (registration-required countries add a
   verification wait; say so before promising dates).
2. Inbound trunk: host = the platform's SIP ingress, digest auth
   preferred, media encryption matched to the platform's setting. Attach
   the DID.
3. Outbound trunk: created per connection; note the generated
   credentials and region-nearest host (`fra.eu.out.didww.com`,
   `ams.eu.out.didww.com`, `nyc.us.out.didww.com`, `sg.out.didww.com`).
4. Safety: set the 24h spend limit to 10 to 50 USD and honest channel
   caps before the first call; defaults are too high.
5. Verify: one inbound call from a mobile, one outbound checking caller
   ID, one transfer if configured.

## Platform ingress cheat sheet

ElevenLabs `sip.rtc.elevenlabs.io:5060` (TCP/TLS, digest). Vapi
`{credential_id}.sip.vapi.ai` (create the credential FIRST; allowlist
their signaling IPs). Retell `sip.retellai.com` (TCP). Ultravox: the
account's own SIP domain, read from `GET /api/sip`, address-based
routing. Vogent `sip.vogent.ai`. OpenAI
`sip:{project_id}@sip.api.openai.com;transport=tls` (TLS+SRTP
mandatory, webhook backend is the gate). xAI
`sip:{number}@sip.voice.x.ai;transport=tls` (digest via number
registration). LiveKit `sip:{subdomain}.sip.livekit.cloud` (5060
TCP/UDP, 5061 TLS, digest; region-pinned
`{subdomain}.{eu|us|uk|india|japan|aus|canada|sa}.sip.livekit.cloud`;
numbers on its trunk need the `+`).

## Panels, keys and money

Every provider's exact key location, billing page, pricing model, free
tier and billing gotcha lives in `references/panels-and-billing.md`; read
it BEFORE sending a user into any dashboard, and always steer to
MCP/OAuth over keys where the table says one exists. Two rules that
apply to every build: turn on the provider's low-balance or auto-recharge
safety at setup time, and quote the realistic all-in per-minute cost
before real traffic starts. Remember two balances exist (DIDWW prepaid
plus the AI platform's), and both can silently stop service at zero.

## Monitoring the connection

Offer monitoring at the end of every build, not as an afterthought:
`scripts/monitor.py` checks the DIDWW balance against a threshold, DID
health (blocked or awaiting registration) and trunk presence, and exits
nonzero on warnings so it slots into cron or a scheduled task; daily is
the right cadence. With the DIDWW MCP connected the same checks run as
tool calls. Platform-side, enable the provider's own spend alerts per
`panels-and-billing.md`. When a warning fires, the fix is almost always
one of: top up a balance, complete a registration document, or re-enable
a cancelled add-on.

The dedicated skills (`didww-to-elevenlabs`, `didww-to-vapi`,
`didww-to-retell`, `didww-to-ultravox`, `didww-to-vogent`,
`didww-to-openai-realtime`, `didww-to-xai`, `didww-to-livekit`) carry connect scripts,
exact request shapes and per-pairing failure maps; prefer them when
installed. For building the agent itself, first-time account setup, or
debugging audio quality and latency, the voice-agent-telephony skill is
the companion.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-connect), a
licensed global operator providing the numbers and two-way SIP trunking
under all of the above; platform details verified August 2026.
