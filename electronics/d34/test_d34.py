#!/usr/bin/env python3
"""Regression tests for the D34 boards (run inside cat-feeder-kicad:local after export).

    ./run.sh test_d34.py

Checks real footprint geometry (not just design intent), routed-board net
connectivity of the power paths, connector keying/uniqueness, edge bands,
silkscreen sizes and the cross-board link. Exits non-zero on any failure.
"""
import itertools, json, math, pathlib, sys
import pcbnew as p
import catalog, design
W_ = design.W

ROOT = pathlib.Path(__file__).resolve().parent
LIB = ROOT / 'd34.pretty'
FAILS = []; PASSES = []


def check(cond, msg):
    (PASSES if cond else FAILS).append(msg)


def near(a, b, tol=0.01): return abs(a - b) <= tol


def fp(lib, name):
    f = p.FootprintLoad(str(lib), name); assert f, name; return f


def pads(f):
    return {(pd.GetNumber(), i): (p.ToMM(pd.GetPosition().x), p.ToMM(pd.GetPosition().y)) for i, pd in enumerate(f.Pads()) if pd.GetNumber()}


def padpos(f):
    out = {}
    for pd in f.Pads():
        if pd.GetNumber(): out.setdefault(pd.GetNumber(), (p.ToMM(pd.GetPosition().x), p.ToMM(pd.GetPosition().y)))
    return out


# ------------------------------------------------------------------ footprints
def test_footprints():
    dk = padpos(fp(LIB, 'ESP32-DevKitC-32E_Socket'))
    n = catalog.DEVKIT_PINS
    check(len(dk) == 2 * n, 'DevKitC socket has 38 pads')
    check(all(near(dk[str(k + 1)][0], 0) and near(dk[str(n + k + 1)][0], 25.40) for k in range(n)),
          'DevKitC rows 25.40 mm apart (Espressif drawing)')
    check(all(near(dk[str(k + 2)][1] - dk[str(k + 1)][1], 2.54) for k in range(n - 1)), 'DevKitC pitch 2.54 mm')
    check(all(near(dk[str(k + 1)][1], dk[str(n + k + 1)][1]) for k in range(n)), 'DevKitC rows aligned (pin k opposite pin k)')
    ss = padpos(fp(LIB, 'StepStick_Socket_2x8_W12.70mm'))
    check(all(near(ss[str(k + 9)][0] - ss[str(k + 1)][0], 12.70) for k in range(8)), 'StepStick rows 12.70 mm apart')
    pol = padpos(fp(pathlib.Path('/usr/share/kicad/footprints/Module.pretty'), 'Pololu_Breakout-16_15.2x20.3mm'))
    a = sorted((round(x, 3), round(y, 3)) for x, y in ss.values()); b_ = sorted((round(x, 3), round(y, 3)) for x, y in pol.values())
    check(a == b_, 'StepStick socket pad positions identical to KiCad Pololu_Breakout-16_15.2x20.3mm')
    # Same pin-1 corner and VMOT position as the Pololu carrier (VMOT top right).
    check(near(ss['9'][0], 12.70) and near(ss['9'][1], 0.0), 'StepStick right-row pin 1 (VMOT) at top right')
    rel = padpos(fp(LIB, 'Relay_DPDT_Omron_G2RL-2'))
    check(near(rel['A2'][0] - rel['A1'][0], 7.5) and near(rel['11'][1] - rel['A1'][1], 20.0) and
          near(rel['14'][1] - rel['11'][1], 5.0) and near(rel['11'][1] - rel['12'][1], 5.0), 'G2RL-2 grid 7.5 / 20 / 5 mm (Omron)')
    for name, pitch in [('JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical', 2.50), ('JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical', 2.50),
                        ('FanPinHeader_1x04_P2.54mm_Vertical', 2.54), ('PhoenixContact_MSTBVA_2,5_2-G-5,08_1x02_P5.08mm_Vertical', 5.08),
                        ('Converter_DCDC_TRACO_TSR-1_THT', 2.54)]:
        q = padpos(fp(LIB, name)); check(near(q['2'][0] - q['1'][0], pitch), f'{name} pitch {pitch} mm')
    q = padpos(fp(LIB, 'Converter_DCDC_TRACO_TSR2-24xxN_TSR2-24xxxN_THT'))
    check(near(q['2'][1] - q['1'][1], 2.54) and near(q['3'][1] - q['2'][1], 2.54), 'TSR 2N SIP-3 pitch 2.54 mm')
    for name in ['Molex_Mini-Fit_Jr_5566-04A_2x02_P4.20mm_Vertical', 'Molex_Mini-Fit_Jr_5566-06A_2x03_P4.20mm_Vertical']:
        q = padpos(fp(LIB, name)); check(near(q['2'][0] - q['1'][0], 4.20) and near(q['4'][1] - q['1'][1], 5.50), f'{name} 4.20 x 5.50 mm')
    for name, pitch in [('JST_VH_B2P-VH_1x02_P3.96mm_Vertical', 3.96), ('JST_VH_B3P-VH_1x03_P3.96mm_Vertical', 3.96),
                        ('JST_VH_B4P-VH_1x04_P3.96mm_Vertical', 3.96), ('JST_XH_B11B-XH-A_1x11_P2.50mm_Vertical', 2.50),
                        ('JST_XH_B12B-XH-A_1x12_P2.50mm_Vertical', 2.50)]:
        q = padpos(fp(LIB, name)); check(near(q['2'][0] - q['1'][0], pitch), f'{name} pitch {pitch} mm')
    for name in ['DIP-16_W7.62mm', 'DIP-20_W7.62mm']:
        q = padpos(fp(LIB, name)); n2 = len(q)
        check(near(q[str(n2)][0] - q['1'][0], 7.62), f'{name} row spacing 7.62 mm')
    f = fp(LIB, 'FanPinHeader_1x04_P2.54mm_Vertical')
    check(any(not pd.GetNumber() for pd in f.Pads()), 'PC fan header has its polarising peg hole')
    check(all(near(p.ToMM(pd.GetDrillSize().x), 1.25) for pd in f.Pads() if not pd.GetNumber()),
          'PC fan header peg hole 1.25 mm (Molex SD-47053-001)')


