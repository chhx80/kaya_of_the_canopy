extends TestCase
## The follow camera's pure parts (refit phase 2): CameraMath, the geometry the
## camera node runs on, and WakeRule, when an ordinary enemy is awake. The node
## itself needs autoloads, so what it does in a running level is covered by
## tests/integration (integration_tests.gd's camera cases, and the camera audit
## every tape replay runs — tape_replay.gd).

const VIEW := Vector2(400, 240)
const LEVEL := Rect2(0, 0, 800, 480)

# ---------------------------------------------------------------- clamp
func test_the_view_never_leaves_the_level() -> void:
	eq(CameraMath.clamp_view(Vector2(-30, -10), LEVEL, VIEW), Vector2(0, 0), "top-left corner")
	eq(CameraMath.clamp_view(Vector2(900, 900), LEVEL, VIEW), Vector2(400, 240), "bottom-right corner")
	eq(CameraMath.clamp_view(Vector2(123, 45), LEVEL, VIEW), Vector2(123, 45), "free in between")

func test_a_bounds_the_size_of_the_view_holds_it_dead_still() -> void:
	var arena := Rect2(400, 240, 400, 240)
	for p: Vector2 in [Vector2(0, 0), Vector2(399, 239), Vector2(401, 241), Vector2(9999, 9999)]:
		eq(CameraMath.clamp_view(p, arena, VIEW), arena.position,
			"a one-screen arena admits exactly one view (from %s)" % str(p))

func test_a_bounds_narrower_than_the_view_pins_its_left_and_top() -> void:
	var small := Rect2(0, 0, 240, 160)
	eq(CameraMath.clamp_view(Vector2(50, 50), small, VIEW), Vector2(0, 0),
		"what the level clamp always did for a level smaller than a screen")

func test_a_bigger_arena_is_followed_inside() -> void:
	var wide := Rect2(400, 0, 800, 240)
	eq(CameraMath.clamp_view(Vector2(600, 30), wide, VIEW), Vector2(600, 0))
	eq(CameraMath.clamp_view(Vector2(100, 0), wide, VIEW), Vector2(400, 0))
	eq(CameraMath.clamp_view(Vector2(1000, 0), wide, VIEW), Vector2(800, 0))

# ---------------------------------------------------------------- vertical anchor
func test_a_jump_inside_the_band_does_not_move_the_view() -> void:
	for rise: float in [0.0, 10.0, 40.0, 56.0]:
		eq(CameraMath.anchored_y(300.0 - rise, 300.0, 56.0, 8.0), 300.0,
			"%.0f px up stays on the floor" % rise)
	eq(CameraMath.anchored_y(308.0, 300.0, 56.0, 8.0), 300.0, "a small drop too")

func test_climbing_or_falling_out_of_the_band_follows_from_its_edge() -> void:
	eq(CameraMath.anchored_y(200.0, 300.0, 56.0, 8.0), 256.0, "100 px up: the view rises 44")
	eq(CameraMath.anchored_y(400.0, 300.0, 56.0, 8.0), 392.0, "100 px down: the view falls 92")

func test_the_anchor_is_continuous_at_the_band_edges() -> void:
	near(CameraMath.anchored_y(243.999, 300.0, 56.0, 8.0), 300.0, 0.01, "just inside the top")
	near(CameraMath.anchored_y(243.0, 300.0, 56.0, 8.0), 299.0, 0.01, "just outside: no jump")
	near(CameraMath.anchored_y(309.0, 300.0, 56.0, 8.0), 301.0, 0.01, "same below")

# ---------------------------------------------------------------- pixel snap
func test_snap_keeps_a_followed_target_on_one_screen_pixel() -> void:
	# A camera lagging a running target by a constant 37.3 px: rounding each
	# separately makes her screen x alternate between 37 and 38. Snapping
	# rounds the gap instead, so her screen x never changes.
	var seen := {}
	for i in 60:
		var t := Vector2(500.0 + float(i) * 1.37, 300.0)
		var base := t - Vector2(37.3, 120.0)
		var cam := CameraMath.snap(base, t)
		eq(cam, cam.round(), "the view is whole pixels")
		seen[t.round().x - cam.x] = true
	eq(seen.size(), 1, "she sits on exactly one screen column: %s" % str(seen.keys()))

