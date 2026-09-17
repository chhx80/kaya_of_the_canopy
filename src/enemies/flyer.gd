extends Enemy
## THE CANOPY WASP — a fixed airborne patrol, and nothing else.
##
## Two properties make it worth having. It has **no gravity**, so its altitude
## is authored rather than emergent; and it sets `drop_through`, so one-way
## platforms never catch it. That second one is the point: a flyer that lands
## on the first wooden walkway it crosses is a walker with wings, and the level
## author loses the only enemy that can hold a line of air above a platform.
##
## It does not chase. The path *is* the threat — you time your jump around it
## the way you would a moving hazard, and it is the same every lap.
##
## Per-instance shape comes off the level entity, so one data file covers a
## horizontal sentry and a vertical elevator-shaft patrol:
##
##     {"type": "enemy_flyer", "x": 12, "y": 5, "axis": "y", "range": 48}

var _t := 0.0
var _origin := Vector2.ZERO
var _axis_x := true
var _dir := 1.0

func on_configured() -> void:
	gravity = 0.0
	_axis_x = String(props.get("axis", cfg.get("patrol_axis", "x"))) != "y"
	_dir = 1.0 if facing >= 0 or not _axis_x else -1.0

func _ready() -> void:
	super._ready()
	_origin = pos
	drop_through = true

func on_respawn() -> void:
	_t = 0.0
	_origin = spawn_pos
	_dir = 1.0 if facing >= 0 or not _axis_x else -1.0
	drop_through = true
	set_anim("fly")

func think(delta: float) -> void:
	set_anim("fly")
	drop_through = true
	_t += delta
	var leg := float(props.get("range", cfg.get("patrol_range", 64.0)))
	var amp := float(props.get("bob", cfg.get("bob_amplitude", 6.0)))
	var period := maxf(0.05, float(cfg.get("bob_period", 1.7)))
	var gain := float(cfg.get("steer_gain", 4.0))
	var bob_max := float(cfg.get("bob_max_speed", 90.0))
	var wobble := sin(_t * TAU / period) * amp

	if _axis_x:
		# Turn at the end of the leg, or early if a solid wall got there first.
		# Re-anchoring on a wall turn keeps the next leg full length instead of
		# grinding along the wall for the rest of the lap.
		if against_wall != 0 and float(against_wall) * _dir > 0.0:
			_dir = -_dir
			_origin.x = pos.x
		elif absf(pos.x - _origin.x) >= leg and (pos.x - _origin.x) * _dir > 0.0:
			_dir = -_dir
		vel.x = speed * _dir
		vel.y = clampf((_origin.y + wobble - pos.y) * gain, -bob_max, bob_max)
		facing = 1 if _dir > 0.0 else -1
	else:
		# on_floor here can only mean a *solid* tile: drop_through is set, so a
		# one-way never reports underfoot.
		if (on_ceiling and _dir < 0.0) or (on_floor and _dir > 0.0):
			_dir = -_dir
			_origin.y = pos.y
		elif absf(pos.y - _origin.y) >= leg and (pos.y - _origin.y) * _dir > 0.0:
			_dir = -_dir
		vel.y = speed * _dir
		vel.x = clampf((_origin.x + wobble - pos.x) * gain, -bob_max, bob_max)
