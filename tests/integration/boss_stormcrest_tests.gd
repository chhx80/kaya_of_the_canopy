extends Node
## In-game suite for THE STORMCREST's two new mechanisms: the roost window and
## the gale.
##
## `tools/bossgate.sh` already answers the five questions of ADR 005 section 4 —
## defeatable, survivable, fair, arena-bound, and it ends. This file does not
## restate any of them. It exists for the two things the gate cannot see:
##
##   * **A boss that refuses damage.** Every one of the gate's checks passes for
##     a boss that can never be hurt at all — check 1 would fail, but it would
##     fail with "the tape did not kill it", which is the same sentence a bad
##     tape produces. So the window is asserted directly, from both sides: the
##     blade off a flying Stormcrest changes nothing, and the same blade into a
##     roosting one takes a point off it.
##   * **A boss that writes to the level's tile grid while the level is being
##     played.** The gale is compared against levels/heights_5.json parsed off
##     disk — not against a copy the boss made of itself — in both directions,
##     and the standable set is compared across all three phases because
##     boss_gate_checks.gd finds the standable tiles ONCE and sweeps every phase
##     against that list.
##
## And one thing the gate reports but does not fail on, which this arena's whole
## shape depends on: **can she get onto a refuge slab, column by column.** The
## gate jumps at a refuge holding one direction and calls the tile unreachable if
## she does not end up standing on that exact column; this measures the landing
## from every floor column and prints the table, so the answer to "why is that
## column unreachable" is a number and not a theory.
##
## Everything here is asserted on the outcome, never on the mechanism.
##
## Standalone (this file owns its whole harness):
##   $GODOT --headless --path . res://tests/integration/boss_stormcrest_runner.tscn
##
## Not wired into tests/integration/integration_tests.gd: this branch does not own
## that file. To wire it in, add to `run_all()`'s list:
##     "t_boss_stormcrest",
## and the method:
##     func t_boss_stormcrest() -> void:
##         var s: Node = (load("res://tests/integration/boss_stormcrest_tests.gd") as GDScript).new()
##         s.standalone = false
##         add_child(s)
##         await s.run_all()
##         passes += s.passes
##         failures.append_array(s.failures)
##         s.queue_free()
## `standalone = false` is what stops it printing its own report.

const LEVEL := "heights_5"
const BOSS := "stormcrest"
const TS := 16.0

## Geometry of heights_5's arena, named so a level edit breaks a name and not a
## number. These are the same values tools/worlds/heights_5.py draws from.
const ARENA_SCREEN := Vector2i(1, 1)
const FLOOR_ROW := 27
const STAND_ROW := 26
const SHELF_ROW := 25
const WEST_SLAB := 31
const EAST_SLAB := 37
const SLAB_W := 4
const PIT_X0 := 31             ## the span arena_inset clamps it to
const PIT_X1 := 44

## src/enemies/stormcrest.gd's `St`.
const ST_WALK := 1
const ST_LAND := 4

var failures: PackedStringArray = PackedStringArray()
var passes := 0
var standalone := true
var _current := ""

var lvl: Node = null
var boss: Enemy = null
var pl: Player = null
var authored: Array = []       ## the fg rows straight out of levels/heights_5.json

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

## The level as it is on disk: the only honest reference for "calm".
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

func gale_rect() -> Rect2i:
	var g: Dictionary = boss.cfg.get("gale", {})
	return Rect2i(int(g.get("x", 0)), int(g.get("y", 0)),
		int(g.get("w", 0)), int(g.get("h", 0)))

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
			if TileCollision.has_flag(lvl.world, r, TileData4.Flag.HAZARD):
				continue
			out[Vector2i(tx, ty)] = true
	return out

func stand_pos(tile: Vector2i) -> Vector2:
	return Vector2(float(tile.x) * TS + (TS - pl.box.x) * 0.5, float(tile.y) * TS - pl.box.y)

