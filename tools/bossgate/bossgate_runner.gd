extends Node
## Headless entry point for the Boss Gate (ADR 005, section 4).
##
## The gate needs the *real* game: autoloads, a Level scene, the boss node, the
## blade, projectiles. `--headless --script` has neither autoloads nor a scene
## tree, so this boots src/core/main.tscn as a child — which is what registers
## Game.main — and then hands control to tests/integration/boss_gate_checks.gd.
##
## Configuration comes from the environment rather than from `--` user args,
## because user args are what switch tools/dev_capture.gd into screenshot mode.
##
##   KAYA_BOSSGATE_LEVEL   level id            (default jungle_5)
##   KAYA_BOSSGATE_BOSS    boss enemy id       (default boss_grove)
##   KAYA_BOSSGATE_MODE    check | record      (default check)
##   KAYA_BOSSGATE_QUICK   1 to thin the sweep (default full)
##   KAYA_BOSSGATE_TAPE    tape path           (default res://tools/bossgate/tapes/<boss>.json)
##
## KAYA_BOSSGATE_MODE=sloppy is a measurement, not a check (see _sloppy):
##   KAYA_BOSSGATE_PROFILE  hands profile in tools/bossgate/sloppy.json (default phone)
##   KAYA_BOSSGATE_SEEDS    fights to run                               (default 20)
##   KAYA_BOSSGATE_FIGHT_S  give up on a fight after this many seconds  (default 150)

const Checks := preload("res://tests/integration/boss_gate_checks.gd")
const Strategy := preload("res://tests/integration/boss_gate_strategy.gd")
const Tape := preload("res://tests/integration/boss_gate_tape.gd")
const Smoke := preload("res://tests/integration/boss_gate_smoke.gd")
const Hands := preload("res://tests/integration/boss_sloppy_hands.gd")
const TellProbe := preload("res://tests/integration/boss_tell_probe.gd")

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var main: PackedScene = load("res://src/core/main.tscn")
	add_child(main.instantiate())
	call_deferred("_run")

func _env(key: String, fallback: String) -> String:
	var v := OS.get_environment(key)
	return v if v != "" else fallback

func _run() -> void:
	var t0 := Time.get_ticks_msec()
	var checks: Node = Checks.new()
	checks.level_id = _env("KAYA_BOSSGATE_LEVEL", "jungle_5")
	checks.boss_id = _env("KAYA_BOSSGATE_BOSS", "boss_grove")
	checks.quick = _env("KAYA_BOSSGATE_QUICK", "") != ""
	checks.tape_path = _env("KAYA_BOSSGATE_TAPE",
		"res://tools/bossgate/tapes/%s.json" % checks.boss_id)
	checks.name = "BossGateChecks"
	add_child(checks)

	var code := 0
	var mode := _env("KAYA_BOSSGATE_MODE", "check")
	if mode == "smoke":
		code = await _smoke(checks)
	elif mode == "probe":
		code = await _probe(checks)
	elif mode == "record":
		code = await _record(checks)
	elif mode == "sloppy":
		code = await _sloppy(checks)
	elif mode == "tells":
		code = await _tells(checks)
	else:
		code = await checks.run_all()
	print("boss gate: %.1fs wall" % ((Time.get_ticks_msec() - t0) / 1000.0))
	get_tree().quit(code)

## Runs the bounded in-suite case on its own, so its cost can be measured the
## way tools/itest.sh would pay it — at wall-clock speed, with no --fixed-fps.
func _smoke(checks: Node) -> int:
	var s: Node = Smoke.new()
	s.level_id = checks.level_id
	s.boss_id = checks.boss_id
	s.tape_path = checks.tape_path
	add_child(s)
	var code: int = await s.run_all()
	for f in s.failures:
		print("  FAIL  %s" % f)
	print("boss gate smoke: %d checks, %s"
		% [s.passes + s.failures.size(),
			"ALL PASSED" if s.failures.is_empty() else "%d FAILED" % s.failures.size()])
	return code

## A measuring stick, not a gate: prints what the blade does to the boss at a
## range of distances. Used to work out why a strategy was losing.
func _probe(checks: Node) -> int:
	var ok: bool = await checks.boot()
	if not ok:
		return 1
	var rec: Node = Strategy.new()
	add_child(rec)
	if OS.get_environment("KAYA_BOSSGATE_PROBE") == "adds":
		await rec.probe_adds(checks)
	else:
		await rec.probe_blade(checks)
	return 0

