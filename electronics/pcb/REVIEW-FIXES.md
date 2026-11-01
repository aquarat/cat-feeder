# Revision A — independent-review corrections, 2026-10-24

**Designer corrections complete; HOLD for the focused independent recheck under
D25. Supplier-project creation remains prohibited.** This record responds to
[the independent review](../../kb/pcb-review.md), without altering that report.
It supersedes the reviewed revision's 52-part counts, native-origin THT CPL and
artifact hashes. It is not supplier placement approval or physical qualification.

## B1: buffer data-input bias

| Added part | Exact selection | Actual connections | KiCad X, Y, rotation |
|---|---|---|---|
| R20 | 10 kΩ UNI-ROYAL 0603WAF1002T5E / C25804 | pad 1 +3V3; pad 2 DPS_TX = U3.2/U1.28 | **79, 113 mm, 0°** |
| R21 | Same | pad 1 DPS_TX_EXT = U4.2/J9.3; pad 2 GND | **91, 109 mm, 90°** |

R14's 10 kΩ OE pull-up and R15's 1 kΩ output series resistor remain. R20 gives
the ESP-side buffer input a defined UART-idle high during reset. R21 gives the
external input a defined low with the DPS absent/off, without pulling an
unpowered DPS TX toward +3V3. Active DPS TX must drive **0.33 mA at 3.3 V or
0.50 mA at 5 V**; this is a calculated resistor load, not a measured interface.
Keep OE disabled while DPS is absent/off. Its disconnected receive-low state
is not a UART session. MCU receive-output bias can be configured in firmware.

`validate_revision.py` checks resistor values/codes, actual schematic XML nodes
against PCB pad nets, and the retained OE/series connections. Current ERC/DRC
then establish no unconnected copper or parity discrepancy. Initial trial
positions exposed a courtyard/track conflict; the final coordinates above pass.

**All original 52 component positions/rotations and the actual outline polygon
are unchanged.** `review-baseline.json` records the pre-fix placements and
outline hash; `review-fix-validation.json` reports the comparison. R21's new
reference text is beside its body at (89.8,109), rotated 90°. No other existing
footprint or reference-text placement was deliberately moved. Mechanical review
can continue using the same envelope; new resistor bodies are ordinary 0603.

## B2: true body-centroid export

`assembly.py` contains **17 exact LCSC-code mappings**, checked against local
F.Fab geometry and pin 1. It generates both CPLs and
[`assembly-reconciliation.json`](assembly-reconciliation.json): **all 54 refs**,
every numbered pad/net/coordinate, native origins, rotated body centres, final
fabrication centres, pin 1 and orientation landmarks. The record is reproducible
from the delivered board, local footprints and retained stock snapshot.

| Exact code | Refs | Native body-centre offset, mm | Orientation evidence |
|---|---|---|---|
| C27438 | J14/J15 | (0,+8.89) | Pin 1 at native (0,0), pad sequence toward +Y |
| C713402 | C10 | (+2.50,0) | Ø8 Fab circle; positive pad 1 at (0,0), negative pad 2 at (+5,0) |
| C5183929 | J1/J16/J17 | (+2.54,−0.30) | Fab body X −2.54…7.62, Y −5.20…4.60; wire-entry face at **+Y=4.60**, entry midpoint (+2.54,+4.60) |
| C49257 | J2/J4/J5/J6/J7/J9 | (0,+2.54) | Pin 1 at (0,0), pad sequence toward +Y |
| C5116483 | J3/J8/J11 | (0,+3.81) | Same pin-one convention |
| C27985187 | J10/J12/J13 | (0,+1.27) | J12/J13 rotated 90°: placed correction **(+1.27,0)** |
| C701341 | U1 | (0,0) | Body-centred native origin; pin 1 (−8.75,−5.26), antenna toward **−Y**, edge midpoint (0,−12.75) |
| C51118/C23654/C20526 | U2/U3/U4/Q1 | (0,0) | Explicit native pin-one offsets; every actual pad saved in reconciliation |
| C25804/C25803/C23162/C21190/C15850/C14663/C15849 | All SMT passives | (0,0) | Centred native origins retained; resistor/ceramic electrical polarity absent, numbered pads retained |

