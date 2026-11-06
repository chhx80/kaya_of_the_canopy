class_name TileRenderer
extends Node2D
## Draws one tile layer straight from the atlas. A TileMapLayer would need a
## TileSet resource authored in the editor; this is fully deterministic and
## code-built.
##
## Refit phase 2: the layer is drawn in CHUNKS of CHUNK x CHUNK tiles, each its
## own CanvasItem whose draw list is recorded once and kept. The scrolling
## camera moves the view every frame; under the screen flip this layer
## re-recorded its whole cull (~480 quads, measured ~1.5 ms) when the screen
## changed, and with a scrolling view that became every 16 px of travel, with
## both layers on the same tick — the worst physics tick of the frame-cost run
## went from 3.4 ms to 9.3 ms. Now scrolling costs no redraw at all: the
## renderer culls off-view chunks by their bounds, and a chunk is re-recorded
## only when something inside it changes (an animated tile's frame, a dissolve,
## a broken tile).
##
## Animated tiles (data/tile_anim.json) are resolved here at draw time: a tile
## can swap to a frame from the fx atlas, be nudged a pixel, or be brightened.
## The tile *id* never changes, so collision cannot tell the difference.
##
## Tile *variants* (assets/tiles/variants.json) are resolved once at setup, for
## the same reason and with the same guarantee: the id stays authored, only the
## atlas cell moves. See src/world/tile_variants.gd.
##
## Phase D, docs/plan-art-motion.md: switch-flip dissolve. `begin_dissolve()`
## is called by Level the instant a switch group flips (collision has already
## changed by then — `TileWorld.set_switch()` is synchronous) and cross-fades
## only the tiles that actually changed from their old ghost/solid art to the
## new one over DISSOLVE_TIME. Nothing here delays or previews collision: a
## body can stand on a tile mid-dissolve exactly as if the art had snapped.

const TS := TileData4.TILE_SIZE
## Tiles per chunk side. 8 x 8 is 128 px: a chunk re-record (an animated water
## frame, a broken crate) is ~64 quads, and a 400 x 240 view touches 12-20.
const CHUNK := 8
## 4 render frames at 60Hz — comfortably inside the Obsidian Heart's shortest
## reforge telegraph (1.05s, data/enemies/obsidian_heart.json's reforge_time).
const DISSOLVE_TIME := 4.0 / 60.0

## One recorded block of the layer.
class Chunk extends Node2D:
	var owner_layer: Node = null
	var rect := Rect2i()                         ## in tiles
	var anim_ids := PackedInt32Array()           ## animated ids inside it
	var sig := 0
	func _draw() -> void:
		owner_layer.call("_paint", self, rect)

var world: TileWorld = null
var layer := "fg"                       ## "fg" or "bg"
var atlas: Texture2D = null
var modulate_color := Color.WHITE:
	set(c):
		modulate_color = c
		refresh()
var view := Rect2(0, 0, 400, 240)

var anim: TileAnim = null
var fx_atlas: Texture2D = null
## Atlas cell per tile of this layer, resolved from neighbours and position.
var _cells: PackedInt32Array = PackedInt32Array()
## Animated ids actually inside the cull, so a level with no water pays nothing.
var _live: PackedInt32Array = PackedInt32Array()
var _chunks: Array[Chunk] = []
var _chunk_cols := 0
## Tile index (ty * world.width + tx) -> seconds remaining of its dissolve.
## Only ever populated for the fg layer — see begin_dissolve().
var _dissolve: Dictionary = {}

func setup(w: TileWorld, which: String) -> void:
	world = w
	layer = which
	atlas = load("res://assets/tiles/tileset.png")
	var resolved := TileVariants.for_world(w)
	_cells = resolved.bg if which == "bg" else resolved.fg
	_setup_anim()
	_build_chunks()
	_refresh_live()

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

