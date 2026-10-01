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
- Cross-links between these pages are relative (`didww-to-vapi.md`); links into the existing site are absolute `https://doc.didww.com/...` URLs and were checked on 2026-10-01. Replace them with internal references when placing the pages.
- No screenshots are included. Suggested ones: the `npx <skill>` installer output, Claude Code showing a skill triggering, and the DIDWW User Panel trunk form for one platform.
- Third-party prices are deliberately left out; the pages point to each provider's billing page instead. Platform details were verified in August 2026 (LiveKit in September 2026); the skills themselves carry the same date.

The content is generated from the skills in `../skills/<name>/SKILL.md` and the scripts' usage text. When a skill changes, update its page here in the same commit.
