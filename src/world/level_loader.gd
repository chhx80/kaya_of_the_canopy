class_name LevelLoader
extends RefCounted
## Parses levels/<id>.json into a TileWorld plus an entity list.
## Pure — tests/test_level_validity.gd loads every level through here with no
## scene tree in sight.

const LEVEL_DIR := "res://levels"
const LEGEND_PATH := "res://data/level_legend.json"

static var _legend: Dictionary = {}

class LevelDef extends RefCounted:
	var id := ""
	var display_name := ""
	var music := ""
	var world: TileWorld = null
	var entities: Array = []
	var spawn := Vector2(16, 16)
	var next_level := ""
	## Top-down maps (the hub) have no gravity, so the "spawn needs a floor"
	## rule does not apply to them.
	var topdown := false
	var errors: PackedStringArray = PackedStringArray()
	var warnings: PackedStringArray = PackedStringArray()

	func ok() -> bool:
		return errors.is_empty()

	func entities_of(type: String) -> Array:
		var out: Array = []
		for e: Dictionary in entities:
			if String(e.get("type", "")) == type:
				out.append(e)
		return out

static func legend() -> Dictionary:
	if _legend.is_empty():
		var f := FileAccess.open(LEGEND_PATH, FileAccess.READ)
		if f:
			var d: Variant = JSON.parse_string(f.get_as_text())
			f.close()
			if typeof(d) == TYPE_DICTIONARY:
				_legend = (d as Dictionary).get("legend", {})
	return _legend

static func level_path(id: String) -> String:
	return "%s/%s.json" % [LEVEL_DIR, id]

static func list_levels() -> PackedStringArray:
	var out := PackedStringArray()
	var d := DirAccess.open(LEVEL_DIR)
	if d == null:
		return out
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		if f.ends_with(".json"):
			out.append(f.get_basename())
		f = d.get_next()
	d.list_dir_end()
	out.sort()
	return out

static func load_level(id: String) -> LevelDef:
	var def := LevelDef.new()
	def.id = id
	var path := level_path(id)
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		def.errors.append("cannot open %s" % path)
		return def
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		def.errors.append("%s is not a JSON object" % path)
		return def
	return from_dict(parsed, def)

static func from_dict(d: Dictionary, def: LevelDef = null) -> LevelDef:
	if def == null:
		def = LevelDef.new()
		def.id = String(d.get("id", ""))
	def.display_name = String(d.get("name", def.id.to_upper()))
	def.music = String(d.get("music", ""))
	def.next_level = String(d.get("next_level", ""))
	def.topdown = bool(d.get("topdown", false))

	var fg_rows: Array = d.get("fg", [])
	var bg_rows: Array = d.get("bg", [])
	if fg_rows.is_empty():
		def.errors.append("level '%s' has no fg layer" % def.id)
		return def
	var h := fg_rows.size()
	var w := 0
	for r: Variant in fg_rows:
		w = maxi(w, String(r).length())

	var world := TileWorld.new(w, h)
	var lg := legend()
	var unknown := {}
	for y in h:
		var row := String(fg_rows[y])
		for x in row.length():
			var ch := row[x]
			if not lg.has(ch):
				unknown[ch] = true
			world.set_fg(x, y, int(lg.get(ch, 0)))
	for y in mini(h, bg_rows.size()):
		var row := String(bg_rows[y])
		for x in mini(w, row.length()):
			var ch := row[x]
			if not lg.has(ch):
				unknown[ch] = true
			world.set_bg(x, y, int(lg.get(ch, 0)))
	for ch: String in unknown.keys():
		def.errors.append("level '%s' uses '%s', which is not in data/level_legend.json" % [def.id, ch])
	def.world = world

	for raw: Variant in d.get("entities", []):
		if typeof(raw) != TYPE_DICTIONARY:
			continue
		var e: Dictionary = (raw as Dictionary).duplicate()
		e["type"] = String(e.get("type", ""))
		# Entity coordinates are tile coords; convert to pixels once, here.
		e["px"] = float(e.get("x", 0)) * TileData4.TILE_SIZE
		e["py"] = float(e.get("y", 0)) * TileData4.TILE_SIZE
		def.entities.append(e)

	var spawns := def.entities_of("player_spawn")
	if spawns.is_empty():
		def.errors.append("level '%s' has no player_spawn" % def.id)
	else:
		var s: Dictionary = spawns[0]
		def.spawn = Vector2(float(s["px"]), float(s["py"]))
	return def
