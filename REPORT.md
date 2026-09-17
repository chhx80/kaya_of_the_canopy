# M1 — the Boss Gate

Branch `wave1/bossgate`. Implements ADR 005 §4 against **THE GROVE WARDEN** in
`jungle_5`, headless.

**Headline: the Grove Warden passes the fairness sweep as ADR 005 specifies it,
but only because of six tiles it cannot reach — and Kaya cannot reach them
either.** Details in *Findings* below. I did not weaken the check, and I did not
touch the boss.

---

## What I built

| File | What it is |
|---|---|
| `tools/bossgate.sh` | the runner. Exit code is the gate. |
| `tools/bossgate/bossgate.tscn` + `bossgate_runner.gd` | headless entry point; boots the real game and hands over to the checks |
| `tests/integration/boss_gate_checks.gd` | the fairness sweep and the other four checks |
| `tests/integration/boss_gate_tape.gd` | the strategy-tape format, `source_sha` staleness, and synthetic-input replay |
| `tests/integration/boss_gate_strategy.gd` | the scripted controller that *records* a tape, plus two diagnostics |
| `tests/integration/boss_gate_smoke.gd` | a 13-second in-suite case for `tools/itest.sh` (not wired in — see *Assumptions*) |

Nothing outside `tools/bossgate/**`, `tools/bossgate.sh` and
`tests/integration/boss_gate_*.gd` is modified. `git status` on this branch
shows only those paths.

### 1. The fairness sweep (built first, as instructed)

For every phase, for every standable tile in the arena, Kaya is pinned on the
tile and the real fight runs until every attack that phase makes has fired
twice — then keeps running until the things it threw are gone.

Three decisions are worth arguing with, because they are what the check means:

**Attacks are discovered, not declared.** A discovery pass watches the fight
from three spread-out tiles and records the boss state-transition on the frame
each damage source appeared. `AIR>LAND` and `SPRAY>WALK` are names the sweep
worked out, not names I typed. A boss with no `st` at all still gets one lumped
attack. If a phase produces no attack, that is a **failure**, not a pass —
silence is not a clean sheet.

**"Connects" is the game's own hit test, observed from outside.** Not a
coverage model. A tracked projectile that leaves the tree while its last sampled
rect — grown by one frame of its own travel — covers Kaya's rect *is* the
projectile resolving on her. Invulnerability is zeroed every frame on purpose:
i-frames are a consolation prize, not a dodge, and the question is whether the
attack reaches the tile.

**The boss behaves naturally.** It chases. I considered pinning it at sampled
positions to measure pure coverage and rejected it: that is modelling again, and
the situation a player is actually in is "it is coming for me". The consequence
is that the sweep conflates *coverage* with *pursuit*, which matters for reading
the result — see *Findings*. The `reach` column exists to separate the two: it
is the greatest distance from the boss at which that attack was ever seen to
connect.

A tile where an attack **never fired** is counted as neither safe nor hit; it is
a hole, and it fails the gate with its own message. That check caught two real
holes in my own sweep: rim tiles whose standing position put Kaya's body on the
screen above (flipping the camera and freezing the boss), and a sample that
stopped the instant the last shockwave *spawned*, before it could arrive.

### 2–5. The rest

- **defeatable / survivable** — replay a frozen strategy tape and require the
  kill inside 90 s, from full health, with ≥1 heart left.
- **arena bound** — measured on every frame of every one of the 84 sweep
  samples: `boss.pos.x` inside `arena_min`/`arena_max` and the boss still on its
  home screen. 0 escapes.
- **it ends** — deliberately *not* gated on the tape. The Warden is put down
  directly, then Kaya walks out of the arena on foot through the real
  `boss_exit`, and the check is that the level reports complete. An "it ends"
  that can only run on days checks 1 and 2 pass tells you nothing on the day
  they fail.

---

## How to verify it

```bash
tools/bossgate.sh            # the gate, full sweep. ~32 s. Currently exits 1.
tools/bossgate.sh --quick    # every 4th tile. ~10 s. Smoke, not proof.
tools/bossgate.sh --record   # search for a strategy tape (~4 min, currently fails)

tools/test.sh                # 129 tests, 8489 assertions, 0 failed
tools/validate.sh            # validate: OK
tools/itest.sh               # integration: 273 checks, ALL PASSED
```

The two diagnostics that produced the numbers quoted below:

```bash
source tools/env.sh
KAYA_BOSSGATE_MODE=probe "$GODOT" --headless --fixed-fps 60 --path . \
  res://tools/bossgate/bossgate.tscn                       # blade damage vs distance
KAYA_BOSSGATE_MODE=probe KAYA_BOSSGATE_PROBE=adds "$GODOT" --headless --fixed-fps 60 \
  --path . res://tools/bossgate/bossgate.tscn              # beetles alive over time
```

The in-suite case, timed the way `itest.sh` would pay for it (no `--fixed-fps`):

```bash
KAYA_BOSSGATE_MODE=smoke "$GODOT" --headless --path . res://tools/bossgate/bossgate.tscn
# boss gate smoke: 8 checks, ALL PASSED      12.8 s wall
```

