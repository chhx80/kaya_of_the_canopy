#!/usr/bin/env python3
"""NEST_5 -- THE OBSIDIAN HEART. World 5's boss level, and the last level.

Self-contained on purpose, exactly like tools/worlds/ruins_5.py,
tools/worlds/heights_5.py and tools/worlds/deeps_5.py:
`python3 tools/worlds/nest_5.py` writes levels/nest_5.json without going near
tools/build_levels.py. To wire it into the shared builder, add

    from worlds.nest_5 import nest_5
    build("nest_5", nest_5(), "THE OBSIDIAN HEART", music="boss")

to tools/build_levels.py's `__main__` block and nothing else changes.

    python3 tools/worlds/nest_5.py             draw, self-check, write
    python3 tools/worlds/nest_5.py --check     draw and self-check only
    python3 tools/worlds/nest_5.py --configs   print the per-configuration report

The boss's sheet is NOT in here: it is `build_boss_obsidian_heart()` in
tools/art/sprites.py, called from tools/gen_art.py, for the reason deeps_5
states -- by M4 every sprite in the game has a generator in the shared module
and a new one authored off to the side would be the only exception.


THE PALETTE, AND WHY IT NAMES JUNGLE TILES
------------------------------------------
`world_kit.Palette.char()` resolves a tile NAME through the flat `legend` key of
data/level_legend.json, which ADR 002's amendment leaves as the *jungle* view
(tools/reachability.py and tools/build_hub.py read it directly). A palette that
names `obsidian` finds no character, falls through to `UNDERSTUDY`, and emits
whatever character the understudy owns -- `stone` -> 's', which the nest tileset
binds to nest_plate, not obsidian. The shapes would be right and the nest would
be built out of the wrong stone.

So this palette names, for each role, the jungle tile that OWNS the character
the nest tileset binds to the art this level wants. It is ADR 002's role table
read in the other direction, and it is safe for the reason ADR 002 pins with a
test: the role mapping preserves gameplay flags across worlds, so grass_top
(solid) and obsidian (solid) are the same tile to every checker that reads
flags, and `"tileset": "nest"` in the level JSON is what decides the art.

The four SWITCH BLOCKS are named DIRECTLY, because they are *shared* characters
-- 'A' switch_block_a_on, 'a' switch_block_a_off, 'B' switch_block_b_on,
'b' switch_block_b_off mean the same tile in every world. That matters more here
than anywhere: the switch blocks are this fight's whole idea.

`Palette.missing()` and `Palette.substituted` both stay EMPTY, which is why
`audit(strict_verbs=True)` can be asked for.


THE SHAPE OF THE LEVEL
----------------------
Four screens, and the approach is a DESCENT that spends the frog and cannot be
walked back up:

    A  the outer flues, cols 0-24 rows 0-14   B  the inner flue, cols 25-49 rows 0-14
    C  solid obsidian,  rows 15-29            D  THE HEARTHOLD -- the arena, rows 15-29

    spawn -> east along the upper flue
          -> off its end into the chute, six tiles down to the lower flue
          -> east across the A->B seam ON THE GROUND
          -> pad_frog at col 27, because what comes next is a THREE-TILE step
             and `LIMITS["human"]["rise"]` is 2: the ledge at row 9 is the
             frog's and nothing else's
          -> east along that ledge to its end at col 35
          -> off the end, down the inner flue, seventeen tiles, through the
             hearthold's roof and onto the arena floor and the pad that makes
             her human again.

The drop is one-way by construction: the hearthold is roofed at row 15 except
the two columns of that flue, and nothing in the arena is within seventeen
tiles of it. Screen C is left as undisturbed obsidian, which is also what keeps
the prover's frontier small (`Kit.fill_solid`'s docstring): a failed hop
exhausts itself inside the rock instead of wandering open space.

**There is no switch block and no lever anywhere in the approach.** See THE
ARENA HAS NO LEVER. The world's verb is taught by nest_1..nest_4; this level is
where it is turned against you.


THE FIGHT
---------
docs/plan-20-levels.md: "Final. Switch-blocks reconfigure the arena between
phases, each phase demanding a different form from pads that move with the
blocks."

**Switch blocks reconfigure the arena between phases.** Literally, and with the
machinery the whole world runs on: src/enemies/obsidian_heart.gd calls
`TileWorld.set_switch`, which is the same call src/world/triggers/switch_trigger.gd
makes. Each phase names a configuration:

    SEALED     group 1 ON,  group 2 OFF     the frog's bay is open
    INVERTED   group 1 OFF, group 2 ON      the bird's bay is open
    MOLTEN     group 1 ON,  group 2 ON      the human's bay is open

SEALED's configuration is `TileWorld`'s own seeded default -- and
tools/solver/sim.gd seeds the same -- so it is the arena exactly as
levels/nest_5.json draws it. That is what lets tools/prove.sh, the traversal
tape, tools/reachability.py and tests/test_level_validity.gd all see the room
the fight opens in rather than a room that only exists at runtime.

Nothing is ever restored. Unlike THE TIDE MAW's flood and THE STORMCREST's gale
the configuration IS the mechanic, so the arena Kaya walks out of is the one
MOLTEN left behind. That costs exactly one obligation and this level meets it in
`check_configs()`: `boss_exit` and the way to it stand in all FOUR
configurations, not just the seeded one.

**Pads that move with the blocks.** `TransformPad` is a node at a fixed
position, so what moves is not the pad but whether you can get to it. Each of
the three bays is TWO TIERS:

    the STEP    a permanent one-way ledge at row 25, stood on at row 24, 32 px
                over the arena floor -- reachable in EVERY configuration
    the PLUG    switch blocks at rows 21-22, filling the columns the climb
                crosses
    the SHELF   a permanent solid at row 23, stood on at row 22, 32 px over the
                step -- with the pad and a gem on it

so the climb from the step to the shelf passes through rows 21-22, which is
exactly what the plug fills. The plug is the gate; the pad is behind it.

    FROG bay   step 28-29   shelf 30-31   plug 'B' in cols 28-29
                                          open only while group 2 is OFF
    BIRD bay   step 42-43   shelf 40-41   plug 'A' in cols 42-43
                                          open only while group 1 is OFF
    HUMAN bay  step 44      shelf 47-48   plug 'b' in col 45, 'a' in col 46
                                          open only while BOTH groups are ON

Against the three configurations above that is exactly one bay per phase, which
is the plan's "each phase demanding a different form" made out of tiles, and
`check_configs()` fails the build if it ever stops being true.

FIVE things about that shape are measurements and not taste, and three of them
were bought with a defect that shipped and was caught:

  * **The plug is at rows 21-22 and NEVER at rows 23-24.** A pad inside a plug
    has zero tiles of headroom in the seeded configuration, and
    `tests/test_level_validity.gd::test_everything_the_player_must_reach_has_headroom`
    fails on exactly that -- measured on the first cut of this level, which put
    the pads at row 24 inside a plug running rows 16-24. Two tiers is what fixes
    it: the pads sit on permanent ground at row 22 with seven clear rows over
    them in every configuration, and the plug gates the *route* instead of the
    *tile*.
  * **No plug column may have anything to stand on beneath it.** The second cut
    gated the human bay by STRIPING one column -- 'b' on even rows, 'a' on odd
    -- because no single switch block is solid in both SEALED and INVERTED and
    open in MOLTEN. A striped column is standable at the seam in each half-open
    state, with one tile of headroom, and
    `test_no_standable_pockets_are_too_short_to_stand_in` found it at (46,17),
    (46,19), (46,21) and (46,23). The general rule underneath that, which
    `_self_checks` now enforces, is the one that matters: a switch tile with a
    floor under it is a tile a body can stand INSIDE, and a body standing inside
    a switch tile is a body the next flip closes on. The human bay's two gates
    are therefore in two columns with air all the way down to the arena floor.
  * **And the human bay's gates are not in its step at all, because of COYOTE
    TIME.** See the BAYS table below for the trajectory that measured it.
  * **The step columns carry a permanent solid at rows 16-19 and NOTHING at row
    20.** Row 20 is where the shed is thrown from; see below.
  * **Every switch tile in the level is at rows 21-22, in three pairs of
    columns, and all six of those columns are outside the span the Heart is
    clamped to.** The second half is why no configuration can put a solid tile
    inside the Heart or leave it stuck in a closing bay -- deeps_5 wrote the
    same constraint for its luminous walls. The first half is stronger than it
    looks and it is this level's answer to "a flip must never crush the player
    where she stands": a body STANDING anywhere in this arena occupies rows
    21-22 (a shelf), 23-24 (a step) or 25-26 (the floor), and of those only the
    shelf overlaps rows 21-22 -- in the SHELF columns, which carry no switch
    tile. So **no flip can ever close on a body that is standing still.**
    `check_configs()` proves that tile by tile rather than asserting it, and
    tests/integration/boss_obsidian_heart_tests.gd proves it again in the
    running game. What is left is a body that is IN THE AIR inside a plug
    column at the moment of the flip, which is a real case, and it is the one
    src/enemies/obsidian_heart.gd telegraphs and then makes room for.
  * **The one-way ledges and the shelf floors are ORDINARY tiles, not switch
    blocks.** A switch block is SOLID, and tools/reachability.py resolves any
    tile carrying a switch group as *never* solid -- so a route that stands on
    one is a route the project's own validator cannot credit (the M5 contract's
    rule 4). Nothing in this level stands on a switch tile in any
    configuration, and `_self_checks` fails the build if that changes.

**"Each phase demanding a different form" is an OFFER here, not a requirement,
and the Boss Gate is what makes that the honest answer rather than the lazy
one.** Only the human throws the blade -- `data/forms/frog.json` and
`data/forms/bird.json` are both `can_attack: false`, the wall ruins_5 hit with
the fish and heights_5 hit with the bird. So a phase that REQUIRED the frog
would be a phase in which Kaya cannot deal one point of damage, and a fight
whose second phase cannot be reached is not a fight. Worse, ADR 005's check 3
sweeps a HUMAN across every standable tile and demands that every attack miss
one of them: a dodge only a frog could reach would fail that check, correctly.

So the arena is built the other way round:

  * every phase's dodges are reachable, standable and fightable AS THE HUMAN --
    the three STEPS are permanent one-ways no configuration touches, and the two
    floor tiles under the comb are the shed's only cover;
  * the BAYS are the phase's other ground: its animal, its gem, and a shelf the
    Heart's body can never reach. Taking the animal costs you the blade until
    you come back down to the floor pad at col 36, which is reachable in every
    configuration -- `check_configs()` and `_strand_graph()` both prove it, and
    that is what stops an animal pad from ever being a softlock.

That is the Stormcrest precedent read forwards. It is also why there are two
`pad_human`s in the arena and the second one is not redundant: MOLTEN's bore is
the fastest in the fight, and a player who spent INVERTED as the bird would
otherwise have to cross the whole floor under it to get her weapon back. The
MOLTEN bay hands it to her where she is standing.


THE ARENA HAS NO LEVER
----------------------
`switch_a`/`switch_b` entities and this boss write the same two booleans. A
lever in the arena would let the player undo the configuration the phase's
geometry is made of, and the Heart would take it back at the next health
threshold -- a fight in which one of the player's verbs sometimes does nothing
and sometimes deletes the ground under her feet. The M5 contract also caps a
level at one lever per group; spending that budget on a fight the boss is
already driving buys nothing. So nest_5 authors no switch entity anywhere and
the Heart owns the state.

What that costs is precise. `world_kit.reconfig_check()` has two arms and its
second -- "in every configuration reachable from here, is at least one lever
still reachable" -- is the ROOT HOLLOW softlock, and it has nothing to check in
a level with no levers. `check_configs()` and `_strand_graph()` replace it with
the claim this level actually needs, and both evaluate all FOUR configurations
rather than the three the fight uses.


WHY THE ARENA IS SHAPED LIKE THIS
---------------------------------
The rule is THE TIDE MAW's, stated in tools/worlds/ruins_5.py and applied to the
Warden, the Stormcrest and the Queen since: every standable tile is the floor or
a refuge above it, every attack misses somewhere a player can actually stand and
fight from, and nothing is safe from everything.

Twenty-three interior columns, and every one of them has a job:

    26-27  open floor. The west end, and where the fight starts: the Boss Gate
           stages Kaya on the leftmost tile of the lowest standable row, which
           is (26,26), and walks her out to `boss_exit` at (27,26) for check 5.
           From (26,26) her chest is at x 424 and the blade's 118 px carries it
           to 542, against a Heart whose left edge never passes 512 -- so the
           staging tile is a place she can fight from, which is what the gate's
           `_can_fight_from` asks of it and what deeps_5 had to engineer for.
    28-29  the FROG STEP, and the two columns of its plug.
    30-31  the FROG SHELF.
    32-33  open floor.
    34-35  under THE COMB: solid obsidian hanging from the roof, rows 16-20.
    36-37  open floor, with the inner flue coming through the roof and landing
           her on (36,26) and the `pad_human` standing there -- inside the span
           the Heart is clamped to, which
           tests/integration/integration_tests.gd asserts of a boss level's
           traversal tape.
    38-39  open floor.
    40-41  the BIRD SHELF.       42-43  the BIRD STEP and its plug.
    44     the HUMAN STEP -- one column, and the east end of a one-way ledge
           that runs unbroken from col 42, because the bird's step and this one
           are the same slab of nest_ledge.
    45-46  the HUMAN BAY'S TWO GATES, in series: 'b' at col 45 is solid while
           group 2 is OFF and 'a' at col 46 while group 1 is OFF, so the pair is
           open only in MOLTEN. Neither column has a floor under it at any
           height, which is what keeps them un-standable and therefore
           crush-proof.
    47-48  the HUMAN SHELF. From (48,26) the blade reaches left to 658 against a
           Heart whose right edge reaches 640.

  * **The bays are ordered SHELF-STEP-GATES-SHELF at the east end, and that is
    not symmetry, it is a leak that was closed.** A shelf next to the next bay's
    climb lets you go up one bay's plug and walk along rows 21-22 into the other
    bay's shelf -- so MOLTEN would have handed you the bird as well. With the
    bird's shelf at the WEST end of the run and the human's at the EAST, every
    climb is walled by the other bay's gate, which is solid in exactly the
    configurations where that bay is shut. `t_each_phase_opens_exactly_one_bay`
    is what proves it, in the running game, for the human AND for the frog.
  * **The comb is the shed's dodge and the steps are the bore's, and the two
    sets do not overlap.** That is ADR 005's check 3 in one sentence and the
    shape heights_5 proved and deeps_5 repeated: a ground attack you dodge by
    being 32 px up, an overhead attack you dodge by standing under rock, and
    nowhere that is both. The bore runs the floor 4 px up and cannot climb; the
    shed is thrown from row 20, so a shard over the comb is born inside solid
    obsidian and `Projectile` kills it on the frame it is born.
  * **The comb stops at row 20 and the shed falls from row 20.** Both numbers
    are measured. Kaya jumping off the floor tops out with her head at y 364,
    which is row 22, so a comb hanging to row 20 leaves the full 46 px of jump
    under it; and the Heart's own leap (-250 px/s against gravity 720, 43 px)
    tops out at y 343, also row 21, so it never brains itself on its own
    ceiling. Row 20 for the shed is the ONLY row that works: every step column
    is deliberately empty at row 20 and solid at rows 16-19, so a shard over a
    step falls in EVERY configuration. Throwing it from row 16 instead -- the
    first cut -- meant a shard over a shut bay died at birth, which made the
    bird and human steps safe from the bore, safe from the shed, outside the
    Heart's reach and still in blade range: a stalemate to camp in, and the one
    thing the gate's check 3 structurally cannot see.
  * **The shed covers every refuge column and no comb column**, six of the
    twelve per volley, alternating. `_self_checks` compares
    data/enemies/obsidian_heart.json's `shed.cols` against the geometry drawn
    here and fails the build if a refuge stops being covered or the comb starts
    being.
  * **The floor is unbroken from col 26 to col 48 in all four configurations,**
    because the lowest switch tile in the level is at row 22 and a body standing
    on the floor occupies rows 25-26. ruins_5 records what the alternative cost:
    raising refuges out of the floor as solid blocks cornered Kaya against her
    own standoff and the recorder never got the Maw below 12 of 18.
  * **No stand row is a multiple of 15.** `CameraController` picks its screen
    from the body's CENTRE and freezes the sim for 0.12 s while it flips, so a
    22 px body on a floor whose cap row is a multiple of 15 has its feet on the
    seam and its centre on the screen above -- the defect ruins_4 shipped. The
    stand rows here are 5, 12, 9, 26, 24 and 22, and `_self_checks` fails the
    build on any claim or entity that stands on a cap row divisible by 15.

The level is authored in the seeded configuration, which is also phase 1, so
tools/prove.sh and the traversal tape both see exactly the geometry in
levels/nest_5.json -- and so does the fight's first phase.
"""
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                                  # noqa: E402
from world_kit import (Kit, Palette, Probe, WorldKitError,          # noqa: E402
                       LIMITS, path_clear)

