extends Node
## The Pickup Gate.  Driven by `tools/pickupgate.sh`.
##
## The Route Prover (ADR 005) proves one thing: the EXIT is reachable along the
## route the level declares. It says nothing about the heart on the shelf the
## route walks under, and three TestFlight reports in one build were exactly
## that -- a pickup in plain view that a player could not get. This asks the
## question the prover does not: for every heart, key and transform pad, can the
## real body touch it, starting from somewhere the route actually goes?
##
## THE SEEDS are the states the proof tape passes through: every hop start, every
## SEED_EVERY frames in between, and where it ends. The tape is replayed frame by frame in a fresh
## ProverSim, so a seed is a state a player has really been in. For each target
## the nearest few hop starts and the nearest few states along the tape are
## searched (PickupReach: the prover's physics, touch as the goal, attack
## pressed and broken tiles carried in the state), first without breaking
## anything and then, if the level has breakables, with.
##
## WHAT A VERDICT MEANS
##   REACHED    a tape exists that touches it from a route state, and it was
##              replayed from that state and touched it again. A proof, under
##              the prover's own limits: no enemies, hazards avoided.
##   NOT FOUND  every seed tried spent its budget. NOT a proof of impossibility
##              -- the frontier is greedy on manhattan distance, which ADR 005
##              measured stalling under ledges -- but a finding, to be checked
##              in the running game before anything is changed. `--probe` is
##              the tool for that.
##
##   tools/pickupgate.sh                         every level
##   tools/pickupgate.sh deeps_2 deeps_4         these
##   tools/pickupgate.sh --world deeps           every level whose id starts so
##   tools/pickupgate.sh jungle_3 --only "26,12;3,4" --seeds 8 --budget 8000
##                                               look harder at a few targets
##   tools/pickupgate.sh --probe deeps_2 --at 36,21 --form frog --goal 42,18 --stand
##
## Exit codes: 0 every target reached, 1 something not found, 3 cannot run.

const DEFAULT_BUDGET := 3000
const DEFAULT_SEEDS := 3
const EXIT_OK := 0
const EXIT_NOT_FOUND := 1
const EXIT_SETUP := 3
## A seed every this many frames of tape, as well as at every hop start. The
## search is greedy on manhattan distance, so where it starts matters more than
## how long it runs: measured on ruins_3, the heart two tiles off the kelp vine
## the route CLIMBS was not found in 8,000 expansions from the hop start at the
## vine's foot (the body sits 9 px left of the vine and every step towards the
## heart is a step away from it), and was found in 21 from a state on the vine.
const SEED_EVERY := 20

var _budget := DEFAULT_BUDGET
var _seeds := DEFAULT_SEEDS
var _level_ids: Array[String] = []
var _world := ""
var _allow_hazard := false
var _no_break := false
var _json_out := ""
## --only x,y;x,y: audit just the targets on these tiles.
var _only: Array[Vector2i] = []

# --probe
var _probe := ""
var _at := Vector2i(-1, -1)
var _form := "human"
var _goal := Vector2i(-1, -1)
var _stand := false
var _broken_at: Array[Vector2i] = []
var _verbose := false


func _ready() -> void:
	# Physics is identical with the mixer muted, and a search runs millions of
	# ticks through `AudioManager.play()`.
	AudioManager.enabled = false
	_parse_args(OS.get_cmdline_user_args())
	get_tree().quit(_run_probe() if _probe != "" else _run_audit())


func _parse_args(args: PackedStringArray) -> void:
	var pending := ""
	for a: String in args:
		if pending != "":
			_set_flag(pending, a)
			pending = ""
		elif a in ["--budget", "--seeds", "--world", "--probe", "--at", "--form", "--goal",
				"--json", "--broken", "--only"]:
			pending = a
		elif a.begins_with("--") and "=" in a:
			var kv := a.split("=", true, 1)
			_set_flag(kv[0], kv[1])
		elif a == "--allow-hazard":
			_allow_hazard = true
		elif a == "--no-break":
			_no_break = true
		elif a == "--stand":
			_stand = true
		elif a == "--verbose":
			_verbose = true
		elif not a.begins_with("--"):
			_level_ids.append(a)


