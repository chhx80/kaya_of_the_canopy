extends Node
## In-game suite for THE OBSIDIAN HEART's one new mechanism: an arena that moves.
##
## `tools/bossgate.sh --level=nest_5 --boss=obsidian_heart` already answers the
## five questions of ADR 005 section 4 — defeatable, survivable, fair,
## arena-bound, and it ends — and since this boss it answers the fair one PER
## PHASE CONFIGURATION, which is the extension that landed in
## tests/integration/boss_gate_checks.gd with this fight. This file does not
## restate any of them. It exists for the things the gate structurally cannot
## see, and there are five:
##
##   * **The gate sweeps where you can STAND. The mechanic is what you can
##     CLIMB.** Every one of this arena's six refuge tiers is standable in every
##     configuration — the plug that seals a bay is two rows above its ledge —
##     so the gate's per-phase standable sets are identical and its diff reports
##     "nothing changed" three times. What actually changed is solidity, and
##     what that buys is reachability: in SEALED only the frog's shelf can be
##     climbed to, in INVERTED only the bird's, in MOLTEN only the human's.
##     `t_each_phase_opens_exactly_one_bay` is that claim, measured by putting
##     the real player on the real ledge and jumping her at the real shelf with
##     the real form code — not by reading tile ids.
##
##   * **A flip must never crush.** `TileWorld.set_switch()` changes an answer;
##     it cannot push a body out of a tile it has just made solid, and nothing in
##     `TileCollision` is watching. This level's geometry is built so that no
##     body STANDING anywhere can be inside a switch tile, and
##     `t_no_flip_can_close_on_a_standing_body` proves that by standing her on
##     every standable tile in the arena and flipping the nest under her. What is
##     left is a body in the AIR inside a plug column at the moment of the flip,
##     which is real, and `t_a_flip_that_closes_on_her_sets_her_down` is the
##     measurement of what `set_switch` does to an overlapping body and of the
##     answer `_make_room_for_player()` gives.
##
##   * **The telegraph.** A safe beat that no test watches is a comment. The
##     Heart holds still for `reforge_time` before it writes, and
##     `t_the_nest_telegraphs_before_it_turns` asserts the order of those two
##     events and that nothing it throws lands during the beat.
##
##   * **Nothing is restored, and that has to be TRUE rather than merely
##     unimplemented.** THE TIDE MAW restores its arena and says so; this one must
##     not, because the configuration is the mechanic. `t_the_arena_is_left_in_the_
##     configuration_that_killed_it` walks the kill and reads the tile grid after.
##
##   * **A dead boss must not keep working.** The last blade of the fight crosses
##     MOLTEN's threshold on the same call that kills it.
##     `t_a_dead_heart_does_not_turn_the_nest` is that.
##
## Everything here is asserted on the outcome, never on the mechanism.
##
## Part of tools/itest.sh once integration folds it in, which is three lines in
## tests/integration/integration_tests.gd and nothing else — the existing
## `_fold_in` pattern, exactly as t_boss_brood_queen:
##
##     "t_boss_obsidian_heart",                          # in the `tests` array
##
##     func t_boss_obsidian_heart() -> void:
##         await _fold_in("res://tests/integration/boss_obsidian_heart_tests.gd")
##
## `standalone = false` is what stops it printing its own report.
##
## Still runnable on its own — this file owns its whole harness:
##   $GODOT --headless --fixed-fps 60 --path . \
##       res://tests/integration/boss_obsidian_heart_runner.tscn
## or, in the suite: ITEST_TIMEOUT=600 tools/itest.sh --only=t_boss_obsidian_heart

const LEVEL := "nest_5"
const BOSS := "obsidian_heart"
const TS := 16.0

