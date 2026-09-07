#!/usr/bin/env bash
# In-game integration suite (needs a real window; run on a desktop session).
# Hard-bounded so a hang shows up as a failure instead of eating the session.
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
LOG="$(mktemp -t kaya_itest)"
"$GODOT" --path . --rendering-driver opengl3 --resolution 400x240 -- --itest=1 >"$LOG" 2>&1 &
PID=$!
LIMIT=${ITEST_TIMEOUT:-240}
for _ in $(seq "$LIMIT"); do
  kill -0 "$PID" 2>/dev/null || break
  sleep 1
done
if kill -0 "$PID" 2>/dev/null; then
  kill -9 "$PID" 2>/dev/null
  grep -viE 'Godot Engine v|OpenGL API|^$' "$LOG" | tail -40
  echo "integration: TIMED OUT after ${LIMIT}s"
  exit 124
fi
wait "$PID"; CODE=$?
grep -viE 'Godot Engine v|OpenGL API|^$' "$LOG"
exit $CODE
