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

# ---------------------------------------------------------------- vertical look-ahead
const DT := 1.0 / 60.0

func _cam_cfg() -> Dictionary:
	return JSON.parse_string(FileAccess.get_file_as_string("res://data/camera.json"))

## Drive look_mode/climb_time through a body moving under `gravity` from
## `vy0`, standing again once it is back down `drop` below where it left (a
## landing), and return the most the look-ahead was ever asked for.
func _jump_mode(c: Dictionary, vy0: float, gravity: float, max_fall: float, drop: float) -> int:
	var y := 0.0
	var vy := vy0
	var t := 0.0
	var worst := 0
	for i in 600:
		vy = minf(vy + gravity * DT, max_fall)
		y += vy * DT
		var landed := vy > 0.0 and y >= drop
		t = CameraMath.climb_time(t, vy, landed, float(c["look_climb_speed"]),
			float(c["look_climb_decay"]), DT)
		var m := CameraMath.look_mode(landed, false, minf(y, drop), vy, t,
			float(c["look_fall_drop_px"]), float(c["look_fall_speed"]), float(c["look_climb_s"]))
		if m != 0:
			worst = m
		if landed:
			break
	return worst

func test_an_ordinary_jump_never_moves_the_view_vertically() -> void:
	var c := _cam_cfg()
	for form: String in ["human", "frog", "bird"]:
		var f: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/forms/%s.json" % form))
		var jv := float(f["jump_vel"])
		var g := float(f["gravity"])
		var mf := float(f["max_fall"])
		for drop: float in [0.0, -32.0, 16.0, 32.0, 48.0]:
			eq(_jump_mode(c, jv, g, mf, drop), 0,
				"a %s jump landing %.0f below where it left: no vertical look" % [form, drop])

func test_a_long_drop_leads_the_view_down() -> void:
	var c := _cam_cfg()
	eq(_jump_mode(c, 0.0, 760.0, 330.0, 8.0 * 16.0), 1, "stepping off an 8-tile drop looks down")
	eq(_jump_mode(c, -260.0, 760.0, 330.0, 6.0 * 16.0), 1, "and so does jumping into a 6-tile one")

func test_a_sustained_climb_leads_the_view_up() -> void:
	var c := _cam_cfg()
	var spd := float(c["look_climb_speed"])
	var dec := float(c["look_climb_decay"])
	var need := float(c["look_climb_s"])
	# A vine at the human's climb speed.
	var t := 0.0
	var frames := 0
	while t < need and frames < 600:
		t = CameraMath.climb_time(t, -60.0, false, spd, dec, DT)
		frames += 1
	lt(float(frames) * DT, need + 0.05, "a vine climb leads up after %.2f s" % (float(frames) * DT))
	# A bird flapping as fast as it may: -172 every 0.24 s against 420.
	t = 0.0
	var vy := 0.0
	var fired := -1.0
	for i in 240:
		if i % 15 == 0:
			vy = -172.0
		vy += 420.0 * DT
		t = CameraMath.climb_time(t, vy, false, spd, dec, DT)
		if fired < 0.0 and CameraMath.look_mode(false, false, -float(i), vy, t, 52.0, 120.0, need) == -1:
			fired = float(i) * DT
	ok(fired > 0.0 and fired < 1.0, "a flapping climb leads up within a second (%.2f s)" % fired)
	# A frog climbing a wall: wall jump, a short cling, again.
	t = 0.0
	fired = -1.0
	var clock := 0.0
	for hop in 8:
		vy = -305.0
		while vy < 0.0:
			vy += 700.0 * DT
			t = CameraMath.climb_time(t, vy, false, spd, dec, DT)
			clock += DT
			if fired < 0.0 and t >= need:
				fired = clock
		for k in 6:      # a tenth of a second on the wall, sliding
			t = CameraMath.climb_time(t, 34.0, false, spd, dec, DT)
			clock += DT
	ok(fired > 0.0, "a frog wall climb leads up a few hops in (%.2f s)" % fired)

