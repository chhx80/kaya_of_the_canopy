#!/usr/bin/env python3
"""heights_1 -- UPDRAFT.  The opener of World 3, THERMAL HEIGHTS.

Self-contained: running this file under the project python writes
levels/heights_1.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `heights_1()` returning `(Grid, Kit)`,
which is the tuple that writer's `build()` helper audits before it writes
anything.

    source tools/env.sh && "$PYVENV" tools/worlds/heights_1.py
    tools/prove.sh heights_1

WHAT THIS LEVEL TEACHES
-----------------------
World 3's new verb is the updraft: a tile of rising air (206 `updraft`,
[0,-400], and 207 `updraft_strong`, [0,-560]).  Nobody has met one before this
level, so -- like every world opener in docs/plan-20-levels.md -- it is
introduced in a room where getting it wrong costs nothing, and only then over a
drop that costs something.

  1. THE LEDGE (screen C).  Kaya arrives human on a cold shoulder of rock and
     walks east.  Nothing is asked of her.  `pad_bird` sits on the walk, on
     flat ground, four tiles short of the thermal's foot.

  2. THE TAME THERMAL (screens C -> A).  A column of `updraft` seventeen tiles
     tall standing ON the very floor she walked in on, with open air on BOTH
     sides for its whole height.  So the ride is entered by walking into it and
     left by steering out of it, at any height, and what is underneath every
     exit is the same floor she started from -- and the four columns that ARE
     the draft catch her on the way down and give the whole ride back.  Falling
     costs nothing, which is the whole reason this column has no walls: see THE
     DRAFTS HAVE NO WALLS.  It ends on `perch_1`, sixteen tiles above the ledge.
     Nothing patrols this room, and the note beside the entities says why.

  3. THE CHASM (screens A -> B).  Ten tiles of air between `perch_1` and
     `perch_2`, with the far lip FIVE tiles higher, over a scree basin sixteen
     tiles under perch_1 that the rib at col 22 seals off from the ledge.  This is
     the same verb over a real drop: the `updraft_strong` column in the middle
     of the gap does all of it, and what a fall costs is the climb back, not a
     life -- the strong column runs down to the basin's own floor, so the basin
     is a place you ride out of.

  4. THE SUMMIT (screen B).  Through the notch at col 35 and down into the nest
     hollow, where `pad_human` and the exit are.  The hollow is walled on both
     sides and four tiles deep, so the human it hands back cannot walk out of
     it into anything: the only thing to do in there is reach the exit
     (ADR 004).

THE MEASUREMENTS THIS GEOMETRY IS BUILT ON
------------------------------------------
All from tests/test_verbs_currents.gd, which drives the *shipping* movement
code with no scene tree, plus data/forms/bird.json:

* An updraft is DRY AIR, not water: `flags_of(206) & WATER == 0`.  It lifts
  every form by one rule, because `FormBase.apply_gravity` makes the fall cap
  `max_fall + current.y`.  Bird max_fall 190 against -400 is a 210 px/s climb;
  against -560 it is 370 px/s.  Kaya's own 330 against -400 is 70 px/s, which
  the test pins at -70 +/- 2.

* THE HOVER, and why every perch here sits one row under its draft's top row.
  The push is area-weighted (`FormBase.current_at`), so the lift tapers as the
  hitbox leaves the top of the column and you settle where what is left exactly
  cancels gravity -- head clear of the lip, feet still inside it.  That is
  `test_an_updraft_column_holds_you_at_its_lip`, and its closing line is the
  instruction to authors: "a landing at the top of a draught has to be
  reachable from the hover, not from an imagined launch."

  The algebra says where that is: equilibrium is current.y = -max_fall, so the
  fraction of a bird's 9 px box still inside the column is 190/400 = 0.475 in
  `updraft` and 190/560 = 0.339 in `updraft_strong` -- feet 4.3 px and 3.1 px
  into the column's TOP ROW.  MEASURED in the running game instead, by the
  `hover` step of tools/seq/heights_1.json after five seconds of settling: the
  bird sits at pos.y 149 with vel.y 22, so its feet are at y=158 against a lip
  at y=160.  The 60 Hz loop does not park on the equilibrium, it oscillates a
  few pixels either side of it -- a 9 px box gives the taper only 9 px to work
  in -- but the answer is the same one to a tile: THE HOVER'S FEET ARE IN THE
  DRAFT'S TOP ROW.

  So a plank one row BELOW the column's top row has its stand row at the hover,
  and both perches here are built that way, one tile of air clear of the
  column.  The drift out costs 16 px of travel, 0.15 s at 104 px/s, about 5 px
  of sink:

      tame   feet y~158-164, plank top y=176 -> arrives 7-18 px above it
      strong feet y~ 78- 83, plank top y= 96 -> arrives 8-18 px above it

  A plank level WITH the draft's top row would have to be reached by flapping
  out of the hover, and a plank two rows above it by flapping and gliding back.
  Both work -- `test_the_bird_can_flap_out_of_the_top_of_an_updraft` -- but
  neither is what a teaching level should ask for first.

* YOU CANNOT JUMP OUT OF A HOVER.  You are airborne the whole time you hover,
  so there is no coyote time and no jump; the exit is steering sideways, and
  for the bird also flapping (`vel.y = flap_vel + current.y` = -172 - 190 =
  -362 at the hover, about 156 px of extra rise).  That is why both columns are
  open on both sides over their whole height and carry three or more rows of
  air above them: a draft you can only leave at one place is a softlock, and
  `_self_checks` below refuses to emit one.

* STAMINA, stated in the units the player spends it in.  flap_cost 12 against
  max_stamina 100, and airborne regen is stamina_regen 46 x 0.25 = 11.5/s
  (form_bird.gd), so a 0.24 s flap cycle is a net 9.24: a full bar buys TEN
  flaps over 2.4 s, which is 250 px (15.6 tiles) of level travel or 292 px
  (18 tiles) of climb.  Perched, regen is 46 + perch_regen_bonus 34 = 80/s, so
  a perch refills the whole bar in 1.25 s.

  That is the honest shape of beat 3 and it is worth writing down rather than
  overclaiming.  Ten tiles of air with the far lip five tiles up is past the
  biggest bird hop this project has ever PROVED -- 6 across and 5 up, on
  jungle_4's perch_2 -> perch_3, which is why LIMITS["bird"] says {rise 5,
  gap 6} -- so the kit's own `cloud_deck` would refuse to draw it, and it is
  deliberately not used here for that reason.  Flapping it cold is not
  impossible: it is about 1.7 s of level flight, seven of the ten flaps a full
  bar buys.  On the thermal it costs none of them.  The lesson this level can
  honestly teach is the price, not an impossibility, and the levels after it
  are where the bar has no perch to lean on.

THE DRAFTS HAVE NO WALLS, WHICH IS WHY `updraft_shaft()` IS NOT USED
-------------------------------------------------------------------
`world_kit.updraft_shaft()` is the kit's updraft vocabulary and it builds on
`Kit.shaft`, so it inherits both historical shaft defects: it cannot be capped
across its full width (defect 6) and its left wall stops two tiles above the
floor so you can walk in rather than being sealed out (defect 5).  Those are
the right guarantees for a chimney and the wrong shape for THIS level.  A
walled shaft can only be left at its mouth, so a rider who mistimes the ride is
committed to it -- and beat 2's entire promise is that a mistake costs nothing
and puts you back where you started.  So both columns here are bare
`k.rect(..., "updraft")` in open chambers, and the guarantees the helper would
have given are re-stated as level-specific claims in `_self_checks`: a floor
under the foot, open non-solid air on both sides of the top row, and two rows
of air above it.

THE PALETTE, AND WHY IT NAMES JUNGLE TILES
------------------------------------------
`world_kit.Palette.char()` resolves a tile NAME through the flat `legend` key of
data/level_legend.json, which ADR 002's amendment leaves as the *jungle* view
because tools/reachability.py and tools/build_hub.py read it directly.  So
world_kit's own HEIGHTS palette -- which names heights_rock, heights_plank,
heights_chain -- finds no character for any of them and falls through to an
understudy, emitting whatever character the understudy owns: `solid` would give
's', which the heights tileset binds to heights_basalt rather than heights_rock,
and `bg` would give 'r', which is heights_cloud, a background accent.  The
shapes would be right and the mountain would be built out of the wrong stone.

So this palette names, for each role, the jungle tile that OWNS the character
the heights tileset binds to the art we want.  It is ADR 002's role table read
in the other direction -- '#' is every world's ground cap, 'L' its background
wall -- and it is safe for exactly the reason ADR 002 pins with a test: the role
mapping preserves gameplay flags across worlds, so grass_top (solid) and
heights_rock (solid) are the same tile to every checker that reads flags, and
`"tileset": "heights"` in the level JSON is what decides the art.  The upshot
that matters here: `Palette.missing()` is empty and `Palette.substituted` stays
EMPTY, so `Kit.audit(strict_verbs=True)` is meaningful -- the columns below are
the real updraft tiles 206 and 207 and not empty air wearing their shape.  The
two draft roles need no trick at all: 'U' and '*' are `shared` characters and
mean the same tile in every world.

WHERE THE WALKED FLOORS SIT
---------------------------
Every stand row in this level is checked against the defect ruins_4 shipped.
`CameraController` picks its screen from the body's CENTRE, so a 22 px body on a
floor capped at a multiple-of-15 row has its feet exactly on the seam and its
centre on the screen ABOVE -- which therefore never draws the floor it is
standing on.  The four stand rows here are 26 (cap 27), 10 (plank 11), 5
(plank 6) and 11 (cap 12); `_self_checks` fails the build if any claimed stand
row has (row + 1) % 15 == 0.

The vertical seam is x=400, the line between cols 24 and 25, and beat 3 crosses
it in mid-glide over the chasm with the strong column two tiles further east at
cols 27-30.  A flight through a seam is not the defect the memory file warns
about -- that one is a WALKED route along a seam, or an on-foot hop that leaves
one screen and lands on another.  Nothing in this level walks near a seam:
every walked floor is wholly inside one screen, and the only on-foot hops are
flat steps along the ledge and the hollow.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                      # noqa: E402
import world_kit                                        # noqa: E402
from world_kit import Kit, Palette, Probe               # noqa: E402

LEVEL_ID = "heights_1"
LEVEL_NAME = "UPDRAFT"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the heights role
## character.  See the module docstring: this is a character map, not an art
## claim, and the art comes from `"tileset": "heights"` at load time.  The five
## draft roles are `shared` characters and need no indirection.
HEIGHTS_W3 = Palette("thermal_heights", {
    "bg": "bg_leaves",              # 'L' -> 242 heights_wall
    "solid": "grass_top",           # '#' -> 240 heights_rock
    "solid_alt": "stone_mossy",     # 'S' -> 241 heights_rock_sun
    "packed": "dirt",               # 'd' -> 243 heights_scree
    "block": "stone",               # 's' -> 249 heights_basalt
    "oneway": "wood_platform",      # '=' -> 246 heights_plank
    "ladder": "vine",               # '|' -> 248 heights_chain
    "hazard": "spikes",             # '^' -> 247 heights_vent
    "breakable": "crate",           # 'c' -> 251 heights_shell
    "decor": "tree_trunk",          # 'T' -> 245 heights_stack
    "void": "bg_dark",              # 'X' -> 244 heights_air
    "water": "water",               # 'w'  shared
    "water_top": "water_top",       # '~'  shared
    "shoulder": "cracked_stone",    # 'k'  shared
    "rubble": "rubble",             # 'o'  shared
    "updraft": "updraft",           # 'U'  shared, 206, [0,-400]
    "updraft_strong": "updraft_strong",   # '*'  shared, 207, [0,-560]
    "downdraft": "downdraft",       # 'V'  shared, 208
    "gust_right": "gust_right",     # ')'  shared, 209
    "gust_left": "gust_left",       # '('  shared, 210
})

## Every draft column in the level: (x0, x1, top_row, bottom_row, role).
## `_self_checks` re-derives the three guarantees `updraft_shaft()` would have
## given from this table against the FINISHED grid -- a floor under the foot,
## non-solid air beside the top row on both sides, and two rows of air above.
DRAFTS = [
    (14, 17, 10, 26, "updraft"),          # the tame thermal, 17 tiles
    (27, 30,  5, 26, "updraft_strong"),   # the chasm's elevator, 22 tiles
]

## The sunlit band: heights_rock_sun is drawn on every exposed upward face above
## this row, so the tops of the high shelves catch the light and the shaded rock
## down in the cleft does not.  Cosmetic only -- 241 and 240 are both plain
## `solid`, the same tile to every flag-reading checker.
SUN_ROW = 13


def _sunlight(k):
    g = k.g
    cap, fill, alt = k.ch("solid"), k.ch("packed"), k.ch("solid_alt")
    p = Probe(g)
    lit = []
    for y in range(1, min(SUN_ROW + 1, g.h - 1)):
        for x in range(g.w):
            if g.fg[y][x] not in (cap, fill):
                continue
            if not p.solid(x, y - 1):
                lit.append((x, y))
    for x, y in lit:
        g.put(x, y, alt)


def heights_1():
    g = Grid(W, H, tileset="heights")
    k = Kit(g, HEIGHTS_W3, form="human")

    # ------------------------------------------------------------- the rock
    # Carved rather than built.  `Kit.fill_solid` says why: a mountain with
    # rooms cut out of it has a small reachable state space, so a prover hop
    # that fails exhausts its frontier instead of spending its whole budget
    # wandering open sky -- and open sky is exactly what a bird level would
    # otherwise be.
    k.fill_bg("bg")
    k.fill_solid("packed")
    k.shell(1, "solid")

    # ============================================= 1. THE LEDGE (screen C)
    # Twenty-one tiles of flat rock.  Stand row 26 over a cap on row 27:
    # 27 % 15 = 12, so the floor is drawn on the same screen as the body
    # standing on it.
    #
    # The roof over it climbs in three steps -- row 15 over cols 1-5, row 9 over
    # cols 6-11, row 5 over the cleft -- rather than running flat.  That is a
    # silhouette fix and it is worth recording as one: the first draft roofed
    # everything west of the cleft at row 15, and the capture of screen A
    # (cols 0-24, rows 0-14) was three-quarters solid rock with the thermal in
    # one corner.  Stepping the roof puts the ridge line across the screen the
    # ride ends on, so what the player sees at the top of the climb is a
    # mountain face and not a wall.
    k.corridor(1, 26, 5, h=11)                # cols 1-5, rows 16-26
    k.corridor(6, 26, 6, h=17)                # cols 6-11, rows 10-26
    k.floor(1, 27, 21, depth=1)               # cap row 27, cols 1-21
    # Not on the route: `Kit.mark` files a "stand" claim, so naming the two
    # walked floors is how `audit()` and `_self_checks` get told to re-check
    # them against the finished grid and against the screen-row rule.
    k.mark("shoulder_w", 4, 26)

    # ==================================== 2. THE TAME THERMAL (screens C -> A)
    # The cleft: one room, rows 6-26, so the ride and the floor it starts from
    # are the same space.  The ledge's air joins it along cols 11/12.
    k.corridor(12, 26, 10, h=21)              # cols 12-21, rows 6-26

    # The rib.  Col 22 is left as rock from row 11 down to the bedrock, which is
    # what makes beat 3's drop a REAL drop: everything west of it falls back
    # onto the ledge, everything east of it falls into the scree basin.  Its top
    # five rows are cut away so the bird crosses it at the height it leaves the
    # perch at, without having to gain a tile first.
    k.clear_rect(22, 6, 1, 5)                 # col 22, rows 6-10

    # The column.  Seventeen tiles, standing on the floor at row 26 so it is
    # entered by walking east into it, and open air at cols 12-13 and 18-21 for
    # its whole height so it is left by steering out of it.  Eighteen tiles of
    # climb is what a whole stamina bar buys cold (18 tiles, see the docstring),
    # so the draft is not a shortcut here, it is the tool.
    x0, x1, top, bottom, role = DRAFTS[0]
    k.rect(x0, top, x1 - x0 + 1, bottom - top + 1, role)

    # The perch, one row UNDER the column's top row, so its stand row IS the
    # hover row and the landing is a 16 px drift rather than a flap.  One tile
    # of air (col 18) between the column and the plank.
    k.ledge(19, 11, 3)                        # plank row 11, stand row 10
    k.mark("perch_1", 20, 10, form="bird")

    # ========================================== 3. THE CHASM (screens A -> B)
    # Twelve columns of open air from the roof to the scree basin.  Its west
    # wall below row 11 is the rib; its east wall is the summit's, at col 35.
    k.corridor(23, 26, 12, h=25)              # cols 23-34, rows 2-26

    # THE UNDERCUT.  The basin runs six tiles east under the summit's own floor,
    # roofed by the three rows of rock at cols 35-40 rows 13-15 and stopped by
    # col 41.  It is a dead end with a heart in it and it is off every hop, so
    # it is worth saying why it is here: without it screen D (cols 25-49, rows
    # 15-29) was two-thirds unbroken rock -- the capture showed the bird pinned
    # to the left edge of a wall -- and the fall into the chasm had no reward in
    # it at all.  It cannot open the summit from below: the hollow's floor is
    # capped on row 12 and rows 13-15 under it are solid across the whole span.
    k.corridor(35, 26, 6, h=11)               # cols 35-40, rows 16-26
    k.floor(23, 27, 18, depth=1)              # the scree basin, stand row 26

    # The elevator.  `updraft_strong` because this column has to lift a bird
    # from wherever the glide off perch_1 drops it -- anywhere in rows 6-26 --
    # to a hover five tiles ABOVE the perch it left, and 370 px/s does that in
    # well under a second.  It runs all the way down to the basin's own floor,
    # which is what makes the basin a place you ride out of rather than a pit:
    # walk east into it and it gives the whole climb back.
    #
    # At cols 27-30, not 25-28.  The vertical screen seam is x=400, the line
    # between cols 24 and 25, and `CameraController` freezes the sim for the
    # length of every flip.  Two tiles of plain air east of the seam means the
    # flip lands while she is still gliding level, not on the frame she meets
    # the lift.
    x0, x1, top, bottom, role = DRAFTS[1]
    k.rect(x0, top, x1 - x0 + 1, bottom - top + 1, role)

    k.ledge(32, 6, 3)                         # plank row 6, stand row 5
    k.mark("perch_2", 33, 5, form="bird")

    # ============================================== 4. THE SUMMIT (screen B)
    # The notch: col 35 is rock from row 8 to the bedrock and open above it, so
    # the hollow has exactly one way in and it is over the top.  Crossing it
    # from perch_2 is two tiles of glide -- 0.31 s, 5 px of sink under
    # glide_gravity 105 -- so she arrives through rows 5-6 with the whole notch
    # to spare.
    k.corridor(35, 7, 1, h=6)                 # col 35, rows 2-7

    # The nest hollow.  Walled by col 35 (rows 8-12) and col 48, floor capped on
    # row 12, four tiles deep against a human rise of two: nothing that lands in
    # here can walk out of it, which is the whole of ADR 004 for this level --
    # the only pad that hands back the human is in a room whose only feature is
    # the exit.
    k.corridor(36, 11, 12, h=10)              # cols 36-47, rows 2-11
    k.floor(36, 12, 12, depth=1)              # cap row 12, stand row 11
    k.mark("hollow_w", 37, 11)

    # ------------------------------------------------------------- dressing
    # Open air behind every carved room, then cloud banding, then background
    # rock stacks.  All on the bg layer, so none of it collides.
    for (x, y, w, h) in [(1, 16, 5, 11), (6, 10, 6, 17), (12, 6, 10, 21),
                         (22, 6, 1, 5), (23, 2, 12, 25), (35, 2, 1, 6),
                         (36, 2, 12, 10), (35, 16, 6, 11)]:
        g.rect(x, y, w, h, "X", "bg")         # 'X' -> 244 heights_air
    for (x, y, w) in [(1, 19, 11), (6, 12, 6), (12, 8, 10), (12, 17, 10),
                      (23, 4, 12), (23, 12, 12), (23, 21, 12),
                      (36, 4, 12), (36, 9, 12), (35, 18, 6)]:
        g.rect(x, y, w, 1, "r", "bg")         # 'r' -> 250 heights_cloud
    # Basalt stacks, background only.  Each one hugs a rock face rather than
    # standing in the middle of a room: a dark column in open air reads as
    # something you can land on, and this level has two columns of moving air
    # whose lanes must stay unambiguous, so nothing decorative goes near cols
    # 14-17 or 27-30.
    # (11,18) was one of these and is not any more: it stood in the middle of the
    # walk from `pad_bird` to `thermal_foot`, which is the first four tiles a
    # player moves as a bird, and in the capture it read as a wall across them.
    for (x, y, h) in [(2, 20, 7), (21, 16, 11), (23, 13, 14),
                      (34, 10, 17), (37, 5, 7), (46, 5, 7), (40, 18, 9)]:
        g.rect(x, y, 1, h, "T", "bg")         # 'T' -> 245 heights_stack
    _sunlight(k)

    # ------------------------------------------------------------- entities
    g.ent("player_spawn", 2, 26)
    g.ent("pad_bird", 9, 26)
    k.mark("thermal_foot", 13, 26, form="bird")
    g.ent("pad_human", 38, 11)
    g.ent("exit", 45, 11)

    # NOTHING PATROLS THE SAFE ROOM, and that is a decision rather than an
    # oversight.  The ledge and the cleft share one unbroken floor from col 1 to
    # col 21, and `walker.json` is 32 px/s with turn_at_ledge and chase_range 96:
    # a walker anywhere on that floor eventually walks the whole of it and
    # arrives at the player, wherever she is.  MEASURED: a walker at (20,26)
    # reached the draft's foot inside five seconds and knocked the bird out of
    # the ride mid-capture.  Beat 2's promise is that a mistake in here costs
    # nothing, and an enemy that can turn up anywhere in the room is a cost.
    #
    # So the inhabitants live where a mistake has already happened.  Both flyers
    # patrol +/- 64 px on x with bob_amplitude 6 and NO chase, so each one stays
    # in its own nine-tile lane: (6,20) is six rows above the ledge walk and
    # never reaches it, and (32,20) is fifteen rows under the perch-to-perch
    # glide line.  The walker is on the scree, which is the floor you only meet
    # by falling into the chasm.  Enemies do not sample currents
    # (`enemy_base.gd` has its own `apply_gravity` and never calls
    # `FormBase.current_at`), so nothing here gets lifted by a column it stands
    # beside.
    g.ent("enemy_flyer", 6, 20)
    g.ent("enemy_flyer", 32, 20)
    g.ent("enemy_walker", 24, 26)

    for (x, y) in [(4, 26), (7, 26), (12, 26),        # the ledge
                   (15, 22), (15, 16),                # riding the tame thermal
                   (20, 10),                          # perch_1
                   (24, 9),                           # out over the chasm
                   (28, 14),                          # riding the strong one
                   (33, 5),                           # perch_2
                   (25, 26), (31, 26),                # down in the scree
                   (40, 11), (43, 11)]:               # the nest hollow
        g.ent("gem", x, y)
    g.ent("heart", 39, 26)                    # the consolation, in the undercut

    # ------------------------------------------------- the route (ADR 005)
    # Six hops.  Three of them are flat walks and exist only so the three that
    # are the level start from a known state; the shape ADR 005 asks for is
    # short hops, because a hop that needs a big budget is a hop that is too
    # coarse.
    g.route("spawn", "pad_bird", form="human")            # east along the ledge
    g.route("pad_bird", "thermal_foot", form="bird")      # four tiles, on foot
    g.route("thermal_foot", "perch_1", form="bird")       # THE RIDE: 16 tiles up
    g.route("perch_1", "perch_2", form="bird")            # 10 across, 5 up, on the strong draft
    g.route("perch_2", "pad_human", form="bird")          # through the notch, into the hollow
    g.route("pad_human", "exit", form="human")            # seven tiles of summit
    return g, k


# --------------------------------------------------------------------- checks
## Three things tools/prove.sh cannot tell you and tests/ only tells you after a
## whole Godot boot.  Cheap, so they run every time the level is emitted.

def _self_checks(g, k):
    p = Probe(g)
    bad = []

    # (a) A standable tile with one tile of headroom reads as a passage and
    # behaves as a wall (defect 2).  tests/test_level_validity.gd checks exactly
    # this; catching it here costs milliseconds instead of a test run.
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
    # and must not stand on a floor the screen it is drawn on does not contain.
    # The second half is the defect ruins_4 shipped: `CameraController` picks the
    # screen from the body's CENTRE, so feet on a cap row that is a multiple of
    # 15 put the centre on the screen above and the floor off the bottom of it.
    must = {"exit", "pad_bird", "pad_human", "player_spawn", "gem", "heart",
            "enemy_walker", "enemy_flyer"}
    for e in g.entities:
        if e["type"] not in must:
            continue
        x, y = e["x"], e["y"]
        if not p.clear(x, y, 2):
            bad.append("%s at (%d,%d) has no two tiles of headroom"
                       % (e["type"], x, y))
        if (p.solid(x, y + 1) or p.oneway(x, y + 1)) and (y + 1) % 15 == 0:
            bad.append("%s at (%d,%d) stands on a cap row %d, a screen "
                       "boundary: its centre lands on the screen above and the "
                       "floor is never drawn" % (e["type"], x, y, y + 1))
    for kind, c in k.claims:
        if kind != "stand":
            continue
        if (c["y"] + 1) % 15 == 0:
            bad.append("%s: stand row %d sits on cap row %d, a screen boundary"
                       % (c["why"], c["y"], c["y"] + 1))

    # (c) The guarantees `world_kit.updraft_shaft()` would have filed, restated
    # for a column that deliberately has no walls (see the docstring).  A draft
    # you can only leave in one place is a softlock, and a draft with nothing
    # under its foot is a draft you can never walk into.
    for (x0, x1, top, bottom, role) in DRAFTS:
        ch = k.ch(role)
        for y in range(top, bottom + 1):
            for x in range(x0, x1 + 1):
                if p.ch(x, y) != ch:
                    bad.append("draft cols %d-%d rows %d-%d: (%d,%d) is '%s', "
                               "not '%s' -- something was drawn over the column"
                               % (x0, x1, top, bottom, x, y, p.ch(x, y), ch))
        for x in range(x0, x1 + 1):
            if not p.solid(x, bottom + 1):
                bad.append("draft cols %d-%d: nothing under its foot at "
                           "(%d,%d), so it cannot be walked into"
                           % (x0, x1, x, bottom + 1))
        for x in (x0 - 1, x1 + 1):
            if p.solid(x, top):
                bad.append("draft cols %d-%d: (%d,%d) beside its top row is "
                           "solid. You cannot jump out of a hover -- steering "
                           "sideways is the exit, so both sides of the top must "
                           "be open air." % (x0, x1, x, top))
        for y in (top - 1, top - 2):
            if p.solid((x0 + x1) // 2, y):
                bad.append("draft cols %d-%d: row %d above it is solid; the "
                           "hover needs air over the lip" % (x0, x1, y))

    # (d) NO WALKED HOP CROSSES MOVING AIR.  Three shapes are walls to
    # tools/solver/sim.gd rather than obstacles, and each one spends the whole
    # 50k budget before it says so: a breakable tile (the prover carries no
    # weapon and models nothing that breaks a tile), a hazard tile (a hazard
    # state is pruned by `rejection()`), and a draft planted across a floor the
    # route WALKS -- the same shape as "a current is a wall for the human",
    # because the column lifts the body off the hop the moment it steps in.
    #
    # The first two are absent by construction: the emitted fg layer uses only
    # '#', 'S', 'd', '=', '.', 'U' and '*', and neither 'c'/'k'/'o' nor '^'
    # appears anywhere.  The third is a geometry question, so it is asked here.
    # Every flat hop -- one whose two ends stand on the same row -- must cross
    # nothing but still air.  The one hop in this level that ENTERS a column,
    # `thermal_foot` -> `perch_1`, is not flat and is meant to be lifted; the
    # three walked hops all stop short of col 14 or sit in the hollow.
    where = dict(g.marks)
    for e in g.entities:
        if e["type"] == "player_spawn":
            where["spawn"] = {"x": e["x"], "y": e["y"]}
        elif e["type"].startswith("pad_") or e["type"] == "exit":
            where[e["type"]] = {"x": e["x"], "y": e["y"]}
    drafts = {k.ch(role) for (_, _, _, _, role) in DRAFTS}
    for hop in g.hops:
        a, b = where.get(hop["from"]), where.get(hop["to"])
        if a is None or b is None or a["y"] != b["y"]:
            continue
        y = a["y"]
        if not (p.solid(a["x"], y + 1) or p.oneway(a["x"], y + 1)):
            continue
        for x in range(min(a["x"], b["x"]), max(a["x"], b["x"]) + 1):
            if p.ch(x, y) in drafts:
                bad.append("route hop '%s' -> '%s' is a flat walk along row %d "
                           "and (%d,%d) is moving air: the column lifts the "
                           "body off the hop and the prover spends its whole "
                           "budget failing to walk through it"
                           % (hop["from"], hop["to"], y, x, y))

    if bad:
        raise world_kit.WorldKitError(
            "%s: %d self-check failure(s):\n  %s"
            % (LEVEL_ID, len(bad), "\n  ".join(bad)))


def main():
    g, k = heights_1()
    for line in k.audit(strict_verbs=True):
        print(line)
    _self_checks(g, k)
    print("  palette      missing=%s substituted=%s"
          % (HEIGHTS_W3.missing() or "none", HEIGHTS_W3.substituted or "none"))
    write(LEVEL_ID, g, LEVEL_NAME, music="world3")


if __name__ == "__main__":
    main()
