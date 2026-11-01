#!/usr/bin/env bash
# Run the headless OpenSCAD image, mounting this entire project so imports work.
# Image: $OPENSCAD_IMAGE, else cat-feeder-openscad (docker/openscad.Dockerfile),
# else an existing rowing-openscad image built from the same fork.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMG="${OPENSCAD_IMAGE:-}"
if [[ -z "$IMG" ]]; then
    for candidate in cat-feeder-openscad rowing-openscad; do
        if docker image inspect "$candidate" >/dev/null 2>&1; then IMG="$candidate"; break; fi
    done
fi
if [[ -z "$IMG" ]] || ! docker image inspect "$IMG" >/dev/null 2>&1; then
    echo "Build the OpenSCAD image first:" >&2
    echo "  docker build -t cat-feeder-openscad -f docker/openscad.Dockerfile docker" >&2
    exit 1
fi
exec docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -v "$ROOT":/work -w /work "$IMG" oscad-run "$@"
