extends Node
## In-game suite for THE TIDE MAW's one new mechanism: the tide.
##
## `tools/bossgate.sh` already answers the five questions of ADR 005 section 4 —
## defeatable, survivable, fair, arena-bound, and it ends. This file does not
## restate any of them. It exists because the Maw does something no other enemy
## in this project does: **it writes to the level's tile grid while the level is
## being played**, and the five checks would all pass while that was quietly
## corrupting the arena.
##
## Everything here is asserted on the outcome, never on the mechanism, because
## the six defects this project has shipped were every one of them a mechanism
## that reported success and an outcome nobody looked at. So:
##
##   * "the tide restores the level" is proved by comparing every tile in the
##     arena against **levels/ruins_5.json parsed off disk**, not against a copy
##     the boss made of itself
##   * "the flood cannot eat a shelf" is proved the same way, with the tide in
##     the other state
##   * "the fairness sweep's assumption holds" is proved by collecting the
##     standable tiles with the real `TileCollision` in both tide states and
##     comparing the sets — that assumption is load-bearing, because
##     boss_gate_checks.gd finds the standable tiles ONCE and then sweeps every
##     phase against them
##   * "the pull is a current you cannot walk out of" is proved by walking out
##     of it: the real human form, holding one direction for a second and a
##     half, drained and then flooded, and the two distances compared
##   * "the refuge is reachable" is proved by jumping onto it with the real
##     player, and "the Maw cannot follow" by running the fight and watching
##     where its body actually goes
##
## Standalone (this file owns its whole harness):
##   $GODOT --headless --path . res://tests/integration/boss_tide_maw_runner.tscn
##
## Not wired into tests/integration/integration_tests.gd: this branch does not
## own that file. To wire it in, add to `run_all()`'s list:
##     "t_boss_tide_maw",
## and the method:
##     func t_boss_tide_maw() -> void:
##         var s: Node = (load("res://tests/integration/boss_tide_maw_tests.gd") as GDScript).new()
##         s.standalone = false
##         add_child(s)
##         await s.run_all()
##         passes += s.passes
##         failures.append_array(s.failures)
##         s.queue_free()
## `standalone = false` is what stops it printing its own report. See REPORT.md.

const LEVEL := "ruins_5"
const BOSS := "tide_maw"
const TS := 16.0

## Geometry of ruins_5's arena, named so a level edit breaks a name and not a
## number. These are the same values tools/worlds/ruins_5.py draws from.
const ARENA_SCREEN := Vector2i(1, 1)
const ARENA_X0 := 26
const ARENA_X1 := 48
const PIT_X0 := 31
const PIT_X1 := 43
const FLOOR_ROW := 27
const SHELF_ROW := 25
const WEST_SLAB := 31          ## the two one-way refuge slabs, 4 tiles each
const EAST_SLAB := 39
const SLAB_W := 4
const PIVOT := 37

## 1.1 s of held input. Long enough for the difference between wading and
## being held by a current to be obvious, short enough that the arena wall is
## still ten tiles away at the end of a drained run.
const WALK_FRAMES := 66

var failures: PackedStringArray = PackedStringArray()
var passes := 0
var standalone := true
var _current := ""

var lvl: Node = null
var boss: Enemy = null
var pl: Player = null
var authored: Array = []       ## the fg rows straight out of levels/ruins_5.json

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

## The level as it is on disk: the only honest reference for "drained".
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
	authored = d.get("fg", []) as Array
	var legend := LevelLoader.legend_for(String(d.get("tileset", "jungle")))
	# char rows -> tile ids, the same resolution the loader does.
	var rows: Array = []
	for raw: Variant in authored:
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

func tide_rect() -> Rect2i:
	var t: Dictionary = boss.cfg.get("tide", {})
	return Rect2i(int(t.get("x", 0)), int(t.get("y", 0)),
		int(t.get("w", 0)), int(t.get("h", 0)))

