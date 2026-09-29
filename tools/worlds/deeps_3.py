#!/usr/bin/env python3
"""deeps_3 -- THE GALLERIES.  World 4, TERMITE DEEPS, the middle level.

Self-contained: running this file under the project python writes
levels/deeps_3.json and nothing else.  It also exports `deeps_3()` returning
`(Grid, Kit)`, which is the tuple tools/build_levels.py's `build()` expects --
that writer audits the kit before it writes anything.

    source tools/env.sh && "$PYVENV" tools/worlds/deeps_3.py
    tools/prove.sh deeps_3

THE SHAPE OF THE LEVEL
----------------------
A termite nest: six chambers cut out of solid rock, joined by tunnels, on a
2x2 screen grid.  Read it as a ring rather than a line -- the long way round is
the way the level is proved, and the short way is a thing the player MAKES.

  THE MOUTH        cols 5-15,  rows 21-27.  The spawn gallery, seven rows tall
                   and lit.  Two shelves climb its east wall to the glass, and
                   its west wall is a `luminous_wall` with a chimney behind it.
  THE LOW TUNNEL   cols 16-21, rows 26-27.  Two tiles tall and dark.
  THE BOAR RUN     cols 22-40, rows 23-27.  The long gallery, crossed on flat
                   floor at row 27 -- the vertical screen seam is between cols
                   24 and 25 and the route walks it, never jumps it.
  THE EAST HALL    cols 41-47, rows 21-27.  The mouth's mirror, with the root
                   ladder climbing out of it.
  THE HIGH GALLERY cols 26-46, rows 9-12.  Where the ladder arrives.  Its floor
                   at cols 31-32 is not rock.
  THE CROWN        cols 2-22,  rows 1-3.   The exit gallery, reached only up
                   the frog shaft.

and three rooms that are not on the route at all:

  THE GLASS ALCOVE cols 17-20, rows 22-23.  Behind `deep_glowwall`.
  THE MID GALLERY  cols 28-44, rows 15-19.  Under the high gallery's floor.
  THE WEST STACK   the chimney (cols 1-3), the west gallery (cols 1-12, rows
                   16-19), the beetle cell (cols 14-17) and the west high
                   corridor (cols 1-13, rows 11-12).  A whole quarter of the
                   level with no unbreakable way into it.

THE MAZE IS THE THING YOU EDIT
------------------------------
Five walls in here are chewable, and none of them is on the proved route -- the
prover carries no attack button (see WHY NO BREAK IS ON THE PROVED ROUTE).  That
is not a level with its verb removed; it is what makes the verb worth having,
because every one of them is a CHORD across the ring:

  C1  THE GLOW WALL     (4, 26-27)    `luminous_wall`, 0.40 s, any form.
      Two tiles west of the spawn.  Behind it the root chimney and the whole
      west stack -- the shortcut that skips four fifths of the level.  It is the
      first thing you see and the last thing you understand.
  C2  THE SPOIL PLUG    (13, 18-19)   `rubble`, 0.18 s, any form.
      The west gallery's east wall.  A beetle cell with a heart in it, and a
      BARK BEETLE that walks out into the gallery the moment you open it.
  C3  THE GALLERY FLOOR (31-32, 13-14) `rubble`, 0.18 s, dug DOWNWARD.
      The high gallery's floor over the mid gallery.  Two holds of 0.18 s and
      the room you are standing on becomes a room you are falling into.
  C4  THE GLASS         (16, 22-23)   `deep_glowwall`, NO break_hold.
      Only the blade opens it, so only Kaya does: the frog has no weapon.  It is
      three tiles east of the shelf you stand on, which is well inside the
      blade's 118 px, and the alcove behind it is a four-tile landing on the far
      side of a three-tile jump.
  C6  THE COMB WALL     (14, 11-12)   `termite_wall`, 0.45 s, any form.
      The frog shaft's west wall, at the foot.  Open it from the ROUTE side and
      the west stack unrolls backwards -- corridor, ladder, gallery, chimney,
      glow wall -- and you come out at your own spawn.  That is the level's one
      real loop, and it only exists after you make it.

Nothing is behind two walls.  Nothing needed is behind any.  Every dead end pays
(three hearts, and they are all in rooms the route does not enter), and the long
way round is where the level's enemies and most of its gems are, so the shortcut
costs you the level -- which is the trade this kind of secret should be.

WHY NO BREAK IS ON THE PROVED ROUTE, MEASURED
---------------------------------------------
`ProverSearch.action_set()` is {left, none, right} x {jump, no jump} x {none,
up, down} -- eighteen actions, and `ATTACK` is not one of them.  The search
therefore never holds attack and never calls `FormBase.tick_break()`, so a
breakable tile is a wall to it no matter which form the hop declares.  This was
not reasoned, it was run: a probe level with one `termite_wall` plug across an
otherwise empty 34-tile corridor, two hops, human:

    hop 1/2  spawn > near_plug   human   143 frames       36 expansions
    FAIL     hop 2/2  near_plug > exit  (as human)
             closest approach 214.0 px, at pixel (320.0, 314.0) = tile (20, 19)
             50000 expansions spent -- budget of 50000 expansions spent
             note: this level has breakable tiles, and the prover cannot break
                   them.

285 seconds to learn that the plug is a wall.  tools/solver/prove.gd prints that
note itself, `Kit.breakable_wall` records the same thing in `Kit.unproven`, and
world_kit's own `proof_tunnel` fixture keeps its plug off its route for exactly
this reason.  So this level's declared route goes the long way round, every
chewable wall is a chord or a door onto a dead end, and
`tools/reachability.py` -- which resolves every breakable as SOLID -- has to
find the exit and all four pads without opening one.  That is the gate that
keeps the shortcuts optional rather than load-bearing.

What the kit cannot check is the OTHER half: that a wall, once broken, actually
leads somewhere.  `audit()` sees the plug and refuses to believe in the arc
through it.  So `check()` below re-probes the finished grid five times, once per
wall, with that wall's tiles cleared, and asserts the thing the break is for.
See `_broken`.

WHICH FORM OPENS WHAT, FROM data/tiles.json AND tests/test_verbs_breakables.gd
------------------------------------------------------------------------------
    rubble          215   break_hold 0.18   any form, 11 ticks
    cracked_stone   211   break_hold 0.35   any form
    luminous_wall   214   break_hold 0.40   any form
    termite_wall    213   break_hold 0.45   any form, 27 ticks
    deep_glowwall   270   no break_hold     the blade only -- and `can_attack`
                                            is false on the frog

`FormBase._break_target_of` probes one pixel outside the hitbox on the side you
are pressing, and `up`/`down` beat facing.  Two consequences this level is built
around:

  * a FLOOR is dug by standing on it and holding down+attack: the probe sits at
    `r.position.y + r.size.y`, which is the top of the tile under your feet.
    That is C3, and it works twice in a row because the second tile is under
    your feet the moment the first one is gone.
  * a CEILING cannot be dug from a corridor a body fits in.  Feet on row y put
    the body's top at 16y-6, so the probe reads row y-1 -- and in any passage
    two tiles tall, row y-1 is air.  Only a one-tile pocket puts a ceiling in
    reach, and `tests/test_level_validity.gd` refuses to let a level contain
    one.  So there is not a single upward break in here, and there cannot be.

FROG AND HUMAN, AND WHERE THEY TRADE
------------------------------------
Kaya walks the whole ring and carries the blade for it: C4 is hers and nothing
else opens it.  The frog exists for one shape -- THE FROG SHAFT (cols 15-22),
whose shelves are three rows apart:

    frog, standing jump ...... apex 5.34 tiles.  Climbs a 3-tile step.
    human, standing jump ..... apex 2.78 tiles.  LIMITS["human"]["rise"] is 2.

so the shaft is a wall to Kaya and a staircase to the frog, and the pad at its
foot is the last thing on the route that is not a jump.  The two other pads are
choices rather than gates: `pad_frog` in the mouth (take the west stack as the
climber and give up the blade) and `pad_human` in the east hall (take it back
before the high half).  Both kinds are placed so ADR 004 holds in the direction
that matters -- the frog can always walk back to a `pad_human`, and the human
can always FALL back to a `pad_frog`: from the crown she walks east off (17,3)
into the shaft's own mouth (cols 18-22 have no floor at row 4), lands on the
first shelf, and drops to the pad at (18,12).  `check()` runs that as a flood
fill.

SEAMS, AND THE ROWS NOTHING STANDS ON
-------------------------------------
`CameraController` picks its screen from the body's CENTRE and freezes the
simulation for 0.12 s while it flips, so both of these are rules:

  * the route crosses the vertical seam (x=400, between cols 24 and 25) twice,
    both times WALKING on unbroken floor: at row 27 in the boar run and at row
    12 in the high crossing.  No hop leaves the ground within three tiles of it.
  * the horizontal seam (y=240, between rows 14 and 15) is crossed exactly once
    on the route, on the root ladder, where a freeze costs nothing because the
    body is latched to a tile.  The only other crossings are falls.
  * nothing in the level stands on row 14.  A floor capped at row 15 puts the
    feet at y=240 and the centre at y=229, which is the UPPER screen -- and that
    screen ends at y=240 and never draws the floor it is standing on.  ruins_4
    shipped a gallery like that once.  The caps in here are rows 4, 7, 10, 13,
    20, 24, 26 and 28.

THE HOPS, AND WHY THERE ARE FOURTEEN OF THEM
--------------------------------------------
The budget is 50,000 expansions PER HOP and the frontier is greedy, so a hop
that spans a whole chamber is a hop that spends its budget learning the shape of
the chamber.  Two shapes in here are hop boundaries by construction:

  * the root ladder is ONE hop, from the hall floor to the high gallery floor
    three tiles west of the ladder's top.  `world_kit.proof_tunnel_seam`
    measured what happens when a hop boundary lands on a ladder top instead:
    the search and the replay disagree by one tile, because
    `ProverSearch._set_input` reads every button held across a seam as a fresh
    press and `climbing` latches on the press.  The geometry was never the
    problem.  So the seam is on flat floor, four tiles from the ladder.
  * no hop's goal is DOWN from where it starts.  The frog shaft is climbed in
    three hops and every one of them ends higher than it began.

THE PALETTE
-----------
`world_kit.Palette.char()` resolves a tile NAME through the flat, jungle-derived
`legend` key of data/level_legend.json, so DEEPS's own names (deep_earth,
deep_comb, ...) have no character there and fall through to UNDERSTUDY -- which
lands `solid` on 's' (deep_packed, the *second* solid) and `bg` on 'r'
(deep_fungus, a background accent that this level uses as a lamp).  ADR 002's
amendment says a character means whatever the level's world says it means, so
this palette is declared in terms of the jungle tile whose character IS the
deeps role character: `grass_top` for '#', `bg_leaves` for 'L', and so on.
`Palette.missing()` is then empty, `audit(strict_verbs=True)` is clean, the
level serialises `"tileset": "deeps"`, and the game paints ids 260-271.

The four breakables are `shared` characters ('o', 'm', 'O', 'c' -> 215, 213,
214, 270) and are the real tiles in every world, so this level loses no verb to
an understudy -- which matters here more than the art does, because the verb IS
the level.

THE DARK, AND WHY THE LAMPS ARE TILES
-------------------------------------
`data/ambience.json` is another agent's file at integration time, so the entry
this level wants is reported rather than written; it is quoted in full in the
hand-off.  The shape of it is the part that belongs here: the pools come off
TILES rather than off authored coordinates, so they cannot drift from the
geometry when a chamber moves.

  * `deep_fungus` (269) is placed on the FG layer -- it has no flags, so it
    collides with nothing -- one tile at every junction and along every gallery
    roof.  `AmbienceLayer._collect_emissive` scans `world.get_fg` and merges a
    run into one lozenge, so a row of it reads as a lit roof and a single tile
    reads as a lamp over a doorway.  That is "light pools marking junctions",
    authored in the grid where it can be audited.
  * `luminous_wall` (214) and `deep_glowwall` (270) -- C1 and C4, the two walls
    that are not earth -- emit as well.  So in a dark level THE WALLS YOU CAN
    BREAK ARE THE WALLS YOU CAN SEE, and the two chords that are hardest to
    guess at are the two things glowing at you.  Breaking one puts its light
    out, which is the correct and slightly sad thing for it to do.

Darkness is a shade quad and a lantern (data/fx.json) and reaches no tile flag,
so none of it changes what tools/prove.sh proved.  The captures in shots/ are
taken with the level's default ambience, which is bright: a screenshot of an
unlit room proves nothing about the room.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                                  # noqa: E402
from world_kit import (Kit, Palette, Probe, WorldKitError,           # noqa: E402
                       check_gap, check_rise, path_clear)

LEVEL_ID = "deeps_3"
LEVEL_NAME = "THE GALLERIES"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the deeps role character.
## See THE PALETTE: this is a character map, not an art claim, and the art comes
## from `"tileset": "deeps"` at load time.  The four breakables need no such
## trick -- their characters are `shared` across every world.
DEEPS_W4 = Palette("termite_deeps", {
    "bg": "bg_leaves",            # 'L' -> deep_comb
    "solid": "grass_top",         # '#' -> deep_earth
    "solid_alt": "stone_mossy",   # 'S' -> deep_crust
    "packed": "dirt",             # 'd' -> deep_chitin
    "block": "stone",             # 's' -> deep_packed
    "oneway": "wood_platform",    # '=' -> deep_shelf
    "ladder": "vine",             # '|' -> deep_ladder
    "hazard": "spikes",           # '^' -> deep_spore
    "decor": "tree_trunk",        # 'T' -> deep_root
    "void": "bg_dark",            # 'X' -> deep_void
    "water": "water",             # 'w'  shared, unused here
    "water_top": "water_top",     # '~'  shared, unused here
    "breakable": "crate",         # 'c' -> deep_glowwall   blade only
    "shoulder": "termite_wall",   # 'm'  shared, 0.45 s
    "glowwall": "luminous_wall",  # 'O'  shared, 0.40 s
    "rubble": "rubble",           # 'o'  shared, 0.18 s
})

## 'r' is the deeps tileset's background accent (deep_fungus, 269) and the kit
## has no role for it.  It goes on the FG layer on purpose -- see THE DARK: it
## declares no flags at all, so it collides with nothing, and only the fg layer
## is scanned for emissive tiles.  `gen_levels._check_characters` still proves it
## means something in this world.
FUNGUS = "r"

# ------------------------------------------------------------------ geometry
#
# Every number below is measured off one of four things: a chamber's floor, the
# frog's three-row shelf pitch, the human's two-row step, or a screen boundary.

VSEAM = 25              # first column of the eastern screens (x = 400)
HSEAM = 15              # first row of the southern screens (y = 240)

# --- the low band (southern screens).  Stand 27 everywhere; cap 28.
LOW_CAP, LOW_STAND = 28, 27

CHIM_X0, CHIM_X1 = 1, 3         # the root chimney's air
CHIM_LADDER = 2
CHIM_TOP = 21                   # its first air row; row 20 is the west gallery's floor
GLOW_X = 4                      # C1, rows 26-27
MOUTH_X0, MOUTH_X1 = 5, 15
MOUTH_TOP = 21                  # roof at row 20
LEDGE_A = (8, 26, 3)            # x, cap, w -> stand 25, two rows over the floor
LEDGE_B = (11, 24, 3)           # -> stand 23, two rows over ledge A
GLASS_X = 16                    # C4, rows 22-23
ALCOVE_X0, ALCOVE_X1 = 17, 20   # rows 22-23, cap 24
ALCOVE_STAND = 23
TUNNEL_X0, TUNNEL_X1 = 16, 21   # rows 26-27, two tiles tall and dark
RUN_X0, RUN_X1 = 22, 40         # rows 23-27, roof at 22
DODGE = ((27, 26, 3), (34, 26, 3))      # stand 25: the boar's charge passes under
HALL_X0, HALL_X1 = 41, 47       # rows 21-27, roof at 20
LADDER_E = 46                   # the root ladder, rows 12-27
SHAFT_E_X0, SHAFT_E_X1 = 45, 46 # its two-wide throat, rows 14-20

# --- the mid band.  Reached by digging C3, left by falling out of it.
MID_X0, MID_X1 = 28, 44
MID_TOP, MID_CAP = 15, 20       # air rows 15-19, roof at 14
MID_STAND = 19
DRAIN_X0, DRAIN_X1 = 43, 44     # the hole in its floor, row 20 -> the east hall

WEST_X0, WEST_X1 = 1, 12        # the west gallery, rows 16-19
WEST_TOP, WEST_CAP = 16, 20
WEST_STAND = 19
WEST_LADDER = 7                 # rows 12-19, up into the west high corridor
SPOIL_X = 13                    # C2, rows 18-19
CELL_X0, CELL_X1 = 14, 17       # the beetle cell, rows 18-19, cap 20

# --- the high band (northern screens).  Stand 12 everywhere; cap 13.
HIGH_CAP, HIGH_STAND = 13, 12
HIGH_FLOOR_X0, HIGH_FLOOR_X1 = 15, 45
HIGH_X0, HIGH_X1 = 26, 46       # the high gallery's air, rows 9-12, roof at 8
HIGH_TOP = 9
## The dome over its western half. A capture is why it exists: with the roof
## flat at row 8 the whole northern screen was four rows of room under nine rows
## of identical rock, and it read as a corridor drawn on a wall. The dome is
## carved over the half of the gallery the route walks LAST, so the search that
## climbs the ladder never sees it, and the HOLLOW TICK hangs in it -- a ceiling
## six rows over the floor is a drop worth telegraphing.
DOME_X0, DOME_X1 = 28, 38
DOME_TOP = 6
CROSS_X0, CROSS_X1 = 23, 25     # the two-tile crossing over the vertical seam
FLOORBREAK_X0, FLOORBREAK_X1 = 31, 32   # C3, rows 13-14
CORR_X0, CORR_X1 = 1, 13        # the west high corridor, rows 11-12, roof at 10
CORR_TOP = 11
COMB_X = 14                     # C6, rows 11-12

# --- the frog shaft and the crown
SHAFT_X0, SHAFT_X1 = 15, 22     # interior; walls at col 14 and col 23
SHAFT_TOP = 5                   # its first air row above the foot rows 11-12
PITCH = 3                       # rows between shelves: 48 px.  The frog's number.
SHELF_1 = (20, 10, 3)           # x, cap, w -> stand 9,  east wall
SHELF_2 = (16, 7, 3)            # -> stand 6,  west wall
CROWN_X0, CROWN_X1 = 2, 22      # air rows 1-3
CROWN_CAP = 4                   # floor at cols 2-17 ONLY: cols 18-22 are the
CROWN_FLOOR_X1 = 17             # shaft's mouth, and the last hop rises through it
CROWN_STAND = 3


def _shelf(k, spec, name, mark_x):
    """One rock shelf in the frog shaft, and the mark the next hop leaves from.

    `solid` rather than `oneway`: a one-way shelf is a shelf you fall through by
    holding down, and this shaft is the one place in the level where falling is
    the punishment rather than the route.
    """
    x, cap, w = spec
    k.ledge(x, cap, w, role="solid", stand_form="frog")
    k.rect(x, cap, w, 1, "solid_alt")          # lit from above: see THE DARK
    k.mark(name, mark_x, cap - 1, form="frog")
    return x, cap - 1, w


def _band(k, x, y, w, h, pitch=3):
    """Courses of `solid_alt` through a mass of dead rock, for the eye only.

    Art, not geometry: `deep_crust` and `deep_earth` are both plain solids, so
    nothing this writes changes a flag, a claim or a proved route -- it only
    stops six rows of identical speckle reading as a blank wall behind the
    rooms. It refuses to touch anything that is not already the plain solid, so
    a floor cap, a ladder, a lamp or a chewable wall inside the rectangle is
    left exactly as it was.
    """
    plain = k.ch("solid")
    for yy in range(y, y + h, pitch):
        for xx in range(x, x + w):
            if k.g.fg[yy][xx] == plain:
                k.put(xx, yy, "solid_alt")


def _fungus(g, points):
    """Lamps, on the fg layer, where the emissive pass can find them.

    `deep_fungus` declares no flags, which is what makes it safe to put on the
    fg layer and is also what makes it dangerous: written over rock it punches a
    non-solid hole in the wall that nothing in this project would report. So a
    lamp may only be placed in air, and asking for one anywhere else raises.
    """
    for (x, y) in points:
        if g.fg[y][x] != ".":
            raise WorldKitError(
                "lamp at (%d,%d) is over '%s', not air: `deep_fungus` has no "
                "flags, so this would open a hole in the wall"
                % (x, y, g.fg[y][x]))
        g.put(x, y, FUNGUS)


def _fungus_row(g, x, y, w):
    _fungus(g, [(x + i, y) for i in range(w)])


def deeps_3():
    """THE GALLERIES -- a ring of six chambers and five chords across it."""
    g = Grid(W, H, tileset="deeps")
    k = Kit(g, DEEPS_W4, form="human")

    # Carved, not built.  prove.gd's own note: a small reachable state space
    # makes a failed search exhaust its frontier instead of spending the whole
    # budget wandering open air -- and a nest is a hole in the ground anyway.
    k.fill_bg("bg")
    k.fill_solid("solid")
    k.shell(1, "solid")

    # ================================================= 1 -- THE LOW BAND
    # THE MOUTH.  Seven rows tall so the two shelves up its east wall have
    # headroom over them; the roof at row 20 is the west gallery's floor.
    k.corridor(MOUTH_X0, LOW_STAND, MOUTH_X1 - MOUTH_X0 + 1,
               h=LOW_STAND - MOUTH_TOP + 1)
    k.floor(MOUTH_X0, LOW_CAP, MOUTH_X1 - MOUTH_X0 + 1, depth=1)

    # The two shelves are two rows apart, which is the human's measured step
    # (LIMITS["human"]["rise"] == 2, apex 2.78 tiles).  Ledge B is where the
    # blade is thrown from and where the jump into the alcove starts.
    k.ledge(*LEDGE_A, stand_form="human")
    k.ledge(*LEDGE_B, stand_form="human")

    # THE ROOT CHIMNEY, behind C1.  Three tiles wide with the ladder up the
    # middle; the ladder passes through the west gallery's floor at row 20,
    # which is the only hole in it.
    k.clear_rect(CHIM_X0, CHIM_TOP, CHIM_X1 - CHIM_X0 + 1, LOW_CAP - CHIM_TOP)
    k.floor(CHIM_X0, LOW_CAP, CHIM_X1 - CHIM_X0 + 1, depth=1)

    # THE LOW TUNNEL: two tiles, which is a body, and no more.
    k.corridor(TUNNEL_X0, LOW_STAND, TUNNEL_X1 - TUNNEL_X0 + 1)
    k.floor(TUNNEL_X0, LOW_CAP, TUNNEL_X1 - TUNNEL_X0 + 1, depth=1)

    # THE GLASS ALCOVE.  Carved before the glass is drawn across its door, so
    # the corridor's own claim on (16,23) is released by `breakable_wall`
    # rather than silently contradicted.
    k.corridor(ALCOVE_X0, ALCOVE_STAND, ALCOVE_X1 - ALCOVE_X0 + 1)
    k.floor(ALCOVE_X0, ALCOVE_STAND + 1, ALCOVE_X1 - ALCOVE_X0 + 1, depth=1)

    # THE BOAR RUN.  Five rows: the floor the charge runs along, and two one-way
    # shelves two rows over it.  THORN BOAR (data/enemies/charger.json) sees
    # 140 px -- eight and three-quarter tiles -- inside a sight_band of 20 px,
    # and telegraphs for wind_up 0.55 s before committing to 165 px/s for
    # 0.85 s.  The run is nineteen tiles long, so it is seen coming with two
    # tiles of warning to spare; the shelves are the 20 px band's answer,
    # because a body standing on one is 32 px above the floor and out of it.
    k.corridor(RUN_X0, LOW_STAND, RUN_X1 - RUN_X0 + 1, h=5)
    k.floor(RUN_X0, LOW_CAP, RUN_X1 - RUN_X0 + 1, depth=1)
    for spec in DODGE:
        k.ledge(*spec, stand_form="human")

    # THE EAST HALL, and the throat the root ladder climbs.  Its two columns are
    # carved before the high floor is capped over them, so the ladder's shaft is
    # a shaft and not a pocket.
    k.corridor(HALL_X0, LOW_STAND, HALL_X1 - HALL_X0 + 1,
               h=LOW_STAND - (MOUTH_TOP) + 1)
    k.floor(HALL_X0, LOW_CAP, HALL_X1 - HALL_X0 + 1, depth=1)
    # The throat the ladder climbs is the LADDER, one tile wide, and nothing is
    # carved beside it. The first draft cut a two-wide shaft here and it ran
    # straight into the mid gallery's east end at rows 15-19: the room that is
    # supposed to be behind C3 had a staircase into it. A ladder tile is not
    # solid, so the column is already a passage, and `FormBase._climb` snaps the
    # body to the column's centre at 60 px/s -- a one-tile channel is what a
    # climb is FOR, and it keeps the rock between the shaft and the gallery.

    # ================================================= 2 -- THE MID BAND
    # THE MID GALLERY: five rows, no door, and a hole in its own floor. The only
    # way in is C3, straight down through the high gallery's floor; the only way
    # out is the drain at its east end, which drops into the east hall. That is
    # the level's one-way, and it is honest -- you can see the hole, the fall is
    # four rows onto a floor, and what it costs is the climb you already made.
    k.corridor(MID_X0, MID_STAND, MID_X1 - MID_X0 + 1, h=MID_STAND - MID_TOP + 1)
    k.floor(MID_X0, MID_CAP, MID_X1 - MID_X0 + 1, depth=1)
    k.clear_rect(DRAIN_X0, MID_CAP, DRAIN_X1 - DRAIN_X0 + 1, 1)

    # THE WEST GALLERY and THE BEETLE CELL.  Both are sealed: the gallery from
    # below by C1, the cell from the gallery by C2.
    k.corridor(WEST_X0, WEST_STAND, WEST_X1 - WEST_X0 + 1,
               h=WEST_STAND - WEST_TOP + 1)
    k.floor(WEST_X0, WEST_CAP, WEST_X1 - WEST_X0 + 1, depth=1)
    k.corridor(CELL_X0, WEST_STAND, CELL_X1 - CELL_X0 + 1)
    k.floor(CELL_X0, WEST_CAP, CELL_X1 - CELL_X0 + 1, depth=1)

    # ================================================= 3 -- THE HIGH BAND
    # One floor from the frog shaft's foot to the root ladder, thirty-one tiles
    # of it, capped at row 13 and walked at row 12. The vertical seam is inside
    # it at cols 24-25 and there is no gap, no hazard and no ledge within three
    # tiles of the crossing.
    k.corridor(HIGH_X0, HIGH_STAND, HIGH_X1 - HIGH_X0 + 1,
               h=HIGH_STAND - HIGH_TOP + 1)
    k.clear_rect(DOME_X0, DOME_TOP, DOME_X1 - DOME_X0 + 1, HIGH_TOP - DOME_TOP)
    k.corridor(CROSS_X0, HIGH_STAND, CROSS_X1 - CROSS_X0 + 1)
    k.clear_rect(SHAFT_X0, SHAFT_TOP, SHAFT_X1 - SHAFT_X0 + 1,
                 HIGH_STAND - SHAFT_TOP + 1)               # rows 5-12
    k.floor(HIGH_FLOOR_X0, HIGH_CAP, HIGH_FLOOR_X1 - HIGH_FLOOR_X0 + 1, depth=1)

    # THE WEST HIGH CORRIDOR, behind C6.  Two tiles tall, dark, and a dead end
    # until the comb wall is open at one end or the ladder is climbed at the
    # other.
    k.corridor(CORR_X0, HIGH_STAND, CORR_X1 - CORR_X0 + 1)
    k.floor(CORR_X0, HIGH_CAP, CORR_X1 - CORR_X0 + 1, depth=1)

    # THE CROWN, and the shaft's mouth. The floor stops at col 17 and that is
    # load-bearing twice over: cols 18-22 have to stay open or the last frog hop
    # is a jump into the underside of the very floor it means to land on
    # (`path_clear` refuses it, and a player would meet it as an invisible lid),
    # and it is also the hole Kaya falls down to get back to the frog pad.
    k.clear_rect(CROWN_X0, 1, CROWN_X1 - CROWN_X0 + 1, CROWN_STAND)
    k.floor(CROWN_X0, CROWN_CAP, CROWN_FLOOR_X1 - CROWN_X0 + 1, depth=1)
    k.clear_rect(CROWN_FLOOR_X1 + 1, CROWN_CAP, CROWN_X1 - CROWN_FLOOR_X1, 1)

    # The shaft's walls, drawn after the carve. The east wall stops two rows
    # above the floor on purpose -- that is `Kit.shaft`'s defect-5 clause by
    # hand, and it is the doorway the route walks in through.
    k.rect(SHAFT_X0 - 1, SHAFT_TOP, 1, 6, "solid")         # col 14, rows 5-10
    k.rect(SHAFT_X1 + 1, 1, 1, 10, "solid")                # col 23, rows 1-10

    # The shelves. Three rows apart, alternating walls, three tiles wide: at
    # full run a frog carries 3.1 tiles, so overshooting a two-tile shelf is the
    # normal failure and a three-tile one is landable.
    _shelf(k, SHELF_1, "shelf_1", SHELF_1[0])
    _shelf(k, SHELF_2, "shelf_2", SHELF_2[0] + 2)

    # Each hop of the climb, checked against the frog's MEASURED limits before
    # anything is drawn over the arc.
    climb_steps = (
        (18, HIGH_STAND, SHELF_1[0], SHELF_1[1] - 1),
        (SHELF_1[0], SHELF_1[1] - 1, SHELF_2[0] + 2, SHELF_2[1] - 1),
        (SHELF_2[0] + 2, SHELF_2[1] - 1, CROWN_FLOOR_X1, CROWN_STAND),
    )
    for (x1, y1, x2, y2) in climb_steps:
        what = "frog shaft hop (%d,%d) -> (%d,%d)" % (x1, y1, x2, y2)
        check_rise(y1 - y2, "frog", what)
        check_gap(abs(x2 - x1), "frog", what)
        k._claim("step", what, x1=x1, y1=y1, x2=x2, y2=y2, form="frog")

    # ================================================= 4 -- the ladders
    # Drawn after every carve, because a ladder written first and carved over
    # afterwards is the draw-order bug audit() exists for.  Each one claims a
    # standable tile beside its top (defect 1).
    k.climb(CHIM_LADDER, WEST_STAND, LOW_STAND, landing="both")
    k.climb(WEST_LADDER, HIGH_STAND, WEST_STAND, landing="both")
    k.climb(LADDER_E, HIGH_STAND, LOW_STAND, landing="left")

    # ================================================= 5 -- the five walls
    # Last, so each plug releases the claim the carve that made the room filed
    # on the tile it now fills.  None of these is on the proved route; see
    # WHY NO BREAK IS ON THE PROVED ROUTE.
    k.glow_wall(GLOW_X, LOW_STAND, 2)                       # C1  'O'  0.40 s
    k.breakable_wall(SPOIL_X, WEST_STAND, 2, role="rubble")  # C2  'o'  0.18 s
    k.breakable_wall(COMB_X, HIGH_STAND, 2, role="shoulder")  # C6 'm'  0.45 s

    # C4, the glass. NOT `breakable_wall`: that helper claims standable ground
    # on both sides at the same row, and the whole point of this one is that the
    # near side is a three-tile jump away over the mouth's own floor. Drawn flat
    # and answered by `check()`, which re-probes the grid with it gone.
    k.rect(GLASS_X, ALCOVE_STAND - 1, 1, 2, "breakable")
    for yy in (ALCOVE_STAND - 1, ALCOVE_STAND):
        k._release(GLASS_X, yy)
    k.note("C4 the glass at (%d,%d-%d) is `deep_glowwall`, which declares no "
           "break_hold: the blade is the only thing that opens it, and the frog "
           "carries none. It is three tiles from ledge B against a blade range "
           "of 118 px." % (GLASS_X, ALCOVE_STAND - 1, ALCOVE_STAND))

    # C3, the high gallery's floor over the mid gallery. Two rows thick, because
    # one dug tile leaves you standing in a hole on rock; two is a fall.
    k.rect(FLOORBREAK_X0, HIGH_CAP, FLOORBREAK_X1 - FLOORBREAK_X0 + 1, 2,
           "rubble")
    k.note("C3 at cols %d-%d rows %d-%d is a FLOOR: it is dug with down+attack, "
           "0.18 s a tile, and the second tile is under your feet the moment the "
           "first is gone. Nothing in the level needs it."
           % (FLOORBREAK_X0, FLOORBREAK_X1, HIGH_CAP, HIGH_CAP + 1))

    # ---------------------------------------------------------------- dressing
    # Background and non-colliding accents only; none of it changes a flag, so
    # none of it changes what tools/prove.sh proved.
    #
    # `void` behind the three big chambers, so the galleries read as holes in
    # rock rather than as rooms with wallpaper; `decor` roots hanging in the
    # tunnels; and `solid_alt` on the lips a body lands on, which is a
    # readability fix as much as a lit-from-above fiction.
    g.rect(MOUTH_X0, MOUTH_TOP, MOUTH_X1 - MOUTH_X0 + 1, 7, "X", "bg")
    g.rect(RUN_X0, 23, RUN_X1 - RUN_X0 + 1, 5, "X", "bg")
    g.rect(MID_X0, MID_TOP, MID_X1 - MID_X0 + 1, 5, "X", "bg")
    g.rect(HIGH_X0, HIGH_TOP, HIGH_X1 - HIGH_X0 + 1, 4, "X", "bg")
    g.rect(CROWN_X0, 1, CROWN_X1 - CROWN_X0 + 1, 3, "X", "bg")
    for x in (7, 12, 30, 37, 44):
        k.rect(x, 21, 1, 2, "decor", "bg")
    for x in (5, 19, 33, 41):
        k.rect(x, 16, 1, 3, "decor", "bg")
    k.rect(LEDGE_A[0], LEDGE_A[1], LEDGE_A[2], 1, "oneway")
    k.rect(HIGH_FLOOR_X0, HIGH_CAP, 8, 1, "solid_alt")
    k.rect(CROWN_X0, CROWN_CAP, CROWN_FLOOR_X1 - CROWN_X0 + 1, 1, "solid_alt")

    # Courses through the five masses of rock that carry no room, at the pitch
    # the chambers are spaced on. See `_band`: this is the only thing in the
    # level that exists purely because of a screenshot.
    _band(k, 25, 1, 25, 5)                 # over the high gallery's dome
    _band(k, 0, 5, 15, 6)                  # the west mass, under the crown
    _band(k, 18, 14, 10, 4)                # between the beetle cell and the mid
    _band(k, 41, 14, 9, 7)                 # around the root ladder
    _band(k, 16, 22, 12, 4)                # between the alcove and the boar run

    # THE LAMPS. One tile of `deep_fungus` over every doorway the maze can be
    # entered or left by, and a run of it along each gallery's roof. See THE
    # DARK: these are fg tiles with no flags, and they are what the ambience
    # entry turns into light.
    _fungus(g, [(MOUTH_X1, MOUTH_TOP), (TUNNEL_X0, 26), (TUNNEL_X1, 26),
                (RUN_X0, 23), (VSEAM, 23), (RUN_X1, 23),
                (HALL_X0, MOUTH_TOP), (LADDER_E - 1, MOUTH_TOP),
                (CROSS_X0, CORR_TOP), (CROSS_X1, CORR_TOP),
                (SHAFT_X0, CORR_TOP), (CORR_X1, CORR_TOP), (CORR_X0, CORR_TOP),
                (MID_X0, MID_TOP), (DRAIN_X0, MID_TOP),
                (WEST_X0, WEST_TOP), (WEST_X1, WEST_TOP), (CELL_X1, 18),
                (CHIM_X0, CHIM_TOP), (SHAFT_X1, SHAFT_TOP)])
    _fungus_row(g, DOME_X0 + 2, DOME_TOP, 6)
    _fungus_row(g, HIGH_X1 - 7, HIGH_TOP, 6)
    _fungus_row(g, CROWN_X0 + 1, 1, 5)
    _fungus_row(g, MOUTH_X0 + 2, MOUTH_TOP, 4)

    # ---------------------------------------------------------------- entities
    g.ent("player_spawn", MOUTH_X0 + 1, LOW_STAND)
    # THERE IS NO SECOND `pad_frog`, AND THAT IS A MEASUREMENT.
    #
    # The mouth was drafted with one, so the player could choose the climber
    # over the blade at the very start. It failed the gate twice:
    #
    #   at (12,27), on the floor ... hop 1 walks over it. prove.sh: "hop 2/14
    #                                mouth_e > tunnel_e: the hop declares form
    #                                'human' but the route arrives as 'frog'".
    #   at (9,25), on ledge A ...... the same failure in 24 expansions. A pad's
    #                                box is the LOWER half of its tile grown by
    #                                3 px, and a greedy frontier heading east
    #                                jumps, because up-and-east is still east.
    #                                Two rows off the walked line is not off the
    #                                route; it is on it, four frames later.
    #
    # A pad anywhere a hop's search can stray is a pad the route cannot declare
    # around, and the level does not need one: every wall in here except the
    # glass opens to a shoulder, so Kaya can walk, break and climb the entire
    # ring and the whole west chord on her own. The frog is for the one shape
    # she cannot make, and it is handed over at the foot of that shape.
    g.ent("pad_human", 43, LOW_STAND)           # the blade back, in the east hall
    g.ent("pad_frog", 18, HIGH_STAND)           # the route's, at the shaft's foot
    g.ent("pad_human", 8, CROWN_STAND)          # the route's last form change
    g.ent("exit", 4, CROWN_STAND)

    # THE BOAR in the run, and a second one in the gallery you have to dig into
    # -- a charge is a threat in a corridor and the mid gallery is seventeen
    # tiles of corridor. THE HOLLOW TICKS hang over three roofs; each tells for
    # wind_up 0.45 s, in which Kaya covers 48 px at max_run.
    g.ent("enemy_charger", 33, LOW_STAND)
    g.ent("enemy_charger", 38, MID_STAND)
    g.ent("enemy_dropper", 30, 23)
    g.ent("enemy_dropper", DOME_X0 + 5, DOME_TOP)   # six rows over the floor
    g.ent("enemy_dropper", 40, MID_TOP)
    # THE BARK BEETLES are both sealed in, and both get out the moment their
    # wall does: one into the glass alcove's jump, one into the west gallery.
    g.ent("enemy_walker", 18, ALCOVE_STAND)
    g.ent("enemy_walker", 15, WEST_STAND)
    g.ent("enemy_walker", 29, HIGH_STAND)

    # Three hearts, all of them in rooms the route does not enter.
    g.ent("heart", 19, ALCOVE_STAND)            # behind the glass
    g.ent("heart", 16, WEST_STAND)              # behind the spoil plug
    g.ent("heart", 33, MID_STAND)               # under the floor you dig
    for (x, y) in [(7, LOW_STAND), (8, 25), (12, 23), (18, LOW_STAND),
                   (24, LOW_STAND), (28, 25), (31, LOW_STAND), (35, 25),
                   (39, LOW_STAND), (44, LOW_STAND),
                   (20, ALCOVE_STAND), (3, WEST_STAND), (9, WEST_STAND),
                   (30, MID_STAND), (36, MID_STAND), (42, MID_STAND),
                   (28, HIGH_STAND), (34, HIGH_STAND), (40, HIGH_STAND),
                   (45, HIGH_STAND), (4, HIGH_STAND), (10, HIGH_STAND),
                   (21, 9), (17, 6), (13, CROWN_STAND), (2, CHIM_TOP + 4)]:
        g.ent("gem", x, y)

    # ------------------------------------------------------ the declared route
    # Fourteen short hops rather than four long ones -- see THE HOPS. Two pads of
    # each kind means neither `pad_frog` nor `pad_human` names a waypoint on its
    # own (gen_levels.Grid._waypoints refuses a type there are several of), so
    # each of the two the route uses carries a mark on its own tile. Standing on
    # that tile is what fires the pad, so the hop that arrives is the hop that
    # transforms, and the next hop's declared form is checked by prove.gd
    # against what actually happened.
    k.mark("mouth_e", MOUTH_X1 - 1, LOW_STAND)
    k.mark("tunnel_e", TUNNEL_X1, LOW_STAND)
    k.mark("run_mid", 28, LOW_STAND)
    k.mark("run_e", 36, LOW_STAND)
    k.mark("ladder_foot", LADDER_E - 1, LOW_STAND)
    k.mark("high_e", 42, HIGH_STAND)
    k.mark("high_mid", 34, HIGH_STAND)
    k.mark("high_w", 27, HIGH_STAND)
    k.mark("shaft_foot", 18, HIGH_STAND)                 # pad_frog
    # shelf_1 and shelf_2 are filed by _shelf(), on the shelves themselves.
    k.mark("crown_e", CROWN_FLOOR_X1, CROWN_STAND, form="frog")
    k.mark("crown_pad", 8, CROWN_STAND, form="frog")     # pad_human

    g.route("spawn", "mouth_e", form="human")
    g.route("mouth_e", "tunnel_e", form="human")
    g.route("tunnel_e", "run_mid", form="human")         # over the vertical seam
    g.route("run_mid", "run_e", form="human")
    g.route("run_e", "ladder_foot", form="human")
    g.route("ladder_foot", "high_e", form="human")       # the root ladder, one hop
    g.route("high_e", "high_mid", form="human")
    g.route("high_mid", "high_w", form="human")
    g.route("high_w", "shaft_foot", form="human")        # over the seam again
    g.route("shaft_foot", "shelf_1", form="frog")
    g.route("shelf_1", "shelf_2", form="frog")
    g.route("shelf_2", "crown_e", form="frog")
    g.route("crown_e", "crown_pad", form="frog")
    g.route("crown_pad", "exit", form="human")
    return g, k


# ==========================================================================
# What the kit cannot check on its own.
# ==========================================================================

## The five chewable walls, as (label, [tiles], what breaking them is FOR).
## `check()` re-probes the finished grid once per wall with that wall's tiles
## cleared. audit() cannot do this -- it sees the plug and correctly refuses to
## believe in the arc through it -- and the prover cannot do it either, because
## it has no attack button. Without these five assertions a chord could be
## authored that opens onto rock, and nothing in the project would say so.
WALLS = {
    "C1 the glow wall": [(4, 26), (4, 27)],
    "C2 the spoil plug": [(13, 18), (13, 19)],
    "C3 the gallery floor": [(31, 13), (31, 14), (32, 13), (32, 14)],
    "C4 the glass": [(16, 22), (16, 23)],
    "C6 the comb wall": [(14, 11), (14, 12)],
}

## (label, from, to, rise) -- the thing each break is for, as a move that must
## become possible once the wall is gone and must NOT be possible while it is
## there.
BREAK_ROUTES = [
    ("C1 the glow wall", (5, 27), (3, 27), 2),
    ("C2 the spoil plug", (12, 19), (14, 19), 2),
    ("C4 the glass", (13, 23), (17, 23), 2),
    ("C6 the comb wall", (13, 12), (15, 12), 2),
]


def _broken(k, tiles):
    """A Probe over a copy of the grid with `tiles` cleared."""
    clone = Grid(k.g.w, k.g.h, tileset=k.g.tileset)
    clone.fg = [row[:] for row in k.g.fg]
    for (x, y) in tiles:
        clone.fg[y][x] = "."
    return Probe(clone)


def check(k, verbose=True):
    """Everything that can be said about this level before the prover runs.

    Not proof -- `tools/prove.sh` is. This is the fast filter for the class of
    error this project has shipped six times, plus the two questions the prover
    structurally cannot answer here: whether a wall opens onto anything, and
    whether a transform can strand you (ADR 004).
    """
    bad = []
    probe = Probe(k.g)

    # 1. Every break leads somewhere, and only after it is broken.
    for label, a, b, rise in BREAK_ROUTES:
        opened = _broken(k, WALLS[label])
        if not opened.standable(*b):
            bad.append("%s: (%d,%d) is not standable even with the wall gone"
                       % (label, b[0], b[1]))
        elif not path_clear(opened, a[0], a[1], b[0], b[1], rise):
            bad.append("%s: nothing gets a body from (%d,%d) to (%d,%d) even "
                       "with the wall gone -- the chord opens onto rock"
                       % (label, a[0], a[1], b[0], b[1]))
        elif path_clear(probe, a[0], a[1], b[0], b[1], rise):
            bad.append("%s: (%d,%d) -> (%d,%d) already works with the wall "
                       "SHUT, so the wall is decoration"
                       % (label, a[0], a[1], b[0], b[1]))
        elif verbose:
            print("  chord        %-22s (%d,%d) -> (%d,%d) only once it is open"
                  % (label, a[0], a[1], b[0], b[1]))

    # C3 is a floor rather than a door, so it is checked as a fall: with it gone
    # the column is open from the high gallery's stand row into the mid gallery.
    dug = _broken(k, WALLS["C3 the gallery floor"])
    col = FLOORBREAK_X0
    if any(dug.solid(col, y) for y in range(HIGH_STAND, MID_TOP + 1)):
        bad.append("C3 the gallery floor: col %d is still blocked between rows "
                   "%d and %d with the floor dug out" % (col, HIGH_STAND, MID_TOP))
    elif not dug.standable(col, MID_STAND):
        bad.append("C3 the gallery floor: the fall lands at (%d,%d), which is "
                   "not standable" % (col, MID_STAND))
    elif verbose:
        print("  chord        %-22s (%d,%d) falls to (%d,%d)"
              % ("C3 the gallery floor", col, HIGH_STAND, col, MID_STAND))

    # 2. ADR 004, both directions, with every wall SHUT -- which is the state
    #    the level is in when you first stand anywhere.
    #    * from the spawn, Kaya must reach the frog pad at the shaft's foot, or
    #      the level cannot be finished at all;
    #    * from the crown, she must be able to get back DOWN to it, or the pad
    #      at (8,3) is a transform that strands her at the exit's door.
    #    * and the west stack must still be sealed, or C1 and C6 are scenery.
    from_spawn = k.reachable_set((6, LOW_STAND), form="human")
    if (18, HIGH_STAND) not in from_spawn:
        bad.append("the frog pad at (18,%d) is not reachable on foot from the "
                   "spawn with every wall shut" % HIGH_STAND)
    if (3, HIGH_STAND) in from_spawn:
        bad.append("the west high corridor is reachable with every wall shut, "
                   "so C1 and C6 are not chords, they are decoration")
    from_crown = k.reachable_set((8, CROWN_STAND), form="human")
    if (18, HIGH_STAND) not in from_crown:
        bad.append("a human left standing in the crown cannot get back to the "
                   "frog pad at (18,%d) -- that is ADR 004" % HIGH_STAND)
    if verbose:
        print("  flood        from the spawn %d standable tiles; from the crown %d"
              % (len(from_spawn), len(from_crown)))

    # 3. The frog shaft is a wall to Kaya. If the human could climb it the pad
    #    at its foot would be decoration and the level would have one verb.
    for (x1, y1, x2, y2) in ((18, HIGH_STAND, SHELF_1[0], SHELF_1[1] - 1),
                             (SHELF_1[0], SHELF_1[1] - 1,
                              SHELF_2[0] + 2, SHELF_2[1] - 1)):
        if path_clear(probe, x1, y1, x2, y2, 2):
            bad.append("the human's two-tile rise clears the shaft step "
                       "(%d,%d) -> (%d,%d); the shelves are meant to be three "
                       "rows apart" % (x1, y1, x2, y2))

    if bad:
        raise WorldKitError("%s: %d check(s) failed:\n  %s"
                            % (LEVEL_ID, len(bad), "\n  ".join(bad)))
    return k.audit(strict_verbs=True)


def main():
    grid, kit = deeps_3()
    missing = kit.pal.missing()
    if missing:
        raise SystemExit("palette has unresolved roles: %s" % (missing,))
    for line in check(kit):
        print(line)
    write(LEVEL_ID, grid, LEVEL_NAME, music="world4")


if __name__ == "__main__":
    main()
