extends Enemy
## THE OBSIDIAN HEART — World 5's boss, and the last fight in the game.
##
## Three scripted phases driven entirely by data/enemies/obsidian_heart.json,
## the same data-driven machine as src/enemies/boss_grove.gd, and deliberately
## not a second one:
##
## THREE ATTACKS FOR THREE TIERS, and that is the shape of the arena as much as
## of the fight — the hearthold has exactly three heights a body can stand at and
## each of them is answered by exactly one attack, so each tier is the dodge for
## the other two:
##
##   the BORE    the slam throws a wave along the floor both ways, 4 px up. It
##               cannot climb, so a bay's one-way step is over it.
##   the GLASS   a level volley swept along the STEP band, thrown at exactly the
##               height of a body standing on a step and under a body standing
##               on the floor.
##   the SHED    the vault gives way and shards fall from row 16 down the shelf
##               columns. The comb is solid at that row, so the two floor tiles
##               under it are the only cover it has.
##
## The three phases are the same three attacks, faster and wider, plus the thing
## that actually distinguishes them: the arena itself.
##
##   SEALED    a closed stone with a coal behind it.
##   INVERTED  the glass has split and the nest turns inside out.
##   MOLTEN    the shell is losing, and it calls two chargers off the walls.
##
## What is here and in no other boss is the arena itself.
##
## **THE NEST RECONFIGURES.** Each phase names a switch configuration in its
## block of the JSON, and `_apply_config()` writes it with `TileWorld.set_switch`
## — the same call `src/world/triggers/switch_trigger.gd` makes, because this is
## the machinery the whole world runs on and a boss that invented a second one
## would be a boss whose arena the prover, the reachability filter and the tile
## renderer all disagreed about. Half of levels/nest_5.json's arena is built out
## of `switch_block_*` tiles, so the SAME authored room is three different rooms
## across the fight:
##
##   SEALED    group 1 ON,  group 2 OFF   the frog's bay is open
##   INVERTED  group 1 OFF, group 2 ON    the bird's bay is open
##   MOLTEN    group 1 ON,  group 2 ON    the human's bay is open
##
## **THE ARENA HAS NO LEVER, AND THAT IS A DECISION.** `switch_a`/`switch_b`
## entities and this boss write the same two booleans. A lever inside the arena
## would let the player undo the configuration the phase's dodge is made of, and
## the Heart would silently take it back at the next health threshold — a fight
## in which one of the player's two verbs sometimes does nothing and sometimes
## deletes the floor she is standing on. So nest_5 authors no switch entity
## anywhere, the Heart owns the state, and what that costs is written out in
## tools/worlds/nest_5.py: `reconfig_check`'s "can you always get back to a
## lever" arm has nothing to check, and the module replaces it with the stronger
## claim this level actually needs — in EVERY configuration the Heart can
## produce, the whole arena floor, `boss_exit` and the floor's transform pad are
## one connected set.
##
## **NOTHING IS RESTORED.** THE TIDE MAW puts its water back and THE STORMCREST
## puts its gale away, because for them the change is weather. Here the
## configuration IS the fight, so the arena Kaya walks out of is the one MOLTEN
## left behind. What that costs is exactly one obligation, and the level is
## authored to meet it: `boss_exit` and the way to it must stand in all four
## configurations, not just the seeded one.
##
## **A FLIP MAY NOT CRUSH.** `set_switch` does not push a body out of a tile it
## turns solid; it changes an answer, and the next frame's `move_x`/`move_y`
## find the player already inside geometry. Measured on a body standing on a
## plinth when its plug turns solid, she is left overlapping two solid tiles
## with the collision resolving her *upward* into the next one. So two things
## guard it, and `tests/integration/boss_obsidian_heart_tests.gd` tests both:
##
##   1. a **telegraph and a safe beat**. A health threshold does not flip the
##      nest on the frame it is crossed. `reforge_time` seconds of the Heart
##      standing still, flared, shuddering, with the switch sound and a HUD
##      line, come first.
##   2. **`_make_room_for_player()`**, which runs on the frame the write lands.
##      If her body is inside anything the write made solid she is set down on
##      the arena floor under her own column — the floor is one unbroken cap in
##      every configuration, which is what makes that always possible — with a
##      beat of invulnerability, because the nest moving is not her mistake.

## The same six states, in the same order, as boss_grove.gd, tide_maw.gd,
## stormcrest.gd and brood_queen.gd. Not a coincidence and not free to change:
## tests/integration/boss_gate_checks.gd names an attack by the state transition
## it fired on and reads those names out of a fixed list.
enum St { IDLE, WALK, WINDUP, AIR, LAND, SPRAY }

