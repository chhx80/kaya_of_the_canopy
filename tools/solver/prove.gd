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

## Levels proved only as far as a boss arena, so the run can end with a summary
## no reader can mistake for six full proofs. One entry per level:
## {"id", "ends_at", "proved", "total", "unproved": Array}
var _partials: Array[Dictionary] = []

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
var _diff_hops := false
## Turns a partial proof into a failure. Off by default: the prover HAS discharged
## its whole obligation when it reaches a boss arena (ADR 005 section 4 hands the
## rest to the boss gate), and a gate that is permanently red is a gate everyone
## learns to ignore. On for anything that wants "full proofs only".
var _require_full := false


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
		elif a == "--diff-hops":
			_diff_hops = true
		elif a == "--require-full":
			_require_full = true
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
		elif ProverTape.is_partial(tape_path):
			# Fresh, but not a full proof. Saying "ok" here would let a partial tape
			# pass for a finished level every time anyone checked.
			var u := ProverTape.unproved_hops(tape_path)
			print("partial %s — fresh, but proves traversal only; %d hop(s) unproved"
				% [tape_path.get_file(), u.size()])
			for item: Variant in u:
				var ud: Dictionary = item
				print("        NOT proved: %s > %s (owner: %s)"
					% [ud.get("from", "?"), ud.get("to", "?"), ud.get("owner", "?")])
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
	if not _partials.is_empty():
		worst = maxi(worst, _report_partials())
	return worst


