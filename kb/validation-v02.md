# Historical geometry validation — v0.2, 2026-10-24

This records the small-cap revision before direct TEC contact and the raised
exhaust/inlet-skirt changes. See [current validation](validation.md); generated
build outputs now belong to that newer revision.

Current design: domed/sloped lid, one clip, thick solid-envelope shell, vented
floor and top-loaded component bays. Honeycomb belongs to the slicer. The
[v0.1 record](validation-v01.md) preserves earlier tests and lessons.

## Reproduce

```sh
bash scripts/export.sh
python3 scripts/check_mesh.py
bash scripts/check_clearances.sh
python3 slicer/make_plates.py --require-part lid_access_coupon --require-part motor_bridge
python3 slicer/make_plates.py --verify-only
```

Geometry output: `build/geometry-report.json`, source SHA-256 hashes, export
logs and `build/logs/clearances.echo`. Bambu project evidence is in
`slicer/plates/plate-report.json`. These are numerical/model checks, not physical
print, load, airflow, cleanability or cooling tests.

## Scope

**Recorded result: PASS.** Ten prototype meshes fit the 170 mm design envelope;
shell/lid are connected and closed; all 37 nominal interference/loading/motion
checks pass. Eight unsliced Bambu projects containing those ten exact source
meshes pass archive, mesh, settings, source-hash and bed/brim-placement checks.

| Item | Measured mesh size (mm) |
| --- | --- |
| Tray sector | 139.666 × 139.665 × 17.2 |
| Feeding-access coupon | 144 × 110 × 16.839 |
| Motor bridge | 142 × 50 × 6.8 |
| Insulation coupon | 60 × 60 × 9.2 |
| Full shell, including hinge | 316 × 322.5 × 123.5 |
| Full lid, including hinge | 316 × 322.5 × 24.1 |

The bowl remains 53.201 mL to the brim. Shell, lid and insulation coupon have
**zero enclosed CAD voids**. The shell needed 232 exact zero-area float32
triangle removals; the prototype parts and lid needed none. Opened/closed,
feeding-recess, component-bay and underside renders were visually reviewed.

- Prototype mesh edges, winding/positive volume, connectedness and bed bounds.
  Ten small prototype parts are intended for the 170 mm design envelope.
- Full shell/lid connectedness is checked separately; these whole objects are
  too large for the A1 Mini and are not issued as printing plates.
- No explicit enclosed honeycomb CAD voids should remain in the new insulation
  coupon, shell or lid. Slicer infill creates the retained-air structure.
- Actual bowl capacity is measured by integrating its exported cavity solid.
- Fixed supports versus component envelopes; bridge versus supports/equipment;
  deck versus shell/supports; vertical component loading paths through the shell.
- Adjacent tray sectors, drive/hub/deck, closed lid/clip, lid motion in 10° steps
  to 110°, and tray motion in 5° steps through one 30° advance.

The positive-clearance tests use a 0.001 mm³ intersection threshold; residuals
around 1e-9 mm³ are numerical noise. Samples do not establish continuous motion
under print tolerances or deformation. The modelled 110° lid pose still needs
a physical hold-open stop/support.

## Checks added for this revision

- The domed lid is an explicitly wound polyhedron. Initial export checks caught
  reversed face winding and a coplanar mouth-chamfer termination. Faces now use
  OpenSCAD's outside-clockwise convention and the cutter continues past the lip
  plane. The access coupon then exported as one positive, closed solid without
  triangle cleanup.
- Original thin motor bridge allowance was improved: fan top Z=55, motor bottom
  Z=58, bridge lip 2 mm, leaving 1 mm fan-to-bridge clearance. Nominal insertion
  paths pass independently of component shape/load qualification.
- Equipment pockets retain solid floor beneath them; intake slots are confined
  to the fan region. Complete-shell mesh connectedness checks include the actual
  vents, support roots and base rather than a surrogate floor.

The mesh checker may remove only exactly zero-area float32 export triangles and
then requires closed edges and a connected positive solid. It does not weld by
tolerance, patch holes or conceal reversed/disconnected solids. Counts are in
the report; regenerating overwrites earlier outputs.
