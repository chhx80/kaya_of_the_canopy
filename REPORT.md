# wave2/legend — a per-world level legend

Branch `wave2/legend`, three commits off `2d48d72`. The work is `74a4362`;
the other two are this report and the `.uid` Godot generates for the new test
script.

## The problem, restated from the measurement

`data/tiles.json` declares 92 tile entries. `data/level_legend.json` mapped 28
characters to ids 0–27. Everything the four new worlds needed — the movement
verbs at 200–215 and the four tilesets at 220–291 — was painted in
`assets/tiles/tileset.png`, covered by `tests/test_tile_variants.gd`, and
**unplaceable**, because a level is a character grid and no character named it.

## What I built

**The legend is per-world.** `data/level_legend.json` now holds:

| key | what it is |
|---|---|
| `shared` | characters meaning the same tile in every world — water, the eleven currents/drafts, the five breakable walls, switch blocks, lava, metal, the hub tiles |
| `tilesets` | one character map per world: `jungle`, `ruins`, `heights`, `deeps`, `nest` |
| `default_tileset` | `jungle` |
| `legend` | a **derived** copy of `shared` + `tilesets.jungle` (see *Compatibility*) |

A level names its world with a top-level key, and **the key is optional —
absent means `jungle`**:

```json
{ "id": "ruins_1", "name": "THE DROWNED GATE", "tileset": "ruins",
  "fg": ["....|....", "#########"], ... }
```

### Where I improved on the brief

The brief proposed "the same characters mean that world's stone, that world's
water, that world's breakable wall". I made that literal and closed, in five
ways:

1. **A role alphabet, not an ad-hoc per-world map.** Every tileset binds the
   *same twelve characters* to its own art:

   | | | | |
   |---|---|---|---|
   | `#` ground cap | `S` the solid it autotiles against | `d` fill under the cap | `s` a second, harder solid |
   | `=` one-way platform | `\|` ladder / climbable | `^` hazard | `c` breakable block |
   | `L` background wall | `T` background column | `r` background accent | `X` background deep / void |

   The consequence that matters is not readability, it is that **the DSL
   idioms become world-agnostic**: `g.ground()`, `g.platform()`, `g.vine()`,
   `g.spikes()`, `g.canopy()` build any of the five worlds unchanged, and a
   screen can be ported between worlds by changing one key. The jungle adds
   `[`, `]`, `-` for tiles no other world has.

2. **A `shared` block, and tilesets may not redefine it.** Water is water. A
   design where `w` means one thing in the ruins and another in the nest would
   be a bug generator; the test refuses it outright.

3. **The tileset key is omitted when it is the default.** Writing
   `"tileset": "jungle"` into the six existing levels would change their bytes,
   change their `source_sha`, and stale every tape in `proofs/` (ADR 005) to
   say what the absence of the key already says.

4. **A rejected level hands back no world at all** — see *Failing loudly*.

5. **The flag-parity invariant is pinned** — see *Compatibility*.

### Where I disagree with nothing, but flag a cost

A character grid is no longer self-describing. You cannot read
`levels/nest_3.json` without first looking at its `tileset` key. Loader, DSL
and validity tier all check it so the failure is loud, but a human skimming a
diff has one more thing to hold. I think that is the right trade — five worlds
is ~75 gameplay ids competing for printable ASCII, and a global legend reaches
`Ω`-means-nest-ledge long before it runs out, which is an LDtk uid table with
extra steps — but it is a real cost and it is now written into ADR 002 rather
than discovered later.

### Failing loudly (requirement 4)

A character the level's own world does not define is an error, and
`LevelLoader.from_dict()` returns a `LevelDef` with **`world == null`**.

The null is the point, and it is a behaviour change beyond the brief. The
unmapped character used to fall through `legend.get(ch, 0)` to tile 0, so the
grid came back looking like a level with some air in it and only `errors` —
which a caller can forget to check — said otherwise. A mis-declared world
would have loaded as a field of empty space: rendering, walkable-looking,
unfinishable. That is the shape of all six historical defects — the mechanism
reported a problem while the outcome looked fine. There is now nothing to
misuse. Every caller in the repo (`Level.load_level`, `validate_scenes.gd`,
`tools/solver/prove.gd` ×2, `overworld.gd`, `diverge.gd`, the tests) checks
`ok()` before touching `.world`; I read each one.

