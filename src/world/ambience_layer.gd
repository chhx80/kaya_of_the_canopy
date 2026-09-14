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
## Pools inside the current view, rebuilt when the view changes rather than per
## frame: a screen flip is the only thing that can change the answer.
var _visible: Array = []
var _flickers := false
var _t := 0.0
var _phase := 0

func setup(r: Role, a: Ambience, w: TileWorld) -> void:
	role = r
	amb = a
	world = w
	if role == Role.LIGHT:
		_pool_tex = load(POOL_TEX)
		# The one material in the level. Additive is what makes a pool read as
		# light falling on the scene rather than as a pale sticker over it.
		var m := CanvasItemMaterial.new()
		m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		material = m
	elif role == Role.SHADE:
		_vig_tex = load(VIGNETTE_TEX)
	_rebuild()
	queue_redraw()

func set_view(r: Rect2) -> void:
	if r == view:
		return
	view = r
	_rebuild()
	queue_redraw()

## Light pools that reach the visible screen. Authored pools are a short list;
## emissive tiles are found by scanning the cull, and runs of them along a row
## are merged into one wide pool so a lake costs a few quads and not a hundred.
func _rebuild() -> void:
	_visible = []
	_flickers = false
	if role != Role.LIGHT or amb == null:
		return
	for raw: Variant in amb.pools:
		var p: Ambience.Pool = raw
		if view.grow(p.radius).has_point(p.pos):
			_visible.append(p)
			_flickers = _flickers or p.flicker > 0.0
	if not amb.emissive.is_empty() and world != null:
		_collect_emissive()
	if _visible.size() > MAX_POOLS:
		_visible.resize(MAX_POOLS)

func _collect_emissive() -> void:
	var ts := TileData4.TILE_SIZE
	var x0 := maxi(0, int(floor(view.position.x / ts)))
	var y0 := maxi(0, int(floor(view.position.y / ts)))
	var x1 := mini(world.width - 1, int(ceil((view.position.x + view.size.x) / ts)))
	var y1 := mini(world.height - 1, int(ceil((view.position.y + view.size.y) / ts)))
	for ty in range(y0, y1 + 1):
		var run_start := -1
		var run_id := 0
		for tx in range(x0, x1 + 2):
			var id := world.get_fg(tx, ty) if tx <= x1 else 0
			var lit: bool = amb.emissive.has(id)
			if lit and run_id == id:
				continue
			if run_start >= 0:
				_add_run(run_start, tx - 1, ty, run_id)
			run_start = tx if lit else -1
			run_id = id if lit else 0
	if _visible.size() > MAX_POOLS:
		_visible.resize(MAX_POOLS)

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
	_visible.append(p)

## How many pools this layer would draw right now. Used by the integration
## suite, which cannot see a draw call but can see the work behind one.
func visible_pools() -> int:
	return _visible.size()

func _process(delta: float) -> void:
	if not _flickers or Game.sim_paused:
		return
	_t += delta
	# Quantised: a flicker that redraws on every frame costs more than the
	# lights do. Sixteen steps is finer than the eye reads at this scale.
	var ph := int(_t * 16.0)
	if ph != _phase:
		_phase = ph
		queue_redraw()

func _draw() -> void:
	if amb == null:
		return
	match role:
		Role.AIR:
			if amb.air.a > 0.0:
				draw_rect(view, amb.air)
		Role.SHADE:
			if amb.vignette > 0.0 and _vig_tex != null:
				draw_texture_rect(_vig_tex, Rect2(view.position, view.size), false,
					Color(1, 1, 1, amb.vignette))
		Role.LIGHT:
			if _pool_tex == null:
				return
			for raw: Variant in _visible:
				var p: Ambience.Pool = raw
				var c := p.colour
				if p.flicker > 0.0:
					c.a *= 1.0 - p.flicker * (0.5 + 0.5 * sin(_t * TAU * p.rate))
				draw_texture_rect(_pool_tex,
					Rect2((p.pos - p.half).round(), p.half * 2.0), false, c)
