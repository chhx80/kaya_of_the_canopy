extends Node
## In-game suite for THE BROOD QUEEN's two new mechanisms: being invisible, and
## the luminous walls the player spends to stop her being invisible.
##
## `tools/bossgate.sh --level=deeps_5 --boss=brood_queen` already answers the five
## questions of ADR 005 section 4 — defeatable, survivable, fair, arena-bound, and
## it ends. This file does not restate any of them. It exists for the things the
## gate structurally cannot see, and there are four:
##
##   * **The gate is blind to blindness.** Its fairness sweep pins Kaya on a tile
##     and watches the game's own collision; rendering is not in that loop at all,
##     which is correct and is also why a boss drawn at zero alpha would sail
##     through every one of its checks. So the visibility mechanic is asserted
##     directly, from both ends: she is fully drawn on every frame she can hurt
##     you deliberately, and she is NOT fully drawn the rest of the time — because
##     a mechanic that never engages is the other way to pass a test about it.
##
##   * **The gate sweeps ONE arena: the one on disk, with both walls standing.**
##     It collects the standable tiles once and never breaks anything. But these
##     walls are breakable and the player decides, so there are four arenas —
##     none, west, east, both — and the gate has measured one of them. The
##     all-broken case is the one that matters, because that is the arena with the
##     least cover in it, and `t_with_every_luminous_wall_broken_it_is_still_fair`
##     is this suite's answer to "what if the player spends everything".
##
##   * **Fairness in the dark is not fairness in the sweep.** The sweep's dodge is
##     mechanical: it asks whether an attack reaches a tile, not whether a player
##     could have known to leave it. This file adds its own bar instead — every
##     telegraph that matters emits something a dark screen cannot dim — and
##     measures it as a worst case rather than asserting it as a principle. The
##     reasoning is written out over `t_she_is_never_both_dark_and_silent`.
##
##   * **A boss that edits the level.** The Maw and the Stormcrest both do and
##     both restore it. This one does not edit it at all, and the walls Kaya
##     breaks are hers and stay broken — including across a death and a respawn,
##     which is the one road by which a "permanent" choice quietly un-happens.
##
## Everything here is asserted on the outcome, never on the mechanism.
##
## Part of tools/itest.sh once integration folds it in, which is three lines in
## tests/integration/integration_tests.gd and nothing else — the existing
## `_fold_in` pattern, exactly as t_boss_stormcrest:
##
##     "t_boss_brood_queen",                             # in the `tests` array
##
##     func t_boss_brood_queen() -> void:
##         await _fold_in("res://tests/integration/boss_brood_queen_tests.gd")
##
## `standalone = false` is what stops it printing its own report.
##
## Still runnable on its own — this file owns its whole harness:
##   $GODOT --headless --fixed-fps 60 --path . \
##       res://tests/integration/boss_brood_queen_runner.tscn
## or, in the suite: ITEST_TIMEOUT=900 tools/itest.sh --only=t_boss_brood_queen

const LEVEL := "deeps_5"
const BOSS := "brood_queen"
const TS := 16.0

## Geometry of deeps_5's royal cell, named so a level edit breaks a name and not
## a number. These are the values tools/worlds/deeps_5.py draws from.
const ARENA_SCREEN := Vector2i(1, 1)
const FLOOR_ROW := 27
const STAND_ROW := 26          ## the row a body's FEET are in, on the floor
const SHELF_ROW := 25
const SHELF_STAND := 24        ## and on a one-way shelf
const SHELF_COL := 36          ## inside the west/east shelf run (35-38)
const COMB_COL := 30           ## under the west comb (29-31)
const OPEN_COL := 33           ## open floor, where the brood shaft lands her
const CELL_A_COL := 45         ## the brood cell behind luminous wall A
const CELL_B_COL := 48         ## and behind wall B
const GLOW_A := 43             ## wall A occupies cols 43-44, rows 25-26
const GLOW_B := 46             ## wall B occupies cols 46-47, rows 25-26
const GLOW_TILE := 214         ## shared `luminous_wall`

