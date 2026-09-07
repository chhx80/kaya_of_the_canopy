extends FormBase
## Fish: free eight-way movement in water, helpless out of it. The air timer is
## the whole tension of a water level — you always know how far the next pool is.

var air_left := 0.0

func configure(d: Dictionary) -> void:
	super.configure(d)
	air_left = float(cfg.get("air_seconds", 2.6))

func update(p: Actor, input: InputState, delta: float) -> void:
	var wet := p.in_water()
	if wet:
		air_left = float(cfg.get("air_seconds", 2.6))
		_swim(p, input, delta)
	else:
		air_left -= delta
		_flop(p, input, delta)
		if drowns and air_left <= 0.0 and p is Player:
			(p as Player).kill()

func _swim(p: Actor, input: InputState, delta: float) -> void:
	var want := Vector2(input.axis_x(), input.axis_y())
	if want.length() > 1.0:
		want = want.normalized()
	var top := float(cfg.get("swim_speed", 92.0))
	if want.length() > 0.01:
		p.vel = p.vel.move_toward(want * top, float(cfg.get("swim_accel", 620.0)) * delta)
		if absf(want.x) > 0.01:
			p.facing = 1 if want.x > 0.0 else -1
	else:
		p.vel = p.vel.move_toward(Vector2.ZERO, float(cfg.get("swim_drag", 420.0)) * delta)
	# Break the surface with a hop so you can cross a lip of land.
	if input.jump_pressed and not p.submerged():
		p.vel.y = float(cfg.get("surface_hop", -150.0))

func _flop(p: Actor, input: InputState, delta: float) -> void:
	tick_timers(p, input, delta)
	run_axis(p, input.axis_x(), delta)
	apply_gravity(p, delta, false)
	if can_jump_now(p):
		do_jump(p)

func anim_for(p: Actor) -> String:
	if p.in_water():
		return "swim" if p.vel.length() > 10.0 else "idle"
	return "flop"

## 0..1 — drawn as an air meter by the HUD.
func air_fraction() -> float:
	var total := float(cfg.get("air_seconds", 2.6))
	return clampf(air_left / total, 0.0, 1.0) if total > 0.0 else 1.0
