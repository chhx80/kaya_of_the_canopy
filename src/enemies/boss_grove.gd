extends Enemy
## THE GROVE WARDEN. Three scripted phases driven entirely by
## data/enemies/boss_grove.json — the fight is tuned without touching code.
##
##   STOMP  walk, leap, land with a shockwave that runs along the floor
##   LEAP   faster, higher, and it calls in beetles
##   FURY   adds a spray of spores between slams
##
## The arena is screen-locked: the camera never flips while it is alive.

enum St { IDLE, WALK, WINDUP, AIR, LAND, SPRAY }

var st: St = St.IDLE
var t := 0.0
var phase := 0
var phase_cfg: Dictionary = {}
var spray_t := 0.0
var arena_min := 0.0
var arena_max := 0.0
var defeated := false

func on_configured() -> void:
	_set_phase(0)

func _ready() -> void:
	super._ready()
	add_to_group(&"bosses")
	# Lock the boss to the screen it spawned on.
	var origin := Screen.origin(home_screen)
	arena_min = origin.x + 8.0
	arena_max = origin.x + Screen.W - 8.0 - box.x
	t = 0.9

func on_respawn() -> void:
	st = St.IDLE
	t = 0.9
	_set_phase(0)

func _set_phase(i: int) -> void:
	var phases: Array = cfg.get("phases", [])
	if phases.is_empty():
		return
	phase = clampi(i, 0, phases.size() - 1)
	phase_cfg = phases[phase]
	spray_t = float(phase_cfg.get("spray_interval", 2.0))

func phase_name() -> String:
	return String(phase_cfg.get("name", ""))

func hurt(amount: int, from: Vector2 = Vector2.ZERO) -> void:
	super.hurt(amount, from)
	# Phase boundaries are health thresholds, so a burst of damage can skip one.
	var phases: Array = cfg.get("phases", [])
	for i in phases.size():
		if health <= int((phases[i] as Dictionary).get("until_health", 0)) and i + 1 < phases.size():
			if phase < i + 1:
				_set_phase(i + 1)
				AudioManager.play("boss_phase")

func think(delta: float) -> void:
	apply_gravity(delta)
	t = maxf(0.0, t - delta)
	var p := player()
	var walk: float = float(phase_cfg.get("walk_speed", 46.0))

	match st:
		St.IDLE:
			vel.x = move_toward(vel.x, 0.0, 400.0 * delta)
			set_anim("idle")
			if t <= 0.0:
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 2.4))
		St.WALK:
			set_anim("walk")
			if p != null and not p.dead:
				facing = 1 if p.center().x > center().x else -1
			vel.x = walk * facing
			if pos.x <= arena_min and facing < 0:
				facing = 1
			elif pos.x >= arena_max and facing > 0:
				facing = -1
			if t <= 0.0 and on_floor:
				st = St.WINDUP
				t = 0.45
			_maybe_spray(delta)
		St.WINDUP:
			vel.x = move_toward(vel.x, 0.0, 900.0 * delta)
			set_anim("windup")
			if t <= 0.0:
				vel.y = float(phase_cfg.get("slam_jump", -250.0))
				vel.x = walk * 1.6 * facing
				st = St.AIR
				AudioManager.play("boss_jump")
		St.AIR:
			set_anim("air")
			if pos.x <= arena_min or pos.x >= arena_max:
				vel.x = -vel.x
				facing = -facing
			if on_floor and vel.y >= 0.0:
				_land()
				st = St.LAND
				t = 0.5
		St.LAND:
			vel.x = move_toward(vel.x, 0.0, 700.0 * delta)
			set_anim("idle")
			if t <= 0.0:
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 2.4))
		St.SPRAY:
			vel.x = 0.0
			set_anim("windup")
			if t <= 0.0:
				_spray()
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 2.4))
	pos.x = clampf(pos.x, arena_min, arena_max)

func _maybe_spray(delta: float) -> void:
	if int(phase_cfg.get("spray", 0)) <= 0:
		return
	spray_t = maxf(0.0, spray_t - delta)
	if spray_t <= 0.0:
		spray_t = float(phase_cfg.get("spray_interval", 2.0))
		st = St.SPRAY
		t = 0.4

func _spray() -> void:
	var n := int(phase_cfg.get("spray", 5))
	var pj: Dictionary = cfg.get("projectile", {})
	for i in n:
		var a := lerpf(-0.9, 0.9, float(i) / maxf(1.0, float(n - 1)))
		var dir := Vector2(sin(a) * float(facing), -cos(a) * 0.6 - 0.35)
		var shot := Projectile.new()
		shot.setup(pj, center() + Vector2(0, -6), dir, world, level)
		level.entities.add_child(shot)
	AudioManager.play("spit")

func _land() -> void:
	AudioManager.play("boss_land")
	# A shockwave along the floor in both directions.
	var pj: Dictionary = (cfg.get("projectile", {}) as Dictionary).duplicate()
	pj["speed"] = float(phase_cfg.get("shockwave_speed", 132.0))
	pj["gravity"] = 0.0
	pj["life"] = 1.6
	pj["frame"] = 1
	for dir in [Vector2.LEFT, Vector2.RIGHT]:
		var shot := Projectile.new()
		shot.setup(pj, Vector2(center().x, pos.y + box.y - 4.0), dir, world, level)
		level.entities.add_child(shot)
	# Reinforcements.
	var adds := int(phase_cfg.get("spawn_adds", 0))
	for i in adds:
		if level == null:
			continue
		var origin := Screen.origin(home_screen)
		level.spawn_entity({
			"type": "enemy_walker",
			"px": origin.x + 40.0 + float(i) * (Screen.W - 96.0),
			"py": pos.y - 8.0,
		})

func die(from: Vector2 = Vector2.ZERO) -> void:
	if defeated:
		return
	defeated = true
	super.die(from)
	if level != null and level.has_method("on_boss_defeated"):
		level.on_boss_defeated(self)
