# Art overhaul plan — towards the Apogee VGA look

Reference points: *Bio Menace*, *Duke Nukem II*, *Halloween Harry*. This is a
plan to close the gap, ordered so each phase ships a visible improvement on its
own and can be stopped after.

## Diagnosis — measured, not guessed

```
tileset distinct colours:      18
kaya sprite distinct colours:   9
shades per hue family:      max 4, typically 2
```

Apogee's VGA games ran a 256-colour palette with **6–10 shades of every
material**. That single number is the root cause: with two or three shades you
can fill a region, but you cannot model a surface. Everything reads flat because
it *is* flat.

Three deficits, in order of how much they cost us:

1. **No shade ramps.** No highlights, no occlusion, no dithered transitions.
2. **No tile variety.** One `dirt` tile repeated forever, no edges, no corners,
   no decorative overlays. Terrain reads as a rectangle of wallpaper.
3. **Thin animation and no atmosphere.** Three-frame run cycle, no particles,
   no animated tiles, uniform lighting across every screen.

## Proof of concept

`tools/proto_shade.py` (not wired into the game) demonstrated phases 1 and 2 on
four tiles and two sprites. Result: `docs/art-proto.png` — top row current,
bottom row prototype. **Phase 1 promoted it into `tools/art/palette.py`**; the
script is kept only as the record of the experiment.

![before and after](art-proto.png)

Two findings worth carrying into the plan:

- **Sprites transform with shading alone.** Distance-to-edge plus a light
  direction gives Kaya and the beetle real volume for no authoring effort.
- **Tiles do not.** Replacing noise with a gradient made them *softer*, not
  better. Apogee tiles contain discrete *things* — pebbles, mortar courses,
  planks, nails — each with its own highlight and shadow. Structure first, then
  shading. That is what the second prototype pass does.

---

## Phase 1 — Palette and shading engine — **DONE**
**The foundation. Biggest single win, and nothing downstream works without it.**

Shipped on `art/phase1-palette`. What was actually built, and where the plan
below was wrong, is in "Phase 1 as built" at the end of this document.

- Replace the 18 flat colours with ~8 material ramps × 7 steps (~50 colours,
  VGA-appropriate).
- Add to `tools/gen_art.py`: `dither()` (4×4 Bayer, for transitions the palette
  cannot express), `blob()` (a lump with a lit and shadowed face), `crack()`,
  and `auto_shade()` (re-lights existing ASCII art from a light direction).
- Re-render every tile and sprite through it.

**Touches:** `tools/gen_art.py` only. Tile ids, the level legend, collision and
every test are untouched — this is a pure repaint.
**Risk:** none to gameplay. **Effort:** the prototype is most of it.

## Phase 2 — Tile variety and autotiling
**The biggest structural change, and the biggest jump after phase 1.**

- **Autotiling.** Generate the 47-tile blob set per terrain material, and pick
  the variant at load time from the eight neighbours. Terrain stops being
  rectangles and grows proper edges, corners and inside curves.
- **Random variants.** 3–4 interchangeable versions of each fill tile, chosen by
  a position hash so a wall never tiles visibly.
- **Decorative overlays** on the background layer: roots, hanging vines, cracks,
  moss, bones, pipework.

**Touches:** `gen_art.py`, `tile_renderer.gd` (variant lookup),
`level_loader.gd` (neighbour resolution at load). The authored level format does
**not** change — variants are derived, so `levels/*.json` and
`tools/build_levels.py` stay as they are.
**Risk:** moderate. Needs a new test that every material has a complete variant
set, or holes appear only in level geometry nobody walks past.

## Phase 3 — Depth and light
- Per-world background tilesets drawn with **desaturated, darker ramp steps** —
  atmospheric perspective, the trick that gives Duke II its depth.
- Replace the procedural parallax silhouettes with real layered art.
- **Lighting.** Either additive light-pool sprites (cheap, predictable) or
  `Light2D` with a `CanvasModulate` ambient (better, costs fill rate).
  **Decide on device** — this is the one phase with a real mobile perf risk.
- Per-level ambient tint, so ROOT HOLLOW feels underground and SKY BRANCH airy.

**Risk:** the only phase that can cost frame rate. Prototype it on the iPhone
before committing.

## Phase 4 — Sprites and animation
- Kaya: 6–8 frame run with weight, jump anticipation, landing squash, a proper
  hurt pose.
- Enemies: 4+ frames each; the walker currently has two.
- Boss: larger (48×48) with visually distinct phases rather than a colour swap.

**Touches:** `gen_art.py` and `data/forms/*.json` (frame lists only — the anim
system already reads them, so no code change).
**Optional, flagged as a decision:** enlarging Kaya from 16×24 to ~20×28 would
buy detail room, but changes the hitbox and therefore every level's clearances.
The headroom tests would catch the fallout, but it is real churn. Recommend
**not** doing this unless the sprite detail proves cramped.

