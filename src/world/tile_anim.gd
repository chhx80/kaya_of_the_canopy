class_name TileAnim
extends RefCounted
## Loads data/tile_anim.json: "how does this tile id move?".
##
## Pure data and pure maths — no nodes, no textures — so the whole table can be
## exercised by the headless unit suite. TileRenderer asks it three questions
## per drawn tile: which atlas frame, what draw offset, how bright.
##
## Animation never touches the tile *id*, so collision, the level format and
## every existing level are untouched by anything in here.

const PATH := "res://data/tile_anim.json"

## Guard rails rather than tunables. A sway wider than a couple of pixels would
## tear a tile away from its neighbours, and a stronger tint would burn through
## the palette. data/tile_anim.json is clamped to these on load.
const MAX_SWAY_PX := 2.0
const MAX_TINT := 0.5
## Redraw quantisation. 24 steps per cycle straddles every point where a rounded
## sine changes pixel, so the renderer repaints when something actually moved.
const SWAY_STEPS := 24
const TINT_STEPS := 8

var atlas_path := ""
var atlas_columns := 4
var cell := TileData4.TILE_SIZE
## Shared clock, advanced by the level so both tile layers stay in phase.
var time := 0.0

var _entries: Dictionary = {}          ## int tile id -> Dictionary
var _animated: PackedByteArray = PackedByteArray()

static var _shared: TileAnim = null

## See PixelFont.release() — same reason.
static func shared() -> TileAnim:
	if _shared == null:
		_shared = TileAnim.new()
		_shared.load_from(PATH)
	return _shared

static func release() -> void:
	_shared = null

# ---------------------------------------------------------------- loading
## A missing or broken table is not an error: the game simply draws still tiles.
func load_from(path: String) -> bool:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return false
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("TileAnim: %s is not a JSON object; tiles will not animate" % path)
		return false
	return load_from_dict(parsed)

func load_from_dict(d: Dictionary) -> bool:
	_entries.clear()
	atlas_path = String(d.get("atlas", ""))
	atlas_columns = maxi(1, int(d.get("atlas_columns", 4)))
	cell = maxi(1, int(d.get("cell", TileData4.TILE_SIZE)))
	var anims: Dictionary = d.get("animations", {})
	var max_id := 0
	for k: String in anims.keys():
		var id := int(k)
		if id < 0:
			continue
		var e := _sanitise(anims[k])
		if e.is_empty():
			continue
		_entries[id] = e
		max_id = maxi(max_id, id)
	_animated.resize(max_id + 1)
	_animated.fill(0)
	for id: int in _entries.keys():
		_animated[id] = 1
	return true

## Drops anything malformed and clamps the rest, so a bad edit degrades to a
## still tile instead of a tile that flies off the grid.
func _sanitise(raw: Variant) -> Dictionary:
	if typeof(raw) != TYPE_DICTIONARY:
		return {}
	var src: Dictionary = raw
	var out: Dictionary = {}
	var frames: Array = src.get("frames", [])
	var fps := float(src.get("fps", 0.0))
	if not frames.is_empty() and fps > 0.0:
		var clean: PackedInt32Array = PackedInt32Array()
		for v: Variant in frames:
			clean.append(maxi(0, int(v)))
		out["frames"] = clean
		out["fps"] = fps
	var sway: Dictionary = src.get("sway", {})
	if not sway.is_empty():
		var hz := float(sway.get("hz", 0.0))
		var px := clampf(float(sway.get("px", 0.0)), 0.0, MAX_SWAY_PX)
		if hz > 0.0 and px > 0.0:
			out["sway_x"] = 0.0 if String(sway.get("axis", "x")) == "y" else px
			out["sway_y"] = px if String(sway.get("axis", "x")) == "y" else 0.0
			out["sway_hz"] = hz
			out["sway_row_phase"] = float(sway.get("row_phase", 0.0))
	var tint: Dictionary = src.get("tint", {})
	if not tint.is_empty():
		var hz := float(tint.get("hz", 0.0))
		var amount := clampf(float(tint.get("amount", 0.0)), 0.0, MAX_TINT)
		if hz > 0.0 and amount > 0.0:
			out["tint_hz"] = hz
			out["tint_amount"] = amount
	return out

# ---------------------------------------------------------------- queries
func has_any() -> bool:
	return not _entries.is_empty()

func animated(id: int) -> bool:
	return id >= 0 and id < _animated.size() and _animated[id] == 1

func entry(id: int) -> Dictionary:
	return _entries.get(id, {})

func ids() -> PackedInt32Array:
	var out := PackedInt32Array()
	for id: int in _entries.keys():
		out.append(id)
	out.sort()
	return out

func advance(delta: float) -> void:
	time += delta

## Index into the fx atlas, or -1 when this tile keeps its own artwork.
func frame_index(id: int, at: float = -1.0) -> int:
	var e: Dictionary = _entries.get(id, {})
	if not e.has("frames"):
		return -1
	var t := time if at < 0.0 else at
	var frames: PackedInt32Array = e["frames"]
	var fps: float = e["fps"]
	var i := int(floor(t * fps)) % frames.size()
	if i < 0:
		i += frames.size()
	return frames[i]

## Where in the fx atlas that frame lives.
func frame_region(index: int) -> Rect2:
	var c := float(cell)
	return Rect2(float(index % atlas_columns) * c, float(index / atlas_columns) * c, c, c)

## Whole-pixel draw offset. Successive tile rows are phase-shifted so a wall of
## foliage ripples instead of sliding about as one sheet.
func offset(id: int, ty: int, at: float = -1.0) -> Vector2:
	var e: Dictionary = _entries.get(id, {})
	if not e.has("sway_hz"):
		return Vector2.ZERO
	var t := time if at < 0.0 else at
	var hz: float = e["sway_hz"]
	var phase: float = t * hz + float(ty) * float(e["sway_row_phase"])
	var s := sin(TAU * phase)
	return Vector2(roundf(float(e["sway_x"]) * s), roundf(float(e["sway_y"]) * s))

## Brightness multiplier — the flicker of a light source.
func tint(id: int, at: float = -1.0) -> float:
	var e: Dictionary = _entries.get(id, {})
	if not e.has("tint_hz"):
		return 1.0
	var t := time if at < 0.0 else at
	return 1.0 + float(e["tint_amount"]) * sin(TAU * t * float(e["tint_hz"]))

## A number that changes exactly when one of `visible_ids` looks different, so
## the renderer can sit still instead of repainting every tile every frame.
func signature(visible_ids: PackedInt32Array, at: float = -1.0) -> int:
	var t := time if at < 0.0 else at
	var h := 1
	for id in visible_ids:
		var e: Dictionary = _entries.get(id, {})
		if e.is_empty():
			continue
		h = (h * 31 + id) & 0x3FFFFFFF
		if e.has("frames"):
			h = (h * 31 + frame_index(id, t)) & 0x3FFFFFFF
		if e.has("sway_hz"):
			h = (h * 31 + int(floor(t * float(e["sway_hz"]) * SWAY_STEPS))) & 0x3FFFFFFF
		if e.has("tint_hz"):
			h = (h * 31 + int(floor(t * float(e["tint_hz"]) * TINT_STEPS))) & 0x3FFFFFFF
	return h