# ------------------------------------------------------------------ boards
def load(B):
    b = p.LoadBoard(str(ROOT / B.name / f'{B.name}.kicad_pcb'))
    net = {}
    for f in b.GetFootprints():
        for pd in f.Pads():
            if pd.GetNumber(): net[(f.GetReference(), pd.GetNumber())] = pd.GetNetname().lstrip('/')
    return b, net


def same(net, *pins):
    ns = {net[x] for x in pins}; return len(ns) == 1 and '' not in ns


def test_pwr(net):
    paths = [
        ('24 V input to P-FET drain', [('J1', '1'), ('Q1', '2')]),
        ('P-FET source feeds TVS cathode, bulk, DPS fuse and aux PTC', [('Q1', '3'), ('D1', '1'), ('C1', '1'), ('F1', '1'), ('F2', '1')]),
        ('Zener clamps gate to source', [('DZ1', '1'), ('Q1', '3')]),
        ('7.5 A fuse feeds DPS IN+', [('F1', '2'), ('J2', '1')]),
        ('DPS IN- and brick return are ground', [('J2', '2'), ('J1', '2'), ('D1', '2')]),
        ('aux PTC feeds both bucks and their input capacitor', [('F2', '2'), ('U1', '1'), ('U2', '1'), ('C3', '1')]),
        ('12 V buck to the tec-card lead (pins 1 and 3), StepStick VMOT and its bulk', [('U1', '3'), ('J3', '1'), ('J3', '3'), ('U4', '9'), ('C8', '1')]),
        ('5 V buck to the ctrl link', [('U2', '3'), ('J9', '1'), ('J9', '2')]),
        ('StepStick pin 4 is the TMC single-wire UART', [('U4', '4'), ('J9', '9')]),
    ]
    for msg, pins in paths:
        check(same(net, *pins), 'pwr: ' + msg)
    check(net[('U4', '15')] == '+3V3', 'pwr: StepStick logic supply is 3.3 V (TMC inputs <= VIO + 0.5 V)')
    check(net[('U4', '6')] == net[('U4', '5')] and sum(1 for k, v in net.items() if v == net[('U4', '6')]) == 2,
          'pwr: StepStick pins 5-6 linked to each other only (A4988 RESET=SLEEP; BTT V1.3 pin 5 NC, CLK 20 k to GND)')
    check(net[('U4', '9')] == '+12V' and '+24V' not in net[('U4', '9')], 'pwr: StepStick VMOT on the regulated 12 V rail (TVS clamp cannot reach the TMC2209)')
    check(not any(v in ('+24V', 'VAUX', 'VIN_RAW', '+24V_DPS') for (r, _), v in net.items() if r == 'U4'),
          'pwr: no 24 V net on any StepStick pin')
    check(net[('D1', '1')] == net[('Q1', '3')], 'pwr: TVS sits after reverse-polarity FET (no fuse-blowing on reversal)')


