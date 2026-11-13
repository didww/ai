---
name: didww-to-xai
description: >
  Connect a DIDWW phone number to an xAI Grok Voice agent over SIP (xAI's
  docs and console now say SpaceXSI). Use whenever the user wants Grok
  answering a real phone number via DIDWW, mentions sip.voice.x.ai, xAI
  or Grok voice agents, the Voice Agent Builder, console.x.ai, a Direct
  SIP number, agent_id, realtime.call.incoming webhooks, or debugging
  calls between DIDWW and Grok. Covers incoming calls and transfers to a
  live person; xAI places no outbound calls.
---

# DIDWW to xAI (Grok Voice)

DIDWW's [xAI integration guide](https://doc.didww.com/integrations/xai/index.html)
is the reference for every panel and console step; this skill follows it
and adds what live calls showed (section 8).

xAI answers calls to numbers added to it as **Direct SIP** numbers.
Incoming calls only: xAI has no API to place calls and publishes no SIP
source addresses, so outbound calls from Grok through DIDWW are not
possible; say so in intake. Transfers to a live person work by SIP REFER:
DIDWW places the new call through a DIDWW outbound trunk.

## 1. Choose the setup first

Confirm in one message: number (or country to buy), what the agent
should do, transfer target if any, and which agent answers:

