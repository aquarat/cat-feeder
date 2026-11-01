#!/usr/bin/env python3
"""Validate and export current routed board. Run inside the KiCad container."""
import collections,csv,hashlib,json,pathlib,subprocess,zipfile
import pcbnew as p
import outline
import project_rules
import assembly
import validate_revision
root=pathlib.Path(__file__).parent
def run(*args):subprocess.run(['kicad-cli',*args],cwd=root,check=True)
b=p.LoadBoard(str(root/'feeder.kicad_pcb'))
p.ZONE_FILLER(b).Fill(b.Zones())
project_rules.save_board(root/'feeder.kicad_pcb',b)
rule_check=project_rules.validate(root/'feeder.kicad_pro')
run('sch','erc','--exit-code-violations','-o','erc.rpt','feeder.kicad_sch')
run('pcb','drc','--schematic-parity','--exit-code-violations','-o','drc.rpt','feeder.kicad_pcb')
run('sch','export','netlist','--format','kicadxml','-o','schematic-netlist.xml','feeder.kicad_sch')
run('sch','export','svg','-o','views','feeder.kicad_sch')
run('sch','export','pdf','-o','views/schematic.pdf','feeder.kicad_sch')
for name,layers in [('top','F.Cu,F.SilkS,Edge.Cuts'),('bottom','B.Cu,B.SilkS,Edge.Cuts'),('assembly','F.Fab,F.SilkS,Dwgs.User,Edge.Cuts')]:
    run('pcb','export','svg','--layers',layers,'--mode-single','--page-size-mode','2','--exclude-drawing-sheet','-o',f'views/{name}.svg','feeder.kicad_pcb')
run('pcb','export','gerbers','--use-drill-file-origin','--layers','F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts','-o','manufacturing/','feeder.kicad_pcb')
run('pcb','export','drill','--drill-origin','plot','--format','excellon','-o','manufacturing/','feeder.kicad_pcb')
b=p.LoadBoard(str(root/'feeder.kicad_pcb'))
parts=json.loads((root/'connectivity.json').read_text())
stock={x['componentCode']:x for x in json.loads((root/'stock-evidence.json').read_text())}
assert {f.GetReference() for f in b.GetFootprints()}=={a['ref'] for a in parts}
for a in parts:
    assert a['lcsc'] in stock and stock[a['lcsc']]['overseasStockCount']>0,a['ref']
    fp=next(f for f in b.GetFootprints() if f.GetReference()==a['ref'])
    for pad in fp.Pads():
        if pad.GetNumber() in a['nets']:assert pad.GetNetname()=='/'+a['nets'][pad.GetNumber()],(a['ref'],pad.GetNumber())
