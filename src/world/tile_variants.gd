class_name TileVariants
extends RefCounted
## Which atlas cell a tile is *drawn* from — phase 2 of docs/art-direction.md.
##
## The gameplay id a level authors never changes. `TileWorld` still stores it,
## `is_solid()` still reads it, and every collision test sees exactly the array
## it saw before. What changes is the cell the renderer blits:
##
##   * one of several interchangeable paintings of the same fill, picked by a
##     hash of the tile's position — so a wall never repeats visibly, and the
##     choice is stable across frames, reloads and screen flips;
##   * dressed with the edges and inside corners its eight neighbours imply,
##     reduced to the 47-case blob set;
##   * and, on the background layer only, the occasional root, hanging vine,
##     crack or moss patch.
##
## The table is generated: `tools/art/tiles.py` paints the variants into the
## atlas and writes `assets/tiles/variants.json` next to it. Nothing here is
## authored, which is the point — `levels/*.json` never mentions a variant.
##
## Pure and node-free, so tools/test.sh can check the whole variant set without
## a scene tree (ADR 003).

const PATH := "res://assets/tiles/variants.json"

## Neighbour bits, clockwise from north. Must match tools/art/tiles.py.
const BIT_N := 1
const BIT_NE := 2
const BIT_E := 4
const BIT_SE := 8
const BIT_S := 16
const BIT_SW := 32
const BIT_W := 64
const BIT_NW := 128
## Every neighbour is the same material: the interior case, and the only one a
## tile without autotiling has.
const MASK_FULL := 255

## The resolved atlas cell for every tile of one level, both layers.
class Resolved extends RefCounted:
	var width := 0
	var height := 0
	var fg: PackedInt32Array = PackedInt32Array()
	var bg: PackedInt32Array = PackedInt32Array()

	func cell(layer: String, x: int, y: int, fallback: int) -> int:
		if x < 0 or y < 0 or x >= width or y >= height:
			return fallback
		var a: PackedInt32Array = bg if layer == "bg" else fg
		var i := y * width + x
		return a[i] if i < a.size() else fallback

## tile id -> material group name. Includes ids with no variants of their own
## (the authored grass edges), because they still have to read as earth.
var group_of: Dictionary = {}
## tile id -> { cases, autotile, decor, decor_permille }
var _tiles: Dictionary = {}
var loaded := false

static var _shared: TileVariants = null
static var _cache_world: TileWorld = null
static var _cache: Resolved = null

static func shared() -> TileVariants:
	if _shared == null:
		_shared = TileVariants.new()
		_shared.load_from(PATH)
	return _shared

## See TileData4.release() — same reason.
static func release() -> void:
	_shared = null
	_cache_world = null
	_cache = null

## The resolved map for a level, computed once. LevelLoader asks for it at load
## and both TileRenderers ask for it again when they set up; they all get the
## same object, so the neighbour sweep happens exactly once per level.
static func for_world(world: TileWorld) -> Resolved:
	if world == null:
		return Resolved.new()
	if _cache != null and _cache_world == world:
		return _cache
	var v := shared()
	var r := Resolved.new()
	r.width = world.width
	r.height = world.height
	r.fg = v.resolve(world, "fg")
	r.bg = v.resolve(world, "bg")
	_cache_world = world
	_cache = r
	return r

# ------------------------------------------------------------------ loading
## A missing or unreadable manifest is not an error: every tile then draws from
## its own atlas cell, exactly as it did before phase 2.
func load_from(path: String) -> bool:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return false
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("TileVariants: %s is not a JSON object" % path)
		return false
	return load_from_dict(parsed as Dictionary)

func load_from_dict(d: Dictionary) -> bool:
	group_of.clear()
	_tiles.clear()
	var groups: Dictionary = d.get("groups", {})
	for k: String in groups.keys():
		group_of[int(k)] = String(groups[k])
	var tiles: Dictionary = d.get("tiles", {})
	for k: String in tiles.keys():
		var src: Dictionary = tiles[k]
		var cases: Dictionary = {}
		var raw_cases: Dictionary = src.get("cases", {})
		for mk: String in raw_cases.keys():
			var ids: Array = raw_cases[mk]
			var list := PackedInt32Array()
			for i: Variant in ids:
				list.append(int(i))
			cases[int(mk)] = list
		var decor: Array = []
		for e: Variant in src.get("decor", []):
			var ed: Dictionary = e
			decor.append({"index": int(ed.get("index", 0)),
				"needs": String(ed.get("needs", "any"))})
		_tiles[int(k)] = {
			"cases": cases,
			"autotile": bool(src.get("autotile", false)),
			"decor": decor,
			"decor_permille": int(src.get("decor_permille", 0)),
		}
	loaded = not _tiles.is_empty()
	return loaded

func has_any() -> bool:
	return loaded

func variant_ids() -> Array:
	var out: Array = _tiles.keys()
	out.sort()
	return out

func record(id: int) -> Dictionary:
	return _tiles.get(id, {})

