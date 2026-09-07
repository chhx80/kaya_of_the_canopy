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

# ---------------------------------------------------------------- shared bits
func _approach(v: float, target: float, rate: float, delta: float) -> float:
	return move_toward(v, target, rate * delta)

## Horizontal acceleration/friction shared by every walking form.
func run_axis(p: Actor, want: float, delta: float, speed_scale: float = 1.0) -> void:
	var top := max_run * speed_scale
	var a := accel if p.on_floor else air_accel
	var fr := friction if p.on_floor else air_friction
	if absf(want) > 0.01:
		p.vel.x = _approach(p.vel.x, want * top, a, delta)
		p.facing = 1 if want > 0.0 else -1
	else:
		p.vel.x = _approach(p.vel.x, 0.0, fr, delta)

func apply_gravity(p: Actor, delta: float, in_water: bool) -> void:
	var g := gravity * (water_gravity_scale if in_water else 1.0)
	var cap := water_max_fall if in_water else max_fall
	p.vel.y = minf(p.vel.y + g * delta, cap)

func tick_timers(p: Actor, input: InputState, delta: float) -> void:
	coyote = coyote_time if p.on_floor else maxf(0.0, coyote - delta)
	buffer = jump_buffer if input.jump_pressed else maxf(0.0, buffer - delta)

func can_jump_now(_p: Actor) -> bool:
	return coyote > 0.0 and buffer > 0.0

func do_jump(p: Actor, scale: float = 1.0) -> void:
	p.vel.y = jump_vel * scale
	coyote = 0.0
	buffer = 0.0

## Override per form. Called once per physics tick.
func update(_p: Actor, _input: InputState, _delta: float) -> void:
	pass

## Which animation should play right now.
func anim_for(_p: Actor) -> String:
	return "idle"
