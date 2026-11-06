class_name AmbienceLayer
extends Node2D
## The drawn half of `Ambience`: haze, vignette and light pools.
##
## One script, three roles, because the three have to sit at three different
## depths in the level and a CanvasItem has exactly one blend mode:
##
##   AIR    behind the tile layers — alpha haze over the parallax planes, which
##          is how distance gets *lighter* rather than only darker.
##   SHADE  in front of the tiles — the vignette, alpha-blended.
##   LIGHT  in front of the vignette — the pools, additive, so a light punches
##          back through the shade it is meant to be fighting.
##
## Entities are drawn after all three. That is the readability rule from the
## phase brief made structural: ambience can dim the world, it can never dim the
## player, an enemy or a pickup. A dark level therefore *increases* the contrast
## between what you are and what you are standing on.
##
## Cost is the reason it is textures and not `Light2D`: everything here is a
## handful of alpha-blended quads at 400x240 with no extra render pass, no
## shadow buffers and no per-light re-draw of the canvas. See the phase 3 notes
## in docs/art-direction.md for the measurements.

enum Role { AIR, SHADE, LIGHT }

const POOL_TEX := "res://assets/sprites/light_pool.png"
const VIGNETTE_TEX := "res://assets/sprites/vignette.png"
## Hard ceiling on pools drawn in one frame. Reached only by emissive tiles —
## a screen of water surface would otherwise draw one quad per tile.
const MAX_POOLS := 16

var role: Role = Role.AIR
var amb: Ambience = null
var world: TileWorld = null
var view := Rect2(0, 0, 400, 240)

var _pool_tex: Texture2D = null
var _vig_tex: Texture2D = null
## Pools inside the current view, rebuilt when the view crosses a tile boundary
## rather than per frame: the pools are found against tile-aligned bounds, so a
## move inside one tile cannot change the answer.
var _visible: Array = []
var _cull := Rect2i(0, 0, -1, -1)
## Every emissive run in the level, found once at setup. Scanning the cull for
## them on each tile-boundary crossing cost ~1 ms a time in the frame-cost run.
var _emissive_all: Array = []
var _flickers := false
var _t := 0.0
var _phase := 0
## Whole-pixel position of the lantern, so a dark level redraws when Kaya moves
## a pixel and not on every frame she stands still.
var _lantern_px := Vector2(-9999, -9999)

func setup(r: Role, a: Ambience, w: TileWorld) -> void:
	role = r
	amb = a
	world = w
	if role == Role.LIGHT:
		_pool_tex = load(POOL_TEX)
		_lantern_px = Vector2(-9999, -9999)
		# The one material in the level. Additive is what makes a pool read as
		# light falling on the scene rather than as a pale sticker over it.
		var m := CanvasItemMaterial.new()
		m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		material = m
	elif role == Role.SHADE:
		_vig_tex = load(VIGNETTE_TEX)
	_scan_emissive()
	_rebuild()
	queue_redraw()

## AIR and SHADE are screen-sized fills: they are drawn once at the local
## origin and *moved* with the view, so scrolling never re-records them. LIGHT
## draws in world space and only re-collects its pools when the tile-aligned
## cull changes; its motes ride the view and redraw on their own clock.
func set_view(r: Rect2) -> void:
	if r == view:
		return
	view = r
	if role != Role.LIGHT:
		position = view.position
		return
	var c := _cull_of(view)
	if c != _cull:
		_rebuild()
		queue_redraw()
	elif not amb.motes.is_empty():
		queue_redraw()

func _cull_of(r: Rect2) -> Rect2i:
	var ts := float(TileData4.TILE_SIZE)
	var p := Vector2i(int(floor(r.position.x / ts)), int(floor(r.position.y / ts)))
	var e := Vector2i(int(ceil(r.end.x / ts)), int(ceil(r.end.y / ts)))
	return Rect2i(p, e - p)

