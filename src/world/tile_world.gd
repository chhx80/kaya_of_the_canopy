class_name TileWorld
extends RefCounted
## The collision view of a level: a grid of tile ids plus the live switch state.
## Deliberately free of nodes and textures so it can be built in a unit test.

const TS := TileData4.TILE_SIZE

var width := 0
var height := 0
var fg: PackedInt32Array = PackedInt32Array()   ## collision layer
var bg: PackedInt32Array = PackedInt32Array()   ## decoration only
var data: TileData4 = null
## switch_states[group] = true/false. Group 0 is unused.
var switch_states: Dictionary = {1: true, 2: false}
## Tiles broken at runtime (breakable crates). Keyed by y * width + x.
var _broken: Dictionary = {}

func _init(w: int = 0, h: int = 0, tile_data: TileData4 = null) -> void:
	data = tile_data if tile_data != null else TileData4.shared()
	resize(w, h)

func resize(w: int, h: int) -> void:
	width = w
	height = h
	fg.resize(w * h)
	bg.resize(w * h)
	fg.fill(0)
	bg.fill(0)

## Build from ASCII-ish rows of comma-free tile ids (used by tests).
static func from_rows(rows: Array, tile_data: TileData4 = null) -> TileWorld:
	var h := rows.size()
	var w := 0
	for r: Array in rows:
		w = maxi(w, r.size())
	var world := TileWorld.new(w, h, tile_data)
	for y in h:
		var row: Array = rows[y]
		for x in row.size():
			world.set_fg(x, y, int(row[x]))
	return world

func idx(x: int, y: int) -> int:
	return y * width + x

func in_bounds(x: int, y: int) -> bool:
	return x >= 0 and y >= 0 and x < width and y < height

func set_fg(x: int, y: int, id: int) -> void:
	if in_bounds(x, y):
		fg[idx(x, y)] = id

func get_fg(x: int, y: int) -> int:
	if not in_bounds(x, y):
		return -1
	if _broken.has(idx(x, y)):
		return 0
	return fg[idx(x, y)]

func set_bg(x: int, y: int, id: int) -> void:
	if in_bounds(x, y):
		bg[idx(x, y)] = id

func get_bg(x: int, y: int) -> int:
	return bg[idx(x, y)] if in_bounds(x, y) else 0

func break_tile(x: int, y: int) -> bool:
	if not in_bounds(x, y):
		return false
	if flags_at(x, y) & TileData4.Flag.BREAKABLE == 0:
		return false
	_broken[idx(x, y)] = true
	return true

func reset_broken() -> void:
	_broken.clear()

func toggle_switch(group: int) -> void:
	switch_states[group] = not bool(switch_states.get(group, false))

func set_switch(group: int, on: bool) -> void:
	switch_states[group] = on

## Raw flags of the tile at grid coords. Out-of-bounds sides are solid walls;
## out-of-bounds below is open so falling off the map can kill you.
func flags_at(x: int, y: int) -> int:
	if y >= height:
		return 0
	if x < 0 or x >= width or y < 0:
		return TileData4.Flag.SOLID
	var id := get_fg(x, y)
	return data.flags_of(id)

## SOLID after resolving switch groups.
func is_solid(x: int, y: int) -> bool:
	var f := flags_at(x, y)
	if f & TileData4.Flag.SOLID == 0:
		return false
	if f & TileData4.Flag.SWITCHED:
		var id := get_fg(x, y)
		if id < 0:
			return true
		var grp := data.switch_group[id]
		var want := data.switch_state[id] == 1
		return bool(switch_states.get(grp, false)) == want
	return true

func is_oneway(x: int, y: int) -> bool:
	return flags_at(x, y) & TileData4.Flag.ONEWAY != 0

func is_ladder(x: int, y: int) -> bool:
	return flags_at(x, y) & TileData4.Flag.LADDER != 0

func is_water(x: int, y: int) -> bool:
	return flags_at(x, y) & TileData4.Flag.WATER != 0

func is_hazard(x: int, y: int) -> bool:
	return flags_at(x, y) & TileData4.Flag.HAZARD != 0

func is_breakable(x: int, y: int) -> bool:
	return flags_at(x, y) & TileData4.Flag.BREAKABLE != 0

func pixel_width() -> int:
	return width * TS

func pixel_height() -> int:
	return height * TS
