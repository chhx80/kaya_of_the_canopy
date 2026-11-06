extends RefCounted
## Replays a proof tape (ADR 005 §3) against the real, booted Level.
##
## The prover proves the *geometry* is traversable. This proves the *level* —
## enemies alive, doors shut, triggers armed, the real camera waking them —
## can actually be finished, because a machine finished it. Nothing here models
## anything: the tape's buttons go in through `InputState` exactly as a thumb's
## would, and the only thing asserted at the end is an outcome.
##
## This class only *plays* the tape and reports where it ended up. Which outcome
## counts as a pass is the caller's, because it is not the same on every level:
## on an ordinary level it is `Game` reporting the level complete, and on a boss
## level a traversal tape cannot reach that and must not claim it — see
## `check_boss_arrival()` in integration_tests.gd.
##
## Frames are *simulation* frames. `Game.sim_paused` is true for the length of
## every hitstop (a kill), and on those ticks the player does not read its input
## at all — so a paused tick must not eat a tape frame, or a tape would desync by
## the width of every freeze. The buttons stay held across it, which is what a
## thumb does too. (The screen flip used to freeze the sim as well; the follow
## camera never does, and the camera audit below fails a replay if anything but
## hitstop ever freezes it.)
##
## THE CAMERA AUDIT. Every tape is a whole level played through the real
## camera, which makes it the widest net the suite has for camera outcomes, so
## each simulated frame is also checked for what a player would see go wrong:
## a freeze that is not hitstop, a view that jumps instead of scrolling, Kaya
## outside the view, an ordinary enemy awake and acting far off the view, and
## one sitting frozen where she can see it. The counts land in the result and
## the caller asserts them (integration_tests.gd, check_camera_audit()).

const TAPE := "res://tests/integration/replay_tape.gd"
const TS := 16.0

## Frames granted after the tape runs out, so a landing or a trigger that fires
## on the tick after the last button has somewhere to happen. No input is held
## during them: they cannot move the player anywhere the tape did not.
const SETTLE_FRAMES := 12

var _tree: SceneTree = null

## Replay Kaya unhittable, and say so.
##
## ADR 005 promised this tier would prove the real level "with enemies alive".
## It cannot, and integration is what showed it: the prover does not simulate
## enemies, so its tape has Kaya walking through them — and one hit does not
## merely cost health, it DESYNCHRONISES THE WHOLE TAPE. player.gd clears the
## input for the duration of hurt_t, so every press after the first contact
## lands on a different frame than the one it was recorded for. Measured: all
## six levels failed, test_arena included, and that level is one screen with a
## single walker.
##
## So the tier proves what it can actually prove — that the recorded buttons
## drive the REAL level to completion through real doors, real switches, real
## transform pads and the real screen-flip freeze — and does not pretend to
## prove survival. Making that honest is the point of the flag; hiding it
## behind a passing gate is how six broken levels shipped.
var invulnerable := true
## A single-frame view move larger than this is a jump, not a scroll. The
## fastest thing the camera follows is a falling body (340 px/s, 5.7 px a
## frame) and the arena ease peaks at pi/2 x its distance over its duration;
## both stay well inside it.
const MAX_VIEW_STEP_PX := 12.0
## The audit's own definition of "far off the view": ten tiles past the screen
## edge. Deliberately NOT read from data/camera.json — an audit that took its
## bound from the tunable it audits passes whatever the tunable says (measured:
## a 5000 px sleep margin sailed through jungle_2 that way).
const FAR_OFF_VIEW_PX := 160.0
var _held: Array[StringName] = []
var trace := false

func _init(tree: SceneTree) -> void:
	_tree = tree

# ------------------------------------------------------------------ input
func _press(a: StringName) -> void:
	if not _held.has(a):
		Input.action_press(a)
		_held.append(a)

func _release_all() -> void:
	for a in _held.duplicate():
		Input.action_release(a)
	_held.clear()

## Exactly the buttons named, and nothing else, held into the next tick.
func _set_actions(actions: Array) -> void:
	for a in _held.duplicate():
		if not actions.has(a):
			Input.action_release(a)
			_held.erase(a)
	for a: StringName in actions:
		_press(a)

# ------------------------------------------------------------------ audit
var _last_view := Vector2(-1, -1)

