#!/usr/bin/env python3
"""nest_3 -- FOUR SHAPES.  World 5, THE OBSIDIAN NEST, third level.

Self-contained: running this file under the project python writes
levels/nest_3.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `nest_3()` returning `(Grid, Kit)`,
the tuple that writer's `build()` expects -- it audits the kit before it writes.

    source tools/env.sh && "$PYVENV" tools/worlds/nest_3.py
    tools/prove.sh nest_3
    ITEST_TIMEOUT=300 tools/itest.sh --only=t_replay_nest_3 --trace=1

WHAT THE LEVEL IS ABOUT
-----------------------
nest_1 taught the lever and nest_2 scaled it.  This is the other half of World
5's brief: the game's whole movement vocabulary, in one level, with the lever
braided through it.  FOUR WINGS, ONE PER FORM, one to a screen, walked as a
ring anticlockwise from the bottom left:

           +---------------------+---------------------+
   rows    |  (0,0) THE QUENCH   |  (1,0) THE AERIE    |
   1-13    |  FISH   + the exit  |  BIRD               |
           +---------------------+---------------------+
   rows    |  (0,1) THE FORGE    |  (1,1) THE FLUE     |
   16-28   |  FLOOR  HUMAN       |  FROG               |
           +---------------------+---------------------+

  1  THE FORGE FLOOR (human, cols 1-24).  Everything Kaya alone can do.  A run,
     a three-tile jump over a shard trench, a CHAIN -- `can_climb` is true in
     data/forms/human.json and false in the other three, so a ladder is the one
     piece of terrain in this game that is hers -- and at the top of it a
     three-tile gap over a six-row drop with `switch_a` on the far shelf.  Jump
     it, or throw the blade across it.  Both open the door she is standing in
     front of; see THE BLADE AND THE PROVER for why the proved route jumps.

  2  THE FLUE (frog, cols 25-47).  A chimney climbed in three-tile steps --
     LIMITS["frog"]["rise"], one tile past the human's -- with the shaft's walls
     one tile off each shoulder so an overshoot meets rock and clings to it
     (`wall_stick_time` 0.55) instead of falling the length of the climb.  The
     lid at the top is OPEN when she gets there and the lever above it shuts it.

  3  THE AERIE (bird, cols 26-47 upper).  No thermals -- see WHAT THIS WORLD
     DOES NOT HAVE.  The bird pays for every tile it gains out of
     `max_stamina` 100, and the only things that give it back are two perches.
     It leaves through a door the FROG opened, and it meets that door shut.

  4  THE QUENCH (fish, cols 2-24 upper).  Still water seven tiles deep, split
     by a wall whose only window is the sluice at rows 10-12.  That sluice is a
     group-1 gate: the lever Kaya threw in the first room is the door at the
     bottom of the last one.

THE BRAID
---------
One lever per group -- nest_1's measured hard rule, re-checked here in
`_self_checks` (h) -- so scale comes from one lever moving several doors in
rooms it cannot see, which is nest_2's finding.  Four doors off two levers:

    A1  col 23, rows 24-25   a_on   the forge floor's east door.  SHUT at
                                    spawn.  The one door in the level whose
                                    lever is in the same frame, and the one the
                                    player watches open.
    A2  col 12, rows 10-12   a_on   the quench's sluice, four screens away and
                                    two forms later.  Same throw.
    B2  col 44, rows 16-17   b_on   the flue's lid.  OPEN at spawn; throwing B
                                    SHUTS IT, and the whole climb with it.
    B1  col 25, rows  5- 6   b_off  the aerie's west door.  Shut at spawn,
                                    opened by the same throw that shut B2.

    switch_a  (8,19)  on the forge floor's west shelf    ->  A1, A2
    switch_b  (39,17) in the flue's head corridor        ->  B1, B2

So Kaya's lever opens the door in front of her AND the fish's sluice; the frog's
shoulder shuts the flue behind it AND opens the door the bird flies through.
Neither lever serves only its own wing, and `_self_checks` (f) fails the build
if that stops being true.

THE COMMITMENT, AND WHY IT IS SAFE
-----------------------------------
B2 and B1 are one group in opposite senses -- nest_2's reversal, on a smaller
board.  The frog climbs the flue through an open lid, walks into the head
corridor, and the throw that opens the bird's door two screens away shuts the
lid it just came through, in the same frame it is standing in.  Everything below
is sealed.

That is a commitment and not a trap because of where the lever is: `switch_b` is
ABOVE the lid.  The region the throw seals off -- head corridor, chimney, aerie,
quench -- contains both the exit and the lever that undoes the seal, and the
aerie's floor has a three-column hole in it at cols 35-37 that drains straight
back down into the corridor the lever is in.  So a bird that finds the aerie's
door shut because it threw twice falls down the chimney, walks four tiles and
throws again.  A wrong throw costs a lap, never a save, which is the standard
nest_2 set.  `_self_checks` (g) proves it rather than asserting it.

ADR 004 -- NO TRANSFORM STRANDS YOU, AND NO CONFIGURATION DOES EITHER
---------------------------------------------------------------------
Four forms, four one-way pads and two switch groups is a bigger board than
`reconfig_check` or nest_1's `_escape` was written for: those search
(where-you-stand x switch-state) as the HUMAN.  `_strand_graph` here searches
(where-you-stand x WHICH FORM YOU ARE x switch-state), with

  * ground jumps at the measured LIMITS for the human and the frog,
  * a clear-space flood for the bird (which is what tools/reachability.py does,
    for the reason it gives: a jump envelope understates a body that flies),
  * a water flood plus the one-tile bank hop for the fish, plus the revert
    `src/player/forms/form_fish.gd` performs when `air_seconds` runs out on
    land -- which is a real edge out of every dry tile a fish can stand on,
  * form changes ONLY on a pad,
  * configuration changes ONLY on a lever's own tile, never from beside it:
    generosity about escaping is the one direction this check must not be wrong
    in.

Then it reverses every edge and floods back from the exit, and asserts that
EVERY REACHABLE STATE CAN STILL REACH THE EXIT.  That is strictly stronger than
"the goal is reachable in one of four configurations", and it is the question
tools/prove.sh structurally cannot ask, because the prover only ever plays the
route that was declared.

The thing it proves that no amount of prose would is this: group 1 can never
return to ON once you are east of A1, because the only thing that sets it is
`switch_a` and `switch_a` is west of A1.  So A2, the sluice at the bottom of the
cistern, cannot close behind the fish.  The check finds that; this docstring
does not assert it.

THE AIRLOCK
-----------
`pad_human` at (26,25) and `pad_frog` at (30,25), four tiles apart on the same
floor, are one shape and not two pads.  Walking east Kaya crosses the human pad
as a human -- `TransformPad._physics_process` refuses when
`p.form_id == form_id` -- and the frog pad turns her; walking back, the frog
crosses the frog pad as a frog and the human pad turns her back.  Four tiles
because `TransformPad.aabb()` is the tile grown by 3 px, so it is 22 px wide,
and two pads closer than two tiles overlap -- a body in the overlap flips form
every 0.8 s forever.

It is also the frog's half of ADR 004: a frog anywhere in the flue below the lid
can walk back down to the floor, become Kaya, and climb the chain to `switch_a`
again.

WHAT THIS WORLD DOES NOT HAVE, AND WHY THAT IS THE POINT
--------------------------------------------------------
Checked, because the brief asked.  `world_kit.NEST` declares roles for `water`
and `water_top` and declares NO `cur_*`, `updraft`, `downdraft` or `gust_*` role
at all.  The current and draught CHARACTERS are `shared` in
data/level_legend.json -- '>' '<' 'u' 'v' '}' '{' 'U' '*' 'V' ')' '(' -- so a
nest level could paint them and they would work.  This one does not:

  * THE BIRD IS OUT OF ITS ELEMENT, on purpose.  THERMAL HEIGHTS spent a whole
    world on moving air; an updraft here would do the bird's work for it on the
    one level that exists to ask whether you can still do it yourself.  So the
    aerie is still air and the exam is stamina.  `flap_cost` 12 against
    `max_stamina` 100 is eight flaps; `flap_interval` 0.24 spreads them over
    1.9 s; one flap is -172 px/s decaying at gravity 420, about 29 px of net
    climb, so 1.8 tiles.  Eight of them is 14 tiles and the aerie is eleven rows
    from the chimney's mouth to the door: the crossing fits in one bar and only
    just, and `stamina_regen` 46/s plus `perch_regen_bonus` 34 is what the two
    perches are for.

  * THE FISH IS IN ITS ELEMENT, because this is the one world that never gave it
    any.  Real water, no current in it: the quench asks the fish's own body --
    the dive, the swim under a wall, and the one-tile bank, which is
    `surface_hop` -210 against gravity 900, 24.5 px, one tile and never two
    (defect 4, and LIMITS["fish"]["rise"] = 1 is what refuses the second).

  * THE FROG HAS ITS SHOULDER and the nest does carry a tile for it.  The
    palette's `shoulder` role is `cracked_stone` (211, `break_hold` 0.35), a
    `shared` character.  MEASURED FROM THE CODE, not assumed, because the first
    capture of it did nothing: `FormBase.tick_break` runs from `update()` for
    every form -- it is deliberately not a per-form override, so the prover sees
    the same walls the game does -- but `_break_target_of` returns nothing
    unless `input.attack` is HELD.  So shouldering is hold-attack-and-press, and
    it works for the frog and the bird precisely because that path never asks
    `can_attack`: their attack button spawns no weapon and still opens the wall.
    There is exactly one of these in the level, at col 43 rows 21-22 with a
    heart behind it, and it is OFF THE PROVED ROUTE.  The nest's OWN breakable,
    `nest_crust` (291), declares no `break_hold` at all, so `_break_target_of`
    skips it and only the BLADE opens it; that one is at col 3, in the wing of
    the only form that carries one, which is where a weapon-only wall belongs.

THE BLADE AND THE PROVER
------------------------
`ProverSearch.action_set()` is {left, none, right} x {jump, no jump} x {none,
up, down} and says in its own comment that ATTACK IS DELIBERATELY ABSENT and may
not be added alone, because `ProverSim.snapshot()` does not carry
`TileWorld._broken`.  So the prover can neither break a tile nor throw the blade
at a lever, and two rules fall out of that:

  * EVERY LEVER ON THE PROVED ROUTE IS THROWN BY CONTACT, which is this level's
    premise anyway: three of its four forms have no weapon at all and the
    fish's `bite` is `reach` 10 with no projectile, so it trips nothing.  The
    trigger box is the BOTTOM TEN PIXELS of the tile inset one pixel a side
    (level.gd: `sw.setup(p + Vector2(1, 6), ...)`, `SwitchTrigger.SIZE` 14x10),
    and each of the four bodies resting on that tile's floor spans [16-h, 16] of
    it: human 22, frog 11, bird 9, fish 9.  All four overlap.
    `_self_checks` (h) re-derives that from data/forms/*.json rather than
    trusting this paragraph.
  * EVERY BREAKABLE IS OFF THE ROUTE.  Both of them are treasure, and
    `_self_checks` (i) fails the build if a hop's bounding box contains one.

The blade is not decoration for it.  The three-tile gap at row 19 is a real jump
over a six-row drop, and `boomerang_blade` is `max_range` 118 px at `speed` 205
with `rise` -8 -- flat, seven tiles -- so from the east shelf the lever on the
west shelf is inside the throw and the jump is optional.  The prover takes the
jump because it has no choice; tools/seq/nest_3.json takes the throw, in the
running game, and shots/nest_3_d_blade_throw.png is it.

WHY THE LEVERS ARE IN THE LANE, WHICH IS NOT WHAT nest_2 DID
-------------------------------------------------------------
nest_2 put both its levers on treads two rows above the walking lane, because a
lever in a corridor is thrown by everyone who walks past it and thrown again
27 frames later if they stop on it.  That was right for a level whose whole
subject is planning a throw.  It is wrong for this one, and deliberately:

  * three of the four forms have no weapon, so CONTACT is the only throw they
    have, and a lever a frog has to hop onto a `oneway` tread to reach is a
    lever the fish and the bird can never reach at all;
  * the re-throw is the recovery path here rather than an accident.  Walking
    back east along the head corridor re-opens the lid -- which is exactly what
    you want to do if you are going back down -- and `_strand_graph` proves that
    every double-throw is a lap and not a save.

`switch_a` is still out of the lane in the sense that matters: its shelf is a
dead end four tiles wide with a three-tile gap in front of it, so nobody walks
past it, they arrive at it.

WHERE THE FLOORS SIT, AND THE FOUR SEAMS
-----------------------------------------
`CameraController` picks its screen from the body's CENTRE and freezes the sim
for 0.12 s while it flips, so a 22 px body on a floor whose cap row is a
multiple of 15 has its feet on the seam and its centre on the screen above --
which never draws the floor it is standing on.  That is the defect ruins_4
shipped.  The stand rows here are 25, 22, 19, 17, 13, 10 and 6, and
`_self_checks` (b) fails the build on any claim or entity that stands on a cap
row divisible by 15.

The route crosses a seam three times:

    hop  6  m_gate_w -> m_lock    the vertical seam at x=400, WALKED, along
                                  unbroken floor with A1 open
    hop 14  pad_bird -> m_air     the horizontal seam at y=240, FLOWN, up the
                                  middle of a three-column chimney
    hop 17  perch_2 -> pad_fish   the vertical seam again, FLOWN, between two
                                  standable ledges at the same row

No ON-FOOT hop changes screen except hop 6, and hop 6 is a flat walk.
`_self_checks` (c) is that rule; it exempts the bird and the fish by name in
SEAM_EXEMPT rather than by silence.

THE PALETTE
-----------
`Palette.char()` resolves a tile NAME through the flat, jungle-derived `legend`
key of data/level_legend.json, so THE OBSIDIAN NEST's own names have no
character there and fall through to UNDERSTUDY -- where `solid` would emit 's'
(nest_plate, the second solid) and `bg` would emit 'r' (nest_vein, a background
accent).  That is the memory note "world_kit ruins palette emits wrong stone",
in World 5.  So every role is declared as the JUNGLE tile that owns the
character the nest tileset binds to the art we want.

The mass is obsidian ('#') and the built walls are nest_block ('d'), which is
the agreement nest_1's captures forced and nest_2 recorded: nest_plate ('s') is
an object and not a mass, so it is declared and never drawn.  Every gate's head
is nest_block, so a doorway reads as masonry cut into glass and the plug in it
reads as the thing that moves.  `Palette.missing()` is empty, `substituted`
stays empty, and the level serialises `"tileset": "nest"`.
"""
import json
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                          # noqa: E402
import world_kit                                            # noqa: E402
from world_kit import (Kit, Palette, Probe, LIMITS,          # noqa: E402
                       BODY_TILES, path_clear, check_gap, check_rise)

