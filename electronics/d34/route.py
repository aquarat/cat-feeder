#!/usr/bin/env python3
"""Autoroute one D34 board with Freerouting 2.1.0, import the session, pour
ground on both layers and save <board>.kicad_pcb.

    FREEROUTING_JAR=/path/freerouting-2.1.0.jar ./run.sh route.py ctrl|pwr [passes]

The jar is mounted read-only at /opt/freerouting.jar by run.sh (official
release, SHA256 2c07d58f75dac03782664081e7a58b41c25400d871a9fcf166a2ea6fe60d5def).
KiCad DRC in export.py, not the router's own report, establishes completion.
"""
import hashlib, json, math, pathlib, subprocess, sys
import pcbnew as p
import build, design, finish

JAR = pathlib.Path('/opt/freerouting.jar')
SHA = '2c07d58f75dac03782664081e7a58b41c25400d871a9fcf166a2ea6fe60d5def'


def xy(x, y): return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def drc(path):
    rep = path.with_suffix('.chk.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--severity-all', '--format', 'json', '-o', str(rep), str(path)],
                   capture_output=True, text=True)
    d = json.loads(rep.read_text()); rep.unlink(); return d


def anchors(b, item, other_pos):
    """Connection point for a DRC 'unconnected' item: pad centre (any layer),
    via centre, or the track end nearest the other item."""
    u = item['uuid']
    for f in b.GetFootprints():
        for pd in f.Pads():
            if pd.m_Uuid.AsString() == u:
                v = pd.GetPosition(); return (p.ToMM(v.x), p.ToMM(v.y), None), pd.GetNetname()
    for t in b.GetTracks():
        if t.m_Uuid.AsString() == u:
            if t.GetClass() == 'PCB_VIA':
                v = t.GetPosition(); return (p.ToMM(v.x), p.ToMM(v.y), None), t.GetNetname()
            ox, oy = other_pos
            ends = [t.GetStart(), t.GetEnd()]
            v = min(ends, key=lambda e: math.hypot(p.ToMM(e.x) - ox, p.ToMM(e.y) - oy))
            return (p.ToMM(v.x), p.ToMM(v.y), 0 if t.GetLayer() == p.F_Cu else 1), t.GetNetname()
    raise KeyError(u)


def dangling_uuids(path):
    """KiCad's own DRC identifies router stubs (dangling tracks/vias)."""
    rep = path.with_suffix('.dangling.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--severity-all', '--format', 'json', '-o', str(rep), str(path)],
                   capture_output=True, text=True)
    d = json.loads(rep.read_text()); rep.unlink()
    return {i['uuid'] for v in d['violations'] if v['type'] in ('track_dangling', 'via_dangling') for i in v['items']}


def route_once(board, passes):
    B = design.BOARDS[board]()
    out = build.ROOT / B.name
    assert hashlib.sha256(JAR.read_bytes()).hexdigest() == SHA, 'unexpected Freerouting jar'
    dsn, ses = out / f'{B.name}.dsn', out / f'{B.name}.ses'
    log = subprocess.run(['java', '-Djava.awt.headless=true', '-jar', str(JAR), '-de', str(dsn), '-do', str(ses),
                          '-mp', passes, '-mt', '1', '-da', '-dct', '0'], capture_output=True, text=True, timeout=3000)
    (out / 'routing.log').write_text(log.stdout[-20000:] + log.stderr[-20000:])
    assert ses.exists(), 'router produced no session'
    b = p.LoadBoard(str(out / f'{B.name}-unrouted.kicad_pcb'))
    assert p.ImportSpecctraSES(b, str(ses))
    # pcbnew 9's Remove() corrupts SWIG track lists here (as rev A found); strip
    # dangling items from the saved file by UUID and reload until stable.
    import re
    tmp = out / f'{B.name}.kicad_pcb'
    build.save_board(tmp, b, B)
    removed = 0
    for _ in range(20):
        dead = dangling_uuids(tmp)
        if not dead: break
        removed += len(dead)
        txt = tmp.read_text()
        txt = re.sub(r'\n\t\((segment|via)\s.*?\n\t\)', lambda m: '' if re.search(r'\(uuid "([^"]+)"\)', m.group(0)).group(1) in dead else m.group(0), txt, flags=re.S)
        tmp.write_text(txt)
    print('removed dangling items:', removed)
    # Finish SES import gaps with the grid router, then re-clean, until KiCad reports none.
    ox, oy = B.origin
    widths = {('/' + n): s['width'] for s in B.netclasses.values() for n in s['nets']}
    for attempt in range(6):
        d = drc(tmp)
        # GND is completed by the copper pours added below; leave GND gaps to them.
        unc = [v for v in d['unconnected_items'] if not any('[/GND]' in i['description'] for i in v['items'])]
        if not unc: break
        b = p.LoadBoard(str(tmp)); done = 0
        for v in unc:
            i1, i2 = v['items']
            a, net = anchors(b, i1, (i2['pos']['x'], i2['pos']['y']))
            c, _ = anchors(b, i2, (a[0], a[1]))
            w = min(widths.get(net, B.default_track), 0.6)
            ok = finish.route(b, net, a, c, w, (ox, oy, ox + B.width, oy + B.height))
            print('finish', net, 'ok' if ok else 'FAILED'); done += ok
        build.save_board(tmp, b, B)
        for _ in range(10):
            dead = dangling_uuids(tmp)
            if not dead: break
            txt = tmp.read_text()
            txt = re.sub(r'\n\t\((segment|via)\s.*?\n\t\)', lambda m: '' if re.search(r'\(uuid "([^"]+)"\)', m.group(0)).group(1) in dead else m.group(0), txt, flags=re.S)
            tmp.write_text(txt)
        if not done: break
    left = len([v for v in drc(tmp)['unconnected_items'] if not any('[/GND]' in i['description'] for i in v['items'])])
    if left:
        return left
    b = p.LoadBoard(str(tmp))
    gnd = b.FindNet('/GND')
    ox, oy = B.origin
    for layer in (p.F_Cu, p.B_Cu):
        z = p.ZONE(b); z.SetLayer(layer); z.SetNet(gnd); z.SetLocalClearance(p.FromMM(.35))
        z.SetPadConnection(p.ZONE_CONNECTION_FULL); z.SetMinThickness(p.FromMM(.25))
        z.SetThermalReliefGap(p.FromMM(.4)); z.SetThermalReliefSpokeWidth(p.FromMM(.6))
        z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
        z.Outline().NewOutline()
        for x, y in [(0, 0), (B.width, 0), (B.width, B.height), (0, B.height)]:
            z.Outline().Append(p.FromMM(ox + x), p.FromMM(oy + y))
        b.Add(z)
    p.ZONE_FILLER(b).Fill(b.Zones())
    build.save_board(out / f'{B.name}.kicad_pcb', b, B)
    left = len(drc(out / f'{B.name}.kicad_pcb')['unconnected_items'])
    if left:
        print(f'{left} unconnected after the GND pours')
        return left
    tracks = [t for t in b.GetTracks()]
    print(f'{B.name}: {sum(t.GetClass() == "PCB_TRACK" for t in tracks)} segments, {sum(t.GetClass() == "PCB_VIA" for t in tracks)} vias')


def main(board, passes='40'):
    # Freerouting is not deterministic; retry from scratch if KiCad still sees opens.
    for attempt in range(4):
        left = route_once(board, passes)
        if not left: return
        print(f'attempt {attempt + 1}: {left} unconnected after finishing; rerouting')
    raise SystemExit('routing incomplete after 4 attempts')


if __name__ == '__main__':
    main(*sys.argv[1:])