def test_tec(net):
    paths = [
        ('DPS OUT+ pins 1-3 to K1 pole 2 COM', [('J2', '1'), ('J2', '2'), ('J2', '3'), ('K1', '21')]),
        ('K1 poles in series (double break)', [('K1', '24'), ('K1', '11')]),
        ('K1 output to K2 NC1/NO2', [('K1', '14'), ('K2', '12'), ('K2', '24')]),
        ('DPS OUT- pins 4-6 to K2 NO1/NC2', [('J2', '4'), ('J2', '5'), ('J2', '6'), ('K2', '14'), ('K2', '22')]),
        ('K2 COM1 to TEC A pins', [('K2', '11'), ('J3', '1'), ('J3', '3')]),
        ('K2 COM2 to TEC B pins', [('K2', '21'), ('J3', '2'), ('J3', '4')]),
        ('+12 V in feeds the fan PTCs, the K2 hold-up diode and the UV switch Q6', [('J1', '1'), ('J1', '3'), ('Q6', '3'), ('F1', '1'), ('F2', '1'), ('F3', '1'), ('D5', '2'), ('R11', '1')]),
        ('thermostat loop fed from the UV switch Q6 collector', [('Q6', '1'), ('J4', '1'), ('R14', '1')]),
        ('TL431 reference divider and hysteresis', [('U1', '1'), ('R11', '2'), ('R13', '1'), ('R14', '2')]),
        ('TL431 cathode drives Q6 base through R15', [('U1', '3'), ('R15', '2')]),
        ('each fan +12 V through its own PTC', [('F1', '2'), ('J5', '2')]),
        ('FAN2 feed PTC', [('F2', '2'), ('J6', '2')]),
        ('FAN3 feed PTC', [('F3', '2'), ('J7', '2')]),
        ('K2 coil fed through D5 with C1 hold-up', [('K2', 'A1'), ('D5', '1'), ('C1', '1')]),
        ('K1 coil fed only through the thermostat loop', [('J4', '2'), ('K1', 'A1')]),
        ('K1 coil low side on Q2 collector', [('K1', 'A2'), ('Q2', '3')]),
        ('K2 coil low side on Q3 collector', [('K2', 'A2'), ('Q3', '3')]),
        ('K1 drive from the ctrl link', [('R4', '1'), ('J9', '3')]),
        ('K2 drive from the ctrl link', [('R6', '1'), ('J9', '4')]),
        ('FAN2 low side on Q4 drain', [('Q4', '2'), ('J6', '1'), ('D7', '2')]),
        ('FAN3 low side on Q5 drain', [('Q5', '2'), ('J7', '1'), ('D8', '2')]),
        ('FAN2 gate from the link', [('Q4', '1'), ('J9', '8')]),
        ('FAN3 gate from the link', [('Q5', '1'), ('J9', '9')]),
    ]
    for msg, pins in paths:
        check(same(net, *pins), 'tec: ' + msg)
    check(net[('U1', '2')] == 'GND' and net[('R13', '2')] == 'GND' and net[('Q6', '2')] == net[('R15', '1')],
          'tec: 12 V undervoltage cut-off wiring (TL431 anode GND, Q6 base via R15)')
    check(net[('J4', '1')] != '+12V', 'tec: the thermostat loop is not fed directly from +12 V (UV switch in series)')
    check(net[('C1', '1')] == net[('K2', 'A1')] and net[('C1', '2')] == net[('K2', 'A2')], 'tec: K2 hold-up C1 directly across the coil')
    check(net[('Q2', '1')] == 'GND' and net[('Q3', '1')] == 'GND' and net[('Q4', '3')] == 'GND' and net[('Q5', '3')] == 'GND', 'tec: low-side emitters/sources on GND')
    check(net[('R5', '2')] == 'GND' and net[('R5', '1')] == net[('Q2', '2')] and net[('R7', '2')] == 'GND' and net[('R7', '1')] == net[('Q3', '2')],
          'tec: K1/K2 driver bases pulled down (relays off with the ctrl lead unplugged)')
    check(net[('R9', '1')] == net[('Q4', '1')] and net[('R9', '2')] == 'GND' and net[('R10', '1')] == net[('Q5', '1')] and net[('R10', '2')] == 'GND',
          'tec: fan FET gates pulled down')
    hc = {net[x] for x in [('J2', '1'), ('J2', '4'), ('K1', '24'), ('K1', '14'), ('J3', '1'), ('J3', '2')]}
    check('GND' not in hc and len(hc) == 6, 'tec: TEC/DPS-output nets are isolated from GND (DPS OUT- has a low-side shunt)')
    check(net[('K1', 'A1')] != '+12V', 'tec: K1 coil is not fed directly from +12 V')
    check(net[('D1', '2')] == net[('K1', 'A2')] and net[('D1', '1')] == net[('DZ2', '1')] and net[('DZ2', '2')] == net[('K1', 'A1')],
          'tec: K1 flyback = diode + 15 V zener across the coil (fast release)')
    check(not any(r == 'U1' and pn in ('9', '16') for (r, pn) in net), 'tec: no ULN2003 (fan/coil drivers are discrete; U1 is the TL431)')


