class_name Blade
extends Actor
## Flies out in the facing direction, reverses at `max_range` or on a wall, then
## homes back to the thrower. Damages enemies on both legs and shatters crates.

enum St { OUT, BACK }

var cfg: Dictionary = {}
var owner_player: Player = null
var st: St = St.OUT
var origin := Vector2.ZERO
var damage := 1
var sprite: Sprite2D = null
var _frame_size := Vector2i(16, 16)
var _spin := 0.0
var _hit_this_throw: Array[int] = []
var _tripped_this_throw: Array[int] = []
var _spark_cd := 0.0

## Phase D, docs/plan-art-motion.md: blade afterimage. A render-history
## buffer of past node positions — nothing fed back into flight, catch or
## damage, read only by `_draw()` below. Sampled every tick and thinned to
## `AFTERIMAGE_COUNT` ghosts spaced `TRAIL_STRIDE` ticks apart, which is what
## keeps the trail legible instead of a smear at the blade's top speed.
## `queue_free()` on the catch (below) takes the whole buffer with it — there
## is no separate ghost node to leak or to kill explicitly.
const AFTERIMAGE_COUNT := 2
const AFTERIMAGE_ALPHAS: Array[float] = [0.40, 0.20]
const TRAIL_STRIDE := 3
var _trail: Array[Vector2] = []

func setup(config: Dictionary, p: Player) -> void:
	cfg = config
	owner_player = p
	world = p.world
	level = p.level
	var hb: Dictionary = cfg.get("hitbox", {"w": 12, "h": 12, "ox": 2, "oy": 2})
	box = Vector2(float(hb.get("w", 12)), float(hb.get("h", 12)))
	_frame_size = Vector2i(int(cfg.get("frame_w", 16)), int(cfg.get("frame_h", 16)))
	damage = int(cfg.get("damage", 1))
	facing = p.facing
	set_center(p.center() + Vector2(p.facing * 8.0, 0.0))
	origin = center()
	vel = Vector2(float(cfg.get("speed", 205.0)) * facing, float(cfg.get("rise", -18.0)))

func _ready() -> void:
	sprite = Sprite2D.new()
	sprite.centered = false
	sprite.region_enabled = true
	sprite.texture = load(String(cfg.get("sprite", "res://assets/sprites/blade.png")))
	var hb: Dictionary = cfg.get("hitbox", {})
	sprite.offset = Vector2(-float(hb.get("ox", 2)), -float(hb.get("oy", 2)))
	add_child(sprite)
	_sync_render_position()

func _physics_process(delta: float) -> void:
	if Game.sim_paused:
		return
	if owner_player == null or not is_instance_valid(owner_player):
		queue_free()
		return

	if st == St.OUT:
		if origin.distance_to(center()) >= float(cfg.get("max_range", 118.0)):
			_turn_back()
	else:
		var to: Vector2 = (owner_player.center() - center()).normalized()
		vel = (vel + to * float(cfg.get("return_accel", 1000.0)) * delta) \
			.limit_length(float(cfg.get("return_max", 300.0)))
		facing = 1 if vel.x >= 0.0 else -1

	# Solid tiles bounce the blade home; crates break instead.
	var before := pos
	_spark_cd = maxf(0.0, _spark_cd - delta)
	step_motion(delta)
	if against_wall != 0 or on_ceiling or on_floor:
		_sparks()
		_hit_tiles()
		if st == St.OUT:
			_turn_back()
		else:
			# Sliding along geometry on the way back should not trap it.
			pos = before
			vel = (owner_player.center() - center()).normalized() \
				* float(cfg.get("return_max", 300.0))

	_damage_enemies()
	_trip_switches()

	if st == St.BACK and aabb().intersects(owner_player.aabb()):
		AudioManager.play("catch")
		queue_free()
		return

	_spin += delta
	var frames: Array = cfg.get("frames", [0, 1])
	var fps := float(cfg.get("spin_fps", 18))
	var f := int(frames[int(_spin * fps) % frames.size()])
	sprite.region_rect = Rect2(f * _frame_size.x, 0, _frame_size.x, _frame_size.y)
	_sync_render_position()
	_record_trail()

## One sample per tick, capped to just enough history for the furthest ghost.
func _record_trail() -> void:
	_trail.append(position)
	var cap := TRAIL_STRIDE * AFTERIMAGE_COUNT + 1
	while _trail.size() > cap:
		_trail.pop_front()
	queue_redraw()

## Drawn in the blade's own `_draw()`, which paints behind `sprite` (a child
## node always renders after its parent's own draw calls) — "drawn behind the
## blade" falls out of the node order for free, with no z-index to keep in
## sync. Positions are past node positions, converted to this tick's local
## space; the source region is the blade's CURRENT spin frame, which reads as
## a trail of the same spinning shape rather than a second animation to keep
## in step.
func _draw() -> void:
	for i in AFTERIMAGE_COUNT:
		var back := TRAIL_STRIDE * (i + 1)
		var idx := _trail.size() - 1 - back
		if idx < 0:
			continue
		var local := _trail[idx] - position
		draw_texture_rect_region(sprite.texture,
			Rect2(local + sprite.offset, Vector2(_frame_size.x, _frame_size.y)),
			sprite.region_rect, Color(1.0, 1.0, 1.0, AFTERIMAGE_ALPHAS[i]))

func _turn_back() -> void:
	st = St.BACK
	vel = (owner_player.center() - center()).normalized() * float(cfg.get("speed", 205.0)) * 0.6

## Struck geometry. Rate-limited because a blade sliding along a wall touches it
## on every one of sixty ticks, and sixty bursts would empty the pool.
func _sparks() -> void:
	if _spark_cd > 0.0:
		return
	_spark_cd = Fx.timing("blade_spark_interval", 0.09)
	# Off the surface it struck, not along the blade's heading: the collision
	# has already zeroed the velocity component that ran into the wall.
	var away := Vector2(-float(against_wall), 0.0)
	if on_floor:
		away.y = -1.0
	elif on_ceiling:
		away.y = 1.0
	if away == Vector2.ZERO:
		away = Vector2(-float(facing), 0.0)
	Fx.burst("spark", center(), away.normalized())

func _hit_tiles() -> void:
	if not bool(cfg.get("breaks_crates", true)) or world == null:
		return
	for t in TileCollision.tiles_with_flag(world, aabb().grow(2.0), TileData4.Flag.BREAKABLE):
		if world.break_tile(t.x, t.y):
			AudioManager.play("crate_break")
			Game.add_score(20)
			if level != null:
				level.on_tile_broken(t)

func _trip_switches() -> void:
	var r := aabb()
	for n in get_tree().get_nodes_in_group(&"switches"):
		var sw := n as SwitchTrigger
		if sw == null or sw.level != level:
			continue
		var sid := sw.get_instance_id()
		# One flip per throw: passing the lever on the way out and again on the
		# way back would otherwise cancel itself out.
		if _tripped_this_throw.has(sid):
			continue
		if r.intersects(sw.aabb()):
			_tripped_this_throw.append(sid)
			sw.toggle()

func _damage_enemies() -> void:
	var r := aabb()
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e == null or not e.active:
			continue
		var eid := e.get_instance_id()
		if _hit_this_throw.has(eid):
			continue
		if r.intersects(e.aabb()):
			_hit_this_throw.append(eid)
			e.hurt(damage, center())