## Light pools that reach the visible screen. Authored pools are a short list;
## emissive tiles are found by scanning the cull, and runs of them along a row
## are merged into one wide pool so a lake costs a few quads and not a hundred.
func _rebuild() -> void:
	_cull = _cull_of(view)
	_visible = []
	_flickers = false
	if role != Role.LIGHT or amb == null:
		return
	for raw: Variant in amb.pools:
		var p: Ambience.Pool = raw
		if _cull_rect().grow(p.radius).has_point(p.pos):
			_visible.append(p)
			_flickers = _flickers or p.flicker > 0.0
	var cr := _cull_rect()
	for raw: Variant in _emissive_all:
		var e: Ambience.Pool = raw
		if cr.grow(e.radius).has_point(e.pos):
			_visible.append(e)
	if _visible.size() > MAX_POOLS:
		_visible.resize(MAX_POOLS)

## The tile-aligned cull as world pixels. Pools are kept against this, not the
## exact view, so the set cannot change between two tile boundaries.
func _cull_rect() -> Rect2:
	var ts := float(TileData4.TILE_SIZE)
	return Rect2(Vector2(_cull.position) * ts, Vector2(_cull.size) * ts)

## Runs of the same emissive tile along a row, merged into one pool each — and
## broken at every screen-width column (25 tiles), which is exactly where the
## screen flip used to clip them. So a lake is lit by the same lozenges it was
## under the flip, and they stay put in the world as the view scrolls over
## them, instead of sliding with a cull edge.
func _scan_emissive() -> void:
	_emissive_all = []
	if role != Role.LIGHT or amb == null or world == null or amb.emissive.is_empty():
		return
	var seg := Screen.W / TileData4.TILE_SIZE
	for ty in world.height:
		var run_start := -1
		var run_id := 0
		for tx in range(0, world.width + 1):
			var id := world.get_fg(tx, ty) if tx < world.width else 0
			var lit: bool = amb.emissive.has(id)
			if lit and run_id == id and tx % seg != 0:
				continue
			if run_start >= 0:
				_add_run(run_start, tx - 1, ty, run_id)
			run_start = tx if lit else -1
			run_id = id if lit else 0

func _add_run(x0: int, x1: int, ty: int, id: int) -> void:
	var e: Dictionary = amb.emissive[id]
	var ts := float(TileData4.TILE_SIZE)
	var p := Ambience.Pool.new()
	p.pos = Vector2((float(x0 + x1) * 0.5 + 0.5) * ts, (float(ty) + 0.5) * ts
		- float(e["lift"]))
	# Wide enough to cover the run, but never taller than a single pool: the
	# texture is round, so a long run gets a flat lozenge of light, which is
	# what a lit surface looks like anyway.
	var base := float(e["radius"])
	p.half = Vector2(base + float(x1 - x0) * ts * 0.5, base)
	p.radius = maxf(p.half.x, p.half.y)
	p.colour = e["colour"]
	_emissive_all.append(p)

## How many pools this layer would draw right now. Used by the integration
## suite, which cannot see a draw call but can see the work behind one.
func visible_pools() -> int:
	return _visible.size()

## The player, found through the Level this layer is a child of. A lookup rather
## than a wired reference because darkness is a *drawing*: nothing in the level
## should have to know it is dark, and nothing here may reach back into movement.
func _lantern_pos() -> Vector2:
	var lv := get_parent()
	if lv == null:
		return Vector2(-9999, -9999)
	var pl: Variant = lv.get("player")
	if pl is Actor:
		return (pl as Actor).center()
	return Vector2(-9999, -9999)

