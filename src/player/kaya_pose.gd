class_name KayaPose
extends RefCounted
## Which of Kaya's frames to draw when the one her animation asks for does not
## suit the space she is in. Render-only: nothing here reads or writes anything
## but its arguments, and collision never sees the result.
##
## The 40 px sprite is 18 px taller than the 10x22 hitbox it stands on, so in a
## two-tile tunnel (17.8% of standable tiles, measured in phase 0) a standing
## frame puts her hat into the rock. Under a ceiling lower than the sprite she
## is drawn stooped instead. In water deep enough to swim she is drawn swimming.
## And in the air under a ceiling the drawn sprite may hang below the hitbox
## (`nudge_y`), because nothing is under her feet to show the gap.
##
## Pure and static so the unit tier can test it headless, and so
## tools/clipgate.sh can run the very same decision against every proof tape.
## Every tunable comes from the form's `pose` block (data/forms/human.json); a
## form without one (the frog, the fish, the bird) is passed straight through.

## tools/clipgate.sh switches these off (--no-pose, --no-stoop) to prove the
## gate fails without them. The game never touches them.
static var enabled := true
static var stoop_enabled := true


## Clear pixels above the hitbox, capped at `cap`. 0 means a ceiling touches her
## head; `cap` means nothing within reach. The hitbox's own columns always
## count. `reach` px either side of it count too -- the brim overhangs her by
## that much -- but only where the column is open at her head, so a tunnel
## mouth ahead of her is a ceiling and the wall she is standing against is not
## (a wall is the sideways fit's problem, see fits_x()).
static func headroom(world: TileWorld, pos: Vector2, box: Vector2, cap: float,
		reach: float = 0.0) -> float:
	if world == null:
		return cap
	var ts := float(TileData4.TILE_SIZE)
	var own := TileCollision.tile_range(pos.x, pos.x + box.x)
	var cols := TileCollision.tile_range(pos.x - reach, pos.x + box.x + reach)
	var top := pos.y
	var head := int(floor(top / ts))
	var best := cap
	for tx in range(cols.x, cols.y + 1):
		var side := tx < own.x or tx > own.y
		if side and world.is_solid(tx, head):
			continue
		var ty := int(floor((top - 0.001) / ts))
		while float(ty + 1) * ts > top - best:
			if world.is_solid(tx, ty):
				best = minf(best, maxf(0.0, top - float(ty + 1) * ts))
				break
			ty -= 1
	return best


## Clear pixels below the hitbox, over its columns, capped at `cap`. Only
## solid tiles count: a one-way plank under her is not something to draw a
## shin through, but it is not rock either, and she can be drawn over it.
static func floor_gap(world: TileWorld, pos: Vector2, box: Vector2, cap: float) -> float:
	if world == null:
		return 0.0
	var ts := float(TileData4.TILE_SIZE)
	var cols := TileCollision.tile_range(pos.x, pos.x + box.x)
	var bottom := pos.y + box.y
	var ty := int(floor((bottom + 0.001) / ts))
	while float(ty) * ts < bottom + cap:
		for tx in range(cols.x, cols.y + 1):
			if world.is_solid(tx, ty):
				return clampf(float(ty) * ts - bottom, 0.0, cap)
		ty += 1
	return cap


## The stooped animation that stands in for `anim` under a low ceiling, or ""
## for one that keeps its own frames there (the swim is already low; the
## narrow set is the shaft's answer). A vine that tops out in a two-tile
## tunnel draws her stooped too -- the climb's reaching arms are 18 px over the
## hitbox, and that is where the rock is.
static func stoop_for(anim: String) -> String:
	if anim == "swim" or anim.begins_with("narrow") or anim.begins_with("stoop"):
		return ""
	if anim == "run" or anim == "push" or anim == "skid" or anim == "turn":
		return "stoop_walk"
	return "stoop"


