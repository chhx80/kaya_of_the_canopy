extends Enemy
## THE BROOD QUEEN — World 4's boss. Three scripted phases driven entirely by
## data/enemies/brood_queen.json, the same data-driven machine as
## src/enemies/boss_grove.gd, tide_maw.gd and stormcrest.gd and deliberately not
## a fourth one:
##
##   BROOD   she crawls, rears, and burrows at you; the surfacing slam throws a
##           wave along the floor both ways.
##   SWARM   faster, she calls soldiers out of the comb, and between charges she
##           drums the roof down on you.
##   HATCH   fastest, wider spore falls, and the abdomen has split.
##
## Two things here are not in the other three bosses.
##
## **She is only drawn while she is attacking.** docs/plan-20-levels.md's sentence
## for this fight is "the arena is dark; she is visible only when she attacks, or
## lit by breaking a luminous wall". Darkness in this game is `Ambience` — two
## quads, visual only, unable to reach a tile flag or a form, which is what lets
## the Route Prover prove a World 4 level at all (ADR 005;
## tests/test_verbs_darkness.gd holds the whole feature to it). So "visible only
## when she attacks" has to be a RENDERING behaviour too, and it is exactly that:
## `_update_anim()` writes `sprite.modulate.a` and nothing else in this file,
## nothing in the collision and nothing in her own decisions can see the number.
## The gate's dodge sweep is mechanical and ignores rendering, which is correct
## and is why it cannot answer the question this mechanic raises; see
## tests/integration/boss_brood_queen_tests.gd, which asks it directly.
##
## **The luminous walls are the player's to spend, and they do not come back.**
## The Maw floods its arena and drains it; the Stormcrest raises a gale and drops
## it. Both are the BOSS changing the world and both restore it, because a boss
## that edits a level is a boss that can break one. This Queen writes nothing at
## all. The two luminous walls in levels/deeps_5.json are ordinary breakable
## tiles, and it is Kaya who breaks them — for light, at the price of the cover
## she was standing behind, permanently. All this file does is *notice*:
##
##   * `lit_fraction()` is how many of them are gone, and it lifts the floor her
##     sprite fades to. Break both and she is fully drawn for the rest of the
##     fight. That is the trade, in one number.
##   * `_watch_the_walls()` rebuilds the level's light layer when one goes, so
##     the `emissive` pool data/ambience.json binds to tile 214 dies WITH the
##     tile. `AmbienceLayer` only recollects emissive tiles when its view
##     changes, and a boss arena locks the camera — so without this the wall
##     would shatter and its glow would stay hanging in the air.
##
## **What darkness is allowed to hide, and what it is not.** Everything in this
## fight that can take a heart off you is either a `Projectile` — the floor wave
## and the spore fall, both entities, and `Level` draws entities *over* the
## ambience layers, so neither is ever dimmed by one pixel — or the Queen's own
## body. Her body is full brightness on every frame of every attack, and while
## she is dim and crawling she pushes a ripple of earth ahead of her every
## `crawl_cue` seconds (`Fx.burst`, which is the particle field, which is also
## drawn over the darkness). So her POSITION is always legible and her INTENT is
## always legible; what the dark takes away is her shape, which is atmosphere.
## The suite asserts both halves of that rather than asserting the alpha.
##
## The states, and the fact that they are the same six in the same order as the
## other three bosses: tests/integration/boss_gate_checks.gd names an attack by
## the state transition it fired on and reads those names out of a fixed list, so
## the floor wave is "AIR>LAND" and the spore fall is "SPRAY>WALK" here exactly
## as the Warden's slam and spray are. AIR is not a jump — this animal never
## leaves the ground — it is the burrow charge, and it keeps the name because the
## name is a contract with the gate and not a description.
enum St { IDLE, WALK, WINDUP, AIR, LAND, SPRAY }

var st: St = St.IDLE
var t := 0.0
var phase := 0
var phase_cfg: Dictionary = {}
var spore_t := 0.0
## What was left of the slam timer when a spore fall interrupted it.
var _slam_left := 0.0
var arena_min := 0.0
var arena_max := 0.0
var defeated := false

## The floor her own spawn defines, and the timers behind the two cues.
var floor_y := 0.0
var _cue_t := 0.0
var _rumble_t := 0.0
var _rumble_i := 0
## Frames since she last put anything visible on the floor. Read by the suite:
## a boss you cannot see is fair only while you can see where she is.
var frames_since_cue := 0
var cues := 0

