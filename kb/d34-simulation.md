# D34 controller: electrical verification by simulation

**Status (2026-10-27): FINAL run against design source hash c24e0a5435e3**
(all three cards; netlist SHA-256 values in `results/summary.json`; harness
lengths from the CAD cut list).

- **187 checks: 169 PASS, 18 FAIL.**
- **0 blocking failures, 18 advisory**, each with its disposition below.

Everything here is SIMULATION — models plus datasheet limits. Nothing was built,
soldered, powered or measured. A PASS means "inside the stated limit under the
stated model and assumptions". It is not a hardware qualification.

Related: [D34 controller](d34-controller.md) · [decisions D32–D37](decisions.md) ·
[plenum sizing → controller requirements](plenum-sizing.md) ·
[electronics/d34/README.md](../electronics/d34/README.md) · suite code
[electronics/d34/sim/](../electronics/d34/sim/) · latest results
`electronics/d34/sim/results/summary.json` / `summary.md`.

Labels: **[sim]** simulated result; **[datasheet]** limit taken from a
manufacturer document (URL, SHA-256 and quote in
`sim/datasheets/datasheet_values.json`); **[assumed]** no document found, value
chosen and stated; **[project]** an engineering margin chosen here.

## How to run

```sh
electronics/d34/sim/run_all.sh            # full suite, ~20 min on the dev machine
electronics/d34/sim/run_all.sh --only s05 # one scenario
electronics/d34/sim/run_all.sh --quick    # reduced sweeps (development only)
```

- Stage A runs `kicad-cli sch export netlist` in `cat-feeder-kicad:local`
  (KiCad 9.0.2) on the three generated schematics → `sim/build/netlists/`.
- Stage B runs `run.py` in `cat-feeder-d34sim:local` (Debian bookworm,
  ngspice-39, numpy/scipy/matplotlib; built once from `sim/Dockerfile`, the
  only step that needs network). Both stages use `--network none`, mount the
  repository read-only and write only `sim/build/netlists` and `sim/results`.
- Output: `results/summary.json` (every check: id, value, limit, operator,
  unit, PASS/FAIL, severity, advisory flag, worst corner, limit source, plus
  provenance: git revision, netlist/board/table hashes, ngspice version,
  image id, vendor model manifest, seed) and `summary.md`; per scenario
  `checks.json`, CSVs and PNG waveforms.
- Exit 0 = suite ran; FAILs are findings. Exit 2 = a scenario crashed or an
  integrity check failed (unmapped part, netlist ≠ `design.json`, changed
  safety-chain topology).
- Random sequences and Monte Carlo use fixed seeds (20261026 + n).
- `fetch_models.sh` re-downloads the manufacturer models and checks SHA-256.

## How the suite follows the design

- **Source of truth.** Values, MPN fields and pin-to-net connectivity come from
  the kicad-cli netlists. `design.json` is only cross-checked pin for pin
  (s00 fails if they differ, e.g. when a schematic was not regenerated).
- **Model table.** [`sim/part_models.csv`](../electronics/d34/sim/part_models.csv)
  maps each MPN (or, as a labelled generic fallback, the KiCad symbol) to a
  model and parameters. An unmapped part fails s00.
- **Roles, not reference designators.** Scenarios find parts by role, read from
  the netlist: the P-FET whose drain is on the brick pin, the relay whose
  contacts touch DPS OUT+, the regulator with a 12 V output, and so on. The
  2026-10-26 re-design (VMOT → VAUX, StepStick moved to the 12 V rail, TRACO
  regulators, new MPNs) was followed without scenario edits beyond the
  mapping rows.
- **Safety-chain topology check.** `d34sim/logic.py` reads and verifies the
  structure that the event model assumes: 74HC123 A grounded, B = WDT_KICK,
  CLR = TEC_EN, Q → ULN → K1, Q̄ → R/diode/C → 74HC573 LE, latch D/Q → ULN → K2,
  K1 coil fed through the thermostat connector, a flyback diode across K1, and
  the K2 coil clamped by ULN COM. It also reads the component values. If the
  structure changes, s05 reports which assumption broke instead of simulating
  the old circuit.
- **Copper.** Track geometry comes from the routed `.kicad_pcb` files. Segments
  are split at T-junctions, and THT pads join the two layers. Each net is
  solved as a resistor network for the actual injection pins, then the
  IPC-2152 fit is applied per segment.
