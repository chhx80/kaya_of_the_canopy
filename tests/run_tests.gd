extends SceneTree
## Headless test runner:  tools/test.sh
## Discovers tests/test_*.gd, runs every `test_*` method, prints a summary and
## exits non-zero on failure so CI can gate on it.

const DIR := "res://tests"

var _done := false

func _initialize() -> void:
	var files := _discover()
	var total := 0
	var failed := 0
	var checks := 0
	var report: Array[String] = []
	print("running %d test file(s)\n" % files.size())
	for path in files:
		var script: GDScript = ResourceLoader.load(path, "GDScript", ResourceLoader.CACHE_MODE_IGNORE)
		if script == null or not script.can_instantiate():
			report.append("  !! could not load %s (parse error?)" % path)
			failed += 1
			continue
		var inst: Object = script.new()
		if inst == null:
			report.append("  !! could not instantiate %s" % path)
			failed += 1
			continue
		var names: Array[String] = []
		for m: Dictionary in script.get_script_method_list():
			var n: String = m["name"]
			if n.begins_with("test_") and not names.has(n):
				names.append(n)
		names.sort()
		var file_fail := 0
		for n in names:
			total += 1
			inst.failures.clear()
			inst.before_each()
			inst.call(n)
			inst.after_each()
			checks += inst.checks
			inst.checks = 0
			if inst.failures.is_empty():
				report.append("  ok   %s :: %s" % [path.get_file(), n])
			else:
				failed += 1
				file_fail += 1
				report.append("  FAIL %s :: %s" % [path.get_file(), n])
				for f: String in inst.failures:
					report.append("         %s" % f)
	for line in report:
		print(line)
	print("\n%d tests, %d assertions, %d failed" % [total, checks, failed])
	_done = true
	if failed > 0:
		print("TESTS FAILED")
		quit(1)
	else:
		print("ALL TESTS PASSED")
		quit(0)

## Safety net: if _initialize ever aborts on a script error, don't hang CI.
func _process(_delta: float) -> bool:
	if not _done:
		push_error("run_tests: aborted before completion (a test file failed to parse?)")
		quit(2)
	return true


func _discover() -> PackedStringArray:
	var out := PackedStringArray()
	var d := DirAccess.open(DIR)
	if d == null:
		return out
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		if f.begins_with("test_") and f.ends_with(".gd"):
			out.append("%s/%s" % [DIR, f])
		f = d.get_next()
	d.list_dir_end()
	out.sort()
	return out
