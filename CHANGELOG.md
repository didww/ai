# Changelog

All notable changes to the skills in this repository. Each skill is versioned independently in its `package.json`.

## didww-to-xai 1.1.0, didww-connect 1.0.6 (2026-11-13)

Aligned with DIDWW's [xAI integration guide](https://doc.didww.com/integrations/xai/index.html) and verified on real calls through DIDWW with the skill: an incoming call answered by an xAI console voice agent and a transfer to a live person by SIP REFER. The skill's new section 8 lists the live test results.

- **Console voice agents.** The skill said xAI has no stored agent, so every call needed your own webhook backend. xAI's console now has voice agents, and a number added with `agent_id` routes to one with no server. That is now the default setup (DIDWW's guide). The webhook backend stays as the developer option, and the skill asks which one first.
- **`register_number.py`:**
  - `--agent agent_...` routes the number to a console agent; `--webhook` remains, and exactly one is required;
  - `--digest` reads the SIP pair from `--env-file` (the DIDWW outbound trunk's credentials file), so no password passes through argv or the chat;
  - `--allow-didww` sets DIDWW's seven signaling IPs;
  - `--list` and `--delete` manage registered numbers;
  - the number must be E.164 with `+`;
  - the one-time secret file is written only for `--webhook`.
- **DIDWW trunk settings from the guide:** inbound trunk to `sip.voice.x.ai` on 5061 over TLS, User Part of R-URI `+{DID}`, IPv4, PCMU/PCMA/telephone-event, SRTP Disable, Max Transfers 1. The skill had no transfer steps and said no outbound trunk is involved. Transfers need one: DIDWW's seven signaling IPs, media encryption Disabled, the destination allowed, and its credentials on the inbound trunk's Authorization.
- **Transfer target `sip:`, not `tel:`.** The skill told the backend to refer to a `tel:` target, which DIDWW rejects. The console tool and the backend now use `sip:+{number}@{DIDWW outbound host}`.
- **No outbound calls:** xAI has no API to place calls and publishes no SIP source addresses. The skill says so in intake.
- **Account facts:**
  - the key type must be Grok API, not Cursor, and xAI creates none until a payment method is on file;
  - auto top-ups are at least 5 USD (the skill said a 25 USD minimum);
  - credits are non-refundable;
  - voice costs 0.08 USD/min;
  - the agent ID comes from the console, because `GET /v1/agents` answers 403 for new teams.
- **New failure-map rows:** a transfer "declined" (a destination the outbound trunk does not allow), a transfer reaching voicemail, a transfer looping back to the agent's own number, silence with Welcome message off, and no API key.
- `tests/test_register_number.py` now has 35 checks: the agent and webhook bodies, `--digest` from a file without printing the password, `--allow-didww`, the refusals, `--list` and `--delete`.
- **`didww-connect`:** xAI gets its own row in the chooser (console agent, incoming and transfers only), the ingress notes and outbound Allowed SIP IPs (it said "no outbound trunk needed"), and the billing facts in `references/panels-and-billing.md`. `docs/didww-to-xai.md`, `docs/didww-connect.md` and the family tables match.

## didww-to-ultravox 1.1.1, didww-connect 1.0.5 (2026-11-10)

Found while connecting a DIDWW number to an Ultravox agent with the skill, and verified on real calls: an incoming call, a SIP REFER transfer to a live number, and an outgoing call through a DIDWW outbound trunk. The skill now links DIDWW's [Ultravox integration guide](https://doc.didww.com/integrations/ultravox/index.html) and follows it.

- **Transfers.** The skill had no transfer steps, and the first transfer failed with `10020 error - Unauthorized`. New step: the built-in `coldTransfer` tool with a `sip:+{number}@{DIDWW outbound host}` target and `sipVerb` REFER, `max_transfers` 1 on the inbound trunk, and the outbound trunk's username and password on the inbound trunk's Authorization. With those, the transfer succeeded and the destination rang.
- **Outbound trunk Allowed SIP IPs.** The skill said Ultravox publishes no source addresses. Ultravox's SIP runs on Voximplant, which publishes its SIP servers; the skill now lists the US and EU ones from the guide, plus DIDWW's seven inbound signaling IPs for transfers. The test call came from one of the listed Voximplant addresses.
- **Media encryption Disabled.** The skill said to match the platform side. Ultravox offers unencrypted media only: with SRTP SDES on the outbound trunk, the outgoing call ended before ringing with 500 No suitable media.
- Smaller corrections: inbound codecs PCMU, PCMA and telephone-event (Ultravox does not take G.729 or G.723); routing by number pattern with DIDWW's default `{DID}` user part (the fallback webhook is for more than 20 agents); outgoing calls with `POST /api/agents/{agent_id}/calls`, where `to` must be a SIP URI; the SIP logs endpoint for diagnosis; new failure-map rows. `connect.py` prints the agent calls endpoint.
- `didww-connect`: Ultravox's ingress notes and outbound Allowed SIP IPs (it said "no published range").

## didww-to-openai-realtime 1.2.0, didww-connect 1.0.4 (2026-11-05)

Aligned with DIDWW's [OpenAI integration guide](https://doc.didww.com/integrations/openai/index.html) and verified on real calls: incoming Realtime calls, a transfer to a live person, and GPT-Live outbound calls through a DIDWW outbound trunk. The skill's new section 7 lists every live test result.

- **Choose the setup first.** `didww-to-openai-realtime` now asks whether the user wants incoming calls, incoming calls with transfer, GPT-Live outbound calls, or both, because they use different OpenAI APIs, trunks and credentials; each option has its own steps.
- **GPT-Live outbound calls.** New `scripts/gptlive_call.py`: one `POST /v1/live/sessions` per run with the DIDWW outbound trunk's digest credentials (`sips:{gateway}:5061`), never retried; attaches to the sideband at once (it replays only 3 s), logs ringing, answer, failure with DIDWW's SIP response and the transcript, and hangs up at `--max-seconds`, on Ctrl-C, or when it cannot attach. `--check` validates without calling; `--init-env` creates a mode-600 credentials file, so the API key and trunk password never pass through the chat. The skill was wrong that OpenAI's SIP interface has no outbound calls.
- **Silent GPT-Live agent.** With client delegation, an unanswered `session.delegation.created` left the agent saying "let me think it through" and then silent. The script answers every delegation with `session.commentary.append` and the same `delegation_id`; on a real call the agent then continued with its recommendation.
- **Incoming calls with DIDWW.** `webhook_server.py` reads the called number from `Diversion` (DIDWW's `To` carries the project ID, so the To-only match rejected every DIDWW call), greets the caller with `response.create` and `tool_choice: "none"` (accepting alone left the agent silent, and a greeting with tools could start a transfer), uses a stricter transfer tool description, logs refer errors with their body, answers non-POST requests with 405, reads `--env-file`, and refuses to start with a `tel:` transfer target (DIDWW answers 603) or one that loops back to a served DID.
- **Trunk settings from the guide:** inbound codecs PCMU, PCMA and telephone-event, IPv4, `max_transfers` 1, the outbound trunk's credentials on the inbound trunk's Authorization, SRTP SDES on the outbound trunk, DIDWW's seven IPs for transfers and OpenAI's four ranges for GPT-Live.
- New `tests/test_gptlive_call.py`; `tests/test_webhook.py` covers the `Diversion` match, the greeting, the `sip:` refer target, the start-up refusals and the 405.
- **OpenAI needs an outbound trunk for transfers and outbound calls.** The hub said "OpenAI and xAI: no outbound trunk needed". DIDWW places every transfer of an incoming Realtime call through the outbound trunk (DIDWW's seven inbound signaling IPs, SRTP SDES, the trunk's username and password on the inbound trunk's Authorization, `max_transfers` 1, a `sip:` target; `tel:` fails with 603), and GPT-Live dials the outbound trunk directly with its digest credentials. Without OpenAI's four SIP ranges in Allowed SIP IPs the call fails with 403 Forbidden before any CDR; without SRTP SDES with 500 No suitable media. xAI is unchanged.
- The OpenAI row and ingress notes: OpenAI also places outbound calls with GPT-Live, and the called DID arrives in `Diversion` (the `To` header holds the project ID).
- `references/panels-and-billing.md`: the webhook permission, the restricted key that worked, outbound SIP enablement for GPT-Live (`outbound_sip_not_enabled`), and DIDWW outbound billing for calls and transfer legs.

## didww-to-elevenlabs 1.1.1, didww-connect 1.0.3 (2026-11-03)

Found while setting up a DIDWW number on an ElevenLabs agent with the skill; every fix was confirmed by real inbound calls and a real live-agent transfer.

- **Number format.** `import_number.py` only accepted numbers with a leading `+`. The DIDWW inbound trunk sends the called number as `{DID}`, without a plus, and DIDWW's ElevenLabs guide says to import it in E.164 without the `+`. The script now accepts either form and always imports the number without the plus; the docs, the example command and the failure map say the same.
- **Media encryption.** New `--media-encryption disabled|allowed|required` to match the DIDWW trunks (`disabled` for SRTP mode Disable, the DIDWW default). It was hardcoded to `allowed`, which stays the default.
- **ElevenLabs MCP host.** `https://api.elevenlabs.io/v1/mcp` names `https://api.us.elevenlabs.io/v1/mcp` as its resource in its OAuth protected-resource metadata, and Claude Code then refuses to start sign-in ("Couldn't start sign-in for elevenlabs"). Every reference now uses `https://api.us.elevenlabs.io/v1/mcp`.
- **Live-agent transfers.** The skill said it covered transfers but had no transfer steps, and its invented inbound digest pair breaks them. New transfer section following DIDWW's AI-to-Live Agent guide: SIP REFER; DIDWW's seven inbound signaling IPs on the outbound trunk; the outbound trunk's username and password on the DIDWW inbound trunk and on the ElevenLabs number; `max_transfers` 1 or more; the inbound trunk's network protocol matching the outbound trunk; the agent's `transfer_to_number` tool with `transfer_type: sip_refer` to a `sip_uri` at the DIDWW outbound host. When outbound calls or transfers are planned, the skill uses the outbound pair from the start. New `import_number.py --update PHONE_NUMBER_ID` switches an imported number's inbound credentials (`PATCH /v1/convai/phone-numbers/{id}`) without the password passing through the chat. New failure-map rows for transfers, the MCP sign-in error and 409 `phone_number_conflict`.
- `didww-connect`: the ElevenLabs MCP host in `references/panels-and-billing.md`, and the ElevenLabs number format and transfer requirements in the platform cheat sheet.

## didww-to-vogent 1.0.3, didww-connect 1.0.3 (2026-11-03)

Found while connecting a DIDWW number to a Vogent agent with the skill, verified on real calls, and aligned with DIDWW's [Vogent integration guide](https://doc.didww.com/integrations/vogent/index.html): the skill and its docs page now follow the guide's three sections (Route Incoming Calls, Enable Outbound Calling, Connect DIDWW SIP Trunks in Vogent), its terms and its troubleshooting.

- **Transfers work only as Warm Transfer.** Cold Transfer (SIP REFER, target built from the phone number, no SIP URI setting) is marked `TRANSFERRED` in Vogent, but DIDWW never places the call: no outbound CDR, also with `0.0.0.0/0` open. Warm Transfer makes Vogent dial the destination itself through the number's `terminationUri`, the DIDWW outbound trunk, from Vogent's servers. New "Live-agent transfers" section following the guide's Step 4: the Call Transfer function (`POST /api/functions`, `allowedNumbers`, never a number linked to the agent), the Transfer Type, which only the dashboard sets (new functions default to Cold; Prompted needs a prompt, which switching to Cold and back clears), adding it to the agent (`PUT /api/agents/{id}` with `linkedFunctionDefinitionInputs`) and the prompt line.
- **The outbound trunk is required even for inbound-only**, because Vogent imports a number only with an outbound trunk's host and credentials (the docs said "needed only for calls the agent places").
- **Outbound trunk Allowed SIP IPs** as in the guide: Vogent's enterprise ranges plus DIDWW's seven inbound signaling IPs; without enterprise ranges, DIDWW support; `0.0.0.0/0` only for temporary testing at the user's own risk; `0.0.0.0/32` matches nothing.
- **Inbound trunk:** UDP 5060, User Part of R-URI `{DID}` (Vogent also accepts `+{DID}`), and Authorization with the outbound trunk's username and password instead of an invented digest pair.
- **Linking the number to the agent is not dashboard-only.** `PUT /api/phone_numbers/{id}` with `{"agentId"}` works. New `connect.py --agent` links right after the import, and `--phone-id ID --agent ID` links a number imported earlier; the "MANUAL STEP" print is gone.
- **Opening line:** without one the agent waits for the caller and the call sounds silent. Standard agents: Opening Line, Inbound calls Only; flow agents: `flowDefinition.openingLineType` `INBOUND_ONLY`.
- **Testing** as in the guide's Step 5, including `POST /api/dials` for an outbound call and Dial History's Transferred status with the `transfer_call` function.
- **Failure map** from the guide's troubleshooting: 401/403/407 on outbound calls or transfers, 484 Address Incomplete, rejection after authentication, the caller shown with an extra `+1` (cosmetic; `cli_prefix` `+` is a likely fix, marked untested), and the API key's secret versus its ID.
- `didww-connect`: Vogent's row, ingress notes and allowed-IP notes follow the guide.
## Agent Skills discovery index (2026-10-30)

- New `.well-known/agent-skills/index.json` in the [Agent Skills discovery](https://github.com/cloudflare/agent-skills-discovery-rfc) format v0.2.0, the same format Telnyx serves at `telnyx.com/.well-known/agent-skills/index.json`. Every skill is a `type: "archive"` entry: a `.tar.gz` with `SKILL.md`, `scripts/`, `references/` and `LICENSE` at the root, and its sha256 `digest`. Extra fields (`version`, `documentation`, `install`) are ignored by clients that do not know them.
- `scripts/build_index.py` generates the folder from `skills/` (descriptions from the SKILL.md frontmatter, versions from `package.json`); archives are rewritten only when their contents change, so digests stay stable. `--check` runs in `scripts/test.sh` and CI.
- `scripts/mirror_index.py` lets didww.com keep its copy current from GitHub on a schedule: it verifies every digest and archive before swapping the new set in, and leaves the live folder untouched on any failure. Handoff for the web team: [`docs/agent-skills-index.md`](docs/agent-skills-index.md).

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
