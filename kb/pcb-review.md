# Independent controller PCB review — revision A draft

**Focused independent recheck completed 2026-10-24 at 15:37 UTC. Decision: CLEARED TO PREPARE THE SUPPLIER PROJECT under D25. B1 and B2 are resolved; no preparation blockers remain from this PCB review.** This supersedes the initial HOLD and the designer's pending-recheck flags. Supplier placement/process checks remain open; this is not permission to request a quote, order, pay or release fabrication. The owner submits the quote request.

Scope: actual schematic/netlist, generator, placed pads and routed copper, local footprints, fabrication ZIP, BOM/CPL, check configuration and public component documentation. This is a design/manufacturing review, **not physical qualification**. No PCB/source/generated files were edited; no supplier account, credential, project, upload, quote or order operation was performed. The local supplier secret was not read.

Related: [design rationale](pcb-design.md), [PCB files/pinouts](../electronics/pcb/README.md), [sourcing](../electronics/pcb/SOURCING.md), [checks](../electronics/pcb/CHECKS.md), [TEC integration](tec-control.md), [packaging handoff](../electronics/pcb/PACKAGING.md), [owner decisions D22–D25](decisions.md).

## 0. Current corrected revision — independent recheck

Reviewed [REVIEW-FIXES.md](../electronics/pcb/REVIEW-FIXES.md), changed generator/finishing/export code, actual schematic and routed board, both BOM/CPL pairs, [exact-code reconciliation](../electronics/pcb/assembly-reconciliation.json), and rule-persistence implementation. Unaffected component research was retained rather than repeated. All checks operated on selected scratch copies; originals and credentials remained untouched. No supplier operations were performed.

### Findings closed

- **B1 — CLOSED:** independently regenerated the netlist from the current schematic and inspected actual PCB pads. R20 is **10 kΩ/C25804**, at **(79,113), 0°**, pad 1 +3V3 and pad 2 `/DPS_TX` joined to U3.2/U1.28. R21 is **10 kΩ/C25804**, at **(91,109), 90°**, pad 1 `/DPS_TX_EXT` joined to U4.2/J9.3 and pad 2 GND. R14's 10 kΩ OE pull-up and R15's 1 kΩ output resistor are retained. DRC verifies connected copper, including R21's plane connection. These implement the requested reset/disconnected-input bias without a board pull-up into unpowered DPS TX. The real DPS TX's ability to drive the calculated 0.33/0.50 mA load remains an interface qualification item, not an unimplemented PCB correction.
- **B2 — CLOSED:** independently derived centres from the **actual placed F.Fab body geometry**, including the capacitor's body circle and rotated headers, without using the designer's datum/rotation table to compute expected positions. **All 54 CPL coordinates agree within 0.000051 mm export-rounding tolerance:** 18 corrected THT centres and 36 centred SMT placements. Both files have exact, unique reference membership. The reconciliation covers **17 exact component codes and all 54 refs**; every listed pad number/net/position matches actual PCB geometry. Supplier zero-angle and additional supplier-origin corrections are explicitly **null/pending**, not falsely certified as zero. The native KiCad angles remain a declared input to the later supplier overlay.
- **Missing netclasses — CLOSED:** delivered project now has Default **0.25 mm**, Motor **1.0 mm**, Power **0.5 mm**, with the 18 slash-prefixed/unprefixed assignments. Reviewed the byte-preserving save wrapper and its use in generation/routing/export. Ran the supplied regression independently: **two actual load/save cycles preserved project bytes; four malformed configurations were rejected**. This restores routing defaults, not a continuous-current rating or minimum-width guarantee.

Selected independently checked final CPL coordinates (X right/Y up, mm):

| Ref | Mid X | Mid Y |
|---|---:|---:|
| J14 | 17.1177 | 30.1100 |
| J15 | 32.3577 | 30.1100 |
| C10 | 42.6177 | 36.0000 |
| J1 | 46.1577 | 7.3000 |
| J12 | 37.3877 | 51.5000 |
| J13 | 13.3877 | 57.8000 |
| U1 | 33.1177 | 67.0000 |

### Current provenance and checks

**These identifiers/counts supersede the 52-part revision recorded in §§1–2.** All **85 manifest entries** matched their contents, and all **11 manufacturing ZIP members** matched the current manufacturing directory. The manifest digest matches the designer's handoff.

| Current artifact | SHA-256 |
|---|---|
| `checksums.json` — 85 files | `9fa46fefed298d092bc83b532faa0848905522ade1cb9342ddb9abefd91d803f` |
| `feeder.kicad_pcb` | `d51e589d13a7a96097fe12be33ff051cb9bbc9b4033ba4c07ba581e1121458c9` |
| `feeder.kicad_sch` | `e654d14f7e0a30f93cc36065ead615d0bef2af4178c14e23c3849ab7990fcace` |
| `manufacturing-draft.zip` | `299060b29d9c513d315a43b801495c119b8515f2023ad7b1e1cb41ccf2d1bfc6` |

