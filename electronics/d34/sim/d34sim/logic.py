"""Behavioural event model of the TEC safety chain (74HC123 watchdog, 74HC573 defrost latch, ULN2003, G2RL relays).

Topology and component values are read from the exported netlists and verified; if the design changes the
safety chain's structure, `extract()` reports what no longer matches instead of silently simulating the old
circuit. Time is stepped at `dt` for N independent instances in parallel (numpy), each with its own
firmware pin pattern, supply events and sampled component/relay parameters.
"""
import numpy as np

from . import models as M
from .flows import Roles

VCC = 3.3
K_TOSHIBA = ((0.90, 1.10), 'Toshiba TC74HC123AP: twOUT = 1.0 Cx Rx, K ~1.00 flat 2-6 V with 1 uF; guaranteed 0.9-1.1 at 4.5-6 V (no 3.3 V row): 0.90-1.10 used')


def _rval(card, ref):
    return M.parse_value(card.comps[ref]['value'])


def _passives_between(card, table, kind, a, b):
    out = []
    for ref, comp in card.comps.items():
        row = M.match(table, comp)
        if row is None or row['model'] != kind:
            continue
        nets = set(card.pins(ref).values())
        if nets == {a, b}:
            out.append(ref)
    return out


def extract(env):
    """Return (params, problems). params holds the safety-chain values; problems lists topology mismatches."""
    probs = []
    ro = Roles(env)
    ctrl, tec = env.cards['ctrl'], env.cards['tec']
    T = env.table
    P = {}
    hc123 = ro.model_refs('ctrl', 'logic_hc123')
    hc573 = ro.model_refs('ctrl', 'logic_hc573')
    dk = ro.model_refs('ctrl', 'devkit')
    if len(hc123) != 1 or len(hc573) != 1 or len(dk) != 1:
        return None, [f'expected one 74HC123, one 74HC573 and one DevKit on ctrl (found {hc123}, {hc573}, {dk})']
    u2, u3, dk = hc123[0], hc573[0], dk[0]
    P['refs'] = dict(hc123=u2, hc573=u3, devkit=dk)
    mpn = ctrl.comps[u2]['mpn'].upper()
    # 74HC123 timing constant K (tw = K R C) by vendor at VCC 3.3 V; see datasheets/datasheet_values.json
    if mpn.startswith('TC74HC123'):
        P['K_range'], P['K_source'] = K_TOSHIBA
    else:
        P['K_range'], P['K_source'] = (0.44, 0.52), 'TI CD74HC123 Fig.5 / Nexperia Fig.6: K ~0.48 at 3.3 V (+-0.02 graph, +-0.02 spread assumed)'
    f = lambda ref, fn: ctrl.net(ref, ctrl.pin_by_func(ref, fn))
    gnd, v33 = 'GND', f(dk, '3V3')
    if f(u2, '1~{A}') != gnd:
        probs.append(f'{u2} 1A not grounded ({f(u2, "1~{A}")})')
    if f(u2, 'VCC') != v33:
        probs.append(f'{u2} VCC not on the DevKit 3V3')
    wdt, en, q, qb = f(u2, '1B'), f(u2, '1~{CLR}'), f(u2, '1Q'), f(u2, '1~{Q}')
    cx, rcx = f(u2, '1Cext'), f(u2, '1Rext/Cext')
    gpio = {}
    for pin, net in ctrl.pins(dk).items():
        fn = ctrl.pin_func[(dk, pin)]
        if fn.startswith('IO'):
            gpio[net] = fn
    for nm, net in (('WDT_KICK', wdt), ('TEC_EN', en)):
        if net not in gpio:
            probs.append(f'{nm} net {net} is not driven directly by a DevKit GPIO')
    rt = _passives_between(ctrl, T, 'resistor', rcx, v33)
    ct = [r for r in ro.model_refs('ctrl', 'cap_mlcc') + ro.model_refs('ctrl', 'cap_elec') if set(ctrl.pins(r).values()) == {cx, rcx}]
    if len(rt) != 1 or len(ct) != 1:
        probs.append(f'watchdog timing R/C not found (R {rt}, C {ct})')
    else:
        P['R_wd'], P['C_wd'], P['R_wd_ref'], P['C_wd_ref'] = _rval(ctrl, rt[0]), M.parse_value(ctrl.comps[ct[0]]['value']), rt[0], ct[0]
    # pulls on the firmware nets
    for key, net in (('pd_en', en), ('pd_wdt', wdt)):
        pd = _passives_between(ctrl, T, 'resistor', net, gnd)
        P[key] = _rval(ctrl, pd[0]) if pd else None
        if not pd:
            probs.append(f'no pull-down on {net}')
    le, d1, q1 = f(u3, 'LE'), f(u3, 'D1'), f(u3, 'Q1')
    if f(u3, '~{OE}') != gnd:
        probs.append(f'{u3} OE not grounded')
    if d1 not in gpio:
        probs.append(f'latch D1 net {d1} not driven by a GPIO')
    pd = _passives_between(ctrl, T, 'resistor', d1, gnd)
    P['pd_def'] = _rval(ctrl, pd[0]) if pd else None
    # ---- latch enable network: (a) RC + diode from 1Q-bar (D34-1/2) or (b) 74HC123 half 2 delay (D34-3)
    caps = ro.model_refs('ctrl', 'cap_mlcc') + ro.model_refs('ctrl', 'cap_elec')
    diodes = ro.model_refs('ctrl', 'diode')
    if f(u2, '2~{CLR}') == qb or f(u2, '2B') == qb:
        P['le_mode'] = 'hc123'
        if f(u2, '2~{A}') != gnd or f(u2, '2B') != qb or f(u2, '2~{CLR}') != qb:
            probs.append(f'{u2} half 2 is not wired A=GND, B=CLR=1Q-bar')
        cx2, rcx2 = f(u2, '2Cext'), f(u2, '2Rext/Cext')
        r2 = _passives_between(ctrl, T, 'resistor', rcx2, v33)
        c2 = [r for r in caps if set(ctrl.pins(r).values()) == {cx2, rcx2}]
        qb2 = f(u2, '2~{Q}')
        rs = [r for r in ctrl.comps if (M.match(T, ctrl.comps[r]) or {}).get('model') == 'resistor' and set(ctrl.pins(r).values()) == {qb2, le}]
        dl = [r for r in diodes if ctrl.net(r, ctrl.pin_by_func(r, 'K')) == qb and ctrl.net(r, ctrl.pin_by_func(r, 'A')) == le]
        if len(r2) != 1 or len(c2) != 1 or len(rs) != 1 or len(dl) != 1:
            probs.append(f'half-2 latch delay network changed (R {r2}, C {c2}, series R {rs}, clamp diode {dl})')
        else:
            P['R_ld'], P['C_ld'] = _rval(ctrl, r2[0]), M.parse_value(ctrl.comps[c2[0]]['value'])
            P['le_refs'] = (rs[0], dl[0], c2[0])
            P['R_le'], P['C_le'] = P['R_ld'], P['C_ld']   # for reporting
    else:
        P['le_mode'] = 'rc'
        rl = _passives_between(ctrl, T, 'resistor', qb, le)
        dl = [r for r in diodes if ctrl.net(r, ctrl.pin_by_func(r, 'K')) == qb and ctrl.net(r, ctrl.pin_by_func(r, 'A')) == le]
        cl = [r for r in caps if set(ctrl.pins(r).values()) == {le, gnd}]
        if len(rl) != 1 or len(dl) != 1 or len(cl) != 1:
            probs.append(f'latch enable network changed (R {rl}, diode {dl}, C {cl})')
        else:
            P['R_le'], P['C_le'], P['le_refs'] = _rval(ctrl, rl[0]), M.parse_value(ctrl.comps[cl[0]]['value']), (rl[0], dl[0], cl[0])
    P['gpio'] = dict(TEC_EN=gpio.get(en), WDT_KICK=gpio.get(wdt), DEFROST_REQ=gpio.get(d1))
    P['nets'] = dict(en=en, wdt=wdt, q=q, qb=qb, le=le, d=d1, q1=q1)
    # ---- across the XH-12 link to the tec card: coil drivers
    sysc = env.system
    R = ro.relays()
    k1, k2 = R['k1'], R['k2']
    uln = ro.model_refs('tec', 'uln2003')
    tdiodes = ro.model_refs('tec', 'diode')
    K = lambda r: tec.net(r, tec.pin_by_func(r, 'K'))
    A = lambda r: tec.net(r, tec.pin_by_func(r, 'A'))
    chain = {}
    for name, src, k in (('K1', q, k1), ('K2', q1, k2)):
        coil_lo, coil_hi = tec.net(k, 'A2'), tec.net(k, 'A1')
        drv = None
        if uln:
            u = uln[0]
            for c in range(1, 8):
                if tec.net(u, tec.pin_by_func(u, f'O{c}')) == coil_lo:
                    drv = ('uln', u, tec.net(u, tec.pin_by_func(u, f'I{c}')))
        for qn in ro.model_refs('tec', 'npn'):
            if tec.net(qn, tec.pin_by_func(qn, 'C')) == coil_lo and tec.net(qn, tec.pin_by_func(qn, 'E')) == gnd:
                base = tec.net(qn, tec.pin_by_func(qn, 'B'))
                rb = [r for r in tec.comps if (M.match(T, tec.comps[r]) or {}).get('model') == 'resistor' and base in tec.pins(r).values()
                      and gnd not in tec.pins(r).values()]
                inp = [n for n in tec.pins(rb[0]).values() if n != base][0] if rb else None
                drv = ('npn', qn, inp)
        if drv is None:
            probs.append(f'{name} ({k}) coil low side not driven by a ULN2003 channel or an NPN low side')
            continue
        if drv[2] is None or not sysc.same(('ctrl', src), ('tec', drv[2])):
            probs.append(f'{name}: driver input {drv[2]} is not connected to ctrl {src}')
        chain[name] = dict(relay=k, driver=drv[0], drv_ref=drv[1], coil_hi=coil_hi, coil_lo=coil_lo)
    P['chain'] = chain
    P['drive'] = chain.get('K1', {}).get('driver', 'uln')
    # K1: coil high side = thermostat loop return; clamp = diode straight across, or diode + zener to the coil high side
    if 'K1' in chain:
        c1 = chain['K1']
        _, jth = ro.lead_conn('THERMO')
        if c1['coil_hi'] not in set(tec.pins(jth).values()):
            probs.append('K1 coil high side is not the thermostat loop return')
        direct = [r for r in tdiodes if K(r) == c1['coil_hi'] and A(r) == c1['coil_lo']]
        P['k1_vz'] = 0.0
        if direct:
            P['k1_flyback'], P['k1_flyback_mpn'] = direct[0], tec.comps[direct[0]]['mpn']
        else:
            d1_ = [r for r in tdiodes if A(r) == c1['coil_lo']]
            z = [r for r in tdiodes if d1_ and K(r) == K(d1_[0]) and A(r) == c1['coil_hi']]
            if d1_ and z:
                P['k1_flyback'], P['k1_flyback_mpn'] = d1_[0], tec.comps[d1_[0]]['mpn']
                P['k1_zener'] = z[0]
                P['k1_vz'] = 15.0 if 'C15' in tec.comps[z[0]]['mpn'] or '15' in tec.comps[z[0]]['value'] else M.parse_value(tec.comps[z[0]]['value'])
            else:
                P['k1_flyback'] = P['k1_flyback_mpn'] = None
                probs.append('no flyback path (diode, or diode + zener) across K1 coil')
    # K2: ULN COM clamp (D34-1/2) or hold-up: supply diode, C across coil+R, freewheel diode into the hold node (D34-3)
    P['k2_holdup'] = None
    if 'K2' in chain:
        c2 = chain['K2']
        if c2['driver'] == 'uln':
            com = tec.net(uln[0], tec.pin_by_func(uln[0], 'COM'))
            if c2['coil_hi'] != com:
                probs.append('K2 coil high side is not the ULN COM clamp rail (no flyback path)')
        else:
            sup = c2['coil_hi']
            d5 = [r for r in tdiodes if K(r) == sup]
            par = [r for r in ro.model_refs('tec', 'cap_elec') + ro.model_refs('tec', 'cap_mlcc') if set(tec.pins(r).values()) == {sup, c2['coil_lo']}]
            if d5 and par:
                P['k2_holdup'] = dict(mode='parallel', C=M.parse_value(tec.comps[par[0]]['value']), R8=None, refs=(d5[0], par[0]))
                d5 = []   # handled
            elif not d5:
                d5 = None
            hold_c = [r for r in ro.model_refs('tec', 'cap_elec') + ro.model_refs('tec', 'cap_mlcc') if sup in tec.pins(r).values()]
            hold = [n for r in hold_c for n in tec.pins(r).values() if n != sup]
            d6 = [r for r in tdiodes if A(r) == c2['coil_lo'] and hold and K(r) == hold[0]]
            r8 = [r for r in tec.comps if (M.match(T, tec.comps[r]) or {}).get('model') == 'resistor'
                  and hold and set(tec.pins(r).values()) == {c2['coil_lo'], hold[0]}]
            if P['k2_holdup']:
                pass
            elif d5 and hold_c and d6 and r8:
                P['k2_holdup'] = dict(mode='series', C=M.parse_value(tec.comps[hold_c[0]]['value']), R8=_rval(tec, r8[0]), refs=(d5[0], hold_c[0], d6[0], r8[0]))
            else:
                probs.append(f'K2 hold-up network not recognised (supply diode {d5}, C {hold_c}, freewheel {d6}, R {r8})')
    # 12 V undervoltage cut-off on the K1 coil feed: PNP (E = +12 V, C = loop feed) driven by a TL431 with hysteresis
    P['uv'] = None
    _, jth = ro.lead_conn('THERMO')
    loop = tec.net(jth, '1')
    for qp in ro.model_refs('tec', 'pnp'):
        if tec.net(qp, tec.pin_by_func(qp, 'C')) == loop:
            v12n = tec.net(qp, tec.pin_by_func(qp, 'E'))
            shunts = ro.model_refs('tec', 'shunt_ref')
            if not shunts:
                probs.append('K1 feed PNP found but no TL431-class reference')
                break
            u = shunts[0]
            refn = tec.net(u, tec.pin_by_func(u, 'REF'))
            rs = {}
            for r in tec.comps:
                if (M.match(T, tec.comps[r]) or {}).get('model') != 'resistor':
                    continue
                nets_ = set(tec.pins(r).values())
                if refn in nets_:
                    other = (nets_ - {refn}).pop()
                    rs[other] = _rval(tec, r)
            if not {v12n, gnd, loop} <= set(rs):
                probs.append(f'UV divider not recognised at {refn}: {rs}')
                break
            P['uv'] = dict(rt=rs[v12n], rb=rs[gnd], rh=rs[loop], pnp=qp, tl431=u, loop=loop)
            g = 1 / rs[v12n] + 1 / rs[gnd] + 1 / rs[loop]
            vref, vs = 2.495, 0.15
            P['uv']['v_trip'] = (vref * g + vs / rs[loop]) / (1 / rs[v12n] + 1 / rs[loop])
            P['uv']['v_rec'] = vref * g * rs[v12n]
    row = M.match(T, tec.comps[k1])
    P['relay'] = row['params']
    return P, probs


