class_name PixelFont
extends RefCounted
## Draws text from assets/fonts/font8.png (8x8 cells, 16 per row, first glyph is
## space/32). Rolling our own beats importing a .fnt: exact pixel placement,
## per-call tinting, and no importer surprises in CI.

const CELL := 8
const COLS := 16
const FIRST := 32
const TEX_PATH := "res://assets/fonts/font8.png"

static var _tex: Texture2D = null

static func texture() -> Texture2D:
	if _tex == null and ResourceLoader.exists(TEX_PATH):
		_tex = load(TEX_PATH)
	return _tex

## Static caches outlive the scene tree, which Godot reports as a leaked object
## at exit. Main drops them on the way out.
static func release() -> void:
	_tex = null

static func width(text: String, scale: int = 1, tracking: int = 0) -> int:
	return text.length() * (CELL + tracking) * scale

static func height(scale: int = 1) -> int:
	return CELL * scale

## Draws `text` with its top-left at `pos`. Returns the advance width.
static func draw(ci: CanvasItem, pos: Vector2, text: String, color: Color = Color.WHITE,
		scale: int = 1, tracking: int = 0) -> int:
	var tex := texture()
	if tex == null:
		return 0
	var up := text.to_upper()
	var x := pos.x
	var adv := (CELL + tracking) * scale
	for i in up.length():
		var code := up.unicode_at(i)
		var idx := code - FIRST
		if idx >= 0 and idx < COLS * 4 and code != 32:
			var src := Rect2(
				float((idx % COLS) * CELL), float((idx / COLS) * CELL),
				float(CELL), float(CELL))
			ci.draw_texture_rect_region(tex,
				Rect2(Vector2(x, pos.y), Vector2(CELL * scale, CELL * scale)), src, color)
		x += adv
	return int(x - pos.x)

## Same, but with a 1px (scaled) drop shadow — the retro default.
static func draw_shadowed(ci: CanvasItem, pos: Vector2, text: String,
		color: Color = Color.WHITE, shadow: Color = Color(0, 0, 0, 0.75),
		scale: int = 1, tracking: int = 0) -> int:
	draw(ci, pos + Vector2(scale, scale), text, shadow, scale, tracking)
	return draw(ci, pos, text, color, scale, tracking)

static func draw_centered(ci: CanvasItem, center_x: float, y: float, text: String,
		color: Color = Color.WHITE, scale: int = 1, tracking: int = 0,
		shadowed: bool = true) -> void:
	var w := width(text, scale, tracking)
	var pos := Vector2(round(center_x - w * 0.5), y)
	if shadowed:
		draw_shadowed(ci, pos, text, color, Color(0, 0, 0, 0.75), scale, tracking)
	else:
		draw(ci, pos, text, color, scale, tracking)
