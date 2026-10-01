# Plan: beautiful pixels, fluent motion

The sequel to `docs/art-direction.md`, whose phases 1-4 are built: material
ramps with Bayer dithering, tile variety, per-level depth and light, and a
20-frame human sheet. This plan is what "significantly better" means from
that baseline, and its centrepiece is the thing the game still does worst:
**Kaya turns by mirror**. `player.gd` sets `sprite.flip_h = facing < 0` on
the same frame `form_base` writes `facing` from the input axis, so a
direction change is a one-frame teleport of her whole body. Everything else
here orbits that fix.

## The invariant that outranks every idea below

**Twenty-six proof tapes replay bit-identically, five boss gates pass, and
`tools/prove.sh --verify-tapes` stays green, after every phase.** `facing`
is gameplay — the blade flies along it, shouldering reads it — so no
motion-feel change may write to it or to any physics state. Every
improvement in this plan lives in rendering: a render-side state machine
may *read* velocity, facing and ground state, and may never write back.
Hit-stop in its classic form (pausing the sim on impact) is **rejected
here by name**, because it would desync every tape; its honest substitute
is sprite-local: the struck thing holds its frame for 2-3 render frames
while the sim walks on. Any idea that cannot be expressed render-only does
not belong in this plan.

## Diagnosis — measured, not guessed

- The human turn is 1 frame (instant `flip_h`); there is no turn, skid,
  push, throw or catch state in `data/forms/human.json`, so shouldering a
  wall for 28 ticks plays `idle`, and throwing the blade shows nothing.
- Form parity failed in phase 4: human has 20 frames across 7 states;
  frog has 9 frames (idle 2, run 2, jump 2, fall/cling/hurt 1), bird 10
  (fly 4 is the only real cycle; idle, glide, jump, fall are 1 each),
  fish 10 (swim 4; idle 1). A frog that hops on 2 frames and a bird that
  glides on 1 read as tokens, not animals.
- Enemy sheets are thinner still (walker-class cycles of 2) and have had
  no phase-4 pass at all.
- `tile_anim.json` animates water, lava, the updraft, chain, clouds and
  the spore — and nothing in worlds 1 or 5; `gen_fx.py::build_tile_anim`
  still writes exactly its original grid, which the M3 integration already
  flagged as the extension point.
- Sprites sit on backgrounds with no edge discipline: no selective
  outline, so Kaya's silhouette dissolves against bright heights cloud and
  dark deeps comb alike. The ambience fix (entities draw over the
  darkness) proves how much silhouette is doing elsewhere.
- Landing from any height looks identical; there is no squash, no dust,
  no takeoff anticipation outside the jump strip.

## Phase A — the turn (the ask, and the hardest part)

A render-facing that lags gameplay-facing. New node-level state in
`player.gd` (never in forms): `render_facing`, plus a `turn_t` clock.

- When `facing` flips while grounded above a speed threshold (~40 px/s),
  `render_facing` holds the OLD direction and a 3-frame `turn` strip plays
  — plant, half-turn (the one hand-drawn asymmetric frame, face-on),
  push-off — over ~0.10 s, then `render_facing` snaps and the run cycle
  resumes. Below the threshold or airborne: a single half-turn frame,
  ~0.05 s. The turn NEVER delays physics; if the player re-reverses
  mid-turn the strip restarts from the half-turn frame, so mashing reads
  as twitchy, not laggy.
- A `skid` state when the axis opposes velocity above ~70 px/s on the
  ground: lean-back frame + dust puff at the heels, held until velocity
  crosses zero. Skid and turn chain naturally: skid -> turn -> run.
- Guard test: turn duration strictly below `coyote_time` + jump buffer,
  so the visual can never imply physics that is not there; and a unit
  test that the render state machine compiles against a recorded frame
  sequence (feed it a velocity/facing trace, assert the state sequence).
- Dust: three 4-frame one-shot particles (turn scuff, landing puff,
  takeoff kick) through the existing `fx.json`/`genfx.sh` pipeline.

New human frames: turn x2, skid x1, push x2 (shouldering — cycles while
`tick_break` runs), throw x2, catch x1, plus a 3-frame idle fidget played
every ~6 s. Sheet grows from 20 to ~31 frames; the generator and
`data/forms/human.json` move in lockstep, and `test_art_palette` already
guards that every named frame exists.

## Phase B — four shapes, for real (form and enemy parity)

Bring every form to the human's standard, each with its own turn:

- **Frog**: 4-frame hop with anticipation crouch, 2-frame cling with
  breathing, a tongue-blink idle, turn frame, and a wall-kick flash frame.
- **Bird**: 2-frame glide (feather ruffle), 2-frame perch idle with a
  head-tilt, a banking TURN frame pair (the bird is the form where
  turning reads most — it banks into the new direction), stall frame when
  stamina empties.
- **Fish**: turn frame (the fish about-faces constantly), 2-frame idle
  fin-sway, a burst frame for the first swim stroke, surface-break splash
  particle.
- **Enemies**: one phase-4 pass over the nine sheets — 4-frame walks,
  anticipation frames before every attack the boss gate's telegraph rules
  already require logically but the art never showed (charger wind-up,
  dropper tremble, shooter bloom), death poof unified. Bosses keep their
  18-frame contract; they gain only edge discipline from Phase C.

