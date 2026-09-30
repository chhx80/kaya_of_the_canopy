extends TestCase
## Tileset probes: the smallest artefact that proves a world's art and data are
## actually wired to each other.
##
## Why this file exists. ADR 002 amended gives every world its own legend, so a
## level says `"tileset": "heights"` and the same twelve role characters bind to
## World 3's tile ids instead of the jungle's. Everything about that arrangement
## fails quietly:
##
##   * a role a tileset forgets to bind falls out as an unknown character, but
##     only in a level that happens to use it;
##   * a role bound to the wrong id loads, plays and renders — as the wrong
##     material, or worse, as a jungle understudy nobody notices in a
##     screenshot (see MEMORY: "world_kit ruins palette emits wrong stone");
##   * a shared verb tile that a world's levels lean on — the updraft is what
##     World 3 is *for* — carries its velocity in data/tiles.json, not in the
##     level, so a level round-trip that dropped it would look like a level
##     bug in five different levels at once.
##
## So each world gets one probe fixture under tests/fixtures/: one screen, built
## from that world's tiles, using every role character the world defines. It is
## in tests/fixtures/ and not in levels/ so LevelLoader.list_levels() never sees
## it — a probe is not a level and must never be something the hub's
## requires_all door waits on.
##
## The probes are also playable by hand:
##   tools/prove.sh --level-file=res://tests/fixtures/heights_probe.json
##
## Registering a new world's probe is one line in PROBES.

## fixture basename -> the tileset it claims. Add a line per world.
const PROBES := {
	"ruins_probe": "ruins",
	"heights_probe": "heights",
	"deeps_probe": "deeps",
	"nest_probe": "nest",
}

## The twelve role characters every tileset binds (data/level_legend.json
## "_comment_roles"). A probe that does not use all of them is not proof of the
## tileset, only of the corner of it the probe happens to touch.
const ROLES := ["#", "S", "d", "s", "=", "|", "^", "c", "L", "T", "r", "X"]

## Probes that claim to place every role. `ruins_probe` predates this file — it
## was authored as the smallest thing tools/prove.sh could *play* through a
## non-jungle legend, and it touches four of the twelve. It is left exactly as it
## was rather than widened, because the tape it backs is evidence about World 2
## and retuning a fixture to satisfy a later test throws that evidence away.
const FULL_COVERAGE := ["heights_probe", "deeps_probe", "nest_probe"]

const DIR := "res://tests/fixtures/"

var data: TileData4

func before_each() -> void:
	data = TileData4.new()
	data.load_from(TileData4.PATH)
	# Static, and the deeps section reads `Ambience.for_level`. Another file in the
	# suite forces darkness on to test it; an escaped override would darken the
	# probe and make this file fail for somebody else's reason.
	Ambience.darkness_override = -1.0
	Ambience.lighting = true

func _path(name: String) -> String:
	return DIR + name + ".json"

func _raw(name: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(_path(name)))
	return parsed as Dictionary if parsed is Dictionary else {}

func _load(name: String) -> LevelLoader.LevelDef:
	return LevelLoader.load_path(_path(name), name)

## Every character used in either layer of a probe.
func _chars_used(name: String) -> Dictionary:
	var seen: Dictionary = {}
	var raw := _raw(name)
	for layer: String in ["fg", "bg"]:
		for row: Variant in (raw.get(layer, []) as Array):
			var s := String(row)
			for i in s.length():
				seen[s[i]] = true
	return seen

# ---------------------------------------------------------------- registration
func test_every_registered_probe_exists_on_disk() -> void:
	gt(float(PROBES.size()), 1.0, "at least two worlds are probed")
	for name: String in PROBES.keys():
		ok(FileAccess.file_exists(_path(name)),
			"probe fixture %s is missing" % _path(name))

func test_no_probe_is_also_a_level() -> void:
	## A probe in levels/ would be a level the hub waits on forever.
	var levels := LevelLoader.list_levels()
	for name: String in PROBES.keys():
		not_ok(levels.has(name), "%s must not be in levels/" % name)

func test_every_probe_declares_the_tileset_it_is_registered_under() -> void:
	for name: String in PROBES.keys():
		eq(String(_raw(name).get("tileset", "")), String(PROBES[name]),
			"%s declares its tileset out loud" % name)

# ------------------------------------------------------------------ the load
func test_every_probe_loads_with_no_errors() -> void:
	## The check the whole file is built on. An unmapped character makes
	## LevelLoader hand back a null world rather than a grid of empty space.
	for name: String in PROBES.keys():
		var def := _load(name)
		ok(def.ok(), "%s: %s" % [name, ", ".join(def.errors)])
		ok(def.world != null, "%s produced a world" % name)
		eq(def.tileset, String(PROBES[name]), "%s read against its own legend" % name)

func test_a_full_coverage_probe_places_every_role_its_tileset_defines() -> void:
	for name: String in FULL_COVERAGE:
		has(PROBES.keys(), name, "%s is in FULL_COVERAGE but not registered" % name)
		var lg := LevelLoader.legend_for(String(PROBES.get(name, "")))
		var used := _chars_used(name)
		for role: String in ROLES:
			ok(lg.has(role), "tileset '%s' leaves role '%s' unbound" % [PROBES.get(name, ""), role])
			ok(used.has(role),
				"%s never places role '%s' — the probe does not prove that binding" % [name, role])

func test_every_probe_places_at_least_the_ground_of_its_world() -> void:
	## The floor of what a probe has to be, for the ones outside FULL_COVERAGE.
	for name: String in PROBES.keys():
		var used := _chars_used(name)
		ok(used.has("#"), "%s places no ground cap" % name)
		ok(used.has("d"), "%s places no fill under the cap" % name)

func test_every_probe_tile_comes_from_its_own_world_or_the_shared_set() -> void:
	## The "jungle understudy" check, at the data level: a probe that resolved
	## to jungle ids would load, play and render, and only a human looking at
	## the screenshot would ever know.
	var doc := LevelLoader.legend_doc()
	var shared: Dictionary = doc.get("shared", {})
	for name: String in PROBES.keys():
		var world_name := String(PROBES[name])
		var own: Dictionary = (doc.get("tilesets", {}) as Dictionary).get(world_name, {})
		var allowed: Dictionary = {}
		for ch: String in shared.keys():
			allowed[int(shared[ch])] = true
		for ch: String in own.keys():
			allowed[int(own[ch])] = true
		var def := _load(name)
		if def.world == null:
			continue
		for y in def.world.height:
			for x in def.world.width:
				for id: int in [def.world.get_fg(x, y), def.world.get_bg(x, y)]:
					ok(allowed.has(id),
						"%s (%d,%d) holds tile %d (%s), which is neither a '%s' tile nor shared"
							% [name, x, y, id, data.name_of(id), world_name])

# ------------------------------------------------------------ the heights probe
## The rest of the file is World 3 specific, because the point of a probe is to
## assert the exact ids, not "some solid tile somewhere".
const HEIGHTS := "heights_probe"

## role character -> the id data/level_legend.json binds it to for "heights".
const HEIGHTS_IDS := {
	"#": 240, "S": 241, "d": 243, "s": 249, "=": 246, "|": 248,
	"^": 247, "c": 251, "L": 242, "T": 245, "r": 250, "X": 244,
}

func test_the_heights_legend_binds_the_ids_thermal_heights_art_was_painted_for() -> void:
	var lg := LevelLoader.legend_for("heights")
	ok(not lg.is_empty(), "data/level_legend.json defines a 'heights' tileset")
	for ch: String in HEIGHTS_IDS.keys():
		eq(int(lg.get(ch, -1)), int(HEIGHTS_IDS[ch]),
			"heights '%s' must bind tile %d" % [ch, int(HEIGHTS_IDS[ch])])
	for ch: String in HEIGHTS_IDS.keys():
		var id := int(HEIGHTS_IDS[ch])
		ok(id >= 240 and id <= 251,
			"heights role '%s' points at %d, outside the 240-251 block" % [ch, id])

