extends TestCase
## Currents and updrafts, driven through the *shipping* movement code.
##
## Every case here builds a TileWorld, an Actor and a real FormBase and runs
## `form.update()` + `actor.step_motion()` — the same two calls `Player` makes
## and the same two the Route Prover makes. Nothing is modelled. There is no
## scene tree, no Level, no Node in the loop at all, which is the point: a
## current that only existed inside the booted game would let the prover prove a
## level that does not exist (docs/adr/005-proving-levels-playable.md).
##
## Tile ids under test, from data/tiles.json:
##   200 water_current_right [68, 0]   204 water_current_right_fast [120, 0]
##   201 water_current_left [-68, 0]   206 updraft [0, -400]
##   206/207/208 are dry air; the 20x ids are water.

const TS := 16.0
const DT := 1.0 / 60.0

var data: TileData4

func before_each() -> void:
	data = TileData4.new()
	data.load_from(TileData4.PATH)

# ------------------------------------------------------------------ fixtures
## A room `w` x `h` tiles with a solid floor and solid side walls.
func _room(w: int, h: int) -> TileWorld:
	var rows: Array = []
	for y in h:
		var r: Array = []
		for x in w:
			r.append(1 if (y == h - 1 or x == 0 or x == w - 1) else 0)
		rows.append(r)
	return TileWorld.from_rows(rows, data)

func _fill(world: TileWorld, x0: int, y0: int, x1: int, y1: int, id: int) -> void:
	for y in range(y0, y1 + 1):
		for x in range(x0, x1 + 1):
			world.set_fg(x, y, id)

func _actor(world: TileWorld, tx: float, ty: float, form_id: String) -> Array:
	var a := Actor.new()
	a.world = world
	var f := FormBase.load_form(form_id)
	var hb: Dictionary = f.hitbox()
	a.box = Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
	a.pos = Vector2(tx * TS, ty * TS)
	return [a, f]

## Run the real loop for `n` ticks and hand back the actor.
func _run(a: Actor, f: FormBase, input: InputState, n: int) -> void:
	for i in n:
		f.update(a, input, DT)
		a.step_motion(DT)
		input.jump_pressed = false
		input.attack_pressed = false

func _still() -> InputState:
	return InputState.new()

# -------------------------------------------------------------- the data itself
func test_the_verb_tiles_declare_the_currents_the_worlds_need() -> void:
	ok(data.has_currents, "data/tiles.json declares at least one current")
	eq(data.current_of(200), Vector2(68, 0), "200 pushes right")
	eq(data.current_of(201), Vector2(-68, 0), "201 pushes left")
	eq(data.current_of(206), Vector2(0, -400), "206 is an updraft")
	eq(data.current_of(208), Vector2(0, 170), "208 is a downdraft")
	ok(data.flags_of(200) & TileData4.Flag.CURRENT != 0, "200 carries the flag")
	ok(data.flags_of(200) & TileData4.Flag.WATER != 0, "200 is still water")
	ok(data.flags_of(206) & TileData4.Flag.WATER == 0, "an updraft is air, not water")

func test_a_current_and_an_updraft_are_the_same_mechanism() -> void:
	## The whole requirement in one assertion: World 2's push and World 3's lift
	## come out of the same field on the same tile record, differing only in
	## which axis the author put the number on.
	for id in [200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210]:
		ok(data.flags_of(id) & TileData4.Flag.CURRENT != 0,
			"tile %d (%s) carries CURRENT" % [id, data.name_of(id)])
		ne(data.current_of(id), Vector2.ZERO, "tile %d has a velocity" % id)
	var horizontal := 0
	var vertical := 0
	for id in [200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210]:
		if is_zero_approx(data.current_of(id).y):
			horizontal += 1
		if is_zero_approx(data.current_of(id).x):
			vertical += 1
	gt(float(horizontal), 0.0, "some are configured horizontally")
	gt(float(vertical), 0.0, "some are configured vertically")

