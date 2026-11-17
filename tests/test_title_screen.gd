extends TestCase
## Kaya on the title screen: the owner's own picture of her
## (assets/title/kaya.png, cut from docs/reference/kaya_title_original.jpg by
## tools/cut_title_kaya.py), and where src/ui/menus/title_screen.gd puts her.
##
## The title needs the autoloads, which a headless --script run does not have,
## so its layout constants are read from source here, as
## tests/test_hud_portrait.gd reads hud.gd. The live layout and a tap on a row
## are checked in the game by tests/integration/integration_tests.gd.

const IMAGE := "res://assets/title/kaya.png"
const TITLE := "res://src/ui/menus/title_screen.gd"
const SCREEN := Vector2(400, 240)

func _const(name: String) -> String:
	var re := RegEx.create_from_string("const %s := (.+)" % name)
	var m := re.search(FileAccess.get_file_as_string(TITLE))
	return "" if m == null else m.get_string(1).strip_edges()

func _f(name: String) -> float:
	return float(_const(name))

func _nums(name: String) -> PackedFloat64Array:
	var s := _const(name)                       # "Vector2(22, 62)" / "Rect2(...)"
	var inner := s.substr(s.find("(") + 1).trim_suffix(")")
	var out := PackedFloat64Array()
	for p in inner.split(","):
		out.append(float(p))
	return out

func _vec(name: String) -> Vector2:
	var n := _nums(name)
	return Vector2(n[0], n[1])

func _image() -> Image:
	var img := Image.new()
	if img.load_png_from_buffer(FileAccess.get_file_as_bytes(IMAGE)) != OK:
		return null
	return img

func test_her_picture_ships_cut_out_of_its_page() -> void:
	var img := _image()
	ok(img != null, "assets/title/kaya.png exists")
	if img == null:
		return
	eq(img.get_pixel(0, 0).a, 0.0, "the page around her is transparent")
	gt(img.get_pixel(img.get_width() / 2, img.get_height() / 3).a, 0.99, "and she is not")

func test_she_is_shown_at_her_own_aspect() -> void:
	## "Do not change anything on Kaya": the rect she is drawn in must not
	## squash or stretch the picture.
	var img := _image()
	if img == null:
		return
	var size := _vec("KAYA_SIZE")
	var want := float(img.get_width()) / float(img.get_height())
	lt(absf(size.x / size.y - want), 0.005, "KAYA_SIZE has the picture's aspect (%.4f)" % want)

func test_she_is_the_hero_of_the_screen() -> void:
	## The in-game sprite is 40 world units tall.
	gt(_vec("KAYA_SIZE").y, 150.0, "she stands over 150 world units tall")

func test_nothing_is_drawn_over_her() -> void:
	var b := Rect2(_vec("KAYA_POS"), _vec("KAYA_SIZE"))
	var col := _f("COL_X")
	var half := _f("ROW_HALF_W")
	var arrow := 14.0 + 8.0                          # the ">" left of a row
	var menu := Rect2(col - half - arrow, _f("ROW0_Y"), (half + arrow) * 2.0, _f("ROW_H") * 4.0)
	ok(Rect2(Vector2.ZERO, SCREEN).encloses(b), "she is inside the screen: %s" % b)
	ok(not b.intersects(menu), "and clear of the menu rows: %s vs %s" % [b, menu])
	var face := _nums("KAYA_FACE")
	ok(Rect2(Vector2.ZERO, b.size).encloses(Rect2(face[0], face[1], face[2], face[3])),
		"KAYA_FACE is inside her picture")
