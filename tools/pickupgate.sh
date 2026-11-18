#!/usr/bin/env bash
# The Pickup Gate. For every heart, key and transform pad, search the real
# movement code -- the Route Prover's simulation, plus the shoulder-break the
# prover leaves out -- from every state the proof tape passes through, and
# require the body to touch it.
#
#   tools/pickupgate.sh                          every level with a fresh tape
#   tools/pickupgate.sh deeps_2 deeps_4          just these
#   tools/pickupgate.sh --world deeps            ids starting with "deeps"
#   tools/pickupgate.sh --budget 6000 --seeds 4  search harder before giving up
#   tools/pickupgate.sh jungle_3 --only "26,12;3,4"  just the targets on these tiles
#   tools/pickupgate.sh --allow-hazard           let the body touch spikes (it costs
#                                                a heart, not a life)
#   tools/pickupgate.sh --json shots/x.json      also write the results
#   tools/pickupgate.sh --probe deeps_2 --at 36,21 --form frog --goal 42,18 --stand
#                                                one search, tile to tile
#   ... --broken "32,23;32,24"                   with those tiles already broken
#
# REACHED is a proof (a replayed tape touches it). NOT FOUND is a finding, not
# a proof: check it in the running game before changing the level.
# Exit codes: 0 everything reached, 1 something not found, 3 cannot run.
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

LOG="$(mktemp -t kaya_pickupgate)"
trap 'rm -f "$LOG"' EXIT

"$GODOT" --headless --path . res://tools/pickupgate/pickupgate.tscn -- "$@" >"$LOG" 2>&1
CODE=$?
grep -viE 'Godot Engine v|OpenGL API|were leaked|was leaked|resources still in use|^\s+at: |^$' "$LOG"
exit $CODE
