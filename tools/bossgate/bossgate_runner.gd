extends Node
## Headless entry point for the Boss Gate (ADR 005, section 4).
##
## The gate needs the *real* game: autoloads, a Level scene, the boss node, the
## blade, projectiles. `--headless --script` has neither autoloads nor a scene
## tree, so this boots src/core/main.tscn as a child — which is what registers
## Game.main — and then hands control to tests/integration/boss_gate_checks.gd.
##
## Configuration comes from the environment rather than from `--` user args,
## because user args are what switch tools/dev_capture.gd into screenshot mode.
##
##   KAYA_BOSSGATE_LEVEL   level id            (default jungle_5)
##   KAYA_BOSSGATE_BOSS    boss enemy id       (default boss_grove)
##   KAYA_BOSSGATE_MODE    check | record      (default check)
##   KAYA_BOSSGATE_QUICK   1 to thin the sweep (default full)
##   KAYA_BOSSGATE_TAPE    tape path           (default res://tools/bossgate/tapes/<boss>.json)

const Checks := preload("res://tests/integration/boss_gate_checks.gd")
const Strategy := preload("res://tests/integration/boss_gate_strategy.gd")
const Tape := preload("res://tests/integration/boss_gate_tape.gd")
const Smoke := preload("res://tests/integration/boss_gate_smoke.gd")

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var main: PackedScene = load("res://src/core/main.tscn")
	add_child(main.instantiate())
	call_deferred("_run")

func _env(key: String, fallback: String) -> String:
	var v := OS.get_environment(key)
	return v if v != "" else fallback

func _run() -> void:
	var t0 := Time.get_ticks_msec()
	var checks: Node = Checks.new()
	checks.level_id = _env("KAYA_BOSSGATE_LEVEL", "jungle_5")
	checks.boss_id = _env("KAYA_BOSSGATE_BOSS", "boss_grove")
	checks.quick = _env("KAYA_BOSSGATE_QUICK", "") != ""
	checks.tape_path = _env("KAYA_BOSSGATE_TAPE",
		"res://tools/bossgate/tapes/%s.json" % checks.boss_id)
	checks.name = "BossGateChecks"
	add_child(checks)

	var code := 0
	var mode := _env("KAYA_BOSSGATE_MODE", "check")
	if mode == "smoke":
		code = await _smoke(checks)
	elif mode == "probe":
		code = await _probe(checks)
	elif mode == "record":
		code = await _record(checks)
	else:
		code = await checks.run_all()
	print("boss gate: %.1fs wall" % ((Time.get_ticks_msec() - t0) / 1000.0))
	get_tree().quit(code)

## Runs the bounded in-suite case on its own, so its cost can be measured the
## way tools/itest.sh would pay it — at wall-clock speed, with no --fixed-fps.
func _smoke(checks: Node) -> int:
	var s: Node = Smoke.new()
	s.level_id = checks.level_id
	s.boss_id = checks.boss_id
	s.tape_path = checks.tape_path
	add_child(s)
	var code: int = await s.run_all()
	for f in s.failures:
		print("  FAIL  %s" % f)
	print("boss gate smoke: %d checks, %s"
		% [s.passes + s.failures.size(),
			"ALL PASSED" if s.failures.is_empty() else "%d FAILED" % s.failures.size()])
	return code

## A measuring stick, not a gate: prints what the blade does to the boss at a
## range of distances. Used to work out why a strategy was losing.
func _probe(checks: Node) -> int:
	var ok: bool = await checks.boot()
	if not ok:
		return 1
	var rec: Node = Strategy.new()
	add_child(rec)
	if OS.get_environment("KAYA_BOSSGATE_PROBE") == "adds":
		await rec.probe_adds(checks)
	else:
		await rec.probe_blade(checks)
	return 0

## Authoring the strategy tape is a search, not a hand. The policy in
## boss_gate_strategy.gd has a dozen knobs; this walks them one at a time,
## keeping whatever setting fought better, and stops the moment a run kills the
## Warden with a heart to spare. What gets written out is that run's buttons —
## the knobs are scaffolding and do not appear in the tape.
const KNOBS := [
	["near", [30.0, 40.0, 48.0, 56.0, 64.0, 80.0]],
	["far", [56.0, 72.0, 92.0, 108.0]],
	["under_trigger", [56.0, 70.0, 84.0, 112.0]],
	["under_min", [16.0, 30.0, 44.0]],
	["under_hold", [26, 36, 44, 64]],
	["jump_hold", [14, 18, 22, 26]],
	["dodge_lead", [0.20, 0.26, 0.32, 0.40]],
	["dodge_late", [0.06, 0.11, 0.16]],
	["panic_hold", [8, 20, 34, 56]],
	["add_jump_gap", [18.0, 26.0, 34.0, 44.0]],
	["throw_min", [16.0, 22.0, 28.0, 40.0]],
	["throw_max", [88.0, 100.0, 112.0, 118.0]],
	["use_under", [true, false]],
	["add_mode", [0, 1]],
	["hop_mode", [true, false]],
	["hop_period", [30, 38, 44, 52]],
	["throw_airborne", [true, false]],
]
const PASSES := 3

