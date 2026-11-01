#!/usr/bin/env python3
"""Check and export one routed D34 board (inside cat-feeder-kicad:local).

    ./run.sh export.py ctrl|pwr

Fails on any ERC/DRC violation (all severities) or unconnected item. Writes
ERC/DRC reports, Gerber + Excellon zip for JLCPCB (fabrication only), SVG and
3D-raytraced PNG views, BOM CSV, envelope/height data and validation.json.
"""
import collections, csv, json, pathlib, shutil, subprocess, sys, zipfile
import pcbnew as p
import build, catalog, design

ROOT = build.ROOT
PCBTRAIN_README = '''Cat feeder D34 controller - {name}
Bare board only (no assembly). 2 layers, FR-4 1.6 mm, 1 oz (35 um) copper, green mask both sides,
white legend both sides, any lead-free finish (immersion silver acceptable; boards are hand-soldered).
Board outline {w:g} x {h:g} mm, 1 mm corner radii, on layer Edge_Cuts (0.1 mm line; use the centreline).
Gerber RS-274X (no X2 attributes), viewed from the top, not mirrored. Excellon drill, metric, absolute
origin: *-PTH.drl plated holes, *-NPTH.drl non-plated holes (one polarising peg hole per fan header).
Minimum track 0.30 mm (power 0.6-2.5 mm), minimum clearance 0.20 mm, vias 0.8/0.4 mm, smallest
finished hole 0.4 mm (vias), no slots, no cut-outs, no V-score.
Files:
{files}
'''


def run(cwd, *args, check=True):
    return subprocess.run(['kicad-cli', *args], cwd=cwd, check=check, capture_output=True, text=True)


def mm(v): return round(p.ToMM(v), 4)