var st: St = St.IDLE
var t := 0.0
var phase := 0
var phase_cfg: Dictionary = {}
var glass_t := 0.0
var shed_t := 0.0
var arena_min := 0.0
var arena_max := 0.0
var defeated := false

## The reconfiguration.
var _shed: Dictionary = {}
## Which phase the nest is being turned over to, and how long is left of the
## telegraph before it is. -1 means "nothing pending".
var _pending := -1
var _reforge := 0.0
## How many times the nest has actually been written. Read by the suite.
var _flips := 0
## True on the frames the telegraph is running, so the pen and the tests can see
## the safe beat as a fact rather than infer it from a pose.
var reforging := false
## The y of the arena floor's surface, taken from the Heart's own spawn rather
## than written down twice: it stands on that floor, so `spawn_pos.y + box.y` IS
## the floor. `_make_room_for_player()` sets her down on it.
var _floor_y := 0.0
## Which volley of the shed this is. The columns alternate, so two volleys cover
## every refuge column and the gate's two samples per tile see both.
var _volley := 0
## Whether the IDLE the Heart is in was entered to shed. The fight's very first
## IDLE is not, and a shower of glass on frame one would be an attack with no
## telegraph at all.
var _volley_armed := false

func on_configured() -> void:
	_shed = cfg.get("shed", {})
	_set_phase(0)

func _ready() -> void:
	super._ready()
	add_to_group(&"bosses")
	# Lock the Heart to a span inside the screen it spawned on, not to the
	# screen. `arena_inset` is tide_maw.gd's mechanism; this boss needs the
	# stronger form of it, because every switch block in the level has to stand
	# OUTSIDE this span — otherwise a configuration could put a solid tile
	# inside the Heart, or the Heart could be standing in a bay that is about to
	# close, and a boss stuck inside its own moving wall is the failure this
	# number exists to make impossible.
	var origin := Screen.origin(home_screen)
	var cols: Array = cfg.get("arena_cols", [])
	if cols.size() == 2:
		# An EXPLICIT column span, not a symmetric inset, and this is the one
		# boss that needs it. Every other arena in the game is symmetric; this
		# one has three switch-block bays and they are not evenly placed, so the
		# clamp has to name the columns the Heart may occupy rather than a
		# distance from the walls. tools/worlds/nest_5.py's `_self_checks`
		# compares these two numbers against the bays and fails the build if the
		# Heart could ever stand in one.
		arena_min = float(int(cols[0])) * float(TileData4.TILE_SIZE)
		arena_max = float(int(cols[1]) + 1) * float(TileData4.TILE_SIZE) - box.x
	else:
		var inset := float(cfg.get("arena_inset", 8.0))
		arena_min = origin.x + inset
		arena_max = origin.x + Screen.W - inset - box.x
	_floor_y = spawn_pos.y + box.y
	t = 0.9

## `Enemy.set_active_screen()` respawns a boss the first time the camera lands
## on its screen, which is the moment the fight starts — and therefore the
## moment the nest has to be in the configuration phase 1 names. It already is,
## because phase 1 IS `TileWorld`'s seeded default, but asserting it here rather
## than assuming it is what lets an approach with its own levers be added to
## this level later without the fight opening in a room nobody designed.
func on_respawn() -> void:
	st = St.IDLE
	t = 0.9
	_pending = -1
	_reforge = 0.0
	reforging = false
	_set_phase(0)

func _set_phase(i: int) -> void:
	var phases: Array = cfg.get("phases", [])
	if phases.is_empty():
		return
	phase = clampi(i, 0, phases.size() - 1)
	phase_cfg = phases[phase]
	glass_t = float(phase_cfg.get("glass_interval", 2.6))
	shed_t = float(phase_cfg.get("shed_interval", 3.0))
	_pending = -1
	_reforge = 0.0
	reforging = false
	_apply_config()

func phase_name() -> String:
	return String(phase_cfg.get("name", ""))

## SEALED, INVERTED and MOLTEN are three stones, not three tints, so each pose
## exists once per phase in data/enemies/obsidian_heart.json as
## `<pose>_p1/_p2/_p3`. Anything without a per-phase variant falls back to the
## plain name, so the state machine below never has to know about this.
func set_anim(pose: String) -> void:
	var key := "%s_p%d" % [pose, phase + 1]
	var anims: Dictionary = cfg.get("anim", {})
	super.set_anim(key if anims.has(key) else pose)

