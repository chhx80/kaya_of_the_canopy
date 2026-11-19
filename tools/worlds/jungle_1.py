#!/usr/bin/env python3
"""jungle_1 -- CANOPY TRAIL, at five times the length (docs/plan-longer-levels.md).

Self-contained: `python tools/worlds/jungle_1.py` writes levels/jungle_1.json.
`tools/build_levels.py` calls `jungle_1()` and audits the `(Grid, Kit)` it gets.

THE SHAPE
---------
350 x 30 tiles: fourteen screens across, two down, of which the route passes
through about eighteen. The trail runs along the forest floor, climbs a giant
tree into the canopy, crosses the treetops on rope bridges, drops back to the
ground through a cave, climbs over an old stone shrine and runs out to the
exit. Six sections, each with one idea and one landmark, a checkpoint between
each pair, and difficulty rising from the first to the last:

  1. THE TRAILHEAD   run, jump, the spike gap, the first vine. The opening
                     screen is today's, tile for tile, enemy for enemy.
  2. THE GREAT TREE  a switchback climb up a trunk four columns wide: one-way
                     branches, upward gap jumps, two vines.
  3. THE BRIDGES     the canopy: rope bridges over the understory, a wasp over
                     every gap, a spitter down the long bridge, then a walk of
                     small knots over a thorn floor.
  4. THE HOLLOW      a cave back down to the ground: ticks on the ceiling,
                     thorns on the ledges, a vine down, a boar on the floor.
  5. THE SHRINE      stone terraces and pits, a boar on the first terrace, a
                     spitter on the altar, a wasp on the high lintel over a
                     bed of thorns.
  6. THE LAST RUN    three pits on two-wide posts, a four-tile leap under a
                     wasp, a gallery of branches over thorns into a spitter's
                     sight, a boar at the gate.

Every jump on the route is inside world_kit.LIMITS (human: rise 2, gap 3)
except the one leap in section 6, which is four tiles with a one-tile drop on
purpose -- the commitment jump -- and is proved, not assumed.

THE CAMERA, AND WHY NOTHING ON THE ROUTE FALLS FURTHER THAN FOUR TILES
-----------------------------------------------------------------------
The view is 308 x 184 world units, so a standing Kaya sees about 92 units
(5.75 tiles) below her centre. tests/integration/tape_replay.gd counts a
landing BLIND when the floor it ends on was outside the view at take-off. Every
drop on the route is four rows or fewer; the cave and the shrine go down vines.

SECRETS
-------
Off the route, each with a way back onto it (tools/pickupgate.sh for the
hearts; `--probe` both ways for each):
  * a bough of four gems over the stump (section 1);
  * a heart and gems on a hidden branch under the long bridge -- drop through
    the bridge (down + jump), walk east, climb the vine up to knot 6 (3);
  * a heart and gems in a vault in the shrine's first terrace, behind three
    crates the blade opens from the step below it (5).

AUTHORING
---------
Each section is a `Section`: a span of columns with its own origin, so its
shapes are written in local coordinates and the section can move as a block.
Its marks are its stretch of the route, in order, and a checkpoint is a mark
too (a route may only name an entity type that occurs once). `g.sections`
keeps them, which is what tools/level_metrics.py reads to split the proof
tape and the enemy count by section.
"""
import os, sys

_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _TOOLS)

from gen_levels import Grid, write                                  # noqa: E402
from world_kit import Kit, JUNGLE                                   # noqa: E402

LEVEL_ID = "jungle_1"
LEVEL_NAME = "CANOPY TRAIL"

W, H = 350, 30
FLOOR = 27          ## the forest floor's cap row; Kaya stands on row 26
CANOPY = 8          ## the bridges' cap row; she stands on row 7
THORNS = 29         ## the bottom row, where every pit ends


