# Direct ceramic TEC contact with the PETG tray

**Status: reduced-order simulation, 2026-10-24; no physical feeder test.**
Latest owner direction is to remove the stock 41.28 × 41.28 × 3 mm aluminium
cold caps and explore the ceramic TEC cold face touching the removable PETG
tray directly. This page evaluates that thermal change. The historical
[cap study](thermal-model.md) and its outputs remain a separate design snapshot.

**Finding:** direct 40 mm contact is thermally close to the prior 41.28 mm cap
under matched ideal conditions. Its slightly smaller footprint raises the
simulated mean by approximately **0.3–0.4°C**; removing aluminium's own vertical
resistance changes it by only **0.002–0.003°C**. Contact gaps and shrinking to
30 mm matter much more. This supports a direct-contact prototype comparison,
not a claim that the food target or ceramic durability is established.

## Scope and reproducibility

```sh
python3 thermal/direct_contact.py
```

Python 3.10+, standard library only. The [new driver](../thermal/direct_contact.py)
imports the historical finite-volume solver without changing its defaults;
generated data live in [direct-output](../thermal/direct-output/), separate from
the old results. [Usage/output index](../thermal/README.md).
All numerical results here are **simulated food-layer-average temperatures**,
including the reported warmest cell, not the warmest actual food point.

### Geometry and assumptions

- Current food geometry: twelve positions, tray Ø280 mm in a Ø316 mm enclosure;
  one rounded 26° wedge, outer radius 137 mm, flat inner end x = 62 mm, 5 mm plan
  corner radius, **1.2 mm PETG floor and 40 mL food**. The 16 mm cavity depth is
  capacity geometry, not the modelled uniform food depth (approximately 12 mm).
- One stationary cold square per wedge, centred at radius **105 mm**. Compare
  historical **41.28 mm square × 3 mm aluminium**, direct **40 mm square with
  zero added aluminium**, and direct **30 mm square with zero added aluminium**.
  The 30 mm case represents the footprint class of the sourced CP203475H; it is
  not twelve TEC operating points or two smaller modules per compartment.
- The 40 mm case is the CAD nominal class, not a tolerance claim for a sourced
  TARK part. [Sourcing evidence](sourcing.md) records the approximately 39.88/40 mm
  TARK and 30 ±0.3 mm Same Sky candidates and their actual thicknesses.
- Ideal fixed outer cold ceramic face **0°C or 2°C** for direct cases. The ceramic
  is already part of the TEC: no extra aluminium or separate ceramic resistance
  is inserted between that imposed outer-face temperature and the PETG contact.
  The old cap case retains the old model's 3 mm / 200 W/(m K) series resistance.
- Food k = 0.5 W/(m K), density 1000 kg/m³, cp = 3800 J/(kg K); PETG k = 0.20.
  Printed deck is 18 mm thick with assumed effective k = 0.06; underside is 30°C.
  All are unchanged estimates, not measured feeder properties.
- **Open:** effective top h = 5 W/(m² K) to 25°C. **Covered/low-h:** h = 1 to the
  same 25°C reservoir. This is an illustrative reduction in top heat gain through
  a cover, **not a computed lid U, chamber temperature or proof of insulation**.
  A separate sheltered sensitivity fixes top air at 10°C, h = 5 and underside
  still at 30°C; it presupposes cooling that air.
- Ideal contact R'' = 0; an added contact R'' = 0.005 m² K/W; and uniform still-air
  gaps of **0.05, 0.2 and 1 mm**, using R'' = gap / 0.026 W/(m K). Gap scenarios
  replace ideal contact with this extra conduction resistance across the whole
  patch. They are not models of mixed contact asperities, liquid condensate,
  evaporation or gap radiation. No paste is assumed on the sliding tray.

