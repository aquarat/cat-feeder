"""Track geometry from the routed .kicad_pcb files and IPC-2152 temperature-rise estimates.

IPC-2152 is a chart standard; the closed-form fit used here is Brooks & Adam (PCD&F 2015) for external
conductors, as recorded in datasheets/datasheet_values.json ('IPC-2152_fit'):
    dT[C] = 215.3 * I[A]^2 * W[mil]^-1.15 * Th[mil]^-1
It describes the IPC-2152 baseline condition (1.6 mm FR-4, no copper planes, still air), i.e. it is
conservative for these 2-layer boards where a GND pour on the opposite side spreads heat.
"""
import math
from collections import defaultdict
from pathlib import Path

from . import sexpr

MIL = 0.0254  # mm
CU_1OZ_MM = 0.035


def ipc2152_dT(i_a, width_mm, thick_mm=CU_1OZ_MM, K=215.3, a=2.0, b=-1.15, c=-1.0):
    return K * abs(i_a) ** a * (width_mm / MIL) ** b * (thick_mm / MIL) ** c


def ipc2152_current(dT, width_mm, thick_mm=CU_1OZ_MM, K=215.3, a=2.0, b=-1.15, c=-1.0):
    return (dT / (K * (width_mm / MIL) ** b * (thick_mm / MIL) ** c)) ** (1 / a)


def load(path):
    tree = sexpr.parse(Path(path).read_text())
    names = {}
    for n in sexpr.children(tree, 'net'):
        nm = n[2] if len(n) > 2 else ''
        names[n[1]] = nm[1:] if nm.startswith('/') else nm
    segs, vias = defaultdict(list), defaultdict(list)
    for s in sexpr.children(tree, 'segment'):
        st = [float(x) for x in sexpr.child(s, 'start')[1:3]]
        en = [float(x) for x in sexpr.child(s, 'end')[1:3]]
        net = names.get(sexpr.value(s, 'net'), '?')
        w = float(sexpr.value(s, 'width'))
        segs[net].append(dict(layer=sexpr.value(s, 'layer'), width=w, start=tuple(st), end=tuple(en),
                              length=math.dist(st, en)))
    for v in sexpr.children(tree, 'via'):
        net = names.get(sexpr.value(v, 'net'), '?')
        vias[net].append(dict(at=tuple(float(x) for x in sexpr.child(v, 'at')[1:3]), drill=float(sexpr.value(v, 'drill')),
                              size=float(sexpr.value(v, 'size'))))
    return dict(segments=segs, vias=vias, path=str(path))


def _key(seg):
    a = tuple(round(x, 2) for x in seg['start'])
    b = tuple(round(x, 2) for x in seg['end'])
    return tuple(sorted((a, b)))


def net_rise(board, net, current, thick_mm=CU_1OZ_MM, plating_mm=0.018):
    """Worst-segment temperature rise for `current` through `net`. Segments duplicated on the other layer with
    the same end points share the current in proportion to width. Returns dict with the worst segment."""
    segs = board['segments'].get(net, [])
    if not segs:
        return None
    by_key = defaultdict(list)
    for s in segs:
        by_key[_key(s)].append(s)
    worst = None
    for key, group in by_key.items():
        wsum = sum(s['width'] for s in group)
        for s in group:
            ieff = current * s['width'] / wsum
            dT = ipc2152_dT(ieff, s['width'], thick_mm)
            rec = dict(net=net, layer=s['layer'], width_mm=s['width'], length_mm=round(s['length'], 2), parallel=len(group) > 1,
                       i_eff=ieff, dT=dT, start=s['start'])
            if worst is None or dT > worst['dT']:
                worst = rec
    total_len = sum(s['length'] for s in segs)
    min_w = min(s['width'] for s in segs)
    vias = board['vias'].get(net, [])
    out = dict(worst=worst, total_length_mm=round(total_len, 1), min_width_mm=min_w, n_segments=len(segs), n_vias=len(vias))
    if vias:
        # Via barrel as a conductor of width pi*drill and thickness = plating (estimate). Current shared equally only if
        # the vias are in parallel; assume the worst case of one via carrying the whole current.
        d = min(v['drill'] for v in vias)
        out['via_dT_single'] = ipc2152_dT(current, math.pi * d, plating_mm)
        out['via_drill_mm'] = d
    return out


def track_r_mohm(board, net, thick_mm=CU_1OZ_MM, temp_c=40.0):
    """Sum of segment resistances (series assumption) - an upper bound for the net's copper resistance."""
    rho = 1.72e-8 * (1 + 0.00393 * (temp_c - 20.0))
    r = 0.0
    for s in board['segments'].get(net, []):
        r += rho * (s['length'] * 1e-3) / (s['width'] * 1e-3 * thick_mm * 1e-3)
    return r * 1e3


def pads(path):
    """Absolute pad centres: list of dict(ref, pin, net, x, y, r) (r = half the larger pad dimension)."""
    tree = sexpr.parse(Path(path).read_text())
    out = []
    for fp in sexpr.children(tree, 'footprint'):
        at = sexpr.child(fp, 'at')
        X, Y = float(at[1]), float(at[2])
        th = math.radians(float(at[3])) if len(at) > 3 else 0.0
        ref = None
        for p in sexpr.children(fp, 'property'):
            if p[1] == 'Reference':
                ref = p[2]
        for pd in sexpr.children(fp, 'pad'):
            a = sexpr.child(pd, 'at')
            dx, dy = float(a[1]), float(a[2])
            x = X + dx * math.cos(th) + dy * math.sin(th)
            y = Y - dx * math.sin(th) + dy * math.cos(th)
            size = sexpr.child(pd, 'size')
            n = sexpr.child(pd, 'net')
            net = n[2] if n is not None and len(n) > 2 else ''
            out.append(dict(ref=ref, pin=pd[1], net=net[1:] if net.startswith('/') else net, x=x, y=y,
                            r=max(float(size[1]), float(size[2])) / 2 if size else 0.5))
    return out


