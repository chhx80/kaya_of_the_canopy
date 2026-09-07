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

func test_every_animation_referenced_by_the_controller_exists() -> void:
	var f := FormBase.load_form("human")
	for name in ["idle", "run", "jump", "fall", "climb", "hurt"]:
		var a: Dictionary = f.anim(name)
		ok(a.has("frames"), "anim '%s' needs frames" % name)
		gt(float((a["frames"] as Array).size()), 0.0, "anim '%s' is empty" % name)

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
