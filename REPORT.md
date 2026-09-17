# M1 — the route DSL, and declared routes for the five existing levels

Branch `wave1/routes`. Nothing pushed, nothing committed to `main`.

## What I built

**1. `Grid.route()` and `Grid.mark()` in `tools/gen_levels.py`.**

`g.route(from_id, to_id, form="human")` appends a hop; `g.mark(name, x, y)`
names a tile that is not an entity. They serialise into `levels/<id>.json`
exactly as ADR 005 specifies:

```json
"route": [{"from": "spawn", "to": "pad_frog", "form": "human"}, ...]
```

Marks needed a serialisation the ADR does not pin down. I chose a sibling key,
tile coordinates, same convention as an entity:

```json
"marks": {"shaft_top": {"x": 13, "y": 8}}
```

**A mark's `(x, y)` is the tile the player's body occupies while standing
there — the tile directly above the floor, exactly where `player_spawn` sits.**
That is the one interface detail the prover has to agree with me on. See
*Assumptions* below.

Both keys are emitted on every level, including the hub, so `"route": []` is an
explicit statement of "declares no route" rather than an absence.

Generation refuses to write a level whose route cannot mean what it says.
Verified by construction against a synthetic level — each of these raises:

| broken thing | message |
|---|---|
| waypoint is not spawn/mark/entity | `route names 'gem', which is neither 'spawn', a mark, nor an entity in the level` |
| entity type occurs more than once | `route names 'gem', but the level has several of them` |
| hops do not chain | `route breaks between 'm' and 'exit' -- a hop has to start where the one before it arrived, or the prover teleports` |
| does not start at spawn | `the route must start at 'spawn', not 'exit'` |
| does not end at an exit | `the route ends at 'm'; it has to end at one of exit, boss_exit` |
| form has no `data/forms/*.json` | `asks for form 'lizard', which has no data/forms entry` |
| mark inside rock / no headroom | `mark 'm' at (4,8) is inside solid tile '#' at row 8` |
| mark on spikes, off-grid, declared twice, named `spawn`, hop to itself | all raise |

**2. Declared routes in `tools/build_levels.py`**, written beside the geometry:
each `mark()` sits against the platform or vine it names, and each level ends
with an `# ---- the intended solution (ADR 005)` block that reads as a
walkthrough. 54 hops over six levels.

| level | hops | the route, in one line |
|---|---|---|
| jungle_1 | 11 | east over the spike pit, up the vine C→A, east along four canopy branches A→B, down the four-platform shaft B→D, east to the exit |
| jungle_2 | 10 | yellow key → yellow door → vine C→A → switch_a → jump the gap A→B → switch_b → red key → one-way fall into D → red door → exit |
| jungle_3 | 8 | walk to the fish pad, then over / under / over / under / over the five pillars, surface and hop the 16px bank onto the human pad, up the vine to the exit |
| jungle_4 | 16 | human → frog pad → into the shaft → six 3-tile rungs → out through the mouth at cols 12-14 onto the roof → bird pad → three perches → human pad → down the vine → exit |
| jungle_5 | 7 | swim the pool, up the vine C→A, east across two screens, off the lip into the sealed arena, across the floor to `boss_exit` |
| test_arena | 2 | run the lane east past the crate, clear the two spike tiles |

jungle_4 is the route the brief specified, hop for hop. Each of its six rungs is
its own hop deliberately: the 3-tile step *is* that level, and a 4th tile on any
rung is the bug that used to drop the player back to the bottom of the shaft.

**3. Six new tests in `tests/test_level_validity.gd`**, reading the raw JSON
(nothing in `src/` consumes `route`, so nothing in `src/` would notice it
vanishing):

- `test_every_playable_level_declares_a_route` — **a level with no route fails.**
- `test_every_route_hop_names_a_form_that_exists`
- `test_every_route_waypoint_resolves_to_one_place`
- `test_every_route_starts_at_the_spawn_and_chains`
- `test_every_route_ends_at_a_way_out`
- `test_every_mark_is_somewhere_the_player_could_be` (not solid, headroom, not a hazard)