LEVEL_ID = "nest_5"
LEVEL_NAME = "THE OBSIDIAN HEART"
W, H = 50, 30

## Role -> the jungle tile that owns the character the nest tileset binds to the
## art this level wants. See the module docstring. The four switch blocks are
## named directly because they are shared characters in every world.
NEST_CHARS = Palette("obsidian_nest", {
    "bg":            "bg_leaves",           # 'L' -> 282 nest_wall
    "solid":         "grass_top",           # '#' -> 280 obsidian
    "solid_alt":     "stone_mossy",         # 'S' -> 281 obsidian_hot
    "packed":        "dirt",                # 'd' -> 283 nest_block
    "block":         "stone",               # 's' -> 290 nest_plate
    "oneway":        "wood_platform",       # '=' -> 286 nest_ledge
    "ladder":        "vine",                # '|' -> 288 nest_chain
    "hazard":        "spikes",              # '^' -> 287 nest_shard
    "breakable":     "crate",               # 'c' -> 291 nest_crust
    "decor":         "tree_trunk",          # 'T' -> 285 nest_flue
    "void":          "bg_dark",             # 'X' -> 284 nest_void
    "water":         "water",               # 'w'  shared
    "water_top":     "water_top",           # '~'  shared
    "switch_a_on":   "switch_block_a_on",   # 'A'  shared, 11
    "switch_a_off":  "switch_block_a_off",  # 'a'  shared, 26
    "switch_b_on":   "switch_block_b_on",   # 'B'  shared, 12
    "switch_b_off":  "switch_block_b_off",  # 'b'  shared, 27
})