func set_phase(i: int) -> void:
	boss.call("_set_phase", i)

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
			out[Vector2i(tx, ty)] = true
	return out

func stand_pos(tile: Vector2i) -> Vector2:
	return Vector2(float(tile.x) * TS + (TS - pl.box.x) * 0.5, float(tile.y) * TS - pl.box.y)

func park(tile: Vector2i) -> void:
	pl.control_enabled = true
	pl.dead = false
	pl.invuln = 999.0
	pl.hurt_t = 0.0
	pl.vel = Vector2.ZERO
	pl.drop_through = false
	pl.pos = stand_pos(tile)
	Game.health = Game.max_health

# ---------------------------------------------------------------- the checks
## 1. The level on disk IS the drained arena. Anything else and tools/prove.sh
## and the tape replay are looking at a level the player never sees.
func t_the_level_on_disk_is_the_drained_arena() -> void:
	_current = "authored-is-drained"
	set_phase(0)
	await frames(2)
	var r := tide_rect()
	var wrong := 0
	var first := ""
	for y in range(r.position.y, r.position.y + r.size.y):
		for x in range(r.position.x, r.position.x + r.size.x):
			if lvl.world.get_fg(x, y) != authored_at(x, y):
				wrong += 1
				if first == "":
					first = "(%d,%d) is %d, the file says %d" \
						% [x, y, lvl.world.get_fg(x, y), authored_at(x, y)]
	check(wrong == 0,
		"phase 1 is authored drained, but %d tile(s) differ from levels/%s.json — %s"
			% [wrong, LEVEL, first])
	check(not bool(boss.get("flooded")), "the Maw does not report itself flooded in EBB")

## 2. Flooding puts real water in the pit — the flag the fish and the human both
## read — and leaves everything the level drew exactly where it was.
func t_the_flood_is_water_and_eats_nothing() -> void:
	_current = "flood"
	set_phase(1)
	await frames(2)
	var r := tide_rect()
	var dry := []
	var eaten := 0
	for y in range(r.position.y, r.position.y + r.size.y):
		for x in range(r.position.x, r.position.x + r.size.x):
			var was: int = authored_at(x, y)
			var now: int = lvl.world.get_fg(x, y)
			if was != 0:
				if now != was:
					eaten += 1
				continue
			if not lvl.world.is_water(x, y):
				dry.append(Vector2i(x, y))
	check(dry.is_empty(),
		"the flood left %d authored-empty tile(s) dry, first %s"
			% [dry.size(), str(dry[0]) if not dry.is_empty() else "-"])
	check(eaten == 0,
		"the flood overwrote %d tile(s) the level authored solid — a shelf, a "
			% eaten + "floor or a wall went under the tide")
	check(bool(boss.get("flooded")), "the Maw reports itself flooded in FLOOD")
	# The surface has to be a surface, or the water has no top to swim up to.
	var top := int(r.position.y)
	check(lvl.world.flags_at(PIVOT, top) & TileData4.Flag.SURFACE != 0,
		"the top row of the flood (%d) carries no water surface" % top)

## 3. Draining is not "roughly the level again". It is the level again.
func t_draining_restores_the_level_exactly() -> void:
	_current = "drain"
	set_phase(1)
	await frames(2)
	set_phase(2)
	await frames(2)
	var r := tide_rect()
	var wrong := 0
	for y in range(r.position.y, r.position.y + r.size.y):
		for x in range(r.position.x, r.position.x + r.size.x):
			if lvl.world.get_fg(x, y) != authored_at(x, y):
				wrong += 1
	check(wrong == 0,
		"UNDERTOW drains, but %d tile(s) did not come back to what levels/%s.json says"
			% [wrong, LEVEL])
	check(not bool(boss.get("flooded")), "the Maw does not report itself flooded in UNDERTOW")

