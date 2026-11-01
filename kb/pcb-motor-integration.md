# Revision B — direct-mounted A4988 motor circuit

2026-10-24. **Complete motor-block connection design; not a routed board or a
qualified protection circuit.** Latest owner direction moves the stepper driver
onto the main PCB. This supersedes the separate Pololu carrier implementation
for revision B. The frozen [revision-A design](pcb-design.md), supplier files and
supplier project are not modified by this block work.

Related: [decisions](decisions.md), [KB index](README.md),
[existing power simulations](pcb-power-simulation.md),
[packaging](pcb-packaging.md), [block handoff](../electronics/revb/motor/README.md).

## Decision and exact supply choice

Retain **Allegro A4988SETTR-T, LCSC C38437**, rather than changing the driver
family. Direct public JLC hydration data returned **19,503 stock / 19,151
presale** at 2026-10-24 16:16 UTC, package `WQFN-28-EP(5x5)`, `smtWeld`, extended
library. This is exact Allegro stock, not the unrelated JLC-house-code listing
or an anonymous carrier clone. Inventory is a snapshot, not a reservation.

The actual Allegro [manufacturer datasheet, rev 8](https://www.allegromicro.com/-/media/files/datasheets/a4988-datasheet.pdf)
is [cached locally](../electronics/revb/motor/evidence/a4988-datasheet.pdf) (fetch with `scripts/fetch_references.py`).
Page 18 establishes every pin; pages 4/6/9/10 establish electrical/timing values;
pages 5/12/19 establish thermal/layout/package requirements. The catalogue's
generic “overvoltage protection” wording does **not** establish a VMOT clamp.

The motor is **STEPPERONLINE 17HS08-1004S, 1 A/phase**, manufacturer current
[product page](https://www.omc-stepperonline.com/nema-17-bipolar-1-8deg-16ncm-22-6oz-in-1a-3-7v-42x42x20mm-4-wires-17hs08-1004s)
and [drawing](https://files.omc-stepperonline.com/17HS08-1004S_Full_Datasheet.pdf):
3.7 Ω ±10%, 4.5 mH ±20%, 1.8° full steps. Older reseller drawings give 3.5 Ω
and 0.13 Nm; do not mix those revisions. The current manufacturer page gives
0.16 Nm and 21.5 mm body length. Current motor drawing retrieval through the
search service succeeded; direct binary download returned HTTP 403.

`MOTOR_SUPPLY` is the **20 V nominal PD motor branch**, assumed ≤21 V steady.
It feeds a candidate 1 Ω damping resistor, then local `VMOT`. Both VBB pins use
VMOT. A4988's 8–35 V operating range does not mean 35 V is a safe design target:
**35 V is also the absolute maximum supply**. Keep RUN low during PD negotiation,
faults and transitions; operation at default USB 5 V is not specified. The
upstream PD/power designer must establish rail qualification and inrush control.

## Full circuit and preserved GPIOs

The machine-readable, 19-placement [circuit.json](../electronics/revb/motor/circuit.json)
and [generator](../electronics/revb/motor/design.py) contain **every pin-to-net,
MPN, LCSC code, datasheet, footprint and reuse mapping**. No positions/routes are
implied. Block-local references should be renumbered by the integrating designer.

| A4988 pin(s) | Name | Connection |
|---|---|---|
| 1 / 26 | OUT2B / OUT2A | M2B / M2A, retained winding terminal J17 |
| 21 / 24 | OUT1B / OUT1A | M1B / M1A, retained winding terminal J16 |
| 2 | ENABLE, active low | GND; RESET/SLEEP provide hardware-off as before |
| 3, 18, exposed pad (CAD 29) | GND | All externally bonded to local ground plane/star |
| 4, 5 | CP1, CP2 | 100 nF ceramic **between** CP1 and CP2 |
| 6 | VCP | 100 nF ceramic **to VMOT**, not to GND |
| 7, 20, 25 | NC | Explicitly unconnected |
| 8 | VREG | 220 nF/50 V X7R directly to GND; internal ~7 V, no external load |
| 9, 10, 11 | MS1/MS2/MS3 | +3V3, fixed 1/16 microstepping |
| 12, 14 | RESET/SLEEP, active low | MOTOR_RUN = ESP32 GPIO23 / WROOM pad 37; shared 10 kΩ pull-down |
| 13 | ROSC | Direct GND: internally ~30 µs off-time, mixed decay on rising and falling currents |
| 15 | VDD | +3V3; local 220 nF bypass |
| 16 | STEP | ESP32 GPIO18 / WROOM pad 30; 10 kΩ pull-down |
| 17 | REF | Fixed 1 kΩ upper / 1.5 kΩ lower divider from +3V3; 100 nF to quiet GND |
| 19 | DIR | ESP32 GPIO19 / WROOM pad 31; 10 kΩ pull-down |
| 22, 28 | VBB1/VBB2 | VMOT; one 1 µF/50 V bypass at each pin group and local 100 µF/50 V bulk |
| 23 / 27 | SENSE1 / SENSE2 | Separate 0.33 Ω, 1%, 0.5 W sense resistors to local ground |

ROSC grounding follows Allegro's low-speed microstepping recommendation. It is
not a 25 kΩ timing resistor mode and does not mean “100% fast decay”: the mixed
cycle is initially fast for 31.25% of off-time, then slow. Automatic decay via
ROSC=VDD is a possible future waveform comparison, not the fitted connection.

RESET/SLEEP both low shut off bridge FETs and reset the translator. The 10 kΩ
RUN pull-down sinks worst listed 2×20 µA leakage at about 0.404 V, below 0.9 V
VIL at the minimum 3 V logic supply. STEP/DIR use 10 kΩ rather than the previous
100 kΩ: a 100 kΩ pull-down cannot guarantee low against the specified ±20 µA
input-current bound. EN being grounded is intentional; it does not override
RESET/SLEEP. This is default-off with high-impedance MCU pins, not an independent
watchdog against firmware deliberately holding RUN high.

Wait **at least 1 ms** after RUN high before STEP. STEP high/low ≥1 µs; DIR
setup/hold ≥200 ns. RUN low resets the electrical home state, so stop/restart
position accounting needs care. 3200 microsteps/revolution means 30° is 266⅔
microsteps: accumulate 266/267 step counts and use actual position feedback.
Motor lead map: black/green = winding A+/A− (JM1.1/.2); red/blue = winding B+/B−
(JM2.1/.2); confirm winding pairs on the purchased motor before energizing.

## Current setting: 0.75 A nominal, not a 1 A nominal trim target

`ItripMAX = VREF / (8 × RS)`; 3.3 V × 1.5k/(1k+1.5k) = **1.980 V**;
RS=0.33 Ω gives **0.750 A peak phase current**. At the 70.71% home state each
phase is about 0.530 A. Neither supply current nor a single home-state winding
reading is the peak current setting. No trimmer is fitted.

For a gentler **0.625 A** initial trial, replace **only upper RM4 with 1.5 kΩ
C22843**. Retain lower RM5=1.5 kΩ and both 0.33 Ω shunts. Increasing upper RM4
reduces current. The supported adjustment range is RM4 ≥1 kΩ; lower values are
rejected by the block tests. A nominal 1 A target leaves no tolerance margin
for this 1 A-rated motor and is not provided as a supported setting.

Executed [tolerance arithmetic](../electronics/revb/motor/checks.json) includes:

- +3V3 +5% maximum = 3.465 V, a requirement on the integrated regulator;
- divider resistors ±1% plus independent ±100 ppm/K ×100 K sensitivity;
- sense resistors ±1% plus ±200 ppm/K ×100 K sensitivity;
- worst-sourcing REF input current +3 µA and divider Thevenin impedance;
- maximum VREF **2.11392 V**, minimum sense **0.3201 Ω**;
- applying the datasheet's ±5% full-scale error gives **0.86677 A**;
- using a broader **+15% error sensitivity** gives **0.94932 A**, below 1 A;
  the reduced-current option gives **0.79460 A** in that same sensitivity.

**Evidence boundary:** Allegro publishes the accuracy table at **25°C, VREF=2 V**;
±5% applies at 70.71%/100% DAC settings and ±15% at 38.27%. It does not provide
an all-temperature/all-DAC-code maximum at arbitrary VREF. Applying 15% across
the range is a conservative engineering sensitivity, **not a new manufacturer
guarantee**. Winding-current waveforms, blanking-time overshoot and temperature
must still confirm ≤1 A peak in service. The 0.75 A default deliberately retains
margin; open/short components and lifetime drift are outside this arithmetic.

Each shunt dissipates at most ~0.186 W at 0.75 A DC; sinusoidal microstepping
averages ~0.093 W per shunt over a cycle. A parked 100% DAC state can hold the
larger single-shunt value. Apply the RL-series derating above 70°C; the ±100 K
tolerance sensitivity is not permission to operate a resistor at full 0.5 W at
125°C. At 0.95 A the instantaneous shunt voltage remains around 0.32 V, below
the 0.5 V sense absolute maximum, before unmeasured switching spikes.

## Assembler parts and footprint checks

[Timestamped evidence](../electronics/revb/motor/evidence/stock-evidence.json)
retains public URL, raw HTML hash, exact model, assembly type, stock and datasheet
link. Existing part records explicitly retain the earlier same-day timestamps.

| Fitted role | Exact MPN / code | Direct JLC stock | Footprint |
|---|---|---:|---|
| UM1 | A4988SETTR-T / **C38437** | 19,503 | Custom exact ET 5×5, 0.5 pitch, EP3.15 |
| RM6/7 shunts | TA-I **RL12FTNR330 / C912788** | 20,566 | Native 1206, 0.33 Ω/0.5 W/1% |
| RM8 damping candidate | **HoLRT2512-2W-1R-1% / C5127856** | 32,674 | Custom manufacturer 2512 land; pulse qualification open |
| RM4 upper divider | **0603WAF1001T5E / C21190** | 35,146,899 | Existing 0603 1 kΩ |
| RM5 lower divider, optional RM4 | **0603WAF1501T5E / C22843** | 3,879,086 | 0603 1.5 kΩ |
| RM1/2/3 pull-downs | **0603WAF1002T5E / C25804** | 40,788,980 | Existing 0603 10 kΩ |
| CM1/4 220 nF | **CL10B224KB8NNNC / C64705** | 170,648 | 0603 50 V X7R ±10% |
| CM2/3/7 100 nF | **CC0603KRX7R9BB104 / C14663** | 44,144,359 | Existing 0603 50 V X7R ±10% |
| CM5/6 1 µF | **CL10A105KB8NNNC / C15849** | 13,777,977 | Existing 0603 50 V X5R ±10%; bias derating unresolved |
| CM8 100 µF bulk | **EEUFR1H101B / C713402** | 4,808 | Existing Ø8/P5 mm through-hole, positive pad 1 |
| JM1/2 winding terminals | Phoenix **1715721 / C5183929** | 991 | Existing 5.08 mm MKDS footprint |

Rejected shunt CSR1206FKR330/C346765 had only **3** direct stock: inadequate for
two assembled boards needing four shunts. Its snapshot is retained as an actual
sourcing iteration. Do not treat its ±100 ppm/K as the selected TA-I's ±200 ppm/K.

**A4988 package comparison:** installed KiCad 9 lacks a 3.15 mm EP variant.
The nearby `QFN-28-1EP_5x5mm_P0.5mm_EP3.1x3.1mm` is derived from a **TMC**
datasheet: 0.25×0.95 mm lands on ±2.375 mm centres, EP3.1. It was not silently
accepted as an Allegro-exact footprint. The generated footprint implements
Allegro p19: **0.30×1.15 mm lands on ±2.40 mm centres, 0.50 mm pitch,
3.15×3.15 mm EP**, 0.20 mm adjacent-pad and 0.25 mm EP-to-pin copper gaps.
Pin 1 is left-upper, numbers progress down the left edge; pad 29 names the
manufacturer's unnumbered exposed pad. Nine 0.83 mm square paste apertures give
62.5% EP paste coverage as an assembly starting point. Stencil and thermal-via
process need assembler confirmation, not a fabricated approval claim.

**Shunt comparison:** cached manufacturer RL-series sheet (TRL-XX0S001O,
2014-08-06, via distributor mirror) gives RL12 body **3.10±0.20 ×1.55±0.10 mm**,
0.55±0.10 mm height. KiCad 1206 lands are 1.125×1.75 mm at ±1.4625 mm,
with 1.80 mm inner gap and 4.05 mm outer span. They overlap the published
terminations and accommodate the body range; broad copper for heat/current
must extend beyond the solder pads. This is a drawing check, not a joint test.

**Damping comparison:** manufacturer HoLRT rev Ho-A0 (2020-04-27) gives 2512 body
6.30±0.20 ×3.20±0.20 ×0.55±0.10 mm and recommended inner/outer/width land
dimensions **4.90/8.10/3.40 mm**. Native KiCad 2512 gives 4.70/7.15/3.35 mm;
the supplied custom land uses manufacturer dimensions (1.60×3.40 mm pads,
centres ±3.25 mm). Exact supplier-linked resistor/ceramic PDF requests returned
403; manufacturer-authored RL/HoLRT series sheets were retrieved through the
linked mirrors and cached. The capacitor/terminal checks inherit the earlier
part/drawing evidence and still need normal assembler reconciliation.

Actual [KiCad-loaded pad checks](../electronics/revb/motor/footprint-checks.json)
and symbol export pass. These are library checks, not schematic ERC or full-board
DRC. The whole board must be regenerated and reviewed independently later.

## Four-layer layout and thermal recommendation

Recommend a **four-layer main PCB**, with a solid nearby ground plane, local
top/bottom ground spreading and thermal vias at the exposed pad and GND pins
3/18. Allegro's **32°C/W θJA is a JEDEC four-layer reference**, not the actual
crescent/enclosure value. A two-layer implementation could work at reduced
current with sufficient copper, but removing the carrier/heatsink makes deliberate
board-level heat spreading preferable to relying on the old carrier rating.

- Start with a compact ~20×20 mm driver/decoupling/sense zone and useful copper
  extending beyond it; reserve distance from ESP32 antenna and switching buck
  nodes. This is placement guidance, not a checked fit or minimum thermal area.
- Plan a 3×3 small-via array under/around EP (e.g. 0.20 mm finished holes,
  ≥0.45 mm lands, ~0.8 mm pitch), tied to planes. Select filled/capped versus
  managed/tented-via stencil treatment with the assembler; open holes can wick
  solder. Footprint generation does not install unqualified via-in-pad geometry.
- Route output/VMOT loops short and wide; begin around 1 mm where space permits,
  then validate finished copper/temperature rather than declaring a current rating.
- Put each shunt next to its SENSE pin; use broad power copper to its upper pad
  and a separate short sensing pickup at that pad wherever fanout permits.
  Return both low pads to the same low-impedance ground region under UM1. These
  are two-terminal shunts, so “Kelvin” means separate PCB pickup/current paths,
  not a four-terminal part. No high-current return may run through the VREF
  divider ground trace. VREF, VREG, CP and local VDD bypass loops stay local.
- Keep 1 µF ceramics closest to VBB; bulk follows within the local driver zone.
  All are downstream of RM8. Do not move the reservoir capacitor CM3 to ground.

Analytical conduction estimate: for sine/cosine microstepping,
`IA²+IB²≈ItripMAX²`; two conducting FETs give ~`2×RDS(on)×ItripMAX²`.
At 0.75 A this is **0.36 W typical / 0.484 W using the 25°C 430 mΩ maximum per
FET**. Add roughly 0.08 W motor-supply bias (20 V×4 mA) and 0.026 W logic bias
(3.3 V×8 mA), plus switching/diode loss and the rise of RDS(on) with temperature.
~0.59 W ×32°C/W ≈19°C rise is only reference arithmetic, not an installed
temperature prediction. Thermal soak must establish the real limit; thermal
shutdown (~165°C typical) is above the 150°C junction maximum and is not a
normal operating target.

Bare IC height is **0.90±0.10 mm**, compared with the prior provisional **22.1 mm
socket/carrier/heatsink stack** above the PCB. This removes that driver-stack
bottleneck. The 11.5 mm capacitor, ~15 mm provisional terminals, integrated PD
parts and underside via/solder clearances still set the actual board envelope.
No revised enclosure fit is claimed by this block study.

## VMOT overshoot: damping helps, but qualification remains open

The old worst passive corner is real as a **simulation result**:
24 V/80 µF/10 µH/20 mΩ wire/30 mΩ ESR → **43.278 V**;
20 V with the same assumptions → **36.065 V**. A 50 V capacitor does not raise
the A4988's 35 V limit, nor does 20 V nominal alone fix hotplug ringing.

Six new [ngspice runs](../electronics/revb/motor/simulation/summary.json)
reproduced those figures (43.27807/36.06506 V) and added RM8 at its −1%
resistance, **0.99 Ω**. The same bulk-only model then peaks at the source voltage:
20/21/24 V respectively. Critical total series resistance for 10 µH/80 µF is
`2√(L/C)=0.707 Ω`; 0.99 Ω gives substantial damping beyond that corner.

However, at 21 V with 120 µF the ideal-source model gives **17.32 A peak,
296.9 W peak and 25.19 mJ dissipated in RM8**. The selected 2 W part's ordinary
DC rating and five-second overload test **do not prove that pulse is allowed**.
The generic series maximum-current column is not permission for a 17 A pulse
in this exact 1 Ω part. **RM8 is a sourced layout candidate, not qualified for
uncontrolled hotplug.** Before power release, the PD/motor-branch integration
must bound inrush with a controlled slew/current-limited path or qualify a
pulse-rated damping network against actual waveforms. Do not simply omit RM8
because its qualification is open: that restores the demonstrated failing corner.
At 0.3 A branch DC, 1 Ω loses 0.3 V/0.09 W, but branch RMS current must be measured.

Regeneration is separate. RM8 is not a clamp and a USB-PD source is not assumed
to sink current. Reverse-blocking elements upstream can trap returned energy.
For context only, with Lmax=5.4 mH and 0.95 A sine/cosine peak, winding magnetic
energy is ~2.44 mJ; dumping that alone into 80 µF initially at 21 V gives ~22.4 V.
This excludes rotor/tray kinetic energy, externally forced motion and repeated
events. Test acceleration/deceleration, RUN-off, supply removal and back-driving;
provide a bounded dump/clamp path if those waveforms demand one.

**No “35 V protection” TVS is fitted or claimed.** A manufacturer
[Littelfuse SMBJ22A](https://www.littelfuse.com/products/overvoltage-protection/tvs-diodes/surface-mount/smbj/smbj22a)
has 22 V standoff but 24.4–26.9 V breakdown and **35.5 V maximum clamping at
16.9 A at 25°C**, already above 35 V before wiring inductance and temperature.
SMBJ24A reaches 38.9 V. SMBJ20A's 32.4 V figure does not automatically solve it:
20 V standoff is below the assumed 21 V high supply and clamping is pulse/temperature
dependent. A valid selection needs guaranteed standoff/leakage at high PD voltage,
worst clamp voltage including dynamics below the driver limit, energy/repetition
and fault interruption. No typical avalanche value substitutes for that check.

## Handoff status and concrete next checks

**Executed:** four topology/tolerance test groups (including deliberate faults),
actual KiCad 9 footprint loads/pad checks and symbol SVG export, six ngspice
passive comparisons, current stock reconciliation. **Not executed:** integrated
schematic/PCB ERC/DRC, layout thermal analysis, assembled current/VMOT measurements,
supplier assembly acceptance or independent revision-B review.

Integrator must retain the exact RESET/SLEEP/CP/sense wiring, connect the PD branch
to `MOTOR_SUPPLY` rather than bypassing RM8, implement the documented thermal
grounding and resolve inrush/regeneration before powered qualification. Bench
bring-up starts with the 0.625 or 0.75 A population, verifies VREF and all
microstep peak currents, observes VMOT at the chip, then tests loaded indexing
and thermal soak in the actual enclosure. No reviewer-clearance status is implied.
