"""S05 - TEC relay chain: K1 cut-off / K2 reversal coil drive, flyback, thermostat-open, latch RC (ngspice),
and the safety properties of the watchdog + defrost interlock over firmware/supply sequences (python event model).
"""
import itertools

import numpy as np

from d34sim import common, logic, report
from d34sim import models as M_
from d34sim.circuit import Ctx
from d34sim.netlist import spice_node
from d34sim.sched import Schedule

TITLE = 'TEC relays: coil drive, flyback, thermostat loop, watchdog and K2 interlock safety properties'


def pwl(points):
    return 'PWL(' + ' '.join(f'{t:.9g} {v:.6g}' for t, v in points) + ')'


def run(env):
    chk = report.Checks('s05_tec_interlock', env.outdir('s05_tec_interlock'))
    L = env.limit
    P, probs = logic.extract(env)
    chk.add('topology', 'Safety-chain topology read from the netlists matches the modelled structure', len(probs), 0, '==', 'issues',
            'suite integrity (logic.extract)', severity='integrity', detail='; '.join(probs))
    if P is None or probs:
        chk.note('Topology changed: the logic model must be reviewed before its results apply.')
        if P is None:
            return chk
    chk.note(f"Extracted: watchdog R {P['R_wd']:.3g} ohm / C {P['C_wd']:.3g} F; latch R {P['R_le']:.3g} / C {P['C_le']:.3g}; "
             f"GPIO {P['gpio']}; K1 flyback {P.get('k1_flyback_mpn')}")
    _spice_part(env, chk, P)
    _logic_part(env, chk, P)
    return chk