## 4. The assumption the whole fairness sweep rests on. boss_gate_checks.gd
## collects the standable tiles ONCE and then sweeps every phase against that
## list; if the tide moved them, every verdict it printed would be about the
## wrong tiles.
func t_the_tide_does_not_move_a_single_standable_tile() -> void:
	_current = "standable-invariant"
	set_phase(0)
	await frames(2)
	var drained := standable_set()
	set_phase(1)
	await frames(2)
	var flooded := standable_set()
	var moved: Array = []
	for t: Vector2i in drained.keys():
		if not flooded.has(t):
			moved.append(t)
	for t: Vector2i in flooded.keys():
		if not drained.has(t):
			moved.append(t)
	check(drained.size() > 0, "the arena has no standable tile at all")
	check(moved.is_empty(),
		"%d tile(s) changed standability with the tide, first %s — the Boss "
			% [moved.size(), str(moved[0]) if not moved.is_empty() else "-"]
			+ "Gate's fairness sweep would be measuring the wrong arena")
	say("  standable tiles: %d drained, %d flooded" % [drained.size(), flooded.size()])

## 5. The two lanes point opposite ways, measured through the same static
## function the player's own movement calls.
func t_the_pull_runs_inward_and_the_counter_current_out() -> void:
	_current = "lanes"
	set_phase(1)
	await frames(2)
	var t: Dictionary = boss.cfg.get("tide", {})
	var lanes: Array = t.get("lanes", [])
	check(lanes.size() >= 2, "the tide declares fewer than two current lanes")
	for raw: Variant in lanes:
		var lane: Dictionary = raw
		var row := int(lane.get("row", -1))
		var inward := String(lane.get("flow", "in")) != "out"
		for x in [PIT_X0 + 2, PIT_X1 - 2]:
			var cell := Rect2(float(x) * TS + 1.0, float(row) * TS + 1.0, 14.0, 14.0)
			var c := FormBase.current_at(lvl.world, cell)
			var toward_pivot: float = signf(float(PIVOT) - float(x)) * c.x
			check(absf(c.x) > 1.0,
				"row %d col %d carries no current at all" % [row, x])
			check((toward_pivot > 0.0) == inward,
				"row %d col %d flows %s; the lane is declared '%s'"
					% [row, x, "toward" if toward_pivot > 0.0 else "away from",
						"in" if inward else "out"])

## 6. "You dodge by riding the counter-current, not by running." Proved by
## running: the real human form, holding one direction for a second and a half
## off the same tile, drained and then flooded.
func t_you_cannot_simply_walk_out_of_the_pull() -> void:
	_current = "the-pull"
	# West of the pivot, so walking west is walking UPSTREAM, and started far
	# enough from the arena wall that the wall is not what stops her: the first
	# cut of this case ran from col 33 for 90 frames and measured 115 px in both
	# tide states, which was the distance to the wall and not the distance she
	# could make.
	var bed := Vector2i(PIVOT - 1, FLOOR_ROW)
	var dry: float = await _walk_from(bed, "left", 0)
	var wet: float = await _walk_from(bed, "left", 1)
	say("  walking west off the bed: %.0f px drained, %.0f px flooded" % [dry, wet])
	check(dry > 60.0, "a drained arena should let Kaya walk (she managed %.0f px)" % dry)
	check(wet < dry * 0.75,
		("the flood's pull did not hold her: %.0f px flooded against %.0f px "
		+ "drained. The bed lane is supposed to be a current you ride out of, "
		+ "not one you stroll out of.") % [wet, dry])

