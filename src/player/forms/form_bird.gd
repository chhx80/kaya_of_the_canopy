extends FormBase
## Bird: flap to climb while stamina lasts, hold jump to glide, and perch to
## refill. Stamina is what stops flight from trivialising every level.

var _flap_cd := 0.0

func update(p: Actor, input: InputState, delta: float) -> void:
	var wet := p.submerged()
	tick_timers(p, input, delta)
	_flap_cd = maxf(0.0, _flap_cd - delta)

	run_axis(p, input.axis_x(), delta, water_move_scale if wet else 1.0)

	var gliding := input.jump and p.vel.y > 0.0 and stamina > 0.0 and not wet
	var g := float(cfg.get("glide_gravity", 105.0)) if gliding else gravity
	if wet:
		g *= water_gravity_scale
	p.vel.y = minf(p.vel.y + g * delta, water_max_fall if wet else max_fall)

	if p.on_floor:
		# Perched: refill faster than in the air.
		stamina = minf(max_stamina, stamina
			+ (float(cfg.get("stamina_regen", 46.0))
				+ float(cfg.get("perch_regen_bonus", 34.0))) * delta)
		if can_jump_now(p):
			do_jump(p, water_jump_scale if wet else 1.0)
			AudioManager.play("flap")
	else:
		stamina = minf(max_stamina, stamina + float(cfg.get("stamina_regen", 46.0)) * delta * 0.25)
		var cost := float(cfg.get("flap_cost", 12.0))
		if input.jump and _flap_cd <= 0.0 and stamina >= cost:
			stamina -= cost
			p.vel.y = float(cfg.get("flap_vel", -172.0))
			_flap_cd = float(cfg.get("flap_interval", 0.24))
			AudioManager.play("flap")

func anim_for(p: Actor) -> String:
	if not p.on_floor:
		if p.vel.y > 0.0 and stamina > 0.0:
			return "glide"
		return "fly"
	return "run" if absf(p.vel.x) > 6.0 else "idle"

## 0..1 — drawn as a stamina bar by the HUD.
func stamina_fraction() -> float:
	return clampf(stamina / max_stamina, 0.0, 1.0) if max_stamina > 0.0 else 0.0
