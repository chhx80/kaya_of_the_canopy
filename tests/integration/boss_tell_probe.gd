extends Node
## Watches a boss fight and writes down what the player is given to read.
##
## Not a check. It is attached to a fight in progress (KAYA_BOSSGATE_MODE=tells
## runs the boss's own policy with Kaya made unhittable, so the fight lasts all
## three phases however it goes) and, every physics frame, notes:
##
##   tells    every entry into a WINDUP or SPRAY state — the poses that announce
##            an attack — how many frames the pose is held, and how many frames
##            after it began the attack it announced first OVERLAPPED Kaya
##            (her box against the boss's body, or against any shot born since
##            the pose began). That second number is the reaction window: what
##            a person has between seeing the tell and being hit.
##   threats  how many hostile things are live at once: shots in flight plus
##            enemies other than the boss inside its arena.
##
## Everything is per phase, by the boss's own `phase`. Generic over all five
## bosses: state names are read from each script's `St` enum.

const TELL_STATES := ["WINDUP", "SPRAY"]
## Give up on an announced attack reaching her after this long.
const REACH_CAP := 240

var boss: Enemy = null
var player: Player = null
var arena := Rect2()

var _names: Dictionary = {}      ## st value -> name
var _prev_st := -1
var _frame := 0
var _open: Array = []            ## [{tag, phase, start, end, reach, born_after}]
var tells: Array = []            ## closed instances
var threat_frames: Dictionary = {}   ## phase -> [frames, sum, max]

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS

## Start watching one fight. The probe outlives it, so several fights add up.
func attach(b: Enemy, p: Player, a: Rect2) -> void:
	boss = b
	player = p
	arena = a
	_prev_st = -1
	_open.clear()
	_names.clear()
	var map: Dictionary = boss.get_script().get_script_constant_map()
	var st_enum: Variant = map.get("St", {})
	if typeof(st_enum) == TYPE_DICTIONARY:
		for k: String in (st_enum as Dictionary).keys():
			_names[int((st_enum as Dictionary)[k])] = k

## Stop watching. A tell whose attack had not reached her by the end of the
## fight still counts, as one that never did.
func detach() -> void:
	for o: Dictionary in _open:
		if int(o["end"]) < 0:
			o["end"] = _frame
		o.erase("shots")
		tells.append(o)
	_open.clear()
	boss = null
	player = null

func _physics_process(_delta: float) -> void:
	if boss == null or not is_instance_valid(boss) or player == null:
		return
	_frame += 1
	var st := int(boss.get("st"))
	var ph := int(boss.get("phase"))
	var name: String = _names.get(st, "st%d" % st)
	if st != _prev_st:
		for o: Dictionary in _open:
			if int(o["end"]) < 0 and int(o["st"]) == _prev_st:
				o["end"] = _frame
		if name in TELL_STATES:
			var prev_name: String = _names.get(_prev_st, "st%d" % _prev_st)
			_open.append({"tag": "%s>%s" % [prev_name, name], "st": st, "phase": ph,
				"start": _frame, "end": -1, "reach": -1, "shots": {}})
	_prev_st = st

	var pr := player.aabb()
	var shots := get_tree().get_nodes_in_group(&"hostile_shots")
	var live := 0
	for n in shots:
		if is_instance_valid(n):
			live += 1
	for n in get_tree().get_nodes_in_group(&"enemies"):
		var e := n as Enemy
		if e != null and e != boss and is_instance_valid(e) and arena.has_point(e.center()):
			live += 1
	var tf: Array = threat_frames.get(ph, [0, 0, 0])
	tf[0] = int(tf[0]) + 1
	tf[1] = int(tf[1]) + live
	tf[2] = maxi(int(tf[2]), live)
	threat_frames[ph] = tf

	# The body counts only while it is doing what the tell announced, not when it
	# has gone back to walking at her.
	var body_hits: bool = boss.aabb().intersects(pr) and not (name in ["WALK", "IDLE"])
	var keep: Array = []
	for o: Dictionary in _open:
		var seen: Dictionary = o["shots"]
		for n in shots:
			var s := n as Projectile
			if s != null and is_instance_valid(s) and not seen.has(s.get_instance_id()):
				# Born while this tell was open or after it: its attack.
				seen[s.get_instance_id()] = s
		if int(o["reach"]) < 0:
			var hit := body_hits and int(o["end"]) >= 0
			for id: int in seen.keys():
				var s2: Variant = seen[id]
				if is_instance_valid(s2) and (s2 as Projectile).aabb().intersects(pr):
					hit = true
			if hit:
				o["reach"] = _frame - int(o["start"])
		var age := _frame - int(o["start"])
		if int(o["end"]) >= 0 and (int(o["reach"]) >= 0 or age > REACH_CAP):
			o.erase("shots")
			tells.append(o)
		else:
			keep.append(o)
	_open = keep

## One line per (phase, tell): count, pose length and reaction window, in frames.
func report(phase_names: Array) -> void:
	var groups: Dictionary = {}
	for o: Dictionary in tells:
		var key := "%d|%s" % [int(o["phase"]), String(o["tag"])]
		if not groups.has(key):
			groups[key] = []
		(groups[key] as Array).append(o)
	var keys := groups.keys()
	keys.sort()
	for key: String in keys:
		var arr: Array = groups[key]
		var ph := int(key.split("|")[0])
		var lens: Array = []
		var reach: Array = []
		for o: Dictionary in arr:
			lens.append(int(o["end"]) - int(o["start"]))
			if int(o["reach"]) >= 0:
				reach.append(int(o["reach"]))
		lens.sort()
		reach.sort()
		var pname: String = phase_names[ph] if ph < phase_names.size() else str(ph)
		print("  phase %d %-9s %-13s x%-3d pose %2d f (%.2f s) | reached Kaya %d/%d, after %s"
			% [ph, pname, String(key.split("|")[1]), arr.size(), int(lens[lens.size() / 2]),
				float(int(lens[lens.size() / 2])) / 60.0, reach.size(), arr.size(),
				"min %d f / median %d f (%.2f s)" % [int(reach[0]), int(reach[reach.size() / 2]),
					float(int(reach[reach.size() / 2])) / 60.0] if not reach.is_empty() else "-"])
	var phs := threat_frames.keys()
	phs.sort()
	for ph: int in phs:
		var tf: Array = threat_frames[ph]
		var pname2: String = phase_names[ph] if ph < phase_names.size() else str(ph)
		print("  phase %d %-9s threats live at once: mean %.1f, max %d  (%.1f s observed)"
			% [ph, pname2, float(int(tf[1])) / float(maxi(1, int(tf[0]))), int(tf[2]),
				float(int(tf[0])) / 60.0])