## Reads the live level rather than the one the replay booted: completing a
## level frees it, and the audit runs on that frame too.
func _audit(r: Dictionary) -> void:
	var lvl: Node = Game.current_level
	if lvl == null or not is_instance_valid(lvl) or lvl.get("cam") == null:
		return
	var cam: CameraController = lvl.get("cam")
	var pl: Node = _player()
	if cam == null or pl == null:
		return
	if Game.sim_paused and not Fx.hitstop_active():
		r["cam_frozen"] = int(r["cam_frozen"]) + 1
	var v := cam.view_rect()
	if _last_view.x >= 0.0:
		var step := (v.position - _last_view).length()
		if step > float(r["cam_max_step"]):
			r["cam_max_step"] = step
	_last_view = v.position
	# Locked in an arena the view stops at the arena edge and she may stand a
	# few pixels past it before the lock lets go: only an unlocked view must
	# always hold her.
	if not cam.locked and not v.has_point((pl as Actor).center()):
		r["cam_lost_kaya"] = int(r["cam_lost_kaya"]) + 1
	for n in _tree.get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e == null or e.level != lvl or e.is_in_group(&"bosses"):
			continue
		if e.active and not v.grow(FAR_OFF_VIEW_PX).intersects(e.aabb()):
			r["enemy_awake_far"] = int(r["enemy_awake_far"]) + 1
			r["cam_note"] = "%s awake at %s, view %s" % [e.enemy_id, str(e.pos.round()), str(v.position)]
		elif not e.active and e.visible and v.intersects(e.aabb()):
			r["enemy_frozen_visible"] = int(r["enemy_frozen_visible"]) + 1
			r["cam_note"] = "%s frozen in view at %s" % [e.enemy_id, str(e.pos.round())]

# ------------------------------------------------------------------ replay
## Returns a result dictionary. `completed` is the only thing a caller should
## treat as a pass; everything else exists to make a failure readable.
func replay(tape: RefCounted) -> Dictionary:
	var id: String = tape.level_id
	var r := {
		"completed": false, "died": false, "level_id": id,
		"sim_frames": 0, "real_frames": 0, "hop": 0, "step": 0,
		"hop_desc": "", "end_tile": Vector2i(-1, -1), "end_form": "",
		"health": 0, "closest_px": -1.0, "goal_tile": Vector2i(-1, -1),
		"note": "",
		"cam_frozen": 0, "cam_max_step": 0.0, "cam_lost_kaya": 0,
		"enemy_awake_far": 0, "enemy_frozen_visible": 0, "cam_note": "",
	}

	_release_all()
	SaveManager.set_flag(id, false)

	var done := [false]
	var on_complete := func(completed_id: String) -> void:
		if completed_id == id:
			done[0] = true
	Game.level_completed.connect(on_complete)

	Game.reset_run()
	Game.goto_level(id)
	# The level builds during _ready; give it the frames the rest of the suite
	# gives it before believing anything about the player.
	for _i in 4:
		await _tree.physics_frame

	var lvl: Node = Game.current_level
	if lvl == null or lvl.get("player") == null:
		Game.level_completed.disconnect(on_complete)
		r["note"] = "level '%s' did not boot a player" % id
		return r

	var goal := _goal_point(lvl, tape)
	r["goal_tile"] = Vector2i((goal / TS).floor())
	var closest := INF

	# A tape that needs four times its own length of wall clock is not being
	# replayed, it is hanging. This is the bound that makes a failure a failure.
	var real_budget: int = tape.total_frames * 4 + 600
	var sim_frames := 0
	var real_frames := 0
	var aborted := false

	for hop_i in tape.hops.size():
		if aborted or done[0]:
			break
		var hop: Dictionary = tape.hops[hop_i]
		r["hop"] = hop_i
		r["hop_desc"] = "%s -> %s as %s" % [hop["from"], hop["to"], hop["form"]]
		var steps: Array = hop["steps"]
		for step_i in steps.size():
			if aborted or done[0]:
				break
			r["step"] = step_i
			var step: Dictionary = steps[step_i]
			var actions: Array = step["actions"]
			var n: int = step["n"]
			var left := n
			while left > 0:
				_set_actions(actions)
				if invulnerable:
					var pl: Node = _player()
					if pl != null:
						pl.set("invuln", 1.0)
				await _tree.physics_frame
				real_frames += 1
				if real_frames > real_budget:
					r["note"] = "replay ran %d frames for a %d-frame tape and never finished" \
						% [real_frames, tape.total_frames]
					aborted = true
					break
				_audit(r)
				# A frozen sim is a hitstop. Hold the buttons, spend no tape.
				if Game.sim_paused:
					continue
				left -= 1
				sim_frames += 1
				var p: Node = _player()
				if p != null:
					closest = minf(closest, p.center().distance_to(goal))
					r["end_tile"] = Vector2i((p.center() / TS).floor())
					r["end_form"] = String(p.form_id)
					if bool(p.dead):
						r["died"] = true
						r["note"] = "Kaya died on tape frame %d" % sim_frames
						aborted = true
						break
				if done[0]:
					break
				if Game.state != Game.State.LEVEL:
					r["note"] = "left the level (state %d) without completing it" % Game.state
					aborted = true
					break
			if trace:
				var p2: Node = _player()
				print("[tape] %s hop %d step %d a=%-18s f=%d tile=%s as %-5s pos=%s vel=%s hp=%d" % [
					id, hop_i, step_i, _names(actions), sim_frames,
					str(r["end_tile"]), String(r["end_form"]),
					str(p2.pos.round()) if p2 != null else "-",
					str(p2.vel.round()) if p2 != null else "-",
					Game.health])

	# Let a trigger that armed on the final tick actually fire.
	_release_all()
	var settle := 0
	while not done[0] and settle < SETTLE_FRAMES and Game.state == Game.State.LEVEL:
		await _tree.physics_frame
		settle += 1
		real_frames += 1
		if Game.sim_paused:
			continue
		var p3: Node = _player()
		if p3 != null:
			closest = minf(closest, p3.center().distance_to(goal))
			r["end_tile"] = Vector2i((p3.center() / TS).floor())
			if bool(p3.dead):
				r["died"] = true

	Game.level_completed.disconnect(on_complete)
	_release_all()

	r["completed"] = done[0]
	r["sim_frames"] = sim_frames
	r["real_frames"] = real_frames
	r["health"] = Game.health
	r["closest_px"] = -1.0 if closest == INF else closest
	return r