## src/enemies/brood_queen.gd's `St`.
const ST_IDLE := 0
const ST_WALK := 1
const ST_WINDUP := 2
const ST_AIR := 3
const ST_LAND := 4
const ST_SPRAY := 5

## THE AMBIENCE ENTRY THIS LEVEL WANTS, and the reason it is a constant in a test
## file and not a diff to data/ambience.json: five agents are adding entries to
## that one file for World 4 at the same time, so deeps_5's is *reported* to
## integration rather than written here. Keeping it here means it is not a
## suggestion — `t_the_light_dies_with_the_wall` installs exactly this dictionary
## into the live level and measures what it does, so the entry that ships is one
## that has been run.
##
## The numbers are the world's, not invented here: darkness 0.88 and vignette 0.40
## are the foundation agent's measured pair for a 74 px lantern, and the emissive
## recipe for tile 214 (gold 6, intensity 0.40, radius 30, lift 0) is the measured
## one for a luminous wall.
const AMBIENCE := {
	"world": "deeps",
	"air": {"ramp": "water", "step": 1, "alpha": 0.45},
	"bg_tint": {"ramp": "purple", "step": 3, "mix": 0.80, "scale": 0.44},
	"fg_tint": {"ramp": "dirt", "step": 5, "mix": 0.40, "scale": 0.84},
	"vignette": 0.40,
	"darkness": 0.88,
	"lights": [],
	"emissive": {
		"214": {"ramp": "gold", "step": 6, "intensity": 0.40, "radius": 30, "lift": 0},
	},
}

var failures: PackedStringArray = PackedStringArray()
var passes := 0
var standalone := true
var _current := ""

var lvl: Node = null
var boss: Enemy = null
var pl: Player = null
var authored: Array = []       ## the fg rows straight out of levels/deeps_5.json

# ---------------------------------------------------------------- harness
func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame

func check(cond: bool, msg: String) -> void:
	if cond:
		passes += 1
	else:
		failures.append("%s :: %s" % [_current, msg])

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
	Game.sim_paused = false
	return true

## The level as it is on disk: the only honest reference for "unbroken".
func load_authored() -> bool:
	var f := FileAccess.open("res://levels/%s.json" % LEVEL, FileAccess.READ)
	if f == null:
		failures.append("boot :: cannot read levels/%s.json" % LEVEL)
		return false
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		failures.append("boot :: levels/%s.json is not an object" % LEVEL)
		return false
	var d: Dictionary = parsed
	var legend := LevelLoader.legend_for(String(d.get("tileset", "jungle")))
	var rows: Array = []
	for raw: Variant in (d.get("fg", []) as Array):
		var row: PackedInt32Array = PackedInt32Array()
		for i in String(raw).length():
			row.append(int(legend.get(String(raw)[i], 0)))
		rows.append(row)
	authored = rows
	return not authored.is_empty()

func authored_at(x: int, y: int) -> int:
	if y < 0 or y >= authored.size():
		return -1
	var row: PackedInt32Array = authored[y]
	return row[x] if x >= 0 and x < row.size() else -1

func set_phase(i: int) -> void:
	boss.call("_set_phase", i)

func stand_pos(tile: Vector2i) -> Vector2:
	return Vector2(float(tile.x) * TS + (TS - pl.box.x) * 0.5, float(tile.y) * TS - pl.box.y)

## `tile` here is the tile the body's FEET are in, the way the level's marks and
## the prover name a place — not the tile it is standing ON.
func park(tile: Vector2i) -> void:
	pl.control_enabled = false
	pl.input.clear()
	pl.dead = false
	pl.invuln = 999.0
	pl.hurt_t = 0.0
	pl.vel = Vector2.ZERO
	pl.drop_through = false
	pl.pos = stand_pos(tile + Vector2i(0, 1))
	Game.health = Game.max_health

## Put Kaya in the royal cell and wake the fight up. Everything in this suite
## needs this and the first cut of it needed it invisibly: `Enemy.set_active_screen`
## leaves a boss frozen until the camera lands on its screen, and deeps_5 spawns
## Kaya four screens away — so a case that parked her nowhere measured a Queen
## whose `think()` had never run, whose alpha was whatever `_ready` left and who
## had never once looked at her own walls. Every check in it passed for the wrong
## reason, which is the failure mode this whole project is built to refuse.
func enter_arena(feet: Vector2i) -> void:
	park(feet)
	lvl.cam.snap_to_target()
	await frames(4)
	park(feet)
	boss.active = true
	await frames(2)

