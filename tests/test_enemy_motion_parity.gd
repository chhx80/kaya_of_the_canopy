extends TestCase
## Phase B, docs/plan-art-motion.md: the enemy pass. Two guards the plan asks
## for by name: every enemy's primary locomotion cycle reads as 4 real frames
## rather than 2, and every attack this diagnosis found already telegraphed in
## *behaviour* now telegraphs in *art* too — at least 2 frames of anticipation
## before the strike. Bosses are explicitly out of scope: "Bosses keep their
## 18-frame contract; they gain only edge discipline from Phase C."
##
## Measured before this phase (see the Phase B report): walker's "move",
## jumper/shooter's "windup", swimmer's "swim" and flyer's "fly" already met
## both floors — only charger's "move" and dropper's "walk" were still
## 2-frame. This test pins the floor so neither regresses and catches a new
## enemy that ships without it.

const DIR := "res://data/enemies"

## Locomotion-cycle keys worth holding to the 4-frame floor. Idle/windup/fire
## single-pose keys are deliberately not in this list — a rooted shooter has
## no "move" to begin with.
const CYCLE_KEYS: Array[String] = ["move", "walk", "fly", "swim"]
## Anticipation strips: the beat that plays before an attack actually lands.
const ANTICIPATION_KEYS: Array[String] = ["windup", "tell"]

func _json(path: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}

func _enemy_files() -> PackedStringArray:
	var out := PackedStringArray()
	var d := DirAccess.open(DIR)
	if d == null:
		return out
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		if f.ends_with(".json"):
			out.append(DIR + "/" + f)
		f = d.get_next()
	d.list_dir_end()
	out.sort()
	return out

func test_every_non_boss_locomotion_cycle_is_at_least_four_frames() -> void:
	for path in _enemy_files():
		var d := _json(path)
		if d.is_empty() or bool(d.get("boss", false)):
			continue
		var anims: Dictionary = d.get("anim", {})
		for key in CYCLE_KEYS:
			if not anims.has(key):
				continue
			var frames: Array = (anims[key] as Dictionary).get("frames", [])
			ok(frames.size() >= 4,
				"%s anim '%s' has only %d frames, want >= 4" % [path, key, frames.size()])

func test_every_attack_has_an_anticipation_strip_of_at_least_two_frames() -> void:
	for path in _enemy_files():
		var d := _json(path)
		if d.is_empty() or bool(d.get("boss", false)):
			continue
		var anims: Dictionary = d.get("anim", {})
		for key in ANTICIPATION_KEYS:
			if not anims.has(key):
				continue
			var frames: Array = (anims[key] as Dictionary).get("frames", [])
			ok(frames.size() >= 2,
				"%s anim '%s' has only %d frames, want >= 2 of anticipation" \
					% [path, key, frames.size()])

## The unified death poof: every non-boss enemy that does not override
## `death_fx` falls back to "scatter" (src/enemies/enemy_base.gd), and every
## one that DOES override it still has to name a real 4-frame emitter.
func test_every_non_boss_death_fx_resolves_to_a_four_frame_emitter() -> void:
	var fx := _json("res://data/fx.json")
	var emitters: Dictionary = (fx.get("particles", {}) as Dictionary).get("emitters", {})
	for path in _enemy_files():
		var d := _json(path)
		if d.is_empty() or bool(d.get("boss", false)):
			continue
		var fx_name := String(d.get("death_fx", "scatter"))
		ok(emitters.has(fx_name), "%s death_fx '%s' has no emitter" % [path, fx_name])
		if not emitters.has(fx_name):
			continue
		var frames: Array = (emitters[fx_name] as Dictionary).get("frames", [])
		eq(frames.size(), 4, "%s death_fx '%s' is not a 4-frame poof" % [path, fx_name])
