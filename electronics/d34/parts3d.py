#!/usr/bin/env python3
"""Write electronics/d34/parts3d.json: per-part 3D envelopes for the CAD fit agent.

    ./run.sh parts3d.py            (inside cat-feeder-kicad:local, after export.py)

Reads the routed <card>.kicad_pcb files (footprint origin, rotation, F.Fab and
pad geometry) and catalog.py (heights, module stacks, mated-plug envelopes,
datasheet references). Schema 'd34-parts3d/1' is documented in the file itself
and in README.md; keep it stable (add keys, never rename them).
"""
import datetime, hashlib, json, pathlib
import pcbnew as p
import catalog, design

ROOT = pathlib.Path(__file__).resolve().parent
BOARD_T = 1.6

CONVENTIONS = {
    'units': 'mm',
    'frame': ('Per card. Origin = top-left corner of the card seen from the component side. '
              '+x along the long edge to the right; +y DOWN towards the slot edge (y = 0 is the top/clip edge, '
              'y = 47 sits in the floor slot); +z out of the component side. z = 0 is the component-side copper '
              'surface, the solder-side surface is z = -1.6. NOTE: (x, y-down, z-out) is LEFT-handed; for a '
              'right-handed frame use v = 47 - y (v up) with the same x and z.'),
    'rotation_deg': 'KiCad footprint orientation, counter-clockwise as seen from the component side (KiCad convention, y down).',
    'origin': 'KiCad footprint anchor in card coordinates (usually pin 1).',
    'shapes': ('Axis-aligned. box: {"type":"box","min":[x,y,z],"max":[x,y,z]}. '
               'cylinder: {"type":"cylinder","axis":"z","centre":[x,y],"r":r,"z":[z0,z1]}.'),
    'groups': ('bodies = the part as fitted (component side, z >= 0); solder = lead/tail protrusion below the '
               'board (z <= -1.6) after trimming; mated = mating plug or plug-in module that is not soldered '
               '(present in service); cable = keep-clear zone for the wire bundle as it leaves the plug '
               '(includes a bend allowance); service = space needed to fit/remove the plug or module '
               '(not occupied in service).'),
    'lead_exit': 'Unit vector (card frame) in which wires leave the mated plug, plus the face centre they leave from.',
    'source': ('Each shape carries "src": datasheet | footprint | estimate. "datasheet" dimensions are from the '
               'PDF named in "ref_doc" (manifest: datasheets/MANIFEST.json); "footprint" = KiCad F.Fab outline; '
               '"estimate" = not yet confirmed - add margin.'),
    'status': 'Geometry derived from footprints and datasheets. Not a measured/physical fit.',
}


def mm(v): return round(p.ToMM(v), 3)


def box(x0, y0, z0, x1, y1, z1, what, src, **kw):
    d = dict(type='box', min=[round(min(x0, x1), 3), round(min(y0, y1), 3), round(min(z0, z1), 3)],
             max=[round(max(x0, x1), 3), round(max(y0, y1), 3), round(max(z0, z1), 3)], what=what, src=src)
    d.update(kw); return d


def cyl(cx, cy, r, z0, z1, what, src, **kw):
    d = dict(type='cylinder', axis='z', centre=[round(cx, 3), round(cy, 3)], r=round(r, 3), z=[round(z0, 3), round(z1, 3)],
             what=what, src=src)
    d.update(kw); return d


def local_to_card(fp, ox, oy):
    """Return f(lx, ly) -> card (x, y) for footprint-local coordinates (unrotated, mm)."""
    pos = fp.GetPosition(); px, py = p.ToMM(pos.x) - ox, p.ToMM(pos.y) - oy
    a = round(fp.GetOrientationDegrees()) % 360
    def f(lx, ly):
        # KiCad: CCW rotation as seen on screen with y down -> (x, y) -> (x cos + y sin, -x sin + y cos)
        if a == 0: rx, ry = lx, ly
        elif a == 90: rx, ry = ly, -lx
        elif a == 180: rx, ry = -lx, -ly
        elif a == 270: rx, ry = -ly, lx
        else: raise ValueError(a)
        return px + rx, py + ry
    return f


