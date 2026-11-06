class_name ParallaxBg
extends Node2D
## Tiling parallax layer, scrolled continuously by the follow camera.
##
## Three properties of this are load-bearing and none is obvious:
##
## * **Scrolling moves the node; it does not redraw it.** `set_view()` runs on
##   every camera move, so it only sets `position`. The draw list (one copy of
##   the strip per column the view touches, usually two) is re-recorded only
##   when that count changes, which on a level it never does after the first
##   frame.
## * **The offset is a whole-pixel function of the whole-pixel view.** The
##   camera hands over an integer view (CameraController.view_rect), and the
##   plane's screen offset is `round(view.x * (1 - factor))`. Rounding the
##   plane and the camera separately instead makes a slow plane step on an
##   irregular beat against the tiles — the "swim" a scrolling backdrop is
##   known for.
## * **Vertically the strip is locked to the view** when it is no taller than
##   the view, which every backdrop is (400x240, tests/test_art_depth.gd). A
##   240px strip has no slack: any vertical offset at all exposes its top or
##   bottom edge mid-screen. Locked, every view shows the whole strip exactly as
##   every screen did under the flip. A taller strip would get its slack mapped
##   across the level's height, so the edge can never show.
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

## `_vf` is kept for the callers' signature; vertical motion is the lock rule
## above, not a factor.
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
	var sx := -fposmod(roundf(view.position.x * (1.0 - factor)), ts.x)
	position = Vector2(view.position.x + sx, view.position.y - _slack_offset(ts.y))
	var cols := int(ceil((view.size.x - sx) / ts.x))
	if cols != _cols:
		_cols = cols
		queue_redraw()

## How far down the strip's own height the view is looking, for a strip taller
## than the view. Zero for every backdrop the game ships.
func _slack_offset(tex_h: float) -> float:
	var slack := tex_h - view.size.y
	if slack <= 0.0 or level_h <= view.size.y:
		return 0.0
	var t := clampf(view.position.y / (level_h - view.size.y), 0.0, 1.0)
	return roundf(slack * t)

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