func test_the_heights_tiles_carry_the_flags_their_roles_promise() -> void:
	## Sanity at the data level: the twelve roles mean the same thing in every
	## world, so the flags have to line up with the jungle's.
	var f := TileData4.Flag
	ok(data.flags_of(240) & f.SOLID != 0, "240 heights_rock is solid")
	ok(data.flags_of(241) & f.SOLID != 0, "241 heights_rock_sun is solid")
	ok(data.flags_of(243) & f.SOLID != 0, "243 heights_scree is solid")
	ok(data.flags_of(249) & f.SOLID != 0, "249 heights_basalt is solid")
	ok(data.flags_of(246) & f.ONEWAY != 0, "246 heights_plank is one-way")
	ok(data.flags_of(246) & f.SOLID == 0, "246 heights_plank is not solid")
	ok(data.flags_of(248) & f.LADDER != 0, "248 heights_chain is climbable")
	ok(data.flags_of(248) & f.SOLID == 0, "248 heights_chain is not solid")
	ok(data.flags_of(247) & f.HAZARD != 0, "247 heights_vent hurts")
	ok(data.flags_of(251) & f.BREAKABLE != 0, "251 heights_shell breaks")
	ok(data.flags_of(251) & f.SOLID != 0, "251 heights_shell is solid until it does")
	for id: int in [242, 244, 245, 250]:
		eq(data.flags_of(id), 0,
			"%d (%s) is a background tile and must carry no flags" % [id, data.name_of(id)])
	for id: int in HEIGHTS_IDS.values():
		ok(data.flags_of(id) & f.WATER == 0,
			"%d (%s) — nothing in Thermal Heights is water" % [id, data.name_of(id)])

func test_the_heights_probe_grid_answers_those_flags_through_a_real_tileworld() -> void:
	## Flags on ids prove the table; this proves the *level* — the grid the
	## loader built from the probe's characters answers collision correctly at
	## the coordinates the fixture authored.
	var def := _load(HEIGHTS)
	ok(def.ok(), "heights probe loads: %s" % ", ".join(def.errors))
	if def.world == null:
		return
	var w := def.world
	eq(w.width, 25, "the probe is one screen wide")
	eq(w.height, 15, "the probe is one screen tall")
	ok(w.is_solid(0, 13), "the ground cap is solid")
	eq(w.get_fg(0, 13), 240, "the ground cap is heights_rock")
	ok(w.is_solid(0, 14), "the fill under the cap is solid")
	eq(w.get_fg(0, 14), 243, "the fill is heights_scree")
	eq(w.get_fg(3, 10), 241, "the sunlit ledge is heights_rock_sun")
	ok(w.is_solid(3, 10), "and it is solid")
	eq(w.get_fg(17, 8), 249, "the high ledge is heights_basalt")
	ok(w.is_solid(17, 8), "and it is solid")
	ok(w.is_oneway(14, 10), "the plank is one-way")
	not_ok(w.is_solid(14, 10), "and not solid")
	ok(w.is_ladder(20, 10), "the chain climbs")
	ok(w.is_hazard(22, 12), "the vent is a hazard")
	ok(w.is_breakable(4, 10), "the shell breaks")
	not_ok(w.is_solid(1, 12), "the walkable floor level is open")
	# Background tiles are decoration only: nothing in bg may affect collision.
	eq(w.get_bg(0, 0), 250, "the sky band is heights_cloud")
	eq(w.get_bg(0, 9), 242, "the wall behind the shaft is heights_wall")
	eq(w.get_bg(1, 5), 245, "the far stacks are heights_stack")
	eq(w.get_bg(0, 13), 244, "under the floor is heights_air")
	not_ok(w.is_solid(0, 0), "a bg cloud is not something you stand on")

func test_the_updraft_vectors_survive_a_level_round_trip() -> void:
	## The verb World 3 is built on. The velocity lives in data/tiles.json and
	## the level only names the character, so this is the one thing a level
	## cannot state for itself — and if it were lost, five levels would break
	## at once with nothing pointing at the cause.
	eq(data.current_of(206), Vector2(0, -400), "206 updraft lifts 400 px/s")
	eq(data.current_of(207), Vector2(0, -560), "207 updraft_strong lifts 560 px/s")
	var lg := LevelLoader.legend_for("heights")
	eq(int(lg.get("U", -1)), 206, "'U' is the updraft")
	eq(int(lg.get("*", -1)), 207, "'*' is the strong updraft")
	var def := _load(HEIGHTS)
	if def.world == null:
		return
	var w := def.world
	# The fixture stands a vent on the floor at (23,12) and stacks 'U' above it
	# with '*' on top, so the column is one shaft of rising air that gets
	# stronger the higher it goes.
	ok(w.is_hazard(23, 12), "the shaft rises out of a vent")
	for y in range(8, 12):
		eq(w.get_fg(23, y), 206, "the shaft at (23,%d) is an updraft" % y)
		eq(w.data.current_of(w.get_fg(23, y)), Vector2(0, -400),
			"(23,%d) still lifts after the round trip" % y)
	for y in range(5, 8):
		eq(w.get_fg(23, y), 207, "the shaft at (23,%d) is a strong updraft" % y)
		eq(w.data.current_of(w.get_fg(23, y)), Vector2(0, -560),
			"(23,%d) still lifts hard after the round trip" % y)
	ok(w.data.has_currents, "the world knows it has currents at all")
	ok(w.flags_at(23, 9) & TileData4.Flag.CURRENT != 0, "the shaft carries the CURRENT flag")
	ok(w.flags_at(23, 9) & TileData4.Flag.WATER == 0, "an updraft is air, not water")
	not_ok(w.is_solid(23, 9), "and you can be inside it")

func test_the_shipping_movement_code_finds_the_lift_in_the_probe() -> void:
	## Not the table and not the grid: the same static call the player and the
	## Route Prover make, on the probe's own world, at the probe's own marks.
	## `current_at` weights by overlap, so a hitbox standing in the shaft gets
	## the full push and one standing beside it gets none.
	var def := _load(HEIGHTS)
	if def.world == null:
		return
	var ts := float(TileData4.TILE_SIZE)
	var inside := Rect2(23.0 * ts + 3.0, 9.0 * ts, 10.0, 16.0)
	var lift := FormBase.current_at(def.world, inside)
	lt(lift.y, -300.0, "a hitbox in the shaft is lifted, hard (got %.1f)" % lift.y)
	near(lift.x, 0.0, 0.001, "and not pushed sideways")
	var beside := Rect2(2.0 * ts + 3.0, 9.0 * ts, 10.0, 16.0)
	eq(FormBase.current_at(def.world, beside), Vector2.ZERO,
		"open air away from the shaft is still")
	var high := Rect2(23.0 * ts + 3.0, 6.0 * ts, 10.0, 16.0)
	lt(FormBase.current_at(def.world, high).y, lift.y,
		"the top of the shaft lifts harder than the bottom")

# -------------------------------------------------------------- the deeps probe
## World 4 specific, and it carries the VERB CONTRACT the five TERMITE DEEPS
## level authors build on. Every number below is measured — by this file, by
## tests/test_verbs_breakables.gd, or by tools/prove.sh — and not reasoned.
const DEEPS := "deeps_probe"

## role character -> the id data/level_legend.json binds it to for "deeps".
const DEEPS_IDS := {
	"#": 260, "S": 261, "d": 263, "s": 271, "=": 266, "|": 268,
	"^": 267, "c": 270, "L": 262, "T": 265, "r": 269, "X": 264,
}

## The five shared walls that can be opened *by hand*, and the seconds of
## shouldering each one takes (data/tiles.json). These are World 4's verb the way
## the updraft is World 3's: the hold lives in the tile table, the level only
## names the character, so no level can state it for itself.
const SHOULDER_HOLDS := {
	211: 0.35,   # 'k' cracked_stone
	212: 0.25,   # 'j' cracked_dirt
	213: 0.45,   # 'm' termite_wall
	214: 0.40,   # 'O' luminous_wall
	215: 0.18,   # 'o' rubble
}

## MEASURED ticks at 60 Hz for a body already flush against the wall, from the
## first frame `attack` is held. Not ceil(hold * 60): `break_progress` is a sum of
## sixty separate additions of 1/60, so 0.25 s lands on 16 ticks and not 15, and
## 0.40 s on 25 and not 24. An author timing a chase around one of these walls
## needs the number play actually produces.
const SHOULDER_TICKS := {215: 11, 212: 16, 211: 21, 214: 25, 213: 27}