## Phase 5 — Motion and juice
Cheap, and disproportionately effective:
- Animated tiles: water surface, lava, swaying foliage, flickering light.
- Particles: landing dust, blade sparks, gem shimmer, leaf scatter on a hit.
- Screen shake on the boss slam; brief hitstop on a kill.

**Effort:** small. **Impact on perceived quality:** large.

## Phase 6 — Consistency and performance pass
Sweep for mismatched materials, verify texture memory and draw calls on device,
re-capture `shots/` and regenerate the store screenshots
(`tools/genstoreshots.sh` picks up new art automatically).

---

## Sequencing

Phase 1 alone is worth doing and lands quickly. Phase 2 is where it starts
looking like an Apogee game. Phase 5 is cheap enough to slot in any time and
flatters everything before it.

Phases 1, 2, 4 and 5 carry no gameplay risk — they are art pipeline and data.
Phase 3 is the one to prototype on hardware first.

## What stays true throughout

Everything remains **generated by scripts in `tools/`** and therefore original.
No phase introduces third-party assets. The generators get richer; the rule does
not change.

---

## Phase 1 as built

Delivered as planned: ramps, `dither()`, `blob()`, `crack()`, `auto_shade()`,
every tile and sprite re-rendered, tile ids and levels byte-identical. Plus the
module split the later phases need: `tools/art/{palette,tiles,sprites,
backdrops}.py`, with `tools/gen_art.py` reduced to the running order.

Measured, the same way the diagnosis was:

```
tileset distinct colours:      18  ->  67
kaya sprite distinct colours:   9  ->  26
generated palette:            12 ramps x 7 steps + ink = 85 colours
```

Six places the plan above was wrong or incomplete. They are worth carrying
forward, because four of them change what phase 2 has to do.

**1. Eight ramps is not enough — it took twelve.** The prototype covered dirt,
grass, stone, wood, skin, tunic and purple. The rest of the game needs water
(three tiles plus the piranha and the gem), metal (spikes, plates, the blade,
every eye highlight), gold (switch blocks, keys, the belt, the logo) and ember
(lava, hearts, the hurt pose). At seven steps that is 85 colours, not the ~50
the plan estimated. Still well inside a VGA budget, but the estimate was low
because it was taken from the prototype's sample rather than from the asset
list.

**2. The prototype's `auto_shade()` double-counts the outline, and it shows on
anything thin.** It treats the ink outline as background, so on a limb three
pixels wide every pixel is adjacent to "outside" and gets the full rim
highlight — the sprite comes out uniformly two steps too pale with no internal
relief. The fix is to keep two notions of inside: *volume* measured against the
whole silhouette including the outline, and *facing* measured against the
material only. That is what is in `palette.auto_shade()` now. It is not visible
on the prototype's two sprites; it is obvious across all of Kaya's eight frames.

**3. "Tiles do not transform with shading alone" is right, and there is a
corollary the plan misses.** Authored structure makes a tile read as material —
but a *fill* tile has exactly one variant, so any structure strong enough to
read also repeats visibly across a whole screen. Background leaves and hub grass
both had to be deliberately held back, and a single flower authored into the hub
grass tile turned the overworld into a perfect grid of flowers and was removed.
**So the phase 2 variant sets are a prerequisite for finishing phase 1's fill
tiles, not just an improvement on top of them.** The terrain tiles that carry a
strong read — masonry, bark, crate, lava, metal — are the ones with genuine
structure; the fills are holding.

**4. Backdrops could not wait for phase 3.** The plan scopes phase 1 to tiles
and sprites and gives the parallax and title art to phase 3. But leaving them on
the old flat colours puts two colour vocabularies on screen at once, which looks
worse than either. They were moved onto the ramps — same silhouettes, same
generators, ramp steps instead of literals. Phase 3's job (real layered art,
per-world tilesets, lighting) is untouched.

**5. A cross-ramp gradient has to be routed by hand.** The title sky runs night
blue to sunset orange, which no single material ramp does. Dithering directly
between `water` and `gold` bands hard, because the two are far apart in hue at
similar luminance. It needs an ordered path *through* the ramps — water, purple
as the bridge, then ember and gold — chosen so every neighbouring pair is close
enough that a Bayer mix reads as a gradient. That list is `backdrops.DUSK`.

**6. "The prototype is most of it" was optimistic.** The prototype covered four
tiles and two sprites; the game has 28 tiles and about fifty sprite cells, and
the per-material tuning is most of the work. It was closer to a third. The
engine really was most of the *hard* part, which is probably what was meant.

**One thing the plan under-sold.** Because every colour now comes from a
generated manifest (`assets/palette.json`), the ramp discipline is *testable* —
`tests/test_art_palette.gd` asserts that no sheet contains a colour that is not
a step on a ramp. Nothing else would catch one hand-picked literal slipping into
a generator, and that check is what stops the palette eroding across phases 2-6
as four more people's worth of art gets added to it.
