#!/usr/bin/env python3
"""heights_2 -- THE THERMALS.  World 3, THERMAL HEIGHTS, second level.

Self-contained: running this file under the project python writes
levels/heights_2.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `heights_2()` returning `(Grid, Kit)`,
the tuple that writer's `build()` expects -- it audits the kit before it writes.

    source tools/env.sh && "$PYVENV" tools/worlds/heights_2.py
    tools/prove.sh heights_2

WHAT THE LEVEL IS ABOUT
----------------------
heights_1 taught the updraft.  This one is about what flying COSTS, and the
first thing that had to be measured is which part of flying costs anything at
all.  Everything below was measured by driving `src/player/forms/form_bird.gd`
through the shipping `form.update()` + `actor.step_motion()` loop at 60 Hz --
the same two calls the prover makes -- in a scratch scene under
`--headless --path .`, because `--script` has no autoloads and the bird's
`sfx("flap")` needs one (ADR 003).

    FLYING LEVEL IS FREE.  A bird that holds its altitude over flat ground
    crossed 196 tiles in 50 s and still had 9.6 of its 100 stamina: the flap
    costs 12, and `stamina_regen` 46 pays back a quarter of that every airborne
    second (form_bird.gd: `stamina + regen * delta * 0.25`), while the sag
    between flaps is bought back by `glide_gravity` 105.  Distance is NOT a
    budget in this game, and a level that spaces its perches out and calls that
    "stamina pressure" would be lying to the player.

    CLIMBING IS THE BUDGET.  `flap_vel` -172 against `gravity` 420 lifts about
    1.98 tiles per flap, and a flap is 12 of 100:

        cold climb, jump mashed ..... 14 tiles in 1.82 s, 25 stamina left
        cold climb, jump mashed ..... 21 tiles in 2.95 s,  2 stamina left
        cold climb, flapped at apex . 32.3 tiles -- optimal play, not human play

      So a mashed bar tops out at about 21 tiles of climb.  That number is the
      level's unit of distance.

    A THERMAL IS FREE HEIGHT.  `updraft` is [0, -400] and `apply_gravity` caps
    the fall at `max_fall + current.y` = 190 - 400 = -210, so a bird in a
    thermal RISES with no input at all:

        20-row updraft column ....... the lip in 1.85 s at 182 px/s, 0 stamina
        it overshoots the lip by .... 3.28 tiles, and settles 2.2 above it
        `updraft_strong` [0,-560] ... overshoots ~10 tiles and hits the ceiling,
                                      which is why this level uses the plain one

    A DOWNDRAFT IS A ONE-WAY DOOR.  `downdraft` is [0, +170] against
    `flap_vel` -172: a flap inside one sets vel.y to -2 px/s.  Flapping flat
    out, the bird sank 2.1 tiles in 2.27 s and then had nothing left -- BEST
    GAIN 0.00 TILES.  You cannot climb sinking air, at any stamina.  Nine
    pixels a second of margin, and it points the wrong way.

    A GUST IS THE SAME TRICK SIDEWAYS.  `gust_right` is [80, 0] and the bird
    runs 104, so `run_axis`'s target is 184 downwind and 24 upwind:

        the 10-tile lane, eastbound . 1.12 s at 184 px/s, 14 stamina
        the 10-tile lane, westbound . 7.35 s at  24 px/s, 27 stamina

    A PERCH IS AN OASIS, AND SO IS A PAD.  On the ground the bird regains
    `stamina_regen` 46 + `perch_regen_bonus` 34 = 80/s: 0 to full in 1.27 s.
    And `Player.set_form()` loads a fresh form, so stepping on a `pad_bird` is
    a full bar by construction (ProverSim.set_form does the same, so the prover
    agrees).

THE SHAPE, AND THE ARITHMETIC IT IS BUILT ON
--------------------------------------------
A cliff riddled with chimneys, carved out of solid rock rather than built in
open sky -- the prover's frontier stays inside the rooms instead of wandering
the sky, which is what makes a bird level provable at all.  Four stages:

  1 THE SCREE (rows 23-29, cols 1-11).  Kaya on foot: two tiles of
    `heights_vent` in the floor to hop, then the `pad_bird` at the foot of the
    cold chimney.  The only walked ground in the level.

  2 THE COLD CHIMNEY (cols 7-11, rows 12-27).  No draught in it at all, and
    that is the point: 14 tiles of climb, which MEASURES at 1.82 s and 75 of
    the 100 stamina mashed.  She arrives on the gallery with a quarter of a bar
    and the floor under her is the oasis that refills it in 1.27 s.  This is
    the level stating its unit before it charges anything for it.

  3 THE GALLERY AND THE CREVICE (cols 12-18, rows 5-14).  `pad_frog` on the
    gallery floor, then three treads -- stand 13 -> 10 -> 7 -> 6 -- climbed on
    legs.  The frog's measured apex is 5.34 tiles, so a 3-tile tread is the
    kit's limit and not a guess (LIMITS["frog"]["rise"]).  Seven tiles of
    height for NO stamina is the cheapest lift in the level, which is the
    point of having a second form here at all.
    A bird that skips the pad can fly the crevice instead, once she has
    refilled: 7 tiles is 42 stamina and she lands with 25.  The declared route
    takes the pads because free height is the better answer and World 3 leans
    on both forms -- the same honesty ruins_3 records about its colonnade.

  4 THE CANYON (cols 25-44, rows 2-13) and THE CELLAR (rows 18-27).  The two
    halves of one loop, and the thing this level exists for.  The canyon's
    floor is a shelf of `heights_vent` at row 14: nothing may stand on it, so
    the crossing is flown and `ProverSim.rejection()` refuses any state that
    touches it.  Eastbound, high:

        the curtain  cols 25-27, rows 2-13, downdraft.  Crossing costs about
                     2.8 tiles of altitude unfought, or two flaps (24 stamina)
                     to hold the line.  It drops her into --
        the thermal  cols 28-31, rows 8-27, updraft.  Free.  It gives back
                     everything the curtain took and puts her in --
        the lane     cols 32-41, rows 5-7, gust_right.  Ten tiles in 1.12 s.
        the island   cols 36-38, a rock stack at stand row 8, under the lane:
                     the oasis in the middle of the crossing, 1.27 s to full.
        the flue     cols 41-44, rows 10-23, downdraft.  The dive: 14 rows in
                     1.42 s at up to 360 px/s.  ONE WAY.  It is the same tile
                     as the curtain and it is why the loop cannot be run
                     backwards -- best gain 0.00 tiles, measured.

    And westbound, low: the cellar's own wind is `gust_left`, cols 32-40 rows
    25-26, so the return leg runs 184 px/s the way the canyon runs 24.  The
    cellar's roof is rock (rows 15-17) with exactly two holes in it: the flue,
    which cannot be climbed, and the thermal, which is free.  From the cellar
    floor to the flight lane is 22 tiles; a mashed bar buys 21.1.  The number
    and the geometry say the same thing, which is the only way this project
    trusts either of them.

  5 THE TERRACE (cols 45-48, rows 2-7).  The exit, reached by flying east over
    the mouth of the flue she came down -- three tiles of clearance above tiles
    that would take her back to the cellar.

WHERE THE FLOORS SIT, AND WHY
-----------------------------
`CameraController` picks its screen from the body's CENTRE and freezes the sim
for SLIDE_TIME while it flips, so a floor capped on the first row of a screen
is a floor its own player never sees (ruins_4 shipped a gallery walked along
the frame's last pixel).  Every stand row here is 27, 13, 10, 8, 7 or 6 -- none
of them 14 or 29, the two rows a 15-row screen boundary would swallow.

The vertical seam is x=400, between cols 24 and 25.  The hall's floor stops at
col 22 and the lip at col 24 is rock: standing there her centre is x=389, so
the launch is on screen 0 and the flip happens three tiles into the glide, over
open air, rather than on the frame she leaves the cliff.  Nothing in this level
is jumped on foot across a seam: the human's hop is at cols 4-5 and the frog's
treads at cols 16-18, both deep inside screen 0.

THE PALETTE
-----------
`Palette.char()` resolves a tile NAME through the flat, jungle-derived `legend`
key of data/level_legend.json, so THERMAL_HEIGHTS's own names (heights_rock,
heights_vent, ...) have no character there and fall through to UNDERSTUDY --
`solid` would emit 's' (heights_basalt, the second solid) and `bg` would emit
'r' (heights_cloud, a background accent).  ADR 002's amendment says a character
means whatever the level's world says it means, so every role here is declared
in terms of the jungle tile whose character IS the heights role character.
`Palette.missing()` is empty, `audit(strict_verbs=True)` is clean, and the
level serialises "tileset": "heights", so the game paints heights art: ids 240,
241, 242, 243, 244, 245, 246, 247, 249 and 250 all appear in the JSON.  The
draughts and the gusts are `shared` characters and are the real tiles either
way -- this level loses no verb to an understudy.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                      # noqa: E402
from world_kit import Kit, Palette                      # noqa: E402

LEVEL_ID = "heights_2"
LEVEL_NAME = "THE THERMALS"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the heights role
## character.  A character map, not an art claim: the art comes from
## `"tileset": "heights"` at load time.  See THE PALETTE above.
HEIGHTS_W3 = Palette("thermal_heights", {
    "bg": "bg_leaves",            # 'L' -> heights_wall
    "solid": "grass_top",         # '#' -> heights_rock
    "solid_alt": "stone_mossy",   # 'S' -> heights_rock_sun
    "packed": "dirt",             # 'd' -> heights_scree
    "block": "stone",             # 's' -> heights_basalt
    "oneway": "wood_platform",    # '=' -> heights_plank
    "ladder": "vine",             # '|' -> heights_chain
    "hazard": "spikes",           # '^' -> heights_vent
    "water": "water",             # '~'  shared, unused here
    "water_top": "water_top",     # 'w'  shared, unused here
    "decor": "tree_trunk",        # 'T' -> heights_stack
    "void": "bg_dark",            # 'X' -> heights_air
    "breakable": "crate",         # 'c' -> heights_shell
    "shoulder": "cracked_stone",  # 'k'  shared
    "rubble": "rubble",           # 'o'  shared
    "updraft": "updraft",         # 'U'  shared
    "updraft_strong": "updraft_strong",   # '*'  shared, unused: see the note
    "downdraft": "downdraft",     # 'V'  shared
    "gust_right": "gust_right",   # ')'  shared
    "gust_left": "gust_left",     # '('  shared
})

## The background accent has no kit role: 'r' is heights_cloud (250), painted
## straight onto the bg layer through the Grid, the way gen_levels' own idioms
## do. It is dressing and carries no flags.
CLOUD = "r"

# ---------------------------------------------------------------- geometry
#
# One table, so a row number below is never a magic number twice. Every stand
# row is checked against the screen grid in WHERE THE FLOORS SIT.

SEAM_ROW = 15                 # first row of the lower screens
SEAM_COL = 25                 # first column of the eastern screens

# 1 THE SCREE
SCREE_X0, SCREE_X1 = 1, 11
SCREE_TOP = 23                # first clear row
SCREE_CAP = 28                # the floor's capped row
SCREE_STAND = SCREE_CAP - 1   # 27
PIT_X, PIT_W = 4, 2           # the vent pit she hops

# 2 THE COLD CHIMNEY
CHIM_X0, CHIM_X1 = 7, 11
CHIM_TOP = 12                 # its head, which opens EAST into the gallery

# 3 THE GALLERY AND THE CREVICE
GALL_X0, GALL_X1 = 12, 15
GALL_TOP = 10
GALL_CAP = 14
GALL_STAND = GALL_CAP - 1     # 13
CREV_X0, CREV_W = 16, 3
CREV_TOP = 5
TREAD_ROW = 11                # first tread: stand 10
TREAD_RISE = 3                # LIMITS["frog"]["rise"], measured apex 5.34
HALL_X0, HALL_X1 = 19, 22
HALL_TOP = 3
HALL_CAP = 7
HALL_STAND = HALL_CAP - 1     # 6
LIP_X0, LIP_X1 = 23, 24       # the rock lip she launches from
LIP_CAP = 8
LIP_STAND = LIP_CAP - 1       # 7

# 4 THE CANYON
CAN_X0, CAN_X1 = 25, 44
CAN_TOP = 2
CAN_BOT = 13                  # last clear row above the vent shelf
SHELF_ROW = 14                # the vents: nothing stands here, ever
SHELF_BOT = 17                # the rock the shelf is the top of
CURTAIN_X0, CURTAIN_W = 25, 3
THERM_X0, THERM_W = 28, 4
THERM_TOP = 8                 # measured: the ride overshoots it by 3.28 tiles
LANE_X0, LANE_W = 32, 10
LANE_Y0, LANE_H = 5, 3
ISLE_X0, ISLE_W = 36, 3
ISLE_CAP = 9
ISLE_STAND = ISLE_CAP - 1     # 8
FLUE_X0, FLUE_W = 41, 4
FLUE_TOP, FLUE_BOT = 10, 23   # stops four rows short of the floor: she lands

# THE CELLAR
CELL_TOP = 18
CELL_CAP = 28
CELL_STAND = CELL_CAP - 1     # 27
BREAK_X, BREAK_W = 35, 4      # vents in the cellar floor: the walk is broken
OASIS_X0, OASIS_W = 32, 3     # the scree shelf beside the thermal: the fuel stop
CGUST_X0, CGUST_W = 32, 9
CGUST_Y0, CGUST_H = 25, 2

# 5 THE TERRACE
TERR_X0, TERR_X1 = 45, 48
TERR_CAP = 7
TERR_STAND = TERR_CAP - 1     # 6


def _air_mark(k, name, x, y, tall=2):
    """A waypoint in mid-air, for a form that does not need a floor.

    Not `Kit.mark`: that files a "stand" claim, and a flight waypoint has no
    floor under it by design. `ProverSearch._reached` accepts arrival for the
    bird on overlap alone -- flying IS being somewhere -- so what has to be
    true of the tile is that a body fits in it, which is what this claims.
    The same hand-off `world_kit.colonnade` and ruins_3's `_wet_mark` make.
    """
    k.g.mark(name, x, y)
    k._claim("clear", "flight waypoint '%s'" % name, x=x, y=y, tall=tall)
    return name


def heights_2():
    g = Grid(W, H, tileset="heights")
    k = Kit(g, HEIGHTS_W3, form="human")

    # ------------------------------------------------------------- the rock
    # Carved, not built. A bird has eighteen actions and no floor to constrain
    # it, so the one thing that keeps a hop's search tractable is walls: the
    # frontier runs out of room instead of running out of budget.
    k.fill_bg("bg")
    k.fill_solid("packed")
    k.shell(1, "solid")

    # ===================================================== 1 -- THE SCREE
    k.clear_rect(SCREE_X0, SCREE_TOP, SCREE_X1 - SCREE_X0 + 1,
                 SCREE_CAP - SCREE_TOP)
    k.floor(SCREE_X0, SCREE_CAP, SCREE_X1 - SCREE_X0 + 1, depth=2)
    # The pit. Two tiles of vent, which the human clears at LIMITS 3 with a
    # tile to spare, and it has rock under it rather than sky: falling in costs
    # a heart, not the level. `Kit.gap` files the arc and checks the width.
    k.rect(PIT_X, SCREE_CAP, PIT_W, 1, "hazard")
    k.gap(PIT_X, SCREE_STAND, PIT_W, form="human",
          landing_w=SCREE_X1 - (PIT_X + PIT_W) + 1)

    # ============================================== 2 -- THE COLD CHIMNEY
    # No draught. 14 tiles from the scree floor to the gallery: 1.82 s and 75
    # of 100 stamina, mashed. The walls are what is left of the fill at col 6
    # and col 12; the head is capped at row 11 because the way out is EAST
    # into the gallery, two tiles of it, and that is claimed below rather than
    # assumed -- a shaft with a lid and no side door is defect 6.
    k.clear_rect(CHIM_X0, CHIM_TOP, CHIM_X1 - CHIM_X0 + 1,
                 SCREE_TOP - CHIM_TOP)

    # ================================= 3 -- THE GALLERY AND THE CREVICE
    k.clear_rect(GALL_X0, GALL_TOP, GALL_X1 - GALL_X0 + 1,
                 GALL_CAP - GALL_TOP)
    k.clear_rect(CREV_X0, CREV_TOP, CREV_W, GALL_CAP - CREV_TOP)
    # One floor under both, so the frog walks from the chimney's head to the
    # foot of the treads without a step in it.
    k.floor(GALL_X0, GALL_CAP, CREV_X0 + CREV_W - GALL_X0, depth=1)
    for x in range(CHIM_X1, GALL_X0 + 1):
        k._claim("clear", "the chimney's head opens east into the gallery",
                 x=x, y=GALL_STAND, tall=2)
    k._claim("step", "off the chimney's head onto the gallery floor",
             x1=CHIM_X1, y1=GALL_STAND, x2=GALL_X0, y2=GALL_STAND,
             form="bird")

    # The treads. `Kit.stair` checks the rise against the frog's MEASURED apex
    # before it draws a tile, which is the whole reason it exists: jungle_4
    # shipped 4-tile rungs that caught sometimes.
    k.stair(CREV_X0, TREAD_ROW, 2, rise=TREAD_RISE, run=0, width=CREV_W,
            form="frog")
    # Straight up through the tread, not diagonally onto its lip: a one-way is
    # the only floor a body can rise through from below, and `path_clear` models
    # the rise as happening in the START column -- at col 15 that column is
    # capped by the gallery's own roof, so a diagonal claim there is false about
    # a jump the frog makes easily. The claim says what the frog does.
    k._claim("step", "the gallery floor up through the first tread",
             x1=CREV_X0 + 1, y1=GALL_STAND, x2=CREV_X0 + 1, y2=TREAD_ROW - 1,
             form="frog")
    k._claim("step", "the top tread onto the hall",
             x1=CREV_X0 + CREV_W - 1, y1=TREAD_ROW - TREAD_RISE - 1,
             x2=HALL_X0, y2=HALL_STAND, form="frog")

    # The hall, and the lip east of it. The hall's floor stops at col 22 and
    # cols 23-24 are rock capped at row 8, so the launch is a walk onto a
    # shoulder rather than a jump across the screen seam.
    k.clear_rect(HALL_X0, HALL_TOP, HALL_X1 - HALL_X0 + 1, HALL_CAP - HALL_TOP)
    k.floor(HALL_X0, HALL_CAP, HALL_X1 - HALL_X0 + 1, depth=1,
            cap="solid_alt")
    k.clear_rect(LIP_X0, HALL_TOP, LIP_X1 - LIP_X0 + 1, LIP_CAP - HALL_TOP)
    k.rect(LIP_X0, LIP_CAP, LIP_X1 - LIP_X0 + 1, 1, "solid_alt")

    # ==================================================== 4 -- THE CANYON
    k.clear_rect(CAN_X0, CAN_TOP, CAN_X1 - CAN_X0 + 1, CAN_BOT - CAN_TOP + 1)
    # The vent shelf. This is the floor of the crossing and nothing may ever
    # stand on it: `ProverSim.rejection()` refuses a state touching a hazard,
    # so "run out of altitude" is a failure the gate can see, and a walked
    # shortcut along the canyon's floor -- which would delete the whole level --
    # is not available to the prover or to the player.
    k.rect(CAN_X0, SHELF_ROW, CAN_X1 - CAN_X0 + 1, 1, "hazard")

    # The island: a stack of basalt hanging under the lane, sunlit on top.
    # Three tiles, because `cloud_deck` refuses a one-tile perch -- the bird
    # runs 104 px/s and its hitbox is 12 px wide.
    k.floor(ISLE_X0, ISLE_CAP, ISLE_W, depth=2, cap="solid_alt", fill="block")

    # The terrace and the exit.
    k.clear_rect(TERR_X0, CAN_TOP, TERR_X1 - TERR_X0 + 1, TERR_CAP - CAN_TOP)
    k.floor(TERR_X0, TERR_CAP, TERR_X1 - TERR_X0 + 1, depth=1, cap="solid_alt")

    # ==================================================== THE CELLAR
    k.clear_rect(CAN_X0, CELL_TOP, CAN_X1 - CAN_X0 + 1, CELL_CAP - CELL_TOP)
    k.floor(CAN_X0, CELL_CAP, CAN_X1 - CAN_X0 + 1, depth=2)
    k.rect(BREAK_X, CELL_CAP, BREAK_W, 1, "hazard")

    # ------------------------------------------------------- the moving air
    # Drawn last, and in this order, because two of these columns are the holes
    # in the shelf: the draught tiles are what replace the vents and the rock
    # at rows 14-17. A column drawn before the shelf would be capped by it,
    # which is the draw-order bug `Kit.audit` exists to catch.
    k.rect(CURTAIN_X0, CAN_TOP, CURTAIN_W, CAN_BOT - CAN_TOP + 1, "downdraft")
    k.rect(THERM_X0, THERM_TOP, THERM_W, CELL_STAND - THERM_TOP + 1, "updraft")
    k.rect(LANE_X0, LANE_Y0, LANE_W, LANE_H, "gust_right")
    k.rect(FLUE_X0, FLUE_TOP, FLUE_W, FLUE_BOT - FLUE_TOP + 1, "downdraft")
    k.rect(CGUST_X0, CGUST_Y0, CGUST_W, CGUST_H, "gust_left")
    # `updraft_strong` is declared and deliberately unused: measured, a bird
    # riding [0,-560] leaves the lip at 370 px/s and coasts ten tiles past it,
    # which in a 30-row level means the ceiling rather than a landing. The
    # plain draught settles 2.2 tiles over its lip, which is a perch height.
    k.note("updraft_strong is declared but not drawn: measured, it overshoots "
           "its lip by ~10 tiles and this level has no room for that.")

    # -------------------------------------------------------------- dressing
    #
    # THE BACKGROUND IS NOT DECORATION HERE, IT IS THE LEGIBILITY OF THE VERB.
    # The draught tiles are fifteen to twenty-eight half-transparent pale-green
    # pixels in a 16x16 cell -- wisps, correctly, because moving air is not a
    # wall. Over `heights_air` (mean 188,181,174) those wisps are almost
    # invisible: the first captures of this level showed a thermal that a
    # player could not see. So every column and lane of moving air is backed on
    # the BG layer with `heights_stack` (mean 61,58,64), and the wisps read
    # against it at a glance. Nothing about collision changes; the shots are
    # the evidence, shots/heights_2_h_thermal.png before and after.
    #
    # Everything outdoors gets `heights_air` -- the canyon, the hall's notch and
    # the terrace, which are all the same sky -- and everything cut into the
    # rock keeps the dark `heights_wall`: the chimney and the cellar are
    # interiors, and painting sky behind them made a shaft look like a window.
    k.rect(CAN_X0, CAN_TOP, CAN_X1 - CAN_X0 + 1, CAN_BOT - CAN_TOP + 1,
           "void", "bg")
    k.rect(HALL_X0, HALL_TOP, LIP_X1 - HALL_X0 + 1, LIP_CAP - HALL_TOP,
           "void", "bg")
    k.rect(TERR_X0, CAN_TOP, TERR_X1 - TERR_X0 + 1, TERR_CAP - CAN_TOP,
           "void", "bg")
    # Cloud banding, in the open sky only: 'r' is heights_cloud, which has no
    # kit role, so it goes on through the Grid the way gen_levels' own idioms
    # do. Rows 3 and 11 -- not row 6, which is the gust lane and wants the dark
    # backing instead.
    for y in (3, 11):
        g.rect(CAN_X0 + 1, y, CAN_X1 - CAN_X0 - 1, 1, CLOUD, "bg")

    # The three VERTICAL draughts are backed; the two horizontal gust lanes are
    # not, and that is the second thing the captures settled. A 10x3 dark
    # rectangle hanging in the sky reads as a platform -- the contact sheet had
    # the lane looking like a ledge the bird could land on, which is the "looks
    # like a passage, behaves like a wall" defect wearing its coat inside out.
    # A tall narrow one reads as what it is: a column of moving air. The gusts
    # keep their pale sky and are felt rather than seen, except in the cellar,
    # where the background is already dark and the wisps carry themselves.
    #
    # The grammar this leaves: every solid you may land on has a bright cap
    # (heights_rock or heights_rock_sun); moving air never does.
    k.rect(CURTAIN_X0, CAN_TOP, CURTAIN_W, CAN_BOT - CAN_TOP + 1, "decor", "bg")
    k.rect(THERM_X0, THERM_TOP, THERM_W, CELL_STAND - THERM_TOP + 1,
           "decor", "bg")
    k.rect(FLUE_X0, FLUE_TOP, FLUE_W, FLUE_BOT - FLUE_TOP + 1, "decor", "bg")

    for (x, y, h) in [(2, 24, 4), (14, 11, 3), (46, 3, 4), (23, 20, 7)]:
        k.rect(x, y, 1, h, "decor", "bg")

    # -------------------------------------------------------------- entities
    g.ent("player_spawn", 2, SCREE_STAND)
    g.ent("pad_bird", 9, SCREE_STAND)             # the chimney's foot
    g.ent("pad_frog", 13, GALL_STAND)             # the gallery
    g.ent("pad_bird", 20, HALL_STAND)             # the hall, at the launch
    g.ent("exit", 46, TERR_STAND)

    # Two flyers, both a fixed patrol (src/enemies/flyer.gd does not chase) and
    # both at least three tiles off the declared route: the vents are this
    # level's threat and a bird with no weapon cannot answer anything else.
    g.ent("enemy_flyer", 34, 11, axis="x", range=40)
    g.ent("enemy_flyer", 26, 21, axis="y", range=48)

    g.ent("heart", 43, CELL_STAND)
    for (x, y) in [(3, SCREE_STAND), (7, SCREE_STAND), (14, GALL_STAND),
                   (17, TREAD_ROW - 1), (17, TREAD_ROW - TREAD_RISE - 1),
                   (21, HALL_STAND), (30, 4), (37, ISLE_STAND), (39, 6),
                   (33, 20), (40, CELL_STAND), (47, TERR_STAND)]:
        g.ent("gem", x, y)

    # --------------------------------------------------- the route (ADR 005)
    # Two `pad_bird`s, so neither names a waypoint on its own -- Grid._waypoints
    # refuses a type there are several of -- and each carries a mark on its own
    # tile. Standing on that tile is what fires the pad, so the hop that
    # arrives is the hop that transforms and prove.gd checks the next hop's
    # declared form against what actually happened.
    #
    # Flight hops are SHORT and most of their waypoints are in mid-air. The
    # prover searches bird flight with eighteen actions per macro and no floor
    # to prune against, so a ten-tile hop is a cheap search and a thirty-tile
    # one is a budget. Every long crossing here is cut at the place the body
    # has to be anyway: the mouth of a draught, the middle of the lane, a perch.
    k.mark("scree_pad", 9, SCREE_STAND)                     # pad_bird
    _air_mark(k, "chim_low", 9, 22)
    _air_mark(k, "chim_high", 9, 16)
    k.mark("crev_foot", CREV_X0 + 1, GALL_STAND, form="frog")
    k.mark("tread_one", CREV_X0 + 1, TREAD_ROW - 1, form="frog")
    k.mark("tread_two", CREV_X0 + 1, TREAD_ROW - TREAD_RISE - 1, form="frog")
    k.mark("hall_pad", 20, HALL_STAND, form="frog")         # pad_bird
    k.mark("lip", LIP_X1, LIP_STAND, form="bird")
    _air_mark(k, "curtain_out", THERM_X0 + 1, 10)   # through the sinking air,
                                                    # into the thermal's throat
    _air_mark(k, "thermal_lip", THERM_X0 + 2, LANE_Y0)
    _air_mark(k, "lane_mid", ISLE_X0, LANE_Y0 + 1)
    k.mark("island", ISLE_X0 + 1, ISLE_STAND, form="bird")
    _air_mark(k, "flue_mouth", FLUE_X0 + 1, FLUE_TOP + 1)
    k.mark("cellar_east", FLUE_X0 + 1, CELL_STAND, form="bird")
    _air_mark(k, "cellar_wind", BREAK_X + 3, CGUST_Y0 - 1)
    k.mark("cellar_oasis", OASIS_X0 + 1, CELL_STAND, form="bird")
    _air_mark(k, "thermal_mid", THERM_X0 + 1, CELL_TOP)
    _air_mark(k, "thermal_top", THERM_X0 + 1, LANE_Y0)
    _air_mark(k, "sky_east", 39, CAN_TOP + 2)

    g.route("spawn", "scree_pad", form="human")        # hop the vent pit
    g.route("scree_pad", "chim_low", form="bird")      # the cold climb, 1 of 3
    g.route("chim_low", "chim_high", form="bird")
    g.route("chim_high", "pad_frog", form="bird")      # 14 tiles, 75 stamina
    g.route("pad_frog", "crev_foot", form="frog")
    g.route("crev_foot", "tread_one", form="frog")     # 3 tiles, no stamina
    g.route("tread_one", "tread_two", form="frog")
    g.route("tread_two", "hall_pad", form="frog")      # a full bar, by pad
    g.route("hall_pad", "lip", form="bird")            # the launch, on rock
    g.route("lip", "curtain_out", form="bird")         # the curtain takes 2.8
    g.route("curtain_out", "thermal_lip", form="bird")  # the thermal gives it back
    g.route("thermal_lip", "lane_mid", form="bird")    # 184 px/s downwind
    g.route("lane_mid", "island", form="bird")         # the oasis
    g.route("island", "flue_mouth", form="bird")
    g.route("flue_mouth", "cellar_east", form="bird")  # the dive. One way.
    g.route("cellar_east", "cellar_wind", form="bird")
    g.route("cellar_wind", "cellar_oasis", form="bird")  # over the broken floor
    g.route("cellar_oasis", "thermal_mid", form="bird")  # 22 tiles for nothing
    g.route("thermal_mid", "thermal_top", form="bird")
    g.route("thermal_top", "sky_east", form="bird")
    g.route("sky_east", "exit", form="bird")           # over the flue's mouth

    return g, k


def check(k, verbose=True):
    """Everything the kit can say about the level before the prover runs.

    Not proof -- tools/prove.sh is. This is the cheap filter for the class of
    error this project has shipped six times. There is no `reconfig_check` here
    because there is no switch block in the level: what gates it is current
    speed, which the flood fills are blind to and therefore generous about.
    """
    if verbose:
        missing = k.pal.missing()
        print("  palette      %s"
              % ("no substitutions" if not missing else missing))
    return k.audit(strict_verbs=True)


if __name__ == "__main__":
    grid, kit = heights_2()
    for line in check(kit):
        print(line)
    write(LEVEL_ID, grid, LEVEL_NAME, music="world3")
