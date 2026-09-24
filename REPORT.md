# wave2/proverfix — the prover's two proof-correctness defects

> This file replaces a leftover `REPORT.md` from wave 1's hub agent ("M6 — the
> 25-door hub", 299 lines) that is still committed on this branch even though
> `9c61796` dropped one from the integration branch. Recover it with
> `git show 2d48d72:REPORT.md` if anyone still needs it.

Branch `wave2/proverfix`. Both defects are fixed and verified against the real
booted game. One integration case is still red on purpose and one was already
red for a reason that is now pinned down; both are in files I do not own and both
are handed over below with the exact change they need.

---

## Defect 1 — jungle_3's last hop did not reproduce

### What was wrong

`tools/prove.sh jungle_3` failed its own self-check:

```
hop 8/8 pad_human > exit replayed to (743,164), but the search left it at (727,105)
```

It was not `snapshot()`/`restore()`. It was the **join between hops**.

A tape is one continuous stream of button presses. The first frame of hop N+1
follows the last frame of hop N with no gap for a thumb to lift in. But
`ProverSearch.run()` rooted every hop's search tree at a node whose action was
`0` — *no button held* — so the first macro of every hop derived its press and
release edges against silence. If the previous hop ended holding a button, the
search read a rising edge that a replay of the same tape can never see.

jungle_3 hits it exactly: hop 7 (`bank_foot > pad_human`, as the fish) ends
holding **jump**, and hop 8 begins standing on the transform pad. The search
spent a phantom `jump_pressed` on a real jump; on replay the button was already
down, `jump_buffer` was never filled, `can_jump_now()` was false, and Kaya stayed
put. Everything after that frame was a different run.

This was found with `tools/diverge.sh`'s sibling instrument, a new
`tools/prove.sh --diff-hops`, which prints the state on both sides of every hop
boundary. It named the cause in one line: at hop 8's boundary every piece of
simulation state was identical and `prev_action=16` (JUMP).

### The fix

- `ProverSearch.run(sim, start, goals, budget, held)` — the root node's action is
  now the bitmask the controller was holding on the frame before the hop begins.
- `prove.gd` carries `held` across hops: `held = res.actions[-1]` after each hop.

**Do not** confuse this with loosening anything: the self-check was correct and
was made stricter, not weaker (below).

### Three things tightened while I was in here

1. **`restore()` now restores everything.** `Actor.last_floor_tile` and
   `last_wall_tile` were never in the snapshot. Nothing in the movement path
   reads them today — which is precisely the argument that was wrong the last two
   times — so they are packed into one int and restored.
   (`ProverSim._tile_bits()` / `_set_tile_bits()`.)
2. **The self-check compares the outcome, not the position.**
   `ProverSim.replay_signature()` is compared at every hop end: position,
   velocity, form, on_floor, climbing, key counts, pickups taken, doors opened,
   switch states. Position alone passes a tape that lands on the right pixel with
   the wrong velocity, or that arrives without having picked the key up.
3. **A self-check that does not finish is not one that passed.** While developing
   this I hit a type error inside the self-check loop; it aborted halfway and the
   level printed `PROVED`, because "returned no error string" was read as
   "checked every hop". `_selfcheck()` now returns `{error, checked}` and
   `_prove_level()` fails unless `checked == hops`.

### Evidence

- `tools/prove.sh` — all six levels come out with a tape that passes the
  self-check. jungle_3: `PROVED — 8 hops, 689 frames, 273 expansions`.
- `tools/diverge.sh` — the prover's simulation and the **real booted game** now
  agree frame for frame on every tape:
  ```
  jungle_2  agrees for all 783 frames
  jungle_1  agrees for all 750 frames
  jungle_3  agrees for all 689 frames
  jungle_5  agrees for all 823 frames
  jungle_4  agrees for all 1040 frames
  ```
- `tools/itest.sh` — **`t_replay_jungle_3` now passes** in the real game. It was
  one of the three cases that were red when I started.

---

## Defect 2 — jungle_5's route ended at a waypoint that does not exist

`src/world/level.gd:130` returns `null` for `boss_exit`; `on_boss_defeated()`
places it. So during play the tile is empty, and the prover — which treated it as
ordinary scenery — walked there, found it in its own simulation, and reported a
level it had not finished.

ADR 005 already draws the line: section 2 gives the prover traversal, section 4
gives the boss gate the fight, including check 5, *"it ends — `boss_exit` is
reachable from the arena floor after defeat"*. So the prover now stops at the
arena and says so, loudly, in three places.

### What `tools/prove.sh jungle_5` prints now