## `tile` here is the tile the body's FEET are in, the way the level's marks and
## the prover name a place — not the tile it is standing ON.
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
## 1. The window, from both sides. This is the fight's one idea and nothing else
## in the suite would notice it breaking in either direction: a Stormcrest that
## can always be hit is an ordinary boss with a long walk, and one that can never
## be hit is unbeatable.
func t_the_roost_is_the_only_window() -> void:
	_current = "the-window"
	boss.respawn()
	set_phase(0)
	boss.active = true
	await frames(2)
	# Airborne: put it in the circle and hit it.
	boss.set("st", ST_WALK)
	boss.set("t", 9.0)
	boss.pos.y = boss.spawn_pos.y - 100.0
	await frames(2)
	var before := boss.health
	boss.hurt(3, boss.center() + Vector2(48.0, 0.0))
	check(boss.health == before,
		"the blade took %d off a FLYING Stormcrest — it is supposed to be "
			% (before - boss.health)
			+ "invulnerable until it roosts, which is the whole fight")
	check(not bool(boss.get("defeated")), "a flying Stormcrest was killed outright")

	# Roosted: hit it again.
	boss.set("st", ST_LAND)
	boss.set("t", 9.0)
	boss.pos.y = boss.spawn_pos.y
	await frames(2)
	before = boss.health
	boss.hurt(1, boss.center() + Vector2(48.0, 0.0))
	check(boss.health == before - 1,
		"the blade did nothing to a ROOSTING Stormcrest (%d -> %d) — there is no "
			% [before, boss.health] + "window at all")

## 2. The roost cycle runs on its own clock, and the window is long enough to
## spend. Measured by watching the real fight rather than by reading the config:
## the first cut of `_volley()` restarted the stoop timer, and the Stormcrest
## circled for eighty seconds without ever coming down.
func t_the_roost_cycle_comes_round_in_every_phase() -> void:
	_current = "the-cycle"
	for phase in (boss.cfg.get("phases", []) as Array).size():
		boss.respawn()
		set_phase(phase)
		boss.active = true
		park(Vector2i(36, STAND_ROW))
		pl.control_enabled = false
		lvl.cam.snap_to_target()
		await frames(2)
		var windows := 0
		var window_frames := 0
		var was := true
		for f in 900:                      ## 15 s, the sweep's own budget
			pl.invuln = 999.0
			Game.health = Game.max_health
			pl.pos = stand_pos(Vector2i(36, STAND_ROW))
			pl.vel = Vector2.ZERO
			await get_tree().physics_frame
			var roosting: bool = bool(boss.call("roosting"))
			if roosting:
				window_frames += 1
				if not was:
					windows += 1
			was = roosting
		var pname := String((boss.cfg.get("phases", [])[phase] as Dictionary).get("name", ""))
		say("  phase %d %-7s %d roost window(s) in 15 s, %.1f s vulnerable"
			% [phase, pname, windows, float(window_frames) / 60.0])
		check(windows >= 2,
			"phase %d (%s) roosted %d time(s) in fifteen seconds — the gate's own "
				% [phase, pname, windows]
				+ "sample is fifteen seconds, and a window it never sees is a window "
				+ "the player never gets")
		check(window_frames >= 120,
			"phase %d (%s) was vulnerable for %.1f s of fifteen; two seconds is "
				% [phase, pname, float(window_frames) / 60.0]
				+ "about two blade throws, and less than that is not a fight")
	pl.control_enabled = true

## 3. The level on disk IS the calm arena. Anything else and tools/prove.sh and
## the traversal tape are looking at a level the player never sees.
func t_the_level_on_disk_is_the_calm_arena() -> void:
	_current = "authored-is-calm"
	boss.respawn()
	set_phase(0)
	await frames(2)
	var r := gale_rect()
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
		"phase 1 is authored calm, but %d tile(s) differ from levels/%s.json — %s"
			% [wrong, LEVEL, first])

