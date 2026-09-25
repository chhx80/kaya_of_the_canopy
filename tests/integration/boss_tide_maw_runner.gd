extends Node
## Headless entry point for tests/integration/boss_tide_maw_tests.gd.
##
## That suite drives the real game — autoloads, the Level scene, the camera, the
## player's own form code — and `--headless --script` has neither autoloads nor
## a scene tree (ADR 003). So this boots src/core/main.tscn as a child, which is
## what sets `Game.main`, and hands control to the suite. Same shape as
## tests/integration/enemies_v2_runner.gd and tools/bossgate/bossgate_runner.gd,
## for the same reason.
##
## It exists because the suite is not part of tools/itest.sh: wiring it in means
## editing tests/integration/integration_tests.gd, which this branch does not
## own. Until that happens, this is how the suite is run at all — see REPORT.md.
##
##   $GODOT --headless --path . res://tests/integration/boss_tide_maw_runner.tscn
##
## Exit code is the gate: 0 every check passed, 1 something failed.
##
## `KAYA_TIDE_MODE=record` runs tests/integration/boss_tide_maw_strategy.gd
## instead and writes tools/bossgate/tapes/tide_maw.json — the strategy tape
## ADR 005's checks 1 and 2 replay. It needs `--fixed-fps 60`, like
## tools/bossgate.sh, so ninety seconds of fight is not ninety seconds of wall
## clock. Configuration is an environment variable rather than a `--` user arg
## because user args are what switch tools/dev_capture.gd into screenshot mode.

## Loaded at run time, not preloaded: a parse error in the suite then reports
## itself here and exits, instead of taking this script down with it and leaving
## a headless process with nothing to quit it.
const SUITE := "res://tests/integration/boss_tide_maw_tests.gd"
const CHECKS := "res://tests/integration/boss_gate_checks.gd"
const STRATEGY := "res://tests/integration/boss_tide_maw_strategy.gd"
const TAPE := "res://tests/integration/boss_gate_tape.gd"
const TAPE_PATH := "res://tools/bossgate/tapes/tide_maw.json"

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var main: PackedScene = load("res://src/core/main.tscn")
	add_child(main.instantiate())
	call_deferred("_run")

func _run() -> void:
	if OS.get_environment("KAYA_TIDE_MODE") == "record":
		get_tree().quit(await _record())
		return
	var script: GDScript = load(SUITE)
	if script == null or not script.can_instantiate():
		push_error("boss_tide_maw: %s failed to compile" % SUITE)
		get_tree().quit(3)
		return
	var suite: Node = script.new()
	suite.name = "TideMawRun"
	add_child(suite)
	get_tree().quit(await suite.run_all())

## Fights the Maw with the policy in boss_tide_maw_strategy.gd and writes the
## result out as a tape. A losing run is not written: a tape that does not win
## is not a proof, and a stale one that does is worse than none.
func _record() -> int:
	var checks: Node = (load(CHECKS) as GDScript).new()
	checks.level_id = "ruins_5"
	checks.boss_id = "tide_maw"
	checks.tape_path = TAPE_PATH
	checks.name = "TideMawGate"
	add_child(checks)
	var ok: bool = await checks.boot()
	if not ok:
		for f in checks.failures:
			print("  FAIL  %s" % f)
		return 1
	var rec: Node = (load(STRATEGY) as GDScript).new()
	rec.name = "TideMawStrategy"
	add_child(rec)
	var tape: Dictionary = await rec.record(checks)
	var outcome: Dictionary = tape["outcome"]
	if not bool(outcome["boss_defeated"]) or bool(outcome["kaya_dead"]) \
			or int(outcome["hearts_left"]) < 1:
		print("  no tape written: the run did not win with a heart to spare.")
		return 1
	if not (load(TAPE) as GDScript).save(TAPE_PATH, tape):
		return 1
	print("  wrote %s" % TAPE_PATH)
	return 0
