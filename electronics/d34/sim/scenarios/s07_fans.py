"""S07 - Fan channels at 25 kHz (ngspice, ctrl + tec cards with ideal 12 V / 5 V feeds).

FAN1: ESP32 GPIO -> 4.7 k -> 2N3904 open collector -> 4-pin fan PWM input (fan-internal pull-up, Intel 4-wire spec bounds).
FAN2: ESP32 GPIO -> low side (ULN2003 channel at 25 kHz, or IRLZ44N switched DC in D34-3) of the blower; input capacitance assumed.
Checks: PWM low level and edges at the fan, transistor/Darlington current and dissipation, clamp/flyback, tach levels.
"""
import numpy as np

from d34sim import common, report, system
from d34sim.circuit import Ctx
from d34sim.netlist import spice_node

TITLE = 'Fans: FAN1 25 kHz PWM via 2N3904; FAN2/FAN3 low side (ULN2003 PWM or IRLZ44N switched DC), tach'


def square(f, duty, t0, t1, edge=20e-9):
    pts = [(0, 0)]
    T = 1 / f
    t = t0
    while t < t1:
        pts += [(t, 0), (t + edge, 1), (t + duty * T, 1), (t + duty * T + edge, 0)]
        t += T
    return 'PWL(' + ' '.join(f'{a:.9g} {b}' for a, b in pts) + ')'