The error names **every** bad character, **and the tileset it was checked
against** — `"level 'ruins_1' (tileset 'ruins') uses '[', which that tileset
does not define in data/level_legend.json"`. A level naming a tileset that
does not exist fails the same way and the message lists the ones that do. An
empty `"tileset": ""` is a typo, not "unset", and also fails.

The same mistake also fails one step earlier: `Grid.to_dict()` refuses to
serialise a grid containing a character its tileset does not define, naming the
layer and coordinates of the first occurrence.

### Compatibility, and the one thing I did not touch

`tools/reachability.py` and `tools/build_hub.py` (neither mine) read
`json.load(...)["legend"]` directly. That key still exists as a resolved copy
of the jungle. Two copies of one fact drift, so
`test_the_compatibility_legend_still_equals_shared_plus_the_default` fails if
it ever does.

Those two tools therefore still resolve every character against the jungle.
**Today that gives them the right answer on a ruins level anyway**, for a
reason worth naming: the role mapping preserves gameplay flags across worlds —
`#` is solid in all five, `^` a hazard in all five, `=` one-way in all five —
and both tools read nothing but flags. I measured that rather than assuming it
(all 12 role chars × 4 worlds, 7 flags each: zero differences), and
`test_a_role_character_has_the_same_gameplay_flags_in_every_world` pins it.
Bind `r` to something solid in one world and that test fails, rather than the
pre-filter quietly modelling a wall as air. **Both tools should still learn
`legend_for(tileset)` before a world needs to break that; this is the
hand-off.**

## Files touched

| File | Change |
|---|---|
| `data/level_legend.json` | `shared` + five `tilesets` + `default_tileset` + the derived `legend` view |
| `src/world/level_loader.gd` | `legend_doc()`, `default_tileset()`, `tileset_names()`, `legend_for(name)`; `legend()` kept meaning the default; `LevelDef.tileset`; per-world resolution and the null-world rejection in `from_dict()` |
| `tools/gen_levels.py` | `legend_for()` / `tileset_names()`; `Grid(w, h, tileset=...)`; `_check_characters()`; `"tileset"` serialised only when non-default; `_tile_flags()` now per-world |
| `tests/test_level_format.gd` (+`.uid`) | **new**, 24 cases |
| `tests/test_level_validity.gd` | +2 cases: every level names a world that exists; no level uses a character its own world does not define |
| `docs/adr/002-level-format.md` | amendment: *the legend is per-world, not global* |

Nothing outside my ownership list is modified. `git status` is clean.

## How to verify

```bash
# 0. fresh worktree only: tools/env.sh must point PROJECT_ROOT here, then
tools/import.sh

# 1. requirement 1 — the six levels (seven files) are byte-identical
tools/genlevels.sh && git status --porcelain levels/    # prints nothing

# 2. unit + data tier
tools/test.sh                                            # 243 tests, 0 failed

# 3. structural validator
tools/validate.sh                                        # exit 0

# 4. requirement 2 — the prover
tools/prove.sh                                           # see Results

# 5. in-game tier
tools/itest.sh                                           # see Results
```

## Results, measured, including what is red

### Requirement 1 — byte-identity: **verified, not assumed**

`tools/genlevels.sh` regenerates all seven committed level files
(`hub`, `jungle_1..5`, `test_arena`) with `git status --porcelain levels/`
printing nothing. Re-checked after every subsequent edit.

### `tools/test.sh` — **243 tests, 37481 assertions, 0 failed**

Baseline before my change was 217 tests. The `FAIL a_vine_no_exit` style lines
in the output are `test_prover_fixtures.gd` deliberately reproducing the six
historical defects; that test passes when they fail.

### `tools/validate.sh` — **exit 0**

