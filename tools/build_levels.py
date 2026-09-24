#!/usr/bin/env python3
"""Level definitions. Run via tools/genlevels.sh.

The five jungle levels below are drawn with `Grid` directly, because `Grid`'s
eighteen methods ARE the jungle vocabulary -- `ground`, `vine`, `canopy`,
`trunk`, `crates`.

The four new worlds of docs/plan-20-levels.md need different shapes, and those
live in tools/world_kit.py. A level that uses them wraps its grid in a `Kit`,
draws, and returns BOTH -- the writer below audits the kit before it writes the
JSON, so a helper's promises are checked against the finished grid rather than
against the call that made them:

    from world_kit import Kit, RUINS

    def ruins_1():
        g = Grid(50, 30)
        k = Kit(g, RUINS)
        k.fill_bg()
        k.shell()
        k.flooded_chamber(2, 12, 46, 16, surface=15)
        cols = k.colonnade(8, 5, 8, surface=15, bed=27, mark="col")
        k.bank(44, 15, 4, rise=1)
        g.ent("player_spawn", 3, 11)
        ...
        return g, k          # <- the tuple is what asks for the audit

Two things the kit will not do for you, both on purpose:

* it does not author a route. ADR 005 wants the intended solution written by
  the author, next to the geometry; the helpers return the mark names in
  traversal order so `g.route()` can be chained down them.
* it does not prove anything. `tools/prove.sh` does. The kit's audit is a fast
  filter that catches the class of error that has shipped here six times, and
  its verdict is not evidence -- exactly the standing rule for
  tools/reachability.py.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_levels import Grid, write
from world_kit import Kit


def jungle_1():
    """CANOPY TRAIL — 2x2 screens. Teaches: run, jump, gaps, spikes, vines,
    one-way platforms, and the screen flip in both axes."""
    g = Grid(50, 30)

    # ---------------- background dressing
    g.canopy(0, 0, 50, 3)
    for x in (4, 11, 29, 38, 46):
        g.trunk(x, 3, 27)
    g.canopy(14, 2, 10, 3)
    g.canopy(33, 1, 12, 3)

    # ---------------- screen C (bottom-left): the start
    g.ground(0, 27, 14)
    g.rect(14, 29, 3, 1, "^")     # 3-tile spike pit: one clean jump
    g.ground(17, 27, 7)
    g.platform(9, 24, 4)          # optional high route with a gem ledge
    g.platform(15, 25, 3)
    # solid divider so the only way east is up the vine
    g.rect(24, 14, 1, 16, "s")

    # ---------------- the vine, C -> A
    g.vine(21, 6, 21)             # rows 6..26
    g.mark("vine_foot", 21, 26)   # stand on the east shelf at its base
    g.mark("vine_top", 21, 6)

    # ---------------- screen A (top-left)
    g.ground(17, 7, 4, depth=2)
    g.platform(12, 10, 4)
    g.platform(6, 12, 4)
    g.ground(0, 13, 5, depth=2)
    g.crates(2, 12, 2, vertical=True)

    # ---------------- A -> B along the canopy
    g.platform(23, 6, 4)
    g.mark("branch_a", 24, 5)
    g.platform(30, 8, 4)
    g.mark("branch_lip", 26, 5)     # the east lip of branch_a, where the jump starts
    g.mark("branch_b", 31, 7)
    g.ground(35, 10, 6, depth=2)
    g.mark("branch_c", 37, 9)
    g.platform(42, 8, 3)
    g.mark("branch_d", 43, 7)

    # ---------------- descent shaft B -> D
    g.platform(45, 12, 4)
    g.mark("descent_1", 46, 11)
    g.platform(45, 17, 4)
    g.mark("descent_2", 46, 16)
    g.platform(40, 21, 4)
    g.mark("descent_3", 41, 20)
    g.platform(38, 24, 4)
    g.mark("descent_4", 39, 23)

    # ---------------- screen D (bottom-right): the run to the exit
    g.ground(25, 27, 25)
    g.rect(33, 27, 4, 3, ".")
    g.rect(33, 29, 4, 1, "^")
    g.crates(29, 26, 3)

    # ---------------- inhabitants and loot
    g.ent("player_spawn", 2, 26)
    # screen C
    g.ent("enemy_walker", 8, 26)
    g.ent("enemy_jumper", 20, 26)
    g.ent("gem", 10, 23)
    g.ent("gem", 11, 23)
    g.ent("gem", 16, 24)
    # screen A
    g.ent("enemy_walker", 18, 6, facing="left")
    g.ent("gem", 13, 9)
    g.ent("gem", 14, 9)
    g.ent("heart", 2, 10)
    # screen B
    g.ent("enemy_walker", 37, 9)
    g.ent("gem", 31, 7)
    g.ent("gem", 32, 7)
    g.ent("gem", 43, 7)
    # screen D
    g.ent("enemy_jumper", 41, 26)
    g.ent("enemy_walker", 45, 26)
    g.ent("gem", 30, 25)
    g.ent("gem", 31, 25)
    g.ent("exit", 47, 26)

    # ---------------- the intended solution (ADR 005)
    # One form the whole way. The level is a loop of the four screens: east
    # along the floor, up the vine, east along the canopy, down the shaft.
    g.route("spawn", "vine_foot", form="human")      # run east, clear the spike pit (14-16)
    g.route("vine_foot", "vine_top", form="human")   # 20 tiles of vine, C -> A
    g.route("vine_top", "branch_a", form="human")    # step off the vine eastward
    # Measured in the running game, not reasoned: NO jump from branch_a lands on
    # the platform at cols 30-33. Ten jump lengths from 0 to 30 frames either
    # drop into the gap or sail over it to branch_c, and braking in mid-air with
    # move_left overshoots backwards into the gap every time. That platform is
    # scenery you pass over, so the route no longer claims you stand on it.
    g.route("branch_a", "branch_lip", form="human")   # walk out to the lip
    g.route("branch_lip", "branch_c", form="human")   # one jump, clearing the gap
    g.route("branch_c", "branch_d", form="human")    # A -> B, the screen flip east
    g.route("branch_d", "descent_1", form="human")   # over the lip into the shaft
    g.route("descent_1", "descent_2", form="human")  # drop through the one-way, B -> D
    g.route("descent_2", "descent_3", form="human")  # off the west edge of the shaft
    g.route("descent_3", "descent_4", form="human")
    g.route("descent_4", "exit", form="human")       # land east of the second spike pit
    return g


def hub(doors):
    """THE CANOPY — top-down overworld, 2x1 screens.

    `doors` is a list of dicts: {level, label, requires?, requires_all?, x, y}.
    Regenerate this whenever a level is added."""
    g = Grid(50, 15, ".")
    g.rect(0, 0, 50, 15, "g", "bg")                 # grass everywhere underneath

    # forest border
    g.rect(0, 0, 50, 2, "@")
    g.rect(0, 13, 50, 2, "@")
    g.rect(0, 0, 2, 15, "@")
    g.rect(48, 0, 2, 15, "@")

    # a lake you have to walk around
    g.rect(26, 10, 7, 3, "W")
    g.rect(27, 9, 5, 1, "W")

    # scattered trees to shape the route
    for (x, y, w, h) in [(7, 3, 2, 2), (11, 10, 3, 2), (18, 3, 2, 3), (20, 11, 4, 1),
                         (30, 3, 2, 2), (36, 9, 3, 2), (39, 3, 3, 2), (44, 10, 2, 2)]:
        g.rect(x, y, w, h, "@")

    # the main path, drawn on the background layer (walkable)
    g.rect(3, 7, 44, 2, "p", "bg")
    for (x, y0, y1) in [(5, 6, 8), (14, 4, 8), (23, 8, 10), (33, 4, 8), (43, 7, 10)]:
        lo, hi = min(y0, y1), max(y0, y1)
        g.rect(x, lo, 1, hi - lo + 1, "p", "bg")
        g.rect(x + 1, lo, 1, hi - lo + 1, "p", "bg")

    g.ent("player_spawn", 3, 7)
    for d in doors:
        g.ent("hub_door", d["x"], d["y"], level=d["level"], label=d["label"],
              requires=d.get("requires", ""), requires_all=d.get("requires_all", False))
    return g


def jungle_2():
    """ROOT HOLLOW — 2x2 screens of stone tunnels. Teaches: keys and doors,
    switch blocks, breakable crates, and a one-way descent."""
    g = Grid(50, 30)
    g.rect(0, 0, 50, 30, "r", "bg")                 # rock backdrop throughout

    # ---- outer shell
    g.rect(0, 0, 50, 3, "s")
    g.rect(0, 28, 50, 2, "s")
    g.rect(0, 0, 2, 30, "s")
    g.rect(48, 0, 2, 30, "s")

    # ---- screen C (bottom-left): entry hall and the yellow key
    # Every step up must be <= 2 tiles: the human apex is 2.78 tiles, so a
    # 3-tile rise is physically impossible. tools/reachability.py enforces it.
    g.ground(2, 26, 12, depth=2)
    g.rect(2, 24, 1, 2, "s")
    g.crates(4, 25, 2, vertical=True)   # stand row 23, 2 up from the floor
    g.platform(6, 22, 4)                # stand row 21, 2 up from the crates
    g.platform(10, 20, 4)               # stand row 19, 2 up again
    g.rect(14, 16, 1, 12, "s")                      # wall with a door in it
    g.rect(14, 24, 1, 2, ".")                       # doorway: two tiles, so a
                                                    # 22px character actually fits

    # ---- screen C right half: past the yellow door
    g.ground(15, 26, 9, depth=2)
    g.rect(19, 29, 3, 1, "^")
    g.rect(19, 26, 3, 3, ".")
    g.platform(17, 22, 3)
    g.vine(22, 8, 19)                   # must reach screen A, not stop at its floor
    # The vine punches a notch in the floor at col 22, so its foot is one tile
    # lower than the shelf either side of it.
    g.mark("vine_foot", 22, 26)
    g.mark("vine_top", 22, 8)

    # ---- screen A (top-left): switch puzzle over a drop
    g.ground(2, 14, 6, depth=2)
    g.rect(8, 13, 4, 1, "A")                        # solid while group 1 is ON
    g.rect(12, 10, 4, 1, "a")                       # solid while group 1 is OFF
    g.ground(16, 9, 6, depth=2)          # reaches col 21, flush with the vine
    # Row 13, not 12: the ledge above occupies rows 9-10, so a platform at row
    # 12 left exactly one tile of headroom and could never be stood on. Flush
    # with the vine at col 21 so you step off rather than jumping a gap.
    g.platform(17, 13, 5)
    g.ground(2, 6, 8, depth=2)
    g.crates(9, 5, 2, vertical=True)

    # ---- screen B (top-right): the red key behind switch group 2
    g.ground(25, 9, 8, depth=2)
    g.mark("ruins_ledge", 26, 8)        # where the jump east off the vine lands
    # The critical path must not run over a switch block: group 2 starts OFF, so
    # this 'B' bridge is intangible until you flip switch_b -- which is on the
    # far side of it. The platform below breaks that circular dependency and
    # leaves the switch blocks as an optional shortcut.
    g.platform(33, 7, 4)
    g.rect(33, 8, 4, 1, "B")
    g.ground(37, 6, 6, depth=2)
    g.platform(43, 9, 4)
    g.rect(30, 4, 4, 1, "b")

    # ---- screen D (bottom-right): the exit behind the red door
    g.ground(25, 26, 22, depth=2)
    g.rect(29, 29, 3, 1, "^")
    g.rect(29, 26, 3, 3, ".")
    g.platform(33, 22, 4)
    g.rect(38, 18, 1, 10, "s")
    g.rect(38, 24, 1, 2, ".")                       # the red doorway, two tiles
    g.ground(39, 26, 9, depth=2)
    g.crates(41, 25, 2)

    # ---- inhabitants
    g.ent("player_spawn", 3, 25)
    g.ent("key_yellow", 11, 19)
    g.ent("door_yellow", 14, 25)
    g.ent("switch_a", 18, 8)
    g.ent("switch_b", 40, 5)
    g.ent("key_red", 44, 8)
    g.ent("door_red", 38, 25)
    g.ent("exit", 46, 25)

    g.ent("enemy_walker", 8, 25)
    g.ent("enemy_walker", 17, 25)
    g.ent("enemy_jumper", 26, 25)
    g.ent("enemy_walker", 27, 8)
    g.ent("enemy_jumper", 4, 13)
    g.ent("enemy_walker", 42, 25)

    for (x, y) in [(7, 21), (8, 21), (12, 18), (18, 8), (26, 8), (34, 5),
                   (34, 21), (35, 21), (43, 25), (5, 5), (6, 5)]:
        g.ent("gem", x, y)
    g.ent("heart", 22, 21)

    # ---- the intended solution (ADR 005)
    # Key, door, key, door, with the switch levers taken on the way past rather
    # than as gates -- the switch blocks are deliberately a shortcut, not the
    # critical path, so the route does not stand on one.
    #
    # KNOWN WART, declared as found: the drop from key_red lands at cols 43-46,
    # which is already EAST of door_red at col 38, so the red door can be walked
    # around entirely. The route still goes through it because that is what the
    # level is about; the fix is geometry and geometry is not this task's to
    # change. Expect the prover to pass and a human to notice the door is free.
    g.route("spawn", "key_yellow", form="human")          # crates, then two platforms
    g.route("key_yellow", "door_yellow", form="human")    # back down to the hall floor
    g.route("door_yellow", "vine_foot", form="human")     # east over the spike pit (19-21)
    g.route("vine_foot", "vine_top", form="human")        # 18 tiles of vine, C -> A
    g.route("vine_top", "switch_a", form="human")         # step west onto the ledge
    g.route("switch_a", "ruins_ledge", form="human")      # jump the gap at 22-24, A -> B
    g.route("ruins_ledge", "switch_b", form="human")      # up the platform and the shelf
    g.route("switch_b", "key_red", form="human")          # drop east onto the key ledge
    g.route("key_red", "door_red", form="human")          # one-way fall into screen D
    g.route("door_red", "exit", form="human")
    return g


def jungle_3():
    """THE WATERWAY — 2x2 screens. Kaya takes the fish form to cross a flooded
    channel, then changes back to climb out. Teaches: water, the air meter,
    eight-way swimming."""
    g = Grid(50, 30)
    g.rect(0, 0, 50, 30, "r", "bg")
    g.rect(0, 0, 50, 2, "s")
    g.rect(0, 0, 2, 30, "s")
    g.rect(48, 0, 2, 30, "s")
    g.rect(0, 28, 50, 2, "s")

    # ---- the shore you start on
    g.ground(2, 26, 7, depth=4)
    g.platform(4, 22, 3)

    # ---- the flooded channel: surface row 21, cols 9..43
    for x in range(9, 44):
        g.put(x, 21, "~")
    g.rect(9, 22, 35, 7, "w")

    # ---- things to swim around. Alternating: the first stops short of the
    # bed so you go over it, the second reaches the surface so you go under.
    g.rect(14, 24, 2, 5, "s")
    g.mark("over_one", 18, 23)
    g.rect(21, 21, 2, 6, "s")
    g.mark("under_two", 24, 27)
    g.rect(28, 25, 2, 4, "s")
    g.mark("over_three", 32, 23)
    g.rect(35, 21, 2, 5, "s")
    g.mark("under_four", 38, 27)
    g.rect(40, 26, 2, 3, "s")
    g.mark("bank_foot", 43, 22)         # open water against the far bank

    # ---- the far bank, and the way up
    g.ground(44, 20, 4, depth=10)
    g.ground(38, 8, 10, depth=2)
    # The vine is drawn AFTER the ledge on purpose: written before, the ledge
    # overwrote its top two tiles and left a 3-tile gap nobody could jump.
    g.vine(45, 6, 14)                   # rows 6..19, punches through the ledge

    # Upper traverse, right to left, every step <= 2 tiles and <= 4 across.
    g.platform(35, 9, 3)                # stand 8
    g.platform(33, 11, 4)               # stand 10
    g.platform(20, 13, 4)               # stand 12
    g.ground(25, 13, 6, depth=2)        # stand 12
    g.platform(14, 13, 4)               # stand 12
    g.ground(2, 12, 10, depth=2)        # stand 11
    g.platform(12, 10, 4)               # stand 9
    g.platform(17, 8, 4)                # stand 7
    g.platform(12, 6, 4)                # stand 5
    g.ground(2, 5, 8, depth=2)          # stand 4 — the cyan key sits here

    g.ent("player_spawn", 3, 25)
    g.ent("pad_fish", 7, 25)
    g.ent("pad_human", 45, 19)
    g.ent("exit", 46, 7)

    g.ent("enemy_walker", 4, 11)
    g.ent("enemy_jumper", 27, 12)
    g.ent("enemy_walker", 40, 7)
    for (x, y) in [(11, 24), (12, 24), (18, 26), (19, 26), (25, 23), (26, 23),
                   (32, 27), (33, 27), (38, 24), (39, 24), (5, 21), (14, 6),
                   (15, 6), (21, 9), (34, 10), (4, 4)]:
        g.ent("gem", x, y)
    g.ent("heart", 26, 12)
    g.ent("key_cyan", 3, 4)
    g.ent("door_cyan", 44, 8)

    # ---- the intended solution (ADR 005)
    # One fish crossing, weaving over and under the five pillars, then human
    # again for the vine. The hop out of the water onto the far bank at
    # bank_foot -> pad_human is the 16px bank that defect 4 died on, so it is a
    # hop of its own and not folded into the swim.
    #
    # KNOWN WART, declared as found: key_cyan and door_cyan are NOT on this
    # route, because the vine surfaces at col 45 and the door is at col 44 --
    # east of the door is the exit, so the exit needs no key and the whole
    # upper-left traverse is optional. Routing through the key would mean
    # declaring a hop that crosses a shut door to fetch the key that opens it,
    # which is not a solution. Flagged for a geometry fix, not fixed here.
    g.route("spawn", "pad_fish", form="human")            # two steps along the shore
    g.route("pad_fish", "over_one", form="fish")          # in, and over the first pillar
    g.route("over_one", "under_two", form="fish")         # under 21-22, which breaks surface
    g.route("under_two", "over_three", form="fish")       # over 28-29, which sits on the bed
    g.route("over_three", "under_four", form="fish")      # under 35-36
    g.route("under_four", "bank_foot", form="fish")       # over 40-41, to the far wall
    g.route("bank_foot", "pad_human", form="fish")        # surface and hop the 16px bank
    g.route("pad_human", "exit", form="human")            # 12 tiles of vine, through the ledge
    return g


def jungle_4():
    """SKY BRANCH — 2x2 screens. Frog first (huge jumps, wall cling) up a shaft,
    then bird (flap on a stamina budget) across the canopy."""
    g = Grid(50, 30)
    g.canopy(0, 0, 50, 2)
    for x in (9, 24, 35, 46):
        g.trunk(x, 2, 28)

    g.rect(0, 28, 50, 2, "d")
    g.rect(0, 0, 1, 30, "s")
    g.rect(49, 0, 1, 30, "s")

    # ---- ground floor: you arrive human
    g.ground(1, 26, 11)
    g.rect(12, 29, 3, 1, "^")
    g.ground(15, 26, 4)

    # ---- the frog shaft: two walls to bounce between
    # The left wall stops two tiles above the floor so you can WALK into the
    # shaft. It used to run to the floor, which sealed the spawn and the frog
    # pad in a box with no way out -- the whole level after it was unreachable.
    g.rect(11, 8, 1, 16, "s")           # rows 8-23, floor level left open
    g.rect(18, 8, 1, 18, "s")           # rows 8-25; the roof covers row 18,7
    g.ground(12, 26, 6)
    g.mark("shaft_foot", 16, 25)        # walk in under the left wall's lip
    # Frog apex is 5.16 tiles, but that is a jump held to full height. Release
    # the button early and jump_cut halves what is left, which tops out around
    # 4.37 tiles -- so a 4-tile step leaves six pixels of margin and lands or
    # misses depending on rounding. Measured in the running game: some 4-tile
    # rungs caught, others dropped you to the bottom of the shaft. The climb is
    # 3-tile steps now, which a cut jump clears with a tile to spare.
    #
    # A chimney also needs a MOUTH. This one used to be capped across its full
    # width at row 7: you climbed the whole shaft and hit a lid, with the bird
    # pad, the human pad and the exit all on the far side of it. Cols 12-14 are
    # open sky now and the climb ends underneath them, so you come out on the
    # roof and walk to the pad.
    g.platform(15, 23, 3)               # stand 22
    g.mark("rung_1", 16, 22)
    g.platform(12, 20, 3)               # stand 19
    g.mark("rung_2", 13, 19)
    g.platform(15, 17, 3)               # stand 16
    g.mark("rung_3", 16, 16)
    g.platform(12, 14, 3)               # stand 13
    g.mark("rung_4", 13, 13)
    g.platform(15, 11, 3)               # stand 10
    g.mark("rung_5", 16, 10)
    g.platform(12, 9, 3)                # stand 8, right under the mouth
    g.mark("rung_6", 13, 8)
    g.ground(15, 7, 4, depth=1)         # the roof, cols 15-18: stand 6
    g.mark("roof", 17, 6)               # out through the mouth and east

    # ---- the bird crossing: perches only, a long way apart
    g.ground(19, 7, 3, depth=1)
    g.platform(25, 5, 3)
    g.mark("perch_1", 26, 4)
    g.platform(31, 9, 3)
    g.mark("perch_2", 32, 8)
    g.platform(37, 4, 3)
    g.mark("perch_3", 38, 3)            # 5 up and 6 across: the stamina test
    g.ground(41, 8, 7, depth=2)

    # ---- and a soft landing back on solid ground
    g.ground(41, 26, 7)
    g.vine(44, 7, 19)                   # through the ledge, so the climb
                                        # ends level with somewhere to stand
    g.mark("vine_foot", 44, 25)         # named because the way down is WEST of
                                        # the exit: without it a distance-driven
                                        # search has no reason to leave the pad
    g.platform(20, 16, 3)
    g.platform(26, 19, 3)
    g.platform(33, 22, 3)
    g.ground(36, 26, 5)

    g.ent("player_spawn", 2, 25)
    g.ent("pad_frog", 8, 25)
    g.ent("pad_bird", 20, 6)
    g.ent("pad_human", 45, 7)
    g.ent("exit", 46, 25)

    g.ent("enemy_jumper", 5, 25)
    g.ent("enemy_walker", 16, 25)
    g.ent("enemy_walker", 43, 7)
    g.ent("enemy_jumper", 38, 25)
    for (x, y) in [(16, 21), (13, 12), (16, 10), (26, 4), (32, 8), (38, 3),
                   (21, 15), (27, 18), (34, 21), (43, 25), (44, 25), (4, 25)]:
        g.ent("gem", x, y)
    g.ent("heart", 42, 7)

    # ---- the intended solution (ADR 005)
    # Arrive human, take the frog pad, climb the shaft in 3-tile steps, leave
    # through the mouth at cols 12-14 onto the roof, take the bird pad, cross
    # the canopy, take the human pad, and climb down the vine to the exit.
    # Every rung is its own hop, because the 3-tile step IS the level -- a 4th
    # tile on any of them is the bug that dropped the player back to the floor.
    g.route("spawn", "pad_frog", form="human")
    g.route("pad_frog", "shaft_foot", form="frog")        # east along the floor, into the shaft
    g.route("shaft_foot", "rung_1", form="frog")
    g.route("rung_1", "rung_2", form="frog")
    g.route("rung_2", "rung_3", form="frog")
    g.route("rung_3", "rung_4", form="frog")
    g.route("rung_4", "rung_5", form="frog")
    g.route("rung_5", "rung_6", form="frog")
    g.route("rung_6", "roof", form="frog")                # up through the mouth (12-14, row 7)
    g.route("roof", "pad_bird", form="frog")              # walk east along the roof
    g.route("pad_bird", "perch_1", form="bird")
    g.route("perch_1", "perch_2", form="bird")
    g.route("perch_2", "perch_3", form="bird")
    g.route("perch_3", "pad_human", form="bird")
    g.route("pad_human", "vine_foot", form="human")       # step west onto the vine, descend
    g.route("vine_foot", "exit", form="human")
    return g


def jungle_5():
    """HEART OF THE GROVE — 2x2 screens ending in the Grove Warden's arena.
    The drop into the arena is one-way on purpose: the camera locks there."""
    g = Grid(50, 30)
    g.canopy(0, 0, 50, 2)
    for x in (6, 19, 30, 44):
        g.trunk(x, 2, 28)
    g.rect(0, 0, 1, 30, "s")
    g.rect(49, 0, 1, 30, "s")
    g.rect(0, 28, 50, 2, "s")

    # ---- screen C: the approach, with a pool and rooted blooms
    g.ground(1, 26, 8)
    for x in range(9, 17):
        g.put(x, 24, "~")
    g.rect(9, 25, 8, 3, "w")
    g.ground(17, 26, 7)
    g.platform(11, 20, 4)
    g.platform(4, 21, 4)
    g.mark("vine_foot", 21, 26)         # the vine notches the shelf at col 21

    # ---- screen A: the canopy walk east
    g.ground(1, 14, 7, depth=2)
    g.platform(9, 12, 4)
    g.ground(14, 10, 9, depth=2)
    g.mark("canopy_ledge", 19, 9)       # where the vine lets you off, C -> A
    g.platform(6, 7, 4)
    g.ground(1, 5, 4, depth=2)

    # ---- screen B: the ledge you jump from
    g.ground(25, 10, 8, depth=2)
    g.mark("east_ledge", 26, 9)         # across the gap at 23-24, A -> B
    g.platform(34, 8, 4)
    g.mark("branch", 35, 7)
    g.ground(39, 6, 9, depth=2)
    g.mark("ledge_b", 41, 5)            # the lip you step off, B -> D

    # ---- screen D: the arena. Sealed on both sides, flat floor.
    g.rect(25, 15, 1, 13, "s")      # down to the floor: a 12-tall wall left a
                                    # one-tile nook nobody can stand in
    g.ground(26, 27, 22)
    g.mark("arena_floor", 38, 26)       # 21 tiles straight down off ledge_b
    g.rect(48, 15, 1, 13, "s")
    g.platform(30, 21, 3)
    g.platform(42, 21, 3)

    # Drawn after the upper ledge on purpose: written before it, the ledge
    # overwrote the top and the climb dead-ended.
    g.vine(21, 9, 18)

    g.ent("player_spawn", 2, 25)
    g.ent("enemy_shooter", 6, 25)
    g.ent("enemy_shooter", 18, 25)
    g.ent("enemy_swimmer", 12, 25)
    g.ent("enemy_swimmer", 14, 26)
    g.ent("enemy_walker", 16, 9)
    g.ent("enemy_jumper", 20, 9)
    g.ent("enemy_shooter", 28, 9)
    g.ent("enemy_walker", 41, 5)
    g.ent("heart", 40, 5)
    g.ent("heart", 3, 4)
    for (x, y) in [(12, 19), (13, 19), (5, 20), (10, 11), (11, 11), (16, 9),
                   (7, 6), (2, 4), (26, 9), (35, 7), (36, 7), (44, 5)]:
        g.ent("gem", x, y)

    g.ent("boss_grove", 40, 25)
    g.ent("boss_exit", 46, 26)

    # ---- the intended solution (ADR 005)
    # Swim the pool, up the vine, east across two screens, then off the lip into
    # the arena, which is sealed on both sides and cannot be left by climbing.
    #
    # The Warden is deliberately NOT a waypoint. A fight is not a traversal
    # problem -- it has its own gate (ADR 005 section 4) -- and boss_grove is
    # authored at row 25 while the arena floor is stood on at row 26, so asking
    # the prover to "arrive at the boss" asks it to reach a point a tile above
    # anywhere the player can be. What this route claims about screen D is the
    # part the prover can actually answer: you can get in, and the floor you
    # land on connects to the way out.
    g.route("spawn", "vine_foot", form="human")           # across the pool at 9-16
    g.route("vine_foot", "canopy_ledge", form="human")    # 17 tiles of vine, C -> A
    g.route("canopy_ledge", "east_ledge", form="human")   # jump the gap at 23-24
    g.route("east_ledge", "branch", form="human")
    g.route("branch", "ledge_b", form="human")
    g.route("ledge_b", "arena_floor", form="human")       # the one-way drop, B -> D
    g.route("arena_floor", "boss_exit", form="human")     # across the arena floor
    return g


def test_arena():
    """Deterministic 1x1-screen arena used by tests/integration. Not reachable
    from the hub — it exists so integration tests never depend on level design."""
    g = Grid(25, 15)
    g.ground(0, 12, 25)
    g.rect(0, 0, 1, 12, "s")       # left wall
    g.rect(24, 0, 1, 12, "s")      # right wall
    g.rect(10, 13, 3, 1, ".")      # hole in the floor slab for the fall test
    g.spikes(20, 11, 2)
    g.crates(18, 11, 1)   # on the far side of the blade lane
    g.platform(14, 8, 3)
    g.vine(17, 5, 7)
    # cols 8..13 are deliberately clear: that is the blade's test lane,
    # and nothing breakable sits within one throw of it.

    g.ent("player_spawn", 2, 11)
    g.ent("enemy_walker", 9, 11)
    g.ent("gem", 4, 11)
    g.ent("heart", 5, 9)
    g.ent("exit", 22, 11)

    # The arena is a fixture, but it still has to be finishable or the replay
    # case built on it proves nothing. Run the lane east, past the crate at
    # col 18, then clear the two spike tiles at 20-21 in one jump.
    g.mark("spike_lip", 19, 11)
    g.route("spawn", "spike_lip", form="human")
    g.route("spike_lip", "exit", form="human")
    return g


HUB_DOORS = [
    {"level": "jungle_1", "label": "CANOPY TRAIL", "x": 5, "y": 6},
    {"level": "jungle_2", "label": "ROOT HOLLOW", "x": 14, "y": 4, "requires": "jungle_1"},
    {"level": "jungle_3", "label": "THE WATERWAY", "x": 23, "y": 9, "requires": "jungle_2"},
    {"level": "jungle_4", "label": "SKY BRANCH", "x": 33, "y": 4, "requires": "jungle_3"},
    {"level": "jungle_5", "label": "HEART OF THE GROVE", "x": 43, "y": 7,
     "requires": "jungle_4", "requires_all": True},
]

def build(level_id, built, name, **kw):
    """Write one level, auditing it first if it came with a Kit.

    A level function returns either a `Grid` or a `(Grid, Kit)` tuple. The
    tuple form runs `Kit.audit()` before anything is written, so a level whose
    shapes stopped being traversable never reaches levels/ at all -- and prints
    whatever the kit could not check, which for the new worlds includes every
    tile drawn with an understudy because data/level_legend.json has no
    character for it yet.
    """
    kit = None
    if isinstance(built, tuple):
        built, kit = built
    if kit is not None:
        for line in kit.audit():
            print(line)
    write(level_id, built, name, **kw)


if __name__ == "__main__":
    build("hub", hub(HUB_DOORS), "THE CANOPY", music="hub", topdown=True)
    build("jungle_1", jungle_1(), "CANOPY TRAIL", music="world1")
    build("jungle_2", jungle_2(), "ROOT HOLLOW", music="world1")
    build("jungle_3", jungle_3(), "THE WATERWAY", music="world2")
    build("jungle_4", jungle_4(), "SKY BRANCH", music="world2")
    build("jungle_5", jungle_5(), "HEART OF THE GROVE", music="boss")
    build("test_arena", test_arena(), "TEST ARENA")
