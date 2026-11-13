---
name: didww-to-openai-realtime
description: >
  Connect DIDWW phone numbers directly to OpenAI over SIP, in two separate
  setups the user chooses between: incoming calls answered by gpt-realtime
  (Realtime API, webhook backend, optional transfer to a live person), and
  outbound calls placed by GPT-Live (Live API) through a DIDWW outbound
  trunk with its username and password. Use whenever the user wants an
  OpenAI voice agent on a DIDWW number, mentions sip.api.openai.com,
  realtime.call.incoming webhooks, Realtime SIP, GPT-Live, gpt-live-1,
  /v1/live/sessions, outbound AI calls from OpenAI, or debugging calls
  between DIDWW and OpenAI. Developer-grade: the agent is code the user
  runs.
---

# DIDWW to OpenAI (Realtime incoming, GPT-Live outbound)

The most direct wiring in the family: DIDWW talks straight to OpenAI, no
platform in between. OpenAI stores no agent: the user's own code defines
it on every call, and DIDWW only carries the call. This skill follows
DIDWW's production guide,
https://doc.didww.com/integrations/openai/index.html, and ships two
scripts: `scripts/webhook_server.py` (incoming calls and transfers) and
`scripts/gptlive_call.py` (outbound calls). Not a no-code path; say so in
intake and offer the hosted platforms (didww-connect) if the user cannot
run code.

## 1. Choose the setup first

Incoming and outbound use different OpenAI APIs (Realtime vs Live), with
different event names, endpoints and DIDWW trunks. Before anything else,
ask which one the user wants (one question, these options):

| Option | Call direction | DIDWW side | OpenAI side | User runs |
|---|---|---|---|---|
| **A. Incoming calls** | callers dial a DID, gpt-realtime answers | inbound SIP trunk to OpenAI | API key, webhook `realtime.call.incoming` | `webhook_server.py` on a **public HTTPS** URL |
| **A+T. Incoming + transfer to a person** | as A, then the agent hands the caller to a live number | as A, plus an outbound trunk whose credentials go on the inbound trunk | as A, plus a transfer tool | same server with `transfer_to` |
| **B. Outbound calls (GPT-Live)** | OpenAI dials a number, the agent talks | outbound trunk with SRTP and OpenAI's IP ranges | API key, outbound SIP enabled for the org | `gptlive_call.py` (no webhook, no public URL) |
| **C. Both** | A or A+T, plus B | one outbound trunk serves transfers and GPT-Live | both | both scripts |

Then confirm the rest in one message, only for the chosen option:

- **A / A+T:** the DID (or the country to buy one in), what the agent
  should do and its greeting, the OpenAI project ID (`proj_...`), where
  the server will run on public HTTPS; for transfers, the number of the
  live person or team (never a DID routed to this same inbound trunk, or
  the call loops back to the agent).
- **B:** the number to call (E.164; for the first test, a phone the user
  can answer), the DIDWW number to show as caller ID, what the agent
  should say and do, and the DIDWW outbound gateway (default
  `fra.eu.out.didww.com`).

Shared prerequisites: OpenAI API billing with a positive prepaid balance
(ChatGPT plans do not include API credit), and an API key in the right
project. A **Restricted** key with only Model capabilities > **Realtime
(/v1/realtime) = Request** was enough for incoming calls, transfers and
GPT-Live outbound in live tests; a Read-only key cannot accept calls.

## 2. Credentials never go through the chat

The OpenAI API key, the webhook signing secret and the DIDWW outbound
trunk password are secrets. Never ask the user to paste them into the
chat, and never print, `cat` or echo a file that holds them. Instead:

1. Create a private template:
   `python3 scripts/gptlive_call.py --init-env ~/.didww-openai.env`
   (mode 600, empty values: `OPENAI_API_KEY`, `DIDWW_SIP_USERNAME`,
   `DIDWW_SIP_PASSWORD`, and `OPENAI_WEBHOOK_SECRET` for option A; leave
   unused lines empty).