## (Re)build the chunk grid. Called again by a boss that rewrites the layer
## (tide_maw.gd, stormcrest.gd re-run setup()), so it reuses what it can.
func _build_chunks() -> void:
	var cols := ceili(float(world.width) / CHUNK)
	var rows := ceili(float(world.height) / CHUNK)
	if _chunks.size() != cols * rows or _chunk_cols != cols:
		for c in _chunks:
			c.queue_free()
		_chunks.clear()
		_chunk_cols = cols
		for cy in rows:
			for cx in cols:
				var c := Chunk.new()
				c.name = "Chunk%d_%d" % [cx, cy]
				c.owner_layer = self
				c.rect = Rect2i(cx * CHUNK, cy * CHUNK,
					mini(CHUNK, world.width - cx * CHUNK), mini(CHUNK, world.height - cy * CHUNK))
				add_child(c)
				_chunks.append(c)
	for c in _chunks:
		_index_anim(c)
	refresh()

func _index_anim(c: Chunk) -> void:
	c.anim_ids = PackedInt32Array()
	if anim == null or not anim.has_any():
		return
	for ty in range(c.rect.position.y, c.rect.end.y):
		for tx in range(c.rect.position.x, c.rect.end.x):
			var id := _id_at(tx, ty)
			if id > 0 and anim.animated(id) and not c.anim_ids.has(id):
				c.anim_ids.append(id)
	c.sig = anim.signature(c.anim_ids) if not c.anim_ids.is_empty() else 0

## Re-record every chunk: the tile grid or the tint changed wholesale.
func refresh() -> void:
	for c in _chunks:
		c.queue_redraw()

## Re-record the chunk holding one tile: a crate broke, a door opened.
func refresh_tile(t: Vector2i) -> void:
	var c := _chunk_at(t.x, t.y)
	if c != null:
		_index_anim(c)
		c.queue_redraw()

func _chunk_at(tx: int, ty: int) -> Chunk:
	if world == null or tx < 0 or ty < 0 or tx >= world.width or ty >= world.height:
		return null
	var i := (ty / CHUNK) * _chunk_cols + (tx / CHUNK)
	return _chunks[i] if i < _chunks.size() else null

func _id_at(tx: int, ty: int) -> int:
	return world.get_bg(tx, ty) if layer == "bg" else world.get_fg(tx, ty)

## The view only decides which animated ids are live (and so which chunks the
## animation clock re-records). Scrolling itself redraws nothing.
func set_view(r: Rect2) -> void:
	if r == view:
		return
	var before := _bounds()
	view = r
	if _bounds() != before:
		_refresh_live()

## Called by Level.on_switch_toggled() right after TileWorld.set_switch() has
## already flipped collision for `group`. Every SWITCHED tile tied to that
## group just swapped solid <-> ghost; `is_solid()` now answers with the NEW
## state, so the OLD art is simply the other half of the pair — see `_paint()`.
func begin_dissolve(group: int) -> void:
	if world == null or layer != "fg":
		return
	for ty in world.height:
		for tx in world.width:
			var id := world.get_fg(tx, ty)
			if id <= 0 or world.data.flags_of(id) & TileData4.Flag.SWITCHED == 0:
				continue
			if world.data.switch_group[id] != group:
				continue
			_dissolve[ty * world.width + tx] = DISSOLVE_TIME
			var c := _chunk_at(tx, ty)
			if c != null:
				c.queue_redraw()

func _physics_process(delta: float) -> void:
	# Consistent with TileAnim (see level.gd's _process): a hitstop freezes
	# every render clock together, so a dissolve never finishes "early"
	# relative to a world that is itself held still.
	if _dissolve.is_empty() or Game.sim_paused:
		return
	var done: Array = []
	for k: int in _dissolve.keys():
		var t: float = float(_dissolve[k]) - delta
		if t <= 0.0:
			done.append(k)
		else:
			_dissolve[k] = t
		var c := _chunk_at(k % world.width, k / world.width)
		if c != null:
			c.queue_redraw()
	for k in done:
		_dissolve.erase(k)

