#!/usr/bin/env python3
"""deeps_1 -- THE LIGHTLESS.  The opener of World 4, TERMITE DEEPS.

Self-contained: running this file under the project python writes
levels/deeps_1.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `deeps_1()` returning `(Grid, Kit)`,
which is the tuple that writer's `build()` helper audits before it writes
anything.

    source tools/env.sh && "$PYVENV" tools/worlds/deeps_1.py
    tools/prove.sh deeps_1

WHAT THIS LEVEL TEACHES
-----------------------
World 4's new verb is DARKNESS: a full-screen shade quad with one additive pool
following the player (src/world/ambience.gd, defaults in data/fx.json).  Nobody
has played in the dark before this level, so -- like every world opener in
docs/plan-20-levels.md -- the verb is introduced where getting it wrong costs
nothing, and only then over something that can hurt.

  1. THE MOUTH (screen A).  Kaya spawns human at (6,12) directly under a
     sinkhole: three columns of open shaft from row 1 down to the gallery she
     stands in, twelve tiles of it.  The floor is flat from col 1 to col 46 and
     the room is seven tiles tall here.  Nothing is asked and nothing patrols
     it.  What the screen says is "this is what lit looks like", and the
     ambience entry below grades its pools eastward -- 0.38, 0.24, 0.14 -- so
     the light is visibly BEHIND her before anything else happens.

  2. THE LIGHTLESS (screens A -> B).  At col 15 the roof drops from row 6 to
     row 8 and the daylight stops.  The same floor continues for thirty-one
     more columns under four tiles of headroom, with no authored light on it at
     all: the only thing that moves with her is the pool she carries.  This is
     the safe room, and it is safe on purpose -- flat floor, no gap, no hazard,
     nothing patrolling.  The one thing in it that is not dark is a patch of
     deep_fungus at (30,9) with a gem under it, which is the first time a pool
     of light means "something is here".

  3. THE MARKED HOLE (screen B).  The floor's cap stops at col 39 and the
     descent shaft is cols 40-41.  A hole in the floor in the dark is a leap of
     faith, so it is signed twice over: fungus at (39,9) and (42,9) flank the
     mouth on the roof, and two more at (41,15) and (41,19) glow inside the
     shaft, so looking down it shows a space rather than a void.  The drop is
     fourteen tiles onto unbroken floor with no hazard under it -- getting it
     wrong still costs nothing -- and a deep_ladder runs the whole height at
     col 40 for anyone who would rather climb.

     Past the hole the tunnel goes two tiles further to a wall of
     `luminous_wall` at col 44 with a heart behind it.  That is the level's one
     concession to the NEXT level's verb: it is the only breakable tile in the
     level, it is off every hop, and it glows, so the first breakable wall in
     the game is met as a light you cannot reach rather than as a puzzle.
     deeps_2 CHEW THROUGH is where it becomes a verb.

     A BREAKABLE IS A WALL TO THE GATE, and that is measured rather than
     assumed: the M4 foundation pass put a one-column `rubble` plug -- the
     cheapest breakable there is, 0.18 s -- across a corridor the prover
     otherwise crossed in 36 expansions, and the run burned its whole 50,000
     budget and failed.  The search alphabet has no ATTACK in it and the
     snapshots carry no broken-tile state.  So the declared route here reaches
     the exit without breaking anything, and every breakable in World 4 is
     player-facing only: foreshadowing, treasure, a shortcut.  `luminous_wall`
     is also the right tile rather than the pretty one -- 270 deep_glowwall,
     which the deeps legend binds to 'c', declares no `break_hold` at all and
     opens only to the blade, so it is a sealed door to the frog and the bird.
     `Kit.glow_wall()` exists to make that choice for you and this level lets
     it.

  4. THE SPORE WALK (screen D).  The same dark, now with something in it.  Two
     pits of deep_spore in the lower gallery's floor, and the fairness argument
     for both is that THEY are the light: `emissive` puts a pool on tile 267, so
     a spore pit in an unlit corridor announces itself from further away than
     Kaya's own lantern reaches.  A dark hazard you cannot see is not a lesson,
     it is a coin toss.  One enemy_walker paces the four tiles between the two
     pits, which is what makes the second jump an ask rather than a repeat.

  5. THE BROOD SHAFT (screen C).  The floor runs west across the vertical seam
     into a chamber twelve tiles tall.  `pad_frog` is at (19,26), three tiles
     inside it, and above it three treads of deep_shelf climb west in 3-tile
     steps -- the frog's measured ceiling, and one tile more than the human's,
     so the pad is load-bearing rather than decoration.  The exit sits on a rock
     shelf at (2,17) under the only warm pool in the screen.  The last thing the
     level teaches is the thing it has been teaching all along: in the dark, you
     walk towards the light that is not yours.

THE MEASUREMENTS THIS GEOMETRY IS BUILT ON
------------------------------------------
* THE LANTERN IS 74 px, which is 4.6 tiles (data/fx.json "darkness").  That is
  the number the route's mark spacing is checked against: `_self_checks` fails
  the build unless every consecutive pair of route waypoints is either inside
  4.6 tiles of each other -- so the next one is already lit when you leave --
  or the destination has a light source within LIGHT_TILES of it.  Eight of the
  eleven hops are the second case, which is the level: you cross the dark
  towards a landmark, you do not grope along it.

* DARKNESS IS ONE ALPHA FOR THE WHOLE LEVEL.  `Ambience.shade` is a single quad
  at one alpha drawn over every screen; there is no per-region dimmer and there
  should not be one.  So "starts lit and descends into the dark" is built out of
  authored POOLS, not out of the shade: screen A carries six of them and screens
  B and D carry none.  Everything that glows below the mouth is a tile, which is
  also why it can be captured, measured and argued about.

* A GEM IS A LANDMARK, which the forced-dark capture
  (shots/deeps_1_k_lantern.png, `tools/shot.sh --darkness=0.88`) showed and
  this file did not plan.  `AmbienceLayer` draws the shade over the TILES and
  under the ENTITIES, so at 0.88 the gallery floor is invisible four tiles from
  Kaya and the gems on it are still at full contrast, brighter than anything
  else on the screen.  The sixteen gems here are therefore a second wayfinding
  layer under the eleven fungus tufts, and they are placed along the route on
  purpose: (22,12), (30,12) and (37,12) are the three stepping stones across
  the lightless gallery, and (25,26), (32,26) and (39,26) the three across the
  spore walk.  It is not load-bearing -- the pool-spacing check below ignores
  them, because a collected gem stops being a landmark -- but it is the reason
  the dark room does not feel empty on the way through it.

* DARKNESS IS VISUAL ONLY, and that is a constraint rather than an omission.
  tests/test_verbs_darkness.gd runs the same movement lit and dark and demands
  the two agree to the last float, because the Route Prover cannot see.  So
  nothing in this file's geometry depends on light, and `tools/prove.sh` proves
  exactly the level a lit version of it would be.  What the prover does NOT
  prove is that a human can see where to go -- that is what the pool spacing
  check and the captures are for.

* HUMAN rise 2, gap 3; FROG rise 3, gap 3 (world_kit.LIMITS, measured).  Every
  step in the frog stair is 3 and every pit is 2 tiles wide, so the human
  crosses both pits at a 3-column displacement and cannot climb any tread.

* THE PITS ARE ONE AND TWO ROWS DEEP, not bottomless.  Pit 1 (cols 35-36) is a
  single row of spore at row 27 over solid fill: fall in, take the hit, climb
  one tile out.  Pit 2 (cols 29-30) is two rows, so it costs the human her full
  2-tile rise to leave.  This is an opener and a hazard that kills outright
  teaches nothing; jungle_1's spike pit is the same shape and the same bargain.

WHERE THE WALKED FLOORS SIT, AND THE TWO SEAMS
----------------------------------------------
`CameraController` picks its screen from the body's CENTRE, so a 22 px body on a
floor whose cap row is a multiple of 15 has its feet exactly on the horizontal
seam and its centre on the screen ABOVE -- which never draws the floor it is
standing on.  That is the defect ruins_4 shipped.  The stand rows here are 12
(cap 13), 26 (cap 27), 23 (shelf 24), 20 (shelf 21) and 17 (cap 18, shelf 18);
`_self_checks` fails the build if any claimed stand row has (row + 1) % 15 == 0.

The vertical seam is x=400, between cols 24 and 25.  Two hops cross it and both
are FLAT WALKS along unbroken floor -- `threshold` -> `dark_gallery` on row 13's
cap and `pit_2_west` -> `pad_frog` on row 27's -- with four or more tiles of
plain floor either side, so the 0.12 s flip freeze lands while she is walking.
No jump in the level leaves one screen and lands on another: pit 1 spans cols
35-36 and pit 2 cols 29-30, both wholly inside screen D, and the frog stair is
wholly inside screen C.  `_self_checks` re-derives that from the route rather
than trusting this paragraph.

The horizontal seam is y=240, between rows 14 and 15, and the route crosses it
once: `shaft_head` -> `shaft_foot`, straight down a two-column shaft with a
ladder in it.  A flip freeze mid-FALL is harmless -- she resumes falling in the
same column, with nothing to miss -- which is why the descent is a shaft and not
a staircase of ledges.  That hop is the one entry in SEAM_EXEMPT and the reason
is recorded there.

THE PALETTE, AND WHY IT NAMES JUNGLE TILES
------------------------------------------
`world_kit.Palette.char()` resolves a tile NAME through the flat `legend` key of
data/level_legend.json, which ADR 002's amendment leaves as the *jungle* view
because tools/reachability.py and tools/build_hub.py read it directly.  So
world_kit's own DEEPS palette -- which names deep_earth, deep_packed,
deep_chitin -- finds no character for any of them and falls through to an
understudy, emitting whatever character the understudy owns.  The memory note
"world_kit ruins palette emits wrong stone" is that failure, in World 2.

So this palette names, for each role, the jungle tile that OWNS the character
the deeps tileset binds to the art we want.  Two of them are worth reading
twice, because the deeps legend binds the two fill characters the opposite way
round from the jungle:

    role "packed"  -> jungle `stone`  -> 's' -> 271 deep_packed   (the bulk)
    role "block"   -> jungle `dirt`   -> 'd' -> 263 deep_chitin   (the lining)

That inversion is data/level_legend.json's choice, not this level's, and the
names are what decide it: world_kit's DEEPS palette asks for deep_packed as the
fill and deep_chitin as the second solid, so this palette asks for the
CHARACTERS that resolve to those two tiles under `"tileset": "deeps"`.  The
result is that `Palette.missing()` is empty and `Palette.substituted` stays
EMPTY, so `Kit.audit(strict_verbs=True)` is meaningful and the JSON carries
deeps ids rather than jungle ones.

`glowwall` needs no trick: 'O' is a `shared` character and `luminous_wall` (214)
means the same tile in every world.  It is also the right one -- 270
deep_glowwall declares no `break_hold`, so only a weapon opens it, and World 4
leans on the frog, which has none.  `Kit.glow_wall()` exists to make that choice
for you.

'r' -> 269 deep_fungus IS THIS LEVEL'S LIGHT, AND IT IS ON THE FG LAYER
----------------------------------------------------------------------
Every other world puts its background accent on the bg layer (heights_1 draws
'r' clouds there).  This one cannot: `AmbienceLayer._collect_emissive` scans
`world.get_fg` and nothing else, so an emissive tile on the bg layer emits
nothing.  deep_fungus has no flags at all -- it is not solid, not a hazard, not
a one-way -- so an 'r' on the fg layer is air that glows, which is exactly what
is wanted and costs the geometry nothing.

There is no kit role for it ('r' belongs to the `bg` role in the jungle, and
this palette needs `bg` for 'L'), so the eleven tiles in FUNGUS are written with
`g.put(x, y, "r")` directly and then re-checked against the finished grid by
`_self_checks`: still 'r', still non-solid, and still touching solid or one-way
rock, because a glowing tuft floating in the middle of a room reads as something
you can land on.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                      # noqa: E402
import world_kit                                        # noqa: E402
from world_kit import Kit, Palette, Probe               # noqa: E402

LEVEL_ID = "deeps_1"
LEVEL_NAME = "THE LIGHTLESS"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the deeps role character.
## See the module docstring: this is a character map, not an art claim, and the
## art comes from `"tileset": "deeps"` at load time.
DEEPS_W4 = Palette("termite_deeps", {
    "bg": "bg_leaves",              # 'L' -> 262 deep_comb
    "solid": "grass_top",           # '#' -> 260 deep_earth
    "solid_alt": "stone_mossy",     # 'S' -> 261 deep_crust
    "packed": "stone",              # 's' -> 271 deep_packed   (the bulk fill)
    "block": "dirt",                # 'd' -> 263 deep_chitin   (the shaft lining)
    "oneway": "wood_platform",      # '=' -> 266 deep_shelf
    "ladder": "vine",               # '|' -> 268 deep_ladder
    "hazard": "spikes",             # '^' -> 267 deep_spore
    "breakable": "crate",           # 'c' -> 270 deep_glowwall (weapon-only, unused)
    "decor": "tree_trunk",          # 'T' -> 265 deep_root
    "void": "bg_dark",              # 'X' -> 264 deep_void
    "glowwall": "luminous_wall",    # 'O'  shared, 214, break_hold 0.4
    "shoulder": "termite_wall",     # 'm'  shared, 213 (unused here; deeps_2's)
    "rubble": "rubble",             # 'o'  shared
    "water": "water",               # '~'  shared (this level is dry)
    "water_top": "water_top",       # 'w'  shared
})

# ---------------------------------------------------------------- the shape
## Every number the rest of the file and the checks read, in one place, because
## "generous floors where visibility is lowest" is a claim about arithmetic.
GALLERY_STAND = 12              # upper gallery: cap row 13
GALLERY_CAP = 13
GALLERY_X0, GALLERY_X1 = 1, 46
MOUTH_X1 = 14                   # the lit end: roof at row 5 instead of row 8
SINK_X0, SINK_X1 = 5, 7         # the sinkhole, rows 1-5

SHAFT_X0, SHAFT_X1 = 40, 41     # the descent, rows 13-22
LADDER_X = 40

CELL_WALL_X = 44                # the luminous wall, gallery rows 9-12
CELL_X0, CELL_X1 = 45, 46       # the heart behind it

LOWER_STAND = 26                # lower gallery + brood shaft floor: cap row 27
LOWER_CAP = 27
CORRIDOR_X0, CORRIDOR_X1 = 21, 41
CHAMBER_X0, CHAMBER_X1 = 1, 20
CHAMBER_TOP = 15                # the brood shaft's roof

## (x0, width, rows of spore).  Both are 2 tiles wide, so the human crosses
## each at a 3-column displacement: LIMITS["human"]["gap"] is 3.
PITS = [(35, 2, (27,)), (29, 2, (27, 28))]

## The frog stair: three treads of deep_shelf climbing WEST in 3-tile steps.
STAIR_X, STAIR_Y = 15, 24
STAIR_COUNT, STAIR_RISE, STAIR_RUN, STAIR_W = 3, 3, 5, 4

EXIT_SHELF = (1, 18, 4)         # x, cap row, width -- stand row 17
EXIT_TILE = (2, 17)
PAD_TILE = (19, 26)

## Every deep_fungus tile, which in this level means every light that is not
## the player's own and not authored in data/ambience.json.  `_self_checks`
## re-checks each one against the finished grid.
FUNGUS = [
    (30, 9),                    # the gem in the middle of the lightless gallery
    (39, 9), (42, 9),           # flanking the descent shaft's mouth
    (41, 15), (41, 19),         # inside the shaft: it is a space, not a void
    (41, 23),                   # the shaft's foot, seen from above
    (14, 24), (9, 21),          # the west lip of treads 1 and 2: the launch point
    (1, 16), (1, 20), (1, 24),  # the brood shaft's west wall, under the exit
]

## Rock that catches the daylight: deep_crust instead of deep_earth on every
## exposed face inside the mouth.  Cosmetic only -- 260 and 261 are both plain
## `solid`, the same tile to every flag-reading checker.
##
## Cols 1-15 and rows 1-13, which is the mouth and nothing else.  The first
## draft ran to row 14 and col 18 and crusted two faces the daylight never
## touches: the roof of the lightless gallery at (15..18, 8) and the CEILING OF
## THE BROOD SHAFT at row 14, twelve rows underground.  A band that says "this
## rock is lit" has to stop where the light does.
CRUST_BOX = (1, 1, 15, 13)      # x, y, w, h

## CHEWED, NOT CUT.  Both galleries are four tiles tall and thirty-odd columns
## long, and a tunnel of constant section is a corridor in a shooter, not a
## termite gallery: the first capture of screen B was eight rows of unbroken
## slab over a flat strip of floor.  Two kinds of relief, and the difference
## between them is whether a body can get into them.
##
## NICHES open downward into a gallery's ceiling.  They have no floor of their
## own -- the row under each one is the gallery's air -- so nothing can stand in
## one and `tests/test_level_validity.gd`'s pocket check skips them, which is
## what makes a 2-tile-tall niche legal where a 2-tile-tall ROOM would be a
## squeeze.  `_self_checks` re-derives exactly that.
NICHES = [
    (20, 7, 3, 2), (27, 6, 3, 3), (34, 7, 3, 2),       # the lightless gallery
    (24, 21, 3, 2), (31, 20, 3, 3), (36, 21, 3, 2),    # the spore walk
]

## CELLS are sealed brood chambers inside the rock: carved on the fg so the
## background comb shows through, and walled on every side, so they are
## scenery and not geometry.  `_self_checks` fails the build if any one of them
## has so much as a corner open, because a "decorative" pocket that touches the
## playable space is a room the prover has to search and the validators have to
## approve.  Two tiles tall minimum, for the same reason a niche is.
CELLS = [
    (11, 2, 3, 2), (17, 3, 3, 2), (21, 1, 3, 2),                  # over the mouth
    (27, 2, 4, 2), (33, 4, 3, 2), (40, 2, 3, 2), (44, 4, 3, 2),   # over the gallery
    (24, 17, 3, 2), (30, 16, 4, 2), (35, 16, 3, 2),               # under the walk
    (44, 16, 3, 2), (45, 20, 3, 2),                               # east of the shaft
]

## The dead end east of the descent, rows 24-26 under the sealed cell.  It is
## here because screen D's east quarter was otherwise a rock block with the
## shaft's foot pinned to the left of it, and because a level that teaches
## "light means something is there" should put something there.
CRAWL = (42, 24, 5, 3)          # x, y, w, h -- cap row 27


def _crust(k):
    """Paint deep_crust on every rock face inside the mouth that the daylight
    can actually fall on.

    A sealed brood cell is air the light never reaches, so its rim does NOT
    count as an exposed face: without that exclusion the three cells inside
    CRUST_BOX came out lined with lit stone and the nine outside it did not,
    which is a band that means nothing.
    """
    g, p = k.g, Probe(k.g)
    cap, fill, alt = k.ch("solid"), k.ch("packed"), k.ch("solid_alt")
    sealed = {(xx, yy)
              for (cx, cy, cw, ch) in CELLS
              for yy in range(cy, cy + ch)
              for xx in range(cx, cx + cw)}
    x, y, w, h = CRUST_BOX
    lit = []
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if g.fg[yy][xx] not in (cap, fill):
                continue
            if any(not p.solid(xx + dx, yy + dy)
                   and (xx + dx, yy + dy) not in sealed
                   for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))):
                lit.append((xx, yy))
    for xx, yy in lit:
        g.put(xx, yy, alt)


def deeps_1():
    g = Grid(W, H, tileset="deeps")
    k = Kit(g, DEEPS_W4, form="human")

    # ------------------------------------------------------------- the rock
    # Carved rather than built.  `Kit.fill_solid` says why, and TERMITE DEEPS is
    # the world it was written for: a tunnel cut out of rock has a tiny
    # reachable state space, so a prover hop that fails exhausts its frontier
    # instead of spending its whole budget wandering open ground.
    k.fill_bg("bg")
    k.fill_solid("packed")
    k.shell(1, "solid")

    # ============================================ 1-2. THE MOUTH AND THE DARK
    # One floor from col 1 to col 46, four tiles of headroom, and seven at the
    # lit end.  The roof step at col 15 is the whole of beat 2's staging: the
    # daylight stops where the ceiling comes down, and she keeps walking.
    k.corridor(GALLERY_X0, GALLERY_STAND,
               GALLERY_X1 - GALLERY_X0 + 1, h=4)          # rows 9-12
    k.clear_rect(GALLERY_X0, 6, MOUTH_X1 - GALLERY_X0 + 1, 3)   # rows 6-8
    k.clear_rect(SINK_X0, 1, SINK_X1 - SINK_X0 + 1, 5)         # the sinkhole

    # The cap, in two runs: cols 40-41 are left uncapped and that hole IS the
    # descent.  Nothing else in the level has a floor missing from it.
    k.floor(GALLERY_X0, GALLERY_CAP, SHAFT_X0 - GALLERY_X0, depth=1)   # cols 1-39
    k.floor(SHAFT_X1 + 1, GALLERY_CAP, GALLERY_X1 - SHAFT_X1, depth=1)  # cols 42-46
    k.mark("threshold", 15, GALLERY_STAND)
    k.mark("dark_gallery", 30, GALLERY_STAND)
    k.mark("shaft_head", SHAFT_X0 - 1, GALLERY_STAND)

    # ========================================= 3. THE MARKED HOLE, AND THE WALL
    k.clear_rect(SHAFT_X0, GALLERY_CAP, 2, 10)            # the shaft, rows 13-22
    # The shaft's lining, cosmetic: deep_chitin either side so the descent reads
    # as something that was chewed rather than as a crack in the earth.
    k.rect(SHAFT_X0 - 1, GALLERY_CAP + 1, 1, 9, "block")
    k.rect(SHAFT_X1 + 1, GALLERY_CAP + 1, 1, 9, "block")

    # The level's ONE breakable tile, and the only thing in it tools/prove.sh
    # cannot model: `Kit.glow_wall` files that in Kit.unproven, loudly.  It
    # plugs the gallery's last two columns from floor to roof (rows 9-12), it is
    # off every hop, and the two tiles of floor west of it (cols 42-43) are
    # where you stand to look at it.
    k.glow_wall(CELL_WALL_X, GALLERY_STAND, 4)

    # ============================================= 4. THE SPORE WALK (screen D)
    k.corridor(CORRIDOR_X0, LOWER_STAND,
               CORRIDOR_X1 - CORRIDOR_X0 + 1, h=4)        # cols 21-41, rows 23-26
    k.floor(CORRIDOR_X0, LOWER_CAP,
            CORRIDOR_X1 - CORRIDOR_X0 + 1, depth=1)

    # ============================================ 5. THE BROOD SHAFT (screen C)
    k.clear_rect(CHAMBER_X0, CHAMBER_TOP,
                 CHAMBER_X1 - CHAMBER_X0 + 1, LOWER_CAP - CHAMBER_TOP)
    k.floor(CHAMBER_X0, LOWER_CAP, CHAMBER_X1 - CHAMBER_X0 + 1, depth=1)

    # The pits, drawn AFTER both floors so nothing caps them back over.  A row
    # of spore replaces the cap; the fill under it stays, so each pit has a
    # solid bottom and a measured price (see the docstring).
    for x0, w, rows in PITS:
        for row in rows:
            k.rect(x0, row, w, 1, "hazard")
        # `Kit.gap` checks the width against LIMITS and files a step claim, so
        # audit() re-checks the arc against the finished grid.
        k.gap(x0, LOWER_STAND, w, form="human",
              landing_w=x0 - CORRIDOR_X0)
    k.mark("shaft_foot", SHAFT_X0, LOWER_STAND)
    k.mark("pit_1_west", PITS[0][0] - 1, LOWER_STAND)
    k.mark("pit_2_west", PITS[1][0] - 1, LOWER_STAND)

    # The dead end east of the shaft's foot.
    cx, cy, cw, ch = CRAWL
    k.corridor(cx, cy + ch - 1, cw, h=ch)
    k.floor(cx, LOWER_CAP, cw, depth=1)

    # The exit shelf, two rows thick so it reads as rock and not as a sheet.
    ex, ey, ew = EXIT_SHELF
    k.floor(ex, ey, ew, depth=2)

    # The frog stair.  `Kit.stair` checks the rise against the frog's MEASURED
    # ceiling before it draws a tile: 3 is the kit's limit and a 4-tile rung is
    # the jungle_4 defect (provable, unplayable).  run 5 against width 4 leaves
    # a 1-tile gap between treads, which is nothing to the frog -- its enormous
    # jump buys height, not distance.
    treads = k.stair(STAIR_X, STAIR_Y, STAIR_COUNT, STAIR_RISE, STAIR_RUN,
                     STAIR_W, form="frog", dx=-1)
    # The one step the stair helper does not file, because it is the step onto
    # the bottom tread from the chamber's own floor.
    world_kit.check_rise(LOWER_STAND - treads[0][1], "frog",
                         "brood shaft floor -> tread_1")
    for i, (tx, stand, tw) in enumerate(treads):
        k.mark("tread_%d" % (i + 1), tx + tw - 1, stand, form="frog")

    # The ladder, drawn LAST of the solid geometry: a climb written before the
    # carve that crosses it is the draw-order bug audit() exists for, and this
    # column runs through the gallery's cap, the shaft and the corridor.
    # landing="left" because (39,12) is the gallery floor and (41,12) is open
    # air over the hole.
    k.climb(LADDER_X, GALLERY_STAND, LOWER_STAND, landing="left")

    # ------------------------------------------------------- chewed, not cut
    # Drawn after every floor and before the light, so a niche cannot be capped
    # back over and a cell cannot be carved through.
    for (x, y, w, h) in NICHES:
        k.clear_rect(x, y, w, h)
    for (x, y, w, h) in CELLS:
        k.clear_rect(x, y, w, h)

    # -------------------------------------------------------------- the light
    # See the docstring: fg, not bg, because _collect_emissive scans the fg.
    for x, y in FUNGUS:
        g.put(x, y, "r")
    _crust(k)

    # ------------------------------------------------------------- dressing
    # Open void behind every carved room, then background roots hugging the
    # rock faces.  All on the bg layer, so none of it collides -- and none of it
    # stands in open air, because a dark column in a dark room reads as
    # something you can land on.
    for (x, y, w, h) in [(1, 1, 18, 12), (1, 9, 46, 4), (40, 13, 2, 10),
                         (21, 23, 21, 4), (1, 15, 20, 12), (42, 24, 5, 3)]:
        g.rect(x, y, w, h, "X", "bg")
    for (x, h, y) in [(2, 7, 6), (13, 7, 6), (20, 4, 9), (27, 4, 9),
                      (34, 4, 9), (43, 4, 9), (22, 4, 23), (38, 4, 23),
                      (2, 11, 15), (19, 11, 15), (11, 4, 23)]:
        g.rect(x, y, 1, h, "T", "bg")

    # ------------------------------------------------------------- entities
    g.ent("player_spawn", 6, GALLERY_STAND)
    g.ent("pad_frog", *PAD_TILE)
    g.ent("exit", *EXIT_TILE)

    # NOTHING PATROLS THE TEACHING ROOMS, and that is a decision rather than an
    # oversight -- the same one heights_1 records.  Beats 1 to 3 promise that
    # the dark by itself costs nothing, and an enemy anywhere on the upper
    # gallery's unbroken 46-tile floor eventually walks the whole of it and
    # arrives wherever she is (walker.json: 32 px/s, turn_at_ledge,
    # chase_range 96).  So the inhabitants live below the hazard lesson.
    #
    # The one in the lower gallery is bounded by the level's own geometry:
    # turn_at_ledge turns a walker at a floor tile with no floor beyond it, and
    # a spore pit is exactly that, so (33,26) paces cols 31-34 and nothing else
    # -- four tiles, between the two pits, which is what makes the jump over
    # pit 2 an ask instead of a repeat of pit 1.
    g.ent("enemy_walker", 33, LOWER_STAND)
    g.ent("enemy_walker", 10, LOWER_STAND)

    for (x, y) in [(2, 12), (9, 12), (12, 12),               # the mouth
                   (22, 12), (30, 12), (37, 12),             # the lightless walk
                   (43, 12), (46, 12),                       # past the hole
                   (25, 26), (32, 26), (39, 26), (45, 26),   # the spore walk
                   (14, 26), (17, 23), (12, 20), (7, 17),    # the brood shaft
                   (4, 17)]:                                 # the exit shelf
        g.ent("gem", x, y)
    g.ent("heart", 45, GALLERY_STAND)     # behind the luminous wall
    g.ent("heart", 3, LOWER_STAND)        # on the brood shaft's floor

    # ------------------------------------------------- the route (ADR 005)
    # Eleven hops, all short.  Three of them are flat walks and exist only so
    # the ones that are the level start from a known state; the two that cross
    # the vertical seam are deliberately among the flat walks.
    g.route("spawn", "threshold", form="human")          # out of the daylight
    g.route("threshold", "dark_gallery", form="human")   # crosses x=400, walking
    g.route("dark_gallery", "shaft_head", form="human")
    g.route("shaft_head", "shaft_foot", form="human")    # the drop, see SEAM_EXEMPT
    g.route("shaft_foot", "pit_1_west", form="human")    # over pit 1
    g.route("pit_1_west", "pit_2_west", form="human")    # over pit 2
    g.route("pit_2_west", "pad_frog", form="human")      # crosses x=400, walking
    g.route("pad_frog", "tread_1", form="frog")          # 3 up: the human cannot
    g.route("tread_1", "tread_2", form="frog")
    g.route("tread_2", "tread_3", form="frog")
    g.route("tread_3", "exit", form="frog")              # west onto the lit shelf
    return g, k


# ======================================================================== light
## The data/ambience.json entry this level is designed around, kept HERE because
## that file belongs to the integration pass and because the pool positions are
## a fact about the geometry above.  `main()` prints it; `_self_checks` holds the
## route to it.  Reading it as data rather than as prose is the only way the
## fairness rule below can be checked at all.
AMBIENCE = {
    "_note": (
        "THE LIGHTLESS. World 4's teacher. `darkness` is one alpha for the "
        "whole level, so 'starts lit and descends into the dark' is built out "
        "of authored pools rather than out of the shade: six in the mouth, "
        "graded eastward (0.58 at the sinkhole's foot, 0.38, then 0.22 at the "
        "threshold) so the daylight is visibly behind her before anything is "
        "asked. Screens B and D carry no authored light at all -- everything "
        "that glows down there is a tile, which is why it can be captured and "
        "argued about. deep_fungus (269) marks the route, luminous_wall (214) "
        "marks the secret she cannot open yet, and deep_spore (267) marks the "
        "only two things that can hurt her: a dark hazard you cannot see is "
        "not a lesson, it is a coin toss. The exit gets the one warm pool in "
        "screen C, because a lit doorway is what this level teaches her to "
        "look for. darkness 0.88 / vignette 0.40 and the 214 and 267 entries "
        "are World 4's measured house recipe, not this level's choices."),
    "world": "deeps",
    "air": {"ramp": "water", "step": 1, "alpha": 0.42},
    "bg_tint": {"ramp": "water", "step": 3, "mix": 0.80, "scale": 0.44},
    "fg_tint": {"ramp": "water", "step": 5, "mix": 0.35, "scale": 0.86},
    "vignette": 0.40,
    "darkness": 0.88,
    "lights": [
        {"x": 6, "y": 2, "radius": 112, "ramp": "gold", "step": 6,
         "intensity": 0.72},
        {"x": 6, "y": 6, "radius": 96, "ramp": "gold", "step": 6,
         "intensity": 0.66},
        {"x": 6, "y": 11, "radius": 88, "ramp": "gold", "step": 5,
         "intensity": 0.58},
        {"x": 2, "y": 11, "radius": 64, "ramp": "gold", "step": 5,
         "intensity": 0.34},
        {"x": 12, "y": 11, "radius": 72, "ramp": "gold", "step": 5,
         "intensity": 0.38},
        {"x": 17, "y": 11, "radius": 60, "ramp": "gold", "step": 4,
         "intensity": 0.22},
        {"x": 19, "y": 25, "radius": 48, "ramp": "grass", "step": 5,
         "intensity": 0.40, "flicker": 0.22},
        {"x": 2, "y": 16, "radius": 76, "ramp": "gold", "step": 6,
         "intensity": 0.58, "flicker": 0.10},
    ],
    "emissive": {
        # 214 and 267 are the foundation pass's MEASURED World 4 values, taken
        # verbatim so five levels light their shared tiles the same way. 269 is
        # this level's own, in the same idiom: deep_fungus is what marks a
        # route, and only THE LIGHTLESS uses it that way.
        "269": {"ramp": "grass", "step": 6, "intensity": 0.42, "radius": 28,
                "lift": 4},
        "214": {"ramp": "gold", "step": 6, "intensity": 0.40, "radius": 30},
        "267": {"ramp": "grass", "step": 5, "intensity": 0.30, "radius": 26,
                "lift": 5},
    },
}

## data/fx.json "darkness": radius 74.0 px.  4.625 tiles.
LANTERN_TILES = 74.0 / 16.0
## How close a landmark has to be to the FAR end of a hop for the hop to be
## fair in the dark.  Five tiles: the pool textures here are radius 24-112 px,
## so a light within five tiles of where you are going is a light you can see
## from where you are standing.
LIGHT_TILES = 5.0

## Route hops allowed to change screen without being a flat walk, and why.
SEAM_EXEMPT = {
    ("shaft_head", "shaft_foot"):
        "a fall, not a hop: fourteen tiles straight down a two-column shaft "
        "with a ladder in it. The 0.12 s flip freeze at y=240 leaves her "
        "falling in the same column with nothing to miss, which is exactly "
        "why the descent is a shaft rather than a staircase of ledges.",
}


# --------------------------------------------------------------------- checks
def _screen(x, y):
    """Which 25x15 screen `CameraController` puts a body standing at (x,y) on.

    The centre of a 22 px body whose feet are on row y+1 is at
    (x*16 + 8, y*16 + 5) -- the same arithmetic the camera does.
    """
    return ((x * 16 + 8) // 400, (y * 16 + 5) // 240)


def _waypoints(g):
    where = dict(g.marks)
    for e in g.entities:
        if e["type"] == "player_spawn":
            where["spawn"] = {"x": e["x"], "y": e["y"]}
        elif e["type"].startswith("pad_") or e["type"] == "exit":
            where[e["type"]] = {"x": e["x"], "y": e["y"]}
    return where


def _lights(g):
    """Every light in the finished level, in tile coordinates.

    Authored pools out of AMBIENCE, plus every emissive tile actually present
    in the fg layer -- which is the point of reading the ambience entry as data
    rather than writing it in a comment.
    """
    out = [(float(p["x"]), float(p["y"])) for p in AMBIENCE["lights"]]
    emit = {ch for ch in ("r", "^", "O")}
    for y in range(g.h):
        for x in range(g.w):
            if g.fg[y][x] in emit:
                out.append((float(x), float(y)))
    return out


def _self_checks(g, k):
    p = Probe(g)
    bad = []

    # (a) A standable tile with one tile of headroom reads as a passage and
    # behaves as a wall (defect 2).  tests/test_level_validity.gd checks exactly
    # this; catching it here costs milliseconds instead of a whole Godot boot.
    for y in range(g.h):
        for x in range(g.w):
            if p.solid(x, y):
                continue
            if not (p.solid(x, y + 1) or p.oneway(x, y + 1)):
                continue
            if p.clear(x, y, 2):
                continue
            for dx in (-1, 1):
                if not p.solid(x + dx, y) and p.clear(x + dx, y, 2):
                    bad.append("(%d,%d) is standable with one tile of headroom "
                               "and reachable from beside it" % (x, y))
                    break

    # (b) Everything the player must touch needs a body's worth of room over it,
    # and must not stand on a floor the screen it is drawn on does not contain
    # (the defect ruins_4 shipped).
    must = {"exit", "pad_frog", "player_spawn", "gem", "heart", "enemy_walker"}
    for e in g.entities:
        if e["type"] not in must:
            continue
        x, y = e["x"], e["y"]
        if not p.clear(x, y, 2):
            bad.append("%s at (%d,%d) has no two tiles of headroom"
                       % (e["type"], x, y))
        if (p.solid(x, y + 1) or p.oneway(x, y + 1)) and (y + 1) % 15 == 0:
            bad.append("%s at (%d,%d) stands on cap row %d, a screen boundary: "
                       "its centre lands on the screen above and the floor is "
                       "never drawn" % (e["type"], x, y, y + 1))
    for kind, c in k.claims:
        if kind == "stand" and (c["y"] + 1) % 15 == 0:
            bad.append("%s: stand row %d sits on cap row %d, a screen boundary"
                       % (c["why"], c["y"], c["y"] + 1))

    # (c) NO ON-FOOT HOP CROSSES A SCREEN SEAM MID-JUMP.  A hop whose two ends
    # are on different screens has to be a flat walk along unbroken standable
    # floor, or be named in SEAM_EXEMPT with a reason.  The camera freezes the
    # sim for the length of every flip, and a freeze in mid-air is the feel
    # defect neither prove.sh nor the tape replay can see.
    where = _waypoints(g)
    for hop in g.hops:
        a, b = where.get(hop["from"]), where.get(hop["to"])
        if a is None or b is None:
            continue
        if _screen(a["x"], a["y"]) == _screen(b["x"], b["y"]):
            continue
        key = (hop["from"], hop["to"])
        if key in SEAM_EXEMPT:
            continue
        if a["y"] != b["y"]:
            bad.append("route hop '%s' -> '%s' changes screen and changes row: "
                       "either make it a flat walk or justify it in SEAM_EXEMPT"
                       % key)
            continue
        y = a["y"]
        for x in range(min(a["x"], b["x"]), max(a["x"], b["x"]) + 1):
            if not p.standable(x, y):
                bad.append("route hop '%s' -> '%s' crosses a screen seam and "
                           "(%d,%d) is not standable, so it is a jump and not a "
                           "walk" % (hop["from"], hop["to"], x, y))
                break

    # (d) THE DARKNESS RULE, and it is the only check in this file that is about
    # World 4 rather than about the engine.  A dark level is fair when you never
    # have to leave a place you can see for a place you cannot: so every hop's
    # destination is either already inside the lantern (4.6 tiles) or has a
    # light source within LIGHT_TILES of it.  Checked against AMBIENCE and
    # against the emissive tiles actually in the grid, so moving a fungus tuft
    # or deleting a pool fails the build.
    lights = _lights(g)
    for hop in g.hops:
        a, b = where.get(hop["from"]), where.get(hop["to"])
        if a is None or b is None:
            continue
        span = ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5
        if span <= LANTERN_TILES:
            continue
        near = min((((lx - b["x"]) ** 2 + (ly - b["y"]) ** 2) ** 0.5
                    for lx, ly in lights), default=1e9)
        if near > LIGHT_TILES:
            bad.append("route hop '%s' -> '%s' is %.1f tiles, past the %.1f-tile "
                       "lantern, and the nearest light to (%d,%d) is %.1f tiles "
                       "away: that is a walk into the dark towards nothing"
                       % (hop["from"], hop["to"], span, LANTERN_TILES,
                          b["x"], b["y"], near))

    # (e) Every fungus tile is still fungus, still air, and still touching rock.
    # The first two catch a later helper drawing over it; the third is a
    # readability rule -- a glowing tuft in the middle of a room reads as
    # something you can land on.
    for x, y in FUNGUS:
        if p.ch(x, y) != "r":
            bad.append("fungus at (%d,%d) is '%s', not 'r' -- something was "
                       "drawn over the level's light" % (x, y, p.ch(x, y)))
            continue
        if p.solid(x, y):
            bad.append("fungus at (%d,%d) resolved to a solid tile" % (x, y))
        if not any(p.solid(x + dx, y + dy) or p.oneway(x + dx, y + dy)
                   for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))):
            bad.append("fungus at (%d,%d) touches no rock and no shelf: a light "
                       "floating in a dark room reads as a platform" % (x, y))

    # (e2) The relief is relief and not geometry.  A niche must have no floor
    # of its own -- the row under it is a gallery's air -- so nothing can stand
    # in one; a cell must be walled on every side including the diagonals, so
    # it is never a room the prover has to search or the validators have to
    # approve.  Both are one line to state and both have failed in this project
    # in other shapes (defect 2 and defect 5).
    for (x, y, w, h) in NICHES:
        for xx in range(x, x + w):
            if p.solid(xx, y + h):
                bad.append("niche at (%d,%d) %dx%d has a floor at (%d,%d): it "
                           "is a room, not relief, and a %d-tile room is a "
                           "squeeze" % (x, y, w, h, xx, y + h, h))
    for (x, y, w, h) in CELLS:
        for yy in range(y - 1, y + h + 1):
            for xx in range(x - 1, x + w + 1):
                if x <= xx < x + w and y <= yy < y + h:
                    continue
                if not p.solid(xx, yy):
                    bad.append("sealed cell at (%d,%d) %dx%d is open at "
                               "(%d,%d): it is a room the prover has to search"
                               % (x, y, w, h, xx, yy))

    # (f) ADR 004 -- NO TRANSFORM PAD STRANDS A FORM.  `pad_frog` is the only
    # pad in the level, so once she is the frog she is the frog, and every place
    # the frog can stand has to still have the exit in front of it.  A
    # conservative ground flood fill from each of these, as the frog: filter and
    # not proof (world_kit.reachable_set says so itself), but it is the question
    # tools/prove.sh structurally cannot ask, because the prover only ever plays
    # the route that was declared.
    for label, entry in STRAND_ENTRIES:
        seen = k.reachable_set(entry, form="frog")
        if EXIT_TILE not in seen:
            bad.append("ADR 004: as the frog, %s at %s cannot reach the exit at "
                       "%s (%d standable tiles in its room)"
                       % (label, entry, EXIT_TILE, len(seen)))

    # (g) The pad is not decoration and the wall is not a door.  Two claims
    # about the HUMAN's reach from the spawn, and the second is why the sealed
    # cell is allowed to exist at all: tools/reachability.py resolves
    # luminous_wall as solid, so anything behind it must be optional.
    human = k.reachable_set((6, GALLERY_STAND), form="human")
    if PAD_TILE not in human:
        bad.append("the human cannot reach pad_frog at %s from the spawn"
                   % (PAD_TILE,))
    if EXIT_TILE in human:
        bad.append("the human can reach the exit at %s without the frog, so the "
                   "pad and the 3-tile treads are decoration" % (EXIT_TILE,))
    if (CELL_X0, GALLERY_STAND) in human:
        bad.append("the cell at (%d,%d) behind the luminous wall is reachable "
                   "without breaking it; the wall is not sealing anything"
                   % (CELL_X0, GALLERY_STAND))

    if bad:
        raise world_kit.WorldKitError(
            "%s: %d self-check failure(s):\n  %s"
            % (LEVEL_ID, len(bad), "\n  ".join(bad)))


## Places the frog can end up, one per room it can stand in, plus the bottom of
## each spore pit -- which is where a missed jump actually puts her and is
## therefore the entry most worth asking about.  Swept by check (f).
STRAND_ENTRIES = [
    ("the pad itself", PAD_TILE),
    ("the brood shaft's floor, west end", (3, LOWER_STAND)),
    ("tread 1", (18, 23)),
    ("tread 2", (13, 20)),
    ("tread 3", (8, 17)),
    ("the exit shelf", (4, 17)),
    ("the lower gallery, west of pit 2", (25, LOWER_STAND)),
    ("the lower gallery, between the pits", (33, LOWER_STAND)),
    ("the shaft's foot", (SHAFT_X0, LOWER_STAND)),
    ("the bottom of pit 1", (35, 27)),
    ("the bottom of pit 2", (29, 28)),
    ("the upper gallery, in the dark", (30, GALLERY_STAND)),
    ("the mouth, back in the daylight", (6, GALLERY_STAND)),
    ("the two tiles east of the hole", (43, GALLERY_STAND)),
]


def main():
    g, k = deeps_1()
    for line in k.audit(strict_verbs=True):
        print(line)
    _self_checks(g, k)
    print("  palette      missing=%s substituted=%s"
          % (DEEPS_W4.missing() or "none", DEEPS_W4.substituted or "none"))
    print("  lantern      %.3f tiles; %d authored pools, %d emissive tiles"
          % (LANTERN_TILES, len(AMBIENCE["lights"]),
             sum(1 for y in range(g.h) for x in range(g.w)
                 if g.fg[y][x] in ("r", "^", "O"))))
    write(LEVEL_ID, g, LEVEL_NAME, music="world4")
    print("--- data/ambience.json  levels[\"%s\"] ---" % LEVEL_ID)
    print(json.dumps(AMBIENCE, indent=6))


if __name__ == "__main__":
    main()
