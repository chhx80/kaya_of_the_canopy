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
