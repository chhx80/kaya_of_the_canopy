extends Node
## THE BOSS GATE — ADR 005 section 4, run against the real fight.
##
## A boss fight is not a traversal problem, so the Route Prover cannot speak to
## it. This is its own gate, and it exists for the same reason the route gate
## does: the failure mode is an unwinnable situation nobody modelled — the fight
## equivalent of a shaft capped across its full width.
##
##   1. defeatable   a strategy tape kills the boss inside a time bound
##   2. survivable   that same tape wins from full health with >= 1 heart left
##   3. fair         for every attack, in every phase, sweep the player across
##                   every standable tile in the arena and assert >= 1 tile
##                   where the attack does not connect
##   4. arena bound  the boss never leaves arena_min/arena_max or its screen
##   5. it ends      boss_exit is reachable from the arena floor after defeat
##
## Check 3 is the one that matters, and the one nothing else detects. Everything
## here is an *outcome*: the sweep does not model the attack's coverage, it puts
## Kaya on a tile and watches the game's own collision either resolve on her or
## not. A projectile disappearing on top of her IS the game's hit test firing.
##
## Run it with tools/bossgate.sh.

const TS := 16.0
const Tape := preload("res://tests/integration/boss_gate_tape.gd")

## Sweep budget. `WANT_INSTANCES` attack instances per tile, because one sample
## is a coincidence; the tile is declared safe only if *every* observed instance
## missed. FRAME_CAP bounds a tile that never sees the attack at all.
const WANT_INSTANCES := 2
const FRAME_CAP := 900          ## 15 s of sim per tile
const DISCOVER_CAP := 900       ## one uninterrupted look per phase, to list its attacks
const SETTLE := 2
## After the last attack of a sample has fired, keep watching this long so the
## thing that was thrown has time to arrive. The Warden's longest-lived shot is
## 2.6 s; three seconds outlives all of them.
const DRAIN_CAP := 180

## Slack added to a vanished projectile's last sampled rect, covering the one
## frame of travel between the sample and the collision that consumed it.
const SWEEP_SLACK := 2.0

## How long the strategy tape is allowed to take, and how much health must be
## left when it is over.
const DEFEAT_TIME_BOUND := 90.0
const MIN_HEARTS_LEFT := 1

var level_id := "jungle_5"
var boss_id := "boss_grove"
var tape_path := "res://tools/bossgate/tapes/boss_grove.json"
## Full sweep by default; tools/bossgate.sh --quick trims it for a smoke run.
var quick := false

var lvl: Node = null
var boss: Enemy = null
var pl: Player = null
## Cached at boot: the boss node is freed 0.35 s after it dies, and check 5
## carries on walking around the arena long after that.
var home_screen := Vector2i.ZERO
var arena_min := 0.0
var arena_max := 0.0

var failures: PackedStringArray = PackedStringArray()
var passes := 0
var lines: PackedStringArray = PackedStringArray()
var _current := ""
var _completed := false

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
	lines.append(s)
	print(s)

# ---------------------------------------------------------------- boot
func boot() -> bool:
	Game.reset_run()
	Game.goto_level(level_id)
	await frames(6)
	lvl = Game.current_level
	if lvl == null or not is_instance_valid(lvl):
		failures.append("boot :: level '%s' did not load" % level_id)
		return false
	pl = lvl.player
	boss = lvl.get("boss") as Enemy
	if pl == null or boss == null:
		failures.append("boot :: level '%s' has no player or no boss" % level_id)
		return false
	if boss.enemy_id != boss_id:
		failures.append("boot :: expected boss '%s', found '%s'" % [boss_id, boss.enemy_id])
		return false
	home_screen = boss.home_screen
	arena_min = float(boss.get("arena_min"))
	arena_max = float(boss.get("arena_max"))
	return true

func arena_tile_origin() -> Vector2i:
	var o := Screen.origin(home_screen)
	return Vector2i(int(o.x / TS), int(o.y / TS))

