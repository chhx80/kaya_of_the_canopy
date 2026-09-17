# REPORT — M2-M5 art: four tilesets and four parallax backdrops

Branch `wave1/art`. Nothing pushed, nothing on `main`, `build/` untouched.

---

## 1. What I built

Four worlds, each a **twelve-tile set plus a three-plane parallax backdrop**,
all script-generated from `tools/art/palette.py`'s ramps with the same
dither/auto-shade discipline as the jungle set. No third-party anything.

| World | Ambience name | Tile ids | Palette |
|---|---|---|---|
| 2. SUNKEN RUINS | `ruins` | 220-231 | `stone` blue-grey 1.6-3.4, `water` in every joint, `foliage` algae held under luma 55 |
| 3. THERMAL HEIGHTS | `heights` | 240-251 | `dirt` 2.2-3.4 mottled heavily with `stone`; the warmth is in the backdrop, not the tiles |
| 4. TERMITE DEEPS | `deeps` | 260-271 | `dirt`/`wood` 21-90 with grey grit; the luminous accent is **violet** |
| 5. THE OBSIDIAN NEST | `obsidian` | 280-291 | `stone`/`purple` 22-45; `ember` only in one-pixel cracks |

Each block, in id order: solid mass, its capped (ledge-top) form, background
wall, secondary solid, background void fill, background column, one-way,
hazard, climbable, a second background fill, a breakable, and one more solid.
The exact names are in `data/tiles.json`, which now carries a comment per block.

### Tile id table for the level agents

```
220 ruin_stone   solid       240 heights_rock      solid
221 ruin_stone_algae solid   241 heights_rock_sun  solid
222 ruin_wall    bg          242 heights_wall      bg
223 ruin_silt    solid       243 heights_scree     solid
224 ruin_deep    bg          244 heights_air       bg
225 ruin_column  bg          245 heights_stack     bg
226 ruin_slab    oneway      246 heights_plank     oneway
227 ruin_urchin  hazard      247 heights_vent      hazard
228 ruin_grate   solid       248 heights_chain     ladder
229 kelp         ladder      249 heights_basalt    solid
230 ruin_algae   bg          250 heights_cloud     bg
231 ruin_cracked solid+break 251 heights_shell     solid+break

260 deep_earth   solid       280 obsidian         solid
261 deep_crust   solid       281 obsidian_hot     solid
262 deep_comb    bg          282 nest_wall        bg
263 deep_chitin  solid       283 nest_block       solid
264 deep_void    bg          284 nest_void        bg
265 deep_root    bg          285 nest_flue        bg
266 deep_shelf   oneway      286 nest_ledge       oneway
267 deep_spore   hazard      287 nest_shard       hazard
268 deep_ladder  ladder      288 nest_chain       ladder
269 deep_fungus  bg          289 nest_vein        bg
270 deep_glowwall solid+break 290 nest_plate      solid
271 deep_packed  solid       291 nest_crust       solid+break
```

`x20/x21` (e.g. 220/221) autotile **against each other** — put the capped form
on top of the mass and the ledge grows a lit crest, an occluded underside and
inside corners. `x22` is the background wall and autotiles on its own. Every
other id is a one-off object with three to six interchangeable paintings.

`270 deep_glowwall` is the luminous breakable the Brood Queen fight is
described around; it uses the existing `breakable` flag, no new mechanic.

---

## 2. Exact commands to verify it

```bash
# 0. FIRST: tools/env.sh in this worktree had PROJECT_ROOT pointing at the
#    main checkout. I repointed it (the file is gitignored, so the fix does not
#    travel). Check yours before anything else:
grep PROJECT_ROOT tools/env.sh          # must be THIS worktree

tools/genart.sh                          # regenerate; output is deterministic
tools/genfx.sh                           # derives from the tileset; run after
tools/test.sh                            # 129 tests, 17917 assertions
tools/validate.sh
tools/itest.sh                           # 273 checks

source tools/env.sh                      # gen_art.py is not chmod +x; use $PYVENV
"$PYVENV" tools/gen_art.py --readability # the measurement in section 4

# rebuild the contact sheets
"$PYVENV" tools/gen_art.py --preview
for w in ruins heights deeps obsidian; do
  tools/grid.sh shots/world_${w}_sheet.png 2 2 \
    shots/world_${w}_ingame.png shots/world_${w}.png \
    shots/world_${w}_backdrop.png shots/world_${w}_tiles.png
done
```

