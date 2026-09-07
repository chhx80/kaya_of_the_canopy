extends TestCase
## Runs over every levels/*.json. A level that fails here would waste a
## playtest, so these are structural rather than stylistic checks.

const TS := TileData4.TILE_SIZE

var ids: PackedStringArray

func before_each() -> void:
	ids = LevelLoader.list_levels()

func test_there_is_at_least_one_level() -> void:
	gt(float(ids.size()), 0.0, "levels/ must not be empty")

func test_every_level_parses_cleanly() -> void:
	for id in ids:
		var def := LevelLoader.load_level(id)
		ok(def.ok(), "%s: %s" % [id, ", ".join(def.errors)])

func test_every_level_has_a_spawn_on_solid_ground() -> void:
	for id in ids:
		var def := LevelLoader.load_level(id)
		if not def.ok():
			continue
		eq(def.entities_of("player_spawn").size(), 1, "%s needs exactly one spawn" % id)
		var tx := int(def.spawn.x / TS)
		var ty := int(def.spawn.y / TS)
		not_ok(def.world.is_solid(tx, ty), "%s spawns inside a wall" % id)
		if def.topdown:
			continue   # no gravity on the overworld
		# There has to be a floor somewhere below the spawn, within a screen.
		var floor_found := false
		for y in range(ty, mini(def.world.height, ty + 15)):
			if def.world.is_solid(tx, y):
				floor_found = true
				break
		ok(floor_found, "%s spawns over a bottomless drop" % id)

func test_every_level_is_a_whole_number_of_screens_or_smaller() -> void:
	for id in ids:
		var def := LevelLoader.load_level(id)
		if not def.ok():
			continue
		gt(float(def.world.width), 0.0, "%s has width" % id)
		gt(float(def.world.height), 0.0, "%s has height" % id)
		lt(float(def.world.width), 401.0, "%s is unreasonably wide" % id)

func test_every_row_is_the_same_length() -> void:
	for id in ids:
		var f := FileAccess.open(LevelLoader.level_path(id), FileAccess.READ)
		if f == null:
			continue
		var d: Variant = JSON.parse_string(f.get_as_text())
		f.close()
		var rows: Array = (d as Dictionary).get("fg", [])
		if rows.is_empty():
			continue
		var w := String(rows[0]).length()
		for i in rows.size():
			eq(String(rows[i]).length(), w, "%s fg row %d is ragged" % [id, i])

func test_every_playable_level_has_a_way_out() -> void:
	for id in ids:
		if id == "hub":
			continue
		var def := LevelLoader.load_level(id)
		if not def.ok():
			continue
		var exits := def.entities_of("exit").size() + def.entities_of("boss_exit").size()
		gt(float(exits), 0.0, "%s has no exit — it cannot be completed" % id)

func test_every_locked_door_has_a_key_of_its_colour_in_the_level() -> void:
	for id in ids:
		var def := LevelLoader.load_level(id)
		if not def.ok():
			continue
		for color in ["yellow", "red", "cyan"]:
			var doors := def.entities_of("door_%s" % color).size()
			var keys := def.entities_of("key_%s" % color).size()
			if doors == 0:
				continue
			ok(keys >= doors,
				"%s has %d %s door(s) but only %d %s key(s)" % [id, doors, color, keys, color])

func test_every_boss_level_pairs_its_boss_with_a_gate() -> void:
	for id in ids:
		var def := LevelLoader.load_level(id)
		if not def.ok():
			continue
		var bosses := 0
		for e: Dictionary in def.entities:
			if String(e.get("type", "")).begins_with("boss_") \
					and String(e.get("type", "")) != "boss_exit":
				bosses += 1
		if bosses == 0:
			continue
		gt(float(def.entities_of("boss_exit").size()), 0.0,
			"%s has a boss but no boss_exit for it to open" % id)

func test_every_transform_pad_names_a_form_that_exists() -> void:
	for id in ids:
		var def := LevelLoader.load_level(id)
		if not def.ok():
			continue
		for e: Dictionary in def.entities:
			var t := String(e.get("type", ""))
			if not t.begins_with("pad_"):
				continue
			var form_id := t.substr(4)
			ok(FileAccess.file_exists("res://data/forms/%s.json" % form_id),
				"%s has a pad for unknown form '%s'" % [id, form_id])