## Every tile Kaya can stand on inside the arena screen, found by putting her
## real hitbox there and asking the real collision code, not by reading tile ids.
## Hazard tiles are excluded: a refuge on spikes is not a refuge.
func standable_tiles() -> Array:
	var out: Array = []
	var t0 := arena_tile_origin()
	var b := pl.box
	for ty in range(t0.y, t0.y + Screen.H / int(TS)):
		for tx in range(t0.x, t0.x + Screen.W / int(TS)):
			var r := Rect2(Vector2(float(tx) * TS + (TS - b.x) * 0.5, float(ty) * TS - b.y), b)
			if TileCollision.has_flag(lvl.world, r, TileData4.Flag.SOLID):
				continue
			if not TileCollision.is_on_floor(lvl.world, r, false):
				continue
			if TileCollision.has_flag(lvl.world, r, TileData4.Flag.HAZARD):
				continue
			# Standing on the arena's rim puts Kaya's body on the screen above,
			# which flips the camera and freezes the boss. That is not a tile
			# inside this arena, and counting it would let a phase report an
			# attack that "never fired" when the fight simply was not running.
			if Screen.index_of(r.get_center(), Vector2i(999, 999)) != home_screen:
				continue
			out.append(Vector2i(tx, ty))
	return out

func stand_pos(tile: Vector2i) -> Vector2:
	return Vector2(float(tile.x) * TS + (TS - pl.box.x) * 0.5, float(tile.y) * TS - pl.box.y)

# ---------------------------------------------------------------- scenario
## Wipes everything the boss has spawned and returns the arena to a known state.
## `respawn()` is the game's own reset, so the start of every sample is the
## state the game itself produces when you walk back onto the screen.
func reset_arena(phase: int) -> void:
	Game.sim_paused = false
	var doomed: Array = []
	for n: Node in entity_children():
		if n == pl or n == boss:
			continue
		if n is Projectile or n is Blade or n is MeleeHit or n is Enemy:
			doomed.append(n)
	for n: Node in doomed:
		entities().remove_child(n)
		n.free()
	boss.respawn()
	boss.active = true
	boss.facing = 1
	var phases: Array = boss.cfg.get("phases", [])
	if phase > 0 and phase <= phases.size() - 1:
		boss.health = int((phases[phase - 1] as Dictionary).get("until_health", 1))
	boss.call("_set_phase", phase)

## Holds Kaya on one tile, awake and fully vulnerable. Invulnerability is
## deliberately zeroed every frame: i-frames are a consolation prize, not a
## dodge, and the question this sweep asks is whether the attack *reaches* the
## tile.
func pin(tile: Vector2i) -> void:
	pl.control_enabled = false
	pl.input.clear()
	pl.dead = false
	pl.invuln = 0.0
	pl.hurt_t = 0.0
	pl.vel = Vector2.ZERO
	pl.drop_through = false
	pl.pos = stand_pos(tile)
	Game.health = Game.max_health

func entities() -> Node2D:
	return lvl.get("entities") as Node2D

func entity_children() -> Array:
	var e := entities()
	return e.get_children() if e != null else []

func adds() -> Array:
	var out: Array = []
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e != null and e != boss and e.level == lvl and is_instance_valid(e):
			out.append(e)
	return out

# ---------------------------------------------------------------- attack tags
const STATE_NAMES := ["IDLE", "WALK", "WINDUP", "AIR", "LAND", "SPRAY"]

func state_name(i: int) -> String:
	return STATE_NAMES[i] if i >= 0 and i < STATE_NAMES.size() else "st%d" % i

## An attack is named by the state transition the boss was making on the frame
## its damage sources appeared. Nothing is hard-coded about *which* transitions
## attack — they are discovered by watching. A boss with no `st` at all still
## gets one lumped attack rather than silently getting none.
func tag_for(prev_st: int, st: int) -> String:
	if prev_st < 0:
		return "attack"
	return "%s>%s" % [state_name(prev_st), state_name(st)]

func boss_state() -> int:
	var v: Variant = boss.get("st")
	return int(v) if typeof(v) == TYPE_INT else -1