## Every tile in the arena screen a body can stand on, found with the real
## collision code — the same question boss_gate_checks.gd asks.
func standable_set() -> Dictionary:
	var out: Dictionary = {}
	var o := Screen.origin(ARENA_SCREEN)
	var t0 := Vector2i(int(o.x / TS), int(o.y / TS))
	var b := pl.box
	for ty in range(t0.y, t0.y + int(Screen.H / TS)):
		for tx in range(t0.x, t0.x + int(Screen.W / TS)):
			var r := Rect2(Vector2(float(tx) * TS + (TS - b.x) * 0.5, float(ty) * TS - b.y), b)
			if TileCollision.has_flag(lvl.world, r, TileData4.Flag.SOLID):
				continue
			if not TileCollision.is_on_floor(lvl.world, r, false):
				continue
			if TileCollision.has_flag(lvl.world, r, TileData4.Flag.HAZARD):
				continue
			out[Vector2i(tx, ty)] = true
	return out

## Break a whole luminous wall the way the blade does — `TileWorld.break_tile`
## plus the level's own redraw hook — rather than by writing a 0 into the grid.
func smash(col: int) -> int:
	var n := 0
	for x in [col, col + 1]:
		for y in [SHELF_ROW, STAND_ROW]:
			if lvl.world.get_fg(x, y) == GLOW_TILE and lvl.world.break_tile(x, y):
				n += 1
				lvl.on_tile_broken(Vector2i(x, y))
	return n

## Run the fight for `n` frames with Kaya parked and immortal, and report what the
## Queen's damage sources did. Every hostile shot is classified by the direction
## it is travelling — down is the spore fall, sideways is the floor wave — and
## "connected" is the game's own rectangles overlapping, measured from outside.
func watch(phase: int, feet: Vector2i, n: int) -> Dictionary:
	boss.respawn()
	set_phase(phase)
	boss.active = true
	park(feet)
	lvl.cam.snap_to_target()
	await frames(2)
	var r := {"wave": 0, "spore": 0, "wave_hit": 0, "spore_hit": 0,
		"wave_east": 0.0, "worst_gap": 0, "body_unseen": 0,
		"lit": 0, "dim": 0, "attack_lit": 0, "attack_frames": 0}
	var seen: Dictionary = {}
	## Frames since the player last had ANY information about where she is: she
	## was drawn, or she put something on the floor. Counting "frames since a cue"
	## alone measures the wrong thing — she emits nothing at all through the whole
	## of the slam recovery, and the slam recovery is a state she is fully drawn
	## in, so the player has been staring at her for half a second.
	var blind := 0
	for f in n:
		park(feet)
		await get_tree().physics_frame
		var a: float = float(boss.get("alpha"))
		var attacking: bool = bool(boss.call("attacking"))
		if attacking:
			r["attack_frames"] = int(r["attack_frames"]) + 1
			if a >= 0.999:
				r["attack_lit"] = int(r["attack_lit"]) + 1
		if a >= 0.999:
			r["lit"] = int(r["lit"]) + 1
		else:
			r["dim"] = int(r["dim"]) + 1
		if a >= 0.999 or int(boss.get("frames_since_cue")) == 0:
			blind = 0
		else:
			blind += 1
			r["worst_gap"] = maxi(int(r["worst_gap"]), blind)
			# A frame on which her body could take a heart off you and neither her
			# sprite nor the floor had said where she was for a third of a second.
			if boss.aabb().intersects(pl.aabb()) and blind > 20:
				r["body_unseen"] = int(r["body_unseen"]) + 1
		for node in get_tree().get_nodes_in_group(&"hostile_shots"):
			var s := node as Projectile
			if s == null or not is_instance_valid(s):
				continue
			var kind := "spore" if s.vel.y > 40.0 and absf(s.vel.x) < 8.0 else "wave"
			var id := s.get_instance_id()
			if not seen.has(id):
				seen[id] = true
				r[kind] = int(r[kind]) + 1
			if kind == "wave":
				r["wave_east"] = maxf(float(r["wave_east"]), s.aabb().end.x)
			if s.aabb().intersects(pl.aabb()):
				r[kind + "_hit"] = int(r[kind + "_hit"]) + 1
	Game.health = Game.max_health
	return r

