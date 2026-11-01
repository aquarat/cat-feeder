"""Review B2: explicit body datums, never pad averages or supplier-angle guesses.

Local coordinates are KiCad +X right/+Y down. Positive footprint rotation maps
(dx,dy) to (dx*cos+dy*sin,-dx*sin+dy*cos), THEN Gerber origin/Y reflection.
Source: actual local F.Fab bodies, reconciled to kb/pcb-review.md §§1/4.
Header/socket body dimensions remain provisional pending exact supplier drawings.
"""
import csv,json,math,pathlib
import pcbnew as p
import outline

# Exact LCSC keys deliberately prevent silently applying family corrections to
# substitutions. Entries: exact local footprint, native body centre, native pin 1.
DATUMS={
 'C701341':('ESP32-WROOM-32E',(0,0),(-8.75,-5.26)),
 'C51118':('SOT-23-5',(0,0),(-1.1375,-.95)),
 'C23654':('SOT-23-5',(0,0),(-1.1375,-.95)),
 'C20526':('SOT-23',(0,0),(-.9375,-.95)),
 'C25804':('R_0603_1608Metric',(0,0),(-.825,0)),
 'C25803':('R_0603_1608Metric',(0,0),(-.825,0)),
 'C23162':('R_0603_1608Metric',(0,0),(-.825,0)),
 'C21190':('R_0603_1608Metric',(0,0),(-.825,0)),
 'C15850':('C_0805_2012Metric',(0,0),(-.95,0)),
 'C14663':('C_0603_1608Metric',(0,0),(-.775,0)),
 'C15849':('C_0603_1608Metric',(0,0),(-.775,0)),
 'C713402':('CP_Radial_D8.0mm_P5.00mm',(2.5,0),(0,0)),
 'C5183929':('TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',(2.54,-.3),(0,0)),
 'C27438':('PinSocket_1x08_P2.54mm_Vertical',(0,8.89),(0,0)),
 'C49257':('PinHeader_1x03_P2.54mm_Vertical',(0,2.54),(0,0)),
 'C5116483':('PinHeader_1x04_P2.54mm_Vertical',(0,3.81),(0,0)),
 'C27985187':('PinHeader_1x02_P2.54mm_Vertical',(0,1.27),(0,0)),
}
LANDMARKS={
 'C701341':{'antenna_edge_midpoint':(0,-12.75)},
 'C713402':{'positive_lead':(0,0),'negative_lead':(5,0)},
 'C5183929':{'wire_entry_face_midpoint':(2.54,4.6)},
}
def rotate(v,angle):
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    return (v[0]*c+v[1]*s,-v[0]*s+v[1]*c)
def placed(v,origin,angle):return [a+b for a,b in zip(origin,rotate(v,angle))]
def fabrication(v):return [v[0]-outline.ORIGIN[0],outline.ORIGIN[1]-v[1]]
def close(a,b,tol=1e-6):assert all(abs(x-y)<tol for x,y in zip(a,b)),(a,b)
def point(v):return [p.ToMM(v.x),p.ToMM(v.y)]