const DT := 1.0 / 60.0

func test_the_deeps_legend_binds_the_ids_termite_deeps_art_was_painted_for() -> void:
	var lg := LevelLoader.legend_for("deeps")
	ok(not lg.is_empty(), "data/level_legend.json defines a 'deeps' tileset")
	for ch: String in DEEPS_IDS.keys():
		eq(int(lg.get(ch, -1)), int(DEEPS_IDS[ch]),
			"deeps '%s' must bind tile %d" % [ch, int(DEEPS_IDS[ch])])
		var id := int(DEEPS_IDS[ch])
		ok(id >= 260 and id <= 271,
			"deeps role '%s' points at %d, outside the 260-271 block" % [ch, id])

func test_the_deeps_tiles_carry_the_flags_their_roles_promise() -> void:
	## The twelve roles mean the same thing in every world, so the flags have to
	## line up with the jungle's and the heights'.
	var f := TileData4.Flag
	ok(data.flags_of(260) & f.SOLID != 0, "260 deep_earth is solid")
	ok(data.flags_of(261) & f.SOLID != 0, "261 deep_crust is solid")
	ok(data.flags_of(263) & f.SOLID != 0, "263 deep_chitin is solid")
	ok(data.flags_of(271) & f.SOLID != 0, "271 deep_packed is solid")
	ok(data.flags_of(266) & f.ONEWAY != 0, "266 deep_shelf is one-way")
	ok(data.flags_of(266) & f.SOLID == 0, "266 deep_shelf is not solid")
	ok(data.flags_of(268) & f.LADDER != 0, "268 deep_ladder is climbable")
	ok(data.flags_of(268) & f.SOLID == 0, "268 deep_ladder is not solid")
	ok(data.flags_of(267) & f.HAZARD != 0, "267 deep_spore hurts")
	ok(data.flags_of(270) & f.BREAKABLE != 0, "270 deep_glowwall breaks")
	ok(data.flags_of(270) & f.SOLID != 0, "270 deep_glowwall is solid until it does")
	for id: int in [262, 264, 265, 269]:
		eq(data.flags_of(id), 0,
			"%d (%s) is a background tile and must carry no flags" % [id, data.name_of(id)])
	for id: int in DEEPS_IDS.values():
		ok(data.flags_of(id) & f.WATER == 0,
			"%d (%s) — nothing in the deeps block is water" % [id, data.name_of(id)])

func test_the_deeps_probe_grid_answers_those_flags_through_a_real_tileworld() -> void:
	## Flags on ids prove the table; this proves the *level* — the grid the loader
	## built from the probe's characters answers collision correctly at the
	## coordinates the fixture authored.
	var def := _load(DEEPS)
	ok(def.ok(), "deeps probe loads: %s" % ", ".join(def.errors))
	if def.world == null:
		return
	var w := def.world
	eq(w.width, 25, "the probe is one screen wide")
	eq(w.height, 15, "the probe is one screen tall")
	ok(w.is_solid(0, 13), "the ground cap is solid")
	eq(w.get_fg(0, 13), 260, "the ground cap is deep_earth")
	ok(w.is_solid(0, 14), "the fill under the cap is solid")
	eq(w.get_fg(0, 14), 263, "the fill is deep_chitin")
	eq(w.get_fg(3, 10), 261, "the overhead ledge is deep_crust")
	ok(w.is_solid(3, 10), "and it is solid")
	eq(w.get_fg(17, 8), 271, "the high ledge is deep_packed")
	ok(w.is_solid(17, 8), "and it is solid")
	ok(w.is_oneway(14, 10), "the shelf is one-way")
	not_ok(w.is_solid(14, 10), "and not solid")
	ok(w.is_ladder(20, 10), "the ladder climbs")
	ok(w.is_hazard(21, 12), "the spore vent is a hazard")
	ok(w.is_breakable(4, 10), "the glowwall breaks")
	not_ok(w.is_solid(1, 12), "the walkable floor level is open")
	not_ok(w.is_solid(23, 12), "and so is the tile a body braces from")
	# Background tiles are decoration only: nothing in bg may affect collision.
	eq(w.get_bg(0, 0), 269, "the ceiling crust is deep_fungus")
	eq(w.get_bg(0, 2), 262, "the wall behind the tunnel is deep_comb")
	eq(w.get_bg(1, 5), 265, "the hanging columns are deep_root")
	eq(w.get_bg(0, 13), 264, "under the floor is deep_void")
	not_ok(w.is_solid(0, 0), "a bg fungus crust is not something you stand on")

# ------------------------------------- VERB CONTRACT 1: the shoulder-break wall
func test_the_break_holds_survive_a_level_round_trip() -> void:
	## The World 4 twin of `test_the_updraft_vectors_survive_a_level_round_trip`.
	## The hold lives in data/tiles.json and the level only names the character; if
	## it were lost, five levels would break at once with nothing pointing at the
	## cause.
	var shared: Dictionary = LevelLoader.legend_doc().get("shared", {})
	var chars := {211: "k", 212: "j", 213: "m", 214: "O", 215: "o"}
	for id: int in SHOULDER_HOLDS.keys():
		near(data.break_hold_of(id), float(SHOULDER_HOLDS[id]), 0.0001,
			"%d (%s) is shouldered through in %.2f s"
				% [id, data.name_of(id), float(SHOULDER_HOLDS[id])])
		eq(int(shared.get(String(chars[id]), -1)), id,
			"'%s' is the shared character for %d" % [chars[id], id])
	# The plug in the probe's last column, hardest at the top.
	var def := _load(DEEPS)
	if def.world == null:
		return
	var w := def.world
	var plug := {8: 213, 9: 214, 10: 211, 11: 212, 12: 215}
	for y: int in plug.keys():
		var id: int = plug[y]
		eq(w.get_fg(24, y), id, "the plug at (24,%d) is %s" % [y, data.name_of(id)])
		ok(w.is_breakable(24, y), "(24,%d) is breakable after the round trip" % y)
		ok(w.is_solid(24, y), "(24,%d) is a wall until it is opened" % y)
		near(w.data.break_hold_of(w.get_fg(24, y)), float(SHOULDER_HOLDS[id]), 0.0001,
			"(24,%d) still takes %.2f s after the round trip" % [y, SHOULDER_HOLDS[id]])

func test_the_deeps_c_role_is_blade_only_and_that_is_a_trap_for_authors() -> void:
	## The one thing about World 4's legend an author will get wrong. 'c' resolves
	## to 270 deep_glowwall, which is BREAKABLE but declares no `break_hold` — so
	## it behaves exactly like the jungle crate: the blade opens it and nothing
	## else does. The frog and the bird have `can_attack: false`, so a 'c' on a
	## mandatory path is a wall to half the forms in the game.
	## Write 'O' (214 luminous_wall, 0.40 s) for a wall every form can open.
	ok(data.flags_of(270) & TileData4.Flag.BREAKABLE != 0, "270 is breakable")
	eq(data.break_hold_of(270), 0.0, "but carries no hold, so not by hand")
	eq(data.break_hold_of(10), 0.0, "the same way the crate always has")
	gt(data.break_hold_of(214), 0.0, "214 luminous_wall is the shoulderable twin")
	var lg := LevelLoader.legend_for("deeps")
	eq(int(lg.get("c", -1)), 270, "'c' is the blade-only one")
	eq(int((LevelLoader.legend_doc().get("shared", {}) as Dictionary).get("O", -1)), 214,
		"'O' is the one any form opens")

