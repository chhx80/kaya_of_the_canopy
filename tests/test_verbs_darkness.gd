extends TestCase
## Darkness: a light radius around the player, for World 4.
##
## Half of this file checks that darkness *works*. The other half checks that it
## does **nothing** — and that half is the important one.
##
## The Route Prover plays a level through the real movement code and cannot see.
## If solvability ever depended on what was lit, no World 4 level could be
## proved, and ADR 005's gate would quietly become a lie for a whole world. So
## darkness is two quads drawn over the tiles and under the entities: it never
## reaches a tile flag, the collision, or a form. The tests below hold it to
## that by running the same movement twice — lit and dark — and demanding the
## two agree to the last float.

const DT := 1.0 / 60.0
const TS := 16.0

func after_each() -> void:
	# Static, and `for_level` consults it. Leaving it set would darken every
	# later test in the run.
	Ambience.darkness_override = -1.0

func _dark(alpha: Variant) -> Ambience:
	return Ambience.from_dict("test", {"world": "jungle", "darkness": alpha})

# --------------------------------------------------------------- the defaults
func test_darkness_tunables_live_in_data_not_in_the_script() -> void:
	var d := Ambience.fx_defaults()
	ok(not d.is_empty(), "data/fx.json carries a darkness block")
	gt(float(d.get("radius", 0.0)), 0.0, "with a light radius")
	gt(float(d.get("intensity", 0.0)), 0.0, "and a brightness")
	ok(d.has("ramp") and d.has("step"), "named as a palette ramp step, not an RGB literal")

func test_a_level_says_dark_with_one_number() -> void:
	var a := _dark(0.86)
	near(a.darkness, 0.86, 0.001, "the shade alpha")
	near(a.shade.a, 0.86, 0.001, "carried onto the quad")
	gt(a.lantern_radius, 0.0, "and she is given a light to carry")
	ok(a.has_light(), "so the light layer has something to draw")

func test_a_level_can_override_any_part_of_it() -> void:
	var a := Ambience.from_dict("test", {"darkness": {
		"alpha": 0.5, "radius": 32.0, "intensity": 0.4, "flicker": 0.3, "rate": 2.0}})
	near(a.darkness, 0.5, 0.001)
	near(a.lantern_radius, 32.0, 0.001)
	near(a.lantern.a, 0.4, 0.001)
	near(a.lantern_flicker, 0.3, 0.001)
	near(a.lantern_rate, 2.0, 0.001)

func test_every_level_that_does_not_ask_for_it_stays_lit() -> void:
	## The regression guard for the five shipped levels.
	for id in ["jungle_1", "jungle_2", "jungle_3", "jungle_4", "jungle_5", "test_arena"]:
		var a := Ambience.for_level(id)
		near(a.darkness, 0.0, 0.0001, "%s is not dark" % id)
		near(a.lantern_radius, 0.0, 0.0001, "%s has no lantern" % id)

func test_darkness_is_clamped_and_survives_nonsense() -> void:
	near(_dark(4.0).darkness, 1.0, 0.001, "over one is one")
	near(_dark(-2.0).darkness, 0.0, 0.001, "under zero is zero")
	near(_dark("very").darkness, 0.0, 0.001, "a string leaves the level lit")
	near(Ambience.from_dict("test", {}).darkness, 0.0, 0.001, "and so does silence")

func test_the_shade_colour_comes_off_the_palette() -> void:
	## Same rule as every other ambient colour: a hand-picked RGB multiplied over
	## the whole screen drags the level off the generated palette.
	var a := _dark(0.9)
	var ramp: Array = Ambience.ramps().get("water", [])
	ok(not ramp.is_empty(), "the water ramp exists in assets/palette.json")
	var step: Array = ramp[0]
	near(a.shade.r, float(step[0]) / 255.0, 0.004, "red is a ramp step")
	near(a.shade.g, float(step[1]) / 255.0, 0.004, "green is a ramp step")
	near(a.shade.b, float(step[2]) / 255.0, 0.004, "blue is a ramp step")