# ---------------------------------------------------------------- the checks
## 1. The mechanic, from both ends. A Queen who is always drawn is an ordinary
## boss in a dim room; a Queen who is never drawn is a cheat. Neither would fail
## one check of the Boss Gate, because rendering is not in the gate's loop.
func t_she_is_drawn_only_while_she_attacks() -> void:
	_current = "the-dark"
	for phase in (boss.cfg.get("phases", []) as Array).size():
		var r: Dictionary = await watch(phase, Vector2i(OPEN_COL, STAND_ROW), 600)
		var pname := String((boss.cfg.get("phases", [])[phase] as Dictionary).get("name", ""))
		say("  phase %d %-6s %d frames lit, %d dim (%d of %d attack frames at full)"
			% [phase, pname, int(r["lit"]), int(r["dim"]),
				int(r["attack_lit"]), int(r["attack_frames"])])
		check(int(r["attack_frames"]) > 0,
			"phase %d (%s) never attacked at all in ten seconds, so this proves nothing"
				% [phase, pname])
		check(int(r["attack_lit"]) == int(r["attack_frames"]),
			("phase %d (%s): she was less than fully drawn on %d of the %d frames she "
			+ "was attacking. Every telegraph and every attack has to be visible or "
			+ "the dark is doing the fighting")
				% [phase, pname, int(r["attack_frames"]) - int(r["attack_lit"]),
					int(r["attack_frames"])])
		check(int(r["dim"]) > 0,
			("phase %d (%s): she was fully drawn on all %d frames, so the fight is not "
			+ "dark at all and the whole mechanic is inert")
				% [phase, pname, int(r["lit"])])

## 2. Landing a hit tells you where she is. The damage flash beats the darkness,
## which is the right way round: the one thing you did on purpose should be the
## one thing you get information for.
func t_the_blade_finding_her_is_a_reveal() -> void:
	_current = "the-reveal"
	await enter_arena(Vector2i(OPEN_COL, STAND_ROW))
	boss.respawn()
	set_phase(0)
	boss.set("st", ST_WALK)
	boss.set("t", 9.0)
	await frames(2)
	check(float(boss.get("alpha")) < 0.5,
		"a crawling Queen is drawn at %.2f; she is supposed to be nearly invisible"
			% float(boss.get("alpha")))
	boss.hurt(1, boss.center() + Vector2(48.0, 0.0))
	await frames(1)
	check(float(boss.get("alpha")) >= 0.999,
		"the blade took a point off her and she stayed at %.2f alpha — a hit that "
			% float(boss.get("alpha"))
			+ "tells you nothing is a hit you cannot follow up")

## 3. The trade, as one number. Every luminous wall the player spends lifts the
## floor her sprite fades to, and spending both ends the mechanic for good.
func t_breaking_a_luminous_wall_lifts_her_out_of_the_dark() -> void:
	_current = "the-trade"
	var ok: bool = await boot()
	if not ok:
		return
	await enter_arena(Vector2i(OPEN_COL, STAND_ROW))
	boss.respawn()
	set_phase(0)
	boss.set("st", ST_WALK)
	boss.set("t", 9.0)
	await frames(2)
	check(int(boss.call("walls_total")) == 8,
		"the Queen found %d luminous wall tiles in her arena; deeps_5 draws two "
			% int(boss.call("walls_total")) + "walls of two-by-two")
	var dark := float(boss.get("alpha"))
	check(int(boss.call("walls_broken")) == 0, "the fight did not start with both walls up")

	check(smash(GLOW_A) == 4, "breaking luminous wall A did not take four tiles")
	await frames(2)
	var half := float(boss.get("alpha"))
	check(int(boss.call("walls_broken")) == 4,
		"she counted %d broken tiles after wall A fell, not 4" % int(boss.call("walls_broken")))
	check(half > dark + 0.05,
		"spending wall A moved her from %.2f to %.2f alpha — the light has to buy "
			% [dark, half] + "something or the cover was given away for nothing")

	check(smash(GLOW_B) == 4, "breaking luminous wall B did not take four tiles")
	await frames(2)
	var full := float(boss.get("alpha"))
	say("  crawling alpha: %.2f dark, %.2f one wall spent, %.2f both" % [dark, half, full])
	check(full >= 0.999,
		"with every luminous wall in the chamber broken she still crawls at %.2f — "
			% full + "the last wall has to end the darkness or the trade has no floor")
	check(not bool(boss.call("attacking")),
		"she was attacking during the measurement, so the alphas above mean nothing")