func test_the_shipping_break_code_opens_the_probes_own_wall() -> void:
	## Not the table and not the grid: `FormBase.tick_break()` — the same code the
	## player and the Route Prover run — against the probe's own TileWorld, with a
	## frog braced on the probe's own ground cap. The frog because it carries no
	## weapon: if this passes, no wall in World 4 needs the blade.
	var def := _load(DEEPS)
	if def.world == null:
		return
	var w := def.world
	var ts := float(TileData4.TILE_SIZE)
	var f := FormBase.load_form("frog")
	not_ok(f.can_attack, "the frog carries nothing")
	var hb: Dictionary = f.hitbox()
	var a := Actor.new()
	a.world = w
	a.box = Vector2(float(hb.get("w", 12)), float(hb.get("h", 11)))
	# Flush against the plug at x=24, feet on the ground cap at row 13.
	a.pos = Vector2(24.0 * ts - a.box.x, 13.0 * ts - a.box.y)
	a.facing = 1
	ok(w.is_solid(24, 12), "the rubble plug is shut to begin with")
	var input := InputState.new()
	input.right = true
	input.attack = true
	var ticks := 0
	for i in 60:
		f.update(a, input, DT)
		a.step_motion(DT)
		input.attack_pressed = false
		if not w.is_solid(24, 12):
			ticks = i + 1
			break
	eq(ticks, int(SHOULDER_TICKS[215]),
		"0.18 s of rubble opens on tick %d" % int(SHOULDER_TICKS[215]))
	w.reset_broken()
	ok(w.is_solid(24, 12), "and a retry puts it back")

func test_every_form_opens_every_shoulder_wall_in_the_same_number_of_ticks() -> void:
	## The other half of the contract, and the thing a level author plans around:
	## the hold is a property of the WALL, not of the body leaning on it. Measured
	## for all four forms against all five walls — twenty runs of the shipping
	## `FormBase.tick_break()` — so "which form is faster at digging" is answered
	## once and is "none of them".
	##
	## The numbers are in SHOULDER_TICKS and they are not ceil(hold * 60): the
	## progress clock is a sum of separate 1/60 additions, so 0.25 s lands on 16
	## ticks and 0.40 s on 25.
	var ts := float(TileData4.TILE_SIZE)
	for form_id: String in ["human", "frog", "bird", "fish"]:
		for id: int in SHOULDER_TICKS.keys():
			var rows: Array = []
			for y in 6:
				var r: Array = []
				for x in 10:
					r.append(1 if (y == 5 or x == 0 or x == 9) else 0)
				rows.append(r)
			var world := TileWorld.from_rows(rows, data)
			world.set_fg(5, 4, id)
			var f := FormBase.load_form(form_id)
			var hb: Dictionary = f.hitbox()
			var a := Actor.new()
			a.world = world
			a.box = Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
			# Flush against the wall from the first tick, so the clock measures the
			# hold and not how long the body took to walk over.
			a.pos = Vector2(5.0 * ts - a.box.x, 5.0 * ts - a.box.y)
			a.facing = 1
			var input := InputState.new()
			input.right = true
			input.attack = true
			var ticks := 0
			for i in 60:
				f.update(a, input, DT)
				a.step_motion(DT)
				input.attack_pressed = false
				if not world.is_solid(5, 4):
					ticks = i + 1
					break
			eq(ticks, int(SHOULDER_TICKS[id]),
				"%s opens %d (%s, %.2f s) on tick %d"
					% [form_id, id, data.name_of(id), float(SHOULDER_HOLDS[id]),
					   int(SHOULDER_TICKS[id])])

func test_the_prover_cannot_break_a_wall_so_no_route_may_need_one() -> void:
	## THE constraint on every World 4 level. Two independent reasons, both read
	## off the shipping prover rather than argued:
	##
	##   1. `ProverSearch.action_set()` is {left,none,right} x {jump,no jump} x
	##      {none,up,down} — eighteen actions, and ATTACK is in none of them. The
	##      search literally cannot hold the button the verb needs.
	##   2. `ProverSim.snapshot()` does not carry `TileWorld._broken`. Even with
	##      attack in the alphabet, a tile opened down one branch would stay open
	##      for every sibling branch, and the search would prove routes that play
	##      cannot reproduce.
	##
	## MEASURED with tools/prove.sh on two 20x8 deeps corridors that differ only by
	## one column of 'o' rubble — the CHEAPEST wall there is, 0.18 s:
	##   open corridor .... PROVED, 1 hop, 143 frames, 36 expansions, exit 0
	##   plugged .......... FAIL, closest approach 102.0 px, 50,000 expansions
	##                      spent (budget exhausted), exit 1
	## So the cost of a break hop is not "more expensive than a walk hop", it is
	## unbounded: 36 expansions against the whole budget, for one tile of the
	## softest wall in the game. Route around it.
	var acts := ProverSearch.action_set()
	eq(acts.size(), 18, "the prover's alphabet is eighteen actions wide")
	for a: int in acts:
		eq(a & ProverSearch.ATTACK, 0,
			"action %s must not hold attack" % ProverSearch.action_name(a))

func test_no_breakable_in_the_probe_stands_between_two_waypoints() -> void:
	## The rule above, applied to this fixture, so the probe stays provable if
	## anyone edits it. Every breakable is strictly right of the ladder the route
	## climbs, or above the walk line, and the route never names a mark inside one.
	var raw := _raw(DEEPS)
	var marks: Dictionary = raw.get("marks", {})
	var def := _load(DEEPS)
	if def.world == null:
		return
	var w := def.world
	for name: String in marks.keys():
		var m: Dictionary = marks[name]
		not_ok(w.is_breakable(int(m.get("x", 0)), int(m.get("y", 0))),
			"mark '%s' sits inside a breakable the prover cannot open" % name)
	# The walk line the first hop uses: spawn (2,12) to ladder_foot (20,12).
	for x in range(2, 21):
		not_ok(w.is_breakable(x, 12),
			"(%d,12) is on the walked line and breakable" % x)
		not_ok(w.is_hazard(x, 12),
			"(%d,12) is on the walked line and a hazard" % x)
	# And the spore field is what keeps the search out of the plug's corner.
	ok(w.is_hazard(21, 12) and w.is_hazard(22, 12),
		"the plug is sealed behind a hazard, not left open to wander into")

# ------------------------------------------------ VERB CONTRACT 2: the darkness
## THE RECIPE AN AUTHOR COPIES for a dark World 4 level. It goes in
## data/ambience.json under the level's own id — `levels/*.json` is geometry only
## — and the shortest form that works is one number: `"darkness": 0.88`, which
## picks up every default in data/fx.json (shade water/step 0, lantern radius
## 74 px, gold/step 5 at intensity 0.8, flicker 0.08 at 1.6 Hz).
##
## The full entry, measured at 400x240 and captured in shots/m4_verbs_darkness.png:
##
##   "deeps_1": {
##     "world": "deeps",
##     "air":     { "ramp": "water", "step": 1, "alpha": 0.30 },
##     "bg_tint": { "ramp": "water", "step": 3, "mix": 0.85, "scale": 0.46 },
##     "fg_tint": { "ramp": "metal", "step": 6, "mix": 0.30, "scale": 0.82 },
##     "vignette": 0.40,
##     "darkness": 0.88,
##     "emissive": {
##       "214": { "ramp": "gold",  "step": 6, "intensity": 0.40, "radius": 30, "lift": 0 },
##       "267": { "ramp": "grass", "step": 5, "intensity": 0.30, "radius": 26, "lift": 5 }
##     }
##   }
##
## Notes that cost something to find:
##   * `darkness` is a shade quad over the tiles plus one additive pool on Kaya.
##     Because it is drawn UNDER the entities, she and the enemies keep full
##     contrast — a dark level raises the figure/ground contrast rather than
##     lowering it. Do not also crush `fg_tint`: 0.82 is as low as the tiles can
##     go and still read inside the lantern.
##   * EMISSIVE TILES ARE HOW A LEVEL LIGHTS ITSELF. `"emissive": {"<tile id>": …}`
##     puts a pool on every one of those tiles and AmbienceLayer._add_run() merges
##     a horizontal run into ONE wide lozenge, so a wall of glowing tiles costs a
##     few quads and not a hundred. That is the mechanism the SPORE LIGHT level
##     wants: make the glowing material a tile id, list the id here, and the
##     lighting follows the geometry with no authored pool at all. `lift` raises
##     the pool off the tile centre (use it for a surface); `lift: 0` centres it
##     (use it for a wall).
##   * GOTCHA, measured: `AmbienceLayer._collect_emissive()` scans `get_fg()` ONLY.
##     A glowing tile listed here must be in the FOREGROUND layer. 269 deep_fungus
##     is lovely and is the obvious thing to reach for, but this probe uses it as
##     background dressing and a bg tile emits nothing — the entry is silently
##     ignored. 267 deep_spore is the World 4 material that is both a hazard and
##     a light, which is the SPORE LIGHT level in one line.
##   * 214 luminous_wall is the obvious one to make emissive: a wall that glows
##     AND is the wall every form can shoulder through, so the light is the
##     signpost for the verb.
##   * Authored `lights` still work and are absolute tile coordinates; prefer
##     `emissive` when the light belongs to a material.
##   * A pool cap of AmbienceLayer.MAX_POOLS = 16 applies to `lights` + emissive.
##     The lantern is drawn outside it on purpose, so a room full of glowing tiles
##     can never blind the player.
##   * `tools/shot.sh --darkness=0.9` forces any level dark without editing data.
const DARK_RECIPE := {
	"world": "deeps",
	"air": {"ramp": "water", "step": 1, "alpha": 0.30},
	"bg_tint": {"ramp": "water", "step": 3, "mix": 0.85, "scale": 0.46},
	"fg_tint": {"ramp": "metal", "step": 6, "mix": 0.30, "scale": 0.82},
	"vignette": 0.40,
	"darkness": 0.88,
	"emissive": {
		"214": {"ramp": "gold", "step": 6, "intensity": 0.40, "radius": 30, "lift": 0},
		"267": {"ramp": "grass", "step": 5, "intensity": 0.30, "radius": 26, "lift": 5},
	},
}