## The last thing printed, and deliberately loud. A partial proof is a real
## result -- the traversal IS proved -- but it is not the result the word PROVED
## means, and the whole history of this project is verification that checked the
## mechanism and reported it as the outcome.
func _report_partials() -> int:
	print("")
	print("prove: %d level(s) are NOT fully proved. Traversal is proved; the rest is not."
		% _partials.size())
	for p: Dictionary in _partials:
		print("  %s — proved %d of %d hops, up to '%s'"
			% [p["id"], p["proved"], p["total"], p["ends_at"]])
		for u: Dictionary in (p["unproved"] as Array):
			print("      NOT proved: %s > %s" % [u["from"], u["to"]])
			print("                  %s" % u["why"])
			print("                  owner: %s" % u["owner"])
	print("  Their tapes are stamped \"partial\": true and carry the unproved hops,")
	print("  so nothing downstream can read them as a finished level.")
	if _require_full:
		print("  --require-full was given, so this run fails.")
		return EXIT_HOP_FAILED
	return EXIT_OK


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
	_settle(sim)
	sim.allow_hazard = _allow_hazard
	for m: Dictionary in _markers(raw):
		sim.add_marker(String(m["name"]), int(m["x"]), int(m["y"]))

	var chain_err := _check_chain(route)
	if chain_err != "":
		print("NOROUTE %s — %s" % [def.id, chain_err])
		return EXIT_NO_ROUTE

	# The boss seam. Everything from the first hop that walks to `boss_exit`
	# onwards is the boss gate's to prove, and the prover stops there rather than
	# walking to a tile that is empty during play.
	var seam := _boss_seam(sim, route, def.id)
	if String(seam["error"]) != "":
		print("%s %s — %s" % [seam["verdict"], def.id, seam["error"]])
		return int(seam["code"])
	var unproved: Array = seam["unproved"]
	route = seam["route"]

	var started := Time.get_ticks_msec()
	var searcher := ProverSearch.new()
	var hops: Array = []
	var hop_actions: Array = []
	var hop_end: Array[Dictionary] = []
	var hop_start: Array = []
	var total_frames := 0
	var total_expansions := 0
	# What the controller is holding as each hop begins. The tape is one
	# continuous stream, so hop N+1's first frame follows hop N's last frame with
	# no gap for a thumb to lift in -- see ProverSearch.run()'s `held`.
	var held := 0

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
		if _diff_hops:
			sim.restore(start)
			hop_start.append(sim.describe_state())
		var res := searcher.run(sim, start, goals, _budget, held)
		total_expansions += res.expansions
		if not res.found:
			_report_failure(def.id, i, route, res, sim)
			return EXIT_HOP_FAILED

		sim.restore(res.end_state)
		if res.actions.size() > 0:
			held = res.actions[res.actions.size() - 1]
		hop_actions.append(res.actions)
		hop_end.append(sim.replay_signature())
		total_frames += res.actions.size()
		hops.append({
			"from": from_id, "to": to_id, "form": want_form if want_form != "" else sim.form_id,
			"frames": ProverTape.run_length(res.actions),
		})
		# Standing on the waypoint is not the same as having used it: the pad
		# transforms you, the key goes in your pocket, the door eats it. Those
		# now happen inside the simulation, where the tape can reproduce them --
		# the search will not call a triggered waypoint reached until they have.
		# All that is left here is to refuse a hop that somehow ended without
		# them, rather than papering over it by applying the effect by hand.
		for g: int in goals:
			if sim.waypoint_is_triggered(g) and not sim.waypoint_satisfied(g):
				var eff := "arrived at '%s' without using it" % to_id
				if true:
					print("FAIL   %s hop %d/%d  %s > %s" % [def.id, i + 1, route.size(), from_id, to_id])
					print("       reached '%s' but could not use it: %s" % [to_id, eff])
					return EXIT_HOP_FAILED
				break
		_say("  hop %d/%d  %-14s > %-14s  %-5s  %4d frames  %6d expansions"
			% [i + 1, route.size(), from_id, to_id, hop.get("form", "-"),
			   res.actions.size(), res.expansions])

	# A tape that does not reproduce the search is not a proof, it is a story
	# about one. Replay it here, in a fresh simulation, before anyone is told
	# the level is playable.
	var sc := _selfcheck(def, raw, hop_actions, hop_end, route, hop_start)
	if String(sc["error"]) != "":
		print("FAIL   %s — the tape does not reproduce the proof" % def.id)
		print("       %s" % sc["error"])
		return EXIT_HOP_FAILED
	# A self-check that did not finish is not a self-check that passed. It has
	# already happened once: a type error inside the loop aborted it mid-way and
	# the level printed PROVED, because "no error string" was read as "checked".
	# The count is the outcome; the empty string was only the mechanism.
	if int(sc["checked"]) != hop_actions.size():
		print("FAIL   %s — the self-check only got through %d of %d hops; it did not run to the end"
			% [def.id, int(sc["checked"]), hop_actions.size()])
		return EXIT_HOP_FAILED

	var ms := Time.get_ticks_msec() - started

	# The verdict. PROVED means the route was played end to end; PARTIAL means it
	# was not, and says where it stopped. Two words, because one word that
	# sometimes means the other is how a level nobody can finish gets a green tick.
	var partial := not unproved.is_empty()
	var ends_at := String(seam["ends_at"])
	var verdict := "PARTIAL" if partial else "PROVED"
	var extra := {}
	if partial:
		extra = {
			"partial": true,
			"proves": "traversal",
			"ends_at": ends_at,
			"unproved": unproved,
		}
		_partials.append({"id": def.id, "ends_at": ends_at, "proved": hops.size(),
			"total": hops.size() + unproved.size(), "unproved": unproved})

	if _write_tapes:
		var tape_path := ProverTape.tape_path_for(path)
		var err := ProverTape.write(tape_path, def.id, path, hops, extra)
		if err != "":
			print("FAIL   %s — could not write the tape: %s" % [def.id, err])
			return EXIT_HOP_FAILED
		_say("%s %s — %d hops, %d frames (%.1fs of play), %d expansions, %d ms -> %s"
			% [verdict, def.id, hops.size(), total_frames, total_frames / 60.0,
			   total_expansions, ms, tape_path.get_file()])
	else:
		_say("%s %s — %d hops, %d frames, %d expansions, %d ms"
			% [verdict, def.id, hops.size(), total_frames, total_expansions, ms])
	if partial:
		# Said here as well as in the run summary, because a reader who greps one
		# level out of a long log must not have to trust that they saw the footer.
		_say("       NOT a full proof: traversal is proved to '%s'; %d hop(s) to 'boss_exit'"
			% [ends_at, unproved.size()])
		_say("       are the boss gate's (ADR 005 section 4). The tape is stamped partial.")
	return EXIT_OK


