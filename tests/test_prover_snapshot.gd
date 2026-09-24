extends TestCase
## The prover's own state, and the rule that `restore()` restores.
##
## This file exists because of the quietest bug this project has found. The
## prover searches by snapshot/restore, and `_reset_form()` used to put back only
## the properties one function had touched -- while `form.update()` writes
## `coyote`, `buffer` and `_drop_timer` every tick and marked nothing. `restore()`
## was called faithfully every time. The state did not come back. So the search
## explored from bodies carrying phantom coyote time and found jumps real play
## cannot make: the proof was real, the tape recording it was not.
##
## The lesson was that checking the MECHANISM (restore was called) is not
## checking the OUTCOME (the state is actually back). So nothing below inspects
## a field to see whether somebody remembered to copy it. Every test here takes
## a running simulation, saves it, disturbs it, restores it, and then asks the
## simulation itself whether the future it produces is the same one -- which is
## the only property the search actually depends on.

const A := preload("res://tools/solver/search.gd")

## Long enough for a full jump arc plus a landing, so coyote, the jump buffer,
## the landing timer and the airborne-velocity memory are all mid-flight when the
## snapshot is taken.
const SPAN := 40


# ------------------------------------------------------------------ fixtures

## A flat room with a vine up the middle, a ledge and a pool: enough geometry for
## every form to be somewhere interesting. Built here rather than read from
## `tests/fixtures/`, because a test that fails when a shared fixture is retuned
## is a test about the fixture.
func _level() -> LevelLoader.LevelDef:
	var fg := [
		"ssssssssssssssssssss",
		"s..................s",
		"s.....|............s",
		"s.....|......####..s",
		"s.....|............s",
		"s.....|............s",
		"s.....|.....wwwwww.s",
		"s...........wwwwww.s",
		"ssssssssssssssssssss",
	]
	var bg: Array = []
	for _y in fg.size():
		bg.append("....................")
	return LevelLoader.from_dict({
		"id": "prover_snapshot_room",
		"name": "SNAPSHOT ROOM",
		"topdown": false,
		"fg": fg,
		"bg": bg,
		"entities": [
			{"type": "player_spawn", "x": 2, "y": 7},
			{"type": "pad_frog", "x": 9, "y": 7},
			{"type": "key_cyan", "x": 4, "y": 7},
		],
	})


## A floor, a two-tile step with a gem on it, and a frog pad under the step.
##
## Every part of that is load-bearing, and it was measured rather than guessed.
## The step means getting to the gem needs a jump, so a hop that begins here
## either reads a press or does not. The pad is what makes the difference SURVIVE:
## without it, both tapes converge -- a wrong first macro costs a few pixels and
## the next jump lands on the same platform anyway, and the run ends in the same
## place (measured: (169, 74) both ways). With the pad, a phantom jump on the first
## macro changes whether the body crosses the pad, and a frog is not a human.
## That is also the shape of jungle_3's failure: the join was on a transform pad.
func _step_room() -> LevelLoader.LevelDef:
	var fg := [
		"ssssssssssssssssssss",
		"s..................s",
		"s.....|............s",
		"s.....|............s",
		"s.....|............s",
		"s.....|............s",
		"s.....|..#####.....s",
		"s..................s",
		"ssssssssssssssssssss",
	]
	var bg: Array = []
	for _y in fg.size():
		bg.append("....................")
	return LevelLoader.from_dict({
		"id": "prover_step_room",
		"name": "STEP ROOM",
		"topdown": false,
		"fg": fg,
		"bg": bg,
		"entities": [
			{"type": "player_spawn", "x": 2, "y": 7},
			{"type": "gem", "x": 11, "y": 5},
			{"type": "pad_frog", "x": 9, "y": 7},
		],
	})


func _sim_of(def: LevelLoader.LevelDef) -> ProverSim:
	var sim := ProverSim.new()
	sim.setup(def)
	var neutral := InputState.new()
	# The game gives a level four frames to build before a tape's first button
	# lands, and Kaya falls the last few pixels onto the floor in them.
	for _i in 4:
		sim.step(neutral)
	return sim


func _sim() -> ProverSim:
	return _sim_of(_level())


## One frame of input, with the press/release edges a continuous tape produces.
func _input(a: int, prev: int) -> InputState:
	var inp := InputState.new()
	inp.left = (a & A.LEFT) != 0
	inp.right = (a & A.RIGHT) != 0
	inp.up = (a & A.UP) != 0
	inp.down = (a & A.DOWN) != 0
	inp.jump = (a & A.JUMP) != 0
	inp.jump_pressed = inp.jump and (prev & A.JUMP) == 0
	inp.jump_released = (prev & A.JUMP) != 0 and not inp.jump
	inp.attack = (a & A.ATTACK) != 0
	inp.attack_pressed = inp.attack and (prev & A.ATTACK) == 0
	inp._prev_jump = (prev & A.JUMP) != 0
	inp._prev_attack = (prev & A.ATTACK) != 0
	return inp