def solve_net(board, padlist, net, inject, thick_mm=CU_1OZ_MM, temp_c=40.0):
    """Nodal solve of one net's copper (segments + vias + THT pads joining both layers).
    inject: {(ref, pin): current_A} (positive = into the copper; must sum to zero).
    Returns (segments with 'i' and 'dT', unconnected injection pads)."""
    import numpy as np
    rho = 1.72e-8 * (1 + 0.00393 * (temp_c - 20.0))
    segs = board['segments'].get(net, [])
    nodes = {}

    def node(layer, x, y, tol=0.05):
        for key, k in nodes.items():
            if key[0] == layer and abs(key[1] - x) < tol and abs(key[2] - y) < tol:
                return k
        k = len(nodes)
        nodes[(layer, x, y)] = k
        return k
    edges = []
    netpads = [p for p in padlist if p['net'] == net]
    # Split segments at T-junctions: other segment ends (same layer) and pad centres lying on the track.
    for s in segs:
        (x0, y0), (x1, y1) = s['start'], s['end']
        L = math.hypot(x1 - x0, y1 - y0)
        cuts = {0.0, 1.0}
        if L > 1e-6:
            pts = [e for o in segs if o is not s and o['layer'] == s['layer'] for e in (o['start'], o['end'])]
            pts += [(p['x'], p['y']) for p in netpads]
            for px, py in pts:
                t = ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / (L * L)
                if 0.0 < t < 1.0:
                    d = abs((px - x0) * (y1 - y0) - (py - y0) * (x1 - x0)) / L
                    if d <= s['width'] / 2:
                        cuts.add(round(t, 6))
        cuts = sorted(cuts)
        for t0, t1 in zip(cuts, cuts[1:]):
            pa = (x0 + t0 * (x1 - x0), y0 + t0 * (y1 - y0))
            pb = (x0 + t1 * (x1 - x0), y0 + t1 * (y1 - y0))
            a = node(s['layer'], *pa)
            b = node(s['layer'], *pb)
            ln = L * (t1 - t0)
            r = rho * (ln * 1e-3) / (s['width'] * 1e-3 * thick_mm * 1e-3)
            sub = dict(s, start=pa, end=pb, length=ln)
            edges.append((a, b, max(r, 1e-7), sub))
    # vias join F and B at their location
    for v in board['vias'].get(net, []):
        a = node('F.Cu', *v['at'])
        b = node('B.Cu', *v['at'])
        edges.append((a, b, 2e-3, None))
    # pads: THT pads join every segment end that lies on them (both layers)
    pad_node = {}
    for j, p in enumerate(netpads):
        k = len(nodes)
        nodes[('PAD', p['ref'], p['pin'], j)] = k
        if (p['ref'], p['pin']) in pad_node:   # multi-hole pins (fuse clips, MSTB) are joined by the part's metal
            edges.append((k, pad_node[(p['ref'], p['pin'])], 1e-5, None))
        else:
            pad_node[(p['ref'], p['pin'])] = k
        for key, n in list(nodes.items()):
            if key[0] in ('F.Cu', 'B.Cu') and math.hypot(key[1] - p['x'], key[2] - p['y']) <= p['r'] + 0.05:
                edges.append((k, n, 1e-6, None))
    n = len(nodes)
    G = np.zeros((n, n))
    for a, b, r, _ in edges:
        g = 1.0 / r
        G[a, a] += g; G[b, b] += g; G[a, b] -= g; G[b, a] -= g
    I = np.zeros(n)
    missing = []
    for key, cur in inject.items():
        if key in pad_node:
            I[pad_node[key]] += cur
        else:
            missing.append(key)
    # connected components: solve each one that contains injections, grounding one node per component
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, r, _ in edges:
        parent[find(a)] = find(b)
    comps = {}
    for k in range(n):
        comps.setdefault(find(k), []).append(k)
    V = np.zeros(n)
    islands = []
    for root, members in comps.items():
        if not np.any(I[members]):
            continue
        if abs(I[members].sum()) > 1e-9:
            islands.append([key for key, k in nodes.items() if k in members and key[0] == 'PAD'])
        ref = members[0]
        keep = members[1:]
        if keep:
            V[keep] = np.linalg.solve(G[np.ix_(keep, keep)], I[keep])
    out = []
    for a, b, r, s in edges:
        if s is None:
            continue
        i = (V[a] - V[b]) / r
        out.append(dict(layer=s['layer'], width_mm=s['width'], length_mm=round(s['length'], 2), start=s['start'], i=abs(i),
                        dT=ipc2152_dT(i, s['width'], thick_mm)))
    vias_i = []
    for a, b, r, s in edges:
        if s is None and r == 2e-3:
            vias_i.append(abs(V[a] - V[b]) / r)
    if islands:
        missing.append(('copper islands with unbalanced injection', islands))
    return out, missing, vias_i
