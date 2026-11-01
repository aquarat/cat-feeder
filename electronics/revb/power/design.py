#!/usr/bin/env python3
"""Two reference-based buck blocks for Rev B; no full-board placement/layout.

Run to regenerate circuit.json. This is the integration pin-net contract.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DS = 'https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf'
INDUCTOR_DS = 'https://www.bourns.com/docs/product-datasheets/srn6045ta.pdf'
PIN_NAMES = {'1': 'FB', '2': 'EN', '3': 'VIN', '4': 'GND', '5': 'SW', '6': 'BST'}


def build():
    evidence = {x['componentCode']: x for x in json.loads((HERE / 'stock-evidence.json').read_text())}
    parts = []

    def add(ref, value, code, footprint, nets, role, **extra):
        e = evidence[code]
        parts.append(dict(ref=ref, value=value, lcsc=code,
                          mpn=e['componentModelEn'], manufacturer=e['componentBrandEn'],
                          footprint=footprint, pins={str(k): v for k, v in nets.items()},
                          role=role, datasheet=e['dataManualUrl'],
                          stock_evidence='stock-evidence.json#' + code,
                          assembly=e['assemblyMode'], **extra))

    for rail, output, ic, inductor, inductance, dcr, irms, isat in [
        (1, '+3V3', 'C780769', 'C2041457', 6.8e-6, .034, 3.6, 5.7),
        (2, '+12V', 'C2071044', 'C2046332', 10e-6, .052, 3.2, 4.6),
    ]:
        sw, bst = f'PWR_SW{rail}', f'PWR_BST{rail}'
        fb = '+3V3' if rail == 1 else 'PWR_FB12'
        add(f'UP{rail}', 'AP63203WU-7' if rail == 1 else 'AP63201WU-7', ic,
            'Package_TO_SOT_SMD:TSOT-23-6',
            {1: fb, 2: 'SYS_20V', 3: 'SYS_20V', 4: 'GND', 5: sw, 6: bst},
            'EN tied to VIN AFTER the hardware-qualified 20V PD load switch',
            pin_names=PIN_NAMES, manufacturer_datasheet=DS,
            symbol='Regulator_Switching:AP63203WU' if rail == 1 else 'Regulator_Switching:AP63201WU',
            vin_operating_max_V=32, output_budget_A=1.0 if rail == 1 else .5,
            switching_frequency_Hz=1.1e6 if rail == 1 else 500e3)
        add(f'LP{rail}', f'{inductance*1e6:g}uH', inductor,
            'Inductor_SMD:L_Bourns_SRN6045TA', {1: sw, 2: output},
            'Semi-shielded inductor; 6x6mm body, 4.5mm maximum height',
            symbol='Device:L', manufacturer_datasheet=INDUCTOR_DS,
            inductance_H=inductance, tolerance=.2, dcr_ohm=dcr, dcr_tolerance=.2,
            irms_A_typ=irms, isat_A_typ=isat, isat_definition='30% inductance loss at 25C')
        base = (rail - 1) * 10
        for offset in (1, 2):
            add(f'CP{base+offset}', '10u 50V X7R', 'C138687',
                'Capacitor_SMD:C_1210_3225Metric', {1: 'SYS_20V', 2: 'GND'},
                'Local input reservoir; two in parallel per converter for DC-bias margin',
                symbol='Device:C', capacitance_F=10e-6, voltage_V=50, tolerance=.1)
        for offset, a, b, role in [(3, 'SYS_20V', 'GND', 'High-frequency VIN bypass'),
                                    (4, bst, sw, 'Bootstrap: BST to SW, never to ground')]:
            add(f'CP{base+offset}', '100n 50V X7R', 'C14663',
                'Capacitor_SMD:C_0603_1608Metric', {1: a, 2: b}, role,
                symbol='Device:C', capacitance_F=100e-9, voltage_V=50, tolerance=.1)
        for offset in ((5, 6, 7, 8) if rail == 1 else (5, 6, 7)):
            add(f'CP{base+offset}', '22u 25V X5R', 'C12891',
                'Capacitor_SMD:C_1206_3216Metric', {1: output, 2: 'GND'},
                'Parallel output MLCC bank; DC-bias/loop qualification still required',
                symbol='Device:C', capacitance_F=22e-6, voltage_V=25, tolerance=.1)

    add('RP1', '249k 1%', 'C22918', 'Resistor_SMD:R_0603_1608Metric',
        {1: '+12V', 2: 'PWR_FB12'}, '12V feedback upper resistor; manufacturer table 1 value',
        symbol='Device:R', resistance_ohm=249000, tolerance=.01)
    add('RP2', '18k 1%', 'C25810', 'Resistor_SMD:R_0603_1608Metric',
        {1: 'PWR_FB12', 2: 'GND'}, '12V feedback lower resistor; Kelvin return to UP2 GND',
        symbol='Device:R', resistance_ohm=18000, tolerance=.01)
    add('CP18', '56p 50V C0G', 'C282507', 'Capacitor_SMD:C_0603_1608Metric',
        {1: '+12V', 2: 'PWR_FB12'}, 'Feedforward across upper feedback resistor, table 1',
        symbol='Device:C', capacitance_F=56e-12, voltage_V=50, tolerance=.05)
    return dict(
        status='Reference-based proposed circuit; not physically validated or laid out',
        input=dict(net='SYS_20V', nominal_V=20, qualification_range_V=[19, 21],
                   dependency='Hardware PD-qualified switched 20V bus, OFF for 5/9/12/15V fallback and contract loss'),
        outputs={'+3V3': dict(budget_A=1.0, loads='ESP32, A4988 logic and low-power peripherals'),
                 '+12V': dict(budget_A=.5, normal_fan_A=.14, loads='Noctua fan only')},
        upstream='DPS5005 20V input and motor power branch upstream of these converters; never through +12V or +3V3',
        parts=parts,
        reference_deviations=['AP63203 uses 6.8uH from manufacturer EVM rather than 3.9uH datasheet table',
                              'Two 10uF input each; four 22uF on 3.3V and three 22uF on 12V for derating/transient margin',
                              '12V nominal target is 11.8667V with manufacturer 249k/18k divider'],
        remove_old=['External 5V/12V input J2', 'AP2112K 3.3V LDO and its obsolete supply path'],
        preserve='ESP32 local 100nF/10uF decoupling, EN reset delay and signal interface biasing')


if __name__ == '__main__':
    (HERE / 'circuit.json').write_text(json.dumps(build(), indent=2) + '\n')