class Section:
    """A stretch of the level in local column coordinates.

    Rows are absolute (every section shares the floor and the canopy line);
    columns are relative to `x0`. Everything the section places is recorded,
    so the route and the metrics can be built from the sections themselves.
    """

    def __init__(self, g, k, key, title, x0):
        self.g, self.k = g, k
        self.key, self.title, self.x0 = key, title, x0
        self.route = []           # mark names in the order they are walked
        self.enemies = []
        self.checkpoints = []

    def X(self, x):
        return self.x0 + x

    # -- foreground ---------------------------------------------------------
    def ground(self, x, y, w, depth=None):
        self.g.ground(self.X(x), y, w, depth=depth)

    def platform(self, x, y, w):
        self.g.platform(self.X(x), y, w)

    def bridge(self, x, y, w):
        self.g.hline(self.X(x), y, w, "-")

    def stone(self, x, y, w, h, cap="S"):
        """Cave and shrine stone: a mossy cap row over plain stone."""
        self.g.rect(self.X(x), y, w, h, "s")
        if cap:
            self.g.hline(self.X(x), y, w, cap)

    def rect(self, x, y, w, h, ch, layer="fg"):
        self.g.rect(self.X(x), y, w, h, ch, layer)

    def pit(self, x, w):
        """Thorns at the bottom of a pit whose sides are already drawn."""
        self.g.rect(self.X(x), THORNS, w, 1, "^")

    def crates(self, x, y, n, vertical=False):
        self.g.crates(self.X(x), y, n, vertical=vertical)

    def vine(self, x, top, bottom, landing):
        self.k.climb(self.X(x), top, bottom, landing=landing)

    # -- background ---------------------------------------------------------
    def canopy(self, x, y, w, h):
        self.g.canopy(self.X(x), y, w, h)

    def trunk(self, x, y, h):
        self.g.trunk(self.X(x), y, h)

    # -- entities -----------------------------------------------------------
    def ent(self, type_, x, y, **props):
        self.g.ent(type_, self.X(x), y, **props)
        if type_.startswith("enemy_"):
            self.enemies.append(type_)

    def gems(self, *cells):
        for x, y in cells:
            self.ent("gem", x, y)

    def mark(self, name, x, y):
        self.k.mark(name, self.X(x), y)
        self.route.append(name)

    def check(self, name, x, y):
        """A checkpoint: the entity long/engine implements, and a mark on the
        same cell so the route can name it."""
        self.g.ent("checkpoint", self.X(x), y)
        self.mark(name, x, y)
        self.checkpoints.append(name)


# ================================================================== sections
def trailhead(s):
    """1. Today's opening, then a raised run, a second pit and the first vine."""
    s.canopy(0, 0, 66, 3)
    s.canopy(14, 2, 10, 2)
    s.canopy(33, 1, 12, 3)
    for x in (4, 11, 29, 38, 46, 58):
        s.trunk(x, 3, 24)

    s.ground(0, FLOOR, 14)
    s.pit(14, 3)                  # 3-tile spike pit: one clean jump
    s.ground(17, FLOOR, 13)
    s.platform(9, 24, 4)          # optional high route with a gem ledge
    s.platform(15, 25, 3)
    s.crates(25, 26, 2)           # a knee-high hop, or the blade
    s.ground(30, 25, 10)          # a two-tile step up
    s.pit(40, 3)                  # the second pit, the same width
    s.ground(43, 25, 8)
    s.vine(50, 19, 24, landing="right")
    s.ground(51, 20, 4)           # the stump the vine climbs
    s.platform(45, 17, 4)         # a bough over the stump: a gem cache
    s.ground(55, 23, 9)

    s.g.ent("player_spawn", 2, 26)
    s.ent("enemy_walker", 8, 26)
    s.ent("enemy_jumper", 20, 26)
    s.ent("enemy_walker", 36, 24, facing="left")
    s.gems((10, 23), (11, 23), (16, 24), (34, 24), (52, 19))
    s.gems((45, 16), (46, 16), (47, 16), (48, 16))

    s.mark("s1_pit1_lip", 13, 26)
    s.mark("s1_step", 31, 24)
    s.mark("s1_pit2_lip", 39, 24)
    s.mark("s1_vine_foot", 50, 24)
    s.mark("s1_stump", 52, 19)
    s.check("cp1", 61, 22)