- **Harness.** If `build/plenum/harness/cutlist.csv` exists, the lengths and gauges
  of every lead are taken from it (route length → min, cut length → nom,
  1.1 × cut → max; multi-segment chains such as the thermostat loop, TEC
  pigtails and Y-spliced probes are summed). The brick's own DC cord stays
  1.2–1.8 m. Otherwise, [`sim/harness.json`](../electronics/d34/sim/harness.json) holds
  per-lead AWG, length [min, nom, max], loop inductance, capacitance and
  contact resistance (all **[assumed]**). The brick lead is 1.2–1.8 m of cord
  plus 0.2–0.4 m inside the case; inter-card leads are 0.25–0.35 m; sensor
  leads up to 0.5 m. Drop a `harness_lengths.json` (lead → metres) from the
  CAD harness model next to it and the lengths are rescaled. Leads whose
  connector no longer exists are skipped and listed in s00.

## Models and their limits of validity

| Part | Model | Source |
|---|---|---|
| IRF4905 | Infineon SPICE macro | manufacturer. If every solver setting fails, the run falls back to a behavioural VDMOS and records this in the scenario notes; no fallback occurred in the final run. |
| IRLZ44N (fan low sides) | Infineon Level-1 SPICE macro | manufacturer. Its threshold of 2.09 V is above the datasheet's 1–2 V, so it is conservative for 3.3 V drive. |
| TL431 (UV reference) | TI SLOJ174 macromodel (DC, nominal 2.494 V); behavioural TL431 for the Vref corners 2.44 / 2.495 / 2.55 V and where the macromodel does not converge | manufacturer / behavioural |
| BC327-25 (UV pass PNP) | behavioural PNP (hFE 160–400, VCE(sat) 0.1–0.3 V) | no manufacturer model reachable |
| BAT42 (THERMO_OK clamp) | behavioural fit (VF ~0.26 V at 2 mA, 0.37 V at 10 mA) | datasheet points |
| Inlet snubber (off-board) | 2.2 Ω + 1 µF + 0.1 µH at the brick end of the W32 pigtail (`externals.json`) | README |
| 2N3904 coil drivers | onsemi model in SPICE; event model uses VCE(sat) 0.13–0.22 V | onsemi Fig. 16 |
| K2 hold-up | event model: C1 (±20 %) holds the coil through D6 after the drive drops and follows the rail through D5/R8 while driven; SPICE cross-check of hold time and C1 reverse voltage | — |
| RXEF050 / RXEF110 | resistance in SPICE; trip time from the datasheet point with I²t scaling; hold vs ambient table | datasheet |
| 1N5817, 1N5819, 2N3904 | onsemi models | manufacturer. The 1N5817's temperature parameters are odd, so its hot leakage is not relied on. |
| 1N4007 | Vishay model | second source |
| 1N4148 | onsemi 1N4148WT die model | stand-in |
| P6KE30A | behavioural fit to the datasheet VBR / VC lines, BV corners 28.5 / 30 / 31.5 V | The same fitting method reproduces Vishay's own P6KE27A model within 1.2 V at 1–14 A. |
| BZX79-C15, 1N5245B | behavioural zener | datasheet Vz, rdif and VF |
| ULN2003A | transistor-level Darlington (2.7 k / 7.2 k / 3 k from the TI schematic) | TI publishes no model. Gain is not calibrated beyond VCE(sat), so peak currents above about 0.5 A are indicative. |
| TRACO TSR 2-24120N, TSR 1-2450, Murata OKI-78SR | behavioural buck: η from datasheet curves, current limit, start-up time | No vendor models exist. UVLO thresholds are **[assumed]**; loop dynamics are a lumped L/R. |
| DevKitC AMS1117 | dropout = 0.95–1.10 V + 0.19–0.25 V/A, fitted to the only datasheet point (1.1 typ / 1.3 max V at 0.8 A) | The current dependence is **[assumed]**. |
| ESP32 | load current source (base, Wi-Fi bursts 500 mA task / 379 mA datasheet), 40 Ω GPIO drivers, clamp diodes, reset pulls from the datasheet | — |
| G2RL-2 relays | coil R (±10 %, tempco) + L, contacts switched at pick-up / drop-out current | **Coil L 0.3–2.0 H [assumed]** (Omron does not publish it). Pick-up 40–70 % and drop-out 10–40 % of rated are assumed spreads inside the datasheet must-operate / must-release limits. Armature travel 2–7 ms (operate) and 1–4 ms (release) are **[assumed]**. |
| 74HC123 / 74HC573 | python event model; SPICE output stubs (40–70 Ω) where currents matter | K = 0.44–0.52 for TI/Nexperia, **0.90–1.10 for the fitted Toshiba TC74HC123AP** (datasheet: tw = 1.0·Cx·Rx). LE threshold anywhere between VIL max and VIH min (0.94–2.36 V at 3.3 V). Toshiba says nothing about a power-up output pulse; Nexperia warns of one. |
| BTT TMC2209 V1.3 | VMOT 2 × 10 µF + 1 µF / 1.1 Ω snubber + SMF28A TVS (BTT schematic) + chopper current source | Chopper modelled as 2 A in-phase pulses at 35 kHz (worst-case ripple, not the real StealthChop waveform). |
| DPS5005 | input: constant-power load + 470 µF; output: CV/CC source + 470 µF | Input/output capacitance and efficiency (90 %) are **[assumed]**; none are published. |
| TEC 2S2P (Adaptive ADV-127-135200-S) | R 3.29 Ω/module + Seebeck 2·α·ΔT with α = 0.0517 V/K (least-squares fit to the datasheet charts, `thermal/adv127-operating-points.json`). Operating points from the thermal model: steady 3.8 A array at ΔT 48 K; pull-down 5 A at ΔT 30 K (~20 V). | `sim/externals.json` |
| Fans | NF-A12x25 with Intel-spec PWM pull-up corners (5.25 V / 1.05 k and 3.3 V / 10 k); RS PRO ODB5115-12HB blower, 0.12 A, with tach | Blower input C 1–4.7 µF and the fan-internal tach stage are **[assumed]**. |
| Brick | MEAN WELL GST160A24-R7B: 470–2200 µF output (**[assumed]**, not published), OCP 105–150 % (modelled as constant current, i.e. hiccup ignored), OVP up to 32.4 V | — |