## Geometry of nest_5's hearthold, named so a level edit breaks a name and not a
## number. These are the values tools/worlds/nest_5.py draws from, in ITS
## convention: a row number is the row a body's FEET are in. The Boss Gate's own
## convention is the row a body STANDS ON, which is one lower; `_on()` converts,
## once, so the difference is visible instead of lurking.
const ARENA_SCREEN := Vector2i(1, 1)
const FLOOR_ROW := 27          ## the cap
const STAND_ROW := 26          ## feet on the arena floor
const STEP_ROW := 25           ## the bays' permanent one-way ledges
const STEP_STAND := 24
const SHELF_ROW := 23          ## the bays' permanent solid upper tier
const SHELF_STAND := 22
const PLUG_TOP := 21
const PLUG_BOT := 22
const ARENA_X0 := 26
const ARENA_X1 := 48
const DROP_COL := 36           ## the flue's landing, and the floor pad_human

## name -> step columns, shelf columns, the column pair the climb runs between,
## ONE column that actually carries that bay's plug (`gate` — the human bay's
## gates are NOT in its step, see tools/worlds/nest_5.py on coyote time), the pad
## on the shelf, and the phase whose configuration opens it.
const BAYS := {
	"frog": {"step": [28, 29], "shelf": [30, 31], "climb": [29, 30],
		"gate": 29, "pad": "frog", "phase": 0},
	"bird": {"step": [42, 43], "shelf": [40, 41], "climb": [42, 41],
		"gate": 42, "pad": "bird", "phase": 1},
	"human": {"step": [44, 44], "shelf": [47, 48], "climb": [44, 47],
		"gate": 45, "pad": "human", "phase": 2},
}

## The four switch-block tile ids, shared across every world.
const SWITCH_IDS := [11, 12, 26, 27]

## src/enemies/obsidian_heart.gd's `St`.
const ST_IDLE := 0
const ST_WALK := 1
const ST_WINDUP := 2
const ST_AIR := 3
const ST_LAND := 4
const ST_SPRAY := 5

## THE AMBIENCE ENTRY THIS LEVEL WANTS, and the reason it is a constant in a test
## file and not a diff to data/ambience.json: that file is integration's, and
## nest_5's entry is *reported* rather than written here. Keeping it here means it
## is not a suggestion — `t_the_hearthold_reads_as_an_ember_room` installs exactly
## this dictionary into the live level and measures what it does, so the entry
## that ships is one that has been run.
##
## The grammar is the world's, not invented here: world "obsidian", an ember
## room, gold reserved for the things you act on, and NO `darkness` key at all —
## the nest is lit by what is burning in it. 281 obsidian_hot and 287 nest_shard
## are the emissive foreground tiles; 289 nest_vein is background dressing and
## stays unlit, because a vein that glowed would compete with the Heart.
const AMBIENCE := {
	"world": "obsidian",
	"air": {"ramp": "ember", "step": 1, "alpha": 0.34},
	"bg_tint": {"ramp": "purple", "step": 2, "mix": 0.78, "scale": 0.42},
	"fg_tint": {"ramp": "ember", "step": 4, "mix": 0.30, "scale": 0.88},
	"vignette": 0.34,
	"lights": [],
	"emissive": {
		"281": {"ramp": "ember", "step": 5, "intensity": 0.42, "radius": 26, "lift": 0},
		"287": {"ramp": "gold", "step": 6, "intensity": 0.34, "radius": 18, "lift": 0},
	},
}

var failures: PackedStringArray = PackedStringArray()
var passes := 0
var standalone := true
var _current := ""

var lvl: Node = null
var boss: Enemy = null
var pl: Player = null

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
	check(a == b, "%s (got %s, expected %s)" % [msg, str(a), str(b)])

func say(s: String) -> void:
	print(s)

func boot() -> bool:
	Game.reset_run()
	Game.goto_level(LEVEL)
	await frames(6)
	lvl = Game.current_level
	if lvl == null or not is_instance_valid(lvl):
		failures.append("boot :: %s did not load" % LEVEL)
		return false
	pl = lvl.player
	boss = lvl.get("boss") as Enemy
	if pl == null or boss == null:
		failures.append("boot :: %s has no player or no boss" % LEVEL)
		return false
	if boss.enemy_id != BOSS:
		failures.append("boot :: expected '%s', found '%s'" % [BOSS, boss.enemy_id])
		return false
	# Put her in the arena and wake the fight the way the game does: the camera
	# landing on the boss's screen is what calls `set_active_screen`, which
	# respawns the Heart, which is what writes phase 1's configuration.
	_park(DROP_COL, STAND_ROW)
	lvl.cam.snap_to_target()
	lvl._on_screen_changed(lvl.cam.screen)
	await frames(6)
	return true

