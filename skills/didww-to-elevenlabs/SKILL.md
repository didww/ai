---
name: didww-to-elevenlabs
description: >
  Connect a DIDWW phone number to an ElevenLabs voice agent over SIP, as
  automatically as both platforms allow. Use whenever the user wants an
  ElevenLabs agent (Agents Platform, Conversational AI) on a real phone
  number via DIDWW, mentions pairing DIDWW with ElevenLabs, importing a
  SIP trunk into ElevenLabs, sip.rtc.elevenlabs.io, or debugging calls
  between the two. Covers inbound, outbound, transfers and verification.
---

# DIDWW to ElevenLabs

The connection is one trunk pair plus one number import. ElevenLabs runs
the agent; DIDWW carries the calls. Everything except one REST call is
automatable through OAuth MCPs, so prefer that path.

## Auth and automation map

| Side | Best path | Auth |
|---|---|---|
| DIDWW (trunks, DID, spend limits) | DIDWW MCP `https://api.didww.com/mcp` | OAuth, no keys |
| ElevenLabs agent create/config, number-to-agent assignment | ElevenLabs hosted MCP `https://api.elevenlabs.io/v1/mcp` | OAuth, no keys |
| ElevenLabs number IMPORT (the one gap: not in their MCP) | REST `POST /v1/convai/phone-numbers` via `scripts/import_number.py` | one `xi-api-key`, or a guided dashboard step |

If either MCP is missing, register it (`claude mcp add --scope user
--transport http didww https://api.didww.com/mcp`, same for elevenlabs)
and have the user authenticate once in `/mcp`.

## The flow

1. **Confirm in one message:** which DIDWW number (or country to buy one
   in), which agent (existing, or create from a described purpose), and
   the transfer destination if any.
2. **DIDWW side (MCP):** create the inbound SIP trunk with host
   `sip.rtc.elevenlabs.io`, port 5060, transport TCP (TLS supported;
   match media encryption on both sides), digest auth with an invented
   username/password pair (preferred over IP filtering: ElevenLabs egress
   IPs are distributed; static IPs are enterprise-only). Attach the DID.
   Create the outbound trunk, note its generated credentials and the
   region-nearest host (`fra.eu.out.didww.com`, `ams.eu.out.didww.com`,
   `nyc.us.out.didww.com`...). Set the 24h spend limit to 10 to 50 USD
   and honest channel caps; never leave defaults.
3. **Agent (ElevenLabs MCP):** create or select the agent, set voice,
   language and prompt.
4. **Import the number:** run `scripts/import_number.py` (or walk the
   dashboard's Import SIP Trunk form). Inbound auth is a
   `credentials` object that must match step 2's digest pair exactly;
   outbound address is the DIDWW host from step 2, hostname only, no
   `sip:` prefix, transport lowercase (`tcp` or `tls`), credentials from
   the outbound trunk. Then assign the agent to the number (MCP:
   `agents_update_phone_number`, or the script's `--agent` flag).
5. **Verify:** inbound call from a mobile, outbound call showing the DID
   as caller ID, transfer if configured. CDRs visible on the DIDWW side.

## Failure map for this exact pairing

- Inbound rejected or silent: digest mismatch between the DIDWW trunk and
  the import's inbound auth, or the number's plus sign differs from how
  it was imported.
- 488 or one-way audio: media encryption mismatch (SRTP on one side
  only).
- Outbound dead: `sip:` prefix or a port pasted into the Address field,
  or wrong region host.
- Everything works but money leaks: default spend limits were kept; go
  back to step 2.

## Panel map and money

ElevenLabs keys: `elevenlabs.io/app/settings/api-keys` (workspace keys:
profile icon, Workspace settings, Service Accounts); needed only for the
import script, everything else rides the OAuth MCP. Billing is
subscription tiers granting credits (Free includes 15 agent minutes,
Starter 6 USD, Creator 22 USD, Pro 99 USD); extra agent minutes about
0.08 USD, concurrency above the tier cap bills 2x, and LLM plus
telephony are billed on top. Warn that agent minutes drain the same
credit pool as TTS. DIDWW side: prepaid; top-up, Auto-charge and the
Low Balance Notification (OFF by default: switch it on) all live in
Billing, Payment Methods.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-elevenlabs) SIP
trunking and ElevenLabs' published SIP interconnect; both sides' guidance
verified August 2026.