# ---------------------------------------------------------------- the sweep
## Watch one tile, in one phase, until every attack that fires has been seen
## `want` times. Returns per-tag {"instances": n, "connects": n, "sources": n}.
##
## "Connects" means the game's own hit test resolved this attack's damage source
## on Kaya: a tracked projectile left the tree while its last sampled rect, grown
## by one frame of its own travel, covered her. That is the same test the
## projectile runs on itself, observed from outside.
func watch_tile(phase: int, tile: Vector2i, want: int, cap: int,
		expected: Array = []) -> Dictionary:
	reset_arena(phase)
	pin(tile)
	lvl.cam.snap_to_target()
	await frames(SETTLE)
	pin(tile)

	var tracked: Dictionary = {}     ## instance_id -> {tag, rect, step, node}
	var known: Dictionary = {}
	var result: Dictionary = {}
	var body: Dictionary = {"frames": 0}
	var prev_st := boss_state()
	var boss_prev := boss.aabb()
	var escapes := 0
	var drain := -1
	var f := 0

	while f < cap:
		pin(tile)
		await get_tree().physics_frame
		f += 1
		var pr := pl.aabb()

		# --- attacks that fired during the frame just executed -------------
		var st := boss_state()
		var tag := tag_for(prev_st, st)
		var fresh := 0
		for n: Node in entity_children():
			if n == pl or n == boss:
				continue
			var is_src: bool = n is Projectile or (n is Enemy and n != boss)
			if not is_src:
				continue
			var id: int = n.get_instance_id()
			if known.has(id):
				continue
			known[id] = true
			fresh += 1
			var step := 4.0
			if n is Projectile:
				step = maxf(4.0, (n as Projectile).vel.length() / 60.0 + 2.0)
			var rect: Rect2 = n.call("aabb")
			tracked[id] = {"tag": tag, "rect": rect, "step": step, "ref": weakref(n),
				"from_x": boss.center().x}
		if fresh > 0:
			if not result.has(tag):
				result[tag] = {"instances": 0, "connects": 0, "sources": 0,
					"reach": 0.0, "first_frame": f}
			var r: Dictionary = result[tag]
			r["instances"] = int(r["instances"]) + 1
			r["sources"] = int(r["sources"]) + fresh

		# --- did anything resolve on Kaya? ---------------------------------
		var gone: Array = []
		for id: int in tracked.keys():
			var e: Dictionary = tracked[id]
			var node := (e["ref"] as WeakRef).get_ref() as Node
			if node != null and is_instance_valid(node) and not node.is_queued_for_deletion():
				var live: Rect2 = node.call("aabb")
				e["rect"] = live
				continue
			gone.append(id)
			var last: Rect2 = e["rect"]
			if last.grow(float(e["step"]) + SWEEP_SLACK).intersects(pr):
				var t: String = e["tag"]
				if result.has(t):
					var rr: Dictionary = result[t]
					rr["connects"] = int(rr["connects"]) + 1
					rr["reach"] = maxf(float(rr["reach"]),
						absf(pl.center().x - float(e["from_x"])))
		for id: int in gone:
			tracked.erase(id)

		# The boss body is not an attack — you dodge a walking boss by walking —
		# but the sweep records where it reaches, because the report should say
		# so rather than leave it unmeasured.
		var swept := boss_prev.merge(boss.aabb())
		boss_prev = boss.aabb()
		if swept.intersects(pr):
			body["frames"] = int(body["frames"]) + 1

		# --- check 4, measured on every frame of every sample ---------------
		if boss.pos.x < arena_min - 0.5 or boss.pos.x > arena_max + 0.5:
			escapes += 1
		elif Screen.index_of(boss.center(), Vector2i(999, 999)) != home_screen:
			escapes += 1

		prev_st = st
		# Stopping the moment the last instance *spawns* would throw away the
		# only thing worth watching: whether it arrives. The sample runs on
		# until every source it is tracking is gone, or until longer than the
		# longest-lived projectile in the boss's config.
		if drain < 0:
			if _satisfied(result, want, expected):
				drain = DRAIN_CAP
		else:
			drain -= 1
			if drain <= 0 or tracked.is_empty():
				break

	Game.health = Game.max_health
	return {"attacks": result, "body_frames": int(body["frames"]),
		"escapes": escapes, "frames": f}

