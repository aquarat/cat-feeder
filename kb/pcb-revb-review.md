# Revision B independent electrical review — motor and buck contracts

2026-10-24. **The reviewed block pin maps and nominal circuits are consistent
with manufacturer evidence. Full-board release remains blocked by unresolved
power-path integration and an unfinished integrated-board review.** These
findings support continued layout development; they are not supplier-project
clearance or proof of hardware performance.

Related: [KB index](README.md), [decisions D28–D31](decisions.md),
[motor rationale](pcb-motor-integration.md), [buck rationale](pcb-buck-integration.md).

## Scope and reproducibility

Reviewed the completed [motor contract](../electronics/revb/motor/circuit.json)
and [power contract](../electronics/revb/power/circuit.json), their evidence,
library footprints and analytical checks. Read project `AGENTS.md` first.
PD implementation, active block layouts and the in-progress root generator were
excluded as requested. Consequently, the dependencies below are **requirements
on the eventual integration**, not findings that a particular PD circuit fails.

Reviewed contract SHA-256:

| Contract | SHA-256 |
|---|---|
| motor/circuit.json | `bfdc47e4515f6b5eb48e115d6cfb54cbbd90c00997efc6c49e553f8f31b2a020` |
| power/circuit.json | `b510bc4d3d561fba8422d0ca079a37c834beef6279489bb971e869d0fc93b56a` |

Independent execution: **4 motor and 8 power tests passed**, using
`python -B -m unittest -v validate` in the motor directory and
`python -B -m unittest -v test_power` in the power directory. These invocations
do not regenerate block artifacts. The saved power contract equals `build()`;
running `check()` on that saved contract reproduces `analysis.json` exactly.
Independent arithmetic reproduces the motor current sensitivity below. All
41 placements' exact MPN and assembly-mode fields match their retained JLC
stock records. All six saved power-footprint hashes match `kicad-audit.json`.
Existing ngspice results were inspected, not independently rerun in this review.

## Critical inputs to settle before freezing the integrated layout

### B1 — Quantify the switched-bus inrush, including the external DPS

**Open integration blocker.** The motor's 1 Ω HoLRT resistor is a damping
candidate, not a qualified hotplug limiter. The retained bulk-only simulation
at 21 V/120 µF/0.99 Ω reports **17.317 A, 296.884 W peak, 25.188 mJ** in RM8.
Neither its 2 W continuous rating nor its five-second overload test establishes
survival of this pulse. Removing RM8 reintroduces the demonstrated undamped
20 V → 36.065 V corner, above A4988's 35 V absolute maximum.

The primary/PD integration must supply a **worst-case output slew/current-limit
specification**, including tolerances, retries and partially discharged loads,
that bounds RM8 pulse/RMS stress and upstream switch SOA. An unbounded RC gate
delay, USB supply current rating or buck soft-start duration is insufficient.
For a genuinely bounded slow ramp, the useful first approximation is
`I_RM8 = C_motor × dV/dt + I_motor`, `P_RM8 = I_RM8² × R`;
check startup load, capacitor tolerance and waveform departures separately.

Input inventory from the contracts:

- Buck input banks: **40.2 µF nominal** directly on `SYS_20V` (including the
  two 100 nF VIN bypasses); use high-side capacitance tolerances for inrush.
- Motor: **100 µF bulk + 2 µF local VBB ceramic nominal**, behind RM8;
  bulk alone can be 120 µF. Charge-pump/startup demand is additional.
- PD-side capacitance, wiring and **external DPS5005 input capacitance/startup
  behavior remain required inputs**. A separate converter's output soft start
  does not limit charging its input capacitor. Account for DPS connection or
  reconnection while the main bus is already live.

Reserve the actual controlled-inrush implementation and its thermal area before
layout freeze. The existing block values do not justify an arbitrary driver or
buck redesign; they do require this missing upstream interface to be bounded.

### B2 — Define qualification, ramp sequencing and available power

