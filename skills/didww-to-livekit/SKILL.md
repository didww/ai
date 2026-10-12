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
in one call. The DIDWW side is the MCP (OAuth) for the number and the
inbound trunk. The MCP has NO outbound trunk tools: the DIDWW outbound
trunk is created by the user in the DIDWW panel.

## The flow

1. **Confirm in one message:** number (or country to buy), the worker's
   `agent_name`, LiveKit Cloud or self-hosted, region (EU data residency
   is a one-word change), whether outbound calls are needed. Say that
   the trunks are encrypted by default (TLS and SRTP) and that plain
   trunks are an opt-out.
2. **LiveKit side, keys:** Cloud dashboard, project, Settings, API keys:
   create a key; the secret is shown once. Note two separate values on
   the settings page: the Project URL (`wss://<project>.livekit.cloud`)
   and the SIP URI (`sip:<sip-subdomain>.sip.livekit.cloud`). Their
   subdomains differ (for example `my-project-ab12cd34` and
   `vjnxecm0tjk`), so never derive one from the other. Self-hosted: the
   SIP service's own host and the server's key pair.
3. **LiveKit side, wiring (`scripts/connect.py`):** with
   `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` set, one run
   creates the inbound trunk (E.164 number with `+`, digest
   `auth_username`/`auth_password` = an invented pair, codecs limited to
   PCMA and PCMU, SRTP required) and the dispatch rule (one room per call,
   `room_config.agents[0].agent_name` = the worker's name, bound to that
   trunk id only). Add `--outbound-host <DIDWW host> --outbound-user
   --outbound-pass` to also create the outbound trunk from the DIDWW
   outbound trunk's credentials, over TLS by default. Pass
   `--sip-uri <SIP URI from settings>`
   (or set `LIVEKIT_SIP_URI`) so it can echo the host for the DIDWW
   trunk; without it a placeholder is printed. `--show` lists everything
   and prints the SIP URI; run it first on an existing project, the
   script does not deduplicate. When the outbound credentials arrive
   after the inbound side exists (the usual order, see step 4), add the
   outbound trunk alone with `--outbound-only --number <DID>
   --outbound-host --outbound-user --outbound-pass`; re-running the
   full command would create a second inbound trunk.
   By hand instead: `lk sip inbound create`
   / `dispatch create` / `outbound create` with a `{"trunk": {...}}` or
   `{"dispatch_rule": {...}}` file, or the dashboard (Telephony, SIP
   trunks, Create new trunk, JSON editor tab, the object WITHOUT the
   wrapper; digest fields only show in the JSON editor).
