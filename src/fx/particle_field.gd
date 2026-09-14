class_name ParticleField
extends Node2D
## A fixed pool of screen-space particles, drawn in one pass from a single
## texture. Everything it can do is described by the "particles" block of
## data/fx.json — this file is only the mechanism.
##
## Deliberately not GPUParticles2D or CPUParticles2D: those want a node (and a
## material) per emitter, which on a 400x240 game with a phone as the target is
## more state than the effect is worth. One pool, one texture, one draw pass,
## no allocation after setup.

## Pool layout. Parallel packed arrays rather than objects, so a burst never
## allocates and the GC never has anything to collect mid-level.
const F_STRIDE := 6       ## x, y, vx, vy, age, life
const I_STRIDE := 2       ## alive, emitter index

var _tex: Texture2D = null
var _cell := 8.0
var _cols := 4
var _names: PackedStringArray = PackedStringArray()
var _emitters: Array[Dictionary] = []
var _by_name: Dictionary = {}
var _f: PackedFloat32Array = PackedFloat32Array()
var _i: PackedInt32Array = PackedInt32Array()
var _free: PackedInt32Array = PackedInt32Array()
var _live := 0
var _rng := RandomNumberGenerator.new()

## Returns false when the effect cannot run (no config, no art). The caller is
## expected to carry on regardless — particles are never load-bearing.
func setup(cfg: Dictionary) -> bool:
	_rng.randomize()
	var path := String(cfg.get("atlas", ""))
	if path == "" or not ResourceLoader.exists(path):
		push_warning("ParticleField: no particle atlas at '%s'; particles are off" % path)
		return false
	_tex = load(path)
	if _tex == null:
		return false
	_cell = float(cfg.get("cell", 8))
	_cols = maxi(1, int(cfg.get("atlas_columns", 4)))
	_compile(cfg.get("emitters", {}))
	_resize(maxi(1, int(cfg.get("pool", 96))))
	return not _emitters.is_empty()

func _compile(raw: Dictionary) -> void:
	for name: String in raw.keys():
		var src: Dictionary = raw[name]
		var frames: PackedInt32Array = PackedInt32Array()
		for v: Variant in src.get("frames", [0]):
			frames.append(maxi(0, int(v)))
		if frames.is_empty():
			frames.append(0)
		var count: Array = src.get("count", [1, 1])
		var life: Array = src.get("life", [0.3, 0.3])
		var speed: Array = src.get("speed", [0.0, 0.0])
		var ang: Array = src.get("angle_deg", [0.0, 0.0])
		_by_name[name] = _emitters.size()
		_names.append(name)
		_emitters.append({
			"row": maxi(0, int(src.get("row", 0))),
			"frames": frames,
			"fps": maxf(0.0, float(src.get("fps", 10.0))),
			"count_min": maxi(0, int(count[0])),
			"count_max": maxi(int(count[0]), int(count[-1])),
			"life_min": maxf(0.01, float(life[0])),
			"life_max": maxf(0.01, float(life[-1])),
			"speed_min": float(speed[0]),
			"speed_max": float(speed[-1]),
			"ang_min": deg_to_rad(float(ang[0])),
			"ang_max": deg_to_rad(float(ang[-1])),
			"aim": bool(src.get("aim", false)),
			"gravity": float(src.get("gravity", 0.0)),
			"drag": maxf(0.0, float(src.get("drag", 0.0))),
			"spread": maxf(0.0, float(src.get("spread_px", 0.0))),
			"fade": bool(src.get("fade", true)),
		})

func _resize(pool: int) -> void:
	_f.resize(pool * F_STRIDE)
	_i.resize(pool * I_STRIDE)
	_f.fill(0.0)
	_i.fill(0)
	_free.resize(pool)
	for n in pool:
		_free[n] = pool - 1 - n     # hand out low slots first, purely for tidiness
	_live = 0

