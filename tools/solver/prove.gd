extends Node
## The Route Prover (ADR 005).  Driven by `tools/prove.sh`.
##
## This is a *scene*, not a `--script`, and that is not a style choice:
## `--headless --script` gives no autoloads and no scene tree, and the form
## scripts reference `AudioManager`. Booting a one-node scene headless gives both
## and costs nothing.
##
## It does not model movement. It seeds the real `Actor` with the real
## `FormBase` subclass and searches over `form.update()` + `actor.step_motion()`
## at 60 Hz, hop by hop along the route the level declares. A hand-written jump
## envelope is exactly what shipped six unfinishable levels; the number that
## envelope got wrong (the frog's apex is 5.34 tiles, not 5.16) is recoverable
## here only because the search is playing the game rather than describing it.
##
##   tools/prove.sh                      prove every level that declares a route
##   tools/prove.sh jungle_1 jungle_4    prove these
##   tools/prove.sh --route "spawn>exit:human" jungle_1
##   tools/prove.sh --verify-tapes       fail if any tape is stale
##   tools/prove.sh --waypoints          list the ids a route may name
##   tools/prove.sh --mark foot:14,25    try a waypoint before writing it into the DSL
##
## Exit codes: 0 every hop proved, 1 a hop failed, 2 a level declared no route.

## ADR 005: "If one hop needs more than ~50k expansions, treat that as evidence
## the hop is too coarse, not a reason to raise the budget."
const DEFAULT_BUDGET := 50000

const EXIT_OK := 0
const EXIT_HOP_FAILED := 1
const EXIT_NO_ROUTE := 2

var _budget := DEFAULT_BUDGET
var _route_override := ""
var _level_files: Array[String] = []
var _level_ids: Array[String] = []
var _verify_tapes := false
var _list_waypoints := false
var _cli_marks: Array[String] = []
var _write_tapes := true
var _allow_hazard := false
var _quiet := false


func _ready() -> void:
	# Physics is identical with the mixer muted, and a search runs millions of
	# ticks through `AudioManager.play()`.
	AudioManager.enabled = false
	_parse_args(OS.get_cmdline_user_args())
	if _verify_tapes:
		get_tree().quit(_run_verify())
		return
	if _list_waypoints:
		get_tree().quit(_run_waypoints())
		return
	get_tree().quit(_run_prove())


# ---------------------------------------------------------------- CLI

func _parse_args(args: PackedStringArray) -> void:
	# `--route X` and `--route=X` both work; the split form is what a shell
	# gives you when the value has spaces in it.
	var pending := ""
	for a: String in args:
		if pending != "":
			_set_flag(pending, a)
			pending = ""
		elif a in ["--route", "--budget", "--level-file", "--mark"]:
			pending = a
		elif a.begins_with("--budget="):
			_budget = int(a.split("=")[1])
		elif a.begins_with("--route="):
			_set_flag("--route", a.split("=", true, 1)[1])
		elif a.begins_with("--level-file="):
			_set_flag("--level-file", a.split("=", true, 1)[1])
		elif a.begins_with("--mark="):
			_set_flag("--mark", a.split("=", true, 1)[1])
		elif a == "--verify-tapes":
			_verify_tapes = true
		elif a == "--waypoints":
			_list_waypoints = true
		elif a == "--no-tape":
			_write_tapes = false
		elif a == "--allow-hazard":
			_allow_hazard = true
		elif a == "--quiet":
			_quiet = true
		elif not a.begins_with("--"):
			_level_ids.append(a)


func _set_flag(flag: String, value: String) -> void:
	match flag:
		"--route": _route_override = value
		"--budget": _budget = int(value)
		"--level-file": _level_files.append(value)
		"--mark": _cli_marks.append(value)


func _say(s: String) -> void:
	if not _quiet:
		print(s)


# ---------------------------------------------------------------- tape check

## A stale tape fails. It does not warn. A stale iOS .pck once shipped a fix
## that was not in the build, and this is the cheap half of never repeating it.
func _run_verify() -> int:
	var paths := _tape_targets()
	if paths.is_empty():
		_say("prove: no tapes to verify")
		return EXIT_OK
	var bad := 0
	for level_path: String in paths:
		var tape_path := ProverTape.tape_path_for(level_path)
		if not FileAccess.file_exists(tape_path):
			print("STALE  %s — no tape; the level has never been proved" % level_path.get_file())
			bad += 1
			continue
		var err := ProverTape.staleness(tape_path, level_path)
		if err != "":
			print("STALE  %s — %s" % [tape_path.get_file(), err])
			bad += 1
		else:
			_say("ok     %s" % tape_path.get_file())
	if bad > 0:
		print("prove: %d stale tape(s) — re-run tools/prove.sh" % bad)
		return EXIT_HOP_FAILED
	return EXIT_OK