def great_tree(s):
    """2. Floor run east, vine up, branches west, vine up into the crown."""
    for x in range(18, 22):       # the landmark: one trunk four columns wide
        s.trunk(x, 2, 23)
    s.canopy(2, 0, 36, 4)
    s.canopy(12, 4, 16, 3)
    s.canopy(16, 7, 8, 2)
    for x in (4, 32):
        s.trunk(x, 4, 21)

    s.ground(0, 25, 40)
    s.vine(36, 18, 24, landing="left")
    s.platform(28, 19, 8)         # B1, at the top of the first vine
    s.platform(20, 18, 5)         # B2: three across, one up
    s.platform(14, 16, 4)         # two across, two up
    s.platform(8, 14, 4)          # two across, two up
    s.vine(7, 7, 13, landing="right")
    s.ground(8, CANOPY, 8, depth=2)   # the crown, where section 3 starts

    s.ent("enemy_walker", 12, 24, facing="left")
    s.ent("enemy_jumper", 26, 24)
    s.ent("enemy_walker", 22, 17)
    s.ent("enemy_flyer", 18, 12, axis="x", range=40)
    s.gems((6, 24), (24, 24), (31, 18), (15, 15), (9, 13))

    s.mark("s2_vine_a_foot", 36, 24)
    s.mark("s2_b1", 34, 18)
    s.mark("s2_b1_lip", 28, 18)
    s.mark("s2_b2", 21, 17)
    s.mark("s2_p3", 15, 15)
    s.mark("s2_p4", 9, 13)
    s.check("cp2", 10, 7)


def bridges(s):
    """3. The treetops. A miss on the first bridge drops back into section 2;
    from the long bridge on, the understory floor is thorns."""
    s.canopy(29, 13, 42, 10)      # the understory: a sea of leaves below
    s.canopy(32, 11, 8, 2)
    s.canopy(48, 12, 14, 1)
    s.canopy(76, 12, 28, 9)
    for x in (20, 27, 31, 52, 56, 74, 80, 85, 91, 100):
        s.trunk(x, 10, 19)

    s.bridge(8, CANOPY, 10)
    s.ground(18, CANOPY, 4, depth=2)
    s.ground(25, CANOPY, 4, depth=2)      # a three-tile gap at 22-24
    s.ground(29, 6, 4, depth=2)           # two up
    s.bridge(33, 6, 14)                   # the long bridge, down the spitter's sight
    s.ground(47, 6, 5, depth=3)
    s.ground(54, 9, 4, depth=2)           # three down, over a two-tile gap
    s.bridge(58, 9, 5)
    s.bridge(66, 9, 4)                    # a broken bridge: three tiles missing
    s.ground(70, 9, 6, depth=3)
    # The crown walk: three-wide knots, three-tile gaps, up and down.
    s.ground(79, 10, 3, depth=2)          # three across, one down
    s.ground(84, 8, 3, depth=2)           # two across, two up
    s.ground(90, 10, 3, depth=2)          # three across, two down
    s.ground(96, 9, 9, depth=3)           # three across, one up
    s.rect(32, THORNS, 73, 1, "^")        # the understory floor

    # The secret under the long bridge: drop through it (down + jump) onto a
    # branch, take the heart, walk east under the spitter's knot and climb the
    # vine in the gap at 52-53, which tops out level with knot 6 -- a step-off
    # exit like every vine on the route. (A vine up through the bridge itself
    # was tried first: leaving its top needs up released on the same frame as
    # jump is pressed. The prover can do that; a thumb on a phone cannot.)
    # The branch also catches a fall into that gap.
    s.ground(37, 12, 17, depth=1)
    s.vine(53, 8, 11, landing="right")

    s.ent("enemy_walker", 15, 7, facing="left")
    s.ent("enemy_flyer", 23, 5, axis="y", range=40)
    s.ent("enemy_flyer", 40, 3, axis="x", range=48)
    s.ent("enemy_shooter", 50, 5)
    s.ent("enemy_flyer", 64, 6, axis="y", range=40)
    s.ent("enemy_flyer", 88, 6, axis="y", range=40)
    s.gems((12, 7), (26, 7), (36, 5), (38, 5), (59, 8), (67, 8), (85, 6))
    s.ent("heart", 39, 11)
    s.gems((38, 11), (40, 11), (41, 11))

    s.mark("s3_bridge1_end", 20, 7)
    s.mark("s3_knot3", 26, 7)
    s.mark("s3_knot4", 30, 5)
    s.mark("s3_long_mid", 40, 5)
    s.mark("s3_knot5", 49, 5)
    s.mark("s3_knot6", 55, 8)
    s.mark("s3_broken_lip", 62, 8)
    s.mark("s3_far", 67, 8)
    s.mark("s3_knot7", 75, 8)
    s.mark("s3_ka", 80, 9)
    s.mark("s3_kb", 85, 7)
    s.mark("s3_kc", 91, 9)
    s.check("cp3", 102, 8)


