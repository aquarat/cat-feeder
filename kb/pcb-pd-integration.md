# Move the USB-C PD board onto the controller PCB

2026-10-24 — **component-level integration proposal, not an assembled or tested
board.** Linked from the [owned PD deliverable](../electronics/revb/pd/README.md).
Parent context: [BOM](../BOM.md), [sourcing](sourcing.md), [decisions](decisions.md),
[existing controller](pcb-design.md). The parent revision owns the main KB index.

## Decision and feasibility

Use **STUSB4500QTR**, retaining the selected **SparkFun DEV-15801** design lineage.
The BOM's selected board is the Pi Hut SparkFun Power Delivery Board USB-C Qwiic;
`kb/sourcing.md` identifies that same STUSB4500 board. The actual SparkFun Eagle
source confirms **STL9P3LLH6** as its switch, not the STL6P3LLH6 used in ST's older
evaluation schematic. Public JLC stock supports the ST controller and the actual
SparkFun FET; there is no stock-driven reason to change PD-controller family.

**A 20 V/5 A contract can gate the power path without an MCU.** Program:

| NVM setting | Target | Reason |
|---|---|---|
| `SNK_PDO_NUMB` | 2 | Only 5 V fallback and 20 V high-power profile enabled |
| PDO1 | 5 V / 0.5 A | Mandatory first PDO; no heavy load allowed on fallback |
| PDO2 | 20 V / 5 A | ST's autonomous match requires equal voltage and source current ≥ sink current |
| PDO3 | disabled; also store 20 V / 5 A | Avoid a latent lower-voltage high-power profile |
| `POWER_ONLY_ABOVE_5V` | 1 | Assert `VBUS_EN_SNK` only after PDO2/3 explicit contract |
| `PWR_OK_CFG` | 2 | `POWER_OK2` identifies PDO2, but is only a test/status signal here |
| `REQ_SRC_CURRENT` | 0 | Request the configured sink operating current |
| `USB_COMM_CAPABLE`, `SNK_UNCONS_POWER` | 0, 0 | Power-only sink; no unconstrained source |
| `GPIO_CFG` | 1 | Preserve error-recovery indication configuration |
| PDO2 under/over-voltage tolerance | 10% / 5% | Nominal 18–21 V monitoring window; threshold tolerances still apply |
| Discharge | enabled; time fields 9 / 12 | Factory 756 ms / 288 ms typical; 630 ms / 240 ms minima |

With a 5 V-only, 20 V/3 A or 20 V/4.3 A source, the connector can remain at 5 V
and STUSB4500 stays alive, but **`PD_20V` stays off**. A 100 W source and a 5 A
e-marked cable are necessary. The source must check the cable and advertise a
5 A capability; a cable appearance or “100 W” printed on a charger is not a
measured contract. This IC does not measure load current or implement a 5 A
electronic current limiter.

Do not use `POWER_OK2` alone as the load enable: ST states that POWER_OK flags
can remain asserted at detach until a new attachment/reset. `VBUS_EN_SNK` is the
disconnect-aware gate output. Do not program a 15 V PDO2 plus 20 V PDO3 and then
assume `POWER_ONLY_ABOVE_5V` means “20 V only”. It accepts either high PDO.

**This behavior depends on verified NVM.** Factory/default NVM can enable a 5 V
path; the proposal does not claim a hardware fuse that recognizes 20 V/5 A under
arbitrary corrupted programming. Firmware is unnecessary for normal negotiation,
but must not overwrite PDO/policy registers with conflicting settings.

## Concrete circuit and actual pin map

The reusable source is [`circuit.py`](../electronics/revb/pd/circuit.py), with
generated [`circuit.json`](../electronics/revb/pd/circuit.json). Every populated
part has an exact MPN, LCSC code and footprint. `None` is deliberate NC. Ref
numbers 201 onward are a proposed namespace; parent integration may renumber.

