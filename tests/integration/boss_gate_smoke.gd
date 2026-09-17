extends Node
## The Boss Gate's in-suite case, bounded to fit tools/itest.sh.
##
## WHAT THIS IS NOT: it is not the gate. The fairness sweep visits every
## standable tile in the arena in every phase, which is about forty-five minutes
## of simulated fight — affordable only because tools/bossgate.sh starts Godot
## with `--fixed-fps 60`, which unhitches the main loop from the wall clock
## while leaving the physics delta at exactly 1/60. tools/itest.sh does not pass
## that flag, so the same sweep would take three quarters of an hour of real
## time inside the suite.
##
## So this case proves the *harness* is alive in-engine and nothing more:
##   - the arena has standable tiles, found with the real collision code
##   - the Warden attacks, and the sweep sees the attack land on a tile
##   - the boss stays inside arena_min/arena_max while it does
##   - after it dies the gate opens and Kaya can walk out of it
##   - the strategy tape, if there is one, is not stale
##
## The verdict — is this fight fair, is it winnable, does it end — comes from
## `tools/bossgate.sh`, and this file deliberately does not restate it. A green
## suite here is not a claim that the Grove Warden passed its gate.
##
## Not wired into tests/integration/integration_tests.gd: this branch does not
## own that file. To wire it in, add to `run_all()`'s list:
##     "t_boss_gate_smoke",
## and the method:
##     func t_boss_gate_smoke() -> void:
##         var s: Node = (load("res://tests/integration/boss_gate_smoke.gd") as GDScript).new()
##         add_child(s)
##         await s.run_all()
##         passes += s.passes
##         failures.append_array(s.failures)
##         s.queue_free()

const Checks := preload("res://tests/integration/boss_gate_checks.gd")
const Tape := preload("res://tests/integration/boss_gate_tape.gd")

## One tile, one phase. Enough to show the sweep can tell a hit from a miss:
## two slams at the Warden's 2.4 s STOMP interval, plus the drain that lets the
## second shockwave arrive.
const SAMPLE_CAP := 700

var level_id := "jungle_5"
var boss_id := "boss_grove"
var tape_path := "res://tools/bossgate/tapes/boss_grove.json"

var passes := 0
var failures: PackedStringArray = PackedStringArray()

var _g: Node = null

func check(cond: bool, msg: String) -> void:
	if cond:
		passes += 1
	else:
		failures.append("boss_gate_smoke :: %s" % msg)

func run_all() -> int:
	_g = Checks.new()
	_g.level_id = level_id
	_g.boss_id = boss_id
	_g.tape_path = tape_path
	_g.name = "BossGateHarness"
	add_child(_g)

	var ok: bool = await _g.boot()
	check(ok, "jungle_5 did not boot with %s in it" % boss_id)
	if not ok:
		return 1

	var tiles: Array = _g.standable_tiles()
	check(tiles.size() > 0, "the arena reports no standable tile")
	if tiles.is_empty():
		return 1

	# The tile nearest the Warden, so the slam is certain to reach it inside
	# the sample: this case is checking that the sweep *works*, not that the
	# fight is fair.
	var target: Vector2i = _nearest_floor_tile(tiles)
	var obs: Dictionary = await _g.watch_tile(0, target, 2, SAMPLE_CAP)
	var attacks: Dictionary = obs["attacks"]
	check(not attacks.is_empty(),
		"the Warden made no attack at all in %d frames — the sweep would have "
			% SAMPLE_CAP + "nothing to say about any tile")
	var connects := 0
	for tag: String in attacks.keys():
		connects += int((attacks[tag] as Dictionary)["connects"])
	check(connects > 0,
		"nothing the Warden did connected with Kaya standing at (%d,%d), right "
			% [target.x, target.y] + "next to it — the sweep cannot detect a hit")
	check(int(obs["escapes"]) == 0,
		"the Warden left arena_min/arena_max or its screen on %d frame(s)"
			% int(obs["escapes"]))

	# Check 5, whole, because it is cheap: put the boss down and walk out.
	await _g.stage_fight()
	_g.pl.control_enabled = false
	_g.pl.invuln = 999.0
	_g.boss.hurt(_g.boss.health, _g.boss.center() + Vector2(48.0, 0.0))
	check(_g.boss.defeated, "the Warden did not report itself defeated when killed")
	check(not _g.lvl.cam.locked, "the arena camera stayed locked after it fell")
	await _g.frames(40)
	var out: Dictionary = await _g.walk_to_exit()
	check(bool(out["completed"]),
		"after the Warden fell, Kaya could not walk to boss_exit (%s)"
			% String(out["why"]))

	# Not "there is a winning tape" — that is bossgate.sh's verdict — but "the
	# tape on disk still matches the level and the boss it was recorded against".
	# A tape that has quietly gone stale is worse than no tape.
	var tape := Tape.load_tape(tape_path)
	if not tape.is_empty():
		var stale := Tape.staleness(tape, level_id, boss_id)
		check(stale == "", "the strategy tape is stale: %s" % stale)
	return 0 if failures.is_empty() else 1

func _nearest_floor_tile(tiles: Array) -> Vector2i:
	var lowest := -1
	for t: Vector2i in tiles:
		lowest = maxi(lowest, t.y)
	var best: Vector2i = tiles[0]
	var bx := 1e9
	var boss_tile := int(_g.boss.center().x / 16.0)
	for t: Vector2i in tiles:
		if t.y != lowest:
			continue
		var d := absf(float(t.x - boss_tile))
		if d < bx:
			bx = d
			best = t
	return best
