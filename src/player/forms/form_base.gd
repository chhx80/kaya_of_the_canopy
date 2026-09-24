class_name FormBase
extends RefCounted
## One movement controller per shape Kaya can take. All tuning comes from
## data/forms/<id>.json — no magic numbers below.

var cfg: Dictionary = {}
var id := "base"

# cached tunables
var gravity := 760.0
var max_fall := 330.0
var max_run := 108.0
var accel := 900.0
var friction := 1100.0
var air_accel := 520.0
var air_friction := 220.0
var jump_vel := -260.0
var jump_cut := 0.42
var coyote_time := 0.09
var jump_buffer := 0.12
var climb_speed := 60.0
var can_attack := true
var can_climb := true
var move_mode := "ground"
var water_gravity_scale := 0.3
var water_max_fall := 74.0
var water_move_scale := 0.62
var water_jump_scale := 0.78
var drowns := false

## Forms that spend a resource (the bird) expose it here; the HUD draws a bar
## whenever `max_stamina > 0`.
var max_stamina := 0.0
var stamina := 0.0

# per-tick state
var coyote := 0.0
var buffer := 0.0
var climbing := false

## The velocity of the medium the actor is standing in this tick — a water push
## or an updraft, in px/s. Refreshed by `update()` before the form moves, and
## folded into every velocity the form sets, so the form is always steering
## *relative to the water* rather than relative to the world. See `current_at()`.
var current := Vector2.ZERO
## Seconds spent shouldering into `_break_target`, and which tile that is.
var break_progress := 0.0
var _break_target := Vector2i(-1, -1)

static func load_form(form_id: String) -> FormBase:
	var path := "res://data/forms/%s.json" % form_id
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("FormBase: missing %s" % path)
		return null
	var d: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(d) != TYPE_DICTIONARY:
		push_error("FormBase: %s is not an object" % path)
		return null
	var script_path := "res://src/player/forms/form_%s.gd" % form_id
	var inst: FormBase
	if ResourceLoader.exists(script_path):
		var s: GDScript = load(script_path)
		inst = s.new()
	else:
		inst = FormBase.new()
	inst.configure(d)
	return inst

func configure(d: Dictionary) -> void:
	cfg = d
	id = String(d.get("id", "base"))
	gravity = float(d.get("gravity", gravity))
	max_fall = float(d.get("max_fall", max_fall))
	max_run = float(d.get("max_run", max_run))
	accel = float(d.get("accel", accel))
	friction = float(d.get("friction", friction))
	air_accel = float(d.get("air_accel", air_accel))
	air_friction = float(d.get("air_friction", air_friction))
	jump_vel = float(d.get("jump_vel", jump_vel))
	jump_cut = float(d.get("jump_cut", jump_cut))
	coyote_time = float(d.get("coyote_time", coyote_time))
	jump_buffer = float(d.get("jump_buffer", jump_buffer))
	climb_speed = float(d.get("climb_speed", climb_speed))
	can_attack = bool(d.get("can_attack", can_attack))
	can_climb = bool(d.get("can_climb", can_climb))
	move_mode = String(d.get("move_mode", move_mode))
	water_gravity_scale = float(d.get("water_gravity_scale", water_gravity_scale))
	water_max_fall = float(d.get("water_max_fall", water_max_fall))
	water_move_scale = float(d.get("water_move_scale", water_move_scale))
	water_jump_scale = float(d.get("water_jump_scale", water_jump_scale))
	drowns = bool(d.get("drowns", drowns))
	max_stamina = float(d.get("max_stamina", 0.0))
	stamina = max_stamina

## Which weapon this form carries, if any.
func weapon_id() -> String:
	return String(cfg.get("weapon", "boomerang_blade" if can_attack else ""))

func hitbox() -> Dictionary:
	return cfg.get("hitbox", {"w": 10, "h": 22, "ox": 3, "oy": 2})

func sprite_path() -> String:
	return String(cfg.get("sprite", "res://assets/sprites/kaya_human.png"))