## 4. The gale is real wind where the phase says, and it eats nothing.
func t_the_gale_is_wind_and_eats_nothing() -> void:
	_current = "the-gale"
	var phases: Array = boss.cfg.get("phases", [])
	for phase in phases.size():
		set_phase(phase)
		await frames(2)
		var lanes: Array = (phases[phase] as Dictionary).get("lanes", [])
		var r := gale_rect()
		var eaten := 0
		var calm: Array = []
		var windy := 0
		for y in range(r.position.y, r.position.y + r.size.y):
			for x in range(r.position.x, r.position.x + r.size.x):
				var was: int = authored_at(x, y)
				var now: int = lvl.world.get_fg(x, y)
				if was != 0:
					if now != was:
						eaten += 1
					continue
				var push := FormBase.current_at(lvl.world,
					Rect2(float(x) * TS + 1.0, float(y) * TS + 1.0, 14.0, 14.0))
				if _in_lanes(x, lanes):
					if absf(push.x) > 1.0:
						windy += 1
					else:
						calm.append(Vector2i(x, y))
					check(absf(push.y) < 0.01,
						"the gale at (%d,%d) pushes vertically (%.0f px/s). A draft "
							% [x, y, push.y]
							+ "changes the height of a jump, and the refuge slabs are a "
							+ "jump; this boss may only blow sideways")
				elif absf(push.x) > 1.0:
					calm.append(Vector2i(x, y))
		check(eaten == 0,
			"phase %d's gale overwrote %d tile(s) the level authored solid — a floor, "
				% [phase, eaten] + "a refuge slab or a buttress went under the wind")
		check(calm.is_empty(),
			"phase %d: %d tile(s) disagree with the phase's own lanes, first %s"
				% [phase, calm.size(), str(calm[0]) if not calm.is_empty() else "-"])
		say("  phase %d: %d windy tile(s) over %d lane(s)" % [phase, windy, lanes.size()])

func _in_lanes(x: int, lanes: Array) -> bool:
	for raw: Variant in lanes:
		var l: Dictionary = raw
		if x >= int(l.get("x0", 0)) and x <= int(l.get("x1", 0)):
			return true
	return false

## 5. Dropping the gale is not "roughly the level again". It is the level again.
func t_the_gale_drops_when_it_dies() -> void:
	_current = "the-gale-drops"
	var ok: bool = await boot()
	if not ok:
		return
	# Killed in PHASE 1, which is the case that matters and the case the first cut
	# of this check did not make: `Enemy.hurt()` calls `die()` and then keeps
	# going through the phase thresholds, so a corpse at 0 health satisfies every
	# one of them and escalates. Killing it from phase 3 hides that, because
	# there is nothing left to escalate to.
	set_phase(0)
	await frames(2)
	pl.invuln = 999.0
	boss.set("st", ST_LAND)
	boss.hurt(boss.health, boss.center() + Vector2(64.0, 0.0))
	check(bool(boss.get("defeated")), "the Stormcrest did not report itself defeated")
	check(int(boss.get("phase")) == 0,
		"the killing blow moved it to phase %d — a dead boss does not change phase, "
			% int(boss.get("phase"))
			+ "and on a boss that writes to the level that is not cosmetic")
	var r := gale_rect()
	var wrong := 0
	for y in range(r.position.y, r.position.y + r.size.y):
		for x in range(r.position.x, r.position.x + r.size.x):
			if lvl.world.get_fg(x, y) != authored_at(x, y):
				wrong += 1
	check(wrong == 0,
		"%d tile(s) of the arena did not come back to what levels/%s.json says "
			% [wrong, LEVEL] + "after the Stormcrest fell")
	# And the outcome, not the tile ids: a body standing anywhere on the floor
	# must be standing in still air. Comparing ids would pass on a repaint that
	# left the collision layer windy, and a screenshot caught exactly that —
	# Kaya walking west at a steady 80 px/s across an arena whose boss was dead.
	var pushed: Array = []
	for x in range(r.position.x, r.position.x + r.size.x):
		var body := Rect2(float(x) * TS + 3.0, float(STAND_ROW) * TS - 6.0, 10.0, 22.0)
		if absf(FormBase.current_at(lvl.world, body).x) > 1.0:
			pushed.append(x)
	check(pushed.is_empty(),
		"the gale still pushes a body on %d floor column(s) after the kill, first %s"
			% [pushed.size(), str(pushed[0]) if not pushed.is_empty() else "-"])

