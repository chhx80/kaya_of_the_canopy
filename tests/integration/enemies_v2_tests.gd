extends Node
## In-game suite for the three enemies added in M2-M5: the charger, the
## ceiling-dropper and the patrolling flyer.
##
## Everything here is asserted on the **outcome a player would see**, never on
## the state machine that produced it. Six shipped defects were all missed the
## same way — the mechanism was checked and the result was not — so:
##
##   * the charger's wind-up is proved by measuring how many frames it stood
##     still and whether the pose on screen changed, not by reading `st`
##   * the flyer ignoring one-way platforms is proved by finding the frame
##     where a *non*-drop-through actor in the same place would have landed,
##     and showing the flyer went straight through it
##   * "killable by the blade" and "damages on contact" are proved by throwing
##     the real blade and by standing in the way, for all three
##
## Runs against `levels/test_arena.json`, which the arena tests already use:
## floor along row 12, walls at columns 0 and 24, a one-way platform at row 8
## columns 14-16, a breakable crate at (18, 11).
##
## Standalone (this file owns its whole harness):
##   $GODOT --headless --path . res://tests/integration/enemies_v2_runner.tscn
##
## Not wired into tests/integration/integration_tests.gd: this branch does not
## own that file. To wire it in, add to `run_all()`'s list:
##     "t_enemies_v2",
## and the method:
##     func t_enemies_v2() -> void:
##         var s: Node = (load("res://tests/integration/enemies_v2_tests.gd") as GDScript).new()
##         s.standalone = false
##         add_child(s)
##         await s.run_all()
##         passes += s.passes
##         failures.append_array(s.failures)
##         s.queue_free()
## `standalone = false` is what stops it printing its own report; the host's
## counters are the ones that matter then. See REPORT.md.

const ARENA := "test_arena"
const TS := 16.0
const FPS := 60.0

## Geometry of test_arena, named so a level edit breaks a name and not a number.
const FLOOR_ROW := 12
const ONEWAY_ROW := 8
const ONEWAY_COL := 15
const CRATE := Vector2i(18, 11)

var failures: PackedStringArray = PackedStringArray()
var passes := 0
var _current := ""

## Cleared by a host that folds this suite into its own run. It does not start
## itself: tests/integration/enemies_v2_runner.gd awaits `run_all()` and exits
## on what it returns, which is also what lets a host await it exactly once.
var standalone := true

# ---------------------------------------------------------------- harness
func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame

func check(cond: bool, msg: String) -> void:
	if cond:
		passes += 1
	else:
		failures.append("%s :: %s" % [_current, msg])

func check_eq(a: Variant, b: Variant, msg: String) -> void:
	check(a == b, "%s (got %s, want %s)" % [msg, str(a), str(b)])

func at_least(a: float, b: float, msg: String) -> void:
	check(a >= b, "%s (got %f, want >= %f)" % [msg, a, b])

func at_most(a: float, b: float, msg: String) -> void:
	check(a <= b, "%s (got %f, want <= %f)" % [msg, a, b])

func level() -> Node:
	return Game.current_level

func player() -> Player:
	var l := level()
	return l.player if l != null and l.get("player") != null else null

func enemies() -> Array:
	return get_tree().get_nodes_in_group(&"enemies").filter(
		func(e: Node) -> bool: return is_instance_valid(e))

func blades() -> Array:
	var out: Array = []
	for n in level().entities.get_children():
		if n is Blade:
			out.append(n)
	return out

## Boots the arena and clears the walker it ships with, so the only enemies in
## the world are the ones a test asked for.
func enter_arena() -> void:
	Game.reset_run()
	Game.goto_level(ARENA)
	await frames(4)
	for n in enemies():
		var e := n as Enemy
		e.remove_from_group(&"enemies")
		e.queue_free()
	await frames(2)

## One entity dictionary in the shape LevelLoader.from_dict() emits: the tile
## coordinates a level author writes, plus the pixel pair src/world/level.gd
## reads back out.
func entity_def(type: String, tx: int, ty: int, props: Dictionary = {}) -> Dictionary:
	var e: Dictionary = props.duplicate()
	e["type"] = type
	e["x"] = tx
	e["y"] = ty
	e["px"] = float(tx) * TS
	e["py"] = float(ty) * TS
	return e

