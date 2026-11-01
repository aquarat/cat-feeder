#!/usr/bin/env python3
"""On-board A4988 block: component/pin contract, not a released full PCB.

Run to regenerate circuit.json. Pin names transcribed from Allegro rev 8 p18;
pad 29 is our CAD name for the unnumbered exposed ground pad.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DS = 'https://www.allegromicro.com/-/media/files/datasheets/a4988-datasheet.pdf'
PIN_NAMES = dict(enumerate([
    'OUT2B', '~ENABLE', 'GND', 'CP1', 'CP2', 'VCP', 'NC', 'VREG',
    'MS1', 'MS2', 'MS3', '~RESET', 'ROSC', '~SLEEP', 'VDD', 'STEP',
    'REF', 'GND', 'DIR', 'NC', 'OUT1B', 'VBB1', 'SENSE1', 'OUT1A',
    'NC', 'OUT2A', 'SENSE2', 'VBB2', 'EP_GND'], 1))
PIN_NETS = dict(enumerate([
    'M2B', 'GND', 'GND', 'M_CP1', 'M_CP2', 'M_VCP', None, 'M_VREG',
    '+3V3', '+3V3', '+3V3', 'MOTOR_RUN', 'GND', 'MOTOR_RUN', '+3V3',
    'STEP', 'M_VREF', 'GND', 'DIR', None, 'M1B', 'VMOT', 'M_SENSE1',
    'M1A', None, 'M2A', 'M_SENSE2', 'VMOT', 'GND'], 1))


def build():
    evidence = {r['componentCode']: r for r in json.loads(
        (HERE / 'evidence/stock-evidence.json').read_text())}
    parts = []

    def add(ref, value, code, footprint, nets, role, **extra):
        e = evidence[code]
        parts.append(dict(ref=ref, value=value, lcsc=code,
            mpn=e['componentModelEn'], manufacturer=e['componentBrandEn'],
            footprint=footprint, pins={str(k): v for k, v in nets.items()},
            role=role, datasheet=DS if code == 'C38437' else e['dataManualUrl'],
            stock_evidence='evidence/stock-evidence.json#' + code,
            assembly=e['assemblyMode'], **extra))

    add('UM1', 'A4988SETTR-T', 'C38437',
        'motor:Allegro_A4988_ET_QFN28_5x5_P0.5_EP3.15', PIN_NETS,
        'Direct soldered motor driver replacing J14/J15 and Pololu module',
        pin_names={str(k): v for k, v in PIN_NAMES.items()},
        symbol='motor:A4988SETTR-T')
    r0603 = 'Resistor_SMD:R_0603_1608Metric'
    for ref, net, old in [('RM1', 'MOTOR_RUN', 'R11'), ('RM2', 'STEP', 'R12'), ('RM3', 'DIR', 'R13')]:
        add(ref, '10k', 'C25804', r0603, {1: net, 2: 'GND'},
            'Hardware pull-down; 10k also bounds the published input leakage',
            resistance_ohm=10000, tolerance=0.01, replaces_ref=old)
    add('RM4', '1k', 'C21190', r0603, {1: '+3V3', 2: 'M_VREF'},
        'Fixed reference upper divider; increase this resistor to reduce current',
        resistance_ohm=1000, tolerance=0.01)
    add('RM5', '1.5k', 'C22843', r0603, {1: 'M_VREF', 2: 'GND'},
        'Fixed reference lower divider; no potentiometer', resistance_ohm=1500, tolerance=0.01)
    for ref, net in [('RM6', 'M_SENSE1'), ('RM7', 'M_SENSE2')]:
        add(ref, '0.33R 0.5W 1%', 'C912788', 'Resistor_SMD:R_1206_3216Metric',
            {1: net, 2: 'GND'}, 'Bridge sense resistor; short power path and Kelvin pickup at pad',
            resistance_ohm=0.33, tolerance=0.01, tcr_ppm_per_K=200, power_W=0.5)
    add('RM8', '1R 2W 1%', 'C5127856', 'motor:Milliohm_HoLRT2512_ManufacturerLand',
        {1: 'MOTOR_SUPPLY', 2: 'VMOT'},
        'Motor-only series damping; pulse capability remains to be qualified',
        resistance_ohm=1.0, tolerance=0.01, power_W=2,
        qualification='Prototype candidate: do not infer inrush pulse rating from 2 W DC rating')
    c0603 = 'Capacitor_SMD:C_0603_1608Metric'
    for ref, value, code, a, b, role, capacitance, old in [
        ('CM1', '220n 50V X7R', 'C64705', 'M_VREG', 'GND', 'VREG bypass, close to pin 8', 220e-9, None),
        ('CM2', '100n 50V X7R', 'C14663', 'M_CP1', 'M_CP2', 'Flying charge-pump capacitor, pin 4 to 5', 100e-9, None),
        ('CM3', '100n 50V X7R', 'C14663', 'M_VCP', 'VMOT', 'Charge-pump reservoir: NOT to GND', 100e-9, None),
        ('CM4', '220n 50V X7R', 'C64705', '+3V3', 'GND', 'Local VDD bypass at pin 15', 220e-9, 'C9'),
        ('CM5', '1u 50V X5R', 'C15849', 'VMOT', 'GND', 'VBB1 bypass close to pin 22', 1e-6, None),
        ('CM6', '1u 50V X5R', 'C15849', 'VMOT', 'GND', 'VBB2 bypass close to pin 28', 1e-6, None),
        ('CM7', '100n 50V X7R', 'C14663', 'M_VREF', 'GND', 'Quiet reference filter, Kelvin ground', 100e-9, None),
    ]:
        add(ref, value, code, c0603, {1: a, 2: b}, role,
            capacitance_F=capacitance, voltage_V=50, replaces_ref=old)
    add('CM8', '100u 50V', 'C713402', 'Capacitor_THT:CP_Radial_D8.0mm_P5.00mm',
        {1: 'VMOT', 2: 'GND'}, 'Local bulk storage AFTER damping resistor; positive pin 1',
        capacitance_F=100e-6, voltage_V=50, replaces_ref='C10')
    term = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'
    for ref, a, b, old in [('JM1', 'M1A', 'M1B', 'J16'), ('JM2', 'M2A', 'M2B', 'J17')]:
        add(ref, 'MKDS 1,5/2-5,08 (1715721)', 'C5183929', term,
            {1: a, 2: b}, 'Retained motor winding screw terminal', replaces_ref=old)
    return dict(schema_version=1, status='BLOCK DESIGN / NOT ROUTED OR HARDWARE QUALIFIED',
        remove_from_revb=['J14', 'J15'], components=parts,
        interface={
            'MOTOR_SUPPLY': '20 V nominal negotiated PD branch, maximum steady input 21 V assumed; motor branch only',
            'VMOT': 'After RM8; existing BUS_SENSE divider may monitor this net',
            '+3V3': 'Regulated logic supply: current calculations require <=3.465 V (3.3 V +5%)',
            'STEP': 'ESP32 GPIO18 / WROOM pin 30',
            'DIR': 'ESP32 GPIO19 / WROOM pin 31',
            'MOTOR_RUN': 'ESP32 GPIO23 / WROOM pin 37; high wakes, low resets and sleeps',
            'GND': 'Common ground; local quiet/power star at exposed pad'},
        motor=dict(mpn='17HS08-1004S', rated_phase_current_A=1.0,
            resistance_ohm=3.7, inductance_H=0.0045,
            datasheet='https://files.omc-stepperonline.com/17HS08-1004S_Full_Datasheet.pdf',
            winding_wires={'JM1.1': 'black A+', 'JM1.2': 'green A-', 'JM2.1': 'red B+', 'JM2.2': 'blue B-'}),
        firmware=dict(microsteps=16, steps_per_turn=3200, wake_delay_ms_min=1,
            step_high_us_min=1, step_low_us_min=1, dir_setup_hold_ns_min=200,
            note='RUN=0 resets translator; re-home/maintain known home-compatible stop state. 30 degrees is 266 2/3 microsteps; use accumulated 266/267 counts plus physical position feedback.'),
        test_points=['VMOT', 'M_VREF', 'MOTOR_RUN', 'GND'],
        limitations=['No all-temperature guaranteed phase-current bound from the published 25 C / VREF=2 V accuracy table alone',
            'Damping is not a voltage clamp or regeneration protection',
            'No power, thermal, EMC or assembled-board measurements have been performed'])


if __name__ == '__main__':
    (HERE / 'circuit.json').write_text(json.dumps(build(), indent=2) + '\n')
