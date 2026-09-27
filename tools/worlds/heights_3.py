#!/usr/bin/env python3
"""heights_3 -- ASH COLUMN.  World 3, THERMAL HEIGHTS.

Self-contained: running this file under the project python writes
levels/heights_3.json and nothing else.  It also exports `heights_3()`
returning `(Grid, Kit)`, which is the tuple tools/build_levels.py's `build()`
expects -- that writer audits the kit before it writes anything.

    source tools/env.sh && "$PYVENV" tools/worlds/heights_3.py
    tools/prove.sh heights_3

THE SHAPE OF THE LEVEL
----------------------
One chimney, climbed bottom to top, in four segments that each ask for a
different verb.  50x30 like every level in this project -- docs/plan-20-levels.md
fixes that, because the side margins carry the touch controls -- but read
vertically: the route gains 24 rows and only ever moves sideways to find the
next lane of moving air.

  1  THE ASH FLOOR (rows 22-27, cols 1-40).  Kaya on foot, west to east, with a
     `gust_right` breathing along the floor and a HOLLOW TICK on the ceiling.
     It ends at `pad_bird` on the last tile of still air west of the column.

  2  THE COLUMN (cols 35-40, rows 14-27).  Four tiles of `updraft` -- 400 px/s
     of lift -- with a one-tile `downdraft` sheath down each shoulder of the
     throat.  The bird rides the core to its lip and steps off west into the cap
     chamber.  Drift out of the core on the way up and the sheath puts you back
     on the ash floor, which is the whole cost of getting it wrong in here.

  3  THE FLUE (cols 27-32, rows 4-13).  The column narrows to a six-tile crack
     with rock shelves alternating up its two walls and BANDS of downdraft
     between them.  The bird cannot climb it and the frog can, and the reason is
     one number each -- see WHY THE FLUE IS FROG-ONLY.  The shelves are two
     tiles wide and the flue's wall rises straight off the outer edge of each
     one, so an overshoot meets rock and clings to it instead of sailing into a
     pit.

  4  THE CROWN (cols 2-24, rows 1-13).  Bird again, west across the seam: a
     `gust_right` headwind sealing the high line, a `gust_left` tailwind in the
     low one, and a second updraft standing on the crown's own floor to lift you
     onto the totem's perch.

NOTHING IN HERE KILLS YOU FOR MISSING A JUMP.  Every fall lands on a floor: the
flue drops you onto its own foot ledge, the crown drops you onto the crown's
floor, and the crown's floor drains down a drafted well (cols 18-20) to the ash
floor, where `pad_bird` and the column are waiting.  The cost is the climb.  The
only `heights_vent` tiles in the level are on a CEILING (see THE VENTS), because
a hazard under a fall line would turn a missed jump into a death.

WHY THE FLUE IS FROG-ONLY, IN FOUR NUMBERS
------------------------------------------
This is the level's spine, and it is arithmetic on data/forms/*.json plus one
fact about how src/player/forms/form_base.gd applies a current:

    do_jump():       p.vel.y = jump_vel * scale + current.y
    apply_gravity(): cap = max_fall + current.y;  vel.y moves toward cap at g

So a current shifts the velocity a jump STARTS with, and the speed a fall ENDS
at, and it does not touch the deceleration of a rise: a body already moving up
at -v slows at exactly `gravity`, draught or no draught.  Two consequences, and
the flue is built out of both:

  * a jump or a flap STARTED inside a downdraft is crippled.  170 px/s onto a
    -172 flap is -2 px/s: the bird does not move.  Onto the frog's -305 wall
    kick it is -135, thirteen pixels of rise.
  * a jump started in STILL air carries its whole arc THROUGH a draught.  The
    frog leaves a shelf at -340 and rises 340^2/(2*700) = 82.6 px whatever the
    air above it is doing.

The shelves are three rows apart, so each hop needs 48 px of rise measured from
one shelf's surface to the next, and every row between them is drafted:

    frog, standing jump ....... 82.6 px   34 px of margin.  Climbs.
    human, standing jump ...... 44.5 px   3.5 px short.  Cannot.
    bird, one flap ............ 172^2/(2*420) = 35.2 px.  Cannot.
    bird, two flaps ........... the second one starts inside a band: -2 px/s.

The bird's stamina never even comes into it -- flap_cost 12 against
max_stamina 100 buys eight flaps, and it is the FIRST one that falls thirteen
pixels short.  The frog's hitbox is 11 px tall (data/forms/frog.json), which is
less than a 16 px tile, so a frog standing on a shelf is entirely inside that
shelf's row: `FormBase.current_at` is area-weighted over the hitbox, and the
still row the shelves sit in is the only air its jump ever samples.  That is why
the bands skip the shelf rows and nothing else.

The same arithmetic is what makes the bands the level's locks rather than its
decoration.  The well under the crown (cols 18-20) and the sheath down the
throat's shoulders are the same trick: air you can fall through and cannot climb.
Without them a bird could flap eight rows up out of the ash floor and skip the
column, the flue and the frog with it.

THE CLING, AND WHAT IT IS FOR
-----------------------------
data/forms/frog.json: wall_stick_time 0.55, wall_slide_speed 34,
wall_jump_vel -305, wall_jump_push 120.  A kick is worth 66 px of rise and it
always leaves the wall.

The flue is deliberately not a pure wall-climb.  A chain of kicks up a shaft is
a shape tools/prove.sh can find and a person cannot repeat -- ADR 005 says
plainly that a provable route is not the same as a fair one, and world_kit's own
note on the frog's 4-tile step is this project's standing example.  So the flue
is a shelf climb with a wall one tile off both shoulders, and what the cling buys
is the MISS: a full-height jump at full run carries 3.1 tiles, so overshooting a
2-tile shelf is the normal failure, and an overshoot meets the far wall and
sticks to it instead of dropping the length of the flue.

MEASURED from the capture, because the slide is not the number on the tin:
form_frog.gd clamps the slide to `wall_slide_speed + current.y`, so inside a
band it is 34 + 170 = 204 px/s and only in a still row is it 34.  The fall it
replaces is 340 + 170 = 510, so the cling still more than halves it, and the
frog re-sticks for another 0.55 s every time the timer runs out while it is
still pressing into the rock -- shots/heights_3_f_frog_cling.png is it holding
the east wall at 204 px/s with two bands either side of it.

WHERE THE WALKED FLOORS SIT, AND WHICH SEAMS THE ROUTE CROSSES
--------------------------------------------------------------
`CameraController` picks its screen from the body's CENTRE and freezes the
simulation for SLIDE_TIME while it flips, so two things here are rules rather
than taste.

Every stand row is at least one row above a multiple-of-15 boundary.  A body
22 px tall standing on a floor capped at row 15 has its feet at y=240 and its
centre at y=229, which puts it on the UPPER screen -- and that screen ends at
y=240 and never draws the floor it is standing on.  ruins_4 shipped a gallery
like that once.  So the caps in here are rows 4, 5, 8, 11, 14 and 28, and the
stand rows are 3, 4, 7, 10, 13 and 27.  Row 14 is a cap and never a stand row.

The route crosses a seam four times and every crossing is flown, or walked on
flat rock:

    hop 2   ash_mid -> core_foot    the vertical seam at x=400, walking, on a
                                    floor with no gap and no hazard in it
    hop 4   core_ride -> core_lip   the horizontal seam at y=240, flying, in the
                                    middle of the updraft core
    hop 10  wind_perch -> wind_door  the vertical seam again, flying
    (off route) the well            a fall, which a 0.12 s pause cannot spoil

No on-foot hop crosses a seam mid-jump.  The frog's three hops live inside rows
4-13 -- one screen -- by construction: that is why segment 3 is in the top band
instead of straddling the middle of the level, and it is the reason the flue is
nine rows and not fifteen.

WHAT IS DRAWN WITH A KIT HELPER AND WHAT IS NOT
----------------------------------------------
`Kit.updraft_shaft` draws the column, so the column inherits both historical
shaft defects: it cannot be capped across its full width (defect 6) and its left
wall stops two tiles above the floor so you can walk in rather than being sealed
out (defect 5).

`Kit.wind_gap` is NOT used, and that is a decision rather than an omission: it
claims a standable lip on each side of the moving air, which is true of a gust
blown across a chasm and false of every gust in here.  The crown's two lanes are
lanes in open sky -- there is nothing to stand on at either end of them, the
bird crosses them in flight, and the claim `wind_gap` would file is a claim this
level cannot keep.  They are drawn with `rect` and answered by tools/prove.sh,
which is the tier that can actually see a gust.

THE VENTS
---------
`heights_vent` is this world's hazard and the prover prunes every state that
touches one, so a vent near the route costs search budget and buys nothing.  The
two in here hang from the ROOF of the ash floor either side of the tick, where
the only way to touch one is to fly up into the ceiling -- which the bird can do
and has no reason to.  Nothing falls onto a hazard anywhere in this level.

THE PALETTE
-----------
`world_kit.Palette.char()` resolves a tile NAME through the flat, jungle-derived
`legend` key of data/level_legend.json, so HEIGHTS's own names (heights_rock,
heights_chain, ...) have no character there and fall through to UNDERSTUDY --
which lands `solid` on 's' (heights_basalt, the *second* solid) and `bg` on 'r'
(heights_cloud, a background accent).  ADR 002's amendment says a character
means whatever the level's world says it means, so this palette is declared in
terms of the jungle tile whose character IS the heights role character:
`grass_top` for '#', `bg_leaves` for 'L', and so on down the list.
`Palette.missing()` is then empty, `audit(strict_verbs=True)` is clean, the level
serialises `"tileset": "heights"`, and the game paints ids 240-251.

The draughts and the gusts are `shared` characters ('U', 'V', ')', '(') and are
the real tiles either way, so this level loses no verb to an understudy -- which
matters more here than anywhere else, because without the draughts this is not a
level, it is a chimney with nothing in it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                          # noqa: E402
from world_kit import Kit, Palette, check_gap, check_rise   # noqa: E402

LEVEL_ID = "heights_3"
LEVEL_NAME = "ASH COLUMN"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the heights role
## character.  See THE PALETTE: this is a character map, not an art claim, and
## the art comes from `"tileset": "heights"` at load time.  The verb roles need
## no such trick -- their characters are `shared` across every world.
HEIGHTS_W3 = Palette("thermal_heights", {
    "bg": "bg_leaves",            # 'L' -> heights_wall
    "solid": "grass_top",         # '#' -> heights_rock
    "solid_alt": "stone_mossy",   # 'S' -> heights_rock_sun
    "packed": "dirt",             # 'd' -> heights_scree
    "block": "stone",             # 's' -> heights_basalt
    "oneway": "wood_platform",    # '=' -> heights_plank
    "ladder": "vine",             # '|' -> heights_chain
    "hazard": "spikes",           # '^' -> heights_vent
    "decor": "tree_trunk",        # 'T' -> heights_stack
    "void": "bg_dark",            # 'X' -> heights_air
    "breakable": "crate",         # 'c' -> heights_shell
    "updraft": "updraft",                 # 'U'  shared, [0, -400]
    "updraft_strong": "updraft_strong",   # '*'  shared, [0, -560]
    "downdraft": "downdraft",             # 'V'  shared, [0, +170]
    "gust_right": "gust_right",           # ')'  shared, [+80, 0]
    "gust_left": "gust_left",             # '('  shared, [-80, 0]
})

## 'r' is the heights tileset's background accent (heights_cloud) and the kit
## has no role for it: ROLES names twelve role characters and 'r' is not one of
## them.  It goes straight onto the bg layer, where it cannot collide with
## anything; gen_levels' `_check_characters` still proves it means something in
## this world.
CLOUD = "r"

# ------------------------------------------------------------------ geometry
#
# Every number below is measured off one of four things: the ash floor, the
# column's lip, the flue's three-row shelf pitch, or a screen boundary.  Nothing
# is a magic number twice.

VSEAM = 25              # first column of the eastern screens (x = 400)
HSEAM = 15              # first row of the southern screens (y = 240)

# --- 1. the ash floor
HALL_X0, HALL_X1 = 1, 40
HALL_TOP = 22           # its first air row; row 21 is the roof
HALL_STAND = 27
HALL_CAP = 28           # the floor itself; row 29 is scree under it
GUST_X0, GUST_X1 = 8, 13    # the exhalation along the floor

# --- 2. the column
THROAT_X0, THROAT_X1 = 35, 40   # the shaft's interior columns
CORE_X0, CORE_X1 = 36, 39       # the updraft core inside it
CORE_LIP = 14                   # the core's top row; the hover settles in it
CHAMBER_X0, CHAMBER_X1 = 34, 41
CHAMBER_TOP = 10                # the cap chamber, rows 10-13, roofed at row 9

# --- 3. the flue
FLUE_X0, FLUE_X1 = 27, 32       # its interior
WEST_X = 27                     # the west shelf's first column (2 wide)
EAST_X = 31                     # and the east shelf's
LEDGE_X0, LEDGE_X1 = 27, 33     # the flue's foot, and what catches every fall
LEDGE_CAP = 14
LEDGE_STAND = 13
PITCH = 3                       # rows between shelves: 48 px.  The whole level.
E1_CAP = LEDGE_CAP - PITCH      # 11  -> stand 10, east wall
W2_CAP = E1_CAP - PITCH         # 8   -> stand  7, west wall
GAL_CAP = W2_CAP - PITCH        # 5   -> stand  4, the head gallery
## The rows the sinking air fills: every row of the flue EXCEPT the rows a frog
## stands in to jump -- 13 (the foot ledge), 10, 7 and 4.  See WHY THE FLUE IS
## FROG-ONLY.
BAND_ROWS = (12, 11, 9, 8, 6, 5)

# --- the head of the flue
GAL_X0, GAL_X1 = 26, 32         # its air; the floor is cols 29-32
GAL_FLOOR_X0 = 29
GAL_STAND = GAL_CAP - 1         # 4
CROSS_X = VSEAM                 # the one-column, two-row doorway west

# --- 4. the crown
CROWN_X0, CROWN_X1 = 2, 24
CROWN_CAP = 14
CROWN_STAND = 13
WELL_X0, WELL_X1 = 18, 20       # the drafted drain back down to the ash floor
HEAD_X0, HEAD_X1 = 16, 21       # the headwind
HEAD_Y0, HEAD_Y1 = 1, 5
TAIL_X0, TAIL_X1 = 10, 15       # the tailwind
TAIL_Y0, TAIL_Y1 = 7, 10
LIFT_X0, LIFT_X1 = 7, 9         # the second updraft
LIFT_TOP = 4
PERCH_X0, PERCH_X1 = 2, 6
PERCH_CAP = 4
PERCH_STAND = PERCH_CAP - 1     # 3


def _air_mark(k, name, x, y, form="bird"):
    """A waypoint in mid-air.

    Not `Kit.mark`: that files a "stand" claim, and nothing inside an updraft is
    standable.  `ProverSearch._reached` accepts arrival with no floor under the
    body when the form is the bird -- it is the one form that can be somewhere
    and stay there without one -- so a bird waypoint inside moving air is
    legitimate, and what it has to promise is that the tile is still OPEN after
    everything else has been drawn over it.  Same hand-off as ruins_3's
    `_wet_mark`, for the same reason: the claim has to match the verb.
    """
    k.g.mark(name, x, y)
    k._claim("clear", "air waypoint '%s' (%s)" % (name, form), x=x, y=y, tall=2)
    return name


def _shelf(k, x, cap, mark_x, name, w=2):
    """One rock shelf in the flue, and a mark on the tile the next hop leaves
    from.

    Drawn AFTER the downdraft bands, so its cap is rock where the band was:
    `audit()` cannot see draw order, and this is the order that matters.
    """
    k.ledge(x, cap, w, role="solid", stand_form="frog")
    k.mark(name, mark_x, cap - 1, form="frog")
    return x, cap - 1, w


def heights_3():
    """ASH COLUMN -- one chimney, four segments, bottom to top."""
    g = Grid(W, H, tileset="heights")
    k = Kit(g, HEIGHTS_W3, form="human")

    # Carved, not built.  prove.gd's own note: a small reachable state space
    # makes a failed search exhaust its frontier instead of spending the whole
    # budget wandering open sky -- and a chimney is a hole in a mountain anyway.
    k.fill_bg("bg")
    k.fill_solid("solid")
    k.shell(1, "solid")

    # ==================================================== 1 -- THE ASH FLOOR
    hall_w = HALL_X1 - HALL_X0 + 1
    k.corridor(HALL_X0, HALL_STAND, hall_w, h=HALL_STAND - HALL_TOP + 1)
    k.floor(HALL_X0, HALL_CAP, hall_w)          # cap 28, scree 29, stand 27
    k._claim("stand", "the ash floor, at the spawn",
             x=HALL_X0 + 1, y=HALL_STAND, form="human")
    k._claim("stand", "the ash floor, at the column's foot",
             x=THROAT_X0, y=HALL_STAND, form="human")

    # The floor breathes east at 80 px/s.  Kaya runs 108, so downwind she makes
    # 188 and upwind 28: the lane is not a wall, it is a thumb on the scale, and
    # it points the way she is going.
    k.rect(GUST_X0, HALL_STAND - 1, GUST_X1 - GUST_X0 + 1, 2, "gust_right")

    # The only two hazards in the level, on the ROOF either side of the tick.
    # See THE VENTS.
    k.put(GUST_X0 - 2, HALL_TOP - 1, "hazard")
    k.put(GUST_X1 - 2, HALL_TOP - 1, "hazard")

    # ======================================================= 2 -- THE COLUMN
    # Carve the chamber and the throat BEFORE the shaft helper writes its walls:
    # a wall drawn first and carved over afterwards is the draw-order bug
    # audit() exists for, and jungle_3 shipped one.
    k.clear_rect(CHAMBER_X0, CHAMBER_TOP, CHAMBER_X1 - CHAMBER_X0 + 1,
                 CORE_LIP - CHAMBER_TOP)                  # rows 10-13
    k.clear_rect(THROAT_X0, CORE_LIP, THROAT_X1 - THROAT_X0 + 1,
                 HALL_TOP - CORE_LIP)                     # rows 14-21
    # Walls, a mouth in the roof (defect 6) and a way in at the foot (defect 5),
    # then 400 px/s of lift between them.
    k.updraft_shaft(THROAT_X0 - 1, THROAT_X1 - THROAT_X0 + 1,
                    CORE_LIP, HALL_TOP - 1, mouth=(CORE_X0, CORE_X1))
    # The sheath: one tile of sinking air down each shoulder of the throat, so
    # leaving the core mid-ride costs you the ride.  It is also what stops a bird
    # flapping up a shoulder instead of riding: a flap started in 170 px/s of
    # downdraft is -2 px/s.
    k.rect(THROAT_X0, HSEAM, 1, HALL_TOP - HSEAM, "downdraft")
    k.rect(THROAT_X1, HSEAM, 1, HALL_TOP - HSEAM, "downdraft")
    # The chamber's two shoulders of floor, where the ride ends.  Written over
    # the row of updraft the shaft helper filled, which is what leaves the core's
    # mouth exactly the four columns the shaft declared.
    k.put(THROAT_X0, CORE_LIP, "solid")
    k.put(THROAT_X1, CORE_LIP, "solid")
    k._claim("stand", "the cap chamber's west shoulder, where the ride ends",
             x=THROAT_X0, y=CORE_LIP - 1, form="bird")
    k._claim("stand", "the cap chamber's east shoulder",
             x=THROAT_X1, y=CORE_LIP - 1, form="bird")
    # The core's foot, carried down to the ash floor itself: the column starts
    # where Kaya is standing, and `pad_bird` is the last still tile west of it,
    # so she cannot walk into the lift as the wrong shape.
    k.rect(CORE_X0, HALL_TOP, CORE_X1 - CORE_X0 + 1,
           HALL_CAP - HALL_TOP, "updraft")

    # ========================================================= 3 -- THE FLUE
    k.clear_rect(FLUE_X0, 1, FLUE_X1 - FLUE_X0 + 1, LEDGE_STAND)    # rows 1-13
    # The two-row doorway east into the cap chamber.  Two rows because a body is
    # two tiles and a one-row slot is a passage on the grid and a wall in play;
    # it is also what keeps (33,13) out of tests/test_level_validity.gd's
    # one-tile-headroom pocket check.
    k.clear_rect(FLUE_X1 + 1, LEDGE_STAND - 1, 1, 2)
    k.floor(LEDGE_X0, LEDGE_CAP, LEDGE_X1 - LEDGE_X0 + 1, depth=1)
    for x in range(LEDGE_X0, LEDGE_X1 + 1):
        k._claim("clear", "the flue's foot ledge", x=x, y=LEDGE_STAND, tall=2)

    # The bands: every row of the flue except the rows a frog stands in.
    for y in BAND_ROWS:
        k.rect(FLUE_X0, y, FLUE_X1 - FLUE_X0 + 1, 1, "downdraft")

    # The shelves, three rows apart, alternating walls.  Two tiles wide on
    # purpose -- see THE CLING.
    _shelf(k, EAST_X, E1_CAP, EAST_X, "flue_1")
    _shelf(k, WEST_X, W2_CAP, WEST_X + 1, "flue_2")

    # The head gallery.  Its floor stops at col 29 and that is load-bearing:
    # cols 27-28 at row 5 have to stay open or the rise out of the west shelf is
    # a jump into the underside of this floor, which `path_clear` refuses and
    # which a player would meet as an invisible lid.
    k.clear_rect(GAL_X0, 1, GAL_X1 - GAL_X0 + 1, GAL_CAP - 1)   # rows 1-4
    k.floor(GAL_FLOOR_X0, GAL_CAP, GAL_X1 - GAL_FLOOR_X0 + 1, depth=1)
    k.clear_rect(CROSS_X, GAL_STAND - 1, 1, 2)
    k._claim("clear", "the doorway west out of the flue's head",
             x=CROSS_X, y=GAL_STAND, tall=2)
    k._claim("stand", "the head gallery's floor",
             x=GAL_FLOOR_X0 + 1, y=GAL_STAND, form="frog")

    # Each hop of the climb, checked against the frog's MEASURED limits before
    # anything is drawn over the arc.  Three up and three across is both limits
    # at once (LIMITS["frog"] is rise 3, gap 3), and the reason the pitch is not
    # four is jungle_4's shipped 4-tile rungs: a jump released early is cut to
    # 4.37 tiles and caught or dropped the player depending on rounding.
    for (x1, y1, x2, y2) in ((WEST_X + 1, LEDGE_STAND, EAST_X, E1_CAP - 1),
                             (EAST_X, E1_CAP - 1, WEST_X + 1, W2_CAP - 1),
                             (WEST_X + 1, W2_CAP - 1, GAL_FLOOR_X0 + 1, GAL_STAND)):
        what = "flue hop (%d,%d) -> (%d,%d)" % (x1, y1, x2, y2)
        check_rise(y1 - y2, "frog", what)
        check_gap(abs(x2 - x1), "frog", what)
        k._claim("step", what, x1=x1, y1=y1, x2=x2, y2=y2, form="frog")

    # ======================================================== 4 -- THE CROWN
    crown_w = CROWN_X1 - CROWN_X0 + 1
    k.clear_rect(CROWN_X0, 1, crown_w, CROWN_STAND)
    k.floor(CROWN_X0, CROWN_CAP, crown_w, depth=1)
    for x in range(CROWN_X0, CROWN_X1 + 1):
        k._claim("clear", "the crown's floor, which catches every fall up here",
                 x=x, y=CROWN_STAND, tall=2)

    # The well.  The crown's floor drains back to the ash floor and it drains ONE
    # WAY, because the thing filling it is sinking air rather than a door.
    well_w = WELL_X1 - WELL_X0 + 1
    k.clear_rect(WELL_X0, CROWN_CAP, well_w, HALL_TOP - CROWN_CAP)
    k.rect(WELL_X0, CROWN_CAP, well_w, HALL_TOP - CROWN_CAP, "downdraft")

    # The headwind seals the high line: 104 px/s of bird into 80 px/s of gust is
    # 24 px/s of progress, and holding altitude costs a flap every 0.24 s --
    # eight flaps, 1.9 s, 46 px into a six-tile lane.  You sink out of it.
    k.rect(HEAD_X0, HEAD_Y0, HEAD_X1 - HEAD_X0 + 1, HEAD_Y1 - HEAD_Y0 + 1,
           "gust_right")
    # The low line is the one that works, and it is a gift: 104 + 80 = 184 px/s
    # west, on a glide, which costs no stamina at all (stamina_regen 46/s only
    # tops up while gliding or perched, so the crossing actually refills you).
    k.rect(TAIL_X0, TAIL_Y0, TAIL_X1 - TAIL_X0 + 1, TAIL_Y1 - TAIL_Y0 + 1,
           "gust_left")
    # And the second updraft, standing on the crown's own floor and open to the
    # roof, so the hover at its lip is not under a lid.
    k.rect(LIFT_X0, LIFT_TOP, LIFT_X1 - LIFT_X0 + 1, CROWN_CAP - LIFT_TOP,
           "updraft")
    k.ledge(PERCH_X0, PERCH_CAP, PERCH_X1 - PERCH_X0 + 1, role="solid",
            stand_form="bird")

    # ---------------------------------------------------------------- dressing
    # Background and recolours only; none of it changes a flag, so none of it
    # changes what tools/prove.sh proved.
    #
    # THE `void` ROLE IS DELIBERATELY UNUSED, and that is a capture talking.  In
    # this tileset `void` resolves to `heights_air` -- which is SKY, pale, not
    # the dark deep the role's name suggests -- so the first draft's three
    # rectangles of it behind the flue, the throat and the well came out of the
    # screenshots as flat grey slabs with hard rectangular edges pasted inside a
    # mountain, and swallowed the bird sprite whole.  Left as `bg`
    # (heights_wall) the draughts are the only bright thing in a shaft, which is
    # what they are.
    #
    # `solid_alt` is heights_rock_sun, and it goes on the tops of the things you
    # land on in the upper half: the flue's shelves, the head gallery and the
    # totem's perch.  That is a readability fix as much as a lit-from-above
    # fiction -- a two-tile shelf the same colour as the wall it grows out of is
    # a shelf you find by falling off it.
    k.rect(EAST_X, E1_CAP, 2, 1, "solid_alt")
    k.rect(WEST_X, W2_CAP, 2, 1, "solid_alt")
    k.rect(GAL_FLOOR_X0, GAL_CAP, GAL_X1 - GAL_FLOOR_X0 + 1, 1, "solid_alt")
    k.rect(PERCH_X0, PERCH_CAP, PERCH_X1 - PERCH_X0 + 1, 1, "solid_alt")
    for x in (4, 16, 24, 31):
        k.rect(x, HALL_TOP, 1, HALL_CAP - HALL_TOP, "decor", "bg")
    for x in (13, 22):
        k.rect(x, 1, 1, 4, "decor", "bg")
    # Cloud, ragged rather than rectangular, and kept off the perch: a clean
    # edged block of it behind the exit read as a UI panel in the first pass.
    g.rect(9, 1, 7, 1, CLOUD, "bg")
    g.rect(11, 2, 4, 1, CLOUD, "bg")
    g.rect(17, 6, 5, 1, CLOUD, "bg")
    g.rect(GAL_X0 + 1, 1, 5, 1, CLOUD, "bg")

    # ---------------------------------------------------------------- entities
    g.ent("player_spawn", HALL_X0 + 1, HALL_STAND)
    g.ent("pad_bird", THROAT_X0, HALL_STAND)          # the last still tile
    g.ent("pad_frog", WEST_X + 1, LEDGE_STAND)        # in still air, on the ledge
    g.ent("pad_bird", GAL_FLOOR_X0 + 1, GAL_STAND)    # the flue's head
    g.ent("exit", PERCH_X0 + 1, PERCH_STAND)

    # THE HOLLOW TICK, over the walked lane six tiles east of the spawn.  It
    # hangs from the hall's roof and tells for wind_up 0.45 s, in which Kaya
    # covers 48 px at max_run: a player who runs is warned and a player who
    # dawdles under it is hit, which is the whole point of a tell.
    g.ent("enemy_dropper", GUST_X0, HALL_TOP)
    # THE CANOPY WASP patrols the headwind lane -- the line the crown does not
    # want you to take.  It is four rows above the low crossing the route uses,
    # so it is a reason and not a toll.
    g.ent("enemy_flyer", HEAD_X0 + 2, HEAD_Y0 + 2)

    g.ent("heart", THROAT_X1, CORE_LIP - 1)       # off the ride, east shoulder
    g.ent("heart", CROWN_X0 + 1, CROWN_STAND)     # where a fall from the crown lands
    for (x, y) in [(4, 26), (12, 26), (20, 26), (33, 26),
                   (EAST_X + 1, E1_CAP - 1), (WEST_X, W2_CAP - 1),
                   (GAL_X1, GAL_STAND), (23, 12), (12, 8), (5, 3)]:
        g.ent("gem", x, y)

    # ------------------------------------------------------ the declared route
    # ADR 005.  Fifteen short hops rather than four long ones, and that is the
    # prover's own arithmetic rather than caution: the budget is 50,000
    # expansions PER HOP and a greedy frontier dives into whatever hole lies
    # between it and the goal, so a hop spanning a whole segment of a 24-row
    # climb is a hop that spends its budget learning the shape of the chimney.
    # Every mark below is either a tile a body can stand on or -- in the column
    # and the crown -- a tile the bird can legitimately be in, in mid-air.
    k.mark("ash_mid", WELL_X0, HALL_STAND, form="human")
    k.mark("core_foot", THROAT_X0, HALL_STAND, form="human")     # pad_bird
    _air_mark(k, "core_ride", CORE_X0 + 1, HALL_TOP - 2)
    _air_mark(k, "core_lip", CORE_X0 + 2, CORE_LIP - 1)
    k.mark("chamber_west", THROAT_X0, CORE_LIP - 1, form="bird")
    # flue_1 and flue_2 are filed by _shelf(), on the shelves themselves.
    k.mark("wind_perch", GAL_FLOOR_X0 + 1, GAL_STAND, form="frog")  # pad_bird
    # MEASURED, and the reason this mark exists.  Asked to fly from the flue's
    # head to `dive` in one hop, the prover spent the whole 50,000-expansion
    # budget and stopped 80.0 px short at tile (27,7) -- back INSIDE the flue it
    # had just climbed.  `dive` is west and five rows DOWN, the flue is down, and
    # the west lane of the flue has no floor, so every row of the descent looked
    # like progress to a manhattan frontier until it met the flue's west wall.
    # That is ADR 005's addendum upside down: falling made the distance better
    # before it made it impossible.  Split at the doorway, neither half has a
    # hole in it worth diving into: they cost 22 and 10 expansions.
    _air_mark(k, "wind_door", CROWN_X1, GAL_STAND)
    _air_mark(k, "dive", CROWN_X1 - 2, TAIL_Y1 - 1)
    _air_mark(k, "tail_in", TAIL_X1, TAIL_Y1 - 1)
    _air_mark(k, "lift_foot", LIFT_X1, TAIL_Y1 - 1)
    _air_mark(k, "lift_lip", LIFT_X0 + 1, LIFT_TOP)

    g.route("spawn", "ash_mid", form="human")           # east along the floor
    g.route("ash_mid", "core_foot", form="human")       # across the seam, walking
    g.route("core_foot", "core_ride", form="bird")      # into the core
    g.route("core_ride", "core_lip", form="bird")       # 400 px/s, up past the seam
    g.route("core_lip", "chamber_west", form="bird")    # step off west
    g.route("chamber_west", "pad_frog", form="bird")    # along the ledge
    g.route("pad_frog", "flue_1", form="frog")          # 3 up, 3 across
    g.route("flue_1", "flue_2", form="frog")
    g.route("flue_2", "wind_perch", form="frog")        # out of the flue
    g.route("wind_perch", "wind_door", form="bird")     # due west, through the wall
    g.route("wind_door", "dive", form="bird")           # and down into the crown
    g.route("dive", "tail_in", form="bird")             # under the headwind
    g.route("tail_in", "lift_foot", form="bird")        # ride the tailwind
    g.route("lift_foot", "lift_lip", form="bird")       # the second updraft
    g.route("lift_lip", "exit", form="bird")            # onto the totem's perch
    return g, k


def main():
    grid, kit = heights_3()
    missing = kit.pal.missing()
    if missing:
        raise SystemExit("palette has unresolved roles: %s" % (missing,))
    for line in kit.audit(strict_verbs=True):
        print(line)
    write(LEVEL_ID, grid, LEVEL_NAME, music="world3")


if __name__ == "__main__":
    main()
