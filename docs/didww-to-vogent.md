# DIDWW to Vogent skill

Use the **didww-to-vogent** skill with **Claude Code** to connect a DIDWW phone number to a **Vogent** voice agent. Vogent's API imports the number and links it to the agent; the one setting its API does not expose, the transfer type of a Call Transfer function, is a single dashboard step that the skill walks you through.

- Route incoming calls from a DIDWW number to a Vogent agent, with an opening line that greets the caller.
- Import the DIDWW number into Vogent over SIP with the DIDWW outbound trunk's host and credentials, and link it to the agent.
- Place outbound calls through DIDWW and transfer active calls to a live person with Vogent warm transfers.

This skill automates the steps described in the [Vogent integration guide](https://doc.didww.com/integrations/vogent/index.html). Read that guide for the manual path and screenshots.

> [!IMPORTANT]
> Transfers from a Vogent agent through DIDWW work only as **Warm Transfer**, where Vogent places the transfer call itself through your DIDWW outbound trunk. **Cold Transfer** is marked as transferred in Vogent, but DIDWW never places the call. Both were verified on real calls in October 2026.

## How the skill works

| Side | Path the skill uses | Authentication |
|---|---|---|
| DIDWW: number, inbound trunk | DIDWW MCP `https://api.didww.com/mcp` | OAuth sign-in, no keys |
| DIDWW: outbound trunk, inbound trunk authorization, spend limits | You, in the DIDWW User Panel. The MCP has no outbound trunk tools, and the outbound password stays out of the chat | Your panel login |
| Vogent: number import and linking the number to the agent | REST `POST /api/phone_numbers`, then `PUT /api/phone_numbers/{id}`, via `scripts/connect.py` | `VOGENT_API_KEY` (Bearer) |
| Vogent: Call Transfer function | REST `POST /api/functions` and `PUT /api/agents/{id}` | `VOGENT_API_KEY` (Bearer) |
| Vogent: transfer type (Warm Transfer) | Dashboard, one setting: the API does not expose it | Your Vogent sign-in |

## Before you begin

- An active [DIDWW account](https://my.didww.com/) with at least one DID number, or a balance to buy one. Numbers in registration-required countries add a verification wait.
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed and signed in.
- The DIDWW MCP connected in Claude Code, so the agent can manage numbers and inbound trunks under your account:

  ```bash
  claude mcp add --scope user --transport http didww https://api.didww.com/mcp
  ```

  Then run `/mcp` inside Claude Code and sign in to the DIDWW User Panel when the browser opens. See [Getting started with DIDWW MCP](https://doc.didww.com/mcp/getting-started.html).
- Access to DIDWW outbound trunks on the account, **even for an inbound-only line**: Vogent imports a number over SIP only with the termination address and credentials of an outbound trunk. If **Voice**, **Outbound Trunks** in the DIDWW User Panel shows **Get Access**, apply there first ([Get access to outbound trunks](https://doc.didww.com/voice/outbound-trunks/get-access.html)): it needs a business account with a company name and VAT/TAX ID, and DIDWW replies within 48 business hours.
- A [Vogent](https://app.vogent.ai/) account with an agent, and a Vogent API key: in Vogent, go to **API > Keys**, click **New Key**, and copy the secret key. The UUID-shaped value in the key list is the key's ID, not the key, and Vogent answers it with "unauthorized".

## Step 1. Install the skill

Run the installer in a terminal:

```bash
npx didww-to-vogent
```

It copies the skill into `~/.claude/skills/didww-to-vogent/` and nothing else. If a previous copy exists, it is moved to `~/.claude/skill-backups/` first. Restart Claude Code afterwards.

Without the npm registry, the same files install straight from GitHub:

```bash
npx skills add didww/ai --skill didww-to-vogent
```

> [!NOTE]
> The installer needs Node.js 16.7 or later. The skill's script needs Python 3 with no extra packages.

## Step 2. Start the conversation

```text
Connect my DIDWW number +33 1 44 55 66 77 to my Vogent agent.
```

The skill confirms the number (or country to buy one in), the agent, and a transfer target if any.

## Step 3. What gets configured

### DIDWW side

The number and the inbound trunk are configured through the DIDWW MCP under your own account permissions. Claude Code asks for confirmation before each tool call unless you have allowed that tool. The outbound trunk, and the outbound credentials on the inbound trunk, are set by you in the DIDWW User Panel.

- **Inbound SIP trunk** ([1. Route Incoming Calls to Vogent](https://doc.didww.com/integrations/vogent/index.html#vogent-inbound)). Host `sip.vogent.ai`, port 5060, transport UDP. **User Part of R-URI** keeps the default `{DID}`; Vogent accepts the called number with or without the `+`, so `+{DID}` also works. The DID is assigned to this trunk, with a capacity limit set through the MCP.
- **Outbound SIP trunk** ([2. Enable Outbound Calling from Vogent through DIDWW](https://doc.didww.com/integrations/vogent/index.html#vogent-outbound)). Required even for an inbound-only line: Vogent needs its host and credentials to import the number, and it carries outbound calls and warm transfers. You create it in the DIDWW User Panel under **Voice**, **Outbound Trunks**, **Create New**. If that page shows **Get Access**, the account is not approved for outbound calling yet; the inbound trunk can be prepared meanwhile. Keep the **Credentials & IP-based** authentication method. In **Allowed SIP IP addresses**, enter the outbound SIP source IP ranges Vogent provides for your enterprise account, together with DIDWW's inbound signaling IPs, as listed in the guide. Vogent does not provide static ranges outside its enterprise plan; without them, contact DIDWW support (support@didww.com) to confirm a supported authentication setup. `0.0.0.0/0` removes the IP restriction and is meant only for temporary testing, at your own risk: SIP digest authentication still applies, but DIDWW does not recommend it. Do not enter `0.0.0.0/32`, which matches no address and silently blocks every call. DIDWW generates the username and password (the key icon in the **Credentials** column); give them to the agent in a file or environment variables rather than pasting them into the chat. Enable the trunk if it shows **Disabled**. The host is the one nearest to where calls are placed: `nyc.us.out.didww.com`, `lac.us.out.didww.com`, `mia.us.out.didww.com`, `fra.eu.out.didww.com`, `ams.eu.out.didww.com`, `sg.out.didww.com` or `hk.out.didww.com`.
- **Outbound credentials on the inbound trunk** ([Step 4: Add Outbound Credentials to the Inbound Trunk](https://doc.didww.com/integrations/vogent/index.html#vogent-inbound-authorization)). On the Vogent inbound trunk, **Authorization**, **Enable Authorization**, with **Auth User** and **Auth Password** set to the outbound trunk's username and password. You enter them in the DIDWW User Panel so the outbound password stays out of the chat.
- **Spend controls.** On the outbound trunk, under **Termination**: **24 Hour Limit (USD)** at its minimum of 50 (the default is 3000, and DIDWW disables the trunk when the limit is reached), **Capacity limit** matching the expected concurrency, and the usage limit notification on. Under **Destination Dialing Settings**, reject all destinations except the countries the agent calls or transfers to. Under **CLI Settings**, the verified transfer setup used **Send Original CLI** on CLI mismatch with any DID allowed; a stricter caller ID rule is untested with transfers.

### Vogent side

These follow [3. Connect DIDWW SIP Trunks in Vogent](https://doc.didww.com/integrations/vogent/index.html#vogent-connect) in the guide.

- **Number import** ([Step 1: Import Your DIDWW Number into Vogent](https://doc.didww.com/integrations/vogent/index.html#vogent-import-number)). One call to the phone numbers API with `type: "sip_import"` carrying the E.164 number with the `+`, the `terminationUri` set to a DIDWW outbound signaling endpoint as a hostname only (no `sip:` prefix or port), and the DIDWW outbound trunk credentials.
- **Link the number to your agent** ([Step 2: Link the Number to Your Agent](https://doc.didww.com/integrations/vogent/index.html#vogent-link-number)). `PUT /api/phone_numbers/{id}` with `{"agentId": "..."}`, the ID shown under your agent's name. The script does it with `--agent`. **Agents**, your agent, **Numbers**, **Link Number** in the dashboard does the same.
- **Opening line** ([Step 3: Set the Agent's Opening Line](https://doc.didww.com/integrations/vogent/index.html#vogent-opening-line)). Without one the agent waits for the caller to speak first. For a **Standard** agent the skill sets **Opening Line** to **Inbound calls Only** with a greeting; for a **Flow** agent the greeting lives in the flow (`flowDefinition.openingLineType` `INBOUND_ONLY` in its versioned prompt).

```bash
DIDWW_TRUNK_PASS=... VOGENT_API_KEY=... python3 ~/.claude/skills/didww-to-vogent/scripts/connect.py \
  --number +33144556677 --didww-host fra.eu.out.didww.com --didww-user USER --agent AGENT_ID
```

To link the agent to a number imported earlier, run `connect.py --phone-id PHONE_NUMBER_ID --agent AGENT_ID`.

## Step 4. Add call transfers to your live agent

This follows [Step 4: Add Call Transfers to Your Live Agent](https://doc.didww.com/integrations/vogent/index.html#vogent-transfer-calls) in the guide. Call transfers in Vogent are a **Call Transfer** function that the agent runs during a call, for example when the caller asks for a person. Vogent offers **Cold Transfer** and **Warm Transfer**. With DIDWW only Warm Transfer works:

- **Cold Transfer** hands the call to DIDWW with a SIP REFER whose target Vogent builds from the phone number alone; it has no SIP URI setting. Vogent marks the call as transferred, but DIDWW never places the new call: there is no outbound call record and the caller waits in silence.
- **Warm Transfer** makes Vogent place a new call to the destination itself, through the number's `terminationUri` (the DIDWW outbound trunk) from Vogent's own servers, so the outbound trunk's **Allowed SIP IP addresses** must accept them. Vogent briefs the person who answers, then connects the caller. Both call legs stay connected for the transferred conversation, so Vogent's per-minute rate and the DIDWW outbound call both run; review both charges before using transfers.

The skill creates the function with `POST /api/functions` (`type` `transfer`, the destination in `allowedNumbers` as `{"number": "+E164"}`, and a started message for the caller), adds it to the agent with `PUT /api/agents/{id}` (`linkedFunctionDefinitionInputs`, listing every function the agent keeps), and for a Standard agent adds a prompt line saying when to call `transfer_call` and with which destination. For a Flow agent, the transfer is a function call node in the flow. Do not use a DIDWW number that is linked to your Vogent agent as the destination, or the transferred call returns to your agent.

> [!IMPORTANT]
> Finish the function in the Vogent dashboard: open **Functions**, the Call Transfer function, **Config**, and set **Transfer Type** to **Warm Transfer**. The API does not expose this setting, and new functions default to Cold Transfer. With **Warm Transfer Type** set to **Prompted**, enter the **Prompt** the agent uses to brief the person who answers. Switching to Cold Transfer and back clears that prompt; enter it again before you save.

## Step 5. Test the configuration

The skill ends every build with the same checks ([Step 5: Test the Configuration](https://doc.didww.com/integrations/vogent/index.html#vogent-test)). Do them before real traffic:

1. **Inbound call.** Call the DIDWW number: the agent answers with its opening line, and **Dial History** in Vogent shows the call as **Incoming**.
2. **Outbound call**, if the agent places calls. From the agent's **Make Call**, **Phone Call**, with your DIDWW number as **From Number**, or with `POST /api/dials` (`callAgentId`, `fromNumberId`, `toNumber` in E.164). Check the caller ID.
3. **Call transfer**, if configured. Ask the agent for a person: the destination rings and hears the briefing, then both sides hear each other. **Dial History** shows **Transferred** and the `transfer_call` function in the **Transcript** tab; the status alone does not confirm that the recipient answered. The DIDWW **Outbound Call Logs** show the transfer as a call through the Vogent outbound trunk.

## Troubleshooting

The skill carries this failure map, which matches the guide's [Troubleshooting](https://doc.didww.com/integrations/vogent/index.html#troubleshooting), and works through it when a test call fails.

| Symptom | Likely cause | Fix |
|---|---|---|
| The call connects, but nobody speaks | The agent waits for the caller to speak first | Set **Opening Line** to **Inbound calls Only** with a greeting |
| The call is not answered by the agent | The number is not linked to the agent, **User Part of R-URI** is not `{DID}` or `+{DID}`, the number is not imported in E.164 with the `+`, or the inbound trunk is not assigned to the DID | Link the number with `connect.py --phone-id ... --agent ...` or on the agent's **Numbers** tab, and check the inbound trunk and the import |
| The number import fails in Vogent | **Termination URI** is not a bare DIDWW outbound signaling endpoint, or the username and password are not the outbound trunk's | Use the hostname only, for example `fra.eu.out.didww.com`, and the outbound trunk credentials |
| **Dial History** shows **Transferred**, but the destination does not ring | **Transfer Type** is not **Warm Transfer**, the outbound trunk's **Allowed SIP IP addresses** do not accept Vogent's servers, or the destination is not in **Allowed Numbers** | Set **Warm Transfer**, fix the allowed addresses, and add the destination. A transfer DIDWW does not receive leaves no entry in the **Outbound Call Logs** |
| **401**, **403** or **407** on an outbound call or transfer | The imported number's credentials differ from the outbound trunk's, the inbound trunk's **Authorization** is off or uses another pair, or the allowed addresses do not accept Vogent's servers | Put the outbound trunk's username and password on both, and fix the allowed addresses |
| **484 Address Incomplete** on an outbound call | The number is not in full E.164 format | Dial `+` and the full international number, without `0`, `00` or `011` prefixes |
| The outbound call or transfer is rejected after authentication | Caller ID not allowed in **CLI Settings**, destination not allowed, the **24 Hour Limit (USD)** or **Capacity limit** reached, or the account balance too low | Check the outbound trunk and the balance in the DIDWW User Panel, and re-enable the trunk if the limit disabled it |
| Vogent shows the caller's number with an extra **+1** | DIDWW sends the caller's number without the `+`, and Vogent reads it as a US number; a call from `+442079460000` appears with `+1` in front | Calls connect normally; only the number shown in Vogent is affected. A caller ID prefix `+` on the DIDWW inbound trunk is the likely fix, not yet tested |
| The Vogent API returns "unauthorized" | The request uses the ID of the API key instead of the secret key | Create a new key under **API > Keys** and copy the secret key |

## Keys, billing and safety

- **Vogent credentials.** In Vogent, go to **API > Keys**, click **New Key**, and copy the secret key. Vogent publishes no pricing page; confirm the per-minute rate inside the panel before scaling.
- **Call details.** **Dial History** in Vogent shows each call's transcript, function calls and completion reason. `GET /api/dials/{id}` returns the same, but the API cannot list calls, so the skill takes the id from the dashboard URL.
- **Two balances.** DIDWW is prepaid, and so is the AI platform. Either one reaching zero stops calls silently. In the DIDWW User Panel, open **Billing, Payment Methods** to top up, enable **Auto-charge**, and switch on the **Low Balance Notification**, which is off by default.
- **Cost per minute.** The real cost is the platform's per-minute or per-token price plus DIDWW call charges, and a warm transfer adds a second DIDWW call for the transferred conversation. The skill quotes the all-in figure before real traffic starts; check the platform's current pricing page, these numbers change.

## Additional resources

- [Vogent integration guide](https://doc.didww.com/integrations/vogent/index.html): the same connection configured by hand.
- [Vogent SIP trunking overview](https://docs.vogent.ai/telephony/sip/overview), [create phone number API](https://docs.vogent.ai/api-reference/create-number), [update phone number API](https://docs.vogent.ai/api-reference/update-phone-number) and [function calling](https://docs.vogent.ai/platform-overview/tools/function-calling) in the Vogent documentation.
- [Inbound trunks](https://doc.didww.com/voice/inbound-trunks/index.html) and [Outbound trunks](https://doc.didww.com/voice/outbound-trunks/index.html) in the DIDWW documentation.
- [DIDWW MCP](https://doc.didww.com/mcp/index.html): the connector the skill uses for the carrier side.
- Skill source and tests: [`skills/didww-to-vogent`](https://github.com/didww/ai/tree/main/skills/didww-to-vogent) in the didww/ai repository. Package: [npmjs.com/package/didww-to-vogent](https://www.npmjs.com/package/didww-to-vogent).
- [DIDWW Connect](didww-connect.md): the hub skill that compares all supported platforms.