## Every attack the phase is known to make must have fired `want` times before
## the sample is allowed to end. Stopping as soon as the attacks seen *so far*
## are satisfied is how a tile ends up silently unmeasured for a second attack,
## and silence is not a pass.
func _satisfied(result: Dictionary, want: int, expected: Array) -> bool:
	var need: Array = expected if not expected.is_empty() else result.keys()
	if need.is_empty():
		return false
	for tag: String in need:
		if not result.has(tag):
			return false
		if int((result[tag] as Dictionary)["instances"]) < want:
			return false
	return true

## Which attacks this phase makes at all, found by watching the fight from a few
## spread-out places with no early exit. The sweep proper then insists on seeing
## every one of them on every tile.
func discover_attacks(phase: int, probes: Array) -> Array:
	var tags: Dictionary = {}
	for tile: Vector2i in probes:
		var obs: Dictionary = await watch_tile(phase, tile, 1 << 30, DISCOVER_CAP)
		for tag: String in (obs["attacks"] as Dictionary).keys():
			tags[tag] = true
	return tags.keys()

# ---------------------------------------------------------------- check 3
func check_fair() -> void:
	_current = "fair"
	var phases: Array = boss.cfg.get("phases", [])
	var tiles := standable_tiles()
	say("")
	say("  arena %s   standable tiles: %d   phases: %d"
		% [str(boss.home_screen), tiles.size(), phases.size()])
	check(tiles.size() > 0, "the arena has no standable tile at all")
	if tiles.is_empty():
		return

	var sweep_tiles: Array = tiles
	if quick:
		sweep_tiles = []
		for i in tiles.size():
			if i % 4 == 0:
				sweep_tiles.append(tiles[i])
	var total_escapes := 0
	var body_tiles: Dictionary = {}
	var safe_by_phase: Dictionary = {}

	for phase in phases.size():
		var pname := String((phases[phase] as Dictionary).get("name", "phase %d" % phase))
		var expected: Array = await discover_attacks(phase, _probe_tiles(sweep_tiles))
		say("  phase %d %-6s attacks: %s" % [phase, pname,
			", ".join(PackedStringArray(expected)) if not expected.is_empty() else "(none)"])
		var per_tag: Dictionary = {}
		for tag: String in expected:
			per_tag[tag] = {"safe": [], "hit": [], "silent": [], "instances": 0, "reach": 0.0}
		for tile: Vector2i in sweep_tiles:
			var obs: Dictionary = await watch_tile(phase, tile, WANT_INSTANCES,
				FRAME_CAP, expected)
			total_escapes += int(obs["escapes"])
			if int(obs["body_frames"]) > 0:
				body_tiles[tile] = true
			var attacks: Dictionary = obs["attacks"]
			# An attack nobody expected still gets a verdict rather than a shrug.
			for tag: String in attacks.keys():
				if not per_tag.has(tag):
					per_tag[tag] = {"safe": [], "hit": [], "silent": [],
						"instances": 0, "reach": 0.0}
			for tag: String in per_tag.keys():
				var e: Dictionary = per_tag[tag]
				if not attacks.has(tag):
					(e["silent"] as Array).append(tile)
					continue
				var a: Dictionary = attacks[tag]
				e["instances"] = int(e["instances"]) + int(a["instances"])
				e["reach"] = maxf(float(e["reach"]), float(a["reach"]))
				if int(a["connects"]) > 0:
					(e["hit"] as Array).append(tile)
				else:
					(e["safe"] as Array).append(tile)

		# Silence is not a pass: a phase that produced no attack at all is a
		# hole in the sweep, not a clean sheet.
		check(not per_tag.is_empty(),
			"phase %d (%s): no attack was observed at all — the sweep proved nothing"
				% [phase, pname])
		safe_by_phase[phase] = per_tag
		for tag: String in per_tag.keys():
			var e: Dictionary = per_tag[tag]
			var safe: Array = e["safe"]
			var hit: Array = e["hit"]
			var silent: Array = e["silent"]
			say("  phase %d %-6s %-12s %d instances over %d tiles | hit %d, missed %d, never fired %d | reach %.0f px"
				% [phase, pname, tag, int(e["instances"]), sweep_tiles.size(),
					hit.size(), safe.size(), silent.size(), float(e["reach"])])
			if not safe.is_empty():
				say("      did not connect on: %s" % _tiles_str(safe))
			check(not safe.is_empty(),
				("phase %d (%s) attack %s connects on EVERY one of the %d standable tiles "
				+ "where it was observed — it has no dodge window, so it is unavoidable damage")
					% [phase, pname, tag, hit.size()])
			# A tile the attack never reached during the sample proves nothing
			# about that tile. Counting it as safe is exactly the mistake that
			# shipped six levels: the mechanism was checked, the outcome was not.
			check(silent.is_empty(),
				("phase %d (%s) attack %s never fired at all on %d tile(s) in %d frames, "
				+ "so the sweep proved nothing there: %s")
					% [phase, pname, tag, silent.size(), FRAME_CAP, _tiles_str(silent)])

	_current = "arena-bound"
	check(total_escapes == 0,
		"the boss left arena_min/arena_max or its home screen on %d frame(s)" % total_escapes)

	# Not part of ADR 005's check 3, and deliberately not a failure: a safe tile
	# you cannot get to during the fight is not a dodge. Reported because the
	# whole point of this gate is that nothing goes unmeasured.
	_current = "fair"
	await _report_refuge_reachability(safe_by_phase)
	say("  the boss body reached %d of the %d swept tiles" % [body_tiles.size(), sweep_tiles.size()])

