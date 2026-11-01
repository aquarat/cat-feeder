# Controller bring-up and system qualification plan

**Status: NOT_RUN. No assembled hardware or application firmware was tested.**
The [41 automated regression tests](../tests/README.md) pass on the independently
cleared 54-part revision. This plan follows [PCB review §3](../../kb/pcb-review.md)
and its linked component documents. It is not a claim that the external DPS,
A4988 carrier, fan, firmware or TEC fail-off stage already works.

## Record and tools

Copy [results-template.json](results-template.json) to a dated run file **in this
directory**, then fill actual board serial/revision, firmware hash (or `null`),
instrument models/calibration, purchased module identities, supply limits,
ambient, wiring, raw capture paths and observations. Leave unexecuted cases
`NOT_RUN`; use `BLOCKED` where a missing fixture/firmware prevents a trial.
Only use `PASS` against a recorded acceptance criterion with measurements.
An unpowered continuity result is not a powered functional result.

Read-only computer checks:

```sh
python3 -m unittest discover -s electronics/tests -v
python3 -m json.tool electronics/bench/results-template.json
sha256sum electronics/pcb/checksums.json electronics/pcb/feeder.kicad_sch electronics/pcb/feeder.kicad_pcb
```

For ROM identification only, if **esptool v5 is already installed**, a verified
3.3 V UART adapter is connected and manual BOOT/reset is performed:

```sh
python3 -m esptool --chip esp32 --port /dev/ttyUSB0 chip-id
```

Choose the actual serial device. This command does not test application logic.
No flashing command or application console command is provided: there is no
application firmware in this design. Scope/generator/electronic-load actions
below are manual instrument settings, not invented SCPI commands.

Use adjustable current-limited 5 V/12 V/motor supplies, DMM, scope with short
ground springs and differential/isolated measurement where needed, signal
generator with verified 0–3.3 V output, thermocouples and a suitable external
dummy load. Record current limits chosen for each fixture and actual load;
there is no qualified whole-board current limit to copy blindly.

## Connection reference

PCB pad numbers, viewed from the component side; confirm square pin 1 and
harness continuity. Colours are not a pinout standard. All PCB grounds are common.

| Interface | Pins / scope points |
|---|---|
| J1 | 1 VMOT (protected 20–24 V nominal), 2 GND |
| J2 | 1 GND, 2 regulated 5 V, 3 regulated 12 V; no onboard step-down from J1 |
| J3 fan | 1 GND, 2 12 V, 3 tach, 4 PWM collector; generic header needs adapter |
| J4/J5 probes | 1 GND, 2 shared DQ, 3 3.3 V |
| J6/J7 | 1 GND, 2 INDEX/HOME, 3 3.3 V |
| J8 | 1 GND, 2 3.3 V, 3 SDA, 4 SCL |
| J9 | 1 GND, 2 DPS RX, 3 DPS TX; **no DPS supply pin** |
| J10 | 1 GND, 2 active-high 3.3 V request only |
| J11 | 1 GND, 2 ESP TX0, 3 ESP RX0, 4 3.3 V **reference, not adapter supply input** |
| J12/J13 | 1 GPIO0 / EN respectively, 2 GND; BOOT / RESET shunts |
| J14 | 1 /EN=GND; 2/3/4 MS1/2/3=3.3 V; 5 RESET, 6 SLEEP (both GPIO23); 7 STEP/GPIO18; 8 DIR/GPIO19 |
| J15 | 1 VMOT, 2 GND, 3 2B, 4 2A, 5 1A, 6 1B, 7 VDD=3.3 V, 8 GND |
| J16/J17 | Coil 1A/1B and 2A/2B respectively; no hot-plugging |

## Ordered test matrix

### B01 — unpowered assembly and harness inspection

- Disconnect all supplies, UART adapters, carrier, DPS and external loads.
  Inspect U1/U2/U3/U4/Q1 orientation, R20/R21 population, C10 polarity, solder
  bridges and underside lead clearance against the current PCB view.
- Verify J1/J2/J3 pin order and resistance/continuity from each supply connector
  to its intended device pins. Allow capacitors to charge during resistance
  checks. Verify no persistent rail-to-ground short and no rail-to-rail short.
- Check purchased carrier component-side pinout and 15.24 mm row spacing before
  inserting it; confirm sense resistor and current-limit procedure. Record
  exact carrier/fan/probe identities. A clone is not qualified by footprint fit.
- **Pass:** actual assembly/harness agrees with connector table and schematic;
  unresolved shorts, orientation or module identity block powered trials.