### `tools/prove.sh` — **bit-for-bit identical to the baseline I measured before touching anything**

|  | before my change | after |
|---|---|---|
| jungle_1 | PROVED, 11 hops, 750 frames, 38435 expansions | PROVED, 11 hops, 750 frames, **38435** |
| jungle_2 | PROVED, 10 hops, 783 frames, 1534 | PROVED, 10 hops, 783 frames, **1534** |
| jungle_3 | **FAIL** — "the tape does not reproduce the proof", hop 8/8 `pad_human > exit` replayed to (743, 164), search left it at (727, 105) | **identical failure, identical coordinates** |
| jungle_4 | PROVED, 16 hops, 1040 frames, 1550 | PROVED, 16 hops, 1040 frames, **1550** |
| jungle_5 | PROVED, 7 hops, 903 frames, 8945 | PROVED, 7 hops, 903 frames, **8945** |
| test_arena | PROVED, 2 hops, 219 frames, 68 | PROVED, 2 hops, 219 frames, **68** |
| exit code | **1** | **1** |

`proofs/*.tape.json` are rewritten byte-identically (`git status` clean), so
no tape went stale.

**Read this honestly: `tools/prove.sh` does not prove all six, and did not
before I started.** My brief said it must still prove all six; the measured
baseline at `2d48d72` is five of six, with `jungle_3` already red. I did not
fix it and it is not mine — `jungle_3`'s red is the same defect as the already-
declared red integration case `t_replay_jungle_3`. What I can state is the
stronger useful claim: **my change is prover-neutral to the expansion count**,
which is the sharpest evidence available that per-world legends did not perturb
the search.

### `tools/itest.sh` — **298 passed, 3 FAILED, exit 1 — identical to the pre-change baseline**

The three are exactly the ones declared red at hand-off, and nothing else:
`t_the_replay_plays_a_tape_split_across_several_hops`, `t_replay_jungle_3`,
`t_replay_jungle_5`.

I did not take this on trust. I checked my five modified files out at `HEAD~1`,
moved the new `tests/test_level_format.gd` aside, and ran the suite again. The two runs are
identical line for line — same three cases, same hop, same sim-frame counts
(181 / 674 / 903), same closest approaches (56.7 px / 194.4 px / 8.5 px), same
298 passing. My change is integration-neutral.

### Negative controls — I broke each invariant to confirm the test catches it

| break | expected | got |
|---|---|---|
| delete `tilesets.deeps["c"]` (→ 270 `deep_glowwall`) | the "every declared tile is nameable" test fails | ✅ that test **and** `test_every_tileset_binds_the_whole_role_alphabet` failed; 2 failed, nothing else |
| set `legend["#"] = 999` | the drift test fails | ✅ exactly 1 failed, `test_the_compatibility_legend_still_equals_shared_plus_the_default` |
| bind `tilesets.heights["r"]` to 9 (spikes) | the flag-parity test fails | ✅ 2 failed: the flag-parity test **and** the nameable test — both true, since rebinding `r` also leaves `heights_cloud` unnameable |
| revert the loader's `def.world = null` to the old fall-through | the null-world test fails | ✅ exactly 1 failed, `test_a_rejected_level_hands_back_no_world_at_all` |

The positive cases (a level in each world loads and keeps that world's ids; `#`
is 2 in the jungle and 220 in the ruins; `[` is legal in the jungle and
rejected in the ruins; a rejected level hands back `world == null`) are all in
`tests/test_level_format.gd` and pass.

### Two things I measured that were handed to me as assumptions

- **Every id my legend names is actually painted.** I decoded
  `assets/tiles/tileset.png` and checked the 16×16 cell behind all 92 legend
  entries (29 shared + 15 jungle + 12 each for ruins, heights, deeps, nest).
  Exactly one is fully transparent: tile 0, `empty`, which is supposed to be.
  The art really is there. The same pass confirms the mapping is a bijection —
  92 entries, 92 distinct ids, and `data/tiles.json` declares 92, so **every
  declared tile is named exactly once and nothing is named twice**.
