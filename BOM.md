# Cat feeder — UK prototype bill of materials

> **Current build list: [Plenum build (D34 + D35)](#plenum-build-d34-controller--d35-plenum--sourced-2026-10-26-simulated-unbuilt)** at the end of this file. The sections before it are the earlier direct-contact trial path, kept for reference.

**Sourcing review: 2026-10-24. Candidate parts, not a released build or a validated refrigerator.** Start with one instrumented wedge; order twelve thermal stacks only after the trial resolves food-temperature spread, power and retention. No purchases have been made.

Read the [sourcing evidence](kb/sourcing.md), [owner decisions](kb/decisions.md), [direct-contact thermal comparison](kb/direct-contact-thermal.md) and [airflow study](kb/airflow.md). Prices exclude delivery unless stated. **D** = directly read supplier page/datasheet; **I** = search-index observation, requiring checkout confirmation; **?** = price/stock unverified. All observations below were collected on the review date; indexed delivery dates may be stale.

**Latest bench recommendation:** one **CP60440** plus **JT-DPS5005**, or reuse a
suitable bench supply. See [TEC power/control](kb/tec-control.md) for the initial
1.2 A-limited, 0–5 V characterization sweep and conditional twelve-site wiring.
No metal cold plates are on the current purchase list.

**Latest controller direction:** [revision B](electronics/revb/README.md) integrates
the STUSB4500 USB-C PD circuitry, A4988 stepper driver and efficient logic/fan
regulators. The SparkFun PD breakout, Pololu motor carrier and two Pololu buck
modules below are standalone/earlier-revision options, not additional purchases
for that integrated board. Revision B's component selection and checks are in
progress; its assembled cost is not yet established.

**Controller PCB draft:** the [editable crescent controller](kb/pcb-design.md)
has a separate [54-part mixed SMT/THT assembly BOM](electronics/pcb/assembly-bom-all.csv)
and [supplier-code/stock evidence](electronics/pcb/SOURCING.md). Independent
review is complete and a JLCPCB project has been prepared from these files.
Supplier placement/process confirmation remains open. Economic PCBA has a
two-assembled-board minimum; only one controller is fitted per feeder.
The board replaces the standalone ESP32 devkit and includes the VMOT capacitor,
signal pull-ups and listed connectors. The A4988 carrier, external regulators,
TEC power path, sensors and harness remain separate purchases. Avoid buying
both controller implementations or duplicating the fitted capacitor.

## Mechanical baseline

Current [CAD parameters](cad/parameters.scad): **Ø316 mm body**, Ø280 mm tray, twelve rounded wedges in four removable quarters; twelve thermal positions at radius 105 mm. Each position currently reserves a **40 × 40 × 4 mm TEC directly contacting PETG** and **40 × 40 × 40 mm sink**. The small metal cold caps have been removed at the owner's request (D19). These are packaging allowances, not proven purchased-part interfaces.

Construction remains PETG, no mechanical screws/bolts and no added foam. Honeycomb insulation belongs in Bambu print settings, not explicit CAD cells; equipment needs floor-supported, top-loaded bounded bays. Daily removal/cleaning must be tool-free. **Electrical screw terminals are explicitly permitted** by the latest PCB request (D22).

## 1. One-wedge thermal trial

“Full” means conditional total fitted quantity, **including** the trial part if reusable. Alternatives are mutually exclusive, not quantities to add together.

| Item / exact product and purchase route | One-wedge quantity | Full quantity | Specification, purpose and fit dependency | Observed price / availability |
|---|---:|---:|---|---|
| First 40 mm sample: [Same Sky CP60440, Anglia Live](https://www.anglia-live.com/product/617268/CP60440/SAME-SKY--CUI-DEVICES-) | 1 | 12 only after trial | **40 ±0.3 × 40 ±0.3 × 4.0 ±0.1 mm**, silicone sealed, 100 mm leads; matches nominal CAD class. Imax 6 A / Qmax 53 W are catalogue maxima, **not** intended settings. Initial test ceiling 1.2 A; contact height/tolerances still need checking. | **D:** £18.38 each, 50 stock, MOQ 1; **B2B-only supplier**, VAT basis unverified. |
| 40 mm TEC candidate: TARK **56610-510**, **CP14-127-10-L1-RT-W4.5** — [manufacturer](https://tark-solutions.com/products/thermoelectric-cooler-modules/peltier-cp-series/CP14-127-10-L1-RT-W4.5), [UK enquiry route](https://www.thermoelectricdevices.co.uk/product/cp1412710l1w4-5/) | 1 if selected | 12 if selected | Approx. 40 mm square, **4.700 ±0.025 mm thick**, RTV sealed, 114.3 mm leads; Imax 3.9 A, Vmax 13.9 V, R 3.32 Ω. Qmax 32.17 W at Th 27°C / ΔT 0 is a catalogue limit, not feeder cooling. **0.7 mm thicker than CAD.** | **?:** request a quote for the exact sealed part; UK page lists the base, non-RT name. Do not accept a silent substitution. |
| Lower-current comparison: Same Sky **CP203475H**, [manufacturer](https://www.sameskydevices.com/product/thermal-management/peltier-devices/single-stage-peltier-modules/cp203475h), [Mouser UK 490-CP203475H](https://www.mouser.co.uk/ProductDetail/CUI-Devices/CP203475H?qs=OEYMhS7p3YaD7QMZoxNU%252BA%3D%3D) | 1 instead, or 1 additional comparison sample | 12 only after adaptation | **30 × 30 × 4.75 mm**, silicone sealed, 100 mm leads; Imax 2 A, Vmax 15.7 V, R 6.7 Ω ±10%. Qmax 18.2 W at Th 27°C / ΔT 0. Smaller direct-contact footprint changes food coverage and location. | **D:** manufacturer specification and curves. **?:** UK price/stock; Mouser page challenged automated access. |
| Hot-side sink: [Fischer ICK S 40x40x20, RS 674-4835](https://uk.rs-online.com/web/p/heatsinks/6744835) | 1 bench sample | 12 only after layout revision/test | **40 × 40 × 20 mm pin-fin**; catalogue 3.5 K/W. **Not a drop-in choice:** only 6 mm would project below the current deck. Airflow/support must be adapted; catalogue rating is not installed performance. | **I:** £13.76 ex / **£16.51 inc VAT**; 64 shown at another location. |
| Shared fan: [Noctua NF-A12x25 PWM, Overclockers UK](https://www.overclockers.co.uk/noctua-nf-a12x25-pwm-fan-120mm/FG-06R-NC.html) | 1, reusable | 1 provisionally | **12 V**, 120 × 120 × 25 mm, 0.14 A max, 4-pin PWM/tach, 105 mm hole pitch. Includes NA-AV2 silicone mounts; check pull-through access/fit. Airflow across all twelve sinks is unproven. | **I:** **£29.99 inc VAT**, in stock. [Manufacturer specification](https://noctua.at/en/products/fan/nf-a12x25-pwm). |
| TIM: [ARCTIC MX-4 4 g, ACTCP00002B, Scan](https://www.scan.co.uk/products/arctic-mx-4-thermal-paste-4g-high-durability-enthusiast-for-all-cpu-coolers) | 1 syringe | Shared consumable; usage TBD | Thin film at TEC–sink **on the dry hot side**. Not glue or a food/sliding-tray interface; no cold-side paste is proposed. | **I:** **£3.98**, due 26 October 2026; reconfirm VAT/arrival. |
| Surface-temperature logging: [waterproof SMD DS18B20 sensor, The Pi Hut](https://thepihut.com/products/waterproof-smd-ds18b20-digital-temperature-sensor) | 2 | TBD | 3–5.5 V, 1-Wire; cold-side and sink-base logging. Cold-side attachment must avoid the sliding track and not force an air gap; a fine probe may be needed. Exact package/attachment to confirm. | **I:** **£6.70 inc VAT each**, in stock. |
| Food/ambient exploratory probes: [DS18B20-compatible probe, The Pi Hut — select ~1 m lead](https://thepihut.com/products/waterproof-ds18b20-digital-temperature-sensor-extras) | Up to 5; reuse fine probes/logger first | TBD | 3–5.5 V, metal tip Ø6 × 30 mm. Four food positions plus ambient; compare/calibrate probes. Large tip can disturb the wedge; listing is not food-contact certification. 4.7 kΩ pull-up **not included**. | **I:** **£3.50 inc VAT each**, in stock; compatible device, not guaranteed genuine Maxim. |
| Hot-side contact retention | Prototype fixture to establish | 12 if layout survives | Keep TEC flat against its sink and cold face at the tray datum. Trial direct PETG contact without a metal cap; long-life retention and moisture detailing remain to qualify. | No verified ready-fit stock retainer selected; printed pockets presently locate the envelopes. |
| TEC power for bench trial | Reuse 1 suitable bench supply, or 1 DPS5005 below | Shared candidate regulator if retained | Record TEC current/voltage; initially characterize CP60440 at 0–5 V with a 1.2 A ceiling. Requires a separate DC input source. | DPS5005 selected as a bench candidate below; fitted bay and thermal performance unqualified. |

**TEC recommendation:** CP60440 is the first purchasable nominal-fit sample;
TARK remains a useful exact-part quote/comparison. The smaller CP203475H loses
substantial direct-contact coverage and is not the default. Neither rated
current nor Qmax establishes efficiency or twelve-site power: consult the
[operating-curve review](kb/tec-control.md#what-the-supplier-curves-support).
The traced CP60440 is not a recommendation for generic untraceable TEC1-12706s.

## 2. Motion and local control — after the thermal trial, or on a separate motion rig

These are **zero for a purely thermal trial** except the ESP32 if used as the logger. Full quantities are independent of the twelve thermal sites.

| Item / exact UK purchase link | Trial / full quantity | Specification and purpose | Observed price / availability |
|---|---|---|---|
| [STEPPERONLINE 17HS08-1004S](https://www.stepperonline.co.uk/nema-17-bipolar-stepper-motor-1-8deg-16ncm-22-66oz-in-1a-extruder-motor-42x42x20mm-4-wires-17hs08-1004s.html) | 0 / 1 | NEMA17, 1.8°, **1 A/phase**, 3.7 Ω/phase, 0.16 Nm holding torque; **21.5 mm body**, nominal 42 mm face (42.3 mm max), Ø5 mm **D shaft, 20 ±1 mm projection**, 400 mm leads. Current-regulated drive, not direct connection to 20 V. Needs screwless motor retention and updated shaft/body clearances. | **I:** £6.31 base + £3.43 UK-stock premium; 20 UK units shown. VAT/final total unverified. |
| [Pololu A4988 Black Edition, product 2128, The Pi Hut](https://thepihut.com/products/a4988-stepper-motor-driver-carrier-black-edition) | 0 / 1 | 8–35 V motor supply, 3–5.5 V logic; use 3.3 V logic. Approx. 1.2 A/phase continuous without additional cooling under supplier conditions; set coil current and verify installed temperature. Header supplied unsoldered. Sleep when parked if mechanically acceptable. | **I:** **£9.60 inc VAT**, five left. Requires local VMOT capacitor below. |
| [Olimex ESP32-DevKit-LiPo, The Pi Hut](https://thepihut.com/products/olimex-esp32-devkit-lipo-esp32-development-board) | 0–1 for logging / 0 with custom PCB | ESP32-WROOM-32, **48 × 28 mm**, headers fitted, micro-USB, user button. Standalone bench alternative to the custom controller; no battery needed. Feed via a supported 5 V input, never the PD bus directly. | **I:** **£7.70 inc VAT**, in stock. |
| [Photo-interrupter module, The Pi Hut](https://thepihut.com/products/photo-interrupter-sensor) | 0 / 2 provisionally | 3.3–5 V, 26.8 × 15 × 18.7 mm, **6 mm slot**, Schmitt output and cable. Two channels for twelve-position ring plus unique home; printed flags/ring remain to design. Supplied **20-slot disc is unsuitable** for twelve positions. | **I:** **£3.50 inc VAT each**, in stock. |
| [Adafruit VL53L0X breakout 3317, The Pi Hut](https://thepihut.com/products/adafruit-vl53l0x-time-of-flight-distance-sensor-30-to-1000mm) | 0 / 1 candidate | 3–5 V breakout, I²C, nominal 30–1000 mm ranging; cat-presence input. Verify fur, lighting and placement. Board dimensions vary in listing/revision; measure actual board before mount design. | **I:** **£16.20 inc VAT**, eleven left. Defer until access geometry is established. |

The motor's **holding torque is not a loaded, cold-tray indexing result**. The direct-drive keyed coupling remains provisional. No gearbox, purchased cups or bearing kit is added without a demonstrated need.

## 3. Power — retain 100 W USB-C PD provisionally

For the final feeder, the starting architecture remains **20 V / 5 A USB-C PD → protected DC bus → controlled TEC power**, with separate logic and fan rails. The motor driver can use the 20 V bus, so a large shared 12 V converter is unnecessary. A low-ripple adjustable voltage regulator with current limiting is also a candidate; a dedicated constant-current topology is not mandatory. A PD trigger alone provides no temperature control.

| Item / exact purchase link | Trial / full quantity | Specification / integration requirement | Observed price / availability |
|---|---|---|---|
| [Anker B121B 100 W charger bundle, UK](https://www.anker.com/uk/products/b121b-100w-3-ports-gan-charger) | 0 if using bench supply / 1 candidate | Select UK mains version; single C1/C2 port supports **20 V / 5 A**. Dedicate one port. Continuous output/temperature derating needs confirmation; included cable's 5 A rating must be checked. | **D:** £59.89 displayed with £19.90-off banner; checkout price and stock unverified. |
| [SparkFun DEV-15801 STUSB4500 PD board, The Pi Hut](https://thepihut.com/products/sparkfun-power-delivery-board-usb-c-qwiic) | 0 / 1 candidate | 5–20 V, up to 5 A; three NVM PDO profiles. Commission 20 V/5 A via I²C; verify high-current output connection and power-good/default-5-V behaviour. Qwiic is for control, **not TEC power**. No native ESPHome support assumed. | **I:** **£30.70 inc VAT**, two left. |
| [StarTech USB31CCV1M, RS 240-6250](https://uk.rs-online.com/web/p/usb-cables/2406250) | 0 / 1 only if needed | **1 m USB-C–USB-C, 100 W / 20 V / 5 A**, USB-IF certified; use an appropriately e-marked 5 A cable. Avoid duplicate purchase if charger includes equivalent. | **I:** **£24.36 inc VAT**, 129 + 21 units shown. |
| [Pololu D24V10F5 5 V/1 A buck, The Pi Hut](https://thepihut.com/products/pololu-5v-1a-step-down-voltage-regulator-d24v10f5) | 0 if USB-powered logger / 1 | 5.1–36 V input, 18 × 13 × 3.5 mm; logic supply. Check ESP32 transient demand and startup while PD is still at 5 V; rated regulation requires input headroom. | **I:** **£12.50 inc VAT**, in stock. |
| [Pololu D24V5F12 12 V/500 mA buck, The Pi Hut](https://thepihut.com/products/pololu-12v-500ma-step-down-voltage-regulator-d24v5f12) | 0 if bench has 12 V / 1 | Approx. 12.1–36 V input, **13 × 10 × 3 mm**, fan-only rail. Fan startup and PD fallback must be handled; no 12 V output from a 5 V input. | **I:** £8.60; stock/VAT basis to reconfirm. |
| [Joy-IT JT-DPS5005, Rapid 00-0660](https://www.rapidonline.com/joy-it-jt-dps5005-programmable-bench-psu-0-50v-0-5a-250w-oled-remote-control-00-0660) | 1 if no bench supply / 1 conditional shared driver | **6–55 V input, 0–5 A CV/CC buck**, ~18.2 V maximum output from 20 V before losses; stock front-panel/UART control. **42 × 45 × 80 mm: does not fit current bay.** Electrical screw terminals may remain under D22. | **D:** £37.33 ex / **~£44.80 inc VAT**, four immediate. Published 100 mVpp ripple; verify actual operation. |

**Explicit alternative, not an adopted change:** [MEAN WELL GST120A24-P1M, DigiKey UK](https://www.digikey.co.uk/en/products/detail/mean-well-usa-inc/GST120A24-P1M/7703595), **24 V / 5 A / 120 W**, 167 × 67 × 35 mm, centre-positive 5.5/2.5 mm plug, IEC C14 inlet. Indexed **£33.67 ex / £40.40 inc VAT**, 4,807 stock. Quantity 0 now / 1 if this route is chosen **instead of** charger + PD board + USB-C cable. UK mains lead is separate; matching DC connector and regulator compatibility remain to select. This reduces negotiation complexity but does not validate the thermal budget.

**Conditional scaling:** four parallel strings of three matched TECs (3S4P),
using adjustable voltage and a total current ceiling. At 1–1.2 A/string the
output is 4–4.8 A; branch balance still needs measurement. A **70 W TEC-output
budget** gives **85.8 W source input** at assumed 90% efficiency plus 8 W
auxiliaries; it is not measured consumption or proven cooling. The
[control study](kb/tec-control.md) also links the optional Pololu 2815 enable
switch and W1209 thermostat, and explains ESPHome UART control, shutdown and
the extra interfaces needed for an installed system.

## 4. Wiring, protection and printed consumables

Quantities below are initial allowances, not a finished harness take-off. Reuse supplies where available; keep connectors and electronics on the dry side.

| Item / exact purchase link | Initial / eventual quantity | Specification / purpose | Observed price / availability |
|---|---|---|---|
| [HobbyRC 18 AWG silicone wire, black + red, 1 m each](https://www.hobbyrc.co.uk/18-awg-flexible-silicone-wire-black-red-1m-2) | 1 pack / measure loom | Short DC power/TEC bench leads. Confirm conductor and installed ampacity; choose bus gauge from actual current, length and bundling. | **I:** **£1.95 inc VAT**, in stock. |
| [WAGO 221-412 two-way lever connectors, pack of 3](https://thepihut.com/products/wago-2-way-block-connector-12-24-awg-pack-of-3) | 2 packs as bench allowance / count after wiring design | Screwless removable splices; **one block per conductor**, not a two-pole connector. 0.14–4 mm² fine-stranded, 32 A IEC rating, 11 mm strip. Keep polarity labelled. | **I:** **£1.50 inc VAT/pack**, **sold out**. [Screwfix 100-pack](https://www.screwfix.com/p/wago-221-412-32a-2-way-lever-connectors-100-pack/8421r) £35.99 inc VAT; local stock unknown, avoid bulk solely for this trial. |
| [Littelfuse FHAC0001ZXJG inline ATO holder, RS 787-4356](https://uk.rs-online.com/web/p/fuse-holders/7874356) | 1 / 1 bus + branch needs TBD | **32 V DC, 20 A holder rating**, 16 AWG leads; actual fuse must suit downstream wiring and inrush. This is not a 20 A fuse recommendation. | **I:** **£5.10 inc VAT**, back order. |
| [Littelfuse 0287005.PXCN 5 A ATOF fuse, RS 787-4108](https://uk.rs-online.com/web/p/car-fuses/7874108) | 1 fitted + 1 spare if suitable / rating review | **32 V DC, 5 A**, candidate input fuse only. A lower-current bench/branch circuit may need a smaller fuse. Final selection requires time/current, ambient derating and wire coordination; a 5 A fuse is not a precise 5 A limiter. | **I:** £3.18 inc VAT displayed, pack basis unconfirmed; stock shown with stale future-delivery text. |
| [Panasonic EEUFR1H101, RS 708-3894](https://uk.rs-online.com/web/p/aluminium-capacitors/7083894) | 0 for thermal-only/custom PCB / 1 for standalone A4988 | **100 µF / 50 V**, radial Ø8 × 11.5 mm, 3.5 mm lead pitch. Bench alternative only: the custom PCB specifies **EEUFR1H101B, 5 mm pitch**, in its assembly BOM. Close to driver across VMOT/GND; verify bus spikes remain below driver rating. | **I:** £3.61 inc VAT displayed, confirm pack size; stock shown. |
| [3DQF Milk White PETG, 1.75 mm / 1 kg, The Pi Hut](https://thepihut.com/products/milk-white-petg-filament-1-75mm-1kg) | Existing PETG or 1 spool / slicer-derived mass TBD | Tray/wedge and fit/insulation coupons. No foam. Full printed shell, tray, hub, drive, clip and ducts need a current slicer take-off; no total print mass claimed. | **I:** **£15.30 inc VAT** sale (£17 regular), one left. Material listing does not establish hygienic printed food surfaces. |
| Small signal wiring and assembly consumables | Reuse / take-off TBD | 4.7 kΩ 1-Wire pull-up to 3.3 V, insulated signal loom, matching headers/fan connector, heat-shrink, solder/perfboard, strain relief; fan PWM interface/tach pull-up as required. Exact SKUs not selected. | Open minor-parts allowance; no complete-basket total claimed. |

## Procurement sequence and remaining gates

1. **Build one direct-contact trial:** exact TEC sample/quote, sink, fan, hot-side contact fixture and logging. Obtain relevant supplier curves/mounting limits before selecting the operating current. Reuse bench instruments; no cold cap is needed.
2. **Measure the whole wedge:** TEC cold side, sink base, ambient and multiple food locations with representative fill and insulated lid. Log current/voltage, cooldown/hold, condensation, contact drag and the warmest food point. A ceramic-face reading alone is insufficient.
3. **Then select the driver/power arrangement and motion parts:** verify installed hot-side rejection, all auxiliary power, connector ratings, shaft fit and loaded indexing.
4. **Only then expand quantities.** Twelve nominal sites do not prove twelve finished assemblies fit, remain serviceable, or stay within 100 W. Hot-side retention, regulator bay, branch balance and fitted controls still need qualification.

No full-build cost is given: TEC quotes, compression hardware, driver channels, shipping/import costs, harness and printed mass remain unresolved. See [kb/sourcing.md](kb/sourcing.md) for source conflicts, rejected candidates and the distinction between catalogue curves, simulations and future physical results.

## Plenum build (D34 controller + D35 plenum) — sourced 2026-10-26, simulated, unbuilt

**This is the current build list.** Sections 1–4 above describe the earlier
direct-contact trial path (D19) and are kept for reference. Every line below
comes from public UK listings dated 2026-10-26 and was checked against a
datasheet or a named retailer page ([sourcing evidence](kb/d34-sourcing.md)).
**Nothing is ordered.** Re-check stock in a logged-in browser before buying.
Prices are ex VAT and exclude delivery.

Verification status (D38) — simulation and geometry checks, not hardware:

- **Electrical:** [D34 simulation suite](kb/d34-simulation.md) on the card
  revision below; [controller design](kb/d34-controller.md).
- **Fit:** [plenum CAD](kb/plenum-cad.md) clearance, mesh and top-loading
  checks; [cable harness](kb/harness.md) routing, bend, slot-fill and
  hand-access checks with the real card parts.
- **Thermal:** [as-sourced sink sizing](kb/plenum-sizing.md), simulated with
  the selected sinks, TEC, blower and fan.

### Totals

| Group | £ ex VAT | Detail |
| --- | ---: | --- |
| Three D34 cards, one set of parts | 244.95 | [card BOM](electronics/d34/sourcing/bom-sourced.md) (66 lines, RS carries 58) |
| Two card sets plus spares | 406.18 | same table, right-hand columns |
| Off-card parts, priced lines | 321.01 | [off-card BOM](electronics/d34/sourcing/bom-offcard.md) |
| DPS5005 TEC regulator | 37.33 | [Rapid 00-0660](https://www.rapidonline.com/joy-it-jt-dps5005-programmable-bench-psu-0-50v-0-5a-250w-oled-remote-control-00-0660) (not in the generated tables) |
| Bare PCBs, 3 designs | ~11–23 (JLCPCB) / ~£340 inc VAT (PCB Train, 3 × 5) | No UK maker is cheaper than JLCPCB ([fab comparison](kb/d34-sourcing.md)) |

**Unpriced off-card lines:** the Alutronic PR 614 and PR 411 sinks (cut-to-length
quote from alutronic.de needed), the 17HS08-1004S motor, the Ø6 × 3 mm magnets,
the stainless basin pins, the 6 mm sleeving and the NA-EC1 fan extension.

### Key off-card parts

| Item | Qty | Part | Supplier | Status |
| --- | ---: | --- | --- | --- |
| 24 V brick, 160 W (D32) | 1 | MEAN WELL GST160A24-R7B | Farnell 2815854 | Datasheet-checked; brick hiccup mode is the short-circuit protection |
| Wall inlet socket | 1 | Kycon KPJX-PM-4S, held by the printed inlet keeper (no screws) | RS 667-7287 | 2.2 Ω MRS25 + 1 µF snubber soldered across its pins |
| TEC | 4 | Adaptive ADV-127-135200-S, 40 × 40 × 4.2 mm | RS 606-975 | Simulated ~1.8–2.0 A each at the food target |
| Hot-side sink | 4 | Alutronic PR 614 cut to 70 mm (75 × 70 × 45) | Alutronic (DE) | **Quote needed.** Stocked UK sinks fail in simulation |
| Cold-side sink | 4 | Alutronic PR 411 cut to 46 mm (74.5 × 46 × 22) | Alutronic (DE) | **Quote needed** |
| Loop blower | 1 | RS PRO ODB5115-12HB, 4.2 CFM / 124 Pa | RS 144-4136 | Below the original 4.5 CFM target; modelled with its own curve |
| Hot-side fan | 1 | Noctua NF-A12x25 PWM | Overclockers FG-06R-NC | Installed flow unmeasured |
| Sink thermostats (in the card BOM) | 4 | RS PRO T24A060ASF2-15, 60 °C NC | RS 222-8227 | **No datasheet: body and tab sizes unverified** |
| Stepper | 1 | StepperOnline 17HS08-1004S | StepperOnline UK | Motor-end connector unconfirmed |
| Rim rollers | 7 | RS PRO SS608-2RS | RS 893-7323 | |
| Crimp tools | 2 | RS PRO HT-303 (insulated terminals); Engineer PA-09 (JST XH) | RS 533-774; Amazon UK | PA-09 only for W01, W02, W28, W29 |

The off-card table also lists the sensors (DS18B20, DRV5033 hall, reed
switch), panel LED and button, inline connectors, wire, heat-shrink and
sleeving.

### Cards

| Card | Bay | Files |
| --- | --- | --- |
| d34-ctrl: ESP32-DevKitC-32E, watchdog, defrost interlock, sensor/UI headers | 45° | [BOM](electronics/d34/d34-ctrl/d34-ctrl-bom.csv), [Gerbers](electronics/d34/d34-ctrl/d34-ctrl-jlcpcb-gerbers.zip) |
| d34-pwr: 24 V entry and reverse protection, wiring fuse, 12/5 V TRACO bucks, TMC2209 StepStick | 225° | [BOM](electronics/d34/d34-pwr/d34-pwr-bom.csv), [Gerbers](electronics/d34/d34-pwr/d34-pwr-jlcpcb-gerbers.zip) |
| d34-tec: K1 cut-off, K2 reversal, thermostat loop, 12 V undervoltage cut-off, switched fans | 315° | [BOM](electronics/d34/d34-tec/d34-tec-bom.csv), [Gerbers](electronics/d34/d34-tec/d34-tec-jlcpcb-gerbers.zip) |

Plug-in modules: ESP32-DevKitC-32E (Rapid 09-1099) and BIGTREETECH TMC2209
V1.3 (3DJake). The DPS5005 sits in the 135° bay.

### Cable harness

34 leads, cut lengths and sources in the
[generated cut list](cad/generated/harness_cutlist.md). Most leads are uncut or
end-cut 300 mm JST pre-crimped leads. W01, W02, W28 and W29 are crimped from
loose SXH contacts. W05 is a Molex 450 mm Mini-Fit lead (Farnell; out of stock
on 2026-10-26, fallback 225 mm plus a soldered extension). W16 has one
soldered junction. Inline deck connectors let the deck lift out without
unsoldering.

### Printed parts (plenum-specific)

| Part | Qty |
| --- | ---: |
| Deck quarter | 4 |
| Motor bridge with hall post | 1 |
| Plenum drive with magnet pocket | 1 |
| Hot-side baffle | 4 |
| Evaporation basin (D37) | 4 |
| Card cap | 3 |
| Fin clip 66° (T0, T270) | 2 |
| Fin clip 90° (T180) | 1 |
| Sensor clip (T90, carries the sink DS18B20) | 1 |
| Inlet keeper | 1 |
| Basin probe clip | 1 |
| Panel pod | 1 |

Shell, lid, tray sectors, hub and clip come from the main build
(`scripts/export.sh`); plenum parts from `scripts/export_plenum.sh`.
Honeycomb infill is a slicer setting.

### Physical-only uncertainties

These cannot be closed by desk work. Check them on arrival or at bring-up:

- T24A060 thermostat body and tab dimensions (no datasheet).
- DPS5005 rear-terminal layout against the 135° bay.
- PR 614 fin dimensions (read from the drawing image).
- DS18B20 probe head diameter against the Ø5.3 deck bore.
- Hall-sensor field at the 3 mm gap.
- Relay release times and real drop-out voltages.
- Installed airflow, frost rate and food temperatures.
- Push-fit drain grip, and inlet-keeper retention.
