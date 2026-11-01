"""Small deterministic grid finisher for two KiCad-detected SES import gaps.

Uses conservative pad envelopes and 0.35 mm planning clearance; final KiCad
DRC remains authoritative. Never waive clearance/connectivity violations.
"""
import heapq,math
import pathlib
import numpy as np
from PIL import Image,ImageDraw
import pcbnew as p
import outline
STEP=.1
X0,Y0=40.,57.
NX,NY=601,731
def xy(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def grid(v):return (round((p.ToMM(v.x)-X0)/STEP),round((p.ToMM(v.y)-Y0)/STEP))
def pos(x,y):return xy(X0+x*STEP,Y0+y*STEP)
def finish(b):
    for net,source,target in [('HOME',(66.25,67.9,0),(63.6122,75.7579,1)),('STEP',(83.75,67.9,0),(72.175,83.,0))]:
        route(b,net,source,target)
    # Retain reviewed SES copper; add the two bias resistors explicitly.
    for net,source,target,width in [
        ('DPS_TX',(79.825,113,0),(80.8625,104,0),.25),
        ('+3V3',(78.175,113,0),(81.175,110,0),.5),
        ('DPS_TX_EXT',(91,109.825,0),(94,106.08,1),.25),
    ]:route(b,net,source,target,width)
    # R21.2 connects through the newly refilled GND plane; final DRC checks it.
    return b

def route(b,net,source,target,width=.25):
    layers=[p.F_Cu,p.B_Cu]
    masks=[]
    for radius in [width/2,.3]:
        images=[Image.new('1',(NX,NY),0) for _ in layers]
        draws=[ImageDraw.Draw(i) for i in images]
        def point(v):return ((p.ToMM(v.x)-X0)/STEP,(p.ToMM(v.y)-Y0)/STEP)
        for layer,draw in zip(layers,draws):
            for f in b.GetFootprints():
                for pad in f.Pads():
                    if not pad.IsOnLayer(layer) or pad.GetNetname()==net:continue
                    box=pad.GetBoundingBox();margin=radius+.35
                    draw.rectangle(((p.ToMM(box.GetLeft())-margin-X0)/STEP,(p.ToMM(box.GetTop())-margin-Y0)/STEP,
                                    (p.ToMM(box.GetRight())+margin-X0)/STEP,(p.ToMM(box.GetBottom())+margin-Y0)/STEP),fill=1)
            for t in b.GetTracks():
                if not t.IsOnLayer(layer) or t.GetNetname()==net:continue
                w=p.ToMM(t.GetWidth(layer) if t.GetClass()=='PCB_VIA' else t.GetWidth())
                r=(w/2+radius+.35)/STEP
                a,c=point(t.GetStart()),point(t.GetEnd())
                draw.line([a,c],fill=1,width=math.ceil(2*r))
                for x,y in [a,c]:draw.ellipse((x-r,y-r,x+r,y+r),fill=1)
        array=np.array(images,dtype=bool)
        yy,xx=np.mgrid[0:NY,0:NX];xx=X0+xx*STEP;yy=Y0+yy*STEP
        rr=np.hypot(xx-outline.CX,yy-outline.CY)
        forbidden=(rr<outline.INNER+radius+.3)|(rr>outline.OUTER-radius-.3)|(yy>129.5)
        array|=forbidden
        masks.append(array)
    blocked,via_blocked=masks
    via_blocked=via_blocked[0]|via_blocked[1]
    # Same-net copper may be joined, but a new drill must never overlap an
    # existing drill. Include same-net holes in this separate via-only mask.
    holes=Image.new('1',(NX,NY),0);draw=ImageDraw.Draw(holes)
    for f in b.GetFootprints():
        for pad in f.Pads():
            drill=pad.GetDrillSize()
            if max(drill.x,drill.y)<=0:continue
            x,y=point(pad.GetPosition());r=(p.ToMM(max(drill.x,drill.y))/2+.15+.35)/STEP
            draw.ellipse((x-r,y-r,x+r,y+r),fill=1)
    for t in b.GetTracks():
        if t.GetClass()=='PCB_VIA':
            x,y=point(t.GetPosition());r=(p.ToMM(t.GetDrillValue())/2+.15+.35)/STEP
            draw.ellipse((x-r,y-r,x+r,y+r),fill=1)
    via_blocked|=np.array(holes,dtype=bool)
    sx,sy=grid(xy(*source[:2]));tx,ty=grid(xy(*target[:2]));start=(source[2],sy,sx);goal=(target[2],ty,tx)
    assert not blocked[start] and not blocked[goal],(net,'blocked endpoints',bool(blocked[start]),bool(blocked[goal]))
    queue=[(0,0,start)];cost={start:0};prev={}
    moves=[(dx,dy,math.hypot(dx,dy)) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]]
    while queue:
        _,g,node=heapq.heappop(queue)
        if g!=cost[node]:continue
        if node==goal:break
        layer,y,x=node
        choices=[]
        for dx,dy,w in moves:
            nx,ny=x+dx,y+dy
            if not(0<=nx<NX and 0<=ny<NY) or blocked[layer,ny,nx]:continue
            if dx and dy and (blocked[layer,y,nx] or blocked[layer,ny,x]):continue
            choices.append(((layer,ny,nx),w))
        if not via_blocked[y,x]:choices.append(((1-layer,y,x),35.))
        for nxt,w in choices:
            ng=g+w
            if ng>=cost.get(nxt,float('inf')):continue
            cost[nxt]=ng;prev[nxt]=node
            h=math.hypot(nxt[2]-tx,nxt[1]-ty)+(0 if nxt[0]==goal[0] else 35)
            heapq.heappush(queue,(ng+h,ng,nxt))
    else:raise RuntimeError(f'No route for {net}')
    nodes=[goal]
    while nodes[-1]!=start:nodes.append(prev[nodes[-1]])
    nodes.reverse();paths=[];current=[]
    for node in nodes:
        if current and node[0]!=current[-1][0]:
            paths.append(current);current=[]
            v=p.PCB_VIA(b);v.SetPosition(pos(node[2],node[1]));v.SetWidth(p.F_Cu,p.FromMM(.6));v.SetWidth(p.B_Cu,p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));b.Add(v)
        current.append(node)
    paths.append(current)
    def track(a,c,layer):
        if a==c:return
        t=p.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetLayer(layers[layer]);t.SetWidth(p.FromMM(width));t.SetNet(b.FindNet(net));b.Add(t)
    track(xy(*source[:2]),pos(sx,sy),source[2])
    for path in paths:
        keep=[path[0]]
        for a,n,c in zip(path,path[1:],path[2:]):
            if (n[1]-a[1],n[2]-a[2])!=(c[1]-n[1],c[2]-n[2]):keep.append(n)
        keep.append(path[-1])
        for a,c in zip(keep,keep[1:]):track(pos(a[2],a[1]),pos(c[2],c[1]),a[0])
    track(pos(tx,ty),xy(*target[:2]),target[2])
    print(f'Finished {net}: {len(nodes)} grid points; cost {cost[goal]:.1f}')
