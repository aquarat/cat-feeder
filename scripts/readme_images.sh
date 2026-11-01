#!/usr/bin/env bash
# Copy the README gallery renders from a fresh `bash scripts/export_plenum.sh`.
# Re-run both after CAD changes so the README never shows an earlier revision.
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=build/plenum/preview
DST=docs/images
mkdir -p "$DST"
for view in closed opened exploded section harness; do
    if [[ ! -f "$SRC/$view.png" ]]; then
        echo "missing $SRC/$view.png; run bash scripts/export_plenum.sh first" >&2
        exit 1
    fi
    if [[ "$SRC/$view.png" -ot cad/feeder.scad || "$SRC/$view.png" -ot cad/plenum.scad || "$SRC/$view.png" -ot cad/parameters.scad ]]; then
        echo "$SRC/$view.png is older than the CAD sources; re-run bash scripts/export_plenum.sh" >&2
        exit 1
    fi
    cp "$SRC/$view.png" "$DST/feeder-$view.png"
done
ls -l "$DST"
