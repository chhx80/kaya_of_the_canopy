extends FormBase
## Kaya on foot: run, jump (coyote + buffered + variable height), climb vines,
## wade and drop through one-way platforms.

var _drop_timer := 0.0

func update(p: Actor, input: InputState, delta: float) -> void:
	var wet := p.submerged()
	var ladder := can_climb and p.on_ladder()
	tick_timers(p, input, delta)

	# ---- ladders take over completely while you hold up/down on one
	if ladder and (input.up or input.down or climbing):
		if not climbing and (input.up or input.down):
			climbing = true
		if climbing:
			_climb(p, input, delta)
			return
	else:
		climbing = false

	# ---- drop through one-way platforms with down + jump
	p.drop_through = _drop_timer > 0.0
	_drop_timer = maxf(0.0, _drop_timer - delta)
	if input.down and input.jump_pressed and p.on_floor:
		_drop_timer = 0.12
		buffer = 0.0
		p.drop_through = true
		p.pos.y += 1.0
		return

	run_axis(p, input.axis_x(), delta, water_move_scale if wet else 1.0)
	apply_gravity(p, delta, wet)

	if can_jump_now(p):
		do_jump(p, water_jump_scale if wet else 1.0)
		AudioManager.play("jump")
	elif wet and input.jump_pressed:
		# Swimming up: a weak repeated stroke rather than a real jump.
		p.vel.y = jump_vel * 0.45
		buffer = 0.0
	# variable jump height
	if input.jump_released and p.vel.y < 0.0:
		p.vel.y *= jump_cut

func _climb(p: Actor, input: InputState, delta: float) -> void:
	p.vel.y = input.axis_y() * climb_speed
	p.vel.x = input.axis_x() * climb_speed * 0.7
	if bool(cfg.get("climb_snap", true)) and absf(input.axis_x()) < 0.01:
		# Snap to the middle of the vine column so climbing looks deliberate.
		var col := int(floor(p.center().x / TileData4.TILE_SIZE))
		var target := col * TileData4.TILE_SIZE + TileData4.TILE_SIZE * 0.5
		p.pos.x = move_toward(p.pos.x, target - p.box.x * 0.5, 60.0 * delta)
	if input.jump_pressed:
		climbing = false
		do_jump(p)
		AudioManager.play("jump")
	elif p.on_floor and input.down:
		climbing = false

func anim_for(p: Actor) -> String:
	if climbing:
		return "climb"
	if not p.on_floor:
		return "jump" if p.vel.y < 0.0 else "fall"
	if absf(p.vel.x) > 6.0:
		return "run"
	return "idle"
