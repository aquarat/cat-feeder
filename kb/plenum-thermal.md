# Forced cold-air plenum versus direct TEC contact

**Status: reduced-order simulation plus hand estimates, 2026-10-25; no physical
test of either concept.** This page evaluates exploring decision D35 (a closed-loop
cold-air plenum under the tray) against the current direct-contact prototype
(D19), following the 2026-10-25 independent review. It extends, and does not
replace, the [direct-contact study](direct-contact-thermal.md) and the historical
[cap study](thermal-model.md). Labels used below: **[sim]** = output of the
finite-volume solver or the scripted lumped/TEC models; **[est]** = engineering
estimate or assumed input; **[src]** = supplier or literature value.

**Finding.** Direct contact can't reach the 2–4 °C warmest-food target without
freezing food. Colder faces do lower the warmest point, but only after the food
over the face has frozen. The plenum cools the whole bowl underside, so it can
meet the target for **covered** wedges with realistic boundaries. It does this at
modest air temperatures (−2 to −5 °C) and with no food below −1 °C. The open
(serving) wedge stays the weak point: its steady warmest point is about 4.6–6.7 °C
**[sim]**. Starting from covered steady state, it takes **41–72 min [sim]** for the
top surface to pass 5 °C. The plenum's main costs are a **~12–17 W cold-chamber load
[est]** dominated by deck leakage, TEC COP of about **0.2–0.35 [sim]**,
**~41–90 W TEC input**, hot sinks of **≤0.4 K/W each**, frost management, and a
**~150 W 24 V brick**.

> **2026-10-26:** sizing on the CAD geometry, with modelled sinks and fans, is in
> [plenum sizing](plenum-sizing.md). It supersedes this page's assumed R_cold ≤1.0 /
> R_hot ≤0.4 K/W, the three-module sizing and the pull-down times.

## Scope and reproducibility

```sh
cd thermal && python3 plenum.py          # writes thermal/plenum-output/
```

Python 3.10+, standard library only, about 30 s. The [driver](../thermal/plenum.py)
imports the historical [solver](../thermal/model.py) without changing it.
`model.py`, `direct_contact.py` and their outputs are untouched. Outputs are in
[plenum-output](../thermal/plenum-output/):

| File | Contents |
|---|---|
| `direct_sweep.csv` | direct40 at Tc 0/−5/−10/−15 °C, both boundary sets, covered/open; ice indicators |
| `plenum_food.csv` | uniform plenum air 2/−2/−5/−10 °C × h 10/15/20/30/50, with an exact 1-D check |
| `plenum_design_food.csv` | coldest/mean/warmest wedge including the air-temperature sawtooth between fin banks |
| `open_exposure.csv` | wedge moved from covered steady state to open, 4 h history |
| `channel_convection.csv` | Re/Nu/h, flow and pressure estimate for 10/12/15 mm channels |
| `heat_balance.csv` | cold-chamber load terms across T_air, h, deck k, leakage, fan heat, TEC count |
| `tec_fit_checks.csv`, `tec_sizing.csv` | TEC parameter fits and residuals; operating point per module/count/sink resistance |
| `pulldown.csv`, `pulldown_history.csv` | lumped 480 g pull-down cases |
| `comparison.csv`, `results.json` | combined table; all parameters, fits, design points, solver/driver SHA-256 |

## Assumptions

**Food/tray geometry** (unchanged from the direct study, [sim] inputs): 12 rounded
26° wedges, 33.84 cm² each on the 2 mm grid. Each holds 40 mL / 40 g (480 g total),
about 11.8 mm deep, on a 1.2 mm PETG floor. Food k is 0.5 W/(m K), ρc_p is
1000 × 3800, and PETG k is 0.20.

**Boundary sets [est]:**

| Set | Room | Bay under deck | Covered top | Open top | Direct contact |
|---|---:|---:|---:|---:|---|
| nominal (existing) | 25 °C | 30 °C | h = 1 | h = 5 | ideal |
| realistic (reviewer) | 22 °C | 32 °C | lid U = 2.5 | h = 5 | 0.1 mm air gap (R″ = 0.00385) |

