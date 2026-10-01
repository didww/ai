# Contributing

Thanks for helping improve DIDWW's AI tools. This file covers the layout, the checks and how to add or change a skill.

## Repository layout

```
skills/<name>/        one Claude Code skill = one npm package
  SKILL.md            instructions; the frontmatter description decides when the skill triggers
  scripts/            stdlib Python only, each with --help
  references/         hub only: supporting reference material
  bin/install.js      npx installer (copy-only, --dry-run, --dest, backs up an existing install)
  install.sh          the same for a clone
  tests/              request-shape tests against stubbed HTTP; no keys, no network
  package.json        npm name = skill name; files whitelist
docs/                 pages for doc.didww.com, one per skill
scripts/              family-wide test and publish runners
```

## Before you open a pull request

1. Run `bash scripts/test.sh`. CI runs the same and must be green.
2. Keep scripts dependency-free (Python standard library) so the installer never needs `pip`.
3. Never commit credentials, account identifiers or real phone numbers. Tests use stubbed HTTP and fake keys.
4. Verify platform facts against the platform's current documentation and update the "verified" date at the end of the skill's `SKILL.md`.
5. If you change a skill's behaviour, update its page in `docs/` in the same change.

## Adding a platform

Copy the closest existing pairing (`didww-to-vogent` is the smallest), then:

- Write `SKILL.md` with a pushy description (what it does and when to trigger), the automation map, the flow, a failure map and the panel map.
- Add one script per REST gap the platform's MCP cannot cover, with a usage docstring.
- Add `tests/test_<script>.py` that stubs `urllib.request.urlopen` and asserts the exact request bodies.
- Fill in `package.json`, keeping `name` equal to the folder name, and add the skill to the tables in the root `README.md`, `skills/README.md`, the hub's `SKILL.md`, and `docs/`.

## Versioning and publishing

Each skill is versioned independently in its `package.json`. Bump the version in the same pull request as the change, then a maintainer publishes with `bash scripts/publish.sh <name>` after `npm login`. npm refuses to overwrite a published version, so a change without a bump cannot ship.

## Commit messages

One line in the imperative mood that says what changed and why, for example `didww-to-vapi: allowlist EU signaling IP on the inbound trunk`.
