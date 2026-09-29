#!/usr/bin/env python3
"""nest_4 -- THE LAST ASCENT.  World 5, THE OBSIDIAN NEST, fourth level, and the
last ordinary level of the game: the climb to the door of The Obsidian Heart.

Self-contained: running this file under the project python writes
levels/nest_4.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `nest_4()` returning `(Grid, Kit)`,
the tuple that writer's `build()` expects -- it audits the kit before it writes.

    source tools/env.sh && "$PYVENV" tools/worlds/nest_4.py
    tools/prove.sh nest_4
    ITEST_TIMEOUT=300 tools/itest.sh --only=t_replay_nest_4 --trace=1

WHAT THE LEVEL IS ABOUT
-----------------------
nest_1 taught the lever, nest_2 scaled it, nest_3 examined the four forms.  This
one is the game's valediction: it teaches nothing and recalls everything, in the
order the game taught it, climbing the whole time.  Twenty-five rows from spawn
to exit, one leg per world, read bottom-left to top-left:

           +---------------------+---------------------+
   rows    | (0,0) THE HALL      | (1,0) THE GALLERY   |
   1-13    |  W5 + THE LAST STAIR|  W4 the dark        |
           +---------------------+---------------------+
   rows    | (0,1) THE SUMP      | (1,1) THE WELL      |
   16-28   |  W2 the sluice      |  W5 lever + W3 flue |
           +---------------------+---------------------+

  1  THE FOOT (cols 4-8, stand row 27).  Dry apron, one walker, a blade-only
     vault two tiles west of the spawn.  The last quiet ground before the water.

  2  THE SLUICE (cols 9-33, rows 25-27) -- WORLD 2 RECALLED.  Kaya wades east
     off the apron into standing water, and at col 24 the roof comes down to row
     25: the water becomes a pipe two tiles tall with rock over it, so there is
     no surface to swim along and the push is the whole cross-section.  Cols
     27-33 are `water_current_right`, and that tile is the recall:

         Kaya's top speed in water is max_run 108 * water_move_scale 0.62
         = 66.96 px/s.  The current is 68.  Swimming back west she makes
         -66.96 + 68 = +1.04 px/s -- EAST.  The sluice is a one-way door by one
         pixel a second, which is the measured fact THE CISTERN was built on,
         restated in black glass.

     No fish and no pad: she does this as herself.  `data/forms/human.json` has
     `drowns: false`, so a roofed pipe is a swim and not a timer.  Cols 24-26 are
     still water deliberately: the vertical screen seam is x=400, the line
     between cols 24 and 25, and a body inching across it at 1 px/s flips the
     camera back and forth -- the feel defect neither prove.sh nor the tape
     replay can see.  She crosses the seam under her own power and the push
     starts at col 27.

  3  THE WELL AND ITS STAIR (cols 34-42) -- the climb out, and the reason a
     human-only swim is authorable at all.  A human cannot climb out of deep
     water onto a flush shore: this project has measured that at 0.0 px of
     closest approach.  Her water jump rises 0.7*(feet - surface - 10) + 27 px,
     which for this well is:

         surface (water_top) row 25, y=400; the bed row 28, so her feet stand at
         y=448.  Rise = 0.7*(448-400-10) + 27 = 53.6 px, and her feet reach
         y=394.4 -- which CLEARS the ledge's row-25 cap by 5.6 px.  This well is
         two tiles deep, so unlike THE CISTERN's four-tile bays it is not a wall.
         It is worse than a wall: 5.6 px is inside the rounding that made
         jungle_4's 4-tile rungs catch sometimes and drop the player other times,
         which is the one class of defect this project has shipped twice.

     So the well is not jumped out of at all, it is climbed: two steps of
     nest_block sixteen pixels apart, the lower one still under water.

         (36,27) THE STEP  -- stand row 26, feet y=432, one tile of water over it
         (37,26) THE BEACH -- stand row 25, feet y=416, flush with the surface
         (38,25) THE LEDGE -- stand row 24, dry

     THE PROVER PAID FOR THAT SHAPE, and this is the most useful measurement in
     the file.  The first draft was the single jump: step to ledge, two tiles
     across and two rows up.  It PROVED -- and cost 43,882 expansions out of a
     50,000 budget, in a four-minute run, for one jump.  ADR 005 is explicit that
     a hop needing that is evidence the hop is wrong rather than evidence the
     budget is small.  Two things came out of chasing it:

       * `ProverSearch._reached` accepts any state whose body rect OVERLAPS the
         target tile.  With the mark on the lip itself the cheapest way to
         satisfy it is to poke her head into the tile above the lip while still
         in the water at the corner -- so the hop "arrived" submerged and the
         next hop had to make the whole jump again.  Every mark on a shore in
         this level is therefore one tile INLAND: her hitbox is 10 px wide, so
         overlapping (608,384)-(624,400) needs her left edge at x >= 598 and the
         water ends at 592.
       * a two-row climb out of water is a precise search whatever it is aimed
         at, and two one-row steps are not.  Stepped, the same three tiles cost
         5, 13 and 2 expansions and the whole level proves in 2.2 seconds
         instead of four minutes.

  4  LEVER A (40,24) -- WORLD 5'S OWN, TAUGHT UP CLOSE AND THEN AT SCALE.
     Three tiles east of the lever is the flue's gate, `switch_block_a_on` at
     (43,23-24), solid while group A is ON, which is how every level starts.  Two
     tiles over her head at (41-42, 21-22) is the other half of the same lever in
     `switch_block_a_off`.  Throw it and the gate sinks and the ceiling grows
     teeth, both inside one screen, which is this world's rule stated where the
     player is looking.  THE COMB, sixteen rows up and a screen across, is the
     same throw doing the same thing in a room the lever cannot see -- which is
     nest_2's finding and this world's scale mechanism.

  5  THE FLUE (cols 43-47, rows 8-24) -- WORLD 3 RECALLED.  `updraft` (206) is
     [0,-400]: seventeen rows in about 1.3 s, and the one leg with a second form
     in it.

         The BIRD's fall cap inside the column is max_fall 190 - 400 = -210 px/s,
         thirteen tiles a second, for no stamina at all -- THE LONG GLIDE's
         measurement, and the reason nothing here asks for a flap.
         KAYA HERSELF also rises in it: 330 - 400 = -70 px/s, four tiles a
         second.  That is why stepping off the east end of the landing is not a
         death: the mouth catches her and hands her back.

     `pad_bird` is on the LEDGE and not in the column, because the column has no
     floor a body can rest on -- see ADR 004.  `pad_human` is on the landing at
     the top, one tile west of the mouth.

  6  THE GALLERY (cols 14-42, stand row 7) -- WORLD 4 RECALLED, AND THE PART
     THAT IS GEOMETRY RATHER THAN AMBIENCE.  `Ambience` has ONE darkness value
     per level and no gradient and no per-region band, and this world does not
     use the key at all -- the dark is World 4's verb and World 5's is the lever
     (nest_1's grammar, nest_2 and nest_3 verbatim).  So "a dark stretch in the
     middle" is not a shade, it is WHERE THE LIGHT IS NOT:

         * every authored pool in this level is in a room the player has to read
           -- the foot, the sump, the well, the ledge and lever A, the hall and
           lever B, the last stair, and the flue's own mouth at the landing;
         * cols 23-38 -- the flat, the comb and the fault -- carry NO authored
           pool at all.  Everything that glows in there is a tile: `obsidian_hot`
           (281) banded around every nest_vein by `_hot()`, and `nest_shard`
           (287) itself, which glows for the reason deeps_1's spore does -- a
           hazard you cannot see is not a lesson, it is a coin toss;
         * the gallery is roofed at row 3 and its bg is `nest_wall`, so no
           parallax reaches it and nothing lifts it, while the rooms at both ends
           get `nest_void` and depth.

     What that buys is contrast rather than blindness, and the difference is
     worth stating: with no `darkness` key a pool-less room is not black, it is
     unlit -- the tiles are still drawn.  A player reads the fault by its hot
     banding and its glowing shards against sixteen columns with no gold and no
     ember pool in them, which is the strongest version of World 4 this world's
     own grammar can say.  The entry is printed by `main()`.

  7  THE COMB (cols 27-31) and THE FAULT (cols 32-36), the two things in the
     unlit stretch.

         THE COMB is lever A's callback.  `switch_block_a_off` teeth hang from
         rows 4-5 at cols 27, 29 and 31 and `switch_block_a_on` pillars fill rows
         4-7 at cols 28 and 30, so with A thrown the teeth are the wall and the
         floor is clear, and with A un-thrown the pillars are the wall and the
         gallery is cut in half.  The player walks under the teeth they made.

         THE FAULT is a two-row trench with a bed of shards in the bottom of it,
         crossed westward: off the landing, drop two rows, jump the shards, climb
         two rows out.  Two tiles of shards, not three, and the reason is
         nest_3's measurement -- `Kit.reachable_set` enumerates dx <= gap, so a
         three-tile hole is four tiles of travel and the conservative flood every
         check in this file runs on reports it as impassable even though the
         prover clears it.  A filter that cannot cross the level's own jump
         reports the level as a softlock.  Landing IN the bed costs a heart and
         the climb out, never a life: it is a floor with shards on it and not a
         pit.

  8  LEVER B (21,5) IN THE HALL, and the two doors it moves.  `switch_block_b_off`
     is solid exactly while group B is OFF, which is how the level starts, so
     both are shut when she arrives:

         B1  col 13, rows 6-7   the hall's door into the last stair
         B2  col  4, rows 2-3   THE BOSS DOOR'S SHUTTER, eleven tiles away at
                                the top of the stair, in a room the lever cannot
                                see.  The last lever in the game opens the last
                                two doors in the game, and the player meets the
                                second one already open.

     The lever is on a nest_block bracket two rows over the walking lane, seven
     tiles east of the door, and all three numbers are load bearing:

         * ON A BRACKET, because a blade thrown from inside the doorway flies
           along the row it was thrown on (`boomerang_blade` is `rise` -8, flat,
           seven tiles at `max_range` 118).  A lever in the lane would be in that
           line, and flipping B while standing IN the gate is a switch block
           turning solid around a body.  Two rows up, it is not in the line.
         * SEVEN TILES EAST OF THE DOOR, because the WINDOW is over the door and
           a bracket beside it would let a player jump from the bracket into the
           window and skip the door entirely.  LIMITS["human"]["gap"] is 3 and
           the kit itself records that 4 and 5 both PROVE, so the margin that
           matters is the measured ceiling and not the table: seven is out of
           reach of anything this game has ever proved.
         * LIT, and it is the only authored pool in the gallery's west half,
           because a lever nobody finds in the unlit stretch is a level nobody
           finishes.

  9  THE WINDOW (col 13, rows 3-4) -- the drain, and the reason this level has no
     softlock.  A gate cuts a level in two and the lever is on one side of it;
     the side without it is the trap every switch level invites.  So the wall
     OVER the door is open, permanently:

         from the stair room's first ledge (stand row 5) the window is one row up
         and two tiles across -- inside her measured envelope.  From the gallery
         floor its feet row is THREE rows up and her measured rise is two, and
         there is nothing on the gallery side to stand on to shorten that.

     So the last stair always drains back into the gallery, in every
     configuration, and the gallery always holds lever B -- while the only way UP
     is still the door.  A wrong throw costs a lap and never a save, which is
     nest_2's standard set.  Check (g) proves it rather than asserting it.

     The hall's roof is raised to row 1 over cols 14-22 for one reason, and it is
     not scenery: a body is two tiles, so stepping EAST out of a window whose
     feet row is 4 needs rows 3 AND 4 clear on the far side.  Under the gallery's
     own roof at row 3 the window would be an alcove a body can enter and never
     leave sideways, which is defect 3 with the ceiling instead of the door.

 10  THE LAST STAIR (cols 1-12) -- the quiet.  Three ledges, a heart, gems, and
     nothing else: no lever, no hazard, no enemy, no dark.  The only screen in
     World 5 that asks for nothing.  Then the boss's door, already open.

THE FALL RULE, WHICH IS THE FAIRNESS BAR AND NOT A HOPE
-------------------------------------------------------
Every fall in this level lands somewhere that costs the climb:

    off the ledge at lever A        -> the well, which has the stair in it
    into the flue's mouth           -> the flue lifts you back to the landing
    into the fault                  -> the trench floor, two rows down
    into the shard bed              -> one heart, then walk off it
    off any stair ledge             -> the stair room's own floor
    through the window              -> the gallery, seven tiles from lever B

There is no hazard under any jump on the route except the fault's own bed, no
bottomless drop anywhere in the level, and nothing that can be entered and not
left.  Check (g) is the machine version of that paragraph.

ADR 004 -- NO TRANSFORM STRANDS YOU, AND NO CONFIGURATION DOES EITHER
---------------------------------------------------------------------
Two forms and two pads, and the argument is about three rooms:

  * BELOW THE FLUE Kaya is herself.  The sluice is one-way, but the ledge is the
    top of it and lever A is ON the ledge, so the bottom of the level never
    becomes a room with no way on.
  * THE COLUMN HAS NO STANDABLE TILE.  Every tile of cols 44-46 between rows 8
    and 24 is updraft, and a body in an updraft has a negative fall cap: it is
    lifted off the floor on the tick it touches it.  That is why the flue's foot
    is not an entry in RECONFIG_ENTRIES, and why `_Nav` models the whole column
    as a single edge -- enter it anywhere and you are on the landing.  The
    column cannot be descended by anything, which is also what makes group A
    permanently OFF above the flue: the only thing that sets it is `switch_a`,
    and `switch_a` is at the bottom.
  * ABOVE THE FLUE the bird can fly wherever the gallery is clear and
    `pad_human` is on the landing, which is the gallery's own floor -- so a
    player who stays a bird is never stranded, and skips nothing either: the
    gallery is a two-to-four row corridor, the comb is two rows under its teeth,
    and a bird has no altitude to spend in either.  A bird that flies back down
    to the ledge can always ride the flue again, because lever A is on the ledge
    with it.

WHY THIS LEVEL QUOTES TWO VERBS THE WORLD DOES NOT OWN
------------------------------------------------------
`world_kit.NEST` declares roles for `water` and `water_top` and declares no
`cur_*` or `updraft` role at all.  The characters are `shared` in
data/level_legend.json -- '>' and 'U' among them -- so a nest level can paint
them and they are the real tiles with the real pushes.  nest_3 checked that and
declined on purpose: it is the exam of the four bodies, and an updraft there
would do the bird's work for it.

This level accepts both, for the opposite reason.  It is the farewell, its
subject IS the other four worlds, and a recalled lesson has to be the lesson: a
switch-gated imitation of a current is a corridor with a story about a current
attached to it.  So the sluice is a real current and the flue is a real
draught, both re-staged in obsidian -- the pipe is the Nest's coolant sluice
under thirteen tiles of rock and the column is a flue with `nest_flue` drawn up
the back of it -- and `audit(strict_verbs=True)` is clean, which means no verb
in here is an understudy.  World 4's verb is the one thing this level does NOT
quote, because `darkness` is a whole-level value and a quoted darkness would
darken the farewell as well as the recall.  Leg 6 is what that costs and how it
is paid.

THE BLADE AND THE PROVER
------------------------
`ProverSearch.action_set()` has no ATTACK in it and `ProverSim.snapshot()`
carries no broken-tile set, so the prover can neither break a tile nor throw the
blade at a lever.  Two rules fall out:

  * BOTH LEVERS ARE THROWN BY CONTACT on the proved route.  The trigger box is
    the bottom ten pixels of the tile inset one pixel a side (level.gd:
    `sw.setup(p + Vector2(1, 6), ...)`, `SwitchTrigger.SIZE` 14x10) and it trips
    at 6 px of bottom-edge penetration; a human resting on the tile's floor
    spans [-6, 16] of it and a bird [7, 16].  Both overlap.  Check (h)
    re-derives that from data/forms/*.json rather than trusting this paragraph.
  * THE ONE BREAKABLE IS OFF THE ROUTE.  `nest_crust` (291) declares no
    `break_hold`, so `FormBase._break_target_of` skips it and only the blade
    opens it -- which is where a weapon-only wall belongs, two tiles from a
    spawn that is holding one.  Check (i) fails the build if a hop's bounding
    box contains it.

WHERE THE FLOORS SIT, AND THE THREE SEAMS
-----------------------------------------
`CameraController` picks its screen from the body's CENTRE and freezes the sim
for 0.12 s while it flips, so a 22 px body on a floor whose cap row is a
multiple of 15 has its feet on the seam and its centre on the screen above --
which never draws the floor it is standing on.  That is the defect ruins_4
shipped.  The stand rows here are 27, 24, 9, 7, 5, 3 and 2, and check (b) fails
the build on any claim or entity standing on a cap row divisible by 15.

The route crosses a seam three times:

    hop  3  sump_e -> pipe_in     x=400, WADED along the pipe's own floor, in
                                  still water, which is why cols 24-26 carry no
                                  push
    hop 13  flue_2 -> flue_3      y=240, FLOWN, straight up the middle of a
                                  three-column column of rising air
    hop 19  comb_w -> flat_w      x=400, WALKED, flat, along unbroken floor

No on-foot hop changes screen except hops 3 and 19, and both are flat.  Check
(c) is that rule; SEAM_EXEMPT names the flown one with its reason.

THE PALETTE
-----------
`Palette.char()` resolves a tile NAME through the flat, jungle-derived `legend`
key of data/level_legend.json, so THE OBSIDIAN NEST's own names have no
character there and fall through to UNDERSTUDY -- where `solid` would emit 's'
(nest_plate, the second solid) and `bg` would emit 'r' (nest_vein, a background
accent).  That is the memory note "world_kit ruins palette emits wrong stone",
in World 5.  So every role is declared as the JUNGLE tile that owns the
character the nest tileset binds to the art we want.

The role table is nest_2's and nest_3's, unchanged on purpose -- the mass is
obsidian ('#'), the built walls are nest_block ('d') through the `block` role,
and nest_plate ('s') is declared and never drawn because a plate is an object
and not a mass.  Note that `world_kit.NEST` names those two roles the other way
round; the CHARACTER is what the game reads, which is why every floor here is
`depth=1` -- `Kit.floor`'s fill role is `packed`, and in this spelling that is
the tile this world agreed not to paint.  Two roles are added to the table that
the other three nest levels leave out, `cur_right` and `updraft`, for the reason
above.  `Palette.missing()` is empty, `substituted` stays empty, and the level
serialises `"tileset": "nest"`.
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
                       BODY_TILES, path_clear, check_gap)

LEVEL_ID = "nest_4"
LEVEL_NAME = "THE LAST ASCENT"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the nest role character.
## A character map, not an art claim: the art comes from `"tileset": "nest"` at
## load time.  Identical to nest_2's and nest_3's, plus the two shared verb
## characters this level quotes -- see WHY THIS LEVEL QUOTES TWO VERBS.
NEST_W5 = Palette("obsidian_nest", {
    "bg": "bg_leaves",              # 'L' -> 282 nest_wall
    "solid": "grass_top",           # '#' -> 280 obsidian      (the mass)
    "solid_alt": "stone_mossy",     # 'S' -> 281 obsidian_hot  (the hot face)
    "block": "dirt",                # 'd' -> 283 nest_block    (built walls)
    "packed": "stone",              # 's' -> 290 nest_plate    (declared, unused)
    "oneway": "wood_platform",      # '=' -> 286 nest_ledge
    "ladder": "vine",               # '|' -> 288 nest_chain    (declared, unused)
    "hazard": "spikes",             # '^' -> 287 nest_shard
    "breakable": "crate",           # 'c' -> 291 nest_crust    (blade only)
    "shoulder": "cracked_stone",    # 'k'  shared 211 (declared, unused)
    "rubble": "rubble",             # 'o'  shared (unused)
    "decor": "tree_trunk",          # 'T' -> 285 nest_flue
    "void": "bg_dark",              # 'X' -> 284 nest_void
    "water": "water",               # 'w'  shared 8
    "water_top": "water_top",       # '~'  shared 7
    "cur_right": "water_current_right",   # '>'  shared 200, [68, 0]
    "updraft": "updraft",                 # 'U'  shared 206, [0, -400]
    "switch_a_on": "switch_block_a_on",    # 'A' shared, 11
    "switch_a_off": "switch_block_a_off",  # 'a' shared, 26
    "switch_b_on": "switch_block_b_on",    # 'B' shared, 12 (declared, unused)
    "switch_b_off": "switch_block_b_off",  # 'b' shared, 27
})


# ---------------------------------------------------------------- the shape
## Every number the geometry and the checks share, in one place.

SEAM_COL = 25                   # first column of the eastern screens (x=400)
SEAM_ROW = 15                   # first row of the lower screens (y=240)
EAST_WALL = 48                  # the level is cols 1..47

# -- the lower band: the foot, the sluice, the well, the ledge ----------------
LOW_CAP, LOW_STAND = 28, 27     # the foot's floor and the sluice's bed
LOW_ROOF = 21                   # rock above everything down here
VAULT_X0, VAULT_X1 = 1, 2       # the blade-only vault, rows 26-27
CRUST_COL = 3                   # its nest_crust plug
SPAWN = (5, LOW_STAND)
SUMP_X0, SUMP_X1 = 9, 23        # open water with air over it
SURFACE = 25                    # the water_top row; water runs 26-27
PIPE_X0, PIPE_X1 = 24, 33       # two tiles tall under rock
PUSH_X0 = 27                    # where `water_current_right` starts
WELL_X0, WELL_X1 = 34, 37       # water_top runs the whole width; 36-37 are the
                                # stair out of it
DEEP_X1 = 35                    # the last column with two tiles of water in it
STEP = (36, 27)                 # the submerged step: stand row 26
BEACH = (37, 26)                # its top step: stand row 25, flush with SURFACE
LEDGE_X0, LEDGE_X1 = 38, 42     # cap 25 -> stand 24
LEDGE_CAP, LEDGE_STAND = 25, 24
SWITCH_A = (40, LEDGE_STAND)
PAD_BIRD = (42, LEDGE_STAND)
TABLEAU = (41, 21, 2, 2)        # switch_block_a_off over the ledge's east end

# -- the flue ----------------------------------------------------------------
FLUE_W_WALL = 43                # rows 8-22; its foot at rows 23-24 is the gate
FLUE_X0, FLUE_X1 = 44, 46       # the column: updraft, rows 8-24
FLUE_E_WALL = 47
FLUE_TOP, FLUE_BOT = 8, 24
MOUTH = (44, 45)                # the two columns the roof claim keeps open

# -- the upper band: the landing, the gallery, the hall, the stair -----------
GAL_CAP, GAL_STAND = 8, 7       # the gallery's floor, from the door to the flue
GAL_ROOF = 3
GAL_X0, GAL_X1 = 14, 42
LANDING_X0, LANDING_X1 = 37, 42  # capped level with the top of the column
PAD_HUMAN = (41, GAL_STAND)
FAULT_X0, FAULT_X1 = 32, 36     # the trench: cap 10 -> stand 9
FAULT_CAP, FAULT_STAND = 10, 9
SHARDS_X0, SHARDS_W = 33, 2     # two tiles, never three: see leg 7
COMB_X0, COMB_X1 = 27, 31       # teeth on the odd columns, pillars on the even
COMB_TEETH = (4, 2)             # rows 4-5, hanging off the roof at row 3
COMB_PILLAR = (4, 4)            # rows 4-7, floor to roof
HALL_X0, HALL_X1 = 14, 22       # roof raised to row 1: see leg 9
HALL_ROOF = 1
BRACKET_X0, BRACKET_W, BRACKET_CAP = 20, 3, 6   # cap 6 -> stand 5
SWITCH_B = (21, 5)
B1_COL = 13                     # the hall's door: rows 6-7
WINDOW = (13, 3, 2)             # col, top row, height: the drain over the door
STAIR_X0, STAIR_X1 = 1, 12
S1_X0, S1_W, S1_CAP = 9, 4, 6   # cols 9-12,  stand 5
S2_X0, S2_W, S2_CAP = 5, 4, 5   # cols 5-8,   stand 4
S3_X0, S3_W, S3_CAP = 1, 4, 4   # cols 1-4,   stand 3
B2_COL = 4                      # the boss door's shutter: rows 2-3, standing
                                # across the top tread four tiles from the door
EXIT_TILE = (2, 3)

## What tools/solver/sim.gd seeds before a switch entity is touched: TileWorld's
## own defaults, group 1 ON and group 2 OFF.  Both levers declare the same, so
## `SwitchTrigger._ready()` agrees.
START_CFG = {1: True, 2: False}
CFGS = [{1: a, 2: b} for a in (True, False) for b in (True, False)]

## (col, solid_when, group, top, stand, why) for every full-height plug.  Check
## (e) reads this table rather than the prose above it.
PLUGS = [
    (FLUE_W_WALL, "on", "a", FLUE_BOT - 1, FLUE_BOT,
     "A1: the flue's gate, three tiles from its own lever"),
    (B1_COL, "off", "b", GAL_STAND - 1, GAL_STAND,
     "B1: the hall's door into the last stair"),
    (B2_COL, "off", "b", 2, 3,
     "B2: the boss door's shutter, eleven tiles from its lever"),
]

## Every nest_vein tile: this level's light.  Each is an AIR tile on the bg layer
## with rock beside it, and `_hot()` bands that rock with obsidian_hot -- which
## is the tile that actually emits, because `AmbienceLayer._collect_emissive`
## scans the fg and 289 is a background tile by its own art.  nest_1 settled
## that, nest_2 and nest_3 re-checked it, and (j) does here.
##
## THE FAULT'S FOUR ARE THE POINT OF THE LIST.  The unlit stretch carries no
## authored pool at all, so the only thing that marks the trench's two take-offs
## and its two safe tiles is the hot band these put there.  See leg 6.
VEINS = [
    (4, LOW_STAND), (7, LOW_STAND),                          # the foot's floor
    (11, LOW_ROOF + 1), (17, LOW_ROOF + 1), (22, LOW_ROOF + 1),
    (35, LOW_ROOF),                                          # the well's roof
    (38, LEDGE_STAND), (41, LEDGE_STAND),                    # lever A's ledge
    (38, GAL_STAND), (40, GAL_STAND),                        # the landing
    (32, FAULT_STAND), (35, FAULT_STAND),                    # the trench's floor
    (31, GAL_STAND), (37, GAL_STAND),                        # its two lips
    (26, GAL_STAND), (29, GAL_STAND),                        # the comb's floor
    (16, GAL_STAND), (20, GAL_STAND),                        # the hall
    (WINDOW[0], WINDOW[1]),                                  # THE WINDOW's head:
    # the drain is a dark slot in a dark wall and the first capture run could
    # not find it. This is the one vein in the level placed to make a piece of
    # GEOMETRY read rather than to light a room: `_hot()` bands the lintel over
    # it, so the way back down announces itself from the gallery floor.
    (3, GAL_STAND), (11, GAL_STAND), (12, 5), (1, 2),        # the last stair
]


def _hot(k):
    """Band the rock a vein touches with obsidian_hot.

    280 and 281 are both plain `solid` -- the same tile to every flag-reading
    checker -- so this is colour and nothing else.  Generated from VEINS rather
    than listed by hand, because the claim is "the glass is hot WHERE THE VEIN
    IS" and a hand-written band drifts off its vein the first time one moves.

    Only the mass and the built walls are repainted: a ledge, a shard or a switch
    block beside a vein keeps its own art, because each of those is a verb and a
    recoloured verb stops reading as itself.
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
    forced -- and it is also what check (d) wants: rock over every switch tile,
    in every configuration, so nothing can ever stand on one.
    """
    k.switch_gate(col, stand, stand - top + 1, group=group,
                  solid_when=solid_when)
    k.put(col, top - 1, "block")
    k.note("%s at col %d: switch_block_%s_%s, %d tiles, rows %d-%d"
           % (why, col, group, solid_when, stand - top + 1, top, stand))
    return col


def _air_mark(k, name, x, y):
    """A waypoint in mid-air, for the bird.

    Not `Kit.mark`: that files a "stand" claim and nothing inside a column of
    rising air is standable.  `ProverSearch._reached` accepts arrival with no
    floor under the body when the form is the bird -- it is the one form that can
    be somewhere and stay there without one -- so what this promises instead is
    that the tile is still OPEN after everything else was drawn over it.
    """
    k.g.mark(name, x, y)
    k._claim("clear", "air waypoint '%s' (bird)" % name, x=x, y=y,
             tall=BODY_TILES)
    return name


def _wet_mark(k, name, x, y):
    """A waypoint inside the sluice: wet and clear rather than standable.

    Kaya walks the pipe's floor rather than swimming it -- `form_human.gd` runs
    `run_axis` with `water_move_scale` and `apply_gravity` with the water cap, so
    on_floor is true down there -- but the tile is water and the claim that
    matters is that it still is.
    """
    k.g.mark(name, x, y)
    k._claim("wet", "sluice waypoint '%s'" % name, x=x, y=y, tall=1)
    k._claim("stand", "sluice waypoint '%s'" % name, x=x, y=y, form="human")
    return name


# ---------------------------------------------------------------- the level

def nest_4():
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

    # ========================================================= 1 -- THE FOOT
    # Rows 22-27, floor capped on row 28 -> stand row 27.  `depth=1`: the mass
    # under it is already obsidian and `Kit.floor`'s fill role is `packed`, which
    # in this world's spelling is the tile the other three levels agreed not to
    # paint.
    k.clear_rect(CRUST_COL + 1, LOW_ROOF + 1, SUMP_X0 - CRUST_COL - 1,
                 LOW_CAP - LOW_ROOF - 1)
    k.floor(1, LOW_CAP, SUMP_X0 - 1, depth=1)

    # THE BLADE VAULT.  `nest_crust` (291) declares no `break_hold`, so
    # shouldering does nothing and only the blade opens it.  Two tiles west of a
    # spawn that is holding one, sealed on every other side, and off every hop:
    # the prover cannot break a tile at all.
    k.clear_rect(VAULT_X0, LOW_STAND - 1, VAULT_X1 - VAULT_X0 + 1, BODY_TILES)
    k.breakable_wall(CRUST_COL, LOW_STAND, BODY_TILES, role="breakable",
                     form="human")

    # =================================== 2 -- THE SLUICE (World 2 recalled)
    # The sump is open water with three rows of air over it; the pipe is two
    # tiles tall with rock on row 25, so there is no surface to swim along and
    # the push is the whole cross-section.  That is what makes it one-way: on a
    # surface a body only feels the area-weighted share of it.
    k.clear_rect(SUMP_X0, LOW_ROOF + 1, SUMP_X1 - SUMP_X0 + 1,
                 LOW_CAP - LOW_ROOF - 1)
    k.rect(SUMP_X0, SURFACE, SUMP_X1 - SUMP_X0 + 1, 1, "water_top")
    k.rect(SUMP_X0, SURFACE + 1, SUMP_X1 - SUMP_X0 + 1, 2, "water")
    # Cols 24-26 are still water: the seam at x=400 is crossed under her own
    # power.  Cols 27-33 are 68 px/s against her 66.96.
    k.rect(PIPE_X0, SURFACE + 1, PUSH_X0 - PIPE_X0, 2, "water")
    k.rect(PUSH_X0, SURFACE + 1, PIPE_X1 - PUSH_X0 + 1, 2, "cur_right")

    # ============================================ 3 -- THE WELL AND THE LEDGE
    k.clear_rect(WELL_X0, LOW_ROOF, WELL_X1 - WELL_X0 + 1, LOW_CAP - LOW_ROOF)
    k.rect(WELL_X0, SURFACE, WELL_X1 - WELL_X0 + 1, 1, "water_top")
    k.rect(WELL_X0, SURFACE + 1, DEEP_X1 - WELL_X0 + 1, 2, "water")
    k.rect(STEP[0], SURFACE + 1, 1, 1, "water")      # one tile of water over the step
    # THE STAIR OUT OF THE WELL: two steps of nest_block, sixteen pixels each,
    # with the water still over the lower one.  Every number behind it is in leg
    # 3 and the reason it is a stair rather than the single jump the first draft
    # had is in leg 3's second half: the jump proves and costs 43,882 expansions
    # out of 50,000, which ADR 005 says is a hop that should not exist.
    k.put(STEP[0], STEP[1], "block")
    k.rect(BEACH[0], BEACH[1], 1, LOW_CAP - BEACH[1], "block")
    k._claim("stand", "the well's submerged step, which is how anything that "
             "falls in here gets out", x=STEP[0], y=STEP[1] - 1, form="human")
    k._claim("stand", "the well's beach, flush with the surface",
             x=BEACH[0], y=BEACH[1] - 1, form="human")

    k.clear_rect(LEDGE_X0, LOW_ROOF, LEDGE_X1 - LEDGE_X0 + 1,
                 LEDGE_CAP - LOW_ROOF)
    k.floor(LEDGE_X0, LEDGE_CAP, LEDGE_X1 - LEDGE_X0 + 1, depth=1)

    # ==================================================== 4 -- LEVER A's HALF
    # The half of group A that APPEARS when the lever is thrown, hung from the
    # ledge's own ceiling two tiles over her head and three tiles from the gate
    # that sinks in the same frame.  Never standable: rock on row 20 above it,
    # and under it the two tiles of headroom the ledge already promises.
    k.switch_lattice(*TABLEAU, group="a", pattern="columns", phase=0)
    k.rect(TABLEAU[0], TABLEAU[1], TABLEAU[2], TABLEAU[3], "switch_a_off")

    # =========================================== 5 -- THE FLUE (World 3)
    # Interior cols 44-46, rows 8-24; walls on 43 and 47.  `Kit.shaft` stops the
    # west wall two tiles above the bottom and carves the foot, so the way in is
    # col 43 at rows 23-24 (defect 5), and it refuses to cap the top across its
    # full width (defect 6).  No floor is drawn inside: rows 25+ of cols 44-46
    # are the fill, and nothing can stand on row 24 anyway -- the push is
    # -400 px/s against a fall cap of 330 (Kaya) and 190 (the bird).
    k.updraft_shaft(FLUE_W_WALL, FLUE_X1 - FLUE_X0 + 1, FLUE_TOP, FLUE_BOT,
                    mouth=MOUTH)

    # ============================== 6 -- THE GALLERY (World 4) and the head
    # One roof at row 3 and one floor capped on row 8 from the door to the
    # landing.  Stand row 7, never 14: the horizontal seam is the line between
    # rows 14 and 15 and nothing in this level stands near it -- the flue crosses
    # it vertically at 210 px/s instead, which is the one way to cross a seam
    # that cannot thrash.
    k.clear_rect(GAL_X0, GAL_ROOF + 1, GAL_X1 - GAL_X0 + 1,
                 GAL_CAP - GAL_ROOF - 1)
    k.clear_rect(FLUE_W_WALL, GAL_ROOF + 1, EAST_WALL - FLUE_W_WALL,
                 GAL_CAP - GAL_ROOF - 1)          # the flue's head, over its walls
    # THE HALL: the corridor opens out over its last nine columns and the two
    # extra rows of roof are load bearing rather than scenic -- see leg 9.
    k.clear_rect(HALL_X0, HALL_ROOF + 1, HALL_X1 - HALL_X0 + 1,
                 GAL_CAP - HALL_ROOF - 1)
    k.floor(GAL_X0, GAL_CAP, GAL_X1 - GAL_X0 + 1, depth=1)

    # THE FAULT.  Two rows down for five columns with a bed of shards in the
    # bottom of it.  Drawn after the gallery floor, which it cuts through.
    k.clear_rect(FAULT_X0, GAL_CAP, FAULT_X1 - FAULT_X0 + 1,
                 FAULT_CAP - GAL_CAP)
    k.floor(FAULT_X0, FAULT_CAP, FAULT_X1 - FAULT_X0 + 1, depth=1)
    k.rect(SHARDS_X0, FAULT_CAP, SHARDS_W, 1, "hazard")
    # The jump is declared so `audit()` re-checks it after everything else is
    # drawn: two tiles of shards is three tiles of travel, west, and the landing
    # is the two safe tiles at the trench's west end.
    k.gap(SHARDS_X0, FAULT_STAND, SHARDS_W, form="human",
          landing_w=SHARDS_X0 - FAULT_X0 + 1)

    # THE COMB, lever A's callback.  Teeth hang from the roof at rows 4-5 and
    # pillars fill rows 4-7 floor to roof, alternating, so exactly one of the two
    # is solid at a time: with A thrown the floor is clear and the teeth are
    # overhead, and with A un-thrown the pillars cut the gallery in half.  Both
    # halves have rock directly over their heads, which is check (d)'s rule and
    # the reason the pillars run all the way up instead of stopping at row 6.
    for x in range(COMB_X0, COMB_X1 + 1):
        if (x - COMB_X0) % 2 == 0:
            k.rect(x, COMB_TEETH[0], 1, COMB_TEETH[1], "switch_a_off")
        else:
            k.rect(x, COMB_PILLAR[0], 1, COMB_PILLAR[1], "switch_a_on")

    # ======================================== 8 -- LEVER B AND ITS BRACKET
    # nest_block, two rows over the walking lane, seven tiles east of the door.
    # All three numbers are argued in leg 8; the short version is that a lever in
    # the lane is in the line a blade thrown from the doorway flies along, and a
    # bracket beside the window is a bracket you can jump into the window from.
    k.ledge(BRACKET_X0, BRACKET_CAP, BRACKET_W)

    # ========================== 9 -- THE DOOR, THE WINDOW AND THE LAST STAIR
    # The wall is col 13, which is fill.  The door is punched through it and
    # plugged below; the window above it is never plugged.
    k.doorway(B1_COL, GAL_STAND, h=BODY_TILES)
    k.clear_rect(WINDOW[0], WINDOW[1], 1, WINDOW[2])

    k.clear_rect(STAIR_X0, HALL_ROOF, STAIR_X1 - STAIR_X0 + 1,
                 GAL_CAP - HALL_ROOF)
    k.floor(STAIR_X0, GAL_CAP, STAIR_X1 - STAIR_X0 + 1, depth=1)
    k.ledge(S1_X0, S1_CAP, S1_W)
    k.ledge(S2_X0, S2_CAP, S2_W)
    k.ledge(S3_X0, S3_CAP, S3_W)

    # --------------------------------------------------------------- the doors
    for col, solid_when, group, top, stand, why in PLUGS:
        _plug(k, col, top, stand, group, solid_when, why)

    # -------------------------------------------------------------- dressing
    # THE FLUE'S OWN ART goes behind the column.  `nest_flue` (285) is a column
    # of glass with the heat running up the inside of it, drawn as background,
    # which is exactly what this shaft is -- and it makes the one lane in the
    # level that moves you look like it moves you, which is the legibility fix
    # heights_4 had to make with a dark wall behind its draughts.
    k.rect(FLUE_X0, GAL_ROOF + 1, FLUE_X1 - FLUE_X0 + 1,
           FLUE_BOT - GAL_ROOF, "decor", "bg")
    # `nest_void` behind the rooms that open out, so they read as depth; the cut
    # rooms keep the dark `nest_wall`.  The gallery is deliberately NOT in here:
    # its whole job is to have nothing in it that lifts, and void with a vein in
    # it is the brightest background this world has.
    k.rect(SUMP_X0, SURFACE, PIPE_X1 - SUMP_X0 + 1, 3, "void", "bg")
    k.rect(STAIR_X0, HALL_ROOF, STAIR_X1 - STAIR_X0 + 1, GAL_CAP - HALL_ROOF,
           "void", "bg")
    k.rect(LEDGE_X0, LOW_ROOF, LEDGE_X1 - LEDGE_X0 + 1, LEDGE_CAP - LOW_ROOF,
           "void", "bg")
    # Flues hang from a roof and stop there.  A dark column running floor to
    # ceiling reads as "looks like a passage, behaves like a wall" with its coat
    # inside out, which nest_1's captures caught.
    for fx in (6, 12, 19):
        k.rect(fx, LOW_ROOF + 1, 1, 3, "decor", "bg")
    for fx in (16, 24, 30, 39):
        k.rect(fx, GAL_ROOF + 1, 1, 3, "decor", "bg")
    for fx in (3, 9):
        k.rect(fx, HALL_ROOF + 1, 1, 3, "decor", "bg")

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
    g.ent("pad_bird", *PAD_BIRD)
    g.ent("pad_human", *PAD_HUMAN)
    g.ent("switch_b", *SWITCH_B)
    g.ent("exit", *EXIT_TILE)

    # Six enemies in fifty by thirty, none of them in the last room and none on a
    # route tile.  `tools/itest.sh` replays the proof tape with every one of them
    # alive, so each holds a line a PLAYER has to plan around rather than a tile
    # the tape walks over.
    #
    # TWO ROOMS ARE DELIBERATELY EMPTY and both are teaching frames: the apron
    # she spawns on and the ledge lever A is on.  The first draft had a walker
    # on each, and the capture run argued them out -- walker.json chases from
    # 96 px at 54 px/s, so the apron one reached Kaya during the title card and
    # the ledge one had her in knockback in the one frame this level most needs
    # read.  A lever, its gate and the blocks it raises are a sentence; an enemy
    # standing in the middle of it is a fight.
    g.ent("enemy_swimmer", 16, SURFACE + 1)          # the sump, off the floor
    g.ent("enemy_swimmer", DEEP_X1, SURFACE + 1)     # the well, as she climbs out
    g.ent("enemy_walker", LANDING_X0 + 1, GAL_STAND)  # the landing, guarding the
                                                      # flue's mouth
    g.ent("enemy_flyer", 23, 5, axis="x", range=32)  # the unlit flat
    g.ent("enemy_charger", 26, GAL_STAND)            # 165 px/s, unlit, on a
                                                     # floor it cannot leave
    g.ent("enemy_dropper", 34, GAL_ROOF + 1)         # the roof over the shards

    # NO GEM SHARES A TILE WITH A LEVER OR A PAD: Pickup draws over the trigger's
    # sprite, and nest_2's first captures lost switch_b behind one.
    g.ent("heart", VAULT_X1, LOW_STAND)              # behind the crust
    g.ent("heart", FAULT_X0 + 1, FAULT_STAND)        # the far side of the shards
    g.ent("heart", S2_X0 + 2, S2_CAP - 1)            # the breath before the boss
    for (x, y) in [(4, LOW_STAND), (8, LOW_STAND), (13, SURFACE + 1),
                   (20, SURFACE + 1), (29, SURFACE + 2), (35, SURFACE + 1),
                   (38, LEDGE_STAND), (45, 18), (45, 12),
                   (38, GAL_STAND), (36, FAULT_STAND), (31, GAL_STAND),
                   (27, GAL_STAND), (24, GAL_STAND), (19, GAL_STAND),
                   (21, 4), (11, S1_CAP - 1), (5, S2_CAP - 1),
                   (3, S3_CAP - 1)]:
        g.ent("gem", x, y)

    # ----------------------------------------------------- the route (ADR 005)
    # Twenty-five short hops rather than five long ones, and that is the prover's
    # arithmetic rather than caution: the budget is 50,000 expansions PER HOP and
    # a greedy frontier dives into whatever hole lies between it and the goal, so
    # a hop spanning a whole leg is a hop that spends its budget learning the
    # shape of the room.
    #
    # There is exactly one `switch_a` and one `switch_b`, so both are waypoints
    # the route NAMES -- which is not a convenience: the foundation measured the
    # same crossing at 13 expansions named and 19,227 unnamed, because a named
    # lever cuts the hop at the tile where the world changes instead of asking
    # one search to find a gate, a lever and the far side of the gate at once.
    _wet_mark(k, "wade", 12, LOW_STAND)
    _wet_mark(k, "sump_e", 21, LOW_STAND)
    _wet_mark(k, "pipe_in", SEAM_COL, LOW_STAND)     # still water, past x=400
    _wet_mark(k, "intake", 29, LOW_STAND)            # inside the push
    _wet_mark(k, "flume_out", WELL_X0, LOW_STAND)    # the well's bed
    k.mark("step", STEP[0], STEP[1] - 1)             # on the step, submerged
    k.mark("beach", BEACH[0], BEACH[1] - 1)          # flush with the surface
    # ONE TILE INLAND FROM THE LIP, and this is the most useful measurement in
    # the file.  With the mark on the lip itself (37,24) the water jump PROVED in
    # 5,066 expansions and the next hop -- a two-tile walk east -- cost 43,818
    # against a budget of 50,000.  The reason is `ProverSearch._reached`: it
    # accepts any state whose body rect OVERLAPS the target tile, and the
    # cheapest way to overlap the tile above the lip is to poke her head into it
    # while she is still in the water at the corner.  So the hop "arrived" with
    # her submerged, and the next hop had to make the whole jump again.
    #
    # At col 38 that is impossible by arithmetic: her hitbox is 10 px wide, so
    # overlapping the rect (608,384)-(624,400) needs her left edge at x >= 598,
    # and the water ends at x = 592.  Any state that reaches this mark is over
    # the ledge's own cap and lands on it.  The walk east then costs 12.
    k.mark("bank", LEDGE_X0 + 1, LEDGE_STAND)
    _air_mark(k, "flue_1", FLUE_X0 + 1, 20)
    _air_mark(k, "flue_2", FLUE_X0 + 1, SEAM_ROW)    # across y=240
    _air_mark(k, "flue_3", FLUE_X0 + 1, 10)
    k.mark("fault_e", FAULT_X1, FAULT_STAND)
    k.mark("fault_w", FAULT_X0, FAULT_STAND)
    k.mark("comb_e", COMB_X1, GAL_STAND)
    k.mark("comb_w", COMB_X0, GAL_STAND)
    k.mark("flat_w", 23, GAL_STAND)
    k.mark("door", GAL_X0, GAL_STAND)
    k.mark("stair_foot", STAIR_X1 - 1, GAL_STAND)
    k.mark("stair_1", S1_X0 + 1, S1_CAP - 1)
    k.mark("stair_2", S2_X0 + 1, S2_CAP - 1)

    g.route("spawn", "wade", form="human")           # off the apron, into water
    g.route("wade", "sump_e", form="human")
    g.route("sump_e", "pipe_in", form="human")       # x=400, still water
    g.route("pipe_in", "intake", form="human")       # into the 68 px/s push
    g.route("intake", "flume_out", form="human")     # carried east, one-way
    g.route("flume_out", "step", form="human")
    g.route("step", "beach", form="human")           # one tile of water jump
    g.route("beach", "bank", form="human")           # out of the water
    g.route("bank", "switch_a", form="human")        # A1 sinks, the teeth grow
    g.route("switch_a", "pad_bird", form="human")
    g.route("pad_bird", "flue_1", form="bird")       # into the column
    g.route("flue_1", "flue_2", form="bird")
    g.route("flue_2", "flue_3", form="bird")         # y=240, flown
    g.route("flue_3", "pad_human", form="bird")      # bob at the lip, steer west
    g.route("pad_human", "fault_e", form="human")    # off the landing, 2 rows
    g.route("fault_e", "fault_w", form="human")      # over the shards
    g.route("fault_w", "comb_e", form="human")       # out of the trench, 2 rows
    g.route("comb_e", "comb_w", form="human")        # under the teeth
    g.route("comb_w", "flat_w", form="human")        # x=400, walked, flat
    g.route("flat_w", "switch_b", form="human")      # B1 and B2 open together
    g.route("switch_b", "door", form="human")
    g.route("door", "stair_foot", form="human")      # through B1
    g.route("stair_foot", "stair_1", form="human")
    g.route("stair_1", "stair_2", form="human")
    g.route("stair_2", "exit", form="human")         # through B2, already open
    return g, k


AMBIENCE = {
    "_note": (
        "THE LAST ASCENT. The level is lit in two halves and the gap between "
        "them is the level's World 4 leg: cols 23-38 -- the flat, the comb and "
        "the fault -- carry NO authored pool at all, and everything that glows "
        "in there is a tile. That is not a mood, it is the only way this world "
        "can say 'dark stretch': `darkness` is one value for a whole level, "
        "World 5 does not use the key (nest_1's grammar), and a gradient does "
        "not exist. EMBER is the room, as everywhere in the nest. GOLD is "
        "reserved for what a throw moves or what you act on -- the two levers "
        "and the three doors they move -- so a player can read the machine off "
        "the light, and the two gold pools in the unlit half's neighbours (the "
        "flue's mouth at the landing, lever B in the hall) are the two things "
        "the dark stretch is navigated BETWEEN. The emissive pair is the "
        "level's own light and both are SOLID, because "
        "AmbienceLayer._collect_emissive scans the fg: 281 obsidian_hot is the "
        "heat `_hot()` bands around every nest_vein -- including the four in "
        "the fault, which is what marks its take-offs when nothing else does -- "
        "and 287 nest_shard is the shard bed, which glows for the reason "
        "deeps_1's spore does. 289 nest_vein is NOT in here: it is a background "
        "tile by its own art and emits nothing from back there, which is the "
        "point."),
    "world": "obsidian",
    "air": {"ramp": "ember", "step": 1, "alpha": 0.28},
    "bg_tint": {"ramp": "ember", "step": 2, "mix": 0.66, "scale": 0.50},
    "fg_tint": {"ramp": "ember", "step": 5, "mix": 0.16, "scale": 0.93},
    "vignette": 0.36,
    "lights": [
        # the two levers
        {"x": 40, "y": 24, "radius": 64, "ramp": "gold", "step": 5,
         "intensity": 0.48, "flicker": 0.18},
        {"x": 21, "y": 5, "radius": 64, "ramp": "gold", "step": 5,
         "intensity": 0.48, "flicker": 0.18},
        # the three doors they move
        {"x": 43, "y": 24, "radius": 56, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 13, "y": 7, "radius": 60, "ramp": "gold", "step": 4,
         "intensity": 0.34},
        {"x": 4, "y": 3, "radius": 60, "ramp": "gold", "step": 6,
         "intensity": 0.50, "flicker": 0.10},
        # ember: the rooms the player has to read. The sluice, the well, the
        # ledge, the flue's mouth, the hall, and the last stair twice -- the
        # quiet room is the brightest thing in the level, which is the whole
        # point of putting it after sixteen unlit columns.
        {"x": 5, "y": 26, "radius": 76, "ramp": "ember", "step": 5,
         "intensity": 0.34},
        {"x": 16, "y": 26, "radius": 72, "ramp": "ember", "step": 4,
         "intensity": 0.28},
        {"x": 30, "y": 27, "radius": 64, "ramp": "ember", "step": 3,
         "intensity": 0.22},
        {"x": 35, "y": 25, "radius": 72, "ramp": "ember", "step": 5,
         "intensity": 0.30},
        {"x": 41, "y": 8, "radius": 76, "ramp": "ember", "step": 5,
         "intensity": 0.32},
        {"x": 18, "y": 6, "radius": 72, "ramp": "ember", "step": 4,
         "intensity": 0.26},
        {"x": 9, "y": 6, "radius": 80, "ramp": "ember", "step": 6,
         "intensity": 0.36},
        {"x": 3, "y": 3, "radius": 72, "ramp": "ember", "step": 6,
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
    ("flue_2", "flue_3"):
        "flown, straight up the middle of a three-column column of rising air. "
        "The 0.12 s flip freeze at y=240 leaves the bird in the same column "
        "with nothing to miss and -210 px/s under it, which is why the one "
        "vertical seam crossing in this level is inside the flue.",
}

## Entries `reconfig_check` is run from: every room a shut gate makes, both sides
## of the one-way sluice, and every pad.  Each is swept over all four
## configurations by reconfig_check itself.  Every one stands on ROCK or in water
## and never on a switch block -- an entry the flood cannot legally stand in
## reports an empty room instead of a trap.
##
## THE GOAL IS PER-ROOM, and this level needs that more than any other in the
## world: no ground flood can cross the flue.  `reachable_set` and
## tools/reachability.py both see seventeen rows of empty air where the updraft
## is, and a human cannot climb that.  So everything below the flue is asked for
## `pad_bird` -- "can you always get to the lift" -- and everything above it for
## the exit.  The end-to-end question is `_strand_graph` in (g), which does model
## the column.
##
## THE FLUE'S FOOT IS DELIBERATELY ABSENT, and it is the one omission.  The gate
## at (43,23-24) does make a room behind it, and every tile of that room is
## updraft: a body inside the column has a fall cap of -70 px/s as Kaya and -210
## as the bird, so it is lifted off the floor on the tick it arrives.  There is
## nothing in there to be trapped standing on, and the flood fill -- which has no
## model of that -- would report a strand the game cannot produce.
RECONFIG_ENTRIES = [
    ("the foot (spawn)", SPAWN, PAD_BIRD),
    ("the sump, west of the push", (12, LOW_STAND), PAD_BIRD),
    ("the sluice, inside the push", (29, LOW_STAND), PAD_BIRD),
    ("the well, past the one-way", (35, LOW_STAND), PAD_BIRD),
    ("the well's step", (STEP[0], STEP[1] - 1), PAD_BIRD),
    ("the well's beach", (BEACH[0], BEACH[1] - 1), PAD_BIRD),
    ("the ledge, at lever A", SWITCH_A, PAD_BIRD),
    ("the landing, off the flue", PAD_HUMAN, EXIT_TILE),
    ("the fault, in the trench", (FAULT_X0, FAULT_STAND), EXIT_TILE),
    ("the gallery, west of the comb", (24, GAL_STAND), EXIT_TILE),
    ("the hall, at lever B", SWITCH_B, EXIT_TILE),
    ("the last stair, behind a shut B1", (6, GAL_STAND), EXIT_TILE),
    ("the stair's top, behind a shut B2", (S3_X0 + 1, S3_CAP - 1), EXIT_TILE),
]

## data/forms/*.json hitbox h, for check (h): a body resting on its tile's floor
## spans [16 - h, 16] of that tile, and the trigger box is [6, 16].
HITBOX_H = {"human": 22, "bird": 9}
SWITCH_BOX_INSET, SWITCH_BOX_SIZE = (1, 6), (14, 10)

FORMS = ("human", "bird")


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
        elif e["type"] in ("pad_bird", "pad_human"):
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
    project's own validator uses -- with four things it has no concept of: the
    switch configuration, the rule that a lever is only thrown FROM ITS OWN TILE,
    hazards as obstacles, and THE COLUMN.

    THE COLUMN is the one this level could not be checked without.  `updraft` is
    a tile flag no flood fill in this project reads, so to every other checker
    the flue is seventeen rows of empty air -- which is generous in the one
    direction a stranding check must never be generous in, because it invents a
    way back DOWN that the game does not have.  So: entering any updraft tile,
    from any direction, as any form, is a single edge to the LANDING, and there
    is no edge out of the column that goes anywhere else.  That is what the game
    does -- a fall cap of -70 px/s (Kaya) or -210 (the bird) lifts a body to the
    lip, where it bobs and steers sideways onto the one standable tile at that
    row -- and it makes the flue one-way in the check as well as in the level.
    """

    def __init__(self, g, pads, levers):
        self.g = g
        self.pads = pads                      # (x, y) -> form
        self.levers = levers                  # (x, y) -> group
        self.draft = NEST_W5.char("updraft")
        self.probe = {(a, b): Probe(g, switches={1: a, 2: b})
                      for a in (True, False) for b in (True, False)}

    def _is_draft(self, x, y):
        return (0 <= x < self.g.w and 0 <= y < self.g.h
                and self.g.fg[y][x] == self.draft)

    def _ground(self, p, x, y, form):
        rise, gap = LIMITS[form]["rise"], LIMITS[form]["gap"]
        out, lifted = [(x - 1, y), (x + 1, y)], False
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
                if self._is_draft(nx, ny):
                    lifted = True             # the fall ends in the column
                    break
                if not p.clear(nx, ny):
                    break
                if p.standable(nx, ny):
                    out.append((nx, ny))
                    break
        keep = [(nx, ny) for (nx, ny) in out
                if 0 <= nx < self.g.w and 0 <= ny < self.g.h
                and not self._is_draft(nx, ny)
                and p.standable(nx, ny) and not p.hazard(nx, ny)
                and path_clear(p, x, y, nx, ny, rise)]
        if lifted or any(self._is_draft(x + dx, y)
                         for dx in (-1, 1) if not p.solid(x + dx, y)):
            keep.append(PAD_HUMAN)
        return keep

    def _fly(self, p, x, y):
        out = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < self.g.w and 0 <= ny < self.g.h):
                continue
            if self._is_draft(nx, ny):
                out.append(PAD_HUMAN)         # the column, and only upward
            elif p.clear(nx, ny) and not p.hazard(nx, ny):
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
        moves = self._fly(p, x, y) if form == "bird" else self._ground(p, x, y, form)
        return out + [(nx, ny, form, cfg) for (nx, ny) in moves]