## The luminous walls, captured once, and how many of them are gone.
var _walls: Array[Vector2i] = []
var _walls_open := -1
var _glow_tile := 0

## Her drawn alpha this frame, and the fade left after an attack ends.
var _reveal := 0.0
var alpha := 1.0

func on_configured() -> void:
	_glow_tile = int((cfg.get("glow", {}) as Dictionary).get("tile", 0))
	_capture_walls()
	_set_phase(0)

func _ready() -> void:
	super._ready()
	add_to_group(&"bosses")
	# Clamped to a span inside the screen it spawned on, not to the screen:
	# `arena_inset` is tide_maw.gd's mechanism and this is the same use of it. The
	# ends of the arena floor — and both brood cells — become places her body
	# never goes, which is what makes them places to stand.
	var origin := Screen.origin(home_screen)
	var inset := float(cfg.get("arena_inset", 8.0))
	arena_min = origin.x + inset
	arena_max = origin.x + Screen.W - inset - box.x
	# The floor is wherever the level stood her, not a row written twice. An
	# arena and a boss that disagree about where the floor is have no chance.
	floor_y = spawn_pos.y + box.y
	# One-way shelves are not floors to her: without this the charge ends ON a
	# refuge and she stands there, which is both absurd and the end of the dodge
	# window that shelf exists to be. Same line, same reason, as the other three.
	drop_through = true
	t = 0.9

func on_respawn() -> void:
	st = St.IDLE
	t = 0.9
	_cue_t = 0.0
	_rumble_t = 0.0
	_rumble_i = 0
	_reveal = 0.0
	drop_through = true
	_set_phase(0)

func _set_phase(i: int) -> void:
	var phases: Array = cfg.get("phases", [])
	if phases.is_empty():
		return
	phase = clampi(i, 0, phases.size() - 1)
	phase_cfg = phases[phase]
	spore_t = float(phase_cfg.get("spore_interval", 2.4))

## BROOD, SWARM and HATCH are three animals, not three tints, so each pose exists
## once per phase in data/enemies/brood_queen.json as `<pose>_p1/_p2/_p3`.
## Anything without a per-phase variant falls back to the plain name, so the
## state machine below never has to know about this.
func set_anim(pose: String) -> void:
	var key := "%s_p%d" % [pose, phase + 1]
	var anims: Dictionary = cfg.get("anim", {})
	super.set_anim(key if anims.has(key) else pose)

func hurt(amount: int, from: Vector2 = Vector2.ZERO) -> void:
	super.hurt(amount, from)
	# The killing blow is not a phase change. `Enemy.hurt()` calls `die()` inside
	# the line above, and then this loop used to run anyway, find health at 0 and
	# escalate a corpse all the way to HATCH. stormcrest.gd records what that cost
	# on a boss that writes to the level; it is cheaper here and it is still a lie
	# in every screenshot and every phase counter, so it is guarded the same way.
	if defeated or health <= 0:
		return
	# Phase boundaries are health thresholds, so a burst of damage can skip one.
	var phases: Array = cfg.get("phases", [])
	for i in phases.size():
		if health <= int((phases[i] as Dictionary).get("until_health", 0)) and i + 1 < phases.size():
			if phase < i + 1:
				_set_phase(i + 1)
				AudioManager.play("boss_phase")

# ------------------------------------------------------------ the luminous walls
## Remember where the level drew them, once. Everything after this is counting.
func _capture_walls() -> void:
	_walls = []
	_walls_open = -1
	var g: Dictionary = cfg.get("glow", {})
	if world == null or g.is_empty() or _glow_tile == 0:
		return
	var x0 := int(g.get("x", 0))
	var y0 := int(g.get("y", 0))
	for j in int(g.get("h", 0)):
		for i in int(g.get("w", 0)):
			if world.get_fg(x0 + i, y0 + j) == _glow_tile:
				_walls.append(Vector2i(x0 + i, y0 + j))

## 0.0 with every wall standing, 1.0 with every one of them broken.
func lit_fraction() -> float:
	if _walls.is_empty():
		return 0.0
	return clampf(float(maxi(0, _walls_open)) / float(_walls.size()), 0.0, 1.0)

func walls_broken() -> int:
	return maxi(0, _walls_open)

func walls_total() -> int:
	return _walls.size()

## Count what is left, and if it changed, make the light change with it.
func _watch_the_walls() -> void:
	if world == null or _walls.is_empty():
		return
	var open := 0
	for w: Vector2i in _walls:
		if world.get_fg(w.x, w.y) != _glow_tile:
			open += 1
	if open == _walls_open:
		return
	_walls_open = open
	_relight()

