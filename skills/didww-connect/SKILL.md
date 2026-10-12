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

DIDWW is the constant: number, two-way SIP trunking, spend controls. The AI
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

The DIDWW MCP (`https://api.didww.com/mcp`, OAuth sign-in, no keys)
covers the number and the inbound trunk. It has NO outbound trunk
tools: the outbound trunk, and with it the 24-hour spend limit, is
created by the user in the DIDWW panel.

1. Number: buy or confirm the DID (registration-required countries add a
   verification wait; say so before promising dates).
2. Inbound trunk (MCP): host = the platform's SIP ingress, digest auth
   preferred, media encryption matched to the platform's setting,
   `capacity_limit` = the concurrent calls the user expects. Attach the
   DID.
3. Outbound trunk (panel, only if the agent places calls):
   - Access first: under Voice, Outbound Trunks a Get Access button means
     the account is not approved yet. The application needs a business
     account (company name, VAT/TAX ID) and DIDWW answers within 48
     business hours, so say this before promising outbound calling;
     inbound goes live meanwhile.
   - The user creates it under Voice, Outbound Trunks, Create New, with
     Authentication method Credentials & IP-Based. That method needs at
     least one Allowed SIP IP: the platform's published SIP egress
     addresses (each pairing skill lists them). Where the platform
     publishes none, do not invent a range and do not suggest
     `0.0.0.0/0` (DIDWW advises against open ranges); send the user to
     DIDWW support (support@didww.com) for that case.
   - Termination: 24 Hour Limit (USD) at its minimum, 50 (the default is
     3000; the trunk is disabled when the limit is reached), Capacity
     limit = expected concurrent calls, usage limit notification on.
     CLI: allow only the connected DID. Destination dialing: Reject All
     except the country prefixes the agent calls. Media encryption mode
     matched to the platform.
   - Host: the region-nearest of `nyc.us.out.didww.com`,
     `lac.us.out.didww.com`, `mia.us.out.didww.com`,
     `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com`,
     `hk.out.didww.com`; port 5060 UDP/TCP, 5061 TLS. A new trunk can
     show Disabled: enable it before the first call. The user hands the
     generated username and password over in a file or environment
     variables, not pasted into chat.
4. Money safety: the Low Balance Notification (Billing, Payment Methods,
   OFF by default) on, plus the limits above.
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
registration). LiveKit `sip:{sip_subdomain}.sip.livekit.cloud` (the SIP URI
from Project settings, not derived from the project URL; 5060
TCP/UDP, 5061 TLS, digest; region-pinned
`{sip_subdomain}.{eu|us|uk|india|japan|aus|canada|sa}.sip.livekit.cloud`;
numbers on its trunk need the `+`).

Allowed SIP IPs for the DIDWW outbound trunk (the platform's egress):
Vapi US `44.229.228.186/32`, `44.238.177.138/32`, EU `63.182.83.170/32`.
Retell `18.98.16.120/30`, `3.42.144.0/23`, `153.57.128.0/18` (plus
`143.223.88.0/21`, `161.115.160.0/19` for some US traffic). LiveKit
Cloud (Canada, EU, India, Japan, US) `143.223.88.0/21`,
`161.115.160.0/19`, `153.57.128.0/18`; self-hosted: its public IP.
ElevenLabs, Ultravox, Vogent: no published range outside enterprise
plans (ElevenLabs Enterprise static SIP is a /24 from their support);
ask DIDWW support. OpenAI and xAI: no outbound trunk needed.

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
under all of the above; platform details verified August 2026, DIDWW
outbound trunk rules October 2026.