## Every enemy in this file is placed the way a level places one: an authored
## entity dictionary through `Level.spawn_entity()`, the same call
## `Level._spawn_entities()` makes for each line of `levels/*.json`.
##
## It used to call `level()._spawn_enemy()` directly, which reached past the
## `enemy_*` registry — the exact thing that was missing. Every test below
## passed while no level on disk could contain the enemy it was testing. Going
## through the front door is what makes them mean anything.
func spawn(id: String, tx: int, ty: int, props: Dictionary = {}) -> Enemy:
	var n: Node = level().spawn_entity(entity_def("enemy_" + id, tx, ty, props))
	# Asserted here rather than left to each caller: several tests below bail
	# out quietly on a null enemy, so an unregistered id used to cost nothing
	# more than a shorter run and a green report.
	check(n is Enemy, "the level places an enemy_%s at tile (%d, %d)" % [id, tx, ty])
	await frames(1)
	return n as Enemy

func place(tx: float, ty: float, settle: int = 20) -> void:
	var p := player()
	p.pos = Vector2(tx * TS, ty * TS)
	p.vel = Vector2.ZERO
	p.dead = false
	p.invuln = 0.0
	p.hurt_t = 0.0
	level().cam.snap_to_target()
	await frames(settle)
	if not is_instance_valid(p):
		return
	p.invuln = 0.0
	p.hurt_t = 0.0

## Parks the player somewhere harmless and immortal, so a test that is about
## the enemy is not also a test of the player's hurt state.
func park(tx: float, ty: float) -> void:
	await place(tx, ty)
	player().invuln = 9999.0

## Throws the blade and waits for it to come home. Returns false if it never did.
func throw_at(dir: int) -> bool:
	var p := player()
	p.facing = dir
	if not p.weapon.try_attack(p):
		return false
	for i in 240:
		await get_tree().physics_frame
		if blades().is_empty():
			return true
	return false

## The sprite cell currently on screen, as a frame index. This is what the
## player actually sees, which is the only honest way to assert "it changed
## pose" rather than "it changed enum".
func shown_frame(e: Enemy) -> int:
	return int(e.sprite.region_rect.position.x / float(e.sprite.region_rect.size.x))

# ---------------------------------------------------------------- tests
func run_all() -> int:
	var tests := [
		"t_a_level_definition_can_place_all_three",
		"t_an_enemy_the_registry_does_not_know_spawns_nothing",
		"t_charger_patrols_and_turns_at_a_wall",
		"t_charger_stands_still_in_a_new_pose_before_every_charge",
		"t_charger_charges_faster_than_kaya_can_run",
		"t_charger_overshoots_and_leaves_a_window",
		"t_a_wall_between_you_and_the_charger_breaks_its_line",
		"t_the_blade_kills_a_charger_and_scores_it",
		"t_a_charger_damages_the_player_on_contact",
		"t_dropper_hangs_still_until_you_walk_under_it",
		"t_dropper_shivers_in_place_before_it_lets_go",
		"t_dropper_lands_on_the_floor_and_walks",
		"t_dropper_set_to_burst_dies_where_it_lands",
		"t_the_blade_kills_a_dropper_on_its_ceiling",
		"t_a_falling_dropper_damages_the_player_on_contact",
		"t_flyer_never_falls_and_holds_its_line",
		"t_flyer_turns_at_the_end_of_its_leg",
		"t_flyer_flies_through_a_one_way_platform_that_would_catch_anyone_else",
		"t_the_blade_kills_a_flyer_and_scores_it",
		"t_a_flyer_damages_the_player_on_contact",
		"t_the_new_enemies_are_tuned_against_kaya_not_against_nothing",
		"t_a_screen_flip_freezes_them_and_puts_them_back_as_they_started",
		"t_the_new_sheets_stay_on_the_material_ramps",
	]
	for t in tests:
		_current = t
		await enter_arena()
		await call(t)
	if standalone:
		_report()
	return 0 if failures.is_empty() else 1

# ---------------------------------------------------------------- the registry
## The registry itself, read from src/world/level.gd rather than copied here,
## so this file cannot drift into agreeing with a list that no longer exists.
func registered_enemy_ids() -> Array:
	var script: GDScript = load("res://src/world/level.gd")
	var consts: Dictionary = script.get_script_constant_map()
	var ids: Array = []
	if consts.has("ENEMY_IDS"):
		ids = consts["ENEMY_IDS"]
	return ids