def hollow(s):
    """4. Down through a cave. Every drop is four rows or a vine."""
    s.rect(0, 3, 36, 25, "r", "bg")
    s.rect(14, 6, 8, 6, "X", "bg")
    s.rect(2, 15, 6, 6, "X", "bg")
    s.rect(24, 20, 6, 5, "X", "bg")

    s.stone(0, 2, 36, 28, cap=None)
    s.rect(1, 4, 33, 23, ".")                 # the cavern
    s.rect(0, 7, 1, 2, ".")                   # the way in, from the last knot
    s.rect(34, 25, 2, 2, ".")                 # the way out, at the bottom east
    s.stone(1, 9, 9, 1)                       # E0
    s.stone(8, 13, 15, 1)                     # E1
    s.rect(15, 12, 2, 1, "^")                 # thorns on E1
    s.vine(23, 12, 20, landing="left")        # the vine down to E2
    s.stone(12, 21, 16, 1)                    # E2, walked west
    s.rect(17, 20, 2, 1, "^")
    s.stone(3, 24, 9, 1)                      # E3
    s.stone(1, 27, 35, 3)                     # the cave floor, walked east

    s.ent("enemy_dropper", 6, 5)
    s.ent("enemy_dropper", 12, 5)
    s.ent("enemy_walker", 20, 12, facing="left")
    s.ent("enemy_dropper", 15, 14)
    s.ent("enemy_walker", 14, 26)
    s.ent("enemy_charger", 28, 26, facing="left")
    s.gems((4, 8), (19, 11), (13, 20), (7, 23), (24, 26))

    s.mark("s4_in", 2, 8)
    s.mark("s4_e0_lip", 9, 8)
    s.mark("s4_e1", 11, 12)
    s.mark("s4_e1_far", 21, 12)
    s.mark("s4_vine_top", 22, 12)
    s.mark("s4_vine_foot", 23, 20)
    s.mark("s4_e2_mid", 19, 20)
    s.mark("s4_e2_lip", 13, 20)
    s.mark("s4_e3", 7, 23)
    s.mark("s4_floor", 2, 26)
    s.mark("s4_run", 20, 26)
    s.mark("s4_out", 34, 26)


def shrine(s):
    """5. Terraces and pits, the altar, then the lintel over a thorn bed."""
    for x in (4, 15, 29, 45, 53):
        s.rect(x, 8, 2, 19, "r", "bg")        # standing stones
    s.canopy(0, 0, 62, 3)
    s.canopy(12, 3, 12, 3)
    s.canopy(26, 3, 8, 2)
    s.canopy(42, 3, 16, 4)

    s.ground(0, FLOOR, 6)
    s.stone(6, 25, 3, 5)                      # a step up two
    s.stone(9, 23, 13, 7)                     # the first terrace, a boar on it
    s.stone(25, 23, 2, 7)                     # a post between two pits
    s.pit(22, 3)
    s.pit(27, 3)
    s.stone(30, 23, 9, 7)                     # the altar terrace
    s.stone(33, 21, 3, 2)                     # the altar, a spitter on it
    s.stone(39, 21, 2, 9)                     # the stair up to the lintel
    s.stone(41, 19, 2, 11)
    s.stone(43, 17, 14, 1)                    # the lintel
    s.ground(43, FLOOR, 14)
    s.rect(43, 26, 14, 1, "^")                # the thorn bed under it
    s.vine(57, 16, 26, landing="left")        # down the far side
    s.ground(57, FLOOR, 6)
    # The vault: a pocket in the first terrace's west face, one row below the
    # step. Standing on the step, Kaya's head is in the terrace's cap row, so
    # the doorway is two crates tall AND the cap over the vault's first column
    # is a third crate: without it she stops at the lip under the overhang
    # (seen in the running game; the probe only touched the heart's box from
    # the lip). The blade opens all three from the step, two of them thrown
    # from a jump.
    s.rect(10, 24, 5, 2, ".")
    s.crates(9, 24, 2, vertical=True)
    s.crates(10, 23, 1)
    s.ent("heart", 12, 25)
    s.gems((11, 25), (13, 25), (14, 25))

    s.ent("enemy_charger", 19, 22, facing="left")
    s.ent("enemy_jumper", 26, 22)
    s.ent("enemy_shooter", 34, 20)
    s.ent("enemy_walker", 37, 22, facing="left")
    s.ent("enemy_flyer", 50, 15, axis="x", range=48)
    s.gems((7, 24), (31, 22), (47, 16), (48, 16), (60, 26))

    s.check("cp4", 2, 26)
    s.mark("s5_step", 7, 24)
    s.mark("s5_terrace", 11, 22)
    s.mark("s5_pit_lip", 21, 22)
    s.mark("s5_post", 25, 22)
    s.mark("s5_altar_foot", 31, 22)
    s.mark("s5_altar", 34, 20)
    s.mark("s5_stair1", 39, 20)
    s.mark("s5_stair2", 41, 18)
    s.mark("s5_lintel_mid", 50, 16)
    s.mark("s5_lintel_end", 56, 16)
    s.mark("s5_vine_foot", 57, 26)
    s.check("cp5", 61, 26)


