#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$PROJECT_ROOT"
# Capture once per device aspect: a phone fills the width and puts the touch
# controls in the side margin; a 4:3 tablet gets a top/bottom band instead.
mkdir -p shots/phone shots/tablet
sed 's#"shots/store_#"shots/phone/store_#g' tools/seq/store_shots.json > /tmp/seq_phone.json
sed 's#"shots/store_#"shots/tablet/store_#g' tools/seq/store_shots.json > /tmp/seq_tablet.json
tools/shot.sh --res=1044x480 --seq=/tmp/seq_phone.json  >/dev/null
tools/shot.sh --res=960x720  --seq=/tmp/seq_tablet.json >/dev/null
"$PYVENV" tools/gen_store_shots.py