## What was actually broken, tested the way a level author meets it: take the
## arena's own JSON off disk, add the three enemies to its entity list, put the
## whole thing through the real LevelLoader, and hand every parsed entity to
## the level's own factory — the two steps Level._spawn_entities() performs on
## boot, with nothing simulated in between.
##
## Before src/world/level.gd knew these three ids, every one of these returned
## null and a level containing one was a level with a hole in it.
func t_a_level_definition_can_place_all_three() -> void:
	await park(3, 10)
	var raw: Variant = JSON.parse_string(
		FileAccess.get_file_as_string("res://levels/%s.json" % ARENA))
	check(typeof(raw) == TYPE_DICTIONARY, "the arena's level file parses")
	if typeof(raw) != TYPE_DICTIONARY:
		return
	var d: Dictionary = (raw as Dictionary).duplicate(true)
	var authored: Array = (d.get("entities", []) as Array).duplicate()
	authored.append({"type": "enemy_charger", "x": 5, "y": 11})
	authored.append({"type": "enemy_dropper", "x": 10, "y": 4})
	authored.append({"type": "enemy_flyer", "x": 19, "y": 5, "axis": "y", "range": 24.0})
	d["entities"] = authored

	var fixture: LevelLoader.LevelDef = LevelLoader.from_dict(d)
	check(fixture.ok(), "a level that places all three is a valid level (%s)"
		% str(fixture.errors))
	if not fixture.ok():
		return

	# Positions are read before a single frame runs: add_child() runs the
	# enemy's _ready() synchronously, so this is where the level put it, not
	# where it walked to.
	var wanted := ["enemy_charger", "enemy_dropper", "enemy_flyer"]
	var made: Dictionary = {}
	var at: Dictionary = {}
	var authored_enemies := 0
	var built := 0
	for e: Dictionary in fixture.entities:
		var type := String(e["type"])
		if not type.begins_with("enemy_"):
			continue
		# The arena ships a walker of its own; it goes through the same door,
		# so it is counted too. Nothing in the file may come back empty.
		authored_enemies += 1
		var n: Node = level().spawn_entity(e)
		check(n is Enemy, "the level factory built a '%s'" % type)
		if n is Enemy:
			built += 1
			if wanted.has(type):
				made[type] = n
				at[type] = (n as Enemy).pos
	check_eq(built, authored_enemies,
		"every enemy the definition authored reached the world")
	check_eq(made.size(), 3, "including all three of the new ones")
	if made.size() != 3:
		return

	for type: String in made.keys():
		var en: Enemy = made[type]
		check_eq("enemy_" + en.enemy_id, type, "%s loaded its own data file" % type)
		check(en.is_in_group(&"enemies"), "%s is a live enemy" % type)
		check(en.get_parent() == level().entities, "%s hangs off the level" % type)
		check(en.world == level().world, "%s collides against this level" % type)
		check(en.max_health >= 1, "%s took its health from data/enemies/" % type)

	var boar: Enemy = made["enemy_charger"]
	var tick: Enemy = made["enemy_dropper"]
	var wasp: Enemy = made["enemy_flyer"]
	check_eq((at["enemy_charger"] as Vector2).x + boar.box.x * 0.5, 5.0 * TS + 8.0,
		"the boar stands in the column it was authored in")
	check_eq(int((at["enemy_charger"] as Vector2).y + boar.box.y), FLOOR_ROW * 16,
		"and on the floor of its tile")
	check_eq(int((at["enemy_dropper"] as Vector2).y), 4 * 16,
		"the tick hangs at the top of the tile above the one it was authored in")
	check_eq((at["enemy_flyer"] as Vector2).x + wasp.box.x * 0.5, 19.0 * TS + 8.0,
		"the wasp holds the column it was authored in")

	# Authored per-instance properties survive the trip through the loader:
	# the wasp was given a vertical leg, so it has to leave its own row.
	var y0 := wasp.pos.y
	var spread := 0.0
	await frames(90)
	for type: String in made.keys():
		check(is_instance_valid(made[type]),
			"%s is still alive after a second and a half of real play" % type)
	if is_instance_valid(wasp):
		spread = absf(wasp.pos.y - y0)
	check(spread > 4.0, "the wasp flies the axis the entity asked for")

## Requirement four. A level that names an enemy the registry has never heard
## of must not leave a silent hole where a threat was authored.
##
## The half that can be asserted from inside the process is asserted: nothing
## is built, nothing half-exists, the level plays on. Godot's warning stream is
## not readable from GDScript, so the warning *text* is verified by reading the
## headless log — the exact grep is in REPORT.md, and it is the only claim in
## this file that a machine here does not make.
func t_an_enemy_the_registry_does_not_know_spawns_nothing() -> void:
	await park(3, 10)
	var children: int = level().entities.get_child_count()
	var live: int = enemies().size()
	# "enemy_" alone, a typo, a real file in src/enemies/ that is not an enemy,
	# and an id nobody ever wrote.
	for bogus: String in ["enemy_", "enemy_walkr", "enemy_enemy_base",
			"enemy_projectile", "enemy_ghost"]:
		var n: Node = level().spawn_entity(entity_def(bogus, 8, 11))
		check(n == null, "'%s' spawns nothing at all" % bogus)
	await frames(10)
	check_eq(level().entities.get_child_count(), children,
		"and leaves no half-built node behind")
	check_eq(enemies().size(), live, "and nothing joins the enemies group")
	check(is_instance_valid(level()) and player() != null and not player().dead,
		"the level plays on regardless")

	# The other side of the same contract: every id the registry does claim can
	# be resolved, or the warning above is the one a real level would hit.
	var ids := registered_enemy_ids()
	check(ids.size() >= 7, "the registry lists every enemy (%s)" % str(ids))
	for id: String in ids:
		check(ResourceLoader.exists("res://src/enemies/%s.gd" % id),
			"registered id '%s' resolves to a script" % id)
		check(FileAccess.file_exists("res://data/enemies/%s.json" % id),
			"registered id '%s' has a data file" % id)
	for id: String in ["walker", "jumper", "shooter", "swimmer",
			"charger", "dropper", "flyer"]:
		check(ids.has(id), "'%s' is still placeable" % id)

