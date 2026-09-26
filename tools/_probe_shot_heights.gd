extends SceneTree
## THROWAWAY. Render proof for tests/fixtures/heights_probe.json.
##
## tools/shot.sh can only reach a scenario, and `level:<id>` resolves through
## LevelLoader.load_level() -> res://levels/<id>.json. A probe deliberately does
## not live in levels/, so there is no scenario that can show it. This builds the
## two shipping TileRenderers plus the three heights parallax planes over the
## probe's own TileWorld and saves the viewport.
##
##   $GODOT --path . --rendering-driver opengl3 --resolution 400x240 \
##       --script res://tools/_probe_shot_heights.gd
##
## Delete after capturing; it is not part of the toolchain.

const FIXTURE := "res://tests/fixtures/heights_probe.json"
const OUT := "shots/world_heights_probe.png"

class Shooter extends Node:
	var out := ""
	func _ready() -> void:
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var err := img.save_png(out)
		print("[capture] %s (%dx%d) err=%d" % [out, img.get_width(), img.get_height(), err])
		get_tree().quit(0 if err == OK else 1)

func _initialize() -> void:
	var def := LevelLoader.load_path(FIXTURE, "heights_probe")
	if not def.ok():
		printerr("probe failed to load: %s" % ", ".join(def.errors))
		quit(1)
		return
	var view := Rect2(0, 0, 400, 240)
	for plane: Array in [["sky", 0.10], ["far", 0.28], ["near", 0.58]]:
		var path := "res://assets/sprites/bg_heights_%s.png" % String(plane[0])
		if not ResourceLoader.exists(path):
			printerr("no backdrop at %s" % path)
			continue
		var p := ParallaxBg.new()
		p.setup(path, float(plane[1]), 0.0)
		p.set_view(view)
		root.add_child(p)
	for layer: String in ["bg", "fg"]:
		var r := TileRenderer.new()
		root.add_child(r)
		r.setup(def.world, layer)
		r.set_view(view)
	var s := Shooter.new()
	s.out = OUT
	root.add_child(s)
