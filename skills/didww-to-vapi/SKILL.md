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
assistant management afterwards. On the DIDWW side the MCP (OAuth)
covers the number and the inbound trunk, but has NO outbound trunk
tools: the DIDWW outbound trunk is created by the user in the panel.

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
2. **DIDWW outbound trunk first (DIDWW panel, the user does it):**
   step 3 needs its credentials, so with Vapi the inbound side waits for
   it too. Under Voice, Outbound Trunks a Get Access button means the
   account is not approved yet (business account with company name and
   VAT/TAX ID; DIDWW answers within 48 business hours): say so before
   promising any date. Create New, Authentication method Credentials &
   IP-Based, Allowed SIP IPs = Vapi's signaling IPs (US
   `44.229.228.186/32`, `44.238.177.138/32`; EU `63.182.83.170/32`).
   Termination: 24 Hour Limit (USD) at its minimum, 50 (default 3000),
   Capacity limit = expected concurrency, usage limit notification on;
   CLI limited to the DID; Destination dialing Reject All except the
   countries the assistant calls. Enable the trunk if it shows Disabled.
   Host: the region-nearest of `nyc.us.out.didww.com`,
   `lac.us.out.didww.com`, `mia.us.out.didww.com`,
   `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com`,
   `hk.out.didww.com`. The user hands the generated username and
   password over in a file or environment variables, not pasted into
   chat.
3. **Vapi credential and number (`scripts/connect.py`):** one run creates
   the `byo-sip-trunk` credential (gateway = the DIDWW termination host,
   outboundAuthenticationPlan = step 2's credentials) and the
   `byo-phone-number` bound to the assistant. It prints the exact ingress
   URI for step 4.
4. **DIDWW inbound trunk (DIDWW MCP):** host =
   `{credential_id}.sip.vapi.ai` from step 3's output, port 5060. Also
   allowlist Vapi's signaling IPs on the trunk (US `44.229.228.186`,
   `44.238.177.138`; EU `63.182.83.170`); missing IPs show up as 401s on
   inbound. Set `capacity_limit` to the expected concurrent calls.
   Attach the DID.
5. **Verify:** inbound from a mobile, outbound caller ID, transfer.
   Vapi's MCP (`list_phone_numbers`, `get_call`) is handy for reading
   call outcomes without leaving the conversation.

## Failure map

- Inbound 401: Vapi signaling IPs not allowed on the DIDWW trunk, or the
  trunk points at bare `sip.vapi.ai` instead of the per-credential host.
- Outbound auth failures: outboundAuthenticationPlan credentials do not
  match the DIDWW outbound trunk; regenerate and re-run the script with
  `--update`.
- Outbound 403 or rejected from DIDWW: caller ID not allowed in the
  outbound trunk's CLI settings, destination not allowed, Vapi's IPs
  missing from its Allowed SIP IPs, or the 24 Hour Limit was reached
  (DIDWW then disables the trunk; re-enable it in the panel).
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
trunking and Vapi's BYO SIP trunk API; verified August 2026, DIDWW
outbound trunk rules October 2026.