## A dead boss does not walk its phase thresholds. `Enemy.hurt()` calls `die()`
## the moment health reaches zero, and without this guard the last blade of the
## fight crosses MOLTEN's `until_health` on the same call — arming a telegraph,
## a reconfiguration and a HUD line for a fight that is over, on a node that is
## already fading out. The Warden gets away with the same shape only because its
## last phase is its last threshold.
func hurt(amount: int, from: Vector2 = Vector2.ZERO) -> void:
	if defeated or _dying_now():
		return
	super.hurt(amount, from)
	if defeated or health <= 0:
		return
	# Phase boundaries are health thresholds, so a burst of damage can skip one.
	var phases: Array = cfg.get("phases", [])
	for i in phases.size():
		if health <= int((phases[i] as Dictionary).get("until_health", 0)) and i + 1 < phases.size():
			if phase < i + 1 and _pending < i + 1:
				_begin_reforge(i + 1)

func _dying_now() -> bool:
	var v: Variant = get("_dying")
	return typeof(v) == TYPE_FLOAT and float(v) > 0.0

# ---------------------------------------------------- the reconfiguration
## The telegraph. Nothing about the world changes here — this only says that it
## is about to, loudly enough that a player standing in a bay has time to leave
## it. `AudioManager.play("switch")` is the sound of a mechanism changing state,
## which is exactly what this is and what tide_maw.gd's tide uses it for.
func _begin_reforge(to_phase: int) -> void:
	_pending = to_phase
	_reforge = float(cfg.get("reforge_time", 1.05))
	reforging = true
	st = St.WINDUP
	t = _reforge
	vel.x = 0.0
	AudioManager.play("boss_phase")
	AudioManager.play("switch")
	Fx.burst("spark", center())
	if level != null and level.hud != null and level.hud.has_method("flash_message"):
		var to_name := "THE NEST TURNS"
		var phases: Array = cfg.get("phases", [])
		if to_phase < phases.size():
			to_name = "THE NEST TURNS — %s" \
				% String((phases[to_phase] as Dictionary).get("name", ""))
		level.hud.flash_message(to_name, 1.4)

func _tick_reforge(delta: float) -> void:
	if _pending < 0:
		return
	_reforge -= delta
	# The shudder: one shake per `reforge_shudder` seconds for the whole beat, so
	# the telegraph escalates on screen instead of being a single frame of noise
	# a player could blink past.
	var shudder := float(cfg.get("reforge_shudder", 0.14))
	if shudder > 0.0 and fposmod(_reforge, shudder) < delta:
		Fx.shake("hurt")
	if _reforge <= 0.0:
		var to_phase := _pending
		_pending = -1
		reforging = false
		_set_phase(to_phase)
		st = St.LAND
		t = float(cfg.get("land_time", 0.5))

## Write the phase's switch configuration into the live world.
##
## This is the whole mechanic in four lines, and everything around it is the
## price of those four lines being honest: the repaint, because a tile whose id
## the renderer resolved at setup keeps drawing the cell it was authored with
## (tide_maw.gd measured that: the arena flooded and the screenshot showed dry
## stone); the level callback, because `Level.on_switch_toggled()` is what a
## lever calls and a boss may not be a special case to the layer underneath it;
## and `_make_room_for_player()`, because `set_switch` cannot move a body.
func _apply_config() -> void:
	if world == null:
		return
	var a := bool(phase_cfg.get("switch_a", true))
	var b := bool(phase_cfg.get("switch_b", false))
	if bool(world.switch_states.get(1, true)) == a \
			and bool(world.switch_states.get(2, false)) == b:
		return                                  # already this room
	world.set_switch(1, a)
	world.set_switch(2, b)
	_flips += 1
	if level != null and level.has_method("on_switch_toggled"):
		level.on_switch_toggled(1)
		level.on_switch_toggled(2)
	_make_room_for_player()