# ----------------------------------------------------------------------------- simulation
class Sample:
    """Per-instance parameters (arrays of length N)."""

    def __init__(self, P, n, rng, corner=None, temp_coil=60.0, v12=12.0):
        rel = P['relay']
        corner = corner or {}
        u = lambda lo, hi: rng.uniform(lo, hi, n)
        def pick(key, lo, hi, worst):
            c = corner.get(key)
            if c == 'worst':
                return np.full(n, worst)
            if c == 'slow':   # the opposite end of the range from 'worst'
                return np.full(n, lo if worst == hi else hi)
            return u(lo, hi)
        # watchdog: tw = K R C ; K ~0.48 at 3.3 V (typ, graph +-0.02) -> 0.44-0.52 assumed spread; R 1 %; C +-10 % X7R,
        # -5 % DC bias (assumed), +-5 % temperature; Rext/Cext pin leakage not published (+-10 % allowance, assumed)
        K = u(*P.get('K_range', (0.44, 0.52)))
        self.tw = K * P['R_wd'] * u(0.99, 1.01) * P['C_wd'] * u(0.90, 1.10) * u(0.90, 1.0) * u(0.95, 1.05) * u(0.9, 1.1)
        self.tau_le = P['R_le'] * u(0.99, 1.01) * P['C_le'] * u(0.90, 1.10) * u(0.90, 1.0) * u(0.95, 1.05)
        if P.get('le_mode') == 'hc123':   # half 2 of the same package: same K, own R/C tolerances
            self.tw2 = K * u(0.98, 1.02) * P['R_ld'] * u(0.99, 1.01) * P['C_ld'] * u(0.90, 1.10) * u(0.90, 1.0) * u(0.95, 1.05) * u(0.9, 1.1)
            if corner.get('vt_le') == 'worst':
                self.tw2 = np.full(n, (P['K_range'][0] * 0.98 * P['R_ld'] * 0.99 * P['C_ld'] * 0.9 * 0.9 * 0.95 * 0.9))
        # LE switching threshold of the 74HC573 at 3.3 V: between VIL max and VIH min (interpolated 0.94-2.36 V)
        self.vt_le = pick('vt_le', 0.94, 2.36, 0.94)
        rc = rel['r_coil'] * (1 + 0.00393 * (temp_coil - 23.0))
        self.rc = np.full(n, rc) * u(0.9, 1.1)                    # +-10 % coil resistance tolerance (datasheet)
        self.L1 = pick('L', rel['L'][0], rel['L'][2], rel['L'][2])
        self.L2 = pick('L2', rel['L'][0], rel['L'][2], rel['L'][0])
        i_rated = 12.0 / rel['r_coil']
        # pick-up between 40 % and the 70 % must-operate; drop-out between the 10 % must-release and 40 % (assumed spread)
        self.iop1, self.iop2 = u(0.40, 0.70) * i_rated, pick('iop2', 0.40, 0.70, 0.40) * i_rated
        self.irel1 = pick('irel1', 0.10, 0.40, 0.10) * i_rated
        self.irel2 = pick('irel2', 0.10, 0.40, 0.40) * i_rated
        self.tm_op1, self.tm_op2 = u(2e-3, 7e-3), pick('tm_op2', 2e-3, 7e-3, 2e-3)       # armature travel (assumed)
        self.tm_rel1 = pick('tm_rel1', 1e-3, 4e-3, 4e-3)
        self.tm_rel2 = pick('tm_rel2', 1e-3, 4e-3, 1e-3)
        self.t_transfer2 = u(1e-3, 3e-3)          # K2 NC-break to NO-make travel incl. bounce (assumed)
        npn = P.get('drive') == 'npn'
        # coil driver saturation: ULN2003 Darlington 0.75-1.05 V; 2N3904 at 30-35 mA / 2.6 mA base 0.13-0.22 V (onsemi Fig.16, +-0.03 V)
        self.vce = u(0.13, 0.22) if npn else u(0.75, 1.05)
        fb = (P.get('k1_flyback_mpn') or '').upper()
        self.vf1 = u(0.25, 0.45) if fb.startswith('1N58') else u(0.6, 0.8)   # K1 flyback: Schottky or 1N400x at ~30 mA
        if P.get('k1_vz'):
            self.vf1 = self.vf1 + P['k1_vz'] * u(13.8 / 15, 15.6 / 15)       # + zener (BZX79-C15 13.8-15.6 V)
        self.vf2 = u(0.25, 0.45) if npn else u(0.7, 1.0)   # K2 freewheel: 1N5817 (hold-up) or ULN2003 clamp at ~30 mA
        self.vin_uln = u(0.65, 0.8) if npn else u(1.3, 2.0)   # driver turn-on at the logic output (NPN VBE via 1k/47k; ULN 2 x VBE)
        hu = P.get('k2_holdup')
        self.c_hold = hu['C'] * u(0.8, 1.2) if hu else None    # electrolytic +-20 %
        if hu and corner.get('c_hold') == 'min':
            self.c_hold = np.full(n, hu['C'] * 0.8)
        self.r8 = hu['R8'] if hu else None
        self.vf5 = u(0.25, 0.45)
        uv = P.get('uv')
        if uv:
            vref = u(2.44, 2.55)                       # TL431A Vref 2.440-2.550 V (datasheet range incl. temperature)
            rt, rb, rh = (uv[k] * u(0.99, 1.01) for k in ('rt', 'rb', 'rh'))
            g = 1 / rt + 1 / rb + 1 / rh
            vs = u(0.1, 0.3)                           # BC327 VCE(sat)
            self.uv_trip = (vref * g + vs / rh) / (1 / rt + 1 / rh)
            self.uv_rec = vref * g * rt
        self.q3_ilim = u(0.15, 0.45)                   # 2N3904 collector current with ~2.6 mA base (hFE 60-170 at 50-150 mA)
        self.v12 = v12