## Phase C — the beauty pass

- **Selective outline**: a generator post-pass on every sprite sheet —
  darkest-ramp-step edge pixels only where the sprite meets background
  (selout, not a black box outline), verified by a before/after pixel
  diff capped at the silhouette. One function in `palette.py`, applied at
  build time, so every sprite inherits it including the five bosses.
- **Ramp hue audit**: a tool that plots hue drift dark->light per ramp
  and flags ramps whose shadows merely darken (pixel-beauty rule: shadows
  shift cool, highlights shift warm). Fix the flagged ramps; the probes'
  pixel-hash tests version with the change.
- **Tile edge light, systematized**: the sunlit caps that levels hand-
  placed with `solid_alt` become an autotile rule in `tiles.py` — top
  edges of standable runs get the +1 ramp step, under-edges of overhangs
  get a one-pixel ambient-occlusion row. Hand-authored levels regenerate
  byte-identically ONLY where they already chose caps; elsewhere the
  pass is additive variants, and every world's probe shot is re-read.
- **Backdrops**: one new parallax plane per world (near-foreground
  grasses/combs/glass shards drifting past below the action), horizon
  gradient banding via the existing dither, and per-world motes in
  ambience (canopy pollen, ruin silt, heights spindrift, deeps spores
  already exist, nest embers).
- **Water and weather**: extend `build_tile_anim` past its original grid
  — sparkle frames on `water_top`, shoreline foam variant, ember-glow
  pulse on `obsidian_hot` (the one M4-style tint entry world 5 never
  got), canopy leaf-sway for world 1 which predates the system entirely.

## Phase D — juice, render-only

- Sprite-local hit-hold (2-3 render frames on the struck enemy), hit
  spark one-shot at the blade's contact point, blade afterimage trail
  (two ghost positions at 40%/20% alpha from the render history buffer).
- Switch flips get a 4-frame dissolve on the tiles that change (ghost
  art cross-fades to solid art); collision stays instant as shipped, and
  the fairness argument is the Heart's own telegraph beat — the dissolve
  must complete well inside it.
- Landing squash (render scale 1.15x/0.85y for 2 frames above a fall
  speed threshold, proportional), jump stretch on launch frame.
- Camera: 2 px landing dip on heavy falls, already-shipped shake audited
  for consistency.
- Death/level-enter transitions: the fade-from-black gains a 4-frame
  pixel-dissolve mask; the victory screen gets a slow ember drift behind
  its text (it is the last thing a player sees).

## Phase E — consistency and verification

- Contact sheets before/after per world (the 10-shot capture seqs all
  exist; re-run and grid them side by side) and a read of every one.
- The probe pixel-hash suites re-pin with the new sheets; every guard
  that exists keeps its teeth (frame-exists, art-depth, readable-layer).
- New guards: every form declares the canonical state set; every enemy
  attack has an anticipation strip at least 2 frames long; selout
  coverage (no sprite ships without the post-pass).
- The full stack at the end of every phase: 306 unit tests, 791+
  integration checks, 26 tapes verified, five gates. Phases are
  independently shippable in A -> B -> C -> D -> E order with F riding
  alongside B (it is sprite work on the same sheets), and A alone is
  the single highest-value change in the plan.

## Phase F — the idle dance

Stand still for five seconds and Kaya dances. An original piece of
choreography in the viral-short-video spirit — a hip-sway into a
two-step, one arm-wave, a little spin, back to idle — not a copy of any
named routine, because the project's first rule is that every asset is
original. The mechanics:

- The idle fidget clock from Phase A grows a second threshold: fidget at
  ~6 s becomes dance at 5 s (the fidget moves to ~12 s as the SECOND
  idle beat, so the two never collide).
- An 8-frame `dance` strip at 8 fps, played twice through, then back to
  `idle` until the clock re-arms (~15 s cooldown so it stays a treat).
  Any input, damage, or ground loss cancels it on the next frame — the
  dance must never cost a player one frame of responsiveness, which is
  the same rule the turn lives under.
- Render-only, like everything in this plan: the clock lives beside
  `render_facing` in `player.gd`, reads input and velocity, writes
  nothing. A tape that happens to idle five seconds dances through its
  replay and still verifies bit-identically.
- Human first; each animal form gets a 4-frame species take in Phase B
  (the frog bobs, the bird head-bangs, the fish loops a barrel roll) so
  the easter egg survives transformation.
- One guard test: the dance state is reachable only from `idle`, exits
  on any input bit, and its strip exists in every form's sheet.
- Captured for the record the way everything else is: a seq that waits
  it out and a short frame-grid in `shots/` proving the whole loop.

## Agent shape

Phase A is one agent (motion is one tightly-coupled system). Phase B
parallelizes four ways (one per form) plus one for enemies, with the
turn-state contract from A written into their briefs. Phase C
parallelizes per world after the two shared tools (selout, hue audit)
land first — the M4 lesson about foundation-before-authors applies
verbatim. D and E are one integration agent each. Every brief carries
the invariant at the top: tapes bit-identical, facing never written.