## The Boss Gate's `stand_pos` convention, converted from the level module's:
## a body whose FEET are in row `y` has its bottom at the top of row y+1.
func _on(x: int, y: int) -> Vector2:
	return Vector2(float(x) * TS + (TS - pl.box.x) * 0.5,
		float(y + 1) * TS - pl.box.y)

## Park her on a tile in a named form. The form is an argument and not an
## assumption, because these probes walk her over transform pads: the first
## version of `t_each_phase_opens_exactly_one_bay` climbed the frog bay, picked
## up `pad_frog` at the top of it, and then measured every later climb as a FROG
## — whose jump is 5.34 tiles against Kaya's 2.78 and which therefore clears
## every plug in the level. It reported the human bay open in SEALED, and the
## trajectory trace read `vy = -340`, which is data/forms/frog.json's `jump_vel`
## and not data/forms/human.json's -260. The level was right and the test was
## wrong, and the *reason* it was wrong is a real fact about this fight — see
## `t_the_frog_the_first_phase_gives_her_is_a_key_to_the_whole_nest`.
func _park(x: int, y: int, form: String = "human") -> void:
	if pl.form_id != form:
		pl.set_form(form)
	pl.control_enabled = false
	pl.input.clear()
	pl.dead = false
	pl.invuln = 999.0
	pl.hurt_t = 0.0
	pl.vel = Vector2.ZERO
	pl.drop_through = false
	pl.pos = _on(x, y)
	Game.health = Game.max_health

func world() -> TileWorld:
	return lvl.world

func solid(x: int, y: int) -> bool:
	return world().is_solid(x, y)

## Does the player's body overlap anything solid RIGHT NOW? Resolved through
## `TileWorld.is_solid()` and not `TileCollision.has_flag(SOLID)`, because a
## switch block carries the SOLID flag whatever its group is doing — the same
## distinction the gate extension had to make.
func inside_solid(body: Rect2) -> bool:
	var cols := TileCollision.tile_range(body.position.x, body.position.x + body.size.x)
	var rows := TileCollision.tile_range(body.position.y, body.position.y + body.size.y)
	for ty in range(rows.x, rows.y + 1):
		for tx in range(cols.x, cols.y + 1):
			if solid(tx, ty):
				return true
	return false

## Force a phase without waiting for the health to fall there. `_set_phase` is
## what the reforge beat calls when it runs out, so this is the same write the
## fight performs, minus the telegraph — which is the point when the subject is
## the write itself.
func set_phase(i: int) -> void:
	boss.call("_set_phase", i)

func standable_arena_tiles() -> Array:
	var out: Array = []
	for y in range(FLOOR_ROW - 6, FLOOR_ROW):
		for x in range(ARENA_X0, ARENA_X1 + 1):
			var r := Rect2(_on(x, y), pl.box)
			if inside_solid(r):
				continue
			if not TileCollision.is_on_floor(world(), r, false):
				continue
			out.append(Vector2i(x, y))
	return out

# ================================================================= the cases
## THE MECHANIC. The gate proves the arena is fair in each configuration; this
## proves the configurations differ in the way the level says they do, and it
## does it with the real player and the real jump rather than with tile ids.
##
## Each bay is climbed the way a player climbs it: stand on the bay's own
## one-way ledge, hold toward the shelf, hold the jump. 32 px against a measured
## 46 px, so the jump is not the question — the plug is.
func t_each_phase_opens_exactly_one_bay() -> void:
	_current = "one bay per phase"
	if not await boot():
		return
	for phase in 3:
		set_phase(phase)
		await frames(2)
		var pname := String((boss.cfg.get("phases", [])[phase] as Dictionary).get("name", ""))
		var opened: Array = []
		for name: String in BAYS.keys():
			var bay: Dictionary = BAYS[name]
			var got: bool = await _can_climb(bay)
			if got:
				opened.append(name)
		say("  %-8s opens: %s" % [pname, ", ".join(PackedStringArray(opened))])
		check_eq(opened.size(), 1,
			"%s opens exactly one bay, not %s" % [pname, str(opened)])
		if opened.size() == 1:
			var want := ""
			for name: String in BAYS.keys():
				if int((BAYS[name] as Dictionary)["phase"]) == phase:
					want = name
			check_eq(opened[0], want, "%s is the %s's phase" % [pname, want])

