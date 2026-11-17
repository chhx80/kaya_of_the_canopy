extends TestCase
## The HD pass contract (docs/plan-hd.md): world units never change, art ships
## at art_scale texels per unit, and every world-space draw goes through the
## one place that multiplies (Display.texture -> HdTexture).

const MANIFEST := "res://assets/art_scale.json"
## Art the game draws at 1x on purpose (tools/art/palette.py UI_1X).
const UI_1X := ["res://assets/fonts/font8.png", "res://assets/sprites/splash.png",
	"res://assets/sprites/icon.png"]

func _manifest() -> Dictionary:
	var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
	return (d as Dictionary).get("sheets", {}) if d is Dictionary else {}

func _scale_of(res_path: String) -> int:
	var rel := res_path.trim_prefix("res://assets/")
	return int((_manifest().get(rel, {}) as Dictionary).get("scale", -1))

func test_display_json_is_the_contract() -> void:
	eq(Display.art_scale(), 2, "ART_SCALE")
	eq(Display.view_size(), Vector2(308, 184), "the explore view")
	eq(Screen.W, 400, "the arena cell is unchanged")
	eq(Screen.H, 240)
	near(Display.view_size().x / float(Screen.W), 0.77, 0.005, "30% larger: 1/1.3 of the old view")

func test_the_render_target_holds_a_whole_arena_at_art_scale() -> void:
	var t := Display.render_texels()
	eq(t, Vector2i(800, 480), "a 400 x 240 arena at 2 texels per unit")
	ok(float(t.x) >= Display.view_size().x * Display.art_scale(), "and the explore view")

func test_the_manifest_records_every_shipped_png() -> void:
	var m := _manifest()
	ok(m.size() > 40, "art_scale.json lists the sheets (%d)" % m.size())
	for rel: String in m.keys():
		var path := "res://assets/" + rel
		var e: Dictionary = m[rel]
		var k := int(e.get("scale", 0))
		var img := Image.load_from_file(ProjectSettings.globalize_path(path))
		ok(img != null, "%s loads" % rel)
		if img == null:
			continue
		if UI_1X.has(path):
			eq(k, 1, "%s stays 1x" % rel)
			continue
		eq(k, Display.art_scale(), "%s ships at art_scale" % rel)
		eq(img.get_width() % k, 0, "%s width is whole world units" % rel)
		eq(img.get_height() % k, 0, "%s height is whole world units" % rel)

func test_an_hd_texture_reads_in_world_units() -> void:
	var t := Display.texture("res://assets/sprites/kaya_human.png")
	ok(t is HdTexture, "wrapped")
	eq(t.get_height(), 40, "Kaya's cell is 40 world units tall, whatever the texels")
	var base: Texture2D = load("res://assets/sprites/kaya_human.png")
	eq(base.get_height(), 40 * Display.art_scale(), "and 80 texels")
	ok(Display.texture("res://assets/sprites/kaya_human.png") == t, "one wrapper per sheet")

func test_world_image_is_the_sheet_in_world_units() -> void:
	var img := Display.world_image("res://assets/tiles/tileset.png")
	var base: Texture2D = load("res://assets/tiles/tileset.png")
	eq(img.get_width() * Display.art_scale(), base.get_width())

## Every asset the game code loads straight, without the wrapper, must be one
## that ships at 1x — or a sprite would draw at twice its size.
func test_no_world_art_is_loaded_around_the_wrapper() -> void:
	var re := RegEx.new()
	re.compile("(\\w+(?:\\.\\w+)?)\\(\\s*\"(res://assets/[^\"]+\\.png)\"")
	for f in _scripts("res://src"):
		var src := FileAccess.get_file_as_string(f)
		for m in re.search_all(src):
			var fn := m.get_string(1)
			var path := m.get_string(2)
			if fn == "Display.texture":
				eq(_scale_of(path), Display.art_scale(), "%s: %s is wrapped, so it must ship at art_scale" % [f, path])
			elif fn == "load" or fn == "preload":
				eq(_scale_of(path), 1, "%s loads %s raw, so it must ship at 1x" % [f, path])

## Sprites named in data/ are loaded through Display.texture by the nodes that
## draw them; they must all ship at art_scale.
func test_every_sprite_named_in_data_ships_at_art_scale() -> void:
	var re := RegEx.new()
	re.compile("\"(res://assets/[^\"]+\\.png)\"")
	for dir in ["res://data", "res://data/forms", "res://data/enemies", "res://data/weapons"]:
		for fn in DirAccess.get_files_at(dir):
			if not fn.ends_with(".json"):
				continue
			var src := FileAccess.get_file_as_string(dir + "/" + fn)
			for m in re.search_all(src):
				eq(_scale_of(m.get_string(1)), Display.art_scale(), "%s/%s names %s" % [dir, fn, m.get_string(1)])

func test_the_world_is_drawn_as_large_as_the_device_allows() -> void:
	var v := Display.view_size()
	# A 19.5:9 phone at the logical height a 4x stretch gives it.
	var r := Display.world_display_for(Vector2(639, 294), v)
	near(r.size.y, 294.0, 0.01, "a phone fills its height")
	near(r.size.x / r.size.y, v.x / v.y, 0.001, "at the view's own aspect")
	near(r.get_center().x, 639.0 * 0.5, 0.01, "centred")
	# A 4:3 tablet.
	r = Display.world_display_for(Vector2(455, 341), v)
	near(r.size.x, 455.0, 0.01, "a tablet fills its width")
	ok(r.size.y < 341.0, "and letterboxes")
	# The arena view: the whole cell, no stretch.
	r = Display.world_display_for(Vector2(639, 294), Vector2(Screen.W, Screen.H))
	near(r.size.x / r.size.y, float(Screen.W) / float(Screen.H), 0.001, "an arena keeps its own shape")

func test_the_arena_pull_back_eases_between_the_two_views() -> void:
	var a := Vector2(Screen.W, Screen.H)
	var e := Display.view_size()
	eq(CameraController.size_at(0.0, e, a), e)
	eq(CameraController.size_at(1.0, e, a), a)
	var mid := CameraController.size_at(0.5, e, a)
	ok(mid.x > e.x and mid.x < a.x, "halfway is in between")

func _scripts(dir: String) -> Array[String]:
	var out: Array[String] = []
	for d in DirAccess.get_directories_at(dir):
		out.append_array(_scripts(dir + "/" + d))
	for f in DirAccess.get_files_at(dir):
		if f.ends_with(".gd"):
			out.append(dir + "/" + f)
	return out
