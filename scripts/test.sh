#!/usr/bin/env bash
# Runs every skill's own test.sh: stdlib Python plus node, no network, no keys.
set -euo pipefail
cd "$(dirname "$0")/.."
for d in skills/*/; do echo "== ${d%/}"; bash "${d}test.sh"; echo; done
