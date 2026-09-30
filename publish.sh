#!/usr/bin/env bash
# Publishes skills to npm (all of them, or the names given). Needs `npm login` first;
# bump "version" in a skill's package.json before republishing it.
set -euo pipefail
cd "$(dirname "$0")"
npm whoami >/dev/null 2>&1 || { echo "Not logged in to npm. Run:  npm login"; exit 1; }
names=("$@"); [[ ${#names[@]} -eq 0 ]] && names=($(ls skills))
for n in "${names[@]}"; do echo "== $n"; bash "skills/$n/publish.sh"; echo; done
