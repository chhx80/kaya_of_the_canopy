#!/usr/bin/env python3
"""nest_1 -- BLACK GLASS.  The opener of World 5, THE OBSIDIAN NEST.

Self-contained: running this file under the project python writes
levels/nest_1.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `nest_1()` returning `(Grid, Kit)`,
which is the tuple that writer's `build()` helper audits before it writes
anything.

    source tools/env.sh && "$PYVENV" tools/worlds/nest_1.py
    tools/prove.sh nest_1

WHAT THIS LEVEL TEACHES
-----------------------
World 5 is switch-blocks at scale (docs/plan-20-levels.md).  The player last
saw a lever in World 2, twelve levels ago, so -- like every world opener -- the
verb is reintroduced where getting it wrong costs nothing, and only then where
it costs something.  Two forms and no more: human and frog.  The four-form
workout is nest_3's.

  1. THE GLASS SHELF (screen A, cols 1-16).  Kaya spawns human at (3,12) on a
     flat obsidian floor with one 2-tile pit of nest_shard in it at cols 5-6.
     That is the whole of the world's vocabulary lesson: black glass underfoot,
     shard in the holes, veins of nest_vein glowing in the walls, nest_ledge
     mezzanines overhead and nest_chain hanging off them.  Nothing patrols it.

  2. THE TRADING WALL (screen A, col 17) -- THE VERB, FREE.  A wall of glass
     from the floor to the roof with TWO doorways in it: a high one at rows 7-8
     plugged with `switch_block_a_off`, and a low one at rows 11-12 plugged with
     `switch_block_a_on`.  Group 1 starts ON (tools/solver/sim.gd seeds
     TileWorld that way), so at spawn the high door is open and the low door is
     a wall.  `switch_a` stands on the floor at (10,12), six tiles west, with
     both doorways in frame: throw it and the wall becomes a door and the door
     becomes a wall, in one screen, in one glance.

     THE WALL ALWAYS HAS EXACTLY ONE DOOR, and that is the reason this beat is
     free rather than merely gentle.  Both doorways cross the same wall into
     the same corridor; a nest_ledge mezzanine at row 9 runs to the sill on
     each side (cols 13-16 and 18-21) and a nest_chain drops off each mezzanine
     to the floor (cols 12 and 22).  So whichever half of group 1 is solid, the
     room east and the room west are connected, both ways, for both forms.
     There is no configuration of this lever that costs the player anything --
     `_self_checks` (e) re-derives exactly that from the finished grid -- and
     the declared route throws it once and walks through the low door because
     that is the short way, not because it is the only way.

  3. THE SHAFT (screens B -> D).  The corridor runs east under four tiles of
     headroom past a second shard pit at cols 33-34 and ends at a hole: cols
     44-45 are open from row 13 to row 26, fourteen tiles.  A nest_chain runs
     the whole height at col 45 for anyone who would rather climb than drop,
     and a two-tile shelf east of the hole (cols 46-47) holds a gem and is
     reachable across the hole at the human's measured 2-tile gap.  The hole is
     the way down and the chain is the way back up, and BOTH of those facts are
     load-bearing in beat 4.

  4. THE SLAG GATE (screen D) -- THE VERB, WITH COMMITMENT AND AT SCALE.  One
     lever, `switch_b` at (37,26), and two gates, and all three are on screen D
     (cols 25-49) at once, which is the whole point of this beat:

       * SIX TILES EAST, at col 43, a `switch_block_b_on` plug across the
         only way out of the shaft's foot.  Group 2 starts OFF, so it is open
         when she walks west through it, and the throw shuts it behind her.
         What that gate closes off is not a corridor, it is the chain -- the
         way back up to the whole first half of the level.  The level's shape
         says so before she throws it: she got here by falling down a
         fourteen-tile hole.

       * NINE TILES WEST, at col 28, a `switch_block_b_off` plug across the
         mouth of the furnace.  It is a wall the whole time she walks up to the
         lever, and the same throw opens it.

     So the lesson is: one lever, two effects, fifteen tiles apart, both of
     them in the frame she is standing in -- screen D is cols 25-49, and the
     lever, the plug at col 43 and the plug at col 28 are all inside it.  The near one takes something away
     and the far one gives something back, and after this level the player
     knows to look at the whole screen when a lever goes over.

  5. THE FURNACE (screen C) -- the frog, and the way out.  `pad_frog` sits at
     (33,26), four tiles west of the lever and east of the gate, so the form
     change happens BEFORE the last door rather than behind it.  Inside the
     furnace three treads of nest_ledge climb west in 3-tile steps -- the
     frog's measured ceiling and one tile more than the human's -- to the exit
     on a rock shelf at (3,17).

WHY THERE ARE EXACTLY TWO LEVERS, AND WHY ONE OF THEM DOES TWO THINGS
---------------------------------------------------------------------
There are two switch groups, and a group may carry only ONE `switch_a` /
`switch_b` entity.  That is not a style rule, it is a divergence between the
game and the prover, measured in this file's sources:

    src/world/triggers/switch_trigger.gd  toggle(): `on = not on;
                                          world.set_switch(group, on)`
    tools/solver/sim.gd:363               `_set_switch(g, not world.switch_states[g])`

The trigger flips its OWN remembered state; the prover flips the WORLD's.  With
one lever per group those are the same number forever.  With two levers on one
group they part company the instant the first is thrown -- the second lever's
`on` is stale, so in the game it re-asserts a state that is already in force
and nothing moves, while the prover toggles.  `tools/prove.sh` would pass a
level `tools/itest.sh` cannot finish.  `_self_checks` (g) fails the build if a
group ever grows a second lever.

Two levers is two throws, so the third lesson rides on the second throw's FAR
effect rather than on a third lever.  That is beat 4 above, and it is written
that way on purpose: "a first taste of scale" is exactly the sentence "the
thing you just did also happened over there", and you cannot teach it with two
levers a room apart.

WHAT THE SWITCH BLOCKS DO, AND WHY EVERY ONE OF THEM IS A DOOR
--------------------------------------------------------------
`tools/reachability.py` resolves a switch tile as NEVER SOLID -- `Level.solid()`
returns False for anything carrying a `switch_group`, because the filter cannot
know which half of a group is up.  So a switch block may be a wall the filter
generously assumes is open, and it may never be a FLOOR: a route that has to
stand on one is a route that filter reports as missing, in every configuration,
every time (ADR 005: it may only ever under-report).

Every switch block in this level is therefore a plug in a wall, and
`_self_checks` (d) encodes the strongest form of that rule it can: EVERY switch
tile has a solid tile (or another tile of the same plug) directly above it.  A
tile with rock over its head is a tile nothing can ever stand on, in any
configuration, whatever the filter believes.

WHY reconfig_check IS GIVEN A DIFFERENT GOAL PER ROOM
-----------------------------------------------------
`world_kit.reconfig_check` asks two questions, and the first one -- "is the goal
reachable in at least ONE of the four configurations" -- is the wrong question
to ask of a level with a gate that closes behind you.  A commitment gate is by
construction a route that no single configuration opens end to end: config
2=OFF opens the shaft's foot and seals the furnace, config 2=ON does the
reverse.  Asking for the exit from the spawn would fail on a level that is
perfectly playable, and the only way to make it pass would be to delete beat 4.

So each entry in RECONFIG_ENTRIES is given the goal that room is actually
trying to reach -- the lever, the pad, or the exit -- and the end-to-end
question is answered instead by ESCAPE_* in `_self_checks` (f), which is a
search over (room x configuration) pairs rather than over configurations one at
a time:

    start at (spawn, group 1 ON / group 2 OFF), flood, and from every lever the
    flood touches, flip that lever and flood again.  Every state the player can
    reach this way must still be able to reach the goal.

That is the softlock question stated exactly, and it is the question the Route
Prover structurally cannot ask, because the prover only ever plays the route
that was declared.  It is still a filter and not a proof: `reachable_set` says
so about itself, and the frog's flood is generous by one verb (it climbs
ladders, and data/forms/frog.json says `can_climb: false`), which matters
nowhere here -- the frog's escape from the furnace is the crack at col 28,
never the chain.

THE CRACK AT COL 28, WHICH IS WHAT KEEPS THE FURNACE HONEST
------------------------------------------------------------
The furnace is behind a group-2 gate and contains no lever.  Shut that gate
with Kaya inside and you have ROOT HOLLOW's circular bridge again.  So the
furnace wall has a second opening that no switch touches: rows 22-23 at col 28,
with a nest_ledge at row 24 on each side of it (cols 25-27 and 29-31).  Its
sill is three tiles over the floor -- LIMITS["frog"]["rise"] is 3 and
LIMITS["human"]["rise"] is 2, both measured -- so it is a door to the frog and a
wall to Kaya, in every configuration, forever.  `pad_frog` is on the east side
of the gate, so by the time anyone is inside the furnace they are already the
frog, and the crack is always behind them.  `_self_checks` (e) re-derives all
four of those claims from the grid rather than trusting this paragraph.

THE MEASUREMENTS THIS GEOMETRY IS BUILT ON
------------------------------------------
* HUMAN rise 2, gap 3; FROG rise 3, gap 3 (world_kit.LIMITS, measured, with
  their provenance).  Every tread in the furnace is a 3-tile step and so is the
  crack's sill, which is what makes the frog load-bearing rather than
  decorative; both shard pits are 2 tiles wide, so the human crosses each at a
  3-column displacement.

* THE MEZZANINES ARE FOUR TILES OVER THE FLOOR and are reached by chain, not by
  jumping: 12 - 8 = 4 is past every form in the table.  That is deliberate --
  the high door has to be a real alternative, not a hop.

* WHERE THE WALKED FLOORS SIT.  `CameraController` picks its screen from the
  body's CENTRE, so a 22 px body on a floor whose cap row is a multiple of 15
  has its feet exactly on the horizontal seam and its centre on the screen
  ABOVE -- which never draws the floor it is standing on.  That is the defect
  ruins_4 shipped.  The stand rows here are 12 (cap 13), 8 (ledge 9), 26 (cap
  27), 23 (ledge 24), 20 (ledge 21) and 17 (ledge/cap 18); `_self_checks` (b)
  fails the build if any claimed stand row has (row + 1) % 15 == 0.

* THE TWO SEAMS.  The vertical seam is x=400, between cols 24 and 25.  Two hops
  cross it -- `wall_e` -> `corridor_mid` on row 12's cap and `gate_west` ->
  `floor_west` on row 26's -- and both are FLAT WALKS along unbroken standable
  floor, so the 0.12 s flip freeze lands while she is walking.  Every jump in
  the level is wholly inside one screen: both shard pits (cols 5-6 and 33-34),
  the gem shelf across the hole (cols 44-45) and all three furnace treads.
  `_self_checks` (c) re-derives that from the route.  The horizontal seam is
  y=240, between rows 14 and 15, and the route crosses it once, falling down
  the shaft -- the one entry in SEAM_EXEMPT, for the reason recorded there.

* THE LEVERS ARE ON THE FLOOR THEY ARE APPROACHED ALONG.  SwitchTrigger's box
  is `Rect2(tile * 16 + (1,6), (14,10))` -- the bottom ten pixels of its tile --
  and both of this level's levers are walked into along the row they sit in: a
  22 px human standing there spans y = 16y-6 .. 16y+16 and an 11 px frog spans
  16y+5 .. 16y+16, so both cover the box.  ruins_4's trap was a trigger whose
  box sat one row under a two-row arrival; `_self_checks` (g) checks every
  form that can reach each lever against that rectangle instead of assuming it.

* A BREAKABLE IS A WALL TO THE GATE (M4's pinned finding: the search alphabet
  has no ATTACK in it and the snapshots carry no broken-tile state).  The
  level's one breakable is a `nest_crust` plug at col 46, rows 25-26, with a
  heart behind it in a two-tile vault at the shaft's foot.  It is off every hop,
  it is optional, and `Kit.cannot_prove` files it loudly.

THE PALETTE, AND WHY IT NAMES JUNGLE TILES
------------------------------------------
`world_kit.Palette.char()` resolves a tile NAME through the flat `legend` key of
data/level_legend.json, which ADR 002's amendment leaves as the *jungle* view
because tools/reachability.py and tools/build_hub.py read it directly.  So
world_kit's own NEST palette -- which names obsidian, nest_plate, nest_block --
finds no character for any of them and falls through to an understudy, emitting
whatever character the understudy owns.  The memory note "world_kit ruins
palette emits wrong stone" is that failure, in World 2.

So this palette names, for each role, the jungle tile that OWNS the character
the nest tileset binds to the art we want.  The two fill characters are the
same way round as TERMITE DEEPS and the opposite way round from the jungle:

    role "packed"  -> jungle `stone`  -> 's' -> 290 nest_plate   (the bulk)
    role "block"   -> jungle `dirt`   -> 'd' -> 283 nest_block   (the lining)

The result is that `Palette.missing()` is empty and `Palette.substituted` stays
EMPTY, so `Kit.audit(strict_verbs=True)` is meaningful and the JSON carries nest
ids (280-291) rather than jungle ones.  The switch blocks need no trick: 'A',
'a', 'B' and 'b' are `shared` characters and mean tiles 11, 26, 12 and 27 in
every world.

WHAT THE CAPTURES CHANGED, WHICH IS FOUR THINGS AND ALL OF THEM MATERIAL
------------------------------------------------------------------------
The first pass of this level was built in world_kit's NEST palette as written,
in TERMITE DEEPS' idiom: `packed` for the bulk, veins on the fg the way deeps_1
puts deep_fungus there.  shots/nest_1_*.png say that is wrong four times over,
and each correction is recorded at the line that makes it.

 1. THE MASS IS OBSIDIAN.  tools/art/tiles.py on 290 nest_plate: "the one tile
    in the world with a bright face, and it is bounded -- a plate is an object,
    not a mass."  Filled with it, the level was riveted iron with black glass
    trimmings.  RIM_NEST (280) is the mass and RIM_NEST_HOT (281) is "its
    capped form", so the bulk and the cold floors are obsidian, and the plate
    is now only what it should be: the lining of the flue.  (nest_2 uses '#'
    and 'd' for its masses and no 's' at all.  That agreement is worth having.)

 2. THE TWO WALLS A LEVER OPENS ARE BUILT.  Black glass standing in front of a
    background of black glass is a wall nobody can see, and the trading wall
    has to be the most legible object on its screen.  283 nest_block is cut
    basalt -- "the only square thing in it", joints that glow -- so the trading
    wall and the furnace's east wall are masonry and everything else is glass.

 3. nest_vein IS A BACKGROUND TILE.  Its art docstring opens with "Background
    flow", and it is a full 16x16 rock fill with one live vein in it.  deeps_1
    could put deep_fungus on the fg because a tuft is air that glows; a rock
    fill in mid-air in a walking lane is furniture, and the corridor captures
    had three of them looking exactly like that.  So VEINS goes on the bg,
    where the flow is behind the glass, and what glows in front of it is the
    obsidian_hot band `_hot()` paints around each one -- 281 is solid, so it
    sits in the rock without punching a hole in it, and it is an fg tile, so
    `AmbienceLayer._collect_emissive`, which scans `world.get_fg` and nothing
    else, can actually see it.  `_self_checks` (h) holds all of that.

 4. A FLUE HANGS FROM A ROOF.  The background nest_flue columns ran floor to
    ceiling in open air, three tiles from a nest_chain that is genuinely
    climbable and drawn as a dark vertical bar of about the same width.
    deeps_1's rule -- "a dark column in a dark room reads as something you can
    land on" -- failing in the one way that matters most.  They stop now.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                      # noqa: E402
import world_kit                                        # noqa: E402
from world_kit import Kit, Palette, Probe               # noqa: E402

LEVEL_ID = "nest_1"
LEVEL_NAME = "BLACK GLASS"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the nest role character.
## See the module docstring: this is a character map, not an art claim, and the
## art comes from `"tileset": "nest"` at load time.
NEST_W5 = Palette("obsidian_nest", {
    "bg": "bg_leaves",              # 'L' -> 282 nest_wall
    "solid": "grass_top",           # '#' -> 280 obsidian      (the cap)
    "solid_alt": "stone_mossy",     # 'S' -> 281 obsidian_hot  (the hot face)
    "packed": "stone",              # 's' -> 290 nest_plate    (the bulk fill)
    "block": "dirt",                # 'd' -> 283 nest_block    (the lining)
    "oneway": "wood_platform",      # '=' -> 286 nest_ledge
    "ladder": "vine",               # '|' -> 288 nest_chain
    "hazard": "spikes",             # '^' -> 287 nest_shard
    "breakable": "crate",           # 'c' -> 291 nest_crust
    "decor": "tree_trunk",          # 'T' -> 285 nest_flue
    "void": "bg_dark",              # 'X' -> 284 nest_void
    "shoulder": "cracked_stone",    # 'k'  shared, 211 (unused here)
    "rubble": "rubble",             # 'o'  shared (unused here)
    "glowwall": "luminous_wall",    # 'O'  shared, 214 (unused here)
    "water": "water",               # 'w'  shared (this level is dry)
    "water_top": "water_top",       # '~'  shared
    "switch_a_on": "switch_block_a_on",    # 'A' shared, 11
    "switch_a_off": "switch_block_a_off",  # 'a' shared, 26
    "switch_b_on": "switch_block_b_on",    # 'B' shared, 12
    "switch_b_off": "switch_block_b_off",  # 'b' shared, 27
})

# ---------------------------------------------------------------- the shape
## Every number the geometry and the checks below share, in one place, because
## "the crack is a door to the frog and a wall to Kaya" is a claim about
## arithmetic and not about prose.

# -- the top half (screens A and B) ----------------------------------------
TOP_STAND = 12                  # the corridor floor: cap row 13
TOP_CAP = 13
TOP_X0, TOP_X1 = 1, 47          # the air runs the full width
TOP_ROOF = 7                    # rows 7..12 are air: four tiles of headroom
FLOOR_X1 = 43                   # the cap stops here; cols 44-45 are the hole

WALL_X = 17                     # THE TRADING WALL
DOOR_LOW_Y = 12                 # rows 11-12, `switch_block_a_on`  (shut at spawn)
DOOR_HIGH_Y = 8                 # rows 7-8,  `switch_block_a_off` (open at spawn)
GATE_H = 2                      # a body is two tiles; a one-tile door is defect 3

MEZZ_CAP = 9                    # the nest_ledge mezzanines: stand row 8
MEZZ_STAND = 8
MEZZ_W = (13, 4)                # west: cols 13-16, up to the sill
MEZZ_E = (18, 4)                # east: cols 18-21, away from it
CHAIN_W, CHAIN_E = 12, 22       # a nest_chain off each mezzanine to the floor

SHAFT_X0, SHAFT_X1 = 44, 45     # THE HOLE: open from row 13 to row 26
SHAFT_CHAIN = 45
SHELF_X, SHELF_W = 46, 2        # the gem shelf east of it, across a 2-tile gap

## (x0, width).  Both 2 tiles, so the human crosses each at a 3-column
## displacement: LIMITS["human"]["gap"] is 3.  A row of nest_shard replaces the
## cap and the fill under it stays, so each pit has a solid bottom and a
## measured price -- fall in, take the hit, climb one tile out.
PITS = [(5, 2), (33, 2)]

# -- the bottom half (screens C and D) --------------------------------------
LOW_STAND = 26                  # the furnace floor and the east corridor: cap 27
LOW_CAP = 27
FURNACE_X0, FURNACE_X1 = 1, 27  # the furnace: rows 16-26
FURNACE_ROOF = 16
EAST_X0, EAST_X1 = 28, 45       # the east corridor: rows 22-26
EAST_ROOF = 22
NARROW_X0, NARROW_X1 = 41, 43   # ... which drops to two tiles here, so the
                                # slag gate can seal it

FURNACE_WALL_X = 28             # the furnace's east wall
GATE_FAR_Y = 26                 # rows 25-26, `switch_block_b_off` (shut at spawn)
CRACK_Y0, CRACK_Y1 = 22, 23     # the frog's door over it: always open
CRACK_CAP = 24                  # the nest_ledge either side of the crack
CRACK_STAND = 23
CRACK_LEDGE_W = (25, 3)         # cols 25-27, inside the furnace
CRACK_LEDGE_E = (29, 3)         # cols 29-31, in the east corridor

GATE_NEAR_X = 43                # rows 25-26, `switch_block_b_on` (open at spawn)
GATE_NEAR_Y = 26

VAULT_X = 46                    # the nest_crust plug, rows 25-26
VAULT_HEART = (47, 26)

## The furnace stair: three treads of nest_ledge climbing WEST in 3-tile steps.
STAIR_X, STAIR_Y = 16, 24
STAIR_COUNT, STAIR_RISE, STAIR_RUN, STAIR_W = 3, 3, 5, 4

EXIT_SHELF = (1, 18, 5)         # x, cap row, width -- stand row 17
EXIT_TILE = (3, 17)

SPAWN = (3, TOP_STAND)
SWITCH_A = (10, TOP_STAND)
SWITCH_B = (37, LOW_STAND)
PAD_TILE = (33, LOW_STAND)

## Every nest_vein tile: this level's light, and the only thing in it that
## glows without being a hazard.  `_self_checks` (h) re-checks each one against
## the finished grid.
VEINS = [
    (2, 7), (8, 7), (15, 12),               # the glass shelf
    (4, 12), (7, 12),                       # flanking the first shard pit
    (16, 7), (18, 7),                       # beside the trading wall's high door
    (16, 12), (18, 12),                     # and at the foot of its low one
    (23, 7), (31, 12), (32, 12), (35, 12),  # the corridor east, and the pit
    (37, 7), (43, 12),                      # the lip of the flue
    (44, 18), (44, 22),                     # inside it: a space, not a void
    (31, 22), (34, 20), (37, 20), (40, 22),  # the slag gate room's roof
    (29, 22), (27, 26),                     # the crack at col 28, both sides
    (25, 26), (18, 16),                     # the furnace mouth and its roof
    (12, 26), (20, 26),                     # the furnace floor
    (1, 16), (1, 20), (1, 23), (5, 16),     # the west wall, under the exit
]

## Niches: relief cut upward into a roof.  They have no floor of their own --
## the row under each is the room's air -- so nothing can stand in one and the
## pocket check skips them, which is what makes a 2-tile niche legal where a
## 2-tile ROOM would be a squeeze.  `_self_checks` (i) re-derives that.
NICHES = [
    (3, 5, 3, 2), (24, 5, 4, 2), (30, 5, 3, 2), (38, 5, 3, 2),   # the top corridor
    (33, 20, 3, 2), (36, 20, 3, 2),                              # the slag room
    (12, 14, 4, 2), (20, 14, 3, 2), (7, 14, 3, 2),               # the furnace roof
]


def p_solid_at(g, x, y):
    """Is the fg tile at (x,y) solid, with switch blocks resolved as open?

    A one-line Probe, so the vein pass can run before the audit builds one.
    """
    return Probe(g).solid(x, y)


def _hot(k):
    """Band the rock a vein touches with obsidian_hot.

    281 and 280 are both plain `solid` -- the same tile to every flag-reading
    checker, and `_self_checks` (a) and the audit are run after this -- so this
    is colour and nothing else.  It is generated from VEINS rather than listed
    by hand because the claim it makes is "the glass is hot WHERE THE VEIN IS",
    and a hand-written band drifts off its vein the first time one moves.

    Only the cap and the fill are repainted: a one-way, a chain, a hazard or a
    switch block next to a vein keeps its own art, because every one of those
    is a verb and a verb that is recoloured stops reading as itself.
    """
    g = k.g
    cap, fill, hot = k.ch("solid"), k.ch("packed"), k.ch("solid_alt")
    for x, y in VEINS:
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < g.w and 0 <= yy < g.h and g.fg[yy][xx] in (cap, fill):
                g.put(xx, yy, hot)


def nest_1():
    g = Grid(W, H, tileset="nest")
    k = Kit(g, NEST_W5, form="human")

    # ------------------------------------------------------------- the rock
    # Carved rather than built.  `Kit.fill_solid` says why: a level cut out of
    # rock has a tiny reachable state space, so a prover hop that fails
    # exhausts its frontier instead of spending its whole budget wandering.
    #
    # THE MASS IS OBSIDIAN AND NOTHING ELSE, which is a correction the first
    # capture forced.  world_kit's NEST palette calls `nest_plate` the packed
    # fill, in the idiom TERMITE DEEPS set, and tools/art/tiles.py says of that
    # tile in as many words: "the one tile in the world with a bright face, and
    # it is bounded -- a plate is an object, not a mass."  Built out of it the
    # whole level was riveted iron with black glass trimmings, which is the
    # opposite of the world.  RIM_NEST (280) is the mass and RIM_NEST_HOT (281)
    # is "its capped form", so the bulk, the shell and the cold floors are all
    # obsidian, and the plate survives as what it is: the lining of the flue.
    k.fill_bg("bg")
    k.fill_solid("solid")
    k.shell(1, "solid")

    # ========================================== 1-2. THE SHELF AND THE WALL
    # One corridor from col 1 to col 47, four tiles of headroom, with the
    # trading wall cut back into it afterwards.
    k.corridor(TOP_X0, TOP_STAND, TOP_X1 - TOP_X0 + 1, h=TOP_STAND - TOP_ROOF + 1)
    k.floor(TOP_X0, TOP_CAP, FLOOR_X1 - TOP_X0 + 1, depth=1)    # cols 1-43
    k.floor(SHELF_X, TOP_CAP, SHELF_W, depth=1)                 # cols 46-47

    # THE HOLE.  Carved before anything else that could cap it, and open from
    # the corridor's floor all the way to the furnace's.
    k.clear_rect(SHAFT_X0, TOP_CAP, SHAFT_X1 - SHAFT_X0 + 1, LOW_STAND - TOP_CAP + 1)

    # The wall itself: solid from the roof to the floor, then the two doorways
    # punched back out of it.  Rows 9-10 stay solid, which is what makes the
    # high door a separate door and not the top half of one tall one.
    #
    # nest_block and not obsidian, and that is the second thing the first
    # capture forced.  283 is cut basalt -- "the only square thing in it", with
    # joints that glow -- and the two walls in this level that a lever opens are
    # the only two BUILT things in it.  A wall of black glass standing in front
    # of a background of black glass is a wall the player cannot see, and this
    # one has to be the most legible object on its screen.
    k.rect(WALL_X, TOP_ROOF, 1, TOP_CAP - TOP_ROOF, "block")
    k.ledge(MEZZ_W[0], MEZZ_CAP, MEZZ_W[1])
    k.ledge(MEZZ_E[0], MEZZ_CAP, MEZZ_E[1])
    # `switch_block_a_on` is solid exactly while group 1 is ON, which is how the
    # level starts; `switch_block_a_off` is solid exactly while it is OFF.  So
    # at spawn the high door is a doorway and the low door is a wall, and the
    # lever trades them.
    k.switch_gate(WALL_X, DOOR_LOW_Y, GATE_H, group="a", solid_when="on")
    k.switch_gate(WALL_X, DOOR_HIGH_Y, GATE_H, group="a", solid_when="off")

    # The chains.  Drawn after the ledges they hang off, and claiming a landing
    # on the side the mezzanine is actually on (defect 1: a vine with no exit).
    k.climb(CHAIN_W, MEZZ_STAND, TOP_STAND, landing="right")
    k.climb(CHAIN_E, MEZZ_STAND, TOP_STAND, landing="left")

    # The shard pits, drawn AFTER the floor so nothing caps them back over.
    for x0, w in PITS:
        k.rect(x0, TOP_CAP, w, 1, "hazard")
        k.gap(x0, TOP_STAND, w, form="human")

    # ============================================== 4-5. THE BOTTOM HALF
    # The furnace first, then the east corridor, then the floor under both.
    k.clear_rect(FURNACE_X0, FURNACE_ROOF,
                 FURNACE_X1 - FURNACE_X0 + 1, LOW_STAND - FURNACE_ROOF + 1)
    # The corridor is five tiles tall to col 40 and TWO from col 41 east.  That
    # is not dressing: `switch_gate` plugs one column, and a two-tile plug in a
    # five-tile corridor is a step, not a gate.  The shaft at cols 44-45 stays
    # open above the narrow part, so the chain still runs from the foot to the
    # top half -- which is the whole of what the slag gate takes away.
    k.corridor(EAST_X0, LOW_STAND, NARROW_X0 - EAST_X0,
               h=LOW_STAND - EAST_ROOF + 1)
    k.corridor(NARROW_X0, LOW_STAND, EAST_X1 - NARROW_X0 + 1, h=GATE_H)
    # The lower floor is capped in obsidian_hot rather than obsidian: 281 is
    # the cooling crust, its art carries its own hot seam two pixels under the
    # top (which is why RIM_NEST_HOT drops `top` -- the cap is what the top is),
    # and it is the same solid to every flag-reading checker. So the deeper
    # half of the level is visibly the hotter one, in tiles rather than in
    # lighting, which means it survives a capture with the ambience off.
    k.floor(FURNACE_X0, LOW_CAP, VAULT_HEART[0] - FURNACE_X0 + 1, depth=1,
            cap="solid_alt")

    # The flue: the hole is lined with nest_plate on both faces, which is the
    # one place in the level a plate belongs -- an object, bounded, riveted,
    # around the one shaft that was cut rather than cooled.
    k.rect(FLOOR_X1, TOP_CAP + 1, 1, LOW_STAND - TOP_CAP - 1, "packed")
    k.rect(SHELF_X, TOP_CAP + 1, 1, LOW_STAND - TOP_CAP - 1, "packed")

    # The furnace's east wall, and the two ways through it.  Basalt, for the
    # same reason the trading wall is: it is the other thing a lever opens.
    k.rect(FURNACE_WALL_X, FURNACE_ROOF, 1, LOW_STAND - FURNACE_ROOF + 1, "block")
    k.clear_rect(FURNACE_WALL_X, CRACK_Y0, 1, CRACK_Y1 - CRACK_Y0 + 1)
    k.ledge(CRACK_LEDGE_W[0], CRACK_CAP, CRACK_LEDGE_W[1], stand_form="frog")
    k.ledge(CRACK_LEDGE_E[0], CRACK_CAP, CRACK_LEDGE_E[1], stand_form="frog")
    world_kit.check_rise(LOW_STAND - CRACK_STAND, "frog",
                         "furnace floor -> the crack's ledge")
    k.switch_gate(FURNACE_WALL_X, GATE_FAR_Y, GATE_H, group="b", solid_when="off")
    k.switch_gate(GATE_NEAR_X, GATE_NEAR_Y, GATE_H, group="b", solid_when="on")

    # The vault at the shaft's foot: the level's ONE breakable tile, and the
    # only thing in it tools/prove.sh cannot model at all.
    k.clear_rect(VAULT_X, LOW_STAND - GATE_H + 1, 2, GATE_H)
    k.rect(VAULT_X, LOW_STAND - GATE_H + 1, 1, GATE_H, "breakable")
    k.cannot_prove(
        "the nest_crust plug at (%d,%d-%d) and the heart behind it at %s: "
        "tools/solver/sim.gd models pads, keys, doors and switches and nothing "
        "that BREAKS a tile, so the search alphabet has no ATTACK in it and a "
        "breakable is a wall to the gate. It is off every hop and optional."
        % (VAULT_X, LOW_STAND - GATE_H + 1, LOW_STAND, VAULT_HEART))

    # The furnace stair.  `Kit.stair` checks the rise against the frog's
    # MEASURED ceiling before it draws a tile: 3 is the kit's limit and a
    # 4-tile rung is the jungle_4 defect (provable, unplayable).
    treads = k.stair(STAIR_X, STAIR_Y, STAIR_COUNT, STAIR_RISE, STAIR_RUN,
                     STAIR_W, form="frog", dx=-1)
    # The one step the stair helper does not file, because it is the step onto
    # the bottom tread from the furnace's own floor.
    world_kit.check_rise(LOW_STAND - treads[0][1], "frog",
                         "furnace floor -> tread_1")
    ex, ey, ew = EXIT_SHELF
    # Two rows thick, so it reads as rock and not as a sheet -- and obsidian
    # all the way through, cold: the way out of the furnace is the one floor
    # down here that has stopped glowing.
    k.floor(ex, ey, ew, depth=2, fill="solid")

    # The chain down the hole, drawn LAST of the solid geometry: a climb
    # written before a carve that crosses it is the draw-order bug audit()
    # exists for, and this column runs from the top corridor to the furnace's
    # floor.  landing="right" because (44,12) is open air over the hole and
    # (46,12) is the gem shelf.
    k.climb(SHAFT_CHAIN, TOP_STAND, LOW_STAND, landing="right")

    # ------------------------------------------------------- carved, not cut
    # Relief last among the carves, so a niche cannot be capped back over.
    for (x, y, w, h) in NICHES:
        k.clear_rect(x, y, w, h)

    # ------------------------------------------------------------- dressing
    # nest_wall is the backdrop of every room and nest_void is used sparingly,
    # which is the third correction the first capture forced: 284 is flat black
    # and a room with it behind every tile is a room whose floor, whose walls
    # and whose gates are all the same nothing. 282 is "background glass -- the
    # facets are still there but the glare is gone", which is exactly what
    # black rock needs to be legible in front of. So the void is kept for the
    # three places that are meant to read as no-place: the bottom of the flue,
    # the roof of the furnace, and the deep cells over the corridor.
    for (x, y, w, h) in [(44, 16, 2, 11), (1, 16, 27, 4), (2, 1, 18, 5)]:
        g.rect(x, y, w, h, "X", "bg")
    # Flues HANG FROM A ROOF and stop; none of them runs to a floor.  The
    # first capture had them floor-to-ceiling in open air, three tiles from a
    # nest_chain that is genuinely climbable and drawn as a dark vertical bar
    # of about the same width -- which is deeps_1's rule ("a dark column in a
    # dark room reads as something you can land on") failing in the one way
    # that matters most: it read as the one column in the room that IS one.
    for (x, y, h) in [(6, 7, 3), (14, 7, 2), (26, 7, 3), (33, 7, 2),
                      (41, 7, 3), (4, 16, 4), (12, 16, 3), (23, 16, 4),
                      (31, 22, 2), (39, 22, 2)]:
        g.rect(x, y, 1, h, "T", "bg")

    # ------------------------------------------------------------- the light
    # ON THE BG LAYER, and that is the fourth thing the capture corrected.
    # deeps_1 put deep_fungus on the fg because a tuft is air that glows and
    # `AmbienceLayer._collect_emissive` scans the fg and nothing else. 289 is
    # not a tuft: tools/art/tiles.py opens its docstring with "Background
    # flow", and it is a full 16x16 rock fill with one live vein in it. On the
    # fg, in a room, it is a rock-looking tile floating at knee height in the
    # walking lane -- the captures of the corridor had three of them and they
    # read as furniture. So a vein goes BEHIND the room, where it is what it
    # is, and the thing that glows in front of it is the obsidian_hot band
    # `_hot` paints around it: 281 is solid, so it can sit in the rock without
    # punching a hole in it, and it is an fg tile, so it can emit.
    # (nest_2 puts its veins on the bg too. That agreement is worth keeping.)
    for x, y in VEINS:
        if p_solid_at(g, x, y):
            raise world_kit.WorldKitError(
                "vein at (%d,%d) is behind solid rock ('%s'): nothing will "
                "ever see it" % (x, y, g.fg[y][x]))
        g.put(x, y, "r", "bg")
    _hot(k)

    # ------------------------------------------------------------- entities
    g.ent("player_spawn", *SPAWN)
    g.ent("switch_a", *SWITCH_A)
    g.ent("switch_b", *SWITCH_B)
    g.ent("pad_frog", *PAD_TILE)
    g.ent("exit", *EXIT_TILE)

    # NOTHING PATROLS THE TEACHING ROOMS, which is the decision deeps_1 and
    # heights_1 both record, and it is worth more here than in either: beat 2's
    # promise is that this lever costs nothing, and a walker on the trading
    # wall's own floor would be the thing that made it cost something.
    #
    # What does live here lives in pockets the route never enters and cannot be
    # left by anything that walks: `turn_at_ledge` pins a walker to the shelf it
    # spawns on (walker.json: 32 px/s, chase_range 96), and a flyer has no
    # chase at all -- flyer.json is patrol_range 64 with a 6 px bob, so one
    # spawned at row 8 stays at row 8 and the corridor's floor four tiles under
    # it is never in its path.
    g.ent("enemy_flyer", 24, MEZZ_STAND)          # over the east mezzanine
    g.ent("enemy_flyer", 35, MEZZ_STAND)          # over the corridor east
    g.ent("enemy_walker", SHELF_X, TOP_STAND)     # the gem shelf, two tiles wide
    g.ent("enemy_walker", CRACK_LEDGE_E[0] + 1, CRACK_STAND)   # the crack, east
    g.ent("enemy_walker", CRACK_LEDGE_W[0] + 1, CRACK_STAND)   # and west

    # Gems along the route, and in each of the three places worth leaving it.
    for (x, y) in [(2, TOP_STAND), (8, TOP_STAND), (14, TOP_STAND),
                   (14, MEZZ_STAND), (20, MEZZ_STAND),
                   (20, TOP_STAND), (26, TOP_STAND), (31, TOP_STAND),
                   (36, TOP_STAND), (41, TOP_STAND), (47, TOP_STAND),
                   (44, LOW_STAND), (40, LOW_STAND), (35, LOW_STAND),
                   (30, CRACK_STAND), (26, CRACK_STAND),
                   (24, LOW_STAND), (18, LOW_STAND), (12, LOW_STAND),
                   (18, 23), (13, 20), (8, 17)]:
        g.ent("gem", x, y)
    g.ent("heart", *VAULT_HEART)                  # behind the nest_crust
    g.ent("heart", 5, LOW_STAND)                  # the furnace's west floor

    # --------------------------------------------------- the route (ADR 005)
    # Sixteen hops, all short.  Three of them are flat walks that exist only so
    # the ones that are the level start from a known state, and the two that
    # cross the vertical seam are deliberately among them.
    k.mark("pit_a_east", PITS[0][0] + PITS[0][1], TOP_STAND)      # (7,12)
    k.mark("wall_west", WALL_X - 1, TOP_STAND)                    # (16,12)
    k.mark("wall_east", WALL_X + 1, TOP_STAND)                    # (18,12)
    k.mark("corridor_mid", 30, TOP_STAND)
    k.mark("pit_b_east", PITS[1][0] + PITS[1][1], TOP_STAND)      # (35,12)
    k.mark("shaft_head", FLOOR_X1, TOP_STAND)                     # (43,12)
    k.mark("shaft_foot", SHAFT_X0, LOW_STAND)                     # (44,26)
    k.mark("gate_west", FURNACE_WALL_X - 2, LOW_STAND, form="frog")   # (26,26)
    k.mark("floor_west", 20, LOW_STAND, form="frog")
    for i, (tx, stand, tw) in enumerate(treads):
        k.mark("tread_%d" % (i + 1), tx + tw - 1, stand, form="frog")

    g.route("spawn", "pit_a_east", form="human")       # over the first shard pit
    g.route("pit_a_east", "switch_a", form="human")    # BEAT 2: the trade
    g.route("switch_a", "wall_west", form="human")
    g.route("wall_west", "wall_east", form="human")    # through the low door
    g.route("wall_east", "corridor_mid", form="human")  # crosses x=400, walking
    g.route("corridor_mid", "pit_b_east", form="human")  # over the second pit
    g.route("pit_b_east", "shaft_head", form="human")
    g.route("shaft_head", "shaft_foot", form="human")  # the drop, see SEAM_EXEMPT
    g.route("shaft_foot", "switch_b", form="human")    # BEAT 4: the slag gate
    g.route("switch_b", "pad_frog", form="human")
    g.route("pad_frog", "gate_west", form="frog")      # through the far gate
    g.route("gate_west", "floor_west", form="frog")    # crosses x=400, walking
    g.route("floor_west", "tread_1", form="frog")      # 3 up: the human cannot
    g.route("tread_1", "tread_2", form="frog")
    g.route("tread_2", "tread_3", form="frog")
    g.route("tread_3", "exit", form="frog")
    return g, k


# ====================================================================== light
## The data/ambience.json entry this level is designed around, kept HERE because
## that file belongs to the integration pass and because the pool positions are
## a fact about the geometry above.  `main()` prints it.
##
## GLASS AND EMBER.  No `darkness` key: the dark is World 4's verb and this
## world's is the lever, so everything here is tint, vignette and the tiles that
## glow.  The emissive entries are what make the level readable -- 289 nest_vein
## marks the route, 281 obsidian_hot is the heat in the rock, and 287 nest_shard
## lights the only two things in the level that can hurt you, because a hazard
## you cannot see is not a lesson, it is a coin toss.
AMBIENCE = {
    "_note": (
        "BLACK GLASS. World 5's teacher, and the first level in the game whose "
        "subject is a lever. Cold glass lit from inside: the air is thin and "
        "dark so the backdrop stays behind the tiles, the fg tint is pushed "
        "one step towards ember rather than desaturated, and every pool is on "
        "something the player has to read -- the two levers, the trading "
        "wall's two doorways, the mouth of the flue, the slag gate's two ends "
        "and the exit. The emissive tiles are the level's own light and are "
        "all three of them SOLID, because AmbienceLayer._collect_emissive "
        "scans the fg: 281 obsidian_hot is the heat, banded around every "
        "nest_vein in the backdrop and run along the whole lower floor, so "
        "the deep half of the level is visibly the hot one; 287 nest_shard is "
        "the two pits, which glow for the reason deeps_1's spore does; 291 "
        "nest_crust is the single breakable, glowing once, which is how "
        "TERMITE DEEPS taught 'this wall is different'. 289 nest_vein is NOT "
        "in here: it is a background tile by its own art and emits nothing "
        "from back there, which is the point -- the flow is behind the glass "
        "and the glass is what you see."),
    "world": "obsidian",
    "air": {"ramp": "ember", "step": 1, "alpha": 0.30},
    "bg_tint": {"ramp": "ember", "step": 2, "mix": 0.72, "scale": 0.48},
    "fg_tint": {"ramp": "ember", "step": 5, "mix": 0.18, "scale": 0.92},
    "vignette": 0.38,
    "lights": [
        {"x": 3, "y": 11, "radius": 72, "ramp": "ember", "step": 5,
         "intensity": 0.34},
        {"x": 10, "y": 11, "radius": 64, "ramp": "gold", "step": 5,
         "intensity": 0.46, "flicker": 0.18},
        {"x": 17, "y": 7, "radius": 56, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 17, "y": 12, "radius": 56, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 30, "y": 10, "radius": 80, "ramp": "ember", "step": 4,
         "intensity": 0.26},
        {"x": 44, "y": 13, "radius": 72, "ramp": "ember", "step": 5,
         "intensity": 0.30},
        {"x": 44, "y": 24, "radius": 64, "ramp": "ember", "step": 4,
         "intensity": 0.26},
        {"x": 37, "y": 25, "radius": 64, "ramp": "gold", "step": 5,
         "intensity": 0.46, "flicker": 0.18},
        {"x": 28, "y": 25, "radius": 56, "ramp": "gold", "step": 4,
         "intensity": 0.32},
        {"x": 20, "y": 24, "radius": 88, "ramp": "ember", "step": 4,
         "intensity": 0.30},
        {"x": 3, "y": 17, "radius": 76, "ramp": "gold", "step": 6,
         "intensity": 0.54, "flicker": 0.10},
    ],
    "emissive": {
        "281": {"ramp": "ember", "step": 5, "intensity": 0.18, "radius": 24},
        "287": {"ramp": "ember", "step": 6, "intensity": 0.32, "radius": 26,
                "lift": 5},
        "291": {"ramp": "ember", "step": 6, "intensity": 0.38, "radius": 28},
    },
}


## Route hops allowed to change screen without being a flat walk, and why.
SEAM_EXEMPT = {
    ("shaft_head", "shaft_foot"):
        "a fall, not a hop: fourteen tiles straight down a two-column hole "
        "with a chain in it. The 0.12 s flip freeze at y=240 leaves her "
        "falling in the same column with nothing to miss, which is exactly why "
        "the descent is a hole and not a staircase of ledges.",
}


## What tools/solver/sim.gd seeds before a switch entity is touched: TileWorld's
## own defaults, group 1 ON and group 2 OFF.  Both of this level's levers
## declare the same thing, so the game's SwitchTrigger._ready() agrees.
START_CFG = {1: True, 2: False}

## Entries reconfig_check is run from: the spawn, every room a shut gate makes,
## and both sides of each gate.  Each is swept over all four configurations by
## reconfig_check itself.  Every one of them stands on ROCK rather than on a
## switch block -- an entry the flood cannot legally stand in reports an empty
## room instead of a trap.
##
## The GOAL is per-room, and the docstring says why at length: a gate that
## closes behind you is by construction a route no single configuration opens
## end to end, so each room is asked whether it can reach what it is actually
## trying to reach. The end-to-end question is ESCAPE_*, below.
RECONFIG_ENTRIES = [
    ("the glass shelf (spawn)",          SPAWN,            SWITCH_A, "human"),
    ("west of the trading wall",         (16, TOP_STAND),  SWITCH_B, "human"),
    ("east of the trading wall",         (18, TOP_STAND),  SWITCH_B, "human"),
    ("the west mezzanine",               (14, MEZZ_STAND), SWITCH_B, "human"),
    ("the east mezzanine",               (20, MEZZ_STAND), SWITCH_B, "human"),
    ("the corridor east",                (30, TOP_STAND),  SWITCH_B, "human"),
    ("the gem shelf across the hole",    (46, TOP_STAND),  SWITCH_B, "human"),
    ("the shaft's foot, behind the slag gate", (44, LOW_STAND), SWITCH_A, "human"),
    ("the slag gate room",               (37, LOW_STAND),  PAD_TILE, "human"),
    ("the furnace floor, behind the far gate", (20, LOW_STAND), EXIT_TILE, "frog"),
    ("the crack's east ledge",           (30, CRACK_STAND), EXIT_TILE, "frog"),
    ("the crack's west ledge",           (26, CRACK_STAND), EXIT_TILE, "frog"),
    ("the top of the furnace stair",     (8, 17),          EXIT_TILE, "frog"),
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
        elif (e["type"].startswith("pad_") or e["type"] == "exit"
              or e["type"].startswith("switch_")):
            where[e["type"]] = {"x": e["x"], "y": e["y"]}
    return where


def _switch_tiles(g):
    """Every switch-block tile in the grid, as (x, y, char)."""
    chars = {NEST_W5.char(r): r for r in
             ("switch_a_on", "switch_a_off", "switch_b_on", "switch_b_off")}
    return [(x, y, g.fg[y][x])
            for y in range(g.h) for x in range(g.w)
            if g.fg[y][x] in chars]


def _escape(k, start, goal, form, cfg=None):
    """Can the player always still finish, from every state they can reach?

    A search over (where you are standing, which switches are thrown) rather
    than over configurations one at a time.  From the start state: flood; if
    the goal is in the flood, this state WINS.  For every lever the flood
    touches, flipping it is an edge to a new state.  The level is softlock-free
    from `start` when every state reachable from it can still reach a winning
    one.

    Returns the list of states that cannot, each as (entry, config), which is
    literally a list of places the player can stand with no way to finish.
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
    # Backward closure: a state is safe if it wins or can step to a safe one.
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


