extends TestCase
## tools/levelstats.sh is how the 5x length target and the difficulty curve are
## held (docs/plan-longer-levels.md), so its numbers are checked here against a
## level and a path built by hand, where every answer can be worked out on
## paper. LevelStats is the pure half; replaying a real tape into a trace is the
## integration tier's (it needs the autoloads), and that tier also checks the
## replay agrees with the real game about when a checkpoint is lit.

const W := 50
const H := 15
const FLOOR := 12
## Kaya walks east two pixels a frame from x = 16, standing on row 12.
const X0 := 16.0
const STEP := 2.0
const N := 373
const BOX := Vector2(10, 22)

func _level() -> LevelLoader.LevelDef:
	var rows: Array = []
	for y in H:
		var r := ".".repeat(W)
		if y == FLOOR:
			r = "#".repeat(W)
		rows.append(r)
	# Hazards: one on the route's row, one two rows under her feet (in range),
	# one three rows under (out of range) and one high up (out of range).
	rows[11] = _put(rows[11], 30, "^")
	rows[13] = _put(rows[13], 20, "^")
	rows[14] = _put(rows[14], 33, "^")
	rows[5] = _put(rows[5], 45, "^")
	return LevelLoader.from_dict({
		"id": "stats_fixture", "fg": rows,
		"entities": [
			{"type": "player_spawn", "x": 1, "y": 11},
			{"type": "checkpoint", "x": 10, "y": 11},
			{"type": "checkpoint", "x": 40, "y": 11},
			{"type": "checkpoint", "x": 25, "y": 3},       # off the route
			{"type": "enemy_walker", "x": 12, "y": 11},
			{"type": "enemy_walker", "x": 22, "y": 11},
			{"type": "enemy_flyer", "x": 32, "y": 6},
			{"type": "gem", "x": 5, "y": 11}, {"type": "gem", "x": 6, "y": 11},
			{"type": "heart", "x": 7, "y": 9}, {"type": "key_red", "x": 8, "y": 11},
			{"type": "exit", "x": 47, "y": 11},
		],
	})

func _raw() -> Dictionary:
	return {"route": [
		{"from": "spawn", "to": "a", "form": "human"},
		{"from": "a", "to": "b", "form": "frog"},
		{"from": "b", "to": "exit", "form": "human"},
	]}

static func _put(row: String, x: int, ch: String) -> String:
	return row.substr(0, x) + ch + row.substr(x + 1)

func _trace() -> Dictionary:
	var pos := PackedVector2Array()
	var box := PackedVector2Array()
	var form := PackedStringArray()
	var y := float(FLOOR * 16) - BOX.y
	for i in N:
		pos.append(Vector2(X0 + STEP * i, y))
		box.append(BOX)
		form.append("frog" if i >= 100 and i < 300 else "human")
	return {"pos": pos, "box": box, "form": form, "tape": "", "partial": false}

func _stats() -> Dictionary:
	var def := _level()
	ok(def.ok(), ", ".join(def.errors))
	return LevelStats.compute(def, _raw(), _trace(), 2)

func test_size_screens_and_route_time() -> void:
	var s := _stats()
	eq(s["tiles"], [W, H], "tiles")
	eq(int(s["screens"]), 2, "50x15 is two 25x15 screens")
	near(float(s["route_s"]), float(N) / 60.0, 0.0001, "route seconds are tape frames at 60 fps")
	# Her centre runs from x 21 to 21 + 2 * 372 = 765: both screens.
	eq(int(s["screens_visited"]), 2, "the route passes both screens")

func test_hops_and_forms() -> void:
	var s := _stats()
	eq(int(s["hops"]), 3, "three declared hops")
	eq(int(s["hops_second_form"]), 1, "one of them declared as a frog")
	eq(s["forms"], ["human", "frog"], "the forms the route plays, in order")

func test_checkpoints_are_lit_under_the_posts_own_rule() -> void:
	var s := _stats()
	eq(int(s["checkpoints"]), 3, "three placed")
	eq(int(s["checkpoints_on_route"]), 2, "the route lights two; the high one is off it")
	# Post at tile 10: its box starts at x 160 - touch_grow (1) = 159. Her box's
	# right edge, 16 + 2i + 10, first passes 159 at i = 67. The one at tile 40
	# (639): i = 307. Times are counted after the frame's step, so (i + 1) / 60.
	var cs: Array = s["checkpoint_s"]
	eq(cs.size(), 2, "two touch times")
	near(float(cs[0]), 68.0 / 60.0, 0.0001, "first post lit at frame 68")
	near(float(cs[1]), 308.0 / 60.0, 0.0001, "second post lit at frame 308")
	# Stretches: spawn->68, 68->308, 308->373. The longest is 240 frames.
	near(float(s["longest_gap_s"]), 240.0 / 60.0, 0.0001, "longest stretch between safe points")

func test_enemies_and_pickups() -> void:
	var s := _stats()
	eq(int(s["enemies"]), 3, "enemies counted")
	eq(int(s["bosses"]), 0, "no boss")
	near(float(s["enemies_per_min"]), 3.0 / (float(N) / 3600.0), 0.001, "enemies per route-minute")
	eq([int(s["gems"]), int(s["hearts"]), int(s["keys"])], [2, 1, 1], "gems, hearts, keys")

func test_hazards_near_the_route() -> void:
	var s := _stats()
	# Her body covers rows 10-11; two tiles round it is rows 8-13. In: (30,11)
	# and (20,13). Out: (33,14), a row too far, and (45,5).
	eq(int(s["hazards_near_route"]), 2, "two hazard tiles within two tiles of the route")
	var wide := LevelStats.compute(_level(), _raw(), _trace(), 3)
	eq(int(wide["hazards_near_route"]), 3, "three tiles out, the row-14 spike is in range too")

func test_no_usable_tape_blanks_the_route_numbers_and_keeps_the_rest() -> void:
	var tr := _trace()
	tr["tape"] = "level has changed since it was proved"
	var s := LevelStats.compute(_level(), _raw(), tr, 2)
	eq(int(s["route_s"]), -1, "no route seconds from a stale tape")
	eq(int(s["longest_gap_s"]), -1, "nor a gap")
	eq(int(s["checkpoints_on_route"]), -1, "nor checkpoints on the route")
	eq(s["forms"], [], "nor forms")
	eq(int(s["enemies"]), 3, "the level's own counts stand")
	eq(int(s["checkpoints"]), 3, "including its checkpoints")
	var t := LevelStats.table([s])
	ok(t.contains("stats_fixture"), "the table names the level")
	ok(t.contains("STALE"), "and says its tape is stale rather than printing numbers")

func test_no_checkpoints_means_the_whole_route_is_one_stretch() -> void:
	var def := LevelLoader.from_dict({
		"id": "bare", "fg": [".".repeat(W), "#".repeat(W)],
		"entities": [{"type": "player_spawn", "x": 1, "y": 0}],
	})
	var tr := _trace()
	var pos := PackedVector2Array()
	for i in N:
		pos.append(Vector2(X0 + STEP * i, 16.0 - BOX.y))
	tr["pos"] = pos
	var s := LevelStats.compute(def, {"route": []}, tr, 2)
	near(float(s["longest_gap_s"]), float(N) / 60.0, 0.0001, "spawn to the end in one go")
	eq(int(s["checkpoints_on_route"]), 0, "none lit")
