"""S01 - 24 V brick hot-plug into the complete three-card system (ngspice).

Inductive brick lead (1.5 m cord + 0.3 m internal, parameterised), charged brick output capacitor,
contact make at t = 10 us (optionally with one bounce). Sweeps: C1 ESR spread (incl. C1 omitted),
brick output capacitance, lead length/inductance, DPS5005 input capacitance (unknown, assumed range)
and the P6KE30A breakdown spread. Peaks at VMOT (StepStick/TMC2209), at the OKI buck inputs, at the
DPS input, Q1 gate/drain stress, TVS current/energy and fuse I2t.
"""
import itertools

import numpy as np

from d34sim import common, flows, report, spice
from d34sim.circuit import Ctx

TITLE = '24 V brick hot-plug (inductive lead) into the full system'


def run(env):
    chk = report.Checks('s01_hotplug', env.outdir('s01_hotplug'))
    L = env.limit
    esr_cases = [('electrolytic ESR min', 'min'), ('ESR nom', 'nom'), ('ESR max (aged, cold)', 'max'), ('C1 omitted (ESR nom)', None)]
    brick_cases = [('brick 470uF/50mOhm', dict(c_out=470e-6, esr=0.05)), ('brick 2200uF/20mOhm', dict(c_out=2200e-6, esr=0.02))]
    lead_cases = [('lead min, low-loss contacts', dict(length='min', L='min', contact='min')),
                  ('lead max', dict(length='max', L='max', contact='nom'))]
    dps_cases = [('DPS Cin 22uF ceramic-like', (22e-6, 0.005)), ('DPS Cin 100uF', (100e-6, 0.05)), ('DPS Cin 470uF', (470e-6, 0.05))]
    tvs_cases = ['min', 'max']
    if getattr(env, 'quick', False):
        esr_cases, brick_cases, dps_cases = esr_cases[2:], brick_cases[1:], dps_cases[:1]
    rows, worst = [], {}
    N, R = flows.names(env)
    V = lambda k: f'v({N[k]})'
    sk = dict(tvs=f'pwr:{R["tvs"]}:{R["tvs_k"]}', f1=f'pwr:{R["f1"]}:1', f2=f'pwr:{R["f2"]}:1', q=f'pwr:{R["q"]}:{R["qd"]}')
    I = {k: 'i(vsense_' + v.replace(':', '_').lower() + ')' for k, v in sk.items()}
    sense = list(sk.values())
    vecs = [V('vin'), V('v24'), V('aux'), V('vmot'), V('v24dps'), V('q_g'), 'v(ext_dps_in_1,ext_dps_in_2)', V('v12'), V('v5'), V('v3v3')]
    vecs += list(I.values())
    combos = list(itertools.product(esr_cases, brick_cases, lead_cases, dps_cases, tvs_cases))
    combos.append(((('ESR max (aged, cold)', 'max')), brick_cases[-1], lead_cases[1], dps_cases[0], 'max', 'bounce'))
    for k, combo in enumerate(combos):
        (en, esr), (bn, bk), (ln, lc), (dn, (dc, desr)), tvs = combo[:5]
        bounce = [(15e-6, 40e-6)] if len(combo) > 5 else None
        corner = dict(temp_C=40.0, tvs_bv=tvs, **lc)
        def make(nv):
            ctx = Ctx(corner, sense=sense, no_vendor=nv)
            if esr is None:
                ctx.esr_override[f'pwr:{R["bulk"]}'] = None
            else:
                ctx.corner['esr'] = esr
            return common.build(env, ctx, brick=dict(v=24.0 * 1.05, t_close=10e-6, bounce=bounce, **bk),
                                dps_in=dict(c_in=dc, esr=desr, p_load=0.0))
        name = f's01_{k:03d}'
        c, info, r = common.run_robust(make, name, vecs, 'tran 1u 2.5m 0 100n', chk)
        t = r['time']
        vgs = r[V('q_g')] - r[V('v24')]
        vds = r[V('vin')] - r[V('v24')]
        itvs = r[I['tvs']]
        ptvs = r[V('v24')] * np.clip(itvs, 0, None)
        row = dict(case=k, c1=en, brick=bn, lead=ln, dps_cin=dn, tvs_bv=tvs, bounce=bool(bounce),
                   vin_raw_pk=r[V('vin')].max(), v24_pk=r[V('v24')].max(), aux_pk=r[V('aux')].max(), vmot_pk=r[V('vmot')].max(),
                   vdps_in_pk=r['v(ext_dps_in_1,ext_dps_in_2)'].max(),
                   vgs_min=vgs.min(), vgs_max=vgs.max(), vds_abs_pk=np.abs(vds).max(),
                   i_tvs_pk=itvs.max(), e_tvs_J=common.integ(t, ptvs),
                   i_q1_pk=np.abs(r[I['q']]).max(),
                   i_f1_pk=np.abs(r[I['f1']]).max(), f1_i2t=common.i2t(t, r[I['f1']]),
                   i_f2_pk=np.abs(r[I['f2']]).max(),
                   lead_R_mohm=info['BRICK']['R'] * 1e3, lead_L_nH=info['BRICK']['L'] * 2e9,
                   solver=r['_opts'].split()[0] + (' gear' if 'gear' in r['_opts'] else ''), fallback=r['_fallback'])
        rows.append(row)
        for key in ('vmot_pk', 'aux_pk', 'v24_pk', 'vdps_in_pk', 'vds_abs_pk', 'i_tvs_pk', 'e_tvs_J', 'f1_i2t', 'i_q1_pk'):
            if key not in worst or row[key] > worst[key][0][key]:
                worst[key] = (row, r, name)
        if 'vgs' not in worst or row['vgs_min'] < worst['vgs'][0]['vgs_min']:
            worst['vgs'] = (row, r, name)
    chk.csv('hotplug_cases.csv', rows)

    def corner_of(row):
        return f"case {row['case']}: {row['c1']}, {row['brick']}, {row['lead']}, {row['dps_cin']}, TVS BV {row['tvs_bv']}" + (' + bounce' if row['bounce'] else '')
    w = worst['vmot_pk'][0]
    v, s = L('tmc2209_vs_abs_max')
    chk.add('vmot_tmc2209_abs', 'Peak VMOT at the StepStick vs TMC2209 absolute maximum VS', w['vmot_pk'], v, '<=', 'V', s,
            severity='rating', corner=corner_of(w))
    v, s = L('tmc2209_vs_op_max')
    chk.add('vmot_tmc2209_op', 'Peak VMOT vs TMC2209 operating maximum (transient excursion)', w['vmot_pk'], v, '<=', 'V', s,
            severity='rating', corner=corner_of(w), advisory=True)
    v, s = L('a4988_vbb_abs_max')
    chk.add('vmot_a4988_abs', 'Peak VMOT vs A4988 absolute maximum VBB (fallback driver)', w['vmot_pk'], v, '<=', 'V', s, corner=corner_of(w))
    w = worst['aux_pk'][0]
    v, s = L('buck_vin_abs_max')
    chk.add('buck_vin_abs', 'Peak 12 V / 5 V buck input (after the PTC) vs regulator absolute maximum input', w['aux_pk'], v, '<=', 'V', s,
            corner=corner_of(w))
    w = worst['v24_pk'][0]
    v, s = L('elec_cap_v_rated')
    chk.add('c1_vrated', 'Peak +24V (C1/C2) vs capacitor rated voltage', w['v24_pk'], v, '<=', 'V', s, corner=corner_of(w))
    w = worst['vdps_in_pk'][0]
    v, s = L('dps5005_vin_max')
    chk.add('dps_vin', 'Peak voltage at the DPS5005 input terminals', w['vdps_in_pk'], v, '<=', 'V', s, corner=corner_of(w))
    w = worst['vgs'][0]
    v, s = L('irf4905_vgs_max')
    chk.add('q1_vgs', 'Q1 IRF4905 |VGS| during hot-plug (zener-clamped)', max(-w['vgs_min'], w['vgs_max']), v, '<=', 'V', s, corner=corner_of(w))
    w = worst['vds_abs_pk'][0]
    v, s = L('irf4905_vds_max')
    chk.add('q1_vds', 'Q1 |VDS| peak during hot-plug', w['vds_abs_pk'], v, '<=', 'V', s, corner=corner_of(w))
    w = worst['i_q1_pk'][0]
    v, s = L('irf4905_ism')
    chk.add('q1_inrush', 'Q1 peak inrush current (body diode conducts before the gate is enhanced)', w['i_q1_pk'], v, '<=', 'A', s, corner=corner_of(w))
    w = worst['i_tvs_pk'][0]
    v, s = L('p6ke30a_ipp')
    chk.add('tvs_ipp', 'P6KE30A peak current during hot-plug vs IPP', w['i_tvs_pk'], v, '<=', 'A', s, corner=corner_of(w))
    w = worst['e_tvs_J'][0]
    v, s = L('p6ke30a_energy')
    chk.add('tvs_energy', 'P6KE30A absorbed energy per hot-plug vs 10/1000 us rating', w['e_tvs_J'], v, '<=', 'J', s, corner=corner_of(w))
    w = worst['f1_i2t'][0]
    melt, s1 = L('fuse297_7a5_i2t_melt')
    frac, s2 = L('fuse_pulse_i2t_fraction')
    chk.add('f1_i2t', 'F1 7.5 A I2t of the hot-plug inrush vs pulse-derated melting I2t', w['f1_i2t'], melt * frac, '<=', 'A2s',
            f'{s1}; x {frac} ({s2})', corner=corner_of(w))
    # ---------------------------------------------------------------- plots
    for key, title in (('vmot_pk', 'worst VMOT'), ('i_tvs_pk', 'worst TVS current')):
        row, r, name = worst[key]
        t = r['time']
        report.plot(chk.outdir / f'{key}.png', f'S01 hot-plug, {title}: {corner_of(row)}', [
            dict(ylabel='V', traces=[(t, r[V('vin')], 'VIN_RAW (J1)'), (t, r[V('v24')], '+24V (bulk/TVS)'), (t, r[V('aux')], 'buck inputs'),
                                     (t, r[V('vmot')], 'StepStick VMOT'), (t, r['v(ext_dps_in_1,ext_dps_in_2)'], 'DPS input')],
                 hlines=[(L('tmc2209_vs_abs_max')[0], 'TMC2209 abs max'), (L('buck_vin_abs_max')[0], 'buck abs max')]),
            dict(ylabel='A', traces=[(t, r[I['tvs']], 'TVS'), (t, r[I['q']], 'Q1 (inrush)'), (t, r[I['f1']], 'F1 (DPS feed)')]),
            dict(ylabel='V', traces=[(t, r[V('q_g')] - r[V('v24')], 'Q1 VGS')], hlines=[(-20, '-20 V abs max')]),
        ])
        chk.csv(f'{key}_waveform.csv', [dict(t=t[i], vin_raw=r[V('vin')][i], v24=r[V('v24')][i], vmot=r[V('vmot')][i],
                                               i_tvs=r[I['tvs']][i], i_q1=r[I['q']][i])
                                          for i in range(0, len(t), max(1, len(t) // 4000))])
    chk.note('Brick 24 V set to +5 % (25.2 V) as the worst-case regulated output; bucks, DevKit, fans and relays are live models.')
    chk.note(f'{len(combos)} corners; DPS5005 input capacitance is not published: 22 uF ceramic-like to 470 uF electrolytic bracket it (assumption).')
    _ovp_fault(env, chk, vecs, sense, V, I)
    _tvs_method_check(env, chk)
    return chk


def _ovp_fault(env, chk, vecs, sense, V, I):
    """Brick failure up to its own OVP trip level (GST160A24: 105-135 % = 32.4 V max), held for 20 ms."""
    L = env.limit
    vovp, s_ovp = L('brick_ovp_max')
    ilim, _ = L('brick_ocp_max')
    for bv in ('min', 'max'):
        def make(nv):
            ctx = Ctx(dict(temp_C=40.0, tvs_bv=bv, smf_bv=bv), sense=sense, no_vendor=nv)
            return common.build(env, ctx, brick=dict(v=vovp, t_close=10e-6, ilim=ilim, c_out=1000e-6, esr=0.03))
        c, info, r = common.run_robust(make, f's01_ovp_{bv}', vecs, 'tran 10u 20m 0 10u', chk)
        late = r['time'] > 15e-3
        vmot = r[V('vmot')][late].max()
        aux = r[V('aux')][late].max()
        p_tvs = (r[V('v24')] * r[I['tvs']])[late].mean()
        v, s = L('tmc2209_vs_abs_max')
        chk.add(f'ovp_vmot_{bv}', f'Brick fault at its OVP limit {vovp} V (TVS BV {bv}): VMOT vs TMC2209 abs max', vmot, v, '<=', 'V',
                f'{s}; brick {s_ovp}', severity='rating', advisory=True, corner=f'TVS BV {bv}')
        v, s = L('p6ke30a_pd')
        chk.add(f'ovp_tvs_power_{bv}', f'P6KE30A dissipation while the brick sits at {vovp} V (lasts until brick OVP hiccup)', p_tvs, v, '<=', 'W',
                s, severity='rating', advisory=True, corner=f'TVS BV {bv}',
                detail=f'TVS current {r[I["tvs"]][late].mean():.2f} A; duration set by the brick OVP response (not published)')
        v, s = L('buck_vin_abs_max')
        chk.add(f'ovp_buck_{bv}', f'Brick fault at {vovp} V (TVS BV {bv}): buck input vs regulator abs max', aux, v, '<=', 'V', s,
                severity='rating', advisory=True, corner=f'TVS BV {bv}')


def _tvs_method_check(env, chk):
    """Validate the behavioural TVS fitting method on a part that has a manufacturer model:
    fit P6KE27A (Vishay datasheet lines: VBR 25.7-28.4 V @ 1 mA, VC 37.5 V @ 16 A) the same way and
    compare clamp voltages against Vishay's own P6KE27A model at 1, 5 and 14 A."""
    from d34sim.models import VENDOR
    rs = (37.5 - 28.4 - 0.0257 * 9.7) / 16.0
    res = {}
    for tag, dev in (('a', f'.include {VENDOR}/p6ke-proxy-p6ke27a/p6ke27a.txt\nX1 0 n p6ke27a\n'),
                     ('b', f'.model DFIT D(IS=1e-11 N=1.5 RS={rs:.4f} BV=27.05 IBV=1m NBV=1)\nD1 0 n DFIT\n')):
        r = spice.run(f's01_tvsfit_{tag}', dev + 'I1 0 n DC 1\n', ['v(n)'], 'dc I1 1 14 1')
        res[tag] = r['v(n)']
    diag = [(i + 1, res['a'][i], res['b'][i]) for i in range(len(res['a']))]
    err = max(abs(b - a) for _, a, b in diag)
    chk.csv('tvs_fit_validation.csv', [dict(I_A=i, vishay_model_V=a, behavioural_fit_V=b) for i, a, b in diag])
    chk.add('tvs_fit_method', 'Behavioural TVS fit method vs manufacturer model (Vishay P6KE27A, 1-14 A)', err, 1.5, '<=', 'V',
            'model validation (project tolerance 1.5 V)', severity='integrity', advisory=True,
            detail='; '.join(f'{i} A: vendor {a:.2f} V, fit {b:.2f} V' for i, a, b in diag[::4]))
