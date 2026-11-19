class_name LevelStats
extends RefCounted
## The numbers tools/levelstats.sh reports per level, from the level and the
## path its proof tape plays (docs/plan-longer-levels.md: "five times the route,
## not five times the empty space", and a difficulty curve that is measured).
##
## Pure: it takes a LevelDef, the level's raw JSON and a trace -- the body's
## position, hitbox and form on every frame of the tape -- and returns a
## Dictionary. Replaying the tape to get the trace needs the prover's sim and
## therefore the autoloads (tools/levelstats/level_trace.gd); this half runs in
## the headless unit tier, so tests/test_levelstats.gd checks every number
## against a hand-built level and a hand-built path.
##
## A trace is {"pos": PackedVector2Array, "box": PackedVector2Array,
## "form": PackedStringArray, "tape": "" or why there is no usable tape,
## "partial": bool}. One entry per tape frame, recorded after the frame's step.

const CONFIG_PATH := "res://data/levelstats.json"
const FPS := 60.0
const TS := TileData4.TILE_SIZE

static func cfg() -> Dictionary:
	var f := FileAccess.open(CONFIG_PATH, FileAccess.READ)
	if f == null:
		return {}
	var d: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	return d if typeof(d) == TYPE_DICTIONARY else {}

## Every metric for one level. Route metrics are -1 (and forms empty) when the
## trace has no usable tape; the static ones never depend on it.
static func compute(def: LevelLoader.LevelDef, raw: Dictionary, trace: Dictionary,
		near_tiles: int = -1) -> Dictionary:
	if near_tiles < 0:
		near_tiles = int(cfg().get("near_hazard_tiles", 2))
	var w := def.world.width
	var h := def.world.height
	var sw := Screen.W / TS
	var sh := Screen.H / TS
	var out := {
		"id": def.id,
		"tiles": [w, h],
		"screens": ceili(float(w) / sw) * ceili(float(h) / sh),
		"enemies": 0, "bosses": 0, "gems": 0, "hearts": 0, "keys": 0,
		"checkpoints": 0,
		"tape": String(trace.get("tape", "missing")),
		"partial": bool(trace.get("partial", false)),
	}
	var cps: Array[Rect2] = []
	for e: Dictionary in def.entities:
		var t := String(e.get("type", ""))
		if t.begins_with("enemy_"):
			out["enemies"] = int(out["enemies"]) + 1
		elif t.begins_with("boss_") and t != "boss_exit":
			out["bosses"] = int(out["bosses"]) + 1
		elif t == "gem":
			out["gems"] = int(out["gems"]) + 1
		elif t == "heart":
			out["hearts"] = int(out["hearts"]) + 1
		elif t.begins_with("key_"):
			out["keys"] = int(out["keys"]) + 1
		elif t == "checkpoint":
			cps.append(Checkpoint.trigger_rect(Vector2(float(e["px"]), float(e["py"]))))
	out["checkpoints"] = cps.size()
	var route: Array = raw.get("route", [])
	out["hops"] = route.size()
	var second := 0
	for hop: Variant in route:
		if String((hop as Dictionary).get("form", "human")) != "human":
			second += 1
	out["hops_second_form"] = second

	var pos: PackedVector2Array = trace.get("pos", PackedVector2Array())
	var box: PackedVector2Array = trace.get("box", PackedVector2Array())
	var forms: PackedStringArray = trace.get("form", PackedStringArray())
	var usable := String(out["tape"]) == "" and pos.size() > 0 and box.size() == pos.size()
	if not usable:
		for k: String in ["route_s", "screens_visited", "checkpoints_on_route",
				"longest_gap_s", "enemies_per_min", "hazards_near_route"]:
			out[k] = -1
		out["forms"] = []
		out["checkpoint_s"] = []
		return out

	var n := pos.size()
	var route_s := float(n) / FPS
	out["route_s"] = route_s
	# Screens the body's centre passes through.
	var seen := {}
	for i in n:
		var c := pos[i] + box[i] * 0.5
		seen[Vector2i(int(floor(c.x / Screen.W)), int(floor(c.y / Screen.H)))] = true
	out["screens_visited"] = seen.size()
	# Forms in the order the route first plays them.
	var fl: Array = []
	for f: String in forms:
		if not fl.has(f):
			fl.append(f)
	out["forms"] = fl
	# The first frame the body lights each checkpoint, under the post's own rule.
	var touch: Array = []
	for r: Rect2 in cps:
		for i in n:
			if Rect2(pos[i], box[i]).intersects(r):
				touch.append(i)
				break
	touch.sort()
	out["checkpoints_on_route"] = touch.size()
	var cs: Array = []
	for f: int in touch:
		cs.append(float(f + 1) / FPS)
	out["checkpoint_s"] = cs
	# The longest stretch of route a death sends you back over: spawn, each
	# checkpoint as the route first lights it, and the end of the tape.
	var marks: Array = [0]
	for f: int in touch:
		marks.append(f + 1)
	marks.append(n)
	var gap := 0
	for i in range(1, marks.size()):
		gap = maxi(gap, int(marks[i]) - int(marks[i - 1]))
	out["longest_gap_s"] = float(gap) / FPS
	out["enemies_per_min"] = float(out["enemies"]) / (route_s / 60.0) if route_s > 0.0 else 0.0
	out["hazards_near_route"] = hazards_near(def.world, pos, box, near_tiles)
	return out

