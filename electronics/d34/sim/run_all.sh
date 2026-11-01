#!/usr/bin/env bash
# D34 controller simulation suite (SIMULATION, not hardware test).
#
#   electronics/d34/sim/run_all.sh [--only s01,s05] [--quick]
#
# Stage A (cat-feeder-kicad:local, no network): export the three card netlists from the
#          generated KiCad schematics with kicad-cli -> sim/build/netlists/.
# Stage B (cat-feeder-d34sim:local, no network): ngspice + Python scenarios -> sim/results/,
#          results/summary.json lists every check, limit, value, PASS/FAIL and model provenance.
# The repository is mounted read-only; only sim/build/netlists and sim/results are writable.
# Building the sim image (first run only) is the one step that needs network access.
set -euo pipefail
SIM=$(cd "$(dirname "$0")" && pwd)
D34=$(cd "$SIM/.." && pwd)
ROOT=$(cd "$D34/../.." && pwd)
image=cat-feeder-d34sim:local
kimage=cat-feeder-kicad:local
uid="$(id -u):$(id -g)"

if ! docker image inspect "$image" >/dev/null 2>&1; then
    docker build -t "$image" -f "$SIM/Dockerfile" "$SIM"
fi
docker image inspect "$kimage" >/dev/null 2>&1 || {
    echo "missing $kimage: build it from electronics/pcb/Dockerfile" >&2; exit 2; }

mkdir -p "$SIM/build/netlists" "$SIM/results"
rm -rf "$SIM/build/netlists/"* "$SIM/results/"*

echo "== Stage A: kicad-cli netlist export"
docker run --rm --network none --user "$uid" -e HOME=/tmp \
    -v "$D34:/d34:ro" -v "$SIM/build/netlists:/out" "$kimage" sh -c '
    set -e
    for c in ctrl pwr tec; do
        cd /d34/d34-$c
        kicad-cli sch export netlist --format kicadsexpr -o /out/d34-$c.net d34-$c.kicad_sch
    done
    kicad-cli version > /out/kicad-cli.version'

git_rev=$(git -C "$ROOT" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)
if [ -n "$(git -C "$ROOT" status --porcelain -- electronics/d34 2>/dev/null)" ]; then git_rev="$git_rev-dirty"; fi

echo "== Stage B: simulations ($git_rev)"
set +e
docker run --rm --network none --user "$uid" -e HOME=/tmp \
    -e GIT_REV="$git_rev" -e SIM_IMAGE_ID="$(docker image inspect "$image" --format '{{.Id}}')" \
    -e KICAD_CLI_VERSION="$(cat "$SIM/build/netlists/kicad-cli.version")" \
    -v "$ROOT:/work:ro" -v "$SIM/results:/work/electronics/d34/sim/results" \
    -w /work/electronics/d34/sim "$image" \
    python3 run.py --netlists build/netlists --results results "$@"
rc=$?
set -e
[ "$rc" = 0 ] && rm -rf "$SIM/results/_work"  # kept for inspection when a scenario crashed
echo "summary: $SIM/results/summary.json (exit $rc)"
exit $rc
