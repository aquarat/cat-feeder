#!/bin/sh
# Run a D34 script inside the KiCad 9.0.2 container (no network).
# Mounts electronics/ so the shared JLCPCB rule files in ../dfm are visible.
# Usage: ./run.sh build.py ctrl
set -e
cd "$(dirname "$0")"
exec docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/..:/work" -w /work/d34 ${FREEROUTING_JAR:+-v "$FREEROUTING_JAR:/opt/freerouting.jar:ro"} \
  cat-feeder-kicad:local /usr/bin/python3 "$@"
