# Boss difficulty: how it is measured, the Grove Warden retuned, the other four

Status: pilot (long/warden), 2026-11-19. Owner's verdict from TestFlight: "the
bosses [are] too hard" — all five. The Grove Warden is the pilot; this file is
what the next phase starts the other four from.

## The measures

All three run headless against the real fight (`--fixed-fps 60`, a few seconds
of wall clock per fight). None of them is a gate; the boss gate (ADR 005 §4) is
unchanged and still has to pass.

**1. The sloppy player** — `tools/bossgate.sh --sloppy[=profile]`
(`KAYA_BOSSGATE_SEEDS`, default 20). The boss's own strategy pen is the brain;
`tests/integration/boss_sloppy_hands.gd` sits between it and the buttons and
adds what a thumb on glass adds. Profiles are in `tools/bossgate/sloppy.json`:

| profile | reaction delay | attack taps lost | jump late by | stick drop-outs |
|---|---|---|---|---|
| clean | 0 | 0 | 0 | none |
| careful (keyboard) | 8–12 f (133–200 ms) | 5 % | 0–3 f | 0.2 /s, 3–6 f |
| **phone** (the bar) | 12–20 f (200–333 ms) | 15 % | 0–6 f | 0.5 /s, 4–10 f |

It prints wins, deaths, hits taken per fight, and every hit attributed to the
boss's **body**, an **add** (any other enemy) or a **shot**, and to the phase it
landed in. Each fight is seeded, so a seed is repeatable up to the loot rolls
`Enemy._drop_loot()` makes with an unseeded RNG.

Why not "replay the winning tape with jitter", as first proposed: the boss
tracks Kaya, so one late frame desynchronises a blind tape and every frame after
it is a fight the tape was never written for. Measured: the jittered tape is a
blind player, and loses whatever the boss's tuning. The pen with slow hands
keeps reacting to the fight actually in front of it.

What it does NOT model, and so how to read it: the pen knows the plan perfectly
and never learns; a first-time human knows nothing and learns fast. And the pen
does not adapt its timing to its own lag, which a person does. (An attempt to
let it — shifting its dodge lead and standoff by the mean delay — made it
*worse*, by pushing the standoff out of blade range; it was removed.) So read
the phone number as "how forgiving is this fight of a late thumb", compare it
between bosses and before/after, and do not read it as a literal win rate.
**Target: phone ≥ 75 %, careful ≥ 95 %**, which with a checkpoint at the door is
a first-time player through in about three attempts.

**2. The tells** — `tools/bossgate.sh --tells[=profile]` (`KAYA_BOSSGATE_SEEDS`
fights, default 5). Kaya cannot be hurt, so the fight runs all its phases.
`tests/integration/boss_tell_probe.gd` logs every entry into a WINDUP or SPRAY
pose: how long the pose is held, and how many frames after it began the attack
first overlapped Kaya — the reaction window. Also threats live at once (shots in
flight plus non-boss enemies in the arena). Anything under ~24 f (0.4 s) is
unreadable on a phone.

**3. The boss gate** as before, plus the strategy tape's hearts left.

## The Grove Warden, before and after

Before = commit c58bcb4. After = this branch. Phone and careful are 40 fights.

| | before | after |
|---|---|---|
| health | 18 (phases at 12 / 6) | 14 (phases at 10 / 5) |
| sloppy **phone** | **0 / 40 won**, 5.0 hits a fight | **36 / 40 won (90 %)**, 3.5 hits |
| sloppy careful | 0 / 40 | 39 / 40 (98 %), 1.5 hits |
| sloppy clean (the pen, no lag) | 0 / 40 (5.1 hits) | 40 / 40, 1.0 hit |
| phone hits by cause | body 74, add 27, shot 99 | body 38, add 11, shot 92 |
| strategy tape (boss gate) | 40.1 s, **3 hearts left** (low 3) | 19.9 s, **5 hearts left** (low 4) |
| pen's record search | 738 plans tried, **no win found** — the committed tape was the only known win | wins on its first plan |
| slam tell (WINDUP pose) | 28 f (0.47 s), no sound | 42 / 39 / 36 f (0.70 / 0.65 / 0.60 s), growl + dust |
| spray tell | 25 f (0.42 s), **same pose as the slam**, no sound | 42 f (0.70 s), green pulse, hiss, shimmer |
| tell → first contact (phone, min / median) | LEAP 28 / 105 f, FURY spray **1** / 97 f, FURY slam **0** / 72 f | STOMP 74 / 85, LEAP 83 / 111, FURY spray 114 / 120, FURY slam 97 / 106 |
| threats live at once (mean / max) | LEAP 3.9 / 6, FURY 4.6 / 9 | LEAP 0.7 / 4, FURY 0.7 / 3 |
| unhittable phone fight lasts | 91 s | 23 s |
| hearts in arena | 0 (a 6 % beetle drop) | one at each phase break, on Kaya's side |
| a death costs | the whole level (13.7 s of proof tape, 8 enemies) | the arena door (a checkpoint — see below) |

