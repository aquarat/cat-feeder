# Cat feeder

An easy-clean, screwless, refrigerated rotary feeder. **Early mechanical and
thermal prototype**, developed from [the original brief](initial-design-brief.md)
and the owner's subsequent decisions in [the project KB](kb/README.md).

**[Product-linked BOM](BOM.md)** — UK-oriented sourcing, trial/full quantities,
observed prices and fit dependencies. Start with one thermal wedge; see the
[sourcing evidence](kb/sourcing.md) for outstanding component choices.
The [TEC control recommendation](kb/tec-control.md) identifies a CP60440 sample
and DPS5005 bench regulator, with conditional three-series/four-parallel scaling.
The [PCB assembly review](kb/pcb-assembly.md) recommends JLCPCB Economic as the
first turnkey controller-board route. The [crescent controller draft](kb/pcb-design.md)
has passed independent review.
The [PCB supports and removable sink cradles](kb/pcb-packaging.md) are integrated.
Subsequent [electrical simulations and regression tests](kb/pcb-simulation.md)
identify regulator thermal, motor-supply ringing and interface limits requiring
qualification; no powered hardware or application firmware has been tested.

> **2026-10-25:** a [five-reviewer general review](kb/review-2026-10-25.md) found
> blockers in both PCB revisions and thermal/drag limits in the direct-contact
> concept. Do not quote the prepared JLCPCB project. Latest decisions: 24 V
> mains brick, electronics inside the case, a hand-soldered through-hole
> controller variant, and an exploratory cold-air plenum
> ([thermal](kb/plenum-thermal.md), [CAD study](kb/plenum-cad.md), [sizing](kb/plenum-sizing.md); [D32–D37](kb/decisions.md)). D34 controller cards:
> [electronics/d34](electronics/d34/README.md), [KB](kb/d34-controller.md).
> Plenum views: `bash scripts/export_plenum.sh` → `build/plenum/preview/`.

## Current direction

- **316 mm nominal body**, 280 mm rotating tray, twelve 40 mL working portions.
- Four lift-out tray quadrants, three rounded wedge bowls each. Every bowl is
  continuous; joins are outside the food cavities. Nominal floor **1.2 mm**,
  bowl depth **16 mm**, plan corner radius **5 mm**, floor fillet **3 mm**.
- A broad, uniquely keyed **axial drive coupling** on the stepper. Lift the
  carrier and tray straight off; no shaft screw, nut or fastening operation.
  This resembles a large gear but does not provide gear reduction.
- Rear pin hinge and **one front-right clip** reuse the rowing IMU mechanisms.
  Filament offcuts form the pins. The enlarged lid needs its own load/fit trial.
- **18 mm printed insulation deck**, low-infill enclosed construction; no foam.
- **Domed lid with a broad, gently sloping feeding recess**. The mouth edge
  stands just 2.8 mm above the tray rim. The rest of the lid grows thicker.
- **12 mm cylindrical walls**, with honeycomb specified by Bambu print settings.
  CAD describes the envelopes; there are no modelled honeycomb cavities.
- **Enclosed, slotted underside** and numerous narrow vertical side vents.
  Floor-rooted seats, guides and bounded electrical bays load from the top.
- **Twelve distributed cooling positions**, one beneath each parked portion,
  replacing the custom circular aluminium plate. The current layout reserves
  40 mm TECs directly contacting the PETG tray and individual heat sinks. Final TEC size,
  count and power depend on the thermal study and a single-position experiment.
- One common fan and local thermostatic control. The original 100 W USB-C supply
  remains a candidate, not a proven budget for this revised cooling layout.
- Bottom **120 mm upward-blowing axial fan**, with a printed inlet skirt,
  enlarged floor intake and raised side exhaust band. See [airflow study](kb/airflow.md).

## Files and views

