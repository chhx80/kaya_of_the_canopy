class_name Display
extends RefCounted
## The HD pass (docs/plan-hd.md): how world units become texels, and how much
## world the player sees. `data/display.json` is read here and nowhere else.
##
## * **World units never change.** A tile is 16 units, hitboxes and speeds are
##   what they were. Only the renderer knows texels exist.
## * **`art_scale` texels per world unit.** World-space art is generated at that
##   density (tools/art/palette.py) and loaded through `texture()`, which wraps
##   it in an HdTexture: every region, offset and size the game code hands it is
##   in world units, and the wrapper multiplies on the way to the GPU.
## * **The view** is the world the camera shows while exploring
##   (`view_w` x `view_h`). Screen.W x Screen.H is a different thing — the boss
##   arena cell and the grid levels were authored on — and a boss arena pulls
##   the view back out to it (CameraController).
##
## Static and pure, like Screen, so the headless `--script` tier can reach it.

const JSON_PATH := "res://data/display.json"

static var _loaded := false
static var _scale := 2
static var _view := Vector2(308, 184)
## path -> HdTexture. One wrapper per sheet, shared by every sprite that draws it.
static var _textures: Dictionary = {}

static func _ensure() -> void:
	if _loaded:
		return
	_loaded = true
	var f := FileAccess.open(JSON_PATH, FileAccess.READ)
	if f == null:
		push_error("Display: no %s" % JSON_PATH)
		return
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("Display: %s is not an object" % JSON_PATH)
		return
	var d: Dictionary = parsed
	_scale = maxi(1, int(d.get("art_scale", 2)))
	_view = Vector2(float(d.get("view_w", 308)), float(d.get("view_h", 184)))

## Texels per world unit.
static func art_scale() -> int:
	_ensure()
	return _scale

## World units visible while exploring.
static func view_size() -> Vector2:
	_ensure()
	return _view

## The largest view the camera ever asks for: a whole arena cell. The world's
## render target is sized for it once, so pulling back never reallocates.
static func max_view_size() -> Vector2:
	var v := view_size()
	return Vector2(maxf(v.x, float(Screen.W)), maxf(v.y, float(Screen.H)))

## The world SubViewport's size in texels.
static func render_texels() -> Vector2i:
	var t := max_view_size() * float(art_scale())
	return Vector2i(ceili(t.x), ceili(t.y))

## A world-space sheet, wrapped so it reads and draws in world units.
static func texture(path: String) -> Texture2D:
	if _textures.has(path):
		return _textures[path]
	var base: Texture2D = load(path)
	if base == null:
		return null
	var t := HdTexture.wrap(base, art_scale())
	_textures[path] = t
	return t

## A world-space sheet as an Image at one pixel per world unit: nearest
## decimation of the shipped texels. For code that measures art in world units
## (the art tests). Exact for a nearest-upscaled sheet; a sheet drawn natively
## at the HD density loses the detail it gained, which is the right answer to
## a question asked in world units.
static func world_image(path: String) -> Image:
	var tex: Texture2D = load(path)
	if tex == null:
		return null
	var img := tex.get_image()
	if img == null:
		return null
	# Headless, get_image() can hand back the cached image; shrink a copy.
	img = img.duplicate()
	if img.is_compressed():
		img.decompress()
	var k := art_scale()
	if k > 1 and img.get_width() % k == 0 and img.get_height() % k == 0:
		img.resize(img.get_width() / k, img.get_height() / k, Image.INTERPOLATE_NEAREST)
	return img

## Where a view of aspect `view` sits in a root viewport of `ui` logical
## pixels: as large as fits, centred. No whole-number stepping — the sharp
## filter in world_view.gdshader is what keeps the pixel edges clean at any
## scale. On a phone the height decides; on a 4:3 tablet the width does.
static func world_display_for(ui: Vector2, view: Vector2) -> Rect2:
	if view.x <= 0.0 or view.y <= 0.0:
		return Rect2(Vector2.ZERO, ui)
	var k := minf(ui.x / view.x, ui.y / view.y)
	var size := view * k
	return Rect2((ui - size) * 0.5, size)

## Static caches are not owned by the tree; Main drops them at exit.
static func release() -> void:
	_textures.clear()
