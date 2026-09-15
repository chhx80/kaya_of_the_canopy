#!/usr/bin/env bash
# Xcode Cloud post-clone hook.
#
# Deliberately does almost nothing. An earlier version installed Godot 4.7.2 and
# 1.2 GB of export templates to regenerate the iOS export on every build. That
# is no longer needed: the engine XCFrameworks are committed xz-compressed under
# ios/frameworks/ (180 MB -> 25 MB, which fits under GitHub's 100 MB per-file
# limit) and reassembled by ci_pre_xcodebuild.sh, and the .pck is committed.
#
# A stale committed .pck is the risk that buys, so tests/test_ios_bundle.gd
# fails the suite if it falls behind the source. Refresh with
# tools/sync_ios_project.sh.
set -euo pipefail
REPO_ROOT="${CI_PRIMARY_REPOSITORY_PATH:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$REPO_ROOT"

echo "--- repository contents the build depends on"
ls -l ios/KayaOfTheCanopy.pck 2>/dev/null | awk '{printf "    pck        %.1f MB\n", $5/1048576}'
du -sh ios/frameworks 2>/dev/null | awk '{print "    frameworks " $1}'
echo "--- nothing to fetch; ci_pre_xcodebuild.sh unpacks the frameworks"