## Run a per-frame action list and return the whole trajectory, so a comparison
## can fail on the frame it first went wrong instead of only at the end.
func _play(sim: ProverSim, acts: PackedInt32Array, prev: int) -> Array:
	var out: Array = []
	var p := prev
	for a: int in acts:
		sim.step(_input(a, p))
		p = a
		out.append(sim.replay_signature())
	return out


func _trail(actions: Array) -> PackedInt32Array:
	var out := PackedInt32Array()
	for a: int in actions:
		out.append(int(a))
	return out


# ------------------------------------------- restore() puts the future back

## The property the search depends on, stated as the search uses it: restore a
## state and the same buttons must produce the same frames, to the pixel.
##
## Run twice from one snapshot, with a long detour in between. If anything at all
## is left behind by `restore()` -- a timer, a flag, a tile -- the second run
## diverges from the first, and this fails without needing to know which field it
## was. That is the point: the bug this guards against was a field nobody had
## thought of.
func _assert_future_is_restorable(sim: ProverSim, warmup: PackedInt32Array,
		tail: PackedInt32Array, detour: PackedInt32Array, what: String) -> void:
	var prev := 0
	for a: int in warmup:
		sim.step(_input(a, prev))
		prev = a

	var saved := sim.snapshot()
	var first := _play(sim, tail, prev)

	sim.restore(saved)
	# The detour is what makes this a test and not a tautology: it leaves the
	# simulation as far from `saved` as it can, so a restore with a hole in it has
	# something wrong to leak.
	var _junk := _play(sim, detour, prev)

	sim.restore(saved)
	var second := _play(sim, tail, prev)

	eq(first.size(), second.size(), "%s: both runs are %d frames" % [what, tail.size()])
	for i in mini(first.size(), second.size()):
		var f: Dictionary = first[i]
		var g: Dictionary = second[i]
		if f != g:
			ok(false, "%s: frame %d differs after restore -- first %s, second %s"
				% [what, i, str(f), str(g)])
			return
	ok(true, "%s: %d frames reproduce exactly after restore" % [what, tail.size()])


func test_restore_reproduces_a_running_jump_frame_for_frame() -> void:
	var run := A.RIGHT
	var leap := A.RIGHT | A.JUMP
	var warmup := _trail([run, run, run, run, run, run, leap, leap])
	var tail := PackedInt32Array()
	for i in SPAN:
		tail.append(leap if i < 8 else run)
	var detour := PackedInt32Array()
	for i in SPAN:
		detour.append(A.LEFT | A.JUMP if i % 5 == 0 else A.LEFT)
	_assert_future_is_restorable(_sim(), warmup, tail, detour, "a running jump")


## The original bug's exact shape: coyote time and the jump buffer are written
## every tick by `form.update()`, so a body that has just left the ground is the
## state most likely to leak. Snapshot mid-air, detour through a landing, restore.
func test_restore_does_not_leave_phantom_coyote_time_behind() -> void:
	var warmup := _trail([A.RIGHT, A.RIGHT, A.RIGHT, A.RIGHT | A.JUMP,
		A.RIGHT | A.JUMP, A.RIGHT | A.JUMP, A.RIGHT, A.RIGHT])
	# A late jump: if the restored body still carries coyote from the detour's
	# landing, this press buys a jump the first run never had.
	var tail := PackedInt32Array()
	for i in SPAN:
		tail.append(A.RIGHT | A.JUMP if i >= 6 and i < 14 else A.RIGHT)
	var detour := PackedInt32Array()
	for _i in SPAN:
		detour.append(0)          # stand still, land, sit on the floor accruing coyote
	_assert_future_is_restorable(_sim(), warmup, tail, detour, "a mid-air body")


func test_restore_reproduces_a_vine_climb() -> void:
	# Walk to the vine column, then climb. The climb writes `climbing` and snaps
	# the x position, which is state the search restores hundreds of times a hop.
	var warmup := PackedInt32Array()
	for _i in 30:
		warmup.append(A.RIGHT)
	var tail := PackedInt32Array()
	for i in SPAN:
		tail.append(A.UP if i < 30 else A.UP | A.JUMP)
	var detour := PackedInt32Array()
	for _i in SPAN:
		detour.append(A.DOWN)
	_assert_future_is_restorable(_sim(), warmup, tail, detour, "a vine climb")


