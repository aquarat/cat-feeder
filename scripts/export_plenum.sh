#!/usr/bin/env bash
# D35 cold-air plenum study: changed parts, D34 card models, harness, assembly
# checks and views. Unchanged prints (sector, hub, clip, ...) come from scripts/export.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=build/plenum
mkdir -p "$OUT"/stl "$OUT"/checks "$OUT"/preview "$OUT"/logs "$OUT"/harness
MODE=(-D 'cooling_concept="plenum"')
run() { # output, part, extra args...
    local out=$1 part=$2; shift 2
    bash scripts/openscad.sh --backend=Manifold "${MODE[@]}" "$@" \
        -o "$out" -D "part=\"$part\"" cad/feeder.scad >"$OUT/logs/$part.log" 2>&1
    if grep -E 'ERROR:|WARNING:' "$OUT/logs/$part.log"; then exit 1; fi
}
# 1. Card models from the KiCad boards (+ electronics/d34/parts3d.json when present).
python3 scripts/gen_d34_cards.py | tee "$OUT/logs/gen_d34_cards.log"
if grep -q '^WARNING' "$OUT/logs/gen_d34_cards.log"; then echo "card generator warnings (see above)"; fi
# 2. Harness: resolve, bend, analytic checks, cut list (fails on any failed lead).
python3 scripts/harness.py | tee "$OUT/logs/harness_check.log"
# 3. Hand access: per-plug blockers and an unplug order (card-internal crowding is
#    reported, not fatal; enclosure/device blockers fail).
bash scripts/openscad.sh --backend=Manifold "${MODE[@]}" --enable=geometry-metrics \
    -o "$OUT/logs/access.echo" -D 'part="access_report"' cad/feeder.scad >"$OUT/logs/access_report.log" 2>&1
python3 scripts/access_order.py "$OUT/logs/access.echo" | tee "$OUT/harness/access.txt"
# 4. Printable parts and check meshes.
for part in deck_quarter motor_bridge plenum_baffle plenum_basin plenum_card_cap \
            plenum_fin_clip plenum_fin_clip_66 plenum_fin_clip_90 plenum_sensor_clip plenum_leak_clip plenum_panel_pod \
            plenum_inlet_keeper plenum_drive; do
    run "$OUT/stl/$part.stl" "$part" --export-format binstl
done
for part in shell lid; do
    run "$OUT/checks/$part.stl" "$part" --export-format binstl
done
# 5. Views.
for part in opened closed exploded section plenum_deck loading underside harness; do
    camera=()
    if [[ "$part" == section ]]; then camera=(--camera=0,0,75,65,0,200,500); fi
    if [[ "$part" == harness ]]; then camera=(--camera=0,-60,380,0,0,55); fi
    run "$OUT/preview/$part.png" "$part" --render --autocenter --viewall \
        --imgsize=1400,1100 --colorscheme=Tomorrow "${camera[@]}"
done
run "$OUT/preview/harness_top.png" harness --render --projection=ortho --autocenter --viewall \
    --imgsize=1400,1400 --colorscheme=Tomorrow --camera=0,0,0,0,0,0,900
run "$OUT/preview/cold_pocket.png" cold_pocket --render --imgsize=1300,1000 --colorscheme=Tomorrow \
    --camera=170,-100,150,0,-100,92
for a in 45 135 225 315; do
    cam=$(python3 -c "import math;a=math.radians($a);print(f'{20*math.cos(a):.1f},{20*math.sin(a):.1f},300,{100*math.cos(a):.1f},{100*math.sin(a):.1f},50')")
    run "$OUT/preview/bay_$a.png" "bay_$a" --render --imgsize=1300,1100 --colorscheme=Tomorrow --camera="$cam"
done
# 6. Clearance checks (every empty_check asserts).
bash scripts/openscad.sh --backend=Manifold "${MODE[@]}" --enable=geometry-metrics \
    -o "$OUT/logs/clearances.echo" -D 'part="checks"' cad/feeder.scad
cat "$OUT/logs/clearances.echo"
if grep -E 'ERROR:|WARNING:' "$OUT/logs/clearances.echo"; then exit 1; fi
echo "$(grep -c 'check =' "$OUT/logs/clearances.echo") plenum clearance checks passed"