func test_every_level_a_hub_gateway_points_at_actually_exists() -> void:
	var hub := LevelLoader.load_level("hub")
	if not hub.ok():
		return
	var doors := hub.entities_of("hub_door")
	gt(float(doors.size()), 0.0, "the hub needs gateways")
	for d: Dictionary in doors:
		var target := String(d.get("level", ""))
		ok(FileAccess.file_exists(LevelLoader.level_path(target)),
			"hub gateway points at missing level '%s'" % target)
		var req := String(d.get("requires", ""))
		if req != "":
			ok(FileAccess.file_exists(LevelLoader.level_path(req)),
				"hub gateway '%s' requires missing level '%s'" % [target, req])

## Anything the player has to physically stand in front of needs room for the
## player to be there. A one-tile gap looks like a doorway on the grid and is a
## solid wall in play — ROOT HOLLOW shipped with exactly that.
const MUST_REACH := [
	"key_yellow", "key_red", "key_cyan",
	"door_yellow", "door_red", "door_cyan",
	"exit", "boss_exit",
	"pad_frog", "pad_fish", "pad_bird", "pad_human",
	"switch_a", "switch_b",
	"heart", "gem",
]

func _player_tiles_tall() -> int:
	var f := FormBase.load_form("human")
	var hb: Dictionary = f.hitbox()
	return ceili(float(hb["h"]) / float(TS))

## Contiguous non-solid tiles going up from (tx, ty). Tiles a door will open
## count as passable, since that is the state the player meets them in.
func _clearance(world: TileWorld, tx: int, ty: int, opened: Dictionary) -> int:
	var n := 0
	var y := ty
	while y >= 0:
		if not opened.has(Vector2i(tx, y)) and world.is_solid(tx, y):
			break
		n += 1
		y -= 1
	return n

func test_a_door_is_at_least_as_tall_as_the_player() -> void:
	var need := _player_tiles_tall()
	ok(Door.HEIGHT_TILES >= need,
		"doors are %d tiles but the player needs %d" % [Door.HEIGHT_TILES, need])

func test_everything_the_player_must_reach_has_headroom() -> void:
	var need := _player_tiles_tall()
	for id in ids:
		var def := LevelLoader.load_level(id)
		if not def.ok() or def.topdown:
			continue
		# Doors punch their own hole, so treat those tiles as open.
		var opened := {}
		for e: Dictionary in def.entities:
			if not String(e.get("type", "")).begins_with("door_"):
				continue
			var dx := int(float(e["px"]) / TS)
			var dy := int(float(e["py"]) / TS)
			for i in Door.HEIGHT_TILES:
				opened[Vector2i(dx, dy - i)] = true
		for e: Dictionary in def.entities:
			var type := String(e.get("type", ""))
			if not MUST_REACH.has(type):
				continue
			var tx := int(float(e["px"]) / TS)
			var ty := int(float(e["py"]) / TS)
			var head := _clearance(def.world, tx, ty, opened)
			ok(head >= need,
				"%s: '%s' at tile (%d,%d) has %d tile(s) of headroom, needs %d"
					% [id, type, tx, ty, head, need])

## A standable tile with only one tile of headroom is a hole in the geometry:
## the player is two tiles tall, so it reads as a passage and behaves as a wall.
## Only flags pockets you could actually walk up to, so decorative gaps sealed
## inside solid rock do not trip it.
func test_no_standable_pockets_are_too_short_to_stand_in() -> void:
	var need := _player_tiles_tall()
	for id in ids:
		var def := LevelLoader.load_level(id)
		if not def.ok() or def.topdown:
			continue
		var w := def.world
		for y in w.height:
			for x in w.width:
				if w.is_solid(x, y) or not w.is_solid(x, y + 1):
					continue     # not a standable floor tile
				if _clearance(w, x, y, {}) >= need:
					continue     # roomy enough
				var approachable := false
				for dx in [-1, 1]:
					if not w.is_solid(x + dx, y) and _clearance(w, x + dx, y, {}) >= need:
						approachable = true
				ok(not approachable,
					"%s: tile (%d,%d) is standable with only %d tile(s) of headroom, "
					% [id, x, y, _clearance(w, x, y, {})]
					+ "reachable from beside it — the player cannot fit")

func test_unknown_legend_characters_are_reported() -> void:
	var def := LevelLoader.from_dict({
		"id": "synthetic",
		"fg": ["..Z..", "#####"],
		"entities": [{"type": "player_spawn", "x": 1, "y": 0}],
	})
	not_ok(def.ok(), "an unmapped character must fail validation")
	ok(", ".join(def.errors).contains("Z"), "the error names the bad character")

func test_a_level_without_a_spawn_is_rejected() -> void:
	var def := LevelLoader.from_dict({"id": "synthetic", "fg": ["#####"], "entities": []})
	not_ok(def.ok(), "no spawn means no level")
