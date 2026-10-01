extends TestCase
## Phase F, docs/plan-art-motion.md: the idle dance's guard test — reachable
## only from true idle, cancelled by any input/ground-loss on the very next
## frame, and (together with tests/test_player_forms.gd's canonical-state-set
## tests) its strip exists in every form's sheet.
##
## Driven directly off Player's own overlay methods the way
## tests/test_render_facing_fsm.gd drives RenderFacingFSM — no scene tree, no
## autoloads (ADR 003). Player extends Node2D, but `_update_overlays()` and
## `_resolve_anim_state()` never touch the node machinery only `_ready()` sets
## up (`sprite`, `add_child`), so a bare `Player.new()` with its fields set by
## hand is enough to drive the same overlay logic the real game runs.

const DT := 1.0 / 60.0

func _idle_player(form_id: String = "human") -> Player:
	var p := Player.new()
	p.form = FormBase.load_form(form_id)
	p.form_id = form_id
	p.facing = 1
	p.on_floor = true
	p.vel = Vector2.ZERO
	p.input = InputState.new()
	return p

func _run_idle_ticks(p: Player, seconds: float) -> void:
	var n := int(ceil(seconds / DT))
	for i in n:
		p._update_overlays(DT)

func test_dance_fires_after_five_seconds_of_true_idle() -> void:
	var p := _idle_player()
	_run_idle_ticks(p, Player.DANCE_IDLE_TIME + 0.05)
	eq(p._resolve_anim_state(), "dance", "five seconds of true idle must reach the dance")

func test_dance_is_not_reachable_before_five_seconds() -> void:
	var p := _idle_player()
	_run_idle_ticks(p, Player.DANCE_IDLE_TIME - 0.5)
	ne(p._resolve_anim_state(), "dance", "the dance must not fire early")

func test_dance_cancels_on_any_input_bit_the_very_next_frame() -> void:
	var p := _idle_player()
	_run_idle_ticks(p, Player.DANCE_IDLE_TIME + 0.05)
	eq(p._resolve_anim_state(), "dance", "sanity: dancing before the input")
	p.input.left = true
	p._update_overlays(DT)
	ne(p._resolve_anim_state(), "dance",
		"a held input bit must cancel the dance on the next tick")

func test_dance_cancels_on_ground_loss_the_very_next_frame() -> void:
	var p := _idle_player()
	_run_idle_ticks(p, Player.DANCE_IDLE_TIME + 0.05)
	eq(p._resolve_anim_state(), "dance")
	p.on_floor = false
	p._update_overlays(DT)
	ne(p._resolve_anim_state(), "dance", "leaving the ground must cancel the dance")

func test_dance_is_not_reachable_while_not_grounded() -> void:
	## _is_truly_idle() requires on_floor — an airborne form (a glide, a long
	## fall) must never be treated as idle no matter how long it holds still.
	var p := _idle_player("bird")
	p.on_floor = false
	_run_idle_ticks(p, Player.DANCE_IDLE_TIME + Player.FIDGET_IDLE_TIME)
	ne(p._resolve_anim_state(), "dance", "airborne must never read as idle")

func test_fidget_is_the_second_beat_once_the_dance_is_on_cooldown() -> void:
	## After a dance plays out, its own ~15s cooldown blocks the next 5s mark,
	## so continued idling reaches the 12s fidget mark instead — the two never
	## collide (docs/plan-art-motion.md, Phase F).
	var p := _idle_player()
	_run_idle_ticks(p, Player.DANCE_IDLE_TIME + 0.05)
	eq(p._resolve_anim_state(), "dance")
	var da: Dictionary = p.form.anim("dance")
	var dance_play := float((da["frames"] as Array).size()) / float(da.get("fps", 8.0))
	_run_idle_ticks(p, dance_play + 0.05)
	ne(p._resolve_anim_state(), "dance", "the dance must have finished")
	_run_idle_ticks(p, Player.FIDGET_IDLE_TIME)
	eq(p._resolve_anim_state(), "fidget", "fidget is the second beat, not a second dance")

func test_dance_strip_exists_in_every_form() -> void:
	for id in ["human", "frog", "bird", "fish"]:
		var f := FormBase.load_form(id)
		ok(f != null, "%s.json must exist" % id)
		if f == null:
			continue
		ok(f.has_anim("dance"), "%s must declare a dance strip" % id)
