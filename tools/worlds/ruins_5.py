#!/usr/bin/env python3
"""RUINS_5 -- THE TIDE MAW. World 2's boss level.

Self-contained on purpose: `python3 tools/worlds/ruins_5.py` writes
levels/ruins_5.json without going near tools/build_levels.py, so this level can
be iterated against tools/prove.sh while the rest of SUNKEN RUINS is being
authored in other worktrees. To wire it into the shared builder, add

    from worlds.ruins_5 import ruins_5
    build("ruins_5", ruins_5(), "THE TIDE MAW", music="boss")

to tools/build_levels.py's `__main__` block and nothing else changes.

--art regenerates assets/sprites/boss_tide_maw.png, the Maw's 18-frame sheet.
It lives here rather than in tools/art/ because this branch owns the boss and
not the art pipeline; the drawing itself goes through tools/art/palette.py, so
every pixel is a step on a generated ramp exactly like the rest of the game.


THE SHAPE OF THE LEVEL
----------------------
Four screens, and the first three exist to put Kaya on the arena floor in the
state the fight wants her in -- human, with the fish one pad away.

    A  upper cistern, cols 0-24 rows 0-14     B  the gallery, cols 25-49 rows 0-14
    C  drowned antechamber, rows 15-29        D  THE ARENA, rows 15-29

    spawn -> pad_fish -> swim east, over one pillar and under the next
          -> duck under the sluice wall at col 20 into the flue
          -> ride the up-current twenty tiles to the surface
          -> pad_human in the water at the flue's mouth -> jump the flue
          -> east along the gallery -> off the lip, twenty tiles down, into
             the arena.

The drop is one-way by construction: the arena is walled at col 25 and col 49
and nothing in it is within reach of row 14.


WHY THE ARENA IS SHAPED LIKE THIS
---------------------------------
`docs/plan-20-levels.md` says the Grove Warden "fails the SPIRIT" of ADR 005's
check 3. Measured, from tools/bossgate.sh --quick on jungle_5 before a line of
this was written:

    refuges: 2 reachable from the arena floor, 2 not
    NOTE  unreachable refuge tiles: (30,21) (43,21)
    NOTE  they sit up to 96 px above the arena floor; Kaya's measured
    NOTE  apex as human is 46 px, so once she is down she cannot return.
    NOTE  refuge (30,21): six seconds of blade throws never damaged the boss

Two failures in one: the refuge is out of reach, and from up there the blade
flies over the boss. So:

  * **No high ledges at all.** Every standable tile in the arena is the floor
    (row 27's cap, stood on at row 26) or a one-way refuge slab two tiles above
    it. Two tiles is 32 px against a measured 46 px jump, and the gate reports
    "refuges: 17 reachable from the arena floor, 0 not".
  * **The bore is what the slabs dodge.** It runs along the floor at the Maw's
    feet, four pixels up; a body on a slab is 32 px over it. Measured:
    "AIR>LAND ... hit 23, missed 8", and the eight are exactly the slab tiles.
  * **The Maw is 46 px tall**, which is the number that makes a slab a place to
    FIGHT from and not merely to hide on: the blade leaves Kaya's chest at about
    y=389 up there and the Maw's box spans 386..432.
  * **The slabs sit INSIDE the Maw's span** (cols 31-34 and 37-40 against a
    clamp of 31-43), so it walks underneath them and its body reaches you. A
    refuge the boss can never stand under is a corner to camp in. Nothing in
    this arena is safe from everything: the bore covers the floor and misses the
    slabs, the spines cover the slabs and the mid-range floor and miss only the
    tiles right under the Maw and the ones out at the walls.
  * **The floor is unbroken wall to wall.** That is not a nicety. The first cut
    of this arena raised the refuges out of the floor as solid blocks, and their
    faces cornered Kaya against her own standoff: the strategy search spent a
    hundred attempts on it and never got the Maw below 12 of 18 health.

The tide is a real tile change, not a repaint -- see src/enemies/tide_maw.gd.
The level is authored DRAINED, which is also phase 1, so tools/prove.sh and the
tape replay both see exactly the geometry in levels/ruins_5.json.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gen_levels import Grid, write                     # noqa: E402
from world_kit import Kit, RUINS                       # noqa: E402


# ------------------------------------------------------------------ geometry
# Named once, because the boss config repeats three of them and a level whose
# arena and whose boss disagree about where the floor is has no chance at all.
ARENA_X0, ARENA_X1 = 26, 48        # interior columns of screen D
PIT_X0, PIT_X1 = 31, 43            # the span the Maw is clamped to
FLOOR_ROW = 27                     # the arena's one unbroken floor
STAND_ROW = FLOOR_ROW - 1          # 26 -- the tile a body's feet are in
SHELF_ROW = 25                     # the one-way refuge slabs
SHELF_STAND = SHELF_ROW - 1        # 24 -- two tiles over the arena floor
WEST_SLAB, EAST_SLAB, SLAB_W = 31, 37, 4   # both inside the Maw's span
DROP_COL = 42                      # the one column of the pit with no slab over it
TIDE_TOP = 21                      # the row the flood's surface lands on


def ruins_5():
    """Draw the level. Returns (Grid, Kit) so main() can audit before writing.

    The drawing is done with `Grid` and the ROLE CHARACTERS of ADR 002's
    amendment -- '#' the world's ground cap, 'd' the fill under it, 's' its
    second solid, '~'/'w' water, 'u' the up-current -- because the grid's
    `tileset="ruins"` is what turns those into ruin stone, silt and grate.

    `Kit` is here for its audit and nothing else. Its palette resolves tile
    NAMES through the flat `legend` key of data/level_legend.json, which is
    still the jungle's (see the note on `legend` in that file), so
    `RUINS.char("solid")` comes back as an understudy and draws ruin_grate
    where ruin_stone was asked for. Drawing through the role characters side-
    steps that entirely and loses nothing: `Kit.Probe` reads the same flat
    legend for FLAGS, and tests/test_level_format.gd pins every role character
    to the same gameplay flags in all five worlds, so the audit's verdict is
    the same in the ruins as in the jungle.
    """
    g = Grid(50, 30, tileset="ruins")
    k = Kit(g, RUINS)

    # ---------------------------------------------------------------- dressing
    g.rect(0, 0, 50, 30, "L", "bg")          # ruin_wall behind everything
    g.rect(1, 1, 48, 3, "X", "bg")           # the deep dark above the roof line
    g.rect(2, 17, 18, 5, "r", "bg")          # algae on the antechamber's wall
    g.rect(26, 16, 23, 9, "r", "bg")
    for x in (28, 34, 41, 46):               # the arena's broken colonnade
        g.trunk(x, 15, 12)
    g.rect(26, TIDE_TOP, 23, 1, "X", "bg")   # the high-water mark on the wall
    for x in (4, 12, 33, 45):
        g.trunk(x, 4, 3)                     # ruin columns

    # ---------------------------------------------------------------- the shell
    # Nothing walks off the edge of the world.
    g.rect(0, 0, 50, 1, "s")
    g.rect(0, 29, 50, 1, "s")
    g.rect(0, 0, 1, 30, "s")
    g.rect(49, 0, 1, 30, "s")

    # =================================================================
    # THE ROCK. Screens A and B are a corridor cut out of solid stone,
    # which is also what keeps the prover's search space small: a failed
    # hop exhausts its frontier instead of wandering open sky.
    # =================================================================
    g.rect(1, 1, 48, 3, "d")                 # the roof, rows 1-3
    g.ground(1, 7, 24, depth=10)             # screen A's mass, rows 7-16
    g.ground(25, 7, 17, depth=8)             # screen B's gallery, cols 25-41
    # Rows 4-6 are left clear: a three-tile corridor the whole way east, and
    # cols 42-48 are left as open air -- that column of nothing is the way into
    # the arena, and there is no way back up it.
    #
    # The lip is at col 41 and not further east because Kaya has to land INSIDE
    # the span the Maw is clamped to: tests/integration/integration_tests.gd
    # asserts exactly that of a boss level's traversal tape, and arena_max plus
    # the Maw's own width puts the east edge of that span at x=704. Measured,
    # with the lip one tile further east: "inside the span the boss is clamped
    # to (496..704, Kaya at 705)". One pixel. The drop is at col 42 now, which
    # lands her at x=689 with fifteen pixels to spare.

    # ---------------------------------------------------------------- screen C
    g.ground(1, 26, 6, depth=3)              # the shore, stand row 25
    g.ground(7, FLOOR_ROW, 16, depth=2)      # the channel bed, cols 7-22

    g.rect(7, 22, 13, 1, "~")                # surface row 22, cols 7-19
    g.rect(7, 23, 13, 4, "w")                # open water, rows 23-26

    # Two pillars, the shape jungle_3 proved: the first rises from the bed and
    # you pass OVER it, the second hangs from the surface and you pass UNDER.
    # Two tiles of clearance on each pass, because a slot a body does not fit
    # through is defect 2 wearing a different hat.
    g.rect(10, 24, 2, 3, "S")
    g.mark("over_one", 12, 23)
    k._claim("wet", "the pass over the bed pillar", x=12, y=23, tall=2)
    g.rect(14, 22, 2, 3, "S")
    g.mark("under_two", 17, 26)
    k._claim("wet", "the pass under the hanging pillar", x=15, y=26, tall=2)

    # The sluice wall: solid from the antechamber's ceiling down to row 24, so
    # the only way east is along the bed.
    g.rect(20, 17, 1, 8, "s")
    g.rect(20, 25, 1, 2, "w")
    k._claim("wet", "the sluice gate under the wall at col 20", x=20, y=26, tall=2)
    g.rect(23, 17, 2, 12, "s")               # the flue's east wall, down to the bed

    # ---------------------------------------------------------------- the flue
    # A 2x20 column of rising water, carved back out of the rock above it. This
    # is SUNKEN RUINS' verb doing the work: 62 px/s of lift under a fish that
    # swims 92, so the climb costs a third of what swimming it would.
    g.rect(21, 7, 2, 20, "u")                # cur_up, rows 7-26
    g.rect(21, 6, 2, 1, "~")                 # it surfaces at row 6, level with
                                             # the gallery floor's standing row
    g.mark("flue_foot", 21, 26)
    g.mark("flue_mid", 21, 15)
    for y in (26, 15, 7):
        k._claim("wet", "the flue at row %d" % y, x=21, y=y, tall=2)

    # ---------------------------------------------------------------- screen B
    k.mark("flue_lip", 23, 6)                # the far side of the flue's mouth
    k.mark("lip", 41, 6)                     # and the last tile before the drop

    # =================================================================
    # SCREEN D -- THE ARENA
    # =================================================================
    g.rect(25, 15, 1, 14, "s")                                  # sealed west
    # ONE unbroken floor, wall to wall. The first cut of this arena raised the
    # flanking shelves out of the floor as solid blocks, and measured, that was
    # a worse fight than the Grove Warden's: the shelf faces were walls, Kaya's
    # standoff is 64-92 px, and once the Maw had walked her into one there was
    # nowhere left to go. tools/bossgate.sh --record spent a hundred attempts on
    # it and its best left the Maw on 12 of 18 health. A boss you dodge by
    # retreating needs somewhere to retreat to.
    g.ground(ARENA_X0, FLOOR_ROW, ARENA_X1 - ARENA_X0 + 1, depth=2)

    # The refuges are one-way slabs over that floor instead: two tiles up, so a
    # 46 px jump reaches them from anywhere beneath, and open underneath, so the
    # whole 23-tile width is still somewhere to run. The bore passes below them.
    #
    # They sit INSIDE the Maw's span (cols 31-43) on purpose, and that is the
    # answer to the obvious objection to the first cut of this arena: a refuge
    # the boss can never stand under is a corner to camp in. Standing on a slab
    # takes you out of the bore; it does not take you out of the fight, because
    # the Maw walks under you and its 46 px body reaches 386..432 while yours on
    # the slab is 378..400. Nothing in the arena is safe from everything, and
    # every attack still has somewhere that is safe from it -- which is the
    # thing ADR 005's check 3 actually asks.
    g.platform(WEST_SLAB, SHELF_ROW, SLAB_W)
    g.platform(EAST_SLAB, SHELF_ROW, SLAB_W)
    for x in (WEST_SLAB, WEST_SLAB + SLAB_W - 1, EAST_SLAB, EAST_SLAB + SLAB_W - 1):
        k._claim("stand", "arena refuge slab at col %d" % x,
                 x=x, y=SHELF_STAND, form="human")
    for x in (ARENA_X0, PIT_X0, 37, PIT_X1, ARENA_X1):
        k._claim("stand", "arena floor at col %d" % x,
                 x=x, y=STAND_ROW, form="human")
    # Getting onto a refuge is the whole point of it, so the step up is a claim
    # and not a hope. The Grove Warden's refuges are 96 px above the arena floor
    # against a measured 46 px jump; these are 32.
    k._claim("step", "the step off the floor onto the west refuge",
             x1=WEST_SLAB, y1=STAND_ROW, x2=WEST_SLAB, y2=SHELF_STAND, form="human")
    k._claim("step", "the step off the floor onto the east refuge",
             x1=EAST_SLAB, y1=STAND_ROW, x2=EAST_SLAB, y2=SHELF_STAND, form="human")
    # Directly under the lip, not in the middle of the pit. The prover's
    # frontier is manhattan distance (ADR 005's addendum), so a landing tile
    # WEST of the fall makes the only way down look like a way away: the search
    # sat at tile (37,5) for the whole 50,000-expansion budget, 304 px short,
    # because stepping east off the lip scored worse than standing on it. Col 42
    # is also the one column inside the Maw's span with no refuge slab over it,
    # so the fall ends on the arena floor and not on a slab.
    k.mark("arena_floor", DROP_COL, STAND_ROW)

    # ---------------------------------------------------------------- entities
    g.ent("player_spawn", 2, 25)
    g.ent("pad_fish", 5, 25)
    g.ent("pad_human", 21, 6)

    # NO transform pad inside the arena, and that is a decision rather than an
    # omission. docs/plan-20-levels.md describes this fight as "flooded, you
    # must be the fish" -- but data/forms/fish.json gives the fish
    # `weapon: "bite"`, and data/weapons/bite.json is `reach: 10.0`. A fish
    # cannot throw the blade at all, and biting a boss whose hurtbox is 40x46
    # means standing inside its contact damage. Measured: with a fish pad on the
    # west refuge the recorder drifted onto it at 13 s of the flooded phase and
    # the run went from six damage and five hearts to zero damage and no hearts,
    # because Kaya spent the rest of the fight as an animal with no weapon.
    #
    # So the flood is fought WADING, and that is what makes it the hard phase:
    # `water_move_scale` 0.62 puts a human at 67 px/s against a 68 px/s pull.
    # The fish stays the level's verb in the approach, where it belongs. Giving
    # the fish a reach weapon, or building a bite-range boss, is a real design
    # answer to the plan's sentence and it is not this branch's to make.

    g.ent("boss_tide_maw", 37, STAND_ROW)
    g.ent("boss_exit", 36, STAND_ROW)

    g.ent("enemy_swimmer", 12, 25)
    g.ent("enemy_swimmer", 17, 24)
    g.ent("enemy_walker", 30, 6)
    g.ent("enemy_shooter", 37, 6)
    g.ent("heart", 3, 24)
    # One heart on each refuge, at the end of the slab furthest from the other:
    # the arena has no pickup you can take without leaving the floor.
    g.ent("heart", WEST_SLAB, SHELF_STAND)
    g.ent("heart", EAST_SLAB + SLAB_W - 1, SHELF_STAND)
    for (x, y) in [(8, 23), (9, 23), (13, 25), (18, 26), (21, 20), (22, 20),
                   (21, 11), (22, 11), (16, 6), (27, 6), (34, 6), (40, 6),
                   (WEST_SLAB + 3, SHELF_STAND), (EAST_SLAB + 1, SHELF_STAND)]:
        g.ent("gem", x, y)

    # ---------------------------------------------------- the intended solution
    # Fish for the whole of the water, human for the whole of the stone. Every
    # hop is short on purpose (ADR 005: "a hop that needs a big budget is a hop
    # that is too coarse") and the two pillar passes are their own hops because
    # over-then-under is what the swim is about.
    g.route("spawn", "pad_fish", form="human")        # two steps along the shore
    g.route("pad_fish", "over_one", form="fish")      # in, and over the bed pillar
    g.route("over_one", "under_two", form="fish")     # under the one that breaks surface
    g.route("under_two", "flue_foot", form="fish")    # duck the sluice wall at col 20
    g.route("flue_foot", "flue_mid", form="fish")     # into the up-current, C -> A
    g.route("flue_mid", "pad_human", form="fish")     # out at the top, onto the pad
    g.route("pad_human", "flue_lip", form="human")    # jump the 2-tile flue mouth
    g.route("flue_lip", "lip", form="human")          # east along the gallery, A -> B
    g.route("lip", "arena_floor", form="human")       # off the lip, 20 tiles down, B -> D
    # And there the prover stops. `boss_exit` is placed by Level.on_boss_defeated()
    # and by nothing else, so this last hop is PARTIAL by design and belongs to
    # tools/bossgate.sh check 5 -- exactly as jungle_5's does.
    g.route("arena_floor", "boss_exit", form="human")
    return g, k


# ======================================================================
# THE MAW'S SHEET.
#
# 18 frames of 48x48: six poses (idle, two swim beats, rear, lunge, crash)
# for each of the three phases, named <pose>_p1/_p2/_p3 in
# data/enemies/tide_maw.json exactly as the Warden's are. The silhouette is an
# anglerfish head on an eel's neck -- all jaw, a lure on a stalk, gill slits
# that open as it escalates -- drawn out of the `water`, `metal`, `gold` and
# `ember` ramps so it reads against ruin stone in both tide states.
#
# The 40x46 collision box sits at (4, 2) in the frame, so it covers the lure,
# the skull, both mandibles and the first coil -- everything that is actually
# the animal. The tip of the upper jaw still overhangs it, because a hurtbox
# larger than the thing that hurts you is the worst kind of unfair. 46 tall is
# also the number that makes a refuge slab a place to FIGHT from: standing on
# row 24 the blade leaves Kaya's chest at about y=389, rising ~2 px over the
# flight, and the Maw's box spans 386..432.
# ======================================================================
FRAME = 48
BOX_W, BOX_H = 40, 46
BOX_OX, BOX_OY = 4, 2


def _maw_cells():
    """The 18 frames, as ASCII rows in tools/art/palette.py's char vocabulary.

    The silhouette is read left to right: a tapering coil rising out of the
    water at the back, the skull over it, then the two mandibles hinged at the
    front of the skull with an ink throat between them. `gape` is the only
    thing that moves far, because the jaw IS the telegraph -- it is shut in
    IDLE, half open on the swim beats, pulled shut and back in WINDUP, wide in
    AIR, and slack in LAND.
    """
    import math

    # phase -> body, trim, eye, lure, gill slashes, extra gape
    PHASES = [
        ("n", "b", "c", "c", 0, 0),     # EBB       navy, cold lure, shut gills
        ("b", "c", "w", "y", 2, 2),     # FLOOD     swollen and pale, gills open
        ("d", "r", "y", "o", 3, 5),     # UNDERTOW  near-black, ember in the gill
    ]
    # pose -> gape, reach, lift, coil sway
    POSES = [
        (2, 0, 0, 0),       # idle
        (3, 1, -1, -2),     # swim a
        (3, 1, 1, 2),       # swim b
        (1, -2, -4, 0),     # windup: pulled back and shut
        (14, 4, -2, 0),     # air: the lunge, jaw wide
        (8, 2, 3, 0),       # land: slack, dragging on the bed
    ]
    F = FRAME

    def make(ph, pose):
        body, trim, eyec, lurec, gills, extra = ph
        gape, reach, lift, coil = pose
        gape += extra
        px = [["." for _ in range(F)] for _ in range(F)]

        def put(x, y, c):
            x, y = int(x), int(y)
            if 0 <= x < F and 0 <= y < F:
                px[y][x] = c

        def disc(cx, cy, rx, ry, c):
            if rx <= 0 or ry <= 0:
                return
            for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
                for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                    if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                        put(x, y, c)

        # ---- the coil, rising out of the water at the back left
        for t in range(41):
            u = t / 40.0
            cx = 7 + 15 * u + coil * math.sin(u * 3.0)
            cy = 46 - 26 * u + lift * u
            r = 9.5 - 4.5 * u
            disc(cx, cy, r, r * 0.8, body)
        for t in range(41):
            u = t / 40.0
            cx = 6 + 15 * u + coil * math.sin(u * 3.0)
            cy = 44 - 26 * u + lift * u
            r = 6.0 - 3.5 * u
            disc(cx, cy, r, r * 0.55, trim)

        # ---- the skull
        hx = 24 + reach                       # the jaw hinge
        hy = 19 + lift                        # the mouth line
        disc(hx - 5, hy - 1, 11, 9.5, body)
        disc(hx - 8, hy - 4, 6.5, 4.5, trim)

        # ---- the mandibles, hinged at (hx, hy)
        JL = 19
        up, lo = [], []
        for i in range(JL + 1):
            u = i / float(JL)
            up.append(hy - 3.0 - gape * 0.55 * u - 1.5 * u)
            lo.append(hy + 3.0 + gape * 0.45 * u)
        for i in range(JL + 1):
            for y in range(int(up[i]) + 1, int(lo[i])):
                put(hx + i, y, "k")           # the throat
        for i in range(JL + 1):
            taper = 3 if i < JL - 4 else 2
            for d in range(taper):
                put(hx + i, up[i] - d, trim if d == taper - 1 else body)
                put(hx + i, lo[i] + d, trim if d == taper - 1 else body)
        for i in range(3, JL - 1, 3):         # teeth, pointing into the gap
            put(hx + i, up[i] + 1, "w")
            put(hx + i, up[i] + 2, "A")
            put(hx + i, lo[i] - 1, "w")
            put(hx + i, lo[i] - 2, "A")

        # ---- gill slashes: one more per phase, ember-lit in the last
        for i in range(gills):
            x = hx - 14 + i * 3
            for y in range(int(hy) - 3, int(hy) + 4):
                put(x, y, "k")
                put(x + 1, y, trim)

        # ---- the eye, high and forward, and the lure it hunts with
        disc(hx - 6, hy - 7, 3.0, 3.0, "k")
        disc(hx - 6, hy - 7, 1.6, 1.6, eyec)
        put(hx - 5, hy - 8, "w")

        sx, sy = hx - 12, hy - 12
        for i in range(11):
            u = i / 10.0
            put(sx + 13 * u * u, sy - 8 * u + 2 * u * u, trim)
        disc(sx + 13, sy - 6, 2.4, 2.4, lurec)
        put(sx + 13, sy - 7, "w")

        # ---- ink outline, so the Maw reads against ruin stone in both tides
        out = [row[:] for row in px]
        for y in range(F):
            for x in range(F):
                if px[y][x] != ".":
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < F and 0 <= ny < F and px[ny][nx] not in (".", "k"):
                        out[y][x] = "k"
                        break
        return ["".join(r) for r in out]

    return [make(ph, pose) for ph in PHASES for pose in POSES]


def write_art():
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from art import palette                                   # noqa: E402
    cells = _maw_cells()
    palette.sheet("boss_tide_maw", cells, FRAME, FRAME)
    print("boss_tide_maw.png  %d frames of %dx%d" % (len(cells), FRAME, FRAME))


def main(argv):
    if "--art" in argv:
        write_art()
        return 0
    g, k = ruins_5()
    for line in k.audit():
        print(line)
    write("ruins_5", g, "THE TIDE MAW", music="boss")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
