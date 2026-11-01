"""S10 - Steady-state power budget and part / copper temperatures at a 40 C bay (ngspice operating points + IPC-2152).

Two operating points on the full system: steady cooling (TEC 2S2P at 3.2 A) and pull-down (5 A) with the stepper
running, both fans, K1 energised, ESP32 at its Wi-Fi average. Every resistor, diode, transistor and regulator in
the netlist is evaluated from the simulated voltages/currents; high-current copper uses the routed tracks.
"""
import re

import numpy as np

from d34sim import common, ext, flows, logic, models as M, pcb, report
from d34sim.circuit import Ctx
from d34sim.netlist import spice_node

TITLE = 'Power budget, per-part dissipation and junction / copper temperatures at 40 C'

BAY = 40.0
ETA_DPS = 0.90   # DPS5005 efficiency not published: assumed (input = output / 0.9)


def run(env):
    chk = report.Checks('s10_power_thermal', env.outdir('s10_power_thermal'))
    L = env.limit
    N, R = flows.names(env)
    ro = flows.Roles(env)
    P, probs = logic.extract(env)
    u2, u3 = P['refs']['hc123'], P['refs']['hc573']
    tp = ext.tec_params()
    cards = env.cards
    # sense every two-terminal semiconductor / regulator / fuse so its current is known
    sense, parts = [], []
    for cname, card in cards.items():
        for ref, comp in card.comps.items():
            row = M.match(env.table, comp)
            if row is None:
                continue
            m = row['model']
            pin = None
            if m in ('diode', 'led'):
                pin = card.pin_by_func(ref, 'A')
            elif m in ('pmos', 'nmos'):
                pin = card.pin_by_func(ref, 'D')
            elif m == 'npn':
                pin = card.pin_by_func(ref, 'C')
            elif m in ('fuse', 'ptc'):
                pin = '1'
            elif m == 'buck':
                pin = card.pin_by_func(ref, 'OUT')
            elif m == 'devkit':
                pin = card.pin_by_func(ref, '5V')
            elif m == 'relay':
                pin = 'A1'
            if pin and pin in card.pins(ref):
                sense.append(f'{cname}:{ref}:{pin}')
                parts.append((cname, ref, m, pin))
    I = {s: 'i(vsense_' + s.replace(':', '_').lower() + ')' for s in sense}
    nd = lambda cname, net: spice_node(cname, net).lower() if not (net == 'GND' and cname == 'pwr') else '0'
    vnodes = set()
    for cname, card in cards.items():
        for ref in card.comps:
            for p, net in card.pins(ref).items():
                vnodes.add(nd(cname, net))
    vnodes.discard('0')
    vnodes = sorted(vnodes)
    vecs = list(I.values()) + [f'v({x})' for x in vnodes] + ['v(dpso_p,dpso_n)', 'v(ext_dps_in_1,ext_dps_in_2)']
    ops = {'steady': tp['steady'], 'pull-down': tp['pulldown']}
    results = {}
    for name, (i_tec, dT) in ops.items():
        v_out = i_tec * tp['R_hot'] + 2 * tp['alpha_V_K'] * dT + 0.6
        p_in = v_out * i_tec / ETA_DPS
        vm_nom = 12.0 if N['vmot'] == N['v12'] else 24.0
        i_step = (2 * 1.0 ** 2 * 3.7 + 1.0) / vm_nom   # stepper running: 2 phases x 1 A in 3.7 ohm + ~1 W driver loss, from VMOT

        fan_gpio = {}
        dkr = ro.model_refs('ctrl', 'devkit')[0]
        io_of = {net: cards['ctrl'].pin_func[(dkr, p_)] for p_, net in cards['ctrl'].pins(dkr).items()}
        for fr in ro.model_refs('tec', 'nmos'):
            g_net = cards['tec'].net(fr, cards['tec'].pin_by_func(fr, 'G'))
            if g_net in io_of:
                fan_gpio[io_of[g_net]] = 'DC 1'     # blower / spare channel switched on

        def make(nv):
            ctx = Ctx(dict(temp_C=BAY, contact='nom', esr='nom'), no_vendor=nv, sense=sense, stepper=f'DC {i_step:.4f}', gpio=fan_gpio,
                      esp_load='DC 0.24', logic_drive={f'{u2}.1Q': 'DC 1', f'{u2}.1~{{Q}}': 'DC 0', f'{u3}.Q1': 'DC 0'})
            return common.build(env, ctx, brick=dict(v=24.0, t_close=None, ilim=10.0),
                                dps_in=dict(c_in=470e-6, esr=0.05, p_load=p_in, t_on=5e-3),
                                dps_out=dict(vset=21.0, ilim=i_tec, c_out=470e-6, esr=0.05),
                                tec=dict(dT=dT, R=tp['R_hot'], alpha=tp['alpha_V_K']),
                                fans={'FAN1': dict(i_run=0.14), 'FAN2': dict(i_run=ext.externals()['blower']['i_A'], pwm_pullup_v=0.0)})
        txt = make(set())[0].text().lower()
        vecs = [v for v in vecs if not v.startswith('v(') or ',' in v or re.search(r'[\s(]' + re.escape(v[2:-1]) + r'[\s)]', txt)]
        c, info, r = common.run_robust(make, f's10_{name}', vecs, 'tran 50u 60m 0 50u', chk)
        last = {k: float(np.mean(v[-20:])) for k, v in r.items() if not k.startswith('_') and k != 'time'}
        results[name] = (last, p_in, i_tec)
    # ---------------------------------------------------------------- per-part dissipation
    rows = []
    vget = lambda last, cname, net: 0.0 if nd(cname, net) == '0' else last.get(f'v({nd(cname, net)})', float('nan'))
    for name, (last, p_in, i_tec) in results.items():
        brick_i = abs(last[I[f'pwr:{R["q"]}:{R["qd"]}']])
        rows.append(dict(op=name, part='BRICK', what='input', I_A=brick_i, P_W=24.0 * brick_i, limit=L('brick_power')[0], T_C=np.nan))
        for cname, ref, m, pin in parts:
            card = cards[cname]
            i = last[I[f'{cname}:{ref}:{pin}']]
            pins = card.pins(ref)
            mpn = card.comps[ref]['mpn']
            if m in ('diode', 'led'):
                va = vget(last, cname, pins[card.pin_by_func(ref, 'A')])
                vk = vget(last, cname, pins[card.pin_by_func(ref, 'K')])
                p = max(i, 0) * (va - vk) + max(-i, 0) * (vk - va)
                rth = 80.0 if mpn.startswith('1N58') else 75.0 if 'P6KE' in mpn else 200.0
                rows.append(dict(op=name, part=f'{cname}:{ref}', what=mpn, I_A=i, P_W=p, T_C=BAY + p * rth, limit=125.0))
            elif m in ('pmos', 'nmos'):
                vd = vget(last, cname, pins[card.pin_by_func(ref, 'D')])
                vs = vget(last, cname, pins[card.pin_by_func(ref, 'S')])
                p = abs(i * (vd - vs))
                rows.append(dict(op=name, part=f'{cname}:{ref}', what=mpn, I_A=i, P_W=p, T_C=BAY + p * L('irf4905_rth_ja')[0], limit=125.0))
            elif m == 'npn':
                vc = vget(last, cname, pins[card.pin_by_func(ref, 'C')])
                ve = vget(last, cname, pins[card.pin_by_func(ref, 'E')])
                p = abs(i * (vc - ve))
                rows.append(dict(op=name, part=f'{cname}:{ref}', what=mpn, I_A=i, P_W=p, T_C=BAY + p * 200.0, limit=125.0))
            elif m in ('fuse', 'ptc'):
                p = abs(i * (vget(last, cname, pins['1']) - vget(last, cname, pins['2'])))
                rows.append(dict(op=name, part=f'{cname}:{ref}', what=mpn, I_A=abs(i), P_W=p, T_C=np.nan, limit=np.nan))
            elif m == 'buck':
                vin = vget(last, cname, pins[card.pin_by_func(ref, 'IN')])
                vo = vget(last, cname, pins[card.pin_by_func(ref, 'OUT')])
                eta = M.match(env.table, card.comps[ref])['params']['eta']
                po = vo * abs(i)
                rows.append(dict(op=name, part=f'{cname}:{ref}', what=mpn, I_A=abs(i), P_W=po * (1 / eta - 1), T_C=np.nan,
                                 limit=M.match(env.table, card.comps[ref])['params']['iout_max']))
            elif m == 'devkit':
                v5 = vget(last, cname, pins[card.pin_by_func(ref, '5V')])
                v33 = vget(last, cname, pins[card.pin_by_func(ref, '3V3')])
                p = (v5 - v33) * abs(i)
                rows.append(dict(op=name, part=f'{cname}:{ref} AMS1117', what='DevKit LDO', I_A=abs(i), P_W=p, T_C=BAY + 15 + p * 90.0, limit=125.0))
            elif m == 'relay':
                va1 = vget(last, cname, pins['A1'])
                va2 = vget(last, cname, pins['A2'])
                rows.append(dict(op=name, part=f'{cname}:{ref} coil', what=mpn, I_A=abs(i), P_W=abs(i * (va1 - va2)), T_C=np.nan, limit=np.nan))
        # resistors
        for cname, card in cards.items():
            for ref, comp in card.comps.items():
                row = M.match(env.table, comp)
                if row is None or row['model'] != 'resistor':
                    continue
                pins = card.pins(ref)
                if '1' not in pins or '2' not in pins:
                    continue
                dv = vget(last, cname, pins['1']) - vget(last, cname, pins['2'])
                rows.append(dict(op=name, part=f'{cname}:{ref}', what=f"resistor {comp['value']}", I_A=dv / M.parse_value(comp['value']),
                                 P_W=dv * dv / M.parse_value(comp['value']), T_C=np.nan, limit=L('resistor_p')[0]))
        # ULN2003: sum of channel dissipations from output voltages and load currents
        if ro.model_refs('tec', 'uln2003'):
            uln = ro.model_refs('tec', 'uln2003')[0]
            tec = cards['tec']
            p_uln = 0.0
            for k in ('K1', 'K2'):
                kr = P['chain'][k]['relay']
                ic = abs(last[I[f'tec:{kr}:A1']])
                p_uln += ic * vget(last, 'tec', P['chain'][k]['coil_lo'])
            p_uln += 0.11 * 1.0   # FAN2 channel at ~0.11 A x ~1 V (DC on)
            rows.append(dict(op=name, part=f'tec:{uln}', what='ULN2003AN (K1, K2, FAN2)', I_A=np.nan, P_W=p_uln,
                             T_C=BAY + p_uln * L('uln2003_rth_ja')[0], limit=L('uln2003_tj_max')[0]))
    chk.csv('dissipation.csv', rows)
    # ---------------------------------------------------------------- checks
    for name, (last, p_in, i_tec) in results.items():
        sub = [r_ for r_ in rows if r_['op'] == name]
        b = [r_ for r_ in sub if r_['part'] == 'BRICK'][0]
        chk.add(f'brick_{name}', f'{name}: brick input power vs the >=150 W / GST160A24 rating', b['P_W'], L('brick_power')[0], '<=', 'W',
                L('brick_power')[1], severity='functional', detail=f"{b['I_A']:.2f} A at 24 V; DPS input {p_in:.0f} W (DPS efficiency 90 % assumed)")
        semis = [r_ for r_ in sub if np.isfinite(r_.get('T_C', np.nan))]
        hot = max(semis, key=lambda x: x['T_C'])
        chk.add(f'tj_{name}', f'{name}: hottest semiconductor junction estimate (P x RthJA + 40 C bay)', hot['T_C'], L('tj_margin')[0], '<=', 'C',
                L('tj_margin')[1], corner=f"{hot['part']} {hot['what']} {hot['P_W']:.2f} W")
        res = max((r_ for r_ in sub if r_['what'].startswith('resistor')), key=lambda x: x['P_W'])
        chk.add(f'resistor_{name}', f'{name}: highest resistor dissipation', res['P_W'], L('resistor_p')[0] * 0.5, '<=', 'W',
                L('resistor_p')[1] + ' (project: <= 50 % of rating)', corner=res['part'])
        for r_ in sub:
            if r_['what'].startswith('OKI') or r_['what'].startswith('TSR'):
                chk.add(f"reg_{name}_{r_['part'].split(':')[1]}", f"{name}: {r_['what']} output current vs rating", r_['I_A'], r_['limit'], '<=', 'A',
                        'regulator rating (part_models.csv / datasheet); TSR 2 full load to ~55 C, TSR 1 to ~45-68 C', severity='rating')
        for pr in [r_ for r_ in sub if 'RXEF' in r_['what']]:
            cname_, ref_ = pr['part'].split(':')
            prm = M.match(env.table, cards[cname_].comps[ref_])['params']
            for tb in (40, 50):
                v = prm.get(f'hold_{tb}C')
                if v:
                    chk.add(f'ptc_hold_{name}_{ref_}_{cname_}_{tb}', f'{name}: {pr["part"]} {pr["what"]} current vs its hold current at {tb} C '
                            '(nuisance-trip margin)', pr['I_A'], v, '<=', 'A', f'Littelfuse {pr["what"]} hold vs ambient table', severity='functional')
        f1 = [r_ for r_ in sub if r_['what'] == '3568']
        if f1:
            v, s = L('fuse_continuous_fraction')
            chk.add(f'f1_cont_{name}', f'{name}: F1 continuous current vs 75 % of the 98 %-rerated 7.5 A', f1[0]['I_A'], 7.5 * 0.98 * v, '<=', 'A', s,
                    severity='functional')
        d_or = [r_ for r_ in sub if r_['part'] == f"ctrl:{R['d_oring']}"]
        if d_or:
            chk.note(f"{name}: ESP32 OR-ing diode {d_or[0]['what']} carries {d_or[0]['I_A'] * 1e3:.0f} mA, {d_or[0]['P_W'] * 1e3:.0f} mW.")
    # ---------------------------------------------------------------- copper at pull-down
    boards = {c: pcb.load(env.d34 / f'd34-{c}' / f'd34-{c}.kicad_pcb') for c in ('pwr', 'tec')}
    pads = {c: pcb.pads(env.d34 / f'd34-{c}' / f'd34-{c}.kicad_pcb') for c in boards}
    last, p_in, i_tec = results['pull-down']
    i_dps = p_in / last['v(ext_dps_in_1,ext_dps_in_2)']
    pc = cards['pwr']
    loads = {}
    for ref in ro.model_refs('pwr', 'buck'):
        pin = pc.pin_by_func(ref, 'IN')
        if pc.net(ref, pin) == pc.net(R['f2'], '2'):
            vo = vget(last, 'pwr', pc.net(ref, pc.pin_by_func(ref, 'OUT')))
            io_ = abs(last[I[f'pwr:{ref}:{pc.pin_by_func(ref, "OUT")}']])
            loads[ref] = (pin, vo * io_ / M.match(env.table, pc.comps[ref])['params']['eta'] / vget(last, 'pwr', pc.net(ref, pin)))
    ss = R['ss']
    if pc.net(ss, pc.pin_by_func(ss, 'VMOT')) == pc.net(R['f2'], '2'):
        loads[ss] = (pc.pin_by_func(ss, 'VMOT'), (2 * 3.7 + 1.0) / 24.0)
    crow = []
    paths = [(p, 'front end') for p in flows.front_paths(ro, i_dps, loads)] + [(p, 'TEC path') for p in flows.tec_paths(ro, i_tec)]
    for (board, net, inj), lab in paths:
        segs, missing, vias_i = pcb.solve_net(boards[board], pads[board], net, inj)
        if not segs:
            continue
        hot = max(segs, key=lambda x: x['dT'])
        crow.append(dict(path=lab, board=board, net=net, i_seg=hot['i'], width_mm=hot['width_mm'], layer=hot['layer'], dT=hot['dT'],
                         x=round(hot['start'][0] - 50, 2), y=round(hot['start'][1] - 50, 2), max_via_A=max(vias_i) if vias_i else 0.0,
                         R_mohm=pcb.track_r_mohm(boards[board], net), missing=str(missing) if missing else ''))
    chk.csv('copper_pulldown.csv', crow)
    v, s = L('track_dT_normal')
    w = max(crow, key=lambda x: x['dT'])
    chk.add('copper_pulldown', 'Pull-down (5 A TEC, ~4.4 A DPS input): hottest routed copper segment (IPC-2152 fit, nodal current split)', w['dT'],
            v, '<=', 'K', s, corner=f"{w['board']} {w['net']} {w['layer']} {w['width_mm']} mm at ({w['x']},{w['y']}), {w['i_seg']:.2f} A")
    chk.note(f'DPS5005 efficiency {ETA_DPS} is an assumption (not published). Junction temperatures use datasheet RthJA in still air at a 40 C bay '
             '(PCB copper and enclosure airflow ignored); AMS1117 includes +15 K for the DevKit board/ESP32 neighbourhood (estimate).')
    return chk