## The slung-hat animation that stands in for `anim` where the space is
## narrower than she is drawn -- a one-tile shaft is 16 px and the brim is 21.
static func narrow_for(anim: String) -> String:
	match anim:
		"climb":
			return "narrow_climb"
		"jump":
			return "narrow_jump"
		"fall":
			return "narrow_fall"
		"swim":
			return "narrow_swim"
	return "narrow"


## Per sprite row, the union of every frame of `anim`: [first, last] opaque
## column, or [-1, -1]. Cached per (bounds file, anim). Empty when the form has
## no bounds or no such animation.
static var _union_cache: Dictionary = {}

static func anim_rows(form: FormBase, anim: String) -> Array:
	var path := String((form.cfg.get("pose", {}) as Dictionary).get("bounds", ""))
	var key := "%s|%s" % [path, anim]
	if _union_cache.has(key):
		return _union_cache[key]
	var rows := bounds(path)
	var out: Array = []
	if not rows.is_empty() and form.has_anim(anim):
		var fh := form.frame_size().y
		for r in fh:
			out.append([-1, -1])
		for f: Variant in (form.anim(anim).get("frames", []) as Array):
			var i := int(f)
			if i < 0 or i >= rows.size():
				continue
			var fr: Array = rows[i]
			for r in mini(fh, fr.size()):
				var e: Array = fr[r]
				if int(e[0]) < 0:
					continue
				var u: Array = out[r]
				u[0] = int(e[0]) if int(u[0]) < 0 else mini(int(u[0]), int(e[0]))
				u[1] = maxi(int(u[1]), int(e[1]))
	_union_cache[key] = out
	return out


## How far any frame of `anim` draws above the hitbox top, in px, from its
## real opaque rows: the stoop rises 10, a swim stroke less than a stand.
static func rise(form: FormBase, anim: String, box: Vector2) -> float:
	var fh := form.frame_size().y
	var rows := anim_rows(form, anim)
	for r in rows.size():
		if int((rows[r] as Array)[0]) >= 0:
			return maxf(0.0, float(fh - r) - box.y)
	return float(fh) - box.y


## Whether some sideways shift of at most `cap` px keeps every frame of an
## animation (`rows`, its per-row union) off the walls either side of her,
## tile row by tile row. The cell sits with its column `ox` on the hitbox's left
## edge and its bottom row on the hitbox's bottom, as Player draws it. Rock over
## the hitbox's own columns is a ceiling or floor, not a wall, and is skipped.
static func fits_x(rows: Array, flip: bool, fw: int, ox: float, world: TileWorld,
		pos: Vector2, box: Vector2, cap: float, dy: float = 0.0) -> bool:
	if rows.is_empty() or world == null:
		return true
	var ts := float(TileData4.TILE_SIZE)
	var own := TileCollision.tile_range(pos.x, pos.x + box.x)
	var top := pos.y + box.y - float(rows.size()) + dy
	var need_right := -INF     ## the shift must be at least this (rock on her left)
	var need_left := INF       ## ...and at most this (rock on her right)
	var lo_ty := int(floor(top / ts))
	var hi_ty := int(floor((pos.y + box.y + dy - 0.001) / ts))
	for ty in range(lo_ty, hi_ty + 1):
		var c0 := 1 << 20
		var c1 := -1
		for r in rows.size():
			var wy := top + float(r) + 0.5
			if int(floor(wy / ts)) != ty:
				continue
			var e: Array = rows[r]
			if int(e[0]) < 0:
				continue
			var a := int(e[0])
			var b := int(e[1])
			if flip:
				var t := a
				a = fw - 1 - b
				b = fw - 1 - t
			c0 = mini(c0, a)
			c1 = maxi(c1, b)
		if c1 < 0:
			continue
		var wl := pos.x - ox + float(c0)
		var wr := pos.x - ox + float(c1 + 1)
		# Out to `cap` beyond the drawn span on each side: a wall the frame does
		# not touch yet still bounds how far it may be shifted toward it.
		for tx in range(own.x - 1, int(floor((wl - cap) / ts)) - 1, -1):
			if world.is_solid(tx, ty):
				need_right = maxf(need_right, float(tx + 1) * ts - wl)
				break
		for tx in range(own.y + 1, int(floor((wr + cap - 0.001) / ts)) + 1):
			if world.is_solid(tx, ty):
				need_left = minf(need_left, float(tx) * ts - wr)
				break
	return maxf(need_right, -cap) <= minf(need_left, cap)


