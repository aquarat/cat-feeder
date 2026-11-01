# PCB operating simulations and regression tests

Run from the repository root:

```sh
TMPDIR=/absolute/path/to/session-scratch bash electronics/sim/run.sh
```

The script builds a project-local Docker image if needed, then runs tests and
ngspice **without network access**, with the source tree read-only. Only each
simulation's results directory and the supplied session scratch directory are
writable host mounts. No host packages or PCB files are
modified. The Dockerfile selects Debian bookworm's ngspice; each report records
the installed version, and source/netlist hashes identify its inputs. It is not
a bit-for-bit dependency lock across future package updates.

The unified pipeline runs **41 PCB regression tests, 67 interface cases,
15 interface integrity tests, waveform plotting, 308 power transients and twelve
power integrity tests**. The changed-divider integrity fixture adds 14 ngspice
cases. All stages, including plotting, run in network-disabled containers.
Interface integrity tests use `TMPDIR` for temporary fixtures. Set the optional
absolute `POWER_RESULTS` path to direct power outputs into session scratch when
verifying without replacing another owner's saved results. The latest
[`run.log`](run.log) used `POWER_RESULTS="$TMPDIR/interface-verification-power"`;
power outputs from that rerun are temporary, while the published power artifacts
remain the separately owned baseline. Capture a transcript with
`> electronics/sim/run.log 2>&1`.

## What is actually exercised

- [`../tests/`](../tests/): regression checks on the reviewed PCB's actual
  netlist and associated artifacts, including intentionally broken fixtures.
- [`interfaces/`](interfaces/README.md): ngspice operating points/transients for
  sensor-bus RC behaviour, ADC filtering, reset bias, EN timing, power-off
  interface injection sensitivity and the fan transistor interface; integrity
  tests cover interrupted reruns, altered divider ratio and corrupt solver output.
- [`power/`](power/): supply-load and motor-bus sensitivity studies, plus
  datasheet-based regulator thermal calculations.
- [`../bench/`](../bench/): the separate physical bring-up procedure and result
  recording. Physical results are **not run** until hardware is available.

## How to read the results

There are three distinct outcomes:

1. **Test/simulator execution:** schema, solver, regression and numerical
   cross-checks passed or failed.
2. **Modeled operating criteria:** individual load/cable/temperature corners
   meet or fail the stated limits. A functioning simulator can reveal a failing
   circuit corner; those results must remain visible.
3. **Hardware qualification:** not established by these runs. Board parasitics,
   component tolerances outside the chosen ranges, real external modules,
   firmware, RF, EMC and installed temperatures need appropriate hardware or
   validated device models.

No ESP32 CPU/application firmware, complete DS18B20 protocol, A4988 chopper,
DPS5005 firmware/power stage or selected-fan internal circuit is emulated here.
Ideal/behavioral/generic models are labelled in the per-study documentation.
In particular a generic BJT or assumed input clamp is a sensitivity model,
not a manufacturer-qualified model of the purchased part.

The released-to-project PCB inputs remain the independently reviewed revision
in [`../pcb/`](../pcb/). Simulations run beside those files and do not silently
alter the saved supplier project. See the [independent electrical review](../../kb/pcb-review.md).


These are **legacy revision** results. They do not validate the new integrated
PD/motor-controller design being developed under `electronics/revb/`.
