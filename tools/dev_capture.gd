extends Node
## Autoload used only by tools/shot.sh — it is inert unless the game is started
## with `-- --scenario=...`. It drives the game with synthetic input and saves
## PNGs of the real viewport, which is how screenshots get produced without a
## human at the keyboard.
##
## Usage:
##   Godot --path . -- --scenario=title --out=shots/title.png --frames=40
##   Godot --path . -- --seq=tools/seq/level1.json
##
## Sequence steps (JSON array, executed in order):
##   {"scenario": "level:jungle_1"}      switch scene
##   {"wait": 30}                        wait N physics frames
##   {"hold": "move_right", "frames": 40}  hold an action for N frames
##   {"press": ["move_right","jump"], "frames": 12}
##   {"release": "move_right"}
##   {"shot": "shots/foo.png"}           capture the viewport
##   {"call": "toggle_debug"}            call a method on the current scene
##   {"teleport": [21, 24]}              move the player to a tile coordinate
##   {"log": "note"}                     print player tile + camera screen

const HOLDABLE := ["move_left", "move_right", "move_up", "move_down", "jump", "attack", "pause"]

var _steps: Array = []
var _step_i := 0
var _wait := 0
var _held: Array[String] = []
var _active := false
var _out := "shots/shot.png"
var _quit_when_done := true

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	# Main instantiates this; it is never an autoload, so it cannot break a
	# shipped build that does not include tools/.
	var args := _parse_args()
	if args.is_empty():
		return
	if args.has("itest"):
		# Integration mode: hand control to the in-game suite instead of the
		# capture sequencer.
		var script: GDScript = load("res://tests/integration/integration_tests.gd")
		if script == null or not script.can_instantiate():
			push_error("DevCapture: integration suite failed to compile")
			get_tree().quit(3)
			return
		var runner: Node = script.new()
		runner.name = "IntegrationTests"
		get_tree().root.add_child.call_deferred(runner)
		return
	_active = true
	if args.has("out"):
		_out = String(args["out"])
	if args.has("seq"):
		_steps = _load_seq(String(args["seq"]))
	else:
		var frames := int(args.get("frames", "40"))
		_steps = []
		if args.has("scenario"):
			_steps.append({"scenario": args["scenario"]})
		_steps.append({"wait": frames})
		_steps.append({"shot": _out})
	if args.has("noquit"):
		_quit_when_done = false

func _parse_args() -> Dictionary:
	var out := {}
	for a in OS.get_cmdline_user_args():
		if not a.begins_with("--"):
			continue
		var body := a.substr(2)
		var eq := body.find("=")
		if eq == -1:
			out[body] = "1"
		else:
			out[body.substr(0, eq)] = body.substr(eq + 1)
	return out

func _load_seq(path: String) -> Array:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("DevCapture: cannot read %s" % path)
		return []
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return parsed if typeof(parsed) == TYPE_ARRAY else []

func _physics_process(_delta: float) -> void:
	if not _active:
		return
	if _wait > 0:
		_wait -= 1
		return
	while _wait == 0 and _step_i < _steps.size():
		var step: Dictionary = _steps[_step_i]
		_step_i += 1
		if _run_step(step):
			return   # step is async (a capture); it resumes itself
	if _step_i >= _steps.size() and _wait <= 0:
		_finish()

func _run_step(step: Dictionary) -> bool:
	if step.has("scenario"):
		_release_all()
		_goto(String(step["scenario"]))
		_wait = int(step.get("settle", 6))
		return false
	if step.has("release"):
		for a in _as_list(step["release"]):
			_release(a)
		return false
	if step.has("hold") or step.has("press"):
		var acts := _as_list(step.get("hold", step.get("press", [])))
		for a in acts:
			_press(a)
		_wait = int(step.get("frames", 1))
		if step.get("sticky", false) == false and step.has("press"):
			# `press` auto-releases after its frames; `hold` stays down.
			_steps.insert(_step_i, {"release": acts})
		return false
	if step.has("shot"):
		_capture(String(step["shot"]))
		return true
	if step.has("touch"):
		var m: Node = Game.main
		if m != null and m.get("touch") != null:
			m.touch.force_enable(bool(step["touch"]))
		return false
	if step.has("touch_press"):
		# Synthesise a screen touch so the overlay can be shown mid-press.
		var t := InputEventScreenTouch.new()
		t.index = int(step.get("index", 0))
		var a: Array = step["touch_press"]
		t.position = Vector2(float(a[0]), float(a[1]))
		t.pressed = true
		Input.parse_input_event(t)
		return false
	if step.has("touch_drag"):
		var dg := InputEventScreenDrag.new()
		dg.index = int(step.get("index", 0))
		var b: Array = step["touch_drag"]
		dg.position = Vector2(float(b[0]), float(b[1]))
		Input.parse_input_event(dg)
		return false
	if step.has("log"):
		var lvl0: Node = Game.current_level
		if lvl0 and lvl0.get("player") != null:
			var pl0: Actor = lvl0.player
			var t0 := (pl0.center() / TileData4.TILE_SIZE).floor()
			print("[log] %s player_tile=%v pos=%v vel=%v on_floor=%s screen=%v" % [
				String(step["log"]), t0, pl0.pos.round(), pl0.vel.round(),
				str(pl0.on_floor), lvl0.cam.screen])
		return false
	if step.has("teleport"):
		var t: Array = step["teleport"]
		var lvl: Node = Game.current_level
		if lvl and lvl.get("player") != null:
			var pl: Actor = lvl.player
			pl.pos = Vector2(float(t[0]), float(t[1])) * TileData4.TILE_SIZE
			pl.vel = Vector2.ZERO
			if lvl.get("cam") != null:
				lvl.cam.snap_to_target()
				lvl._on_screen_changed(lvl.cam.screen)
		_wait = int(step.get("settle", 4))
		return false
	if step.has("call"):
		var scene: Node = Game.main.current_scene() if Game.main else null
		if scene and scene.has_method(String(step["call"])):
			scene.call(String(step["call"]))
		return false
	if step.has("wait"):
		_wait = int(step["wait"])
		return false
	return false

func _as_list(v: Variant) -> Array[String]:
	var out: Array[String] = []
	if typeof(v) == TYPE_ARRAY:
		for e: Variant in v:
			out.append(String(e))
	else:
		out.append(String(v))
	return out

func _press(action: String) -> void:
	if action in HOLDABLE and not _held.has(action):
		Input.action_press(action)
		_held.append(action)

func _release(action: String) -> void:
	if _held.has(action):
		Input.action_release(action)
		_held.erase(action)

func _release_all() -> void:
	for a in _held.duplicate():
		_release(a)

func _goto(scenario: String) -> void:
	if scenario == "title":
		Game.goto_title()
	elif scenario == "hub":
		Game.reset_run()
		Game.goto_hub()
	elif scenario.begins_with("level:"):
		Game.reset_run()
		Game.goto_level(scenario.substr(6))
	elif scenario == "gameover":
		Game.goto_game_over()
	elif scenario == "victory":
		Game.goto_victory()
	else:
		push_error("DevCapture: unknown scenario '%s'" % scenario)

func _capture(path: String) -> void:
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var dir := path.get_base_dir()
	if dir != "" and not DirAccess.dir_exists_absolute(dir):
		DirAccess.make_dir_recursive_absolute(dir)
	var err := img.save_png(path)
	print("[capture] %s (%dx%d) err=%d" % [path, img.get_width(), img.get_height(), err])
	if _step_i >= _steps.size():
		_finish()

func _finish() -> void:
	_active = false
	_release_all()
	if _quit_when_done:
		get_tree().quit()
