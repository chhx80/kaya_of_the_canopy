extends TestCase
## Gates tools/world_kit.py -- the authoring kit for the four new worlds.
##
## Three jobs, in order of how much they are worth:
##
## 1. Run the kit's own Python self-test, so `tools/test.sh` fails when the kit
##    stops refusing the geometry it is supposed to refuse. The kit is Python
##    and its self-test is the only place that can exercise "this call must
##    raise"; reaching it from here is what puts it in a gate.
## 2. Re-derive the kit's traversal invariants from the COMMITTED fixture rooms,
##    with the engine's own TileData4 flags rather than the kit's copy of them.
##    Two independent implementations agreeing is worth more than one running
##    twice, and it is the kit's output that ships, not its opinion.
## 3. Check that LIMITS has not drifted away from data/forms/*.json. The whole
##    table is measured against a specific jump_vel and gravity; retune either
##    and the numbers become a lie that reads like a measurement.
##
## What this file does NOT do is claim the rooms are playable. That is
## tools/prove.sh (ADR 005), one room at a time -- the commands are in REPORT.md.

const TS := TileData4.TILE_SIZE
const FIXTURES := "res://tests/fixtures/world_kit"
const KIT := "res://tools/world_kit.py"

## Rooms the kit emits, and what tools/prove.sh is expected to do with each.
## Kept in step with PROOFS in tools/world_kit.py by
## test_the_room_table_matches_the_kit below, so the two cannot drift.
##
##   "prove"   exit 0.
##   "fail"    exit 1 -- the failing twin of a "prove" room, one tile past the
##             limit. A room at the limit that proves says nothing about where
##             the edge is without one past it that does not.
##   "measure" no expected verdict; whatever the prover says is the number.
##   "bug"     fails for a reason that is not the geometry. See
##             proof_tunnel_seam() in the kit -- it reproduces a hop-seam
##             divergence in tools/solver/**, which this branch does not own.
##   "coarse"  every step in it proves on its own; the whole climb in one hop
##             exhausts the budget, and splitting it into hops hits the seam
##             bug. Blocked, with both halves of why committed.
const ROOMS := {
	"rise_human_2": "coarse", "rise_human_2_seam": "bug",
	"rise_human_3": "fail",
	"rise_frog_3": "prove", "rise_frog_4": "measure", "rise_frog_6": "fail",
	"gap_human_3": "prove", "gap_human_4": "measure",
	"gap_human_5": "measure", "gap_human_7": "fail",
	"gap_frog_3": "prove", "gap_frog_4": "measure", "gap_frog_6": "fail",
	"ruins_colonnade": "prove", "heights_deck": "prove",
	"deeps_tunnel": "prove", "deeps_tunnel_seam": "bug",
	"nest_lattice": "prove",
}

# ------------------------------------------------------------------ the kit

func test_the_python_selftest_passes() -> void:
	var py := _python()
	if py == "":
		_fail("cannot find PYVENV in tools/env.sh, so the kit's self-test did "
			+ "not run. env.sh is gitignored -- copy tools/env.sh.example.")
		return
	var out: Array = []
	var code := OS.execute(py, [ProjectSettings.globalize_path(KIT),
		"--selftest"], out, true)
	var text := "\n".join(out)
	eq(code, 0, "python tools/world_kit.py --selftest failed:\n%s" % text)
	ok(text.contains("0 failed"), "self-test summary was: %s" % text.strip_edges())


func _python() -> String:
	var f := FileAccess.open("res://tools/env.sh", FileAccess.READ)
	if f == null:
		return ""
	var path := ""
	while not f.eof_reached():
		var line := f.get_line().strip_edges()
		if line.begins_with("export PYVENV="):
			path = line.split("=", true, 1)[1].strip_edges().trim_prefix("\"").trim_suffix("\"")
	f.close()
	if path != "" and FileAccess.file_exists(path):
		return path
	return ""


