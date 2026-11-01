"""S06 - DPS5005 output through K1/K2 into the 2S2P TARK array (ngspice).

Steady cooling and pull-down currents (string balance, connector pins, relay contacts), K1 make onto the array
with the DPS output capacitor charged to its CV setpoint, K1 make onto a shorted TEC lead, defrost with Seebeck
EMF aiding the drive, and the K1 open-contact voltage after a break. The DPS input inrush through F1 is in S01;
K2 switching under load is covered by the S05 interlock analysis.
"""
import numpy as np

from d34sim import common, ext, flows, logic, report
from d34sim.circuit import Ctx

TITLE = 'DPS5005 into the 2S2P TEC array through K1/K2: steady, pull-down, make/break and defrost'


def pwl(points):
    return 'PWL(' + ' '.join(f'{t:.9g} {v:.6g}' for t, v in points) + ')'


def run(env):
    chk = report.Checks('s06_dps_tec', env.outdir('s06_dps_tec'))
    L = env.limit
    P, probs = logic.extract(env)
    ro = flows.Roles(env)
    R = ro.relays()
    tec = env.cards['tec']
    k1, k2, jo, jt = R['k1'], R['k2'], R['jo'], R['jt']
    tp = ext.tec_params()
    alpha = tp['alpha_V_K']
    u2, u3 = P['refs']['hc123'], P['refs']['hc573']
    sense = [f'tec:{k1}:21', f'tec:{k2}:11', f'tec:{k2}:21']

    def I(key):
        card, ref, pin = key.split(':')
        if ref == jo:
            return f'ldps_out_{pin}#branch'      # current in the lead conductor of that connector pin
        if ref == jt:
            return f'ltec_{pin}#branch'
        return 'i(vsense_' + key.replace(':', '_').lower() + ')'
    vecs = [I(k) for k in sense] + [I(f'tec:{jo}:{p}') for p in '123456'] + [I(f'tec:{jt}:{p}') for p in '1234']
    vecs += ['v(dpso_p,dpso_n)', 'v(ext_tec_1,ext_tec_2)', 'v(ext_tec_3,ext_tec_4)']
    for pin in ('21', '24', '11', '14'):
        vecs.append(f'v({_n(tec, k1, pin)})')
    (i_st, dt_st), (i_pd, dt_pd) = tp['steady'], tp['pulldown']
    cases = [
        # name, vset, ilim, dT, k1 on at, k2 (defrost), dps enable, tec short
        (f'steady cooling {i_st} A (dT {dt_st} K)', 21.0, i_st, dt_st, 0.0, 0, 'DC 1', False),
        (f'pull-down {i_pd} A (dT {dt_pd} K)', 21.0, i_pd, dt_pd, 0.0, 0, 'DC 1', False),
        (f'K1 makes onto array, DPS CV 21 V charged (dT {dt_st} K)', 21.0, 5.0, dt_st, 20e-3, 0, 'DC 1', False),
        (f'defrost: K2 reversed, K1 makes, Seebeck aiding (dT {dt_st} K, CV 12 V)', 12.0, 5.0, dt_st, 20e-3, 1, 'DC 1', False),
        ('K1 makes onto a shorted TEC lead (DPS CV 21 V charged)', 21.0, 5.0, 0.0, 20e-3, 0, 'DC 1', True),
        (f'K1 breaks {i_pd} A pull-down current', 21.0, i_pd, dt_pd, -1.0, 0, 'DC 1', False),
    ]
    rows = []
    res = {}
    for k, (name, vset, ilim, dT, t_on, dfr, en, short) in enumerate(cases):
        if t_on >= 0:
            k1_drive = pwl([(0, 0), (t_on, 0), (t_on + 1e-6, 1)]) if t_on > 0 else 'DC 1'
        else:
            k1_drive = pwl([(0, 1), (30e-3, 1), (30.001e-3, 0)])
        drive = {f'{u2}.1Q': k1_drive, f'{u3}.Q1': f'DC {dfr}'}
        p_in = 0.0

        def make(nv):
            ctx = Ctx(dict(temp_C=40.0, contact='max'), no_vendor=nv, logic_drive=drive, sense=sense)
            c, info = common.build(env, ctx, brick=dict(v=24.0, t_close=None),
                                   dps_in=dict(c_in=470e-6, esr=0.05, p_load=0.0, t_on=0.0),
                                   dps_out=dict(vset=vset, ilim=ilim, c_out=470e-6, esr=0.05, enable=en),
                                   tec=dict(dT=dT, R=tp['R_hot'], alpha=alpha))
            if short:
                c.add('* TEC lead short at the array end', 'Rshort ext_TEC_1 ext_TEC_2 0.01', 'Rshort2 ext_TEC_3 ext_TEC_4 0.01')
            return c, info
        c, info, r = common.run_robust(make, f's06_{k}', vecs, 'tran 5u 80m 0 20u', chk)
        t = r['time']
        late = t > 70e-3 if t_on >= 0 else (t > 20e-3) & (t < 29e-3)
        i_out = sum(r[I(f'tec:{jo}:{p}')] for p in ('1', '2', '3'))
        row = dict(case=name, i_dps_out=abs(i_out[late].mean()), i_pk=np.abs(i_out).max(),
                   i_k1=np.abs(r[I(f'tec:{k1}:21')]).max(),
                   i_k2_11=np.abs(r[I(f'tec:{k2}:11')]).max(), i_k2_21=np.abs(r[I(f'tec:{k2}:21')]).max(),
                   i_j2_pin_max=max(np.abs(r[I(f'tec:{jo}:{p}')])[late].max() for p in '123456'),
                   i_j3_pin_max=max(np.abs(r[I(f'tec:{jt}:{p}')])[late].max() for p in '1234'),
                   string_imbalance=abs(np.abs(r[I(f'tec:{jt}:1')])[late].mean() - np.abs(r[I(f'tec:{jt}:3')])[late].mean()),
                   v_tec1=r['v(ext_tec_1,ext_tec_2)'][late].mean(), v_dps=r['v(dpso_p,dpso_n)'][late].mean(),
                   k1_drop=np.abs(r[vecs[-4]] - r[vecs[-1]])[late].mean())
        if t_on < 0:
            after = t > 45e-3
            row['k1_open_contact_V'] = np.abs(r[vecs[-4]] - r[vecs[-1]])[after].max()
        rows.append(row)
        res[name] = (row, r)
    chk.csv('dps_tec_cases.csv', rows)
    # ---- checks
    v, s = L('g2rl_contact_a')
    worst = max((r_ for r_ in rows if 'short' not in r_['case']), key=lambda x: x['i_k1'])
    chk.add('k1_peak', 'Peak K1 contact current (all cases except the TEC-lead short)', worst['i_k1'],
            v, '<=', 'A', s, corner=worst['case'])
    sh = [r_ for r_ in rows if 'short' in r_['case']][0]
    chk.add('k1_make_short', 'K1 makes onto a shorted TEC lead with the DPS output capacitor charged: peak contact current', sh['i_k1'], 8.0 * 10,
            '<=', 'A', 'no make/inrush rating published for G2RL-2; project screen 10 x the 8 A rating (contact-welding risk if exceeded)',
            severity='rating', advisory=True, detail='DPS output capacitance is assumed 470 uF (not published)')
    v, s = L('g2rl_carry_70C')
    chk.add('k_carry', 'Continuous relay contact current at pull-down (5 A)', max(r_['i_dps_out'] for r_ in rows if 'pull-down' in r_['case']), v,
            '<=', 'A', s)
    v, s = L('minifit_a_per_pin')
    chk.add('j2_pin', 'Highest DPS-output Mini-Fit pin current (3 pins per pole share the current)', max(r_['i_j2_pin_max'] for r_ in rows if 'short' not in r_['case']),
            v, '<=', 'A', s)
    chk.add('j3_pin', 'Highest TEC Mini-Fit pin current (one pin per string per pole)', max(r_['i_j3_pin_max'] for r_ in rows if 'short' not in r_['case']),
            v, '<=', 'A', s)
    v, s = tp['Imax'], tp['source']
    chk.add('tec_module_i', 'Highest TEC string (module) current in operation incl. defrost with aiding Seebeck EMF',
            max(abs(r_['i_dps_out']) / 2 + r_['string_imbalance'] / 2 for r_ in rows if 'short' not in r_['case']), v, '<=', 'A', s)
    br = [r_ for r_ in rows if 'breaks' in r_['case']][0]
    v, s = L('g2rl_contact_v')
    chk.add('k1_open_v', 'Voltage across the opened K1 (both poles in series) after breaking 5 A (DPS rises to CV)', br.get('k1_open_contact_V', 0.0),
            v, '<=', 'V', s + ' (rated switching voltage)')
    v, s = L('dps5005_iout_max')
    chk.add('dps_i', 'DPS output current at pull-down (CC setting) vs DPS5005 rating', max(r_['i_dps_out'] for r_ in rows if 'short' not in r_['case']),
            v, '<=', 'A', s)
    st = [r_ for r_ in rows if r_['case'].startswith('steady')][0]
    pd = [r_ for r_ in rows if r_['case'].startswith('pull-down')][0]
    hr = (24.0 - 0.3) / 1.1
    chk.add('dps_headroom', 'DPS output voltage needed at pull-down vs DPS5005 headroom (Vin >= 1.1 x Vout from ~23.7 V)', pd['v_dps'], hr, '<=', 'V',
            'Joy-IT DPS5005 manual: input >= 1.1 x output', severity='functional')
    chk.note(f"Steady cooling: DPS {st['v_dps']:.2f} V / {st['i_dps_out']:.2f} A, TEC string {st['v_tec1']:.2f} V; K1 two-pole drop {st['k1_drop'] * 1e3:.0f} mV at max contact R.")
    chk.note(f"TEC alpha {alpha:.4f} V/K per module from {tp['source']}.")
    chk.note('K2 switching under load is excluded by the S05 interlock analysis except in the supply-loss races reported there.')
    for name, (row, r) in res.items():
        if name.startswith('K1 makes onto array') or name.startswith('defrost'):
            t = r['time']
            report.plot(chk.outdir / ('k1_make.png' if name.startswith('K1') else 'defrost_make.png'), f'S06 {name}', [
                dict(ylabel='A', traces=[(t, r[I(f'tec:{k1}:21')], 'K1 contact'), (t, r[I(f'tec:{jt}:1')], 'string 1'), (t, r[I(f'tec:{jt}:3')], 'string 2')]),
                dict(ylabel='V', traces=[(t, r['v(dpso_p,dpso_n)'], 'DPS output'), (t, r['v(ext_tec_1,ext_tec_2)'], 'TEC string 1 terminals')])])
    return chk


def _n(card, ref, pin):
    from d34sim.netlist import spice_node
    return spice_node('tec', card.net(ref, pin)).lower()