# ------------------------------------------------------------------ masking
## Reduce a raw eight-neighbour mask to one of the 47 blob cases: a diagonal
## only changes the drawing when both cardinals beside it are present too.
static func canon_mask(raw: int) -> int:
	var m := raw & (BIT_N | BIT_E | BIT_S | BIT_W)
	if raw & BIT_N and raw & BIT_E and raw & BIT_NE:
		m |= BIT_NE
	if raw & BIT_E and raw & BIT_S and raw & BIT_SE:
		m |= BIT_SE
	if raw & BIT_S and raw & BIT_W and raw & BIT_SW:
		m |= BIT_SW
	if raw & BIT_W and raw & BIT_N and raw & BIT_NW:
		m |= BIT_NW
	return m

## Position hash. Deterministic and stateless, which is what makes a variant
## survive a reload, a screen flip and a repaint of the same frame.
static func hash_at(x: int, y: int, salt: int) -> int:
	var h := (x * 73856093) ^ (y * 19349663) ^ (salt * 83492791)
	h &= 0x7fffffff
	h = ((h ^ (h >> 15)) * 2246822519) & 0x7fffffff
	h = ((h ^ (h >> 13)) * 3266489917) & 0x7fffffff
	return h ^ (h >> 16)

# ---------------------------------------------------------------- resolution
## The atlas cell for every tile of one layer. Cells with no variants — and
## every tile at all if the manifest is missing — map to their own id.
func resolve(world: TileWorld, layer: String) -> PackedInt32Array:
	var out := PackedInt32Array()
	if world == null:
		return out
	out.resize(world.width * world.height)
	for y in world.height:
		for x in world.width:
			out[y * world.width + x] = cell_for(world, layer, x, y)
	return out

func cell_for(world: TileWorld, layer: String, x: int, y: int) -> int:
	var id := world.get_bg(x, y) if layer == "bg" else world.get_fg(x, y)
	if id <= 0 or not _tiles.has(id):
		return maxi(id, 0)
	var rec: Dictionary = _tiles[id]
	var cases: Dictionary = rec["cases"]
	var mask := MASK_FULL
	if bool(rec["autotile"]):
		mask = canon_mask(_neighbours(world, layer, x, y, String(group_of.get(id, ""))))
	if not cases.has(mask):
		mask = MASK_FULL
	var h := hash_at(x, y, id)
	if mask == MASK_FULL:
		var deco := _decor_for(world, rec, x, y, id)
		if deco >= 0:
			return deco
	var list: PackedInt32Array = cases[mask]
	return list[h % list.size()] if list.size() > 0 else id

## Which of the eight neighbours are the same material. Out of bounds counts as
## the same, so the map border is not mistaken for a cliff face.
func _neighbours(world: TileWorld, layer: String, x: int, y: int, grp: String) -> int:
	var raw := 0
	if _same(world, layer, x, y - 1, grp): raw |= BIT_N
	if _same(world, layer, x + 1, y - 1, grp): raw |= BIT_NE
	if _same(world, layer, x + 1, y, grp): raw |= BIT_E
	if _same(world, layer, x + 1, y + 1, grp): raw |= BIT_SE
	if _same(world, layer, x, y + 1, grp): raw |= BIT_S
	if _same(world, layer, x - 1, y + 1, grp): raw |= BIT_SW
	if _same(world, layer, x - 1, y, grp): raw |= BIT_W
	if _same(world, layer, x - 1, y - 1, grp): raw |= BIT_NW
	return raw

func _same(world: TileWorld, layer: String, x: int, y: int, grp: String) -> bool:
	if x < 0 or y < 0 or x >= world.width or y >= world.height:
		return true
	var id := world.get_bg(x, y) if layer == "bg" else world.get_fg(x, y)
	return String(group_of.get(id, "")) == grp

# ------------------------------------------------------------------- decor
## Roots, vines, cracks and moss, at `decor_permille` of interior cells.
## `needs` gates each one on the *foreground* around the cell, so a vine hangs
## off something and a root sits on something.
func _decor_for(world: TileWorld, rec: Dictionary, x: int, y: int, id: int) -> int:
	var permille: int = rec["decor_permille"]
	var decor: Array = rec["decor"]
	if permille <= 0 or decor.is_empty():
		return -1
	var h := hash_at(x, y, id + 977)
	if h % 1000 >= permille:
		return -1
	var ok: Array = []
	for e: Variant in decor:
		var ed: Dictionary = e
		if _decor_fits(world, String(ed["needs"]), x, y):
			ok.append(int(ed["index"]))
	if ok.is_empty():
		return -1
	return int(ok[(h / 1000) % ok.size()])

func _decor_fits(world: TileWorld, needs: String, x: int, y: int) -> bool:
	match needs:
		"ceiling":
			return _fg_solid(world, x, y - 1) and not _fg_solid(world, x, y)
		"floor":
			return _fg_solid(world, x, y + 1)
	return true

static func _fg_solid(world: TileWorld, x: int, y: int) -> bool:
	if x < 0 or y < 0 or x >= world.width or y >= world.height:
		return false
	return world.data.flags_of(world.get_fg(x, y)) & TileData4.Flag.SOLID != 0
