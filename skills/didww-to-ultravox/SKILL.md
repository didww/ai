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
is ADDRESS-BASED. Calls arrive at `{user}@{account_sip_domain}` and the
account's SIP settings decide what is accepted and which agent answers,
by a regex on the user part (by default `agent_{agent_id}`; with DIDWW,
the DID). That inverts the usual setup: instead of importing the number
into the platform, you point the DIDWW trunk at the account's SIP domain.
The DIDWW MCP (OAuth) automates
the number and the inbound trunk (it has no outbound trunk tools: the
user creates the DIDWW outbound trunk in the panel); `scripts/connect.py` automates the Ultravox side via
its REST API (`X-API-Key` header).

DIDWW's [Ultravox guide](https://doc.didww.com/integrations/ultravox/index.html)
is the reference for every panel step (inbound trunk, outbound trunk,
Ultravox settings, transfers, outbound calls, troubleshooting); this
skill follows it.

## The two routing shapes: pick one in intake

**Number patterns (simple, DIDWW's guide):** the DIDWW inbound trunk
sends the DID as the user part (`{DID}`, the default, without `+`) to
the account SIP domain, and an `allowedAgents` entry with a
`toUserPattern` such as `^\+?33144556677$` sends it to the agent. Up to
20 entries; one pattern can list several numbers,
`^\+?(33144556677|33144556678)$`.

**Fallback webhook (flexible: more than 20 agents, or routing decided
at call time):** calls that match no allowed agent hit the account's
`fallbackHandler` webhook, which receives `toUri` (the DID) and answers
`startAgentCall` with the chosen agent, or `reject`. A tiny public HTTPS
endpoint maps DID to agent.

## The flow

1. **Confirm in one message:** number (or country to buy), agent, one
   agent per number or a DID-to-agent map, transfer target, and whether
   the agent places outgoing calls.
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
   `^agent_<agent_id>$`, so a DIDWW trunk sending `{DID}` needs a pattern
   such as `^\+?33144556677$`) or the `fallbackHandler` URL (https;
   Ultravox generates its signing secret, which the handler must verify;
   `--show --show-secrets` reveals it, normal output redacts it).
   Outgoing calls are placed one per request with
   `POST /api/agents/{agent_id}/calls` and `medium.sip.outgoing`
   `{to, from, username, password}`: `to` must be a SIP URI at the
   DIDWW outbound host (`sip:+{number}@fra.eu.out.didww.com`; a plain
   number is rejected with 400), `from` the DID, and the outbound
   trunk's credentials. Never retry a create automatically: each request
   dials again.
4. **DIDWW inbound trunk (MCP):** host = the account SIP domain, port
   5060, UDP, User Part of R-URI `{DID}`, IPv4 only; codecs PCMU, PCMA
   and telephone-event only (Ultravox takes G.722, Opus, PCMU, PCMA and
   iLBC; DIDWW's default list also has G.729 and G.723); SRTP Disabled;
   `max_transfers` 1 when the agent transfers (the default 0 rejects
   REFER); `capacity_limit` = expected concurrent calls; DID attached.
   For transfers the user also turns on the inbound trunk's
   Authorization in the panel with the outbound trunk's Username and
   Password: DIDWW places the transferred call through the outbound
   trunk with them, and without them the transfer fails with
   `10020 error - Unauthorized`.
   **DIDWW outbound trunk (panel, the user does it, for outgoing calls
   and transfers):** Under Voice, Outbound Trunks a Get Access button means the account is
   not approved yet (business account with company name and VAT/TAX ID;
   DIDWW answers within 48 business hours): say so and finish the
   inbound side meanwhile. Create New,
   Authentication method Credentials & IP-Based (keep the credentials:
   the Voximplant addresses below are shared by many customers).
   Allowed SIP IPs: for transfers, DIDWW's seven inbound signaling IPs
   `46.19.209.14`, `46.19.210.14`, `46.19.212.14`, `46.19.213.14`,
   `46.19.214.14`, `46.19.215.14`, `185.238.173.14`; for outgoing calls
   also Voximplant's published US and EU SIP servers (Ultravox's SIP
   runs on Voximplant) `69.167.178.6`, `69.167.178.14`, `3.147.160.14`,
   `78.13.219.90`, `3.123.246.217`, `143.244.45.166`. Check the current
   list at `https://api.voximplant.com/getMediaResources?with_sbcs`;
   other regions may need other addresses, so confirm with Ultravox.
   Never invent a range or suggest `0.0.0.0/0`.
   Media encryption mode: Disabled (the default). Ultravox offers
   unencrypted media only, so with SRTP SDES its outgoing calls fail
   with 500 No suitable media before ringing.
   Termination: 24 Hour Limit (USD) at its minimum, 50 (default 3000),
   Capacity limit = expected concurrency, usage limit notification on;
   CLI limited to the DID; Destination dialing Reject All except the
   countries the agent calls. Enable the trunk if it shows Disabled.
   Host: the region-nearest of `nyc.us.out.didww.com`,
   `lac.us.out.didww.com`, `mia.us.out.didww.com`,
   `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com`,
   `hk.out.didww.com`. The user hands the generated credentials over in
   a file or environment variables, not pasted into chat. These credentials go into `medium.sip.outgoing`
   and onto the inbound trunk's Authorization.
