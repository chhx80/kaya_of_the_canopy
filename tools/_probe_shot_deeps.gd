extends SceneTree
## THROWAWAY. Render proof for tests/fixtures/deeps_probe.json, and the measured
## demo of the World 4 darkness recipe. The World 3 twin is
## tools/_probe_shot_heights.gd; this one adds the three AmbienceLayers and a
## body for the lantern to follow.
##
## tools/shot.sh can only reach a scenario, and `level:<id>` resolves through
## LevelLoader.load_level() -> res://levels/<id>.json. A probe deliberately does
## not live in levels/, so there is no scenario that can show it.
##
##   $GODOT --path . --rendering-driver opengl3 --resolution 400x240 \
##       --script res://tools/_probe_shot_deeps.gd -- --mode=lit
##
## --mode=lit     the probe under the shipping renderers, no ambience
## --mode=dark    the DARK_RECIPE from tests/test_tileset_probes.gd applied, with
##                Kaya standing in it carrying her light
## --mode=shut    the shoulder plug in the last column, untouched
## --mode=open    the same, after FormBase.tick_break() has dug the bottom tile
##
## Everything is reached through load() inside _initialize(): a static reference
## makes Godot compile the whole dependency graph while this file is loading,
## which is before the autoload names exist, and ambience_layer.gd mentions
## `Game`. Delete after capturing; it is not part of the toolchain.

const FIXTURE := "res://tests/fixtures/deeps_probe.json"
const DT := 1.0 / 60.0
const TS := 16.0

## Kept in step with DARK_RECIPE in tests/test_tileset_probes.gd, which asserts it
## loads. Emissive keys must be FOREGROUND tile ids: _collect_emissive() scans
## get_fg() only.
const DARK := {
	"world": "deeps",
	"air": {"ramp": "water", "step": 1, "alpha": 0.30},
	"bg_tint": {"ramp": "water", "step": 3, "mix": 0.85, "scale": 0.46},
	"fg_tint": {"ramp": "metal", "step": 6, "mix": 0.30, "scale": 0.82},
	"vignette": 0.40,
	"darkness": 0.88,
	"emissive": {
		"214": {"ramp": "gold", "step": 6, "intensity": 0.40, "radius": 30, "lift": 0},
		"267": {"ramp": "grass", "step": 5, "intensity": 0.30, "radius": 26, "lift": 5},
	},
}

class Shooter extends Node:
	var out := ""
	func _ready() -> void:
		for _i in 4:
			await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var err := img.save_png(out)
		print("[capture] %s (%dx%d) err=%d" % [out, img.get_width(), img.get_height(), err])
		get_tree().quit(0 if err == OK else 1)

## AmbienceLayer._lantern_pos() reads `player` off its parent, which in the game
## is the Level. This is the smallest thing that satisfies that contract.
class Holder extends Node2D:
	var player: Node = null

func _initialize() -> void:
	var mode := "lit"
	var out := ""
	# A magnifier, so a one-tile outcome is legible at 400x240. Pure Node2D
	# transform with the project's nearest filtering, so the pixels stay pixels.
	var zoom := 1.0
	var at := Vector2.ZERO
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--mode="):
			mode = a.substr(7)
		elif a.begins_with("--out="):
			out = a.substr(6)
		elif a.begins_with("--zoom="):
			zoom = a.substr(7).to_float()
		elif a.begins_with("--at="):
			var parts := a.substr(5).split(",")
			if parts.size() == 2:
				at = Vector2(parts[0].to_float(), parts[1].to_float())
	if out == "":
		out = {"lit": "shots/world_deeps_probe.png",
			"dark": "shots/m4_verbs_darkness.png",
			"shut": "shots/_m4_break_shut.png",
			"open": "shots/_m4_break_open.png"}.get(mode, "shots/world_deeps_probe.png")

	var LL: GDScript = load("res://src/world/level_loader.gd")
	var def: Object = LL.load_path(FIXTURE, "deeps_probe")
	if not def.ok():
		printerr("probe failed to load: %s" % ", ".join(def.errors))
		quit(1)
		return
	var world: Object = def.world
	var view := Rect2(0, 0, 400, 240)

	if mode == "open":
		_dig(world)

	var holder: Node2D = Holder.new()
	holder.scale = Vector2(zoom, zoom)
	holder.position = -at * zoom
	root.add_child(holder)

	var PB: GDScript = load("res://src/world/parallax_bg.gd")
	for plane: Array in [["sky", 0.10], ["far", 0.28], ["near", 0.58]]:
		var path := "res://assets/sprites/bg_deeps_%s.png" % String(plane[0])
		if not ResourceLoader.exists(path):
			printerr("no backdrop at %s" % path)
			continue
		var p: Node = PB.new()
		holder.add_child(p)
		p.setup(path, float(plane[1]), 0.0)
		p.set_view(view)

	var dark := mode == "dark"
	var AM: GDScript = load("res://src/world/ambience.gd")
	var AL: GDScript = load("res://src/world/ambience_layer.gd")
	var amb: Object = AM.from_dict("deeps_probe", DARK) if dark else null

	if dark:
		_layer(holder, AL, 0, amb, world, view)          # AIR, behind the tiles

	var TR: GDScript = load("res://src/world/tile_renderer.gd")
	for layer: String in ["bg", "fg"]:
		var r: Node = TR.new()
		holder.add_child(r)
		r.setup(world, layer)
		r.set_view(view)
		if dark:
			r.modulate_color = amb.bg_tint if layer == "bg" else amb.fg_tint

	if dark:
		# Kaya first, so the layers above her are the ones that must not dim her:
		# SHADE and LIGHT are added after, but entities are drawn after those in
		# the real Level, so she is re-parented to the end below.
		var body: Object = _body(world)
		holder.player = body
		_layer(holder, AL, 1, amb, world, view)          # SHADE: darkness + vignette
		_layer(holder, AL, 2, amb, world, view)          # LIGHT: pools, additive
		holder.add_child(_kaya(body))                    # drawn last, full contrast

	var s := Shooter.new()
	s.out = out
	root.add_child(s)

