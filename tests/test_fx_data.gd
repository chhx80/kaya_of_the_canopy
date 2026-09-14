extends TestCase
## The Phase 5 effect data. Everything the juice does is described by
## data/fx.json and data/tile_anim.json, so a bad edit here is a bad edit to the
## game — and two of these checks are outright soft-lock guards: a hitstop that
## outlasts its ceiling, or a shake wider than the camera's cull margin, are the
## only ways these effects could stop being cosmetic.

const FX_PATH := "res://data/fx.json"
const ANIM_PATH := "res://data/tile_anim.json"
const PARTICLE_ART := "res://assets/sprites/fx/particles.png"
const TILE_ANIM_ART := "res://assets/sprites/fx/tile_anim.png"

func _json(path: String) -> Dictionary:
	var txt := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(txt)
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}

## Straight off the PNG header. Image.load_from_file() would do it too, but it
## warns that the path will not survive an export — and this is a check on the
## source tree, not on anything the game loads at runtime.
func _png_size(path: String) -> Vector2i:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return Vector2i.ZERO
	var head := f.get_buffer(24)
	f.close()
	if head.size() < 24 or head.slice(12, 16).get_string_from_ascii() != "IHDR":
		return Vector2i.ZERO
	return Vector2i(head.decode_s32(16), head.decode_s32(20))

func _frames_in(path: String, cell: int) -> int:
	var size := _png_size(path)
	if size == Vector2i.ZERO or cell <= 0:
		return -1
	return (size.x / cell) * (size.y / cell)

# ---------------------------------------------------------------- art
func test_the_effect_art_the_data_names_exists() -> void:
	ok(FileAccess.file_exists(PARTICLE_ART), "missing %s (run tools/genfx.sh)" % PARTICLE_ART)
	ok(FileAccess.file_exists(TILE_ANIM_ART), "missing %s (run tools/genfx.sh)" % TILE_ANIM_ART)

func test_the_particle_atlas_is_a_whole_number_of_cells() -> void:
	var cfg: Dictionary = (_json(FX_PATH).get("particles", {}) as Dictionary)
	var cell := int(cfg.get("cell", 8))
	var size := _png_size(String(cfg.get("atlas", PARTICLE_ART)))
	ne(size, Vector2i.ZERO, "the particle atlas must be a readable PNG")
	if size == Vector2i.ZERO:
		return
	eq(size.x % cell, 0, "atlas width must divide by the cell size")
	eq(size.y % cell, 0, "atlas height must divide by the cell size")

# ---------------------------------------------------------------- particles
func test_every_emitter_is_completely_described() -> void:
	var cfg: Dictionary = (_json(FX_PATH).get("particles", {}) as Dictionary)
	var emitters: Dictionary = cfg.get("emitters", {})
	gt(float(emitters.size()), 3.0, "expected an emitter per Phase 5 effect")
	gt(float(int(cfg.get("pool", 0))), 0.0, "the pool needs a size")
	for name: String in emitters.keys():
		var e: Dictionary = emitters[name]
		for key in ["row", "frames", "fps", "count", "life", "speed", "angle_deg"]:
			ok(e.has(key), "emitter '%s' is missing '%s'" % [name, key])
		var life: Array = e.get("life", [0.0, 0.0])
		gt(float(life[0]), 0.0, "emitter '%s' needs a positive life" % name)
		ok(float(life[-1]) >= float(life[0]), "emitter '%s' life range is backwards" % name)
		var count: Array = e.get("count", [0, 0])
		gt(float(int(count[-1])), 0.0, "emitter '%s' would never spawn anything" % name)
		ok(int(count[-1]) <= int(cfg.get("pool", 0)),
			"emitter '%s' asks for more particles than the pool holds" % name)

