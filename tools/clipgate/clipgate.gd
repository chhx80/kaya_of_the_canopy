extends Node
## The clip gate (Kaya Refit, phase 1). Replays every proof tape in proofs/
## through the prover's own simulation and asserts that, on every frame, the
## pixels Kaya's sprite actually DRAWS never land on a solid tile.
##
## Why it exists: the 40 px Kaya is 18 px taller than the 10x22 hitbox she
## collides with, and 17.8% of standable tiles have exactly two tiles of
## headroom. Collision is not changing, so nothing in movement, the prover or the
## replay tier can see her hat go into the rock. The fix (KayaPose: draw the
## stoop) is render-only, so the proof has to be about the render.
##
## What "drawn" means here, precisely, because a gate that checks a guessed
## rectangle is the mechanism-not-outcome mistake this project keeps making:
##
##   * the physics is ProverSim -- the real Actor, the real form, the real
##     TileCollision, plus the prover's door/switch/pad/key mirror -- fed the
##     tape's buttons exactly as the prover's self-check feeds them;
##   * the render is a real Player node, never stepped, whose state is copied
##     from the sim every tick and then put through Player's OWN render path
##     (_note_motion_events, _update_anim, _sync_render_position), so the frame,
##     the flip, the offset, the squash/stretch scale and the pose decision are
##     whatever the game would have set on the Sprite2D;
##   * the footprint is read back off that Sprite2D and inverted pixel by pixel
##     -- each world pixel's centre is mapped back into the frame and the
##     sheet's real alpha is looked up -- so a transparent corner of the cell is
##     never counted and a hat brim always is.
##
## It fails loudly: level, tape frame, hop, animation, sheet frame, tile.
##
##   tools/clipgate.sh                 every tape
##   tools/clipgate.sh jungle_1 deeps_2
##   tools/clipgate.sh --no-stoop      the same, with only the stoop switched
##                                     off -- a run that has to FAIL
##   tools/clipgate.sh --no-pose       with every KayaPose decision off -- also
##                                     has to FAIL
##   tools/clipgate.sh --all-forms     also gate the frog, fish and bird
##   tools/clipgate.sh --show=N        list N clips per level (default 6)

const ProveScript := preload("res://tools/solver/prove.gd")
const DT := 1.0 / 60.0
const GATED_FORMS := ["human"]

var _ids: Array[String] = []
var _all_forms := false
var _show := 6

var _alpha: Dictionary = {}          ## sprite path -> Image
var _kinds: Dictionary = {}          ## "side/anim" -> clipping frames, all tapes
var _diagnose := false
var _trace := -1
var _diag: Dictionary = {}
var _diag_shift: Dictionary = {}


func _ready() -> void:
	AudioManager.enabled = false
	for a: String in OS.get_cmdline_user_args():
		if a == "--no-pose":
			KayaPose.enabled = false
		elif a == "--no-stoop":
			KayaPose.stoop_enabled = false
		elif a.begins_with("--trace="):
			_trace = int(a.split("=")[1])
		elif a == "--diagnose":
			_diagnose = true
		elif a == "--all-forms":
			_all_forms = true
		elif a.begins_with("--show="):
			_show = int(a.split("=")[1])
		elif not a.begins_with("--"):
			_ids.append(a)
	get_tree().quit(_run())


func _run() -> int:
	var tapes := _tapes()
	if tapes.is_empty():
		print("clipgate: no tapes found in res://proofs -- nothing proved is not a pass")
		return 1
	print("clipgate: %d tape(s), pose decision %s, gating %s" % [tapes.size(),
		("ON" if KayaPose.stoop_enabled else "ON but the stoop OFF (--no-stoop)")
			if KayaPose.enabled else "OFF (--no-pose)",
		"every form" if _all_forms else "the human form"])
	var failed: Array[String] = []
	var frames_total := 0
	var body_total := 0
	var anim_total: Dictionary = {}
	for tape_path: String in tapes:
		var r := _replay(tape_path)
		frames_total += int(r["frames"])
		body_total += int(r.get("body", 0))
		for k: String in (r["anims"] as Dictionary).keys():
			anim_total[k] = int(anim_total.get(k, 0)) + int(r["anims"][k])
		if String(r["verdict"]) != "PASS":
			failed.append(String(r["level"]))
	print("")
	var keys: Array = anim_total.keys()
	keys.sort()
	var parts: Array[String] = []
	for k: String in keys:
		parts.append("%s %d" % [k, anim_total[k]])
	print("drawn: %s" % ", ".join(parts))
	print("hitbox itself in rock (collision's, not counted): %d frames" % body_total)
	if not _kinds.is_empty():
		var kk: Array = _kinds.keys()
		kk.sort()
		var kp: Array[String] = []
		for k: String in kk:
			kp.append("%s %d" % [k, _kinds[k]])
		print("clipping frames by side/anim: %s" % ", ".join(kp))
	if _diagnose:
		print("diagnose: %s" % str(_diag))
		print("diagnose shifts: %s" % str(_diag_shift))
	if failed.is_empty():
		print("clipgate: PASS -- %d tapes, %d frames, no drawn pixel on a solid tile"
			% [tapes.size(), frames_total])
		return 0
	print("clipgate: FAIL -- %d of %d tapes clip: %s"
		% [failed.size(), tapes.size(), ", ".join(failed)])
	return 1


