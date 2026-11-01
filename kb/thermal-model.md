# Thermal propagation through one PETG food wedge

**Status: reproducible reduced-order simulation, 2026-10-24; not a physical test.**

**Historical cap baseline:** owner decision D19 now removes the small metal caps
and proceeds with direct TEC-to-PETG contact. The cap-based results and geometry
below remain comparison evidence, not the current CAD or purchasing direction.
See the [direct-contact comparison](direct-contact-thermal.md) for the new
40 mm/30 mm ceramic-face and contact-gap scenarios.

## Finding and design implication

With an ideal **0°C local cap**, the nominal conduction-dominated scenario gives
about **6.4°C mean and 11.7°C warmest thickness-averaged food**, whereas an ideal
full-footprint cold face gives about **2.0°C throughout the layer**. The weak point
is lateral heat travel from the inner tip to the small cap, in addition to the
vertical plastic/contact resistance. This is evidence to **prototype one real
wedge before sizing twelve TECs**, not evidence that the assembly meets a storage
temperature target or that it necessarily fails under every enclosure condition.

The latest architecture remains twelve stationary, individually sourced caps;
the full-area calculation is a diagnostic reference, not a proposal to restore
a custom aluminium disc. Simplicity and sourcing take priority over optimising
electrical efficiency. No foam is assumed.

**Footprint extension:** longer rectangular cold footprints materially improve
the same model. A 60 × 40 mm rectangle at r105 reduces the nominal 2 mm-grid
maximum from 11.96°C to **7.73°C**, but has just **0.186 mm nominal clearance**
between neighbouring sites. Moving it to r107 improves clearance while increasing
the maximum to **8.66°C**. A 70 × 30 mm rectangle and two 30 mm squares also improve
the original square, with different warm spots and packaging tradeoffs. See the
matched-boundary comparisons below; no candidate is validated for the food target.

### Geometry snapshot

This local-wedge study predates the v0.2 enclosure revision (316 mm outside,
12 mm walls, domed/sloped lid and slicer-generated honeycomb). Its food/cap
geometry remains applicable; it does not solve the new enclosure's chamber
temperature, airflow or whole-appliance insulation performance.

Taken from `cad/parameters.scad` and `food_outline()` in `cad/feeder.scad`:

- Twelve positions in a 300 mm diameter housing; analyse one parked compartment.
- Convex 26° wedge, outer radius 137 mm, flat inner truncation at **x = 62 mm**
  (not an inner circular arc), plan corner radius 5 mm.
- Floor 1.2 mm PETG; nominal food cavity depth 16 mm. Nominal portion 40 mL.
- Cap centred at x = 105 mm, y = 0; **41.28 × 41.28 × 3 mm aluminium**, square
  axes radial/tangential. A 40 × 40 mm TEC envelope is an allowance, not a selection.
- Printed low-infill deck 18 mm thick, without added foam.

The analytic plan mask performs the same circular erosion/dilation as the CAD
rounded outline, without CAD circle tessellation. At 0.5 mm grid spacing the
footprint is 33.55 cm²; 40 mL corresponds to **11.92 mm uniform depth**. Cap/food
overlap is 16.98 cm², **50.6%** of the footprint. The full cap area is 17.04 cm².
The 3 mm CAD floor-to-wall fillet, mouth chamfer and variable floor thickness
near walls are omitted; these numbers are not a mesh-derived capacity estimate.
The 16 mm sensitivity has approximately 54 mL, not 40 mL.

## Reproduce and inspect

```sh
python3 thermal/model.py
python3 thermal/model.py --checks-only
```

Python 3.10+ standard library only. Run from the project root. No installation or
system changes. The first command regenerates all outputs and runs the checks.
Geometry is explicit in `thermal/model.py`, not read live from changing CAD.

