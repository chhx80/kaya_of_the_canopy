#!/usr/bin/env bash
# Boots an exported build headless and fails on any startup error.
#
# This exists because a release export once died at startup on an autoload that
# the export filter had stripped — something no source-tree test can see, and
# nothing a screenshot would reveal either.
#
#   usage: tools/smoke_build.sh [path-to-binary]
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

BIN="${1:-build/macos/app/Kaya of the Canopy.app/Contents/MacOS/Kaya of the Canopy}"
if [ ! -x "$BIN" ]; then
  echo "smoke: no binary at '$BIN' — run tools/export_macos.sh first" >&2
  exit 2
fi

# Known-benign engine shutdown chatter. `AudioManager._exit_tree` already stops
# and unbinds every stream (verified), but the AudioServer releases its own
# playback reference after the ObjectDB leak check runs, so the line appears
# even on a stock project. Everything else is a genuine failure.
ALLOW='resources still in use at exit'

LOG="$(mktemp -t kaya_smoke)"
"$BIN" --headless --quit >"$LOG" 2>&1 &
PID=$!
for _ in $(seq 40); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
kill -9 "$PID" 2>/dev/null
wait "$PID" 2>/dev/null

BAD="$(grep -E '^(ERROR|SCRIPT ERROR|USER ERROR)' "$LOG" | grep -vE "$ALLOW" || true)"
if [ -n "$BAD" ]; then
  echo "smoke: FAILED — the exported build reports errors at startup:"
  echo "$BAD" | head -20
  exit 1
fi
echo "smoke: exported build starts clean"
