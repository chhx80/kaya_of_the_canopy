extends Enemy
## THE GROVE WARDEN. Three scripted phases driven entirely by
## data/enemies/boss_grove.json — the fight is tuned without touching code.
##
##   STOMP  walk, leap, land with a shockwave that runs along the floor
##   LEAP   faster, higher, and it calls in beetles
##   FURY   adds a spray of spores between slams
##
## The camera is locked to its arena (Enemy.arena) while it is alive.

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
	var origin := arena.position
	var inset := float(cfg.get("arena_inset", 8.0))
	arena_min = origin.x + inset
	arena_max = origin.x + arena.size.x - inset - box.x
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
				_phase_break()

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
			# It looms rather than shoves. Measured with the sloppy player
			# (tools/bossgate.sh --sloppy): half of every hit a phone-handed run
			# took was the Warden simply walking into her — no tell, no attack,
			# 42 px of body she cannot jump. Inside `loom_gap` px of her it
			# stands its ground and lets the slam be the threat. The body still
			# hurts, so walking into it, or under its landing, still costs.
			if p != null and not p.dead and _gap_to(p) < float(phase_cfg.get("loom_gap", 0.0)):
				vel.x = 0.0
				set_anim("idle")
			if pos.x <= arena_min and facing < 0:
				facing = 1
			elif pos.x >= arena_max and facing > 0:
				facing = -1
			if t <= 0.0 and on_floor:
				st = St.WINDUP
				t = float(phase_cfg.get("windup_time", 0.45))
				_tell("slam")
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

## CONTACT. Its body hurts only while it is attacking with it — the leap and
## the landing, the states `contact.hurts_in` names. Touching it otherwise is a
## shove: she is pushed clear for `contact.shove_time` seconds and keeps her
## heart. Measured with the sloppy player before this: with the Warden looming
## instead of walking into her, body contact was STILL the largest single cause
## of hits on phone hands — 76 of 179 over thirty fights — nearly all of it a
## late thumb carrying her one step too far while it stood, wound up or sprayed.
## A boss you cannot jump has to be a wall you can bump, or the fight is decided
## by a 200 ms input lag instead of by reading it. No `contact` block keeps the
## old rule: every touch is a hit.
func _touch_player() -> void:
	var rule: Dictionary = cfg.get("contact", {})
	if rule.is_empty():
		super._touch_player()
		return
	var p := player()
	if p == null or p.dead or not aabb().intersects(p.aabb()):
		return
	var hurts: Array = rule.get("hurts_in", [])
	if St.keys()[st] in hurts:
		p.take_damage(contact_damage, center() - p.center())
		return
	if p.hurt_t > 0.0:
		return
	var shove: Array = rule.get("shove", [160.0, -90.0])
	var dir := 1.0 if p.center().x > center().x else -1.0
	p.vel = Vector2(float(shove[0]) * dir, float(shove[1]))
	p.hurt_t = float(rule.get("shove_time", 0.15))

## Daylight between the Warden's body and hers, in x. Negative when they overlap.
func _gap_to(p: Player) -> float:
	return absf(p.center().x - center().x) - (box.x + p.box.x) * 0.5

func _maybe_spray(delta: float) -> void:
	if int(phase_cfg.get("spray", 0)) <= 0:
		return
	spray_t = maxf(0.0, spray_t - delta)
	if spray_t <= 0.0:
		spray_t = float(phase_cfg.get("spray_interval", 2.0))
		st = St.SPRAY
		t = float(phase_cfg.get("spray_windup", 0.4))
		_tell("spray")

## THE TELLS. Measured with `tools/bossgate.sh --tells` before this existed: the
## slam crouched for 28 frames and the spray for 25, in the SAME pose, with no
## sound until the attack itself — so on a phone, where a thumb is slower than a
## key, the spray was a shot out of nothing and a player could not tell which of
## the two was coming. Each now has its own sound and its own look, both named in
## data/enemies/boss_grove.json's `tells`: the slam stamps dust at its feet, the
## spray glows (see `_update_anim`) and sheds a shimmer at its mouth.
func _tell(kind: String) -> void:
	var tells: Dictionary = cfg.get("tells", {})
	var tell: Dictionary = tells.get(kind, {})
	if tell.is_empty():
		return
	var sfx := String(tell.get("sfx", ""))
	if sfx != "":
		AudioManager.play(sfx)
	var fx := String(tell.get("fx", ""))
	if fx != "":
		var at := Vector2(center().x, pos.y + box.y) if kind == "slam" \
			else center() + Vector2(float(facing) * box.x * 0.5, -6.0)
		Fx.burst(fx, at)