def last_run(s):
    """6. Posts over pits, the long leap, the thorn gallery, the gate."""
    s.canopy(0, 0, 74, 4)
    s.canopy(11, 4, 10, 2)
    s.canopy(33, 4, 10, 3)
    s.canopy(52, 4, 14, 2)
    for x in (3, 7, 16, 22, 27, 37, 42, 47, 58, 64, 70):
        s.trunk(x, 4, 23)

    s.ground(0, FLOOR, 10)
    s.pit(10, 3)
    s.ground(13, FLOOR, 2)                    # post 1
    s.pit(15, 3)
    s.ground(18, FLOOR, 2)                    # post 2
    s.pit(20, 3)
    s.ground(23, FLOOR, 6)
    s.pit(29, 4)                              # the four-tile leap, one down
    s.ground(33, 28, 8)
    # The thorn gallery: three one-way branches over a floor of thorns.
    s.rect(41, THORNS, 20, 1, "^")
    s.platform(43, 26, 3)
    s.platform(49, 25, 3)
    s.platform(55, 27, 3)
    s.ground(61, FLOOR, 12)
    s.rect(73, 0, 1, FLOOR, "s")              # the world's east wall

    s.ent("enemy_flyer", 16, 23, axis="x", range=40)
    s.ent("enemy_jumper", 25, 26)
    s.ent("enemy_flyer", 31, 23, axis="y", range=40)
    s.ent("enemy_walker", 38, 27, facing="left")
    s.ent("enemy_flyer", 53, 22, axis="y", range=40)
    s.ent("enemy_shooter", 64, 26)
    s.ent("enemy_charger", 69, 26, facing="left")
    s.gems((13, 25), (14, 25), (18, 25), (31, 25), (32, 25), (50, 23))
    s.g.ent("exit", s.X(71), 26)

    s.mark("s6_pit1_lip", 9, 26)
    s.mark("s6_post1", 14, 26)
    s.mark("s6_post2", 19, 26)
    s.mark("s6_leap_lip", 28, 26)
    s.mark("s6_landing", 35, 27)
    s.mark("s6_gallery_lip", 40, 27)
    s.mark("s6_p1", 44, 25)
    s.mark("s6_p2", 50, 24)
    s.mark("s6_p3", 56, 26)
    s.mark("s6_bank", 61, 26)


SECTIONS = (
    ("s1", "THE TRAILHEAD", 0, trailhead),
    ("s2", "THE GREAT TREE", 64, great_tree),
    ("s3", "THE BRIDGES", 72, bridges),
    ("s4", "THE HOLLOW", 177, hollow),
    ("s5", "THE SHRINE", 213, shrine),
    ("s6", "THE LAST RUN", 276, last_run),
)


def jungle_1():
    g = Grid(W, H)
    k = Kit(g, JUNGLE)
    g.sections = []
    for key, title, x0, draw in SECTIONS:
        s = Section(g, k, key, title, x0)
        draw(s)
        g.sections.append(s)
    # The intended solution (ADR 005): human the whole way, through every
    # section's marks in order, from the spawn to the exit.
    stops = ["spawn"] + [m for s in g.sections for m in s.route] + ["exit"]
    for a, b in zip(stops, stops[1:]):
        g.route(a, b, form="human")
    return g, k


if __name__ == "__main__":
    g, k = jungle_1()
    for line in k.audit():
        print(line)
    write(LEVEL_ID, g, LEVEL_NAME, music="world1")