LEVEL_ID = "nest_3"
LEVEL_NAME = "FOUR SHAPES"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the nest role character.
## A character map, not an art claim: the art comes from `"tileset": "nest"` at
## load time.  Identical to nest_2's, on purpose -- the world's mass is
## obsidian and its built walls are nest_block, and a third spelling of that
## inside one world would be a bug nobody could see.
NEST_W5 = Palette("obsidian_nest", {
    "bg": "bg_leaves",              # 'L' -> 282 nest_wall
    "solid": "grass_top",           # '#' -> 280 obsidian      (the mass)
    "solid_alt": "stone_mossy",     # 'S' -> 281 obsidian_hot  (the hot face)
    "block": "dirt",                # 'd' -> 283 nest_block    (built walls)
    "packed": "stone",              # 's' -> 290 nest_plate    (declared, unused)
    "oneway": "wood_platform",      # '=' -> 286 nest_ledge
    "ladder": "vine",               # '|' -> 288 nest_chain
    "hazard": "spikes",             # '^' -> 287 nest_shard
    "breakable": "crate",           # 'c' -> 291 nest_crust    (blade only)
    "shoulder": "cracked_stone",    # 'k'  shared 211, break_hold 0.35
    "rubble": "rubble",             # 'o'  shared (unused)
    "decor": "tree_trunk",          # 'T' -> 285 nest_flue
    "void": "bg_dark",              # 'X' -> 284 nest_void
    "water": "water",               # 'w'  shared
    "water_top": "water_top",       # '~'  shared
    "switch_a_on": "switch_block_a_on",    # 'A' shared, 11
    "switch_a_off": "switch_block_a_off",  # 'a' shared, 26
    "switch_b_on": "switch_block_b_on",    # 'B' shared, 12
    "switch_b_off": "switch_block_b_off",  # 'b' shared, 27
})


# ---------------------------------------------------------------- the shape
## Every number the geometry and the checks share, in one place.

SEAM_COL = 25                   # first column of the eastern screens (x=400)
SEAM_ROW = 15                   # first row of the lower screens (y=240)
EAST_WALL = 48                  # the level is cols 1..47

# -- the two bands.  Rows 14-15 are the divider: row 14 is the upper band's
#    floor cap and row 15 its fill, so the lower band's roof is row 16 except
#    where the head corridor is cut into it.
UP_CAP, UP_STAND = 14, 13
LOW_CAP, LOW_STAND = 26, 25
LOW_ROOF = 16

# -- 1. the forge floor (screen C, cols 1-24) --------------------------------
#    Read west to east: the vault, the spawn, the trench, the chain, the shelf
#    the chain lands on, the gap, the shelf the lever is on, and the door.
VAULT_X0, VAULT_X1 = 1, 2       # the blade-only vault, rows 24-25
CRUST_COL = 3                   # its nest_crust plug
SPAWN = (5, LOW_STAND)
TRENCH_X0, TRENCH_W = 7, 2      # the shard trench in the floor
CHAIN_COL = 11                  # rows 19-25: the human's own terrain
SHELF_CAP, SHELF_STAND = 20, 19
CSHELF_X0, CSHELF_X1 = 12, 15   # the chain's landing, and the lattice's roof
BLADE_GAP_X0, BLADE_GAP_W = 16, 2
LSHELF_X0, LSHELF_X1 = 18, 21   # the lever's shelf, 4 wide
SWITCH_A = (19, SHELF_STAND)
A1_COL = 23                     # the forge floor's east door
LATTICE_A = (12, 21, 4, 2)      # hanging off the chain shelf's own cap