func test_snap_leaves_a_whole_pixel_camera_exactly_where_it_is() -> void:
	for t: Vector2 in [Vector2(10.5, 7.5), Vector2(333.3, 88.8), Vector2(0.49, 1.51)]:
		eq(CameraMath.snap(Vector2(120, 40), t), Vector2(120, 40),
			"a clamped or locked camera is never nudged (target %s)" % str(t))

func test_snap_never_strays_more_than_a_pixel() -> void:
	for i in 200:
		var base := Vector2(float(i) * 0.731, float(i) * 0.413)
		var t := base + Vector2(200.0 + float(i % 7) * 0.29, 120.0 - float(i % 5) * 0.37)
		var d := CameraMath.snap(base, t) - base
		ok(absf(d.x) <= 1.0 and absf(d.y) <= 1.0, "snap moved the camera by %s" % str(d))

# ---------------------------------------------------------------- hard zone
func test_keep_in_does_nothing_while_she_is_comfortably_inside() -> void:
	var v := Vector2(100, 100)
	eq(CameraMath.keep_in(v, VIEW, v + VIEW * 0.5, Vector2(64, 40)), v)

func test_keep_in_drags_the_view_just_far_enough() -> void:
	var v := Vector2(100, 100)
	eq(CameraMath.keep_in(v, VIEW, Vector2(300, 110), Vector2(64, 40)), Vector2(100, 70),
		"her centre 10 px from the top edge: the view rises 30 to put it 40 in")
	eq(CameraMath.keep_in(v, VIEW, Vector2(490, 200), Vector2(64, 40)), Vector2(154, 100),
		"and 10 px from the right edge: across by 54")

func test_keep_in_holds_her_inside_at_any_speed() -> void:
	var v := Vector2(0, 400)
	var t := Vector2(200, 520)
	for i in 120:
		t.y -= 9.0           # 540 px/s straight up, faster than anything in the game
		v = v.lerp(t - VIEW * 0.5, CameraMath.approach(6.0, 1.0 / 60.0))
		v = CameraMath.keep_in(v, VIEW, t, Vector2(64, 40))
		ok(Rect2(v, VIEW).grow(-39.9).has_point(t), "frame %d: she is in frame" % i)

# ---------------------------------------------------------------- arena ease
func test_the_arena_ease_starts_and_lands_softly() -> void:
	eq(CameraMath.ease(0.0), 0.0)
	eq(CameraMath.ease(1.0), 1.0)
	near(CameraMath.ease(0.5), 0.5, 0.0001, "symmetric")
	lt(CameraMath.ease(0.05), 0.01, "slow off the mark: not a snap")
	gt(CameraMath.ease(0.95), 0.99, "and slow into the lock")
	eq(CameraMath.ease(-1.0), 0.0, "clamped")
	eq(CameraMath.ease(2.0), 1.0, "clamped")

func test_the_ease_is_monotonic() -> void:
	var last := -1.0
	for i in 101:
		var v := CameraMath.ease(float(i) / 100.0)
		ok(v >= last, "the pan never backs up")
		last = v

func test_the_approach_is_frame_rate_independent() -> void:
	var one := CameraMath.approach(10.0, 1.0 / 30.0)
	var two := CameraMath.approach(10.0, 1.0 / 60.0)
	near(1.0 - one, (1.0 - two) * (1.0 - two), 1e-6, "two 60Hz steps = one 30Hz step")

# ---------------------------------------------------------------- wake rule
func test_an_awake_enemy_stays_awake_while_near_the_view() -> void:
	eq(WakeRule.decide(true, true, true, true), WakeRule.Act.STAY)
	eq(WakeRule.decide(true, false, true, false), WakeRule.Act.STAY, "its spawn need not be")

