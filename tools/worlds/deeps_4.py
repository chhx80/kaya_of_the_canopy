#!/usr/bin/env python3
"""deeps_4 -- SPORE LIGHT.  World 4's last level, the run-up to The Brood Queen.

Self-contained: running this file under the project python writes
levels/deeps_4.json, so the level can be iterated on without touching
tools/build_levels.py.  It also exports `deeps_4()` returning `(Grid, Kit)`,
which is the tuple tools/build_levels.py's `build()` expects -- that writer
audits the kit before it writes anything.

    source tools/env.sh && "$PYVENV" tools/worlds/deeps_4.py
    tools/prove.sh deeps_4

WHAT DARKNESS ACTUALLY IS HERE, MEASURED OUT OF src/world/
----------------------------------------------------------
Every number below came from reading the code that draws it, and the level is
built on them rather than on what "a dark level" sounds like.

  * DARKNESS IS TWO QUADS.  `AmbienceLayer` draws a flat shade over the tiles
    and one additive pool that follows the player (`_draw_lantern`), and
    entities are drawn after both.  It never reaches a tile flag, the collision
    or a form -- tests/test_verbs_darkness.gd runs 240 ticks lit and dark and
    demands the same pixel.  So the Route Prover proves the same geometry a lit
    room would, and what it CANNOT prove is that a human can see where to go.
    Every piece of light in this level is therefore an authored promise, not a
    mechanism, and the self-checks at the bottom of this file are what hold it.

  * THE CARRIED LIGHT IS 74 px.  data/fx.json's darkness block: radius 74,
    intensity 0.8, flicker 0.08.  That is 4.6 tiles from her centre, so a pit
    three tiles wide is ALWAYS visible from its own take-off tile.  Darkness in
    this engine cannot hide a hazard from the body standing next to it; what it
    hides is the room.  The exam is therefore never "did you see the spike" --
    it is "which way is on", answered at room scale by the spore light.

  * A POOL IS A LOZENGE, AND ITS SIZE IS ARITHMETIC.
    `AmbienceLayer._collect_emissive` walks the **fg layer only** inside the
    current screen, merges each horizontal run of one tile id, and draws it at
    half-extents (radius + (x1-x0)*8, radius) px.  With the fungus radius of 36
    this file asks for, a six-tile mat reaches 36 + 40 = 76 px -- about nine
    tiles wide in all -- and a two-tile lamp reaches 38.  POOLS below is that
    formula, and `check()` runs it over the finished grid.

    Two consequences the level is drawn around:
      - an emissive tile in the BG layer emits nothing.  Every spore mat here
        is written to the fg (see SPORE), which is why it is a character rather
        than a kit role.
      - runs are capped at MAX_POOLS 16 per screen.  This level's worst screen
        draws five.

  * LIGHT IS NOT OCCLUDED.  The pools are additive quads over the whole view;
    rock does not stop them.  A spore mat sealed behind a wall therefore
    already glows through it, and **breaking a wall can never add light to a
    room** -- it can only remove an emissive tile.  That is the opposite of the
    obvious reading of this level's title, and it is load-bearing: see THE
    LANTERN BLOCK.

  * AND 0.86 IS TOO DARK FOR THIS PALETTE.  The shade is alpha-blended over the
    tiles and the pools are ADDITIVE over the shade, so a pool brightens rock
    and the air beside it by the same number: it raises the floor, it does not
    raise the contrast.  At the 0.86 data/fx.json calls the common case, a
    solid tile and the void next to it are both 14% of themselves and the first
    capture run could not see a spore vent from the tile in front of it, with
    the lantern ON it.  The entry this level asks for is 0.74, which is still
    the darkest in the game, and the argument is measured rather than tasteful
    -- the A/B is three captures at 0.62 / 0.72 / 0.82 of the same two rooms.
    The other half of the same fix is in `dressing`: a corridor backed by
    `deep_void` gives an additive pool nothing to land on at all.

THE SHAPE OF THE LEVEL
----------------------
50x30, two screens by two, as docs/plan-20-levels.md fixes: the vertical seam is
between cols 24 and 25, the horizontal one between rows 14 and 15.  Carved out
of solid rock rather than built, so the prover's frontier stays inside the
tunnels.

  THE VENT WALK (rows 24-27, stand row 27, cols 1-45).  Kaya on foot, west to
        east, over three lit stations and two dark crossings with a spore vent
        in each.  The seam at cols 24/25 is crossed on flat floor in the light
        of the second station -- nothing in this level jumps across a seam.

  THE ROOT CHIMNEY (cols 41-45, rows 15-23).  Three chitin shelves three rows
        apart: the frog's climb, and the only one it can make.  Each rung
        carries its own spore mat, so the climb is lit rung by rung and the
        dark between them is the whole of the shaft.

  THE ROOT (col 44, rows 8-18).  A hanging root across the horizontal screen
        seam.  `data/forms/frog.json` sets `can_climb: false`, so this is
        Kaya's, and `pad_human` sits on the top rung: the frog gets you up the
        shelves, the woman gets you up the root.  A ladder rather than more
        shelves because the seam is at rows 14/15 and a HOP across a seam flips
        the camera in mid-air -- the one thing this project has shipped twice.

  THE HIGH GALLERY (rows 5-8, stand row 8, cols 2-44).  Walked back west, and
        the exam: two more vents, the lantern block, and the vault above it.

  THE VAULT (cols 21-23, rows 2-4) behind `deep_glowwall` at col 20.  270
        declares no break_hold, so only the blade opens it -- and the frog has
        `can_attack: false`.  A woman-only room, reached only from the top of
        the lantern block, and the only place in the level that is not on the
        route.

WHY NOTHING THE ROUTE NEEDS IS BEHIND A BREAKABLE
-------------------------------------------------
`ProverSearch.action_set()` is eighteen actions -- {left, none, right} x {jump,
no jump} x {none, up, down}.  There is no ATTACK bit, so the prover never
presses attack, `FormBase.tick_break` never runs, and a breakable tile is a
wall to it.  Measured on this branch, a two-tile `termite_wall` plug across an
otherwise empty corridor: FAIL, closest approach 118.0 px, the whole budget
spent.  `tools/reachability.py` agrees for its own reason -- it reads the flags
and `breakable` tiles are `solid` -- so a level that hides a `MUST_REACH`
entity behind a wall fails validate.sh as well.

So in World 4 a breakable wall can never gate anything mandatory, and this
level does not pretend otherwise.  What it does instead is make breaking a
*choice with a price*, which is what the tile art has said all along
(tools/art/tiles.py:t_luminous_wall -- "the only light in a dark room, so
breaking it is a choice, not a freebie"):

  THE LANTERN BLOCK (cols 15-16, rows 7-8).  Two tiles of `luminous_wall` on
        the gallery floor, the only light for eight tiles either side, and the
        route goes OVER it: a two-tile step, which is the human's measured
        rise, and the prover climbs it.  Standing on its top is also the only
        way up to the vault ledge.  You may instead shoulder through it --
        break_hold 0.4, 25 ticks a tile -- and what that buys you is a flat
        walk, and what it costs is the lamp: cols 13-18 go dark, the take-off
        for the last vent goes dark with them, and the vault becomes
        unreachable because the step you would have climbed is gone.  The blade
        shatters a BREAKABLE on contact, so it is also possible to put out the
        light by accident.

  THE SPORE VAULT is the other half of the same sentence, from the other side:
        its mat glows *through* the glowwall that seals it (light is not
        occluded), so the vault advertises itself as a violet haze around a
        cracked wall long before you can open it.  Breaking that wall does not
        move the light one pixel -- it moves YOU into it.

THE POOL-TO-POOL RULE, AS ARITHMETIC
------------------------------------
Every vent crossing has to be honest: you can see the far shore before you
commit, and the tile you cross is not lit.  That is checkable rather than
felt, so `check()` checks it -- POOLS gives each mat's lozenge in pixels by
`AmbienceLayer`'s own formula, and every entry in CROSSINGS asserts that its
landing tile is inside a lozenge and that at least one of its vent tiles is
inside none.  A mat moved two tiles in "dressing" fails the build.

ADR 004 -- NO TRANSFORM STRANDS YOU
-----------------------------------
  * THE WOMAN cannot leave the vent walk: the chimney's first shelf is three
    rows up and her measured rise is two.  `pad_frog` is on that floor.
  * THE FROG cannot leave the chimney: it cannot climb (`can_climb: false`),
    so the root is not a way out for it, and anything it falls off lands back
    on the vent walk with `pad_frog` on it.  `pad_human` is on the top shelf.
  * THE WOMAN in the high gallery can always fall back down the root shaft to
    the top shelf -- she climbs, so she can also come back up -- and off the
    shelf to the vent walk, where `pad_frog` is.  The loop closes in every
    direction.
  * `check()` floods both walking forms with `reachable_set` to keep that
    honest, including the negatives.  Note the one place the flood is more
    generous than the game: it lets ANY form climb a ladder, because it reads
    the tile and not `can_climb`.  The frog's real domain is therefore smaller
    than the flood says, which only makes the strand argument stronger.

THE PALETTE
-----------
`Palette.char()` resolves a tile NAME through the flat, jungle-derived `legend`
key of data/level_legend.json, so TERMITE DEEPS's own names (deep_earth,
deep_shelf, ...) have no character there and fall through to UNDERSTUDY --
which lands `solid` on 's' (deep_packed, the *second* solid) and `bg` on 'r'
(deep_fungus, which is the one tile in this world that must never be drawn by
accident).  ADR 002's amendment says a character means whatever the level's
world says it means, so this palette is declared in terms of the jungle tile
whose character IS the deeps role character: `grass_top` for '#', `bg_leaves`
for 'L', and so on.  `Palette.missing()` is empty, `audit(strict_verbs=True)`
is clean, and the level serialises `"tileset": "deeps"`, so the game paints
deep_earth and deep_shelf.  The three breakables are `shared` characters and
are the real tiles either way.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                      # noqa: E402
from world_kit import Kit, Palette, reachable_set       # noqa: E402

LEVEL_ID = "deeps_4"
LEVEL_NAME = "SPORE LIGHT"
W, H = 50, 30

## Roles -> the jungle tile whose legend character is the deeps role character.
## See THE PALETTE in the module docstring: this is a character map, not an art
## claim, and the art comes from `"tileset": "deeps"` at load time.
DEEPS_W4 = Palette("termite_deeps", {
    "bg": "bg_leaves",            # 'L' -> deep_comb
    "solid": "grass_top",         # '#' -> deep_earth
    "solid_alt": "stone_mossy",   # 'S' -> deep_crust
    "packed": "dirt",             # 'd' -> deep_chitin
    "block": "stone",             # 's' -> deep_packed
    "oneway": "wood_platform",    # '=' -> deep_shelf
    "ladder": "vine",             # '|' -> deep_ladder
    "hazard": "spikes",           # '^' -> deep_spore
    "water": "water",             # 'w'  shared, unused
    "water_top": "water_top",     # '~'  shared, unused
    "decor": "tree_trunk",        # 'T' -> deep_root
    "void": "bg_dark",            # 'X' -> deep_void
    "breakable": "crate",         # 'c' -> deep_glowwall: blade only, no
                                  #        break_hold, so the frog cannot open it
    "glowwall": "luminous_wall",  # 'O'  shared, break_hold 0.4: any form
    "shoulder": "termite_wall",   # 'm'  shared, break_hold 0.45
    "rubble": "rubble",           # 'o'  shared, break_hold 0.18
})

## 'r' is deep_fungus: the luminous mat, background art with no collision and no
## kit role -- ROLES has `decor` and `void` and nothing for "a glowing crust on
## the floor". Written as a character for the same reason heights_4 writes its
## cloud field that way, and written to the **fg layer**, which is the part that
## matters: `AmbienceLayer._collect_emissive` reads `world.get_fg()` and nothing
## else, so the identical tile in the bg layer is a picture of a light rather
## than a light. The character is in the deeps tileset, so
## Grid._check_characters accepts it and the game paints tile 269.
SPORE = "r"

## What data/ambience.json is asked for, and the only two numbers in this file
## that live in another agent's file. They are here because the geometry is
## drawn to them -- see THE POOL-TO-POOL RULE.
FUNGUS_RADIUS = 36.0          # emissive.269.radius
LAMP_RADIUS = 30.0            # emissive.214.radius
TS = 16


def spore(k, x, y, w):
    """A mat of deep_fungus on the fg layer: one merged pool, `w` tiles wide."""
    k.g.rect(x, y, w, 1, SPORE)
    return (x, y, w)


def lozenge(x, y, w, radius):
    """The pool `AmbienceLayer._add_run` would draw over this run, in pixels.

    Copied arithmetic, deliberately: half-extents are (radius + (x1-x0)*8,
    radius) around the run's centre. If that function changes, this file's
    self-checks are what should notice.
    """
    x0, x1 = x, x + w - 1
    cx = (float(x0 + x1) * 0.5 + 0.5) * TS
    cy = (float(y) + 0.5) * TS - 4.0
    half_x = radius + float(x1 - x0) * TS * 0.5
    return (cx - half_x, cx + half_x, cy - radius, cy + radius)


# =========================================================================
# The level.
# =========================================================================

def deeps_4():
    g = Grid(W, H, tileset="deeps")
    k = Kit(g, DEEPS_W4, form="human")

    # ------------------------------------------------------------- the rock
    # Carved, not built. A tunnel cut out of a solid block keeps the prover's
    # frontier inside the tunnel instead of wandering an open room, which is
    # what `fill_solid` exists for.
    k.fill_bg("bg")
    k.fill_solid("packed")
    k.shell(1, "solid")

    # ================================================== THE VENT WALK (rows 24-27)
    # Four tiles of air over a capped floor. Four and not three because a
    # three-tile corridor leaves 26 px over a 22 px body, and a jump that bonks
    # at 26 px carries about two and a half tiles -- which is not enough for the
    # three-tile vents below. Head room is what makes a gap jumpable.
    k.corridor(1, 27, 45, h=4)
    k.floor(1, 28, 45, depth=1)
    # THE ROOF LIFTS OVER EACH VENT, and that is arithmetic rather than shape.
    # A body standing on row 27 has its top at y=426 and a four-tile corridor
    # puts the rock at y=384: 42 px of head room against a jump apex of
    # 260^2/(2*760) = 44.5 px. She bonks, the bonk costs a third of the airtime,
    # and a three-tile vent then lands her ON the vent. Measured: hop 7 spent
    # all 50,000 expansions and got 0.7 px from the far lip, in mid-air, because
    # every landing that touched the hazard was pruned. One more row of air is
    # 58 px of head room, no bonk, and the full 73 px of reach.
    k.clear_rect(10, 23, 9, 1)            # over VENT A, cols 10-18
    k.clear_rect(27, 23, 10, 1)           # over VENT B, cols 27-36

    spore(k, 3, 27, 6)                    # POOL 1, THE SPORE MOUTH: cols 3-8,
                                          # lighting cols 1-10
    k.rect(13, 27, 2, 1, "hazard")        # VENT A, two tiles: the teacher
    spore(k, 18, 27, 4)                   # POOL 2: cols 18-21, lighting 16-23
    # THE LOW HINGE, laid ACROSS the vertical seam on purpose. A run is
    # collected per screen, so a mat that stops at col 24 lights nothing at all
    # on the far side of the flip: this one is two tiles of light on each screen
    # and the camera changes inside it.
    spore(k, 23, 27, 4)                   # cols 23-26
    k.rect(30, 27, 3, 1, "hazard")        # VENT B, three: the ceiling of her reach
    spore(k, 35, 27, 6)                   # POOL 3, THE CHIMNEY FOOT: cols 35-40

    # ============================================ THE ROOT CHIMNEY (rows 15-23)
    # Cut above the east end of the walk, so the shaft and the walk are one body
    # of air: anything that falls off a shelf lands on the floor with `pad_frog`
    # on it, which is the whole of the frog's half of ADR 004.
    k.clear_rect(41, 15, 5, 9)
    k.ledge(41, 25, 3, stand_form="frog")     # RUNG 1 -> stand 24
    k.ledge(43, 22, 3, stand_form="frog")     # RUNG 2 -> stand 21
    k.ledge(41, 19, 3, stand_form="frog")     # RUNG 3 -> stand 18
    spore(k, 41, 24, 3)                   # POOL 4a, on rung 1
    spore(k, 43, 21, 2)                   # POOL 4b, on rung 2 -- two tiles, not
                                          # three: col 45 is the shoulder plug
    spore(k, 41, 18, 3)                   # POOL 4c, on rung 3, under pad_human

    # THE SHOULDER POCKET, off the second rung and off the route: a plug of
    # termite_wall with two gems behind it. `breakable_wall` claims a standable
    # tile on both sides at row 21, which is what stops a wall being a thing you
    # can only hit from mid-air.
    k.clear_rect(46, 20, 2, 2)
    k.rect(46, 22, 2, 1, "solid")
    k.breakable_wall(45, 21, 2, role="shoulder", form="frog")

    # ============================================= THE HIGH GALLERY (rows 5-8)
    # Carved in three pieces, because the middle one has the vault's floor over
    # it. Carving it as one corridor and drawing the vault floor afterwards is
    # the draw-order bug audit() exists for: the corridor's own claim would say
    # four tiles of air where there are three.
    # The column the block is climbed from (col 17) is deliberately NOT under
    # the vault's floor: a body rises in its own column before it crosses, so a
    # lid two tiles over the take-off makes the step onto the block impossible.
    # The first draft had the ledge starting at col 20, one tile too far west,
    # and check() reported the whole west half of the gallery unreachable.
    k.corridor(2, 8, 16, h=4)             # cols 2-17,  rows 5-8
    k.corridor(18, 8, 6, h=3)             # cols 18-23, rows 6-8, under the vault
    k.corridor(24, 8, 21, h=4)            # cols 24-44, rows 5-8
    k.rect(2, 9, 42, 1, "solid")          # the gallery floor, cols 2-43. Col 44
                                          # is left rock for the root to punch.
    k.rect(18, 5, 6, 1, "solid")          # the vault ledge's floor -> stand 4

    k.clear_rect(7, 4, 8, 1)              # the roof lifts over VENT D, cols 7-14
    k.clear_rect(28, 4, 9, 1)             # and over VENT C, cols 28-36. Same
                                          # 42-px-against-44.5 arithmetic as the
                                          # vent walk; it stops at col 24 so the
                                          # vault keeps its floor and its wall.
    k.rect(10, 8, 3, 1, "hazard")         # VENT D, the last crossing
    k.rect(31, 8, 3, 1, "hazard")         # VENT C
    spore(k, 2, 8, 6)                     # POOL 7, THE LAST LIGHT: cols 2-7
    spore(k, 23, 8, 6)                    # POOL 5, THE HIGH HINGE: cols 23-28,
                                          # laid across the vertical seam so the
                                          # camera flip happens inside one light
    spore(k, 36, 8, 7)                    # POOL 6, THE ROOT TOP: cols 36-42

    # THE VAULT AND ITS LEDGE. Carved above the gallery: rows 3-4 from over the
    # lantern block east to the level's mid-line, with the vault itself one row
    # taller so the tick has somewhere to hang.
    k.clear_rect(15, 3, 9, 2)             # cols 15-23, rows 3-4
    k.clear_rect(21, 2, 3, 1)             # the vault's extra head room
    k.breakable_wall(20, 4, 2, role="breakable")
    spore(k, 21, 4, 3)                    # POOL 8, and the reason the vault
                                          # glows through its own wall

    # THE LANTERN BLOCK. Drawn last of the gallery's solids so that the claims
    # it releases are the ones the corridor filed.
    k.glow_wall(15, 8, 2, thickness=2)

    # THE ROOT. Drawn after the gallery, which would otherwise carve its top two
    # tiles away, and after the chimney, whose air it hangs in.
    k.climb(44, 8, 18, landing="left")

    # ---------------------------------------------------------------- dressing
    # Background only: nothing here has collision or carries a claim. It is
    # still the second most important block in the file, and it was written
    # after reading the captures rather than before.
    #
    # THE TUNNELS KEEP THE COMB BEHIND THEM, and that is a legibility fix rather
    # than a mood. The first draft backed every corridor with `deep_void`, which
    # is the right tile for a hole and the wrong one for a room: under a 0.86
    # shade quad a black backdrop has nothing for an additive pool to land on,
    # so the first capture run was a level in which the spore vents were
    # invisible from the tile in front of them -- with the lantern ON them. The
    # comb is dark and it is not black, and that difference is the whole of what
    # a light in this level has to work with.
    #
    # `fill_bg` has already laid the comb everywhere, so the tunnels need
    # nothing. What gets the void is what is genuinely deep: the chimney, which
    # is a shaft through the warren rather than a gallery in it.
    g.rect(42, 15, 3, 8, "X", "bg")
    # Great roots against the rock, where a face is tall enough to show one.
    for x in (6, 20, 34):
        g.rect(x, 24, 1, 3, "T", "bg")
    for x in (7, 27, 40):
        g.rect(x, 5, 1, 3, "T", "bg")

    # -------------------------------------------------------------- entities
    g.ent("player_spawn", 3, 27)
    g.ent("pad_frog", 38, 27)             # in POOL 3, at the chimney's foot
    g.ent("pad_human", 41, 18)            # on the top rung, in POOL 4c
    g.ent("exit", 4, 8)                   # in POOL 7

    # Three, and where they are NOT is the design. tools/itest.sh replays the
    # proof tape in the real game, with enemies, and the prover's simulation has
    # none: a patrol parked on the proved line is a knockback the tape cannot
    # absorb. Two are behind walls the tape never opens. The tick is the one on
    # the route, and it is on the route the way a dropper is supposed to be: it
    # hangs in the lantern's own light, it is triggered from the tile BELOW it,
    # and `wind_up` 0.45 s against her 108 px/s means it lands on the floor she
    # has left. Put out the lamp and it is invisible, which is the level's whole
    # argument in one enemy.
    g.ent("enemy_dropper", 17, 5)
    g.ent("enemy_walker", 46, 21)         # in the shoulder pocket, on the gems
    # The vault's guard hangs from its ceiling rather than patrolling its floor.
    # A walker here chases at 54 px/s from 96 px away, which means it comes
    # THROUGH the doorway the instant the wall opens: the capture run measured
    # it as a knockback that threw Kaya off the ledge before the shot. A tick is
    # triggered by the tile under it, so the room can be looked into from the
    # door and is only defended once you are inside it.
    g.ent("enemy_dropper", 22, 2)         # in the vault, over the heart

    for (x, y) in [(5, 27), (8, 27), (19, 27), (24, 27), (36, 27), (39, 27),
                   (42, 24), (44, 21), (42, 18), (46, 21), (47, 21),
                   (5, 8), (7, 8), (24, 8), (27, 8), (38, 8), (41, 8),
                   (16, 6), (21, 4)]:
        g.ent("gem", x, y)
    g.ent("heart", 20, 27)                # in POOL 2, before the three-tile vent
    g.ent("heart", 23, 4)                 # in the vault, behind the glowwall

    # --------------------------------------------------- the route (ADR 005)
    # One pad of each kind, so each names a waypoint on its own -- and a pad
    # waypoint is only satisfied once the form has actually changed
    # (`ProverSim.waypoint_satisfied`), which is a stronger promise than a mark
    # on the pad's tile.
    #
    # Hops are short and each contains at most one jump, for the reason ADR 005
    # gives: a hop that needs a big budget is a hop that is too coarse. The two
    # exceptions are the root, which is one continuous climb because a seam at a
    # ladder makes the prover reject its own tape (world_kit.proof_tunnel_seam),
    # and the two seam crossings, which are flat walks.
    # A mark ON the landing tile is a needle. The prover is greedy on manhattan
    # distance, so a goal sitting exactly where the arc first touches down makes
    # every overshoot look like a step backwards -- and the only states nearer
    # the goal are the mid-air ones over the vent, which is where hop 7 spent
    # 50,000 expansions. Each of these sits two tiles PAST the far lip, so
    # landing anywhere on the far shore is progress.
    k.mark("lamp_1", 9, 27)
    k.mark("ledge_a", 12, 27)
    k.mark("past_a", 17, 27)
    k.mark("lamp_2", 20, 27)
    k.mark("seam_low", 25, 27)
    k.mark("ledge_b", 29, 27)
    k.mark("past_b", 35, 27)
    k.mark("chim_foot", 41, 27)
    k.mark("rung_1", 42, 24, form="frog")
    k.mark("rung_2", 44, 21, form="frog")
    k.mark("rung_3", 43, 18, form="frog")
    k.mark("root_top", 43, 8)
    k.mark("lamp_6", 38, 8)
    k.mark("ledge_c", 34, 8)
    k.mark("past_c", 28, 8)
    k.mark("seam_high", 24, 8)
    k.mark("block_e", 17, 8)
    k.mark("block_top", 16, 6)
    k.mark("ledge_d", 13, 8)
    k.mark("past_d", 7, 8)

    g.route("spawn", "lamp_1", form="human")
    g.route("lamp_1", "ledge_a", form="human")
    g.route("ledge_a", "past_a", form="human")
    g.route("past_a", "lamp_2", form="human")
    g.route("lamp_2", "seam_low", form="human")
    g.route("seam_low", "ledge_b", form="human")
    g.route("ledge_b", "past_b", form="human")
    g.route("past_b", "pad_frog", form="human")
    g.route("pad_frog", "chim_foot", form="frog")
    g.route("chim_foot", "rung_1", form="frog")
    g.route("rung_1", "rung_2", form="frog")
    g.route("rung_2", "rung_3", form="frog")
    g.route("rung_3", "pad_human", form="frog")
    g.route("pad_human", "root_top", form="human")
    g.route("root_top", "lamp_6", form="human")
    g.route("lamp_6", "ledge_c", form="human")
    g.route("ledge_c", "past_c", form="human")
    g.route("past_c", "seam_high", form="human")
    g.route("seam_high", "block_e", form="human")
    g.route("block_e", "block_top", form="human")
    g.route("block_top", "ledge_d", form="human")
    g.route("ledge_d", "past_d", form="human")
    g.route("past_d", "exit", form="human")

    return g, k


# =========================================================================
# What the kit cannot check, encoded so it fails the build instead of the
# playtest.
# =========================================================================

## Every emissive run in the level: (x, y, w, radius).
## The radii are the ones the ambience entry in the report asks for, and the
## geometry above is drawn to them.
POOLS = [
    (3, 27, 6, FUNGUS_RADIUS), (18, 27, 4, FUNGUS_RADIUS),
    (23, 27, 4, FUNGUS_RADIUS), (35, 27, 6, FUNGUS_RADIUS),
    (41, 24, 3, FUNGUS_RADIUS), (43, 21, 2, FUNGUS_RADIUS),
    (41, 18, 3, FUNGUS_RADIUS),
    (2, 8, 6, FUNGUS_RADIUS), (23, 8, 6, FUNGUS_RADIUS),
    (36, 8, 7, FUNGUS_RADIUS), (21, 4, 3, FUNGUS_RADIUS),
    # The lantern block is two tiles wide and two rows tall, and a run is per
    # ROW, so it is two pools and not one.
    (15, 7, 2, LAMP_RADIUS), (15, 8, 2, LAMP_RADIUS),
]

## (name, vent tiles, take-off tile, landing tile). Each one asserts the level's
## whole promise about darkness, and the two halves of it are different claims:
## the vent tiles are genuinely UNLIT -- no pool touches them at all -- and both
## shores are within LANTERN_TILES of a lit tile, so you can never be asked to
## jump at something you have no light to see.
CROSSINGS = [
    ("vent A", [(13, 27), (14, 27)], (12, 27), (15, 27)),
    ("vent B", [(30, 27), (31, 27), (32, 27)], (29, 27), (33, 27)),
    ("vent C", [(31, 8), (32, 8), (33, 8)], (34, 8), (30, 8)),
    ("vent D", [(10, 8), (11, 8), (12, 8)], (13, 8), (9, 8)),
]

## data/fx.json darkness.radius 74 px, in tiles, rounded down. What the body
## carries with it, and therefore how far ahead of herself a player can see when
## the level gives her nothing.
LANTERN_TILES = 4

## ADR 004 as floods rather than assertions. `reachable_set` refuses the bird
## and the fish; both of this level's forms walk, which is exactly where the
## risk is.  (label, form, from, must reach, must NOT reach)
RECOVERY = [
    ("the spawn can always walk back to pad_frog",
     "human", (3, 27), (38, 27), None),
    ("and cannot climb the chimney's first rung (rise 3 against her 2)",
     "human", (3, 27), None, (42, 24)),
    ("the frog climbs the chimney to pad_human",
     "frog", (38, 27), (41, 18), None),
    ("and anything it falls off drains back to pad_frog",
     "frog", (42, 24), (38, 27), None),
    ("the woman on the top rung reaches the exit",
     "human", (41, 18), (4, 8), None),
    ("and can always get back down to pad_frog from the high gallery",
     "human", (43, 8), (38, 27), None),
]

## Every waypoint the declared route names, in order, with the form that is
## supposed to be standing on it. The check below floods to each of them with
## breakable tiles left SOLID, which is what both the prover and
## tools/reachability.py do -- see WHY NOTHING THE ROUTE NEEDS IS BEHIND A
## BREAKABLE.
ROUTE_LEGS = [
    ("human", (3, 27), [(9, 27), (12, 27), (17, 27), (20, 27), (25, 27),
                        (29, 27), (35, 27), (38, 27)]),
    ("frog", (38, 27), [(41, 27), (42, 24), (44, 21), (43, 18), (41, 18)]),
    ("human", (41, 18), [(43, 8), (38, 8), (34, 8), (28, 8), (24, 8), (17, 8),
                         (16, 6), (13, 8), (7, 8), (4, 8)]),
]

## Tiles that must still be deep_fungus when the grid is finished. A mat drawn
## over by a later helper is a light that silently stops existing, and the level
## is navigated by these.
MATS = [(x, y, w) for (x, y, w, r) in POOLS if r == FUNGUS_RADIUS]

SCREEN_W, SCREEN_H = 25, 15
MAX_POOLS = 16          # AmbienceLayer.MAX_POOLS


def screen_runs():
    """POOLS as AmbienceLayer would actually collect them: per screen.

    `_collect_emissive` scans the tiles inside the CURRENT VIEW, so a run laid
    across the vertical seam is two runs, one on each screen, and a run that
    stops at col 24 emits nothing at all on the screen to its east. That is not
    a detail -- it is why the two hinge mats straddle the seam instead of
    sitting beside it. Returns {(screen_col, screen_row): [(x, y, w, radius)]}.
    """
    out = {}
    for (x, y, w, r) in POOLS:
        col = x
        while col < x + w:
            sc = col // SCREEN_W
            end = min(x + w, (sc + 1) * SCREEN_W)
            out.setdefault((sc, y // SCREEN_H), []).append(
                (col, y, end - col, r))
            col = end
    return out


def _lit(px):
    """Is this tile's centre inside a pool drawn on this tile's own screen?"""
    x, y = px
    cx, cy = (x + 0.5) * TS, (y + 0.5) * TS
    for (mx, my, mw, r) in screen_runs().get((x // SCREEN_W, y // SCREEN_H), []):
        x0, x1, y0, y1 = lozenge(mx, my, mw, r)
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            return True
    return False


def _unlit(px):
    """Does NO pool on this screen touch this tile at all?

    Stricter than `not _lit`: a tile whose edge catches the fringe of a lozenge
    is half in the light, and a 'dark crossing' made of half-lit tiles is not
    one.
    """
    x, y = px
    tx0, tx1, ty0, ty1 = x * TS, (x + 1) * TS, y * TS, (y + 1) * TS
    for (mx, my, mw, r) in screen_runs().get((x // SCREEN_W, y // SCREEN_H), []):
        x0, x1, y0, y1 = lozenge(mx, my, mw, r)
        if x0 < tx1 and x1 > tx0 and y0 < ty1 and y1 > ty0:
            return False
    return True


def _near_light(px, reach=LANTERN_TILES):
    """Is there a lit tile within one carried light of this one, on this row?"""
    x, y = px
    return any(_lit((x + d, y)) for d in range(-reach, reach + 1))


def check(k, verbose=True):
    """Everything that can be said about this level before the prover runs.

    Not proof -- `tools/prove.sh` is.  Five things, in the order they would
    otherwise be discovered: that the light is where the level says it is, that
    the crossings are honestly bracketed, that no screen asks for more pools
    than AmbienceLayer will draw, that the declared route never needs a wall
    broken, and that no transform strands you.
    """
    g = k.g
    problems = []

    # 1. the mats survived the draw order
    for (x, y, w) in MATS:
        for i in range(w):
            if g.fg[y][x + i] != SPORE:
                problems.append(
                    "the mat at (%d,%d) w%d lost tile (%d,%d) -- it is '%s' "
                    "now, so that pool does not exist"
                    % (x, y, w, x + i, y, g.fg[y][x + i]))
    # and the lamp is still a lamp
    for yy in (7, 8):
        for xx in (15, 16):
            if g.fg[yy][xx] != k.ch("glowwall"):
                problems.append("the lantern block lost (%d,%d)" % (xx, yy))

    # 2. every crossing is honest: the vents are unlit, both shores are within
    #    one carried light of something lit, and the tile is a vent at all
    for name, vents, take, land in CROSSINGS:
        for v in vents:
            if g.fg[v[1]][v[0]] != k.ch("hazard"):
                problems.append("%s: (%d,%d) is '%s', not a spore vent"
                                % (name, v[0], v[1], g.fg[v[1]][v[0]]))
            if not _unlit(v):
                problems.append(
                    "%s: the vent at %s is touched by a pool. A crossing lit "
                    "end to end is not a crossing" % (name, (v,)))
        for what, t in (("take-off", take), ("landing", land)):
            if not _near_light(t):
                problems.append(
                    "%s: the %s %s has no lit tile within %d -- that is a jump "
                    "at a shore she has no light to see"
                    % (name, what, (t,), LANTERN_TILES))
        if verbose:
            print("  crossing     %-7s %d dark vent(s);  take-off %s, landing %s"
                  % (name, len(vents),
                     "lit" if _lit(take) else "near light",
                     "lit" if _lit(land) else "near light"))

    # 3. no screen asks AmbienceLayer for more runs than it will draw
    runs = screen_runs()
    for key in sorted(runs):
        if len(runs[key]) > MAX_POOLS:
            problems.append("screen %s asks for %d pools; AmbienceLayer draws "
                            "%d and drops the rest"
                            % (key, len(runs[key]), MAX_POOLS))
        if verbose:
            print("  pools        screen %s  %d run(s)" % (key, len(runs[key])))

    # 4. the declared route never needs a wall broken. `reachable_set` reads the
    #    tile flags, and every breakable in this world is `solid`, so this is the
    #    same blindness the prover and reachability.py have.
    for form, start, legs in ROUTE_LEGS:
        seen = reachable_set(k, start, form=form)
        for leg in legs:
            if leg not in seen:
                problems.append(
                    "route leg %s is not reachable as the %s from %s with "
                    "every breakable left solid (%d tiles reachable)"
                    % (leg, form, start, len(seen)))
        if verbose:
            print("  route        %-5s from %-9s %d legs, %d tiles reachable"
                  % (form, "(%d,%d)" % start, len(legs), len(seen)))

    # 5. ADR 004
    for label, form, start, want, deny in RECOVERY:
        seen = reachable_set(k, start, form=form)
        if want is not None and want not in seen:
            problems.append("%s -- as the %s, %s cannot reach %s (%d tiles). "
                            "That is an ADR 004 strand."
                            % (label, form, start, want, len(seen)))
        if deny is not None and deny in seen:
            problems.append("%s -- as the %s, %s CAN reach %s and must not "
                            "(%d tiles)." % (label, form, start, deny, len(seen)))
        if verbose:
            print("  adr004       %-5s from %-9s %-16s %s"
                  % (form, "(%d,%d)" % start,
                     ("reaches %s" % (want,)) if want else ("denied %s" % (deny,)),
                     label))

    if problems:
        raise SystemExit("deeps_4: %d check(s) failed:\n  %s"
                         % (len(problems), "\n  ".join(problems)))
    return k.audit(strict_verbs=True)


if __name__ == "__main__":
    grid, kit = deeps_4()
    for line in check(kit):
        print(line)
    write(LEVEL_ID, grid, LEVEL_NAME, music="world4")
