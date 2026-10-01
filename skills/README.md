# Skills

The nine skills, one folder each. The table of skills, install instructions and requirements are in the [root README](../README.md); this page covers the folder itself.

Claude Code skills that put an AI voice agent on a DIDWW phone number. One hub skill picks
the platform and does the universal DIDWW wiring (number, inbound and outbound SIP trunks,
digest auth, spend limits, verification calls); eight pairing skills cover one voice platform
each, as automatically as that platform's API and MCP allow.

## Install

Each skill is its own npm package and installs into `~/.claude/skills/<name>/`:

```bash
npx didww-connect
npx didww-to-livekit
```

Straight from GitHub, no registry: `npx skills add didww/ai --skill didww-to-livekit`
(or `npx skills add didww/ai --list` to see all nine). From a clone: `./skills/<name>/install.sh`,
or copy `skills/<name>` to `~/.claude/skills/<name>`. Restart Claude Code afterwards; the skills
trigger on their own when you mention DIDWW together with a platform.

Every installer copies files and nothing else; an existing install is moved to
`~/.claude/skill-backups/`, never overwritten. Carrier-side automation uses the DIDWW MCP
(`https://api.didww.com/mcp`, OAuth sign-in); nothing here stores credentials.

## Layout

```
skills/<name>/
  SKILL.md          the skill (frontmatter description drives triggering)
  scripts/          one stdlib Python script per REST gap; --help on each
  references/       hub only: where keys and billing live per provider
  bin/install.js    npx installer (--dry-run, --dest DIR, --help)
  install.sh        same thing for a clone
  tests/            request-shape tests against stubbed HTTP, no keys
  package.json      npm name = skill name
```

## Tests

From the repo root, `bash scripts/test.sh` runs every skill's checks (stdlib Python plus node, no network, no keys).
GitHub Actions runs the same on every push.

## Publishing

`npm login` once, then from the repo root `bash scripts/publish.sh` for all nine or `bash scripts/publish.sh didww-to-vapi`
for one. Bump the `version` in that skill's `package.json` first; npm refuses to overwrite
a published version.

Companion skill for building the agent itself: voice-agent-telephony.

License: MIT