# ------------------------------------------------------------------ geometry
# Named once, because data/enemies/obsidian_heart.json repeats several of them
# and an arena whose boss and whose author disagree about where the floor is has
# no chance at all. `_self_checks` compares the two files.

# ---- screen A, the outer flues
UPPER_STAND = 5                      # feet row of the flue she spawns in
UPPER_CAP = UPPER_STAND + 1          # 6
UPPER_X0, UPPER_X1 = 1, 16
CHUTE_X0, CHUTE_X1 = 17, 19          # three columns of open shaft
LOWER_STAND = 12
LOWER_CAP = LOWER_STAND + 1          # 13
LOWER_X0 = 13

# ---- screen B, the frog's ledge and the inner flue
EAST_X1 = 31                         # the lower flue ends here
PAD_FROG_COL = 27
LEDGE_STAND = 9                      # a THREE-tile step: the frog's, not hers
LEDGE_CAP = LEDGE_STAND + 1          # 10
LEDGE_X0, LEDGE_X1 = 32, 35
ALCOVE_X0, ALCOVE_X1 = 29, 31        # headroom carved for the frog's jump
FLUE_X0, FLUE_X1 = 36, 37

# ---- screen D, THE HEARTHOLD
ARENA_X0, ARENA_X1 = 26, 48
ROOF_ROW = 15
FLOOR_ROW = 27                       # the one unbroken floor cap
STAND_ROW = FLOOR_ROW - 1            # 26
STEP_ROW = 25                        # the bays' permanent one-way ledges
STEP_STAND = STEP_ROW - 1            # 24 -- 32 px over the arena floor
SHELF_ROW = 23                       # the bays' permanent solid upper tier
SHELF_STAND = SHELF_ROW - 1          # 22 -- 32 px over the step
PLUG_TOP, PLUG_BOT = 21, 22          # EVERY switch tile in the level is here
BAY_CAP_TOP, BAY_CAP_BOT = 16, 20    # permanent roof over the step columns
SHED_ROW = 16                        # the shed falls from the arena's top row
COMB_TOP, COMB_BOT = 16, 20
COMB = (34, 35)
DROP_COL = 36                        # where the inner flue lands her
EXIT_COL = 27
BOSS_COL = 35

## THE THREE BAYS, column by column.
##
## `step`  the columns carrying the permanent one-way ledge at row 25
## `plug`  col -> the switch-block role filling rows 21-22 of that column
## `cap`   the columns carrying the permanent roof at rows 16-20
## `shelf` the columns carrying the permanent solid at row 23
## `climb` the two columns the climb runs between, as (from step, to shelf)
##
## EVERY PLUG COLUMN IS UNIFORM over rows 21-22 -- one role, both rows -- and
## that is the rule that makes this arena legal. The first cut striped the human
## bay's plug by ROW, which is the only way to gate one column on two groups,
## and it put a one-tile slot at (45,21) in SEALED: floor under it, cap over it,
## the shelf beside it to walk in from.
## `tests/test_level_validity.gd::test_no_standable_pockets_are_too_short_to_stand_in`
## found it, and it is right to -- a 16 px gap next to a ledge reads as a
## passage and behaves as a wall. A uniform column cannot do that in either
## state: solid, there is nowhere to stand; open, the row below is open too, so
## nothing has a floor.
##
## The human bay is gated on BOTH groups by putting its two roles in DIFFERENT
## COLUMNS IN SERIES along the climb instead: 'b' at cols 44-45 is solid while
## group 2 is OFF, 'a' at col 46 is solid while group 1 is OFF, and the climb has
## to pass through both. Open only when both groups are ON, which is MOLTEN and
## nothing else.
##
## AND THE HUMAN BAY'S GATES ARE NOT IN ITS STEP AT ALL, WHICH IS COYOTE TIME.
##
## That is a rule the RUNNING GAME taught, and no amount of geometry here would
## have. The first two cuts put the gates in the step's own columns, on the
## reasoning that a body jumping from a plugged column is stopped by that
## column's plug. `tests/integration/boss_obsidian_heart_tests.gd` put the real
## player on the real ledge and found the human bay open in SEALED anyway; the
## trajectory trace says why, in one number:
##
##     f0   x= 723.25 y= 373.67 vy= -260.0   cols=45..45
##
## `data/forms/human.json` has `coyote_time` 0.09 -- five and a bit frames of
## still-jumpable after the ground runs out. With twelve frames of run-up she
## leaves the step's east end at 108 px/s, is 9-18 px past it before the coyote
## window shuts, and jumps from the NEXT COLUMN ALONG. Whatever is plugged in the
## column she started in never enters the question.
##
## So the human bay's step is ONE column, col 44, and both of its gates stand in
## the two columns east of it -- which is more than coyote time can carry her --
## and NEITHER gate column has a floor under it. That last part is what keeps the
## crush guarantee intact: a switch tile with something solid beneath it makes a
## standable tile inside itself in whichever configuration opens it, and a body
## standing there would be a body a flip can close on. Cols 45 and 46 have air
## from row 23 all the way down to the arena floor, so there is nothing to stand
## on inside them in any configuration.
##
## The frog's and the bird's gates ARE in their step columns and that is safe for
## a reason the human's is not: their shelves are immediately adjacent to their
## steps, so there is no column to coyote into -- the shelf's own solid face is
## what she runs into instead.
##
## `check_configs()` still checks all of this and it is still only a FILTER: its
## `path_clear` models one arc and knows nothing about coyote time.
## `t_each_phase_opens_exactly_one_bay` in the suite is the proof.
BAYS = [
    dict(name="frog", step=(28, 29), plug={28: "switch_b_on", 29: "switch_b_on"},
         cap=(28, 29), shelf=(30, 31), climb=(29, 30), pad="pad_frog"),
    dict(name="bird", step=(42, 43), plug={42: "switch_a_on", 43: "switch_a_on"},
         cap=(42, 43), shelf=(40, 41), climb=(42, 41), pad="pad_bird"),
    dict(name="human", step=(44, 44),
         plug={45: "switch_b_off", 46: "switch_a_off"},
         cap=(44, 46), shelf=(47, 48), climb=(44, 47), pad="pad_human"),
]