def lbox(T, lx0, ly0, lx1, ly1, z0, z1, what, src, **kw):
    (ax, ay), (bx, by) = T(lx0, ly0), T(lx1, ly1)
    return box(ax, ay, z0, bx, by, z1, what, src, **kw)


def exit_dir(T, lx, ly):
    (ax, ay), (bx, by) = T(0, 0), T(lx, ly)
    return [round(bx - ax, 3) + 0.0, round(by - ay, 3) + 0.0, 0.0]


def part_record(B, a, fp, ox, oy):
    c = catalog.get(a); g = catalog.geometry(a.kind)
    T = local_to_card(fp, ox, oy)
    xs, ys = [], []
    for it in fp.GraphicalItems():
        if it.GetLayer() == p.F_Fab and it.GetClass() not in ('PCB_TEXT', 'PCB_FIELD'):
            r = it.GetBoundingBox(); xs += [mm(r.GetLeft()) - ox, mm(r.GetRight()) - ox]; ys += [mm(r.GetTop()) - oy, mm(r.GetBottom()) - oy]
    fab = (min(xs), min(ys), max(xs), max(ys)) if xs else None
    pads = [(mm(pd.GetPosition().x) - ox, mm(pd.GetPosition().y) - oy, mm(max(pd.GetSize(p.F_Cu).x, pd.GetSize(p.F_Cu).y)) / 2)
            for pd in fp.Pads() if pd.GetDrillSize().x > 0 and pd.GetNumber()]
    rec = dict(ref=a.ref, kind=a.kind, value=a.value, mfr=c['mfr'], mpn=c['mpn'],
               footprint=str(fp.GetFPID().GetLibItemName()),
               origin=[round(p.ToMM(fp.GetPosition().x) - ox, 3), round(p.ToMM(fp.GetPosition().y) - oy, 3)],
               rotation_deg=round(fp.GetOrientationDegrees()) % 360,
               ref_doc=g.get('doc', ''), bodies=[], solder=[], mated=[], cable=[], service=[], lead_exit=None, notes=g.get('note', ''))
    # ---------------------------------------------------------------- component side
    if g.get('local'):
        for sh in g['local']:
            grp, lx0, ly0, lx1, ly1, z0, z1, what, src = sh
            rec[grp].append(lbox(T, lx0, ly0, lx1, ly1, z0, z1, what, src))
    elif g.get('cyl'):
        r, h, src = g['cyl']
        # Radial can: centre = midpoint of the two leads.
        (x1, y1), (x2, y2) = [(px, py) for px, py, _ in pads[:2]]
        rec['bodies'].append(cyl((x1 + x2) / 2, (y1 + y2) / 2, r, 0.0, h, 'can', src))
    elif fab:
        rec['bodies'].append(box(fab[0], fab[1], 0.0, fab[2], fab[3], g.get('h', c.get('h', 0)), 'body (F.Fab outline x height)',
                                 g.get('h_src', 'estimate')))
    # ---------------------------------------------------------------- mated plug and cable
    if g.get('plug'):
        if g['plug'][0] == 'fab':   # plug footprint = header body outline (+ margin)
            _, ztop, src = g['plug']; m = g.get('plug_margin', 0.0)
            (px0, py0), (px1, py1) = (fab[0] - m, fab[1] - m), (fab[2] + m, fab[3] + m)
            T_ = lambda x, y: (x, y)
        else:
            px0, py0, px1, py1, ztop, src = g['plug']; T_ = T
        rec['mated'].append(lbox(T_, px0, py0, px1, py1, 0.0, ztop, 'mated plug housing', src))
        bend = g.get('bend', 10.0)
        cx, cy = T_((px0 + px1) / 2, (py0 + py1) / 2)
        if g.get('side_exit'):   # wires leave a vertical face of the plug, parallel to the card
            z0, z1, L = g['side_exit']
            for sgn in (-1, 1):
                y0_, y1_ = (py0 - L, py0) if sgn < 0 else (py1, py1 + L)
                rec['cable'].append(box(px0, y0_, z0, px1, y1_, z1, f'wire entry side {"-y" if sgn < 0 else "+y"} ({L:g} mm straight + bend; '
                                        'only one side is used, orientation unverified)', 'estimate'))
            rec['lead_exit'] = dict(direction=[0.0, 1.0, 0.0], alternative_direction=[0.0, -1.0, 0.0],
                                    face_centre=[round(cx, 3), round(py1, 3), round((z0 + z1) / 2, 3)],
                                    note='wires leave horizontally from one long face of the plug; screws are reached from +z')
        else:
            rec['cable'].append(lbox(T_, px0, py0, px1, py1, ztop, ztop + bend, f'wire bundle leaving plug top (incl. {bend:g} mm bend allowance)', 'estimate'))
            rec['lead_exit'] = dict(direction=[0.0, 0.0, 1.0], face_centre=[round(cx, 3), round(cy, 3), round(ztop, 3)],
                                    note='wires leave the top of the plug (+z), then bend along the card')
        if g.get('service'):
            rec['service'].append(lbox(T_, px0, py0, px1, py1, ztop, ztop + g['service'], 'finger/insertion clearance (not occupied in service)', 'estimate'))
    if g.get('exit'):   # module-specific exits (e.g. DevKit USB)
        lx, ly, ex, ey, z, note = g['exit']
        cx, cy = T(lx, ly)
        rec['lead_exit'] = dict(direction=exit_dir(T, ex, ey), face_centre=[round(cx, 3), round(cy, 3), z], note=note)
    # ---------------------------------------------------------------- solder side
    prot = g.get('protrusion', 2.5)
    if pads:
        r = max(pp[2] for pp in pads)
        x0 = min(pp[0] for pp in pads) - r; x1 = max(pp[0] for pp in pads) + r
        y0 = min(pp[1] for pp in pads) - r; y1 = max(pp[1] for pp in pads) + r
        rec['solder'].append(box(x0, y0, -BOARD_T - prot, x1, y1, -BOARD_T,
                                 f'solder fillets and lead ends, {prot:g} mm below the solder side (trim leads)', g.get('prot_src', 'estimate')))
    rec['max_z'] = round(max([s['max'][2] if s['type'] == 'box' else s['z'][1] for s in rec['bodies'] + rec['mated'] + rec['cable']] + [0]), 3)
    return rec


