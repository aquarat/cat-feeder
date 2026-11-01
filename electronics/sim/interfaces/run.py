#!/usr/bin/env python3
"""ngspice interface sensitivity studies, not ESP32/DPS/firmware emulation."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
PCB = ROOT / "electronics/pcb"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Circuit:
    def __init__(self):
        manifest = json.loads((PCB / "checksums.json").read_text())
        for name in ("feeder.kicad_sch", "feeder.kicad_pcb", "schematic-netlist.xml"):
            assert sha(PCB / name) == manifest[name], f"Unreviewed/stale input: {name}"
        tree = ET.parse(PCB / "schematic-netlist.xml")
        self.parts = {p.attrib["ref"]: p.findtext("value") for p in tree.findall("./components/comp")}
        self.pins = {}
        for net in tree.findall("./nets/net"):
            for node in net.findall("node"):
                self.pins[node.attrib["ref"], node.attrib["pin"]] = net.attrib["name"].lstrip("/")

    def value(self, ref, a, b):
        assert {self.pins[ref, "1"], self.pins[ref, "2"]} == {a, b}, ref
        token = self.parts[ref].split()[0]
        match = re.fullmatch(r"([\d.]+)([pnumkM]?)", token)
        assert match, token
        return float(match[1]) * {"": 1, "p": 1e-12, "n": 1e-9, "u": 1e-6,
                                 "m": 1e-3, "k": 1e3, "M": 1e6}[match[2]]


def simulate(out, name, body, vectors, duration=None, step=None):
    """Keep each input, solver log and numeric waveform for audit/reproduction."""
    folder = out / name
    folder.mkdir(parents=True, exist_ok=True)
    command = f"tran {step:.12g} {duration:.12g} 0 {step:.12g}" if duration else "op"
    deck = (f"Cat feeder interface study: {name}\n{body}\n"
            ".options reltol=1e-5 abstol=1e-12 vntol=1e-7\n.control\n"
            "set noaskquit\nset wr_singlescale\nset wr_vecnames\nset numdgt=12\n"
            f"{command}\nwrdata wave.dat {' '.join(vectors)}\nquit\n.endc\n.end\n")
    (folder / "model.cir").write_text(deck)
    # Never interpret an earlier waveform as output from this invocation.
    (folder / "wave.dat").unlink(missing_ok=True)
    (folder / "solver.log").unlink(missing_ok=True)
    process = subprocess.run(["ngspice", "-b", "model.cir"], cwd=folder,
                             capture_output=True, text=True, timeout=45)
    log = process.stdout + process.stderr
    (folder / "solver.log").write_text(log)
    assert process.returncode == 0 and not re.search(
        r"\b(error|fatal|warning|failed|aborted|singular)\b|timestep too small", log, re.I), log
    lines = (folder / "wave.dat").read_text().splitlines()
    headings = lines[0].split()
    assert len(set(headings)) == len(headings) and set(vectors) <= set(headings), name
    data = [[float(x) for x in line.split()] for line in lines[1:] if line.strip()]
    assert data and all(len(row) == len(headings) for row in data), name
    assert all(math.isfinite(x) for row in data for x in row), name
    if duration is not None:
        assert headings[0] == "time" and len(data) >= 2, name
        times = [row[0] for row in data]
        assert abs(times[0]) <= 1e-15, f"{name}: missing transient start"
        assert all(b > a for a, b in zip(times, times[1:])), f"{name}: nonmonotonic time"
        assert math.isclose(times[-1], duration, rel_tol=1e-8, abs_tol=1e-15), f"{name}: incomplete transient"
    return {label: [row[i] for row in data] for i, label in enumerate(headings)}


def at(wave, vector, time):
    times = wave["time"]
    assert times[0] <= time <= times[-1], "Sample outside waveform"
    for i in range(1, len(times)):
        if times[i] >= time:
            fraction = (time - times[i - 1]) / (times[i] - times[i - 1])
            return wave[vector][i - 1] + fraction * (wave[vector][i] - wave[vector][i - 1])
    raise AssertionError("Waveform too short")


def crossing(wave, vector, level, after=0):
    times, values = wave["time"], wave[vector]
    for i in range(1, len(times)):
        if times[i] >= after and values[i - 1] < level <= values[i]:
            return times[i - 1] + (times[i] - times[i - 1]) * (level - values[i - 1]) / (values[i] - values[i - 1])
    return None


def bus_studies(out, c):
    records = []
    # Ideal external low-side switch: tests cable RC, not the DS18B20 protocol.
    for kind, ref, net, caps in [
        ("onewire", "R3", "ONEWIRE", [200e-12, 1e-9, 2e-9, 5e-9]),
        ("i2c", "R16", "I2C_SDA", [50e-12, 100e-12, 200e-12, 400e-12]),
    ]:
        resistance = c.value(ref, "+3V3", net)
        for cap, tolerance in itertools.product(caps, [.99, 1.01]):
            r = resistance * tolerance
            name = f"{kind}_{cap*1e12:.0f}p_{tolerance:.2f}R"
            wave = simulate(out, name, f"""Vrail rail 0 3.3
