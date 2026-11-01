# One-compartment thermal screening

## Direct ceramic contact study (2026-10-24)

```sh
python3 thermal/direct_contact.py
```

This imports the existing solver with unchanged historical defaults and writes
to **`thermal/direct-output/`** (or `--output PATH`). Read the
[direct-contact interpretation](../kb/direct-contact-thermal.md). It compares a
40 × 40 mm ceramic face with **zero added aluminium**, a single 30 × 30 mm
candidate, and the historical 41.28 × 41.28 × 3 mm cap at radius 105 mm.

- `steady_cases.csv`: matched open/covered scenarios, imposed 0/2°C cold faces,
  perfect contact, added contact resistance and 0.05/0.2/1 mm air gaps.
- `decomposition_controls.csv`: fixed-footprint aluminium-removal and
  fixed-aluminium footprint-change controls.
- `boundary_material_sensitivity.csv`: separate sheltered-air, warmer ambient,
  top heat-transfer, food and deck conductivity sensitivities.
- `grid_convergence.csv`: 2/1 mm ideal cases; 0.5 mm for both direct40 environments
  at 0°C and the historical-cap/direct30 open comparisons at 0°C.
- `transient.csv`: four-hour food-only histories, 60-second steps; initially
  4/25°C direct40 food, plus selected gap and footprint comparisons.
- `time_convergence.csv`: 30/60/300-second steps at 15/60/120 minutes for direct40,
  ideal 0°C, both environments and initial temperatures.
- `conditional_foodpath_loads.csv`: illustrative eleven-covered/one-open sums,
  twelve-open sums and initial extraction loads, **not whole-unit or electrical watts**.
- `results.json`: every steady case's full parameters, solver/driver hashes,
  numerical checks and summaries; SVG/field CSV pairs show direct40 open/covered.

Every transient step checks boundary/storage energy balance, with integrated
energy reported in the histories. Steady cases enforce energy/temperature bounds;
the driver also checks contact, cold-face and footprint monotonicity and runs the
historical solver's independent analytic/conservation checks. Geometry is still
an explicit snapshot. The fixed ceramic boundary does not resolve ceramic
temperature gradients, TEC operating conditions, contact mechanics or durability.

## Historical cap and footprint study

Python 3.10+; standard library only. No installation, OpenSCAD, NumPy or system
changes required. From the project root:

```sh
python3 thermal/model.py
python3 thermal/model.py --checks-only
```

The first command regenerates `thermal/output/` (or pass `--output PATH`):

- `results.json`: all scenario parameters, numerical checks and summary results.
- `steady_cases.csv`: baseline, full-area reference and sensitivity cases.
- `grid_convergence.csv`: 4, 2, 1 and 0.5 mm grids.
- `transient.csv`: 4-hour histories, initially 4°C or 25°C, local or full plate.
- `time_convergence.csv`: 60 versus 300 second steps, compared at two hours.
- `footprint_comparison.csv`: original square, 60 × 40 mm rectangles at r105/r107,
  70 × 30 mm at r100, two 30 mm squares at r82/r115, and full-area reference;
  identical nominal, sheltered-top and low-top-coefficient boundaries for each.
- `footprint_fit.csv`: analytic twelve-site fit, outer radius and sensitivity to
  0.3 mm per-side pocket clearance.
- `footprint_grid_convergence.csv`: 2 and 1 mm grids for every footprint/environment;
  additionally 0.5 mm for the near-4°C 60 × 40/r105 low-h case.
- `*_nominal.svg`: one nominal heatmap for each comparison footprint.
- `local_baseline_field.csv`, `full_plate_reference_field.csv`: cell coordinates,
  food-layer-average temperatures and cold-contact fractions on the 2 mm grid.
- Matching `.svg` heatmaps: common 0–25°C scale; dashed square is the cold cap.

The script asserts energy conservation, a uniform equilibrium, an analytic
full-plate solution, steady maximum-principle bounds, rectangle-union area
without overlap double-counting, and analytical site-fit checks. No runtime package
dependencies or hardware access. Geometry and properties are explicit in the
`Parameters` dataclass; they are a design snapshot, not automatically imported
from CAD. Change parameters and regenerate when the design changes.

Read [the engineering interpretation](../kb/thermal-model.md) before using the
numbers. Fixed cold-face temperature is an optimistic boundary condition;
the model neither selects a TEC nor validates food-top temperature.

The new rectangles are **generic commodity-size candidates, not verified
purchases**. Every cooled rectangle is assumed isothermal at 0°C; the solver
does not predict spreading within a real larger plate or select its TECs.
The sheltered case fixes top air at **10°C and underside at 30°C**. It is not
the older sensitivity with both reservoirs at 10°C, nor a prediction that the
printed honeycomb enclosure will achieve 10°C internally.

## Cold-air plenum comparison (D35)

```sh
python3 thermal/plenum.py
```

Compares direct 40 mm contact at 0 to −15 °C faces with a forced-air plenum
under the tray (air temperature × h sweep), adds a cold-chamber heat balance,
fitted TEC sizing and food pull-down. Outputs go in `plenum-output/`. It imports the
solver without changing its defaults. Interpretation and labels:
[plenum thermal study](../kb/plenum-thermal.md). Simulated and estimated only.

```sh
cd thermal && python3 plenum_cad.py   # ~11 min
```

Re-runs the plenum on the CAD study geometry (15 × 77.5 mm channel, four sites).
It models plate-fin hot and cold sinks, datasheet fan and blower curves and the
shell's slot resistance, then the TEC operating points, food, open exposure and
pull-down. Outputs go in `plenum-cad-output/`. See
[plenum sizing](../kb/plenum-sizing.md). Estimates only.

**Stocked and candidate sinks (2026-10-26).** `SINKS_STOCK`/`COLD_STOCK` hold drawn
geometry for the stocked trial sinks (Fischer SK 100 75 SA, TED TDEX6015/TH) and the
cut-to-length candidates (Alutronic PR 614 and PR 411, Fischer SK 444). The source drawings
are in [`datasheets/`](datasheets/) with `MANIFEST.json` (URL, SHA-256, date; fetch with `scripts/fetch_references.py`). Explicit
cold bypass ducts (`cold_slots`) and the extra `food_target.csv`/`current_capped.csv`
checks are new. Simulation: the stocked pair is infeasible, and PR 614 + PR 411 meets the
targets with thin margin (see [plenum sizing](../kb/plenum-sizing.md#stocked-and-candidate-sinks-2026-10-26-later-pass-sim-est)).