# ============================================================================== SPICE
def _spice_part(env, chk, P):
    L = env.limit
    tec, ctrl = env.cards['tec'], env.cards['ctrl']
    ch = P['chain']
    n = lambda net: spice_node('tec', net).lower()
    nc = lambda net: spice_node('ctrl', net).lower()
    k1, k2 = ch['K1']['relay'], ch['K2']['relay']
    npn = P.get('drive') == 'npn'
    hc = P.get('le_mode') == 'hc123'
    u2, u3 = P['refs']['hc123'], P['refs']['hc573']
    dk = P['refs']['devkit']
    thermo_io = [net for p_, net in ctrl.pins(dk).items() if 'THERMO' in net]
    vec_coil = [f'i(vtec_{k1.lower()}c)', f'i(vtec_{k2.lower()}c)']
    V = dict(k1h=f'v({n(ch["K1"]["coil_hi"])})', k1l=f'v({n(ch["K1"]["coil_lo"])})', k2h=f'v({n(ch["K2"]["coil_hi"])})',
             k2l=f'v({n(ch["K2"]["coil_lo"])})', le=f'v({nc(P["nets"]["le"])})', qb=f'v({nc(P["nets"]["qb"])})')
    sense = []
    d2 = P['le_refs'][1]
    sense.append(f'ctrl:{d2}:{ctrl.pin_by_func(d2, "K")}')
    isd2 = f'i(vsense_ctrl_{d2.lower()}_{ctrl.pin_by_func(d2, "K")})'
    iq = {}
    for kname in ('K1', 'K2'):
        if ch[kname]['driver'] == 'npn':
            q_ = ch[kname]['drv_ref']
            key = f'tec:{q_}:{tec.pin_by_func(q_, "C")}'
            sense.append(key)
            iq[kname] = 'i(vsense_' + key.replace(':', '_').lower() + ')'
    hu = P.get('k2_holdup')
    if hu:
        c1 = hu['refs'][1]
        hold_net = [x for x in tec.pins(c1).values() if x != ch['K2']['coil_hi']][0]
        V['c1'] = f'v({n(ch["K2"]["coil_hi"])},{n(hold_net)})'
    if thermo_io:
        V['th'] = f'v({nc(thermo_io[0])})'
    vecs = list(V.values()) + vec_coil + [isd2] + list(iq.values())
    rows = []
    rel = P['relay']
    i_rated = 12.0 / rel['r_coil']
    T_OFF, T_RE = 100e-3, 420e-3
    for Lc in ('min', 'nom', 'max'):
        on_off_on = pwl([(0, 0), (5e-3, 0), (5.001e-3, 1), (T_OFF, 1), (T_OFF + 1e-6, 0), (T_RE, 0), (T_RE + 1e-6, 1)])
        drive = {f'{u2}.1Q': pwl([(0, 0), (5e-3, 0), (5.001e-3, 1), (T_OFF, 1), (T_OFF + 1e-6, 0)]),
                 f'{u2}.1~{{Q}}': pwl([(0, 1), (5e-3, 1), (5.001e-3, 0), (T_OFF, 0), (T_OFF + 1e-6, 1)]),
                 f'{u3}.Q1': on_off_on}
        if hc:   # half 2: Q-bar high while idle, low for the delay after K1 is commanded off (shortened to 60 ms here)
            e = 5e-9   # CMOS output edge (HC at 3.3 V: ~10 ns)
            drive[f'{u2}.2~{{Q}}'] = pwl([(0, 1), (T_OFF, 1), (T_OFF + e, 0), (T_OFF + 60e-3, 0), (T_OFF + 60e-3 + e, 1)])
            drive[f'{u2}.2Q'] = pwl([(0, 0), (T_OFF, 0), (T_OFF + e, 1), (T_OFF + 60e-3, 1), (T_OFF + 60e-3 + e, 0)])

        def make(nv):
            ctx = Ctx(dict(temp_C=40.0, relay_L=Lc, hc_rout=40.0), no_vendor=nv, logic_drive=drive, sense=sense)
            return common.build(env, ctx, brick=dict(v=24.0, t_close=None))
        c, info, r = common.run_robust(make, f's05_coil_{Lc}', vecs, 'tran 5u 520m 0 20u', chk)
        t = r['time']
        on = (t > T_OFF - 10e-3) & (t < T_OFF)
        i1, i2 = r[vec_coil[0]], r[vec_coil[1]]
        row = dict(L=Lc, v_coil_k1=(r[V['k1h']] - r[V['k1l']])[on].mean(), v_coil_k2=(r[V['k2h']] - r[V['k2l']])[on].mean(),
                   i_k1=i1[on].mean(), i_k2=i2[on].mean(), k1_lo_pk=r[V['k1l']].max(), k2_lo_pk=r[V['k2l']][t < T_RE].max(),
                   t_k1_to_10pct_ms=(common.first_cross(t, i1, 0.10 * i_rated, rising=False, after=T_OFF) - T_OFF) * 1e3,
                   t_k2_to_40pct_ms=(common.first_cross(t, i2, 0.40 * i_rated, rising=False, after=T_OFF) - T_OFF) * 1e3,
                   t_k2_to_10pct_ms=(common.first_cross(t, i2, 0.10 * i_rated, rising=False, after=T_OFF) - T_OFF) * 1e3,
                   i_d2_pk=np.abs(r[isd2]).max(),
                   t_k2_pickup_ms=(common.first_cross(t, i2, 0.70 * i_rated, after=5e-3) - 5e-3) * 1e3,
                   t_k2_repickup_ms=(common.first_cross(t, i2, 0.70 * i_rated, after=T_RE) - T_RE) * 1e3,
                   t_k1_pickup_ms=(common.first_cross(t, i1, 0.70 * i_rated, after=5e-3) - 5e-3) * 1e3)
        for kname, vv in iq.items():
            row[f'i_{kname}_drv_pk'] = np.abs(r[vv]).max()
            if kname == 'K2':
                vce = r[V['k2l']]
                pw = np.abs(r[vv]) * np.maximum(vce, 0)
                dt_ = np.diff(t, prepend=t[0])
                row['q3_p_pk'] = pw.max()
                row['q3_e_mJ'] = float(np.sum((pw * dt_)[(t > 5e-3) & (t < 60e-3)]) * 1e3)
        if 'c1' in V:
            row['c1_min_V'] = r[V['c1']].min()
        if hc:
            row['le_rise_us'] = _le_edge(env, P) * 1e6
        rows.append(row)
        if Lc == 'max':
            report.plot(chk.outdir / 'coils.png', f'S05 coil drive, release and K2 hold-up (L = {rel["L"][2]} H assumed)', [
                dict(ylabel='A', traces=[(t, i1, f'{k1} coil'), (t, i2, f'{k2} coil')],
                     hlines=[(0.7 * i_rated, 'must-operate (70 %)'), (0.1 * i_rated, 'must-release (10 %)')]),
                dict(ylabel='V', traces=[(t, r[V['k1l']], f'{k1} coil low side'), (t, r[V['k2l']], f'{k2} coil low side')] +
                     ([(t, r[V['c1']], 'K2 hold-up capacitor')] if 'c1' in V else [])),
                dict(ylabel='V', traces=[(t, r[V['le']], 'LATCH_EN'), (t, r[V['qb']], '74HC123 1Q-bar')])])
    chk.csv('coil_cases.csv', rows)
    # ---- thermostat opens while K1 is energised
    def make_th(nv):
        ctx = Ctx(dict(temp_C=40.0, relay_L='max'), no_vendor=nv, logic_drive={f'{u2}.1Q': 'DC 1', f'{u2}.1~{{Q}}': 'DC 0', f'{u3}.Q1': 'DC 0'})
        return common.build(env, ctx, brick=dict(v=24.0, t_close=None), thermo=dict(closed=pwl([(0, 1), (30e-3, 1), (30.001e-3, 0)])))
    vth = [V['k1h'], V['k1l'], vec_coil[0]] + ([V['th']] if 'th' in V else [])
    th_temps = {}
    for tc in (25.0, 40.0):    # the clamp diode's VF is highest when cold
        def make_th_t(nv, tc=tc):
            ctx = Ctx(dict(temp_C=tc, relay_L='max'), no_vendor=nv, logic_drive={f'{u2}.1Q': 'DC 1', f'{u2}.1~{{Q}}': 'DC 0', f'{u3}.Q1': 'DC 0'})
            return common.build(env, ctx, brick=dict(v=24.0, t_close=None), thermo=dict(closed=pwl([(0, 1), (30e-3, 1), (30.001e-3, 0)])))
        th_temps[tc] = common.run_robust(make_th_t, f's05_thermo_open_{int(tc)}', vth, 'tran 5u 80m 0 20u', chk)[2]
    rt = min(th_temps.values(), key=lambda r_: r_[V['th']].min() if 'th' in V else 0)
    make_th = make_th_t
    t_th = (common.first_cross(rt['time'], rt[vec_coil[0]], 0.10 * i_rated, rising=False, after=30e-3) - 30e-3) * 1e3
    th_fix = None
    if 'th' in V and rt[V['th']].min() < -0.3:
        th_net = [x for x in tec.nets if x.startswith('THERMO_OK')]
        if th_net:
            def make_fix(nv):
                c_, i_ = make_th(nv)
                c_.add('.model DWHATIF D(IS=3.3e-6 N=1.0 RS=0.06 BV=20 IBV=1m CJO=110p)',
                       f'Dwhatif_th 0 {n(th_net[0])} DWHATIF')
                return c_, i_
            th_fix = common.run_robust(make_fix, 's05_thermo_open_fix', vth, 'tran 5u 80m 0 20u', chk)[2][V['th']].min()
    # ---- checks
    v, s = L('g2rl_must_operate_frac')
    drv_txt = '2N3904 VCE(sat)' if npn else 'ULN2003 VCE(sat)'
    for kk in ('k1', 'k2'):
        vcoil = min(r_[f'v_coil_{kk}'] for r_ in rows)
        r_hot = rel['r_coil'] * 1.10 * (1 + 0.00393 * (40 + 35 - 23))
        chk.add(f'{kk}_pickup_hot', f'{kk.upper()} coil current with a hot coil (40 C bay + 35 K self-heating, +10 % R) vs must-operate current',
                vcoil / r_hot * 1e3, v * i_rated * 1e3, '>=', 'mA', s + ' (pick-up is an ampere-turn threshold: 70 % x 33.3 mA)',
                severity='functional', detail=f'coil voltage {vcoil:.2f} V (12 V rail, {drv_txt}, loop wiring); self-heating 35 K estimated')
    vmax, s = (40.0, 'onsemi 2N3904 VCEO 40 V') if npn else L('uln2003_vce_max')
    chk.add('flyback_k1', f'{k1} coil low side peak at turn-off (clamp) vs driver VCE max', max(r_['k1_lo_pk'] for r_ in rows), vmax, '<=', 'V', s)
    chk.add('flyback_k2', f'{k2} coil low side peak at turn-off vs driver VCE max', max(r_['k2_lo_pk'] for r_ in rows), vmax, '<=', 'V', s)
    if iq:
        v, s = L('q2n3904_ic_max')
        for kname in iq:
            chk.add(f'drv_ic_{kname.lower()}', f'{kname} 2N3904 low side peak collector current (incl. hold-up recharge on re-energise)',
                    max(r_[f'i_{kname}_drv_pk'] for r_ in rows), v, '<=', 'A', s)
    if hu and hu.get('mode') == 'parallel':
        k2p = max(r_['t_k2_pickup_ms'] for r_ in rows)
        k1p = min(r_['t_k1_pickup_ms'] for r_ in rows)
        import json as _j
        FC = _j.loads((env.d34 / 'sim' / 'firmware_contract.json').read_text())
        chk.add('k2_pickup_time', 'K2 coil reaches the 70 % must-operate current after its drive turns on (C1 is charged through Q3 first), '
                'vs the firmware wait before re-arming K1', k2p + 7.0, FC['wait_before_rearm_s'] * 1e3 * 0.5, '<=', 'ms',
                'README contract wait >= 400 ms before re-arming K1; project: coil pick-up + 7 ms travel within half of it', severity='functional',
                advisory=False,
                detail=f"coil current at must-operate after {k2p:.1f} ms (Omron's 15 ms operate time assumes a stiff 12 V coil supply); "
                       f"K1 reaches it in {k1p:.1f} ms; K2 re-pick-up after its hold-up decayed: {max(r_['t_k2_repickup_ms'] for r_ in rows):.1f} ms")
        chk.add('q3_energy', 'Q3 (2N3904) pulse energy while charging C1 at K2 turn-on', max(r_['q3_e_mJ'] for r_ in rows), 20.0, '<=', 'mJ',
                'project screen: TO-92 die/lead-frame thermal mass ~1 mJ/K -> <= ~20 K junction rise (no SOA curve published)',
                severity='rating', advisory=True, detail=f"peak power {max(r_['q3_p_pk'] for r_ in rows):.2f} W (PD 625 mW continuous)")
    if hu:
        v, s = L('elec_cap_reverse_max')
        chk.add('c1_reverse', 'K2 hold-up capacitor: most negative voltage after the hold-up discharges (electrolytic reverse bias)',
                min(r_['c1_min_V'] for r_ in rows), v, '>=', 'V', s, severity='rating')
        k1r = max(r_['t_k1_to_10pct_ms'] for r_ in rows)
        k2h = min(r_['t_k2_to_40pct_ms'] for r_ in rows)
        chk.add('holdup_order_spice', 'Drive removed from both coils at once (SPICE, L corners): K2 coil stays above a 40 % drop-out level longer '
                'than K1 takes to fall to 10 %', k2h - k1r, 10.0, '>=', 'ms', 'safety requirement (K1 opens first) incl. >= 10 ms project margin '
                'for armature travel', severity='safety', detail=f'K1 decays to 10 % in <= {k1r:.1f} ms; K2 stays above 40 % for >= {k2h:.0f} ms')
        k2max = max(r_['t_k2_to_10pct_ms'] for r_ in rows)
        chk.note(f'K2 release delayed by the hold-up: coil above 10 % of rated for up to {k2max:.0f} ms after its drive drops '
                 '(README says ~0.25 s; the contract waits >= 400 ms before re-arming K1).')
    if hc:
        le_r = max(r_['le_rise_us'] for r_ in rows)
        chk.add('le_transition', '74HC573 LE input edge (from 74HC123 half-2 Q-bar through the 1 k series resistor), 10-90 %', le_r * 1e-6,
                L('hc_input_tt_max_3v3')[0], '<=', 's', L('hc_input_tt_max_3v3')[1], severity='rating')
    v, s = L('hc123_iout_abs')
    chk.add('d2_current', '74HC123 1Q-bar output current through the latch-enable clamp diode (worst 40 ohm driver)',
            max(r_['i_d2_pk'] for r_ in rows), v, '<=', 'A', s, severity='rating')
    if 'th' in V:
        chk.add('thermo_open_io', 'Thermostat opens with K1 energised: most negative voltage at the ESP32 THERMO_OK input (25 and 40 C)', rt[V['th']].min(), -0.3,
                '>=', 'V', L('esp32_pin_over')[1] + ' (lower limit -0.3 V)', severity='rating',
                detail=('the K1 coil current freewheels through the diode + zener and drives the thermostat return (and the THERMO_OK divider) '
                        'to about -15 V for a few ms; the ESP32 input clamp conducts through the 1 k series resistor. ' +
                        (f'WHAT-IF Schottky (1N5817-class) from GND to THERMO_OK: {th_fix:.2f} V' if th_fix is not None else '')))
    chk.add('thermo_open_release', 'Thermostat opens with K1 energised: K1 coil current falls to 10 % (must-release)', t_th, 20.0, '<=', 'ms',
            'project (fast firmware-independent cut-off)', severity='safety', detail=f'coil L {rel["L"][2]} H (max assumed)')
    if P.get('uv'):
        _uv_spice(env, chk, P)
    for r_ in rows:
        chk.note(f"L {r_['L']}: K1 coil to 10 % in {r_['t_k1_to_10pct_ms']:.1f} ms; K2 to 40 % in {r_['t_k2_to_40pct_ms']:.1f} ms, "
                 f"to 10 % in {r_['t_k2_to_10pct_ms']:.1f} ms")
    chk.models.setdefault('relay_inductance', f'G2RL coil inductance not published: {rel["L"]} H assumed (min/nom/max)')


