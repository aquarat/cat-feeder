# Rev B power-block handoff

**Selected:** AP63203WU-7 / C780769 for 3.3 V (1 A design budget); AP63201WU-7 / C2071044 for approximately 12 V (0.5 A fan-start budget, 0.14 A normal).

Read [rationale, layout constraints and qualification gaps](../../../kb/pcb-buck-integration.md).

- `circuit.json`: complete **22-component** numbered-pin integration contract, MPNs, JLC codes, KiCad symbols/footprints, datasheet links.
- `design.py`: source generator; follows the motor block's parts schema.
- `analysis.json`, `analyze.py`, `test_power.py`: explicit assumptions and eight analytical/fault-injection tests.
- `stock-evidence.json`, `refresh-stock.py`: read-only public stock snapshots, including rejected candidates; selection is defined by `circuit.json`, not by presence in the evidence file.
- `kicad-audit.json`, `audit_kicad.py`, `power.pretty/`: installed KiCad 9.0.2 symbol/pad checks and exact standard footprint copies.
- `reference-sources.json`, retained PDFs/text: manufacturer-authored reference evidence and mirror provenance.

**Required upstream contract:** `SYS_20V` is a hardware-qualified 20 V switched supply, OFF for fallback contracts and contract loss. Both buck EN pins tie to this supply. Neither rail waits on ESP32 firmware. Feed motor power and DPS5005 separately from the qualified 20 V bus; include the buck banks' 40 µF nominal input capacitance in upstream switch inrush calculations.

The new PCB integrator must check layout/loop/transient/thermal behavior. These files contain no full-board layout and no physical test results. Capacitor DC-bias retention and 10 µs load-step recovery are screening assumptions, not measured guarantees. The 0.5 A fan-start budget is not a qualified continuous thermal rating.
