#!/usr/bin/env python3
"""Block topology, sourcing and conservative current-envelope regression checks."""
import copy
import json
import unittest
from pathlib import Path
from design import build

HERE = Path(__file__).resolve().parent


def current_corner(top=1000, bottom=1500, sense=.33, error=.15):
    # Design assumptions: supply +5%; divider 1% initial +100ppm/K*100K;
    # sense 1% initial +200ppm/K*100K; reference current worst sourcing 3uA.
    rt = top * .98
    rb = bottom * 1.02
    vref = 3.3 * 1.05 * rb/(rt+rb) + 3e-6 * rt*rb/(rt+rb)
    return dict(vref_max_V=vref, sense_min_ohm=sense*.97,
                current_max_A=vref/(8*sense*.97)*(1+error),
                current_nominal_A=3.3*bottom/(top+bottom)/(8*sense))


def validate(d):
    parts = {p['ref']: p for p in d['components']}
    assert len(parts) == len(d['components'])
    u = parts['UM1']['pins']
    assert set(u) == set(map(str, range(1, 30)))
    for pin, net in {1:'M2B', 2:'GND', 3:'GND', 7:None, 9:'+3V3', 10:'+3V3',
                    11:'+3V3', 12:'MOTOR_RUN', 13:'GND', 14:'MOTOR_RUN', 15:'+3V3',
                    16:'STEP', 17:'M_VREF', 18:'GND', 19:'DIR', 20:None,
                    21:'M1B', 22:'VMOT', 23:'M_SENSE1', 24:'M1A', 25:None,
                    26:'M2A', 27:'M_SENSE2', 28:'VMOT', 29:'GND'}.items():
        assert u[str(pin)] == net, (pin, net)
    for ref, pins in {'CM1': [u['8'], 'GND'], 'CM2': [u['4'], u['5']],
                      'CM3': [u['6'], 'VMOT'], 'CM4':['+3V3','GND'],
                      'CM5':['VMOT','GND'], 'CM6':['VMOT','GND'],
                      'CM7':['M_VREF','GND'], 'CM8':['VMOT','GND'],
                      'RM6':[u['23'],'GND'], 'RM7':[u['27'],'GND'],
                      'RM8':['MOTOR_SUPPLY','VMOT'],
                      'RM4':['+3V3','M_VREF'], 'RM5':['M_VREF','GND']}.items():
        assert list(parts[ref]['pins'].values()) == pins, ref
    for ref, net in [('RM1','MOTOR_RUN'), ('RM2','STEP'), ('RM3','DIR')]:
        assert parts[ref]['pins'] == {'1':net, '2':'GND'}
        leakage = 40e-6 if ref == 'RM1' else 20e-6
        assert leakage * parts[ref]['resistance_ohm']*1.01 < 3.0*.3
    assert parts['CM1']['capacitance_F'] == 220e-9
    assert parts['CM2']['capacitance_F'] == parts['CM3']['capacitance_F'] == 100e-9
    for ref in ['CM1','CM2','CM3','CM5','CM6','CM8']:
        assert parts[ref]['voltage_V'] >= 50
    assert parts['RM4']['resistance_ohm'] >= 1000
    assert parts['RM5']['resistance_ohm'] == 1500
    assert parts['RM6']['resistance_ohm'] == parts['RM7']['resistance_ohm'] == .33
    corner = current_corner(parts['RM4']['resistance_ohm'])
    assert corner['current_max_A'] <= d['motor']['rated_phase_current_A']
    assert corner['current_max_A']*.33*1.03 < .5
    evidence = {r['componentCode']:r for r in json.loads((HERE/'evidence/stock-evidence.json').read_text())}
    for p in parts.values():
        e = evidence[p['lcsc']]
        assert p['mpn'] == e['componentModelEn']
        assert e['overseasStockCount'] >= 20, p['lcsc']
        assert p['datasheet'].startswith('https://')
    return corner


class BlockTests(unittest.TestCase):
    def test_design_and_saved_contract(self):
        self.assertEqual(build(), json.loads((HERE/'circuit.json').read_text()))
        validate(build())

    def test_dangerous_topology_mutations_rejected(self):
        for ref, pin, bad in [('UM1','29',None), ('UM1','23','GND'),
                              ('UM1','12','+3V3'), ('UM1','14','+3V3'),
                              ('UM1','25','GND'), ('CM3','2','GND'),
                              ('CM2','2','GND'), ('CM8','1','MOTOR_SUPPLY')]:
            d=copy.deepcopy(build())
            next(p for p in d['components'] if p['ref']==ref)['pins'][pin]=bad
            with self.subTest(ref=ref,pin=pin), self.assertRaises(AssertionError): validate(d)

    def test_overcurrent_and_weak_pulldown_rejected(self):
        for ref, value in [('RM4', 470), ('RM6', .1), ('RM1', 100000)]:
            d=copy.deepcopy(build())
            next(p for p in d['components'] if p['ref']==ref)['resistance_ohm']=value
            with self.subTest(ref=ref), self.assertRaises(AssertionError): validate(d)

    def test_lower_current_adjustment(self):
        self.assertAlmostEqual(current_corner(1500)['current_nominal_A'], .625)
        self.assertLess(current_corner(1500)['current_max_A'], 1)


if __name__ == '__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BlockTests))
    (HERE/'checks.json').write_text(json.dumps(dict(
        status='PASS' if result.wasSuccessful() else 'FAIL', tests_run=result.testsRun,
        default=current_corner(), reduced=current_corner(1500),
        default_using_published_5pct=current_corner(error=.05),
        status_scope='Topology and assumed tolerance arithmetic; not all-temperature guaranteed accuracy or measured waveforms'),indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