func test_restore_puts_a_transform_pad_and_its_cooldown_back() -> void:
	# Walking right reaches pad_frog, which changes the form, the hitbox and the
	# pad's cooldown. Restoring across a transform has to undo all three.
	var warmup := PackedInt32Array()
	for _i in 70:
		warmup.append(A.RIGHT)
	var tail := PackedInt32Array()
	for i in SPAN:
		tail.append(A.LEFT | A.JUMP if i % 7 == 0 else A.LEFT)
	var detour := PackedInt32Array()
	for _i in SPAN:
		detour.append(A.RIGHT)
	_assert_future_is_restorable(_sim(), warmup, tail, detour, "a form change")


## Not the same claim as the ones above: this one says the snapshot is enough to
## rebuild the state from a DIFFERENT one, not merely from itself. The search
## restores sibling states in any order, so a snapshot that only round-trips
## against its own immediate past is not enough.
func test_a_snapshot_restores_the_same_way_from_any_other_state() -> void:
	var sim := _sim()
	var prev := 0
	for _i in 20:
		sim.step(_input(A.RIGHT, prev))
		prev = A.RIGHT
	var saved := sim.snapshot()
	var direct := sim.describe_state()

	# Somewhere else entirely: a different form, a key in hand, mid-climb.
	var far := _sim()
	var p2 := 0
	for _i in 80:
		far.step(_input(A.RIGHT, p2))
		p2 = A.RIGHT
	for _i in 20:
		far.step(_input(A.UP, p2))
		p2 = A.UP
	far.restore(saved)
	var rebuilt := far.describe_state()

	for k: String in direct.keys():
		eq(rebuilt.get(k), direct[k],
			"restore rebuilt '%s' as %s, not %s" % [k, str(rebuilt.get(k)), str(direct[k])])



# ------------------------------------------------ the hop boundary is a join

## A tape is one continuous stream of presses, so the first frame of hop N+1
## follows the last frame of hop N with no gap for a thumb to lift in. The search
## used to root every hop at "no button held", which let it read a rising edge the
## replay could never see: a body standing on the floor with jump already down
## got a free jump from the search's first macro, and got nothing at all from the
## replay's. On jungle_3 that is exactly what happened -- hop 7 ended holding
## jump, hop 8 began on the transform pad, and the search left the body at
## (727, 105) where the same buttons replayed to (743, 164).
##
## Asserted as the outcome: search a hop whose goal can only be reached by
## jumping, from a body that is already holding jump, then replay the actions the
## search returned with jump held going in. Rooting the search at zero fails this
## -- measured in this room, the zero-rooted tape opens with "right+jump", leaves
## the search at (166, 85) and replays to (194, 74).
func test_a_hop_that_begins_with_jump_already_held_reproduces() -> void:
	var sim := _sim_of(_step_room())
	var held := _land_holding_jump(sim)
	eq(held, A.JUMP, "the join is reached with jump held and nothing else")
	ok(sim.actor.on_floor, "and with both feet on the floor")

	var start := sim.snapshot()
	var goals := sim.waypoint_indices("gem")
	gt(float(goals.size()), 0.0, "the room has a gem on the step to aim at")

	var res: ProverSearch.Result = ProverSearch.new().run(sim, start, goals, 20000, held)
	ok(res.found, "the search gets onto the step: %s" % res.reason)
	if not res.found:
		return
	sim.restore(res.end_state)
	var want := sim.replay_signature()

	# A fresh simulation, the same arrival, then the tape and nothing else.
	var fresh := _sim_of(_step_room())
	var p := _land_holding_jump(fresh)
	var trail := _play(fresh, res.actions, p)
	gt(float(trail.size()), 0.0, "the hop recorded some frames")
	var got: Dictionary = trail[trail.size() - 1]
	eq(got["pos"], want["pos"],
		"the tape replayed to %s; the search left the body at %s"
		% [str(got["pos"]), str(want["pos"])])
	eq(got["vel"], want["vel"], "and with the same velocity")
	eq(got["on_floor"], want["on_floor"], "and standing, or not, the same way")

	# And the other half: rooted at "nothing held", the same search in the same
	# room produces a tape that does NOT reproduce. Without this the test above
	# could be passing because the room is too forgiving to tell the difference --
	# which is what a first draft of it did, on a room with no step in it.
	var blind: ProverSearch.Result = ProverSearch.new().run(
		_sim_of(_step_room()), start, goals, 20000, 0)
	ok(blind.found, "the zero-rooted search also finds a way: %s" % blind.reason)
	if not blind.found:
		return
	var check := _sim_of(_step_room())
	var cp := _land_holding_jump(check)
	var ctrail := _play(check, blind.actions, cp)
	var cgot: Dictionary = ctrail[ctrail.size() - 1]
	var csim := _sim_of(_step_room())
	_land_holding_jump(csim)
	csim.restore(blind.end_state)
	var cwant := csim.replay_signature()
	ne(cgot["pos"], cwant["pos"],
		("a search rooted at 'no button held' must NOT reproduce here -- it does, "
		+ "so this room no longer exercises the bug and the test above proves nothing"))