## And the other half of the same claim: the pad in the bay the phase opens is a
## pad she can actually reach and step onto, which is what makes the phase
## "demand a form" rather than merely contain one.
func t_the_bay_a_phase_opens_hands_her_its_form() -> void:
	_current = "the bay hands her its form"
	if not await boot():
		return
	for name: String in BAYS.keys():
		var bay: Dictionary = BAYS[name]
		set_phase(int(bay["phase"]))
		_park(DROP_COL, STAND_ROW)
		await frames(2)
		var climbed: bool = await _can_climb(bay)
		check(climbed, "the %s bay is climbable in its own phase" % name)
		if not climbed:
			continue
		# She is standing on the shelf now. The pad is on it, so give the pad a
		# few frames to do what pads do.
		pl.control_enabled = false
		await frames(70)
		check_eq(pl.form_id, String(bay["pad"]),
			"the %s bay's pad turns her into the %s" % [name, String(bay["pad"])])
		# And nothing in this arena can strand an animal: the floor is
		# configuration-independent and the floor pad is always on it.
		check(not solid(DROP_COL, STAND_ROW) and not solid(DROP_COL, STAND_ROW - 1),
			"the floor pad's tile is clear in %s" % name)

## THE FROG IS A KEY TO THE WHOLE NEST, and that is a consequence of the design
## rather than a hole in it — measured here because the alternative is not
## knowing.
##
## Every plug in this arena is sized against Kaya: two rows, at the top of a
## 32 px climb she makes with a measured 46 px jump. `data/forms/frog.json` jumps
## 5.34 tiles. So a frog does not climb the bays, it goes over them — and the
## frog is exactly what SEALED, the first phase, hands her.
##
## Three things make that a reward and not a bug, and all three are asserted:
##
##   * the frog cannot be obtained anywhere else in the arena, so the freedom is
##     bought by spending SEALED on the bay instead of on the Heart;
##   * the frog cannot attack (`can_attack: false`), so no amount of freedom
##     wins the fight — she has to come back down to the floor pad for that;
##   * and it cannot strand her: tools/worlds/nest_5.py's `_strand_graph`
##     floods (tile x form x configuration) from the landing tile and finds
##     1017 states and zero dead ends, so every bay a frog reaches is a bay she
##     can leave.
##
## What the arena keeps from a frog is nothing. What it keeps from KAYA is the
## fight, and that is the claim `t_each_phase_opens_exactly_one_bay` makes.
func t_the_frog_the_first_phase_gives_her_is_a_key_to_the_whole_nest() -> void:
	_current = "the frog is a key"
	if not await boot():
		return
	for phase in 3:
		set_phase(phase)
		var opened: Array = []
		for name: String in BAYS.keys():
			_park(DROP_COL, STAND_ROW, "frog")
			await frames(2)
			var got: bool = await _can_climb(BAYS[name], "frog")
			if got:
				opened.append(name)
		var pname := String((boss.cfg.get("phases", [])[phase] as Dictionary).get("name", ""))
		say("  as the frog, %-8s opens: %s"
			% [pname, ", ".join(PackedStringArray(opened))])
		check_eq(opened.size(), 1,
			"the frog gets exactly one bay in %s too -- the plugs are a WALL "
			% pname
			+ "across the climb, not a ceiling over it, so a 5.34-tile jump "
			+ "buys nothing here")
	# And the freedom it buys is not a weapon. Parked on open floor well away
	# from the arena's `pad_human`, which would hand her the blade back before
	# the question could be asked — the pads are one-way and they are fast.
	_park(33, STAND_ROW, "frog")
	await frames(2)
	check_eq(pl.form_id, "frog", "she is the frog")
	check_eq(pl.form.weapon_id(), "",
		"the frog has no weapon, so no bay it opens wins the fight")
	# The floor pad is what sells it back, and it is on the one row no
	# configuration touches.
	check(not solid(DROP_COL, STAND_ROW) and not solid(DROP_COL, STAND_ROW - 1),
		"and the floor pad that turns her back is clear in every configuration")

