---
name: didww-to-vogent
description: >
  Connect a DIDWW phone number to a Vogent voice agent over SIP import.
  Use whenever the user wants a Vogent agent on a real phone number via
  DIDWW, mentions pairing DIDWW with Vogent, sip_import numbers,
  sip.vogent.ai, warm transfers from a Vogent agent to a live person, or
  debugging calls between the two.
---

# DIDWW to Vogent

A clean self-serve pairing that follows DIDWW's Vogent integration guide
(`doc.didww.com/integrations/vogent/`; section numbers below are the
guide's). Vogent has no official MCP; its REST API (Bearer key) imports
the number and links the agent with `scripts/connect.py` and creates
transfer functions, while the DIDWW MCP (OAuth) automates the number and
the inbound trunk. The DIDWW outbound trunk is the manual step: the MCP
has no outbound trunk tools, so the user creates it in the DIDWW panel,
and Vogent cannot import the number without its credentials.

Live-agent transfers with DIDWW work ONLY as **Warm Transfer**: Vogent
dials the destination itself through the DIDWW outbound trunk. Cold
Transfer (SIP REFER) never reaches DIDWW. Verified on real calls,
October 2026.

## The flow

1. **Confirm in one message:** number (or country to buy), which agent,
   transfer target if any.
2. **DIDWW inbound trunk (MCP; guide 1, Route Incoming Calls to
   Vogent):** host `sip.vogent.ai`, port 5060, `transport_protocol` UDP
   (the default), `username` (User Part of R-URI) the default `{DID}`:
   Vogent accepts the called number with or without the `+`, so `+{DID}`
   also works. `capacity_limit` = expected concurrent calls. Attach the
   DID.
3. **DIDWW outbound trunk (panel, the user does it; guide 2, Enable
   Outbound Calling from Vogent through DIDWW), REQUIRED even for an
   inbound-only line:** Vogent imports a number over SIP only with an
   outbound trunk's termination address and credentials. Under Voice,
   Outbound Trunks a Get Access button means the account is not approved
   yet (business account with company name and VAT/TAX ID; DIDWW answers
   within 48 business hours): say so and finish the DIDWW inbound trunk
   meanwhile. Create New, Friendly name (e.g. `Vogent`), Authentication
   method Credentials & IP-based. Allowed SIP IP addresses: the outbound
   SIP source ranges Vogent provides for an enterprise account, together
   with DIDWW's seven inbound signaling IPs (the guide's list:
   `46.19.209.14`, `46.19.210.14`, `46.19.212.14`, `46.19.213.14`,
   `46.19.214.14`, `46.19.215.14`, `185.238.173.14` and
   `184.195.128.0/21`). Vogent publishes no static range
   outside its enterprise plan: without one, send the user to DIDWW
   support (support@didww.com) to confirm a supported authentication
   setup. `0.0.0.0/0` is for temporary testing only, at the user's own
   risk: DIDWW does not recommend it, the digest credentials are then the
   only protection, so the spend limits below matter (the October 2026
   warm transfer tests ran this way). Never `0.0.0.0/32`: it matches
   nothing and silently blocks every call. Termination: 24 Hour Limit
   (USD) at its minimum, 50 (default 3000), Capacity limit = expected
   concurrency, usage limit notification on; Destination dialing Reject
   All except the countries the agent calls or transfers to. CLI: the
   verified setup used On CLI mismatch "Send Original CLI" with Allow any
   DID(s); a stricter CLI rule is untested with transfers. Enable the
   trunk if it shows Disabled. Host: the region-nearest of
   `nyc.us.out.didww.com`, `lac.us.out.didww.com`,
   `mia.us.out.didww.com`, `fra.eu.out.didww.com`,
   `ams.eu.out.didww.com`, `sg.out.didww.com`, `hk.out.didww.com`. The
   user copies the credentials (key icon in the Credentials column) into
   a file or environment variables, not into chat; read them inside
   scripts and never print them.
