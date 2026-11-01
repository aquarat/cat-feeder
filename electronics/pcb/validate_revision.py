"""Checks missing from generic ERC/DRC: input bias, data joins and preservation."""
import csv,hashlib,json,xml.etree.ElementTree as ET
import pcbnew as p
from assembly import close,point

def validate(root,board,parts,outline_points):
    baseline=json.loads((root/'review-baseline.json').read_text())
    footprints={f.GetReference():f for f in board.GetFootprints()}
    for ref,pos in baseline['placements_KiCad_mm_deg'].items():
        f=footprints[ref];close(point(f.GetPosition())+[f.GetOrientationDegrees()],pos)
    assert set(footprints)-set(baseline['placements_KiCad_mm_deg'])=={'R20','R21'}
    digest=hashlib.sha256(json.dumps(outline_points,separators=(',',':')).encode()).hexdigest()
    assert digest==baseline['outline_vertices_compact_json_sha256'],'outline changed'
    nodes={}
    xml=ET.parse(root/'schematic-netlist.xml').getroot()
    for net in xml.findall('./nets/net'):
        for node in net.findall('node'):nodes[(node.attrib['ref'],node.attrib['pin'])]=net.attrib['name']
    partmap={a['ref']:a for a in parts}
    for ref,nets in {'R20':{'1':'+3V3','2':'DPS_TX'},'R21':{'1':'DPS_TX_EXT','2':'GND'}}.items():
        a=partmap[ref]
        assert a['value']=='10k' and a['lcsc']=='C25804' and a['nets']==nets
        comp=next(c for c in xml.findall('./components/comp') if c.attrib['ref']==ref)
        assert comp.findtext('value')=='10k'
        assert next(v.text for v in comp.findall('./fields/field') if v.attrib['name']=='LCSC')=='C25804'
    for ref,pin,net in [('U3','2','DPS_TX'),('U4','2','DPS_TX_EXT'),('R14','1','+3V3'),
                        ('R14','2','UART_OEn'),('R15','1','DPS_TX_BUF'),('R15','2','DPS_RX_EXT')]:
        assert partmap[ref]['nets'][pin]==net
    assert partmap['R14']['value']=='10k' and partmap['R15']['value']=='1k'
    checked=0
    for a in parts:
        actual={t.GetNumber():t.GetNetname() for t in footprints[a['ref']].Pads()}
        for pin,net in a['nets'].items():
            assert nodes[(a['ref'],pin)]==actual[pin]=='/'+net,(a['ref'],pin,net)
            checked+=1
    for suffix in ['', '-all']:
        expected={a['ref'] for a in parts if suffix or a['assembly']=='SMT'};seen=[]
        for row in csv.DictReader((root/f'assembly-bom{suffix}.csv').open()):
            for ref in row['Designator'].split(','):
                seen.append(ref);a=partmap[ref]
                assert row['LCSC Part #']==a['lcsc'] and row['Comment']==a['value']
                assert row['Footprint']==a['fp'].split(':')[1]
        assert len(seen)==len(set(seen)) and set(seen)==expected
        cpl=list(csv.DictReader((root/f'assembly-cpl{suffix}.csv').open()))
        assert len(cpl)==len(expected) and {a['Designator'] for a in cpl}==expected
    result={'baseline_PCB_sha256':baseline['PCB_sha256'],'original_placements_preserved':52,
            'outline_unchanged':True,'new_placements_KiCad_mm_deg':{r:partmap[r]['pos'] for r in ['R20','R21']},
            'B1_value_code_and_pad_netlist_checks':'passed','schematic_nodes_compared_to_PCB':checked,
            'BOM_values_codes_footprints_unique_refs_and_CPL_membership':'passed',
            'independent_recheck':'pending; D25 HOLD remains'}
    (root/'review-fix-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