# -- 2. the flue (screen D, cols 25-47) --------------------------------------
PAD_HUMAN_LOW = (26, LOW_STAND)
PAD_FROG_LOW = (30, LOW_STAND)
## The shaft is EAST of the head corridor, not under it: the corridor's own
## floor is a lid over everything below it, so a climb that ends under cols
## 35-43 ends under a ceiling.  `audit()` caught the first draft doing exactly
## that -- "nothing gets a body from (41,22) to (44,19) as the frog".
BUTTRESS_X0 = 39                # the pier under the corridor, rows 19-23
FLUE_WALL_COL = 43              # rows 19-23: the shaft's west shoulder
S1_X0, S1_X1, S1_CAP = 44, 45, 23
S2_X0, S2_X1, S2_CAP = 46, 47, 20
PITCH = 3                       # rows between shelves: the frog's ceiling
B2_COL = 44                     # the flue's lid, rows 16-17
CORR_X0, CORR_X1 = 26, 43       # the head corridor, rows 16-17
CORR_CAP, CORR_STAND = 18, 17
SWITCH_B = (39, CORR_STAND)
PAD_BIRD = (36, CORR_STAND)
CHIM_X0, CHIM_X1 = 35, 37       # the chimney through the divider, rows 14-15
SECRET_X0, SECRET_X1 = 40, 42   # the shoulder-break cell, rows 21-22
SECRET_CAP = 23

# -- 3. the aerie (screens A and B upper, cols 26-47) ------------------------
AERIE_X0, AERIE_X1 = 26, 47
B1_COL = 25                     # the aerie's west wall, rows 1-13
B1_STAND = 6                    # its door: rows 5-6
MIDWALL_COL = 30                # rows 6-13: what stops the floor being walked
WSHAFT_X0, WSHAFT_X1 = 26, 29   # rows 14-16: the aerie's west shoulder, open
PERCH_1 = (31, 11)              # cols 31-33, cap 11 -> stand 10
PERCH_2 = (26, 7)               # cols 26-28, cap  7 -> stand  6
PERCH_W = 3
LATTICE_B = (44, 3, 4, 6)       # cols 44-47, hanging off a lintel at row 2

# -- 4. the quench (screen A lower half, cols 2-24) --------------------------
LEDGE_X0, LEDGE_X1 = 22, 24     # where the bird lands, cap 7 -> stand 6
CIST_X0, CIST_X1 = 2, 21
CIST_TOP = 1
SURFACE = 7                     # the water_top row; water runs 8..13
A2_COL = 12                     # the sluice wall, rows 4-13
A2_STAND, A2_H = 12, 3          # its window: rows 10-12
BANK_X0, BANK_W = 4, 5          # cols 4-8, cap 7 -> stand 6
STEP_X0, STEP_W, STEP_ROW = 2, 2, 9   # the submerged step beside the bank
PAD_FISH = (LEDGE_X0, SURFACE - 1)
PAD_HUMAN_BANK = (BANK_X0 + 1, SURFACE - 1)
EXIT_TILE = (7, SURFACE - 1)

## What tools/solver/sim.gd seeds before a switch entity is touched: TileWorld's
## own defaults, group 1 ON and group 2 OFF.  Both levers declare the same, so
## `SwitchTrigger._ready()` agrees.
START_CFG = {1: True, 2: False}
CFGS = [{1: a, 2: b} for a in (True, False) for b in (True, False)]

## (col, solid_when, group, top, stand, why) for every door.  `_self_checks`
## (e) reads this table rather than the prose above it.
PLUGS = [
    (A1_COL, "on", "a", LOW_STAND - 1, LOW_STAND,
     "A1: the forge floor's east door"),
    (A2_COL, "on", "a", A2_STAND - A2_H + 1, A2_STAND,
     "A2: the quench's sluice"),
    (B2_COL, "on", "b", LOW_ROOF, CORR_STAND,
     "B2: the flue's lid, shut by the throw that opens B1"),
    (B1_COL, "off", "b", B1_STAND - 1, B1_STAND,
     "B1: the aerie's west door"),
]

## Every nest_vein tile: this level's light.  Each is an AIR tile on the bg
## layer with rock beside it, and `_hot()` bands that rock with obsidian_hot --
## which is the tile that actually emits, because
## `AmbienceLayer._collect_emissive` scans the fg and 289 is a background tile
## by its own art.  nest_1 settled that and nest_2 re-checked it; (j) does here.
VEINS = [
    (4, LOW_STAND), (13, LOW_STAND), (22, LOW_STAND),        # the forge floor
    (27, LOW_STAND), (33, LOW_STAND), (38, LOW_STAND), (46, LOW_STAND),
    (14, SHELF_STAND), (21, SHELF_STAND),                    # its two shelves
    (44, S1_CAP - 1), (46, S2_CAP - 1),                      # the flue
    (36, CORR_STAND), (42, CORR_STAND),                      # the head corridor
    (31, UP_STAND), (34, UP_STAND), (38, UP_STAND), (45, UP_STAND),
    (26, 3), (26, 10), (29, UP_STAND),                       # the aerie's walls
    (11, SURFACE - 1), (13, SURFACE - 1),                    # the sluice wall
    (24, SURFACE - 1), (8, SURFACE - 1),                     # ledge and bank
]


def _hot(k):
    """Band the rock a vein touches with obsidian_hot.

    280 and 281 are both plain `solid` -- the same tile to every flag-reading
    checker -- so this is colour and nothing else.  Generated from VEINS rather
    than listed by hand, because the claim is "the glass is hot WHERE THE VEIN
    IS" and a hand-written band drifts off its vein the first time one moves.

    Only the mass and the built walls are repainted: a ledge, a chain, a shard
    or a switch block beside a vein keeps its own art, because each of those is
    a verb and a recoloured verb stops reading as itself.
    """
    g = k.g
    mass, built, hot = k.ch("solid"), k.ch("block"), k.ch("solid_alt")
    for x, y in VEINS:
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < g.w and 0 <= yy < g.h and g.fg[yy][xx] in (mass, built):
                g.put(xx, yy, hot)


def _plug(k, col, top, stand, group, solid_when, why):
    """A door with no key: a column of switch blocks filling a corridor.

    Full height, always.  A plug one tile short of its own roof is the defect
    this world is most able to produce, because a switch block LOOKS like a wall
    whatever it is doing.  The head is drawn in nest_block so the opening reads
    as masonry cut into glass -- the legibility correction nest_1's captures
    forced -- and it is also what `_self_checks` (d) wants: rock over every
    switch tile, in every configuration, so nothing can ever stand on one.
    """
    k.switch_gate(col, stand, stand - top + 1, group=group,
                  solid_when=solid_when)
    k.put(col, top - 1, "block")
    k.note("%s at col %d: switch_block_%s_%s, %d tiles, rows %d-%d"
           % (why, col, group, solid_when, stand - top + 1, top, stand))
    return col


def _air_mark(k, name, x, y):
    """A waypoint in mid-air, for the bird.

    Not `Kit.mark`: that files a "stand" claim and nothing inside a chimney is
    standable.  `ProverSearch._reached` accepts arrival with no floor under the
    body when the form is the bird -- it is the one form that can be somewhere
    and stay there without one -- so what this promises instead is that the tile
    is still OPEN after everything else was drawn over it.
    """
    k.g.mark(name, x, y)
    k._claim("clear", "air waypoint '%s' (bird)" % name, x=x, y=y,
             tall=BODY_TILES)
    return name


def _wet_mark(k, name, x, y):
    """A waypoint under water, for the fish: wet rather than standable."""
    k.g.mark(name, x, y)
    k._claim("wet", "swim waypoint '%s' (fish)" % name, x=x, y=y, tall=1)
    return name


# ---------------------------------------------------------------- the level

