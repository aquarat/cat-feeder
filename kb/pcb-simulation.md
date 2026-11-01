# PCB operating simulation and test results

2026-10-24. **Electrical models and regression tests have now been executed.**
This supersedes the earlier statement that only ERC/DRC and mechanical checks
had run. No assembled PCB or application firmware has been tested.

## Reproduce

```sh
bash electronics/sim/run.sh
```

The [runner and model documentation](../electronics/sim/README.md) describe the
network-disabled ngspice container and read-only reviewed design inputs. Logs,
numeric results and model decks are under `electronics/sim/`; source hashes and
tool versions are recorded. The supplier's saved design remains the reviewed
54-part revision. These experiments do not upload replacement manufacturing files.

## Executed scope

| Work | Result and meaning |
|---|---|
| Actual-netlist/PCB regression suite | **41 tests pass**, including 27 injected electrical faults and four provenance-tampering cases; checks all 179 XML nodes against PCB pads and all 85 frozen artifacts |
| Interface study | **67 ngspice DC/transient cases**, with RC/divider closed-form cross-checks; **15 runner-integrity tests pass**, including 14 additional real ngspice changed-divider cases; several assumed cable/power-order corners fail their operating criteria |
| Power study | **308 distinct ngspice transient cases**, plus 36 analytical thermal corners and nine nominal load ceilings; twelve simulator/oracle/error-path integrity tests pass |
| Physical bring-up | **13 planned cases, all NOT_RUN**; firmware NOT_IMPLEMENTED |

The simulation harness completing successfully means its calculations and
solver checks ran correctly. **It does not mean the PCB passed every operating
condition.** Exact model parameters, failed rows and assumed external conditions
are retained in the [interface results](../electronics/sim/interfaces/README.md)
and [power study](pcb-power-simulation.md).

### Runner review follow-up — R1/R2

The [independent review](pcb-simulation-review.md) records the original findings
and verifies R1/R2 and the later power-publication findings closed. R1 is addressed by atomic
RUNNING publication before source validation, FAILED publication on exceptions,
new run IDs, stale waveform deletion and invalidation of grouped CSVs/plots.
Only COMPLETE permits consumption. Tests verify timeout and KeyboardInterrupt
replace an old PASS with FAILED, and an actual child-process SIGKILL leaves
RUNNING. The final console summary's out-of-scope `data` reference is corrected,
and successful completion/return is tested. Plotting rejects incomplete reports.

R2's ADC crossing threshold now derives from XML-sourced R18/R19. A fixture
changes R18 to 120 kΩ **in memory only** and passes all 14 ADC ngspice cases,
including independent time-constant/final-voltage checks. Other integrity tests
reject stale, truncated, nonmonotonic, malformed/nonfinite solver output and
warning/nonzero-exit results; exact baseline criterion counts and 1-Wire timing
margins are verified.

The unified Docker run completed with **68 tests passing** (41 PCB + 15
interface + 12 power), **375 baseline solver cases** (67 interface + 308 power),
and **14 additional changed-divider solver cases**. Deliberately invalid solver
inputs are error-path tests, not modeled operating cases. All **85/85 frozen
artifact hashes match**. The [execution log](../electronics/sim/run.log) records
the final run. Power integrity coverage now includes late publication errors,
interruption and retained-waveform completeness/peak checks. This is verification of the legacy `electronics/pcb/`
revision, not the new `electronics/revb/` integrated PD/motor-controller design.

The machine-readable interface summary exposes **19/63 failed criterion
evaluations**: 3/8 1-Wire, 2/8 I²C standard-mode, 6/8 I²C fast-mode and 8/24 fan;
the 15 ADC/reset-bias/carrier-reset evaluations pass. Criteria overlap and
hypothetical clamps remain UNQUALIFIED. This is not a whole-board PASS.

## Findings that affect the build

### 1. The 3.3 V regulator needs a measured load/temperature budget

