#!/usr/bin/env python3
"""Refresh the pinned upstream Bambu profiles; normal plate generation is offline."""
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

REVISION = "79df7ae309be398ed30c9f397c13c9911c2edc57"
BASE = f"https://raw.githubusercontent.com/bambulab/BambuStudio/{REVISION}/"
HERE = Path(__file__).resolve().parent
PRESETS = {
    "machine": "Bambu Lab A1 mini 0.4 nozzle",
    "process": "0.20mm Standard @BBL A1M",
    "filament": "Generic PETG @BBL A1M",
}


def main():
    sources, cache = {}, {}

    def flatten(kind, name, stack=()):
        key = (kind, name)
        if key in stack:
            raise ValueError(f"Profile inheritance cycle: {key}")
        if key in cache:
            return cache[key]
        path = f"resources/profiles/BBL/{kind}/{name}.json"
        with urlopen(BASE + quote(path), timeout=60) as response:
            raw = response.read()
        sources[path] = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        result = {}
        if data.get("inherits"):
            result.update(flatten(kind, data["inherits"], stack + (key,)))
        for included in data.get("include", []):
            result.update(flatten(kind, included, stack + (key,)))
        result.update(data)
        result.pop("inherits", None)
        result.pop("include", None)
        cache[key] = result
        return result

    profiles = {kind: flatten(kind, name) for kind, name in PRESETS.items()}
    out = HERE / "profiles"
    out.mkdir(exist_ok=True)
    with urlopen(BASE + "LICENSE", timeout=60) as response:
        license_text = response.read()
    (out / "upstream-LICENSE.txt").write_bytes(license_text)
    for kind, profile in profiles.items():
        (out / f"{kind}.json").write_text(json.dumps(profile, indent=2) + "\n")
    provenance = {
        "repository": "https://github.com/bambulab/BambuStudio",
        "revision": REVISION,
        "license": "AGPL-3.0; see upstream LICENSE",
        "license_sha256": hashlib.sha256(license_text).hexdigest(),
        "presets": PRESETS,
        "source_sha256": sources,
        "flattened_sha256": {
            f"{kind}.json": hashlib.sha256((out / f"{kind}.json").read_bytes()).hexdigest()
            for kind in PRESETS
        },
    }
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"Saved three resolved profiles from {len(sources)} pinned upstream files to {out}")


if __name__ == "__main__":
    main()