func test_the_dark_recipe_an_author_copies_actually_loads() -> void:
	## The recipe above is quoted in a comment, which rots. This runs it.
	var a := Ambience.from_dict("deeps_probe", DARK_RECIPE)
	near(a.darkness, 0.88, 0.001, "the level is dark")
	gt(a.lantern_radius, 0.0, "and Kaya carries a light")
	ok(a.has_light(), "so the light layer has something to draw")
	eq(a.world, "deeps", "over the deeps backdrop")
	gt(a.vignette, 0.0, "with the walls closing in")
	# Emissive tiles are keyed by tile id, and both are tiles this probe places.
	ok(a.emissive.has(214), "214 luminous_wall glows")
	ok(a.emissive.has(267), "267 deep_spore glows")
	gt(float((a.emissive[214] as Dictionary)["radius"]), 0.0, "with a radius")
	# The one-liner short form has to keep working too.
	var b := Ambience.from_dict("deeps_probe", {"darkness": 0.88})
	near(b.darkness, 0.88, 0.001, "one number is a dark level")
	near(b.lantern_radius, float(Ambience.fx_defaults().get("radius", 0.0)), 0.001,
		"and the lantern comes from data/fx.json")

func test_darkness_is_not_something_a_probe_or_a_level_file_can_carry() -> void:
	## Where the mistake would be made: putting the mood in the geometry. Ambience
	## is keyed by level id in data/ambience.json, and `levels/*.json` has no
	## lighting keys at all — which is also why the prover can never see it.
	for name: String in PROBES.keys():
		var raw := _raw(name)
		for key: String in ["darkness", "lights", "emissive", "vignette", "air"]:
			not_ok(raw.has(key),
				"%s carries '%s' — lighting belongs in data/ambience.json" % [name, key])
	# And a probe, having no ambience entry of its own, is lit like everything else.
	var a := Ambience.for_level("deeps_probe")
	near(a.darkness, 0.0, 0.0001, "an unlisted level is not dark by accident")

func test_the_deeps_art_is_not_the_jungle_wearing_a_different_id() -> void:
	## MEMORY: a world kit once emitted the jungle's stone under ruins ids and the
	## level looked plausible. Pixels, not ids.
	var tex: Texture2D = load("res://assets/tiles/tileset.png")
	if tex == null:
		return
	var img := tex.get_image()
	var cols := int(img.get_width() / 16)
	var jungle := LevelLoader.legend_for("jungle")
	for ch: String in DEEPS_IDS.keys():
		if not jungle.has(ch):
			continue
		var d := int(DEEPS_IDS[ch])
		var j := int(jungle[ch])
		gt(float(_painted(img, d, cols)), 0.0,
			"deeps role '%s' (cell %d) has no art at all" % [ch, d])
		ne(_digest(img, d, cols), _digest(img, j, cols),
			"deeps role '%s' (cell %d) is painted identically to the jungle's cell %d"
				% [ch, d, j])
	# And not the heights' either: 240-251 and 260-271 were generated by the same
	# script from different ramps, which is exactly how two blocks come out equal.
	for ch: String in DEEPS_IDS.keys():
		ne(_digest(img, int(DEEPS_IDS[ch]), cols),
			_digest(img, int(HEIGHTS_IDS[ch]), cols),
			"deeps role '%s' is painted identically to the heights' role" % ch)

# --------------------------------------------------------------- the nest probe
## World 5 specific, and it carries the SWITCH VERB CONTRACT the five OBSIDIAN
## NEST level authors build on. The machinery is M2-vintage and battle-tested;
## what was missing was the numbers and the sharp edges in one place. Every
## number below is measured — by this file, by tools/prove.sh over
## tests/fixtures/nest_scratch_*.json, or read off the shipping code — and not
## reasoned.
const NEST := "nest_probe"

## role character -> the id data/level_legend.json binds it to for "nest".
## 280-291 is the whole block: twelve roles, twelve ids, none spare.
const NEST_IDS := {
	"#": 280, "S": 281, "d": 283, "s": 290, "=": 286, "|": 288,
	"^": 287, "c": 291, "L": 282, "T": 285, "r": 289, "X": 284,
}

## The four shared switch blocks. character -> [tile id, group, solid-when].
## These are World 5's verb the way the updraft is World 3's and the shoulder
## wall is World 4's: the pairing lives in data/tiles.json, the level only names
## the character, so no level can state it for itself.
const SWITCH_TILES := {
	"A": [11, 1, true], "a": [26, 1, false],
	"B": [12, 2, true], "b": [27, 2, false],
}

## MEASURED off the shipping code, because a level author has to place the lever
## on a tile and needs to know what part of that tile is live:
## Level._spawn_entity() does `sw.setup(p + Vector2(1, 6), ...)` and
## SwitchTrigger.SIZE is (14, 10) — so the trip box is the BOTTOM TEN PIXELS of
## the 16x16 tile, inset one pixel on each side. It is NOT the tile.
const LEVER_OFFSET := Vector2(1, 6)

func test_the_nest_legend_binds_the_ids_the_obsidian_nest_art_was_painted_for() -> void:
	var lg := LevelLoader.legend_for("nest")
	ok(not lg.is_empty(), "data/level_legend.json defines a 'nest' tileset")
	for ch: String in NEST_IDS.keys():
		eq(int(lg.get(ch, -1)), int(NEST_IDS[ch]),
			"nest '%s' must bind tile %d" % [ch, int(NEST_IDS[ch])])
		var id := int(NEST_IDS[ch])
		ok(id >= 280 and id <= 291,
			"nest role '%s' points at %d, outside the 280-291 block" % [ch, id])

func test_the_nest_tiles_carry_the_flags_their_roles_promise() -> void:
	## The twelve roles mean the same thing in every world, so the flags line up
	## with the jungle's, the heights' and the deeps'.
	var f := TileData4.Flag
	ok(data.flags_of(280) & f.SOLID != 0, "280 obsidian is solid")
	ok(data.flags_of(281) & f.SOLID != 0, "281 obsidian_hot is solid")
	ok(data.flags_of(283) & f.SOLID != 0, "283 nest_block is solid")
	ok(data.flags_of(290) & f.SOLID != 0, "290 nest_plate is solid")
	ok(data.flags_of(286) & f.ONEWAY != 0, "286 nest_ledge is one-way")
	ok(data.flags_of(286) & f.SOLID == 0, "286 nest_ledge is not solid")
	ok(data.flags_of(288) & f.LADDER != 0, "288 nest_chain is climbable")
	ok(data.flags_of(288) & f.SOLID == 0, "288 nest_chain is not solid")
	ok(data.flags_of(287) & f.HAZARD != 0, "287 nest_shard hurts")
	ok(data.flags_of(291) & f.BREAKABLE != 0, "291 nest_crust breaks")
	ok(data.flags_of(291) & f.SOLID != 0, "291 nest_crust is solid until it does")
	for id: int in [282, 284, 285, 289]:
		eq(data.flags_of(id), 0,
			"%d (%s) is a background tile and must carry no flags" % [id, data.name_of(id)])
	for id: int in NEST_IDS.values():
		ok(data.flags_of(id) & f.WATER == 0,
			"%d (%s) — nothing in the nest block is water" % [id, data.name_of(id)])
		ok(data.flags_of(id) & f.SWITCHED == 0,
			"%d (%s) — a world tile never carries a switch group" % [id, data.name_of(id)])

