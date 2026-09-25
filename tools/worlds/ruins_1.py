#!/usr/bin/env python3
"""ruins_1 — DROWNED STEPS. The opener of World 2, SUNKEN RUINS.

Self-contained: `python tools/worlds/ruins_1.py` writes levels/ruins_1.json.
`tools/build_levels.py` can also call `ruins_1()` and get the `(Grid, Kit)`
tuple its `build()` helper audits before writing.

WHAT THIS LEVEL TEACHES
-----------------------
World 2's new verb is the water current: a tile that carries you (ids 200-205,
`data/tiles.json`). Nobody has met one before this level, so it is introduced
three times, in the order a teaching level owes the player:

  1. DRY STONE. Kaya arrives human on a ruined terrace, walks east, and sees
     the flooded nave below her. Nothing is asked of her.
  2. A CURRENT THAT HELPS. She steps off the terrace into a trough flowing
     east -- the direction she was already going. Getting it wrong costs
     nothing: the water takes her where she wanted to go. What she learns on
     the way out is that she cannot swim back: a human's 66.96 px/s (max_run
     108 x water_move_scale 0.62) loses to the water's 68.
  3. THE FISH, WHERE BEING A FISH IS OBVIOUSLY BETTER. A shallow pool with
     `pad_fish` standing IN it, so the transform never beaches her, and then a
     drowned nave of submerged colonnades to weave through.
  4. A CURRENT THAT PUSHES BACK. A tube flowing west that she must cross going
     east. This is the gate of the level and the reason the fish is not
     optional: 92 px/s of swim against 68 of water is 24 px/s of headway, and
     the human's 66.96 against the same 68 is -1. If she loses it she is
     washed back out of the tube into the nave, under a bell of trapped air --
     no damage, no dead end, just the crossing again.
  5. THE EXIT. Out of the water on a one-tile bank (the only step the fish's
     surface_hop clears), human again, and up a kelp rope into the dry
     gatehouse.

WHY THE GEOMETRY IS WHAT IT IS
------------------------------
* The fish CANNOT hop a 16 px bank from land: on land it jumps
  jump_vel 150^2 / (2 x gravity 900) = 12.5 px, less than a tile. It can leave
  the water, because `surface_hop` -210 against the same gravity is 24.5 px.
  So the only place the route ever asks the fish to leave the water is
  `bank_foot` -> `pad_human`, and that is a ONE tile rise off the surface --
  the same shape jungle_3 proves. Everything else the fish does, it does wet.
* `data/forms/fish.json` sets `out_of_water: "revert"`, so a beached fish
  becomes Kaya again rather than dying. That is a kindness, not a licence: the
  prover (`tools/solver/sim.gd`, `rejection()`) refuses a fish state with no
  air left outright, so a route that walks a fish over dry stone fails the
  gate even though a human would survive it. Hence `pad_fish` at (27, 24),
  which is a tile of standing water, not a tile of shore.
* Every step up on the human's half of the route is ONE tile. The measured
  limit is two (`LIMITS` in tools/world_kit.py); this is the gentlest level in
  the world and it spends none of that margin.

THE PALETTE, AND WHY IT NAMES JUNGLE TILES
------------------------------------------
`world_kit.Palette` resolves a role to a character through the flat `legend`
key of data/level_legend.json -- which ADR 002's amendment leaves as the
*jungle* view, because tools/reachability.py and tools/build_hub.py read it
directly. A palette that names `ruin_stone` therefore finds no character,
falls through to its understudy, and emits whatever character the understudy
happens to own: `stone` -> 's', which the ruins tileset binds to ruin_grate,
not ruin_stone. The shapes would be right and the whole level would be built
out of the wrong stone.

So this palette names, for each role, the jungle tile that OWNS the character
the ruins tileset binds to the art we want. It is the same statement as ADR
002's role table read in the other direction -- '#' is the world's ground cap,
'L' its background wall -- and it is safe for exactly the reason ADR 002 pins
with a test: the role mapping preserves gameplay flags across worlds, so
grass_top (solid) and ruin_stone (solid) are the same tile to every checker
that reads flags, and `"tileset": "ruins"` in the level JSON is what decides
the art. The upshot that matters: `Palette.substituted` stays EMPTY, so
`Kit.audit(strict_verbs=True)` is meaningful here -- the currents below are
the real current tiles (200/201), not still water wearing their walls.
"""
import os, sys