Both bucks have EN tied directly to their input. This is manufacturer-permitted
**only on the intended qualified bus**; they do not themselves reject lower PD
contracts. Establish autonomous 20 V/current-contract qualification, fallback
off, detach/contract-loss behavior and reverse-current behavior without relying
on the downstream ESP32 to power its own supply. Attachment alone is not proof
of a 20 V/5 A contract. A 5 A design needs the appropriate source and cable
capability as well as voltage selection.

**Slow-inrush interaction:** AP63203 can start as the switched bus crosses its
low-voltage operating region, while A4988 still has VMOT below its 8 V operating
minimum. The rail will traverse intermediate voltages even after successful
20 V negotiation. Define RUN-low through this ramp, PD changes and discharge;
release RUN only after valid VMOT, then wait at least 1 ms before STEP.
The 10 kΩ pull-down handles a high-impedance MCU, not firmware already driving
RUN high. Ensure that firmware/rail sensing or an existing hardware interlock
actually implements the intended sequencing; no additional interlock topology
is prescribed by this review.

The bucks reserve **11.542 W at the stated simultaneous load budgets and assumed
80% efficiency**. Motor, PD switch/cable loss and DPS input share the remaining
power; 100 W USB input is not 100 W available to the TEC regulator. Specify the
DPS operating limit and simultaneous startup case before final power routing.

### B3 — Bound transient and returned-energy voltages

Neither RM8 nor a 50 V capacitor clamps VMOT. The PD source must not be assumed
to sink regenerative current; reverse blocking can trap energy. The motor
study's ~22.4 V magnetic-energy-only example excludes tray/rotor kinetic energy
and repeated or externally driven motion. Establish the energy destination and
voltage envelope for deceleration, RUN-off, unplug and back-driving. Keep VMOT
below 35 V with margin, and buck VIN within its **32 V operating** limit.

There is **no verified “35 V TVS protection”** in these contracts. In particular,
SMBJ22A's published 35.5 V clamp at its specified pulse current already exceeds
the A4988 limit. A TVS standoff or typical breakdown value is not a clamp bound.
Whether a dump/clamp component is needed depends on the bounded integration
and measured waveforms; reserve space if that decision remains open.

## Motor circuit findings

The [Allegro rev-8 text](../electronics/revb/motor/evidence/a4988-datasheet.txt) (cached manufacturer documents: fetch with `scripts/fetch_references.py`)
and rendered pages 18/19 were independently inspected. The contract agrees:

| Function | Verified pads / connection |
|---|---|
| Winding outputs | 1 OUT2B; 26 OUT2A; 21 OUT1B; 24 OUT1A |
| Supplies and ground | 22/28 VBB → VMOT; 15 VDD → 3.3 V; 3/18 and CAD pad 29 → GND |
| Pump / regulator | 100 nF between 4 CP1 and 5 CP2; 100 nF from 6 VCP **to VMOT**; 220 nF from 8 VREG to GND |
| Controls | 2 ENABLE → GND; 12 RESET and 14 SLEEP → RUN; 16 STEP; 19 DIR; 9/10/11 high → 1/16 step |
| Current control | 17 REF → divider/filter; 23/27 → separate 0.33 Ω shunts; 13 ROSC → GND |
| NC | 7/20/25 explicitly unconnected |

Grounding ENABLE is consistent with RESET/SLEEP providing default-off behavior.
Using the **listed** ±20 µA input leakage and +1% pull-down resistance, shared
RUN reaches 0.404 V and individual STEP/DIR 0.202 V, below 0.9 V VIL at 3 V VDD.
These are checks against the published table, whose electrical characteristics
are stated at 25°C; they are not a newly established all-temperature leakage
bound. Keep the pull-downs and account for MCU pin behavior at boot/brownout.

