"""S04 - Power-up / power-down sequencing of the 12 V and 5 V bucks and the ESP32 3.3 V rail (ngspice).

(a) brick plug-in: rail order, overshoot, monotonic 3.3 V rise;
(b) Wi-Fi TX bursts on the DevKit AMS1117 behind the 1N5819: minimum 3.3 V vs ESP32 VDD min and brown-out,
    across OKI 5 V setpoint tolerance, link-lead length, diode temperature and AMS1117 dropout (typ/max);
(c) brick removal at idle and at pull-down load: rail collapse order and 3.3 V behaviour;
(d) USB-only (DevKit on a PC, brick unplugged): back-feed through the 1N5819 into the 5 V buck output.
"""
import numpy as np

from d34sim import common, flows, report
from d34sim.circuit import Ctx

TITLE = 'Rail sequencing, Wi-Fi burst droop on the ESP32 3.3 V rail, power-down and USB back-feed'

LDO = {'typ': dict(vdo0=0.95, kdo=0.19), 'max': dict(vdo0=1.10, kdo=0.25)}


def pwl(points):
    return 'PWL(' + ' '.join(f'{t:.9g} {v:.6g}' for t, v in points) + ')'


def bursts(t0, t1, period, width, base, peak, edge=2e-6):
    pts = [(0, base)]
    t = t0
    while t + width < t1:
        pts += [(t, base), (t + edge, peak), (t + width, peak), (t + width + edge, base)]
        t += period
    return pwl(pts)