## 4. The light dies with the wall. `AmbienceLayer` recollects emissive tiles only
## when its view changes, and a boss arena locks the camera — so without
## `brood_queen.gd`'s relight the wall would shatter and its glow would go on
## being drawn over the hole. This installs the ambience entry deeps_5 is asking
## integration for and measures the pools before and after.
func t_the_light_dies_with_the_wall() -> void:
	_current = "the-light"
	var ok: bool = await boot()
	if not ok:
		return
	# The light layer only collects emissive tiles inside its own VIEW, so the
	# camera has to be looking at the royal cell before any of this means anything.
	await enter_arena(Vector2i(OPEN_COL, STAND_ROW))
	var lights: AmbienceLayer = lvl.get("lights") as AmbienceLayer
	check(lights != null, "the level has no light layer")
	if lights == null:
		return
	var amb := Ambience.from_dict(LEVEL, AMBIENCE)
	check(amb.emissive.has(GLOW_TILE),
		"the proposed ambience entry does not make tile %d emissive" % GLOW_TILE)
	check(amb.darkness > 0.5 and amb.lantern_radius > 0.0,
		"the proposed ambience entry does not actually darken the level")
	lights.setup(lights.role, amb, lvl.world)
	lvl.cam.snap_to_target()
	await frames(2)
	var before := lights.visible_pools()
	check(before > 0,
		"the luminous walls light nothing at all, so there is no trade to make")
	# Kaya is nowhere near them; the boss is what notices, on its own think().
	smash(GLOW_A)
	await frames(4)
	var mid := lights.visible_pools()
	smash(GLOW_B)
	await frames(4)
	var after := lights.visible_pools()
	say("  light pools over the walls: %d standing, %d after one fell, %d after both"
		% [before, mid, after])
	check(mid < before,
		"breaking wall A left the same %d pool(s) burning — a lamp with nothing "
			% before + "holding it up")
	check(after == 0,
		"%d pool(s) are still drawn where the walls used to be" % after)

## 5. The player's choice is permanent — including across the one road by which a
## permanent choice quietly un-happens. Walking out of the arena and back in
## respawns the boss (Level._on_screen_changed -> set_active_screen -> respawn),
## and dying and being killed both run code that the other two bosses use to put
## their arena back.
func t_the_walls_are_the_players_and_they_do_not_come_back() -> void:
	_current = "permanent"
	var ok: bool = await boot()
	if not ok:
		return
	await enter_arena(Vector2i(OPEN_COL, STAND_ROW))
	smash(GLOW_A)
	smash(GLOW_B)
	await frames(2)
	check(int(boss.call("walls_broken")) == 8, "both walls did not register as broken")
	boss.respawn()
	await frames(2)
	check(int(boss.call("walls_broken")) == 8,
		"respawning the Queen put %d wall tile(s) back — the Maw restores its flood "
			% (8 - int(boss.call("walls_broken")))
			+ "and the Stormcrest its gale because those are the BOSS's; these are Kaya's")
	set_phase(0)
	pl.invuln = 999.0
	boss.set("st", ST_LAND)
	boss.hurt(boss.health, boss.center() + Vector2(64.0, 0.0))
	await frames(2)
	check(bool(boss.get("defeated")), "the Queen did not report herself defeated")
	check(int(boss.get("phase")) == 0,
		"the killing blow moved her to phase %d — a dead boss does not walk its "
			% int(boss.get("phase")) + "phase thresholds")
	var left := 0
	for x in [GLOW_A, GLOW_A + 1, GLOW_B, GLOW_B + 1]:
		for y in [SHELF_ROW, STAND_ROW]:
			if lvl.world.get_fg(x, y) == GLOW_TILE:
				left += 1
	check(left == 0, "%d luminous wall tile(s) came back when she died" % left)

