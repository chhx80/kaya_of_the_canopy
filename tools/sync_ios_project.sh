#!/usr/bin/env bash
# Produces the committed Xcode project that Xcode Cloud builds from.
#
# Xcode Cloud needs an .xcodeproj in the repo. It must NOT live in build/:
# Xcode writes Packaging.log there during Distribute, and that log carries live
# Apple auth headers. One was pushed to GitHub. So the tracked copy lives in
# ios/ and this script is the only thing that writes it.
#
# The project is *generated*; the SDK gate in export_ios.sh guards linking,
# which happens on Apple's machines, not here. So this deliberately skips it.
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"

STAGE="$(mktemp -d -t kaya_ios)"
trap 'rm -rf "$STAGE"' EXIT

"$PYVENV" tools/stamp_build.py

echo "generating Xcode project…"
"$GODOT" --headless --path . --export-release "iOS" "$STAGE/KayaOfTheCanopy.xcodeproj" \
  >/tmp/kaya_ios_sync.log 2>&1 || true

if [ ! -f "$STAGE/KayaOfTheCanopy.xcodeproj/project.pbxproj" ]; then
  echo "error: Godot did not write a project. Tail of the log:" >&2
  grep -E '^(ERROR|error:)' /tmp/kaya_ios_sync.log | head -10 >&2
  exit 1
fi

# Strip everything that is output rather than project, and everything that has
# ever carried a credential.
find "$STAGE" \( -name '*.log' -o -name '*.ipa' -o -name 'DistributionSummary.plist' \
  -o -name 'ExportOptions.plist' \) -delete
find "$STAGE" \( -name '*.xcarchive' -o -name '*.dSYM' \) -prune -exec rm -rf {} + 2>/dev/null || true

# Refuse to publish anything that still looks like a credential.
if grep -rlEq '(DSESSIONID|X-Apple-GS-Token|myacinfo)["'"'"']?[[:space:]]*[=:]' "$STAGE" 2>/dev/null; then
  echo "error: generated output still contains a credential marker — not syncing" >&2
  exit 1
fi

# ios/ holds two kinds of thing: the GENERATED export, and curated files the
# repo owns (the compressed frameworks, the CI hooks, .gdignore). An earlier
# version wiped ios/ wholesale and silently deleted seven tracked files, so the
# curated set is preserved explicitly.
CURATED=(frameworks ci_scripts .gdignore)
KEEP="$(mktemp -d -t kaya_keep)"
for c in "${CURATED[@]}"; do
  [ -e "ios/$c" ] && cp -R "ios/$c" "$KEEP/" || true
done

rm -rf ios
mkdir -p ios
cp -R "$STAGE"/. ios/
for c in "${CURATED[@]}"; do
  [ -e "$KEEP/$c" ] && cp -R "$KEEP/$c" ios/ || true
done
rm -rf "$KEEP"
cp export/PrivacyInfo.xcprivacy ios/ 2>/dev/null || true

# The two big engine libraries are gitignored and shipped compressed; drop the
# 350 MB of uncompressed copies the export just wrote. Named explicitly, not
# globbed: `ios/*.xcframework` also matched the tiny committed visionOS stubs.
rm -rf ios/KayaOfTheCanopy.xcframework ios/MoltenVK.xcframework

# Record what the .pck was built from. tests/test_ios_bundle.gd compares this
# against the live project, so a stale committed .pck fails the suite instead of
# shipping a build that silently lags the source.
"$PYVENV" tools/hash_game_data.py > ios/.pck_source_hash
echo "recorded pck source hash: $(cat ios/.pck_source_hash)"

echo "wrote ios/ ($(find ios -type f | wc -l | tr -d ' ') files, $(du -sh ios | cut -f1))"
echo
echo "Point the Xcode Cloud workflow at:  ios/KayaOfTheCanopy.xcodeproj"
