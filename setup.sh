#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="mingli-skill"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-$HOME/.codex/skills}"
DESTINATION="$TARGET_DIR/$SKILL_NAME"

if [[ -e "$DESTINATION" || -L "$DESTINATION" ]]; then
  printf 'Installation target already exists: %s\n' "$DESTINATION" >&2
  printf 'Choose another target directory or remove the existing skill first.\n' >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
mkdir -p "$DESTINATION"
tar \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='datasets/cache' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  -C "$SOURCE_DIR" \
  -cf - . | tar -C "$DESTINATION" -xf -

test -f "$DESTINATION/SKILL.md"
printf 'Installed %s to %s\n' "$SKILL_NAME" "$DESTINATION"