## Where the prover's job stops and the boss gate's begins.
##
## `boss_exit` is not an entity the player can walk to. `Level.spawn_entity()`
## returns null for it and `Level.on_boss_defeated()` places it once the fight is
## won -- so during play the tile is empty, and a prover that treats it as
## ordinary scenery writes a tape that walks to nothing and a level that never
## completes. That is exactly how jungle_5 failed: the route ended at a waypoint
## that does not exist yet.
##
## ADR 005 already draws this line. Section 2 gives the prover traversal; section
## 4 gives the boss gate the fight, including check 5, "it ends -- boss_exit is
## reachable from the arena floor after defeat". So the honest model is not to
## teach the prover to fake the gate, and not to let it search its own simulation
## where the gate does happen to exist -- that is proving a level the player never
## sees, which is the modelling mistake ADR 005 exists to stop. It is to prove the
## route as far as the arena and say, in the verdict and in the tape, that the
## rest is not proved and who owns it.
##
## Returns {route, unproved, ends_at, error, verdict, code}.
func _boss_seam(sim: ProverSim, route: Array, level_id: String) -> Dictionary:
	var out := {"route": route, "unproved": [] as Array, "ends_at": "",
		"error": "", "verdict": "FAIL", "code": EXIT_HOP_FAILED}
	var cut := -1
	for i in route.size():
		var to_id := String((route[i] as Dictionary)["to"])
		var idxs := sim.waypoint_indices(to_id)
		var is_gate := not idxs.is_empty()
		for g: int in idxs:
			if not sim.waypoint_is_boss_gate(g):
				is_gate = false
		if is_gate:
			cut = i
			break
	if cut < 0:
		return out

	# A gate nothing can ever open. No boss means on_boss_defeated() is never
	# called, so `boss_exit` is placed by nothing and the level cannot be
	# finished by anyone. This is a real failure, not a seam.
	if sim.boss_count == 0:
		out["error"] = ("the route ends at 'boss_exit', but the level places no boss. "
			+ "Level.on_boss_defeated() is what puts that gate in the world, so "
			+ "nothing ever will: this level cannot be finished.")
		return out

	# Nothing left to prove. A route straight from spawn to the gate asks the
	# prover to certify a level it never plays a frame of.
	if cut == 0:
		out["verdict"] = "NOROUTE"
		out["code"] = EXIT_NO_ROUTE
		out["error"] = ("the route's first hop walks to 'boss_exit', which does not exist "
			+ "until the boss dies. Give the route a waypoint on the arena floor and "
			+ "end it there; ADR 005 section 4 check 5 proves the gate.")
		return out

	var unproved: Array = []
	for i in range(cut, route.size()):
		var h: Dictionary = route[i]
		unproved.append({
			"from": String(h["from"]), "to": String(h["to"]),
			"why": "'boss_exit' is placed by Level.on_boss_defeated(), so it is not in the world during play",
			"owner": "the boss gate (ADR 005 section 4, check 5: boss_exit is reachable from the arena floor after defeat)",
		})
	out["route"] = route.slice(0, cut)
	out["unproved"] = unproved
	out["ends_at"] = String((route[cut] as Dictionary)["from"])
	_say("  note   %s: the route ends at 'boss_exit'. Proving traversal to '%s' only;"
		% [level_id, out["ends_at"]])
	_say("         the last %d hop(s) are the boss gate's, not the prover's." % unproved.size())
	return out


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
## The game builds the level and gives it SETTLE_FRAMES before a tape's first
## button lands; in them Kaya falls the last few pixels onto the floor. The
## prover used to start searching from the raw spawn instead, one frame before
## she was standing -- so the very first jump in a tape was swallowed, and every
## frame after it was recorded against a body in a different place.
##
## It is small and it compounds: measured on jungle_2, the tape ended hop 2 four
## pixels short of the door it claimed to reach, and hop 3 twenty-five pixels
## short of the vine. The prover proved a run that started somewhere the game
## never starts.
const SETTLE_FRAMES := 4

static func _settle(sim: ProverSim) -> void:
	var neutral := InputState.new()
	for _i in SETTLE_FRAMES:
		sim.step(neutral)


