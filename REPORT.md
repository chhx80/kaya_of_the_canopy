# M1 — headless integration tier + tape replay

Branch `wave1/replay`. Everything below was run in this worktree; numbers are
measured, not estimated.

---

## READ THIS FIRST — a shipping bug that blocks the whole of M1

**ADR 005 puts proof tapes at `levels/<id>.tape.json`. `LevelLoader.list_levels()`
globs `levels/*.json`, so every tape is picked up as a level.** The moment my
fixture tape landed, this happened:

| What | Before the tape | After the tape |
|------|-----------------|----------------|
| `LevelLoader.list_levels()` | 7 ids | 8 ids, incl. `"test_arena.tape"` |
| `tools/test.sh` | 0 failed | **1 failed** (`test_level_validity :: test_every_level_parses_cleanly`) |
| `tools/validate.sh` | OK | **1 problem** + `tools/reachability.py` dies with `KeyError: 'fg'` |
| HEART OF THE GROVE door, after clearing all 5 levels | `unlocked=true` | **`unlocked=false`** |

That last row is not a test-hygiene problem, it is the game. `src/hub/door.gd:26`
resolves a `requires_all` door by demanding a save flag for **every** id
`list_levels()` returns. Nothing ever completes a level called
`test_arena.tape`, so the flag is never set, so **the final hub door can never
open in a shipped build**. `levels/` is not in any `exclude_filter` in
`export_presets.cfg`, so tapes ship inside the `.pck` and the break reaches a
phone.

I verified this in the booted hub rather than by reading the code — the test set
only the five flags a player can actually earn, then read the door back:

```
=== WITH tape ===     [tmp] final door 'jungle_5' unlocked=false
=== WITHOUT tape ===  [tmp] final door 'jungle_5' unlocked=true
```

### The fix — two lines, verified, NOT applied

I applied both, confirmed all three gates go green, then **reverted them**,
because `src/**` is on my do-not-edit list and `tools/reachability.py` is not
mine either. Whoever owns them needs these:

```diff
--- a/src/world/level_loader.gd            (list_levels, line 61)
-		if f.ends_with(".json"):
+		if f.ends_with(".json") and not f.ends_with(".tape.json"):
```
```diff
--- a/tools/reachability.py                (main, line 295)
-        if not name.endswith(".json"):
+        if not name.endswith(".json") or name.endswith(".tape.json"):
```

Measured with both applied: `tools/test.sh` → `129 tests, 8489 assertions, 0
failed`; `tools/validate.sh` → `validate: OK`; `tools/itest.sh` → `290 checks,
ALL PASSED, 5 skipped`.

This is not specific to my fixture. The prover will write five more tapes and
break these three things five more times. **It should land before any other
M1 branch merges.**

I would also add `levels/*.tape.json` to every `exclude_filter` in
`export_presets.cfg` so proof tapes never ship — but that file is not mine, and
I cannot run `tools/smoke_build.sh` to prove the export is still clean (see
*What I could not verify*).

---

## 1. `tools/itest.sh` is headless

`tools/itest.sh` now runs `--headless` with no `--rendering-driver` and no
`--resolution`. The hard timeout is unchanged (`ITEST_TIMEOUT`, default 240 s,
SIGKILL then exit 124). It gained a `"$@"` passthrough so flags reach the suite.

Measured on the unmodified suite, before I added anything:

```
integration: 273 checks, ALL PASSED     exit 0, no window, 58 s wall clock
```

That is the 273 from ADR 005, reproduced. `CLAUDE.md:29` now says
`(headless; hard-bounded)` instead of `(needs a display; hard-bounded)`. That
one line is my only CLAUDE.md edit.

Two new flags, for authoring tapes:

- `tools/itest.sh --only=<substring>` — run only matching cases (~3 s)
- `tools/itest.sh --trace=1` — print the tape's progress step by step

## 2. The tape replay harness

**`tests/integration/replay_tape.gd`** — loads and *refuses* a tape. Refusing is
the point, so every disagreement is an error and none is a warning. A tape is
refused when:

- `source_sha` ≠ `sha256(levels/<id>.json)` → **`STALE TAPE`**, with both hashes
  and the `tools/prove.sh <id>` command to fix it
