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
| DIDWW (DID, inbound trunk) | DIDWW MCP `https://api.didww.com/mcp` | OAuth, no keys |
| DIDWW outbound trunk, 24-hour spend limit | The user, in the DIDWW panel: the MCP has no outbound trunk tools | Panel login |
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
   IPs are distributed; static IPs are enterprise-only). Set
   `capacity_limit` to the expected concurrent calls. Attach the DID.
   **Outbound trunk (DIDWW panel, the user does it):** only if the agent
   places calls. Under Voice, Outbound Trunks a Get Access button means
   the account is not approved yet (business account with company name
   and VAT/TAX ID; DIDWW answers within 48 business hours): say so and
   finish the inbound side meanwhile. Create New, Authentication method
   Credentials & IP-Based, which needs at least one Allowed SIP IP.
   ElevenLabs publishes no SIP egress range for the standard endpoint;
   Enterprise static SIP (`sip-static.rtc.elevenlabs.io`) comes with a
   /24 to list. Without it, send the user to DIDWW support
   (support@didww.com); never invent a range or suggest `0.0.0.0/0`.
   Termination: 24 Hour Limit (USD) at its minimum, 50 (default 3000),
   Capacity limit = expected concurrency, usage limit notification on;
   CLI limited to the DID; Destination dialing Reject All except the
   countries the agent calls; Media encryption mode matching the
   import. Enable the trunk if it shows Disabled. Host: the
   region-nearest of `fra.eu.out.didww.com`, `ams.eu.out.didww.com`,
   `nyc.us.out.didww.com`, `lac.us.out.didww.com`,
   `mia.us.out.didww.com`, `sg.out.didww.com`, `hk.out.didww.com`. The
   user hands the generated credentials over in a file or environment
   variables, not pasted into chat.
3. **Agent (ElevenLabs MCP):** create or select the agent, set voice,
   language and prompt.
4. **Import the number:** run `scripts/import_number.py` (or walk the
   dashboard's Import SIP Trunk form). Inbound auth is a
   `credentials` object that must match step 2's digest pair exactly;
   outbound address is the DIDWW host from step 2, hostname only, no
   `sip:` prefix, transport lowercase (`tcp` or `tls`), credentials from
   the outbound trunk. Without an outbound trunk yet, leave out all
   three `--outbound-*` values: the number imports for inbound calls
   only. Passwords can come from `ELEVENLABS_INBOUND_PASS` and
   `DIDWW_TRUNK_PASS` instead of the command line. Then assign the agent
   to the number (MCP: `agents_update_phone_number`, or the script's
   `--agent` flag, which sets `agent_id` on the import).
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
- Outbound 403 or rejected from DIDWW: source IP not in the outbound
  trunk's Allowed SIP IPs, caller ID not allowed in its CLI settings,
  destination not allowed, or the 24 Hour Limit was reached (DIDWW then
  disables the trunk; re-enable it in the panel).
- Everything works but money leaks: the outbound trunk kept its 3000 USD
  default limit; lower it to 50 in the panel.

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
verified August 2026, DIDWW outbound trunk rules October 2026.