def _uv_spice(env, chk, P):
    """12 V undervoltage cut-off: thresholds/hysteresis on a slow ramp (tec card, ideal 12 V) and chatter during load steps
    (full system: DPS load step, blower start, both relays, stepper start)."""
    from d34sim import flows, system
    L = env.limit
    tec = env.cards['tec']
    uv = P['uv']
    n = lambda net: spice_node('tec', net).lower()
    _, j1 = env.harness['leads']['LINK_12V']['b']
    v12n = n(tec.net(j1, '1'))
    k1_on = n(P['chain']['K1'].get('drv_ref') and tec.net(P['chain']['K1']['drv_ref'], tec.pin_by_func(P['chain']['K1']['drv_ref'], 'B')) or 'K1_ON')
    claim = (9.37, 10.31)
    rows = []
    for corner in ('2.44', '2.495', '2.55'):
        def make(nv):
            ctx = Ctx(dict(temp_C=40.0, tl431_vref=float(corner)), no_vendor=nv | {'TL431'})
            c, info = system.build(env.cards, env.harness, ctx, cards_in=('tec',), thermo=dict())
            g_ = c.node('tec', 'GND')
            c.add('* ideal 12 V ramp 12 -> 8 -> 12 V (0.4 s each way) into the VH-3 link pins; K1 driven on',
                  f'V12ramp {v12n} {g_} PWL(0 12 0.05 12 0.45 8 0.5 8 0.9 12)',
                  f'Vk1on {n("K1_ON")} {g_} 3.3')
            return c, info
        c, info, r = common.run_robust(make, f's05_uv_ramp_{corner}', [f'v({v12n})', f'v({n(uv["loop"])})'], 'tran 50u 0.95 0 100u', chk)
        t, v, lp = r['time'], r[f'v({v12n})'], r[f'v({n(uv["loop"])})']
        i_off = np.nonzero((t > 0.05) & (t < 0.5) & (lp < 0.5 * v))[0]
        i_on = np.nonzero((t > 0.5) & (lp > 0.5 * v))[0]
        rows.append(dict(vref=corner, v_trip=float(v[i_off[0]]) if len(i_off) else np.nan, v_rec=float(v[i_on[0]]) if len(i_on) else np.nan))
    chk.csv('uv_thresholds.csv', rows)
    trip = [r_['v_trip'] for r_ in rows]
    rec = [r_['v_rec'] for r_ in rows]
    lo, hi = claim[0] - 0.25, claim[0] + 0.25
    det = (f"trip {min(trip):.2f}-{max(trip):.2f} V, recover {min(rec):.2f}-{max(rec):.2f} V (claim {claim[0]} / {claim[1]} +-0.2 V); "
           f"analytic nominal {uv['v_trip']:.2f} / {uv['v_rec']:.2f} V")
    chk.add('uv_trip_lo', f'UV cut-off trip threshold, lowest over TL431 Vref corners (SPICE ramp) vs claim {claim[0]} - 0.2 V', min(trip), lo, '>=',
            'V', 'README D34 claim (+-0.2 V) + 0.05 V model allowance', severity='functional', detail=det)
    chk.add('uv_trip_hi', f'UV cut-off trip threshold, highest over Vref corners vs claim {claim[0]} + 0.2 V', max(trip), hi, '<=', 'V',
            'README D34 claim', severity='functional', detail=det)
    chk.add('uv_hysteresis', 'UV cut-off hysteresis (recover - trip), minimum over corners', min(b - a for a, b in zip(trip, rec)), 0.5, '>=', 'V',
            'project: >= 0.5 V hysteresis against 12 V ripple/load steps', severity='functional')
    # ---- chatter: full system, everything starts at once while running from the brick
    from d34sim import common as C_
    N, R = flows.names(env)
    ro = flows.Roles(env)
    u2, u3 = P['refs']['hc123'], P['refs']['hc573']
    dk = ro.model_refs('ctrl', 'devkit')[0]
    io_of = {net: env.cards['ctrl'].pin_func[(dk, p_)] for p_, net in env.cards['ctrl'].pins(dk).items()}
    gp = {}
    for fr in ro.model_refs('tec', 'nmos'):
        g_net = tec.net(fr, tec.pin_by_func(fr, 'G'))
        if g_net in io_of:
            gp[io_of[g_net]] = 'PWL(0 0 20m 0 20.001m 1)'
    worst = None
    for brick_v, label in ((24.0 * 0.97, 'brick -3 %'), (24.0, 'brick nominal')):
        def make2(nv):
            ctx = Ctx(dict(temp_C=40.0, length='max', contact='max'), no_vendor=nv, gpio=gp, stepper='PWL(0 0 20m 0 20.01m 2.0)',
                      logic_drive={f'{u2}.1Q': 'PWL(0 0 20m 0 20.001m 1)', f'{u2}.1~{{Q}}': 'PWL(0 1 20m 1 20.001m 0)',
                                   f'{u3}.Q1': 'PWL(0 0 20m 0 20.001m 1)'})
            return C_.build(env, ctx, brick=dict(v=brick_v, t_close=None),
                            dps_in=dict(c_in=470e-6, esr=0.05, p_load=112.0, t_on=20e-3),
                            fans={'FAN1': dict(i_run=0.14), 'FAN2': dict(i_run=0.12, c_in=4.7e-6, pwm_pullup_v=0.0)})
        c, info, r = C_.run_robust(make2, f's05_uv_chatter_{int(brick_v * 10)}', [f'v({N["v12tec"]})', f'v({n(uv["loop"])})'],
                                    'tran 5u 120m 0 10u', chk)
        t = r['time']
        m = t > 15e-3
        v12min = float(r[f'v({N["v12tec"]})'][m].min())
        loop = r[f'v({n(uv["loop"])})'][m]
        drops = int(np.sum((loop[:-1] > 6) & (loop[1:] <= 6)))
        if worst is None or v12min < worst[0]:
            worst = (v12min, drops, label)
    # ---- slow aux-PTC trip with defrost running (K1 and K2 energised, DPS loaded): who releases first (SPICE, worst L corner)
    i_rated = 12.0 / P['relay']['r_coil']
    k1, k2 = P['chain']['K1']['relay'], P['chain']['K2']['relay']
    ptc_rows = []
    for t_ramp in (0.05, 0.5, 2.0):
        for Lc, vref in (('max', '2.44'), ('min', '2.55')):
            def make3(nv):
                ctx = Ctx(dict(temp_C=40.0, relay_L=Lc, tl431_vref=float(vref)), no_vendor=nv | {'TL431'},
                          logic_drive={f'{u2}.1Q': 'DC 1', f'{u2}.1~{{Q}}': 'DC 0', f'{u3}.Q1': 'DC 1'})
                c_, i_ = C_.build(env, ctx, brick=dict(v=24.0, t_close=None), exclude=(f'pwr:{R["f2"]}',),
                                  dps_in=dict(c_in=470e-6, esr=0.05, p_load=112.0, t_on=5e-3))   # load after the OP (avoids the collapsed CPL solution)
                c_.add(f'* aux PTC trip: 0.2 ohm -> 2 kohm (log-linear) over {t_ramp * 1e3:.0f} ms from t = 50 ms',
                       f'Bptc {N["v24"]} {N["aux"]} I=V({N["v24"]},{N["aux"]})/(0.2*pow(10,4*min(max((time-0.05)/{t_ramp},0),1)))')
                return c_, i_
            vv = [f'i(vtec_{k1.lower()}c)', f'i(vtec_{k2.lower()}c)', f'v({N["v12tec"]})']
            c, info, r = C_.run_robust(make3, f's05_ptc_trip_{int(t_ramp * 1e3)}_{Lc}', vv, f'tran 20u {0.06 + 1.6 * t_ramp} 0 100u', chk)
            t = r['time']
            v_pre = float(np.interp(0.045, t, r[vv[2]]))
            if v_pre < 11.0:
                raise RuntimeError(f'PTC-trip race {t_ramp} s / L {Lc}: system not powered before the trip (12 V = {v_pre:.2f} V at 45 ms)')
            t1 = C_.first_cross(t, r[vv[0]], 0.10 * i_rated, rising=False, after=0.05)
            t2 = C_.first_cross(t, r[vv[1]], 0.40 * i_rated, rising=False, after=0.05)
            ptc_rows.append(dict(ramp_s=t_ramp, L=Lc, vref=vref, t_k1_10pct=t1, t_k2_40pct=t2, margin_ms=(t2 - t1) * 1e3,
                                 v12_at_k1=float(np.interp(t1, t, r[vv[2]])) if np.isfinite(t1) else np.nan))
    chk.csv('ptc_trip_race.csv', ptc_rows)
    wm = min(ptc_rows, key=lambda x: x['margin_ms'] if np.isfinite(x['margin_ms']) else 1e9)
    chk.add('ptc_trip_order', 'Slow aux-PTC trip during defrost (SPICE, 50 ms / 0.5 s / 2 s resistance ramps, relay L and TL431 Vref corners): '
            'K2 coil stays above a 40 % drop-out until K1 has fallen below 10 %, with armature-travel margin', wm['margin_ms'], 10.0, '>=', 'ms',
            'safety requirement (K1 opens first) + 10 ms project margin', severity='safety',
            corner=f"ramp {wm['ramp_s']} s, L {wm['L']}, Vref {wm['vref']}", detail=f"K1 drops at 12 V = {wm['v12_at_k1']:.2f} V")
    chk.add('uv_chatter_margin', 'Normal start-up load step (DPS 112 W, blower, both relays, stepper 2 A at once): lowest 12 V at the tec card vs the '
            'highest UV trip point', worst[0], max(trip) + 0.5, '>=', 'V', 'project: >= 0.5 V above the worst trip point (no nuisance cut-off)',
            severity='functional', corner=worst[2], detail=f'UV feed dropped {worst[1]} times')