The hub is excluded by id, matching the existing
`test_every_playable_level_has_a_way_out`.

## Verify it

```sh
tools/genlevels.sh     # regenerates levels/*.json; route validation runs here
tools/test.sh          # 135 tests, 8785 assertions, 0 failed
tools/validate.sh      # validate: OK + reachability clean on all six
tools/itest.sh         # integration: 273 checks, ALL PASSED  (exit 0)
```

All three gates pass on this branch.

To see the routes drawn on the grids (what I reviewed them against):

```sh
python3 - <<'EOF'
import json
for lid in ["jungle_1","jungle_2","jungle_3","jungle_4","jungle_5","test_arena"]:
    d = json.load(open("levels/%s.json" % lid)); fg=[list(r) for r in d["fg"]]
    ents={}
    for e in d["entities"]: ents.setdefault(e["type"],[]).append((e["x"],e["y"]))
    def at(w):
        if w=="spawn": return ents["player_spawn"][0]
        if w in d["marks"]: return (d["marks"][w]["x"], d["marks"][w]["y"])
        return ents[w][0]
    print("="*60); print(lid)
    for i,w in enumerate(["spawn"]+[h["to"] for h in d["route"]]):
        x,y=at(w); print("  %s %-13s (%2d,%2d) floor='%s'" % ("0123456789abcdefg"[i],w,x,y,fg[y+1][x])); fg[y][x]="0123456789abcdefg"[i]
    for r in fg: print("".join(r))
EOF
```

To see the gate actually bite, delete `"route"` from any `levels/*.json` and run
`tools/test.sh`. I checked eight mutations this way and each one failed loudly
with the right message: no route, empty route, broken chain, missing terminal
exit, wrong start, unknown form, ambiguous waypoint (`gem`), mark moved into
rock.

## What I could NOT verify

**The routes themselves are UNVERIFIED. Every one of them must be proved at
merge by `tools/prove.sh`.** I do not own the prover and did not stub, fake or
approximate it. Nothing in this branch is evidence that any of these levels can
be played — it is a set of 54 claims written to be checked.

Concretely, I have *not* shown that:

- any hop is physically traversable. Reachability (`tools/validate.sh`) says the
  entities are reachable, and ADR 005 says that verdict is never again quoted as
  evidence. I am not quoting it.
- my hop lengths are sane for a best-first search. Where the intended path moves
  *away* from the goal I inserted a mark so distance still falls — jungle_4's
  `vine_foot`, because the way down is west of the exit — but that is a guess
  about a heuristic I cannot run.
- the jumps I assume are the hard ones actually land: jungle_2's 3-tile gap at
  cols 22-24 (twice), jungle_3's 16px bank hop (the shape of historical defect
  4), jungle_4's frog rungs and the 5-up/6-across bird flight to `perch_3`.
- a form can reach a pad at all — e.g. jungle_3 puts `pad_fish` two tiles inland
  and the fish has to cross that ground to reach water.

What I *did* verify about the routes is weaker and structural: every waypoint
resolves to exactly one place, the hops chain from spawn to an exit, and every
mark sits on a non-solid tile with a non-solid tile above it and a floor or a
vine under it. I checked that last one by eye as well, by printing each grid
with the route overlaid.

There is no screenshot. Item 4 of the definition of done does not apply — this
change adds no rendered feature, only data and tests — and `shots/` is not mine.
I also did not touch `CHANGELOG.md`: it is outside my ownership list and eight
agents editing it would collide. **Someone needs to add a CHANGELOG line for
this at merge.**

## Two defects I found and did NOT fix

I was told not to redesign any level. Both of these are geometry, so I declared
them in comments beside the route and left them alone. Both are the same class
of bug as the six historical ones — the level still finishes, so no gate sees
them — and both make a designed gate free.