def nest_3():
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

    # =================================================== 1 -- THE FORGE FLOOR
    # One floor, cols 1..47, shared with the flue's foot.  That continuity is
    # what makes the airlock work and is the whole of the frog's ADR 004.
    k.clear_rect(1, LOW_ROOF + 1, 47, LOW_CAP - LOW_ROOF - 1)   # rows 17..25
    k.floor(1, LOW_CAP, 47, depth=1)
    for x in (2, 12, 28, 34, 46):
        k._claim("stand", "the forge floor at col %d" % x, x=x, y=LOW_STAND,
                 form="human")

    # THE BLADE VAULT.  `nest_crust` (291) declares no `break_hold`, so
    # shouldering does nothing and only the blade opens it -- which is where a
    # weapon-only wall belongs, in the wing of the only form with a weapon.  The
    # cell is sealed on every other side and is off every hop: the prover cannot
    # break a tile at all.
    k.rect(VAULT_X0, LOW_ROOF + 1, CRUST_COL - VAULT_X0 + 1,
           23 - LOW_ROOF, "solid")               # a two-row cell under the rock
    k.clear_rect(VAULT_X0, LOW_STAND - 1, VAULT_X1 - VAULT_X0 + 1, BODY_TILES)
    k.breakable_wall(CRUST_COL, LOW_STAND, BODY_TILES, role="breakable",
                     form="human")

    # THE SHARD TRENCH.  Two tiles of hole, which is three tiles of travel --
    # LIMITS["human"]["gap"] is a distance between stand tiles, not a hole
    # width, and `Kit.reachable_set` enumerates dx <= gap.  A three-tile hole is
    # four tiles of travel: proofs say the human clears it (gap_human_3 PROVED)
    # and the conservative flood every check in this file runs on says she does
    # not, and a filter that cannot cross the level's own first jump reports the
    # whole level as a softlock.  So every hole here is two.
    k.clear_rect(TRENCH_X0, LOW_CAP, TRENCH_W, 2)
    k.rect(TRENCH_X0, LOW_CAP + 2, TRENCH_W, 1, "hazard")
    k.gap(TRENCH_X0, LOW_STAND, TRENCH_W, form="human",
          landing_w=A1_COL - (TRENCH_X0 + TRENCH_W))

    # THE CHAIN and the two shelves it serves.  `can_climb` is true only for the
    # human, so this is the one piece of terrain in the game that is hers: the
    # frog, the bird and the fish all walk straight past it.  Drawn BEFORE the
    # shelves so a later cap cannot bury its top -- THE WATERWAY shipped that
    # bug -- and `audit()` re-checks it after everything else anyway.
    k.climb(CHAIN_COL, SHELF_STAND, LOW_STAND, landing="right")
    k.ledge(CSHELF_X0, SHELF_CAP, CSHELF_X1 - CSHELF_X0 + 1, role="solid")
    k.ledge(LSHELF_X0, SHELF_CAP, LSHELF_X1 - LSHELF_X0 + 1, role="solid")

    # THE BLADE GAP.  Three tiles of air over a six-row drop onto the floor --
    # nothing up here kills you for missing it, it costs you the climb.  The
    # lever is on the far shelf, so the jump and the throw open the same door.
    k.gap(BLADE_GAP_X0, SHELF_STAND, BLADE_GAP_W, form="human",
          landing_w=LSHELF_X1 - LSHELF_X0 + 1)

    # THE STONES.  A group-1 lattice hanging off the chain shelf's own cap,
    # with nothing under it and nothing on it to reach: the point is that the
    # player watches it shift one column when the lever is thrown, so every gold
    # block later in the level is already legible.  Hung from ROCK, which is
    # what lets it exist at all -- `_self_checks` (d) wants a solid tile over
    # every switch tile in every configuration, and a `columns` lattice
    # satisfies that for its own lower rows because each column is one character
    # top to bottom.
    k.switch_lattice(*LATTICE_A, group="a", pattern="columns", phase=1)

    # THE EAST DOOR.  One column of rock from the roof down to the lintel is
    # what makes A1 a door rather than a kerb: at col 23 the only opening is the
    # two rows a body is, so the plug seals it and there is no lip to jump over
    # it by.  Cols 22 and 24 stay open, which is what lets her fall off the east
    # end of the lever's shelf and land in front of the door she just opened.
    k.rect(A1_COL, LOW_ROOF + 1, 1, LOW_STAND - 1 - LOW_ROOF, "block")

    # ========================================================= 2 -- THE FLUE
    # The pier under the head corridor, and the shaft's west shoulder.  Both
    # stop two rows above the floor so the shaft is walked into rather than
    # sealed off -- jungle_4's wall ran to the floor and boxed the spawn in with
    # the whole rest of the level outside it.
    k.rect(BUTTRESS_X0, SECRET_CAP - 4, FLUE_WALL_COL - BUTTRESS_X0 + 1,
           5, "solid")                          # rows 19-23, cols 39-43

    # THE SHOULDER BREAK.  `cracked_stone` carries break_hold 0.35: hold attack
    # and press into it for 0.35 s and it goes.  Every form can, including the
    # two with no weapon -- `FormBase.tick_break` never asks `can_attack`.
    # A cell with a heart, sealed on every other side, and OFF THE ROUTE:
    # tools/solver/sim.gd applies pads, keys, doors and switches and nothing
    # that breaks a tile, so a hop through this plug fails the gate however good
    # the geometry is.
    k.clear_rect(SECRET_X0, SECRET_CAP - BODY_TILES,
                 SECRET_X1 - SECRET_X0 + 1, BODY_TILES)

    # The two shelves of the climb, three rows apart: LIMITS["frog"]["rise"] is
    # 3 because a jump released early is cut to 4.37 tiles and jungle_4's 4-tile
    # rungs caught or dropped the player on rounding.  Each grows off one wall of
    # the shaft, so an overshoot meets the far wall and clings.
    k.ledge(S1_X0, S1_CAP, S1_X1 - S1_X0 + 1, role="solid", stand_form="frog")
    k.ledge(S2_X0, S2_CAP, S2_X1 - S2_X0 + 1, role="solid", stand_form="frog")
    k.breakable_wall(FLUE_WALL_COL, SECRET_CAP - 1, BODY_TILES,
                     role="shoulder", form="frog")

    # THE HEAD CORRIDOR, rows 16-17, cut into the divider, and the flue's own
    # head space east of it.  Two rows, which is a body exactly: there is no arc
    # over `switch_b` in here, so the lever is thrown by anything that walks the
    # corridor and not only by something that lands on it.  Cut BEFORE the lid,
    # which plugs the seam between the two.
    k.clear_rect(CORR_X0, LOW_ROOF, EAST_WALL - CORR_X0, BODY_TILES)
    k.floor(CORR_X0, CORR_CAP, CORR_X1 - CORR_X0 + 1, depth=1)
    # Its west end is sealed, and that seal is load-bearing: one tile of rock at
    # col 25 is the difference between a corridor that always holds `switch_b`
    # and a corridor you can walk off the west end of into the hall below the
    # lid, which is the softlock the 236 dead states were.
    k.rect(B1_COL, LOW_ROOF, 1, BODY_TILES, "block")
    for x in range(CORR_X0, CORR_X1 + 1):
        k._claim("clear", "the head corridor", x=x, y=CORR_STAND,
                 tall=BODY_TILES)

    for (x1, y1, x2, y2) in ((S2_X0, LOW_STAND, S1_X1, S1_CAP - 1),
                             (S1_X1, S1_CAP - 1, S2_X0, S2_CAP - 1),
                             (S2_X0, S2_CAP - 1, CORR_X1, CORR_STAND)):
        what = "flue hop (%d,%d) -> (%d,%d)" % (x1, y1, x2, y2)
        check_rise(y1 - y2, "frog", what)
        check_gap(abs(x2 - x1), "frog", what)
        k._claim("step", what, x1=x1, y1=y1, x2=x2, y2=y2, form="frog")

    # THE CHIMNEY through the divider.  Three columns, so the bird has room to
    # correct inside it, and open to the aerie's floor row above.  It is also
    # the drain: everything the lid seals off still falls back to the lever.
    k.clear_rect(CHIM_X0, UP_CAP, CHIM_X1 - CHIM_X0 + 1, LOW_ROOF - UP_CAP)

    # ======================================================== 3 -- THE AERIE
    k.clear_rect(B1_COL, 1, EAST_WALL - B1_COL, UP_CAP - 1)      # rows 1..13
    k.rect(B1_COL, 1, 1, UP_CAP - 1, "block")                    # the west wall
    # The mid wall.  Without it the aerie's floor is a corridor and the bird
    # walks the whole crossing at 104 px/s for nothing; with it, everything west
    # of col 30 is above row 6, which is flight.
    k.rect(MIDWALL_COL, B1_STAND, 1, UP_CAP - B1_STAND, "solid")
    # THE WEST SHOULDER IS A HOLE, and it is a repair rather than a flourish,
    # made twice.  With a FLOOR here, anything that is not a bird and ends up
    # west of the mid wall is stranded on four tiles six rows under the only
    # perch -- and a body can end up there, because `form_fish.gd` reverts Kaya
    # to human after `air_seconds` 2.6 on the ledge and the human then walks
    # east through an open B1.  `_strand_graph` found that as eight dead states
    # at (26..29,13).  Opened all the way to the HALL it was worse and the same
    # search said so: 236 dead states, because a body that falls to the hall is
    # below the lid and the lid is shut.  So it drops two rows into the head
    # CORRIDOR, which is the one room in the level that always holds the lever
    # that undoes the seal.
    k.clear_rect(WSHAFT_X0, UP_CAP, WSHAFT_X1 - WSHAFT_X0 + 1, LOW_ROOF - UP_CAP)

    # The two perches.  `cloud_deck` checks each hop against the largest this
    # project has ever PROVED -- 6 across and 5 up, proofs/jungle_4.tape.json --
    # rather than against a model, and refuses a perch under two tiles wide
    # because the bird's hitbox is 12 px at 104 px/s.
    perch_names = k.cloud_deck([PERCH_1, PERCH_2], width=PERCH_W, mark="perch")

    # The group-2 lattice, hung from its own lintel in the aerie's east corner
    # where nothing has to fly through it.  It is in whatever state the frog's
    # throw left it, which is the second half of the lesson the forge floor's
    # stones started.
    k.rect(LATTICE_B[0], LATTICE_B[1] - 1, LATTICE_B[2], 1, "block")
    k.switch_lattice(*LATTICE_B, group="b", pattern="columns", phase=0)

    # ======================================================= 4 -- THE QUENCH
    # The bird's landing, drawn before the cistern so the cistern's carve cannot
    # eat it, and capped at row 7 -- the water's own surface row -- so the step
    # off it is a step down into water and not a dive into rock.
    k.clear_rect(LEDGE_X0, 1, LEDGE_X1 - LEDGE_X0 + 1, SURFACE - 1)
    k.floor(LEDGE_X0, SURFACE, LEDGE_X1 - LEDGE_X0 + 1, depth=1)

    # Seven tiles of still water under six of air.  `flooded_chamber` refuses
    # water less than two tiles deep -- one tile puts a fish's head in the
    # surface and its belly on the bed -- and refuses a chamber flooded to its
    # own ceiling, because the fish has to be able to surface.  `bed=False`: the
    # bed is the divider, already obsidian, and the kit's bed is nest_plate.
    k.flooded_chamber(CIST_X0, CIST_TOP, CIST_X1 - CIST_X0 + 1,
                      UP_CAP - CIST_TOP, surface=SURFACE, wall=False, bed=False)

    # THE SLUICE WALL.  Solid from row 4 -- three rows above the surface, so
    # there is no swimming over it -- down to the bed, with one window in it.
    k.rect(A2_COL, 4, 1, UP_CAP - 4, "block")

    # THE BANK.  One tile, because surface_hop -210 against gravity 900 clears
    # 24.5 px and there is no argument that gets you two; `depth=1` so the water
    # runs on UNDERNEATH it and the west basin stays one body of water rather
    # than two wells the fish cannot swim between.
    k.bank(BANK_X0, SURFACE + 1, BANK_W, rise=1, depth=1)

    # THE SUBMERGED STEP, which is the human's half of ADR 004 and the half this
    # project has got wrong twice.  A bank flush with `water_top` is a bank the
    # FISH hops (one tile, 24.5 px) and a wall the HUMAN cannot climb: her water
    # jump is jump_vel -260 * water_jump_scale 0.78 against gravity 760 *
    # water_gravity_scale 0.3, and it keeps the water's gravity only while her
    # upper body is still wet, which makes the rise 0.7*(feet - surface - 10) +
    # 27 px.  From the cistern's own bed that lands her under the lip -- this
    # project has measured that at 0.0 px of closest approach.  From a step
    # whose top is row 9, two tiles under the surface, her feet start at y=144
    # against a surface at y=112 and the jump is 42.4 px: she clears the row-7
    # cap by ten.  `oneway`, so the water stays ONE body and the fish is never
    # shut under or over it.
    k.rect(STEP_X0, STEP_ROW, STEP_W, 1, "oneway")
    k._claim("stand", "the cistern's submerged step, which is how a human who "
             "fell in gets out", x=STEP_X0, y=STEP_ROW - 1, form="human")

    # --------------------------------------------------------------- the doors
    for col, solid_when, group, top, stand, why in PLUGS:
        _plug(k, col, top, stand, group, solid_when, why)

    # -------------------------------------------------------------- dressing
    # The open halls get `nest_void` behind them and the cut rooms keep the dark
    # `nest_wall`, so everything the level opens out into reads as depth and
    # everything cut into the rock reads as interior.  The flues hang from the
    # roofs and stop there -- a dark column running floor to ceiling beside a
    # climbable chain is "looks like a passage, behaves like a wall" with its
    # coat inside out, which nest_1's captures caught.
    k.rect(1, LOW_ROOF + 1, 20, LOW_CAP - LOW_ROOF - 1, "void", "bg")
    k.rect(B1_COL + 1, 1, EAST_WALL - B1_COL - 1, UP_CAP - 1, "void", "bg")
    k.rect(CIST_X0, SURFACE, CIST_X1 - CIST_X0 + 1, UP_CAP - SURFACE,
           "void", "bg")
    # Flues hang from a roof and stop there.  The first capture of the aerie was
    # a black rectangle with two ledges in it: eleven rows of open sky with
    # nothing to measure it against reads as a hole rather than a chamber, and
    # a bird crossing it has no way to tell how far it has got.  These are the
    # ruler.  All of it is `bg`, so none of it carries a flag and none of it
    # changes what tools/prove.sh proved.
    for fx in (7, 14, 21):
        k.rect(fx, LOW_ROOF + 1, 1, 4, "decor", "bg")
    for fx in (26, 31, 37):
        k.rect(fx, CORR_CAP + 1, 1, 4, "decor", "bg")
    for (fx, fh) in ((28, 5), (33, 3), (37, 6), (42, 4), (46, 3)):
        k.rect(fx, 1, 1, fh, "decor", "bg")

    # ------------------------------------------------------------- the light
    for x, y in VEINS:
        if Probe(g).solid(x, y):
            raise world_kit.WorldKitError(
                "vein at (%d,%d) is behind solid rock ('%s'): nothing will ever "
                "see it" % (x, y, g.fg[y][x]))
        g.put(x, y, "r", "bg")
    _hot(k)

    # -------------------------------------------------------------- entities
    g.ent("player_spawn", *SPAWN)
    g.ent("switch_a", *SWITCH_A)
    g.ent("pad_human", *PAD_HUMAN_LOW)
    g.ent("pad_frog", *PAD_FROG_LOW)
    g.ent("switch_b", *SWITCH_B)
    g.ent("pad_bird", *PAD_BIRD)
    g.ent("pad_fish", *PAD_FISH)
    g.ent("pad_human", *PAD_HUMAN_BANK)
    g.ent("exit", *EXIT_TILE)

    # Four enemies, one per wing, none of them on a route tile.
    # walker.json is 32 px/s with `turn_at_ledge`, so it is pinned to the shelf
    # it spawns on: this one paces the landing east of the shard trench, which
    # is the reason to have the blade in your hand coming out of the jump.
    g.ent("enemy_walker", CSHELF_X1 + 1, LOW_STAND)
    # The flue's foot, under the first shelf: something to leave behind rather
    # than something to fight on a two-tile ledge.
    g.ent("enemy_jumper", 33, LOW_STAND)
    # flyer.json has no chase at all, so one on Y in the aerie's dead east air
    # guards the corner lattice and never crosses the perches.
    g.ent("enemy_flyer", 41, 8, axis="y", range=40)
    # The east basin, off the dive line and west of the sluice's mouth.
    g.ent("enemy_swimmer", 17, 11)

    # NO GEM SHARES A TILE WITH A LEVER OR A PAD: Pickup draws over the
    # trigger's sprite, and nest_2's first captures lost switch_b behind one.
    g.ent("heart", VAULT_X0 + 1, LOW_STAND)          # behind the crust
    g.ent("heart", SECRET_X0 + 1, SECRET_CAP - 1)    # behind the shoulder plug
    g.ent("heart", CSHELF_X0 + 2, SHELF_STAND)
    for (x, y) in [(9, LOW_STAND), (14, LOW_STAND), (28, LOW_STAND),
                   (34, LOW_STAND), (46, LOW_STAND),
                   (LSHELF_X1, SHELF_STAND), (S1_X0, S1_CAP - 1),
                   (S2_X1, S2_CAP - 1), (CORR_X0 + 1, CORR_STAND),
                   (32, PERCH_1[1] - 1), (27, PERCH_2[1] - 1),
                   (45, UP_STAND), (33, UP_STAND),
                   (19, 5), (9, 4), (14, 11), (5, 11)]:
        g.ent("gem", x, y)

    # ----------------------------------------------------- the route (ADR 005)
    # Twenty-four short hops rather than four long ones, and that is the
    # prover's arithmetic rather than caution: the budget is 50,000 expansions
    # PER HOP and a greedy frontier dives into whatever hole lies between it and
    # the goal, so a hop spanning a whole wing is a hop that spends its budget
    # learning the shape of the room.
    #
    # There is exactly one `switch_a` and one `switch_b`, so both are waypoints
    # the route can NAME -- which is not a convenience: the foundation measured
    # the same crossing at 13 expansions named and 19,227 unnamed, because a
    # named lever cuts the hop at the tile where the world changes instead of
    # asking one search to find a gate, a lever and the far side of the gate at
    # once.
    k.mark("m_chain_foot", CHAIN_COL, LOW_STAND)
    k.mark("m_shelf_c", CSHELF_X0 + 1, SHELF_STAND)
    # Two tiles west of the chain's top, not on it.  A hop seam AT a ladder top
    # makes the prover reject its own tape: `ProverSearch._set_input` derives
    # jump and climb edges from the PREVIOUS macro and there is none at the
    # start of a hop, so a held `up` reads as a fresh press and the search comes
    # out a whole tile above the replay.  tests/fixtures/world_kit/
    # deeps_tunnel_seam.json is that bug, committed.  Ending the climbing hop
    # out on the shelf gives the walk two tiles to release the button in.
    k.mark("m_gate_w", A1_COL - 1, LOW_STAND)
    k.mark("m_lock", PAD_HUMAN_LOW[0], LOW_STAND)
    k.mark("m_flue_foot", S2_X0, LOW_STAND, form="frog")
    k.mark("m_s1", S1_X1, S1_CAP - 1, form="frog")
    k.mark("m_s2", S2_X0, S2_CAP - 1, form="frog")
    k.mark("m_head_e", CORR_X1, CORR_STAND, form="frog")
    _air_mark(k, "m_air", CHIM_X0 + 1, UP_STAND)
    _wet_mark(k, "m_dive", 19, 9)
    _wet_mark(k, "m_sluice_e", A2_COL + 1, A2_STAND - 1)
    _wet_mark(k, "m_sluice_w", A2_COL - 1, A2_STAND - 1)
    _wet_mark(k, "m_surface", 3, SURFACE + 1)
    k.mark("m_bank", BANK_X0, SURFACE - 1, form="fish")
    # Two `pad_human` entities, so the type names no waypoint on its own --
    # gen_levels.Grid._waypoints refuses a type there are several of -- and the
    # pad carries a mark on its own tile instead.  Standing on that tile is what
    # fires the pad (TransformPad's box is the lower half of it grown by 3 px),
    # so the hop that arrives is the hop that transforms, and prove.gd checks
    # the next hop's declared form against what actually happened.
    k.mark("m_bank_pad", *PAD_HUMAN_BANK)

    g.route("spawn", "m_chain_foot", form="human")      # over the shard trench
    g.route("m_chain_foot", "m_shelf_c", form="human")  # up the chain
    g.route("m_shelf_c", "switch_a", form="human")      # the blade gap, jumped
    g.route("switch_a", "m_gate_w", form="human")       # off the shelf's east end
    g.route("m_gate_w", "m_lock", form="human")         # through A1, over x=400
    g.route("m_lock", "pad_frog", form="human")         # the airlock
    g.route("pad_frog", "m_flue_foot", form="frog")
    g.route("m_flue_foot", "m_s1", form="frog")         # 3 up
    g.route("m_s1", "m_s2", form="frog")                # 3 up, 3 across
    g.route("m_s2", "m_head_e", form="frog")            # up through the open lid
    g.route("m_head_e", "switch_b", form="frog")        # thrown by the body:
                                                        # B2 shuts, B1 opens
    g.route("switch_b", "pad_bird", form="frog")
    g.route("pad_bird", "m_air", form="bird")           # up the chimney
    g.route("m_air", "perch_1", form="bird")
    g.route("perch_1", "perch_2", form="bird")
    g.route("perch_2", "pad_fish", form="bird")         # through B1, over x=400
    g.route("pad_fish", "m_dive", form="fish")
    g.route("m_dive", "m_sluice_e", form="fish")
    g.route("m_sluice_e", "m_sluice_w", form="fish")    # through A2
    g.route("m_sluice_w", "m_surface", form="fish")
    g.route("m_surface", "m_bank", form="fish")         # the one-tile bank
    g.route("m_bank", "m_bank_pad", form="fish")
    g.route("m_bank_pad", "exit", form="human")
    assert perch_names == ["perch_1", "perch_2"], perch_names
    return g, k