## One AmbienceLayer. `set_process(false)` because _process() reads the `Game`
## autoload, which does not exist under --script; nothing here animates anyway.
func _layer(parent: Node2D, AL: GDScript, role: int, amb: Object, world: Object,
		view: Rect2) -> Node:
	var l: Node = AL.new()
	parent.add_child(l)
	l.set_process(false)
	l.view = view
	l.setup(role, amb, world)
	print("  ambience role %d: %d pool(s) in view, lantern radius %.0f"
		% [role, l.visible_pools(), amb.lantern_radius])
	return l

## An Actor standing on the probe's floor at the spawn mark, for the lantern to
## follow. Not a Player: Player._physics_process() reads the `Game` autoload.
func _body(world: Object) -> Object:
	var AC: GDScript = load("res://src/world/actor.gd")
	var FB: GDScript = load("res://src/player/forms/form_base.gd")
	var f: Object = FB.load_form("human")
	var hb: Dictionary = f.hitbox()
	var a: Object = AC.new()
	a.world = world
	a.box = Vector2(float(hb.get("w", 10)), float(hb.get("h", 22)))
	# level.gd: player.pos = Vector2(p.x + 3.0, p.y + 16.0 - player.box.y)
	a.pos = Vector2(2.0 * TS + 3.0, 12.0 * TS + 16.0 - a.box.y)
	a.facing = 1
	return a

## The sprite Player would draw on its idle frame, at the same offset.
func _kaya(body: Object) -> Node2D:
	var FB: GDScript = load("res://src/player/forms/form_base.gd")
	var f: Object = FB.load_form("human")
	var hb: Dictionary = f.hitbox()
	var fs: Vector2i = f.frame_size()
	var n := Node2D.new()
	n.position = (body.pos as Vector2).round()
	var sp := Sprite2D.new()
	sp.centered = false
	sp.region_enabled = true
	sp.texture = load(f.sprite_path())
	sp.region_rect = Rect2(0, 0, fs.x, fs.y)
	sp.offset = Vector2(-float(hb.get("ox", 3)), -float(hb.get("oy", 2)))
	n.add_child(sp)
	return n

## Drive the shipping break verb on the probe's own plug, exactly as
## tests/test_tileset_probes.gd does, so the "open" panel is an outcome and not a
## set_fg().
func _dig(world: Object) -> void:
	var AC: GDScript = load("res://src/world/actor.gd")
	var FB: GDScript = load("res://src/player/forms/form_base.gd")
	var IS: GDScript = load("res://src/core/input_state.gd")
	var f: Object = FB.load_form("frog")
	var hb: Dictionary = f.hitbox()
	var a: Object = AC.new()
	a.world = world
	a.box = Vector2(float(hb.get("w", 12)), float(hb.get("h", 11)))
	a.pos = Vector2(24.0 * TS - a.box.x, 13.0 * TS - a.box.y)
	a.facing = 1
	var input: Object = IS.new()
	input.right = true
	input.attack = true
	for i in 60:
		f.update(a, input, DT)
		a.step_motion(DT)
		input.attack_pressed = false
		if not world.is_solid(24, 12):
			print("  dug (24,12) in %d ticks" % (i + 1))
			return
	print("  (24,12) never opened")
