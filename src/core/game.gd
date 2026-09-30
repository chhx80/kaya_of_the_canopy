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

## Identity of the running build, shown on the title and pause screens. Three
## bug reports have been ambiguous between "the fix is wrong" and "you are on an
## older build"; this makes that answerable at a glance.
var build_info: Dictionary = {}

## Timestamp first: the commit hash necessarily lags by one when the bundle is
## rebuilt as part of the commit that ships it, but the build time never lies.
func build_label() -> String:
	var t := String(build_info.get("built", "?")).replace("2026-", "")
	var c := String(build_info.get("commit", "?"))
	return "%s %s%s" % [t, c, "+" if bool(build_info.get("dirty", false)) else ""]

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var f := FileAccess.open("res://data/build_info.json", FileAccess.READ)
	if f != null:
		var d: Variant = JSON.parse_string(f.get_as_text())
		f.close()
		if typeof(d) == TYPE_DICTIONARY:
			build_info = d

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

## THE ENDING.
##
## The overworld decides where the game ends, not this file and not levels/.
## Counting FILES is the mistake that made HEART OF THE GROVE unopenable for a
## whole milestone: `requires_all` asked for a flag on every file in levels/,
## which included five levels with no gateway and the integration fixture, so
## the door waited on flags nothing could set. Everything below reads the
## gateway list instead, the way HubDoor.unlocked() reads it.
const HUB_LEVEL := "hub"

## Every level the overworld offers a way into, in gateway order.
func hub_levels() -> PackedStringArray:
	var out := PackedStringArray()
	var def := LevelLoader.load_level(HUB_LEVEL)
	if not def.ok():
		return out
	for d: Dictionary in def.entities_of("hub_door"):
		out.append(String(d.get("level", "")))
	return out

## The last level in the game: the one gateway no other gateway is waiting on.
## Derived rather than hardcoded to "nest_5", so a sixth world ends the game at
## ITS last door with nothing here changed. Empty if the hub does not load or
## does not have exactly one terminus -- tests/test_hub_layout.gd is what keeps
## the chain a chain, and a malformed hub must not accidentally end the game.
func final_level() -> String:
	var def := LevelLoader.load_level(HUB_LEVEL)
	if not def.ok():
		return ""
	var gateways: Array = def.entities_of("hub_door")
	var required := {}
	for d: Dictionary in gateways:
		var req := String(d.get("requires", ""))
		if req != "":
			required[req] = true
	var ends: Array = []
	for d: Dictionary in gateways:
		var id := String(d.get("level", ""))
		if not required.has(id):
			ends.append(id)
	return String(ends[0]) if ends.size() == 1 else ""

## True when every gateway on the overworld is flagged cleared. Not what fires
## the ending -- see complete_level -- but it is what "100%" means, and the
## integration tests measure it.
func run_is_complete() -> bool:
	var levels := hub_levels()
	if levels.is_empty():
		return false
	for id in levels:
		if not SaveManager.get_flag(id):
			return false
	return true

func complete_level(level_id: String) -> void:
	# THE ENDING, and it is two conditions rather than one.
	#
	# It is the LAST DOOR that ends the game, not the last flag. "every gateway
	# is now cleared" reads like the same statement and is not: it also fires on
	# save states the requires chain cannot produce -- clear jungle_1 last, with
	# the other twenty-four already green, and the game would end on World 1's
	# first level -- and it fires on levels the overworld does not even offer,
	# like the test_arena fixture. Both were measured, in the integration suite.
	# Clearing the terminus already implies the chain behind it was walked, so
	# the weaker-looking condition is the stronger one.
	#
	# And it is a FIRST clear. Whether this is the finishing blow has to be
	# decided before the flag goes down, because afterwards a replay of the last
	# level is indistinguishable from finishing it: firing on the state would
	# send every post-game visit to nest_5 to the victory screen instead of back
	# to the hub, and take the finished save away from the player.
	var first_clear := not SaveManager.get_flag(level_id)
	SaveManager.set_flag(level_id, true)
	SaveManager.add_score(score)
	SaveManager.save()
	level_completed.emit(level_id)
	var last := final_level()
	if first_clear and last != "" and level_id == last:
		goto_victory()
	else:
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