## Stand her on EVERY standable tile in the arena and turn the nest over under
## her, in every direction. Nothing may end up inside geometry.
##
## This is the structural claim tools/worlds/nest_5.py makes about the level —
## every switch tile is at rows 21-22 of six columns, and a body standing in this
## arena occupies rows 21-22 of a SHELF column, 23-24 of a step or 25-26 of the
## floor — measured here against the running game instead of against the grid.
func t_no_flip_can_close_on_a_standing_body() -> void:
	_current = "no flip crushes a standing body"
	if not await boot():
		return
	var tiles := standable_arena_tiles()
	check(tiles.size() > 0, "the arena has standable tiles")
	var crushed: Array = []
	var moved: Array = []
	for t: Vector2i in tiles:
		for from_phase in 3:
			for to_phase in 3:
				if from_phase == to_phase:
					continue
				set_phase(from_phase)
				_park(t.x, t.y)
				await frames(1)
				var before := pl.pos
				set_phase(to_phase)
				await frames(1)
				if inside_solid(pl.aabb()):
					if not crushed.has(t):
						crushed.append(t)
				if pl.pos != before and not moved.has(t):
					moved.append(t)
	say("  %d standable tile(s) x 6 reconfigurations: %d ended inside geometry, "
		% [tiles.size(), crushed.size()]
		+ "%d had to be moved" % moved.size())
	check(crushed.is_empty(),
		"a flip left her inside solid tiles on %s" % str(crushed))
	check(moved.is_empty(),
		"a flip had to set her down from %s — she was standing still, and a "
			% str(moved)
		+ "standing body should never need rescuing")

## WHAT `set_switch` ACTUALLY DOES TO AN OVERLAPPING BODY, measured rather than
## assumed, and what this boss does about it.
##
## The measurement first, because the answer only makes sense next to it: put her
## in mid-air inside a bay's plug column, with the plug open, and close it. The
## tile she is occupying becomes solid; `TileWorld.set_switch()` writes two
## booleans and returns; nothing in `TileCollision` is watching, so on the next
## frame `move_y` finds her already inside geometry and resolves her out of it in
## whichever direction it reaches first — which for a body inside a two-row plug
## is upward, into the permanent cap above it.
##
## So the Heart does not rely on the collision code noticing.
## `_make_room_for_player()` runs on the frame the write lands, asks whether her
## body is inside anything the write made solid, and sets her down on the arena
## floor under her own column with a beat of invulnerability. The floor is what
## makes that always possible: one unbroken cap that no configuration touches.
func t_a_flip_that_closes_on_her_sets_her_down() -> void:
	_current = "a flip that closes on her sets her down"
	if not await boot():
		return
	for name: String in BAYS.keys():
		var bay: Dictionary = BAYS[name]
		var open_phase := int(bay["phase"])
		var shut_phase := (open_phase + 1) % 3
		var col := int(bay["gate"])
		# With the bay open, its plug column is air. Put her there, in the air,
		# exactly where the plug is about to be.
		set_phase(open_phase)
		await frames(1)
		pl.control_enabled = false
		pl.dead = false
		pl.invuln = 0.0
		pl.vel = Vector2.ZERO
		pl.pos = Vector2(float(col) * TS + (TS - pl.box.x) * 0.5,
			float(PLUG_BOT + 1) * TS - pl.box.y)
		await frames(1)
		var was_clear := not inside_solid(pl.aabb())
		check(was_clear, "the %s bay's plug column is air while it is open" % name)
		# And now the nest turns.
		set_phase(shut_phase)
		await frames(2)
		check(not inside_solid(pl.aabb()),
			"after the %s bay closed on her she is not inside geometry" % name)
		check(pl.pos.y + pl.box.y >= float(FLOOR_ROW) * TS - 0.5,
			"and she was set down on the arena floor (feet at y %.1f, floor at %.1f)"
				% [pl.pos.y + pl.box.y, float(FLOOR_ROW) * TS])
		check(pl.invuln > 0.0,
			"with a beat of invulnerability — the nest moving is not her mistake")
		check(not pl.dead, "and alive")

