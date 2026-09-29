#!/usr/bin/env python3
"""deeps_2 -- CHEW THROUGH.  World 4, TERMITE DEEPS, second level.

Self-contained: running this file under the project python writes
levels/deeps_2.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `deeps_2()` returning `(Grid, Kit)`,
the tuple that writer's `build()` expects -- it audits the kit before it writes.

    source tools/env.sh && "$PYVENV" tools/worlds/deeps_2.py
    tools/prove.sh deeps_2

WHAT THE LEVEL TEACHES
----------------------
The world's second verb: a wall that is not a wall.  `FormBase.tick_break()`
opens any tile with a `break_hold` if you press into it with attack held --
sideways by facing, up or down by the stick -- and the blade still shatters the
same tiles on contact.  Five breakable tiles, five costs, one per beat:

    tile             id   break_hold   frames   where          atlas reads as
    rubble          215      0.18 s      11     beat 1 floor   32/256 px: chips
    cracked_dirt    212      0.25 s      16     beat 2 wall    brown, cracked
    cracked_stone   211      0.35 s      21     beat 1 wall    GREY masonry
    luminous_wall   214      0.40 s      25     beat 3 vault   grey + gold seam
    termite_wall    213      0.45 s      28     beat 4 wall    brown, chipped

THE LAST COLUMN IS NOT DECORATION, it is why beat 1 is the 21-frame wall rather
than the 11-frame one.  The costs wanted the cheapest wall first; the ATLAS
would not have it.  Measured out of assets/tiles/tileset.png, cell by cell:
`rubble` is 32 opaque pixels of 256 -- scattered chips, correctly, because it
is rubble -- and the first capture pass put it across beat 1's corridor and
produced a screenshot of Kaya walking into an empty corridor and stopping dead
against nothing at all.  Of the five, exactly two are GREY against this world's
browns: cracked_stone (211) and luminous_wall (214).  So the two walls that
have to be read at a glance in a dark level get them -- the one that teaches
the verb and the one with the treasure behind it -- and the half-transparent
tile moved to the only place where seeing through it is an affordance rather
than a bug: a floor, where the gaps show the shaft underneath.

Reported upward, not worked around: 212 and 213 are brown-on-brown and lean on
their `deep_void` backing to have a silhouette at all.  That is a note for the
World 4 art pass, not something a level can fix.

ACCUMULATED, not ceil'd, and the difference is real.  `tick_break` does
`break_progress += delta` and opens the tile on the first tick where
`break_progress >= break_hold`, so the count is not ceil(hold * 60): a sum of
sixteen 1/60ths in doubles is 0.2666..., and a sum of *fifteen* is
0.24999999999999997, which is less than 0.25.  cracked_dirt therefore costs 16
frames where the arithmetic says 15, and luminous_wall 25 where it says 24.
tests/test_verbs_breakables.gd pins the rubble end of this exactly ("still shut
after 10 ticks of a 0.18 s wall ... open by the 12th").  The M4 foundation
agent's contract table reads 11/16/25/27; this file's simulation of the same
accumulation gives 28 rather than 27 for termite_wall, which is one frame and
changes nothing about the level -- it is written down because a number nobody
wrote down is a number that gets re-derived wrongly.

Releasing attack for one frame zeroes the progress, so the cost is 11 to 28
frames of *uninterrupted* hold.  That is what makes an enemy walking at you the
real price of the 0.45 s wall, and it is why beat 4 is the one with a beetle
in it.

THE VERBS ARE DIFFERENTIATED BY WHO CAN USE THEM, AND HOW
---------------------------------------------------------
Every wall here carries a `break_hold`, so every wall opens to every form,
including the frog -- which has `can_attack: false` and no blade at all.  That
is deliberate and it is the one rule a World 4 level may not break: the palette
points `glowwall` at `luminous_wall` (214) rather than at `deep_glowwall` (270),
because 270 declares NO break_hold and only a weapon opens it.  A frog room
behind a 270 is a sealed room.  `check()` below asserts the hold of every plug
this level draws, so that cannot be reintroduced by a palette edit.

Given that, the two ways in read differently in play and the level uses both:

  * THE BLADE is instant and works at range.  The first wall is dead ahead in a
    straight, empty corridor six tiles from the spawn, which is the one place in
    the level where a thrown blade is the obvious thing to try.
  * THE SHOULDER is a hold, and it is the only option when you are the frog.
    The vault at beat 3 is met as the frog, by construction: the route turns
    her at (30,27) and there is no `pad_human` until screen B.

THE PROVER CANNOT BREAK A TILE.  MEASURED.
------------------------------------------
This is the load-bearing fact about the whole design, so it was measured
against the shipping prover rather than inferred from reading it.  Two rooms,
identical but for one tile, at `--budget=8000`:

    30x15 corridor, spawn (2,12) -> exit (26,12) ............ PROVED
        1 hop, 231 frames, 58 expansions, 307 ms
    the same corridor with ONE `rubble` tile at (15,11-12) .. FAILED
        8000 expansions spent, closest approach 166.0 px, stopped at tile (15,11)

`ProverSearch.action_set()` enumerates {left, none, right} x {jump, none} x
{none, up, down} -- eighteen actions, and ATTACK is not among them, even though
the bit exists.  `ProverSim.snapshot()` does not record which tiles are broken
either, so a search that *could* press attack would corrupt its own restores.
`prove.gd::_report_failure` says so out loud when a level has breakables in it.

So: **no wall in this level is ever the only way through.**  Every one of the
four is a chord across a loop whose long arc is walkable, climbable rock, and
that arc is what the declared route takes.  This is a constraint, not a taste:
a route hop through a plug fails the gate by 166 px, and ADR 005 does not
negotiate.  The teaching therefore has to come from *placement* --
the wall is always the short, straight, lit-by-reward line and the arc is
always visibly the long way round -- and `check()` encodes the half of that
which is mechanical:

  * with every plug SOLID, a human flood fill from the spawn still reaches the
    frog pad and a frog flood fill from the pad still reaches the exit.  No
    plug is a lock.
  * no mark on the declared route stands on a breakable tile.  A floor that can
    be dissolved under a waypoint is a waypoint that stops existing.
  * every plug's tile declares break_hold > 0, so the frog is never shut out.

The honest cost of that constraint is reported in REPORT: a player who never
discovers the verb can finish this level.  The walls are worth 2 hearts, ~9
gems and three shortcuts, and nothing else.

THE FOUR BEATS
--------------
Four screens, one beat each, walked as an S: the top-left screen, down the
east side of it into the bottom-left, east along the cellar into the
bottom-right, and up the east wall into the top-right, where the exit is.

  BEAT 1  THE CRUMB WALL (screen A: cols 1-23, rows 1-13).  A safe room, no
          enemies.  Spawn (3,12), walk east, and at col 9 a `cracked_stone`
          plug fills both rows of a two-tile corridor.  Grey masonry in a brown
          gallery, backed with void, at eye level, six tiles from where she
          starts: it is the first thing in the level and it cannot be walked
          past.  Twenty-one frames of hold, or one thrown blade -- and the blade
          is the point, because `attack` in Kaya's hands is a verb the player
          brought with them from World 1.  The arc is the ladder at col 6 she
          has just walked over: up to
          the shelf at stand 6, east to col 17, and off the end into a
          four-tile fall back onto the gallery at cols 18-19, east of the plug.
          A `rubble` tile is set INTO THE FLOOR at (16,13) -- the same verb
          pressed down instead of sideways, eleven frames, the cheapest wall in
          the game -- and the shaft under it drops
          through both screen seams onto beat 2's low line, skipping the
          descent ladder entirely.  The floor is the reliable place to teach
          the down-press: her feet are flush against it, where a ceiling needs
          her to jump and hold at the top of the arc.

  BEAT 2  BREAK HIGH OR WALK LOW (screen C: cols 3-23, rows 16-21).  The choice
          beat, and it is a choice because both answers are on screen at once.
          The ladder from beat 1 lands at (22,17) on the HIGH line, stand 17.
          Walking west there is a two-column pit at cols 15-16 -- jump it and
          meet a `cracked_dirt` plug at col 11 (sixteen frames), or drop into
          the pit and take the LOW line at stand 20, which is longer, plainer,
          and has no wall in it at all.  West of the plug the high line runs to
          col 6 with a heart, two gems and a BARK BEETLE on it, and then ends:
          cols 4-5 have no floor, so the reward shelf tips you back down onto
          the low line beside the ladder the route was heading for anyway.  The
          wall buys the treasure and about four tiles; it locks nothing.
          The beetle cannot follow you out.  `walker.gd` turns on
          `not ground_ahead(facing, 2.0)` even while chasing, so the missing
          floor at col 5 pens it west and the plug pens it east -- and its chase
          test is `absf(dy) < 40.0` while the low line is 42.5 px below its
          centre, so it does not even notice the route passing underneath.

  BEAT 3  THE LUMINOUS VAULT (screen D: cols 28-46, rows 17-27).  A wall with
          something behind it worth wanting and NOTHING else behind it: a
          4x2 cell at cols 28-31 holding a heart, two gems and a beetle, sealed
          by a `luminous_wall` at col 32 (twenty-four frames).  It is a dead
          end.  That is the point -- beats 1, 2 and 4 are shortcuts, so one wall
          in the level has to be a door to a room rather than a saving of time,
          or the verb only ever means "faster".
          It is reached as the FROG, off the first tread of the frog stair
          (stand 24, cols 33-36), so the blade is not on the table: this is the
          beat where the hold is the only verb there is.  The stair itself is
          three-tile rises, which is why the frog is here at all --
          LIMITS["frog"]["rise"] is 3 and the human's is 2.

  BEAT 4  THE PACKED WALL (screen B: cols 27-47, rows 5-13).  A wall under
          pressure.  The ladder out of screen D runs col 43 from row 18 to row
          6 and pierces BOTH of screen B's corridors, so at the halfway point
          you can step off west into the lower corridor -- stand 12, cols
          33-47, with a `termite_wall` at col 32 and a BARK BEETLE patrolling
          in front of it.  Twenty-seven uninterrupted frames with a 32 px/s
          patrol closing (54 px/s once you are inside `chase_range` 96) and the
          exit five tiles beyond the wall.  Let go once and the clock restarts.
          The arc is to stay on the ladder to the top, take the `pad_human` at
          (40,6) and walk the upper corridor west to col 31, where the floor
          stops and a six-tile fall lands in the exit alcove.  The route takes
          the arc, so the tape never enters the beetle's corridor: the ladder
          tile at (43,13) is a hole in the lower corridor's floor, which pens
          the beetle in cols 33-42 by the same `ground_ahead` rule as beat 2.

WHERE THE FLOORS SIT
--------------------
`CameraController` picks its screen from the body's CENTRE, so a floor capped
on the first row of a screen is a floor its own player never sees -- ruins_4
shipped a gallery walked along the last pixel of a frame.  The horizontal seam
is y=240, between rows 14 and 15; the vertical seam is x=400, between cols 24
and 25.  Every stand row here is 6, 12, 17, 20, 24, 21, 18, 27 -- none of them
14 or 29 -- and `check()` asserts that of every mark rather than trusting this
paragraph.

The seams are crossed exactly three times and never by a jump:

    col 22, rows 12-17   the ladder down from beat 1 into beat 2
    col 16, rows 13-18   the rubble floor chute, a fall
    col 43, rows 6-18    the ladder up from beat 3 into beat 4
    rows 26-27, col 24/25   the cellar, walked flat across the vertical seam

A hop on foot across a seam is the defect that pens this project in; a climb or
a fall across one is fine, and ruins_4's bank_foot -> bank_top hop proves the
horizontal seam is crossable inside a single hop.

THE PALETTE
-----------
`Palette.char()` resolves a tile NAME through the flat, jungle-derived `legend`
key of data/level_legend.json, so DEEPS's own names (deep_earth, deep_ladder,
...) have no character there and would fall through to UNDERSTUDY -- and two of
those understudies land on the wrong deeps role (`solid` emits 's', which is
deep_packed, and `bg` emits 'r', which is deep_fungus).  ADR 002's amendment
says a character means whatever the level's world says it means, so this
palette is declared in terms of the JUNGLE tile whose character IS the deeps
role character: `grass_top` for '#', `bg_leaves` for 'L', `dirt` for 'd'.

The four breakables need no such trick.  'o', 'j', 'O' and 'm' are `shared`
characters -- the same tile in every world -- so `rubble`, `cracked_dirt`,
`luminous_wall` and `termite_wall` resolve to themselves.  The result is zero
substitutions: `Palette.missing()` is empty and `audit(strict_verbs=True)` is
clean, and the level serialises `"tileset": "deeps"`, so the game paints
deep_earth and deep_ladder while the walls stay the walls.

DARKNESS
--------
deeps_2 is early, so it is dim rather than black -- the desired
data/ambience.json entry is in AMBIENCE below, quoted rather than written,
because that file is shared.  Darkness is visual only (data/fx.json's
`_why_visual_only`), so it changes nothing here that the prover can see.  What
it does change is what the geometry has to do for itself: every plug is set in
a frame of rock with clear air on both sides of it, at the end of a straight
run, so it reads as a filled doorway rather than as more wall.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                      # noqa: E402
from world_kit import Kit, Palette, tiles               # noqa: E402

LEVEL_ID = "deeps_2"
LEVEL_NAME = "CHEW THROUGH"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the deeps role character.
## See THE PALETTE in the module docstring: this is a character map, not an art
## claim, and the art comes from `"tileset": "deeps"` at load time.  The four
## breakables are `shared` characters and are the real tiles either way.
DEEPS_W4 = Palette("termite_deeps", {
    "bg": "bg_leaves",             # 'L' -> deep_comb
    "solid": "grass_top",          # '#' -> deep_earth
    "solid_alt": "stone_mossy",    # 'S' -> deep_crust
    "packed": "dirt",              # 'd' -> deep_chitin
    "block": "stone",              # 's' -> deep_packed
    "oneway": "wood_platform",     # '=' -> deep_shelf
    "ladder": "vine",              # '|' -> deep_ladder
    "hazard": "spikes",            # '^' -> deep_spore
    "water": "water",              # 'w'  shared
    "water_top": "water_top",      # '~'  shared
    "decor": "tree_trunk",         # 'T' -> deep_root
    "void": "bg_dark",             # 'X' -> deep_void
    "rubble": "rubble",            # 'o'  shared, 215, 0.18 s -- the floor chute
    "breakable": "cracked_stone",  # 'k'  shared, 211, 0.35 s -- beat 1
    # THE KIT HAS FOUR BREAKABLE ROLES AND THIS LEVEL DRAWS FIVE BREAKABLE
    # TILES, so one of the solid roles it does not otherwise use carries the
    # fifth.  `block` is "a second decorative solid" and this level draws no
    # decorative solid at all, so it is the one to spend.  Nothing downstream
    # cares -- `breakable_wall` reads the role's FLAGS, and cracked_dirt is
    # `solid` + `breakable` + break_hold like every other plug here -- but it
    # is worth the four lines, because a reader looking for beat 2's wall will
    # otherwise grep for a breakable role and not find it.
    "block": "cracked_dirt",       # 'j'  shared, 212, 0.25 s -- beat 2
    "glowwall": "luminous_wall",   # 'O'  shared, 214, 0.40 s -- beat 3
    "shoulder": "termite_wall",    # 'm'  shared, 213, 0.45 s -- beat 4
})

## The four plugs, as (role, x, feet_row, height, what it is for).  One list so
## check() can walk them instead of re-deriving the coordinates, and so the
## break-cost table in the docstring has a single source.
PLUGS = [
    ("breakable", 9, 12, 2, "beat 1: the corridor plug, six tiles from the spawn"),
    ("rubble",   16, 13, 1, "beat 1: the floor chute, pressed DOWN not sideways"),
    ("block",    11, 17, 2, "beat 2: the high line's wall"),
    ("glowwall", 32, 24, 2, "beat 3: the vault"),
    ("shoulder", 32, 12, 2, "beat 4: the packed wall, with a beetle on it"),
]

## The ambience entry this level wants.  REPORTED, NOT WRITTEN:
## data/ambience.json is shared with five other levels being authored in
## parallel, so this module prints the block instead of editing the file.
##
## The world's recipe is darkness 0.88 / vignette 0.40 / emissive keyed by
## FOREGROUND tile id (a glow tile on the bg layer is silently ignored) with
## the 74 px player lantern from data/fx.json.  deeps_2 takes the whole recipe
## except the alpha: 0.70 rather than 0.88, because this is the world's second
## level and its job is to teach a verb, not to hide it.  At 0.88 a `rubble`
## tile four tiles ahead is inside the lantern and a `termite_wall` across a
## corridor is not, which makes the level about the light instead of about the
## wall.  Integration should raise it to 0.88 the moment deeps_3 exists to
## carry the dark half of the arc; nothing in the geometry changes if it does,
## because darkness never reaches collision (data/fx.json `_why_visual_only`).
##
## The one emitter is 214, luminous_wall -- the vault at beat 3, which is an fg
## tile and therefore actually lights.  It is the only wall in the level with a
## room behind it, and it is the only one you can see from across a chamber.
AMBIENCE = '''    "deeps_2": {
      "_note": "CHEW THROUGH. The second level of the world, so it is dim rather than black: darkness 0.70 against the world's 0.88 keeps a wall four tiles ahead legible, because this is the level that has to teach you that some walls are not walls. The only emitter is the luminous wall at the vault (214), an fg tile, merged along its run -- the one wall here with a room behind it is the one you can see from across the chamber.",
      "world": "deeps",
      "air": { "ramp": "water", "step": 1, "alpha": 0.34 },
      "bg_tint": { "ramp": "water", "step": 3, "mix": 0.80, "scale": 0.52 },
      "fg_tint": { "ramp": "gold", "step": 5, "mix": 0.20, "scale": 0.92 },
      "vignette": 0.40,
      "darkness": 0.70,
      "emissive": {
        "214": { "ramp": "gold", "step": 6, "intensity": 0.34, "radius": 30, "lift": 5 }
      }
    },'''


def deeps_2():
    g = Grid(W, H, tileset="deeps")
    k = Kit(g, DEEPS_W4, form="human")

    # ------------------------------------------------------------- the rock
    # Carved, not built.  A tunnel cut out of solid earth keeps the prover's
    # frontier inside the tunnel instead of wandering open space -- which is
    # the difference between a 58-expansion hop and a budget failure.
    k.fill_bg("bg")
    k.fill_solid("packed")
    k.shell(1, "solid")

    # ============================================== BEAT 1 -- THE CRUMB WALL
    # The gallery: stand 12 over a cap at 13.  Row 13 is inside the top-left
    # screen with her (the seam is row 14/15), so she can see the floor she is
    # standing on.
    k.corridor(1, 12, 23, h=2)                  # rows 11-12, cols 1..23
    k.floor(1, 13, 23, depth=1)                 # cap row 13

    # The arc over the plug: a ladder at col 6 -- which she walks over on the
    # way to the wall -- to a shelf at stand 6, east along it, and off the end
    # at cols 18-19 into a four-tile fall back to the gallery.  Drawn before the
    # ladders, which all go in last so nothing caps them.
    k.corridor(6, 6, 14, h=2)                   # rows 5-6, cols 6..19
    k.floor(6, 7, 12, depth=1)                  # cap row 7, cols 6..17
    k.clear_rect(18, 7, 2, 4)                   # the hole at cols 18-19, rows 7..10

    # ========================================= BEAT 2 -- BREAK HIGH OR WALK LOW
    # The high line, stand 17.  Its cap is deliberately in two pieces: the pit
    # at cols 15-16 is the visible alternative to the wall, and the missing cap
    # at cols 4-5 is how the reward shelf west of the wall tips you back down
    # onto the low line instead of dead-ending.
    k.corridor(4, 17, 20, h=2)                  # rows 16-17, cols 4..23
    k.floor(6, 18, 9, depth=1)                  # cap row 18, cols 6..14
    k.floor(17, 18, 7, depth=1)                 # cap row 18, cols 17..23
    # A missing CAP is not a hole: the level is carved out of a solid block, so
    # the packed earth under row 18 is still there until it is cut away.  Both
    # of these are throats through to the low line, and the first draft left
    # them uncut -- the flood fill reached 55 tiles and stopped on the high
    # line, which is check() rule 2 catching exactly what it is for.
    k.clear_rect(15, 18, 2, 1)                  # the pit at cols 15-16
    k.clear_rect(4, 18, 2, 1)                   # the reward shelf's west fall-off

    # The low line, stand 20.  Longer, plainer, and the route's answer.
    k.corridor(3, 20, 21, h=2)                  # rows 19-20, cols 3..23
    k.floor(3, 21, 21, depth=1)                 # cap row 21, cols 3..23

    # The cellar, stand 27, cols 2..47.  The one place anything crosses the
    # vertical seam (x=400, between cols 24 and 25) and it crosses it walking
    # flat on rock.
    k.corridor(2, 27, 46, h=2)                  # rows 26-27
    k.floor(2, 28, 46, depth=1)                 # cap row 28

    # ============================================ BEAT 3 -- THE LUMINOUS VAULT
    # The stair chamber, carved BEFORE the treads: a tread written first and
    # carved over afterwards is the draw-order bug audit() exists for.
    k.clear_rect(32, 17, 15, 9)                 # cols 32..46, rows 17..25
    # Three-tile rises, which is the whole reason the frog is in this level:
    # check_rise refuses a 4-tile tread for LIMITS["frog"]["rise"] = 3, and
    # refuses ANY of these for the human, whose rise is 2.
    k.stair(33, 25, 3, rise=3, run=3, width=4, form="frog")

    # The vault: a 4x2 cell with one wall and no other opening.  Its cap is its
    # own, so audit() can tell a room from a pit.
    k.clear_rect(28, 23, 4, 2)                  # cols 28..31, rows 23-24
    k.floor(28, 25, 4, depth=1)                 # cap row 25

    # ============================================== BEAT 4 -- THE PACKED WALL
    # The upper corridor, stand 6.  Its cap stops at col 32 so that walking
    # west off the end is a six-tile fall into the exit alcove -- the arc.
    k.corridor(27, 6, 21, h=2)                  # rows 5-6, cols 27..47
    k.floor(32, 7, 16, depth=1)                 # cap row 7, cols 32..47

    # The exit alcove: six rows tall, cols 27..31, open to the sky of the upper
    # corridor and sealed from the lower corridor by the packed wall.
    k.clear_rect(27, 7, 5, 6)                   # rows 7..12
    k.floor(27, 13, 5, depth=1)                 # cap row 13

    # The lower corridor, stand 12, cols 33..47: the beetle's pen and the wall.
    k.corridor(33, 12, 15, h=2)                 # rows 11-12
    k.floor(33, 13, 15, depth=1)                # cap row 13

    # ------------------------------------------------------------- the plugs
    # After every floor and before the ladders.  breakable_wall claims a
    # standable tile on BOTH sides at the plug's own row -- so a wall you would
    # have to hit from mid-air fails the audit -- and releases the corridor
    # claim it is deliberately filling in.
    k.breakable_wall(9, 12, 2, role="breakable")        # beat 1, cracked_stone, 21f
    k.breakable_wall(11, 17, 2, role="block")           # beat 2, cracked_dirt,  16f
    k.glow_wall(32, 24, 2)                              # beat 3, luminous_wall, 25f
    k.breakable_wall(32, 12, 2, role="shoulder")        # beat 4, termite_wall,  28f

    # The floor chute.  Not breakable_wall: that helper is about a plug ACROSS a
    # corridor and claims room to stand on either side of it, which is the wrong
    # shape for a tile you are standing on top of.  One rubble tile in the
    # gallery's cap, with a clear shaft under it down to beat 2's pit.
    k.put(16, 13, "rubble")
    k.clear_rect(16, 14, 1, 2)                  # rows 14-15; rows 16-20 are already air
    k.note("the floor chute at (16,13): `rubble` in the gallery's cap, pressed "
           "DOWN + attack.  Eleven frames, and the shaft under it falls through "
           "both screen seams onto beat 2's low line.  A ceiling plug was tried "
           "first and rejected: `_break_target_of` probes one pixel above the "
           "head, and a 22 px body standing in a two-tile corridor has its head "
           "10 px inside the upper tile, so a ceiling can only be reached at the "
           "very top of a jump -- 11 frames of hold inside a jump arc is not a "
           "thing to teach a verb with.  A floor is always flush.")

    # ------------------------------------------------------------- the ladders
    # Every climb last, so no cap drawn later can overwrite one.  That failure
    # mode -- a ladder capped by a floor written afterwards -- is what
    # audit()'s ladder_exit claim is for, and it has happened twice in this
    # project.
    k.climb(6, 6, 12, landing="right")          # beat 1's arc, up to the shelf
    k.climb(22, 12, 17, landing="left")         # beat 1 -> beat 2, across the seam
    k.climb(3, 20, 27, landing="right")         # beat 2 -> the cellar
    k.climb(43, 6, 18, landing="left")          # beat 3 -> beat 4, across the seam
    # That last one pierces BOTH of screen B's corridors on the way past, and
    # both of those holes are load-bearing: (43,11-12) is the step-off into the
    # beetle's pen, and (43,13) is the missing floor tile that pens the beetle
    # in cols 33-42 by `walker.gd`'s `not ground_ahead(facing, 2.0)`.

    # -------------------------------------------------------------- dressing
    # Root columns and voids on the BACKGROUND layer only -- nothing here has
    # collision.  In a dark level this is most of what tells you a chamber is a
    # chamber, so the voids sit behind the two rooms with treasure in them.
    for x in (4, 13, 20):
        k.rect(x, 8, 1, 3, "decor", "bg")
    for x in (8, 19):
        k.rect(x, 22, 1, 4, "decor", "bg")
    for x in (29, 37, 45):
        k.rect(x, 14, 1, 2, "decor", "bg")
    k.rect(28, 23, 4, 2, "void", "bg")          # behind the vault
    k.rect(6, 16, 5, 2, "void", "bg")           # behind beat 2's reward shelf
    k.rect(27, 11, 20, 2, "void", "bg")         # the exit alcove and the beetle's pen
    k.rect(33, 17, 14, 9, "void", "bg")         # the stair chamber
    # A PLUG IS ONLY LEGIBLE AGAINST SOMETHING.  `deep_void` is the darkest
    # background tile in the world, and a solid plug standing in a corridor
    # backed with it is a lit block against black rather than more wall -- which
    # is most of what a dim level has instead of an outline.  Measured the hard
    # way: the first capture pass drew beat 1 out of `rubble` (215), whose art
    # is 32 opaque pixels of 256 -- scattered chips, not masonry -- and the
    # screenshot showed Kaya walking into a corridor with nothing in it.  She
    # was stopped dead; the wall simply could not be seen.  Beat 1 is
    # `cracked_stone` now, the one breakable in the atlas that is GREY against
    # this world's browns, and 215 was moved to the one place a half-transparent
    # tile is an asset: the floor, where seeing the shaft through the gaps in
    # the debris is the affordance.
    k.rect(7, 11, 5, 2, "void", "bg")           # behind beat 1's plug
    k.rect(9, 16, 5, 2, "void", "bg")           # behind beat 2's plug

    # -------------------------------------------------------------- entities
    g.ent("player_spawn", 3, 12)
    g.ent("pad_frog", 30, 27)
    g.ent("pad_human", 40, 6)
    g.ent("exit", 28, 12)

    # Three beetles, and every one of them is behind or in front of a wall.
    # None is on the declared route, which is not squeamishness: the prover does
    # not model enemies at all, so an enemy standing on the route is a hazard
    # the tape meets for the first time in tools/itest.sh.
    g.ent("enemy_walker", 8, 17)                # beat 2: guarding the reward shelf
    g.ent("enemy_walker", 29, 24)               # beat 3: inside the vault
    g.ent("enemy_walker", 37, 12)               # beat 4: the pressure

    g.ent("heart", 7, 17)                       # behind beat 2's wall
    g.ent("heart", 30, 24)                      # inside the vault
    for (x, y) in [(12, 12), (15, 12), (10, 6), (14, 6),
                   (9, 17), (10, 17), (18, 17), (21, 17),
                   (7, 20), (13, 20), (19, 20),
                   (10, 27), (17, 27), (24, 27), (27, 27),
                   (28, 24), (31, 24),
                   (35, 24), (38, 21), (41, 18),
                   (35, 6), (45, 6), (34, 12), (45, 12)]:
        g.ent("gem", x, y)

    # --------------------------------------------------- the route (ADR 005)
    # One pad of each kind, so `pad_frog` and `pad_human` name waypoints on
    # their own (gen_levels.Grid._waypoints refuses a type there are several
    # of) and the hop that arrives is the hop that transforms.
    #
    # No mark sits at the top of a ladder.  world_kit's `deeps_tunnel_seam`
    # proof room is the reproduction: `ProverSearch._set_input` derives
    # jump_pressed/jump_released from the previous macro, and at the start of a
    # hop there is no previous macro, so a hop that BEGINS on a ladder top with
    # `up` held reads a fresh press the replay can never see -- the search
    # leaves the body one tile from where the tape puts it.  Every mark here is
    # on flat floor, at least two tiles from any ladder.
    k.mark("shelf_w", 8, 6)
    k.mark("gallery_e", 21, 12)
    k.mark("high_e", 23, 17)
    k.mark("low_m", 12, 20)
    k.mark("low_w", 5, 20)
    k.mark("cellar_w", 2, 27)
    k.mark("cellar_m", 20, 27)
    k.mark("step_1", 34, 24, form="frog")
    k.mark("step_2", 37, 21, form="frog")
    k.mark("step_3", 42, 18, form="frog")
    k.mark("upper_e", 45, 6, form="frog")
    k.mark("upper_w", 33, 6)

    g.route("spawn", "shelf_w", form="human")
    g.route("shelf_w", "gallery_e", form="human")
    g.route("gallery_e", "high_e", form="human")
    g.route("high_e", "low_m", form="human")
    g.route("low_m", "low_w", form="human")
    g.route("low_w", "cellar_w", form="human")
    g.route("cellar_w", "cellar_m", form="human")
    g.route("cellar_m", "pad_frog", form="human")
    g.route("pad_frog", "step_1", form="frog")
    g.route("step_1", "step_2", form="frog")
    g.route("step_2", "step_3", form="frog")
    g.route("step_3", "upper_e", form="frog")
    g.route("upper_e", "pad_human", form="frog")
    g.route("pad_human", "upper_w", form="human")
    g.route("upper_w", "exit", form="human")

    return g, k


SPAWN_TILE = (3, 12)
PAD_FROG_TILE = (30, 27)
EXIT_TILE = (28, 12)


def _open_plugs(g):
    """Replace every plug tile with air, returning what was there.

    Used only by check(): the question "is this wall a lock or a shortcut" is
    the difference between the flood fill with them shut and the flood fill
    with them open, and the only way to ask it is to ask it twice.
    """
    was = []
    for _role, x, y, h, _why in PLUGS:
        for yy in range(y - h + 1, y + 1):
            was.append((x, yy, g.fg[yy][x]))
            g.fg[yy][x] = "."
    return was


def _restore(g, was):
    for x, y, ch in was:
        g.fg[y][x] = ch


def hold_frames(hold, dt=1.0 / 60.0):
    """How many frames of held input a `break_hold` really costs.

    NOT ceil(hold * 60), and the difference is not pedantry: `tick_break` does
    `break_progress += delta` and compares, so what matters is the accumulated
    double, not the exact quotient.  Fifteen 1/60ths sum to 0.24999999999999997
    and a 0.25 s wall is still shut on that frame.  Measured here rather than
    tabulated, so the number in the docstring and the number this file prints
    cannot drift apart -- which they did, once, for exactly as long as it took
    to read them side by side.
    """
    p = 0.0
    n = 0
    while p < hold:
        p += dt
        n += 1
    return n


def check(k, verbose=True):
    """Everything the kit can say about this level before the prover runs.

    Not proof -- `tools/prove.sh` is.  These are the four rules this level has
    that CAN be encoded, and the first of them is the one the whole design
    turns on.
    """
    g = k.g
    out = []

    # 1. Every plug opens to every form.  A tile with no break_hold opens only
    #    to a weapon, and the frog has none -- so a plug without one is a wall
    #    that some route through this level cannot pass.  This is the assertion
    #    that stops a palette edit sealing the vault with deep_glowwall (270).
    for role, x, y, h, why in PLUGS:
        name = k.pal.name(role)
        flags = tiles().flags_for_name(name)
        hold = float(flags.get("break_hold", 0.0) or 0.0)
        if not flags.get("breakable"):
            raise AssertionError("plug at (%d,%d) is '%s', which is not breakable"
                                 % (x, y, name))
        if hold <= 0.0:
            raise AssertionError(
                "plug at (%d,%d) is '%s', which declares no break_hold: only a "
                "WEAPON opens it, and the frog has none.  %s" % (x, y, name, why))
        if verbose:
            print("  plug         %-14s %-14s %4.2f s = %2d frames  %s"
                  % ("(%d,%d)x%d" % (x, y, h), name, hold, hold_frames(hold), why))

    # 2. No plug is a lock.  With every one of them SOLID -- which is how the
    #    Route Prover and tools/reachability.py both see them -- a human flood
    #    fill from the spawn still reaches the frog pad, and a frog flood fill
    #    from the pad still reaches the exit.
    human_shut = k.reachable_set(SPAWN_TILE, form="human")
    if PAD_FROG_TILE not in human_shut:
        raise AssertionError(
            "with every wall shut, the human cannot reach pad_frog at %s from "
            "the spawn (%d standable tiles reached).  A wall has become a lock, "
            "and a lock cannot be proved: measured, a single rubble tile across "
            "a corridor costs the prover 8000 expansions and 166 px."
            % (PAD_FROG_TILE, len(human_shut)))
    frog_shut = k.reachable_set(PAD_FROG_TILE, form="frog")
    if EXIT_TILE not in frog_shut:
        raise AssertionError(
            "with every wall shut, the frog cannot reach the exit at %s from "
            "pad_frog (%d standable tiles reached)" % (EXIT_TILE, len(frog_shut)))

    # 3. And each wall is still worth breaking.  Opened, the same two floods
    #    grow -- by a shortcut's worth for beats 1, 2 and 4, and by a whole
    #    sealed room for beat 3.  A wall that changes nothing is decoration.
    was = _open_plugs(g)
    human_open = k.reachable_set(SPAWN_TILE, form="human")
    frog_open = k.reachable_set(PAD_FROG_TILE, form="frog")
    _restore(g, was)
    grew = (len(human_open) - len(human_shut)) + (len(frog_open) - len(frog_shut))
    if grew <= 0:
        raise AssertionError(
            "opening all four walls adds nothing a flood fill can see (%d/%d "
            "human, %d/%d frog).  Every wall in this level is optional by "
            "necessity, so if none of them opens anything the verb is not in "
            "the level at all."
            % (len(human_open), len(human_shut), len(frog_open), len(frog_shut)))
    if verbose:
        print("  walls shut   human %d standable tiles, frog %d"
              % (len(human_shut), len(frog_shut)))
        print("  walls open   human %d (+%d), frog %d (+%d)"
              % (len(human_open), len(human_open) - len(human_shut),
                 len(frog_open), len(frog_open) - len(frog_shut)))

    # 4. Nothing the route stands on can be dissolved, and no stand row sits on
    #    the first row of a screen.  Both are cheap; both have shipped.
    flags_of_char = tiles().flags_of_char
    for name, m in sorted(g.marks.items()):
        below = g.fg[m["y"] + 1][m["x"]]
        if flags_of_char.get(below, {}).get("breakable"):
            raise AssertionError(
                "mark '%s' at (%d,%d) stands on '%s', which is breakable: a "
                "waypoint whose floor can be dissolved is a waypoint that stops "
                "existing" % (name, m["x"], m["y"], below))
        if m["y"] % 15 == 14:
            raise AssertionError(
                "mark '%s' stands on row %d, whose floor is the first row of the "
                "next screen: CameraController picks the screen from the body's "
                "centre, so that floor is never drawn (ruins_4 shipped it once)"
                % (name, m["y"]))
    if verbose:
        print("  marks        %d, none standing on a breakable, none on a seam row"
              % len(g.marks))

    out.extend(k.audit(strict_verbs=True))
    return out


if __name__ == "__main__":
    grid, kit = deeps_2()
    for line in check(kit):
        print(line)
    write(LEVEL_ID, grid, LEVEL_NAME, music="world4")
    print("\n  data/ambience.json wants this entry (not written -- shared file):\n")
    print(AMBIENCE)