func test_an_awake_enemy_far_off_the_view_despawns() -> void:
	eq(WakeRule.decide(true, true, false, true), WakeRule.Act.DESPAWN)
	eq(WakeRule.decide(true, true, false, false), WakeRule.Act.DESPAWN)

func test_a_despawned_enemy_respawns_when_its_spawn_comes_near() -> void:
	eq(WakeRule.decide(false, true, false, true), WakeRule.Act.RESPAWN)
	eq(WakeRule.decide(false, true, false, false), WakeRule.Act.STAY, "not before")

func test_it_never_pops_back_in_on_a_spawn_already_in_view() -> void:
	# Despawned with its spawn in range: not clear, so no respawn there...
	var clear := WakeRule.next_clear(WakeRule.Act.DESPAWN, true, true)
	not_ok(clear, "despawning in sight of its spawn leaves it not clear")
	eq(WakeRule.decide(false, clear, false, true), WakeRule.Act.STAY, "so it stays gone")
	# ...until that spawn has been out of range once.
	clear = WakeRule.next_clear(WakeRule.Act.STAY, clear, false)
	ok(clear, "the spawn scrolling out of range clears it")
	eq(WakeRule.decide(false, clear, false, true), WakeRule.Act.RESPAWN, "and it comes back")

func test_respawning_uses_up_the_clear_flag() -> void:
	not_ok(WakeRule.next_clear(WakeRule.Act.RESPAWN, true, true))
	ok(WakeRule.next_clear(WakeRule.Act.DESPAWN, false, false),
		"despawning with the spawn out of range is clear at once")

## The one property the whole rule exists for, checked over every state:
## nothing is awake far from the view, and nothing that comes back does so
## anywhere but at a spawn that is in range.
func test_no_state_leaves_an_enemy_awake_far_away() -> void:
	for awake: bool in [true, false]:
		for clear: bool in [true, false]:
			for body_near: bool in [true, false]:
				for spawn_near: bool in [true, false]:
					var act := WakeRule.decide(awake, clear, body_near, spawn_near)
					var after := act == WakeRule.Act.RESPAWN or (awake and act == WakeRule.Act.STAY)
					if after and act == WakeRule.Act.STAY:
						ok(body_near, "awake and far: %s" % str([awake, clear, body_near, spawn_near]))
					if act == WakeRule.Act.RESPAWN:
						ok(spawn_near, "respawned out of range: %s" % str([awake, clear, body_near, spawn_near]))

# ---------------------------------------------------------------- tunables
func test_the_camera_tunables_are_sane() -> void:
	var d: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://data/camera.json"))
	ok(d is Dictionary, "data/camera.json parses")
	var c: Dictionary = d
	for k: String in ["lead_px", "lead_rate", "follow_x_rate", "follow_y_rate", "air_band_up_px",
			"air_band_down_px", "keep_in_x_px", "keep_in_y_px", "enemy_wake_margin_px", "enemy_sleep_margin_px",
			"arena_ease_s", "arena_release_px"]:
		ok(c.has(k), "camera.json names %s" % k)
	lt(float(c["enemy_sleep_margin_px"]), 160.0 - 16.0,
		"despawn well inside the replay audit's 'far' (tape_replay.gd FAR_OFF_VIEW_PX)")
	gt(float(c["enemy_sleep_margin_px"]), float(c["enemy_wake_margin_px"]),
		"despawning happens further out than waking: hysteresis, not thrash")
	gt(float(c["enemy_wake_margin_px"]), 0.0, "an enemy wakes before it is visible")
	gt(float(c["arena_ease_s"]), 0.0, "entering an arena eases rather than snaps")
	gt(float(c["arena_release_px"]), 0.0, "and the lock does not thrash on its rim")
	lt(float(c["lead_px"]), float(Screen.W) * 0.25, "the look-ahead keeps her well inside the view")
	lt(float(c["lead_px"]), float(Screen.W) * 0.5 - float(c["keep_in_x_px"]),
		"and the hard zone never fights the look-ahead")
	lt(float(c["air_band_up_px"]), float(Screen.H) * 0.5 - float(c["keep_in_y_px"]),
		"nor the floor anchor's band")
