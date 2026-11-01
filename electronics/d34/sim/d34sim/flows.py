"""Current paths through the routed copper, located from the netlist by part role (not by hard-coded refs),
so a re-annotated or re-routed design is followed automatically. Each path is a list of
(board, net, {(ref, pin): injected current}) for pcb.solve_net."""
from . import models as M


class Roles:
    def __init__(self, env):
        self.env, self.cards, self.h = env, env.cards, env.harness
        self.table = env.table

    def model_refs(self, card, model):
        c = self.cards[card]
        return [r for r, comp in sorted(c.comps.items()) if (M.match(self.table, comp) or {}).get('model') == model]

    def lead_conn(self, lead):
        return tuple(self.h['leads'][lead]['a'])

    def pin_on(self, card, ref, net):
        return sorted(p for p, n in self.cards[card].pins(ref).items() if n == net)

    def pins_by_func(self, card, ref, func):
        c = self.cards[card]
        return c.pin_by_func(ref, func)

    # ---------------------------------------------------------------- roles
    def front_end(self):
        c = self.cards['pwr']
        _, jb = self.lead_conn('BRICK')
        vin = c.net(jb, '1')
        q = [r for r in self.model_refs('pwr', 'pmos') if c.net(r, c.pin_by_func(r, 'D')) == vin][0]
        v24 = c.net(q, c.pin_by_func(q, 'S'))
        f1 = self.model_refs('pwr', 'fuse')[0]
        f2 = self.model_refs('pwr', 'ptc')[0]
        _, jd = self.lead_conn('DPS_IN')
        return dict(jb=jb, vin=vin, q=q, qd=c.pin_by_func(q, 'D'), qs=c.pin_by_func(q, 'S'), v24=v24, f1=f1, f2=f2,
                    v24dps=c.net(f1, '2'), vmot=c.net(f2, '2'), jd=jd)

    def bucks(self):
        c = self.cards['pwr']
        out = {}
        for r in self.model_refs('pwr', 'buck'):
            row = M.match(self.table, c.comps[r])
            out[row['params']['vout']] = r
        return out

    def relays(self):
        """K1 = relay whose contacts touch the DPS OUT+ net; K2 = the other."""
        c = self.cards['tec']
        _, jo = self.lead_conn('DPS_OUT')
        outp = c.net(jo, '1')
        outn = c.net(jo, '4')
        ks = self.model_refs('tec', 'relay')
        k1 = [k for k in ks if outp in c.pins(k).values()][0]
        k2 = [k for k in ks if k != k1][0]
        return dict(k1=k1, k2=k2, outp=outp, outn=outn, jo=jo, jt=self.lead_conn('TEC')[1])


def split(pins, total):
    return {p: total / len(pins) for p in pins}


def tec_paths(ro, current, defrost=False):
    """DPS output -> K1 (two poles in series) -> K2 -> TEC array 2S2P -> K2 -> DPS OUT-."""
    c = ro.cards['tec']
    R = ro.relays()
    k1, k2, jo, jt = R['k1'], R['k2'], R['jo'], R['jt']
    paths = []
    p_in = ro.pin_on('tec', jo, R['outp'])
    k1_in = ro.pin_on('tec', k1, R['outp'])[0]
    paths.append(('tec', R['outp'], {**{(jo, p): current / len(p_in) for p in p_in}, (k1, k1_in): -current}))
    # K1 internal series: pole 2 NO -> pole 1 COM (net between the poles)
    mid = c.net(k1, '24')
    paths.append(('tec', mid, {(k1, '24'): current, (k1, '11'): -current}))
    tecp = c.net(k1, '14')
    # K2: de-energised NC contacts (12, 22); energised NO (14, 24)
    a_net, b_net = c.net(k2, '11'), c.net(k2, '21')
    if not defrost:
        paths.append(('tec', tecp, {(k1, '14'): current, (k2, '12'): -current}))
        drive, ret = a_net, b_net
        k2_out, k2_ret = '11', '21'
        paths.append(('tec', R['outn'], {(k2, '22'): current, **{(jo, p): -current / 3 for p in ro.pin_on('tec', jo, R['outn'])}}))
    else:
        paths.append(('tec', tecp, {(k1, '14'): current, (k2, '24'): -current}))
        drive, ret = b_net, a_net
        k2_out, k2_ret = '21', '11'
        paths.append(('tec', R['outn'], {(k2, '14'): current, **{(jo, p): -current / 3 for p in ro.pin_on('tec', jo, R['outn'])}}))
    dp = ro.pin_on('tec', jt, drive)
    rp = ro.pin_on('tec', jt, ret)
    paths.append(('tec', drive, {(k2, k2_out): current, **{(jt, p): -current / len(dp) for p in dp}}))
    paths.append(('tec', ret, {**{(jt, p): current / len(rp) for p in rp}, (k2, k2_ret): -current}))
    return paths