- [Model and usage](../thermal/README.md)
- [Local-cap map](../thermal/output/local_baseline.svg)
- [Full-area reference map](../thermal/output/full_plate_reference.svg)
- [Steady scenarios CSV](../thermal/output/steady_cases.csv)
- [Grid convergence CSV](../thermal/output/grid_convergence.csv)
- [Transient histories CSV](../thermal/output/transient.csv)
- [Time-step comparison CSV](../thermal/output/time_convergence.csv)
- [Complete parameter/result/check JSON](../thermal/output/results.json)
- [Matched footprint comparison CSV](../thermal/output/footprint_comparison.csv)
- [Analytic twelve-site fit CSV](../thermal/output/footprint_fit.csv)
- [Footprint/grid/environment refinement CSV](../thermal/output/footprint_grid_convergence.csv)

The SVGs and field CSVs use the **2 mm engineering/sensitivity grid**; finer-grid
summary results are separately identified. All temperatures below are food-layer
averages, even the column labelled “maximum”.

## Model and boundary conditions

A Cartesian finite-volume mask retains cells whose centres lie within the
rounded wedge. Every retained cell has area A = dx². Boundary faces form a
staircase; cold-cap fractional overlap with each square is calculated exactly.
For multiple rectangles this is the **union** of clipped rectangles, computed
using x slabs and merged y intervals; overlapping patches are never counted twice.
Thickness L is volume divided by the retained footprint, unless explicitly set.

For food-cell temperature T_i:

```text
C_i dT_i/dt = sum_j G_ij (T_j - T_i)
              + G_c,i (T_c - T_i)
              + G_a,i (T_a - T_i)
              + G_b,i (T_b - T_i)

C_i   = rho cp L A
G_ij  = k_food m L + k_PETG t_floor             [square adjacent cells]
R_c'' = t_floor/k_PETG + L/(2 k_food) + R_contact'' + t_Al/k_Al
G_c,i = f_i A / R_c''
G_a,i = h_top A + h_side L (exposed cell-edge length)
R_b'' = t_deck/k_deck + t_floor/k_PETG + L/(2 k_food)
G_b,i = (1-f_i) A / R_b''
```

R'' is area-normalised thermal resistance in m² K/W; G is W/K; f_i is cold
overlap fraction. m is an illustrative lateral transport multiplier, normally
1. The floor's small parallel lateral conductance is included by assuming it
shares the food node's local temperature. Food and floor are not separate
temperature fields. The half-food-depth resistance is a representative-centre
closure, **not an exact solution for a vertically stratified mean temperature**.
Top convection acts on that same node, not on a resolved top surface.

For the ideal full-area reference f_i = 1 everywhere. The deck-to-food pathway
then disappears because the fixed cold face intercepts it; any heat reaching
that ideal plate directly is outside this food-only model.

Steady equations are solved by Jacobi-preconditioned conjugate gradient with
relative residual tolerance 1e-10. Backward Euler gives transient results with
60-second steps, checked against 300-second steps. Reported `balance_W` is
ambient + underside input minus cold extraction: zero at steady state and equal
to stored-energy rate in a transient.

### Nominal assumptions, not measured material specifications

| Quantity | Value | Interpretation |
|---|---:|---|
| Food conductivity | 0.5 W/(m K) | Water-rich-food estimate; no bulk flow |
| Food density / heat capacity | 1000 kg/m³ / 3800 J/(kg K) | 40 mL has 152 J/K thermal capacity |
| PETG conductivity | 0.20 W/(m K) | Uniform effective solid floor; print anisotropy unresolved |
| Aluminium conductivity | 200 W/(m K) | 3 mm conduction resistance, isothermal cap boundary |
| Effective deck conductivity | 0.06 W/(m K) | Unverified low-infill print estimate; sweep 0.03–0.20 |
| Top coefficient | 5 W/(m² K) | Effective imposed top heat gain; sweep 1–10 |
| Top environment | 25°C | May represent ambient/open position; covered chamber unknown |
| Deck underside | 30°C | Illustrative warm-base boundary, not a solved heat sink |
| Cap cold face | 0°C | Held exactly, unlimited ideal cooling; also test 2°C |
| Added contact resistance | 0 | Optimistic perfect contact; floor resistance still present |
| Lateral wall boundary | Adiabatic | Side-heating stress case also provided |