func test_the_nest_probe_grid_answers_those_flags_through_a_real_tileworld() -> void:
	## Flags on ids prove the table; this proves the *level* — the grid the loader
	## built from the probe's characters answers collision correctly at the
	## coordinates the fixture authored.
	var def := _load(NEST)
	ok(def.ok(), "nest probe loads: %s" % ", ".join(def.errors))
	if def.world == null:
		return
	var w := def.world
	eq(w.width, 25, "the probe is one screen wide")
	eq(w.height, 15, "the probe is one screen tall")
	ok(w.is_solid(0, 13), "the ground cap is solid")
	eq(w.get_fg(0, 13), 280, "the ground cap is obsidian")
	ok(w.is_solid(0, 14), "the fill under the cap is solid")
	eq(w.get_fg(0, 14), 283, "the fill is nest_block")
	eq(w.get_fg(3, 6), 281, "the overhead shelf is obsidian_hot")
	ok(w.is_solid(3, 6), "and it is solid")
	eq(w.get_fg(14, 8), 290, "the exit shelf is nest_plate")
	ok(w.is_solid(14, 8), "and it is solid")
	ok(w.is_oneway(6, 10), "the bypass deck is one-way")
	not_ok(w.is_solid(6, 10), "and not solid")
	ok(w.is_ladder(13, 10), "the chain climbs")
	ok(w.is_hazard(17, 12), "the shard field is a hazard")
	ok(w.is_breakable(4, 6), "the crust breaks")
	ok(w.is_water(21, 12), "the pool is water")
	not_ok(w.is_solid(1, 12), "the walkable floor level is open")
	# Background tiles are decoration only: nothing in bg may affect collision.
	eq(w.get_bg(0, 0), 289, "the ceiling is nest_vein")
	eq(w.get_bg(0, 2), 282, "the wall behind the gallery is nest_wall")
	eq(w.get_bg(1, 5), 285, "the flues are nest_flue")
	eq(w.get_bg(0, 13), 284, "under the floor is nest_void")
	not_ok(w.is_solid(0, 0), "a bg vein is not something you stand on")

# ------------------------------- SWITCH VERB CONTRACT 1: the pairing and the seed
func test_the_four_switch_blocks_are_two_pairs_and_the_table_says_so() -> void:
	## The data half. Two groups exist and there is no third: a level gets one
	## 'a' lever and one 'b' lever, and every switch_a in it shares group 1.
	var f := TileData4.Flag
	var shared: Dictionary = LevelLoader.legend_doc().get("shared", {})
	var groups: Dictionary = {}
	for ch: String in SWITCH_TILES.keys():
		var spec: Array = SWITCH_TILES[ch]
		var id := int(spec[0])
		eq(int(shared.get(ch, -1)), id, "'%s' is the shared character for %d" % [ch, id])
		ok(data.flags_of(id) & f.SOLID != 0, "%d (%s) is a wall" % [id, data.name_of(id)])
		ok(data.flags_of(id) & f.SWITCHED != 0, "%d (%s) is switched" % [id, data.name_of(id)])
		eq(data.switch_group[id], int(spec[1]), "%d belongs to group %d" % [id, int(spec[1])])
		eq(data.switch_state[id] == 1, bool(spec[2]),
			"%d is solid when its group is %s" % [id, "ON" if bool(spec[2]) else "OFF"])
		groups[int(spec[1])] = true
	eq(groups.size(), 2, "there are exactly two switch groups in the whole game")
	# And nothing else in the table is switched, so an author cannot reach for a
	# third pair that does not exist.
	var switched: Array = []
	for id in data.switch_group.size():
		if data.flags_of(id) & f.SWITCHED != 0:
			switched.append(id)
	eq(switched, [11, 12, 26, 27], "the only switch tiles in data/tiles.json")

func test_group_one_starts_on_and_group_two_starts_off_everywhere() -> void:
	## The seed, in the two places that seed it. Everything an author draws with
	## 'A'/'a'/'B'/'b' reads off this: 'A' and 'b' are WALLS on frame one, 'a' and
	## 'B' are HOLES on frame one, before any lever is touched.
	var rows: Array = [[0, 0], [1, 1]]
	var bare := TileWorld.from_rows(rows, data)
	eq(bool(bare.switch_states.get(1, false)), true, "TileWorld seeds group 1 ON")
	eq(bool(bare.switch_states.get(2, true)), false, "TileWorld seeds group 2 OFF")
	var def := _load(NEST)
	if def.world == null:
		return
	var w := def.world
	ok(w.is_solid(8, 12), "'A' at (8,12) is a wall before the lever is thrown")
	not_ok(w.is_solid(10, 9), "'a' at (10,9) is a hole before the lever is thrown")
	not_ok(w.is_solid(20, 10), "'B' at (20,10) is a hole before the lever is thrown")
	ok(w.is_solid(21, 10), "'b' at (21,10) is a wall before the lever is thrown")
	# And the prover seeds the same world the same way — ProverSim.reset() repeats
	# TileWorld's defaults and then applies each switch entity's own `on`, in the
	# order SwitchTrigger._ready() applies them.
	var sim := ProverSim.new()
	sim.setup(def)
	eq(sim.switch_bits, 1, "the prover starts the probe with group 1 on and group 2 off")

func test_switch_group_survives_the_level_round_trip_into_a_tileworld() -> void:
	## The World 5 twin of `test_the_updraft_vectors_survive_a_level_round_trip`.
	## The group and the sense live in data/tiles.json and the level only names
	## the character; if they were lost, five levels would break at once with
	## nothing pointing at the cause. Both configurations, on the probe's own grid,
	## through the shipping TileWorld.is_solid().
	var def := _load(NEST)
	if def.world == null:
		return
	var w := def.world
	var a_gate := [Vector2i(8, 11), Vector2i(8, 12)]
	var a_ghost := [Vector2i(10, 8), Vector2i(10, 9)]
	var b_lid := [Vector2i(20, 10), Vector2i(22, 10)]
	var b_ghost := [Vector2i(21, 10), Vector2i(23, 10)]
	for t: Vector2i in a_gate:
		eq(w.get_fg(t.x, t.y), 11, "(%d,%d) is switch_block_a_on" % [t.x, t.y])
	for t: Vector2i in a_ghost:
		eq(w.get_fg(t.x, t.y), 26, "(%d,%d) is switch_block_a_off" % [t.x, t.y])
	for t: Vector2i in b_lid:
		eq(w.get_fg(t.x, t.y), 12, "(%d,%d) is switch_block_b_on" % [t.x, t.y])
	for t: Vector2i in b_ghost:
		eq(w.get_fg(t.x, t.y), 27, "(%d,%d) is switch_block_b_off" % [t.x, t.y])
	# Configuration 1: the seed.
	for t: Vector2i in a_gate:
		ok(w.is_solid(t.x, t.y), "group 1 ON: (%d,%d) is a wall" % [t.x, t.y])
	for t: Vector2i in a_ghost:
		not_ok(w.is_solid(t.x, t.y), "group 1 ON: (%d,%d) is open" % [t.x, t.y])
	# Configuration 2: after the lever. Group 2 is untouched, which is the point —
	# the two groups are independent.
	w.set_switch(1, false)
	for t: Vector2i in a_gate:
		not_ok(w.is_solid(t.x, t.y), "group 1 OFF: (%d,%d) is open" % [t.x, t.y])
	for t: Vector2i in a_ghost:
		ok(w.is_solid(t.x, t.y), "group 1 OFF: (%d,%d) is a wall" % [t.x, t.y])
	for t: Vector2i in b_lid:
		not_ok(w.is_solid(t.x, t.y), "group 2 is untouched by group 1's lever")
	w.set_switch(2, true)
	for t: Vector2i in b_lid:
		ok(w.is_solid(t.x, t.y), "group 2 ON: the lid closes")
	for t: Vector2i in b_ghost:
		not_ok(w.is_solid(t.x, t.y), "group 2 ON: its pair opens")
	w.set_switch(1, true)
	w.set_switch(2, false)
	ok(w.is_solid(8, 12), "and the seed is restorable")