- **54 components = 36 SMT + 18 THT; 621 trace segments, 55 routing vias**, plus the unchanged twelve ESP32 thermal-land holes.
- Fresh KiCad **9.0.2** ERC: **0 errors, 0 warnings**. Fresh DRC with schematic parity: **0 violations, 0 unconnected, 0 parity issues**. Used the existing network-disabled image and writable scratch project to avoid the already-understood read-only library-discovery issue.
- Independently compared **179 netlist nodes**, including singleton NC nodes, against actual PCB pad nets. The designer's 163-node result counts intended connected nodes; these are different scopes, not contradictory counts. Checked new resistor values/codes against the regenerated schematic netlist and both expanded BOMs.
- Compared against the retained, hash-verified original PCB, not only the designer's new baseline record: **all original 52 placements/rotations, pad sizes/drills/positions/nets and the outline polygon are unchanged**. Copper comparison found **32 added segments and 3 added vias; no removed original copper items**. Actual phase paths remain ≥1 mm and via-free. Inspected refreshed top/bottom views around R20/R21 and the new routes.
- Checked schematic/PCB/project/library-table scratch inputs remained byte-identical to the reviewed originals after checks. No unexplained new circuit/layout finding arose.

Scratch evidence (outside the repository): the review scratch directory's `recheck/` subdirectory contains `independent-recheck.json`, `independent-netlist.xml`, fresh reports and the independent checking script. Report SHA-256: ERC `e25572f269ef8c8e9754870aa65448f87908dfae07306b118be2e7dd64a5b16d`; DRC `d7d224de45468339615ada2c43e6cb067e030730808a0bd2335906261d8246fc`; independent summary `104eafa2218f5c2cab1d90239402c29cdd381bd7df2c9f18f01c8c9f20e84b7a`.

**Remaining gates are unchanged in scope:** exact header/socket drawings or supplier fit confirmation; supplier pad/rotation/polarity overlays; ESP32 thermal-land solder process; curved-board handling/panelisation. Resolve them during project preparation and before fabrication acceptance. LDO thermal/load budget, actual DPS grounding/levels/power order, fan waveform, motor current/transients, sensors, external TEC shutdown and firmware remain bench/system qualification. Mechanical mount integration is the primary session's separate task and was not re-reviewed here.

## 1. Initial findings — resolved by §0, retained as rationale

The following describes the **superseded 52-part draft**. Its present-tense defect descriptions and requested fixes are historical; both preparation blockers are now closed.

### B1 — P2 electrical: the UART buffers have floating data inputs in normal supported states

**Actual defect, not a missing-firmware complaint.** In `electronics/pcb/generate.py:74–77`, U3.2 (`DPS_TX`, connected to U1.28/GPIO17) and U4.2 (`DPS_TX_EXT`, connected to J9.3) have no bias resistor. The same connections were verified on actual PCB pads and the exported schematic netlist. R14 pulls up the **OE pins**, not either data input.

- U3.2 can float while the ESP32 is reset or its UART pin has not been configured.
- U4.2 floats with the optional DPS cable disconnected, and can float with the DPS unpowered. These are normal bare-controller/commissioning conditions.
- Disabling OE only disables the output stage. TI's SN74LVC1G125 data sheet, §§7.3.2–7.3.3, explicitly distinguishes this from Ioff at VCC = 0 and says not to leave CMOS inputs floating during operation. An undefined input can produce excess supply current/oscillation even with its output disabled. Neither ERC nor the present DRC encodes that requirement.

**Concrete fix:** add a 10 kΩ pull-up from U3.2 to +3V3, and a 10 kΩ pull-down from U4.2/J9.3 to GND, using the already selected resistor family if desired. The input-side pull-down avoids feeding an unpowered DPS through a board-side pull-up. Confirm the actual DPS TX can drive the resulting 0.33 mA at 3.3 V (0.5 mA at 5 V); select another resistance only with a leakage/logic-level budget. Keep R14 and the output series resistor. Disable OE while the DPS is absent/off; its receive-low state while disconnected is not a valid UART session. Regenerate schematic, layout, BOM, placements and checks. A pull-up on the ESP-side receive output is also useful, but can instead be provided by the MCU input configuration; it does not replace the two buffer-input fixes.

### B2 — P1 assembly data: THT `Mid X/Mid Y` fields contain pin-one origins, not centroids

