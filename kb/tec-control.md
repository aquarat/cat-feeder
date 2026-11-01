# TEC power and control: one-site trial and twelve-site scaling

**Reviewed 2026-10-24. Supplier evidence and proposed bench settings; no physical
feeder measurements or implemented control firmware.**

Context: [KB index](README.md), [decisions D19–D21](decisions.md),
[BOM](../BOM.md), [sourcing](sourcing.md),
[direct-contact thermal study](direct-contact-thermal.md) and [airflow](airflow.md).
This review advances the earlier unresolved driver/curve questions. The latest
prototype uses twelve nominal **40 × 40 × 4 mm** sites at r105 and **direct
ceramic-to-PETG contact**. No cold cap is required for this trial; wear, flatness,
contact temperature drop and indexing drag are physical questions to measure.

## Recommendation

1. **Trial one Same Sky CP60440 with one Joy-IT JT-DPS5005**, or reuse an adjustable
   low-ripple, current-limited bench supply. The CP60440 has a directly verified
   UK purchase route and matches the nominal 4 mm thickness. Start with a
   **1.2 A current ceiling and a slow 0–5 V voltage sweep**, with the hot-side fan
   running continuously. This is an exploratory envelope, not a proven cooling
   setting. Measure food as well as ceramic temperatures before buying twelve.
2. Use **adjustable constant voltage (CV), current limiting and temperature
   feedback**. Dedicated constant-current TEC electronics are unnecessary for
   this stage. The DPS5005's published ripple is a starting specification to
   check on the bench, not established low-ripple performance at this load.
3. If the thermal trial succeeds at roughly **1–1.2 A/site**, investigate
   **three TECs in series per branch, four branches in parallel (3S4P)** on one
   DPS5005. This keeps output current around 4–4.8 A. Expansion depends on
   measured branch balance, installed sink temperatures and source power.
4. Retain **20 V/5 A USB-C PD provisionally**. A **70 W TEC-output operating cap**
   is a useful initial full-array budget: about **86 W at the source** assuming
   90% conversion and 8 W auxiliaries. These assumptions require measurement.
   The 24 V supply below is a separate alternative, not an adopted change.

The central uncertainty is thermal: at low current, a warm hot side can leave
little useful cooling. A regulator that fits the electrical budget does not
establish acceptable food temperature.

## Purchasable candidates

**D** = directly read page/datasheet; **I** = search-index observation;
**?** = unverified. Prices/stock are observations on the review date, exclude
delivery, and need reconfirmation. Quantities are one initially unless stated.