func test_the_renderer_picks_switch_art_by_solidity_and_not_by_the_authored_id() -> void:
	## The M2 fix, pinned. A pair is authored as either half and the *ghost* is
	## always the `_off` art, so `TileRenderer._draw_layer()` resolves the cell
	## from `world.is_solid()` rather than swapping ids in the grid. Without it,
	## half of every switch wall in World 5 renders as the wrong state.
	var r := TileRenderer.new()
	eq(r._ghost_of(11), 26, "11 ghosts as 26")
	eq(r._ghost_of(12), 27, "12 ghosts as 27")
	eq(r._solid_of(26), 11, "26 solidifies as 11")
	eq(r._solid_of(27), 12, "27 solidifies as 12")
	eq(r._ghost_of(280), 280, "and an ordinary tile is left alone")
	r.free()

# ----------------------------- SWITCH VERB CONTRACT 2: which forms throw a lever
func test_the_lever_box_is_the_bottom_ten_pixels_of_its_tile() -> void:
	## THE RULE THAT COST RUINS_4 A DEBUGGING SESSION. The entity's x,y is a tile;
	## the thing that trips is 14x10 at +1,+6 inside it. A body that arrives in the
	## row above never touches it, and a body swimming through the TOP of the
	## lever's own row can miss it too.
	eq(SwitchTrigger.SIZE, Vector2(14, 10), "the trip box is 14x10")
	var ts := float(TileData4.TILE_SIZE)
	var tile := Vector2(8.0 * ts, 10.0 * ts)
	var sw := SwitchTrigger.new()
	sw.setup(tile + LEVER_OFFSET, 1, true)
	var box := sw.aabb()
	eq(box.position, Vector2(129.0, 166.0), "one pixel in, six pixels down")
	eq(box.end, Vector2(143.0, 176.0), "and flush with the bottom of the tile")
	near(box.position.y - tile.y, 6.0, 0.0001, "six pixels of the tile are dead")
	near(tile.y + ts - box.end.y, 0.0, 0.0001, "and none at the bottom")
	# THE DEAD ZONE, measured rather than described: the trip is decided by the
	# body's BOTTOM edge, and that edge has to reach 6 px into the lever's tile.
	# Six pixels is a third of a tile and the whole of the ruins_4 trap.
	var bottom_at := func(y: float) -> bool:
		return box.intersects(Rect2(tile.x + 1.0, y - 9.0, 14.0, 9.0))
	not_ok(bottom_at.call(tile.y), "a body whose feet stop at the tile's top misses")
	not_ok(bottom_at.call(tile.y + 5.0), "five pixels in still misses")
	not_ok(bottom_at.call(tile.y + 6.0), "six pixels in is the edge, and edges do not count")
	ok(bottom_at.call(tile.y + 7.0), "seven pixels in is the first pixel that trips it")
	ok(bottom_at.call(tile.y + ts), "and a body sunk to the bottom of the row trips it")
	# So a 9 px fish swimming along the TOP of the lever's own row does trip it,
	# but only by 3 px of overlap — and one swimming 3 px higher, which is still
	# visually inside the row, does not.
	ok(box.intersects(Rect2(tile.x + 1.0, tile.y, 14.0, 9.0)),
		"a fish at the top of the lever's own row trips it by three pixels")
	not_ok(box.intersects(Rect2(tile.x + 1.0, tile.y - 3.0, 14.0, 9.0)),
		"three pixels higher and the same fish swims straight past")
	# And a body that arrives in the row ABOVE never touches it at all. That is
	# the ruins_4 trap: a two-row arrival whose live row is the wrong one.
	var row_above := Rect2(tile.x + 1.0, tile.y - ts, 14.0, 9.0)
	not_ok(box.intersects(row_above), "the row above is not even close")
	# Sideways the box is 14 of 16 px, so a body anywhere over the tile touches it.
	ok(box.intersects(Rect2(tile.x, tile.y + 10.0, 10.0, 6.0)),
		"a 10 px body against the tile's left edge is inside the box")
	ok(box.intersects(Rect2(tile.x + 6.0, tile.y + 10.0, 10.0, 6.0)),
		"and against its right edge")
	sw.free()

func test_every_form_trips_a_lever_by_standing_on_the_floor_under_it() -> void:
	## The contact half of the verb, for all four forms, measured through the same
	## predicate SwitchTrigger._physics_process() uses — `aabb().intersects(p.aabb())`
	## — with each body settled on a real floor by the shipping movement code. The
	## frog and the bird carry no weapon at all, so if this failed for them a lever
	## would be scenery to half the forms in the game.
	var ts := float(TileData4.TILE_SIZE)
	var rows: Array = []
	for y in 8:
		var r: Array = []
		for x in 12:
			r.append(1 if (y == 6 or y == 7 or x == 0 or x == 11) else 0)
		rows.append(r)
	var world := TileWorld.from_rows(rows, data)
	# The lever sits on tile (5,5): the row whose floor is the cap at row 6.
	var sw := SwitchTrigger.new()
	sw.setup(Vector2(5.0 * ts, 5.0 * ts) + LEVER_OFFSET, 1, true)
	var overlaps: Dictionary = {}
	for form_id: String in ["human", "frog", "bird", "fish"]:
		var f := FormBase.load_form(form_id)
		var hb: Dictionary = f.hitbox()
		var a := Actor.new()
		a.world = world
		a.box = Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
		# Centred on the lever's column, dropped from just above the floor, then
		# settled — so the y is the one play produces and not one this test chose.
		a.pos = Vector2(5.0 * ts + (ts - a.box.x) * 0.5, 6.0 * ts - a.box.y - 2.0)
		var input := InputState.new()
		for i in 20:
			f.update(a, input, DT)
			a.step_motion(DT)
		ok(a.on_floor, "%s settles on the floor" % form_id)
		var hit := sw.aabb().intersects(a.aabb())
		ok(hit, "%s (%d px tall) standing under the lever trips it"
			% [form_id, int(a.box.y)])
		overlaps[form_id] = sw.aabb().intersects(a.aabb())
	eq(overlaps.size(), 4, "all four forms were measured")
	sw.free()

func test_only_the_human_can_trip_a_lever_from_range() -> void:
	## The other half, and the one an author will get wrong. `Blade._trip_switches()`
	## is the only code in the game that toggles a SwitchTrigger without a body
	## touching it, and the blade is the human's weapon. The fish DOES carry a
	## weapon — `can_attack` is true — but `bite` spawns a MeleeHit, which trips
	## nothing. So a lever placed out of reach is a HUMAN-ONLY lever, and a lever
	## a frog, a bird or a fish has to throw must be somewhere its body can go.
	eq(FormBase.load_form("human").weapon_id(), "boomerang_blade", "the human throws the blade")
	eq(FormBase.load_form("fish").weapon_id(), "bite", "the fish bites instead")
	eq(FormBase.load_form("frog").weapon_id(), "", "the frog carries nothing")
	eq(FormBase.load_form("bird").weapon_id(), "", "the bird carries nothing")
	var blade := FileAccess.get_file_as_string("res://src/player/weapons/blade.gd")
	ok(blade.contains("_trip_switches"), "the blade is what reaches a lever")
	var melee := FileAccess.get_file_as_string("res://src/player/weapons/melee_hit.gd")
	not_ok(melee.contains("switch"), "and the bite is not")