## The camera snap comes BEFORE the phase is set, and that order is the whole
## point of this helper. Landing the camera on the arena screen fires
## `Level._on_screen_changed`, which calls `set_active_screen` on every enemy,
## which respawns the ones that were inactive — and `Enemy.respawn()` puts the
## Maw back into phase 1, which drains the arena. Setting the phase first and
## snapping afterwards measured 113 px in both tide states, because both runs
## were drained. This is not a quirk of the test: re-entering the arena really
## does reset the fight, and it is why `reset_arena()` in boss_gate_checks.gd
## respawns before it sets a phase.
func _walk_from(tile: Vector2i, dir: String, phase: int) -> float:
	park(tile)
	lvl.cam.snap_to_target()
	await frames(2)
	set_phase(phase)
	boss.active = false
	await frames(2)
	park(tile)
	await frames(2)
	var x0 := pl.center().x
	for f in WALK_FRAMES:
		pl.invuln = 999.0
		Game.health = Game.max_health
		_hold([dir])
		await get_tree().physics_frame
	var moved := absf(pl.center().x - x0)
	_hold([])
	boss.active = true
	return moved

## 7. The refuge is two tiles up, and two tiles is a jump Kaya has. Proved by
## jumping, with the real form code, from the pit floor beside it.
func t_the_refuge_shelf_is_two_tiles_up_and_she_can_make_it() -> void:
	_current = "refuge-reachable"
	park(Vector2i(PIVOT, FLOOR_ROW))
	lvl.cam.snap_to_target()
	await frames(2)
	set_phase(0)
	boss.active = false
	await frames(2)
	check(FLOOR_ROW - SHELF_ROW == 2,
		"the refuges are %d tiles over the arena floor, not 2" % (FLOOR_ROW - SHELF_ROW))
	# Onto the SLAB, not onto one nominated tile of it. Kaya runs at 108 px/s
	# and a running jump crosses three or four tiles, so insisting she lands on
	# the column nearest the Maw would be testing her braking distance and not
	# whether the refuge is reachable.
	var west: bool = true
	for slab in [[WEST_SLAB, WEST_SLAB + SLAB_W - 1], [EAST_SLAB, EAST_SLAB + SLAB_W - 1]]:
		var from := Vector2i(int(slab[0]) - 3 if west else int(slab[1]) + 3, FLOOR_ROW)
		var got: Vector2i = await _hop(from, int(slab[0]), int(slab[1]))
		check(got.y == SHELF_ROW,
			"Kaya could not get from the arena floor at col %d onto the refuge at cols %d-%d (she ended on %s)"
				% [from.x, int(slab[0]), int(slab[1]), str(got)])
		if got.y == SHELF_ROW:
			say("  the %s refuge: reached col %d from the floor at col %d"
				% ["west" if west else "east", got.x, from.x])
		west = false
	boss.active = true

## Jump at the slab and report the tile she actually ended up standing on.
func _hop(from: Vector2i, x0: int, x1: int) -> Vector2i:
	var toward := "right" if x0 > from.x else "left"
	for run_up in [0, 6, 12, 20, 30]:
		park(from)
		lvl.cam.snap_to_target()
		_hold([])
		await frames(2)
		for f in 110:
			pl.invuln = 999.0
			Game.health = Game.max_health
			var held: Array = [toward]
			if f >= run_up and f < run_up + 18:
				held.append("jump")
			_hold(held)
			await get_tree().physics_frame
			var t: Vector2i = pl.last_floor_tile
			if pl.on_floor and t.y == SHELF_ROW and t.x >= x0 and t.x <= x1:
				_hold([])
				return t
		_hold([])
	return pl.last_floor_tile