### B02 — 5 V startup, EN/BOOT and bare-controller reset states

- Initially leave J1/J2.3, motor carrier, fan, sensors, DPS and TEC disconnected.
  Hold EN low with J13 and apply current-limited **5.0 V at J2.2**.
- Probe U2.1/U2.3=5 V, U2.5/U1.2/J11.4≈3.3 V, all relative to J2.1.
  Record current, startup overshoot/rise time and C2/C4 droop.
- Release reset; scope EN and 3.3 V. Inspect BOOT high, J10.2 low, J14.5/.6/.7/.8
  low, U3.1/U4.1 high, U3.2 high and U4.2 low with J9 absent.
  The EN RC is nominal 10 ms, not a promise of reset timing under every ramp.
- **Acceptance:** WROOM supply stays in its documented 3.0–3.6 V operating
  range during intended powered operation; obtain full regulator/output and
  logic-level tolerance budgets before declaring production acceptance.
  No unexplained excessive current, brownouts, undefined buffer input or
  unintended request/STEP pulse. Capture startup/slow ramp/brownout separately.

### B03 — ROM programming connection

- Use J11.1 GND, adapter TX→J11.3, adapter RX←J11.2; do not parallel adapter
  supply with J11.4/LDO. Confirm adapter logic level before connection.
- Short J12 while toggling J13, release reset, run the ROM identification
  command above, then remove BOOT shunt and reset again.
- **Pass:** repeatable ROM identification and correct strap behaviour. This
  establishes neither application startup nor any control-loop behaviour.

### B04 — ESP rail transients and installed thermal budget

- With a separately identified **test firmware** (not supplied here), exercise
  radio idle, association/reconnect, transmit bursts and sustained intended
  radio duty. Repeat with measured A4988 logic/probe/optional sensor loads.
- Scope U1.2 at C3/C4 and J2.2, log input/3.3 V current and brownout/reset
  telemetry. Test at documented installed ambient, cable length and ventilation.
  Capture minimum/maximum voltage and current pulse duration, not just averages.
- Log U2 case/board and bay ambient to thermal steady state under a documented
  criterion; case temperature is not junction temperature. Use load-step fixture
  tests to characterize the rail separately if firmware remains unavailable.
- **Limits/evidence:** AP2112's 600 mA headline is not a board thermal rating.
  Review uses θJA=184 °C/W and `(5−3.3)×I`; 300 mA gives 0.51 W/~94 °C rise
  (estimate). 150 °C absolute junction maximum is not an operating target;
  review's **125 °C junction design target** is provisional and needs a justified
  measurement/model uncertainty margin. At assumed 50 °C ambient the same model
  permits only about 240 mA. Stop before the justified thermal/voltage limits;
  do not rely on shutdown (~160 °C typical). Derive the permitted sensor load
  and radio duty from these results. Firmware-dependent trials remain blocked.

### B05 — fan PWM, reset full-speed concept and tach

- Connect the qualified fan harness to J3 and apply its regulated 12 V at J2.3.
  With MCU EN held low, scope Q1 base (pad 1), collector/J3.4 and fan tach/J3.3.
  Expect base low, released collector and full-speed request **only if the real
  fan provides the specified internal pull-up**. Test controller 5 V off while
  fan 12 V remains on; check unintended 3.3 V rail lift.
- Using qualified test firmware, or a 0–3.3 V fixture on the GPIO26 side of R8
  with the powered MCU held reset/high-Z, drive 25 kHz at 0/25/50/75/100% GPIO
  duty. Measure the **inverted** collector duty. Check at intended cable length,
  supply tolerance and startup. Do not drive a pin of an unpowered MCU.
- **Noctua evidence:** 25 kHz nominal, permitted 21–28 kHz; PWM low ≤0.8 V;
  internal pull-up up to 5.25 V/5 mA. Scope the 40 µs waveform, edge times,
  high/low levels and speed response; Noctua recommends push-pull over this
  open-collector topology because weak pull-up can distort edges. Define an
  acceptable high-level/pulse-width margin against the exact fan specification
  before sign-off; a guessed RC waveform is insufficient.
- Confirm tach tops out at 3.3 V through R6=10 kΩ and enters GPIO34 through
  R7=1 kΩ. For the documented two pulses/revolution fan, RPM=30×tach Hz.
  Record actual maximum RPM and duty response; 0% PWM behaviour is fan-specific.

### B06 — DPS ground compatibility before UART hookup