What the measurement found, in the order it was fixed:

1. **Beetles were the biggest killer of the clean pen** (122 of 202 hits). LEAP
   called two per slam to a garrison of four, and they were spawned at the floor
   ends — which are the only floor the Warden's body cannot reach, i.e. where a
   player goes to breathe. Now one per slam, at most two, spawned at the end
   *away* from Kaya, none in FURY, and the garrison scatters at a phase break.
2. **The body.** The Warden walked into her (42 px of body she cannot jump) and
   every touch was a heart. Now it **looms** (`loom_gap`): it stops advancing
   24 px short and lets the slam be the threat. And its body only hurts in the
   leap and the landing (`contact.hurts_in`); touching it otherwise is a shove,
   no heart. Phone body hits 74 → 38.
3. **The shockwave crossed the whole arena** from anywhere (life 1.6 s). Now
   0.9 / 1.0 / 1.1 s, so the floor ends are somewhere to run *to*, not only a
   frame-perfect jump.
4. **FURY was where 102 of 169 phone hits landed** (LEAP's garrison still on the
   floor under a 1.2 s slam and a 5-spore spray). Slam 1.2 → 2.0 s, spray 5 → 3
   spores, every 2.2 s, walk 78 → 58.
5. **Tells**, as in the table. The spray now looks and sounds different from the
   slam. `windup_time` and `spray_windup` are per-phase data (were code constants).
6. **Phase break**: 1.5 s stagger, a screen shake, and a heart dropped at the end
   of the floor on Kaya's side of the Warden — never its far side, which she
   cannot reach (the first version dropped it at the far end and the sloppy
   player walked into the body going for it).

Still a boss: three phases with their own look and move set, 14 health, a
shockwave that has to be jumped or outrun, beetles in LEAP, spores in FURY. The
pen ends on five hearts only because it has no lag; the phone player takes 3.5
hits a fight against five hearts and the two the phase breaks drop.

## The checkpoint

`{"type": "checkpoint", "x": 39, "y": 5}` in `levels/jungle_5.json`, from
`tools/build_levels.py`: the west end of the lip she lands on from the branch
and steps off into the arena drop, so it is touched on every way into the fight.
**No shim was needed**: `tools/reachability.py`, `tools/prove.sh` and the boss
gate all ignore an entity type they do not know, and the proof tape changed only
its `source_sha`. Until `long/engine` lands, `Level.spawn_entity()` prints
`Level: unknown entity type 'checkpoint'` as a warning and spawns nothing.

What `long/engine`'s checkpoint must do here for the numbers above to mean
anything: on a respawn at (39,5) the Warden must be back at full health in phase
0 (`Enemy.respawn()` → `boss_grove.gd`'s `on_respawn()` already does that), its
beetles and shots gone, the camera unlocked until she drops in again, and Kaya
at full hearts (as a level start gives her today).

## The other four: measured, and what to change

Measured on this branch, their code and data untouched. Phone and careful are
40 fights each with each boss's own pen at its default plan (their tapes record
no plan; the defaults win clean in all four). Tells are 8 phone fights.