Using the AP2112 SOT25 reference θJA of 184°C/W and a 125°C design target, the
calculated total continuous load ceiling at 50°C ambient is **239.5 mA at 5.0 V
input**, falling to **208.8 mA at 5.25 V**. At 5.25 V/50°C, a nominal 200 mA
load leaves only 3.2°C of modeled junction margin. This covers ESP32, carrier
logic and all sensors combined. Actual board thermal resistance is unmeasured.

**18/36 thermal corners fail** the 125°C target. A sustained 300–500 mA warm-bay
requirement needs a different regulator arrangement or proven lower dissipation
before that build. The IC's 600 mA headline does not establish that thermal budget.

Regulator load-step simulations deliberately use assumed response dynamics:
they are useful sensitivity tests, **not validated AP2112 transient predictions**.
Their 97/144 failed rail-envelope cases cannot be interpreted as a real-device
failure rate or a proven worst-case bound.

### 2. Motor-supply ringing needs damping/clamp qualification

With C10's actual 100 µF nominal value and assumed lead impedance/ESR corners,
**17/162 connection transients exceed 35 V**, the A4988 maximum. The worst
modeled 24 V case reaches **43.28 V**; a representative more-damped case reaches
27.08 V. The independent RLC solution agrees with the simulated waveforms.

These scenarios assume an ideal source and an abrupt connection; wiring
inductance, source current limiting and capacitor ESR are not measured. Test
the actual harness/source at the carrier and establish margin, adding qualified
damping/clamping if needed. C10's 50 V rating does not protect a 35 V driver.

### 3. Bus capacitance and read timing matter

- **1-Wire:** with 2 µs controller-low and sampling at 15 µs, 1 nF reaches
  ~3.09 V; the +1% pull-up corner at **2 nF reaches only 2.464 V**, marginally
  below the 2.475 V ESP32 screening threshold. At 5 nF it clearly fails. This
   establishes a modeled capacitance/timing constraint, not a cable-length limit.
  The −1% R, 2 nF passing corner has only **0.138577 µs** of sample margin;
  +1% R has **−0.122044 µs**. The report records crossing time and margin from
  slot start; no sample-jitter budget or complete sensor protocol is validated.
- **I²C:** existing 4.7 kΩ pull-ups at 100 pF give ~400 ns rise, missing the
  300 ns fast-mode limit. At 400 pF, ~1.6 µs misses standard-mode too. Select
  speed/pull-up arrangement using the actual cable and attached modules.
- **Fan:** the generic transistor model sinks low adequately in the selected
  cases, but weak pull-ups plus 2 nF miss the high-level midpoint criterion in
  8/24 scenarios. This does not assert that the selected Noctua fan fails;
  its actual pull-up/waveform and harness need measurement.

### 4. Power-order backfeeding remains unresolved

Explicitly hypothetical input clamps predict **0.134–0.207 mA** ADC injection
when motor power is present and the MCU rail is off, and **2.52–2.91 mA** into
an unpowered DPS input with board TX enabled. These are sensitivity estimates,
not measured clamp currents or permitted ratings. Confirm real power sequencing,
off-rail behavior and external shutdown architecture.

### Checks that behave as intended in the models

Reset bias cases remain defined under the injected leakage budgets; the assumed
Pololu RESET/SLEEP network is 0.30 V at reset. At 24 V, the ADC divider's ±1%
resistor corners give 2.142–2.222 V; the assumed C8 corners give 0.727–1.091 ms
filter time constants. These do not test firmware, ADC accuracy or full startup.

## What remains to test physically

The [bench plan](../electronics/bench/README.md) specifies probes, connector pins,
stimuli and evidence for rails/EN/boot, load steps and heating, fan PWM/tach,
DPS grounding/UART power order, temperature-probe CRC/disconnect faults, motor
operation and external TEC shutdown. Its [record template](../electronics/bench/results-template.json)
contains no fabricated measurements and marks every case NOT_RUN.

No device-level ESP32 firmware execution, RF/EMC, selected-fan internal model,
DS18B20 protocol implementation, A4988 switching model or DPS5005 converter
model is claimed. These are specific gaps between the performed simulations
and a powered system test.