On the 2 mm grid, nominal area resistances are approximately 0.0060 (floor),
0.0118 (half food layer) and 0.000015 (aluminium) m² K/W. Thus reducing aluminium
thickness resistance is unlikely to fix the dominant vertical restriction.
Nominal cold-patch U is about 56 W/(m² K); uncovered deck path U is about
3.15 W/(m² K). Radiation is not separately solved; the top coefficient can
represent an effective combined exchange but is not calibrated to a lid.

The latest confirmed printed honeycomb/retained-air top enclosure is not resolved
here. Its skins, webs, sealed cells and feeding opening require a separate
chamber/lid heat balance or measurements to establish the actual top environment
and effective coefficient. “Air-filled” alone does not establish conductivity:
solid webs, radiation and cell convection can matter. The top-h sweep is a
boundary-condition sensitivity, not a validated honeycomb insulation calculation.

## Steady results and nonzero holding load

2 mm grid, nominal parameters:

| Cold-face coverage | Mean °C | Minimum °C | Maximum °C | Food-to-cap W | Top input W | Deck input W |
|---|---:|---:|---:|---:|---:|---:|
| Local 41.28 mm square | 6.46 | 3.38 | 11.96 | 0.428 | 0.314 | 0.115 |
| Ideal whole footprint | 2.05 | 2.05 | 2.05 | 0.388 | 0.388 | 0 |

The nominal local case has **81% of plan area above 4°C in the averaged layer**.
The maximum is near the flat inner end, x ≈ 62 mm. The refined result is 6.37°C
mean, 11.66°C maximum and 0.426 W extracted.

Twelve identical nominal wedges would imply about **5.1 W of this modelled
food-path holding load**. That is **not the whole appliance load, a TEC rating,
or an electrical consumption estimate**. It excludes direct cap/deck bridges,
most walls/lid/seams, chamber leakage, moisture/condensation and TEC internal
back-conduction. Serving and covered positions do not share identical boundaries.
A lower extracted W in a poor-contact case can simply mean warmer food and less
heat gain, not improved cooling performance.

## Practical rectangular footprint comparisons

All dimensions below are **radial × tangential**, aligned with the compartment
centreline. The rectangular alternatives are generic commodity sizes to investigate,
**not verified purchases, an actual spreader design, or evidence of plate
isothermality**. All use the same assumed 3 mm aluminium thickness and ideal 0°C
cold boundary, 40 mL fill, PETG floor, deck, food properties and perfect contact.
The model has no separate in-plane aluminium temperature field: a small TEC under
a long plate does not automatically keep that whole plate at 0°C. Two patches
likewise both have imposed 0°C boundaries, without an assumed module arrangement.

### Twelve-position analytical fit

Each site's bisectors lie at ±15° because the positions repeat every 30°. For a
centred rectangle of radial length L, tangential width W and centre r:

```text
inner x = r - L/2
normal margin to site bisector = (r - L/2) sin(15°) - (W/2) cos(15°)
adjacent mirrored-site corner gap = 2 × minimum normal margin
outer corner radius = sqrt((r + L/2)² + (W/2)²)
```

For the two-rectangle candidate take the minimum margin across both rectangles.
Containment inside each site's angular sector proves nonoverlap for all twelve
rotations. For these mirror-symmetric candidates, the adjacent inward corner pair
also achieves the stated gap. Inflating a pocket by c per side replaces inner x
by inner x − c and half width by W/2 + c. Pocket c = 0.3 mm below is an illustrative
fit allowance matching the current CAD convention, not a tolerance qualification.

