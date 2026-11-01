# Sourcing evidence and procurement rationale

Reviewed **2026-10-24**. Companion to the [UK prototype BOM](../BOM.md).
**Superseded interface:** subsequent owner decision D19 removes the small metal
cold caps in favour of a direct TEC/PETG trial. Cap procurement, compression
stack and CAD dimensions below record the earlier sourcing pass; consult the
current BOM and decisions for the prototype direction.
The [direct-contact thermal](direct-contact-thermal.md) and [airflow](airflow.md)
studies add current footprint and sink-exposure evidence.
The later [TEC control review](tec-control.md) adds a purchasable CP60440 sample,
DPS5005 regulator, numeric TARK curve excerpts and conditional wiring/budgets;
it supersedes the earlier unresolved-driver status below, without claiming a
qualified fitted controller or measured refrigerator performance.
Context: [KB index](README.md), [owner decisions](decisions.md),
[component references](component-references.md), [thermal model](thermal-model.md)
and [mechanical review](mechanical-review.md).

## Status and evidence discipline

This is a catalogue/source review, with a limited visual reading of manufacturer
TEC curves. **No feeder physical thermal, torque, cleaning or life test is reported.**
Existing geometry/thermal studies remain studies; no new STL or feeder thermal
performance is claimed here. No purchased part is finalized.

The procurement recommendation follows D13: one wedge before twelve stacks.
Ordinary sourced parts, PETG, tool-free servicing, no screws/bolts and no foam
take precedence over the initial brief's custom-disc/two-TEC arrangement.

Prices/availability in the BOM carry **D** (direct source), **I** (search-index
observation) or **?** (unverified). Search results can retain obsolete arrival
dates; they are leads, not live reservations. RS direct access returned 403;
some Pi Hut fetches were subsequently rate-limited (429); the TARK page returned
406 on a repeat fetch. Mouser UK presented an automated-access challenge.
Manufacturer specifications and the Same Sky PDF were available separately.
UK tax, delivery and minimum pack sizes must be checked where not established.

## Dimensional baseline and discrepancies

[cad/parameters.scad](../cad/parameters.scad) was inspected for this review.
It currently has `body_r = 158`, hence **Ø316 mm**; historical studies use the
earlier Ø300 mm body. Tray Ø280 mm, twelve sites at r105, cap 41.28 mm square ×3 mm,
TEC 40 ×40 ×4 mm and sink 40 ×40 ×40 mm are the sourcing baseline.

| Interface | Current CAD allowance | Sourced candidate / implication |
|---|---|---|
| Cold cap | 41.28 square ×3 mm | Stock Custom Thermoelectric cap matches nominal envelope; sensor hole/edge details and tolerances still need modelling/measurement. |
| 40 mm TEC | 4 mm thickness | TARK 56610-510 is 4.700 ±0.025 mm; cap height/stack compression must be revised. |
| Smaller TEC | 40 mm pocket | CP203475H is 30 ±0.3 mm square ×4.75 ±0.025 mm; location, overhang, spreading and load application change. |
| Heat sink | 40 mm height | Fischer candidate is 20 mm high; retention/ducting cannot assume the drawn block. |
| Motor body / shaft | 28 mm / 18 mm | 17HS08-1004S drawing gives 21.5 mm body / 20 ±1 mm shaft; blind shaft stop and shoulder need review. |
| Fan | 120 ×120 ×25 mm | NF-A12x25 PWM fits nominal size; 105 mm mounting pitch, silicone mount access and duct fit remain unverified. |

## Stock caps and thermal coverage

