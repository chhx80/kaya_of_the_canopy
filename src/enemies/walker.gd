extends Enemy
## Patrols a ledge, turns at walls and drops, optionally chases when the player
## comes within `chase_range`.

var _turn_cooldown := 0.0

func on_respawn() -> void:
	set_anim("move")

func think(delta: float) -> void:
	_turn_cooldown = maxf(0.0, _turn_cooldown - delta)
	apply_gravity(delta)

	var spd := speed
	var chase_range := float(cfg.get("chase_range", 0.0))
	if chase_range > 0.0:
		var p := player()
		if p != null and not p.dead and absf(p.center().x - center().x) < chase_range \
				and absf(p.center().y - center().y) < 40.0:
			facing = 1 if p.center().x > center().x else -1
			spd = float(cfg.get("chase_speed", speed * 1.6))

	if on_floor and _turn_cooldown <= 0.0:
		var blocked := against_wall == facing
		var ledge := bool(cfg.get("turn_at_ledge", true)) and not ground_ahead(facing, 2.0)
		if blocked or ledge:
			facing = -facing
			_turn_cooldown = 0.15
	vel.x = spd * facing
	set_anim("move")