func _set_flag(flag: String, v: String) -> void:
	match flag:
		"--budget": _budget = int(v)
		"--seeds": _seeds = int(v)
		"--world": _world = v
		"--probe": _probe = v
		"--at": _at = _tile(v)
		"--form": _form = v
		"--goal": _goal = _tile(v)
		"--json": _json_out = v
		"--broken":
			for part: String in v.split(";", false):
				_broken_at.append(_tile(part))
		"--only":
			for part: String in v.split(";", false):
				_only.append(_tile(part))


static func _tile(s: String) -> Vector2i:
	var xy := s.split(",")
	if xy.size() != 2:
		return Vector2i(-1, -1)
	return Vector2i(int(xy[0]), int(xy[1]))


# ---------------------------------------------------------------- level setup

## A sim exactly as the prover builds one: setup, the game's settle frames, the
## level's own marks.
func _make_sim(raw: Dictionary) -> ProverSim:
	var def := LevelLoader.from_dict(raw.duplicate())
	if not def.ok() or def.topdown:
		return null
	var sim := ProverSim.new()
	sim.setup(def)
	var neutral := InputState.new()
	for _i in 4:     # prove.gd SETTLE_FRAMES
		sim.step(neutral)
	sim.allow_hazard = _allow_hazard
	var mk: Variant = raw.get("marks", {})
	if typeof(mk) == TYPE_DICTIONARY:
		for n: Variant in (mk as Dictionary).keys():
			var v: Dictionary = (mk as Dictionary)[n]
			sim.add_marker(String(n), int(v.get("x", 0)), int(v.get("y", 0)))
	return sim


## The states the proof tape passes through: each hop start, every SEED_EVERY
## frames along it, and the end. Each is {"state", "held", "label", "form"}. Empty when the
## tape is stale or missing: a stale tape describes a level that is not there.
func _route_seeds(reach: PickupReach, level_path: String) -> Array:
	var out: Array = []
	var tape_path := ProverTape.tape_path_for(level_path)
	if ProverTape.staleness(tape_path, level_path) != "":
		return out
	var t := ProverTape.read(tape_path)
	var sim := reach.sim
	var input := InputState.new()
	var prev := 0
	for hop: Variant in (t.get("hops", []) as Array):
		var hd: Dictionary = hop
		out.append({"state": reach.snap(), "held": prev, "form": sim.form_id, "hop": true,
			"label": "%s>%s" % [hd.get("from", "?"), hd.get("to", "?")]})
		var f := 0
		for run: Variant in (hd.get("frames", []) as Array):
			var rd: Dictionary = run
			var bits := ProverTape.action_bits(String(rd.get("a", "none")))
			for _i in int(rd.get("n", 0)):
				ProverTape.apply(input, bits, prev)
				reach.tick(input)
				prev = bits
				f += 1
				if f % SEED_EVERY == 0:
					out.append({"state": reach.snap(), "held": prev, "form": sim.form_id, "hop": false,
						"label": "%s>%s+%d" % [hd.get("from", "?"), hd.get("to", "?"), f]})
	out.append({"state": reach.snap(), "held": prev, "form": sim.form_id, "hop": true,
		"label": "end of route"})
	return out


static func _is_target(type: String) -> bool:
	return type == "heart" or type.begins_with("key_") or type.begins_with("pad_")


# ---------------------------------------------------------------- the audit

func _targets_levels() -> Array[String]:
	var out: Array[String] = []
	for id: String in _level_ids:
		out.append(id)
	if out.is_empty():
		for id: String in LevelLoader.list_levels():
			if _world == "" or id.begins_with(_world):
				out.append(id)
	return out


