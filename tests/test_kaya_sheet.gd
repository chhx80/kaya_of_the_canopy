extends TestCase
## The 40 px Kaya's sheet against the data that addresses it (Kaya Refit,
## phase 1). The art is generated, the frame indices are hand-written in
## data/forms/human.json, and the render nudges read a bounds file the generator
## writes beside the sheet. Three files that must agree, and nothing else in
## either tier looks at all three together.

const FORM := "res://data/forms/human.json"
const HUB_SHEET := "res://assets/sprites/kaya_hub.png"

var _cfg: Dictionary = {}
var _img: Image = null


func before_each() -> void:
	if not _cfg.is_empty():
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(FORM))
	_cfg = parsed if parsed is Dictionary else {}
	var tex: Texture2D = load(String(_cfg.get("sprite", "")))
	_img = tex.get_image() if tex != null else null


func _anim_frames(name: String) -> Array:
	return ((_cfg.get("anim", {}) as Dictionary).get(name, {}) as Dictionary).get("frames", [])


## [first, last] opaque row of a frame, from the imported sheet's own alpha.
func _rows_span(f: int) -> Vector2i:
	var fw := int(_cfg["frame_w"])
	var lo := -1
	var hi := -1
	for y in _img.get_height():
		for x in fw:
			if _img.get_pixel(f * fw + x, y).a > 0.0:
				if lo < 0:
					lo = y
				hi = y
				break
	return Vector2i(lo, hi)


func _width(f: int) -> int:
	var fw := int(_cfg["frame_w"])
	var lo := fw
	var hi := -1
	for y in _img.get_height():
		for x in fw:
			if _img.get_pixel(f * fw + x, y).a > 0.0:
				lo = mini(lo, x)
				hi = maxi(hi, x)
	return hi - lo + 1


func test_the_cell_is_32_by_40_with_the_hitbox_at_her_feet() -> void:
	ok(_img != null, "kaya_human loads")
	if _img == null:
		return
	eq(int(_cfg["frame_w"]), 32)
	eq(int(_cfg["frame_h"]), 40)
	eq(_img.get_height(), 40, "the sheet is one row of 40 px cells")
	var hb: Dictionary = _cfg["hitbox"]
	eq(int(hb["w"]), 10, "the hitbox is unchanged")
	eq(int(hb["h"]), 22, "the hitbox is unchanged")
	eq(int(hb["ox"]) * 2 + int(hb["w"]), 32, "hitbox centred on column 16")
	eq(int(hb["oy"]) + int(hb["h"]), 40, "hitbox bottom on the cell bottom")

## The dance's arm-wave is a little hop, one pixel off the ground on purpose.
const HOP_FRAMES := [35]

func test_every_grounded_frame_stands_on_row_39() -> void:
	if _img == null:
		return
	for name: String in ["idle", "run", "land", "turn", "skid", "push", "throw", "catch",
			"fidget", "dance", "stoop", "stoop_walk", "narrow"]:
		for f: Variant in _anim_frames(name):
			if HOP_FRAMES.has(int(f)):
				continue
			var span := _rows_span(int(f))
			eq(span.y, 39, "%s frame %d: feet on row 39" % [name, int(f)])

func test_the_low_frames_fit_two_tiles() -> void:
	if _img == null:
		return
	for name: String in ["stoop", "stoop_walk", "swim"]:
		for f: Variant in _anim_frames(name):
			gt(float(_rows_span(int(f)).x), 7.5, "%s frame %d must start on row 8 or lower"
				% [name, int(f)])

func test_the_narrow_frames_fit_a_one_tile_shaft() -> void:
	if _img == null:
		return
	for name: String in ["narrow", "narrow_climb", "narrow_jump", "narrow_fall", "narrow_swim"]:
		ok(not _anim_frames(name).is_empty(), "%s has frames" % name)
		for f: Variant in _anim_frames(name):
			lt(float(_width(int(f))), 16.5, "%s frame %d must be at most 16 px wide"
				% [name, int(f)])

func test_the_bounds_file_matches_the_sheet() -> void:
	if _img == null:
		return
	var pose: Dictionary = _cfg.get("pose", {})
	var rows: Array = KayaPose.bounds(String(pose.get("bounds", "")))
	var fw := int(_cfg["frame_w"])
	eq(rows.size(), int(_img.get_width() / fw), "one bounds entry per frame")
	var bad := 0
	for f in rows.size():
		var fr: Array = rows[f]
		for y in fr.size():
			var lo := -1
			var hi := -1
			for x in fw:
				if _img.get_pixel(f * fw + x, y).a > 0.0:
					if lo < 0:
						lo = x
					hi = x
			var e: Array = fr[y]
			if int(e[0]) != lo or int(e[1]) != hi:
				bad += 1
	eq(bad, 0, "rows where kaya_human.bounds.json disagrees with the sheet -- run tools/genart.sh")

func test_the_hub_keeps_the_16_by_24_sheet() -> void:
	var tex: Texture2D = load(HUB_SHEET)
	ok(tex != null, "kaya_hub loads")
	if tex == null:
		return
	eq(tex.get_height(), 24, "the overworld Kaya is 24 px tall")
	gt(float(tex.get_width() / 16), 9.5, "frames 0 and 2-9 exist (hub_player.gd reads them)")
