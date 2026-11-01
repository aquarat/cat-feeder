# Controller PCB — editable revision A draft

Updated 2026-10-24. This implements the catalogue-iteration workflow in [D22/D23](decisions.md). **A fully routed, electrically/geometrically checked design draft exists; no PCB has been ordered, assembled or physically tested.**

**Current handoff: D25 HOLD remains pending focused independent recheck.** The
[independent review](pcb-review.md) found B1 floating UART-buffer inputs, B2
incorrect THT centroids and missing routing classes. Designer corrections are
complete in [the precise fix record](../electronics/pcb/REVIEW-FIXES.md);
supplier-project creation remains prohibited until rechecked. Enclosure fit is
a separate ongoing task. The owner submits any later quote request.

## Deliverable and evidence

- [KiCad project](../electronics/pcb/feeder.kicad_pro), [schematic](../electronics/pcb/feeder.kicad_sch), [routed PCB](../electronics/pcb/feeder.kicad_pcb), [readable schematic PDF](../electronics/pcb/views/schematic.pdf).
- [PCB README and complete pinout](../electronics/pcb/README.md), [assembly view](../electronics/pcb/views/assembly.png), [top copper](../electronics/pcb/views/top.png), [bottom copper](../electronics/pcb/views/bottom.png), [crescent comparison/mechanical handoff](../electronics/pcb/PACKAGING.md).
- [Mixed-process BOM](../electronics/pcb/assembly-bom-all.csv), [mixed-process placement file](../electronics/pcb/assembly-cpl-all.csv), [all-part quotation scope](../electronics/pcb/quotation-bom-all.csv), [draft manufacturing ZIP](../electronics/pcb/manufacturing-draft.zip); separate SMT-only BOM/CPL are also available.
- [Check record](../electronics/pcb/CHECKS.md): KiCad **9.0.2 ERC 0, DRC 0, unconnected 0, schematic parity 0**. Corrected crescent board has **54 components, 621 trace segments and 55 routing vias**. [Hashes](../electronics/pcb/checksums.json) tie checks to the current artifacts.
- [Supplier selections/substitutions](../electronics/pcb/SOURCING.md) and [timestamped direct JLC evidence](../electronics/pcb/stock-evidence.json). Every selected component code had positive stock; this is neither a reservation nor an assembly acceptance.

## Architecture and rationale

The two-layer controller carries an assembler-fitted **ESP32-WROOM-32E-N4** and accepts a separately fitted standard **A4988 carrier** in two ordinary 1×8 sockets. Latest owner steering favours a shallow wall-following crescent where packaging warrants it: the current **R141/R91** outline has a **58.12 × 80 mm** bounding box and **4083.21 mm²** area, only **2.17% above** the rounded 50 × 80 mm baseline. It brings out two powered DS18B20 connectors, two optical inputs, optional I²C and programming headers. Three stocked Phoenix 5.08 mm electrical screw terminals handle motor input and its two windings; D22 explicitly permits these terminals.

External regulated **5 V logic and 12 V fan rails** keep switching-converter parts/thermal burden off this first carrier. An AP2112 provides 3.3 V; its installed thermal/load budget still needs measurement. VMOT is a separate protected **20/24 V** input. Motor current is set on the purchased A4988 module; no validated board motor-current rating is claimed. Phase/load tracks are 1 mm, signals 0.25 mm and logic/fan rails 0.5 mm; trace width is geometry, not a measured rating.

The PC-style four-wire fan is always powered from 12 V; an MMBT3904 provides an **inverting open-collector PWM** interface and the tach input has a 3.3 V pull-up. This avoids assuming a generic MOSFET conducts well solely from its threshold specification. J3 is an ordinary header and needs a fan adapter harness.

**TEC high-current regulation stays external**, following [TEC control](tec-control.md). The PCB has a default-low logic enable connector for a separately engineered external switch/interlock and two default-disabled SN74LVC1G125 UART buffers for the DPS5005. It does not contain a 5 A TEC power path. UART RX accepts a 5 V-class signal; UART TX remains 3.3 V with a series resistor. Exact DPS logic levels, grounding, protocol and power-order behaviour remain bench questions. The enable header is **not a verified DPS enable pin**, and hardware power removal is not established by an ESP32 pull-down.

Default-low A4988 RESET/SLEEP inhibits the motor; fixed 1/16 microstepping keeps wiring simple. Firmware must explicitly enable the motor and UART, account for fan-PWM inversion, detect failed sensors/fan/motion, and coordinate the external TEC interlock. **No firmware has been implemented.**

