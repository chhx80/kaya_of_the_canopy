extends TestCase
## Refit phase 3: the enemies and bosses redrawn at Kaya's scale
## (tools/art/enemies40.py). Two things matter more than the drawing, and this
## file measures both on the shipped sheets, the way a player sees them:
##
##   1. collision did not move -- the art is anchored on the unchanged box by a
##      `render` block, the box stays filled by drawn body, and the drawing is
##      not mostly outside it;
##   2. every telegraph is still a change of silhouette or of brightness that a
##      player can read, measured per tell, on the exact frames the JSON plays.
##
## The thresholds are measurements of the sheets (and of the 16/48 px sheets
## they replaced, where that is the bar), recorded in REPORT.md.

const DIR := "res://data/enemies"

## Smallest share of the hurtbox any frame may leave empty, per enemy: a
## hurtbox much bigger than what is drawn is the unfairness the Grove Warden's
## docstring records. Set a little under the measured minimum of each sheet,
## and never under what the sheet it replaced managed (stormcrest's roost is
## two legs under a body, and was 0.39 at 48 px).
const MIN_COVER := {
	"walker": 0.75, "jumper": 0.75, "shooter": 0.85, "swimmer": 0.95,
	"charger": 0.75, "dropper": 0.80, "flyer": 0.90,
	"boss_grove": 0.65, "tide_maw": 0.60, "stormcrest": 0.39,
	"brood_queen": 0.58, "obsidian_heart": 0.70,
}
## Smallest share of a frame's opaque pixels that must lie inside the box. The
## refit draws bigger than the box on purpose (antennae, crests, legs), as Kaya
## is drawn bigger than hers, but never so much bigger that the box is a
## minority of the animal.
const MIN_INSIDE := 0.30

var _img_cache: Dictionary = {}

func _cfg(id: String) -> Dictionary:
	return Enemy.load_config(id)

func _ids() -> PackedStringArray:
	var out := PackedStringArray()
	var d := DirAccess.open(DIR)
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

func _sheet(c: Dictionary) -> Image:
	var path := String(c.get("sprite", ""))
	if not _img_cache.has(path):
		var tex: Texture2D = load(path)
		_img_cache[path] = tex.get_image() if tex != null else null
	return _img_cache[path]

func _frames(c: Dictionary, anim: String) -> Array:
	var a: Dictionary = (c.get("anim", {}) as Dictionary).get(anim, {})
	return a.get("frames", [])

## Opaque test for one pixel of frame `f`.
func _op(img: Image, c: Dictionary, f: int, x: int, y: int) -> bool:
	return img.get_pixel(f * int(c["frame_w"]) + x, y).a > 0.0

func _top_row(img: Image, c: Dictionary, f: int) -> int:
	for y in int(c["frame_h"]):
		for x in int(c["frame_w"]):
			if _op(img, c, f, x, y):
				return y
	return int(c["frame_h"])

func _width(img: Image, c: Dictionary, f: int) -> int:
	var lo := 9999
	var hi := -1
	for y in int(c["frame_h"]):
		for x in int(c["frame_w"]):
			if _op(img, c, f, x, y):
				lo = mini(lo, x)
				hi = maxi(hi, x)
	return hi - lo + 1

func _count_rows(img: Image, c: Dictionary, f: int, y0: int, y1: int) -> int:
	var n := 0
	for y in range(y0, y1):
		for x in int(c["frame_w"]):
			if _op(img, c, f, x, y):
				n += 1
	return n

## Pixels brighter than `t` in luma: how much of a frame is "lit".
func _bright(img: Image, c: Dictionary, f: int, t: float = 0.8) -> int:
	var n := 0
	for y in int(c["frame_h"]):
		for x in int(c["frame_w"]):
			var col := img.get_pixel(f * int(c["frame_w"]) + x, y)
			if col.a > 0.0 and col.r * 0.299 + col.g * 0.587 + col.b * 0.114 > t:
				n += 1
	return n

