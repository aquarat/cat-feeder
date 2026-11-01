# Geometry validation — v0.3, 2026-10-24

Direct ceramic/PETG contact, raised hot-bay exhausts, expanded bottom intake,
floor-rooted fan skirt and integrated crescent PCB/cradles. Historical results: [v0.2](validation-v02.md),
[v0.1](validation-v01.md). These are model checks, not physical tests.

## Reproduce

```sh
bash scripts/export.sh
python3 scripts/check_mesh.py
bash scripts/check_clearances.sh
python3 slicer/make_plates.py --require-part lid_access_coupon --require-part motor_bridge --require-part fan_inlet_coupon --require-part pcb_cradle --require-part pcb_mount_coupon
python3 slicer/make_plates.py --verify-only
```

## Recorded result

**PASS:** thirteen connected, closed prototype meshes fit the 170 mm design
envelope; full shell/lid are connected and closed; **44 nominal clearance,
loading and sampled-motion checks** pass. **Eleven unsliced Bambu projects**
contain the thirteen exact prototype meshes and pass independent read-back,
hash, settings and bed/brim-placement checks.
The separate [PCB fit study](pcb-packaging.md) passes 21 checks against the
actual integrated shell. Maximum residuals are 7.51e-10 mm³ (main) and
1.13e-10 mm³ (PCB study), below the 0.001 mm³ threshold.

| Item | Actual mesh bounds (mm) |
|---|---|
| Tray sector | 139.666 × 139.665 × 17.2 |
| Deck quarter | 145.192 × 145.192 × 18 |
| Feeding-access coupon | 144 × 110 × 16.839 |
| Motor bridge | 142 × 50 × 6.8 |
| Fan-inlet coupon | 124 × 124 × 11 |
| PCB cradle, two required | 61.599 × 44 × 9 |
| PCB mount coupon | 66 × 88 × 32 |
| Insulation coupon | 60 × 60 × 9.2 |
| Full shell including hinge | 316 × 322.5 × 123.5 |
| Full lid including hinge | 316 × 322.5 × 24.1 |

Current cavity volume is **53.201 mL**, leaving 13.201 mL nominal headroom at
40 mL. Shell, lid and insulation coupon have zero enclosed CAD voids; sparse
honeycomb is a slicer setting. The shell export needed **232 exactly zero-area
float32 triangle removals**; prototype parts and lid needed none. Mesh checking
does not weld, patch holes or use tolerance-based repairs.

Results/source SHA-256: `build/geometry-report.json`. Export logs and
`build/logs/clearances.echo` record the actual runs. Plate evidence is in
`slicer/plates/plate-report.json`. Closed, underside, section, loading and fan
coupon views were inspected after the changed geometry was exported.

## Revision-specific checks

- Crescent PCB bottom Z33; edge seat and two removable sink cradles replace the
  obsolete devkit pocket and two support sets. Four ledge notches admit the
  cradles from above. Tests include unwired PCB insertion, cradle insertion,
  installed harness allowance and straight terminal-driver access. The two new
  bias resistors remain inside the existing 2 mm-high SMT envelope; the original
  52 placements and PCB outline are unchanged by the electrical corrections.

- Small cold caps and their deck recesses removed. Provisional 40 mm TEC faces
  now meet the deck/tray underside at Z102; 40 mm-high sink allowances occupy
  Z58–98. Nominal TEC/sink-versus-deck and TEC-versus-shell checks added.
- Tray rotation checks include direct TEC bodies at 5° samples across one 30°
  advance. They establish no positive-volume collision, not contact pressure,
  friction or tolerance-qualified indexing.
- Printed 118/114 mm square inlet skirt is integral with the floor at Z28–30.
  It is included in fan-envelope and vertical loading tests. No added outlet
  funnel competes with the bridge's 1 mm fan clearance.
- Floor cuts are 34 × 50 × 3.5 mm, with Y centres from −47 to +47 mm. The
  parameter assertion preserves 0.95 mm nominal clearance to corner seats after
  0.3 mm easing. The inlet coupon uses the same cuts, seats and skirt modules.
- 120 side slots are 3 × 22 mm, Z58–80. An assertion keeps them below the
  Z81–84 deck ledge. Full-shell topology includes these slots and support roots.
- Equipment remains floor-supported and staged top-loaded. The real 20 mm
  Fischer sink is **not** substituted for the 40 mm CAD allowance: only 6 mm
  would be exposed below the deck. See [airflow](airflow.md).

Intersections use a 0.001 mm³ threshold. Numerical residuals below 1e-9 mm³ do
not represent physical interference. Lid motion remains sampled in 10° steps
to 110°; support/stop, deflection, fits and retention require physical trials.
Whole shell/lid remain too large for the A1 Mini and need subdivisions/joints.
No GUI slicing, printing, installed-flow or refrigerator performance is claimed.