def main(board):
    B = design.BOARDS[board]()
    out = ROOT / B.name; name = B.name
    pcb = out / f'{name}.kicad_pcb'
    b = p.LoadBoard(str(pcb))
    p.ZONE_FILLER(b).Fill(b.Zones())
    build.save_board(pcb, b, B)
    # ------------------------------------------------------------ checks
    erc = run(out, 'sch', 'erc', '--severity-all', '--format', 'json', '-o', 'erc.json', f'{name}.kicad_sch', check=False)
    run(out, 'sch', 'erc', '--severity-all', '-o', 'erc.rpt', f'{name}.kicad_sch', check=False)
    drc = run(out, 'pcb', 'drc', '--schematic-parity', '--severity-all', '--format', 'json', '-o', 'drc.json', f'{name}.kicad_pcb', check=False)
    run(out, 'pcb', 'drc', '--schematic-parity', '--severity-all', '-o', 'drc.rpt', f'{name}.kicad_pcb', check=False)
    ercj = json.loads((out / 'erc.json').read_text()); drcj = json.loads((out / 'drc.json').read_text())
    erc_v = [v for s in ercj.get('sheets', []) for v in s.get('violations', [])]
    drc_v = drcj.get('violations', []); unc = drcj.get('unconnected_items', []); par = drcj.get('schematic_parity', [])
    summary = {'ERC_violations': len(erc_v), 'DRC_violations': len(drc_v), 'unconnected': len(unc), 'parity': len(par),
               'ERC_types': dict(collections.Counter(v['type'] for v in erc_v)),
               'DRC_types': dict(collections.Counter(v['type'] for v in drc_v))}
    print(json.dumps(summary))
    # ------------------------------------------------------------ fabrication outputs
    man = out / 'gerbers'
    if man.exists(): shutil.rmtree(man)
    man.mkdir()
    run(out, 'pcb', 'export', 'gerbers', '--layers', 'F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts',
        '--subtract-soldermask', '-o', 'gerbers/', f'{name}.kicad_pcb')
    run(out, 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th', '--drill-origin', 'absolute',
        '--generate-map', '--map-format', 'gerberx2', '-o', 'gerbers/', f'{name}.kicad_pcb')
    zpath = out / f'{name}-jlcpcb-gerbers.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(man.iterdir()): z.write(f, f.name)
    # PCB Train (UK) package: RS-274X without X2 attributes (their documented format), Excellon PTH +
    # NPTH, one ZIP per design with a README (they accept default CAD names; no renaming required).
    pt = out / 'pcbtrain'
    if pt.exists(): shutil.rmtree(pt)
    pt.mkdir()
    run(out, 'pcb', 'export', 'gerbers', '--layers', 'F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts',
        '--subtract-soldermask', '--no-x2', '-o', 'pcbtrain/', f'{name}.kicad_pcb')
    run(out, 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th', '--drill-origin', 'absolute',
        '-o', 'pcbtrain/', f'{name}.kicad_pcb')
    (pt / 'README.txt').write_text(PCBTRAIN_README.format(name=name, w=B.width, h=B.height,
                                   files='\n'.join('  ' + f.name for f in sorted(pt.iterdir()) if f.name != 'README.txt')))
    with zipfile.ZipFile(out / f'{name}-pcbtrain.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pt.iterdir()): z.write(f, f.name)
    # Second DRC against PCB Train's published capabilities (independent of the JLCPCB rule file).
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        shutil.copy(pcb, td / pcb.name); shutil.copy(out / f'{name}.kicad_pro', td / f'{name}.kicad_pro')
        shutil.copy(ROOT / 'pcbtrain-2layer.kicad_dru', td / f'{name}.kicad_dru')
        run(td, 'pcb', 'drc', '--severity-error', '--format', 'json', '-o', 'pt.json', pcb.name, check=False)
        ptj = json.loads((td / 'pt.json').read_text())
    summary['DRC_pcbtrain'] = len(ptj.get('violations', [])) + len(ptj.get('unconnected_items', []))
    # ------------------------------------------------------------ views
    views = out / 'views'; views.mkdir(exist_ok=True)
    run(out, 'sch', 'export', 'pdf', '-o', 'views/schematic.pdf', f'{name}.kicad_sch')
    run(out, 'sch', 'export', 'svg', '-o', 'views', f'{name}.kicad_sch')
    for vname, layers in [('top', 'F.Cu,F.Mask,F.Silkscreen,Edge.Cuts'), ('bottom', 'B.Cu,B.Mask,B.Silkscreen,Edge.Cuts'),
                          ('assembly', 'F.Silkscreen,F.Fab,F.Courtyard,Edge.Cuts')]:
        extra = ['--mirror'] if vname == 'bottom' else []
        run(out, 'pcb', 'export', 'svg', '--layers', layers, '--mode-single', '--page-size-mode', '2',
            '--exclude-drawing-sheet', *extra, '-o', f'views/{vname}.svg', f'{name}.kicad_pcb')
    for side in ('top', 'bottom'):
        r = run(out, 'pcb', 'render', '--side', side, '--quality', 'high', '--width', '1600', '--height', '1000',
                '--background', 'opaque', '-o', f'views/render-{side}.png', f'{name}.kicad_pcb', check=False)
        if r.returncode: print('render failed', side, r.stderr[-400:])
    run(out, 'pcb', 'export', 'step', '--board-only', '--force', '-o', 'views/board-only.step', f'{name}.kicad_pcb', check=False)
    # ------------------------------------------------------------ BOM
    rows = collections.OrderedDict()
    for a in B.parts:
        c = catalog.get(a)
        key = (c['mpn'], a.value if a.kind == 'R' else c['mpn'])
        r = rows.setdefault(key, dict(refs=[], c=c, a=a))
        r['refs'].append(a.ref)
    with (out / f'{name}-bom.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Board', 'References', 'Qty', 'Value', 'Description', 'Manufacturer', 'MPN', 'KiCad footprint',
                    'Supplier', 'Stock no', 'Pack', 'Datasheet', 'Checked'])
        for (mpn, _), r in rows.items():
            c, a = r['c'], r['a']
            w.writerow([name, ' '.join(r['refs']), len(r['refs']), a.value if a.kind in ('R', 'C100n', 'C1u') else '',
                        c['desc'], c['mfr'], mpn, c['fp'], c.get('supplier', 'RS'), c.get('rs') or c.get('farnell', ''),
                        c.get('pack', ''), c.get('ds', ''), c.get('check', '')])
        for e in catalog.EXTRAS.get(name, []):
            w.writerow([name, '(off-board)', e['qty'], '', e['desc'], e['mfr'], e['mpn'], '', e.get('supplier', 'RS'),
                        e.get('rs', e.get('url', '')), e.get('pack', ''), e.get('ds', ''), e.get('check', '')])
    # ------------------------------------------------------------ geometry / envelope
    ox, oy = B.origin
    comps = []
    for fp in b.GetFootprints():
        a = next(x for x in B.parts if x.ref == fp.GetReference()); c = catalog.get(a)
        fp.BuildCourtyardCaches(); bb = fp.GetCourtyard(p.F_CrtYd).BBox()
        comps.append(dict(ref=a.ref, kind=a.kind, x0=mm(bb.GetLeft()) - ox, y0=mm(bb.GetTop()) - oy,
                          x1=mm(bb.GetRight()) - ox, y1=mm(bb.GetBottom()) - oy,
                          body_h=c.get('h'), mated_h=c.get('mate_h', c.get('h'))))
    pads = []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            pads.append(dict(ref=fp.GetReference(), pad=pad.GetNumber(), net=pad.GetNetname().lstrip('/'),
                             x=mm(pad.GetPosition().x) - ox, y=mm(pad.GetPosition().y) - oy,
                             sx=mm(pad.GetSize(p.F_Cu).x), sy=mm(pad.GetSize(p.F_Cu).y),
                             drill=mm(pad.GetDrillSize().x), fp=str(fp.GetFPID().GetLibItemName())))
    widths = collections.defaultdict(set); vias = 0; segs = 0
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA': vias += 1
        else:
            segs += 1; widths[t.GetNetname().lstrip('/')].add(round(p.ToMM(t.GetWidth()), 3))
    texts = []
    for d in b.GetDrawings():
        if isinstance(d, p.PCB_TEXT):
            texts.append(dict(text=d.GetText(), h=mm(d.GetTextHeight()), t=mm(d.GetTextThickness()), layer=d.GetLayerName()))
    for fp in b.GetFootprints():
        for t in (fp.Reference(),):
            if t.IsVisible(): texts.append(dict(text=t.GetText(), h=mm(t.GetTextHeight()), t=mm(t.GetTextThickness()), layer=t.GetLayerName()))
        for item in fp.GraphicalItems():
            if isinstance(item, p.PCB_TEXT) and item.IsVisible() and item.GetLayerName().endswith('Silkscreen'):
                texts.append(dict(text=item.GetText(), h=mm(item.GetTextHeight()), t=mm(item.GetTextThickness()), layer=item.GetLayerName()))
    over = []
    for c in comps:
        if c['x0'] < 0 or c['x1'] > B.width: over.append(c['ref'])
    tallest = max(comps, key=lambda c: c['body_h'] or 0); tallest_m = max(comps, key=lambda c: c['mated_h'] or 0)
    envelope = {'status': 'computed from footprints + catalogue heights (datasheet or estimate); not a fit test',
                'board_mm': [B.width, B.height, 1.6], 'edge_band_mm': B.band,
                'parts_overhanging_short_edges': over,
                'min_x': min(c['x0'] for c in comps), 'max_x': max(c['x1'] for c in comps),
                'tallest_body': [tallest['ref'], tallest['body_h']], 'tallest_mated_with_cable_bend': [tallest_m['ref'], tallest_m['mated_h']],
                'underside_protrusion_mm': 2.5, 'components': comps}
    (out / 'envelope.json').write_text(json.dumps(envelope, indent=1) + '\n')
    report = dict(board=name, tool='KiCad 9.0.2 (kicad-cli)', rules='electronics/dfm/jlcpcb-2layer-recommended.kicad_dru + project net classes',
                  size_mm=[B.width, B.height], parts=len(B.parts), track_segments=segs, vias=vias,
                  min_width_by_net={k: min(v) for k, v in sorted(widths.items())}, **summary,
                  silk_text_min=[min(t['h'] for t in texts), min(t['t'] for t in texts)],
                  physical_testing='none')
    (out / 'validation.json').write_text(json.dumps(report, indent=1) + '\n')
    (out / 'pads.json').write_text(json.dumps(pads, indent=0) + '\n')
    (out / 'silk-texts.json').write_text(json.dumps(texts, indent=0) + '\n')
    ok = not (erc_v or drc_v or unc or par or summary.get('DRC_pcbtrain'))
    print(name, 'CHECKS PASS' if ok else 'CHECKS FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main(sys.argv[1])
