"""Part -> SPICE model mapping and per-part SPICE emitters.

The mapping table is `part_models.csv` (matched on the netlist MPN field). Every
emitted element records its provenance so the summary can list, per part,
whether a manufacturer model or a behavioural model was used.
"""
import csv
import json
import re
from pathlib import Path

SIM = Path(__file__).resolve().parent.parent
VENDOR = SIM / 'models' / 'vendor'


def parse_value(s):
    """'4.7k' -> 4700, '1M' -> 1e6, '100u 50V' -> 1e-4, '330' -> 330."""
    s = s.strip().split()[0]
    m = re.match(r'^([0-9.]+)([pnumkKMR]?)([0-9]*)$', s)
    if not m:
        raise ValueError(f'cannot parse value {s!r}')
    num, mult, frac = m.groups()
    if frac:
        num = f'{num}.{frac}'
    return float(num) * {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3, 'k': 1e3, 'K': 1e3, 'M': 1e6, 'R': 1, '': 1}[mult]


def load_table(path=None):
    rows = []
    with open(path or SIM / 'part_models.csv', newline='') as f:
        for r in csv.DictReader(f):
            r['params'] = json.loads(r['params']) if r['params'].strip() else {}
            rows.append(r)
    return rows


def match(table, comp):
    """MPN rows first, then symbol (libpart) rows - the latter catch modules and generic passives."""
    for kind in ('mpn', 'value', 'libpart'):
        for r in table:
            if r['match'] != kind:
                continue
            if re.search(r['pattern'], comp.get(kind, '') or ''):
                return r
    return None


def vendor_map():
    p = SIM / 'models' / 'vendor_map.json'
    return json.loads(p.read_text()) if p.exists() else {}


