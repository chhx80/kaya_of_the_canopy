# Shipping Kaya of the Canopy

Everything is driven by `export_presets.cfg` (committed on purpose, so a build is
reproducible from a clean checkout) and the scripts in `tools/`.

## Targets and current status

| Target | Script | Status on this machine |
|---|---|---|
| **Web** | `tools/export_web.sh` | ✅ builds — `build/web/` (PWA enabled, ~40 MB wasm) |
| **macOS** | `tools/export_macos.sh` | ✅ builds — `build/macos/KayaOfTheCanopy.zip`, verified by `tools/smoke_build.sh` |
| **macOS playtest** | `tools/export_playtest.sh` | ✅ builds — same game plus the capture harness, for driving a *packaged* build |
| **Android** | `tools/export_android.sh` | ⛔ blocked — no JDK and no Android SDK installed |
| **iOS** | `tools/export_ios.sh` | ⛔ blocked — Xcode is present, but `app_store_team_id` is account-specific and deliberately not committed |

## Prerequisites

### Local toolchain
Every script sources `tools/env.sh`, which is gitignored because it holds
absolute paths. Copy `tools/env.sh.example` to `tools/env.sh` and point it at
your Godot binary and a Python 3 venv with Pillow installed.

### Export templates
Both the editor and the headless exporter need the 4.7.2 templates in
`~/Library/Application Support/Godot/export_templates/4.7.2.stable/`. Install with:

```
curl -L -o templates.tpz \
  https://github.com/godotengine/godot/releases/download/4.7.2-stable/Godot_v4.7.2-stable_export_templates.tpz
unzip -q templates.tpz -d tpl
mkdir -p "$HOME/Library/Application Support/Godot/export_templates/4.7.2.stable"
cp tpl/templates/* "$HOME/Library/Application Support/Godot/export_templates/4.7.2.stable/"
```

### Android
1. JDK 17 — `brew install --cask temurin@17`
2. Android SDK with `build-tools;34.0.0` and `platform-tools`; export `ANDROID_HOME`.
3. A release keystore, referenced from Godot's editor settings or the
   `GODOT_ANDROID_KEYSTORE*` environment variables listed in the script.
4. `tools/export_android.sh release`

The preset ships `arm64-v8a` and `x86_64` only — armeabi-v7a is off because a
32-bit build is no longer accepted by Play for new apps.

### iOS — full walkthrough

**1. Sign Xcode into your developer account.**
Xcode ▸ Settings ▸ Accounts ▸ **+** ▸ Apple ID. After it syncs, select the team
and click *Manage Certificates…* ▸ **+** ▸ *Apple Development* so a signing
certificate lands in your keychain. Verify with:

```
security find-identity -v -p codesigning     # expect at least one identity
```

**2. Find your Team ID** — ten characters like `A1B2C3D4E5`. Either
appleid → [developer.apple.com/account](https://developer.apple.com/account) ▸
Membership details ▸ Team ID, or read it from the certificate name printed by
the command above.

**3. Put it in the preset.** In `export_presets.cfg`, under `[preset.3.options]`:

```
application/app_store_team_id="A1B2C3D4E5"
```

It is deliberately blank in the repo because it is account-specific.
`tools/export_ios.sh` refuses to run while it is empty rather than emitting an
Xcode project that cannot sign.

**4. Export.**

```
tools/export_ios.sh          # writes build/ios/KayaOfTheCanopy.xcodeproj
```

**5. In Xcode:** open that project, select the *KayaOfTheCanopy* target ▸
Signing & Capabilities ▸ tick **Automatically manage signing** and pick your
team. Xcode registers the bundle id `com.cateira.kayaofthecanopy` with your
account on first build. Change it in the preset first if you want a different
one — it must be unique across the App Store.

**6. Run on a device** (⌘R with an iPhone attached) before anything else. This
is the first time the game will have been played on a touchscreen.

**7. Ship it.** Product ▸ **Archive** ▸ Distribute App ▸ *TestFlight & App
Store*. Then in App Store Connect create the app record (same bundle id), and
the build appears under TestFlight within ~15 minutes of processing.

#### App Store Connect needs, beyond the build
- **Screenshots** at 6.7" (1290×2796) and 13" iPad (2064×2752). `shots/` has
  the raw 400×240 captures; they need upscaling and framing to those exact sizes.
- **Privacy answers**: "Data Not Collected" across the board. `export/PrivacyInfo.xcprivacy`
  already declares this, and the game makes no network calls.
- **Age rating**: cartoon fantasy violence, infrequent/mild.
- **Export compliance**: no encryption beyond Apple's own — answer "No" to the
  ITSAppUsesNonExemptEncryption question.

`min_ios_version` is **15.0**. Godot rejects anything below 14 because of its
Metal requirement, even though this game runs on the compatibility renderer.
`targeted_device_family=2` means iPhone **and** iPad.

#### Verified on the simulator
`tools/export_ios.sh` was run end to end, the Xcode project compiled clean
(`BUILD SUCCEEDED`), and the game was installed and launched on an iPhone 16 Pro
simulator — landscape, touch overlay auto-enabled, correct bundle id, version
and icons. Screenshot: `shots/35_ios_simulator.png`.

Note for Apple Silicon Macs: Godot's iOS template ships a simulator slice
containing **x86_64 only**, so a simulator build needs `ARCHS=x86_64` (Rosetta)
or you go straight to a physical device. The device slice is genuine arm64 and
is unaffected.

#### Two things to watch on a real device
- **Orientation** is `sensor landscape`, so the phone can be held either way up.
  (This was set to *portrait* until the first iOS build was prepared — a landscape
  game shipped portrait would have been the first thing a tester hit.
  `tests/test_project_config.gd` now guards it.)
- **Thumb reach — measured, and it is real.** On the iPhone 16 Pro simulator the
  game renders 2000 px wide inside a 2622 px screen, leaving **311 px of black
  bar on each side** (~104 pt). The notch and home indicator fall harmlessly in
  those bars, but so do the physical screen corners: the Jump button sits about
  a centimetre inboard of where a thumb naturally rests. Play it before deciding
  how to fix it. The options are a non-integer `scale_mode` (gives up
  pixel-perfect scaling), or drawing the touch overlay in real screen space
  rather than viewport space (keeps pixel-perfect, more work). Do not change
  this blind — it is a genuine trade-off, not a bug.

## Store assets
- Icons: `export/icons/icon_<size>.png`, all generated by
  `tools/gen_art.py` (`build_store_icons`) from the same 128 px roundel, so
  every size stays consistent. Re-run `tools/genart.sh` after changing the art.
- Boot splash: `assets/sprites/splash.png`.
- Privacy: `export/PrivacyInfo.xcprivacy`. The game collects nothing — no
  analytics, no ads, no network, no identifiers. The only stored data is
  `user://save.json` inside the app container. Godot emits its own
  required-reason declarations for the engine's file/disk APIs; ours documents
  the game's position and is copied into the Xcode project by the export script.

## Release checklist

```
tools/test.sh            # 52 unit tests, headless
tools/validate.sh        # scripts compile, scenes resolve, levels/data parse
tools/itest.sh           # 172 in-game integration checks
tools/export_macos.sh
tools/smoke_build.sh     # boots the *exported* build and fails on startup errors
```

`smoke_build.sh` is not optional. A release export once died at startup because
the export filter stripped `tools/`, which at the time held an autoload — no
source-tree test and no screenshot could have caught that.
