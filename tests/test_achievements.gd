extends TestCase
## The achievement definitions checked against the game they describe. An id
## typed wrong, or pointing at a level that is not a world's boss level, would
## be an achievement nobody can ever earn -- and App Store Connect would not
## notice, because it only ever sees the ids, never the levels.

const WORLDS := ["jungle", "ruins", "heights", "deeps", "nest"]

var entries: Array = []

func before_each() -> void:
	entries = AchievementBook.load_entries()

func _bundle_id() -> String:
	var raw := FileAccess.get_file_as_string("res://export_presets.cfg")
	var at := raw.find("application/bundle_identifier=\"")
	if at < 0:
		return ""
	at += "application/bundle_identifier=\"".length()
	return raw.substr(at, raw.find("\"", at) - at)

func test_one_achievement_per_world() -> void:
	eq(entries.size(), WORLDS.size(), "five worlds, five achievements")
	var seen := {}
	for e: Variant in entries:
		var level := String((e as Dictionary).get("level", ""))
		var world := level.get_slice("_", 0)
		ok(WORLDS.has(world), "%s belongs to a known world" % level)
		not_ok(seen.has(world), "world %s has only one achievement" % world)
		seen[world] = true

func test_every_achievement_is_earned_on_that_worlds_boss_level() -> void:
	for e: Variant in entries:
		var d: Dictionary = e
		var level := String(d.get("level", ""))
		var def := LevelLoader.load_level(level)
		ok(def.ok(), "%s exists and loads" % level)
		if not def.ok():
			continue
		var bosses := 0
		for ent: Variant in def.entities:
			if String((ent as Dictionary).get("type", "")).begins_with("boss_") \
					and String((ent as Dictionary).get("type", "")) != "boss_exit":
				bosses += 1
		eq(bosses, 1, "%s is a boss level, so clearing it means the boss fell" % level)

func test_ids_are_unique_and_namespaced_by_the_bundle_id() -> void:
	var bundle := _bundle_id()
	ne(bundle, "", "the iOS preset has a bundle id")
	var ids := {}
	for e: Variant in entries:
		var d: Dictionary = e
		var id := String(d.get("id", ""))
		ok(id.begins_with(bundle + "."), "%s starts with %s." % [id, bundle])
		not_ok(ids.has(id), "%s is unique" % id)
		ids[id] = true
		ok(String(d.get("title", "")) != "" and String(d.get("description", "")) != "",
			"%s has a title and a description for App Store Connect" % id)

func test_clearing_a_boss_level_earns_exactly_its_achievement() -> void:
	eq(AchievementBook.for_level(entries, "ruins_5"),
		["com.cateira.kayaofthecanopy.world2"] as Array[String], "ruins_5 earns world 2")
	eq(AchievementBook.for_level(entries, "ruins_4").size(), 0, "an ordinary level earns nothing")

func test_a_boss_cleared_before_achievements_existed_is_owed_one() -> void:
	var cleared := {"jungle_5": true, "ruins_5": true}
	var have := {"com.cateira.kayaofthecanopy.world1": true}
	var owed := AchievementBook.owed(entries,
		func(l: String) -> bool: return cleared.has(l),
		func(a: String) -> bool: return have.has(a))
	eq(owed, ["com.cateira.kayaofthecanopy.world2"] as Array[String],
		"world 2 is owed; world 1 is already recorded; the rest are not cleared")

func test_old_saves_gain_an_achievements_section() -> void:
	var old := {"version": 2, "flags": {"jungle_5": true}, "settings": {}}
	var sm: GDScript = load("res://src/core/save_manager.gd")
	var d: Dictionary = sm.call("migrate", old)
	ok(d.has("achievements"), "a pre-achievements save is given the section")
	eq((d["achievements"] as Dictionary).size(), 0, "and it starts empty")