## A few tiles spread across the sweep set, for the discovery pass.
func _probe_tiles(tiles: Array) -> Array:
	if tiles.size() <= 3:
		return tiles
	return [tiles[0], tiles[tiles.size() / 2], tiles[tiles.size() - 1]]

func _tiles_str(tiles: Array) -> String:
	var parts: PackedStringArray = PackedStringArray()
	for t: Vector2i in tiles:
		parts.append("(%d,%d)" % [t.x, t.y])
		if parts.size() >= 12:
			parts.append("...")
			break
	return " ".join(parts)

## Can Kaya get to the tiles that are safe, from where the fight puts her?
## Measured by jumping her at it with the real form code, not by comparing
## numbers to a jump envelope — the envelope is what shipped six defects.
func _report_refuge_reachability(safe_by_phase: Dictionary) -> void:
	var floor_tiles := _floor_tiles()
	if floor_tiles.is_empty():
		return
	var checked: Dictionary = {}
	var unreachable: Array = []
	var reachable: Array = []
	for phase: int in safe_by_phase.keys():
		var per_tag: Dictionary = safe_by_phase[phase]
		for tag: String in per_tag.keys():
			for tile: Vector2i in ((per_tag[tag] as Dictionary)["safe"] as Array):
				if checked.has(tile):
					continue
				checked[tile] = true
				if floor_tiles.has(tile):
					reachable.append(tile)
					continue
				var ok: bool = await _can_hop_onto(tile, floor_tiles)
				if ok:
					reachable.append(tile)
				else:
					unreachable.append(tile)
	say("  refuges: %d reachable from the arena floor, %d not"
		% [reachable.size(), unreachable.size()])
	if not unreachable.is_empty():
		var apex: float = await _measure_apex()
		var rise := 0.0
		for t: Vector2i in unreachable:
			rise = maxf(rise, float(floor_tiles[0].y - t.y) * TS)
		say("      NOTE  unreachable refuge tiles: %s" % _tiles_str(unreachable))
		say("      NOTE  they sit up to %.0f px above the arena floor; Kaya's measured"
			% rise)
		say("      NOTE  apex as %s is %.0f px, so once she is down she cannot return."
			% [pl.form_id, apex])
		say("      NOTE  a safe tile you cannot get to is not a dodge. ADR 005's")
		say("      NOTE  check 3 does not ask this, so it is reported, not failed.")
	# A refuge you cannot shoot back from is a stalemate, not a dodge — the other
	# half of the same question, and just as cheap to answer by trying it.
	for t: Vector2i in reachable + unreachable:
		var can: bool = await _can_fight_from(t)
		if not can:
			say("      NOTE  refuge (%d,%d): six seconds of blade throws never damaged"
				% [t.x, t.y])
			say("      NOTE  the boss from there — safe, but not a place to fight from.")