| Candidate and purchase route | Evidence / observed cost | Role and limitation |
|---|---|---|
| **Same Sky CP60440**, [Anglia Live](https://www.anglia-live.com/product/617268/CP60440/SAME-SKY--CUI-DEVICES-) | **D:** £18.38 each, 50 stock, MOQ 1; VAT basis not established. **B2B-only seller.** | First direct-contact sample; nominal 40 × 40 × 4 mm. Twelve at the displayed unit price would be £220.56 before unresolved tax/delivery. |
| **Joy-IT JT-DPS5005**, [Rapid 00-0660](https://www.rapidonline.com/joy-it-jt-dps5005-programmable-bench-psu-0-50v-0-5a-250w-oled-remote-control-00-0660) | **D:** £37.33 ex VAT, about £44.80 inc; four immediate, further 417 in four working days. | One reusable manual/remote CV/CC buck module; requires an external DC source. Its 250 W label does not increase a 100 W source budget. |
| **TARK 56610-510 / CP14-127-10-L1-RT-W4.5**, [UK enquiry route](https://www.thermoelectricdevices.co.uk/product/cp1412710l1w4-5/) | **?:** exact sealed-part UK stock/price. UK listing names the base non-RT part. | Useful lower-current comparison with numeric manufacturer curves; **4.7 mm thick**, so not a drop-in for 4 mm CAD. Confirm exact RT SKU. |
| **Joy-IT JT-DPS5015**, [Rapid 00-0662](https://www.rapidonline.com/joy-it-jt-dps5015-psu-0-50v-0-15a-750w-programmable-with-remote-00-0662) | **I:** £47.13 ex VAT, 106 shown; not live-confirmed here. | Alternative 15 A driver if all-parallel wiring is justified; higher bus current and only 0.6 A nameplate margin at 14.4 A. Not the first purchase. |
| **Pololu 2815 Big MOSFET Slide Switch HP**, [manufacturer](https://www.pololu.com/product/2815), [TME distributor route](https://www.tme.eu/en/details/pololu-2815/other-modules/pololu/big-mosfet-slide-switch-hp/) | **D:** manufacturer US$8.49, backorders allowed; **?:** UK stock/price. | Default-off, GPIO-controlled disconnect upstream of TEC converter; not temperature control or a certified safety disconnect. |
| **W1209 12 V thermostat**, [Kunkune UK](https://kunkune.co.uk/shop/arduino-sensors/temperature-relay-controller-thermostat-w1209/) | **D:** £4.90 listed; 10 kΩ NTC probe, heating/cooling modes and relay. | Simple manual temperature control or a separate hot-side interlock. Use relay for low-current enable logic, not the TEC bus; DC contact ratings vary between boards. |

**Updated terminal permission (D22):** the owner explicitly permits electrical
screw terminals in the PCB proposal. The DPS and W1209 terminals can therefore
remain; the earlier requirement to replace them with soldered pigtails is
superseded. Support boards in dry, floor-supported, top-loaded bounded bays;
daily tray servicing remains tool-free. Board/bay fit is not established here.

**Integration review:** the 42 × 45 × 80 mm DPS5005 cannot fit the present
25 × 45 × 15 mm provisional converter pocket. Use it externally as bench
equipment for this trial; an installed version requires a new floor-supported,
top-loaded bay and harness layout. The 20 mm Fischer sink also exposes only
6 mm below the present deck, so it needs a separate airflow/mounting revision.
Neither component is silently substituted into the validated CAD envelopes.

### CP60440 mechanical/electrical evidence

[Manufacturer product page](https://www.sameskydevices.com/product/thermal-management/peltier-devices/single-stage-peltier-modules/cp60440)
and [CP60 datasheet](https://www.sameskydevices.com/product/resource/cp60.pdf),
revision 1.06 dated 2024-09-12:

- **40 ±0.3 × 40 ±0.3 × 4.0 ±0.1 mm**, silicone RTV seal;
  20 AWG leads, 100 ±5 mm. Nominal fit still needs tolerance/lead-exit checks.
- Imax 6 A, Vmax 15.4 V, resistance 2.17 Ω ±10%, Qmax 53 W at
  Th = 27°C, ΔT = 0. These are catalogue values, not proposed feeder settings.
- Datasheet hot-side limit **80°C** conflicts with webpage **100°C**: retain
  the conservative 80°C document limit pending clarification. Neither is an
  acceptable target for the PETG-supported assembly; proposed trips are lower.

## What the supplier curves support

`Th` = hot ceramic temperature, `Tc` = cold ceramic temperature,
`ΔT = Th − Tc`. `Qc` is **net heat pumped at the cold face**,
`Ptec = I × V`, and `Qh = Qc + Ptec` is heat rejected at the hot side.
Published net-Qc already includes internal back-conduction: do not subtract
`KΔT` again. External contact/insulation losses and food-temperature gradients
still have to be accounted for.

### CP60440: rough visual readings, not numeric calculator output

The **CP60440 plots on datasheet page 10** give the following approximate
points. Reading uncertainty is roughly **±0.5 V and ±1 W Qc**; this is not a
statistical tolerance or measured accuracy. Rounded arithmetic below must not
be interpreted as greater precision than the graph.

| Th / Tc °C | Current A | V/site, approx. | Qc/site W, approx. | Ptec/site W | Ptec ×12 W | Source W, assumed¹ |
|---|---:|---:|---:|---:|---:|---:|
| 27 / 7 | 1.2 | 3.3 | 6 | 4.0 | 48 | 61 |
| 27 / −3 | 1.2 | 3.6 | 1.5–2 | 4.3 | 52 | 66 |
| 50 / 20 | 1.2 | 4.4 | 3 | 5.3 | 63 | 78 |

¹ `12 × I × V / 0.90 + 8 W`, calculated before rounding. The warm-cold-face
examples **do not describe refrigerated food**. At Th = 50°C / ΔT = 40 K
(Tc = 10°C), the 1.2 A curve has **no positive Qc**. Raising current may restore
cooling but rapidly consumes the twelve-site power budget. Do not extrapolate
the 27°C-hot-side result to a 40–50°C installed sink, or assign TARK's results
below to this different module.

For the first row, Qh is approximately **10 W/site, 120 W across twelve sinks**,
despite only about 48 W of TEC electrical input. Keeping the hot ceramic at
27°C with ordinary ambient air would itself be demanding. These are conditional
operating points, not a self-consistent simulation of the fan/sink assembly.

### TARK comparison: retrieved numeric manufacturer operating curves

[Exact manufacturer's part/calculator](https://tark-solutions.com/products/thermoelectric-cooler-modules/peltier-cp-series/CP14-127-10-L1-RT-W4.5):
40 mm footprint, **4.700 ±0.025 mm** thickness, RTV sealed; Imax 3.9 A and
Vmax 13.9 V at Th 27°C. The calculator notes coefficients updated in 2020.
The selected curve points below hold **Tc = 0°C**, with nearest samples to
1.0 and 1.2 A; actual sample currents differ slightly.

| Th °C | Actual I A | V/site | Qc/site W | Ptec/site W | Qh/site W | Ptec ×12 W | Qh ×12 W | Source W, assumed¹ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 0.9991 | 4.551 | 3.10 | 4.55 | 7.65 | 54.6 | 91.8 | 68.6 |
| 30 | 1.2024 | 5.184 | 5.07 | 6.23 | 11.30 | 74.8 | 135.6 | 91.1 |
| 35 | 0.9973 | 4.833 | 1.74 | 4.82 | 6.56 | 57.8 | 78.7 | 72.3 |
| 35 | 1.1975 | 5.465 | 3.68 | 6.54 | 10.22 | 78.5 | 122.7 | 95.3 |
| 40 | 0.9999 | 5.131 | 0.43 | 5.13 | 5.56 | 61.6 | 66.7 | 76.4 |
| 40 | 1.2024 | 5.779 | 2.38 | 6.95 | 9.33 | 83.4 | 112.0 | **100.6** |

¹ Same assumed 90% converter efficiency and 8 W source-side auxiliary allowance.
These are **supplier model predictions**, not measured TECs or appliance results.
The lower Qh in a warmer-hot-side row partly reflects lost cooling, not an
improvement. At 35°C the positive-Qc curve starts near 0.83 A; at 40°C near
0.96 A. A nearest-point request for “0.8 A” would return a clipped endpoint,
not evidence of cooling at 0.8 A.

Selected values and the read-only calculator request are preserved in
[electronics/tark-operating-points.json](../electronics/tark-operating-points.json).
Response path: embedded Drupal JSON → `temdatasheet.temdsInput` →
`temQcgraph_json`. The preserved data are excerpts, not a complete curve or a
replacement for supplier tolerances.

**Implication:** roughly 1 A/site may fit 100 W electrically, but at a 40°C hot
side this TARK model leaves only about **0.43 W/site** net cooling at Tc 0°C.
Roughly 1.2 A/site improves capacity but reaches/exceeds the source budget at
the hotter point. Neither proves the whole-food target or the required installed
sink temperature. The new direct40 model gives about 0.21 W covered / 0.43 W
open food-path holding load at an ideal 0°C face under its assumed boundaries;
it omits whole-enclosure parasitics. Thus even the TARK 40°C/1 A point has very
little margin against the modelled open-food path alone. It is not a demonstrated
whole-feeder operating point.

## Regulator and wiring

The [JT-DPS5005 specification](https://joy-it.net/en/products/JT-DPS5005) gives
**6–55 V input, 0–50 V / 0–5 A output**, CV/CC, 42 ×45 ×80 mm and published
**100 mV peak-to-peak ripple**. It is **buck-only**: the
[manual](https://joy-it.net/files/files/Produkte/JT-DPS5005/JT-DPS5005-Manual.pdf)
requires `Vin ≥ 1.1 × Vout`. Nominal maximum output is therefore about
**18.18 V from 20 V**, or **21.82 V from 24 V**, before cable/switch losses.
The 50 V output headline is unavailable from either proposed source.

### Conditional 3S4P arrangement

```text
PD 20 V / 5 A -> input protection -> DC bus
                                      +-> 12 V buck -> fan + thermostat
                                      +->  5 V buck -> ESP32 / sensors
                                      +-> motor driver (budget during indexing)
                                      +-> default-off switch -> DPS5005 input

DPS OUT+ -> branch fuse A -> TEC1 -> TEC2 -> TEC3 -> DPS OUT-
         -> branch fuse B -> TEC4 -> TEC5 -> TEC6 -> DPS OUT-
         -> branch fuse C -> TEC7 -> TEC8 -> TEC9 -> DPS OUT-
         -> branch fuse D -> TEC10 -> TEC11 -> TEC12 -> DPS OUT-
```

Each TEC arrow is red-positive to black-negative for the verified cooling
orientation: connect the preceding TEC's black lead to the next TEC's red.
Confirm face orientation at low power. Keep series midpoints isolated from
ground and other branches; do not mix TEC types in the array.

- At 1–1.2 A per branch, total output current is 4–4.8 A. CP60440's tabulated
  points need roughly **10–13 V/string**; TARK's need **13.7–17.3 V/string**.
  The upper TARK point has modest dropout headroom on a real 20 V rail.
- Prefer **CV with a total current ceiling**, rather than trying to force one
  aggregate constant current through parallel strings. In shared CC, loss of
  one branch can drive more current into those remaining. CV reduces that
  failure mechanism, but unequal resistance, temperatures and Seebeck voltages
  still produce unequal branch currents.
- A 4.8 A total limit **is not four 1.2 A limits**. Characterize individual
  branches at warm startup and cold hold. A shorted TEC leaves only two in its
  branch and can overload them; an open TEC disables three sites. Branch fuses
  protect wiring but may not clear promptly under a current-limited supply.
  Choose fuse curves from actual fault/inrush measurements and shut down on
  detected imbalance; branch sensing/protection is an unresolved installed detail.
- Use matching modules and measured thermal conditions. One output cannot
  independently regulate all twelve food sites. If imbalance defeats useful
  common-voltage operation, **four regulators, each driving one series string**,
  are the next escalation; twelve regulators are not the default.

| Alternative | Tradeoff |
|---|---|
| All twelve parallel | About 3–6 V but **12–14.4 A** for this current envelope. Requires a larger driver (e.g. DPS5015), heavier distribution and branch checks; each site's disconnection is independent. |
| Two series × six parallel | About 6–12 V and **6–7.2 A**; exceeds DPS5005 current range. |
| Four series × three parallel | Only 3–3.6 A, but TARK points require about **18.2–23.1 V**, unsuitable for reliable 20 V buck operation; upper points also exceed 24 V/DPS dropout headroom. Some CP60440 points fit electrically, without resolving cooling. |
| Twelve in series | Tens of volts beyond either proposed source/buck capability; one open loses the array. |

Use short, polarity-labelled, dry-side harnesses with strain relief. The existing
18 AWG allowance needs voltage-drop/temperature checks for the actual loom;
do not reuse it unquestioningly for the 14.4 A all-parallel bus. Lever connectors
join conductors, so positive and negative need separate blocks. Hot-side fan
and logic power remain **upstream of TEC shutdown**.

### Source budget and separate 24 V option

The **8 W auxiliary allowance is an estimate**, including rail conversion losses,
fan, ESP32/sensors and a parked/sleeping motion system. The selected Noctua's
12 V ×0.14 A = 1.68 W nameplate maximum is only one component. Measure motor
indexing peaks and reduce TEC demand during motion rather than assuming they fit.

At 70 W TEC output, `70/0.90 + 8 = 85.8 W`, or **4.29 A at 20 V**.
This leaves nominal source headroom, but it is not a measured margin. Efficiency,
wiring drop, startup and continuous charger capability may change it. Measure
the **input rail**: DPS output watts and an output power-trip setting cannot
enforce a precise 5 A PD input ceiling. Verify 20 V/5 A negotiation and a 5 A
e-marked cable; default 5 V/fallback must inhibit the TECs. See the
[BOM power section](../BOM.md#3-power--retain-100-w-usb-c-pd-provisionally).

**Explicit alternative:** [MEAN WELL GST120A24-P1M](https://www.digikey.co.uk/en/products/detail/mean-well-usa-inc/GST120A24-P1M/7703595),
24 V/5 A/120 W, replaces the charger, PD board and USB-C cable. Existing BOM
index evidence was £40.40 inc VAT; direct stock/price unconfirmed here. It needs
a correctly rated matching 5.5/2.5 mm DC connection and UK mains lead. It improves
voltage/power headroom and removes negotiation, but does not solve insufficient
Qc or hot-side rejection. Fan and logic still require their separate bucks.

## Manual operation versus ESP32 control

| Route | What is supplied / what remains to implement |
|---|---|
| DPS5005 front panel | Stock firmware sets voltage/current, displays readings and enables output. Best first supervised characterization. No external temperature or fan feedback by itself. |
| W1209 thermostat + fixed DPS voltage/current | Manual setpoint/hysteresis for slow on/off control, using relay contacts for low-current switch enable. Autonomous cycling needs a separate output-side switch arrangement with the DPS kept powered/manually enabled; the upstream cutoff shown above with `S-INI = OFF` will not automatically restart. Separate hot-side protection and fan-failure detection still needed. |
| ESPHome **native** `modbus_controller` | Stock DPS firmware retained. Generic UART Modbus register reads/writes are available; register entities, local temperature loop, startup and faults must be configured. Not a native turnkey DPS thermostat. |
| [`syssi/esphome-dps`](https://github.com/syssi/esphome-dps) | Ready-made DPS protocol support including DPS5005/5015, but an **external component**, not ESPHome core. Still needs local thermal/interlock logic; pin a reviewed revision if used. |
| Custom ESP32 firmware | Can implement the same stock UART protocol and a dedicated state machine. More development/testing; replacement DPS firmware is unnecessary. |

[Native ESPHome register-number documentation](https://esphome.io/components/number/modbus_controller/)
and [DPS communication protocol v1.2](https://www.laskakit.cz/user/related_files/dps5005_cnc_communication__protocol_v1_2.pdf)
support setting voltage/current and output state. Key holding-register values:
`U_SET 0x0000` stores V ×100; `I_SET 0x0001` stores A ×1000;
`UOUT 0x0002`, `IOUT 0x0003` are telemetry; `ONOFF 0x0009` controls output.
Check telemetry scales against a meter on the actual firmware, particularly
IOUT where protocol examples/revisions are inconsistent. Confirm address/baud,
write acknowledgement and readback before enabling power.

Use the module's **UART-TTL** interface, cross TX/RX and reference the documented
signal ground; optional USB/Bluetooth modules are adapters, not required for an
ESP32. Verify 3.3 V compatibility on the supplied revision before connecting.
Do not power the ESP32 from the DPS communications connector's VCC. Do not add
an OUT−/system-ground bond that bypasses the converter's current-sense shunt;
check the grounding of UART, logger and oscilloscope connections together.
Prevent an externally powered UART from back-powering a disconnected DPS board;
use appropriate interface isolation/buffering if required by bench checks.

A local temperature loop can adjust **voltage slowly**, with current and source
power bounded separately. Use the worst monitored food/cold-side condition for
demand and the hottest sink for limiting; calibrate what a cold-face sensor says
about the warmest food. Bound/inhibit the integrator at limits and during faults.
Direct low-frequency PWM at high peak TEC current is not equivalent to smooth
DC at the same average current: resistive heating follows mean-square current.
Temperature hysteresis with sensible dwell is a different, slow control choice.

## Default-off, startup and fault behaviour

The following is a **proposed control specification, not installed firmware**.

- In the DPS preset, save **`S-INI = OFF`**. On every restart read/reapply
  voltage/current limits before output enable; remembered settings must not
  cause an uncontrolled restart. `I-SET` provides current limiting;
  `S-OVP`, `S-OCP`, `S-OPP` are protective **trip/shutdown** settings, not smooth
  operating-limit loops. Coordinate them with normal settings and verify trips.
- Put a **Pololu 2815** in the TEC-converter input path, physical slide switch
  OFF, with an enable pulldown. Low/disconnected ON means off; 3.3 V high turns
  it on. Its recommended range is 4.5–32 V, compatible with 20/24 V. Manufacturer
  testing gives **6 A at a 55°C device temperature** at 12 V/22°C ambient in
  still air; the 16 A headline permits 150°C and is not the design rating here.
  Measure installed temperature, transients and turn-off delay; input/output
  capacitors mean disconnect need not remove TEC current instantaneously.
- A separate **W1209 hot-sink probe in heating mode** can close its relay while
  cool and open above a selected threshold. Put those low-current contacts in
  series with ESP32 → switch ON, with the pulldown on the switch side. This
  removes TEC enable even if UART stops responding. Verify actual relay logic,
  power-loss behaviour and probe open/short response on the purchased board.
  It is an independent temperature gate, **not a fault-latching safety system**:
  a stuck-high GPIO could re-enable after the thermostat cools. One sink probe
  also does not detect every local sink failure in a twelve-site array.

| State/event | Proposed response |
|---|---|
| Power-up / PD fallback / ESP32 reset | Hardware enable low; DPS output off. Require correct source voltage/contract, valid sensors and verified settings. |
| Start cooling | Fan first; require stable tach for about **2 s**, power/read/configure DPS, then enable and ramp voltage. |
| Sink too hot | Illustrative **45°C software trip**, separate **50–55°C hardware trip**. Disable TEC; keep fan on. Set final values from actual PETG/support/module conditions. |
| Fan tach lost while commanded on | After illustrative **2 s** timeout, disable TEC and latch a fault. A running rotor does not prove airflow: blocked vents/bypass also require sink-temperature monitoring. |
| Sensor invalid/stale, UART timeout, unexpected output, source undervoltage | Disable via hardware enable; log and latch fault locally. Validate sensor freshness and reject startup/error readings. |
| Normal stop | TEC off first; fan run-on about **60 s or until sinks cool**, using measured thresholds. No powered run-on is possible after complete source loss. |
| Fault recovery | Require cleared conditions and explicit reset; do not automatically resume from a software fault. Restart through the full sequence. |

The timeouts/thresholds above are starting proposals. An ESP32 watchdog/reset
must return the enable low; a software timeout cannot act during a hard hang
with a GPIO stuck high. The separate hot-side gate covers overheating only.
If deterministic fan-loss shutdown during that failure is required, add an
independent heartbeat/tach gate and verify it. Control must run locally without
Wi-Fi/Home Assistant; a network connection is for monitoring, not the cooling
interlock.

## First bench run and evidence needed before scaling

1. Fit one CP60440 flat to its hot-side sink, using the intended dry-side TIM
   and supported retention. Place the actual PETG wedge directly on the cold
   ceramic; keep the sensing attachment out of the sliding track. Record the
   contact fixture/preload rather than treating it as a finished cartridge.
2. Run the fan continuously. Set current limit **1.2 A**, start voltage at zero,
   and increase in small steps toward **5 V maximum for this first sweep**.
   Monitor sink temperature throughout; stop on the configured thermal limit.
   Record CV versus current-limit operation. Do not jump to the module's 6 A
   catalogue maximum when the cold face fails to reach target.
3. Log actual TEC I/V, source I/V, hot and cold ceramic/sink-base temperatures,
   ambient and food at inner, outer, central and upper positions. Test chilled
   holding and pull-down separately under the intended lid/fill conditions.
   Record condensation, contact repeatability and drag after indexing.
4. Check regulator ripple/overshoot with appropriate differential/isolated
   probing, especially startup, enable, current limiting and source loss.
   Measure converter efficiency at the real low-voltage load. A nominal
   100 mVpp specification is not a measured waveform.
5. Exercise sensor disconnection, stopped fan, lost UART, brownout/reconnect,
   output disable and thermostat trip before an unattended run. Record observed
   thresholds/delays separately from the proposed settings above.
6. Only after the one-site thermal result, characterize a three-series string,
   then branch balance and all twelve sinks under the single bottom fan.
   Installed airflow and sink temperatures must be measured; free-air fan
   ratings or catalogue sink K/W do not close this calculation.

**Outstanding decisions:** warmest-food acceptance condition and intended ambient;
exact TEC purchase eligibility/selection; direct-contact wear/flatness; retained
hot-side stack and bay fit; branch protection/sensing; sensor count/placement;
actual ripple, efficiency, auxiliary peaks and installed sink temperatures;
and whether measured performance justifies twelve sites on 100 W or the explicit
24 V alternative. No electrical/control proposal here validates refrigeration.
