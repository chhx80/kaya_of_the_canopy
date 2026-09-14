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

## Phase 2 — Tile variety and autotiling — **DONE**
**The biggest structural change, and the biggest jump after phase 1.**

Shipped on `art/phase2-tiles`. What was actually built, and where the plan
below was wrong, is in "Phase 2 as built" at the end of this document.

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

## Phase 3 — Depth and light — **DONE**

Shipped on `art/phase3-depth`. Lighting is additive pools, decided on measured
numbers; what was built and where the plan below was wrong is in "Phase 3 as
built" at the end of this document.

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


## Phase 2 as built

Delivered as planned: the 47-case blob set per terrain material resolved from
the eight neighbours at load, four interchangeable paintings of every fill
picked by a position hash, and roots, vines, cracks and moss scattered over the
background layer. `levels/*.json`, `tools/build_levels.py`, `data/tiles.json`
and `data/level_legend.json` are byte-identical, because variants are derived
rather than authored.

Measured the same way as the diagnosis:

```
tileset cells:                       28  ->  1482  (256x1488, 1.5 MB of VRAM)

distinct atlas cells drawn, per level, as cells / tiles placed:
    THE CANOPY   hub grass     1/640  ->  40/640
                 hub path      1/110  ->  32/110
                 hub tree      1/284  ->   8/284
    CANOPY TRAIL dirt           1/99  ->  18/99
                 grass top      1/57  ->   9/57
                 bg leaves     1/182  ->   8/182
    ROOT HOLLOW  masonry       1/358  ->  42/358
                 bg rock      1/1500  ->  12/1500
```

Five places the plan above was wrong or incomplete.

**1. The plan puts the variant lookup in `tile_renderer.gd` and the neighbour
resolution in `level_loader.gd`. Split that way it is computed twice** — the
level has two `TileRenderer`s and neither of them can see the `LevelDef`. What
actually works is a third, pure module (`src/world/tile_variants.gd`) that owns
both, with a one-level cache keyed on the `TileWorld`: the loader asks for the
map while it still has the grid in hand, and both renderers ask again during
`setup()` and get the same object back. The sweep happens once. It also puts the
whole resolver in tier one of ADR 003 — it is node-free, so `tools/test.sh` can
check all 47 cases of all seven materials without a scene tree.

**2. The two mechanisms are not independent, and treating them as independent
is the mistake that nearly shipped.** The plan lists autotiling and random
variants as separate bullets, which invites building them that way: the 47 blob
cases give an edge its shape, and the random variants go on the interior case,
where all the gridding is. That is what the first pass did — four paintings of
the interior, one of each edge case — on the reasoning that edge cases are rare.

They are not rare. The commonest tile on a platform screen is the *top of a
ledge*, and that is one single blob case: 57 grass tops in CANOPY TRAIL drew
from 3 cells, and a long ledge gridded exactly the way an undifferentiated fill
does. How often a case comes up is a property of the level, not of the mask, so
every case carries the full set. That is the whole reason the atlas is 1482
cells rather than 400, and it is worth it — the counts above are what it buys.
It also means the completeness test has to check the variant count per *case*,
not per tile.

**3. Each case must not be generated from scratch.** Generating 47 full fills
per material makes `tools/genart.sh` slow enough to stop being something you run
casually. Painting the edges *over a copy* of an already-rendered interior is
both faster and better: the interior a case is dressed from is chosen by the
mask, so neighbouring edge tiles do not share one painting either. The whole
generator still runs in about a second.

**4. Autotiling every id that could take it is wrong.** The plan says "per
terrain material", which reads as "everything that is terrain". But tiles 16 and
17 are *authored* cliff faces — autotiling them would fight the level designer,
and one-off objects (crate, spike plate, switch block, rope bridge) want to
repeat, because a repeat is what makes them read as the same object. Seven ids
autotile; ten more take random variants only; the rest are left alone. The
neighbour groups still have to include the authored edges, though, or a platform
grows a second cliff face against its own corner tile.

**5. A rim band is a ruled line unless it is deliberately broken.** This is the
same failure `t_water()` already warns about for foam. The first pass painted a
clean two-pixel lit band along every exposed face and the hub read as a meadow
with a green pinstripe drawn round it. Rims need both a ragged depth and a
chance of being skipped entirely per column. Related: varying only the *texture*
of the hub tree left the trunk in the same four pixels of every tile, so a stand
of them kept a perfect column rhythm — the fix was to move the trunk per variant
and leave a third of them as canopy with no trunk at all.

