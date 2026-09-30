---
name: didww-to-livekit
description: >
  Connect a DIDWW phone number to a LiveKit Agents worker over SIP, on
  LiveKit Cloud or self-hosted: inbound trunk, dispatch rule to a named
  agent, optional outbound trunk. Use whenever the user wants a LiveKit
  agent (any STT, LLM and TTS combination, including Claude as the
  brain) answering a real number via DIDWW, mentions sip.livekit.cloud,
  SIP inbound trunks or dispatch rules, lk sip commands, agent_name
  dispatch, or debugging calls between DIDWW and LiveKit. This is the
  bring-your-own-brain pairing: the agent is code the user runs.
---

# DIDWW to LiveKit

The open-framework option in the family. LiveKit is the SIP-to-WebRTC
bridge plus the agent runtime; the STT, LLM and TTS are whatever the
worker code plugs in, which is why this is the pairing to reach for when
the user wants Claude (or any model) as the brain and does not want a
hosted platform in between. The price is that a worker process must be
running (LiveKit Cloud agent deployment or the user's own machine); no
worker, no answer. Say that in intake and offer ElevenLabs, Vapi or
Retell if the user wants no-code.

LiveKit has no MCP; its SIP API is a Twirp HTTP service signed with the
project's API key and secret, and `scripts/connect.py` covers all of it
in one call. The DIDWW side is the MCP (OAuth) as always.

## The flow

1. **Confirm in one message:** number (or country to buy), the worker's
   `agent_name`, LiveKit Cloud or self-hosted, region (EU data residency
   is a one-word change), whether outbound calls are needed.
2. **LiveKit side, keys:** Cloud dashboard, project, Settings, Keys:
   create a key; the secret is shown once. Note the project URL
   (`wss://<subdomain>.livekit.cloud`); the SIP URI on the same settings
   page is `sip:<subdomain>.sip.livekit.cloud`. Self-hosted: the SIP
   service's own host and the server's key pair.
3. **LiveKit side, wiring (`scripts/connect.py`):** with
   `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` set, one run
   creates the inbound trunk (E.164 number with `+`, digest
   `auth_username`/`auth_password` = an invented pair, SRTP allowed) and
   the dispatch rule (one room per call, `room_config.agents[0].agent_name`
   = the worker's name, bound to that trunk id only). Add
   `--outbound-host <DIDWW host> --outbound-user --outbound-pass` to
   also create the outbound trunk from the DIDWW outbound trunk's
   credentials. `--show` lists everything and prints the SIP URI; run it
   first on an existing project, the script does not deduplicate.
4. **DIDWW side (MCP, OAuth):** inbound trunk with host
   `<subdomain>.sip.livekit.cloud` (or region-pinned
   `<subdomain>.<eu|us|uk|india|japan|aus|canada|sa>.sip.livekit.cloud`),
   port 5060 TCP/UDP or 5061 TLS, digest auth with the SAME pair as
   step 3, SRTP matching `--srtp`. Attach the DID. Outbound trunk
   created; note host and generated credentials for step 3's outbound
   flags. Spend limits 10 to 50 USD/day, honest channel caps.
5. **Worker:** the agent code registers `agent_name` in its worker
   options (explicit dispatch) and must be running when the call
   arrives. The dialed DID is `sip.trunkPhoneNumber` and the caller is
   `sip.phoneNumber` on the SIP participant, so one worker can serve
   many numbers. Outbound calls are the worker's `CreateSIPParticipant`
   through the outbound trunk (token needs the `sip.call` grant).
6. **Verify:** inbound from a mobile, watch the worker log pick up the
   job; outbound checking caller ID; transfer if configured.

## Failure map

- 403 on the INVITE: digest pair differs between the DIDWW trunk and
  the LiveKit trunk (or a region-pinned endpoint refused a call that
  local rules keep in-country).
- 404 on the INVITE: the dialed number is on no inbound trunk; almost
  always the `+` missing, DIDWW shows numbers without it.
- Rings then 486, or rings and nobody answers: `agent_name` in the
  dispatch rule differs from the worker's, or the worker is not running.
- Answered then dead after about 30 seconds: media timeout, no RTP is
  reaching LiveKit; check the SRTP setting matches on both trunks and
  that nothing filters UDP 10000 to 20000 (self-hosted).
- One-way audio, self-hosted: the SIP service advertises a private IP;
  set `use_external_ip` on it.
- Outbound 503: the outbound trunk address must be the bare DIDWW host
  (`fra.eu.out.didww.com`), no `sip:`, no port.
- 405 when a provider tries to REGISTER: LiveKit never accepts
  registration; DIDWW does not register, so this only shows up if the
  user pointed a PBX at the URI.
- IP allowlist ignored on Cloud: `allowed_addresses` is enabled per
  project by LiveKit support; digest works without asking anyone.

## Panel map and money

LiveKit Cloud: `cloud.livekit.io`, project, Settings, Keys (secret shown
once); the SIP URI and regional endpoints are on the same project
settings page. Money: Build tier is free with no card, includes 1,000
agent-session minutes, 1,000 SIP minutes and 5 concurrent sessions;
Ship 50 USD/month (5,000 minutes, 20 concurrent), Scale 500 USD/month
(50,000 minutes, up to 600 concurrent). Beyond the allowance agent
sessions are 0.01 USD/min and SIP 0.004 USD/min (0.003 on Scale). The
model bill is separate: the STT, LLM and TTS providers the worker uses,
or LiveKit Inference credits. For the firewall on a self-hosted or
locked-down DIDWW side, LiveKit Cloud's static ranges are
`143.223.88.0/21`, `161.115.160.0/19`, `153.57.128.0/18` (Canada, EU,
India, Japan, US). DIDWW side: prepaid; top-up, Auto-charge and Low
Balance Notification (OFF by default) in Billing, Payment Methods.

---

Built around [DIDWW](https://www.didww.com/?ref=didww-to-livekit) SIP
trunking and LiveKit's SIP API; verified September 2026. For writing
the worker itself, the voice-agent-telephony skill is the companion.