# ---------------------------------------------------------------------------------------------
# Behavioural fallback library (used only where no working manufacturer model exists).
# Each entry: SPICE text + provenance + the datasheet points it was fitted to.
BEHAVIOURAL = {
    'D1N5819_B': ('.model D1N5819_B D(IS=9.4e-7 N=1.05 RS=0.075 BV=40 IBV=1m CJO=110p M=0.35 EG=0.69 XTI=2 TT=0)',
                  'behavioural fit: VF 0.32 V @ 0.1 A, 0.45 V @ 1 A (25 C typical curve)'),
    'D1N5817_B': ('.model D1N5817_B D(IS=3.3e-6 N=1.0 RS=0.06 BV=20 IBV=1m CJO=110p M=0.35 EG=0.69 XTI=2)',
                  'behavioural fit: VF ~0.27 V @ 0.1 A, ~0.38 V @ 1 A (25 C; datasheet max 0.45 V @ 1 A)'),
    'DBAT42_B': ('.model DBAT42_B D(IS=2e-8 N=1.05 RS=2.0 BV=30 IBV=0.5u CJO=7p M=0.4 EG=0.69 XTI=2)',
                 'behavioural fit BAT42: VF ~0.26 V at 2 mA, ~0.37 V at 10 mA (datasheet 0.4 V max at 10 mA)'),
    'D1N4007_B': ('.model D1N4007_B D(IS=7e-9 N=1.8 RS=0.04 BV=1000 IBV=5u CJO=15p M=0.33 TT=5u)',
                  'behavioural fit: VF ~0.93 V @ 1 A'),
    'D1N4148_B': ('.model D1N4148_B D(IS=2.52n N=1.752 RS=0.568 BV=100 IBV=100u CJO=4p M=0.333 TT=11.54n)',
                  'generic 1N4148 parameters'),
    'DZ1N5245B_B': ('.model DZ1N5245B_B D(IS=1e-12 N=1 RS=1 BV=15 IBV=8.5m NBV=1.5 CJO=60p)',
                    'behavioural zener: Vz 15 V @ 8.5 mA, Zzt ~16 ohm'),
    'IRF4905_B': ('.model IRF4905_B VDMOS(pchan Vto=-3.0 Kp=30 Rd=6m Rs=4m Rb=8m Lambda=0.01 '
                  'Cgdmax=1.6n Cgdmin=0.35n Cgs=2.6n Cjo=2.0n Is=5e-9 N=1.3 BV=55 IBV=250u TT=60n)',
                  'behavioural VDMOS: Vth -2..-4 V, Rds(on) ~20 mOhm @ -10 V, Ciss ~3.4 nF, body diode'),
    'IRLZ44N_B': ('.model IRLZ44N_B VDMOS(Vto=1.6 Kp=14 Rd=5m Rs=4m Rb=8m Lambda=0.01 Cgdmax=1.0n Cgdmin=0.12n Cgs=1.6n Cjo=0.6n '
                  'Is=1e-9 N=1.2 BV=55 IBV=250u TT=60n)',
                  'behavioural VDMOS: Vth ~1.6 V (1-2 V), Rds(on) ~25 mOhm at 5 V, ~40 mOhm at 3.3 V (assumed), Ciss ~1.7 nF'),
    'QBC327_B': ('.model QBC327_B PNP(IS=2e-14 BF=250 BR=10 VAF=60 IKF=0.6 ISE=1e-14 NE=1.5 RB=10 RC=0.3 RE=0.1 CJE=60p CJC=25p '
                 'TF=1n TR=50n)', 'behavioural BC327-25 class PNP: hFE 160-400, VCE(sat) ~0.1-0.2 V at 50 mA / 2.5 mA'),
    'Q2N3904_B': ('.model Q2N3904_B NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 ISE=6.734f IKF=66.78m '
                  'XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 CJC=3.638p MJC=.3085 VJC=.75 FC=.5 CJE=4.493p MJE=.2593 '
                  'VJE=.75 TR=239.5n TF=301.2p ITF=.4 VTF=4 XTF=2 RB=10)',
                  'widely published 2N3904 Gummel-Poon parameter set (generic)'),
    'DZBZX79C15_B': ('.model DZBZX79C15_B D(IS=2e-14 N=1.0 RS=1.5 BV=15 IBV=5m NBV=1.5 CJO=80p TT=10n)',
                     'behavioural BZX79-C15: Vz 15 V @ 5 mA; forward VF ~0.75 V @ 10 mA (used forward as a plain diode)'),
    'DLED_G_B': ('.model DLED_G_B D(IS=1e-20 N=1.7 RS=10 BV=5 IBV=10u)', 'behavioural green LED ~2.0 V @ 5 mA'),
    'DCLAMP_B': ('.model DCLAMP_B D(IS=1e-14 N=1.0 RS=20 CJO=1p)', 'generic CMOS ESD clamp diode (assumed 20 ohm)'),
    'DSUB_B': ('.model DSUB_B D(IS=1e-14 N=1.0 RS=2)', 'generic substrate diode'),
    'QDARL1_B': ('.model QDARL1_B NPN(IS=1e-14 BF=150 VAF=100 RB=50 RC=2 CJE=5p CJC=4p TF=2n TR=200n)',
                 'ULN2003 behavioural driver transistor'),
    'QDARL2_B': ('.model QDARL2_B NPN(IS=4e-14 BF=120 IKF=0.6 VAF=100 RB=5 RC=1.2 CJE=25p CJC=15p TF=4n TR=400n)',
                 'ULN2003 behavioural output transistor (fitted: VCE(sat) ~0.9 V @ 100 mA, ~1.1 V @ 350 mA)'),
    'DULNCLAMP_B': ('.model DULNCLAMP_B D(IS=1e-12 N=1.5 RS=0.8 BV=60 IBV=10u)', 'ULN2003 clamp diode: VF ~1.7 V @ 350 mA'),
}


TL431_B = """.subckt TL431_B k a ref params: vref=2.495
* behavioural TL431: cathode current switches on when V(ref,a) exceeds vref (gain ~0.5 A/V per mV-scale tanh), limited to ~100 mA,
* needs V(k,a) > ~1.3 V headroom; ref input bias 2 uA. Datasheet: Vref 2.495 V (TL431A +-1 %), IKmin 1 mA, IK max 100 mA.
Bk k a I=0.1*0.5*(1+tanh((V(ref,a)-{vref})/0.002))*0.5*(1+tanh((V(k,a)-1.3)/0.15))+1e-6*V(k,a)
Iref ref a 2u
.ends TL431_B
"""

ULN_B = """.subckt ULN2003A_CH_B in out com gnd
R1 in b1 2.7k
R2 b1 gnd 7.2k
Q1 out b1 b2 QDARL1_B
R3 b2 gnd 3k
Q2 out b2 gnd QDARL2_B
Dc out com DULNCLAMP_B
Ds gnd out DSUB_B
.ends ULN2003A_CH_B
"""