Rpull rail bus {r}
Cwire bus 0 {cap}
Vgate gate 0 PULSE(1 0 2u 1n 1n 100u 200u)
Ssink bus 0 gate 0 SINK
.model SINK SW(Ron=20 Roff=1e12 Vt=0.5 Vh=0)
""", ["v(bus)"], 80e-6, 20e-9)
            low = 3.3 * 20 / (r + 20)
            # Compare ngspice to the independent RC closed-form solution.
            elapsed = 13e-6 - .5e-9
            predicted = 3.3 - (3.3 - low) * math.exp(-elapsed / (r * cap))
            sample = at(wave, "v(bus)", 15e-6)
            assert abs(sample - predicted) < .003, (name, sample, predicted)
            t30 = crossing(wave, "v(bus)", .3 * 3.3, 2e-6)
            t70 = crossing(wave, "v(bus)", .7 * 3.3, 2e-6)
            rise = t70 - t30
            high_crossing = crossing(wave, "v(bus)", .75 * 3.3, 2e-6)
            assert abs(rise / (.84729786 * r * cap) - 1) < .01, name
            records.append({"case": name, "model": "lumped RC and ideal sink",
                            "bus": kind, "capacitance_pF": cap * 1e12,
                            "pullup_ohm": r, "rise_30_70_ns": rise * 1e9,
                            "sample_at_15us_V": sample,
                            "high_crossing_from_slot_start_us": high_crossing * 1e6 if kind == "onewire" else None,
                            "sample_margin_us": (15e-6 - high_crossing) * 1e6 if kind == "onewire" else None,
                            "criterion": "1-Wire: high >=0.75*3.3V at 15us from slot start, release at 2us; I2C: 30-70% <=1000/300ns",
                            "onewire_read_high": sample >= .75 * 3.3 if kind == "onewire" else None,
                            "i2c_100kHz": rise <= 1e-6 if kind == "i2c" else None,
                            "i2c_400kHz": rise <= 300e-9 if kind == "i2c" else None})
    return records


def adc_studies(out, c):
    top = c.value("R18", "VMOT", "BUS_SENSE")
    bottom = c.value("R19", "BUS_SENSE", "GND")
    cap = c.value("C8", "BUS_SENSE", "GND")
    records = []
    for bus, rt, rb in itertools.product([20, 24], [.99, 1.01], [.99, 1.01]):
        r1, r2 = top * rt, bottom * rb
        wave = simulate(out, f"adc_{bus}V_{rt:.2f}_{rb:.2f}",
                        f"Vbus bus 0 {bus}\nRtop bus adc {r1}\nRbottom adc 0 {r2}\nCfilter adc 0 {cap}",
                        ["v(adc)"])
        observed = wave["v(adc)"][-1]
        assert abs(observed - bus * r2 / (r1 + r2)) < 1e-5
        records.append({"case": "powered divider", "VMOT_V": bus, "R18_factor": rt,
                        "R19_factor": rb, "ADC_V": observed,
                        "below_3V3_rail": observed < 3.3,
                        "scope": "DC headroom only, not ADC accuracy or overvoltage qualification"})
    for tolerance in [.8, 1.2]:
        tau = top * bottom / (top + bottom) * cap * tolerance
        wave = simulate(out, f"adc_step_C{tolerance:.1f}",
                        f"Vbus bus 0 PULSE(0 24 1m 1n 1n 20m 40m)\nRtop bus adc {top}\nRbottom adc 0 {bottom}\nCfilter adc 0 {cap*tolerance}",
                        ["v(adc)"], .008, 2e-6)
        final_voltage = 24 * bottom / (top + bottom)
        observed_tau = crossing(wave, "v(adc)", final_voltage * (1 - math.exp(-1)), .001) - .001
        assert abs(observed_tau / tau - 1) < .005
        records.append({"case": "filter step", "C8_factor": tolerance,
                        "time_constant_ms": observed_tau * 1000})
    # Explicit hypothetical MCU input clamp, not an Espressif silicon model.
    for bus, clamp in itertools.product([20, 24], [.3, .6]):
        wave = simulate(out, f"adc_off_{bus}V_clamp{clamp}", f"""Vbus bus 0 {bus}