func test_no_emitter_points_outside_the_particle_atlas() -> void:
	var cfg: Dictionary = (_json(FX_PATH).get("particles", {}) as Dictionary)
	var cell := int(cfg.get("cell", 8))
	var cols := int(cfg.get("atlas_columns", 4))
	var total := _frames_in(String(cfg.get("atlas", PARTICLE_ART)), cell)
	if total < 0:
		return   # the art check above already reported this
	for name: String in (cfg.get("emitters", {}) as Dictionary).keys():
		var e: Dictionary = (cfg["emitters"] as Dictionary)[name]
		for f: Variant in e.get("frames", []):
			var index := int(e.get("row", 0)) * cols + int(f)
			lt(float(index), float(total),
				"emitter '%s' frame %d is off the end of the atlas" % [name, int(f)])

# ---------------------------------------------------------------- shake
func test_no_shake_preset_can_out_reach_the_cull_margin() -> void:
	var shake: Dictionary = (_json(FX_PATH).get("shake", {}) as Dictionary)
	var cap := float(shake.get("max_px", 0.0))
	gt(cap, 0.0, "the shake block needs a max_px")
	ok(cap <= CameraController.MAX_SHAKE_PX,
		"data allows %f px of shake but the camera caps at %f" % [cap, CameraController.MAX_SHAKE_PX])
	var presets: Dictionary = shake.get("presets", {})
	gt(float(presets.size()), 1.0, "expected a preset for the slam and one for damage")
	for name: String in presets.keys():
		var p: Dictionary = presets[name]
		var amp := float(p.get("amplitude_px", 0.0))
		gt(amp, 0.0, "shake '%s' would not move" % name)
		ok(amp <= cap, "shake '%s' exceeds max_px" % name)
		gt(float(p.get("seconds", 0.0)), 0.0, "shake '%s' has no duration" % name)
		lt(float(p.get("seconds", 0.0)), 1.0, "shake '%s' outstays its welcome" % name)
		gt(float(p.get("hz", 0.0)), 0.0, "shake '%s' has no frequency" % name)

# ---------------------------------------------------------------- hitstop
func test_hitstop_is_bounded_both_in_data_and_in_code() -> void:
	var hs: Dictionary = (_json(FX_PATH).get("hitstop", {}) as Dictionary)
	var ceiling := float(hs.get("max_seconds", 0.0))
	gt(ceiling, 0.0, "hitstop needs a max_seconds")
	ok(ceiling <= 0.5, "a freeze longer than half a second reads as a hang")
	var presets: Dictionary = hs.get("presets", {})
	gt(float(presets.size()), 0.0, "expected at least one hitstop preset")
	for name: String in presets.keys():
		var secs := float(presets[name])
		gt(secs, 0.0, "hitstop '%s' would do nothing" % name)
		ok(secs <= ceiling, "hitstop '%s' is longer than max_seconds" % name)

func test_every_timing_the_call_sites_read_is_present() -> void:
	var timings: Dictionary = (_json(FX_PATH).get("timings", {}) as Dictionary)
	for key in ["land_dust_min_fall", "gem_shimmer_interval", "blade_spark_interval"]:
		ok(timings.has(key), "missing timing '%s'" % key)
		gt(float(timings.get(key, 0.0)), 0.0, "timing '%s' must be positive" % key)

# ---------------------------------------------------------------- tile table
func _anim() -> TileAnim:
	var a := TileAnim.new()
	a.load_from(ANIM_PATH)
	return a

func test_the_animation_table_only_names_tiles_that_exist() -> void:
	var tiles := TileData4.new()
	tiles.load_from(TileData4.PATH)
	var a := _anim()
	ok(a.has_any(), "expected some animated tiles")
	for id in a.ids():
		lt(float(id), float(tiles.count()), "tile id %d is not in data/tiles.json" % id)
		ne(tiles.name_of(id), "?", "tile id %d has no name" % id)

func test_no_animation_points_outside_the_tile_frame_atlas() -> void:
	var a := _anim()
	var total := _frames_in(a.atlas_path, a.cell)
	ok(total != 0, "the tile frame atlas must hold frames")
	if total < 0:
		return
	for id in a.ids():
		var e := a.entry(id)
		if not e.has("frames"):
			continue
		var frames: PackedInt32Array = e["frames"]
		for f in frames:
			lt(float(f), float(total), "tile %d names frame %d, past the atlas" % [id, f])

