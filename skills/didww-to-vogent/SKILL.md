---
name: didww-to-vogent
description: >
  Connect a DIDWW phone number to a Vogent voice agent over SIP import.
  Use whenever the user wants a Vogent agent on a real phone number via
  DIDWW, mentions pairing DIDWW with Vogent, sip_import numbers,
  sip.vogent.ai, or debugging calls between the two.
---

# DIDWW to Vogent

A clean self-serve pairing with one honest manual step. Vogent has no
official MCP; its API (Bearer key from the app's API Keys page) imports
the number in one call via `scripts/connect.py`, and the DIDWW MCP
(OAuth) automates the number and the inbound trunk. The DIDWW outbound
trunk is a second manual step: the MCP has no outbound trunk tools, so
the user creates it in the DIDWW panel. The agent-to-number binding is the
gap: Vogent documents it only in the dashboard (Numbers tab under the
Agent), so the skill imports automatically and then walks the user
through that single click.

## The flow

1. **Confirm in one message:** number (or country to buy), which agent,
   transfer target if any.
2. **DIDWW inbound trunk (MCP):** host `sip.vogent.ai`, digest auth
   with an invented username/password pair, `capacity_limit` = expected
   concurrent calls, DID attached.
   **DIDWW outbound trunk (panel, the user does it):** step 3's import
   needs its credentials. Under Voice, Outbound Trunks a Get Access button means the account is
   not approved yet (business account with company name and VAT/TAX ID;
   DIDWW answers within 48 business hours): say so and finish the
   inbound side meanwhile. Create New,
   Authentication method Credentials & IP-Based, which needs at least
   one Allowed SIP IP. Vogent has no static SIP egress range outside its
   enterprise plan: an enterprise customer gets the range from Vogent,
   anyone else asks DIDWW support (support@didww.com); never invent a
   range or suggest `0.0.0.0/0`.
   Termination: 24 Hour Limit (USD) at its minimum, 50 (default 3000),
   Capacity limit = expected concurrency, usage limit notification on;
   CLI limited to the DID; Destination dialing Reject All except the
   countries the agent calls. Enable the trunk if it shows Disabled.
   Host: the region-nearest of `nyc.us.out.didww.com`,
   `lac.us.out.didww.com`, `mia.us.out.didww.com`,
   `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com`,
   `hk.out.didww.com`. The user hands the generated credentials over in
   a file or environment variables, not pasted into chat.
3. **Vogent side (`scripts/connect.py`):** one call to
   `POST /phone_numbers` with `type: "sip_import"` carrying the E.164
   number, `terminationUri` (the DIDWW outbound host) and the step 2
   credentials.
4. **Bind the agent (dashboard, one step):** open the agent, Numbers tab,
   attach the imported number. Tell the user exactly this and wait for
   their done.
5. **Verify:** inbound from a mobile, outbound caller ID, transfer.

## Failure map

- Inbound rejected: digest pair mismatch between the DIDWW trunk and what
  Vogent expects for the imported number.
- Import accepted but calls dead: check the terminationUri has no `sip:`
  prefix and is the region-nearest DIDWW host.
- Outbound 403 or rejected from DIDWW: source not in the outbound
  trunk's Allowed SIP IPs, caller ID not allowed in its CLI settings,
  destination not allowed, or the 24 Hour Limit was reached (DIDWW then
  disables the trunk; re-enable it in the panel).
- Agent not answering: the dashboard binding step was skipped; it is not
  in the API response.

## Panel map and money

Vogent keys: `app.vogent.ai`, API Keys page in the sidebar. Pricing has
NO public page; marketing says around 0.09 USD/min, so verify the real
rate inside the panel before the user scales. DIDWW side: prepaid;
top-up, Auto-charge and Low Balance Notification (OFF by default) in
Billing, Payment Methods.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-vogent) SIP
trunking and Vogent's number API; verified August 2026, DIDWW outbound
trunk rules October 2026.