## Settle, press jump once, and hold it until the body is standing still again --
## so the join is reached with the button already down and its rising edge spent.
## Returns the action held on the last frame, which is what the next hop inherits.
##
## "Standing" means on_floor AND not still falling. `Actor.step_motion()` can set
## on_floor from its closing one-way probe on a frame where vel.y is still the
## full fall speed, so waiting only for on_floor lands on a body that is about to
## be moved again, and every measurement after it is of the wrong frame.
func _land_holding_jump(sim: ProverSim) -> int:
	var prev := 0
	for _i in 20:
		sim.step(_input(0, prev))
		prev = 0
	sim.step(_input(A.JUMP, prev))
	prev = A.JUMP
	var frames := 0
	while frames < 300 and not (sim.actor.on_floor and is_zero_approx(sim.actor.vel.y)):
		sim.step(_input(A.JUMP, prev))
		prev = A.JUMP
		frames += 1
	return prev


## The other half of the same claim, and the one that says the edge is really
## being read: with jump already down, the search cannot spend a rising edge on
## its first macro, because `can_jump_now()` needs the buffer that only
## `jump_pressed` fills. So a first action of "jump" must be a jump that does
## nothing -- and the body must still be falling, not rising.
func test_jump_held_across_a_join_cannot_buy_a_fresh_jump() -> void:
	var sim := _sim()
	_land_holding_jump(sim)
	ok(sim.actor.on_floor, "the body is standing on the floor with jump still held")

	# A whole macro of held jump, exactly as a search rooted at `held` would drive
	# it. Nothing may launch.
	var saved := sim.snapshot()
	for _i in ProverSearch.MACRO:
		sim.step(_input(A.JUMP, A.JUMP))
	ok(sim.actor.vel.y >= 0.0,
		"a held jump must not launch: vel.y is %.1f" % sim.actor.vel.y)
	ok(sim.actor.on_floor, "and the body is still on the floor")

	# Releasing and pressing again is how a real hop has to do it, and that does
	# launch -- so the assertion above is about the edge, not about a broken jump.
	sim.restore(saved)
	sim.step(_input(0, A.JUMP))
	sim.step(_input(A.JUMP, 0))
	lt(sim.actor.vel.y, 0.0, "released and pressed again, the jump fires")


# --------------------------------------------- nothing mutable is overlooked

## A classification, not a copy check. Every variable `Actor` declares is either
## carried by snapshot/restore or named here as one the movement path never reads.
## Adding a variable to `src/world/actor.gd` therefore fails this test until
## somebody decides which it is -- which is the step that was skipped when
## `form.update()`'s timers were left out of the form restore.
const ACTOR_VARS_RESTORED := ["pos", "vel", "box", "on_floor", "was_on_floor",
	"on_ceiling", "against_wall", "facing", "drop_through",
	"last_floor_tile", "last_wall_tile"]

## Set by whoever builds the simulation and never by a tick, so they are not
## per-state at all.
const ACTOR_VARS_NOT_STATE := ["world", "level"]

func test_every_variable_actor_declares_is_classified() -> void:
	var a := Actor.new()
	var seen: Array[String] = []
	for p: Dictionary in a.get_property_list():
		if int(p.get("usage", 0)) & PROPERTY_USAGE_SCRIPT_VARIABLE:
			seen.append(String(p["name"]))
	for name: String in seen:
		ok(ACTOR_VARS_RESTORED.has(name) or ACTOR_VARS_NOT_STATE.has(name),
			("Actor.%s is new and unclassified. If a tick can write it, the prover's "
			+ "snapshot must carry it; if not, add it to ACTOR_VARS_NOT_STATE and say why. "
			+ "Leaving it out is how the search found jumps real play cannot make.") % name)
	for name: String in ACTOR_VARS_RESTORED:
		ok(seen.has(name), "Actor.%s is gone; this list is stale" % name)


## The same rule for the forms. The prover derives the form's state by reflection
## precisely so a new per-tick variable is captured without anyone remembering to
## come here -- so this asserts the reflection actually sees the timers that
## caused the original bug, rather than listing what to copy.
func test_the_form_snapshot_sees_the_timers_that_caused_the_original_bug() -> void:
	var sim := _sim()
	var props: Array = sim._form_props["human"]
	var names: Array[String] = []
	for n: StringName in props:
		names.append(String(n))
	for want: String in ["coyote", "buffer", "climbing", "_drop_timer", "_land_t", "_air_vy",
			"current", "break_progress", "_break_target"]:
		ok(names.has(want),
			"the form snapshot no longer sees '%s'; that is the bug, verbatim" % want)
