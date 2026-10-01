extends TestCase
## Guards Phase A of docs/plan-art-motion.md: the turn.
##
## RenderFacingFSM is deliberately a plain RefCounted that reads its inputs as
## arguments and writes nothing back to them (ADR 003's tier-1 tests have no
## scene tree, no Player, no Actor) — so this drives it the way the real game
## would, one physics tick (1/60 s) at a time, off a recorded trace, and
## asserts the state sequence and the `render_facing` it produces.

const DT := 1.0 / 60.0

# ------------------------------------------------------------------- guard
func test_full_turn_strip_is_shorter_than_coyote_time() -> void:
	## The whole point of lagging render_facing: it must never be able to run
	## long enough to visually imply ground, or a jump window, that the
	## physics underneath it has already taken away.
	var f := FormBase.load_form("human")
	ok(f != null, "human.json must exist")
	lt(RenderFacingFSM.TURN_FULL_TIME, f.coyote_time,
		"the 3-frame turn strip must finish before coyote_time runs out")

func test_half_turn_is_even_shorter() -> void:
	var f := FormBase.load_form("human")
	lt(RenderFacingFSM.TURN_HALF_TIME, f.coyote_time, "the half-turn too")

# ------------------------------------------------------------------- idle
func test_facing_unchanged_never_moves_render_facing() -> void:
	var fsm := RenderFacingFSM.new(1)
	for i in 10:
		fsm.update(DT, 1, 80.0, true, 1.0)
	eq(fsm.render_facing, 1)
	eq(fsm.state, RenderFacingFSM.State.NORMAL)

# ------------------------------------------------------------- grounded turn
func test_grounded_reversal_above_threshold_plays_the_full_strip_then_snaps() -> void:
	## A mid-speed reversal (40-70 px/s: too slow to skid, fast enough for the
	## full strip) must hold the OLD facing through the whole strip and then
	## snap — never drift the sprite's direction a frame early or late.
	var fsm := RenderFacingFSM.new(1)
	# Running right, well below the skid threshold.
	for i in 6:
		fsm.update(DT, 1, 55.0, true, 1.0)
	eq(fsm.render_facing, 1)

	# The axis — and therefore `facing`, which form_base.gd flips on the same
	# tick the axis does — reverses while the body is still moving the old way.
	var ticks := 0
	var saw_turn := false
	while ticks < 20 and fsm.render_facing != -1:
		fsm.update(DT, -1, 55.0, true, -1.0)
		if fsm.state == RenderFacingFSM.State.TURN:
			saw_turn = true
			ok(fsm.turn_frame_index() >= 0 and fsm.turn_frame_index() <= 2,
				"turn_frame_index in range while turning")
			eq(fsm.render_facing, 1, "render_facing holds the OLD direction mid-turn")
		ticks += 1
	ok(saw_turn, "a mid-speed reversal must pass through State.TURN")
	eq(fsm.render_facing, -1, "render_facing eventually snaps to the new facing")
	eq(fsm.state, RenderFacingFSM.State.NORMAL, "and the turn ends")
	lt(float(ticks) * DT, f_coyote(), "the whole strip finished inside coyote_time")

func test_slow_or_airborne_reversal_is_a_single_half_turn() -> void:
	var fsm := RenderFacingFSM.new(1)
	fsm.update(DT, -1, 10.0, true, -1.0)   # below TURN_SPEED_MIN
	eq(fsm.state, RenderFacingFSM.State.TURN)
	eq(fsm.turn_frame_index(), 1, "the half-turn is the strip's middle frame")
	var ticks := 0
	while ticks < 20 and fsm.state == RenderFacingFSM.State.TURN:
		fsm.update(DT, -1, 10.0, true, -1.0)
		ticks += 1
	eq(fsm.render_facing, -1)
	lt(float(ticks) * DT, 0.09, "the half-turn alone must clear coyote_time too")

func test_airborne_reversal_is_a_half_turn_regardless_of_speed() -> void:
	var fsm := RenderFacingFSM.new(1)
	# Fast enough for the full strip on the ground, but airborne here.
	fsm.update(DT, -1, 90.0, false, -1.0)
	eq(fsm.state, RenderFacingFSM.State.TURN)
	eq(fsm.turn_frame_index(), 1)

# ------------------------------------------------------------------- skid
func test_fast_opposed_axis_skids_before_it_turns() -> void:
	## "facing" flips the instant the axis does (run_axis() in form_base.gd),
	## but a body doing 100 px/s cannot actually be facing backwards yet — so
	## while velocity is still fighting the old direction this must read as a
	## held lean-back (SKID), not a turn, and render_facing must NOT move.
	var fsm := RenderFacingFSM.new(1)
	for i in 6:
		fsm.update(DT, 1, 100.0, true, 1.0)
	eq(fsm.render_facing, 1)

	fsm.update(DT, -1, 100.0, true, -1.0)   # axis (and facing) flip; body still at +100
	eq(fsm.state, RenderFacingFSM.State.SKID, "opposed axis above SKID_SPEED_MIN is a skid")
	eq(fsm.render_facing, 1, "render_facing holds the direction the body is still moving")

func test_skid_releases_into_a_turn_once_velocity_crosses_zero() -> void:
	## Chained, as the plan requires: skid -> turn -> run. Velocity decelerates
	## towards the new direction (as accel against an opposed axis would in the
	## real game); the skid must end exactly when it crosses zero, and a turn
	## (to catch `render_facing` up to the `facing` that already flipped) must
	## follow.
	var fsm := RenderFacingFSM.new(1)
	fsm.update(DT, 1, 100.0, true, -1.0)   # already opposed: starts the skid
	eq(fsm.state, RenderFacingFSM.State.SKID)

	var vel := 100.0
	var saw_skid := true
	var saw_turn_or_done := false
	for i in 30:
		vel -= 15.0   # ~900 px/s^2 accel at 60 ticks/s, matches human.json's "accel"
		fsm.update(DT, -1, vel, true, -1.0)
		if fsm.state == RenderFacingFSM.State.SKID:
			eq(fsm.render_facing, 1, "still leaning into the old direction while skidding")
		elif fsm.state == RenderFacingFSM.State.TURN or fsm.render_facing == -1:
			saw_turn_or_done = true
			break
	ok(saw_turn_or_done, "the skid must release once velocity stops opposing the axis")

# ------------------------------------------------------------- re-reversal
func test_mashing_the_direction_restarts_at_the_half_turn_frame() -> void:
	## Re-reversing mid-turn must read as twitchy, not as a second full strip
	## from the top — it restarts AT the half-turn frame, never the plant.
	var fsm := RenderFacingFSM.new(1)
	fsm.update(DT, -1, 55.0, true, -1.0)   # starts a full turn (1 -> -1)
	eq(fsm.state, RenderFacingFSM.State.TURN)
	eq(fsm.turn_frame_index(), 0, "the strip opens on the plant frame")

	fsm.update(DT, 1, 55.0, true, 1.0)     # mashed back to +1 one tick later
	eq(fsm.state, RenderFacingFSM.State.TURN, "still turning — now resolving back to +1")
	eq(fsm.turn_frame_index(), 1,
		"a re-reversal must snap straight to the half-turn frame, not the plant")

func f_coyote() -> float:
	return FormBase.load_form("human").coyote_time
