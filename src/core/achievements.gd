extends Node
## Game Center achievements: one per world, earned by clearing its boss level
## (data/achievements.json; the decisions live in AchievementBook).
##
## Two facts about the platform shape this:
## * The Game Center plugin's success event does not say WHICH achievement it
##   was for, so results cannot be matched to requests. Instead every unlocked
##   achievement is re-reported after each sign-in; reporting a completed one
##   again is a no-op in GameKit, and one earned offline still gets through.
## * Unlocks are recorded in the save (its own section, kept across NEW GAME),
##   not in Game Center, so a player who is
##   never signed in loses nothing and the game behaves the same on desktop,
##   where there is no Game Center at all.

signal unlocked(id: String)

var entries: Array = []
## The GameCenter engine singleton on iOS, or a test double; null elsewhere.
var backend: Object = null
var signed_in := false
## Unlocked during this session: only these get the system's banner. Old ones
## re-reported after sign-in arrive silently.
var _fresh: Dictionary = {}

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS     # sign-in events arrive while paused, too
	entries = AchievementBook.load_entries()
	Game.level_completed.connect(_on_level_completed)
	_backfill()
	if Engine.has_singleton("GameCenter"):
		use_backend(Engine.get_singleton("GameCenter"))

## Attach a platform (or a fake) and ask it to sign the player in.
func use_backend(b: Object) -> void:
	backend = b
	signed_in = false
	if backend != null and backend.has_method("authenticate"):
		backend.call("authenticate")

func is_unlocked(id: String) -> bool:
	return SaveManager.has_achievement(id)

func _process(_delta: float) -> void:
	if backend == null:
		return
	while int(backend.call("get_pending_event_count")) > 0:
		var ev: Variant = backend.call("pop_pending_event")
		if typeof(ev) != TYPE_DICTIONARY:
			continue
		var d: Dictionary = ev
		if String(d.get("type", "")) == "authentication":
			signed_in = String(d.get("result", "")) == "ok"
			if signed_in:
				report_all()

func _on_level_completed(level_id: String) -> void:
	for id in AchievementBook.for_level(entries, level_id):
		_unlock(id, true)

func _unlock(id: String, fresh: bool) -> void:
	if is_unlocked(id):
		return
	SaveManager.set_achievement(id)
	SaveManager.save()
	if fresh:
		_fresh[id] = true
	unlocked.emit(id)
	_report(id)

## A boss cleared before achievements existed earns its achievement now,
## quietly: there is no moment to celebrate, it is just put right.
func _backfill() -> void:
	for id in AchievementBook.owed(entries,
			func(level: String) -> bool: return SaveManager.get_flag(level),
			func(a: String) -> bool: return SaveManager.has_achievement(a)):
		_unlock(id, false)

func report_all() -> void:
	for e: Variant in entries:
		var id := String((e as Dictionary).get("id", ""))
		if is_unlocked(id):
			_report(id)

func _report(id: String) -> void:
	if backend == null or not signed_in:
		return            # reported on the next successful sign-in instead
	# The banner belongs to the first time an achievement reaches Game Center,
	# even if that is a later sign-in; every re-report after that is silent.
	var banner := _fresh.has(id)
	_fresh.erase(id)
	backend.call("award_achievement", {
		"name": id, "progress": 100.0, "show_completion_banner": banner})