| Footprint / centre radius mm | Radial extent mm | Raw union cm² | Adjacent site gap mm | Gap with 0.3 mm pockets | Outer corner radius mm |
|---|---|---:|---:|---:|---:|
| Original 41.28 square / 105 | 84.36–125.64 | 17.04 | 3.795 | 3.060 | 127.32 |
| 60 × 40 / 105 | 75–135 | 24.00 | **0.186** | **−0.549: overlaps** | 136.47 |
| 60 × 40 / 107 | 77–137 | 24.00 | 1.221 | **0.486** | 138.45 |
| 70 × 30 / 100 | 65–135 | 21.00 | 4.669 | 3.934 | 135.83 |
| Two 30 squares / 82 and 115 | 67–97 and 100–130 | 18.00 | 5.704 | 4.969 | 130.86 |

All five **bare footprints** fit without overlap at twelve sites and fit inside
the 146 mm deck radius and 150 mm housing radius, including the optional pocket
allowance for those radial-envelope checks. Only 60 × 40/r105 fails the inflated
neighbour-pocket test. The two squares have a **3 mm same-site radial gap**,
reduced to 2.4 mm with 0.3 mm inflation of each square.

These are geometry checks, not manufacturing approval. A 0.486 mm residual web
for 60 × 40/r107 is thin; clamps, insulation webs, electrical routes, supporting
lands and print tolerances still need design. Footprints may extend outside the
food outline (particularly 60 × 40/r107), which reduces useful overlap. A 30 mm
wide cap does **not** fully support the current 40 × 40 mm TEC allowance: the
70 × 30 and two-square candidates need a compatible smaller module or a separate
supported interface. Two caps per site do not establish whether one or two TECs
would be used, or whether the additional hardware suits the simplicity priority.

### Footprint coverage and temperatures under matched boundaries

2 mm grid, all caps fixed at 0°C. Coverage is the cold union intersecting the
discretised food footprint, not raw metal area. Each row reports
**minimum / mean / maximum layer-average °C**.

- **Nominal:** top environment 25°C, top h = 5 W/(m² K), underside 30°C.
- **Sheltered:** top environment **10°C**, top h = 5, underside **30°C**.
- **Low h:** top environment 25°C, top h = **1**, underside 30°C.

| Footprint | Overlap cm² / coverage | Nominal min / mean / max °C | Sheltered min / mean / max °C | Low-h min / mean / max °C |
|---|---:|---:|---:|---:|
| Original square r105 | 16.96 / 50.1% | 3.38 / 6.46 / **11.96** | 1.73 / 3.82 / **7.55** | 1.41 / 3.51 / **7.44** |
| 60 × 40 r105 | 23.68 / 70.0% | 2.60 / 3.96 / **7.73** | 1.19 / 2.12 / **4.68** | 0.82 / 1.69 / **4.16** |
| 60 × 40 r107 | 23.60 / 69.7% | 2.60 / 4.11 / **8.66** | 1.19 / 2.22 / **5.31** | 0.82 / 1.80 / **4.83** |
| 70 × 30 r100 | 21.00 / 62.1% | 2.93 / 4.59 / **8.21** | 1.42 / 2.55 / **5.01** | 1.03 / 2.12 / **4.50** |
| Two 30 squares r82/r115 | 18.00 / 53.2% | 3.30 / 5.51 / **9.50** | 1.67 / 3.17 / **5.88** | 1.30 / 2.77 / **5.47** |
| Ideal full footprint | 33.84 / 100% | 2.05 / 2.05 / **2.05** | 0.82 / 0.82 / **0.82** | 0.44 / 0.44 / **0.44** |

The longer narrow rectangle and two squares move the warmest location from the
inner tip to the **outer lateral shoulder**, around x = 132 mm, |y| = 29 mm on
the 2 mm grid. This exposes a different limitation: radial reach alone leaves
the widening outer shoulders poorly covered. The 60 × 40 footprints retain their
warmest location at the inner tip, x ≈ 62 mm.

Nominal food-path extraction is 0.428 W (original), 0.434 W (60 × 40/r105),
0.431 W (60 × 40/r107), 0.442 W (70 × 30) and 0.446 W (two squares). Improved
distribution can cool food substantially without a large increase in this
particular holding load. These still omit direct plate losses, TEC back-leakage,
and appliance heat rejection, so do not establish electrical headroom.