**jungle_2: the red door can be walked around.** `key_red` is at (44,8) on the
platform at cols 43-46. The only way off it is down, and the fall lands at
cols 43-46 row 25 — already *east* of `door_red` at col 38, two tiles from the
exit. You cannot climb back west either: `ground(37,42)` stands at row 5 and the
key platform at row 8, and a 3-tile rise is impossible for the human (apex 2.78).
So the red key/door pair gates nothing. The route still goes through the door,
because that is what the level is about; expect the prover to pass it and expect
it to look silly in the tape (walk west past the exit, open a door, walk back).

**jungle_3: the cyan key is not on the route, and the cyan door gates nothing.**
The vine surfaces at col 45; `door_cyan` is at col 44 and the `exit` at col 46.
The exit is therefore on the near side and needs no key. Worse, `door_cyan`
shut makes tile (44,7) solid, so the only way *to* the key is over the closed
door that the key opens. I would have had to declare a hop that crosses a shut
door to fetch its own key, which is not a solution, so `key_cyan`, `door_cyan`
and the whole ten-platform upper-left traverse are off-route and unproved.
Note `tools/reachability.py` reports `key_cyan` reachable. It is wrong, or
rather it is modelling something that is not the game — which is the entire
premise of ADR 005.

## Assumptions I made about other agents' work

1. **Marks serialise as `"marks": {"<name>": {"x": <tile>, "y": <tile>}}`,
   sibling to `"route"`.** ADR 005 names `g.mark("shaft_top", x, y)` but does not
   specify the JSON. If the prover author wants a different shape, this is a
   one-line change in `Grid.to_dict` plus a regenerate — tell me and I will move
   it rather than you working around it.
2. **A waypoint's tile is where the player's body is, not where its feet touch.**
   `(x, y)` names the tile *above* the floor, matching `player_spawn` — e.g.
   jungle_4 spawns at (2,25) with ground at row 26. The prover must seed and
   goal on that convention. If it instead treats `y` as the floor tile, every
   waypoint in this branch is one tile low.
3. **The prover's arrival tolerance is at least about a tile.** I dropped
   `boss_grove` from jungle_5's route partly for this: it is authored at (40,25)
   while the arena floor is stood on at row 26, so "arrive at the boss" is a
   point no player position can coincide with. The rest of my entity waypoints
   all sit exactly on the standing row, so this only matters if the tolerance is
   very tight.
4. **A fight is not a traversal problem.** jungle_5's route stops at
   `boss_exit` and says nothing about the Warden — that is the Boss Gate's
   question (ADR 005 §4), and whoever owns it owns the strategy tape.
5. **`hub()` is untouched.** I verified `def hub(...)` in `tools/build_levels.py`
   is byte-identical to `HEAD`. But `levels/hub.json` *is* regenerated (it gained
   `"marks": {}` and `"route": []`), because it comes out of the same
   `write()`. Whoever rebuilds the hub will regenerate that file from their own
   tree — if they do not have my `gen_levels.py`, their `hub.json` will drop
   those two keys. Harmless for the hub itself (it declares no route by design,
   and the test skips it by id), but worth knowing at merge.
6. **`switch_*` and `door_*` effects apply between hops, as ADR 005 says.**
   jungle_2's route crosses `switch_a` and `switch_b`; neither flip touches a
   tile the later hops stand on, which I checked by hand against the grid. It is
   still an assumption about semantics I did not run.

## One thing I changed outside the level files

`tools/env.sh` in this worktree had `PROJECT_ROOT` pointing at
`/Users/christianheuer/git/jungle-project` — the main checkout, not this
worktree — so `tools/genlevels.sh` was `cd`-ing out of the worktree and
regenerating the main repo's `levels/`. I repointed it at this worktree. The
file is gitignored and per-worktree so it does not merge, and I confirmed the
main checkout is clean (`git -C .../jungle-project status --porcelain` is
empty; the write there was byte-identical to what was already committed). **If
the other seven worktrees were seeded the same way, they have the same bug and
may be running their tools against the main checkout.** Worth checking.

I also ran `tools/import.sh` once, because this worktree had no `.godot/`, so
every test file failed to load with `Could not find base class "TestCase"`.
`.godot/` is gitignored.