## Making a broken wall DARK, which is a separate problem from breaking it.
##
## `AmbienceLayer` scans the visible tiles for `emissive` ids once, when its view
## changes (`_rebuild`), because on an ordinary level a screen flip is the only
## thing that can change the answer. A boss arena locks the camera, so the view
## never changes, so the pool bound to tile 214 would go on being drawn over the
## hole where the wall used to be — a lamp with nothing holding it up. One
## re-collect per wall broken is the whole fix, and it is here rather than in
## src/world/level.gd because this is the only place in the game where a
## breakable tile is also a light and the camera is nailed down.
func _relight() -> void:
	if level == null:
		return
	var lights: Node = level.get("lights")
	if lights == null or not lights.has_method("setup"):
		return
	lights.call("setup", lights.get("role"), lights.get("amb"), lights.get("world"))

# ---------------------------------------------------------------- the fight
func think(delta: float) -> void:
	drop_through = true
	apply_gravity(delta)
	t = maxf(0.0, t - delta)
	_reveal = maxf(0.0, _reveal - delta)
	frames_since_cue += 1
	_watch_the_walls()
	var p := player()
	var walk: float = float(phase_cfg.get("walk_speed", 42.0))

	match st:
		St.IDLE:
			vel.x = move_toward(vel.x, 0.0, 400.0 * delta)
			set_anim("idle")
			# Settling, and still shifting the earth under her. The cue runs here
			# as well as in the crawl because IDLE is a state she spends dim, and
			# a state that is both dim and silent is the one hole a dark fight can
			# have — tests/integration/boss_brood_queen_tests.gd measures the
			# longest such gap directly and this is what closes it.
			_crawl_cue(delta)
			if t <= 0.0:
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 1.7))
		St.WALK:
			set_anim("walk")
			if p != null and not p.dead:
				facing = 1 if p.center().x > center().x else -1
			vel.x = walk * facing
			if pos.x <= arena_min and facing < 0:
				facing = 1
			elif pos.x >= arena_max and facing > 0:
				facing = -1
			_crawl_cue(delta)
			if t <= 0.0 and on_floor:
				# Which way she will burrow, decided HERE and not on the frame she
				# surfaces, so the rumble line below and the charge agree. Facing
				# away from the wall she is against, because a charge that ends on
				# the frame it starts merges the telegraph and the attack into one
				# state transition and the gate would tag it as a third attack it
				# then demands to see on every tile.
				if pos.x <= arena_min + 8.0:
					facing = 1
				elif pos.x >= arena_max - 8.0:
					facing = -1
				st = St.WINDUP
				t = float(cfg.get("windup_time", 0.62))
				_rumble_i = 0
				_rumble_t = 0.0
			_maybe_spores(delta)
		St.WINDUP:
			vel.x = move_toward(vel.x, 0.0, 900.0 * delta)
			set_anim("windup")
			_rumble(delta)
			if t <= 0.0:
				st = St.AIR
				t = float(phase_cfg.get("charge_time", 0.8))
				vel.x = float(phase_cfg.get("charge_speed", 124.0)) * facing
				AudioManager.play("boss_jump")
		St.AIR:
			set_anim("air")
			vel.x = float(phase_cfg.get("charge_speed", 124.0)) * facing
			_crawl_cue(delta)
			if t <= 0.0 or pos.x <= arena_min or pos.x >= arena_max:
				_slam()
				st = St.LAND
				t = float(cfg.get("land_time", 0.55))
		St.LAND:
			vel.x = move_toward(vel.x, 0.0, 700.0 * delta)
			set_anim("land")
			if t <= 0.0:
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 1.7))
		St.SPRAY:
			vel.x = move_toward(vel.x, 0.0, 500.0 * delta)
			set_anim("windup")
			if t <= 0.0:
				_spores()
				st = St.WALK
				# Back onto the slam timer she left, NOT onto a fresh one.
				# `spore_interval` is shorter than `slam_interval`, so a fresh
				# timer here would re-arm the charge forever and the fight would
				# be a spore fall and nothing else — the bug stormcrest.gd
				# measured on its own volley and wrote down.
				t = maxf(0.05, _slam_left)
	_hold_the_arena(delta)

