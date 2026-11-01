"""Regression and fault-injection tests on the frozen exported KiCad XML/PCB."""

import copy
import csv
import json
import unittest

from netlist_checks import (
    PCB, DOMAIN_CHECKS, Netlist, RuleViolation, board_data, check_adc,
    check_boot_and_programming, check_fan, check_motor, check_rails,
    check_sensor_buses, check_tec_logic_only, check_uart, normalize,
    verify_provenance,
)


class ReviewedArtifacts(unittest.TestCase):
    def test_complete_reviewed_hash_manifest_and_source_files(self):
        self.assertEqual(len(verify_provenance()), 85)

    def test_provenance_rejects_altered_schematic_pcb_xml_and_manifest(self):
        # In-memory read substitution; no frozen file or temporary PCB is written.
        for target in ("feeder.kicad_sch", "feeder.kicad_pcb", "schematic-netlist.xml", "checksums.json"):
            with self.subTest(target=target):
                def read(name):
                    data = (PCB / name).read_bytes()
                    return data + b"\n" if name == target else data
                with self.assertRaisesRegex(RuleViolation, "hash mismatch|manifest identity"):
                    verify_provenance(read)

    def test_actual_pcb_pads_match_all_xml_nodes_including_nc(self):
        n = Netlist.load()
        footprints, pads, _ = board_data((PCB / "feeder.kicad_pcb").read_text())
        self.assertEqual(len(footprints), 54)
        self.assertEqual(len(n.pins), 179)
        self.assertEqual(set(footprints), set(n.components))
        self.assertEqual(pads, n.pins)
        for ref, component in n.components.items():
            with self.subTest(ref=ref):
                self.assertEqual(footprints[ref]["Value"], component.findtext("value"))

    def test_actual_carrier_rows_not_mirrored_and_have_correct_pitch(self):
        _, _, positions = board_data((PCB / "feeder.kicad_pcb").read_text())
        left, right = positions[("J14", "1")], positions[("J15", "1")]
        self.assertAlmostEqual(right[0] - left[0], 15.24, places=5)
        self.assertAlmostEqual(left[1], right[1], places=5)
        for ref in ("J14", "J15"):
            start = positions[(ref, "1")]
            for pin in range(1, 9):
                x, y = positions[(ref, str(pin))]
                self.assertAlmostEqual(x, start[0], places=5)
                self.assertAlmostEqual(y - start[1], (pin - 1) * 2.54, places=5)

    def test_connectivity_and_bom_agree_with_export_not_used_as_electrical_oracle(self):
        n = Netlist.load()
        connections = json.loads((PCB / "connectivity.json").read_text())
        with (PCB / "design-bom.csv").open(newline="") as source:
            rows = list(csv.DictReader(source))
        bom = {row["Reference"]: row for row in rows}
        self.assertEqual(len(rows), 54)
        self.assertEqual(len(connections), 54)
        self.assertEqual(set(bom), set(n.components))
        self.assertEqual({c["ref"] for c in connections}, set(n.components))
        declared = {}
        for comp in connections:
            ref = comp["ref"]
            xml = n.components[ref]
            with self.subTest(ref=ref):
                self.assertEqual(comp["value"], xml.findtext("value"))
                self.assertEqual(bom[ref]["Value"], xml.findtext("value"))
                code = xml.find("fields/field[@name='LCSC']").text
                self.assertEqual(bom[ref]["LCSC"], code)
                self.assertEqual(comp["lcsc"], code)
                self.assertEqual(bom[ref]["Assembly"], comp["assembly"])
                self.assertEqual(bom[ref]["Footprint"].split(":", 1)[-1],
                                 xml.findtext("footprint").split(":", 1)[-1])
            for pin, net in comp["nets"].items():
                declared[(ref, pin)] = normalize(net)
        self.assertEqual(len(declared), 163)
        for pin, net in declared.items():
            self.assertEqual(n.net(pin), net, pin)
        for pin in set(n.pins) - set(declared):
            self.assertEqual(n.nodes[n.net(pin)], {pin})
            self.assertTrue(n.net(pin).startswith("unconnected-"))
        self.assertEqual(sum(row["Assembly"] == "SMT" for row in rows), 36)
        self.assertEqual(sum(row["Assembly"] == "THT" for row in rows), 18)


class ElectricalRequirements(unittest.TestCase):
    def setUp(self):
        self.n = Netlist.load()

    def test_separate_power_domains_and_ldo_pinout(self):
        check_rails(self.n)

    def test_boot_reset_nc_straps_and_programming(self):
        check_boot_and_programming(self.n)

    def test_fan_bec_pinmap_base_bias_tach_and_reset_release_topology(self):
        check_fan(self.n)

    def test_shared_powered_onewire_independent_position_and_i2c_inputs(self):
        check_sensor_buses(self.n)

    def test_dps_uart_direction_oe_and_both_data_input_biases(self):
        check_uart(self.n)

    def test_carrier_pin_rows_coils_reset_sleep_and_bulk_polarity(self):
        check_motor(self.n)

    def test_adc1_divider_voltage_and_rc_from_real_component_values(self):
        check_adc(self.n)

    def test_tec_connector_is_default_low_logic_only(self):
        check_tec_logic_only(self.n)

    def test_signal_net_renaming_does_not_change_requirements(self):
        root = copy.deepcopy(self.n.root)
        for net in root.findall("nets/net"):
            name = normalize(net.attrib["name"])
            if name not in {"GND", "+3V3", "+5V", "+12V", "VMOT"}:
                net.set("name", "renamed_signal_" + net.attrib["code"])
        n = Netlist(root)
        for check in DOMAIN_CHECKS:
            check(n)