## THE SLOPPY PLAYER. The strategy tape proves the fight can be won by a pen
## with perfect hands; this asks how often it is won by the same plan with a
## person's. Each boss's own policy fights it `seeds` times through
## tests/integration/boss_sloppy_hands.gd, and what comes back is the number every
## boss is held to: how many of those fights were won, and how many hearts the
## average one cost. Exit 0 whatever the result — it measures, it does not judge.
const STRATEGIES := {
	"boss_grove": "res://tests/integration/boss_gate_strategy.gd",
	"tide_maw": "res://tests/integration/boss_tide_maw_strategy.gd",
	"stormcrest": "res://tests/integration/boss_stormcrest_strategy.gd",
	"brood_queen": "res://tests/integration/boss_brood_queen_strategy.gd",
	"obsidian_heart": "res://tests/integration/boss_obsidian_heart_strategy.gd",
}

func _sloppy(checks: Node) -> int:
	var profile_name := _env("KAYA_BOSSGATE_PROFILE", "phone")
	var profile := Hands.load_profile(profile_name)
	if profile.is_empty():
		print("  FAIL  no hands profile '%s' in %s" % [profile_name, Hands.PROFILES])
		return 1
	var seeds := int(_env("KAYA_BOSSGATE_SEEDS", "20"))
	var fight_s := float(_env("KAYA_BOSSGATE_FIGHT_S", "150"))
	var path: String = STRATEGIES.get(checks.boss_id, "")
	if path == "":
		print("  FAIL  no strategy for boss '%s'" % checks.boss_id)
		return 1
	var rec: Node = (load(path) as GDScript).new()
	rec.name = "SloppyStrategy"
	add_child(rec)
	# The plan is the one that won: the knobs the recorder wrote into the tape,
	# unless told otherwise. A tape from before the recorder kept them has none,
	# and the policy's own defaults are then the plan being measured.
	var knobs: Dictionary = Tape.load_tape(checks.tape_path).get("knobs", {})
	var fixed := _env("KAYA_BOSSGATE_KNOBS", "")
	if fixed != "":
		var parsed: Variant = JSON.parse_string(fixed)
		if typeof(parsed) == TYPE_DICTIONARY:
			knobs = parsed as Dictionary
	rec.configure(knobs)
	print("  plan: %s" % JSON.stringify(knobs))
	print("SLOPPY PLAYER  %s in %s, hands '%s', %d fights of up to %.0f s"
		% [checks.boss_id, checks.level_id, profile_name, seeds, fight_s])
	var wins := 0
	var deaths := 0
	var timeouts := 0
	var hits_total := 0
	var win_secs := 0.0
	var dealt_total := 0
	var max_hp := 0
	var cause_total := {"body": 0, "add": 0, "shot": 0}
	var phase_total := {}
	for i in seeds:
		await checks.frames(75)
		var booted: bool = await checks.boot()
		if not booted:
			print("  FAIL  could not boot %s" % checks.level_id)
			return 1
		var hands := Hands.new()
		hands.setup(profile, 1000 + i)
		hands.boss = checks.boss
		hands.player = checks.pl
		Tape.hands = hands
		rec.set("max_frames", int(fight_s * 60.0))
		var t: Dictionary = await rec.record(checks)
		hands.observe()
		Tape.hands = null
		Tape.release_all()
		var o: Dictionary = t["outcome"]
		var won: bool = bool(o["boss_defeated"]) and not bool(o["kaya_dead"])
		var secs := float(int(t["recorded_frames"])) / 60.0
		var hits := hands.damage_taken
		max_hp = checks.boss.max_health
		var dealt := max_hp - maxi(0, int(o["boss_health"]))
		if won:
			wins += 1
			win_secs += secs
		elif bool(o["kaya_dead"]) or Game.health <= 0:
			deaths += 1
		else:
			timeouts += 1
		hits_total += hits
		dealt_total += dealt
		for k: String in cause_total.keys():
			cause_total[k] = int(cause_total[k]) + int(hands.causes[k])
		for ph: int in hands.by_phase.keys():
			phase_total[ph] = int(phase_total.get(ph, 0)) + int(hands.by_phase[ph])
		print("    seed %2d  %-7s %5.1f s  boss %2d/%d dealt  hits taken %d (body %d, add %d, shot %d)  hearts left %d"
			% [i, "WIN" if won else ("dead" if bool(o["kaya_dead"]) else "timeout"),
				secs, dealt, max_hp, hits, int(hands.causes["body"]), int(hands.causes["add"]),
				int(hands.causes["shot"]), int(o["hearts_left"])])
	var n := float(maxi(1, seeds))
	print("  SLOPPY %s/%s: won %d/%d (%.0f%%), died %d, timed out %d | hits taken %.2f a fight | boss damage dealt %.0f%% | mean win %.1f s"
		% [checks.boss_id, profile_name, wins, seeds, 100.0 * float(wins) / n, deaths,
			timeouts, float(hits_total) / n, 100.0 * float(dealt_total) / (n * float(maxi(1, max_hp))),
			win_secs / float(maxi(1, wins))])
	print("  hits by cause: body %d, add %d, shot %d"
		% [int(cause_total["body"]), int(cause_total["add"]), int(cause_total["shot"])])
	var phs := phase_total.keys()
	phs.sort()
	var parts: PackedStringArray = []
	for ph: int in phs:
		parts.append("phase %d: %d" % [ph, int(phase_total[ph])])
	print("  hits by phase: %s" % ", ".join(parts))
	return 0