def _self_checks(g, k):
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

    # (b) Everything the player must touch needs a body's worth of room over it,
    # and must not stand on a floor the screen it is drawn on does not contain
    # (the defect ruins_4 shipped).
    must = {"exit", "pad_frog", "player_spawn", "switch_a", "switch_b",
            "gem", "heart", "enemy_walker", "enemy_flyer"}
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

    # (c) NO ON-FOOT HOP CROSSES A SCREEN SEAM MID-JUMP.  A hop whose two ends
    # are on different screens has to be a flat walk along unbroken standable
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
                           "(%d,%d) is not standable, so it is a jump and not a "
                           "walk" % (hop["from"], hop["to"], x, y))
                break

    # (d) NO SWITCH BLOCK IS EVER A FLOOR.  tools/reachability.py resolves a
    # switch tile as never solid, so a route that stands on one is a route it
    # reports as missing in every configuration.  The strongest form of that
    # rule a grid can carry: every switch tile has rock (or the rest of its own
    # plug) directly over its head, so nothing can be on top of it whatever the
    # configuration.  Checked with the switches resolved BOTH ways, because
    # "solid" is a property of a configuration and "has rock above it" is not.
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

    # (e) THE TWO BEATS, RE-DERIVED FROM THE GRID.  Four claims this file's
    # docstring makes in prose and would otherwise be unable to keep.
    for cfg, open_door, shut_door in (
            ({1: True, 2: False}, DOOR_HIGH_Y, DOOR_LOW_Y),
            ({1: False, 2: False}, DOOR_LOW_Y, DOOR_HIGH_Y)):
        pr = Probe(g, switches=cfg)
        for yy in range(open_door - GATE_H + 1, open_door + 1):
            if pr.solid(WALL_X, yy):
                bad.append("the trading wall: with group 1 %s the doorway at "
                           "(%d,%d) is shut, so the wall has no door at all"
                           % ("ON" if cfg[1] else "OFF", WALL_X, yy))
        if not all(pr.solid(WALL_X, yy)
                   for yy in range(shut_door - GATE_H + 1, shut_door + 1)):
            bad.append("the trading wall: with group 1 %s the doorway at "
                       "(%d,%d) is open too, so the lever trades nothing"
                       % ("ON" if cfg[1] else "OFF", WALL_X, shut_door))
        # ... and both sides stay connected, whichever door is the open one.
        if (WALL_X + 1, TOP_STAND) not in k.reachable_set(
                (WALL_X - 1, TOP_STAND), form="human", switches=cfg):
            bad.append("the trading wall: with group 1 %s the corridor west of "
                       "it cannot reach the corridor east of it. Beat 2 is "
                       "free only because the wall always has exactly one door"
                       % ("ON" if cfg[1] else "OFF"))
    # The slag gate really gates, and the crack really is frog-only.
    shut = {1: False, 2: True}
    if SWITCH_B in k.reachable_set((SHAFT_X0, LOW_STAND), form="human",
                                   switches=shut):
        bad.append("the slag gate at col %d does not seal the shaft's foot "
                   "with group 2 ON: nothing closes behind her" % GATE_NEAR_X)
    if SWITCH_A not in k.reachable_set((SHAFT_X0, LOW_STAND), form="human",
                                       switches=shut):
        bad.append("with the slag gate shut the shaft's foot cannot reach a "
                   "lever: the chain at col %d is what makes that room legal"
                   % SHAFT_CHAIN)
    open_b = {1: False, 2: True}
    if PAD_TILE not in k.reachable_set((26, LOW_STAND), form="human",
                                       switches=open_b):
        bad.append("with group 2 ON the furnace mouth cannot reach the pad: "
                   "the far gate is not open when the lever says it is")
    if PAD_TILE in k.reachable_set((26, LOW_STAND), form="human",
                                   switches={1: False, 2: False}):
        bad.append("with group 2 OFF the furnace mouth still reaches the pad, "
                   "so the far gate gates nothing for the human")
    if SWITCH_B not in k.reachable_set((26, LOW_STAND), form="frog",
                                       switches={1: False, 2: False}):
        bad.append("with the far gate shut the FROG cannot leave the furnace: "
                   "the crack at (%d,%d-%d) is what keeps it honest"
                   % (FURNACE_WALL_X, CRACK_Y0, CRACK_Y1))

    # (f) NO STATE THE PLAYER CAN REACH IS A DEAD END.  The end-to-end
    # question, asked over (room x configuration).  Two runs, because the pad
    # is one-way: the human's objective is the pad, and the frog's is the exit.
    for label, start, goal, form, cfg in (
            ("human, from the spawn", SPAWN, PAD_TILE, "human", None),
            ("frog, from the pad, group 2 ON", PAD_TILE, EXIT_TILE, "frog",
             {1: False, 2: True}),
            ("frog, from the pad, group 2 OFF", PAD_TILE, EXIT_TILE, "frog",
             {1: False, 2: False})):
        for entry, config in _escape(k, start, goal, form, cfg):
            bad.append("ESCAPE (%s): standing at %s with switches %s there is "
                       "no sequence of flips that reaches %s -- that is a "
                       "softlock" % (label, entry, config, tuple(goal)))

    # (g) ONE LEVER PER GROUP, and every lever inside the box its own trigger
    # draws.  SwitchTrigger.aabb() is Rect2(tile*16 + (1,6), (14,10)); a 22 px
    # human standing on the tile spans 16y-6..16y+16 and an 11 px frog spans
    # 16y+5..16y+16, so both cover it -- but only if the lever is on the floor
    # they walk along, which is the trap ruins_4 shipped.
    groups = {}
    for e in g.entities:
        if e["type"] in ("switch_a", "switch_b"):
            groups.setdefault(e["type"], []).append((e["x"], e["y"]))
    for t, places in sorted(groups.items()):
        if len(places) > 1:
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
            for form, box_h in (("human", 22), ("frog", 11)):
                top = (sy + 1) * 16 - box_h
                if top > sy * 16 + 6:
                    bad.append("%s at (%d,%d): the %s's body spans %d..%d and "
                               "the trigger box is %d..%d -- it walks past its "
                               "own lever" % (t, sx, sy, form, top,
                                              (sy + 1) * 16,
                                              sy * 16 + 6, sy * 16 + 16))

    # (h) Every vein is still a vein, still on the BACKGROUND, still visible
    # through open air, and still has the hot band `_hot` owes it.  The first
    # two catch a later helper drawing over it; the third is the readability
    # rule the captures wrote (see the vein pass); the fourth is what makes it
    # glow at all, since a bg tile emits nothing and 281 is what does.
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
            bad.append("vein at (%d,%d) is behind solid rock: nothing will "
                       "ever see it" % (x, y))
        if not any(p.ch(x + dx, y + dy) == hot
                   for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))):
            bad.append("vein at (%d,%d) has no obsidian_hot beside it, so the "
                       "one thing in the level that can emit there does not: "
                       "_hot() only bands the cap and the fill" % (x, y))

    # (i) The relief is relief and not geometry: a niche must have no floor of
    # its own, so nothing can stand in one and the pocket check in (a) skips it.
    for (x, y, w, h) in NICHES:
        for xx in range(x, x + w):
            if p.solid(xx, y + h):
                bad.append("niche at (%d,%d) %dx%d has a floor at (%d,%d): it "
                           "is a room, not relief, and a %d-tile room is a "
                           "squeeze" % (x, y, w, h, xx, y + h, h))

    # (j) The frog is load-bearing and the breakable is optional.  Three claims
    # about the HUMAN's reach from the spawn, in the configuration the level
    # actually starts in.
    human = k.reachable_set(SPAWN, form="human", switches=START_CFG)
    if PAD_TILE not in human:
        bad.append("the human cannot reach pad_frog at %s from the spawn"
                   % (PAD_TILE,))
    if EXIT_TILE in human:
        bad.append("the human can reach the exit at %s without the frog, so "
                   "the pad and the 3-tile treads are decoration" % (EXIT_TILE,))
    if VAULT_HEART in human:
        bad.append("the vault at %s is reachable without breaking the "
                   "nest_crust at col %d; the plug is not sealing anything"
                   % (VAULT_HEART, VAULT_X))

    if bad:
        raise world_kit.WorldKitError(
            "%s: %d self-check failure(s):\n  %s"
            % (LEVEL_ID, len(bad), "\n  ".join(bad)))