## The cull in tiles: the view plus one tile of margin.
func _bounds() -> Rect2i:
	if world == null:
		return Rect2i()
	var x0 := maxi(0, int(floor(view.position.x / TS)) - 1)
	var y0 := maxi(0, int(floor(view.position.y / TS)) - 1)
	var x1 := mini(world.width - 1, int(ceil((view.position.x + view.size.x) / TS)) + 1)
	var y1 := mini(world.height - 1, int(ceil((view.position.y + view.size.y) / TS)) + 1)
	return Rect2i(x0, y0, x1 - x0, y1 - y0)

func _refresh_live() -> void:
	_live = PackedInt32Array()
	if anim == null or not anim.has_any() or world == null:
		return
	var b := _bounds().grow_individual(0, 0, 1, 1)
	for c in _chunks:
		if c.anim_ids.is_empty() or not c.rect.intersects(b):
			continue
		for id in c.anim_ids:
			if not _live.has(id):
				_live.append(id)

## Re-record only a visible chunk whose animated tiles have actually changed
## frame — a still screen costs nothing, and a screen of water repaints a few
## times a second rather than sixty.
func _process(_delta: float) -> void:
	if _live.is_empty():
		return
	var b := _bounds().grow_individual(0, 0, 1, 1)
	for c in _chunks:
		if c.anim_ids.is_empty() or not c.rect.intersects(b):
			continue
		var sig := anim.signature(c.anim_ids)
		if sig != c.sig:
			c.sig = sig
			c.queue_redraw()

## Records one chunk's tiles onto `ci` (the chunk), in world coordinates.
func _paint(ci: CanvasItem, b: Rect2i) -> void:
	if world == null or atlas == null:
		return
	var cols := world.data.atlas_columns
	var animating := anim != null and anim.has_any()
	for ty in range(b.position.y, b.end.y):
		for tx in range(b.position.x, b.end.x):
			var id := _id_at(tx, ty)
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
				# The authored id may be either half (the `_off` tiles' art is
				# the ghost), so pick art by solidity rather than swapping.
				var cur_solid := world.is_solid(tx, ty)
				art = _solid_of(id) if cur_solid else _ghost_of(id)
				var remain: float = float(_dissolve.get(vi, 0.0))
				if remain > 0.0:
					# Cross-fade the half this tile just left (OLD) into the
					# half it just became (NEW, already `art`) — collision
					# switched on the flip frame; only the paint catches up.
					var old_art := _ghost_of(id) if cur_solid else _solid_of(id)
					var k := clampf(remain / DISSOLVE_TIME, 0.0, 1.0)
					var dst2 := Vector2(tx * TS, ty * TS)
					var old_src := Rect2(float((old_art % cols) * TS), float((old_art / cols) * TS), TS, TS)
					var new_src := Rect2(float((art % cols) * TS), float((art / cols) * TS), TS, TS)
					var c := modulate_color
					ci.draw_texture_rect_region(atlas, Rect2(dst2, Vector2(TS, TS)), old_src,
						Color(c.r, c.g, c.b, c.a * k))
					ci.draw_texture_rect_region(atlas, Rect2(dst2, Vector2(TS, TS)), new_src,
						Color(c.r, c.g, c.b, c.a * (1.0 - k)))
					continue
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
			ci.draw_texture_rect_region(tex, Rect2(dst, Vector2(TS, TS)), src, col)

## Which animated tile ids are inside the current cull. Empty means this layer
## costs nothing per frame.
func live_animated_ids() -> PackedInt32Array:
	return _live

## How many tiles are mid-dissolve right now. Like `live_animated_ids()`, this
## is for the integration suite, which cannot see a draw call but can see the
## work behind one — tests/integration/integration_tests.gd uses it to prove
## the dissolve is running without reaching into `_dissolve` directly.
func dissolving_count() -> int:
	return _dissolve.size()

## How many chunks this layer is drawn in. For the integration suite.
func chunk_count() -> int:
	return _chunks.size()

func _ghost_of(id: int) -> int:
	match id:
		11: return 26
		12: return 27
	return id

func _solid_of(id: int) -> int:
	match id:
		26: return 11
		27: return 12
	return id
