# Changelog

All notable changes to the skills in this repository. Each skill is versioned independently in its `package.json`.

## Security and correctness review (2026-10-13)

`didww-to-openai-realtime` 1.1.0, `didww-to-vapi` 1.1.0, `didww-to-ultravox` 1.1.0, `didww-to-elevenlabs` 1.1.0, `didww-to-livekit` 1.1.1, and 1.0.2 of `didww-connect`, `didww-to-retell`, `didww-to-vogent` and `didww-to-xai`. Started from an automated review; every finding was reproduced in code and checked against the vendor's own documentation or OpenAPI schema before it was fixed, and the request shapes of all scripts were rechecked against those schemas.

- **All nine installers** refuse a `--dest` they do not own (home, `~/.claude`, the skills root, the backups folder, the package itself, a folder holding another skill or other files), a bare `--dest` and unknown options. Previously `--dest ~` would have moved the home directory into the backups. New `scripts/test_installers.py` runs every installer against a throwaway home.
- **OpenAI Realtime** `webhook_server.py`: refuses to start without `OPENAI_WEBHOOK_SECRET` and `OPENAI_API_KEY` (it used to accept unsigned webhooks); matches the To number exactly instead of by substring; caps the body at 1 MB with a socket timeout and a threaded server; drops duplicate deliveries by `webhook-id` (recorded only after success, so OpenAI's retries still run); implements the transfer the docs promised: a `transfer_call` tool in the accept body, a watcher on the call websocket, and `POST /v1/realtime/calls/{call_id}/refer` with `target_uri`. The docs now call the number match routing, not authentication, and say to keep the project ID private.
- **Vapi**: rebuilt on the setup documented by both Vapi (DIDWW SIP integration) and DIDWW (Vapi integration guide): the DIDWW inbound trunk points at `sip.vapi.ai` / `sip.eu.vapi.ai`, an inbound Vapi credential lists DIDWW's seven signaling IPs as inbound gateways, a separate outbound credential points at the DIDWW outbound host, the number is imported in E.164 with the `+`, and transfers use `max_transfers` 1 plus inbound-trunk Authorization. `--eu` now also sends the API calls to `api.eu.vapi.ai` (it only changed the printout). New `--rotate` replaces the nonexistent `--update` the docs referred to; new `--transport`; inbound-only setup without an outbound trunk.
- **Ultravox**: `--allow-agent` sends `allowedAgents` as `{agentId, toUserPattern}` objects (it sent strings, which the API schema rejects) and validates the UUID; new `--allow-didww` sets `46.19.208.0/21` and `185.238.172.0/22`, which cover every DIDWW signaling location; `0.0.0.0/0` is refused; the fallback handler's signing secret is redacted unless `--show-secrets`; strict flag parsing. The skill no longer suggests leaving the allowlist open: it is Ultravox's inbound authentication.
- **ElevenLabs**: the import sends `provider: "sip_trunk"` as in the API schema (it sent `provider_type`, which does not exist); the outbound trunk is optional so inbound can go live first; `agent_id` is set on the import itself.
- **xAI**: the one-time webhook secret is saved untruncated to `xai-<number>.json` (mode 0600, never overwritten) and masked on screen; the webhook URL must be https.
- **Monitor** (`didww-connect`): a check that cannot run now counts as a warning (a failing DID or trunk request used to end in OK); lists are paged at DIDWW's maximum of 100 and follow `links.next` on the same host only (it asked for 200 and read one page); `--number` matches exactly and warns when the number is missing or terminated; `DIDWW_API_BASE` must be https.
- **Retell, Vogent**: no `null` password is sent when only a username is given (Vogent requires both); echoed responses mask passwords.
- **LiveKit**: `LIVEKIT_URL` must be `https://` or `wss://` except on localhost.
- Every script that takes a password also reads it from an environment variable (`DIDWW_TRUNK_PASS` for the DIDWW outbound trunk; `ELEVENLABS_INBOUND_PASS`, `LIVEKIT_INBOUND_PASS`, `XAI_SIP_PASS`), and every script rejects unknown or valueless flags instead of ignoring them.

## All nine skills: DIDWW outbound trunk and spend limits corrected (2026-10-12)

`didww-connect` 1.0.1, `didww-to-livekit` 1.1.0 (both together with the changes below), and 1.0.1 of `didww-to-elevenlabs`, `didww-to-vapi`, `didww-to-retell`, `didww-to-ultravox`, `didww-to-vogent`, `didww-to-openai-realtime` and `didww-to-xai`. Checked against the DIDWW outbound trunk documentation.

- The DIDWW MCP has no outbound trunk tools, so every skill and doc page now says the user creates the DIDWW outbound trunk in the DIDWW User Panel (Voice, Outbound Trunks, Create New) and hands its credentials over in a file or environment variables. The MCP still covers the number and the inbound trunk.
- The recommended 24-hour spend limit of 10 to 50 USD was impossible: the outbound trunk's **24 Hour Limit (USD)** has a minimum of 50 and a default of 3000. The skills now set it to 50, with a capacity limit, the usage notification, caller ID limited to the DID and destinations limited to the countries the agent calls.
- Outbound access needs DIDWW's approval first (Get Access, a business account, a reply within 48 business hours). The skills check for this before promising outbound calls. For Vapi, the whole connection waits for it.
- The **Credentials & IP-Based** method needs at least one Allowed SIP IP. Each skill lists the platform's egress addresses where they are published (Vapi, Retell, LiveKit Cloud). Where none are published (ElevenLabs, Ultravox and Vogent outside enterprise plans), it sends the user to DIDWW support and never suggests `0.0.0.0/0`.
- Inbound trunks get a `capacity_limit` through the MCP. OpenAI Realtime and xAI use no outbound trunk, so their skills no longer ask for a 24-hour limit.
- Full list of DIDWW outbound hosts: `nyc.us`, `lac.us`, `mia.us`, `fra.eu`, `ams.eu`, `sg` and `hk` `.out.didww.com`.
- New failure map entry: an outbound call rejected by DIDWW after authentication (Allowed SIP IP, caller ID, destination, or the 24-hour limit, which disables the trunk).

## didww-to-livekit 1.1.0, didww-connect 1.0.1 (2026-10-09)

`didww-to-livekit`, verified end to end on LiveKit Cloud:

- Trunks are encrypted by default: `connect.py` now defaults to `--transport tls --srtp require`, and the skill sets the DIDWW inbound trunk to port 5061, TLS and SRTP SDES. Plain trunks are an opt-out (`--transport tcp --srtp disable`).
- `connect.py --sip-uri` (or `LIVEKIT_SIP_URI`) takes the SIP URI from the project settings. It is no longer derived from the Project URL, whose subdomain is different.
- `connect.py --outbound-only` adds the outbound trunk to a project that already has the inbound side.
- Both LiveKit trunks limit codecs to PCMA and PCMU and set `media.encryption`; the deprecated `media_encryption` field is no longer sent.
- The DIDWW outbound trunk is created by the user in the DIDWW panel, because the DIDWW MCP has no outbound trunk tools. The skill lists the LiveKit Cloud static IP ranges for its allowed IP list.
- Failure map rewritten from observed responses: `400 Bad Request` and `500 No suitable media` on SRTP mismatch, `484`, and `404` is not caused by a missing `+`.

`didww-connect`: LiveKit dashboard labels corrected (Settings, API keys; SIP URI).

## 1.0.0 (2026-10-01)

Initial public release of nine Claude Code agent skills, each installable with `npx <name>`:

- `didww-connect`: platform choice, universal DIDWW wiring, health monitor.
- `didww-to-elevenlabs`, `didww-to-vapi`, `didww-to-retell`, `didww-to-ultravox`, `didww-to-vogent`: hosted voice platforms.
- `didww-to-openai-realtime`, `didww-to-xai`: direct SIP to a model provider with a user-run backend.
- `didww-to-livekit`: bring-your-own-brain agents on LiveKit Cloud or self-hosted.

Also: per-skill tests with stubbed HTTP, GitHub Actions, and documentation drafts for doc.didww.com in `docs/`.