# ---------------------------------------------------------------- charger
func t_charger_patrols_and_turns_at_a_wall() -> void:
	# The player stands on the one-way, well outside the charger's sight band,
	# so this is a patrol test and nothing else.
	await park(14, 6)
	var c := await spawn("charger", 2, 11, {"facing": "left"})
	check(c != null, "the charger spawns")
	if c == null:
		return
	check_eq(int(c.pos.y + c.box.y), FLOOR_ROW * 16, "it stands on the floor")
	var x0 := c.pos.x
	await frames(60)
	check(c.pos.x < x0, "it walks the way it is facing")
	await frames(90)
	check_eq(c.facing, 1, "and turns around at the wall")
	var x1 := c.pos.x
	await frames(60)
	check(c.pos.x > x1, "then walks back the other way")
	at_most(absf(c.vel.x), float(c.cfg["speed"]) + 1.0,
		"a patrolling charger never exceeds its patrol speed")

## The fairness contract, measured the way a player experiences it: before the
## charge there is a run of frames where the boar does not move at all AND is
## drawn in a pose it never uses while patrolling.
func t_charger_stands_still_in_a_new_pose_before_every_charge() -> void:
	await park(14, 6)
	var c := await spawn("charger", 9, 11)
	if c == null:
		return
	c.contact_damage = 0

	# 40 frames of ordinary patrol, to learn what "patrolling" looks like.
	var patrol_poses: Dictionary = {}
	for i in 40:
		await get_tree().physics_frame
		patrol_poses[shown_frame(c)] = true
	check(patrol_poses.size() > 0, "the patrol has poses to compare against")

	# Settle 0: place() normally waits 20 frames, which is most of the
	# telegraph — the measurement has to start on the frame the player lands
	# in the line, not a third of a second later.
	await place(16, 10, 0)
	player().invuln = 9999.0

	var xs: PackedFloat32Array = PackedFloat32Array()
	var vs: PackedFloat32Array = PackedFloat32Array()
	var poses: PackedInt32Array = PackedInt32Array()
	var charge_speed := float(c.cfg["charge_speed"])
	var patrol_speed := float(c.cfg["speed"])
	var charge_at := -1
	for i in 180:
		await get_tree().physics_frame
		if not is_instance_valid(c):
			break
		xs.append(c.pos.x)
		vs.append(c.vel.x)
		poses.append(shown_frame(c))
		if charge_at < 0 and absf(c.vel.x) > patrol_speed * 2.0:
			charge_at = i
	check(charge_at > 0, "it charges once the player is in its line")
	if charge_at <= 0:
		return

	# Walk backwards from the charge through every frame it was stationary.
	var still := 0
	var i := charge_at - 1
	var pose_set: Dictionary = {}
	var x_lo := 1e9
	var x_hi := -1e9
	while i >= 0 and absf(vs[i]) < 1.0:
		still += 1
		pose_set[poses[i]] = true
		x_lo = minf(x_lo, xs[i])
		x_hi = maxf(x_hi, xs[i])
		i -= 1
	at_least(float(still) / FPS, float(c.cfg["wind_up"]) * 0.9,
		"the wind-up holds it still for the advertised time")
	at_most(x_hi - x_lo, 1.0, "and it really is still, not creeping forward")
	check(pose_set.size() > 0, "the wind-up draws something")
	var shared := 0
	for f: int in pose_set.keys():
		if patrol_poses.has(f):
			shared += 1
	check_eq(shared, 0, "the wind-up pose is one the patrol never uses")
	check(charge_speed > patrol_speed * 2.0, "and what follows is a charge")

func t_charger_charges_faster_than_kaya_can_run() -> void:
	await park(14, 6)
	var c := await spawn("charger", 9, 11)
	if c == null:
		return
	c.contact_damage = 0
	await place(16, 10)
	player().invuln = 9999.0
	var top := 0.0
	for i in 180:
		await get_tree().physics_frame
		if not is_instance_valid(c):
			break
		top = maxf(top, absf(c.vel.x))
	var human := FormBase.load_form("human")
	at_least(top, float(c.cfg["charge_speed"]) * 0.9, "the charge reaches its speed")
	check(top > human.max_run, "and outruns Kaya, which is why the tell exists")