Not simulated: firmware itself, the DS18B20 protocol beyond bus timing, the
TMC2209 chopper control loop, the DPS5005 control loop, EMC/RF, ESP32
internals at ns time scales (ESD is an analytic bound), and contact
arcing / welding physics.

## Final results [sim] — c24e0a5435e3

The only change from bef910cab0df is ctrl R12 = 47 k (THERMO_OK → IO36),
clamped by D9 BAT42 with no filter capacitor. The ctrl card was re-routed, so
netlists and copper were re-extracted.

**R12 / THERMO_OK checks:**

| Check | Result |
|---|---|
| IO36 minimum when a thermostat opens with K1 energised (SPICE at 25 °C and 40 °C; the BAT42's VF is highest cold) | **−0.25 V** (limit −0.3 V) — PASS (was −0.33 V) |
| THERMO_OK_IN high level at a 40 °C bay | **2.72 V** vs VIH 2.55 V (0.75 × VDD max 3.399 V) — PASS. Worst divider output 2.76 V: 12 V −3 %, divider 1 %, BC327 0.3 V. Minus a 37 mV drop across 47 k: BAT42 leakage 0.73 µA (Vishay Fig. 3 typical at 3 V × 2 for maximum, +30 % reading allowance) plus ESP32 input leakage 50 nA. |
| THERMO_OK_IN at 75 °C (above the bay limit, margin only) | 2.20 V — advisory FAIL. Leakage reaches ~12 µA, a 0.56 V drop. |
| Digital high level (S09, nominal) | 2.97 V — PASS |

**Everything else:** no regressions. All blocking checks from bef910cab0df
still pass, including:
- 12 V-loss races (0 of ~6000);
- slow aux-PTC trip: K1 opens ≥ 67 ms before K2;
- UV trip 9.15–9.56 V, hysteresis ≥ 0.79 V, no chatter at start-up;
- K2 pick-up 28.5 ms;
- reversed brick VDS 27.9 V;
- interlock and contract sequences.

**Advisory failures and their dispositions (18):**

| # | Check | Value vs limit | Disposition |
|---|---|---|---|
| 1–2 | s01 `ovp_tvs_power_min/max` | 123 / 10 W vs P6KE30A 5 W steady | Only if the brick fails at its OVP level, and it lasts until the brick's OVP hiccup acts (not published). Accept. The TVS may fail short, which then trips the brick. |
| 3 | s02 `aux_reverse` | VAUX −0.74 V vs −0.5 V (project) | Reversed plug-in only, brief. The TSR modules publish no reverse rating. Accept, or add a Schottky across VAUX. |
| 4 | s03 `f1_clear` | F1 may take ~550 s at 136 % | By design: F1 is a wiring fuse, and the GST160A24 hiccup OCP is the short-circuit protection (README). |
| 5 | s03 `f1_j1_minifit` | 10 A vs 9 A | Only with a constant-current brick. The GST160A24 hiccups. Accept. |
| 6 | s03 `v33_short_d1` | 1.5 A vs 1 A (1N5817) | Only during a 3V3 short, until the AMS1117 thermal shutdown. IFSM 25 A. Accept. |
| 7–9 | s05 `enum_rearm_cornerA/B/random` | 84 / 87 / 76 orderings | Only orderings that break the firmware contract (re-arm < 0.4–0.65 s after a DEFROST change). Contract sequences pass (0). Firmware rule. |
| 10 | s05 `random_rearm` | 304 random patterns | Same as 7–9 (random pin activity breaks the contract). Firmware rule. |
| 11 | s05 `cutoff_clr_retrigger` | 247 patterns | Documented 74HC123 behaviour: a TEC_EN rising edge while WDT_KICK is high re-triggers. Firmware rule: never pulse TEC_EN. |
| 12–13 | s09 `esd_iec_2`, `esd_iec_8` | 1.5 / 6.0 A vs 1.33 A (HBM-equivalent) | Leads are inside the enclosure; HBM 2 kV passes. Accept, or add TVS arrays if leads become touchable. |
| 14 | s11 `wdt_band_lo` | 0.305 s vs claimed 0.32 s | Only with the assumed ±10 % Rext/Cext leakage allowance. Document 0.30–0.65 s. Far above the 100 ms kick period. |
| 15 | s11 `latch_band_lo` | 0.297 s vs 0.32 s | As 14. Still ≫ K1 release (≤ 7.2 ms) and < the 0.8 s firmware wait. |
| 16–17 | s11 `uv_trip_mc`, `uv_trip_mc_hi` | trip 9.05–9.73 V vs 9.37 ± 0.25 V | The full TL431A Vref range (2.44–2.55 V) plus BC327 VCE(sat). Functionally fine: K1 still opens first, with hysteresis ≥ 0.86 V. Document the wider band, or use a TL431B. |
| 18 | s11 `thermo_ok_in_high_75C` | 2.20 V vs 2.55 V | Above the 40 °C bay limit. Read IO36 with the ADC (threshold ~1.4 V), as the README already advises. |

**Runtime and model notes:**
- The run took 2314 s.
- Several full-system SPICE runs converged only with behavioural replacements
  for the IRF4905 / IRLZ44N / TL431 manufacturer models; the scenario notes
  list each one.
- The PTC-trip race now applies the DPS load after the operating point. The
  first attempt had settled into the collapsed constant-power-load solution;
  a guard now reports any unpowered start instead of passing it silently.

## Results [sim] — round bef910cab0df (superseded)


**Run summary:**
- 185 checks in 2046 s; no crashes, and all integrity checks pass.
- **167 PASS, 18 FAIL: 1 blocking (rating) and 17 advisory.**

**What the extractor now reads:**
- The UV cut-off: Q6 BC327 feeding the thermostat loop (LOOP12), U1 TL431,
  and R11 / R13 / R14 (1 k / 330 / 10 k) giving the hysteresis.
- The K2 hold-up: C1 220 µF directly across the coil, fed through D5 and
  charged only through Q3.

**Models:**
- The TI TL431 macromodel (SLOJ174) is used where it converges, otherwise the
  behavioural TL431.
- There is no BC327 manufacturer model, so it is behavioural.
- The inlet snubber (2.2 Ω + 1 µF + 0.1 µH) sits at the brick end of the
  85 mm W32 pigtail (`sim/externals.json`). The brick lead is now split there.

| Priority | Result |
|---|---|
| 1. Slow 12 V loss | **Pass.** Supply-loss Monte Carlo, 12 V decay τ 1 ms–2 s, all three loss types: **0 of ~6000** (random and drop-out-worst corners). SPICE slow aux-PTC trip during defrost (0.05, 0.5 and 2 s resistance ramps × relay L × TL431 Vref corners): K1 is below 10 % at least **67 ms** before K2 reaches 40 %; K1 drops at 9.05–9.6 V on the 12 V rail. |
| 2. UV chatter / hysteresis | **Pass.** SPICE ramp over Vref 2.44–2.55 V: trip 9.15–9.56 V, recover 9.94–10.39 V, hysteresis ≥ 0.79 V. Start-up with everything at once (DPS 112 W, blower with 4.7 µF, both relays, stepper 2 A; brick −3 %, long lead): 12 V minimum 11.6 V, 0 cut-off drops. *Advisory:* the Monte Carlo trip band is 9.05–9.73 V (TL431A full 2.44–2.55 V Vref range plus BC327 VCE(sat)), slightly wider than the claimed ±0.2 V. |
| 3. K2 timing (C1 directly across the coil) | **Pass.** Drive removed from both coils at once: K1 falls to 10 % in ≤ 2.6 ms, K2 stays above 40 % for ≥ 69 ms. C1 never reverse-biased. K2 pick-up is delayed by C1 charging: the coil reaches must-operate after **28.5 ms** (K1: 1.1 ms). Q3 peak 94 mA (200 mA rating; it is gain-limited), pulse energy 17 mJ / 1.1 W peak (advisory screen 20 mJ). That 28.5 ms + 7 ms travel sits well inside the 400 ms wait before re-arming K1. Re-pick-up after a hold-up decay is the same (28 ms). |
| 4. THERMO_OK minimum | **FAIL (blocking, marginal): −0.328 V** at IO36 when a thermostat opens with K1 energised (limit −0.3 V). R12 10 k + BAT42 reduce it from −0.72 V. |
| 5. Reverse brick | **Pass.** VIN_RAW ringing gives VDS ≤ 27.9 V (55 V rating) with the off-board snubber; 29.3 V if moved onto J1. Q1 peak 0.27 A; +24V ≥ −0.76 V. Hot-plug with the snubber: VDS ≤ 1.3 V, inrush ≤ 147 A, C1 ≤ 25.4 V. *Advisory:* VAUX −0.74 V. |
| 6. Everything else | Unchanged passes (s01, s03, s04, s06–s10). Interlock: 0 hardware violations in all orderings; contract sequences 0; brown-outs 0. |

**Advisories (17):**
- Brick OVP-level fault into the P6KE30A (×2).
- VAUX during a reversed plug-in.
- F1 as a wiring fuse.
- Mini-Fit J1 under a constant-current brick.
- 1N5817 in a 3V3 short.
- Contract-dependent re-arm orderings (×4).
- The CLR re-trigger rule.
- IEC ESD (×2).
- Watchdog / latch / UV band edges (×4).

**Model note:** several full-system SPICE runs (relay coil, UV ramp, two s06
cases) converged only after the manufacturer IRF4905 / IRLZ44N / TL431 models
were swapped for their behavioural fits. Each instance is listed in the
scenario notes.

## Defects and suggested fixes [sim] — round bef910cab0df (superseded: B' resolved by R12 = 47 k)

**B'. THERMO_OK still slightly below −0.3 V at IO36** (blocking, rating,
marginal). Parts: ctrl D9 BAT42, R12 10 k; tec D1/DZ2 clamp.
- **Mechanism.** When a thermostat opens with K1 energised, THERMO_RET goes
  to about −15 V. The divider puts about −3.8 V on THERMO_OK, which drives
  ~0.38 mA through R12 into D9. The BAT42 (behavioural fit, 40 °C) holds the
  pin at −0.33 V. The ESP32 pin current is tiny (tens of µA through its own
  clamp), so the risk is low, but the pin is outside its −0.3 V absolute
  maximum.