func _player() -> Node:
	var lvl: Node = Game.current_level
	if lvl == null or not is_instance_valid(lvl):
		return null
	var p: Variant = lvl.get("player")
	if p == null or not is_instance_valid(p as Node):
		return null
	return p as Node

## Where the tape is trying to end up, in world pixels. Used only to say how
## close a failed replay got — the same number the prover reports when a hop
## fails, so the two failures read alike.
##
## It is the *tape's own* last waypoint, not always the exit, because a tape no
## longer always aims at one: a boss level's traversal tape ends on the arena
## floor, and measuring it against a `boss_exit` that only exists once the boss
## is dead reports a distance to a place that is not there. The waypoint is an
## entity type, a named mark, or — when the tape names something this level does
## not have — the exit, so the readout degrades to the old one instead of to
## nothing.
func _goal_point(lvl: Node, tape: RefCounted) -> Vector2:
	var def: Variant = lvl.get("def")
	if def == null:
		return Vector2.ZERO
	var want := ""
	if not tape.hops.is_empty():
		want = String((tape.hops[tape.hops.size() - 1] as Dictionary).get("to", ""))

	if want != "":
		for e: Dictionary in (def.entities as Array):
			if String(e.get("type", "")) == want:
				return Vector2(float(e.get("px", 0.0)), float(e.get("py", 0.0))) + Vector2(8, 8)
		var mark: Variant = _mark(String(def.id), want)
		if mark != null:
			return mark as Vector2

	for e: Dictionary in (def.entities as Array):
		var t := String(e.get("type", ""))
		if t == "exit" or t == "boss_exit":
			return Vector2(float(e.get("px", 0.0)), float(e.get("py", 0.0))) + Vector2(8, 8)
	return Vector2.ZERO

## A named mark from the level file, in world pixels, or null. `LevelDef` does
## not carry `marks` — they are authoring waypoints, not gameplay — so this
## reads the level json the same way the prover does.
func _mark(level_id: String, name: String) -> Variant:
	var f := FileAccess.open("res://levels/%s.json" % level_id, FileAccess.READ)
	if f == null:
		return null
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		return null
	var marks: Variant = (parsed as Dictionary).get("marks", null)
	if typeof(marks) != TYPE_DICTIONARY or not (marks as Dictionary).has(name):
		return null
	var m: Dictionary = (marks as Dictionary)[name]
	return Vector2(float(m.get("x", 0)) * TS, float(m.get("y", 0)) * TS) + Vector2(8, 8)

static func _names(actions: Array) -> String:
	if actions.is_empty():
		return "-"
	var out: PackedStringArray = PackedStringArray()
	for a: StringName in actions:
		out.append(String(a).replace("move_", ""))
	return "+".join(out)

## One line that says what happened, for a failure message.
static func describe(r: Dictionary) -> String:
	var bits: PackedStringArray = PackedStringArray()
	bits.append("hop %d (%s) step %d" % [r["hop"], r["hop_desc"], r["step"]])
	bits.append("%d sim frames" % r["sim_frames"])
	# The form matters as much as the tile: a hop recorded for one form replayed
	# in another is a whole class of failure, and it looks like "stuck" without
	# this.
	bits.append("ended at tile %s as %s" % [str(r["end_tile"]), String(r["end_form"])])
	bits.append("goal tile %s" % str(r["goal_tile"]))
	if float(r["closest_px"]) >= 0.0:
		bits.append("closest %.1f px" % float(r["closest_px"]))
	bits.append("health %d" % r["health"])
	if bool(r["died"]):
		bits.append("DIED")
	if String(r["note"]) != "":
		bits.append(String(r["note"]))
	return " | ".join(bits)
