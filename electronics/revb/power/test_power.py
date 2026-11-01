#!/usr/bin/env python3
"""Analytical regression and fault-injection tests for the integration contract."""
import unittest
from design import build
from analyze import check


class PowerTests(unittest.TestCase):
    def setUp(self):
        self.circuit = build()
        self.parts = {p['ref']: p for p in self.circuit['parts']}

    def test_operating_envelope(self):
        results = check(self.circuit)
        self.assertLess(results['+3V3']['peak_A'], 1.5)
        self.assertLess(results['+12V']['startup_peak_typical_soft_start_A'], 1.7)
        self.assertLess(results['maximum_rail_input_power_at_80_percent_W'], 12)

    def test_bootstrap_to_ground_is_rejected(self):
        self.parts['CP4']['pins']['2'] = 'GND'
        with self.assertRaises(AssertionError): check(self.circuit)

    def test_saturated_inductor_substitution_is_rejected(self):
        self.parts['LP2']['isat_A_typ'] = 1.2
        with self.assertRaises(AssertionError): check(self.circuit)

    def test_tenfold_smaller_inductor_is_rejected(self):
        self.parts['LP1']['inductance_H'] /= 10
        with self.assertRaises(AssertionError): check(self.circuit)

    def test_reversed_feedback_is_rejected(self):
        self.parts['RP1']['resistance_ohm'], self.parts['RP2']['resistance_ohm'] = 18000, 249000
        with self.assertRaises(AssertionError): check(self.circuit)

    def test_16v_input_cap_substitution_is_rejected(self):
        self.parts['CP11']['voltage_V'] = 16
        with self.assertRaises(AssertionError): check(self.circuit)

    def test_raw_vbus_dependency_is_rejected(self):
        self.parts['UP2']['pins']['3'] = 'VBUS_RAW'
        with self.assertRaises(AssertionError): check(self.circuit)

    def test_inadequate_transient_capacitance_is_rejected(self):
        self.parts['CP8']['capacitance_F'] = 1e-6
        with self.assertRaisesRegex(AssertionError, 'ESP32 minimum'): check(self.circuit)


if __name__ == '__main__': unittest.main(verbosity=2)