_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _TOOLS)

from gen_levels import Grid, write                                  # noqa: E402
import world_kit                                                    # noqa: E402
from world_kit import Kit, Palette, Probe                           # noqa: E402

LEVEL_ID = "ruins_1"
LEVEL_NAME = "DROWNED STEPS"


## Role -> the jungle tile that owns the character the ruins tileset binds to
## the art this level wants. See the module docstring.
RUINS = Palette("sunken_ruins", {
    "bg":         "bg_leaves",      # 'L' -> 222 ruin_wall
    "solid":      "grass_top",      # '#' -> 220 ruin_stone
    "solid_alt":  "stone_mossy",    # 'S' -> 221 ruin_stone_algae
    "packed":     "dirt",           # 'd' -> 223 ruin_silt
    "block":      "stone",          # 's' -> 228 ruin_grate
    "oneway":     "wood_platform",  # '=' -> 226 ruin_slab
    "ladder":     "vine",           # '|' -> 229 kelp
    "hazard":     "spikes",         # '^' -> 227 ruin_urchin
    "breakable":  "crate",          # 'c' -> 231 ruin_cracked
    "decor":      "tree_trunk",     # 'T' -> 225 ruin_column
    "void":       "bg_dark",        # 'X' -> 224 ruin_deep
    "water":      "water",          # 'w' (shared)
    "water_top":  "water_top",      # '~' (shared)
    "shoulder":   "cracked_stone",  # 'k' (shared)
    "rubble":     "rubble",         # 'o' (shared)
    "cur_right":      "water_current_right",        # '>' (shared, 200)
    "cur_left":       "water_current_left",         # '<' (shared, 201)
    "cur_up":         "water_current_up",           # 'u' (shared, 202)
    "cur_down":       "water_current_down",         # 'v' (shared, 203)
    "cur_right_fast": "water_current_right_fast",   # '}' (shared, 204)
    "cur_left_fast":  "water_current_left_fast",    # '{' (shared, 205)
})

ALGAE_ROWS = range(19, 28)   ## the waterline band the algae stains


def _algae(k):
    """Stain the ashlar where the water has stood.

    Purely cosmetic: 'S' is ruin_stone_algae, solid, the same tile to every
    flag-reading checker as the '#' it replaces. Applied only to faces that
    touch open space in the waterline band, so it draws a tide line rather
    than a texture.
    """
    g = k.g
    cap = k.ch("solid")
    alt = k.ch("solid_alt")
    stained = []
    for y in ALGAE_ROWS:
        for x in range(g.w):
            if g.fg[y][x] != cap:
                continue
            for dx, dy in ((0, -1), (-1, 0), (1, 0)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < g.w and 0 <= ny < g.h):
                    continue
                if g.fg[ny][nx] not in (cap, alt, k.ch("packed")):
                    stained.append((x, y))
                    break
    for x, y in stained:
        g.put(x, y, alt)


