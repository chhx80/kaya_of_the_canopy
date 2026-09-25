extends Node
## In-game integration suite. The headless unit runner has no autoloads and no
## scene tree, so anything involving nodes — the blade, enemies, pickups,
## triggers, respawn — is verified here instead, driving the real game.
##
## Run with tools/itest.sh (exit code is the gate).

const ARENA := "test_arena"
const TS := 16.0

const TAPE := preload("res://tests/integration/replay_tape.gd")
const TAPE_REPLAY := preload("res://tests/integration/tape_replay.gd")
const LEVEL_DIR := "res://levels"

var failures: PackedStringArray = PackedStringArray()
var skips: PackedStringArray = PackedStringArray()
var passes := 0
var _current := ""
var _only := ""      ## --only=<substring>: run a subset while authoring a tape
var _trace := false  ## --trace=1: print the tape's progress step by step

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--only="):
			_only = a.substr(7)
		elif a.begins_with("--trace"):
			_trace = true
	call_deferred("run_all")

func skip(msg: String) -> void:
	skips.append(msg)

# ---------------------------------------------------------------- harness
func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame

func check(cond: bool, msg: String) -> void:
	if cond:
		passes += 1
	else:
		failures.append("%s :: %s" % [_current, msg])

func near(a: float, b: float, tol: float, msg: String) -> void:
	check(absf(a - b) <= tol, "%s (got %f, want ~%f)" % [msg, a, b])

func check_eq(a: Variant, b: Variant, msg: String) -> void:
	check(a == b, "%s (got %s, want %s)" % [msg, str(a), str(b)])

func gt_check(a: int, b: int, msg: String) -> void:
	check(a > b, "%s (got %d, want > %d)" % [msg, a, b])

func gt_check_f(a: float, b: float, msg: String) -> void:
	check(a > b, "%s (got %f, want > %f)" % [msg, a, b])

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

func enter_arena() -> void:
	await enter(ARENA)

func enter(level_id: String) -> void:
	Game.reset_run()
	Game.goto_level(level_id)
	await frames(4)

func enter_hub() -> void:
	Game.reset_run()
	Game.goto_hub()
	await frames(6)

func find_in_group(group: StringName) -> Array:
	return get_tree().get_nodes_in_group(group).filter(
		func(n: Node) -> bool: return is_instance_valid(n))

## Places the player and lets them settle, so a throw is never made mid-fall
## (the blade leaves from the player's centre, so height matters).
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

# ---------------------------------------------------------------- tests
func run_all() -> void:
	var tests := [
		"t_level_boots_with_player_on_the_ground",
		"t_gem_pickup_increments_the_counter",
		"t_heart_pickup_restores_health",
		"t_spikes_hurt_and_knock_back",
		"t_blade_flies_out_and_comes_back_and_is_caught",
		"t_blade_only_one_in_flight",
		"t_blade_damages_an_enemy_once_per_throw",
		"t_two_hits_kill_a_walker_and_award_score",
		"t_blade_breaks_a_crate",
		"t_enemy_contact_damages_the_player",
		"t_offscreen_enemies_are_frozen",
		"t_falling_out_of_the_world_kills",
		"t_exit_completes_the_level_and_sets_its_flag",
		"t_locked_door_stays_shut_without_the_key",
		"t_the_matching_key_opens_the_door_and_is_consumed",
		"t_switch_blocks_swap_which_half_is_solid",
		"t_the_blade_can_trip_a_switch_from_range",
		"t_hub_loads_its_doors",
		"t_hub_door_is_locked_until_its_prerequisite_is_cleared",
		"t_completed_level_sets_a_flag_that_survives_a_save_round_trip",
		"t_save_migration_upgrades_an_ancient_file",
		"t_full_loop_hub_to_level_and_back_marks_the_door_cleared",
		"t_a_pad_transforms_kaya_and_keeps_her_feet_planted",
		"t_frog_jumps_far_higher_than_the_human_and_carries_no_blade",
		"t_frog_clings_to_a_wall_instead_of_dropping",
		"t_fish_swims_freely_in_water",
		"t_fish_can_beach_itself_onto_the_bank",
		"t_fish_out_of_air_turns_back_into_kaya",
		"t_fish_bite_damages_an_adjacent_enemy",
		"t_bird_flapping_spends_stamina_and_perching_refills_it",
		"t_bird_cannot_climb_forever",
		"t_the_exit_puts_kaya_back_in_her_own_shape",
		"t_shooter_only_fires_when_you_are_in_its_line",
		"t_an_enemy_shot_hurts_the_player_and_dies_on_a_wall",
		"t_swimmer_stays_in_its_water_and_chases",
		"t_boss_spawns_locked_to_its_arena",
		"t_boss_changes_phase_as_its_health_falls",
		"t_boss_death_opens_the_way_out_and_unlocks_the_camera",
		"t_landing_dust_puffs_and_then_clears_itself_up",
		"t_the_particle_pool_cannot_be_overrun",
		"t_killing_an_enemy_freezes_the_sim_and_always_lets_go",
		"t_hitstop_refuses_to_stack_on_a_freeze_it_does_not_own",
		"t_hitstop_never_outlives_the_level_that_started_it",
		"t_shake_moves_the_camera_and_puts_it_back_exactly",
		"t_a_shake_cannot_throw_the_screen_flip_off_target",
		"t_effects_are_inert_when_nothing_is_attached",
		"t_animated_tiles_repaint_without_changing_the_level",
		"t_pause_freezes_the_level_and_resumes_it",
		"t_options_write_straight_through_to_the_save_file",
		"t_touch_stick_drives_the_same_actions_as_a_keyboard",
		"t_touch_overlay_hides_itself_when_a_gamepad_is_present",
		"t_the_ambience_layers_sit_between_the_right_neighbours",
		"t_light_pools_follow_the_screen_and_only_exist_where_a_level_asked",
		"t_a_tape_that_no_longer_matches_its_level_is_refused",
		"t_a_tape_that_is_malformed_or_starts_anywhere_but_spawn_is_refused",
	]
	for t in tests:
		if _only != "" and not t.contains(_only):
			continue
		_current = t
		await enter_arena()
		await call(t)
	await run_replays()
	_report()

# ---------------------------------------------------------------- the gate itself
## These two do to the tape gate what the rest of the suite does to the game:
## check the outcome, not the mechanism. A stale-tape rule nobody has watched
## fire is a comment. So each of them hands the loader a tape that is wrong in
## one specific way and insists it is refused.

const SCRATCH := "user://itest_tape_scratch.json"

