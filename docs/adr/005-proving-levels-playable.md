# ADR 005 — Proving a level playable, instead of modelling it

**Status:** accepted
**Supersedes:** the evidentiary role of `tools/reachability.py` (which survives
as a fast pre-filter, never as proof).

## Context

Five shipped levels produced six defects that made a level impossible to
finish. Every one was found by a human on a phone; none by the suite. The cause
was constant: `tools/reachability.py` models movement with a hand-derived jump
envelope, and the model is more generous than the game. Measured: the frog's
real apex is **5.34 tiles**; the model says 5.16. One defect turned on ~6 px.

Two measurements change what is possible:

1. The shipping movement code runs **headless with no display**. `FormBase` is
   `RefCounted`, `TileCollision` is static and pure, `Actor` never needs a tree.
   A one-node scene under `--headless` has autoloads — which `--script` does
   not, and the form scripts reference `AudioManager`.
2. The **whole integration suite** runs headless too: 273 checks, exit 0, no
   window.

A third measurement bounds the design: a blind whole-level search is **not
tractable**. Greedy best-first solved `jungle_2` in 8,461 expansions (1.8 s) but
failed `jungle_1` and `jungle_4` at 400,000 expansions, stalling in local
minima and never discovering the transform pads.

## Decision

A level is playable when a machine has **played it**, twice, two ways.

### 1. The route, declared by the author

Levels declare their intended solution in the DSL, beside the geometry:

```python
g.route("spawn",     "pad_frog", form="human")
g.route("pad_frog",  "shaft_top", form="frog")
g.route("shaft_top", "exit",      form="bird")
```

`Grid.route(from_id, to_id, form=...)` appends to a `route` array. Waypoint ids
are either an entity type present in the level (`exit`, `pad_frog`, `key_cyan`),
the literal `spawn`, or a named marker placed with `g.mark("shaft_top", x, y)`.
Serialised into `levels/<id>.json` as:

```json
"route": [{"from": "spawn", "to": "pad_frog", "form": "human"}, ...]
```

A level with no `route` **fails the gate**. Silence is not a pass.

### 2. The prover

`tools/prove.sh [level-id ...]` runs `tools/solver/prove.tscn` headless.

Per hop: seed the real `Actor` at the `from` waypoint with the declared form,
search over the real `form.update()` + `actor.step_motion()` loop, goal is the
`to` waypoint. Action set is the 18 combinations of
{left, none, right} × {jump, no jump} × {none, up, down}, plus attack when the
form can, each held for a 4-frame macro. Frontier is best-first on manhattan
distance. Between hops the prover applies entity effects: `pad_*` changes form,
`key_*` sets a flag, `door_*` requires its flag, `switch_a/b` flips tile
solidity.

Exit codes: `0` all hops proved, `1` a hop failed, `2` a level declared no
route. A failure names the hop, the closest approach in pixels, and the
expansions spent.

On success it writes `levels/<id>.tape.json`:

```json
{"level": "jungle_4", "fps": 60, "source_sha": "<sha256 of the level json>",
 "hops": [{"from": "spawn", "to": "pad_frog", "form": "human",
           "frames": [{"n": 12, "a": "right"}, {"n": 4, "a": "right+jump"}]}]}
```

`a` is a `+`-joined subset of `left right up down jump attack`; `n` is how many
consecutive frames hold it. `source_sha` makes a tape stale the instant the
level changes — a stale tape **fails**, it does not warn. That rule exists
because a stale iOS `.pck` once shipped a fix that was not in the build.

### 3. The replay

The integration tier gains a case per level: boot the real `Level`, feed the
tape through `InputState`, assert the level reports complete. The prover proves
the *geometry* is traversable; the replay proves the *real level* — enemies
alive, doors shut, triggers armed, the screen flip freezing the sim — can be
finished. `tools/itest.sh` runs `--headless`.

### 4. The boss gate

A fight is not a traversal problem. Per boss:

1. **defeatable** — a strategy tape kills it inside a time bound
2. **survivable** — that tape wins from full health with ≥1 heart left
3. **fair** — for every attack, in every phase, sweep the player across every
   standable tile in the arena and assert ≥1 tile where the attack does not
   connect
4. **no softlock** — the prover runs over the arena in each phase config, and
   the boss stays inside `arena_min`/`arena_max`
5. **it ends** — `boss_exit` is reachable from the arena floor after defeat

Check 3 is the one that catches a boss beatable only by taking unavoidable
damage.

## Consequences

- **Definition of done gains two items**: the level declares a route that
  `tools/prove.sh` completes, and its tape replays in `tools/itest.sh`.