## It cannot stop where you were standing. That overshoot is the counter-attack
## window, so both halves are asserted: it goes past you, and it spends a
## measurable stretch below its own patrol speed afterwards.
func t_charger_overshoots_and_leaves_a_window() -> void:
	await park(14, 6)
	var c := await spawn("charger", 6, 11)
	if c == null:
		return
	c.contact_damage = 0
	await place(12, 10)
	player().invuln = 9999.0
	var target_x := player().center().x
	var patrol_speed := float(c.cfg["speed"])

	var charged := false
	var slow_run := 0
	var best_slow := 0
	var past := false
	for i in 300:
		await get_tree().physics_frame
		if not is_instance_valid(c):
			break
		if absf(c.vel.x) > patrol_speed * 2.0:
			charged = true
			slow_run = 0
		elif charged and absf(c.vel.x) < patrol_speed - 1.0:
			# Below walking pace: still skidding or dazed, and hittable. Once
			# it resumes patrol it sits at exactly `speed`, which ends the run.
			slow_run += 1
			best_slow = maxi(best_slow, slow_run)
		else:
			slow_run = 0
		if charged and c.center().x > target_x + TS:
			past = true
	check(charged, "it charges")
	check(past, "and slides a full tile past where the player stood")
	at_least(float(best_slow) / FPS, 0.35,
		"then spends a punishable stretch below walking pace")

func t_a_wall_between_you_and_the_charger_breaks_its_line() -> void:
	await place(14, 10)
	player().invuln = 9999.0
	var c := await spawn("charger", 22, 11, {"facing": "left"})
	if c == null:
		return
	c.contact_damage = 0
	var w: TileWorld = level().world
	check(w.is_solid(CRATE.x, CRATE.y), "the crate between them starts solid")
	var patrol_speed := float(c.cfg["speed"])
	# Short enough that the boar is still walking toward the crate, not past
	# the turn it makes when it reaches it.
	var top := 0.0
	for i in 90:
		await get_tree().physics_frame
		top = maxf(top, absf(c.vel.x))
	at_most(top, patrol_speed + 1.0, "a charger cannot see you through a wall")

	# Same positions, one tile of difference.
	w.break_tile(CRATE.x, CRATE.y)
	level().on_tile_broken(CRATE)
	check(not w.is_solid(CRATE.x, CRATE.y), "the crate is gone")
	var charged := false
	for i in 180:
		await get_tree().physics_frame
		if not is_instance_valid(c):
			break
		if absf(c.vel.x) > patrol_speed * 2.0:
			charged = true
			break
	check(charged, "with the line open it charges")

func t_the_blade_kills_a_charger_and_scores_it() -> void:
	await place(6, 10)
	var c := await spawn("charger", 11, 11, {"facing": "left"})
	if c == null:
		return
	c.contact_damage = 0
	c.speed = 0.0
	c.cfg["drops"] = {}          # a random gem would muddy the score check
	c.cfg["sight_range"] = 0.0   # hold it still; this test is about the blade
	var value := c.score_value
	var hp := c.max_health
	check(hp > 1, "the boar takes more than one hit")
	var score_before := Game.score
	for throw in hp:
		if not is_instance_valid(c):
			break
		player().pos.x = 6 * TS
		player().vel = Vector2.ZERO
		check(await throw_at(1), "throw %d comes back" % throw)
		await frames(20)
	check(not is_instance_valid(c) or c.health <= 0,
		"%d blade hits kill a charger" % hp)
	check_eq(Game.score, score_before + value, "and score it at its value")

func t_a_charger_damages_the_player_on_contact() -> void:
	await place(9, 10)
	var c := await spawn("charger", 9, 11, {"facing": "left"})
	if c == null:
		return
	var p := player()
	c.speed = 0.0
	c.cfg["sight_range"] = 0.0
	c.pos = Vector2(p.pos.x, p.pos.y + p.box.y - c.box.y)
	c.vel = Vector2.ZERO
	# Spawning on top of the player already landed one hit; clear the
	# invulnerability it granted so the next one is the one being measured.
	p.invuln = 0.0
	var before := Game.health
	await frames(10)
	check(Game.health < before, "walking into a charger hurts")

# ---------------------------------------------------------------- dropper
func t_dropper_hangs_still_until_you_walk_under_it() -> void:
	await park(3, 10)
	var d := await spawn("dropper", 10, 4)
	check(d != null, "the dropper spawns")
	if d == null:
		return
	check_eq(int(d.pos.y), 4 * 16,
		"it hangs at the top of its tile, against the ceiling above it")
	var at := d.pos
	await frames(120)
	check_eq(d.pos, at, "two seconds with the player elsewhere and it has not moved")
	check(not d.on_floor, "and it is not resting on anything")