# ------------------------------------------------------------------ anchors
func test_every_enemy_has_a_render_anchor_that_centres_its_box() -> void:
	for id in _ids():
		var c := _cfg(id)
		ok(c.has("render"), "%s has no render anchor" % id)
		var hb: Dictionary = c.get("hitbox", {})
		var at: Dictionary = c.get("render", {})
		var slack := float(c["frame_w"]) - float(hb["w"])
		lt(absf(float(at.get("ox", -99)) - slack * 0.5), 1.01,
			"%s art is not centred on its box" % id)
		lt(float(at.get("oy", 0)) + float(hb["h"]), float(c["frame_h"]) + 0.01,
			"%s box hangs below its frame" % id)

func test_the_sheets_are_the_refit_sizes() -> void:
	## A sheet regenerated at the old size, or a JSON left at it, draws a
	## 16 px cell of a 32 px animal: half a beetle.
	for id in _ids():
		var c := _cfg(id)
		var boss := bool(c.get("boss", false))
		eq(int(c["frame_w"]), 64 if boss else 32, "%s frame_w" % id)
		var img := _sheet(c)
		ok(img != null, "%s sheet loads" % id)
		if img != null:
			eq(img.get_height(), int(c["frame_h"]), "%s sheet height" % id)
			eq(img.get_width() % int(c["frame_w"]), 0, "%s sheet is whole cells" % id)

# ----------------------------------------------------------------- fairness
func test_every_frame_fills_its_hurtbox() -> void:
	for id in _ids():
		var c := _cfg(id)
		var img := _sheet(c)
		if img == null:
			continue
		var hb: Dictionary = c["hitbox"]
		var at: Dictionary = c["render"]
		var n := int(img.get_width() / int(c["frame_w"]))
		var worst := 1.0
		var worst_f := -1
		for f in n:
			var tot := 0
			var hit := 0
			for y in range(int(at["oy"]), int(at["oy"]) + int(hb["h"])):
				for x in range(int(at["ox"]), int(at["ox"]) + int(hb["w"])):
					tot += 1
					if _op(img, c, f, x, y):
						hit += 1
			var share := float(hit) / float(tot)
			if share < worst:
				worst = share
				worst_f = f
		gt(worst, float(MIN_COVER.get(id, 0.6)) - 0.001,
			"%s frame %d covers only %d%% of its hurtbox" % [id, worst_f, int(worst * 100.0)])

func test_no_frame_is_mostly_outside_its_box() -> void:
	for id in _ids():
		var c := _cfg(id)
		var img := _sheet(c)
		if img == null:
			continue
		var hb: Dictionary = c["hitbox"]
		var at: Dictionary = c["render"]
		var n := int(img.get_width() / int(c["frame_w"]))
		for f in n:
			var all := 0
			var inside := 0
			for y in int(c["frame_h"]):
				for x in int(c["frame_w"]):
					if not _op(img, c, f, x, y):
						continue
					all += 1
					if x >= int(at["ox"]) and x < int(at["ox"]) + int(hb["w"]) \
							and y >= int(at["oy"]) and y < int(at["oy"]) + int(hb["h"]):
						inside += 1
			gt(float(inside) / float(maxi(1, all)), MIN_INSIDE,
				"%s frame %d is mostly outside its box" % [id, f])

# --------------------------------------------------------------- telegraphs
## CHARGER: the crest stands up. The wind-up's held frame tops out above every
## frame of the patrol and of the charge itself.
func test_charger_tell_the_crest_stands_above_everything_else_it_does() -> void:
	var c := _cfg("charger")
	var img := _sheet(c)
	var wind: Array = _frames(c, "windup")
	var held := _top_row(img, c, int(wind[wind.size() - 1]))
	for anim in ["move", "charge", "dazed"]:
		for f: Variant in _frames(c, anim):
			lt(float(held), float(_top_row(img, c, int(f))) - 1.5,
				"charger wind-up crest is no taller than %s frame %d" % [anim, int(f)])

## JUMPER: the knees fold up. The coil (last wind-up frame) reaches higher
## than the sitting pose it starts from.
func test_jumper_tell_the_knees_rise_above_the_sitting_outline() -> void:
	var c := _cfg("jumper")
	var img := _sheet(c)
	var wind: Array = _frames(c, "windup")
	var idle := _top_row(img, c, int(_frames(c, "idle")[0]))
	var coil := _top_row(img, c, int(wind[wind.size() - 1]))
	lt(float(coil), float(idle) - 2.0, "the coiled hopper is no taller than the sitting one")