## 6. And the other half of the same claim: she writes nothing. The Maw's tide and
## the Stormcrest's gale are both the boss editing the tile grid, and both have a
## suite case pinning what they may touch. This one may touch nothing, so the
## whole arena is compared against levels/deeps_5.json after a fight in every
## phase.
func t_the_queen_never_writes_to_the_level() -> void:
	_current = "she-writes-nothing"
	var ok: bool = await boot()
	if not ok:
		return
	for phase in 3:
		boss.respawn()
		set_phase(phase)
		boss.active = true
		park(Vector2i(SHELF_COL, SHELF_STAND))
		lvl.cam.snap_to_target()
		await frames(420)
	var wrong := 0
	var first := ""
	var o := Screen.origin(ARENA_SCREEN)
	var t0 := Vector2i(int(o.x / TS), int(o.y / TS))
	for y in range(t0.y, t0.y + int(Screen.H / TS)):
		for x in range(t0.x, t0.x + int(Screen.W / TS)):
			if lvl.world.get_fg(x, y) != authored_at(x, y):
				wrong += 1
				if first == "":
					first = "(%d,%d) is %d, the file says %d" \
						% [x, y, lvl.world.get_fg(x, y), authored_at(x, y)]
	check(wrong == 0,
		"twenty-one seconds of fight changed %d tile(s) of the royal cell — %s. "
			% [wrong, first]
			+ "This boss is not allowed to edit the level; only Kaya is")

## 7. FAIRNESS IN THE DARK, and the reason it needs its own bar.
##
## The Boss Gate's sweep is mechanical: it pins Kaya on a tile, fires the attack
## at her and asks whether the rectangles met. It cannot ask whether a player
## could have KNOWN to be somewhere else, and in a chamber where the boss is drawn
## at 12 % alpha that is the whole question. So this is the bar, and it is stated
## as two facts about the fight rather than as a feeling about it:
##
##   1. **Every damage source is either an entity or a lit Queen.** The floor wave
##      and the spore fall are `Projectile`s, and src/world/level.gd inserts the
##      three ambience layers *before* `Entities` in the tree — so a projectile is
##      drawn over the shade quad and is never dimmed by one pixel, whatever the
##      level's darkness is. Case 1 above pins the other half: her body is at full
##      alpha on every frame of every attack, telegraph included.
##   2. **She is never both dark and silent.** While she is dim she is pushing a
##      ripple of earth along the floor every `crawl_cue` seconds, and during the
##      burrow windup a rumble line marching out ahead of her every
##      `rumble_interval`. Both are `Fx.burst` — the particle field, which
##      src/world/level.gd also draws after the ambience layers. So her POSITION is
##      always on screen even when her body is not.
##
## This case measures the worst gap between those floor cues across a real fight
## in every phase, and separately counts the frames on which her body was actually
## touching Kaya while she was dim AND the floor had said nothing for a third of a
## second. That second number is the one that would make the fight a coin flip,
## and it has to be zero.
func t_she_is_never_both_dark_and_silent() -> void:
	_current = "dark-but-not-silent"
	var ok: bool = await boot()
	if not ok:
		return
	var worst := 0
	var unseen := 0
	for phase in 3:
		var r: Dictionary = await watch(phase, Vector2i(OPEN_COL, STAND_ROW), 600)
		worst = maxi(worst, int(r["worst_gap"]))
		unseen += int(r["body_unseen"])
	say("  worst gap between floor cues while she was dim: %d frames (%.2f s)"
		% [worst, float(worst) / 60.0])
	check(worst <= 20,
		("she went %d frames (%.2f s) dim with nothing on the floor to say where she "
		+ "was. Particles are the one thing a dark level cannot dim, so they are the "
		+ "whole of what makes this fight readable")
			% [worst, float(worst) / 60.0])
	check(unseen == 0,
		"her body was on Kaya on %d frame(s) while she was dim and the floor had been "
			% unseen + "silent for over a third of a second — that is a heart taken "
			+ "for information the player never had")