func t_dropper_shivers_in_place_before_it_lets_go() -> void:
	await park(3, 10)
	var d := await spawn("dropper", 10, 4)
	if d == null:
		return
	d.contact_damage = 0
	var cling_pose := shown_frame(d)
	var hang_y := d.pos.y

	# Settle 0, for the same reason as the charger's wind-up: place()'s usual
	# 20-frame wait would swallow most of the tell.
	await place(10, 10, 0)
	player().invuln = 9999.0

	var still := 0
	var poses: Dictionary = {}
	var dropped := false
	for i in 180:
		await get_tree().physics_frame
		if not is_instance_valid(d):
			break
		if d.pos.y > hang_y + 0.5:
			dropped = true
			break
		still += 1
		poses[shown_frame(d)] = true
	check(dropped, "it does eventually let go")
	at_least(float(still) / FPS, float(d.cfg["wind_up"]) * 0.9,
		"but only after shivering in place for the advertised tell")
	check(not poses.has(cling_pose), "and the shiver never draws the cling pose")

func t_dropper_lands_on_the_floor_and_walks() -> void:
	await park(3, 10)
	var d := await spawn("dropper", 10, 4)
	if d == null:
		return
	d.contact_damage = 0
	await place(10, 10)
	player().invuln = 9999.0
	# Get the player out from under it so the landing is not a collision test.
	await frames(40)
	await place(3, 10)
	player().invuln = 9999.0
	for i in 180:
		await get_tree().physics_frame
		if not is_instance_valid(d) or d.on_floor:
			break
	check(is_instance_valid(d), "a walking dropper survives the landing")
	if not is_instance_valid(d):
		return
	check(d.on_floor, "it reaches the floor")
	check_eq(int(d.pos.y + d.box.y), FLOOR_ROW * 16, "and stands on it")
	var x0 := d.pos.x
	await frames(60)
	check(absf(d.pos.x - x0) > 4.0, "then crawls off like a beetle")

func t_dropper_set_to_burst_dies_where_it_lands() -> void:
	await park(3, 10)
	var d := await spawn("dropper", 10, 4)
	if d == null:
		return
	d.contact_damage = 0
	d.cfg["land_action"] = "die"
	d.cfg["drops"] = {}
	var value := d.score_value
	var score_before := Game.score
	await place(10, 10)
	player().invuln = 9999.0
	await frames(40)
	await place(3, 10)
	player().invuln = 9999.0
	var gone := false
	for i in 180:
		await get_tree().physics_frame
		if not is_instance_valid(d) or d.health <= 0:
			gone = true
			break
	check(gone, "a bursting dropper does not survive the impact")
	check_eq(Game.score, score_before + value, "and scores like any other kill")

func t_the_blade_kills_a_dropper_on_its_ceiling() -> void:
	await place(6, 10)
	var d := await spawn("dropper", 11, 11)
	if d == null:
		return
	d.contact_damage = 0
	d.cfg["drops"] = {}
	check_eq(d.max_health, 1, "one hit is meant to do it")
	check(await throw_at(1), "the blade comes back")
	await frames(20)
	check(not is_instance_valid(d) or d.health <= 0,
		"the blade kills a clinging dropper")

func t_a_falling_dropper_damages_the_player_on_contact() -> void:
	await park(3, 10)
	var d := await spawn("dropper", 10, 9)
	if d == null:
		return
	await place(10, 10)
	var p := player()
	p.invuln = 0.0
	var before := Game.health
	var hurt := false
	for i in 240:
		await get_tree().physics_frame
		if Game.health < before:
			hurt = true
			break
	check(hurt, "a dropper that lands on you hurts")

# ---------------------------------------------------------------- flyer
func t_flyer_never_falls_and_holds_its_line() -> void:
	await park(3, 10)
	var f := await spawn("flyer", 6, 5)
	check(f != null, "the flyer spawns")
	if f == null:
		return
	f.contact_damage = 0
	var y0 := f.pos.y
	var amp := float(f.cfg["bob_amplitude"])
	var worst := 0.0
	var grounded := false
	var x0 := f.pos.x
	var moved := 0.0
	for i in 240:
		await get_tree().physics_frame
		worst = maxf(worst, absf(f.pos.y - y0))
		moved = maxf(moved, absf(f.pos.x - x0))
		if f.on_floor:
			grounded = true
	check(not grounded, "four seconds in the air and it never lands")
	at_most(worst, amp + 2.0, "it holds its altitude inside the authored bob")
	at_least(moved, 16.0, "and it is patrolling, not hovering")