## Damage dealt dominates deliberately. An earlier weighting scored survival
## highly enough that the search settled on a strategy which never threw the
## blade at all: it survived the full ninety seconds and dealt one damage, and
## every later trial was measured against that. Staying alive is worth
## something only while she is also fighting.
func _score(t: Dictionary) -> float:
	var o: Dictionary = t["outcome"]
	var dealt := 18 - int(o["boss_health"])
	var s := float(dealt) * 40.0 + float(int(o["hearts_left"])) * 4.0
	if bool(o["boss_defeated"]):
		s += 1000.0
	if bool(o["kaya_dead"]):
		s -= 40.0
	return s

func _won(t: Dictionary) -> bool:
	var o: Dictionary = t["outcome"]
	return bool(o["boss_defeated"]) and not bool(o["kaya_dead"]) \
		and int(o["hearts_left"]) >= 1

## Four structurally different openings, because a single greedy descent locks
## onto whichever knob it improved first and never looks at the others again:
## seeded with the hop strategy it settled three whole hearts worse than the
## default and never climbed back out.
const SEEDS := [
	{},
	{"hop_mode": true, "throw_airborne": true},
	{"use_under": false, "near": 96.0, "far": 112.0},
	{"add_mode": 1, "near": 48.0},
]

var _tries := 0
var _best: Dictionary = {}
var _best_score := -1e9

func _record(checks: Node) -> int:
	var ok: bool = await checks.boot()
	if not ok:
		print("  FAIL  could not boot %s" % checks.level_id)
		return 1
	var rec: Node = Strategy.new()
	rec.name = "BossGateStrategy"
	add_child(rec)

	for seed_i in SEEDS.size():
		var won: bool = await _descend(checks, rec, SEEDS[seed_i], seed_i)
		if won:
			return _write(checks, _best, _tries)
	var o: Dictionary = _best["outcome"] if _best.has("outcome") else {}
	print("  %d strategies tried; the best left the Warden on %s health with Kaya on %s."
		% [_tries, str(o.get("boss_health", "?")), str(o.get("hearts_left", "?"))])
	print("  No tape written: a tape that does not win is not a proof.")
	return 1

## Greedy coordinate descent from one opening. Returns true if it won.
func _descend(checks: Node, rec: Node, seed: Dictionary, seed_i: int) -> bool:
	var params: Dictionary = seed.duplicate()
	var local := -1e9
	print("    seed %d: %s" % [seed_i, JSON.stringify(seed)])
	for pass_i in PASSES:
		for knob: Array in KNOBS:
			var key: String = knob[0]
			for v: Variant in (knob[1] as Array):
				var trial := params.duplicate()
				trial[key] = v
				if trial == params and _tries > 0:
					continue
				rec.configure(trial)
				# A losing attempt ends with Kaya dead, and the level answers
				# that on its own clock: died -> 0.9 s -> lose_life ->
				# restart_level, which swaps the whole level out from under the
				# next attempt. Let that finish, then boot a clean one.
				await checks.frames(75)
				var booted: bool = await checks.boot()
				if not booted:
					print("    could not re-boot the arena; stopping the search")
					return false
				var t: Dictionary = await rec.record(checks)
				_tries += 1
				var sc := _score(t)
				if sc > local:
					local = sc
					params = trial
				if sc > _best_score:
					_best_score = sc
					_best = t
					print("      try %3d  %-14s = %-6s  ->  warden %2d hp, kaya %d hearts%s"
						% [_tries, key, str(v),
							int((t["outcome"] as Dictionary)["boss_health"]),
							int((t["outcome"] as Dictionary)["hearts_left"]),
							"  WIN" if _won(t) else ""])
				if _won(t):
					_best = t
					return true
	return false

func _write(checks: Node, tape: Dictionary, tries: int) -> int:
	var outcome: Dictionary = tape["outcome"]
	print("  won on try %d: %d frames (%.1f s), %d hearts left, lowest %d"
		% [tries, int(tape["recorded_frames"]), float(int(tape["recorded_frames"])) / 60.0,
			int(outcome["hearts_left"]), int(outcome["lowest_hearts"])])
	if not Tape.save(checks.tape_path, tape):
		return 1
	print("  wrote %s" % checks.tape_path)
	return 0
