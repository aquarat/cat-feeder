#!/usr/bin/env python3
"""Import local autorouter result, pour ground, export only the current board."""
import csv,json,pathlib,sys,re
import pcbnew as p
import outline
import finish_route
import project_rules
ROOT=pathlib.Path(__file__).resolve().parent
def xy(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
b=p.LoadBoard(str(ROOT/'feeder-unrouted.kicad_pcb'))
assert p.ImportSpecctraSES(b,str(ROOT/(sys.argv[1] if len(sys.argv)>1 else 'feeder.ses')))
b=finish_route.finish(b)
gnd=b.FindNet('GND')
for layer in [p.F_Cu,p.B_Cu]:
    z=p.ZONE(b);z.SetLayer(layer);z.SetNet(gnd);z.SetLocalClearance(p.FromMM(.2))
    z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetMinThickness(p.FromMM(.2))
    z.SetThermalReliefGap(p.FromMM(.25));z.SetThermalReliefSpokeWidth(p.FromMM(.4))
    z.Outline().NewOutline()
    # Fill clips to the actual curved board edge and its copper clearance.
    for x,y in [(40,57),(101,57),(101,131),(40,131)]:
        z.Outline().Append(p.FromMM(x),p.FromMM(y))
    b.Add(z)
p.ZONE_FILLER(b).Fill(b.Zones())
b.GetDesignSettings().SetAuxOrigin(xy(*outline.ORIGIN))
for net in b.GetNetInfo().NetsByNetcode().values():
    if net.GetNetname():net.SetNetname('/'+net.GetNetname())
# KiCad assigns named singleton nets to intentional schematic no-connect pins.
nc={'U1':{4:'SENSOR_VP',5:'SENSOR_VN',13:'IO14',14:'IO12',17:'NC',18:'NC',19:'NC',20:'NC',21:'NC',22:'NC',23:'IO15',24:'IO2',26:'IO4',29:'IO5',32:'NC'},'U2':{4:'NC'}}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        pin=nc.get(fp.GetReference(),{}).get(int(pad.GetNumber()))
        if pin:
            net=p.NETINFO_ITEM(b,f'unconnected-({fp.GetReference()}-{pin}-Pad{pad.GetNumber()})');b.Add(net);pad.SetNet(net)
project_rules.save_board(ROOT/'feeder.kicad_pcb',b)
project_rules.validate(ROOT/'feeder.kicad_pro')
# Remove duplicate SES segments and its dead-end +5V branch in serialized form.
# pcbnew 9's Remove() corrupted SWIG objects on this imported board; text
# cleanup avoids that API failure and the result is reloaded by final DRC.
seen=set()
def clean_segment(match):
    text=match.group(0)
    get=lambda key:re.search(r'\('+key+r'\s+([^)]*)\)',text).group(1)
    ends=tuple(sorted([get('start'),get('end')]))
    key=(get('layer'),get('net'),get('width'),ends)
    dead=get('layer')=='"B.Cu"' and ends==('77.2878 76.846','78.0438 76.846')
    if key in seen or dead:return ''
    seen.add(key);return text
path=ROOT/'feeder.kicad_pcb'
path.write_text(re.sub(r'\(segment\s+(?:[^()]|\([^()]*\))*\)',clean_segment,path.read_text()))
parts=json.loads((ROOT/'connectivity.json').read_text());groups={}
for a in parts:
    if a['lcsc'] and a['assembly']=='SMT':groups.setdefault((a['value'],a['fp'],a['lcsc']),[]).append(a['ref'])
with (ROOT/'assembly-bom.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['Comment','Designator','Footprint','LCSC Part #'])
    for (value,fp,lcsc),refs in groups.items():w.writerow([value,','.join(refs),fp.split(':')[1],lcsc])
with (ROOT/'assembly-cpl.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['Designator','Mid X','Mid Y','Layer','Rotation'])
    for fp in b.GetFootprints():
        a=next(x for x in parts if x['ref']==fp.GetReference())
        if a['assembly']=='SMT':
            w.writerow([fp.GetReference(),f'{p.ToMM(fp.GetPosition().x)-outline.ORIGIN[0]:.4f}mm',f'{outline.ORIGIN[1]-p.ToMM(fp.GetPosition().y):.4f}mm','top',f'{fp.GetOrientationDegrees():.1f}'])
print('Imported tracks:',len(b.GetTracks()),'Ground zones filled; CPL is KiCad rotation convention, supplier visual alignment still required.')
with (ROOT/'quotation-bom-all.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['Designator','Comment','Footprint','LCSC Part #','Assembly process','Supplier URL'])
    for a in parts:w.writerow([a['ref'],a['value'],a['fp'].split(':')[1],a['lcsc'],a['assembly'],'https://jlcpcb.com/partdetail/'+a['lcsc']])