def _strand_graph(g, start, goal):
    """(where x which form x which switches), flooded forward then backward.

    nest_1's `_escape` and nest_2's adaptation search (where x switches) as the
    human; nest_3 put the form in the key for its four wings.  This level has two
    forms and a one-way lift, so it keeps the form in the key and adds the lift to
    the edges -- see `_Nav`.

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
    # Computed here rather than in (g) because (e) needs it too: it is the only
    # model in this file that knows the flue is one-way.
    seen, dead = _strand_graph(g, SPAWN, EXIT_TILE)

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
    # IN BOTH RESOLUTIONS, because tests/test_level_validity.gd asks it in the
    # DEFAULT one -- group 1 ON, group 2 OFF -- and `Probe(g)` with no switches
    # resolves every switch block as passable.  The first draft of the comb had a
    # gem inside a pillar and this check, asked the generous way, said nothing.
    must = {"exit", "player_spawn", "switch_a", "switch_b", "gem", "heart",
            "pad_bird", "pad_human"}
    resolutions = [Probe(g, switches={1: True, 2: True}),
                   Probe(g, switches={1: False, 2: False})]
    for e in g.entities:
        if e["type"] not in must:
            continue
        x, y = e["x"], e["y"]
        for pr in resolutions:
            if not pr.clear(x, y, BODY_TILES):
                bad.append("%s at (%d,%d) has no two tiles of headroom once the "
                           "switch blocks are resolved (a switch tile is solid "
                           "in exactly one of the two, and the suite asks in the "
                           "default one)" % (e["type"], x, y))
                break
        if (p.solid(x, y + 1) or p.oneway(x, y + 1)) and (y + 1) % 15 == 0:
            bad.append("%s at (%d,%d) stands on cap row %d, a screen boundary: "
                       "its centre lands on the screen above and the floor is "
                       "never drawn" % (e["type"], x, y, y + 1))
    for kind, c in k.claims:
        if kind == "stand" and (c["y"] + 1) % 15 == 0:
            bad.append("%s: stand row %d sits on cap row %d, a screen boundary"
                       % (c["why"], c["y"], c["y"] + 1))

    # (c) NO ON-FOOT HOP CROSSES A SCREEN SEAM MID-JUMP.  A human hop whose ends
    # are on different screens has to be a flat walk along unbroken standable
    # floor; a bird hop across one has to be named in SEAM_EXEMPT with a reason.
    # The camera freezes the sim for the length of every flip, and a freeze in
    # mid-air is the feel defect neither prove.sh nor the tape replay can see.
    for hop in g.hops:
        a, b = where.get(hop["from"]), where.get(hop["to"])
        if a is None or b is None:
            bad.append("route hop '%s' -> '%s' names a waypoint this module "
                       "cannot locate" % (hop["from"], hop["to"]))
            continue
        if _screen(a["x"], a["y"]) == _screen(b["x"], b["y"]):
            continue
        key = (hop["from"], hop["to"])
        if hop["form"] == "bird":
            if key not in SEAM_EXEMPT:
                bad.append("route hop '%s' -> '%s' is flown across a screen "
                           "seam and is not named in SEAM_EXEMPT" % key)
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

    # (d) NO SWITCH BLOCK IS EVER A FLOOR -- nest_2's check, kept because it is
    # the strongest form of the rule a grid can carry.  tools/reachability.py
    # resolves a switch tile as never solid, so a route that stands on one is a
    # route it reports as missing in every configuration.  Every switch tile has
    # rock, or the rest of its own plug, directly over its head, checked with the
    # switches resolved BOTH ways -- "solid" is a property of a configuration and
    # "has rock above it" is not.  This is why the comb's pillars run floor to
    # roof instead of stopping under the teeth.
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

    # (e) THE THREE DOORS AND THE COMB DO WHAT THE DOCSTRING SAYS, re-derived
    # from the grid: each plug is solid in exactly the configurations its own
    # table row claims, the comb is a wall in exactly one resolution of group A,
    # and neither lever is decoration.
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
    comb_walk = [(x, GAL_STAND) for x in range(COMB_X0, COMB_X1 + 1)]
    for on, want_open in ((False, True), (True, False)):
        pr = Probe(g, switches={1: on, 2: False})
        walkable = all(pr.standable(x, y) for x, y in comb_walk)
        if walkable != want_open:
            bad.append("THE COMB with group A %s is %s, and the whole point of "
                       "it is that the lever at %s decides"
                       % ("ON" if on else "OFF",
                          "walkable" if walkable else "a wall", SWITCH_A))
    start_flood = k.reachable_set(SPAWN, form="human", switches=START_CFG)
    if (FLUE_X0, FLUE_BOT) in start_flood:
        bad.append("the flue's foot is reachable from the spawn with A1 shut: "
                   "switch_a is decoration")
    if SWITCH_A not in start_flood:
        bad.append("switch_a is not reachable from the spawn before any throw, "
                   "so the level cannot be started")
    after_a = k.reachable_set(PAD_HUMAN, form="human",
                              switches={1: False, 2: False})
    if EXIT_TILE in after_a:
        bad.append("the exit is reachable from the landing with B1 and B2 shut: "
                   "switch_b is decoration")
    if SWITCH_B not in after_a:
        bad.append("lever B is not reachable from the landing, so the level "
                   "cannot be finished")
    # ... and the window is a drain and not a door: three rows against a
    # measured rise of two, with nothing on the gallery side to stand on.
    if (WINDOW[0], WINDOW[1] + WINDOW[2] - 1) in after_a:
        bad.append("the window at %s is reachable from the gallery floor, so it "
                   "is a way round B1 and not a drain"
                   % ((WINDOW[0], WINDOW[1] + WINDOW[2] - 1),))
    # ... and NOTHING ABOVE THE FLUE IS EVER IN AN A-ON CONFIGURATION, which is
    # what makes the comb a statement rather than a puzzle the player can
    # re-pose, and what lets `_reconfig` admit the A-ON floods up there as
    # configurations no body can be in.  `reachable_set` cannot answer this --
    # it has no model of the column and cheerfully falls down it -- so the
    # question goes to the one model in this file that does.
    a_on_upstairs = [s for s in seen if s[1] < SEAM_ROW and s[3][0]]
    if a_on_upstairs:
        bad.append("%d state(s) above the flue have group A ON, e.g. (%d,%d) as "
                   "the %s: the column is supposed to be one-way and both the "
                   "comb and every A-ON admission in _reconfig depend on it"
                   % (len(a_on_upstairs), a_on_upstairs[0][0],
                      a_on_upstairs[0][1], a_on_upstairs[0][2]))

    # (f) NEITHER GROUP IS A LOCAL SWITCH.  World 5's scale mechanism is one
    # lever moving doors in rooms it cannot see (nest_2's finding), so every
    # group has at least one block more than six tiles from its own lever.
    lever_of = {1: SWITCH_A, 2: SWITCH_B}
    far = {1: 0, 2: 0}
    for x, y, ch in _switch_tiles(g):
        grp = int(flags[ch]["switch_group"])
        lx, ly = lever_of[grp]
        if abs(x - lx) + abs(y - ly) > 6:
            far[grp] += 1
    for grp, n in sorted(far.items()):
        if n == 0:
            bad.append("group %d has every one of its blocks within six tiles "
                       "of its lever at %s: it is a local switch and the "
                       "world's scale mechanism is gone" % (grp, lever_of[grp]))

    # (g) NO STATE THE PLAYER CAN REACH IS A DEAD END -- ADR 004, over
    # (where x which form x which switches).  See ADR 004 in the docstring, and
    # `_Nav` for the one edge this level could not be checked without.
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

    # (h) ONE LEVER PER GROUP -- nest_1's measured hard rule -- and a trigger box
    # both bodies cover.  SwitchTrigger.aabb() is Rect2(tile*16 + (1,6),
    # (14,10)); a body resting on the tile's floor spans [16-h, 16] of the tile,
    # and h comes from data/forms/*.json.
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
            box_bot = SWITCH_BOX_INSET[1] + SWITCH_BOX_SIZE[1]
            for form, hb in sorted(HITBOX_H.items()):
                if 16 - hb >= box_bot:
                    bad.append("%s at (%d,%d): a %s resting on the tile spans "
                               "%d..16 and the box ends at %d -- that form "
                               "cannot throw it by body"
                               % (t, sx, sy, form, 16 - hb, box_bot))

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

    # (j) Every vein is still a vein, still on the BACKGROUND, still in open air,
    # and still has the obsidian_hot band `_hot()` owes it -- a bg tile emits
    # nothing and 281 is what does.  The four in the fault are the ones that
    # matter: they are the only light in the unlit stretch.
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

    # (k) NOTHING ON THE ROUTE COSTS THE BIRD A FLAP.  `flap_cost` 12 against
    # `max_stamina` 100 is eight flaps and the prover cannot wait on a perch --
    # `ProverSearch._key()` does not hash stamina, so "same place, fuller tank"
    # is a state the frontier can never contain (THE LONG GLIDE's finding).  Here
    # the answer is structural rather than budgeted: every bird hop is inside the
    # column, where the push is -400 px/s and a flap buys nothing, so the run
    # length does not matter.  This check is that the claim stays true.
    for hop in g.hops:
        if hop["form"] != "bird":
            continue
        for end in ("from", "to"):
            wp = where.get(hop[end])
            if wp is None:
                continue
            x, y = wp["x"], wp["y"]
            inside = (FLUE_X0 <= x <= FLUE_X1 and FLUE_TOP <= y <= FLUE_BOT)
            at_end = (x, y) in (PAD_BIRD, PAD_HUMAN)
            if not (inside or at_end):
                bad.append("bird hop '%s' -> '%s' has an end at (%d,%d), which "
                           "is neither inside the column nor one of its two "
                           "pads: that is a flight the tank has to pay for and "
                           "the prover cannot refill a tank"
                           % (hop["from"], hop["to"], x, y))

    # (l) THE FALL RULE, machine-checked: no jump on the route has a hazard under
    # its landing except the fault's own bed, and no hop's landing is over a
    # bottomless drop.  This is the fairness bar in the docstring; (g) covers the
    # softlocks and this covers the deaths.
    for hop in g.hops:
        b = where.get(hop["to"])
        if b is None or hop["form"] == "bird":
            continue
        x, y = b["x"], b["y"]
        below = next((yy for yy in range(y + 1, g.h) if p.solid(x, yy)), None)
        if below is None:
            bad.append("route waypoint '%s' at (%d,%d) is over a bottomless "
                       "drop" % (hop["to"], x, y))
        elif p.hazard(x, y + 1):
            bad.append("route waypoint '%s' at (%d,%d) stands on a hazard"
                       % (hop["to"], x, y))

    if bad:
        raise world_kit.WorldKitError(
            "%s: %d self-check failure(s):\n  %s"
            % (LEVEL_ID, len(bad), "\n  ".join(bad)))
    if verbose:
        print("  self-checks  (a) pockets (b) headroom + seam rows (c) seam hops")
        print("               (d) no switch block is ever a floor, in either "
              "resolution")
        print("               (e) three doors + the comb, both levers "
              "load-bearing, the window is a drain")
        print("               (f) both groups reach past their own lever")
        print("               (g) ADR 004: %d (tile, form, config) states "
              "reachable, 0 dead ends" % len(seen))
        print("               (h) one lever per group, box covered by both "
              "bodies")
        print("               (i) %d breakable(s), none on the route  (j) %d "
              "veins lit" % (len(breakables), len(VEINS)))
        print("               (k) every bird hop is inside the column  (l) the "
              "fall rule")
    return len(seen)


def _reconfig(k, entry, goal, label, states, verbose=True):
    """`reconfig_check`, with the two answers it does not know about admitted.

    Its second question is "in every configuration reachable from here, is at
    least one SWITCH reachable".  That is the right question almost everywhere and
    it is the wrong one twice in this level, for two reasons that are the level
    rather than excuses for it:

    1. IT FLOODS CONFIGURATIONS THE PLAYER CANNOT BE IN.  Group A can only return
       to ON by touching `switch_a`, which is at the bottom of a one-way flue, so
       nothing above the flue is ever in an A-ON configuration -- and with A ON
       the comb is a wall, which cuts the gallery off from lever B.
       `_strand_graph` -- which carries the form, models the column and only
       flips a lever from its own tile -- says so, and this helper asks it rather
       than asserting it.

    2. A ROOM WHOSE ONLY WAY OUT IS THE EXIT IS NOT A TRAP.  The top of the last
       stair is behind B2, and past B2 the only thing left in the game is the
       door.

    Anything else is re-raised untouched.  Adapted from nest_2's helper and
    nest_3's, which made the same kind of admission for their own reasons.
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
    g, k = nest_4()
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