class Registry:
    """Collects .model/.subckt/.include text and provenance for one circuit."""

    def __init__(self):
        self.models, self.includes, self.subckts = {}, [], {}
        self.provenance = {}
        self.vmap = vendor_map()
        self.no_vendor = set()
        self.missing_vendor = set()

    def need(self, name):
        if name in BEHAVIOURAL:
            self.models[name] = BEHAVIOURAL[name][0]
            return BEHAVIOURAL[name][1]
        raise KeyError(name)

    def vendor_or_fallback(self, key, fallback):
        """Return (model_name, pin_order or None, kind, provenance)."""
        v = self.vmap.get(key)
        if v and v.get('use', True) and key not in self.no_vendor and not (VENDOR / v['file']).exists():
            self.missing_vendor.add(key)
        if v and v.get('use', True) and key not in self.no_vendor and (VENDOR / v['file']).exists():
            inc = str(VENDOR / v['file'])
            if inc not in self.includes:
                self.includes.append(inc)
            return v['model'], v.get('pins'), v.get('type', 'model'), f"manufacturer model {v['file']} ({v.get('source', '')})"
        prov = self.need(fallback)
        return fallback, None, 'model', 'behavioural ' + prov

    def subckt(self, name, text):
        self.subckts[name] = text

    def text(self):
        out = [f'.include {i}' for i in self.includes]
        out += list(self.models.values())
        out += list(self.subckts.values())
        return '\n'.join(out)


# ---------------------------------------------------------------------------------------------
def emit(card, ref, comp, row, nodes, ctx, reg):
    """SPICE lines for one component. nodes: {pin: spice node}."""
    m, p = row['model'], dict(row['params'])
    p.update(ctx.part_params.get(f'{card.name}:{ref}', {}))
    tag = f'{card.name}_{ref}'
    prov = row['provenance']
    lines = []
    if m == 'connector' or m.startswith('logic_'):
        reg.provenance[tag] = 'port (harness)' if m == 'connector' else 'logic: python event model'
        if m.startswith('logic_'):
            lines += ctx.logic_stub(card, ref, comp, nodes, reg)
        return lines
    if m == 'resistor':
        val = parse_value(comp['value']) * ctx.rmult(card.name, ref, p['tol'])
        lines.append(f'R{tag} {nodes["1"]} {nodes["2"]} {val:.6g}')
    elif m in ('cap_elec', 'cap_mlcc'):
        C = (p.get('C') or parse_value(comp['value'])) * ctx.cmult(card.name, ref, p['tol']) * (1 + p.get('dc_bias', 0.0))
        esr = p['esr'] if not isinstance(p['esr'], list) else p['esr'][ctx.idx('esr')]
        esr = ctx.esr_override.get(f'{card.name}:{ref}', esr)
        if esr is None:  # part omitted (unsoldered) in this corner
            reg.provenance[tag] = 'omitted in this corner'
            return []
        n1, n2 = nodes['1'], nodes['2']
        lines += [f'C{tag} {n1} {tag}_x {C:.6g}', f'R{tag}esr {tag}_x {tag}_y {esr:.6g}', f'L{tag}esl {tag}_y {n2} {p["esl"]:.4g}']
    elif m in ('diode', 'led'):
        a = nodes[card.pin_by_func(ref, 'A')]
        k = nodes[card.pin_by_func(ref, 'K')]
        if m == 'led':
            name, prov = 'DLED_G_B', 'behavioural ' + reg.need('DLED_G_B')
        else:
            key = p['vendor']
            fb = ctx.tvs_model() if key == 'P6KE30A' else p['fallback']
            if key == 'P6KE30A':
                BEHAVIOURAL[fb] = ctx.tvs_text(fb)
                if 'tvs_bv' in ctx.corner:   # explicit breakdown corners need the datasheet-line fit
                    key = None
            if key is None:
                name, pins, kind, prov = fb, None, 'model', 'behavioural ' + reg.need(fb)
            else:
                name, pins, kind, prov = reg.vendor_or_fallback(key, fb)
            if kind == 'subckt':
                order = [{'A': a, 'K': k}[x] for x in pins]
                lines.append(f'X{tag} {" ".join(order)} {name}')
                reg.provenance[tag] = prov
                return lines
        lines.append(f'D{tag} {a} {k} {name}')
    elif m == 'pmos':
        g, d, s = (nodes[card.pin_by_func(ref, x)] for x in 'GDS')
        name, pins, kind, prov = reg.vendor_or_fallback(p['vendor'], p['fallback'])
        if kind == 'subckt':
            lines.append(f'X{tag} {" ".join({"D": d, "G": g, "S": s}[x] for x in pins)} {name}')
        else:
            lines.append(f'M{tag} {d} {g} {s} {name}')
    elif m == 'nmos':
        g, d, s_ = (nodes[card.pin_by_func(ref, x)] for x in 'GDS')
        name, pins, kind, prov = reg.vendor_or_fallback(p['vendor'], p['fallback'])
        if kind == 'subckt':
            lines.append(f'X{tag} {" ".join({"D": d, "G": g, "S": s_}[x] for x in pins)} {name}')
        else:
            lines.append(f'M{tag} {d} {g} {s_} {name}')
    elif m == 'pnp':
        e, b, c = (nodes.get(card.pin_by_func(ref, x), '0') for x in 'EBC')
        name, pins, kind, prov = reg.vendor_or_fallback(p['vendor'], p['fallback'])
        if kind == 'subckt':
            lines.append(f'X{tag} {" ".join({"C": c, "B": b, "E": e}[x] for x in pins)} {name}')
        else:
            lines.append(f'Q{tag} {c} {b} {e} {name}')
    elif m == 'shunt_ref':
        k, a, rf = (nodes.get(card.pin_by_func(ref, x), '0') for x in ('K', 'A', 'REF'))
        v = reg.vmap.get(p['vendor'])
        if v and v.get('use', True) and (VENDOR / v['file']).exists() and 'tl431_vref' not in ctx.corner and p['vendor'] not in reg.no_vendor:
            name, pins, kind, prov = reg.vendor_or_fallback(p['vendor'], None)
            lines.append(f'X{tag} {" ".join({"K": k, "A": a, "REF": rf}[x] for x in pins)} {name}')
        else:
            reg.subckt('TL431_B', TL431_B)
            vref = ctx.corner.get('tl431_vref', 2.495)
            lines.append(f'X{tag} {k} {a} {rf} TL431_B vref={vref}')
            prov = f'behavioural TL431 (Vref {vref} V; datasheet 2.495 V +-1 % for TL431A)'
    elif m == 'npn':
        e, b, c = (nodes.get(card.pin_by_func(ref, x), '0') for x in 'EBC')
        name, pins, kind, prov = reg.vendor_or_fallback(p['vendor'], p['fallback'])
        if kind == 'subckt':
            lines.append(f'X{tag} {" ".join({"C": c, "B": b, "E": e}[x] for x in pins)} {name}')
        else:
            lines.append(f'Q{tag} {c} {b} {e} {name}')
    elif m == 'fuse':
        lines.append(f'R{tag} {nodes["1"]} {nodes["2"]} {p["r_cold"]:.6g}')
    elif m == 'ptc':
        r = ctx.part_params.get(f'{card.name}:{ref}', {}).get('r', p['rmin'] * 1.5)
        lines.append(f'R{tag} {nodes["1"]} {nodes["2"]} {r:.6g}')
    elif m == 'buck':
        vin, gnd, vout = (nodes[card.pin_by_func(ref, x)] for x in ('IN', 'GND', 'OUT'))
        lines += buck(tag, vin, gnd, vout, p, ctx)
    elif m == 'relay':
        lines += relay(tag, card, ref, nodes, p, ctx, reg)
    elif m == 'uln2003':
        lines += uln2003(tag, card, ref, nodes, p, ctx, reg)
    elif m == 'stepstick':
        lines += ctx.stepstick(card, ref, nodes, p, reg)
    elif m == 'devkit':
        lines += ctx.devkit(card, ref, nodes, p, reg)
    else:
        raise KeyError(f'no emitter for model {m}')
    reg.provenance.setdefault(tag, prov)
    return lines