def check(k, verbose=True):
    """Everything the kit can say about this level before the prover runs.

    Not proof -- `tools/prove.sh` is.  This is the fast filter for the class of
    error this project has shipped six times, plus the one question the prover
    structurally cannot answer: whether a switch configuration the player is
    allowed to leave the level in has sealed them away from a lever.
    """
    for label, entry, goal, form in RECONFIG_ENTRIES:
        sizes = k.reconfig_check(entry, goal, form=form)
        if verbose:
            print("  reconfig     %-42s %-6s %s" % (label, form, sizes))
    return k.audit(strict_verbs=True)


def main():
    g, k = nest_1()
    for line in check(k):
        print(line)
    _self_checks(g, k)
    print("  palette      missing=%s substituted=%s"
          % (NEST_W5.missing() or "none", NEST_W5.substituted or "none"))
    print("  light        %d authored pools, %d emissive tiles on the fg"
          % (len(AMBIENCE["lights"]),
             sum(1 for y in range(g.h) for x in range(g.w)
                 if g.fg[y][x] in ("r", "S", "^"))))
    write(LEVEL_ID, g, LEVEL_NAME, music="world5")
    print("--- data/ambience.json  levels[\"%s\"] ---" % LEVEL_ID)
    print(json.dumps(AMBIENCE, indent=6))


if __name__ == "__main__":
    main()