## Kaya's real jump height, measured by jumping her, not read off a curve. The
## envelope in tools/reachability.py is 6 px optimistic and that is what shipped
## defect 6; this number comes from the shipping form code.
func _measure_apex() -> float:
	var floor_tiles := _floor_tiles()
	if floor_tiles.is_empty():
		return 0.0
	reset_arena(0)
	boss.active = false
	pl.control_enabled = true
	pl.invuln = 999.0
	pl.dead = false
	pl.vel = Vector2.ZERO
	pl.pos = stand_pos(floor_tiles[floor_tiles.size() / 2])
	Tape.release_all()
	await frames(2)
	var start := pl.pos.y
	var top := start
	for f in 90:
		pl.invuln = 999.0
		pl.hurt_t = 0.0
		Tape.apply(["jump"] if f < 18 else [])
		await get_tree().physics_frame
		top = minf(top, pl.pos.y)
	Tape.release_all()
	pl.control_enabled = false
	boss.active = true
	return start - top

## Stand on the tile and throw the blade at the boss for six seconds. Synthetic
## input goes through the real InputMap, so this is the weapon the player has,
## fired the way the player fires it.
func _can_fight_from(tile: Vector2i) -> bool:
	reset_arena(0)
	pl.control_enabled = true
	pl.dead = false
	pl.invuln = 999.0
	pl.hurt_t = 0.0
	pl.vel = Vector2.ZERO
	pl.pos = stand_pos(tile)
	lvl.cam.snap_to_target()
	await frames(2)
	var hurt_it := false
	for f in 360:
		pl.invuln = 999.0
		pl.hurt_t = 0.0
		Game.health = Game.max_health
		pl.pos = stand_pos(tile)
		pl.vel = Vector2.ZERO
		pl.facing = 1 if boss.center().x > pl.center().x else -1
		Tape.apply([] if (f / 3) % 2 == 1 else ["attack"])
		await get_tree().physics_frame
		if boss.health < boss.max_health:
			hurt_it = true
			break
	Tape.release_all()
	pl.control_enabled = false
	return hurt_it

func _floor_tiles() -> Array:
	var out: Array = []
	var lowest := -1
	for t: Vector2i in standable_tiles():
		lowest = maxi(lowest, t.y)
	for t: Vector2i in standable_tiles():
		if t.y == lowest:
			out.append(t)
	return out

## Runs the real player: stand under the target, hold toward it, jump, and see
## whether she ends up standing on it. Tries from every floor tile within a
## screen's reach, nearest first.
func _can_hop_onto(target: Vector2i, floor_tiles: Array) -> bool:
	var order: Array = floor_tiles.duplicate()
	order.sort_custom(func(a: Vector2i, b: Vector2i) -> bool:
		return absi(a.x - target.x) < absi(b.x - target.x))
	var tries := mini(order.size(), 6)
	for i in tries:
		var from: Vector2i = order[i]
		for run_up in [0, 8, 16, 26, 40]:
			var got: bool = await _try_hop(from, target, run_up)
			if got:
				return true
	return false