def _smin(a, b, eps):
    return f'(0.5*(({a})+({b})-sqrt((({a})-({b}))^2+{eps}^2)))'


def _smax(a, b, eps):
    return f'(0.5*(({a})+({b})+sqrt((({a})-({b}))^2+{eps}^2)))'


def buck(tag, vin, gnd, vout, p, ctx):
    """Behavioural Murata OKI-78SR: UVLO, soft-start, dropout, constant-efficiency input current.
    Output dynamics: L_out with damping R in parallel, sized so a 0.5 A load step gives ~0.15-0.2 V deviation
    (datasheet dynamic load response 150-225 mV for a 50 % step)."""
    vset = p['vout'] * ctx.buck_vmult(tag)
    tss = p['tss']
    eta = p['eta']
    lo, rd = p.get('l_out', 5e-6), p.get('r_damp', 0.5)
    vexpr = _smin(f'{vset:.4f}*V({tag}_ss,{gnd})', _smax(f'V({vin},{gnd})-{p["vdrop"]:.3f}', '0', 0.05), 0.05)
    iexpr = _smax(f'V({vout},{gnd})*I(V{tag}s)', '0', 0.01) + f'/({eta}*' + _smax(f'V({vin},{gnd})', '4', 0.2) + ')'
    return [
        f'* {tag}: behavioural OKI-78SR buck (vset {vset:.3f} V, eta {eta}, UVLO {p["vin_on"]} V assumed, Lout {lo} H)',
        f'C{tag}in {vin} {gnd} {p["cin"]:.4g}',
        f'B{tag}en {tag}_en0 {gnd} V=0.5*(1+tanh((V({vin},{gnd})-{(p["vin_on"] + p["vin_off"]) / 2:.3f})/0.15))',
        f'R{tag}ss {tag}_en0 {tag}_ss 1k',
        f'C{tag}ss {tag}_ss {gnd} {tss / 1e3 / 2.0:.4g}',
        f'B{tag}o {tag}_o {gnd} V={vexpr}',
        f'R{tag}o {tag}_o {tag}_l 0.03',
        f'L{tag}o {tag}_l {tag}_s {lo}', f'R{tag}d {tag}_l {tag}_s {rd}',
        f'V{tag}s {tag}_s {vout} 0',
        f'C{tag}out {vout} {gnd} {p["cout"]:.4g}',
        f'B{tag}in {vin} {gnd} I={iexpr}',
    ]