## What the fight gives a player to read: every tell, how long it is held, and
## how long after it the attack reaches her; and how many threats are live at
## once. Kaya cannot be hurt, so the fight runs through all its phases on the
## boss's own policy. See tests/integration/boss_tell_probe.gd.
func _tells(checks: Node) -> int:
	var path: String = STRATEGIES.get(checks.boss_id, "")
	if path == "":
		print("  FAIL  no strategy for boss '%s'" % checks.boss_id)
		return 1
	var rec: Node = (load(path) as GDScript).new()
	add_child(rec)
	var knobs: Dictionary = Tape.load_tape(checks.tape_path).get("knobs", {})
	var fights := int(_env("KAYA_BOSSGATE_SEEDS", "5"))
	var profile := Hands.load_profile(_env("KAYA_BOSSGATE_PROFILE", "clean"))
	var probe: Node = TellProbe.new()
	add_child(probe)
	var secs := 0.0
	# Several fights, because one clean fight is over before most of its
	# attacks have been seen twice.
	for i in fights:
		await checks.frames(75)
		var ok: bool = await checks.boot()
		if not ok:
			return 1
		rec.configure(knobs)
		rec.set("max_frames", int(float(_env("KAYA_BOSSGATE_FIGHT_S", "240")) * 60.0))
		probe.call("attach", checks.boss, checks.pl, checks.arena)
		var hands := Hands.new()
		hands.setup(profile, 1000 + i)
		hands.player = checks.pl
		hands.boss = checks.boss
		hands.unhittable = true
		Tape.hands = hands
		var t: Dictionary = await rec.record(checks)
		Tape.hands = null
		Tape.release_all()
		probe.call("detach")
		secs += float(int(t["recorded_frames"])) / 60.0
	var names: Array = []
	for p: Dictionary in checks.boss.cfg.get("phases", []):
		names.append(String(p.get("name", "")))
	print("TELLS  %s in %s: %d fight(s), %.1f s of fight, hands '%s'"
		% [checks.boss_id, checks.level_id, fights, secs,
			_env("KAYA_BOSSGATE_PROFILE", "clean")])
	probe.report(names)
	return 0

## Authoring the strategy tape is a search, not a hand. The policy in
## boss_gate_strategy.gd has a dozen knobs; this walks them one at a time,
## keeping whatever setting fought better, and stops the moment a run kills the
## Warden with a heart to spare. What gets written out is that run's buttons —
## the knobs are scaffolding and do not appear in the tape.
const KNOBS := [
	["near", [30.0, 40.0, 48.0, 56.0, 64.0, 80.0]],
	["far", [56.0, 72.0, 92.0, 108.0]],
	["under_trigger", [56.0, 70.0, 84.0, 112.0]],
	["under_min", [16.0, 30.0, 44.0]],
	["under_hold", [26, 36, 44, 64]],
	["jump_hold", [14, 18, 22, 26]],
	["dodge_lead", [0.20, 0.26, 0.32, 0.40]],
	["dodge_late", [0.06, 0.11, 0.16]],
	["panic_hold", [8, 20, 34, 56]],
	["add_jump_gap", [18.0, 26.0, 34.0, 44.0]],
	["throw_min", [16.0, 22.0, 28.0, 40.0]],
	["throw_max", [88.0, 100.0, 112.0, 118.0]],
	["use_under", [true, false]],
	["add_mode", [0, 1]],
	["hop_mode", [true, false]],
	["hop_period", [30, 38, 44, 52]],
	["throw_airborne", [true, false]],
	["flee_gap", [26.0, 34.0, 40.0, 48.0]],
]
const PASSES := 3

