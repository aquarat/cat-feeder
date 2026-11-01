"""Preserve explicit project rules across pcbnew's lossy headless SaveBoard.

SaveBoard can serialize its default in-memory NET_SETTINGS over the project.
Keep the on-disk project authoritative, then verify it before CLI checks.
"""
import json
import pathlib
import pcbnew as p

WIDTHS={'Default':.25,'Motor':1.,'Power':.5}
MOTOR=['VMOT','M1A','M1B','M2A','M2B']
POWER=['GND','+3V3','+5V','+12V']
def validate(path):
    data=json.loads(pathlib.Path(path).read_text())
    classes={c['name']:c for c in data['net_settings']['classes']}
    assert set(classes)==set(WIDTHS),classes
    for name,width in WIDTHS.items():
        assert classes[name]['track_width']==width,(name,classes[name])
        assert classes[name]['clearance']==.2
        assert classes[name]['via_diameter']==.6 and classes[name]['via_drill']==.3
    patterns={(x['pattern'],x['netclass']) for x in data['net_settings']['netclass_patterns']}
    assert patterns=={(prefix+n,cls) for cls,names in [('Motor',MOTOR),('Power',POWER)] for prefix in ['', '/'] for n in names}
    ds=data['board']['design_settings']
    for key,value in {'min_clearance':.2,'min_track_width':.2,'min_via_diameter':.6,
                      'min_through_hole_diameter':.2,'min_copper_edge_clearance':.3,'min_hole_clearance':.25}.items():
        assert ds['rules'][key]==value,(key,ds['rules'][key])
    assert not ds.get('drc_exclusions',[])
    for key in ['clearance','shorting_items','unconnected_items','track_width','copper_edge_clearance']:
        assert ds.get('rule_severities',{}).get(key,'error')!='ignore',key
    return {'class_widths_mm':WIDTHS,'patterns_checked':len(patterns),'project_rules':'passed'}

def save_board(path,board):
    path=pathlib.Path(path);project=path.with_suffix('.kicad_pro')
    original=project.read_bytes() if project.exists() else None
    try:
        p.SaveBoard(str(path),board)
    finally:
        if original is not None:project.write_bytes(original)