def test_ctrl(netc):
    def rbetween(a, b):
        return any({netc.get((r, '1')), netc.get((r, '2'))} == {a, b} for r in {k[0] for k in netc if k[0].startswith('R')})
    check(rbetween('FAN1_PWM', 'GND'), 'ctrl: GPIO12 strap pulled low')
    check(rbetween('TEC_EN', 'GND') and rbetween('DEFROST_REQ', 'GND') and rbetween('WDT_KICK', 'GND'), 'ctrl: TEC enable/kick/defrost default low')
    check(netc[('U2', '3')] == 'TEC_EN' and netc[('U2', '2')] == 'WDT_KICK' and netc[('U2', '13')] == 'K1_ON', 'ctrl: watchdog wiring')
    check(netc[('U3', '11')] == 'LATCH_EN' and netc[('U3', '2')] == 'DEFROST_REQ' and netc[('U3', '19')] == 'K2_ON' and netc[('U3', '1')] == 'GND',
          'ctrl: defrost latch wiring (LE, D1, Q1, OE low)')
    check(netc[('U2', '4')] == 'LATCH_RAW' and netc[('D2', '1')] == 'LATCH_RAW' and netc[('D2', '2')] == 'LATCH_EN', 'ctrl: LE clamped low by D2 while 1Q-bar is low')
    check(netc[('U2', '10')] == 'LATCH_RAW' and netc[('U2', '11')] == 'LATCH_RAW' and netc[('U2', '9')] == 'GND',
          'ctrl: 74HC123 half 2 triggered by 1Q-bar rising (B and CLR)')
    check({netc[('R5', '1')], netc[('R5', '2')]} == {'LATCH_DLY', 'LATCH_EN'} and netc[('U2', '12')] == 'LATCH_DLY',
          'ctrl: LE = delayed 2Q-bar through R5 (no RC ramp on LE)')
    check(not any(netc.get((c, p_)) == 'LATCH_EN' for c in ('C4', 'C5') for p_ in ('1', '2')), 'ctrl: no capacitor on LE')
    check(netc[('D9', '1')] == 'THERMO_OK_IN' and netc[('D9', '2')] == 'GND' and {netc[('R12', '1')], netc[('R12', '2')]} == {'THERMO_OK', 'THERMO_OK_IN'},
          'ctrl: IO36 Schottky clamp D9 behind R12')
    check(netc[('U1', '19')] == '+5V_DK' and netc[('D1', '1')] == '+5V_DK' and netc[('D1', '2')] == '+5V', 'ctrl: DevKit 5V via Schottky')
    check(netc[('U1', '1')] == '+3V3', 'ctrl: DevKit 3V3 pin is the 3.3 V rail')
    high = {'+12V', '+24V', 'VMOT', 'VIN_RAW', 'TEC_A', 'TEC_B'}
    check(not (set(netc.values()) & high), 'ctrl: no rail above 5 V on the controller card')