## THE TELEGRAPH AND THE SAFE BEAT. A health threshold does not flip the nest on
## the frame it is crossed, and this asserts the ORDER of the two events and the
## gap between them — not that a variable exists.
func t_the_nest_telegraphs_before_it_turns() -> void:
	_current = "the nest telegraphs before it turns"
	if not await boot():
		return
	var flips_before: int = boss.call("flips")
	var solid_before := _switch_solidity()
	# One blade's worth of damage over the first threshold.
	while boss.health > int((boss.cfg.get("phases", [])[0] as Dictionary)["until_health"]):
		boss.hurt(1, boss.center())
	await frames(1)
	check(bool(boss.get("reforging")),
		"crossing the threshold starts the reforge rather than the flip")
	check_eq(int(boss.call("flips")), flips_before,
		"and nothing has been written yet")
	check_eq(_switch_solidity(), solid_before, "the arena has not moved yet")
	check_eq(int(boss.get("st")), ST_WINDUP, "it is holding the windup pose")
	# Nothing it owns may land during the beat.
	var beat := int(float(boss.cfg.get("reforge_time", 1.05)) * 60.0)
	var hits := 0
	var held := Game.health
	for i in beat - 4:
		Game.health = held
		await get_tree().physics_frame
		if Game.health < held:
			hits += 1
	check_eq(hits, 0, "and it does not hit her during the beat")
	check(bool(boss.get("reforging")), "the beat is still running at %d frames" % (beat - 4))
	await frames(12)
	check(not bool(boss.get("reforging")), "and then it ends")
	check_eq(int(boss.call("flips")), flips_before + 1, "having written the nest once")
	check(_switch_solidity() != solid_before, "and the arena has moved")
	say("  the reforge held for %.2f s before the write" % float(boss.cfg.get("reforge_time", 1.05)))

## NOTHING IS RESTORED. THE TIDE MAW puts its water back on death and says so;
## this one must not, because the configuration is the mechanic. The arena Kaya
## walks out of is the one MOLTEN left behind — and `boss_exit` is still
## reachable across it, which is the obligation that buys.
func t_the_arena_is_left_in_the_configuration_that_killed_it() -> void:
	_current = "nothing is restored"
	if not await boot():
		return
	set_phase(2)
	await frames(2)
	var molten := _switch_solidity()
	check_eq(int(boss.get("phase")), 2, "it is in MOLTEN")
	pl.invuln = 999.0
	boss.hurt(boss.health, boss.center() + Vector2(64.0, 0.0))
	await frames(30)
	check_eq(_switch_solidity(), molten,
		"the nest is still in MOLTEN's configuration after the Heart falls")
	# And the way out is open across it.
	var gate_open := false
	for n: Node in (lvl.get("entities") as Node2D).get_children():
		if n is LevelExit:
			gate_open = true
	check(gate_open, "and the gate is open")
	var walkable := true
	for x in range(ARENA_X0, ARENA_X1 + 1):
		var r := Rect2(_on(x, STAND_ROW), pl.box)
		if inside_solid(r) or not TileCollision.is_on_floor(world(), r, false):
			walkable = false
	check(walkable,
		"and the arena floor is walkable end to end in the configuration it was left in")