func test_frames_cycle_at_the_rate_they_were_given() -> void:
	var a := _anim()
	var d := {"animations": {"7": {"frames": [0, 1, 2, 3], "fps": 4.0}}}
	a.load_from_dict(d)
	eq(a.frame_index(7, 0.0), 0, "starts on the first frame")
	eq(a.frame_index(7, 0.3), 1, "second frame a quarter of a second in")
	eq(a.frame_index(7, 0.8), 3, "and the last just before the loop")
	eq(a.frame_index(7, 1.0), 0, "then wraps")
	eq(a.frame_index(99, 1.0), -1, "a tile with no animation has no frame")

func test_sway_is_whole_pixel_bounded_and_staggered_by_row() -> void:
	var a := _anim()
	a.load_from_dict({"animations": {
		"6": {"sway": {"axis": "x", "px": 1.0, "hz": 1.0, "row_phase": 0.25}}}})
	var differed := false
	for step in 40:
		var t := float(step) * 0.05
		var o := a.offset(6, 0, t)
		eq(o, o.round(), "sway must land on whole pixels")
		ok(absf(o.x) <= 1.0, "sway stays inside its amplitude")
		eq(o.y, 0.0, "an x sway never moves a tile vertically")
		if a.offset(6, 1, t) != o:
			differed = true
	ok(differed, "successive rows must not sway in lockstep")

func test_a_reckless_edit_is_clamped_rather_than_obeyed() -> void:
	var a := _anim()
	a.load_from_dict({"animations": {
		"6": {"sway": {"axis": "x", "px": 999.0, "hz": 1.0}},
		"24": {"tint": {"hz": 1.0, "amount": 99.0}}}})
	for step in 20:
		var t := float(step) * 0.05
		ok(absf(a.offset(6, 0, t).x) <= TileAnim.MAX_SWAY_PX,
			"sway must be clamped to MAX_SWAY_PX")
		ok(absf(a.tint(24, t) - 1.0) <= TileAnim.MAX_TINT,
			"tint must be clamped to MAX_TINT")

func test_malformed_entries_are_dropped_not_half_applied() -> void:
	var a := _anim()
	a.load_from_dict({"animations": {
		"6": {"frames": [], "fps": 0.0},
		"7": {"sway": {"axis": "x", "px": 0.0, "hz": 4.0}},
		"8": "not a dictionary"}})
	not_ok(a.has_any(), "nothing usable was described, so nothing animates")
	eq(a.frame_index(6, 1.0), -1, "an empty frame list is not an animation")
	eq(a.offset(7, 0, 1.0), Vector2.ZERO, "a zero-width sway does not move")
	near(a.tint(8, 1.0), 1.0, 0.0001, "a malformed entry leaves the tile alone")

func test_a_missing_table_leaves_every_tile_still() -> void:
	var a := TileAnim.new()
	not_ok(a.load_from("res://data/there_is_no_such_file.json"),
		"a missing table reports failure")
	not_ok(a.has_any(), "and animates nothing")
	not_ok(a.animated(7), "so no tile is animated")
	eq(a.offset(7, 0, 1.0), Vector2.ZERO, "and no tile moves")

func test_the_repaint_signature_tracks_change_and_nothing_else() -> void:
	var a := _anim()
	var ids := a.ids()
	ok(ids.size() > 0, "need animated ids to test with")
	eq(a.signature(ids, 1.0), a.signature(ids, 1.0), "the same moment looks the same")
	ne(a.signature(ids, 0.0), a.signature(ids, 9.7), "a different moment does not")
	eq(a.signature(PackedInt32Array(), 3.0), a.signature(PackedInt32Array(), 8.0),
		"a screen with no animated tiles never asks for a repaint")

func test_animating_a_tile_never_changes_what_it_is() -> void:
	# The whole safety argument for Phase 5: animation is a draw-time decision.
	var tiles := TileData4.new()
	tiles.load_from(TileData4.PATH)
	var a := _anim()
	for id in a.ids():
		var before := tiles.flags_of(id)
		a.advance(1.7)
		var _unused := a.frame_index(id)
		eq(tiles.flags_of(id), before, "tile %d changed flags while animating" % id)