## SHOOTER: the bloom opens. The last frame before the spit is wider than any
## idle-sway frame.
func test_shooter_tell_the_petals_flare_wider_than_it_ever_sways() -> void:
	var c := _cfg("shooter")
	var img := _sheet(c)
	var wind: Array = _frames(c, "windup")
	var flare := _width(img, c, int(wind[wind.size() - 1]))
	for f: Variant in _frames(c, "idle"):
		gt(float(flare), float(_width(img, c, int(f))) + 3.0,
			"the flared bloom is not wider than idle frame %d" % int(f))

## DROPPER: legs let go. Every shiver frame has fewer pixels gripping the rock
## above its box than the cling pose, and the last has under two thirds.
func test_dropper_tell_legs_come_off_the_ceiling() -> void:
	var c := _cfg("dropper")
	var img := _sheet(c)
	var oy := int((c["render"] as Dictionary)["oy"])
	var cling := _count_rows(img, c, int(_frames(c, "cling")[0]), 0, oy)
	var tell: Array = _frames(c, "tell")
	for f: Variant in tell:
		lt(float(_count_rows(img, c, int(f), 0, oy)), float(cling),
			"tell frame %d grips the ceiling as hard as the cling" % int(f))
	lt(float(_count_rows(img, c, int(tell[tell.size() - 1]), 0, oy)), float(cling) * 0.67,
		"by the last shiver frame, a third of the grip has not let go")

## STORMCREST: up or down. Roosting is legs on the floor row; airborne is no
## legs at all, so the bottom six rows answer "can I hit it" by silhouette.
func test_stormcrest_roosts_on_legs_and_flies_without_them() -> void:
	var c := _cfg("stormcrest")
	var img := _sheet(c)
	var h := int(c["frame_h"])
	for p in ["_p1", "_p2", "_p3"]:
		for anim in ["idle", "walk", "windup", "land"]:
			for f: Variant in _frames(c, anim + p):
				gt(float(_count_rows(img, c, int(f), h - 6, h)), 10.0,
					"stormcrest %s%s frame %d has no legs on the floor" % [anim, p, int(f)])
		for f: Variant in _frames(c, "air" + p):
			eq(_count_rows(img, c, int(f), h - 6, h), 0,
				"stormcrest airborne frame %d still shows legs" % int(f))

## BROOD QUEEN and OBSIDIAN HEART: they light up. Every attack frame
## (windup, air, land) is brighter than every idle and walk frame of the same
## phase -- for the Queen this is what reads through her `dark_alpha`, for the
## Heart it is the flare that comes before the hit.
func test_the_lit_bosses_are_brighter_on_every_attack_frame() -> void:
	for id in ["brood_queen", "obsidian_heart"]:
		var c := _cfg(id)
		var img := _sheet(c)
		for p in ["_p1", "_p2", "_p3"]:
			var calm := 0
			for anim in ["idle", "walk"]:
				for f: Variant in _frames(c, anim + p):
					calm = maxi(calm, _bright(img, c, int(f)))
			for anim in ["windup", "air", "land"]:
				for f: Variant in _frames(c, anim + p):
					gt(float(_bright(img, c, int(f))), float(calm),
						"%s %s%s frame %d is no brighter than it is at rest" % [id, anim, p, int(f)])

## Every boss: the held windup frame (the gather) is a different silhouette
## from its idle, by a real number of pixels, in every phase.
func test_every_boss_gather_changes_its_outline() -> void:
	for id in _ids():
		var c := _cfg(id)
		if not bool(c.get("boss", false)):
			continue
		var img := _sheet(c)
		for p in ["_p1", "_p2", "_p3"]:
			var idle := int(_frames(c, "idle" + p)[0])
			var wind: Array = _frames(c, "windup" + p)
			var held := int(wind[wind.size() - 1])
			var diff := 0
			for y in int(c["frame_h"]):
				for x in int(c["frame_w"]):
					if _op(img, c, idle, x, y) != _op(img, c, held, x, y):
						diff += 1
			gt(float(diff), 120.0, "%s%s gather is barely a new outline (%d px)" % [id, p, diff])
