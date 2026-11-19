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
##   {"setting": ["music", 0.0]}         change a saved setting (affects the next scenario)
##   {"log": "note"}                     print player/camera state and the
##                                        nearest enemy's health/_flash/_hold_t
##                                        (Phase D: staging a hit-hold or
##                                        landing-dip capture without guessing
##                                        a frame count from outside)
##   {"perf": "label", "frames": 240}    measure frame cost and print it
##   {"route_perf": "jungle_1"}          play the level's proof tape through real input
##   {"route_perf": "res://tests/fixtures/x.json"}  ...or a fixture's, by path, and
##                                       time every frame of it (docs/plan-longer-levels.md)
##   {"bench": "res://tests/fixtures/x.json", "iters": 600}  time, in isolation, each
##                                       per-frame path that could grow with level area
##   {"perf": "label", "cap": 60}        ...with the frame rate held at 60, the
##                                        way a phone runs it: every frame then
##                                        carries a physics tick, so per-frame
##                                        physics/process/render cost is honest
##   {"lighting": false}                 phase 3 ambience off, for an A/B perf run
##   {"tap": "pause"}                    a real touch on the overlay's pause
##                                        button, in window pixels through the
##                                        root's stretch; logs whether it opened
##   {"tap": "menu:LEAVE LEVEL"}         ...or on a row of the open pause menu;
##                                        logs where the game went
##   {"tap": "pause", "index": 1}        ...as the second finger on the glass
##   {"thumb": true}                     rest a finger (index 0) on the stick's
##                                        home in window pixels; false lifts it
##   {"tape": "jungle_1", "shots": "shots/x_%d.png", "every": 150, "max": 4, "skip": 0}
##                                        boot the level and play its real proof
##                                        tape (Kaya unhittable, as in the replay
##                                        tier), shooting every N sim frames —
##                                        the camera mid-run on real play. The
##                                        tree is paused for each capture, so a
##                                        shot never adds frames to the tape
##   {"tape": "jungle_1", "contacts": true}  ...and print a [contact] line each
##                                        time an enemy or a hostile shot first
##                                        overlaps her: where a player who
##                                        ignores the enemies would be hit
##   {"cleared": ["jungle_1", ...]}      stage a save: those flags set, rest wiped
##   {"cleared": "all"}                  ...or every gateway on the overworld
##
## `{"scenario": "hub"}` walks in at the spawn; `{"scenario": "hub:nest_5"}` walks
## in standing at that gateway, the way the game places you when you come back out
## of a level — which is the only way to photograph a door's label and prompt
## without steering the walker across half the map first.

const HOLDABLE := ["move_left", "move_right", "move_up", "move_down", "jump", "attack", "pause"]

