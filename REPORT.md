# wave2/replayfix — report

> This file replaced the `wave1/hub` agent's report that was still sitting in
> the worktree root. That report is unchanged in history — `git show 2d48d72:REPORT.md`.

Branch `wave2/replayfix`. Files touched: `tests/integration/tape_replay.gd`,
`tests/integration/integration_tests.gd`. Nothing else. No new
`proofs/*.fixture.tape.json` was needed — see FAILURE 1 below, the fixture was
deleted rather than added to.

---

## FAILURE 1 — `t_the_replay_plays_a_tape_split_across_several_hops`: **deleted**

The case re-cut the arena tape into three hops at arbitrary seams and asserted
the level still finished. It had rotted: it re-cut `hops[0]` only, so the day
`proofs/test_arena.tape.json` was re-proved into two hops it silently dropped
the second, ran 181 of 219 frames and ended 56.7 px short of the exit.

Repairing it was easy — flatten every hop's frames before cutting, and add a
`total_frames` guard so the same rot fails with "the re-cut lost frames"
instead of "the level did not finish". I built that repair, watched the guard
fire (`got 181, want 219`), and then went looking for whether the thing the
case tests is tested anywhere else now that six real prover tapes exist with 2
to 16 hops each.

It is, and better. I injected two hop-boundary defects into `tape_replay.gd`
and ran the whole tier against each:

| injected defect | real tapes | the re-cut case |
|---|---|---|
| a one-frame input lull at every hop seam | `jungle_1`, `jungle_4`, `test_arena` all FAIL | **passes** |
| seed each hop at its `from` waypoint, the way the prover does | `jungle_1` dies mid-route, `jungle_4` lands 18.8 px short | **passes** |

Three seams in one 219-frame arena tape is a strictly smaller sample of the
same property than fifty-odd seams across five real levels, and the case's
invented waypoints (`mid_a`, `mid_b`) name nothing, so the seeding regression
skips them entirely. It was weaker than the tapes beside it at the one thing it
existed to check, so I deleted it instead of repairing it, and left the
measurements above in a comment at `tests/integration/integration_tests.gd:255`
so the next person does not re-add it blind.

Both injections were temporary; `tape_replay.gd` is restored (`git diff`
carries neither).

## FAILURE 2 — `t_replay_jungle_5`: now asserts arrival, not completion

`src/world/level.gd:213` places `boss_exit` only inside `on_boss_defeated()`,
so a traversal tape walks to the gate's tile and finds nothing: 8.5 px is as
close as a tape can get to finishing that level. `run_replays()` now branches
on whether the level declares a boss entity, and a boss level goes to
`check_boss_arrival()`, which asserts what the recorded buttons actually
produce:

- Kaya is alive at the end of the tape
- she is on the boss's own screen (`Screen.index_of(...) == boss.home_screen`)
- she is `on_floor`
- she is inside the span `boss_grove.gd` clamps itself to
  (`arena_min .. arena_max + box.x`) — the arena as the boss defines it, not a
  rectangle written in the test
- the boss is still alive, which is *why* the case stops there

and it fails loudly if the tape ever *does* complete a boss level, because that
would mean either the boss became skippable or the tape now fights and this
case must be rewritten rather than left agreeing with something new.

Ordinary levels are untouched: they still require `Game.level_completed`, plus
the save flag and the return to the hub.

**Verified the assertion can fail**, not just pass: truncating
`proofs/jungle_5.tape.json` to its first two hops produced

```
FAIL t_replay_jungle_5 :: and onto the boss's screen — ... ended at tile (20, 9) as human ... (got (0, 0), want (1, 1))
FAIL t_replay_jungle_5 :: inside the span the boss is clamped to (408..792, Kaya at 321)
```

The tape was restored from `git` immediately; `git status` shows `proofs/`
clean.

## Two supporting changes in `tape_replay.gd`

- `_goal_point()` now resolves **the tape's own last waypoint** — an entity
  type, or a named mark read from `levels/<id>.json` — falling back to the exit.
  The old version always measured against `exit`/`boss_exit`, which on a boss
  level is a distance to a place that does not exist. Nothing changes for
  today's five ordinary tapes (their last hop is `-> exit`); it matters the
  moment the prover stops routing jungle_5 at `boss_exit`.
- `describe()` and the `--trace` line now print the form Kaya ended in. That is
  what made the `jungle_3` diagnosis below readable in one line instead of
  thirty.

The unhittable relaxation is unchanged, still narrow (`invuln` is set only on
tape frames, never during the settle window) and still documented in full at the
top of `tape_replay.gd`.

---

## Gates — exactly what I got

```
tools/test.sh       217 tests, 19283 assertions, 0 failed — ALL TESTS PASSED
tools/validate.sh   validate: OK
tools/itest.sh      301 passed, 1 FAILED
tools/prove.sh      5 of 6 PROVED, jungle_3 FAILS
```

**`tools/itest.sh` is not clean, and the one red case is not mine.** It is
`t_replay_jungle_3`, one of the three you listed as already red. My two are
green; the count went 298 → 301 passed, 3 → 1 failed.

**`tools/prove.sh` is not clean either, on the same level.** `jungle_1`,
`jungle_2`, `jungle_4`, `jungle_5` and `test_arena` all PROVED; `jungle_3`
fails its own self-check (see below). Worth recording: the run rewrote every
`proofs/*.tape.json` and `git status` came back **clean** — the tapes it
produced are byte-identical to the committed ones, so the proofs reproduce and
everything I measured above was measured against the tapes the prover actually
writes today.

