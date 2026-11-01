# D34 simulation summary (SIMULATION (models + datasheet limits), not a hardware test)

git 3531314b2c65-dirty, ngspice 39, seed 20261026, harness lengths: CAD cut list build/plenum/harness/cutlist.csv (route .. cut .. 1.1 x cut) over harness.json

**187 checks: 169 PASS, 18 FAIL (0 non-advisory); crashed: none**

| | Check | Value | Limit | Severity | Corner / detail |
|---|---|---|---|---|---|
| PASS | `s00_integrity.mapping` Every netlist part maps to a simulation model (part_models.csv) | 0 parts | == 0 | integrity |  |
| PASS | `s00_integrity.netlist_vs_design_json` Exported KiCad netlist matches design.json pin-for-pin | 0 pins | == 0 | integrity |  |
| PASS (adv.) | `s00_integrity.harness_coverage` harness.json leads match the connectors in the design (missing connectors are skipped) | 0 items | == 0 | integrity |  - leads without a connector: []; connectors without a lead model: [] |
| PASS | `s00_integrity.lead_nets` Inter-card leads join identically named nets pin for pin | 0 pins | == 0 | integrity |  |
| PASS | `s01_hotplug.vmot_tmc2209_abs` Peak VMOT at the StepStick vs TMC2209 absolute maximum VS | 2.629 V | <= 32 | rating | case 84: C1 omitted (ESR nom), brick 2200uF/20mOhm, lead min, low-loss contacts, DPS Cin 22uF ceramic-like, TVS BV min |
| PASS (adv.) | `s01_hotplug.vmot_tmc2209_op` Peak VMOT vs TMC2209 operating maximum (transient excursion) | 2.629 V | <= 29 | rating | case 84: C1 omitted (ESR nom), brick 2200uF/20mOhm, lead min, low-loss contacts, DPS Cin 22uF ceramic-like, TVS BV min |
| PASS | `s01_hotplug.vmot_a4988_abs` Peak VMOT vs A4988 absolute maximum VBB (fallback driver) | 2.629 V | <= 35 | rating | case 84: C1 omitted (ESR nom), brick 2200uF/20mOhm, lead min, low-loss contacts, DPS Cin 22uF ceramic-like, TVS BV min |
| PASS | `s01_hotplug.buck_vin_abs` Peak 12 V / 5 V buck input (after the PTC) vs regulator absolute maximum input | 25.18 V | <= 36 | rating | case 72: C1 omitted (ESR nom), brick 470uF/50mOhm, lead min, low-loss contacts, DPS Cin 22uF ceramic-like, TVS BV min |
| PASS | `s01_hotplug.c1_vrated` Peak +24V (C1/C2) vs capacitor rated voltage | 25.45 V | <= 50 | rating | case 90: C1 omitted (ESR nom), brick 2200uF/20mOhm, lead max, DPS Cin 22uF ceramic-like, TVS BV min |
| PASS | `s01_hotplug.dps_vin` Peak voltage at the DPS5005 input terminals | 25.76 V | <= 55 | rating | case 90: C1 omitted (ESR nom), brick 2200uF/20mOhm, lead max, DPS Cin 22uF ceramic-like, TVS BV min |
| PASS | `s01_hotplug.q1_vgs` Q1 IRF4905 /VGS/ during hot-plug (zener-clamped) | 14.94 V | <= 20 | rating | case 0: electrolytic ESR min, brick 470uF/50mOhm, lead min, low-loss contacts, DPS Cin 22uF ceramic-like, TVS BV min |
| PASS | `s01_hotplug.q1_vds` Q1 /VDS/ peak during hot-plug | 1.297 V | <= 55 | rating | case 16: electrolytic ESR min, brick 2200uF/20mOhm, lead min, low-loss contacts, DPS Cin 470uF, TVS BV min |
| PASS | `s01_hotplug.q1_inrush` Q1 peak inrush current (body diode conducts before the gate is enhanced) | 146.7 A | <= 260 | rating | case 16: electrolytic ESR min, brick 2200uF/20mOhm, lead min, low-loss contacts, DPS Cin 470uF, TVS BV min |
| PASS | `s01_hotplug.tvs_ipp` P6KE30A peak current during hot-plug vs IPP | 0.01535 A | <= 14 | rating | case 86: C1 omitted (ESR nom), brick 2200uF/20mOhm, lead min, low-loss contacts, DPS Cin 100uF, TVS BV min |
| PASS | `s01_hotplug.tvs_energy` P6KE30A absorbed energy per hot-plug vs 10/1000 us rating | 3.645e-07 J | <= 0.823 | rating | case 90: C1 omitted (ESR nom), brick 2200uF/20mOhm, lead max, DPS Cin 22uF ceramic-like, TVS BV min |
| PASS | `s01_hotplug.f1_i2t` F1 7.5 A I2t of the hot-plug inrush vs pulse-derated melting I2t | 0.6192 A2s | <= 25.84 | rating | case 88: C1 omitted (ESR nom), brick 2200uF/20mOhm, lead min, low-loss contacts, DPS Cin 470uF, TVS BV min |
| PASS (adv.) | `s01_hotplug.ovp_vmot_min` Brick fault at its OVP limit 32.4 V (TVS BV min): VMOT vs TMC2209 abs max | 10.36 V | <= 32 | rating | TVS BV min |
| FAIL (adv.) | `s01_hotplug.ovp_tvs_power_min` P6KE30A dissipation while the brick sits at 32.4 V (lasts until brick OVP hiccup) | 122.9 W | <= 5 | rating | TVS BV min - TVS current 3.87 A; duration set by the brick OVP response (not published) |
| PASS (adv.) | `s01_hotplug.ovp_buck_min` Brick fault at 32.4 V (TVS BV min): buck input vs regulator abs max | 31.7 V | <= 36 | rating | TVS BV min |
| PASS (adv.) | `s01_hotplug.ovp_vmot_max` Brick fault at its OVP limit 32.4 V (TVS BV max): VMOT vs TMC2209 abs max | 10.36 V | <= 32 | rating | TVS BV max |
| FAIL (adv.) | `s01_hotplug.ovp_tvs_power_max` P6KE30A dissipation while the brick sits at 32.4 V (lasts until brick OVP hiccup) | 10.35 W | <= 5 | rating | TVS BV max - TVS current 0.32 A; duration set by the brick OVP response (not published) |
| PASS (adv.) | `s01_hotplug.ovp_buck_max` Brick fault at 32.4 V (TVS BV max): buck input vs regulator abs max | 32.32 V | <= 36 | rating | TVS BV max |
| PASS (adv.) | `s01_hotplug.tvs_fit_method` Behavioural TVS fit method vs manufacturer model (Vishay P6KE27A, 1-14 A) | 1.156 V | <= 1.5 | integrity |  - 1 A: vendor 27.83 V, fit 27.78 V; 5 A: vendor 30.42 V, fit 30.04 V; 9 A: vendor 32.99 V, fit 32.26 V; 13 A: vendor 35.56 V, fit 34.49 V |
| PASS | `s02_reverse.q1_vds` Q1 /VDS/ peak when the brick is plugged in reversed (cable ringing into Coss) | 27.86 V | <= 55 | rating |  |
| PASS | `s02_reverse.q1_vgs` Q1 /VGS/ during reversed plug-in | 0.511 V | <= 20 | rating |  |
| PASS | `s02_reverse.q1_leak` Steady reverse leakage through Q1 (model at 40 C) vs IDSS max at 150 C | 1.122e-05 A | <= 0.00025 | rating |  |
| PASS | `s02_reverse.q1_dvdt_turnon` Q1 stays off during a reversed plug-in (peak reverse current through the FET) | 0.2678 A | <= 1 | functional | lead min, low-loss, brick 470uF/50mOhm - Cgd couples the -24 V drain step onto the gate (VGS down to 0.2 V): the FET conducts for 0 us; the P6KE30A then conducts forward (0 A pk) |
| PASS | `s02_reverse.rails_reverse` Most negative board rail (+24V, VMOT, 12 V, 5 V, 3V3) during reversed plug-in | -0.764 V | >= -1 | rating | lead min, low-loss, brick 470uF/50mOhm - +24V below -1 V for 0 us |
| PASS | `s02_reverse.vmot_reverse_tmc` Most negative StepStick VMOT during reversed plug-in vs TMC2209 VS abs min -0.5 V | -0.0249 V | >= -0.5 | rating | lead min, low-loss, brick 470uF/50mOhm |
| FAIL (adv.) | `s02_reverse.aux_reverse` Most negative 12 V / 5 V regulator input (after the PTC) during reversed plug-in | -0.7377 V | >= -0.5 | rating | lead min, low-loss, brick 470uF/50mOhm - duration below -0.5 V not computed; +24V minimum -0.76 V |
| PASS (adv.) | `s02_reverse.whatif_snubber_vds` WHAT-IF (what-if: same snubber moved onto J1 (VIN_RAW to GND)): Q1 /VDS/ peak on a reversed plug-in | 29.33 V | <= 55 | rating |  |
| FAIL (adv.) | `s03_faults.f1_clear` F1 7.5 A clears a DPS-input short at the brick current limit (7-10 A) | 545.8 s | <= 5 | protection |  - 136 % of the rerated fuse: F1 is not guaranteed to open; the brick hiccup is the effective protection (README D34-3 documents F1 as a wiring fuse and the GST160A24 hiccup as the short-circuit protection) |
| PASS | `s03_faults.f1_copper` Hottest copper on the F1 path while a brick-limited short persists | 79.75 K | <= 80 | protection | pwr +24V_DPS F.Cu 2.5 mm at (32.0,20.6) carrying 10.0 A - steady 80 K (constant-current brick; hiccup duty lowers the average) |
| FAIL (adv.) | `s03_faults.f1_j1_minifit` Brick inlet J1 (Mini-Fit Jr) current during a brick-limited short | 10 A | <= 9 | protection |  - exceeds the 9 A contact rating only while the brick stays in constant current; a hiccup brick cycles it |
| PASS | `s03_faults.f1_j2_mstb` DPS input plug J2 (MSTB) current during a brick-limited short | 10 A | <= 12 | protection |  |
| PASS | `s03_faults.f2_clear` F2 RXEF110 trips on a VMOT short at the brick current limit | 2.481 s | <= 10 | protection |  - 10.0 A |
| PASS | `s03_faults.f2_copper` Hottest copper on the aux path until the PTC trips (first-order track model, tau 40 s estimated) | 17.78 K | <= 80 | protection | pwr VAUX F.Cu 0.8 mm at (41.0,30.0) carrying 10.0 A - steady-state would be 296 K |
| PASS (adv.) | `s03_faults.v12_short_copper` +12 V short: copper at the 12 V regulator current limit (continuous auto-recovery) | 74.39 K | <= 80 | protection | tec +12V F.Cu 1.5 mm at (61.2,20.0) carrying 7.2 A - TSR 2-24120N current limit 5.0-7.2 A (behavioural TRACO TSR 2-24120N (no vendor SPICE): eta 95 % at 24 V full load, st) |
| PASS | `s03_faults.v12_short_vh` +12 V short: VH-3 link current (2 pins share +12 V) | 3.6 A | <= 7 | protection |  |
| PASS | `s03_faults.fan1_short_trip` FAN1 lead short (+12 V to its return) at the 12 V regulator current limit: F1 (RXEF050) time to trip | 0.4823 s | <= 2 | protection |  - 7.2 A; TSR 2-24120N current limit 5.0-7.2 A (behavioural TRACO TSR 2-24120N (no vendor SPICE): eta 95 % at 24 V full load, st) |
| PASS | `s03_faults.fan1_short_copper` FAN1 short: hottest +12 V copper until the polyfuse trips | 0.6404 K | <= 80 | protection | tec +12V F.Cu 2.0 mm at (11.9,17.0) carrying 7.2 A |
| PASS | `s03_faults.fan2_short_trip` FAN2 lead short (+12 V to its return) at the 12 V regulator current limit: F2 (RXEF050) time to trip | 0.4823 s | <= 2 | protection |  - 7.2 A; TSR 2-24120N current limit 5.0-7.2 A (behavioural TRACO TSR 2-24120N (no vendor SPICE): eta 95 % at 24 V full load, st) |
| PASS | `s03_faults.fan2_short_fet` FAN2 short with the low-side Q4 on: MOSFET energy until the polyfuse trips | 1.312 J | <= 2 | protection |  - 7.2 A x 53 mOhm x 0.48 s |
| PASS | `s03_faults.fan2_short_copper` FAN2 short: hottest +12 V copper until the polyfuse trips | 0.6404 K | <= 80 | protection | tec +12V F.Cu 2.0 mm at (11.9,17.0) carrying 7.2 A |
| PASS | `s03_faults.fan3_short_trip` FAN3 lead short (+12 V to its return) at the 12 V regulator current limit: F3 (RXEF050) time to trip | 0.4823 s | <= 2 | protection |  - 7.2 A; TSR 2-24120N current limit 5.0-7.2 A (behavioural TRACO TSR 2-24120N (no vendor SPICE): eta 95 % at 24 V full load, st) |
| PASS | `s03_faults.fan3_short_fet` FAN3 short with the low-side Q5 on: MOSFET energy until the polyfuse trips | 1.312 J | <= 2 | protection |  - 7.2 A x 53 mOhm x 0.48 s |
| PASS | `s03_faults.fan3_short_copper` FAN3 short: hottest +12 V copper until the polyfuse trips | 0.6404 K | <= 80 | protection | tec +12V F.Cu 2.0 mm at (11.9,17.0) carrying 7.2 A |
| PASS | `s03_faults.v5_short_xh` +5 V short at the ctrl card: XH-11 current per pin (2 pins +5 V, 2 pins GND) | 1.25 A | <= 3 | protection |  - TSR 1-2450 current limit 2.0-2.5 A (behavioural TRACO TSR 1-2450 (no vendor SPICE): eta 86.5 % at 24 V full load, ri) |
| FAIL (adv.) | `s03_faults.v33_short_d1` 3V3 short (sensor header): D1 1N5819 current at the AMS1117 current limit (max 1.5 A) | 1.5 A | <= 1 | protection |  - until the AMS1117 thermal shutdown (~5 W in SOT-223); IFSM 25 A so survivable for seconds |
| PASS | `s03_faults.tec_short_relay` TEC lead short: steady relay contact current (DPS constant-current limit) | 5 A | <= 8 | protection |  - the K1 make onto a short with charged DPS output capacitance is simulated in S06 |
| PASS | `s03_faults.tec_short_copper` TEC short at DPS 5 A: hottest TEC copper (continuous) | 19.94 K | <= 80 | protection | tec TEC_P F.Cu 2.5 mm at (42.5,37.5) carrying 5.0 A |
| PASS | `s03_faults.copper_paths` Every fault current path resolves on the routed copper (pads found, no open islands) | 0 paths | == 0 | integrity |  |
| PASS | `s04_sequencing.up_3v3_overshoot` Power-up: peak ESP32 3.3 V | 3.309 V | <= 3.6 | rating |  |
| PASS | `s04_sequencing.up_3v3_monotonic` Power-up: 3.3 V rise is monotonic below 3.0 V (largest dip during the rise) | 0.0002166 V | <= 0.05 | functional |  |
| PASS | `s04_sequencing.up_order` Power-up completes: all rails within 90 % (ms after plug-in, +24/+12/+5/3V3) | 23.27 ms | <= 30 | functional |  - +24V 1.65 ms, +12V 23.27 ms, +5V 2.34 ms, 3V3 1.98 ms |
| PASS | `s04_sequencing.wifi_3v3_vdd` Wi-Fi TX bursts: minimum ESP32 3.3 V vs VDD min | 3.203 V | >= 3 | functional | task 500 mA, OKI5 x0.97, lead max, 40.0 C, AMS1117 dropout max |
| PASS | `s04_sequencing.wifi_3v3_bod` Wi-Fi TX bursts: minimum ESP32 3.3 V vs brown-out detector (default level 0, upper tolerance) | 3.203 V | >= 2.48 | functional | task 500 mA, OKI5 x0.97, lead max, 40.0 C, AMS1117 dropout max |
| PASS | `s04_sequencing.wifi_3v3_vdd_ds` Wi-Fi TX at the datasheet 379 mA peak: minimum 3.3 V vs VDD min | 3.257 V | >= 3 | functional | OKI5 x0.97, lead max, 40.0 C, dropout max |
| PASS | `s04_sequencing.down_order_0` Power-down (idle): relays lose 12 V (below 9 V) before the ESP32 3.3 V falls below 3.0 V | 85.21 ms | > 0 | functional |  - 12 V < 9 V at 48.5 ms, 3V3 < 3.0 V at 133.7 ms after unplug |
| PASS | `s04_sequencing.down_3v3_mono_0` Power-down (idle): 3.3 V decays without rebounding (largest rebound) | 8.119e-05 V | <= 0.1 | functional |  |
| PASS | `s04_sequencing.down_order_110` Power-down (pull-down 100 W DPS load): relays lose 12 V (below 9 V) before the ESP32 3.3 V falls below 3.0 V | 0.8096 ms | > 0 | functional |  - 12 V < 9 V at 1.1 ms, 3V3 < 3.0 V at 1.9 ms after unplug |
| PASS | `s04_sequencing.down_3v3_mono_110` Power-down (pull-down 100 W DPS load): 3.3 V decays without rebounding (largest rebound) | 0.0008112 V | <= 0.1 | functional |  |
| PASS | `s04_sequencing.usb_backfeed` USB-only (brick unplugged): reverse current from the DevKit through the OR-ing Schottky into the 5 V buck output | 3.339e-05 A | <= 0.001 | functional |  - pwr +5V rises to -0.02 V; ctrl 3V3 3.30 V |
| PASS | `s05_tec_interlock.topology` Safety-chain topology read from the netlists matches the modelled structure | 0 issues | == 0 | integrity |  |
| PASS | `s05_tec_interlock.k1_pickup_hot` K1 coil current with a hot coil (40 C bay + 35 K self-heating, +10 % R) vs must-operate current | 24.69 mA | >= 23.33 | functional |  - coil voltage 11.78 V (12 V rail, 2N3904 VCE(sat), loop wiring); self-heating 35 K estimated |
| PASS | `s05_tec_interlock.k2_pickup_hot` K2 coil current with a hot coil (40 C bay + 35 K self-heating, +10 % R) vs must-operate current | 24.31 mA | >= 23.33 | functional |  - coil voltage 11.60 V (12 V rail, 2N3904 VCE(sat), loop wiring); self-heating 35 K estimated |
| PASS | `s05_tec_interlock.flyback_k1` K1 coil low side peak at turn-off (clamp) vs driver VCE max | 28.08 V | <= 40 | rating |  |
| PASS | `s05_tec_interlock.flyback_k2` K2 coil low side peak at turn-off vs driver VCE max | 11.99 V | <= 40 | rating |  |
| PASS | `s05_tec_interlock.drv_ic_k1` K1 2N3904 low side peak collector current (incl. hold-up recharge on re-energise) | 0.03069 A | <= 0.2 | rating |  |
| PASS | `s05_tec_interlock.drv_ic_k2` K2 2N3904 low side peak collector current (incl. hold-up recharge on re-energise) | 0.09354 A | <= 0.2 | rating |  |
| PASS | `s05_tec_interlock.k2_pickup_time` K2 coil reaches the 70 % must-operate current after its drive turns on (C1 is charged through Q3 first), vs the firmware wait before re-arming K1 | 35.52 ms | <= 200 | functional |  - coil current at must-operate after 28.5 ms (Omron's 15 ms operate time assumes a stiff 12 V coil supply); K1 reaches it in 1.1 ms; K2 re-pick-up after its hold-up decayed: 28.1 ms |
| PASS (adv.) | `s05_tec_interlock.q3_energy` Q3 (2N3904) pulse energy while charging C1 at K2 turn-on | 16.97 mJ | <= 20 | rating |  - peak power 1.09 W (PD 625 mW continuous) |
| PASS | `s05_tec_interlock.c1_reverse` K2 hold-up capacitor: most negative voltage after the hold-up discharges (electrolytic reverse bias) | 2.924e-05 V | >= -1 | rating |  |
| PASS | `s05_tec_interlock.holdup_order_spice` Drive removed from both coils at once (SPICE, L corners): K2 coil stays above a 40 % drop-out level longer than K1 takes to fall to 10 % | 66.65 ms | >= 10 | safety |  - K1 decays to 10 % in <= 2.6 ms; K2 stays above 40 % for >= 69 ms |
| PASS | `s05_tec_interlock.le_transition` 74HC573 LE input edge (from 74HC123 half-2 Q-bar through the 1 k series resistor), 10-90 % | 3.1e-07 s | <= 7.4e-07 | rating |  |
| PASS | `s05_tec_interlock.d2_current` 74HC123 1Q-bar output current through the latch-enable clamp diode (worst 40 ohm driver) | 0.002914 A | <= 0.025 | rating |  |
| PASS | `s05_tec_interlock.thermo_open_io` Thermostat opens with K1 energised: most negative voltage at the ESP32 THERMO_OK input (25 and 40 C) | -0.2525 V | >= -0.3 | rating |  - the K1 coil current freewheels through the diode + zener and drives the thermostat return (and the THERMO_OK divider) to about -15 V for a few ms; the ESP32 input clamp conducts through the 1 k series resistor.  |
| PASS | `s05_tec_interlock.thermo_open_release` Thermostat opens with K1 energised: K1 coil current falls to 10 % (must-release) | 3.282 ms | <= 20 | safety |  - coil L 2.0 H (max assumed) |
| PASS | `s05_tec_interlock.uv_trip_lo` UV cut-off trip threshold, lowest over TL431 Vref corners (SPICE ramp) vs claim 9.37 - 0.2 V | 9.149 V | >= 9.12 | functional |  - trip 9.15-9.56 V, recover 9.94-10.39 V (claim 9.37 / 10.31 +-0.2 V); analytic nominal 9.38 / 10.31 V |
| PASS | `s05_tec_interlock.uv_trip_hi` UV cut-off trip threshold, highest over Vref corners vs claim 9.37 + 0.2 V | 9.563 V | <= 9.62 | functional |  - trip 9.15-9.56 V, recover 9.94-10.39 V (claim 9.37 / 10.31 +-0.2 V); analytic nominal 9.38 / 10.31 V |
| PASS | `s05_tec_interlock.uv_hysteresis` UV cut-off hysteresis (recover - trip), minimum over corners | 0.7946 V | >= 0.5 | functional |  |
| PASS | `s05_tec_interlock.ptc_trip_order` Slow aux-PTC trip during defrost (SPICE, 50 ms / 0.5 s / 2 s resistance ramps, relay L and TL431 Vref corners): K2 coil stays above a 40 % drop-out until K1 has fallen below 10 %, with armature-travel margin | 66.84 ms | >= 10 | safety | ramp 0.5 s, L max, Vref 2.44 - K1 drops at 12 V = 9.06 V |
| PASS | `s05_tec_interlock.uv_chatter_margin` Normal start-up load step (DPS 112 W, blower, both relays, stepper 2 A at once): lowest 12 V at the tec card vs the highest UV trip point | 11.6 V | >= 10.06 | functional | brick nominal - UV feed dropped 0 times |
| PASS | `s05_tec_interlock.contract_interlock` Firmware-contract defrost entries and exits: the K2 command changes while K1 contacts are closed | 0 of 2000 | == 0 | safety |  |
| PASS | `s05_tec_interlock.contract_rearm_race` Firmware-contract defrost entries and exits: K1 and K2 contacts in motion together | 0 of 2000 | == 0 | safety |  - 0 with the DPS output on |
| PASS | `s05_tec_interlock.contract_rearm` Firmware contract: K1 re-closes after the defrost change | 2000 instances | == 2000 | functional |  |
| PASS | `s05_tec_interlock.contract_k2_follows` Firmware contract: K2 follows DEFROST_REQ before K1 re-arms (latch transparent within the 0.8 s wait) | 2000 instances | == 2000 | functional |  |
| PASS | `s05_tec_interlock.enum_interlock_cornerA` All 2904 orderings of TEC_EN-off / DEFROST change (entry and exit) / re-arm, 0-1 s gaps, DPS on or off, corner A: the K2 command changes while K1 is closed (hardware interlock) | 0 of 2904 | == 0 | safety | corner A: earliest latch opening (LE threshold 0.94 V), slowest K1 release (L max, drop-out 10 %, 4 ms travel), fastest K2 - examples: [] |
| FAIL (adv.) | `s05_tec_interlock.enum_rearm_cornerA` Same orderings, corner A: K1 and K2 contacts in motion together (re-arm before K2 has transferred) - firmware-contract dependent | 84 of 2904 | == 0 | safety | corner A: earliest latch opening (LE threshold 0.94 V), slowest K1 release (L max, drop-out 10 %, 4 ms travel), fastest K2 - 1 with DPS on; for order off->dfr->on a re-arm gap >= 400 ms avoids it |
| PASS | `s05_tec_interlock.enum_interlock_cornerB` All 2904 orderings of TEC_EN-off / DEFROST change (entry and exit) / re-arm, 0-1 s gaps, DPS on or off, corner B: the K2 command changes while K1 is closed (hardware interlock) | 0 of 2904 | == 0 | safety | corner B: slowest K2 transfer (L max, pick-up 70 %, 7 ms travel) - examples: [] |
| FAIL (adv.) | `s05_tec_interlock.enum_rearm_cornerB` Same orderings, corner B: K1 and K2 contacts in motion together (re-arm before K2 has transferred) - firmware-contract dependent | 87 of 2904 | == 0 | safety | corner B: slowest K2 transfer (L max, pick-up 70 %, 7 ms travel) - 4 with DPS on; for order off->dfr->on a re-arm gap >= 650 ms avoids it |
| PASS | `s05_tec_interlock.enum_interlock_random` All 2904 orderings of TEC_EN-off / DEFROST change (entry and exit) / re-arm, 0-1 s gaps, DPS on or off, random: the K2 command changes while K1 is closed (hardware interlock) | 0 of 2904 | == 0 | safety | parameters sampled uniformly over the assumed ranges - examples: [] |
| FAIL (adv.) | `s05_tec_interlock.enum_rearm_random` Same orderings, random: K1 and K2 contacts in motion together (re-arm before K2 has transferred) - firmware-contract dependent | 76 of 2904 | == 0 | safety | parameters sampled uniformly over the assumed ranges - 4 with DPS on; for order off->dfr->on a re-arm gap >= 650 ms avoids it |
| PASS | `s05_tec_interlock.cutoff_after_trigger` K1 never stays closed longer than the watchdog timeout + release after the last 74HC123 trigger (stuck / random / reset / brown-out / thermostat patterns) | 0.6232 s | <= 0.6704 | safety |  |
| FAIL (adv.) | `s05_tec_interlock.cutoff_clr_retrigger` K1 held on without WDT_KICK edges, by TEC_EN rising edges while WDT_KICK is high (74HC123 CLR-trigger) | 247 instances | == 0 | functional |  - longest K1 closure after the last WDT edge: 2.24 s |
| PASS | `s05_tec_interlock.cutoff_after_en_low` K1 opens within 50 ms after TEC_EN goes low (all random patterns) | 6.2 ms | <= 50 | safety |  |
| PASS | `s05_tec_interlock.cutoff_boot` K1 never closes while the ESP32 is in reset / ROM boot (GPIOs high-impedance) | 0 instances | == 0 | safety |  |
| PASS | `s05_tec_interlock.cutoff_thermo` K1 is open within 100 ms of any thermostat opening | 0 instances | == 0 | safety |  |
| PASS | `s05_tec_interlock.random_interlock` Random / stuck / reset / thermostat pin patterns: the K2 command changes while K1 is closed | 0 of 4010 | == 0 | safety |  |
| FAIL (adv.) | `s05_tec_interlock.random_rearm` Random pin patterns: K1 and K2 contacts in motion together (fast TEC_EN/DEFROST_REQ activity) | 304 of 4010 | == 0 | safety |  |
| PASS | `s05_tec_interlock.brownout_interlock` 3V3 brown-outs (to 0-2.4 V, 5-300 ms; ESP32 resets and re-runs the contract from boot) during cooling or defrost: K2 contacts move while K1 is closed | 0 of 993 | == 0 | safety |  - default model: half 2 starts its delay at power-up (CLR-trigger rule) |
| PASS (adv.) | `s05_tec_interlock.brownout_interlock_nopulse` Sensitivity: same brown-outs if the 74HC123 half 2 gives no pulse at power-up (latch transparent at once) | 0 of 993 | == 0 | safety |  - latch content is undefined at power-up; the ESP32 resets and re-runs the contract from boot |
| PASS (adv.) | `s05_tec_interlock.pwm_hung_limitation` CPU hung but a hardware PWM/LEDC keeps toggling WDT_KICK: K1 stays closed (watchdog cannot see it) | 997 instances | == 997 | functional |  |
| PASS | `s05_tec_interlock.race_12v_mc` Defrost running (K2 energised, DPS on), then 12V lost (12 V decay tau 1 ms-2 s), random: runs where K2 starts to drop before K1 has opened | 0 fraction | <= 0 | safety |  - 0 of 2005; tau < 50 ms: 0 of 1033 fail |
| PASS | `s05_tec_interlock.race_3v3_mc` Defrost running (K2 energised, DPS on), then 3V3 lost (12 V decay tau 1 ms-2 s), random: runs where K2 starts to drop before K1 has opened | 0 fraction | <= 0 | safety |  - 0 of 2014 |
| PASS | `s05_tec_interlock.race_aux_mc` Defrost running (K2 energised, DPS on), then aux lost (12 V and 3V3) (12 V decay tau 1 ms-2 s), random: runs where K2 starts to drop before K1 has opened | 0 fraction | <= 0 | safety |  - 0 of 1981; tau < 50 ms: 0 of 988 fail |
| PASS | `s05_tec_interlock.race_12v_wc` Defrost running (K2 energised, DPS on), then 12V lost (12 V decay tau 1 ms-2 s), drop-out worst (K1 10 %, K2 40 %, C1 -20 %): runs where K2 starts to drop before K1 has opened | 0 fraction | <= 0 | safety |  - 0 of 2005; tau < 50 ms: 0 of 1033 fail |
| PASS | `s05_tec_interlock.race_3v3_wc` Defrost running (K2 energised, DPS on), then 3V3 lost (12 V decay tau 1 ms-2 s), drop-out worst (K1 10 %, K2 40 %, C1 -20 %): runs where K2 starts to drop before K1 has opened | 0 fraction | <= 0 | safety |  - 0 of 2014 |
| PASS | `s05_tec_interlock.race_aux_wc` Defrost running (K2 energised, DPS on), then aux lost (12 V and 3V3) (12 V decay tau 1 ms-2 s), drop-out worst (K1 10 %, K2 40 %, C1 -20 %): runs where K2 starts to drop before K1 has opened | 0 fraction | <= 0 | safety |  - 0 of 1981; tau < 50 ms: 0 of 988 fail |
| PASS (adv.) | `s05_tec_interlock.whatif_k1_uv` WHAT-IF (not in design): 12 V undervoltage detector (9.0 V) removes K1 drive; all supply-loss runs, drop-out worst | 0 fraction | <= 0 | safety |  - 0 of 6000 |
| PASS | `s05_tec_interlock.wdt_min_vs_kick` Shortest sampled watchdog timeout vs the firmware kick period (rising edges at >= 10 Hz -> 100 ms) | 0.302 s | > 0.1 | functional |  - tw 0.302-0.632 s; README states 0.32-0.65 s |
| PASS | `s06_dps_tec.k1_peak` Peak K1 contact current (all cases except the TEC-lead short) | 4.764 A | <= 8 | rating | K1 breaks 5.0 A pull-down current |
| PASS (adv.) | `s06_dps_tec.k1_make_short` K1 makes onto a shorted TEC lead with the DPS output capacitor charged: peak contact current | 40.97 A | <= 80 | rating |  - DPS output capacitance is assumed 470 uF (not published) |
| PASS | `s06_dps_tec.k_carry` Continuous relay contact current at pull-down (5 A) | 4.762 A | <= 8 | rating |  |
| PASS | `s06_dps_tec.j2_pin` Highest DPS-output Mini-Fit pin current (3 pins per pole share the current) | 1.587 A | <= 9 | rating |  |
| PASS | `s06_dps_tec.j3_pin` Highest TEC Mini-Fit pin current (one pin per string per pole) | 2.381 A | <= 9 | rating |  |
| PASS | `s06_dps_tec.tec_module_i` Highest TEC string (module) current in operation incl. defrost with aiding Seebeck EMF | 2.381 A | <= 4 | rating |  |
| PASS | `s06_dps_tec.k1_open_v` Voltage across the opened K1 (both poles in series) after breaking 5 A (DPS rises to CV) | 18.15 V | <= 30 | rating |  |
| PASS | `s06_dps_tec.dps_i` DPS output current at pull-down (CC setting) vs DPS5005 rating | 4.762 A | <= 5 | rating |  |
| PASS | `s06_dps_tec.dps_headroom` DPS output voltage needed at pull-down vs DPS5005 headroom (Vin >= 1.1 x Vout from ~23.7 V) | 20.93 V | <= 21.55 | functional |  |
| PASS | `s07_fans.fan1_vol` FAN1 PWM low level at the fan connector (strongest Intel-spec pull-up, 5 mA) | 0.05186 V | <= 0.8 | rating | 5.25 V / 1050 ohm, blower Cin 1.0 uF, duty 0.2 |
| PASS | `s07_fans.fan1_edges` FAN1 PWM 10-90 % rise time at 25 kHz (weak pull-up + cable) vs 10 % of the 40 us period | 0.6984 us | <= 4 | functional | 3.3 V / 10000 ohm, blower Cin 4.7 uF, duty 0.5 |
| PASS | `s07_fans.q_ic` 2N3904 peak collector current | 0.007777 A | <= 0.2 | rating | 5.25 V / 1050 ohm, blower Cin 1.0 uF, duty 0.2 |
| PASS | `s07_fans.fet_fan_peak` Q4 (IRLZ44N) FAN2 turn-on peak current (blower input capacitor through the feed polyfuse) | 5.601 A | <= 47 | rating | 3.3 V / 10000 ohm, blower Cin 4.7 uF, duty 0.5 - blower input capacitance not published (1 and 4.7 uF assumed) |
| PASS | `s07_fans.fet_fan_power` Q4 conduction loss with the blower on (35 mOhm at VGS 4 V max x1.5 hot; 3.3 V drive below spec) | 0.000756 W | <= 0.1 | rating |  - simulated average over the on/off test 0.000 W |
| PASS | `s07_fans.fet_gate_drive` Q4 gate drive: ESP32 3.3 V vs IRLZ44N VGS(th) max 2.0 V (datasheet); manufacturer model threshold 2.09 V | 2.64 V | >= 2.5 | functional |  |
| PASS | `s07_fans.fan2_flyback` FAN2 low-side node peak at turn-off (flyback clamp to the fan feed) | 7.544 V | <= 55 | rating | 5.25 V / 1050 ohm, blower Cin 1.0 uF, duty 0.2 |
| PASS | `s07_fans.tach2_backdrive` Blower tach (open collector referenced to the switched FAN2 ground) back-driving the ESP32 tach input while the low side is off | 3.298 V | <= 3.6 | rating | 5.25 V / 1050 ohm, blower Cin 1.0 uF, duty 0.2 - fan-internal tach transistor/base drive is a generic model (22 k base resistor, 2N3904-class) |
| PASS | `s08_stepper.vmot_ripple` StepStick VMOT ripple (pk-pk) with both bridges chopping in phase | 0.1529 V | <= 0.6 | functional | duty 0.5 |
| PASS | `s08_stepper.ripple_C4` C4 (22u 50V, on VMOT) ripple current vs rating | 0.04782 A rms | <= 0.1455 | rating |  |
| PASS | `s08_stepper.ripple_C8` C8 (100u 50V, on VMOT) ripple current vs rating | 0.5467 A rms | <= 0.8439 | rating |  |
| PASS | `s08_stepper.vmot_min` Lowest VMOT under chopping vs TMC2209 minimum VS 5.5 V | 11.89 V | >= 5.5 | functional |  |
| PASS | `s09_io.ow_rise` 1-Wire release to ESP32 VIH (0.75 VDD), worst bus, all probe leads 0.5 m | 0.515 us | <= 13 | functional | OWA (1 probes, lead max) |
| PASS | `s09_io.ow_vol` 1-Wire low level while a DS18B20 pulls down (vs ESP32 VIL) | 0.04175 V | <= 0.825 | functional |  |
| PASS | `s09_io.lid_closed` Lid switch closed: level at the ESP32 pin (LID_IN) | 0.003164 V | <= 0.8253 | rating |  |
| PASS | `s09_io.home_on` Home sensor active (open collector 0.2 V): level at the ESP32 pin | 0.1973 V | <= 0.8253 | rating |  |
| PASS | `s09_io.strap_io12` Strapping: GPIO12 (MTDI) at reset must read 0 for 3.3 V flash (WROOM-32E) | 0.003126 V | <= 0.8253 | functional |  |
| PASS | `s09_io.strap_io0` Strapping: GPIO0 at reset reads 1 (SPI boot) with the panel button released | 3.301 V | >= 2.476 | functional |  |
| PASS | `s09_io.esd_hbm` HBM 2 kV on a lid lead: peak current into the ESP32 pin clamp (through the 1 k series resistor) | 0.8 A | <= 1.33 | rating |  - analytic bound V/(R_gun + R_series) |
| FAIL (adv.) | `s09_io.esd_iec_2` IEC 61000-4-2 2 kV contact on a lid lead: peak current into the ESP32 pin clamp | 1.504 A | <= 1.33 | rating |  - leads are inside the enclosure; exposure is only during servicing. Add a TVS array (e.g. per-input 5 V TVS) if leads are touchable |
| FAIL (adv.) | `s09_io.esd_iec_8` IEC 61000-4-2 8 kV contact on a lid lead: peak current into the ESP32 pin clamp | 6.015 A | <= 1.33 | rating |  - leads are inside the enclosure; exposure is only during servicing. Add a TVS array (e.g. per-input 5 V TVS) if leads are touchable |
| PASS | `s09_io.thermo_ok_level` THERMO_OK (thermostats closed) at the ESP32 input vs VIH (digital read) | 2.97 V | >= 2.476 | functional |  - margin is small; reading IO36 with the ADC (threshold ~1.4 V) avoids it (see S11 Monte Carlo) |
| PASS | `s10_power_thermal.brick_steady` steady: brick input power vs the >=150 W / GST160A24 rating | 93.62 W | <= 160 | functional |  - 3.90 A at 24 V; DPS input 76 W (DPS efficiency 90 % assumed) |
| PASS | `s10_power_thermal.tj_steady` steady: hottest semiconductor junction estimate (P x RthJA + 40 C bay) | 85.42 C | <= 125 | rating | ctrl:U1 AMS1117 DevKit LDO 0.34 W |
| PASS | `s10_power_thermal.resistor_steady` steady: highest resistor dissipation | 0.07997 W | <= 0.2 | rating | tec:R1 |
| PASS | `s10_power_thermal.reg_steady_U1` steady: TSR 2-24120N output current vs rating | 1.011 A | <= 2 | rating |  |
| PASS | `s10_power_thermal.reg_steady_U2` steady: TSR 1-2450 output current vs rating | 0.2508 A | <= 1 | rating |  |
| PASS | `s10_power_thermal.ptc_hold_steady_F2_pwr_40` steady: pwr:F2 RXEF110 current vs its hold current at 40 C (nuisance-trip margin) | 0.6119 A | <= 0.89 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_steady_F2_pwr_50` steady: pwr:F2 RXEF110 current vs its hold current at 50 C (nuisance-trip margin) | 0.6119 A | <= 0.79 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_steady_F1_tec_40` steady: tec:F1 RXEF050 current vs its hold current at 40 C (nuisance-trip margin) | 0.14 A | <= 0.41 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_steady_F1_tec_50` steady: tec:F1 RXEF050 current vs its hold current at 50 C (nuisance-trip margin) | 0.14 A | <= 0.36 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_steady_F2_tec_40` steady: tec:F2 RXEF050 current vs its hold current at 40 C (nuisance-trip margin) | 0.12 A | <= 0.41 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_steady_F2_tec_50` steady: tec:F2 RXEF050 current vs its hold current at 50 C (nuisance-trip margin) | 0.12 A | <= 0.36 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_steady_F3_tec_40` steady: tec:F3 RXEF050 current vs its hold current at 40 C (nuisance-trip margin) | 3.341e-05 A | <= 0.41 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_steady_F3_tec_50` steady: tec:F3 RXEF050 current vs its hold current at 50 C (nuisance-trip margin) | 3.341e-05 A | <= 0.36 | functional |  |
| PASS | `s10_power_thermal.f1_cont_steady` steady: F1 continuous current vs 75 % of the 98 %-rerated 7.5 A | 3.288 A | <= 5.513 | functional |  |
| PASS | `s10_power_thermal.brick_pull-down` pull-down: brick input power vs the >=150 W / GST160A24 rating | 132.5 W | <= 160 | functional |  - 5.52 A at 24 V; DPS input 112 W (DPS efficiency 90 % assumed) |
| PASS | `s10_power_thermal.tj_pull-down` pull-down: hottest semiconductor junction estimate (P x RthJA + 40 C bay) | 85.42 C | <= 125 | rating | ctrl:U1 AMS1117 DevKit LDO 0.34 W |
| PASS | `s10_power_thermal.resistor_pull-down` pull-down: highest resistor dissipation | 0.07997 W | <= 0.2 | rating | tec:R1 |
| PASS | `s10_power_thermal.reg_pull-down_U1` pull-down: TSR 2-24120N output current vs rating | 1.011 A | <= 2 | rating |  |
| PASS | `s10_power_thermal.reg_pull-down_U2` pull-down: TSR 1-2450 output current vs rating | 0.2508 A | <= 1 | rating |  |
| PASS | `s10_power_thermal.ptc_hold_pull-down_F2_pwr_40` pull-down: pwr:F2 RXEF110 current vs its hold current at 40 C (nuisance-trip margin) | 0.6194 A | <= 0.89 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_pull-down_F2_pwr_50` pull-down: pwr:F2 RXEF110 current vs its hold current at 50 C (nuisance-trip margin) | 0.6194 A | <= 0.79 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_pull-down_F1_tec_40` pull-down: tec:F1 RXEF050 current vs its hold current at 40 C (nuisance-trip margin) | 0.14 A | <= 0.41 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_pull-down_F1_tec_50` pull-down: tec:F1 RXEF050 current vs its hold current at 50 C (nuisance-trip margin) | 0.14 A | <= 0.36 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_pull-down_F2_tec_40` pull-down: tec:F2 RXEF050 current vs its hold current at 40 C (nuisance-trip margin) | 0.12 A | <= 0.41 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_pull-down_F2_tec_50` pull-down: tec:F2 RXEF050 current vs its hold current at 50 C (nuisance-trip margin) | 0.12 A | <= 0.36 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_pull-down_F3_tec_40` pull-down: tec:F3 RXEF050 current vs its hold current at 40 C (nuisance-trip margin) | 3.341e-05 A | <= 0.41 | functional |  |
| PASS | `s10_power_thermal.ptc_hold_pull-down_F3_tec_50` pull-down: tec:F3 RXEF050 current vs its hold current at 50 C (nuisance-trip margin) | 3.341e-05 A | <= 0.36 | functional |  |
| PASS | `s10_power_thermal.f1_cont_pull-down` pull-down: F1 continuous current vs 75 % of the 98 %-rerated 7.5 A | 4.899 A | <= 5.513 | functional |  |
| PASS | `s10_power_thermal.copper_pulldown` Pull-down (5 A TEC, ~4.4 A DPS input): hottest routed copper segment (IPC-2152 fit, nodal current split) | 19.94 K | <= 20 | rating | tec TEC_P F.Cu 2.5 mm at (42.5,37.45), 5.00 A |
| FAIL (adv.) | `s11_montecarlo.wdt_band_lo` Watchdog timeout minimum over tolerances vs the README band lower end 0.32 s | 0.3048 s | >= 0.32 | functional |  - p0.1 0.326 s, median 0.444 s, p99.9 0.598 s |
| PASS (adv.) | `s11_montecarlo.wdt_band_hi` Watchdog timeout maximum over tolerances vs the README band upper end 0.65 s | 0.64 s | <= 0.65 | functional |  |
| PASS | `s11_montecarlo.wdt_min` Watchdog timeout minimum vs the kick period (10 Hz -> 100 ms), 2x margin | 0.3048 s | > 0.2 | functional |  |
| PASS (adv.) | `s11_montecarlo.wdt_rext` Watchdog REXT vs the largest recommended value | 4.7e+05 ohm | <= 1e+06 | rating |  |
| FAIL (adv.) | `s11_montecarlo.latch_band_lo` Latch re-open delay (74HC123 half 2) minimum vs README band 0.32 s | 0.2973 s | >= 0.32 | functional |  |
| PASS (adv.) | `s11_montecarlo.latch_band_hi` Latch re-open delay maximum vs README band 0.65 s | 0.6374 s | <= 0.65 | functional |  |
| PASS | `s11_montecarlo.latch_vs_fw_wait` Latch re-open delay maximum vs the firmware wait of 0.8 s before changing DEFROST_REQ | 0.6374 s | <= 0.8 | functional |  |
| PASS | `s11_montecarlo.interlock_margin` Latch re-opens only after K1 has opened: min(latch delay - K1 release) over tolerances | 292.9 ms | > 0 | safety |  - latch delay 297.3-637.4 ms; K1 release 1.2-6.6 ms (coil L 0.3-2.0 H assumed, clamp diode + zener) |
| PASS | `s11_montecarlo.interlock_margin_wc` Worst case (all tolerances stacked): latch re-open delay minus K1 release | 277.1 ms | > 0 | safety |  - latch 284 ms (K 0.9, R -1 %, C -10 % -10 % -5 %, leakage -10 %) vs K1 release 7.2 ms (L 2 H, coil R -10 %, drop-out 10 %, clamp 14.05 V, 4 ms travel) |
| FAIL (adv.) | `s11_montecarlo.uv_trip_mc` UV cut-off trip threshold over tolerances (TL431A Vref 2.44-2.55 V, R 1 %, BC327 VCE(sat) 0.1-0.3 V): range | 9.05 V | >= 9.12 | functional |  - trip 9.05-9.73 V, recover 9.94-10.69 V, hysteresis >= 0.86 V |
| FAIL (adv.) | `s11_montecarlo.uv_trip_mc_hi` UV cut-off trip threshold, maximum over tolerances | 9.732 V | <= 9.62 | functional |  |
| PASS | `s11_montecarlo.thermo_ok_vih_wc` THERMO_OK worst case (12 V -3 %, divider 1 %, VDD +3 %) vs ESP32 VIH = 0.75 VDD | 0.2834 V | >= 0 | functional |  - Monte Carlo: 0.00 % of 200000 below VIH; level 2.84-3.11 V; divider R1 1k / R2 330 |
| PASS | `s11_montecarlo.thermo_ok_max` THERMO_OK maximum vs ESP32 pin limit VDD + 0.3 V | -0.09781 V | <= 0.3 | rating |  |
| PASS | `s11_montecarlo.thermo_ok_in_high_40C` THERMO_OK_IN high level at IO36 through R12 47k with D9 leakage at 40 C + ESP32 input leakage vs VIH (0.75 x VDD max 3.399 V) | 2.722 V | >= 2.549 | functional |  - leakage 0.73 uA; drop 37 mV; worst divider output 2.76 V |
| FAIL (adv.) | `s11_montecarlo.thermo_ok_in_high_75C` THERMO_OK_IN high level at IO36 through R12 47k with D9 leakage at 75 C + ESP32 input leakage vs VIH (0.75 x VDD max 3.399 V) | 2.204 V | >= 2.549 | functional |  - leakage 11.70 uA; drop 555 mV; worst divider output 2.76 V; above the 40 C bay limit: shown for margin |
| PASS | `s11_montecarlo.relay_pickup_mc` Relay coil current (12 V band, ULN VCE(sat), coil R +-10 %, coil 40-75 C) vs must-operate current: fraction below | 0 fraction | <= 0 | functional |  - min 24.0 mA vs 23.3 mA; must-operate is the guaranteed maximum, typical parts pick up lower |