func t_flyer_turns_at_the_end_of_its_leg() -> void:
	await park(3, 10)
	var f := await spawn("flyer", 10, 5, {"range": 32.0})
	if f == null:
		return
	f.contact_damage = 0
	var x0 := f.pos.x
	var lo := x0
	var hi := x0
	var dirs: Dictionary = {}
	for i in 300:
		await get_tree().physics_frame
		lo = minf(lo, f.pos.x)
		hi = maxf(hi, f.pos.x)
		if absf(f.vel.x) > 1.0:
			dirs[signi(int(f.vel.x))] = true
	check_eq(dirs.size(), 2, "it flies both ways, so it turned")
	at_most(hi - lo, 32.0 * 2.0 + 8.0, "and stays inside the leg it was given")
	at_least(hi - lo, 32.0, "having actually flown the leg")

## The one that matters. A one-way platform catches anything whose feet cross
## its top edge from above — so the test finds the exact frame where the
## flyer's box crossed row 8's top edge, confirms a non-drop-through actor in
## that same place would have been stopped, and asserts the flyer was not.
func t_flyer_flies_through_a_one_way_platform_that_would_catch_anyone_else() -> void:
	await park(3, 10)
	var w: TileWorld = level().world
	check(w.is_oneway(ONEWAY_COL, ONEWAY_ROW), "row 8 really is a one-way")
	var f := await spawn("flyer", ONEWAY_COL, 5,
		{"axis": "y", "range": 56.0, "bob": 0.0})
	if f == null:
		return
	f.contact_damage = 0
	var lip := float(ONEWAY_ROW * 16)
	var crossed := false
	var would_have_landed := false
	var grounded := false
	var lowest := f.pos.y
	var rose_back := false
	var bottom_before := f.pos.y + f.box.y
	for i in 300:
		await get_tree().physics_frame
		var bottom := f.pos.y + f.box.y
		if bottom_before <= lip and bottom > lip:
			crossed = true
			# The exact condition src/world/tile_collision.gd's move_y uses to
			# stop a falling actor on a one-way.
			var probe := Rect2(Vector2(f.pos.x, lip - f.box.y), f.box)
			would_have_landed = TileCollision.is_on_floor(w, probe, false)
		if f.on_floor:
			grounded = true
		if bottom > lowest:
			lowest = bottom
		if crossed and bottom < lip:
			rose_back = true
		bottom_before = bottom
	check(crossed, "the flyer's path takes it down through the platform row")
	check(would_have_landed,
		"and that platform would have caught an actor that respects one-ways")
	check(not grounded, "but the flyer never reports standing on it")
	at_least(lowest, lip + 8.0, "it gets well below the platform")
	check(rose_back, "and climbs back through it on the return leg")

func t_the_blade_kills_a_flyer_and_scores_it() -> void:
	await place(6, 10)
	var f := await spawn("flyer", 11, 10)
	if f == null:
		return
	f.contact_damage = 0
	f.speed = 0.0
	f.cfg["bob_amplitude"] = 0.0
	f.cfg["drops"] = {}
	var value := f.score_value
	var hp := f.max_health
	var score_before := Game.score
	for throw in hp:
		if not is_instance_valid(f):
			break
		player().pos.x = 6 * TS
		player().vel = Vector2.ZERO
		check(await throw_at(1), "throw %d comes back" % throw)
		await frames(20)
	check(not is_instance_valid(f) or f.health <= 0,
		"%d blade hits kill a flyer" % hp)
	check_eq(Game.score, score_before + value, "and score it at its value")

func t_a_flyer_damages_the_player_on_contact() -> void:
	await place(9, 10)
	var f := await spawn("flyer", 9, 11)
	if f == null:
		return
	var p := player()
	f.speed = 0.0
	f.cfg["bob_amplitude"] = 0.0
	f.pos = Vector2(p.pos.x, p.center().y - f.box.y * 0.5)
	f.vel = Vector2.ZERO
	p.invuln = 0.0
	var before := Game.health
	await frames(10)
	check(Game.health < before, "flying into Kaya hurts")

# ---------------------------------------------------------------- tuning
## Cheap, but these are the numbers that decide whether any of the above is a
## fight or a tax, and they are only meaningful next to the player's own.
func t_the_new_enemies_are_tuned_against_kaya_not_against_nothing() -> void:
	var human := FormBase.load_form("human")
	var c := Enemy.load_config("charger")
	check(float(c["speed"]) < human.max_run, "you can outwalk a patrolling boar")
	check(float(c["charge_speed"]) > human.max_run, "you cannot outrun its charge")
	at_least(float(c["wind_up"]), 0.3, "so the tell has to be long enough to read")
	at_least(float(c["recover"]), 0.5, "and the overshoot has to be punishable")

	var d := Enemy.load_config("dropper")
	at_least(float(d["wind_up"]), 0.3, "the dropper's shiver is long enough to read")
	check(float(d["trigger_depth"]) > 0.0, "and it only reacts to what is below it")

	var f := Enemy.load_config("flyer")
	check(is_zero_approx(float(f["gravity"])), "the flyer has no gravity at all")
	check(float(f["speed"]) < human.max_run, "and you can outpace it on foot")

