extends TestCase
## Every sound the code asks for must exist on disk. A missing WAV is silent at
## runtime — no error, no crash — so this is the only thing that would catch it.

const SFX_DIR := "res://assets/audio/sfx/"
const MUSIC_DIR := "res://assets/audio/music/"

func _scan(dir: String, out: PackedStringArray) -> PackedStringArray:
	var d := DirAccess.open(dir)
	if d == null:
		return out
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		var p := "%s/%s" % [dir, f]
		if d.current_is_dir():
			if not f.begins_with("."):
				_scan(p, out)
		elif f.ends_with(".gd"):
			out.append(p)
		f = d.get_next()
	d.list_dir_end()
	return out

func _ids(call: String) -> PackedStringArray:
	var ids := PackedStringArray()
	var re := RegEx.new()
	re.compile("AudioManager\\.%s\\(\\s*\"([a-z0-9_]+)\"" % call)
	for path in _scan("res://src", PackedStringArray()):
		var text := FileAccess.get_file_as_string(path)
		for m in re.search_all(text):
			var id := m.get_string(1)
			if id != "" and not ids.has(id):
				ids.append(id)
	ids.sort()
	return ids

func test_every_sfx_the_code_plays_exists() -> void:
	var ids := _ids("play")
	gt(float(ids.size()), 10.0, "expected the code to reference plenty of SFX")
	for id in ids:
		ok(FileAccess.file_exists(SFX_DIR + id + ".wav"),
			"missing SFX '%s' (referenced in src/)" % id)

func test_every_music_track_the_code_requests_exists() -> void:
	for id in _ids("music"):
		ok(FileAccess.file_exists(MUSIC_DIR + id + ".wav"),
			"missing music track '%s'" % id)

func test_every_level_names_a_track_that_exists() -> void:
	for level_id in LevelLoader.list_levels():
		var def := LevelLoader.load_level(level_id)
		if def.music == "":
			continue
		ok(FileAccess.file_exists(MUSIC_DIR + def.music + ".wav"),
			"level '%s' asks for missing track '%s'" % [level_id, def.music])

func test_audio_files_are_not_empty() -> void:
	for dir in [SFX_DIR, MUSIC_DIR]:
		var d := DirAccess.open(dir)
		if d == null:
			continue
		d.list_dir_begin()
		var f := d.get_next()
		while f != "":
			if f.ends_with(".wav"):
				var fa := FileAccess.open(dir + f, FileAccess.READ)
				gt(float(fa.get_length()), 1000.0, "%s%s is suspiciously small" % [dir, f])
				fa.close()
			f = d.get_next()
		d.list_dir_end()
