"""Assemble a SPICE circuit from the exported card netlists, the part-model table and the harness."""
from . import harness as H
from . import models as M
from .netlist import spice_node

IDX = {'min': 0, 'nom': 1, 'max': 2}


def smin(a, b, eps):
    """Smooth min for B-source expressions (continuous derivative; error <= eps/2)."""
    return f'(0.5*(({a})+({b})-sqrt((({a})-({b}))^2+{eps}^2)))'


def smax(a, b, eps):
    return f'(0.5*(({a})+({b})+sqrt((({a})-({b}))^2+{eps}^2)))'


class Ctx:
    """Scenario context: corner choices, tolerances, waveforms for modules and logic outputs."""

    def __init__(self, corner=None, **kw):
        self.corner = dict(corner or {})
        self.part_params = kw.get('part_params', {})       # 'card:ref' -> params override
        self.esr_override = kw.get('esr_override', {})     # 'card:ref' -> ESR or None (omit part)
        self.tol = kw.get('tol', {})                       # 'card:ref' -> multiplier (MC)
        self.gpio = kw.get('gpio', {})                     # 'IO32' -> PWL text of 0..1 control
        self.esp_load = kw.get('esp_load', 'DC 0.08')      # 3V3 load inside the DevKit (ESP32 module)
        self.ldo = kw.get('ldo', {})                       # DevKit LDO params override
        self.logic_drive = kw.get('logic_drive', {})       # 'U2.1Q' -> PWL text 0..1
        self.stepper = kw.get('stepper', None)             # SPICE current-source spec on VMOT
        self.buck_vm = kw.get('buck_vmult', {})            # 'pwr_U1' -> setpoint multiplier
        self.boot_pulls = kw.get('boot_pulls', True)
        self.usb_vbus = kw.get('usb_vbus', None)           # volts at DevKit USB VBUS (None = unplugged)
        self.no_vendor = set(kw.get('no_vendor', ()))        # vendor model keys to replace by behavioural fallbacks
        self.sense = set(kw.get('sense', ()))              # 'card:ref:pin' -> 0 V source between net and pin

    def idx(self, key):
        v = self.corner.get(key, 'nom')
        return IDX[v] if isinstance(v, str) else v

    def rmult(self, card, ref, tol):
        return self.tol.get(f'{card}:{ref}', 1.0)

    def cmult(self, card, ref, tol):
        return self.tol.get(f'{card}:{ref}', 1.0)

    def buck_vmult(self, tag):
        return self.buck_vm.get(tag, 1.0)

    # ---------------------------------------------------------------- TVS corners
    def tvs_model(self):
        return f'DP6KE30A_{self.corner.get("tvs_bv", "nom").upper()}'

    def tvs_text(self, name):
        """Behavioural P6KE30A fit: BV at 1 mA in [28.5, 31.5] V (datasheet), Vc 41.4 V at 14.5 A for the BV-max part,
        BV tempco +0.098 %/K (assumed P6KE class value) from 25 C to the bay temperature."""
        bv = {'MIN': 28.5, 'NOM': 30.0, 'MAX': 31.5}[name.split('_')[-1]]
        t = self.corner.get('temp_C', 40.0)
        bv_t = bv * (1 + 0.00098 * (t - 25.0))
        rs = (41.4 - 31.5 - 0.0257 * 9.6) / 14.5
        return (f'.model {name} D(IS=1e-11 N=1.5 RS={rs:.4f} BV={bv_t:.3f} IBV=1m NBV=1 CJO=2.5n M=0.33)',
                f'behavioural P6KE30A: BV(1 mA) {bv} V at 25 C -> {bv_t:.2f} V at {t} C, RS {rs:.3f} ohm from Vc 41.4 V @ 14.5 A')

    # ---------------------------------------------------------------- logic chips (SPICE stubs)
    def logic_stub(self, card, ref, comp, nodes, reg):
        vcc = nodes.get(card.pin_by_func(ref, 'VCC'))
        gnd = nodes.get(card.pin_by_func(ref, 'GND'))
        tag = f'{card.name}_{ref}'
        lines = [f'* {tag}: logic stub (outputs driven by scenario; Icc 20 uA)', f'R{tag}cc {vcc} {gnd} 165k']
        rout = self.corner.get('hc_rout', 70.0)
        for (r, pin), func in card.pin_func.items():
            if r != ref or pin not in nodes:
                continue
            node = nodes[pin]
            if func in ('VCC', 'GND') or node in (vcc, gnd):
                continue
            is_out = func[:2] in ('1Q', '2Q') or func.startswith('1~{Q}') or func.startswith('2~{Q}') or func.startswith('Q')
            key = f'{ref}.{func}'
            if is_out:
                ctl = self.logic_drive.get(key, 'DC 0')
                lines += [f'V{tag}_{pin}c {tag}_{pin}c 0 {ctl}',
                          f'B{tag}_{pin} {tag}_{pin}o {gnd} V=V({vcc},{gnd})*V({tag}_{pin}c)',
                          f'R{tag}_{pin} {tag}_{pin}o {node} {rout}']
            else:
                lines += [f'C{tag}_{pin} {node} {gnd} 3.5p']
        reg.provenance[tag] = 'logic: python event model; SPICE stub (Icc, output driver from scenario)'
        return lines

    # ---------------------------------------------------------------- StepStick
    def stepstick(self, card, ref, nodes, p, reg):
        tag = f'{card.name}_{ref}'
        vm = nodes[card.pin_by_func(ref, 'VMOT')]
        gnd = nodes[card.pin_by_func(ref, 'GND')]
        vdd = nodes.get(card.pin_by_func(ref, 'VDD'))
        bv = {'min': 31.1, 'nom': 32.7, 'max': 34.4}[self.corner.get('smf_bv', 'nom')]
        lines = [f'* {tag}: BTT TMC2209 V1.3 module (BTT schematic): VS 2 x 10 uF + 1 uF/1.1 ohm snubber + SMF28A TVS',
                 f'C{tag}vm {vm} {tag}_cx {p["c_vmot"]:.4g}', f'R{tag}vm {tag}_cx {gnd} 0.005',
                 f'C{tag}sn {vm} {tag}_sx 1u', f'R{tag}sn {tag}_sx {gnd} 1.1',
                 f'* SMF28A: VBR 31.1-34.4 V @ 1 mA, VC 45.4 V @ 4.4 A (typical SMF-series sheet values, not retrieved: ASSUMED)',
                 f'.model DSMF28A_{tag} D(IS=1e-12 N=1.5 RS=2.44 BV={bv} IBV=1m NBV=1 CJO=300p)',
                 f'D{tag}tvs {gnd} {vm} DSMF28A_{tag}',
                 f'B{tag}vdd {vdd} {gnd} I={p["i_vdd"]}*0.5*(1+tanh((V({vdd},{gnd})-2.0)/0.2))']
        if self.stepper:
            lines.append(f'I{tag}chop {vm} {gnd} {self.stepper}')
        reg.provenance[tag] = 'behavioural StepStick: VMOT capacitance + chopper current source (scenario)'
        return lines

    # ---------------------------------------------------------------- ESP32-DevKitC
    BOOT_PULL = {'IO0': ('up', 45e3), 'IO2': ('down', 45e3), 'IO12': ('down', 45e3), 'IO15': ('up', 45e3), 'IO5': ('up', 45e3)}

    def devkit(self, card, ref, nodes, p, reg):
        tag = f'{card.name}_{ref}'
        v5 = nodes[card.pin_by_func(ref, '5V')]
        v33 = nodes[card.pin_by_func(ref, '3V3')]
        gnd = nodes[card.pin_by_func(ref, 'GND')]
        ld = dict(vout=3.3, vdo0=0.95, kdo=0.25, iq=0.005, tau=3e-6, rout=0.02)
        ld.update(self.ldo)
        iout = smax(f'I(V{tag}s)', '0', 0.01)
        ldo_t = smax(smin(str(ld['vout']), f'V({v5},{gnd})-({ld["vdo0"]}+{ld["kdo"]}*{iout})', 0.02), '0', 0.02)
        lines = [f'* {tag}: ESP32-DevKitC-32E behavioural: {p["ldo"]} (dropout {ld["vdo0"]} V + {ld["kdo"]} V/A), ESP32 load',
                 f'C{tag}5 {v5} {tag}_c5 {p["c5v"]:.4g}', f'R{tag}5 {tag}_c5 {gnd} 0.01',
                 f'B{tag}t {tag}_t {gnd} V={ldo_t}',
                 f'R{tag}t {tag}_t {tag}_f 1', f'C{tag}t {tag}_f {gnd} {ld["tau"]:.3g}',
                 f'E{tag}o {tag}_o {gnd} {tag}_f {gnd} 1', f'R{tag}o {tag}_o {tag}_s {ld["rout"]}',
                 f'V{tag}s {tag}_s {v33} 0',
                 f'B{tag}in {v5} {gnd} I={iout}+{ld["iq"]}*0.5*(1+tanh((V({v5},{gnd})-1.0)/0.3))',
                 f'C{tag}33 {v33} {tag}_c33 {p["c3v3"]:.4g}', f'R{tag}33 {tag}_c33 {gnd} 0.01',
                 f'V{tag}espc {tag}_espc 0 {self.esp_load}',
                 f'B{tag}esp {v33} {gnd} I=V({tag}_espc)*0.5*(1+tanh((V({v33},{gnd})-2.2)/0.15))+V({v33},{gnd})/2e3']
        if self.usb_vbus is not None:
            lines += [f'V{tag}usb {tag}_vbus {gnd} {self.usb_vbus}', f'D{tag}usb {tag}_vbus {v5} D1N5819_B']
            reg.need('D1N5819_B')
        reg.need('DCLAMP_B')
        for (r, pin), func in card.pin_func.items():
            if r != ref or not func.startswith('IO') or pin not in nodes:
                continue
            node = nodes[pin]
            lines += [f'D{tag}_{func}h {node} {v33} DCLAMP_B', f'D{tag}_{func}l {gnd} {node} DCLAMP_B',
                      f'C{tag}_{func} {node} {gnd} 3p']
            if func in self.gpio:
                lines += [f'V{tag}_{func}c {tag}_{func}c 0 {self.gpio[func]}',
                          f'B{tag}_{func} {tag}_{func}o {gnd} V=V({v33},{gnd})*V({tag}_{func}c)',
                          f'R{tag}_{func} {tag}_{func}o {node} 40']
            elif self.boot_pulls and func in self.BOOT_PULL:
                d, rv = self.BOOT_PULL[func]
                lines.append(f'R{tag}_{func}pu {node} {v33 if d == "up" else gnd} {rv}')
        if 'IO0' in [card.pin_func[(ref, q)] for q in card.pins(ref)]:
            lines.append(f'* DevKit on-board 10k pull-up on IO0 (BOOT)')
            lines.append(f'R{tag}_boot {nodes[card.pin_by_func(ref, "IO0")]} {v33} 10k')
        reg.provenance[tag] = f'behavioural DevKitC: {p["ldo"]} dropout model, ESP32 load source, GPIO 40 ohm drivers + clamps'
        return lines