Rerunning the realistic set with this tooling gives warmest layer-average values of
10.0 °C covered and 12.3 °C open at Tc = 0 °C **[sim]**. That is the low end of the
reviewer's quoted 11–15 °C. The reviewer's exact open-top coefficient was not
recorded, so this is a reproduction of the stated inputs, not of their run.

**Plenum food model.** I reused the solver with `full_plate=True`, the cold boundary
set to plenum air, and `contact_r = 1/h`. Deck conduction under the food is removed
because the tray now sits in cold air. The uniform result matches an independent
analytic node to < 10⁻⁶ K (asserted). The script also reports an exact 1-D series
profile (air–h–floor–food–top). Its top temperatures agree with the post-processed
estimate within about 0.1–0.4 K.

**"Warmest" = estimated top surface [sim+est].** For both concepts this is the
solver node plus `q_top·(d/2)/k_food`. It sits 0.3–1.3 K above the layer-average
maximum, which the direct page reported as its "max". "Food bottom" =
cold boundary + flux × series resistance below the food. It is the ice indicator,
and **−1 °C** is taken as the approximate initial freezing point of wet food [est].

**Air sawtooth [est].** Air circulates one way around the annulus through N fin
banks. Between banks it warms by `Q_air/(N ṁ c_p)`, about 1.1–2.3 K at the
flows below. The warmest wedge sees mean air + half of that rise.

