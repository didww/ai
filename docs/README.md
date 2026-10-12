# Documentation for doc.didww.com

Draft pages for a new **AI agent skills** section of https://doc.didww.com/, one page per skill plus a landing page. They follow the structure of the existing integration guides (introduction with bullets, Before you begin, numbered steps, Note / Important / Warning admonitions, Troubleshooting, Additional resources) and link to the existing ElevenLabs, Retell AI, Vapi, trunk and MCP pages instead of repeating them.

| File | Proposed location |
|---|---|
| `index.md` | `ai-skills/index` (section landing page; a sibling of Integrations and MCP, or a child of Integrations) |
| `didww-connect.md` | `ai-skills/didww-connect` |
| `didww-to-<platform>.md` (8 files) | `ai-skills/didww-to-<platform>` |

## Format notes for the docs team

- Plain Markdown. Convert to the site's source format (reStructuredText or MyST) as usual; the structure maps one to one.
- Admonitions use the GitHub syntax: `> [!NOTE]`, `> [!IMPORTANT]`, `> [!WARNING]`. They correspond to Sphinx `note`, `important` and `warning` directives.
- Cross-links between these pages are relative (`didww-to-vapi.md`); links into the existing site are absolute `https://doc.didww.com/...` URLs and were checked on 2026-10-01 (the outbound trunk links added on 2026-10-12). Replace them with internal references when placing the pages.
- No screenshots are included. Suggested ones: the `npx <skill>` installer output, Claude Code showing a skill triggering, and the DIDWW User Panel trunk form for one platform.
- Third-party prices are deliberately left out; the pages point to each provider's billing page instead. Platform details were verified in August 2026, LiveKit end to end on LiveKit Cloud in October 2026, and the DIDWW outbound trunk rules against the outbound trunk documentation on 2026-10-12.

## Changes since the first draft (2026-10-12)

If an earlier copy of these pages was already handed over, every page changed. Replace them all.

- **Outbound trunk.** The DIDWW MCP has no outbound trunk tools, so every page now says you create the outbound trunk in the User Panel (**Voice**, **Outbound Trunks**, **Create New**). The earlier draft said the MCP created it.
- **Spend limit.** The earlier draft recommended a 24-hour limit of 10 to 50 USD, below the trunk's minimum of 50. The pages now say: **24 Hour Limit (USD)** at 50 (the default is 3000), a capacity limit, the usage notification, caller ID limited to the DID and destinations limited to the countries called.
- **Outbound access.** A new "Before you begin" item on the pages that place calls: outbound trunk access must be approved first. On the Vapi page it is required even for inbound calls.
- **Allowed SIP IP addresses.** Each page gives the platform's source addresses for the outbound trunk, or says to contact DIDWW support where the platform publishes none.
- **Hosts.** The full list of outbound hosts: `nyc.us`, `lac.us`, `mia.us`, `fra.eu`, `ams.eu`, `sg` and `hk` `.out.didww.com`.
- **LiveKit page.** Trunks are encrypted by default (TLS on port 5061 plus SRTP SDES). The SIP URI is copied from the project settings rather than derived. `--outbound-only` is new, and the failure map is rewritten from tested calls.
- **OpenAI Realtime and xAI pages.** These pages handle inbound calls only, so they no longer ask for a 24-hour limit, just a capacity limit on the inbound trunk.

The content is generated from the skills in `../skills/<name>/SKILL.md` and the scripts' usage text. When a skill changes, update its page here in the same commit.