## 8. THE ARENA THE GATE NEVER SEES. Its sweep runs against levels/deeps_5.json
## with both walls standing, because nothing in it breaks a tile. The player can
## break both, and that is the arena with the least cover in the game — so this
## makes the two dodges again with everything spent, and then proves the trade was
## real by showing the wave now goes where it could not before.
func t_with_every_luminous_wall_broken_it_is_still_fair() -> void:
	_current = "all-walls-broken"
	var ok: bool = await boot()
	if not ok:
		return
	# First, with the walls up: the wave dies on wall A and never reaches the cells.
	var intact: Dictionary = await watch(2, Vector2i(SHELF_COL, SHELF_STAND), 600)
	var wall_face := float(GLOW_A) * TS
	check(int(intact["wave"]) > 0, "no floor wave was thrown at all, so this proves nothing")
	check(float(intact["wave_east"]) <= wall_face + 8.0,
		("with the walls standing, a floor wave reached x=%.0f — past the west face of "
		+ "luminous wall A at x=%.0f. The wall is what shelters the brood cells; if the "
		+ "wave is already getting through, there was never a trade to make")
			% [float(intact["wave_east"]), wall_face])

	smash(GLOW_A)
	smash(GLOW_B)
	await frames(4)
	check(int(boss.call("walls_broken")) == 8, "the walls did not break")
	var standable := standable_set()
	check(not standable.has(Vector2i(GLOW_A, SHELF_ROW)),
		"the top of wall A is still standable after it was broken")

	# The wave's dodge, with nothing left to hide behind but the one-way shelves.
	# They are not breakable, which is why they are the floor of this argument.
	var shelf: Dictionary = await watch(2, Vector2i(SHELF_COL, SHELF_STAND), 720)
	check(int(shelf["wave"]) > 0, "no floor wave in the sample")
	check(int(shelf["wave_hit"]) == 0,
		("with every luminous wall broken, %d floor wave(s) reached a body on the "
		+ "one-way shelf. That shelf is the only wave dodge left, and it is the only "
		+ "one that cannot be spent")
			% int(shelf["wave_hit"]))
	check(standable.has(Vector2i(SHELF_COL, SHELF_ROW)),
		"the shelf is not a standable tile any more")

	# The spore fall's dodge is rock, and rock is not breakable either.
	var comb: Dictionary = await watch(2, Vector2i(COMB_COL, STAND_ROW), 720)
	check(int(comb["spore"]) > 0, "no spore fall in the sample")
	check(int(comb["spore_hit"]) == 0,
		"%d spore(s) reached a body standing under the comb, which is the only shelter "
			% int(comb["spore_hit"]) + "the spore fall has")

	# And the price. The cells behind the walls were safe from the wave; they are
	# not now, and the proof is that the wave physically gets there.
	var cell: Dictionary = await watch(2, Vector2i(CELL_A_COL, STAND_ROW), 720)
	say("  floor wave furthest east: x=%.0f with the walls up, x=%.0f with them gone "
		% [float(intact["wave_east"]), float(cell["wave_east"])]
		+ "(wall A stood at x=%.0f)" % wall_face)
	check(float(cell["wave_east"]) > wall_face + TS,
		("the walls are broken and the floor wave still stops at x=%.0f. If the cells "
		+ "stay safe after the cover is gone, the player spent a wall for nothing")
			% float(cell["wave_east"]))

