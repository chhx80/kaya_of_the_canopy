extends Node
## Runs the prover's simulation and the real booted game on the SAME tape, one
## frame at a time, and reports the first frame where they stop agreeing.
##
## The prover says a level is playable. The replay tier says the recorded buttons
## do not finish it. Exactly one of them is wrong, and nothing else in the
## project can say which — so this steps them side by side until they part.

const EPS := 0.75            ## px; below this is float noise, not divergence
const ACTS: Array[StringName] = [&"move_left", &"move_right", &"move_up",
	&"move_down", &"jump", &"attack"]
const BITS := [1, 2, 4, 8, 16, 32]

var _held: Array[StringName] = []


func _ready() -> void:
	var ids: Array[String] = []
	for a in OS.get_cmdline_user_args():
		if not a.begins_with("--"):
			ids.append(a)
	if ids.is_empty():
		ids = ["jungle_2", "jungle_1", "jungle_3", "jungle_5", "jungle_4"]
	# Game.goto_level needs a registered Main, so boot the real one first. This
	# is the actual game, not a harness that resembles it.
	add_child((load("res://src/core/main.tscn") as PackedScene).instantiate())
	for _i in 6:
		await get_tree().physics_frame
	for id in ids:
		await _compare(id)
	get_tree().quit(0)


func _press(a: StringName) -> void:
	if not _held.has(a):
		Input.action_press(a)
		_held.append(a)


func _apply(bits: int) -> void:
	for i in ACTS.size():
		var want: bool = (bits & int(BITS[i])) != 0
		var have: bool = _held.has(ACTS[i])
		if want and not have:
			_press(ACTS[i])
		elif have and not want:
			Input.action_release(ACTS[i])
			_held.erase(ACTS[i])


func _edges(inp: InputState, bits: int) -> void:
	var was := inp.jump
	inp.left = (bits & 1) != 0
	inp.right = (bits & 2) != 0
	inp.up = (bits & 4) != 0
	inp.down = (bits & 8) != 0
	inp.jump = (bits & 16) != 0
	inp.attack = (bits & 32) != 0
	inp.jump_pressed = inp.jump and not was
	inp.jump_released = was and not inp.jump
	inp._prev_jump = was