AMBIENCE = {
    "_note": (
        "FOUR SHAPES. The working floor of the nest, and the one level in the "
        "world that is lit in four different rooms at once. EMBER is the room "
        "everywhere: the forge floor is the hottest thing in the level and the "
        "quench the coldest, which is the `bg_tint` doing the work rather than "
        "a second alpha. GOLD is reserved for what a throw moves or what you "
        "act on -- the two levers, and each of the four doors they move -- so "
        "the player can read the machine off the light. No `darkness` key: the "
        "dark is World 4's verb and this world's is the lever. The two "
        "emissive entries are the level's own light and both are SOLID, "
        "because AmbienceLayer._collect_emissive scans the fg: 281 "
        "obsidian_hot is the heat `_hot()` bands around every nest_vein, and "
        "287 nest_shard is the trench, which glows for the reason deeps_1's "
        "spore does -- a hazard you cannot see is a coin toss. 289 nest_vein "
        "is NOT in here: it is a background tile by its own art and emits "
        "nothing from back there, which is the point."),
    "world": "obsidian",
    "air": {"ramp": "ember", "step": 1, "alpha": 0.26},
    "bg_tint": {"ramp": "ember", "step": 2, "mix": 0.66, "scale": 0.52},
    "fg_tint": {"ramp": "ember", "step": 5, "mix": 0.16, "scale": 0.93},
    "vignette": 0.34,
    "lights": [
        # the two levers
        {"x": 8, "y": 19, "radius": 64, "ramp": "gold", "step": 5,
         "intensity": 0.48, "flicker": 0.18},
        {"x": 39, "y": 17, "radius": 64, "ramp": "gold", "step": 5,
         "intensity": 0.48, "flicker": 0.18},
        # the four doors they move
        {"x": 23, "y": 24, "radius": 56, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 12, "y": 11, "radius": 60, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 44, "y": 16, "radius": 56, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 25, "y": 5, "radius": 60, "ramp": "gold", "step": 6,
         "intensity": 0.50, "flicker": 0.10},
        # ember: the things that are always true -- the chain, the chimney, the
        # perches, the bank
        {"x": 17, "y": 22, "radius": 72, "ramp": "ember", "step": 5,
         "intensity": 0.30},
        {"x": 36, "y": 15, "radius": 72, "ramp": "ember", "step": 4,
         "intensity": 0.30},
        {"x": 32, "y": 10, "radius": 64, "ramp": "ember", "step": 4,
         "intensity": 0.24},
        {"x": 27, "y": 6, "radius": 64, "ramp": "ember", "step": 4,
         "intensity": 0.24},
        {"x": 42, "y": 22, "radius": 64, "ramp": "ember", "step": 4,
         "intensity": 0.26},
        {"x": 5, "y": 25, "radius": 72, "ramp": "ember", "step": 5,
         "intensity": 0.32},
        {"x": 6, "y": 6, "radius": 72, "ramp": "ember", "step": 6,
         "intensity": 0.34},
    ],
    "emissive": {
        "281": {"ramp": "ember", "step": 5, "intensity": 0.18, "radius": 24},
        "287": {"ramp": "ember", "step": 6, "intensity": 0.32, "radius": 26,
                "lift": 5},
    },
}


