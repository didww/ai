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
(OAuth) automates the carrier side. The agent-to-number binding is the
gap: Vogent documents it only in the dashboard (Numbers tab under the
Agent), so the skill imports automatically and then walks the user
through that single click.

## The flow

1. **Confirm in one message:** number (or country to buy), which agent,
   transfer target if any.
2. **DIDWW side (MCP):** inbound trunk with host `sip.vogent.ai`, digest
   auth with an invented username/password pair, DID attached. Outbound
   trunk created; note host and generated credentials. Spend limits 10 to
   50 USD/day, honest channel caps.
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
trunking and Vogent's number API; verified August 2026.