## The flip may not crush. If Kaya's body is inside anything the write just made
## solid, set her down on the arena floor under her own column.
##
## The floor is what makes this always possible: levels/nest_5.json caps the
## arena with one unbroken run of plain obsidian at row 27 and puts no switch
## tile on it or in the row above it, in any configuration, so "straight down,
## same column" is always somewhere she fits. It is checked rather than assumed
## — if the column below her is somehow not clear the search walks outward along
## the floor row — and if nothing at all is clear she is left exactly where she
## was, because a boss that teleports the player into a wall to avoid crushing
## her has not solved anything.
func _make_room_for_player() -> void:
	var p := player()
	if p == null or p.dead or level == null:
		return
	if not _rect_hits_solid(p.aabb()):
		return
	var ts := float(TileData4.TILE_SIZE)
	var origin := Screen.origin(home_screen)
	var col := int(floor(p.center().x / ts))
	var col0 := int(origin.x / ts)
	var col1 := col0 + int(Screen.W / ts) - 1
	for step in int(Screen.W / ts):
		for dir in [1, -1]:
			var c: int = col + dir * step
			if c < col0 or c > col1:
				continue
			var where := Vector2(float(c) * ts + (ts - p.box.x) * 0.5,
				_floor_y - p.box.y)
			if _rect_hits_solid(Rect2(where, p.box)):
				continue
			p.pos = where
			p.vel = Vector2.ZERO
			p.drop_through = false
			p.invuln = maxf(p.invuln, 0.8)
			AudioManager.play("land")
			Fx.burst("dust", Vector2(p.center().x, where.y + p.box.y))
			return

## `TileCollision.has_flag(SOLID)` ORs the RAW flags of every overlapped tile,
## and a switch block carries SOLID whatever its group is doing — so it answers
## "is there a switch block here", not "is it solid right now". That is correct
## for every other level in the game and wrong for every question this one asks.
## `TileWorld.is_solid()` resolves the group, so the test is written out.
func _rect_hits_solid(r: Rect2) -> bool:
	var cols := TileCollision.tile_range(r.position.x, r.position.x + r.size.x)
	var rows := TileCollision.tile_range(r.position.y, r.position.y + r.size.y)
	for ty in range(rows.x, rows.y + 1):
		for tx in range(cols.x, cols.y + 1):
			if world.is_solid(tx, ty):
				return true
	return false

# ---------------------------------------------------------------- the fight
func think(delta: float) -> void:
	# The plinths and shelves are one-way and solid blocks inside and outside the
	# Heart's span, and its slam clears 40 px against their 32 — so without this
	# it could land ON a refuge, which is both absurd and the end of the dodge
	# window that slab exists to be. `drop_through` is Actor's own switch for
	# "one-ways are not floors this tick"; the Heart is never anywhere but the
	# arena floor.
	drop_through = true
	apply_gravity(delta)
	t = maxf(0.0, t - delta)

	# The safe beat pre-empts everything, including the state machine: a boss
	# that kept slamming through its own telegraph would have made the telegraph
	# a lie.
	if _pending >= 0:
		vel.x = move_toward(vel.x, 0.0, 900.0 * delta)
		set_anim("windup")
		_tick_reforge(delta)
		_hold_the_arena(delta)
		return

	var p := player()
	var walk: float = float(phase_cfg.get("walk_speed", 46.0))

	match st:
		St.IDLE:
			# The shed's windup, and the fight's opening beat. The pose is the
			# flared windup rather than the idle, because this is a telegraph:
			# the Heart brightens before the vault gives way.
			vel.x = move_toward(vel.x, 0.0, 400.0 * delta)
			set_anim("windup" if _volley_armed else "idle")
			if t <= 0.0:
				if int(phase_cfg.get("shed", 0)) > 0 and _volley_armed:
					_shed_volley()
				_volley_armed = false
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 2.2))
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
				t = float(cfg.get("windup_time", 0.45))
			_maybe_glass(delta)
			_maybe_shed(delta)
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
				_slam()
				st = St.LAND
				t = float(cfg.get("land_time", 0.5))
		St.LAND:
			vel.x = move_toward(vel.x, 0.0, 700.0 * delta)
			set_anim("land")
			if t <= 0.0:
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 2.2))
		St.SPRAY:
			vel.x = 0.0
			set_anim("windup")
			if t <= 0.0:
				_glass()
				st = St.WALK
				t = float(phase_cfg.get("slam_interval", 2.2))
	_hold_the_arena(delta)

## Check 4 of the boss gate is "the boss stays inside arena_min/arena_max", and
## it is measured at the END of the physics frame — after `step_motion()`, which
## runs after `think()`. Clamping the position and then moving is what put the
## Maw two pixels outside its own arena on two frames and the Warden outside its
## own on 4,502, so the clamp bites on the VELOCITY, before the move that would
## use it, and the position clamp stays as the backstop. Same lines, same
## reason, as tide_maw.gd and boss_grove.gd.
func _hold_the_arena(delta: float) -> void:
	pos.x = clampf(pos.x, arena_min, arena_max)
	if delta <= 0.0:
		return
	var next_x := pos.x + vel.x * delta
	if next_x < arena_min:
		vel.x = (arena_min - pos.x) / delta
	elif next_x > arena_max:
		vel.x = (arena_max - pos.x) / delta