def _le_edge(env, P):
    """LE rising edge: 74HC123 half-2 Q-bar (10 ns CMOS edge, 40 ohm) through the series resistor into the LE pin (3.5 pF) and the
    reverse-biased clamp diode (manufacturer model), with 1Q-bar high. Values from the netlist."""
    from d34sim import spice
    from d34sim.models import Registry, match
    ctrl = env.cards['ctrl']
    rs, dref, _ = P['le_refs']
    rval = M_.parse_value(ctrl.comps[rs]['value'])
    reg = Registry()
    row = match(env.table, ctrl.comps[dref])
    name, pins, kind, prov = reg.vendor_or_fallback(row['params']['vendor'], row['params']['fallback'])
    dline = f'X1 lenode rawnode {name}' if kind == 'subckt' else f'D1 lenode rawnode {name}'
    net = (reg.text() + f'\nVq q0 0 PWL(0 0 1u 0 1.005u 3.3)\nRout q0 qnode 40\nRser qnode lenode {rval}\nCle lenode 0 3.5p\n'
           f'Vraw rawnode 0 3.3\n{dline}\n')
    r = spice.run('s05_le_edge', net, ['v(lenode)'], 'tran 0.5n 3u 0 1n')
    return _rise(r['time'], r['v(lenode)'], 0.33, 2.97)