func _tapes() -> Array[String]:
	var out: Array[String] = []
	if not _ids.is_empty():
		for id: String in _ids:
			out.append("res://proofs/%s.tape.json" % id)
		return out
	var d := DirAccess.open("res://proofs")
	if d == null:
		return out
	for f: String in d.get_files():
		if f.ends_with(".tape.json"):
			out.append("res://proofs/" + f)
	out.sort()
	return out


func _replay(tape_path: String) -> Dictionary:
	var tape := ProverTape.read(tape_path)
	var id := String(tape.get("level", tape_path.get_file().replace(".tape.json", "")))
	var res := {"level": id, "verdict": "FAIL", "frames": 0, "anims": {}}
	var level_path := LevelLoader.level_path(id)
	var stale := ProverTape.staleness(tape_path, level_path)
	if stale != "":
		print("FAIL  %-12s stale tape: %s" % [id, stale])
		return res
	var def := LevelLoader.load_path(level_path, id)
	if not def.ok():
		print("FAIL  %-12s level does not load: %s" % [id, str(def.errors)])
		return res
	var acts := ProverTape.frames(tape_path, level_path)
	if acts.is_empty():
		print("FAIL  %-12s tape has no frames" % id)
		return res

	# Where each hop starts, for naming a clip in the author's terms.
	var hop_names: Array[String] = []
	var hop_start: PackedInt32Array = PackedInt32Array()
	var n := 0
	for hop: Dictionary in (tape.get("hops", []) as Array):
		hop_start.append(n)
		hop_names.append("%s>%s" % [hop.get("from", "?"), hop.get("to", "?")])
		for run: Dictionary in (hop.get("frames", []) as Array):
			n += int(run.get("n", 0))

	var sim := ProverSim.new()
	sim.setup(def)
	var neutral := InputState.new()
	for _i in ProveScript.SETTLE_FRAMES:
		sim.step(neutral)

	var shadow := Player.new()
	shadow.world = sim.world
	shadow._ready()
	var inp := InputState.new()
	shadow.input = inp
	_mirror(shadow, sim)

	var clips: Array[String] = []
	var clip_frames := 0
	var body_frames := 0
	var gated := 0
	var anims: Dictionary = {}
	var prev := 0
	for f in acts.size():
		var bits := acts[f]
		ProverTape.apply(inp, bits, prev)
		prev = bits
		var fall_speed := sim.actor.vel.y
		sim.step(inp)
		_mirror(shadow, sim)
		shadow._note_motion_events(fall_speed)
		shadow._update_anim(DT)
		shadow._sync_render_position()

		if f == _trace:
			_print_trace(shadow, sim)
		if not (_all_forms or GATED_FORMS.has(sim.form_id)):
			continue
		gated += 1
		anims[shadow._anim] = int(anims.get(shadow._anim, 0)) + 1
		var body := _hitbox_in_rock(shadow, sim)
		if body:
			body_frames += 1
			continue
		var hit := _clip(shadow, sim)
		if hit.is_empty():
			continue
		if _diagnose:
			var fix := "none"
			for d in [1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8, -8, 10, -10, 12, -12]:
				if _clip(shadow, sim, Vector2(d, 0)).is_empty():
					fix = "x%+d" % d
					break
			if fix == "none":
				for d in [1, 2, 3, 4, 5, 6, 8, 10]:
					if _clip(shadow, sim, Vector2(0, d)).is_empty():
						fix = "y+%d" % d
						break
			var dk := "%s/%s %s" % [hit.get("side", "?"), shadow._anim, fix.substr(0, 2) if fix != "none" else "none"]
			_diag[dk] = int(_diag.get(dk, 0)) + 1
			var hk := "%s" % fix
			_diag_shift[hk] = int(_diag_shift.get(hk, 0)) + 1
		clip_frames += 1
		var key := "%s/%s" % [hit.get("side", "?"), shadow._anim]
		_kinds[key] = int(_kinds.get(key, 0)) + 1
		if clips.size() < _show:
			var h := hop_start.bsearch(f, false) - 1
			clips.append("  frame %4d  hop %d %-24s %-6s anim %-10s sheet frame %2d%s  %s  (hitbox %v%s)"
				% [f, h + 1, hop_names[maxi(h, 0)], sim.form_id, shadow._anim,
				int(shadow.sprite.region_rect.position.x / shadow.sprite.region_rect.size.x),
				" flipped" if shadow.sprite.flip_h else "", hit["what"], sim.actor.pos,
				", itself in rock" if body else ""])
	res["frames"] = gated
	res["anims"] = anims
	res["body"] = body_frames
	if gated == 0:
		print("FAIL  %-12s no gated frames were drawn -- nothing checked is not a pass" % id)
		return res
	if clip_frames == 0:
		res["verdict"] = "PASS"
		print("PASS  %-12s %5d frames" % [id, gated])
		return res
	print("FAIL  %-12s %d of %d frames draw onto a solid tile:" % [id, clip_frames, gated])
	for c: String in clips:
		print(c)
	if clip_frames > clips.size():
		print("  ... and %d more frame(s)" % (clip_frames - clips.size()))
	return res


