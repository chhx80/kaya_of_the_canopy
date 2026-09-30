#!/usr/bin/env bash
# In-game integration suite. Runs --headless: the real Level, its entities,
# triggers and bosses all simulate with no display (ADR 005), so this is a CI
# gate, not a desktop-only one.
# Hard-bounded so a hang shows up as a failure instead of eating the session.
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
LOG="$(mktemp -t kaya_itest)"
"$GODOT" --headless --path . -- --itest=1 "$@" >"$LOG" 2>&1 &
PID=$!
# 240 was honest for a five-level game. The twenty-five-level game's full run is
# 791 checks -- five boss suites with their own arenas, and a replay tape per
# level -- and most of it is spent waiting on physics frames rather than on the
# CPU, so it runs in about real time: MEASURED at 1008 s and 1020 s on two runs
# on an idle M-series machine, using 2m42s of CPU in that span. This
# is a bound on a HANG, not a budget, and it has to clear a loaded or slower
# machine by a wide margin or the gate reports TIMED OUT on a suite that passed.
# 1800 is 17 minutes plus 75%. Override it DOWNWARD when driving a subset:
#   ITEST_TIMEOUT=600 tools/itest.sh --only=t_boss_obsidian_heart
LIMIT=${ITEST_TIMEOUT:-1800}
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
