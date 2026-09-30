---
name: didww-to-openai-realtime
description: >
  Point a DIDWW phone number directly at OpenAI's Realtime API over SIP,
  with a generated webhook backend for call control. Use whenever the
  user wants gpt-realtime answering a real phone number via DIDWW,
  mentions sip.api.openai.com, realtime.call.incoming webhooks, Realtime
  SIP, or debugging calls between DIDWW and OpenAI. This is the
  developer-grade pairing: the agent behavior is code the user owns.
---

# DIDWW to OpenAI Realtime

The most direct wiring in the family: the DIDWW trunk points straight at
OpenAI, no platform in between. The tradeoff is that there is no agent
object to configure; every incoming call fires a webhook and YOUR code
accepts it with instructions. This skill therefore generates that
backend (`scripts/webhook_server.py`) rather than pretending
configuration exists. Not a no-code path; say so in intake and offer the
hosted platforms if the user has no way to run a small public HTTPS
endpoint.

## The flow

1. **Confirm in one message:** number (or country to buy), what the
   agent should do (becomes the instructions), transfer target, where
   the webhook backend will run (any host that can serve public HTTPS:
   a five-dollar VPS, a serverless function, a tunnel for testing).
2. **OpenAI side:** in platform settings, create a project webhook for
   `realtime.call.incoming` pointing at the backend URL; note the
   webhook secret. The project ID (`proj_...`) becomes the SIP address.
3. **DIDWW side (MCP, OAuth):** inbound trunk with destination
   `sip:{project_id}@sip.api.openai.com;transport=tls`, port 5061,
   TLS signaling and SRTP media (both REQUIRED; EU data residency uses
   `sip-eu.api.openai.com`). Attach the DID. Note: no digest auth
   exists on OpenAI's ingress; the webhook's accept/reject decision IS
   the auth gate, so the generated server rejects calls to unknown DIDs
   by default.
4. **Deploy the backend:** `scripts/webhook_server.py` is a stdlib-only
   starting point: verifies the webhook signature, accepts calls with
   the model and instructions, exposes the transfer via the refer
   endpoint (`POST /v1/realtime/calls/{call_id}/refer` with
   `tel:` target). Adapt, deploy, set `OPENAI_API_KEY` and
   `OPENAI_WEBHOOK_SECRET` in its environment.
5. **Verify:** inbound call from a mobile; watch the server log accept
   the call; test the transfer phrase. Outbound calls are not part of
   OpenAI's SIP interface as of August 2026; originate outbound from the
   DIDWW side or a platform if needed.

## Failure map

- Call rings once and dies: TLS or SRTP not set on the DIDWW trunk
  (both are mandatory), or the project ID in the SIP address is wrong.
- Webhook never fires: webhook not configured for the project, or the
  backend URL is not publicly reachable HTTPS.
- Call connects then silence: the accept API call failed; check the
  server log, the API key, and that the accept happens within seconds.
- Anyone can ring the URI: expected; keep the unknown-DID rejection in
  the server, it is the security model.

## Panel map and money

OpenAI keys: `platform.openai.com/api-keys`; webhooks (required here):
`platform.openai.com/settings/project/webhooks`, copy the signing
secret at creation. Billing: prepaid credits under Settings, Billing
(minimum 5 USD); auto-recharge defaults to ON during setup and credits
EXPIRE after one year, non-refundable: say both out loud. Realtime
bills in audio tokens, not minutes; a typical phone conversation lands
around 0.05 to 0.10 USD/min of model cost depending on talk ratio.
DIDWW side: prepaid; top-up, Auto-charge and Low Balance Notification
(OFF by default) in Billing, Payment Methods.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-openai) SIP
trunking and OpenAI's Realtime SIP guide; verified August 2026. xAI's
Grok voice offers a near-identical interface (`sip.voice.x.ai`); the
didww-to-xai skill covers it.