| STUSB4500 QFN pin | Function | Net / connection |
|---|---|---|
| 1, 2 | CC1DB, CC1 | `PD_CC1`, receptacle A5 |
| 3 | NC | NC, not GND |
| 4, 5 | CC2, CC2DB | `PD_CC2`, receptacle B5 |
| 6 | RESET, active high | `PD_RESET`, 100 kΩ to GND and test pad |
| 7, 8 | SCL, SDA | PD-side isolated bus, pulled up to `PD_3V3` |
| 9 | DISCH | `PD_DISCH_OUT`, 1 kΩ/1 W from switched output |
| 10, 25 | GND, exposed pad | GND; pad 25 is real electrical ground |
| 11 | ATTACH | NC |
| 12, 13 | ADDR0, ADDR1 | GND → address 0x28 |
| 14, 15 | POWER_OK3, GPIO | NC |
| 16 | VBUS_EN_SNK, HV open drain | `PD_EN_SNK_N`, through 22 kΩ to common gates |
| 17 | A_B_SIDE | NC |
| 18 | VBUS_VS_DISCH | `PD_VBUS_SENSE`, through 1 kΩ/1 W to raw VBUS |
| 19 | ALERT | NC; poll status over I²C |
| 20 | POWER_OK2 | `PD_PDO2_N` test pad, no 20 V pull-up |
| 21 | VREG_1V2 | 1 µF to GND, no external loads |
| 22 | VSYS | GND in the selected implementation |
| 23 | VREG_2V7 | 1 µF to GND, no external loads |
| 24 | VDD | Raw connector VBUS with local 1 µF/50 V |

The dead-battery CC connections supply internal Rd behavior; do not add separate
5.1 kΩ resistors that parallel the IC's internal terminations. ESDA25W pin 1 is
CC1 cathode, pin 2 CC2 cathode, pin 3 common anode/GND. This is the ST reference
ESD arrangement. Its 24 V standoff does **not** clamp CC to a low logic voltage;
the STUSB4500 provides its own short-to-VBUS protection up to 22 V.

### Receptacle

Use **GCT USB4105-GF-A-060**, rated **5 A collectively across VBUS contacts**,
6.25 A collectively across ground contacts. Wire **A4, A9, B4, B9** to raw VBUS
and **A1, A12, B1, B12** to GND, plus all shell tabs to GND. CC1/CC2 are distinct.
Data and SBU contacts remain NC. KiCad's 16-contact footprint has overlapping
pads for the internally paired power contacts: retain all logical pad numbers,
give each pair the same net, and do not infer that the 12 physical solder tails
mean only two current-carrying contacts.

The retrieved 2021 mechanical drawing lists 20 V; the later GCT product
specification **A3, 2023-02-27**, lists **48 V / 240 W**, matching JLC's current
catalogue. Both are retained; use the later specification for the voltage rating
and the drawing for the footprint. The -060 shell stakes are 0.60 mm nominal;
manufacturer drawing has alternate -120/blank stake lengths, not interchangeable
mechanical heights. Mixed SMT contacts and through-hole shell stakes require
assembler process confirmation despite JLC's `smtWeld` classification.

### External gated high-current path