```
  note   jungle_5: the route ends at 'boss_exit'. Proving traversal to 'arena_floor' only;
         the last 1 hop(s) are the boss gate's, not the prover's.
  hop 1/6  spawn > vine_foot ... hop 6/6  ledge_b > arena_floor
PARTIAL jungle_5 — 6 hops, 823 frames (13.7s of play), 8925 expansions, 55281 ms -> jungle_5.tape.json
       NOT a full proof: traversal is proved to 'arena_floor'; 1 hop(s) to 'boss_exit'
       are the boss gate's (ADR 005 section 4). The tape is stamped partial.

prove: 1 level(s) are NOT fully proved. Traversal is proved; the rest is not.
  jungle_5 — proved 6 of 7 hops, up to 'arena_floor'
      NOT proved: arena_floor > boss_exit
                  'boss_exit' is placed by Level.on_boss_defeated(), so it is not in the world during play
                  owner: the boss gate (ADR 005 section 4, check 5: ...)
```

The verdict word is `PARTIAL`, not `PROVED`. The run ends with a summary of every
partial level. `--verify-tapes` reports a partial tape as `partial`, never `ok`.

### What the tape carries

`proofs/jungle_5.tape.json` gained four top-level fields, so nothing downstream
can read it as a finished level by accident:

```json
"partial": true,
"proves": "traversal",
"ends_at": "arena_floor",
"unproved": [{"from": "arena_floor", "to": "boss_exit",
              "why":   "'boss_exit' is placed by Level.on_boss_defeated(), so it is not in the world during play",
              "owner": "the boss gate (ADR 005 section 4, check 5: boss_exit is reachable from the arena floor after defeat)"}]
```

Read them with `ProverTape.is_partial(path)` and `ProverTape.unproved_hops(path)`.

### Decisions I made, and why

- **A partial level exits 0.** The prover has discharged its whole obligation
  when it reaches the arena; a gate that is permanently red is a gate everyone
  learns to ignore. `tools/prove.sh --require-full` turns a partial into exit 1
  for anyone who wants the stricter contract (CI, a release gate).
- **The prover does not search the last hop in its own simulation.** It could:
  `boss_exit` exists as an entity in `ProverSim` from frame zero. That would be
  proving a level the player never sees, which is the modelling mistake ADR 005
  exists to stop. The verdict says the hop was *not* attempted, not that it
  failed.
- **A `boss_exit` with no boss in the level is a hard FAIL**, not a partial:
  `on_boss_defeated()` is what places the gate, so nothing ever will and the
  level cannot be finished by anyone.
- **A route whose *first* hop walks to `boss_exit` is `NOROUTE`**: there would be
  nothing left for the prover to prove.
- **No level file was edited.** The seam works off the existing
  `levels/jungle_5.json` route as authored.

---

## Exactly how to verify all of this

```bash
tools/test.sh          # 226 tests, 19387 assertions, 0 failed
tools/validate.sh      # validate: OK
tools/prove.sh         # 5 PROVED + 1 PARTIAL (jungle_5), exit 0
tools/diverge.sh       # all five tapes agree with the real game, every frame
tools/itest.sh         # 301 passed, 2 FAILED (both below), exit 1

tools/prove.sh jungle_3 --diff-hops   # the instrument that found defect 1
tools/prove.sh --require-full         # exit 1, because jungle_5 is partial
tools/prove.sh --verify-tapes         # jungle_5 reports `partial`, not `ok`
```

Timings on this machine, single-threaded, with four other agents sharing it:
jungle_1 334 s (hop 5 alone is 36,619 expansions), jungle_5 55 s, jungle_2 9 s,
jungle_4 8 s, jungle_3 1.6 s, test_arena 0.4 s. `tools/test.sh` ~9 min, most of
it `test_prover_fixtures.gd`'s twelve child processes.

---

## What is still red, and whose it is

`tools/itest.sh` — **301 passed, 2 failed.** Three were red when I started; one
of them (`t_replay_jungle_3`) is now green.

### 1. `t_replay_jungle_5` — red on purpose, needs the integration tier to learn about `partial`

```
FAIL t_replay_jungle_5 :: tape did not finish the level —
     hop 5 (ledge_b -> arena_floor as human) step 8 | 823 sim frames |
     ended at tile (38, 26) | goal tile (46, 26) | closest 135.2 px
```

That is the correct outcome and an honest message: the tape ends on the arena
floor, tile (38, 26), which is exactly where the prover says it stops. The case
asserts `completed` for every level with a tape, and jungle_5's tape no longer
claims to complete one.

**I did not change it: `tests/integration/**` is not mine.** What it needs, in
`integration_tests.gd::run_replays()`:

```gdscript
if ProverTape.is_partial(TAPE.tape_path(id)):
    # or read d["partial"] in replay_tape.gd and expose it on the loaded tape
    check(not bool(r["completed"]), "%s's tape is partial and must not complete it" % id)
    check_eq(r["end_tile"], <arena_floor tile>, "it reaches the arena floor")
    check(level().boss != null and not level().boss.defeated, "and the boss is still alive")
    continue
```

