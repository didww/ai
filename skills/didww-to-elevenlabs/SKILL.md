---
name: didww-to-elevenlabs
description: >
  Connect a DIDWW phone number to an ElevenLabs voice agent over SIP, as
  automatically as both platforms allow. Use whenever the user wants an
  ElevenLabs agent (Agents Platform, Conversational AI) on a real phone
  number via DIDWW, mentions pairing DIDWW with ElevenLabs, importing a
  SIP trunk into ElevenLabs, sip.rtc.elevenlabs.io, live-agent transfers
  (SIP REFER), or debugging calls between the two. Covers inbound,
  outbound, transfers and verification.
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
| ElevenLabs agent create/config, number-to-agent assignment | ElevenLabs hosted MCP `https://api.us.elevenlabs.io/v1/mcp` | OAuth, no keys |
| ElevenLabs number IMPORT (the one gap: not in their MCP), and the credential switch for transfers | REST `POST /v1/convai/phone-numbers` (`PATCH .../{id}` with `--update`) via `scripts/import_number.py` | one `xi-api-key`, or a guided dashboard step |

If either MCP is missing, register it (`claude mcp add --scope user
--transport http didww https://api.didww.com/mcp`, and `claude mcp add
--scope user --transport http elevenlabs
https://api.us.elevenlabs.io/v1/mcp`) and have the user authenticate
once in `/mcp`. Use the `api.us` host: `api.elevenlabs.io/v1/mcp`
answers too, but its OAuth metadata names
`https://api.us.elevenlabs.io/v1/mcp` as the resource, and Claude Code
then refuses to start sign-in ("Couldn't start sign-in for elevenlabs:
Try again in a moment").

## The flow

1. **Confirm in one message:** which DIDWW number (or country to buy one
   in), which agent (existing, or create from a described purpose),
   whether the agent places calls, and the transfer destination if any.
   Outbound calls and transfers both need the DIDWW outbound trunk, and
   its username/password then become the inbound digest pair too, so
   settle this before creating anything.
2. **Outbound trunk (DIDWW panel, the user does it), first, when the
   agent places calls or transfers them:** under Voice, Outbound Trunks
   a Get Access button means the account is not approved yet (business
   account with company name and VAT/TAX ID; DIDWW answers within 48
   business hours): say so and build the inbound side meanwhile with an
   invented pair, then switch pairs as in "Live-agent transfers". Create
   New, Authentication method Credentials & IP-Based, which needs at
   least one Allowed SIP IP. For transfers: DIDWW's seven inbound
   signaling IPs (below). For calls the agent places: ElevenLabs' egress
   as well, but ElevenLabs publishes no SIP egress range for the
   standard endpoint; Enterprise static SIP
   (`sip-static.rtc.elevenlabs.io`) comes with a /24 to list. Without
   it, send the user to DIDWW support (support@didww.com); never invent
   a range or suggest `0.0.0.0/0`. Note the IP version of the list
   (IPv4 only, for example): the inbound trunk's network protocol must
   match it.
   Termination: 24 Hour Limit (USD) at its minimum, 50 (default 3000),
   Capacity limit = expected concurrency, usage limit notification on;
   CLI limited to the DID; Destination dialing Reject All except the
   countries the agent calls and the transfer destinations; Media
   encryption mode matching the import. Enable the trunk if it shows
   Disabled. Host: the region-nearest of `fra.eu.out.didww.com`,
   `ams.eu.out.didww.com`, `nyc.us.out.didww.com`,
   `lac.us.out.didww.com`, `mia.us.out.didww.com`, `sg.out.didww.com`,
   `hk.out.didww.com`. The user hands the generated credentials over in
   a file or environment variables, not pasted into chat.
3. **Inbound trunk (DIDWW MCP `create_sip_trunk`):** host
   `sip.rtc.elevenlabs.io`, port 5060, `transport_protocol` TCP (TLS on
   5061 supported; match media encryption on both sides), `username`
   `{DID}` (DIDWW puts the called number there in E.164 WITHOUT the
   plus, which is why step 5 imports it without one), `capacity_limit`
   = expected concurrent calls. Digest auth (preferred over IP
   filtering: ElevenLabs egress IPs are distributed; static IPs are
   enterprise-only) with:
   - outbound calls or transfers planned: the OUTBOUND trunk's username
     and password from step 2, never an invented pair (an invented pair
     breaks transfers). The user enters them in the panel (Inbound
     Trunks, Edit, Authorization, Enable Authorization) so the outbound
     password stays out of the chat; via the MCP (`auth_enabled`,
     `auth_user`, `auth_password`) only if the user accepts it passing
     through the chat. For transfers also `max_transfers` 1 or more
     (default 0 refuses every REFER) and `network_protocol_priority`
     matching the outbound trunk (`force IPv4`, the default, when its
     Allowed SIP IPs are IPv4 only).
   - inbound only: an invented username/password pair, set through the
     MCP.
   Attach the DID.
4. **Agent (ElevenLabs MCP):** create or select the agent, set voice,
   language and prompt.
5. **Import the number:** run `scripts/import_number.py` (or walk the
   dashboard's Import SIP Trunk form). The number goes in E.164 without
   the `+` (`--number 33144556677`; the script also takes `+` and drops
   it). Inbound auth is a `credentials` object that must match step 3's
   digest pair exactly; `--media-encryption` matches the DIDWW trunks
   (`disabled` for SRTP mode Disable, the DIDWW default; `required` for
   SRTP; left out, the script sends ElevenLabs' default `allowed`).
   Outbound address
   is the DIDWW host from step 2, hostname only, no `sip:` prefix,
   transport lowercase (`tcp` or `tls`), credentials from the outbound
   trunk. Without an outbound trunk yet, leave out all three
   `--outbound-*` values: the number imports for inbound calls only.
   Passwords can come from `ELEVENLABS_INBOUND_PASS` and
   `DIDWW_TRUNK_PASS` instead of the command line. Then assign the agent
   to the number (MCP: `agents_update_phone_number`, or the script's
   `--agent` flag, which sets `agent_id` on the import).
6. **Transfers, if a destination was given:** "Live-agent transfers"
   below.
7. **Verify:** inbound call from a mobile, outbound call showing the DID
   as caller ID, transfer if configured. CDRs visible on the DIDWW side.

## Live-agent transfers

Following DIDWW's AI-to-Live Agent guide
(`doc.didww.com/integrations/elevenlabs/ai-to-liveagent-call-transfers.html`),
proven on a real call. ElevenLabs transfers with an in-dialog SIP REFER.
DIDWW authenticates the REFER with the inbound trunk's Authorization
pair, then places the new leg to the live agent through the customer's
OUTBOUND trunk, from DIDWW's own signaling IPs. So all of these hold:

- Outbound trunk (Credentials & IP-Based) lists DIDWW's inbound
  signaling IPs in Allowed SIP IPs: `46.19.209.14`, `46.19.210.14`,
  `46.19.212.14`, `46.19.213.14`, `46.19.214.14`, `46.19.215.14`,
  `185.238.173.14` (doc.didww.com General SIP Information). The transfer
  destination's country is allowed in its Destination dialing.
- DIDWW inbound trunk: Authorization = the outbound trunk's username and
  password; `max_transfers` >= 1; `network_protocol_priority` = the IP
  version of the outbound trunk's Allowed SIP IPs (`force IPv4` for the
  list above). MCP `update_sip_trunk` sets the last two; the user pastes
  the pair in the panel as in step 3.
- ElevenLabs number: inbound credentials = that same pair. On a number
  already imported with another pair: `ELEVENLABS_INBOUND_PASS=...
  scripts/import_number.py --update <phone_number_id> --inbound-user
  <outbound user> --media-encryption <matching the trunk>` (REST `PATCH
  /v1/convai/phone-numbers/{id}` with an `inbound_trunk_config.credentials`
  object; the MCP's `agents_update_phone_number` takes the same body but
  puts the password in the chat). Change this and the DIDWW inbound
  trunk back to back: inbound calls fail while the two pairs differ.
- Agent: ElevenLabs MCP `agents_update_transfer_to_number_tool`. Read
  the agent first (`agents_get`): the call writes the whole tool slot,
  so carry over existing transfers. `name` `transfer_to_number`,
  `params.transfers` items `{"transfer_type": "sip_refer",
  "transfer_destination": {"type": "sip_uri", "sip_uri":
  "sip:+33612345678@fra.eu.out.didww.com"}, "condition": "the caller
  asks for a person"}`: the destination in E.164 with the `+`, at the
  outbound trunk's DIDWW host. The agent must be published and live.

Verify: call the DID, ask for a person; the destination rings and
audio flows both ways. DIDWW shows an inbound CDR and an outbound CDR
on the outbound trunk.

## Failure map for this exact pairing

- Claude Code says "Couldn't start sign-in for elevenlabs": the MCP was
  registered at `api.elevenlabs.io/v1/mcp`; remove it and add
  `https://api.us.elevenlabs.io/v1/mcp`.
- Import answers 409 `phone_number_conflict`: ElevenLabs numbers are
  unique across all workspaces, and this one is registered in another
  workspace; it has to be removed there first (DIDWW cannot do it).
- Inbound rejected or silent: digest mismatch between the DIDWW trunk and
  the import's inbound auth, or the number was imported with a `+`
  while DIDWW sends `{DID}` without one (re-import without the plus).
- 488 or one-way audio: media encryption mismatch (SRTP on one side
  only, or `--media-encryption required` against an SRTP-off trunk).
- Outbound dead: `sip:` prefix or a port pasted into the Address field,
  or wrong region host.
- Outbound 403 or rejected from DIDWW: source IP not in the outbound
  trunk's Allowed SIP IPs, caller ID not allowed in its CLI settings,
  destination not allowed, or the 24 Hour Limit was reached (DIDWW then
  disables the trunk; re-enable it in the panel).
- Agent announces the transfer, then nothing happens or the call drops:
  DIDWW refused the REFER. `max_transfers` is 0 (the default), or the
  inbound trunk's Authorization is not the outbound trunk's pair (an
  invented inbound pair breaks transfers).
- REFER accepted but the destination never rings: DIDWW's inbound
  signaling IPs are missing from the outbound trunk's Allowed SIP IPs,
  the destination country is not allowed there, the 24 Hour Limit
  disabled the trunk, or the inbound and outbound trunks' network
  protocols differ (IPv4 against IPv6).
- No transfer at all: the agent is not published or live, the tool is
  missing or not `sip_refer` to a `sip_uri` destination, or the
  condition is too narrow for what callers say.
- Inbound calls stop right after setting up transfers: only one side was
  switched to the outbound pair (the DIDWW inbound trunk or the
  ElevenLabs number); both must carry the same pair.
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
verified August 2026, DIDWW outbound trunk rules October 2026; number
format, MCP host and live-agent transfers verified on real calls October
2026.