## `hold_from` is how many frames of run-up to take before the jump: a standing
## jump and a running jump are different jumps, and only trying one of them is
## how a reachability check ends up more optimistic than the game.
func _try_hop(from: Vector2i, target: Vector2i, run_up: int) -> bool:
	reset_arena(0)
	boss.active = false            ## the hop question is geometry, not combat
	pl.control_enabled = true
	pl.dead = false
	pl.invuln = 999.0
	pl.hurt_t = 0.0
	pl.vel = Vector2.ZERO
	pl.pos = stand_pos(from)
	lvl.cam.snap_to_target()
	Tape.release_all()
	await frames(2)
	var toward := "right" if target.x >= from.x else "left"
	var got := false
	for f in 110:
		pl.invuln = 999.0
		pl.hurt_t = 0.0
		Game.health = Game.max_health
		var held: Array = [toward]
		# Hold jump for 18 frames from the end of the run-up: the human form
		# cuts a short hop, so a held press is the highest jump it has.
		if f >= run_up and f < run_up + 18:
			held.append("jump")
		Tape.apply(held)
		await get_tree().physics_frame
		if pl.on_floor and pl.last_floor_tile == target:
			got = true
			break
	Tape.release_all()
	pl.control_enabled = false
	boss.active = true
	return got

# ---------------------------------------------------------------- checks 1,2,5
## Puts Kaya where the strategy tape was recorded from. Everything about the
## start of the fight has to be identical or a tape is not a proof.
func fight_start_tile() -> Vector2i:
	var floor_tiles := _floor_tiles()
	if floor_tiles.is_empty():
		return Vector2i.ZERO
	floor_tiles.sort_custom(func(a: Vector2i, b: Vector2i) -> bool: return a.x < b.x)
	return floor_tiles[0]

func stage_fight() -> void:
	Game.reset_run()
	Game.sim_paused = false
	reset_arena(0)
	Tape.release_all()
	pl.control_enabled = false
	pl.input.clear()
	pl.dead = false
	pl.invuln = 0.0
	pl.hurt_t = 0.0
	pl.vel = Vector2.ZERO
	pl.pos = stand_pos(fight_start_tile())
	if pl.form_id != "human":
		pl.set_form("human")
	lvl.cam.snap_to_target()
	await frames(4)
	pl.control_enabled = true
	Game.health = Game.max_health

## Replays a recorded tape against the live fight. Returns what happened.
func replay(tape: Dictionary) -> Dictionary:
	var per_frame := Tape.decode(tape.get("frames", []) as Array)
	await stage_fight()
	var f := 0
	var killed_at := -1
	var min_health := Game.max_health
	while f < per_frame.size():
		Tape.apply(per_frame[f] as Array)
		await get_tree().physics_frame
		f += 1
		min_health = mini(min_health, Game.health)
		if boss.defeated and killed_at < 0:
			killed_at = f
			break
		if pl.dead or Game.health <= 0:
			break
	Tape.release_all()
	return {"frames": f, "killed_at": killed_at, "health": Game.health,
		"min_health": min_health, "dead": pl.dead,
		"boss_health": boss.health, "phase": int(boss.get("phase"))}

func check_tape() -> void:
	_current = "defeatable"
	var booted: bool = await boot()
	if not booted:
		return
	var tape := Tape.load_tape(tape_path)
	var stale := Tape.staleness(tape, level_id, boss_id)
	check(stale == "", "strategy tape %s: %s" % [tape_path, stale])
	if stale != "":
		say("  no usable strategy tape — checks 1 and 2 cannot run")
		return

	var n := Tape.frame_count(tape.get("frames", []) as Array)
	say("")
	say("  strategy tape: %d frames (%.1f s)" % [n, float(n) / 60.0])
	var r: Dictionary = await replay(tape)
	var secs := float(int(r["frames"])) / 60.0
	say("  replay: %d frames (%.1f s), boss health %d, phase %d, hearts %d (low %d)"
		% [int(r["frames"]), secs, int(r["boss_health"]), int(r["phase"]),
			int(r["health"]), int(r["min_health"])])

	check(int(r["killed_at"]) > 0,
		"the strategy tape did not kill the boss (health %d/%d left after %.1f s)"
			% [int(r["boss_health"]), boss.max_health, secs])
	check(secs <= DEFEAT_TIME_BOUND,
		"the fight took %.1f s, over the %.0f s bound" % [secs, DEFEAT_TIME_BOUND])

	_current = "survivable"
	check(not bool(r["dead"]), "Kaya died during the strategy tape")
	check(int(r["health"]) >= MIN_HEARTS_LEFT,
		("the tape wins with %d heart(s) left, not %d — a tape that only wins at "
		+ "zero is a coin flip, not a fight")
			% [int(r["health"]), MIN_HEARTS_LEFT])