var _steps: Array = []
var _step_i := 0
var _wait := 0
var _held: Array[String] = []
var _active := false
var _busy := false            ## an async step (a perf run) owns the sequencer
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
	if not _active or _busy:
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
			print("[log] %s player_tile=%v pos=%v vel=%v on_floor=%s view=%v locked=%s frozen=%s cam=%v dip=%v" % [
				String(step["log"]), t0, pl0.pos.round(), pl0.vel.round(),
				str(pl0.on_floor), lvl0.cam.view_rect().position, str(lvl0.cam.locked),
				str(Game.sim_paused), lvl0.cam.position, lvl0.cam.dip_offset])
		# Phase D authoring aid: the nearest enemy's own combat state, so a hit
		# -hold/hit-spark capture can be staged by watching health/_flash/
		# _hold_t tick instead of guessing a frame count from outside.
		var nearest: Enemy = null
		var best := INF
		for n in get_tree().get_nodes_in_group(&"enemies"):
			var e := n as Enemy
			if e == null or not is_instance_valid(e):
				continue
			var d := 0.0
			if lvl0 and lvl0.get("player") != null:
				d = e.center().distance_to((lvl0.player as Actor).center())
			if d < best:
				best = d
				nearest = e
		if nearest != null:
			print("[log]   nearest enemy health=%d _flash=%.3f _hold_t=%.3f pos=%v" % [
				nearest.health, nearest._flash, nearest._hold_t, nearest.pos.round()])
		return false
	if step.has("teleport"):
		var t: Array = step["teleport"]
		var lvl: Node = Game.current_level
		if lvl and lvl.get("player") != null:
			var pl: Actor = lvl.player
			pl.pos = Vector2(float(t[0]), float(t[1])) * TileData4.TILE_SIZE
			pl.vel = Vector2.ZERO
			# Re-frame and settle who is awake on the spot: the follow camera
			# would otherwise pan there, and a teleport into a boss arena is
			# what (re)starts the fight a capture is staged on.
			if lvl.has_method("settle_view"):
				lvl.settle_view()
		_wait = int(step.get("settle", 4))
		return false
	if step.has("setting"):
		var kv: Array = step["setting"]
		SaveManager.set_setting(String(kv[0]), kv[1])
		return false
	if step.has("call"):
		var scene: Node = Game.main.current_scene() if Game.main else null
		if scene and scene.has_method(String(step["call"])):
			scene.call(String(step["call"]))
		return false
	if step.has("lighting"):
		Ambience.lighting = bool(step["lighting"])
		return false
	if step.has("cleared"):
		# Stage a save. The overworld reads SaveManager to decide which gateways
		# are open and what "CLEARED n/25" says, so a capture of a mid-game or
		# end-game hub has to set the flags BEFORE the scene loads.
		SaveManager.wipe()
		var want: Array[String] = []
		if typeof(step["cleared"]) == TYPE_STRING and String(step["cleared"]) == "all":
			for id in Game.hub_levels():
				want.append(id)
		else:
			want = _as_list(step["cleared"])
		for id: String in want:
			SaveManager.set_flag(id, true)
		SaveManager.save()
		print("[cleared] %d flag(s) staged" % want.size())
		return false
	if step.has("tape"):
		_play_tape(String(step["tape"]), String(step.get("shots", "")),
			int(step.get("every", 150)), int(step.get("max", 4)), int(step.get("skip", 0)),
			bool(step.get("contacts", false)))
		return true   # async, like perf
	if step.has("bench"):
		_bench(String(step["bench"]), int(step.get("iters", 600)))
		return true   # async
	if step.has("route_perf"):
		_route_perf(String(step["route_perf"]))
		return true   # async
	if step.has("perf"):
		_measure(String(step["perf"]), int(step.get("frames", 240)), int(step.get("cap", 0)))
		return true   # async; _measure clears _busy and the sequencer resumes
	if step.has("wait"):
		_wait = int(step["wait"])
		return false
	if step.has("tap"):
		_tap(String(step["tap"]), int(step.get("index", 4)))
		return true   # async: down, two frames, up
	if step.has("thumb"):
		var tc: Control = Game.main.get("touch")
		tc.call("force_enable", true)
		var ev := InputEventScreenTouch.new()
		ev.index = 0
		ev.position = get_tree().root.get_final_transform() * (tc.get("_stick_home") as Vector2)
		ev.pressed = bool(step["thumb"])
		Input.parse_input_event(ev)
		print("[thumb] %s window=%s" % ["down" if ev.pressed else "up", str(ev.position)])
		return false
	return false