- **Fix, any one of:**
  - R12 → 47 k (clamp current ~80 µA → about −0.22 V);
  - a lower-VF Schottky (e.g. BAT54/BAT43/SD103 class at sub-mA);
  - clamp THERMO_OK on the tec card before the lead.
- **Check:** the BAT42 VF at 0.3–0.4 mA and 40 °C at bring-up.

**Margins to keep in mind:**
- UV trip band 9.05–9.73 V over the full TL431A Vref range (claim
  9.37 ± 0.2 V). Use a 0.5 %-grade TL431B if the tighter band matters.
- K2 pick-up 28.5 ms through C1. Firmware must not treat DEFROST_FB as
  "K2 has moved"; the ≥ 400 ms wait covers this.
- Q3 pulse 17 mJ per K2 turn-on (no SOA curve published for the 2N3904).
- TEC copper +19.9 K (20 K project target).
- Watchdog 0.305–0.640 s.
- Firmware rules unchanged: run the waits after every reset too.

**Resolved from D34-3 [sim]:**
- A: slow 12 V loss race (was 25–59 % failures, now 0).
- Reverse-brick VDS margin (was 54 V, now 27.9 V).
- THERMO_OK (was −0.72 V, now −0.33 V).

## Results [sim] — D34-3 round (superseded)


