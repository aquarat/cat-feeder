# Floor-supported drop-in internals

2026-10-24 geometry study. Latest owner direction: closed lower floor with long
slit vents, floor-supported equipment, bounded electrical pockets, top loading
through the lid seam and no screws. This page supplements [decisions](decisions.md)
and supersedes the missing-support observations in the historical
[mechanical review](mechanical-review.md) only where described below.

## Geometry and load paths

**Later integrated PCB revision:** [PCB packaging](pcb-packaging.md) supersedes
the devkit pocket and two of the twelve support sets described below. The main
shell now calls `pcb_adapted_internals()` and has four ledge notches. A real
crescent-outline PCB seats at Z33 beneath two removable cradles. The other three
board pockets remain legacy allowances, not selected power-module interfaces.
Use the new page's staged service order: seat the PCB before wiring it, then
install cradles and cartridges. The old four-board checks below are historical;
the current [44 main and 21 PCB checks](validation.md) use the adapted assembly.

`cad/internals.scad` provides `internals()` for union into the lower enclosure,
`electronics_envelopes()` for assembly previews, `motor_bridge()` in assembly
coordinates, `motor_bridge_print()` with its underside at Z=0, and
`component_support_checks()` for the existing geometry-metrics checks.
There is no top-level geometry in this library.

- Floor top is Z=28 mm (25 mm legs + 3 mm base). All fixed supports penetrate
  that floor by 0.02 mm; these are integral features of the enclosure.
- Twelve radial 40 × 40 × 40 mm sink envelopes sit on four 3 × 3 mm corner
  posts each, at Z=58 mm. Short L-shaped guides locate their corners laterally.
  Their roots reach the floor independently of the deck. Guides stop at Z=64.
  Removing the 3 mm cold caps raised the sink seats by 3 mm: sink top Z=98,
  direct TEC face Z=102, level with the deck and tray underside.
  A real finned sink must have suitable bearing lands, or need a revised adapter.
- The central 120 × 120 × 25 mm fan sits at Z=30 on four corner seats with
  open-top side guides. A floor-rooted 118 mm outer / 114 mm inner square skirt
  rises from Z28 to Z30 beneath the fan frame to reduce suction recirculation.
  The 34 floor slots retain at least 0.95 mm nominal clearance to corner seats
  after easing. Frame/pad contact and flow resistance need a physical trial;
  see [airflow](airflow.md) and the separate fan-inlet coupon.
- Four motor-support pillars at X=±67, Y=±20 stay outside the fan envelope.
  Their locating nibs engage blind sockets beneath a removable bridge. Gravity
  seats the bridge; its square 43 mm pocket laterally locates the 42 mm motor.
  This is positive lateral location, not a qualified anti-lift clip.
- Motor bottom Z=58 and fan top Z=55 leave 3 mm. Integration lowered the fan
  and increased the bridge's bearing lip from 0.8 to **2 mm**, starting at Z=56,
  giving **1 mm nominal fan clearance**. Side arms are 4.8 mm thick. The bridge
  still needs a stiffness, print tolerance and warm-creep trial.
  Bridge removal is required before lifting out the fan.
- An open-top perimeter raceway has walls at radii 135–136.2 and 141–142.2 mm,
  with lead gates at the twelve cartridge axes and short radial lead channels.
  A separate short channel serves the fan/motor area. These reserve routing
  space; they are not a completed harness, connector or strain-relief design.

## Provisional electronics

The local `provisional_boards` list is the single source for pockets and envelopes.
Dimensions are **unselected component allowances**, not measured final PCBs.
The stated height must include underside components; the model's solid seat
does not provide standoffs or clearance for unmodelled solder joints.

| Candidate | Centre X,Y (mm) | Radial × tangential × height (mm) | Bottom/top Z |
|---|---:|---:|---:|
| ESP32 devkit | 105,0 | 28 × 52 × 13 | 29.5 / 42.5 |
| USB PD | 0,105 | 22 × 30 × 8 | 29.5 / 37.5 |
| Buck converter | -105,0 | 25 × 45 × 15 | 29.5 / 44.5 |
| Motor driver | 0,-105 | 16 × 20 × 12 | 29.5 / 41.5 |

