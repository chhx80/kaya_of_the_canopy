extends Enemy
## THE THORN BOAR — patrol, spot, wind up, charge, overshoot.
##
## The charge is faster than Kaya can run, which is the point and also the
## danger: an enemy that closes faster than you can retreat is unavoidable
## damage unless it tells you first. So the wind-up is not decoration. It
## **stops dead** for `wind_up` seconds and raises its crest, and nothing —
## not the player moving, not a hit — shortens that window. Everything after
## it is the player's own fault.
##
## The other half of the bargain is the overshoot. The boar cannot stop at the
## end of a charge: `_recover()` bleeds the speed off over `skid_decel`, so it
## always slides past where you were standing and spends `recover` seconds
## dazed with its back to you. That is the counter-attack window.
##
## It only spots what it is facing, inside `sight_range`, within `sight_band`
## vertically, and only down a line with no solid tile in it — walking behind
## a pillar really does break the lock.

enum St { PATROL, WINDUP, CHARGE, RECOVER }

var st: St = St.PATROL
var t := 0.0
var _turn_cooldown := 0.0

func on_respawn() -> void:
	st = St.PATROL
	t = 0.0
	_turn_cooldown = 0.0
	set_anim("move")

func think(delta: float) -> void:
	apply_gravity(delta)
	t = maxf(0.0, t - delta)
	_turn_cooldown = maxf(0.0, _turn_cooldown - delta)
	match st:
		St.PATROL:
			_patrol(delta)
		St.WINDUP:
			_windup()
		St.CHARGE:
			_charge()
		St.RECOVER:
			_recover(delta)

# ---------------------------------------------------------------- states
func _patrol(_delta: float) -> void:
	set_anim("move")
	if on_floor and _turn_cooldown <= 0.0:
		var blocked := against_wall == facing
		var ledge := bool(cfg.get("turn_at_ledge", true)) \
			and not ground_ahead(facing, float(cfg.get("ledge_lookahead", 2.0)))
		if blocked or ledge:
			facing = -facing
			_turn_cooldown = float(cfg.get("turn_cooldown", 0.15))
	vel.x = speed * facing
	# Only charges from the ground: a boar that spots you mid-fall would launch
	# itself across a pit and die on its own charge.
	if on_floor and sees_player():
		_enter_windup()

func _enter_windup() -> void:
	st = St.WINDUP
	t = float(cfg.get("wind_up", 0.55))
	vel.x = 0.0
	set_anim("windup")
	AudioManager.play(String(cfg.get("sfx_windup", "blip")))

## Stationary, and deliberately unconditional: the wind-up cannot be cut short
## by the player leaving, because a telegraph you can cancel is not a promise.
func _windup() -> void:
	vel.x = 0.0
	set_anim("windup")
	if t <= 0.0:
		st = St.CHARGE
		t = float(cfg.get("charge_time", 0.85))
		set_anim("charge")
		AudioManager.play(String(cfg.get("sfx_charge", "hop")))
		Fx.burst("dust", feet(), Vector2(-float(facing), -0.4))

func _charge() -> void:
	set_anim("charge")
	vel.x = float(cfg.get("charge_speed", 160.0)) * facing
	if against_wall == facing:
		_stagger(float(cfg.get("wall_recover", 1.3)))
		return
	# No ledge check here on purpose — committing is what makes the charge
	# readable, and a level that puts a pit in front of one means it.
	if not bool(cfg.get("charge_commits", true)) and on_floor \
			and not ground_ahead(facing, float(cfg.get("ledge_lookahead", 2.0))):
		_stagger(float(cfg.get("recover", 0.9)))
		return
	if t <= 0.0:
		_stagger(float(cfg.get("recover", 0.9)))

func _stagger(seconds: float) -> void:
	st = St.RECOVER
	t = seconds
	set_anim("dazed")
	AudioManager.play(String(cfg.get("sfx_stagger", "land")))
	Fx.burst("dust", feet(), Vector2(-float(facing), -0.6))

func _recover(delta: float) -> void:
	set_anim("dazed")
	# The overshoot. It does not stop where the charge ended; it slides past.
	vel.x = move_toward(vel.x, 0.0, float(cfg.get("skid_decel", 240.0)) * delta)
	if t <= 0.0:
		st = St.PATROL
		set_anim("move")

# ---------------------------------------------------------------- sight
## Facing, in range, roughly level, and nothing solid in between.
func sees_player() -> bool:
	var p := player()
	if p == null or p.dead:
		return false
	var d := p.center() - center()
	if d.x * float(facing) <= 0.0:
		return false
	if absf(d.x) > float(cfg.get("sight_range", 140.0)):
		return false
	if absf(d.y) > float(cfg.get("sight_band", 20.0)):
		return false
	return line_is_clear(center(), p.center())

## Samples the eye line every `sight_step` pixels. Coarser than the collision
## sweep, and deliberately so: this asks "is there a wall between us", not
## "would a 1 px gap let a photon through".
func line_is_clear(from: Vector2, to: Vector2) -> bool:
	if world == null:
		return false
	var d := to - from
	var steps := int(ceilf(d.length() / maxf(1.0, float(cfg.get("sight_step", 6.0)))))
	for i in range(1, steps):
		var q := from + d * (float(i) / float(steps))
		if TileCollision.solid_at_pixel(world, q.x, q.y):
			return false
	return true
