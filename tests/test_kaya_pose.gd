extends TestCase
## KayaPose: which frame the 40 px Kaya is drawn as, decided from the space she
## is in (Kaya Refit, phase 1). Pure and static, so it is tested here headless
## against hand-built rooms. tools/clipgate.sh is the outcome check -- every
## proof tape, every drawn pixel -- and these are the cases that pin down why it
## passes, so a regression shows up as a named rule rather than as a level.
##
## Legend (TileWorld's default tile data): 0 empty, 1 solid dirt, 8 water.

const TS := 16
const BOX := Vector2(10, 22)

var human: FormBase


func before_each() -> void:
	KayaPose.enabled = true
	KayaPose.stoop_enabled = true
	if human == null:
		human = FormBase.load_form("human")


## A room `w` tiles wide and `h` tall, solid all round, plus the `solid` tiles
## inside it. The floor is the bottom row.
func _room(w: int, h: int, solid: Array = []) -> TileWorld:
	var rows: Array = []
	for y in h:
		var r: Array = []
		for x in w:
			r.append(1 if (y == 0 or y == h - 1 or x == 0 or x == w - 1) else 0)
		rows.append(r)
	for c: Vector2i in solid:
		rows[c.y][c.x] = 1
	return TileWorld.from_rows(rows)


## Standing on the floor of `world`, hitbox left edge at `x`.
func _feet(world: TileWorld, x: float) -> Vector2:
	return Vector2(x, float((world.height - 1) * TS) - BOX.y)


# ---------------------------------------------------------------- headroom
func test_headroom_is_capped_in_the_open() -> void:
	var w := _room(10, 8)
	near(KayaPose.headroom(w, _feet(w, 70.0), BOX, 18.0), 18.0, 0.001)

func test_headroom_in_a_two_tile_tunnel_is_ten() -> void:
	# floor is row 6 (y 96), ceiling row 3 (bottom y 64): 32 px clear, hitbox 22
	var w := _room(10, 7, [Vector2i(3, 3), Vector2i(4, 3), Vector2i(5, 3), Vector2i(6, 3)])
	near(KayaPose.headroom(w, _feet(w, 70.0), BOX, 18.0), 10.0, 0.001)

func test_a_wall_beside_her_is_not_a_ceiling() -> void:
	# A full-height wall at column 6, her hitbox flush against it at x 86..96.
	var solid: Array = []
	for y in range(1, 7):
		solid.append(Vector2i(6, y))
	var w := _room(10, 8, solid)
	near(KayaPose.headroom(w, _feet(w, 86.0), BOX, 18.0, 7.0), 18.0, 0.001,
		"the brim's reach must skip a column that is rock at her head")

func test_an_overhang_ahead_within_the_brim_is_a_ceiling() -> void:
	# Tunnel mouth: rock on row 3 from column 6 rightward, open below it. She
	# stands at x 84..94, just short of it, so it is not over her hitbox.
	var solid: Array = []
	for x in range(6, 9):
		solid.append(Vector2i(x, 3))
	var w := _room(10, 7, solid)
	near(KayaPose.headroom(w, _feet(w, 84.0), BOX, 18.0, 0.0), 18.0, 0.001,
		"hitbox columns alone see nothing")
	near(KayaPose.headroom(w, _feet(w, 84.0), BOX, 18.0, 7.0), 10.0, 0.001,
		"the brim's reach does")


# ---------------------------------------------------------------- choose
func _choose(anim: String, w: TileWorld, p: Vector2, on_floor: bool = true,
		wet: bool = false, flip: bool = false) -> String:
	return KayaPose.choose(anim, human, w, p, BOX, on_floor, wet, flip)

func test_open_ground_passes_every_animation_through() -> void:
	var w := _room(12, 8)
	for a: String in ["idle", "run", "jump", "fall", "climb", "turn"]:
		eq(_choose(a, w, _feet(w, 90.0)), a, "%s in the open" % a)

func test_a_low_ceiling_stoops_her() -> void:
	var solid: Array = []
	for x in range(1, 11):
		solid.append(Vector2i(x, 3))
	var w := _room(12, 7, solid)
	eq(_choose("idle", w, _feet(w, 90.0)), "stoop")
	eq(_choose("run", w, _feet(w, 90.0)), "stoop_walk")
	eq(_choose("land", w, _feet(w, 90.0)), "stoop")

func test_the_stoop_fits_a_two_tile_tunnel() -> void:
	# Two tiles is 32 px; the hitbox is 22, so nothing may rise more than 10 --
	# 9, keeping a pixel for the rounding of a float position to the screen.
	for a: String in ["stoop", "stoop_walk", "swim"]:
		lt(KayaPose.rise(human, a, BOX), 9.001, "%s must fit a two-tile tunnel" % a)
		gt(KayaPose.rise(human, a, BOX), 0.0, "%s still has a head above the hitbox" % a)

