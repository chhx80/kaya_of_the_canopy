extends TestCase
## The per-world legend (ADR 002).
##
## `data/level_legend.json` is the only thing standing between the art in
## `data/tiles.json` and a level file: a tile nothing can name is a tile that
## cannot be placed. These tests are written against that outcome — "every
## declared tile is nameable, and naming one wrongly fails loudly" — rather
## than against the mechanism, because the mechanism has been right before
## while the outcome was not.

const LEGEND_PATH := "res://data/level_legend.json"
const TILES_PATH := "res://data/tiles.json"

## The twelve characters every world binds to its own art. A tileset missing
## one of these is half-built, and the level author who discovers that is the
## one who has already laid out a screen with it.
const ROLE_CHARS := ["#", "S", "d", "s", "=", "|", "^", "c", "L", "T", "r", "X"]

func _json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	return parsed as Dictionary

func _doc() -> Dictionary:
	return _json(LEGEND_PATH)

func _shared() -> Dictionary:
	return _doc().get("shared", {}) as Dictionary

func _tilesets() -> Dictionary:
	return _doc().get("tilesets", {}) as Dictionary

func _declared_tiles() -> Dictionary:
	return _json(TILES_PATH).get("tiles", {}) as Dictionary

# ---------------------------------------------------------------- the document

func test_the_legend_declares_shared_characters_and_named_tilesets() -> void:
	var doc := _doc()
	ok(doc.has("shared"), "data/level_legend.json needs a 'shared' map")
	ok(doc.has("tilesets"), "data/level_legend.json needs a 'tilesets' map")
	gt(float(_shared().size()), 0.0, "'shared' must not be empty")
	gt(float(_tilesets().size()), 1.0,
		"one tileset is the old global legend wearing a new key")

func test_the_default_tileset_is_one_that_exists() -> void:
	var name := LevelLoader.default_tileset()
	ok(_tilesets().has(name),
		"default_tileset is '%s', which 'tilesets' does not define" % name)

func test_the_five_worlds_of_the_plan_all_have_a_tileset() -> void:
	# docs/plan-20-levels.md: jungle, Sunken Ruins, Thermal Heights,
	# Termite Deeps, The Obsidian Nest.
	for name in ["jungle", "ruins", "heights", "deeps", "nest"]:
		ok(_tilesets().has(name), "no tileset named '%s'" % name)

## `legend` is a resolved copy of the default world, kept only because
## tools/reachability.py and tools/build_hub.py read that key straight out of
## the JSON. Two copies of the same fact drift; this is what stops it.
func test_the_compatibility_legend_still_equals_shared_plus_the_default() -> void:
	var expected: Dictionary = {}
	expected.merge(_shared())
	expected.merge(_tilesets()[LevelLoader.default_tileset()] as Dictionary, true)
	var actual: Dictionary = _doc().get("legend", {}) as Dictionary
	eq(actual.size(), expected.size(),
		"'legend' has %d entries, shared + %s has %d"
			% [actual.size(), LevelLoader.default_tileset(), expected.size()])
	for ch: String in expected.keys():
		eq(int(actual.get(ch, -1)), int(expected[ch]),
			"'legend' maps '%s' to %s, shared + %s maps it to %d"
				% [ch, actual.get(ch, "nothing"), LevelLoader.default_tileset(),
					int(expected[ch])])

## A tileset that redefines a shared character makes water mean one thing in
## the jungle and another in the ruins — which is exactly the confusion the
## shared block exists to prevent.
func test_no_tileset_redefines_a_shared_character() -> void:
	var shared := _shared()
	for name: String in _tilesets().keys():
		for ch: String in (_tilesets()[name] as Dictionary).keys():
			not_ok(shared.has(ch),
				"tileset '%s' redefines shared character '%s'" % [name, ch])

func test_every_character_names_a_tile_that_data_tiles_json_declares() -> void:
	var tiles := _declared_tiles()
	for ch: String in _shared().keys():
		ok(tiles.has(str(int(_shared()[ch]))),
			"shared '%s' -> id %d, which data/tiles.json does not declare"
				% [ch, int(_shared()[ch])])
	for name: String in _tilesets().keys():
		var set_: Dictionary = _tilesets()[name] as Dictionary
		for ch: String in set_.keys():
			ok(tiles.has(str(int(set_[ch]))),
				"tileset '%s' maps '%s' to id %d, which data/tiles.json does not declare"
					% [name, ch, int(set_[ch])])

