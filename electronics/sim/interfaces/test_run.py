#!/usr/bin/env python3
"""Runner integrity regressions; real ngspice required for changed-divider test."""
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import run


class InterfaceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="interface-integrity-")
        self.addCleanup(self.temporary.cleanup)
        self.out = Path(self.temporary.name)

    def report(self):
        return json.loads((self.out / "report.json").read_text())

    def old_pass(self):
        run.write_report(self.out, {"run_id": "old-pass", "run_status": "COMPLETE",
                                    "execution_status": "PASS", "results": {"old": []}})
        for name in ("bus.csv", "adc.csv", "bias_uart.csv", "fan.csv", "waveforms.svg"):
            (self.out / name).write_text("old successful evidence")

    def assert_failed(self, error):
        report = self.report()
        self.assertEqual(report["run_status"], "FAILED")
        self.assertEqual(report["execution_status"], "FAIL")
        self.assertNotEqual(report["run_id"], "old-pass")
        self.assertIn(error, report["error"])
        self.assertNotIn("results", report)
        for name in ("bus.csv", "adc.csv", "bias_uart.csv", "fan.csv", "waveforms.svg"):
            self.assertFalse((self.out / name).exists(), name)

    def test_timeout_invalidates_previous_pass(self):
        self.old_pass()
        with patch.object(run.subprocess, "run", side_effect=subprocess.TimeoutExpired("ngspice", 45)):
            with self.assertRaises(subprocess.TimeoutExpired):
                run.main(["--output", str(self.out)])
        self.assert_failed("TimeoutExpired")

    def test_keyboard_interrupt_invalidates_previous_pass(self):
        self.old_pass()
        with patch.object(run.subprocess, "run", side_effect=KeyboardInterrupt("injected interrupt")):
            with self.assertRaises(KeyboardInterrupt):
                run.main(["--output", str(self.out)])
        self.assert_failed("KeyboardInterrupt")

    def test_running_is_published_before_input_validation(self):
        self.old_pass()

        def invalid_input():
            report = self.report()
            self.assertEqual(report["run_status"], "RUNNING")
            self.assertEqual(report["execution_status"], "RUNNING")
            self.assertNotIn("results", report)
            raise AssertionError("intentional input rejection")

        with patch.object(run, "Circuit", side_effect=invalid_input):
            with self.assertRaisesRegex(AssertionError, "intentional input rejection"):
                run.main(["--output", str(self.out)])
        self.assert_failed("intentional input rejection")

    def test_sigkill_leaves_running_not_old_pass(self):
        self.old_pass()
        # Stop at input validation in a real child, after atomic invalidation.
        script = """
import pathlib, sys, time
sys.path.insert(0, sys.argv[1])
import run
def block():
    pathlib.Path(sys.argv[2], 'ready').write_text('ready')
    time.sleep(60)
run.Circuit = block
run.main(['--output', sys.argv[2]])
"""
        child = subprocess.Popen([sys.executable, "-c", script, str(Path(run.__file__).parent), str(self.out)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            while not (self.out / "ready").exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue((self.out / "ready").exists(), "child failed to reach validation barrier")
            child.kill()
            child.communicate(timeout=5)
            self.assertEqual(child.returncode, -signal.SIGKILL)
            self.assertEqual(self.report()["run_status"], "RUNNING")
            self.assertNotEqual(self.report()["run_id"], "old-pass")
            self.assertNotIn("results", self.report())
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)

    def test_complete_run_returns_and_prints_report_case_counts(self):
        self.old_pass()
        report = {"execution_status": "PASS", "circuit_status": "CONDITIONAL",
                  "results": {"bus": [{"case": "example"}]}}
        output = io.StringIO()
        with patch.object(run, "run_studies", return_value=report), contextlib.redirect_stdout(output):
            run.main(["--output", str(self.out)])
        self.assertEqual(self.report()["run_status"], "COMPLETE")
        self.assertIn("Cases: {'bus': 1}", output.getvalue())
        self.assertNotEqual(self.report()["run_id"], "old-pass")

    def test_report_replacement_is_atomic(self):
        self.old_pass()
        replace = Path.replace
        observed = []

        def inspect_replace(source, target):
            observed.append(self.report()["execution_status"])
            self.assertEqual(json.loads(source.read_text())["run_status"], "RUNNING")
            return replace(source, target)

        with patch.object(Path, "replace", inspect_replace):
            run.write_report(self.out, {"run_status": "RUNNING"})
        self.assertEqual(observed, ["PASS"])
        self.assertEqual(self.report()["run_status"], "RUNNING")
        self.assertFalse((self.out / "report.json.tmp").exists())

    def test_changed_divider_120k_uses_real_ngspice(self):
        circuit = run.Circuit()
        # In-memory XML-derived component fixture; frozen source is untouched.
        circuit.parts["R18"] = "120k"
        records = run.adc_studies(self.out, circuit)
        self.assertEqual(len(records), 14)
        self.assertEqual(len(list(self.out.glob("*/wave.dat"))), 14)
        steps = [row for row in records if row["case"] == "filter step"]
        for row in steps:
            expected_ms = (120000 * 10000 / 130000) * 100e-9 * row["C8_factor"] * 1000
            self.assertAlmostEqual(row["time_constant_ms"], expected_ms, delta=.00001)
        final = (self.out / "adc_step_C1.2/wave.dat").read_text().splitlines()[-1].split()
        self.assertAlmostEqual(float(final[-1]), 24 / 13, delta=.004)

    def fake_solver(self, waveform, log="", returncode=0):
        def invoke(*args, **kwargs):
            if waveform is not None:
                (Path(kwargs["cwd"]) / "wave.dat").write_text(waveform)
            return subprocess.CompletedProcess(args[0], returncode, log, "")
        return patch.object(run.subprocess, "run", side_effect=invoke)

    def simulate(self):
        return run.simulate(self.out, "fixture", "Vbus bus 0 1", ["v(bus)"], 1, .1)

    def test_truncated_transient_rejected(self):
        with self.fake_solver("time v(bus)\n0 0\n0.5 1\n"):
            with self.assertRaisesRegex(AssertionError, "incomplete transient"):
                self.simulate()

    def test_nonmonotonic_transients_rejected(self):
        for middle in ("0.5 1\n0.5 1", "0.6 1\n0.4 1"):
            with self.subTest(middle=middle), self.fake_solver(f"time v(bus)\n0 0\n{middle}\n1 1\n"):
                with self.assertRaisesRegex(AssertionError, "nonmonotonic time"):
                    self.simulate()

    def test_stale_solver_waveform_cannot_be_reused(self):
        folder = self.out / "fixture"
        folder.mkdir()
        (folder / "wave.dat").write_text("time v(bus)\n0 0\n1 1\n")
        (folder / "solver.log").write_text("old successful solver")
        with self.fake_solver(None):
            with self.assertRaises(FileNotFoundError):
                self.simulate()
        self.assertFalse((folder / "wave.dat").exists())
        self.assertEqual((folder / "solver.log").read_text(), "")

    def test_solver_diagnostics_and_nonzero_exit_rejected(self):
        for diagnostic in ("Warning", "Error", "fatal", "failed", "aborted", "singular", "timestep too small"):
            with self.subTest(diagnostic=diagnostic), self.fake_solver("time v(bus)\n0 0\n1 1\n", diagnostic):
                with self.assertRaises(AssertionError):
                    self.simulate()
        with self.fake_solver("time v(bus)\n0 0\n1 1\n", returncode=1):
            with self.assertRaises(AssertionError):
                self.simulate()

    def test_malformed_and_nonfinite_solver_data_rejected(self):
        for waveform in ("time v(bus)\n0 0\n1 nan\n", "time v(bus)\n0 0\n1 inf\n",
                         "time v(bus)\n0 0\n1\n", "time v(other)\n0 0\n1 1\n",
                         "time v(bus) v(bus)\n0 0 0\n1 1 1\n", "time v(bus)\n0.1 0\n1 1\n"):
            with self.subTest(waveform=waveform), self.fake_solver(waveform):
                with self.assertRaises(AssertionError):
                    self.simulate()

    def test_criterion_counts_preserve_overlapping_failures(self):
        summary = run.criterion_summary({"bus": [
            {"case": "both", "i2c_100kHz": False, "i2c_400kHz": False},
            {"case": "fast", "i2c_100kHz": True, "i2c_400kHz": False},
            {"case": "unset", "onewire_read_high": None},
            {"case": "unqualified", "status": "UNQUALIFIED"}]})
        self.assertEqual(summary["failed_evaluations"], 3)
        self.assertEqual(summary["by_criterion"]["i2c_100kHz"],
                         {"evaluated": 2, "failed": 1, "failed_cases": ["both"]})
        self.assertEqual(summary["by_criterion"]["i2c_400kHz"]["failed_cases"], ["both", "fast"])
        self.assertEqual(summary["by_criterion"]["onewire_read_high"]["evaluated"], 0)

    def test_completed_baseline_criteria_and_margins(self):
        results = Path(os.environ.get("INTERFACE_RESULTS", str(Path(run.__file__).parent / "results")))
        report = json.loads((results / "report.json").read_text())
        self.assertEqual(report["run_status"], "COMPLETE")
        self.assertEqual(report["source_sha256"]["electronics/sim/interfaces/run.py"], run.sha(Path(run.__file__)))
        self.assertEqual({key: len(rows) for key, rows in report["results"].items()},
                         {"bus": 16, "adc": 14, "bias_uart": 13, "fan": 24})
        self.assertEqual(report["criteria"]["failed_evaluations"], 19)
        expected = {"onewire_read_high": (8, 3), "i2c_100kHz": (8, 2), "i2c_400kHz": (8, 6),
                    "midpoint_0_8V_low_2_1V_high": (24, 8), "below_3V3_rail": (8, 0),
                    "defined_at_assumed_2V_high_0_8V_low": (6, 0), "low_below_0_3VDD": (1, 0)}
        for key, (evaluated, failed) in expected.items():
            counts = report["criteria"]["by_criterion"][key]
            self.assertEqual((counts["evaluated"], counts["failed"]), (evaluated, failed))
            failures = [row["case"] for rows in report["results"].values() for row in rows if row.get(key) is False]
            self.assertEqual(counts["failed_cases"], failures)
        margins = {row["case"]: row["sample_margin_us"] for row in report["results"]["bus"]}
        self.assertAlmostEqual(margins["onewire_2000p_0.99R"], .138577, places=5)
        self.assertAlmostEqual(margins["onewire_2000p_1.01R"], -.122044, places=5)

    def test_plotter_rejects_incomplete_reports(self):
        plotter = Path(run.__file__).parents[1] / "plot_interfaces.py"
        for status in ("RUNNING", "FAILED"):
            with self.subTest(status=status):
                run.write_report(self.out, {"run_status": status})
                process = subprocess.run([sys.executable, str(plotter), "--output", str(self.out)],
                                         capture_output=True, text=True, timeout=10)
                self.assertNotEqual(process.returncode, 0)
                self.assertIn("Only COMPLETE", process.stderr)
                self.assertFalse((self.out / "waveforms.svg").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
