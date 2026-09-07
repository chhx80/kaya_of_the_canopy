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

func test_a_50x30_tile_level_is_exactly_2x2_screens() -> void:
	var w := TileWorld.new(50, 30)
	eq(Screen.count_for(w.pixel_width(), w.pixel_height()), Vector2i(2, 2))