func test_the_room_table_matches_the_kit() -> void:
	# ROOMS above and PROOFS in tools/world_kit.py describe the same set. Two
	# lists of the same thing drift; this is the cheapest way to notice.
	var src := FileAccess.open("res://tools/world_kit.py", FileAccess.READ)
	ok(src != null, "tools/world_kit.py must be readable")
	if src == null:
		return
	var text := src.get_as_text()
	src.close()
	for name: String in ROOMS:
		ok(text.contains("\"%s\":" % name),
			"%s is in this test's ROOMS but not in world_kit.py's PROOFS" % name)
		var verdict := String(ROOMS[name])
		ok(text.contains("\"" + verdict + "\")"),
			"world_kit.py declares no '%s' verdict" % verdict)


# ----------------------------------------------------------- the proof rooms

func test_every_proof_room_is_committed() -> void:
	for name: String in ROOMS:
		ok(FileAccess.file_exists("%s/%s.json" % [FIXTURES, name]),
			"%s.json is missing -- run python3 tools/world_kit.py --emit-proofs"
			% name)


func test_every_proof_room_loads_and_declares_a_route() -> void:
	for name: String in ROOMS:
		var def := _room(name)
		if def == null:
			continue
		ok(def.ok(), "%s: %s" % [name, ", ".join(def.errors)])
		var raw := _raw(name)
		var route: Array = raw.get("route", [])
		gt(float(route.size()), 0.0, "%s declares no route; ADR 005 fails it" % name)
		if route.is_empty():
			continue
		eq(String((route[0] as Dictionary)["from"]), "spawn",
			"%s: the route must start at spawn" % name)
		var last := String((route[route.size() - 1] as Dictionary)["to"])
		ok(last == "exit" or last == "boss_exit",
			"%s: the route ends at '%s', not an exit" % [name, last])


func test_every_mark_in_a_proof_room_is_standable() -> void:
	# A mark in mid-air, or with its head in rock, passes generation and costs a
	# whole prover run to discover. The body is 22px, so two tiles.
	for name: String in ROOMS:
		var def := _room(name)
		if def == null or not def.ok():
			continue
		var raw := _raw(name)
		var marks: Dictionary = raw.get("marks", {})
		for mark_name: String in marks:
			var m: Dictionary = marks[mark_name]
			var x := int(m["x"])
			var y := int(m["y"])
			not_ok(def.world.is_solid(x, y),
				"%s: mark '%s' at (%d,%d) is inside a solid tile"
				% [name, mark_name, x, y])
			not_ok(def.world.is_solid(x, y - 1),
				"%s: mark '%s' at (%d,%d) has no headroom"
				% [name, mark_name, x, y])
			ok(_supported(def, x, y),
				"%s: mark '%s' at (%d,%d) has nothing under it -- not a floor, "
				+ "not a platform, not a ladder, not water"
				% [name, mark_name, x, y])


func test_every_ladder_in_a_proof_room_has_a_landing() -> void:
	# Defect 1: a vine with no exit at the top, "reachable" via a blind mid-air
	# jump. Checked here against the engine's own flags, not the kit's copy.
	for name: String in ROOMS:
		var def := _room(name)
		if def == null or not def.ok():
			continue
		var w := def.world.width
		var h := def.world.height
		var tops: Dictionary = {}
		for x in w:
			for y in h:
				if def.world.is_ladder(x, y):
					if not tops.has(x):
						tops[x] = y
		for x: int in tops:
			var top: int = tops[x]
			var found := false
			for y in range(top, mini(h, top + 3)):
				for dx in [-1, 1]:
					if _supported(def, x + dx, y) \
							and not def.world.is_solid(x + dx, y) \
							and not def.world.is_solid(x + dx, y - 1):
						found = true
			ok(found, "%s: the ladder in column %d tops out at row %d with "
				% [name, x, top]
				+ "nothing to step onto within three rows")