**Actual file-format mismatch; not a demonstrated misassembly.** `export.py:37–40` exports `fp.GetPosition()` unchanged into `assembly-cpl-all.csv`. For all 18 THT placements this is the native pin-one origin. JLC's [CPL specification](https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly) requires component **centroids** for surface-mount **and through-hole** parts. A disclaimer about later alignment does not turn these numbers into centroids.

Examples from the actual board, in KiCad millimetres before the shared origin transform:

| Ref/group | Current native origin | Geometric body centre / correction |
|---|---|---|
| J14 | (59, 91), pad 1 | Header centre (59, 99.89): **8.89 mm** Y error; exported Mid Y should be 30.11 rather than 39.00 for a centred model |
| J15 | (74.24, 91), pad 1 | (74.24, 99.89), same error |
| C10 | (82, 94), positive lead | Body centre (84.5, 94): **2.50 mm** X error |
| J1/J16/J17 | Positive/first terminal pin | Native Fab-body centre offset approximately (+2.54, −0.30); verify against the matched library body datum |
| Vertical 1×3 / 1×4 headers | First pin | Centre offset (0, +2.54) / (0, +3.81) |
| J10 | First pin | Centre offset (0, +1.27) |
| J12/J13, rotated 90° | First pin | Centre offset (+1.27, 0) |

**Concrete fix:** keep editable footprint datums if convenient, but implement explicit, reviewed component-centre offsets in the CPL exporter and apply footprint rotation before converting to X-right/Y-up manufacturing coordinates. Alternatively use supplier-library-specific translations backed by an actual pad-to-pad overlay. Do not blindly average ESP32 pads: its asymmetrical exposed-pad pattern is not its body centroid. U1's existing origin is the module body centre; ordinary SMT origins here are already centred.

Create an offset/rotation reconciliation record keyed by exact LCSC code, including pin 1, C10 polarity, U1 antenna direction and Phoenix wire-entry direction. Preserve the lower-left origin shared with Gerber/drill. Verify all 52 refs once, not just the SMT subset, and regenerate hashes. **Supplier zero-angle differences still need the later JLC placement preview**; this review does not invent a universal SOT-23 or connector rotation correction. A documented supplier origin conversion is an acceptable resolution; an unreviewed native-origin file is not.

## 2. Initial 52-part check provenance and layout — superseded by §0

The completed draft was retained across the server interruption; earlier successful inspection was not discarded. All 17 entries in `checksums.json` matched their files. Every member of `manufacturing-draft.zip` matched the corresponding current `manufacturing/` file: nine Gerbers, job file and drill file.

Reviewed SHA-256 identifiers:

| Artifact | SHA-256 |
|---|---|
| `feeder.kicad_pcb` | `6a69582a57236ffb769218b08e0ee6d3e82f06e7c02e8eaae30bb5485bf9b993` |
| `feeder.kicad_sch` | `d97d6615be4132802ad40a7f4b0182ebc2bd9599989a6fe4dab076b4d7ac8113` |
| `manufacturing-draft.zip` | `95c399eb721dc370e74a6b388c92d979405977f0f6ba8c412e1f7161703c6037` |
| `checksums.json` | `81713bd2a6c569b833eeadc26984dafe5054f207d778d5876cc833d4d2bc506c` |

Independent KiCad **9.0.2** checks were run in the existing `cat-feeder-kicad:local` image with networking disabled. Its image ID was `sha256:7d5c6efc608913909f9f96531652ace8fc809bcab82a8d0e21c774c67a7279b9`.

- First runs against a read-only mount produced 52 library-availability warnings apiece, all about missing local library `feeder`; they had **zero unconnected and zero schematic-parity issues**. These were investigated rather than suppressed.
- Checks on a scratch copy containing the same project and local libraries, with writable project-directory access, produced **ERC 0 errors/0 warnings; DRC 0 violations/0 unconnected/0 parity issues**. The schematic, PCB, project and library tables remained byte-identical to the originals afterward. This separates the read-only-mount library-discovery problem from circuit violations.
- Actual `pcbnew` inspection independently counted **52 footprints, 589 trace segments, 52 routing vias**, plus twelve 0.2 mm holes within U1 pad 39. Compared actual pad-net assignments with `schematic-netlist.xml`: **no mismatches** among its represented nodes. Deliberately unused pads carry singleton NC nets.
- BOM reference counts are **34 unique SMT refs** and **52 unique mixed-process refs**. No missing or duplicate BOM reference was found. Positive-stock evidence is a timestamped snapshot, not a reservation or assembly acceptance.
- Inspected current top/bottom copper and component views, not only check reports. Copper is present on both sides; the top antenna strip is clear on both enabled copper layers. Motor phase routes are 1.0 mm throughout and have no routing vias. VMOT has no routing vias; its only sub-1 mm segments are the previously described 0.8014 mm ADC spur. +3V3/+5V/GND routed tracks inspected are 0.5 mm. Ground pours provide additional paths; their full connections are not thermal-relief spokes.