func test_standing_or_swimming_never_looks() -> void:
	eq(CameraMath.look_mode(true, false, 200.0, 300.0, 5.0, 52.0, 120.0, 0.6), 0, "standing")
	eq(CameraMath.look_mode(false, true, 200.0, 300.0, 5.0, 52.0, 120.0, 0.6), 0, "swimming")
	eq(CameraMath.climb_time(3.0, -200.0, true, 40.0, 2.0, DT), 0.0, "standing empties the clock")

func test_the_look_puts_her_on_the_third_line_at_a_steady_fall() -> void:
	# Follow a steady 330 px/s fall with the real exponential follow: once the
	# lead is fully in, her centre settles look_y_ahead_px above the view's.
	var c := _cam_cfg()
	var rate := CameraMath.follow_rate(float(c["follow_y_rate"]), float(c["look_follow_y_rate"]), 1.0)
	var ahead := float(c["look_y_ahead_px"])
	var y := 0.0
	var cam := 0.0
	for i in 600:
		y += 330.0 * DT
		var goal := CameraMath.blend_look(y - 8.0, y, 330.0, 1.0, ahead, rate,
			float(c["look_y_max_lag_px"]))
		cam = lerpf(cam, goal, CameraMath.approach(rate, DT))
	# The 60 Hz follow trails a few units less than the continuous v / rate
	# the lead assumes, so she settles a touch above the line, never below it.
	near(cam - y, ahead + 1.5, 1.5, "she sits %.1f above the view's centre" % (cam - y))
	var v := Display.view_size()
	gt(v.y * 0.5 + ahead - 10.0, 5.0 * 16.0, "and sees at least five tiles under her feet")
	lt(ahead, v.y * 0.5 - float(c["keep_in_y_px"]), "without the hard zone fighting it")
	gt(float(c["look_y_max_lag_px"]), 340.0 / float(c["follow_y_rate"]),
		"the lag lead covers the fastest fall at the slowest follow")

func test_the_follow_quickens_only_with_the_look() -> void:
	eq(CameraMath.follow_rate(6.0, 12.0, 0.0), 6.0, "no look: the ordinary follow")
	eq(CameraMath.follow_rate(6.0, 12.0, -1.0), 12.0, "a full look either way")
	eq(CameraMath.follow_rate(6.0, 12.0, 0.5), 9.0, "in proportion between")

func test_the_follow_speed_cap() -> void:
	eq(CameraMath.limit_step(100.0, 130.0, 8.0), 108.0, "down, capped")
	eq(CameraMath.limit_step(100.0, 70.0, 8.0), 92.0, "up, capped")
	eq(CameraMath.limit_step(100.0, 103.0, 8.0), 103.0, "a small step passes untouched")
	var c := _cam_cfg()
	var cap := float(c["follow_y_max_speed"]) / 60.0
	lt(cap, 12.0 - 108.0 / 60.0 - 1.0, "inside the tape audit's 12-a-frame step, with a run across")
	gt(cap, 340.0 / 60.0 + 1.0, "and fast enough to get ahead of the fastest fall")

func test_the_look_blend_is_continuous_through_a_turn() -> void:
	near(CameraMath.blend_look(100.0, 90.0, 0.0, 0.0001, 30.0, 6.0, 60.0), 100.0, 0.01, "a hair down")
	near(CameraMath.blend_look(100.0, 90.0, 0.0, -0.0001, 30.0, 6.0, 60.0), 100.0, 0.01, "a hair up")
	eq(CameraMath.blend_look(100.0, 90.0, 300.0, 0.0, 30.0, 6.0, 60.0), 100.0, "off is the anchor")
	eq(CameraMath.look_y(0.0, 9999.0, 1, 30.0, 6.0, 60.0), 90.0, "the lag lead is capped")

# ---------------------------------------------------------------- arena approach
const ARENA := Rect2(400, 240, 400, 240)

func test_the_approach_band_sits_only_above_the_arena() -> void:
	var z := CameraMath.approach_zone(ARENA, 128.0)
	ok(z.has_point(Vector2(600, 120)), "128 above the arena's top is in it")
	ok(not z.has_point(Vector2(600, 100)), "further up is not")
	ok(not z.has_point(Vector2(380, 300)), "beside the arena is not: a walk in has the floor in view")
	ok(z.encloses(ARENA), "and the arena itself is")

