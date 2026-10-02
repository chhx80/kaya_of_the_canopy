extends TestCase
## The iOS build ships a COMMITTED ios/KayaOfTheCanopy.pck rather than building
## one at CI time. That is fast, and it means the .pck can silently fall behind
## the source — you would ship a build that plays an older game than the repo
## describes, which is exactly the kind of thing that makes a fixed bug look
## unfixed on a device.
##
## tools/sync_ios_project.sh records a hash of everything that goes into the
## .pck. This checks it still matches.

const HASH_FILE := "res://ios/.pck_source_hash"
const PCK := "res://ios/KayaOfTheCanopy.pck"

## A recorded hash is not enough. I regenerated ios/.pck_source_hash without
## regenerating the .pck itself, which made the guard report "in sync" while
## TestFlight shipped a build three commits behind — the old pillarboxed layout.
## These checks read the .pck's actual BYTES and look for content that can only
## be there if it was rebuilt from the current source. Metadata cannot fake it.
var _pck_cache: PackedByteArray = PackedByteArray()

func _pck_bytes() -> PackedByteArray:
	if _pck_cache.is_empty():
		var f := FileAccess.open(PCK, FileAccess.READ)
		if f != null:
			_pck_cache = f.get_buffer(f.get_length())
			f.close()
	return _pck_cache

## PackedByteArray.find() searches for a single byte, not a subsequence, so
## this is a plain scan with a first-byte shortcut. The buffer is cached.
func _pck_contains(needle: String) -> bool:
	var hay := _pck_bytes()
	var pin := needle.to_utf8_buffer()
	var n := pin.size()
	var h := hay.size()
	if n == 0 or n > h:
		return false
	var first := pin[0]
	var i := 0
	while i <= h - n:
		if hay[i] == first:
			var j := 1
			while j < n and hay[i + j] == pin[j]:
				j += 1
			if j == n:
				return true
		i += 1
	return false

func test_the_pck_contains_the_current_root_scene() -> void:
	# Every node name in main.tscn must appear in the packed scene.
	var text := FileAccess.get_file_as_string("res://src/core/main.tscn")
	var re := RegEx.new()
	re.compile('\\[node name="([A-Za-z0-9_]+)"')
	var names: Array[String] = []
	for m in re.search_all(text):
		var n := m.get_string(1)
		if not names.has(n):
			names.append(n)
	gt(float(names.size()), 2.0, "main.tscn should declare several nodes")
	for n in names:
		ok(_pck_contains(n),
			"ios/KayaOfTheCanopy.pck has no '%s' — it predates the current main.tscn. " % n
			+ "Run tools/sync_ios_project.sh.")

func test_the_pck_contains_the_current_stretch_mode() -> void:
	var cfg := FileAccess.get_file_as_string("res://project.godot")
	var re := RegEx.new()
	re.compile('window/stretch/aspect="([a-z_]+)"')
	var m := re.search(cfg)
	ok(m != null, "project.godot declares a stretch aspect")
	if m == null:
		return
	ok(_pck_contains(m.get_string(1)),
		"the .pck does not carry stretch/aspect=%s — it is stale. Run tools/sync_ios_project.sh."
			% m.get_string(1))

func test_the_pck_contains_the_current_level_geometry() -> void:
	# The original version of this check probed jungle_2 row 24 alone — the
	# exact content that had shipped broken once. The guard then slept for
	# seven weeks while four worlds landed, because the one row it pinned
	# never changed again. A sentinel pinned to what was current when it was
	# written rots the day the game grows past it; this one enumerates the
	# levels directory instead, so a level the pck has never heard of is a
	# failure by construction.
	var dir := DirAccess.open("res://levels")
	ok(dir != null, "cannot open res://levels")
	if dir == null:
		return
	for name in dir.get_files():
		if not name.ends_with(".json"):
			continue
		var f := FileAccess.open("res://levels/%s" % name, FileAccess.READ)
		var d: Variant = JSON.parse_string(f.get_as_text())
		f.close()
		var rows: Array = (d as Dictionary).get("fg", [])
		if rows.is_empty():
			continue
		# The middle row is reliably long and distinctive for every level.
		var probe := String(rows[rows.size() / 2])
		ok(_pck_contains(probe),
			"the .pck does not contain %s's current geometry — the shipped game "
			% name + "differs from the source. Run tools/sync_ios_project.sh.")

func test_the_pck_contains_the_current_player_animation_data() -> void:
	# Levels cover content breadth; this covers the newest system depth. The
	# probe is an exact byte slice of the form file on disk (files ship
	# verbatim in the pck), anchored at the dance block the art-and-motion
	# plan added — if a later change renames it, re-anchor on whatever is
	# newest, which is the point of the exercise.
	var f := FileAccess.open("res://data/forms/human.json", FileAccess.READ)
	var text := f.get_as_text()
	f.close()
	var at := text.find("\"dance\"")
	ok(at >= 0, "data/forms/human.json no longer declares a dance block — re-anchor this probe")
	if at < 0:
		return
	ok(_pck_contains(text.substr(at, 60)),
		"the .pck does not contain the human form's current animation data — "
		+ "the shipped game predates the art-and-motion pass. "
		+ "Run tools/sync_ios_project.sh.")

func test_the_committed_ios_pck_is_present() -> void:
	ok(FileAccess.file_exists(PCK),
		"ios/KayaOfTheCanopy.pck is missing — run tools/sync_ios_project.sh")

func test_a_source_hash_was_recorded_for_it() -> void:
	ok(FileAccess.file_exists(HASH_FILE),
		"no ios/.pck_source_hash — run tools/sync_ios_project.sh")

func test_the_engine_frameworks_are_committed_compressed() -> void:
	for f in ["res://ios/frameworks/libgodot.device.tar.xz",
			"res://ios/frameworks/libMoltenVK.device.tar.xz",
			"res://ios/frameworks/KayaOfTheCanopy.Info.plist",
			"res://ios/frameworks/MoltenVK.Info.plist"]:
		ok(FileAccess.file_exists(f), "missing %s — the iOS build cannot link without it" % f)

## The standalone `xz` binary is Homebrew, not macOS. Using it in CI cost a
## build with exit 127. Everything must unpack with /usr/bin/tar alone.
func test_compressed_frameworks_are_tar_xz_not_raw_xz() -> void:
	var d := DirAccess.open("res://ios/frameworks")
	if d == null:
		return
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		if not d.current_is_dir() and f.ends_with(".xz"):
			ok(f.ends_with(".tar.xz"),
				"%s is a raw .xz — CI has no xz binary; use .tar.xz so bsdtar can read it" % f)
		f = d.get_next()
	d.list_dir_end()

func test_no_framework_exceeds_the_github_file_limit() -> void:
	var d := DirAccess.open("res://ios/frameworks")
	if d == null:
		return
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		if not d.current_is_dir():
			var fa := FileAccess.open("res://ios/frameworks/" + f, FileAccess.READ)
			if fa != null:
				var mb := float(fa.get_length()) / 1048576.0
				fa.close()
				lt(mb, 100.0, "ios/frameworks/%s is %.1f MB — GitHub rejects files over 100 MB" % [f, mb])
		f = d.get_next()
	d.list_dir_end()
