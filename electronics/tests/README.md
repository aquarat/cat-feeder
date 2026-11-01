# Controller electrical regression tests

Run from the repository root, using **Python 3.9+ and its standard library only**:

```sh
python3 -m unittest discover -s electronics/tests -v
```

Executed on 2026-10-24: **41 tests passed**, including 27 electrical mutation
test methods (29 injected fault cases) and four provenance-tampering cases.
This is automated design regression evidence, not a powered-board test.

## Inputs and independent requirements

The suite reads the current **54-component** `electronics/pcb/schematic-netlist.xml`.
It never imports the generator or executes any code in `electronics/pcb/`.
Requirements come from the independently cleared revision in
[PCB review §0 and §3](../../kb/pcb-review.md), the connector contracts and
manufacturer pin numbering. `connectivity.json` and `design-bom.csv` are
cross-checks, not the electrical oracle.

- The review's manifest SHA-256 is pinned independently in the test helper.
  All **85 manifest entries**, including the actual schematic and PCB, must
  match. The source schematic/PCB also have explicit review hash anchors.
- A small read-only KiCad S-expression parser compares **all 179 XML nodes**
  with actual PCB pads, including singleton NC pins and repeated ESP32 EPAD
  lands. It checks the physical A4988 socket row orientation, 15.24 mm spacing
  and 2.54 mm pitch on the actual board, not a geometry summary.
- All 54 BOM references, values, exact codes, footprint names and assembly
  classes agree with the XML; all 163 declared connected nodes agree with
  `connectivity.json`. The other 16 XML nodes must be singleton NC nets.

| Requirement | Checks |
|---|---|
| Power | J1 motor input, J2 GND/5 V/12 V; AP2112 VIN/EN/GND/VOUT/NC; ESP32 ground/power; separate high-voltage nets; bulk/decoupling values |
| Reset/programming | EN 10 kΩ/1 µF, BOOT pull-up/shunts, UART0 TX/RX, unloaded critical straps/flash pins |
| Fan | Q1 B/E/C = 1/2/3, 4.7 kΩ base drive, 100 kΩ base pull-down, collector-only PWM, permanent 12 V motor feed; 3.3 V tach pull-up and 1 kΩ input resistor |
| Sensors | J4/J5 GND/DQ/3.3 V on the same GPIO27 bus with exactly one 4.7 kΩ pull-up; independent GPIO32/33 position inputs; GPIO21/22 I²C |
| DPS UART | J9 is GND/DPS RX/DPS TX; correct U3/U4 A/Y/VCC/GND/OE pins; GPIO13 OE pull-up; **R20 TX pull-up and R21 external TX pull-down**; 1 kΩ transmit series resistor |
| Motor | Actual J14/J15 pin rows, separate coils, fixed microsteps, GPIO23 RESET/SLEEP pull-down, GPIO18/19 STEP/DIR pull-downs, 100 µF/50 V C10 polarity |
| ADC | GPIO35/ADC1, 100 kΩ/10 kΩ divider, 100 nF filter, bus/11 transfer, nominal RC and 24 V resistor-tolerance check |
| TEC | J10 is GPIO25 logic only with 10 kΩ pull-down; no motor/fan/5 V rail connected to the request net |

Connections are compared by component pin endpoints; signal net labels can all
be renamed and still pass the electrical checks. Critical reference designators
are intentionally checked where the review, BOM and bench procedure identify a
specific resistor or connector. Rail labels are part of the supply interface
contract. Multiple identical capacitors across a rail are checked individually;
parallel extra pull-up resistors are rejected.

## Why the mutation tests matter

In-memory copies of the **real exported XML** are changed. Each mutation must
fail its relevant electrical rule, **without invoking provenance or comparing
against the unmodified BOM**. Cases include a disconnected ESP supply,
5 V/12 V swap, incorrect LDO pin, motor power at J10, missing TEC/fan/UART bias,
BJT C/E swap, 12 V tach pull-up, wrong resistor decades, a split/incorrect
temperature bus, duplicate 1-Wire pull-up, INDEX/HOME or UART RX/TX swaps,
boot-strap misuse, grounded OE, the original floating UART input defect,
backfeeding external TX pull-up, reversed motor row, missing SLEEP connection,
too-weak motor pull-down, mixed coils, reversed electrolytic, wrong ADC divider,
missing ADC filter and wrong EN capacitor. Separate in-memory read substitutions
verify rejection of altered schematic, PCB, XML and manifest bytes.

## Scope and assumptions

- Hash verification binds the XML to the exact schematic/PCB previously checked
  by the independent reviewer. This run **does not re-export KiCad XML or rerun
  ERC/DRC**, and pad-net parity does not prove copper continuity or track capacity.
  A legitimate redesign requires review and new provenance anchors; do not
  automatically accept replacement hashes to make a failed run green.
- Fan reset checks prove the **bias/released-collector topology**. Full speed
  assumes MCU high impedance, a conforming fan's internal PWM pull-up and
  working fan power. Edge quality and Noctua compatibility need a scope.
- Motor reset analysis explicitly assumes the **external Pololu carrier's
  100 kΩ SLEEP pull-up**. A 5% carrier resistor and 1% board resistor are analysis
  assumptions, not measured clone tolerances. Nominal reset voltage is 0.30 V
  at 3.3 V; the check compares the ratio with the A4988 0.3×VDD low-input limit.
  The carrier is not among the 54 assembled parts. Its pinout, current-setting
  network and wake timing require physical verification.
- ADC arithmetic assumes nominal 24 V and ±1% resistors. It establishes neither
  accuracy nor surge/clamp protection, nor powered-off injection acceptability.
- No ESP32 instruction execution, application firmware, DPS protocol, real fan,
  regulator thermal behaviour or external TEC power stage is simulated here.
  Default-low J10 is not an independent shutdown or a verified DPS enable input.
- No physical results or food-safe temperatures are inferred. Follow the
  [bench plan](../bench/README.md); every physical/firmware case starts `NOT_RUN`.

Tests only read the frozen artifacts. Python may create `__pycache__` inside
`electronics/tests/`; no PCB outputs are written.