4. **DIDWW side (MCP, OAuth; outbound trunk in the panel):**
   - Inbound trunk (Voice, Inbound Trunks, Create New, SIP Trunk): Type
     `Static Endpoint`; User Part of R-URI `{DID}` (this is what
     LiveKit matches against the trunk's `numbers`); Host
     `<sip-subdomain>.sip.livekit.cloud`, the SIP URI without `sip:`
     (or region-pinned
     `<sip-subdomain>.<eu|us|uk|india|japan|aus|canada|sa>.sip.livekit.cloud`);
     Port 5061, Transport TLS; CLI Format E.164. Authorization tab:
     Enable Authorization with the SAME pair as step 3. Media & DTMF
     tab: Codecs PCMA and PCMU only (G.711 is the whole overlap, DIDWW
     has no G.722), SRTP Mode `SRTP SDES`, DTMF RFC 2833. Attach the
     DID.
   - Outbound trunk: NOT available through the MCP. Ask the user to
     create it in the panel (Voice, Outbound Trunks, Create New) with
     the settings below and to hand over the generated username and
     password, in a file or environment variables rather than pasted
     into chat. Do the inbound side meanwhile. Credentials &
     IP-Based needs at least one Allowed SIP IP even with credentials.
     LiveKit Cloud in Canada, EU, India, Japan, US: `143.223.88.0/21`,
     `161.115.160.0/19`, `153.57.128.0/18` (also in the allowed RTP
     list if there is one); other Cloud regions have no static range;
     self-hosted: the SIP service's public IP. Enable SRTP SDES in its
     media settings. Allow the DID as caller ID. Note host and
     generated credentials for step 3's outbound flags. Before Create
     New: a Get Access button under Voice, Outbound Trunks means the
     account is not approved yet (business account with company name
     and VAT/TAX ID; DIDWW answers within 48 business hours); say so
     and finish the inbound side meanwhile. Termination: 24 Hour Limit
     (USD) at its minimum, 50 (default 3000; the trunk is disabled when
     it is reached), Capacity limit = expected concurrency, usage limit
     notification on; CLI limited to the DID; Destination dialing Reject
     All except the countries the agent calls. Enable the trunk if it
     shows Disabled. Host: the region-nearest of `nyc.us.out.didww.com`,
     `lac.us.out.didww.com`, `mia.us.out.didww.com`,
     `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com`,
     `hk.out.didww.com`.
   - NOTE, the DIDWW trunks must match the script: it creates secure
     LiveKit trunks by default (`--transport tls --srtp require`,
     both directions verified on Cloud). A DIDWW trunk left on TCP 5060
     with SRTP Mode Disabled does not fall back to plain audio, the
     call fails: inbound 400 Bad Request, outbound 500 No suitable
     media. LiveKit's outbound trunk reaches DIDWW on 5061 by itself,
     the port never goes in the address.
   - Plain trunks, only if the user asks: run the script with
     `--transport tcp --srtp disable`, DIDWW inbound trunk Port 5060,
     Transport TCP, SRTP Mode Disabled, no SRTP on the DIDWW outbound
     trunk. On an outbound trunk `allow` and `require` BOTH offer
     encrypted media only, so `allow` is not a fallback there.
5. **Worker:** the agent code registers `agent_name` in its worker
   options (explicit dispatch) and must be running when the call
   arrives. The dialed DID is `sip.trunkPhoneNumber` and the caller is
   `sip.phoneNumber` on the SIP participant, so one worker can serve
   many numbers. Outbound calls are the worker's `CreateSIPParticipant`
   through the outbound trunk (token needs the `sip.call` grant).
6. **Verify:** inbound from a mobile, watch the worker log pick up the
   job; outbound checking caller ID; transfer if configured.

## Failure map

- 407 then 401 on the INVITE: digest pair differs between the DIDWW
  trunk and the LiveKit trunk. A single 407 is the normal challenge.
- 404 on the INVITE: no inbound trunk or dispatch rule matched. Check
  User Part of R-URI is `{DID}`, the DID is in the trunk's `numbers`,
  the rule's `trunk_ids` holds that trunk, and the source is inside
  `allowed_addresses` if set. A missing `+` is NOT the cause: numbers
  are normalised before matching.
- 400 Bad Request on the INVITE (LiveKit's call record says 488 Media
  Failed): no media agreement. Codecs other than PCMA/PCMU on the DIDWW
  trunk, or SRTP settings that disagree (DIDWW SRTP Disabled while the
  LiveKit trunk requires encryption).
- Outbound 500 No suitable media, from DIDWW: the LiveKit outbound trunk
  offers SRTP (`allow` or `require`) and the DIDWW outbound trunk has no
  SRTP SDES. Enable it there or drop encryption on the LiveKit trunk.
- Rings then 486, or rings and nobody answers: `agent_name` in the
  dispatch rule differs from the worker's, or the worker is not running
  (486 comes after `ringing_timeout`, 3 minutes by default). Only a
  LiveKit Agents worker is started by `agent_name`; any other bot must
  join the room by itself.
- Answered then dead after about 30 seconds: media timeout, no RTP is
  reaching LiveKit; check the SRTP setting matches on both trunks and
  that nothing filters UDP 10000 to 20000 (self-hosted).
- No audio or one-way audio, self-hosted: the SIP service advertises a
  private IP; set `use_external_ip` or `nat_1_to_1_ip` on it.
- Outbound trunk refused at creation: the address must be the bare DIDWW
  host (`fra.eu.out.didww.com`), no `sip:`, no `;transport=`.
- Outbound 401, 403 or 407 from DIDWW: wrong credentials, or the source
  is not in the trunk's Allowed SIP IP list (ranges in step 4).
- Outbound 484: dialed number incomplete; use full E.164 with the `+`.
- Outbound rejected after authentication: caller ID is not a DID on the
  account, destination not allowed, or the balance; or the 24 Hour
  Limit was reached, which disables the trunk (re-enable it in the
  panel).
- 405 when a provider tries to REGISTER: LiveKit never accepts
  registration; DIDWW does not register with a Static Endpoint trunk,
  so this only shows up if the trunk Type is Dynamic Registration or
  the user pointed a PBX at the URI.
- IP allowlist ignored on Cloud: `allowed_addresses` is enabled per
  project by LiveKit support; digest works without asking anyone.

## Panel map and money

LiveKit Cloud: `cloud.livekit.io`, project, Settings, API keys (secret
shown once); the Project URL and the SIP URI, which have different
subdomains, are on the same project settings page; trunks and dispatch
rules are under Telephony. Money: Build tier is free with no card,
includes 1,000 agent-session minutes, 1,000 SIP minutes and 5
concurrent sessions;
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
trunking and LiveKit's SIP API; verified October 2026 on LiveKit Cloud
(inbound and outbound, plain and with TLS plus SRTP). For writing
the worker itself, the voice-agent-telephony skill is the companion.