**6. The atlas is now 1.5 MB of VRAM where it was 32 KB.** Nothing on the
desktop notices and the generator still runs in about a second, but the plan
never costs the variant sets and phase 6 explicitly owns "verify texture memory
and draw calls on device". This is the number that pass is for. If it has to
come down, the lever is the per-case variant count on the materials a level
places in the hundreds, not the case count.

**One thing the plan under-sold.** It calls the completeness test a risk
mitigation. It is also the only way to work on this at all: a variant set is
fourteen hundred images nobody will ever look at one at a time, and the
difference between "all 47 cases present" and "46 of them" is invisible until a
player stands in the one piece of geometry that makes the missing shape.
---

## Phase 3 as built

Delivered: three parallax planes per world instead of two flat strips, painted
through an explicit depth model; a per-level ambience file; and lighting, which
after measurement is **additive light pools, not `Light2D`**.

Measured, the same way everything else here is:

```
parallax planes per level:        2  ->  3   (sky / far / near)
backdrop worlds:                  1  ->  2   (jungle, sky)
colours off the ramps, backdrops: 0  ->  0   (they are ramp output now, and tested)
draw calls, a lit level:         13  ->  17
frame cost of all of phase 3:          +0.05 .. +0.19 ms   (see below)
```

### The lighting decision, with the numbers

The plan says to decide on device. The device is not in this loop, so it was
decided on the two things that *are* measurable here and do carry to a phone:
the ratio between the two implementations on the same renderer, and what each
one does to readability.

`tools/dev_capture.gd` grew a `{"perf": …}` step: it drops vsync, lifts the fps
cap and reports wall-clock frame time, the renderer's own CPU time, draw calls
and video memory. `tools/seq/perf.json` measures every level **twice in the same
process**, lighting on and off, because measuring two separate launches of the
game mostly measures how warm the machine was. GPU timestamps read 0.000 — the
GL Compatibility backend does not report them on macOS — so wall-clock frame
time is the gate, and the fill-rate argument is made by arithmetic below.

All of phase 3, lit vs unlit, same process, 240 frames each:

```
                lit      unlit     delta     draw calls
jungle_1       0.728 ms  0.666 ms  +0.06 ms   17 / 14
jungle_2       0.920     0.726     +0.19      18 / 15
jungle_3       0.844     0.780     +0.06      20 / 17
jungle_4       0.709     0.636     +0.07      17 / 14
jungle_5       0.805     0.756     +0.05      19 / 16
```

One representative run; repeating it moves the third decimal but not the band.
Against the 16.6 ms frame that is 0.3–1.1% of the budget, for three extra draw
calls: one haze quad, one vignette, one batch of pools.

Then the same scene with `Light2D` + `CanvasModulate` instead — same pool
texture, same positions, same count, built as a throwaway branch purely to get
the number:

```
ROOT HOLLOW, 7 lights      pools 0.852 / 0.872 ms     Light2D 1.327 ms   +55%
HEART OF THE GROVE, 4      pools 0.679               Light2D 0.708      + 4%
```

The cost scales with the number of lights overlapping the screen, which is what
you would expect: in the compatibility renderer each light is another pass over
every canvas item it touches, and a tile layer is one canvas item holding a few
hundred draw commands. Seven lights over ROOT HOLLOW's tile layers is seven
extra traversals of those commands. Fewer draw calls, more work — the draw-call
monitor actually reads *lower* for the `Light2D` version (16 vs 18), which is a
good reminder that draw calls are a proxy and frame time is not.

So the cheap variant wins on cost. It also wins on the thing that was supposed
to be `Light2D`'s advantage, which is the part worth writing down:

**`CanvasModulate` dims the player.** It applies to everything in its canvas
layer, so Kaya, the enemies, the gems and the hearts all go down with the room.
`shots/56_phase3_light2d_rejected.png` is the capture the decision was made on:
the rejected `Light2D` build on the left, the shipped pools on the right, same
level, same lights. The brief's hard constraint is
that a player must instantly be able to tell what is solid; a lighting model
whose ambient term lands on the player works against that at exactly the moment
the level is darkest. The pools are ordered into the scene *behind the
entities*, so a dark level now has **more** contrast between Kaya and the floor
than a bright one, not less. That ordering is the reason the layers are three
nodes and not one, and it is checked in the integration suite, because it is
invisible until it is wrong.