Each shallow four-sided pocket has 0.5 mm side allowance, 1.5 mm walls and an
open-top lead notch. Pockets sit below four cartridge positions, between their
corner supports. No fixed bridge crosses their vertical insertion paths.
Connector protrusions, USB cable bend radius, electrical insulation, power
distribution, sensors and final driver/power ratings remain unselected.
The later [DPS5005 recommendation](tec-control.md) is bench equipment for now:
its 42 × 45 × 80 mm assembly exceeds the provisional converter pocket. The
current loading checks do not claim to fit that regulator or its wiring.

## Installation and servicing order

1. Open the lid; remove tray, hub/drive and removable deck pieces as needed to
   expose the lower enclosure. The lid seam is the only loading entrance.
2. Lower the four electronics modules into their floor pockets. Lay leads into
   the open notches/channels before installing cartridges above them.
3. Lower the fan between its corner guides.
4. Lower the motor bridge onto its four floor-rooted locating posts, then lower
   the motor into its square pocket. It can also be lowered with the motor.
5. Lower the sink/TEC assemblies onto their corner seats.
6. Install the removable deck over the TECs, followed by drive/hub and food tray.
   There are no cold caps. The 41.2 mm through-windows clear the provisional
   40 mm TEC bodies; actual edge seals and lead exits need a sample fit.

Reverse this order for deep service. Electronics are accessible after lifting
their overlying cartridges and deck pieces. This is tool-free staged assembly,
not unrestricted access to every component without removing other parts.
Food-contact daily cleaning should not require dismantling this equipment bay.

## Limits and evidence

The bridge is separately printable flat-side down; its small blind locating
socket roofs still require slicer inspection. The integral supports print with
the lower enclosure. Full enclosure segmentation/bed compatibility is separate.
The seats support component weight; **they do not implement thermal compression,
TEC face-height adjustment, moisture sealing, motor axial retention or a complete
screwless cartridge**. See [component mounting evidence](component-references.md).
No physical fit, cooling, load, airflow or cleaning trial is claimed.

`component_support_checks()` checks actual boolean intersections for fixed
supports against component envelopes, bridge against equipment and supports,
and vertical board/fan/sink/motor insertion paths at nominal dimensions. Complete
assembly checks must additionally include the primary agent's shell, floor vent
cuts, deck, tray and lid. Export and mesh results are recorded below when run.

### Local verification, 2026-10-24

The following was the subagent's initial verification, before the fan/bridge
clearance improvement and full-shell integration. Current evidence belongs in
the regenerated main geometry report and [validation](validation.md).

Used the pinned `rowing-openscad` image, Manifold backend and
`--enable=geometry-metrics`, overriding `deck_z=84` and `body_r=158` while the
primary parameter edit was pending. The floor/fan defaults were 28/32 mm.
All seven intersection checks passed the existing 0.001 mm³ threshold; the
largest residual was 1.56e-11 mm³. These check nominal straight vertical loading,
not deflection, hand access or clearance to the unintegrated shell/deck.

Exported the bridge and fixed supports; additionally unioned the latter with a
**surrogate unvented Ø292 × 3 mm floor**, solely to verify every support root
connects. The existing standard-library STL checker found:

| Export | Actual mesh bounds (mm) | Topology |
|---|---|---|
| Print-oriented motor bridge | 142 × 50 × 6.8, bottom Z=0 | One connected outward closed surface; 216 triangles |
| Supports + surrogate floor | 292 × 292 × 36, bottom Z=25 | One connected outward closed surface; 5,864 triangles |

Neither mesh needed zero-area-triangle cleanup. Reviewed the rendered oblique
view of supports, bridge and board envelopes: board wells remain open between
the cartridge posts, and the removable bridge seats on the four central pillars.
This is a local geometry result, not validation of the final vented enclosure.

The checked `internals.scad` SHA-256 is
`a7914d2e92eac363592a25c4ee3104e5f26a363936188f28f4a2d785bf33088b`.
Temporary verification wrappers, images, STLs, echo log and JSON report were kept
in scratch outside the repository; regenerate final build outputs after integration.
