# Independent PCB simulation review

Reviewed 2026-10-24, with subsequent fix verification. **Interface R1/R2 and power P1 are now closed:** see the [interface follow-up](#interface-fix-verification) and [power follow-up](#power-fix-verification). Interface and power studies reproduce; circuit failures are exposed and physical qualification remains open. Original findings below preserve their reviewed source revisions and are superseded by the corresponding closure notes.

Initial-pass scope: completed [interface runner](../electronics/sim/interfaces/run.py), [model documentation](../electronics/sim/interfaces/README.md), [report](../electronics/sim/interfaces/results/report.json), generated decks/logs/waveforms, and the actual KiCad XML/checksum inputs. Power simulations and the separate test/bench work were excluded from that pass and reviewed subsequently in the addendum. Context: [decisions](decisions.md) and [KB index](README.md). This review owns only this page; recommendations below are not applied code changes.

## Evidence and reproduction

- Reviewed runner SHA-256: `4535475bddfe11512b7abf7b132e93e3e46206a515f23ea782ff31db0d5939a8`.
- All four source hashes in `results/report.json:5–9` match the actual runner, XML, schematic and PCB. The three PCB-source hashes also match `electronics/pcb/checksums.json:2–3,16`.
- Independently reran all **67 cases** using the existing `cat-feeder-spice:local` image, `--network none`, current UID/GID, repository mounted read-only and session scratch mounted writable. No packages installed. Tool reports **ngspice-39**; 67 is the case count, not the ngspice version.
- Completed rerun report equals the published JSON exactly. All **67/67 decks, 67/67 waveforms and 67/67 solver logs are byte-identical**. No saved solver log matches warning, failed, singular, timestep-too-small or aborted diagnostics.
- Case counts: bus 16, ADC 14, bias/UART/EN 13, fan 24. These are actual DC/transient solver outputs; the resistor/RC closed forms provide cross-checks rather than replacing execution.
- Scratch evidence lives under `$TMPDIR/interface-review-rerun` and `$TMPDIR/interface-review-mutated-divider` in this review session. Scratch is temporary; durable baseline evidence is the linked interface results. The completed rerun preceded the deliberate failure-injection checks below.

## Findings requiring code/report handling fixes

### R1 — Medium: failed rerun can leave an apparently successful old report

**References:** `run.py:47–64,247–265`.

The output directory is reused, but `report.json` is replaced only after all studies finish. A timeout, failed analytic assertion, stale-input rejection or other exception leaves the previous PASS report and CSVs in place, potentially alongside partially overwritten case artifacts. Source hashes cannot expose this when the same source encounters a new execution failure.

**Reproduced:** after the successful scratch rerun, injected `subprocess.TimeoutExpired` at the solver call and called `main()` with that same output directory. The exception propagates, but the previous report remains byte-identical and still says `PASS: all solver runs, finite-output checks and analytic oracles passed`. This does not conceal any failure in the presently published completed run; it is a failure-handling defect for future runs/readers.

**Improve:** create a fresh run directory with an explicit run ID/status, mark the requested run RUNNING before input validation, then publish COMPLETE/FAILED status atomically. Preserve prior successful evidence separately rather than leaving it at the new run's success path. At minimum invalidate the old summary before work starts and write a failure summary on exceptions. Exercise an interrupted rerun against a previously successful output directory.

### R2 — Low: ADC transient oracle hard-codes the present divider ratio

**Reference:** `run.py:125–146`, especially `24 / 11` at line 145.

The deck and theoretical time constant use XML-derived R18/R19, but the 63.2% crossing threshold assumes a 100 kΩ/10 kΩ divider. It is correct for today's inputs. After an intentional reviewed ratio change, the solver can be correct while this oracle rejects it or measures the wrong crossing.

**Reproduced:** in memory only, used a `Circuit` subclass returning 120 kΩ for R18, leaving other values unchanged; the eight DC cases complete and the first transient assertion fails against the unchanged `24/11` threshold. No design or XML was modified.

**Improve:** derive the target as `24 * bottom / (top + bottom) * (1 - exp(-1))`. A changed-ratio regression is meaningful here because it checks an independent invariant, not today's fixed number.

## Verified calculations and model interpretation

### ADC DC, filter and hypothetical MCU-off clamp

**References:** `run.py:124–163`; `report.json:224–334`; XML component definitions at `schematic-netlist.xml:153,855,873`, BUS_SENSE nodes at line 1325.

- XML actually supplies R18 = 100 kΩ, R19 = 10 kΩ, C8 = 100 nF; both endpoints of each passive are checked by `Circuit.value()`.
- All four independent ±1% resistor combinations are simulated at both 20 V and 24 V. The 24 V range is **2.142470694–2.221814849 V**, consistent with `Vbus*R19/(R18+R19)`. These are resistor-tolerance corners, **not ±1% ADC/system accuracy**; divider ratio error is approximately −1.80%/+1.83% before silicon/reference errors.
- Thevenin resistance is **9.090909 kΩ**. C8 = 80/120 nF gives analytic τ = **0.7272727/1.0909091 ms**. Waveform crossings yield **0.727273451/1.090909663 ms**; agreement is much tighter than the 0.5% assertion. R tolerance is not combined with C tolerance in these transient cases; documentation describes C-only sensitivity correctly.
- The source edge is at 1 ms, and the measured time subtracts that delay correctly. The 1 ns finite edge introduces negligible error here.
- MCU-off current prediction correctly includes divider loading and the assumed clamp's 10 Ω incremental resistance: **0.133853–0.206773 mA**. The return is forcibly held at 0 V. This is possible injection into an assumed clamp, not a simulation of rail charging/backpower, actual diode behavior or damage limits.

### Sensor bus timing and I²C rise limits

**References:** `run.py:85–120`; `report.json:14–222`; `README.md:28–29,48–54`; XML R3/R16 definitions at lines 585/819 and ONEWIRE/I2C_SDA nets at lines 1467/1435.

- The sink starts low and releases at approximately **2.0005 µs**. Sampling is at **15 µs from slot start**, leaving approximately **13 µs** of rise time, not 15 µs after release. The closed-form oracle uses that correct elapsed time and the nonzero 20 Ω sink's starting voltage.
- The 30–70% exponential rise formula `ln(7/3)*R*C` is correct. Standard/fast-mode limits of 1000/300 ns are applied to this rise interval, not to the 15 µs sample.
- Correct exposed failures: **3/8 1-Wire cases**, **2/8 I²C standard-mode cases**, **6/8 I²C fast-mode cases**. I²C 100 pF already misses 300 ns; 400 pF misses 1000 ns.
- **Important marginal pass:** 1-Wire, 2 nF, −1% R reaches 2.475 V at **14.861423 µs**: only **0.138577 µs** before the chosen sample. At +1% R it crosses at **15.122044 µs**, failing as reported. The apparent passing 2 nF corner has almost no scheduling/input-threshold margin. This is a genuine design-interface constraint under the assumptions, not a solver problem.
- Improve the criterion wording (`run.py:117` / JSON rows) to explicitly say “15 µs from slot start; release at 2 µs.” Record crossing time and sample margin, and sweep the intended earlier sample/jitter budget. A sample at the latest modeled instant cannot establish robust protocol timing.
- Bus initial DC is already low, rather than a falling edge from a precharged cable at slot start. For the current maximum 5 nF, the approximately 20 Ω discharge time constant is 0.10 µs, so 2 µs low makes that simplification reasonable. It is not a demonstrated sensor pull-down or full read/write/reset transaction.
- Only SDA is exercised. XML R17/SCL is also 4.7 kΩ (`schematic-netlist.xml:837,1430`), but actual SCL capacitance/stretching is not validated by these cases. The README explicitly scopes this to SDA RC.

### Fan PWM phase, generic transistor and current assumptions

**References:** `run.py:216–243`; `README.md:35–38,64–71`; `report.json:431–719`; saved `fan_R10000_C2000p_B100_T25/model.cir:2–19`.

- Source period **40 µs = 25 kHz**. The GPIO is low/released around 160–180 µs, high/sinking around 180–200 µs. Sampling at **170/190 µs is correctly phased**; the inversion has not been mistaken for a failed transistor. Finite 10 ns edges make exact threshold duty approximately 50.025%, immaterial to this midpoint screen.
- Actual Q1 XML pin order is base/emitter/collector = FAN_BASE/GND/FAN_PWM_OD; the code explicitly checks it before constructing the ngspice collector/base/emitter instance. R8/R9 are really 4.7 kΩ/100 kΩ (`schematic-netlist.xml:531,675,693,1364,1373`).
- **8/24 high midpoint failures are correctly reported**, all at 2 nF and 10/100 kΩ pull-up. Sink midpoints are **0.019600–0.085598 V**. These are generic-model results, not vendor-qualified MMBT3904 limits or failures proven for the chosen fan.
- Independent waveform extraction: BF100/25°C, 10 kΩ/2 nF rises through 2.1 V **10.466473 µs after 160 µs**, missing the half-pulse strobe; 100 kΩ/100 pF crosses after **5.884464 µs**, despite passing its midpoint; 100 kΩ/2 nF never crosses within that released half-cycle. A passing midpoint therefore does not establish duty/edge fidelity. Previous-cycle midpoints closely match the reported final cycle for these sampled cases.
- At the BF100/25°C sink midpoint, inferred base current `(3.3−Vbase)/R8−Vbase/R9` is approximately **0.543–0.553 mA**; collector pull-up current spans **4.930 to 0.0523 mA** across 1.05–100 kΩ. Thus the transistor is strongly saturated, particularly under weak pull-ups. BF100/300 is a sensitivity sweep, not a meaningful vendor worst-case bound on saturation storage; fixed TR/TF/junction capacitances and ideal GPIO drive can dominate release timing.
- Improve: retain GPIO/current vectors, measure threshold-crossing delays and effective output pulse width, sweep intended duty extremes, and explore storage/drive assumptions as explicitly hypothetical sensitivities. A current-source pull-up scenario is also useful because a real fan need not contain the assumed resistor. Actual loading, storage and timing require a validated model or oscilloscope measurements; no PCB redesign is implied.

### Reset leakage, UART clamp and EN response

**References:** `run.py:166–212`; `report.json:336–429`; `README.md:32–34,59–63`.

- Leakage polarity is correct: a positive current from signal to ground pulls a pull-up down; negative current injects into a pull-down and raises it. The +1% R corner is adverse in both cases. Ohm-law cross-checks and all six stated **assumed 2.0/0.8 V** screening outcomes are correct: high nodes **3.2495/3.1889 V**, low nodes **0.0505/0.0101/0.101/0.101 V**.
- Those thresholds and 1/5/11 µA budgets are explicitly exploratory, not a validated inventory of all MCU/buffer/module worst-case currents. The actual high results also exceed 0.75×3.3 V, but that does not establish a full reset/power-ramp guarantee.
- Assumed carrier 100 kΩ pull-up plus R11 10 kΩ produces **0.30 V** correctly. Carrier pull-up tolerance, reset leakage and internal MCU pulls are not swept. No firmware reset behavior is executed.
- Enabled DPS-off UART: `(3.3−Vclamp)/(20+1000+10)` predicts **2.91262/2.52427 mA**, matching the solver apart from the stated small shunt leakage. Disabled model has zero **clamp** current, not necessarily zero leakage everywhere: its 1 TΩ source and 1 GΩ shunt leave the node below the artificial clamp threshold. Real disabled-output/Ioff leakage and DPS clamp topology are not modeled, so the zero cannot certify isolation.
- EN's measured **11.090355/16.635533 ms** to 75% is consistent with `−ln(0.25)*R1*C5` at ±20% C. This confirms ideal-rail RC behavior only.

## Reporting/provenance improvements and hardware boundaries

1. **Keep solver and circuit outcomes separate.** Current `execution_status`/`circuit_status` (`run.py:257–263`, `report.json:2–3`) and README make the distinction correctly. Add machine-readable criterion counts and failed case IDs so downstream summaries cannot reduce the entire report to its PASS prefix. There are **19 failed criterion evaluations**: 3 one-wire + 2 I²C standard + 6 I²C fast + 8 fan; I²C criteria overlap, so this is not a count of 19 distinct circuits. Explicit UNQUALIFIED clamps should remain unqualified rather than acquire invented pass limits.
2. **Keep provenance precise.** This is a selected-subnetwork model whose passive values/endpoints come from the XML, with explicit Q1 pin checking. It does not regenerate a full SPICE netlist from PCB geometry, model parasitics, or independently prove XML-to-layout consistency merely by hashing. The current documentation does not make those stronger claims. Adding per-case artifact paths and hashes would make the saved waveform-to-summary chain easier to audit; ADC/bias case labels are presently reused across parameter variants.
3. **Do not present arbitrary sweeps as guaranteed worst-case coverage.** Generic BJT temperature/BF sweeps, ideal rails/GPIO, hypothetical grounded clamps, arbitrary leakage budgets and lumped cable capacitance are disclosed. The outstanding severe uncertainties are actual power-off injection/backpower behavior, real fan pull-up/storage/edge behavior, and the complete bus load/timing margin. Bench evidence or authoritative device bounds must resolve those; fixing the runner cannot do so.
4. **Useful focused follow-ups:** interrupted-run status test; changed-divider oracle test; explicit failed-corner summary checks; waveform pulse-width/crossing checks; sample-jitter/capacitance sensitivity; actual-device leakage/threshold budgets when available. These recommendations concern coverage; they are not a review of the concurrently developed test suite.

**Disposition:** accept the present interface numbers as reproduced conditional simulations. Fix R1 before relying on unattended repeated-report collection, and R2 before changing divider ratio. No hidden circuit PASS, wrong fan strobe phase, wrong 1-Wire 13 µs rise interval, incorrect current-source sign, fabricated vendor model or claimed ESP32 firmware execution was found in this reviewed revision. Hardware qualification remains open for the explicitly identified interfaces.

## Power, regression and bench addendum

Second pass, 2026-10-24, after those agents completed. Reviewed [power runner/model contract](../electronics/sim/power/README.md), [power findings](pcb-power-simulation.md), [electrical regression implementation](../electronics/tests/netlist_checks.py), [tests](../electronics/tests/test_electrical.py), and [bench plan/template](../electronics/bench/README.md). **Frozen revision A remains the input.** No `electronics/revb/` work was inspected, and no interface implementation or pending interface fixes were re-reviewed during this pass.

### Reproduction and source identity

- Ran the entire power runner in `cat-feeder-spice:local`, network disabled, repository read-only, writable session scratch only. **308 distinct transient circuits, 36 thermal corners and nine current limits reproduce.** The two representative VMOT reruns make 310 normal-run solver invocations, not 310 distinct transient models.
- `summary.json`, `provenance.json`, `model-hashes.json`, all four numerical CSVs and `vmot-worst.svg` are **byte-identical** to published results. So are **308/308 model decks, 308/308 logs and 6/6 compressed retained waveforms**. Every source hash in power provenance matches the actual input. Container ID matches `sha256:48cf511518c3085a51e342c6076d2e8c81d415f469a1da941c59c97baafc9b91`; Python 3.12.14, ngspice 39.
- Independently ran **all five power integrity tests** and **all 41 electrical regression test methods** successfully in the read-only container. The electrical suite comprises five artifact tests, nine requirements tests and 27 electrical-mutation methods; the latter contain **29 fault cases**, with **four additional provenance-tampering subcases**. Counts in the README are accurate, but are not additional test-method totals.
- All 13 physical cases B01–B13 are `NOT_RUN`, with empty measurements/evidence, `overall_status: NOT_RUN` and firmware `NOT_IMPLEMENTED`. No physical execution is represented by either software test count.
- Scratch: `$TMPDIR/power-review-rerun`, `power-review-integrity`, and `power-review-publication-failure`. A second full power run was deliberately subjected to late publication failure as described below; the reproduced normal-run evidence was obtained first.

Reviewed source anchors (SHA-256):

| File | Digest |
|---|---|
| `electronics/sim/power/run.py` | `a1299742707ef37e89c0d978f82f1ad14315dfc09cf76b899c9d3c523b2435d3` |
| `electronics/sim/power/test_run.py` | `f0195d5434936725fa6fa4f80caec7a0a5787dc16420936b5f41da0d985706e1` |
| `electronics/tests/netlist_checks.py` | `005cdcf1c9707860610320ec88f7c93e5f7d80d5fa1b04741d060a11bb0582c8` |
| `electronics/tests/test_electrical.py` | `274e5cecddee612734dd816cef3d8209c369f4d3624495df76be8a089e0e3a93` |
| `electronics/bench/README.md` | `f1368103deea13f9a825aabd21b41441f934676b953823ed0fb2d571d9c41a04` |
| `electronics/bench/results-template.json` | `94c7289d53dcdc64e1cc86607e9379bd11ae1ae50373b87c46b77239d6403a09` |
| `kb/pcb-power-simulation.md` | `3ceb9010189506e365a21414d362f4bcca902ea3f16646cac63d05201342db8f` |

### P1 — Blocking report-integrity defect: late error writes suite PASS

**References:** `electronics/sim/power/run.py:329–330,349–370`; `electronics/sim/power/test_run.py:46–53`.

The summary starts FAIL, then is changed to PASS **before** `model-hashes.json` and `summary.json` are published. The exception handler only adds `error`; it does not restore FAIL. An artifact-publication error can therefore return process exit 1 while publishing `suite_execution: PASS` with an error attached. This contradicts the intended failure-report contract even though normal-run engineering failures remain correctly exposed.

**Reproduced with real solver runs:** wrapped `write_json()` in memory to raise `OSError('injected artifact publication failure')` only for `model-hashes.json`; otherwise ran the full unmodified model sequence in a fresh scratch directory. Result: stderr reports `Power suite FAIL`, return value **1**, but the persisted summary says **`suite_execution: PASS`** and contains the injected error. No PCB or source edits were needed.

**Required fix:** explicitly set `summary['suite_execution'] = 'FAIL'` on every caught failure, and publish success only after required artifacts complete. Use atomic summary replacement and include failure stage/run identity. Add a late-publication-error regression; the existing top-level test mocks only the early `source_checks()` failure and consequently cannot catch this defect. If the output medium itself is unwritable, retain nonzero exit and do not promise that a FAIL file can always be written.

**Related interrupted-rerun gap:** `main()` does not write RUNNING/invalidate the old summary before work, and catches `Exception`, not `KeyboardInterrupt`. Injecting `KeyboardInterrupt` in `source_checks()` while reusing the successful scratch output leaves its old PASS summary byte-identical. An interrupt during a later case could leave mixed artifacts. Mark the new run in progress before validation, or use fresh per-run directories plus an atomic completed-run pointer. Interruption tests should explicitly distinguish the previous completed run from the current failed/aborted attempt. This is not evidence that the published completed baseline is stale.

**Disposition:** P1 blocks trusting power JSON alone as an unattended run-completion signal. It does **not** invalidate the independently reproduced numerical baseline or justify changing the frozen PCB.

### Mathematical and engineering assessment

#### Thermal calculations — correct estimates with appropriately disclosed limits

**References:** power `run.py:258–280`, power `README.md:36–51`, `pcb-power-simulation.md:29–69`.

- Independently recomputed all rows using `(VIN−3.3)*Iload + VIN*80 µA` and `Tj=Ta+184*Pd`: exact agreement at stored precision. Inserting each nominal derived current ceiling back into the thermal equation reaches 125°C within **1.5×10⁻¹⁴°C** numerical roundoff.
- **18/36** corners exceed the 125°C target. At 5.25 V/50°C the ceiling is **208.814716 mA**, or **203.645259 mA** with the stated −1.5% output sensitivity. At 5 V/50°C, 240 mA gives **125.1456°C**, correctly FAIL; rounding it to “about 240 mA” in the bench plan is explicitly an estimate, not a qualified setting.
- The 229.48°C extreme is algebraic over-budget evidence, not a physically sustained operating temperature. The documents correctly identify θJA as a reference package value, not installed-board measurement, and do not infer burst duty, shutdown behavior or a 600 mA board thermal rating. Nominal VIN is explicitly at U2, separate from source-wire dissipation.
- No thermal-model code bug found. Actual board thermal resistance, ambient, output tolerance, quiescent-current variation and sustained load remain hardware/model uncertainty rather than numerical defects.

#### VMOT RLC — valid terminal-voltage solution and meaningful independent checks

**References:** power `run.py:147–206`, power `README.md:76–93`, `pcb-power-simulation.md:98–127`.

- State equations are `dVc/dt=I/C`, `dI/dt=(VIN−Vc−(Rwire+ESR)*I)/L`; the measured VMOT terminal is **`Vc+ESR*I`**. Code includes ESR in damping and again correctly in the terminal voltage, rather than accidentally comparing the ideal capacitor voltage to 35 V. Underdamped, critically damped and overdamped closed forms are consistent with these equations.
- Independently integrated those state equations using a separate standard-library RK4 implementation (10 ns step, 2 ms span; no runner/oracle import). For worst `vmot_099`, peak is **43.278069264 V**, versus ngspice **43.278012826 V**: **56.4 µV** difference. For heavily damped `vmot_080`, both peak at **20.000000 V** to numerical precision. The independent integration uses an ideal connection step; the 1 ns source edge and output-grid sampling explain small peak differences.
- All **17/162** ≥35 V failures are retained. The reported maximum whole-trace analytic disagreement **2.366570 mV**, lossless **47.999994606 V** peak and charge oracle **3.103931275 V** reproduce. The source-edge midpoint correction is appropriate at the stated tolerances.
- 61.03 A inrush is an ideal-source sensitivity, not an assertion about the purchased supply or capacitor surge capability. Catalogue impedance is explicitly distinguished from broadband ESR. Omitted driver ceramics, divider loading, contact dynamics, current limiting, motor regeneration and layout resonances are disclosed. No TVS/clamp protection or complete motor-drive simulation is falsely claimed.
- Small runner coverage gap: representative reruns at `run.py:197–204` bypass the normal log/schema/finite/end-time validator and check only return code before compression. Their saved traces reproduce now, but ngspice can return zero on some failed analyses. Prefer the same validation path for retained reruns and verify their extrema agree with the first run; otherwise a plot/retained trace has a weaker integrity guarantee than its CSV.

#### Regulator transients — valid behavioral experiment, not AP2112 prediction

**References:** power `run.py:209–255,283–293`, power `README.md:53–74`, `pcb-power-simulation.md:71–96`.

- The behavioral branch draws the same pass current from VIN that it delivers to output; a separate 80 µA branch adds input consumption. Input/output storage and assumed ESR are actual circuit elements. The initial checks correctly account for 100 mA load, finite controller gain (3.29 V initial output) and source-resistance drop. The 1 GΩ output shunt causes only negligible nanamp-scale deviations within the explicit checks.
- Nominal output storage is **20.4 µF**: C2+C4 plus directly connected C3/C6/C7/C9. The hard-coded aggregate is guarded by exact-value/connectivity checks; changes correctly require re-review. The separate charge test checks `ΔV=IΔt/C`, including half the 1 ns rising edge.
- **97/144** assumed-rail failures reproduce: **36/72 at 500 mA**, **61/72 at 700 mA**. Global extrema **0.207584708–5.189991997 V** agree with the written report. The 700 mA load and 800 mA ceiling are labeled overload/sensitivity rather than guaranteed ratings.
- The fixed 10 A/V gain, first-order lag, finite storage and saturation make slow cases strongly underdamped; large droop/overshoot is therefore a property of this chosen controller. Varying lag does not bracket a real AP2112's complete compensation, current limit or dropout behavior. The documents already say this explicitly and distinguish solver verification from a validated silicon model.
- Initial KCL and a separate charge oracle validate implementation pieces, not the full dynamic control response. Useful next verification is transient branch-current/charge balance and a step-size convergence check on one extreme and one near-threshold case. Actual loop response still needs a validated device model or bench load steps; do not turn these arbitrary sensitivity parameters into an AP2112 pass/fail prediction.

### Regression tests — substantive, correctly scoped design checks

**References:** `electronics/tests/netlist_checks.py:33–45,60–127,137–270,295–321`; `test_electrical.py:16–85,88–284`; tests `README.md:13–31,51–87`.

- Requirements use actual exported component pins and independent interface contracts; they do not import or execute the PCB generator. All **85 frozen-manifest artifacts** are verified against a pinned manifest identity, with separate schematic/board anchors. Consequently unrelated edits elsewhere in the frozen manifest can stop this revision-A suite by design; new revision-B work is not implicitly covered.
- The PCB parser compares **179 unique component/pin nodes**, checking consistent net assignment across repeated EPAD lands, and compares 54 footprint references/values to XML. Carrier row spacing/pitch/orientation checks use actual placed-pad coordinates. This adds structural evidence beyond hashing, but does not simulate copper paths or repeat ERC/DRC; the README states that boundary correctly.
- The 29 electrical mutations exercise semantic rules directly, without hashes or generator-produced BOM data as the rejection mechanism. They catch meaningful swapped pins, missing bias, incorrect pull-up rails, divider changes and capacitor polarity. The signal-renaming positive test also confirms endpoint-based requirements rather than accidental dependence on human-readable signal names.
- ADC checks are legitimate frozen-revision assertions, not a broad ADC accuracy model. Unlike the earlier interface oracle R2, fixed `24/11` in `netlist_checks.py:256` follows explicit requirements for **exactly** 100 kΩ/10 kΩ at lines 252–253; rejecting a changed ratio is intended here.
- Motor pull-down arithmetic correctly chooses +1% board resistance and −5% assumed carrier resistance to maximize reset voltage. External carrier tolerances and MCU/high-Z behavior remain assumptions. Fan tests prove topology, not fan compatibility or reset-speed measurements.
- No blocking regression-suite defect or inflated physical-test claim found. Mutation coverage is selected, not exhaustive. Useful additions are board-side pad-net/row-coordinate mutation checks and repeated-EPAD inconsistency cases, since current fault injection primarily targets XML. These would verify parser/geometry rejection paths rather than duplicate the existing positive pad-parity check.

### Bench plan — honest unexecuted procedure with unresolved acceptance budgets

**References:** bench `README.md:3–17,82–95,106–124,147–179,210–272`; `results-template.json:1–48`.

- The plan cleanly separates unpowered inspection, ROM identification, instrument fixtures, future test firmware and external fail-off qualification. No invented firmware commands or executed firmware/hardware results appear. ESP32 ROM identification is correctly not treated as application validation.
- Power-order injection, DPS ground/shunt compatibility, fan pull-up/edge measurements, probe stale/CRC handling, carrier current/VMOT spikes and ADC-off injection are covered as future trials. External TEC de-energization explicitly requires a real external stage/interlocks and measured residual power, not an acknowledged UART command or J10's default bias alone.
- Null acceptance criteria in the template are appropriate for an unexecuted template but do not establish any pass basis. Firmware timing, fan pulse-width/high-level margins, injection-current limits, temperature uncertainty and fail-off response budgets must be filled before those cases can pass. The prose already requires this; a future result-record validator should reject PASS rows missing criteria, measurements, evidence and applicable firmware/instrument identities.
- Minor wording clarification: connector table `README.md:52` calls J1 “protected 20–24 V nominal,” while the power study establishes **no proven onboard clamp**. Define that as an external fixture/supply requirement rather than a protection property of revision A. Later B10 text correctly warns that 100 µF/50 V storage does not protect the 35 V driver by itself.

### Addendum disposition

**The published normal-run power numbers and all 41 regression tests are independently reproduced; their limits and unperformed hardware tests are honestly labeled.** Thermal, VMOT and behavioral-LDO FAIL counts remain visible alongside execution PASS. **Fix P1 before consuming power JSON as a reliable completion/failure record.** Retained-rerun validation, late/interrupted-failure coverage and future bench-result validation are the concrete additional improvements. No result in this addendum qualifies revision-A hardware or the unreviewed revision-B redesign.

## Interface fix verification

2026-10-24 follow-up, **completed interfaces only**; concurrent power changes and revision B were not inspected. Reviewed runner SHA-256 `8f32361b3782bc57edac3a2e1a4da23fe567e07ed263847b48a5260724169d1e`; integrity-test SHA-256 `74307753f34934fcde9319bca358f75d83ab1befaa8c5de6bd89ba7c2957ae35`.

- **R1 closed for the documented invocation.** `interfaces/run.py:265–268,307–330` atomically publishes a fresh run ID/RUNNING before input validation, publishes COMPLETE only after studies/CSV writes, and publishes FAILED on caught exceptions including KeyboardInterrupt. The real child-process SIGKILL test confirms RUNNING persists after the publication barrier. Stale waveforms/logs are removed before each solver call; malformed, nonfinite, nonmonotonic and truncated transients are rejected (`run.py:47–78`). Consumers must require COMPLETE; old case directories can remain during a failed run, as documented.
- Independently injected an additional **final COMPLETE replacement failure** using the already reproduced result as the study fixture. The OSError propagates and the persisted report is **FAILED/FAIL with no results**, confirming the late-publication status defect previously found in power is absent from this interface path. This extra check mocks study execution, not the atomic file operation/error handler.
- **R2 closed.** `run.py:157–164` derives the transient threshold from `24*bottom/(top+bottom)`. The changed-120 kΩ test (`test_run.py:131–143`) executes all **14 real ADC ngspice cases**, verifies the changed time constants and approximately **24/13 V** final output, without editing frozen XML.
- Independently reran **all 67 baseline cases and all 15 integrity tests** in the network-disabled image, repository read-only, scratch under session TMPDIR. All pass. Baseline report matches exactly apart from run UUID/timestamps; **67/67 decks, waveforms and logs are byte-identical**. All reported source hashes match. Scratch reproduction: `$TMPDIR/interface-fix-review`.
- **19 failed evaluations out of 63 confirmed**, with failed case IDs and overlapping I²C criteria explicitly retained (`run.py:271–281`, README lines 92–97). Hypothetical clamps remain UNQUALIFIED. Slot-start crossing/margin fields reproduce **+0.138577/−0.122044 µs** for the two 2 nF resistor corners; no hardware success is implied.

**Disposition: interface R1/R2 fixes verified; no new blocking issue found in this follow-up.** Original model/hardware limitations remain. Power P1 status awaits its separate completed-code review.

## Power fix verification

2026-10-24 follow-up; completed power code only, no revision-B scope. Reviewed runner SHA-256 `3dce0ff2210c85e0bc5c3cd6b9b21af83e515e6e036c4b91b74e46ca540b87a9`; integrity-test SHA-256 `3f48b67991429c9e0c6c44eb2ccb9e6df97852908f4f8ffe90ef548eecc150e8`.

- **P1 closed.** `power/run.py:37–51,355–424` atomically publishes RUNNING before source checks, retains run ID/stage, and publishes COMPLETE/PASS only after artifact publication. Late exceptions explicitly force FAILED/FAIL; KeyboardInterrupt produces ABORTED/FAIL and exit 130. SIGKILL after the initial publication leaves RUNNING. Same-directory flushed/fsynced temporary JSON plus atomic replacement avoids partial JSON. The README correctly requires single-writer output, final-status/run-ID gating and honoring nonzero exit when the output medium cannot accept a failure record.
- **Independently reran all 12 integrity methods: PASS**, in the network-disabled image with read-only repository and session scratch. Coverage includes both late publication failures **after all actual solver runs**, real-child SIGKILL immediately before final publication, KeyboardInterrupt, failed atomic replacement, unwritable failure reporting, six malformed/stale retained-output variants and real-solver peak disagreement. Thus this follow-up exercised three complete model sequences through the failure tests; it did not need another separate normal 308-case run. Transcript: `$TMPDIR/power-fix-review-integrity/test-integrity.log`.
- **Retained-waveform gap closed.** First solves and representative reruns now share `solve_deck()` (`run.py:143–174,226–230`): stale data removal, solver/log, row shape, finite values, end-time and monotonic-time checks precede compression. Retained VMOT peak voltage **and current** must match the first solve within 1e-9 relative/absolute tolerance. Independently extracted peaks from both published retained traces (`vmot_062`, `vmot_099`) exactly match their CSV rows.
- Published summary/provenance run IDs agree; all source and **308 model hashes** match. Four numerical CSVs, **308 decks, 308 logs and six retained waveforms** remain byte-identical to the earlier independently reproduced baseline. **308 distinct circuits / 310 normal-run solver invocations** is correct. Summary remains COMPLETE/PASS for execution, with tested envelope FAIL and unchanged **18 thermal / 17 VMOT / 97 behavioral-LDO** failed corners; physical tests remain NOT PERFORMED.

**Disposition: publication blocker P1 and retained-rerun validation finding verified closed; no new blocking issue found.** Earlier model assumptions and hardware qualification limits remain unchanged.