## Check 5 is about the level around the fight, not the fight, so it does not
## wait on a strategy tape: the Warden is put down directly and the question is
## only whether the way out opens and can be walked to. Staging the kill is the
## point — an "it ends" that can only run after checks 1 and 2 pass tells you
## nothing on the day they fail.
func check_it_ends() -> void:
	_current = "it-ends"
	var ok: bool = await boot()
	if not ok:
		return
	await stage_fight()
	pl.control_enabled = false
	pl.invuln = 999.0
	boss.hurt(boss.health, boss.center() + Vector2(48.0, 0.0))
	# `die()` runs inside that call, so the flags are readable now — a few
	# frames later the node has queue_free'd itself and is gone.
	check(boss.defeated, "the boss did not report itself defeated when killed outright")
	check(not lvl.cam.locked, "the arena camera stayed locked after the boss fell")
	await frames(40)
	var out: Dictionary = await walk_to_exit()
	check(bool(out["completed"]),
		"after the boss fell, Kaya could not reach boss_exit from the arena floor "
			+ "(%s)" % String(out["why"]))
	say("  it ends: %s after %d frames (%.1f s)"
		% ["walked out through the gate" if bool(out["completed"])
			else "NEVER reached the gate", int(out["frames"]),
			float(int(out["frames"])) / 60.0])

## After the kill, put Kaya back on the arena floor and walk her out. The check
## is the outcome the player cares about — the level reports complete — not that
## an exit entity was spawned somewhere.
func walk_to_exit() -> Dictionary:
	var gate: LevelExit = null
	for n: Node in entity_children():
		if n is LevelExit:
			gate = n as LevelExit
			break
	if gate == null:
		return {"completed": false, "frames": 0, "why": "no exit was placed at all"}
	var target := gate.aabb().get_center().x
	_completed = false
	if not Game.level_completed.is_connected(_on_completed):
		Game.level_completed.connect(_on_completed)
	pl.control_enabled = true
	pl.dead = false
	pl.invuln = 999.0
	pl.hurt_t = 0.0
	pl.vel = Vector2.ZERO
	pl.pos = stand_pos(fight_start_tile())
	Tape.release_all()
	await frames(2)
	var f := 0
	while f < 900 and not _completed:
		pl.invuln = 999.0
		pl.hurt_t = 0.0
		Game.health = Game.max_health
		var to := target - pl.center().x
		var held: Array = []
		if to < -2.0:
			held.append("left")
		elif to > 2.0:
			held.append("right")
		# Only jump when something is actually in the way, so the walk stays a
		# walk and the check keeps meaning "she can get there on foot".
		if pl.against_wall != 0 and signi(pl.against_wall) == signi(to) and pl.on_floor:
			held.append("jump")
		Tape.apply(held)
		await get_tree().physics_frame
		f += 1
	Tape.release_all()
	Game.level_completed.disconnect(_on_completed)
	return {"completed": _completed, "frames": f,
		"why": "walked for %d frames and the level never reported complete" % f}

func _on_completed(_id: String) -> void:
	_completed = true

# ---------------------------------------------------------------- entry point
func run_all() -> int:
	var ok: bool = await boot()
	if not ok:
		_report()
		return 1
	say("BOSS GATE  %s in %s%s" % [String(boss.cfg.get("display_name", boss_id)), level_id,
		"  (quick)" if quick else ""])
	await check_fair()
	await check_tape()
	await check_it_ends()
	return _report()

func _report() -> int:
	say("")
	if failures.is_empty():
		say("boss gate: %d checks, ALL PASSED" % passes)
		return 0
	for f in failures:
		say("  FAIL  %s" % f)
	say("boss gate: %d checks, %d FAILED" % [passes + failures.size(), failures.size()])
	return 1
