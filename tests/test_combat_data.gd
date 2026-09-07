extends TestCase
## Data-level checks for weapons and enemies. Behaviour is covered by
## tests/integration (which needs a real scene tree); this catches typos and
## balance mistakes without booting the game.

func _ids(dir: String) -> PackedStringArray:
	var out := PackedStringArray()
	var d := DirAccess.open(dir)
	if d == null:
		return out
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		if f.ends_with(".json"):
			out.append(f.get_basename())
		f = d.get_next()
	d.list_dir_end()
	out.sort()
	return out

# ---------------------------------------------------------------- weapons
func test_the_blade_loads_and_is_a_boomerang() -> void:
	var w := WeaponBase.load_weapon("boomerang_blade")
	ok(w != null, "boomerang_blade.json exists")
	eq(w.id, "boomerang_blade")
	gt(w.cooldown, 0.0, "a weapon without a cooldown is a machine gun")
	eq(w.ammo, -1, "the starting weapon has unlimited ammo")

func test_blade_range_is_reachable_but_not_screen_wide() -> void:
	var w := WeaponBase.load_weapon("boomerang_blade")
	var r := float(w.cfg["max_range"])
	gt(r, 6.0 * TileData4.TILE_SIZE, "must out-range a walker's approach")
	lt(r, float(Screen.W) * 0.5, "must not cover half a screen")

func test_blade_returns_faster_than_it_leaves() -> void:
	var w := WeaponBase.load_weapon("boomerang_blade")
	gt(float(w.cfg["return_max"]), float(w.cfg["speed"]),
		"the catch should feel snappier than the throw")

func test_every_weapon_file_has_the_keys_the_code_reads() -> void:
	for id in _ids("res://data/weapons"):
		var w := WeaponBase.load_weapon(id)
		ok(w != null, "%s loads" % id)
		if w == null:
			continue
		for key in ["sprite", "hitbox", "damage", "cooldown"]:
			ok(w.cfg.has(key), "%s is missing '%s'" % [id, key])
		ok(FileAccess.file_exists(String(w.cfg["sprite"])), "%s sprite missing" % id)

# ---------------------------------------------------------------- enemies
func test_every_enemy_has_a_script_and_a_sheet() -> void:
	for id in _ids("res://data/enemies"):
		var c := Enemy.load_config(id)
		not_ok(c.is_empty(), "%s parses" % id)
		ok(ResourceLoader.exists("res://src/enemies/%s.gd" % id),
			"data/enemies/%s.json has no matching controller" % id)
		ok(FileAccess.file_exists(String(c.get("sprite", ""))), "%s sprite missing" % id)

func test_every_enemy_has_sane_stats() -> void:
	for id in _ids("res://data/enemies"):
		var c := Enemy.load_config(id)
		gt(float(c.get("health", 0)), 0.0, "%s needs health" % id)
		lt(float(c.get("health", 0)), 40.0, "%s health looks like a typo" % id)
		gt(float(c.get("score", 0)), 0.0, "%s should be worth something" % id)
		var hb: Dictionary = c.get("hitbox", {})
		gt(float(hb.get("w", 0)), 0.0, "%s hitbox width" % id)
		gt(float(hb.get("h", 0)), 0.0, "%s hitbox height" % id)
		lt(float(hb.get("w", 99)), float(c.get("frame_w", 16)) + 1.0,
			"%s hitbox is wider than its sprite" % id)

func test_enemy_hitboxes_sit_inside_their_sprite_frame() -> void:
	for id in _ids("res://data/enemies"):
		var c := Enemy.load_config(id)
		var hb: Dictionary = c.get("hitbox", {})
		var fw := float(c.get("frame_w", 16))
		var fh := float(c.get("frame_h", 16))
		lt(float(hb.get("ox", 0)) + float(hb.get("w", 0)), fw + 0.01,
			"%s hitbox overflows the frame horizontally" % id)
		lt(float(hb.get("oy", 0)) + float(hb.get("h", 0)), fh + 0.01,
			"%s hitbox overflows the frame vertically" % id)

func test_walker_is_slower_than_the_player() -> void:
	var walker := Enemy.load_config("walker")
	var human := FormBase.load_form("human")
	lt(float(walker.get("speed", 0)), human.max_run, "you must be able to outrun a beetle")
	lt(float(walker.get("chase_speed", 0)), human.max_run, "…even when it chases")

func test_jumper_cannot_out_jump_the_player() -> void:
	var jumper := Enemy.load_config("jumper")
	var human := FormBase.load_form("human")
	var j_apex := pow(float(jumper["jump_vel"]), 2.0) / (2.0 * float(jumper["gravity"]))
	var p_apex := pow(human.jump_vel, 2.0) / (2.0 * human.gravity)
	lt(j_apex, p_apex, "the hopper must not reach ledges Kaya cannot")

func test_drop_chances_are_probabilities() -> void:
	for id in _ids("res://data/enemies"):
		var c := Enemy.load_config(id)
		var drops: Dictionary = c.get("drops", {})
		var total := 0.0
		for k: String in drops.keys():
			var v := float(drops[k])
			gt(v, 0.0, "%s drop '%s' must be > 0" % [id, k])
			lt(v, 1.01, "%s drop '%s' must be <= 1" % [id, k])
			has(Pickup.FRAMES, k, "%s drops unknown pickup '%s'" % [id, k])
			total += v
		lt(total, 1.01, "%s drop chances sum above 1" % id)
