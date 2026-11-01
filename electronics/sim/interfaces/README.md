# Interface operating simulations

`run.py` executes **67 ngspice DC/transient cases**. Values and passive endpoints
come from the reviewed KiCad XML; the schematic, PCB and XML must match their
reviewed hashes. This tests selected electrical subnetworks, not the complete
ESP32, DS18B20, A4988 or DPS5005, and executes no application firmware.

Run with the shared simulation image, from the repository root:

```sh
docker build -t cat-feeder-spice:local -f electronics/sim/Dockerfile electronics/sim
mkdir -p electronics/sim/interfaces/results
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -v "$PWD:/work:ro" -v "$PWD/electronics/sim/interfaces/results:/results" \
  cat-feeder-spice:local python electronics/sim/interfaces/run.py --output /results
```

Each case retains `model.cir`, `solver.log` and `wave.dat`. Grouped CSVs and
`results/report.json` record measurements, criteria, tool version and source
hashes. An execution PASS means the solver and analytic cross-checks worked;
**it does not mean all operating corners passed**. Failed scenario criteria
remain false in the report. Source hashes expose results from an older revision.

Only `run_status: COMPLETE` authorizes reading case artifacts. Each invocation
atomically replaces the previous report with RUNNING **before input validation**;
exceptions (including timeout/KeyboardInterrupt) replace it with FAILED. SIGKILL
cannot execute cleanup and leaves RUNNING, not an old PASS. CSVs/plots are
invalidated before studies begin; previous case directories may remain during a
failed run and must not be consumed. Each solver invocation deletes its previous
waveform/log first. Transients must start at zero, have strictly increasing time
and reach the requested end; nonfinite/malformed output and solver diagnostics
are rejected. The plotter refuses incomplete reports.

`test_run.py` adds **15 integrity tests**: failed/interrupted reruns, publication
ordering/atomic replacement, an actual child-process SIGKILL, successful return,
stale/truncated/nonmonotonic/malformed solver output, warning/exit rejection,
criterion totals/margins and plot gating. Its changed-divider fixture executes
**14 additional real ngspice cases** with R18 = 120 kΩ in memory; the transient
oracle derives its threshold from the actual divider ratio. Frozen PCB files
are never edited. Run the unified `../run.sh` to regenerate the baseline before
these tests; test scratch uses `TMPDIR` and is removed afterwards. The durable
test transcript is [`../run.log`](../run.log).

## Models and limits

| Subnetwork | Actual PCB inputs | Explicit external assumptions / limits |
|---|---|---|
| 1-Wire | R3 4.7 kΩ, shared J4/J5 bus | Ideal 3.3 V rail, ±1% R, 200 pF–5 nF lumped total capacitance, 20 Ω ideal pull-down; controller releases after 2 µs and samples at 15 µs. Threshold is ESP32 input-high 0.75×VDD. No sensor protocol/CRC, cable transmission line, leakage or protection model. |
| I²C | R16 4.7 kΩ on SDA | 50–400 pF, same ideal sink/rail. 30–70% rise limits: 1000 ns standard-mode / 300 ns fast-mode. Clock/data timing, arbitration and breakout pull-ups are outside this RC model. |
| ADC | R18 100 kΩ, R19 10 kΩ, C8 100 nF | ±1% resistors; C8 ±20% sensitivity, ideal unloaded ADC. 3.3 V headroom is not an accuracy, attenuation, sampling-settling or surge test. |
| MCU-off ADC | Same divider | Hypothetical 0.3/0.6 V input clamp, 10 Ω incremental resistance, return clamped to 0 V. **Not an Espressif diode model**. Shows possible injection, not damage or a permissible current rating. |
| UART/reset bias | R20/R21, R14, R10/R12/R13, R11 | Injected leakage 1/5/11 µA is an exploratory budget; no claim these include every device's worst-case leakage. 2 V/0.8 V is the stated screening criterion. Motor RESET/SLEEP adds the documented external Pololu 100 kΩ pull-up. |
| DPS-off UART | R15 1 kΩ | Generic 3.3 V buffer: 20 Ω enabled, 1 TΩ disabled. Hypothetical DPS input clamps 0.3/0.7 V plus 10 Ω. No actual DPS input schematic, protocol, Ioff/ESD, ground-shunt or chip power-ramp model. |
| EN | R1 10 kΩ, C5 1 µF | Ideal rail step; C5 ±20%. Reports time to 75% rail. No ESP32 boot, rail-ramp threshold, brownout or firmware execution. |
| Fan PWM | Q1 topology, R8 4.7 kΩ, R9 100 kΩ | **Self-authored generic NPN**, not Jiangsu Changjing's validated MMBT3904 model. BF 100/300, 25/85°C; assumed CJE 8 pF, CJC 4 pF, TF 0.35 ns, TR 250 ns, IS 10⁻¹⁴ A, VAF 100 V, IKF 0.1 A, RB/RC/RE 10/1/0.5 Ω. External resistor pull-up 1.05/10/100 kΩ to 5.25 V, 100 pF/2 nF line capacitance, 25 kHz/50% command. Real fan pull-up may be a current source. Screen ≤0.8 V low and ≥2.1 V high at half-pulse; not full timing qualification. |