## Copy the simulated body into the render-only Player. The form instance is
## shared, not copied: `anim_for()` reads its live state (climbing, _land_t).
func _mirror(p: Player, sim: ProverSim) -> void:
	if p.form_id != sim.form_id:
		p.set_form(sim.form_id)
	p.form = sim.form
	var a := sim.actor
	p.pos = a.pos
	p.vel = a.vel
	p.box = a.box
	p.on_floor = a.on_floor
	p.was_on_floor = a.was_on_floor
	p.on_ceiling = a.on_ceiling
	p.against_wall = a.against_wall
	p.facing = a.facing
	p.drop_through = a.drop_through


## The drawn footprint against the solid tiles under it, or {} when clean.
func _clip(p: Player, sim: ProverSim, shift: Vector2 = Vector2.ZERO) -> Dictionary:
	var s := p.sprite
	if not s.visible:
		return {}
	var img := _sheet(p.form.sprite_path())
	if img == null:
		return {"what": "cannot read the sheet %s" % p.form.sprite_path()}
	var region := s.region_rect
	var fw := region.size.x
	var fh := region.size.y
	var org := p.position + s.position + shift
	var sc := s.scale
	var x0 := org.x + sc.x * s.offset.x
	var y0 := org.y + sc.y * s.offset.y
	var x1 := x0 + sc.x * fw
	var y1 := y0 + sc.y * fh
	var ts := TileData4.TILE_SIZE
	var world := sim.world
	# The body's own pixels: where collision put her. A drawn pixel in here that
	# is also in rock is collision's doing (the drop-through nudge parks the
	# hitbox a pixel into a solid floor for a frame), it happens at any sprite
	# size, and it is counted by _hitbox_in_rock() instead -- this gate is about
	# what the bigger sprite draws OUTSIDE the box collision keeps clear.
	var hb := Rect2i(Vector2i(p.position), Vector2i(p.box))
	var worst := {}
	var worst_n := 0
	for ty in range(int(floor(y0 / ts)), int(floor((y1 - 0.001) / ts)) + 1):
		for tx in range(int(floor(x0 / ts)), int(floor((x1 - 0.001) / ts)) + 1):
			if not world.is_solid(tx, ty):
				continue
			var n := 0
			var first := Vector2i.ZERO
			for wy in range(maxi(ty * ts, int(floor(y0))), mini((ty + 1) * ts, int(ceil(y1)))):
				for wx in range(maxi(tx * ts, int(floor(x0))), mini((tx + 1) * ts, int(ceil(x1)))):
					var u := int(floor(((wx + 0.5) - org.x) / sc.x - s.offset.x))
					var v := int(floor(((wy + 0.5) - org.y) / sc.y - s.offset.y))
					if u < 0 or v < 0 or u >= int(fw) or v >= int(fh):
						continue
					if hb.has_point(Vector2i(wx, wy)):
						continue
					if s.flip_h:
						u = int(fw) - 1 - u
					if img.get_pixel(int(region.position.x) + u, int(region.position.y) + v).a <= 0.0:
						continue
					if n == 0:
						first = Vector2i(wx, wy)
					n += 1
			if n > worst_n:
				worst_n = n
				worst = {"side": _side(p, tx, ty),
					"what": "%d px on tile (%d,%d) id %d [%s], first at world (%d,%d)"
					% [n, tx, ty, world.get_fg(tx, ty), _side(p, tx, ty), first.x, first.y]}
	return worst