## Replay every hop's recorded buttons in a fresh simulation and require the
## body to arrive where the search left it. Without this the prover can emit a
## tape it never actually played: the search explores by snapshot/restore, and
## anything it changes outside the button stream silently stops being true the
## moment the buttons are replayed end to end.
func _selfcheck(def: LevelLoader.LevelDef, raw: Dictionary, hop_actions: Array,
		hop_end: Array[Dictionary], route: Array, hop_start: Array = []) -> Dictionary:
	var sim := ProverSim.new()
	sim.setup(def)
	_settle(sim)
	sim.allow_hazard = _allow_hazard
	for m: Dictionary in _markers(raw):
		sim.add_marker(String(m["name"]), int(m["x"]), int(m["y"]))
	var inp := InputState.new()
	var prev := 0
	var checked := 0
	for i in hop_actions.size():
		if _diff_hops and i < hop_start.size():
			var want_s: Dictionary = hop_start[i]
			var got_s: Dictionary = sim.describe_state()
			var diffs: Array[String] = []
			for k: String in want_s.keys():
				if want_s[k] != got_s.get(k):
					diffs.append("%s: search=%s replay=%s" % [k, want_s[k], got_s.get(k)])
			print("  [hop %d start] prev_action=%d  %s" % [i + 1, prev,
				"identical" if diffs.is_empty() else ""])
			for d: String in diffs:
				print("        %s" % d)
		var acts: PackedInt32Array = hop_actions[i]
		for a: int in acts:
			_tape_input(inp, a, prev)
			sim.step(inp)
			prev = a
		var want: Dictionary = hop_end[i]
		var got := sim.replay_signature()
		var why := _signature_diff(want, got)
		if why != "":
			var h: Dictionary = route[i]
			return {"error": "hop %d/%d  %s > %s: %s"
				% [i + 1, route.size(), h["from"], h["to"], why], "checked": checked}
		checked += 1
	return {"error": "", "checked": checked}


## How the replay differs from the search, in the terms the reader needs, or ""
## when it does not. Position first, because it is the one a human can picture.
##
## Position alone was not enough. "The search left the body here" also means
## moving like this, in this shape, with this key spent and this switch thrown --
## a replay that lands on the right pixel with the wrong velocity is somewhere
## else one frame later, and one that lands there without having taken the key
## walks the next hop through a door the search found open.
static func _signature_diff(want: Dictionary, got: Dictionary) -> String:
	var wp: Vector2 = want["pos"]
	var gp: Vector2 = got["pos"]
	if gp.distance_to(wp) > 1.0:
		return "replayed to %v, but the search left it at %v" % [gp.round(), wp.round()]
	var wv: Vector2 = want["vel"]
	var gv: Vector2 = got["vel"]
	if gv.distance_to(wv) > 1.0:
		return ("replayed to the right pixel but moving at %v, where the search left it at %v"
			% [gv.round(), wv.round()])
	for k: String in ["form", "on_floor", "climbing", "keys", "taken", "opened", "switches"]:
		if want[k] != got[k]:
			return "replayed with %s = %s, where the search left it %s" \
				% [k, str(got[k]), str(want[k])]
	return ""


## The edge rules a replayed tape sees: a press is a frame whose predecessor did
## not hold the button. Must match ProverSearch._set_input and the integration
## tier's replay, or the three disagree about what a tape means.
static func _tape_input(inp: InputState, a: int, prev: int) -> void:
	inp.left = (a & ProverSearch.LEFT) != 0
	inp.right = (a & ProverSearch.RIGHT) != 0
	inp.up = (a & ProverSearch.UP) != 0
	inp.down = (a & ProverSearch.DOWN) != 0
	var was := (prev & ProverSearch.JUMP) != 0
	inp.jump = (a & ProverSearch.JUMP) != 0
	inp.jump_pressed = inp.jump and not was
	inp.jump_released = was and not inp.jump
	inp._prev_jump = was
	var wasa := (prev & ProverSearch.ATTACK) != 0
	inp.attack = (a & ProverSearch.ATTACK) != 0
	inp.attack_pressed = inp.attack and not wasa


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