**Run summary:**
- 178 checks in 1317 s; no crashes, and all integrity checks pass.
- **157 PASS, 21 FAIL.** Of the FAILs, **5 are blocking** (4 safety, 1 rating);
  the other 16 are advisory: firmware-contract-dependent, informational or
  what-if checks.

**What the extractor now reads from the netlist:**
- 2N3904 coil drivers (Q2/Q3) with the K1 diode + 15 V zener clamp (D1/DZ2).
- The K2 hold-up: D5 feed, C1 220 µF, R8 100 Ω, D6.
- The latch delay from 74HC123 half 2: R26 470 k / C5 1 µF, D2 1N5817,
  R5 1 k into LE.
- The watchdog: R1 470 k / C4 1 µF.
- C9 100 nF from Q1 gate to source.
- IRLZ44N fan low sides (Q4/Q5) with RXEF050 polyfuses on every fan feed.

All of these are cross-checked against `design.json`. Firmware contract
parameters live in `sim/firmware_contract.json` (copied from the README).

| Priority | Result |
|---|---|
| 1. K1 opens before K2 on supply loss | **3V3 loss: pass** (0 of 2000, random and drop-out-worst corner). SPICE: with both drives removed, K1 falls to 10 % in ≤ 2.6 ms while K2 stays above 40 % for ≥ 66 ms (hold-up time ≤ 185 ms; C1 never reverse-biased). **12 V loss: FAIL for slow rail decays (defect A).** |
| 2. Interlock margin | Pass. Worst-case stack: latch re-opens ≥ 284 ms after K1 is commanded off; K1 release ≤ 7.2 ms. Monte Carlo margin ≥ 293 ms. All entry/exit orderings with 0–1 s gaps, 3 parameter corners: 0 hardware-interlock violations. Contract sequences (2000, entry and exit): 0 violations. Brown-outs with ESP32 reset (both power-up assumptions): 0. |
| 3. Reverse brick | Pass. With C9, Q1 stays off: peak 0.81 A (was 31–44 A); +24V ≥ −0.84 V; StepStick VMOT ≥ −0.03 V. **Margin note:** with Q1 blocking, the cable now rings VIN_RAW down to −54 V against the 55 V VDSS (1 V margin). What-if: a 1 µF + 2.2 Ω snubber brings it to 28 V. Advisory: regulator inputs (VAUX) reach −0.74 V. |
| 4. Fan faults | Pass. A fan-lead short at the 7.2 A TSR 2 limit trips the RXEF050 in ≤ 0.48 s. IRLZ44N energy ≤ 1.3 J. +12 V copper (now 2.0 mm) +53 K at 7.2 A continuous, +0.6 K until the polyfuse trips. Switched-DC blower turn-on peak 5.7 A through the MOSFET (47 A rating). Gate drive 2.64 V vs VGS(th) max 2.0 V (+0.5 V margin; the manufacturer model's threshold is 2.09 V). Flyback ≤ 7.6 V. Tach back-drive ≤ 3.30 V. |
| 5. Watchdog band | Toshiba K 0.9–1.1 × 470 k × 1 µF with tolerances gives **0.305–0.640 s** (claimed 0.32–0.65 s). The low end falls below the claim only through the ±10 % pin-leakage allowance I added (advisory). Latch delay 0.297–0.637 s. Both stay inside the 0.8 s firmware wait and far above the 100 ms kick period. |
| 6. Previously passing checks | All still pass (details below). |

| Scenario | Outcome |
|---|---|
| s01 hot-plug (97 corners) | Pass: buck inputs ≤ 25.2 V, DPS input ≤ 25.8 V, TVS ≤ 0.02 A, Q1 inrush ≤ 147 A, F1 I²t ≤ 0.63 A²s. Advisory: a brick OVP-level fault puts 123 W into the P6KE30A. |
| s02 reverse polarity | See priority 3. |
| s03 faults | Pass except advisories: F1 is a wiring fuse (documented); Mini-Fit J1 at 10 A only under a constant-current brick; 1N5817 at 1.5 A in a 3V3 short. |
| s04 sequencing | Pass: Wi-Fi bursts give 3V3 ≥ 3.20 V; power-down order and USB back-feed fine. New: a slow aux-PTC trip (0.5 s resistance ramp) makes 12 V fall from 11 V to 4.8 V in 74 ms — inside the regime of defect A (advisory evidence). A 50 ms ramp gives 8.8 ms (outside it). |
| s05 relays and interlock | Coil drive with a hot coil: K1 24.8 mA, K2 24.3 mA (must-operate 23.3 mA). K1 clamp peak 28.2 V (2N3904 VCEO 40 V). Driver currents ≤ 93 mA (200 mA). LE edge 0.31 µs (limit 0.74 µs). D2 current 2.9 mA (25 mA). Thermostat-open cut-off within 3.2 ms. **FAIL:** THERMO_OK pin −0.72 V (defect B). Contract-dependent advisories: orderings that re-arm < 0.4–0.65 s after a DEFROST change, the CLR re-trigger rule, the PWM-hung watchdog limitation. |
| s06 DPS → TEC | Pass. Contacts ≤ 4.8 A; DPS headroom 20.9 of 21.5 V. |
| s07 fans | Pass (see priority 4). FAN1 PWM VOL 0.05 V, edges ≤ 0.65 µs. |
| s08 stepper | Pass. Ripple 0.15 V pk-pk; C8 0.56 A rms. |
| s09 I/O | Pass. Advisory: IEC-level ESD, no TVS. |
| s10 power / thermal | Pass. Brick 92 W steady / 132 W pull-down. Fan polyfuses at ≤ 0.14 A (hold 0.36 A at 50 °C). Aux PTC 0.55 A (0.79 A). TEC copper +19.9 K (20 K project limit, no margin). |
| s11 Monte Carlo | Relay pick-up now passes in all samples (2N3904 VCE(sat) gives ~0.7 V more coil voltage). Interlock margins as above. Watchdog/latch band lower ends are advisory. |

## Defects and suggested fixes [sim] — D34-3 round (superseded)

Card sources were not edited by this work.

**A. K2 can still drop before K1 when +12 V decays slowly** (blocking, safety).
Parts: tec K1/K2 coils, D5/C1/R8/D6 hold-up; scenario s05, families
`race_12v_*` and `race_aux_*`.
- **Mechanism.** With Q3 still on, D5 lets the hold-up capacitor follow a
  slowly falling rail, so both coils see the same falling voltage. The relay
  with the higher drop-out level releases first.
- **Monte Carlo (random relay spread):** 25 % of 12 V-loss runs fail. All
  failures are at 12 V decay time constants ≥ 36 ms; fast losses (τ < 50 ms)
  fail in only 3 of 1045 runs.
- **Drop-out worst corner** (K1 drops at 10 % of rated, K2 at 40 %, C1
  −20 %): failures from τ ≥ 19 ms (59 % of 12 V-loss runs, 6 % of aux-loss
  runs).
- **3V3 loss always passes.**
- **Realistic trigger.** A slow aux-PTC trip with the DPS running takes 74 ms
  from 11 V to 4.8 V (s04). A collapse of the 12 V regulator output itself is
  fast (≤ 9 ms).
- **K2 then breaks** ≤ 5 A at ≤ 21 V, inside its 8 A / 30 VDC rating, but
  against the rule.
- **Fix:** a +12 V undervoltage detector that removes K1's drive (Q2 base, or
  74HC123 CLR) below ~9 V. For example, a TL431 or a 2N3904 + 8.2 V zener
  pulling Q2_B low, or a supervisor IC. **WHAT-IF [sim]: 9.0 V threshold →
  0 of 6000 failures** in all supply-loss families at the drop-out-worst
  corner.
