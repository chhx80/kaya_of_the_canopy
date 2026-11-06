class_name AchievementBook
extends RefCounted
## The achievement definitions in data/achievements.json and the pure decisions
## about them. No nodes and no Game Center here, so tests/test_achievements.gd
## can check them headless; src/core/achievements.gd is the thin part that
## talks to the platform.

const PATH := "res://data/achievements.json"

static func load_entries(path: String = PATH) -> Array:
	var raw := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(raw)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("AchievementBook: %s is not a JSON object" % path)
		return []
	var list: Variant = (parsed as Dictionary).get("achievements", [])
	return list if typeof(list) == TYPE_ARRAY else []

## Achievements a clear of `level_id` earns.
static func for_level(entries: Array, level_id: String) -> Array[String]:
	var out: Array[String] = []
	for e: Variant in entries:
		var d: Dictionary = e
		if String(d.get("level", "")) == level_id:
			out.append(String(d.get("id", "")))
	return out

## Achievements a save has earned but not yet recorded: a boss cleared before
## achievements existed. `cleared` answers whether a level is completed and
## `has` whether an achievement is already recorded.
static func owed(entries: Array, cleared: Callable, has: Callable) -> Array[String]:
	var out: Array[String] = []
	for e: Variant in entries:
		var d: Dictionary = e
		var id := String(d.get("id", ""))
		if bool(cleared.call(String(d.get("level", "")))) and not bool(has.call(id)):
			out.append(id)
	return out