def _rise(t, v, lo, hi):
    a = np.nonzero(v >= lo)[0]
    b = np.nonzero(v >= hi)[0]
    return float(t[b[0]] - t[a[0]]) if len(a) and len(b) else float('nan')


# ============================================================================== python event model
CORNER_A = dict(vt_le='worst', L='worst', irel1='worst', tm_rel1='worst', L2='worst', iop2='worst', tm_op2='worst')   # latch opens early, K1 slow to open, K2 fast
CORNER_B = dict(L2='slow', iop2='slow', tm_op2='slow')                                                                  # K2 slow to transfer (re-arm race)


def _logic_part(env, chk, P):
    L = env.limit
    rng = np.random.default_rng(env.seed)
    quick = getattr(env, 'quick', False)
    rows = []
    tw_kick = 0.1   # kick period used for compliant firmware: rising edges at 10 Hz (README D34-3 requires >= 10 Hz)

    # ---------------------------------------------------------------- (1) firmware contract (README D34-3), entry and exit
    # DPS off; TEC_EN low; wait >= 0.8 s; change DEFROST_REQ; wait >= 400 ms; re-arm (TEC_EN + kicks at >= 10 Hz);
    # wait >= 50 ms; DPS on. Waits sampled from the minimum up to +25 %.
    n = 300 if quick else 2000
    entry = rng.random(n) < 0.5
    sc = Schedule(n, init=dict(en=1, wdt=0, dfr=0, dps=1, thermo=1))
    for i in range(n):
        t_off = 0.3
        sc.kicks(i, 0.0, t_off, tw_kick)
        sc.set(i, t_off - 0.01, 'dps', 0)
        sc.set(i, t_off, 'en', 0)
        t_d = t_off + rng.uniform(0.8, 1.0)
        sc.set(i, 0.0, 'dfr', 0 if entry[i] else 1)
        sc.set(i, t_d, 'dfr', 1 if entry[i] else 0)
        t_arm = t_d + rng.uniform(0.4, 0.5)
        sc.set(i, t_arm, 'en', 1)
        sc.kicks(i, t_arm, 2.8, tw_kick)
        sc.set(i, t_arm + rng.uniform(0.05, 0.08), 'dps', 1)
    S = logic.Sample(P, n, rng)
    o = logic.simulate(P, S, sc.compile(), n, 2.8, steady=dict(en=1, dfr=(~entry).astype(int)))
    rows.append(_summ('contract defrost entry/exit (README D34-3 waits)', o, n))
    chk.add('contract_interlock', 'Firmware-contract defrost entries and exits: the K2 command changes while K1 contacts are closed',
            int((o['k2_cmd_k1_closed'] > 0).sum()), 0, '==', f'of {n}', 'safety requirement: K2 switches only with K1 open', severity='safety')
    chk.add('contract_rearm_race', 'Firmware-contract defrost entries and exits: K1 and K2 contacts in motion together',
            int(((o['k1_make_k2_moving'] > 0) | (o['k2_start_k1_closed'] > 0)).sum()), 0, '==', f'of {n}',
            'safety requirement: K2 settled before K1 makes', severity='safety',
            detail=f"{int((o['k1_make_k2_moving_dps'] > 0).sum())} with the DPS output on")
    chk.add('contract_rearm', 'Firmware contract: K1 re-closes after the defrost change', int((o['k1_closures'] >= 1).sum()), n, '==', 'instances',
            'functional (K1 must re-arm)', severity='functional')
    chk.add('contract_k2_follows', 'Firmware contract: K2 follows DEFROST_REQ before K1 re-arms (latch transparent within the 0.8 s wait)',
            int((o['k2_cmd_changes'] >= 1).sum()), n, '==', 'instances', 'functional (README: latch delay max 0.65 s < 0.8 s wait)',
            severity='functional')
    # ---------------------------------------------------------------- (2) exhaustive event orderings
    gaps = [0.0, 0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0]
    combos = list(itertools.product(itertools.permutations(('off', 'dfr', 'on')), gaps, gaps, (0, 1), (1, 0)))
    if quick:
        combos = combos[::3]
    n = len(combos)
    for cname, corner in (('corner A', CORNER_A), ('corner B', CORNER_B), ('random', None)):
        sc = Schedule(n, init=dict(en=1, wdt=0, dfr=0, dps=1, thermo=1))
        dfr0 = np.array([1 - c[4] for c in combos])
        for i, (order, g1, g2, dps_off, to) in enumerate(combos):
            t = 0.3
            sc.kicks(i, 0.0, 0.3, tw_kick)
            sc.set(i, 0.0, 'dfr', 1 - to)
            if dps_off:
                sc.set(i, 0.29, 'dps', 0)
            for ev, gap in zip(order, (0.0, g1, g2)):
                t += gap
                if ev == 'off':
                    sc.set(i, t, 'en', 0)
                    sc.set(i, t, 'wdt', 0)
                elif ev == 'dfr':
                    sc.set(i, t, 'dfr', to)
                else:
                    sc.set(i, t, 'en', 1)
                    sc.kicks(i, t, 3.4, tw_kick)
        S = logic.Sample(P, n, np.random.default_rng(env.seed + 1), corner=corner)
        o = logic.simulate(P, S, sc.compile(), n, 3.4, steady=dict(en=1, dfr=dfr0))
        rows.append(_summ(f'exhaustive orderings ({cname})', o, n))
        bad = o['k2_cmd_k1_closed'] > 0
        chk.add(f'enum_interlock_{cname.replace(" ", "")}', f'All {n} orderings of TEC_EN-off / DEFROST change (entry and exit) / re-arm, 0-1 s gaps, '
                f'DPS on or off, {cname}: the K2 command changes while K1 is closed (hardware interlock)', int(bad.sum()), 0, '==', f'of {n}',
                'safety requirement: the latch only follows DEFROST_REQ after K1 has opened', severity='safety', corner=_cdesc(cname),
                detail=f'examples: {[combos[i] for i in np.nonzero(bad)[0][:4]]}')
        bad2 = (o['k1_make_k2_moving'] > 0) | (o['k2_start_k1_closed'] > 0)
        rearm_ok = [g for g in gaps if not any(bad2[i] for i, c in enumerate(combos) if c[0] == ('off', 'dfr', 'on') and c[2] >= g)]
        chk.add(f'enum_rearm_{cname.replace(" ", "")}', f'Same orderings, {cname}: K1 and K2 contacts in motion together (re-arm before K2 has '
                'transferred) - firmware-contract dependent', int(bad2.sum()), 0, '==', f'of {n}',
                'safety requirement; the hardware does not enforce it (README contract waits >= 400 ms)', severity='safety', advisory=True,
                corner=_cdesc(cname), detail=f"{int((o['k1_make_k2_moving_dps'] > 0).sum())} with DPS on; for order off->dfr->on a re-arm gap "
                                              f">= {min(rearm_ok) * 1e3 if rearm_ok else float('nan'):.0f} ms avoids it")
    # ---------------------------------------------------------------- (3) stuck pins, resets, brown-outs, random telegraph
    n = 1000 if quick else 6000
    sc = Schedule(n, init=dict(en=2, wdt=2, dfr=2, dps=1, thermo=1))
    labels = []
    for i in range(n):
        kind = str(rng.choice(['stuck', 'telegraph', 'reset', 'brownout', 'thermo', 'pwm_hung']))
        labels.append(kind)
        sc.set(i, 0.0, 'boot', 1)
        sc.set(i, 0.12, 'boot', 0)            # ROM boot / strapping: GPIO32/33/25 are inputs (Z) -> pulled low
        t = 0.12
        win = (np.inf, np.inf)
        if kind == 'reset':
            win = (rng.uniform(0.3, 2.0), 0.0)
            win = (win[0], win[0] + rng.uniform(0.001, 0.4))
        if kind == 'stuck':
            for p in ('en', 'wdt', 'dfr'):
                sc.set(i, t, p, int(rng.integers(0, 3)))
        elif kind == 'brownout':
            # compliant firmware running (TEC on, defrost on or off), then a 3V3 dip to 0-2.4 V for 5-300 ms
            # The dip takes 3V3 below the ESP32 brown-out level, so the ESP32 resets: its pins go high-impedance for the dip plus a
            # 0.1-0.3 s boot, then the firmware re-runs the contract from boot (DEFROST_REQ, wait >= 0.8 + 0.4 s, re-arm).
            dfr0 = int(rng.integers(0, 2))
            sc.set(i, t, 'dfr', dfr0)
            sc.set(i, t + 0.9, 'en', 1)
            t0 = rng.uniform(1.2, 2.0)
            t1 = t0 + rng.uniform(0.005, 0.3)
            sc.kicks(i, t + 0.9, t0, tw_kick)
            sc.v33[i].append((t0, t1, rng.uniform(0.0, 2.4)))
            for p_ in ('en', 'wdt', 'dfr'):
                sc.set(i, t0, p_, 2)
            tb = t1 + rng.uniform(0.1, 0.3)
            sc.set(i, t0, 'boot', 1)
            sc.set(i, tb, 'boot', 0)
            sc.set(i, tb, 'dfr', int(rng.integers(0, 2)))
            ta = tb + rng.uniform(1.2, 1.4)
            sc.set(i, ta, 'en', 1)
            sc.kicks(i, ta, 4.0, tw_kick)
        elif kind in ('telegraph', 'reset', 'thermo'):
            while t < 2.4:
                p = str(rng.choice(['en', 'wdt', 'dfr'], p=[0.3, 0.5, 0.2]))
                if not (win[0] <= t < win[1]):
                    sc.set(i, t, p, int(rng.integers(0, 3)))
                t += float(np.exp(rng.uniform(np.log(0.001), np.log(0.4))))
            if kind == 'reset':
                for p in ('en', 'wdt', 'dfr'):
                    sc.set(i, win[0], p, 2)
                sc.set(i, win[0], 'boot', 1)
                sc.set(i, win[1], 'boot', 0)
            if kind == 'thermo':
                t0 = rng.uniform(0.3, 1.8)
                sc.set(i, t0, 'thermo', 0)
                sc.set(i, t0 + rng.uniform(0.01, 0.5), 'thermo', 1)
        elif kind == 'pwm_hung':                # CPU hung while a hardware PWM keeps toggling WDT_KICK
            sc.set(i, t, 'en', 1)
            sc.kicks(i, t, 2.5, 0.004)
        if rng.random() < 0.3:
            sc.set(i, rng.uniform(0.2, 2.4), 'dps', 0)
    S = logic.Sample(P, n, np.random.default_rng(env.seed + 2))
    o = logic.simulate(P, S, sc.compile(), n, 4.0)
    labels = np.array(labels)
    for kind in sorted(set(labels)):
        m = labels == kind
        rows.append(_summ(f'random: {kind}', {k: (v[m] if isinstance(v, np.ndarray) and v.shape == (n,) else v) for k, v in o.items()}, int(m.sum())))
    tw_max = float(S.tw.max())
    bound = tw_max + 0.05
    nk = labels != 'pwm_hung'
    chk.add('cutoff_after_trigger', 'K1 never stays closed longer than the watchdog timeout + release after the last 74HC123 trigger '
            '(stuck / random / reset / brown-out / thermostat patterns)', float(o['max_k1_after_trig'][nk].max()), bound, '<=', 's',
            f'safety requirement; bound = sampled tw max {tw_max:.2f} s + 50 ms release', severity='safety')
    clr = nk & (o['max_k1_after_kick'] > bound)
    chk.add('cutoff_clr_retrigger', 'K1 held on without WDT_KICK edges, by TEC_EN rising edges while WDT_KICK is high (74HC123 CLR-trigger)',
            int(clr.sum()), 0, '==', 'instances', 'documented 74HC123 behaviour (TI/Nexperia: rising CLR triggers when B is high); '
            'firmware must not pulse TEC_EN as a keep-alive', severity='functional', advisory=True,
            detail=f'longest K1 closure after the last WDT edge: {float(o["max_k1_after_kick"][nk].max()):.2f} s')
    chk.add('cutoff_after_en_low', 'K1 opens within 50 ms after TEC_EN goes low (all random patterns)',
            float(o['max_k1_after_en_low'].max()) * 1e3, 50.0, '<=', 'ms', 'safety requirement (project bound incl. diode-slowed release)',
            severity='safety')
    chk.add('cutoff_boot', 'K1 never closes while the ESP32 is in reset / ROM boot (GPIOs high-impedance)', int((o['k1_closed_boot'] > 0).sum()), 0,
            '==', 'instances', 'safety requirement', severity='safety')
    chk.add('cutoff_thermo', 'K1 is open within 100 ms of any thermostat opening', int((o['k1_closed_thermo_open'] > 0).sum()), 0, '==',
            'instances', 'safety requirement (firmware-independent cut-off)', severity='safety')
    m = nk & (labels != 'brownout')
    chk.add('random_interlock', 'Random / stuck / reset / thermostat pin patterns: the K2 command changes while K1 is closed',
            int((o['k2_cmd_k1_closed'][m] > 0).sum()), 0, '==', f'of {int(m.sum())}', 'safety requirement', severity='safety')
    chk.add('random_rearm', 'Random pin patterns: K1 and K2 contacts in motion together (fast TEC_EN/DEFROST_REQ activity)',
            int(((o['k1_make_k2_moving'][m] > 0) | (o['k2_start_k1_closed'][m] > 0)).sum()), 0, '==', f'of {int(m.sum())}', 'safety requirement (not enforced by hardware)',
            severity='safety', advisory=True)
    b = labels == 'brownout'
    chk.add('brownout_interlock', '3V3 brown-outs (to 0-2.4 V, 5-300 ms; ESP32 resets and re-runs the contract from boot) during cooling or '
            'defrost: K2 contacts move while K1 is closed',
            int((o['k2_start_k1_closed'][b] > 0).sum()), 0, '==', f'of {int(b.sum())}', 'safety requirement', severity='safety',
            detail='default model: half 2 starts its delay at power-up (CLR-trigger rule)')
    # sensitivity: no 74HC123 half-2 pulse at power-up (behaviour not specified by Toshiba)
    P2 = dict(P, no_powerup_pulse=True)
    o2 = logic.simulate(P2, logic.Sample(P2, n, np.random.default_rng(env.seed + 2)), sc.compile(), n, 4.0)
    chk.add('brownout_interlock_nopulse', 'Sensitivity: same brown-outs if the 74HC123 half 2 gives no pulse at power-up (latch transparent at once)',
            int((o2['k2_start_k1_closed'][b] > 0).sum()), 0, '==', f'of {int(b.sum())}', 'safety requirement', severity='safety', advisory=True,
            detail='latch content is undefined at power-up; the ESP32 resets and re-runs the contract from boot')
    hung = labels == 'pwm_hung'
    chk.add('pwm_hung_limitation', 'CPU hung but a hardware PWM/LEDC keeps toggling WDT_KICK: K1 stays closed (watchdog cannot see it)',
            int((o['k1_closures'][hung] > 0).sum()), int(hung.sum()), '==', 'instances',
            'documents a limitation: kick WDT_KICK from the control loop in software, never from LEDC/RMT/timer hardware', severity='functional',
            advisory=True)
    # ---------------------------------------------------------------- (4) supply-loss races during defrost (K2 energised, DPS on)
    n = 600 if quick else 6000
    taus = []
    kinds = []
    sc = Schedule(n, init=dict(en=1, wdt=0, dfr=1, dps=1, thermo=1))
    for i in range(n):
        sc.kicks(i, 0.0, 2.5, tw_kick)
        kind = str(rng.choice(['12V lost', '3V3 lost', 'aux lost (12 V and 3V3)']))
        kinds.append(kind)
        t0 = 0.5
        tau = float(np.exp(rng.uniform(np.log(0.001), np.log(2.0))))   # 1 ms (short/hiccup) .. 2 s (slow PTC trip)
        taus.append(tau if kind != '3V3 lost' else np.nan)
        if kind in ('12V lost', 'aux lost (12 V and 3V3)'):
            sc.v12[i].append((t0, tau))
        if kind in ('3V3 lost', 'aux lost (12 V and 3V3)'):
            sc.v33[i].append((t0 + (rng.uniform(0, 0.05) if kind.startswith('aux') else 0), 99.0, 0.0))
    taus = np.array(taus)
    for cname, corner in (('random', None), ('drop-out worst (K1 10 %, K2 40 %, C1 -20 %)', dict(irel1='worst', irel2='worst', L='worst', c_hold='min'))):
        S = logic.Sample(P, n, np.random.default_rng(env.seed + 3), corner=corner)
        o = logic.simulate(P, S, sc.compile(), n, 2.5, steady=dict(en=1, dfr=1))
        kk = np.array(kinds)
        for kind in sorted(set(kinds)):
            m = kk == kind
            k = int((o['k2_start_k1_closed_dps'][m] > 0).sum())
            rows.append(dict(family=f'supply loss during defrost ({cname}): {kind}', instances=int(m.sum()), k2_under_k1_dps=k))
            det = f'{k} of {int(m.sum())}'
            if kind != '3V3 lost':
                bad = m & (o['k2_start_k1_closed_dps'] > 0)
                if bad.any():
                    det += f'; failing 12 V decay time constants {np.nanmin(taus[bad]) * 1e3:.0f}-{np.nanmax(taus[bad]) * 1e3:.0f} ms'
                ok_fast = m & (taus < 0.05)
                det += f'; tau < 50 ms: {int((o["k2_start_k1_closed_dps"][ok_fast] > 0).sum())} of {int(ok_fast.sum())} fail'
            chk.add(f'race_{kind.split()[0].lower()}_{"wc" if corner else "mc"}', f'Defrost running (K2 energised, DPS on), then {kind} '
                    f'(12 V decay tau 1 ms-2 s), {cname}: runs where K2 starts to drop before K1 has opened', k / max(m.sum(), 1), 0.0, '<=',
                    'fraction', 'safety requirement: K2 never switches under load (README: K1 always opens first)', severity='safety', detail=det)
        if corner is not None:
            Pw = dict(P, k1_uv=9.0)
            ow = logic.simulate(Pw, logic.Sample(Pw, n, np.random.default_rng(env.seed + 3), corner=corner), sc.compile(), n, 2.5,
                                steady=dict(en=1, dfr=1))
            kw = int((ow['k2_start_k1_closed_dps'] > 0).sum())
            chk.add('whatif_k1_uv', 'WHAT-IF (not in design): 12 V undervoltage detector (9.0 V) removes K1 drive; all supply-loss runs, drop-out worst',
                    kw / n, 0.0, '<=', 'fraction', 'suggested-fix evaluation', severity='safety', advisory=True, detail=f'{kw} of {n}')
        vcmin = float(np.min(o['vc_min'])) if np.isfinite(o['vc_min']).any() else float('nan')
        if corner is None:
            chk.note(f'K2 hold-up capacitor minimum voltage over the supply-loss runs: {vcmin:.2f} V (event model).')
    chk.csv('logic_families.csv', rows)
    S = logic.Sample(P, 20000, np.random.default_rng(env.seed + 4))
    chk.add('wdt_min_vs_kick', 'Shortest sampled watchdog timeout vs the firmware kick period (rising edges at >= 10 Hz -> 100 ms)', float(S.tw.min()),
            0.1, '>', 's', f"README firmware contract (kick >= 10 Hz); {P['K_source']}; R 1 %, C +-10 %, -5 % bias, +-5 % temp, "
            '+-10 % pin-leakage allowance', severity='functional', detail=f'tw {S.tw.min():.3f}-{S.tw.max():.3f} s; README states 0.32-0.65 s')
    return rows


def _cdesc(c):
    return {'corner A': 'corner A: earliest latch opening (LE threshold 0.94 V), slowest K1 release (L max, drop-out 10 %, 4 ms travel), fastest K2',
            'corner B': 'corner B: slowest K2 transfer (L max, pick-up 70 %, 7 ms travel)',
            'random': 'parameters sampled uniformly over the assumed ranges'}[c]


def _summ(name, o, n):
    return dict(family=name, instances=n, k2_cmd_k1_closed=int((o['k2_cmd_k1_closed'] > 0).sum()), k2_start_k1_closed=int((o['k2_start_k1_closed'] > 0).sum()),
                k2_start_k1_closed_dps=int((o['k2_start_k1_closed_dps'] > 0).sum()),
                k2_moving_while_k1_closed=int((o['k2_move_k1_closed'] > 0).sum()), k1_onto_moving_k2=int((o['k1_make_k2_moving'] > 0).sum()),
                k1_closures=int(o['k1_closures'].sum()), max_k1_after_en_low_ms=float(o['max_k1_after_en_low'].max() * 1e3),
                max_k1_after_trigger_s=float(o['max_k1_after_trig'].max()), max_k1_after_wdt_edge_s=float(o['max_k1_after_kick'].max()))
