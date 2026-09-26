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
	# Lock the Warden to a span inside the screen it spawned on, not to the screen.
	# It used to inset by a flat 8 px, which is to say it could put its body on
	# every tile of the arena floor including both corners — and since Kaya can no
	# longer jump over it (42 px of hurtbox against a 46 px jump) that left her
	# nowhere at all to retreat to. Measured with KAYA_BOSSGATE_TRACE=1: of five
	# hearts spent in a losing run, four went to its body while the nearest shot
	# was 999 px away. `arena_inset` is src/enemies/tide_maw.gd's mechanism and
	# this is the same use of it — the ends of the floor become somewhere it
	# cannot reach, so distance is an answer the arena actually offers.
	var origin := Screen.origin(home_screen)
	var inset := float(cfg.get("arena_inset", 8.0))
	arena_min = origin.x + inset
	arena_max = origin.x + Screen.W - inset - box.x
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

## STOMP, LEAP and FURY are three different animals, not three tints, so each
## pose exists once per phase in data/enemies/boss_grove.json as
## `<pose>_p1/_p2/_p3`. Anything without a per-phase variant falls back to the
## plain name, so the state machine below never has to know about this.
func set_anim(pose: String) -> void:
	var key := "%s_p%d" % [pose, phase + 1]
	var anims: Dictionary = cfg.get("anim", {})
	super.set_anim(key if anims.has(key) else pose)

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
	# The refuge slabs in jungle_5's arena are one-way platforms inside the span
	# the Warden walks, and its slam clears 39 px against their 32 — so without
	# this it lands ON a refuge and stands there, which is both absurd and the end
	# of the dodge window that slab exists to be. `drop_through` is Actor's own
	# switch for "one-ways are not floors this tick"; the Warden is never anywhere
	# but the arena floor. Same reason, same line, as src/enemies/tide_maw.gd.
	drop_through = true
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
			set_anim("land")
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
	_hold_the_arena(delta)

## Check 4 of the boss gate is "the boss stays inside arena_min/arena_max", and it
## is measured at the END of the physics frame — after `step_motion()`, which runs
## after `think()`. This used to be a bare `pos.x = clampf(...)` here, and it got
## away with it only because the Warden's arena was the whole screen and the
## screen has walls that stopped it two tiles short of its own clamp. With
## `arena_inset` the clamp is what stops it, and clamping the position and then
## moving put it outside its arena on 4,502 frames of the fairness sweep — which
## is a failure, not a rounding error. So the clamp bites on the VELOCITY, before
## the move that would use it, and the position clamp stays as the backstop.
## src/enemies/tide_maw.gd's `_hold_the_arena()` is this, for the same reason; its
## comment names this file as the one that had not needed it yet.
func _hold_the_arena(delta: float) -> void:
	pos.x = clampf(pos.x, arena_min, arena_max)
	if delta <= 0.0:
		return
	var next_x := pos.x + vel.x * delta
	if next_x < arena_min:
		vel.x = (arena_min - pos.x) / delta
	elif next_x > arena_max:
		vel.x = (arena_max - pos.x) / delta

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
	Fx.shake("boss_slam")
	Fx.burst("dust", Vector2(center().x, pos.y + box.y))
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
	# Reinforcements, up to a garrison size and no further. Measured with
	# `KAYA_BOSSGATE_MODE=probe KAYA_BOSSGATE_PROBE=adds` while this was uncapped:
	#
	#   phase 1 LEAP   slam every 1.7s, 2 add(s) per slam | live beetles
	#                  5s:2, 10s:4, 15s:8, 20s:10, 25s:14, 30s:16
	#   phase 2 FURY   slam every 1.2s, 1 add(s) per slam | 30s:7
	#
	# Sixteen beetles in an arena twenty-two tiles wide, and nothing in the fight
	# ever takes one away. The blade needs two hits to clear a beetle and lands
	# about one hit a second, so past about four of them the player cannot spend
	# them as fast as the Warden mints them and the fight stops being decided by
	# play. It still calls for help on every slam; the arena just holds a fixed
	# garrison now.
	var live := live_adds()
	var cap := int(cfg.get("max_adds", 4))
	for i in int(phase_cfg.get("spawn_adds", 0)):
		if level == null or live >= cap:
			continue
		live += 1
		var origin := Screen.origin(home_screen)
		level.spawn_entity({
			"type": "enemy_walker",
			"px": origin.x + 40.0 + float(i) * (Screen.W - 96.0),
			"py": pos.y - 8.0,
		})

## How many hostile bodies are standing in the arena. Counted from the live scene
## rather than tallied on spawn, so a beetle that walks into the blade comes off
## the books — and counted *by screen*, because every other enemy in the level is
## in the same `enemies` group: jungle_5 authors eight of them across its other
## three screens, and counting those would mean the garrison was full before the
## fight started and the Warden never called anyone.
func live_adds() -> int:
	var n := 0
	for node in get_tree().get_nodes_in_group(&"enemies"):
		var e := node as Enemy
		if e == null or e == self or not is_instance_valid(e) or e.level != level:
			continue
		if Screen.index_of(e.center(), Vector2i(999, 999)) != home_screen:
			continue
		n += 1
	return n

func die(from: Vector2 = Vector2.ZERO) -> void:
	if defeated:
		return
	defeated = true
	super.die(from)
	if level != null and level.has_method("on_boss_defeated"):
		level.on_boss_defeated(self)