def main():
    out = dict(schema='d34-parts3d/1', generated=datetime.date.today().isoformat(), conventions=CONVENTIONS, cards={})
    srcs = []
    for key in ('ctrl', 'pwr', 'tec'):
        B = design.BOARDS[key]()
        pcb = ROOT / B.name / f'{B.name}.kicad_pcb'
        srcs.append(pcb)
        b = p.LoadBoard(str(pcb)); ox, oy = B.origin
        parts = []
        for a in B.parts:
            fp = next(f for f in b.GetFootprints() if f.GetReference() == a.ref)
            parts.append(part_record(B, a, fp, ox, oy))
        envelope = dict(component_side_max_z=max(r['max_z'] for r in parts),
                        solder_side_min_z=min([s['min'][2] for r in parts for s in r['solder']] + [-BOARD_T]))
        out['cards'][B.name] = dict(bay=B.bay, kicad_pcb=f'{B.name}/{B.name}.kicad_pcb',
                                    board=dict(outline=[0.0, 0.0, B.width, B.height], thickness=BOARD_T, corner_radius=1.0,
                                               edge_bands_mm=B.band, z_component_surface=0.0, z_solder_surface=-BOARD_T),
                                    envelope=envelope, parts=parts)
    h = hashlib.sha256()
    for s in srcs: h.update(s.read_bytes())
    out['source_pcb_sha256'] = h.hexdigest()
    (ROOT / 'parts3d.json').write_text(json.dumps(out, indent=1) + '\n')
    for n, c in out['cards'].items():
        print(n, len(c['parts']), 'parts', c['envelope'])


if __name__ == '__main__':
    main()