The sheltered result is deliberately **not** the earlier both-reservoirs-at-10°C
sensitivity: the underside stays warm and its uncovered deck pathway matters.
For the original square, changing the underside from 10 to 30°C increases the
maximum from 4.47 to **7.55°C**, even though the top air remains 10°C.

### Selection implications

- **60 × 40/r105:** best thermal footprint among these finite candidates, but
  nominal neighbour clearance is too small for the example pocket allowance.
- **60 × 40/r107:** improved neighbour spacing at the cost of a longer uncooled
  inner tip and a still-thin pocket web. Nominal maximum improves about 3.30°C
  over the original square, but remains well above 4°C.
- **70 × 30/r100:** relatively generous site spacing and reaches the inner tip;
  its narrow width leaves warm outer shoulders. Nominal maximum improves about
  3.74°C, but module-to-cap compatibility is unresolved.
- **Two 30 mm squares:** distributed contact improves the square baseline while
  adding possible component/contact complexity. It is less effective in these
  scenarios than either single rectangular footprint.

These results justify comparing a **real rectangular plate coupon** with the
original square before dismissing distributed cooling. They do not justify a
4°C food claim. **Grid refinement matters for the favourable 60 × 40/r105 low-h
case:** maximum layer-average temperature is 4.157°C at 2 mm, **3.985°C at 1 mm**,
and **3.943°C at 0.5 mm**; the refined mean is 1.638°C. Thus the idealised fine-grid
scenario falls just below 4°C. It would be wrong to categorically reject that
footprint based only on the 2 mm result, or to treat its 0.057°C simulated margin
as real design margin. It still has the tightest neighbour fit, assumes a uniform
0°C plate and perfect contact, and leaves top temperature unresolved. A mean
below 4°C is not a maximum below 4°C; neither is a layer-average maximum a validated
top-surface maximum. The ideal full-area reference is still a reference only.

The latest top concept—sealed 0.8 mm skins, 12 mm cells in a 9.2 mm lid, and an
8 mm wall with 5 mm cells—does not by itself establish a 10°C chamber. Web bridging,
radiative exchange, sealing, internal/external convection and the feeding opening
need a separate enclosure heat balance. No honeycomb conductivity or chamber CFD
result is inferred from this footprint comparison.

### Sensitivity: one change at a time, 2 mm grid

| Changed assumption | Mean °C | Maximum °C | Cold W |
|---|---:|---:|---:|
| Nominal | 6.46 | 11.96 | 0.428 |
| Top h = 1 W/(m² K) | 3.51 | 7.44 | 0.206 |
| Top h = 10 W/(m² K) | 9.10 | 15.55 | 0.636 |
| Added contact R'' = 0.005 m² K/W | 7.39 | 12.66 | 0.408 |
| Uniform 0.2 mm air gap, k = 0.026 W/(m K) | 7.85 | 13.01 | 0.398 |
| Uniform 1 mm air gap | 11.84 | 15.97 | 0.311 |
| Deck k = 0.03 W/(m K) | 5.72 | 10.40 | 0.388 |
| Deck k = 0.12 W/(m K) | 7.65 | 14.34 | 0.494 |
| Deck k = 0.20 W/(m K) | 8.82 | 16.57 | 0.559 |
| Food k = 0.3 W/(m K) | 8.36 | 15.33 | 0.380 |
| Food k = 0.6 W/(m K) | 5.89 | 10.84 | 0.443 |
| Lateral food transport ×10 | 5.17 | 6.00 | 0.466 |
| Remove food vertical resistance | 3.79 | 9.86 | 0.492 |
| Fill to 16 mm, approximately 54 mL | 6.95 | 11.25 | 0.418 |
| Cap held at 2°C | 7.97 | 13.06 | 0.395 |
| Top ambient 30°C, underside 35°C | 7.69 | 14.19 | 0.510 |
| Add side h = 5 W/(m² K) | 8.94 | 16.30 | 0.582 |
| Both environments already held at 10°C | 2.45 | 4.47 | 0.164 |

