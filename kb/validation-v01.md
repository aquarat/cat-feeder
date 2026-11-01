# Historical v0.1 geometry validation — 2026-10-24

This records the earlier explicit-honeycomb, two-clip revision. See
[current validation](validation.md) for the domed, one-clip, floor-supported revision.

**Evidence: computed meshes and sampled motion, not physical prints.**
Reproduce with `bash scripts/export.sh`, `python3 scripts/check_mesh.py`, then
`bash scripts/check_clearances.sh`. Uses the rowing OpenSCAD image, Manifold
backend and the fork's `geometry-metrics` capability.

## Results

- Eight prototype meshes have closed triangle edges and one outward solid
  surface each. The honeycomb coupon additionally has 35 enclosed void surfaces.
- All eight fit within a 170 × 170 × 170 mm envelope, resting at Z=0.
- Tray sector: **139.67 × 139.67 × 17.2 mm**.
- Insulation quadrant: **145.19 × 145.19 × 18 mm**; its seams are between
  cooling sites. This is still a packaging coupon without joining/retention.
- Bowl void, integrated from its actual mesh: **53.201 mL** to the brim;
  **13.201 mL** headroom above the 40 mL working fill.
- Full shell and lid are each one connected solid, with **344 / 493** enclosed
  air-cell surfaces respectively. These whole models exceed the print bed and
  are verification models in `build/checks/`, not final manufacturing parts.
- Nominal body diameter is 300 mm; rear hinge increases model depth to 306.5 mm.

The dry coupling, adjacent sectors, closed lid and closed clips have no material
interference above the 0.001 mm³ numerical threshold. Sampled tray rotation
**0–30° in 5° steps** and lid opening **0–110° in 10° steps** pass against their
modelled surrounding geometry. Values around 1e-9 mm³ are numerical residuals.
Discrete samples do not prove clearance at every intermediate angle or under
print tolerances, deflection, wear or foreign material. The display's 110° pose
does not provide a physical lid support/stop.

## Defects caught and fixed

- The reused production IMU hinge axis is at **Y=32.0 mm**, not its rear wall at
  Y=28.5. An early adapter used the wall coordinate, detaching the hinge and
  creating a small collision during opening. Corrected the translation and
  added full-shell/lid connectedness checks as well as motion checks.
- Added a drive shoulder and blind shaft-tip datum after the mechanical review
  found the hub's axial position was otherwise undefined.
- Brought the tray's dry flange onto the print bed; no suspended flange support
  is required in the prototype orientation.
- Moved deck seams between cooling pockets, added shell clearance and a support
  ledge. Cartridge compression/support and quadrant retention are still open.

## Mesh precision handling

Binary STL stores float32 coordinates. In the full shell export, 456 triangles
at complex intersections collapsed to exactly zero area after conversion.
The checker removes **only exact zero-area records**, then requires closed
two-triangle edges, a positive outer volume and a single outward solid surface
before saving the cleaned file. It does not weld nearby vertices, patch holes
or repair a genuinely disconnected/non-manifold mesh. No prototype part needed
this cleanup in the recorded run.

The machine-readable `build/geometry-report.json` records dimensions, volumes,
enclosed-void counts, cleanup counts and CAD source SHA-256 hashes. Export logs
and `build/logs/clearances.echo` retain the numerical evidence. Regenerate after
geometry changes; do not treat this dated page as a fresh test of a later design.

## Visual review

Reviewed generated opened, sectional and honeycomb cutaway views. The insulation
cutaway intentionally removes the top skin to show the cells; the normal lid
has continuous top and bottom skins. Heat-sink, fan and motor blocks remain
packaging envelopes. The [mechanical review](mechanical-review.md) lists the
remaining assembly and physical-trial work.
