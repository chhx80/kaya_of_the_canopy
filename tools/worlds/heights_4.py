#!/usr/bin/env python3
"""heights_4 -- THE LONG GLIDE.  World 3's last level, the run-up to The Stormcrest.

Self-contained: running this file under the project python writes
levels/heights_4.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `heights_4()` returning `(Grid, Kit)`,
which is the tuple tools/build_levels.py's `build()` expects -- that writer
audits the kit before it writes anything.

    source tools/env.sh && "$PYVENV" tools/worlds/heights_4.py
    tools/prove.sh heights_4

WHAT THE BIRD ACTUALLY DOES -- MEASURED, NOT MODELLED
-----------------------------------------------------
Every number below came out of a probe that ran `FormBase.update()` +
`Actor.step_motion()` at 60 Hz -- the two calls the player and the Route Prover
both make -- against a `TileWorld` built from the real tile table.  They are the
level: each piece of geometry here exists because one of these numbers says it
has to.

  * HOLDING JUMP IS NOT GLIDING.  `form_bird.gd` flaps whenever `input.jump` is
    held, `_flap_cd` (0.24 s) has elapsed and stamina >= flap_cost 12, and glides
    (glide_gravity 105 instead of gravity 420) only while `vel.y > 0` in the gaps
    between flaps.  A held button is therefore a *powered* glide: 8 flaps climb
    15.4 tiles in 2 s, and once the tank is empty air regen (stamina_regen 46 *
    0.25 = 11.5/s) still buys one flap a second, which in still air is a net
    climb.  Measured over 15 s of held jump: 96.9 tiles across and 31.5 tiles UP.

    That one measurement decides the whole level.  In open sky a bird's altitude
    is limited by the rock above it and by nothing else, so "trade altitude for
    distance" is not something the form does on its own -- it is something the
    author has to build.  Here it is built twice: with ceilings (THE LANE) and
    with falling air (THE CURTAIN).

  * A DIVE (jump released) is 0.57 tiles across per tile down at terminal
    (max_fall 190 against max_run 104), and terminal arrives in half a second.
    That is the emergency brake, not travel: 12.5 across costs 14.8 down.

  * AN UPDRAUGHT IS AN ELEVATOR AND IT IS FREE.  updraft (206) is [0,-400], so
    the fall cap becomes 190-400 and the bird rises at 210 px/s -- 13 tiles a
    second -- for no stamina at all.  The push is area-weighted, so at the top it
    overshoots about 3 tiles above the column's last row, bobs, and settles
    roughly level with it: from a shaft foot at row 25 the probe crossed the
    shaft's top row (6) at frame 101 and had steered out onto a perch capped on
    that same row by frame 256.  Both towers here are drawn to that shape -- the
    landing perch is capped level with the top of the column, one column clear of
    it.  Nothing in this level climbs by flapping, which is why the tank is still
    there when the exam starts.

  * A DOWNDRAFT IS THE ONE PLACE A FLAP IS WORTHLESS.  downdraft (208) is
    [0,+170] and a flap sets `vel.y = flap_vel -172 + current.y` = -2 px/s.
    Inside falling air the bird cannot climb at all; the tank only buys a
    shallower sink, and letting go of the button raises the fall cap to
    190+170 = 360.  Measured, crossing ten tiles of curtain at max_run (107
    frames):

        tank 100 -> sinks 0.18 tiles      tank 24 -> sinks 3.19 tiles
        tank  60 -> sinks 1.06 tiles      tank  0 -> sinks 5.85 tiles
        button released -> 30.4 tiles in the same 107 frames

    THE CURTAIN below is eight tiles rather than ten, so those figures scale to
    roughly 0.15 / 0.85 / 2.6 / 4.7.  The mouth it aims at is five rows tall,
    which is the arithmetic that makes the crossing survivable on an empty tank
    and comfortable on a full one -- and makes letting go of the button fatal to
    the attempt at any tank.

  * A GUST IS A WALL WITH A SPEED LIMIT.  gust_left (210) is [-80,0] against the
    bird's max_run 104: flying into it the ground speed is 24 px/s.  Measured
    both ways round.  No gust is on this level's route, deliberately: a headwind
    costs seconds, and seconds spent inching across a screen seam are the camera
    thrash this project has already shipped once.  The vertical pair is the wind
    this level is about.

  * A PERCH IS THE TANK.  stamina_regen 46 + perch_regen_bonus 34 = 80/s on the
    floor: empty to full is 1.25 s of standing still, against 8.7 s in the air.
    Both glides start from a perch, and that is the level's whole instruction for
    the player.  It is NOT what makes the route provable -- see THE TANK AND THE
    PROVER below, which is the most useful thing in this file.

  * THE FROG, for the stair out of the sump: hitbox 12x11, apex 5.34 tiles held,
    and it landed cleanly on 3-tile rungs in the probe.  LIMITS["frog"]["rise"]
    is 3 and the rungs are 3 apart.  LIMITS["frog"]["gap"] is 3 and the kit calls
    that a REAL ceiling -- four tiles fails by over two tiles of closest
    approach -- which is the fact the sump's four-tile gap is built on.

THE SHAPE OF THE LEVEL
----------------------
50x30, two screens by two, because docs/plan-20-levels.md fixes that: the side
margins of a wider world are where the touch controls live.  The vertical seam is
between cols 24 and 25, the horizontal one between rows 14 and 15.

  THE SUMP (cols 1-12, rows 19-27).  A sealed hall under the west massif, floor
        at row 28 (stand row 27).  Kaya spawns on foot, walks three tiles east to
        `pad_frog`, and the frog climbs two 3-tile rungs to a ledge with
        `pad_bird` on it.  Then, and only then, anything in this level flies.

  THE FOUR-TILE GAP (cols 4-7, rows 20-21).  Between that ledge and the
        updraught's mouth, with a nine-row drop under it.  It is the level's one
        piece of arithmetic aimed at a form rather than at the player: the frog
        clears three tiles and not four, measured, so the frog cannot follow the
        bird into the shaft -- and a frog carried to the top of the tower would
        be a frog that cannot fly, cannot climb back down, and has no pad to
        touch.  ADR 004 is enforced by a gap, and the shaft is floored at row 22
        so nothing can get into it from the sump floor either.

  T1, THE UPDRAUGHT (cols 9-12, rows 4-21).  `updraft_shaft`, mouth at cols 9-10,
        17 rows in about 1.4 s.  One-way, like ruins_4's flumes: the fall cap
        inside it is -210 px/s, so nothing comes back down, and nothing the level
        needs is behind it.

  PERCH 1 (cols 14-16, plank on row 4, stand row 3).  The launch balcony, capped
        on the shaft's own top row.  1.25 s here is a full tank.

  GLIDE 1, THE LONG ONE (cols 17-43, 26 tiles).  The leg the level is named for,
        and the forgiving one.  THE FUNNEL steps the ceiling down east of the
        balcony -- S1 at cols 18-19 leaves rows 3-9, S2 at cols 20-21 leaves rows
        5-9, and THE EYRIE MASS (cols 22-32, rows 1-7) leaves rows 8-9 for eleven
        tiles -- so the line has to come off the balcony and down into THE LANE
        (rows 8-9) a row at a time, one row of height per step of distance.  And
        once that roof is overhead the altitude is spent, which is the only
        meaning "committed" can have for a form that otherwise climbs a tile a
        second.  The lane's floor is the MID-SHELF (rows 10-11, stand row 9), so
        sinking early costs a climb and nothing else.  At col 33 the lane runs
        out into the curtain, and the curtain finishes the descent for you.

  THE CURTAIN (downdraft, cols 33-40, rows 1-17).  Eight tiles of falling air
        from the roof to the shoulder, crossed twice, meaning something different
        each way.  Eastbound it is a helping hand you cannot miss: THE FIN (cols
        41-43, rows 5-10) means an arrival that is still high slides down rock
        into the doorway at rows 11-13.  Westbound it is the exam.

  T2, THE CRAG DRAUGHT (cols 44-46, rows 3-15) and THE SUMMIT PLANK (cols 47-48,
        row 4, stand row 3).  The way back up, and free: the bird arrives at rows
        11-13, drifts into the column, rides 12 rows, bobs at the lip and steers
        east onto the plank -- the same shape as the tower and the balcony.  The
        plank is the staging perch: 1.25 s on it and the tank is full.  This is
        also where the pocket drains to, so a failed exam is a lap of the crag
        and not a life.

  GLIDE 2, THE EXAM (cols 42-33 westbound, rows 1-6).  Out of the summit's west
        doorway (col 43, rows 1-4), across eight tiles of falling air, into THE
        EYRIE's mouth: a cave cut into the eyrie mass at cols 25-32, rows 2-6,
        with the way out of the level at the back of it.  Leave high with a full
        tank and you arrive in the top of the mouth; leave with an empty one and
        you arrive scraping its bottom lip; let go of the button and you are on
        the shoulder, thirty rows down, looking at the crag again.

  THE POCKET (cols 25-46, rows 12-17) over THE SHOULDER (cols 25-48, rows 18-28).
        Where a failed line lands.  Standing there inside the curtain the bird
        cannot fly out -- a flap is worth -2 px/s -- so it walks east out of the
        wind and flaps the two rows into T2's column.  THE POCKET STEP (cols
        41-43, cap row 16) is the same idea one storey up: it keeps the east end
        of the pocket two rows under the fin rather than six.

WHY THE EXIT IS NOT SKIPPABLE, WHICH IS A GEOMETRY ARGUMENT AND NOT A HOPE
--------------------------------------------------------------------------
A form with no altitude ceiling makes sequence hard to enforce: in open sky
everything is reachable from everywhere.  So the eyrie is behind air rather than
behind rock, and the argument runs:

  * The eyrie's only opening is its east face, rows 2-6 at col 32.  Row 1 and row
    7 of cols 22-32 are solid and cols 22-24 are solid from row 1 to row 28, so
    it cannot be entered from above, below or the west, and the lane that passes
    underneath it is sealed off from it by its floor.
  * To be at rows 2-6 east of col 32 you have to be inside the curtain, and
    inside the curtain a bird cannot gain a pixel of height.
  * So you have to enter the curtain high from its EAST side, and the only still
    air on that side above the fin is cols 41-42 at rows 1-4, which is the
    summit's doorway.
  * The summit is T2's lip, and T2's foot is at rows 11-15 -- which is where
    GLIDE 1 arrives, having been forced down to rows 8-9 by the eyrie mass.

So the level cannot be finished out of order, and none of that depends on the
player not noticing something.

THE TANK AND THE PROVER, WHICH IS WHY THIS LEVEL IS SHAPED THE WAY IT IS
------------------------------------------------------------------------
`ProverSearch._key()` hashes position, velocity, form, on_floor, coyote, buffer
and the switch/key bits.  It does NOT hash stamina.  Two states that differ only
in how full the tank is therefore collapse into one, and the consequence is
sharp: **the prover cannot wait on a perch.**  Sitting still for 1.25 s produces
states it has already seen, so the frontier never contains "same place, fuller
tank".  A level that needs a refill between two hops is a level the gate cannot
play, however obvious the perch is to a human.

Everything about this level's second half follows from that:

  * No climb on the route costs stamina.  Both towers are updraughts, and the
    east crag is a draught rather than the plank ladder the first draft had --
    a bird flapping nine rows up a chimney arrives with a tank of about 10, and
    then the exam is a coin toss.
  * The mouth is five rows tall, not three.  Three rows is the better puzzle and
    it needs a tank of ~35 at the summit; five rows is crossable on an empty
    tank, so the proof does not depend on a refill that the search is
    structurally unable to perform.  What the player experiences is unchanged in
    kind: a full tank puts you in the middle of the mouth and an empty one puts
    you on its lip.
  * The curtain is eight tiles rather than ten, for the same arithmetic.
  * Each crossing is ONE hop whose goal is both downwind and BELOW its start.  An
    earlier draft put a waypoint mid-curtain at a height the search had already
    sunk past; it spent all 50,000 expansions and stopped 3.7 px under the tile,
    unable to lift itself four pixels.  A mark above the line is not a hard mark
    in falling air, it is an impossible one.

ADR 004 -- NO TRANSFORM STRANDS YOU
-----------------------------------
There are two pads and both are in the sump, which is the whole of the argument:

  * THE HUMAN exists only on the sump floor.  `pad_frog` is three tiles from the
    spawn on that floor, and she cannot leave it: the first rung is three rows up
    and her measured rise is two.
  * THE FROG exists only in the sump.  `pad_bird` is on the top rung; if it falls
    off anything it lands on the floor and climbs again; and it cannot follow the
    bird out, because the gap to the shaft is four tiles and it clears three.
  * THE BIRD needs no pad, and there is nowhere in the level a bird cannot leave:
    the pocket drains east into T2's column, and T2 reaches the summit.
  * So the level ends as the bird -- it touches the exit in the eyrie.  An
    earlier draft put `pad_human` next to that exit, which reads better and is a
    trap: the eyrie's floor ends at col 32, a walking Kaya steps off it into the
    curtain, falls thirteen rows into the pocket, and there is no pad down there
    and no rise she can climb.  A nicer last beat is not worth a softlock.

`check()` floods the two walking forms with `reachable_set` to keep all of that
honest -- including the negative halves, which are the ones that matter: the frog
must NOT reach the shaft and the human must NOT reach the rungs.

THE PALETTE
-----------
`Palette.char()` resolves a tile NAME through the flat, jungle-derived `legend`
key of data/level_legend.json, so THERMAL HEIGHTS's own names (heights_rock,
heights_plank, ...) have no character there and fall through to UNDERSTUDY --
which lands `solid` on 's' (heights_basalt, the *second* solid) and `bg` on 'r'
(heights_cloud, a background accent).  ADR 002's amendment says a character means
whatever the level's world says it means, so this palette is declared in terms of
the jungle tile whose character IS the heights role character: `grass_top` for
'#', `bg_leaves` for 'L', and so on.  The result is zero substitutions
(`Palette.missing()` is empty and `audit(strict_verbs=True)` is clean) and the
level serialises `"tileset": "heights"`, so the game paints heights_rock and
heights_plank.  The draughts are `shared` characters and are the real tiles either
way: this level loses no verb to an understudy, which for a level whose whole
subject is moving air is the difference between a proof and a story about one.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                      # noqa: E402
from world_kit import Kit, Palette, reachable_set       # noqa: E402

LEVEL_ID = "heights_4"
LEVEL_NAME = "THE LONG GLIDE"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the heights role
## character.  See THE PALETTE in the module docstring: this is a character map,
## not an art claim, and the art comes from `"tileset": "heights"` at load time.
HEIGHTS_W3 = Palette("thermal_heights", {
    "bg": "bg_leaves",            # 'L' -> heights_wall
    "solid": "grass_top",         # '#' -> heights_rock
    "solid_alt": "stone_mossy",   # 'S' -> heights_rock_sun
    "packed": "dirt",             # 'd' -> heights_scree
    "block": "stone",             # 's' -> heights_basalt
    "oneway": "wood_platform",    # '=' -> heights_plank
    "ladder": "vine",             # '|' -> heights_chain
    "hazard": "spikes",           # '^' -> heights_vent
    "water": "water",             # 'w'  shared
    "water_top": "water_top",     # '~'  shared
    "decor": "tree_trunk",        # 'T' -> heights_stack
    "void": "bg_dark",            # 'X' -> heights_air
    "breakable": "crate",         # 'c' -> heights_shell
    "shoulder": "cracked_stone",  # 'k'  shared
    "rubble": "rubble",           # 'o'  shared
    "updraft": "updraft",         # 'U'  shared
    "updraft_strong": "updraft_strong",   # '*'  shared
    "downdraft": "downdraft",     # 'V'  shared
    "gust_right": "gust_right",   # ')'  shared
    "gust_left": "gust_left",     # '('  shared
})

## 'r' is heights_cloud: background, no collision, and no kit role -- ROLES has
## `decor` and `void` and nothing for "a wisp behind the playfield". Written
## straight onto the bg layer rather than through the palette, because inventing a
## role for it would put a character in the kit that the other four worlds have
## no use for. The character is in the heights tileset, so
## Grid._check_characters accepts it and the game paints tile 250.
CLOUD = "r"


def air_mark(k, name, x, y, tall=2):
    """Name a tile of open air on a flight path.

    `Kit.mark` promises the tile is STANDABLE, which is the right promise for a
    walked route and the wrong one for a bird: most of the waypoints in this
    level are places a glide passes through at 104 px/s with twenty rows of
    nothing underneath them.  What is still worth promising -- and what this
    claims -- is that a body FITS there, so an air mark a later mass is drawn
    over fails the audit instead of failing the prover twenty minutes later.
    """
    k.g.mark(name, x, y)
    k._claim("clear", "air mark '%s'" % name, x=x, y=y, tall=tall)
    return name


def heights_4():
    g = Grid(W, H, tileset="heights")
    k = Kit(g, HEIGHTS_W3, form="bird")

    # ------------------------------------------------------------ the mountain
    # Built rather than carved: this is a sky level and open air is the default
    # state of most of the grid. Order matters and audit() is what checks it -- a
    # mass drawn over an earlier lane is the bug that system exists for.
    k.fill_bg("bg")
    k.shell(1, "solid")

    # THE WEST MASSIF: the roof over the sump and the west wall of the sky.
    k.rect(1, 1, 7, 18, "packed")
    k.rect(1, 1, 7, 1, "solid")

    # ===================================================== THE SUMP (the start)
    # Sealed: massif above, shell west and south, the updraught's walls east.
    # Capped out to col 13 -- one column further than the hall needs -- because
    # col 13 is the shaft's east wall and it stops at row 21, so a floor that
    # stopped at col 12 left a hole in the ground under it.
    k.floor(1, 28, 13)                    # cap row 28 -> stand row 27

    # THE STAIR OUT OF THE SUMP. Two planks, three rows apart, which is the
    # frog's measured rise; `stair` checks that against LIMITS before it draws a
    # tile. Both rungs are kept west of col 6 so that a frog jumping off one
    # cannot reach the updraught's rows even at the top of its 5.34-tile arc --
    # it carries about a tile and a half sideways over three rows of climb, and
    # the column starts at col 9.
    k.ledge(2, 25, 4)                     # plank cols 2-5 -> stand row 24
    k.ledge(2, 22, 2)                     # plank cols 2-3 -> stand row 21

    # ====================================================== T1, THE UPDRAUGHT
    # x=8 w=4 puts the interior at cols 9-12 and the walls on cols 8 and 13; the
    # helper stops the west wall two tiles above the bottom and carves the foot,
    # so the mouth of the shaft is col 8 at rows 20-21 (defect 5), and the roof
    # claim keeps rows 2-3 open above cols 9-10 (defect 6).
    k.updraft_shaft(8, 4, 4, 21, mouth=(9, 10))
    # The shaft's own floor, drawn after it: without this the column is open to
    # the sump hall below and the frog can be lifted out of the level from the
    # ground. With it, the four-tile gap at rows 20-21 is the only way in.
    k.rect(9, 22, 4, 1, "solid")

    # PERCH 1, the launch balcony. Capped on row 4 -- the shaft's own top row --
    # because a bird leaves an updraught by bobbing at the lip and steering
    # sideways, not by being launched clear of it.
    k.ledge(14, 4, 3)                     # plank cols 14-16 -> stand row 3

    # ============================================= THE MID-SHELF AND THE LANE
    # The shelf is GLIDE 1's floor and the roof of everything below it. Stand row
    # 9: nothing in this level stands on row 14 or row 29, because a floor capped
    # on a multiple-of-15 row is drawn on the far side of a screen seam from the
    # body standing on it -- ruins_4 shipped a gallery nobody could see.
    k.floor(14, 10, 19, depth=2)          # cap row 10, cols 14-32 -> stand row 9
    k.rect(14, 12, 11, 17, "packed")      # the massif under it, cols 14-24
    k.rect(14, 12, 11, 1, "solid")

    # THE FUNNEL: two spurs hanging off the roof west of the eyrie mass, each two
    # rows deeper than the last, so the sky east of the balcony steps DOWN --
    # slot rows 3-9 under S1, rows 5-9 under S2, rows 8-9 under the mass.
    #
    # Measured out of the first capture run, which is the only reason it is two
    # spurs and not one. The first draft hung S1 from row 1 to row 3, level with
    # the balcony's own standing row, and holding the button off the balcony --
    # which is what a player does, and which FLAPS (8 of them, 15 tiles of climb)
    # -- pinned the bird against the roof and rammed it into S1's west face two
    # tiles from the perch. It stopped dead at 104 px/s with vel.x reading 0. That
    # is a wall, not a glide.
    #
    # Stepped, the same held button reads as the lesson instead: you drift east
    # under S1, the ceiling comes down, and you trade a row of height for each
    # step of distance. Which is the sentence the level is trying to say.
    k.rect(18, 1, 2, 2, "packed")
    k.rect(18, 2, 2, 1, "solid")
    k.rect(20, 1, 2, 4, "packed")
    k.rect(20, 4, 2, 1, "solid")

    # ============================================ THE EYRIE MASS AND THE EYRIE
    # Eleven tiles of ceiling over the lane with the way out of the level cut
    # into it. Drawn solid and carved second: the carve is what makes the mouth.
    k.rect(22, 1, 11, 7, "packed")
    k.rect(22, 1, 11, 1, "solid")         # the roof of the world here
    k.rect(22, 7, 11, 1, "solid")         # its underside, and the lane's ceiling
    k.clear_rect(25, 2, 8, 5)             # THE EYRIE: cols 25-32, rows 2-6
    k.rect(25, 7, 8, 1, "solid")          # its floor -> stand row 6

    # ============================================================ THE CURTAIN
    # Eight tiles of falling air, roof to shoulder. The whole level turns on the
    # sink table in the docstring; this is the tile that produces it. Flush
    # against the eyrie mass on purpose: a column of still air between the two
    # would be a riser a bird could climb out of the lane on, which is the skip
    # the geometry argument above exists to rule out.
    k.rect(33, 1, 8, 17, "downdraft")

    # THE FIN. Rock at rows 5-10 across the three columns between the curtain and
    # the crag, so the still air on the crag's side of the wind is cols 41-42 at
    # rows 1-4 and nothing else. Eastbound it is what funnels a high arrival down
    # into the doorway; the rest of the time it is the lid on the only riser that
    # could have short-circuited the level.
    k.rect(41, 5, 3, 6, "solid")

    # ============================================ THE SHOULDER AND THE POCKET
    k.floor(25, 18, 24)                   # cap row 18, cols 25-48 -> stand row 17
    # THE POCKET STEP, drawn after the curtain, which would otherwise fill these
    # tiles: it puts the east end of the pocket two rows under the fin instead of
    # six, which is a human rise and a frog rise as well as a bird's.
    k.rect(41, 16, 3, 2, "packed")
    k.rect(41, 16, 3, 1, "solid")         # cap row 16 -> stand row 15

    # ====================================================== T2, THE CRAG DRAUGHT
    # Hand-drawn rather than `updraft_shaft`, because its west wall is not a wall
    # at all: col 43 has to be open at rows 1-4 (the summit's doorway, where the
    # exam starts) and at rows 11-15 (where GLIDE 1 arrives), and rock only in
    # between -- which the fin above already is. What the helper would draw
    # instead is a wall from top to bottom, sealing both.
    k.rect(47, 5, 2, 13, "packed")        # the crag's east body, cols 47-48
    k.rect(44, 3, 3, 13, "updraft")       # the column, cols 44-46, rows 3-15
    k.ledge(47, 4, 2)                     # THE SUMMIT PLANK -> stand row 3

    # ---------------------------------------------------------------- dressing
    # Background only: nothing here has collision or carries a claim. It is still
    # the second most important block in the file, and both halves of it were
    # written after reading the captures rather than before.
    #
    # THE SKY is heights_cloud. In THERMAL HEIGHTS the pale cloud field is what
    # open air looks like -- heights_1's summit and heights_2's lane both read
    # that way -- and the first capture run of this level, whose lanes were
    # `fill_bg("bg")` like a ruins interior, read as a cave with a bird in it.
    g.rect(0, 0, W, H, CLOUD, "bg")
    #
    # THE WIND IS DRAWN DARK, and that is a legibility fix and not a mood.
    # `tools/art/tiles.py:t_draft` is "mostly transparent -- it sits in front of
    # the backdrop": three streaks at alpha 110. Over the pale cloud field the one
    # verb this level is ABOUT is almost invisible; over heights_wall it reads as
    # a moving column. So every draught in the level gets the wall behind it, and
    # the level acquires a rule a player can see from the balcony: the dark bands
    # in the sky are the ones that move you.
    k.rect(9, 4, 4, 18, "bg", "bg")       # T1, the updraught
    k.rect(33, 1, 8, 17, "bg", "bg")      # THE CURTAIN
    k.rect(44, 3, 3, 13, "bg", "bg")      # T2, the crag draught
    # heights_air ('X') and heights_stack ('T') were both tried behind the curtain
    # and both are worse: the air tile is a PALE field, so the streaks disappear
    # into the cloud sky again, and the stack tile is a columnar pattern that
    # reads as rock -- a wall drawn across the one lane the level asks you to fly
    # through. The wall it is. Updraught and downdraft then look alike, which is
    # the shared art of the world (heights_1 and heights_2 draw them the same
    # way); what tells them apart is the streak direction and, more usefully, the
    # shape -- a tower is three columns between rock walls, the curtain is eight
    # columns of open sky.
    # The two rooms that really are rooms keep the wall as well.
    k.rect(1, 19, 13, 9, "bg", "bg")      # the sump
    k.rect(25, 2, 8, 5, "bg", "bg")       # the eyrie
    # Stacks against the rock, where a face meets sky.
    k.rect(2, 20, 1, 8, "decor", "bg")
    k.rect(31, 12, 1, 6, "decor", "bg")

    # -------------------------------------------------------------- entities
    g.ent("player_spawn", 2, 27)
    g.ent("pad_frog", 5, 27)
    g.ent("pad_bird", 3, 21)              # the top rung, four tiles from the shaft
    g.ent("exit", 27, 6)                  # at the back of the eyrie

    # Three flyers, and where they are NOT is deliberate. `tools/itest.sh` replays
    # the proof tape in the real game, with enemies, and the prover's simulation
    # has none: a patrol parked on the proved line is a knockback the tape cannot
    # absorb and a failure that says nothing about the level. So each one holds a
    # line a PLAYER has to plan around -- the shelf at the lane's west mouth, the
    # pocket, the sump -- a row or more off the tape's own path.
    # None of them is inside the curtain: `Enemy` does not sample currents (only
    # `FormBase` does), so a flyer in falling air would be the one thing on screen
    # the wind does not touch.
    g.ent("enemy_flyer", 16, 9, axis="x", range=32)
    g.ent("enemy_flyer", 30, 16, axis="x", range=64)
    g.ent("enemy_flyer", 10, 24, axis="y", range=48)

    for (x, y) in [(3, 27), (8, 27), (4, 24), (11, 18), (11, 12), (16, 3),
                   (20, 6), (24, 9), (30, 9), (35, 4), (38, 8), (42, 12),
                   (45, 8), (48, 3), (31, 6), (34, 16), (39, 17)]:
        g.ent("gem", x, y)
    g.ent("heart", 2, 21)                 # on the rung, before the first flight
    g.ent("heart", 48, 3)                 # the staging perch, before the exam
    g.ent("heart", 30, 17)                # the consolation in the pocket

    # --------------------------------------------------- the route (ADR 005)
    # One pad of each kind, so each names a waypoint on its own -- and a pad
    # waypoint is only satisfied when the form has actually changed
    # (`ProverSim.waypoint_satisfied`), which is a stronger promise than a mark on
    # the pad's tile. The first draft used marks and hop 12 arrived at the tile
    # in mid-air, 8 px above the trigger box, still a bird.
    #
    # Air marks every four to six tiles along each glide, for the reason ADR 005
    # gives: a hop that needs a big budget is a hop that is too coarse. The two
    # curtain crossings are the exception and are one hop each -- see THE TANK
    # AND THE PROVER.
    k.mark("rung", 3, 24, form="frog")
    k.mark("shaft_foot", 9, 21, form="bird")
    air_mark(k, "shaft_mid", 10, 14)
    air_mark(k, "shaft_lip", 11, 5)
    k.mark("perch_1", 15, 3, form="bird")
    air_mark(k, "step_off", 19, 6)                  # under S1, already committed
    air_mark(k, "lane_w", 23, 9)
    air_mark(k, "lane_e", 30, 9)
    air_mark(k, "curtain_in", 34, 9)
    air_mark(k, "crag_door", 43, 12)
    air_mark(k, "draught_foot", 45, 13)
    k.mark("summit", 47, 3, form="bird")            # the staging plank
    air_mark(k, "launch", 42, 2)                    # still air, east of the wind
    air_mark(k, "mouth", 33, 3)

    g.route("spawn", "pad_frog", form="human")
    g.route("pad_frog", "rung", form="frog")
    g.route("rung", "pad_bird", form="frog")
    g.route("pad_bird", "shaft_foot", form="bird")
    g.route("shaft_foot", "shaft_mid", form="bird")
    g.route("shaft_mid", "shaft_lip", form="bird")
    g.route("shaft_lip", "perch_1", form="bird")
    g.route("perch_1", "step_off", form="bird")
    g.route("step_off", "lane_w", form="bird")
    g.route("lane_w", "lane_e", form="bird")
    g.route("lane_e", "curtain_in", form="bird")
    g.route("curtain_in", "crag_door", form="bird")
    g.route("crag_door", "draught_foot", form="bird")
    g.route("draught_foot", "summit", form="bird")
    g.route("summit", "launch", form="bird")
    g.route("launch", "mouth", form="bird")
    g.route("mouth", "exit", form="bird")

    return g, k


## ADR 004 as floods rather than assertions. `reachable_set` refuses the bird and
## the fish -- a ground flood would understate a flying form badly -- so these are
## only the walking forms, which is exactly where the risk is.
##
## The NEGATIVE cases are the point and are listed first in spirit: a frog that
## can reach the shaft is a frog that gets lifted into a level it cannot play,
## and a human who can reach the rungs is a human who can be left on one.
##
##   (label, form, from, must reach, must NOT reach)
RECOVERY = [
    ("the spawn can always walk back to pad_frog",
     "human", (2, 27), (5, 27), None),
    ("and cannot get up the frog's first rung (rise 3 against her 2)",
     "human", (2, 27), None, (3, 24)),
    ("the frog climbs the stair to pad_bird",
     "frog", (5, 27), (3, 21), None),
    ("and cannot cross the four-tile gap into the updraught (its ceiling is 3)",
     "frog", (5, 27), None, (9, 21)),
    ("nor reach the shaft from the sump floor, which the shaft's own floor blocks",
     "frog", (5, 27), None, (10, 21)),
]


def check(k, verbose=True):
    """Everything the kit can say about this level before the prover runs.

    Not proof -- `tools/prove.sh` is, and for the glides it is the only thing
    that could be: a ground flood fill has no model of a bird at all. What this
    catches is the class of error this project has shipped six times, plus the
    question the prover cannot answer because the route never goes there: can a
    walking form end up somewhere it cannot leave.
    """
    for label, form, start, want, deny in RECOVERY:
        seen = reachable_set(k, start, form=form)
        if want is not None and want not in seen:
            raise SystemExit(
                "heights_4: %s -- as the %s, %s cannot reach %s (%d tiles "
                "reachable). That is an ADR 004 strand."
                % (label, form, start, want, len(seen)))
        if deny is not None and deny in seen:
            raise SystemExit(
                "heights_4: %s -- as the %s, %s CAN reach %s, and must not. "
                "(%d tiles reachable.)"
                % (label, form, start, deny, len(seen)))
        if verbose:
            print("  adr004       %-5s from %-9s %-9s %s"
                  % (form, start,
                     ("reaches %s" % (want,)) if want else ("denied %s" % (deny,)),
                     label))
    return k.audit(strict_verbs=True)


if __name__ == "__main__":
    grid, kit = heights_4()
    for line in check(kit):
        print(line)
    write(LEVEL_ID, grid, LEVEL_NAME, music="world3")