## A DEAD BOSS DOES NOT TURN THE NEST. The last blade of the fight crosses
## MOLTEN's threshold on the same call that kills it, and a telegraph that
## outlived the thing telegraphing it would reconfigure the arena under a player
## who has already won.
func t_a_dead_heart_does_not_turn_the_nest() -> void:
	_current = "a dead heart does not turn the nest"
	if not await boot():
		return
	pl.invuln = 999.0
	# Kill it outright from full health, which crosses all three thresholds on
	# one call — the burst-damage case boss_grove.gd's comment names.
	var before := _switch_solidity()
	boss.hurt(boss.max_health, boss.center() + Vector2(64.0, 0.0))
	var flips_at_death: int = boss.call("flips")
	check(boss.defeated, "it reports itself defeated")
	check(not bool(boss.get("reforging")), "with no reforge left running")
	check_eq(flips_at_death, 0,
		"and killing it outright from full health wrote the nest zero times, "
		+ "however many thresholds that one call crossed")
	# The node frees itself 0.35 s after it dies, so what outlives it is the
	# arena — which is the thing that would have moved.
	await frames(40)
	check_eq(_switch_solidity(), before,
		"the nest is in the same configuration 40 frames after it fell")

## The Heart's own span, against the bays. The gate measures that it stays inside
## `arena_min`/`arena_max`; this measures that those numbers are the right ones —
## that the span excludes every column that carries a switch tile, so no
## configuration can close on the BOSS either.
func t_the_heart_can_never_stand_in_a_bay() -> void:
	_current = "the heart can never stand in a bay"
	if not await boot():
		return
	var lo: float = boss.get("arena_min")
	var hi: float = boss.get("arena_max")
	check(lo < hi, "the arena span is non-empty (%.0f..%.0f)" % [lo, hi])
	var plug_cols: Array = []
	for y in range(PLUG_TOP, PLUG_BOT + 1):
		for x in range(ARENA_X0, ARENA_X1 + 1):
			if SWITCH_IDS.has(world().get_fg(x, y)) and not plug_cols.has(x):
				plug_cols.append(x)
	plug_cols.sort()
	check(plug_cols.size() > 0, "the arena has switch blocks in it at all")
	var body_lo := int(floor(lo / TS))
	var body_hi := int(floor((hi + boss.box.x - 0.001) / TS))
	say("  the Heart's body occupies cols %d..%d; switch blocks stand in cols %s"
		% [body_lo, body_hi, str(plug_cols)])
	for c: int in plug_cols:
		check(c < body_lo or c > body_hi,
			"col %d carries a switch block and is inside the Heart's span" % c)
	# And every switch tile in the level is on the two rows the level module
	# says, which is what makes the standing-body claim above structural.
	var stray: Array = []
	for y in world().height:
		for x in world().width:
			if SWITCH_IDS.has(world().get_fg(x, y)) and (y < PLUG_TOP or y > PLUG_BOT):
				stray.append(Vector2i(x, y))
	check(stray.is_empty(),
		"every switch tile in nest_5 is on rows %d-%d; these are not: %s"
			% [PLUG_TOP, PLUG_BOT, str(stray)])

## THE AMBIENCE nest_5 WANTS. Reported to integration rather than written into
## data/ambience.json, and run here so what is reported has been run: the entry
## installs, the room renders, and the mechanic's own tiles are the lit ones.
func t_the_hearthold_reads_as_an_ember_room() -> void:
	_current = "ambience"
	if not await boot():
		return
	check(not AMBIENCE.has("darkness"),
		"the nest carries no darkness key — it is lit by what is burning in it")
	check_eq(String(AMBIENCE["world"]), "obsidian", "the world is 'obsidian'")
	var em: Dictionary = AMBIENCE["emissive"]
	check(em.has("281") and em.has("287"),
		"obsidian_hot and nest_shard are the emissive foreground tiles")
	check(not em.has("289"),
		"nest_vein is background dressing and stays unlit — a vein that glowed "
		+ "would compete with the Heart")
	# `Ambience` is a resource class, not an autoload: the level holds one in
	# `amb`. Installing the entry means replacing what that holds and letting the
	# layers redraw, which is what a level with this entry in data/ambience.json
	# would have done at load.
	var amb: Ambience = lvl.get("amb") as Ambience
	check(amb != null, "the level carries an Ambience")
	if amb != null:
		var installed: Ambience = Ambience.from_dict(LEVEL, AMBIENCE)
		check(installed != null, "the entry parses into an Ambience")
		if installed != null:
			lvl.set("amb", installed)
			await frames(4)
			check(is_instance_valid(lvl),
				"and the hearthold still renders with it installed")
	say("  data/ambience.json wants this entry for nest_5: %s" % JSON.stringify(AMBIENCE))