func _maybe_glass(delta: float) -> void:
	if int(phase_cfg.get("glass", 0)) <= 0:
		return
	glass_t = maxf(0.0, glass_t - delta)
	if glass_t <= 0.0:
		glass_t = float(phase_cfg.get("glass_interval", 2.6))
		st = St.SPRAY
		t = 0.4

## THE GLASS. A volley swept along the STEP BAND in both directions: level, fast,
## and at exactly the height of a body standing on one of the bays' one-way
## ledges.
##
## It exists because the arena has three tiers and the fight owes each of them an
## answer. The bore runs the floor and cannot climb; the shed falls out of the
## vault onto the shelves; and between them sits the step at rows 23-24, which no
## configuration can take away, which the Heart's own body can never reach
## (`arena_cols` keeps it out of every bay's columns) and from which the blade
## still reaches the Heart. Without the glass a step is safe from everything in
## the arena and still a place to fight from, which is a stalemate — and the one
## failure ADR 005's check 3 structurally cannot see, because check 3 only asks
## whether each attack misses SOMEWHERE.
##
## The numbers are measured and tools/worlds/nest_5.py's `_self_checks` re-checks
## them against the geometry every build: a body on a step spans y 378..400 and a
## body on the floor spans y 410..432, so the volley is thrown `glass_height`
## above the Heart's centre with `glass_spread` of stack, which puts every shard
## inside the first band and none of them inside the second. Standing on the
## floor IS the dodge, which is what makes the fight a conversation between two
## heights rather than a race.
func _glass() -> void:
	var n := int(phase_cfg.get("glass", 3))
	var pj: Dictionary = (cfg.get("projectile", {}) as Dictionary).duplicate()
	pj["speed"] = float(phase_cfg.get("glass_speed", 150.0))
	pj["gravity"] = 0.0
	pj["life"] = 2.2
	pj["frame"] = 2
	var h := float(cfg.get("glass_height", 20.0))
	var spread := float(cfg.get("glass_spread", 8.0))
	for i in n:
		var f := 0.0 if n <= 1 else float(i) / float(n - 1)
		var y := center().y - h - spread * f
		for dir in [Vector2.LEFT, Vector2.RIGHT]:
			var shot := Projectile.new()
			shot.setup(pj, Vector2(center().x, y), dir, world, level)
			level.entities.add_child(shot)
	AudioManager.play("spit")

## THE VAULT SHEDS. Shards fall out of the arena's top interior row, spread
## across it, and the two combs are the only cover: a shard born at that row
## over a comb is born inside solid obsidian and `Projectile` kills it on the
## frame it is born. The brood shaft in deeps_5's roof taught this trick and
## THE BROOD QUEEN's spore fall is where it was measured.
##
## It runs in EVERY phase, and that is the reason it exists: without something
## that comes down, a one-way refuge at row 25 is safe from the bore, safe from
## the sparks, out of the Heart's own reach and therefore safe from everything,
## which is a corner to camp in and the one thing the gate's check 3 cannot see.
## Is it time for the vault to shed? Called from WALK, and it answers by putting
## the Heart into IDLE for `shed_windup` seconds.
##
## The state matters more than it looks. tests/integration/boss_gate_checks.gd
## names an attack by the STATE TRANSITION its damage sources appeared on, so a
## purely timer-driven attack gets a different tag every time the timer happens
## to land in a different state — and every one of those tags is then "silent"
## on every tile where it did not fire, which is check 3's hardest failure. IDLE
## is otherwise entered only at the start of the fight, so WALK>IDLE is this
## attack and nothing else. THE BROOD QUEEN's spore fall solves the same problem
## the same way, through SPRAY.
func _maybe_shed(delta: float) -> void:
	if int(phase_cfg.get("shed", 0)) <= 0 or _shed.is_empty():
		return
	shed_t = maxf(0.0, shed_t - delta)
	if shed_t <= 0.0:
		shed_t = float(phase_cfg.get("shed_interval", 3.0))
		st = St.IDLE
		t = float(phase_cfg.get("shed_windup", 0.5))
		_volley_armed = true

