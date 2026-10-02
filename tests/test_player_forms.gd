extends TestCase
## Every form must load, be internally consistent, and produce a jump arc that
## actually clears the gaps the levels are built around.

const TS := 16.0

func _apex_px(f: FormBase) -> float:
	# v² / 2g for the upward phase.
	return (f.jump_vel * f.jump_vel) / (2.0 * f.gravity)

func _airtime_s(f: FormBase) -> float:
	# up + down, symmetric while below terminal velocity.
	return 2.0 * absf(f.jump_vel) / f.gravity

func test_human_form_loads_with_every_tunable() -> void:
	var f := FormBase.load_form("human")
	ok(f != null, "human.json must exist")
	eq(f.id, "human")
	eq(f.move_mode, "ground")
	ok(f.can_attack, "the human form carries the blade")
	ok(f.can_climb, "the human form climbs vines")
	gt(f.max_run, 0.0)
	gt(f.gravity, 0.0)
	lt(f.jump_vel, 0.0, "jump velocity points up (negative Y)")

func test_human_jump_clears_three_tiles_but_not_four() -> void:
	var f := FormBase.load_form("human")
	var apex := _apex_px(f)
	gt(apex, 2.6 * TS, "must clear a 2-tile step comfortably")
	lt(apex, 3.4 * TS, "must NOT trivialise a 4-tile wall")

func test_human_jump_spans_the_three_tile_spike_pit() -> void:
	var f := FormBase.load_form("human")
	var reach := f.max_run * _airtime_s(f)
	gt(reach, 3.5 * TS, "a 3-tile pit has to be jumpable at full run")

func test_hitbox_fits_inside_a_one_tile_corridor() -> void:
	var f := FormBase.load_form("human")
	var hb: Dictionary = f.hitbox()
	lt(float(hb["w"]), TS, "must fit a 1-tile wide gap")
	lt(float(hb["h"]), 2.0 * TS, "must fit a 2-tile high corridor")

func test_has_anim_is_false_for_a_state_the_form_never_declared() -> void:
	var f := FormBase.load_form("human")
	not_ok(f.has_anim("there_is_no_such_state"))

## Phase B, docs/plan-art-motion.md, guard tests: every form's canonical state
## set — the states player.gd's `_resolve_anim_state()` can ask the form for,
## either the two cross-form render overlays (`turn`, `dance`) it gates on
## generically, or the states each form's own `anim_for()` returns.
##
## Phase E, docs/plan-art-motion.md: this used to be four separate test
## functions — one bespoke check for human (written in Phase A, before the
## animal forms existed) plus a shared `_assert_states()` helper called once
## per animal form in Phase B. Measured: the four were already identical in
## everything but the form id and its expected name list, so this is that,
## unified into the one canonical-set test over all four forms the plan asks
## for — one failure clearly says which form and which state regressed,
## nothing is lost by folding the human case in alongside the other three.
const CANONICAL_STATES: Dictionary = {
	"human": ["idle", "run", "jump", "fall", "land", "climb", "hurt",
		"turn", "skid", "push", "throw", "catch", "fidget", "dance"],
	"frog": ["idle", "jump", "fall", "cling", "hurt", "turn", "wallkick",
		"dance"],
	"bird": ["idle", "run", "jump", "fall", "fly", "glide", "hurt", "turn",
		"stall", "dance"],
	"fish": ["idle", "swim", "run", "jump", "fall", "flop", "hurt", "turn",
		"burst", "dance"],
}

func test_every_form_declares_its_canonical_state_set() -> void:
	for id: String in CANONICAL_STATES.keys():
		var f := FormBase.load_form(id)
		ok(f != null, "%s.json must exist" % id)
		if f == null:
			continue
		for name: String in (CANONICAL_STATES[id] as Array):
			var a: Dictionary = f.anim(name)
			ok(a.has("frames"), "%s anim '%s' needs frames" % [id, name])
			gt(float((a.get("frames", []) as Array).size()), 0.0,
				"%s anim '%s' is empty" % [id, name])
			ok(f.has_anim(name), "%s: has_anim('%s') must agree with anim()" % [id, name])

## Every form this test suite knows about must have a bespoke entry above —
## a canonical-set test that silently skips a new form is worse than no test,
## because it reports green while covering nothing. `test_sprite_sheet_for_
## each_form_exists_on_disk()` below already enumerates every form on disk the
## same way; this mirrors it so the two can never drift apart.
func test_every_form_on_disk_has_a_canonical_state_set_entry() -> void:
	for id in _form_ids():
		ok(CANONICAL_STATES.has(id),
			"form '%s' exists on disk but CANONICAL_STATES has no entry for it" % id)

func test_every_form_declares_turn_and_dance() -> void:
	## The two overlays player.gd's _resolve_anim_state() gates on generically
	## for every form, not just the ones with a bespoke list above — a new
	## form that forgets either falls silently through to its base animation,
	## which is exactly the failure mode has_anim() exists to make loud.
	for id in _form_ids():
		var f := FormBase.load_form(id)
		if f == null:
			continue
		ok(f.has_anim("turn"), "%s must declare 'turn'" % id)
		ok(f.has_anim("dance"), "%s must declare 'dance'" % id)

func test_sprite_sheet_for_each_form_exists_on_disk() -> void:
	for id in _form_ids():
		var f := FormBase.load_form(id)
		ok(f != null, "form %s loads" % id)
		if f == null:
			continue
		ok(FileAccess.file_exists(f.sprite_path()),
			"missing sheet %s for form %s" % [f.sprite_path(), id])

func _form_ids() -> PackedStringArray:
	var out := PackedStringArray()
	var d := DirAccess.open("res://data/forms")
	if d == null:
		return out
	d.list_dir_begin()
	var f := d.get_next()
	while f != "":
		if f.ends_with(".json"):
			out.append(f.get_basename())
		f = d.get_next()
	d.list_dir_end()
	out.sort()
	return out