def test_connectors(boards):
    allc = []
    for B in boards:
        for ref, c in B.connectors.items():
            k = catalog.K[c['kind']]
            allc.append((B.name, ref, c, k))
    keyed_families = {'JST XH', 'JST VH', 'PC fan 4-pin (KK 254)', 'Molex Mini-Fit Jr', 'Phoenix MSTB 5.08'}
    for bn, ref, c, k in allc:
        if k.get('pluggable'):
            check(k['family'] in keyed_families, f'{bn} {ref}: pluggable connector family {k["family"]} is polarised/keyed')
    # Same family + pin count => identical voltage roles (a harness can only mate where it is electrically equivalent).
    groups = {}
    for bn, ref, c, k in allc:
        if k.get('pluggable'):
            groups.setdefault((k['family'], len(c['roles'])), []).append((bn, ref, tuple(c['roles'])))
    norm = lambda r: tuple({'ANALOG': 'LOGIC', 'FANGND': 'GND'}.get(x, x) for x in r)   # 3.3 V signals; fan ground (switched or not)
    compat = lambda a, b: all(x == y or 'NC' in (x, y) for x, y in zip(norm(a), norm(b)))
    for key, items in groups.items():
        roles = {r for _, _, r in items}
        ok = all(compat(a, b) for a in roles for b in roles)
        check(ok, f'connector type {key}: {len(items)} instance(s) carry compatible roles (NC = unused) {sorted(roles)}')
    hv = {'12V', '24V', 'TEC', 'MOTOR', 'FANGND'}
    for key, items in groups.items():
        r = items[0][2]
        if set(r) & hv:
            check(all(set(x[2]) & hv for x in items), f'{key}: high-voltage connector type never used for 3.3 V logic')
    # The fixed link: both ends identical, pin for pin.
    bc, bp, bt = boards
    for (a, ra), (b, rb), name in [((bc, 'J1'), (bp, 'J9'), 'ctrl J1 / pwr J9 (XH-11)'), ((bc, 'J2'), (bt, 'J9'), 'ctrl J2 / tec J9 (XH-12)'),
                                   ((bp, 'J3'), (bt, 'J1'), 'pwr J3 / tec J1 (VH-3 12 V)')]:
        check(a.connectors[ra]['nets'] == b.connectors[rb]['nets'] and a.connectors[ra]['kind'] == b.connectors[rb]['kind'],
              f'link {name}: same type, identical nets pin-for-pin')
    for c in (bc.connectors['J1'], bc.connectors['J2']):
        check(set(c['roles']) <= {'GND', '3V3', '5V', 'LOGIC'} and c['roles'].count('GND') >= 2,
              f'link {c["kind"]}: only 5 V, 3.3 V, GND (>= 2) and logic to the controller')


