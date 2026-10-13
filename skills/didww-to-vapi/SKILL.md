---
name: didww-to-vapi
description: >
  Connect a DIDWW phone number to a Vapi assistant over BYO SIP trunking,
  as automatically as Vapi allows. Use whenever the user wants a Vapi
  assistant on a real phone number via DIDWW, mentions pairing DIDWW with
  Vapi, byo-sip-trunk credentials, sip.vapi.ai, or debugging calls
  between the two. Covers inbound, outbound, transfers and agent
  binding, following Vapi's and DIDWW's own DIDWW guides.
---

# DIDWW to Vapi

Vapi is fully API-first for this connection, but its official MCP
(`https://mcp.vapi.ai/mcp`, Bearer API key) is READ-ONLY for trunks and
numbers: it lists and inspects but cannot create. So the write path is
REST, wrapped in `scripts/connect.py`; use the MCP for verification and
assistant management afterwards. On the DIDWW side the MCP (OAuth)
covers the number and the inbound trunk, but has NO outbound trunk
tools: the DIDWW outbound trunk is created by the user in the panel.

## How the two sides recognise each other

Both vendors document the same setup (docs.vapi.ai "DIDWW SIP
integration" and doc.didww.com "Vapi" integration guide): the DIDWW
inbound trunk points at Vapi's regional host `sip.vapi.ai` (EU org:
`sip.eu.vapi.ai`), and Vapi recognises the call by its source: an
"inbound" Vapi credential lists DIDWW's seven signaling IPs as
inbound-only gateways (`46.19.209.14`, `46.19.210.14`, `46.19.212.14`,
`46.19.213.14`, `46.19.214.14`, `46.19.215.14`, `185.238.173.14`, from
doc.didww.com General SIP Information). The number is imported on that
credential in E.164 with the `+`. A separate "outbound" credential points
at the DIDWW outbound endpoint with digest auth. Transfers are SIP REFER:
DIDWW must allow them (`max_transfers` >= 1) and authenticate them with
the outbound trunk's credentials. Vapi signaling IPs (for the DIDWW
outbound trunk): US `44.229.228.186/32`, `44.238.177.138/32`; EU
`63.182.83.170/32` (docs.vapi.ai SIP networking; DIDWW's Vapi page shows
older EU addresses, trust Vapi's page for Vapi's IPs).

## The flow

1. **Confirm in one message:** which DIDWW number (or country to buy),
   which assistant (existing ID or create one), region of the Vapi
   organization (US or EU), transport (UDP default, TCP, or TLS on 5061)
   and transfer target if any.
2. **DIDWW outbound trunk (DIDWW panel, the user does it; needed for
   outbound calls and transfers, inbound can go live without it):**
   under Voice, Outbound Trunks a Get Access button means the account is
   not approved yet (business account with company name and VAT/TAX ID;
   DIDWW answers within 48 business hours): say so before promising any
   date. Create New, Authentication method Credentials & IP-Based,
   Allowed SIP IPs = Vapi's signaling IPs for the region PLUS DIDWW's
   seven signaling IPs (both guides require them for transfers). Never
   `0.0.0.0/0`. Termination: 24 Hour Limit (USD) at its minimum, 50
   (default 3000), Capacity limit = expected concurrency, usage limit
   notification on; CLI limited to the DID; Destination dialing Reject
   All except the countries the assistant calls. Enable the trunk if it
   shows Disabled. Host: the region-nearest of `nyc.us.out.didww.com`,
   `lac.us.out.didww.com`, `mia.us.out.didww.com`,
   `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com`,
   `hk.out.didww.com`. The user hands the generated username and
   password over in a file or environment variables (the script reads
   `DIDWW_TRUNK_PASS`), not pasted into chat.
3. **Vapi side (`scripts/connect.py`):** one run creates the outbound
   credential (with the `--didww-*` flags), the inbound credential (the
   seven DIDWW gateways, plus the outbound credentials for authenticated
   transfers) and the `byo-phone-number` (E.164 with `+`, bound to the
   assistant), on `api.vapi.ai` or, with `--eu`, `api.eu.vapi.ai`. Without
   the `--didww-*` flags it sets up inbound only. It prints the DIDWW-side
   values for steps 2 and 4.
4. **DIDWW inbound trunk (DIDWW MCP `create_sip_trunk`):** host
   `sip.vapi.ai` (EU `sip.eu.vapi.ai`), port 5060 (5061 for TLS),
   `transport_protocol` matching step 3, `max_transfers` 1,
   `capacity_limit` = expected concurrent calls; for transfers also
   `auth_enabled` true with `auth_user`/`auth_password` = the outbound
   trunk's credentials. Assign the DID.
5. **Transfers (optional):** a Vapi `transferCall` tool with a SIP
   destination `sip:+E164@<DIDWW outbound host>`, blind transfer,
   `sipVerb: refer`, added to the assistant's `model.toolIds`.
6. **Verify:** inbound from a mobile, outbound caller ID, transfer.
   Vapi's MCP (`list_phone_numbers`, `get_call`) is handy for reading
   call outcomes without leaving the conversation.

## Failure map

- Inbound never reaches the assistant: the number is not on the inbound
  credential, the credential is missing a DIDWW signaling IP (calls can
  come from any DIDWW location), the trunk points at the wrong region's
  host (EU org on `sip.vapi.ai`), or transport/port differ between the
  DIDWW trunk and the gateways.
- Outbound auth failures: the credentials in Vapi do not match the
  DIDWW outbound trunk; after regenerating them run
  `scripts/connect.py --rotate <outbound credential id> --rotate
  <inbound credential id> --didww-user ...` and update the DIDWW inbound
  trunk's `auth_user`/`auth_password` to the same pair.
- Outbound 403 or rejected from DIDWW: caller ID not allowed in the
  outbound trunk's CLI settings, destination not allowed, Vapi's IPs
  missing from its Allowed SIP IPs, or the 24 Hour Limit was reached
  (DIDWW then disables the trunk; re-enable it in the panel).
- Transfer fails: `max_transfers` is 0 on the inbound trunk, the inbound
  trunk's Authorization is off or stale, or DIDWW's signaling IPs are
  missing from the outbound trunk's Allowed SIP IPs.
- API calls fail although the key is right: an EU-hosted organization
  must use `api.eu.vapi.ai` (Vapi's guide); add `--eu`.

## Panel map and money

Vapi keys: `dashboard.vapi.ai/org/api-keys`, shown ONCE at creation.
Billing: prepaid credits (1 credit = 1 USD) with card auto-reload
(minimum 10 USD); 10 USD free credits with no card to start. Real
per-minute cost is the 0.05 USD platform fee PLUS provider passthrough,
typically 0.15 to 0.30 USD/min; numbers 2 USD/month. Critical warning
for the user: a negative balance freezes the wallet and add-ons
INCLUDING PHONE NUMBERS auto-cancel, so set auto-reload on day one.
DIDWW side: prepaid; top-up, Auto-charge and Low Balance Notification
(OFF by default) in Billing, Payment Methods.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-vapi) SIP
trunking and Vapi's BYO SIP trunk API; flow checked against Vapi's and
DIDWW's DIDWW/Vapi guides October 2026.
