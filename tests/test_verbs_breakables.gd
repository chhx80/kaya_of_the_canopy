extends TestCase
## Breakable walls: crate-breaking generalised to arbitrary wall tiles.
##
## Two things had to be true before World 4 could be built out of them.
##
## 1. A wall must be breakable by a form that carries no weapon. The frog is
##    half of World 4 and has `can_attack: false`, so a wall only the blade
##    could open would be a wall the frog could not pass.
## 2. Breaking must happen where the Route Prover can see it. The blade is a
##    Node; it does not exist inside `tools/test.sh` and it does not exist
##    inside the prover. A route through a wall that only the blade could open
##    could never be proved, and an unprovable route is the thing ADR 005 exists
##    to abolish.
##
## So the verb lives on the form: hold attack, press into the wall. Everything
## below drives it through `form.update()` against a real TileWorld, with no
## scene tree, no Level and no weapon anywhere.
##
## Tiles, from data/tiles.json: 211 cracked_stone (0.35 s), 213 termite_wall
## (0.45 s), 215 rubble (0.18 s), 10 crate (no break_hold — weapon only).

const TS := 16.0
const DT := 1.0 / 60.0

var data: TileData4

func before_each() -> void:
	data = TileData4.new()
	data.load_from(TileData4.PATH)

func _room(w: int, h: int) -> TileWorld:
	var rows: Array = []
	for y in h:
		var r: Array = []
		for x in w:
			r.append(1 if (y == h - 1 or x == 0 or x == w - 1) else 0)
		rows.append(r)
	return TileWorld.from_rows(rows, data)

func _actor(world: TileWorld, px: float, py: float, form_id: String) -> Array:
	var a := Actor.new()
	a.world = world
	var f := FormBase.load_form(form_id)
	var hb: Dictionary = f.hitbox()
	a.box = Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
	a.pos = Vector2(px, py)
	return [a, f]

func _run(a: Actor, f: FormBase, input: InputState, n: int) -> void:
	for i in n:
		f.update(a, input, DT)
		a.step_motion(DT)
		input.jump_pressed = false
		input.attack_pressed = false

# ------------------------------------------------------------------- the data
func test_the_wall_tiles_are_breakable_and_declare_a_hold() -> void:
	for id in [211, 212, 213, 214, 215]:
		ok(data.flags_of(id) & TileData4.Flag.BREAKABLE != 0,
			"%d (%s) is breakable" % [id, data.name_of(id)])
		ok(data.flags_of(id) & TileData4.Flag.SOLID != 0,
			"%d (%s) is a wall, not scenery" % [id, data.name_of(id)])
		gt(data.break_hold_of(id), 0.0, "%d can be shouldered through" % id)

func test_the_crate_is_untouched_by_the_generalisation() -> void:
	## The regression that matters: crates behaved one way for five levels and
	## must go on behaving that way. No `break_hold`, so no shouldering — the
	## blade is still the only thing that opens one.
	ok(data.flags_of(10) & TileData4.Flag.BREAKABLE != 0, "still breakable")
	eq(data.break_hold_of(10), 0.0, "but not by hand")

func test_a_wall_that_is_not_breakable_is_not_breakable() -> void:
	eq(data.break_hold_of(1), 0.0, "dirt")
	eq(data.break_hold_of(3), 0.0, "stone")
	eq(data.break_hold_of(-1), 0.0, "out of range")

# --------------------------------------------------- outcome: the wall opens
func test_the_frog_digs_through_a_wall_it_has_no_weapon_for() -> void:
	var world := _room(10, 6)
	world.set_fg(5, 4, 213)
	var made := _actor(world, 4.0 * TS + 2.0, 4.0 * TS + 5.0, "frog")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	not_ok(f.can_attack, "the frog carries nothing")
	ok(world.is_solid(5, 4), "the wall is shut to begin with")
	var input := InputState.new()
	input.right = true
	input.attack = true
	input.attack_pressed = true
	_run(a, f, input, 60)                      # 1.0 s against a 0.45 s wall
	not_ok(world.is_solid(5, 4), "the wall is open")
	ok(a.pos.x > 4.0 * TS + 2.0, "and she walks into the space it left")

func test_a_wall_takes_the_time_its_data_says_it_takes() -> void:
	## Outcome, not mechanism: the wall is still shut one tick before the hold
	## elapses and open one tick after. 215 rubble is 0.18 s — 11 ticks.
	var world := _room(10, 6)
	world.set_fg(5, 4, 215)
	# Flush against it from the first tick, so the clock measures the hold and
	# not how long she took to walk over.
	var made := _actor(world, 5.0 * TS - 12.0, 4.0 * TS + 5.0, "frog")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var input := InputState.new()
	input.right = true
	input.attack = true
	_run(a, f, input, 10)
	ok(world.is_solid(5, 4), "still shut after 10 ticks of a 0.18 s wall")
	_run(a, f, input, 2)
	not_ok(world.is_solid(5, 4), "open by the 12th")