def ruins_1():
    g = Grid(50, 30, tileset="ruins")
    k = Kit(g, RUINS, form="human")

    # The level is CARVED, not built: solid ruin stone everywhere, then cut
    # out. `Kit.fill_solid` says why that is worth doing -- a carved level has
    # a small reachable state space, so a prover hop that fails exhausts its
    # frontier instead of spending its whole budget wandering open sky.
    k.fill_bg("bg")
    k.fill_solid("solid")

    # ============================================ 1. dry stone (screens A -> C)
    # You arrive in the gatehouse gallery, high and dry, and walk east until
    # the floor stops. The drop into the hall below is twelve tiles and
    # one-way, which is the level saying what it is: you are going down into
    # the water and you are not coming back up this way.
    k.clear_rect(1, 8, 9, 4)                  # the gallery, cols 1-9 rows 8-11
    k.floor(1, 12, 6, depth=6)                # its floor stops at col 6
    k.clear_rect(7, 12, 3, 6)                 # the well down into the hall
    k.mark("lip", 6, 11)                      # the last tile with stone under it

    # The hall. Six tiles of headroom, a flat floor, one walker, and a view
    # east down into the water.
    k.corridor(1, 23, 9, h=6)                 # cols 1-9, rows 18-23
    k.floor(1, 24, 9, depth=6)                # cap row 24, silt beneath
    k.mark("terrace", 8, 23)

    # ========================================= 2. the current that HELPS
    # A trough three tiles deep flowing east, with still water at each end so
    # the arrows read as a thing that starts and stops. Kaya walks off the
    # terrace at col 10 and falls into it; the water does the rest.
    #
    # She cannot swim back out the way she came, and that is the lesson: her
    # 66.96 px/s in water is less than the trough's 68. Nothing is lost by
    # discovering it, because east is where the level goes.
    k.corridor(10, 26, 11, h=9)               # cols 10-20, rows 18-26
    k.rect(10, 27, 11, 1, "packed")           # the silt bed
    k.rect(10, 24, 11, 1, "water_top")
    k.rect(10, 25, 11, 2, "water")
    world_kit.current_channel(k, 11, 26, 9, "right", height=3, wall=False)
    k.mark("trough_in", 11, 26)               # the first tile of moving water
    k.mark("trough_out", 20, 26)              # still water at the downstream end

    # ------------------------------------------------ the steps back into air
    # Three one-tile risers. DROWNED STEPS is named for them.
    k.corridor(21, 25, 1, h=8)
    k.floor(21, 26, 1, depth=4)
    k.corridor(22, 24, 1, h=7)
    k.floor(22, 25, 1, depth=5)
    # Three tiles of dry floor, not two, so the level's VERTICAL screen seam
    # (between cols 24 and 25) falls in the middle of flat ground rather than
    # on the step down into the pool. `CameraController` picks the screen from
    # the player's centre and freezes the sim for the length of every flip, so
    # a spot where the player naturally hesitates on the seam line flips the
    # camera back and forth. The ADR-005 gate cannot see that -- the prover has
    # no camera and the tape replay skips paused ticks -- so it is geometry's
    # job to keep the seam somewhere dull.
    k.corridor(23, 23, 3, h=6)
    k.floor(23, 24, 3, depth=6)
    k.mark("steps_top", 23, 23)

    # ====================================== 3. the fish, where a fish is better
    # A shallow pool with the pad standing in it. Two tiles of water is the
    # kit's floor for a fish and it is what this is: enough to swim, shallow
    # enough that a human wades it with her head at the surface. She steps
    # down one tile into it, the pad fires, and she is already wet.
    world_kit.flooded_chamber(k, 26, 18, 4, 7, surface=23, wall=False, bed=True)

    # ------------------------------------------------------ the drowned nave
    # Roofed: rock sits straight on the water from col 30 east, so the nave is
    # a swim and not a wade. Surface row 23, bed row 27.
    k.clear_rect(30, 23, 9, 4)
    k.rect(30, 23, 9, 1, "water_top")
    k.rect(30, 24, 9, 3, "water")
    k.rect(30, 27, 9, 1, "packed")
    # Three fallen columns: over, under, over. `clearance=2` is the same rule
    # as a two-tile corridor -- a one-tile slot is a shape the body does not
    # fit through, which is defect 2 with water in it.
    cols = world_kit.colonnade(k, 31, 3, 3, surface=23, bed=26,
                               pattern=["over", "under", "over"],
                               width=2, mark="col", clearance=2)

    # A bell of trapped air against the nave roof, immediately downstream of
    # the tube. This is where the water puts you if the crossing beats you.
    world_kit.air_pocket(k, 36, 22, 3, h=2, roof=True)

    # ========================================= 4. the current that PUSHES BACK
    # A two-tile tube flowing west, and the level's one real demand. The fish
    # makes 24 px/s of headway through it (swim_speed 92 - 68) and crosses in
    # under three seconds. A human makes -1 and never crosses at all, which is
    # what makes the fish form the answer rather than a convenience.
    #
    # `current_channel` claims the tile just upstream of the flow is clear,
    # because a current with nothing behind it pins you against a wall for
    # ever. Here that tile is `tube_mouth`, and it is also the bail-out: lose
    # the crossing and you are put back on it, under the air bell.
    # Three tiles tall, not two, and that is a checker's requirement rather
    # than a designer's: `tools/reachability.py` walks the human four-ways and
    # calls a tile passable only with two non-solid tiles above it, so a
    # two-tile tube under a roof is a wall to it and it declared the whole of
    # the level east of here unreachable. Three tiles is also honest about the
    # geometry -- the tube is the nave's water carrying on under a lower roof,
    # and its surface row joins the nave's.
    k.clear_rect(39, 23, 5, 3)                # cols 39-43, rows 23-25
    k.rect(39, 23, 5, 1, "water_top")
    k.rect(39, 24, 5, 2, "water")
    world_kit.current_channel(k, 40, 25, 3, "left", height=3, wall=False)
    k.mark("tube_mouth", 39, 25)
    k.mark("tube_far", 43, 25)

    # ================================================== 5. out, and the exit
    # A flooded well: open water at the bottom, ten tiles of air above it, and
    # the gatehouse floor sealing the top. Falling back down it costs a swim,
    # not a life.
    world_kit.flooded_chamber(k, 44, 13, 2, 14, surface=23, wall=False, bed=True)
    k.mark("bank_foot", 45, 24)

    # The bank. `rise=1` is the only rise there is: surface_hop -210 against
    # gravity 900 lifts the fish 24.5 px, so one tile clears and two do not.
    # This is defect 4's tile, and the helper refuses to draw it any taller.
    world_kit.bank(k, 46, 23, 3, rise=1)

    # The chimney above the bank, and the gatehouse it opens into. The floor
    # is drawn BEFORE the kelp on purpose: written the other way round the
    # floor overwrites the top of the rope and the climb dead-ends, which is
    # how jungle_3 and jungle_5 both nearly shipped.
    k.clear_rect(46, 13, 2, 7)                # cols 46-47, rows 13-19
    k.corridor(30, 11, 19, h=4)               # the gatehouse, cols 30-48, rows 8-11
    k.floor(30, 12, 19, depth=1)              # its floor
    k.climb(47, 11, 21, landing="left")       # kelp, through the floor at row 12
    k.mark("sill", 46, 11)

    # ---------------------------------------------------------------- dressing
    for x in (3, 5):
        g.rect(x, 8, 1, 4, "T", "bg")         # columns in the gallery
    # Empty burial niches in the gallery's east wall. Sealed in rock and on
    # nobody's route: two tiles of headroom apiece so they read as alcoves and
    # not as the one-tile pockets defect 2 was made of.
    for x in (13, 16, 19, 22):
        k.clear_rect(x, 9, 1, 2)
        g.rect(x, 9, 1, 2, "T", "bg")
    for x in (3, 7, 13, 17, 27):
        g.rect(x, 18, 1, 6, "T", "bg")        # ruin columns standing in the air
    for x in (32, 35, 38):
        g.rect(x, 23, 1, 4, "T", "bg")        # and their drowned twins
    g.rect(30, 23, 14, 4, "X", "bg")          # the deep dark behind the nave
    g.rect(44, 23, 2, 4, "X", "bg")
    for x in (34, 38, 42, 46):
        g.rect(x, 8, 1, 4, "T", "bg")         # the gatehouse colonnade
    for (x, y, w, h) in [(10, 22, 11, 2), (26, 22, 4, 1), (39, 23, 5, 1),
                         (1, 22, 9, 1), (30, 10, 19, 1), (1, 10, 9, 1)]:
        g.rect(x, y, w, h, "r", "bg")         # algae bloom on the back wall
    _algae(k)

    # ------------------------------------------------------------- inhabitants
    g.ent("player_spawn", 2, 11)
    g.ent("enemy_walker", 7, 23)
    g.ent("pad_fish", 27, 24)
    g.ent("enemy_swimmer", 33, 25)
    g.ent("enemy_swimmer", 36, 25)
    # At col 47, not col 46, and the distance is the whole point. A
    # TransformPad's trigger box is its tile grown by three pixels, so a pad at
    # col 46 -- the bank's own west face -- reaches back over the water at col
    # 45 and fires while the fish is still airborne above it. MEASURED: it did,
    # and the hop after it began with a human falling into the well, which she
    # cannot climb out of (see REPORT.md section on the water-exit probe). One
    # column inland the pad cannot be touched from the water at all: reaching
    # its box needs pos.x >= 735, and at any depth col 46 is solid there, so
    # the only way to satisfy it is to have already cleared the bank.
    g.ent("pad_human", 47, 21)
    g.ent("exit", 32, 11)

    for (x, y) in [(3, 11), (4, 11),          # the gallery
                   (4, 23), (5, 23),          # the hall floor
                   (14, 25), (16, 25),        # swept past, in the current
                   (26, 24),                  # the shallow pool
                   (31, 24), (34, 26),        # over the first column, under the second
                   (41, 25),                  # the reward for beating the tube
                   (44, 24),                  # the foot of the well
                   (35, 11), (36, 11), (44, 11)]:   # the gatehouse
        g.ent("gem", x, y)
    g.ent("heart", 37, 22)                    # inside the air bell

    # ------------------------------------------ the intended solution (ADR 005)
    # Human the whole way east until the water gets deep, fish through the
    # nave and the tube, human again for the climb out. Thirteen hops, none of
    # them long, because a hop that needs a big budget is a hop that is too
    # coarse (ADR 005's addendum).
    g.route("spawn", "lip", form="human")                 # east along the gallery
    g.route("lip", "terrace", form="human")               # off the end, twelve tiles down
    g.route("terrace", "trough_in", form="human")         # step off, into the flow
    g.route("trough_in", "trough_out", form="human")      # CARRIED east, 9 tiles
    g.route("trough_out", "steps_top", form="human")      # the three one-tile risers
    g.route("steps_top", "pad_fish", form="human")        # down one, into the shallows
    g.route("pad_fish", cols[0], form="fish")             # over the first column
    g.route(cols[0], cols[1], form="fish")                # under the second
    g.route(cols[1], cols[2], form="fish")                # over the third
    g.route(cols[2], "tube_mouth", form="fish")           # into the tube's mouth
    g.route("tube_mouth", "tube_far", form="fish")        # UPSTREAM, 24 px/s of headway
    g.route("tube_far", "bank_foot", form="fish")         # out into the well
    g.route("bank_foot", "pad_human", form="fish")        # surface and hop the 16 px bank
    g.route("pad_human", "sill", form="human")            # ten tiles of kelp, D -> B
    g.route("sill", "exit", form="human")                 # west across the gatehouse
    return g, k


# --------------------------------------------------------------------- checks
## Two things tools/prove.sh cannot tell you and tests/ only tells you after a
## whole Godot boot. Cheap, so they run every time the level is emitted.

def _self_checks(g, k):
    p = Probe(g)
    bad = []
    # A standable tile with one tile of headroom reads as a passage and behaves
    # as a wall (defect 2). tests/test_level_validity.gd checks exactly this;
    # catching it here costs milliseconds instead of a test run.
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
    # Everything the player must touch needs a body's worth of room over it.
    must = {"exit", "pad_fish", "pad_human", "gem", "heart"}
    for e in g.entities:
        if e["type"] not in must:
            continue
        x, y = e["x"], e["y"]
        if not p.clear(x, y, 2):
            bad.append("%s at (%d,%d) has no two tiles of headroom"
                       % (e["type"], x, y))
    if bad:
        raise world_kit.WorldKitError(
            "%s: %d self-check failure(s):\n  %s"
            % (LEVEL_ID, len(bad), "\n  ".join(bad)))


def main():
    g, k = ruins_1()
    for line in k.audit(strict_verbs=True):
        print(line)
    _self_checks(g, k)
    write(LEVEL_ID, g, LEVEL_NAME, music="world2")


if __name__ == "__main__":
    main()
