# Revision A check record

Checked 2026-10-24, KiCad 9.0.2. [Machine-readable results](validation.json), [ERC](erc.rpt), [DRC including parity](drc.rpt), [artifact hashes](checksums.json).

**Review-corrected revision; D25 HOLD pending focused independent recheck.** [B1/B2 and rule-persistence provenance](REVIEW-FIXES.md).

| Check | Current result |
|---|---|
| Schematic electrical-rule check | **0 violations** |
| PCB design-rule check | **0 violations**, including warnings |
| PCB connectivity | **0 unconnected items** |
| Schematic/PCB parity | **0 issues**, including intentional NC pads |
| Component inventory | 54: 36 SMT + 18 THT |
| Actual routed crescent board | 621 trace segments, 55 routing vias; 12 additional plated ESP32 thermal-land holes |
| Actual outline | 4083.21 mm²; nominal 58.12 × 80 mm bounding box; R141/R91 with 2 mm fillets |
| Motor phase traces | All 1.0 mm; no routing vias in the phase paths |
| VMOT | Main load path 1.0 mm; two short segments on the low-current R18 sense branch are 0.8014 mm |
| Other rail/signal traces | 0.5 mm / 0.25 mm |
| Minimum rules | 0.2 mm copper clearance, 0.3 mm copper-to-edge, 0.25 mm hole clearance; 0.2 mm minimum plated hole for ESP32 footprint |
| BOM/CPL/design comparison | Both complete reference sets, uniqueness, values/codes/footprints, schematic XML vs actual pads, B1 input biases, positive stock snapshot passed |
| Centroids/orientation record | 54 refs; 18 THT body offsets rotated before origin conversion, 36 centred SMT origins preserved; supplier angles pending |
| Rule persistence | Default/Motor/Power 0.25/1.0/0.5 mm; 18 patterns; two load/save cycles passed; four broken configurations rejected |
| Placement/outline preservation | All original 52 positions/rotations and actual polygon unchanged versus recorded review baseline |
| Manufacturing coordinate system | CPL, Gerber and drill: lower-left board-bounding-box origin, X right/Y up |
| Physical/thermal/RF/EMC tests | **None** |

## Issues caught and corrected

- Initial schematic label placements were off grid; moved symbols/pin stubs onto the KiCad grid and reran ERC.
- Placement courtyard overlaps were corrected before routing.
- The rectangular baseline's router success left a disconnected 3.3 V island. That baseline route was superseded by the owner's crescent preference, not reused as final manufacturing data. The **new crescent route** required two HOME/STEP finishing paths, duplicate-segment cleanup and removal of a dead-end +5 V branch. `finish_route.py` plans conservative 0.1 mm-grid paths; KiCad then checks the actual copper, including vias and plane refill. Its first finishing pass exposed a clearance issue, corrected before final export. No connectivity/clearance issue was waived.
- Local schematic labels create `/NET` PCB net names; normalized routed PCB names and assigned the schematic's singleton `unconnected-(...)` nets. No parity warnings were waived.
- ESP32 native footprint keepout listed 32 copper layers; KiCad trimmed the placed copy to this two-layer stack. Compared normalized footprint files: pad shapes/drills/coordinates were identical; the keepout layer-set difference caused the warning. Local library now explicitly keeps out **both enabled copper layers**, as does the board-wide top antenna exclusion. No electrical/clearance/keepout/parity violation was waived; the independent review distinguishes that from every possible DRC category being enabled.
- Replaced scarce C178702 motor capacitor with stocked **C713402 / EEUFR1H101B**, including its actual **5.00 mm pitch** footprint. Rechecked after moving the ground pad and refilling copper.
- Replaced the rectangular outline with a compact R141/R91 crescent, shifted J1 inward 2.5 mm, regenerated routing, then reran all checks/exports. See [packaging comparison](PACKAGING.md); no current-pocket fit assertion.
- Used one shared origin for Gerbers, drill and CPL, rather than relying on a supplier's automatic placement translation.
- Actual width inspection identified the 0.8014 mm ADC-divider spur; the 1 mm claim is limited to the real motor/load paths.
- Inspected current schematic, top, bottom and assembly SVG/PNG views. Moved passive reference/value text away from net labels. Pin-one marks, cap polarity, carrier outline, edge outline, connector placement and empty antenna region were reviewed. This is a 2D design review, not a 3D fit or solderability trial.
- Exported board-only STEP and a separately labelled outline-envelope STL. Reloaded STL: watertight, consistent winding, positive 6533.13 mm³ volume, measured 58.1185 × 80 × 1.6000 mm bounds. The polygon tessellation is within approximately 0.003 mm of nominal arc extrema. Holes/components are omitted from the STL; the STEP contains board holes but no component models. These packaging aids do not validate installed height/clearances.

## Boundaries of these results

The independent review found defects not captured by the earlier clean checks: floating buffer inputs and pin-one origins in THT centroid fields. Those are now corrected and checked explicitly. This revision also fixes the lost Motor/Power definitions instead of relying on already-wide copper. See [REVIEW-FIXES.md](REVIEW-FIXES.md) for exact changes and current validation. All exports/mesh/views were regenerated for this revision; the earlier review's counts and hashes are historical.

ERC checks encoded pin types, not whether the design satisfies every module's electrical requirements. DRC checks the configured geometry rules, not assembler approval, analog/RF performance, current capacity or condensation protection. Stock is a public snapshot, not reserved inventory. CPL angles are unqualified against supplier library conventions. Mixed SMT/THT assembly, exact connector drawings, ESP32 thermal-pad processing, A4988 module fit, DPS5005 compatibility and enclosure integration still need the work described in the [README](README.md).
