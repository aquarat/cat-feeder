# Plenum sizing on the CAD geometry (D35)

**Status: reduced-order estimates and simulation, 2026-10-26; nothing measured.**
This page re-runs the [plenum thermal study](plenum-thermal.md) on the
[CAD study](plenum-cad.md) geometry: a 15 × 77.5 mm channel, four sites and
70 × 70 × 45 mm hot-sink envelopes. Unlike the earlier run, it does not assume
sink resistances. It models them from fin geometry and datasheet fan curves.
Labels: **[sim]** solver output, **[est]** estimate or assumed input, **[src]**
supplier value.

Related: [decisions D32/D35](decisions.md), [plenum CAD](plenum-cad.md),
[2026-10-25 review](review-2026-10-25.md), [BOM plenum table](../BOM.md).

## Reproduce

```sh
cd thermal && python3 plenum_cad.py    # ~11 min, stdlib only → thermal/plenum-cad-output/
```

[`plenum_cad.py`](../thermal/plenum_cad.py) imports `plenum.py` and `model.py`
unchanged. Each output file has one job:

- `hot_side.csv` and `cold_side.csv`: sink and fan operating points.
- `layouts.csv`: the combined layouts.
- `sizing.csv`: TEC operating points.
- `food.csv`: warmest and coldest wedges.
- `open_exposure.csv` and `pulldown.csv`: each as-sourced layout (column `layout`).
- `food_target.csv`: air needed for 4 °C warmest covered food, and the TEC point there.
- `current_capped.csv`: the coldest air each layout holds at ≤ 2.2 A per ADV127.
- `required_r_hot.csv`: the maximum hot-side resistance per module count.
- `results.json`: everything above, with script hashes.

## Findings

1. **The cold side is the bottleneck, not the hot sinks [sim].** One 5015 blower
   moves only ~1.4–1.8 L/s round the loop, so a 50 × 50 mm cold sink is
   flow-limited (NTU ≈ 0.3). That gives **R_cold ≈ 2.0–2.5 K/W**, against the
   ≤1.0 K/W the earlier study assumed. The TEC cold face then has to sit at about
   −13 °C to hold −5 °C air, and the extra ΔT is what costs COP.
2. **The CP60440 (6 A class) does not work at four sites [sim].** Its higher
   back-conduction makes it infeasible or ~84–122 W in every realistic layout.
   **TARK-class low-current modules (Imax 3.9 A) are feasible in all baffled layouts.**
3. **Hot-side air must be forced through the fins [sim].** With the CAD's open
   diagonals, about 60 % of the fan air bypasses the sinks. Each sink then reaches
   only 1.3 K/W and no module type is feasible. With printed baffles closing the
   gaps between sinks, each 70 mm sink reaches **0.59–0.66 K/W** at ~2.6–3.0 L/s.
   The 70 mm envelope is therefore adequate *for TARK modules*.
4. **The intake slots and wall vents restrict the 120 mm fan [est].** Its
   2.34 mm H₂O shut-off pressure leaves only ~10–12 L/s through the shell.
   Increasing slot area by 1.5× cuts R_hot by ~10 %.
5. **CAD rev 2 (2026-10-26) adopts these fixes** (see [plenum CAD](plenum-cad.md)).
   As modelled: R_hot 0.65 K/W, R_cold 1.24 K/W, 4 × TARK at ~1.6 A / 7.1–7.2 V,
   **44–47 W TEC power**, and covered warmest food at **2.3–3.1 °C** with nothing
   below −0.1 °C [sim].
6. **The serving wedge still warms when open [sim].** At steady state its top
   surface reaches 6.4–7.5 °C. Starting from covered, the top passes 5 °C after
   **27–52 min** (rev 2), against 41–72 min in the earlier study.
7. **Pull-down is slow [sim].** At 2.5 A per module (rev 2), 20 °C food takes
   **~2.5–3.6 h** to reach a 4 °C mean. Fridge-cold food (5 °C) takes 47–68 min.
   Loading chilled food matters.

## Hot-side sink and fan [est]

Model:

- **Sinks:** plate-fin, 6063 aluminium, 6 mm base, radial channels. Heat
  transfer uses the Teertstra developing-flow Nu, with fin efficiency, NTU
  referenced to inlet air, Song–Lee–Au spreading from the 40 mm source, and one
  0.15 K·cm²/W paste joint.
- **Fan:** Noctua NF-A12x25 [src: 102.1 m³/h, 2.34 mm H₂O], with its curve
  linearised between those endpoints.
- **Airflow path:** floor intake slots (5950 mm²) and wall slits (7920 mm²), both
  at Cd 0.6.
- **Inlet air:** room + 2 K (22 °C room, realistic boundary set).

| Layout (hot side) | Fan total L/s | Per sink L/s | R_hot K/W |
| --- | --- | --- | --- |
| 4 × 70 mm, open diagonals (6000 mm² bypass) | 12.0 | 1.1 | 1.29 |
| 4 × 70 mm, baffled | 10.2 | 2.6 | 0.66 |
| 4 × 70 mm, baffled, 1.5× intake/vent area | 12.0 | 3.0 | 0.59 |
| 3 × 70 mm, baffled, 1.5× | 10.7 | 3.6 | 0.53 |
| 2 × 100 × 70 mm, baffled, 1.5× | 10.5 | 5.3 | 0.40 |
| **CAD rev 2:** 4 × 70 mm, drop-in baffles (~800 mm² leakage), intake ×1.2, two slit rows (×2) | 12.2 | 2.6 | **0.65** |

A 3 mm fin pitch (24 fins, 1 mm) beats 2.5 or 4 mm at these flows.

Maximum R_hot for −5 °C air (`required_r_hot.csv`, CAD cold side) [sim]:

| Modules | 4 × TARK | 4 × CP60440 | 3 × TARK | 3 × CP60440 |
| --- | --- | --- | --- | --- |
| at 50 % Imax | 0.86 | 0.56 | 0.51 | 0.38 |

## Cold side [est]

The blower drives the closed loop: four fin banks in series, each in parallel
with any side gap, plus channel friction and four dynamic heads.

| Cold configuration | Loop L/s | h tray (lower / developing) W/m²K | R_cold K/W |
| --- | --- | --- | --- |
| 50 × 50 mm, 5 mm pitch, 10 mm side gap, MF50151V2 (3.5 CFM, 100 Pa) | 1.37 | 5.1 / 8.3 | 2.18 |
| 50 × 50 mm, 5 mm pitch, 27.5 mm side gap (CAD as drawn) | 1.42 | 5.5 / 8.5 | 2.53 |
| 50 radial × 80 mm along flow, 4 mm pitch, no side gap, MF50151V1 (4.5 CFM, 167 Pa) | 1.61 | 6.9 / 9.4 | 1.26 |
| **CAD rev 2:** 70 radial × 60 mm along flow, 4 mm pitch, 6.5 mm total side gap, MF50151V1 | 1.77 | 8.2 / 10.1 | **1.24** |

R_cold includes the 6.5 mm spacer and two paste joints. Since 1/(ṁc_p) ≈ 0.5–0.6 K/W,
more fins alone cannot get below ~0.7 K/W. Only more loop flow can.

## TEC operating points, −5 °C air [sim]

These assume the realistic boundary set, one open wedge, deck k 0.065 and the
nominal leak. The power-supply ("brick") figure is (TEC/0.9 + 8 W) × 1.25.

