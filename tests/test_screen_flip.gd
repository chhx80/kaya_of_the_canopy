extends TestCase
## Screen-flip maths. The camera node itself needs autoloads, so the geometry
## lives in `Screen` where a headless run can reach it.

func test_screen_count_rounds_up_partial_screens() -> void:
	eq(Screen.count_for(400, 240), Vector2i(1, 1), "exactly one screen")
	eq(Screen.count_for(800, 240), Vector2i(2, 1))
	eq(Screen.count_for(401, 241), Vector2i(2, 2), "a single spare pixel still needs a screen")
	eq(Screen.count_for(0, 0), Vector2i(1, 1), "never zero screens")

func test_index_of_maps_points_to_screens() -> void:
	var s := Vector2i(2, 2)
	eq(Screen.index_of(Vector2(0, 0), s), Vector2i(0, 0))
	eq(Screen.index_of(Vector2(399, 239), s), Vector2i(0, 0), "last pixel of screen 0")
	eq(Screen.index_of(Vector2(400, 239), s), Vector2i(1, 0), "first pixel of screen 1")
	eq(Screen.index_of(Vector2(400, 240), s), Vector2i(1, 1))

func test_index_of_clamps_outside_the_level() -> void:
	var s := Vector2i(2, 2)
	eq(Screen.index_of(Vector2(-50, -50), s), Vector2i(0, 0))
	eq(Screen.index_of(Vector2(9999, 9999), s), Vector2i(1, 1))

func test_origin_and_rect_agree() -> void:
	eq(Screen.origin(Vector2i(1, 1)), Vector2(400, 240))
	var r := Screen.rect(Vector2i(2, 0))
	eq(r.position, Vector2(800, 0))
	eq(r.size, Vector2(400, 240))

# ---------------------------------------------------------------- device fit
## The world view is always exactly one screen and always centred, whatever the
## device aspect. If this drifts, the flip camera starts showing the next screen.
func test_the_world_view_is_always_one_screen_and_centred() -> void:
	for ui in [Vector2(400, 240), Vector2(522, 240), Vector2(400, 300), Vector2(960, 240)]:
		var r := Screen.world_rect_for(ui)
		eq(r.size, Vector2(W_H()), "world view must stay one screen at ui %v" % ui)
		near(r.get_center().x, ui.x * 0.5, 1.0, "centred horizontally at ui %v" % ui)
		near(r.get_center().y, ui.y * 0.5, 1.0, "centred vertically at ui %v" % ui)

func W_H() -> Vector2:
	return Vector2(Screen.W, Screen.H)

func test_a_wide_phone_leaves_a_side_margin_for_the_touch_buttons() -> void:
	# 19.5:9 at a 240 px logical height.
	var r := Screen.world_rect_for(Vector2(522, 240))
	gt(r.position.x, 40.0, "a phone must leave enough margin to hold a button")
	near(r.position.y, 0.0, 0.01, "and no vertical margin")

func test_a_four_three_tablet_leaves_a_vertical_margin_instead() -> void:
	var r := Screen.world_rect_for(Vector2(400, 300))
	near(r.position.x, 0.0, 0.01, "no side margin on 4:3")
	gt(r.position.y, 20.0, "but a usable band top and bottom")

func test_an_exact_five_three_display_has_no_margin_at_all() -> void:
	var r := Screen.world_rect_for(Vector2(Screen.W, Screen.H))
	eq(r.position, Vector2.ZERO, "no letterboxing when the aspect already matches")

func test_a_50x30_tile_level_is_exactly_2x2_screens() -> void:
	var w := TileWorld.new(50, 30)
	eq(Screen.count_for(w.pixel_width(), w.pixel_height()), Vector2i(2, 2))