The rest of jungle_5 — the fight and the gate opening — is ADR 005 §4's, and
`tests/integration/boss_gate_*.gd` already exists to hold it. My added tape
fields are additive: `replay_tape.gd` ignores unknown top-level keys, so the
partial tape loads and replays today without any change to that file.

### 2. `t_the_replay_plays_a_tape_split_across_several_hops` — pre-existing, now diagnosed

```
FAIL :: three hops play as one continuous run — hop 2 (mid_b -> exit as human)
        step 4 | 181 sim frames | ended at tile (19, 10) | goal tile (22, 11)
```

**Not caused by anything I did, and not a replay-continuity bug.** The fixture
re-cuts `test_arena`'s tape into three hops with:

```gdscript
var frames: Array = ((d["hops"] as Array)[0] as Dictionary)["frames"]
```

It takes **hop 0 only**. `test_arena`'s tape has two hops — `spawn > spike_lip`
(181 frames) and `spike_lip > exit` (38 frames) — so the re-cut tape is the first
181 frames with the last 38 thrown away, and the level cannot complete. That
matches the failure exactly: 181 sim frames, stopped 56.7 px short of the exit.
It was written when `test_arena`'s tape was a single hop.

`proofs/test_arena.tape.json` is byte-identical before and after my change
(`git diff` touches only `jungle_3` and `jungle_5`), so this failure predates me.
The fix is one line in a file I do not own — flatten every hop's steps:

```gdscript
var frames: Array = []
for h: Dictionary in (d["hops"] as Array):
    frames.append_array(h["frames"] as Array)
```

### Noise I observed but did not touch

`tools/itest.sh`'s log carries two `SCRIPT ERROR`s that fail no check and are in
files I do not own — `integration_tests.gd:378` (`invuln` on a Nil player in
`t_spikes_hurt_and_knock_back`) and `boomerang_blade.gd:8` (`filter` lambda
argument conversion). Both are pre-existing. Flagging, not fixing.

---

## What I could NOT verify

- **That `boss_exit` is reachable from the arena floor after the boss dies.**
  That is the point of the seam — it is ADR 005 §4 check 5, it belongs to the
  boss gate, and nothing on this branch tests it. `tools/prove.sh` now says so
  in the verdict instead of implying otherwise.
- **That a tape survives contact with enemies.** Unchanged and still true:
  `tape_replay.gd` runs Kaya unhittable, because `player.gd` clears input for
  `hurt_t` and one hit desynchronises a whole tape. The replay proves the buttons
  drive the real level through real doors, pads and screen flips. It does not
  prove survival.
- **That the search finds the *best* route, or that any level is fun or fair.**
  Out of scope, as ADR 005 says.
- **jungle_1 hop 5 costs 36,619 expansions** — within the 50,000 budget, but ADR
  005's own rule says a hop that expensive is a hop that is too coarse. It proves
  today. I did not re-cut it; the route belongs to the levels/routes work, not to
  the prover.
- **`tools/smoke_build.sh` was not run.** Nothing here ships in a build.

---

## Assumptions about other agents' work

1. **`tests/integration/**` is someone else's.** I assume the owner of
   `integration_tests.gd` / `tape_replay.gd` will teach `run_replays()` about
   `"partial"` as sketched above. Until they do, `t_replay_jungle_5` stays red,
   and the message it prints is accurate about why.
2. **`levels/jungle_5.json`'s route is correct as authored** — `arena_floor` is a
   real mark at tile (38, 26) and the last hop to `boss_exit` is deliberate. The
   seam reads that route unchanged. If the routes agent re-cuts jungle_5 so it
   ends at `arena_floor` with no `boss_exit` hop at all, the prover will simply
   print `PROVED` and the partial machinery will go quiet — that is fine, but the
   level would then declare no intent to reach the gate, which I think is worse.
3. **`src/world/level.gd`'s `boss_exit` behaviour stays as it is** — placed only
   by `on_boss_defeated()`. If someone makes the gate exist from the start (as a
   closed door, say), the seam should be deleted, not kept.
4. **`data/forms/*.json` tuning is stable.** `tests/test_prover_snapshot.gd`
   avoids hard-coded frame counts where it can (it loops until the body lands
   rather than guessing the arc length), but two of its rooms are sized against
   the human's 2.78-tile apex.
5. **Nobody else regenerates `proofs/*.tape.json` from an older prover.** The
   tapes on this branch were written by the fixed prover; `jungle_3.tape.json`
   and `jungle_5.tape.json` changed, the other four are byte-identical.

---

## Files changed

Mine, as assigned:

| File | Change |
|---|---|
| `tools/solver/search.gd` | `run(..., held)`: the hop's search tree is rooted at the buttons already down |
| `tools/solver/prove.gd` | carries `held` across hops; the boss seam (`_boss_seam`); `PARTIAL` verdict + run summary; `_signature_diff`; `_selfcheck` returns `{error, checked}`; `--diff-hops`, `--require-full` |
| `tools/solver/sim.gd` | `_tile_bits`/`_set_tile_bits` in snapshot/restore; `replay_signature()`; `describe_state()`; `boss_count`; `waypoint_is_boss_gate()` |
| `tools/solver/tape.gd` | `write(..., extra)`; `is_partial()`; `unproved_hops()` |
| `tools/prove.sh` | header documents the two verdicts and the new flags |
| `tests/test_prover_snapshot.gd` | **new**, 9 cases (see below) |

Outside my list, deliberately, and each is the prover's own output rather than
another agent's source:

| File | Why |
|---|---|
| `proofs/jungle_3.tape.json`, `proofs/jungle_5.tape.json` | regenerated by the fixed prover; this is what `tools/prove.sh` writes. The other four tapes are unchanged, byte for byte. |
| `shots/70..72_proverfix_*.png` | the definition of done asks for a screenshot (see the caveat below) |
| `REPORT.md` | this file; it overwrote wave 1's leftover hub report, see the note at the top |
| `CHANGELOG.md` | the definition of done asks for an entry. Appended at the end only, to keep the conflict surface with the other four agents to one hunk. |

I did not touch `tests/integration/**`, `src/**`, `data/**`, `levels/**`,
`tools/build_levels.py`, `tools/gen_levels.py` or `build/`.

### About the screenshots

They are **scene-setting, not proof**, and I would rather say that than let a
picture carry weight it has not earned:

- `shots/70_proverfix_jungle3_vine_foot.png` — where hop 8 begins, the
  `pad_human` at the foot of the vine in column 45.
- `shots/71_proverfix_jungle3_vine_top_exit.png` — where it ends: the top of the
  vine, the cyan door and the exit.
- `shots/72_proverfix_jungle5_arena_floor.png` — the arena floor with the Grove
  Warden alive and **no gate anywhere on screen**, which is defect 2 in one
  frame.

The fix is to a verification tool and renders nothing of its own. The real
evidence is `tools/diverge.sh` agreeing with the booted game for every frame of
every tape, and `t_replay_jungle_3` going green.

Reproduce the shots with `tools/shot.sh --seq=<file>` on:

```json
[
 {"scenario": "level:jungle_3", "settle": 60},
 {"teleport": [45, 19], "settle": 200},
 {"shot": "shots/70_proverfix_jungle3_vine_foot.png"},
 {"scenario": "level:jungle_3", "settle": 60},
 {"teleport": [41, 7], "settle": 200},
 {"shot": "shots/71_proverfix_jungle3_vine_top_exit.png"},
 {"scenario": "level:jungle_5", "settle": 60},
 {"teleport": [38, 26], "settle": 200},
 {"shot": "shots/72_proverfix_jungle5_arena_floor.png"}
]
```

---

## `tests/test_prover_snapshot.gd`

Nine cases, and none of them inspects a field to see whether somebody remembered
to copy it — that is the mechanism, and checking the mechanism is what shipped
six broken levels. Each takes a running simulation, saves it, disturbs it as far
as it can, restores it, and asks the **simulation** whether the future it
produces is the same one.

- `test_restore_reproduces_a_running_jump_frame_for_frame`
- `test_restore_does_not_leave_phantom_coyote_time_behind` — the original bug's
  exact shape
- `test_restore_reproduces_a_vine_climb`
- `test_restore_puts_a_transform_pad_and_its_cooldown_back`
- `test_a_snapshot_restores_the_same_way_from_any_other_state` — the search
  restores siblings in any order, so round-tripping against its own past is not
  enough
- `test_a_hop_that_begins_with_jump_already_held_reproduces` — defect 1
- `test_jump_held_across_a_join_cannot_buy_a_fresh_jump` — the edge rule itself
- `test_every_variable_actor_declares_is_classified` — a new `Actor` variable
  fails this until somebody decides whether a tick can write it
- `test_the_form_snapshot_sees_the_timers_that_caused_the_original_bug`

One note on the sixth, because it nearly shipped as a test that proved nothing.
My first draft ran the hop in a plain room with a step in it, and it **passed
either way** — rooted at `held` and rooted at `0`. Measured: both tapes end at
(169, 74), because a wrong first macro costs a few pixels and the next jump lands
on the same platform anyway. The difference has to be kept from washing out, so
the room now has a transform pad under the step: a phantom jump changes whether
the body crosses the pad, and a frog is not a human. Rooted at `held` the tape
reproduces; rooted at `0` the search ends at (166, 85) and its own tape replays
to (194, 74). The test asserts **both** halves, so if the room ever stops
discriminating it says so rather than passing quietly.