ROSC grounded means nominal 30 µs off-time (**20–40 µs table range**) and mixed
decay on rising and falling current. It does not mean continuously fast decay:
fast decay occupies 31.25% of each off-time. The selected 100 nF X7R/220 nF X7R
capacitor classes and connections follow the reference. VREG is not a supply
for external circuitry. The two 1 µF/50 V X5R VBB bypasses still require effective
capacitance and installed-temperature checks; the 100 µF bulk does not replace
their local high-frequency function.

### Current-limit arithmetic is sound within its declared assumptions

`VREF = 3.3 × 1.5k/(1k+1.5k) = 1.980 V`;
`ItripMAX = VREF/(8 × 0.33) = 0.750 A`.
The home-state winding current is approximately 0.530 A, not the peak setting.
Independent recomputation gives:

| Stated sensitivity | Result |
|---|---:|
| 3.465 V rail; divider ±2%; shunts −3%; REF sourcing 3 µA | VREF 2.1139236 V, Rsense 0.3201 Ω |
| Apply +5% trip-current error | 0.866768 A |
| Apply +15% trip-current sensitivity | 0.949317 A |

The TA-I page-2 rendered table confirms **RL12 ±200 ppm/K**, not RL04's ±300 ppm/K.
The ±2%/±3% resistor excursions are the stated initial-tolerance plus 100 K TCR
sensitivity. Allegro's ±5% entries apply at 70.71%/100% DAC and ±15% at 38.27%,
with **VREF=2 V and TA=25°C**. The documentation correctly does not turn the
0.949 A sensitivity into a guaranteed all-temperature/all-microstep ceiling.
Blanking-time current rise and actual winding waveforms remain qualification
items. There is no basis here to increase the nominal setting to 1 A.

**Cross-block acceptance detail:** motor arithmetic assumes +3V3 ≤3.465 V.
The buck bring-up text's ESP32-only 3.0–3.6 V criterion is therefore not enough
to retain that exact motor bound. Include the 3.465 V condition while the motor
is active, or explicitly recalculate current sensitivity using measured/allowed
rail excursions. The AP63203's 3.27–3.33 V **CCM** table is not a transient or
PFM-overshoot guarantee.

## Buck circuit findings

The retained [Diodes DS41326 rev 2-2 text](../electronics/revb/power/AP63200-family.txt)
supports **1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 BST** for both selected WU parts.
Both bootstrap capacitors correctly connect BST–SW; UP1 FB senses its output
after LP1. UP2 uses 249 kΩ upper/18 kΩ lower, with 56 pF across the upper resistor,
matching the manufacturer's 12 V table. Its nominal output is **11.8667 V**;
reference/resistor corners reproduce **11.5310–12.2111 V**, before temperature
drift and dynamic ripple.

- AP63203 is fixed 3.3 V, nominal **1.1 MHz**, PWM/PFM. AP63201 is adjustable,
  nominal **500 kHz**, forced PWM; its 258 µA test-condition IQ is distinct from
  the family's 22 µA PFM headline. AP63205 is not a 12 V substitute.
- The manufacturer's [AP63203WU EVM guide](https://www.diodes.com/assets/Evaluation-Boards/AP63203WU-EVM-User-Guide.pdf)
  indexed BOM independently confirms **6.8 µH**, versus 3.9 µH in the datasheet
  table. Thus 6.8 µH is reference-supported, not a discovered value error.
- Exact Bourns **SRN6045TA-6R8M / -100M** indexed manufacturer tables confirm
  34/52 mΩ ±20%, typical Irms 3.6/3.2 A and Isat 5.7/4.6 A. Isat denotes 30%
  inductance loss at 25°C; these are not hard all-temperature saturation bounds.
- The computed 0.618/1.716 A ripple and 1.389/1.573 A startup peaks reproduce.
  The ±6% number is spread-spectrum excursion, not guaranteed oscillator
  absolute tolerance; 4 ms soft start and 80 ns minimum on-time are typical.
  Assumed extra L/current-rating derating does not create manufacturer limits.
