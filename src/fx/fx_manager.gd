extends Node
## Autoload `Fx`. The one place the game asks for juice: particles, screen shake
## and hitstop. Tunables all live in data/fx.json.
##
## Every entry point is a no-op when the effect is unavailable — no config, no
## art, no level, or the player has turned shake off. Nothing in here returns a
## value the game needs, so an effect that fails to load costs a warning and
## nothing else. That is deliberate: juice must never be on the critical path.
##
## Hitstop reuses `Game.sim_paused`, the flag the camera already freezes the
## simulation with, and is careful never to take that flag away from the camera:
## if a screen flip is mid-slide when the freeze ends, the slide keeps ownership.

const CONFIG_PATH := "res://data/fx.json"
## The freeze is bounded twice — here and in data — because a hitstop that never
## ends is indistinguishable from a soft-lock.
const HITSTOP_CEILING := 0.5

var _cfg: Dictionary = {}
var _field: ParticleField = null
var _cam: CameraController = null

var _shake_left := 0.0
var _shake_total := 0.0
var _shake_amp := 0.0
var _shake_hz := 0.0
var _shake_vertical := 1.0

var _hitstop_left := 0.0
var _hitstop_owned := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS   # a freeze must tick itself back out
	_load_config()
	Game.state_changed.connect(_on_state_changed)

func _load_config() -> void:
	var f := FileAccess.open(CONFIG_PATH, FileAccess.READ)
	if f == null:
		push_warning("Fx: no %s; effects are off" % CONFIG_PATH)
		return
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("Fx: %s is not a JSON object; effects are off" % CONFIG_PATH)
		return
	_cfg = parsed

func enabled() -> bool:
	return bool(_cfg.get("enabled", false))

func _section(name: String) -> Dictionary:
	return _cfg.get(name, {})

func _preset(section: String, name: String) -> Dictionary:
	var presets: Dictionary = (_section(section) as Dictionary).get("presets", {})
	return presets.get(name, {})

## A number from the "timings" block — the thresholds and intervals the call
## sites would otherwise have to hard-code.
func timing(key: String, fallback: float) -> float:
	return float((_section("timings") as Dictionary).get(key, fallback))

# ---------------------------------------------------------------- wiring
## Called by a level once its nodes exist. Until then every effect is inert,
## which is exactly what the title screen and the hub want.
func attach(field: ParticleField, cam: CameraController) -> void:
	reset()
	_field = field
	_cam = cam
	if _field != null and not _field.setup(_section("particles")):
		_field = null

## `field` identifies the caller: a level that is torn down *after* its
## successor has attached must not unplug the successor.
func detach(field: ParticleField = null) -> void:
	if field != null and _field != null and field != _field:
		return
	reset()
	_field = null
	_cam = null

## Puts the world back exactly as it was found: no freeze, no offset. Called on
## every state change and whenever a level goes away, so neither effect can
## outlive the scene that asked for it.
func reset() -> void:
	_release_hitstop()
	_shake_left = 0.0
	_shake_amp = 0.0
	if _cam != null and is_instance_valid(_cam):
		_cam.set_shake(Vector2.ZERO)
	if _field != null and is_instance_valid(_field):
		_field.clear()

func _on_state_changed(_s: int) -> void:
	reset()

# ---------------------------------------------------------------- particles
func burst(kind: String, at: Vector2, dir: Vector2 = Vector2.ZERO) -> int:
	if not enabled() or _field == null or not is_instance_valid(_field):
		return 0
	if not in_view(at):
		return 0
	return _field.burst(kind, at, dir)

## Whether a point is on the screen the player is looking at. Bursts outside it
## are dropped rather than pooled: an off-screen gem must never be the reason a
## landing raises no dust. With no camera to ask, everything counts as visible.
func in_view(at: Vector2) -> bool:
	if _cam == null or not is_instance_valid(_cam):
		return true
	return _cam.view_rect().grow(float(TileData4.TILE_SIZE)).has_point(at)

func particles() -> ParticleField:
	return _field if _field != null and is_instance_valid(_field) else null