- **Alternative:** feed K2's hold-up through its own diode from a separately
  held rail. That still fails when the decay is slower than the hold-up time.

**B. THERMO_OK input driven to −0.72 V when a thermostat opens** (blocking,
rating). Parts: tec D1/DZ2 clamp, R1/R2 divider; ctrl R12 → IO36.
- **Mechanism.** The K1 coil current now freewheels through D1 + the 15 V
  zener into THERMO_RET. This pulls the thermostat return, and the 1 k / 330 Ω
  divider, to about −15 V for a few ms, so the ESP32 input clamp conducts
  through R12 (pin abs min −0.3 V).
- **WHAT-IF [sim]:** a 1N5817 from GND to THERMO_OK gives −0.35 V, so on its
  own it is not quite enough.
- **Fix:** a BAT54-class Schottky (VF ≈ 0.2 V at mA) from GND to THERMO_OK,
  plus R12 raised to 10 k, or the same clamp on the ctrl side at IO36.

**Margins and advisories to note:**
- **Reverse-brick VIN_RAW ringing:** −54 V against VDSS 55 V (Q1 now blocks
  cleanly, so the cable ring is undamped). Fix: an RC snubber at J1 (1 µF +
  2.2 Ω → 28 V [sim]) or a bidirectional TVS (e.g. SMBJ33CA).