## The three configurations the Heart forces, in phase order, and the fourth it
## never uses. Group 1 ON / group 2 OFF is `TileWorld`'s seeded default and
## tools/solver/sim.gd seeds the same, which is why SEALED is first.
PHASE_CONFIGS = [
    ("SEALED", (True, False)),
    ("INVERTED", (False, True)),
    ("MOLTEN", (True, True)),
]
UNUSED_CONFIG = ("(unused)", (False, False))
ALL_CONFIGS = PHASE_CONFIGS + [UNUSED_CONFIG]
SEEDED = PHASE_CONFIGS[0][1]

## What data/enemies/obsidian_heart.json must agree with. `_self_checks` reads
## the JSON and compares; a number that lives in two files and is checked in
## neither is how an arena and its boss end up disagreeing about the floor.
BOSS_JSON = "data/enemies/obsidian_heart.json"


def nest_5():
    """Draw the level. Returns (Grid, Kit) so main() can audit before writing.

    Drawn with `Grid` and the ROLE CHARACTERS of ADR 002's amendment -- '#' the
    world's ground cap, 'd' the fill under it, 's' its second solid, '=' its
    one-way, 'A'/'a'/'B'/'b' the shared switch blocks -- because the grid's
    `tileset="nest"` is what turns those into obsidian, nest block, plate, ledge
    and glass lattice.

    `Kit.audit()` is deliberately CONFIGURATION-BLIND: `world_kit.Probe` with
    `switches=None` treats every switch block as passable, which is what
    tools/reachability.py does and is the right answer when you do not know the
    state. So the claims below are the ones that hold in EVERY configuration,
    and the per-configuration questions belong to `check_configs()` and
    `_strand_graph()`, which are a different kind of question: not "is this tile
    standable" but "is this room still escapable".
    """
    g = Grid(W, H, tileset="nest")
    k = Kit(g, NEST_CHARS, form="human")

    # ---------------------------------------------------------------- the nest
    # Solid obsidian everywhere, then carved. `Kit.fill_solid`'s own docstring is
    # the reason: a flue cut out of rock has a tiny reachable state space, so a
    # failed prover hop exhausts its frontier instead of burning its budget.
    k.fill_bg("bg")
    g.rect(0, 0, W, H, "d")
    k.shell(1, "block")

    # ================================================================
    # SCREEN A -- the outer flues
    # ================================================================
    k.corridor(UPPER_X0, UPPER_STAND, CHUTE_X1 - UPPER_X0 + 1)
    g.rect(UPPER_X0, UPPER_CAP, UPPER_X1 - UPPER_X0 + 1, 1, "#")
    for x in (UPPER_X0, 6, 11, UPPER_X1):
        k._claim("stand", "upper flue at col %d" % x,
                 x=x, y=UPPER_STAND, form="human")
    # The chute: six tiles, one-way by construction, no locked door needed.
    g.rect(CHUTE_X0, UPPER_CAP, CHUTE_X1 - CHUTE_X0 + 1,
           LOWER_CAP - UPPER_CAP, ".")
    for x in range(CHUTE_X0, CHUTE_X1 + 1):
        k._claim("clear", "the chute at col %d" % x,
                 x=x, y=UPPER_STAND, tall=2)
    g.rect(CHUTE_X0, 1, CHUTE_X1 - CHUTE_X0 + 1, UPPER_STAND - 1, "X", "bg")

    # The lower flue, floored right across the A->B seam so the screen flip
    # happens with her feet on the ground: a route that crosses a seam airborne
    # passes the gate and plays badly, because the flip freezes the simulation
    # for the title card and she falls through the pause.
    k.corridor(LOWER_X0, LOWER_STAND, EAST_X1 - LOWER_X0 + 1)
    g.rect(LOWER_X0, LOWER_CAP, EAST_X1 - LOWER_X0 + 1, 1, "#")
    for x in (LOWER_X0, 18, 23, 25, PAD_FROG_COL, EAST_X1):
        k._claim("stand", "lower flue at col %d" % x,
                 x=x, y=LOWER_STAND, form="human")

    # ================================================================
    # SCREEN B -- the frog's ledge and the inner flue
    # ================================================================
    # Three tiles from row 12 up to row 9: inside `LIMITS["frog"]["rise"]` (3)
    # and outside `LIMITS["human"]["rise"]` (2). That is the whole reason
    # `pad_frog` is on this level -- not decoration, a wall she cannot climb as
    # herself. The alcove is the headroom the jump needs; without it the frog
    # rises into the roof of a two-tile corridor and the step is impossible
    # however big her jump is, which is defect 6 in one sentence.
    g.rect(ALCOVE_X0, LEDGE_STAND - 1, ALCOVE_X1 - ALCOVE_X0 + 1,
           LOWER_STAND - LEDGE_STAND + 2, ".")
    k.corridor(LEDGE_X0, LEDGE_STAND, LEDGE_X1 - LEDGE_X0 + 1)
    g.rect(LEDGE_X0, LEDGE_CAP, LEDGE_X1 - LEDGE_X0 + 1, 1, "#")
    for x in range(ALCOVE_X0, ALCOVE_X1 + 1):
        k._claim("clear", "the frog's headroom at col %d" % x,
                 x=x, y=LEDGE_STAND, tall=2)
    k._claim("step", "the three-tile step onto the frog's ledge",
             x1=EAST_X1, y1=LOWER_STAND, x2=LEDGE_X0, y2=LEDGE_STAND,
             form="frog")
    for x in range(LEDGE_X0, LEDGE_X1 + 1):
        k._claim("stand", "the frog's ledge at col %d" % x,
                 x=x, y=LEDGE_STAND, form="frog")

    # The inner flue: two columns with no floor at the ledge's east end.
    g.rect(FLUE_X0, LEDGE_STAND - 1, FLUE_X1 - FLUE_X0 + 1,
           ROOF_ROW - LEDGE_STAND + 2, ".")
    for x in range(FLUE_X0, FLUE_X1 + 1):
        k._claim("clear", "the inner flue at col %d" % x,
                 x=x, y=LEDGE_STAND, tall=2)
        k._claim("clear", "the inner flue through the roof at col %d" % x,
                 x=x, y=ROOF_ROW, tall=2)
    g.rect(FLUE_X0, 1, FLUE_X1 - FLUE_X0 + 1, LEDGE_STAND - 2, "X", "bg")
    # A wall east of it, so the ledge ends AT the flue rather than offering a
    # one-tile hop over it.
    g.rect(FLUE_X1 + 1, 1, 1, ROOF_ROW - 1, "s")

    # ================================================================
    # SCREEN D -- THE HEARTHOLD
    # ================================================================
    g.rect(ARENA_X0 - 1, ROOF_ROW, 1, H - 1 - ROOF_ROW, "s")   # sealed west
    g.rect(ARENA_X0, ROOF_ROW + 1, ARENA_X1 - ARENA_X0 + 1,
           FLOOR_ROW - ROOF_ROW - 1, ".")
    g.rect(ARENA_X0, ROOF_ROW, ARENA_X1 - ARENA_X0 + 1, 1, "s")
    g.rect(FLUE_X0, ROOF_ROW, FLUE_X1 - FLUE_X0 + 1, 1, ".")   # the flue's mouth
    g.rect(ARENA_X0, ROOF_ROW + 1, ARENA_X1 - ARENA_X0 + 1,
           FLOOR_ROW - ROOF_ROW - 1, "X", "bg")

    # ONE unbroken floor, wall to wall, with hot obsidian bleached in under the
    # comb so the fight reads: the cover is the one patch of the floor that is
    # already glowing.
    g.ground(ARENA_X0, FLOOR_ROW, ARENA_X1 - ARENA_X0 + 1, depth=3)
    g.hline(COMB[0], FLOOR_ROW, COMB[1] - COMB[0] + 1, "S")

    # THE COMB. Solid obsidian from the roof down to row 20, which is what makes
    # the two floor tiles under it the shed's dodge window: a shard thrown from
    # row 20 over the comb is born inside solid rock. Plate, like the roof, and
    # not the ground cap: '#' draws a lit top edge and the only face of a comb
    # the player ever sees is its underside.
    g.rect(COMB[0], COMB_TOP, COMB[1] - COMB[0] + 1,
           COMB_BOT - COMB_TOP + 1, "s")
    for x in range(COMB[0], COMB[1] + 1):
        k._claim("stand", "the floor under the comb at col %d" % x,
                 x=x, y=STAND_ROW, form="human")

    # ---------------------------------------------------------- THE THREE BAYS
    for bay in BAYS:
        _bay(k, bay)

    for x in (ARENA_X0, EXIT_COL, 32, DROP_COL, 38, ARENA_X1):
        k._claim("stand", "arena floor at col %d" % x,
                 x=x, y=STAND_ROW, form="human")

    # Where the flue puts her: directly under the fall, not in the middle of the
    # arena. The prover's frontier is manhattan distance (ADR 005's addendum), so
    # a landing tile east of the drop makes the only way down look like a way
    # away. Col 36 is also inside the span the Heart is clamped to, which
    # tests/integration/integration_tests.gd asserts of a boss level's traversal
    # tape, and it has no bay over it.
    k.mark("hearthold", DROP_COL, STAND_ROW, form="frog")

    # ---------------------------------------------------------------- dressing
    # Flues and veins: background only, so nothing here can change a single
    # answer the collision code gives.
    for x in (4, 9, 14, 22):
        g.trunk(x, 1, 3)
    for x, y in ((6, 8), (15, 8), (20, 3), (26, 10), (33, 5), (45, 4)):
        g.rect(x, y, 2, 2, "r", "bg")
    for x in (27, 33, 38, 48):
        g.rect(x, ROOF_ROW + 1, 1, 2, "r", "bg")

    # ---------------------------------------------------------------- entities
    g.ent("player_spawn", 2, UPPER_STAND)
    g.ent("boss_obsidian_heart", BOSS_COL, STAND_ROW)
    g.ent("boss_exit", EXIT_COL, STAND_ROW)

    # The approach's one pad: the step at col 32 is three tiles and Kaya climbs
    # two.
    g.ent("pad_frog", PAD_FROG_COL, LOWER_STAND)
    # The arena's floor pad, where the flue lands her. She arrives as the frog
    # and this is what puts the blade back in her hand -- heights_5's device for
    # heights_5's reason. It stands on the open floor at row 26, which is
    # configuration-independent ground, and `check_configs()` proves it
    # reachable in all four configurations: that is what stops an animal pad
    # from ever being a softlock.
    g.ent("pad_human", DROP_COL, STAND_ROW)
    for bay in BAYS:
        g.ent(bay["pad"], bay["shelf"][0], SHELF_STAND)
        g.ent("gem", bay["shelf"][1], SHELF_STAND)

    # Two bodies in the lower flue WEST of where the chute lands her, so the nest
    # is inhabited without the traversal tape having to fight its way through a
    # corridor two tiles tall. She lands around col 18 and goes east, and
    # tests/test_combat_data.gd pins a walker's chase below her run speed.
    # Nothing at all is authored inside the arena: an enemy in there is a damage
    # source the gate's fairness sweep would have to attribute to an attack, and
    # this fight's adds are the Heart's to call.
    g.ent("enemy_walker", LOWER_X0 + 1, LOWER_STAND)
    g.ent("enemy_charger", LOWER_X0 + 3, LOWER_STAND)
    g.ent("enemy_flyer", CHUTE_X1, 8, axis="y", range=32)

    g.ent("heart", 8, UPPER_STAND)
    g.ent("heart", 22, LOWER_STAND)
    g.ent("heart", LEDGE_X1, LEDGE_STAND)
    # One heart on a step at each end of the arena: the two refuges every
    # configuration offers, so there is no pickup in here you can take without
    # leaving the floor.
    g.ent("heart", BAYS[0]["step"][0], STEP_STAND)
    g.ent("heart", BAYS[1]["step"][1], STEP_STAND)
    for (x, y) in [(4, UPPER_STAND), (11, UPPER_STAND), (16, UPPER_STAND),
                   (18, 9), (15, LOWER_STAND), (19, LOWER_STAND),
                   (24, LOWER_STAND), (26, LOWER_STAND), (30, LOWER_STAND),
                   (LEDGE_X0, LEDGE_STAND), (LEDGE_X0 + 2, LEDGE_STAND),
                   (ARENA_X0, STAND_ROW), (33, STAND_ROW),
                   (38, STAND_ROW), (ARENA_X1, STAND_ROW),
                   (BAYS[0]["step"][1], STEP_STAND),
                   (BAYS[2]["step"][0], STEP_STAND)]:
        g.ent("gem", x, y)

    # ---------------------------------------------------- the intended solution
    # Human to the pad, frog from there on, and every hop short on purpose (ADR
    # 005: "a hop that needs a big budget is a hop that is too coarse").
    k.mark("flue_head", 11, UPPER_STAND)
    k.mark("chute_foot", CHUTE_X0 + 1, LOWER_STAND)
    # The approach's frog pad gets a MARK rather than being named as an entity
    # waypoint: `Grid._waypoints()` makes every entity type a waypoint, and this
    # level has two `pad_frog`s and two `pad_human`s -- one on the route and one
    # in a bay -- so `pad_frog` is ambiguous and `_check_route` rightly refuses
    # it. The mark sits on the same tile and the pad still fires the way it does
    # in play: tools/solver/sim.gd runs pads by OVERLAP with a cooldown, not by
    # waypoint name, so the hop that ends on this tile is the hop that ends as
    # the frog.
    k.mark("flue_pad", PAD_FROG_COL, LOWER_STAND)
    k.mark("step_foot", EAST_X1, LOWER_STAND, form="frog")
    k.mark("ledge_lip", LEDGE_X1, LEDGE_STAND, form="frog")
    g.route("spawn", "flue_head", form="human")        # east along the flue
    g.route("flue_head", "chute_foot", form="human")   # off the end, 6 down
    g.route("chute_foot", "flue_pad", form="human")    # east, A -> B on the ground
    g.route("flue_pad", "step_foot", form="frog")      # east to the foot of the step
    g.route("step_foot", "ledge_lip", form="frog")     # THREE tiles up, and east
    g.route("ledge_lip", "hearthold", form="frog")     # 17 tiles down, B -> D
    # And there the prover stops. `boss_exit` is placed by
    # Level.on_boss_defeated() and by nothing else, so this last hop is PARTIAL
    # by design and belongs to tools/bossgate.sh check 5 -- exactly as
    # jungle_5's, ruins_5's, heights_5's and deeps_5's do.
    g.route("hearthold", "boss_exit", form="human")
    return g, k


