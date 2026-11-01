#!/usr/bin/env bash
# Run the board's regression suite and operating sensitivity models locally.
set -euo pipefail
cd "$(dirname "$0")/../.."
image=cat-feeder-spice:local
if ! docker image inspect "$image" >/dev/null 2>&1; then
    docker build -t "$image" -f electronics/sim/Dockerfile electronics/sim
fi
power_results=${POWER_RESULTS:-"$PWD/electronics/sim/power/results"}
scratch=${TMPDIR:?Set TMPDIR to a writable session scratch directory}
mkdir -p electronics/sim/interfaces/results "$power_results" "$scratch"
image_id=$(docker image inspect "$image" --format '{{.Id}}')
docker run --rm --network none --user "$(id -u):$(id -g)" \
    -v "$PWD:/work:ro" "$image" \
    python -m unittest discover -s electronics/tests -v
docker run --rm --network none --user "$(id -u):$(id -g)" \
    -v "$PWD:/work:ro" -v "$PWD/electronics/sim/interfaces/results:/results" \
    "$image" python electronics/sim/interfaces/run.py --output /results
docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e TMPDIR=/scratch -e INTERFACE_RESULTS=/results \
    -v "$PWD:/work:ro" -v "$scratch:/scratch" \
    -v "$PWD/electronics/sim/interfaces/results:/results:ro" \
    "$image" python electronics/sim/interfaces/test_run.py
docker run --rm --network none --user "$(id -u):$(id -g)" \
    -v "$PWD:/work:ro" -v "$PWD/electronics/sim/interfaces/results:/results" \
    "$image" python electronics/sim/plot_interfaces.py --output /results
docker run --rm --network none --user "$(id -u):$(id -g)" \
    -e SIM_IMAGE_ID="$image_id" \
    -v "$PWD:/work:ro" -v "$power_results:/results" \
    "$image" python electronics/sim/power/run.py --output /results
docker run --rm --network none --user "$(id -u):$(id -g)" \
    -v "$PWD:/work:ro" -v "$power_results:/results" \
    "$image" python electronics/sim/power/test_run.py --output /results
