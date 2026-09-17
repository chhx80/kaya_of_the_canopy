extends RefCounted
## A *strategy tape*: the literal button presses of the intended fight, in the
## same shape as the route tapes of ADR 005.
##
##   {"boss": "boss_grove", "level": "jungle_5", "fps": 60,
##    "source_sha": "<sha256 of the level json + the boss json>",
##    "frames": [{"n": 12, "a": "right"}, {"n": 4, "a": "right+attack"}]}
##
## `a` is a `+`-joined subset of {left right up down jump attack}; `n` is how
## many consecutive frames hold it.
##
## `source_sha` covers *both* the level and the boss config, because either one
## moving invalidates the fight. A stale tape fails; it does not warn. That rule
## is ADR 005's, and it exists because a stale iOS .pck once shipped a fix that
## was not in the build.

const ACTIONS := ["left", "right", "up", "down", "jump", "attack"]
## The InputMap action each tape token presses. The game polls real `Input`
## through `InputState`, so a replay has to go through the same door.
const ACTION_MAP := {
	"left": &"move_left", "right": &"move_right",
	"up": &"move_up", "down": &"move_down",
	"jump": &"jump", "attack": &"attack",
}


## sha256 over the level JSON and the boss JSON, in that order. Text is read
## raw, so reformatting either file is a change — which is the intent.
static func source_sha(level_id: String, boss_id: String) -> String:
	var ctx := HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	for path: String in ["res://levels/%s.json" % level_id,
			"res://data/enemies/%s.json" % boss_id]:
		var f := FileAccess.open(path, FileAccess.READ)
		if f == null:
			return ""
		ctx.update(f.get_buffer(f.get_length()))
		f.close()
	return ctx.finish().hex_encode()


## Run-length encode a per-frame list of action-name arrays.
static func encode(per_frame: Array) -> Array:
	var out: Array = []
	var run := ""
	var n := 0
	for i in per_frame.size():
		var held: Array = per_frame[i]
		var key := _canonical(held)
		if key == run and n > 0:
			n += 1
		else:
			if n > 0:
				out.append({"n": n, "a": run})
			run = key
			n = 1
	if n > 0:
		out.append({"n": n, "a": run})
	return out


## Expand the run-length form back into one entry per frame.
static func decode(frames: Array) -> Array:
	var out: Array = []
	for f: Variant in frames:
		var d: Dictionary = f
		var n := int(d.get("n", 0))
		var a := String(d.get("a", ""))
		var held: Array = [] if a == "" else Array(a.split("+"))
		for i in n:
			out.append(held)
	return out


static func frame_count(frames: Array) -> int:
	var n := 0
	for f: Variant in frames:
		n += int((f as Dictionary).get("n", 0))
	return n


## Sorted and deduplicated, so two runs holding the same buttons in a different
## order collapse into one entry instead of two.
static func _canonical(held: Array) -> String:
	var keep: Array = []
	for a: String in ACTIONS:
		if held.has(a):
			keep.append(a)
	return "+".join(PackedStringArray(keep))


static func save(path: String, tape: Dictionary) -> bool:
	var dir := path.get_base_dir()
	if not DirAccess.dir_exists_absolute(ProjectSettings.globalize_path(dir)):
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		push_error("BossGateTape: cannot write %s" % path)
		return false
	f.store_string(JSON.stringify(tape, "  ") + "\n")
	f.close()
	return true


static func load_tape(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}


## Empty string when the tape matches the files it was recorded against;
## otherwise the reason it is stale.
static func staleness(tape: Dictionary, level_id: String, boss_id: String) -> String:
	if tape.is_empty():
		return "no tape"
	if String(tape.get("level", "")) != level_id:
		return "tape is for level '%s', not '%s'" % [tape.get("level", ""), level_id]
	if String(tape.get("boss", "")) != boss_id:
		return "tape is for boss '%s', not '%s'" % [tape.get("boss", ""), boss_id]
	if int(tape.get("fps", 0)) != 60:
		return "tape is %s fps, the sim is 60" % str(tape.get("fps", 0))
	var want := source_sha(level_id, boss_id)
	if want == "":
		return "cannot hash the level or the boss config"
	if String(tape.get("source_sha", "")) != want:
		return "source_sha %s does not match %s (level or boss config changed)" \
			% [String(tape.get("source_sha", "")).substr(0, 12), want.substr(0, 12)]
	return ""


# ---------------------------------------------------------------- replay
## Press exactly the actions named, release everything else. Synthetic input
## goes through the real InputMap, so `InputState.poll()` sees it the way it
## sees a keyboard.
static func apply(held: Array) -> void:
	for name: String in ACTIONS:
		var action: StringName = ACTION_MAP[name]
		if held.has(name):
			if not Input.is_action_pressed(action):
				Input.action_press(action)
		elif Input.is_action_pressed(action):
			Input.action_release(action)


static func release_all() -> void:
	apply([])