# --------------------------- SWITCH VERB CONTRACT 3: what the gate can prove
func test_the_prover_tells_two_switch_configurations_apart() -> void:
	## THE LOAD-BEARING ONE. A route that crosses a gate, throws the lever again
	## and crosses back visits the same ground twice in two different worlds, and
	## the search would prune the second visit as a duplicate unless the switch
	## state is part of the key. `ProverSearch._key()` folds `sim.switch_bits` in;
	## this proves it does, by changing nothing else.
	var def := _load(NEST)
	if def.world == null:
		return
	var sim := ProverSim.new()
	sim.setup(def)
	var search := ProverSearch.new()
	var on_key: int = search._key(sim)
	ok(sim.world.is_solid(8, 12), "the gate starts shut")
	var s: Array = sim.snapshot()
	var flipped: Array = s.duplicate()
	flipped[10] = 0                  # ProverSim.snapshot(): index 10 is switch_bits
	sim.restore(flipped)
	not_ok(sim.world.is_solid(8, 12), "and restoring the other configuration opens it")
	var off_key: int = search._key(sim)
	ne(on_key, off_key,
		"the same body in two switch states must be two states to the search")
	sim.restore(s)
	eq(search._key(sim), on_key, "and flipping back is the state it was")
	ok(sim.world.is_solid(8, 12), "gate included")

func test_no_switch_tile_in_the_probe_is_something_the_route_stands_on() -> void:
	## THE CONSTRAINT ON EVERY WORLD 5 LEVEL, and it comes from the OTHER gate.
	## tools/reachability.py:81 resolves any tile carrying a `switch_group` as
	## NOT SOLID, unconditionally — it cannot know which half is up, so it assumes
	## the passable one. That is safe for a wall (the checker walks through a gate
	## it should not) and a silent lie for a FLOOR: a ledge made of 'A' is a ledge
	## reachability believes you fall through, and a ledge made of 'a' is one it
	## believes is not there at all. Switch blocks are walls and doors. Never
	## floors, never the one platform a jump lands on.
	var def := _load(NEST)
	if def.world == null:
		return
	var w := def.world
	var raw := _raw(NEST)
	var marks: Dictionary = raw.get("marks", {})
	var f := TileData4.Flag
	for name: String in marks.keys():
		var m: Dictionary = marks[name]
		var x := int(m.get("x", 0))
		var y := int(m.get("y", 0))
		eq(w.flags_at(x, y) & f.SWITCHED, 0,
			"mark '%s' sits inside a switch block" % name)
		eq(w.flags_at(x, y + 1) & f.SWITCHED, 0,
			"mark '%s' stands ON a switch block" % name)
	# And the walked line, spawn (2,12) east to the chain at (13,12): nothing under
	# it is switched, and nothing on it is a hazard or a breakable.
	for x in range(2, 14):
		eq(w.flags_at(x, 13) & f.SWITCHED, 0,
			"(%d,13) is floor the route walks and it is switched" % x)
		not_ok(w.is_hazard(x, 12), "(%d,12) is on the walked line and a hazard" % x)
		not_ok(w.is_breakable(x, 12), "(%d,12) is on the walked line and breakable" % x)

func test_the_nest_art_is_not_another_world_wearing_a_different_id() -> void:
	## MEMORY: a world kit once emitted the jungle's stone under ruins ids and the
	## level looked plausible. Pixels, not ids — and by World 5 there are four
	## earlier blocks to collide with, all generated by the same script from
	## different ramps, which is exactly how two blocks come out equal.
	var tex: Texture2D = load("res://assets/tiles/tileset.png")
	if tex == null:
		return
	var img := tex.get_image()
	var cols := int(img.get_width() / 16)
	var jungle := LevelLoader.legend_for("jungle")
	for ch: String in NEST_IDS.keys():
		var n := int(NEST_IDS[ch])
		gt(float(_painted(img, n, cols)), 0.0,
			"nest role '%s' (cell %d) has no art at all" % [ch, n])
		if jungle.has(ch):
			ne(_digest(img, n, cols), _digest(img, int(jungle[ch]), cols),
				"nest role '%s' (cell %d) is painted identically to the jungle's" % [ch, n])
		ne(_digest(img, n, cols), _digest(img, int(HEIGHTS_IDS[ch]), cols),
			"nest role '%s' is painted identically to the heights' role" % ch)
		ne(_digest(img, n, cols), _digest(img, int(DEEPS_IDS[ch]), cols),
			"nest role '%s' is painted identically to the deeps' role" % ch)
	# The switch blocks are shared art, and the whole verb reads off the player
	# being able to see which half is up: the two halves of a pair must not be
	# painted the same.
	for pair: Array in [[11, 26], [12, 27]]:
		gt(float(_painted(img, int(pair[0]), cols)), 0.0,
			"cell %d has no art at all" % int(pair[0]))
		gt(float(_painted(img, int(pair[1]), cols)), 0.0,
			"cell %d has no art at all" % int(pair[1]))
		ne(_digest(img, int(pair[0]), cols), _digest(img, int(pair[1]), cols),
			"%d and %d are painted the same, so the state is invisible"
				% [int(pair[0]), int(pair[1])])
	ne(_digest(img, 11, cols), _digest(img, 12, cols),
		"group 1 and group 2 blocks must be tellable apart")

# --------------------------------------------------------------------- the art
func test_every_probe_resolves_to_atlas_cells_that_exist_and_are_painted() -> void:
	## The render half. A tile whose atlas cell is off the sheet or blank draws
	## nothing, and only in the world that uses it — which is exactly the shape
	## of bug a new tileset produces.
	var tex: Texture2D = load("res://assets/tiles/tileset.png")
	ok(tex != null, "the tileset atlas loads")
	if tex == null:
		return
	var img := tex.get_image()
	var cols := int(img.get_width() / 16)
	var cells := cols * int(img.get_height() / 16)
	# One assertion per distinct cell rather than per tile: 375 tiles resolve to
	# a couple of dozen paintings, and a blank cell is blank wherever it lands.
	var seen: Dictionary = {}
	for name: String in PROBES.keys():
		var def := _load(name)
		if def.world == null or def.variants == null:
			continue
		for layer: String in ["fg", "bg"]:
			var resolved: PackedInt32Array = def.variants.bg if layer == "bg" else def.variants.fg
			for i in resolved.size():
				var c := resolved[i]
				if c <= 0 or seen.has(c):
					continue
				seen[c] = true
				lt(float(c), float(cells), "%s %s resolves cell %d off the sheet" % [name, layer, c])
				if c < cells:
					gt(float(_painted(img, c, cols)), 0.0,
						"%s %s draws blank atlas cell %d" % [name, layer, c])
	gt(float(seen.size()), 20.0, "the probes are not a stub: %d distinct paintings" % seen.size())

func test_the_heights_art_is_not_the_jungle_wearing_a_different_id() -> void:
	## MEMORY: a world kit once emitted the jungle's stone under ruins ids and
	## the level looked plausible. Pixels, not ids: each heights role must be
	## painted differently from the jungle role it stands in for.
	var tex: Texture2D = load("res://assets/tiles/tileset.png")
	if tex == null:
		return
	var img := tex.get_image()
	var cols := int(img.get_width() / 16)
	var jungle := LevelLoader.legend_for("jungle")
	for ch: String in HEIGHTS_IDS.keys():
		if not jungle.has(ch):
			continue
		var h := int(HEIGHTS_IDS[ch])
		var j := int(jungle[ch])
		gt(float(_painted(img, h, cols)), 0.0,
			"heights role '%s' (cell %d) has no art at all" % [ch, h])
		ne(_digest(img, h, cols), _digest(img, j, cols),
			"heights role '%s' (cell %d) is painted identically to the jungle's cell %d"
				% [ch, h, j])

func _painted(img: Image, index: int, cols: int) -> int:
	var x0 := (index % cols) * 16
	var y0 := int(index / cols) * 16
	var n := 0
	for y in range(y0, y0 + 16):
		for x in range(x0, x0 + 16):
			if img.get_pixel(x, y).a > 0.0:
				n += 1
	return n

## Cheap content hash of one atlas cell — enough to tell two paintings apart.
func _digest(img: Image, index: int, cols: int) -> String:
	var x0 := (index % cols) * 16
	var y0 := int(index / cols) * 16
	var ctx := HashingContext.new()
	ctx.start(HashingContext.HASH_MD5)
	var buf := PackedByteArray()
	for y in range(y0, y0 + 16):
		for x in range(x0, x0 + 16):
			var c := img.get_pixel(x, y)
			buf.append(int(c.r8))
			buf.append(int(c.g8))
			buf.append(int(c.b8))
			buf.append(int(c.a8))
	ctx.update(buf)
	return ctx.finish().hex_encode()
