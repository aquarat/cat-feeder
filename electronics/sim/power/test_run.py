#!/usr/bin/env python3
"""Tests of independent oracles and error paths (requires actual ngspice)."""
import argparse
import json
import math
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import run


class PowerIntegrityTests(unittest.TestCase):
    def seed_previous_pass(self, directory):
        path = Path(directory)/'summary.json'
        run.write_json(path, {'run_id': 'previous-completed-attempt',
                              'suite_execution': 'PASS', 'run_state': 'COMPLETE'})
        return path

    def test_reviewed_netlist_and_negative_mutants(self):
        parts, rejected = run.source_checks()
        self.assertEqual(parts['C10']['LCSC'], 'C713402')
        self.assertEqual(rejected, ['value', 'net'])

    def test_lossless_closed_form_at_quarter_and_half_period(self):
        inductance, capacitance, supply = 10e-6, 100e-6, 24
        tau = math.sqrt(inductance*capacitance)
        voltage, current = run.lc_response(math.pi/2*tau, supply, inductance, capacitance, 0)
        self.assertAlmostEqual(voltage, supply, places=10)
        self.assertAlmostEqual(current, supply*math.sqrt(capacitance/inductance), places=10)
        voltage, current = run.lc_response(math.pi*tau, supply, inductance, capacitance, 0)
        self.assertAlmostEqual(voltage, 2*supply, places=10)
        self.assertAlmostEqual(current, 0, places=10)

    def test_overdamped_and_critical_oracle(self):
        inductance, capacitance = 10e-6, 100e-6
        critical = 2*math.sqrt(inductance/capacitance)
        for resistance in (critical, 2*critical):
            samples = [run.lc_response(t*1e-6, 24, inductance, capacitance, resistance)[0]
                       for t in range(0, 2001, 10)]
            self.assertTrue(all(b >= a for a,b in zip(samples, samples[1:])))
            self.assertLessEqual(max(samples), 24)
            self.assertAlmostEqual(samples[-1], 24, places=5)

    def test_invalid_spice_is_not_suite_pass(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            with self.assertRaises(RuntimeError):
                run.simulate(Path(directory), 'invalid', 'Xbad a 0 NONEXISTENT_SUBCKT',
                             ['v(a)'], .001, 1e-6)

    def test_top_level_failure_returns_nonzero_and_fail_json(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            with patch('sys.argv', ['run.py', '--output', directory]), \
                 patch.object(run, 'source_checks', side_effect=RuntimeError('intentional schema failure')):
                status = run.main()
            report = json.loads((Path(directory)/'summary.json').read_text())
            self.assertNotEqual(status, 0)
            self.assertEqual(report['suite_execution'], 'FAIL')

    def test_late_publication_failure_after_real_results(self):
        # Both late failure positions run ALL actual solvers, not mocked results.
        for failure in ('model-hashes.json', 'final-summary'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
                summary_path = self.seed_previous_pass(directory)
                original = run.write_json

                def failing_publication(path, value):
                    if (failure == path.name or
                            (failure == 'final-summary' and path.name == 'summary.json'
                             and value['suite_execution'] == 'PASS')):
                        raise OSError('intentional late publication failure')
                    return original(path, value)

                with patch('sys.argv', ['run.py', '--output', directory]), \
                     patch.object(run, 'write_json', side_effect=failing_publication):
                    status = run.main()
                report = json.loads(summary_path.read_text())
                self.assertEqual(status, 1)
                self.assertEqual(report['suite_execution'], 'FAIL')
                self.assertEqual(report['run_state'], 'FAILED')
                self.assertNotEqual(report['run_id'], 'previous-completed-attempt')
                self.assertEqual(report['stage'], 'model_hash_publication' if failure == 'model-hashes.json'
                                 else 'summary_publication')
                self.assertEqual(report['simulated_transients'], 308)
                self.assertEqual(report['thermal_target_failures'], 18)
                self.assertEqual(report['vmot_35V_failures'], 17)
                self.assertEqual(report['ldo_behavioral_rail_failures'], 97)
                self.assertEqual(len((Path(directory)/'ldo-sensitivity.csv').read_text().splitlines()), 145)

    def test_hard_interrupt_before_final_publication_leaves_new_running(self):
        # SIGKILL cannot execute any exception handler. The old PASS must already
        # have been replaced, even after every actual model has finished.
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            summary_path = self.seed_previous_pass(directory)
            script = '''import os, signal, sys
from pathlib import Path
from unittest.mock import patch
import run
original = run.write_json
def interrupted_publish(path, value):
    if path.name == 'summary.json' and value['suite_execution'] == 'PASS':
        os.kill(os.getpid(), signal.SIGKILL)
    return original(path, value)
with patch.object(run, 'write_json', side_effect=interrupted_publish):
    sys.exit(run.main())
'''
            proc = subprocess.run([sys.executable, '-c', script, '--output', directory],
                                  cwd=run.HERE, capture_output=True, text=True, timeout=180)
            self.assertEqual(proc.returncode, -signal.SIGKILL, proc.stdout+proc.stderr)
            report = json.loads(summary_path.read_text())
            self.assertEqual(report['suite_execution'], 'RUNNING')
            self.assertEqual(report['run_state'], 'RUNNING')
            self.assertEqual(report['stage'], 'summary_publication')
            self.assertNotEqual(report['run_id'], 'previous-completed-attempt')
            self.assertEqual(report['simulated_transients'], 308)
            self.assertEqual(len(json.loads((Path(directory)/'model-hashes.json').read_text())), 308)
            provenance = json.loads((Path(directory)/'provenance.json').read_text())
            self.assertEqual(report['run_id'], provenance['run_id'])

    def test_keyboard_interrupt_invalidates_previous_pass(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            summary_path = self.seed_previous_pass(directory)
            with patch('sys.argv', ['run.py', '--output', directory]), \
                 patch.object(run, 'source_checks', side_effect=KeyboardInterrupt):
                status = run.main()
            report = json.loads(summary_path.read_text())
            self.assertEqual(status, 130)
            self.assertEqual(report['suite_execution'], 'FAIL')
            self.assertEqual(report['run_state'], 'ABORTED')
            self.assertNotEqual(report['run_id'], 'previous-completed-attempt')

    def test_atomic_publication_error_preserves_running_json(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            path = Path(directory)/'summary.json'
            run.write_json(path, {'suite_execution': 'RUNNING'})
            before = path.read_bytes()
            with patch.object(run.os, 'replace', side_effect=OSError('intentional rename failure')):
                with self.assertRaises(OSError):
                    run.write_json(path, {'suite_execution': 'PASS'})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])

    def test_unwritable_failure_report_still_returns_nonzero(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            with patch('sys.argv', ['run.py', '--output', directory]), \
                 patch.object(run, 'write_json', side_effect=OSError('intentional unwritable output')):
                self.assertEqual(run.main(), 1)

    def test_retained_solver_rejects_zero_exit_bad_or_stale_waveforms(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            path = Path(directory)/'retained.cir'
            path.write_text('test fixture; subprocess output injected\n')
            valid_rows = [[i*.00005, 24.] for i in range(21)]
            for defect in ('missing', 'nonfinite', 'incomplete', 'time', 'schema', 'solver-log'):
                with self.subTest(defect=defect):
                    # A leftover good trace must not mask a missing fresh output.
                    path.with_suffix('.dat').write_text('time v(out)\n'+''.join(
                        f'{t} {v}\n' for t,v in valid_rows))

                    def fake_solver(*args, **kwargs):
                        rows = [r[:] for r in valid_rows]
                        if defect == 'nonfinite':
                            rows[5][1] = float('nan')
                        if defect == 'incomplete':
                            rows = rows[:12]
                        if defect == 'time':
                            rows[6][0] = rows[5][0]
                        if defect == 'schema':
                            rows[5].append(0.)
                        if defect != 'missing':
                            path.with_suffix('.dat').write_text('time v(out)\n'+''.join(
                                ' '.join(map(str,r))+'\n' for r in rows))
                        return subprocess.CompletedProcess(args, 0,
                            'Error: simulated analysis failed' if defect == 'solver-log' else '', '')

                    with patch.object(run.subprocess, 'run', side_effect=fake_solver):
                        with self.assertRaises(RuntimeError):
                            run.solve_deck(path, 1, .001, keep=True)
                    self.assertFalse(path.with_suffix('.dat.gz').exists())

    def test_retained_waveform_must_match_first_solve_extrema(self):
        with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
            out = Path(directory)
            rows = run.simulate(out, 'retained', 'Vref out 0 24\nRload out 0 1k',
                                ['v(out)'], .001, 1e-6)
            path = out/'models/retained.cir'
            with self.assertRaisesRegex(RuntimeError, 'peak differs'):
                run.solve_deck(path, 1, .001, keep=True,
                               expected_peaks={1:max(r[1] for r in rows)-1})
            self.assertFalse(path.with_suffix('.dat.gz').exists())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT/'test-integrity.log').open('w') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(PowerIntegrityTests))
    print((OUTPUT/'test-integrity.log').read_text())
    raise SystemExit(0 if result.wasSuccessful() else 1)
