extends Node
## Headless entry point for THE STORMCREST's strategy tape and for
## tests/integration/boss_stormcrest_tests.gd.
##
## It exists for the reason tests/integration/boss_tide_maw_runner.gd does, and
## it is deliberately the same shape: `tools/bossgate/bossgate_runner.gd`
## preloads ONE pen — `boss_gate_strategy.gd`, the Grove Warden's — so the way a
## second boss was added without touching the Warden's was a runner of its own,
## and this is the third. `tools/bossgate.sh --level=heights_5 --boss=stormcrest`
## still runs the whole gate: only *recording* is boss-specific, because only
## the policy is.
##
##   $GODOT --headless --fixed-fps 60 --path . \
##       res://tests/integration/boss_stormcrest_runner.tscn
##
## Exit code is the gate: 0 every check passed, 1 something failed.
##
##   KAYA_CREST_MODE=record   fight it with boss_stormcrest_strategy.gd and write
##                            tools/bossgate/tapes/stormcrest.json
##   KAYA_CREST_KNOBS={...}   one named policy setting, no search
##   KAYA_CREST_TRACE=1       a line of the fight every second
##
## `--fixed-fps 60` matters: it unhitches the main loop from the wall clock so
## the physics delta stays exactly 1/60 and ninety seconds of fight is not ninety
## seconds of sitting here. Configuration is an environment variable rather than
## a `--` user arg because user args are what switch tools/dev_capture.gd into
## screenshot mode.

## Loaded at run time, not preloaded: a parse error in the suite then reports
## itself here and exits, instead of taking this script down with it and leaving
## a headless process with nothing to quit it.
const SUITE := "res://tests/integration/boss_stormcrest_tests.gd"
const CHECKS := "res://tests/integration/boss_gate_checks.gd"
const STRATEGY := "res://tests/integration/boss_stormcrest_strategy.gd"
const TAPE := "res://tests/integration/boss_gate_tape.gd"
const TAPE_PATH := "res://tools/bossgate/tapes/stormcrest.json"
const LEVEL := "heights_5"
const BOSS := "stormcrest"

## ADR 005's check 2 passes at one heart left, and one heart is a bad thing to
## aim at. The search below stops at a win that keeps this many, and writes the
## best win it saw if none does — the bar THE TIDE MAW's tape set.
const WANT_HEARTS := 3

## Four structurally different openings. A single greedy descent locks onto
## whichever knob it improved first; these are hand-picked policies rather than a
## coordinate descent because this fight has a clock in it (the roost cycle) and
## the knobs that matter are the ones that decide where she waits out a lap.
const SEEDS := [
	{},
	{"near": 76.0, "far": 104.0},
	{"near": 48.0, "far": 80.0, "throw_min": 24.0},
	{"under_gap": 64.0, "panic_hold": 40},
	{"dodge_lead": 0.42, "jump_hold": 22},
	{"near": 88.0, "far": 112.0, "under_gap": 72.0},
]

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var main: PackedScene = load("res://src/core/main.tscn")
	add_child(main.instantiate())
	call_deferred("_run")

func _run() -> void:
	if OS.get_environment("KAYA_CREST_MODE") == "record":
		get_tree().quit(await _record())
		return
	var script: GDScript = load(SUITE)
	if script == null or not script.can_instantiate():
		push_error("boss_stormcrest: %s failed to compile" % SUITE)
		get_tree().quit(3)
		return
	var suite: Node = script.new()
	suite.name = "StormcrestRun"
	add_child(suite)
	get_tree().quit(await suite.run_all())

## Fights it with the policy in boss_stormcrest_strategy.gd and writes the result
## out as a tape. A losing run is not written: a tape that does not win is not a
## proof, and a stale one that does is worse than none.
func _record() -> int:
	var checks: Node = (load(CHECKS) as GDScript).new()
	checks.level_id = LEVEL
	checks.boss_id = BOSS
	checks.tape_path = TAPE_PATH
	checks.name = "StormcrestGate"
	add_child(checks)
	var ok: bool = await checks.boot()
	if not ok:
		for f in checks.failures:
			print("  FAIL  %s" % f)
		return 1
	var rec: Node = (load(STRATEGY) as GDScript).new()
	rec.name = "StormcrestStrategy"
	add_child(rec)

	var fixed := OS.get_environment("KAYA_CREST_KNOBS")
	var trials: Array = SEEDS
	if fixed != "":
		var parsed: Variant = JSON.parse_string(fixed)
		if typeof(parsed) != TYPE_DICTIONARY:
			print("  FAIL  KAYA_CREST_KNOBS is not a JSON object: %s" % fixed)
			return 1
		trials = [parsed as Dictionary]

	var best: Dictionary = {}
	for i in trials.size():
		var knobs: Dictionary = trials[i]
		if i > 0:
			# A losing attempt ends with Kaya dead, and the level answers that on
			# its own clock: died -> 0.9 s -> lose_life -> restart_level, which
			# swaps the whole level out from under the next attempt. Let that
			# finish, then boot a clean one.
			await checks.frames(75)
			var booted: bool = await checks.boot()
			if not booted:
				print("    could not re-boot the arena; stopping here")
				break
		rec.configure(knobs)
		print("    try %d  %s" % [i + 1, JSON.stringify(knobs)])
		var t: Dictionary = await rec.record(checks)
		if _acceptable(t) and _better(t, best):
			best = t
		if _won(t):
			break

	if best.is_empty():
		print("  No tape written: a tape that does not win is not a proof.")
		return 1
	var outcome: Dictionary = best["outcome"]
	if int(outcome["hearts_left"]) < WANT_HEARTS:
		print("  %d strategies tried and none kept %d hearts; writing the best win:"
			% [trials.size(), WANT_HEARTS])
	print("  %d frames (%.1f s), %d hearts left, lowest %d"
		% [int(best["recorded_frames"]), float(int(best["recorded_frames"])) / 60.0,
			int(outcome["hearts_left"]), int(outcome["lowest_hearts"])])
	if not (load(TAPE) as GDScript).save(TAPE_PATH, best):
		return 1
	print("  wrote %s" % TAPE_PATH)
	return 0

## Good enough to write down: exactly what the gate will accept, no more.
func _acceptable(t: Dictionary) -> bool:
	var o: Dictionary = t["outcome"]
	return bool(o["boss_defeated"]) and not bool(o["kaya_dead"]) \
		and int(o["hearts_left"]) >= 1

func _won(t: Dictionary) -> bool:
	return _acceptable(t) \
		and int((t["outcome"] as Dictionary)["hearts_left"]) >= WANT_HEARTS

## Fewer hearts lost first, then a shorter fight: a tape is a demonstration, and
## one that dawdles demonstrates the wrong thing.
func _better(t: Dictionary, than: Dictionary) -> bool:
	if than.is_empty():
		return true
	var a: Dictionary = t["outcome"]
	var b: Dictionary = than["outcome"]
	if int(a["hearts_left"]) != int(b["hearts_left"]):
		return int(a["hearts_left"]) > int(b["hearts_left"])
	return int(t["recorded_frames"]) < int(than["recorded_frames"])