def front_paths(ro, i_dps, i_aux_by_load):
    """Brick inlet -> Q1 -> +24V -> F1 -> DPS input; +24V -> F2 -> VMOT loads {ref: (pin, current)}."""
    F = ro.front_end()
    i_tot = i_dps + sum(i for _, i in i_aux_by_load.values())
    i_aux = i_tot - i_dps
    paths = [('pwr', F['vin'], {(F['jb'], '1'): i_tot, (F['q'], F['qd']): -i_tot}),
             ('pwr', F['v24'], {(F['q'], F['qs']): i_tot, (F['f1'], '1'): -i_dps, (F['f2'], '1'): -i_aux})]
    if i_dps > 0:
        paths.append(('pwr', F['v24dps'], {(F['f1'], '2'): i_dps, (F['jd'], '1'): -i_dps}))
    if i_aux > 0:
        inj = {(F['f2'], '2'): i_aux}
        for ref, (pin, i) in i_aux_by_load.items():
            inj[(ref, pin)] = inj.get((ref, pin), 0.0) - i
        paths.append(('pwr', F['vmot'], inj))
    return paths


def names(env):
    """Role -> SPICE node name (lower case, as ngspice reports vectors) and role -> (card, ref) map.
    Derived from the netlist so net renames (e.g. VMOT -> VAUX) are followed automatically."""
    from .netlist import spice_node
    ro = Roles(env)
    c = env.cards
    F = ro.front_end()
    B = ro.bucks()
    n = lambda card, net: spice_node(card, net).lower()
    pc, cc, tc = c['pwr'], c['ctrl'], c['tec']
    ss = ro.model_refs('pwr', 'stepstick')[0]
    dk = ro.model_refs('ctrl', 'devkit')[0]
    tvs = [r for r in ro.model_refs('pwr', 'diode') if 'P6KE' in pc.comps[r]['mpn']][0]
    d_or = [r for r in ro.model_refs('ctrl', 'diode') if cc.net(r, cc.pin_by_func(r, 'K')) == cc.net(dk, cc.pin_by_func(dk, '5V'))][0]
    v12, v5 = pc.net(B[12.0], pc.pin_by_func(B[12.0], 'OUT')), pc.net(B[5.0], pc.pin_by_func(B[5.0], 'OUT'))
    _, j12t = env.harness['leads']['LINK_12V']['b']
    nets = dict(vin=n('pwr', F['vin']), v24=n('pwr', F['v24']), v24dps=n('pwr', F['v24dps']), aux=n('pwr', F['vmot']),
                vmot=n('pwr', pc.net(ss, pc.pin_by_func(ss, 'VMOT'))), v12=n('pwr', v12), v5=n('pwr', v5),
                q_g=n('pwr', pc.net(F['q'], pc.pin_by_func(F['q'], 'G'))),
                v5ctrl=n('ctrl', cc.net(d_or, cc.pin_by_func(d_or, 'A'))), v5dk=n('ctrl', cc.net(dk, cc.pin_by_func(dk, '5V'))),
                v3v3=n('ctrl', cc.net(dk, cc.pin_by_func(dk, '3V3'))), v12tec=n('tec', tc.net(j12t, '1')),
                v3v3pwr=n('pwr', pc.net(ss, pc.pin_by_func(ss, 'VDD'))))
    bulk = [r for r in ro.model_refs('pwr', 'cap_elec') if F['v24'] in pc.pins(r).values()]
    refs = dict(q=F['q'], qd=F['qd'], qs=F['qs'], tvs=tvs, tvs_k=pc.pin_by_func(tvs, 'K'), bulk=bulk[0] if bulk else None, f1=F['f1'], f2=F['f2'], buck12=B[12.0], buck5=B[5.0], ss=ss, devkit=dk,
                d_oring=d_or, jd=F['jd'])
    return nets, refs