assembly_check=assembly.export(root,b,parts)
cpl=list(csv.DictReader((root/'assembly-cpl.csv').open()))
assert {a['Designator'] for a in cpl}=={a['ref'] for a in parts if a['assembly']=='SMT'}
assert all(0<float(a['Mid X'][:-2])<outline.XMAX-outline.XMIN and 0<float(a['Mid Y'][:-2])<80 for a in cpl)
groups={}
for a in parts:groups.setdefault((a['value'],a['fp'],a['lcsc']),[]).append(a['ref'])
with (root/'assembly-bom-all.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['Comment','Designator','Footprint','LCSC Part #'])
    for (value,fp,lcsc),refs in groups.items():w.writerow([value,','.join(refs),fp.split(':')[1],lcsc])
assert {a['Designator'] for a in csv.DictReader((root/'assembly-cpl-all.csv').open())}=={a['ref'] for a in parts}
widths=collections.defaultdict(set)
for t in b.GetTracks():
    if t.GetClass()=='PCB_TRACK':widths[t.GetNetname()].add(round(p.ToMM(t.GetWidth()),4))
for name in ['/M1A','/M1B','/M2A','/M2B']:assert min(widths[name])>=1.0
for name in ['/'+n for n in project_rules.POWER]:assert min(widths[name])>=.5
assert not any(t.GetClass()=='PCB_VIA' and t.GetNetname() in ['/M1A','/M1B','/M2A','/M2B'] for t in b.GetTracks())
# Only the low-current R18 divider spur necks down; VMOT load path is 1 mm.
for t in b.GetTracks():
    if t.GetClass()=='PCB_TRACK' and t.GetNetname()=='/VMOT' and p.ToMM(t.GetWidth())<1:
        assert p.ToMM(t.GetWidth())>=.8
        assert all(76.99<=p.ToMM(v.x)<=78.1 and 97.2<=p.ToMM(v.y)<=97.9 for v in [t.GetStart(),t.GetEnd()])
report={'tool':'KiCad 9.0.2','board_bounding_box_mm':[round(outline.XMAX-outline.XMIN,4),80],'outline':'shallow crescent; R141 outer/R91 inner; 2mm corner fillets','layers':2,'components':len(parts),
        'assembly_process_counts':dict(collections.Counter(a['assembly'] for a in parts)),
        'routing_vias':sum(t.GetClass()=='PCB_VIA' for t in b.GetTracks()),
        'track_segments':sum(t.GetClass()=='PCB_TRACK' for t in b.GetTracks()),
        'track_widths_mm':{k:sorted(v) for k,v in sorted(widths.items())},
        'ERC_violations':0,'DRC_violations':0,'unconnected':0,'schematic_parity_issues':0,
        'assembly_origin':'lower left corner of board bounding rectangle; +X right, +Y up',
        'project_configuration':rule_check,'centroid_validation':assembly_check,
        'BOM_CPL_and_design_connectivity':'passed','stock':'all 54 selected components had positive direct JLC stock; snapshot not reservation',
        'physical_testing':'none; no current, thermal, RF, EMC or enclosure qualification'}
(root/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
poly=p.SHAPE_POLY_SET();assert b.GetBoardPolygonOutlines(poly)
contour=poly.Outline(0)
points=[[p.ToMM(contour.CPoint(i).x),p.ToMM(contour.CPoint(i).y)] for i in range(contour.PointCount())]
validate_revision.validate(root,b,parts,points)
study={'status':'2D packaging study; housing/post/sink/height fit not verified',
       'KiCad_edge_polygon_area_mm2':poly.Area()/1e12,'rounded_rectangle_baseline_area_mm2':50*80-(4-3.141592653589793)*2**2,
       'bounding_box_mm':[outline.XMAX-outline.XMIN,80], 'radial_band_mm':[outline.INNER,outline.OUTER],
       'CAD_circle_center_mm':[outline.CX,outline.CY],'placement_origin_mm':list(outline.ORIGIN),
       'bore_radius_assumed_mm':146,'outer_radial_gap_mm':5,
       'fan_assumed_mm':[120,120],'minimum_gap_to_fan_circumscribed_circle_mm':91-(60**2+60**2)**.5,
       'enclosure_floor_assumed_z_mm':28,'board_z_mm':'not assigned; retain underside pin/air gap',
       'outline_vertices_KiCad_mm':points,
       'mapping_to_enclosure_xy':'x = KiCad_x + 41; y = 90 - KiCad_y; rotate around enclosure origin as needed'}
(root/'outline-study.json').write_text(json.dumps(study,indent=2)+'\n')
run('pcb','export','step','--board-only','--force','--drill-origin','-o','views/board-only.step','feeder.kicad_pcb')
with zipfile.ZipFile(root/'manufacturing-draft.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in sorted((root/'manufacturing').iterdir()):z.write(f,f.name)
project_rules.validate(root/'feeder.kicad_pro')  # CLI exports must preserve it too.
# Hash only after packaging.py and render-views.py regenerate dependent files.
# finalize.py creates the final manifest; do not certify a previous mesh/view.
