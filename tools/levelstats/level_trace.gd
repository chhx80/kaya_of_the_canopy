class_name LevelTrace
extends RefCounted
## Replays a level's proof tape in the prover's simulation (tools/solver/sim.gd,
## the real Actor and forms) and records where the body is on every frame: the
## trace LevelStats measures. Needs the autoloads -- the form scripts call
## AudioManager -- so it runs in a scene (tools/levelstats/levelstats.tscn, and
## the integration tier), never under --script.
##
## The replay is the prover's own self-check replay: settle, then the tape's
## buttons through ProverTape.apply(), one sim.step() a frame. The integration
## tier checks that it agrees with the real game about when a checkpoint is lit
## (t_levelstats_and_the_game_agree_on_the_checkpoint_frame).

## {"pos", "box", "form", "tape", "partial"} -- see LevelStats. `tape` is "" when
## the tape was replayed, else why it was not (missing, stale).
static func replay(def: LevelLoader.LevelDef, level_path: String) -> Dictionary:
	var tape_path := ProverTape.tape_path_for(level_path)
	var out := {"pos": PackedVector2Array(), "box": PackedVector2Array(),
		"form": PackedStringArray(), "tape": "", "partial": false}
	var why := ProverTape.staleness(tape_path, level_path)
	if why != "":
		out["tape"] = why
		return out
	out["partial"] = ProverTape.is_partial(tape_path)
	var frames := ProverTape.frames(tape_path, level_path)
	var sim := ProverSim.new()
	sim.setup(def)
	(load("res://tools/solver/prove.gd") as GDScript).call("_settle", sim)
	var inp := InputState.new()
	var prev := 0
	var pos := PackedVector2Array()
	var box := PackedVector2Array()
	var form := PackedStringArray()
	pos.resize(frames.size())
	box.resize(frames.size())
	form.resize(frames.size())
	for i in frames.size():
		ProverTape.apply(inp, frames[i], prev)
		sim.step(inp)
		prev = frames[i]
		pos[i] = sim.actor.pos
		box[i] = sim.actor.box
		form[i] = sim.form_id
	out["pos"] = pos
	out["box"] = box
	out["form"] = form
	return out
