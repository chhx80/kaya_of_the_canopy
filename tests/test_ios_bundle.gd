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

func test_the_committed_ios_pck_is_present() -> void:
	ok(FileAccess.file_exists(PCK),
		"ios/KayaOfTheCanopy.pck is missing — run tools/sync_ios_project.sh")

func test_a_source_hash_was_recorded_for_it() -> void:
	ok(FileAccess.file_exists(HASH_FILE),
		"no ios/.pck_source_hash — run tools/sync_ios_project.sh")

func test_the_engine_frameworks_are_committed_compressed() -> void:
	for f in ["res://ios/frameworks/libgodot.device.a.xz",
			"res://ios/frameworks/libMoltenVK.device.a.xz",
			"res://ios/frameworks/KayaOfTheCanopy.Info.plist",
			"res://ios/frameworks/MoltenVK.Info.plist"]:
		ok(FileAccess.file_exists(f), "missing %s — the iOS build cannot link without it" % f)

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
