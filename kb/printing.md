# Prototype printing — editable Bambu projects

Updated 2026-10-24. **UNSLICED preparation, not a successful print or a tested
refrigerator.** Latest owner direction puts honeycomb in **slicer infill settings**
inside solid CAD insulation volumes, rather than explicit CAD cells. No foam or
screw/bolt additions are involved. See [decisions](decisions.md),
[geometry validation](validation.md) and [mechanical review](mechanical-review.md).

## Generate and open

After the latest STL export and geometry checks finish, from the project root:

```sh
python3 slicer/make_plates.py
python3 slicer/make_plates.py --verify-only
```

Deliverables are in [`slicer/plates/`](../slicer/plates/). Open each `.3mf` **as a
project** in Bambu Studio and retain its settings. Geometry and settings are
editable. Slice and inspect there before printing. Regenerate whenever STLs or
process settings change; `--verify-only` rejects a changed source or configuration.
Save hand-edited projects elsewhere: generation replaces its output files.

The generator uses only Python's standard library and bundled profiles, offline.
This Linux aarch64 host has no available Bambu Studio/Orca/Prusa slicer executable;
no GUI, packages or remote machine were installed/used. The upstream rowing
sensor slicer was inspected read-only, including its exported clip orientation,
0.20 mm journal-layer requirement and solid-clip settings. Its sliced macOS
deliveries do not establish slicing or fit of these feeder parts.

## Plate plan and embedded settings

Every project selects **Bambu Lab A1 mini, 0.4 mm nozzle, Generic PETG, Textured
PEI**, 0.20 mm first and subsequent layers, adaptive layers off, Arachne walls,
5 mm outer brim, support off and print-by-layer. Each supplied part appears once;
these are prototype trials, not a complete feeder production kit.

| File prefix | Parts | Walls | Top/bottom | Infill |
|---|---|---:|---|---|
| `01-insulation-coupon` | `insulation_coupon` | 3 | 4 layers / 0.8 mm each | **8% honeycomb** |
| `02-closure-trials` | `closure_coupon_base`, `closure_coupon_lid`, `clip` | 6 | 6 layers / 1.2 mm each | **100% rectilinear** |
| `03-drive` | `drive` | 6 | 6 layers / 1.2 mm each | **100% rectilinear** |
| `04-hub` | `hub` | 6 | 6 layers / 1.2 mm each | 40% gyroid |
| `05-tray-sector` | `sector` | 5 | 6 layers / 1.2 mm each | **100% rectilinear** |
| `06-deck-quarter` | `deck_quarter` | 3 | 4 layers / 0.8 mm each | **8% honeycomb** |
| `07-lid-access-coupon` (if exported) | `lid_access_coupon` | 3 | 4 layers / 0.8 mm each | **8% honeycomb** |
| `08-motor-bridge` (if exported) | `motor_bridge` | 6 | 6 layers / 1.2 mm each | 40% gyroid |
| `09-fan-inlet-coupon` (if exported) | `fan_inlet_coupon` | 6 | 6 layers / 1.2 mm each | 40% gyroid |
| `10-pcb-cradle` (if exported; print twice) | `pcb_cradle` | 6 | 6 layers / 1.2 mm each | 40% gyroid |
| `11-pcb-mount-coupon` (if exported) | `pcb_mount_coupon` | 6 | 6 layers / 1.2 mm each | 40% gyroid |

All filenames end in `-unsliced.3mf`. Process settings live in
[`slicer/make_plates.py`](../slicer/make_plates.py), and are stored at project level
in each archive so small drive/clip parts cannot accidentally inherit insulating
infill. The complete project config embeds flattened official machine, process
and filament profiles with source hashes; no unresolved inheritance is required.
Profile provenance and schema references are in the [slicer README](../slicer/README.md).

Generic PETG defaults are **255°C nozzle, 70°C textured bed, 8 mm³/s volumetric
limit**, subject to the actual filament's calibration. Prototype overrides use
25 mm/s first-layer walls, 60 mm/s outer walls, 40 mm/s top surfaces and 25 mm/s
bridges. These are starting settings, not measured optimums. Machine start/end
and filament-change templates are embedded, but **no sliced G-code exists**.