These are parameter scenarios, not statistical confidence limits or rigorous
upper/lower physical bounds. The gap calculation is conduction-only, with an
assumed still-air conductivity. The side-load stress case exposes every staircase
perimeter face to ambient: shared divider walls may instead have near-zero net
flux, and staircase perimeter overestimates smooth perimeter. No precision claim
is attached to that side case. The 10°C case presupposes an independently cooled
environment and does not calculate how to achieve it. Enhanced lateral transport
does not prove natural mixing exists in actual food; cooling from below can
produce stable stratification in a water-like fluid above about 4°C.

## Transient interpretation

2 mm grid, nominal assumptions, 60-second backward-Euler steps:

| Initial food / cold coverage | 15 min mean / max °C | 60 min mean / max °C | 120 min mean / max °C |
|---|---:|---:|---:|
| 4°C / local | 4.77 / 7.14 | 6.04 / 10.76 | 6.40 / 11.76 |
| 25°C / local | 16.20 / 24.12 | 8.45 / 16.04 | 6.74 / 12.67 |
| 4°C / full-area | 2.65 / 2.65 | 2.06 / 2.06 | 2.05 / 2.05 |
| 25°C / full-area | 9.13 / 9.13 | 2.25 / 2.25 | 2.05 / 2.05 |

Pre-chilling does not remove continuous holding heat gain: the uncovered tip
warms even while the cold patch stays at 0°C. Initial warm-food extraction is
2.38 W per local cap, falling toward 0.43 W. These transient times assume the
cap starts and stays cold, and omit aluminium, PETG, TEC and enclosure thermal
mass. They are illustrative food dynamics, not appliance pull-down guarantees.

## Numerical verification and convergence

| Grid mm | Cells | Area cm² | Mean °C | Maximum °C | Cold W |
|---|---:|---:|---:|---:|---:|
| 4 | 210 | 33.60 | 6.4143 | 11.7610 | 0.42589 |
| 2 | 846 | 33.84 | 6.4630 | 11.9556 | 0.42824 |
| 1 | 3354 | 33.54 | 6.3737 | 11.7169 | 0.42534 |
| 0.5 | 13420 | 33.55 | 6.3711 | 11.6561 | 0.42566 |

From 1 to 0.5 mm: mean changes **0.0026°C**, maximum **0.0609°C**, extraction
**0.075%**, area **0.030%**. From 2 to 0.5 mm: mean changes 0.092°C and maximum
0.300°C. Staircase geometry makes convergence non-monotonic; no Richardson order
or exact error bound is claimed. Material and boundary uncertainties are much
larger than this observed refinement difference.

The footprint extension also refines **all eighteen footprint/environment
combinations from 2 to 1 mm**. Across these comparisons, the largest absolute
changes are 0.0893°C in mean and 0.2551°C in maximum. The 1 mm maxima are:

| Footprint | Nominal maximum °C | Sheltered maximum °C | Low-h maximum °C |
|---|---:|---:|---:|
| Original square | 11.717 | 7.386 | 7.232 |
| 60 × 40/r105 | 7.495 | 4.517 | 3.985 |
| 60 × 40/r107 | 8.406 | 5.136 | 4.642 |
| 70 × 30/r100 | 8.034 | 4.884 | 4.370 |
| Two 30 squares | 9.313 | 5.753 | 5.330 |
| Full-area reference | 2.058 | 0.823 | 0.441 |

The threshold-adjacent 60 × 40/r105 low-h case receives a further 0.5 mm check;
from 1 to 0.5 mm its mean changes 0.00385°C and maximum 0.04182°C. The simulation's
4°C crossing is grid-sensitive, while its broader improvement over the original
square is robust to this refinement. See the footprint convergence CSV for
minimum, mean, maximum, coverage and heat balance at every resolution.

At two hours, 300 versus 60 second time steps differ by 0.0154°C mean / 0.0434°C
maximum for initially chilled local food, and 0.0725°C / 0.1486°C for initially
warm local food. Full-area warm-food mean difference is 0.00436°C. These quantify
time-step sensitivity, rather than proving transient accuracy at all early times.