| Layout | Module | Load W | I A | V V | Tc °C | Th °C | COP | TEC W | Brick W |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CAD 4 × 70 baffled | TARK | 12.8–14.0 | 1.66–1.80 | 7.5–8.1 | −13 | 34–36 | 0.24–0.26 | 50–58 | 79–91 |
| CAD 4 × 70 baffled | CP60440 | — | infeasible | | | | | | |
| 4 × improved | TARK | 14.0–14.7 | 1.49–1.54 | 6.7–6.9 | −10 | 32–33 | 0.35 | 40–43 | 66–69 |
| 4 × improved | CP60440 | 14.0–14.7 | 2.7–2.8 | 7.8–8.1 | −10 | 38–40 | 0.16–0.17 | 84–91 | 126–136 |
| 3 × improved | TARK | 13.9–14.5 | 1.79–1.86 | 7.9–8.1 | −12 | 34–35 | 0.32–0.33 | 42–45 | 69–73 |
| 2 × 100 improved | TARK | 13.8–14.3 | 2.7 / infeasible | 11.1 | −15 | 39 | 0.23 | 60 | 93 |
| **CAD rev 2** | **TARK** | 14.7–15.2 | **1.57–1.61** | **7.1–7.2** | −10 | 34 | 0.33 | **44–47** | **72–75** |
| CAD rev 2 | CP60440 | 14.7–15.2 | 3.1 / infeasible | 9.1 | −10 | 45 | 0.13 | 114 | 168 |

Ranges span the lower and developing tray h. "Improved" means baffled hot sinks,
1.5× intake/vent area, 50 × 80 mm cold sinks with no side gap, and the 4.5 CFM
blower. Fewer, larger sites are worse: one blower's flow limits each cold sink,
and the loop sawtooth grows.

## Food, CAD rev 2 layout (TARK) [sim]

| h basis | Position | Warmest-wedge mean °C | Warmest top °C | Coldest bottom °C |
| --- | --- | --- | --- | --- |
| lower (8.2) | covered | 2.5 | 3.1 | 0.9 |
| lower (8.2) | open, steady | 6.5 | 7.5 | 4.7 |
| developing (10.1) | covered | 1.7 | 2.3 | −0.1 |
| developing (10.1) | open, steady | 5.4 | 6.4 | 3.4 |

For comparison, the "4 × improved" layout (50 × 80 mm cold sinks) gives 2.6–3.9 °C
covered warmest.

The covered wedges meet the 2–4 °C target with no food below −1 °C.

## Changes adopted in CAD rev 2 (2026-10-26)

1. **Hot-side baffles:** four drop-in printed plates on the diagonals, seated in
   floor rails and held down by the deck. Floor aprons under each sink's inner
   face complete the seal. Estimated leakage ~800 mm² at the bridge-arm slots and
   fan corners. No screws.
2. **More vent area:** intake slots widened from 3.5 to 4.2 mm (×1.2), with ribs
   still ≥1 mm after edge easing, plus a second wall-slit row at Z32–54 (×2),
   kept solid ±9° round the inlet grommet.
3. **Cold sinks 70 radial × 60 mm along flow, 4 mm pitch.** A 50 × 80 mm sink
   would have collided with the blower, rollers and deck seams. The wider sink
   fills the channel apart from a 6.5 mm total side gap and performs the same
   (1.24 against 1.26 K/W).
4. **Blower:** a 4.5 CFM / 167 Pa 5015-class blower (Sunon MF50151V1-1B00U-A99
   class [src: DigiKey listing]), moved 5 mm upstream and 5 mm inboard.
5. **TECs:** TARK-class 40 mm modules (CP14-127-10 class, Imax 3.9 A, R 3.32 Ω),
   modelled 4.7 mm thick. The CP60440 is dropped for the plenum.

## As sourced (2026-10-26) [sim, est]

