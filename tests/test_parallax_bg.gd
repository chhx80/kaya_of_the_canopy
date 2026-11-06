extends TestCase
## The parallax contract after the screen flip went (Kaya Refit phase 3).
##
## Two things here were wrong for a long time and invisible in review:
##
## * **Direction.** Until phase 3 a plane's screen offset was computed from
##   `1 - factor`, so the sky (0.10) scrolled at 90% of the tiles and the
##   near-foreground grass (0.82) at 18%: depth ran backwards. A screenshot
##   cannot show it; only a moving camera can, so it is pinned here as numbers.
## * **Slack.** Every strip used to be exactly one screen, so vertically it
##   could only be locked to the view. Strips are now sized by
##   data/parallax.json, and ParallaxBg maps the extra height across the
##   level. The edge of a strip must never be on screen, at any view.

const SPEC := "res://data/parallax.json"
const LEVEL_SCRIPT := "res://src/world/level.gd"
const AMBIENCE := "res://data/ambience.json"
## level.gd's constant for each plane (it owns the factors; data mirrors them)
const CONSTS := {"sky": "PARALLAX_SKY", "far": "PARALLAX_FAR",
	"near": "PARALLAX_NEAR", "fg": "PARALLAX_FG"}

var _spec: Dictionary = {}

func before_each() -> void:
	if _spec.is_empty():
		var raw: Variant = JSON.parse_string(FileAccess.get_file_as_string(SPEC))
		if raw is Dictionary:
			_spec = raw

func _planes() -> Dictionary:
	return _spec.get("planes", {})

func _view() -> Vector2:
	var v: Array = _spec.get("view", [400, 240])
	return Vector2(float(v[0]), float(v[1]))

## The strip height data/parallax.json asks for, the same formula
## tools/art/parallax_worlds.py paints to.
func _strip_h(plane: String) -> int:
	var p: Dictionary = _planes()[plane]
	var design := float(_spec.get("design_level_h", 480))
	return int(_view().y) + int(roundf(float(p["vertical"]) * (design - _view().y)))

func _bg(path: String, f: float, level_h: float) -> ParallaxBg:
	var b := ParallaxBg.new()
	b.level_h = level_h
	b.setup(path, f)
	return b

func _worlds() -> Array[String]:
	var out: Array[String] = []
	var raw: Variant = JSON.parse_string(FileAccess.get_file_as_string(AMBIENCE))
	var amb: Dictionary = raw if raw is Dictionary else {}
	var d: Dictionary = amb.get("default", {})
	var names: Array = [String(d.get("world", "jungle"))]
	for id: String in (amb.get("levels", {}) as Dictionary).keys():
		names.append(String((amb["levels"][id] as Dictionary).get("world", names[0])))
	for n: String in names:
		if not out.has(n):
			out.append(n)
	return out

# ------------------------------------------------------------------ direction
func test_a_plane_moves_at_its_factor_of_the_tiles() -> void:
	## 100 px of camera travel moves the tiles 100 px on screen and a plane
	## `factor * 100`. Measured on a strip wide enough not to wrap.
	for f: float in [0.10, 0.28, 0.58, 0.82]:
		var b := _bg("res://assets/sprites/bg_jungle_fg.png", f, 480.0)
		b.set_view(Rect2(0, 0, 400, 240))
		var a := b.screen_offset().x
		b.set_view(Rect2(100, 0, 400, 240))
		var shift := a - b.screen_offset().x
		near(shift, roundf(100.0 * f), 0.01, "factor %.2f moves %.0f px per 100" % [f, shift])
		b.free()

func test_further_planes_move_slower() -> void:
	var last := -1.0
	for plane: String in ["sky", "far", "near", "fg"]:
		var f := float((_planes()[plane] as Dictionary)["factor"])
		gt(f, last, "%s scrolls faster than the plane behind it" % plane)
		lt(f, 1.0, "%s scrolls slower than the tiles" % plane)
		last = f

