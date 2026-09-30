# Panels, Keys and Money: All Providers

Where things live in each provider's panel and how each one bills,
verified August 2026. Menu labels drift; treat paths as landmarks and
adapt if the user reports different screens. Always prefer MCP/OAuth over
keys where a column says so.

## DIDWW (the constant)

- Panel `my.didww.com` (signup `/users/sign_up`; sandbox panel
  `my-sandbox.didww.com`).
- Automation: MCP `https://api.didww.com/mcp` with OAuth: NO key needed.
  API key (script fallbacks only): panel menu API, then DIDWW API 3,
  Create new API Key.
- Money: pure PREPAID. Billing, then Payment Methods: card, PayPal, wire;
  Instant Payments for one-click top-up; Auto-charge toggle per method.
  Low Balance Notification lives on the same page and is OFF by default:
  switch it on with a threshold, every time, because services and number
  renewals stop at zero balance.

## ElevenLabs

- Panel `elevenlabs.io/app`. Keys: `elevenlabs.io/app/settings/api-keys`
  (workspace Service Account keys: profile icon, Workspace settings,
  Service Accounts). Prefer the OAuth MCP
  (`api.elevenlabs.io/v1/mcp`) for everything it covers.
- Money: monthly SUBSCRIPTION tiers granting credits (Free includes 15
  agent minutes; Starter 6 USD/75 min; Creator 22 USD/275 min; Pro 99
  USD/1,238 min). Extra agent minutes about 0.08 USD; concurrency above
  the tier cap bills 2x. LLM usage and telephony are billed ON TOP of
  the per-minute rate.
- Gotcha: agent minutes drain the same credit pool as TTS, so a chatty
  agent eats the subscription fast; watch usage in the first week.

## Vapi

- Panel `dashboard.vapi.ai`. Keys: `/org/api-keys`, shown ONCE at
  creation. Their MCP (`mcp.vapi.ai/mcp`, Bearer key) reads but cannot
  create trunks/numbers.
- Money: PREPAID credits, 1 credit = 1 USD, card with auto-reload
  (minimum 10 USD). 10 USD free credits, no card needed to start.
  Platform 0.05 USD/min plus provider passthrough (real total usually
  0.15 to 0.30 USD/min); numbers 2 USD/month.
- Gotcha: a NEGATIVE balance freezes the wallet, and if frozen at billing
  time add-ons INCLUDING PHONE NUMBERS auto-cancel. Set auto-reload on
  day one.

## Retell

- Panel `dashboard.retellai.com`. Keys: API Keys tab. Their MCP
  (`mcp.retellai.com`, Bearer key) covers agents AND number import:
  fullest automation of the group.
- Money: PREPAID credits with optional auto-recharge, Billing tab. 10 USD
  free trial credits. Real cost roughly 0.07 to 0.31 USD/min; using your
  own DIDWW trunk zeroes Retell's 0.015 USD/min telephony line, a real
  saving worth telling the user.
- Gotcha: subscription items (numbers, extra knowledge bases,
  concurrency) bill the card separately at cycle end, and calls
  hard-block at zero credits.

## Ultravox

- Panel `app.ultravox.ai`. Keys: Settings, API Keys, Generate New Key.
  No MCP.
- Money: usage-based, 0.05 USD/min agent time; SIP minutes are a
  SEPARATE line (about 0.005 USD/min). 30 free minutes. Pay-as-you-go
  has concurrency caps; Pro at 100 USD/month removes them.
- Gotcha: two meters run per call (agent time plus SIP time); quote both.

## Vogent

- Panel `app.vogent.ai`. Keys: API Keys page in the sidebar. No MCP.
- Money: per-minute, around 0.09 USD/min per their marketing, but there
  is NO public pricing page; verify actual rates inside the panel before
  the user scales anything.

## OpenAI (Realtime SIP)

- Panel `platform.openai.com`. Keys: `/api-keys`. Webhooks:
  `/settings/project/webhooks` (create, copy the signing secret).
- Money: PREPAID credits, Settings then Billing, minimum purchase 5 USD.
  Auto-recharge defaults to ON during setup; credits EXPIRE after one
  year, non-refundable. Realtime bills in audio tokens, not minutes
  (about 600 tokens/min heard, 1,200/min spoken); a typical phone
  conversation lands around 0.05 to 0.10 USD/min of model cost depending
  on talk ratio.
- Gotcha: the expiry and default auto-recharge surprise people; say both
  out loud during setup.

## xAI (Grok voice)

- Panel `console.x.ai`. Keys: API Keys page. Billing: Billing, API spend
  management (buy credits), Billing details for the card.
- Money: PREPAID credits, minimum top-up 25 USD, no free credits
  documented; calls hard-fail the instant credits hit zero unless auto
  top-up is configured (threshold, amount, monthly cap).

## LiveKit (Cloud or self-hosted)

- Panel `cloud.livekit.io`: project, Settings, Keys (API key plus a
  secret shown ONCE); the project URL, SIP URI and regional SIP
  endpoints are on the same settings page. No MCP; the SIP API is a
  Twirp HTTP service, covered by the skill's `scripts/connect.py`.
- Money: Build tier FREE with no card (1,000 agent-session minutes,
  1,000 SIP minutes, 5 concurrent sessions); Ship 50 USD/month (5,000
  minutes, 20 concurrent); Scale 500 USD/month (50,000 minutes, up to
  600 concurrent). Overage: agent session 0.01 USD/min, SIP 0.004
  USD/min (0.003 on Scale). The STT, LLM and TTS the worker uses bill
  separately at their own providers, or through LiveKit Inference
  credits.
- Gotcha: three meters run per call (agent session, SIP minute, the
  model providers), and a stopped worker means unanswered calls, not
  an error message; monitor the worker, not only the balances.

## The advice that applies everywhere

Turn on every low-balance or auto-recharge safety the provider offers at
setup time, not after the first dead call; tell the user the realistic
per-minute all-in cost for their chosen stack before the first real
traffic; and remind them the DIDWW side is prepaid too, so two balances
need watching: that is what the hub's `scripts/monitor.py` checks.