class ElectricalMutationTests(unittest.TestCase):
    """Mutate real XML in memory; semantic checks must reject, not hash checks."""

    def setUp(self):
        self.root = copy.deepcopy(Netlist.load().root)

    def node(self, ref, pin):
        for net in self.root.findall("nets/net"):
            for node in net.findall("node"):
                if (node.get("ref"), node.get("pin")) == (ref, pin):
                    return net, node
        self.fail(f"mutation target missing: {ref}.{pin}")

    def disconnect(self, ref, pin):
        net, node = self.node(ref, pin)
        net.remove(node)

    def move(self, ref, pin, destination):
        target, _ = self.node(*destination)
        source, node = self.node(ref, pin)
        source.remove(node)
        target.append(node)

    def swap(self, a, b):
        net_a, node_a = self.node(*a)
        net_b, node_b = self.node(*b)
        net_a.remove(node_a)
        net_b.remove(node_b)
        net_b.append(node_a)
        net_a.append(node_b)

    def value(self, ref, value):
        self.root.find(f"components/comp[@ref='{ref}']/value").text = value

    def rejected(self, check):
        with self.assertRaises(RuleViolation):
            check(Netlist(self.root))

    def test_disconnected_esp_supply(self):
        self.disconnect("U1", "2")
        self.rejected(check_rails)

    def test_swapped_five_and_twelve_volt_rail_header(self):
        self.swap(("J2", "2"), ("J2", "3"))
        self.rejected(check_rails)

    def test_ldo_output_pin_miswired_to_five_volts(self):
        self.move("U2", "5", ("J2", "2"))
        self.rejected(check_rails)

    def test_tec_request_connected_to_motor_power(self):
        self.move("J10", "2", ("J1", "1"))
        self.rejected(check_tec_logic_only)

    def test_missing_tec_default_low_bias(self):
        self.disconnect("R10", "2")
        self.rejected(check_tec_logic_only)

    def test_swapped_bjt_collector_emitter(self):
        self.swap(("Q1", "2"), ("Q1", "3"))
        self.rejected(check_fan)

    def test_missing_fan_base_pulldown(self):
        self.disconnect("R9", "2")
        self.rejected(check_fan)

    def test_tach_pullup_to_twelve_volts(self):
        self.move("R6", "1", ("J2", "3"))
        self.rejected(check_fan)

    def test_wrong_fan_base_resistor(self):
        self.value("R8", "47")
        self.rejected(check_fan)

    def test_second_temperature_probe_on_wrong_bus(self):
        self.move("J5", "2", ("J6", "2"))
        self.rejected(check_sensor_buses)

    def test_onewire_pullup_to_five_volts(self):
        self.move("R3", "1", ("J2", "2"))
        self.rejected(check_sensor_buses)

    def test_duplicate_onewire_pullup(self):
        comp = copy.deepcopy(self.root.find("components/comp[@ref='R3']"))
        comp.set("ref", "R99")
        self.root.find("components").append(comp)
        for pin in ("1", "2"):
            net, node = self.node("R3", pin)
            node = copy.deepcopy(node)
            node.set("ref", "R99")
            net.append(node)
        self.rejected(check_sensor_buses)

    def test_index_home_swapped_at_mcu(self):
        self.swap(("U1", "8"), ("U1", "9"))
        self.rejected(check_sensor_buses)

    def test_critical_gpio_moved_to_flash_voltage_boot_strap(self):
        self.swap(("U1", "16"), ("U1", "14"))
        self.rejected(check_uart)
        self.rejected(check_boot_and_programming)

    def test_uart_oe_grounded_instead_of_reset_disabled(self):
        self.move("U3", "1", ("J2", "1"))
        self.rejected(check_uart)

    def test_uart_bias_removal_regresses_original_review_defect(self):
        for ref in ("R14", "R20", "R21"):
            with self.subTest(ref=ref):
                self.setUp()
                self.disconnect(ref, "2")
                self.rejected(check_uart)

    def test_dps_external_tx_bias_changed_to_backfeeding_pullup(self):
        self.move("R21", "2", ("U1", "2"))
        self.rejected(check_uart)

    def test_j9_rx_tx_crossed(self):
        self.swap(("J9", "2"), ("J9", "3"))
        self.rejected(check_uart)

    def test_uart_fault_current_resistor_wrong_decade(self):
        self.value("R15", "100")
        self.rejected(check_uart)

    def test_carrier_power_row_reversed(self):
        for pin in range(1, 5):
            self.swap(("J15", str(pin)), ("J15", str(9 - pin)))
        self.rejected(check_motor)

    def test_carrier_sleep_disconnected(self):
        self.disconnect("J14", "6")
        self.rejected(check_motor)

    def test_carrier_default_bias_too_weak_against_external_pullup(self):
        self.value("R11", "1M")
        self.rejected(check_motor)

    def test_motor_coils_mixed(self):
        self.swap(("J16", "1"), ("J17", "1"))
        self.rejected(check_motor)

    def test_motor_bulk_capacitor_reversed(self):
        self.swap(("C10", "1"), ("C10", "2"))
        self.rejected(check_motor)

    def test_adc_divider_resistors_swapped(self):
        self.value("R18", "10k")
        self.value("R19", "100k")
        self.rejected(check_adc)

    def test_adc_filter_disconnected(self):
        self.disconnect("C8", "2")
        self.rejected(check_adc)

    def test_boot_reset_capacitor_wrong_value(self):
        self.value("C5", "100n")
        self.rejected(check_boot_and_programming)


if __name__ == "__main__":
    unittest.main()