The [Custom Thermoelectric CP-1.63-1.63-AL-01 page](https://customthermoelectric.com/cold-plate-1-63-x-1-63-x-12.html)
directly lists a ready-made 6061 cap, 41.28 ×41.28 ×3 mm, 14 g, sensor hole,
surface finish ≤32 microinches, US$13.75 each / US$11.80 at ten, **five remaining**.
This is a credible sample purchase without custom manufacturing. Finish is not
the same as a verified flatness/parallelism tolerance; request the latter for
the chosen TEC mounting method. UK delivery/import charges and twelve-piece
replenishment are unresolved.

Integration review re-opened this hyphenated product URL and confirmed the
dimensions, price and five-piece stock listing on 2026-10-24; the initial BOM's
mistyped URL has been corrected.

No exact, ready-to-use **60 ×40 ×3 mm** precision cold plate was verified.
Searches frequently returned hollow rectangular tube or cut-to-size raw stock.
Neither is a finished cold cap. Do not turn the geometry comparison into a
purchase recommendation or reintroduce custom manufacture by implication.

The [thermal study](thermal-model.md) identifies warm remote food regions even
with an ideal 0°C square cap. Its longer-cap comparison improves coverage but
does not establish all-food refrigeration. At r105 the 60 ×40 arrangement has
only about 0.186 mm bare adjacent clearance and overlapping 0.3 mm-clearance
pockets; r107 still leaves thin webs. These are existing model results, not
measured food temperatures or a qualified alternative stock assembly.

## TEC selection and curve evidence

### Candidate identities

1. **TARK 56610-510 / CP14-127-10-L1-RT-W4.5**:
   [manufacturer specification/interactive curves](https://tark-solutions.com/products/thermoelectric-cooler-modules/peltier-cp-series/CP14-127-10-L1-RT-W4.5).
   Approx. 39.88/40 mm square, 4.700 ±0.025 mm thick, RTV sealed, 114.3 mm leads;
   Imax 3.9 A, Vmax 13.9 V, R 3.32 Ω, Qmax 32.17 W at Th 27°C and ΔT 0.
   The [Thermoelectric Devices UK listing](https://www.thermoelectricdevices.co.uk/product/cp1412710l1w4-5/)
   is for the base CP14-127-10-L1-W4.5 name, not proof of exact sealed-part stock.
   Its site directs enquiries to **sales@thermoelectricdevices.co.uk** while
   updating. Request exact part, quantity-one/twelve prices, lead time,
   compression guidance and low-current Qc/V curves at the intended hot side.
   No numeric low-current operating point was extracted from its interactive
   plots in this review; this is the footprint-preserving quote candidate.
2. **Same Sky CP203475H**:
   [manufacturer page](https://www.sameskydevices.com/product/thermal-management/peltier-devices/single-stage-peltier-modules/cp203475h),
   [CP20H datasheet, revision 1.06 dated 2024-09-12](https://www.sameskydevices.com/product/resource/cp20h.pdf).
   Pages 1–2 specify 30 ±0.3 mm square, 4.75 ±0.025 mm thick, silicone/703 RTV
   seal, 22 AWG leads 100 ±5 mm, Imax 2 A, Vmax 15.7 V, R 6.7 Ω ±10%.
   Qmax is 18.2 W at Th 27°C / 19.5 W at Th 50°C; ΔTmax 70/77°C is at
   **zero heat load**, with the datasheet noting vacuum conditions for ΔTmax.
   Maximum assembly compression is 1 MPa, **not a recommended working preload**.
   [Mouser UK 490-CP203475H](https://www.mouser.co.uk/ProductDetail/CUI-Devices/CP203475H?qs=OEYMhS7p3YaD7QMZoxNU%252BA%3D%3D)
   is an exact order route, but UK stock/price were not verified. A stock count
   from another regional index is not treated as UK availability.

### What the published curves actually support

The CP203475H plots on **page 7** were visually inspected. At **Th = 50°C,
ΔT = 40 K (Tc = 10°C)**, the approximate readings are:

| Current | Net heat pumped Qc | Module voltage | Calculated electrical input I × V |
|---:|---:|---:|---:|
| 0.8 A | About 3.5 W | About 8.5 V | About 6.8 W |
| 1.2 A | About 6 W | About 12 V | About 14 W |

These are **rough manufacturer-curve readings**, roughly ±0.5 W/±0.5 V visual
precision, not bench measurements, fitted model parameters or chosen operating
points. In particular, **Tc = 10°C is not the required cold-cap/food target**.
At Th 50°C / ΔT 50 K (Tc 0°C), the 0.8 A curve falls to only about 1–2 W Qc.
The 0.4 A curve has no positive Qc at ΔT 40 K. Simply reducing current can
therefore remove useful cooling at the required temperature difference.

Illustratively, twelve modules at the first point consume about **82 W at the
TECs alone**; the second is around **170 W**. These arithmetic examples exclude
converter losses, fan, controller and motor, and do **not** predict feeder
performance. They explain why the 2 A part is worth a sample comparison yet
cannot establish that twelve sites meet the provisional 100 W architecture.

Selection must compare **Qc, input power and Qh = Qc + I×V** at actual Th/Tc,
including contact drops and sink/airflow feedback. Published net-Qc curves
already include internal back-conduction; do not subtract KΔT again. When
using a separate physical model, include that leakage once. Twelve installed
modules also create twelve passive heat paths when unpowered; quantify them
rather than assuming idle sites are insulated. Smaller footprint alone does
not establish a lower thermal conductance or better system efficiency.

### Rejected shortcuts

- Generic “TEC1-12706 / 60 W” offers lack the required exact low-current curves,
  traceability and sealing evidence. Do not multiply their headline Qmax by twelve.
- TARK **56610-511 EP** is not interchangeable with the selected RT candidate:
  manufacturer seal description includes **low-density syntactic foam epoxy**;
  broker electrical specifications also conflict. It is not the no-foam default.
- A 30 mm TEC under the 41.28 mm cap needs new spreading and compression checks;
  the smaller part is not a drop-in 40 mm replacement.

## Hot side and screwless retention

The [Fischer ICK S 40x40x20 / RS 674-4835](https://uk.rs-online.com/web/p/heatsinks/6744835)
is a credible 40 mm-footprint sample, listed at 3.5 K/W and £16.51 inc VAT.
Its rating conditions must be checked against manufacturer data; the installed
air path, spacing and simultaneous sink loading must be tested. No exact
40 ×40 ×40 mm sink was verified. The actual 20 mm height is deliberately stated.

A cheaper [RS 750-0951 sink](https://uk.rs-online.com/web/p/heatsinks/7500951)
is 40 ×40 ×18 mm, indexed £2.98 inc VAT and 8.2°C/W under a distributed-load,
vertical-fin/60°C rating condition. That is not directly comparable with the
Fischer number without matching conditions. Adhesive mounting does not supply
TEC compression, and no cooling qualification follows from either rating.

[Noctua's fan data](https://noctua.at/en/products/fan/nf-a12x25-pwm) establishes
12 V, 0.14 A max, four-pin PWM/tach and the 120 ×120 ×25 mm envelope. Use the
manufacturer data over contradictory reseller attributes. For example,
[Scan's chromax NF-A12X25-PWM-CH-BK-S listing](https://www.scan.co.uk/products/120mm-noctua-nf-a12x25-pwm-chromax-black-swap-fan-12v-9-blade-sso2-bearing-2000rpm-60cfm-airflow-226)
showed £30.98/in stock but a table entry incorrectly said PWM “No”. The original
brown model was £28.99 at Scan with an indexed 28 October arrival; the BOM uses
the £29.99 Overclockers listing instead. Verify screwless silicone mounts fit
the printed structure and can be serviced without dismantling wet parts.

[Ferrotec's installation guidance](https://thermal.ferrotec.com/technology/thermoelectric-reference-guide/thermalref06/)
requires suitable flat/parallel interfaces, compression and moisture management;
the ceramics must not carry tray shear or structural loads. PETG locator clips
alone have no established long-term preload at hot-side temperature.

The [Malico CL-BU-40X40 / RS 489-5802](https://uk.rs-online.com/web/p/heatsink-mounting-accessories/4895802)
was investigated (indexed £3.79 inc VAT, pack basis unclear, five shown). It
hooks under a BGA package against a PCB; it is **not a verified cap–TEC–sink
clamp**. Fischer THFU clips need compatible grooved sinks and target package
thickness; THFM types generally use screw attachment. Neither is a demonstrated
stock solution for this stack. They are excluded from the ready-to-buy BOM.

Outstanding cartridge requirements: independent metal compression/load path,
supplier-supported preload, supported cap height, strain-relieved wires,
spill/condensate separation and removal without screws or greasy daily handling.
TIM stays within the dry cartridge. The cap-to-removable-tray contact method,
flatness and drag remain unresolved; thermal paste is not the sliding interface.

## Motor, controls and instrumentation

The [17HS08-1004S drawing](https://files.omc-stepperonline.com/17HS08-1004S_Full_Datasheet.pdf)
specifies a 5 mm D shaft, 20 ±1 mm projection, 16.5 mm D-cut length and 4.5 mm
flat-to-opposite-surface dimension. The 21.5 mm body and shaft projection differ
from the CAD's 28/18 mm assumptions. Check engagement, blind-tip clearance and
motor retention with the real part. The **17HS10-0704S is not a casual substitute**:
the supplier describes its shaft as round/O type. A 0.16 Nm holding-torque
specification does not prove starting torque with cold food and contact drag.

Pololu's A4988 Black Edition avoids the screw-terminal wiring on the Adafruit
A4988 breakout. It still needs initial header soldering, current-limit setup,
local VMOT bulk capacitance (supplier guidance: at least 47 µF) and installed
thermal checks. The BOM's 100 µF/50 V Panasonic part has voltage headroom for
20/24 V operation, but does not raise the driver's 35 V limit or eliminate the
need to control bus spikes. No auxiliary driver sink is prescribed before testing.

The ESP32 board is a local ESPHome candidate, not implemented firmware. Optical
position plus unique-home channels avoid treating a keyed shaft as position
feedback. Power the selected sensor modules from compatible rails and check
output levels before connecting to 3.3 V GPIOs. A supplied twenty-slot encoder
disc cannot directly represent the twelve serving positions.

For the one-wedge trial, log cold cap and sink base plus ambient and food at
centre, remote inner/outer and upper locations. Reuse a fine-probe logger if
available; inexpensive Ø6 ×30 mm DS18B20-compatible probes perturb a small wedge
and may have offset/response differences. Compare/calibrate sensors; report
warmest food temperature, not only the cap. Full-feeder sensor count and
independent overtemperature protection are still open. A presence sensor must
be tested against real fur/light/access conditions before relying on it to
inhibit motion.

## Power and harness rationale

The initial brief's **100 W PD** approach remains provisional. It needs a
verified 20 V/5 A contract, 5 A cable, suitable DC path and controlled current
conversion. The [SparkFun DEV-15801 guide](https://learn.sparkfun.com/tutorials/power-delivery-board---usb-c-qwiic-hookup-guide)
confirms the STUSB4500 board identity, NVM profiles and commissioning requirement.
Its control connector is not a power-distribution connector. Default/fallback
5 V, negotiation failure and restart must leave TECs disabled; the 5 V and 12 V
step-down rails cannot be presumed regulated during those states.

The originally considered [Adafruit HUSB238 switchable board 5991](https://www.adafruit.com/product/5991)
was US$9.95. Its [pinout guide](https://learn.adafruit.com/adafruit-usb-type-c-power-delivery-switchable-breakout/pinouts.md)
describes a **default 3 A jumper**, cut for 5 A on the relevant revision. Its
output screw terminal conflicts with strict screwless wiring; an adequately
rated soldered alternative would need verification. It is not the default BOM
choice merely because its headline says 100 W.

The Anker B121B is an exact UK charger candidate rather than an assumed continuous
100 W supply. [An indexed Amazon UK offer](https://www.amazon.co.uk/Anker-Charger-Ultra-Compact-Adapter-Display-Dark-Gray/dp/B0FL2DR4TH)
showed £39.99/in stock and qualification language referring to one hour at 25°C.
Confirm sustained output at the intended ambient; a promotional wattage or
changing discount banner is insufficient. Dedicate the PD port. Confirm the
bundle cable rating before buying the separately listed StarTech cable.

The **24 V MEAN WELL alternative is explicitly a different architecture**:
one external regulated supply replaces charger/PD board/cable, but requires a
matching 5.5/2.5 mm current-rated socket/lead and UK IEC mains lead. The selected
logic/fan buck input ranges and A4988 motor supply range include 24 V; the future
TEC current driver and protection must also do so. No direct TEC connection to
either 20 V or 24 V is intended.

No controllable low-ripple TEC current-regulator module has been qualified.
Select after curve/bench work establishes voltage compliance, channel currents,
grouping, heat dissipation, enable behaviour and sensing. Direct low-frequency
PWM at high peak current cannot be equated to the same average DC current:
Joule heating depends on mean-square current. Avoid adding twelve cheap driver
boards before confirming the necessary topology and service burden.

The harness provision uses short 18 AWG leads and WAGO lever splices, with
fused input and insulated, strain-relieved dry-side terminations. WAGO 221-412
joins two wires **electrically together**; use separate blocks for positive and
negative. Final bus/branch gauges, fuse values and connector quantities follow
the measured topology. The 20 A holder rating does not select a 20 A fuse, and
the example 5 A fuse does not provide an exact 5 A current ceiling. Small signal
connectors, fan PWM/tach interfacing, pull-ups and bus fault protection remain
part of the electronics take-off, not hidden completed work.

## Open questions and next evidence

1. Exact one-piece and twelve-piece TEC quotes, seal identity and low-current
   TARK curve data; cap restock/import total and flatness specification.
2. A readily sourced screwless compression assembly with known preload, dry
   mounting and removable-tray contact. No stock clip has yet met this need.
3. Installed sink performance with the shared fan, duct pressure losses and
   simultaneous hot-side load; confirm source rating conditions first.
4. Representative wedge trial: fill, initial/ambient temperatures, insulated
   lid, warmest food location, current/voltage, cooldown/holding and condensation.
   Record measured results separately from catalogue curves and simulations.
5. Current-regulator SKU/topology, total DC input including auxiliaries and
   conversion losses, continuous PSU rating and shutdown behaviour.
6. Actual motor shaft engagement, screwless motor mount, loaded indexing and
   home/position sensing; then choose final harness and connector counts.
7. Cleanability, service cycle and slicer-derived PETG quantity for the current
   geometry. One nominal 1 kg spool is a purchasing unit, not a whole-build mass.

These findings supersede any assumption that the thermal CAD blocks already
constitute an orderable twelve-stack assembly. They do not change owner decisions
or choose a final thermal architecture. The [BOM](../BOM.md) is the linked,
prototype-first procurement view of this evidence.