- The 70% input/50% output bias retention, temperature factors, 10 mΩ ESR and
  10 µs response are assumptions. The 3.025 V minimum-rail estimate leaves only
  ~25 mV beyond 3.0 V under those assumptions. Require exact capacitor curves
  or biased measurements and real load-step/PFM/unload tests.
- **High capacitance matters too:** four 22 µF outputs are 88 µF nominal before
  module-local capacitors, exceeding the datasheet's usual 22–68 µF suggestion.
  That suggestion is not an absolute maximum and does not prove instability.
  Qualify loop/startup behavior at both high and low effective capacitance;
  examining only the assumed 33.66 µF low corner is insufficient. The three-cap
  12 V bank also departs from the two-cap reference.

These are qualification limits already substantially recognized by the block
authors, not evidence that the selected topology must be replaced. The 0.5 A
fan value is startup headroom, not a demonstrated continuous thermal rating.

## Exact sourcing and footprint reconciliation

Read the [motor stock snapshot](../electronics/revb/motor/evidence/stock-evidence.json)
and [power stock snapshot](../electronics/revb/power/stock-evidence.json) by exact
code; programmatically compared every populated MPN and assembly mode. Rejected
parts retained in those files were not confused with fitted parts. Stock is the
recorded 2026-10-24 public snapshot, not a new reservation or supplier acceptance.

| Fitted exact MPN / JLC code | Package/land result |
|---|---|
| A4988SETTR-T / C38437 | Exact ET custom footprint: 5×5 mm body, 0.5 mm pitch, 3.15 mm EP; 19,503 stock / 19,151 presale |
| RL12FTNR330 / C912788 | TA-I 1206, 0.33 Ω/0.5 W/1%; manufacturer body/termination dimensions fit the cited 1206 lands |
| HoLRT2512-2W-1R-1% / C5127856 | Custom 1.6×3.4 mm pads at ±3.25 mm implement 4.90/8.10/3.40 mm manufacturer land dimensions; pulse rating still open |
| 0603WAF1001T5E / C21190; 0603WAF1501T5E / C22843; 0603WAF1002T5E / C25804 | Exact 1k/1.5k/10k 0603 catalogue mappings |
| CL10B224KB8NNNC / C64705; CC0603KRX7R9BB104 / C14663; CL10A105KB8NNNC / C15849 | Exact 220 nF X7R / 100 nF X7R / 1 µF X5R, all 50 V/0603; C14663 also used by bucks |
| EEUFR1H101B / C713402 | Exact **B formed-lead 5 mm pitch**, Ø8×11.5 mm, positive pad 1; not the 3.5 mm straight-lead variant; `manualWeld` |
| Phoenix MKDS 1,5/ 2-5,08 (1715721) / C5183929 | Exact native Phoenix 5.08 mm pitch footprint inherited from revision A; `manualWeld` |
| AP63203WU-7 / C780769; AP63201WU-7 / C2071044 | TSOT26/TSOT-23-6; respectively 7,420/4,049 and 8,981/8,723 stock/presale |
| SRN6045TA-6R8M / C2041457; SRN6045TA-100M / C2046332 | Exact **TA** series, not non-TA substitutions; 6×6 mm body, 4.5 mm maximum height; 146/121 and 6,634/6,425 stock/presale |
| CL32B106KBJNNNE / C138687 | 10 µF/50 V X7R **1210**, mapped to C_1210_3225Metric |
| CL31A226KAHNNNE / C12891 | 22 µF/25 V X5R **1206**, mapped to C_1206_3216Metric |
| 0603WAF2493T5E / C22918; 0603WAF1802T5E / C25810 | Exact 249k/18k 1% 0603 divider parts |
| TCC0603COG560J500CT / C282507 | Exact 56 pF/50 V C0G 0603 feedforward part |

All listed parts have positive stock and presale snapshot values. Only CM8 and
the two motor terminals are manual-weld within these two blocks; all other
placements are `smtWeld`. Exact capacitor performance curves and some exact
distributor PDFs remain unavailable; catalogue dimensions/value matching is
not substituted for those electrical data. See [motor evidence provenance](../electronics/revb/motor/evidence/README.md),
[power sources](../electronics/revb/power/reference-sources.json) and inherited
[Panasonic/Phoenix sourcing](../electronics/pcb/SOURCING.md).