## A real touch at a control the game draws, injected in WINDOW pixels — the
## coordinates a finger produces — and converted from the control's logical
## position through the root's own stretch transform. The integration tier taps
## in logical pixels on a headless 1:1 window, so it cannot see a stretch that
## puts input somewhere other than the picture; this can, at any --res.
## `"pause"` taps the touch overlay's pause button and logs whether the menu
## opened; `"menu:<ROW>"` taps that row of the open pause menu and logs where
## the game is afterwards.
func _tap(what: String, index: int) -> void:
	_busy = true
	var touch: Control = Game.main.get("touch")
	touch.call("force_enable", true)
	await get_tree().process_frame
	var logical: Vector2 = touch.call("pause_button_centre")
	var ui_node: Node = Game.main.get("ui") as Node
	if what.begins_with("menu:"):
		var menu: Node = ui_node.get_node_or_null("PauseScreen")
		var row: int = (menu.get("ITEMS") as Array).find(what.substr(5)) if menu != null else -1
		if row < 0:
			print("[tap] %s: no pause menu, or no such row" % what)
			_busy = false
			return
		var W := Screen.ui_size(get_viewport()).x
		logical = Vector2(W * 0.5, float(menu.get("ROW0_Y")) + float(menu.get("ROW_H")) * (float(row) + 0.5))
	var root := get_tree().root
	var to_window := root.get_final_transform()
	var at := to_window * logical
	print("[tap] window_size=%s root.size=%s visible=%s final=%s screen=%s ds_scale=%s" % [
		str(DisplayServer.window_get_size()), str(root.size), str(root.get_visible_rect()),
		str(root.get_final_transform()), str(root.get_screen_transform()),
		str(DisplayServer.screen_get_scale())])
	for pressed: bool in [true, false]:
		var ev := InputEventScreenTouch.new()
		ev.index = index
		ev.position = at
		ev.pressed = pressed
		Input.parse_input_event(ev)
		# Rendered frames, not physics ticks: Main polls the pause action in
		# _process, and at startup physics catches up several ticks a frame.
		for _i in 3:
			await get_tree().process_frame
	var opened: bool = ui_node.has_node("PauseScreen")
	print("[tap] %s logical=%s window=%s stretch=%s -> pause menu %s, state=%s level=\"%s\"" % [
		what, str(logical), str(at), str(to_window.get_scale()),
		"OPENED" if opened else "NOT OPENED", Game.State.keys()[Game.state], Game.current_level_id])
	_busy = false
	if _step_i >= _steps.size():
		_finish()

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
	elif scenario.begins_with("hub:"):
		# Stand at a named gateway, exactly as coming back out of that level does.
		Game.reset_run()
		Game.goto_hub(scenario.substr(4))
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
	# Hurt, she blinks (player.gd hides the sprite in half of each 0.16 s of
	# i-frames); a still that lands on the hidden half shows a level with no
	# hero in it. Show her for the frame that is captured.
	var lvl: Node = Game.current_level
	if lvl != null and is_instance_valid(lvl) and lvl.get("player") != null:
		var sp: Variant = lvl.player.get("sprite")
		if sp is CanvasItem:
			(sp as CanvasItem).visible = true
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var dir := path.get_base_dir()
	if dir != "" and not DirAccess.dir_exists_absolute(dir):
		DirAccess.make_dir_recursive_absolute(dir)
	var err := img.save_png(path)
	# The physics frame is printed because a capture is not free: it costs a few
	# ticks, so "wait 40 then shoot" twice is not 80 ticks apart. Sequences that
	# have to land on a specific moment are timed off these numbers.
	print("[capture] %s (%dx%d) err=%d frame=%d" % [
		path, img.get_width(), img.get_height(), err, Engine.get_physics_frames()])
	if _step_i >= _steps.size():
		_finish()

## Plays a proof tape (tests/integration/replay_tape.gd) through the real input
## path and shoots it. Frames are sim frames, exactly as in tape_replay.gd: a
## hitstop tick holds the buttons and spends no tape.
func _play_tape(id: String, pattern: String, every: int, max_shots: int, skip: int,
		contacts: bool = false) -> void:
	_busy = true
	var loader: GDScript = load("res://tests/integration/replay_tape.gd")
	var tape: RefCounted = loader.call("load_for", id)
	if not bool(tape.call("ok")):
		print("[tape] %s: %s" % [id, String(tape.get("error"))])
		_end_async()
		return
	Game.reset_run()
	Game.goto_level(id)
	for _i in 4:
		await get_tree().physics_frame
	var sim := 0
	var taken := 0
	for hop: Dictionary in (tape.get("hops") as Array):
		for st: Dictionary in (hop["steps"] as Array):
			var acts: Array = st["actions"]
			var left := int(st["n"])
			while left > 0:
				for a in _held.duplicate():
					if not acts.has(StringName(a)):
						_release(a)
				for a: StringName in acts:
					_press(String(a))
				var lvl: Node = Game.current_level
				if lvl == null or lvl.get("player") == null or Game.state != Game.State.LEVEL:
					print("[tape] %s left the level at sim frame %d" % [id, sim])
					_end_async()
					return
				lvl.player.set("invuln", 1.0)
				await get_tree().physics_frame
				# A capture holds the tree (see _process): no node ticked, so
				# no tape frame is spent and no button changes.
				while get_tree().paused:
					await get_tree().physics_frame
				if Game.sim_paused:
					continue
				left -= 1
				sim += 1
				var now: Node = Game.current_level
				if contacts and now != null and is_instance_valid(now):
					_log_contacts(now.get("player") as Actor, sim, String(hop["to"]))
				if pattern != "" and taken < max_shots and sim > skip and (sim - skip) % every == 0:
					_tape_shot = pattern % taken
					taken += 1
	print("[tape] %s played %d sim frames, %d shot(s)" % [id, sim, taken])
	_end_async()

