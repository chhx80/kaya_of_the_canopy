#!/usr/bin/env python3
"""ruins_4 -- THE CISTERN.  World 2's last level, the run-up to The Tide Maw.

Self-contained: running this file under the project python writes
levels/ruins_4.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `ruins_4()` returning `(Grid, Kit)`,
which is the tuple tools/build_levels.py's `build()` expects -- that writer
audits the kit before it writes anything.

    source tools/env.sh && "$PYVENV" tools/worlds/ruins_4.py
    tools/prove.sh ruins_4

THE SHAPE OF THE LEVEL
----------------------
Three stages of a drowned cistern, climbed bottom to top.  Every stage is
entered as one form and left as the other; current speed decides which way
each lane can be swum, and the two switch gates decide which door is shut.

  STAGE 1  THE INTAKE (rows 21-28).  A dry gallery, a sump, and the intake:
           three tiles of `water_current_left` at 68 px/s.  That number is
           the level's whole vocabulary -- Kaya's top speed in water is
           max_run 108 * water_move_scale 0.62 = 66.96 px/s, so she cannot
           gain a pixel on it, and the fish swims 92 and makes 24 px/s.  Past
           the lip the flume is `water_current_right_fast` at 120 px/s, which
           neither form can beat: stage 1 is a one-way door.  Nothing the rest
           of the level needs is on the gallery side of it.

  STAGE 2  THE CISTERN (rows 12-18).  A dry gallery over a drowned half of
           plain water; the gallery's floor is row 14 and is also the drowned
           half's roof, so the swim beneath it surfaces only at its two ends.
           Everything walked in this stage stands on row 13, which is a fact
           about the screen seam and not about the fiction -- see WHERE THE
           WALKED FLOOR OF THIS STAGE SITS, below.  The west end is the bay
           with the stepping stone, the only place the two halves trade forms.
           Throwing switch_a on the west bank opens the `switch_gate` that
           seals the stair into stage 3.

  STAGE 3  THE HEADER TANK (rows 1-10).  The same one-way in miniature: three
           tiles of `water_current_right` to push west through, then a
           `..._left_fast` flume into a tank whose only shore is behind a
           second `switch_gate`.  Its switch is on the tank's bed, so the fish
           that was thrown in there can always open it -- and the shore is two
           tiles of rock with open water off its east edge, so Kaya can always
           dive back to the lever: whether she threw the sluice shut herself or
           beached to find it shut, walking east off the shelf puts her in the
           tank with it.  That clause is a repair and not a flourish; the first
           draft's sluice was five tiles tall and sealed the shore off from its
           own tank, which is the trap this level shipped with.

WHAT THE SWITCH BLOCKS DO, AND WHY THEY ARE DOORS RATHER THAN FLOORS
--------------------------------------------------------------------
The first draft of this level made the weirs *decks*: throw the switch and a
walkway rises a tile out of the water, which is what "switch blocks set the
water level" reads like.  It proved, and `tools/reachability.py` rejected it,
and reachability was right to.  That filter resolves a switch tile as
**never solid** -- `Level.solid()` returns False for anything with a
`switch_group` -- because it cannot know which half of a group is up.  So a
switch block can be a wall the checker generously assumes is open, and it can
never be a floor: a route that has to stand on one is a route the filter
reports as missing, every time, in every configuration.

That is not a bug in the filter, it is the direction it is allowed to be
wrong in (ADR 005: it may only ever under-report).  So every switch block
here is something that *blocks* while it is solid -- a grating, a gate --
and never something you stand on.  What the flip changes is which lane is
open and which door is shut, which is the same sentence as "where you can
swim and where you can stand" with the floors left to the rock.

ADR 004 -- NO TRANSFORM STRANDS YOU
-----------------------------------
The fish beaches itself the way defect 4 said it must: `surface_hop` -210
against gravity 900 clears 24.5 px, so one tile and never two.  Every body of
water in the level has a one-tile bank out of it, and the bank's rock is always
flush with the `water_top` row so the hop out is one tile and not two -- the
gallery lip (9,24), the stage-2 west bank (8,13) and bay stone (10,13), the
stage-3 tank shelf (3,6), the east tank's lip (24,6).

That is the fish's half of ADR 004.  Kaya's half is harder and is the thing
this level got wrong twice, because a flush bank the fish hops out of is a bank
a human CANNOT climb: her water jump measures 0.7*(feet - surface - 10) + 27 px
of rise, and from the bottom of a full-depth well that lands her four pixels
under the lip.  So every pocket she can fall into has a step in it, one tile of
rock or slab whose top is two tiles under the water's surface, and it is that
step and not the bank that she jumps from:

    cols 10-11 row 27      the sump's step
    cols  9,11 row  16     the stage-2 bay's two `oneway` slabs
    col  23    rows  9-10  the stage-3 east tank's step
    col   4    rows  9-10  the stage-3 west tank's step

Neither switch can be left in a state that seals you away from a switch;
`check()` below runs `reconfig_check` over all four configurations from nine
entries -- one for each side of each one-way, plus the two rooms a shut gate
makes, which is where the trap was hiding.

THE PALETTE
-----------
world_kit's `Palette.char()` resolves a tile NAME through the flat,
jungle-derived `legend` key of data/level_legend.json, so RUINS's own names
(ruin_stone, kelp, ...) have no character there and fall through to
UNDERSTUDY.  Two of those understudies land on the wrong ruins role: `solid`
would emit `s` (ruin_grate, the *second* solid) and `bg` would emit `r`
(ruin_algae, a background accent).  ADR 002's amendment says a character means
whatever the level's world says it means, so this palette is declared in terms
of the jungle tile whose character IS the ruins role character -- `grass_top`
for `#`, `bg_leaves` for `L`.  The result is zero substitutions
(`Palette.missing()` is empty and `audit(strict_verbs=True)` is clean) and the
level serialises `"tileset": "ruins"`, so the game paints ruin_stone and kelp.
The currents and the switch blocks are `shared` characters and are the real
tiles either way -- this level loses no verb to an understudy.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                      # noqa: E402
from world_kit import Kit, Palette                      # noqa: E402

LEVEL_ID = "ruins_4"
LEVEL_NAME = "THE CISTERN"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the ruins role
## character.  See the module docstring: this is a character map, not an art
## claim, and the art comes from `"tileset": "ruins"` at load time.
RUINS_W2 = Palette("sunken_ruins", {
    "bg": "bg_leaves",            # 'L' -> ruin_wall
    "solid": "grass_top",         # '#' -> ruin_stone
    "solid_alt": "stone_mossy",   # 'S' -> ruin_stone_algae
    "packed": "dirt",             # 'd' -> ruin_silt
    "block": "stone",             # 's' -> ruin_grate
    "oneway": "wood_platform",    # '=' -> ruin_slab
    "ladder": "vine",             # '|' -> kelp
    "hazard": "spikes",           # '^' -> ruin_urchin
    "water": "water",             # 'w'  shared
    "water_top": "water_top",     # '~'  shared
    "decor": "tree_trunk",        # 'T' -> ruin_column
    "void": "bg_dark",            # 'X' -> ruin_deep
    "breakable": "crate",         # 'c' -> ruin_cracked
    "shoulder": "cracked_stone",  # 'k'  shared
    "rubble": "rubble",           # 'o'  shared
    "cur_right": "water_current_right",
    "cur_left": "water_current_left",
    "cur_up": "water_current_up",
    "cur_down": "water_current_down",
    "cur_right_fast": "water_current_right_fast",
    "cur_left_fast": "water_current_left_fast",
    "switch_a_on": "switch_block_a_on",
    "switch_a_off": "switch_block_a_off",
    "switch_b_on": "switch_block_b_on",
    "switch_b_off": "switch_block_b_off",
})


def ruins_4():
    g = Grid(W, H, tileset="ruins")
    k = Kit(g, RUINS_W2, form="human")

    # ------------------------------------------------------------- the rock
    # Carved rather than built: a solid block with rooms cut out of it keeps
    # the prover's frontier inside the rooms instead of wandering open water.
    k.fill_bg("bg")
    k.fill_solid("packed")
    k.shell(1, "solid")
    k.rect(48, 0, 1, H, "solid")          # second east wall: the level is cols 1..47

    # ==================================================== STAGE 1 -- THE INTAKE
    k.clear_rect(1, 21, 9, 4)             # the gallery's air, rows 21..24
    k.floor(1, 25, 9)                     # cap row 25, stand row 24

    k.clear_rect(10, 21, 14, 4)           # the sump's air
    k.rect(10, 25, 14, 1, "water_top")
    k.rect(10, 26, 14, 2, "water")
    k.rect(10, 28, 14, 1, "solid")        # the bed
    k.rect(10, 27, 2, 1, "solid")         # the step Kaya jumps off to leave the sump
    k.rect(13, 27, 2, 2, "solid")         # a stump off the bed: swim over it
    k.rect(20, 25, 2, 1, "solid")         # a pier off the surface: swim under it

    # THE SUMP STONES -- the level's only `switch_lattice`, and the one thing
    # in it that is optional. A row of switch blocks suspended in the sump's
    # air: with group 1 ON the odd columns are solid and you hop east along
    # them, and throwing switch_a two stages later shifts every
    # stone one tile. They lead nowhere -- cols 24-36 are thirteen tiles of
    # rock -- so nothing depends on them, which is the point:
    #
    #   * `tools/reachability.py` resolves a switch tile as never solid, so it
    #     cannot stand on one. Anything it must reach may not be up here.
    #   * `tests/test_level_validity.gd` refuses a standable tile with one tile
    #     of headroom, and a rows-lattice is ALWAYS one-tile courses while a
    #     columns- or checker-lattice is a wall. Suspended in open air with
    #     nothing underneath is the one arrangement a lattice can take that the
    #     suite accepts: the solid stones have two clear tiles over them and the
    #     open ones have no floor under them, so the pocket check skips them.
    #     That is also why the stump and the pier moved out from under this
    #     row: standing on either with a stone directly overhead is a one-tile
    #     pocket, and the check found it.
    #
    # So the level's form gating is done with current speed, which the flood
    # fills are blind to and therefore generous about, and its doors are
    # `switch_gate` plugs, which they resolve as open. The lattice is what the
    # player sees the mechanic on before it matters.
    k.switch_lattice(11, 23, 9, 1, group="a", pattern="columns", phase=1)

    # The intake and the flume run under thirteen tiles of rock, so the sump
    # and the east bay share no air and no surface. The only way through is
    # the tube, and the tube only runs one way.
    # The mouth is three tiles of still water, deliberately: the vertical
    # screen seam is x=400 px, between cols 24 and 25, and `CameraController`
    # picks its screen from the body's centre. A body inching east at 24 px/s
    # across that line flips the camera back and forth every time it wobbles,
    # which is a feel defect neither prove.sh nor the tape replay can see. So
    # the seam is crossed in still water and the push starts at col 27.
    k.rect(24, 26, 3, 2, "water")
    k.rect(27, 26, 3, 2, "cur_left")          # 68 px/s: the fish makes 24, Kaya makes none
    k.rect(30, 26, 7, 2, "cur_right_fast")    # 120 px/s: nothing swims back

    k.clear_rect(37, 21, 11, 4)           # the east bay's air
    k.rect(37, 25, 11, 1, "water_top")
    k.rect(37, 26, 11, 2, "water")
    k.rect(37, 28, 11, 1, "solid")

    # =================================================== STAGE 2 -- THE CISTERN
    k.rect(1, 11, 47, 1, "solid")         # the cistern's roof
    k.rect(1, 19, 47, 1, "solid")         # its floor, and stage 1's ceiling
    k.clear_rect(30, 11, 11, 1)           # the shaft up into stage 3

    # WHERE THE WALKED FLOOR OF THIS STAGE SITS, AND WHY IT IS ROW 14
    # The horizontal screen seam is y=240, the line between tile rows 14 and
    # 15, and `CameraController` picks the screen from the body's CENTRE. A
    # body 22 px tall standing on a floor capped at row 15 has its feet at
    # y=240 and its centre at y=229, so it gets the UPPER screen -- which ends
    # at y=240 and therefore never draws the floor it is standing on: the first draft's gallery was walked from col 12 to col 34 along
    # the frame's last pixel, over a floor row nobody ever saw, with an
    # enemy_walker patrolling the same invisible ledge. Capped at row 14 the
    # floor is inside the upper screen with her, so everything standable in
    # this stage stands on row 13 over rock on row 14 -- bank, stone, gallery
    # and alcove alike. Nothing here changes screen, and the price is that the
    # gallery is two rows of air rather than three: row 11 is the cistern's
    # roof and cannot move, because it is stage 3's tank beds.
    k.clear_rect(1, 12, 8, 2)             # the west bank's air, rows 12..13
    k.floor(1, 14, 8, depth=1)            # cap row 14, stand 13; one slab thick,
                                          # because the silt trap is the chamber
                                          # under it
    # The west bay: two one-column wells with a stone between them. Four things
    # have to be true of it at once.
    #
    #  * Both wells are open water all the way to the surface at row 14 with
    #    air above -- a body cannot climb a wall diagonally, and a column of
    #    water with rock directly over it is a column you enter and cannot
    #    leave upwards.
    #  * Kaya has to be able to get out of a well she falls into, and a human
    #    cannot climb out of deep water onto a flush shore: this project has
    #    measured that at 0.0 px. So each well has a step in it whose top is
    #    row 16, two tiles under the surface. Her water jump is jump_vel
    #    -260 * water_jump_scale 0.78 against gravity 760 * water_gravity_scale
    #    0.3, and it keeps the water's gravity only while her upper body is
    #    still wet, which makes the rise 0.7*(feet - surface - 10) + 27 px.
    #    From a step (feet y=256, surface y=224) that is 43 px and her feet
    #    reach y=213, clearing the row-14 tops by 10 px. From the cistern's own
    #    floor at y=304 the same jump ends at y=228 -- FOUR PIXELS SHORT. The
    #    steps are the difference between a bay and a drowning.
    #  * The stone splits the crossing. Bank to stone is two tiles and stone to
    #    gallery is two, where bank to gallery in one leap is three -- and a
    #    three-tile gap over WATER is what cost hop 15 fifty thousand
    #    expansions before the stone was here. The prover dives into the hole
    #    (ADR 005's addendum) and a hole you can swim around in is a far bigger
    #    hole than a pit that kills you.
    #  * The steps are `oneway` slabs and the stone stops at row 15, so all of
    #    this water is ONE body: the silt trap, both wells, under the stone and
    #    the whole drowned half join up along rows 17-18. That is what keeps
    #    the fish's swim west a swim -- it never has to hop the stone, which is
    #    a hop the prover spent its entire 50k budget failing to find -- and a
    #    one-way is the only floor a body can arrive on from ABOVE and still
    #    rise through from BELOW, so neither form can be shut under or over it.
    k.clear_rect(9, 12, 3, 2)             # the bay's head, cols 9..11
    k.rect(9, 14, 3, 1, "water_top")
    k.rect(9, 15, 3, 4, "water")          # rows 15..18
    k.rect(10, 14, 1, 2, "solid")         # the stepping stone: rows 14-15, top at
                                          # row 14, and open water underneath it
    k.clear_rect(10, 13, 1, 1)            # the air above it, where she stands
    k.rect(9, 16, 1, 1, "oneway")         # the west well's step
    k.rect(11, 16, 1, 1, "oneway")        # the east well's step

    # The silt trap: a flooded side chamber cut under the bank's slab, off the
    # route, with a heart in it. It opens into the west well, so the swim west
    # passes its mouth and the way back out is the well's own step. Open water,
    # not a screened cell -- see the note on THE SUMP STONES for why a
    # `switch_lattice` across a passage is not something this project's own
    # checks will accept.
    k.clear_rect(2, 15, 7, 4)
    k.rect(2, 15, 7, 4, "water")

    # The dry gallery runs from the west bay to the gate and no further: the
    # rock east of the stair alcove is what stops the stair being reached from
    # the east bay instead, which would have made switch_a decoration. The
    # gallery's floor is also the drowned half's roof, so the swim beneath it
    # surfaces only at its two ends.
    k.clear_rect(12, 12, 23, 2)           # gallery + alcove, cols 12..34, rows 12..13
    k.rect(12, 14, 32, 1, "solid")        # the floor, cols 12..43
    k.rect(12, 15, 32, 4, "water")        # the drowned half, rows 15..18

    k.clear_rect(44, 12, 4, 2)            # the east bay's head, where the riser arrives
    k.rect(44, 14, 4, 1, "water_top")
    k.rect(44, 15, 4, 4, "water")

    # The gate on the stair. `switch_block_a_on` is solid exactly while group 1
    # is ON, which is how the level starts, so the alcove at cols 31-34 -- the
    # foot of the stair -- is shut until the west bank's lever is thrown. Two
    # tiles, which is the whole height of the gallery's air: row 11 is rock
    # from col 1 to col 29, so there is no lip to jump over it by. It is the
    # ONLY door into the alcove: cols 35-43 at rows 12-13 are rock and the bay
    # below has no bank to climb out onto.
    k.switch_gate(30, 13, 2, group="a", solid_when="on")

    # The riser: a column of rising water out of stage 1's east bay, punched
    # through both divider rows. Drawn after stage 2's floor, which would
    # otherwise cap it.
    k.rect(45, 19, 2, 6, "cur_up")        # rows 19..24

    # ============================================== STAGE 3 -- THE HEADER TANK
    k.clear_rect(2, 1, 39, 6)             # rows 1..6 over the tanks and the landing
    k.clear_rect(30, 7, 11, 4)            # the shaft, rows 7..10 -- carved BEFORE
                                          # the ledges, because a ledge written
                                          # first and carved over afterwards is
                                          # the draw-order bug audit() exists for
    k.rect(41, 5, 1, 7, "solid")          # the shaft's east wall
    k.rect(29, 8, 1, 3, "solid")          # the east tank's east wall
    k.rect(26, 8, 3, 3, "packed")         # rock under the landing's west end

    k.rect(4, 7, 10, 1, "water_top")      # the west tank; cols 2..3 stay rock,
    k.rect(4, 8, 10, 3, "water")          # which is the shelf the fish beaches on
    k.rect(4, 9, 1, 2, "solid")           # the shelf's own submerged step: the one
                                          # tile that makes the sealed tank
                                          # escapable, see the sluice note below
    # The east tank stops at col 23, two columns short of where it started.
    # The vertical screen seam is x=400, the line between cols 24 and 25, and
    # the first draft put the fish pad at (26,6) with the water it dives into at
    # col 25: she stood on one screen and jumped into another, which is a blind
    # dive by construction. Standing at (24,6) her centre is x=392, so the pad,
    # the lip and every tile of the tank she is aiming at are on the same
    # screen; the flip now happens while she walks the landing, on solid rock.
    k.rect(21, 7, 3, 1, "water_top")      # the east tank
    k.rect(21, 8, 3, 3, "water")
    k.rect(23, 9, 1, 2, "solid")          # its submerged step

    # The upper tube, under seven tiles of rock for the same reason as the
    # first one: three tiles of 68 px/s to push west through, then a 120 px/s
    # flume into the west tank.
    k.rect(18, 9, 3, 2, "cur_right")
    k.rect(14, 9, 4, 2, "cur_left_fast")

    # The stair down the shaft, all one-way, so Kaya walks underneath each
    # tread and jumps up through it.
    k.ledge(31, 12, 4)                    # stand 11
    k.ledge(36, 11, 4)                    # stand 10
    k.ledge(31, 9, 4)                     # stand 8
    k.ledge(24, 7, 16)                    # stand 6 -- the stage-3 floor and the
                                          # east tank's lip

    # The exit stair, and the sluice gate the tank's own lever opens.
    # `switch_block_b_off` is solid exactly while group 2 is OFF, which is how
    # the level starts.
    #
    # THREE tiles tall, rows 2-4, and the height is the whole fix for the trap
    # this level shipped with. Five tiles (rows 2-6) sealed the shelf: a fish
    # arriving along row 9 can beach at (3,6) without ever crossing switch_b's
    # trigger box, which is ten pixels of row 10, and the human it turns into
    # was then standing on two tiles of rock with the sluice shut, her jump
    # measured 31 px short of the stair and nothing to do but be eaten by the
    # swimmer. Rows
    # 5-6 of col 4 are open now, so walking east off the shelf drops her back
    # into the tank, where the lever on the bed is -- the shelf always drains
    # to the switch, in every configuration.
    #
    # It still gates. Above the plug is row 1 alone, 16 px against a 22 px
    # body. Below it she can only walk out into open water: (5,6) is air over
    # the tank and (4,6) has no floor. And the jump that reaches the first
    # tread has to cross col 4 at rows 3-4 -- 108 px/s carries her 16 px east
    # in 0.15 s, by which time she has risen 26 px and her head is in row 4 --
    # so with group 2 OFF that jump is a wall, and only the lever opens it.
    k.switch_gate(4, 4, 3, group="b", solid_when="off")
    k.ledge(5, 5, 4)                      # stand 4
    k.ledge(9, 3, 4)                      # stand 2

    # -------------------------------------------------------------- dressing
    for x in (5, 17, 26, 33):
        k.rect(x, 12, 1, 2, "decor", "bg")
    for x in (7, 20, 39):
        k.rect(x, 21, 1, 4, "decor", "bg")
    k.rect(2, 1, 12, 6, "void", "bg")
    k.rect(27, 26, 10, 2, "void", "bg")
    k.rect(11, 15, 33, 4, "void", "bg")

    # -------------------------------------------------------------- entities
    g.ent("player_spawn", 2, 24)
    g.ent("pad_fish", 9, 24)
    g.ent("pad_human", 8, 13)
    g.ent("switch_a", 3, 13)
    g.ent("pad_fish", 24, 6)
    g.ent("switch_b", 8, 10)
    g.ent("pad_human", 3, 6)
    g.ent("exit", 11, 2)

    g.ent("enemy_swimmer", 16, 26)
    g.ent("enemy_swimmer", 40, 26)
    g.ent("enemy_swimmer", 12, 9)
    g.ent("enemy_walker", 38, 6)
    g.ent("enemy_walker", 22, 13)
    for (x, y) in [(12, 26), (18, 26), (39, 26), (46, 16), (33, 17), (17, 17),
                   (4, 13), (33, 12), (37, 10), (33, 8), (22, 8), (12, 8),
                   (7, 4), (28, 6)]:
        g.ent("gem", x, y)
    g.ent("heart", 34, 6)
    g.ent("heart", 4, 17)

    # --------------------------------------------------- the route (ADR 005)
    # Two pads of each kind means neither `pad_fish` nor `pad_human` names a
    # waypoint on its own -- gen_levels.Grid._waypoints refuses a type there
    # are several of -- so each pad carries a mark on its own tile. Standing
    # on that tile is what fires the pad (TransformPad's box is the lower half
    # of it), so the hop that arrives is the hop that transforms, and the next
    # hop's declared form is checked by prove.gd against what actually
    # happened rather than against what was intended.
    k.mark("sump_lip", 9, 24)                       # pad_fish
    k.mark("sump_bar", 17, 26, form="fish")
    k.mark("sump_pier", 23, 27, form="fish")
    k.mark("tube_mouth", 25, 27, form="fish")
    k.mark("intake", 29, 27, form="fish")
    k.mark("flume_out", 38, 26, form="fish")
    k.mark("riser_foot", 45, 25, form="fish")
    k.mark("cistern_e", 45, 17, form="fish")
    # Named for what they are: waypoints in the drowned half. They were called
    # weir_e/m/w after a weir that was designed and never built -- the switch
    # blocks that would have been it are the sump lattice and the two gates --
    # and a route mark that lies about the geometry is a route mark that sends
    # the next author looking for a tile that was never there.
    k.mark("drowned_e", 40, 17, form="fish")
    k.mark("drowned_m", 27, 17, form="fish")
    k.mark("drowned_w", 14, 17, form="fish")
    # One row under the surface, not on it. A mark on the surface tile beside
    # the bank is a mark the greedy search can reach by hopping out onto the
    # pad and falling back in -- which fires the pad, and the hop then ends
    # as the human the next hop is not expecting.
    k.mark("bank_foot", 9, 15, form="fish")
    k.mark("bank_top", 8, 13)                       # pad_human
    k.mark("bay_stone", 10, 13)
    k.mark("gallery_e", 28, 13)
    k.mark("stair_1", 32, 11)
    k.mark("stair_2", 37, 10)
    k.mark("stair_3", 32, 8)
    k.mark("tank_lip", 24, 6)                       # pad_fish
    k.mark("tank_bed", 22, 10, form="fish")
    k.mark("tube_in", 21, 10, form="fish")
    k.mark("tube_out", 13, 10, form="fish")
    k.mark("tank_shelf", 5, 7, form="fish")
    k.mark("tank_top", 3, 6)                        # pad_human

    g.route("spawn", "sump_lip", form="human")
    g.route("sump_lip", "sump_bar", form="fish")
    g.route("sump_bar", "sump_pier", form="fish")
    g.route("sump_pier", "tube_mouth", form="fish")
    g.route("tube_mouth", "intake", form="fish")
    g.route("intake", "flume_out", form="fish")
    g.route("flume_out", "riser_foot", form="fish")
    g.route("riser_foot", "cistern_e", form="fish")
    g.route("cistern_e", "drowned_e", form="fish")
    g.route("drowned_e", "drowned_m", form="fish")
    g.route("drowned_m", "drowned_w", form="fish")
    g.route("drowned_w", "bank_foot", form="fish")
    g.route("bank_foot", "bank_top", form="fish")
    g.route("bank_top", "switch_a", form="human")
    g.route("switch_a", "bay_stone", form="human")
    g.route("bay_stone", "gallery_e", form="human")
    g.route("gallery_e", "stair_1", form="human")
    g.route("stair_1", "stair_2", form="human")
    g.route("stair_2", "stair_3", form="human")
    g.route("stair_3", "tank_lip", form="human")
    g.route("tank_lip", "tank_bed", form="fish")
    g.route("tank_bed", "tube_in", form="fish")
    g.route("tube_in", "tube_out", form="fish")
    g.route("tube_out", "switch_b", form="fish")
    g.route("switch_b", "tank_shelf", form="fish")
    g.route("tank_shelf", "tank_top", form="fish")
    g.route("tank_top", "exit", form="human")

    return g, k


## Entries reconfig_check is run from: the spawn, plus both sides of every
## one-way current in the level. Each is swept over all four switch
## configurations by reconfig_check itself.
##
## All of them sit on rock rather than on a switch block, deliberately: every
## switch block here is a door, so none of them is ever a tile you stand on,
## and an entry that the flood cannot stand on reports an empty room instead
## of a trap.
## The bay entry is one of the wells' steps rather than the drowned half:
## the half under the gallery's floor is a place the human cannot be (see the
## bay's fourth bullet), and an entry the flood cannot legally stand in reports
## an empty room instead of a trap. The tank shelf is here because the trap
## this level shipped with was exactly that room -- one tile of standable rock
## behind a shut sluice -- and nothing in the list was standing on it to notice.
RECONFIG_ENTRIES = [
    ("stage 1 gallery (spawn)", (2, 24)),
    ("stage 1 sump (above the intake)", (16, 27)),
    ("stage 1 east bay (past the flume)", (40, 27)),
    ("stage 2 west bank", (3, 13)),
    ("stage 2 bay (fallen into the east well)", (11, 15)),
    ("stage 2 stair alcove (behind the gate)", (32, 13)),
    ("stage 3 east tank", (22, 10)),
    ("stage 3 west tank (past the flume)", (8, 10)),
    ("stage 3 tank shelf (behind the sluice)", (3, 6)),
]

EXIT_TILE = (11, 2)


def check(k, verbose=True):
    """Everything the kit can say about this level before the prover runs.

    Not proof -- `tools/prove.sh` is. This is the fast filter that catches the
    class of error this project has shipped six times, plus the one question
    the prover structurally cannot answer: whether a switch configuration the
    player is allowed to leave the level in has sealed them away from a lever.
    """
    for label, entry in RECONFIG_ENTRIES:
        sizes = k.reconfig_check(entry, EXIT_TILE, form="human")
        if verbose:
            print("  reconfig     %-34s %s" % (label, sizes))
    return k.audit(strict_verbs=True)


if __name__ == "__main__":
    grid, kit = ruins_4()
    for line in check(kit):
        print(line)
    write(LEVEL_ID, grid, LEVEL_NAME, music="world2")
