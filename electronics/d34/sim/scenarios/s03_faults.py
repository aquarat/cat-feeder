"""S03 - Overcurrent / short circuit on each protected branch (Python + datasheet tables + PCB geometry).

For each fault: the fault current range (set by the source's own limit), the protective device's time to
clear (datasheet opening-time table / PTC trip point), and whether the copper (IPC-2152 fit on the real
routed tracks), connectors, relay contacts and semiconductors in the path survive for that time.
"""
import math

import numpy as np

from d34sim import flows, pcb, report

TITLE = 'Short circuits on each branch: clearing time vs track, connector and device ratings'


def fuse297_tmax(i, rating, table):
    """Max opening time (s) of the Littelfuse 297 mini fuse by log-log interpolation of the datasheet table.
    Returns inf below 135 % (the fuse may carry 110-135 % indefinitely / for up to 600 s)."""
    pct = 100.0 * i / rating
    pts = sorted((float(k), v[1]) for k, v in table.items() if v[1] is not None)
    if pct < pts[0][0]:
        return math.inf
    for (p0, t0), (p1, t1) in zip(pts, pts[1:]):
        if p0 <= pct <= p1:
            f = (math.log(pct) - math.log(p0)) / (math.log(p1) - math.log(p0))
            return math.exp(math.log(t0) + f * (math.log(t1) - math.log(t0)))
    return pts[-1][1]


def ptc_tmax(i, t_ref=8.2, i_ref=5.5, ihold=1.1):
    """RXEF110 max time to trip: datasheet point 8.2 s at 5.5 A (20 C); I^2 t = const assumed for other currents."""
    if i <= ihold:
        return math.inf
    return t_ref * (i_ref / i) ** 2


def track_transient_dT(dT_ss, t, tau=40.0):
    """First-order thermal response of a track (tau ~40 s estimated for 1 oz on 1.6 mm FR-4)."""
    return dT_ss if math.isinf(t) else dT_ss * (1 - math.exp(-t / tau))


