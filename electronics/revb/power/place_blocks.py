#!/usr/bin/env python3
"""Validate actual KiCad 9 local placements; emit placement-only block boards/SVG.

Coordinates use KiCad x-right, y-down and SetOrientationDegrees conventions.
Uses enclosing boxes of loaded F.CrtYd edges, not guessed body dimensions.
This is conservative for the TSOT's stepped courtyard; actual edges are exported.
Pad clearance uses conservative enclosing rectangles (also for rounded pads).
"""
import html
import itertools
import json
import math
from pathlib import Path
import pcbnew as p

HERE = Path(__file__).resolve().parent


def xy(x, y):
    return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def bounds(points):
    return [min(x for x, y in points), min(y for x, y in points),
            max(x for x, y in points), max(y for x, y in points)]


def gap(a, b):
    dx = max(a[0]-b[2], b[0]-a[2], 0)
    dy = max(a[1]-b[3], b[1]-a[3], 0)
    return math.hypot(dx, dy)


def rect_svg(box, color, fill='none', width=.06):
    x, y, xx, yy = box
    return f'<rect x="{x}" y="{y}" width="{xx-x}" height="{yy-y}" fill="{fill}" stroke="{color}" stroke-width="{width}"/>'


def build():
    layout = json.loads((HERE/'layout.json').read_text())
    parts = {x['ref']: x for x in json.loads((HERE/'circuit.json').read_text())['parts']}
    all_refs = [r for placements in layout.values() for r in placements]
    assert len(set(all_refs)) == len(all_refs) and set(all_refs) == set(parts)
    report = dict(kicad_version=p.Version(), units='mm',
                  convention='KiCad x right/y down; angles passed to SetOrientationDegrees',
                  status='Placement-only geometry and clearance check; unrouted, not main PCB', blocks={})
    for name, placements in layout.items():
        board = p.BOARD()
        shapes, pads, actual = {}, [], {}
        for ref, (x, y, angle) in placements.items():
            part = parts[ref]
            library, fpname = part['footprint'].split(':')
            fp = p.FootprintLoad('/usr/share/kicad/footprints/'+library+'.pretty', fpname)
            assert fp
            fp.SetReference(ref)
            fp.SetValue(part['value'])
            fp.SetPosition(xy(x, y))
            fp.SetOrientationDegrees(angle)
            board.Add(fp)
            points, edges = [], []
            for item in fp.GraphicalItems():
                if item.GetLayer() == p.F_CrtYd:
                    assert item.GetShape() == p.SHAPE_T_SEGMENT
                    edge = [(p.ToMM(v.x), p.ToMM(v.y)) for v in (item.GetStart(), item.GetEnd())]
                    edges.append(edge)
                    points.extend(edge)
            assert len(points) >= 8, (ref, 'missing courtyard edges')
            box = bounds(points)
            shapes[ref] = box
            actual[ref] = dict(placement=[x, y, angle], footprint=part['footprint'], courtyard=box, courtyard_edges=edges, pads={})
            for pad in fp.Pads():
                pin = pad.GetNumber()
                net = part['pins'][pin]
                if not board.FindNet(net):
                    board.Add(p.NETINFO_ITEM(board, net))
                pad.SetNet(board.FindNet(net))
                pos = [p.ToMM(pad.GetPosition().x), p.ToMM(pad.GetPosition().y)]
                bb = pad.GetBoundingBox()
                boxp = [p.ToMM(bb.GetX()), p.ToMM(bb.GetY()), p.ToMM(bb.GetRight()), p.ToMM(bb.GetBottom())]
                actual[ref]['pads'][pin] = dict(center=pos, net=net, copper_bbox=boxp)
                pads.append(dict(ref=ref, pin=pin, net=net, box=boxp))
        cgaps = [(gap(a, b), ra, rb) for (ra,a),(rb,b) in itertools.combinations(shapes.items(),2)]
        near_c = min(cgaps)
        assert near_c[0] >= .2-1e-6, (name, 'courtyard gap below 0.2mm', near_c)
        pgaps = [(gap(a['box'], b['box']), a['ref']+'.'+a['pin'], b['ref']+'.'+b['pin'])
                 for a,b in itertools.combinations(pads,2) if a['net'] != b['net']]
        near_p = min(pgaps)
        assert near_p[0] >= .2-1e-6, (name, 'different-net pad clearance', near_p)
        extent = bounds([(b[0],b[1]) for b in shapes.values()]+[(b[2],b[3]) for b in shapes.values()])
        result = dict(extent=extent, width_mm=extent[2]-extent[0], height_mm=extent[3]-extent[1],
                      minimum_courtyard_gap_mm=near_c[0], closest_courtyards=near_c[1:],
                      minimum_different_net_pad_bbox_clearance_mm=near_p[0], closest_pads=near_p[1:], parts=actual)
        report['blocks'][name] = result
        # Unrouted review aid with an edge margin, not a fabricated block design.
        x0,y0,x1,y1 = [extent[0]-.5,extent[1]-.5,extent[2]+.5,extent[3]+.5]
        for start,end in [((x0,y0),(x1,y0)),((x1,y0),(x1,y1)),((x1,y1),(x0,y1)),((x0,y1),(x0,y0))]:
            edge=p.PCB_SHAPE();edge.SetShape(p.SHAPE_T_SEGMENT);edge.SetStart(xy(*start));edge.SetEnd(xy(*end));edge.SetLayer(p.Edge_Cuts);edge.SetWidth(p.FromMM(.05));board.Add(edge)
        p.SaveBoard(str(HERE/(name+'-placement.kicad_pcb')),board)
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0-1} {y0-1} {x1-x0+2} {y1-y0+2}" width="900" height="1000">',
             rect_svg([x0-1,y0-1,x1+1,y1+1],'white','white'),rect_svg(extent,'#999')]
        for ref, info in actual.items():
            for (ax,ay),(bx,by) in info['courtyard_edges']:
                svg.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="#812cb3" stroke-width=".05"/>')
            for pin,pad in info['pads'].items():
                color = '#8ec7a0' if pad['net']=='GND' else '#d89d54'
                svg.append(rect_svg(pad['copper_bbox'],color,color))
                px,py=pad['center'];svg.append(f'<text x="{px}" y="{py+.11}" font-size=".38" text-anchor="middle">{html.escape(pin)}</text>')
            xx,yy,_=info['placement']
            svg.append(f'<text x="{xx}" y="{yy+.12}" font-size=".42" text-anchor="middle" fill="#143a66">{ref}</text>')
        svg.append('<circle cx="0" cy="0" r=".1" fill="red"/></svg>')
        (HERE/(name+'-placement.svg')).write_text('\n'.join(svg))
        print(name, result['width_mm'],result['height_mm'], 'courtyard',near_c,'pad clearance',near_p)
    (HERE/'layout-checks.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__': build()
