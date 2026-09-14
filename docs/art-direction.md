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

## Phase 4 — Sprites and animation — **DONE**
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

Shipped on `art/phase4-sprites`. What was actually built, and the four places
the paragraph above was wrong, is in "Phase 4 as built" at the end of this
document. Kaya was **not** enlarged — the recommendation held.

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

---

## Phase 4 as built

Delivered as planned: an eight-frame run, jump anticipation and a landing
squash, a real hurt pose, four to six frames on every enemy, and a 48×48 boss
whose three phases are three different animals. Counted the same way the
diagnosis was:

```
kaya frames:          8  ->  20
enemy frames:     2 each  ->  4-5 each
boss frames:          3  ->  18  (6 poses x 3 phases)
boss frame size:  32x32  ->  48x48
```

Four places the plan above was wrong. Two of them are the same mistake seen
from different angles, and it is the one worth carrying into phase 6.

**1. "Frame lists only — no code change" is false, and it could not have been
true.** The anim system reads frame lists from `data/`, so *adding frames* to an
existing animation needs no code. But three of the four things the phase asks
for are not more frames of an existing pose — they are poses that nothing ever
asks for:

- *Jump anticipation and landing squash are states, not frames.* The player's
  animation player loops its frame list forever, so a `jump` list beginning with
  a crouch cycles back through the crouch in mid-air. Anticipation needs the
  list to play once and hold, which is a `"loop": false` flag and four lines in
  `player.gd` and `enemy_base.gd`. The landing squash additionally needs
  somebody to notice the landing: `form_human.gd` now holds a `land` pose for
  110 ms after a touchdown above 130 px/s. The impact speed has to be sampled
  on the last airborne tick, because `step_motion()` has already zeroed `vel.y`
  by the time the form sees the landing.
- *"Visually distinct phases" cannot be expressed in frame lists at all.* The
  Warden's state machine asks for `idle`/`walk`/`windup`/`air`; nothing in that
  vocabulary knows which phase it is in, so all three phases resolve to the same
  frames no matter how many you draw. `boss_grove.gd` now overrides `set_anim()`
  to prefer `<pose>_p1/_p2/_p3` and fall back to the plain name. That is six
  lines, and without them the other seventeen boss frames are unreachable.
- *One animation was already unreachable.* `shooter.json` has declared a `fire`
  animation since M2, and nothing could ever display it: `WINDUP` shot and
  dropped back to `IDLE` in the same tick. It now holds a `FIRE` state for
  200 ms. Worth noting because the data looked complete and was not — which is
  what the new frame-coverage test in `test_art_palette.gd` now guards against
  from the other direction.

**2. Enlarging the boss moves its render anchor, and `ox`/`oy` live inside the
`hitbox` block.** The collision box is `w`/`h` and did not change — 26×26, so
every clearance and every headroom assertion is untouched. But `ox`/`oy` in the
same block are not collision at all; `enemy_base.gd` uses them only to place the
sprite, at `(-ox, -oy)` from the box and mirrored when flipped. Leaving them at
`(3, 5)` while the frame went 32→48 would have drawn a 48-pixel boss down and to
the right of a 26-pixel hurtbox. They are now `(11, 20)`: the box centred
horizontally, its bottom on the boss's feet. `test_combat_data.gd` asserts that
relationship, because the failure is silent — the boss still fights correctly,
it just fights next to itself. **The lesson for phase 6: `hitbox` in this
project is two unrelated things wearing one name.**

**3. The fish and the piranha were drawn facing the wrong way, and animating
them is what made it visible.** Both were authored head-left. `flip_h` is keyed
off `facing`, so `facing == 1` drew them unflipped — swimming backwards. With
two near-identical frames nobody could tell; with a four-beat tail sweep it is
obvious. Both are still authored head-left, because that is the easier read, and
`sprites.mirror()` flips them on the way out.

**4. Ink-coloured limbs disappear.** The beetle's legs were pure outline, which
is period-correct and works on a light backdrop. Against phase 3's dark terrain
they were invisible, so a four-frame leg cycle animated nothing. They now carry
a chitin segment (`purple` step 3.2) above an ink foot. The same problem would
have sunk Kaya's eight-frame run for a different reason: with one skin tone the
far leg reads as the near leg flickering, so `S`/`n`/`N` were added as a
two-step-darker copy of `s`/`m`/`M`. **Any limb that crosses the body needs its
own value, not just its own outline.**

**One thing the plan under-sold.** Composing frames instead of drawing each one
whole — `_kaya()` stacks a head, one of five torsos and one of twelve leg
blocks, and `_swap()` derives the opposite half of the run cycle by exchanging
the near and far materials — is what makes twenty frames affordable. It also
makes them *consistent*: the second half of the run is the same length of stride
as the first by construction rather than by care. The assertions inside
`_kaya()` and `cell()` caught about a dozen mistyped rows that would otherwise
have shipped as a silhouette one pixel out.
