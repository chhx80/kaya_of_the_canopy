extends Node
## Autoload. Versioned JSON save at user://save.json with a migration chain.

const PATH := "user://save.json"
const CURRENT_VERSION := 2

var data: Dictionary = {}

func _ready() -> void:
	load_or_create()

static func default_data() -> Dictionary:
	return {
		"version": CURRENT_VERSION,
		"flags": {},                 ## level_id -> true when completed
		"best_score": 0,
		"total_gems": 0,
		"settings": {
			"music": 0.7,
			"sfx": 0.8,
			"touch_opacity": 0.5,
			"touch_scale": 1.0,
			"screen_flip": true,
		},
	}

func load_or_create() -> void:
	if not FileAccess.file_exists(PATH):
		data = default_data()
		save()
		return
	var f := FileAccess.open(PATH, FileAccess.READ)
	if f == null:
		data = default_data()
		return
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("SaveManager: corrupt save, starting fresh")
		data = default_data()
		save()
		return
	data = migrate(parsed)
	save()

## Upgrades any older save to CURRENT_VERSION. Pure so it can be unit tested.
static func migrate(old: Dictionary) -> Dictionary:
	var d := old.duplicate(true)
	var v := int(d.get("version", 0))
	if v < 1:
		# v0 had a flat "completed" array and no settings block.
		var flags := {}
		for id: Variant in d.get("completed", []):
			flags[String(id)] = true
		d["flags"] = flags
		d.erase("completed")
		d["best_score"] = int(d.get("score", 0))
		d.erase("score")
		v = 1
	if v < 2:
		# v1 had no touch settings and no gem counter.
		var settings: Dictionary = d.get("settings", {})
		settings["touch_opacity"] = float(settings.get("touch_opacity", 0.5))
		settings["touch_scale"] = float(settings.get("touch_scale", 1.0))
		settings["screen_flip"] = bool(settings.get("screen_flip", true))
		settings["music"] = float(settings.get("music", 0.7))
		settings["sfx"] = float(settings.get("sfx", 0.8))
		d["settings"] = settings
		d["total_gems"] = int(d.get("total_gems", 0))
		v = 2
	d["version"] = CURRENT_VERSION
	# Guarantee every key exists even if an older file was missing one.
	var base := default_data()
	for k: String in base.keys():
		if not d.has(k):
			d[k] = base[k]
	return d

func save() -> void:
	var f := FileAccess.open(PATH, FileAccess.WRITE)
	if f == null:
		push_error("SaveManager: cannot write %s" % PATH)
		return
	f.store_string(JSON.stringify(data, "  "))
	f.close()

# ---- accessors -------------------------------------------------------------
func get_flag(id: String) -> bool:
	return bool((data.get("flags", {}) as Dictionary).get(id, false))

func set_flag(id: String, value: bool) -> void:
	var flags: Dictionary = data.get("flags", {})
	flags[id] = value
	data["flags"] = flags

func completed_count() -> int:
	var n := 0
	for k: String in (data.get("flags", {}) as Dictionary).keys():
		if data["flags"][k]:
			n += 1
	return n

func add_score(s: int) -> void:
	data["best_score"] = maxi(int(data.get("best_score", 0)), s)

func setting(key: String, fallback: Variant = null) -> Variant:
	return (data.get("settings", {}) as Dictionary).get(key, fallback)

func set_setting(key: String, value: Variant) -> void:
	var s: Dictionary = data.get("settings", {})
	s[key] = value
	data["settings"] = s

func wipe() -> void:
	data = default_data()
	save()
