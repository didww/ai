---
name: didww-to-retell
description: >
  Connect a DIDWW phone number to a Retell AI agent over custom telephony,
  with full MCP automation: Retell's official MCP can create agents AND
  import numbers. Use whenever the user wants a Retell agent on a real
  phone number via DIDWW, mentions pairing DIDWW with Retell, custom
  telephony, sip.retellai.com, import-phone-number, or debugging calls
  between the two.
---

# DIDWW to Retell

The most automatable pairing in the family: Retell's official MCP
(`https://mcp.retellai.com`, Bearer API key) covers agent creation,
configuration AND phone number import, and the DIDWW MCP (OAuth) covers
the number and the inbound trunk. When both are connected, everything
except the DIDWW outbound trunk is tool calls: the DIDWW MCP has no
outbound trunk tools, so the user creates that one in the DIDWW panel. `scripts/connect.py` exists
only for sessions without the Retell MCP.

## Auth and automation map

| Side | Best path | Auth |
|---|---|---|
| DIDWW (DID, inbound trunk) | DIDWW MCP `https://api.didww.com/mcp` | OAuth, no keys |
| DIDWW outbound trunk, 24-hour spend limit | The user, in the DIDWW panel | Panel login |
| Retell (agent, number import, binding) | Retell MCP `https://mcp.retellai.com` | Bearer API key, entered once at MCP setup |
| No Retell MCP available | `scripts/connect.py` | `RETELL_API_KEY` env var |

## The flow

1. **Confirm in one message:** number (or country to buy), agent
   (existing or create from a described purpose), transfer target,
   country allowlists for calls if the user wants them.
2. **DIDWW inbound trunk (MCP):** host `sip.retellai.com`, transport
   TCP (Retell's recommendation; UDP packets can get dropped), digest
   auth preferred (Retell has no single stable inbound IP),
   `capacity_limit` = expected concurrent calls. Attach the DID.
   **DIDWW outbound trunk (panel, the user does it):** under Voice,
   Outbound Trunks a Get Access button means the account is not
   approved yet (business account with company name and VAT/TAX ID;
   DIDWW answers within 48 business hours): say so and finish the
   inbound side meanwhile. Create New, Authentication method
   Credentials & IP-Based; its required Allowed SIP IPs are Retell's
   egress ranges `18.98.16.120/30`, `3.42.144.0/23`, `153.57.128.0/18`
   (plus `143.223.88.0/21`, `161.115.160.0/19` for some US traffic).
   Termination: 24 Hour Limit (USD) at its minimum, 50 (default 3000),
   Capacity limit = expected concurrency, usage limit notification on;
   CLI limited to the DID; Destination dialing Reject All except the
   countries the agent calls. Enable the trunk if it shows Disabled.
   Host: the region-nearest of `nyc.us.out.didww.com`,
   `lac.us.out.didww.com`, `mia.us.out.didww.com`,
   `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com`,
   `hk.out.didww.com`. The user hands the generated credentials over in
   a file or environment variables, not pasted into chat.
3. **Retell side (MCP or script):** one import call does everything:
   `phone_number` (E.164), `termination_uri` (the DIDWW outbound host),
   `sip_trunk_auth_username`/`password`, `transport`, and the agent
   binding inline via `inbound_agents` / `outbound_agents`. There is no
   separate trunk object to manage.
4. **Verify:** inbound from a mobile, outbound caller ID, transfer.
   Retell's MCP reads call logs for verification without leaving the
   conversation.

## Failure map

- Inbound silent or rejected: digest mismatch, or the DIDWW trunk uses
  UDP where TCP was expected; set `;transport=tcp`.
- Later changes to the trunk (new carrier host, new credentials): Retell
  requires DELETE and RE-IMPORT of the number, not an edit; re-bind the
  agent in the same call.
- Outbound 403 or rejected from DIDWW: source not in the outbound
  trunk's Allowed SIP IPs, caller ID not allowed in its CLI settings,
  destination not allowed, or the 24 Hour Limit was reached (DIDWW then
  disables the trunk; re-enable it in the panel).
- Country restrictions blocking test calls: check
  `allowed_inbound_country_list` / `allowed_outbound_country_list` set at
  import.

## Panel map and money

Retell keys: dashboard, API Keys tab (the same key powers their MCP).
Billing tab: prepaid credits with optional auto-recharge; 10 USD free
trial credits. Real cost roughly 0.07 to 0.31 USD/min, and using the
DIDWW trunk zeroes Retell's 0.015 USD/min telephony line: say this, it
is a genuine saving. Warn that subscription items (numbers, knowledge
bases, concurrency) bill the card separately at cycle end and that
calls hard-block at zero credits. DIDWW side: prepaid; top-up,
Auto-charge and Low Balance Notification (OFF by default) in Billing,
Payment Methods.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-retell) SIP
trunking and Retell's custom telephony docs; verified August 2026, DIDWW
outbound trunk rules October 2026.