**Deck conductivity [src/est].** The owner's range is k_eff = 0.05–0.08 W/(m K),
with a 0.12 stress case. Sources:
- PET-G hot-box panels (100 mm thick, 25 % infill) measured **0.074 (gyroid) and
  0.090 (honeycomb) W/(m K)** ([Polymers 2023, PMC10222068](https://pmc.ncbi.nlm.nih.gov/articles/PMC10222068)).
- A thin-sample SPIE/RPI study measured **0.15–0.31 W/(m K)** for PLA/ABS/PETG
  at 20–98 % infill. Honeycomb was 30–60 % below grid, and the lowest values were
  near 20 % ([RPI copy](https://www.lrc.rpi.edu/programs/solidstate/pdf/1267008.pdf)).
- A rough parallel-path estimate [est] for ~10 % vertical webs plus cell radiation
  gives ≈ 0.06. The earlier KB default was 0.06, unverified.

So 0.05–0.08 is optimistic-to-central for an 18 mm deck, and 0.12 is
plausible if skins/perimeters dominate. **Measure it.**

## 1. Direct contact at colder faces [sim]

direct40, 2 mm grid. Each cell is layer mean / estimated warmest top / coldest
food bottom over the face, in °C.

| Set, position | Tc 0 | Tc −5 | Tc −10 | Tc −15 |
|---|---|---|---|---|
| nominal covered | 3.8 / 8.0 / 0.5 | −0.5 / 4.4 / −4.4 | −4.8 / 0.8 / −9.3 | −9.2 / −2.9 / −14.2 |
| nominal open | 6.9 / 13.1 / 1.2 | 3.2 / 10.5 / −3.6 | −0.5 / 8.0 / −8.3 | −4.2 / 5.5 / −13.1 |
| realistic covered | 5.5 / 10.4 / 1.3 | 1.6 / 7.3 / −3.5 | −2.4 / 4.3 / −8.2 | −6.4 / 1.2 / −13.0 |
| realistic open | 7.2 / 12.8 / 1.8 | 3.6 / 10.4 / −2.8 | 0.05 / 8.0 / −7.4 | −3.5 / 5.5 / −12.0 |

Below Tc = −5 °C, **the whole 16 cm² face footprint has food below −1 °C in every
case [sim]**. At Tc = −10 °C, the share of layer-average cells below −1 °C is 47–89 %.
Realistic-covered first reaches a ≤ 4.3 °C warmest point at Tc ≈ −10 °C. By then
68 % of the food layer is frozen and the bottom sits near −8 °C. Open never gets
below 5.5 °C, even at −15 °C. The model has no latent heat, so a real freezing
front would slow down and change these numbers. Ice also means a frozen tray
bond, which would lock the tray to the ceramic and stall indexing. The warm tip
stays limited by lateral conduction (47 % coverage). Making the face colder trades
an unsafe warm spot for an icy cold one.

## 2. Plenum food temperatures [sim]

**Uniform plenum air (no sawtooth), realistic set.** Each cell is mean / warmest
top, °C (full grid in `plenum_food.csv`).

| T_air | h = 10 | h = 15 | h = 20 | h = 30 | h = 50 |
|---|---|---|---|---|---|
| +2 covered | 6.6 / 7.0 | 5.5 / 6.0 | 4.9 / 5.4 | 4.3 / 4.8 | 3.7 / 4.3 |
| −2 covered | 3.5 / 4.0 | 2.2 / 2.8 | 1.5 / 2.1 | 0.7 / 1.4 | 0.1 / 0.7 |
| −5 covered | 1.1 / 1.8 | −0.3 / 0.4 | −1.1 / −0.4 | −1.9 / −1.2 | −2.7 / −1.9 |
| −10 covered | −2.7 / −2.0 | −4.4 / −3.6 | −5.4 / −4.6 | −6.4 / −5.5 | −7.2 / −6.4 |
| +2 open | 9.4 / 10.2 | 7.9 / 8.8 | 7.1 / 8.0 | 6.1 / 7.0 | 5.2 / 6.2 |
| −2 open | 6.9 / 7.8 | 5.1 / 6.1 | 4.1 / 5.1 | 2.9 / 4.0 | 1.8 / 3.0 |
| −5 open | 5.0 / 6.0 | 3.0 / 4.1 | 1.8 / 3.0 | 0.5 / 1.8 | −0.7 / 0.6 |
| −10 open | 1.9 / 3.1 | −0.5 / 0.8 | −1.9 / −0.5 | −3.5 / −2.0 | −4.9 / −3.3 |

The field is laterally uniform: the inner-tip problem disappears. The vertical
gradient through the food is only about 0.6–1.5 K. Food-bottom minima stay above
−1 °C for −5 °C/h ≤ 10 covered, −2 °C/h ≤ 30, and all open cases at T_air ≥ −5 °C
with h ≤ 20. The nominal set's h = 1 lid over-cools covered wedges, so control would
run warmer air there.

**With sawtooth, candidate design points (realistic).** Warmest-wedge mean / top / bottom, °C.

| Design | Loop v, sawtooth | Covered warmest wedge | Covered coldest-wedge bottom | Open warmest wedge (steady) | Open: top > 5 °C after |
|---|---|---|---|---|---|
| T_air −5, h 10 | 1.5 m/s, 2.3 K | 2.0 / **2.6** / 1.4 | −0.4 | 5.7 / **6.7** / 4.8 | **72 min** |
| T_air −2, h 15 | 2.4 m/s, 1.4 K | 2.8 / **3.3** / 2.2 | 1.0 | 5.6 / **6.6** / 4.7 | **41 min** |
| T_air −5, h 15 | 2.4 m/s, 1.5 K | 0.3 / **1.0** / −0.3 | **−1.6 (ice risk)** | 3.6 / **4.6** / 2.5 | — |

The open wedge reaches steady state with a time constant of about 1 h
(`open_exposure.csv`). An index/serving schedule that leaves food in the aperture
for < 1 h meets < 5 °C. Leaving it open all day does not, unless air is colder
or h is higher, and colder or faster air puts the coldest covered wedge at ice risk.
Put the coldest air (just after a fin bank) under the serving position.

## 3. Channel convection estimate [est]

Channel width is 80 mm. Air at −2 °C has ν ≈ 1.3 × 10⁻⁵ m²/s. D_h = 2HW/(H+W) is
17.8, 20.9 and 25.3 mm for H = 10, 12 and 15 mm. Correlations used:
- fully developed laminar, one heated wall: Nu = 5.385 (Shah & London);
- laminar developing over the ~0.22 m between fin banks: Stephan correlation
  scaled to one heated wall;
- Re > 4000: Gnielinski, linearly blended across 2300–4000.

| H = 12 mm, v | Re | h lower bound | h developing est. | Loop flow | Δp est. |
|---|---:|---:|---:|---:|---:|
| 0.5 m/s | 800 | 6.2 | 7.5 | 0.5 L/s | 1.6 Pa |
| 1.0 m/s | 1600 | 6.2 | 8.6 | 1.0 L/s | 5 Pa |
| 1.5 m/s | 2400 | 6.7 | 9.8 | 1.4 L/s | 11 Pa |
| 2.0 m/s | 3200 | 11.1 | 12.7 | 1.9 L/s | 19 Pa |
| 3.0 m/s | 4800 | 18.4 | 18.4 | 2.9 L/s | 43 Pa |

Δp assumes 0.7 m of duct plus ~6 dynamic heads for fin banks, turns and rim bumps.
**Plausible h is 8–12 W/(m² K) at 1–2 m/s.** That velocity range is realistic for a
40–60 mm fan working against 5–20 Pa. Reaching h ≈ 15–20 needs about 2.4–3.3 m/s
and 25–60 Pa, which is at or beyond small axial fans (a blower or turbulators would
help). h = 30–50 is implausible without jet impingement. Channel height changes h
only weakly at a fixed volume flow. The **design case is T_air −5 °C, h 10**.

## 4. Cold-chamber heat balance [est, food term sim]

Realistic set, T_air −5 °C, h 10, 3 TECs, deck k 0.065, fan 0.5 W, nominal leakage.
Every term is heat entering the cold air:

| Term | W | Basis |
|---|---:|---|
| Food (11 covered + 1 open) | 2.23 | [sim] FV wedges |
| Lid over hub/rim/non-food | 1.78 | U 2.5 × (Ø292 lid − food area) × ΔT |
| **Deck from bay (Ø292, 18 mm)** | **4.82** | 1/h + t/k + 1/10, bay 32 °C |
| Side wall, 35 mm cold band | 2.12 | 12 mm wall at same k, outside h 8 |
| TEC retainer bridges | 1.11 | 0.01 W/K per TEC [est] |
| Fan motor | 0.5 | owner range 0.3–1 |
| Hub/shaft bridge from motor | 0.5 | [est] |
| Air exchange, sensible + latent | 0.49 + 0.32 | 0.01 L/s seams + 0.005 L/s aperture; 22 °C/50 % RH; frost at T_air −3 K |
| **Total** | **13.9** | range **12.3** (tight, k 0.05, fan 0.3) to **17.3** (leaky 0.05 L/s, k 0.08, fan 1) |

Further cases: k = 0.12 gives 16.2 W, and the nominal set gives 12.0 W. **Frost** is
about **10 g/day** at nominal leakage, 4.6 g/day tight and 36 g/day leaky (each
0.01 L/s adds about 6.5 g/day). Defrost needs a drain and a periodic TEC-off or
reversed-polarity cycle. Its latent energy is small (10 g × 334 kJ/kg ≈ 3.3 kJ/day)
but its schedule matters. The deck is the largest single load. Lowering bay
temperature or adding deck thickness is worth more than extra TEC count.

## 5. TEC fits and sizing [src → sim]

Model: `Qc = αIT_c − ½I²R − KΔT`, `V = αΔT + IR`. Temperatures are in K;
published net-Qc curves already include KΔT, so it is applied once here.

| Module | Fit | α V/K | R Ω | K W/K | Check |
|---|---|---:|---:|---:|---|
| CP60440 | max-parameter, from Imax 6 A, Vmax 15.4 V, **ΔTmax 68 K** ([Same Sky page](https://www.sameskydevices.com/product/thermal-management/peltier-devices/single-stage-peltier-modules/cp60440)) | 0.0513 | 1.985 | 0.525 | Qmax 56.7 vs 53 W; 27/7 °C at 1.2 A: 5.3 vs 6 W; 27/−3 °C: −0.6 vs 1.5–2 W → **conservative at large ΔT** |
| CP60440 | least squares on graph readings + Qmax + ΔTmax | 0.0505 | 2.126 | 0.464 | 27/−3 °C: 0.9 W; Qmax 52.7 W |
| TARK CP14-127-10 | least squares, 6 calculator points | 0.0475 | 3.178 | 0.274 | residuals ≤ 0.05 W, ≤ 0.07 V |

Sizing finds the smallest current meeting Qc/N with `Tc = fin-air − Qc·R_cold` and
`Th = hot air + Qh·R_hot`. Hot-sink inlet air is room + 5 °C = 27 °C [est].
Design load 13.9 W:

| Case | I | V | TEC in | Tc / Th | COP | Heat rejected |
|---|---:|---:|---:|---:|---:|---:|
| 3 × CP60440 (cons.), R_cold 1.0, R_hot 0.4 K/W | 2.86 A | 8.2 V | **70 W** | −10.8 / 38.2 °C | 0.20 | 84 W |
| same, CP60440 lsq fit | 2.52 A | 7.8 V | 59 W | −10.8 / 36.7 | 0.24 | 73 W |
| 3 × TARK, same sinks | 1.76 A | 7.7 V | **41 W** | −10.8 / 34.3 | 0.34 | 55 W |
| 4 × CP60440, same sinks | 2.44 A | 7.1 V | 70 W | −9.4 / 35.4 | 0.20 | 84 W |
| 2 × CP60440, R_cold 0.5, R_hot 0.25 | 2.82 A | 7.9 V | 44 W | −10.1 / 34.3 | 0.31 | 58 W |
| 3 × CP60440, R_cold 2.0, R_hot 0.6 | — | — | **infeasible** | | | |
| 3 × CP60440, deck k 0.12 (16.2 W) | 3.26 A | 9.2 V | 90 W | | 0.18 | 106 W |
| 4 × CP60440, leaky, k 0.08 (17.0 W) | 2.71 A | 7.8 V | 85 W | | 0.20 | 102 W |

**Needed sinks [sim]:** cold sink ≤ **1.0 K/W** per module (≤ 1.5 with four modules).
Hot sink ≤ **0.4 K/W** per module to 27 °C air (0.6 works only with R_cold 0.5 and
four modules). Sink quality matters more than module count: 3 vs 4 modules barely
changes power. A small 40 × 40 mm pin fin in the plenum is roughly 1–3 K/W [est]
at 1.5 m/s. A 0.4 K/W hot sink is a fan-ducted ~80 mm class sink, not the
3.5 K/W-catalogue 40 × 40 × 20 Fischer part [src: airflow.md]. A lower-K module
(the TARK class, 3.9 A Imax) is markedly better than the 6 A CP60440 at this
~4.6 W/module, ΔT ≈ 45–49 K duty. Its 4.7 mm thickness no longer matters, because
the tray does not touch it.

**Brick [est]:** `(TEC/0.9 + 8 W aux) × 1.25` gives 108 W for the conservative
CP60440 case, 135 W for the k = 0.12 stress case and 67 W with TARK modules.
**Specify a 24 V brick of ≥ 150 W** (about 6.3 A). Pull-down above about 3 A/module
gains almost nothing (below).

Wiring note: three CP60440s in series need about 24.6 V, which exceeds the
DPS5005's ~21.8 V ceiling from 24 V. Three in parallel draw ~8.6 A, over its 5 A.
**Four modules as 2S2P** (~14.3 V, 4.9 A) fit the existing DPS5005 marginally.
Otherwise use one regulator per module. This is for the electronics owner to decide.

## 6. Pull-down [sim, lumped]

The model has two nodes. The food node is 480 g food + ~250 g tray, 2.14 kJ/K.
The air node is air, sinks and deck skin, 500 J/K [est]. It uses the realistic set,
an air setpoint of −5 °C, h 10 and 3 × CP60440 (conservative fit) at 3 or 4 A
while above setpoint.

| Start | Food mean ≤ 5 °C | ≤ 4 °C | Final mean |
|---|---:|---:|---:|
| Unit and food at 20 °C | 2.2–2.3 h | 2.7 h | 1.4 °C |
| 20 °C food into running unit | 2.2 h | 2.6 h | 1.4 °C |
| 5 °C (fridge) food into running unit | 0 | 25 min | 1.4 °C |
| 5 °C food, unit starting at 20 °C | 20–25 min | 45–50 min | 1.4 °C |

The food time constant is about **79 min**. It is set by the food-to-air conductance
(h 10), not by TEC current: 4 A beats 3 A by only 0–5 min. Load food from the fridge.
Warm-food pull-down to < 5 °C exceeds two hours. The lumped node ignores internal
food gradients (~18 min conduction time), so the warmest point lags this mean.

## Comparison and recommendation

| Concept (realistic set) | Covered warmest / mean | Open warmest (steady) | Ice | Load / TEC input |
|---|---|---|---|---|
| Direct40, Tc 0 °C | 10.4 / 5.5 °C | 12.8 °C | none | 12 sites, food path only 0.3–0.4 W/site [sim] |
| Direct40, Tc −10 °C | 4.3 / −2.4 °C | 8.0 °C | **whole face footprint, 68 % of layer** | colder faces at 12 sites, not sized |
| Plenum −5 °C, h 10 | **2.6 / 2.0 °C** (warmest wedge) | 6.7 °C (> 5 °C after 72 min) | none (coldest bottom −0.4 °C) | 13.9 W (12.3–17.3); 41–70 W, 3 modules |
| Plenum −2 °C, h 15 | 3.3 / 2.8 °C | 6.6 °C (41 min) | none | 13.3 W; 49 W (CP60440 cons.) |

**Recommendation [est]:** adopt the plenum as the primary concept for covered-food
holding. Design for h ≈ 10, air at −3 to −5 °C, three or four modules, cold sinks
≤ 1 K/W and hot sinks ≤ 0.4 K/W, on a ≥ 150 W 24 V brick. Prefer a lower-K
(≈ 4 A Imax) module. Treat the serving wedge as time-limited (< ~1 h open) and
put the coldest air under it. Reduce deck leakage before adding TECs.

**Main uncertainties:** deck k_eff (0.05–0.12); achieved h and velocity, plus
flow bypass around the tray rim, quadrant gaps and bumps; air exchange through the
open aperture (which drives frost and sensible load); installed hot-sink resistance
and bay temperature; the CP60440 large-ΔT fit; and the open-top h. The model omits
air contact with the food top inside the chamber (which would help covered food),
radiation, food latent heat and indexing transients.

**Single most informative physical test:** build a **plenum coupon**. Use one
real 18 mm printed deck section with the tray-height side wall, a 12 mm channel,
one wedge-sized PETG floor holding 40 g of wet food, one small fan and one TEC with
the candidate cold and hot sinks. Under a lid, log air at the fin outlet and at
the wedge, the food bottom/middle/top, deck top/bottom surface temperatures, and
TEC V/I, against a 22 °C room and a heated 32 °C "bay" plate. In one run this
measures h (from food flux versus air ΔT), deck k_eff (from the deck surface ΔT
and heat-flux balance) and real TEC COP. Those three numbers dominate every result
above. Then open the lid aperture for an hour to measure open-wedge warming and
frost mass.

Related: [direct-contact study](direct-contact-thermal.md) · [thermal model](thermal-model.md) ·
[TEC control](tec-control.md) · [airflow](airflow.md) · [sourcing](sourcing.md) · [decisions](decisions.md) · [KB index](README.md).
