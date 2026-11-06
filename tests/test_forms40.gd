extends TestCase
## Kaya's animal forms at the 40 px era's scale (Kaya Refit, phase 3;
## tools/art/forms40.py). The drawings grew from 16x16 to 24-wide cells while
## the hitboxes stayed exactly as they were, so this checks the shipped sheets
## against the rules the generator promises and against the data that places
## them: nothing below the hitbox, room for a one-tile tunnel, the cling inside
## the hitbox's columns, narrow frames that fit a shaft, and a bounds file that
## agrees with the pixels.

## The collision every proof tape and boss gate depends on. Never changes.
const HITBOX := {
	"frog": Vector2i(12, 11),
	"fish": Vector2i(14, 9),
	"bird": Vector2i(12, 9),
}
## How many frames each sheet had before the redraw: every index the data used
## then must still exist, and still mean the same beat.
const OLD_FRAMES := {"frog": 9, "fish": 6, "bird": 10}
const TUNNEL := 16.0
const ROUNDING := 1.0
const NARROW_W := 16

var _cfg: Dictionary = {}
var _img: Dictionary = {}


func before_each() -> void:
	if not _cfg.is_empty():
		return
	for id: String in HITBOX.keys():
		var parsed: Variant = JSON.parse_string(
			FileAccess.get_file_as_string("res://data/forms/%s.json" % id))
		var d: Dictionary = parsed if parsed is Dictionary else {}
		_cfg[id] = d
		var tex: Texture2D = load(String(d.get("sprite", "")))
		_img[id] = tex.get_image() if tex != null else null


func _fw(id: String) -> int:
	return int((_cfg[id] as Dictionary).get("frame_w", 0))


func _fh(id: String) -> int:
	return int((_cfg[id] as Dictionary).get("frame_h", 0))


func _hb(id: String) -> Dictionary:
	return (_cfg[id] as Dictionary).get("hitbox", {})


func _frames(id: String, anim: String) -> Array:
	return (((_cfg[id] as Dictionary).get("anim", {}) as Dictionary).get(anim, {})
		as Dictionary).get("frames", [])


## Opaque extents of one frame: x = first col, y = first row, z = last col,
## w = last row; all -1 for an empty frame.
func _extent(id: String, f: int) -> Vector4i:
	var img: Image = _img[id]
	var fw := _fw(id)
	var e := Vector4i(fw, _fh(id), -1, -1)
	for y in _fh(id):
		for x in fw:
			if img.get_pixel(f * fw + x, y).a > 0.0:
				e = Vector4i(mini(e.x, x), mini(e.y, y), maxi(e.z, x), maxi(e.w, y))
	return e if e.z >= 0 else Vector4i(-1, -1, -1, -1)


func _count(id: String) -> int:
	var img: Image = _img[id]
	return img.get_width() / maxi(1, _fw(id))


func test_the_hitboxes_never_changed() -> void:
	for id: String in HITBOX.keys():
		var hb := _hb(id)
		var want: Vector2i = HITBOX[id]
		eq(int(hb.get("w", 0)), want.x, "%s hitbox width" % id)
		eq(int(hb.get("h", 0)), want.y, "%s hitbox height" % id)


func test_the_hitbox_is_centred_on_the_feet_of_the_cell() -> void:
	for id: String in HITBOX.keys():
		var hb := _hb(id)
		eq(int(hb["ox"]) * 2 + int(hb["w"]), _fw(id), "%s hitbox centred in the cell" % id)
		eq(int(hb["oy"]) + int(hb["h"]), _fh(id), "%s hitbox bottom on the cell bottom" % id)


func test_the_forms_are_drawn_bigger_than_before() -> void:
	## The point of the phase: no form is still a 16 px drawing beside her.
	for id: String in HITBOX.keys():
		ok(_img[id] != null, "%s sheet loads" % id)
		if _img[id] == null:
			continue
		var widest := 0
		for f in _count(id):
			var e := _extent(id, f)
			widest = maxi(widest, e.z - e.x + 1)
		gt(float(widest), 18.0, "%s is drawn wider than the old 16 px cell" % id)


func test_every_old_frame_index_still_exists() -> void:
	for id: String in HITBOX.keys():
		if _img[id] == null:
			continue
		gt(float(_count(id)) + 0.5, float(OLD_FRAMES[id]), "%s keeps frames 0-%d"
			% [id, int(OLD_FRAMES[id]) - 1])
		for f in _count(id):
			ok(_extent(id, f).x >= 0, "%s frame %d is not empty" % [id, f])


func test_nothing_is_drawn_below_the_hitbox() -> void:
	## A frog on a floor, a beached fish and a perched bird all have rock right
	## under the hitbox's bottom row. The cell ends there, and every frame
	## must reach it or stop above it -- checked on the alpha, not the layout.
	for id: String in HITBOX.keys():
		if _img[id] == null:
			continue
		var hb := _hb(id)
		var bottom := int(hb["oy"]) + int(hb["h"]) - 1
		for f in _count(id):
			lt(float(_extent(id, f).w), float(bottom) + 0.5, "%s frame %d below its hitbox"
				% [id, f])