Neither the generic NPN parameters nor the capacitor/line assumptions are
measured parts. No manufacturer AP2112/ESP32/DPS macro-model is claimed here.
Datasheet/standard context: [independent review](../../../kb/pcb-review.md),
[Espressif module datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf),
[NXP I²C UM10204](https://www.nxp.com/docs/en/user-guide/UM10204.pdf),
[Noctua PWM guidance](https://www.noctua.at/en/support/faqs/microcontroller-guide-pwm-setup-and-rpm-monitoring).
These links identify the limits' context; public Noctua/ADI retrieval during this
run was rate-limited/timed out. Existing independent-review evidence was retained.

## Results from the actual runs

- **I²C:** ~197–201 ns at 50 pF; ~394–402 ns at 100 pF. The latter misses the
  300 ns fast-mode limit but meets standard-mode. 400 pF gives ~1.58–1.61 µs,
  missing even the 1000 ns standard-mode limit with these pull-ups.
- **1-Wire:** 1 nF reaches ~3.09–3.10 V at the chosen sample time. At 2 nF,
  the +1% resistor corner is ~2.464 V, just below the 2.475 V threshold. At
  5 nF, ~1.40–1.42 V fails. This is a capacitance/timing limit, not a certified
  cable length; the complete cable/probe bus must be measured.
  At 2 nF the −1% resistor corner crosses high at **14.861423 µs**, leaving
  only **0.138577 µs** before sampling; +1% crosses at **15.122044 µs**, a
  **−0.122044 µs** margin. Times are from slot start, with release at 2 µs.
- **ADC:** at 24 V, ±1% resistor corners give **2.142–2.222 V**. Filter time
  constants are **0.727–1.091 ms** for the assumed capacitor corners. With the
  MCU rail off, hypothetical clamps carry **0.134–0.207 mA** over 20/24 V.
  Actual MCU power sequencing/backfeed remains unqualified.
- **Bias:** all six injected-leakage screening cases remain defined; modeled
  Pololu RESET/SLEEP is **0.30 V** at reset. EN reaches 75% in **11.09–16.64 ms**.
- **DPS off:** enabled TX injects **2.52–2.91 mA** into the hypothetical clamp.
  Disabled-buffer model has zero clamp current. This quantifies why board-side
  pull-ups and OE reset defaults alone do not handle every power-loss sequence.
- **Fan:** all modeled sink midpoints are **0.020–0.086 V**. **8/24** assumed
  pull-up/capacitance corners miss the exploratory high threshold at mid-pulse;
  all use 2 nF with a 10 kΩ or 100 kΩ pull-up. This supports a real fan/cable
  oscilloscope test, not a claim that the chosen Noctua fan fails.

The report contains **19 failed criterion evaluations out of 63**: 3/8 1-Wire,
2/8 I²C standard-mode, 6/8 I²C fast-mode, 8/24 fan, 0/8 ADC headroom,
0/6 reset bias and 0/1 carrier reset. I²C criteria overlap; 19 is not a count
of distinct circuits. Hypothetical clamp cases remain UNQUALIFIED and have no
invented passing threshold. See the [independent review](../../../kb/pcb-simulation-review.md)
for the original R1/R2 findings and remaining model limitations.

The RC/divider results are checked against closed-form exponential/Ohm-law
solutions. Generic transistor results are sensitivity predictions only; chip
dynamic behaviour needs a validated model or bench measurements.