func test_the_approach_starts_only_on_a_real_fall_into_the_band() -> void:
	ok(CameraMath.approach_on(false, true, true, true, false, true), "falling into the band")
	ok(not CameraMath.approach_on(false, true, true, true, false, false),
		"a hop in a corridor that crosses the band is not a fall")
	ok(not CameraMath.approach_on(false, true, true, true, true, true), "nor is standing in it")
	ok(not CameraMath.approach_on(false, true, false, true, false, true), "nor falling beside it")
	ok(not CameraMath.approach_on(false, false, true, true, false, true),
		"nor falling back in before she was ever clear of it after a release")

func test_the_approach_holds_through_the_fall_and_lets_go_on_a_landing() -> void:
	ok(CameraMath.approach_on(true, true, true, true, false, false),
		"held once started, whatever her speed does")
	ok(CameraMath.approach_on(true, false, false, true, false, false), "and across the band's rim")
	ok(not CameraMath.approach_on(true, true, true, true, true, false),
		"a landing above the arena ends it: she is platforming, not dropping in")
	ok(not CameraMath.approach_on(true, true, false, false, false, false), "and so does drifting off")

func test_a_release_does_not_re_engage_the_approach() -> void:
	# unlock() disarms it; only leaving the band (grown by the release margin) re-arms.
	ok(not CameraMath.approach_armed(false, true), "still near after a release: disarmed")
	ok(CameraMath.approach_armed(false, false), "clear of it: armed again")
	ok(CameraMath.approach_armed(true, true), "armed stays armed")

func test_a_drop_counts_only_with_nothing_between_her_and_the_arena() -> void:
	# 6 x 8 tiles: a ledge three tiles wide on row 3, the arena's top at row 6.
	var rows: Array = []
	for y in 8:
		var r: Array = []
		for x in 6:
			r.append(1 if (y == 3 and x < 3) or y == 7 else 0)
		rows.append(r)
	var w := TileWorld.from_rows(rows)
	ok(CameraMath.clear_below(w, 66.0, 78.0, 40.0, 96.0), "over the open shaft: clear")
	ok(not CameraMath.clear_below(w, 20.0, 32.0, 40.0, 96.0), "over the ledge: it catches her")
	ok(not CameraMath.clear_below(w, 44.0, 56.0, 40.0, 96.0), "grazing the ledge's edge still does")
	ok(CameraMath.clear_below(w, 20.0, 32.0, 64.0, 96.0), "already past it: clear")

func test_the_approach_hold_meets_the_arena_view_at_its_top() -> void:
	var m := Vector2(48, 32)
	eq(CameraMath.approach_hold(m, 200.0, 128.0), m, "above the band: the whole hard zone")
	eq(CameraMath.approach_hold(m, 128.0, 128.0), m, "at its top: still whole")
	eq(CameraMath.approach_hold(m, 64.0, 128.0), m * 0.5, "half way down: half")
	eq(CameraMath.approach_hold(m, 0.0, 128.0), Vector2.ZERO, "at the arena: none, the lock's own view")
	eq(CameraMath.approach_hold(m, -5.0, 128.0), Vector2.ZERO, "inside: none")
	eq(CameraMath.approach_hold(m, 16.0, 0.0), m * 0.5, "a band thinner than the margin fades over the margin")
	# The goal rides her fall at (1 + margin / band) of her speed.
	var c := _cam_cfg()
	var band := float(c["arena_approach_px"])
	lt(340.0 / 60.0 * (1.0 + float(c["keep_in_y_px"]) / band), 8.0,
		"so the fastest fall moves the approach's goal under 8 a frame")
	# With no margin left, keep_in only insists she is in view at all, which the
	# arena view already does: the approach goal and the lock's goal coincide.
	var arena_view := Vector2(400, 240)
	eq(CameraMath.keep_in(arena_view, Vector2(400, 240), Vector2(600, 241),
		CameraMath.approach_hold(m, -1.0, band)), arena_view, "the hand-over is seamless")

