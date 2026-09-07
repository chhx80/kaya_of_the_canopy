extends TestCase
## Project settings that only bite on a real device, where nothing else would
## catch them until a build is in someone's hands.

func test_the_game_is_landscape_on_handhelds() -> void:
	var o := int(ProjectSettings.get_setting("display/window/handheld/orientation", -1))
	# 0 landscape, 2 reverse landscape, 4 sensor landscape.
	has([0, 2, 4], o, "handheld orientation must be a landscape mode, got %d" % o)

func test_logical_resolution_is_the_one_everything_is_drawn_for() -> void:
	eq(int(ProjectSettings.get_setting("display/window/size/viewport_width", 0)), Screen.W)
	eq(int(ProjectSettings.get_setting("display/window/size/viewport_height", 0)), Screen.H)

func test_rendering_stays_pixel_perfect() -> void:
	eq(String(ProjectSettings.get_setting("display/window/stretch/mode", "")), "viewport")
	eq(String(ProjectSettings.get_setting("display/window/stretch/aspect", "")), "keep")
	eq(String(ProjectSettings.get_setting("display/window/stretch/scale_mode", "")), "integer")
	eq(int(ProjectSettings.get_setting("rendering/textures/canvas_textures/default_texture_filter", -1)),
		0, "textures must be nearest-neighbour")

func test_sim_runs_at_sixty_hertz() -> void:
	eq(int(ProjectSettings.get_setting("physics/common/physics_ticks_per_second", 0)), 60)

func test_arm64_exports_are_possible() -> void:
	ok(bool(ProjectSettings.get_setting("rendering/textures/vram_compression/import_etc2_astc", false)),
		"ETC2/ASTC must be on or iOS and Android exports refuse to build")

func test_every_input_action_the_game_reads_is_defined() -> void:
	for action in ["move_left", "move_right", "move_up", "move_down",
			"jump", "attack", "pause"]:
		ok(ProjectSettings.has_setting("input/" + action), "missing input action '%s'" % action)

func test_the_app_icon_referenced_by_the_project_exists() -> void:
	var icon := String(ProjectSettings.get_setting("application/config/icon", ""))
	ne(icon, "", "the project needs an icon")
	ok(FileAccess.file_exists(icon), "missing app icon %s" % icon)
