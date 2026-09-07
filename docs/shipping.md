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

### Local toolchain — one command
```
tools/bootstrap.sh
```
Fetches Godot 4.7.2 and the export templates, builds the Python venv the asset
generators need, writes `tools/env.sh` (gitignored — it holds absolute paths),
and runs the test suite to prove the setup works. Idempotent; re-run freely.

Everything lands in `.tooling/` inside the repo except the export templates,
which Godot insists live in `~/Library/Application Support/Godot/`.

If you prefer to wire it up by hand, copy `tools/env.sh.example` instead.

### Moving to another machine
Only two things are machine-specific and therefore *not* in the repo:
1. **The toolchain** — `tools/bootstrap.sh` handles it.
2. **Your signing certificates.** Sign Xcode into your Apple ID on the new
   machine (Xcode ▸ Settings ▸ Accounts) and add an *Apple Development*
   certificate. The Team ID itself (`8XG8GS2HT3`) is already committed in
   `export_presets.cfg`, as is the signing-identity fix.

Everything else — presets, icons, the privacy manifest, all source and assets —
travels with the clone.

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

**0. Xcode 26.1 or newer is mandatory.**
Godot 4.7.2's iOS **device** library is built against the **iOS 26.1 SDK** and
references symbols that do not exist in older ones. On Xcode 16 (iOS 18 SDK) a
device build dies at link time with:

```
Undefined symbol: _CADynamicRangeAutomatic
Undefined symbol: _CADynamicRangeConstrainedHigh
Undefined symbol: _CADynamicRangeHigh
Undefined symbol: _CADynamicRangeStandard
Undefined symbol: _MTLTensorDomain
```

Check yours with `xcodebuild -showsdks`. `tools/export_ios.sh` now refuses to
run below 26.1 rather than letting you discover it at the end of a build.

**Beware:** a *simulator* build succeeds on older Xcode, because the simulator
slice does not reference those symbols. Simulator success is not evidence that a
device build will link.

If you cannot update Xcode, the alternatives are to drop back to a Godot version
whose iOS template targets your SDK (which means re-testing the whole project on
that version), or to build the iOS export template from source with your own
Xcode. Updating Xcode is far cheaper.

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