func _run_audit() -> int:
	var worst := EXIT_OK
	var report: Array = []
	var missing: Array[String] = []
	for id: String in _targets_levels():
		var path := LevelLoader.level_path(id)
		var raw := _read_json(path)
		var sim := _make_sim(raw)
		if sim == null:
			continue
		var reach := PickupReach.new(sim)
		var seeds := _route_seeds(reach, path)
		if seeds.is_empty():
			# Not a pass. A level nobody has proved has no route states to start
			# from, and saying nothing would read as "every heart is fine".
			print("NO TAPE    %s -- no fresh proof tape, so no route states to search from" % id)
			missing.append("%s (no fresh tape)" % id)
			worst = EXIT_NOT_FOUND
			reach.dispose()
			continue
		var can_break := PickupReach.has_breakables(sim) and not _no_break
		for e: Dictionary in (raw.get("entities", []) as Array):
			var type := String(e.get("type", ""))
			if not _is_target(type):
				continue
			if not _only.is_empty() and not _only.has(Vector2i(int(e.get("x", 0)), int(e.get("y", 0)))):
				continue
			var r := _audit_one(reach, seeds, e, can_break)
			r["level"] = id
			r["type"] = type
			r["x"] = int(e.get("x", 0))
			r["y"] = int(e.get("y", 0))
			report.append(r)
			var at := "%s %s (%d,%d)" % [id, type, int(e.get("x", 0)), int(e.get("y", 0))]
			if bool(r["found"]):
				print("REACHED    %-30s from %-26s as %-5s %4d frames %5d exp%s" % [at,
					r["seed"], r["form"], int(r["frames"]), int(r["expansions"]),
					"  (breaks %d tile(s))" % int(r["broke"]) if int(r["broke"]) > 0 else ""])
			else:
				worst = EXIT_NOT_FOUND
				missing.append(at)
				print("NOT FOUND  %-30s closest %.1f px, body at tile %v; %d exp over %d seed(s)" % [
					at, float(r["closest"]), r["closest_tile"], int(r["expansions"]), int(r["seeds"])])
		reach.dispose()
	print("")
	if missing.is_empty():
		print("pickupgate: every heart, key and pad was touched from the route (%d)" % report.size())
	else:
		print("pickupgate: %d of %d NOT FOUND -- check each in the running game:"
			% [missing.size(), report.size()])
		for m: String in missing:
			print("    %s" % m)
	if _json_out != "":
		var f := FileAccess.open(_json_out, FileAccess.WRITE)
		if f != null:
			f.store_string(JSON.stringify(report, " ") + "\n")
			f.close()
	return worst