Scratch evidence, including `actual-board.json`, checked-copy reports and downloaded data sheets, was kept in temporary storage outside the repository. This report preserves durable conclusions. Final independent report hashes: DRC `f5ff53ab74efcde7a1e62983ca47dbc1591888d6ad5451ba5b3495612550876b`; ERC `aef31e893df1394383a298ff989d35447a0f52e386d6a57e24ad4c7cf0c01b49`.

### Initial rule configuration finding — resolved by §0

`feeder.kicad_pro:236–335` contains only the `Default` netclass, with track width 0.2 mm. Its patterns still refer to **absent `Motor` and `Power` class definitions**. The generator at lines 264–272 intends to create these classes, but the delivered project has lost them. Therefore it does **not** preserve the claimed motor/power routing defaults for future GUI edits. Current actual copper has the inspected widths above; this is not evidence that current motor tracks are 0.2 mm.

Restore the definitions in the delivered project and fix the import/save workflow so they survive. Prefer explicit minimum-width rules for phase/load paths if automatic enforcement is intended; a preferred netclass track width alone is not a current-capacity guarantee. Keep the intentional VMOT sensing spur distinguishable from its load path. Also add a project-configuration assertion to export verification.

`drc_exclusions` is empty. Clearance, shorts, unrouted nets, antenna restrictions and footprint-library mismatch checks have not been waived. The project does have several `ignore` severities (footprint filters/type, missing courtyard, PTH/NPTH-inside-courtyard); those are not proof of a suppressed electrical defect. The 0.2 mm minimum plated-hole rule accommodates the actual ESP32 land holes and is a legitimate declared manufacturing choice, subject to supplier capability. The claim “no rule severity was suppressed” should be read narrowly, rather than implying every available DRC category is enabled.

## 3. Electrical review

### ESP32-WROOM-32E-N4: pinout, straps, programming and antenna

Verified against Espressif module data sheet v2.1, pin table and boot-configuration chapter:

- U1.2 is 3.3 V; U1.1/.15/.38 and exposed pad .39 are GND. Assigned GPIOs match the documentation: pads 6/7 are input-only GPIO34/35, pads 27/28 are GPIO16/17, pads 30/31 are GPIO18/19, pads 33/36 are GPIO21/22 and pad 37 is GPIO23. The six NC module pads and pad 32 are not incorrectly used as GPIOs.
- GPIO0 has R2 = 10 kΩ to 3.3 V and the grounded BOOT shunt J12. GPIO2 and MTDI/GPIO12 are unconnected, allowing their internal default pull-downs; GPIO5 and MTDO/GPIO15 likewise retain their defaults. No external load was found forcing the 1.8 V flash-supply strap or preventing ROM download. GPIO13 controlling OE is not a boot strap.
- EN has the recommended starting RC values R1 = 10 kΩ/C5 = 1 µF and J13 reset-to-GND. J11 provides true UART0 TX/RX and 3.3 V reference. Manual BOOT/reset programming is feasible; an onboard USB bridge/auto-reset circuit is not necessary for a bare-controller assembly.
- Module body is 18 × 25.5 mm; its origin is (75, 63). The antenna occupies the top module region, with a board-wide copper exclusion to Y56.7 and a module-footprint exclusion on both copper layers. No copper-under-antenna error was found. The board material still extends beneath the antenna. Espressif prefers an overhanging antenna or suitable board cutout and substantial surrounding clearance; the enclosure/wires/sinks must preserve RF space and be range-tested. **Copper keepout is not an installed 15 mm all-direction clearance claim.** This is a packaging/RF qualification item, not evidence of a pinout fault.

### AP2112 supply and thermal budget

U2 actual pads agree with the SOT25 data sheet: 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT. VIN and EN are both at external +5 V, output is +3V3. C1 and C2 provide nominal 10 µF input/output storage; C4 adds module-side bulk capacitance and C3 adds 100 nF. AP2112 is stable with suitable 1 µF ceramic capacitance; the selected larger nominal values provide margin, but effective capacitance under bias still matters.

**The present board has no established continuous 600 mA thermal budget.** Diodes DS39724 Rev. 2-2 gives SOT25 θJA = 184°C/W, absolute maximum junction temperature 150°C, typical shutdown around 160°C. Using that reference thermal resistance and exactly 5.0 V input:

| Total 3.3 V load | Estimated LDO dissipation | Estimated temperature rise |
|---|---:|---:|
| 200 mA | 0.340 W | 63°C |
| 240 mA | 0.408 W | 75°C |
| 300 mA | 0.510 W | 94°C |
| 500 mA continuous | 0.850 W | 156°C |

These are calculations using a data-sheet thermal resistance, **not measured installed temperatures**. At an assumed 50°C bay ambient, 300 mA would estimate ~144°C junction, leaving inadequate engineering margin to the absolute maximum. A 125°C design target under the same assumptions permits only ~240 mA total. ESP32 radio demand, A4988 logic, both probes and optional sensor modules all consume this budget. Brief peak-current capability is not the same as continuous dissipation.

For a low-duty-cycle controller prototype this can remain a qualification item, as already disclosed, rather than forcing a converter redesign merely to prepare a bare-board supplier project. Record the allowed external sensor load/ambient/radio duty and measure droop and temperature. If sustained high-radio operation or ≥300 mA total at a warm ambient is required, change regulator/package or rail architecture **before purchasing that use-case build**. Do not use thermal shutdown as the design limit. Never power J11.4 from an adapter in parallel with the LDO.

### UART gates, sequencing and DPS ground relationship

- U3 is the transmit buffer: GPIO17 → U3.2 → U3.4 → R15 1 kΩ → J9.2 (DPS RX). U4 is the receive buffer: J9.3 (DPS TX) → U4.2 → U4.4 → GPIO16. Both have GND at pin 3, VCC at pin 5, active-low OE at pin 1, and local 100 nF decoupling. Pin directions/numbering match TI DBV, not merely a generic five-pin package assumption.
- TI permits 5.5 V input operation and specifies Ioff with the device supply at 0 V. Thus a live 3.3/5 V DPS TX is compatible with the buffer input limits when the board is off, subject to actual interface transients. Board TX remains a **3.3 V output**, not a 5 V level-up converter. R15 limits fault/backfeed current but does not establish compatibility by itself.
- R14 = 10 kΩ biases OE high during reset. The corrected revision adds R20/R21 data-input bias (B1 closed in §0). Neither bias nor OE detects DPS power loss or isolates grounds. If firmware has enabled U3 while the DPS loses power, its high output can still feed the DPS input through R15. Required startup/shutdown sequencing and the real DPS input clamp behaviour remain bench interfaces. Ioff at the board's VCC = 0 is not protection for the opposite power-order case.
- J9.1, J1.2, J2.1 and all other board grounds are one common net. No DPS OUT− is explicitly connected on this PCB. Consequently the board itself does not encode a shunt bypass. However a non-isolated common-ground connection is suitable only if the purchased DPS communications ground is compatible with source IN−. Do not bond OUT− to source/system GND through the UART, an oscilloscope or a USB-ground path: DPS variants have low-side current sensing, and published teardown reports also describe low-side output switching. Such a bond can bypass sensing and/or shutdown. Measure the actual IN−/OUT−/UART-ground relationship before attaching the harness; use an isolated interface if it requires separation. The generic DPS name is insufficient to certify this interface.

### A4988 carrier, motor supply and trace connections

Compared actual J14/J15 pad coordinates and nets with Pololu's component-side wiring picture, carrier schematic and dimensions:

- Rows are **15.24 mm apart**, at X59 and X74.24, with 2.54 mm pitch and aligned first pins at Y91. They are not mirrored.
- J14 top-to-bottom is `/EN` tied GND, MS1/MS2/MS3 tied 3.3 V, RESET/SLEEP tied `MOTOR_RUN`, STEP, DIR. J15 is VMOT, GND, 2B, 2A, 1A, 1B, VDD/3.3 V, GND. J16 is coil 1A/1B; J17 is coil 2A/2B. The two coil pairs are not inadvertently mixed.
- The fixed high microstep pins select 1/16 stepping. R11 = 10 kΩ pulls RESET/SLEEP low and dominates the Pololu carrier's 100 kΩ SLEEP pull-up (about 0.30 V when undriven at 3.3 V). R12/R13 give STEP/DIR defined low states. Grounding `/EN` permanently is permissible because RESET/SLEEP inhibit the carrier; it does mean there is no separately controllable enable pin. Observe the carrier wake delay before STEP pulses.
- C10 positive is VMOT at (82,94), negative GND at (87,94). It is **100 µF/50 V**, local to the carrier's VMOT side, not across a coil or logic supply. Pololu recommends at least 47 µF electrolytic near VMOT to damp supply-lead LC spikes. Actual routing reaches VMOT and all phase pads; current paths have the widths/no-via properties in §2. No missing-capacitor or swapped-power-row blocker was found.
- A 50 V capacitor does not raise A4988's 35 V motor-supply limit. The declared 20/24 V protected source is compatible nominally, but real spike/ripple tests, carrier current setting, connector heating and phase-path thermal tests remain mandatory before load qualification. Clone pinout/current-sense resistor and heatsink height must be checked on the actual separately purchased carrier.

