#!/usr/bin/env python3
"""Check actual KiCad footprint placement; no complete board routing is implied.

Courtyard bounds are conservative (include line stroke). Copper checks use the
rotated rectangular envelope of each pad, including roundrect corner material
that is not actually copper. All supplied placements are orthogonal rotations.
"""
import itertools
import json
import math
from pathlib import Path
import pcbnew

HERE = Path(__file__).resolve().parent
SEPARATE = {'RM8', 'CM8', 'JM1', 'JM2'}


def mm(n):
    return round(pcbnew.ToMM(n), 7)


def box_record(box):
    return [mm(box.GetLeft()), mm(box.GetTop()), mm(box.GetRight()), mm(box.GetBottom())]


def separation(a, b):
    dx = max(a[0]-b[2], b[0]-a[2], 0)
    dy = max(a[1]-b[3], b[1]-a[3], 0)
    return math.hypot(dx, dy)


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def load():
    design = json.loads((HERE/'circuit.json').read_text())
    layout = json.loads((HERE/'layout.json').read_text())
    parts = {p['ref']: p for p in design['components']}
    assert set(parts) == set(layout), 'Missing or additional placement reference'
    assert layout['UM1'] == [0, 0, 0]
    placed, pads = {}, []
    for ref, p in parts.items():
        library, name = p['footprint'].split(':')
        folder = HERE/'footprints/motor.pretty' if library == 'motor' else Path('/usr/share/kicad/footprints')/(library+'.pretty')
        fp = pcbnew.FootprintLoad(str(folder), name)
        assert fp is not None, p['footprint']
        x, y, angle = layout[ref]
        assert angle % 90 == 0
        fp.SetOrientationDegrees(angle)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        courts = [box_record(g.GetBoundingBox()) for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_CrtYd]
        assert courts, ref
        court = [min(b[0] for b in courts), min(b[1] for b in courts),
                 max(b[2] for b in courts), max(b[3] for b in courts)]
        placed[ref] = dict(placement=layout[ref], courtyard_bbox_mm=court, pads={})
        for pad in fp.Pads():
            pin = pad.GetNumber()
            if not pin or not pad.IsOnLayer(pcbnew.F_Cu): continue
            pos, size = pad.GetPosition(), pad.GetSize()
            cx, cy = mm(pos.x), mm(pos.y)
            sx, sy = mm(size.x), mm(size.y)
            if round(pad.GetOrientationDegrees()) % 180 == 90: sx, sy = sy, sx
            rect = [cx-sx/2, cy-sy/2, cx+sx/2, cy+sy/2]
            net = p['pins'][pin]
            r = dict(id=ref+'.'+pin, ref=ref, pin=pin, xy_mm=[cx, cy],
                     net=net, copper_envelope_mm=rect)
            pads.append(r)
            placed[ref]['pads'][pin] = r
    return placed, pads


def svg(placed, pads):
    # Drawing directly from KiCad-extracted coordinates; core view only.
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-11 -11 22 22" width="880" height="880">',
             '<rect x="-11" y="-11" width="22" height="22" fill="#fff"/>',
             '<rect x="-10" y="-10" width="20" height="20" fill="#f8fafc" stroke="#64748b" stroke-width=".05"/>']
    for ref, part in placed.items():
        if ref in SEPARATE: continue
        a,b,c,d=part['courtyard_bbox_mm']
        lines.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" fill="none" stroke="#a855f7" stroke-width=".04"/>')
        x,y,_=part['placement']
        lines.append(f'<text x="{x}" y="{y+.12}" text-anchor="middle" font-family="sans-serif" font-size=".34">{ref}</text>')
    for pad in pads:
        if pad['ref'] in SEPARATE: continue
        a,b,c,d=pad['copper_envelope_mm']
        colour='#16a34a' if pad['net']=='GND' else '#c2410c'
        lines.append(f'<rect x="{a}" y="{b}" width="{c-a}" height="{d-b}" fill="{colour}" fill-opacity=".6"/>')
        x,y=pad['xy_mm']
        lines.append(f'<text x="{x}" y="{y+.07}" text-anchor="middle" font-family="sans-serif" font-size=".18">{pad["pin"]}</text>')
    lines.append('</svg>')
    (HERE/'layout.svg').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    placed, pads=load()
    intersections=[]
    for (a,pa),(b,pb) in itertools.combinations(placed.items(),2):
        if overlaps(pa['courtyard_bbox_mm'],pb['courtyard_bbox_mm']): intersections.append([a,b])
    violations=[]
    distances=[]
    for a,b in itertools.combinations(pads,2):
        if a['net'] is not None and a['net']==b['net']: continue
        gap=separation(a['copper_envelope_mm'],b['copper_envelope_mm'])
        distances.append((gap,a['id'],b['id']))
        if gap < .2-1e-6: violations.append(dict(a=a['id'],b=b['id'],gap_mm=gap))
    courts=[p['courtyard_bbox_mm'] for r,p in placed.items() if r not in SEPARATE]
    core=[min(b[0] for b in courts),min(b[1] for b in courts),max(b[2] for b in courts),max(b[3] for b in courts)]
    within=core[0]>=-10 and core[1]>=-10 and core[2]<=10 and core[3]<=10
    report=dict(status='PASS' if not intersections and not violations and within else 'FAIL',
        scope='Actual KiCad footprints: conservative courtyard/pad envelopes only; no complete routing/thermal/assembly validation',
        kicad_version=pcbnew.GetBuildVersion(), units='mm',
        coordinate_convention='KiCad board coordinates: +x right, +y down; rotations passed to SetOrientationDegrees',
        separate_anchors=sorted(SEPARATE), core_bbox_mm=core,
        core_size_mm=[core[2]-core[0],core[3]-core[1]], fits_20mm_square=within,
        courtyard_intersections=intersections, pad_clearance_violations=violations,
        smallest_different_net_pad_gaps_mm=sorted(distances)[:15], footprints=placed)
    (HERE/'layout-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    svg(placed,pads)
    print(json.dumps({k:v for k,v in report.items() if k!='footprints'},indent=2))
    assert report['status']=='PASS'