**Why `--fixed-fps 60`.** Plain `--headless` runs the main loop at wall-clock
speed: 2000 physics frames took 33.2 s. With `--fixed-fps 60` the same 2000
frames took 0.04 s. The physics delta stays exactly 1/60 either way, so the
simulation is unchanged — the loop just stops sleeping. The full sweep is about
45 minutes of simulated fight and is only affordable because of this.

**Determinism**: two consecutive full runs produce byte-identical verdict lines.

---

## Current verdict

```
BOSS GATE  THE GROVE WARDEN in jungle_5
  arena (1, 1)   standable tiles: 28   phases: 3
  phase 0 STOMP  AIR>LAND     56 instances over 28 tiles | hit 22, missed 6, never fired 0 | reach  63 px
  phase 1 LEAP   AIR>LAND     56 instances over 28 tiles | hit 22, missed 6, never fired 0 | reach  85 px
  phase 2 FURY   AIR>LAND     84 instances over 28 tiles | hit 22, missed 6, never fired 0 | reach 102 px
  phase 2 FURY   SPRAY>WALK   56 instances over 28 tiles | hit 12, missed 16, never fired 0 | reach  13 px
  refuges: 10 reachable from the arena floor, 6 not
  the boss body reached 22 of the 28 swept tiles
  it ends: walked out through the gate after 174 frames (2.9 s)
  FAIL  defeatable :: strategy tape res://tools/bossgate/tapes/boss_grove.json: no tape
boss gate: 17 checks, 1 FAILED
```

| Check | Verdict |
|---|---|
| 3. fair | **PASS**, with a serious caveat — read Finding 1 |
| 4. arena bound | **PASS** — 0 escapes over 84 samples |
| 5. it ends | **PASS** — she walks out in 2.9 s |
| 1. defeatable | **UNVERIFIED** — I could not author a tape |
| 2. survivable | **UNVERIFIED** — same |

---

## Findings (reported, not fixed — `boss_grove.gd` and its JSON are not mine)

### Finding 1 — the slam's only dodge window is a ledge Kaya cannot get back onto

The slam shockwave (`AIR>LAND`) misses exactly six tiles, in every phase:
`(30,21) (31,21) (32,21) (42,21) (43,21) (44,21)`. Those are the two one-way
platforms. Every one of the 22 floor tiles is hit.

Measured, not reasoned:

- The platforms sit **96 px** above the arena floor. Kaya's apex as the human
  form, measured by jumping her with the shipping form code, is **46 px**. The
  frog's measured apex (`tools/validate.sh` prints it) is 5.34 tiles ≈ 85 px,
  and there is no transform pad in the arena anyway. A scripted hop tried 6
  launch tiles × 5 run-up lengths from the floor and never landed on one.
- From a platform, six seconds of continuous blade throws never damaged the
  Warden. The blade leaves level from her chest at y≈325 and the Warden's
  hitbox is y 390–416; it flies over.

So the sweep's answer is literally "yes, there is a tile where the slam does not
connect", and the honest answer is "yes, on a ledge you can only be on before
the fight starts, and from which you cannot fight". Once Kaya is on the arena
floor — which she must be, to do any damage at all — **there is no standable
tile where the slam does not connect**. The only remaining answer to it is a
timed jump.

I report this as a NOTE rather than a failure because ADR 005's check 3 does not
ask it, and ADR 005 is a binding interface contract I was told not to redesign.
If the other seven of us agree, the natural amendment is: *a safe tile must also
be reachable from the arena floor.* The machinery to enforce that is already
written and already runs (`_report_refuge_reachability`); it is one `check()`
away from being a gate.

### Finding 2 — the slam covers the floor by pursuit, not by reach

The `reach` column says the slam was never observed to connect further than
63/85/102 px from where the boss launched it, against a theoretical travel of
211/240/269 px (`shockwave_speed` × `life` 1.6 s). It does not cover the arena.
It does not need to: the Warden walks to you first. Any reader of this gate
should hold the two apart — an attack can fail check 3 because it is too big, or
because the boss is too good at following you, and the fix is different.

The spore spray, by contrast, is genuinely local: `reach 13 px`, and it misses 16
of 28 tiles. It is a fair attack by any reading.

### Finding 3 — LEAP fills the arena with beetles and never empties it

Measured with the adds probe, Kaya parked out of reach so the only driver is the
boss's own slam cycle:

```
phase 0 STOMP  slam every 2.4s, 0 add(s) per slam | live beetles 5s:0  10s:0  15s:0  20s:0  25s:0  30s:0
phase 1 LEAP   slam every 1.7s, 2 add(s) per slam | live beetles 5s:2  10s:4  15s:8  20s:10 25s:14 30s:16
phase 2 FURY   slam every 1.2s, 1 add(s) per slam | live beetles 5s:1  10s:2  15s:3  20s:4  25s:6  30s:7
```

