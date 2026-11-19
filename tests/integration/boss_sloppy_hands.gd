extends RefCounted
## SLOPPY HANDS — a human's thumbs between a boss policy and the buttons.
##
## A strategy tape proves a fight CAN be won. It says nothing about whether a
## person on a phone will win it: the pen reacts on the frame a shot appears,
## presses every button it means to, and never lets its thumb slide off the
## stick. Replaying the winning tape with noise does not answer the question
## either — the boss tracks Kaya, so one late frame desynchronises a blind tape
## and every frame after it is a different fight the tape was never written for.
##
## So the measurement keeps the policy as the BRAIN and puts this in front of its
## HANDS. Every frame the policy decides what it wants held; what actually gets
## pressed is that decision as it stood `delay` frames ago, with the faults a
## touch screen adds on top:
##
##   delay         reaction time, drawn from [delay_min, delay_max] frames and
##                 re-drawn every `redraw_frames`, so it drifts within a fight
##   attack_miss   chance a tap on the attack button does not register at all
##   jump_late     a jump lands 0..jump_late_max frames after it was meant to
##   dropout       the thumb slides off the floating stick: the horizontal axis
##                 reads neutral for a few frames, `dropout_per_s` times a second
##
## Profiles live in tools/bossgate/sloppy.json. Seeded, so a seed is repeatable
## up to what the game itself randomises (beetle loot).
##
## It is installed as `boss_gate_tape.gd`'s static `hands`, which is the one
## door every policy's presses go through, so no boss strategy is edited to be
## measured.

const PROFILES := "res://tools/bossgate/sloppy.json"

var delay_min := 0
var delay_max := 0
var redraw_frames := 30
var attack_miss := 0.0
var jump_late_max := 0
var dropout_per_s := 0.0
var dropout_min := 0
var dropout_max := 0

## Hits Kaya took while these hands were on the controls. Counted here because
## this is the one place every frame of every policy passes through.
var damage_taken := 0
## What each of those hits was, by what was touching her when it was seen:
## "body" (the boss), "add" (any other enemy), "shot" (neither, so a projectile
## that has already been spent on her). Needs `boss` and `player` set.
var causes := {"body": 0, "add": 0, "shot": 0}
var boss: Enemy = null
## The same hits by the boss's `phase` when they landed: {phase: count}.
var by_phase := {}
var player: Player = null
## How near counts as touching, since the hit is seen a frame late and she has
## already been knocked back by then.
const TOUCH_SLOP := 4.0

var _rng := RandomNumberGenerator.new()
var _line: Array = []
var _delay := 0
var _redraw := 0
var _dropout := 0
var _prev: Array = []
var _attack_lost := false
var _jump_wait := 0
var _jump_seen := false
var _last_health := -1

static func load_profile(name: String) -> Dictionary:
	var f := FileAccess.open(PROFILES, FileAccess.READ)
	if f == null:
		return {}
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	var all: Dictionary = parsed
	var p: Variant = all.get(name, {})
	return p as Dictionary if typeof(p) == TYPE_DICTIONARY else {}

func setup(profile: Dictionary, seed_value: int) -> void:
	delay_min = int(profile.get("delay_min", 0))
	delay_max = int(profile.get("delay_max", delay_min))
	redraw_frames = maxi(1, int(profile.get("redraw_frames", 30)))
	attack_miss = float(profile.get("attack_miss", 0.0))
	jump_late_max = int(profile.get("jump_late_max", 0))
	dropout_per_s = float(profile.get("dropout_per_s", 0.0))
	var drop: Array = profile.get("dropout_frames", [0, 0])
	dropout_min = int(drop[0])
	dropout_max = int(drop[1])
	_rng.seed = seed_value
	_line.clear()
	_prev.clear()
	_delay = _rng.randi_range(delay_min, delay_max)
	_redraw = redraw_frames
	_dropout = 0
	_attack_lost = false
	_jump_wait = 0
	_jump_seen = false
	_last_health = -1
	damage_taken = 0
	causes = {"body": 0, "add": 0, "shot": 0}
	by_phase = {}

## Counts any hit since the last look. Called every frame by filter(), and once
## more after the fight, because the hit that ends one lands after its last press.
func observe() -> void:
	if _last_health >= 0 and Game.health < _last_health:
		damage_taken += _last_health - Game.health
		var c := _cause()
		causes[c] = int(causes[c]) + _last_health - Game.health
		var ph := int(boss.get("phase")) if boss != null and is_instance_valid(boss) else -1
		by_phase[ph] = int(by_phase.get(ph, 0)) + _last_health - Game.health
	_last_health = Game.health

func _cause() -> String:
	if player == null or not is_instance_valid(player):
		return "shot"
	var pr := player.aabb().grow(TOUCH_SLOP)
	if boss != null and is_instance_valid(boss) and boss.aabb().intersects(pr):
		return "body"
	for n in player.get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e != null and e != boss and is_instance_valid(e) and e.aabb().intersects(pr):
			return "add"
	return "shot"

## Kaya cannot be hurt while these hands are on. For measuring what a fight
## throws at her over all of its phases, not for counting what it costs.
var unhittable := false

func filter(held: Array) -> Array:
	observe()
	if unhittable and player != null and is_instance_valid(player):
		player.invuln = 999.0

	_line.append(held.duplicate())
	_redraw -= 1
	if _redraw <= 0:
		_redraw = redraw_frames
		_delay = _rng.randi_range(delay_min, delay_max)
	var i := _line.size() - 1 - _delay
	var out: Array = (_line[i] as Array).duplicate() if i >= 0 else []
	# The history only ever needs to reach back delay_max frames.
	if _line.size() > delay_max + 2:
		_line.pop_front()

	# A tap that does not register stays lost until the finger lifts.
	if out.has("attack"):
		if not _prev.has("attack") and not _attack_lost:
			_attack_lost = _rng.randf() < attack_miss
		if _attack_lost:
			out.erase("attack")
	else:
		_attack_lost = false

	# A jump that lands late: the first few frames of the hold do not count.
	if out.has("jump"):
		if not _jump_seen:
			_jump_seen = true
			_jump_wait = _rng.randi_range(0, jump_late_max)
		if _jump_wait > 0:
			_jump_wait -= 1
			out.erase("jump")
	else:
		_jump_seen = false
		_jump_wait = 0

	# The thumb slides off the stick.
	if _dropout <= 0 and dropout_per_s > 0.0 \
			and _rng.randf() < dropout_per_s / float(Engine.physics_ticks_per_second):
		_dropout = _rng.randi_range(dropout_min, dropout_max)
	if _dropout > 0:
		_dropout -= 1
		out.erase("left")
		out.erase("right")

	_prev = out
	return out