## The animation to draw. `anim` is what the animation state machine asked for;
## `flip` is whether the sprite is drawn facing left; `wet` is
## Actor.submerged(). A form whose data has no `pose` block is passed straight
## through. In order: water makes an airborne frame a swim; a ceiling lower than
## the sprite makes it a stoop; and a space the result cannot fit sideways, at
## any shift up to `max_nudge_x`, makes it the slung-hat narrow set.
static func choose(anim: String, form: FormBase, world: TileWorld, pos: Vector2,
		box: Vector2, on_floor: bool, wet: bool, flip: bool = false) -> String:
	var pose: Dictionary = form.cfg.get("pose", {})
	if not enabled or pose.is_empty() or world == null:
		return anim
	var fs := form.frame_size()
	var ox := float((form.hitbox() as Dictionary).get("ox", 0))
	var cap := float(pose.get("max_nudge_x", 0.0))
	var out := anim
	var swim_from: Array = pose.get("swim_anims", [])
	if wet and not on_floor and swim_from.has(anim) and form.has_anim("swim"):
		out = "swim"
	var up := rise(form, out, box)
	if stoop_enabled and headroom(world, pos, box, up, float(pose.get("headroom_reach", 0.0))) < up:
		var alt := stoop_for(out)
		if alt != "" and form.has_anim(alt):
			out = alt
	var dy := nudge_y(out, form, world, pos, box, on_floor)
	if fits_x(anim_rows(form, out), flip, fs.x, ox, world, pos, box, cap, dy):
		return out
	# Low and narrow at once -- the end of a two-tile tunnel, against its wall --
	# is the slung-hat crouch; the slung-hat stand is as tall as any frame.
	var narrow := "narrow_stoop" if out.begins_with("stoop") else narrow_for(out)
	if form.has_anim(narrow):
		return narrow
	return out


## Render-space drop, in px, for a sprite in the air under a ceiling: the part
## of the frame's rise the headroom cannot hold, limited by the clear space
## under her feet. Zero on the ground, where her feet are where her feet are.
static func nudge_y(anim: String, form: FormBase, world: TileWorld, pos: Vector2,
		box: Vector2, on_floor: bool) -> float:
	var pose: Dictionary = form.cfg.get("pose", {})
	if not enabled or pose.is_empty() or world == null or on_floor:
		return 0.0
	var r := rise(form, anim, box)
	var short := r - headroom(world, pos, box, r, float(pose.get("headroom_reach", 0.0)))
	if short <= 0.0:
		return 0.0
	return minf(short, floor_gap(world, pos, box, short))


## Whether the landing squash / launch stretch may scale the sprite this tick.
## A stretch adds 15% to the height and a squash 15% to the width; under a
## ceiling that already sets the pose, the extra pixels go straight into rock.
static func allows_scale(anim: String, chosen: String) -> bool:
	return anim == chosen


## Whether a vertical stretch of `scale_y` still fits under the ceiling. The
## stretch is pinned at the feet, so the whole drawn height (hitbox plus the
## frame's rise above it) grows by `scale_y`. `choose()` and `nudge_y()` reason
## about the UNscaled rise, so without this the launch stretch drew 1-2 px into
## the rock exactly where the headroom equals the frame: five frames across
## deeps_2, heights_3 and ruins_4 in `tools/clipgate.sh --all-forms`.
static func allows_stretch(form: FormBase, anim: String, world: TileWorld, pos: Vector2,
		box: Vector2, scale_y: float) -> bool:
	if not enabled or scale_y <= 1.0 or world == null:
		return true
	var pose: Dictionary = form.cfg.get("pose", {})
	var r := rise(form, anim, box)
	var need := (box.y + r) * scale_y - box.y
	return headroom(world, pos, box, need, float(pose.get("headroom_reach", 0.0))) >= need