# ---------------------------------------------------------------- emitting
## Throws a burst of `kind` at `at`. `dir` only matters for emitters that aim.
## Returns how many particles were actually spawned — the pool never grows, so
## a burst under load is quietly smaller rather than a frame-rate cliff.
func burst(kind: String, at: Vector2, dir: Vector2 = Vector2.ZERO) -> int:
	if _tex == null or not _by_name.has(kind):
		return 0
	var e: Dictionary = _emitters[int(_by_name[kind])]
	var aim := 0.0
	if bool(e["aim"]) and not dir.is_zero_approx():
		aim = dir.angle()
	var want: int = _rng.randi_range(int(e["count_min"]), int(e["count_max"]))
	var made := 0
	for n in want:
		var slot := _take()
		if slot < 0:
			break                    # pool exhausted: drop the rest
		var fi := slot * F_STRIDE
		var spread: float = e["spread"]
		var angle: float = aim + _rng.randf_range(float(e["ang_min"]), float(e["ang_max"]))
		var speed: float = _rng.randf_range(float(e["speed_min"]), float(e["speed_max"]))
		_f[fi] = at.x + _rng.randf_range(-spread, spread)
		_f[fi + 1] = at.y + _rng.randf_range(-spread, spread)
		_f[fi + 2] = cos(angle) * speed
		_f[fi + 3] = sin(angle) * speed
		_f[fi + 4] = 0.0
		_f[fi + 5] = _rng.randf_range(float(e["life_min"]), float(e["life_max"]))
		_i[slot * I_STRIDE] = 1
		_i[slot * I_STRIDE + 1] = int(_by_name[kind])
		made += 1
	if made > 0:
		queue_redraw()
	return made

func _take() -> int:
	if _free.is_empty():
		return -1
	var slot := _free[_free.size() - 1]
	_free.remove_at(_free.size() - 1)
	_live += 1
	return slot

func live_count() -> int:
	return _live

func pool_size() -> int:
	return _i.size() / I_STRIDE

func emitter_names() -> PackedStringArray:
	return _names

func clear() -> void:
	if pool_size() == 0:
		return
	_resize(pool_size())
	queue_redraw()

# ---------------------------------------------------------------- simulate
func _physics_process(delta: float) -> void:
	if _live <= 0 or Game.sim_paused:
		return                       # hitstop freezes the debris too
	for slot in pool_size():
		if _i[slot * I_STRIDE] == 0:
			continue
		var fi := slot * F_STRIDE
		var age: float = _f[fi + 4] + delta
		if age >= _f[fi + 5]:
			_i[slot * I_STRIDE] = 0
			_free.append(slot)
			_live -= 1
			continue
		var e: Dictionary = _emitters[_i[slot * I_STRIDE + 1]]
		var damp: float = maxf(0.0, 1.0 - float(e["drag"]) * delta)
		_f[fi + 4] = age
		_f[fi + 2] *= damp
		_f[fi + 3] = _f[fi + 3] * damp + float(e["gravity"]) * delta
		_f[fi] += _f[fi + 2] * delta
		_f[fi + 1] += _f[fi + 3] * delta
	queue_redraw()

func _draw() -> void:
	if _tex == null or _live <= 0:
		return
	for slot in pool_size():
		if _i[slot * I_STRIDE] == 0:
			continue
		var fi := slot * F_STRIDE
		var e: Dictionary = _emitters[_i[slot * I_STRIDE + 1]]
		var frames: PackedInt32Array = e["frames"]
		var age: float = _f[fi + 4]
		var life: float = _f[fi + 5]
		# Played at the authored rate, holding the last frame: a particle always
		# gets through its arc instead of looping back to the bright frame.
		var f := mini(int(age * float(e["fps"])), frames.size() - 1)
		var src := Rect2(float(frames[f]) * _cell, float(int(e["row"])) * _cell, _cell, _cell)
		var col := Color.WHITE
		if bool(e["fade"]):
			col.a = clampf(1.0 - age / life, 0.0, 1.0)
		draw_texture_rect_region(_tex,
			Rect2(Vector2(_f[fi], _f[fi + 1]).round(), Vector2(_cell, _cell)), src, col)
