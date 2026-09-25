#!/usr/bin/env python3
"""ruins_2 -- THE COLONNADE.  World 2 of docs/plan-20-levels.md, level 2.

Self-contained: running this file under the project python writes
`levels/ruins_2.json`.  It is also importable, so the merge can wire
`build()` into tools/build_levels.py without moving a line of geometry.

    "$PYVENV" tools/worlds/ruins_2.py
    tools/prove.sh ruins_2

WHAT THE LEVEL IS
-----------------
ruins_1 teaches what a current does.  This one makes you work with one.

A drowned hall runs west to east under a collapsed roof.  Four submerged
columns alternate: the first two rise from the bed so you pass OVER them at
the surface, the other two hang from the roof so you pass UNDER them along the
bed.  That forces a serpentine, and the four gaps between the columns are
where the water moves:

    gap 1 (cols 19-22)   >    east, 68 px/s    ride it east while you sink
    gap 2 (cols 25-28)   u    up,   62 px/s    it lifts you back to the roof
    gap 3 (cols 31-34)   >    east, 68 px/s    ride it east while you sink
    gap 4 (cols 37-40)   u    up,   62 px/s    it lifts you to the key

Eastbound every gap pushes the way the weave already wants to go, so the hall
reads as one long slide.  Westbound every one of them is against you.  The
fish swims 92 px/s (data/forms/fish.json), so:

    with a 68 px/s horizontal current    160 px/s   2.4 gap-widths a second
    against it                            24 px/s   one gap in 2.7 seconds
    with a 62 px/s up current            154 px/s
    against it                            30 px/s

Nothing here is a wall.  Everything here is slow.  That is the whole design:
the trip out is the obvious read and the trip home is the level.

THE ORDER OF PLAY, AND WHY IT IS NOT CIRCULAR
---------------------------------------------
    spawn -> font            gallery, dry, human ('font' is the pad's tile)
    font -> key_cyan         east down the hall, with every current
    key_cyan -> door_cyan    west up the hall, against every current
    door_cyan -> pad_human   the exit chamber behind the door
    pad_human -> exit

`key_cyan` is taken strictly before `door_cyan` is touched, and nothing on the
outward leg shuts behind Kaya: the currents are 68 and 62 px/s against a
92 px/s swimmer, so every gap is two-way.  The FAST current tiles (`}` and `{`,
120 px/s) are deliberately NOT used anywhere in this level -- 120 > 92 means a
fast gap is a one-way valve, and every gap here is on the only path through
the hall, so one of them would seal the return.  That is jungle_2's old
circular dependency (a switch that sealed the route to its own key) with water
instead of switch blocks, and it is the shape this module refuses to draw.

Everything behind `door_cyan` -- `pad_human` and `exit` -- is reachable ONLY
through the door, which is a submerged gate at col 9, rows 20-21.  That
placement is load-bearing rather than decorative: if `pad_human` could be
reached before the key, a player could turn human in a chamber with a shut
door and no `pad_fish`, and a human cannot climb out of deep water in this
game (form_human.gd strokes at jump_vel * 0.45 = -117 px/s against
water_gravity 228, about nine pixels).  Behind the door, that state is
unreachable.

THE AIR POCKET THAT MATTERS
---------------------------
Measured, not assumed: form_fish.gd resets `air_left` to `air_seconds` on
every tick the fish is wet, and only counts down when it is not.  The air
budget in this engine is therefore time spent OUT of the water, not under it.
So an air pocket "matters" exactly where the route leaves the water.

The key sits on a dry slab at cols 41-44, one tile above the waterline, inside
the pocket the gap-4 up-current lifts you into.  Reaching `key_cyan` at (42,19)
costs about 0.8 s of the fish's 2.6 s -- prove.sh spends 32 frames out of the
water on that hop -- and the two gems further along the slab at cols 43-44 cost
more, an air-budget bet the level offers and never demands.  The other pockets
(cols 6-8, 11-12, 19-22, 25-28, 37-40) are the collapsed roof's light wells,
kept inside `AIR_POCKET_SPAN` so the kit checks their spacing, and the two over
the up-channels are what those channels vent into.

THE HUMAN IN THE WATER, AND THE TWO WAYS BACK
---------------------------------------------
A human walks in water at max_run 108 * water_move_scale 0.62 = 67.0 px/s.  The
east currents push at 68.  So a human in the hall cannot swim home, and
`pad_fish` is a trigger rather than a wall -- its box is the lower 8 px of its
tile, and a player who jumps while running east clears it and lands in the
shaft.  Two exits answer that, and both were driven in the running game rather
than argued:

  the kelp, col 11    Everything a human can fall into from the gallery is the
                      shaft pool, cols 10-12.  Dropped at (11,24) as a human,
                      sixteen strokes reach the kelp at row 19 and she climbs
                      out onto the gallery floor at (10,7).
  pad_fish, col 43    On the key slab, and there for no other reason.  Every
                      current in the hall pushes east or up, every column pass
                      is enterable from the bed (a submerged jump is
                      -260 * 0.78 against water_gravity 228, about five tiles),
                      and gap 4 lifts you to the waterline beside the slab.  So
                      a human carried into the hall ends up exactly there, and
                      the pad turns her back into something that can swim home.

A one-tile sill only a 14x9 fish fits under was built first and thrown away.
It closed the state outright and it PROVED -- but tools/reachability.py models
every form as two tiles tall, so it called `key_cyan` unreachable and
tools/validate.sh went red.  Making a shape the pre-filter cannot see is not
worth a level whose gate is amber, and loosening the filter to fit the level is
the move ADR 005 exists to forbid.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))          # tools/ on the path

from gen_levels import Grid, write                                    # noqa: E402
from world_kit import Kit, Palette, RUINS                             # noqa: E402

LEVEL_ID = "ruins_2"
LEVEL_NAME = "THE COLONNADE"


# --------------------------------------------------------------- the palette
#
# world_kit resolves a palette's tile NAME to a character against the *jungle*
# legend (`_Tiles.char_of_id` reads data/level_legend.json's derived `legend`
# key), and no ruins tile has a jungle character.  So RUINS falls through to
# UNDERSTUDY, which hands `solid` the character 's' -- and in a ruins grid 's'
# is ruin_grate, not ruin_stone.  The gameplay flags match, so audit() and
# prove.sh are unaffected, but the level would be drawn entirely in grating.
#
# ADR 002's amendment is what actually fixes this: every tileset binds the same
# twelve ROLE characters, so '#' is the ruins' ground cap and '|' its kelp
# whatever the palette calls them.  The right stand-in for "the ruins' ground
# cap" is therefore the jungle tile that owns '#', and for "background wall"
# the one that owns 'L'.  Two entries; everything else in RUINS already lands
# on the correct role character.
RUINS_CHARS = Palette("sunken_ruins", dict(
    RUINS.roles,
    solid="grass_top",      # -> '#' -> ruin_stone (220) in a ruins grid
    bg="bg_leaves",         # -> 'L' -> ruin_wall  (222)
))


# ----------------------------------------------------------------- the level
#
# Rows, once and for all:
#
#    0- 1  shell
#    2- 7  the gallery: dry, human, spawn and pad_fish        (cols 2-12)
#    8     gallery floor                                      (cols 2-10)
#    9-16  rock, pierced by the entry shaft                   (cols 11-12)
#   17-19  air: the exit chamber, the shaft, the light wells
#   20-26  water: the exit pool, the drowned hall
#   27     the bed
#   28-29  rock
#
# Two rows lower than they first were, and the reason is the HUD rather than
# the geometry: the hearts and the air meter are painted over the top ~2 tiles
# of the viewport, and the exit chamber sat right under them.  A screen-locked
# camera cannot scroll that away, so the fix is to put the air band in rows
# 17-19, which is the third row of screen (0,1) and clear of the bars.
#
# THE TWO SEAMS, which are why those rows are those rows.
#
# `CameraController` picks the screen from the player's CENTRE and freezes the
# sim for the length of every flip, so a route that runs ALONG a seam flips the
# camera every time the body wobbles across it.  prove.sh has no camera and the
# tape replay skips paused ticks, so neither can see it: it is a feel defect the
# ADR 005 gate is structurally blind to, and ruins_3 shipped one.
#
# On a 50x30 level the seams are y = 240 px (rows 14|15) and x = 400 px
# (cols 24|25).  So:
#
#  * The air band is rows 17-19 under a SOLID roof at row 16.  A 22 px human
#    standing on the bank has her centre at y 309 and, with her head stopped by
#    that roof at the top of a jump, never above y 283.  The horizontal seam is
#    unreachable from inside the chamber rather than merely unused by the route.
#  * The water is rows 20-26; the fish's centre never rises above y 276.
#  * The colonnade sits at 17, 23, 29 and 35, so the VERTICAL seam falls inside
#    the solid second column (cols 23-24).  Every current is at least a column
#    away from it, and the crossing itself is a straight 92 px/s run through
#    still water in both directions -- one flip each way, not a struggle on the
#    line.

WATER_TOP = 20          # the row that carries the surface tile
WATER_BED = 26          # the last row of water; the bed caps at 27
AIR_FOOT = 19           # the bottom row of the air band above the water
AIR_H = 3               # rows 17-19 ...
AIR_ROOF = AIR_FOOT - AIR_H             # ... under a solid roof at row 16
GALLERY_FLOOR = 8       # the dry room's floor cap; you stand on row 7

COL_X = (17, 23, 29, 35)
GAPS = ((19, 4), (25, 4), (31, 4), (37, 4))     # (first col, width)
SLAB = (41, 4)                                  # the dry landing that holds the key
HALL = (10, 31)                                 # open water, cols 10-40


def build():
    """Draw the level.  Returns (Grid, Kit) the way build_levels.build() wants."""
    g = Grid(50, 30, tileset="ruins")
    k = Kit(g, RUINS_CHARS, form="fish")

    k.fill_bg()
    # Carved, not built: solid silt everywhere, then cut the rooms out of it.
    # It keeps the prover's reachable state space small, which is the one thing
    # ADR 005's addendum says a level can do to help the search.
    k.fill_solid("packed")

    _gallery(k)
    _exit_chamber(k)
    _hall(k)
    _colonnade(k)
    _currents(k)
    _light_wells(k)
    _key_slab(k)
    _dressing(k)
    _inhabitants(g)
    _route(g)

    return g, k


# ------------------------------------------------------------- the west end

def _gallery(k):
    """Dry ground, a human, and one way down: the shaft at cols 11-12.

    `pad_fish` sits on the last floor tile before the hole, so walking east off
    the gallery cannot put a human in the water.  A human who jumps the pad and
    lands in the hall anyway is not stranded either -- the kelp in the shaft is
    the way back up, and it is the only reason the shaft has one.  She cannot
    climb out of deep water on her own: form_human.gd strokes at
    jump_vel * 0.45 = -117 px/s against water_gravity 228, which is nine pixels.
    """
    k.clear_rect(2, 2, 11, GALLERY_FLOOR - 2)         # cols 2-12, rows 2-7
    k.rect(2, GALLERY_FLOOR, 9, 1, "solid")           # the floor, cols 2-10
    k.clear_rect(11, GALLERY_FLOOR, 2, AIR_FOOT - GALLERY_FLOOR + 1)
    # The route cannot name `pad_fish`: there are two of them (the recovery pad
    # on the key slab is the other) and gen_levels rejects a waypoint that names
    # several places. So the gallery pad's own tile gets a name. Standing on it
    # is standing in the pad's trigger box -- ProverSim.step() runs the trigger
    # pass after the motion pass, so the hop that arrives here arrives as a fish.
    k.mark("font", 10, GALLERY_FLOOR - 1, form="human")


def _exit_chamber(k):
    """Behind the door: a bank, the pad back to human, and the way out.

    The pool shelves one tile per column (bed caps at 21, 22, 23 going east), so
    the fish rides in at the surface and steps onto the bank without needing a
    hop, and a human who falls back in can walk up the same steps.
    """
    k.clear_rect(2, AIR_ROOF + 1, 7, AIR_H)   # cols 2-8, the air band
    k.floor(2, WATER_TOP, 4, depth=1)         # the bank, cols 2-5, stand row 17
    for i, col in enumerate((6, 7, 8)):       # the shelving bed
        k.rect(col, WATER_TOP + 1 + i, 1, 1, "solid")
        k.rect(col, WATER_TOP, 1, 1, "water_top")
        if i:
            k.rect(col, WATER_TOP + 1, 1, i, "water")
    k.air_pocket(6, AIR_FOOT, 3, h=AIR_H)     # the pocket over the exit pool

    # The gate.  Two tiles, because Door.HEIGHT_TILES is 2 and a 22 px body
    # needs both of them (defect 3).  Level.spawn_entity writes tile 25 across
    # it until the cyan key opens it, and back to empty when it does.
    k.doorway(9, WATER_TOP + 1, h=2)


# ------------------------------------------------------------- the drowned hall

def _hall(k):
    """Open water from the foot of the shaft to the foot of the key slab."""
    x, w = HALL
    k.rect(x, WATER_TOP, w, WATER_BED - WATER_TOP + 1, "water")
    k.rect(x, WATER_BED + 1, w, 1, "solid")                 # the bed
    # Two bed waypoints under the hall's west end.  They cost nothing to place
    # and they cut the whole proof from 1,141 expansions to 474, because the
    # long west hop stops asking the manhattan frontier to find the door from
    # eight tiles away with a colonnade in between.
    k.mark("sill", 14, WATER_BED)
    k.mark("pool", 12, WATER_BED)
    # The shaft's two columns break the roof, so their top row is a surface.
    k.rect(11, WATER_TOP, 2, 1, "water_top")
    k.air_pocket(11, AIR_FOOT, 2, h=AIR_H)
    # air_pocket roofs the pocket at AIR_ROOF; the shaft has to go through it.
    k.clear_rect(11, GALLERY_FLOOR, 2, AIR_ROOF - GALLERY_FLOOR + 1)
    # The kelp, gallery floor to waterline.  Drawn last so nothing can overwrite
    # its top, which is how THE WATERWAY nearly shipped a vine with a gap in it.
    k.climb(11, 7, AIR_FOOT, landing="left", stand_form="human")


def _colonnade(k):
    """Four columns, alternating over/under, and the serpentine they force."""
    names = k.colonnade(
        COL_X[0], len(COL_X), COL_X[1] - COL_X[0],
        surface=WATER_TOP, bed=WATER_BED,
        pattern=["over", "under", "over", "under"],
        width=2, mark="col", clearance=2)
    assert names == ["col_1", "col_2", "col_3", "col_4"], names


def _currents(k):
    """The water, moving.  Every one of these is beatable, and says so.

    `current_channel` claims the tile downstream of each channel is clear, which
    is the softlock the shape invites: a current with a wall at the end of it
    pins you against it forever.  The two up-channels vent into light wells and
    the two east-channels vent into the pass under the next column.
    """
    deep = WATER_BED - WATER_TOP + 1          # 7 rows of water
    for i, (x, w) in enumerate(GAPS):
        if i % 2 == 0:
            k.current_channel(x, WATER_BED, w, "right", height=deep, wall=False)
        else:
            k.current_channel(x, WATER_TOP, deep, "up", height=w, wall=False)


def _light_wells(k):
    """Where the roof has fallen in.  Air, and the vent the up-channels need.

    Spaced inside AIR_POCKET_SPAN so the kit checks them; the fish does not
    actually need to breathe underwater in this engine (see the module
    docstring), so these earn their place as the vents and as the only daylight
    in the hall.
    """
    for x, w in (GAPS[0], GAPS[1], GAPS[3]):
        k.air_pocket(x, AIR_FOOT, w, h=AIR_H)


def _key_slab(k):
    """The dry landing at the east end, and the air bet it offers."""
    x, w = SLAB
    k.clear_rect(x, AIR_FOOT - AIR_H + 1, w, AIR_H)
    k.floor(x, WATER_TOP, w)                  # stand row 17
    k.mark("slab", x, AIR_FOOT, form="fish")


def _dressing(k):
    """Background only.  Nothing here has a flag."""
    for x in (4, 14, 21, 33, 45):
        k.g.vline(x, 2, 26, k.ch("decor"), "bg")
    k.rect(2, WATER_BED + 2, 46, 2, "void", "bg")


# ------------------------------------------------------------------ contents

def _inhabitants(g):
    g.ent("player_spawn", 4, GALLERY_FLOOR - 1)
    g.ent("pad_fish", 10, GALLERY_FLOOR - 1)
    g.ent("door_cyan", 9, WATER_TOP + 1)
    g.ent("key_cyan", 42, AIR_FOOT)
    g.ent("pad_human", 4, AIR_FOOT)
    # Not on the route: the recovery pad for a human who fell into the hall.
    # See "THE HUMAN IN THE WATER" above -- it is the east half's counterpart
    # to the kelp, and the fish that arrives here for the key is already a fish,
    # so it changes nothing about the intended play.
    g.ent("pad_fish", 43, AIR_FOOT)
    g.ent("exit", 2, AIR_FOOT)

    # Swimmers in the open gaps, off the pass rows: the prover does not simulate
    # enemies (ADR 005 says so plainly), so the tape walks through these and the
    # replay runs invulnerable.  Nothing here is on the line the route swims.
    g.ent("enemy_swimmer", 21, 24)
    g.ent("enemy_swimmer", 33, 24)
    g.ent("heart", 27, 18)

    # Every pickup needs two tiles of headroom (tests/test_level_validity.gd):
    # a gem in an over-pass goes on row 21, not on row 20 under the roof.
    for (x, y) in [(18, 21), (22, 25), (26, 18), (30, 21), (34, 25), (38, 18),
                   (43, 19), (44, 19), (6, 7), (8, 7), (7, 18)]:
        g.ent("gem", x, y)


def _route(g):
    """The intended solution (ADR 005).

    Hop by hop rather than in three long legs, because a hop that needs a big
    budget is a hop that is too coarse -- and because the two legs through the
    hall are the same water travelled twice in opposite directions, and the
    whole point of the level is that the second one is harder.  Splitting them
    at the columns is what makes each half of that statement checkable: compare
    the frame counts prove.sh prints for hops 3-5 against hops 9-11.
    """
    g.route("spawn", "font", form="human")          # six tiles of dry gallery

    # East, with everything.
    g.route("font", "pool", form="fish")            # off the ledge, down the shaft
    g.route("pool", "sill", form="fish")            # east along the bed
    g.route("sill", "col_1", form="fish")           # up and over col 17-18
    g.route("col_1", "col_2", form="fish")          # gap 1 east, sink to the bed
    g.route("col_2", "col_3", form="fish")          # gap 2 up, back to the roof
    g.route("col_3", "col_4", form="fish")          # gap 3 east, sink again
    g.route("col_4", "slab", form="fish")           # gap 4 up, onto the dry slab
    g.route("slab", "key_cyan", form="fish")        # one tile of air, and back

    # West, against everything.  Same waypoints, read backwards.
    g.route("key_cyan", "col_4", form="fish")
    g.route("col_4", "col_3", form="fish")          # gap 3 westward: 24 px/s
    g.route("col_3", "col_2", form="fish")          # gap 2 downward: 30 px/s
    g.route("col_2", "col_1", form="fish")          # gap 1 westward: 24 px/s
    g.route("col_1", "sill", form="fish")           # down out of the colonnade
    g.route("sill", "pool", form="fish")            # west along the bed
    g.route("pool", "door_cyan", form="fish")       # up to the gate, with the key

    g.route("door_cyan", "pad_human", form="fish")  # up the shelving bank
    g.route("pad_human", "exit", form="human")


def main():
    g, k = build()
    for line in k.audit():
        print(line)
    write(LEVEL_ID, g, LEVEL_NAME, music="world2")


if __name__ == "__main__":
    main()
