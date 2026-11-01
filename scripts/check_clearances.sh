#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/logs
bash scripts/openscad.sh --backend=Manifold --enable=geometry-metrics \
    -o build/logs/clearances.echo -D 'part="checks"' cad/feeder.scad
cat build/logs/clearances.echo
if grep -E 'ERROR:|WARNING:' build/logs/clearances.echo; then exit 1; fi