### Gate results, run in this worktree after the final change

```
tools/test.sh      129 tests, 17917 assertions, 0 failed   ALL TESTS PASSED
tools/validate.sh  validate: OK   (all six existing levels still reachable)
tools/itest.sh     integration: 273 checks, ALL PASSED
```

`tools/test.sh` went from 8,489 assertions to 17,917 with no new test file:
`tests/test_tile_variants.gd` walks every atlas cell the manifest names, and
there are now 3,265 of them.

---

## 3. Contact sheets

One per world, four 400x240 panels each, built with `tools/grid.sh`:

- **`shots/world_ruins_sheet.png`**
- **`shots/world_heights_sheet.png`**
- **`shots/world_deeps_sheet.png`**
- **`shots/world_obsidian_sheet.png`**

Panel order is: **top-left** the world drawn by the running game; **top-right**
the same layers composited offline with all four player forms standing in it;
**bottom-left** the three parallax planes alone; **bottom-right** the twelve
tiles at 4x in id order.

Also in `shots/`: `world_<w>_ingame.png` (the raw captures),
`world_<w>.png` for all **six** worlds including `jungle` and `sky` — those two
are the calibration baseline for section 4, not new art — and
`readability.json`.

---

## 4. Readability: what I measured and what it says

The brief names a real defect in the shipped art: the green frog is hard to
pick out against the green hill parallax. Nothing in either test tier can see
that, so I built a measurement and calibrated it on that exact case.

`tools/gen_art.py --readability` composites the real layer stack (three
parallax planes, background tile layer, solid tile layer), stands each of the
four forms in it at **seven positions** — on the floor, on two ledges, in
mid-air, in a walled room and against open backdrop — walks the outline of each
sprite, and compares every boundary pixel against the scenery pixel immediately
outside it.

- **Threshold is derived, not chosen.** Colour distance is the usual weighted
  RGB approximation; the cutoff is the *smallest distance between two adjacent
  steps of any ramp in `assets/palette.json`* — **28.6**, `foliage` 0 to 1.
  Below that the palette cannot express a difference, so neither can a player.
- **`lost%`** is how much of the outline is camouflaged. It is never near zero
  and should not be: a sprite with a wide internal range always loses its dark
  pixels against a dark world.
- **`hole%`** is the largest *connected* stretch lost. This is the number that
  decides, because a silhouette survives scattered losses and dies when one
  whole side of it goes.

```
  world      fg-bg           human           frog           fish           bird
              luma     lost / hole    lost / hole    lost / hole    lost / hole
  deeps      +28.6      0.3%/  0.9%     0.0%/  0.0%    10.4%/  5.0%     0.0%/  0.0%
  heights    +35.2      0.0%/  0.0%     0.0%/  0.0%     2.9%/  2.5%     0.0%/  0.0%
  jungle     +23.1      0.9%/  1.8%    15.2%/ 10.4%     0.7%/  2.5%     0.0%/  0.0%
  obsidian   +20.6      0.0%/  0.0%     0.0%/  0.0%     0.0%/  0.0%     0.0%/  0.0%
  ruins      +29.8      0.9%/  0.9%     4.8%/  4.2%     0.0%/  0.0%     0.0%/  0.0%
  sky        +42.3      0.1%/  0.9%    10.7%/  6.2%     0.7%/  2.5%     1.0%/  6.9%
```

`jungle`/frog is the worst cell in the table — the defect the brief describes,
reproduced as a number. Every new world beats it on both figures.

**`fg-bg luma`** is the second half of readability: mean brightness of the
solid layer minus the background layer. It is there because the first pass of
TERMITE DEEPS measured **+14.9** and the screen was one flat brown field in
which you could not tell floor from wall. It is +28.6 now.

### The honest weak spots, worst first

1. **The fish in TERMITE DEEPS — the weakest new combination** (10.4% lost /
   5.0% hole). The fish is built entirely from the `gold` ramp and its shadow
   side is `4e2e11`, which is `gold` step 1; the Deeps' packed earth is `dirt`
   2-3. Those browns are inherently close. I pulled the fill off the hue with
   grey grit (which is why the Deeps mass looks gravelly) and that halved the
   hole, but it cannot go to zero without the world stopping being brown.
   `docs/plan-20-levels.md` puts world 4 on frog and human, so this is a form
   that should rarely appear there — but if a level does put the fish in the
   Deeps, this is the combination to look at.