2. Open it for the user (macOS: `open -e ~/.didww-openai.env`) and let
   them fill it in and save.
3. Check it without revealing values: `... --check` (option B), or start
   the server, which refuses to run with a missing key or secret.

Both scripts redact the key and the trunk credentials from their logs.
The outbound trunk credentials are entered on the DIDWW inbound trunk by
the user in the panel, not through MCP, so they never pass through you.

## 3. Option A: incoming calls (Realtime API)

1. **DIDWW inbound trunk (MCP `create_sip_trunk`):** `host`
   `sip.api.openai.com` (European data residency:
   `sip-eu.api.openai.com`), `port` 5061, `username` = the OpenAI project
   ID (User Part of R-URI), `transport_protocol` TLS,
   `media_encryption_mode` SRTP SDES, `codecs` [PCMU, PCMA,
   telephone-event], `network_protocol_priority` "force IPv4",
   `capacity_limit` = expected concurrent calls; with transfers also
   `max_transfers` 1. Keep the default Diversion inject mode ("Add
   Diversion as +DID number"): the `To` header carries the project ID, so
   the called DID reaches OpenAI only in `Diversion`. Then
   `assign_did_to_trunk`. The project ID in the trunk and the webhook
   must belong to the SAME OpenAI project, or calls fail with 400 after
   about 15 s. No digest auth exists on OpenAI's ingress: anyone who
   knows the project ID can send calls to it, so treat the SIP address
   like a credential and keep the server's reject-by-default.
2. **Start the server before the webhook:** fill `AGENTS` in
   `scripts/webhook_server.py` (DID -> instructions, greeting, optional
   `transfer_to`), run it with `--env-file ~/.didww-openai.env` (or set
   `OPENAI_API_KEY` and `OPENAI_WEBHOOK_SECRET` in its environment)
   behind public HTTPS. It refuses to start with a `tel:` or looping
   transfer target. It verifies the
   webhook signature, drops duplicate deliveries, reads the called number
   from `Diversion` (falls back to `To`), accepts known DIDs with the
   model and instructions, rejects everything else with 603, opens the
   call WebSocket and sends the greeting as `response.create` with
   `tool_choice: "none"` (without it the agent waits silently, and a
   greeting turn with tools can start a transfer). `LOG_TRANSCRIPT=1`
   logs what the agent says, for tests.
3. **OpenAI webhook:** Project settings > Webhooks > Create, URL = the
   full HTTPS endpoint including the path (`https://host/webhook`),
   event type `realtime.call.incoming`, copy the signing secret
   (`whsec_...`) into the env file. Creating webhooks needs the
   Webhooks write permission (`api.webhooks.write`); if the page asks for
   it, the org or project owner must grant it or create the webhook.
4. **Hosting:** any always-on host that serves public HTTPS and allows
   long-lived WebSockets. A temporary tunnel (cloudflared quick tunnel,
   ngrok) is fine for a test, but its URL changes on every restart and
   dies when the computer sleeps or loses network; the webhook URL must
   then be updated, which needs the webhook permission again. Keep the
   machine awake during tests and move to a permanent address before
   real calls.
5. **Verify:** call the DID from a mobile; the server logs the webhook
   and `accepted ...`, the agent greets, both sides hear each other.

### Transfers (A+T): hand the caller to a live person

DIDWW supports cold transfers by SIP REFER on inbound calls: the server
calls OpenAI's `refer` endpoint, OpenAI sends REFER to DIDWW, and DIDWW
places a new call through the user's outbound trunk. After a successful
transfer the OpenAI session ends.

1. **Outbound trunk (panel only, the DIDWW MCP has no outbound trunk
   tools):** outbound termination access must be granted first (Voice >
   Outbound Trunks shows Get Access otherwise). Create New, Friendly name
   (e.g. `OpenAI`), keep **Credentials & IP-based**, Allowed SIP IP
   addresses = DIDWW's signaling IPs `46.19.209.14 46.19.210.14
   46.19.212.14 46.19.213.14 46.19.214.14 46.19.215.14 185.238.173.14`,
   Media encryption mode **SRTP SDES** (otherwise 500 No suitable media;
   use a separate trunk if another integration needs unencrypted media),
   a low **24 hour limit (USD)** and only the destinations needed.
2. **Credentials on the inbound trunk:** the user copies the outbound
   trunk Username and Password (key icon in the Credentials column) to the
   OpenAI inbound trunk: Edit > Authorization > Enable Authorization, Auth
   User, Auth Password, Submit. DIDWW authenticates the transferred leg
   with these; missing ones give Transfer Failed: 401/Unauthorized.
3. **Inbound trunk:** Max Transfers 1 or higher, Network Protocol IPv4.
4. **Server:** `transfer_to` = `sip:+NUMBER@fra.eu.out.didww.com` (any
   DIDWW outbound signaling endpoint). `tel:` URIs, as in OpenAI's
   examples, fail with 603 Unconfigured xfer for tel URIs; the server
   refuses to start with one. The transfer tool's description and the
   instructions must say the model may transfer ONLY after the caller
   asks for a person.
5. **Verify:** talk without asking for a person (no transfer), then ask
   for one; the destination rings and shows the original caller's number
   (subject to the outbound trunk's CLI settings). A 200 from `refer`
   only means the REFER was relayed; check the destination and the DIDWW
   Outbound Call Logs.

## 4. Option B: outbound calls (GPT-Live)

No inbound trunk, webhook or public URL is involved: the script creates
the call and OpenAI dials through the DIDWW outbound trunk.

1. **Outbound trunk:** as in Transfers step 1 (SRTP SDES is required),
   and add OpenAI's ranges to **Allowed SIP IP addresses**, keeping the
   DIDWW IPs if transfers are used: `13.79.45.80/28 23.98.140.64/28
   40.67.149.176/28 40.83.204.240/28`. OpenAI publishes them as SRTP media
   ranges (developers.openai.com/api/docs/guides/voice-sip, "SIP signaling
   and media IP ranges"); the tested call came from 40.67.149.189. They
   are shared by all OpenAI customers, so keep Credentials & IP-based
   authentication; do not open the trunk to 0.0.0.0/0. The caller ID
   must be a DIDWW number the trunk's CLI settings allow.
2. **OpenAI:** the organization needs outbound SIP enabled (otherwise
   `403 outbound_sip_not_enabled`: contact OpenAI) and access to
   `gpt-live-1`.
3. **Credentials:** the env file from section 2, with the outbound trunk
   Username and Password as `DIDWW_SIP_USERNAME` / `DIDWW_SIP_PASSWORD`.
   OpenAI's dashboard has no place for them: they travel with every call
   request.
4. **Dry check, then one call:**
   ```
   python3 scripts/gptlive_call.py --env-file ~/.didww-openai.env \
     --to +15105550199 --from +15105550100 \
     --instructions-file agent.txt --check
   python3 scripts/gptlive_call.py --env-file ~/.didww-openai.env \
     --to +15105550199 --from +15105550100 \
     --instructions-file agent.txt --max-seconds 300
   ```
   Each run places exactly ONE call and never retries: a retry dials the
   destination again (OpenAI itself already repeats a failed INVITE).
   Before each run, tell the user which number will ring; one call per
   request. If the create request times out, the call may still have
   been placed: check the DIDWW Outbound Call Logs before trying again.
5. **What the script does:** `POST /v1/live/sessions` (201 with
   `session.id`; the phone may still be ringing), attaches at once to
   `wss://api.openai.com/v1/live/sessions/{id}/attach` (it replays only
   3 s, and the session disappears seconds after a failed call), logs
   `transport.ringing` / `answered` / `failed` (with DIDWW's SIP response),
   prints the transcript, answers delegated tasks (below), and hangs up
   with `POST .../hangup` at `--max-seconds` or Ctrl-C. Exit code 0 means
   the call was answered. OpenAI caps ringing at 3 minutes and a call at
   2 hours.
6. **Verify:** ringing and answered events, both sides hear each other,
   the destination sees the DIDWW caller ID, and the DIDWW Outbound Call
   Logs show the call with Success on the trunk (MCP `create_export`
   `outbound_cdr` filtered by caller ID; share the panel link, and a
   login-free signed link only when the user asks for one).

### Why a GPT-Live agent says "one moment" and goes silent

GPT-Live hands reasoning and tool work to a backend ("delegation"). With
**client delegation** (the script's mode), the server receives
`session.delegation.created`, which holds only a delegation ID, not the
task: the server keeps the conversation from
`session.input_transcript.delta` / `session.output_transcript.delta` and
must return a result with `session.commentary.append` (spoken,
paraphrased) or `session.thinking.append` (silent context), same
`delegation_id`, at most 500 tokens. If nothing comes back, the agent
says it needs a moment and then stays silent: seen in a live sales-style
test. `gptlive_call.py` answers every delegation from
`handle_delegation()`, which by default says that nothing can be checked
or arranged during the call (verified on a live call: the agent went on
with its recommendation instead of stalling); replace it with real
lookups or actions, and
report an action as done only after it really succeeded. **Responses
delegation** (OpenAI runs the backend model) is the alternative; it is
untested here and probably needs Responses write permission on the key.
The restricted key logs `missing_scope ... api.responses.write` at the
start of each call: harmless, it only disables history compaction.

Instructions describe behavior; they do not add capabilities. State the
agent's role and the call direction ("you are calling the person"), the
opening line, what to collect one question at a time, what never to do
(invent prices, ask for card numbers or passwords), and when to end the
call; offer only actions the server implements.

## 5. Failure map

Incoming:
- 400 Bad Request about 15 s after the INVITE, no webhook in the server
  log: the R-URI project ID is not the webhook's project, the event type
  is not selected, or the webhook URL is unreachable (tunnel gone).
- Server rejects every call as an unknown number: it matched `To`, which
  holds the project ID; read `Diversion`.
- Call connects, agent silent: no greeting `response.create`, or the
  accept failed (server log: key permission or project).
- "bad url" when creating the webhook: server not running or not public,
  or the URL lacks the handler path.
- Agent transfers callers who did not ask: greeting without
  `tool_choice: "none"`, or a vague tool description.

Transfers (DIDWW inbound call log shows Transfer Failed: ...):
- 401/Unauthorized: inbound trunk Authorization missing or wrong.
- 500/No suitable media: outbound trunk media is not SRTP SDES.
- 403 Forbidden then a dropped call: DIDWW IPs missing on the outbound
  trunk, or credentials mismatch.
- Rejected outright: Max Transfers is 0, or Network Protocol does not
  match the allowed IP version.
- 603 Unconfigured xfer for tel URIs: use a `sip:` target.
- Rejected after authentication: CLI settings, blocked destination,
  24-hour limit, capacity or balance.

Outbound (GPT-Live):
- `transport.failed` 403 Forbidden and no DIDWW CDR: OpenAI ranges
  missing from Allowed SIP IP addresses.
- 500 No suitable media (often three INVITEs in the logs): SRTP SDES
  missing on the outbound trunk.
- `outbound_sip_not_enabled`: ask OpenAI to enable outbound SIP.
- Attach returns 404 / `session_id_not_found`: the session closed after
  a failure; attach immediately with the unchanged ID.
- Agent says "one moment", then silence: unanswered delegation.
- Agent promises an action that never happens: the instructions ask for
  something the server does not implement.

## 6. Panel map and money

OpenAI keys: `platform.openai.com/api-keys`; webhooks (option A):
`platform.openai.com/settings/project/webhooks`, copy the signing secret
at creation; project ID: Settings > Project > General. Billing: prepaid
credits under Settings, Billing (minimum 5 USD); auto-recharge defaults
to ON during setup and credits EXPIRE after one year, non-refundable: say
both out loud. Realtime bills in audio tokens, not minutes; a typical
phone conversation lands around 0.05 to 0.10 USD/min of model cost
depending on talk ratio. DIDWW side: prepaid; top-up, Auto-charge and Low
Balance Notification (OFF by default) in Billing, Payment Methods.
Outbound calls and every transfer leg are billed per minute at the DIDWW
outbound rate for the destination, on top of the inbound call and the
OpenAI usage: set a low 24-hour limit on the outbound trunk.

## 7. Live test results (November 2026)

Every rule above comes from DIDWW's guide and these real calls; use them
to recognise a symptom quickly.

Incoming and transfers:
- Answered with TLS, SRTP SDES and PCMU/PCMA/telephone-event; the
  greeting started 1.3 s after the accept once the server sent
  `response.create` (before that, the agent waited silently).
- The webhook's `To` was `<sip:proj_...@sip.api.openai.com:5061>`; the
  DID came only in `Diversion: <sip:+DID@sip.didww.com>;reason=unconditional`.
- A project ID in the R-URI that belonged to a different project than
  the webhook: no webhook, and about 15 s later OpenAI answered DIDWW
  with 400 Bad Request. Restricting codecs changed nothing.
- Creating the webhook needed `api.webhooks.write` from the project
  owner; OpenAI rejected the URL as "bad url" until the server answered
  200 on the full `/webhook` path.
- With a loose tool description and no `tool_choice: "none"` greeting,
  the model called `transfer_call` unprompted. Fixed by both.
- Transfer Failed: 401/Unauthorized without the inbound trunk's
  Authorization; 500/No suitable media with a non-SRTP outbound trunk;
  success with SRTP SDES, DIDWW's seven IPs and the outbound pair on
  the inbound trunk: the destination rang showing the original caller's
  number, and the leg appeared in the Outbound Call Logs.
- A temporary quick tunnel died when the computer went to sleep
  (`Unauthorized: Tunnel not found` on reconnect); incoming calls failed
  until a new URL was set on the webhook.

Outbound (GPT-Live):
- Outbound SIP was already enabled for the test organization. The create
  request returned 201 (OpenAI's guide says 200).
- Against an outbound trunk without SRTP: 500 No suitable media, and
  OpenAI sent the INVITE three times on its own.
- With only DIDWW's IPs allowed: `transport.failed` 403 Forbidden within
  0.5 s and no DIDWW CDR. The call came from 40.67.149.189; with
  OpenAI's four /28 ranges added (and no `0.0.0.0/0`) calls connected
  and the CDR showed Success.
- DIDWW accepted GPT-Live's Opus/SRTP offer as is; nothing on the
  outbound trunk's codecs needed changing.
- The sideband replays only 3 s, and after a failed call the session
  was gone within seconds (attach: 404 `session_id_not_found`).
- `missing_scope ... api.responses.write` arrived as an `error` event on
  every call with the restricted key; calls worked normally.
- Unanswered client delegation: the agent said "let me think it
  through" and stayed silent (delegation at 107 s, never answered).
  With `gptlive_call.py` answering it: delegation at 79 s,
  `session.commentary.appended`, the agent gave its recommendation and
  closed the call normally. Transcript deltas arrive on the sideband.
- One 11 s call showed no speech events before the person hung up; not
  reproduced in later calls.

Not tested: REFER transfers of GPT-Live outbound calls, Responses
delegation, the EU host `sip-eu.api.openai.com`, and DIDWW gateways
other than `fra.eu.out.didww.com`.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-openai) SIP
trunking, DIDWW's OpenAI guide and OpenAI's Telephony and SIP guide;
incoming calls, transfers and GPT-Live outbound verified with live calls
in November 2026. xAI's Grok voice offers a near-identical incoming
interface (`sip.voice.x.ai`); the didww-to-xai skill covers it.
