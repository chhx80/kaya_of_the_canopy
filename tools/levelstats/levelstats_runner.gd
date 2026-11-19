extends Node
## tools/levelstats.sh: one row per level, from the level JSON and its proof tape.
##
##   tools/levelstats.sh                          every side-view level in levels/
##   tools/levelstats.sh jungle_1 jungle_5        just these
##   tools/levelstats.sh --level-file=res://tests/fixtures/x.json
##   tools/levelstats.sh --json                   the same rows as JSON
##   tools/levelstats.sh --strict                 exit 1 if any tape is missing or stale
##
## Exit codes: 0 reported; 1 a level failed to load, or (with --strict) a row
## has no usable tape. A missing or stale tape is otherwise shown, not hidden:
## the row keeps its static numbers and prints NONE or STALE in place of the
## route's, because a stale proof measures a level that no longer exists.

var _ids: Array[String] = []
var _files: Array[String] = []
var _json := false
var _strict := false

func _ready() -> void:
	AudioManager.enabled = false
	for a: String in OS.get_cmdline_user_args():
		if a == "--json":
			_json = true
		elif a == "--strict":
			_strict = true
		elif a.begins_with("--level-file="):
			_files.append(a.split("=", true, 1)[1])
		elif not a.begins_with("--"):
			_ids.append(a)
	get_tree().quit(_run())

func _run() -> int:
	var targets: Array[String] = []
	if _ids.is_empty() and _files.is_empty():
		for id in LevelLoader.list_levels():
			targets.append(LevelLoader.level_path(id))
	for id in _ids:
		targets.append(LevelLoader.level_path(id))
	targets.append_array(_files)
	var rows: Array = []
	var code := 0
	for path in targets:
		var def := LevelLoader.load_path(path)
		if not def.ok():
			printerr("levelstats: %s: %s" % [path, ", ".join(def.errors)])
			code = 1
			continue
		if def.topdown:
			continue
		var raw := _read(path)
		var trace := LevelTrace.replay(def, path)
		var row := LevelStats.compute(def, raw, trace)
		rows.append(row)
		if _strict and String(row["tape"]) != "":
			printerr("levelstats: %s: %s" % [def.id, row["tape"]])
			code = 1
	if _json:
		print(JSON.stringify(rows, " "))
	else:
		print(LevelStats.table(rows))
		var c := LevelStats.cfg()
		var rt: Array = c.get("target_route_s", [])
		var sc: Array = c.get("target_screens", [])
		if rt.size() == 2 and sc.size() == 2:
			print("\ntarget (docs/plan-longer-levels.md): route %d-%d s, %d-%d screens"
				% [rt[0], rt[1], sc[0], sc[1]])
		print("scr: screens in the grid; vis: screens the route passes; 2nd: hops declared in a form")
		print("other than human; cp: checkpoints the route lights / placed; gap_s: longest route")
		print("seconds between spawn, checkpoints and the end; /min: enemies per route-minute;")
		print("haz: hazard tiles within %d tiles of the route; tape: ok, partial (boss level: route" \
			% int(LevelStats.cfg().get("near_hazard_tiles", 2)))
		print("to the arena), STALE or NONE (route columns blank).")
	return code

func _read(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var d: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return d if typeof(d) == TYPE_DICTIONARY else {}