def export(root,board,parts):
    root=pathlib.Path(root);stock={a['componentCode']:a for a in json.loads((root/'stock-evidence.json').read_text())}
    byref={f.GetReference():f for f in board.GetFootprints()}
    assert len(byref)==len(parts)==54
    close(point(board.GetDesignSettings().GetAuxOrigin()),outline.ORIGIN)
    assert set(DATUMS)=={a['lcsc'] for a in parts}
    records={};rows=[]
    for code,(name,offset,pin1) in DATUMS.items():
        local=p.FootprintLoad(str(root/'feeder.pretty'),name);assert local
        # Check against body geometry, excluding reference/value text and
        # courtyards. C10 uses its actual circular F.Fab body, not its '+' mark.
        shapes=[g for g in local.GraphicalItems() if g.GetLayer()==p.F_Fab and g.GetClass()=='PCB_SHAPE']
        if code=='C713402':
            circle=next(g for g in shapes if g.GetShape()==p.SHAPE_T_CIRCLE)
            close(point(circle.GetCenter()),offset)
            assert abs(p.ToMM(circle.GetRadius())-4)<1e-6
        else:
            pts=[point(v) for g in shapes for v in [g.GetStart(),g.GetEnd()]]
            close([(min(v[i] for v in pts)+max(v[i] for v in pts))/2 for i in [0,1]],offset)
        close(point(next(t for t in local.Pads() if t.GetNumber()=='1').GetPosition()),pin1)
        records[code]={'MPN':stock[code]['componentModelEn'],'footprint':name,
            'native_body_offset_mm':offset,'native_pin1_mm':pin1,
            'native_landmarks_mm':LANDMARKS.get(code,{}),
            'supplier_zero_angle_correction_deg':None,'supplier_origin_correction_mm':None,
            'supplier_status':'PENDING placement-library pad overlay; no correction invented',
            'body_evidence':'local F.Fab datum; exact header/socket body drawing still pending' if code in ['C27438','C49257','C5116483','C27985187'] else 'local F.Fab; independent review matched package/body',
            'placements':[]}
    for a in parts:
        code=a['lcsc'];name,offset,pin1=DATUMS[code];fp=byref[a['ref']]
        assert fp.GetFPID().GetLibItemName()==name and a['fp'].split(':')[1]==name
        origin=point(fp.GetPosition());angle=fp.GetOrientationDegrees()
        close(origin,a['pos'][:2]);assert abs((angle-a['pos'][2])%360)<1e-6
        assert fp.GetLayer()==p.F_Cu
        if a['assembly']=='SMT':close(offset,(0,0))
        body=placed(offset,origin,angle);centre=fabrication(body)
        pads=[{'number':t.GetNumber(),'net':t.GetNetname(),'KiCad_mm':point(t.GetPosition()),'fabrication_mm':fabrication(point(t.GetPosition()))} for t in fp.Pads()]
        actual_pin1=next(t['KiCad_mm'] for t in pads if t['number']=='1')
        close(actual_pin1,placed(pin1,origin,angle))
        landmarks={k:{'KiCad_mm':placed(v,origin,angle),'fabrication_mm':fabrication(placed(v,origin,angle))} for k,v in LANDMARKS.get(code,{}).items()}
        if code=='C713402':
            assert next(t['net'] for t in pads if t['number']=='1')=='/VMOT'
            assert next(t['net'] for t in pads if t['number']=='2')=='/GND'
            close(next(t['KiCad_mm'] for t in pads if t['number']=='2'),landmarks['negative_lead']['KiCad_mm'])
        record={'ref':a['ref'],'process':a['assembly'],'native_origin_KiCad_mm':origin,
                'body_centroid_KiCad_mm':body,'centroid_fabrication_mm':centre,
                'KiCad_rotation_deg':angle,'CPL_rotation_deg':angle,
                'pin1_fabrication_mm':fabrication(actual_pin1),'landmarks':landmarks,'pads':pads}
        records[code]['placements'].append(record)
        rows.append([a['ref'],f'{centre[0]:.4f}mm',f'{centre[1]:.4f}mm','top',f'{angle:.1f}'])
    # Independent numerical anchors detect rotation/reflection/order regressions.
    flat={a['ref']:a for c in records.values() for a in c['placements']}
    for ref,expected in {'J14':(59,99.89),'J15':(74.24,99.89),'C10':(84.5,94),
                         'J1':(88.04,122.7),'J12':(79.27,78.5),'J13':(55.27,72.2),'U1':(75,63)}.items():
        close(flat[ref]['body_centroid_KiCad_mm'],expected)
    close(flat['J14']['centroid_fabrication_mm'],(17.11772858835597,30.11))
    assert sum(a['process']=='THT' for a in flat.values())==18
    for suffix in ['', '-all']:
        selected={a['ref'] for a in parts if suffix or a['assembly']=='SMT'}
        with (root/f'assembly-cpl{suffix}.csv').open('w') as f:
            w=csv.writer(f);w.writerow(['Designator','Mid X','Mid Y','Layer','Rotation']);w.writerows(r for r in rows if r[0] in selected)
        exported=list(csv.DictReader((root/f'assembly-cpl{suffix}.csv').open()))
        assert len(exported)==len(selected) and {r['Designator'] for r in exported}==selected
        for r in exported:
            close([float(r[k][:-2]) for k in ['Mid X','Mid Y']],flat[r['Designator']]['centroid_fabrication_mm'],.000051)
    report={'status':'Designer correction for independent recheck; supplier angles pending',
            'origin_KiCad_mm':outline.ORIGIN,'axes':'CPL +X right/+Y up; native footprint +Y down',
            'formula':'rotate offset (dx*cos+dy*sin, -dx*sin+dy*cos); add native placement; subtract origin X and reflect Y',
            'parts_by_exact_LCSC':records,'verified_refs':len(flat),'THT_centroids_corrected':18,'SMT_origins_preserved':36}
    (root/'assembly-reconciliation.json').write_text(json.dumps(report,indent=2)+'\n')
    return {'refs_checked':len(flat),'THT_body_centroids':18,'SMT_centred_origins':36,'supplier_angles':'pending'}