On fill rate, since that was the stated risk: a lit screen blends roughly
800,000 pixels per frame — three parallax planes, two tile layers, a haze quad,
a vignette and a handful of pools over 400x240. At 60 Hz that is under 50
Mpix/s. Any phone that can run the game at all clears that by more than an order
of magnitude; the pools are capped at 16 per frame so a screen of water surface
cannot turn into a hundred quads. **Still to do on device:** confirm on the
iPhone that the added texture memory (+1.0 MB, 27.3 total) and the extra
per-frame alpha blending behave, and re-check with the touch overlay drawn.

### The depth model

The old strips were painted at the dark end of `foliage` — every one of them. So
the furthest thing on screen was also the highest-contrast thing on screen: a
black wall behind a lit jungle. The plan's own sentence ("distance reads as
lower contrast, not just smaller") was the fix, and it is now structural rather
than a matter of care.

`tools/art/backdrops.Plane` owns a slice of one ramp — its *window* — and every
brush paints in **material value**, 0 for the shadowed side of a thing and 1 for
the lit side. The plane maps that onto its window when it renders. The width of
the window is therefore the plane's entire contrast budget, and a far plane with
1.2 steps cannot out-contrast a near plane with 2.2 however it is drawn. The
numbers are printed by `tools/genart.sh` and the planes' own docstrings say
which is which.

Two things fall out of that and neither was obvious before building it:

- **Distance can be brighter.** Haze lightens what is behind it. The jungle sky
  plane is a pale blue-grey, well above the tiles in front of it, and it reads
  as further away than the old near-black did — because what fell off is the
  contrast, not the brightness.
- **A material's window is not the plane's window.** SKY BRANCH's far plane
  holds both a cloud sea and the canopy far below it. One window for both put a
  dark saturated green slab directly behind the play field: the busiest edge on
  screen, in the worst place. Materials get per-ramp window overrides, used
  sparingly — the canopy is painted pale, which is also what a forest seen
  through that much air actually looks like.

### Six places the plan was wrong

**1. Two of the five levels cannot show a backdrop at all.** ROOT HOLLOW and THE
WATERWAY author a solid wall of `bg_rock` behind every tile of every screen —
measured, 0% of either level has the parallax visible, against 54–69% for the
other three. "Per-world background tilesets" would have meant drawing a cave set
and a water set that no one would ever see. So two worlds were built, `jungle`
and `sky`, and the two walled levels get their depth entirely from ambient tint,
vignette and light pools. That is also why the ambience file separates "which
backdrop" from "what the air is doing": for half the game only the second half
of that applies.

**2. "Desaturated, darker ramp steps" is half right and the wrong half is
load-bearing.** Desaturated, yes. Darker, no — see the depth model above. Had
the phase been built to the plan's wording it would have produced a slightly
nicer version of the problem it was meant to fix.

**3. A per-level ambient tint is three numbers, not a colour.** It started as one
RGB per layer and the grove came out magenta: a violet tint at full strength cuts
a quarter of the green out of every brown tile in the level. It needs the hue
(a ramp step), how much of that hue to take, and how far to knock the layer back,
as three separate fields. Only then can a level be pushed violet without being
pushed *purple*.

**4. The mood had to live outside `levels/*.json`.** The level files are shared
with `tools/build_levels.py`, the validators and every test that parses them,
and the brief froze them. `data/ambience.json` keys off the level id instead,
which turned out better than an inline field would have been: an artist can
re-light the whole game without touching a single tile, and the lighting can be
switched off wholesale for a measurement.

**5. The real cost of `Light2D` here is not fill rate.** The plan's parenthetical
is "better, costs fill rate". At 400x240 fill rate is not what hurts; the extra
pass over every canvas item per light is. Worth knowing, because it means the
cost scales with *lights overlapping the screen*, not with how big they are —
the opposite of the intuition the plan was working from.

**6. "Prototype it on the iPhone before committing" could not be honoured, and
the fallback is not as good.** What is in hand is a same-process A/B on one
desktop GL driver plus an arithmetic argument about overdraw. It is enough to
choose between two implementations that differ by 55%; it is not enough to
certify a frame budget on a tile-based mobile GPU. The device check is listed
above as outstanding, and phase 6 is where it belongs.

**One thing the plan under-sold.** Because the planes are ramp output now rather
than blends, the backdrop exemption in `tests/test_art_palette.gd` could be
closed: `tests/test_art_depth.gd` asserts every plane and both lighting textures
are pure ramp, that each plane is exactly one screen (which is what makes the
vertical lock seam-free), that the sky plane has no holes in it, that no plane
out-contrasts the tileset, and — the one that will actually catch someone — that
no level's ambience may dim the solid layer below two thirds or below its own
background layer. The readability constraint was the one thing in this phase a
data file could break silently, and now it cannot.
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
