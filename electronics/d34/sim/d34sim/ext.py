"""Off-board devices attached through the harness. All behavioural; assumptions are stated per model.

Each function takes the far-end nodes {pin: node} of an external lead and returns SPICE lines.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def tec_params():
    """TEC array parameters from sim/externals.json (datasheet of the fitted module)."""
    e = json.loads((Path(__file__).resolve().parent.parent / 'externals.json').read_text())['tec']
    return dict(R=e['R_ohm'], R_hot=e.get('R_ohm_50C', e['R_ohm']), alpha_V_K=e['alpha_V_K'], Imax=e['Imax_A'],
                steady=(e['op_steady']['i_array_A'], e['op_steady']['dT_K']), pulldown=(e['op_pulldown']['i_array_A'], e['op_pulldown']['dT_K']),
                source=f"{e['part']}: {e['source']}")


def externals():
    return json.loads((Path(__file__).resolve().parent.parent / 'externals.json').read_text())


def brick(far, v=24.0, c_out=1000e-6, esr=0.03, r_src=0.02, ilim=7.0, t_close=1e-6, bounce=None, polarity=1, arc=True):
    """24 V brick: output capacitor (ASSUMED 470-2200 uF class) with ESR, already charged; contact closes at t_close.
    ilim: crude constant-current limit (A) by a series behavioural limiter. bounce: list of (t_open, t_close) after
    the first make. polarity -1 = reversed plug."""
    p, n = (far['1'], far['2']) if polarity > 0 else (far['2'], far['1'])
    # Contact: log-conductance follows a PWL control (breakpoints help the integrator): 1 pS -> 500 S over 1 us (log-linear).
    pwl = [(0, 1)] if t_close is None else [(0, 0), (t_close, 0), (t_close + 1e-6, 1)]  # None: connected at the OP
    for to, tc in (bounce or []):
        pwl += [(to, 1), (to + 2e-7, 0), (tc, 0), (tc + 1e-6, 1)]
    pwl_s = ' '.join(f'{t:.9g} {x}' for t, x in pwl)
    arc_pts = [(0, 0)]
    for to, tc in (bounce or []) if arc else []:
        # a bounce (re-close within 1 ms) arcs for the whole gap; a removal arcs only until the lead current has decayed (20 us)
        te = tc + 1e-6 if tc - to < 1e-3 else to + 20e-6
        arc_pts += [(to, 0), (to + 1e-9, 1), (te, 1), (te + 1e-9, 0)]
    arc_s = ' '.join(f'{t:.9g} {x}' for t, x in arc_pts)
    return [f'* brick {v} V, Cout {c_out*1e6:.0f} uF ESR {esr} ohm, Rsrc {r_src}, current limit {ilim} A (assumed)',
            f'Vbrk brk_src brk_n {v}',
            f'Rbrk brk_src brk_i {r_src}',
            f'Bbrk_lim brk_i brk_o I={ilim}*tanh(V(brk_i,brk_o)/(0.002*{ilim}))',
            f'Cbrk brk_o brk_c {c_out:.4g}', f'Rbrk_esr brk_c brk_n {esr}',
            f'Vbrk_ctl brk_ctl 0 PWL({pwl_s})',
            f'Bbrk_sw brk_o {p} I=V(brk_o,{p})*exp(-27.63+33.84*min(max(V(brk_ctl),0),1))',
            '* contact arc while a bounce separates: ~12 V arc voltage, 50 mOhm (assumed DC arc model)',
            '* contact/cable snubber (assumed 10 nF + 10 ohm; keeps an opening contact finite for the solver)',
            f'Cbrk_sn brk_o brk_snx 10n', f'Rbrk_sn brk_snx {p} 10',
            f'Vbrk_arc brk_arc 0 PWL({arc_s})',
            f'Bbrk_arc brk_o {p} I=V(brk_arc)*(max(V(brk_o,{p})-12,0)-max(-V(brk_o,{p})-12,0))/0.05',
            f'Rbrk_ref brk_n {n} 1e-4']


def dps_input(far, c_in=470e-6, esr=0.05, p_load=0.0, t_on=0.05, uvlo=6.0):
    """DPS5005 input: input capacitance ASSUMED (not published), constant-power load after a start delay."""
    a, b = far['1'], far['2']
    return [f'* DPS5005 input: C {c_in*1e6:.0f} uF (assumed) ESR {esr}, P {p_load} W after {t_on*1e3:.0f} ms',
            f'Cdpsin {a} dpsin_x {c_in:.4g}', f'Rdpsin dpsin_x {b} {esr}',
            f'Vdps_on dps_on 0 ' + ('DC 1' if t_on <= 0 else f'PWL(0 0 {t_on} 0 {t_on + 1e-3} 1)'),
            f'Bdpsin {a} {b} I=V(dps_on)*{p_load}/(0.5*(V({a},{b})+{uvlo}+sqrt((V({a},{b})-{uvlo})^2+0.25)))*0.5*(1+tanh((V({a},{b})-{uvlo})/0.3))']


def dps_output(far, vset=20.0, ilim=5.0, c_out=470e-6, esr=0.05, enable='DC 1'):
    """DPS5005 output (pins 1-3 OUT+, 4-6 OUT- joined at the DPS terminal): CV/CC behavioural source.
    Output capacitance ASSUMED. enable: PWL 0..1 of the output stage (Modbus ON/OFF)."""
    pos = [far[k] for k in ('1', '2', '3') if k in far]
    neg = [far[k] for k in ('4', '5', '6') if k in far]
    lines = [f'* DPS5005 output: CV {vset} V / CC {ilim} A, Cout {c_out*1e6:.0f} uF (assumed)']
    for i, n in enumerate(pos):
        lines.append(f'Rdpsp{i} dpso_p {n} 1e-3')
    for i, n in enumerate(neg):
        lines.append(f'Rdpsn{i} dpso_n {n} 1e-3')
    lines += [f'Vdps_en dps_en 0 {enable}',
              f'Bdpso dpso_n dpso_p I=V(dps_en)*{ilim}*0.5*(1+tanh(({vset}-V(dpso_p,dpso_n))/0.05))',
              f'Cdpso dpso_p dpso_x {c_out:.4g}', f'Rdpso dpso_x dpso_n {esr}',
              'Rdpso_ref dpso_n 0 1e7']
    return lines


def tec_array(far, dT=40.0, R=3.32, alpha=0.0475, L_module=1e-7):
    """2S2P TARK CP14-127-10: each string = 2 modules in series between pin A (1/3) and pin B (2/4).
    Seebeck EMF 2*alpha*dT, positive at A (opposes cooling current A->B). dT may be a SPICE expression."""
    lines = [f'* TEC 2S2P: R {R} ohm/module, alpha {alpha:.4f} V/K, dT {dT} K']
    for s, (a, b) in enumerate((('1', '2'), ('3', '4'))):
        if a not in far or b not in far:
            continue
        lines += [f'Rtec{s} {far[a]} tec{s}_m {2 * R:.4f}', f'Ltec{s} tec{s}_m tec{s}_e {2 * L_module:.3g}',
                  f'Btec{s} tec{s}_e {far[b]} V={2 * alpha:.5f}*({dT})']
    return lines


def thermostats(far, closed='DC 1', r_contact=0.05, n=4):
    """Series loop of n KSD301 NC thermostats; closed: PWL 0..1."""
    return [f'* thermostat loop: {n} x KSD301, {r_contact} ohm per contact (assumed)',
            f'Vth_ctl th_ctl 0 {closed}',
            f'Sth {far["1"]} th_m th_ctl 0 SW_TH', f'Rth th_m {far["2"]} {n * r_contact}',
            '.model SW_TH SW(VT=0.5 VH=0.1 RON=0.001 ROFF=1e9)']


def fan4(far, name, i_run=0.14, c_in=2.2e-6, pwm_pullup_v=5.0, pwm_pullup_r=10e3, tach='DC 0', tach_rb=22e3):
    """4-pin PC fan (Intel 4-wire spec style): motor = constant current + input capacitor (ASSUMED values);
    PWM input pulled up internally to pwm_pullup_v via pwm_pullup_r (ASSUMED within the Intel limits);
    TACH = open-collector NPN to fan ground, driven by `tach` PWL (1 = output low)."""
    g, v, t, pw = far.get('1'), far.get('2'), far.get('3'), far.get('4')
    lines = [f'* fan {name}: {i_run} A, Cin {c_in*1e6:.1f} uF, PWM pull-up {pwm_pullup_r/1e3:.0f}k to {pwm_pullup_v} V (assumed)',
             f'C{name}in {v} {name}_cx {c_in:.4g}', f'R{name}in {name}_cx {g} 0.2',
             f'B{name}m {v} {g} I={i_run}*0.5*(1+tanh((V({v},{g})-6)/0.5))']
    if pw:
        lines += [f'B{name}pu {name}_pu {g} V=min({pwm_pullup_v}, max(V({v},{g})-1,0))',
                  f'R{name}pu {name}_pu {pw} {pwm_pullup_r}', f'C{name}pw {pw} {g} 20p']
    if t:
        lines += [f'V{name}tc {name}_tc 0 {tach}',
                  f'B{name}tb {name}_tbs {g} V=V({name}_tc)*min(5, max(V({v},{g}),0))',
                  f'R{name}tb {name}_tbs {name}_tb {tach_rb}',
                  f'Q{name}t {t} {name}_tb {g} Q2N3904_B', f'C{name}t {t} {g} 50p']
    return lines


def motor(far, R=3.7, L=4e-3):
    """17HS08-1004S: two phases R 3.7 ohm (BOM) and L ASSUMED 4 mH. Pins: 1 2B, 2 2A, 3 1A, 4 1B."""
    return [f'* motor: R {R} ohm, L {L*1e3:.1f} mH per phase (L assumed)',
            f'Rm1 {far["3"]} m1x {R}', f'Lm1 m1x {far["4"]} {L}',
            f'Rm2 {far["2"]} m2x {R}', f'Lm2 m2x {far["1"]} {L}']


def ds18b20(far, name, pull='DC 0', c_in=30e-12, i_vdd=1.5e-3, probes=1):
    """DS18B20 on an XH-3 header (1 GND, 2 DQ, 3 3V3): DQ input capacitance ASSUMED 30 pF, open-drain pull-down
    (on when `pull` = 1, 4 mA at 0.4 V class), VDD supply current."""
    g, dq, vdd = far['1'], far['2'], far['3']
    c_in = c_in * probes + (probes - 1) * 50e-12   # extra probes daisy-chained at the far end (50 pF each for the stub, assumed)
    i_vdd = i_vdd * probes
    return [f'* DS18B20 {name} x{probes}', f'C{name}dq {dq} {g} {c_in:.3g}',
            f'V{name}c {name}_c 0 {pull}', f'S{name} {dq} {g} {name}_c 0 SW_OW',
            '.model SW_OW SW(VT=0.5 VH=0.1 RON=60 ROFF=1e10)',
            f'B{name}vdd {vdd} {g} I={i_vdd}*0.5*(1+tanh((V({vdd},{g})-2.0)/0.2))']
