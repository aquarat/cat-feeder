#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/stl build/checks build/preview build/logs
for part in sector hub drive deck_quarter insulation_coupon lid_access_coupon motor_bridge fan_inlet_coupon pcb_cradle pcb_mount_coupon clip closure_coupon_base closure_coupon_lid capacity; do
    bash scripts/openscad.sh --backend=Manifold --export-format binstl \
        -o "build/stl/$part.stl" -D "part=\"$part\"" cad/feeder.scad \
        >"build/logs/$part.log" 2>&1
    if grep -E 'ERROR:|WARNING:' "build/logs/$part.log"; then exit 1; fi
done
for part in shell lid; do
    bash scripts/openscad.sh --backend=Manifold --export-format binstl \
        -o "build/checks/$part.stl" -D "part=\"$part\"" cad/feeder.scad \
        >"build/logs/$part.log" 2>&1
    if grep -E 'ERROR:|WARNING:' "build/logs/$part.log"; then exit 1; fi
done
for part in opened closed exploded section tray access loading underside fan_inlet_coupon; do
    camera=()
    if [[ "$part" == section ]]; then camera=(--camera=0,0,65,65,0,200,480); fi
    bash scripts/openscad.sh --backend=Manifold --render --autocenter --viewall \
        --imgsize=1400,1100 --colorscheme=Tomorrow "${camera[@]}" \
        -o "build/preview/$part.png" -D "part=\"$part\"" cad/feeder.scad \
        >"build/logs/$part.log" 2>&1
    if grep -E 'ERROR:|WARNING:' "build/logs/$part.log"; then exit 1; fi
done
