# Plan: twenty more levels, all of them provably playable

Status: proposed, 2026-09-16. Supersedes nothing; extends ADR 002 (level
format) and ADR 003 (two test tiers).

## The problem this plan has to solve

There are five playable levels today. Between them they have shipped **six
defects that made a level impossible to finish**, every one found by a human
playing on a phone and none by the test suite:

| # | Defect | What the checker believed |
|---|--------|---------------------------|
| 1 | Vine with no exit at the top | reachable — via a blind mid-air jump |
| 2 | One-way platform with one tile of headroom | not "solid", so exempt from the pocket check |
| 3 | Door one tile tall, player 22 px | the door opened, so the tile was clear |
| 4 | Fish could not hop the 16 px bank | hop height never compared to the bank |
| 5 | Frog sealed behind a 20-tile wall | jumps only checked the destination |
| 6 | Shaft capped across its full width | vertical moves were never checked at all |

The pattern is constant: `tools/reachability.py` models movement with a
hand-derived jump envelope, and the model is more generous than the game. It is
measurably wrong — the frog's real apex is **5.34 tiles**, the model says 5.16,
and defect 6 turned on roughly six pixels.

Five levels have needed six rounds of human playtesting to become finishable.
Twenty more at that rate is not a plan, it is a treadmill. **So the first
deliverable is not a level. It is a gate that makes "playable" a fact.**

## Phase 0 — the Route Prover

Replace the model with the game. Instead of asking "does my envelope say this
is reachable", execute the shipping movement code and see whether it arrives.

Three things were measured today to check this is real, not hopeful:

**1. The shipping physics runs headless, with no display.**
`FormBase` is `RefCounted` and `TileCollision` is static and pure; `Actor` is a
`Node2D` that never needs to be in a tree. Booting a one-node scene with
`--headless` gives autoloads (`AudioManager`, which the form scripts reference,
so `--script` mode cannot work) and the real `form.update()` +
`actor.step_motion()` loop at full speed. A frog jump measured **5.34 tiles** —
the true number, not the modelled one.

**2. It is fast enough.** ~4,500 four-frame macro-steps per second, ~18,000
physics ticks per second, single-threaded.

**3. A blind whole-level search is NOT tractable.** Greedy best-first from
spawn to exit:

```
jungle_2   SOLVED    8,461 expansions,  1.8 s
jungle_1   no route  400,000 expansions, 89 s   (needs the vine, and stalls in a local minimum)
jungle_4   no route  400,000 expansions, 86 s   (needs the frog pad; search never gets there)
```

That result shapes the design and is the reason this phase exists at all. The
prover must not search blind. It searches **hop by hop along a declared route**:

```python
g.route("spawn", "pad_frog", form="human")
g.route("pad_frog", "shaft_top", form="frog")
g.route("shaft_top", "key_cyan", form="frog")
g.route("key_cyan", "door_cyan", form="frog")
g.route("door_cyan", "exit",     form="bird")
```

Each hop is short, so each is seconds — jungle_2 fell to a *whole-level* greedy
search in 1.8 s, and a hop is a fraction of that. The route is written by the
author in the DSL, next to the geometry it describes, which means:

- it is a machine-checkable statement of the intended solution
- it doubles as design documentation for what the level is *about*
- it produces an **input tape** — the literal button presses that finish the
  level — which the in-engine tier can replay

### What the prover does

1. Loads the level exactly as the game does (`LevelLoader`).
2. For each hop: instantiates the real form, seeds the real `Actor` at the
   previous waypoint, and searches over the full action set (left / right / up /
   down / jump / attack, held in four-frame macros) with a distance heuristic.
3. Applies entity effects between hops — a `pad_*` changes form, a `key_*` sets
   a flag, a `door_*` requires it, `switch_a/b` flips tile solidity.
4. Fails loudly with the hop that could not be completed and the closest it got.
5. Writes `levels/<id>.tape.json` — the proof.

### What replays it

