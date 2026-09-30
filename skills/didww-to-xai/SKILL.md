---
name: didww-to-xai
description: >
  Point a DIDWW phone number at xAI's Grok voice over SIP. Use whenever
  the user wants Grok answering a real phone number via DIDWW, mentions
  sip.voice.x.ai, xAI realtime calls, registering a phone number with
  xAI, or debugging calls between DIDWW and Grok. Developer-grade: agent
  behavior is configured per call over a websocket the user's code owns.
---

# DIDWW to xAI (Grok voice)

xAI's SIP interface mirrors OpenAI's shape with one improvement: the
number is REGISTERED with xAI first (an API object carrying its own SIP
auth), so ingress is gated by digest credentials or an IP allowlist
rather than webhook-only. Like OpenAI, there is no stored agent: on each
incoming call a webhook fires and your code connects a websocket to
configure voice, instructions and turn detection. Not a no-code path;
offer the hosted platforms if the user cannot run a small backend.

## The flow

1. **Confirm in one message:** number (or country to buy), agent
   behavior (becomes the per-call session config), transfer target,
   where the webhook backend runs.
2. **Register the number (`scripts/register_number.py`):**
   `POST https://api.x.ai/v2/phone-numbers` with `origin: "byo_trunk"`
   (the customer-owned-number type), the number, `webhook: {url}` for
   incoming-call events (an object, not a bare string) and `sip_auth`:
   digest credentials as `auth_username`/`auth_password` (preferred;
   invent a pair) and/or `allowed_addresses` with DIDWW's signaling
   IPs. The response carries the webhook signing secret exactly once
   and the SIP password is never returned again: store both
   immediately, the password in the DIDWW trunk, the secret in the
   backend's environment.
3. **DIDWW side (MCP, OAuth):** inbound trunk with destination
   `sip:{number}@sip.voice.x.ai;transport=tls`, digest auth from step 2.
   Attach the DID, set spend limits.
4. **Backend:** on the incoming-call webhook (carries `call_id`),
   connect `wss://api.x.ai/v1/realtime?call_id={call_id}` and send
   `session.update` with voice, instructions and turn detection. Call
   control: `POST /v1/realtime/calls/{call_id}/refer` with a `tel:`
   target for transfers, `/hangup` to end; DTMF arrives as
   `input_audio_buffer.dtmf_event_received` events. The OpenAI variant
   server in the didww-to-openai-realtime skill is the closest template;
   adapt its accept step to the websocket model.
5. **Verify:** inbound call, transfer phrase, hangup handling.

## Failure map

- Call never reaches xAI: TLS missing on the trunk, or digest pair
  mismatch with the registration object.
- Webhook fires but silence: the websocket connect or `session.update`
  failed; log both.
- Lost the SIP password: it is unreadable after creation; rotate by
  updating the registration and the DIDWW trunk together.
- Lost the webhook signing secret: also shown only at registration;
  re-register the number and update the backend's environment.
- 422 on registration: field names drifted; the API's error names the
  accepted fields (`auth_username`, `webhook.url`, ...), adjust and rerun.

## Panel map and money

xAI keys: `console.x.ai`, API Keys page. Billing: Billing, API spend
management: prepaid credits with a 25 USD minimum top-up and no free
credits documented; calls hard-fail the instant credits hit zero, so
configure auto top-up (threshold, amount, monthly cap) at setup. DIDWW
side: prepaid; top-up, Auto-charge and Low Balance Notification (OFF by
default) in Billing, Payment Methods.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-xai) SIP
trunking and xAI's speech-to-speech SIP docs; verified August 2026.
