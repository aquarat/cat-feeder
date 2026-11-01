#!/usr/bin/env bash
# Re-download the manufacturer SPICE models listed in models/vendor/manifest.json and verify SHA-256.
# Needs network. Several files carry "commercial use or resale restricted" headers: keep them for local
# simulation; decide before committing them to a public repository. Missing models -> behavioural fallbacks.
set -euo pipefail
cd "$(dirname "$0")/models/vendor"
python3 - <<'PY'
import hashlib, json, pathlib, urllib.request
for e in json.load(open('manifest.json')):
    f, url, sha = e.get('original_file') or e.get('file'), e.get('url'), e.get('sha256')
    if not f or not url or not sha:
        continue
    p = pathlib.Path(f)
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == sha:
        print('ok      ', f); continue
    p.parent.mkdir(parents=True, exist_ok=True)
    data = urllib.request.urlopen(url, timeout=60).read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha:
        print('MISMATCH', f, got); continue
    p.write_bytes(data); print('fetched ', f)
PY
