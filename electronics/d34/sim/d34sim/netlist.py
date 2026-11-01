"""Load the KiCad-exported netlists of the three D34 cards and the harness that joins them.

The exported `.net` files (kicad-cli, kicadsexpr format) are the source of truth:
component values, MPN fields and pin-to-net connectivity all come from them.
`design.json` (written by the design generator) is only used for a cross-check.
"""
import json
import re
from pathlib import Path

from . import sexpr

CARDS = ('ctrl', 'pwr', 'tec')


class Card:
    def __init__(self, name, comps, nets, source):
        self.name, self.comps, self.nets, self.source = name, comps, nets, source
        self.pin_net = {}
        self.pin_func = {}
        for net, nodes in nets.items():
            for ref, pin, func in nodes:
                self.pin_net[(ref, pin)] = net
                self.pin_func[(ref, pin)] = func

    def net(self, ref, pin):
        return self.pin_net.get((ref, str(pin)))

    def pins(self, ref):
        """{pin: net} for one component (unconnected pins omitted)."""
        return {p: n for (r, p), n in self.pin_net.items() if r == ref}

    ALIASES = {'IN': ('Vin', 'VIN', 'VI'), 'OUT': ('Vout', 'VOUT', 'VO'), 'GND': ('COM_GND',)}

    def pin_by_func(self, ref, func):
        for name in (func,) + self.ALIASES.get(func, ()):
            for (r, p), f in self.pin_func.items():
                if r == ref and f == name:
                    return p
        return None

    def refs_on(self, net):
        return sorted({r for r, p, f in self.nets.get(net, [])})

    def nodes_on(self, net):
        return list(self.nets.get(net, []))


def load_net(path, name):
    tree = sexpr.parse(Path(path).read_text())
    comps = {}
    for comp in sexpr.children(sexpr.child(tree, 'components'), 'comp'):
        ref = sexpr.value(comp, 'ref')
        fields = {}
        fl = sexpr.child(comp, 'fields')
        if fl is not None:
            for f in sexpr.children(fl, 'field'):
                nm = sexpr.value(f, 'name')
                fields[nm] = f[2] if len(f) > 2 and isinstance(f[2], str) else ''
        lib = sexpr.child(comp, 'libsource')
        comps[ref] = dict(ref=ref, value=sexpr.value(comp, 'value', ''), footprint=sexpr.value(comp, 'footprint', ''),
                          mpn=fields.get('MPN', ''), libpart=sexpr.value(lib, 'part', '') if lib else '',
                          lib=sexpr.value(lib, 'lib', '') if lib else '')
    nets = {}
    for net in sexpr.children(sexpr.child(tree, 'nets'), 'net'):
        nm = sexpr.value(net, 'name', '')
        nm = nm[1:] if nm.startswith('/') else nm
        nodes = []
        for nd in sexpr.children(net, 'node'):
            nodes.append((sexpr.value(nd, 'ref'), sexpr.value(nd, 'pin'), sexpr.value(nd, 'pinfunction', '')))
        if nm.startswith('unconnected-'):
            continue
        nets[nm] = nodes
    return Card(name, comps, nets, str(path))


def load_cards(netdir):
    return {c: load_net(Path(netdir) / f'd34-{c}.net', c) for c in CARDS}


def crosscheck_design_json(card, design_json):
    """Compare pin->net between the exported netlist and design.json. Returns list of mismatches."""
    d = json.loads(Path(design_json).read_text())
    bad = []
    for part in d['parts']:
        for pin, net in part['nets'].items():
            got = card.net(part['ref'], pin)
            if got != net:
                bad.append(f"{card.name} {part['ref']}.{pin}: design.json {net} vs netlist {got}")
    return bad


def spice_node(card, net):
    """Card-qualified SPICE node name."""
    if net is None:
        return None
    s = re.sub(r'[^A-Za-z0-9_]', lambda m: {'+': 'P', '-': 'M'}.get(m.group(0), '_'), net)
    return f'{card}_{s}'


class System:
    """Logical connectivity across cards: nets joined by leads (pin k <-> pin k)."""

    def __init__(self, cards, harness):
        self.cards, self.harness = cards, harness
        self.parent = {}
        for lead in harness['leads'].values():
            a, b = lead['a'], lead['b']
            if not (isinstance(b, list) and b[0] in cards):
                continue
            ca, cb = cards[a[0]], cards[b[0]]
            pa, pb = ca.pins(a[1]), cb.pins(b[1])
            for pin, na in pa.items():
                nb = pb.get(pin)
                if nb is not None:
                    self.union((a[0], na), (b[0], nb))

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        self.parent[self.find(x)] = self.find(y)

    def same(self, a, b):
        return self.find(a) == self.find(b)

    def members(self, x):
        r = self.find(x)
        keys = set(self.parent) | {x}
        return sorted(k for k in keys if self.find(k) == r)
