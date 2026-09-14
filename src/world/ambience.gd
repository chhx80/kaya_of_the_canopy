class_name Ambience
extends RefCounted
## Per-level air and light — phase 3 of docs/art-direction.md.
##
## `levels/*.json` is the authored *geometry* and nothing else; it is shared with
## the level editor and the validators and deliberately did not change for this
## phase. So the mood of a level lives here instead, keyed by level id, in
## `data/ambience.json`: which backdrop world it uses, how much air sits between
## the camera and the backdrop, how far the two tile layers are knocked back, and
## where the lights are.
##
## Every colour in that file is a **ramp step**, not an RGB literal, read back
## out of the generated `assets/palette.json`. That is the same discipline the
## art generators work under (tests/test_art_palette.gd), and it matters more
## here than it looks: an ambient tint is multiplied over every pixel of a level,
## so one hand-picked colour would drag the whole screen off the palette.
##
## Pure data — no nodes — so a headless test can load and check it.

const PATH := "res://data/ambience.json"
const PALETTE := "res://assets/palette.json"

## One light pool. Positions are already in pixels; the tile coordinates in the
## JSON are converted once, on load.
class Pool extends RefCounted:
	var pos := Vector2.ZERO
	## Half-extents of the quad. Round for an authored pool; stretched sideways
	## for a run of emissive tiles, so a lake gets a lozenge of light rather than
	## a circle as tall as it is wide.
	var half := Vector2(48, 48)
	var radius := 48.0
	var colour := Color.WHITE
	var flicker := 0.0
	var rate := 1.0

var id := ""
var world := "jungle"
## Haze drawn over the parallax planes and *behind* the tile layers, so it can
## push the backdrop away without touching anything the player stands on.
var air := Color(0, 0, 0, 0)
var bg_tint := Color.WHITE
var fg_tint := Color.WHITE
var vignette := 0.0
var pools: Array = []              ## Array[Pool], placed by hand
var emissive: Dictionary = {}      ## tile id -> {colour, radius, lift}

static var _ramps: Dictionary = {}
static var _table: Dictionary = {}

## Set only by the capture harness (`{"lighting": false}` in a seq, used by
## tools/seq/perf.json). Strips the haze, the vignette and every pool while
## leaving the backdrop planes and the tile tints alone, so the cost of *the
## lighting* can be measured against the same running process rather than
## against a different launch of the game on a differently warm machine.
static var lighting := true

# ---------------------------------------------------------------- loading
static func ramps() -> Dictionary:
	if _ramps.is_empty():
		var raw := FileAccess.get_file_as_string(PALETTE)
		var parsed: Variant = JSON.parse_string(raw)
		if parsed is Dictionary:
			_ramps = (parsed as Dictionary).get("ramps", {})
	return _ramps

## A ramp step as a Color. Out-of-range names and steps fall back to white
## rather than erroring: a bad tint should look wrong, not refuse to boot.
static func ramp_colour(ramp: String, idx: int) -> Color:
	var r: Array = ramps().get(ramp, [])
	if r.is_empty():
		return Color.WHITE
	var c: Array = r[clampi(idx, 0, r.size() - 1)]
	return Color(float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0)

## A ramp step read as a *tint* — a multiplier, not a colour. Three separate
## numbers, because they are three separate decisions and rolling them into one
## RGB triple is how tints end up unjustifiable:
##
##   ramp/step  the hue, normalised so its brightest channel is 1.0
##   mix        how much of that hue to take — 1.0 is the full ramp colour,
##              which on a saturated ramp is far more cast than a level wants
##   scale      how far the layer is knocked back
##
## `mix` is the one that was missing first time round: the grove came out
## magenta because a violet tint at full strength cuts a quarter of the green
## out of every brown tile in the level.
static func _tint(spec: Dictionary) -> Color:
	if spec.is_empty():
		return Color.WHITE
	var c := ramp_colour(String(spec.get("ramp", "metal")), int(spec.get("step", 6)))
	var peak := maxf(0.001, maxf(c.r, maxf(c.g, c.b)))
	var mix := clampf(float(spec.get("mix", 1.0)), 0.0, 1.0)
	var scale := float(spec.get("scale", 1.0))
	return Color(
		lerpf(1.0, c.r / peak, mix) * scale,
		lerpf(1.0, c.g / peak, mix) * scale,
		lerpf(1.0, c.b / peak, mix) * scale)

static func _colour(spec: Dictionary, default_alpha: float = 1.0) -> Color:
	if spec.is_empty():
		return Color(0, 0, 0, 0)
	var c := ramp_colour(String(spec.get("ramp", "metal")), int(spec.get("step", 6)))
	c.a = float(spec.get("alpha", default_alpha))
	return c

static func table() -> Dictionary:
	if _table.is_empty():
		var raw := FileAccess.get_file_as_string(PATH)
		var parsed: Variant = JSON.parse_string(raw)
		if parsed is Dictionary:
			_table = parsed as Dictionary
	return _table

## The ambience for a level. Unknown ids get the default entry, so a new level
## looks like the rest of the game before anyone has art-directed it.
static func for_level(level_id: String) -> Ambience:
	var t := table()
	var levels: Dictionary = t.get("levels", {})
	var d: Dictionary = t.get("default", {})
	var merged := d.duplicate(true)
	if levels.has(level_id):
		for k: String in (levels[level_id] as Dictionary).keys():
			merged[k] = (levels[level_id] as Dictionary)[k]
	var a := from_dict(level_id, merged)
	if not lighting:
		a.air.a = 0.0
		a.vignette = 0.0
		a.pools.clear()
		a.emissive.clear()
	return a

static func from_dict(level_id: String, d: Dictionary) -> Ambience:
	var a := Ambience.new()
	a.id = level_id
	a.world = String(d.get("world", "jungle"))
	a.air = _colour(d.get("air", {}), 0.0)
	a.bg_tint = _tint(d.get("bg_tint", {}))
	a.fg_tint = _tint(d.get("fg_tint", {}))
	a.vignette = clampf(float(d.get("vignette", 0.0)), 0.0, 1.0)
	var i := 0
	for raw: Variant in d.get("lights", []):
		var l: Dictionary = raw
		var p := Pool.new()
		p.pos = Vector2(float(l.get("x", 0)) + 0.5, float(l.get("y", 0)) + 0.5) \
			* float(TileData4.TILE_SIZE)
		p.radius = float(l.get("radius", 56.0))
		p.half = Vector2(p.radius, p.radius)
		p.colour = ramp_colour(String(l.get("ramp", "gold")), int(l.get("step", 5)))
		p.colour.a = float(l.get("intensity", 0.6))
		p.flicker = clampf(float(l.get("flicker", 0.0)), 0.0, 1.0)
		# Staggered rates: lights that breathe in step read as one big pulse.
		p.rate = float(l.get("rate", 0.7 + 0.13 * float(i % 5)))
		a.pools.append(p)
		i += 1
	var em: Dictionary = d.get("emissive", {})
	for key: String in em.keys():
		var e: Dictionary = em[key]
		var col := ramp_colour(String(e.get("ramp", "water")), int(e.get("step", 6)))
		col.a = float(e.get("intensity", 0.3))
		a.emissive[int(key)] = {
			"colour": col,
			"radius": float(e.get("radius", 26.0)),
			"lift": float(e.get("lift", 4.0)),
		}
	return a

func has_light() -> bool:
	return not pools.is_empty() or not emissive.is_empty()