These correct **all 18 THT centres**, retaining all **36 centred SMT origins**.
Header/socket body extents are the explicit local Fab-body model; exact supplier
body/tail drawings remain open as identified in the independent review. The
Phoenix and Panasonic datums use the previously matched exact package evidence.

For native offset `(dx,dy)` and KiCad angle θ, the placed offset is
`(dx*cosθ + dy*sinθ, −dx*sinθ + dy*cosθ)`. Add it to the native placement **before**
the shared Gerber/CPL conversion: `X = x − 41.88227141164403`, `Y = 130 − y`.
Numerical anchor checks include J14 centre (59,99.89), CPL (17.1177,30.1100);
C10 (84.5,94); J1 (88.04,122.7); J12 (79.27,78.5); J13 (55.27,72.2).

**Supplier zero-angle and supplier-origin corrections are explicitly `null`
(pending), not zero corrections claimed verified.** CPL angles remain native
KiCad angles. Later supplier pad overlays must match U1 antenna/pin 1, gate and
transistor pin numbering, C10 positive lead, terminal wire entry and connector
pin sequence. No supplier library, project or placement preview was accessed.

## Routing-rule persistence and validation

- Restored Default **0.25 mm**, Motor **1.0 mm**, Power **0.5 mm** classes, with
  18 explicit slash-prefixed/unprefixed assignments. Project rules retain
  0.2 mm clearance, 0.3 mm edge clearance, 0.25 mm hole spacing and 0.2 mm minimum
  plated hole for U1. No DRC exclusions are present.
- `project_rules.save_board()` preserves the authoritative project bytes around
  headless `pcbnew.SaveBoard()`, which otherwise wrote cached/default netclass
  data over them. Generation writes its canonical definitions after initial
  placement export; route import and final refill use the preserving wrapper.
  Export validates the project **before checks and after CLI exports**.
- `test_project_rules.py` passed two actual load/save cycles with byte-identical
  project retention. It rejects missing Motor, wrong Power width, missing
  assignment and a wrong minimum-hole rule. No GUI behaviour is inferred from
  this headless regression test.
- Preferred routing widths are not minimum-width/current-capacity guarantees.
  Export independently inspects actual phase copper (≥1 mm, no vias), actual
  power tracks (≥0.5 mm), and limits the two VMOT 0.8014 mm sensing-spur segments
  to their known bounded location; VMOT load copper remains 1 mm.
- Retained the reviewed base `feeder.ses` and its HOME/STEP finishing. Added
  explicit R20/R21 routes in `finish_route.py`; R21 GND joins the refilled plane.
  Same-net drills now also block new vias, preventing overlapping drills at
  THT endpoints. The new DSN includes 54 parts; the retained SES is intentionally
  the 52-part base, completed by this checked deterministic finishing step.

## Current results and reproduction

**54 parts = 36 SMT + 18 THT; 621 track segments, 55 routing vias**, plus twelve
U1 thermal-land holes. Current KiCad 9.0.2 **ERC 0, DRC 0, unconnected 0, parity 0**.
BOM checks expand every grouped reference and validate value, exact code,
footprint, uniqueness and both CPL memberships. Every intended schematic node
is compared to actual PCB pads, separately from the generic parity check.

Run `generate.py`, `route.py`, `export.py` as separate KiCad-container processes
using the [README commands](README.md#rebuild). Then run `packaging.py` and
`render-views.py` in the isolated geometry/render environment, inspect current
views, and run `finalize.py` last. This regenerates Gerbers/drill/ZIP, schematic,
BOM/CPL/reconciliation, board STEP, checked envelope STL and previews before
creating the comprehensive `checksums.json`. UUIDs/timestamps can change hashes
on regeneration; this is geometric/electrical reproducibility, not byte-for-byte
deterministic KiCad export.

The regenerated envelope STL remains watertight with consistent winding,
positive ~6533.13 mm³ volume and 58.1185 × 80 × 1.6 mm bounds. Its omitted
components/drills and unassigned installed Z are documented in
[PACKAGING.md](PACKAGING.md). Current board STEP includes 199 drilled holes.
The 52-part review hashes remain historical only; use the new manifest for
focused recheck. The reviewer owns the recheck decision and report.
