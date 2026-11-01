"""Deterministic grid finisher for connections the Freerouting SES import leaves
open (rev A saw the same import gaps). Adapted from electronics/pcb/finish_route.py.

Plans 0.1 mm-grid paths on both copper layers around every foreign-net pad,
track and via with a conservative margin; KiCad DRC remains authoritative.
"""
import heapq, math
import numpy as np
from PIL import Image, ImageDraw
import pcbnew as p

STEP = .1
MARGIN = .3   # planning clearance beyond the 0.2-0.5 mm rule clearances


def xy(x, y): return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def route(b, net, a, c, width, box, via=(0.8, 0.4)):
    """a, c: (x_mm, y_mm, layer_index 0=F 1=B or None for THT). box: (x0, y0, x1, y1) mm."""
    X0, Y0, X1, Y1 = box
    NX, NY = int((X1 - X0) / STEP) + 1, int((Y1 - Y0) / STEP) + 1
    layers = [p.F_Cu, p.B_Cu]
    netcode = b.FindNet(net).GetNetCode()

    def pt(v): return ((p.ToMM(v.x) - X0) / STEP, (p.ToMM(v.y) - Y0) / STEP)
    masks = []
    for radius in (width / 2, via[0] / 2):
        imgs = [Image.new('1', (NX, NY), 0) for _ in layers]
        drs = [ImageDraw.Draw(i) for i in imgs]
        for li, layer in enumerate(layers):
            dr = drs[li]
            for f in b.GetFootprints():
                for pd in f.Pads():
                    if not pd.IsOnLayer(layer) or pd.GetNetCode() == netcode: continue
                    bb = pd.GetBoundingBox(); m = radius + MARGIN + .2
                    dr.rectangle(((p.ToMM(bb.GetLeft()) - m - X0) / STEP, (p.ToMM(bb.GetTop()) - m - Y0) / STEP,
                                  (p.ToMM(bb.GetRight()) + m - X0) / STEP, (p.ToMM(bb.GetBottom()) + m - Y0) / STEP), fill=1)
            for t in b.GetTracks():
                if t.GetNetCode() == netcode: continue
                if t.GetClass() == 'PCB_VIA':
                    x, y = pt(t.GetPosition()); r = (p.ToMM(t.GetWidth(p.F_Cu)) / 2 + radius + MARGIN + .2) / STEP
                    dr.ellipse((x - r, y - r, x + r, y + r), fill=1); continue
                if not t.IsOnLayer(layer): continue
                w = (p.ToMM(t.GetWidth()) / 2 + radius + MARGIN + .2) / STEP
                s, e = pt(t.GetStart()), pt(t.GetEnd())
                dr.line([s, e], fill=1, width=math.ceil(2 * w))
                for x, y in (s, e): dr.ellipse((x - w, y - w, x + w, y + w), fill=1)
            # Rule-area keep-outs that forbid tracks (e.g. under the TRACO TSR 2N) are obstacles too.
            for z in b.Zones():
                if not (z.GetIsRuleArea() and z.GetDoNotAllowTracks() and z.IsOnLayer(layer)): continue
                if z.GetZoneName() == 'edge keep-out': continue
                bb = z.GetBoundingBox(); m = radius + MARGIN
                dr.rectangle(((p.ToMM(bb.GetLeft()) - m - X0) / STEP, (p.ToMM(bb.GetTop()) - m - Y0) / STEP,
                              (p.ToMM(bb.GetRight()) + m - X0) / STEP, (p.ToMM(bb.GetBottom()) + m - Y0) / STEP), fill=1)
        arr = np.array(imgs, dtype=bool)
        yy, xx = np.mgrid[0:NY, 0:NX]
        edge = radius + 0.6
        arr[:, (yy * STEP + Y0 < Y0 + edge) | (yy * STEP + Y0 > Y1 - edge) | (xx * STEP + X0 < X0 + edge) | (xx * STEP + X0 > X1 - edge)] = True
        masks.append(arr)
    blocked, vb = masks
    vb = vb[0] | vb[1]
    holes = Image.new('1', (NX, NY), 0); dh = ImageDraw.Draw(holes)
    for f in b.GetFootprints():
        for pd in f.Pads():
            d = pd.GetDrillSize()
            if max(d.x, d.y) <= 0: continue
            x, y = pt(pd.GetPosition()); r = (p.ToMM(max(d.x, d.y)) / 2 + via[1] / 2 + .4) / STEP
            dh.ellipse((x - r, y - r, x + r, y + r), fill=1)
    vb |= np.array(holes, dtype=bool)

    def g(x, y): return (round((x - X0) / STEP), round((y - Y0) / STEP))
    sx, sy = g(*a[:2]); tx, ty = g(*c[:2])
    starts = [(l, sy, sx) for l in ((a[2],) if a[2] is not None else (0, 1))]
    goals = {(l, ty, tx) for l in ((c[2],) if c[2] is not None else (0, 1))}
    for s in starts: blocked[s] = False
    for s in goals: blocked[s] = False
    # Clear a small disc around the endpoints (they sit on same-net copper).
    for (cx, cy) in ((sx, sy), (tx, ty)):
        rr = int(1.0 / STEP)
        for L in (0, 1):
            ys, xs = np.ogrid[-rr:rr + 1, -rr:rr + 1]
            disc = xs * xs + ys * ys <= rr * rr
            y0, x0 = max(cy - rr, 0), max(cx - rr, 0)
            sub = blocked[L, y0:cy + rr + 1, x0:cx + rr + 1]
            d = disc[(y0 - (cy - rr)):(y0 - (cy - rr)) + sub.shape[0], (x0 - (cx - rr)):(x0 - (cx - rr)) + sub.shape[1]]
            ownpad = any(pd.GetNetCode() == netcode and pd.HitTest(xy(X0 + cx * STEP, Y0 + cy * STEP)) for f in b.GetFootprints() for pd in f.Pads())
            if ownpad: sub[d] = False
    q = [(0, 0, s) for s in starts]; cost = {s: 0 for s in starts}; prev = {}
    moves = [(dx, dy, math.hypot(dx, dy)) for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]]
    end = None
    while q:
        _, gc, node = heapq.heappop(q)
        if gc != cost[node]: continue
        if node in goals: end = node; break
        L, y, x = node; ch = []
        for dx, dy, w in moves:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < NX and 0 <= ny < NY) or blocked[L, ny, nx]: continue
            if dx and dy and (blocked[L, y, nx] or blocked[L, ny, x]): continue
            ch.append(((L, ny, nx), w))
        if not vb[y, x]: ch.append(((1 - L, y, x), 40.))
        for nxt, w in ch:
            ng = gc + w
            if ng >= cost.get(nxt, 1e18): continue
            cost[nxt] = ng; prev[nxt] = node
            heapq.heappush(q, (ng + math.hypot(nxt[2] - tx, nxt[1] - ty), ng, nxt))
    if end is None: return False
    nodes = [end]
    while nodes[-1] not in starts: nodes.append(prev[nodes[-1]])
    nodes.reverse()
    nobj = b.FindNet(net)

    def P(n): return xy(X0 + n[2] * STEP, Y0 + n[1] * STEP)
    seg = [nodes[0]]
    def flush(seg):
        keep = [seg[0]]
        for u, v, w in zip(seg, seg[1:], seg[2:]):
            if (v[1] - u[1], v[2] - u[2]) != (w[1] - v[1], w[2] - v[2]): keep.append(v)
        keep.append(seg[-1])
        for u, v in zip(keep, keep[1:]):
            if (u[1], u[2]) == (v[1], v[2]): continue
            t = p.PCB_TRACK(b); t.SetStart(P(u)); t.SetEnd(P(v)); t.SetLayer(layers[u[0]]); t.SetWidth(p.FromMM(width)); t.SetNet(nobj); b.Add(t)
    for n in nodes[1:]:
        if n[0] != seg[-1][0]:
            flush(seg)
            v = p.PCB_VIA(b); v.SetPosition(P(n)); v.SetWidth(p.F_Cu, p.FromMM(via[0])); v.SetWidth(p.B_Cu, p.FromMM(via[0]))
            v.SetDrill(p.FromMM(via[1])); v.SetViaType(p.VIATYPE_THROUGH); v.SetLayerPair(p.F_Cu, p.B_Cu); v.SetNet(nobj); b.Add(v)
            seg = [n]
        else:
            seg.append(n)
    flush(seg)
    for a_, layer in ((a, nodes[0][0]), (c, nodes[-1][0])):
        s = xy(a_[0], a_[1]); e = P(nodes[0] if a_ is a else nodes[-1])
        if s != e:
            t = p.PCB_TRACK(b); t.SetStart(s); t.SetEnd(e); t.SetLayer(layers[layer]); t.SetWidth(p.FromMM(width)); t.SetNet(nobj); b.Add(t)
    return True
