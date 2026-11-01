#!/bin/sh
# Quick placement check: build + DRC on the unrouted board (ignores unconnected items).
cd "$(dirname "$0")"
./run.sh build.py "$1" 2>&1 | grep -v shape_poly
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD/..:/work" -w /work/d34/d34-$1 cat-feeder-kicad:local \
  bash -c "kicad-cli pcb drc --format json -o /tmp/u.json d34-$1-unrouted.kicad_pcb >/dev/null; cat /tmp/u.json" | python3 -c "
import json,sys;d=json.load(sys.stdin)
for v in d['violations']: print(v['type'],[(i['description'][:45],i['pos']['x']-50,i['pos']['y']-50) for i in v['items']])"