Review B1 correction: **R20 10 kΩ pulls U3.2/DPS_TX to +3V3; R21 10 kΩ pulls U4.2/DPS_TX_EXT to GND**, both existing C25804/0603WAF1002T5E. R14 OE pull-up and R15 output series resistor remain. OE disable alone does not define buffer data inputs. Keep OE disabled with DPS absent/off; the pulldown's calculated active load is 0.33 mA at 3.3 V / 0.50 mA at 5 V, pending actual interface qualification. New placements are R20 (79,113,0°), R21 (91,109,90°); original 52 placements and exact outline are preserved.

## Catalogue iteration

**36 SMT placements** have exact stocked JLC/LCSC codes; **18 THT parts** have stocked candidates with `manualWeld` metadata. The **`assembly-*-all.csv`** pair covers all 54 mixed-process placements; the unsuffixed pair covers SMT only. B2 is corrected with explicit body-centre offsets for all 18 THT parts, rotated before the common Gerber/CPL origin conversion. Centred SMT origins are retained. [Exact-code reconciliation](../electronics/pcb/assembly-reconciliation.json) covers every pad/pin-one, C10 polarity, Phoenix wire entry and U1 antenna. Supplier zero-angle corrections remain explicitly pending. The [assembly-service study](pcb-assembly.md) supplies service/cost context, not a quote.

The scarce original Panasonic motor capacitor was replaced by **EEUFR1H101B / C713402**, with its correct **5 mm** lead pitch and a refreshed footprint/copper/check/export cycle. The near-fit AISHI option was superseded because exact published ripple/impedance evidence was less complete. A zero-stock 1×2 header was replaced by a stocked Hong Cheng part. Two ordinary single-gate UART buffers were retained over a finer-pitch dual. The sourcing page preserves superseded candidates and the reasons, rather than silently replacing evidence.

The offline router's success report was independently checked. The earlier rectangular route had a missing 3.3 V island; after the crescent outline/J1 change, a fresh route required HOME/STEP finishing and duplicate/dead-end cleanup instead. Schematic net-name parity and the ESP32 two-layer keepout-library mismatch were also fixed without suppressing rules. Current ERC/DRC and rendered views were regenerated for the final crescent, not carried forward from the rectangle.

The correction retains that checked base route and adds explicit R20/R21 connections before refill, then regenerates checks and all outputs. Missing Motor/Power routing defaults are restored (Default/Motor/Power = 0.25/1.0/0.5 mm). A preserving save wrapper prevents headless KiCad from replacing project definitions; repeated actual save cycles and deliberate invalid configurations test the regression. Export asserts project settings and actual copper widths separately. The manufacturing ZIP, centroid reconciliation, regenerated mesh/views and sources are tied to the final manifest after all dependent exports finish.

Economic PCBA supports single-side SMT+THT and has a published **two-assembled-board minimum**; the board follows that process direction. Curved-board panelisation/handling and exact part eligibility remain supplier questions. Official API access was not used; supplier-project preparation follows the separate D25 workflow, which these designer corrections did not access. Public catalogue evidence remains the PCB's sourcing record. Supplier project preparation is prohibited until the focused independent recheck; no quotation request has been submitted.

## Packaging and next decisions

**The current mechanical CAD bays/posts do not fit this crescent PCB.** No enclosure CAD or upstream submodule was changed for this work. The R146 bore gives nominal 5 mm outer radial allowance; a centred 120 mm-square fan's bounding circle has nominal 6.15 mm clearance to R91. These are **bore/fan-only 2D bounds**: sink/post volumes and the R105 TEC-site projections remain unresolved and may overlap. Floor is Z28; PCB installed Z/rotation are not assigned.

A floor-supported, bounded, top-loaded dry pocket still needs design with underside solder-pin clearance, retention, harness bend/strain-relief space, purchased carrier/heatsink height and antenna keep-clear area. The board has rounded 2 mm corners and no mechanical mounting holes, consistent with tool-free retention as a future integration step. [Packaging handoff](../electronics/pcb/PACKAGING.md) includes current outline vertices, board-only STEP and a watertight, checked outline-envelope STL, with explicit coordinate transforms and omitted geometry. Primary mechanical review must verify fit; the crescent does not by itself solve it.

Before releasing a manufacturing revision, resolve supplier CPL rotations/pin-one alignment, exact THT drawings/assembly eligibility and ESP32 thermal-land solder processing. Before powered system trials, verify external protection and rails, LDO temperature under radio load, actual carrier current setting/VMOT spikes, fan/probe behaviour, DPS interface compatibility and an independent fail-off TEC power arrangement. Cooling, food safety, EMC, cleanability and installed RF performance are untested. These are specific open interfaces; a clean CAD rule check does not close them.

Related: [KB index](README.md), [decisions](decisions.md), [BOM](../BOM.md), [drop-in layout](drop-in-layout.md), [mechanical review](mechanical-review.md), [thermal/control proposal](tec-control.md).