- Keep TEC output/load and UART disconnected. Record purchased DPS variant.
  Measure powered-off continuity and powered differential voltages between
  source IN−, OUT− and communications ground. Consult its actual interface data.
- **Gate:** only join J9.1 to a verified source/system-compatible UART ground.
  Do not bond DPS OUT− to board/system ground through the UART, USB or scope:
  that can bypass a low-side current shunt or output switching. If ground
  separation is required, qualify an isolated interface first. Use differential
  or properly isolated probes; never defeat scope protective earth.
- **Pass:** documented ground topology and probe/adapter connections preserve
  current sensing and shutdown. No generic “DPS5005” compatibility assumption.

### B07 — UART biases, direction and both power orders

- First use a protected interface fixture; hold MCU reset or use identified test
  firmware. With J9 absent, verify R14 holds /OE high, R20 holds U3.2 high and
  R21 holds U4.2 low. This disconnected RX-low state is not a valid UART session.
- At powered 3.3 V logic, drive external TX/J9.3 at verified 3.3 V and (only
  when fixture-qualified) 5.0 V. Verify U4.4/GPIO16 stays 3.3 V logic and J9.3
  sources about 0.33/0.50 mA into R21. Enable /OE only after inputs are valid.
  Drive U3.2/GPIO17 and scope U3.4 then J9.2 after the 1 kΩ R15.
- Test controller off/DPS on; controller on/DPS off with /OE high; normal both
  on; DPS removed while /OE enabled; controller brownout while DPS on. Measure
  J9 voltages, off-rail lift and injection/backfeed currents in each state.
  Use a current-limited dummy clamp fixture first for the enabled-TX/DPS-off
  case; connect the actual DPS only within its established pin-current limits.
- **Limits/evidence:** SN74LVC1G125 input operation allows 5.5 V and has Ioff
  at VCC=0; this does not protect an unpowered DPS from an enabled powered-board
  TX. Board TX is 3.3 V, not a 5 V translator. Ground sharing is not isolation.
  Real DPS RX VIH, clamp current and inactive-state limits are unresolved and
  must be obtained/measured before calling this case PASS. OE/bias do not detect
  DPS loss automatically. Protocol/timeout/recovery tests require future firmware.

### B08 — powered probes, CRC and freshness handling

- Connect powered probes to J4/J5 after checking individual harness pinout.
  Scope DQ at both connectors with one probe, two probes and intended maximum
  cable; check shared bus continuity, one pull-up and recovery/rise waveform.
- **Planned firmware cases, NOT EXECUTED:** enumerate and bind both ROM IDs to
  intended locations; verify ROM/scratchpad CRC, conversion-complete timing and
  resolution-dependent maximum conversion time from the exact probe data sheet.
  Unplug each probe, unplug both, interrupt a conversion, force CRC corruption
  using a fixture, hold DQ low and emulate a repeated old valid sample.
- Require explicit invalid/stale state with timestamp/age, bounded recovery and
  external TEC request inhibition per a documented fault policy. A previous
  plausible temperature, the DS18B20 power-on value, a library error sentinel or
  bad CRC must not be accepted as a fresh reading. Select timeout from actual
  conversion schedule; no invented firmware API or arbitrary food setpoint.
- Because J4/J5 share one bus, one short can disable both. Firmware must not
  misrepresent the connectors as fault-isolated independent buses.

### B09 — INDEX/HOME and optional I²C

- Use 3.3 V/open-collector fixtures at J6.2/J7.2; independently release/pull low,
  then simulate bounce, stuck-low and missing sensor. Never apply 5 V. Confirm
  GPIO32/33 and 10 kΩ bias; qualify any optical module's separate LED drive.
- At J8 scope SDA/SCL with actual module pull-ups and cable. Review estimates
  `tr≈0.8473RC`: 4.7 kΩ gives roughly 250 pF at 100 kHz or 75 pF at 400 kHz;
  use measured rise times and the selected devices' limits. Parallel module
  pull-ups change sink current. Position debounce, homing timeout, stuck-sensor
  response and I²C error recovery are planned firmware tests, not executed.

### B10 — motor reset default, stepping and power transients

- Power down before insertion or wiring. Install only a pin-verified A4988
  carrier with its current limit set for the actual motor and cooling. J14.1
  /EN is permanently low; **RESET/SLEEP provide inhibition**, not an enable GPIO.