## Distinct hazard tiles within `near` tiles of the body on any frame.
static func hazards_near(w: TileWorld, pos: PackedVector2Array, box: PackedVector2Array,
		near: int) -> int:
	var found := {}
	var last := Rect2i(-1, -1, 0, 0)
	for i in pos.size():
		var x0 := int(floor(pos[i].x / TS)) - near
		var y0 := int(floor(pos[i].y / TS)) - near
		var x1 := int(floor((pos[i].x + box[i].x - 0.001) / TS)) + near
		var y1 := int(floor((pos[i].y + box[i].y - 0.001) / TS)) + near
		var r := Rect2i(x0, y0, x1 - x0 + 1, y1 - y0 + 1)
		if r == last:
			continue
		last = r
		for ty in range(maxi(0, y0), mini(w.height - 1, y1) + 1):
			for tx in range(maxi(0, x0), mini(w.width - 1, x1) + 1):
				if w.is_hazard(tx, ty):
					found[ty * w.width + tx] = true
	return found.size()

## The human-readable table: one row per level, then the plan's targets.
static func table(rows: Array) -> String:
	var head := ["level", "tiles", "scr", "vis", "route_s", "hops", "2nd", "cp",
		"gap_s", "enem", "/min", "haz", "forms", "gem/hrt/key", "tape"]
	var lines: Array[PackedStringArray] = [PackedStringArray(head)]
	for r: Dictionary in rows:
		var t: Array = r["tiles"]
		var cp := "%d/%d" % [maxi(0, int(r["checkpoints_on_route"])), int(r["checkpoints"])] \
			if int(r["route_s"]) >= 0 else "-/%d" % int(r["checkpoints"])
		var tape := "ok"
		if String(r["tape"]) != "":
			tape = "NONE" if String(r["tape"]).contains("missing") else "STALE"
		elif bool(r["partial"]):
			tape = "partial"
		lines.append(PackedStringArray([
			String(r["id"]), "%dx%d" % [int(t[0]), int(t[1])], str(r["screens"]),
			_n(r["screens_visited"], "%d"), _n(r["route_s"], "%.1f"), str(r["hops"]),
			str(r["hops_second_form"]), cp, _n(r["longest_gap_s"], "%.1f"),
			str(r["enemies"]) + ("+B" if int(r["bosses"]) > 0 else ""),
			_n(r["enemies_per_min"], "%.1f"), _n(r["hazards_near_route"], "%d"),
			",".join(PackedStringArray(r["forms"])) if not (r["forms"] as Array).is_empty() else "-",
			"%d/%d/%d" % [int(r["gems"]), int(r["hearts"]), int(r["keys"])], tape]))
	var widths: Array[int] = []
	for c in head.size():
		var wmax := 0
		for l in lines:
			wmax = maxi(wmax, l[c].length())
		widths.append(wmax)
	var out := PackedStringArray()
	for l in lines:
		var cells := PackedStringArray()
		for c in l.size():
			cells.append(l[c].rpad(widths[c]) if c == 0 or c == l.size() - 2 or c == 12 \
				else l[c].lpad(widths[c]))
		out.append("  ".join(cells).strip_edges(false, true))
	return "\n".join(out)

static func _n(v: Variant, fmt: String) -> String:
	var f := float(v)
	if f < 0.0:
		return "-"
	return fmt % (int(f) if fmt == "%d" else f)