func _compare(id: String) -> void:
	var lvl_path := "res://levels/%s.json" % id
	var tape_path := "res://proofs/%s.tape.json" % id
	if not FileAccess.file_exists(tape_path):
		print("%-12s no tape" % id)
		return
	# hop boundaries, so a divergence can be named by the hop it starts in
	var tape_raw: Dictionary = ProverTape.read(tape_path)
	var bounds: Array = []
	var acc := 0
	for h: Variant in (tape_raw.get("hops", []) as Array):
		var hd: Dictionary = h
		var n := 0
		for st: Variant in (hd.get("frames", []) as Array):
			n += int((st as Dictionary).get("n", 0))
		bounds.append({"at": acc, "to_from": String(hd.get("from", "?")),
			"desc": "%s > %s" % [hd.get("from", "?"), hd.get("to", "?")]})
		acc += n
	var bits := ProverTape.frames(tape_path, lvl_path)
	if bits.is_empty():
		print("%-12s tape is stale or unreadable" % id)
		return

	# the prover's side
	var def := LevelLoader.load_level(id)
	var sim := ProverSim.new()
	sim.setup(def)
	var raw: Dictionary = _raw(lvl_path)
	var marks: Variant = raw.get("marks", {})
	if typeof(marks) == TYPE_DICTIONARY:
		for n: Variant in (marks as Dictionary).keys():
			var m: Dictionary = (marks as Dictionary)[n]
			sim.add_marker(String(n), int(m.get("x", 0)), int(m.get("y", 0)))
	var inp := InputState.new()

	# the real game's side
	for a in _held.duplicate():
		Input.action_release(a)
	_held.clear()
	SaveManager.set_flag(id, false)
	Game.reset_run()
	Game.goto_level(id)
	for _i in 4:
		await get_tree().physics_frame
	var lvl: Node = Game.current_level
	if lvl == null or lvl.get("player") == null:
		print("%-12s did not boot" % id)
		return
	var pl: Actor = lvl.player
	pl.set("invuln", 1e9)          # damage is a separate, known divergence

	# The real level gets four frames to build before the tape starts, and in them
	# Kaya settles onto the floor. Give the sim the same four, or it swallows the
	# first jump because it is still airborne on frame 0 — a harness artefact that
	# looks exactly like a physics divergence.
	var settle := 4
	for a in OS.get_cmdline_user_args():
		if a == "--nosettle":
			settle = 0
	var neutral := InputState.new()
	for _i in settle:
		sim.step(neutral)

	var d0 := pl.pos - sim.actor.pos
	if d0.length() > EPS:
		print("%-12s DIFFERENT SPAWN  game=%v sim=%v" % [id, pl.pos, sim.actor.pos])

	var hist: Array = []
	var f := 0
	while f < bits.size():
		_apply(int(bits[f]))
		await get_tree().physics_frame
		if not is_instance_valid(pl) or pl.get("dead"):
			print("  [f%4d] the game lost Kaya (died / level reloaded); sim continues alone" % f)
			pl = null
		if Game.sim_paused:
			continue               # screen flip: the prover has no such thing
		_edges(inp, int(bits[f]))
		sim.step(inp)
		for b: Variant in bounds:
			var bd: Dictionary = b
			if int(bd["at"]) == f + 1:
				var wp := String(bd["to_from"])
				var at_wp := "n/a"
				var idxs := sim.waypoint_indices(wp)
				if not idxs.is_empty():
					at_wp = "NO"
					for gi: int in idxs:
						if sim.waypoint_rect(gi).intersects(sim.actor.aabb()):
							at_wp = "yes"
							break
					if at_wp == "NO":
						for gi: int in idxs:
							print("        want rect %s   body %s" % [
								sim.waypoint_rect(gi), sim.actor.aabb()])
				print("  [f%4d] next hop %-26s sim at '%s'? %-4s  sim=%v" % [
					f + 1, bd["desc"], wp, at_wp, sim.actor.pos.round()])
		var gclimb := false
		var sclimb := false
		var gf: Variant = pl.get("form") if pl != null else null
		if gf != null:
			gclimb = bool((gf as RefCounted).get("climbing"))
		sclimb = bool(sim.form.get("climbing"))
		hist.append("  %4d %-18s game y=%7.2f vy=%7.1f fl=%d cl=%d | sim y=%7.2f vy=%7.1f fl=%d cl=%d" % [
			f, _names(int(bits[f])),
			pl.pos.y if pl != null else -1.0, pl.vel.y if pl != null else 0.0,
			int(pl.on_floor) if pl != null else -1, int(gclimb),
			sim.actor.pos.y, sim.actor.vel.y, int(sim.actor.on_floor), int(sclimb)])
		if hist.size() > 14:
			hist.pop_front()
		var d := Vector2.ZERO
		if pl != null and settle > 0:
			d = pl.pos - sim.actor.pos
		if d.length() > EPS:
			print("--- the fourteen frames up to the split ---")
			for line: String in hist:
				print(line)
			print("%-12s DIVERGES at frame %d/%d" % [id, f, bits.size()])
			print("    game pos=%v vel=%v on_floor=%s form=%s" % [
				pl.pos.round(), pl.vel.round(), str(pl.on_floor), pl.get("form_id")])
			
			print("    sim  pos=%v vel=%v on_floor=%s form=%s" % [
				sim.actor.pos.round(), sim.actor.vel.round(),
				str(sim.actor.on_floor), sim.form_id])
			print("    delta=%v   buttons=%s" % [d.round(), _names(int(bits[f]))])
			return
		f += 1
	print("%-12s agrees for all %d frames" % [id, bits.size()])


func _names(b: int) -> String:
	var out: Array[String] = []
	for i in ACTS.size():
		if (b & int(BITS[i])) != 0:
			out.append(String(ACTS[i]))
	return "+".join(out) if out.size() > 0 else "-"


func _raw(path: String) -> Dictionary:
	var fh := FileAccess.open(path, FileAccess.READ)
	if fh == null:
		return {}
	var p: Variant = JSON.parse_string(fh.get_as_text())
	fh.close()
	return p if typeof(p) == TYPE_DICTIONARY else {}
