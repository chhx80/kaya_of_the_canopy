#!/usr/bin/env python3
"""nest_2 -- THE SWITCHYARD.  World 5, THE OBSIDIAN NEST, second level.

Self-contained: running this file under the project python writes
levels/nest_2.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `nest_2()` returning `(Grid, Kit)`,
the tuple that writer's `build()` expects -- it audits the kit before it writes.

    source tools/env.sh && "$PYVENV" tools/worlds/nest_2.py
    tools/prove.sh nest_2

WHAT THE LEVEL IS ABOUT
-----------------------
nest_1 taught the lever: one throw, two doors, both in the frame you are
standing in.  This is that sentence with the level in between -- SWITCH-BLOCKS
AT SCALE, made literal.  Two levers, six doors, four screens, and the doors a
lever moves are mostly somewhere you cannot see.  Nothing else: no current, no
draught, no breakable, no second form.  The whole vocabulary is

    gold    = group A = switch_block_a_on / _off   (ids 11 and 26)
    magenta = group B = switch_block_b_on / _off   (ids 12 and 27)

and the level is what you can build out of nothing but those, which is the
brief World 5's second level was given.

ONE LEVER PER GROUP, AND WHY THAT IS A HARD RULE AND NOT A STYLE
-----------------------------------------------------------------
nest_1 measured it and this file re-checks it in `_self_checks` (g):

    src/world/triggers/switch_trigger.gd  toggle(): `on = not on;
                                          world.set_switch(group, on)`
    tools/solver/sim.gd:363               `_set_switch(g, not world.switch_states[g])`

The trigger flips its OWN remembered state; the prover flips the WORLD's.  One
lever per group and those are the same number forever; two levers on a group
and the second one's `on` is stale the instant the first is thrown, so the game
re-asserts a state already in force and nothing moves while the prover toggles.
`tools/prove.sh` would pass a level `tools/itest.sh` cannot finish.

So scale cannot come from more levers.  It comes from the only place left:
ONE LEVER MOVING SEVERAL DOORS, in rooms that are not the room it is in.  Gold
moves three (the siding's east door, and two of the four plugs down the
gantry); magenta moves three (the cellar's west door, and the other two plugs).
That is the level.

THE CABIN, WHICH IS WHY BOTH LEVERS ARE IN ONE FRAME
------------------------------------------------------
`switch_a` stands on a nest_ledge at (29,25) over the cellar floor and
`switch_b` on another at (30,18) over the siding, two columns and seven rows
apart.  Screen D is cols 25-49 x rows 15-29, so BOTH LEVERS, the chain between
them, the cellar's west door and the siding's east door are in one frame: from
the foot of the chain a player can see the two things they can change and two
of the six things that changes.  That is this level's answer to "all switch
state must be readable at a glance" -- the state is legible because the
CONTROLS are in one place, and what is two rooms away is what has to be planned
rather than seen.

They are on treads rather than in the walking lane on purpose.
`SwitchTrigger._physics_process` toggles on OVERLAP with a 0.45 s cooldown, so
a lever set in a corridor is thrown by everyone who walks past it and thrown
again 27 frames later if they stop on it.  The trigger box is the BOTTOM TEN
PIXELS of its tile (`Rect2(tile*16 + (1,6), (14,10))`); a 22 px body walking
the floor two rows below reaches 22 px up from the row under the tread and
stops ten pixels short of it, so the lane under a tread is clean and the hop up
is a decision.  `_self_checks` (g) re-derives both halves of that.

THE SIX DOORS, AND WHAT EACH THROW COSTS
-----------------------------------------
Group 1 (A) starts ON and group 2 (B) starts OFF -- TileWorld's defaults, which
`tools/solver/sim.gd:reset()` seeds and `SwitchTrigger._ready()` agrees with --
so at spawn the SOLID blocks are `a_on` and `b_off`, and `a_off` and `b_on` are
the ghosts.

    beta   col 26, rows 23-27   b_on    the cellar's west door.  OPEN at spawn;
                                        throwing B SHUTS IT.  The commitment:
                                        after it there is no walking back west
                                        along the yard floor, and the level's
                                        shape says so -- everything else you
                                        need is east and up.
    sigma  col 37, rows 17-20   a_on    the siding's east door.  Shut at spawn,
                                        opened by A, and it is in the cabin's
                                        own frame: the one effect of a throw
                                        this level lets you watch.
    G1     col 38, rows 3-13    a_on    the gantry's east plug.  Opened by A.
    G2     col 26, rows 3-13    b_off   opened by B.
    G3     col 17, rows 3-13    a_off   OPEN at spawn and SHUT by A -- the
                                        reversal the whole level turns on.
    P      col  9, rows 3-13    b_off   the exit's door.  Opened by B.

Walking the gantry westward the four plugs alternate gold, magenta, gold,
magenta, and G1 and G3 are the same group in opposite senses, so NO
CONFIGURATION OPENS THE GANTRY END TO END.  Whatever you do at the cabin, the
gantry stops you at G3 -- and the way on from there is not a lever, it is a
hole in the floor.

THE CHUTES, WHICH ARE THE LEVEL'S REAL SECOND VERB
---------------------------------------------------
Four holes, none of them switched, each one draining a room that a shut gate
could otherwise seal:

    chute W   gantry cols 21-22 -> the west hall.  The one the route uses: with
              G3 shut it is the way on, and it lands you at the foot of the
              lift, looking up at the door you found shut in the first minute.
    chute M   gantry cols 34-35 -> the siding, west of sigma, four tiles from
              switch_b.  The gantry's middle segment always drains to a lever.
    chute E   siding col 42 -> the cellar.  The siding east always drains to a
              lever, so sigma can never seal anyone in.
    the lift  col 15, a nest_chain from the hall's floor to the gantry, in a
              shaft cut through fourteen rows of glass.  A chain and not a
              hole, because this one has to run BOTH ways.

That is the design rule this level is built to, and `_self_checks` (f) proves
it rather than asserting it: EVERY REGION ANY CONFIGURATION CAN CARVE EITHER
HOLDS THE EXIT OR DRAINS, WITHOUT A THROW, TOWARDS A LEVER.  A player who
throws the wrong thing loses a lap, never a save.

THE DECLARED ROUTE, AND THE TWO THROWS IT MAKES
------------------------------------------------
    1  spawn (3,27), walk east along the hall, over the vertical seam, through
       `beta` (open) into the cellar.
    2  up onto the tread: throw A.  `sigma` opens IN FRAME; G1 opens two
       screens away; G3 shuts.
    3  up the chain, onto the second tread: throw B.  P and G2 open; `beta`
       shuts behind and below.
    4  east along the siding through `sigma`, over chute E, up the chain at
       col 46 to the gantry.
    5  west along the gantry: G1 open, jump chute M, G2 open -- and G3 SHUT.
    6  drop chute W, thirteen rows, into the hall she started in.
    7  west to the lift, climb it, walk out through P.

Two throws, one per lever, and the prover is free to have made more: the
foundation's measurement says `ProverSearch._key()` carries `switch_bits`, so a
gate crossed in one configuration and re-crossed in the other is two states and
not one.  This route does not need that licence; it is recorded because the
route's shape should be the level's argument and not the gate's limit.

WHY reconfig_check IS GIVEN A DIFFERENT GOAL PER ROOM
------------------------------------------------------
`world_kit.reconfig_check`'s first question -- "is the goal reachable in at
least ONE of the four configurations" -- is the wrong question here, for
exactly the reason nest_1 records: G1 and G3 are one group in opposite senses,
so no single configuration opens the way out, and asking any room for the exit
would fail a level that is perfectly playable.  Each room is asked instead for
the thing that room is trying to reach, and the end-to-end question is answered
by `_escape()` in `_self_checks` (f), which searches (where you stand x which
switches are thrown) and may throw levers as it goes.

WHERE THE FLOORS SIT, AND THE TWO SEAMS
----------------------------------------
`CameraController` picks its screen from the body's CENTRE, so a 22 px body on
a floor whose cap row is a multiple of 15 has its feet on the horizontal seam
and its centre on the screen above -- which never draws the floor it stands on.
That is the defect ruins_4 shipped.  The stand rows here are 27 (cap 28), 25
and 18 (the treads), 20 (cap 21) and 13 (cap 14); `_self_checks` (b) fails the
build if any of them, or any entity, stands on a cap row that is a multiple
of 15.

The vertical seam is x=400, between cols 24 and 25.  Three hops cross it and
all three are FLAT WALKS along unbroken standable floor -- the hall's floor at
row 27 and the gantry's at row 13 -- so the 0.12 s flip freeze lands while she
is walking.  Every jump in the level is wholly inside one screen: chute M's
three-tile gap at cols 34-35, the one-tile hop over chute E at col 42, and both
tread hops.  `_self_checks` (c) re-derives that from the route.

The horizontal seam is y=240, between rows 14 and 15.  Three hops cross it: two
chain climbs and one fall.  All three are in SEAM_EXEMPT with their reasons --
a body on a chain and a body in a fourteen-row hole are the two bodies a freeze
cannot embarrass, because neither has an arc to lose.

WHY EVERY SWITCH BLOCK IS A DOOR AND NEVER A FLOOR
----------------------------------------------------
`tools/reachability.py` resolves a switch tile as NEVER SOLID -- `Level.solid()`
returns False for anything carrying a `switch_group` -- because the filter
cannot know which half of a group is up.  So a switch block may be a wall the
filter generously assumes is open, and it may never be a FLOOR: a route that
stands on one is a route the filter reports as missing, in every configuration
(ADR 005: it may only ever under-report).

The first draft of this level had a three-tile `a_on` HATCH set into the
siding's floor -- gold solid is a floor you walk over, gold ghost is a hole you
fall through -- and it is exactly the shape that rule forbids.  It is gone.
`_self_checks` (d) encodes the strongest form of the rule a grid can carry:
every switch tile has rock, or the rest of its own plug, directly over its
head, so nothing can be on top of one in any configuration.  The holes in this
level's floors are holes, cut in rock, and no lever moves them.

THE PALETTE
------------
`Palette.char()` resolves a tile NAME through the flat, jungle-derived `legend`
key of data/level_legend.json, so THE OBSIDIAN NEST's own names have no
character there and fall through to UNDERSTUDY -- where `solid` would emit 's'
(nest_plate, the second solid) and `bg` would emit 'r' (nest_vein, a background
accent).  That is the memory note "world_kit ruins palette emits wrong stone",
in World 5.  So every role is declared as the JUNGLE tile that owns the
character the nest tileset binds to the art we want.

The mass is obsidian ('#') and the built walls are nest_block ('d'), which is
the correction nest_1's captures forced and the agreement its docstring records
for this file: nest_plate ('s') is an object and not a mass, so it does not
appear here at all.  Every gate's head and sill is nest_block, so a doorway
reads as masonry cut into glass and the plug in it reads as the thing that
moves.  `Palette.missing()` is empty, `substituted` stays empty, and the level
serialises "tileset": "nest".
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                      # noqa: E402
import world_kit                                        # noqa: E402
from world_kit import Kit, Palette, Probe               # noqa: E402

LEVEL_ID = "nest_2"
LEVEL_NAME = "THE SWITCHYARD"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the nest role character.
## A character map, not an art claim: the art comes from `"tileset": "nest"` at
## load time.  See THE PALETTE above.
NEST_W5 = Palette("obsidian_nest", {
    "bg": "bg_leaves",              # 'L' -> 282 nest_wall
    "solid": "grass_top",           # '#' -> 280 obsidian      (the mass)
    "solid_alt": "stone_mossy",     # 'S' -> 281 obsidian_hot  (the hot face)
    "block": "dirt",                # 'd' -> 283 nest_block    (built walls)
    "packed": "stone",              # 's' -> 290 nest_plate    (declared, unused)
    "oneway": "wood_platform",      # '=' -> 286 nest_ledge
    "ladder": "vine",               # '|' -> 288 nest_chain
    "hazard": "spikes",             # '^' -> 287 nest_shard
    "breakable": "crate",           # 'c' -> 291 nest_crust    (declared, unused)
    "decor": "tree_trunk",          # 'T' -> 285 nest_flue
    "void": "bg_dark",              # 'X' -> 284 nest_void
    "shoulder": "cracked_stone",    # 'k'  shared (unused)
    "rubble": "rubble",             # 'o'  shared (unused)
    "water": "water",               # 'w'  shared (this level is dry)
    "water_top": "water_top",       # '~'  shared
    "switch_a_on": "switch_block_a_on",    # 'A' shared, 11
    "switch_a_off": "switch_block_a_off",  # 'a' shared, 26
    "switch_b_on": "switch_block_b_on",    # 'B' shared, 12
    "switch_b_off": "switch_block_b_off",  # 'b' shared, 27
})

# ---------------------------------------------------------------- the shape
## Every number the geometry and the checks share, in one place: "G1 and G3 are
## the same group in opposite senses" is a claim about arithmetic, not prose.

SEAM_COL = 25                   # first column of the eastern screens (x=400)
SEAM_ROW = 15                   # first row of the lower screens (y=240)
EAST_WALL = 48                  # the level is cols 1..47

# -- the yard floor: the west hall and the cellar (screens C and D) ----------
YARD_CAP = 28
YARD_STAND = YARD_CAP - 1       # 27
HALL_X0, HALL_X1 = 1, 25        # the west hall, ten rows tall
HALL_TOP = 18
SPAWN = (3, YARD_STAND)
LIFT_COL = 15                   # the chain: hall floor -> the gantry
BETA_COL = 26                   # b_on, rows 23-27: the cellar's west door
CELL_X0, CELL_X1 = 27, 47       # the cellar
CELL_TOP = 23

TREAD_A = (28, 26, 3)           # x, row, w -- stand row 25
SWITCH_A = (29, 25)

# -- the siding (screen D) ---------------------------------------------------
SID_CAP = 21
SID_STAND = SID_CAP - 1         # 20
SID_X0, SID_X1 = 27, 47
SID_TOP = 17
TREAD_B = (29, 19, 3)           # stand row 18
SWITCH_B = (30, 18)
CHAIN1_COL = 32                 # cellar <-> siding
SIGMA_COL = 37                  # a_on, rows 17-20: the siding's east door
CHUTE_E = 42                    # one tile of the siding's floor, missing
CHAIN2_COL = 46                 # siding <-> gantry, across the horizontal seam

# -- the gantry (screens A and B) -------------------------------------------
GAN_CAP = 14
GAN_STAND = GAN_CAP - 1         # 13
GAN_TOP = 3                     # an eleven-row hall, cols 1..47
P_COL = 9                       # b_off: the exit's door
Q_COL = 13                      # a_on: the door before it, and the reason the
                                # exit needs BOTH levers thrown
G3_COL = 17                     # a_off: open at spawn, shut by A
G2_COL = 26                     # b_off
G1_COL = 38                     # a_on
CHUTE_W = (21, 2)               # x, w -- down into the west hall
CHUTE_M = (34, 2)               # x, w -- down onto the siding, west of sigma
EXIT_TILE = (4, GAN_STAND)

## (col, solid_when, group) for every plug, in the order the gantry meets them
## going west.  `_self_checks` (e) reads this table rather than the prose.
PLUGS = [
    (BETA_COL, "on", "b", CELL_TOP, YARD_STAND, "beta: the cellar's west door"),
    (SIGMA_COL, "on", "a", SID_TOP, SID_STAND, "sigma: the siding's east door"),
    (G1_COL, "on", "a", GAN_TOP, GAN_STAND, "G1: the gantry's east plug"),
    (G2_COL, "off", "b", GAN_TOP, GAN_STAND, "G2"),
    (G3_COL, "off", "a", GAN_TOP, GAN_STAND, "G3: the reversal"),
    (Q_COL, "on", "a", GAN_TOP, GAN_STAND, "Q: the lift's west door"),
    (P_COL, "off", "b", GAN_TOP, GAN_STAND, "P: the exit's door"),
]

## What tools/solver/sim.gd seeds before a switch entity is touched: TileWorld's
## own defaults, group 1 ON and group 2 OFF.  Both levers declare the same, so
## SwitchTrigger._ready() agrees.
START_CFG = {1: True, 2: False}

## Every nest_vein tile: this level's light.  Each one is an AIR tile on the bg
## layer with rock beside it, and `_hot()` bands that rock with obsidian_hot,
## which is the tile that actually emits -- `AmbienceLayer._collect_emissive`
## scans the fg and 289 is a background tile by its own art.  nest_1 settled
## that; `_self_checks` (h) re-checks it here.
VEINS = [
    (2, 27), (8, 27), (12, 27), (19, 27), (23, 27),      # the west hall's floor
    (25, 19), (1, 22),                                   # the hall's far walls
    (28, 27), (35, 27), (40, 27), (45, 27),              # the cellar
    (27, 20), (34, 20), (40, 20), (45, 20),              # the siding
    (6, 13), (12, 13), (20, 13), (24, 13),               # the gantry, west half
    (30, 13), (37, 13), (44, 13),                        # and east
    (7, 3), (25, 3), (39, 3),                           # its roof
]

## Niches: relief cut upward into a roof.  They have no floor of their own, so
## nothing can stand in one and the pocket check skips them -- which is what
## makes a 2-tile niche legal where a 2-tile ROOM would be a squeeze.
## `_self_checks` (i) re-derives that.
## A niche is cut INTO a roof, which means the rows ABOVE the room's top row of
## air -- the first draft put the cellar's at rows 23-24, which is the cellar's
## AIR, and the clear_rect took two tiles out of the chain at col 32 and
## disconnected the two levers from each other.  Every entry here is checked
## against the chains and the chutes by hand and against the grid by (i).
NICHES = [
    (4, 1, 3, 2), (10, 1, 3, 2), (23, 1, 2, 2),          # the gantry's roof
    (30, 1, 3, 2), (41, 1, 3, 2),
    (5, 16, 4, 2), (11, 16, 3, 2), (17, 16, 3, 2),       # the west hall's roof
    (29, 16, 3, 1), (41, 16, 3, 1),                      # the siding's roof
    (35, 22, 3, 1), (44, 22, 2, 1),                      # the cellar's roof:
]                                                        # one tile, because the
                                                         # siding's floor is the
                                                         # other side of it


def _hot(k):
    """Band the rock a vein touches with obsidian_hot.

    280 and 281 are both plain `solid` -- the same tile to every flag-reading
    checker -- so this is colour and nothing else.  Generated from VEINS rather
    than listed by hand, because the claim is "the glass is hot WHERE THE VEIN
    IS" and a hand-written band drifts off its vein the first time one moves.

    Only the mass and the built walls are repainted: a ledge, a chain, a shard
    or a switch block next to a vein keeps its own art, because each of those
    is a verb and a recoloured verb stops reading as itself.
    """
    g = k.g
    mass, built, hot = k.ch("solid"), k.ch("block"), k.ch("solid_alt")
    for x, y in VEINS:
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < g.w and 0 <= yy < g.h and g.fg[yy][xx] in (mass, built):
                g.put(xx, yy, hot)


def _tread(k, spec, group):
    """A nest_ledge two rows over a walking lane, with a lever on it.

    Two tiles is the human's measured rise (LIMITS["human"]["rise"] = 2, apex
    2.78 tiles), and the ledge is a `oneway` so the hop up is made STRAIGHT UP
    through the tread from the tile below -- which is the only kind of rise
    `path_clear` models in the start column.
    """
    x, row, w = spec
    k.ledge(x, row, w)
    for xx in range(x, x + w):
        k._claim("step", "up through the tread at (%d,%d)" % (x, row),
                 x1=xx, y1=row + 1, x2=xx, y2=row - 1, form="human")
    return x, row - 1, w


def _plug(k, col, top, stand, group, solid_when, why):
    """A door with no key: a column of switch blocks filling a corridor.

    Full height, always.  A plug one tile short of its own roof is the defect
    this world is most able to produce, because a switch block LOOKS like a
    wall whatever it is doing.  The head and sill are drawn in nest_block so
    the opening reads as masonry cut into glass -- the legibility correction
    nest_1's captures forced.
    """
    k.switch_gate(col, stand, stand - top + 1, group=group, solid_when=solid_when)
    k.put(col, top - 1, "block")
    k.put(col, stand + 1, "block")
    k.note("%s at col %d: switch_block_%s_%s, %d tiles, rows %d-%d"
           % (why, col, group, solid_when, stand - top + 1, top, stand))
    return col


def nest_2():
    g = Grid(W, H, tileset="nest")
    k = Kit(g, NEST_W5, form="human")

    # ------------------------------------------------------------- the rock
    # Carved rather than built: a level cut out of rock has a tiny reachable
    # state space, so a prover hop that fails exhausts its frontier instead of
    # spending its whole budget wandering.  The mass is obsidian and nothing
    # else -- see THE PALETTE.
    k.fill_bg("bg")
    k.fill_solid("solid")
    k.shell(1, "solid")
    k.rect(EAST_WALL, 0, 1, H, "solid")

    # ============================================ THE YARD FLOOR (rows 18-28)
    # The west hall is ten rows tall and the cellar five, with `beta` in the
    # step between them.  One floor runs under both, cols 1..47.
    k.clear_rect(HALL_X0, HALL_TOP, HALL_X1 - HALL_X0 + 1, YARD_CAP - HALL_TOP)
    k.clear_rect(CELL_X0, CELL_TOP, CELL_X1 - CELL_X0 + 1, YARD_CAP - CELL_TOP)
    k.floor(HALL_X0, YARD_CAP, CELL_X1 - HALL_X0 + 1, depth=1)

    # ================================================= THE SIDING (rows 17-21)
    k.clear_rect(SID_X0, SID_TOP, SID_X1 - SID_X0 + 1, SID_CAP - SID_TOP)
    k.floor(SID_X0, SID_CAP, SID_X1 - SID_X0 + 1, depth=1)

    # ================================================= THE GANTRY (rows 3-14)
    k.clear_rect(1, GAN_TOP, CELL_X1, GAN_CAP - GAN_TOP)
    k.floor(1, GAN_CAP, CELL_X1, depth=1)

    # ------------------------------------------------------------ the chutes
    # Cut AFTER the floors they are holes in, and none of them is switched:
    # these are what make every room in the level drain towards a lever.  See
    # THE CHUTES in the docstring, and `_self_checks` (f), which proves it.
    #
    # chute W drops thirteen rows into the west hall; chute M drops three onto
    # the siding, four tiles from switch_b; chute E drops six into the cellar.
    k.clear_rect(CHUTE_W[0], GAN_CAP, CHUTE_W[1], HALL_TOP - GAN_CAP)
    k.clear_rect(CHUTE_M[0], GAN_CAP, CHUTE_M[1], SID_TOP - GAN_CAP)
    k.clear_rect(CHUTE_E, SID_CAP, 1, CELL_TOP - SID_CAP)
    # The one the route jumps rather than falls down, declared so the kit
    # checks its width against the human's measured reach.
    k.gap(CHUTE_M[0], GAN_STAND, CHUTE_M[1], form="human",
          landing_w=G2_COL + 1 - (CHUTE_M[0] - 1))
    k.gap(CHUTE_E, SID_STAND, 1, form="human")

    # ------------------------------------------------------------ the chains
    # Drawn after every floor, because each punches through one: a ladder
    # written first and capped afterwards is the draw-order bug `Kit.audit()`
    # exists to catch.  None of them is gated.
    k.climb(LIFT_COL, GAN_STAND, YARD_STAND, landing="right")
    k.climb(CHAIN1_COL, SID_STAND, YARD_STAND, landing="right")
    k.climb(CHAIN2_COL, GAN_STAND, SID_STAND, landing="left")

    # ------------------------------------------------------------- the treads
    _tread(k, TREAD_A, "a")
    _tread(k, TREAD_B, "b")

    # -------------------------------------------------------------- the plugs
    for col, solid_when, group, top, stand, why in PLUGS:
        _plug(k, col, top, stand, group, solid_when, why)

    # --------------------------------------------------------------- hazards
    # Two shard pits, both off every hop and both guarding something.  A hazard
    # is a wall to the prover -- `ProverSim.rejection()` refuses any state
    # touching one -- so this is enforced by construction and not by intent.
    k.rect(44, YARD_STAND, 2, 1, "hazard")        # the cellar's dead end
    k.rect(18, GAN_STAND, 2, 1, "hazard")         # the gantry's pocket at G3

    # -------------------------------------------------------------- dressing
    # The halls get `nest_void` behind them and the cut rooms keep the dark
    # `nest_wall`: everything the level opens out into reads as depth, and
    # everything cut into the rock reads as interior.  The flues hang from the
    # roofs and stop there -- a dark column running floor to ceiling beside a
    # climbable chain is the "looks like a passage, behaves like a wall" defect
    # with its coat inside out, which is what nest_1's captures caught.
    k.rect(HALL_X0, HALL_TOP, HALL_X1 - HALL_X0 + 1, YARD_CAP - HALL_TOP,
           "void", "bg")
    k.rect(1, GAN_TOP, CELL_X1, GAN_CAP - GAN_TOP, "void", "bg")
    for (nx, ny, nw, nh) in NICHES:
        k.clear_rect(nx, ny, nw, nh)
    for fx in (7, 23, 33, 43):
        k.rect(fx, GAN_TOP, 1, 4, "decor", "bg")
    for fx in (4, 11, 22):
        k.rect(fx, HALL_TOP, 1, 3, "decor", "bg")

    # ------------------------------------------------------------- the light
    for x, y in VEINS:
        if Probe(g).solid(x, y):
            raise world_kit.WorldKitError(
                "vein at (%d,%d) is behind solid rock ('%s'): nothing will "
                "ever see it" % (x, y, g.fg[y][x]))
        g.put(x, y, "r", "bg")
    _hot(k)

    # -------------------------------------------------------------- entities
    g.ent("player_spawn", *SPAWN)
    g.ent("switch_a", *SWITCH_A)
    g.ent("switch_b", *SWITCH_B)
    g.ent("exit", *EXIT_TILE)

    # Enemies live where the route does not and cannot follow it out.
    # walker.json is 32 px/s with `turn_at_ledge`, so a walker is pinned to the
    # shelf it spawns on; flyer.json has no chase at all, patrol_range 64 with
    # a 6 px bob, so one at row 20 stays at row 20 and the hall's floor seven
    # rows below is never in its path.
    g.ent("enemy_walker", 35, YARD_STAND)         # the cellar
    # The pocket behind G3 gets a FLYER and not a walker, which the captures
    # settled: a walker put there crossed its own shard pit, reached the lip of
    # chute W and knocked Kaya off the gantry -- and would have followed her
    # down the hole. flyer.json has no chase and this one patrols on Y, so it
    # guards the gem above the shards and stays in the pocket forever.
    g.ent("enemy_flyer", 19, 9, axis="y", range=32)
    g.ent("enemy_flyer", 9, 20, axis="x", range=48)     # over the west hall
    g.ent("enemy_flyer", 40, 8, axis="y", range=40)     # over the gantry east

    # NO GEM SHARES A TILE WITH A LEVER.  Pickup sprites draw over the
    # trigger's, and the first captures of the cabin had a blue gem sitting
    # exactly where switch_b is -- the one object in the frame the room exists
    # to show.  Both cabin gems sit one tile along their own tread instead.
    g.ent("heart", 47, YARD_STAND)                # past the cellar's shards:
                                                  # a 3-tile hop, the human's
                                                  # measured reach, off route
    g.ent("heart", 2, GAN_STAND)                  # past the exit's door
    for (x, y) in [(2, YARD_STAND), (9, YARD_STAND), (18, YARD_STAND),
                   (24, YARD_STAND), (28, 25), (31, YARD_STAND),
                   (38, YARD_STAND), (42, YARD_STAND),
                   (28, SID_STAND), (31, 18), (35, SID_STAND),
                   (40, SID_STAND), (45, SID_STAND),
                   (45, GAN_STAND), (36, GAN_STAND), (30, GAN_STAND),
                   (24, GAN_STAND), (20, GAN_STAND), (11, GAN_STAND),
                   (6, GAN_STAND)]:
        g.ent("gem", x, y)

    # --------------------------------------------------- the route (ADR 005)
    # Fourteen hops.  There is exactly one `switch_a` and one `switch_b` in the
    # level, so both are waypoints the route can NAME -- which is not a
    # convenience: the foundation measured the same crossing at 13 expansions
    # named and 19,227 unnamed, because a named lever cuts the hop at the tile
    # where the world changes instead of asking one search to find a gate, a
    # lever and the far side of the gate at once.
    k.mark("hall_east", HALL_X1 - 1, YARD_STAND)         # (24,27), before beta
    k.mark("cellar_west", CELL_X0 + 1, YARD_STAND)       # (28,27)
    k.mark("chain1_top", CHAIN1_COL, SID_STAND)          # (32,20)
    k.mark("sigma_west", SIGMA_COL - 1, SID_STAND)       # (36,20)
    k.mark("chute_e_east", CHUTE_E + 1, SID_STAND)       # (43,20)
    k.mark("chain2_foot", CHAIN2_COL, SID_STAND)         # (46,20)
    k.mark("chain2_top", CHAIN2_COL, GAN_STAND)          # (46,13)
    k.mark("g1_west", G1_COL - 1, GAN_STAND)             # (37,13)
    k.mark("chute_m_west", CHUTE_M[0] - 1, GAN_STAND)    # (33,13)
    k.mark("g2_west", G2_COL - 1, GAN_STAND)             # (25,13)
    k.mark("hall_drop", CHUTE_W[0], YARD_STAND)          # (21,27)
    k.mark("lift_foot", LIFT_COL, YARD_STAND)            # (15,27)
    k.mark("lift_top", LIFT_COL, GAN_STAND)              # (15,13)
    k.mark("vestibule", 11, GAN_STAND)                   # between Q and P

    g.route("spawn", "hall_east", form="human")          # the vertical seam, flat
    g.route("hall_east", "cellar_west", form="human")    # through beta
    g.route("cellar_west", "switch_a", form="human")     # A OFF: sigma and G1
                                                         # open, G3 shuts
    g.route("switch_a", "chain1_top", form="human")
    g.route("chain1_top", "switch_b", form="human")      # B ON: P and G2 open,
                                                         # beta shuts
    g.route("switch_b", "sigma_west", form="human")
    g.route("sigma_west", "chute_e_east", form="human")  # through sigma, over
                                                         # the chute
    g.route("chute_e_east", "chain2_foot", form="human")
    g.route("chain2_foot", "chain2_top", form="human")   # the horizontal seam
    g.route("chain2_top", "g1_west", form="human")       # through G1
    g.route("g1_west", "chute_m_west", form="human")     # OVER chute M
    g.route("chute_m_west", "g2_west", form="human")     # through G2, over the
                                                         # vertical seam
    g.route("g2_west", "hall_drop", form="human")        # DOWN chute W: G3 is shut
    g.route("hall_drop", "lift_foot", form="human")
    g.route("lift_foot", "lift_top", form="human")       # the horizontal seam
    g.route("lift_top", "vestibule", form="human")       # through Q
    g.route("vestibule", "exit", form="human")           # through P

    return g, k


# ====================================================================== light
## The data/ambience.json entry this level is designed around, kept HERE
## because that file belongs to the integration pass and because the pool
## positions are a fact about the geometry above.  `main()` prints it.
##
## GOLD IS THE THING YOU ACT ON.  nest_1 set that grammar and this level needs
## it more, because its levers are two and its doors are six: every authored
## pool on a LEVER or a DOOR is gold, every pool that is only the room being a
## room is ember, and nothing else is lit at all.  A player who has learned
## "walk towards the gold" in BLACK GLASS is being told the truth here.
AMBIENCE = {
    "_note": (
        "THE SWITCHYARD. World 5's second level and the first one whose "
        "subject is COMPOSITION: two levers, six doors, and most of the doors "
        "in rooms the lever cannot see. The light says which is which. GOLD "
        "pools sit on the two levers in the cabin and on all five gantry "
        "plugs plus the two yard doors -- the things a throw moves -- and "
        "EMBER pools sit on the three chutes and the two chain heads, which "
        "are the things that are always true. No `darkness` key: the dark is "
        "World 4's verb and this world's is the lever, so everything here is "
        "tint, vignette and the tiles that glow. The emissive entries are the "
        "level's own light and both are SOLID, because "
        "AmbienceLayer._collect_emissive scans the fg: 281 obsidian_hot is "
        "the heat banded around every nest_vein in the backdrop, and 287 "
        "nest_shard is the two pits, which glow for the reason deeps_1's "
        "spore does -- a hazard you cannot see is a coin toss. 289 nest_vein "
        "is NOT in here: it is a background tile by its own art and emits "
        "nothing from back there, which is the point."),
    "world": "obsidian",
    "air": {"ramp": "ember", "step": 1, "alpha": 0.28},
    "bg_tint": {"ramp": "ember", "step": 2, "mix": 0.70, "scale": 0.50},
    "fg_tint": {"ramp": "ember", "step": 5, "mix": 0.18, "scale": 0.92},
    "vignette": 0.36,
    "lights": [
        {"x": 29, "y": 25, "radius": 64, "ramp": "gold", "step": 5,
         "intensity": 0.48, "flicker": 0.18},
        {"x": 30, "y": 18, "radius": 64, "ramp": "gold", "step": 5,
         "intensity": 0.48, "flicker": 0.18},
        {"x": 26, "y": 25, "radius": 56, "ramp": "gold", "step": 4,
         "intensity": 0.32},
        {"x": 37, "y": 19, "radius": 56, "ramp": "gold", "step": 4,
         "intensity": 0.32},
        {"x": 38, "y": 9, "radius": 60, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 26, "y": 9, "radius": 60, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 17, "y": 9, "radius": 60, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 13, "y": 9, "radius": 60, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 9, "y": 9, "radius": 64, "ramp": "gold", "step": 6,
         "intensity": 0.52, "flicker": 0.10},
        {"x": 21, "y": 14, "radius": 72, "ramp": "ember", "step": 4,
         "intensity": 0.30},
        {"x": 34, "y": 14, "radius": 64, "ramp": "ember", "step": 4,
         "intensity": 0.26},
        {"x": 42, "y": 21, "radius": 56, "ramp": "ember", "step": 4,
         "intensity": 0.24},
        {"x": 15, "y": 20, "radius": 76, "ramp": "ember", "step": 5,
         "intensity": 0.30},
        {"x": 46, "y": 16, "radius": 64, "ramp": "ember", "step": 4,
         "intensity": 0.26},
        {"x": 3, "y": 26, "radius": 72, "ramp": "ember", "step": 5,
         "intensity": 0.32},
    ],
    "emissive": {
        "281": {"ramp": "ember", "step": 5, "intensity": 0.18, "radius": 24},
        "287": {"ramp": "ember", "step": 6, "intensity": 0.32, "radius": 26,
                "lift": 5},
    },
}


## Route hops allowed to change screen without being a flat walk, and why.
SEAM_EXEMPT = {
    ("chain2_foot", "chain2_top"):
        "a climb, not a hop: seven rows of nest_chain at col 46. The 0.12 s "
        "flip freeze at y=240 leaves her hanging on the chain in the same "
        "column with nothing to miss, which is why both of this level's deck "
        "changes are chains and not staircases.",
    ("lift_foot", "lift_top"):
        "the same, fourteen rows of it, in a shaft cut through solid glass: "
        "there is nowhere for a frozen frame to put her but where she already "
        "is.",
    ("g2_west", "hall_drop"):
        "a fall, not a hop: she walks west off the gantry into chute W and "
        "drops thirteen rows down a two-column hole into the hall she started "
        "in. The freeze happens in mid-fall with rock either side.",
}


## Entries `reconfig_check` is run from: every room a shut gate makes, and both
## sides of each one.  Each is swept over all four configurations by
## reconfig_check itself.  Every one of them stands on ROCK rather than on a
## switch block -- an entry the flood cannot legally stand in reports an empty
## room instead of a trap.
##
## The GOAL is per-room, for the reason the docstring gives at length: G1 and
## G3 are one group in opposite senses, so no single configuration opens the
## level end to end and asking any room for the exit would fail a level that is
## perfectly playable.  The end-to-end question is `_escape()` in (f).
##
## THE EXIT CHAMBER (cols 1-8, west of P) IS DELIBERATELY ABSENT.  It holds no
## lever, so reconfig_check would call it stranded in every configuration where
## P is shut -- and it holds the EXIT, so a player standing in it has already
## finished.  `_escape()` seeds it anyway and answers the question properly.
RECONFIG_ENTRIES = [
    ("the west hall (spawn)",           SPAWN,                   SWITCH_A),
    ("the hall, under chute W",         (21, YARD_STAND),        SWITCH_A),
    ("the cellar",                      (28, YARD_STAND),        SWITCH_B),
    ("the cellar's dead end",           (47, YARD_STAND),        SWITCH_A),
    ("the siding, west of sigma",       (34, SID_STAND),         SWITCH_A),
    ("the siding, east of sigma",       (44, SID_STAND),         SWITCH_A),
    ("the gantry, east of G1",          (44, GAN_STAND),         SWITCH_B),
    ("the gantry, between G1 and G2",   (30, GAN_STAND),         SWITCH_B),
    ("the gantry, between G2 and G3",   (24, GAN_STAND),         SWITCH_A),
    ("the lift's head (between G3, Q)", (16, GAN_STAND),         SWITCH_A),
]


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
        elif e["type"] == "exit" or e["type"].startswith("switch_"):
            where[e["type"]] = {"x": e["x"], "y": e["y"]}
    return where


def _switch_tiles(g):
    """Every switch-block tile in the grid, as (x, y, char)."""
    chars = {NEST_W5.char(r) for r in
             ("switch_a_on", "switch_a_off", "switch_b_on", "switch_b_off")}
    return [(x, y, g.fg[y][x])
            for y in range(g.h) for x in range(g.w)
            if g.fg[y][x] in chars]


def _escape(k, start, goal, form="human", cfg=None):
    """Can the player always still finish, from every state they can reach?

    A search over (where you are standing, which switches are thrown) rather
    than over configurations one at a time.  From the start state: flood; if
    the goal is in the flood, this state WINS.  For every lever the flood
    touches, flipping it is an edge to a new state.  The level is softlock-free
    from `start` when every state reachable from it can still reach a winning
    one.

    Returns the states that cannot, each as (where, config) -- literally a list
    of places the player can stand with no way to finish.  Adapted from
    nest_1's `_escape`, which is the shape this world needs and which this
    level needs more: six doors and four holes is more geometry than a
    per-configuration check can hold in one question.

    Filter and not proof, for the reason `world_kit.reachable_set` gives about
    itself -- but it is the question tools/prove.sh structurally cannot ask,
    because the prover only ever plays the route that was declared.
    """
    levers = [(int(e["x"]), int(e["y"]), 1 if e["type"] == "switch_a" else 2)
              for e in k.g.entities if e["type"] in ("switch_a", "switch_b")]
    start_state = (tuple(start), tuple(sorted((cfg or START_CFG).items())))
    seen, order, wins, edges = {start_state}, [start_state], set(), {}
    stack = [start_state]
    while stack:
        state = stack.pop()
        where, flat = state
        config = dict(flat)
        flood = k.reachable_set(where, form=form, switches=config)
        if tuple(goal) in flood:
            wins.add(state)
        out = []
        for lx, ly, grp in levers:
            if not any((lx + dx, ly + dy) in flood
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            nxt = dict(config)
            nxt[grp] = not nxt[grp]
            nstate = ((lx, ly), tuple(sorted(nxt.items())))
            out.append(nstate)
            if nstate not in seen:
                seen.add(nstate)
                order.append(nstate)
                stack.append(nstate)
        edges[state] = out
    safe = set(wins)
    changed = True
    while changed:
        changed = False
        for state in order:
            if state in safe:
                continue
            if any(n in safe for n in edges.get(state, ())):
                safe.add(state)
                changed = True
    return [(s[0], dict(s[1])) for s in order if s not in safe]


def _self_checks(g, k, verbose=True):
    p = Probe(g)
    bad = []

    # (a) A standable tile with one tile of headroom reads as a passage and
    # behaves as a wall (defect 2).  tests/test_level_validity.gd checks
    # exactly this; catching it here costs milliseconds instead of a Godot boot.
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

    # (b) Everything the player must touch needs a body's worth of room over
    # it, and must not stand on a floor the screen it is drawn on does not
    # contain -- the defect ruins_4 shipped.
    must = {"exit", "player_spawn", "switch_a", "switch_b", "gem", "heart",
            "enemy_walker", "enemy_flyer"}
    for e in g.entities:
        if e["type"] not in must:
            continue
        x, y = e["x"], e["y"]
        if not p.clear(x, y, 2):
            bad.append("%s at (%d,%d) has no two tiles of headroom"
                       % (e["type"], x, y))
        if e["type"] == "enemy_flyer":
            continue                      # it does not stand on anything
        if (p.solid(x, y + 1) or p.oneway(x, y + 1)) and (y + 1) % 15 == 0:
            bad.append("%s at (%d,%d) stands on cap row %d, a screen boundary: "
                       "its centre lands on the screen above and the floor is "
                       "never drawn" % (e["type"], x, y, y + 1))
    for kind, c in k.claims:
        if kind == "stand" and (c["y"] + 1) % 15 == 0:
            bad.append("%s: stand row %d sits on cap row %d, a screen boundary"
                       % (c["why"], c["y"], c["y"] + 1))

    # (c) NO ON-FOOT HOP CROSSES A SCREEN SEAM MID-JUMP.  A hop whose ends are
    # on different screens has to be a flat walk along unbroken standable
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
                           "(%d,%d) is not standable, so it is a jump and not "
                           "a walk" % (hop["from"], hop["to"], x, y))
                break

    # (d) NO SWITCH BLOCK IS EVER A FLOOR.  tools/reachability.py resolves a
    # switch tile as never solid, so a route that stands on one is a route it
    # reports as missing in every configuration.  The strongest form of that
    # rule a grid can carry: every switch tile has rock (or the rest of its own
    # plug) directly over its head.  Checked with the switches resolved BOTH
    # ways, because "solid" is a property of a configuration and "has rock
    # above it" is not.  The hatch this level's first draft had -- three tiles
    # of `a_on` set into the siding's floor -- is what this check deleted.
    for x, y, ch in _switch_tiles(g):
        above = g.fg[y - 1][x] if y > 0 else "#"
        if above == ch:
            continue
        for cfg in ({1: True, 2: True}, {1: False, 2: False}):
            if not Probe(g, switches=cfg).solid(x, y - 1):
                bad.append("switch block at (%d,%d) has '%s' over it, which is "
                           "not solid in every configuration: something could "
                           "stand on a switch block, and the reachability "
                           "filter resolves one as never solid"
                           % (x, y, above))
                break

    # (e) THE SIX DOORS DO WHAT THE DOCSTRING SAYS, re-derived from the grid.
    # Each plug is solid in exactly the two configurations its own table row
    # claims, and -- the load-bearing one -- G1 and G3 are never open together,
    # which is what makes the gantry a thing you cannot walk end to end and the
    # chute the way on.
    for col, solid_when, group, top, stand, why in PLUGS:
        grp = 1 if group == "a" else 2
        for on in (True, False):
            cfg = {1: True, 2: False}
            cfg[grp] = on
            pr = Probe(g, switches=cfg)
            want = (on == (solid_when == "on"))
            for yy in range(top, stand + 1):
                if pr.solid(col, yy) != want:
                    bad.append("%s: with group %d %s the tile (%d,%d) is %s, "
                               "which is not what switch_block_%s_%s means"
                               % (why, grp, "ON" if on else "OFF", col, yy,
                                  "solid" if not want else "open",
                                  group, solid_when))
                    break
    for cfg in ({1: True, 2: True}, {1: True, 2: False},
                {1: False, 2: True}, {1: False, 2: False}):
        pr = Probe(g, switches=cfg)
        if not pr.solid(G1_COL, GAN_STAND) and not pr.solid(G3_COL, GAN_STAND):
            bad.append("with group 1 %s both G1 and G3 are open, so the gantry "
                       "can be walked end to end and chute W -- the whole "
                       "second half of the level -- is decoration"
                       % ("ON" if cfg[1] else "OFF"))

    # ... and the level cannot be finished without BOTH throws.
    start = k.reachable_set(SPAWN, form="human", switches=START_CFG)
    if EXIT_TILE in start:
        bad.append("the exit is reachable from the spawn in the starting "
                   "configuration: neither lever is load-bearing")
    if SWITCH_A not in start or SWITCH_B in start:
        if SWITCH_A not in start:
            bad.append("switch_a is not reachable from the spawn before any "
                       "throw, so the level cannot be started")
    for grp, other, name in ((1, 2, "switch_a"), (2, 1, "switch_b")):
        cfg = dict(START_CFG)
        cfg[grp] = not cfg[grp]
        if EXIT_TILE in k.reachable_set(SPAWN, form="human", switches=cfg):
            bad.append("with only %s thrown the exit is already reachable: "
                       "the other lever is decoration" % name)

    # (f) NO STATE THE PLAYER CAN REACH IS A DEAD END.  The end-to-end
    # question, asked over (where you stand x which switches are thrown), with
    # lever throws as edges.  This is what the four chutes are for.
    for where_, config in _escape(k, SPAWN, EXIT_TILE, "human"):
        bad.append("ESCAPE: standing at %s with switches %s there is no "
                   "sequence of flips that reaches %s -- that is a softlock"
                   % (where_, config, EXIT_TILE))

    # (g) ONE LEVER PER GROUP -- nest_1's measured hard rule -- and every lever
    # inside the box its own trigger draws.  SwitchTrigger.aabb() is
    # Rect2(tile*16 + (1,6), (14,10)); a 22 px human standing on the tile spans
    # 16y-6..16y+16, so it covers the box, but only if the lever is on the
    # floor it is walked into along, which is the trap ruins_4 shipped.
    groups = {}
    for e in g.entities:
        if e["type"] in ("switch_a", "switch_b"):
            groups.setdefault(e["type"], []).append((e["x"], e["y"]))
    for t in ("switch_a", "switch_b"):
        places = groups.get(t, [])
        if len(places) != 1:
            bad.append("%d %s entities at %s. SwitchTrigger.toggle() flips its "
                       "OWN remembered state and tools/solver/sim.gd flips the "
                       "WORLD's, so two levers on one group part company the "
                       "instant the first is thrown: prove.sh would pass a "
                       "level itest.sh cannot finish" % (len(places), t, places))
        for (sx, sy) in places:
            if not (p.solid(sx, sy + 1) or p.oneway(sx, sy + 1)):
                bad.append("%s at (%d,%d) has no floor under it: its trigger "
                           "box is the bottom 10 px of the tile and nothing "
                           "can stand in it" % (t, sx, sy))
            top = (sy + 1) * 16 - 22
            if top > sy * 16 + 6:
                bad.append("%s at (%d,%d): the human's body spans %d..%d and "
                           "the trigger box is %d..%d -- she walks past her "
                           "own lever" % (t, sx, sy, top, (sy + 1) * 16,
                                          sy * 16 + 6, sy * 16 + 16))
            # ... and the lane two rows under a tread stays clean, which is why
            # the levers are up there at all.
            body_top = (sy + 3) * 16 - 22
            if body_top <= sy * 16 + 16:
                bad.append("%s at (%d,%d): a body walking the lane two rows "
                           "below spans %d..%d and would reach into the "
                           "trigger box at %d..%d -- the lever throws itself"
                           % (t, sx, sy, body_top, (sy + 3) * 16,
                              sy * 16 + 6, sy * 16 + 16))

    # (h) Every vein is still a vein, still on the BACKGROUND, still visible
    # through open air, and still has the obsidian_hot band `_hot` owes it --
    # a bg tile emits nothing, and 281 is what does.
    hot = NEST_W5.char("solid_alt")
    for x, y in VEINS:
        if g.bg[y][x] != "r":
            bad.append("vein at (%d,%d) is '%s' on the bg, not 'r' -- something "
                       "was drawn over the level's light" % (x, y, g.bg[y][x]))
            continue
        if p.ch(x, y) == "r":
            bad.append("vein at (%d,%d) is on the FG: 289 is a full rock fill "
                       "and reads as furniture in a walking lane" % (x, y))
        if p.solid(x, y):
            bad.append("vein at (%d,%d) is behind solid rock" % (x, y))
        if not any(p.ch(x + dx, y + dy) == hot
                   for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))):
            bad.append("vein at (%d,%d) has no obsidian_hot beside it, so the "
                       "one thing that can emit there does not" % (x, y))

    # (i) The relief is relief and not geometry: a niche must have no floor of
    # its own, so nothing can stand in one and the pocket check in (a) skips it.
    for (x, y, w, h) in NICHES:
        for xx in range(x, x + w):
            if p.solid(xx, y + h):
                bad.append("niche at (%d,%d) %dx%d has a floor at (%d,%d): it "
                           "is a room, not relief, and a %d-tile room is a "
                           "squeeze" % (x, y, w, h, xx, y + h, h))

    if bad:
        raise world_kit.WorldKitError(
            "%s: %d self-check failure(s):\n  %s"
            % (LEVEL_ID, len(bad), "\n  ".join(bad)))
    if verbose:
        print("  self-checks  (a) pockets (b) headroom+seam rows (c) seam hops "
              "(d) no switch floor")
        print("               (e) six doors, G1/G3 never both open, both "
              "levers load-bearing")
        print("               (f) escape: no reachable state is a dead end "
              "(g) one lever per group")
        print("               (h) %d veins lit (i) %d niches are relief"
              % (len(VEINS), len(NICHES)))


def _reconfig(k, entry, goal, label, verbose=True):
    """`reconfig_check`, with the one answer it does not know about admitted.

    Its second question is "in every configuration reachable from here, is at
    least one SWITCH reachable" -- because in a level where the only way out of
    a room is a lever, a room with no lever in it is a softlock.  That is the
    right question almost everywhere and the wrong one in the west half of this
    level, for a reason that is the level's whole ending: with group 1 OFF and
    group 2 ON, the hall, the lift and the gantry west of G3 reach THE EXIT and
    no lever at all.  That is not a room the player cannot leave, it is the room
    the player leaves through the door.

    So this runs the kit's check, and if the only complaint is stranding, it
    re-asks for each stranded configuration whether the EXIT is in the flood.
    If it is, the state is a win and is reported as one; if it is not, the
    original error is re-raised untouched.
    """
    try:
        sizes = k.reconfig_check(entry, goal, form="human")
        if verbose:
            print("  reconfig     %-34s %s" % (label, sizes))
        return sizes
    except world_kit.WorldKitError as err:
        if "no switch is reachable" not in str(err) or "not reachable in ANY" in str(err):
            raise
        wins, sizes = [], {}
        for cfg in ({1: a, 2: b} for a in (True, False) for b in (True, False)):
            seen = k.reachable_set(entry, form="human", switches=cfg)
            key = (cfg[1], cfg[2])
            sizes[key] = len(seen)
            if not any((SWITCH_A[0] + dx, SWITCH_A[1]) in seen
                       or (SWITCH_B[0] + dx, SWITCH_B[1]) in seen
                       for dx in (-1, 0, 1)):
                if EXIT_TILE not in seen:
                    raise
                wins.append(key)
        if verbose:
            print("  reconfig     %-34s %s  (config(s) %s reach the EXIT and "
                  "no lever: that is the way out, not a trap)"
                  % (label, sizes, wins))
        return sizes


def check(k, verbose=True):
    """Everything the kit can say about this level before the prover runs.

    Not proof -- `tools/prove.sh` is.  This is the fast filter for the class of
    error this project has shipped six times, plus the question the prover
    structurally cannot answer: whether a configuration the player is allowed
    to leave the level in has sealed them away from a lever.
    """
    for label, entry, goal in RECONFIG_ENTRIES:
        _reconfig(k, entry, goal, label, verbose=verbose)
    return k.audit(strict_verbs=True)


def main():
    g, k = nest_2()
    for line in check(k):
        print(line)
    _self_checks(g, k)
    print("  palette      missing=%s substituted=%s"
          % (NEST_W5.missing() or "none", NEST_W5.substituted or "none"))
    write(LEVEL_ID, g, LEVEL_NAME, music="world5")
    print("--- data/ambience.json  levels[\"%s\"] ---" % LEVEL_ID)
    print(json.dumps(AMBIENCE, indent=6))


if __name__ == "__main__":
    main()