- Authoring cost rises: a level is not done when it looks right.
- `tools/reachability.py` keeps running because it costs milliseconds and
  catches gross errors before the expensive prover starts. **Its verdict is
  never again quoted as evidence that a level is playable.**
- The gate proves a route exists and a tape finishes the level. It does **not**
  prove the level is fun or fair to a human taking damage. Human playtesting
  stays in the loop — the intent is that it starts finding design problems
  instead of impossibilities.

## Addendum — the search heuristic, and four things that did not work

The frontier is ordered by manhattan distance to the waypoint. That is a bad
guide in a platformer: a gap between two ledges drops you *level with the
target*, which scores better than the jump that crosses it, so the search dives
into the hole. Measured on jungle_1, crossing one three-tile gap cost **44,421
of a 50,000 expansion budget**, and the closest approach was recorded in mid-air
over the pit, ten tiles short, on the goal's own row.

Four replacements were built and measured. **All four were reverted**, and the
numbers are here so the next person does not repeat them:

| Attempt | jungle_3 | jungle_4 | Verdict |
|---|---|---|---|
| baseline, manhattan | 180 | 875 | all six levels prove |
| charge "below the goal" 3× | — | — | jungle_2 1,357 → 4,713. Worse. |
| order by a tile distance field | 4,830 | — | 27× worse; broke jungle_1 hop 1 |
| …with sub-tile interpolation | 1,374 | — | still 7× worse |
| …as a *filter* instead of a metric | 180 | 875 | free — but pruned the jump **across** a pit as if it were a dive **into** one, because an airborne body was judged by whatever lay directly beneath it. Broke jungle_1 and jungle_2. |
| …scoring an airborne body by where it could land | 1,645 | timeout | still 9× worse |
| manhattan + 0.6 × terrain surplus | 198 | 1,050 | at baseline on both — then broke jungle_1 hop 3, which costs 8 expansions today |

The pattern is consistent: every variant fixed one level and broke another. The
tile field is a **model**, and a model that is nearly right is exactly what
produced the six historical defects. It is not accurate enough to steer the
search, and it was not made accurate enough in the time spent on it.

What stands instead:

- **Manhattan stays.** It proves all six levels.
- **A hop that needs a big budget is a hop that is too coarse.** That was already
  the rule; jungle_1's crossing is now its own hop and still costs 44k, so the
  rule has a limit and this is where it sits.
- **This is the top open problem for M2 onwards.** Twenty more levels will meet
  it. The most promising untried direction is to stop treating the search as
  single-shot: run the cheap manhattan search first, and only if it exhausts its
  budget rerun that one hop with terrain weighting. Then the slow, less reliable
  guide is paid for only where the fast one has already demonstrably failed,
  which is the one arrangement none of the four attempts tried.

## Addendum — what the proof does not cover: pickups (`tools/pickupgate.sh`)

A PROVED level is one whose EXIT the tape reaches. Three TestFlight reports in
one build (deeps_2 twice, deeps_4) were about everything else: a heart in plain
view that a player had already lost the means to reach, and a way on that only
the search had found. None of them could fail this gate, because none of them
was on the route.

`tools/pickupgate.sh` asks the other question with the same physics. For each
heart, key and transform pad it replays the level's tape, takes a seed at every
hop start and every 20 frames along it, and searches from the nearest seeds
(`PickupReach`, tools/pickupgate/reach.gd) until the body TOUCHES the trigger
box, which is what `Pickup` and `TransformPad` check. It also does the two
things this ADR's prover will not: it presses attack, carrying broken tiles and
`break_progress` in the state (so a shoulder-break is real and is undone by
restore), and it models the blade's out-leg with the blade's own numbers on a
real Actor.

How far to trust it, measured:
- **REACHED** is a replayed tape from a route state. Same limits as the prover:
  no enemies, hazards avoided unless `--allow-hazard`.
- **NOT FOUND** is a lead, not a verdict. The frontier is greedy manhattan, and
  it inherits the weakness the addendum above describes: from a hop start one
  tile left of the ruins_3 kelp vine it spent 8,000 expansions without the
  heart two tiles off that vine, and found it in 8 from a state on the vine.
  Seeding along the whole tape fixed that case; it does not fix the class.
  `--probe` searches tile to tile, which is how every NOT FOUND in the first
  audit was settled, leg by leg, before anything was changed.
- Exhausting even a 5x2 room costs 8,000-14,000 expansions (75-170 s), so no
  NOT FOUND in a real level is ever an exhausted frontier.
