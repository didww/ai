#!/usr/bin/env bash
# Publishes this skill to npm. Needs `npm login` first; bump "version" in
# package.json before republishing, npm refuses to overwrite a version.
set -euo pipefail
cd "$(dirname "$0")"
npm whoami >/dev/null 2>&1 || { echo "Not logged in to npm. Run:  npm login"; exit 1; }
bash test.sh
npm publish --access public "$@"
NAME="$(node -p "require('./package.json').name")"
echo; echo "Published ${NAME}. Try:  npx ${NAME} --dry-run"
