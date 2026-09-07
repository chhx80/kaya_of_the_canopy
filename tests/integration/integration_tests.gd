extends Node
## In-game integration suite. The headless unit runner has no autoloads and no
## scene tree, so anything involving nodes — the blade, enemies, pickups,
## triggers, respawn — is verified here instead, driving the real game.
##
## Run with tools/itest.sh (exit code is the gate).

const ARENA := "test_arena"
const TS := 16.0

var failures: PackedStringArray = PackedStringArray()
var passes := 0
var _current := ""

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("run_all")

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
		"t_fish_drowns_when_it_leaves_the_water",
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
		"t_pause_freezes_the_level_and_resumes_it",
		"t_options_write_straight_through_to_the_save_file",
		"t_touch_stick_drives_the_same_actions_as_a_keyboard",
		"t_touch_overlay_hides_itself_when_a_gamepad_is_present",
	]
	for t in tests:
		_current = t
		await enter_arena()
		await call(t)
	_report()

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
	var before := Game.health
	await place(20, 10)
	await frames(30)
	check(Game.health < before, "spikes hurt")
	check(player().invuln > 0.0, "and grant brief invulnerability")

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

func t_fish_drowns_when_it_leaves_the_water() -> void:
	await enter(WATERWAY)
	var p := player()
	p.set_form("fish")
	p.pos = Vector2(4 * TS, 24 * TS)   # dry shore
	p.vel = Vector2.ZERO
	level().cam.snap_to_target()
	await frames(6)
	check(not p.in_water(), "we are on dry land")
	check(p.form.air_fraction() > 0.9, "the air meter starts full")
	await frames(int(float(p.form.cfg["air_seconds"]) * 60.0) + 20)
	check(p.dead, "a fish out of water dies")

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
	if failures.is_empty():
		print("integration: %d checks, ALL PASSED" % passes)
		get_tree().quit(0)
	else:
		for f in failures:
			print("  FAIL %s" % f)
		print("integration: %d passed, %d FAILED" % [passes, failures.size()])
		get_tree().quit(1)