## 9. The cells you shelter in are reached over the wall, not through it. A
## shelter that can only be entered by destroying it is not a shelter, and this is
## the one claim in the level that a reachability model would happily agree with
## and be wrong about — tools/reachability.py reads a breakable tile as a wall.
func t_the_brood_cells_are_entered_over_the_wall() -> void:
	_current = "over-the-wall"
	var ok: bool = await boot()
	if not ok:
		return
	await enter_arena(Vector2i(OPEN_COL, STAND_ROW))
	boss.active = false
	await frames(2)
	for from_col in [GLOW_A - 1, CELL_A_COL]:
		var target := GLOW_A if from_col < GLOW_A else GLOW_A + 1
		var got: Vector2i = await hop(Vector2i(from_col, STAND_ROW),
			"right" if from_col < GLOW_A else "left")
		check(got.y == SHELF_ROW,
			("nothing gets a body from the floor at col %d onto luminous wall A "
			+ "(landed on %s). A brood cell you can only enter by breaking the wall "
			+ "in front of it is not cover, it is a door")
				% [from_col, str(got)])
		if got.y == SHELF_ROW:
			say("  col %d -> wall top col %d (wanted %d)" % [from_col, got.x, target])
	var whole := 0
	for x in [GLOW_A, GLOW_A + 1, GLOW_B, GLOW_B + 1]:
		for y in [SHELF_ROW, STAND_ROW]:
			if lvl.world.get_fg(x, y) == GLOW_TILE:
				whole += 1
	check(whole == 8,
		"%d of the 8 luminous wall tiles survived the hops; getting in must not "
			% whole + "cost a wall")
	boss.active = true

## One jump, holding one direction, the way boss_gate_checks.gd does it — with the
## correction heights_5's suite recorded: `Actor.last_floor_tile` is written only
## on the frame a floor is RESOLVED, so it has to be cleared first and a landing
## refused until she has actually left the ground.
func hop(from: Vector2i, dir: String) -> Vector2i:
	var best := Vector2i(-1, -1)
	for run_up in [0, 6, 12]:
		park(from)
		pl.control_enabled = true
		pl.last_floor_tile = Vector2i(-1, -1)
		lvl.cam.snap_to_target()
		hold([])
		await frames(2)
		var airborne := false
		for f in 90:
			pl.invuln = 999.0
			Game.health = Game.max_health
			var held: Array = [dir]
			if f >= run_up and f < run_up + 18:
				held.append("jump")
			hold(held)
			await get_tree().physics_frame
			if not pl.on_floor:
				airborne = true
				continue
			if airborne and pl.last_floor_tile.y == SHELF_ROW:
				best = pl.last_floor_tile
				break
		hold([])
		pl.control_enabled = false
		if best.x >= 0:
			return best
	return best

# ---------------------------------------------------------------- input
const ACTIONS := {"left": &"move_left", "right": &"move_right",
	"up": &"move_up", "down": &"move_down", "jump": &"jump", "attack": &"attack"}

func hold(held: Array) -> void:
	for name: String in ACTIONS.keys():
		var a: StringName = ACTIONS[name]
		if held.has(name):
			if not Input.is_action_pressed(a):
				Input.action_press(a)
		elif Input.is_action_pressed(a):
			Input.action_release(a)

# ---------------------------------------------------------------- entry point
const CASES := [
	"t_she_is_drawn_only_while_she_attacks",
	"t_the_blade_finding_her_is_a_reveal",
	"t_breaking_a_luminous_wall_lifts_her_out_of_the_dark",
	"t_the_light_dies_with_the_wall",
	"t_the_walls_are_the_players_and_they_do_not_come_back",
	"t_the_queen_never_writes_to_the_level",
	"t_she_is_never_both_dark_and_silent",
	"t_with_every_luminous_wall_broken_it_is_still_fair",
	"t_the_brood_cells_are_entered_over_the_wall",
]

func run_all() -> int:
	var ok: bool = await boot()
	if not ok or not load_authored():
		return _report()
	say("THE BROOD QUEEN  %s, %d phases, %d luminous wall tile(s)"
		% [LEVEL, (boss.cfg.get("phases", []) as Array).size(),
			int(boss.call("walls_total"))])
	for name: String in CASES:
		_current = name
		await call(name)
	hold([])
	return _report()

func _report() -> int:
	if not standalone:
		return 1 if not failures.is_empty() else 0
	if failures.is_empty():
		print("brood queen: %d checks, ALL PASSED" % passes)
		return 0
	for f in failures:
		print("  FAIL  %s" % f)
	print("brood queen: %d checks, %d FAILED" % [passes + failures.size(), failures.size()])
	return 1
