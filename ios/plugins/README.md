# Game Center plugin

Third-party native code (not art, audio or level data), MIT-licensed:
see `LICENSE-godot-ios-plugins.txt`.

- Source: https://github.com/godot-sdk-integrations/godot-ios-plugins
  at commit `caafb2c`, `plugins/gamecenter`, unmodified.
- Built on 2026-11-06 against Godot **4.7.2-stable** headers, with
  Xcode 16.0 / iOS 18.0 SDK:
  - headers: `scons platform=ios target=template_release` in the engine source,
    stopped once the generated headers existed (the plugin's own
    `scripts/generate_headers.sh` still passes Godot 3's `target=release_debug`);
  - `./scripts/generate_xcframework.sh gamecenter release 4.0` and `... debug 4.0`.
- Godot's iOS exporter reads `res://ios/plugins` with a plain directory read, so
  `ios/.gdignore` does not hide it (`editor_export_platform_apple_embedded.h`,
  `get_plugins`). `tools/sync_ios_project.sh` keeps this folder when it
  regenerates `ios/`.
- Enabled by `plugins/GameCenter=true` in the iOS export preset; the entitlement
  comes from `entitlements/game_center=true`.
- Used by `src/core/achievements.gd` through the `GameCenter` engine singleton.