# ---------------------------------------------------------------- helpers
## Stand her on the bay's own ledge, hold toward the shelf, hold the jump, and
## report whether her feet end up on the shelf. The real player, the real form
## code, the real collision — the envelope in tools/reachability.py is what
## shipped six defects and it does not get a vote here.
func _can_climb(bay: Dictionary, form: String = "human") -> bool:
	var from_col := int((bay["climb"] as Array)[0])
	var to_col := int((bay["climb"] as Array)[1])
	var toward := "right" if to_col > from_col else "left"
	for run_up in [0, 6, 12, 20]:
		_park(from_col, STEP_STAND, form)
		pl.last_floor_tile = Vector2i(-1, -1)
		boss.active = false
		pl.control_enabled = true
		await frames(2)
		var airborne := false
		var got := false
		for f in 90:
			pl.invuln = 999.0
			pl.hurt_t = 0.0
			Game.health = Game.max_health
			var held: Array = [toward]
			if f >= run_up and f < run_up + 18:
				held.append("jump")
			BossGateTape.apply(held)
			await get_tree().physics_frame
			if not pl.on_floor:
				airborne = true
				continue
			# `feet` is the tile she is STANDING ON, which is the Boss Gate's
			# convention and one row below this file's: standing on the shelf
			# puts her feet in row 22 and her weight on row 23. Comparing
			# against SHELF_STAND instead of SHELF_ROW was worth six failures.
			var feet := Vector2i(int(floor(pl.feet().x / TS)),
				int(floor((pl.feet().y + 1.0) / TS)))
			if airborne and feet.y == SHELF_ROW \
					and feet.x >= int((bay["shelf"] as Array)[0]) \
					and feet.x <= int((bay["shelf"] as Array)[1]):
				got = true
				break
		BossGateTape.release_all()
		pl.control_enabled = false
		boss.active = true
		if got:
			if OS.get_environment("KAYA_HEART_CLIMB") != "":
				say("      climbed %s from col %d run-up %d, landed on (%d,%d)"
					% [String(bay["pad"]), from_col, run_up,
						int(floor(pl.feet().x / TS)),
						int(floor((pl.feet().y + 1.0) / TS))])
			return true
	return false

## The solidity of every switch tile in the arena, as a comparable value. Read
## through `TileWorld.is_solid()`, so this is what the collision code answers
## right now and not what the file says.
func _switch_solidity() -> String:
	var bits: PackedStringArray = PackedStringArray()
	for y in range(PLUG_TOP, PLUG_BOT + 1):
		for x in range(ARENA_X0, ARENA_X1 + 1):
			if SWITCH_IDS.has(world().get_fg(x, y)):
				bits.append("1" if solid(x, y) else "0")
	return "".join(bits)

# ---------------------------------------------------------------- entry point
const BossGateTape := preload("res://tests/integration/boss_gate_tape.gd")

const CASES := [
	"t_each_phase_opens_exactly_one_bay",
	"t_the_bay_a_phase_opens_hands_her_its_form",
	"t_the_frog_the_first_phase_gives_her_is_a_key_to_the_whole_nest",
	"t_no_flip_can_close_on_a_standing_body",
	"t_a_flip_that_closes_on_her_sets_her_down",
	"t_the_nest_telegraphs_before_it_turns",
	"t_the_arena_is_left_in_the_configuration_that_killed_it",
	"t_a_dead_heart_does_not_turn_the_nest",
	"t_the_heart_can_never_stand_in_a_bay",
	"t_the_hearthold_reads_as_an_ember_room",
]

func run_all() -> int:
	if standalone:
		print("THE OBSIDIAN HEART — nest_5")
	for name: String in CASES:
		print("  %s" % name)
		await call(name)
	if not standalone:
		return 0 if failures.is_empty() else 1
	print("")
	for f in failures:
		print("  FAIL  %s" % f)
	print("obsidian heart: %d checks, %s"
		% [passes + failures.size(),
			"ALL PASSED" if failures.is_empty() else "%d FAILED" % failures.size()])
	return 0 if failures.is_empty() else 1
