# D34 hand-soldered prototype controller

**Status (2026-10-26, rev D34-2 sourcing pass): three cards, designed and machine-checked; every part
sourced (RS UK for 55 of 60 lines) and checked against a datasheet. Nothing ordered or built.**
Sourcing, verification evidence and the PCB fab choice: [D34 sourcing](d34-sourcing.md).
Labels used below:

- **[checked]**: verified by an automated test or ERC/DRC on the generated files.
- **[datasheet]**: taken from a manufacturer or distributor document.
- **[estimate]**: worked out by hand or from typical values.
- **[untested]**: needs a physical trial.

No card has been fabricated, soldered, powered or run with firmware.

Files, regeneration and pinouts: [electronics/d34/README.md](../electronics/d34/README.md).
Related: [decisions D32–D35](decisions.md), [plenum sizing → controller requirements](plenum-sizing.md),
[2026-10-25 review](review-2026-10-25.md), [JLCPCB rules](../electronics/dfm/README.md),
[TEC control](tec-control.md), [plenum CAD bays](plenum-cad.md).

## Simulation round 2026-10-26: defects and fixes

The simulation agent ran `electronics/d34/sim/run_all.sh` on source `decb7e396781`
([kb/d34-simulation.md](d34-simulation.md)). Changes made in response (new source hash `49de0a823799`; ERC/DRC clean on both rule sets, 159 tests pass):

| # | Defect (simulated) | Fix |
|---|---|---|
| 1 | Latch re-opened at 12.7 ms worst case while K1 could still be releasing (16.4 ms) | LE now from the spare 74HC123 half: delay 0.32–0.65 s, clean edge |
| 2 | On 12 V / 3.3 V loss during defrost K2 dropped before K1 in 70–88 % of runs | K2 hold-up (D5 + C1 220 µF across the coil) + K1 diode/zener fast release; ULN2003 replaced by 2N3904s (≈0.7 V more coil voltage) |
| 3 | Firmware contract gaps (re-arm race, PWM kick, TEC_EN pulsing, tach) | Contract rewritten (README): waits 0.8 s / 400 ms, DPS off until K1 re-armed, kick in software, tach only when on |
| 4 | Reversed brick: Q1 VGS −5.4 V, 31 A for 22 µs, −1.7 V rails | C9 100 nF gate–source on Q1 (sim what-if: 0.81 A, −0.84 V) |
| 5 | ULN2003 fan channels 1.6 A peaks at 25 kHz; 5–7 A on a shorted lead | FAN2/FAN3 switched DC on IRLZ44N + 1N5817 flyback; RXEF050 0.5 A PTC on each fan feed (FAN1–3) |
| 6 | +12 V copper 0.8 mm: +153 K at the TSR 2 7.2 A current limit | +12 V net class 2.0 mm on pwr and tec |
| 7 | F1 cannot clear a brick-limited short | Documented: F1 is a wiring fuse; MEAN WELL GST160A24 overload protection is **hiccup mode** at 105–150 % (datasheet) and is the real short protection |
| 8 | 74HC573 LE ramp 41 ms (limit 0.74 µs) | Fixed by #1 (no RC on LE) |
| 9 | C5 dumped 61 mA into the 74HC123 output | Fixed by #1 (C5 is now the half-2 timing capacitor; LE clamp current 3 mA via R5 1 k) |
| 10 | Watchdog 0.69–1.36 s; 1 MΩ at the noise limit | 470 k × 1 µF → 0.32–0.65 s; kick ≥ 10 Hz |
| 11 | IEC 61000-4-2 ESD on cabled GPIOs (advisory) | **Not added**: no free board area; leads are inside the enclosure, touched only in servicing. Open item |
| 12 | DPS headroom 20.9 V needed vs 21.5 V available | Series path already minimal (IRF4905 20 mΩ, 7.5 A mini-blade, two G2RL poles, 2.5 mm copper); pull-down remains voltage-limited at the highest TEC current: expect a slightly lower peak pull-down current, not a malfunction |

## Simulation round 2 (2026-10-26): fixes