## True when the hitbox itself, as rendered, overlaps a solid tile.
func _hitbox_in_rock(p: Player, sim: ProverSim) -> bool:
	var r := Rect2(p.position, p.box)
	var cols := TileCollision.tile_range(r.position.x, r.end.x)
	var rows := TileCollision.tile_range(r.position.y, r.end.y)
	for ty in range(rows.x, rows.y + 1):
		for tx in range(cols.x, cols.y + 1):
			if sim.world.is_solid(tx, ty):
				return true
	return false


## Where the tile is relative to the hitbox, which is what tells a reader whether
## this is a ceiling (the stoop's job), a wall or a floor.
func _side(p: Player, tx: int, ty: int) -> String:
	var ts := float(TileData4.TILE_SIZE)
	if (ty + 1) * ts <= p.pos.y:
		return "ceiling"
	if ty * ts >= p.pos.y + p.box.y:
		return "floor"
	return "wall"


func _sheet(path: String) -> Image:
	if _alpha.has(path):
		return _alpha[path]
	var img := Image.load_from_file(ProjectSettings.globalize_path(path))
	_alpha[path] = img
	return img


## Everything the pose decision saw on one frame (--trace=N).
func _print_trace(p: Player, sim: ProverSim) -> void:
	var pose: Dictionary = p.form.cfg.get("pose", {})
	var flip := p.sprite.flip_h
	var wanted := p._resolve_anim_state()
	var fs := p.form.frame_size()
	var up := KayaPose.rise(p.form, p._anim, p.box)
	print("  trace: pos %v box %v on_floor %s flip %s wanted %s drawn %s" % [p.pos, p.box,
		p.on_floor, flip, wanted, p._anim])
	print("         headroom %.1f (reach %.1f)  sprite.position %v  offset %v  scale %v" % [
		KayaPose.headroom(sim.world, p.pos, p.box, up, float(pose.get("headroom_reach", 0.0))),
		float(pose.get("headroom_reach", 0.0)), p.sprite.position, p.sprite.offset, p.sprite.scale])
	for a: String in [wanted, p._anim]:
		print("         fits_x(%s) = %s" % [a, KayaPose.fits_x(KayaPose.anim_rows(p.form, a), flip,
			fs.x, float(p.form.hitbox().get("ox", 0)), sim.world, p.pos, p.box,
			float(pose.get("max_nudge_x", 0.0)))])
	var frame := int(p.sprite.region_rect.position.x / p.sprite.region_rect.size.x)
	var rows := KayaPose.bounds(String(pose.get("bounds", "")))
	var org := p.pos.round() + Vector2(0.0, p.sprite.position.y) + p.sprite.offset * p.sprite.scale
	print("         wall_overlap(frame %d) = %v" % [frame, KayaPose.wall_overlap(rows[frame], flip,
		fs.x, org, p.sprite.scale, sim.world, Rect2(p.pos.round(), p.box))])
	var ts := TileData4.TILE_SIZE
	var tx0 := int(floor(p.pos.x / ts)) - 3
	var ty0 := int(floor((p.pos.y - 20) / ts))
	for ty in range(ty0, ty0 + 4):
		var line := "         row %3d " % ty
		for tx in range(tx0, tx0 + 7):
			line += "#" if sim.world.is_solid(tx, ty) else "."
		print(line + "   (cols %d..%d)" % [tx0, tx0 + 6])