func test_a_tile_without_a_current_has_none() -> void:
	eq(data.current_of(8), Vector2.ZERO, "plain water does not push")
	eq(data.current_of(1), Vector2.ZERO, "dirt does not push")
	eq(data.current_of(-1), Vector2.ZERO, "out of range is still zero")
	eq(data.current_of(99999), Vector2.ZERO, "past the table is still zero")

# --------------------------------------------------------------- sampling
func test_sampling_is_weighted_by_how_far_into_the_current_you_are() -> void:
	## A step function on a tile edge would make the push depend on which side of
	## one pixel the hitbox sat. Six pixels is what cost this project a level.
	var world := _room(10, 6)
	_fill(world, 5, 0, 9, 4, 200)
	# A 16-wide box exactly straddling the boundary at x = 80: half in.
	var half := FormBase.current_at(world, Rect2(72, 32, 16, 16))
	near(half.x, 34.0, 0.01, "half inside is half the push")
	var all_in := FormBase.current_at(world, Rect2(80, 32, 16, 16))
	near(all_in.x, 68.0, 0.01, "fully inside is the full push")
	var out := FormBase.current_at(world, Rect2(48, 32, 16, 16))
	near(out.x, 0.0, 0.01, "outside is no push")

func test_opposed_currents_cancel_where_they_meet() -> void:
	var world := _room(10, 6)
	_fill(world, 4, 2, 4, 2, 200)
	_fill(world, 5, 2, 5, 2, 201)
	var c := FormBase.current_at(world, Rect2(4 * TS, 2 * TS, 32, 16))
	near(c.x, 0.0, 0.01, "equal and opposite over the two tiles")

func test_a_level_with_no_currents_costs_nothing_to_sample() -> void:
	var plain := TileData4.new()
	plain.load_from_dict({"tiles": {"0": {"name": "empty"}, "1": {"name": "dirt", "solid": true}}})
	not_ok(plain.has_currents, "a table with no current tile says so")
	var world := TileWorld.from_rows([[1, 1], [0, 0]], plain)
	eq(FormBase.current_at(world, Rect2(0, 0, 16, 16)), Vector2.ZERO)

# ------------------------------------------------- outcome: the actor moves
func test_a_still_fish_is_carried_downstream_by_a_water_current() -> void:
	var world := _room(20, 8)
	_fill(world, 1, 1, 18, 6, 200)
	var made := _actor(world, 3, 3, "fish")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var x0 := a.pos.x
	_run(a, f, _still(), 60)
	ne(a.vel.x, 0.0, "the current changed the fish's velocity")
	near(a.vel.x, 68.0, 1.0, "carried at the speed of the water")
	gt(a.pos.x - x0, 50.0, "and actually moved downstream in one second")

func test_a_fish_swims_upstream_slowly_but_does_get_there() -> void:
	## World 2's tension: 92 px/s of swim against 68 px/s of water is 24 px/s of
	## headway. If this ever reads <= 0 the world is a wall, not a level.
	var world := _room(30, 8)
	_fill(world, 1, 1, 28, 6, 200)
	var made := _actor(world, 20, 3, "fish")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var x0 := a.pos.x
	var input := _still()
	input.left = true
	_run(a, f, input, 60)
	lt(a.vel.x, 0.0, "making headway against the push")
	near(a.vel.x, -24.0, 1.0, "own 92 minus the water's 68")
	lt(a.pos.x, x0 - 15.0, "a whole second buys about a tile")

func test_the_fast_current_is_a_one_way_gate() -> void:
	## 120 px/s beats the fish's 92: swimming into it still loses ground. That is
	## the difference between the two data configurations, and a level may rely
	## on it, so it is asserted rather than assumed.
	var world := _room(30, 8)
	_fill(world, 1, 1, 28, 6, 204)
	var made := _actor(world, 20, 3, "fish")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var x0 := a.pos.x
	var input := _still()
	input.left = true
	_run(a, f, input, 60)
	gt(a.vel.x, 0.0, "still swept downstream while swimming upstream")
	gt(a.pos.x, x0, "lost ground")