## Contact log for `"contacts": true`: one line per enemy (keyed by its
## spawn tile) or per volley of shots, re-armed after a second clear of it.
var _last_contact: Dictionary = {}

func _log_contacts(pl: Actor, sim: int, hop_to: String) -> void:
	if pl == null or not is_instance_valid(pl):
		return
	var box := pl.aabb()
	var hits: Array[String] = []
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e != null and e.active and e.aabb().intersects(box):
			hits.append("%s@%s" % [e.enemy_id, str(Vector2i((e.spawn_pos / TileData4.TILE_SIZE).floor()))])
	for n in get_tree().get_nodes_in_group(&"hostile_shots"):
		if n.has_method("aabb") and (n.call("aabb") as Rect2).intersects(box):
			hits.append("shot")
	for key in hits:
		if sim - int(_last_contact.get(key, -9999)) > 60:
			print("[contact] t=%.1fs before %s: %s, Kaya at %s" % [float(sim) / 60.0, hop_to,
				key, str(Vector2i((pl.center() / TileData4.TILE_SIZE).floor()))])
		_last_contact[key] = sim

## The tape's capture point. Requested from inside the physics-frame await,
## where pausing would swallow the tick that is about to run; taken here
## instead, at idle, after that tick has run with the buttons the replay
## tier would have held.
var _tape_shot := ""

func _process(_delta: float) -> void:
	if _tape_shot == "" or get_tree().paused:
		return
	var path := _tape_shot
	_tape_shot = ""
	get_tree().paused = true
	# Held invulnerable, she is mid-blink on every tick (player.gd hides the
	# sprite in half of each 0.16 s of i-frames). The tree is paused, so
	# showing her for the shot changes nothing the tape can see.
	var lvl: Node = Game.current_level
	if lvl != null and lvl.get("player") != null:
		var sp: Variant = lvl.player.get("sprite")
		if sp is CanvasItem:
			(sp as CanvasItem).visible = true
	await _snap(path)
	get_tree().paused = false

func _snap(path: String) -> void:
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var dir := path.get_base_dir()
	if dir != "" and not DirAccess.dir_exists_absolute(dir):
		DirAccess.make_dir_recursive_absolute(dir)
	print("[capture] %s err=%d frame=%d" % [path, img.save_png(path), Engine.get_physics_frames()])

func _end_async() -> void:
	_release_all()
	_busy = false
	if _step_i >= _steps.size():
		_finish()

## Frame cost along a whole route: what a level of a given SIZE costs, for the
## longer-levels pilot (docs/plan-longer-levels.md). Loads the level by id or by
## res:// path, plays its proof tape through Input exactly as the capture `tape`
## step does (Kaya held invulnerable, hitstop spends no tape), and samples every
## physics tick: the engine's own physics and process times, and -- when there
## is a renderer -- the world viewport's render CPU/GPU time and the draw calls.
## Uncapped and vsync off, as `perf` runs, so a windowed run also reports the
## wall time of every rendered frame. Headless (no renderer) the render columns
## read 0 and the script cost is the whole story.
const _TAPE_ACTIONS := {1: "move_left", 2: "move_right", 4: "move_up", 8: "move_down",
	16: "jump", 32: "attack"}
## Ticks dropped from the front of a route_perf sample: the level's first
## frames build chunks and upload art, which is load cost, not frame cost.
const _ROUTE_PERF_WARMUP := 30

