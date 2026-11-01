#!/usr/bin/env bash
# Per-lead solid-interference diagnostic (non-asserting); prints only collisions.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/openscad.sh --backend=Manifold -D 'cooling_concept="plenum"' --enable=geometry-metrics \
    -o build/plenum/logs/harness_report.echo -D 'part="harness_report"' cad/feeder.scad >/dev/null 2>&1
grep 'measure =' build/plenum/logs/harness_report.echo | sed 's/ECHO: measure = //;s/"//g' |
    awk -F', mm3 = ' '$2+0>0.001{printf "%s = %.1f mm3\n",$1,$2}'
