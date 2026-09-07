extends Node
## Autoload. Owns the top-level state machine and the current run's stats.
##
## Scenes are swapped into Main's `World` node; the HUD and menus live on Main's
## `UI` CanvasLayer. Nothing else in the game calls `change_scene_to_*`.

signal state_changed(new_state: int)
signal stats_changed()
signal level_completed(level_id: String)
signal player_died()

enum State { BOOT, TITLE, HUB, LEVEL, PAUSED, GAME_OVER, VICTORY }

const SCREEN_W := Screen.W
const SCREEN_H := Screen.H

const TITLE_SCENE := "res://src/ui/menus/title_screen.tscn"
const HUB_SCENE := "res://src/hub/overworld.tscn"
const LEVEL_SCENE := "res://src/world/level.tscn"
const GAME_OVER_SCENE := "res://src/ui/menus/game_over.tscn"
const VICTORY_SCENE := "res://src/ui/menus/victory.tscn"

var state: State = State.BOOT
var main: Node = null                  ## set by src/core/main.gd on ready

# ---- run stats -------------------------------------------------------------
var max_health := 5
var health := 5
var lives := 3
var score := 0
var gems := 0
var keys := {"yellow": 0, "red": 0, "cyan": 0}
var current_level_id := ""
var current_level: Node = null

## Frozen simulation (camera slide, transitions). Actors check this every tick.
var sim_paused := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS

# ---- stats -----------------------------------------------------------------
func reset_run() -> void:
	max_health = 5
	health = max_health
	lives = 3
	score = 0
	gems = 0
	keys = {"yellow": 0, "red": 0, "cyan": 0}
	stats_changed.emit()

func add_score(n: int) -> void:
	score += n
	stats_changed.emit()

func add_gem(n: int = 1) -> void:
	gems += n
	score += 25 * n
	stats_changed.emit()

func add_health(n: int) -> void:
	health = clampi(health + n, 0, max_health)
	stats_changed.emit()

func add_key(color: String) -> void:
	keys[color] = int(keys.get(color, 0)) + 1
	stats_changed.emit()

func use_key(color: String) -> bool:
	if int(keys.get(color, 0)) <= 0:
		return false
	keys[color] -= 1
	stats_changed.emit()
	return true

func damage(n: int = 1) -> void:
	if health <= 0:
		return
	health = maxi(0, health - n)
	stats_changed.emit()
	if health <= 0:
		player_died.emit()

# ---- state transitions -----------------------------------------------------
func _set_state(s: State) -> void:
	state = s
	state_changed.emit(s)

func goto_title() -> void:
	current_level_id = ""
	current_level = null
	_set_state(State.TITLE)
	_swap(TITLE_SCENE)

func goto_hub(from_level: String = "") -> void:
	current_level_id = ""
	current_level = null
	_set_state(State.HUB)
	var hub := _swap(HUB_SCENE)
	if hub and from_level != "" and hub.has_method("place_at_door"):
		hub.place_at_door(from_level)

func goto_level(level_id: String) -> void:
	current_level_id = level_id
	health = max_health
	_set_state(State.LEVEL)
	var lvl := _swap(LEVEL_SCENE)
	current_level = lvl
	if lvl and lvl.has_method("load_level"):
		lvl.load_level(level_id)
	stats_changed.emit()

func restart_level() -> void:
	if current_level_id != "":
		goto_level(current_level_id)

func complete_level(level_id: String) -> void:
	SaveManager.set_flag(level_id, true)
	SaveManager.add_score(score)
	SaveManager.save()
	level_completed.emit(level_id)
	goto_hub(level_id)

func lose_life() -> void:
	lives -= 1
	stats_changed.emit()
	if lives <= 0:
		goto_game_over()
	else:
		restart_level()

func goto_game_over() -> void:
	_set_state(State.GAME_OVER)
	_swap(GAME_OVER_SCENE)

func goto_victory() -> void:
	_set_state(State.VICTORY)
	_swap(VICTORY_SCENE)

func _swap(scene_path: String) -> Node:
	if main == null:
		push_error("Game: no Main registered; cannot swap to %s" % scene_path)
		return null
	return main.swap_world(scene_path)

# ---- helpers ---------------------------------------------------------------
func screen_size() -> Vector2i:
	return Vector2i(SCREEN_W, SCREEN_H)