### Fan PWM and tach

Q1's actual nets are B/E/C = pads 1/2/3, respectively GPIO26 through R8 = 4.7 kΩ / GND / J3.4. R9 = 100 kΩ keeps its base low when undriven. At nominal 3.3 V the base-drive estimate is ~0.5 mA, appropriate for a roughly 5 mA maximum PWM sink load at a forced gain near 10. This is preferable to assuming MOSFET threshold voltage proves adequate drive. No fan motor current passes through Q1.

J3.1/.2/.3/.4 correctly give GND/+12 V/tach/PWM. The fan remains powered; the collector waveform is inverted relative to GPIO26. At reset the collector is released, so a conforming fan's internal pull-up requests full speed. Tach has R6 = 10 kΩ to **3.3 V**, R7 = 1 kΩ in series into input-only GPIO34: about 0.33 mA pull-up current, not a dangerous 12 V pull-up. For Noctua's two-pulse/revolution tach, RPM = 30 × frequency in Hz.

**Important qualification detail:** Noctua's own PWM white paper specifies 25 kHz (21–28 kHz), ≤0.8 V low, up to 5.25 V open-circuit/5 mA sourced, but also **recommends a CMOS push-pull driver over an open-collector circuit** because weak pull-up current can deform edges. Thus the sink circuit is plausible, not a verified match to the selected Noctua fan. Scope the actual 40 µs-period waveform and speed response across duty range and cable length. If rise time is inadequate, engineer a compatible driven-high stage or qualified pull-up; do not directly expose ESP32 GPIO to a 5 V fan pull-up. This does not prevent bare-controller project preparation, but it must not be reported as tested 25 kHz fan control.

### Sensors, I²C, ADC and TEC enable

- J4/J5 use GND/DQ/+3V3, share GPIO27 and **one** 4.7 kΩ pull-up. Correct for powered DS18B20 probes; this is one shared bus, not two fault-isolated channels. Probe lead colours are not a pinout standard. Cable loading, conversion timing and fault handling remain firmware/bench work.
- J6/J7 are independent INDEX/HOME inputs on GPIO32/33 with 10 kΩ pull-ups, suitable for 3.3 V logic or open collectors. They are not 5 V-tolerant inputs and do not directly power a bare optointerrupter LED with a defined current. The specified optical modules/harnesses must meet those conditions.
- J8 is GND/+3V3/SDA/SCL, with R16/R17 = 4.7 kΩ. Additional module pull-ups appear in parallel. With 4.7 kΩ, the first-order I²C rise-time limits correspond to roughly 250 pF at 100 kHz or 75 pF at 400 kHz (using `tr ≈ 0.8473 RC`); cable/probe loading must be considered. This is not a validated long-cable bus.
- R18/R19 = 100 kΩ/10 kΩ map VMOT to GPIO35/ADC1 as bus/11: 20 V → 1.82 V; 24 V → 2.18 V. Both are sensible ADC input levels with the chosen attenuation/calibration. Thevenin resistance is ~9.09 kΩ; C8 = 100 nF gives ~0.91 ms nominal filtering. R18 dissipates only ~4.8 mW at 24 V. The capacitor is near the divider at Y105, not adjacent to the MCU input at Y65.36; moving it toward the ADC would better filter pickup on the long motor-area route. With VMOT alive and 3.3 V off, this divider can inject limited current into the unpowered MCU input; include that state in rail sequencing/backfeed measurements. It is not a precision voltage monitor or surge clamp.
- GPIO25 → J10.2 has R10 = 10 kΩ to GND. This is a default-low **logic request** only. It is not a DPS5005 enable pin, an onboard TEC switch, a watchdog or independent power disconnect. An external fail-off stage and its own input bias/interlocks are still required. A stuck-high MCU or disconnected external harness is not made safe merely by this board-side resistor. Those controls and future firmware need not be finished to price/prepare the bare controller; unattended thermal operation remains out of scope until they are proven.

## 4. Footprints and manufacturing process

