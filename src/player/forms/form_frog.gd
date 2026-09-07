extends FormBase
## Frog: a huge, slow, committed jump and a brief cling to walls. No weapon —
## the trade for the height is that you cannot answer anything that finds you.

var _cling := 0.0
var _cling_dir := 0

func update(p: Actor, input: InputState, delta: float) -> void:
	var wet := p.submerged()
	tick_timers(p, input, delta)

	# --- wall cling: pressing into a wall in mid-air slows the slide and buys
	# --- a short window for a kick-off jump.
	var pressing := int(signf(input.axis_x()))
	if not p.on_floor and p.against_wall != 0 and pressing == p.against_wall and not wet:
		if _cling <= 0.0 or _cling_dir != p.against_wall:
			_cling = float(cfg.get("wall_stick_time", 0.55))
			_cling_dir = p.against_wall
	var clinging := _cling > 0.0 and not p.on_floor and p.against_wall == _cling_dir
	if clinging:
		_cling = maxf(0.0, _cling - delta)
		p.facing = -_cling_dir
		if input.jump_pressed:
			p.vel.y = float(cfg.get("wall_jump_vel", -305.0))
			p.vel.x = -_cling_dir * float(cfg.get("wall_jump_push", 120.0))
			_cling = 0.0
			buffer = 0.0
			AudioManager.play("jump")
			return
	else:
		_cling = maxf(0.0, _cling - delta)

	run_axis(p, input.axis_x(), delta, water_move_scale if wet else 1.0)
	apply_gravity(p, delta, wet)
	if clinging:
		# Clamp *after* gravity, or the slide speed drifts up by g*dt each tick.
		p.vel.y = minf(p.vel.y, float(cfg.get("wall_slide_speed", 34.0)))
	if can_jump_now(p):
		do_jump(p, water_jump_scale if wet else 1.0)
		AudioManager.play("hop")
	if input.jump_released and p.vel.y < 0.0:
		p.vel.y *= jump_cut

func anim_for(p: Actor) -> String:
	if _cling > 0.0 and not p.on_floor and p.against_wall != 0:
		return "cling"
	if not p.on_floor:
		return "jump" if p.vel.y < 0.0 else "fall"
	return "idle"