## Brackets one tick's script work: a node that runs first (lowest priority)
## and one that runs last, each stamping the clock. The difference is what every
## _physics_process (or _process) in the tree cost this tick -- tighter than the
## engine's monitors, which also count the engine's own stepping.
class _Stamp extends Node:
	var start: Array = [0]           ## shared with the pair's other half
	var samples: Array[float] = []   ## filled by the last-running half, in ms
	var first := true
	var physics := true
	func _ready() -> void:
		process_mode = Node.PROCESS_MODE_ALWAYS
	func _physics_process(_d: float) -> void:
		if physics:
			_stamp_now()
	func _process(_d: float) -> void:
		if not physics:
			_stamp_now()
	func _stamp_now() -> void:
		var now := Time.get_ticks_usec()
		if first:
			start[0] = now
		elif int(start[0]) > 0:
			samples.append(float(now - int(start[0])) / 1000.0)

func _stamp(physics: bool, first: bool, start: Array, samples: Array[float]) -> _Stamp:
	var s := _Stamp.new()
	s.physics = physics
	s.first = first
	s.start = start
	s.samples = samples
	if physics:
		s.process_physics_priority = -100000 if first else 100000
	else:
		s.process_priority = -100000 if first else 100000
	get_tree().root.add_child(s)
	return s

func _route_perf(id: String) -> void:
	_busy = true
	var level_path := id if id.begins_with("res://") else LevelLoader.level_path(id)
	var frames := ProverTape.frames(ProverTape.tape_path_for(level_path), level_path)
	if frames.is_empty():
		print("[route_perf] %s: no fresh tape (%s)" % [id,
			ProverTape.staleness(ProverTape.tape_path_for(level_path), level_path)])
		_end_async()
		return
	Game.reset_run()
	Game.goto_level(id)
	for _i in 30:
		await get_tree().physics_frame
	var lvl: Node = Game.current_level
	var w: TileWorld = lvl.get("world") if lvl != null else null
	var vp := get_viewport()
	var rid := RID()
	var wvp: Variant = Game.main.get("world_viewport") if Game.main != null else null
	if wvp is SubViewport:
		rid = (wvp as SubViewport).get_viewport_rid()
		RenderingServer.viewport_set_measure_render_time(rid, true)
	var old_vsync := DisplayServer.window_get_vsync_mode()
	var old_max := Engine.max_fps
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	var phys: Array[float] = []
	var proc: Array[float] = []
	var wcpu := 0.0
	var wgpu := 0.0
	var calls := 0.0
	var frame_ms: Array[float] = []
	var counter := [0, Time.get_ticks_usec()]
	var on_draw := func() -> void:
		var now := Time.get_ticks_usec()
		frame_ms.append(float(now - int(counter[1])) / 1000.0)
		counter[1] = now
	RenderingServer.frame_post_draw.connect(on_draw)
	var tick_ms: Array[float] = []
	var idle_ms: Array[float] = []
	var ps: Array = [0]
	var qs: Array = [0]
	var probes: Array[Node] = [_stamp(true, true, ps, tick_ms), _stamp(true, false, ps, tick_ms),
		_stamp(false, true, qs, idle_ms), _stamp(false, false, qs, idle_ms)]
	var sim := 0
	var i := 0
	var completed := false
	while i < frames.size():
		var bits := frames[i]
		for b: int in _TAPE_ACTIONS.keys():
			if bits & b:
				_press(String(_TAPE_ACTIONS[b]))
			else:
				_release(String(_TAPE_ACTIONS[b]))
		lvl = Game.current_level
		if lvl == null or lvl.get("player") == null or Game.state != Game.State.LEVEL:
			completed = Game.state == Game.State.HUB
			break
		lvl.player.set("invuln", 1.0)
		await get_tree().physics_frame
		phys.append(Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0)
		proc.append(Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0)
		calls += Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
		if rid.is_valid():
			wcpu += RenderingServer.viewport_get_measured_render_time_cpu(rid)
			wgpu += RenderingServer.viewport_get_measured_render_time_gpu(rid)
		if Game.sim_paused:
			continue
		i += 1
		sim += 1
	RenderingServer.frame_post_draw.disconnect(on_draw)
	for pr in probes:
		pr.queue_free()
	_release_all()
	DisplayServer.window_set_vsync_mode(old_vsync)
	Engine.max_fps = old_max
	if rid.is_valid():
		RenderingServer.viewport_set_measure_render_time(rid, false)
	var n := maxi(1, phys.size())
	for a: Array[float] in [frame_ms, tick_ms, idle_ms]:
		if a.size() > _ROUTE_PERF_WARMUP:
			var rest := a.slice(_ROUTE_PERF_WARMUP)
			a.clear()
			a.append_array(rest)
	print("[route_perf] %s tiles=%s tape_frames=%d sampled=%d completed=%s | script_physics_ms %s | script_process_ms %s | engine physics_ms %s | engine process_ms %s | frame_ms %s (%d drawn) | world_cpu=%.3f world_gpu=%.3f draw_calls=%.0f | nodes=%d" % [
		id, "%dx%d" % [w.width, w.height] if w != null else "?", frames.size(), phys.size(),
		str(completed or Game.state == Game.State.HUB), _dist(tick_ms), _dist(idle_ms),
		_dist(phys.slice(mini(phys.size(), _ROUTE_PERF_WARMUP))),
		_dist(proc.slice(mini(proc.size(), _ROUTE_PERF_WARMUP))), _dist(frame_ms),
		frame_ms.size(), wcpu / n, wgpu / n, calls / n,
		int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT))])
	_end_async()