Rtop bus adc {top}
Rbottom adc 0 {bottom}
Bclamp adc clamp_return I=max((v(adc)-{clamp})/10,0)
Vmonitor clamp_return 0 0
""", ["v(adc)", "i(Vmonitor)"])
        injection = wave["i(Vmonitor)"][-1]
        predicted = ((bus - clamp) / top - clamp / bottom) / (1 + 10 / top + 10 / bottom)
        assert abs(injection - predicted) < 1e-8
        records.append({"case": "unpowered MCU clamp sensitivity", "VMOT_V": bus,
                        "assumed_clamp_V": clamp, "injection_mA": injection * 1000,
                        "status": "UNQUALIFIED: possible injection; no permitted MCU injection current assumed"})
    return records


def bias_and_uart(out, c):
    records = []
    for ref, net, pull, leakage in [
        ("R20", "DPS_TX", "+3V3", 5e-6),
        ("R21", "DPS_TX_EXT", "GND", -5e-6),
        ("R14", "UART_OEn", "+3V3", 11e-6),
        ("R10", "TEC_EN", "GND", -1e-6),
        ("R12", "STEP", "GND", -1e-6),
        ("R13", "DIR", "GND", -1e-6),
    ]:
        r = c.value(ref, net, pull) * 1.01
        rail = 3.3 if pull == "+3V3" else 0
        wave = simulate(out, f"bias_{ref}", f"Vpull pull 0 {rail}\nRbias pull signal {r}\nIleak signal 0 {leakage}", ["v(signal)"])
        value = wave["v(signal)"][-1]
        assert abs(value - (rail - leakage * r)) < 1e-6
        records.append({"case": "reset bias leakage sensitivity", "ref": ref, "net": net,
                        "assumed_leakage_uA": leakage * 1e6, "voltage_V": value,
                        "defined_at_assumed_2V_high_0_8V_low": value >= 2 if rail else value <= .8})
    r = c.value("R11", "MOTOR_RUN", "GND")
    wave = simulate(out, "motor_sleep_reset", f"Vdd rail 0 3.3\nRcarrier rail run 100k\nR11 run 0 {r}", ["v(run)"])
    records.append({"case": "reset with Pololu 100k SLEEP pullup", "voltage_V": wave["v(run)"][-1],
                    "low_below_0_3VDD": wave["v(run)"][-1] < .3 * 3.3})
    r = c.value("R15", "DPS_TX_BUF", "DPS_RX_EXT")
    for clamp, enabled in itertools.product([.3, .7], [True, False]):
        drive_r = 20 if enabled else 1e12
        wave = simulate(out, f"uart_dps_off_{clamp}_{enabled}", f"""Vtx source 0 3.3
Rdriver source output {drive_r}
R15 output dps_rx {r}
Bclamp dps_rx clamp_return I=max((v(dps_rx)-{clamp})/10,0)
Vmonitor clamp_return 0 0
Rleak dps_rx 0 1e9
""", ["v(dps_rx)", "i(Vmonitor)"])
        records.append({"case": "DPS off, board on", "buffer_enabled": enabled,
                        "assumed_DPS_input_clamp_V": clamp,
                        "injection_mA": wave["i(Vmonitor)"][-1] * 1000,
                        "status": "UNQUALIFIED external clamp/output model; enable sequencing required"})
    ren = c.value("R1", "+3V3", "EN")
    cen = c.value("C5", "EN", "GND")
    for scale in [.8, 1.2]:
        wave = simulate(out, f"enable_RC_C{scale}",
                        f"Vdd rail 0 PULSE(0 3.3 1m 1n 1n 100m 200m)\nR1 rail en {ren}\nC5 en 0 {cen*scale}",
                        ["v(en)"], .04, 10e-6)
        delay = crossing(wave, "v(en)", .75 * 3.3, .001) - .001
        assert abs(delay / (-math.log(.25) * ren * cen * scale) - 1) < .005
        records.append({"case": "EN RC ideal rail step", "C5_factor": scale,
                        "time_to_75percent_ms": delay * 1000,
                        "scope": "RC response, not ESP32 boot/brownout emulation"})
    return records


def fan_studies(out, c):
    assert [c.pins["Q1", str(i)] for i in (1, 2, 3)] == ["FAN_BASE", "GND", "FAN_PWM_OD"]
    rbase = c.value("R8", "FAN_PWM_GPIO", "FAN_BASE")
    rdown = c.value("R9", "FAN_BASE", "GND")
    records = []
    for pullup, cap, beta, temp in itertools.product([1050, 10000, 100000], [100e-12, 2e-9], [100, 300], [25, 85]):
        name = f"fan_R{pullup}_C{cap*1e12:.0f}p_B{beta}_T{temp}"
        wave = simulate(out, name, f"""Vfan fan_pullup 0 5.25