func test_every_frame_fits_a_one_tile_tunnel() -> void:
	for id: String in HITBOX.keys():
		if _img[id] == null:
			continue
		var hb := _hb(id)
		var max_rise := TUNNEL - ROUNDING - float(hb["h"])
		for f in _count(id):
			var rise := float(hb["oy"]) - float(_extent(id, f).y)
			lt(rise, max_rise + 0.5, "%s frame %d rises %d px over the hitbox, max %d"
				% [id, f, int(rise), int(max_rise)])


func test_the_frog_clings_inside_its_hitbox_columns() -> void:
	## The wall is flush with the hitbox while she clings, on whichever side the
	## render facing puts it, so the cling may not overhang either side.
	var hb := _hb("frog")
	var lo := int(hb["ox"])
	var hi := lo + int(hb["w"]) - 1
	ok(not _frames("frog", "cling").is_empty(), "frog has a cling")
	for f: Variant in _frames("frog", "cling"):
		var e := _extent("frog", int(f))
		ok(e.x >= lo and e.z <= hi, "cling frame %d spans cols %d..%d, hitbox %d..%d"
			% [int(f), e.x, e.z, lo, hi])


func test_narrow_frames_fit_a_one_tile_shaft() -> void:
	## KayaPose.choose() swaps these in where nothing else fits sideways.
	var wanted := {"frog": ["narrow", "narrow_jump", "narrow_fall", "narrow_stoop"],
		"fish": ["narrow", "narrow_swim"]}
	for id: String in wanted.keys():
		for anim: String in wanted[id]:
			ok(not _frames(id, anim).is_empty(), "%s has %s" % [id, anim])
			for f: Variant in _frames(id, anim):
				var e := _extent(id, int(f))
				lt(float(e.z - e.x + 1), float(NARROW_W) + 0.5, "%s %s frame %d is %d px wide"
					% [id, anim, int(f), e.z - e.x + 1])


func test_each_bounds_file_matches_its_sheet() -> void:
	for id: String in HITBOX.keys():
		if _img[id] == null:
			continue
		var pose: Dictionary = (_cfg[id] as Dictionary).get("pose", {})
		eq(String(pose.get("bounds", "")), "res://assets/sprites/kaya_%s.bounds.json" % id,
			"%s pose points at its own bounds" % id)
		var rows: Array = KayaPose.bounds(String(pose.get("bounds", "")))
		eq(rows.size(), _count(id), "%s: one bounds entry per frame" % id)
		var img: Image = _img[id]
		var fw := _fw(id)
		var bad := 0
		for f in rows.size():
			var fr: Array = rows[f]
			eq(fr.size(), _fh(id), "%s frame %d has a row per pixel row" % [id, f])
			for y in fr.size():
				var lo := -1
				var hi := -1
				for x in fw:
					if img.get_pixel(f * fw + x, y).a > 0.0:
						if lo < 0:
							lo = x
						hi = x
				var e: Array = fr[y]
				if int(e[0]) != lo or int(e[1]) != hi:
					bad += 1
		eq(bad, 0, "rows where kaya_%s.bounds.json disagrees -- run tools/genart.sh" % id)


func test_the_nudge_can_clear_the_widest_overhang() -> void:
	## Beside a wall the drawn frame is shifted off the rock by up to
	## max_nudge_x. A cap smaller than the overhang leaves pixels in the wall.
	for id: String in HITBOX.keys():
		if _img[id] == null:
			continue
		var hb := _hb(id)
		var lo := int(hb["ox"])
		var hi := lo + int(hb["w"]) - 1
		var over := 0
		for f in _count(id):
			var e := _extent(id, f)
			over = maxi(over, maxi(lo - e.x, e.z - hi))
		var cap := float(((_cfg[id] as Dictionary).get("pose", {}) as Dictionary)
			.get("max_nudge_x", 0.0))
		gt(cap + 0.5, float(over), "%s overhangs %d px, nudge cap %.1f" % [id, over, cap])


func test_every_form_wears_her_outfit() -> void:
	## Whose frog is that? Hers: each sheet carries the straw of the hat, the
	## green of her top and the yellow of her shorts, from the same ramps.
	var parsed: Variant = JSON.parse_string(
		FileAccess.get_file_as_string("res://assets/palette.json"))
	var ramps: Dictionary = (parsed as Dictionary).get("ramps", {}) if parsed is Dictionary else {}
	for id: String in HITBOX.keys():
		if _img[id] == null:
			continue
		var img: Image = _img[id]
		var seen := {}
		for y in img.get_height():
			for x in img.get_width():
				var c := img.get_pixel(x, y)
				if c.a > 0.0:
					seen[Vector3i(c.r8, c.g8, c.b8)] = true
		for ramp: String in ["straw", "cloth", "gold"]:
			var found := false
			for step: Variant in (ramps.get(ramp, []) as Array):
				var s: Array = step
				if seen.has(Vector3i(int(s[0]), int(s[1]), int(s[2]))):
					found = true
					break
			ok(found, "%s sheet uses her %s ramp" % [id, ramp])