def relay(tag, card, ref, nodes, p, ctx, reg):
    """Omron G2RL-2: coil R-L (R at bay temperature), contacts switched by coil current with hysteresis.
    Mechanical operate/release delays are NOT in SPICE (python event model adds them)."""
    t = ctx.corner.get('temp_C', 40.0)
    rc = p['r_coil'] * (1 + 0.00393 * (t - 23.0))
    L = p['L'][ctx.idx('relay_L')] if isinstance(p['L'], list) else p['L']
    iop = p['op_frac'] * 12.0 / rc
    irel = p['rel_frac'] * 12.0 / rc
    rcont = p['r_contact'][ctx.idx('contact')]
    n = lambda pin: nodes.get(pin, f'{tag}_nc{pin}')
    vt, vh = (iop + irel) / 2 * 1e3, (iop - irel) / 2 * 1e3
    lines = [f'* {tag}: G2RL-2 behavioural, Rcoil {rc:.1f} ohm at {t} C, L {L} H (assumed), Iop {iop*1e3:.1f} mA, Irel {irel*1e3:.1f} mA',
             f'L{tag}c {n("A1")} {tag}_cx {L}', f'R{tag}c {tag}_cx {tag}_cs {rc:.2f}', f'V{tag}c {tag}_cs {n("A2")} 0',
             f'H{tag}ctl {tag}_ctl 0 V{tag}c 1000',
             f'.model SW_{tag}_NO SW(VT={vt:.4f} VH={vh:.4f} RON={rcont} ROFF=1e8)',
             f'.model SW_{tag}_NC SW(VT={vt * 0.95:.4f} VH={vh * 0.95:.4f} RON=1e8 ROFF={rcont})']
    for pole in ('1', '2'):
        com, nc, no = f'{pole}1', f'{pole}2', f'{pole}4'
        if no in nodes:
            lines.append(f'S{tag}{no} {n(com)} {n(no)} {tag}_ctl 0 SW_{tag}_NO')
        if nc in nodes:
            lines.append(f'S{tag}{nc} {n(com)} {n(nc)} {tag}_ctl 0 SW_{tag}_NC')
    return lines


def uln2003(tag, card, ref, nodes, p, ctx, reg):
    name, pins, kind, prov = reg.vendor_or_fallback(p['vendor'], 'QDARL1_B')
    if name == 'QDARL1_B':
        for k in ('QDARL2_B', 'DULNCLAMP_B', 'DSUB_B'):
            reg.need(k)
        reg.subckt('ULN2003A_CH_B', ULN_B)
        reg.provenance[tag] = 'behavioural ULN2003A channel (2.7k/7.2k/3k Darlington per TI schematic; fitted VCE(sat))'
    gnd = nodes[card.pin_by_func(ref, 'GND')]
    com = nodes.get(card.pin_by_func(ref, 'COM'), f'{tag}_com')
    lines = []
    for ch in range(1, 8):
        i_pin, o_pin = card.pin_by_func(ref, f'I{ch}'), card.pin_by_func(ref, f'O{ch}')
        if o_pin is None or o_pin not in nodes:
            continue
        i_node = nodes.get(i_pin, f'{tag}_i{ch}')
        if name == 'QDARL1_B':
            lines.append(f'X{tag}_{ch} {i_node} {nodes[o_pin]} {com} {gnd} ULN2003A_CH_B')
        else:
            mapping = {'IN': i_node, 'OUT': nodes[o_pin], 'COM': com, 'GND': gnd}
            lines.append(f'X{tag}_{ch} {" ".join(mapping[x] for x in pins)} {name}')
            reg.provenance[tag] = prov
    return lines