Built-in checks passed:

- Rectangle-union areas with overlapping, duplicate, nested, clipped and disjoint
  rectangles; equivalent single/overlapping representations give identical cold
  fractions. No heat-extraction area is double-counted.
- Analytical twelve-site containment for every finite candidate, including the
  expected 0.3 mm pocket-overlap failure at 60 × 40/r105 and success at r107.
- Uniform 7°C equilibrium with all reservoirs at 7°C: maximum error 6.5e-11°C.
- Isolated nonuniform food, no cold/ambient sources: one implicit step conserves
  total energy within 4.8e-9 J.
- Full-area uniform solution compared with analytic
  `T = (U_c T_c + h T_a)/(U_c + h)`: error 3.1e-11°C.
- Arbitrary loaded transient step: net boundary heat equals storage rate within
  5.1e-11 W.
- Every steady scenario has residual energy imbalance below 1e-7 W and obeys
  the boundary-temperature maximum principle. These are numerical checks,
  not physical validation of assumed transport coefficients.

## TEC headroom: why twelve large modules are not twelve Qmax ratings

No module curve, current, voltage, hot-side sink resistance or fan performance
has been selected here. An ideal fixed cap is optimistic about available cooling
power and cap uniformity. In a simple single-stage TEC model:

```text
Qc = alpha Tc I - I² R / 2 - K (Th - Tc)
V  = alpha (Th - Tc) + I R
Qh = Qc + V I
```

Tc is absolute temperature in the Peltier term. The **K ΔT term is passive
hot-to-cold leakage**. Even with I = 0, a module conducts heat from the hot side
into the cold assembly. Twelve large modules can therefore add twelve parallel
leak paths; reducing current does not remove those paths. If each selected
module had conductance K, their aggregate back-conduction would be `12 K ΔT`.
K is intentionally not invented for an undecided module.

Available headroom must be evaluated from actual **I, V, ΔT and hot-side
temperature**, with the heat sink rejecting **Qc + electrical input**. More
module area can ease local spreading while adding leakage and heat rejection.
Summing catalogue Qmax values (specified at ΔT = 0) does not size this appliance.
When using manufacturer net-Qc curves, the internal K ΔT penalty is already
included: do not subtract it twice. External bridges still add to useful load.

Source retrieved 2026-10-24: Ferrotec, [Thermoelectric Reference Guide §11,
Mathematical Modeling of Modules](https://thermal.ferrotec.com/technology/thermoelectric-reference-guide/thermalref11/),
especially §§11.4, 11.6 and 11.7. This source supports the TEC equations and
Qmax caveat; it is **not** a source of measured PETG/food/deck properties here.

## Limits and practical next decision

This is not CFD or a three-dimensional conjugate heat-transfer model. The
layer-average representation **cannot validate the food-top temperature**, local
freezing at the floor, natural convection, or the warmest real food point. The
nominal top Biot scale `h L/k` is about 0.12, and the cold-interface scale is much
larger; a perfectly uniform vertical layer is not established. Ambient coupling,
food rheology/mixing, sliding contact, air gaps and low-infill print conductance
remain unknown. Missing wall/lid/seam and moisture paths can increase load;
a cold closed chamber can reduce the imposed top load.

For the simplest useful next build, use **one actual rounded PETG wedge, one stock
cap and the intended printed deck**. Hold or measure the cap temperature and
log food at the inner tip, above the cap, outer edge and near the top, with 40 mL
of the actual food. Start chilled and observe several hours at the intended
ambient, including the open-serving condition. Measure whether the floor really
rests on the cap after repeated indexing and condensation. That experiment
distinguishes contact, lateral spread and vertical stratification without first
building twelve cooling branches.

Use those measured temperatures and heat loads to choose a TEC operating point
and sink/fan assembly. More electrical cooling at the same cap temperature alone
does not remove a lateral transport bottleneck. Keep the sourced-cap architecture
as the current prototype, but do not claim an all-food temperature target from a
cold-cap sensor or this averaged model alone.
