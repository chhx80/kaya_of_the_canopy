class_name TileCollision
extends RefCounted
## Axis-separated AABB sweep against a TileWorld.
##
## Everything is static and takes plain values, so `tests/test_tile_collision.gd`
## can exercise every edge case without instancing a scene. Rects are top-left
## anchored, in pixels, and may hold fractional positions; only the *render*
## position is rounded to whole pixels.

const TS := TileData4.TILE_SIZE
const EPS := 0.001
## Never step further than this in one sub-step, so nothing tunnels through a tile.
const MAX_STEP := float(TS) - 1.0

class Result extends RefCounted:
	var rect: Rect2
	var hit_left := false
	var hit_right := false
	var hit_ceiling := false
	var on_floor := false
	## The tile that stopped downward motion, if any (used for breakables).
	var floor_tile := Vector2i(-1, -1)
	var ceiling_tile := Vector2i(-1, -1)
	var wall_tile := Vector2i(-1, -1)

	func hit_wall() -> bool:
		return hit_left or hit_right


static func tile_range(a: float, b: float) -> Vector2i:
	## Inclusive tile index range covering the pixel span [a, b).
	return Vector2i(int(floor(a / TS)), int(floor((b - EPS) / TS)))


static func _solid_for(world: TileWorld, tx: int, ty: int) -> bool:
	return world.is_solid(tx, ty)


## Move along X only. `rect` is modified into the returned Result.
static func move_x(world: TileWorld, rect: Rect2, dx: float) -> Result:
	var res := Result.new()
	res.rect = rect
	if is_zero_approx(dx):
		return res
	var remaining := dx
	while absf(remaining) > 0.0:
		var step: float = clampf(remaining, -MAX_STEP, MAX_STEP)
		remaining -= step
		var r := res.rect
		r.position.x += step
		var rows := tile_range(r.position.y, r.position.y + r.size.y)
		if step > 0.0:
			var tx := int(floor((r.position.x + r.size.x - EPS) / TS))
			for ty in range(rows.x, rows.y + 1):
				if _solid_for(world, tx, ty):
					r.position.x = float(tx * TS) - r.size.x
					res.hit_right = true
					res.wall_tile = Vector2i(tx, ty)
					remaining = 0.0
					break
		else:
			var tx := int(floor(r.position.x / TS))
			for ty in range(rows.x, rows.y + 1):
				if _solid_for(world, tx, ty):
					r.position.x = float((tx + 1) * TS)
					res.hit_left = true
					res.wall_tile = Vector2i(tx, ty)
					remaining = 0.0
					break
		res.rect = r
	return res


## Move along Y only.
## `drop_through` disables one-way platforms for this move (player pressing down+jump).
static func move_y(world: TileWorld, rect: Rect2, dy: float, drop_through: bool = false) -> Result:
	var res := Result.new()
	res.rect = rect
	if is_zero_approx(dy):
		# Still report standing on ground so idle actors keep on_floor.
		res.on_floor = is_on_floor(world, rect, drop_through)
		return res
	var remaining := dy
	while absf(remaining) > 0.0:
		var step: float = clampf(remaining, -MAX_STEP, MAX_STEP)
		remaining -= step
		var r := res.rect
		var prev_bottom := r.position.y + r.size.y
		r.position.y += step
		var cols := tile_range(r.position.x, r.position.x + r.size.x)
		if step > 0.0:
			var ty := int(floor((r.position.y + r.size.y - EPS) / TS))
			for tx in range(cols.x, cols.y + 1):
				var blocks := _solid_for(world, tx, ty)
				if not blocks and not drop_through and world.is_oneway(tx, ty):
					# One-way: only catches you if your feet started above its top edge.
					blocks = prev_bottom <= float(ty * TS) + EPS
				if blocks:
					r.position.y = float(ty * TS) - r.size.y
					res.on_floor = true
					res.floor_tile = Vector2i(tx, ty)
					remaining = 0.0
					break
		else:
			var ty := int(floor(r.position.y / TS))
			for tx in range(cols.x, cols.y + 1):
				if _solid_for(world, tx, ty):
					r.position.y = float((ty + 1) * TS)
					res.hit_ceiling = true
					res.ceiling_tile = Vector2i(tx, ty)
					remaining = 0.0
					break
		res.rect = r
	return res


## True when a solid (or catchable one-way) tile sits directly under the rect.
static func is_on_floor(world: TileWorld, rect: Rect2, drop_through: bool = false) -> bool:
	var ty := int(floor((rect.position.y + rect.size.y + 1.0) / TS))
	var cols := tile_range(rect.position.x, rect.position.x + rect.size.x)
	var bottom := rect.position.y + rect.size.y
	for tx in range(cols.x, cols.y + 1):
		if _solid_for(world, tx, ty):
			return true
		if not drop_through and world.is_oneway(tx, ty) and absf(bottom - float(ty * TS)) < 2.0:
			return true
	return false


## OR of the flags of every tile the rect overlaps.
static func sample_flags(world: TileWorld, rect: Rect2) -> int:
	var cols := tile_range(rect.position.x, rect.position.x + rect.size.x)
	var rows := tile_range(rect.position.y, rect.position.y + rect.size.y)
	var f := 0
	for ty in range(rows.x, rows.y + 1):
		for tx in range(cols.x, cols.y + 1):
			f |= world.flags_at(tx, ty)
	return f


static func has_flag(world: TileWorld, rect: Rect2, flag: int) -> bool:
	return sample_flags(world, rect) & flag != 0


## Every tile coordinate the rect overlaps that carries `flag`.
static func tiles_with_flag(world: TileWorld, rect: Rect2, flag: int) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	var cols := tile_range(rect.position.x, rect.position.x + rect.size.x)
	var rows := tile_range(rect.position.y, rect.position.y + rect.size.y)
	for ty in range(rows.x, rows.y + 1):
		for tx in range(cols.x, cols.y + 1):
			if world.flags_at(tx, ty) & flag:
				out.append(Vector2i(tx, ty))
	return out


## Convenience: solid test used by AI ledge checks.
static func solid_at_pixel(world: TileWorld, px: float, py: float) -> bool:
	return world.is_solid(int(floor(px / TS)), int(floor(py / TS)))