func frame_size() -> Vector2i:
	return Vector2i(int(cfg.get("frame_w", 16)), int(cfg.get("frame_h", 24)))

func anim(name: String) -> Dictionary:
	var a: Dictionary = cfg.get("anim", {})
	return a.get(name, {"frames": [0], "fps": 1})

# ------------------------------------------------------------------ currents
## The velocity of the medium under `rect`: the area-weighted mean of the
## `current` vectors of every tile it overlaps.
##
## Weighted rather than all-or-nothing on purpose. A step function at a tile
## boundary would make the push depend on which side of a single pixel the
## hitbox sat, and a six-pixel difference between the model and the game is
## exactly what cost this project a level before (docs/adr/005). Weighting also
## means a current ramps in as you enter it, which is what it looks like.
##
## Static and pure: it takes a TileWorld and a Rect2 and touches nothing else,
## so a headless test — and the prover — get the same answer as the game.
static func current_at(world: TileWorld, rect: Rect2) -> Vector2:
	if world == null or world.data == null or not world.data.has_currents:
		return Vector2.ZERO
	var area := rect.size.x * rect.size.y
	if area <= 0.0:
		return Vector2.ZERO
	var ts := float(TileData4.TILE_SIZE)
	var cols := TileCollision.tile_range(rect.position.x, rect.position.x + rect.size.x)
	var rows := TileCollision.tile_range(rect.position.y, rect.position.y + rect.size.y)
	var sum := Vector2.ZERO
	for ty in range(rows.x, rows.y + 1):
		for tx in range(cols.x, cols.y + 1):
			if world.flags_at(tx, ty) & TileData4.Flag.CURRENT == 0:
				continue
			var overlap := Rect2(float(tx) * ts, float(ty) * ts, ts, ts).intersection(rect)
			if overlap.size.x <= 0.0 or overlap.size.y <= 0.0:
				continue
			sum += world.data.current_of(world.get_fg(tx, ty)) \
				* (overlap.size.x * overlap.size.y / area)
	return sum

# ------------------------------------------------------------- breakable walls
## Shoulder through a breakable wall: hold attack and press into it.
##
## The generalisation of crate-breaking. The blade still shatters any BREAKABLE
## tile it touches, but the blade is a Node — invisible to the prover, and the
## frog does not carry one. This path is neither: it is pure form state against
## the TileWorld, so a route through a wall can be proved as well as played.
func tick_break(p: Actor, input: InputState, delta: float) -> void:
	var target := _break_target_of(p, input)
	if target != _break_target:
		_break_target = target
		break_progress = 0.0
	if target.x < 0:
		return
	break_progress += delta
	if break_progress < p.world.data.break_hold_of(p.world.get_fg(target.x, target.y)):
		return
	break_progress = 0.0
	_break_target = Vector2i(-1, -1)
	if not p.world.break_tile(target.x, target.y):
		return
	# The level, when there is one, owns the noise and the debris. There is no
	# level under `tools/test.sh` or inside the prover, and the wall still opens.
	if p.level != null and p.level.has_method("on_tile_broken"):
		p.level.call("on_tile_broken", target)

## The breakable tile being shouldered, or (-1, -1). Up and down beat facing, so
## a frog can dig a ceiling or a floor out of a shaft it is wedged in.
func _break_target_of(p: Actor, input: InputState) -> Vector2i:
	if not input.attack or p.world == null or p.world.data == null:
		return Vector2i(-1, -1)
	var dir := Vector2i(p.facing, 0)
	if input.up:
		dir = Vector2i(0, -1)
	elif input.down:
		dir = Vector2i(0, 1)
	# A one-pixel sliver just outside the hitbox on that side. Inset on the other
	# axis so brushing past a corner is not the same as pressing into a wall.
	var r := p.aabb()
	var probe := Rect2()
	if dir.x != 0:
		var px := r.position.x + r.size.x if dir.x > 0 else r.position.x - 1.0
		probe = Rect2(px, r.position.y + 2.0, 1.0, maxf(1.0, r.size.y - 4.0))
	else:
		var py := r.position.y + r.size.y if dir.y > 0 else r.position.y - 1.0
		probe = Rect2(r.position.x + 2.0, py, maxf(1.0, r.size.x - 4.0), 1.0)
	for t in TileCollision.tiles_with_flag(p.world, probe, TileData4.Flag.BREAKABLE):
		if p.world.data.break_hold_of(p.world.get_fg(t.x, t.y)) > 0.0:
			return t
	return Vector2i(-1, -1)