- `source_sha` is absent, or `level` names a different level
- `fps` ≠ `Engine.physics_ticks_per_second`
- `hops` is empty, a hop has no frames, a step holds for `n < 1`
- an `a` token is not one of `left right up down jump attack`
- the first hop does not start at `spawn` — a tape proves the level can be
  played *through*, not that a shortcut exists
- the tape is over 10 800 frames (3 minutes) — that is a runaway, not a proof

**`tests/integration/tape_replay.gd`** — boots the real `Level` through
`Game.goto_level`, feeds the tape in through `Input.action_press` so it arrives
via the real `InputState.poll()`, and asserts one thing: `Game.level_completed`
fires for that level. Plus `SaveManager.get_flag(id)` and `Game.state == HUB`.

A failure prints the outcome, not the mechanism:

```
FAIL t_replay_test_arena :: tape did not finish the level — hop 0 (spawn -> exit
as human) step 0 | 30 sim frames | ended at tile (5, 11) | goal tile (22, 11) |
closest 267.2 px | health 5
```

`closest … px` mirrors the closest-approach number ADR 005 asks the prover to
report, so a prover failure and a replay failure read alike.

## 3. Fixture tape — `levels/test_arena.tape.json`

Hand-authored against the real physics, iterating on the trace output. One hop,
`spawn → exit` as human, 224 frames:

| held | frames | what it does |
|------|--------|--------------|
| `right` | 44 | accelerate to 108 px/s |
| `right+jump` | 6 | cut jump **over the walker** (a straight run takes a hit here) |
| `right` | 74 | run to the crate |
| `right+jump` | 6 | cut jump **onto the crate** at tile 18 |
| `right` | 18 | land on it |
| `right+jump` | 40 | full jump **over both spike tiles** (20, 21) |
| `right` | 12 | land at tile 23, against the wall |
| `left` | 24 | walk back into the totem |

It finishes at sim frame **207 of 224, with 5/5 health** — it does not tank the
spikes, it clears them. Margins were read off the trace, not modelled: the
descent passes `y=145` while `x=368`, i.e. 31 px of clearance over the spike
row, rather than the ~3 px a tighter line would have had.

## 4. Per-level replay cases

`run_replays()` enumerates `levels/*.json`, drops `*.tape.json` and any
`topdown` map (the hub), and adds one case per level. No tape ⇒ skip with the
command that makes it:

```
SKIP t_replay_jungle_1: no proof tape at levels/jungle_1.tape.json — run tools/prove.sh jungle_1
```

Skips are counted and printed separately from passes, so a silent skip cannot
read as a pass.

## 5. Tests of the gate itself

A stale-tape rule nobody has watched fire is a comment. Three cases bend the
committed fixture one field at a time and insist on a refusal — wrong sha,
missing sha, wrong level, wrong fps, no hops, non-`spawn` start, unknown button,
`n = 0`. A fourth re-cuts the single-hop fixture into three hops at step
boundaries and insists the level still finishes, which is the only thing that
proves hop concatenation works.

I also proved the gate goes red end to end, by breaking the committed tape:

| tape state | result |
|------------|--------|
| correct | `290 checks, ALL PASSED, 5 skipped` |
| `source_sha` zeroed | `280 passed, 6 FAILED` — `STALE TAPE: …` |
| valid sha, buttons that stop at tile 5 | `284 passed, 2 FAILED` — `closest 267.2 px` |

---

## Verify it

```sh
tools/import.sh                  # a fresh worktree has no .godot class cache
tools/itest.sh                   # -> integration: 290 checks, ALL PASSED, 5 skipped
tools/itest.sh --only=t_replay_test_arena --trace=1   # ~3 s, prints the trajectory

# the gate really is a gate:
python3 -c "import json;d=json.load(open('levels/test_arena.tape.json'));d['source_sha']='0'*64;json.dump(d,open('levels/test_arena.tape.json','w'),indent=1)"
tools/itest.sh | grep FAIL       # -> STALE TAPE: ...
git checkout levels/test_arena.tape.json
```

Gate status as committed:

