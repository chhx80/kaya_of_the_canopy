extends TestCase
## Phase D, docs/plan-art-motion.md: the sprite-local hit-hold's guard test —
## the honest substitute for the classic hit-stop the plan rejects by name.
## `Enemy.hurt()` arms `_hold_t` on a non-lethal hit; `_update_anim()` is the
## ONLY place that reads it, and only to zero the delta fed to the frame-
## advance arithmetic. Driven directly off `_update_anim()` the way
## tests/test_idle_dance.gd drives Player's overlay methods: no scene tree, no
## autoloads (ADR 003) — `sprite` is set by hand since `_ready()` never runs.

const DT := 1.0 / 60.0

func _enemy() -> Enemy:
	var e := Enemy.new()
	e.sprite = Sprite2D.new()
	e._frame_size = Vector2i(16, 16)
	e.box = Vector2(14, 12)
	e.cfg = {
		"anim": {"move": {"frames": [0, 1, 2, 3], "fps": 20.0, "loop": true}},
		"hitbox": {"w": 14, "h": 12, "ox": 1, "oy": 2},
	}
	e._anim = "move"
	e.pos = Vector2(40.0, 20.0)
	e.vel = Vector2(12.0, 5.0)
	e.health = 7
	e.facing = 1
	return e

func test_hold_freezes_the_anim_clock_on_the_very_first_held_tick() -> void:
	var e := _enemy()
	e._hold_t = Enemy.HIT_HOLD_TIME
	var frame0 := e._anim_i
	# fps=20 would ordinarily move the frame inside 1/20s; one held tick must
	# not move it at all.
	e._update_anim(DT)
	eq(e._anim_i, frame0, "the frame must hold on the very first held tick")
	ok(e._hold_t > 0.0, "the hold timer itself ticks down, though")

func test_hold_holds_for_its_whole_duration_then_releases() -> void:
	var e := _enemy()
	e._hold_t = Enemy.HIT_HOLD_TIME
	var frame0 := e._anim_i
	var n := int(round(Enemy.HIT_HOLD_TIME / DT))
	for i in n:
		e._update_anim(DT)
		eq(e._anim_i, frame0, "frame must not move anywhere inside the hold window")
	ok(e._hold_t <= 0.0001, "the hold must have released by its own duration")

func test_hold_releases_and_the_anim_clock_resumes_afterward() -> void:
	var e := _enemy()
	e._hold_t = Enemy.HIT_HOLD_TIME
	var frame0 := e._anim_i
	var n := int(round(Enemy.HIT_HOLD_TIME / DT))
	for i in n:
		e._update_anim(DT)
	var moved := false
	for i in 30:
		e._update_anim(DT)
		if e._anim_i != frame0:
			moved = true
			break
	ok(moved, "the anim clock must resume once the hold releases")

## The whole safety argument for a render-side freeze instead of classic
## hit-stop: two enemies with identical starting state, one held and one not,
## must produce a bit-identical trace of every piece of sim state
## `_update_anim()` could in principle touch. It never does — this pins that.
func test_hold_never_writes_position_velocity_health_or_flash() -> void:
	var held := _enemy()
	held._hold_t = Enemy.HIT_HOLD_TIME
	held._flash = Enemy.FLASH_TIME
	var free := _enemy()
	free._flash = Enemy.FLASH_TIME
	for i in 12:
		held._update_anim(DT)
		free._update_anim(DT)
		eq(held.pos, free.pos, "pos must not depend on the hold")
		eq(held.vel, free.vel, "vel must not depend on the hold")
		eq(held.health, free.health, "health must not depend on the hold")
		near(held._flash, free._flash, 0.0001, "_flash must not depend on the hold")

func test_hold_duration_is_two_to_three_render_frames() -> void:
	# docs/plan-art-motion.md names the hold "2-3 render frames" by name;
	# hurt() and die() both need AudioManager/Fx, which this tier has no
	# autoloads for (ADR 003), so the branch that arms _hold_t is exercised in
	# tests/integration/integration_tests.gd instead — this pins the constant
	# itself, which is the part a unit test can see.
	gt(Enemy.HIT_HOLD_TIME, 1.0 / 60.0 - 0.0001, "at least ~2 render frames")
	lt(Enemy.HIT_HOLD_TIME, 4.0 / 60.0 + 0.0001, "at most ~3 render frames")

func test_fresh_enemy_is_never_held() -> void:
	var e := _enemy()
	eq(e._hold_t, 0.0, "a fresh enemy starts unheld")