2. **The frog in SUNKEN RUINS** (4.8% / 4.2%). Algae on grey stone, and the
   frog is green. It is a third of the jungle defect and I judged the algae
   worth keeping, but it is the second thing I would look at.
3. **THERMAL HEIGHTS' background wall (242) is very dark.** In the capture the
   walled half and the open half are a large value jump apart. That is
   deliberate — a gallery cut into a cliff — but a level that wants a *bright*
   enclosed room in this world should use `244 heights_air` or
   `250 heights_cloud` as its background fill instead.
4. **TERMITE DEEPS is the weakest world aesthetically.** Its background comb
   reads more as horizontal ribbing than as cells at 16 px, and the grey grit
   that fixed the fish contrast pushes it away from "dark browns". It is
   readable and it works; it is not as good as the other three.
5. **The heights sky is the brightest plane in the set** (luma span 205.8, p90
   177, p99 239 — a near-white cloud sea across the bottom third). The existing
   `sky` world already does this deliberately and passes the same test, but it
   is the plane most likely to need a level-side `air`/`bg_tint` to sit under.

---

## 5. What I could NOT verify

Stated plainly rather than implied away.

- **The new worlds are not covered by `tests/test_art_depth.gd`.** That file
  derives its world list from `data/ambience.json`, which I do not own and did
  not change, so it still only checks `jungle` and `sky`. **The moment a level
  agent adds an ambience entry naming `ruins`/`heights`/`deeps`/`obsidian`, all
  of those checks start applying to my planes.** I ran the same four assertions
  by hand against all twelve new planes — exactly 400x240, sky plane fully
  opaque, far/near planes not fully opaque, zero off-ramp colours, luma span
  under the tileset's 226.8 — and all twelve pass. That is a hand-run check, not
  a suite run.
- **How the tiles look under a real ambience.** The in-engine captures used a
  near-neutral throwaway ambience entry (air alpha 0.06, vignette 0.10). A
  level with a heavy tint, thick haze or a light-radius darkness pass will look
  materially different — particularly TERMITE DEEPS, whose boss arena is meant
  to be unlit. I aimed the Deeps at surviving that (its void fill is the
  darkest in the game and its accent is a hue no form uses) but I could not
  test it, because the darkness verb is not built yet.
- **No level uses these tiles.** I do not own `levels/*.json`,
  `data/level_legend.json` or `tools/build_levels.py`. The autotiling is proven
  by `tests/test_tile_variants.gd` and by the in-engine captures, not by a
  shipped level.
- **Device VRAM.** The atlas is 256x3680, 3.77 MB as RGBA, 260 KB on disk. That
  is inside the 4096 px maximum texture size every current target guarantees,
  with 416 px of headroom. I did not measure it on a phone; M6 owns that.
- **Tile animation.** `data/tile_anim.json` is not mine. Nothing in the new
  sets animates — no lava-style flow on `281 obsidian_hot`, no drift on
  `230 ruin_algae`, no breathing on `269 deep_fungus`. They are all drawn to
  work as static tiles; animating them later needs only an entry in that file.
- **Colour-blind readability.** The measurement uses a luminance-weighted RGB
  distance, which is a rough proxy. I did not simulate protanopia or
  deuteranopia. The two worlds I would expect to be worst there are RUINS
  (green algae on grey) and the NEST (red ember on violet-black).

---

## 6. Assumptions I made about other agents' work

Each of these is a place where my work breaks if someone else chose
differently. Ordered by how much damage a mismatch does.

1. **Backdrop world names are `ruins`, `heights`, `deeps`, `obsidian`.**
   `data/ambience.json` must use exactly those strings, because
   `Ambience.for_level()` resolves them to `assets/sprites/bg_<world>_*.png`.
   A different string is a level with no backdrop art and a failing
   `test_art_depth.gd`. **This is the assumption most likely to bite.**
   Note the world for level set 5 is `obsidian`, but its tile names are
   prefixed `nest_` — the tile ids are what levels reference, so this only
   matters when writing the ambience entry.