## Per-frame, per-row opaque extents of a sheet, from the `.bounds.json` the art
## generator writes beside it (tools/art/kaya40.py write_bounds). Cached; an
## empty array when the form has none, which turns the wall nudge off.
static var _bounds_cache: Dictionary = {}

static func bounds(path: String) -> Array:
	if path == "":
		return []
	if _bounds_cache.has(path):
		return _bounds_cache[path]
	var out: Array = []
	var f := FileAccess.open(path, FileAccess.READ)
	if f != null:
		var parsed: Variant = JSON.parse_string(f.get_as_text())
		if parsed is Dictionary:
			out = (parsed as Dictionary).get("rows", [])
	_bounds_cache[path] = out
	return out


## How far the drawn cell overlaps solid tiles beside her, as the shift that
## would clear it: positive moves the sprite right (rock on her left), negative
## left. `rows` is one frame's [first, last] opaque column per row; `org` is
## where the cell's (0, 0) lands in the world and `sc` its scale. Tiles over the
## hitbox's own columns are a ceiling or a floor, not a wall, and are left to
## the stoop and nudge_y -- shifting sideways cannot clear them.
static func wall_overlap(rows: Array, flip: bool, fw: int, org: Vector2, sc: Vector2,
		world: TileWorld, hb: Rect2) -> Vector2:
	var ts := float(TileData4.TILE_SIZE)
	var push_left := 0.0       ## rock on her right
	var push_right := 0.0      ## rock on her left
	var mid := hb.position.x + hb.size.x * 0.5
	for r in rows.size():
		var e: Array = rows[r]
		var c0 := int(e[0])
		if c0 < 0:
			continue
		var c1 := int(e[1])
		if flip:
			var t := c0
			c0 = fw - 1 - c1
			c1 = fw - 1 - t
		var wl := org.x + sc.x * float(c0)
		var wr := org.x + sc.x * float(c1 + 1)
		var wy := org.y + sc.y * (float(r) + 0.5)
		var ty := int(floor(wy / ts))
		for tx in range(int(floor(wl / ts)), int(floor((wr - 0.001) / ts)) + 1):
			if not world.is_solid(tx, ty):
				continue
			var t0 := float(tx) * ts
			if t0 < hb.end.x and t0 + ts > hb.position.x:
				continue                      # over the hitbox: not a wall
			if t0 + ts * 0.5 >= mid:
				push_left = maxf(push_left, wr - t0)
			else:
				push_right = maxf(push_right, t0 + ts - wl)
	return Vector2(push_right, push_left)


## Render-space sideways shift that keeps the drawn frame off a wall, up to
## `cap` px: the wide brim stops at the rock and her body stops with it, the
## way a hat that size would. 0 when nothing is in the way, or when rock on
## both sides means no shift can clear it (a shaft narrower than the sprite).
static func nudge_x(rows: Array, flip: bool, fw: int, org: Vector2, sc: Vector2,
		world: TileWorld, hb: Rect2, cap: float) -> float:
	if not enabled or rows.is_empty() or world == null or cap <= 0.0:
		return 0.0
	var o := wall_overlap(rows, flip, fw, org, sc, world, hb)
	var dx := 0.0
	if o.x > 0.0 and o.y <= 0.0:
		dx = ceilf(o.x)
	elif o.y > 0.0 and o.x <= 0.0:
		dx = -ceilf(o.y)
	if dx == 0.0 or absf(dx) > cap:
		return 0.0
	var after := wall_overlap(rows, flip, fw, org + Vector2(dx, 0.0), sc, world, hb)
	if after.x > 0.0 or after.y > 0.0:
		return 0.0
	return dx
