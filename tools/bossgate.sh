#!/usr/bin/env bash
# THE BOSS GATE -- ADR 005, section 4.
#
#   tools/bossgate.sh                 run every check against jungle_5's boss
#   tools/bossgate.sh --quick         thin the fairness sweep (smoke, not proof)
#   tools/bossgate.sh --record        re-record the strategy tape, then re-check
#   tools/bossgate.sh --level=x --boss=y
#   tools/bossgate.sh --sloppy[=profile]  measure: the boss's own policy through
#                                     tools/bossgate/sloppy.json's hands, many
#                                     seeds (KAYA_BOSSGATE_SEEDS). Not a check.
#   tools/bossgate.sh --tells         measure: every telegraph and its reaction
#                                     window, threats live at once. Not a check.
#
# Exit code is the gate: 0 all checks passed, 1 a check failed.
#
# --fixed-fps unhitches the main loop from the wall clock: the physics delta
# stays exactly 1/60, so the simulation is bit-identical to a real run, it just
# stops sleeping between frames. The fairness sweep is thousands of seconds of
# simulated fight and is only affordable this way.
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

export KAYA_BOSSGATE_LEVEL="${KAYA_BOSSGATE_LEVEL:-jungle_5}"
export KAYA_BOSSGATE_BOSS="${KAYA_BOSSGATE_BOSS:-boss_grove}"
export KAYA_BOSSGATE_MODE=check
export KAYA_BOSSGATE_QUICK="${KAYA_BOSSGATE_QUICK:-}"
RECORD=0
SLOPPY=0

for a in "$@"; do
  case "$a" in
    --quick)   export KAYA_BOSSGATE_QUICK=1 ;;
    --record)  RECORD=1 ;;
    --level=*) export KAYA_BOSSGATE_LEVEL="${a#--level=}" ;;
    --boss=*)  export KAYA_BOSSGATE_BOSS="${a#--boss=}" ;;
    --tape=*)  export KAYA_BOSSGATE_TAPE="${a#--tape=}" ;;
    --sloppy)  SLOPPY=1 ;;
    --tells)   SLOPPY=tells ;;
    --tells=*) SLOPPY=tells; export KAYA_BOSSGATE_PROFILE="${a#--tells=}" ;;
    --sloppy=*) SLOPPY=1; export KAYA_BOSSGATE_PROFILE="${a#--sloppy=}" ;;
    *) echo "bossgate: unknown option '$a'" >&2; exit 2 ;;
  esac
done

run() {
  "$GODOT" --headless --fixed-fps 60 --path . res://tools/bossgate/bossgate.tscn 2>&1 \
    | grep -viE 'Godot Engine v|OpenGL API|^$'
  return "${PIPESTATUS[0]}"
}

if [ "$SLOPPY" = tells ]; then
  KAYA_BOSSGATE_MODE=tells run
  exit $?
fi
if [ "$SLOPPY" = 1 ]; then
  KAYA_BOSSGATE_MODE=sloppy run
  exit $?
fi
if [ "$RECORD" = 1 ]; then
  KAYA_BOSSGATE_MODE=record run || exit 1
fi
run