func test_the_capture_switch_still_strips_everything() -> void:
	## tools/seq/perf.json measures lighting on against lighting off in one
	## process. A dark level has to go all the way off, or the A/B is not one.
	Ambience.darkness_override = 0.9
	Ambience.lighting = false
	var a := Ambience.for_level("jungle_1")
	Ambience.lighting = true
	near(a.darkness, 0.0, 0.0001, "darkness off with the rest of the lighting")
	near(a.lantern_radius, 0.0, 0.0001, "and the lantern with it")

# ------------------------------------------- the constraint: it changes nothing
func _room_with_a_pit() -> TileWorld:
	var rows: Array = []
	for y in 12:
		var r: Array = []
		for x in 20:
			var v := 0
			if x == 0 or x == 19:
				v = 1
			elif y == 11:
				v = 1
			elif y == 8 and (x < 9 or x > 12):
				v = 1
			r.append(v)
		rows.append(r)
	return TileWorld.from_rows(rows)

## Run a fixed script of inputs and return every position visited.
func _trace(form_id: String) -> Array:
	var world := _room_with_a_pit()
	var a := Actor.new()
	a.world = world
	var f := FormBase.load_form(form_id)
	var hb: Dictionary = f.hitbox()
	a.box = Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
	a.pos = Vector2(2.0 * TS, 6.0 * TS)
	var input := InputState.new()
	var out: Array = []
	for i in 240:
		input.right = i < 150
		input.left = i >= 190
		input.jump = (i % 40) < 6
		input.jump_pressed = (i % 40) == 0
		f.update(a, input, DT)
		a.step_motion(DT)
		out.append(a.pos)
	return out

func test_movement_is_identical_in_the_dark() -> void:
	## The load-bearing test of this file. The same 240 ticks, once with the
	## level lit and once with it as dark as World 4 gets, must land on the same
	## pixel every tick — because the prover will only ever see the lit one.
	for form_id in ["human", "frog", "bird"]:
		Ambience.darkness_override = -1.0
		var lit := _trace(form_id)
		Ambience.darkness_override = 1.0
		var _dark_level := Ambience.for_level("jungle_1")
		ok(_dark_level.darkness > 0.9, "the level really is dark for %s" % form_id)
		var dark := _trace(form_id)
		eq(lit.size(), dark.size(), "same number of ticks")
		var drift := 0.0
		for i in lit.size():
			drift = maxf(drift, (lit[i] as Vector2).distance_to(dark[i] as Vector2))
		near(drift, 0.0, 0.0, "%s moves identically in the dark" % form_id)

func test_darkness_never_becomes_a_tile_flag() -> void:
	## The shape of the mistake this is guarding against: if darkness were ever
	## given a tile to live on, collision would start reading it. Every flag the
	## tile table defines has to be one the prover can evaluate.
	var data := TileData4.new()
	data.load_from(TileData4.PATH)
	var known := TileData4.Flag.SOLID | TileData4.Flag.ONEWAY | TileData4.Flag.LADDER \
		| TileData4.Flag.WATER | TileData4.Flag.HAZARD | TileData4.Flag.BREAKABLE \
		| TileData4.Flag.SURFACE | TileData4.Flag.SWITCHED | TileData4.Flag.CURRENT
	for id in data.count():
		eq(data.flags_of(id) & ~known, 0,
			"tile %d (%s) carries only flags collision understands" % [id, data.name_of(id)])

func test_the_lantern_is_drawn_outside_the_pool_budget() -> void:
	## AmbienceLayer caps pools at MAX_POOLS so a screen of emissive tiles cannot
	## flood the frame. The player's own light must not be inside that cap: being
	## blinded because the room had too many glowing tiles is a softlock made of
	## pixels, and no test could tell it from the level being hard.
	var src := FileAccess.get_file_as_string("res://src/world/ambience_layer.gd")
	var draw_at := src.find("func _draw_lantern")
	gt(float(draw_at), 0.0, "the lantern has its own draw")
	var body := src.substr(draw_at, src.find("func _draw(") - draw_at)
	not_ok(body.contains("_visible"), "and does not go through the capped list")