func test_the_steered_ease_matches_the_lerp_on_a_still_target() -> void:
	var from := Vector2(0, 0)
	var to := Vector2(90, 120)
	var p := from
	var t := 0.0
	for i in 36:
		var e0 := CameraMath.ease(t)
		t = minf(1.0, t + 1.0 / 36.0)
		p = CameraMath.ease_step(p, to, e0, CameraMath.ease(t), 1e9)
		near(p.distance_to(from.lerp(to, CameraMath.ease(t))), 0.0, 0.01, "frame %d" % i)
	eq(p, to, "and arrives with the ease")

func test_the_steered_ease_never_steps_past_its_cap_and_still_arrives() -> void:
	var p := Vector2.ZERO
	var to := Vector2(0, 300)
	var t := 0.0
	var frames := 0
	while p.distance_to(to) > 0.01 and frames < 200:
		var e0 := CameraMath.ease(t)
		t = minf(1.0, t + 1.0 / 36.0)
		var q := CameraMath.ease_step(p, to, e0, CameraMath.ease(t), 8.0)
		ok(q.distance_to(p) <= 8.0 + 0.001, "frame %d steps %.2f" % [frames, q.distance_to(p)])
		p = q
		frames += 1
	lt(float(frames), 200.0, "a capped ease still arrives (in %d frames)" % frames)
	# A pan pushed off its line (by the hard zone) carries on from where it is.
	var pushed := CameraMath.ease_step(Vector2(50, 0), Vector2(100, 0), 0.5, 0.6, 1e9)
	near(pushed.x, 60.0, 0.001, "a fifth of what is left, from where the view is")

func test_the_approach_band_is_deep_enough_for_the_pull_back() -> void:
	var c := _cam_cfg()
	var band := float(c["arena_approach_px"])
	# What a fall covers while the pull-back eases in, from the moment the fall
	# counts (look_fall_speed) toward the human's max fall: the band must hold
	# most of it, or the arena view is still arriving as she crosses the top.
	var f: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://data/forms/human.json"))
	var v := float(c["look_fall_speed"])
	var y := 0.0
	var t := 0.0
	while t < float(c["arena_ease_s"]):
		v = minf(float(f["max_fall"]), v + float(f["gravity"]) / 60.0)
		y += v / 60.0
		t += 1.0 / 60.0
	gt(band, y * 0.5, "the band holds over half the ease's fall (%.0f)" % y)
	lt(band, 240.0, "and no deeper than an arena cell: an approach, not a second arena")

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
			"arena_ease_s", "arena_release_px", "look_y_ahead_px", "look_y_max_lag_px",
			"look_fall_speed", "look_fall_drop_px", "look_climb_speed", "look_climb_s",
			"look_climb_decay", "look_y_in_rate", "look_y_out_rate", "look_y_vel_rate",
			"look_follow_y_rate", "follow_y_max_speed", "arena_approach_px"]:
		ok(c.has(k), "camera.json names %s" % k)
	lt(float(c["enemy_sleep_margin_px"]), 160.0 - 16.0,
		"despawn well inside the replay audit's 'far' (tape_replay.gd FAR_OFF_VIEW_PX)")
	gt(float(c["enemy_sleep_margin_px"]), float(c["enemy_wake_margin_px"]),
		"despawning happens further out than waking: hysteresis, not thrash")
	gt(float(c["enemy_wake_margin_px"]), 0.0, "an enemy wakes before it is visible")
	gt(float(c["arena_ease_s"]), 0.0, "entering an arena eases rather than snaps")
	gt(float(c["arena_release_px"]), 0.0, "and the lock does not thrash on its rim")
	# Against the view the camera actually shows (docs/plan-hd.md), not the
	# 400 x 240 arena cell these were first tuned for.
	var v := Display.view_size()
	lt(float(c["lead_px"]), v.x * 0.25, "the look-ahead keeps her well inside the view")
	lt(float(c["lead_px"]), v.x * 0.5 - float(c["keep_in_x_px"]),
		"and the hard zone never fights the look-ahead")
	lt(float(c["air_band_up_px"]), v.y * 0.5 - float(c["keep_in_y_px"]),
		"nor the floor anchor's band")
