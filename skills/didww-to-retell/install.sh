#!/usr/bin/env bash
# Installs didww-to-retell into ~/.claude/skills/didww-to-retell/ (same as: npx didww-to-retell).
# Safe to re-run: an existing install is moved to ~/.claude/skill-backups/ first.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${HOME}/.claude/skills/didww-to-retell"
BACKUP_ROOT="${HOME}/.claude/skill-backups"
echo "Installing didww-to-retell"
echo "  source: ${SRC}"
echo "  dest:   ${DEST}"
if [[ -d "$DEST" ]]; then
  BACKUP="${BACKUP_ROOT}/didww-to-retell-$(date +%Y%m%d-%H%M%S)"
  echo "  backing up existing install to ${BACKUP}"
  mkdir -p "$BACKUP_ROOT"; mv "$DEST" "$BACKUP"
fi
mkdir -p "$DEST"
cp "${SRC}/SKILL.md" "${DEST}/SKILL.md"
cp -R "${SRC}/scripts" "${DEST}/scripts"
[[ -d "${SRC}/references" ]] && cp -R "${SRC}/references" "${DEST}/references"
find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
chmod +x "${DEST}/scripts/"*.py 2>/dev/null || true
echo; echo "Done. Restart Claude Code. It triggers on its own when you mention DIDWW together with Retell."