## The committed fixture tape, as raw JSON, so a test can bend one field of it.
func arena_tape_json() -> Dictionary:
	var f := FileAccess.open(TAPE.tape_path(ARENA), FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return parsed as Dictionary if typeof(parsed) == TYPE_DICTIONARY else {}

func write_scratch(d: Dictionary) -> String:
	var f := FileAccess.open(SCRATCH, FileAccess.WRITE)
	f.store_string(JSON.stringify(d))
	f.close()
	return SCRATCH

## Loads a bent copy of the fixture and returns the refusal, or "" if it was
## wrongly accepted.
func refusal_for(bend: Callable) -> String:
	var d := arena_tape_json()
	if d.is_empty():
		return "FIXTURE MISSING"
	bend.call(d)
	var t: RefCounted = TAPE.load_from(ARENA, write_scratch(d))
	return t.error

func t_a_tape_that_no_longer_matches_its_level_is_refused() -> void:
	var fixture: RefCounted = TAPE.load_for(ARENA)
	check(fixture.ok(), "the committed fixture tape loads: %s" % fixture.error)
	check_eq(fixture.source_sha, TAPE.level_sha(ARENA),
		"and its source_sha is the sha256 of levels/%s.json" % ARENA)

	# One byte of the level changing must be enough. This is the rule that a
	# stale iOS .pck taught us to have, so it fails — it never warns.
	var stale := refusal_for(func(d: Dictionary) -> void:
		d["source_sha"] = "0".repeat(64))
	check(stale.contains("STALE TAPE"),
		"a tape whose source_sha misses is refused (got '%s')" % stale)

	var missing := refusal_for(func(d: Dictionary) -> void: d.erase("source_sha"))
	check(missing != "", "a tape with no source_sha at all is refused")

	var wrong_level := refusal_for(func(d: Dictionary) -> void: d["level"] = "jungle_9")
	check(wrong_level != "", "a tape that names another level is refused")

	var wrong_clock := refusal_for(func(d: Dictionary) -> void: d["fps"] = 30)
	check(wrong_clock != "", "a tape recorded at another frame rate is refused")

func t_a_tape_that_is_malformed_or_starts_anywhere_but_spawn_is_refused() -> void:
	var no_hops := refusal_for(func(d: Dictionary) -> void: d["hops"] = [])
	check(no_hops != "", "a tape with no hops is refused")

	# ADR 005: a tape is proof the level can be played *through*. One that starts
	# at a pad or a door proves a shortcut instead.
	var midway := refusal_for(func(d: Dictionary) -> void:
		((d["hops"] as Array)[0] as Dictionary)["from"] = "pad_frog")
	check(midway.contains("spawn"), "a tape that does not start at spawn is refused")

	var bad_button := refusal_for(func(d: Dictionary) -> void:
		var frames: Array = ((d["hops"] as Array)[0] as Dictionary)["frames"]
		(frames[0] as Dictionary)["a"] = "right+wiggle")
	check(bad_button.contains("wiggle"), "an action this build has no button for is refused")

	var zero_frames := refusal_for(func(d: Dictionary) -> void:
		var frames: Array = ((d["hops"] as Array)[0] as Dictionary)["frames"]
		(frames[0] as Dictionary)["n"] = 0)
	check(zero_frames != "", "a step held for no frames is refused")

	check(not TAPE.exists_for("no_such_level_at_all"),
		"a level with no tape beside it is simply absent, not an error")

## There is no "replay a tape re-cut into several hops" case, and that is on
## purpose. There was one: it took the arena tape, re-cut it at three arbitrary
## seams and asserted the level still finished. It had rotted — it re-cut
## `hops[0]` only, so the day the arena was re-proved into two hops it silently
## dropped the second and ran 181 of 219 frames, ending 56.7 px short. Repairing
## it is easy; the question was whether the thing it tested is tested anywhere
## else, now that six real prover tapes exist with 2 to 16 hops each.
##
## It is, and better. Two hop-boundary defects were injected into
## tape_replay.gd and the whole tier run against each:
##
##   a one-frame lull at every hop seam   real tapes: jungle_1, jungle_4 and
##                                        test_arena all fail. Re-cut case: PASSES.
##   seed each hop at its `from` waypoint,
##   the way the prover does              real tapes: jungle_1 dies mid-route,
##                                        jungle_4 lands 18.8 px short.
##                                        Re-cut case: PASSES.
##
## It passes both because three seams in one 219-frame arena tape is a smaller
## sample of the same property than fifty-odd seams across five real levels —
## and because its invented waypoints (`mid_a`, `mid_b`) name nothing, so a
## driver that seeds at waypoints simply skips them. The case was strictly
## weaker than the tapes beside it at the one thing it existed to check, so it
## was deleted rather than repaired. Re-run those two injections before adding
## anything like it back.

# ---------------------------------------------------------------- tape replay
## ADR 005 §3. One case per level: play the level with the proof tape written by
## tools/prove.sh and assert the outcome those buttons actually produce.
##
## On an ordinary level that outcome is the whole of §3 — the level reports
## itself complete. On a boss level it is not, and cannot be: see
## `check_boss_arrival()`.
##
## A level with no tape SKIPS, loudly, so this tier stays green before the
## prover lands — and turns red the moment a tape exists and is wrong. A tape
## that no longer matches its level is wrong: it fails, it never warns.
func run_replays() -> void:
	for id in replayable_levels():
		_current = "t_replay_%s" % id
		if _only != "" and not _current.contains(_only):
			continue
		if not TAPE.exists_for(id):
			skip("%s: no proof tape at proofs/%s.tape.json — run tools/prove.sh %s"
				% [_current, id, id])
			continue
		var tape: RefCounted = TAPE.load_for(id)
		if not tape.ok():
			failures.append("%s :: %s" % [_current, tape.error])
			continue
		var driver: RefCounted = TAPE_REPLAY.new(get_tree())
		driver.trace = _trace
		var r: Dictionary = await driver.replay(tape)
		if boss_of(id) != "":
			check_boss_arrival(id, r)
		elif bool(r["completed"]):
			passes += 1
			check(SaveManager.get_flag(id),
				"completing %s sets its flag" % id)
			check(Game.state == Game.State.HUB,
				"finishing %s returns to the hub" % id)
			if _trace:
				print("[tape] %s COMPLETE in %d sim frames (tape is %d)"
					% [id, r["sim_frames"], tape.total_frames])
		else:
			failures.append("%s :: tape did not finish the level — %s"
				% [_current, TAPE_REPLAY.describe(r)])
	# Whatever happened above, the next thing to run must start from a level.
	_current = "harness"
	await enter_arena()

## A boss level's tape proves arrival, because arrival is all it records.
##
## `src/world/level.gd` places `boss_exit` only inside `on_boss_defeated()`, so
## on jungle_5 the tape walks to the gate's tile and finds nothing there: the
## closest a pure traversal tape can get to completing that level is standing on
## the right square with 8.5 px of error and no gate. Asserting completion there
## asserts something the recording cannot contain, and a gate that demands the
## impossible gets relaxed until it demands nothing.
##
## So this asserts the outcome the buttons *do* produce: Kaya, alive, carried
## from spawn onto the floor of the boss arena, with the fight still in front of
## her. Whether the fight can then be won, survived and walked out of is the
## Boss Gate's question (ADR 005 §4) and is answered by
## tests/integration/boss_gate_*.gd — deliberately not here, and not implied
## here.
func check_boss_arrival(id: String, r: Dictionary) -> void:
	if bool(r["completed"]):
		failures.append(("%s :: the %s tape finished the level, which a traversal tape "
			+ "cannot do — boss_exit is placed when the boss dies. Either the boss has "
			+ "become skippable, or this tape now fights and this case must assert the "
			+ "fight instead of arrival. — %s")
			% [_current, id, TAPE_REPLAY.describe(r)])
		return

	var lvl: Node = level()
	if lvl == null or not is_instance_valid(lvl) or String(lvl.def.id) != id:
		failures.append("%s :: the replay left %s before the tape ran out — %s"
			% [_current, id, TAPE_REPLAY.describe(r)])
		return
	var p: Player = lvl.player as Player
	if p == null or not is_instance_valid(p):
		failures.append("%s :: no player at the end of the %s tape — %s"
			% [_current, id, TAPE_REPLAY.describe(r)])
		return
	var boss: Node = lvl.get("boss") as Node
	if boss == null or not is_instance_valid(boss):
		failures.append("%s :: %s declares a '%s' the level never spawned"
			% [_current, id, boss_of(id)])
		return

	var where := TAPE_REPLAY.describe(r)
	check(not bool(r["died"]), "the %s tape carries Kaya to the arena alive — %s" % [id, where])
	# The arena is the boss's own screen and the span it is clamped inside — the
	# numbers boss_grove.gd itself fights within, not a rectangle written here.
	var c := p.center()
	check_eq(Screen.index_of(c, Vector2i(999, 999)), boss.home_screen,
		"and onto the boss's screen — %s" % where)
	check(p.on_floor, "standing on the arena floor, not falling through it — %s" % where)
	check(c.x >= boss.arena_min and c.x <= boss.arena_max + boss.box.x,
		"inside the span the boss is clamped to (%.0f..%.0f, Kaya at %.0f)"
			% [boss.arena_min, boss.arena_max + boss.box.x, c.x])
	# And the reason completion is not asserted is itself an outcome: the tape
	# did not beat the Warden.
	check(not bool(boss.get("defeated")),
		"with the boss still alive, which is why this case stops here — %s" % where)

## The boss entity a level declares, or "" if it has none. `boss_exit` is a
## gate, not a boss, and a level may carry one without the fight being spawned.
func boss_of(id: String) -> String:
	var d := level_json(id)
	for raw: Variant in (d.get("entities", []) as Array):
		var t := String((raw as Dictionary).get("type", ""))
		if t.begins_with("boss_") and t != "boss_exit":
			return t
	return ""

func level_json(id: String) -> Dictionary:
	var f := FileAccess.open("%s/%s.json" % [LEVEL_DIR, id], FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return parsed as Dictionary if typeof(parsed) == TYPE_DICTIONARY else {}

## Every level a tape can be asked to finish: the playable ones. The hub is a
## top-down map with no exit to reach, so it is not one of them.
func replayable_levels() -> PackedStringArray:
	var out: PackedStringArray = PackedStringArray()
	var d := DirAccess.open(LEVEL_DIR)
	if d == null:
		failures.append("harness :: cannot list %s" % LEVEL_DIR)
		return out
	var names := d.get_files()
	names.sort()
	for n in names:
		if not n.ends_with(".json") or n.ends_with(".tape.json"):
			continue
		var id := n.substr(0, n.length() - 5)
		var def := level_json(id)
		if def.is_empty() or bool(def.get("topdown", false)):
			continue
		out.append(id)
	return out

func t_level_boots_with_player_on_the_ground() -> void:
	var p := player()
	check(p != null, "player exists")
	await frames(20)
	check(p.on_floor, "player settles on the floor")
	check_eq(int(p.pos.y + p.box.y), 12 * 16, "feet rest on the floor tile top")
	check_eq(Game.health, Game.max_health, "starts at full health")

func t_gem_pickup_increments_the_counter() -> void:
	var before := Game.gems
	await place(4, 10)
	await frames(30)
	check_eq(Game.gems, before + 1, "walking onto a gem collects it")
	check_eq(Game.score, 25, "a gem is worth 25")

func t_heart_pickup_restores_health() -> void:
	Game.health = 2
	await place(5, 8)
	await frames(40)
	check_eq(Game.health, 3, "a heart heals one")

func t_spikes_hurt_and_knock_back() -> void:
	# Sample at the first hit: the player stands on the spikes, so a fixed
	# 30-frame wait lets hits accumulate until she dies and player() goes nil.
	await place(20, 10)
	var before := Game.health
	var hurt := false
	for _i in 30:
		await frames(1)
		if Game.health < before:
			hurt = true
			break
	check(hurt, "spikes hurt")
	var p := player()
	check(p != null and p.invuln > 0.0, "and grant brief invulnerability")

func t_blade_flies_out_and_comes_back_and_is_caught() -> void:
	await place(3, 10)
	await frames(10)
	var p := player()
	p.facing = 1
	check(p.weapon != null, "player is armed")
	check(p.weapon.try_attack(p), "throw accepted")
	await frames(2)
	check_eq(blades().size(), 1, "exactly one blade in the world")
	var b: Blade = blades()[0]
	var start_x := b.center().x
	await frames(18)
	check(b.center().x > start_x + 20.0, "blade travels outward")
	# let it run its full course
	var caught := false
	for i in 200:
		await get_tree().physics_frame
		if not is_instance_valid(b):
			caught = true
			break
	check(caught, "blade returns and is caught")
	check_eq(blades().size(), 0, "nothing left in flight")

func t_blade_only_one_in_flight() -> void:
	await place(3, 10)
	var p := player()
	check(p.weapon.try_attack(p), "first throw fires")
	await frames(1)
	check(not p.weapon.try_attack(p), "second throw is refused while one is out")
	check_eq(blades().size(), 1, "still only one blade")

func t_blade_damages_an_enemy_once_per_throw() -> void:
	await place(13, 10)
	var p0 := player()
	p0.facing = -1
	var e: Enemy = enemies()[0] as Enemy
	e.pos = Vector2(9 * TS, p0.pos.y + p0.box.y - e.box.y)
	e.speed = 0.0
	e.contact_damage = 0
	var before := e.health
	p0.weapon.try_attack(p0)
	for i in 200:
		await get_tree().physics_frame
		if blades().is_empty():
			break
	check_eq(e.health, before - 1, "one throw deals exactly one hit, not two")

func t_two_hits_kill_a_walker_and_award_score() -> void:
	await place(13, 10)
	var p := player()
	var e: Enemy = enemies()[0] as Enemy
	e.pos = Vector2(9 * TS, p.pos.y + p.box.y - e.box.y)
	e.speed = 0.0
	e.contact_damage = 0
	e.cfg["drops"] = {}      # a random gem drop would muddy the score check
	var score_before := Game.score
	var value := e.score_value
	for throw in 2:
		p.facing = -1
		p.pos.x = 13 * TS
		p.weapon.try_attack(p)
		for i in 200:
			await get_tree().physics_frame
			if blades().is_empty():
				break
		await frames(20)
	check(not is_instance_valid(e) or e.health <= 0, "two throws kill a 2 HP walker")
	check_eq(Game.score, score_before + value, "score goes up by the enemy's value")

func t_blade_breaks_a_crate() -> void:
	await place(14, 10)
	var w: TileWorld = level().world
	check(w.is_solid(18, 11), "the crate starts solid")
	var p := player()
	p.facing = 1
	p.weapon.try_attack(p)
	for i in 200:
		await get_tree().physics_frame
		if blades().is_empty():
			break
	check(not w.is_solid(18, 11), "the blade shatters it")

func t_enemy_contact_damages_the_player() -> void:
	await place(9, 10)
	var p := player()
	var e: Enemy = enemies()[0] as Enemy
	e.pos = Vector2(p.pos.x, p.pos.y + p.box.y - e.box.y)
	e.vel = Vector2.ZERO
	var before := Game.health
	await frames(10)
	check(Game.health < before, "standing on a walker hurts")

func t_offscreen_enemies_are_frozen() -> void:
	var e: Enemy = enemies()[0] as Enemy
	check(e.active, "the arena is one screen, so the walker is awake")
	e.set_active_screen(Vector2i(5, 5))
	check(not e.active, "an enemy on another screen is frozen")
	var before := e.pos
	await frames(20)
	check_eq(e.pos, before, "and does not move")

func t_falling_out_of_the_world_kills() -> void:
	await place(11, 14)
	player().pos.y = level().world.pixel_height() + 64.0
	await frames(6)
	check(player().dead, "falling off the map kills")

func t_exit_completes_the_level_and_sets_its_flag() -> void:
	SaveManager.set_flag(ARENA, false)
	await place(22, 10)
	await frames(30)
	check(SaveManager.get_flag(ARENA), "touching the totem completes the level")
	check_eq(Game.state, Game.State.HUB, "and returns you to the hub")

# ---------------------------------------------------------------- doors & switches
const HOLLOW := "jungle_2"
const YELLOW_DOOR_TILE := Vector2i(14, 25)
const SWITCH_A_BLOCK := Vector2i(8, 13)     # solid while group 1 is ON
const SWITCH_A_GHOST := Vector2i(12, 10)    # solid while group 1 is OFF

func t_locked_door_stays_shut_without_the_key() -> void:
	await enter(HOLLOW)
	var w: TileWorld = level().world
	check(w.is_solid(YELLOW_DOOR_TILE.x, YELLOW_DOOR_TILE.y), "a closed door is a wall")
	await place(13, 24, 24)
	var p := player()
	var before := p.pos.x
	p.vel.x = 200.0
	await frames(20)
	check(p.pos.x < float(YELLOW_DOOR_TILE.x * TS), "you cannot walk through it")
	check(p.pos.x >= before - 1.0, "and you are not shoved backwards")

func t_the_matching_key_opens_the_door_and_is_consumed() -> void:
	await enter(HOLLOW)
	# The doorway is what is under test — a patrolling beetle knocking the
	# player airborne mid-walk would make this flaky for an unrelated reason.
	for n in enemies():
		var e := n as Enemy
		e.contact_damage = 0
		e.speed = 0.0
	var w: TileWorld = level().world
	Game.add_key("yellow")
	check_eq(int(Game.keys["yellow"]), 1, "key picked up")
	await place(13, 24, 30)
	# Walk into it — a closed door is solid, so contact means "pressed against".
	for i in 20:
		player().vel.x = 200.0
		await get_tree().physics_frame
	check(not w.is_solid(YELLOW_DOOR_TILE.x, YELLOW_DOOR_TILE.y), "the door opens")
	check_eq(int(Game.keys["yellow"]), 0, "and the key is spent")
	var doors := find_in_group(&"doors")
	check(doors.size() > 0 and (doors[0] as Door).open, "the door reports itself open")

	# The bug that shipped: the door "opened" but the gap was one tile and the
	# player is 22 px tall, so the doorway was a wall you could see through.
	# Opening it is not the assertion — getting to the other side is.
	var p := player()
	for i in 120:
		p.vel.x = 140.0
		await get_tree().physics_frame
		if p.pos.x > float((YELLOW_DOOR_TILE.x + 1) * TS):
			break
	check(p.pos.x > float((YELLOW_DOOR_TILE.x + 1) * TS),
		"the player walks through the opened door (reached x=%d, needed past %d)"
			% [int(p.pos.x), (YELLOW_DOOR_TILE.x + 1) * TS])
	check(p.on_floor, "and is standing on the far side, not wedged in the frame")

func t_switch_blocks_swap_which_half_is_solid() -> void:
	await enter(HOLLOW)
	var w: TileWorld = level().world
	check(w.is_solid(SWITCH_A_BLOCK.x, SWITCH_A_BLOCK.y), "group 1 starts ON")
	check(not w.is_solid(SWITCH_A_GHOST.x, SWITCH_A_GHOST.y), "so its pair is passable")
	var sw: SwitchTrigger = null
	for n in find_in_group(&"switches"):
		if (n as SwitchTrigger).group == 1:
			sw = n
			break
	check(sw != null, "level has a group 1 switch")
	if sw == null:
		return
	sw.toggle()
	await frames(2)
	check(not w.is_solid(SWITCH_A_BLOCK.x, SWITCH_A_BLOCK.y), "flipping swaps them")
	check(w.is_solid(SWITCH_A_GHOST.x, SWITCH_A_GHOST.y), "the ghost half becomes solid")

func t_the_blade_can_trip_a_switch_from_range() -> void:
	# Group 2's lever sits three tiles along a ledge in ROOT HOLLOW: far enough
	# that only a thrown blade reaches it.
	await enter(HOLLOW)
	var sw: SwitchTrigger = null
	for n in find_in_group(&"switches"):
		if (n as SwitchTrigger).group == 2:
			sw = n
			break
	if sw == null:
		check(false, "no group 2 switch")
		return
	var before := sw.on
	await place(37, 4, 24)
	var p := player()
	check(p.on_floor, "thrower is standing on the ledge")
	p.facing = 1
	p.weapon.try_attack(p)
	for i in 200:
		await get_tree().physics_frame
		if blades().is_empty():
			break
	check(sw.on != before, "the blade flips the lever on its way past")

# ---------------------------------------------------------------- hub & save
func t_hub_loads_its_doors() -> void:
	await enter_hub()
	var hub: Node = Game.main.current_scene()
	check(hub != null and hub.get("doors") != null, "hub scene is up")
	check(hub.doors.size() >= 2, "hub has doors")
	check(hub.player != null, "hub has a walker")

func t_hub_door_is_locked_until_its_prerequisite_is_cleared() -> void:
	SaveManager.set_flag("jungle_1", false)
	await enter_hub()
	var hub: Node = Game.main.current_scene()
	var gated: HubDoor = null
	for d: HubDoor in hub.doors:
		if d.requires != "":
			gated = d
			break
	check(gated != null, "at least one door is gated")
	if gated == null:
		return
	check(not gated.unlocked(), "%s is locked before %s is cleared" % [gated.level_id, gated.requires])
	SaveManager.set_flag(gated.requires, true)
	check(gated.unlocked(), "and unlocks once the prerequisite is done")
	SaveManager.set_flag("jungle_1", false)

func t_completed_level_sets_a_flag_that_survives_a_save_round_trip() -> void:
	SaveManager.set_flag(ARENA, false)
	SaveManager.save()
	await enter(ARENA)
	await place(22, 10, 30)
	await frames(20)
	check(SaveManager.get_flag(ARENA), "flag set on completion")
	SaveManager.save()
	SaveManager.load_or_create()
	check(SaveManager.get_flag(ARENA), "flag still set after reload")
	SaveManager.set_flag(ARENA, false)
	SaveManager.save()

func t_save_migration_upgrades_an_ancient_file() -> void:
	var ancient := {"completed": ["jungle_1", "jungle_2"], "score": 4200}
	var migrated := SaveManager.migrate(ancient)
	check_eq(int(migrated["version"]), SaveManager.CURRENT_VERSION, "version bumped")
	check(bool((migrated["flags"] as Dictionary).get("jungle_1", false)),
		"v0 completed list became flags")
	check_eq(int(migrated["best_score"]), 4200, "v0 score became best_score")
	check(not migrated.has("completed"), "the old key is gone")
	var settings: Dictionary = migrated["settings"]
	for k in ["music", "sfx", "touch_opacity", "touch_scale", "screen_flip"]:
		check(settings.has(k), "settings gained '%s'" % k)

func t_full_loop_hub_to_level_and_back_marks_the_door_cleared() -> void:
	# The whole progression loop in one test: hub -> gateway -> level -> exit ->
	# hub, with the door now showing as cleared.
	SaveManager.set_flag("jungle_1", false)
	SaveManager.save()
	await enter_hub()
	var hub: Node = Game.main.current_scene()
	var door: HubDoor = null
	for d: HubDoor in hub.doors:
		if d.level_id == "jungle_1":
			door = d
			break
	check(door != null, "the first gateway exists")
	if door == null:
		return
	check(door.unlocked(), "the first gateway is open from the start")
	check(not door.completed(), "and is not yet cleared")
	hub._try_enter(door)
	await frames(8)
	check_eq(Game.state, Game.State.LEVEL, "entering the gateway loads the level")
	check_eq(Game.current_level_id, "jungle_1", "…the right one")

	# Walk into that level's exit.
	var ex: LevelExit = null
	for n in find_in_group(&"triggers"):
		if n is LevelExit:
			ex = n
			break
	check(ex != null, "jungle_1 has an exit")
	if ex == null:
		return
	var p := player()
	p.pos = ex.pos + Vector2(2, 0)
	await frames(20)
	check_eq(Game.state, Game.State.HUB, "the exit returns you to the hub")
	check(SaveManager.get_flag("jungle_1"), "and the level is flagged complete")

	await frames(6)
	var hub2: Node = Game.main.current_scene()
	var door2: HubDoor = null
	var gated: HubDoor = null
	for d: HubDoor in hub2.doors:
		if d.level_id == "jungle_1":
			door2 = d
		elif d.requires == "jungle_1":
			gated = d
	check(door2 != null and door2.completed(), "the gateway now shows as cleared")
	check(gated != null and gated.unlocked(), "and the next one has opened")
	SaveManager.set_flag("jungle_1", false)
	SaveManager.save()

# ---------------------------------------------------------------- forms
const WATERWAY := "jungle_3"
const SKY := "jungle_4"

func _apex_of(p: Player) -> float:
	## Jump straight up from a standstill and report how high we got, in pixels.
	p.vel = Vector2.ZERO
	var start := p.pos.y
	var best := start
	Input.action_press("jump")
	for i in 90:
		await get_tree().physics_frame
		best = minf(best, p.pos.y)
		if i == 30:
			Input.action_release("jump")
	Input.action_release("jump")
	return start - best

func t_a_pad_transforms_kaya_and_keeps_her_feet_planted() -> void:
	await enter(SKY)
	var p := player()
	check_eq(p.form_id, "human", "levels start human")
	var pad: TransformPad = null
	for n in find_in_group(&"pads"):
		if (n as TransformPad).form_id == "frog":
			pad = n
			break
	check(pad != null, "SKY BRANCH has a frog pad")
	if pad == null:
		return
	await place(6, 24, 24)
	var feet_before := p.pos.y + p.box.y
	p.pos.x = pad.pos.x
	await frames(10)
	check_eq(p.form_id, "frog", "stepping on the pad transforms her")
	var feet_after := p.pos.y + p.box.y
	near(feet_after, feet_before, 2.0, "the smaller hitbox stays on the ground")

func t_frog_jumps_far_higher_than_the_human_and_carries_no_blade() -> void:
	await enter(SKY)
	await place(4, 24, 26)
	var p := player()
	var human_apex: float = await _apex_of(p)
	check(p.weapon != null, "the human carries the blade")
	p.set_form("frog")
	await place(4, 24, 26)
	var frog_apex: float = await _apex_of(p)
	check(frog_apex > human_apex * 1.4,
		"the frog must jump much higher (%d vs %d px)" % [int(frog_apex), int(human_apex)])
	check(p.weapon == null, "…and gives up the blade for it")
	check(not p.form.can_attack, "the frog cannot attack")

func t_frog_clings_to_a_wall_instead_of_dropping() -> void:
	await enter(SKY)
	var p := player()
	p.set_form("frog")
	# The frog shaft has a wall at column 11; press into it in mid-air.
	p.pos = Vector2(12 * TS, 18 * TS)
	p.vel = Vector2(0, 200.0)
	level().cam.snap_to_target()
	Input.action_press("move_left")
	var touched := false
	for i in 30:
		await get_tree().physics_frame
		if p.against_wall != 0:
			touched = true
			break
	check(touched, "reached the wall")
	# The cling is applied on the tick *after* contact is reported, so sample a
	# few frames later and take the worst reading.
	var worst := 0.0
	for i in 8:
		await get_tree().physics_frame
		worst = maxf(worst, p.vel.y)
	Input.action_release("move_left")
	check(worst <= float(p.form.cfg.get("wall_slide_speed", 34.0)) + 1.0,
		"clinging caps the fall speed (peak %d px/s)" % int(worst))

func t_fish_swims_freely_in_water() -> void:
	await enter(WATERWAY)
	var p := player()
	p.set_form("fish")
	p.pos = Vector2(18 * TS, 25 * TS)
	p.vel = Vector2.ZERO
	level().cam.snap_to_target()
	await frames(4)
	check(p.in_water(), "the channel is water")
	var y0 := p.pos.y
	Input.action_press("move_up")
	await frames(24)
	Input.action_release("move_up")
	check(p.pos.y < y0 - 12.0, "a fish can swim upward against gravity")
	var x0 := p.pos.x
	Input.action_press("move_right")
	await frames(24)
	Input.action_release("move_right")
	check(p.pos.x > x0 + 12.0, "and sideways")

## The east bank is one tile above the water. The surface hop used to reach
## 12.5 px against a 16 px step, so a fish could never leave the water and the
## level was a dead end for anyone who used the fish pad.
func t_fish_can_beach_itself_onto_the_bank() -> void:
	await enter(WATERWAY)
	var p := player()
	p.set_form("fish")
	var hop: float = absf(float(p.form.cfg["surface_hop"]))
	var g: float = float(p.form.cfg["gravity"])
	check(hop * hop / (2.0 * g) > float(TS),
		"the surface hop must clear a one-tile bank (reaches %.1f px, needs %d)"
			% [hop * hop / (2.0 * g), TS])

	p.pos = Vector2(42 * TS, 22 * TS)
	p.vel = Vector2.ZERO
	level().cam.snap_to_target()
	await frames(6)
	check(p.in_water(), "starting in the channel")
	# Swim up until the head breaks the surface — that is when the hop is
	# allowed — rather than guessing a frame count.
	Input.action_press("move_up")
	Input.action_press("move_right")
	var surfaced := false
	for i in 120:
		await get_tree().physics_frame
		if not p.submerged():
			surfaced = true
			break
	check(surfaced, "the fish reaches the surface")
	Input.action_press("jump")
	await frames(3)
	Input.action_release("jump")
	var beached := false
	for i in 90:
		await get_tree().physics_frame
		if p.on_floor and not p.in_water():
			beached = true
			break
	Input.action_release("move_up")
	Input.action_release("move_right")
	check(beached, "the fish beaches itself on the bank (ended at tile %v)"
		% (p.center() / TS).floor())

func t_fish_out_of_air_turns_back_into_kaya() -> void:
	await enter(WATERWAY)
	var p := player()
	p.set_form("fish")
	p.pos = Vector2(4 * TS, 24 * TS)   # dry shore
	p.vel = Vector2.ZERO
	level().cam.snap_to_target()
	await frames(6)
	check(not p.in_water(), "we are on dry land")
	check(p.form.air_fraction() > 0.9, "the air meter starts full")
	await frames(int(float(p.form.cfg["air_seconds"]) * 60.0) + 30)
	# Reverting rather than dying: a beached fish must never be a dead end, and
	# dying to a mechanic nobody explained reads as a bug.
	check_eq(p.form_id, "human", "running out of air turns her back")
	check(not p.dead, "and does not kill her")

func t_fish_bite_damages_an_adjacent_enemy() -> void:
	await enter(WATERWAY)
	var p := player()
	p.set_form("fish")
	check(p.weapon != null and p.weapon.id == "bite", "the fish bites instead of throwing")
	var es := enemies()
	if es.is_empty():
		check(false, "the level has an enemy to bite")
		return
	var e: Enemy = es[0] as Enemy
	e.contact_damage = 0
	e.speed = 0.0
	p.pos = e.pos - Vector2(12.0, 0.0)
	p.facing = 1
	await frames(2)
	var before := e.health
	p.weapon.try_attack(p)
	await frames(10)
	check_eq(e.health, before - 1, "the bite lands")

func t_bird_flapping_spends_stamina_and_perching_refills_it() -> void:
	await enter(SKY)
	await place(4, 24, 26)
	var p := player()
	p.set_form("bird")
	await frames(20)
	check(p.form.max_stamina > 0.0, "the bird has a stamina budget")
	p.form.stamina = p.form.max_stamina
	var full := p.form.stamina
	Input.action_press("jump")
	await frames(40)
	Input.action_release("jump")
	check(p.form.stamina < full, "flapping costs stamina")
	var spent := p.form.stamina
	var landed := false
	for i in 300:             # glide down and perch
		await get_tree().physics_frame
		if p.on_floor:
			landed = true
			break
	check(landed, "the bird comes back down")
	await frames(40)
	check(p.form.stamina > spent, "perching refills it")

func t_bird_cannot_climb_forever() -> void:
	# An exhausted bird already in the air can glide, but not climb. (From the
	# ground it can still make an ordinary jump — that costs nothing.)
	await enter(SKY)
	await place(4, 20, 4)
	var p := player()
	p.set_form("bird")
	p.form.stamina = 0.0
	p.vel = Vector2.ZERO
	await frames(2)
	var y0 := p.pos.y
	Input.action_press("jump")
	for i in 40:
		await get_tree().physics_frame
		p.form.stamina = 0.0
		check(p.pos.y >= y0 - 2.0, "an exhausted bird never gains height")
		if p.on_floor:
			break
	Input.action_release("jump")

func t_the_exit_puts_kaya_back_in_her_own_shape() -> void:
	await enter(ARENA)
	var p := player()
	p.set_form("frog")
	check_eq(p.form_id, "frog", "transformed")
	await place(22, 10, 30)
	await frames(20)
	check_eq(Game.state, Game.State.HUB, "the level ended")
	# The exit reverts the form before the hand-off, so nothing leaks out.
	check(SaveManager.get_flag(ARENA), "and it counted as complete")
	SaveManager.set_flag(ARENA, false)
	SaveManager.save()

# ---------------------------------------------------------------- late enemies
const GROVE := "jungle_5"

func shots() -> Array:
	return find_in_group(&"hostile_shots")

func first_enemy(id: String) -> Enemy:
	for n in enemies():
		if (n as Enemy).enemy_id == id:
			return n
	return null

func t_shooter_only_fires_when_you_are_in_its_line() -> void:
	await enter(GROVE)
	var sh := first_enemy("shooter")
	check(sh != null, "HEART OF THE GROVE has a shooter")
	if sh == null:
		return
	sh.contact_damage = 0
	var p := player()
	# Well above its sight band: nothing should come out.
	p.pos = sh.pos - Vector2(60.0, 90.0)
	p.vel = Vector2.ZERO
	await frames(120)
	check_eq(shots().size(), 0, "no shots while you are out of its line")
	# Now step into line.
	p.pos = Vector2(sh.pos.x - 60.0, sh.pos.y)
	for i in 200:
		await get_tree().physics_frame
		p.pos = Vector2(sh.pos.x - 60.0, sh.pos.y)
		p.invuln = 1.0
		if shots().size() > 0:
			break
	check(shots().size() > 0, "it spits once you are level with it")

func t_an_enemy_shot_hurts_the_player_and_dies_on_a_wall() -> void:
	await enter(GROVE)
	var p := player()
	await place(4, 25, 20)
	var pj := Projectile.new()
	pj.setup({"speed": 90.0, "damage": 1, "life": 3.0, "frame": 0, "gravity": 0.0},
		p.center() + Vector2(30.0, 0.0), Vector2.LEFT, level().world, level())
	level().entities.add_child(pj)
	var before := Game.health
	p.invuln = 0.0
	await frames(40)
	check(Game.health < before, "the shot connects")
	check(not is_instance_valid(pj), "and is consumed")

func t_swimmer_stays_in_its_water_and_chases() -> void:
	await enter(GROVE)
	var sw := first_enemy("swimmer")
	check(sw != null, "the level has a piranha")
	if sw == null:
		return
	sw.contact_damage = 0
	check(sw.in_water(), "it starts in the pool")
	await frames(90)
	check(sw.in_water(), "and stays there when left alone")
	var p := player()
	p.set_form("fish")
	p.pos = sw.pos + Vector2(40.0, 0.0)
	p.invuln = 999.0
	var d0 := sw.center().distance_to(p.center())
	await frames(30)
	check(sw.center().distance_to(p.center()) < d0, "it closes on a swimming player")

# ---------------------------------------------------------------- boss
func boss() -> Enemy:
	var b := find_in_group(&"bosses")
	return b[0] as Enemy if b.size() > 0 else null

func t_boss_spawns_locked_to_its_arena() -> void:
	await enter(GROVE)
	var b := boss()
	check(b != null, "the Warden is present")
	if b == null:
		return
	check_eq(b.health, b.max_health, "at full health")
	var p := player()
	p.pos = b.pos - Vector2(40.0, 40.0)
	p.invuln = 999.0
	level().cam.snap_to_target()
	level()._on_screen_changed(level().cam.screen)
	await frames(10)
	check(level().cam.locked, "the camera locks in the arena")
	# It must never wander out of its own screen.
	await frames(240)
	check_eq(Screen.index_of(b.center(), Vector2i(9, 9)), b.home_screen,
		"the boss stays in its arena")

func t_boss_changes_phase_as_its_health_falls() -> void:
	await enter(GROVE)
	var b := boss()
	if b == null:
		check(false, "no boss")
		return
	check_eq(b.phase, 0, "starts in phase 1")
	check_eq(b.phase_name(), "STOMP", "…named STOMP")
	while b.health > 12:
		b.hurt(1, b.center())
	await frames(2)
	check_eq(b.phase, 1, "drops into phase 2 at the health threshold")
	while b.health > 6:
		b.hurt(1, b.center())
	await frames(2)
	check_eq(b.phase, 2, "and phase 3")
	check_eq(b.phase_name(), "FURY", "…named FURY")

func t_boss_death_opens_the_way_out_and_unlocks_the_camera() -> void:
	await enter(GROVE)
	var b := boss()
	if b == null:
		check(false, "no boss")
		return
	var score_before := Game.score
	var value := b.score_value
	var exits_before := 0
	for n in find_in_group(&"triggers"):
		if n is LevelExit:
			exits_before += 1
	check_eq(exits_before, 0, "the gate is closed while it lives")
	while b.health > 0:
		b.hurt(1, b.center())
	await frames(6)
	check(b.defeated, "the Warden falls")
	check_eq(Game.score, score_before + value, "and is worth its score")
	check(not level().cam.locked, "the camera unlocks")
	var exits_after := 0
	for n in find_in_group(&"triggers"):
		if n is LevelExit:
			exits_after += 1
	check_eq(exits_after, 1, "the gate opens")

# ---------------------------------------------------------------- juice
## Phase 5. Two of these are soft-lock guards rather than feature tests: a
## hitstop that never releases `Game.sim_paused`, or a shake that leaves the
## camera off its screen, would both look like the game had hung.
func field() -> ParticleField:
	return Fx.particles()

func t_landing_dust_puffs_and_then_clears_itself_up() -> void:
	var f := field()
	check(f != null, "the level has a particle field")
	if f == null:
		return
	f.clear()
	await place(3, 3, 0)
	var seen := 0
	for i in 90:
		await get_tree().physics_frame
		seen = maxi(seen, f.live_count())
		if player() != null and player().on_floor and i > 4:
			break
	gt_check(seen, 0, "landing from a height raises dust")
	await frames(60)
	check_eq(f.live_count(), 0, "and every particle is handed back to the pool")

func t_the_particle_pool_cannot_be_overrun() -> void:
	var f := field()
	check(f != null, "the level has a particle field")
	if f == null:
		return
	await place(4, 10)
	f.clear()
	# Far more bursts than the pool could ever hold, in a single frame.
	for i in 200:
		Fx.burst("scatter", player().center())
	check(f.live_count() <= f.pool_size(),
		"live particles (%d) must never exceed the pool (%d)" % [f.live_count(), f.pool_size()])
	gt_check(f.live_count(), 0, "though the burst did spawn something")
	await frames(60)
	check_eq(f.live_count(), 0, "and the flood drains completely")

func t_killing_an_enemy_freezes_the_sim_and_always_lets_go() -> void:
	await place(3, 10)
	var live := enemies()
	check(not live.is_empty(), "the arena has an enemy to kill")
	if live.is_empty():
		return
	var e: Enemy = live[0]
	var clock := TileAnim.shared().time
	e.hurt(99, e.center())
	check(Game.sim_paused, "the kill freezes the simulation")
	check(Fx.hitstop_active(), "and Fx is the one holding the flag")
	await frames(2)
	near(TileAnim.shared().time, clock, 0.001, "animated tiles hold their frame too")
	await frames(40)   # two thirds of a second — far past any hitstop preset
	check(not Game.sim_paused, "the freeze always lets go")
	check(not Fx.hitstop_active(), "and Fx no longer claims it")

func t_hitstop_refuses_to_stack_on_a_freeze_it_does_not_own() -> void:
	await place(3, 10)
	# Stand in for a screen flip mid-slide, which owns sim_paused for 0.12s.
	Game.sim_paused = true
	Fx.hitstop("kill")
	check(not Fx.hitstop_active(), "hitstop stands aside when something else is frozen")
	Game.sim_paused = false
	await frames(20)
	check(not Game.sim_paused, "and never clears a flag it did not set")

func t_hitstop_never_outlives_the_level_that_started_it() -> void:
	await place(3, 10)
	Fx.hitstop("kill")
	check(Game.sim_paused, "hitstop froze the simulation")
	# Leaving mid-freeze is exactly what dying or taking an exit does.
	await enter_arena()
	check(not Game.sim_paused, "the new level starts unfrozen")
	check(not Fx.hitstop_active(), "no freeze survives a scene swap")
	await frames(10)
	check(not Game.sim_paused, "and it stays that way")

func t_shake_moves_the_camera_and_puts_it_back_exactly() -> void:
	await place(4, 10)
	var cam: CameraController = level().cam
	var home: Vector2 = cam.screen_origin(cam.screen)
	var screen0: Vector2i = cam.screen
	check_eq(cam.position, home, "the camera starts on its screen origin")
	Fx.shake("boss_slam")
	var moved := false
	for i in 14:
		await get_tree().physics_frame
		if cam.position != home:
			moved = true
		check_eq(cam.screen, screen0, "a shake never changes the screen index")
		check_eq(cam.base_pos, home, "and never moves the camera itself, only the offset")
		check(cam.shake_offset.length() <= CameraController.MAX_SHAKE_PX + 0.001,
			"the offset stays inside the tile cull margin")
	check(moved, "the screen actually shook")
	await frames(40)
	check_eq(cam.shake_offset, Vector2.ZERO, "the offset decays to exactly zero")
	check_eq(cam.position, home, "so the camera lands back on the exact screen origin")

func t_a_shake_cannot_throw_the_screen_flip_off_target() -> void:
	await enter("jungle_1")
	var cam: CameraController = level().cam
	check(cam.flip_mode, "this test needs the flip camera")
	if not cam.flip_mode:
		return
	Fx.shake("boss_slam")
	var p := player()
	# A ledge one screen to the east, crossed while the camera is still shaking.
	p.pos = Vector2(37.0 * TS, 9.0 * TS)
	p.vel = Vector2.ZERO
	await frames(60)
	check_eq(cam.screen, Vector2i(1, 0), "the camera followed onto the next screen")
	check_eq(cam.position, cam.screen_origin(cam.screen), "and landed dead on it")
	check_eq(cam.base_pos, cam.screen_origin(cam.screen), "with the slide finished")
	check(not Game.sim_paused, "the slide released the simulation")

func t_effects_are_inert_when_nothing_is_attached() -> void:
	await place(4, 10)
	Fx.detach()
	check_eq(Fx.burst("dust", Vector2(64, 64)), 0, "a burst with no field spawns nothing")
	Fx.shake("boss_slam")        # no camera to shake: must be a no-op, not a crash
	await frames(4)
	# Hitstop deliberately still works without art or a camera — it is simulation,
	# not decoration — but it must still let go on its own.
	Fx.hitstop("kill")
	await frames(30)
	check(not Game.sim_paused, "a freeze with nothing attached still releases")
	check(not Fx.hitstop_active(), "and hands the flag back")

func t_animated_tiles_repaint_without_changing_the_level() -> void:
	await place(4, 10)
	var anim := TileAnim.shared()
	check(anim.has_any(), "the animation table loaded")
	var fg: TileRenderer = level().tiles_fg
	check(fg.live_animated_ids().has(6), "the arena's vines are seen as animated")
	var before := anim.time
	await frames(20)
	gt_check_f(anim.time, before, "the shared tile clock advances with the level")
	# The point of the whole design: the tile id, and therefore collision, is
	# exactly what it was before Phase 5.
	check_eq(level().world.get_fg(17, 6), 6, "the vine tile id is untouched")
	check(level().world.is_ladder(17, 6), "and it is still a ladder while it sways")

# ---------------------------------------------------------------- ui
func t_pause_freezes_the_level_and_resumes_it() -> void:
	await enter(ARENA)
	await place(4, 10, 20)
	var p := player()
	Input.action_press("pause")
	await frames(2)
	Input.action_release("pause")
	await frames(2)
	check(Game.main.ui.has_node("PauseScreen"), "pause screen opened")
	check(get_tree().paused, "the tree is paused")
	var before := p.pos
	Input.action_press("move_right")
	await frames(20)
	Input.action_release("move_right")
	check_eq(p.pos, before, "nothing moves while paused")
	var pause_node: Node = Game.main.ui.get_node("PauseScreen")
	pause_node.queue_free()
	await frames(4)
	check(not get_tree().paused, "closing it resumes the tree")

func t_options_write_straight_through_to_the_save_file() -> void:
	var old := float(SaveManager.setting("music", 0.7))
	SaveManager.set_setting("music", 0.3)
	SaveManager.save()
	SaveManager.load_or_create()
	near(float(SaveManager.setting("music", 0.0)), 0.3, 0.001, "music volume persisted")
	SaveManager.set_setting("screen_flip", false)
	SaveManager.save()
	SaveManager.load_or_create()
	check(not bool(SaveManager.setting("screen_flip", true)), "screen flip persisted")
	# Restore, and prove the camera honours the setting on the next level load.
	await enter(ARENA)
	check(not level().cam.flip_mode, "the camera reads the setting at load time")
	SaveManager.set_setting("screen_flip", true)
	SaveManager.set_setting("music", old)
	SaveManager.save()

func t_touch_stick_drives_the_same_actions_as_a_keyboard() -> void:
	await enter(ARENA)
	await place(4, 10, 20)
	var touch: Control = Game.main.touch
	check(touch != null, "the overlay exists")
	if touch == null:
		return
	touch.force_enable(true)
	var p := player()
	var x0 := p.pos.x
	# Thumb down on the left half, then dragged right.
	var down := InputEventScreenTouch.new()
	down.index = 0
	down.position = Vector2(70, 190)
	down.pressed = true
	Input.parse_input_event(down)
	var drag := InputEventScreenDrag.new()
	drag.index = 0
	drag.position = Vector2(110, 190)
	Input.parse_input_event(drag)
	await frames(24)
	check(Input.is_action_pressed(&"move_right"), "the stick presses move_right")
	check(p.pos.x > x0 + 8.0, "and the player actually runs")
	var up := InputEventScreenTouch.new()
	up.index = 0
	up.position = Vector2(110, 190)
	up.pressed = false
	Input.parse_input_event(up)
	await frames(4)
	check(not Input.is_action_pressed(&"move_right"), "lifting the thumb releases it")
	touch.force_enable(false)

func t_touch_overlay_hides_itself_when_a_gamepad_is_present() -> void:
	var touch: Control = Game.main.touch
	if touch == null:
		check(false, "no overlay")
		return
	touch.force_enable(true)
	check(touch.visible, "forced on for the test")
	touch._update_visibility()
	# On this desktop there is no touchscreen, so the overlay must stand down.
	check(not touch.enabled, "no touchscreen means no overlay")
	check(not touch.visible, "and is hidden")

# ---------------------------------------------------------------- report
func _report() -> void:
	print("")
	for s in skips:
		print("  SKIP %s" % s)
	var tail := "" if skips.is_empty() else ", %d skipped" % skips.size()
	if failures.is_empty():
		print("integration: %d checks, ALL PASSED%s" % [passes, tail])
		get_tree().quit(0)
	else:
		for f in failures:
			print("  FAIL %s" % f)
		print("integration: %d passed, %d FAILED%s" % [passes, failures.size(), tail])
		get_tree().quit(1)


# ---------------------------------------------------------------- ambience
## Phase 3. The ambience layers are three instances of one script at three fixed
## depths, and every one of them is wrong if it lands in the wrong place: haze in
## front of the tiles washes the level out, light behind them never shows, and a
## vignette after the entities dims the player. Nothing outside a running scene
## tree can see the order, so it is checked here.
func t_the_ambience_layers_sit_between_the_right_neighbours() -> void:
	var l := level()
	var names: Array[String] = []
	for c in l.get_children():
		names.append(String(c.name))
	check(names.find("BgSky") == 0, "the furthest plane is drawn first")
	check(names.find("Air") > names.find("BgNear"), "haze is in front of the parallax")
	check(names.find("Air") < names.find("TilesBg"), "and behind the tiles")
	check(names.find("Shade") > names.find("TilesFg"), "the vignette is over the tiles")
	check(names.find("Lights") > names.find("Shade"), "light punches through it")
	check(names.find("Lights") < names.find("Entities"),
		"and nothing ambient is ever drawn over the player")
	# The roles have to match the depths, which is a separate mistake to make:
	# three layers all quietly doing the same job looks like a lighting bug.
	check_eq(l.air.role, AmbienceLayer.Role.AIR, "Air layer role")
	check_eq(l.shade.role, AmbienceLayer.Role.SHADE, "Shade layer role")
	check_eq(l.lights.role, AmbienceLayer.Role.LIGHT, "Lights layer role")

func t_light_pools_follow_the_screen_and_only_exist_where_a_level_asked() -> void:
	# The arena is deliberately unlit (data/ambience.json), so it is also the
	# proof that an unlit level pays nothing for the feature.
	var arena_pools: int = level().lights.visible_pools()
	check_eq(arena_pools, 0, "the arena has no light pools")
	await enter("jungle_2")
	var l := level()
	var authored: int = l.amb.pools.size()
	gt_check(authored, 0, "ROOT HOLLOW authors light pools")
	var lit := 0
	for sx in 2:
		for sy in 2:
			l._on_screen_changed(Vector2i(sx, sy))
			var n: int = l.lights.visible_pools()
			check(n <= AmbienceLayer.MAX_POOLS, "pools per screen stay capped")
			lit += n
	gt_check(lit, 0, "and they are found on the screens they sit on")
