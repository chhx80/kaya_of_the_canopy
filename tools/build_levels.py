#!/usr/bin/env python3
"""Level definitions. Run via tools/genlevels.sh."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_levels import Grid, write


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

    # ---------------- screen A (top-left)
    g.ground(17, 7, 4, depth=2)
    g.platform(12, 10, 4)
    g.platform(6, 12, 4)
    g.ground(0, 13, 5, depth=2)
    g.crates(2, 12, 2, vertical=True)

    # ---------------- A -> B along the canopy
    g.platform(23, 6, 4)
    g.platform(30, 8, 4)
    g.ground(35, 10, 6, depth=2)
    g.platform(42, 8, 3)

    # ---------------- descent shaft B -> D
    g.platform(45, 12, 4)
    g.platform(45, 17, 4)
    g.platform(40, 21, 4)
    g.platform(38, 24, 4)

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
    g.ground(2, 26, 12, depth=2)
    g.rect(2, 24, 1, 2, "s")
    g.platform(6, 22, 4)
    g.platform(11, 19, 4)
    g.crates(4, 25, 3, vertical=True)
    g.rect(14, 16, 1, 12, "s")                      # wall with a door in it
    g.rect(14, 24, 1, 2, ".")                       # doorway: two tiles, so a
                                                    # 22px character actually fits

    # ---- screen C right half: past the yellow door
    g.ground(15, 26, 9, depth=2)
    g.rect(19, 29, 3, 1, "^")
    g.rect(19, 26, 3, 3, ".")
    g.platform(17, 22, 3)
    g.vine(22, 15, 12)

    # ---- screen A (top-left): switch puzzle over a drop
    g.ground(2, 14, 6, depth=2)
    g.rect(8, 13, 4, 1, "A")                        # solid while group 1 is ON
    g.rect(12, 10, 4, 1, "a")                       # solid while group 1 is OFF
    g.ground(16, 9, 5, depth=2)
    g.platform(21, 12, 4)
    g.ground(2, 6, 8, depth=2)
    g.crates(9, 5, 2, vertical=True)

    # ---- screen B (top-right): the red key behind switch group 2
    g.ground(25, 9, 8, depth=2)
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
    g.ent("key_yellow", 12, 18)
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

    # ---- things to swim around
    g.rect(14, 24, 2, 5, "s")
    g.rect(21, 21, 2, 6, "s")
    g.rect(28, 25, 2, 4, "s")
    g.rect(35, 21, 2, 5, "s")
    g.rect(40, 26, 2, 3, "s")

    # ---- the far bank, and the way up
    g.ground(44, 20, 4, depth=10)
    g.vine(45, 9, 11)
    g.ground(38, 8, 10, depth=2)
    g.platform(33, 11, 4)
    g.ground(25, 13, 6, depth=2)
    g.platform(19, 10, 4)
    g.ground(2, 12, 10, depth=2)
    g.platform(13, 7, 4)
    g.ground(2, 5, 8, depth=2)

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
    g.rect(11, 8, 1, 18, "s")
    g.rect(18, 6, 1, 20, "s")
    g.ground(12, 26, 6)
    g.platform(12, 20, 3)
    g.platform(15, 15, 3)
    g.platform(12, 11, 3)
    g.ground(12, 7, 6, depth=1)

    # ---- the bird crossing: perches only, a long way apart
    g.ground(19, 7, 3, depth=1)
    g.platform(25, 5, 3)
    g.platform(31, 9, 3)
    g.platform(37, 4, 3)
    g.ground(41, 8, 7, depth=2)

    # ---- and a soft landing back on solid ground
    g.ground(41, 26, 7)
    g.vine(44, 9, 17)
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
    for (x, y) in [(13, 19), (16, 14), (13, 10), (26, 4), (32, 8), (38, 3),
                   (21, 15), (27, 18), (34, 21), (43, 25), (44, 25), (4, 25)]:
        g.ent("gem", x, y)
    g.ent("heart", 42, 7)
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
    g.vine(21, 15, 12)

    # ---- screen A: the canopy walk east
    g.ground(1, 14, 7, depth=2)
    g.platform(9, 12, 4)
    g.ground(14, 10, 9, depth=2)
    g.platform(6, 7, 4)
    g.ground(1, 5, 4, depth=2)

    # ---- screen B: the ledge you jump from
    g.ground(25, 10, 8, depth=2)
    g.platform(34, 8, 4)
    g.ground(39, 6, 9, depth=2)

    # ---- screen D: the arena. Sealed on both sides, flat floor.
    g.rect(25, 15, 1, 13, "s")      # down to the floor: a 12-tall wall left a
                                    # one-tile nook nobody can stand in
    g.ground(26, 27, 22)
    g.rect(48, 15, 1, 13, "s")
    g.platform(30, 21, 3)
    g.platform(42, 21, 3)

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
    return g


HUB_DOORS = [
    {"level": "jungle_1", "label": "CANOPY TRAIL", "x": 5, "y": 6},
    {"level": "jungle_2", "label": "ROOT HOLLOW", "x": 14, "y": 4, "requires": "jungle_1"},
    {"level": "jungle_3", "label": "THE WATERWAY", "x": 23, "y": 9, "requires": "jungle_2"},
    {"level": "jungle_4", "label": "SKY BRANCH", "x": 33, "y": 4, "requires": "jungle_3"},
    {"level": "jungle_5", "label": "HEART OF THE GROVE", "x": 43, "y": 7,
     "requires": "jungle_4", "requires_all": True},
]

if __name__ == "__main__":
    write("hub", hub(HUB_DOORS), "THE CANOPY", music="hub", topdown=True)
    write("jungle_1", jungle_1(), "CANOPY TRAIL", music="world1")
    write("jungle_2", jungle_2(), "ROOT HOLLOW", music="world1")
    write("jungle_3", jungle_3(), "THE WATERWAY", music="world2")
    write("jungle_4", jungle_4(), "SKY BRANCH", music="world2")
    write("jungle_5", jungle_5(), "HEART OF THE GROVE", music="boss")
    write("test_arena", test_arena(), "TEST ARENA")
