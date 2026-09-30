---
name: didww-to-ultravox
description: >
  Connect a DIDWW phone number to an Ultravox Realtime voice agent over
  SIP. Use whenever the user wants an Ultravox agent on a real phone
  number via DIDWW, mentions pairing DIDWW with Ultravox, an account SIP
  domain, agent_ addresses, allowedCidrRanges, or debugging calls between
  the two. Covers the address-based routing model that makes Ultravox
  different from every number-import platform.
---

# DIDWW to Ultravox

Ultravox has no number-import object and no official MCP: inbound routing
is ADDRESS-BASED. Calls arrive at `agent_{agent_id}@{account_sip_domain}`
and the account's SIP settings decide what is accepted. That inverts the
usual setup: instead of importing the number into the platform, you point
the DIDWW trunk at the right SIP address. The DIDWW MCP (OAuth) automates
the carrier side; `scripts/connect.py` automates the Ultravox side via
its REST API (`X-API-Key` header).

## The two routing shapes: pick one in intake

**One agent per number (simple):** the DIDWW inbound trunk's destination
is the agent's own SIP address. Works when the trunk can carry a custom
destination user part; where the DIDWW trunk format sends the DID as the
user part instead, use the second shape.

**Fallback webhook (flexible, needed for multiple numbers):** calls that
match no agent address hit the account's `fallbackHandler` webhook, which
receives `toUri` (the DID) and answers `startAgentCall` with the chosen
agent, or `reject`. A tiny public HTTPS endpoint maps DID to agent; this
is the general answer for carrier trunks and the honest cost of
Ultravox's model.

## The flow

1. **Confirm in one message:** number (or country to buy), agent, one
   agent per number or a DID-to-agent map, transfer target.
2. **Read the account SIP domain:** `GET /api/sip` (the `domain` field is
   read-only and per-account; never guess it). `scripts/connect.py
   --show` prints it.
3. **Ultravox side (`scripts/connect.py`):** set `allowedCidrRanges` to
   DIDWW's signaling ranges (or leave open and rely on the reject logic),
   set `allowedAgents` or the `fallbackHandler` URL, and for outbound
   note that calls are placed per call via `POST /api/calls` with
   `medium.sip.outgoing` carrying the DIDWW host and outbound trunk
   credentials.
4. **DIDWW side (MCP):** inbound trunk pointed at the account SIP domain
   (destination per the routing shape chosen), DID attached, outbound
   trunk created with credentials for step 3's outgoing calls, spend
   limits set (10 to 50 USD/day).
5. **Verify:** inbound from a mobile; outbound via a test
   `POST /api/calls`; transfers (Ultravox has the richest transfer set:
   cold REFER, warm, bridged). SIP minutes bill separately from model
   time; mention it.

## Failure map

- Inbound 603 rejects: the To address matches no allowed agent and no
  fallback handler is set; fix `allowedAgents` regex or add the handler.
- Inbound never arrives: CIDR allowlist missing DIDWW's signaling range,
  or the trunk sends the DID as user part while routing expected an
  agent address (switch to the fallback shape).
- Outbound auth failures: credentials in `medium.sip.outgoing` do not
  match the DIDWW outbound trunk.

## Panel map and money

Ultravox keys: `app.ultravox.ai`, Settings, API Keys, Generate New Key.
Pricing runs two meters per call: 0.05 USD/min agent time plus SIP
minutes billed separately (about 0.005 USD/min); quote both. 30 free
minutes to start; pay-as-you-go has concurrency caps that only the
100 USD/month Pro plan removes. DIDWW side: prepaid; top-up, Auto-charge
and Low Balance Notification (OFF by default) in Billing, Payment
Methods.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-ultravox) SIP
trunking and Ultravox's SIP docs; verified August 2026.