func test_every_tileset_binds_the_whole_role_alphabet() -> void:
	for name: String in _tilesets().keys():
		var set_: Dictionary = _tilesets()[name] as Dictionary
		for ch: String in ROLE_CHARS:
			ok(set_.has(ch),
				"tileset '%s' does not bind '%s' — a level built for it cannot "
					% [name, ch]
					+ "use the idiom that writes that character")

func test_no_tileset_maps_two_characters_to_the_same_tile() -> void:
	for name: String in _tilesets().keys():
		var set_: Dictionary = _tilesets()[name] as Dictionary
		var seen := {}
		for ch: String in set_.keys():
			var tid := int(set_[ch])
			not_ok(seen.has(tid),
				"tileset '%s' maps both '%s' and '%s' to tile %d"
					% [name, seen.get(tid, "?"), ch, tid])
			seen[tid] = ch

## The whole point of this change, stated as an outcome. Before it,
## data/tiles.json declared 88 ids and a level could name 28 of them; the
## other 60 were painted, tested and unplaceable. If a future world adds art
## and forgets the legend, this is the test that says so.
func test_every_declared_tile_can_be_named_by_some_level() -> void:
	var nameable := {}
	for ch: String in _shared().keys():
		nameable[int(_shared()[ch])] = "shared '%s'" % ch
	for name: String in _tilesets().keys():
		var set_: Dictionary = _tilesets()[name] as Dictionary
		for ch: String in set_.keys():
			nameable[int(set_[ch])] = "%s '%s'" % [name, ch]
	for key: String in _declared_tiles().keys():
		var tid := int(key)
		var t: Dictionary = _declared_tiles()[key] as Dictionary
		ok(nameable.has(tid),
			"tile %d (%s) is declared and painted but no character in any "
				% [tid, t.get("name", "?")]
				+ "tileset names it, so no level can place it")

# ---------------------------------------------------------------- the loader

func test_legend_for_merges_shared_into_each_world() -> void:
	for name: String in _tilesets().keys():
		var merged := LevelLoader.legend_for(name)
		for ch: String in _shared().keys():
			eq(int(merged.get(ch, -1)), int(_shared()[ch]),
				"legend_for('%s') lost shared character '%s'" % [name, ch])
		var own: Dictionary = _tilesets()[name] as Dictionary
		for ch: String in own.keys():
			eq(int(merged.get(ch, -1)), int(own[ch]),
				"legend_for('%s') lost its own character '%s'" % [name, ch])

func test_legend_for_an_undefined_world_is_empty() -> void:
	ok(LevelLoader.legend_for("atlantis").is_empty(),
		"an undefined tileset must resolve to nothing, not to the default")

func test_tileset_names_lists_every_world() -> void:
	var names := LevelLoader.tileset_names()
	eq(names.size(), _tilesets().size(), "tileset_names() must list them all")
	for name: String in _tilesets().keys():
		ok(names.has(name), "tileset_names() omits '%s'" % name)

func test_the_legacy_legend_call_still_returns_the_default_world() -> void:
	var lg := LevelLoader.legend()
	eq(int(lg.get("#", -1)),
		int((_tilesets()[LevelLoader.default_tileset()] as Dictionary)["#"]),
		"LevelLoader.legend() must keep meaning the default world")

# ------------------------------------------------- a level in each world loads

func _grid_using(chars: Array, w: int) -> Array:
	## One row naming every character, padded, over a floor of the first one.
	var top := ""
	for ch: String in chars:
		top += ch
	while top.length() < w:
		top += "."
	var floor_row := ""
	while floor_row.length() < w:
		floor_row += String(chars[0])
	return [top, floor_row]