| gate | result |
|------|--------|
| `tools/itest.sh` | **green** — 290 checks, 5 skips |
| `tools/test.sh` | **red, 1 failure** — blocker above, not my code |
| `tools/validate.sh` | **red, 1 problem** — blocker above, not my code |

Both reds are the same root cause and clear completely with the two-line patch
in the blocker section, which I ran and measured before reverting.

---

## What I could NOT verify

- **`tools/smoke_build.sh` — not run, not changed.** It needs an exported binary
  under `build/`, and `build/` is off limits (live Apple credentials). I own the
  file but changing a gate I cannot execute is worse than leaving it, so it is
  untouched. It would not have caught the shipping bug above anyway: it greps
  startup output for `ERROR`, and a locked door logs nothing.
- **Tapes shipping inside the `.pck`.** I read `export_presets.cfg` and found no
  filter that excludes `levels/`, so I believe they ship — but I did not export
  a build and confirm it.
- **The replay against any real level.** All five jungle cases skip; the prover
  does not exist yet. The harness has only ever been shown to finish
  `test_arena`. If the prover's tapes disagree with my reading of the format,
  that will surface as a `t_replay_jungle_*` failure, not silently.
- **`--only` and `--trace` under an old windowed run.** Never tested with a
  display; `itest.sh` is headless-only now.
- **Screenshot.** Definition of done item 4 asks for one in `shots/`. This
  change renders nothing — it is a test harness — and `shots/` is not mine.
- **`CHANGELOG.md`.** Not in my ownership, and eight agents editing it is a
  guaranteed conflict. Suggested entry:
  > - `tools/itest.sh` runs `--headless`; the integration tier gained a proof-tape
  >   replay (ADR 005 §3) with a per-level case that skips until a tape exists,
  >   and a hand-authored fixture tape for `test_arena`.

## Assumptions I made about other agents' work

1. **`source_sha` is `sha256` of the level file's raw bytes, lowercase hex** —
   identical to `shasum -a 256 levels/<id>.json`, computed with
   `FileAccess.get_sha256()`. ADR 005 says "sha256 of the level json" without
   fixing whether that is the bytes or a canonicalised re-serialisation. If the
   prover normalises the JSON first, **every tape will be rejected as stale**.
   This is the single most likely way our two halves fail to meet.
2. **A tape's frames are *simulation* frames, not wall-clock frames.** The
   replay holds the current buttons and spends **no** tape frame while
   `Game.sim_paused` is true, because the player does not read input on those
   ticks. Screen flips freeze the sim for `SLIDE_TIME`, so if the prover instead
   counts every real tick, tapes will desync by the width of each screen
   transition. The prover steps physics directly and has no flips, so I believe
   simulation frames is what it will naturally emit — but this is an assumption.
3. **The tape starts at the level's own spawn**, and the replay concatenates
   hops with no state applied between them. The prover seeds each hop at its
   waypoint; the replay does not, because the real level gets there by playing.
   A tape whose hop *N+1* does not continue from where hop *N* left off will
   fail here even though the prover proved every hop.
4. **`a` uses the six tokens in ADR 005** (`left right up down jump attack`),
   `+`-joined, with `""` or `"none"` for an empty frame. Anything else is
   refused by name so the mismatch is obvious.
5. **Waypoint ids are free text to the replay.** It records `from`/`to`/`form`
   for diagnostics only and never resolves them, so markers added by the DSL
   agent need no coordination with me. The one exception is hop 0, which must
   be `"spawn"`.
6. **The boss gate (ADR 005 §4) is not mine and is not here.** `t_replay_*`
   would happily replay a strategy tape if one appeared at
   `levels/<id>.tape.json`, but nothing checks defeat time, remaining hearts or
   dodge windows.
7. **`tools/prove.sh` writes exactly one tape per level id.** There is no
   convention here for a second tape (e.g. a boss strategy tape) beside the
   route tape; if one is needed, we need to agree a filename.

## Local, uncommitted change

`tools/env.sh` is gitignored and `tools/bootstrap.sh` hardcodes `PROJECT_ROOT`
to the main checkout, so in a worktree every script runs against the **wrong
repo**. I repointed it at this worktree. Anyone picking this branch up in a
fresh worktree must do the same.