4. **Add the outbound credentials to the inbound trunk (panel; guide 2,
   Step 4):** Inbound Trunks, the Vogent trunk, Edit, Authorization,
   Enable Authorization, Auth User and Auth Password = the outbound
   trunk's username and password. Never an invented pair. The user
   pastes them so the password stays out of the chat; the MCP
   (`auth_enabled`, `auth_user`, `auth_password`) only if the user
   accepts it passing through the chat.
5. **Import the number (`scripts/connect.py`; guide 3, Step 1):** one
   call to `POST /api/phone_numbers` with `type: "sip_import"` carrying
   the E.164 number with `+`, `terminationUri` = a DIDWW outbound
   signaling endpoint near where calls are placed, as a hostname only
   (no `sip:` prefix, no port), and the outbound trunk credentials.
   Dashboard alternative: Settings, Call Settings, Numbers, Add Phone
   Number, Import via SIP (country code plus the national part, not the
   country code twice).
6. **Link the number to the agent (guide 3, Step 2):** `PUT
   /api/phone_numbers/{id}` with `{"agentId": "<agent id>"}` (the ID
   under the agent's name; `GET /api/agents` lists them).
   `connect.py --agent <id>` does it right after the import;
   `connect.py --phone-id <id> --agent <id>` links a number imported
   earlier. Dashboard: Agents, the agent, Numbers, Link Number.
7. **Opening line (guide 3, Step 3):** without one the agent waits for
   the caller to speak first, which callers hear as silence. Standard
   agents: Config tab, Opening Line, Inbound calls Only, with a greeting
   (API: `openingLine` on the agent). Flow agents keep the greeting in
   the flow (API: the versioned prompt's `flowDefinition.openingLineType`
   `INBOUND_ONLY` via `PUT /api/agents/{id}/versioned_prompts/{vpId}`,
   sending the whole flowDefinition back with only that field changed;
   back up the prompt first).
8. **Call transfers, if a target was given:** "Live-agent transfers"
   below (guide 3, Step 4).
9. **Test (guide 3, Step 5):** inbound: the agent answers with its
   opening line and Dial History shows the call as Incoming. Outbound:
   the agent's Make Call, Phone Call, From Number = the DIDWW number, or
   `POST /api/dials` with `callAgentId`, `fromNumberId` (the imported
   number's id) and `toNumber` in E.164; check the caller ID. Transfer:
   the destination rings and hears the briefing, then both sides hear
   each other; Dial History shows Transferred and `transfer_call` in the
   Transcript tab (the status alone does not prove the recipient
   answered); DIDWW's Outbound Call Logs show the leg on the Vogent
   outbound trunk.

## Live-agent transfers

Vogent offers Cold and Warm Transfer. With DIDWW only Warm works.

- **Cold Transfer does NOT work with DIDWW.** Vogent hands the call off
  with a SIP REFER whose target it builds from the phone number alone
  (no SIP URI setting, unlike ElevenLabs), marks the dial
  `TRANSFERRED`, and DIDWW never places the call: no outbound CDR, the
  caller waits in silence. Verified twice, also with `0.0.0.0/0` open.
- **Warm Transfer works.** Vogent dials the destination itself through
  the number's `terminationUri` (the DIDWW outbound trunk) with the
  imported credentials, from its own servers, briefs the person who
  answers, then connects the caller. So the outbound trunk's Allowed SIP
  IPs must accept Vogent's servers (step 3). A warm transfer is an
  additional outbound call through DIDWW and both legs stay up, so
  Vogent's per-minute rate and the DIDWW outbound call both run for the
  whole transferred conversation.

Setup (guide 3, Step 4: Add Call Transfers to Your Live Agent):
1. **Create the Call Transfer function:** `POST /api/functions` with
   `{"type": "transfer", "name": "transfer_call", "description": "...",
   "allowedNumbers": [{"number": "+E164"}], "lifecycleMessages":
   {"started": ["Sure, let me connect you to a colleague, one moment
   please."]}}`. Dashboard: Functions, New Function, Display Name, Name,
   Description, Function Type Call Transfer. Allowed Numbers holds the
   destination with Allow transfer to any number off. Never a DIDWW
   number linked to the agent: the transferred call comes straight back
   to the agent.
2. **Set Transfer Type to Warm Transfer in the Vogent dashboard**
   (Functions, the function, Config tab): the API does not expose the
   transfer type and new functions default to Cold. Warm Transfer Type
   Prompted needs a Prompt, for example: "You are briefing a human
   colleague who has just answered the phone. In one short sentence,
   say that a caller needs help and summarise what they asked for, then
   say you are connecting them now." Switching to Cold and back clears
   the Prompt; re-enter it before saving.
3. **Add the function to the agent:** `PUT /api/agents/{id}` with
   `linkedFunctionDefinitionInputs: [{"functionDefinitionId": "<id>"}]`
   (send every function the agent should keep). Dashboard: the agent's
   Config tab, Functions.
4. **Tell the agent when to transfer:** Standard agents: Model tab,
   Prompt, a line naming `transfer_call` and the destination, then
   Update. Flow agents: a function call node in the flow.

## Failure map

- Call connects but nobody speaks: no opening line (step 7).
- Agent not answering at all: the number is not linked to the agent
  (step 6), the inbound trunk's User Part of R-URI is not `{DID}` or
  `+{DID}`, the number is not imported in E.164 with the `+`, or the
  inbound trunk is not assigned to the DID.
- Number import fails: `terminationUri` is not a bare DIDWW outbound
  host (no `sip:`, no port), or the username and password are not the
  outbound trunk's.
- Dial History says Transferred but the destination does not ring:
  Transfer Type is not Warm (a REFER-based cold transfer leaves no
  outbound CDR at DIDWW), the outbound trunk's Allowed SIP IPs do not
  accept Vogent's servers (or hold `0.0.0.0/32`), or the destination is
  not in the function's Allowed Numbers.
- 401, 403 or 407 on an outbound call or transfer: the imported number's
  credentials differ from the outbound trunk's, the inbound trunk's
  Authorization is off or carries another pair (step 4), or the Allowed
  SIP IPs do not accept Vogent's servers.
- 484 Address Incomplete on an outbound call: dial the full E.164
  number (`+...`), without `0`, `00` or `011` prefixes.
- Outbound call or transfer rejected after authentication: caller ID not
  allowed in CLI Settings, destination not allowed, the 24 Hour Limit or
  Capacity limit reached (the 24-hour limit disables the trunk;
  re-enable it in the panel), or the DIDWW balance is too low.
- Caller shown in Vogent with an extra `+1` (a call from `+442079460000`
  appears as `+1 442079460000`): DIDWW sends the caller ID without `+`
  and Vogent assumes a US number. Calls connect normally; only the
  number shown in Vogent is affected. Possible fix, untested:
  `cli_prefix` `+` on the DIDWW inbound trunk.
- API returns "unauthorized": the saved value is the key's ID (a UUID),
  not the secret; create a new key and copy the secret.

## Panel map and money

Vogent keys: `app.vogent.ai`, API, Keys, New Key; copy the secret key
when shown. Dial History shows each call's transcript, function calls
and completion reason; `GET /api/dials/{id}` returns the same, but the
API cannot list dials, so take the id from the dashboard URL. Pricing
has NO public page; marketing says around 0.09 USD/min, so verify the
real rate inside the panel before the user scales. DIDWW side: prepaid;
top-up, Auto-charge and Low Balance Notification (OFF by default) in
Billing, Payment Methods.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-vogent) SIP
trunking and Vogent's number API; verified August 2026, DIDWW outbound
trunk rules October 2026; inbound, agent linking, opening line and warm
transfer re-verified on real calls October 2026, and aligned with
DIDWW's Vogent integration guide November 2026.