| File | Purpose |
| --- | --- |
| `cad/parameters.scad` | Dimensions, provisional component envelopes and clearances |
| `cad/feeder.scad` | Parametric assembly, section, exploded view and prototype parts |
| `cad/internals.scad` | Floor supports, removable motor bridge, board bays and loading paths |
| `cad/pcb_mount.scad` | Crescent PCB edge seat, lift-out sink cradles and staged loading paths |
| `docker/openscad.Dockerfile` | Headless build of the pinned public OpenSCAD fork |
| `scripts/openscad.sh` | Run OpenSCAD in that Docker image, with this project mounted |
| `scripts/fetch_references.py` | Fetch the manufacturer datasheets listed in `references.json` |
| `scripts/export.sh` | Export prototype STLs and current PNG views |
| `scripts/check_mesh.py` | Actual mesh topology, connectedness, bed fit and bowl capacity |
| `kb/` | Decisions, evidence, open questions and handover notes |
| `thermal/` | Thermal modelling tools and their results |
| `slicer/` | Editable Bambu project plate generation and print settings |
| `cad/lib/` | Hinge/clip mechanisms and edge helpers vendored from upstream ([provenance](#provenance)) |

Generated outputs are in `build/stl/`, `build/preview/` and
`build/geometry-report.json`. `capacity.stl` is the **empty volume of one bowl**
for measurement, not a printable part. Colours in assembly views distinguish
components; the rectangular heat sinks and fan are packaging envelopes.

[Opened assembly](build/preview/opened.png) ·
[Section](build/preview/section.png) ·
[Feeding recess](build/preview/access.png) ·
[Component bays](build/preview/loading.png) ·
[Underside](build/preview/underside.png) ·
[Fan inlet coupon](build/preview/fan_inlet_coupon.png)

The bowl capacity is **53.20 mL**. The full lid and shell remain assembly-scale
models requiring printable subdivision. See [validation details and limits](kb/validation.md)
for the tested revision and [the drop-in layout](kb/drop-in-layout.md) for assembly order.
The current thirteen prototype meshes and 44 nominal clearance checks pass; eleven
editable, unsliced Bambu projects are available in [slicer/plates](slicer/plates/).
The PCB fit study adds 21 passing checks against the integrated shell.

The [earlier thermal study](kb/thermal-model.md) identifies lateral heat spreading
as an unresolved issue with small cold footprints. The latest prototype removes
the small aluminium caps and tests direct TEC-to-PETG contact. Start with one
instrumented wedge and its insulated cover before scaling to twelve sites.
The [direct-contact comparison](kb/direct-contact-thermal.md) finds only about
0.3–0.4°C higher mean food-layer temperature without the small caps under matched
ideal cold-face conditions; contact gaps matter more. These are simulations.

## Reproduce

The CAD scripts run a headless OpenSCAD in Docker. Build the image once
(20–40 minutes; it compiles the pinned
[public OpenSCAD fork](https://github.com/aquarat/openscad), which adds the
experimental `geometry-metrics` checks):

```sh
docker build -t cat-feeder-openscad -f docker/openscad.Dockerfile docker
```

Manufacturer datasheets are not redistributed. Fetch them to the paths the
documentation cites (hash-checked against the revisions used):

```sh
python3 scripts/fetch_references.py
```

Export and check:

```sh
bash scripts/export.sh
python3 scripts/check_mesh.py
bash scripts/check_clearances.sh
python3 slicer/make_plates.py --require-part lid_access_coupon --require-part motor_bridge --require-part fan_inlet_coupon --require-part pcb_cradle --require-part pcb_mount_coupon
python3 slicer/make_plates.py --verify-only
```

Editable **unsliced** Bambu projects are written to `slicer/plates/`. Open them
as projects and retain their settings, then slice in Bambu Studio. No GUI or
slicer executable is required to generate these files here; no print G-code
is claimed. See [printing notes](kb/printing.md).

For one part or a parameter variation:

```sh
mkdir -p build/stl
bash scripts/openscad.sh --backend=Manifold --export-format binstl \
  -D 'part="sector"' -D 'floor_t=1.6' \
  -o build/stl/sector-thicker.stl cad/feeder.scad
```

## Prototype print order

1. **One tray sector**: check 40 mL filling, cat access, leakage and cleaning.
   Print flat underside down. The dry inner flange is on the bed too.
2. **Drive and hub**: check the measured motor shaft, master-tooth engagement,
   vertical removal and torque. Nominal sliding clearance is 0.3 mm per side;
   the provisional 5 mm D shaft has a separate close fit. The drive's blind
   socket seats on the shaft tip, its shoulder supports the hub, and two tabs
   provide a finger grip. The motor envelope assumes a 28 mm body/18 mm shaft.
3. **Rowing closure coupons and clip**: reproduce the actual hinge/catch
   interfaces. These are upstream coupons, not a full-size lid strength test.
4. **One insulation quadrant**: cold face down, as exported. Start with
   0.8 mm skins and 5–8% infill; inspect closure of the infill and print accuracy.
   This is a packaging coupon; module retention and moisture detailing follow
   the selected cooling cartridge.
5. **Insulation coupon**: a plain 60 mm square envelope. Apply the Bambu
   honeycomb/skin settings and inspect the generated infill and roof layers.
6. **Feeding-access coupon**: the actual front section of the sloped lid,
   including its thin opening lip. Check access and whisker clearance over a tray.
7. **Motor bridge**: its 2 mm bearing lip sits 1 mm above the fan; check seating
   on the four floor posts and the actual motor before a full loaded build.
8. **Fan-inlet coupon**: trial the actual enlarged floor slots, 2 mm-high inlet
    skirt and corner seats with the selected 120 mm fan before printing the shell.
9. **PCB mount coupon and two cradles**: check the edge seat, locating sockets,
   actual solder tails and driver stack. The cradle project contains one copy;
   print two for the assembly. Connect terminal wires after seating the PCB.

PETG, 0.4 mm nozzle and 0.2 mm layers are the initial process assumptions.
Use solid floors/perimeters on food parts; low infill applies to insulation,
not liquid-retaining walls. Rounded geometry helps washing, but does not by
itself establish FDM surface cleanability or food-contact suitability. Treat
these as water/fit prototypes until the material and cleaning process are settled.

## What is modelled versus resolved

The tray, drive, closure coupons, feeding-access coupon and removable motor
bridge have exportable prototype geometry. Mesh checks establish printable size
and closed surfaces, not physical fit, lifetime or liquid tightness.

The **full shell and lid are assembly studies**, not final A1 Mini prints.
Their quadrant joints, full-size lid support/stop, anti-lift retention, fan duct,
indexing sensor, condensate management and cartridge clamps still need detail.
Bounded electronics bays and floor-supported component seats are present. The
crescent uses its actual PCB outline with provisional component/harness heights;
the other three pockets remain unselected module allowances. The deck needs final quadrant joining and
cartridge retention features. Final hardware dimensions and firmware pinout
are not frozen.

The direct-contact prototype needs repeatable TEC face height and hot-side
contact with its sink. The deck carries the tray around each exposed cold face;
physical flatness/contact and sliding drag need a trial. Small aluminium caps
are removed. A proven long-life spring clamp is not a prerequisite for testing
the concept, but the final hot-side retention method remains to qualify.

Daily operation should be: release the clip, open lid, lift the complete tray by
its carrier, separate quadrants for washing/refilling, reseat and close. The
hub's unique key restores mechanical phase; starting a new food batch must
still reset the serving count. The four identical tray quadrants can otherwise
be exchanged, so lifting/reloading during an active batch requires rechecking it.

## Provenance

`cad/lib/` holds three OpenSCAD files vendored from the author's rowing-computer
project, unchanged apart from include paths: `sensor.scad` (the rear pin hinge
and clip mechanisms, rowing revision `5eb1d5683712bf8eaba0b004c4f59e09f8ab5160`)
and `edges.scad`/`dfm.scad`, which are also published in the
[OpenSCAD fork](https://github.com/aquarat/openscad) at
`12b187123519cd9050ce37341aefaa3e31ced1f7`.

This repository is a published snapshot of the project's working repository.
Issues and pull requests are welcome; accepted changes are applied upstream
and appear here in the next snapshot.

## Licence

Copyleft throughout: CERN-OHL-S-2.0 for hardware designs, GPL-3.0-or-later for
software, CC-BY-SA-4.0 for documentation, plus third-party AGPL/SparkFun files.
See [LICENSE.md](LICENSE.md). This is an untested prototype; no warranty.