func test_a_level_in_every_world_loads_and_keeps_that_worlds_ids() -> void:
	for name: String in _tilesets().keys():
		var merged := LevelLoader.legend_for(name)
		var chars: Array = merged.keys()
		chars.sort()
		var rows := _grid_using(chars, chars.size())
		var def := LevelLoader.from_dict({
			"id": "synthetic_%s" % name,
			"tileset": name,
			"fg": rows,
			"entities": [{"type": "player_spawn", "x": 0, "y": 0}],
		})
		ok(def.ok(), "%s: %s" % [name, ", ".join(def.errors)])
		if not def.ok():
			continue
		eq(def.tileset, name, "the def must remember which world it read")
		for i in chars.size():
			var ch := String(chars[i])
			eq(def.world.get_fg(i, 0), int(merged[ch]),
				"tileset '%s': '%s' loaded as tile %d, legend says %d"
					% [name, ch, def.world.get_fg(i, 0), int(merged[ch])])

## The same characters, different worlds, different tiles. This is the claim
## the design is built on, so it gets its own check rather than being implied.
func test_the_same_character_means_a_different_tile_in_a_different_world() -> void:
	var rows := ["#####", "#####"]
	var ents := [{"type": "player_spawn", "x": 1, "y": 0}]
	var jungle := LevelLoader.from_dict({
		"id": "synthetic_j", "fg": rows, "entities": ents})
	var ruins := LevelLoader.from_dict({
		"id": "synthetic_r", "tileset": "ruins", "fg": rows, "entities": ents})
	ok(jungle.ok() and ruins.ok(), "both synthetic levels must load")
	if not (jungle.ok() and ruins.ok()):
		return
	ne(jungle.world.get_fg(0, 0), ruins.world.get_fg(0, 0),
		"'#' must be the jungle's ground in one and the ruins' stone in the other")
	eq(jungle.world.get_fg(0, 0), 2, "'#' is grass_top in the jungle")
	eq(ruins.world.get_fg(0, 0), 220, "'#' is ruin_stone in the ruins")

func test_a_level_that_names_no_tileset_gets_the_default() -> void:
	var def := LevelLoader.from_dict({
		"id": "synthetic", "fg": ["##", "##"],
		"entities": [{"type": "player_spawn", "x": 0, "y": 0}]})
	eq(def.tileset, LevelLoader.default_tileset(),
		"a level with no 'tileset' key is a level in the default world")

func test_every_committed_level_names_a_world_that_exists() -> void:
	for id in LevelLoader.list_levels():
		var def := LevelLoader.load_level(id)
		ok(LevelLoader.tileset_names().has(def.tileset),
			"%s reads against tileset '%s', which the legend does not define"
				% [id, def.tileset])

# ------------------------------------------------------------ failing loudly

## Requirement: a character this world does not define must fail, not become
## empty space. `[` is the jungle's grass edge; the ruins have no such tile.
func test_a_character_from_another_world_fails_in_this_one() -> void:
	var jungle := LevelLoader.from_dict({
		"id": "synthetic", "fg": ["[##]", "####"],
		"entities": [{"type": "player_spawn", "x": 1, "y": 0}]})
	ok(jungle.ok(), "'[' is legal in the jungle: %s" % ", ".join(jungle.errors))

	var ruins := LevelLoader.from_dict({
		"id": "synthetic", "tileset": "ruins", "fg": ["[##]", "####"],
		"entities": [{"type": "player_spawn", "x": 1, "y": 0}]})
	not_ok(ruins.ok(), "'[' is not a ruins tile and must be rejected")
	var msg := ", ".join(ruins.errors)
	ok(msg.contains("["), "the error names the character: %s" % msg)
	ok(msg.contains("ruins"), "the error names the tileset: %s" % msg)

## The failure that matters is not the error string, it is that nobody can go
## on to use the grid. Before this change the unmapped character fell through
## to tile 0, so a mis-declared level loaded as a field of empty space with a
## message in a log — the exact shape of the six defects this project has
## already shipped. There is no grid to misuse.
func test_a_rejected_level_hands_back_no_world_at_all() -> void:
	var def := LevelLoader.from_dict({
		"id": "synthetic", "tileset": "ruins", "fg": ["[##]", "####"],
		"entities": [{"type": "player_spawn", "x": 1, "y": 0}]})
	not_ok(def.ok(), "precondition: the level is rejected")
	eq(def.world, null,
		"a rejected level must not hand back a grid where the bad character "
		+ "silently became empty space")