## Damage dealt dominates deliberately. An earlier weighting scored survival
## highly enough that the search settled on a strategy which never threw the
## blade at all: it survived the full ninety seconds and dealt one damage, and
## every later trial was measured against that. Staying alive is worth
## something only while she is also fighting.
func _score(t: Dictionary) -> float:
	var o: Dictionary = t["outcome"]
	var dealt := _max_hp - int(o["boss_health"])
	var s := float(dealt) * 40.0 + float(int(o["hearts_left"])) * 4.0
	if bool(o["boss_defeated"]):
		s += 1000.0
	if bool(o["kaya_dead"]):
		s -= 40.0
	return s

## ADR 005's check 2 passes at one heart left, and one heart is a bad thing to
## aim at: the first win this descent stumbled into once the pen learned to aim
## kept exactly one of five, which is a coin flip dressed up as a proof. So the
## search does not stop at a win, it stops at a win worth showing — and if it
## never finds one it writes the best win it did see rather than nothing, saying
## so. THE TIDE MAW's tape keeps three of five; that is the bar.
const WANT_HEARTS := 3

## Good enough to stop searching.
func _won(t: Dictionary) -> bool:
	return _acceptable(t) \
		and int((t["outcome"] as Dictionary)["hearts_left"]) >= WANT_HEARTS

## Good enough to write down: exactly what the gate will accept, no more.
func _acceptable(t: Dictionary) -> bool:
	var o: Dictionary = t["outcome"]
	return bool(o["boss_defeated"]) and not bool(o["kaya_dead"]) \
		and int(o["hearts_left"]) >= 1

## Fewer hearts lost first, then a shorter fight: a tape is a demonstration, and
## one that dawdles demonstrates the wrong thing.
func _better_win(t: Dictionary, than: Dictionary) -> bool:
	if than.is_empty():
		return true
	var a: Dictionary = t["outcome"]
	var b: Dictionary = than["outcome"]
	if int(a["hearts_left"]) != int(b["hearts_left"]):
		return int(a["hearts_left"]) > int(b["hearts_left"])
	return int(t["recorded_frames"]) < int(than["recorded_frames"])

## Every win goes through here, so the search can carry on looking for a better
## one without losing the one it already has.
func _keep(t: Dictionary) -> void:
	if _acceptable(t) and _better_win(t, _best_win):
		_best_win = t

## Four structurally different openings, because a single greedy descent locks
## onto whichever knob it improved first and never looks at the others again:
## seeded with the hop strategy it settled three whole hearts worse than the
## default and never climbed back out.
const SEEDS := [
	{},
	{"hop_mode": true, "throw_airborne": true},
	{"use_under": false, "near": 96.0, "far": 112.0},
	{"add_mode": 1, "near": 48.0},
]

var _tries := 0
## The boss's full health, read at boot: what "damage dealt" is out of.
var _max_hp := 18
var _best: Dictionary = {}
var _best_score := -1e9
## The best tape seen so far that the gate would actually accept.
var _best_win: Dictionary = {}