## The per-frame paths that walk something sized by the LEVEL rather than by
## the view, each called `iters` times on a level that has settled with Kaya
## mid-route, and timed per call in microseconds: every pickup's tick, the wake
## pass over every enemy, both tile layers' animation pass, a scroll of one
## tile (the cull change that re-collects live animations and light pools), and
## the whole tree's canvas items. Compare a 50x30 row with its 200x45 twin.
func _bench(id: String, iters: int) -> void:
	_busy = true
	Game.reset_run()
	Game.goto_level(id)
	for _i in 20:
		await get_tree().physics_frame
	var lvl: Node = Game.current_level
	var w: TileWorld = lvl.get("world")
	var pl: Actor = lvl.get("player")
	# Mid-level, on the floor: the same relative spot in either size.
	pl.pos = Vector2(w.pixel_width() * 0.5, pl.pos.y)
	lvl.call("settle_view")
	for _i in 20:
		await get_tree().physics_frame
	var pickups := get_tree().get_nodes_in_group(&"pickups")
	var enemies := get_tree().get_nodes_in_group(&"enemies")
	var tiles_fg: Node = lvl.get("tiles_fg")
	var tiles_bg: Node = lvl.get("tiles_bg")
	var lights: Node = lvl.get("lights")
	var cam: Node = lvl.get("cam")
	var r: Rect2 = cam.call("view_rect")
	var out := {}
	var t := Time.get_ticks_usec()
	# What the engine would tick: only the pickups the level has left awake.
	var awake := pickups.filter(func(n: Node) -> bool: return n.is_physics_processing())
	for _i in iters:
		for n in awake:
			n.call("_physics_process", 1.0 / 60.0)
	out["pickups"] = Time.get_ticks_usec() - t
	t = Time.get_ticks_usec()
	for _i in iters:
		lvl.call("_update_wake")
	out["wake"] = Time.get_ticks_usec() - t
	t = Time.get_ticks_usec()
	for _i in iters:
		tiles_fg.call("_process", 1.0 / 60.0)
		tiles_bg.call("_process", 1.0 / 60.0)
	out["tile_anim"] = Time.get_ticks_usec() - t
	t = Time.get_ticks_usec()
	for i in iters:
		var step := Vector2(float(TileData4.TILE_SIZE) * float(i % 2), 0.0)
		lvl.call("_on_view_changed", Rect2(r.position + step, r.size))
	out["scroll_tile"] = Time.get_ticks_usec() - t
	lvl.call("_on_view_changed", r)
	print("[bench] %s tiles=%dx%d pickups=%d(%d awake) enemies=%d chunks=%d emissive=%d | us/call: pickups=%.1f wake=%.1f tile_anim=%.1f scroll_one_tile=%.1f" % [
		id, w.width, w.height, pickups.size(), awake.size(), enemies.size(),
		tiles_fg.get_child_count() + tiles_bg.get_child_count(),
		(lights.get("_emissive_all") as Array).size(),
		float(out["pickups"]) / iters, float(out["wake"]) / iters,
		float(out["tile_anim"]) / iters, float(out["scroll_tile"]) / iters])
	_end_async()