func test_every_bad_character_is_named_not_just_the_first() -> void:
	var def := LevelLoader.from_dict({
		"id": "synthetic", "tileset": "nest", "fg": ["[#]", "###"],
		"entities": [{"type": "player_spawn", "x": 1, "y": 0}]})
	not_ok(def.ok(), "precondition: the level is rejected")
	var msg := ", ".join(def.errors)
	ok(msg.contains("["), "the error names '[': %s" % msg)
	ok(msg.contains("]"), "the error names ']': %s" % msg)

func test_a_bad_character_on_the_background_layer_fails_too() -> void:
	var def := LevelLoader.from_dict({
		"id": "synthetic", "tileset": "deeps",
		"fg": ["##", "##"], "bg": ["[.", ".."],
		"entities": [{"type": "player_spawn", "x": 0, "y": 0}]})
	not_ok(def.ok(), "a background character must be checked like any other")

func test_a_level_naming_a_world_that_does_not_exist_fails() -> void:
	var def := LevelLoader.from_dict({
		"id": "synthetic", "tileset": "atlantis", "fg": ["##", "##"],
		"entities": [{"type": "player_spawn", "x": 0, "y": 0}]})
	not_ok(def.ok(), "an undefined tileset must not fall back to the jungle")
	var msg := ", ".join(def.errors)
	ok(msg.contains("atlantis"), "the error names the tileset asked for: %s" % msg)
	ok(msg.contains("jungle"), "and lists the ones that exist: %s" % msg)
	eq(def.world, null, "and hands back no grid")

## An empty string is a typo, not "unset". Falling back would load the level
## against the wrong world and say nothing.
func test_an_empty_tileset_name_fails_rather_than_defaulting() -> void:
	var def := LevelLoader.from_dict({
		"id": "synthetic", "tileset": "", "fg": ["##", "##"],
		"entities": [{"type": "player_spawn", "x": 0, "y": 0}]})
	not_ok(def.ok(), "\"tileset\": \"\" is a mistake, not the default world")

## The role characters mean the same *kind* of tile in every world: '#' is
## solid everywhere, '^' is a hazard everywhere, '=' is one-way everywhere.
##
## That is load-bearing for two tools this change does not touch.
## `tools/reachability.py` and `tools/build_hub.py` read the flat `legend`
## key, which is the jungle, and they read nothing but gameplay flags — so
## while this holds they get the right answer for a ruins level by accident.
## Bind 'r' to something solid in one world and they would silently model a
## wall as air, which is precisely the class of mistake ADR 005 exists to stop.
## Break this deliberately if a world needs it, but break those two tools in
## the same change.
func _flag_word(t: Dictionary) -> String:
	## A printable summary of one tile's gameplay flags, so a failure says what
	## actually differs instead of which of seven booleans did.
	var parts: Array[String] = []
	for f: String in ["solid", "oneway", "ladder", "water", "hazard", "breakable"]:
		if bool(t.get(f, false)):
			parts.append(f)
	if t.has("switch_group"):
		parts.append("switch_group")
	return "+".join(parts) if not parts.is_empty() else "none"

func test_a_role_character_has_the_same_gameplay_flags_in_every_world() -> void:
	var tiles := _declared_tiles()
	var jungle: Dictionary = _tilesets()["jungle"] as Dictionary
	for name: String in _tilesets().keys():
		if name == "jungle":
			continue
		var set_: Dictionary = _tilesets()[name] as Dictionary
		for ch: String in ROLE_CHARS:
			if not set_.has(ch) or not jungle.has(ch):
				continue
			var here: Dictionary = tiles.get(str(int(set_[ch])), {}) as Dictionary
			var there: Dictionary = tiles.get(str(int(jungle[ch])), {}) as Dictionary
			eq(_flag_word(here), _flag_word(there),
				"'%s' is %s as %s in '%s', but %s as %s in the jungle"
					% [ch, _flag_word(here), here.get("name", "?"), name,
						_flag_word(there), there.get("name", "?")])