5. **Transfers (optional):** add the built-in `coldTransfer` tool to the
   agent with `parameterOverrides` `target`
   `sip:+{number}@{DIDWW outbound host}` (never `tel:`; DIDWW answers
   603) and `sipVerb` `REFER`, plus a prompt rule to transfer only when
   the caller asks for a person. Ultravox sends REFER to DIDWW, which
   dials the target through the outbound trunk.
6. **Verify:** inbound from a mobile; outbound via one
   `POST /api/agents/{agent_id}/calls`; a transfer (the tool result
   reads Transfer succeeded). After a call,
   `GET /api/calls/{call_id}/sip_logs` returns a link to its SIP log,
   with the source address and DIDWW's responses. SIP minutes bill
   separately from model time; mention it.

## Failure map

- Inbound 603 rejects: the To address matches no allowed agent and no
  fallback handler is set; fix `allowedAgents` regex or add the handler.
- Inbound never arrives: CIDR allowlist missing DIDWW's signaling range,
  or no `toUserPattern` matches the DID the trunk sends.
- Call drops at once or has no audio: a codec Ultravox does not take;
  keep PCMU, PCMA and telephone-event on the inbound trunk.
- Transfer fails with `10020 error - Unauthorized`: the inbound trunk's
  Authorization is off or not set to the outbound trunk's credentials.
- Transfer rejected: `max_transfers` 0, a `tel:` target (603), DIDWW's
  seven IPs missing on the outbound trunk, or SRTP on it (500 No
  suitable media).
- Outgoing call ends at once as `unjoined`, SIP log shows 500 No
  suitable media: SRTP SDES on the outbound trunk; set Disabled.
- Outgoing call create returns 400: `to` is not a SIP URI.
- Outbound auth failures: credentials in `medium.sip.outgoing` do not
  match the DIDWW outbound trunk.
- Outbound 403 or rejected from DIDWW: source not in the outbound
  trunk's Allowed SIP IPs (the call's SIP log shows which Voximplant
  address sent it), caller ID not allowed in its CLI settings,
  destination not allowed, or the 24 Hour Limit was reached (DIDWW then
  disables the trunk; re-enable it in the panel).

## Panel map and money

Ultravox keys: `app.ultravox.ai`, Settings, API Keys, Generate New Key.
Pricing runs two meters per call: 0.05 USD/min agent time plus SIP
minutes billed separately (about 0.005 USD/min); quote both. 30 free
minutes to start; pay-as-you-go has concurrency caps that only the
100 USD/month Pro plan removes. DIDWW side: prepaid; top-up, Auto-charge
and Low Balance Notification (OFF by default) in Billing, Payment
Methods. Each transfer is a new DIDWW outbound call, billed at the
destination's outbound rate on top of the inbound call.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-ultravox) SIP
trunking, DIDWW's Ultravox guide and Ultravox's SIP docs; verified
August 2026, DIDWW outbound trunk rules October 2026; incoming calls, a
REFER transfer and an outgoing call verified on real calls through
DIDWW in November 2026.