static func _dist(a: Array[float]) -> String:
	if a.is_empty():
		return "-"
	var s := a.duplicate()
	s.sort()
	var sum := 0.0
	for v: float in s:
		sum += v
	return "avg=%.3f p50=%.3f p95=%.3f max=%.3f" % [sum / s.size(), s[s.size() / 2],
		s[int(s.size() * 0.95)], s[s.size() - 1]]

## Frame cost, for the phase 3 lighting decision (docs/art-direction.md).
##
## Three numbers, because they answer different questions. `frame` is wall clock
## between two finished frames with vsync off and the fps cap lifted — the only
## figure that says whether a change costs frame rate. `cpu` and `gpu` are the
## renderer's own timings for the viewport, which is what separates "we are
## submitting too much" from "we are filling too many pixels"; lighting shows up
## in `gpu`. Draw calls are printed because that is the number a phone minds
## most.
##
## Physics stays at 60Hz throughout, so uncapping the frame rate changes what is
## measured but not what is simulated.
func _measure(label: String, frames: int, cap: int = 0) -> void:
	_busy = true
	var vp := get_viewport()
	var rid := vp.get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(rid, true)
	# The world draws into its own SubViewport, which the root's timings do
	# not include. Timed separately so a fill-rate change shows up where it is.
	var wrid := RID()
	var wvp: Variant = Game.main.get("world_viewport") if Game.main != null else null
	if wvp is SubViewport:
		wrid = (wvp as SubViewport).get_viewport_rid()
		RenderingServer.viewport_set_measure_render_time(wrid, true)
	var old_vsync := DisplayServer.window_get_vsync_mode()
	var old_max := Engine.max_fps
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = cap
	for _i in 45:                       # warm up: shaders, atlas uploads, tween settle
		await RenderingServer.frame_post_draw
	var samples: Array[float] = []
	var cpu := 0.0
	var gpu := 0.0
	var calls := 0.0
	var phys := 0.0
	var proc := 0.0
	var wcpu := 0.0
	var wgpu := 0.0
	var last := Time.get_ticks_usec()
	for _i in frames:
		await RenderingServer.frame_post_draw
		var now := Time.get_ticks_usec()
		samples.append(float(now - last) / 1000.0)
		last = now
		cpu += RenderingServer.viewport_get_measured_render_time_cpu(rid)
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(rid)
		if wrid.is_valid():
			wcpu += RenderingServer.viewport_get_measured_render_time_cpu(wrid)
			wgpu += RenderingServer.viewport_get_measured_render_time_gpu(wrid)
		calls += Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
		phys += Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0
		proc += Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
	samples.sort()
	var n := samples.size()
	var sum := 0.0
	for v in samples:
		sum += v
	var vram := Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0
	print("[perf] %s cap=%d frames=%d frame_ms avg=%.3f p50=%.3f p95=%.3f max=%.3f | render_cpu=%.3f render_gpu=%.3f | world_cpu=%.3f world_gpu=%.3f | physics_ms=%.3f process_ms=%.3f | draw_calls=%.0f vram=%.1fMB" % [
		label, cap, n, sum / maxf(1.0, float(n)), samples[n / 2], samples[int(n * 0.95)],
		samples[n - 1], cpu / float(n), gpu / float(n), wcpu / float(n), wgpu / float(n),
		phys / float(n), proc / float(n), calls / float(n), vram])
	DisplayServer.window_set_vsync_mode(old_vsync)
	Engine.max_fps = old_max
	RenderingServer.viewport_set_measure_render_time(rid, false)
	if wrid.is_valid():
		RenderingServer.viewport_set_measure_render_time(wrid, false)
	_busy = false
	if _step_i >= _steps.size():
		_finish()

func _finish() -> void:
	_active = false
	_release_all()
	if _quit_when_done:
		get_tree().quit()