Sixteen walkers after thirty seconds of LEAP, in an arena 22 tiles wide, with no
cap and nothing that removes them. `spawn_adds` fires from `_land()` on every
slam. Every losing run of my strategy search died in that crowd: in phase STOMP
Kaya took one hit in 28 seconds; once LEAP opened she lost four hearts in four
and a half.

This is not one of ADR 005's five checks and the gate does not fail on it. It is
the most likely reason checks 1 and 2 are unverified.

---

## What I could NOT verify — stated plainly

**Checks 1 (defeatable) and 2 (survivable) are unverified. There is no strategy
tape, because I could not produce one that wins.**

What I actually did: `tools/bossgate.sh --record` runs a scripted controller
against the real fight and writes down the buttons. The controller is
parameterised (standoff band, dodge lead, jump hold, under-pass trigger and
commitment, beetle handling, hop cycle, throw range — thirteen knobs) and the
runner walks them by greedy coordinate descent from four structurally different
openings, keeping a tape only if it kills the Warden with a heart to spare.

**696 strategies were tried. The best left the Warden on 9 of 18 health with
Kaya dead and 0 hearts.** No tape was written, because a tape that does not win
is not a proof.

What that does and does not mean:

- It does **not** mean the Grove Warden is unbeatable. My controller has no aim,
  no memory of the boss's cycle, one fixed opening, and no model of the arena
  beyond two walls. A human is very probably better than it.
- It does mean that no simple reactive strategy I could build gets past half the
  fight, and the measurements above say where it comes apart.
- Checks 1 and 2 will start working the moment anyone lands a winning tape at
  `tools/bossgate/tapes/boss_grove.json`; the replay, the time bound, the heart
  bound and the staleness rule are all written and exercised.

Also not verified:

- **Check 4 is only half done.** I measured the boss staying inside
  `arena_min`/`arena_max` and on its home screen, on every frame of every
  sample. ADR 005's other half — "the prover runs over the arena in each phase
  configuration" — needs `tools/solver/**`, which I do not own and which does
  not exist on this branch.
- **Whether the six platform refuges can be reached on the way *into* the
  arena.** The arena screen is open above them (rows 15–20 at those columns are
  empty), so falling in from screen (1,0) probably lands there, but that is a
  route question and belongs to the Route Prover. I measured only "not from the
  arena floor".
- **No screenshot.** The definition of done asks for one; this feature is a
  headless gate and renders nothing. `shots/` is also not mine.
- **`CHANGELOG.md` not updated** — not my file, and eight branches editing it
  is a merge conflict. Suggested entry:
  `- Boss Gate (ADR 005 §4): fairness sweep, arena bound and it-ends run against the Grove Warden headless via tools/bossgate.sh.`

---

## Assumptions I made about other agents' work

1. **`tools/itest.sh` stays as it is on this branch**, so my in-suite case is
   *not* wired into `tests/integration/integration_tests.gd` — I do not own that
   file. `tests/integration/boss_gate_smoke.gd` is self-contained and carries
   the exact two-part patch in its header comment. It costs 12.8 s at wall-clock
   speed, against the suite's current 59 s and its 240 s bound.
2. **`itest.sh` will move to `--headless`** (an M1 task per the plan). If
   whoever owns it also adds `--fixed-fps 60`, the *whole* existing suite gets
   dramatically faster at identical simulation, and the full fairness sweep
   becomes affordable in-suite. Measured: 2000 physics frames, 33.2 s → 0.04 s.
   I recommend it, and I did not do it.
3. **Strategy tapes live at `tools/bossgate/tapes/<boss_id>.json`**, not beside
   the route tapes in `levels/`. I do not own `levels/`. The format mirrors ADR
   005's route tape — `{"boss", "level", "fps": 60, "source_sha", "frames":
   [{"n", "a"}]}` — and `source_sha` hashes the level JSON *and* the boss JSON,
   because either one moving invalidates the fight. Stale fails, it does not
   warn. If the Route Prover author wants tapes unified under `levels/`, the
   path is a single variable (`tape_path`).
4. **`data/enemies/boss_grove.json` and `src/enemies/boss_grove.gd` are
   unchanged by anyone else in wave 1.** The sweep reads the boss's `st`,
   `phase`, `arena_min`, `arena_max` and calls `_set_phase` to stage a phase; it
   writes nothing except staging. If the Warden's state machine is renumbered,
   `STATE_NAMES` in `boss_gate_checks.gd` needs the same edit — the sweep still
   *works* without it, the attacks are just named `st3>st4`.
5. **`levels/jungle_5.json` keeps its `boss_grove` and `boss_exit` entities and
   its arena on screen (1,1).** Everything else — arena bounds, floor, platforms
   — is discovered at runtime, so the gate follows the level if it is re-cut.
6. **`tools/env.sh` in a worktree points at the main checkout.** Mine did
   (`PROJECT_ROOT=/Users/christianheuer/git/jungle-project`), which means every
   `tools/*.sh` would have run against `main` instead of this branch. I
   repointed it at this worktree. It is gitignored, so nothing is committed —
   but the other seven of us should check the same thing before quoting a green
   gate.