func test_a_one_tile_shaft_slings_the_hat() -> void:
	# A 16 px shaft at column 5, walls either side, six rows tall.
	var solid: Array = []
	for y in range(1, 7):
		solid.append(Vector2i(4, y))
		solid.append(Vector2i(6, y))
	var w := _room(11, 9, solid)
	var p := Vector2(83.0, 60.0)          # inside the shaft, centred on the vine
	eq(_choose("climb", w, p, false), "narrow_climb")
	eq(_choose("jump", w, p, false), "narrow_jump")
	eq(_choose("fall", w, p, false), "narrow_fall")
	var rows := KayaPose.anim_rows(human, "narrow_climb")
	ok(KayaPose.fits_x(rows, false, 32, 11.0, w, p, BOX, 8.0), "and the narrow set fits it")

func test_water_makes_an_airborne_frame_a_swim() -> void:
	var rows: Array = []
	for y in 10:
		var r: Array = []
		for x in 12:
			r.append(1 if (y == 9 or x == 0 or x == 11) else (8 if y >= 2 else 0))
		rows.append(r)
	var w := TileWorld.from_rows(rows)
	var p := Vector2(90.0, 80.0)
	eq(_choose("fall", w, p, false, true), "swim")
	eq(_choose("fall", w, p, false, false), "fall", "dry, the fall stays a fall")
	eq(_choose("run", w, p, true, true), "run", "walking the lake bed is not swimming")

func test_a_form_without_a_pose_block_is_untouched() -> void:
	var frog := FormBase.load_form("frog")
	var solid: Array = []
	for x in range(1, 11):
		solid.append(Vector2i(x, 3))
	var w := _room(12, 7, solid)
	eq(KayaPose.choose("idle", frog, w, _feet(w, 90.0), Vector2(14, 12), true, false), "idle")

func test_switching_it_off_is_a_pass_through() -> void:
	var solid: Array = []
	for x in range(1, 11):
		solid.append(Vector2i(x, 3))
	var w := _room(12, 7, solid)
	KayaPose.enabled = false
	eq(_choose("idle", w, _feet(w, 90.0)), "idle")
	KayaPose.enabled = true
	KayaPose.stoop_enabled = false
	ne(_choose("idle", w, _feet(w, 90.0)), "stoop")
	KayaPose.stoop_enabled = true


# ---------------------------------------------------------------- nudges
func test_facing_a_wall_the_brim_stops_at_it() -> void:
	# Wall at column 6 (x 96); hitbox flush against it at 86..96, facing it.
	var solid: Array = []
	for y in range(1, 7):
		solid.append(Vector2i(6, y))
	var w := _room(10, 8, solid)
	var p := _feet(w, 86.0)
	var rows: Array = KayaPose.bounds("res://assets/sprites/kaya_human.bounds.json")[0]
	var org := p + Vector2(-11, -18)
	var hb := Rect2(p, BOX)
	var before := KayaPose.wall_overlap(rows, false, 32, org, Vector2.ONE, w, hb)
	gt(before.y, 0.0, "the idle brim reaches past a flush wall")
	var dx := KayaPose.nudge_x(rows, false, 32, org, Vector2.ONE, w, hb, 8.0)
	lt(dx, 0.0, "so she is drawn shifted away from it")
	lt(absf(dx), 8.001, "by no more than max_nudge_x")
	eq(KayaPose.wall_overlap(rows, false, 32, org + Vector2(dx, 0), Vector2.ONE, w, hb),
		Vector2.ZERO, "and the shifted frame is clear")

func test_no_sideways_nudge_in_the_open() -> void:
	var w := _room(12, 8)
	var p := _feet(w, 90.0)
	var rows: Array = KayaPose.bounds("res://assets/sprites/kaya_human.bounds.json")[0]
	near(KayaPose.nudge_x(rows, false, 32, p + Vector2(-11, -18), Vector2.ONE, w,
		Rect2(p, BOX), 8.0), 0.0, 0.001)

func test_airborne_under_a_ceiling_the_sprite_hangs_lower() -> void:
	# Two-tile room, hitbox pressed to the ceiling mid-jump: 10 px under her feet.
	var solid: Array = []
	for x in range(1, 11):
		solid.append(Vector2i(x, 3))
	var w := _room(12, 7, solid)
	var p := Vector2(90.0, 64.0)          # top flush with the ceiling's underside
	near(KayaPose.nudge_y("stoop", human, w, p, BOX, false), KayaPose.rise(human, "stoop", BOX),
		0.001, "with the hitbox's top on the rock, all of the frame's rise hangs below")
	near(KayaPose.nudge_y("stoop", human, w, p, BOX, true), 0.0, 0.001,
		"never on the ground: her feet are where her feet are")