Also worth recording for the agent on the other side of the boss seam: the
prover still proves `jungle_5`'s last hop, `arena_floor > boss_exit`, in 80
frames / 20 expansions. It has not yet been made honest about that seam, and my
side does not depend on it being — `check_boss_arrival` is about where Kaya
ends, not about what the hop is called.

Reproduce:

```bash
tools/test.sh
tools/validate.sh
ITEST_TIMEOUT=300 tools/itest.sh                       # 301 passed, 1 FAILED (jungle_3)
ITEST_TIMEOUT=300 tools/itest.sh --only=jungle_5       # the boss seam alone
ITEST_TIMEOUT=300 tools/itest.sh --only=jungle_3 --trace=1
tools/prove.sh                                         # ~4 min; jungle_3 FAILs, proofs/ stays clean
```

Note for a fresh worktree: `tools/import.sh` must be run first or every
`class_name` fails to resolve and the suite times out instead of failing.

## What I could NOT verify

- **Whether the boss arrival check still passes once the prover's side of the
  seam lands.** If the other agent re-cuts jungle_5's route to end at
  `arena_floor` instead of `boss_exit`, my assertions hold unchanged (they are
  about where Kaya ends, not about what the last hop is named) and the goal
  readout improves. If they instead make the tape *fight*, `check_boss_arrival`
  will fail on "the tape finished the level" and needs rewriting — deliberately,
  with a message that says so.
- **No screenshot.** This change is test-tier only; nothing renders differently,
  so there is no frame that would prove anything. Definition-of-done item 4 does
  not apply and I am not claiming it.
- **`CHANGELOG.md`** is outside my ownership so I did not edit it. Proposed
  entry is at the bottom of this file.

## Found but not fixed — for whoever owns these

**1. `t_replay_jungle_3` is a prover defect, not a replay defect.** `prove.sh`
now says so itself:

```
FAIL   jungle_3 — the tape does not reproduce the proof
       hop 8/8  pad_human > exit replayed to (743.000000, 164.000000),
       but the search left it at (727.000000, 105.000000)
```

In the running game it is worse than a drift, and the form readout I added is
what shows it. The tape's
hop 7 is recorded `pad_human -> exit as human`, but in the real level Kaya is
still a **fish** for the whole hop, which is why she bobs at x≈690 pressing
human buttons and never climbs. Hop 6 (`bank_foot -> pad_human`) ends at tile
(43, 21); `pad_human` is at tile **(45, 19)**. The prover applies the pad's form
change at the hop boundary by fiat (ADR 005 §2), so it recorded a
transformation the buttons do not produce — the proof is real, the tape is not.
The driver replayed the buttons faithfully. Owner: `tools/solver/**`.

**2. A test in my own file silently swallows its assertions when it errors.**
`t_spikes_hurt_and_knock_back` throws every run:

```
SCRIPT ERROR: Invalid access to property or key 'invuln' on a base object of type 'Nil'.
    at: t_spikes_hurt_and_knock_back (integration_tests.gd:484)
```

`player()` is null there, so `check(player().invuln > 0.0, ...)` never runs —
and a GDScript error mid-test is not counted as a failure, so the suite reports
a pass it did not earn. The same happens at `integration_tests.gd:546`
(`t_two_hits_kill_a_walker_and_award_score`, a `filter` type error inside
`boomerang_blade.gd:8`). Both predate this branch. I left them alone rather than
turn my branch red for something outside my job, but this is the exact shape of
defect this project keeps shipping: a gate that is green because it did not run.

## Assumptions about other agents' work

- The prover keeps writing tapes in the ADR 005 format `replay_tape.gd` already
  parses. I changed no part of the format or its refusals.
- `src/world/level.gd` keeps placing `boss_exit` only on boss death, and
  `boss_grove.gd` keeps exposing `home_screen`, `arena_min`, `arena_max`, `box`
  and `defeated`. `check_boss_arrival` reads all five and would need updating if
  any is renamed.
- `Level` keeps exposing `boss` and `def`. Boss detection itself does not depend
  on that — it reads the level JSON for an entity type starting `boss_` that is
  not `boss_exit`, so a second boss level needs no change here.
- `levels/*.json` keeps `marks` as `{name: {x, y}}` in tile coordinates.
  `_goal_point()` reads it; if it is absent the readout falls back to the exit
  and nothing fails.
- Nobody else edits `tests/integration/tape_replay.gd`,
  `tests/integration/replay_tape.gd` or `tests/integration/integration_tests.gd`.
  `replay_tape.gd` is unchanged on this branch.

## Proposed CHANGELOG entry (not applied — file not mine)

> **The replay tier tells the truth about boss levels.** A traversal tape cannot
> finish `jungle_5`: `boss_exit` is placed when the Warden dies, so the tape
> walks to the gate's tile and finds nothing, 8.5 px short forever. A boss
> level's replay now asserts what its tape records — Kaya carried alive from
> spawn onto the arena floor, inside the span the boss clamps itself to, with
> the fight still ahead — and fails loudly if a tape ever *does* complete one.
> Ordinary levels still have to report themselves complete.
>
> The synthetic "tape re-cut into several hops" case was deleted rather than
> repaired. Two hop-boundary defects injected into the replay driver were caught
> by the real prover tapes and missed by the re-cut case; the measurements are
> in the comment where it used to be.
