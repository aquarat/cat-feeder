#!/usr/bin/env python3
"""Run in KiCad 9 container; validates actual pads and inventories native lands."""
import json
from pathlib import Path
import pcbnew

HERE = Path(__file__).resolve().parent
lib = HERE / 'footprints/motor.pretty'
name = 'Allegro_A4988_ET_QFN28_5x5_P0.5_EP3.15'
fp = pcbnew.FootprintLoad(str(lib), name)
assert fp is not None
numbered = {p.GetNumber(): p for p in fp.Pads() if p.GetNumber()}
assert set(numbered) == {str(i) for i in range(1, 30)}
def mm(v): return round(pcbnew.ToMM(v), 6)
def record(p):
    return dict(pin=p.GetNumber(), xy_mm=[mm(p.GetPosition().x), mm(p.GetPosition().y)],
                size_mm=[mm(p.GetSize().x), mm(p.GetSize().y)])
for i in range(1, 29):
    p = record(numbered[str(i)])
    side, j = divmod(i-1, 7)
    xy = [[-2.4, -1.5+j*.5], [-1.5+j*.5, 2.4], [2.4, 1.5-j*.5], [1.5-j*.5, -2.4]][side]
    assert p['xy_mm'] == xy
    assert sorted(p['size_mm']) == [.3, 1.15]
assert record(numbered['29'])['size_mm'] == [3.15, 3.15]
assert record(numbered['29'])['xy_mm'] == [0, 0]
native = {}
for n in ['Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_1206_3216Metric',
          'Resistor_SMD:R_2512_6332Metric', 'Capacitor_SMD:C_0603_1608Metric',
          'Capacitor_THT:CP_Radial_D8.0mm_P5.00mm',
          'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',
          'Package_DFN_QFN:QFN-28-1EP_5x5mm_P0.5mm_EP3.1x3.1mm']:
    folder, part = n.split(':')
    f = pcbnew.FootprintLoad('/usr/share/kicad/footprints/' + folder + '.pretty', part)
    assert f is not None, n
    native[n] = [record(p) for p in f.Pads() if p.GetNumber()]
out = dict(kicad_version=pcbnew.GetBuildVersion(), status='PASS: pad geometry only',
    custom=dict(name=name, pads=[record(p) for p in numbered.values()],
        adjacent_pin_copper_gap_mm=.2, pin_to_EP_gap_mm=.25,
        ep_paste_area_ratio=9*.83**2/3.15**2), native=native)
rd = pcbnew.FootprintLoad(str(lib), 'Milliohm_HoLRT2512_ManufacturerLand')
assert rd is not None
rp = {p.GetNumber(): record(p) for p in rd.Pads()}
assert rp['1']['xy_mm'] == [-3.25, 0] and rp['2']['xy_mm'] == [3.25, 0]
assert rp['1']['size_mm'] == rp['2']['size_mm'] == [1.6, 3.4]
out['damping_manufacturer_land'] = rp
(HERE / 'footprint-checks.json').write_text(json.dumps(out, indent=2) + '\n')
print('PASS: KiCad loaded all selected footprints; exact 29-pad Allegro geometry checked')