| Item | Independently established | Remaining boundary |
|---|---|---|
| Phoenix 1715721 / C5183929, J1/J16/J17 | Exact Phoenix document identifies MKDS 1,5/2-5,08, **5.08 mm pitch, 0.9 × 0.9 mm pins, recommended 1.3 mm PCB holes**, body 10.16 × 9.8 mm, installed height 13.8 mm, 3.5 mm solder tails. Dimensioned drawing shows the pin line 4.6 mm from the wire-entry face. Actual footprint has 5.08 mm pitch, 1.3 mm holes/2.6 mm pads and the corresponding 9.8 mm body depth/orientation. No terminal-footprint mismatch found. | The small nominal diagonal-to-hole margin is manufacturer-specified, not a reason to invent a larger hole without tolerance review. Confirm finished-hole tolerances and THT process. Full ground-plane connections increase soldering heat demand. Housing support must resist terminal tightening and cable loads. |
| Panasonic EEUFR1H101B / C713402, C10 | Manufacturer's **exact B-suffix product page** independently confirms 100 µF/50 V, Ø8 × 11.5 mm and **5.0 mm lead pitch**. Actual board is D8/P5, 0.8 mm holes. B-formed/taped version must not be replaced using the usual 3.5 mm straight-lead assumption. Series sheet gives nominal 0.6 mm leads. Polarity and nearby placement are correct. | Formed-lead/body tolerance and lead forming/cutting belong to assembly review. 870 mArms and 61 mΩ are ratings at 100 kHz; the latter is impedance, not universal ESR. Motor ripple is not yet qualified. |
| BOOMELE C27438 sockets, J14/J15 | LCSC exact catalogue confirms 1×8, 2.54 mm, 8.5 mm insulation height, 3.2 mm tails, 3 A catalogue rating. Actual board uses 1 mm holes and 1.7 mm pads at correct pitch/row separation. Pololu carrier mating grid independently matches. | Exact socket tail cross-section/tolerance, body width and insertion/mating geometry were **not independently verified from a supplier drawing**: the linked PDF and public EDA endpoint returned HTTP 403. Catalogue pitch is not a completed hole-tolerance or carrier-height check. |
| C49257 1×3, C5116483 1×4, C27985187 1×2 headers | Actual board has the intended pin counts, 2.54 mm pitch and 1 mm holes. Selected catalogue records identify ordinary vertical headers, not a keyed fan connector. | Exact supplier drawings remain unverified; direct linked PDF retrieval failed (403). Do not declare finished fit from the native KiCad name. Obtain drawings/assembler confirmation of maximum tail dimensions, tolerances, body and mating height; change the selection if those cannot be established. |
| U1 module | Module pad table/body/land-pattern documentation agrees with WROOM-32E. Actual thermal pattern has **nine 0.9 mm-square paste lands** and **twelve 0.2 mm plated holes** between them, all GND. This is not a single huge unsegmented paste aperture. | Holes are ordinary through-hole pads open in the masks; do not assume tenting or filled/capped via-in-pad. Agree solder-paste/wicking handling with assembler. Espressif explicitly says base-board EPAD soldering is optional; an intentionally unsoldered EPAD footprint is a possible simplification if this process is rejected. |
| U2/U3/U4/Q1 and passives | Actual pad-net mapping agrees with AP2112 SOT25, TI DBV buffer and MMBT3904 B/E/C assignment. 0603 resistor/capacitor and 0805 bulk-cap footprints match selected package families. | Supplier component-library zero rotations are not established solely by a manufacturer top-view drawing. C15850/C15849 dielectric/effective-capacitance assumptions and Q1 exact vendor electrical limits must remain tied to selected codes, not substituted by name alone. |

**THT drawing and assembly acceptance are still open, not proven defects.** They may be resolved as part of corrected supplier-project preparation, but are fabrication-release gates: obtain an exact drawing or explicit supplier pad/tail/body match for each selected header/socket family. Neither `manualWeld` metadata nor positive stock means JLC has accepted these exact parts on the chosen service.

The 0.2 mm U1 holes imply an 8:1 nominal board-thickness/hole ratio at 1.6 mm. This is a conventional plated-hole process question, not a blind/buried microvia requirement. The twelve holes and segmented paste need explicit acknowledgement in the fabrication/assembly choices. The manufacturing stack remains two-layer FR-4 with top-side SMT and THT; empty backside paste/silkscreen files are not an electrical defect.

The crescent has no mounting holes or explicit panel rails/fiducials. A supplier can add panel handling and panel fiducials; that does not alone require redesigning this prototype. Confirm the curved-board handling/rail choice before final pricing/release. THT tails, socket/carrier height, terminal access, soldering heat and the RF area must be represented in the eventual enclosure fit check.

### Supplier orientation and source-confirmation path

After B1/B2 and the focused recheck, the preparing session should use the **mixed-process** BOM/CPL pair and exact part-code matches. Inspect the supplier placement view against actual numbered PCB pads, not just the board outline or part body. Priorities: U1 antenna and pin 1; U2/U3/U4/Q1 pin 1 and pad numbering; C10 positive lead; J14/J15 first-pin direction; Phoenix terminal entry faces. Confirm all passive positions too. Record any library translation/rotation back into a reproducible export/reconciliation file; a screenshot without saved corrections is insufficient.

