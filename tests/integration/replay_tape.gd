extends RefCounted
## A proof tape (ADR 005) and the rules that decide whether it may be believed.
##
## The tape is the output of `tools/prove.sh` — the literal button presses that
## finish a level. This class does nothing but load one and refuse it. Refusing
## is the point: a tape that no longer matches its level is not a weaker proof,
## it is no proof at all, so every disagreement here is an error and never a
## warning. A stale iOS `.pck` once shipped a fix that was not in the build;
## a stale tape must not be able to do the same thing to a level.
##
## Format, from ADR 005:
##   {"level": "jungle_4", "fps": 60, "source_sha": "<sha256 of the level json>",
##    "hops": [{"from": "spawn", "to": "pad_frog", "form": "human",
##              "frames": [{"n": 12, "a": "right"}, {"n": 4, "a": "right+jump"}]}]}

## Every token `a` may contain. Anything else is a typo or a tape written
## against a different build, and both must fail rather than be ignored.
const ACTIONS := {
	"left": &"move_left", "right": &"move_right",
	"up": &"move_up", "down": &"move_down",
	"jump": &"jump", "attack": &"attack",
}

## A tape longer than this is a runaway, not a proof. 60 Hz, so ~3 minutes.
const MAX_FRAMES := 10800

var level_id := ""
var fps := 60
var source_sha := ""
var hops: Array[Dictionary] = []     ## {from, to, form, steps: Array[Dictionary]}
var total_frames := 0
var error := ""                      ## non-empty means: do not replay this

func ok() -> bool:
	return error == ""

static func tape_path(id: String) -> String:
	return "res://levels/%s.tape.json" % id

static func level_path(id: String) -> String:
	return "res://levels/%s.json" % id

static func exists_for(id: String) -> bool:
	return FileAccess.file_exists(tape_path(id))

## The sha the tape must carry: sha256 of the level file's bytes, lowercase hex.
## Identical to `shasum -a 256 levels/<id>.json`, so the prover, this replay and
## a human at a terminal can all compute the same number independently.
static func level_sha(id: String) -> String:
	var p := level_path(id)
	if not FileAccess.file_exists(p):
		return ""
	return FileAccess.get_sha256(p).to_lower()

## Loads and fully validates. Never returns null; check `ok()` / `error`.
static func load_for(id: String) -> RefCounted:
	return load_from(id, tape_path(id))

## Same, from a tape that is not (yet) beside its level. The suite uses this to
## prove the refusals above actually refuse: a rule nobody has watched fire is
## not a rule, it is a comment.
static func load_from(id: String, path: String) -> RefCounted:
	var t: RefCounted = (load("res://tests/integration/replay_tape.gd") as GDScript).new()
	t._load(id, path)
	return t

func _fail(msg: String) -> void:
	if error == "":
		error = msg

func _load(id: String, path: String) -> void:
	level_id = id
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		_fail("cannot read %s" % path)
		return
	var text := f.get_as_text()
	f.close()
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		_fail("%s is not a JSON object" % path)
		return
	var d: Dictionary = parsed

	var declared := String(d.get("level", ""))
	if declared != id:
		_fail("%s claims level '%s' but sits beside '%s'" % [path, declared, id])
		return

	# Stale-tape gate. This is the whole reason the sha is in the format, so it
	# is checked before anything about the frames is believed.
	var want := level_sha(id)
	if want == "":
		_fail("no level file at %s to check the tape against" % level_path(id))
		return
	source_sha = String(d.get("source_sha", "")).to_lower()
	if source_sha == "":
		_fail("%s carries no source_sha; it cannot be shown to match %s"
			% [path, level_path(id)])
		return
	if source_sha != want:
		_fail(("STALE TAPE: %s was proved against a different %s\n" +
			"      tape source_sha %s\n" +
			"      level sha256    %s\n" +
			"      The level changed after the tape was written. Re-prove it:" +
			" tools/prove.sh %s") % [path, level_path(id), source_sha, want, id])
		return

	# The tape is a list of frames, so its clock must be the game's clock.
	fps = int(d.get("fps", 0))
	var engine_fps := Engine.physics_ticks_per_second
	if fps != engine_fps:
		_fail("%s was recorded at %d fps but the sim runs at %d"
			% [path, fps, engine_fps])
		return

	var raw_hops: Variant = d.get("hops", null)
	if typeof(raw_hops) != TYPE_ARRAY or (raw_hops as Array).is_empty():
		_fail("%s declares no hops" % path)
		return

	var hop_i := 0
	for raw: Variant in (raw_hops as Array):
		if typeof(raw) != TYPE_DICTIONARY:
			_fail("%s hop %d is not an object" % [path, hop_i])
			return
		var h: Dictionary = raw
		var steps: Array[Dictionary] = []
		var raw_frames: Variant = h.get("frames", null)
		if typeof(raw_frames) != TYPE_ARRAY:
			_fail("%s hop %d has no frames array" % [path, hop_i])
			return
		var step_i := 0
		for rf: Variant in (raw_frames as Array):
			if typeof(rf) != TYPE_DICTIONARY:
				_fail("%s hop %d step %d is not an object" % [path, hop_i, step_i])
				return
			var sf: Dictionary = rf
			var n := int(sf.get("n", 0))
			if n < 1:
				_fail("%s hop %d step %d holds for %d frames"
					% [path, hop_i, step_i, n])
				return
			var acts: Variant = _parse_actions(String(sf.get("a", "")))
			if acts == null:
				_fail("%s hop %d step %d: unknown action '%s' (allowed: %s)"
					% [path, hop_i, step_i, String(sf.get("a", "")),
						", ".join(ACTIONS.keys())])
				return
			steps.append({"n": n, "actions": acts})
			total_frames += n
			step_i += 1
		if steps.is_empty():
			_fail("%s hop %d ('%s' -> '%s') is empty"
				% [path, hop_i, String(h.get("from", "?")), String(h.get("to", "?"))])
			return
		hops.append({
			"from": String(h.get("from", "?")),
			"to": String(h.get("to", "?")),
			"form": String(h.get("form", "?")),
			"steps": steps,
		})
		hop_i += 1

	# A tape is a proof that the level can be finished *from the start*. One
	# that begins anywhere else describes a shortcut, not a playthrough.
	var first_from := String((hops[0] as Dictionary).get("from", ""))
	if first_from != "spawn":
		_fail("%s starts at '%s', not 'spawn'; it does not prove the level can be played through"
			% [path, first_from])
		return

	if total_frames > MAX_FRAMES:
		_fail("%s is %d frames long; the cap is %d" % [path, total_frames, MAX_FRAMES])

## "right+jump" -> [&"move_right", &"jump"]. Returns null on an unknown token so
## the caller can tell "no buttons this frame" from "this tape is wrong".
static func _parse_actions(a: String) -> Variant:
	var out: Array[StringName] = []
	var s := a.strip_edges()
	if s == "" or s == "none":
		return out
	for tok in s.split("+", false):
		var key := tok.strip_edges()
		if not ACTIONS.has(key):
			return null
		var action: StringName = ACTIONS[key]
		if not out.has(action):
			out.append(action)
	return out
