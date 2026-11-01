#!/usr/bin/env python3
"""Run in cat-feeder-kicad:local with repository mounted /work, working dir /work.

Reads installed KiCad 9 symbols and footprints and copies exact footprints here.
Does not invoke the frozen PCB generator or modify frozen artifacts.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'pcb'))
from generate import libsymbol, kids, kid, unq

circuit = json.loads((HERE / 'circuit.json').read_text())
out = HERE / 'power.pretty'
out.mkdir(exist_ok=True)
report = dict(kicad_version=pcbnew.Version(), footprints={}, symbols={})
for part in circuit['parts']:
    fp = part['footprint']
    library, name = fp.split(':')
    path = Path('/usr/share/kicad/footprints') / (library+'.pretty') / (name+'.kicad_mod')
    assert path.is_file(), fp
    obj = pcbnew.FootprintLoad(str(path.parent), name)
    assert obj is not None
    pads = {pad.GetNumber(): dict(x_mm=pcbnew.ToMM(pad.GetPosition().x),
                                 y_mm=pcbnew.ToMM(pad.GetPosition().y),
                                 size_x_mm=pcbnew.ToMM(pad.GetSize().x),
                                 size_y_mm=pcbnew.ToMM(pad.GetSize().y)) for pad in obj.Pads()}
    assert set(pads) == set(part['pins']), (part['ref'], pads, part['pins'])
    shutil.copyfile(path, out/path.name)
    report['footprints'][fp] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), pads=pads)
    symbol = libsymbol(part['symbol'])
    names = {}
    for unit in kids(symbol, 'symbol'):
        for pin in kids(unit, 'pin'):
            names[unq(kid(pin, 'number')[1])] = unq(kid(pin, 'name')[1])
    assert set(names) == set(part['pins']), (part['ref'], names)
    if part['ref'].startswith('UP'):
        assert names == {'1': 'FB', '2': 'EN', '3': 'IN', '4': 'GND', '5': 'SW', '6': 'BST'}, names
    report['symbols'][part['symbol']] = names
(HERE / 'kicad-audit.json').write_text(json.dumps(report, indent=2)+'\n')
print(f"Verified {len(report['footprints'])} footprints and {len(report['symbols'])} symbols on KiCad {pcbnew.Version()}")