Original STL orientation is preserved; only translations centre the parts on a
180 × 180 mm bed and seat them at Z=0. Clips keep their C-shaped spring profile
in XY and pin eye vertical. Mesh/brim bounds and source hashes are recorded in
[`plate-report.json`](../slicer/plates/plate-report.json). No whole shell/lid from
`build/checks`, capacity-measurement solid or purchased-part envelope is plated.
Full-size lid/shell subdivisions and joints need their own design/plate review.
The revised whole lid/body is Ø316 mm with a 12 mm body wall, exceeding this bed.
The lid-access coupon, motor bridge and fan-inlet coupon are separate exports.
To require all current optional parts, use
`python3 slicer/make_plates.py --require-part lid_access_coupon --require-part motor_bridge --require-part fan_inlet_coupon --require-part pcb_cradle --require-part pcb_mount_coupon`.

The bridge settings follow the [drop-in layout notes](drop-in-layout.md): keep its
flat-side-down export, six walls and 1.2 mm skins. Supports remain off for its
short blind locating-socket roofs, pending sliced bridge inspection. This is a
robust starting process, not proof of motor load capacity or warm PETG creep
resistance; the thin motor seat especially needs a physical trial.

## Trial sequence and limits

1. **Insulation coupon and closure trials first.** The intended insulation coupon
   is a plain solid 60 × 60 mm CAD volume; the generator always embeds whatever
   current `insulation_coupon.stl` was exported. If an older STL still contains
   explicit internal cavities, infill settings cannot fill those voids: re-export
   the revised solid CAD before the final delivery. `enclosed_mesh_voids` in the
   report distinguishes enclosed geometry cavities from slicer-generated infill.
2. In the sliced coupon/deck preview, check honeycomb and inspect the first solid
   roof layers for bridging and sag. **8% is an infill setting, not 92% retained air
   for the whole part**: skins, perimeters, ribs and small features add material.
   Honeycomb infill does not prove airtight cells or thermal performance. Thin
   local walls may become all-perimeter material despite low-density infill.
3. Check closure motion, pin fit and clip release before repeating prints. Keep
   0.20 mm layers and the exported spring orientation; support is disabled as a
   trial starting point. Inspect short bridges in the sliced preview.
4. Print one sector and confirm flatness, coupling fit and washing access. Six
   bottom layers target a continuous 1.2 mm floor, and solid infill avoids sparse
   regions in the thin food tray. **Settings alone do not establish watertightness**:
   check layer preview, calibrated extrusion and a physical water-hold trial.
   Hygiene, cleaning durability and food-contact suitability remain physical
   material/process questions; a closed mesh is not a sealed printed bowl.
5. Test one hub/drive with the actual stepper shaft before repeats. Deck quarters
   remain packaging/insulation prototypes; their settings do not validate thermal
   contact, clamps, sealing or a complete refrigeration assembly.

## Verification evidence

**Integrated v0.3 PCB handoff:** regenerated after adding the crescent support
coupon and removable cradles. All **eleven projects / thirteen meshes** pass
generation and independent `--verify-only` read-back. All five optional parts are included;
the insulation coupon has zero enclosed mesh voids. These remain unsliced.

Initial generator execution passed for **six archives / eight meshes** before the
later optional exports were available; final counts come from the current report.
It checks
exact source bytes by SHA-256; reopens each ZIP; verifies every serialized vertex
and face against its STL; checks closed consistently wound edges, positive volume,
object/part/plate mappings, embedded settings, unchanged orientation, bed contact
and non-overlapping conservative brim bounds. All published source/dimension
numbers belong to the accompanying report, and must be regenerated after CAD
changes. No earlier revision's mesh numbers or thermal results are reused here.

**Not yet established:** actual Bambu GUI import/round-trip, slicer warning-free
toolpaths, roof bridging, print time/mass, extrusion quality, fit, water sealing
or cooling. These projects provide reproducible inputs for that next slicing and
physical-trial step.