The custom A4988 pad numbering agrees with the manufacturer's top view; EP pad
29 is an explicit CAD convention for the manufacturer's unnumbered grounded
pad. Copper gaps are 0.20 mm adjacent pins / 0.25 mm EP-to-pin. Nine 0.83 mm
paste squares yield 62.5% EP coverage, a process starting point.

**TSOT footprint distinction:** the loaded KiCad land is not a literal copy of
Diodes' suggested land. KiCad uses 1.325×0.60 mm pads on ±1.1375 mm row centres;
Diodes' suggested geometry uses 1.00×0.70 mm lands and 3.199 mm overall span.
Both use 0.95 mm pitch and the correct lead numbering. The KiCad pad covers the
published 0.30–0.45 mm lead width and 2.8 mm lead-tip span, so no pad/lead mismatch
was found. Describe it as a compatible standard land, not an exact
manufacturer-land reproduction. The saved Bourns land dimensions are
2.35×5.1 mm pads at ±2.075 mm, agreeing with the cited recommended pattern.

## JLC process inputs and next review

Official pages checked on 2026-10-24:

- [Via covering](https://jlcpcb.com/help/article/pcb-via-covering): ordinary
  ink plugging excludes holes in pads and vias within 0.35 mm of a pad. A
  solder-mask tent is not the filled/capped process. Specify the chosen A4988
  thermal-via treatment and stencil apertures together; use a supported
  filled/capped process for vias in the solder land, or an explicitly reviewed
  alternative placement/process. Merely checking a generic “tented” option
  does not qualify under-pad solder wicking. The cited free filling offer is
  for six layers and above, not automatically this four-layer proposal.
- [Rails/fiducials](https://jlcpcb.com/help/article/how-to-add-edge-rails-fiducials-for-pcb-assembly-order):
  standard PCBA calls for rails at least 5 mm wide; recommended fiducials are
  1 mm copper with 2 mm mask opening, three or four around the edges, observing
  its 3.35 mm edge-clearance instruction. Resolve the crescent's process panel,
  tab positions and rail removal; these are panel-process features, not a
  reason to arbitrarily enlarge the finished enclosure PCB.
- [Economic tooling-hole guidance](https://jlcpcb.com/help/article/how-to-add-tooling-holes-for-pcb-assembly-order)
  (search-indexed official text) specifies 1.152 mm NPTH and 0.148 mm mask
  expansion, distinct from other process-edge examples. Select the actual
  service and agreed tooling plan rather than mixing Economic and Standard
  rules. Internal copper clearance around tooling holes matters on four layers.
- [Rigid capabilities](https://jlcpcb.com/capabilities/pcb-capabilities):
  multilayer outer copper supports 1/2 oz; inner copper defaults to 0.5 oz.
  State the chosen stackup. Allegro's four-layer 32°C/W and Diodes' single-layer
  2 oz 89°C/W thermal test fixtures do not establish this board's temperatures.

Before release, inspect the integrated schematic/net mapping and actual PCB:
local VIN–GND and BST–SW loops; both A4988 VBB bypasses; externally joined GND
pins/EP; shunt pickup/current-return separation; quiet REF/FB routing; continuous
nearby return plane; switch-node area; copper/via current and thermal capacity;
antenna separation; polarity and pick-and-place rotation. Check final mask/paste
clearances with the selected JLC stackup/process, then run integrated ERC/DRC
and reconcile BOM/CPL/Gerbers against the reviewed source identifier.

Physical qualification must subsequently resolve current peaks, inrush/retry,
regeneration, rail transients, real fan startup, biased capacitance and enclosure
thermal soak. **No full-board independent clearance, supplier signoff or
assembled-board result is asserted by this scoped review.**