def _bay(k, bay):
    """One two-tier bay: a permanent step, switch-block plugs, a shelf.

    The plugs occupy rows 21-22 and nothing else in the level carries a switch
    tile, which is the whole of this level's crush-safety argument -- see the
    docstring. Nothing about a plug is claimed, because whether a plug tile is
    solid is not a property of the grid, it is a property of a configuration
    (`world_kit.switch_lattice` says the same); `check_configs()` is where that
    is asked.
    """
    name = bay["name"]
    s0, s1 = bay["step"]
    c0, c1 = bay["cap"]
    h0, h1 = bay["shelf"]
    # The step: a permanent one-way, reachable from the floor in EVERY
    # configuration, and therefore this arena's guaranteed dodge for the bore.
    k.ledge(s0, STEP_ROW, s1 - s0 + 1, stand_form="human")
    k._claim("step", "the step off the floor into the %s bay" % name,
             x1=s0, y1=STAND_ROW, x2=s0, y2=STEP_STAND, form="human")
    # A permanent cap down to row 20 over every step and plug column. With the
    # plug at rows 21-22 it is what stops a standable tile ever appearing on top
    # of a solid plug: standing needs two clear rows and the most this column
    # can offer above a solid plug row is one.
    k.rect(c0, BAY_CAP_TOP, c1 - c0 + 1, BAY_CAP_BOT - BAY_CAP_TOP + 1, "block")
    # The plugs. Uniform down the column; see the BAYS table.
    for col, role in bay["plug"].items():
        for row in range(PLUG_TOP, PLUG_BOT + 1):
            k.put(col, row, role)
            k._release(col, row)
    # The shelf: permanent solid at row 23, stood on at row 22, with seven clear
    # rows over it in every configuration -- which is what gives the pad on it
    # the headroom tests/test_level_validity.gd demands, and what lets the shed
    # fall onto it from row 16.
    k.rect(h0, SHELF_ROW, h1 - h0 + 1, 1, "solid_alt")
    for x in range(h0, h1 + 1):
        k._claim("stand", "the %s bay's shelf at col %d" % (name, x),
                 x=x, y=SHELF_STAND, form="human")
        k._claim("clear", "the %s bay's shelf headroom at col %d" % (name, x),
                 x=x, y=SHELF_STAND, tall=2)
    # And the climb the plugs gate, claimed as a step so `audit()` checks that
    # nothing was later drawn across the arc. It is checked with switch blocks
    # PASSABLE, which is the configuration-blind question -- can this climb exist
    # at all. Whether it exists right now is `check_configs()`.
    f, t = bay["climb"]
    k._claim("step", "the climb from the %s step to its shelf" % name,
             x1=f, y1=STEP_STAND, x2=t, y2=SHELF_STAND, form="human")