func _tape_targets() -> Array[String]:
	var out: Array[String] = []
	for f: String in _level_files:
		out.append(f)
	for id: String in _level_ids:
		out.append(LevelLoader.level_path(id))
	if out.is_empty():
		for id: String in LevelLoader.list_levels():
			if _has_route(LevelLoader.level_path(id)):
				out.append(LevelLoader.level_path(id))
	return out


func _has_route(path: String) -> bool:
	var d := _read_json(path)
	return d.has("route") and not (d["route"] as Array).is_empty()


## Every id a route may name, per level. The routes agent needs this to write
## `g.route(...)` against what the level actually contains, and it doubles as a
## cheap check that the prover can parse every level it will be asked to prove.
func _run_waypoints() -> int:
	for path: String in _tape_targets_all():
		var raw := _read_json(path)
		if raw.is_empty():
			print("%s: cannot read" % path)
			continue
		var def := LevelLoader.from_dict(raw.duplicate())
		if def.id == "":
			def.id = path.get_file().get_basename()
		if not def.ok() or def.topdown:
			print("%-12s (skipped: %s)" % [def.id, "top-down" if def.topdown else "does not load"])
			continue
		var sim := ProverSim.new()
		sim.setup(def)
		for m: Dictionary in _markers(raw):
			sim.add_marker(String(m["name"]), int(m["x"]), int(m["y"]))
		var counts := {}
		for e: Dictionary in sim.ents:
			var t := String(e["type"])
			counts[t] = int(counts.get(t, 0)) + 1
		var names: Array = counts.keys()
		names.sort()
		var parts: Array[String] = []
		for n: String in names:
			var c := int(counts[n])
			parts.append(n if c == 1 else "%s x%d (%s#0..%s#%d)" % [n, c, n, n, c - 1])
		print("%-12s spawn, %s" % [def.id, ", ".join(parts)])
	return EXIT_OK


func _tape_targets_all() -> Array[String]:
	var out: Array[String] = []
	for f: String in _level_files:
		out.append(f)
	for id: String in _level_ids:
		out.append(LevelLoader.level_path(id))
	if out.is_empty():
		for id: String in LevelLoader.list_levels():
			out.append(LevelLoader.level_path(id))
	return out


# ---------------------------------------------------------------- proving

func _run_prove() -> int:
	var targets := _tape_targets_all()
	var worst := EXIT_OK
	for path: String in targets:
		var code := _prove_level(path)
		# A missing route outranks a failed hop: it means the level was never
		# even claimed to be finishable.
		worst = maxi(worst, code)
	return worst


