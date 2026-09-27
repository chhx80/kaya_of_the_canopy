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
const FULL_COVERAGE := ["heights_probe"]

const DIR := "res://tests/fixtures/"

var data: TileData4

func before_each() -> void:
	data = TileData4.new()
	data.load_from(TileData4.PATH)

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
