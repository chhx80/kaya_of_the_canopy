extends Node
## Headless entry point for tests/integration/enemies_v2_tests.gd.
##
## That suite drives the real game — autoloads, a Level scene, the camera, the
## blade — and `--headless --script` has neither autoloads nor a scene tree
## (ADR 003). So this boots src/core/main.tscn as a child, which is what sets
## `Game.main`, and then hands control to the suite. It is the same shape as
## tools/bossgate/bossgate_runner.gd, for the same reason.
##
## It exists because the suite is not part of tools/itest.sh: wiring it in
## means editing tests/integration/integration_tests.gd, which this branch does
## not own. Until that happens, this is how the suite is run at all — see
## REPORT.md.
##
##   $GODOT --headless --path . res://tests/integration/enemies_v2_runner.tscn
##
## Exit code is the gate: 0 every check passed, 1 something failed.
##
## `KAYA_V2_MODE=shot` runs tests/integration/enemies_v2_shot.gd instead, which
## needs a window. Configuration is an environment variable rather than a `--`
## user arg because user args are what switch tools/dev_capture.gd into
## screenshot mode — the same reason tools/bossgate.sh uses the environment.

## Loaded at run time, not preloaded: a parse error in the suite then reports
## itself here and exits, instead of taking this script down with it and
## leaving a headless process with nothing to quit it.
const SUITE := "res://tests/integration/enemies_v2_tests.gd"
const SHOT := "res://tests/integration/enemies_v2_shot.gd"

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var main: PackedScene = load("res://src/core/main.tscn")
	add_child(main.instantiate())
	call_deferred("_run")

func _run() -> void:
	var path: String = SHOT if OS.get_environment("KAYA_V2_MODE") == "shot" else SUITE
	var script: GDScript = load(path)
	if script == null or not script.can_instantiate():
		push_error("enemies_v2: %s failed to compile" % path)
		get_tree().quit(3)
		return
	var suite: Node = script.new()
	suite.name = "EnemiesV2Run"
	add_child(suite)
	if path != SUITE:
		return   # the shot script drives and quits itself
	get_tree().quit(await suite.run_all())