func _process(delta: float) -> void:
	# Only the light layer animates: the haze and the shade are flat fills that
	# move with the view (set_view) and never need repainting.
	if role != Role.LIGHT or amb == null or Game.sim_paused:
		return
	if amb.lantern_radius > 0.0:
		var here := _lantern_pos().round()
		if here != _lantern_px:
			_lantern_px = here
			queue_redraw()
	var has_motes: bool = not amb.motes.is_empty()
	if not _flickers and amb.lantern_flicker <= 0.0 and not has_motes:
		return
	_t += delta
	if has_motes:
		# Motes drift continuously, not in flicker's quantised steps -- a
		# handful of extra redraws a frame is the whole cost (single-digit
		# particle counts, no texture beyond a filled rect), and it is what
		# keeps the drift smooth rather than stepping once every 1/16 s.
		queue_redraw()
		return
	# Quantised: a flicker that redraws on every frame costs more than the
	# lights do. Sixteen steps is finer than the eye reads at this scale.
	var ph := int(_t * 16.0)
	if ph != _phase:
		_phase = ph
		queue_redraw()

## The light Kaya carries in a dark level. Drawn outside `_visible` so a screen
## full of emissive tiles can never push it past MAX_POOLS and leave her blind
## in a room she cannot see — that is a softlock made of pixels.
func _draw_lantern() -> void:
	if amb.lantern_radius <= 0.0:
		return
	var at := _lantern_pos()
	if at.x < -9000.0:
		return
	var c := amb.lantern
	if amb.lantern_flicker > 0.0:
		c.a *= 1.0 - amb.lantern_flicker * (0.5 + 0.5 * sin(_t * TAU * amb.lantern_rate))
	var half := Vector2(amb.lantern_radius, amb.lantern_radius)
	draw_texture_rect(_pool_tex, Rect2((at - half).round(), half * 2.0), false, c)

func _draw() -> void:
	if amb == null:
		return
	match role:
		Role.AIR:
			if amb.air.a > 0.0:
				draw_rect(Rect2(Vector2.ZERO, view.size), amb.air)
		Role.SHADE:
			# Darkness first, vignette on top: the vignette is the *edge* of the
			# screen getting darker still, not a second flat fill.
			if amb.darkness > 0.0:
				draw_rect(Rect2(Vector2.ZERO, view.size), amb.shade)
			if amb.vignette > 0.0 and _vig_tex != null:
				draw_texture_rect(_vig_tex, Rect2(Vector2.ZERO, view.size), false,
					Color(1, 1, 1, amb.vignette))
		Role.LIGHT:
			if _pool_tex == null:
				return
			_draw_lantern()
			for raw: Variant in _visible:
				var p: Ambience.Pool = raw
				var c := p.colour
				if p.flicker > 0.0:
					c.a *= 1.0 - p.flicker * (0.5 + 0.5 * sin(_t * TAU * p.rate))
				draw_texture_rect(_pool_tex,
					Rect2((p.pos - p.half).round(), p.half * 2.0), false, c)
			_draw_motes()

## Phase C, docs/plan-art-motion.md: a handful of ambient drift specks, one
## recipe per backdrop world (Ambience.MOTE_SPECS). Screen-space and purely a
## function of `_t` and the mote's own index -- no RNG, nothing read from the
## world or the player -- so this never becomes a second source of truth for
## anything a replay tape could disagree with; it is drawn, and nothing reads
## it back. Additive, like the pools it is drawn beside, which is why a speck
## of pollen or an ember reads as light rather than as a sprite pasted on.
func _draw_motes() -> void:
	var spec: Dictionary = amb.motes
	if spec.is_empty() or _pool_tex == null:
		return
	var n := int(spec.get("count", 0))
	var sz: float = float(spec.get("size", 1.5))
	var spd: float = float(spec.get("speed", 8.0))
	var col := Ambience.ramp_colour(String(spec.get("ramp", "gold")), int(spec.get("step", 5)))
	col.a = float(spec.get("alpha", 0.4))
	for i in n:
		var seed := float(i) * 91.7
		var wx := view.size.x + sz * 4.0
		var px := fmod(seed * 13.0 + _t * spd * (0.6 + 0.08 * float(i % 3)), wx) - sz * 2.0
		var py := fmod(seed * 37.0 + sin(_t * 0.5 + seed) * 10.0, view.size.y)
		var at := (view.position + Vector2(px, py)).round()
		draw_rect(Rect2(at, Vector2(sz, sz)), col)