func test_letting_go_of_attack_loses_the_progress() -> void:
	var world := _room(10, 6)
	world.set_fg(5, 4, 213)
	var made := _actor(world, 4.0 * TS + 2.0, 4.0 * TS + 5.0, "frog")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var digging := InputState.new()
	digging.right = true
	digging.attack = true
	_run(a, f, digging, 20)
	gt(f.break_progress, 0.0, "part way through")
	var idle := InputState.new()
	idle.right = true
	_run(a, f, idle, 5)
	eq(f.break_progress, 0.0, "released, so the hold starts again")
	_run(a, f, digging, 20)
	ok(world.is_solid(5, 4), "20 more ticks is not enough on its own")

func test_walking_past_a_wall_does_not_dig_it() -> void:
	## `attack` is held for a whole throw of the blade; brushing a wall during
	## one must not quietly dissolve it. Facing decides, and she faces away.
	var world := _room(12, 6)
	world.set_fg(5, 4, 213)
	var made := _actor(world, 6.0 * TS + 1.0, 4.0 * TS + 5.0, "frog")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var input := InputState.new()
	input.right = true
	input.attack = true
	_run(a, f, input, 120)
	ok(world.is_solid(5, 4), "the wall behind her is still there")

func test_up_and_down_dig_a_ceiling_and_a_floor() -> void:
	## Kaya, because at 22 px she is the form whose head reaches a ceiling two
	## tiles up. The verb itself does not care which form is holding it.
	var world := _room(10, 6)
	world.set_fg(4, 5, 211)          # the floor she stands on
	world.set_fg(4, 3, 211)          # the ceiling over her head
	var made := _actor(world, 4.0 * TS + 1.0, 5.0 * TS - 22.0, "human")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var up := InputState.new()
	up.up = true
	up.attack = true
	_run(a, f, up, 40)
	not_ok(world.is_solid(4, 3), "dug the ceiling out")
	var down := InputState.new()
	down.down = true
	down.attack = true
	_run(a, f, down, 40)
	not_ok(world.is_solid(4, 5), "and the floor out from under herself")

func test_the_human_can_shoulder_a_wall_as_well_as_throw_at_it() -> void:
	## The blade still breaks walls — it always broke anything BREAKABLE. This
	## is the other half: the same wall opens to the same verb for every form,
	## so a level does not have to know which one you arrive in.
	var world := _room(10, 6)
	world.set_fg(5, 4, 211)
	world.set_fg(5, 3, 211)
	var made := _actor(world, 4.0 * TS + 2.0, 3.0 * TS + 10.0, "human")
	var a: Actor = made[0]
	var f: FormBase = made[1]
	var input := InputState.new()
	input.right = true
	input.attack = true
	_run(a, f, input, 60)
	not_ok(world.is_solid(5, 4) and world.is_solid(5, 3), "a wall gave way")

# ------------------------------ the constraint: no node, no level, no weapon
func test_breaking_needs_no_scene_tree_no_level_and_no_weapon() -> void:
	var world := _room(10, 6)
	world.set_fg(5, 4, 215)
	var a := Actor.new()
	a.world = world
	a.level = null
	a.box = Vector2(12, 11)
	a.pos = Vector2(4.0 * TS + 2.0, 4.0 * TS + 5.0)
	a.facing = 1
	not_ok(a.is_inside_tree(), "not in a scene tree")
	var f := FormBase.load_form("frog")
	var input := InputState.new()
	input.right = true
	input.attack = true
	for i in 20:
		f.update(a, input, DT)
		a.step_motion(DT)
	not_ok(world.is_solid(5, 4), "the wall opened with nothing but a TileWorld")

func test_a_broken_wall_comes_back_when_the_level_resets() -> void:
	## Dying and retrying has to put the wall back, or a level gets easier every
	## time you fail it and the proved route stops describing what you play.
	var world := _room(10, 6)
	world.set_fg(5, 4, 215)
	var made := _actor(world, 4.0 * TS + 2.0, 4.0 * TS + 5.0, "frog")
	var input := InputState.new()
	input.right = true
	input.attack = true
	_run(made[0] as Actor, made[1] as FormBase, input, 20)
	not_ok(world.is_solid(5, 4), "open")
	world.reset_broken()
	ok(world.is_solid(5, 4), "and shut again on restart")
