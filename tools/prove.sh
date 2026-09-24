#!/usr/bin/env bash
# The Route Prover (ADR 005). Plays each level's declared route with the real
# movement code and writes levels/<id>.tape.json as the proof.
#
#   tools/prove.sh                          every level that has a route
#   tools/prove.sh jungle_1 jungle_4        just these
#   tools/prove.sh --route "spawn>exit:human" jungle_1
#   tools/prove.sh --level-file=res://tests/fixtures/x.json
#   tools/prove.sh --verify-tapes           fail if any tape is stale
#   tools/prove.sh --waypoints              list the ids a route may name
#   tools/prove.sh --mark foot:14,25        try a waypoint before writing the DSL
#   tools/prove.sh --diff-hops jungle_3     name the state that differs at each hop
#                                           boundary between the search and a replay
#   tools/prove.sh --require-full           make a PARTIAL verdict fail the run
#
# Two verdicts, and they are not the same claim:
#   PROVED   the whole route was played, and the tape reproduces it.
#   PARTIAL  the route ends at a `boss_exit`, which Level.on_boss_defeated()
#            places and nothing else does. Traversal is proved as far as the
#            arena; the rest is the boss gate's (ADR 005 section 4). The tape is
#            stamped "partial": true and lists the hops it does not prove.
#
# Exit codes: 0 every hop proved, 1 a hop failed, 2 a level declared no route.
# A PARTIAL level exits 0 -- the prover HAS finished its job -- unless
# --require-full is given. The run ends with a summary naming every partial.
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

LOG="$(mktemp -t kaya_prove)"
trap 'rm -f "$LOG"' EXIT

"$GODOT" --headless --path . res://tools/solver/prove.tscn -- "$@" >"$LOG" 2>&1
CODE=$?

# Godot's banner and its exit-time RID bookkeeping are noise; the prover's own
# lines are the report.
grep -viE 'Godot Engine v|OpenGL API|were leaked|resources still in use|^\s+at: |^$' "$LOG"
exit $CODE