## Route hops allowed to change screen without being a flat walk, and why.
SEAM_EXEMPT = {
    ("pad_bird", "m_air"):
        "flown, straight up the middle of a three-column chimney. The 0.12 s "
        "flip freeze at y=240 leaves the bird in the same column with nothing "
        "to miss, which is why the hand-off from the frog to the bird is a "
        "chimney rather than a staircase.",
    ("perch_2", "pad_fish"):
        "flown, out through the aerie's west door and across x=400 in open "
        "air. Both ends are standable ledges on the same row and the landing "
        "is three tiles wide, so the freeze happens mid-glide with somewhere "
        "to put her down.",
}

## Entries `reconfig_check` is run from: every room a shut gate makes, and both
## sides of each one, plus every pad.  Each is swept over all four
## configurations by reconfig_check itself.  Every one stands on ROCK rather
## than on a switch block -- an entry the flood cannot legally stand in reports
## an empty room instead of a trap.
##
## The GOAL is per-room, for the reason nest_2 records at length: B1 and B2 are
## one group in opposite senses, so no single configuration opens the level end
## to end and asking any room for the exit would fail a level that is perfectly
## playable.  The end-to-end question is `_strand_graph` in (g).
##
## reconfig_check refuses the bird and the fish by name -- a ground flood would
## understate one and overstate the other -- so the quench and the aerie are
## absent here and answered by (g), which floods per form.
RECONFIG_ENTRIES = [
    ("the forge floor (spawn)", SPAWN, SWITCH_A),
    ("the lever's shelf, at switch_a", SWITCH_A, (CSHELF_X0, SHELF_STAND)),
    ("the chain's landing", (CSHELF_X0, SHELF_STAND), SWITCH_A),
    ("the forge floor, east of the trench", (A1_COL - 1, LOW_STAND), SWITCH_A),
    ("the flue's foot, east of A1", PAD_HUMAN_LOW, SWITCH_A),
    ("the flue's first shelf", (S1_X1, S1_CAP - 1), SWITCH_A),
    ("the flue's second shelf", (S2_X0, S2_CAP - 1), SWITCH_B),
    ("the head corridor, above the lid", SWITCH_B, SWITCH_B),
    ("the head corridor, at pad_bird", PAD_BIRD, SWITCH_B),
]

## data/forms/*.json hitbox h, for check (h): a body resting on its tile's floor
## spans [16 - h, 16] of that tile, and the trigger box is [6, 16].
HITBOX_H = {"human": 22, "frog": 11, "bird": 9, "fish": 9}
SWITCH_BOX_INSET, SWITCH_BOX_SIZE = (1, 6), (14, 10)

FORMS = ("human", "frog", "bird", "fish")


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
        elif e["type"] in ("pad_frog", "pad_bird", "pad_fish"):
            where.setdefault(e["type"], {"x": e["x"], "y": e["y"]})
    return where


def _switch_tiles(g):
    """Every switch-block tile in the grid, as (x, y, char)."""
    chars = {NEST_W5.char(r) for r in
             ("switch_a_on", "switch_a_off", "switch_b_on", "switch_b_off")}
    return [(x, y, g.fg[y][x])
            for y in range(g.h) for x in range(g.w)
            if g.fg[y][x] in chars]