The sim re-run on `49de0a823799` (178 checks, 157 pass) found two blocking defects and one 1 V margin. Fixed in source `bef910cab0df` (ERC/DRC clean on both rule sets, 164 tests pass):

| # | Defect (simulated) | Fix |
|---|---|---|
| A | A slowly falling +12 V (τ ≥ ~19–36 ms; slow aux-PTC trip with the DPS running) let K2 drop before K1 in 25–59 % of runs, because C1 tracks the rail while Q3 is on | **12 V undervoltage cut-off on the tec card:** the thermostat loop (K1's coil supply) is switched by Q6 BC327, held on by a TL431 (U1) while +12 V × 330/1330 > 2.495 V. R14 10 k from the switched loop to REF gives hysteresis: off below ≈ 9.37 V, on above ≈ 10.31 V (resistor tolerances ±1 %, TL431 ±1 % → ±~0.2 V). Entirely in the 12 V domain, so 3.3 V collapsing does not affect it. K1 therefore opens at ~9.4 V, before either relay's drop-out, while K2 is still energised. [design; re-simulation pending] |
| B | THERMO_OK reached −0.72 V at IO36 when a thermostat opens (K1 flyback through D1 + zener drags THERMO_RET to ≈ −15 V) | ctrl **R12 1 k → 47 k** (10 k in round 2 still gave −0.328 V) and **D9 BAT42** Schottky from GND to IO36 (behind R12); sim estimate ≈ −0.22 V |
| C | A reversed brick now rings VIN_RAW to −54 V against Q1's 55 V | **Off-board RC snubber, 2.2 Ω + 1 µF, across the Kycon inlet socket** (no room on the pwr card at J1; the 85 mm inlet pigtail adds only ~0.1 µH against ~1 µH of brick cable). Sim's version at J1 gave 28 V; please re-run it with the snubber at the far end of W32 |

Layout (round 2): to make the tec card routable, R8/D6 were removed (C1 directly across K2's coil), the
FAN1 driver Q1 + R3 moved into the band next to J5, D5 and D8 sit under C1 (y ≈ 21.5), Q4/Q5 moved 0.3 mm
down, and the TL431 cut-off (U1, Q6, R11, R13–R15) occupies the bottom-right corner.

R12 = 47 k check (round 3, source `c24e0a5435e3`): R12 is a plain series resistor from the tec divider (THERMO_OK, source ≈ 250 Ω)
to IO36; there is no pull-up/pull-down on the IO36 side and no filter capacitor. ESP32 input leakage
≤ 50 nA → ≤ 2.4 mV error; BAT42 reverse leakage at 3 V is sub-µA at 25 °C (≈ 0.1 V drop at 47 k only if it
reached ~2 µA when hot): THERMO_OK_IN stays ≈ 2.9–3.0 V, still read best with the ADC (threshold ~1.4 V).
RC with the ~10 pF pin/ADC capacitance ≈ 0.5 µs.

Firmware: after any reset or brown-out, run the full contract waits from boot before re-arming K1,
because the latch contents are undefined at power-up (README contract, item 4).

## Superseded layout

The first D34 layout used two boards: 94 × 52 mm and 137 × 52 mm, joined by
a 2 × 10 IDC ribbon. CAD checks on 2026-10-26 showed that neither fits a
diagonal bay, flat or vertical. The free envelope per bay is 44 mm radial ×
85 mm tangential × 51 mm high (Z29.5–Z80.5). It is limited by the hot-sink
faces, the motor-bridge post at R89 and the shell. That layout is replaced
by the three cards below. Its checks no longer apply.

## Architecture: three vertical cards

Each card is **81 × 47 × 1.6 mm**. It stands in a printed floor slot with
its plane tangential and its components facing the axis. The top long edge
takes a printed clip. Both long edges keep a 3 mm band free of pads and
courtyards [checked]. Connectors are in the top half or at the short ends.

| Card | Bay | Contents |
|---|---|---|
| **d34-ctrl** | 45° | Socketed ESP32-DevKitC-32E (antenna inside the card outline); lid, leak, home, panel UI and DPS5005 UART headers; TEC watchdog (74HC123) and defrost latch (74HC573) under the module. **Only 5 V and 3.3 V on this card** [checked]. |
| **d34-pwr** | 225° | 24 V brick entry (Mini-Fit, at the grommet end); IRF4905 reverse FET; P6KE30A; 100 µF bulk; 7.5 A mini-blade fuse to the DPS5005 input; 1.1 A PTC on the aux branch; TRACO TSR 2-24120N (12 V 2 A) and TSR 1-2450 (5 V 1 A) bucks; StepStick (VMOT = 12 V) and motor; one 1-Wire header per bus. |
| **d34-tec** | 315° | K1 cut-off relay (two poles in series) and K2 polarity-reversal relay (G2RL-2); thermostat loop; DPS5005 output in (Mini-Fit 6); TEC array out (Mini-Fit 4); 2N3904 coil drivers with K2 hold-up; IRLZ44N fan low sides with a 0.5 A polyfuse each; three fan headers. |

The DPS5005 keeps the 135° bay.

**Leads.** Each lead is a different keyed family or pin count, with the
same pin order at both ends [checked]:

- ctrl J1 XH-11 ↔ pwr J9: 5 V, 3.3 V, GND, stepper, 1-Wire.
- ctrl J2 XH-12 ↔ tec J9: GND, relay drive, thermostat sense, fan PWM/tach (tach pull-ups are on ctrl).
- pwr J3 VH-3 → tec J1: +12 V, GND, +12 V.
- pwr J2 MSTB-2 → DPS IN.
- DPS OUT → tec J2 Mini-Fit 6.
- tec J3 Mini-Fit 4 → TECs.

Leads run about 250–350 mm under the deck. GND is shared through the links;
the TEC nets are isolated from it.

**Why this split.**
- The relays, the TEC copper and the 12 V fan loads sit together on the tec
  card.
- All 24 V conversion and the stepper sit at the brick end.
- The controller never sees more than 5 V.
- The power card and the tec card come out at about 70 % courtyard
  occupancy.
- The controller is fuller, about 80 %. Its 2 × DIP logic and 15
  resistors sit under the socketed DevKit (≤ 8 mm tall [checked] against
  an ~11 mm module underside [estimate]).

### Part choices kept from the first layout

- **ESP32-DevKitC-32E (V4) in two 1×19 sockets.**
  - Rows 25.40 mm apart, pin order and EXT_5V via BAT760 [datasheet;
    footprint checked].
  - A 1N5817 (was 1N5819; lower VF) stops USB back-feeding the 5 V buck.
- **StepStick socket**, pads identical to KiCad's Pololu footprint with rows
  12.70 mm apart [checked]. Driver: **BIGTREETECH TMC2209 V1.3**, pinout
  read from BTT's own V1.3 schematic [datasheet].
  - **VMOT = +12 V** (TSR 2-24120N), not the 24 V brick: the TVS clamp can no
    longer reach the TMC2209 (32 V abs max). 17HS08-1004S: 1.0 A, 3.7 Ω,
    4.5 mH, 0.16 N·m [datasheet]. At a few rpm the coil needs ~3.7 V at 1 A,
    so torque is current-limited, not supply-limited [estimate]. BTT's manual
    quotes 12–28 V for the module (the IC is 4.75–29 V): 12 V is at BTT's
    stated minimum.
  - Pin 4 is wired straight to the ESP32 single-wire UART (TMC2209
    PDN_UART); BTT V1.3 has no series resistor, so ctrl R6 (1 k) on TX is required.
  - Pins 5 and 6 are linked to each other only. BTT V1.3: pin 5 not connected,
    pin 6 CLK with a 20 k pull-down. A4988: RESET tied to SLEEP, which the
    Pololu carrier pulls up (Pololu's recommended wiring). The old 10 k
    pull-up (R2) is gone.
  - MS1/MS2 open: internal pull-downs give UART address 0 [datasheet].
  - With an A4988, firmware must hold IO17 low and leave IO16 as an input
    so that MS3 = 0, which gives full step. The first layout's three
    jumpers were dropped for space.
- **TRACO TSR bucks** (replaced the Murata OKI-78SR, which RS does not stock).
  TSR 2-24120N: 15–36 V in, 12 V **2 A**; TSR 1-2450: 6.5–36 V in, 5 V 1 A,
  ±2 % [datasheet]. Neither publishes an absolute maximum above 36 V; the TVS
  clamp (30–33 V) is below 36 V. TSR 1 needs 22 µF/50 V at its input above
  32 V (C3 provides it). TRACO: no traces under the TSR 2N body (keep-out added).
- **G2RL-2 DC12 relays.** 8 A at 30 VDC [datasheet]. The hole grid is
  checked [checked].
- **12 V undervoltage cut-off (sim round 2):** TL431 + BC327 switch the thermostat-loop supply off below
  ~9.4 V (on above ~10.3 V), so K1 always opens first on a slowly falling 12 V rail.
- **Coil and fan drivers (2026-10-26 sim round; ULN2003 removed).** K1/K2 coils: 2N3904 low sides
  (1 k base, 47 k pull-down). FAN2/FAN3: IRLZ44N low sides, switched DC, 1N5817 flyback, and every fan
  feed (FAN1-3) through its own RXEF050 (0.5 A hold). FAN1 (NF-A12x25, 4-pin) gets PWM from an NPN open
  collector, so firmware **inverts** it.

### Changes made for space

| Was | Now | Consequence |
|---|---|---|
| 2 A mini-blade aux fuse | Littelfuse RXEF110 PTC (1.1 A hold, 2.2 A trip, 72 V) | Resettable. Aux peak is ~0.65 A at 24 V [estimate]; TRACO suggest 1.6 A slow-blow per TSR 1. |
| 3 fan-mode jumpers + 3 NPNs | FAN1 = 4-pin PWM via NPN (ground always on); FAN2 = low-side PWM + tach; FAN3 = low-side PWM, spare | FAN1 cannot be switched fully off (NF-A12x25 has a minimum speed) |
| JP4–JP6 StepStick straps | None; A4988 support is full step only (see above) | TMC2209 is the intended driver |
| 2 × 10 IDC ribbon | Two keyed XH leads + one VH lead | The controller gets 5 V via XH-11 |
| 12 V/relay LEDs | Removed | No on-board relay-state LEDs; firmware reads DEFROST_FB and THERMO_OK |
| 220 µF entry bulk | 100 µF 50 V low-ESR (8 mm) | Plus the bucks' input capacitors and C3 (22 µF). Hot-plug damping slightly weaker [untested]. |
| LEAK RC filter, logic decoupler | Removed / one 100 nF for both 74HC chips | Use firmware averaging on the leak ADC |
| Watchdog 470 k / 2.2 µF | 470 k / 1 µF (sim round; 1 M was at the Toshiba noise limit) | Timeout 0.32–0.65 s; firmware kicks at ≥ 10 Hz |

## TEC power and safety chain (unchanged in principle)

```
brick 24 V ─pwr J1─► IRF4905 ─► P6KE30A + 100 µF ─┬─ F1 7.5 A ─► pwr J2 ─► DPS5005 IN
                                                  └─ F2 PTC 1.1 A ─► VMOT ─► StepStick, 12 V buck ─► tec card, 5 V buck ─► ctrl card
DPS OUT+ ─tec J2─► K1 pole 2 ─► K1 pole 1 (series = double break) ─► K2 (DPDT reversal) ─► tec J3 TEC A/B
DPS OUT− ─tec J2─────────────────────────────────────────────────► K2
+12 V ─► tec J4 ─► RS PRO T24 NC (60 °C) ×4 in series on the hot sinks ─► K1 coil ─► Q2 2N3904 ◄─ K1_ON ◄─ 74HC123 watchdog (ctrl)
+12 V ─► D5 ─► K2 coil (C1 220 µF hold-up across it) ─► Q3 2N3904 ◄─ K2_ON ◄─ 74HC573 latch ◄─ LE ◄─ 74HC123 half 2 (ctrl)
```

- **Firmware-independent cut-off.** The K1 coil is powered through the
  series thermostats from the 12 V fan rail. An open thermostat, a lost
  12 V rail or an unplugged tec lead drops TEC power. The thermostats
  switch only about 35 mA (+9 mA divider) at 12 V. The RS PRO T24 thermostats
  are listed at 16 A 250 V AC/DC [distributor; no datasheet published].
  THERMO_OK (about 3.0 V via a 1 k / 330 Ω divider) reports the loop state.
- **Watchdog.** K1_ON needs TEC_EN high and continuous rising edges on
  WDT_KICK. 10 k/100 k pull-downs keep it off during boot, a crash or with
  the controller unplugged [checked: nets]. The tec-card 2N3904 bases have
  47 k pull-downs, so the relays are off if the XH-12 lead is unplugged [checked: nets].
  Timeout 470 k × 1 µF: 0.32–0.65 s [estimate from the sim's K spread].
- **Defrost interlock (redesigned 2026-10-26).** LE = 74HC123 half 2's Q-bar, triggered when 1Q-bar
  rises (K1 commanded off): LE goes high 0.32–0.65 s later with a CMOS edge, and a 1N5817 (D2) clamps it
  low the moment K1 is commanded on. This replaces the 47 k/1 µF ramp that crossed the LE threshold over
  41 ms and the 61 mA capacitor dump into the 74HC123 output. Latch re-open delay ≥ 0.32 s vs K1 release
  ≤ 16.4 ms [sim worst case]: ≥ 19× margin.
- **Supply-loss ordering (K1 before K2).** K2's coil is fed through D5 with C1 220 µF directly across it
  (round 2: R8/D6 removed; Q3's limited collector current charges C1 softly in ~30 ms): after +12 V or 3.3 V loss K2 stays energised for
  τ ≈ 360 Ω × 220 µF = 79 ms (release between ~23 ms at a 70 % drop-out and ~0.24 s at 5 %) [estimate].
  K1's flyback is 1N5817 + 15 V zener (clamp ~27 V, 2N3904 VCEO 40 V): its current collapses in
  ~1–2.5 ms (L 1–2 H, 33 mA, 27 V) plus ≤ 4 ms travel ≈ ≤ 6.5 ms [estimate]. K1 therefore breaks the TEC
  current in every supply-loss case; margin ≥ 3.5× at the most pessimistic K2 drop-out. Pending re-simulation.
- **Firmware rules** (see the README contract): kick WDT_KICK from the control loop (≥ 10 Hz), never from a
  hardware PWM; never pulse TEC_EN as a keep-alive; after changing DEFROST_REQ wait ≥ 400 ms before
  re-arming K1; keep the DPS output off until K1 is re-armed; read TACH2 only while FAN2 is fully on.
- **TEC isolation.** DPS OUT− goes through the DPS's low-side shunt
  [community teardown, not verified here; TEC nets are kept off GND regardless]. TEC nets never touch GND [checked].
- **DPS5005 UART.** 3.3 V logic: GND, TX, RX, 3.3 V, Modbus RTU 2400–19200 Bd
  [Riden manual; pinout from Yoctopuce/OpenDPS community sources]. Both ends
  are 3.3 V, so 5 V tolerance does not matter. 1 k series resistors on both
  lines and a 10 k idle pull-up; DPS 3.3 V left unconnected.

## Power budget [estimate]

| Load | Steady | Pull-down / peak |
|---|---:|---:|
| DPS5005 input for 4 TARK-class modules (2S2P) at ~90 % | ~48 W (2.0 A) | ~102 W (4.3 A) |
| Stepper 17HS08-1004S on the 12 V rail (IRUN ~0.7 A rms, both phases ~4 W while moving; IHOLD reduced at rest) | ~0–1 W | ~4.5 W (0.37 A at 12 V) |
| 12 V: NF-A12x25 0.14 A, blower ~0.1 A, 2 relays 67 mA, THERMO divider 9 mA (+0.3 A spare) | ~3.5 W | ~7 W |
| 12 V rail total (TSR 2-24120N, 2 A) | ~0.4 A | ~1.0 A |
| 5 V: ESP32 DevKit + logic | ~1.3 W | ~2.5 W |
| **Brick (24 V)** | **~57 W, 2.4 A** | **~120 W, 5.0 A**, inside the D32 ≥150 W brick |

| Branch / part | Current or rating | Margin / heat |
|---|---|---|
| F1 7.5 A (DPS feed) | 4.3–5.3 A | ok |
| PTC aux branch (both bucks; motor now included via the 12 V buck) | ~0.65 A peak at 24 V | ok (1.1 A hold) |
| IRF4905 at 5 A | — | 0.5–0.8 W, roughly 30–50 K rise [estimate] |
| VIN track, J1 → FET | J1 turned 180°: 2.5 mm on **both layers** for ~5 mm, 2.0 mm (both layers) for the last 1.6 mm between the TO-220 gate and source pads; the brick GND now leaves upwards and no longer crosses it | Rise ≲ 10 K at 5 A [estimate; measure] |
| Other TEC/24 V copper | 2.5 mm (TEC_B 2.5 mm on B.Cu, part of it inside the slot band) | ≤ ~12 K [estimate] |
| G2RL relays | carry 5 A at 85 °C | [datasheet] |
| Mini-Fit Jr | 9 A per pin | [datasheet] |
| JST VH | 10 A | [catalogue, unverified here] |

## Surge protection: TVS choice

The coordinator asked about a lower clamp for the regulated 24 V brick
(Vmax ≈ 25.2 V). Any TVS with Vwm ≥ 25.2 V has breakdown at about
28.5–31.9 V:

| Part | Vwm | Vbr @ 1 mA | Vc @ Ipp | Slope (Vc−Vbr,max)/Ipp | Clamp @ 1–2 A |
|---|---:|---:|---:|---:|---:|
| P6KE30A (fitted) | 25.6 V | 28.5–31.5 V | 41.4 V @ 14.5 A | ≈ 0.68 Ω | ≈ 30–32.9 V |
| SMAJ26A (SMD) | 26.0 V | 28.9–31.9 V | 42.1 V @ 9.5 A | ≈ 1.07 Ω | ≈ 30–34 V |
| 1.5KE30A | 25.6 V | 28.5–31.5 V | 41.4 V @ 36 A | ≈ 0.28 Ω | ≈ 30–32.1 V |
| P6KE27A | 23.1 V | 25.7–28.4 V | 37.5 V | — | rejected: Vwm below the brick maximum |

All values are from the datasheet min/max lines. The 1–2 A clamp is an
**estimate**: a linear slope from Vbr,max, with typical parts near 30 V.

A realistic hot-plug current into the TVS is small, because the 100 µF and
buck input capacitors absorb a 2 m lead's inductive overshoot. So the clamp
should sit near 30–33 V [estimate].

- That is below the TRACO bucks' 36 V input maximum.
- It is **at or above the TMC2209 absolute maximum of 32 V** in the worst
  case (operating maximum 29 V) [datasheet].
- No through-hole TVS with Vwm ≥ 25.2 V clamps meaningfully lower.

P6KE30A is kept (ST datasheet: VRM 26 V, VBR 28.5–31.5 V at 1 mA, Vc 41.5 V
at 14.5 A). **Resolved (2026-10-26): the StepStick VMOT now comes from the
regulated 12 V rail**, so the clamp only has to protect the DPS5005 input and the
two TRACO bucks (36 V input maximum). C8 (100 µF) now sits on +12 V at the
StepStick. Still worth scoping +24 V at hot-plug during bring-up.

## Card geometry for CAD

**Superseded by [`parts3d.json`](../electronics/d34/parts3d.json)** (2026-10-26): per-part boxes and
cylinders in card coordinates, mated plugs, cable bend zones, lead-exit directions and service volumes,
each tagged `datasheet` / `footprint` / `estimate`. Schema and conventions are inside the file and in the
[README](../electronics/d34/README.md). Summary of the harness-access pass (2026-10-26):

- **ctrl:** top row is now HOME (XH-3), SENSE (XH-4: lid reed + basin probe in one housing) and UI (XH-5),
  ~7 mm apart; DPS-UART, PWR and TEC link strips unchanged at the right end.
- **pwr:** one XH-3 per 1-Wire bus (J4 bus A, J6 bus B) with 12 mm gaps; J5, J7, J10 removed. Second row
  J3 VH-3, J2 MSTB-2, J8 VH-4 respaced. J1 Mini-Fit turned 180° (VIN on both layers).
- **tec:** the tall second-row plugs (J1 VH-3, J2 Mini-Fit 6, J4 VH-2, J3 Mini-Fit 4) are 5 mm lower,
  ~9 mm below the fan plugs; TEC copper re-laid to suit.
- Bodies: DevKit on 8.51 mm Samtec sockets, module PCB ~11 mm up, top ~16 mm; StepStick top ~22 mm
  [estimate: heatsink]; tallest mated plug Mini-Fit 23.5 mm + 8 mm bend; MSTB plug 22 mm with wires
  leaving horizontally. Solder side: leads trimmed to ≤ 2.5 mm below the board (sockets 1.6 mm).

## Open questions and risks

1. ~~TVS versus the TMC2209 absolute maximum~~ **resolved**: VMOT is +12 V.
2. ~~BTT TMC2209 V1.3 pinout~~ **resolved** from BTT's V1.3 schematic (see StepStick above).
3. **DPS5005 comm connector**: 4-pin, 3.3 V logic, GND/TX/RX/3V3; pitch 1.25 mm
   (JST-GH type) on most units, 1.0 mm reported once. The lead is made from the
   DPS comms cable after metering, so either works ([sourcing](d34-sourcing.md)).
4. **DevKit supply.** TSR 1-2450 ±2 % (≥ 4.90 V) − 1N5817 (≤ 0.39 V at 0.5 A,
   ≤ 0.45 V at 1 A) − lead ~0.03 V → ≥ 4.48 V at 0.5 A. AMS1117 dropout 1.1 V
   typ / 1.3 V max at 0.8 A → ≥ 3.18 V worst case, ~3.4 V typical [datasheet
   limits, estimate]. Was ≈ 0.1 V worse with the 1N5819.
5. **Watchdog timeout**: Toshiba TC74HC123AP (RS) gives tw ≈ 1.0 × 1 µF × 1 MΩ
   ≈ 1.0 s; ±1 µA Rx/Cx leakage can move it noticeably at 1 MΩ. Firmware should
   kick at ≥ 5 Hz.
6. ~~Decoupling~~ **resolved**: U2 and U3 each have their own 100 nF next to VCC
   (both DIPs turned so VCC faces free space).
7. **No silkscreen references** on small passives where there was no room
   (C1, C2, C4–C6 on ctrl; DZ1 on pwr). See `views/assembly.svg`.
8. **GND pads** are solid to the pours. Use a ≥ 60 W iron.
9. **Thermal.** FET, track, PTC and relay temperatures are estimates.
   Measure them in the closed case at pull-down current.
10. **Routing.** Freerouting plus a grid finisher, clean by DRC, not
    hand-optimised. The TEC copper was placed by hand.
11. **A4988 fallback.** Full step only, firmware-held MS3. TMC2209 is the
    supported driver.
12. **Fit.** Heights are now from datasheets except the DevKit header
    spacer, the BTT heatsink, the fuse-in-holder and the MSTB plug wire exit
    ([`parts3d.json`](../electronics/d34/parts3d.json) marks each shape
    `datasheet`/`footprint`/`estimate`). The slot, clip and lead routing need
    CAD and a print trial.
13. **Thermostats.** RS PRO T24A060ASF2-15 (opens 60 °C, closes 45 °C) has no
    published datasheet; size and tab width unverified. Opening point is 60 °C
    (was 65 °C KSD301): hot-sink estimate is 34 °C steady at 22 °C room
    ([plenum sizing](plenum-sizing.md)).
14. **Pre-crimped lead lengths** (300 / 225 mm) against the real routing.