## 5b. The same thing by the other road into it. Walking out of the arena and
## back in respawns the boss (Level._on_screen_changed -> set_active_screen ->
## respawn), which puts it back in phase 1 — and phase 1 is calm. A gale that
## survives that is a gale nothing in the fight will ever take away again.
func t_the_gale_drops_when_it_respawns() -> void:
	_current = "the-gale-drops-on-respawn"
	var ok: bool = await boot()
	if not ok:
		return
	set_phase(2)
	await frames(2)
	var windy := 0
	var r := gale_rect()
	for x in range(r.position.x, r.position.x + r.size.x):
		var body := Rect2(float(x) * TS + 3.0, float(STAND_ROW) * TS - 6.0, 10.0, 22.0)
		if absf(FormBase.current_at(lvl.world, body).x) > 1.0:
			windy += 1
	check(windy > 0, "TEMPEST put no wind on the floor at all, so this proves nothing")
	boss.respawn()
	await frames(2)
	var pushed: Array = []
	for x in range(r.position.x, r.position.x + r.size.x):
		var body := Rect2(float(x) * TS + 3.0, float(STAND_ROW) * TS - 6.0, 10.0, 22.0)
		if absf(FormBase.current_at(lvl.world, body).x) > 1.0:
			pushed.append(x)
	check(pushed.is_empty(),
		"%d floor column(s) are still windy after the Stormcrest respawned into "
			% pushed.size() + "phase 1, which is calm")

## 6. The assumption the whole fairness sweep rests on. boss_gate_checks.gd
## collects the standable tiles ONCE and then sweeps every phase against that
## list; if the gale moved them, every verdict it printed would be about the
## wrong arena.
func t_the_gale_does_not_move_a_single_standable_tile() -> void:
	_current = "standable-invariant"
	var ok: bool = await boot()
	if not ok:
		return
	set_phase(0)
	await frames(2)
	var calm := standable_set()
	check(calm.size() > 0, "the arena has no standable tile at all")
	for phase in [1, 2]:
		set_phase(phase)
		await frames(2)
		var windy := standable_set()
		var moved: Array = []
		for t: Vector2i in calm.keys():
			if not windy.has(t):
				moved.append(t)
		for t: Vector2i in windy.keys():
			if not calm.has(t):
				moved.append(t)
		check(moved.is_empty(),
			"%d tile(s) changed standability in phase %d, first %s — the Boss Gate's "
				% [moved.size(), phase, str(moved[0]) if not moved.is_empty() else "-"]
				+ "fairness sweep would be measuring the wrong arena")
	say("  standable tiles: %d, unchanged by the gale" % calm.size())

## 7. Can she get onto the refuge, column by column. The gate reports this and
## does not fail on it, and its method is one held direction and a jump — so a
## column it calls unreachable might be a column the arena cannot offer, or might
## be one the scripted jump flies past. The difference is a measurement, so this
## takes it: jump from every floor column toward each slab and print where she
## lands.
func t_every_refuge_column_can_be_landed_on() -> void:
	_current = "refuge-columns"
	var ok: bool = await boot()
	if not ok:
		return
	set_phase(0)
	boss.active = false
	await frames(2)
	var floor_cols: Array = []
	for t: Vector2i in standable_set().keys():
		if t.y == FLOOR_ROW:
			floor_cols.append(t.x)
	floor_cols.sort()
	var landed: Dictionary = {}          ## slab column -> the floor column it came from
	var table: PackedStringArray = PackedStringArray()
	for from_col: int in floor_cols:
		for dir: String in ["right", "left"]:
			var got: Vector2i = await _hop(Vector2i(from_col, STAND_ROW), dir)
			if got.y == SHELF_ROW:
				table.append("%d%s->%d" % [from_col, "R" if dir == "right" else "L", got.x])
				if not landed.has(got.x):
					landed[got.x] = "%d%s" % [from_col, "R" if dir == "right" else "L"]
	say("  landings: %s" % " ".join(table))
	var missed: Array = []
	for slab in [WEST_SLAB, EAST_SLAB]:
		for i in SLAB_W:
			if not landed.has(slab + i):
				missed.append(slab + i)
	check(missed.is_empty(),
		"no jump from any floor column lands on refuge column(s) %s — those tiles "
			% str(missed)
			+ "are standable and unreachable, which is a safe tile that is not a dodge")
	boss.active = true