## Check 4 of the boss gate is "the boss stays inside arena_min/arena_max", and it
## is measured at the END of the physics frame — after `step_motion()`, which runs
## after `think()`. Clamping the position here and then moving is the bug the
## Grove Warden shipped: it reported 4,502 frames outside its own arena. So the
## clamp bites on the VELOCITY, before the move that would use it, and the
## position clamp stays as the backstop. She has no ceiling to hold because she
## never leaves the floor.
func _hold_the_arena(delta: float) -> void:
	pos.x = clampf(pos.x, arena_min, arena_max)
	if delta <= 0.0:
		return
	var next_x := pos.x + vel.x * delta
	if next_x < arena_min:
		vel.x = (arena_min - pos.x) / delta
	elif next_x > arena_max:
		vel.x = (arena_max - pos.x) / delta

# ---------------------------------------------------------------- the cues
## The ripple of earth she pushes ahead of herself while she crawls. This is the
## fight's answer to its own darkness: particles are drawn over the shade quad,
## so where she is is never a secret even when what she is stays one.
func _crawl_cue(delta: float) -> void:
	var every := float(cfg.get("crawl_cue", 0.22))
	if every <= 0.0:
		return
	_cue_t -= delta
	if _cue_t > 0.0:
		return
	_cue_t = every
	_emit_cue(center().x + float(facing) * box.x * 0.4)

## The rumble line: a run of dust walking out along the floor ahead of her during
## the windup, in the direction she is about to burrow. It is the telegraph, and
## it is the telegraph precisely because it is made of particles — the one kind of
## thing in this game a dark level cannot dim.
func _rumble(delta: float) -> void:
	var every := float(cfg.get("rumble_interval", 0.07))
	if every <= 0.0:
		return
	_rumble_t -= delta
	if _rumble_t > 0.0:
		return
	_rumble_t = every
	_rumble_i += 1
	var step := float(cfg.get("rumble_step", 14.0))
	_emit_cue(center().x + float(facing) * (box.x * 0.5 + float(_rumble_i) * step))

func _emit_cue(x: float) -> void:
	cues += 1
	frames_since_cue = 0
	Fx.burst("dust", Vector2(clampf(x, arena_min, arena_max + box.x), floor_y - 3.0))

# ---------------------------------------------------------------- the attacks
## The floor wave: she surfaces, and the shock runs the floor in both directions
## four pixels up. It is the fight's main attack and it is dodged by being 32 px
## over the floor on a one-way shelf, or by standing behind a luminous wall —
## which is a solid tile, so the wave dies on it, which is the whole of the trade
## this level is about.
func _slam() -> void:
	AudioManager.play("boss_land")
	Fx.shake("boss_slam")
	Fx.burst("dust", Vector2(center().x, pos.y + box.y))
	_emit_cue(center().x)
	var pj: Dictionary = (cfg.get("projectile", {}) as Dictionary).duplicate()
	pj["speed"] = float(phase_cfg.get("wave_speed", 132.0))
	pj["gravity"] = 0.0
	pj["life"] = float(phase_cfg.get("wave_life", 1.7))
	pj["frame"] = 1
	for dir in [Vector2.LEFT, Vector2.RIGHT]:
		var shot := Projectile.new()
		shot.setup(pj, Vector2(center().x, pos.y + box.y - 4.0), dir, world, level)
		level.entities.add_child(shot)
	_call_the_brood()

## Soldiers out of the comb, up to a garrison size and no further. The cap is the
## Grove Warden's lesson and it is not a style choice: measured there with
## `KAYA_BOSSGATE_MODE=probe KAYA_BOSSGATE_PROBE=adds`, an uncapped call-for-help
## put sixteen bodies in a twenty-two tile arena inside thirty seconds, and past
## about four the player cannot spend them as fast as the boss mints them. She
## still calls on every slam; the arena just holds a fixed garrison.
func _call_the_brood() -> void:
	var n := int(phase_cfg.get("spawn_adds", 0))
	if n <= 0 or level == null:
		return
	var live := live_adds()
	var cap := int(cfg.get("max_adds", 3))
	var kind := String(cfg.get("add_type", "enemy_walker"))
	for i in n:
		if live >= cap:
			return
		live += 1
		var side := -1.0 if (i % 2) == 0 else 1.0
		level.spawn_entity({
			"type": kind,
			"px": clampf(center().x + side * 36.0 - 8.0, arena_min, arena_max),
			"py": floor_y - 32.0,
		})

## How many hostile bodies are standing in the arena. Counted from the live scene
## rather than tallied on spawn, so a soldier that walks into the blade comes off
## the books — and counted *by screen*, because every other enemy in the level is
## in the same `enemies` group: deeps_5 authors three of them in its approach, and
## counting those would mean the garrison was full before the fight started.
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