# ------------------------------------------------- the per-configuration sweep
def _probe(g, cfg):
    return Probe(g, switches={1: cfg[0], 2: cfg[1]})


def _floor_run(g, cfg):
    p = _probe(g, cfg)
    return {x for x in range(ARENA_X0, ARENA_X1 + 1) if p.standable(x, STAND_ROW)}


def _bay_open(g, cfg, bay):
    """Is this bay's shelf standable AND climbable from its step?"""
    p = _probe(g, cfg)
    h0, h1 = bay["shelf"]
    if not all(p.standable(x, SHELF_STAND) for x in range(h0, h1 + 1)):
        return False
    f, t = bay["climb"]
    return path_clear(p, f, STEP_STAND, t, SHELF_STAND, LIMITS["human"]["rise"])


def check_configs(g, verbose=True):
    """The claim this level owes that `reconfig_check` cannot make.

    `world_kit.reconfig_check()`'s second arm -- "is a lever still reachable" --
    has nothing to check in a level with no lever, so this is the stronger claim
    in its place, evaluated in all FOUR configurations because nothing stops a
    later edit from giving the Heart the fourth:

      1. every arena floor tile from col 26 to col 48 is standable, so the floor
         is one connected run whatever the nest has done to itself;
      2. `boss_exit`, the floor's `pad_human` and all three bay STEPS are
         standable -- the steps are the bore's dodge and they may never switch;
      3. no tile that is standable in this configuration has a switch block
         inside the body standing on it, which is "a flip can never crush
         someone standing still" proved tile by tile rather than asserted;
      4. across the three configurations the fight uses, each bay is open in
         exactly one -- otherwise "each phase demanding a different form" is not
         what the tiles say.

    Raises `WorldKitError` on any failure. A conservative filter and NOT a proof:
    tools/prove.sh plays the approach and tools/bossgate.sh plays the arena.
    """
    problems = []
    open_in = {b["name"]: [] for b in BAYS}
    switch_chars = {NEST_CHARS.char(r) for r in
                    ("switch_a_on", "switch_a_off", "switch_b_on", "switch_b_off")}
    for label, cfg in ALL_CONFIGS:
        p = _probe(g, cfg)
        floor = _floor_run(g, cfg)
        missing = sorted({x for x in range(ARENA_X0, ARENA_X1 + 1)} - floor)
        if missing:
            problems.append(
                "%s (A=%s B=%s): the arena floor is broken at col(s) %s -- a "
                "configuration that takes a floor tile away can seal a pocket"
                % (label, cfg[0], cfg[1], missing))
        wants = [("boss_exit", EXIT_COL, STAND_ROW),
                 ("the floor pad_human", DROP_COL, STAND_ROW)]
        for bay in BAYS:
            for x in range(bay["step"][0], bay["step"][1] + 1):
                wants.append(("the %s bay's step" % bay["name"], x, STEP_STAND))
        for what, x, y in wants:
            if not p.standable(x, y):
                problems.append("%s (A=%s B=%s): %s at (%d,%d) is not standable"
                                % (label, cfg[0], cfg[1], what, x, y))
        # Claim 3, the crush proof: a body standing on ANY standable tile in
        # this configuration occupies (x, y) and (x, y-1); no switch tile may be
        # either of them.
        for y in range(ROOF_ROW, FLOOR_ROW):
            for x in range(ARENA_X0, ARENA_X1 + 1):
                if not p.standable(x, y):
                    continue
                for row in (y, y - 1):
                    if g.fg[row][x] in switch_chars:
                        problems.append(
                            "%s: a body standing on (%d,%d) has a switch block "
                            "at (%d,%d) inside it -- a flip would close on "
                            "someone standing still" % (label, x, y, x, row))
        opens = []
        for bay in BAYS:
            if _bay_open(g, cfg, bay):
                opens.append(bay["name"])
                if (label, cfg) in PHASE_CONFIGS:
                    open_in[bay["name"]].append(label)
        if verbose:
            print("  config %-10s A=%-5s B=%-5s  floor %2d/%d   bays open: %s"
                  % (label, cfg[0], cfg[1], len(floor),
                     ARENA_X1 - ARENA_X0 + 1,
                     ", ".join(opens) if opens else "(none)"))
    for name, where in open_in.items():
        if len(where) != 1:
            problems.append(
                "the %s bay is open in %d of the three phase configurations "
                "(%s); each phase must offer exactly one bay"
                % (name, len(where), ", ".join(where) or "none"))
    if problems:
        raise WorldKitError("nest_5 configurations: " + "; ".join(problems))
    if verbose:
        for name, where in open_in.items():
            print("  the %-5s bay is open in %s and nothing else" % (name, where[0]))
    return open_in