`tools/itest.sh` gains a case per level: boot the real game, feed the tape
through `InputState`, assert the level reports complete. The pure tier proves
the *geometry* is traversable; the replay proves the *real level*, with enemies
alive, doors closed, triggers armed and the screen-flip freezing the sim, can
actually be finished.

### What happens to `tools/reachability.py`

Demoted, not deleted. It runs in milliseconds and catches gross errors (an exit
walled off, a spawn in rock) before the expensive prover starts. It stops being
evidence. Its verdict is never quoted as proof again.

### Honest limits of the gate

The prover proves a route **exists** and a tape **completes the level**. It does
not prove the level is fun, fair, or beatable while taking damage — the tape may
walk through an enemy the prover ignored. Human playtesting stays in the loop;
the intent is that it starts finding *design* problems instead of
impossibilities.

**Exit criterion for Phase 0:** all five existing levels carry a proved route
and a replaying tape, and the six historical defects are re-introduced one at a
time and confirmed to fail the gate.

## Phase 1 — content architecture

### Screen size: decided, 2026-09-16

**400×240, 25×15 tiles per screen. Unchanged.** Asked before authoring began,
because changing it afterwards is a re-author of 25 levels instead of 5. The
deciding argument was not the rework: the side margins are where the touch
controls now live, and widening the world puts them back on top of the
playfield — a bug reported twice already. Levels stay 50×30, two by two.

### Shape

Four new worlds of five levels each = 20. With the existing jungle that is five
worlds, 25 levels.

| World | Theme | Forms it leans on | New verb |
|-------|-------|-------------------|----------|
| 1 | Canopy Trail (exists) | human | — |
| 2 | Sunken Ruins | fish, human | currents; rising water |
| 3 | Thermal Heights | bird, frog | updrafts; bird stamina as a real budget |
| 4 | Termite Deeps | frog, human | darkness with a light radius; breakable walls |
| 5 | The Obsidian Nest | all four | switch-blocks at scale; the final boss |

Each world is 4 levels + 1 boss level, and each opens with a level that teaches
its new verb in a safe room before using it over a hazard.

### Engine work this implies

Deliberately small, because every new mechanic is a new class of bug:

- **Currents** — a tile flag adding a constant velocity. Touches
  `tile_data.gd`, `form_fish.gd`. Cheap.
- **Updrafts** — the same flag with a vertical vector. Free once currents exist.
- **Rising water** — animate the water line over time. Touches `TileWorld`; the
  prover needs a time dimension for these levels, which is the most expensive
  item on this list. *Candidate to cut first.*
- **Darkness** — `Ambience` already does lighting; add a radius around the
  player. Visual only, no collision impact, so the prover is unaffected.
- **Enemies** — four types today (walker, jumper, shooter, swimmer) will not
  carry 25 levels. Add three: a charger, a ceiling-dropper, a patrolling flyer.
- **Bosses** — four new. Each is the existing three-phase machine plus its
  world's verb, not a new system. See *Bosses* below; they are a requirement,
  not a garnish, and they have their own gate.

No moving platforms. They would need dynamic collision against a static-tile
collision model, and that is a rewrite, not a feature.

### The hub

`hub()` is a 50×15 top-down map with five doors, regenerated from a list. It
grows to 50×30 (2×2 screens) holding 25 doors in five clusters, gated
world-by-world on the previous world's boss. No new systems — the same
`hub_door` entity and `requires` chain.

## Bosses

**Every world ends with one.** Five in total: `boss_grove` exists, four are new.
Each reuses the data-driven phase machine in `boss_grove.gd`
(`data/enemies/*.json`, `until_health` thresholds, per-phase poses) and adds
exactly one idea — its world's verb turned against you.