func test_a_current_does_not_slow_you_down_when_you_swim_with_it() -> void:
	var world := _room(30, 8)
	_fill(world, 1, 1, 28, 6, 200)
	var still_water := _room(30, 8)
	_fill(still_water, 1, 1, 28, 6, 8)
	var pushed := _actor(world, 3, 3, "fish")
	var plain := _actor(still_water, 3, 3, "fish")
	var input := _still()
	input.right = true
	_run(pushed[0] as Actor, pushed[1] as FormBase, input, 40)
	var input2 := _still()
	input2.right = true
	_run(plain[0] as Actor, plain[1] as FormBase, input2, 40)
	gt((pushed[0] as Actor).vel.x, (plain[0] as Actor).vel.x + 50.0,
		"downstream is the fish's own speed plus the water's, not a cap")

# --------------------------------------------------------------- updrafts
func test_an_updraft_turns_a_falling_human_into_a_rising_one() -> void:
	var world := _room(12, 20)
	_fill(world, 1, 1, 10, 17, 206)
	var made := _actor(world, 5, 14, "human")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var y0 := a.pos.y
	_run(a, f, _still(), 90)
	lt(a.vel.y, 0.0, "the updraft changed the sign of her velocity")
	near(a.vel.y, -70.0, 2.0, "330 px/s of terminal fall minus 400 of lift")
	lt(a.pos.y, y0 - 40.0, "and she is higher up than she started")

func test_an_updraft_lifts_every_form_by_the_same_rule() -> void:
	for form_id in ["human", "frog", "bird"]:
		var world := _room(12, 20)
		_fill(world, 1, 1, 10, 17, 206)
		var made := _actor(world, 5, 14, form_id)
		var a: Actor = made[0]
		var f: FormBase = made[1]
		var y0 := a.pos.y
		_run(a, f, _still(), 90)
		lt(a.pos.y, y0, "%s rises in an updraft" % form_id)

func test_an_updraft_column_holds_you_at_its_lip() -> void:
	## What a rider actually experiences, measured rather than assumed. Because
	## the push is area-weighted, the lift tapers as the hitbox leaves the top of
	## the column, and you settle where the remaining lift exactly cancels
	## gravity — head clear of the lip, hovering, not launched.
	##
	## Level authors need this number: a landing at the top of a draught has to
	## be reachable from the hover, not from an imagined launch.
	var world := _room(12, 26)
	_fill(world, 4, 10, 7, 24, 206)
	var made := _actor(world, 5, 22, "human")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	_run(a, f, _still(), 300)
	var lip := 10.0 * TS
	lt(a.pos.y, lip, "her head is above the top of the column")
	gt(a.pos.y + a.box.y, lip, "her feet are still inside it")
	near(a.vel.y, 0.0, 6.0, "and she has settled, not oscillated")
	# Stable: another two seconds does not move her.
	var settled := a.pos.y
	_run(a, f, _still(), 120)
	near(a.pos.y, settled, 1.0, "the hover holds")

func test_you_leave_the_top_of_an_updraft_by_steering_out_of_it() -> void:
	## The escape from that hover, because a draught you cannot get out of is a
	## softlock and the prover only finds an exit if one exists.
	##
	## Note what is *not* here: she cannot jump out. She is airborne the whole
	## time she hovers, so there is no coyote time and no jump. Steering sideways
	## is the exit for a walking form; the bird has one more (below).
	var world := _room(12, 26)
	_fill(world, 4, 10, 7, 24, 206)
	var made := _actor(world, 5, 22, "human")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	_run(a, f, _still(), 300)
	not_ok(a.on_floor, "hovering, so nothing to jump off")
	var input := _still()
	input.right = true
	_run(a, f, input, 60)
	gt(a.pos.x, 8.0 * TS, "she steers sideways out of the column")
	eq(FormBase.current_at(world, a.aabb()), Vector2.ZERO, "and is clear of it")

func test_the_bird_can_flap_out_of_the_top_of_an_updraft() -> void:
	## World 3's promise — "updrafts are the only way to regain height" — only
	## holds if the bird can convert the ride into height it keeps.
	var world := _room(12, 26)
	_fill(world, 4, 14, 7, 24, 206)
	var made := _actor(world, 5, 22, "bird")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	_run(a, f, _still(), 180)
	var hover := a.pos.y
	var input := _still()
	input.jump = true
	input.jump_pressed = true
	_run(a, f, input, 24)
	lt(a.pos.y, hover - 16.0, "a flap from the hover carries it a tile clear")
	lt(a.pos.y + a.box.y, 14.0 * TS, "fully above the column it rode up")