# ---------------------------------------------------------------- shared bits
## Play a cue, if there is anything to play it.
##
## Forms are driven from three places now: the running game, `tools/test.sh`
## (no scene tree, ADR 003) and the Route Prover. Only the first has a working
## AudioManager — under `--script` the autoload object exists but never ran
## `_ready()`, so its player pool is empty and every cue throws. Routing cues
## through here means a jump in a unit test is a jump and not a stack trace.
static func sfx(cue: String) -> void:
	if AudioManager != null and AudioManager.is_node_ready():
		AudioManager.play(cue)

func _approach(v: float, target: float, rate: float, delta: float) -> float:
	return move_toward(v, target, rate * delta)

## Horizontal acceleration/friction shared by every walking form.
## Targets are offset by `current.x`: standing still in a river means drifting
## with it, and swimming upstream means your own top speed minus its push.
func run_axis(p: Actor, want: float, delta: float, speed_scale: float = 1.0) -> void:
	var top := max_run * speed_scale
	var a := accel if p.on_floor else air_accel
	var fr := friction if p.on_floor else air_friction
	if absf(want) > 0.01:
		p.vel.x = _approach(p.vel.x, want * top + current.x, a, delta)
		p.facing = 1 if want > 0.0 else -1
	else:
		p.vel.x = _approach(p.vel.x, current.x, fr, delta)

## Fall towards terminal velocity, which an updraft shifts: a `current.y` of
## -400 turns a 330 px/s fall into a 70 px/s climb.
##
## `move_toward` rather than the old `min(v + g*dt, cap)` because the cap can now
## be *below* the current speed — walking into an updraft at full fall speed has
## to decelerate at gravity, not snap. Below the cap the two are identical, so
## every measured jump arc in tests/test_player_forms.gd is unchanged.
func apply_gravity(p: Actor, delta: float, in_water: bool, g_override: float = -1.0) -> void:
	var g := (gravity if g_override < 0.0 else g_override) \
		* (water_gravity_scale if in_water else 1.0)
	var cap := (water_max_fall if in_water else max_fall) + current.y
	p.vel.y = move_toward(p.vel.y, cap, g * delta)

func tick_timers(p: Actor, input: InputState, delta: float) -> void:
	coyote = coyote_time if p.on_floor else maxf(0.0, coyote - delta)
	buffer = jump_buffer if input.jump_pressed else maxf(0.0, buffer - delta)

func can_jump_now(_p: Actor) -> bool:
	return coyote > 0.0 and buffer > 0.0

func do_jump(p: Actor, scale: float = 1.0) -> void:
	p.vel.y = jump_vel * scale + current.y
	coyote = 0.0
	buffer = 0.0

## Called once per physics tick, by the player and by the Route Prover alike.
##
## Deliberately NOT the per-form override: currents and breakable walls change
## where the player ends up, so they cannot live in a Node that only exists in
## the booted game — the prover would then prove a level that does not exist.
## They are sampled and applied here, and every form's `step()` inherits them
## whether its author remembered them or not.
func update(p: Actor, input: InputState, delta: float) -> void:
	current = current_at(p.world, p.aabb())
	step(p, input, delta)
	tick_break(p, input, delta)

## Override per form. Everything above the medium: run, jump, swim, climb.
func step(_p: Actor, _input: InputState, _delta: float) -> void:
	pass

## Which animation should play right now.
func anim_for(_p: Actor) -> String:
	return "idle"