func _prove_level(path: String) -> int:
	var raw := _read_json(path)
	if raw.is_empty():
		print("FAIL   %s — cannot read or parse" % path)
		return EXIT_HOP_FAILED
	var def := LevelLoader.from_dict(raw.duplicate())
	if def.id == "":
		def.id = path.get_file().get_basename()
	if not def.ok():
		for e: String in def.errors:
			print("FAIL   %s — %s" % [def.id, e])
		return EXIT_HOP_FAILED
	if def.topdown:
		_say("skip   %s — top-down map, nothing to jump" % def.id)
		return EXIT_OK

	var route := _route_for(raw)
	if route.is_empty():
		# ADR 005: "A level with no route fails the gate. Silence is not a pass."
		print("NOROUTE %s — declares no route; silence is not a pass" % def.id)
		return EXIT_NO_ROUTE

	var sim := ProverSim.new()
	sim.setup(def)
	sim.allow_hazard = _allow_hazard
	for m: Dictionary in _markers(raw):
		sim.add_marker(String(m["name"]), int(m["x"]), int(m["y"]))

	var chain_err := _check_chain(route)
	if chain_err != "":
		print("NOROUTE %s — %s" % [def.id, chain_err])
		return EXIT_NO_ROUTE

	var started := Time.get_ticks_msec()
	var searcher := ProverSearch.new()
	var hops: Array = []
	var total_frames := 0
	var total_expansions := 0

	for i in route.size():
		var hop: Dictionary = route[i]
		var from_id := String(hop["from"])
		var to_id := String(hop["to"])
		var want_form := String(hop.get("form", ""))

		if want_form != "" and sim.form_id != want_form:
			print("FAIL   %s hop %d/%d  %s > %s" % [def.id, i + 1, route.size(), from_id, to_id])
			print("       the hop declares form '%s' but the route arrives as '%s'"
				% [want_form, sim.form_id])
			return EXIT_HOP_FAILED

		var goals := sim.waypoint_indices(to_id)
		if goals.is_empty():
			print("NOROUTE %s — waypoint '%s' is not an entity, a marker or 'spawn'"
				% [def.id, to_id])
			return EXIT_NO_ROUTE

		var start: Array = sim.snapshot()
		var res := searcher.run(sim, start, goals, _budget)
		total_expansions += res.expansions
		if not res.found:
			_report_failure(def.id, i, route, res, sim)
			return EXIT_HOP_FAILED

		sim.restore(res.end_state)
		total_frames += res.actions.size()
		hops.append({
			"from": from_id, "to": to_id, "form": want_form if want_form != "" else sim.form_id,
			"frames": ProverTape.run_length(res.actions),
		})
		# Standing on the waypoint is not the same as having used it: the pad
		# transforms you, the key goes in your pocket, the door eats it.
		for g: int in goals:
			if sim.waypoint_rect(g).intersects(sim.actor.aabb()):
				var eff := sim.apply_waypoint_effect(g)
				if eff != "":
					print("FAIL   %s hop %d/%d  %s > %s" % [def.id, i + 1, route.size(), from_id, to_id])
					print("       reached '%s' but could not use it: %s" % [to_id, eff])
					return EXIT_HOP_FAILED
				break
		_say("  hop %d/%d  %-14s > %-14s  %-5s  %4d frames  %6d expansions"
			% [i + 1, route.size(), from_id, to_id, hop.get("form", "-"),
			   res.actions.size(), res.expansions])

	var ms := Time.get_ticks_msec() - started
	if _write_tapes:
		var tape_path := ProverTape.tape_path_for(path)
		var err := ProverTape.write(tape_path, def.id, path, hops)
		if err != "":
			print("FAIL   %s — could not write the tape: %s" % [def.id, err])
			return EXIT_HOP_FAILED
		_say("PROVED %s — %d hops, %d frames (%.1fs of play), %d expansions, %d ms -> %s"
			% [def.id, hops.size(), total_frames, total_frames / 60.0, total_expansions, ms,
			   tape_path.get_file()])
	else:
		_say("PROVED %s — %d hops, %d frames, %d expansions, %d ms"
			% [def.id, hops.size(), total_frames, total_expansions, ms])
	return EXIT_OK


## The failure report is the product here. Naming the hop, how close it got and
## what it spent is the difference between "the gate is broken" and "tile 34,12
## is one pixel too high".
func _report_failure(level_id: String, i: int, route: Array, res: ProverSearch.Result, sim: ProverSim) -> void:
	var hop: Dictionary = route[i]
	print("FAIL   %s hop %d/%d  %s > %s  (as %s)"
		% [level_id, i + 1, route.size(), hop["from"], hop["to"], hop.get("form", "-")])
	print("       closest approach %.1f px, at pixel (%.1f, %.1f) = tile (%d, %d)"
		% [res.closest, res.closest_at.x, res.closest_at.y,
		   int(res.closest_at.x) / TileData4.TILE_SIZE, int(res.closest_at.y) / TileData4.TILE_SIZE])
	print("       %d expansions spent — %s" % [res.expansions, res.reason])
	var goals := sim.waypoint_indices(String(hop["to"]))
	for g: int in goals:
		var r := sim.waypoint_rect(g)
		print("       target '%s' is the rect (%.0f, %.0f)-(%.0f, %.0f)"
			% [hop["to"], r.position.x, r.position.y, r.end.x, r.end.y])
	if not sim.allow_hazard:
		print("       note: states touching a hazard are pruned; --allow-hazard relaxes that")
	if _has_breakables(sim):
		# The prover has no weapon. Leaving crates solid can only ever make it
		# fail a level it might have passed, never pass one it should fail —
		# but a route that counts on smashing one will die here, and the
		# failure would otherwise look like geometry.
		print("       note: this level has breakable tiles, and the prover cannot break them.")
		print("             It carries no weapon, so a crate is a wall to it. If the route")
		print("             goes through one, the route needs a way round, not a bigger budget.")


