# Integrated USB-C PD front end — revision-B proposal

**Feasible, component-level connectivity complete, not fabrication/bench qualified.**
See [the detailed integration note](../../../kb/pcb-pd-integration.md) before use.

- `circuit.py` → `circuit.json`: 38 parts/pads with physical pad-to-net assignments,
  exact manufacturer part numbers, LCSC codes, footprints and integration ports.
- `PD.pretty/`: the missing ST PowerFLAT footprint, derived from SparkFun's actual
  Eagle package and checked against ST's land drawing. Drain pins 5–8 aggregate
  to pad 5. Paste segmentation is a proposed change requiring assembly review.
- `stock-evidence.json`: timestamped **public** JLC inventory/identity evidence;
  counts are not reserved inventory. `check-stock.py --refresh` takes a new
  snapshot without touching the old controller revision.
- `commissioning.ino`: one-time NVM setup proposal using SparkFun's documented
  library API. Not compiled or executed on hardware. No invented raw NVM bytes.
- `reference/`: actual SparkFun schematic/source and manufacturer documentation
  (some retrieved through public distributor mirrors); see `sources.json`. Fetch the
  manufacturer documents with `scripts/fetch_references.py`.
- `footprint-check.json`: actual KiCad 9 footprint availability and pad checks.
  Reproduce with the command in `validate_footprints.py`; the FET copper is also
  compared to the original Eagle package, with coordinate-system conversion.

External nets: `PD_20V`, `+3V3` (host), `HOST_SCL`, `HOST_SDA`, `GND`.
`PD_VBUS_RAW` is an internal node/test-power input, not the load output. All nets
starting `PD_` except `PD_20V` stay inside the front-end unless explicitly used
for test access. Map/renumber these in the parent revision; do not merge by ref
number blindly.

The high-current switch uses ST's **two-FET** reference arrangement with the
lower-resistance FET from SparkFun DEV-15801. The power-off-isolated I²C buffer
uses TI's standard application connection. No external PD daughterboard remains.

NVM **must** be commissioned: two enabled PDOs, 5 V/0.5 A and 20 V/5 A,
`POWER_ONLY_ABOVE_5V=1`. The factory default does not implement the required gate
policy. A 20 V/3 A or 20 V/4.3 A source leaves the load OFF. A 5 A e-marked cable
and a source actually advertising 20 V/5 A are required.

The 1 kΩ output discharge assumes **≤150 µF total effective downstream
capacitance**, including the motor driver and all connected regulators/modules.
The parent must resolve this budget before freezing the schematic.

Regenerate connectivity:

```sh
python electronics/revb/pd/circuit.py
```

Only `electronics/revb/pd/**` and `kb/pcb-pd-integration.md` were authored in this
subtask. No supplier account operation or full-board layout was performed.
