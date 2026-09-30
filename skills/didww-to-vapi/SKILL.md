---
name: didww-to-vapi
description: >
  Connect a DIDWW phone number to a Vapi assistant over BYO SIP trunking,
  as automatically as Vapi allows. Use whenever the user wants a Vapi
  assistant on a real phone number via DIDWW, mentions pairing DIDWW with
  Vapi, byo-sip-trunk credentials, sip.vapi.ai, or debugging calls
  between the two. Covers inbound, outbound, agent binding and the
  credential-ID ingress trap.
---

# DIDWW to Vapi

Vapi is fully API-first for this connection, but its official MCP
(`https://mcp.vapi.ai/mcp`, Bearer API key) is READ-ONLY for trunks and
numbers: it lists and inspects but cannot create. So the write path is
REST, wrapped in `scripts/connect.py`; use the MCP for verification and
assistant management afterwards.

## The one fact that breaks most Vapi trunk setups

Vapi's inbound ingress embeds the credential:
`{number}@{credential_id}.sip.vapi.ai` (EU: `.sip.eu.vapi.ai`). The
credential must exist BEFORE the DIDWW inbound trunk can be built,
because the trunk's destination host is that per-credential hostname.
Order of operations below respects this; never copy an ingress host from
someone else's tutorial.

## The flow

1. **Confirm in one message:** which DIDWW number (or country to buy),
   which assistant (existing ID or create one), region (US or EU), and
   transfer target if any.
2. **DIDWW outbound trunk first (DIDWW MCP, OAuth):** create it, note the
   generated username/password and region host (`fra.eu.out.didww.com`
   etc.). Set spend limits (10 to 50 USD/day) and channel caps.
3. **Vapi credential and number (`scripts/connect.py`):** one run creates
   the `byo-sip-trunk` credential (gateway = the DIDWW termination host,
   outboundAuthenticationPlan = step 2's credentials) and the
   `byo-phone-number` bound to the assistant. It prints the exact ingress
   URI for step 4.
4. **DIDWW inbound trunk (DIDWW MCP):** host =
   `{credential_id}.sip.vapi.ai` from step 3's output, port 5060. Also
   allowlist Vapi's signaling IPs on the trunk (US `44.229.228.186`,
   `44.238.177.138`; EU `63.182.83.170`); missing IPs show up as 401s on
   inbound. Attach the DID.
5. **Verify:** inbound from a mobile, outbound caller ID, transfer.
   Vapi's MCP (`list_phone_numbers`, `get_call`) is handy for reading
   call outcomes without leaving the conversation.

## Failure map

- Inbound 401: Vapi signaling IPs not allowed on the DIDWW trunk, or the
  trunk points at bare `sip.vapi.ai` instead of the per-credential host.
- Outbound auth failures: outboundAuthenticationPlan credentials do not
  match the DIDWW outbound trunk; regenerate and re-run the script with
  `--update`.
- Number rejected on create: try `numberE164CheckEnabled: false` (the
  script sets it) and the number without the plus.

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
trunking and Vapi's BYO SIP trunk API; verified August 2026.