class Circuit:
    def __init__(self, cards, harness, ctx, table=None):
        self.cards, self.h, self.ctx = cards, harness, ctx
        self.table = table or M.load_table()
        self.reg = M.Registry()
        self.reg.no_vendor = set(getattr(ctx, 'no_vendor', ()))
        self.lines = []
        self.included = []
        self.ground = None
        self.unmapped = []
        self.skipped_leads = []

    def node(self, card, net):
        if net == 'GND' and card == self.ground:
            return '0'
        return spice_node(card, net)

    def add_cards(self, names, exclude=(), ground='pwr'):
        self.ground = ground if ground in names else names[0]
        for cname in names:
            card = self.cards[cname]
            self.included.append(cname)
            self.lines.append(f'* ---------------- card {cname} ({card.source})')
            for ref, comp in sorted(card.comps.items()):
                if ref in exclude or f'{cname}:{ref}' in exclude:
                    continue
                row = M.match(self.table, comp)
                if row is None:
                    self.unmapped.append(f'{cname}:{ref} ({comp["mpn"] or comp["value"]})')
                    continue
                nodes = {p: self.node(cname, n) for p, n in card.pins(ref).items()}
                for p in list(nodes):
                    if f'{cname}:{ref}:{p}' in self.ctx.sense:
                        s = f'{nodes[p]}_s_{ref}_{p}'
                        self.lines.append(f'Vsense_{cname}_{ref}_{p} {nodes[p]} {s} 0')
                        nodes[p] = s
                self.lines += M.emit(card, ref, comp, row, nodes, self.ctx, self.reg)
        return self

    def lead(self, name, corner=None, temp_c=None, tap=False):
        """Emit one lead. Inter-card leads join card nodes; external leads end at ext_<lead>_<pin> nodes.
        Returns {pin: far-end node} for external leads."""
        lead = self.h['leads'][name]
        corner = corner or self.ctx.corner
        cp = H.conductor(self.h, name, corner, temp_c if temp_c is not None else self.ctx.corner.get('temp_C', 40.0))
        a_card, a_ref = lead['a']
        card = self.cards[a_card]
        pins_a = card.pins(a_ref)
        if not pins_a:
            self.lines.append(f'* lead {name}: connector {a_card} {a_ref} not in this design - skipped')
            self.skipped_leads.append(name)
            return {}, cp
        inter = isinstance(lead['b'], list)
        far = {}
        if inter:
            b_card, b_ref = lead['b']
            pins_b = self.cards[b_card].pins(b_ref)
        gnd_a = self.node(a_card, 'GND')
        gnd_b = self.node(lead['b'][0], 'GND') if inter else f'ext_{name}_gnd'
        self.lines.append(f'* lead {name}: {cp["length"]:.3f} m, R {cp["R"]*1e3:.1f} mOhm/conductor '
                          f'(wire {cp["R_wire"]*1e3:.1f} + contacts {cp["R_contact"]*1e3:.1f}), L {cp["L"]*1e9:.0f} nH, C {cp["C"]*1e12:.0f} pF')
        gnd_far = None
        for pin, na in sorted(pins_a.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            a = self.node(a_card, na)
            if inter:
                nb = pins_b.get(pin)
                if nb is None:
                    continue
                b = self.node(lead['b'][0], nb)
            else:
                b = f'ext_{name}_{pin}'
                far[pin] = b
                if na == 'GND':
                    gnd_far = b
            t = f'{name}_{pin}'
            if tap and len(lead['segments']) > 1:
                # card-side segment (last) ends at the tap node (e.g. the inlet socket), the rest runs on to the far end
                segl = [H.pick(sg['length_m'], corner.get('length', 'nom')) for sg in lead['segments']]
                f = segl[-1] / sum(segl)
                tp = f'ext_{name}_{pin}_tap'
                cp.setdefault('tap', {})[pin] = tp
                self.lines += [f'R{t}a {a} {t}_ma {cp["R"] * f:.5g}', f'L{t}a {t}_ma {tp} {max(cp["L"] * f, 1e-12):.4g}',
                               f'R{t} {tp} {t}_m {cp["R"] * (1 - f):.5g}', f'L{t} {t}_m {b} {max(cp["L"] * (1 - f), 1e-12):.4g}']
            else:
                self.lines += [f'R{t} {a} {t}_m {cp["R"]:.5g}', f'L{t} {t}_m {b} {max(cp["L"], 1e-12):.4g}']
            if na != 'GND' and cp['C'] > 0:
                self.lines += [f'C{t}a {a} {gnd_a} {cp["C"] / 2:.4g}',
                               f'C{t}b {b} {gnd_b if inter else (gnd_far or gnd_a)} {cp["C"] / 2:.4g}']
        return far, cp

    def add(self, *lines):
        self.lines += list(lines)

    def text(self):
        t = self.ctx.corner.get('temp_C', 40.0)
        return f'.temp {t}\n' + self.reg.text() + '\n' + '\n'.join(self.lines)