def run(env):
    chk = report.Checks('s03_faults', env.outdir('s03_faults'))
    L = env.limit
    ds = env.datasheets.get('parts', {})
    boards = {c: pcb.load(env.d34 / f'd34-{c}' / f'd34-{c}.kicad_pcb') for c in ('ctrl', 'pwr', 'tec')}
    fuse_tab = ds['0297007.5']['values']['opening_time_vs_pct_rating']['value']
    rerate = L('fuse297_7a5_rerate_40C')[0]
    ocp_lo, s_ocp = L('brick_ocp_min')
    ocp_hi, _ = L('brick_ocp_max')
    from d34sim import models as M

    def ilim(ref):
        comp = env.cards['pwr'].comps[ref]
        row = M.match(env.table, comp)
        lim = row['params'].get('ilim', [2.5, 3.5, 5.0])
        return lim[0], lim[2], f"{comp['mpn']} current limit {lim[0]}-{lim[2]} A ({row['provenance'][:80]})"
    dT_fault, s_fault = L('track_dT_fault')
    rows = []

    pads = {c: pcb.pads(env.d34 / f'd34-{c}' / f'd34-{c}.kicad_pcb') for c in boards}
    ro = flows.Roles(env)
    integrity = []

    def copper(paths, t_clear, label):
        """Solve each path's copper; return (dT at clearing time, location, steady dT) for the hottest segment."""
        worst = None
        for board, net, inj in paths:
            segs, missing, vias_i = pcb.solve_net(boards[board], pads[board], net, inj)
            if missing:
                integrity.append(f'{label}: {board} {net}: {missing}')
            if not segs:
                continue
            hot = max(segs, key=lambda x: x['dT'])
            tr = track_transient_dT(hot['dT'], t_clear)
            rows.append(dict(fault=label, board=board, net=net, i_segment_A=hot['i'], t_clear_s=t_clear, dT_steady=hot['dT'],
                             dT_at_clear=tr, width_mm=hot['width_mm'], layer=hot['layer'],
                             x_mm=round(hot['start'][0] - 50, 2), y_mm=round(hot['start'][1] - 50, 2),
                             max_via_A=max(vias_i) if vias_i else 0.0))
            if worst is None or tr > worst[0]:
                worst = (tr, f'{board} {net} {hot["layer"]} {hot["width_mm"]} mm at ({hot["start"][0] - 50:.1f},{hot["start"][1] - 50:.1f}) '
                             f'carrying {hot["i"]:.1f} A', hot['dT'])
        return worst

    # ------------------------------------------------------------------ F1: DPS input short
    i_f = ocp_hi
    t1 = fuse297_tmax(i_f, 7.5 * rerate, fuse_tab)
    w = copper(flows.front_paths(ro, i_f, {}), t1, 'F1 branch: DPS input short (brick-limited)')
    chk.add('f1_clear', f'F1 7.5 A clears a DPS-input short at the brick current limit ({ocp_lo:.0f}-{ocp_hi:.0f} A)',
            t1, 5.0, '<=', 's', f'Littelfuse 297 opening-time table (135 % -> 600 s max) at 98 % rerating; brick {s_ocp}; project limit 5 s',
            severity='protection', advisory=True,
            detail=f'{100 * i_f / (7.5 * rerate):.0f} % of the rerated fuse: F1 is not guaranteed to open; the brick hiccup is the effective '
                   'protection (README D34-3 documents F1 as a wiring fuse and the GST160A24 hiccup as the short-circuit protection)')
    chk.add('f1_copper', 'Hottest copper on the F1 path while a brick-limited short persists', w[0], dT_fault, '<=', 'K', s_fault,
            severity='protection', corner=w[1], detail=f'steady {w[2]:.0f} K (constant-current brick; hiccup duty lowers the average)')
    v, s = L('minifit_a_per_pin')
    chk.add('f1_j1_minifit', 'Brick inlet J1 (Mini-Fit Jr) current during a brick-limited short', i_f, v, '<=', 'A', s, severity='protection',
            advisory=True, detail='exceeds the 9 A contact rating only while the brick stays in constant current; a hiccup brick cycles it')
    v, s = L('mstb_a_per_pin')
    chk.add('f1_j2_mstb', 'DPS input plug J2 (MSTB) current during a brick-limited short', i_f, v, '<=', 'A', s, severity='protection')
    # ------------------------------------------------------------------ F2: aux branch short
    r_ptc = 0.15
    i_aux = min(ocp_hi, 25.2 / (r_ptc + 0.05))
    t2 = ptc_tmax(i_aux)
    F = ro.front_end()
    pc_ = ro.cards['pwr']
    loads = {r: (pc_.pin_by_func(r, 'IN'), None) for r in ro.model_refs('pwr', 'buck')}
    for r in ro.model_refs('pwr', 'stepstick'):
        loads[r] = (pc_.pin_by_func(r, 'VMOT'), None)
    loads = {r: v for r, v in loads.items() if pc_.net(r, v[0]) == F['vmot']}   # only loads on the PTC output
    w = None
    for ref, (pin, _) in loads.items():   # short located at each VMOT load in turn
        wi = copper(flows.front_paths(ro, 0.0, {ref: (pin, i_aux)}), t2, f'F2 branch: VMOT short at {ref} (brick-limited)')
        if wi and (w is None or wi[0] > w[0]):
            w = wi
    chk.add('f2_clear', 'F2 RXEF110 trips on a VMOT short at the brick current limit', t2, 10.0, '<=', 's',
            'Littelfuse RXEF110 max time to trip 8.2 s at 5.5 A (I2t scaling assumed); project limit 10 s', severity='protection',
            detail=f'{i_aux:.1f} A')
    chk.add('f2_copper', 'Hottest copper on the aux path until the PTC trips (first-order track model, tau 40 s estimated)', w[0], dT_fault,
            '<=', 'K', s_fault, severity='protection', corner=w[1], detail=f'steady-state would be {w[2]:.0f} K')
    # PTC nuisance trip margin is a power-budget item (S10)
    # ------------------------------------------------------------------ 12 V faults
    t_h = math.inf  # OKI hiccups indefinitely
    b12 = ro.bucks()[12.0]
    oki_lo, oki_hi, s_oki = ilim(b12)
    l5_lo, l5_hi, s_5 = ilim(ro.bucks()[5.0])
    pc = ro.cards['pwr']
    v12 = pc.net(b12, pc.pin_by_func(b12, 'OUT'))
    _, j12 = ro.lead_conn('LINK_12V')
    jp = ro.pin_on('pwr', j12, v12)
    bo = (b12, pc.pin_by_func(b12, 'OUT'))
    worst12 = (0.0, '', 0.0)
    for ref in sorted({r for r, p, f in pc.nodes_on(v12)} - {b12}):
        for pin in ro.pin_on('pwr', ref, v12):
            wi = copper([('pwr', v12, {bo: oki_hi, (ref, pin): -oki_hi})], t_h, f'+12V short at pwr {ref}.{pin} (regulator current limit)')
            if wi and wi[0] > worst12[0]:
                worst12 = wi
    tc = ro.cards['tec']
    _, j12t = ro.h['leads']['LINK_12V']['b']
    jt = ro.pin_on('tec', j12t, v12)
    for ref in sorted({r for r, p, f in tc.nodes_on(v12)} - {j12t}):
        for pin in ro.pin_on('tec', ref, v12):
            wi = copper([('tec', v12, {**{(j12t, p): oki_hi / len(jt) for p in jt}, (ref, pin): -oki_hi})], t_h,
                        f'+12V short at tec {ref}.{pin} (regulator current limit)')
            if wi and wi[0] > worst12[0]:
                worst12 = wi
    chk.add('v12_short_copper', '+12 V short: copper at the 12 V regulator current limit (continuous auto-recovery)', worst12[0], dT_fault, '<=', 'K', s_fault,
            severity='protection', corner=worst12[1], advisory=True,
            detail=s_oki)
    v, s = L('vh_a_per_pin')
    chk.add('v12_short_vh', '+12 V short: VH-3 link current (2 pins share +12 V)', oki_hi / 2, v, '<=', 'A', s, severity='protection')
    # ---- fan lead shorts: each fan connector's +12 V pin, its feed protection and its low-side switch
    for lead in ('FAN1', 'FAN2', 'FAN3'):
        if lead not in env.harness['leads']:
            continue
        _, jf = env.harness['leads'][lead]['a']
        fpins = tc.pins(jf)
        if not fpins:
            continue
        feed = fpins.get('2')
        ptc = [r for r in ro.model_refs('tec', 'ptc') if feed in tc.pins(r).values() and v12 in tc.pins(r).values()]
        low = fpins.get('1')
        sw = None
        if low and low != 'GND':
            for r in ro.model_refs('tec', 'nmos'):
                if tc.net(r, tc.pin_by_func(r, 'D')) == low:
                    sw = ('nmos', r)
            for r in ro.model_refs('tec', 'uln2003'):
                sw = sw or ('uln2003', r)
        if ptc:
            prow = M.match(env.table, tc.comps[ptc[0]])['params']
            t_ref, i_ref = prow.get('t_trip_ref', [4.0, 2.5])
            i_f = oki_hi
            t_trip = ptc_tmax(i_f, t_ref=t_ref, i_ref=i_ref, ihold=prow['ihold'])
            chk.add(f'{lead.lower()}_short_trip', f'{lead} lead short (+12 V to its return) at the 12 V regulator current limit: {ptc[0]} '
                    f'({tc.comps[ptc[0]]["mpn"]}) time to trip', t_trip, 2.0, '<=', 's',
                    f'Littelfuse {tc.comps[ptc[0]]["mpn"]} max time to trip {t_ref} s at {i_ref} A (I2t scaling assumed); project limit 2 s',
                    severity='protection', detail=f'{i_f:.1f} A; {s_oki}')
            if sw and sw[0] == 'nmos':
                rds = 0.035 * 1.5   # IRLZ44N 35 mOhm max at 4 V, x1.5 hot (datasheet); 3.3 V drive is below the specified VGS
                e = i_f ** 2 * rds * t_trip
                chk.add(f'{lead.lower()}_short_fet', f'{lead} short with the low-side {sw[1]} on: MOSFET energy until the polyfuse trips',
                        e, 2.0, '<=', 'J', 'IRLZ44N RthJA 62 K/W, Tj 175 C: ~2 J absorbs without exceeding Tj from a 40 C bay (TO-220 '
                        'thermal mass ~1.5 J/K estimate, project screen)', severity='protection', detail=f'{i_f:.1f} A x {rds * 1e3:.0f} mOhm x {t_trip:.2f} s')
            w = copper([('tec', v12, {**{(j12t, p): i_f / len(jt) for p in jt}, (ptc[0], next(p for p, n in tc.pins(ptc[0]).items() if n == v12)): -i_f})],
                       t_trip, f'{lead} short: +12V copper until {ptc[0]} trips')
            if w:
                chk.add(f'{lead.lower()}_short_copper', f'{lead} short: hottest +12 V copper until the polyfuse trips', w[0], dT_fault, '<=', 'K', s_fault,
                        severity='protection', corner=w[1])
        elif sw and sw[0] == 'uln2003':
            v, s = L('uln2003_ic_max')
            chk.add(f'{lead.lower()}_lowside_short', f'{lead} lead short with the ULN2003 channel on: current available to the channel', oki_lo, v, '<=',
                    'A', f'{s}; source = {s_oki}', severity='protection', detail='nothing limits the 12 V fan feed below the ULN2003 rating')
        else:
            chk.add(f'{lead.lower()}_feed_protected', f'{lead} +12 V feed has its own polyfuse', 0, 1, '==', '', 'project (fault containment)',
                    severity='protection', advisory=True)
    # ------------------------------------------------------------------ 5 V / 3V3
    v, s = L('xh_a_per_pin')
    chk.add('v5_short_xh', '+5 V short at the ctrl card: XH-11 current per pin (2 pins +5 V, 2 pins GND)', l5_hi / 2, v, '<=', 'A', s,
            severity='protection', detail=s_5)
    ilim_ldo = 1.5
    v, s = L('d1n5819_if_max')
    chk.add('v33_short_d1', '3V3 short (sensor header): D1 1N5819 current at the AMS1117 current limit (max 1.5 A)', ilim_ldo, v, '<=', 'A', s,
            severity='protection', advisory=True, detail='until the AMS1117 thermal shutdown (~5 W in SOT-223); IFSM 25 A so survivable for seconds')
    # ------------------------------------------------------------------ TEC output short
    v, s = L('g2rl_contact_a')
    i_tec = L('dps5005_iout_max')[0]
    chk.add('tec_short_relay', 'TEC lead short: steady relay contact current (DPS constant-current limit)', i_tec, v, '<=', 'A', s,
            severity='protection', detail='the K1 make onto a short with charged DPS output capacitance is simulated in S06')
    w = copper(flows.tec_paths(ro, i_tec, defrost=False), math.inf, 'TEC short (DPS CC), cooling polarity')
    w2 = copper(flows.tec_paths(ro, i_tec, defrost=True), math.inf, 'TEC short (DPS CC), defrost polarity')
    w = max(w, w2, key=lambda x: x[0])
    chk.add('tec_short_copper', 'TEC short at DPS 5 A: hottest TEC copper (continuous)', w[0], dT_fault, '<=', 'K', s_fault, corner=w[1],
            severity='protection')
    chk.csv('fault_copper.csv', rows)
    chk.add('copper_paths', 'Every fault current path resolves on the routed copper (pads found, no open islands)', len(integrity), 0, '==',
            'paths', 'suite integrity', severity='integrity', detail='; '.join(map(str, integrity))[:600])
    chk.note('Fault currents are bounded by the source limits: brick OCP (GST160A24 class, 105-150 %), each regulator\'s datasheet current limit '
             '(part_models.csv), DPS 5 A CC.')
    chk.note('Clearing times use datasheet maxima; F1 below 135 % of rating may never open (Littelfuse 297 table).')
    chk.note('Track temperatures: nodal solve of each net\'s routed copper (segments split at T-junctions, THT pads join layers) '
             'then the IPC-2152 (Brooks & Adam) external fit per segment; GND is a pour and is not assessed.')
    return chk
