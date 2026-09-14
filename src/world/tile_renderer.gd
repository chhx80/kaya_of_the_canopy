class_name TileRenderer
extends Node2D
## Draws one tile layer straight from the atlas, culled to the visible screen.
## A TileMapLayer would need a TileSet resource authored in the editor; this is
## ~40 lines, fully deterministic, and lets the camera drive the cull.
##
## Animated tiles (data/tile_anim.json) are resolved here at draw time: a tile
## can swap to a frame from the fx atlas, be nudged a pixel, or be brightened.
## The tile *id* never changes, so collision cannot tell the difference.
##
## Tile *variants* (assets/tiles/variants.json) are resolved once at setup, for
## the same reason and with the same guarantee: the id stays authored, only the
## atlas cell moves. See src/world/tile_variants.gd.

const TS := TileData4.TILE_SIZE

var world: TileWorld = null
var layer := "fg"                       ## "fg" or "bg"
var atlas: Texture2D = null
var modulate_color := Color.WHITE
var view := Rect2(0, 0, 400, 240)

var anim: TileAnim = null
var fx_atlas: Texture2D = null
## Atlas cell per tile of this layer, resolved from neighbours and position.
var _cells: PackedInt32Array = PackedInt32Array()
## Animated ids actually inside the cull, so a level with no water pays nothing.
var _live: PackedInt32Array = PackedInt32Array()
var _live_bounds := Rect2i()
var _live_valid := false
var _signature := 0

func setup(w: TileWorld, which: String) -> void:
	world = w
	layer = which
	atlas = load("res://assets/tiles/tileset.png")
	var resolved := TileVariants.for_world(w)
	_cells = resolved.bg if which == "bg" else resolved.fg
	_setup_anim()
	_refresh_live()
	queue_redraw()

## Animation is strictly optional: a missing table or a missing fx atlas leaves
## every tile exactly as it was drawn before Phase 5.
func _setup_anim() -> void:
	anim = TileAnim.shared()
	if anim == null or not anim.has_any():
		return
	if anim.atlas_path != "" and ResourceLoader.exists(anim.atlas_path):
		fx_atlas = load(anim.atlas_path)
	else:
		push_warning("TileRenderer: no fx atlas at '%s'; tiles keep their still art"
			% anim.atlas_path)

func set_view(r: Rect2) -> void:
	if r != view:
		view = r
		_refresh_live()
		queue_redraw()

func _bounds() -> Rect2i:
	if world == null:
		return Rect2i()
	var x0 := maxi(0, int(floor(view.position.x / TS)) - 1)
	var y0 := maxi(0, int(floor(view.position.y / TS)) - 1)
	var x1 := mini(world.width - 1, int(ceil((view.position.x + view.size.x) / TS)) + 1)
	var y1 := mini(world.height - 1, int(ceil((view.position.y + view.size.y) / TS)) + 1)
	return Rect2i(x0, y0, x1 - x0, y1 - y0)

func _refresh_live() -> void:
	if anim == null or not anim.has_any() or world == null:
		_live = PackedInt32Array()
		return
	var b := _bounds()
	if _live_valid and b == _live_bounds:
		return
	_live_bounds = b
	_live_valid = true
	_live = PackedInt32Array()
	for ty in range(b.position.y, b.position.y + b.size.y + 1):
		for tx in range(b.position.x, b.position.x + b.size.x + 1):
			var id := world.get_bg(tx, ty) if layer == "bg" else world.get_fg(tx, ty)
			if id > 0 and anim.animated(id) and not _live.has(id):
				_live.append(id)

## Repaint only when an animated tile on this screen has actually changed —
## a still screen costs nothing, and a screen of water repaints a few times a
## second rather than sixty.
func _process(_delta: float) -> void:
	if _live.is_empty():
		return
	var sig := anim.signature(_live)
	if sig != _signature:
		_signature = sig
		queue_redraw()

func _draw() -> void:
	if world == null or atlas == null:
		return
	var b := _bounds()
	var cols := world.data.atlas_columns
	var animating := not _live.is_empty()
	for ty in range(b.position.y, b.position.y + b.size.y + 1):
		for tx in range(b.position.x, b.position.x + b.size.x + 1):
			var id := world.get_bg(tx, ty) if layer == "bg" else world.get_fg(tx, ty)
			if id <= 0:
				continue
			# Which cell of the atlas this tile is painted from. Switch blocks
			# carry no variants, so ghosting still works off the id itself.
			var art := id
			var vi := ty * world.width + tx
			if vi < _cells.size():
				art = _cells[vi]
			if layer == "fg" and world.flags_at(tx, ty) & TileData4.Flag.SWITCHED:
				# Ghost the inactive half of a switch pair instead of hiding it.
				if not world.is_solid(tx, ty):
					art = _ghost_of(id)
			var tex := atlas
			var src := Rect2(float((art % cols) * TS), float((art / cols) * TS), TS, TS)
			var dst := Vector2(tx * TS, ty * TS)
			var col := modulate_color
			if animating and anim.animated(id):
				var frame := anim.frame_index(id)
				if frame >= 0 and fx_atlas != null:
					tex = fx_atlas
					src = anim.frame_region(frame)
				dst += anim.offset(id, ty)
				var k := anim.tint(id)
				if not is_equal_approx(k, 1.0):
					col = Color(col.r * k, col.g * k, col.b * k, col.a)
			draw_texture_rect_region(tex, Rect2(dst, Vector2(TS, TS)), src, col)

## Which animated tile ids are inside the current cull. Empty means this layer
## costs nothing per frame.
func live_animated_ids() -> PackedInt32Array:
	return _live

func _ghost_of(id: int) -> int:
	match id:
		11: return 26
		26: return 11
		12: return 27
		27: return 12
	return id