func _maybe_spores(delta: float) -> void:
	if int(phase_cfg.get("spores", 0)) <= 0:
		return
	spore_t = maxf(0.0, spore_t - delta)
	if spore_t <= 0.0:
		spore_t = float(phase_cfg.get("spore_interval", 2.4))
		_slam_left = t
		st = St.SPRAY
		t = 0.4

## The spore fall: she drums the roof and the comb sheds over the column the
## player is standing in. Thrown from the arena's TOP INTERIOR ROW rather than
## from her mouth, and that is the design, not an implementation shortcut — a
## shot born inside a comb is born inside solid earth and `Projectile` kills it on
## its first frame, so the floor under the two combs is the only place this
## attack cannot reach, and it is a place you can stand, walk to and fight from.
## An arc out of her mouth would have made the dodge a matter of range, which is
## the same dodge the wave already has.
func _spores() -> void:
	var n := int(phase_cfg.get("spores", 0))
	if n <= 0 or level == null:
		return
	var s: Dictionary = cfg.get("spore", {})
	var pj: Dictionary = (cfg.get("projectile", {}) as Dictionary).duplicate()
	pj["speed"] = float(phase_cfg.get("spore_speed", 150.0))
	pj["gravity"] = float(phase_cfg.get("spore_gravity", 40.0))
	pj["life"] = 4.0
	pj["frame"] = 0
	var ts := float(TileData4.TILE_SIZE)
	var p := player()
	var aim := center().x if p == null or p.dead else p.center().x
	# Snapped to the column she is standing in. A fall that lands on tile centres
	# makes the comb's shelter exact instead of approximate: off-grid, a shot
	# could come down eight pixels from a body that is standing under solid rock.
	var col := roundf((aim - ts * 0.5) / ts)
	var spread := float(phase_cfg.get("spore_spread", 32.0))
	var y := float(int(s.get("row", 16))) * ts + ts * 0.5
	var lo := float(int(s.get("x0", 0))) * ts + ts * 0.5
	var hi := float(int(s.get("x1", 0))) * ts + ts * 0.5
	for i in n:
		var f := 0.0 if n <= 1 else float(i) / float(n - 1)
		var x := clampf(col * ts + ts * 0.5 + lerpf(-spread, spread, f), lo, hi)
		var shot := Projectile.new()
		shot.setup(pj, Vector2(x, y), Vector2.DOWN, world, level)
		level.entities.add_child(shot)
	AudioManager.play("spit")

# ---------------------------------------------------------------- the dark
## True on every frame she can be seen for what she is: the three attack states
## and the telegraph that precedes them.
func attacking() -> bool:
	return st == St.WINDUP or st == St.AIR or st == St.LAND or st == St.SPRAY

## What `_update_anim()` will draw her at. A pure function of the fight state, so
## the suite can assert it frame by frame without reaching into a Sprite2D.
##
##   * attacking, or hit: full. The blade finding her is a reveal, which is the
##     right way round — landing a hit should tell you where she is.
##   * otherwise: `dark_alpha`, lifted towards 1.0 by how many luminous walls the
##     player has spent. Break both and she never hides again.
##   * and a fade of `reveal_time` out of every attack, so a slam does not blink
##     out on the frame the wave leaves her.
func visibility() -> float:
	if _flash > 0.0 or attacking():
		return 1.0
	var base := clampf(float(cfg.get("dark_alpha", 0.12)), 0.0, 1.0)
	base = base + (1.0 - base) * lit_fraction()
	var fade := float(cfg.get("reveal_time", 0.5))
	if _reveal > 0.0 and fade > 0.0:
		base = maxf(base, _reveal / fade)
	return clampf(base, 0.0, 1.0)

## `Enemy._update_anim()` rewrites `sprite.modulate` every frame — white, or the
## damage flash — so the alpha has to be applied after it and not instead of it.
## Overriding here rather than reaching in from `think()` is what keeps the two
## in the same frame: think(), then step_motion(), then this.
func _update_anim(delta: float) -> void:
	super._update_anim(delta)
	if attacking():
		_reveal = float(cfg.get("reveal_time", 0.5))
	alpha = visibility()
	if sprite != null:
		sprite.modulate.a = alpha

func die(from: Vector2 = Vector2.ZERO) -> void:
	if defeated:
		return
	defeated = true
	# Note what is NOT here: the walls Kaya broke stay broken. The Maw drains its
	# arena on death and the Stormcrest drops its gale, because both of those were
	# the boss's doing. These were hers.
	super.die(from)
	if level != null and level.has_method("on_boss_defeated"):
		level.on_boss_defeated(self)