## THE VAULT SHEDS. Shards fall out of the arena's vault down the columns
## data/enemies/obsidian_heart.json names, and the comb is the only cover: a
## shard born at that row over the comb is born inside solid obsidian and
## `Projectile` kills it on the frame it is born. deeps_5's brood shaft taught
## the trick and THE BROOD QUEEN's spore fall is where it was measured.
##
## It runs in EVERY phase, and that is the reason it exists: without something
## that comes down, a one-way step is safe from the bore, out of the Heart's own
## reach and still in blade range, which is a stalemate to camp in.
##
## The columns ALTERNATE between volleys rather than firing all twelve at once.
## Six is a shower you can read and run out of; twelve is a wall. Two volleys
## cover every column, which is what the gate's two samples per tile need to see.
func _shed_volley() -> void:
	var cols: Array = _shed.get("cols", [])
	if level == null or cols.is_empty():
		return
	var ts := float(TileData4.TILE_SIZE)
	var row := float(_shed.get("row", 20))
	var pj: Dictionary = (cfg.get("projectile", {}) as Dictionary).duplicate()
	pj["speed"] = float(phase_cfg.get("shed_speed", 140.0))
	pj["gravity"] = float(phase_cfg.get("shed_gravity", 90.0))
	pj["life"] = 2.6
	pj["frame"] = 2
	var want := int(phase_cfg.get("shed", 6))
	var thrown := 0
	for i in cols.size():
		if i % 2 != _volley % 2:
			continue
		if thrown >= want:
			break
		thrown += 1
		var col := float(int(cols[i]))
		var shot := Projectile.new()
		shot.setup(pj, Vector2(col * ts + ts * 0.5, row * ts + ts * 0.5),
			Vector2.DOWN, world, level)
		level.entities.add_child(shot)
	_volley += 1
	AudioManager.play("spit")

## The bore: the slam throws a wave along the floor in both directions, four
## pixels off it. It is the fight's main attack and it is dodged by being on a
## refuge — 32 px up, and behind that refuge's own solid face, which is what
## stops the wave rather than a rule saying it stops.
func _slam() -> void:
	AudioManager.play("boss_land")
	Fx.shake("boss_slam")
	Fx.burst("dust", Vector2(center().x, pos.y + box.y))
	var pj: Dictionary = (cfg.get("projectile", {}) as Dictionary).duplicate()
	pj["speed"] = float(phase_cfg.get("bore_speed", 132.0))
	pj["gravity"] = 0.0
	pj["life"] = float(phase_cfg.get("bore_life", 1.7))
	pj["frame"] = 1
	for dir in [Vector2.LEFT, Vector2.RIGHT]:
		var shot := Projectile.new()
		shot.setup(pj, Vector2(center().x, pos.y + box.y - 4.0), dir, world, level)
		level.entities.add_child(shot)
	# Reinforcements, up to a garrison size and no further — boss_grove.gd's
	# measured cap, for its measured reason: nothing in the fight ever takes an
	# add away, so an uncapped call-for-help mints them faster than the blade can
	# spend them and the fight stops being decided by play.
	var live := live_adds()
	var cap := int(cfg.get("max_adds", 2))
	var add_type := String(cfg.get("add_type", "enemy_charger"))
	for i in int(phase_cfg.get("spawn_adds", 0)):
		if level == null or live >= cap:
			continue
		live += 1
		var origin := Screen.origin(home_screen)
		level.spawn_entity({
			"type": add_type,
			"px": origin.x + 48.0 + float(i) * (Screen.W - 112.0),
			"py": pos.y - 8.0,
		})

## How many hostile bodies are standing in the arena. Counted from the live
## scene rather than tallied on spawn, so one that walks into the blade comes
## off the books — and counted BY SCREEN, because every other enemy in the level
## is in the same `enemies` group and counting the ones out in the flues would
## mean the garrison was full before the fight started.
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

## How many times the nest has been written. The suite reads this rather than
## inferring reconfiguration from a tile, because "the mechanic ran" and "the
## tile changed" are two claims and this file owes both.
func flips() -> int:
	return _flips

func die(from: Vector2 = Vector2.ZERO) -> void:
	if defeated:
		return
	defeated = true
	# A pending reforge dies with it. Everything else about this boss leaves the
	# world as it stands — the configuration IS the mechanic — but a telegraph
	# that outlived the thing telegraphing it would turn the arena over under a
	# player who has already won.
	_pending = -1
	_reforge = 0.0
	reforging = false
	super.die(from)
	if level != null and level.has_method("on_boss_defeated"):
		level.on_boss_defeated(self)