func _record(checks: Node) -> int:
	var ok: bool = await checks.boot()
	if not ok:
		print("  FAIL  could not boot %s" % checks.level_id)
		return 1
	var rec: Node = Strategy.new()
	rec.name = "BossGateStrategy"
	add_child(rec)
	_max_hp = checks.boss.max_health

	# The pen's own defaults, first and on their own. The descent below never
	# tries them — its first trial is already the first value of its first knob —
	# and since the pen learned to aim (see the note at the top of
	# tests/integration/boss_gate_strategy.gd) the defaults are a real candidate
	# rather than a starting point. A tape recorded from them is also the tape
	# that is cheapest to reproduce by hand.
	# One named setting, no search: KAYA_BOSSGATE_KNOBS='{"use_under": false}'.
	# The search below is thorough and slow, and when the question is "what does
	# THIS policy do", running it seven hundred times is not the way to ask. Pair it
	# with KAYA_BOSSGATE_TRACE=1.
	var fixed := _env("KAYA_BOSSGATE_KNOBS", "")
	if fixed != "":
		var parsed: Variant = JSON.parse_string(fixed)
		if typeof(parsed) != TYPE_DICTIONARY:
			print("  FAIL  KAYA_BOSSGATE_KNOBS is not a JSON object: %s" % fixed)
			return 1
		rec.configure(parsed as Dictionary)
		var one: Dictionary = await rec.record(checks)
		one["knobs"] = parsed
		_tries = 1
		_keep(one)
		var o1: Dictionary = one["outcome"]
		print("      knobs %s  ->  warden %2d hp, kaya %d hearts%s"
			% [fixed, int(o1["boss_health"]), int(o1["hearts_left"]), _win_tag(one)])
		if _best_win.is_empty():
			print("  No tape written: a tape that does not win is not a proof.")
			return 1
		return _write(checks, _best_win, _tries)

	rec.configure({})
	var plain: Dictionary = await rec.record(checks)
	plain["knobs"] = {}
	_tries += 1
	_best = plain
	_best_score = _score(plain)
	var o0: Dictionary = plain["outcome"]
	_keep(plain)
	print("      try   1  %-14s = %-6s  ->  warden %2d hp, kaya %d hearts%s"
		% ["(defaults)", "-", int(o0["boss_health"]), int(o0["hearts_left"]),
			_win_tag(plain)])
	if _won(plain):
		return _write(checks, _best_win, _tries)

	for seed_i in SEEDS.size():
		var won: bool = await _descend(checks, rec, SEEDS[seed_i], seed_i)
		if won:
			return _write(checks, _best_win, _tries)
	if not _best_win.is_empty():
		print("  %d strategies tried and none of them kept %d hearts, so what is"
			% [_tries, WANT_HEARTS])
		print("  written is the best win any of them managed:")
		return _write(checks, _best_win, _tries)
	var o: Dictionary = _best["outcome"] if _best.has("outcome") else {}
	print("  %d strategies tried; the best left the Warden on %s health with Kaya on %s."
		% [_tries, str(o.get("boss_health", "?")), str(o.get("hearts_left", "?"))])
	print("  No tape written: a tape that does not win is not a proof.")
	return 1

## Greedy coordinate descent from one opening. Returns true if it won.
func _descend(checks: Node, rec: Node, seed: Dictionary, seed_i: int) -> bool:
	var params: Dictionary = seed.duplicate()
	var local := -1e9
	print("    seed %d: %s" % [seed_i, JSON.stringify(seed)])
	for pass_i in PASSES:
		for knob: Array in KNOBS:
			var key: String = knob[0]
			for v: Variant in (knob[1] as Array):
				var trial := params.duplicate()
				trial[key] = v
				if trial == params and _tries > 0:
					continue
				rec.configure(trial)
				# A losing attempt ends with Kaya dead, and the level answers
				# that on its own clock: died -> 0.9 s -> lose_life ->
				# restart_level, which swaps the whole level out from under the
				# next attempt. Let that finish, then boot a clean one.
				await checks.frames(75)
				var booted: bool = await checks.boot()
				if not booted:
					print("    could not re-boot the arena; stopping the search")
					return false
				var t: Dictionary = await rec.record(checks)
				# The plan travels with its buttons, so the sloppy-player
				# measurement can fight with the same plan that won.
				t["knobs"] = trial
				_tries += 1
				var held: Dictionary = _best_win
				_keep(t)
				var sc := _score(t)
				if sc > local:
					local = sc
					params = trial
				# Printed when the run is the best yet by score OR when it is the best
				# win yet, because those are no longer the same thing: a run that trades
				# two hearts for the same kill scores barely higher and is the one worth
				# writing down.
				if sc > _best_score or _best_win != held:
					if sc > _best_score:
						_best_score = sc
						_best = t
					print("      try %3d  %-14s = %-6s  ->  warden %2d hp, kaya %d hearts%s"
						% [_tries, key, str(v),
							int((t["outcome"] as Dictionary)["boss_health"]),
							int((t["outcome"] as Dictionary)["hearts_left"]),
							_win_tag(t)])
				if _won(t):
					return true
	return false

func _win_tag(t: Dictionary) -> String:
	if _won(t):
		return "  WIN"
	return "  win, but thin" if _acceptable(t) else ""

func _write(checks: Node, tape: Dictionary, tries: int) -> int:
	var outcome: Dictionary = tape["outcome"]
	print("  won on try %d: %d frames (%.1f s), %d hearts left, lowest %d"
		% [tries, int(tape["recorded_frames"]), float(int(tape["recorded_frames"])) / 60.0,
			int(outcome["hearts_left"]), int(outcome["lowest_hearts"])])
	if not Tape.save(checks.tape_path, tape):
		return 1
	print("  wrote %s" % checks.tape_path)
	return 0
