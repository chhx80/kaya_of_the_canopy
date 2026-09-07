class_name TileData4
extends RefCounted
## Loads data/tiles.json into flag bitmasks. Pure data, no scene tree — so the
## collision tests can build a world without booting the game.

enum Flag {
	NONE      = 0,
	SOLID     = 1 << 0,
	ONEWAY    = 1 << 1,
	LADDER    = 1 << 2,
	WATER     = 1 << 3,
	HAZARD    = 1 << 4,
	BREAKABLE = 1 << 5,
	SURFACE   = 1 << 6,   ## top row of a body of water
	SWITCHED  = 1 << 7,   ## solidity depends on a switch group
}

const TILE_SIZE := 16
const PATH := "res://data/tiles.json"

var flags: PackedInt32Array = PackedInt32Array()
var names: PackedStringArray = PackedStringArray()
## For SWITCHED tiles: group number (1..N) and the group state that makes it solid.
var switch_group: PackedInt32Array = PackedInt32Array()
var switch_state: PackedInt32Array = PackedInt32Array()
var atlas_columns := 16

static var _shared: TileData4 = null

static func shared() -> TileData4:
	if _shared == null:
		_shared = TileData4.new()
		_shared.load_from(PATH)
	return _shared

## See PixelFont.release() — same reason.
static func release() -> void:
	_shared = null

func load_from(path: String) -> bool:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("TileData: cannot open %s" % path)
		return false
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("TileData: %s is not a JSON object" % path)
		return false
	return load_from_dict(parsed)

func load_from_dict(d: Dictionary) -> bool:
	atlas_columns = int(d.get("atlas_columns", 16))
	var tiles: Dictionary = d.get("tiles", {})
	var max_id := 0
	for k: String in tiles.keys():
		max_id = maxi(max_id, int(k))
	flags.resize(max_id + 1)
	names.resize(max_id + 1)
	switch_group.resize(max_id + 1)
	switch_state.resize(max_id + 1)
	for k: String in tiles.keys():
		var id := int(k)
		var t: Dictionary = tiles[k]
		var fl := 0
		if t.get("solid", false): fl |= Flag.SOLID
		if t.get("oneway", false): fl |= Flag.ONEWAY
		if t.get("ladder", false): fl |= Flag.LADDER
		if t.get("water", false): fl |= Flag.WATER
		if t.get("hazard", false): fl |= Flag.HAZARD
		if t.get("breakable", false): fl |= Flag.BREAKABLE
		if t.get("water_surface", false): fl |= Flag.SURFACE
		if t.has("switch_group"):
			fl |= Flag.SWITCHED
			switch_group[id] = int(t["switch_group"])
			switch_state[id] = 1 if t.get("switch_state", true) else 0
		flags[id] = fl
		names[id] = String(t.get("name", "tile_%d" % id))
	return true

func flags_of(id: int) -> int:
	if id < 0 or id >= flags.size():
		return 0
	return flags[id]

func name_of(id: int) -> String:
	if id < 0 or id >= names.size():
		return "?"
	return names[id]

## Atlas coordinate for a tile id, for TileSet setup.
func atlas_coords(id: int) -> Vector2i:
	return Vector2i(id % atlas_columns, id / atlas_columns)

func count() -> int:
	return flags.size()
