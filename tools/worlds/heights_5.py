#!/usr/bin/env python3
"""HEIGHTS_5 -- THE STORMCREST. World 3's boss level.

Self-contained on purpose, exactly like tools/worlds/ruins_5.py:
`python3 tools/worlds/heights_5.py` writes levels/heights_5.json without going
near tools/build_levels.py, so this level can be iterated against
tools/prove.sh and tools/bossgate.sh while the rest of THERMAL HEIGHTS is being
authored in other worktrees. To wire it into the shared builder, add

    from worlds.heights_5 import heights_5
    build("heights_5", heights_5(), "THE STORMCREST", music="boss")

to tools/build_levels.py's `__main__` block and nothing else changes.

`--art` regenerates assets/sprites/boss_stormcrest.png, the Stormcrest's
18-frame sheet. It lives here rather than in tools/art/sprites.py for the
reason THE TIDE MAW's does: this branch owns the boss and not the art pipeline,
and regenerating a shared module's output would collide with the five agents
screenshotting concurrently. The drawing itself goes through tools/art/palette.py,
so every pixel is a step on a generated ramp like the rest of the game.


THE PALETTE, AND WHY IT NAMES JUNGLE TILES
------------------------------------------
`world_kit.Palette.char()` resolves a tile NAME through the flat `legend` key of
data/level_legend.json, which ADR 002's amendment leaves as the *jungle* view
(tools/reachability.py and tools/build_hub.py read it directly). A palette that
names `heights_rock` therefore finds no character, falls through to
`UNDERSTUDY`, and emits whatever character the understudy owns -- `stone` -> 's',
which the heights tileset binds to heights_basalt, not heights_rock. The shapes
would be right and the mountain would be built out of the wrong stone.

So this palette names, for each role, the jungle tile that OWNS the character
the heights tileset binds to the art this level wants. It is ADR 002's role
table read in the other direction, and it is safe for the reason ADR 002 pins
with a test: the role mapping preserves gameplay flags across worlds, so
grass_top (solid) and heights_rock (solid) are the same tile to every checker
that reads flags, and `"tileset": "heights"` in the level JSON is what decides
the art. `Palette.missing()` and `Palette.substituted` both stay EMPTY, which is
why `audit(strict_verbs=True)` can be asked for here: nothing was drawn with a
stand-in, so the updraft in the chimney is a real updraft and not empty air
wearing its shape.


THE SHAPE OF THE LEVEL
----------------------
Four screens. The first three are THERMAL HEIGHTS' own verb spent as the bird,
and they exist to put Kaya on the floor of the eyrie in the state the fight
wants her in:

    A  the ridge, cols 0-24 rows 0-14      B  the east ridge, cols 25-49 rows 0-14
    C  the wind-shelter, rows 15-29        D  THE EYRIE -- the arena, rows 15-29

    spawn -> pad_bird -> east through the doorway into the chimney
          -> ride sixteen tiles of updraft (-400 px/s under a bird that falls
             at 190, so the climb is free and costs no stamina at all)
          -> out of the mouth onto the crest
          -> east along the ridge, over the cleft, to the lip at col 40
          -> off the lip, down the light-shaft in the eyrie's roof, sixteen
             tiles, onto the arena floor and the pad that makes her human again.

The drop is one-way by construction: the eyrie is roofed at row 15 except for
the three columns of that shaft, and nothing in the arena is within reach of it.


THE FIGHT, AND THE ONE THING IT DOES NOT DO
-------------------------------------------
docs/plan-20-levels.md: "Airborne, fought as the bird. It is only vulnerable
while roosting, so the fight is stamina against its roost cycle; updrafts are
the only way to regain height."

Two of those three are here. The third cannot be, and pretending otherwise
would ship an unwinnable fight:

**The bird has no weapon.** data/forms/bird.json is `can_attack: false`, so
`FormBase.weapon_id()` returns "" and `Player.try_attack()` has nothing to
throw. A fight fought as the bird is a fight in which Kaya cannot deal one
point of damage in ninety seconds. This is the same wall ruins_5 hit with the
fish (whose `bite` has `reach: 10.0`), and the same answer: the verb stays in
the approach, where it can be spent, and the fight is fought with the blade.
Giving the bird a weapon is a real design answer to that sentence and it is not
this branch's to make.

**So the roost comes down to the blade.** The Stormcrest owns the sky --
`src/enemies/stormcrest.gd` refuses damage on any frame it is not roosting, and
plays a ricochet instead -- and it has to land to fold its wings. Its three
roost pads are on the arena floor (the bleached rock at cols 32, 37 and 42),
which is what makes the window a window: the blade leaves Kaya's chest 5-17 px
above the floor she is standing on, and a 46 px body standing on that same floor
is the only thing in this arena the blade can reach. Measured from the gate's
own `_can_fight_from`, every safe tile in the arena damages it inside six
seconds, because the stoop follows Kaya and the roost is wherever the stoop
ended.

**And the roost cycle is the clock.** It circles, invulnerable, for
`dive_interval` seconds, feathers the floor, stoops, and is then vulnerable for
`roost_time`. Every window missed is another lap of its attacks to survive, and
that -- not a health bar race -- is the shape of the fight.


WHY THE ARENA IS SHAPED LIKE THIS
---------------------------------
The rule is THE TIDE MAW's, stated in tools/worlds/ruins_5.py and applied to the
Grove Warden afterwards (see CHANGELOG, "THE GROVE WARDEN passes its gate"):
every standable tile is the floor or a one-way refuge two tiles above it, no
refuge is out of the boss's reach for good, and every attack misses somewhere a
player can actually stand.

  * **No high ledges at all.** The arena's standable set is the floor (row 27's
    cap, stood on at row 26) and the two one-way slabs at row 25, stood on at
    row 24 -- 32 px over the floor against Kaya's measured 46 px jump. Everything
    above is open sky, because the gate measures refuge reachability by JUMPING
    at it from the floor row and nothing else: a tile three tiles up is
    reported unreachable however elegant the staircase to it.
  * **And therefore no updraft in the arena.** This is the one place the world's
    verb had to be left out, and the number is the reason: a body jumping off
    the floor tops out with its head in row 22.75, so an updraft column whose
    foot is at row 22 or lower is entered by any jump -- including the jump onto
    a refuge slab, which it would then lift her straight past. An arena thermal
    that makes the refuges unreachable fails the gate's check 3 in spirit and
    passes it in letter, which is the exact failure ADR 005 exists to stop. The
    thermals are in the approach, where they lift her sixteen tiles.
  * **The gale is the verb instead.** `stormcrest.gd` writes real gust tiles into
    the arena air per phase and takes them out again (the tide_maw mechanism,
    with the same three rules), so the wind is a fact about the world and not a
    tint: SQUALL blows the two shelters out, TEMPEST blows the whole floor
    inward. A human runs 108 px/s against a gust of 80, so holding a shelter
    costs 28 px/s of press and never becomes a wall.
  * **The bore misses the slabs; the feathers miss the shelters.** The stoop's
    crash throws a wave along the floor at the Stormcrest's feet, 4 px up, and a
    body on a slab is 32 px over it. The feather volley falls out of the sky, and
    the two buttresses (cols 26-29 and 45-48, rows 16-21) are solid rock that
    eats it -- so the four floor tiles under each buttress are the volley's dodge
    and the slabs are the bore's. Nothing in this arena is safe from everything:
    the bore runs the floor wall to wall, under the buttresses and under the
    slabs alike.
  * **The buttresses stop at row 21, five rows over the shelter, and that is a
    measured number rather than a proportion.** They were drawn down to row 24 in
    the first cut -- a two-tile nook -- and a body under a roof 32 px up cannot
    jump: she rises ten pixels, which is neither over the bore nor onto anything.
    The Boss Gate answers "is this refuge reachable" by jumping at it from the
    six nearest floor tiles, and two of those six for the west slab are the
    shelter's own tiles, so a roof low enough to stop a jump there also takes two
    of its six attempts away. Row 21 leaves the full 46 px of jump under the
    rock, and the rock still eats the volley: a feather leaving the Stormcrest at
    y=320 on the steepest angle the fan throws is at col 29 by the time it has
    fallen to row 21, which is inside the buttress.
  * **The slabs sit INSIDE the span the Stormcrest is clamped to** (cols 31-40
    against a clamp of 31-44), so it roosts underneath them and its 46 px body
    reaches a body on the slab. A refuge the boss can never be fought from, or
    never reached by, is a corner to camp in.
  * **The floor is unbroken wall to wall.** ruins_5 records what the alternative
    cost: raising the refuges out of the floor as solid blocks cornered Kaya
    against her own standoff and the recorder never got the Maw below 12 of 18.

The level is authored with the arena calm, which is also phase 1, so
tools/prove.sh and the traversal tape both see exactly the geometry in
levels/heights_5.json.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from gen_levels import Grid, write                     # noqa: E402
from world_kit import Kit, Palette                     # noqa: E402

LEVEL_ID = "heights_5"
LEVEL_NAME = "THE STORMCREST"
W, H = 50, 30

## Role -> the jungle tile that owns the character the heights tileset binds to
## the art this level wants. See the module docstring.
HEIGHTS_CHARS = Palette("thermal_heights", {
    "bg":         "bg_leaves",      # 'L' -> 242 heights_wall
    "solid":      "grass_top",      # '#' -> 240 heights_rock
    "solid_alt":  "stone_mossy",    # 'S' -> 241 heights_rock_sun
    "packed":     "dirt",           # 'd' -> 243 heights_scree
    "block":      "stone",          # 's' -> 249 heights_basalt
    "oneway":     "wood_platform",  # '=' -> 246 heights_plank
    "ladder":     "vine",           # '|' -> 248 heights_chain
    "hazard":     "spikes",         # '^' -> 247 heights_vent
    "breakable":  "crate",          # 'c' -> 251 heights_shell
    "decor":      "tree_trunk",     # 'T' -> 245 heights_stack
    "void":       "bg_dark",        # 'X' -> 244 heights_air
    "water":      "water",          # 'w'  shared
    "water_top":  "water_top",      # '~'  shared
    "shoulder":   "cracked_stone",  # 'k'  shared
    "rubble":     "rubble",         # 'o'  shared
    "updraft":        "updraft",          # 'U'  shared, 206, -400 px/s
    "updraft_strong": "updraft_strong",   # '*'  shared, 207
    "downdraft":      "downdraft",        # 'V'  shared, 208
    "gust_right":     "gust_right",       # ')'  shared, 209, +80 px/s
    "gust_left":      "gust_left",        # '('  shared, 210
})

# ------------------------------------------------------------------ geometry
# Named once, because data/enemies/stormcrest.json repeats four of them and an
# arena whose boss and whose author disagree about where the floor is has no
# chance at all.
MASS_TOP = 11                      # the mountain's surface row (cap)
CREST_STAND = MASS_TOP - 1         # 10 -- the ridge you walk east along
CLEFT_X0, CLEFT_X1 = 15, 18        # the four-tile cleft in the ridge
CLEFT_TOP = 14                     # its floor cap; stood on at row 13
SHAFT_X0, SHAFT_X1 = 9, 10         # the chimney: two columns of updraft
SHAFT_TOP, SHAFT_FOOT = MASS_TOP, 26
CHAMBER_STAND = 26                 # the wind-shelter's floor, stood on
LIP_COL = 40                       # the last ridge tile before the light-shaft

ARENA_X0, ARENA_X1 = 26, 48        # interior columns of screen D
ROOF_ROW = 15                      # the eyrie's roof
NOTCH_X0, NOTCH_X1 = 41, 43        # the light-shaft through it
BUTT_W0, BUTT_W1 = 26, 29          # west buttress columns
BUTT_E0, BUTT_E1 = 45, 48          # east buttress columns
BUTT_TOP, BUTT_BOT = 16, 21        # its rows: solid rock over each shelter
FLOOR_ROW = 27                     # the arena's one unbroken floor
STAND_ROW = FLOOR_ROW - 1          # 26 -- the tile a body's feet are in
SHELF_ROW = 25                     # the one-way refuge slabs
SHELF_STAND = SHELF_ROW - 1        # 24 -- two tiles over the arena floor
WEST_SLAB, EAST_SLAB, SLAB_W = 31, 37, 4
PIT_X0, PIT_X1 = 31, 44            # the span the Stormcrest is clamped to
DROP_COL = 42                      # where the light-shaft lands her
ROOST_COLS = (32, 37, 42)          # the bleached pads it comes down on
GALE_Y, GALE_H = SHELF_ROW, 2      # the rows the gale may write into


def heights_5():
    """Draw the level. Returns (Grid, Kit) so main() can audit before writing.

    Drawn with `Grid` and the ROLE CHARACTERS of ADR 002's amendment -- '#' the
    world's ground cap, 'd' the fill under it, 's' its second solid, '=' its
    one-way, 'U' the updraft -- because the grid's `tileset="heights"` is what
    turns those into heights rock, scree, basalt, planks and thermal air. `Kit`
    is here for its claims and its audit: the claims are checked against the
    grid as it FINALLY stands, which is the only moment they are true or false.
    """
    g = Grid(W, H, tileset="heights")
    k = Kit(g, HEIGHTS_CHARS, form="bird")

    # ---------------------------------------------------------------- dressing
    g.rect(0, 0, W, H, "L", "bg")            # heights_wall behind everything
    g.rect(1, 1, 48, 10, "X", "bg")          # open air above the ridge line
    g.rect(26, 16, 23, 11, "X", "bg")        # and inside the eyrie
    for x in (4, 13, 22, 29, 36, 45):        # cloud banks
        g.rect(x, 2, 3, 2, "r", "bg")
    for x in (3, 20, 34, 47):                # basalt stacks on the skyline
        g.trunk(x, 5, 6)
    for x in (30, 39):
        g.trunk(x, 17, 8)                    # stacks inside the eyrie

    # ---------------------------------------------------------------- the shell
    # Nothing walks off the edge of the world.
    g.rect(0, 0, W, 1, "s")
    g.rect(0, H - 1, W, 1, "s")
    g.rect(0, 0, 1, H, "s")
    g.rect(W - 1, 0, 1, H, "s")

    # =================================================================
    # THE MOUNTAIN. Screens A and C are a solid mass with the chimney and
    # the shelter cut out of it, which is also what keeps the prover's
    # frontier small: a failed hop exhausts its frontier inside the rock
    # instead of wandering open sky.
    # =================================================================
    g.rect(1, MASS_TOP, 48, H - 1 - MASS_TOP, "d")
    g.hline(1, MASS_TOP, 48, "#")            # the surface, cols 1-48

    # ---------------------------------------------------------------- screen C
    # The wind-shelter she starts in: three rows of air under nine tiles of rock.
    g.rect(1, 24, 7, 3, "."), g.hline(1, FLOOR_ROW, 10, "#")
    # The doorway east into the chimney: two tiles, because a body is 22 px and
    # defect 3 was a door one tile tall.
    g.rect(8, 25, 1, 2, ".")
    k._claim("clear", "the doorway into the chimney at col 8",
             x=8, y=CHAMBER_STAND, tall=2)
    for x in (2, 5, 7):
        k._claim("stand", "the shelter floor at col %d" % x,
                 x=x, y=CHAMBER_STAND, form="human")

    # ---------------------------------------------------------------- the chimney
    # Sixteen tiles of rising air in a two-column shaft, walled by the mass on
    # both sides and open at the top. THERMAL HEIGHTS' verb doing the work: 400
    # px/s of lift under a bird whose own terminal fall is 190, so
    # `FormBase.apply_gravity` caps her at -210 px/s and she climbs sixteen
    # tiles in 1.2 s without spending a single one of her eight flaps.
    g.rect(SHAFT_X0, SHAFT_TOP, 2, SHAFT_FOOT - SHAFT_TOP + 1, "U")
    g.mark("draft_foot", SHAFT_X0, SHAFT_FOOT)
    # Mid-shaft and mouth are tiles in a column of air, not places to stand, so
    # they are plain Grid marks: `ProverSearch._reached_goal` counts a bird as
    # arrived wherever it touches, which is the whole point of being one.
    g.mark("draft_mid", SHAFT_X0, 18)
    k._claim("stand", "the foot of the chimney", x=SHAFT_X0, y=SHAFT_FOOT,
             form="bird")
    k._claim("clear", "the chimney's mouth", x=SHAFT_X0, y=SHAFT_TOP - 1, tall=2)
    k._claim("clear", "the chimney's mouth, east column",
             x=SHAFT_X0 + 1, y=SHAFT_TOP - 1, tall=2)

    # ---------------------------------------------------------------- the ridge
    # The crest is one walked line from the chimney's mouth to the lip, so the
    # A -> B screen seam is crossed on solid ground rather than in mid-flight.
    # A route that crosses a seam airborne passes the gate and plays badly --
    # the flip freezes the simulation for the title card and she falls through
    # the pause.
    k.mark("crest", SHAFT_X0 + 3, CREST_STAND, form="bird")
    # The cleft: four tiles of ridge missing, with its own floor three tiles
    # down. A missed hop costs altitude, not a life -- the bird clears 6 across
    # and 5 up (proofs/jungle_4.tape.json), so climbing back out is free.
    g.rect(CLEFT_X0, MASS_TOP, CLEFT_X1 - CLEFT_X0 + 1, CLEFT_TOP - MASS_TOP, ".")
    g.hline(CLEFT_X0, CLEFT_TOP, CLEFT_X1 - CLEFT_X0 + 1, "#")
    k._claim("stand", "the cleft floor", x=CLEFT_X0 + 1, y=CLEFT_TOP - 1,
             form="bird")
    k._claim("step", "the hop across the cleft",
             x1=CLEFT_X0 - 1, y1=CREST_STAND, x2=CLEFT_X1 + 1, y2=CREST_STAND,
             form="bird")
    k.mark("ridge", CLEFT_X1 + 4, CREST_STAND, form="bird")
    k.mark("lip", LIP_COL, CREST_STAND, form="bird")

    # =================================================================
    # SCREEN D -- THE EYRIE
    # =================================================================
    g.rect(25, ROOF_ROW, 1, H - 1 - ROOF_ROW, "s")          # sealed west
    # The roof, and the light-shaft through it. Everything from row 16 down is
    # carved back out of the mass above.
    g.rect(ARENA_X0, ROOF_ROW + 1, ARENA_X1 - ARENA_X0 + 1,
           FLOOR_ROW - ROOF_ROW - 1, ".")
    g.hline(ARENA_X0, ROOF_ROW, ARENA_X1 - ARENA_X0 + 1, "s")
    g.rect(NOTCH_X0, MASS_TOP, NOTCH_X1 - NOTCH_X0 + 1, ROOF_ROW - MASS_TOP + 1, ".")
    for x in range(NOTCH_X0, NOTCH_X1 + 1):
        k._claim("clear", "the light-shaft at col %d" % x, x=x, y=ROOF_ROW, tall=2)

    # The two buttresses. Solid rock from the roof down to row 24, which is what
    # makes the four floor tiles under each of them the feather volley's dodge
    # window: a shot falling out of the sky dies on the rock, and nothing in the
    # fan is flat enough to come in sideways under a roof 32 px off the floor.
    # Basalt, like the roof, and not the ground cap: '#' draws a lit top edge and
    # the only face of a buttress the player ever sees is its underside.
    g.rect(BUTT_W0, BUTT_TOP, BUTT_W1 - BUTT_W0 + 1, BUTT_BOT - BUTT_TOP + 1, "s")
    g.rect(BUTT_E0, BUTT_TOP, BUTT_E1 - BUTT_E0 + 1, BUTT_BOT - BUTT_TOP + 1, "s")

    # ONE unbroken floor, wall to wall, with the three roost pads bleached into
    # it so the fight reads: the Stormcrest comes down on the sunlit rock.
    g.ground(ARENA_X0, FLOOR_ROW, ARENA_X1 - ARENA_X0 + 1, depth=2)
    for x in ROOST_COLS:
        g.hline(x - 1, FLOOR_ROW, 3, "S")

    # The refuges: one-way slabs two tiles over the floor, inside the span the
    # Stormcrest is clamped to, open underneath so the whole 23-tile width is
    # still somewhere to run.
    g.platform(WEST_SLAB, SHELF_ROW, SLAB_W)
    g.platform(EAST_SLAB, SHELF_ROW, SLAB_W)
    for x in (WEST_SLAB, WEST_SLAB + SLAB_W - 1, EAST_SLAB, EAST_SLAB + SLAB_W - 1):
        k._claim("stand", "arena refuge slab at col %d" % x,
                 x=x, y=SHELF_STAND, form="human")
    for x in (ARENA_X0, BUTT_W1, PIT_X0, 36, PIT_X1, BUTT_E0, ARENA_X1):
        k._claim("stand", "arena floor at col %d" % x,
                 x=x, y=STAND_ROW, form="human")
    # Getting onto a refuge is the whole point of it, so the step up is a claim
    # and not a hope: 32 px against a measured 46 px jump.
    k._claim("step", "the step off the floor onto the west refuge",
             x1=WEST_SLAB, y1=STAND_ROW, x2=WEST_SLAB, y2=SHELF_STAND, form="human")
    k._claim("step", "the step off the floor onto the east refuge",
             x1=EAST_SLAB, y1=STAND_ROW, x2=EAST_SLAB, y2=SHELF_STAND, form="human")
    # Directly under the shaft, not in the middle of the arena. The prover's
    # frontier is manhattan distance (ADR 005's addendum), so a landing tile
    # west of the fall makes the only way down look like a way away. Col 42 is
    # also inside the span the Stormcrest is clamped to, which
    # tests/integration/integration_tests.gd asserts of a boss level's
    # traversal tape, and it has no slab over it.
    k.mark("arena_floor", DROP_COL, STAND_ROW, form="human")

    # ---------------------------------------------------------------- entities
    g.ent("player_spawn", 2, CHAMBER_STAND)
    g.ent("pad_bird", 5, CHAMBER_STAND)
    # The one pad in the arena, and it only ever makes her human. She arrives on
    # the wing -- which is the plan's sentence, honoured where it can be -- and
    # the pad is what puts the blade back in her hand. It is inert for the rest
    # of the fight (`TransformPad` returns early when the form already matches),
    # which is also why it cannot disturb the gate's fairness sweep: that sweep
    # pins a HUMAN on every standable tile, and this pad has nothing to say to
    # one. A second pad in here would: measured on ruins_5, a fish pad inside the
    # arena turned a five-heart win into a no-damage loss because Kaya spent the
    # fight as an animal with no weapon.
    g.ent("pad_human", DROP_COL, STAND_ROW)

    g.ent("boss_stormcrest", 37, STAND_ROW)
    g.ent("boss_exit", 36, STAND_ROW)

    # Three fixed patrols in the sky, well above the walked crest: the ridge is
    # the route and the air over it is not empty. Nothing is authored inside the
    # arena -- an add in there is a damage source the gate's sweep would have to
    # attribute to an attack, and this fight's threat is the bird.
    g.ent("enemy_flyer", 14, 5, axis="x", range=40)
    g.ent("enemy_flyer", 33, 4, axis="x", range=56)
    g.ent("enemy_flyer", 21, 7, axis="y", range=32)

    g.ent("heart", 7, CHAMBER_STAND)
    # One heart on each refuge, at the end furthest from the other: the arena has
    # no pickup you can take without leaving the floor.
    g.ent("heart", WEST_SLAB, SHELF_STAND)
    g.ent("heart", EAST_SLAB + SLAB_W - 1, SHELF_STAND)
    for (x, y) in [(3, 26), (6, 26), (9, 22), (10, 18), (9, 14),
                   (12, CREST_STAND), (16, CLEFT_TOP - 1), (17, CLEFT_TOP - 1),
                   (24, CREST_STAND), (28, CREST_STAND), (35, CREST_STAND),
                   (39, CREST_STAND), (27, STAND_ROW), (47, STAND_ROW),
                   (WEST_SLAB + 3, SHELF_STAND), (EAST_SLAB + 1, SHELF_STAND)]:
        g.ent("gem", x, y)

    # ---------------------------------------------------- the intended solution
    # Human for the two steps to the pad, bird for all of the mountain, human
    # again on the arena floor. Every hop is short on purpose (ADR 005: "a hop
    # that needs a big budget is a hop that is too coarse").
    g.route("spawn", "pad_bird", form="human")        # three steps along the shelter
    g.route("pad_bird", "draft_foot", form="bird")    # out of the doorway into the shaft
    g.route("draft_foot", "draft_mid", form="bird")   # into the updraft, C -> A
    g.route("draft_mid", "crest", form="bird")        # out of the mouth onto the ridge
    g.route("crest", "ridge", form="bird")            # over the cleft
    g.route("ridge", "lip", form="bird")              # east along the ridge, A -> B
    g.route("lip", "pad_human", form="bird")          # down the light-shaft, B -> D
    # And there the prover stops. `boss_exit` is placed by
    # Level.on_boss_defeated() and by nothing else, so this last hop is PARTIAL
    # by design and belongs to tools/bossgate.sh check 5 -- exactly as jungle_5's
    # and ruins_5's do.
    g.route("pad_human", "boss_exit", form="human")
    return g, k


# ======================================================================
# THE STORMCREST'S SHEET.
#
# 18 frames of 48x48: six poses (roost, two flap beats, stoop, dive, crash) for
# each of the three phases, named <pose>_p1/_p2/_p3 in
# data/enemies/stormcrest.json exactly as the Warden's and the Maw's are. The
# silhouette is a crested storm-bird -- hooked beak, a comb of quills over the
# skull, four-fingered pinions, a long forked tail -- drawn out of the `metal`,
# `stone`, `gold` and `ember` ramps so it reads against heights rock in the air
# and on the ground.
#
# The 40x46 collision box sits at (4, 2) in the frame. 46 tall is not a style
# choice: a body standing on a refuge slab has its chest at y=383..395 and a
# 46 px body standing on the arena floor spans 386..432, so the blade reaches
# the Stormcrest from the slab AND its body reaches her there. The wings sweep
# through the full height of the box on both flap beats for the other half of
# the same fairness: a hurtbox that is mostly empty air still hurts you.
# ======================================================================
FRAME = 48
BOX_W, BOX_H = 40, 46
BOX_OX, BOX_OY = 4, 2


def _crest_cells():
    """The 18 frames, as ASCII rows in tools/art/palette.py's char vocabulary.

    Six pose functions, each drawn three times with a different ramp set. They
    are written out one at a time rather than parameterised from a single
    drawing, because the first cut of this sheet WAS one parameterised drawing
    and it made an animal that filled about half its own hitbox: a 40x46 box
    around a 36x30 bird is contact damage out of thin air, and the project's own
    rule about the Maw's overhanging jaw ("a hurtbox larger than the thing that
    hurts you is the worst kind of unfair") cuts both ways. Every pose here is
    laid out against the box: crest or wingtip near y=2, talons or tail near
    y=46, and the body across the middle.
    """
    import math

    F = FRAME

    # phase -> body, trim (lit feathering), quill (primaries), eye, beak, charge
    PHASES = [
        ("a", "A", "w", "y", "A", None),   # EYRIE    slate, white primaries
        ("a", "w", "y", "o", "y", "o"),    # SQUALL   lit, gold comb and beak
        ("k", "a", "o", "r", "o", "r"),    # TEMPEST  storm-black, ember charge
    ]

    class Cell:
        def __init__(self):
            self.px = [["." for _ in range(F)] for _ in range(F)]

        def put(self, x, y, c):
            x, y = int(round(x)), int(round(y))
            if 0 <= x < F and 0 <= y < F:
                self.px[y][x] = c

        def disc(self, cx, cy, rx, ry, c):
            if rx <= 0 or ry <= 0:
                return
            for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
                for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                    if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                        self.put(x, y, c)

        def taper(self, x0, y0, x1, y1, r0, r1, c):
            """A limb: a line swept by a shrinking disc."""
            n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 2
            for i in range(n + 1):
                u = i / float(n)
                r = r0 + (r1 - r0) * u
                self.disc(x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, r, r, c)

        def pinion(self, ox, oy, ang, length, width, base, tip, lead=1.0):
            """One wing: an airfoil swept along `ang`, primaries on the outer
            third.

            Drawn as a solid shape between a leading and a trailing edge rather
            than as a fan of rays. The first cut was the fan, and four 1 px
            fingers read as a comb at 48x48 and as a smear at 400x240 — which is
            the resolution this is for. `lead` is which side is the leading edge
            (+1 or -1), so the two wings of a beat curve away from each other
            instead of both bending the same way.
            """
            px_, py_ = -math.sin(ang) * lead, math.cos(ang) * lead
            steps = int(length * 2) + 2
            for i in range(steps + 1):
                u = i / float(steps)
                cx = ox + length * u * math.cos(ang)
                cy = oy + length * u * math.sin(ang)
                half = width * (0.30 + 0.70 * math.sin(math.pi * min(1.0, u * 0.95)))
                # the chord sits behind the arm, so the leading edge is a line
                shift = half * 0.55
                for t in range(int(-half * 0.45), int(half * 1.45) + 1):
                    v = t + shift - half * 0.55
                    c = tip if (u > 0.60 and t > -half * 0.1) else base
                    self.put(cx + px_ * v, cy + py_ * v, c)
            # the arm along the leading edge: what makes it read as a wing and
            # not a leaf.
            self.taper(ox, oy, ox + length * 0.86 * math.cos(ang),
                       oy + length * 0.86 * math.sin(ang), 3.6, 1.4, base)
            # three primaries split out of the outer third
            for k in range(3):
                u = 0.66 + k * 0.11
                cx = ox + length * u * math.cos(ang)
                cy = oy + length * u * math.sin(ang)
                half = width * (0.30 + 0.70 * math.sin(math.pi * min(1.0, u * 0.95)))
                for t in range(0, int(half * 1.4)):
                    self.put(cx + px_ * (t + half * 0.1), cy + py_ * (t + half * 0.1), "k")

        def head(self, hx, hy, face, body, trim, quill, eyec, beakc, charge,
                 gape=0, tilt=0.0):
            """Skull, comb, hooked beak and eye. `face` is -1 left, +1 right."""
            self.disc(hx, hy, 6.0, 5.4, body)
            self.disc(hx - face * 1.5, hy - 1, 4.0, 3.2, trim)
            # the comb of quills, swept back away from the beak
            for i in range(6):
                a = 0.55 + i * 0.22 + tilt
                for t in range(3, 12 + (i % 2)):
                    self.put(hx - face * t * math.cos(a), hy - t * math.sin(a), quill)
            # hooked beak
            for i in range(9):
                self.put(hx + face * (5 + i), hy - 1 - gape + i // 3, beakc)
                self.put(hx + face * (5 + i), hy + 1 + gape - i // 3, beakc)
                if i < 6:
                    self.put(hx + face * (5 + i), hy - gape + i // 4, "k")
            for i in range(3):
                self.put(hx + face * (13 + i), hy + i - 1 + gape // 2, beakc)
            # the eye
            self.disc(hx + face * 1.5, hy - 1, 2.6, 2.6, "k")
            self.disc(hx + face * 1.5, hy - 1, 1.3, 1.3, eyec)
            self.put(hx + face * 1.5, hy - 2, "w")
            if charge is not None:
                for i in range(3):
                    self.put(hx - face * (4 + i * 2), hy - 8 - i, charge)

        def talons(self, x, y, c, spread=3):
            for i in range(4):
                self.put(x, y + i, c)
            for t in (-spread, 0, spread):
                self.put(x + t, y + 4, c)
                self.put(x + t, y + 5, "k")

        def ink(self):
            out = [row[:] for row in self.px]
            for y in range(F):
                for x in range(F):
                    if self.px[y][x] != ".":
                        continue
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < F and 0 <= ny < F \
                                and self.px[ny][nx] not in (".", "k"):
                            out[y][x] = "k"
                            break
            return ["".join(r) for r in out]

    def roost(ph):
        """Upright on the rock, wings folded, crest up. The vulnerable pose, and
        the one the fight opens on."""
        body, trim, quill, eyec, beakc, charge = ph
        c = Cell()
        c.taper(25, 33, 27, 42, 3.0, 2.0, trim)          # shanks
        c.taper(19, 33, 18, 42, 3.0, 2.0, trim)
        c.talons(27, 42, trim)
        c.talons(18, 42, trim)
        c.disc(23, 26, 12.0, 14.0, body)                 # the standing body
        c.disc(21, 23, 8.0, 9.0, trim)                   # breast
        # the folded wing, a long shield down the flank
        for i in range(24):
            u = i / 23.0
            c.disc(27 + 6 * u, 16 + 22 * u, 5.5 - 3.0 * u, 4.0 - 2.0 * u,
                   body if u < 0.7 else quill)
        c.taper(31, 34, 41, 45, 4.0, 1.5, body)          # tail
        c.taper(35, 36, 43, 46, 2.5, 1.0, quill)
        c.taper(20, 16, 17, 11, 5.0, 4.0, body)          # neck
        c.head(16, 10, -1, body, trim, quill, eyec, beakc, charge)
        return c.ink()

    def flap(ph, up):
        """Cruising. The two beats between them sweep the whole height of the
        box, which is the other half of making a 46 px hurtbox honest."""
        body, trim, quill, eyec, beakc, charge = ph
        c = Cell()
        sx, sy = 24.0, 27.0
        if up:
            c.pinion(sx, sy, -2.05, 24, 8.0, body, quill, -1.0)   # far wing, up-left
            c.pinion(sx + 2, sy - 1, -0.90, 27, 9.5, trim, quill, 1.0)
        else:
            c.pinion(sx, sy, 2.05, 24, 8.0, body, quill, 1.0)
            c.pinion(sx + 2, sy + 1, 0.90, 27, 9.5, trim, quill, -1.0)
        c.disc(sx - 1, sy + 2, 12.0, 9.5, body)              # the barrel body
        c.disc(sx - 4, sy + 4, 8.0, 6.0, trim)
        c.taper(sx + 8, sy + 3, 45, sy + (9 if up else 1), 5.0, 1.5, body)  # tail
        c.taper(sx + 10, sy + 5, 46, sy + (12 if up else 3), 2.5, 1.0, quill)
        for x in (18, 24):                                   # tucked legs
            c.taper(x, sy + 8, x - 2, sy + 12, 2.4, 1.4, trim)
        c.taper(sx - 8, sy - 1, 14, sy - 4, 5.5, 4.5, body)  # neck, thrust forward
        c.head(11, sy - 6, -1, body, trim, quill, eyec, beakc, charge,
               gape=1 if up else 0)
        return c.ink()

    def stoop(ph):
        """The telegraph: it stalls over a roost pad, wings back, screaming. The
        one frame the player has to read, so it is the widest silhouette."""
        body, trim, quill, eyec, beakc, charge = ph
        c = Cell()
        sx, sy = 26.0, 24.0
        c.pinion(sx, sy, -1.45, 23, 8.0, body, quill, -1.0)
        c.pinion(sx + 1, sy, -0.80, 25, 9.0, trim, quill, 1.0)
        c.disc(sx - 2, sy + 4, 11.0, 12.0, body)
        c.disc(sx - 5, sy + 3, 7.0, 7.5, trim)
        c.taper(sx + 6, sy + 12, 44, 44, 4.5, 1.5, body)
        c.taper(23, sy + 14, 21, 45, 3.0, 2.0, trim)
        c.talons(21, 41, trim, 2)
        c.taper(sx - 9, sy + 1, 16, sy + 6, 5.0, 4.2, body)
        c.head(13, sy + 8, -1, body, trim, quill, eyec, beakc, charge, gape=4)
        return c.ink()

    def dive(ph):
        """The stoop itself: a dart pointing down and forward, wings shut."""
        body, trim, quill, eyec, beakc, charge = ph
        c = Cell()
        c.pinion(30, 20, -0.95, 20, 6.0, body, quill, -1.0)       # swept hard back
        c.pinion(31, 22, -0.80, 18, 5.0, trim, quill, 1.0)
        c.taper(32, 14, 18, 36, 10.0, 8.0, body)             # the diagonal body
        c.taper(30, 16, 19, 33, 6.0, 5.0, trim)
        c.taper(35, 9, 44, 2, 5.0, 2.0, body)                # tail, straight up-right
        c.taper(37, 11, 46, 5, 2.5, 1.0, quill)
        for d in (-3, 3):                                    # trailing legs
            c.taper(28 + d, 26, 33 + d, 18, 2.4, 1.4, trim)
        c.head(15, 39, -1, body, trim, quill, eyec, beakc, charge, gape=2,
               tilt=-0.5)
        return c.ink()

    def crash(ph):
        """Roosted after the stoop: sprawled over the rock, wings half open,
        head low. This is the window, and it should look like one."""
        body, trim, quill, eyec, beakc, charge = ph
        c = Cell()
        c.pinion(25, 29, -2.75, 21, 7.5, body, quill, 1.0)       # wings thrown wide
        c.pinion(27, 29, -0.35, 21, 7.5, body, quill, -1.0)
        c.taper(20, 36, 18, 45, 3.0, 2.0, trim)              # braced legs
        c.taper(29, 36, 32, 45, 3.0, 2.0, trim)
        c.talons(18, 42, trim)
        c.talons(32, 42, trim)
        c.disc(24, 32, 13.0, 10.5, body)
        c.disc(21, 34, 8.5, 6.5, trim)
        c.taper(34, 33, 45, 40, 4.5, 1.5, body)
        c.taper(36, 35, 46, 43, 2.5, 1.0, quill)
        c.taper(16, 29, 12, 31, 5.0, 4.4, body)
        c.head(10, 32, -1, body, trim, quill, eyec, beakc, charge, gape=1)
        return c.ink()

    cells = []
    for ph in PHASES:
        cells.append(roost(ph))
        cells.append(flap(ph, True))
        cells.append(flap(ph, False))
        cells.append(stoop(ph))
        cells.append(dive(ph))
        cells.append(crash(ph))
    return cells


def write_art():
    sys.path.insert(0, os.path.dirname(HERE))
    from art import palette                                   # noqa: E402
    cells = _crest_cells()
    palette.sheet("boss_stormcrest", cells, FRAME, FRAME)
    print("boss_stormcrest.png  %d frames of %dx%d" % (len(cells), FRAME, FRAME))


def main(argv):
    if "--art" in argv:
        write_art()
        return 0
    g, k = heights_5()
    missing = HEIGHTS_CHARS.missing()
    if missing:
        print("  PALETTE  %d role(s) with no legend character: %s"
              % (len(missing), ", ".join("%s->%s" % m for m in missing)))
    for line in k.audit(strict_verbs=True):
        print(line)
    write(LEVEL_ID, g, LEVEL_NAME, music="boss")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
