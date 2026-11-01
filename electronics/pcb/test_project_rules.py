"""Regression: real pcbnew saves retain rules; broken project classes fail checks.

Run inside KiCad container with TMPDIR pointing at writable scratch storage.
"""
import copy,json,pathlib,shutil,tempfile
import pcbnew as p
import project_rules
root=pathlib.Path(__file__).parent
with tempfile.TemporaryDirectory() as temp:
    dest=pathlib.Path(temp)
    for suffix in ['.kicad_pcb','.kicad_pro']:shutil.copy2(root/('feeder'+suffix),dest/('feeder'+suffix))
    path=dest/'feeder.kicad_pro';original=path.read_bytes()
    for _ in range(2):
        board=p.LoadBoard(str(dest/'feeder.kicad_pcb'))
        project_rules.save_board(dest/'feeder.kicad_pcb',board)
        assert path.read_bytes()==original
        project_rules.validate(path)
    good=json.loads(original)
    missing=copy.deepcopy(good);missing['net_settings']['classes']=[c for c in missing['net_settings']['classes'] if c['name']!='Motor']
    width=copy.deepcopy(good);next(c for c in width['net_settings']['classes'] if c['name']=='Power')['track_width']=.2
    patterns=copy.deepcopy(good);patterns['net_settings']['netclass_patterns'].pop()
    holes=copy.deepcopy(good);holes['board']['design_settings']['rules']['min_through_hole_diameter']=.3
    for label,bad in [('missing Motor',missing),('wrong Power width',width),('missing assignment',patterns),('wrong ESP32 hole rule',holes)]:
        path.write_text(json.dumps(bad))
        try:project_rules.validate(path)
        except AssertionError:pass
        else:raise AssertionError(f'Validator accepted {label}')
print('PASS: two real load/save cycles and four rejected configuration regressions')