func test_data_mirrors_the_factors_level_gd_uses() -> void:
	## Read from the source rather than loaded: level.gd needs the autoloads,
	## which a headless --script run does not have.
	var src := FileAccess.get_file_as_string(LEVEL_SCRIPT)
	for plane: String in CONSTS.keys():
		var re := RegEx.create_from_string("const %s := ([0-9.]+)" % String(CONSTS[plane]))
		var m := re.search(src)
		ok(m != null, "level.gd defines %s" % CONSTS[plane])
		if m == null:
			continue
		near(float((_planes()[plane] as Dictionary)["factor"]), float(m.get_string(1)),
			0.0001, "data/parallax.json %s factor matches level.gd" % plane)

# ------------------------------------------------------------------ vertical
func test_the_strip_edge_never_shows_vertically() -> void:
	## Sweep the whole vertical travel of a two-screen and a three-screen level:
	## the strip must cover the view at every row.
	var b := _bg("res://assets/sprites/bg_jungle_near.png", 0.58, 480.0)
	var h := b.texture.get_size().y
	for level_h: float in [480.0, 720.0]:
		b.level_h = level_h
		var y := 0.0
		while y <= level_h - 240.0:
			b.set_view(Rect2(0, y, 400, 240))
			var top := b.screen_offset().y
			ok(top <= 0.0 and top + h >= 240.0,
				"level %.0f, view y %.0f: strip spans %.0f..%.0f" % [level_h, y, top, top + h])
			y += 8.0
	b.free()

func test_vertical_rate_matches_the_factor_on_a_design_level() -> void:
	var design := float(_spec.get("design_level_h", 480))
	for plane: String in ["far", "near"]:
		var b := _bg("res://assets/sprites/bg_jungle_%s.png" % plane,
			float((_planes()[plane] as Dictionary)["factor"]), design)
		b.set_view(Rect2(0, 0, 400, 240))
		var a := b.screen_offset().y
		b.set_view(Rect2(0, design - 240.0, 400, 240))
		var moved := a - b.screen_offset().y
		near(moved / (design - 240.0), float((_planes()[plane] as Dictionary)["vertical"]),
			0.01, "%s moves vertically at its vertical factor" % plane)
		b.free()

func test_a_one_screen_level_shows_the_floor_of_the_strip() -> void:
	## No vertical travel: show the bottom rows, where the horizon is painted.
	var b := _bg("res://assets/sprites/bg_jungle_near.png", 0.58, 240.0)
	b.set_view(Rect2(0, 0, 400, 240))
	eq(b.screen_offset().y + b.texture.get_size().y, 240.0, "strip bottom on the view bottom")
	b.free()

# ------------------------------------------------------------------ strips
func test_every_strip_has_the_size_data_asks_for() -> void:
	for w: String in _worlds():
		for plane: String in ["sky", "far", "near", "fg"]:
			var path := "res://assets/sprites/bg_%s_%s.png" % [w, plane]
			if plane == "fg" and not ResourceLoader.exists(path):
				continue          # fg is optional per world
			var tex: Texture2D = load(path)
			ok(tex != null, "%s exists" % path)
			if tex == null:
				continue
			var p: Dictionary = _planes()[plane]
			eq(int(tex.get_width()), int(p["width"]), "%s width" % path)
			eq(int(tex.get_height()), _strip_h(plane), "%s height" % path)

func test_a_two_screen_level_never_shows_a_strip_repeat() -> void:
	## A strip repeating inside one level is the cheapest tell there is.
	for plane: String in ["sky", "far", "near", "fg"]:
		var p: Dictionary = _planes()[plane]
		var travel := float(p["factor"]) * _view().x
		gt(float(p["width"]) + 0.5, _view().x + travel,
			"%s strip covers the view plus a level of travel" % plane)
		eq(int(p["width"]) % 16, 0, "%s width keeps the 4x4 dither tiling across the wrap" % plane)

func test_a_level_draws_at_most_two_copies_per_plane() -> void:
	## Wider strips must not cost more draws than one-screen ones did.
	for plane: String in ["sky", "far", "near", "fg"]:
		var b := _bg("res://assets/sprites/bg_jungle_%s.png" % plane,
			float((_planes()[plane] as Dictionary)["factor"]), 480.0)
		var x := 0.0
		while x <= 400.0:
			b.set_view(Rect2(x, 0, 400, 240))
			lt(float(b.copies()), 2.5, "%s at x %.0f draws %d copies" % [plane, x, b.copies()])
			x += 4.0
		b.free()
