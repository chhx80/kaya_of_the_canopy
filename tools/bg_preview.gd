extends SceneTree
## Renders one world's parallax planes through the real ParallaxBg node and the
## real imported textures, at the four corners of a two-screen level, with
## Kaya standing in front for scale. For the worlds whose levels wall the
## backdrop in behind background tiles (ruins, heights, deeps, obsidian: no
## level shows their parallax), this is the only way to see it in the engine.
##
##   $GODOT --path . --rendering-driver opengl3 --resolution 400x240 \
##       --script res://tools/bg_preview.gd -- --world=ruins --out=shots/p3_bg_ruins_%d.png
##
## Not a game frame: there are no tiles, no ambience haze, no light pools.

const PLANES := {"sky": 0.10, "far": 0.28, "near": 0.58, "fg": 0.82}
const LEVEL := Vector2(800, 480)
const VIEWS: Array[Vector2] = [Vector2(0, 0), Vector2(400, 0), Vector2(0, 240), Vector2(400, 240)]

func _initialize() -> void:
	var world := "jungle"
	var out := "shots/bg_preview_%d.png"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--world="):
			world = a.trim_prefix("--world=")
		elif a.begins_with("--out="):
			out = a.trim_prefix("--out=")
	_run.call_deferred(world, out)

func _run(world: String, out: String) -> void:
	var holder := Node2D.new()
	root.add_child(holder)
	var planes: Array[ParallaxBg] = []
	for name: String in PLANES.keys():
		var path := "res://assets/sprites/bg_%s_%s.png" % [world, name]
		if not ResourceLoader.exists(path):
			continue
		var b := ParallaxBg.new()
		b.level_h = LEVEL.y
		holder.add_child(b)
		b.setup(path, float(PLANES[name]))
		planes.append(b)
	var kaya := Sprite2D.new()
	kaya.texture = load("res://assets/sprites/kaya_human.png")
	kaya.region_enabled = true
	kaya.region_rect = Rect2(0, 0, 32, 40)
	kaya.centered = false
	holder.add_child(kaya)
	for i in VIEWS.size():
		var v := VIEWS[i]
		holder.position = -v                       # the camera, by hand
		for b in planes:
			b.set_view(Rect2(v, Vector2(400, 240)))
		kaya.position = v + Vector2(184, 176)
		for _f in 3:
			await process_frame
		await RenderingServer.frame_post_draw
		var img := root.get_texture().get_image()
		img.save_png(out % i)
		print("[bg_preview] %s" % (out % i))
	quit()