The model uses lateral food/PETG conduction, a half-food-depth vertical resistance,
and imposed top/deck boundary loads as documented in the
[original equations](thermal-model.md#model-and-boundary-conditions). Food and
floor share a thickness-averaged node. Side faces are adiabatic, food does not
mix, and there is no separate aluminium spreading field. The rounded 3 mm
floor-wall fillet, variable local floor thickness and mouth chamfer are omitted.

## Matched steady comparisons

**2 mm grid**, 40 mL, ideal contact. Every temperature is a food-layer average.
The imposed outer ceramic/cold boundary is `Tc`. Loads are heat entering that
boundary **from the modelled food path**, not electrical input or total TEC load.

| Cold footprint | Tc °C | Open mean / max °C | Covered mean / max °C | Open / covered cold W |
|---|---:|---:|---:|---:|
| Prior 41.28 mm cap, 3 mm Al | 0 | 6.46 / 11.96 | 3.51 / 7.44 | 0.428 / 0.206 |
| Direct 40 mm, no added Al | 0 | 6.87 / 12.33 | 3.82 / 7.76 | 0.426 / 0.211 |
| Direct 30 mm, no added Al | 0 | 10.95 / 15.74 | 7.16 / 10.96 | 0.377 / 0.232 |
| Prior 41.28 mm cap, 3 mm Al | 2 | 7.97 / 13.06 | 5.26 / 8.92 | 0.395 / 0.192 |
| Direct 40 mm, no added Al | 2 | 8.35 / 13.41 | 5.55 / 9.21 | 0.393 / 0.196 |
| Direct 30 mm, no added Al | 2 | 12.13 / 16.57 | 8.66 / 12.20 | 0.348 / 0.215 |

The 2 mm wedge area is 33.84 cm². Useful cold overlap is **16.96 cm² / 50.1%**
for the historical cap, **16.00 cm² / 47.3%** for direct40, and
**9.00 cm² / 26.6%** for direct30. The original aluminium cap extends only
0.64 mm beyond the nominal ceramic on each side; it was not a broad spreader.
All faces are assumed uniformly cold; TEC ceramic nonuniformity is unresolved.

At Tc = 0°C, direct40 versus the prior cap increases mean/max by **0.412/0.374°C
open** and **0.311/0.320°C covered**. Direct30 versus direct40 increases mean/max
by **4.075/3.414°C open** and **3.346/3.208°C covered**. A smaller module might
have other power/mounting benefits, but these calculations show a substantial
food-side coverage penalty at the same centre and outer-face temperature.

### Separating aluminium resistance from footprint

Two diagnostic controls are in
[decomposition_controls.csv](../thermal/direct-output/decomposition_controls.csv):

- Retain 41.28 mm footprint but set aluminium thickness to zero: open mean/max
  moves from 6.4630/11.9556°C to **6.4601/11.9533°C**; covered to
  **3.5043/7.4339°C** from 3.5059/7.4354°C.
- Retain 3 mm aluminium resistance but reduce footprint to 40 mm: open mean/max
  becomes **6.8777/12.3318°C**, versus **6.8747/12.3295°C** when that aluminium
  resistance is removed too.

At this grid, the series area resistances are **PETG 0.0060**, representative
half-food layer **0.01182**, aluminium **0.000015 m² K/W**. Aluminium accounts
for only about **0.084%** of that ideal stack resistance. Thus the small net
temperature change is mostly reduced contact footprint, not loss of a useful
vertical conductor. Real contact and spreading changes remain empirical questions.

## Contact/gap sensitivity

Direct40, Tc = 0°C, otherwise matched 2 mm scenarios:

| Added interface assumption | R'' m² K/W | Open mean / max °C | Covered mean / max °C |
|---|---:|---:|---:|
| Ideal contact | 0 | 6.87 / 12.33 | 3.82 / 7.76 |
| Uniform 0.05 mm air gap | 0.001923 | 7.25 / 12.62 | 4.04 / 7.96 |
| Added contact resistance | 0.005000 | 7.83 / 13.05 | 4.39 / 8.26 |
| Uniform 0.2 mm air gap | 0.007692 | 8.30 / 13.40 | 4.69 / 8.52 |
| Uniform 1 mm air gap | 0.038462 | 12.35 / 16.37 | 7.58 / 11.00 |

A 0.2 mm uniform gap raises mean/max by **1.43/1.07°C open** and
**0.87/0.77°C covered**, larger than changing from the old cap to direct40.
The 1 mm case is a poor-contact stress case, not an acceptable gap specification.
All three footprints also have the full gap/contact sweep at Tc = 2°C in
[steady_cases.csv](../thermal/direct-output/steady_cases.csv). Matching a
simulated gap does not establish a real print tolerance or required preload.

Separate [boundary/material scenarios](../thermal/direct-output/boundary_material_sensitivity.csv)
give direct40 mean/max of **4.10/7.80°C** with imposed 10°C top air and 30°C base,
**8.17/14.64°C** at 30°C ambient/35°C base, and **9.56/15.91°C** with open top
h = 10. These are not additional covered-case predictions. The uncertainty in
boundary conditions and contact is much larger than aluminium's own resistance.

## Food-path loads for electronics screening

For **direct40 / ideal contact**, the model gives:

| Imposed ceramic face | One open / covered holding W | Eleven covered + one open W | Twelve open W | Initially 25°C: one / twelve extraction W |
|---|---:|---:|---:|---:|
| 0°C | 0.426 / 0.211 | 2.750 | 5.109 | 2.245 / 26.936 |
| 2°C | 0.393 / 0.196 | 2.552 | 4.718 | 2.065 / 24.781 |

The eleven-plus-one sum assumes all twelve 40 mL portions remain present and
stationary under the chosen separate boundaries. It is **not an indexing-cycle
simulation**. Prior-cap eleven-plus-one holding is 2.698 W at 0°C: the change
to direct40 is only **+0.052 W** for this conditional aggregate. Initially 4°C
food gives direct40 extraction of **0.359 W/site at Tc = 0°C** or **0.180 W/site
at Tc = 2°C**. Those are initial fluxes, not equilibrium holding powers.

One 40 mL portion has **152 J/K** heat capacity. Lowering that portion uniformly
from 25 to 4°C would remove **3.192 kJ**, or **38.304 kJ for twelve**, before
ongoing heat gains. Dividing by one hour gives a storage-only scale of
**0.887 W/portion or 10.64 W/twelve**. This is an energy arithmetic reference,
not a predicted cooldown time: these local-face simulations do not reach a
uniform 4°C condition, and cold extraction changes throughout the transient.

**These watts are only one contribution to required net cold load.** Missing
terms include direct deck/support-to-ceramic bridges, exposed ceramic outside
the food footprint, lid/walls/seams and chamber cooling, air exchange through
the serving opening, moisture/condensation, motor/electronics heat reaching the
cold region, and transient thermal mass of PETG, TECs, sinks and enclosure.
There is no installed-flow or fan model. The assumed covered boundary must be
measured; whole-unit load cannot be inferred by simply adding twelve wedges.

For the electronics agent: compare **net manufacturer Qc at actual Th/Tc and
current** against food-path load **plus measured/estimated external parasitics**.
Heat rejection is `Qh = Qc + electrical input`; it is not the food-path watts.
Net-Qc curves already include TEC internal hot-to-cold conduction. If using a
separate physical TEC model instead, include that conduction once, not twice.
The [existing sourcing curve readings](sourcing.md#what-the-published-curves-actually-support)
are not operating-point guarantees for direct40. This study neither chooses a
current nor demonstrates that a 100 W supply can maintain twelve ceramic faces
at 0°C. Lower extraction with a smaller patch or a gap can simply mean warmer
food, not a more efficient refrigerator.

## Transient results

Direct40, imposed Tc = 0°C, perfect contact, 2 mm grid, 60-second backward-Euler
steps. The cold face starts cold and remains exactly cold. **Only food thermal
mass is included**; startup of the TEC or appliance is not simulated.

| Boundary / initial food | 15 min mean / max °C | 60 min mean / max °C | 120 min mean / max °C | 240 min mean / max °C |
|---|---:|---:|---:|---:|
| Open / 4°C | 4.91 / 7.17 | 6.37 / 10.98 | 6.79 / 12.09 | 6.87 / 12.32 |
| Covered / 4°C | 3.66 / 5.70 | 3.71 / 7.23 | 3.79 / 7.64 | 3.81 / 7.75 |
| Open / 25°C | 16.66 / 24.24 | 9.01 / 16.52 | 7.20 / 13.11 | 6.88 / 12.35 |
| Covered / 25°C | 16.35 / 24.18 | 7.32 / 14.80 | 4.54 / 9.53 | 3.85 / 7.86 |

For initially warm food, extraction at 60/120 minutes is **0.551/0.444 W open**
and **0.415/0.251 W covered**, down from 2.245 W at time zero. Integrated
extraction at two hours is **5.107 kJ open / 4.233 kJ covered**, including ongoing
heat gains, not just the reduction in food stored energy. The covered initially
4°C example illustrates why a low mean does not establish a low warmest region.

[Transient CSV](../thermal/direct-output/transient.csv) also includes direct40
at Tc = 2°C from both initial temperatures, the 0.2 mm gap from 25°C in both
environments, and covered historical-cap/direct30 warm-start comparisons.
No cooldown or holding safety conclusion is inferred from these trajectories.

## Numerical checks and refinement

Every ideal footprint/environment/Tc combination has 2 and 1 mm results.
Additional 0.5 mm runs check direct40 open and covered at Tc = 0°C and the
open historical-cap/direct30 comparisons. Direct40 Tc = 0°C:

| Boundary | Grid mm | Mean °C | Max layer-average °C | Extracted W |
|---|---:|---:|---:|---:|
| Open | 2 | 6.8747 | 12.3295 | 0.425750 |
| Open | 1 | 6.7716 | 12.0721 | 0.423649 |
| Open | 0.5 | 6.7708 | 12.0174 | 0.423920 |
| Covered | 2 | 3.8167 | 7.7553 | 0.211290 |
| Covered | 1 | 3.7291 | 7.5337 | 0.209314 |
| Covered | 0.5 | 3.7277 | 7.4899 | 0.209520 |

At 0.5 mm, area = **33.55 cm²**, food depth = **11.9225 mm**. Direct40 changes
from 1 to 0.5 mm by **0.00088°C mean / 0.05464°C max open** and
**0.00144°C mean / 0.04375°C max covered**. Fine-grid open mean/max values are
**6.3711/11.6561°C** for the prior cap and **10.8776/15.5214°C** for direct30;
the footprint ranking and modest prior-cap/direct40 difference persist. Grid
masking makes convergence non-monotonic; these differences are not exact error
bounds. Gap sensitivities and transient fields use the 2 mm engineering grid.

For direct40 / Tc = 0°C / both environments and both starts, **30/60/300 second**
steps are compared at 15, 60 and 120 minutes. Across those samples, 60 versus
30 seconds differs by at most **0.0632°C mean / 0.0477°C max**; 300 versus
30 seconds by at most **0.525°C mean / 0.402°C max**. Hence the published
trajectories use 60 seconds. This is time-discretisation sensitivity, not proof
that the reduced-order transient is physically accurate.

Checks passed in [results.json](../thermal/direct-output/results.json):

- Maximum steady energy imbalance across all new solves: **6.53 × 10⁻¹³ W**.
- Maximum transient step boundary/storage mismatch: **4.12 × 10⁻¹⁰ W**.
- Maximum integrated transient energy mismatch: **1.64 × 10⁻⁶ J**, using
  backward-Euler endpoint flux quadrature consistently with the solver.
- Every temperature lies within its imposed boundary/initial-temperature bounds.
- Pointwise monotonicity: worse contact and a warmer ceramic do not improve the
  field; direct30 does not outperform direct40 at matched conditions.
- Historical solver checks rerun: uniform equilibrium, analytic full-area
  resistor network, isolated-system energy, loaded transient conservation,
  rectangle-union overlap accounting and historical footprint containment.

The driver records its own and the solver's SHA-256 hashes plus every scenario's
parameters. Numerical conservation validates the discretised equations, not the
material estimates, contact assumptions or cooling architecture.

## Interpretation boundaries and physical prototype

These scenarios do not predict **achievable closed-loop TEC cold-face temperature**,
electrical input, heat-sink temperature, contact pressure, scratching, friction,
ceramic fracture, print warpage or service life. Removing a cap can change those
interfaces even if its through-thickness thermal resistance was negligible.
Matched contact resistance isolates the thermal geometry comparison; it does
not assert ceramic/PETG and aluminium/PETG have equal real contact quality.
The old model also omitted TEC-to-cap TIM resistance, so removing that interface
cannot be assigned an extra quantified benefit from these results.

There is no CFD, resolved vertical food temperature, chamber energy balance,
food-storage safety claim or physical durability qualification. Scenario ranges
are conditional comparisons, not statistical confidence limits or guaranteed
physical bounds. A cold-face sensor alone does not establish all-food temperature.

A useful next prototype is one actual 40 mm ceramic TEC beneath one 40 mL PETG
wedge and the intended deck/cover. Record cold face, sink base, ambient, food
over the face, inner tip, outer shoulder and near the food top. Compare covered
and serving-open periods, initially chilled and warm food, and repeat after
indexing/cleaning. Log current/voltage alongside temperatures. This separates
actual contact and lateral-spreading limitations from lack of TEC headroom.
Observe contact/flatness, drag, condensate and ceramic condition separately:
none is established by the thermal solver. The owner's willingness to try a
physical prototype is consistent with this evidence level.
