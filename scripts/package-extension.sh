#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE="$ROOT/extension/xarchive"
DESTINATION="$ROOT/app/assets/xarchive-connector.zip"
mkdir -p "$ROOT/app/assets"
python3 "$ROOT/scripts/sync-extension-release.py"
python3 "$ROOT/scripts/build-extension-package.py" --source "$SOURCE" --destination "$DESTINATION"