## One jump, holding one direction, the way boss_gate_checks.gd does it — with
## one correction that turned out to matter a great deal.
##
## `Actor.last_floor_tile` is written by `TileCollision.move_y` only on the frame
## a floor is *resolved*; standing still on one leaves it exactly as it was. So
## "she is on the floor and her last floor tile is the refuge" is true on the
## FIRST frame of the next measurement too, and the first cut of this case
## reported every one of the twenty-five jumps landing on col 34 — including
## jumps that started four tiles east of it and were held west. The stale read is
## the measurement, not the hop.
##
## Two lines fix it, and both are outcome-shaped rather than clever: clear the
## tile before the jump, and refuse to believe a landing until she has actually
## left the ground.
func _hop(from: Vector2i, dir: String) -> Vector2i:
	var best := Vector2i(-1, -1)
	for run_up in [0, 8, 16]:
		park(from)
		pl.last_floor_tile = Vector2i(-1, -1)
		lvl.cam.snap_to_target()
		_hold([])
		await frames(2)
		var airborne := false
		for f in 90:
			pl.invuln = 999.0
			Game.health = Game.max_health
			var held: Array = [dir]
			if f >= run_up and f < run_up + 18:
				held.append("jump")
			_hold(held)
			await get_tree().physics_frame
			if not pl.on_floor:
				airborne = true
				continue
			if airborne and pl.last_floor_tile.y == SHELF_ROW:
				best = pl.last_floor_tile
				break
		_hold([])
		if best.x >= 0:
			return best
	return best

## 8. It cannot follow her onto a refuge. The other half of what makes a refuge a
## refuge, measured by running the fight in every phase and watching where its
## body actually goes — including its altitude, because this is the first boss
## that can leave the top of its own screen.
func t_it_never_lands_on_a_refuge_slab() -> void:
	_current = "stays-off-the-slabs"
	var ok: bool = await boot()
	if not ok:
		return
	var on_slab := 0
	var trespass := 0
	var top := 9999.0
	for phase in 3:
		boss.respawn()
		set_phase(phase)
		boss.active = true
		park(Vector2i(36, STAND_ROW))
		pl.control_enabled = false
		lvl.cam.snap_to_target()
		await frames(2)
		for f in 600:
			pl.invuln = 999.0
			Game.health = Game.max_health
			pl.pos = stand_pos(Vector2i(36, STAND_ROW))
			pl.vel = Vector2.ZERO
			await get_tree().physics_frame
			var r := boss.aabb()
			top = minf(top, r.position.y)
			if r.position.x < float(PIT_X0) * TS - 0.5 or r.end.x > float(PIT_X1 + 1) * TS + 0.5:
				trespass += 1
			if boss.on_floor and absf(r.end.y - float(SHELF_ROW) * TS) < 4.0:
				on_slab += 1
			if Screen.index_of(boss.center(), Vector2i(999, 999)) != ARENA_SCREEN:
				trespass += 1
	pl.control_enabled = true
	say("  30 s of fight: the Stormcrest's body topped out at y=%.0f (the arena's roof is y=%.0f)"
		% [top, float(Screen.origin(ARENA_SCREEN).y)])
	check(on_slab == 0,
		"it stood on a refuge slab on %d frame(s) — `drop_through` is what keeps "
			% on_slab + "one-ways from being floors to it")
	check(trespass == 0,
		"it left its arena on %d frame(s)" % trespass)

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
	"t_the_roost_is_the_only_window",
	"t_the_roost_cycle_comes_round_in_every_phase",
	"t_the_level_on_disk_is_the_calm_arena",
	"t_the_gale_is_wind_and_eats_nothing",
	"t_the_gale_drops_when_it_dies",
	"t_the_gale_drops_when_it_respawns",
	"t_the_gale_does_not_move_a_single_standable_tile",
	"t_every_refuge_column_can_be_landed_on",
	"t_it_never_lands_on_a_refuge_slab",
]

func run_all() -> int:
	var ok: bool = await boot()
	if not ok or not load_authored():
		return _report()
	say("THE STORMCREST  %s, %d phases"
		% [LEVEL, (boss.cfg.get("phases", []) as Array).size()])
	for name: String in CASES:
		_current = name
		await call(name)
	_hold([])
	return _report()

func _report() -> int:
	if not standalone:
		return 1 if not failures.is_empty() else 0
	if failures.is_empty():
		print("stormcrest: %d checks, ALL PASSED" % passes)
		return 0
	for f in failures:
		print("  FAIL  %s" % f)
	print("stormcrest: %d checks, %d FAILED" % [passes + failures.size(), failures.size()])
	return 1
