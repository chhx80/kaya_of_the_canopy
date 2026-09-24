class_name LevelLoader
extends RefCounted
## Parses levels/<id>.json into a TileWorld plus an entity list.
## Pure — tests/test_level_validity.gd loads every level through here with no
## scene tree in sight.

const LEVEL_DIR := "res://levels"
const LEGEND_PATH := "res://data/level_legend.json"

## The whole legend document, parsed once. `_resolved` caches one merged
## char -> id map per tileset name, because from_dict() asks for it per level.
static var _doc: Dictionary = {}
static var _resolved: Dictionary = {}

class LevelDef extends RefCounted:
	var id := ""
	var display_name := ""
	var music := ""
	var world: TileWorld = null
	## Atlas cells for both layers, derived from the eight neighbours and the
	## tile position (docs/art-direction.md phase 2). Purely cosmetic: `world`
	## still holds the ids the level authored, and collision reads those.
	var variants: TileVariants.Resolved = null
	var entities: Array = []
	var spawn := Vector2(16, 16)
	var next_level := ""
	## Top-down maps (the hub) have no gravity, so the "spawn needs a floor"
	## rule does not apply to them.
	var topdown := false
	## Which per-world legend this level's characters were read against
	## (ADR 002). Always a name data/level_legend.json defines; a level naming
	## one it does not define is an error, not a fallback.
	var tileset := ""
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

## The parsed data/level_legend.json, cached.
static func legend_doc() -> Dictionary:
	if _doc.is_empty():
		var f := FileAccess.open(LEGEND_PATH, FileAccess.READ)
		if f:
			var d: Variant = JSON.parse_string(f.get_as_text())
			f.close()
			if typeof(d) == TYPE_DICTIONARY:
				_doc = d as Dictionary
	return _doc

## The tileset a level gets when it names none.
static func default_tileset() -> String:
	return String(legend_doc().get("default_tileset", "jungle"))

## Every tileset name a level may name, sorted.
static func tileset_names() -> PackedStringArray:
	var raw: Variant = legend_doc().get("tilesets", {})
	var out := PackedStringArray()
	if typeof(raw) != TYPE_DICTIONARY:
		return out
	for k: String in (raw as Dictionary).keys():
		out.append(k)
	out.sort()
	return out

## char -> tile id for one world: the shared characters plus that world's own.
## Empty for a name the file does not define, which is how from_dict() tells a
## typo'd tileset from a real one.
static func legend_for(name: String) -> Dictionary:
	if _resolved.has(name):
		return _resolved[name] as Dictionary
	var doc := legend_doc()
	var sets: Variant = doc.get("tilesets", {})
	if typeof(sets) != TYPE_DICTIONARY or not (sets as Dictionary).has(name):
		return {}
	var merged: Dictionary = {}
	var shared: Variant = doc.get("shared", {})
	if typeof(shared) == TYPE_DICTIONARY:
		merged.merge(shared as Dictionary)
	var own: Variant = (sets as Dictionary)[name]
	if typeof(own) == TYPE_DICTIONARY:
		merged.merge(own as Dictionary, true)
	_resolved[name] = merged
	return merged

## The default world's legend. Kept because callers outside this file (and
## tools/reachability.py, tools/build_hub.py, which read the JSON directly)
## predate per-world legends and only ever look at jungle levels.
static func legend() -> Dictionary:
	return legend_for(default_tileset())

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
		# A proof tape is not a level. They live in proofs/ for exactly this
		# reason, but the rule is repeated here because the consequence of one
		# slipping back in is severe and silent: every id this returns must be
		# completed before the hub's requires_all door opens, so a stray
		# levels/x.tape.json makes the FINAL DOOR UNOPENABLE in a shipped build.
		if f.ends_with(".json") and not f.ends_with(".tape.json"):
			out.append(f.get_basename())
		f = d.get_next()
	d.list_dir_end()
	out.sort()
	return out

static func load_level(id: String) -> LevelDef:
	return load_path(level_path(id), id)


## Load a level from an explicit path. Used for levels that are built but not yet
## part of the game -- staging/ holds those, and staging/ is deliberately outside
## LEVEL_DIR so list_levels() never sees them. A hub with doors to twenty levels
## that do not exist is not something to ship while they do not exist.
static func load_path(path: String, id: String = "") -> LevelDef:
	var def := LevelDef.new()
	def.id = id if id != "" else path.get_file().get_basename()
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
	# ADR 002: the characters in the grid mean whatever this level's world says
	# they mean. No "tileset" key is the jungle, which is why the five levels
	# that predate per-world legends are byte-identical.
	def.tileset = String(d.get("tileset", default_tileset()))
	var lg := legend_for(def.tileset)
	if lg.is_empty():
		def.errors.append("level '%s' names tileset '%s', which data/level_legend.json does not define (it defines %s)"
			% [def.id, def.tileset, ", ".join(tileset_names())])
		return def

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
	if not unknown.is_empty():
		# Hand back no world at all. An unmapped character used to fall through
		# `lg.get(ch, 0)` to tile 0, so a mis-declared world would have loaded
		# as a level made almost entirely of empty space -- playable-looking,
		# wrong, and silent. `errors` alone is not enough, because a caller
		# that forgets ok() would get that grid; nothing may.
		var bad: Array = unknown.keys()
		bad.sort()
		for ch: String in bad:
			def.errors.append("level '%s' (tileset '%s') uses '%s', which that tileset does not define in data/level_legend.json"
				% [def.id, def.tileset, ch])
		def.world = null
		return def
	def.world = world
	# Resolve the tile variants once, here, while the whole grid is in hand.
	# The renderers ask for the same map when they set up and get this one back.
	def.variants = TileVariants.for_world(world)

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
