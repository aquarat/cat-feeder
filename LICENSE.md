# Licensing

Everything in this project is published under copyleft licences: you must
credit the source, and modified versions you distribute must stay open under
the same terms. The exact per-path mapping is in [`REUSE.toml`](REUSE.toml);
full texts are in [`LICENSES/`](LICENSES/).

| What | Licence |
| --- | --- |
| Hardware design sources: `cad/` (including `cad/lib/`), `analysis/`, `electronics/` design and fabrication files, `BOM.md` | [CERN-OHL-S-2.0](LICENSES/CERN-OHL-S-2.0.txt) |
| Software: `*.py`, `*.sh`, Dockerfiles, `thermal/` | [GPL-3.0-or-later](LICENSES/GPL-3.0-or-later.txt) |
| Documentation, `kb/`, Markdown, images and other data | [CC-BY-SA-4.0](LICENSES/CC-BY-SA-4.0.txt) |
| `slicer/profiles/`: presets flattened from [Bambu Studio](https://github.com/bambulab/BambuStudio) | [AGPL-3.0-only](LICENSES/AGPL-3.0-only.txt), Bambu Lab |
| `slicer/plates/`: our geometry with those presets embedded | CERN-OHL-S-2.0 and AGPL-3.0-only |
| `electronics/revb/pd/reference/`: SparkFun STUSB4500 board and library | CC-BY-SA-4.0 (hardware), [MIT](LICENSES/MIT.txt) (code), SparkFun Electronics |

Copyright 2026 aquarat and cat-feeder contributors, except the third-party
files named above.

**Source location** (CERN-OHL-S §4.1): <https://github.com/aquarat/cat-feeder>.

Manufacturer datasheets and SPICE models are not redistributed. Their URLs and
hashes are in [`references.json`](references.json) and
[`electronics/d34/sim/models/vendor/manifest.json`](electronics/d34/sim/models/vendor/manifest.json);
`scripts/fetch_references.py` and `electronics/d34/sim/fetch_models.sh` fetch
them to the paths the documentation cites.

## No warranty

This is an untested prototype that involves mains-powered supplies,
thermoelectric coolers, food contact and an animal. Simulations and rendered
models are not test results. Build or use it at your own risk; the licences
above disclaim all warranties and liability.