- With MCU reset, measure J14.5/.6. Nominal 10 kΩ PCB pull-down against the
  documented external carrier 100 kΩ SLEEP pull-up gives ~0.30 V at 3.3 V.
  Verify the actual carrier remains reset/asleep and no coil current/step occurs
  at startup, reset and logic-rail loss. Record any different carrier pull-up.
- With test firmware or a properly isolated powered logic fixture, bring
  RESET/SLEEP high, wait the A4988 specified wake time (at least 1 ms), then
  apply valid STEP pulses/direction setup/hold and measure actual motion. Fixed
  MS1/2/3 high selects 1/16 stepping. Log coil currents, driver temperature,
  missed steps, connector/phase-route heating and actual required duty.
- Probe VMOT at J15.1/J15.2 and C10 using short/differential connections during
  startup, stepping, deceleration and supply interruption with actual leads.
  Motor supply is nominal 20–24 V; keep transients below **A4988's 35 V limit**
  with margin. C10's 50 V rating does not raise that limit. Verify ripple current
  and temperature against exact capacitor frequency/ambient ratings; 870 mArms
  at 100 kHz and 61 mΩ impedance are not universal motor-ripple/ESR values.
- Mechanical jam, home/index mismatch and recovery policies require firmware
  and guarded mechanical tests; they remain planned.

### B11 — ADC transfer and powered-off injection

- With logic powered, apply 0/10/20/24 V to J1 using a limited source and measure
  R19.1/C8.1 and GPIO35 (U1.7) versus ground. Expect nominal bus/11:
  20 V→1.818 V, 24 V→2.182 V. Record actual resistor tolerance and offset.
- Apply bounded bus steps; nominal Thevenin resistance ~9.09 kΩ and 100 nF
  yield ~0.91 ms RC. Measure pickup at the MCU, not only beside C8 near the motor.
  Calibrated ADC readings/attenuation require future test firmware.
- With the carrier initially absent, characterize VMOT-on/logic-off under
  current limiting. Measure U1.7 injection and 3.3 V rail lift before repeating
  with actual peripherals. R18 limits current but is not an isolation or surge
  clamp. Establish ESP32 off-state injection acceptance from manufacturer
  guidance; do not infer acceptance from a powered ADC reading below 3.3 V.

### B12 — external TEC fail-off, independent of MCU intent

- **Blocked until the external stage and its own input bias/interlocks exist.**
  Begin with a current-limited dummy load; no TEC power flows through this PCB.
  J10.2 is only a logic request and is not a documented DPS enable connection.
- Demonstrate load de-energization on J10 unplug, controller reset/power loss,
  external control supply loss, external watchdog timeout and independent
  overtemperature/fan-loss interlock. Inject stuck-high J10 and frozen firmware:
  independent interlocks must still remove load power. Measure residual current
  and shutdown time at the load, including the actual external switching stage.
- Select trip limits, permitted residual power and fault response time from a
  documented thermal/electrical hazard budget before declaring PASS. Do not
  substitute UART “output off” acknowledgement for measured load isolation.
  The PCB's board-side R10 cannot bias a disconnected external input.

### B13 — integrated firmware fault/recovery matrix

- **Planned, NOT EXECUTED; no application firmware exists.** Cover sensor CRC,
  disconnect/stale timestamps, fan tach loss, motor stall/home timeout, DPS
  timeout/malformed replies/reboot, ESP reset/brownout, watchdog expiry, loss of
  network and power restoration. Log state transitions, alarm, requested and
  measured external power, and whether restart requires operator action.
- Fault policies, timing budgets, actual external safeguards and firmware build
  identity are required before execution. Never turn a mocked expected state
  into a passed application test. Thermal/food qualification is separate and
  no food-safe setpoint is established by this matrix.

## Evidence boundaries and references

The [independent review](../../kb/pcb-review.md#public-references-actually-consulted)
records the Espressif WROOM data sheet v2.1, TI SCES223U SN74LVC1G125,
Diodes AP2112 DS39724 Rev. 2-2, Pololu 1182 carrier documents, exact Panasonic
EEUFR1H101B and Noctua PWM paper. Use those manufacturer limits and exact
purchased-component documents, not a similarly named clone. Probe conversion,
A4988 wake/STEP timings and instrument-specific current limits must be checked
against the hardware used for the run.

Design review and automated checks leave the same real interfaces unresolved:
LDO installed thermal/transient budget; fan edge quality; DPS grounds, thresholds
and opposite power order; real carrier current/heat/VMOT spikes; probe fault
handling; external fail-off and application firmware. Each remains `NOT_RUN`
until evidence is attached.