- **VAUX during a reversed plug-in:** −0.74 V at the TSR inputs (no reverse
  rating published). Optional: a Schottky across VAUX (anode GND).
- **Watchdog and latch bands:** 0.305 / 0.297 s low ends vs the claimed
  0.32 s, only under the assumed ±10 % Rext/Cext leakage allowance. Either
  document 0.30–0.65 s or accept.
- **TEC copper:** +19.9 K at 5 A against the 20 K project target (zero
  margin).
- **Earlier advisories still present:** brick OVP fault into the P6KE30A;
  IEC ESD on leads; 1N5817 in a 3V3 short.
- **Firmware rules (unchanged plus one new):**
  - Bit-bang WDT_KICK.
  - Never pulse TEC_EN.
  - Keep the ≥ 0.8 s / ≥ 400 ms waits; the enumeration shows re-arm gaps
    under 0.4–0.65 s can let K1 make onto a moving K2.
  - **After any reset or brown-out, run the same waits from boot before
    re-arming** (modelled; the latch content is undefined at power-up).

**Resolved from the previous round [sim]:**
- Interlock margin (was −3.7 ms, now +277 ms).
- 3V3-loss race (was 88 %, now 0 %).
- Q1 reverse dV/dt turn-on.
- ULN2003 fan overcurrent and the fan short circuit.
- +12 V copper at the current limit (was 153 K, now 53 K).
- LE slow edge.
- C5 dump into the 74HC123 output.
- Watchdog 1.36 s (now ≤ 0.64 s).
- Relay pick-up margin.

