#!/usr/bin/env python3
"""ruins_3 — TIDE GALLERY.  World 2, SUNKEN RUINS.

Run it on its own to rebuild the level:

    $PYVENV tools/worlds/ruins_3.py          # $PYVENV from tools/env.sh

It writes levels/ruins_3.json and nothing else.  `tools/build_levels.py` can
also call `ruins_3()` and hand the (Grid, Kit) tuple to its own `build()`; the
tuple is what asks for the kit audit.

-------------------------------------------------------------------------- air

The brief for this level is "air is the resource".  That sentence only means
something once you have read src/player/forms/form_fish.gd, because the code
does the opposite of what "a submerged gallery" suggests:

    if wet:  air_left = air_seconds        # water REFILLS the meter
    else:    air_left -= delta             # air DRAINS it

For a fish, water *is* breath.  `air_seconds` is 2.6 and it only ticks down
while the fish is out of the water, so a fish that never leaves the water never
spends a thing.  The constraint cannot come from the length of a swim.  It can
only come from the length of a DRY crossing.

So the gallery is flooded and broken into pools by courses of masonry whose
tops stand one tile proud of the waterline.  The fish crosses one by breaking
the surface (`surface_hop` -210 against gravity 900 is 24.5 px, so exactly one
16 px course and never two) and flopping over the top at `max_run` 40 px/s.
The pools are the checkpoints; the courses are what the meter is for.

Three dry crossings, and they are a progression:

    off the west shelf .... 2 tiles   you meet the meter and it does not bite
    the first course ...... 3 tiles   it bites; the bar is visibly half gone
    the portage ........... 4 tiles   about half of what the meter can buy

tools/prove.sh enforces all three: ProverSim.rejection() refuses any state in
which a fish's `air_left` has reached zero, so a crossing one tile too long
fails the gate rather than the player.  MEASURED with --route on this grid, the
terrace's ceiling is between eight and ten tiles of flop; the portage asks for
four.  The slack is deliberate, and tools/world_kit.py's own note on the frog's
4-tile step is the argument -- the prover finds the one input that works, so a
crossing it clears with a handful of frames to spare is provable and
unplayable.  The numbers are in REPORT.md section 4.2.

`out_of_water` is "revert", not "die", which is why none of this is cruel: a
fish that runs out turns back into Kaya on top of a wall, and a human can swim
(slowly) back to the one pad_fish.  Every current in here has a still-water
lane beside it for exactly that reason.

----------------------------------------------------------------- the currents

data/tiles.json: `>` pushes 68 px/s, `}` pushes 120.  The fish swims at 92.

    with a 68 lane .... 160 px/s   a dozen tiles in a second and a half
    into a 68 lane ....  24 px/s   the same dozen tiles in eight seconds
    into a 120 lane ... -28 px/s   you go backwards; it is a valve, not a swim

That table is the level.  Gallery one is a 68 lane four rows deep with still
water above and below it, so the trip out is quick and the trip back is a
different lane rather than a slower one -- a human makes 108 *
`water_move_scale` 0.62 = 66.96 px/s, which is LESS than the lane's 68, so a
Kaya who lost the fish form could never swim home through it.

The fork between pool three and pool four is the 120 valve: the covered
aqueduct is one-way and takes a second, the colonnade below it is
current-free, two-way, and carries the heart and most of the gems.  Both halves
have to work.  The route declares the aqueduct, because riding a current is
what World 2 is for; REPORT.md records the prove.sh runs over the colonnade,
forwards and backwards.

------------------------------------------------------------------ the screens

The level is 2x2 screens of 25x15 and the seam matters.  `CameraController`
derives the screen from the player's CENTRE and freezes the simulation for
SLIDE_TIME while it flips, so a route that runs ALONG a seam flips the camera
every time the body wobbles across it.  The first draft of this level put the
waterline at row 12 and every swim waypoint at row 14 -- one pixel-wobble from
the horizontal seam at y=240 -- and the captures are what showed it.

So the water is entirely below the seam, which is also what jungle_3 does:

    rows  0-14  screens A and B   the dry ruin: the way in, and the way out
    rows 15-29  screens C and D   the flooded gallery, every pool, every current

The surface hop's apex reaches row 15.8, eighteen pixels clear of the seam;
the only flips on the route are the four it should have -- in at the top left,
out at the top right, and the two courses.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))          # tools/

from gen_levels import Grid, write, legend_for      # noqa: E402
from world_kit import (                             # noqa: E402
    Kit, Palette, RUINS, ROLES, WorldKitError, tiles,
)


# --------------------------------------------------------------- the palette
#
# world_kit's `_Tiles` resolves a role's tile NAME to a character through
# data/level_legend.json's flat `legend` key, and that key is the *jungle*
# tileset by construction (ADR 002's amendment keeps it as a view for
# reachability.py and build_hub.py).  So RUINS.char("solid") asks for
# `ruin_stone`, does not find it in the jungle legend, and falls back to the
# `stone` understudy -- emitting 's', which in a ruins grid is `ruin_grate`.
# Every current role falls back to plain water, and `Kit.audit(strict_verbs)`
# then reports the whole world as substituted.
#
# The characters are right there: ADR 002's amendment landed the per-world
# legend, and `legend_for("ruins")` returns it.  This subclass is the few lines
# that use it.  It lives here and not in tools/world_kit.py because that file
# is not mine to edit; it is the same hand-off ADR 002 names for
# reachability.py and build_hub.py, and REPORT.md repeats it.
class RuinsLegend(Palette):
    """RUINS, resolved against the ruins legend instead of the jungle one."""

    def __init__(self):
        super().__init__(RUINS.world, RUINS.roles)
        legend = legend_for("ruins")
        # A legend may map several characters to one id; first wins, sorted, so
        # the choice does not depend on dict order.  Same rule as _Tiles.
        self._char_of_id = {}
        for ch in sorted(legend):
            self._char_of_id.setdefault(int(legend[ch]), ch)

    def char(self, role):
        want = self.name(role)
        tid = tiles().by_name.get(want)
        if tid is None:
            raise WorldKitError("no tile named '%s' in data/tiles.json" % want)
        ch = self._char_of_id.get(tid)
        if ch is None:
            raise WorldKitError(
                "tileset 'ruins' binds no character to '%s' (id %d) in "
                "data/level_legend.json" % (want, tid))
        return ch

    def missing(self):
        out = []
        for role in ROLES:
            if role not in self.roles:
                continue
            tid = tiles().by_name.get(self.roles[role])
            if tid is None or tid not in self._char_of_id:
                out.append((role, self.roles[role]))
        return out


# ------------------------------------------------------------------ geometry
#
# One waterline for the whole level.  Everything else is measured off it, so a
# row number below is never a magic number twice.

W, H = 50, 30

SEAM = 15            # first row of screens C and D; the water starts below it
CEILING = 14         # solid roof over the gallery
AIR_TOP = 15         # first clear row of the air above the water
SURFACE = 18         # the water_top row
DEEP_TOP = 19        # first fully submerged row
BED = 28             # the silt bed's cap row

COURSE = SURFACE - 1        # a course stands one tile proud of the water
COURSE_STAND = COURSE - 1   # and you stand on row 16

GAL_X0, GAL_X1 = 10, 40     # the flooded gallery's first and last column

LANE_X0, LANE_X1 = 11, 19       # gallery one's 68 px/s lane
LANE_Y0, LANE_Y1 = 19, 22

BANK1_X, BANK1_W = 22, 3        # the first course
FORK_X, FORK_W = 28, 9          # the masonry the fork is cut through
CHUTE_Y = DEEP_TOP              # the aqueduct's floor row (rows 18-19)
PORTAGE_X, PORTAGE_W = 41, 7    # the long crossing; this is the air pinch
KELP_X = 47                     # the way out


def _wet_mark(k, name, x, y, tall=2):
    """A swim waypoint.

    Not `Kit.mark`: that files a "stand" claim, and `Probe.standable` counts a
    water tile as standable, so a mark that quietly stopped being water would
    still pass.  A fish waypoint has to be WET -- `ProverSearch._reached`
    accepts arrival only when the body is `submerged()` -- so this files the
    claim that says so, the way `world_kit.colonnade` does.
    """
    k.g.mark(name, x, y)
    k._claim("wet", "swim waypoint '%s'" % name, x=x, y=y, tall=tall)
    return name


def ruins_3():
    """TIDE GALLERY — 2x2 screens.  Four pools, two courses of masonry, and the
    tide running east through both of them."""
    g = Grid(W, H, tileset="ruins")
    k = Kit(g, RuinsLegend(), form="human")

    # A carved level, not a built one: prove.gd notes that a small reachable
    # state space makes a failed search exhaust its frontier instead of burning
    # its whole budget wandering open sky, and this is a ruin anyway.
    k.fill_bg("bg")
    k.fill_solid("solid")

    # ------------------------------------------------- screen A: the way in
    # Two collapsed cells and a shaft, descending east.  Every step of it goes
    # east and down, which is also the direction the manhattan frontier wants
    # to go: the first draft ran west before it ran east and the search had to
    # climb out of the hole that made.
    k.clear_rect(1, 2, 8, 5)                    # cell one,  cols 1-8,  rows 2-6
    k.clear_rect(6, 7, 2, 2)                    # the chimney between them
    k.clear_rect(1, 9, 9, 5)                    # cell two,  cols 1-9,  rows 9-13
    k.clear_rect(8, CEILING, 2, 3)              # the shaft,  cols 8-9, rows 14-16
    for x in range(1, 9):
        k._claim("clear", "cell one", x=x, y=6, tall=2)
    for x in range(1, 8):
        k._claim("clear", "cell two", x=x, y=13, tall=2)
    k._claim("stand", "cell one's floor", x=2, y=6, form="human")
    k._claim("stand", "cell two's floor", x=7, y=13, form="human")
    k._claim("stand", "the shaft foot, on the west shelf",
             x=8, y=COURSE_STAND, form="human")

    # ------------------------------------------- screens C and D: the gallery
    gw = GAL_X1 - GAL_X0 + 1
    k.clear_rect(GAL_X0, AIR_TOP, gw, BED - AIR_TOP)        # rows 15-27
    k.rect(GAL_X0, SURFACE, gw, 1, "water_top")
    k.rect(GAL_X0, DEEP_TOP, gw, BED - DEEP_TOP, "water")   # rows 19-27
    k.rect(GAL_X0, BED, gw, H - BED, "packed")              # the silt bed

    # Gallery one: the tide runs east four rows down.  Still water above it and
    # below it, and that is the return lane -- see the module docstring.
    k.rect(LANE_X0, LANE_Y0, LANE_X1 - LANE_X0 + 1,
           LANE_Y1 - LANE_Y0 + 1, "cur_right")

    # The first course.  surface_hop clears exactly one tile; world_kit.bank
    # refuses two, which is defect 4's epitaph.
    k.bank(BANK1_X, SURFACE, BANK1_W, rise=1)

    # ------------------------------------------------- the fork
    # Upper: a covered aqueduct at 120 px/s.  92 < 120, so it is a valve.
    k.current_channel(FORK_X, CHUTE_Y, FORK_W, "right", height=2, fast=True)
    # The masonry it is buried in.  Without this the aqueduct's roof would be a
    # nine-tile dry ledge in the middle of a flooded hall: nine tiles at
    # 40 px/s is 3.6 s against a 2.6 s meter, so it would be a trap that looks
    # like a path.  Filling it in deletes the trap instead of signposting it.
    k.rect(FORK_X, AIR_TOP, FORK_W, COURSE - AIR_TOP, "solid")

    # Lower: the colonnade.  No current, passable both ways, and it is where
    # the heart and most of the gems are -- the aqueduct buys four seconds and
    # costs you the room.
    k.rect(29, 21, 2, 3, "solid")       # hangs from the aqueduct's floor
    k.rect(33, 25, 2, 3, "solid")       # rises from the bed
    for x in (29, 30):
        k._claim("wet", "colonnade: the pass under the hanging column",
                 x=x, y=BED - 1, tall=4)
    for x in (33, 34):
        k._claim("wet", "colonnade: the pass over the standing column",
                 x=x, y=24, tall=4)

    # The tide wells up against the eastern weir.  62 px/s of lift, stopping a
    # row short of the surface so it helps the fish rise without ever pushing
    # it out of the water and spending air it did not choose to spend.
    k.rect(GAL_X1, DEEP_TOP + 1, 1, BED - DEEP_TOP - 2, "cur_up")

    # ------------------------------------------- screen B: the portage, and out
    k.bank(PORTAGE_X, SURFACE, PORTAGE_W, rise=1)
    k.clear_rect(42, 1, 6, 4)                   # the exit cell,  rows 1-4
    k.clear_rect(43, 8, 4, 2)                   # a landing off the kelp
    k.clear_rect(KELP_X, 5, 1, CEILING - 5 + 1)  # the kelp shaft, rows 5-14
    for x in range(43, 47):
        k._claim("clear", "the exit cell", x=x, y=4, tall=2)
        k._claim("clear", "the kelp landing", x=x, y=9, tall=2)
    k._claim("stand", "the kelp landing", x=45, y=9, form="human")
    # Drawn AFTER the bank, the cell and the landing, all of which write over
    # col 47.  jungle_3 shipped the opposite order once and lost the top two
    # tiles of its vine.
    k.climb(KELP_X, 4, COURSE_STAND, landing="left")

    # ------------------------------------------------------------- dressing
    k.rect(GAL_X0, SURFACE, gw, BED - SURFACE, "void", "bg")
    for x in (13, 26, 39):
        k.rect(x, AIR_TOP, 1, BED - AIR_TOP, "decor", "bg")
    for x in (3, 44):
        k.rect(x, 2, 1, 5, "decor", "bg")

    # -------------------------------------------------------------- entities
    g.ent("player_spawn", 2, 6)
    g.ent("pad_fish", 8, COURSE_STAND)
    g.ent("pad_human", 45, COURSE_STAND)
    g.ent("exit", 43, 4)

    g.ent("enemy_swimmer", 17, 24)
    g.ent("enemy_swimmer", 26, 22)
    g.ent("enemy_swimmer", 34, 23)
    g.ent("heart", 45, 9)
    for (x, y) in [(5, 6), (3, 13), (15, 25), (16, 25), (26, 26), (31, 25),
                   (32, 26), (35, 22), (36, 23), (44, 16), (46, 4)]:
        g.ent("gem", x, y)

    # ----------------------------------------------------- the declared route
    # ADR 005.  This is the INTENDED solution, not the shortest path: the
    # colonnade under the fork also works (REPORT.md records the run), and the
    # route names the aqueduct because riding a current is the thing World 2
    # has to teach.
    #
    # Every hop is short on purpose.  Three of them are dry -- pad_fish >
    # tide_in, pocket_two > bank_one and portage_west > pad_human -- and the
    # air meter carries across a hop boundary, so splitting one buys the search
    # nothing it has not paid for.
    k.mark("cell_two", 7, 13, form="human")
    _wet_mark(k, "tide_in", 12, 20)          # in the lane, just off the shelf
    _wet_mark(k, "pocket_two", 20, 20)       # past the lane's end, calm water
    k.mark("bank_one", BANK1_X + BANK1_W - 1, COURSE_STAND, form="fish")
    _wet_mark(k, "chute_in", FORK_X + 1, CHUTE_Y)
    _wet_mark(k, "chute_out", FORK_X + FORK_W + 1, CHUTE_Y)
    k.mark("portage_west", PORTAGE_X, COURSE_STAND, form="fish")
    # The way out is three hops, not one, and that is ADR 005's rule rather
    # than caution.  MEASURED: asking the prover to get from pad_human to the
    # exit in a single hop spent the whole 50,000-expansion budget and stopped
    # 64.0 px short at tile (43, 9) -- the exit is up and WEST, the kelp is
    # east, and the manhattan frontier walked straight at the goal into solid
    # masonry.  Split at the kelp's foot and its head, every hop's heuristic
    # points the way the body has to go.
    k.mark("kelp_foot", KELP_X, COURSE_STAND, form="human")
    k.mark("kelp_top", KELP_X - 1, 4, form="human")
    # The colonnade, named so it can be proved with tools/prove.sh --route
    # without editing the level.  Not on the declared route -- but there is one
    # mark per pass and not one at each end, and that is not tidiness.  The
    # standing column has to be crossed OVER, and rising makes the distance to a
    # goal four rows lower worse before it makes it better -- ADR 005's
    # addendum, in one shape.  MEASURED on this grid: slow_west > slow_east as a
    # single hop proves, but costs 559 expansions; split at each pass it costs
    # 12 + 14 + 7 = 33.  An earlier draft with 5-tile columns and two tiles of
    # clearance did NOT finish the single hop inside the 50,000 budget at all,
    # which is why the columns here are three tiles tall with four tiles of
    # water past them.
    _wet_mark(k, "slow_west", 27, 25)     # pool three, at depth
    _wet_mark(k, "slow_under", 31, 26)    # under the hanging column
    _wet_mark(k, "slow_over", 35, 22)     # over the standing one
    _wet_mark(k, "slow_east", 37, 25)     # pool four, at depth

    g.route("spawn", "cell_two", form="human")           # east, and down
    g.route("cell_two", "pad_fish", form="human")        # the shaft
    g.route("pad_fish", "tide_in", form="fish")          # flop off the shelf
    g.route("tide_in", "pocket_two", form="fish")        # ride the 68 lane
    g.route("pocket_two", "bank_one", form="fish")       # surface, hop 16 px
    g.route("bank_one", "chute_in", form="fish")         # down to the aqueduct
    g.route("chute_in", "chute_out", form="fish")        # the 120 valve
    g.route("chute_out", "portage_west", form="fish")    # surface, hop 16 px
    g.route("portage_west", "pad_human", form="fish")    # the air pinch
    g.route("pad_human", "kelp_foot", form="human")      # two tiles of terrace
    g.route("kelp_foot", "kelp_top", form="human")       # twelve rows of kelp
    g.route("kelp_top", "exit", form="human")            # west to the totem
    return g, k


def main():
    g, k = ruins_3()
    for line in k.audit():
        print(line)
    write("ruins_3", g, "TIDE GALLERY", music="world2")


if __name__ == "__main__":
    main()