# ---------------------------------------------------------------- shake
func shake_enabled() -> bool:
	return enabled() and bool((_section("shake") as Dictionary).get("enabled", false)) \
		and bool(SaveManager.setting("screen_shake", true))

## Starts a shake preset. A shake already running is only replaced by a stronger
## one, so a hit during a boss slam cannot flatten the slam.
func shake(preset_name: String) -> void:
	if not shake_enabled() or _cam == null or not is_instance_valid(_cam):
		return
	var p := _preset("shake", preset_name)
	if p.is_empty():
		return
	var cap := float((_section("shake") as Dictionary).get("max_px", CameraController.MAX_SHAKE_PX))
	var amp := clampf(float(p.get("amplitude_px", 0.0)), 0.0,
		minf(cap, CameraController.MAX_SHAKE_PX))
	var secs := maxf(0.0, float(p.get("seconds", 0.0)))
	if amp <= 0.0 or secs <= 0.0:
		return
	if _shake_left > 0.0 and _current_shake_strength() > amp:
		return
	_shake_amp = amp
	_shake_total = secs
	_shake_left = secs
	_shake_hz = maxf(0.0, float(p.get("hz", 20.0)))
	_shake_vertical = clampf(float(p.get("vertical", 1.0)), 0.0, 1.0)

func shake_strength() -> float:
	return _current_shake_strength()

func _current_shake_strength() -> float:
	if _shake_total <= 0.0:
		return 0.0
	return _shake_amp * (_shake_left / _shake_total)

## Deterministic rather than random: two sines that beat against each other decay
## to exactly zero, which is what keeps the camera provably back on its screen.
func _shake_offset() -> Vector2:
	if _shake_left <= 0.0:
		return Vector2.ZERO
	var t := _shake_total - _shake_left
	var falloff := _shake_left / _shake_total
	return Vector2(
		sin(TAU * _shake_hz * t),
		sin(TAU * _shake_hz * 1.37 * t + 1.1) * _shake_vertical) * _shake_amp * falloff

# ---------------------------------------------------------------- hitstop
func hitstop_enabled() -> bool:
	return enabled() and bool((_section("hitstop") as Dictionary).get("enabled", false))

## A few frames of freeze. Refused — not queued — when the simulation is already
## frozen by something else, because stacking freezes is how one gets stuck.
func hitstop(preset_name: String) -> void:
	if not hitstop_enabled() or Game.state != Game.State.LEVEL:
		return
	if _hitstop_left > 0.0 or Game.sim_paused:
		return
	var section := _section("hitstop")
	var presets: Dictionary = section.get("presets", {})
	var ceiling := minf(HITSTOP_CEILING, float(section.get("max_seconds", HITSTOP_CEILING)))
	var secs := clampf(float(presets.get(preset_name, 0.0)), 0.0, ceiling)
	if secs <= 0.0:
		return
	_hitstop_left = secs
	_hitstop_owned = true
	Game.sim_paused = true

func hitstop_active() -> bool:
	return _hitstop_owned

func _release_hitstop() -> void:
	_hitstop_left = 0.0
	if not _hitstop_owned:
		return
	_hitstop_owned = false
	# If a screen flip began while we were frozen, the slide now owns the flag
	# and will clear it when it lands. Taking it back would unfreeze mid-slide.
	if _cam != null and is_instance_valid(_cam) and _cam.is_sliding():
		return
	Game.sim_paused = false

# ---------------------------------------------------------------- tick
func _physics_process(delta: float) -> void:
	if _hitstop_owned:
		_hitstop_left -= delta
		if _hitstop_left <= 0.0:
			_release_hitstop()
	if _shake_left <= 0.0:
		return
	_shake_left = maxf(0.0, _shake_left - delta)
	if _cam == null or not is_instance_valid(_cam):
		_shake_left = 0.0
		return
	# Note the explicit zero on the last tick: the camera must land back on the
	# exact screen origin, not near it.
	_cam.set_shake(Vector2.ZERO if _shake_left <= 0.0 else _shake_offset())