func test_a_downdraft_pins_you_down() -> void:
	var world := _room(12, 20)
	_fill(world, 1, 1, 10, 17, 208)
	var plain := _room(12, 20)
	var pushed := _actor(world, 5, 3, "bird")
	var free := _actor(plain, 5, 3, "bird")
	_run(pushed[0] as Actor, pushed[1] as FormBase, _still(), 60)
	_run(free[0] as Actor, free[1] as FormBase, _still(), 60)
	gt((pushed[0] as Actor).vel.y, (free[0] as Actor).vel.y + 100.0,
		"a downdraft drags a bird down harder than gravity alone")

func test_a_gust_shifts_where_running_gets_you() -> void:
	var world := _room(40, 8)
	_fill(world, 1, 1, 38, 6, 209)
	var made := _actor(world, 20, 5, "human")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var input := _still()
	input.left = true
	# Short: at 900 px/s^2 the run reaches its target in a fifth of a second, and
	# a long run would only measure the distance to the left wall.
	_run(a, f, input, 20)
	near(a.vel.x, -28.0, 2.0, "108 px/s of run into an 80 px/s gust")

# --------------------------------------- the constraint, stated as a test
func test_currents_need_no_scene_tree_no_level_and_no_player() -> void:
	## This is the architectural guarantee written down. If a current ever moves
	## into a Node, this test is what stops it: an Actor with `level == null`,
	## outside any tree, driven by the same two calls the prover makes, must
	## still be pushed.
	var world := _room(20, 8)
	_fill(world, 1, 1, 18, 6, 200)
	var a := Actor.new()
	a.world = world
	a.level = null
	a.box = Vector2(10, 22)
	a.pos = Vector2(3 * TS, 3 * TS)
	not_ok(a.is_inside_tree(), "the actor is not in a scene tree")
	eq(a.get_parent(), null, "and has no parent")
	var f := FormBase.load_form("human")
	var before := a.vel
	f.update(a, InputState.new(), DT)
	a.step_motion(DT)
	ne(a.vel.x, before.x, "velocity changed with nothing but a TileWorld present")
	gt(a.vel.x, 0.0, "and changed in the direction the tile declares")

func test_the_current_is_visible_on_the_form_the_prover_holds() -> void:
	## The prover reads back state to score a search node. `form.current` is the
	## medium it is moving through and has to be readable without a Player.
	var world := _room(12, 20)
	_fill(world, 1, 1, 10, 17, 207)
	var made := _actor(world, 5, 10, "frog")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	f.update(a, InputState.new(), DT)
	near(f.current.y, -560.0, 0.01, "the strong updraft, read off the form")
	near(f.current.x, 0.0, 0.01)

# ---------------------------------------------------- no current, no change
func test_a_level_without_currents_moves_exactly_as_it_did_before() -> void:
	## The regression guard. Every existing level has no current tile, and the
	## arcs tests/test_player_forms.gd measures must not have moved by a pixel.
	var world := _room(16, 12)
	var made := _actor(world, 5, 9, "frog")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	_run(a, f, _still(), 30)               # land and settle
	ok(a.on_floor, "on the ground before the jump")
	var floor_y := a.pos.y
	var input := _still()
	input.jump = true                       # held, so no jump-cut shortens it
	input.jump_pressed = true
	var apex := a.pos.y
	for i in 150:
		f.update(a, input, DT)
		a.step_motion(DT)
		input.jump_pressed = false
		apex = minf(apex, a.pos.y)
	var tiles := (floor_y - apex) / TS
	# 5.3385 is the number ADR 005 was written around — the *real* apex, not the
	# 5.16 the old model predicted. Pinned to two thousandths of a tile, because
	# a defect in this project once turned on six pixels.
	near(tiles, 5.3385, 0.002, "the frog's apex, measured at %f tiles" % tiles)