def simulate(P, S, drive, n, T, dt=2e-4, record=None, steady=None):
    """drive(t, step) -> dict of arrays (n,): en, wdt, dfr in {0,1,2(Z)}, v33 (V), v12 (V), thermo (0/1), dps (0/1).
    Returns dict of event counters per instance and optional traces for instances in `record`."""
    steps = int(T / dt)
    q_end = np.full(n, -1.0)
    v_le = np.zeros(n)
    t_raw_rise = np.full(n, -np.inf)
    hold = S.c_hold is not None
    hold_par = hold and (P.get('k2_holdup') or {}).get('mode') == 'parallel'
    vc = np.full(n, 12.0)
    uv_ok = np.ones(n, bool)
    prev_uv = np.ones(n, bool)
    latch = np.zeros(n, bool)
    i1 = np.zeros(n); i2 = np.zeros(n)
    st1 = np.zeros(n, np.int8); st2 = np.zeros(n, np.int8)   # 0 released, 1 operating (moving), 2 operated, 3 releasing (moving)
    tmv1 = np.zeros(n); tmv2 = np.zeros(n)
    k1_closed = np.zeros(n, bool)
    prev_wdt = np.zeros(n, bool); prev_en = np.zeros(n, bool); prev_qb = np.ones(n, bool)
    prev_v33 = np.full(n, 3.3)
    if steady is not None:   # start from a settled state: dict en, dfr (0/1 arrays or scalars)
        en0 = np.broadcast_to(np.asarray(steady.get('en', 0)) == 1, (n,))
        latch = np.broadcast_to(np.asarray(steady.get('dfr', 0)) == 1, (n,)).copy()
        q_end = np.where(en0, S.tw, -1.0)
        v_le = np.where(en0, 0.0, VCC)
        i1 = np.where(en0, (S.v12 - S.vce) / S.rc, 0.0)
        i2 = np.where(latch, (S.v12 - S.vf5 - S.vce) / S.rc, 0.0)
        vc = np.where(latch, S.v12 - S.vf5 - S.vce, 0.0)
        out_vc0 = vc
        t_raw_rise = np.where(en0, np.inf, -np.inf)
        st1 = np.where(en0, 2, 0).astype(np.int8)
        st2 = np.where(latch, 2, 0).astype(np.int8)
        prev_en = en0.copy()
    out = {k: np.zeros(n, int) for k in ('k2_cmd_changes', 'k2_cmd_k1_closed', 'k2_cmd_k1_closed_dps', 'k2_start_k1_closed', 'k2_start_k1_closed_dps', 'k2_move_k1_closed', 'k2_move_k1_closed_dps', 'k1_make_k2_moving', 'k1_make_k2_moving_dps',
                                         'k1_closed_en_low', 'k1_closed_no_kick', 'k1_closed_thermo_open', 'k1_closed_boot',
                                         'k1_closures')}
    out['max_k1_after_en_low'] = np.zeros(n)
    out['vc_min'] = np.full(n, 99.0)
    out['uv_trips'] = np.zeros(n, int)
    out['max_k1_after_kick'] = np.zeros(n)
    t_en_low = np.full(n, np.inf)
    t_last_kick = np.full(n, -np.inf)
    t_last_trig = np.full(n, -np.inf)
    out['max_k1_after_trig'] = np.zeros(n)
    t_thermo_open = np.full(n, np.inf)
    t_boot = np.full(n, np.inf)
    prev_k2on = None
    tr = {k: [] for k in ('t', 'en', 'wdt', 'dfr', 'q', 'v_le', 'k2on', 'i1', 'i2', 'k1', 'k2', 'v12', 'v33')} if record is not None else None
    for s in range(steps):
        t = s * dt
        d = drive(t, s)
        v33 = d['v33']
        vcc_ok = v33 > 2.0
        en = (d['en'] == 1) & vcc_ok
        wdt = (d['wdt'] == 1) & vcc_ok
        dfr = (d['dfr'] == 1) & vcc_ok
        # 74HC123 (A grounded): trigger on B rising with CLR high, or CLR rising with B high
        trig = en & ((wdt & ~prev_wdt) | (en & ~prev_en & wdt))
        powerup = vcc_ok & (prev_v33 <= 2.0)
        trig |= powerup & en                                     # Nexperia: possible power-up pulse when CLR is high
        q_end = np.where(trig, t + S.tw, q_end)
        q_end = np.where(~en, -1.0, q_end)
        q = en & (t < q_end) & vcc_ok
        qb_high = ~q & vcc_ok
        # latch enable RC: slow charge through R when Q-bar is high; fast discharge through the diode when low
        v_le = np.where(qb_high, v_le + (v33 - v_le) * (1 - np.exp(-dt / S.tau_le)),
                        np.minimum(v_le, np.where(vcc_ok, 0.45, v_le)) * np.exp(-dt / S.tau_le))
        if P.get('le_mode') == 'hc123':
            # half 2 is triggered by every rise of 1Q-bar (B and CLR); 2Q-bar keeps LE low for tw2; the 1N5817 holds LE low
            # while 1Q-bar is low. No pulse is assumed at power-up (worst case: transparent at once; K1 is off then).
            rise = qb_high & ~prev_qb & ~powerup
            t_raw_rise = np.where(rise, t, t_raw_rise)
            # power-up: CLR (= B = 1Q-bar) rises with VCC; per the CLR-trigger rule this starts a delay (default). The
            # 'no_powerup_pulse' sensitivity case makes the latch transparent at once instead.
            t_raw_rise = np.where(powerup, -np.inf if P.get('no_powerup_pulse') else t, t_raw_rise)
            transparent = qb_high & (t - t_raw_rise >= S.tw2) & vcc_ok
        else:
            transparent = (v_le > S.vt_le) & vcc_ok
        latch = np.where(powerup, np.random.default_rng(s).random(n) < 0.5, latch)   # undefined at power-up
        latch = np.where(transparent, dfr, latch)
        k2on = latch & vcc_ok
        if prev_k2on is None:
            prev_k2on = k2on.copy()
        k2_cmd_change = (k2on != prev_k2on) & vcc_ok
        prev_k2on = k2on
        # ULN inputs follow the logic outputs (scaled by the logic supply)
        u1 = q & (v33 > S.vin_uln)
        if P.get('k1_uv'):          # what-if: 12 V undervoltage detector removes K1 drive below the threshold
            u1 = u1 & (d['v12'] > P['k1_uv'])
        u2 = k2on & (v33 > S.vin_uln)
        # coils
        v12 = d['v12']
        th = d['thermo'] == 1
        if P.get('uv'):
            uv_ok = np.where(uv_ok, v12 > S.uv_trip, v12 > S.uv_rec)
            out['uv_trips'] += uv_ok != prev_uv
            prev_uv = uv_ok
            th = th & uv_ok
        vs1 = np.where(th, v12, 0.0)
        vc1 = np.where(u1 & th, np.maximum(vs1 - S.vce, -S.vf1), -S.vf1 - i1 * 0)
        vc1 = np.where(u1 & ~th, -S.vf1, vc1)
        if hold_par:
            # C1 directly across the coil, charged only through Q3 (current-limited by its gain) from +12 V via D5
            rail = v12 - S.vf5 - S.vce
            need = rail - vc
            charge = np.where(u2 & (need > 0), np.minimum(need * S.c_hold / dt, np.maximum(S.q3_ilim - i2, 0.0)), 0.0)
            vc = vc + (charge - i2) * dt / S.c_hold
            # rail below C1: D5 blocks, C1 only discharges into the coil (handled by the - i2 term above)
            vc2 = vc
            out['vc_min'] = np.minimum(out['vc_min'], vc)
        elif hold:
            rail = v12 - S.vf5
            from_cap = vc - i2 * S.r8
            vc2 = np.where(u2, np.maximum(rail, from_cap) - S.vce, vc - S.vf2)
            vc2 = np.where(~u2 & (i2 <= 0), np.minimum(vc2, 0.0), vc2)
            rail_feeds = u2 & (rail >= from_cap)
            vc = np.where(rail_feeds, vc + (rail - S.vce - vc) * (1 - np.exp(-dt / (S.r8 * S.c_hold))), vc - i2 * dt / S.c_hold)
            out['vc_min'] = np.minimum(out['vc_min'], vc)
        else:
            vc2 = np.where(u2, np.maximum(v12 - S.vce, -S.vf2), -S.vf2)
        i1 = np.maximum(i1 + dt * (vc1 - i1 * S.rc) / S.L1, 0.0)
        i2 = np.maximum(i2 + dt * (vc2 - i2 * S.rc) / S.L2, 0.0)
        # armatures
        k2_was_moving = (st2 == 1) | (st2 == 3)
        for st, i, iop, irel, top, trel, tmv in ((st1, i1, S.iop1, S.irel1, S.tm_op1, S.tm_rel1, tmv1),
                                                  (st2, i2, S.iop2, S.irel2, S.tm_op2 + S.t_transfer2, S.tm_rel2 + S.t_transfer2, tmv2)):
            start_op = (st == 0) & (i >= iop)
            start_rel = (st == 2) & (i <= irel)
            st[start_op] = 1; tmv[start_op] = t + top[start_op]
            st[start_rel] = 3; tmv[start_rel] = t + trel[start_rel]
            done = ((st == 1) | (st == 3)) & (t >= tmv)
            st[done & (st == 1)] = 2
            st[done & (st == 3)] = 0
            # a coil that drops/picks again mid-travel reverses (conservative: still counts as moving)
            back = (st == 1) & (i <= irel)
            st[back] = 3; tmv[back] = t + trel[back]
        # K1 contacts closed from the end of operate travel until the start of release travel completes
        k1_now = (st1 == 2) | (st1 == 3)
        k2_moving = (st2 == 1) | (st2 == 3)
        k2_start = k2_moving & ~k2_was_moving
        out['k2_cmd_k1_closed'] += k2_cmd_change & k1_now
        out['k2_cmd_changes'] += k2_cmd_change
        out['k2_cmd_k1_closed_dps'] += k2_cmd_change & k1_now & (d['dps'] == 1)
        out['k2_start_k1_closed'] += k2_start & k1_now
        out['k2_start_k1_closed_dps'] += k2_start & k1_now & (d['dps'] == 1)
        dps = d['dps'] == 1
        out['k2_move_k1_closed'] += (k2_moving & k1_now)
        out['k2_move_k1_closed_dps'] += (k2_moving & k1_now & dps)
        k1_make = k1_now & ~k1_closed
        out['k1_closures'] += k1_make
        out['k1_make_k2_moving'] += k1_make & (k2_moving | k2_was_moving)
        out['k1_make_k2_moving_dps'] += k1_make & (k2_moving | k2_was_moving) & dps
        k1_closed = k1_now
        # bookkeeping for the cut-off properties
        t_en_low = np.where(~en & np.isinf(t_en_low), t, np.where(en, np.inf, t_en_low))
        t_last_kick = np.where(wdt & ~prev_wdt, t, t_last_kick)
        t_last_trig = np.where(trig, t, t_last_trig)
        out['max_k1_after_trig'] = np.where(k1_now, np.maximum(out['max_k1_after_trig'], t - np.maximum(t_last_trig, 0)),
                                            out['max_k1_after_trig'])
        t_thermo_open = np.where(~th & np.isinf(t_thermo_open), t, np.where(th, np.inf, t_thermo_open))
        out['max_k1_after_en_low'] = np.where(k1_now & np.isfinite(t_en_low), np.maximum(out['max_k1_after_en_low'], t - t_en_low),
                                              out['max_k1_after_en_low'])
        out['max_k1_after_kick'] = np.where(k1_now, np.maximum(out['max_k1_after_kick'], t - np.maximum(t_last_kick, 0)),
                                            out['max_k1_after_kick'])
        out['k1_closed_thermo_open'] += k1_now & np.isfinite(t_thermo_open) & (t - t_thermo_open > 0.1)
        boot = d.get('boot', np.zeros(n, bool))
        t_boot = np.where(boot & np.isinf(t_boot), t, np.where(boot, t_boot, np.inf))
        out['k1_closed_boot'] += k1_now & boot & (t - t_boot > 0.05)   # beyond the release time of a K1 that was on at reset
        prev_wdt, prev_en, prev_v33, prev_qb = wdt, en, v33, qb_high
        if tr is not None and s % 5 == 0:
            for k, v in (('t', t), ('en', en), ('wdt', wdt), ('dfr', dfr), ('q', q), ('v_le', v_le), ('k2on', k2on), ('i1', i1),
                         ('i2', i2), ('k1', st1.copy()), ('k2', st2.copy()), ('v12', v12), ('v33', v33)):
                tr[k].append(v if np.isscalar(v) else np.asarray(v)[record].copy())
    if tr is not None:
        out['trace'] = {k: np.array(v) for k, v in tr.items()}
    return out
