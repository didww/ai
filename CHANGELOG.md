# Changelog

All notable changes to the skills in this repository. Each skill is versioned independently in its `package.json`.

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