## 8. The Maw cannot follow her onto a shelf. This is the other half of what
## makes the refuge a refuge, and it is measured by letting the fight run in
## every phase and watching where the body actually goes.
func t_the_maw_never_reaches_a_refuge_shelf() -> void:
	_current = "the-maw-stays-in-the-pit"
	var trespass := 0
	var lowest := 9999.0
	var highest := -9999.0
	for phase in 3:
		set_phase(phase)
		boss.respawn()
		boss.call("_set_phase", phase)
		boss.active = true
		park(Vector2i(PIVOT, FLOOR_ROW))
		pl.control_enabled = false
		await frames(2)
		for f in 420:
			pl.invuln = 999.0
			Game.health = Game.max_health
			pl.pos = stand_pos(Vector2i(PIVOT, FLOOR_ROW))
			pl.vel = Vector2.ZERO
			await get_tree().physics_frame
			var r := boss.aabb()
			lowest = minf(lowest, r.position.x)
			highest = maxf(highest, r.end.x)
			if r.position.x < float(PIT_X0) * TS - 0.5 or r.end.x > float(PIT_X1 + 1) * TS + 0.5:
				trespass += 1
	pl.control_enabled = true
	say("  the Maw's body swept x %.0f..%.0f over 21 s; the pit is %.0f..%.0f"
		% [lowest, highest, float(PIT_X0) * TS, float(PIT_X1 + 1) * TS])
	check(trespass == 0,
		("the Maw's body left the pit (cols %d-%d) on %d frame(s) — the flanking "
		+ "shelves are only a refuge while it cannot follow her onto them")
			% [PIT_X0, PIT_X1, trespass])

## 9. The tide goes out with it, so check 5 of the boss gate walks Kaya out of a
## drained ruin and not out of a flooded one.
func t_the_tide_goes_out_when_the_maw_dies() -> void:
	_current = "the-tide-goes-out"
	var ok: bool = await boot()
	if not ok:
		return
	set_phase(1)
	await frames(2)
	check(bool(boss.get("flooded")), "the arena is flooded going into the kill")
	pl.invuln = 999.0
	boss.hurt(boss.health, boss.center() + Vector2(64.0, 0.0))
	check(bool(boss.get("defeated")), "the Maw did not report itself defeated")
	var r := tide_rect()
	var wet := 0
	for y in range(r.position.y, r.position.y + r.size.y):
		for x in range(r.position.x, r.position.x + r.size.x):
			if authored_at(x, y) == 0 and lvl.world.is_water(x, y):
				wet += 1
	check(wet == 0, "%d tile(s) of the arena were still under water after the Maw fell" % wet)

# ---------------------------------------------------------------- input
const ACTIONS := {"left": &"move_left", "right": &"move_right",
	"up": &"move_up", "down": &"move_down", "jump": &"jump", "attack": &"attack"}

func _hold(held: Array) -> void:
	for name: String in ACTIONS.keys():
		var a: StringName = ACTIONS[name]
		if held.has(name):
			if not Input.is_action_pressed(a):
				Input.action_press(a)
		elif Input.is_action_pressed(a):
			Input.action_release(a)

# ---------------------------------------------------------------- entry point
const CASES := [
	"t_the_level_on_disk_is_the_drained_arena",
	"t_the_flood_is_water_and_eats_nothing",
	"t_draining_restores_the_level_exactly",
	"t_the_tide_does_not_move_a_single_standable_tile",
	"t_the_pull_runs_inward_and_the_counter_current_out",
	"t_you_cannot_simply_walk_out_of_the_pull",
	"t_the_refuge_shelf_is_two_tiles_up_and_she_can_make_it",
	"t_the_maw_never_reaches_a_refuge_shelf",
	"t_the_tide_goes_out_when_the_maw_dies",
]

func run_all() -> int:
	var ok: bool = await boot()
	if not ok or not load_authored():
		return _report()
	say("THE TIDE MAW  %s, %d phases" % [LEVEL, (boss.cfg.get("phases", []) as Array).size()])
	for name: String in CASES:
		_current = name
		await call(name)
	_hold([])
	return _report()

func _report() -> int:
	if not standalone:
		return 1 if not failures.is_empty() else 0
	if failures.is_empty():
		print("tide maw: %d checks, ALL PASSED" % passes)
		return 0
	for f in failures:
		print("  FAIL  %s" % f)
	print("tide maw: %d checks, %d FAILED" % [passes + failures.size(), failures.size()])
	return 1