def run(env):
    chk = report.Checks('s04_sequencing', env.outdir('s04_sequencing'))
    L = env.limit
    N, R = flows.names(env)
    V = lambda k: f'v({N[k]})'
    vecs = [V('v24'), V('aux'), V('v12'), V('v5'), V('v5ctrl'), V('v5dk'), V('v3v3'), V('v12tec'), V('v3v3pwr')]
    vdd_min, s_vdd = L('esp32_vdd_min')
    vdd_max, s_vmax = L('esp32_vdd_max')
    bod, s_bod = L('esp32_bod_v')
    # ------------------------------------------------------------------ (a) power-up
    def make_up(nv):
        ctx = Ctx(dict(temp_C=40.0), no_vendor=nv)
        return common.build(env, ctx, brick=dict(v=24.0, t_close=1e-3, c_out=1000e-6, esr=0.03))
    c, info, r = common.run_robust(make_up, 's04_powerup', vecs, 'tran 5u 40m 0 5u', chk)
    t = r['time']
    tr = {}
    for name, key, frac in (('+24V', V('v24'), 0.9 * 24), ('+12V', V('v12'), 0.9 * 12), ('+5V', V('v5'), 0.9 * 5),
                            ('3V3', V('v3v3'), 0.9 * 3.3)):
        tr[name] = common.first_cross(t, r[key], frac)
    v33 = r[V('v3v3')]
    rising = v33[(t > 1e-3) & (v33 < 3.0)]
    nonmono = float(np.max(np.maximum.accumulate(rising) - rising)) if len(rising) else 0.0
    chk.add('up_3v3_overshoot', 'Power-up: peak ESP32 3.3 V', v33.max(), vdd_max, '<=', 'V', s_vmax)
    chk.add('up_3v3_monotonic', 'Power-up: 3.3 V rise is monotonic below 3.0 V (largest dip during the rise)', nonmono, 0.05, '<=', 'V',
            'project: ESP32 needs a clean rising supply before EN (DevKit EN RC ~2 ms)', severity='functional')
    chk.add('up_order', 'Power-up completes: all rails within 90 % (ms after plug-in, +24/+12/+5/3V3)',
            float(max(tr.values()) - 1e-3) * 1e3, 30.0, '<=', 'ms', 'project (buck UVLO/soft-start are ASSUMED; not published by Murata)',
            severity='functional', detail=', '.join(f'{k} {1e3 * (v - 1e-3):.2f} ms' for k, v in tr.items()))
    report.plot(chk.outdir / 'powerup.png', 'S04 power-up (brick plugged at 1 ms)', [
        dict(ylabel='V', traces=[(t, r[V('v24')], '+24V'), (t, r[V('v12')], '+12V'), (t, r[V('v5')], '+5V (pwr)'),
                                 (t, r[V('v5dk')], 'DevKit 5V pin'), (t, v33, '3V3')])])
    # ------------------------------------------------------------------ (b) Wi-Fi bursts
    rows = []
    worst = None
    i_peak_task = 0.5
    i_peak_ds, s_tx = L('esp32_tx_peak')
    for peak, plab in ((i_peak_task, 'task 500 mA'), (i_peak_ds, 'datasheet 379 mA')):
        for vm in (0.97, 1.0):
            for lead in ('nom', 'max'):
                for temp in (25.0, 40.0):
                    for ldo in ('typ', 'max'):
                        if getattr(env, 'quick', False) and (lead == 'nom' or temp == 40.0):
                            continue
                        load = bursts(5e-3, 25e-3, 5e-3, 2e-3, 0.08, peak)

                        def make(nv):
                            ctx = Ctx(dict(temp_C=temp, length=lead, contact=lead, L=lead), no_vendor=nv, esp_load=load,
                                      ldo=LDO[ldo], buck_vmult={f'pwr_{R["buck5"]}': vm})
                            return common.build(env, ctx, brick=dict(v=24.0, t_close=None, c_out=1000e-6, esr=0.03))
                        name = f's04_wifi_{int(peak * 1e3)}_{vm}_{lead}_{int(temp)}_{ldo}'
                        c, info, r = common.run_robust(make, name, vecs, 'tran 2u 27m 0 2u', chk)
                        m = r['time'] > 4e-3
                        row = dict(peak=plab, oki5_set=vm, lead=lead, temp_C=temp, ldo=ldo,
                                   v5_min=r[V('v5')][m].min(), v5dk_min=r[V('v5dk')][m].min(),
                                   v33_min=r[V('v3v3')][m].min(), v33_mean=r[V('v3v3')][m].mean(),
                                   headroom_min=(r[V('v5dk')] - r[V('v3v3')])[m].min())
                        rows.append(row)
                        if worst is None or row['v33_min'] < worst[0]['v33_min']:
                            worst = (row, r)
    chk.csv('wifi_burst_cases.csv', rows)
    w = worst[0]
    corner = f"{w['peak']}, OKI5 x{w['oki5_set']}, lead {w['lead']}, {w['temp_C']} C, AMS1117 dropout {w['ldo']}"
    chk.add('wifi_3v3_vdd', 'Wi-Fi TX bursts: minimum ESP32 3.3 V vs VDD min', w['v33_min'], vdd_min, '>=', 'V', s_vdd, corner=corner,
            severity='functional')
    chk.add('wifi_3v3_bod', 'Wi-Fi TX bursts: minimum ESP32 3.3 V vs brown-out detector (default level 0, upper tolerance)',
            w['v33_min'], bod, '>=', 'V', s_bod, corner=corner, severity='functional')
    ds_rows = [r_ for r_ in rows if r_['peak'].startswith('datasheet')]
    if ds_rows:
        wd = min(ds_rows, key=lambda x: x['v33_min'])
        chk.add('wifi_3v3_vdd_ds', 'Wi-Fi TX at the datasheet 379 mA peak: minimum 3.3 V vs VDD min', wd['v33_min'], vdd_min, '>=', 'V',
                f'{s_vdd}; {s_tx}', severity='functional',
                corner=f"OKI5 x{wd['oki5_set']}, lead {wd['lead']}, {wd['temp_C']} C, dropout {wd['ldo']}")
    r = worst[1]
    t = r['time']
    report.plot(chk.outdir / 'wifi_worst.png', f'S04 Wi-Fi bursts, worst corner: {corner}', [
        dict(ylabel='V', traces=[(t, r[V('v5')], '+5V at buck'), (t, r[V('v5ctrl')], '+5V at ctrl'),
                                 (t, r[V('v5dk')], 'DevKit 5V (after 1N5819)')]),
        dict(ylabel='V', traces=[(t, r[V('v3v3')], '3V3')], hlines=[(vdd_min, 'VDD min 3.0 V'), (bod, 'BOD')])])
    # ------------------------------------------------------------------ (c) power-down
    for case, p_dps in (('idle', 0.0), ('pull-down 100 W DPS load', 110.0)):
        def make_dn(nv):
            ctx = Ctx(dict(temp_C=40.0), no_vendor=nv)
            return common.build(env, ctx, brick=dict(v=24.0, t_close=None, bounce=[(10e-3, 10.0)], c_out=1000e-6, esr=0.03),
                                dps_in=dict(c_in=470e-6, esr=0.05, p_load=p_dps, t_on=0.0))
        c, info, r = common.run_robust(make_dn, f's04_powerdown_{int(p_dps)}', vecs, 'tran 10u 300m 0 20u', chk)
        t = r['time']
        t12 = common.first_cross(t, r[V('v12tec')], 9.0, rising=False, after=10e-3)
        t33 = common.first_cross(t, r[V('v3v3')], 3.0, rising=False, after=10e-3)
        v33 = r[V('v3v3')][t > 10e-3]
        rebound = float(np.max(v33 - np.minimum.accumulate(v33)))
        chk.add(f'down_order_{int(p_dps)}', f'Power-down ({case}): relays lose 12 V (below 9 V) before the ESP32 3.3 V falls below 3.0 V',
                (t33 - t12) * 1e3 if np.isfinite(t12) else -1.0, 0.0, '>', 'ms', 'project: hardware drops the TEC relays while logic is still valid',
                severity='functional', detail=f'12 V < 9 V at {1e3 * (t12 - 10e-3):.1f} ms, 3V3 < 3.0 V at {1e3 * (t33 - 10e-3):.1f} ms after unplug')
        chk.add(f'down_3v3_mono_{int(p_dps)}', f'Power-down ({case}): 3.3 V decays without rebounding (largest rebound)', rebound, 0.1, '<=', 'V',
                'project: no supply bounce that could re-run the ESP32 boot', severity='functional')
        report.plot(chk.outdir / f'powerdown_{int(p_dps)}.png', f'S04 brick removed at 10 ms ({case})', [
            dict(ylabel='V', traces=[(t, r[V('v24')], '+24V'), (t, r[V('v12tec')], '+12V at tec card'),
                                     (t, r[V('v5')], '+5V'), (t, r[V('v3v3')], '3V3')])])
    # ------------------------------------------------------------------ (c2) aux PTC trips with the DPS running: how fast does 12 V fall?
    for t_ramp in (0.05, 0.5):
        def make_ptc(nv):
            ctx = Ctx(dict(temp_C=40.0), no_vendor=nv)
            c, info = common.build(env, ctx, brick=dict(v=24.0, t_close=None), exclude=(f'pwr:{R["f2"]}',),
                                   dps_in=dict(c_in=470e-6, esr=0.05, p_load=80.0, t_on=0.0))
            c.add(f'* aux PTC trip: resistance 0.2 ohm -> 2 kohm (log-linear) over {t_ramp * 1e3:.0f} ms from t = 20 ms (thermal trip, assumed)',
                  f'Bptc {N["v24"]} {N["aux"]} I=V({N["v24"]},{N["aux"]})/(0.2*pow(10,4*min(max((time-0.02)/{t_ramp},0),1)))')
            return c, info
        c, info, r = common.run_robust(make_ptc, f's04_ptc_trip_{int(t_ramp * 1e3)}', vecs, f'tran 20u {0.05 + 1.5 * t_ramp} 0 50u', chk)
        t = r['time']
        a = common.first_cross(t, r[V('v12tec')], 11.0, rising=False, after=0.02)
        b = common.first_cross(t, r[V('v12tec')], 4.8, rising=False, after=0.02)
        chk.note(f'Aux PTC trip over {t_ramp * 1e3:.0f} ms with the DPS loaded: 12 V at the tec card falls from 11 V to 4.8 V (K2 40 % drop-out) '
                 f'in {(b - a) * 1e3:.1f} ms; the 12 V regulator drops out when VAUX < ~14.5 V (assumed UVLO).')

    # ------------------------------------------------------------------ (d) USB back-feed
    IB = 'i(vsense_ctrl_' + R['d_oring'].lower() + '_' + env.cards['ctrl'].pin_by_func(R['d_oring'], 'A') + ')'

    def make_usb(nv):
        ctx = Ctx(dict(temp_C=40.0), no_vendor=nv, usb_vbus=5.1, sense=[f'ctrl:{R["d_oring"]}:{env.cards["ctrl"].pin_by_func(R["d_oring"], "A")}'])
        return common.build(env, ctx, brick=None, dps_in=None)
    c, info, r = common.run_robust(make_usb, 's04_usb_only', vecs + [IB], 'tran 10u 50m 0 20u', chk)
    m = r['time'] > 40e-3
    i_back = -r[IB][m].mean()
    chk.add('usb_backfeed', 'USB-only (brick unplugged): reverse current from the DevKit through the OR-ing Schottky into the 5 V buck output',
            abs(i_back), 1e-3, '<=', 'A', '1N5817/1N5819 IR max 1 mA at 25 C (rated VR); project: no back-powering of the pwr card',
            severity='functional', detail=f'pwr +5V rises to {r[V("v5")][m].mean():.2f} V; ctrl 3V3 {r[V("v3v3")][m].mean():.2f} V')
    chk.note('Regulator UVLO thresholds are not published for the OKI-78SR or TRACO TSR (datasheet_values.json): turn-on 14.5 V (12 V) / 6.5 V (5 V) '
             'assumed; start-up times from part_models.csv (TSR 2: 20 ms datasheet, TSR 1: ~2 ms assumed from the 0.7 ms rise plot).')
    chk.note('AMS1117 dropout is specified only at 0.8 A (1.1 V typ / 1.3 V max); the current dependence below 0.8 A is an assumption.')
    return chk
