extends Enemy
## Patrols a body of water on a sine path and lunges when you swim close.
## Out of water it just flops and falls, which is how you cheese it.

var _t := 0.0
var _base_y := 0.0

func on_configured() -> void:
	gravity = 0.0

func on_respawn() -> void:
	_t = 0.0
	_base_y = pos.y
	set_anim("swim")

func _ready() -> void:
	super._ready()
	_base_y = pos.y

func think(delta: float) -> void:
	set_anim("swim")
	if not in_water():
		# Beached: gravity takes over until it slides back into the channel.
		vel.y = minf(vel.y + float(cfg.get("beached_gravity", 640.0)) * delta, 300.0)
		vel.x = move_toward(vel.x, 0.0, 200.0 * delta)
		return
	_t += delta
	var p := player()
	var chasing := false
	if p != null and not p.dead and center().distance_to(p.center()) \
			< float(cfg.get("chase_range", 96.0)) and p.in_water():
		chasing = true
		var to := (p.center() - center()).normalized()
		vel = vel.move_toward(to * float(cfg.get("chase_speed", 72.0)), 420.0 * delta)
		facing = 1 if to.x > 0.0 else -1
	if not chasing:
		if against_wall != 0:
			facing = -facing
			_base_y = pos.y
		vel.x = speed * facing
		# Sine cruise around the depth it started at.
		var amp := float(cfg.get("wave_amplitude", 26.0))
		var period := maxf(0.2, float(cfg.get("wave_period", 2.1)))
		var target := _base_y + sin(_t * TAU / period) * amp
		vel.y = clampf((target - pos.y) * 4.0, -90.0, 90.0)
