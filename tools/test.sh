#!/usr/bin/env bash
# Runs the headless unit suite. Exit code is the gate.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
"$GODOT" --headless --path . --script res://tests/run_tests.gd "$@"

# The committed iOS pck must track the source it was exported from. The byte
# probes in tests/test_ios_bundle.gd catch content the pck visibly lacks; this
# catches EVERY divergence, because the hash walks src/, data/, levels/ and
# assets/ — the probes' blind spots included. It lives here rather than in the
# Godot suite so the comparison runs the exact same python that recorded the
# hash, with no re-implementation to drift.
CURRENT="$("$PYVENV" tools/hash_game_data.py)"
RECORDED="$(cat ios/.pck_source_hash 2>/dev/null || echo missing)"
if [ "$CURRENT" != "$RECORDED" ]; then
  echo "FAIL ios pck source hash: the committed ios/KayaOfTheCanopy.pck was" >&2
  echo "     exported from different source than this checkout." >&2
  echo "     recorded $RECORDED" >&2
  echo "     current  $CURRENT" >&2
  echo "     Run tools/sync_ios_project.sh and commit the result." >&2
  exit 1
fi
