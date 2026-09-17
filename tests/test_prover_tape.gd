extends TestCase
## The proof tape, and the rule that a stale one fails.
##
## A tape is a claim about one exact grid: these buttons, in this order, finish
## this level. The moment the level changes the claim is about something that no
## longer exists. ADR 005 is blunt about what happens then — a stale tape
## **fails**, it does not warn — because a stale iOS `.pck` once shipped a fix
## that was not in the build.
##
## The pure half of this file exercises `ProverTape` directly. The end-to-end
## half runs the real prover as a child process, edits the level underneath the
## tape it just wrote, and asserts the tool refuses it.

const EXIT_OK := 0
const EXIT_HOP_FAILED := 1

const LEVEL := "user://prover_tape_case.json"
const TAPE := "user://prover_tape_case.tape.json"

const A := preload("res://tools/solver/search.gd")


func after_each() -> void:
	for p: String in [LEVEL, TAPE]:
		if FileAccess.file_exists(p):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(p))


# ------------------------------------------------------------ the encoding

func test_frames_collapse_into_runs() -> void:
	var actions := PackedInt32Array([A.RIGHT, A.RIGHT, A.RIGHT,
		A.RIGHT | A.JUMP, A.RIGHT | A.JUMP, 0])
	var runs := ProverTape.run_length(actions)
	eq(runs.size(), 3, "three distinct stretches of input")
	eq((runs[0] as Dictionary)["n"], 3)
	eq((runs[0] as Dictionary)["a"], "right")
	eq((runs[1] as Dictionary)["n"], 2)
	eq((runs[1] as Dictionary)["a"], "right+jump")
	eq((runs[2] as Dictionary)["a"], "none", "an empty frame is still a frame")


func test_every_action_name_round_trips() -> void:
	# The tape is the contract between the prover and the replay tier. A name
	# that does not decode back to the same buttons is a silently wrong replay.
	for a: int in A.action_set():
		eq(ProverTape.action_bits(A.action_name(a)), a,
			"'%s' should decode back to the action it came from" % A.action_name(a))


func test_applying_a_frame_derives_the_press_and_release_edges() -> void:
	# Coyote time, the jump buffer and the frog's wall kick all read the edges,
	# not the held state, so a replay that only sets `jump` plays differently.
	var input := InputState.new()
	ProverTape.apply(input, A.JUMP, 0)
	ok(input.jump and input.jump_pressed, "the first held frame is a press")
	ProverTape.apply(input, A.JUMP, A.JUMP)
	ok(input.jump and not input.jump_pressed, "holding it is not a press again")
	ProverTape.apply(input, 0, A.JUMP)
	ok(input.jump_released and not input.jump, "letting go is a release")


# --------------------------------------------------------------- staleness

func test_a_tape_matching_its_level_is_not_stale() -> void:
	_write_level(11)
	ProverTape.write(TAPE, "case", LEVEL, [])
	eq(ProverTape.staleness(TAPE, LEVEL), "", "nothing has changed yet")


func test_a_tape_goes_stale_the_moment_the_level_changes() -> void:
	_write_level(11)
	ProverTape.write(TAPE, "case", LEVEL, [])
	_write_level(10)      # one tile of the grid moved
	ne(ProverTape.staleness(TAPE, LEVEL), "",
		"the tape describes a grid that no longer exists")
	ok("changed" in ProverTape.staleness(TAPE, LEVEL),
		"and it should say so: %s" % ProverTape.staleness(TAPE, LEVEL))


func test_a_stale_tape_yields_no_frames_to_replay() -> void:
	# The replay tier gets nothing rather than something misleading.
	_write_level(11)
	ProverTape.write(TAPE, "case", LEVEL,
		[{"from": "spawn", "to": "exit", "form": "human",
		  "frames": [{"n": 30, "a": "right"}]}])
	eq(ProverTape.frames(TAPE, LEVEL).size(), 30, "fresh tape replays")
	_write_level(10)
	eq(ProverTape.frames(TAPE, LEVEL).size(), 0, "stale tape replays nothing")


func test_a_tape_with_no_source_sha_is_stale() -> void:
	_write_level(11)
	var f := FileAccess.open(TAPE, FileAccess.WRITE)
	f.store_string(JSON.stringify({"level": "case", "fps": 60, "hops": []}))
	f.close()
	ne(ProverTape.staleness(TAPE, LEVEL), "", "a tape that cannot be checked is not trusted")


# --------------------------------------------------------------- end to end

func test_the_prover_writes_a_tape_and_then_rejects_it_once_the_level_moves() -> void:
	_write_level(11)
	eq(_run([]), EXIT_OK, "the corridor is walkable, so it should prove")
	ok(FileAccess.file_exists(TAPE), "and proving it should leave a tape")

	var tape := ProverTape.read(TAPE)
	eq(tape.get("fps"), 60, "tapes are recorded at the sim rate")
	eq(tape.get("source_sha"), FileAccess.get_sha256(LEVEL), "against this exact level")
	gt(float((tape.get("hops", []) as Array).size()), 0.0, "with at least one hop in it")

	eq(_run(["--verify-tapes"]), EXIT_OK, "and the tape verifies while nothing has moved")

	_write_level(10)      # the floor rises by one tile; the tape is now a lie
	eq(_run(["--verify-tapes"]), EXIT_HOP_FAILED,
		"a stale tape has to fail the gate, not warn about it")


# ------------------------------------------------------------------ helpers

## A walkable corridor whose floor sits at `floor_row`, so the level can be
## changed by one tile without becoming unfinishable.
func _write_level(floor_row: int) -> void:
	var rows: Array = []
	for y in 13:
		var line := ""
		for x in 14:
			# Rock everywhere but a corridor two tiles tall sitting on floor_row,
			# which is the height Kaya needs and one tile of slack to move it by.
			var solid := x == 0 or x == 13 or y >= floor_row or y < floor_row - 2
			line += "s" if solid else "."
		rows.append(line)
	var doc := {
		"id": "prover_tape_case", "name": "TAPE CASE", "topdown": false,
		"fg": rows, "bg": rows.map(func(_r: String) -> String: return ".".repeat(14)),
		"entities": [
			{"type": "player_spawn", "x": 2, "y": floor_row - 1},
			{"type": "exit", "x": 10, "y": floor_row - 1},
		],
		"route": [{"from": "spawn", "to": "exit", "form": "human"}],
	}
	var f := FileAccess.open(LEVEL, FileAccess.WRITE)
	f.store_string(JSON.stringify(doc))
	f.close()


func _run(extra: Array) -> int:
	var args := PackedStringArray([
		"--headless", "--path", ProjectSettings.globalize_path("res://"),
		"res://tools/solver/prove.tscn", "--",
		"--quiet", "--budget", "8000", "--level-file", LEVEL,
	])
	for e: String in extra:
		args.append(e)
	var out: Array = []
	return OS.execute(OS.get_executable_path(), args, out, true)