## The spray's glow: a pulse of `tells.spray.tint` over the frame for as long as
## the spray is winding up. Applied after Enemy's own write of `sprite.modulate`
## (white, or the damage flash), which is the same order brood_queen.gd uses.
func _update_anim(delta: float) -> void:
	super._update_anim(delta)
	if sprite == null or st != St.SPRAY or _flash > 0.0:
		return
	var tell: Dictionary = (cfg.get("tells", {}) as Dictionary).get("spray", {})
	var tint: Array = tell.get("tint", [])
	if tint.size() < 3:
		return
	var hz := float(tell.get("pulse_hz", 6.0))
	var k := 0.5 + 0.5 * sin(t * TAU * hz)
	sprite.modulate = Color.WHITE.lerp(Color(float(tint[0]), float(tint[1]), float(tint[2])), k)

## THE PHASE BREAK. A phase used to change on the frame of the hit that crossed
## the threshold: the Warden went faster mid-stride, with nothing to say a new
## fight had started. Now it staggers for `phase_break.pause` seconds — standing,
## no slam, no spray — and drops `phase_break.drop` (a heart) at the end of the
## floor on Kaya's side of it, inside the margin `arena_inset` keeps its body out
## of: somewhere it cannot follow, and never on the far side of the Warden, which
## she cannot jump. The first version dropped it at the end furthest from the
## Warden, and the sloppy-player measurement walked into its body going for it. Applied on the threshold crossing
## only, never by `_set_phase()`: the boss gate's fairness sweep sets phases
## directly and is not a fight anyone has earned a heart in.
func _phase_break() -> void:
	var brk: Dictionary = cfg.get("phase_break", {})
	if brk.is_empty():
		return
	st = St.IDLE
	t = float(brk.get("pause", 0.0))
	vel.x = 0.0
	spray_t = float(phase_cfg.get("spray_interval", 2.0))
	var shake := String(brk.get("shake", ""))
	if shake != "":
		Fx.shake(shake)
	# A new phase starts clean: the beetles it called in scatter. Measured with
	# the sloppy player, FURY was where 102 of 169 hits landed, with LEAP's
	# garrison still on the floor under a faster slam and a spray.
	if bool(brk.get("clear_adds", false)):
		for e in _adds():
			e.die(e.center())
	var drop := String(brk.get("drop", ""))
	if drop == "" or level == null:
		return
	var origin := arena.position
	var margin := float(brk.get("drop_margin", 40.0))
	var x := origin.x + margin
	var p := player()
	var kaya_x := p.center().x if p != null else origin.x
	if kaya_x > center().x:
		x = origin.x + arena.size.x - margin - 16.0
	level.spawn_entity({
		"type": drop,
		"px": x,
		"py": spawn_pos.y + box.y - 16.0,
		"from_drop": true,
	})

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
	# How far the wave runs is its reach, and the ends of the floor are only
	# somewhere to run TO while it falls short of them: at 1.6 s a wave crossed
	# the whole arena from anywhere the Warden can land, so the only answer to
	# every slam was a jump timed to the frame.
	pj["life"] = float(phase_cfg.get("shockwave_life", 1.6))
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
	#
	# And they arrive at the end of the floor FURTHEST from Kaya. The two ends are
	# the only floor the Warden's body cannot reach, so they are where a player
	# goes to breathe — and the first beetle always used to land on the west one,
	# which is where she starts. Measured with the sloppy player: beetles dropped
	# on her refuge were a third of every hit it took in LEAP.
	var live := live_adds()
	var cap := int(cfg.get("max_adds", 4))
	var origin := arena.position
	var ends: Array[float] = [origin.x + 40.0, origin.x + arena.size.x - 56.0]
	var p := player()
	if p != null and absf(p.center().x - ends[0]) < absf(p.center().x - ends[1]):
		ends.reverse()
	for i in int(phase_cfg.get("spawn_adds", 0)):
		if level == null or live >= cap:
			continue
		live += 1
		level.spawn_entity({
			"type": "enemy_walker",
			"px": ends[i % ends.size()],
			"py": pos.y - 8.0,
		})

## How many hostile bodies are standing in the arena. Counted from the live scene
## rather than tallied on spawn, so a beetle that walks into the blade comes off
## the books — and counted *by screen*, because every other enemy in the level is
## in the same `enemies` group: jungle_5 authors eight of them across its other
## three screens, and counting those would mean the garrison was full before the
## fight started and the Warden never called anyone.
func live_adds() -> int:
	return _adds().size()

func _adds() -> Array[Enemy]:
	var out: Array[Enemy] = []
	for node in get_tree().get_nodes_in_group(&"enemies"):
		var e := node as Enemy
		if e == null or e == self or not is_instance_valid(e) or e.level != level:
			continue
		if not arena.has_point(e.center()):
			continue
		out.append(e)
	return out

func die(from: Vector2 = Vector2.ZERO) -> void:
	if defeated:
		return
	defeated = true
	super.die(from)
	if level != null and level.has_method("on_boss_defeated"):
		level.on_boss_defeated(self)