## Screen-flip scrolling resets every enemy on the screen you walk back into.
## A charger frozen mid-charge or a dropper frozen mid-fall has to come back as
## a patrolling boar and a clinging tick, not resume where it left off — that
## is the one path through these three state machines that nothing else exercises.
func t_a_screen_flip_freezes_them_and_puts_them_back_as_they_started() -> void:
	await park(14, 6)
	var c := await spawn("charger", 9, 11)
	var d := await spawn("dropper", 10, 4)
	var f := await spawn("flyer", 6, 5)
	if c == null or d == null or f == null:
		return
	for e: Enemy in [c, d, f]:
		e.contact_damage = 0
	# Standing under the tick and in front of the boar sets both of them off.
	await place(10, 10, 0)
	player().invuln = 9999.0
	await frames(70)
	check(absf(c.pos.x - c.spawn_pos.x) > 4.0, "the boar has moved off its spawn")
	check(d.pos.y > d.spawn_pos.y, "the tick has let go")

	var elsewhere := Vector2i(9, 9)
	for e: Enemy in [c, d, f]:
		e.set_active_screen(elsewhere)
		check(not e.active, "%s freezes when the camera leaves" % e.enemy_id)
	var frozen := [c.pos, d.pos, f.pos]
	await frames(30)
	for i in 3:
		var e: Enemy = [c, d, f][i]
		check_eq(e.pos, frozen[i] as Vector2, "%s does not move while frozen" % e.enemy_id)

	# Out of every trigger before they wake, or the tick starts its tell on the
	# next frame and the cling pose is never drawn.
	await place(3, 10, 0)
	player().invuln = 9999.0
	for e: Enemy in [c, d, f]:
		e.set_active_screen(e.home_screen)
		check(e.active, "%s wakes up again" % e.enemy_id)
		check_eq(e.pos, e.spawn_pos, "%s is back where it started" % e.enemy_id)
		check_eq(e.health, e.max_health, "%s is back at full health" % e.enemy_id)
	await frames(10)
	check_eq(int(shown_frame(d)), 0, "and the tick is drawn clinging again")
	at_most(absf(d.pos.y - d.spawn_pos.y), 0.01, "not falling")

## `tests/test_art_palette.gd` names the sheets it checks in a const list that
## does not know about these three yet (see REPORT.md). Until it does, the
## ramp-purity rule is enforced here rather than nowhere.
func t_the_new_sheets_stay_on_the_material_ramps() -> void:
	var pal: Variant = JSON.parse_string(
		FileAccess.get_file_as_string("res://assets/palette.json"))
	var ramps: Dictionary = (pal as Dictionary).get("ramps", {})
	var allowed: Dictionary = {}
	for name: String in ramps.keys():
		for col: Variant in (ramps[name] as Array):
			allowed[_hex(col)] = true
	allowed[_hex((pal as Dictionary)["ink"])] = true
	for id: String in ["charger", "dropper", "flyer"]:
		var cfg := Enemy.load_config(id)
		var tex: Texture2D = load(String(cfg.get("sprite", "")))
		check(tex != null, "%s sheet loads" % id)
		if tex == null:
			continue
		var img := tex.get_image()
		var strays: Dictionary = {}
		for y in img.get_height():
			for x in img.get_width():
				var col := img.get_pixel(x, y)
				if col.a <= 0.0:
					continue
				var hex := "%02x%02x%02x" % [int(round(col.r * 255.0)),
					int(round(col.g * 255.0)), int(round(col.b * 255.0))]
				if not allowed.has(hex):
					strays[hex] = true
		check_eq(strays.size(), 0,
			"%s has off-ramp colours: %s" % [id, str(strays.keys())])

func _hex(rgb: Variant) -> String:
	var a: Array = rgb
	return "%02x%02x%02x" % [int(a[0]), int(a[1]), int(a[2])]

# ---------------------------------------------------------------- report
## Prints, and only prints. Quitting is the runner's job — a sub-suite that
## kills the process takes the host's remaining cases with it.
func _report() -> void:
	print("")
	if failures.is_empty():
		print("enemies_v2: %d checks, ALL PASSED" % passes)
	else:
		for f in failures:
			print("  FAIL %s" % f)
		print("enemies_v2: %d passed, %d FAILED" % [passes, failures.size()])