2. **Ids 200-219 belong to the verbs agent and I never touched them.** I moved
   `VARIANT_BASE` from 32 to 400 so that *both* our ranges sit below the
   variants — `tests/test_tile_variants.gd` asserts every declared gameplay id
   is below `variant_base`, and with the old value of 32 the verbs agent's ids
   would have failed that check too. Atlas cells 28-219 are blank and
   unreferenced; `tools/art/tiles.py` now has a `T_AT(id, img)` helper that
   places a tile at an explicit index, which is what they need to paint theirs.
   **If the verbs agent declares ids 200-219 in `data/tiles.json` without
   painting them, those cells are transparent** — no test catches it, because
   the tests only walk cells the *variant manifest* names.
3. **`data/tiles.json` merge.** I appended only inside 220-399 and renumbered
   and removed nothing. I also added five `_comment_*` keys — **at the top
   level, not inside `tiles`**. That matters: `TileData4.load_from_dict()` does
   `var t: Dictionary = tiles[k]` over every key in `tiles`, so a string value
   in there is a runtime type error and `int("_comment_ruins")` is `0`, which
   would have clobbered tile id 0's flags. I made that mistake and caught it
   before committing; anyone adding notes to that file should do the same.
4. **`breakable`, `oneway`, `ladder`, `hazard` keep their current meanings.** I
   used only flags that already exist. `270 deep_glowwall` and the three other
   breakables assume the crate's breaking behaviour applies unchanged.
5. **The four player form sheets do not change.** Every readability number
   above is measured against the current `assets/sprites/kaya_*.png`. If the
   enemies/sprites agent re-lights a form, **re-run
   `tools/gen_art.py --readability`** — the numbers are cheap to regenerate and
   the whole point of them is that they are not a promise.
6. **`tools/art/sprites_enemies_v2.py` is the enemies agent's file and I never
   created, read or imported it.** I also added **no new files under
   `tools/art/`** on purpose — the tilesets went into the existing
   `tools/art/tiles.py` and the backdrops into `tools/art/backdrops.py`, and
   the measurement harness went into `tools/gen_art.py`, all three of which are
   explicitly mine.
7. **`tools/dev_capture.gd` and `tools/seq/` are not mine.** To get in-engine
   captures I temporarily wrote four throwaway levels, four ambience entries,
   the legend characters they needed and one seq file, took the shots, then
   deleted the levels and the seq file and `git checkout`ed `data/ambience.json`
   and `data/level_legend.json`. **The only things that survive are the PNGs in
   `shots/`.** `git status` after cleanup shows changes to
   `data/tiles.json`, `tools/art/*`, `tools/gen_art.py`, `assets/**` and
   `shots/**` and nothing else. The throwaway harness is not committed; if you
   need it again it is thirty lines and the shape is described here.

---

## 7. Things that went wrong on the way, and are worth knowing

Three of these were invisible to every check except looking at the picture.

- **`tools/env.sh` in this worktree pointed `PROJECT_ROOT` at the main
  checkout.** Every `tools/*.sh` script does `cd "$PROJECT_ROOT"` first, so my
  first baseline run of `test.sh`, `validate.sh` and `itest.sh` was testing
  `~/git/jungle-project` and not this branch at all. It also meant one early
  generator run wrote into the main checkout — I checked, `git status` there is
  clean and `main` is undamaged, because the run regenerated byte-identical
  output from the unmodified file it found there. The file is gitignored, so my
  fix does not travel; **check it in your own worktree before trusting a green
  suite.**
- **All four in-engine captures drew THE OBSIDIAN NEST's tiles with the right
  backdrop behind them.** The throwaway harness re-read `level_legend.json`
  per level, so all four worlds assigned the same characters to their own
  different ids and only the last mapping was written. The levels loaded, the
  tiles rendered, nothing errored, and the picture was simply wrong. Fixed by
  threading one legend through all four.
- **THERMAL HEIGHTS read as planking**, not rock, for its first two passes:
  level strata on a brown ramp is a wall of boards. Fixed by making the bedding
  wander and pinch out, and by turning half the surface grey mineral.
- **The heights cliff frame painted itself down the right edge of the screen**
  as well as the left, because `Plane.set()` wraps in x by design and the loop
  started at `x0 - 12`.
- **The basalt-stack background tile had a 2 px stripe of `metal` 4.0 —
  luma 140 — repeating every 16 px**, which is the frog's own band. It is a
  shadowed cleft now.
