# Longer levels: the engine side (branch `long/engine`)

Status: built 2026-11-19 for the pilot in `docs/plan-longer-levels.md`. This is
the reference for the two branches that place checkpoints and author the long
levels (`long/jungle1`, `long/warden`).

## Checkpoints

### Placing one

```json
{"type": "checkpoint", "x": 40, "y": 25}
```

`(x, y)` is the cell Kaya stands in, her feet on the tile below: the
`player_spawn` rule. In the DSL, `g.checkpoint(40, 25)` (same as
`g.ent("checkpoint", 40, 25)`, plus a placement check when the level is
written). The post is two tiles tall: it occupies `(x, y)` and `(x, y-1)`.

A post must stand where a respawn can seat her, because a respawn does no other
check:

- neither `(x, y)` nor `(x, y-1)` is solid (a switch block counts as solid in
  either state) or a hazard, and `y >= 1`;
- something to stand on: `(x, y+1)` solid and not a switch block, or one-way;
  or the cell itself is water or a ladder.

`tools/gen_levels.py` refuses to write a level that breaks this;
`tools/validate.sh` and `tests/test_level_validity.gd` fail on one
(`LevelLoader.checkpoint_problems()`). validate.sh now also rejects any entity
type it does not know.

### Naming one in a route

Several checkpoints are several entities of one type, so a route names them by
index, `checkpoint#0`, `checkpoint#1`, ... in entity order (the prover's own
`type#n` spelling, now also accepted by the DSL and the validity test). With a
single checkpoint, plain `checkpoint`. A checkpoint is a waypoint the body
reaches by touching the post (`Checkpoint.trigger_rect()`: both cells, grown
by 1 px), so a hop ending at one ends where play would light it. A route need
not name its checkpoints at all; `tools/levelstats.sh` finds them on the tape.

### What a death does

Touching a post (edge-triggered: stepping onto it, and again each time she comes
back to it) makes it the active checkpoint and records the world at that
instant. A death with lives left reloads the level and puts that world back:

| kept from the moment the post was touched | reset |
|---|---|
| keys in hand | enemies (back on their spawns, full health) |
| pickups already taken (gems, hearts, keys) stay gone | hearts: refilled to full, as every restart does |
| doors already opened | form timers, bird stamina |
| every lever, and both switch groups | enemy drops not yet picked up |
| every broken block | a boss not yet beaten |
| a boss already beaten, and its gate | |
| Kaya's **form** and facing | |

She respawns on the post with `respawn_invuln_s` (1.5 s) of invulnerability, so
a walker that respawned on top of the post cannot take a heart before she has
seen it. Everything is in `data/checkpoint.json`.

**Why it cannot soft-lock.** Every kept item is restored as it was at one
instant she really stood on the post, all from the same frame: keys, doors and
pickups together. A door can never be shut behind a spent key, and a key can
never be handed out twice. What differs from that instant is only enemies
(which gate nothing), hearts (more, not fewer) and form timers (fresh). So any
way on that existed when she stood on the post exists again. The form is the
one that needs a rule: transform pads are one-way, so respawning a frog as a
human past the frog pad could strand her; she comes back in the shape she
touched the post in. The only way to be stuck at a checkpoint is to have been
stuck there already, which the level's own design (and the prover) decides.

**Keys are now per level.** They used to survive every restart while the key
pickups came back too, so a death could double a key; and they survived leaving
a level. Now a fresh attempt (`Game.goto_level`) starts with none and a
checkpoint respawn restores exactly the keys held at the post.

**What forgets the checkpoint:** RESTART LEVEL in the pause menu (back to the
spawn), leaving the level, the title, game over, finishing the level, a new
run. God mode keeps working: a fall in god mode costs no life and returns to the
checkpoint.

### The look

`assets/sprites/checkpoint.png`, drawn natively at 2x by
`tools/art/checkpoint_art.py` (also run by `tools/gen_art.py`): a carved post on
a stone footing with a bronze brazier. Unlit: cold coals, a dead glyph. Lit: a
three-frame flame and the glyph burning gold. A lit post throws an additive
glow (the ambience light-pool texture) so it reads in the deeps; an unlit one a
faint glow so it can be found in the dark. Lighting one plays `checkpoint`
(tools/gen_audio.py), bursts the `checkpoint` emitter (data/fx.json) and flashes
CHECKPOINT on the HUD. Only the active post is lit.

## Large levels

A level is any whole number of 25x15 screens; nothing in the runtime assumes
50x30. What was checked, and what changed, is in the long/engine report
(`REPORT.md` on that branch) with the measurements. In short:

- **Prover:** the duplicate-state key packed x into 11 bits, so past column 120
  every x was one bucket. Now 13 bits of x and 12 of y (504 x 248 tiles).
  50x30 proofs are unchanged.
- **Tile renderer:** the per-frame animation pass and the per-scroll live set
  walked every chunk in the level; now only the chunks under the view.
- **Fixtures:** `tools/stress_level.py` builds the same per-screen content at
  any size (`tests/fixtures/stress_*`), each with a proved route through three
  checkpoints. `tools/seq/long_perf.json` times a whole route
  (`{"route_perf": ...}`); `tools/seq/long_bench.json` times each per-frame
  path that walks something level-sized (`{"bench": ...}`).
- `Game.goto_level("res://tests/fixtures/x.json")` plays a fixture by path.
- `tools/clipgate.sh res://tests/fixtures/x.tape.json` gates a fixture's tape.

## tools/levelstats.sh

One row per level from the level JSON and its proof tape, replayed in the
prover's sim (`tools/levelstats/`):

```
tools/levelstats.sh                    every side-view level
tools/levelstats.sh jungle_1 --json    one level, as JSON
tools/levelstats.sh --level-file=res://tests/fixtures/stress_200x45_jungle.json
tools/levelstats.sh --strict           exit 1 if any tape is missing or stale
```

Columns: tiles; `scr` screens in the grid; `vis` screens the route passes;
`route_s` tape frames / 60; `hops` declared; `2nd` hops declared in a form other
than human; `cp` checkpoints the route lights / placed; `gap_s` the longest
route time between spawn, each checkpoint (as the route first lights it) and
the end, i.e. the most a death can cost; `enem` enemies (`+B` a boss);
`/min` enemies per route-minute; `haz` hazard tiles within
`near_hazard_tiles` (data/levelstats.json, 2) of her body on any frame;
`forms` the forms the route plays; gems/hearts/keys; `tape` ok, partial (a
boss level's tape stops at the arena), STALE or NONE (route columns blank).

The pure half (`LevelStats`) is unit-tested against a hand-built level and path
(`tests/test_levelstats.gd`); the integration tier checks the replay lights the
arena's checkpoint on the same tape frame the real game does.
