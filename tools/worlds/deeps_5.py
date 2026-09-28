#!/usr/bin/env python3
"""DEEPS_5 -- THE BROOD QUEEN. World 4's boss level.

Self-contained on purpose, exactly like tools/worlds/ruins_5.py and
tools/worlds/heights_5.py: `python3 tools/worlds/deeps_5.py` writes
levels/deeps_5.json without going near tools/build_levels.py, so this level can
be iterated against tools/prove.sh and tools/bossgate.sh while the other four
TERMITE DEEPS levels are being authored in other worktrees. To wire it into the
shared builder, add

    from worlds.deeps_5 import deeps_5
    build("deeps_5", deeps_5(), "THE BROOD QUEEN", music="boss")

to tools/build_levels.py's `__main__` block and nothing else changes.

Unlike the Stormcrest's and the Maw's, this boss's sheet is NOT in here: it is
`build_boss_brood_queen()` in tools/art/sprites.py, called from
tools/gen_art.py, because by M4 every sprite in the game has a generator in the
shared module (see CHANGELOG, "M3 polish: every sprite has a generator") and a
new one authored off to the side would be the only exception.


THE PALETTE, AND WHY IT NAMES JUNGLE TILES
------------------------------------------
`world_kit.Palette.char()` resolves a tile NAME through the flat `legend` key of
data/level_legend.json, which ADR 002's amendment leaves as the *jungle* view
(tools/reachability.py and tools/build_hub.py read it directly). A palette that
names `deep_earth` therefore finds no character, falls through to `UNDERSTUDY`,
and emits whatever character the understudy owns -- `stone` -> 's', which the
deeps tileset binds to deep_packed, not deep_earth. The shapes would be right
and the mound would be built out of the wrong earth.

So this palette names, for each role, the jungle tile that OWNS the character
the deeps tileset binds to the art this level wants. It is ADR 002's role table
read in the other direction, and it is safe for the reason ADR 002 pins with a
test: the role mapping preserves gameplay flags across worlds, so grass_top
(solid) and deep_earth (solid) are the same tile to every checker that reads
flags, and `"tileset": "deeps"` in the level JSON is what decides the art.

The three breakables are the exception and they are named DIRECTLY, because they
are *shared* characters -- 'O' luminous_wall, 'm' termite_wall, 'o' rubble mean
the same tile in every world, so they have characters in the flat legend and
need no stand-in. That matters more here than anywhere else in the game: the
luminous wall is this fight's whole idea, and a luminous wall drawn with an
understudy would be a crate that lights nothing.

`Palette.missing()` and `Palette.substituted` both stay EMPTY, which is why
`audit(strict_verbs=True)` can be asked for.


THE SHAPE OF THE LEVEL
----------------------
Four screens, and the approach is a DESCENT, which is the one thing a termite
mound gives you for free:

    A  the upper galleries, cols 0-24 rows 0-14    B  the east gallery, cols 25-49 rows 0-14
    C  solid earth,         rows 15-29             D  THE ROYAL CELL -- the arena, rows 15-29

    spawn -> east along the upper gallery
          -> off its end into the chute, seven tiles down to the lower gallery
          -> east across the A->B seam on solid ground
          -> east along the east gallery to its end at col 34
          -> off the end, eleven tiles down the brood shaft, through the cell's
             roof and onto the arena floor.

The drop is one-way by construction: the cell is roofed at row 15 except the
three columns of that shaft, and nothing in the arena is within eleven tiles of
it. Screen C is left as undisturbed earth, which is also what keeps the prover's
frontier small (`Kit.fill_solid`'s docstring): a failed hop exhausts itself
inside the rock instead of wandering open space.

**There is no transform pad in this level, and that is a decision.** Every other
DEEPS level leans on the frog; this one is a fall, and a fall needs no form. The
reason to keep it that way is the arena: `data/forms/frog.json` is
`can_attack: false`, so arriving as a frog would mean authoring a `pad_human` on
the arena floor, and ruins_5 measured what a second pad inside an arena costs.
More to the point, THIS fight is about the blade and a breakable wall -- the
luminous wall's break_hold is 0.4 s, so Kaya can shoulder through it *or* cut it
with the blade, and both of those are hers as a human and neither is the frog's.


THE FIGHT
---------
docs/plan-20-levels.md: "The arena is dark. She is visible only when she
attacks, or lit by breaking a luminous wall -- which also removes the cover you
were standing behind."

All three of those are here, and the third is a real, permanent trade:

  * **Dark** is `Ambience` -- a shade quad and a lantern, visual only, so
    tools/prove.sh proves the same geometry a lit room would (ADR 005;
    tests/test_verbs_darkness.gd holds the whole feature to that). The entry for
    deeps_5 belongs in data/ambience.json and is reported rather than written
    here, because five agents are adding entries to that one file at once.
  * **Visible only when she attacks** is a RENDERING behaviour in
    src/enemies/brood_queen.gd: her sprite alpha is her attack state. Nothing in
    the collision, the tile grid or her own decisions can see it.
  * **The luminous walls are two real breakable plugs of cover**, at cols 43-44
    and 46-47, each two columns wide and two tiles tall, standing between the
    arena floor and a brood cell behind it. Breaking one lights the chamber (the `emissive` pool bound to
    tile 214 dies with the tile, which src/enemies/brood_queen.gd is what
    notices) and lets the ground wave into the cell it was shielding. The Queen
    never puts them back: unlike THE TIDE MAW's flood and THE STORMCREST's gale,
    this change to the level is the PLAYER's and it is permanent.


WHY THE ARENA IS SHAPED LIKE THIS
---------------------------------
The rule is THE TIDE MAW's, stated in tools/worlds/ruins_5.py and applied to the
Warden and the Stormcrest afterwards: every standable tile is the floor or a
one-way refuge two tiles above it, every attack misses somewhere a player can
actually stand and fight from, and nothing is safe from everything.

Twenty-three interior columns, and every one of them has a job:

    26-28  open floor. The west end, and where the fight starts: the Boss Gate
           stages Kaya on the leftmost tile of the lowest standable row, which
           is (26,27), and walks her out to `boss_exit` at (27,26) for check 5.
           So NO luminous wall may stand west of the gate -- tools/reachability.py
           reads a breakable as a wall, and a gate behind one is a gate the
           validator says nobody can reach. That single constraint is why both
           walls are at the east end.
    29-31  under the WEST COMB: solid earth hanging from the roof, rows 16-21.
    32-34  open floor, with the brood shaft coming through the roof at 32-34 and
           landing her on (33,26) -- inside the span the Queen is clamped to,
           which tests/integration/integration_tests.gd asserts of a boss
           level's traversal tape.
    35-36  the WEST SHELF: a one-way refuge, row 25, stood on at row 24.
    37-38  the EAST SHELF, the same.
    39-41  under the EAST COMB.
    42     open floor.
    43-44  LUMINOUS WALL A, rows 25-26.
    45     the first brood cell: floor, open to the roof.
    46-47  LUMINOUS WALL B, rows 25-26.
    48     the second brood cell.

  * **The combs are the spore fall's dodge and the shelves are the wave's, and
    the two sets do not overlap.** That is the whole of ADR 005's check 3 in one
    sentence, and it is the shape heights_5 proved: a ground attack you dodge by
    being 32 px up, an overhead attack you dodge by standing under rock, and
    nowhere that is both. The wave runs the floor 4 px up and dies on a luminous
    wall; the spore fall is thrown from the roof row, so a shot over a comb is
    born inside solid earth and dies on the frame it is born.
  * **The combs stop at row 21, five rows over the floor, which is a measured
    number.** heights_5 recorded what row 24 cost: a body under a roof 32 px up
    rises ten pixels, which is neither over the wave nor onto anything. Row 21
    leaves the full 46 px of measured jump under the rock.
  * **The combs are over PLAIN FLOOR, never over a shelf.** A shelf under a comb
    would be safe from the wave and safe from the spore fall at once, which is a
    corner to camp in and the one thing the gate's check 3 cannot see (it only
    asks whether each attack misses *somewhere*).
  * **The luminous walls are OUTSIDE the Queen's clamp and the cells behind them
    are entered over the top.** `arena_inset` 120 holds her body inside
    x 520..680, i.e. cols 32-42; wall A starts at x 688. So she can never be
    stopped by a wall, and she can never follow Kaya into a cell -- but a
    two-tile wall is a 32 px step against a 46 px jump, so Kaya gets in and out
    without breaking anything. A shelter you can only reach by destroying it
    would be no shelter at all.
  * **Each wall is TWO columns wide, and that is a measurement and not a taste.**
    The first cut made them one column each, and the Boss Gate answered "is this
    refuge reachable" by holding one direction and jumping at it from the six
    nearest floor tiles -- which flew clean over a 16 px target and reported the
    top of wall B unreachable. heights_5's suite recorded the same effect from
    the other side ("a column it calls unreachable might be one the scripted
    jump flies past"). A two-tile top is a landing, and all four of them are
    reported reachable now.
  * **The floor is unbroken from col 26 to col 42.** ruins_5 records what the
    alternative cost: raising refuges out of the floor as solid blocks cornered
    Kaya against her own standoff and the recorder never got the Maw below 12 of
    18. The two walls are the only solids standing on this floor and they are
    both behind the fight.
  * **Every tile the Queen cannot reach is a tile the blade can reach her from.**
    The extremes are (26,27) and (48,27): from (26,27) Kaya's chest is at x 432
    and the blade's 118 px carries it to 550, against a Queen whose left edge
    never passes 520; from (48,27) it carries to 650 against a right edge that
    reaches 680. Both connect, which is the other half of "no refuge is a
    stalemate" -- and the Boss Gate measured it rather than took it on trust:
    16 refuges reachable from the arena floor, 0 not, and not one of them
    reported as a place the blade could not reach her from.

The level is authored with nothing broken, which is also phase 1, so
tools/prove.sh and the traversal tape both see exactly the geometry in
levels/deeps_5.json -- and unlike the other two world-changing bosses, so does
every later phase, because this Queen does not write to the tile grid at all.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                     # noqa: E402
from world_kit import Kit, Palette                     # noqa: E402

LEVEL_ID = "deeps_5"
LEVEL_NAME = "THE BROOD QUEEN"
W, H = 50, 30

## Role -> the jungle tile that owns the character the deeps tileset binds to the
## art this level wants. See the module docstring. The three breakables are named
## directly because they are shared characters in every world.
DEEPS_CHARS = Palette("termite_deeps", {
    "bg":         "bg_leaves",      # 'L' -> 262 deep_comb
    "solid":      "grass_top",      # '#' -> 260 deep_earth
    "solid_alt":  "stone_mossy",    # 'S' -> 261 deep_crust
    "packed":     "dirt",           # 'd' -> 263 deep_chitin
    "block":      "stone",          # 's' -> 271 deep_packed
    "oneway":     "wood_platform",  # '=' -> 266 deep_shelf
    "ladder":     "vine",           # '|' -> 268 deep_ladder
    "hazard":     "spikes",         # '^' -> 267 deep_spore
    "breakable":  "crate",          # 'c' -> 270 deep_glowwall (weapon only)
    "decor":      "tree_trunk",     # 'T' -> 265 deep_root
    "void":       "bg_dark",        # 'X' -> 264 deep_void
    "water":      "water",          # 'w'  shared
    "water_top":  "water_top",      # '~'  shared
    "glowwall":   "luminous_wall",  # 'O'  shared, 214, break_hold 0.4
    "shoulder":   "termite_wall",   # 'm'  shared, 213, break_hold 0.45
    "rubble":     "rubble",         # 'o'  shared, 215
})

# ------------------------------------------------------------------ geometry
# Named once, because data/enemies/brood_queen.json repeats six of them and an
# arena whose boss and whose author disagree about where the floor is has no
# chance at all.

# ---- screen A, the upper galleries
UPPER_STAND = 5                    # feet row of the gallery she spawns in
UPPER_CAP = UPPER_STAND + 1        # 6  -- its floor
UPPER_X0, UPPER_X1 = 1, 16         # the floored run; the chute is east of it
CHUTE_X0, CHUTE_X1 = 17, 19        # three columns of open shaft
LOWER_STAND = 12                   # feet row of the lower gallery
LOWER_CAP = LOWER_STAND + 1        # 13
LOWER_X0, LOWER_X1 = 13, 23        # in screen A; it continues into B

# ---- screen B, the east gallery and the brood shaft
EAST_X0, EAST_X1 = 25, 31          # floored run in B, feet still on LOWER_STAND
SHAFT_X0, SHAFT_X1 = 32, 34        # the brood shaft: three columns, no floor

# ---- screen D, THE ROYAL CELL
ARENA_X0, ARENA_X1 = 26, 48        # interior columns
ROOF_ROW = 15
FLOOR_ROW = 27                     # the one unbroken floor cap
STAND_ROW = FLOOR_ROW - 1          # 26 -- the tile a body's feet are in
SHELF_ROW = 25                     # the one-way refuges
SHELF_STAND = SHELF_ROW - 1        # 24 -- 32 px over the arena floor
COMB_TOP, COMB_BOT = 16, 21        # the overhangs, hung from the roof
WEST_COMB = (29, 31)
EAST_COMB = (39, 41)
WEST_SHELF = (35, 36)
EAST_SHELF = (37, 38)
GLOW_A, GLOW_B = 43, 46            # the two luminous walls
GLOW_W, GLOW_H = 2, 2              # two columns wide, rows 25-26
CELL_A = (45, 45)                  # the brood cell behind wall A
CELL_B = (48, 48)                  # and behind wall B
DROP_COL = 33                      # where the brood shaft lands her
BOSS_COL = 40                      # where the Queen is standing when it starts
EXIT_COL = 27                      # boss_exit, on the open west floor


def deeps_5():
    """Draw the level. Returns (Grid, Kit) so main() can audit before writing.

    Drawn with `Grid` and the ROLE CHARACTERS of ADR 002's amendment -- '#' the
    world's ground cap, 'd' the fill under it, 's' its second solid, '=' its
    one-way, 'O' the shared luminous wall -- because the grid's `tileset="deeps"`
    is what turns those into deep earth, chitin, packed spoil, shelf and glowing
    comb. `Kit` is here for its claims and its audit: the claims are checked
    against the grid as it FINALLY stands, which is the only moment at which
    they are true or false.
    """
    g = Grid(W, H, tileset="deeps")
    k = Kit(g, DEEPS_CHARS, form="human")

    # ---------------------------------------------------------------- the mound
    # Solid earth everywhere, then carved. `Kit.fill_solid`'s own docstring is
    # the reason: a tunnel cut out of rock has a tiny reachable state space, so
    # a failed prover hop exhausts its frontier instead of burning its budget.
    k.fill_bg("bg")                          # deep_comb behind everything
    g.rect(0, 0, W, H, "d")                  # deep_chitin: the mound's body
    k.shell(1, "block")                      # nothing walks off the world

    # ================================================================
    # SCREEN A -- the upper galleries
    # ================================================================
    k.corridor(UPPER_X0, UPPER_STAND, CHUTE_X1 - UPPER_X0 + 1)
    g.rect(UPPER_X0, UPPER_CAP, UPPER_X1 - UPPER_X0 + 1, 1, "#")
    for x in (UPPER_X0, 6, 11, UPPER_X1):
        k._claim("stand", "upper gallery at col %d" % x,
                 x=x, y=UPPER_STAND, form="human")
    # The chute. Three columns of nothing from the gallery's end down to the
    # lower gallery, so walking east off col 16 is the way on and the only one.
    # Seven tiles: a fall costs nothing and cannot be climbed back up, which is
    # what makes the descent one-way without a single locked door.
    g.rect(CHUTE_X0, UPPER_CAP, CHUTE_X1 - CHUTE_X0 + 1,
           LOWER_CAP - UPPER_CAP, ".")
    for x in range(CHUTE_X0, CHUTE_X1 + 1):
        k._claim("clear", "the chute at col %d" % x,
                 x=x, y=UPPER_STAND, tall=2)
    g.rect(CHUTE_X0, 1, CHUTE_X1 - CHUTE_X0 + 1, UPPER_STAND - 1, "X", "bg")

    # The lower gallery, running east to the A->B seam. It is floored right
    # across the seam so the screen flip happens with her feet on the ground:
    # a route that crosses a seam airborne passes the gate and plays badly --
    # the flip freezes the simulation for the title card and she falls through
    # the pause.
    k.corridor(LOWER_X0, LOWER_STAND, EAST_X1 - LOWER_X0 + 1)
    g.rect(LOWER_X0, LOWER_CAP, EAST_X1 - LOWER_X0 + 1, 1, "#")
    for x in (LOWER_X0, 18, 23, 25, EAST_X1):
        k._claim("stand", "lower gallery at col %d" % x,
                 x=x, y=LOWER_STAND, form="human")

    # ================================================================
    # SCREEN B -- the east gallery and the brood shaft
    # ================================================================
    # Three columns with no floor at the gallery's east end: she walks off col 31
    # and falls eleven tiles, through the cell's roof, onto the arena floor.
    g.rect(SHAFT_X0, LOWER_STAND - 1, SHAFT_X1 - SHAFT_X0 + 1,
           ROOF_ROW - LOWER_STAND + 2, ".")
    for x in range(SHAFT_X0, SHAFT_X1 + 1):
        k._claim("clear", "the brood shaft at col %d" % x,
                 x=x, y=LOWER_STAND, tall=2)
        k._claim("clear", "the brood shaft through the roof at col %d" % x,
                 x=x, y=ROOF_ROW, tall=2)
    g.rect(SHAFT_X0, 1, SHAFT_X1 - SHAFT_X0 + 1, LOWER_STAND - 2, "X", "bg")
    # And a wall east of it, so the gallery ends AT the shaft rather than
    # offering a 1-tile hop over it.
    g.rect(SHAFT_X1 + 1, 1, 1, ROOF_ROW - 1, "s")

    # ================================================================
    # SCREEN D -- THE ROYAL CELL
    # ================================================================
    g.rect(ARENA_X0 - 1, ROOF_ROW, 1, H - 1 - ROOF_ROW, "s")   # sealed west
    g.rect(ARENA_X0, ROOF_ROW + 1, ARENA_X1 - ARENA_X0 + 1,
           FLOOR_ROW - ROOF_ROW - 1, ".")
    g.rect(ARENA_X0, ROOF_ROW, ARENA_X1 - ARENA_X0 + 1, 1, "s")
    # ... with the brood shaft coming through it.
    g.rect(SHAFT_X0, ROOF_ROW, SHAFT_X1 - SHAFT_X0 + 1, 1, ".")
    g.rect(ARENA_X0, ROOF_ROW + 1, ARENA_X1 - ARENA_X0 + 1,
           FLOOR_ROW - ROOF_ROW - 1, "X", "bg")

    # ONE unbroken floor, wall to wall, with crust bleached into the two shelf
    # bays so the fight reads: the Queen comes at you across the pale spoil.
    g.ground(ARENA_X0, FLOOR_ROW, ARENA_X1 - ARENA_X0 + 1, depth=3)
    for x0, x1 in (WEST_SHELF, EAST_SHELF):
        g.hline(x0, FLOOR_ROW, x1 - x0 + 1, "S")

    # The two combs. Solid earth from the roof down to row 21, which is what
    # makes the three floor tiles under each of them the spore fall's dodge
    # window: a shot thrown from the roof row over a comb is born inside solid
    # earth. Packed spoil, like the roof, and not the ground cap: '#' draws a lit
    # top edge and the only face of a comb the player ever sees is its underside.
    for x0, x1 in (WEST_COMB, EAST_COMB):
        g.rect(x0, COMB_TOP, x1 - x0 + 1, COMB_BOT - COMB_TOP + 1, "s")
        for x in range(x0, x1 + 1):
            k._claim("stand", "the floor under the comb at col %d" % x,
                     x=x, y=STAND_ROW, form="human")

    # The refuges: one-way shelves two tiles over the floor, inside the span the
    # Queen is clamped to, open underneath so the whole 18-tile run is still
    # somewhere to sprint.
    for x0, x1 in (WEST_SHELF, EAST_SHELF):
        k.ledge(x0, SHELF_ROW, x1 - x0 + 1, stand_form="human")
        # Getting onto a refuge is the whole point of it, so the step up is a
        # claim and not a hope: 32 px against a measured 46 px jump.
        k._claim("step", "the step off the floor onto the shelf at col %d" % x0,
                 x1=x0, y1=STAND_ROW, x2=x0, y2=SHELF_STAND, form="human")

    # THE LUMINOUS WALLS. Two tiles tall each, standing on the floor at the east
    # end with a brood cell behind them. `Kit.glow_wall` is what checks that the
    # tile chosen is really breakable and that there is room to work at it from
    # both sides, and what records -- loudly, in Kit.unproven -- that
    # tools/solver/sim.gd cannot break a tile, so the route goes round them.
    for x in (GLOW_A, GLOW_B):
        k.glow_wall(x, STAND_ROW, GLOW_H, thickness=GLOW_W, form="human")
    for x0, x1 in (CELL_A, CELL_B):
        for x in range(x0, x1 + 1):
            k._claim("stand", "the brood cell floor at col %d" % x,
                     x=x, y=STAND_ROW, form="human")
            k._claim("clear", "the brood cell at col %d is open to the roof" % x,
                     x=x, y=SHELF_STAND, tall=2)
    # And the step that gets her in without breaking anything: up onto the wall's
    # own top, 32 px, and down the other side. A shelter you could only reach by
    # destroying it would be no shelter at all.
    for x in (GLOW_A, GLOW_A + 1, GLOW_B, GLOW_B + 1):
        k._claim("stand", "the top of the luminous wall at col %d" % x,
                 x=x, y=SHELF_STAND, form="human")
    for x in (GLOW_A, GLOW_B):
        k._claim("step", "up onto the luminous wall at col %d" % x,
                 x1=x - 1, y1=STAND_ROW, x2=x, y2=SHELF_STAND, form="human")

    for x in (ARENA_X0, EXIT_COL, DROP_COL, 42, ARENA_X1):
        k._claim("stand", "arena floor at col %d" % x,
                 x=x, y=STAND_ROW, form="human")

    # Where the shaft puts her: directly under the fall, not in the middle of the
    # arena. The prover's frontier is manhattan distance (ADR 005's addendum), so
    # a landing tile east of the drop makes the only way down look like a way
    # away. Col 33 is also inside the span the Queen is clamped to, which
    # tests/integration/integration_tests.gd asserts of a boss level's traversal
    # tape, and it has no shelf over it.
    k.mark("cell_floor", DROP_COL, STAND_ROW, form="human")

    # ---------------------------------------------------------------- dressing
    # Roots through the galleries and fungus on the comb faces: background only,
    # so nothing here can change a single answer the collision code gives.
    for x in (4, 9, 14, 21, 28, 37, 43):
        g.trunk(x, 1, 3)
    for x in (30, 40):
        g.trunk(x, COMB_BOT + 1, 4)
    for x, y in ((6, 8), (15, 8), (20, 4), (27, 9), (36, 6), (45, 3)):
        g.rect(x, y, 2, 2, "r", "bg")
    for x in (27, 34, 42, 46):
        g.rect(x, ROOF_ROW + 1, 1, 2, "r", "bg")

    # ---------------------------------------------------------------- entities
    g.ent("player_spawn", 2, UPPER_STAND)
    g.ent("boss_brood_queen", BOSS_COL, STAND_ROW)
    g.ent("boss_exit", EXIT_COL, STAND_ROW)

    # One flyer in the chute -- the only place in this level tall enough for one
    # -- hung in its EAST column while the fall comes down the west one, so the
    # mound has something alive in it and the traversal tape is not asked to
    # thread a moving body in mid-air. Nothing at all is authored inside the
    # arena: an enemy in there is a damage source the gate's fairness sweep
    # would have to attribute to an attack, and this fight's adds are the
    # Queen's to call.
    g.ent("enemy_flyer", CHUTE_X1, 8, axis="y", range=32)
    # And two walkers in the lower gallery WEST of where the chute lands her, so
    # the mound is inhabited without the traversal tape having to fight its way
    # through a corridor two tiles tall. She lands around col 18 and goes east,
    # and tests/test_combat_data.gd pins a walker's chase below her run speed,
    # so a beetle behind her stays behind her.
    g.ent("enemy_walker", LOWER_X0 + 1, LOWER_STAND)
    g.ent("enemy_walker", LOWER_X0 + 2, LOWER_STAND)

    g.ent("heart", 8, UPPER_STAND)
    g.ent("heart", 22, LOWER_STAND)
    g.ent("heart", 29, LOWER_STAND)
    # One heart on each refuge shelf: the arena has no pickup you can take
    # without leaving the floor.
    g.ent("heart", WEST_SHELF[0], SHELF_STAND)
    g.ent("heart", EAST_SHELF[1], SHELF_STAND)
    # And one in each brood cell, which is the carrot for finding out that you
    # can get in there over the wall instead of through it.
    g.ent("gem", CELL_A[0], STAND_ROW)
    g.ent("gem", CELL_B[0], STAND_ROW)
    for (x, y) in [(4, UPPER_STAND), (11, UPPER_STAND), (16, UPPER_STAND),
                   (17, 9), (15, LOWER_STAND), (19, LOWER_STAND),
                   (23, LOWER_STAND), (26, LOWER_STAND), (31, LOWER_STAND),
                   (ARENA_X0, STAND_ROW), (30, STAND_ROW),
                   (40, STAND_ROW), (42, STAND_ROW),
                   (WEST_SHELF[1], SHELF_STAND), (EAST_SHELF[0], SHELF_STAND)]:
        g.ent("gem", x, y)

    # ---------------------------------------------------- the intended solution
    # Human throughout, and every hop short on purpose (ADR 005: "a hop that
    # needs a big budget is a hop that is too coarse").
    k.mark("gallery", 11, UPPER_STAND)
    k.mark("chute_foot", CHUTE_X0 + 1, LOWER_STAND)
    k.mark("gallery_b", EAST_X0 + 2, LOWER_STAND)
    k.mark("shaft_lip", EAST_X1, LOWER_STAND)
    g.route("spawn", "gallery", form="human")            # east along the gallery
    g.route("gallery", "chute_foot", form="human")        # off the end, 7 tiles down
    g.route("chute_foot", "gallery_b", form="human")      # east, A -> B on the ground
    g.route("gallery_b", "shaft_lip", form="human")       # east to the shaft's lip
    g.route("shaft_lip", "cell_floor", form="human")      # 11 tiles down, B -> D
    # And there the prover stops. `boss_exit` is placed by
    # Level.on_boss_defeated() and by nothing else, so this last hop is PARTIAL
    # by design and belongs to tools/bossgate.sh check 5 -- exactly as jungle_5's,
    # ruins_5's and heights_5's do.
    g.route("cell_floor", "boss_exit", form="human")
    return g, k


def main(argv):
    g, k = deeps_5()
    missing = DEEPS_CHARS.missing()
    if missing:
        print("  PALETTE  %d role(s) with no legend character: %s"
              % (len(missing), ", ".join("%s->%s" % m for m in missing)))
    for line in k.audit(strict_verbs=True):
        print(line)
    write(LEVEL_ID, g, LEVEL_NAME, music="boss")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