- **`assets/tiles/variants.json` covers the new worlds' structural tiles**
  (220–226, 228–231, 240–246, 248–251, 260–266, 268–271, 280–286, 288–291).
  The ids with no variant entry — the hazards 227/247/267/287, and the verbs
  200–215 — are the same categories that have none in the jungle either (vine,
  water, spikes, crates, switch blocks, lava). They will render as their flat
  atlas cell, which is correct.

## What I could NOT verify

1. **That a level in a new world renders on screen.** There is no such level:
   creating one means editing `tools/build_levels.py`, which another agent
   owns, and adding a file to `levels/` would change `list_levels()` — which
   gates the hub's `requires_all` door and requires a declared route, so a
   stub level would fail `prove.sh` with exit 2. I therefore have **no
   screenshot**, and I am not claiming the feature renders. What I have is:
   the loader returns the world's ids for the world's characters (tested), the
   atlas cells those ids point at are painted (measured), and the renderer is
   untouched by this change. The first ruins level is the thing that will
   actually prove it:
   `tools/shot.sh --scenario=level:ruins_1 --out=shots/ruins_1.png`.
2. **`CHANGELOG.md` is not updated.** `CLAUDE.md`'s definition of done item 5
   asks for it; `CHANGELOG.md` is not in my ownership list and five agents
   appending to it is a guaranteed conflict. Entry text to paste is at the
   bottom of this file.
3. **Anything about how the new worlds *play*.** This change makes tiles
   nameable. It says nothing about whether a current is fun or an updraft is
   survivable; ADR 005's gate is what will answer that, one level at a time.

## Assumptions about other agents' work

1. **`tools/build_levels.py` (not mine) needs no signature change.** I put the
   tileset on the `Grid`, not on `write()`, so the new-worlds agent writes
   `Grid(50, 30, tileset="ruins")` and `write("ruins_1", g, "THE DROWNED
   GATE", music="world2")` unchanged. Verified by regenerating all seven
   existing levels through the current, unmodified `build_levels.py`.
2. **`data/tiles.json` (not mine) is the id authority and I did not touch it.**
   My role→id mapping is read off the names the art agent chose
   (`ruin_slab`/`heights_plank`/`deep_shelf`/`nest_ledge` are all `oneway`, so
   they are all `=`). If a name and its flags disagree about intent, the flags
   won; `test_every_character_names_a_tile_that_data_tiles_json_declares` and
   the flag-parity test are where that would surface.
3. **Three of the four new worlds have twelve declared ids inside a
   twenty-wide block** (e.g. ruins uses 220–231 of 220–239). I assumed the
   gaps are the "deliberate room to grow" `data/tiles.json` says they are, and
   bound only the declared ids. Adding an id later without a legend entry now
   **fails** `test_every_declared_tile_can_be_named_by_some_level` rather than
   going unnoticed.
4. **`tools/reachability.py` and `tools/build_hub.py` are someone's to fix.**
   See *Compatibility*. They are correct today and will stay correct while
   flag-parity holds.
5. **The three already-red integration cases are not mine.** `t_replay_jungle_3`,
   `t_replay_jungle_5`, `t_the_replay_plays_a_tape_split_across_several_hops`
   were declared red at hand-off, and `prove.sh`'s `jungle_3` failure at
   `2d48d72` is the same defect from the other tier.

## CHANGELOG entry for whoever owns the file

```markdown
- **Per-world level legends** (ADR 002 amendment). `data/level_legend.json`
  splits into `shared` characters and one `tilesets` map per world; a level
  names its world with an optional top-level `"tileset"` key (absent =
  `jungle`). Every tileset binds the same twelve role characters to its own
  art, so `g.ground()` builds the jungle, the ruins, the heights, the deeps
  and the nest unchanged. The 64 tile ids the four new worlds and the movement
  verbs added could not previously appear in any level; they can now, and
  `tests/test_level_format.gd` fails if a future world's art lands without a
  legend entry. A character its world does not define is now an error that
  yields no `TileWorld` at all, instead of silently becoming empty space. All
  seven committed level files regenerate byte-identically.
```