## Assumptions the owner must confirm

- **Brick:** GST160A24-R7B output capacitance and OVP response time (not
  published); DC cord length and gauge (1.2–1.8 m 18 AWG assumed).
- **G2RL coil inductance and release time with its flyback diode.** This sets
  defects 1–3; measure it at bring-up.
- **DPS5005:** input/output capacitance, efficiency, CV/CC behaviour at
  enable.
- **Blower:** input capacitance, and whether a 4-wire PWM blower is acceptable.
- **Regulator UVLO thresholds** (not published by TRACO or Murata).
- **Harness:** the cut list read on 2026-10-26 still lists six 22 AWG DPS-output
  wires and per-probe 1-Wire headers. The coordinator states two 18 AWG wires
  and one header per bus. Re-run after the fit agent updates `cutlist.csv`.
- **74HC123 vendor:** the Toshiba part is fitted (K = 1.0). A TI or
  Nexperia substitute halves the timeout.
- **Blower** input capacitance and tach-stage design (affects defect 5 and the
  tach back-drive check).
- **Licensing:** several downloaded vendor model files restrict redistribution
  (Symmetry "commercial use restricted" headers). Decide before committing
  `sim/models/vendor/`.

## Change log

- 2026-10-27 (c24e0a5435e3, FINAL): R12 = 47 k re-run. Added the BAT42 leakage-at-temperature check on THERMO_OK_IN and a 25 °C clamp case, and a guard against collapsed operating points in the PTC-trip race. 187 checks: 169 PASS, 18 advisory FAIL, 0 blocking.
- 2026-10-27 (bef910cab0df): re-run with the TL431/BC327 UV cut-off, the parallel K2 hold-up, the BAT42 THERMO_OK clamp and the off-board inlet snubber. New checks: UV ramp thresholds, start-up chatter, SPICE slow PTC-trip race, K2 pick-up time, Q3 pulse energy. Fixed in the event model: D5 now blocks C1 from following the rail down. The TI TL431 macromodel is added; there is no BC327 model.
- 2026-10-26 (D34-3): re-run on the redesign (49de0a823799). The extractor now handles NPN coil drivers, the zener clamp, the K2 hold-up, the half-2 latch delay, MOSFET fan low sides and per-fan polyfuses. Firmware contract parameters live in `firmware_contract.json`. ESP32 reset on brown-out is modelled. Vendor model files are git-ignored (`fetch_models.sh`); without them the run falls back to the behavioural models and `summary.json` records this.
- 2026-10-26: suite created (s00–s11). Runs on D34-1, then on the
  in-progress D34-2 working tree, then on the final round (decb7e396781) with
  CAD cut-list harness lengths and the ADV-127 TEC fit.