# ------------------------------------------------------------- the strand graph
class _Nav:
    """Movement per form, per configuration, over the finished grid.

    Lifted from tools/worlds/nest_3.py's `_Nav` -- the same shape as
    tools/reachability.py, which is the model this project's own validator uses
    -- with ONE difference that is this level's whole subject: the configuration
    does not change at a lever, because there is no lever. It changes because
    THE BOSS changed it, which can happen at any moment and in any order (a
    burst of damage can skip a phase threshold). So the configuration edges go
    from every state to every phase configuration, which is the most generous
    thing the Heart can do and therefore the only safe thing to check against.
    """

    def __init__(self, g, pads):
        self.g = g
        self.pads = pads
        self.probe = {c: _probe(g, c) for _l, c in ALL_CONFIGS}

    def _ground(self, p, x, y, form):
        rise, gap = LIMITS[form]["rise"], LIMITS[form]["gap"]
        out = [(x - 1, y), (x + 1, y)]
        if p.ladder(x, y) and form == "human":
            out += [(x, y - 1), (x, y + 1)]
        for dy in range(1, rise + 1):
            for dx in range(-gap, gap + 1):
                out.append((x + dx, y - dy))
        for dx in range(-gap, gap + 1):
            out.append((x + dx, y))
        for dx in range(-gap, gap + 1):
            for dy in range(1, self.g.h):
                nx, ny = x + dx, y + dy
                if not p.clear(nx, ny):
                    break
                if p.standable(nx, ny):
                    out.append((nx, ny))
                    break
        return [(nx, ny) for (nx, ny) in out
                if 0 <= nx < self.g.w and 0 <= ny < self.g.h
                and p.standable(nx, ny) and not p.hazard(nx, ny)
                and path_clear(p, x, y, nx, ny, rise)]

    def _fly(self, p, x, y):
        out = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (0 <= nx < self.g.w and 0 <= ny < self.g.h
                    and p.clear(nx, ny) and not p.hazard(nx, ny)):
                out.append((nx, ny))
        return out

    def successors(self, state):
        x, y, form, cfg = state
        p = self.probe[cfg]
        out = []
        for (px, py), pform in self.pads.items():
            if abs(px - x) <= 1 and abs(py - y) <= 1 and pform != form:
                out.append((x, y, pform, cfg))
        # The Heart's flip, from anywhere, to any phase configuration.
        for _label, other in PHASE_CONFIGS:
            if other != cfg:
                out.append((x, y, form, other))
        moves = self._fly(p, x, y) if form == "bird" \
            else self._ground(p, x, y, form)
        return out + [(nx, ny, form, cfg) for (nx, ny) in moves]


def _strand_graph(g, start, goals):
    """(where x which form x which switches), flooded forward then backward.

    nest_3's check, adapted: every state the player can get into inside the
    hearthold, and every one of those from which she can no longer reach BOTH
    the floor's `pad_human` (her weapon) and `boss_exit` (the way out). ADR 004
    per configuration, which the brief called this level's hardest obligation.

    Returns (reachable, dead_ends).
    """
    pads = {(int(e["x"]), int(e["y"])): e["type"][4:]
            for e in g.entities if e["type"].startswith("pad_")
            and int(e["y"]) >= ROOF_ROW}
    nav = _Nav(g, pads)
    root = (start[0], start[1], "human", SEEDED)
    seen, back, q = {root}, {}, deque([root])
    while q:
        s = q.popleft()
        for n in nav.successors(s):
            back.setdefault(n, []).append(s)
            if n not in seen:
                seen.add(n)
                q.append(n)
    good = set(seen)
    for goal in goals:
        wins = [s for s in seen if (s[0], s[1]) == tuple(goal)]
        reach, q = set(wins), deque(wins)
        while q:
            s = q.popleft()
            for prev in back.get(s, ()):
                if prev in seen and prev not in reach:
                    reach.add(prev)
                    q.append(prev)
        good &= reach
    return seen, sorted(seen - good)


