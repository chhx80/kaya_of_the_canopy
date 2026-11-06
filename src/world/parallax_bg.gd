class_name ParallaxBg
extends Node2D
## Tiling parallax layer, scrolled continuously by the follow camera.
##
## Four properties of this are load-bearing and none is obvious:
##
## * **`factor` is how fast the plane moves on screen, as a fraction of the
##   tiles.** 0 is glued to the camera (infinitely far), 1 is glued to the
##   world. The sky is 0.10, the near-foreground 0.82. Until Kaya Refit phase 3
##   the offset was computed from `1 - factor`, which ran every plane backwards
##   — the sky scrolled at 90% of the tiles and the foreground grass at 18% —
##   and the screen flip hid it. tests/test_parallax_bg.gd pins the direction.
## * **Scrolling moves the node; it does not redraw it.** `set_view()` runs on
##   every camera move, so it only sets `position`. The draw list (one copy of
##   the strip per column the view touches, usually two) is re-recorded only
##   when that count changes, which on a level it never does after the first
##   frame.
## * **The offset is a whole-pixel function of the whole-pixel view.** The
##   camera hands over an integer view (CameraController.view_rect), and the
##   plane's screen offset is `round(view.x * factor)`. Rounding the plane and
##   the camera separately instead makes a slow plane step on an irregular
##   beat against the tiles — the "swim" a scrolling backdrop is known for.
## * **Vertically the strip's slack is mapped across the level's height.** A
##   strip is painted taller than the view (data/parallax.json sizes it), and
##   the top of the level shows its top rows, the bottom of the level its
##   bottom rows, so its edge can never show. On the two-screen-tall level the
##   strips are sized for, that is the plane's own factor vertically too. A
##   level with no vertical travel (one screen tall) shows the bottom rows,
##   where each world's horizon and ground are painted. A strip no taller than
##   the view has no slack and is locked to it.
##
## `view` is the camera's *unshaken* rect, so a screen shake cannot make the
## backdrop re-tile under itself.

var texture: Texture2D = null
var factor := 0.25          ## 0 = glued to the camera, 1 = glued to the world
var tint := Color.WHITE
var view := Rect2(0, 0, 400, 240)
## The level's pixel height, for a strip taller than the view. 0 = unknown.
var level_h := 0.0
var _cols := -1

## `_vf` is kept for the callers' signature; vertical motion comes from the
## strip's height (the slack rule above), not from a factor.
func setup(tex_path: String, f: float, _vf: float = 0.0) -> void:
	texture = load(tex_path)
	factor = f
	_cols = -1
	set_view(view)

func set_view(r: Rect2) -> void:
	view = r
	if texture == null:
		return
	var ts := texture.get_size()
	var sx := -fposmod(roundf(view.position.x * factor), ts.x)
	position = Vector2(view.position.x + sx, view.position.y - _slack_offset(ts.y))
	var cols := int(ceil((view.size.x - sx) / ts.x))
	if cols != _cols:
		_cols = cols
		queue_redraw()

## How far down the strip's own height the view is looking: 0 at the top of
## the level, all of the slack at the bottom.
func _slack_offset(tex_h: float) -> float:
	var slack := tex_h - view.size.y
	if slack <= 0.0:
		return 0.0
	if level_h <= view.size.y:
		return slack
	var t := clampf(view.position.y / (level_h - view.size.y), 0.0, 1.0)
	return roundf(slack * t)

## The strip's top-left on screen, relative to the view. For the tests and the
## integration suite: this is the whole of what the plane does.
func screen_offset() -> Vector2:
	return position - view.position

## How many copies of the strip are drawn. For the integration suite, which
## cannot see a draw call but can see the work behind one.
func copies() -> int:
	return maxi(0, _cols)

func _draw() -> void:
	if texture == null:
		return
	var w := texture.get_size().x
	for c in _cols:
		draw_texture(texture, Vector2(float(c) * w, 0.0), tint)