func test_no_oneway_platform_is_stood_on_with_one_tile_of_headroom() -> void:
	# Defect 2: a one-way platform with one tile of clearance. Not "solid", so
	# the pocket check skipped it, so nobody could ever be on it. A platform
	# with a lid one tile above is scenery pretending to be a route.
	for name: String in ROOMS:
		var def := _room(name)
		if def == null or not def.ok():
			continue
		for x in def.world.width:
			for y in def.world.height:
				if not def.world.is_oneway(x, y):
					continue
				if y - 1 < 0 or def.world.is_solid(x, y - 1):
					continue        # buried: not somewhere anyone stands
				ok(y - 2 < 0 or not def.world.is_solid(x, y - 2),
					"%s: the platform at (%d,%d) has one tile of headroom; a "
					% [name, x, y]
					+ "body is 22px and needs two")


# -------------------------------------------------------------- LIMITS drift

func test_limits_still_agree_with_the_form_data() -> void:
	# apex = jump_vel^2 / (2 * gravity), the same derivation
	# tools/reachability.py uses. The kit's rise must be at or under it for
	# every form -- and STRICTLY under for the frog, because the measurement
	# that produced 3 is that a cut jump reaches far less than the apex.
	var want := {"human": 2, "frog": 3, "bird": 5, "fish": 1}
	for form: String in want:
		var d := _json("res://data/forms/%s.json" % form)
		ok(not d.is_empty(), "data/forms/%s.json must load" % form)
		if d.is_empty():
			continue
		var v: float = absf(float(d.get("jump_vel", 0.0)))
		var g: float = float(d.get("gravity", 700.0))
		var apex_tiles: float = (v * v / (2.0 * g)) / float(TS)
		if form == "bird":
			# The bird flaps; its ceiling is the largest hop this project has
			# proved, which lives in proofs/jungle_4.tape.json, not in an apex.
			gt(float(d.get("flap_vel", 0.0)) * -1.0, 0.0,
				"the bird must still have a flap for LIMITS to mean anything")
			continue
		if form == "fish":
			var hop: float = absf(float(d.get("surface_hop", 0.0)))
			var hop_tiles: float = (hop * hop / (2.0 * g)) / float(TS)
			gt(hop_tiles, float(want[form]),
				"the fish surface hop is %.2f tiles; LIMITS says a %d-tile bank"
				% [hop_tiles, want[form]])
			lt(hop_tiles, float(want[form]) + 1.0,
				"the fish surface hop is %.2f tiles, so a %d-tile bank would "
				% [hop_tiles, want[form] + 1]
				+ "now clear -- LIMITS is stale, and defect 4 was this exact bug")
			continue
		gt(apex_tiles, float(want[form]),
			"%s apex is %.2f tiles but LIMITS asks for a %d-tile rise"
			% [form, apex_tiles, want[form]])
		if form == "frog":
			gt(apex_tiles, 5.0, "the frog apex was measured at 5.34 tiles; it "
				+ "is now %.2f, so the 3-tile rung is no longer the same "
				% apex_tiles + "conclusion")


# ------------------------------------------------------------------ helpers

func _raw(name: String) -> Dictionary:
	return _json("%s/%s.json" % [FIXTURES, name])


func _json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return parsed as Dictionary if parsed is Dictionary else {}


func _room(name: String) -> LevelLoader.LevelDef:
	var path := "%s/%s.json" % [FIXTURES, name]
	if not FileAccess.file_exists(path):
		return null
	return LevelLoader.load_path(path, name)


func _supported(def: LevelLoader.LevelDef, x: int, y: int) -> bool:
	var w: TileWorld = def.world
	if not w.in_bounds(x, y):
		return false
	if w.is_ladder(x, y) or w.is_water(x, y):
		return true
	if y + 1 >= w.height:
		return false
	return w.is_solid(x, y + 1) or w.is_oneway(x, y + 1)