def test_geometry(B, b):
    ox, oy = B.origin
    bad = []
    for f in b.GetFootprints():
        for pd in f.Pads():
            y = p.ToMM(pd.GetPosition().y) - oy; r = p.ToMM(max(pd.GetSize(p.F_Cu).x, pd.GetSize(p.F_Cu).y)) / 2
            if y - r < B.band or y + r > B.height - B.band: bad.append(f'{f.GetReference()}.{pd.GetNumber()}')
        f.BuildCourtyardCaches(); bb = f.GetCourtyard(p.F_CrtYd).BBox()
        if p.ToMM(bb.GetTop()) - oy < B.band - 1e-3 or p.ToMM(bb.GetBottom()) - oy > B.height - B.band + 1e-3:
            bad.append(f.GetReference() + ' courtyard')
    check(not bad, f'{B.name}: {B.band} mm long-edge bands free of pads and courtyards {bad}')
    if B.name == 'd34-ctrl':
        env = json.loads((ROOT / B.name / 'envelope.json').read_text())
        u1 = next(c for c in env['components'] if c['ref'] == 'U1')
        body = (0.7, 15.4, 55.0, 43.2)   # DevKitC outline on this card (antenna end at x = 0.7)
        under = [c for c in env['components'] if c['ref'] != 'U1' and c['x0'] < body[2] and c['x1'] > body[0]
                 and c['y0'] < body[3] and c['y1'] > body[1]]
        tall = [(c['ref'], c['body_h']) for c in under if (c['body_h'] or 99) > 8.0]
        check(not tall, f'ctrl: {len(under)} parts under the DevKitC are all <= 8 mm tall (module underside ~11 mm up) {tall}')
    # CAD-checked bay (2026-10-26): card <= 81 x 47, component side <= 36 mm incl. mated plug + cable bend,
    # solder side <= 3 mm; everything (incl. the DevKit antenna) inside the 85 mm tangential envelope.
    env = json.loads((ROOT / B.name / 'envelope.json').read_text())
    w, h = env['board_mm'][:2]
    check(w <= 81.0 + 1e-6 and h <= 47.0 + 1e-6, f'{B.name}: card {w} x {h} mm fits 81 x 47')
    depth = max(max(c['body_h'] or 0, c['mated_h'] or 0) for c in env['components'])
    check(depth <= 36.0, f'{B.name}: component-side depth {depth} mm <= 36 mm (bodies and mated plugs + bend)')
    check(env['underside_protrusion_mm'] <= 3.0, f'{B.name}: solder-side protrusion <= 3 mm')
    x0 = min(env['min_x'], 0.7 if B.name == 'd34-ctrl' else 0); x1 = env['max_x']
    check(x0 >= -2.0 and x1 <= W_ + 2.0, f'{B.name}: all courtyards (and DevKit antenna) within the 85 mm envelope ({x0:.2f}..{x1:.2f})')
    texts = json.loads((ROOT / B.name / 'silk-texts.json').read_text())
    small = [t['text'] for t in texts if t['h'] < 1.0 - 1e-6 or t['t'] < 0.15 - 1e-6]
    check(not small, f'{B.name}: silkscreen text >= 1.0 mm high, >= 0.15 mm stroke {small}')
    v = json.loads((ROOT / B.name / 'validation.json').read_text())
    check(v['ERC_violations'] == 0 and v['DRC_violations'] == 0 and v['unconnected'] == 0 and v['parity'] == 0,
          f'{B.name}: ERC/DRC/parity clean (all severities)')
    if '+12V' in v['min_width_by_net'] and B.name in ('d34-pwr', 'd34-tec'):
        check(v['min_width_by_net']['+12V'] >= 1.5, f"{B.name}: +12 V min track width {v['min_width_by_net']['+12V']} mm >= 1.5 mm (2.0 mm class; TSR 2 short-circuit current)")
    for netn, w in v['min_width_by_net'].items():
        cls = next((k for k, s in B.netclasses.items() if netn in s['nets']), None)
        if cls == 'TEC':
            check(w >= 1.5, f'{B.name}: high-current net {netn} min track width {w} mm >= 1.5 mm (paralleled on both layers where < 2.5)')


def main():
    test_footprints()
    boards = [design.ctrl(), design.pwr(), design.tec()]
    loaded = [load(B) for B in boards]
    test_ctrl(loaded[0][1]); test_pwr(loaded[1][1]); test_tec(loaded[2][1])
    test_connectors(boards)
    for B, (b, _) in zip(boards, loaded): test_geometry(B, b)
    for m in PASSES: print('PASS', m)
    for m in FAILS: print('FAIL', m)
    print(f'{len(PASSES)} passed, {len(FAILS)} failed')
    (ROOT / 'test-results.json').write_text(json.dumps({'passed': PASSES, 'failed': FAILS}, indent=1) + '\n')
    sys.exit(1 if FAILS else 0)


if __name__ == '__main__':
    main()