| | Tide Maw (ruins_5) | Stormcrest (heights_5) | Brood Queen (deeps_5) | Obsidian Heart (nest_5) |
|---|---|---|---|---|
| health / phases | 18 / 12, 6 | 12 / 8, 4 | 12 / 8, 4 | 24 / 16, 8 |
| clean pen ends on (hearts) | 3 | 5 | 1 | 2 |
| clean (pen, no lag) | 40/40, 2.0 hits | 40/40, 0 hits | 40/40, 4.0 hits | 40/40, 3.0 hits |
| careful | **0 / 40** | 18 / 40 (45 %) | 1 / 40 (2 %) | 2 / 40 (5 %) |
| **phone** | **0 / 40**, 6.0 hits | **0 / 40**, 5.6 | **0 / 40**, 6.1 | **0 / 40**, 5.0 |
| phone hits: body / add / shot | 98 / 0 / 142 | 72 / 0 / 151 | 50 / 63 / 131 | 71 / 0 / 130 |
| slam tell | 28 f | 34 f | 38 f | 28 f (63 f opening shed) |
| spray tell | **25 f, slam pose** | **25 f, slam pose** | **25 f, slam pose** | **25 f, slam pose** |
| worst tell → contact (min f) | slam 28 | slam **0** (TEMPEST) | slam 13 (SWARM) | **LAND>WINDUP 0 / median 8** |
| threats live, max | 6 | 5 | **10** | **11** |
| hearts in arena | 2 | 2 | 2 | 2 |
| a death costs | whole level (10.8 s tape) | whole level (8.5 s) | whole level (6.2 s) | whole level (7.8 s) |

Proposed, in order of what the measurement says hurts most. Each wants the same
loop as the Warden: change data, run `--sloppy=phone` 40 seeds, look at the cause
column, repeat; then `--record` and the gate.

- **All four**
  - Checkpoint at the arena door.
  - Spray tell 0.4 s → 0.7 s, with its own sound and look. Today all four use
    `set_anim("windup")` for both attacks, held 25 f.
  - The phase break (stagger + a heart on Kaya's side). Their arenas already
    hold two placed hearts; the pens never fetch them, which the Warden's
    `fetch_hearts` now does — port it.
  - The contact rule and the loom: body hits are 30–40 % of every phone hit on
    all four.
  - The mechanisms above live in `src/enemies/boss_grove.gd` only. The four
    bosses are copies of its state machine (`St` enum, WINDUP/SPRAY, the 0.45 /
    0.4 constants), so the next phase should hoist tells, phase break, contact
    and loom into a shared boss base rather than paste them four times.
- **Tide Maw** — the hardest: 0 % even on careful hands. Health 18 → 14; bore
  life 1.6 s → ~1.0 s (the same arena-crossing problem as the shockwave); FLOOD
  and UNDERTOW spray 5 → 3; slam interval 1.5 s in UNDERTOW → ~2.0 s.
- **Stormcrest** — the dive reaches her in 0 f in TEMPEST: give the dive a
  windup that cannot be cut short; volleys 4 / 5 → 3; roost_time (its
  vulnerable window) 2.4 / 2.2 / 2.0 → ~3.0 s each.
- **Brood Queen** — adds: max threats 10 in HATCH, 63–106 add hits. max_adds
  3 → 2, clear on phase break, spawn away from Kaya. In the dark the tell is the
  only thing visible, so it matters doubly here.
- **Obsidian Heart** — health 24 → ~16. LAND→WINDUP chains a second slam onto
  the landing with 0–8 f between: put a floor under it (a minimum recovery
  before the next windup). 11 threats at once in INVERTED / MOLTEN: cap the shed
  volley.

## Reproducing

```
tools/bossgate.sh --sloppy=phone                         # Warden, 20 fights
KAYA_BOSSGATE_SEEDS=40 tools/bossgate.sh --sloppy=careful
tools/bossgate.sh --tells=phone
KAYA_BOSSGATE_LEVEL=ruins_5 KAYA_BOSSGATE_BOSS=tide_maw tools/bossgate.sh --sloppy=phone
KAYA_BOSSGATE_TRACE=1 KAYA_BOSSGATE_SEEDS=1 tools/bossgate.sh --sloppy=phone   # every hit, with context
tools/shot.sh --seq=tools/seq/warden_tells.json          # the tells, on their own frames
```

Before numbers were taken in a detached worktree of c58bcb4 with only the
measurement files copied in (`boss_sloppy_hands.gd`, `boss_tell_probe.gd`,
`boss_gate_tape.gd`, `bossgate_runner.gd`, `sloppy.json`, `bossgate.sh`,
`dev_capture.gd`).