| World | Boss | The fight |
|-------|------|-----------|
| 1 | **The Grove Warden** (exists) | Three phases, spray and slam. |
| 2 | **The Tide Maw** | The arena floods and drains between phases. Flooded, you must be the fish; drained, human. Its pull is a current — you dodge by riding the counter-current, not by running. |
| 3 | **The Stormcrest** | Airborne, fought as the bird. It is only vulnerable while roosting, so the fight is stamina against its roost cycle; updrafts are the only way to regain height. |
| 4 | **The Brood Queen** | The arena is dark. She is visible only when she attacks, or lit by breaking a luminous wall — which also removes the cover you were standing behind. |
| 5 | **The Obsidian Heart** | Final. Switch-blocks reconfigure the arena between phases, each phase demanding a different form from pads that move with the blocks. |

### The Boss Gate

The Route Prover proves traversal. **A boss fight is not a traversal problem**,
so it needs its own gate, and it needs one for the same reason the levels did:
the failure mode is an *unwinnable situation nobody modelled* — the fight
equivalent of a shaft capped across its full width.

Five checks, all run headless:

1. **Defeatable.** The author writes a *strategy tape* alongside the route
   tape — the intended fight. Replayed against the real boss, the boss must
   die within a time bound.
2. **Survivable.** That same replay must win from full health with at least one
   heart left. A tape that only wins at exactly zero health is not a fight, it
   is a coin flip.
3. **Fair — every attack has a dodge window.** For each attack, in each phase,
   sweep the player across every standable tile in the arena and assert at
   least one tile where the attack does not connect. An attack that covers the
   whole arena is unavoidable damage, and this is the check that catches it.
   *This is the check worth building first.*
4. **No softlock.** Run the Route Prover over the arena itself, in each phase
   configuration — this matters most for The Obsidian Heart, whose arena moves.
   The boss must also stay inside `arena_min`/`arena_max`.
5. **It ends.** After defeat, `boss_exit` must be reachable from the arena
   floor — one more proved hop.

Checks 1 and 2 catch a boss that cannot be beaten. Check 3 catches one that
cannot be beaten *fairly*, which is the harder and more common bug. Checks 4
and 5 catch the level around the fight.

### This is now affordable

`tools/itest.sh` was believed to need a display. Measured today, the whole
suite runs under `--headless` — 273 checks, exit 0, no window. The real `Level`
scene, enemies, weapons, triggers and bosses can therefore all be driven in CI
with no display at all. Boss simulation is not a special rig; it is the
integration tier with a longer script. `itest.sh` switching to `--headless` is
an M1 task, and `CLAUDE.md`'s note about needing a display is stale.

## Milestones

Each milestone ends with screenshots and a playable build, as with every
milestone so far.

- **M1 — the gate.** Route Prover, tape replay, `itest.sh` to headless, and the
  Boss Gate's dodge-window sweep run against The Grove Warden. Routes for the
  five existing levels; six historical defects reproduced as failures.
  *No new content.*
- **M2 — World 2, Sunken Ruins.** Currents, 4 levels + **The Tide Maw**, tileset palette.
- **M3 — World 3, Thermal Heights.** Updrafts, 4 levels + **The Stormcrest**.
- **M4 — World 4, Termite Deeps.** Darkness, breakables, 4 levels + **The Brood Queen**.
- **M5 — World 5, The Obsidian Nest.** Switch-blocks, 4 levels + **The Obsidian Heart**.
- **M6 — hub, balance, on-device pass.** 25-door hub, difficulty curve, VRAM and
  frame cost measured on a real iPhone.

M1 is the long pole and produces no visible content. It pays for itself from
roughly level 8 onward, and it is the only reason the answer to "make sure they
can all be played" is a gate rather than a promise.

## Definition of done, extended

`CLAUDE.md` gains two items:

5. The level declares a route, and `tools/prove.sh` completes every hop.
6. The proof tape replays in `tools/itest.sh` and the level reports complete.

## What I would cut under pressure

In order: rising water (forces time into the prover), the three new enemy types
(reuse the four), then level *count* per world — five down to four, or three.

**Never the bosses.** A world without one does not end, it just stops. If a
world has to shrink, it shrinks in ordinary levels and keeps its boss.

I would not cut M1 either; without it the other 20 levels inherit the defect
rate of the first five.