func _audit_one(reach: PickupReach, seeds: Array, e: Dictionary, can_break: bool) -> Dictionary:
	var goal := PickupReach.target_rect(e)
	var dist := PackedFloat32Array()
	for s: Dictionary in seeds:
		reach.restore(s["state"])
		dist.append(PickupReach.gap(reach.sim.actor.aabb(), goal))
	var idx: Array[int] = []
	for i in seeds.size():
		idx.append(i)
	idx.sort_custom(func(a: int, b: int) -> bool: return dist[a] < dist[b])
	# The nearest few of each kind. Nearest alone was worse than hop starts alone
	# on two hearts (deeps_4's vault, deeps_1's (3,26)): the closest states along
	# a tape are often the wrong side of a wall, while a hop start is somewhere
	# an author chose to stand. So both, interleaved, nearest first.
	var hops: Array[int] = idx.filter(func(i: int) -> bool: return bool(seeds[i]["hop"]))
	var mids: Array[int] = idx.filter(func(i: int) -> bool: return not bool(seeds[i]["hop"]))
	idx = []
	for k in _seeds:
		if k < hops.size():
			idx.append(hops[k])
		if k < mids.size():
			idx.append(mids[k])
	var best := {"found": false, "closest": 1.0e9, "closest_tile": Vector2i(-1, -1),
		"expansions": 0, "seeds": 0, "broke": 0}
	# Without breaking first: it is cheaper, and "only by breaking a wall" is a
	# different answer from "by walking", worth saying.
	var passes: Array[bool] = [false]
	if can_break:
		passes.append(true)
	for attack: bool in passes:
		for i in idx.size():
			var s: Dictionary = seeds[idx[i]]
			var r := reach.search(s["state"], int(s["held"]), goal, false, attack, _budget)
			if _verbose:
				reach.restore(s["state"])
				print("       seed %-28s %-5s at %v gap %.0f px, attack %s: %s in %d exp" % [
					s["label"], s["form"], reach.sim.actor.pos.round(), dist[idx[i]],
					str(attack), "found" if bool(r["found"]) else "not found", int(r["expansions"])])
			best["expansions"] = int(best["expansions"]) + int(r["expansions"])
			best["seeds"] = maxi(int(best["seeds"]), i + 1)
			if float(r["closest"]) < float(best["closest"]):
				best["closest"] = r["closest"]
				var at: Vector2 = r["closest_at"]
				best["closest_tile"] = Vector2i(int(at.x) / 16, int(at.y) / 16)
			if not bool(r["found"]):
				continue
			if not reach.replays(s["state"], int(s["held"]), r["actions"], goal, false):
				print("       note: a path was found from %s but did not replay; not counted"
					% s["label"])
				continue
			best["found"] = true
			best["seed"] = s["label"]
			best["form"] = s["form"]
			best["frames"] = (r["actions"] as PackedInt32Array).size()
			best["broke"] = r["broke"]
			return best
	return best


# ---------------------------------------------------------------- one probe

func _run_probe() -> int:
	var raw := _read_json(LevelLoader.level_path(_probe))
	var sim := _make_sim(raw)
	if sim == null or _at.x < 0 or _goal.x < 0:
		print("pickupgate: --probe needs a loadable level, --at x,y and --goal x,y")
		return EXIT_SETUP
	for t: Vector2i in _broken_at:
		sim.world.break_tile(t.x, t.y)
	var reach := PickupReach.new(sim)
	var start := reach.seed_at(_at, _form)
	var goal := PickupReach.tile_rect(_goal)
	var can_break := PickupReach.has_breakables(sim) and not _no_break
	print("probe  %s: %s at tile %v (pos %v, on_floor %s) -> tile %v, %s, breaking %s, budget %d" % [
		_probe, _form, _at, sim.actor.pos.round(), str(sim.actor.on_floor), _goal,
		"standing on it" if _stand else "touching it", "on" if can_break else "off", _budget])
	var r := reach.search(start, 0, goal, _stand, can_break, _budget)
	var code := EXIT_NOT_FOUND
	if bool(r["found"]):
		var ok := reach.replays(start, 0, r["actions"], goal, _stand)
		var acts: PackedInt32Array = r["actions"]
		print("REACHED  %d frames, %d expansions, broke %d tile(s), replay %s" % [acts.size(),
			int(r["expansions"]), int(r["broke"]), "reproduces it" if ok else "DOES NOT reproduce it"])
		if _verbose:
			for run: Dictionary in ProverTape.run_length(acts):
				print("    %3d x %s" % [int(run["n"]), run["a"]])
		code = EXIT_OK if ok else EXIT_NOT_FOUND
	else:
		var at: Vector2 = r["closest_at"]
		print("NOT FOUND  closest %.1f px, body at %v = tile (%d,%d), %d expansions, frontier %s" % [
			float(r["closest"]), at.round(), int(at.x) / 16, int(at.y) / 16, int(r["expansions"]),
			"EXHAUSTED: nothing in this action set gets there" if bool(r["exhausted"])
				else "not exhausted (budget spent)"])
	reach.dispose()
	return code


func _read_json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}