- **A. Console voice agent (default, DIDWW's guide).** Built in the xAI
  console under Voice Agents; no server. The number is added to the
  agent. Section 5A.
- **B. Your own backend.** The number points at your webhook; per call
  your code joins the call over a websocket and sends the session
  config. Only when the user needs per-call logic the console cannot do,
  and can run public HTTPS. Section 5B.

Both use the same DIDWW trunks (sections 3 and 4).

## 2. Credentials never go through the chat

Create mode-600 files and open them for the user to fill in:
`~/.xai.env` (`XAI_API_KEY=`) and, for transfers,
`~/.didww-xai-outbound-trunk.env` (`DIDWW_SIP_USERNAME=`,
`DIDWW_SIP_PASSWORD=`). Check that values are present without printing
them; `scripts/register_number.py --env-file` reads them. Passwords the
DIDWW panel or the xAI console needs are typed there by the user.

Say up front: API keys must be of type **Grok API** (the dialog also
offers **Cursor**, the wrong one), and xAI creates no Grok API key until
a payment method is on file. Credits are prepaid and non-refundable;
calls are rejected at zero balance. No free credits.

## 3. DIDWW inbound trunk (MCP)

`create_sip_trunk`: host `sip.voice.x.ai`, port `5061`, transport `TLS`,
username `+{DID}` (xAI matches the number in E.164 with the `+`),
`network_protocol_priority` `force IPv4` (the default), codecs `PCMU`,
`PCMA`, `telephone-event` (xAI takes G.711 and G.722; DIDWW's default
list has G.729 and G.723), `media_encryption_mode` `Disable` (TLS
signaling with plain RTP works), `max_transfers` 1 when the agent
transfers (the default 0 rejects REFER), `capacity_limit` = expected
concurrency. Assign the DID; if it is routed elsewhere, say what stops
and confirm first.

Authorization (the user sets it in the panel: Inbound Trunks, Edit,
Authorization, so the password stays out of the chat): for transfers,
the outbound trunk's Username and Password (DIDWW authenticates the
transferred call with them, whatever xAI's own auth is). For digest
toward xAI, the same pair goes on the xAI number. Verify with
`get_trunk`: `auth_enabled` true and `auth_user` equal to the file's
username.

## 4. DIDWW outbound trunk (panel, the user; transfers only)

Under Voice, Outbound Trunks a **Get Access** button means the account
is not approved yet (business account, company name and VAT/TAX ID;
DIDWW answers within 48 business hours): finish the inbound side
meanwhile. Create New: **Credentials & IP-based**; Allowed SIP IPs
DIDWW's seven inbound signaling IPs `46.19.209.14`, `46.19.210.14`,
`46.19.212.14`, `46.19.213.14`, `46.19.214.14`, `46.19.215.14`,
`185.238.173.14` (xAI sends nothing to this trunk, so no xAI addresses);
Media encryption mode **Disabled**, matching the inbound trunk.
Termination: 24 Hour Limit (USD) at its minimum, 50 (default 3000),
capacity, and only the destinations transfers go to (a transfer to a
destination the trunk does not allow is declined). CLI: the original
caller's number must be allowed, because transfers keep it. Credentials
go into the file from section 2.

## 5A. Console voice agent

1. **Agent:** console.x.ai, Voice Agents, Create agent (a template or
   Start from scratch). Configuration tab: Instructions; **Welcome
   message** on with a Greeting (off means the agent waits for the
   caller to speak); Publish. Try it live tests the agent in a browser,
   not transfers.
2. **Number:** the agent's Deployment tab, Phone numbers, Add number,
   **Direct SIP**: Name; Phone number in E.164 with `+`; SIP URI shows
   `sip:{number}@sip.voice.x.ai;transport=tls`. Authentication: either
   Allowed addresses with DIDWW's seven signaling IPs, or (preferred,
   since those IPs serve every DIDWW customer) Allowed addresses empty
   and Authentication Username and Password = the inbound trunk's Auth
   User and Auth Password. The guide calls both optional; never leave
   both empty (anyone could ring the number on the user's credits).
   Same step by API, digest read from the files:

   ```
   python3 scripts/register_number.py --number +15105550100 \
     --agent agent_XXXX --digest \
     --env-file ~/.xai.env --env-file ~/.didww-xai-outbound-trunk.env
   ```

   201 with `phone_number_id` and `sip_host`. The agent ID is in the
   console address bar (`/voice/agents/agent_...`) or the Deployment
   tab's Code integration (`?agent_id=agent_...`); there is no agents
   API to look it up (`GET /v1/agents` answered 403 "agents endpoint is
   not enabled for this team"). `--list` shows registered numbers,
   `--delete ID` removes one (confirm first; the number stays on DIDWW).
3. **Transfers:** Configuration, Tools, Add tool, **Transfer call** (or
   edit an existing `transfer_call`): Tool name `transfer_call`;
   Description = exactly when to transfer; Destinations **Custom**, a
   Label, Destination `sip:+{number}@{DIDWW outbound host}` (e.g.
   `fra.eu.out.didww.com`), never `tel:` and never a DID on the xAI
   inbound trunk (the call loops back to the agent). Publish. Put the
   same rule in Instructions ("transfer only after the caller asks for a
   person").

## 5B. Your own backend

`register_number.py --number ... --webhook https://... --digest
--env-file ...` saves the one-time webhook signing secret to a mode-600
file. On `realtime.call.incoming`, verify `webhook-id`,
`webhook-timestamp` and `webhook-signature`, open
`wss://api.x.ai/v1/realtime?call_id={call_id}` with the API key, send
`session.update` (voice, instructions, turn_detection), then
`response.create` so the agent speaks first. Transfer:
`POST /v1/realtime/calls/{call_id}/refer` with
`{"target_uri": "sip:+{number}@{DIDWW outbound host}"}` (xAI also takes
`tel:`, DIDWW does not); it blocks until the destination answers: 200
`{}` answered, 502 with the carrier's SIP status, 504 timeout; after a
502 the session stays usable. `/hangup` ends the call; keypresses arrive
as `input_audio_buffer.dtmf_event_received`. The OpenAI skill's
`webhook_server.py` is the closest template. This path was not
exercised in the DIDWW live calls.

## 6. Verify

Incoming call from a mobile: the greeting plays; the agent's
Conversations tab lists the call with Caller and Destination. Transfer:
a normal chat does not transfer; asking for a person does; the
destination answers; Conversations shows the `transfer_call` tool call.
The transfer leg is in DIDWW's Outbound Call Logs.

## 7. Failure map

- Call never reaches the agent: host, port 5061 or TLS wrong; R-URI not
  `+{DID}` or the number in xAI differs; digest pair differs between the
  inbound trunk and the xAI number; number not added; xAI credits at
  zero.
- Silence when the call connects: Welcome message off.
- No audio: codecs other than G.711, or SRTP on the inbound trunk.
- Transfer result `{"status": "failed", "reason": "the call was
  declined"}` (no SIP code is shown): destination not allowed on the
  outbound trunk, `max_transfers` 0, inbound Authorization not the
  outbound pair, `tel:` target, DIDWW's IPs missing, original CLI not
  allowed, 24 Hour Limit or balance.
- Transfer reaches voicemail: it worked; the destination did not answer.
- Transfer returns to the agent: the destination is the DID itself.
- Transfers the caller did not ask for: tighten Description and
  Instructions together.
- No API key can be created: payment method missing, or Cursor type.
- 5B only: webhook fires, then silence: websocket or `session.update`
  failed; lost signing secret: delete and add the number again; 422:
  field names drifted, the error lists the accepted ones.
- Lost SIP password: xAI never returns it; delete the number, add it
  with a new pair, and update the inbound trunk together.

## 8. Live test results (November 2026)

Every rule above comes from DIDWW's guide and these real calls.

- Setup: new DIDWW inbound trunk as in section 3 (capacity 2), new
  outbound trunk as in section 4 (UK destinations only), a new xAI
  account with 5 USD of credits, a console agent from the Customer
  Support template.
- The number was added with `POST /v2/phone-numbers` (`agent_id`,
  digest = the outbound trunk's pair): 201; `sip_host`
  `sip.voice.x.ai`, and an `inbound_trunk_id` starting `ST_`. The
  console then listed it as Direct SIP.
- Incoming call answered with the greeting over TLS with plain RTP and
  G.711, with the digest pair on the xAI number and the same pair in the
  inbound trunk's Authorization.
- First transfer: declined about 0.2 s after the tool call. The
  destination was the test DID itself (a US number), and the trunk
  allowed only UK destinations.
- With `sip:+44...@fra.eu.out.didww.com` the transfer completed: once
  into the destination's voicemail (it forwards to a mobile that did not
  answer), then answered. After a completed transfer the console shows
  the tool as running with no result: the agent's session ends.
- Save changes on the Transfer call tool applied to the next call with
  Publish still disabled; DIDWW's guide says Publish, which is harmless.
- Creating a key showed "Add a payment method to create Grok API keys";
  `GET /v1/agents` 403 and `/v2/agents` 404 for a new team.

Not tested: section 5B, Allowed addresses instead of digest, G.722,
TCP, a zero credit balance.

## 9. Panel map and money

xAI: `console.x.ai`; API Keys (type Grok API); Billing, API spend
management (prepaid credits, auto top-up with a threshold, an amount of
at least 5 USD and a monthly cap; invoiced billing off by default);
Voice Agents, with the agent tabs Configuration, Speech, Deployment,
Conversations and Insights. Voice costs 0.08 USD/min (grok-voice-3.0).
DIDWW side: prepaid; top-up, Auto-charge and Low Balance Notification
(OFF by default) in Billing, Payment Methods. Each transfer is a new
DIDWW outbound call billed at the destination's rate on top of the
inbound call.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-xai) SIP
trunking, DIDWW's xAI guide and xAI's SIP docs; verified August 2026,
console agents, incoming calls and transfers verified with live calls
through DIDWW in November 2026.
