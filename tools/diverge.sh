#!/usr/bin/env bash
# Steps the prover's simulation and the real booted game through the same proof
# tape, one frame at a time, and reports the first frame where they part.
# Use when prove.sh says PROVED and the replay tier says the tape does not
# finish the level: exactly one of them is wrong and nothing else can say which.
set -uo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
"$GODOT" --headless --path . res://tools/solver/diverge.tscn -- "$@"
