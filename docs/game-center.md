# Game Center achievements

Five achievements, one per world, each earned by clearing that world's boss
level. The definitions live in `data/achievements.json`; the game code in
`src/core/achievements.gd` (with the pure logic in `achievement_book.gd`); the
native plugin in `ios/plugins/` (see its README for provenance and licence).

## What you set up in App Store Connect

The game cannot create achievements; Apple only accepts ones registered for the
app. Until they exist, reports from the game are rejected and nothing appears.

1. **Developer portal**, Identifiers, `com.cateira.kayaofthecanopy`: make sure
   *Game Center* is checked. (Xcode Cloud's automatic signing usually does this
   from the entitlement; check it once.)
2. **App Store Connect**, the app, *Features* tab, *Game Center*: enable it.
3. Add each achievement below. The **Achievement ID must match exactly**; it is
   the only thing the game sends.
   - *Hidden*: No. *Achievable more than once*: No.
   - Localization: English, with the name and both descriptions below.
   - Image: `export/achievements/<Achievement ID>.png` (1024x1024, flattened RGB).
4. In the app version you submit, add the achievements under the *Game Center*
   section, or they ship disabled.
5. To test before release: sign into Game Center on the iPhone with a
   **sandbox** account (Settings, Game Center, or the account Xcode/TestFlight
   uses), install the TestFlight build, beat a boss.

| Achievement ID | Reference name | Points | Name | Pre-earned description | Earned description |
|---|---|---|---|---|---|
| `com.cateira.kayaofthecanopy.world1` | World 1 | 20 | Warden Felled | Defeat the Grove Warden and clear the Canopy Trail. | You defeated the Grove Warden and cleared the Canopy Trail. |
| `com.cateira.kayaofthecanopy.world2` | World 2 | 30 | Tide Turned | Defeat the Tide Maw and clear the Sunken Ruins. | You defeated the Tide Maw and cleared the Sunken Ruins. |
| `com.cateira.kayaofthecanopy.world3` | World 3 | 40 | Storm Stilled | Defeat the Stormcrest and clear the Thermal Heights. | You defeated the Stormcrest and cleared the Thermal Heights. |
| `com.cateira.kayaofthecanopy.world4` | World 4 | 50 | Queen Toppled | Defeat the Brood Queen and clear the Termite Deeps. | You defeated the Brood Queen and cleared the Termite Deeps. |
| `com.cateira.kayaofthecanopy.world5` | World 5 | 60 | Heart of Glass | Defeat the Obsidian Heart and clear the Obsidian Nest. | You defeated the Obsidian Heart and cleared the Obsidian Nest. |

Points rise with the worlds' difficulty and total 200 of the 1,000 Apple allows,
leaving room for later achievements.

## How the game reports them

- Signs the player in to Game Center at launch. A player who declines or is
  offline loses nothing: unlocks are recorded in the save (their own section,
  kept across NEW GAME) and reported at the next successful sign-in.
- Every sign-in re-reports every unlocked achievement. The plugin's result does
  not say which achievement it answers, so matching results to requests is not
  possible; re-reporting a completed achievement is a no-op in GameKit, so this
  is safe and nothing earned offline is lost.
- The completion banner shows once: the first time an achievement reaches Game
  Center. A boss beaten before achievements existed earns its achievement on the
  next launch, silently.
- On desktop and in tests there is no Game Center; the same code runs with no
  backend, and `tests/integration/integration_tests.gd` drives it with a fake
  that has the plugin's exact surface.

## Regenerating the images

`$PYVENV tools/art/achievement_art.py` (they are built from the boss sprites,
so regenerate them after boss art changes).