Rfan fan_pullup pwm {pullup}
Cwire pwm 0 {cap}
Vgpio gpio 0 PULSE(0 3.3 20u 10n 10n 20u 40u)
R8 gpio base {rbase}
R9 base 0 {rdown}
Q1 pwm base 0 GENERIC_NPN
.model GENERIC_NPN NPN(IS=1e-14 BF={beta} VAF=100 IKF=0.1
+ RB=10 RC=1 RE=0.5 CJE=8p CJC=4p TF=0.35n TR=250n)
.temp {temp}
""", ["v(pwm)", "v(base)"], 200e-6, 20e-9)
        # Final cycle: GPIO low/released at ~160 us, GPIO high/sink at ~180 us.
        high = at(wave, "v(pwm)", 170e-6)
        low = at(wave, "v(pwm)", 190e-6)
        assert low >= -.01 and max(wave["v(pwm)"]) <= 5.5, name
        records.append({"case": name, "model": "generic NPN, NOT selected-vendor model",
                        "pullup_ohm": pullup, "wire_pF": cap * 1e12,
                        "BF": beta, "temperature_C": temp,
                        "released_midpoint_V": high, "sink_midpoint_V": low,
                        "midpoint_0_8V_low_2_1V_high": low <= .8 and high >= 2.1,
                        "criterion_scope": "exploratory midpoint margins; not complete fan timing compliance"})
    return records


def write_report(out, report):
    temporary = out / "report.json.tmp"
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    temporary.replace(out / "report.json")


def criterion_summary(data):
    keys = ("onewire_read_high", "i2c_100kHz", "i2c_400kHz",
            "midpoint_0_8V_low_2_1V_high", "below_3V3_rail",
            "defined_at_assumed_2V_high_0_8V_low", "low_below_0_3VDD")
    counts = {}
    for key in keys:
        rows = [row for group in data.values() for row in group if isinstance(row.get(key), bool)]
        counts[key] = {"evaluated": len(rows), "failed": sum(not row[key] for row in rows),
                       "failed_cases": [row["case"] for row in rows if not row[key]]}
    return {"by_criterion": counts, "failed_evaluations": sum(v["failed"] for v in counts.values()),
            "note": "Overlapping criterion evaluations, not distinct failed circuits; clamps remain unqualified."}


def run_studies(out):
    circuit = Circuit()
    data = {"bus": bus_studies(out, circuit), "adc": adc_studies(out, circuit),
            "bias_uart": bias_and_uart(out, circuit), "fan": fan_studies(out, circuit)}
    report = {
        "execution_status": "PASS: all solver runs, finite-output checks and analytic oracles passed",
        "circuit_status": "CONDITIONAL: assumed cable/loading/power-order corners include failures; no hardware qualification",
        "tool": subprocess.check_output(["ngspice", "--version"], text=True).strip(),
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                          [Path(__file__), PCB / "schematic-netlist.xml", PCB / "feeder.kicad_sch", PCB / "feeder.kicad_pcb"]},
        "physical_measurements": False, "firmware_executed": False,
        "results": data,
        "criteria": criterion_summary(data),
    }
    for group, records in data.items():
        fields = list(dict.fromkeys(key for record in records for key in record))
        with (out / (group + ".csv")).open("w") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args(argv)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    status = {"run_id": str(uuid.uuid4()), "started_utc": datetime.now(timezone.utc).isoformat(),
              "run_status": "RUNNING", "execution_status": "RUNNING",
              "circuit_status": "NOT_EVALUATED", "physical_measurements": False, "firmware_executed": False}
    # Atomic invalidation precedes input checks. Even a hard kill leaves RUNNING,
    # never the previous PASS. Only COMPLETE reports authorize consuming artifacts.
    write_report(out, status)
    try:
        for name in ("bus.csv", "adc.csv", "bias_uart.csv", "fan.csv", "waveforms.svg"):
            (out / name).unlink(missing_ok=True)
        report = run_studies(out)
        report.update(run_id=status["run_id"], started_utc=status["started_utc"],
                      finished_utc=datetime.now(timezone.utc).isoformat(), run_status="COMPLETE")
        write_report(out, report)
    except BaseException as exc:
        status.update(run_status="FAILED", execution_status="FAIL", error=f"{type(exc).__name__}: {exc}",
                      finished_utc=datetime.now(timezone.utc).isoformat())
        write_report(out, status)
        raise
    print(report["execution_status"])
    print(report["circuit_status"])
    print("Cases:", {k: len(v) for k, v in report["results"].items()})


if __name__ == "__main__":
    main()