def run(env):
    chk = report.Checks('s07_fans', env.outdir('s07_fans'))
    L = env.limit
    ctrl, tec = env.cards['ctrl'], env.cards['tec']
    from d34sim import flows
    ro = flows.Roles(env)
    dk = ro.model_refs('ctrl', 'devkit')[0]
    io_of = {net: ctrl.pin_func[(dk, p)] for p, net in ctrl.pins(dk).items()}
    _, j5 = env.harness['leads']['FAN1']['a']
    _, j6 = env.harness['leads']['FAN2']['a']
    fan1_pwm_net = None
    # FAN1 drive: the GPIO whose net reaches the NPN base resistor through the XH-12 link
    q = [r for r in ro.model_refs('tec', 'npn') if tec.net(r, tec.pin_by_func(r, 'C')) == tec.net(j5, '4')][0]
    fan_od = tec.net(q, tec.pin_by_func(q, 'C'))
    base = tec.net(q, tec.pin_by_func(q, 'B'))
    rb = [r for r in tec.comps if r.startswith('R') and base in tec.pins(r).values()][0]
    fan1_pwm_net = [n for n in tec.pins(rb).values() if n != base][0]
    gpio1 = io_of.get(fan1_pwm_net)
    fan2_n = tec.net(j6, '1')
    uln = [r for r in ro.model_refs('tec', 'uln2003')]
    fets = [r for r in ro.model_refs('tec', 'nmos') if tec.net(r, tec.pin_by_func(r, 'D')) == fan2_n]
    if fets:
        sw = fets[0]
        sw_pin = tec.pin_by_func(sw, 'D')
        fan2_in = tec.net(sw, tec.pin_by_func(sw, 'G'))
        sw_kind = 'nmos'
    else:
        sw = uln[0]
        ch = [c for c in range(1, 8) if tec.net(sw, tec.pin_by_func(sw, f'O{c}')) == fan2_n][0]
        sw_pin = tec.pin_by_func(sw, f'O{ch}')
        fan2_in = tec.net(sw, tec.pin_by_func(sw, f'I{ch}'))
        sw_kind = 'uln2003'
    gpio2 = io_of.get(fan2_in)
    n = lambda card, net: spice_node(card, net).lower()
    v12 = tec.net(j6, '2')
    rows = []
    worst = {}
    vecs = [f'v({n("tec", fan_od)})', f'v(ext_fan1_4)', f'v({n("tec", fan2_n)})', f'v({n("tec", v12)},{n("tec", fan2_n)})',
            f'i(vsense_tec_{q.lower()}_{tec.pin_by_func(q, "C")})', f'i(vsense_tec_{sw.lower()}_{sw_pin})',
            f'v({n("ctrl", "TACH1")})' if 'TACH1' in ctrl.nets else 'v(0)']
    tach2 = tec.net(j6, '3')
    tach2_io = None
    if tach2 and tach2 in ctrl.nets:
        rr = [r for r in ctrl.comps if r.startswith('R') and tach2 in ctrl.pins(r).values()]
        for r in rr:
            other = [x for x in ctrl.pins(r).values() if x != tach2][0]
            if other in io_of:
                tach2_io = other
        vecs.append(f'v({n("ctrl", tach2_io or tach2)})')
    from d34sim import ext as E
    bl = E.externals()['blower']
    for pu_v, pu_r, cap_lab, c_in in ((5.25, 1.05e3, f'blower Cin {bl["c_in_F"][0] * 1e6:.1f} uF', bl['c_in_F'][0]),
                                      (3.3, 10e3, f'blower Cin {bl["c_in_F"][1] * 1e6:.1f} uF', bl['c_in_F'][1])):
        for duty in (0.2, 0.5, 0.8):
            # FAN1: 25 kHz PWM. FAN2: 25 kHz low-side PWM (ULN2003 design) or switched DC on at 0.2 ms, off at 0.9 ms (MOSFET design)
            f2 = square(25e3, duty, 0.2e-3, 1.2e-3) if sw_kind == 'uln2003' else 'PWL(0 0 0.2m 0 0.20002m 1 0.9m 1 0.90002m 0)'
            gp = {gpio1: square(25e3, duty, 0.2e-3, 1.2e-3), gpio2: f2}

            def make(nv):
                ctx = Ctx(dict(temp_C=40.0), no_vendor=nv, gpio=gp, sense=[f'tec:{q}:{tec.pin_by_func(q, "C")}',
                                                                           f'tec:{sw}:{sw_pin}'])
                c, info = system.build(env.cards, env.harness, ctx, cards_in=('ctrl', 'tec'),
                                       fans={'FAN1': dict(i_run=0.14, pwm_pullup_v=pu_v, pwm_pullup_r=pu_r),
                                             'FAN2': dict(i_run=bl['i_A'], c_in=c_in, pwm_pullup_v=0.0,
                                                          tach='DC 1' if bl.get('tach') else 'DC 0')})
                _, j1 = env.harness['leads']['LINK_12V']['b']
                c.add('* ideal 12 V into the tec card VH-3 and 5 V into the ctrl link (supplies are studied in S04)',
                      f'V12ext {n("tec", tec.net(j1, "1"))} {n("tec", "GND")} 12.0',
                      f'V5ext {n("ctrl", "+5V")} 0 5.0')
                return c, info
            c, info, r = common.run_robust(make, f's07_{int(pu_v * 10)}_{int(duty * 100)}', vecs, 'tran 20n 1.2m 0 50n', chk)
            t = r['time']
            m = t > 0.6e-3
            dt = np.diff(t, prepend=t[0])
            ic_q = r[vecs[4]]
            iu = r[vecs[5]]
            vq = r[vecs[0]]
            vu = r[vecs[2]]
            pwm = r[vecs[1]]
            row = dict(pullup=f'{pu_v} V / {pu_r:.0f} ohm', blower=cap_lab, duty=duty,
                       fan1_vol=float(np.median(pwm[m][pwm[m] < 0.5 * pu_v])) if (pwm[m] < 0.5 * pu_v).any() else float('nan'),
                       fan1_rise_us=_edge(t[m], pwm[m], 0.1 * pu_v, 0.9 * pu_v) * 1e6,
                       q_ic_pk=np.abs(ic_q).max(), q_p_avg=float(np.sum(np.abs(vq * ic_q)[m] * dt[m]) / (t[m][-1] - t[m][0])),
                       uln_ic_pk=np.abs(iu).max(), uln_p_avg=float(np.sum(np.abs(vu * iu)[m] * dt[m]) / (t[m][-1] - t[m][0])),
                       fan2_n_pk=vu.max(), fan2_v_min=r[vecs[3]][m].min(),
                       tach2_io_max=r[vecs[7]][m].max() if len(vecs) > 7 else float('nan'))
            rows.append(row)
            for k in ('fan1_vol', 'q_ic_pk', 'uln_ic_pk', 'uln_p_avg', 'fan2_n_pk', 'fan1_rise_us', 'tach2_io_max'):
                if k not in worst or (np.isfinite(row[k]) and row[k] > worst[k][0][k]):
                    worst[k] = (row, r)
    chk.csv('fan_cases.csv', rows)
    cd = lambda w: f"{w['pullup']}, {w['blower']}, duty {w['duty']}"
    v, s = L('fan_pwm_vol_max')
    w = worst['fan1_vol'][0]
    chk.add('fan1_vol', 'FAN1 PWM low level at the fan connector (strongest Intel-spec pull-up, 5 mA)', w['fan1_vol'], v, '<=', 'V', s, corner=cd(w))
    w = worst['fan1_rise_us'][0]
    chk.add('fan1_edges', 'FAN1 PWM 10-90 % rise time at 25 kHz (weak pull-up + cable) vs 10 % of the 40 us period', w['fan1_rise_us'], 4.0, '<=',
            'us', 'project: edges < 10 % of the PWM period (Intel spec allows 21-28 kHz)', severity='functional', corner=cd(w))
    v, s = L('q2n3904_ic_max')
    w = worst['q_ic_pk'][0]
    chk.add('q_ic', '2N3904 peak collector current', w['q_ic_pk'], v, '<=', 'A', s, corner=cd(w))
    w = worst['uln_ic_pk'][0]
    w2 = worst['uln_p_avg'][0]
    w3 = worst['fan2_n_pk'][0]
    if sw_kind == 'uln2003':
        v, s = L('uln2003_ic_max')
        chk.add('uln_fan_peak', 'ULN2003 FAN2 channel peak current at 25 kHz (blower input capacitor recharged every cycle)', w['uln_ic_pk'], v, '<=',
                'A', s, corner=cd(w), detail='blower input capacitance not published (1 and 4.7 uF assumed)')
        chk.add('uln_fan_power', 'ULN2003 FAN2 channel average dissipation', w2['uln_p_avg'], 0.25, '<=', 'W',
                'project: <= 0.25 W per channel (DIP-16 66.7 K/W)', corner=cd(w2))
        v, s = L('uln2003_vce_max')
    else:
        chk.add('fet_fan_peak', f'{sw} (IRLZ44N) FAN2 turn-on peak current (blower input capacitor through the feed polyfuse)', w['uln_ic_pk'], 47.0,
                '<=', 'A', 'Infineon IRLZ44N ID 47 A', corner=cd(w), detail='blower input capacitance not published (1 and 4.7 uF assumed)')
        rds_hot = 0.035 * 1.5
        p_on = bl['i_A'] ** 2 * rds_hot
        chk.add('fet_fan_power', f'{sw} conduction loss with the blower on (35 mOhm at VGS 4 V max x1.5 hot; 3.3 V drive below spec)', p_on, 0.1,
                '<=', 'W', 'project (TO-220 62 K/W)', detail=f'simulated average over the on/off test {w2["uln_p_avg"]:.3f} W')
        chk.add('fet_gate_drive', f'{sw} gate drive: ESP32 3.3 V vs IRLZ44N VGS(th) max 2.0 V (datasheet); manufacturer model threshold 2.09 V',
                3.3 * 0.8, 2.0 + 0.5, '>=', 'V', 'Infineon IRLZ44N VGS(th) 1.0-2.0 V; Fig 1 shows ~32 mOhm at VGS 3.0 V for 3 A; project margin 0.5 V '
                'over the max threshold at the ESP32 VOH min (0.8 VDD)', severity='functional')
        v, s = L('irlz44n_vds_max')
    chk.add('fan2_flyback', 'FAN2 low-side node peak at turn-off (flyback clamp to the fan feed)', w3['fan2_n_pk'], v, '<=', 'V', s, corner=cd(w3))
    if bl.get('tach') and 'tach2_io_max' in worst:
        w = worst['tach2_io_max'][0]
        chk.add('tach2_backdrive', 'Blower tach (open collector referenced to the switched FAN2 ground) back-driving the ESP32 tach input '
                'while the low side is off', w['tach2_io_max'], 3.3 + L('esp32_pin_over')[0], '<=', 'V', L('esp32_pin_over')[1],
                severity='rating', corner=cd(w), detail='fan-internal tach transistor/base drive is a generic model (22 k base resistor, 2N3904-class)')
    chk.note(f"Blower {bl['part']} ({bl['i_A']} A, tach {'yes' if bl.get('tach') else 'no'}): on a low-side-switched channel its tach is "
             'referenced to the switched ground, so it is only valid while the channel is on (read tach at 100 % duty or gate it in firmware).')
    chk.note(f'FAN1 drive from {gpio1} (strap pin: 10 k pull-down keeps it low at boot), FAN2 from {gpio2}.')
    row, r = worst['uln_ic_pk']
    t = r['time']
    report.plot(chk.outdir / 'fan_pwm.png', f'S07 fans at 25 kHz: {cd(row)}', [
        dict(ylabel='V', traces=[(t, r[vecs[1]], 'FAN1 PWM pin at fan'), (t, r[vecs[2]], 'FAN2 low side (ULN output)')]),
        dict(ylabel='A', traces=[(t, r[vecs[4]], '2N3904 Ic'), (t, r[vecs[5]], f'{sw} FAN2 low side')])], xscale=1e6, xlabel='time (us)')
    return chk


def _edge(t, v, lo, hi):
    up = np.nonzero((v[:-1] < lo) & (v[1:] >= lo))[0]
    best = []
    for i in up:
        j = np.nonzero(v[i:] >= hi)[0]
        if len(j):
            best.append(t[i + j[0]] - t[i])
    return float(max(best)) if best else float('nan')
