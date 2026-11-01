#!/usr/bin/env python3
"""Derive short-route suggestions and previews from measured KiCad placements.

Checks conservative pad-bbox/trace-capsule clearance. Suggestions are not copper
in the placement boards and do not constitute a routed/DRC-clean board.
"""
import itertools
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent


def point_segment(pt, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    denom = dx*dx+dy*dy
    t = max(0, min(1, ((pt[0]-a[0])*dx+(pt[1]-a[1])*dy)/denom)) if denom else 0
    return math.hypot(pt[0]-a[0]-t*dx, pt[1]-a[1]-t*dy)


def segment_distance(a, b, c, d):
    def cross(a, b, c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    if cross(a,b,c)*cross(a,b,d) < 0 and cross(c,d,a)*cross(c,d,b) < 0:
        return 0
    return min(point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b))


def segment_box(a, b, box):
    x,y,xx,yy=box
    if any(x<=pt[0]<=xx and y<=pt[1]<=yy for pt in (a,b)): return 0
    corners=[(x,y),(xx,y),(xx,yy),(x,yy)]
    return min(segment_distance(a,b,c,d) for c,d in zip(corners,corners[1:]+corners[:1]))


def build():
    measured=json.loads((HERE/'layout-checks.json').read_text())
    output={'status':'Checked short-route suggestions only; no copper added to placement boards',
            'layers':'All suggested short routes F.Cu; reserve B.Cu mainly for continuous GND', 'blocks':{}}
    for name,block in measured['blocks'].items():
        parts=block['parts']; rail=1 if name=='logic' else 2; base=(rail-1)*10
        def pad(ref, pin): return parts[ref]['pads'][str(pin)]['center']
        def u(pin): return pad(f'UP{rail}',pin)
        def c(n,pin): return pad(f'CP{base+n}',pin)
        routes=[]
        def route(net,width,points,role):
            routes.append(dict(net=net,width_mm=width,points=points,role=role,
                               length_mm=sum(math.dist(a,b) for a,b in zip(points,points[1:]))))
        route('SYS_20V',.4,[u(3),[-1.1375,1.6],[-.775,1.9625],c(3,1)],'VIN to closest 100n bypass')
        route('GND',.4,[u(4),[1.1375,1.6],[.775,1.9625],c(3,2)],'Closest bypass return to IC ground')
        route('SYS_20V',.25,[u(2),u(3)],'EN to qualified VIN')
        route(f'PWR_SW{rail}',.6,[u(5),pad(f'LP{rail}',1)],'Short SW connection to inductor input')
        route(f'PWR_SW{rail}',.4,[[3,0],c(4,2)],'Short bootstrap SW branch')
        route(f'PWR_BST{rail}',.2,[u(6),[2.15,-.95],[2.15,-1.875],c(4,1)],'Bootstrap high-side connection')
        route('SYS_20V',.6,[c(3,1),[-1.475,3.55],c(1,1),c(2,1)],'Input reservoir positive bus')
        route('GND',.6,[c(3,2),[1.475,3.55],c(1,2),c(2,2)],'Input reservoir ground bus, stitch to plane')
        vout='+3V3' if rail==1 else '+12V'
        bank=list(range(5,9 if rail==1 else 8))
        route(vout,.8,[pad(f'LP{rail}',2),[9.575,3.65],[8.975,4.25]]+[c(i,1) for i in bank],
              'Output inductor to bank positive bus; sense at first capacitor')
        route('GND',.8,[c(i,2) for i in bank],'Output bank ground bus; multiple short plane vias')
        if rail==2:
            route('PWR_FB12',.2,[pad('RP1',2),pad('RP2',1)],'Local feedback divider midpoint')
            route('PWR_FB12',.2,[[-3.2,-.95],u(1)],'Quiet midpoint to IC FB, away from SW')
            route('PWR_FB12',.2,[pad('CP18',2),pad('RP1',2)],'Feedforward capacitor FB end')
            route('+12V',.2,[pad('CP18',1),pad('RP1',1)],'Feedforward output end')
        allpads=[(ref+'.'+pin,info) for ref,part in parts.items() for pin,info in part['pads'].items()]
        checks=[]
        for r in routes:
            for a,b in zip(r['points'],r['points'][1:]):
                for pin,info in allpads:
                    if info['net']!=r['net']:
                        checks.append((segment_box(a,b,info['copper_bbox'])-r['width_mm']/2,r['role'],pin))
        for r,s in itertools.combinations(routes,2):
            if r['net']==s['net']: continue
            for a,b in zip(r['points'],r['points'][1:]):
                for c0,d in zip(s['points'],s['points'][1:]):
                    checks.append((segment_distance(a,b,c0,d)-(r['width_mm']+s['width_mm'])/2,r['role'],s['role']))
        nearest=min(checks)
        assert nearest[0]>=.2-1e-6,(name,'short route clearance failed',nearest)
        output['blocks'][name]=dict(routes=routes,minimum_screened_clearance_mm=nearest[0],closest_pair=nearest[1:],
            sense_pickup=dict(ref=f'CP{base+5}',pin='1',center=c(5,1)),
            sense_routing_note='Complete a separate low-current Kelvin sense route to UP1.1 (logic), or RP1.1/CP18.1 (fan). Prefer B.Cu across y=4.65 below the inductor, then up the input/left side; never beneath SW or the inductor. Add endpoint vias in free copper, not capacitor pads. Final via/trace/plane checks belong to integrator.',
            ground_note='UP GND and closest input bypass form the primary local return. Stitch input/output ground buses to bottom plane. Fan RP2.2 requires a quiet return to local UP2 GND; do not join through motor/fan load return traces.')
        # Physical-scale preview: actual courtyard edges and conservative pad shapes.
        scale=52; margin=65; x0,y0,x1,y1=block['extent']
        def px(pt):return (round((pt[0]-x0)*scale+margin),round((pt[1]-y0)*scale+margin))
        im=Image.new('RGB',(round((x1-x0)*scale+2*margin),round((y1-y0)*scale+2*margin)), 'white')
        draw=ImageDraw.Draw(im);font=ImageFont.load_default(size=16)
        small=ImageFont.load_default(size=12)
        draw.text((12,12),f'{name}: {block["width_mm"]:.2f} x {block["height_mm"]:.2f} mm; purple = actual courtyard',fill='#333333',font=small)
        for ref,info in parts.items():
            for a,b in info['courtyard_edges']:draw.line([px(a),px(b)],fill='#8b279f',width=2)
            for pin,pp in info['pads'].items():
                box=pp['copper_bbox'];color='#91bba2' if pp['net']=='GND' else '#dcb884'
                draw.rectangle([px(box[:2]),px(box[2:])],fill=color)
                draw.text(px(pp['center']),pin,fill='black',anchor='mm',font=small)
        colors={'GND':'#328354','SYS_20V':'#b62b20','PWR_FB12':'#205ea1','+12V':'#cb7020','+3V3':'#cb7020'}
        for r in routes:
            draw.line([px(pt) for pt in r['points']],fill=colors.get(r['net'],'#b01d97'),width=max(2,round(r['width_mm']*scale)))
        for ref,info in parts.items():
            draw.text(px(info['placement'][:2]),ref,fill='#15324c',anchor='mm',font=font,stroke_width=1,stroke_fill='white')
        draw.ellipse([px([-.09,-.09]),px([.09,.09])],fill='red')
        im.save(HERE/(name+'-placement.png'))
        print(name,'checked route clearance',round(nearest[0],4),'mm')
    (HERE/'layout-routes.json').write_text(json.dumps(output,indent=2)+'\n')


if __name__=='__main__':build()