# ------------------------------------------------------------------ self-checks
def _self_checks(g, k, verbose=True):
    """Everything this level asserts about itself that `audit()` cannot.

    (a) the arena and data/enemies/obsidian_heart.json agree about the floor,
        the shed row, which columns the shed covers, and which columns the Heart
        is clamped to;
    (b) no claim and no entity stands on a cap row divisible by 15 (ruins_4's
        screen-seam defect);
    (c) nothing in the level stands ON a switch tile in any configuration
        (tools/reachability.py resolves a switched tile as never solid, so a
        route that stood on one would be a route the validator cannot credit);
    (d) the shed covers every refuge column and no comb column;
    (e) ADR 004 per configuration, via `_strand_graph`;
    (f) every plug column is uniform over rows 21-22;
    (h) no column between a step and its shelf is left un-plugged;
    (g) no standable tile in ANY configuration has one tile of headroom while
        being walkable into from beside -- the rule
        tests/test_level_validity.gd applies to the level on disk, applied here
        to all four rooms the level becomes.
    """
    import json
    problems = []
    with open(os.path.join(os.path.dirname(os.path.dirname(HERE)), BOSS_JSON)) as f:
        boss = json.load(f)

    # (a) the two files agree.
    shed = boss.get("shed", {})
    if int(shed.get("row", -1)) != SHED_ROW:
        problems.append("%s shed.row is %s, the arena throws from %d"
                        % (BOSS_JSON, shed.get("row"), SHED_ROW))
    cols = list(boss.get("arena_cols", []))
    if cols != [32, 39]:
        problems.append("%s arena_cols is %s; the plug columns are %s, and the "
                        "Heart's body must stay clear of every one of them"
                        % (BOSS_JSON, cols,
                           sorted(c for b in BAYS for c in b["plug"])))
    for bay in BAYS:
        for c in bay["plug"]:
            if cols and cols[0] <= c <= cols[1]:
                problems.append(
                    "the %s bay's plug at col %d is inside the Heart's clamp "
                    "(%s) -- a boss inside its own moving wall"
                    % (bay["name"], c, cols))

    # (d) THE THREE TIERS AND THE THREE ATTACKS.
    #
    # The arena has exactly three heights a body can stand at, and the fight has
    # exactly one attack for each of them -- which is what "nothing is safe from
    # everything" means here, checked rather than asserted:
    #
    #   floor  rows 25-26   the BORE, running the floor 4 px up
    #   step   rows 23-24   the GLASS, a volley swept along the step band
    #   shelf  rows 21-22   the SHED, falling from row 16
    #
    # and each tier is the dodge for the other two. The comb is the shed's own
    # dodge on the floor, and it earns that by being solid at the row the shed
    # is thrown from, so a shard over it dies on the frame it is born.
    shed_cols = set(int(c) for c in shed.get("cols", []))
    want = set()
    for bay in BAYS:
        want |= set(range(bay["shelf"][0], bay["shelf"][1] + 1))
    if not want <= shed_cols:
        problems.append("shed.cols misses shelf column(s) %s -- a shelf the shed "
                        "cannot reach is out of the bore's reach, out of the "
                        "glass's reach and out of the Heart's reach, which is a "
                        "stalemate to camp in" % sorted(want - shed_cols))
    comb_cols = set(range(COMB[0], COMB[1] + 1))
    if shed_cols & comb_cols:
        problems.append("shed.cols includes comb column(s) %s, and the floor "
                        "under the comb is the shed's only dodge"
                        % sorted(shed_cols & comb_cols))
    for c in sorted(shed_cols):
        if g.fg[SHED_ROW][c] != ".":
            problems.append("shed column %d is not open at row %d, so its shard "
                            "is born inside rock" % (c, SHED_ROW))
    # The glass sweeps the step band. It must clear every step's body and miss
    # every floor body: a body on a step at row 24 spans y 378..400 and a body on
    # the floor spans y 410..432, so the volley's own band has to live inside the
    # first and outside the second. The boss JSON's `glass_height` is the offset
    # from the Heart's centre; the Heart's centre is 23 px below its top and its
    # feet are on the floor at y 432.
    gh = float(boss.get("glass_height", 0.0))
    gspread = float(boss.get("glass_spread", 0.0))
    heart_centre = float(FLOOR_ROW) * 16.0 - 46.0 + 23.0
    top = heart_centre - gh - gspread - 3.0
    bot = heart_centre - gh + 3.0
    step_top = float(STEP_ROW) * 16.0 - 22.0
    step_bot = float(STEP_ROW) * 16.0
    floor_top = float(FLOOR_ROW) * 16.0 - 22.0
    if not (top >= step_top and bot <= step_bot):
        problems.append("the glass volley spans y %.0f..%.0f, which is not "
                        "inside a step body's %.0f..%.0f" % (top, bot,
                                                             step_top, step_bot))
    if bot >= floor_top:
        problems.append("the glass volley reaches y %.0f, which is inside a "
                        "floor body's %.0f..%.0f -- the floor is the glass's "
                        "dodge and it has just stopped being one"
                        % (bot, floor_top, float(FLOOR_ROW) * 16.0))

    # (b) the screen seam.
    for kind, c in k.claims:
        rows = [c["y"] + 1] if kind == "stand" else []
        for r in rows:
            if r % 15 == 0:
                problems.append("%s: stands on cap row %d, a screen seam"
                                % (c["why"], r))
    for e in g.entities:
        if e["type"] in ("player_spawn", "boss_exit") or e["type"].startswith("pad_"):
            if (int(e["y"]) + 1) % 15 == 0:
                problems.append("%s at (%s,%s) stands on a screen seam"
                                % (e["type"], e["x"], e["y"]))

    # (c) nothing stands on a switch tile, in any configuration.
    switch_chars = {NEST_CHARS.char(r) for r in
                    ("switch_a_on", "switch_a_off", "switch_b_on", "switch_b_off")}
    for label, cfg in ALL_CONFIGS:
        p = _probe(g, cfg)
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                if p.standable(x, y) and g.fg[y + 1][x] in switch_chars:
                    problems.append("%s: (%d,%d) stands ON a switch tile" %
                                    (label, x, y))

    # (h) COYOTE TIME. `data/forms/human.json`'s `coyote_time` is 0.09 s and she
    # runs at 108 px/s, so leaving a ledge buys her up to 10 px -- most of a
    # column -- of still-jumpable air. A gate in the column she STANDS in is
    # therefore not a gate: she steps off it and jumps from the next one. See
    # the BAYS table for the trace that measured it.
    #
    # The rule: every column from the step's far edge up to (not including) the
    # shelf must carry a plug, EXCEPT the step's own columns -- and if a step
    # column is left unplugged, the first column past it must be plugged.
    for bay in BAYS:
        s0, s1 = bay["step"]
        h0, h1 = bay["shelf"]
        toward_east = h0 > s1
        span = list(range(s1 + 1, h0)) if toward_east else list(range(h1 + 1, s0))
        gaps = [c for c in span if c not in bay["plug"]]
        if gaps:
            problems.append(
                "the %s bay leaves col(s) %s between its step and its shelf "
                "un-plugged, and coyote time is 0.09 s" % (bay["name"], gaps))
        if not span and not any(c in bay["plug"] for c in range(s0, s1 + 1)):
            problems.append(
                "the %s bay's shelf is adjacent to its step and neither is "
                "plugged: nothing gates it at all" % bay["name"])
        # And no gate column may have anything solid under it, in any
        # configuration: a floor under a plug is a standable tile inside the
        # plug, which is a body a flip can close on.
        for col in bay["plug"]:
            if col >= s0 and col <= s1:
                continue                     # a step column: its floor is the
                                             # one-way, two rows below the plug
            for label, cfg in ALL_CONFIGS:
                pp = _probe(g, cfg)
                for row in range(PLUG_BOT + 1, FLOOR_ROW):
                    if pp.solid(col, row) or pp.oneway(col, row):
                        problems.append(
                            "%s: the %s bay's gate at col %d has something to "
                            "stand on at row %d, so a body could stand INSIDE "
                            "its plug in the configuration that opens it -- "
                            "which is a body the next flip closes on"
                            % (label, bay["name"], col, row))

    # (f) every plug column is UNIFORM over rows 21-22, and (g) the pocket rule
    # that tests/test_level_validity.gd applies to the SEEDED configuration,
    # applied here to all four. (g) is the check that caught the striped plug,
    # and running it per configuration rather than per file is the only way this
    # level can be sure: the shipped test sees one of four rooms.
    for bay in BAYS:
        for col, role in bay["plug"].items():
            rows = {g.fg[r][col] for r in range(PLUG_TOP, PLUG_BOT + 1)}
            if len(rows) != 1:
                problems.append(
                    "the %s bay's plug at col %d is not uniform (%s). A column "
                    "with two switch roles in it is standable at the seam in "
                    "one of the four configurations, with one tile of headroom "
                    "-- which reads as a passage and behaves as a wall"
                    % (bay["name"], col, sorted(rows)))
    for label, cfg in ALL_CONFIGS:
        p = _probe(g, cfg)

        def clearance(x, y):
            n = 0
            while y - n >= 0 and not p.solid(x, y - n):
                n += 1
            return n

        for y in range(ROOF_ROW, H - 1):
            for x in range(ARENA_X0, ARENA_X1 + 1):
                if p.solid(x, y):
                    continue
                if not (p.solid(x, y + 1) or p.oneway(x, y + 1)):
                    continue
                if clearance(x, y) >= 2:
                    continue
                for dx in (-1, 1):
                    if not p.solid(x + dx, y) and clearance(x + dx, y) >= 2:
                        problems.append(
                            "%s: (%d,%d) is standable with %d tile(s) of "
                            "headroom and can be walked into from (%d,%d)"
                            % (label, x, y, clearance(x, y), x + dx, y))

    # (e) ADR 004, per configuration.
    seen, dead = _strand_graph(g, (DROP_COL, STAND_ROW),
                               [(DROP_COL, STAND_ROW), (EXIT_COL, STAND_ROW)])
    if dead:
        problems.append(
            "%d state(s) inside the hearthold cannot get back to both the floor "
            "pad and boss_exit, e.g. %s" % (len(dead), dead[:6]))
    if verbose:
        print("  strand graph: %d states (tile x form x configuration) from the "
              "landing tile," % len(seen))
        print("                %d of them dead ends. Every state can still reach "
              "the floor pad" % len(dead))
        print("                AND boss_exit, in every configuration the Heart "
              "can force.")
    if problems:
        raise WorldKitError("nest_5 self-checks: \n  " + "\n  ".join(problems))


def main(argv):
    g, k = nest_5()
    missing = NEST_CHARS.missing()
    if missing:
        print("  PALETTE  %d role(s) with no legend character: %s"
              % (len(missing), ", ".join("%s->%s" % m for m in missing)))
    for line in k.audit(strict_verbs=True):
        print(line)
    print("  CONFIGURATIONS")
    check_configs(g)
    if "--configs" in argv:
        return 0
    print("  SELF-CHECKS")
    _self_checks(g, k)
    if "--check" in argv:
        return 0
    write(LEVEL_ID, g, LEVEL_NAME, music="boss")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
