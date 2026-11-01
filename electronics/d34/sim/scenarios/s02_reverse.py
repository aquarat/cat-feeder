"""S02 - Reversed brick plug: IRF4905 reverse-polarity FET blocks, leakage, gate/drain stress (ngspice)."""
import numpy as np

from d34sim import common, flows, report
from d34sim.circuit import Ctx

TITLE = 'Reverse-polarity hot-plug: P-FET blocking, leakage, VGS/VDS stress'


def run(env):
    chk = report.Checks('s02_reverse', env.outdir('s02_reverse'))
    L = env.limit
    rows, worst = [], None
    N, R = flows.names(env)
    V = lambda k: f'v({N[k]})'
    sq, st = f'pwr:{R["q"]}:{R["qd"]}', f'pwr:{R["tvs"]}:{R["tvs_k"]}'
    IQ, IT = 'i(vsense_' + sq.replace(':', '_').lower() + ')', 'i(vsense_' + st.replace(':', '_').lower() + ')'
    vecs = [V('vin'), V('v24'), V('aux'), V('vmot'), V('q_g'), V('v12'), V('v5'), V('v3v3'), IQ, IT]
    cases = [(ln, lc, bn, bk) for ln, lc in (('lead min, low-loss', dict(length='min', L='min', contact='min')),
                                             ('lead max', dict(length='max', L='max')))
             for bn, bk in (('brick 470uF/50mOhm', dict(c_out=470e-6, esr=0.05)), ('brick 2200uF/20mOhm', dict(c_out=2200e-6, esr=0.02)))]
    variants = [('as designed', ())]
    pc = env.cards['pwr']
    qg_net = pc.net(R['q'], pc.pin_by_func(R['q'], 'G'))
    qs_net = pc.net(R['q'], pc.pin_by_func(R['q'], 'S'))
    has_cgs = [r for r in pc.comps if r.startswith('C') and set(pc.pins(r).values()) == {qg_net, qs_net}]
    if has_cgs:
        chk.note(f'Q1 gate-source capacitor fitted in the design: {has_cgs} ({pc.comps[has_cgs[0]]["value"]}); no what-if needed.')
    else:
        variants.append(('what-if: 100 nF Q1 gate-source capacitor (suggested fix)', (f'Cwhatif_q1gs {N["q_g"]} {N["v24"]} 100n',)))
    from d34sim import ext as E_
    if E_.externals().get('inlet_snubber'):
        chk.note('Off-board inlet snubber (sim/externals.json) is included in every run at the brick end of the inlet pigtail.')
        variants.append(('what-if: same snubber moved onto J1 (VIN_RAW to GND)', (f'Cwhatif_sn {N["vin"]} sn_x 1u', 'Rwhatif_sn sn_x 0 2.2')))
    else:
        variants.append(('what-if: RC snubber 1 uF + 2.2 ohm from VIN_RAW to GND (suggested fix)',
                         (f'Cwhatif_sn {N["vin"]} sn_x 1u', 'Rwhatif_sn sn_x 0 2.2')))
    for vname, extra in variants:
        for k, (ln, lc, bn, bk) in enumerate(cases):
            def make(nv):
                ctx = Ctx(dict(temp_C=40.0, **lc), sense=[sq, st], no_vendor=nv)
                return common.build(env, ctx, brick=dict(v=25.2, t_close=10e-6, polarity=-1, **bk), extra=extra)
            c, info, r = common.run_robust(make, f's02_{k}{"_fix" if extra else ""}', vecs, 'tran 1u 20m 0 1u', chk)
            t = r['time']
            vds = r[V('vin')] - r[V('v24')]
            vgs = r[V('q_g')] - r[V('v24')]
            iq = np.abs(r[IQ])
            late = t > 15e-3
            dt = np.diff(t, prepend=t[0])
            row = dict(variant=vname, case=k, lead=ln, brick=bn, vds_min=vds.min(), vgs_min=vgs.min(), vgs_max=vgs.max(),
                       v24_min=r[V('v24')].min(), vmot_min=r[V('vmot')].min(), aux_min=r[V('aux')].min(), v12_min=r[V('v12')].min(),
                       v5_min=r[V('v5')].min(), v33_min=r[V('v3v3')].min(),
                       t_rev_cond_us=float(dt[iq > 1.0].sum() * 1e6), t_v24_below_m1_us=float(dt[r[V('v24')] < -1.0].sum() * 1e6),
                       i_leak_ss=iq[late].mean(), i_q1_pk=iq.max(), i_tvs_fwd_pk=-r[IT].min(),
                       fallback=r['_fallback'])
            rows.append(row)
            if extra:
                continue
            if worst is None or row['v24_min'] < worst[0]['v24_min']:
                worst = (row, r)
    chk.csv('reverse_cases.csv', rows)
    w = worst[0]
    corner = f"{w['lead']}, {w['brick']}"
    base = [r_ for r_ in rows if r_['variant'] == 'as designed']
    fix = [r_ for r_ in rows if r_['variant'] != 'as designed']
    v, s = L('irf4905_vds_max')
    chk.add('q1_vds', 'Q1 |VDS| peak when the brick is plugged in reversed (cable ringing into Coss)', max(-r_['vds_min'] for r_ in base), v, '<=', 'V', s)
    v, s = L('irf4905_vgs_max')
    chk.add('q1_vgs', 'Q1 |VGS| during reversed plug-in', max(max(-r_['vgs_min'], r_['vgs_max']) for r_ in base), v, '<=', 'V', s)
    v, s = L('irf4905_idss_150')
    chk.add('q1_leak', 'Steady reverse leakage through Q1 (model at 40 C) vs IDSS max at 150 C', max(r_['i_leak_ss'] for r_ in base), v, '<=', 'A', s)
    chk.add('q1_dvdt_turnon', 'Q1 stays off during a reversed plug-in (peak reverse current through the FET)',
            max(r_['i_q1_pk'] for r_ in base), 1.0, '<=', 'A', 'functional requirement: reverse FET must block (project limit 1 A)',
            severity='functional', corner=corner,
            detail=f"Cgd couples the -24 V drain step onto the gate (VGS down to {min(r_['vgs_min'] for r_ in base):.1f} V): the FET conducts "
                   f"for {max(r_['t_rev_cond_us'] for r_ in base):.0f} us; the P6KE30A then conducts forward ({max(r_['i_tvs_fwd_pk'] for r_ in base):.0f} A pk)")
    v, s = L('elec_cap_reverse_max')
    vmin = min(min(r_['v24_min'], r_['vmot_min'], r_['aux_min'], r_['v12_min'], r_['v5_min'], r_['v33_min']) for r_ in base)
    chk.add('rails_reverse', 'Most negative board rail (+24V, VMOT, 12 V, 5 V, 3V3) during reversed plug-in', vmin, v, '>=', 'V', s,
            corner=corner, detail=f"+24V below -1 V for {max(r_['t_v24_below_m1_us'] for r_ in base):.0f} us")
    chk.add('vmot_reverse_tmc', 'Most negative StepStick VMOT during reversed plug-in vs TMC2209 VS abs min -0.5 V', min(r_['vmot_min'] for r_ in base),
            -0.5, '>=', 'V', 'ADI TMC2209 abs max VS -0.5 V (lower limit)', corner=corner)
    chk.add('aux_reverse', 'Most negative 12 V / 5 V regulator input (after the PTC) during reversed plug-in', min(r_['aux_min'] for r_ in base),
            -0.5, '>=', 'V', 'TRACO TSR: no reverse rating published; project -0.5 V (one diode drop)', corner=corner, advisory=True,
            detail=f"duration below -0.5 V not computed; +24V minimum {min(r_['v24_min'] for r_ in base):.2f} V")
    sn = [r_ for r_ in rows if 'snubber' in r_['variant']]
    if sn:
        chk.add('whatif_snubber_vds', f"WHAT-IF ({sn[0]['variant']}): Q1 |VDS| peak on a reversed plug-in", max(-r_['vds_min'] for r_ in sn),
                L('irf4905_vds_max')[0], '<=', 'V', 'suggested-fix verification', advisory=True)
    fix = [r_ for r_ in fix if 'snubber' not in r_['variant']]
    if fix:
        chk.add('whatif_fix_blocks', 'WHAT-IF (not in design): with 100 nF gate-source on Q1, peak reverse FET current',
                max(r_['i_q1_pk'] for r_ in fix), 1.0, '<=', 'A', 'suggested-fix verification', severity='functional', advisory=True,
                detail=f"most negative rail {min(min(r_['v24_min'], r_['aux_min']) for r_ in fix):.2f} V")
    r = worst[1]
    t = r['time']
    report.plot(chk.outdir / 'reverse_worst.png', f'S02 reversed brick, {corner}', [
        dict(ylabel='V', traces=[(t, r[V('vin')], 'VIN_RAW (Q1 drain)'), (t, r[V('v24')], '+24V (Q1 source)'),
                                 (t, r[V('q_g')], 'Q1 gate')], hlines=[(-55, '-55 V VDSS')]),
        dict(ylabel='A', traces=[(t, r[IQ], 'Q1 drain current'), (t, r[IT], 'TVS (neg = forward)')])],
        xscale=1e3)
    chk.csv('reverse_worst_waveform.csv', [dict(t=t[i], vin_raw=r[V('vin')][i], v24=r[V('v24')][i], vg=r[V('q_g')][i],
                                                 i_q1=r[IQ][i]) for i in range(0, len(t), max(1, len(t) // 3000))])
    chk.note('Brick 25.2 V (+5 %) reversed at the Mini-Fit; the board side is otherwise unpowered (no USB on the DevKit).')
    chk.note('Not modelled: a USB cable to an earthed PC while an earthed-negative brick is reversed (outside the D34 netlist).')
    return chk
