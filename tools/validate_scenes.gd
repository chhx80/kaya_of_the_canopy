extends SceneTree
## Headless structural check — Claude's eyes on things the editor would catch.
##   * every .tscn loads and every ext_resource it names exists
##   * every .gd compiles
##   * every level in levels/ passes LevelLoader validation
## Run with tools/validate.sh.

var _done := false
var problems := PackedStringArray()

func _initialize() -> void:
	_check_scripts("res://src")
	_check_scripts("res://tools")
	_check_scripts("res://tests")
	_check_scenes("res://src")
	_check_levels()
	_check_data()
	if problems.is_empty():
		print("validate: OK")
		_done = true
		quit(0)
	else:
		for p in problems:
			print("  PROBLEM  %s" % p)
		print("validate: %d problem(s)" % problems.size())
		_done = true
		quit(1)

func _process(_d: float) -> bool:
	if not _done:
		push_error("validate aborted")
		quit(2)
	return true

func _walk(dir: String, ext: String) -> PackedStringArray:
	var out := PackedStringArray()
	var d := DirAccess.open(dir)
	if d == null:
		return out
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		var p := "%s/%s" % [dir, f]
		if d.current_is_dir():
			if not f.begins_with("."):
				out.append_array(_walk(p, ext))
		elif f.ends_with(ext):
			out.append(p)
		f = d.get_next()
	d.list_dir_end()
	return out

const SELF_PATH := "res://tools/validate_scenes.gd"

func _check_scripts(root: String) -> void:
	for p in _walk(root, ".gd"):
		# Never re-load a script that is currently executing — reloading its own
		# bytecode mid-run corrupts the VM.
		if p == SELF_PATH or p == "res://tests/run_tests.gd":
			continue
		var s: Resource = ResourceLoader.load(p, "GDScript")
		# A GDScript with a parse error still comes back as an object, so null
		# is not enough — ask whether it is actually usable.
		if s == null:
			problems.append("script fails to load: %s" % p)
		elif not (s as GDScript).can_instantiate():
			problems.append("script fails to compile: %s" % p)

func _check_scenes(root: String) -> void:
	for p in _walk(root, ".tscn"):
		var text := FileAccess.get_file_as_string(p)
		for line in text.split("\n"):
			if line.begins_with("[ext_resource"):
				var i := line.find("path=\"")
				if i == -1:
					continue
				var rest := line.substr(i + 6)
				var path := rest.substr(0, rest.find("\""))
				if not ResourceLoader.exists(path):
					problems.append("%s references missing resource %s" % [p, path])
		var packed: PackedScene = ResourceLoader.load(p, "PackedScene")
		if packed == null:
			problems.append("scene fails to load: %s" % p)
		elif not packed.can_instantiate():
			problems.append("scene cannot be instantiated: %s" % p)

func _check_levels() -> void:
	var ids := LevelLoader.list_levels()
	if ids.is_empty():
		problems.append("no levels found in levels/")
	for id in ids:
		var def := LevelLoader.load_level(id)
		for e in def.errors:
			problems.append("level %s: %s" % [id, e])

func _check_data() -> void:
	for dir in ["res://data", "res://data/forms", "res://data/enemies", "res://data/weapons"]:
		var d := DirAccess.open(dir)
		if d == null:
			continue
		d.list_dir_begin()
		var f := d.get_next()
		while f != "":
			if f.ends_with(".json"):
				var txt := FileAccess.get_file_as_string("%s/%s" % [dir, f])
				if typeof(JSON.parse_string(txt)) != TYPE_DICTIONARY:
					problems.append("invalid JSON: %s/%s" % [dir, f])
			f = d.get_next()
		d.list_dir_end()