Public component pages are `https://jlcpcb.com/partdetail/<C-code>` and `https://www.lcsc.com/product-detail/<C-code>.html`; exact linked data-sheet URLs are preserved in `stock-evidence.json` under `dataManualUrl`. JLC's [KiCad export guidance](https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad) also describes a fabrication-toolkit translation route. A plugin is not a substitute for reviewing its exact mappings. No supplier orientation was claimed verified in this review because no account project was created or uploaded.

## 5. Decision boundaries and handoff

1. **Designer corrections and independent recheck complete:** B1 buffer input bias, B2 centroid translation/reconciliation and routing-class persistence are closed. Use the corrected 54-part build and current hashes in §0; the initial 52-part identifiers/counts are historical only.
2. **Supplier-project preparation is cleared under D25**, retaining the documented THT drawing/process, U1 thermal-land, panel handling and supplier-angle checks. The designer's pending/HOLD status notes may now be updated to reference this conclusion. Owner submits the quote request. This review itself has performed none of those supplier actions.
3. **Before fabrication acceptance:** close exact THT fit and supplier placement/process items; carry the corrected build identity into the supplier project. Do not treat the current native-angle draft files as approved machine setup.
4. **Before powered load/unattended trials:** supply budget/thermal and transients, real A4988 module/current limit, PWM/tach waveforms, DPS logic/ground/power order, sensors, external protections and independent TEC shutdown. No completed application firmware is demanded as a prerequisite for a bare-controller supplier project.
5. **Mechanical fit remains the primary session's separate task.** At the initial review, the existing CAD bays/posts did not fit this crescent. Mount integration is now proceeding separately and has not been assessed by this focused electrical/manufacturing recheck. This review does not duplicate a mechanical blocker for a bench-controller build or assert that nominal bore/fan 2D clearance validates retained installation. Terminal height, socket/carrier stack, underside solder tails and antenna clearance are useful handoff constraints.

## Public references actually consulted

- [Espressif WROOM-32E/32UE data sheet](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf), v2.1: module pinout, straps, EN timing, physical/land pattern and optional EPAD soldering.
- [Espressif module layout guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32/pcb-layout-design.html#general-principles-of-pcb-layout-for-modules-positioning-a-module-on-a-base-board): antenna placement and enclosure clearance.
- [TI SN74LVC1G125](https://www.ti.com/lit/ds/symlink/sn74lvc1g125.pdf), SCES223U, August 2026: pinout, OE, Ioff, input limits and floating-input prohibition.
- [Diodes AP2112 manufacturer document, mirrored by SparkFun](https://cdn.sparkfun.com/assets/1/7/c/5/f/AP2112_Datasheet.pdf), DS39724 Rev. 2-2: pinout, capacitors and thermal limits. Direct Diodes retrieval returned 403; the mirror was actually downloaded/read.
- [Pololu A4988 carrier 1182](https://www.pololu.com/product/1182), linked component-side wiring image, schematic and dimension picture: socket mapping, SLEEP pull-up, supply ranges and electrolytic guidance.
- [Phoenix 1715721 manufacturer document, distributor mirror](https://xonstorage.z8.web.core.windows.net/pdf/phoenixcontact_1715721_apr22_xonlink.pdf), dimensions and drawings pp. 6–7. Direct Phoenix page returned 403; the manufacturer's mirrored drawing was actually downloaded and visually inspected.
- [Panasonic exact EEUFR1H101B page](https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models/EEUFR1H101B) and [linked FR-A sheet](https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1259.pdf): exact 5 mm-pitch part and electrical ratings.
- [LCSC C27438 socket catalogue](https://www.lcsc.com/product-detail/C27438.html): direct catalogue dimensions; exact drawing access failure distinguished above.
- [Noctua PWM specifications](https://cdn.noctua.at/media/Noctua_PWM_specifications_white_paper.pdf) and [microcontroller guidance](https://www.noctua.at/en/support/faqs/microcontroller-guide-pwm-setup-and-rpm-monitoring): indexed technical text corroborated the current-source, frequency, tach and open-collector caveat; no measured waveform is claimed.
- DPS grounding evidence: [DPS5005 build discussion](https://www.eevblog.com/forum/projects/dps5005-based-power-supply/) and [teardown discussion](https://www.eevblog.com/forum/projects/dps5005-portable-mini-lab-psu/25/). These are third-party observations, **not a verified schematic of the owner's future Joy-IT unit**; hence the explicit continuity/power-order qualification requirement.
