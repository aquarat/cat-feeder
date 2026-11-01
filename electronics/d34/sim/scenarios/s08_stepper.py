"""S08 - StepStick supply: chopper ripple on VMOT and ripple current in its electrolytic (ngspice, full system).

Behavioural TMC2209 supply current: both bridges chopping in phase at 35 kHz (worst case for ripple), 1 A per phase,
duty swept over standstill (I*R/VMOT) to running (back-EMF) values. Reports VMOT ripple, the largest
electrolytic ripple current on the VMOT net against its datasheet rating, and the 12 V rail seen by the tec card.
"""
import numpy as np

from d34sim import common, flows, report
from d34sim import models as M_
from d34sim.circuit import Ctx

TITLE = 'StepStick VMOT ripple and capacitor ripple current at 1 A/phase'


def run(env):
    chk = report.Checks('s08_stepper', env.outdir('s08_stepper'))
    L = env.limit
    N, R = flows.names(env)
    ro = flows.Roles(env)
    pc = env.cards['pwr']
    ss = R['ss']
    vmot_net = pc.net(ss, pc.pin_by_func(ss, 'VMOT'))
    caps = [r for r in ro.model_refs('pwr', 'cap_elec') if vmot_net in pc.pins(r).values()]
    big = max(caps, key=lambda r: __import__('d34sim.models', fromlist=['x']).parse_value(pc.comps[r]['value']))
    sense = [f'pwr:{c}:1' for c in caps]
    I = {c: f'i(vsense_pwr_{c.lower()}_1)' for c in caps}
    vecs = [f'v({N["vmot"]})', f'v({N["v12tec"]})', f'v({N["v12"]})'] + list(I.values())
    rows, worst = [], None
    f = 35e3
    vm_nom = 12.0 if N['vmot'] == N['v12'] else 24.0
    for duty in (0.15, 0.31, 0.5, 0.7):
        T = 1 / f
        pts = [(0, 0)]
        t = 1e-3
        while t < 3e-3:
            pts += [(t, 0), (t + 50e-9, 2.0), (t + duty * T, 2.0), (t + duty * T + 50e-9, 0)]
            t += T
        chop = 'PWL(' + ' '.join(f'{a:.9g} {b}' for a, b in pts) + ')'

        def make(nv):
            ctx = Ctx(dict(temp_C=40.0, esr='nom'), no_vendor=nv, stepper=chop, sense=sense)
            return common.build(env, ctx, brick=dict(v=24.0, t_close=None))
        c, info, r = common.run_robust(make, f's08_{int(duty * 100)}', vecs, 'tran 50n 3m 0 100n', chk)
        t = r['time']
        m = t > 1.5e-3
        row = dict(duty=duty, vmot_pp=np.ptp(r[vecs[0]][m]), vmot_min=r[vecs[0]][m].min(), v12tec_pp=np.ptp(r[vecs[1]][m]),
                   i_avg=2.0 * duty)
        for cref, iv in I.items():
            x = r[iv][m]
            row[f'irms_{cref}'] = float(np.sqrt(np.mean((x - x.mean()) ** 2)))
        rows.append(row)
        if worst is None or row['vmot_pp'] > worst[0]['vmot_pp']:
            worst = (row, r)
    chk.csv('stepper_ripple.csv', rows)
    w = worst[0]
    chk.add('vmot_ripple', 'StepStick VMOT ripple (pk-pk) with both bridges chopping in phase', w['vmot_pp'], 0.05 * vm_nom, '<=', 'V',
            'project: <= 5 % of VMOT (TMC2209 asks for >= 100 uF low-ESR on VS; no ripple limit published)', severity='functional',
            corner=f"duty {w['duty']}")
    for cref in caps:
        row = M_.match(env.table, pc.comps[cref])
        rated = row['params'].get('ripple_a_rms') or 0.0
        s = f"{pc.comps[cref]['mpn']} rated ripple {rated} A rms (100 kHz, 105 C; part_models.csv / datasheet)"
        if not rated:
            chk.note(f'{cref} {pc.comps[cref]["mpn"]}: no ripple rating in part_models.csv - check skipped')
            continue
        # 35 kHz frequency multiplier ~0.97 (between 10 k 0.95 and 100 k 1.0); no ambient multiplier published -> 105 C rating used
        i = max(r_[f'irms_{cref}'] for r_ in rows)
        chk.add(f'ripple_{cref}', f'{cref} ({pc.comps[cref]["value"]}, on VMOT) ripple current vs rating', i, rated * 0.97, '<=', 'A rms',
                s + ' x 0.97 frequency factor at 35 kHz', severity='rating')
    v, s = L('tmc2209_vs_op_max')
    chk.add('vmot_min', 'Lowest VMOT under chopping vs TMC2209 minimum VS 5.5 V', min(r_['vmot_min'] for r_ in rows), 5.5, '>=', 'V',
            'ADI TMC2209 VS operating 5.5-29 V', severity='functional')
    t = worst[1]['time']
    report.plot(chk.outdir / 'vmot_ripple.png', f"S08 VMOT with 2 x 1 A chopping, duty {w['duty']}", [
        dict(ylabel='V', traces=[(t, worst[1][vecs[0]], 'StepStick VMOT'), (t, worst[1][vecs[1]], '+12 V at tec card')]),
        dict(ylabel='A', traces=[(t, worst[1][I[c]], c) for c in caps])], xscale=1e3)
    chk.note(f'VMOT net {vmot_net}; electrolytics on it: {caps}. Chopper modelled as 2 A pulses (1 A per phase in phase) at 35 kHz.')
    return chk