class _Nav:
    """Movement per form, per configuration, over the finished grid.

    Deliberately the same shape as tools/reachability.py -- the model this
    project's own validator uses -- with three things it has no concept of: the
    switch configuration, the fish's revert, and the rule that a lever is only
    thrown FROM ITS OWN TILE.  That last one is the conservative direction:
    generosity about escaping is the one way a stranding check must not be
    wrong.
    """

    def __init__(self, g, pads, levers):
        self.g = g
        self.pads = pads                      # (x, y) -> form
        self.levers = levers                  # (x, y) -> group
        self.probe = {(c[1], c[2]): Probe(g, switches={1: c[1], 2: c[2]})
                      for c in [(0, a, b) for a in (True, False)
                                for b in (True, False)]}

    def _ground(self, p, x, y, form):
        rise, gap = LIMITS[form]["rise"], LIMITS[form]["gap"]
        out = [(x - 1, y), (x + 1, y)]
        if p.ladder(x, y) and form == "human":
            out += [(x, y - 1), (x, y + 1)]
        if p.water(x, y):
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

    def _swim(self, p, x, y):
        if not p.water(x, y):
            # Out of water it flops one tile and falls, which is `_ground` with
            # the fish's own measured limits.
            return self._ground(p, x, y, "fish")
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if (0 <= nx < self.g.w and 0 <= ny < self.g.h
                        and p.water(nx, ny) and p.clear(nx, ny)):
                    out.append((nx, ny))
        # The bank: one tile of rise, and only out of the surface.
        if not p.water(x, y - 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y - 1
                if (0 <= nx < self.g.w and ny >= 0
                        and p.standable(nx, ny) and not p.hazard(nx, ny)):
                    out.append((nx, ny))
        return out

    def successors(self, state):
        x, y, form, cfg = state
        p = self.probe[cfg]
        out = []
        for (px, py), pform in self.pads.items():
            if abs(px - x) <= 1 and abs(py - y) <= 1 and pform != form:
                out.append((x, y, pform, cfg))
        if (x, y) in self.levers:
            grp = self.levers[(x, y)]
            out.append((x, y, form,
                        (not cfg[0], cfg[1]) if grp == 1 else (cfg[0], not cfg[1])))
        if form == "fish" and not p.water(x, y):
            out.append((x, y, "human", cfg))     # form_fish.gd, air_seconds 2.6
        if form == "bird":
            moves = self._fly(p, x, y)
        elif form == "fish":
            moves = self._swim(p, x, y)
        else:
            moves = self._ground(p, x, y, form)
        return out + [(nx, ny, form, cfg) for (nx, ny) in moves]


def _strand_graph(g, start, goal):
    """(where x which form x which switches), flooded forward then backward.

    nest_1's `_escape` and nest_2's adaptation of it search (where x switches)
    as the human.  With four forms and one-way pads the form is part of the
    state, so this is that search with the form in the key and each form's own
    movement on the edges.  See ADR 004 in the docstring.

    Returns (reachable, dead_ends): every state the player can get into, and
    every one of those from which the exit is no longer reachable.
    """
    pads = {(int(e["x"]), int(e["y"])): e["type"][4:]
            for e in g.entities if e["type"].startswith("pad_")}
    levers = {(int(e["x"]), int(e["y"])): (1 if e["type"].endswith("a") else 2)
              for e in g.entities if e["type"] in ("switch_a", "switch_b")}
    nav = _Nav(g, pads, levers)

    root = (start[0], start[1], "human", (START_CFG[1], START_CFG[2]))
    seen, back, q = {root}, {}, deque([root])
    while q:
        s = q.popleft()
        for n in nav.successors(s):
            back.setdefault(n, []).append(s)
            if n not in seen:
                seen.add(n)
                q.append(n)

    wins = [s for s in seen if (s[0], s[1]) == tuple(goal)]
    good, q = set(wins), deque(wins)
    while q:
        s = q.popleft()
        for prev in back.get(s, ()):
            if prev in seen and prev not in good:
                good.add(prev)
                q.append(prev)
    return seen, sorted(seen - good)


def _self_checks(g, k, verbose=True):
    p = Probe(g)
    bad = []
    where = _waypoints(g)
    flags = world_kit.tiles().flags_of_char

    # (a) A standable tile with one tile of headroom reads as a passage and
    # behaves as a wall (defect 2).  tests/test_level_validity.gd checks exactly
    # this; catching it here costs milliseconds instead of a Godot boot.
    for y in range(g.h):
        for x in range(g.w):
            if p.solid(x, y):
                continue
            if not (p.solid(x, y + 1) or p.oneway(x, y + 1)):
                continue
            if p.clear(x, y, BODY_TILES):
                continue
            for dx in (-1, 1):
                if not p.solid(x + dx, y) and p.clear(x + dx, y, BODY_TILES):
                    bad.append("(%d,%d) is standable with one tile of headroom "
                               "and reachable from beside it" % (x, y))
                    break

    # (b) Everything the player must touch needs a body's worth of room over it,
    # and nothing stands on a floor the screen it is drawn on does not contain.
    must = {"exit", "player_spawn", "switch_a", "switch_b", "gem", "heart",
            "pad_frog", "pad_bird", "pad_fish", "pad_human"}
    for e in g.entities:
        if e["type"] not in must:
            continue
        x, y = e["x"], e["y"]
        if not p.clear(x, y, BODY_TILES):
            bad.append("%s at (%d,%d) has no two tiles of headroom"
                       % (e["type"], x, y))
        if (p.solid(x, y + 1) or p.oneway(x, y + 1)) and (y + 1) % 15 == 0:
            bad.append("%s at (%d,%d) stands on cap row %d, a screen boundary: "
                       "its centre lands on the screen above and the floor is "
                       "never drawn" % (e["type"], x, y, y + 1))
    for kind, c in k.claims:
        if kind == "stand" and (c["y"] + 1) % 15 == 0:
            bad.append("%s: stand row %d sits on cap row %d, a screen boundary"
                       % (c["why"], c["y"], c["y"] + 1))

    # (c) NO ON-FOOT HOP CROSSES A SCREEN SEAM MID-JUMP.  A human or frog hop
    # whose ends are on different screens has to be a flat walk along unbroken
    # standable floor; a bird or fish hop across one has to be named in
    # SEAM_EXEMPT with a reason.  The camera freezes the sim for the length of
    # every flip, and a freeze in mid-air is the feel defect neither prove.sh
    # nor the tape replay can see.
    for hop in g.hops:
        a, b = where.get(hop["from"]), where.get(hop["to"])
        if a is None or b is None:
            bad.append("route hop '%s' -> '%s' names a waypoint this module "
                       "cannot locate" % (hop["from"], hop["to"]))
            continue
        if _screen(a["x"], a["y"]) == _screen(b["x"], b["y"]):
            continue
        key = (hop["from"], hop["to"])
        if hop["form"] in ("bird", "fish"):
            if key not in SEAM_EXEMPT:
                bad.append("route hop '%s' -> '%s' is flown or swum across a "
                           "screen seam and is not named in SEAM_EXEMPT" % key)
            continue
        if key in SEAM_EXEMPT:
            continue
        if a["y"] != b["y"]:
            bad.append("on-foot route hop '%s' -> '%s' changes screen and "
                       "changes row: make it a flat walk or justify it" % key)
            continue
        for x in range(min(a["x"], b["x"]), max(a["x"], b["x"]) + 1):
            if not p.standable(x, a["y"]):
                bad.append("on-foot route hop '%s' -> '%s' crosses a screen "
                           "seam and (%d,%d) is not standable, so it is a jump "
                           "and not a walk"
                           % (hop["from"], hop["to"], x, a["y"]))
                break

    # (d) NO SWITCH BLOCK IS EVER A FLOOR -- nest_2's check, copied because it
    # is the strongest form of the rule a grid can carry.  tools/reachability.py
    # resolves a switch tile as never solid, so a route that stands on one is a
    # route it reports as missing in every configuration.  Every switch tile has
    # rock, or the rest of its own plug, directly over its head, checked with
    # the switches resolved BOTH ways -- "solid" is a property of a
    # configuration and "has rock above it" is not.
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

    # (e) THE FOUR DOORS DO WHAT THE DOCSTRING SAYS, re-derived from the grid.
    # Each plug is solid in exactly the configurations its own table row claims,
    # and -- the load-bearing pair -- B1 and B2 are never open together, which
    # is what makes the frog's throw a commitment.
    for col, solid_when, group, top, stand, why in PLUGS:
        grp = 1 if group == "a" else 2
        for on in (True, False):
            cfg = dict(START_CFG)
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
    for cfg in CFGS:
        pr = Probe(g, switches=cfg)
        if not pr.solid(B2_COL, CORR_STAND) and not pr.solid(B1_COL, B1_STAND):
            bad.append("with group 2 %s both the flue's lid and the aerie's "
                       "door are open, so the frog's throw costs nothing and "
                       "the commitment is decoration"
                       % ("ON" if cfg[2] else "OFF"))

    # ... and neither lever is decoration: the exit is not reachable on foot
    # from the spawn before a throw, and switch_a alone does not open the way.
    start_flood = k.reachable_set(SPAWN, form="human", switches=START_CFG)
    if PAD_FROG_LOW in start_flood:
        bad.append("the frog pad is reachable from the spawn with A1 shut: "
                   "switch_a is decoration")
    if SWITCH_A not in start_flood:
        bad.append("switch_a is not reachable from the spawn before any throw, "
                   "so the level cannot be started")

    # (f) EVERY GATE'S LEVER IS IN A DIFFERENT WING FROM AT LEAST ONE OF ITS
    # DOORS.  That is the braid, and it is the claim in the docstring most
    # likely to rot silently.
    wings = {"forge": (1, 24, 16, 28), "flue": (25, 47, 16, 28),
             "aerie": (25, 47, 1, 15), "quench": (1, 24, 1, 15)}

    def wing_of(x, y):
        for name, (x0, x1, y0, y1) in wings.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return name
        return "?"

    lever_wing = {}
    for e in g.entities:
        if e["type"] in ("switch_a", "switch_b"):
            lever_wing[1 if e["type"].endswith("a") else 2] = \
                wing_of(e["x"], e["y"])
    served = {1: set(), 2: set()}
    for x, y, ch in _switch_tiles(g):
        grp = int(flags[ch]["switch_group"])
        served[grp].add(wing_of(x, y))
    for grp, wset in served.items():
        home = lever_wing.get(grp)
        if not (wset - {home}):
            bad.append("group %d has its lever in the %s wing and every one of "
                       "its blocks in that same wing: the braid is gone"
                       % (grp, home))

    # (g) NO STATE THE PLAYER CAN REACH IS A DEAD END -- ADR 004, over
    # (where x which form x which switches).  See the docstring.
    seen, dead = _strand_graph(g, SPAWN, EXIT_TILE)
    if EXIT_TILE not in {(s[0], s[1]) for s in seen}:
        bad.append("the exit at %s is not reachable from the spawn at all "
                   "(%d states explored)" % (EXIT_TILE, len(seen)))
    elif dead:
        show = "; ".join("(%d,%d) as the %s with group1=%s group2=%s"
                         % (s[0], s[1], s[2], s[3][0], s[3][1])
                         for s in dead[:6])
        bad.append("ADR 004: %d of %d reachable states can no longer reach the "
                   "exit -- %s%s" % (len(dead), len(seen), show,
                                     " ..." if len(dead) > 6 else ""))

    # (h) ONE LEVER PER GROUP -- nest_1's measured hard rule -- and a trigger
    # box every one of the four bodies covers.  SwitchTrigger.aabb() is
    # Rect2(tile*16 + (1,6), (14,10)); a body resting on the tile's floor spans
    # [16-h, 16] of the tile, and h comes from data/forms/*.json.
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
                           "box is the bottom 10 px of the tile and nothing can "
                           "stand in it" % (t, sx, sy))
            box_top, box_bot = SWITCH_BOX_INSET[1], SWITCH_BOX_INSET[1] + \
                SWITCH_BOX_SIZE[1]
            for form, hb in sorted(HITBOX_H.items()):
                if 16 - hb >= box_bot:
                    bad.append("%s at (%d,%d): a %s resting on the tile spans "
                               "%d..16 and the box is %d..%d -- that form "
                               "cannot throw it by body, and three of the four "
                               "have no other way"
                               % (t, sx, sy, form, 16 - hb, box_top, box_bot))

    # (i) NO BREAKABLE IS ON THE ROUTE.  `ProverSearch.action_set()` has no
    # ATTACK in it and `ProverSim.snapshot()` carries no broken-tile set, so a
    # hop through a breakable fails the gate however good the geometry is.
    breakables = {(x, y) for y in range(g.h) for x in range(g.w)
                  if flags.get(g.fg[y][x], {}).get("breakable")}
    for hop in g.hops:
        a, b = where.get(hop["from"]), where.get(hop["to"])
        if a is None or b is None:
            continue
        x0, x1 = sorted((a["x"], b["x"]))
        y0, y1 = sorted((a["y"], b["y"]))
        for (bx, by) in breakables:
            if x0 <= bx <= x1 and y0 - 2 <= by <= y1:
                bad.append("route hop '%s' -> '%s' passes the breakable at "
                           "(%d,%d); the prover cannot open one"
                           % (hop["from"], hop["to"], bx, by))

    # (j) Every vein is still a vein, still on the BACKGROUND, still in open
    # air, and still has the obsidian_hot band `_hot()` owes it -- a bg tile
    # emits nothing and 281 is what does.
    hot = NEST_W5.char("solid_alt")
    for x, y in VEINS:
        if g.bg[y][x] != "r":
            bad.append("vein at (%d,%d) is '%s' on the bg, not 'r' -- something "
                       "was drawn over the level's light" % (x, y, g.bg[y][x]))
            continue
        if p.solid(x, y):
            bad.append("vein at (%d,%d) is behind solid rock" % (x, y))
        if not any(p.ch(x + dx, y + dy) == hot
                   for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))):
            bad.append("vein at (%d,%d) has no obsidian_hot beside it, so the "
                       "one thing that can emit there does not" % (x, y))

    # (k) THE BIRD'S STAMINA.  `flap_cost` 12 against `max_stamina` 100 is eight
    # flaps and `stamina_regen` only tops up while gliding or perched, so a run
    # of bird hops with no perch under it has to stay under
    # world_kit.BIRD_HOPS_PER_PERCH.
    perches = {(PERCH_1[0] + PERCH_W // 2, PERCH_1[1] - 1),
               (PERCH_2[0] + PERCH_W // 2, PERCH_2[1] - 1)}
    run = 0
    for hop in g.hops:
        if hop["form"] != "bird":
            run = 0
            continue
        run += 1
        b = where.get(hop["to"])
        if b is not None and (b["x"], b["y"]) in perches:
            run = 0
        if run > world_kit.BIRD_HOPS_PER_PERCH:
            bad.append("%d bird hops with no perch to refill on; the bar is "
                       "eight flaps" % run)

    if bad:
        raise world_kit.WorldKitError(
            "%s: %d self-check failure(s):\n  %s"
            % (LEVEL_ID, len(bad), "\n  ".join(bad)))
    if verbose:
        print("  self-checks  (a) pockets (b) headroom + seam rows (c) seam hops")
        print("               (d) no switch block is ever a floor, in either "
              "resolution")
        print("               (e) four doors, B1/B2 never both open, switch_a "
              "load-bearing")
        print("               (f) both levers serve a wing that is not their "
              "own")
        print("               (g) ADR 004: %d (tile, form, config) states "
              "reachable, 0 dead ends" % len(seen))
        print("               (h) one lever per group, box covered by all four "
              "bodies")
        print("               (i) %d breakables, none on the route  (j) %d "
              "veins lit" % (len(breakables), len(VEINS)))
        print("               (k) bird hops per perch within the eight-flap bar")
    return len(seen)


def _reconfig(k, entry, goal, label, states, verbose=True):
    """`reconfig_check`, with the two answers it does not know about admitted.

    Its second question is "in every configuration reachable from here, is at
    least one SWITCH reachable".  That is the right question almost everywhere
    and it is the wrong one twice in this level, for two different reasons, and
    both of them are the point of the level rather than excuses for it:

    1. IT FLOODS AS ONE FORM.  `reachable_set` refuses the bird and the fish by
       name and has no concept of a transform pad, so asked about the flue it
       answers for a human standing where only a frog can be.  With group 1 ON
       the human's flood east of A1 finds no lever, because the only lever up
       there is `switch_b` at the top of a frog-only climb.

    2. IT FLOODS CONFIGURATIONS THE PLAYER CANNOT BE IN.  Group 1 can only
       return to ON by touching `switch_a`, which is WEST of A1, so no body is
       ever east of A1 with A1 shut.  `_strand_graph` -- which does carry the
       form and does only flip a lever from its own tile -- says so, and this
       helper asks it rather than asserting it: a stranded configuration is
       admitted only when no reachable state in the whole level stands at this
       entry in that configuration.

    Anything else is re-raised untouched.  Adapted from nest_2's helper, which
    made the same kind of admission for its own reason.
    """
    try:
        sizes = k.reconfig_check(entry, goal, form="human")
        if verbose:
            print("  reconfig     %-38s %s" % (label, sizes))
        return sizes
    except world_kit.WorldKitError as err:
        if "no switch is reachable" not in str(err) or "not reachable in ANY" in str(err):
            raise
        unreal, wins, sizes = [], [], {}
        for cfg in CFGS:
            seen = k.reachable_set(entry, form="human", switches=cfg)
            key = (cfg[1], cfg[2])
            sizes[key] = len(seen)
            if any((sx + dx, sy) in seen
                   for (sx, sy) in (SWITCH_A, SWITCH_B)
                   for dx in (-1, 0, 1)):
                continue
            if EXIT_TILE in seen:
                wins.append(key)                  # the way out, not a trap
            elif not any(st[0] == entry[0] and st[1] == entry[1]
                         and st[3] == key for st in states):
                unreal.append(key)                # nobody can ever be here
            else:
                raise
        if verbose:
            note = []
            if wins:
                note.append("%s reach the EXIT and no lever" % (wins,))
            if unreal:
                note.append("%s are configurations no body can be in here"
                            % (unreal,))
            print("  reconfig     %-38s %s  (%s)"
                  % (label, sizes, "; ".join(note)))
        return sizes


def check(g, k, verbose=True):
    """Everything the kit can say about this level before the prover runs.

    Not proof -- `tools/prove.sh` is.  This is the fast filter for the class of
    error this project has shipped six times, plus the question the prover
    structurally cannot answer: whether a configuration the player is allowed to
    leave the machine in has sealed them out of it.
    """
    states, _dead = _strand_graph(g, SPAWN, EXIT_TILE)
    for label, entry, goal in RECONFIG_ENTRIES:
        _reconfig(k, entry, goal, label, states, verbose=verbose)
    return k.audit(strict_verbs=True)


def main():
    g, k = nest_3()
    missing = k.pal.missing()
    if missing:
        raise SystemExit("palette has unresolved roles: %s" % (missing,))
    for line in check(g, k):
        print(line)
    _self_checks(g, k)
    print("  palette      missing=%s substituted=%s"
          % (NEST_W5.missing() or "none", NEST_W5.substituted or "none"))
    write(LEVEL_ID, g, LEVEL_NAME, music="world5")
    print("--- data/ambience.json  levels[\"%s\"] ---" % LEVEL_ID)
    print(json.dumps(AMBIENCE, indent=6))


if __name__ == "__main__":
    main()
