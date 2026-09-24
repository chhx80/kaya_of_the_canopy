class_name ProverTape
extends RefCounted
## Read and write `levels/<id>.tape.json` — the proof ADR 005 asks for.
##
## The tape is the literal button presses that finish the level, so the
## integration tier can replay it through `InputState` against the real `Level`
## and assert the level reports complete.
##
## `source_sha` is the point of the file. A tape describes one exact grid; the
## instant the level changes the tape is a claim about something that no longer
## exists, and a stale claim **fails**. It does not warn. That rule is here
## because a stale iOS `.pck` once shipped a fix that was not in the build.


static func tape_path_for(level_path: String) -> String:
	# Shipped levels keep their tapes in proofs/, NOT beside the level.
	# LevelLoader.list_levels() globs levels/*.json, so a tape in there becomes a
	# level id -- and the hub's requires_all door demands a save flag for every
	# id it lists, so the final door could never open in a shipped build.
	# levels/ is not excluded from the .pck either, so the tapes would ship.
	# Moving them kills the whole class instead of filtering for it in three
	# places. A level somewhere else (a test writing to user://) keeps its tape
	# beside it, because nothing globs those directories.
	var base := level_path.get_file().get_basename()
	if level_path.begins_with("res://levels/"):
		return "res://proofs/%s.tape.json" % base
	return "%s/%s.tape.json" % [level_path.get_base_dir(), base]


## sha256 of the level file exactly as it sits on disk.
static func source_sha(level_path: String) -> String:
	return FileAccess.get_sha256(level_path)


## Collapse a per-frame action list into ADR 005's `{"n": 12, "a": "right"}` runs.
static func run_length(actions: PackedInt32Array) -> Array:
	var out: Array = []
	var i := 0
	while i < actions.size():
		var a := actions[i]
		var n := 0
		while i + n < actions.size() and actions[i + n] == a:
			n += 1
		out.append({"n": n, "a": ProverSearch.action_name(a)})
		i += n
	return out


## `extra` is merged into the document, and exists for one thing: a tape that
## does not cover the whole route has to SAY so, in the file, where a reader and
## a replay both trip over it. jungle_5's route ends at `boss_exit`, which
## `level.gd` does not place until the boss dies -- so the prover proves as far
## as the arena floor and stamps the tape `partial`, with the hops it did not
## prove and who owns them. A tape that quietly stops early is the same defect
## class as a stale one: a claim about something it never played.
static func write(tape_path: String, level_id: String, level_path: String, hops: Array,
		extra: Dictionary = {}) -> String:
	var dir := tape_path.get_base_dir()
	if not DirAccess.dir_exists_absolute(dir):
		DirAccess.make_dir_recursive_absolute(dir)
	var doc := {
		"level": level_id,
		"fps": 60,
		"source_sha": source_sha(level_path),
		"hops": hops,
	}
	doc.merge(extra, true)
	var f := FileAccess.open(tape_path, FileAccess.WRITE)
	if f == null:
		return "cannot open %s for writing" % tape_path
	f.store_string(JSON.stringify(doc, " ") + "\n")
	f.close()
	return ""


static func read(tape_path: String) -> Dictionary:
	var f := FileAccess.open(tape_path, FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


## True when this tape covers only part of its level's route. Written by the
## prover; read by anything that would otherwise treat the tape as a full proof.
static func is_partial(tape_path: String) -> bool:
	return bool(read(tape_path).get("partial", false))


## The hops a partial tape does not prove, each {from, to, why, owner}.
static func unproved_hops(tape_path: String) -> Array:
	var u: Variant = read(tape_path).get("unproved", [])
	return u if typeof(u) == TYPE_ARRAY else []


## "" when the tape still describes this level; otherwise why it does not.
## Callers must treat a non-empty return as a failure, never as a warning.
static func staleness(tape_path: String, level_path: String) -> String:
	var t := read(tape_path)
	if t.is_empty():
		return "tape is missing or unreadable"
	if not FileAccess.file_exists(level_path):
		return "the level it was proved against is gone"
	var want := source_sha(level_path)
	var got := String(t.get("source_sha", ""))
	if got == "":
		return "tape carries no source_sha"
	if got != want:
		return "level has changed since it was proved (tape %s, level %s)"\
			% [got.substr(0, 12), want.substr(0, 12)]
	if int(t.get("fps", 0)) != 60:
		return "tape was recorded at %s fps, the sim runs at 60" % str(t.get("fps"))
	return ""


## Flatten a tape back into one action per frame, for the replay tier.
## Returns an empty array if the tape is stale — callers get nothing to replay
## rather than something misleading to replay.
static func frames(tape_path: String, level_path: String) -> PackedInt32Array:
	var out := PackedInt32Array()
	if staleness(tape_path, level_path) != "":
		return out
	var t := read(tape_path)
	for hop: Variant in (t.get("hops", []) as Array):
		if typeof(hop) != TYPE_DICTIONARY:
			continue
		for run: Variant in ((hop as Dictionary).get("frames", []) as Array):
			if typeof(run) != TYPE_DICTIONARY:
				continue
			var d: Dictionary = run
			var bits := action_bits(String(d.get("a", "none")))
			for _i in int(d.get("n", 0)):
				out.append(bits)
	return out


## Inverse of ProverSearch.action_name(): "right+jump" -> the bitmask.
static func action_bits(name: String) -> int:
	if name == "none" or name == "":
		return 0
	var bits := 0
	for part: String in name.split("+", false):
		match part:
			"left": bits |= ProverSearch.LEFT
			"right": bits |= ProverSearch.RIGHT
			"up": bits |= ProverSearch.UP
			"down": bits |= ProverSearch.DOWN
			"jump": bits |= ProverSearch.JUMP
			"attack": bits |= ProverSearch.ATTACK
	return bits


## Drive an InputState from one frame of a tape, deriving the press/release
## edges the forms read. `prev` is the previous frame's bitmask.
static func apply(input: InputState, bits: int, prev: int) -> void:
	input.left = bits & ProverSearch.LEFT != 0
	input.right = bits & ProverSearch.RIGHT != 0
	input.up = bits & ProverSearch.UP != 0
	input.down = bits & ProverSearch.DOWN != 0
	input.jump = bits & ProverSearch.JUMP != 0
	input.attack = bits & ProverSearch.ATTACK != 0
	input.jump_pressed = input.jump and prev & ProverSearch.JUMP == 0
	input.jump_released = prev & ProverSearch.JUMP != 0 and not input.jump
	input.attack_pressed = input.attack and prev & ProverSearch.ATTACK == 0
	input._prev_jump = prev & ProverSearch.JUMP != 0
	input._prev_attack = prev & ProverSearch.ATTACK != 0
