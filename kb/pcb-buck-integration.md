# Revision B onboard buck regulators

2026-10-24. **Reference-based circuit proposal and analytical screening; no assembled-board measurements.** See [project KB](README.md), [decisions](decisions.md), [frozen revision A](pcb-design.md), and the [integration contract](../electronics/revb/power/circuit.json). Revision A and its supplier project are historical artifacts; the primary integrator owns the new KiCad revision.

## Integration recommendation

- **3.3 V:** Diodes **AP63203WU-7**, JLC **C780769**, 32 V input, 2 A synchronous converter, fixed 3.3 V, 1.1 MHz. Allocate **1 A** to ESP32 peaks plus motor logic/peripherals, subject to transient and thermal qualification.
- **12 V fan:** Diodes **AP63201WU-7**, JLC **C2071044**, same 32 V/2 A family and TSOT-23-6 footprint, 500 kHz forced PWM. Allocate **0.5 A startup capability**, with **0.14 A** normal Noctua load. Manufacturer divider gives **11.867 V nominal**; this is intentional and within a ±5% 12 V target.
- Supply both from **`SYS_20V`**, the **hardware-qualified, switched 20 V PD bus**. EN connects directly to that bus; these are not fed from raw USB VBUS. No 5 V logic rail is needed.
- STUSB4500 must negotiate autonomously from its upstream supply/NVM. Its power-switch decision must not depend on the ESP32, which is downstream and initially unpowered. STUSB programming and PD-switch implementation belong to the other blocks.
- Feed external DPS5005 and the motor power branch directly from the qualified 20 V distribution, **not through either buck**. A 20 V/5 A contract is a **shared 100 W input ceiling**, not an additional 100 W allowance for the DPS. These rails alone reserve up to **11.54 W / 0.577 A at 20 V**, assuming 80% efficiency at simultaneous 1 A/0.5 A outputs, before motor and switch/cable losses.

`electronics/revb/power/design.py` generates **22 components** with full numbered pin-net maps in `circuit.json`. References are `UP*`, `LP*`, `CP*`, `RP*`; map the single input net to the PD agent's actual qualified output. Retain existing ESP32 local decoupling/reset delay and fan default-full-speed PWM behavior. Replace the old AP2112 LDO/external-rail input path in the new revision.

## Why these parts

AP63203 avoids the heat and current limitations of the old LDO. At 1 A, even a hypothetical 20-to-3.3 V LDO would dissipate **16.7 W**; these are direct synchronous bucks.

AP63200 initially looked best for the fan because its PFM mode saves light-load power. The direct public snapshot returned `overseasStockCount=281`, `canPresaleNumber=4`; AP63201 returned **8,981 / 8,723**. Select AP63201 for procurement resilience and accept its forced-PWM light-load overhead. The manufacturer's table gives the same external 12 V circuit for AP63200/AP63201. AP63200 C2071868 remains a documented pin-compatible substitution requiring BOM update and PFM ripple testing. **AP63205 is fixed 5 V and cannot substitute for a 12 V rail.** TI LMR16006 is only 0.6 A and nonsynchronous, so it misses the 3.3 V peak target and the requested synchronous/common-family solution.

Public distributor descriptions incorrectly imply 22 µA/PFM behavior for AP63201. The **manufacturer datasheet wins**: AP63201 is forced PWM and lists **258 µA** quiescent current under its specified non-switching test, versus 22 µA for AP63203/AP63200. Neither number includes loaded switching losses.

## Actual pin map and reference circuits

Both ICs, **top view numbered pads**:

| Pad | Manufacturer function | UP1, 3.3 V | UP2, fan |
|---|---|---|---|
| 1 | FB | `+3V3`, direct sense after LP1 | `PWR_FB12`, divider midpoint |
| 2 | EN | `SYS_20V` | `SYS_20V` |
| 3 | VIN | `SYS_20V` | `SYS_20V` |
| 4 | GND | GND | GND |
| 5 | SW | `PWR_SW1` | `PWR_SW2` |
| 6 | BST | `PWR_BST1` | `PWR_BST2` |

Each bootstrap capacitor is **100 nF between BST and SW**, not ground. Each SW connects through its own inductor to its output. Both converters have internal compensation and synchronous MOSFETs; no external catch diode is required.

Sources:

1. [Diodes AP63200/01/03/05 datasheet](https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf), DS41326: pin descriptions, figures 20–22, tables 1–3, equations 6–12, layout figure 25. A manufacturer-authored **Rev 2-2, January 2019** mirror is retained in [reference sources](../electronics/revb/power/reference-sources.json), because direct manufacturer download returned HTTP 403. Current manufacturer search-indexed tables were also cross-checked; this is not a claim that the retained mirror is the newest revision.
2. [Diodes AP63203 EVB guide](https://www.diodes.com/assets/Evaluation-Boards/AP63203-EVB-User-Guide.pdf) and retained manufacturer-authored [AP63203WU-EVM guide mirror](https://pdf.htelec.com/pdf/36/AP63203WU-EVM%20User%20Guide%20Manual%20R1.pdf): **6.8 µH** EVM inductor, 100 nF bootstrap, 2×22 µF output reference. The datasheet table recommends 3.9 µH; 6.8 µH here follows the EVM and reduces ripple at this lower load budget.
3. [Bourns SRN6045TA manufacturer datasheet](https://www.bourns.com/docs/product-datasheets/srn6045ta.pdf), [distributor mirror](https://www.farnell.com/datasheets/2163191.pdf): inductance/current/DCR table and land pattern. Manufacturer tables were read through indexed PDF text; direct download was blocked.

### Fan voltage setting

`Vout = VFB × (1 + Rtop/Rbottom)` with **VFB = 0.800 V**, **Rtop = 249 kΩ**, **Rbottom = 18 kΩ**. This is exactly the manufacturer's nominal "12 V" table, giving 11.8667 V. Use **56 pF C0G across Rtop** as that table specifies. With ±1% resistors and VFB=0.792–0.808 V, arithmetic corners are **11.531–12.211 V**, excluding resistor temperature drift and transient ripple. Divider current is approximately 44.4 µA; top-resistor dissipation is 0.49 mW.

### Enable and fallback handling

The manufacturer's EN pin is high-voltage tolerant: direct VIN connection is explicitly permitted; recommended VIN range is **3.8–32 V**, EN absolute maximum 35 V. Normal input qualification here is **19–21 V**, not permission to operate a 32 V bus with uncontrolled spikes.

**Hard dependency:** the upstream power switch must remain OFF for USB fallback 5/9/12/15 V, failed negotiation, insufficient contract/current, detach and contract loss. It must also manage inrush and reverse/backfeed behavior. These two bucks do **not** independently authenticate PD. An ordinary `VBUS_EN_SNK`/attachment indication alone must not be assumed to mean "20 V at 5 A"; the PD design must establish the actual meaning of its selected control signal/NVM configuration.

If that dependency changes, redesign EN control before integration: the IC has a precision EN threshold (rising 1.15–1.23 V, falling 1.05–1.15 V), internal pull-up current sources and datasheet UVLO-divider equations. A simple divider ignoring those currents is wrong; a voltage threshold alone also cannot establish a 5 A contract. No speculative UVLO resistor network is populated in this contract. The present approach keeps power sequencing independent of firmware and avoids circular boot dependencies.

Disabling VIN does not guarantee immediate output discharge. Test rail decay, external UART/I²C back-powering, and reverse current through synchronous stages. Do not power the board through the programming header's 3.3 V reference pin.

## Exact stocked BOM and footprints

Timestamped evidence is in [stock-evidence.json](../electronics/revb/power/stock-evidence.json). These are **public hydration fields**, not reserved inventory or assembly acceptance. `overseasStockCount / canPresaleNumber` are reported verbatim; their values differ and must not be treated as interchangeable promises. The selected parts all have positive values for both. The script uses the existing frozen `electronics/pcb/check-stock.py` parser without modifying it, with pacing/retries for public HTTP 429 responses.

| Refs | Exact MPN | JLC code | Snapshot stock / presale | KiCad footprint |
|---|---|---|---|---|
| UP1 | AP63203WU-7 | C780769 | 7,420 / 4,049 | `Package_TO_SOT_SMD:TSOT-23-6` |
| UP2 | AP63201WU-7 | C2071044 | 8,981 / 8,723 | same |
| LP1 | SRN6045TA-6R8M | C2041457 | 146 / 121 | `Inductor_SMD:L_Bourns_SRN6045TA` |
| LP2 | SRN6045TA-100M | C2046332 | 6,634 / 6,425 | same |
| CP1/2/11/12 | CL32B106KBJNNNE, 10 µF 50 V X7R | C138687 | 107,442 / 61,900 | `Capacitor_SMD:C_1210_3225Metric` |
| CP3/4/13/14 | CC0603KRX7R9BB104, 100 nF 50 V X7R | C14663 | 44,140,263 / 26,320,042 | `Capacitor_SMD:C_0603_1608Metric` |
| CP5/6/7/8/15/16/17 | CL31A226KAHNNNE, 22 µF 25 V X5R | C12891 | 1,631,352 / 1,203,878 | `Capacitor_SMD:C_1206_3216Metric` |
| RP1 | 0603WAF2493T5E, 249 kΩ 1% | C22918 | 181,661 / 171,127 | `Resistor_SMD:R_0603_1608Metric` |
| RP2 | 0603WAF1802T5E, 18 kΩ 1% | C25810 | 854,914 / 734,659 | same |
| CP18 | TCC0603COG560J500CT, 56 pF 50 V C0G | C282507 | 1,244 / 1,231 | `Capacitor_SMD:C_0603_1608Metric` |

All selected entries are `smtWeld`. Public AP63201 metadata says MSL 3; let the assembler apply its actual packaging/baking requirements. The attempted 0.1% 249 kΩ Yageo option returned 16/0 and was replaced by the stocked 1% Uniroyal part. Earlier non-TA Bourns candidates are retained in evidence only, not the populated BOM.

**KiCad verification executed:** six distinct footprints and five symbols loaded on **KiCad 9.0.2**. Regulator library symbols use name `IN` for manufacturer `VIN`, with the same pad 3. Pin-number sets match every component's net map. [Audit record](../electronics/revb/power/kicad-audit.json) includes pad coordinates/sizes and source hashes; exact standard-library copies are in `electronics/revb/power/power.pretty/`. The Bourns land pattern is 6.5 mm overall by 5.1 mm, two 2.35×5.1 mm pads at X ±2.075 mm with a 1.8 mm gap, matching its recommended drawing. Inductor body is 6×6 mm, maximum height 4.5 mm. This verifies library availability and pin mapping, not the assembled-board placement/orientation.

## Component sizing and assumptions

**Inductors:** LP1 is 6.8 µH ±20%, 34 mΩ ±20%, typical Irms 3.6 A / Isat 5.7 A. LP2 is 10 µH ±20%, 52 mΩ ±20%, typical Irms 3.2 A / Isat 4.6 A. Bourns defines Isat at **30% inductance reduction** and Irms at **40°C rise**; these are not flat inductance guarantees. Screening additionally reduces L by 20% for bias/temperature and typical current ratings by 20%. Even that assumed Isat margin exceeds the regulator's 3.1 A maximum high-side peak limit. Temperature dependence, fault energy and actual inductor heating remain bench checks.

**Capacitors:** two local 10 µF/50 V 1210 input MLCCs per converter; four local 22 µF/25 V 1206 outputs for 3.3 V, three for 12 V. X5R output parts imply an **85°C capacitor temperature ceiling**. No assumption that a 22 µF marking means 22 µF under DC bias is made. Screening assumes 70% input/50% output DC-bias retention, then 0.9 tolerance and 0.85 temperature factors: **10.71 µF effective input per converter**, **33.66 µF effective 3.3 V output**, **25.245 µF effective fan output**. Those retention factors are **design assumptions, not extracted manufacturer curve minima**. Obtain exact MPN bias curves (Samsung simulation data) or biased-capacitance measurements before considering this qualified; change parallel count/package if the floor fails. Distributor datasheet links for each exact capacitor are in `circuit.json`/stock evidence.

The reference uses one 10 µF input and two 22 µF outputs. Extra capacitors provide derating/load-step margin but are an explicit reference deviation needing loop/startup checks. The first three-capacitor 3.3 V study gave 0.284 V droop for a 0.7 A step over an assumed 10 µs response, marginal against the ESP32's 3.0 V minimum after regulator tolerance. Four capacitors reduce that simplified estimate to **0.215 V**, leaving 3.025 V after a 3.27 V initial rail and 30 mV distribution allowance. **10 µs response is an assumption, not measured loop behavior**; slower response can still fail. Existing module-local bypass remains required.

## Executed analytical screening

[Reproducible analysis](../electronics/revb/power/analysis.json) evaluates 21 V input, -6% switching-frequency spread, -20% L tolerance and another -20% L derating. Nominal frequencies have no published absolute tolerance bounds in the retained datasheet, so these are **assumed corners**, not a full guaranteed worst-case analysis.

`ΔIL = Vout × (1−Vout/Vin)/(L×f)`; `Ipeak = Iload + ΔIL/2`. Typical 4 ms soft-start capacitor-charging current is added for startup screening.

| Result | 3.3 V / 1 A | Fan / 0.5 A startup |
|---|---:|---:|
| Screened ripple current | 0.618 A p-p | 1.716 A p-p |
| Peak load current | 1.309 A | 1.358 A |
| Peak including typical-soft-start charging | 1.389 A | 1.573 A |
| Inductor RMS | 1.016 A | 0.704 A |
| CCM output ripple, assumed bank ESR 10 mΩ | 8.4 mV | 35.2 mV |
| On-time at highest spread frequency | 135 ns | 1,066 ns |

Both peak estimates are below the **2.5 A minimum** IC high-side current threshold. On-time exceeds the **80 ns typical** minimum; absolute minimum-time bounds are unpublished. At light ESP32 load AP63203 enters PFM, so its burst ripple is not predicted by this CCM calculation. AP63201 remains forced PWM and can circulate reverse inductor current at light fan load.

**Losses are estimated, not validated:** MOS conduction using typical 25°C RDS(on) gives about 0.080 W / 0.050 W; the assumed-hot inductor copper terms are about 0.055 W / 0.040 W. Switching, gate-drive and core losses are missing from those terms. A separate deliberately broad **80–90% efficiency assumption** gives total converter loss **0.37–0.83 W** at 3.3 V/1 A and **0.66–1.48 W** at 11.87 V/0.5 A. At the normal 0.14 A fan load it gives **0.18–0.42 W**. No efficiency figure is measured or guaranteed.

The datasheet's **89°C/W θJA** uses a particular single-layer 2 oz test board; it does not characterize our crescent PCB. Assigning all of the above total loss to the IC would imply roughly 33–73°C rise for the full 1 A logic load, and 59–132°C for a continuous 0.5 A fan load. That deliberately conservative illustration is why **0.5 A startup electrical headroom is not a demonstrated continuous thermal rating**, and sustained ESP32 load must be tested. 160°C thermal shutdown is fault protection, not an operating target.

Eight tests passed, including fault injection for bootstrap-to-ground, wrong inductor value, inadequate Isat, reversed feedback, 16 V input capacitor, raw-VBUS connection and inadequate transient capacitance. These tests establish circuit/assumption consistency, not control-loop stability or hardware performance.

## Layout handoff and physical checks

1. Follow manufacturer layout figure 25: place VIN bypass directly across **pins 3 and 4**, with the smallest practical high-di/dt loop. Put BST capacitor directly between pins 6 and 5. Keep SW copper short to LP and small in area; no signal/FB routing under SW/inductors.
2. Put output MLCC banks next to their inductors. Sense `+3V3` and `+12V` at the output capacitor positive pad with quiet traces; route RP2 ground to UP2's local capacitor/IC ground, not through fan/motor/DPS return currents.
3. Use a continuous bottom ground plane and several ground stitching vias at local input/output capacitor ground pads. Datasheet recommends **2 oz top and bottom copper** for its 2 A design. If the integrated board stays 1 oz, demonstrate thermal performance at the selected lower loads; do not transfer the datasheet thermal number without testing. Separate these hot parts from the ESP32 antenna and warm motor driver.
4. Place buck input branches independently of motor damping/high-current DPS paths. The local banks add **40 µF nominal** directly to the switched 20 V bus, plus upstream/motor/DPS capacitance. PD switch inrush design must include all of it and input MLCC charging before buck soft start; buck soft start alone does not limit this input inrush.
5. Measure startup with 5/9/12/15 V fallback and 20 V source, failed negotiation, unplug/replug and load disconnect. Confirm hardware gating, no backfeed and no damaging VIN/SW overshoot; preserve margin below the 32 V operating rating rather than using 35 V absolute maximum as a clamp target.
6. Measure ESP32 Wi-Fi bursts and 0.1↔0.8/1 A electronic-load steps at the module; require 3.0–3.6 V throughout, including startup/unload. Measure 12 V fan cold startup/stall/retry current and PWM/tach behavior with the selected physical fan. Check larger output banks for ringing/oscillation across load and supply corners.
7. Record efficiencies, inductor/IC/capacitor temperatures and rail ripple at installed ambient, with the motor and DPS operating. No feeder bench thermal, ripple or fan-start data exists in this handoff.

## Reproduce

From repository root:

```sh
python electronics/revb/power/design.py
python electronics/revb/power/analyze.py
python electronics/revb/power/test_power.py
docker run --rm --network none --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work cat-feeder-kicad:local /usr/bin/python3 electronics/revb/power/audit_kicad.py
```

`refresh-stock.py` fetches missing snapshot codes only; archive/delete the owned snapshot deliberately if refreshing all timestamped records. It performs public read-only requests, no supplier account operations. Add a link to this page from the primary KB index during the main integration; that index is outside this subtask's file ownership.
