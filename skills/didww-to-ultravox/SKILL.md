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
the number and the inbound trunk (it has no outbound trunk tools: the
user creates the DIDWW outbound trunk in the panel); `scripts/connect.py` automates the Ultravox side via
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
3. **Ultravox side (`scripts/connect.py`):** always restrict
   `allowedCidrRanges` to DIDWW (`--allow-didww` sets `46.19.208.0/21`
   and `185.238.172.0/22`, which cover every DIDWW signaling location
   per doc.didww.com). The allowlist IS Ultravox's inbound
   authentication: until DIDWW's ranges are on it, DIDWW's INVITEs are
   not accepted, and never use `0.0.0.0/0` (any address; Ultravox
   itself advises against it).
   Then either `allowedAgents` (`--allow-agent AGENT_UUID[=TO_USER_REGEX]`,
   objects `{agentId, toUserPattern}`, max 20; the pattern defaults to
   `^agent_<agent_id>$`, so a DID-as-user-part trunk needs a pattern
   such as `^\+?33144556677$`) or the `fallbackHandler` URL (https;
   Ultravox generates its signing secret, which the handler must verify;
   `--show --show-secrets` reveals it, normal output redacts it). For outbound
   note that calls are placed per call via `POST /api/calls` with
   `medium.sip.outgoing` carrying the DIDWW host and outbound trunk
   credentials.
4. **DIDWW inbound trunk (MCP):** pointed at the account SIP domain
   (destination per the routing shape chosen), `capacity_limit` =
   expected concurrent calls, DID attached.
   **DIDWW outbound trunk (panel, the user does it, only for outgoing
   calls):** Under Voice, Outbound Trunks a Get Access button means the account is
   not approved yet (business account with company name and VAT/TAX ID;
   DIDWW answers within 48 business hours): say so and finish the
   inbound side meanwhile. Create New,
   Authentication method Credentials & IP-Based, which needs at least
   one Allowed SIP IP. Ultravox publishes no SIP egress range (its SIP
   runs on Voximplant): ask Ultravox support for the source addresses,
   or DIDWW support (support@didww.com); never invent a range or
   suggest `0.0.0.0/0`.
   Termination: 24 Hour Limit (USD) at its minimum, 50 (default 3000),
   Capacity limit = expected concurrency, usage limit notification on;
   CLI limited to the DID; Destination dialing Reject All except the
   countries the agent calls. Enable the trunk if it shows Disabled.
   Host: the region-nearest of `nyc.us.out.didww.com`,
   `lac.us.out.didww.com`, `mia.us.out.didww.com`,
   `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com`,
   `hk.out.didww.com`. The user hands the generated credentials over in
   a file or environment variables, not pasted into chat. These credentials go into `medium.sip.outgoing`.
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
- Outbound 403 or rejected from DIDWW: source not in the outbound
  trunk's Allowed SIP IPs, caller ID not allowed in its CLI settings,
  destination not allowed, or the 24 Hour Limit was reached (DIDWW then
  disables the trunk; re-enable it in the panel).

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
trunking and Ultravox's SIP docs; verified August 2026, DIDWW outbound
trunk rules October 2026.