func _has_breakables(sim: ProverSim) -> bool:
	for y in sim.world.height:
		for x in sim.world.width:
			if sim.world.flags_at(x, y) & TileData4.Flag.BREAKABLE:
				return true
	return false


# ---------------------------------------------------------------- route input

## The route comes from the level when the author has declared one, and from
## `--route` when they have not yet. The CLI form exists so this tool is not
## blocked on the DSL gaining `g.route()`:
##   --route "spawn>pad_frog:human,pad_frog>exit:frog"
func _route_for(raw: Dictionary) -> Array:
	if _route_override != "":
		return _parse_route_string(_route_override)
	var r: Variant = raw.get("route", [])
	if typeof(r) != TYPE_ARRAY:
		return []
	var out: Array = []
	for item: Variant in (r as Array):
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var d: Dictionary = item
		out.append({"from": String(d.get("from", "")), "to": String(d.get("to", "")),
			"form": String(d.get("form", ""))})
	return out


func _parse_route_string(s: String) -> Array:
	var out: Array = []
	for part: String in s.split(",", false):
		var seg := part.strip_edges()
		if seg == "":
			continue
		var form := ""
		if ":" in seg:
			var bits := seg.split(":", true, 1)
			seg = bits[0]
			form = bits[1].strip_edges()
		var ends := seg.split(">", true, 1)
		if ends.size() != 2:
			push_error("prove: cannot read route hop '%s'" % part)
			continue
		out.append({"from": ends[0].strip_edges(), "to": ends[1].strip_edges(), "form": form})
	return out


## A route is a chain, not a bag of hops: the prover carries position and
## velocity across the join, so the tape it writes is one continuous run of
## button presses that the replay tier can feed straight into `InputState`.
func _check_chain(route: Array) -> String:
	if String((route[0] as Dictionary)["from"]) != "spawn":
		return "the route starts at '%s'; it has to start at 'spawn'" \
			% (route[0] as Dictionary)["from"]
	for i in range(1, route.size()):
		var prev := String((route[i - 1] as Dictionary)["to"])
		var here := String((route[i] as Dictionary)["from"])
		if prev != here:
			return "hop %d leaves from '%s' but hop %d arrived at '%s' — the route is not a chain" \
				% [i + 1, here, i, prev]
	return ""


## `g.mark("shaft_top", x, y)` serialises as a top-level `marks` OBJECT keyed by
## name — `{"shaft_top": {"x": 13, "y": 8}}` — which ADR 005 now pins. A
## `markers` array and a `marker` entity are still read, because two of us
## guessed differently before the ADR said so and a level file in either shape
## should not silently become unprovable.
## `--mark shaft_top:14,25` adds one from the command line, which is how you try
## a waypoint out before committing it to the DSL.
func _markers(raw: Dictionary) -> Array:
	var out: Array = []
	for m: String in _cli_marks:
		var bits := m.split(":", true, 1)
		if bits.size() != 2:
			push_error("prove: cannot read --mark '%s' (want name:x,y)" % m)
			continue
		var xy := bits[1].split(",")
		if xy.size() != 2:
			push_error("prove: cannot read --mark '%s' (want name:x,y)" % m)
			continue
		out.append({"name": bits[0].strip_edges(), "x": int(xy[0]), "y": int(xy[1])})
	# the canonical shape: {"name": {"x": .., "y": ..}}
	var mk: Variant = raw.get("marks", {})
	if typeof(mk) == TYPE_DICTIONARY:
		for name: Variant in (mk as Dictionary).keys():
			var v: Variant = (mk as Dictionary)[name]
			if typeof(v) != TYPE_DICTIONARY:
				continue
			var vd: Dictionary = v
			out.append({"name": String(name), "x": int(vd.get("x", 0)),
				"y": int(vd.get("y", 0))})
	var m: Variant = raw.get("markers", [])
	if typeof(m) != TYPE_ARRAY:
		return out
	for item: Variant in (m as Array):
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var d: Dictionary = item
		out.append({"name": String(d.get("name", "")), "x": int(d.get("x", 0)),
			"y": int(d.get("y", 0))})
	return out


func _read_json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}
