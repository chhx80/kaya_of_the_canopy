class_name RenderFacingFSM
extends RefCounted
## Phase A of docs/plan-art-motion.md: the turn.
##
## `facing` is gameplay state — form_base.gd's `run_axis()` writes it from the
## input axis the instant the axis changes, because the blade and the
## shouldering code need an immediate answer. This class turns that instant
## flip into something that *reads* as a turn: `render_facing` is the
## direction the sprite actually faces, and it lags `facing` through a short
## animation before snapping to match it.
##
## Pure and argument-driven on purpose. `update()` takes everything it reads
## (facing, horizontal velocity, grounded state, input axis) as parameters and
## writes to nothing but its own fields — never to `facing`, `vel` or any
## physics state — so `tools/test.sh` (no scene tree, no autoloads, ADR 003)
## can drive it from a recorded trace with no Player, no Actor, not even a
## TileWorld. See tests/test_render_facing_fsm.gd.

enum State { NORMAL, TURN, SKID }

## Grounded speed above which a facing flip gets the full 3-frame turn strip
## (plant, half-turn, push-off); below it, or in the air, a flip gets a
## single held half-turn frame instead.
const TURN_SPEED_MIN := 40.0
## Grounded speed above which an input axis that opposes velocity is a skid
## (a held lean-back) rather than the turn strip.
const SKID_SPEED_MIN := 70.0

## 3 frames at 40 fps. Guarded by tests/test_render_facing_fsm.gd to stay
## strictly under data/forms/human.json's coyote_time: the turn must never be
## able to run long enough to imply ground, or a jump window, that the
## physics underneath it has already taken away.
const TURN_FULL_FPS := 40.0
const TURN_FULL_FRAMES := 3
const TURN_FULL_TIME := TURN_FULL_FRAMES / TURN_FULL_FPS
## A single held frame, airborne or slow.
const TURN_HALF_TIME := 0.05

## Phase B, docs/plan-art-motion.md: the bird is the one form where turning
## reads most, and its 2-frame "bank into the new direction" pair does not fit
## the grounded 3-frame strip or the generic single held half-turn — a glide
## banking over 3 frames at 40fps would read as a stumble, not a wing-over.
## `update()`'s `flying` parameter (default false, so every existing call site
## and every recorded trace is untouched) swaps the whole TURN resolution for
## this pair instead. 2 frames at 30fps is still comfortably under the
## shortest coyote_time in the game (bird's own, 0.08s) — see
## tests/test_render_facing_fsm.gd.
const BANK_FPS := 30.0
const BANK_FRAMES := 2
const BANK_TIME := BANK_FRAMES / BANK_FPS

var render_facing := 1
var state: int = State.NORMAL

var _turn_elapsed := 0.0
var _turn_full := false
var _turn_bank := false
var _turn_target := 1          ## the `facing` this turn is resolving towards

func _init(start_facing: int = 1) -> void:
	reset(start_facing)

func reset(start_facing: int) -> void:
	render_facing = start_facing
	state = State.NORMAL
	_turn_elapsed = 0.0
	_turn_full = false
	_turn_bank = false
	_turn_target = start_facing

func _signi(v: float) -> int:
	if v > 0.0:
		return 1
	if v < 0.0:
		return -1
	return 0

## One tick. `axis_x` is -1/0/1, read straight off InputState.axis_x().
## `flying` is new in Phase B (docs/plan-art-motion.md): true for a form whose
## `move_mode` is "fly" (the bird), which always resolves a reversal as the
## 2-frame banking pair instead of the grounded 3-frame strip or the generic
## held half-turn. Defaults to false, so every pre-existing call site (and
## every recorded trace) is bit-identical to before this parameter existed.
func update(delta: float, facing: int, vel_x: float, on_floor: bool, axis_x: float,
		flying: bool = false) -> void:
	var speed := absf(vel_x)
	var vel_sign := _signi(vel_x)
	var axis_sign := _signi(axis_x)
	var opposed := axis_sign != 0 and vel_sign != 0 and axis_sign != vel_sign

	# Skid: the axis is fighting the velocity hard enough that `facing` has
	# already flipped (run_axis() does that on the same tick the axis does)
	# while the body is still travelling the old way. Held until velocity
	# itself crosses zero — not until the axis changes — which is what makes
	# it a lean-back rather than a second kind of turn.
	if on_floor and opposed and speed > SKID_SPEED_MIN:
		state = State.SKID
		render_facing = vel_sign
		_turn_target = facing
		_turn_elapsed = 0.0
		return

	# Already mid-turn: checked BEFORE the "nothing to do" test below, because
	# a mash that flips `facing` back to `render_facing` must still read as a
	# twitch, not silently cancel the strip as if nothing had happened.
	if state == State.TURN:
		if facing != _turn_target:
			# Re-reversed mid-turn. Restart at the half-turn frame (or the
			# bank's first frame, flying) rather than the plant, so mashing
			# the direction keys reads as twitchy, not laggy.
			_turn_bank = flying
			_turn_full = (not flying) and on_floor and speed >= TURN_SPEED_MIN
			_turn_elapsed = _restart_elapsed()
			_turn_target = facing
		_turn_elapsed += delta
		if _turn_elapsed >= _duration():
			render_facing = facing
			state = State.NORMAL
		return

	# Not turning (NORMAL, or a skid that just released): nothing to resolve.
	state = State.NORMAL
	if render_facing == facing:
		_turn_target = facing
		return

	# A fresh mismatch: start a new turn.
	state = State.TURN
	_turn_bank = flying
	_turn_full = (not flying) and on_floor and speed >= TURN_SPEED_MIN
	_turn_target = facing
	_turn_elapsed = delta
	if _turn_elapsed >= _duration():
		render_facing = facing
		state = State.NORMAL

func _restart_elapsed() -> float:
	if _turn_bank:
		return 0.0
	return (TURN_FULL_TIME / TURN_FULL_FRAMES) if _turn_full else 0.0

func _duration() -> float:
	if _turn_bank:
		return BANK_TIME
	return TURN_FULL_TIME if _turn_full else TURN_HALF_TIME

## 0..2 into the 3-frame strip, 0..1 into the 2-frame banking pair (flying),
## or 1 (the half-turn frame) for the single-frame airborne/slow variant. -1
## outside State.TURN.
func turn_frame_index() -> int:
	if state != State.TURN:
		return -1
	if _turn_bank:
		var bi := int(_turn_elapsed / BANK_TIME * BANK_FRAMES)
		return clampi(bi, 0, BANK_FRAMES - 1)
	if not _turn_full:
		return 1
	var idx := int(_turn_elapsed / TURN_FULL_TIME * TURN_FULL_FRAMES)
	return clampi(idx, 0, TURN_FULL_FRAMES - 1)
