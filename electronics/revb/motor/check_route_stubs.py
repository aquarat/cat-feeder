#!/usr/bin/env python3
"""Clearance of suggested local F.Cu stubs/vias against actual loaded pad bounds.

This does not establish complete connectivity, drill clearance, stackup current
capacity, filled planes, or full-board DRC. Rectangular pad envelopes are a
conservative approximation for native rounded pads.
"""
import itertools
import json
import math
from check_layout import HERE, load


def point_segment(p, a, b):
    v=[b[0]-a[0],b[1]-a[1]]
    norm=v[0]**2+v[1]**2
    t=max(0,min(1,((p[0]-a[0])*v[0]+(p[1]-a[1])*v[1])/norm)) if norm else 0
    return math.hypot(p[0]-a[0]-t*v[0],p[1]-a[1]-t*v[1])


def cross(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def segments(a,b,c,d):
    # Proper intersection plus endpoint distances (also handles collinearity).
    if cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0: return 0
    return min(point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b))


def inside(p,box):
    return box[0]<=p[0]<=box[2] and box[1]<=p[1]<=box[3]


def segment_box(a,b,box):
    if inside(a,box) or inside(b,box): return 0
    corners=[[box[0],box[1]],[box[2],box[1]],[box[2],box[3]],[box[0],box[3]]]
    return min(segments(a,b,p,q) for p,q in zip(corners,corners[1:]+corners[:1]))


def check(placed,pads,source):
    by_id={p['id']:p for p in pads}
    vias={v['id']:v for v in source['vias']}
    violations=[]
    distances=[]
    strokes=[]
    def record(gap,a,b):
        distances.append([gap,a,b])
        if gap < .2-1e-6: violations.append(dict(a=a,b=b,gap_mm=gap))
    for i,r in enumerate(source['routes']):
        name=f'route{i+1}:{r["from"]}'
        assert by_id[r['from']]['net']==r['net']
        assert math.dist(by_id[r['from']]['xy_mm'],r['points'][0])<1e-6, name
        if 'to' in r:
            assert by_id[r['to']]['net']==r['net']
            assert math.dist(by_id[r['to']]['xy_mm'],r['points'][-1])<1e-6, name
        elif 'via' in r:
            v=vias[r['via']]
            assert v['net']==r['net'] and math.dist(v['xy_mm'],r['points'][-1])<1e-6
        else:
            assert r['net']=='GND' and inside(r['points'][-1],by_id['UM1.29']['copper_envelope_mm'])
        for a,b in zip(r['points'],r['points'][1:]):
            strokes.append((name,r['net'],r['width_mm'],a,b))
            for p in pads:
                if p['net']==r['net']: continue
                record(segment_box(a,b,p['copper_envelope_mm'])-r['width_mm']/2,name,p['id'])
    for a,b in itertools.combinations(strokes,2):
        if a[1]==b[1]: continue
        record(segments(a[3],a[4],b[3],b[4])-(a[2]+b[2])/2,a[0],b[0])
    for v in vias.values():
        for p in pads:
            if p['net']==v['net']: continue
            record(segment_box(v['xy_mm'],v['xy_mm'],p['copper_envelope_mm'])-v['diameter_mm']/2,v['id'],p['id'])
        for s in strokes:
            if s[1]==v['net']: continue
            record(point_segment(v['xy_mm'],s[3],s[4])-(v['diameter_mm']+s[2])/2,v['id'],s[0])
    for a,b in itertools.combinations(vias.values(),2):
        if a['net']==b['net']: continue
        record(math.dist(a['xy_mm'],b['xy_mm'])-(a['diameter_mm']+b['diameter_mm'])/2,a['id'],b['id'])
    return dict(status='PASS' if not violations else 'FAIL', route_count=len(source['routes']),
        via_count=len(vias), violations=violations,
        smallest_gaps_mm=sorted(distances)[:15],
        scope='Only supplied F.Cu stubs/via annuli versus actual pad envelopes and each other; not full-board DRC')


def render(source):
    base=(HERE/'layout.svg').read_text().replace('</svg>','')
    colours={'GND':'#15803d','VMOT':'#be123c','M_SENSE1':'#0369a1','M_SENSE2':'#0369a1','M_VREF':'#7c3aed'}
    for r in source['routes']:
        points=' '.join(f'{x},{y}' for x,y in r['points'])
        base+=f'<polyline points="{points}" stroke="{colours.get(r["net"],"#ea580c")}" stroke-width="{r["width_mm"]}" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity=".8"/>\n'
    for v in source['vias']:
        x,y=v['xy_mm']
        base+=f'<circle cx="{x}" cy="{y}" r="{v["diameter_mm"]/2}" fill="#334155"/><circle cx="{x}" cy="{y}" r="{v["drill_mm"]/2}" fill="#fff"/>\n'
    (HERE/'layout-stubs.svg').write_text(base+'</svg>\n')


if __name__=='__main__':
    placed,pads=load()
    source=json.loads((HERE/'critical-routes.json').read_text())
    result=check(placed,pads,source)
    (HERE/'route-stub-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    render(source)
    print(json.dumps(result,indent=2))
    assert result['status']=='PASS'