These results assume the *target* sink geometry. The stocked trial sinks do not reach
it: see [stocked and candidate sinks](#stocked-and-candidate-sinks-2026-10-26-later-pass-sim-est).

The [sourcing pass](d34-sourcing.md) replaced three assumptions. Layout
`CAD_rev3_sourced` in `plenum_cad.py` models all three:

- **Blower:** RS PRO ODB5115-12HB (RS 144-4136) gives 4.2 CFM / 124 Pa at 1.44 W,
  the best UK-stocked 5015. The loop drops to 1.61 L/s, tray h to 6.9–9.4 W/m²K
  and R_cold rises to 1.31 K/W.
- **Baffle slots** are widened for the harness (+~500 mm² leakage, 1300 mm² in
  total), so R_hot rises to 0.674 K/W.
- **TECs:** Adaptive ADV-127-135200-S (RS 606-975), with TARK only on quote.
  [`adv127-operating-points.json`](../thermal/adv127-operating-points.json) holds
  points read by eye from its datasheet charts at Th 25/50 °C. The least-squares
  fit gives α 0.0517 V/K, R 3.29 Ω and **K 0.331 W/K**, against TARK's 0.274; the
  max-parameter fit would overstate K at 0.37.

| Module | I A | V V | COP | TEC W | Brick budget W |
| --- | --- | --- | --- | --- | --- |
| **ADV-127 (sourced)** | 1.85–1.95 | 8.6–9.0 | 0.22–0.23 | **63–70** | 98–107 |
| TARK (quote only) | 1.62–1.69 | 7.3–7.6 | 0.30–0.31 | 47–51 | 76–81 |

Results with the ADV modules:

- **Food (air held at −5 °C) [sim]:** covered warmest 2.6–3.9 °C, coldest food
  bottom +0.2 °C. The open serving wedge passes 5 °C after 11–40 min.
- **Pull-down at 2.5 A per module:** 20 °C food takes 2.8–4.9 h to reach a 4 °C
  mean; 5 °C food takes 58–114 min.
- **DPS5005 (2S2P):** ~3.7–3.9 A at ~17–18 V steady, within its 5 A rating.
  Pull-down stays capped at ~2.3–2.5 A per module.
- **Brick:** the 160 W GST160A24 covers steady state with margin.

TARK modules would save ~16–19 W if a quote is reasonable, so they remain an
optional upgrade, not a blocker.

## Stocked and candidate sinks (2026-10-26, later pass) [sim, est]

The sourcing pass bought trial sinks that do not match the modelled envelopes. This pass
models their real geometry, searches UK stock for closer parts and re-runs the as-sourced
evaluation: same NF-A12x25 and ODB5115-12HB curves, vents, 1300 mm² baffle leakage,
76 × 64 mm pockets and ADV-127 fit as `CAD_rev3_sourced`. Everything here is simulation or
estimate; no sink has been measured.

**Geometry from maker drawings** (files and hashes in
[`thermal/datasheets/MANIFEST.json`](../thermal/datasheets/MANIFEST.json), fetch with `scripts/fetch_references.py`; [est] = read by scale):

| Part | W × H mm | Base | Fins | Fin t / gap mm | Source |
| --- | --- | --- | --- | --- | --- |
| Fischer SK 100 75 SA (stocked, hot) | 66 × 40, 75 long | 10 | 7 at 10.2 pitch | 2.2–4.2 tapered, mean 3.2 [est] / ~7.0 | Fischer drawing 001014624 |
| TED TDEX6015/TH (stocked, cold) | 60 × 15.8, 60 long | 4.3 [est] | 14 + two 8.2 mm end blocks, 15 slots | 1.2 / 1.79 [est] | TED TDEX6015/TH12G sheet (same extrusion **assumed**) |
| Alutronic PR 614 (hot candidate) | 75 × 45 | 5 | 22 at ~3.5 pitch | ~1.35 mean / ~2.2 [est; matches 4.18 kg/m] | Alutronic sheet + profile |
| Alutronic PR 411 (cold candidate) | 74.5 × 22 | 3 | 13 at ~6.03 pitch | ~1.7 [est; 1.71 kg/m] / ~4.3 | Alutronic sheet |
| Fischer SK 444 (cold alternative) | 62.5 × 20 | 3.5 | 12 at 5.5 pitch | ~1.9 / 3.6 | Fischer drawing 001014249 |

**Model changes** (`plenum_cad.py`): `Sink` takes drawn channel count, gap, solid width and
wetted faces. The cold side can take explicit bypass ducts (`cold_slots`): over the fin tips
across the full 77.5 mm channel, both sides and under the base outside the 45 mm collar.
These use laminar rectangular-duct friction (Shah & London) plus one entry head. The older
single side gap stays as it was for the earlier layouts. It ignored the 1 mm over the tips
and the strip under the base, and its friction term is 4× the laminar parallel-plate value.
That understated bypass, so `CAD_rev3_sourced` (R_cold 1.31) reads 1.40 K/W as
`rev3_target_slots`. A smaller hot sink dropped into the unchanged 70 × 45 bay adds the side
and under-tip gaps (`hot_dropin_bypass`).

### Results [sim]

Two h bases (lower / developing). "Air for 4 °C" is the loop air that puts the warmest
covered food top at 4 °C; the TEC point is taken there. Brick budget = (TEC/0.9 + 8) × 1.25.

| Layout | R_hot K/W | R_cold K/W | Cold fins / bypass | Air for 4 °C | Coldest food | ADV-127 I A | TEC W | Brick W | Targets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Target sinks, slot accounting | 0.674 | 1.40 | 81 % | −4.6 / −3.0 | +1.7 | 1.83 / 1.68 | 62 / 53 | 96 / 83 | pass |
| **Stocked, drop-in** (SK 100 75 + TDEX6015) | 1.47 | **6.81** | **11 %** | −4.4 / −2.9 | — | infeasible | — | — | **fail** |
| Stocked, CAD fitted (aprons, cold fillers) | 1.36 | 1.97 (loop 0.89 L/s) | 91 % | −7.9 / −5.2 | — | infeasible | — | — | fail |
| PR 614 + TDEX6015 | 0.667 | 6.81 | 11 % | | | infeasible | | | fail |
| SK 100 + PR 411 46 mm | 1.36 | 1.81 | 93 % | | | infeasible | | | fail |
| PR 614 + SK 444 50 mm | 0.667 | 2.37 | 52 % | −4.3 / −2.9 | +1.7 | 2.38 / 2.05 | 103 / 77 | 153 / 117 | fail (I, brick) |
| **PR 614 70 mm + PR 411 46 mm (recommended)** | **0.667** | **1.81** | 93 % | −4.3 / −2.9 | +1.7 | **1.96 / 1.80** | **71 / 60** | **108 / 93** | **pass, thin margin** |
| PR 614 70 mm + PR 411 60 mm (needs lip relief) | 0.667 | 1.63 | 93 % | −4.4 / −2.9 | +1.7 | 1.89 / 1.74 | 66 / 56 | 102 / 88 | pass |

- **The stocked parts fail by a wide margin [sim].** The TDEX6015's 1.8 mm slots and 16 mm
  height leave a 7 mm gap under the tray and 8 mm at each side, so ~89 % of the loop air
  bypasses it. With ADV-127s at ≤ 2.2 A the loop can only be held at ~+11 °C. Ducting it
  (printed fillers) halves the loop flow (0.89 L/s) and still cannot reach +3 °C. The
  SK 100's seven 7 mm channels give 1.36–1.47 K/W, double the target. Either stocked part
  alone makes the system infeasible (rows 4–5), so this is not a fan or TEC problem.
- **No RS, Farnell or other UK-stocked profile meets either envelope [search, 2026-10-26].**
  Two agents searched about 460 Fischer drawings and all Alutronic and ABL standard profiles.
  RS/Farnell carry only coarse Fischer profiles near 70 mm. SK 64 has a 17 mm groove under
  the TEC face. SK 444, 649 and 670 are only at TME (EU) and are narrower. Prices and stock
  could not be read live (RS/Farnell block scripts).
- **Recommended: Alutronic PR 614 cut to 70 mm (hot) and PR 411 cut to 46 mm (cold), both
  sold by length direct from Alutronic (DE), quote required.** PR 614 matches the modelled
  target almost exactly (0.667 against 0.674 K/W), but is 75 mm wide against the 70 mm
  tangential envelope. PR 411 is 74.5 mm wide, so the circular outer lip limits its length
  to ~46 mm. 60 mm would gain ~0.18 K/W but needs a lip relief.
- **Targets with the recommended pair [sim]:** covered warmest food 4 °C needs loop air at
  −4.3 °C (lower h) / −2.9 °C (developing). Coldest food is +1.7 °C. The ADV-127 runs at
  1.80–1.96 A against the 2.2 A target, with 60–71 W TEC, ~75–87 W from the brick and a
  93–108 W budget against 110 W. The margin is thin at the lower h. Holding −5 °C air instead
  would need 2.12–2.28 A and a 124–141 W budget, so don't run colder than the food needs.
  The open serving wedge passes 5 °C after 18–45 min (from covered, −5 °C air).
  Pull-down at 2.5 A takes ~3.0–4.2 h for 20 °C food and 61–97 min for 5 °C food.
- **Food temperature at a given air temperature barely depends on the sinks** (tray h moves
  < 0.5 K). The sinks decide whether the TECs can hold that air at an acceptable current.
- **The open/pull-down rows for infeasible layouts** in `open_exposure.csv` assume −5 °C air
  they cannot reach. Their pull-down air temperatures leave the model's valid range; read
  them only as "never reaches 4 °C".

### CAD changes the recommendation needs (for the CAD owner; not made here)

- `pl_hot_sink = [70,75,45]` (radial, tangential, height): +5 mm tangential. Check the
  baffle ends (`pl_baffle_end`), corner guides, card bays and posts. `pl_fin = [1.4,2.2]`
  [est] for the thermostat J-clips.
- `pl_cold_sink = [74.5,46]` and `pl_cold_dr = 1.25`: the inner face clears the inner wall
  by 0.5 mm, and the corners reach R140.4, inside the existing R140.5 assert. Height stays
  22 mm, so `pl_pocket = [76,64]` and the spacer are unchanged. A 60 mm length would put the
  corners at R141.7, through the outer wall (R141), and needs a local relief.
- If the stocked trial parts were kept anyway: `pl_hot_sink = [75,66,40]` and
  `pl_fin = [4.0,7.0]`, plus printed fillers round a 60 × 16 cold sink. The model says this
  still cannot cool, so it is not recommended.

## Controller requirements that follow (input to D34)

- **TEC drive:** four modules 2S2P on one DPS5005. Steady state needs ~14.2–14.4 V
  and ~3.2 A with TARK (CAD rev 2), or ~17–18 V and ~3.7–3.9 A with the sourced
  ADV-127; pull-down at 2.5 A per module needs ~5 A at ~20 V, which is at
  the DPS5005 limit, so cap pull-down at ~2.3 A per module. The 24 V input gives
  enough headroom.
- **Defrost:** one DPDT polarity-reversal relay covers all four modules.
- **Fans:** one 12 V 4-pin PWM fan (NF-A12x25, ~1 W) and one 12 V 5015 blower (~1 W)
  with speed control. This needs a 12 V buck from 24 V.
- **Supply:** steady state ~44–47 W TEC (TARK) or ~63–70 W (ADV-127) plus ~8 W auxiliaries; pull-down ~100 W
  TEC. Keep the D32 ≥150 W brick for pull-down headroom.
- **Protection and sensing:** bimetal cutouts on the hot sinks, outside firmware.
  Sensors for chamber air, one food wedge, hot-sink temperature and room air.

## Limits

- Fan curves are linearised from two datasheet points. Real axial fans stall
  between those points, so the installed flow must be measured.
- Fin correlations assume clean, ideal plate channels. Frost on the cold fins
  will reduce flow and h, and defrost intervals are not modelled.
- Lip and seam leakage, the drive bore and window sealing follow the nominal
  leak case only.
- The pull-down model holds the hot-side inlet at room + 5 K (plenum.py),
  slightly more conservative than the steady-state runs.
- Blower input power is assumed (0.6–1.0 W) and goes into the cold loop.
- Stocked/candidate fin thicknesses and the TDEX6015/TH fin layout are read off drawings
  by scale [est]. Serrations on PR 411 fins and tapers are averaged. Cold bypass ducts are
  idealised rectangles; the circular channel and the corner clipping are not resolved.

## Harness slot cost (estimate, 2026-10-27)

Widening the diagonal baffle slots to 23 mm for the cable harness
([harness](harness.md)) raises the hot-side bypass from ~1300 to ~1540 mm².
In the `CAD_rev3_sourced` run that moved R_hot from 0.674 to 0.689 K/W and
added roughly 2 W of TEC power. The harness model extrapolates ~2.5 W of
slot leakage, against the 1.7 W assessed. Both are estimates. The bundles
partly block the slots (fill 0.14–0.31), which is not modelled, so the real
cost is probably lower.
