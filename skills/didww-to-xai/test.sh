#!/usr/bin/env bash
# Regression checks for this skill: stdlib Python plus node, no network, no keys.
set -euo pipefail
cd "$(dirname "$0")"
python3 -c 'import ast, sys; [ast.parse(open(f).read(), f) for f in sys.argv[1:]]; print(f"syntax OK: {len(sys.argv) - 1} script(s)")' scripts/*.py
for t in tests/test_*.py; do python3 "$t"; done
node bin/install.js --dry-run >/dev/null && echo "installer: dry-run OK"
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