Use ST DS12499 **Figure 10 common-source back-to-back PMOS topology**, fitted with
two **STL9P3LLH6** parts (SparkFun's actual FET). Q201 drain is raw VBUS; its source
joins Q202 source at `PD_FET_SOURCE`; Q202 drain is `PD_20V`. Both gates join.
The 100 kΩ gate-to-common-source resistor defaults them off. STUSB4500 pulls the
gates through 22 kΩ. A series 100 Ω + 100 nF/50 V network connects the common
gate to switched output, preserving the reference's slew-control arrangement.

Unlike SparkFun's single-FET board, the pair blocks reverse body-diode discharge
when off. It is **not an ideal-diode controller while on**. Motor regeneration,
externally imposed output voltage, output fault protection and short-circuit
current control remain system-level responsibilities.

Physical FET pins: **1/2/3 source, 4 gate, 5/6/7/8 drain**. The reference continuous
drain copper land is represented by three touching pad-5 rectangles, as in the
SparkFun Eagle package; JSON explicitly records aliases 6/7/8 → 5. Do not substitute
a generic 3-pin MOSFET symbol without mapping all source and drain lands.

The required PowerFLAT 3.3×3.3 footprint is **absent from the inspected KiCad 9
stock library**. `PD.pretty/ST_PowerFLAT_3.3x3.3_SparkFun.kicad_mod` supplies it,
with copper dimensions from SparkFun and ST's recommended land drawing. Four
paste apertures replace the large central paste opening (~65% central coverage);
this proposed paste change is still subject to assembler review. CC-BY-SA-4.0
SparkFun attribution/license is retained in `reference/sparkfun-LICENSE.md`.

### Decoupling, ratings and discharge

- All VBUS, output and gate-network capacitors in this block are **50 V**.
  SparkFun Eagle C6's library suffix is 16 V although its net is raw VBUS; this
  proposal deliberately corrects that source-data rating instead of copying it.
- VREG_1V2 and VREG_2V7 each get 1 µF. ST requires 0.5–10 µF effective; verify
  bias/tolerance/temperature for the selected MLCCs. The small 50 V parts are not
  assumed to retain their entire nominal capacitance at 20 V.
- Raw input nominal capacitance is 2 µF (ST supply and local LDO input), plus
  parasitics/TVS. Bulk load capacitance belongs after the switch. Keep actual
  Type-C attach capacitance within the applicable sink requirements.
- Both discharge paths use **1 kΩ, 1 W, 2512**: 22 mA and 0.484 W initially at
  22 V (22.2 mA/0.489 W with −1% R), below the ST pin limits of 50 mA input-side
  and 500 mA output-side. This avoids relying on a 0603 resistor's unspecified
  repetitive pulse overload.
- **≤150 µF total effective switched-output capacitance**, including wiring and
  external modules, is the provisional integration limit. At 22 V, 1.01 kΩ and
  150 µF, ideal RC discharge to 0.6 V takes **0.546 s**, below the default minimum
  discharge interval of 0.630 s. ST internal resistance and residual sourcing
  are not included: measure actual decay. To 5 V takes 0.224 s versus 0.240 s
  minimum transition interval; therefore do not add capacitance without review.
  Normal firmware must not renegotiate down under active loads.
  This RC estimate assumes the IC's discharge switch remains active throughout:
  raw-VBUS collapse also removes its VDD supply in this VBUS-powered reference
  arrangement. Confirm discharge completion during actual unplug, not only a
  simulated resistor connected continuously to ground.
- ESDA25P35-1U1M TVSs protect raw VBUS and output per ST reference. Pin 1 cathode,
  pin 2 anode. Their 22 V standoff/24.6 V typical breakdown is not proof of a
  <28 V clamp at all surge currents: published ESD/35 A surge clamps can exceed
  controller absolute maximums. Qualification and layout inductance matter.

## 3.3 V I²C isolation and power-off behavior

The selected implementation follows ST's **VSYS grounded, VDD from raw VBUS**
reference. A separate **TPS70933DBVR** makes `PD_3V3` from raw VBUS solely for bus
bias; a **TCA9517ADGKR** separates the PD and host power domains. This is signal
power-off isolation, **not galvanic isolation**. There is no diode from either ST
internal VREG into the ESP32 rail, unlike the SparkFun board's BAT60A connection.

TPS709 pin map: **1 IN/raw VBUS, 2 GND, 3 EN floating, 4 NC, 5 OUT/PD_3V3**.
Floating EN is explicitly permitted by TI and uses its internal enable bias;
**never connect this EN to 20 V** (6.5 V operating limit). Input has 1 µF/50 V;
output has 10 µF/25 V plus a local buffer bypass. TPS709 needs effective output
capacitance per its datasheet; the chosen 10 µF gives headroom at 3.3 V, but
manufacturer bias data remains a qualification item.

TCA9517 pins: **1 VCCA/PD_3V3, 2 SCLA/PD_SCL, 3 SDAA/PD_SDA, 4 GND,
5 EN/host +3V3, 6 SDAB/HOST_SDA, 7 SCLB/HOST_SCL, 8 VCCB/host +3V3**.
Both supply pins have local 100 nF; each bus has its own 4.7 kΩ pull-ups.

**Orientation is critical:** STUSB4500 requires VIL ≤0.35 V. TCA's **A-side**
VOL ≤0.2 V satisfies that; B-side VOL can be **0.6 V**, so ST must not be put on
the B-side. ESP32-side inputs must recognize 0.6 V as LOW, and its driven LOW
must satisfy TCA B's ≤0.45 V input criterion. Ordinary ESP32 3.3 V GPIO at these
pull-up currents is the intended interface; verify chosen GPIO configuration.
Do not directly cascade this B side with another offset-buffer B side.

| Power state | Intended behavior |
|---|---|
| USB present, host off | ST negotiates autonomously; raw-bias LDO powered; TCA host side high-impedance with VCCB absent; no pull-ups into dead ESP32 rail |
| Host powered, USB absent | PD rail off; TCA isolates A side; ST unpowered SCL/SDA pulldowns cannot hold the host bus low |
| Both powered | 3.3 V bus on each side; standard open-drain I²C |
| Both off | No powered pull-ups |
| USB falling through brownout | Brief bus interruption possible while ST and LDO thresholds cross; host driver needs timeout/recovery, not a claimed glitch-free hot swap |

TI states high-impedance I²C pins with either supply absent. This is better
defined than assuming the ST's unpowered inputs are transparent: ST explicitly
warns SCL/SDA pull down when neither VDD nor VSYS exists. Independent host power
does not power the ST in this design. Keep direct PD-side test wires disconnected
in normal operation so they do not bypass the isolator.

Start at **100 kHz**, ≤200 pF per side (4.7 kΩ nominal gives ~0.80 µs rise time).
400 kHz requires tighter capacitance (~75 pF at nominal R for 300 ns) and a
timing check. The parent must account for any existing pull-ups in parallel.

## Exact parts and public JLC evidence

Snapshot queried 2026-10-24 16:17–16:26 UTC. Values below are the public hydration
field `overseasStockCount`; `canPresaleNumber`, purchase minimum, assembly mode,
price and page SHA-256 are preserved separately in
[`stock-evidence.json`](../electronics/revb/pd/stock-evidence.json). Counts are
**not reserved**, not a promise of immediate quoted assembly availability.

| MPN | LCSC/JLC code | Listed stock | Used for |
|---|---|---:|---|
| STUSB4500QTR | C2678061 | 5,024 | QFN24 PD controller |
| STL9P3LLH6 | C2969828 | 852 | 2 × low-loss PMOS |
| USB4105-GF-A-060 | C3025063 | 850 | 5 A USB-C connector |
| ESDA25W | C2935152 | 3,633 | CC ESD array |
| ESDA25P35-1U1M | C1974707 | 9,179 | 2 × VBUS TVS |
| TPS70933DBVR | C89347 | 16,814 | Raw-side 3.3 V bias LDO |
| TCA9517ADGKR | C201698 | 17,355 | Power-off isolated I²C buffer |
| 25121WF1001T4E | C54315 | 70,086 | 1 kΩ 1 W discharge resistors |
| 0603WAF1003T5E | C25803 | 18,225,360 | 100 kΩ, 0603 |
| 0603WAF2202T5E | C31850 | 3,208,990 | 22 kΩ, 0603 |
| 0603WAF1000T5E | C22775 | 10,672,050 | 100 Ω, 0603 |
| 0603WAF4701T5E | C23162 | 17,145,360 | 4.7 kΩ pull-ups |
| CL10A105KB8NNNC | C15849 | 13,774,226 | 1 µF 50 V X5R, 0603 |
| CC0603KRX7R9BB104 | C14663 | 44,140,203 | 100 nF 50 V X7R, 0603 |
| CL21A106KAYNNNE | C15850 | 9,138,642 | 10 µF 25 V X5R, 0805, only PD 3.3 V rail |

Each public page is `https://jlcpcb.com/partdetail/<code>`. The old ST reference
STL6P3LLH6/C457492 was also checked (51 listed, 30 mΩ max) but **not selected**:
the actual SparkFun FET has better stock and half the nominal maximum resistance.
No Tech Public/HXY look-alike is silently substituted for an ST part.

Standard KiCad footprints and custom pad aliases are explicit in `circuit.json`.
The actual KiCad 9 image check is recorded in `footprint-check.json`. Electrical
pin identity is taken from manufacturer tables/source, not a package-name guess.
The custom FET footprint's pin 1 is bottom-left in its zero-rotation top view;
parent CPL rotation must be reconciled against the assembler's actual package
orientation. The footprint-load check does not establish assembly rotation.

## Current path losses — calculated, not measured

STL9P3LLH6 data: 12 mΩ typical / 15 mΩ maximum at VGS = −10 V, test ID = −4.5 A;
22.5 mΩ max at −4.5 V. With 100 kΩ/22 kΩ drive, nominal VGS ≈−16.39 V at 20 V,
and ≈−18.10 V at 22 V including worst 1% divider direction and low driver VOL.
This is below ±20 V gate absolute maximum in the stated steady input range;
arbitrary cable transients are not covered by that DC calculation.

At **5 A** using the 25 °C −10 V maximum resistance, the two-FET path is
approximately **30 mΩ, 0.150 V drop, 0.750 W**. Typical values give **0.600 W**.
An illustrative 1.6× hot-resistance multiplier gives **1.20 W / 0.240 V** for
the pair; this is a temperature sensitivity estimate, not a guaranteed hot limit
or measured junction temperature. Copper spreading and thermal interaction must
be checked on the final crescent layout. There is no justification to dissipate
this in a narrow isolated pad with no spreading copper.

GCT specifies 40 mΩ initial maximum contact resistance (50 mΩ after testing).
Assuming equal sharing across four contacts in each direction gives another
**20 mΩ loop / 0.50 W at 5 A** initially (0.625 W after-test value). Real sharing,
plug/contact wear, PCB traces and cable losses are unmeasured. Do not claim
100 W delivered to TECs. TPS bias typically adds only small dissipation; reserve
10 mA raw-input overhead conservatively until measured. Limit **total source
current**, including this front end and all motor/fan/controller loads, to 5 A;
use ≤4.9 A load-budget target to leave control/inrush margin.

## NVM commissioning and release checks

[`commissioning.ino`](../electronics/revb/pd/commissioning.ino) supplies concrete
SparkFun-library calls; it is a **fixture program**, not normal boot firmware.
The target is logical configuration, not a fabricated 40-byte NVM image. Retain
factory calibration/reserved bits and use ST's documented NVM method/library.

1. Cable disconnected; fixture supplies current-limited 5 V to `PD_VBUS_RAW`.
   Fixture shorts `PD_GATE` to `PD_FET_SOURCE` to force both PMOS off regardless
   of factory NVM. This only shunts the 22 kΩ limited gate driver, not a power
   rail. Independently supply the host 3.3 V and use HOST_SCL/HOST_SDA. Ground
   is common. Hold the on-board ESP32 in reset if a separate fixture MCU owns
   the bus. Supplying host 3.3 V alone cannot commission this circuit.
2. Wait ≥30 ms after power/reset (example waits 100 ms), read current NVM, record
   original image, write target once, verify readback. The sketch covers exposed
   SparkFun API fields; discharge enable/timing still require explicit ST-tool
   readback. Do not overwrite reserved bits to invent a desired dump.
3. Remove fixture gate clamp and power-cycle all rails. Confirm the target
   survives cold startup. Disable downstream loads initially.
4. With PD analyzer/e-load, check 5 V-only, 20 V/3 A, 20 V/4.3 A, proper 20 V/5 A,
   both cable orientations, 3 A vs 5 A cable, detach, hard reset, source power
   sharing renegotiation, over/under-voltage and MCU held in reset/off.
5. Measure source current, load inrush, gate/source voltage, off leakage,
   input/output discharge, bus power-off injection, and connector/FET temperature
   at intended maximum ambient and current. Verify no load activation on fallback.

All those physical checks are **unrun**. The sketch is not compiler-verified in
this subtask; integrate/pin the real SparkFun library and fixture platform first.

## Explicit unresolved items

- Parent must allocate board-edge USB access, shell soldering/process, 5 A copper
  and thermal spreading, total load budget, fuse/electronic fault limiting and
  motor regeneration handling. No full-board layout was generated here.
- Confirm effective downstream capacitance **including external TEC regulators**.
  If >150 µF, the current discharge component values are not approved unchanged.
  Slew-rate/inrush and FET linear-mode SOA also need validation with real capacitance.
- Manufacturer MLCC DC-bias curves and final footprint stencil/X-ray policy need
  review; all quoted electrical/thermal losses are calculations, not trial results.
- TVS clamping coordination is reference-derived, not independently surge-rated
  below every downstream absolute maximum. Do not advertise completed IEC tests.
- Manufacturing must establish a one-time NVM programming/readback fixture.
  Assembled factory-default ICs do not automatically implement the load gate policy.
- Actual unplug discharge must be checked with collapsing ST VDD; the RC estimate
  alone does not prove the internal discharge switch stays active long enough.
- TCA bus isolation is specified at missing supplies, not a guarantee of bus
  continuity through arbitrary brownout waveforms. Check recovery in host firmware.
- Stock snapshots need refresh before the parent freezes its assembler BOM.
  No supplier project, order, account, checkout or quotation was touched.

## Primary evidence

- [SparkFun hookup guide](https://learn.sparkfun.com/tutorials/power-delivery-board---usb-c-qwiic-hookup-guide/all):
  identity, NVM API and autonomous behavior.
- [Actual SparkFun source](https://github.com/sparkfun/Power_Delivery_Board-USB-C/tree/42134985243912d4803d1ff985458e44d11f1ee0),
  including `Hardware/SparkFun_STUSB4500_USB-PD.sch`, retained locally. Pin nets and
  FET identity were parsed from Eagle XML, not inferred from a photograph.
- [STUSB4500 DS12499](https://www.st.com/resource/en/datasheet/stusb4500.pdf),
  §§2.2, 3.3, 3.4, 5–7 and Fig.10. Direct download timed out; actual Rev.3 PDF from
  SparkFun is retained, and the current ST web-indexed text was cross-checked for
  pin map, policy and power-off warning. Do not mislabel the local file as Rev.8.
- [STL9P3LLH6](https://www.st.com/resource/en/datasheet/stl9p3llh6.pdf): manufacturer
  RDS(on), pinout and land drawing; downloaded Rev.2 manufacturer PDF mirror plus
  current Rev.3 ST web-indexed data agree on selected electrical values.
- [GCT USB4105 drawing](https://gct.co/files/drawings/usb4105.pdf) and
  [GCT specification A3 mirror](https://www.ariat-tech.com/datasheet/62/USB4105-GF-A.pdf).
- [ST ESDA25W family sheet](https://www.st.com/resource/en/datasheet/esdaxxxwx.pdf),
  [ESDA25P35-1U1M](https://www.st.com/resource/en/datasheet/esda25p35-1u1m.pdf).
- [TI TCA9517A](https://www.ti.com/lit/ds/symlink/tca9517a.pdf),
  [TI TPS709](https://www.ti.com/lit/ds/symlink/tps709.pdf): directly downloaded,
  pin maps, missing-supply isolation, VOL and capacitor/enable requirements checked.

Local URLs, mirror identities and SHA-256 hashes are in
[`sources.json`](../electronics/revb/pd/sources.json). Web retrieval, source
inspection and KiCad footprint loading are evidence; they do not constitute
PCB electrical simulation or a physical refrigeration/power qualification.
