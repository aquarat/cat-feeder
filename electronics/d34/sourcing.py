#!/usr/bin/env python3
"""Sourced BOM for the D34 cards: per-set quantities, RS (or other) stock numbers, packs, price breaks,
public stock figures and order totals for 1 set and for 2 sets with spares.

    python3 sourcing.py            (plain Python 3, no KiCad needed)

Inputs: design.py (parts on the cards), catalog.py (K + EXTRAS: supplier, stock no, pack),
sourcing/findchips-2026-10-26.json (dated public price/stock snapshot), sourcing/manual.json
(lines priced from other public pages: module retailers, RS export site, Farnell).
Outputs: sourcing/bom-sourced.csv, sourcing/bom-sourced.json, sourcing/bom-sourced.md (table for kb/).
Nothing is ordered; prices are ex VAT unless the line says otherwise.
"""
import collections, csv, json, math, pathlib
import catalog, design

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / 'sourcing'


def load_snapshot():
    snap = json.loads((SRC / 'findchips-2026-10-26.json').read_text())
    by = {}
    for r in snap['rows']:
        by[(r['dist'], r['sku'].replace('-', ''))] = r
    return snap, by


def unit_price(row, qty):
    """Per-piece GBP price at the largest break <= qty (findchips lists breaks in pieces)."""
    br = sorted((int(q), float(v)) for q, cur, v in row['price'] if cur == 'GBP')
    if not br:
        return None
    best = br[0][1]
    for q, v in br:
        if q <= qty:
            best = v
    return best


def spares(kind, per_set):
    """Pieces to hold for 2 sets plus spares: modules/relays +1, fuses +2, everything else +25 % (min 1)."""
    if kind in ('modules', 'relay'):
        return 2 * per_set + 1
    if kind == 'fuse':
        return 2 * per_set + 2
    return 2 * per_set + max(1, math.ceil(0.25 * per_set))


def lines():
    """Aggregate on-board parts (all three cards) and off-board extras into purchase lines."""
    out = collections.OrderedDict()
    for key in ('ctrl', 'pwr', 'tec'):
        B = design.BOARDS[key]()
        for a in B.parts:
            c = catalog.get(a)
            lk = (c.get('rs') or c.get('farnell') or c['mpn'], c['mpn'])
            L = out.setdefault(lk, dict(desc=c['desc'] + (f' {a.value}' if a.kind == 'R' else ''), mfr=c['mfr'], mpn=c['mpn'],
                                        supplier=c.get('supplier', 'RS'), stock_no=c.get('rs') or c.get('farnell', ''),
                                        pack=c.get('pack', 1), ds=c.get('ds', ''), check=c.get('check', ''), refs=[], qty=0,
                                        cls='relay' if a.kind == 'G2RL2' else 'part'))
            L['refs'].append(f'{key}:{a.ref}'); L['qty'] += 1
            if a.kind in ('DEVKIT', 'STEPSTICK'):   # each module footprint = 2 socket strips
                L['qty'] += 1
    for board, ex in catalog.EXTRAS.items():
        for e in ex:
            lk = e.get('merge') or e['id']
            L = out.setdefault(lk, dict(desc=e['desc'], mfr=e['mfr'], mpn=e['mpn'], supplier=e.get('supplier', 'RS'),
                                        stock_no=e.get('rs', ''), pack=e.get('pack', 1), ds=e.get('ds', ''),
                                        check=e.get('check', ''), refs=[], qty=0, url=e.get('url', ''), price=e.get('price'),
                                        cls='modules' if e['id'] in ('devkit', 'stepstick') else 'fuse' if e['id'].startswith('fuse') else 'part'))
            if e.get('merge'):
                L['desc'] = 'JST XH housing 3-way (home sensor + two 1-Wire bus leads)'
            L['refs'].append(f'{board}:off-board'); L['qty'] += e['qty']
    return out


def main():
    snap, by = load_snapshot()
    manual = json.loads((SRC / 'manual.json').read_text()) if (SRC / 'manual.json').exists() else {}
    rows = []
    tot = collections.defaultdict(float)
    for lk, L in lines().items():
        dist = {'RS': 'RS', 'Farnell': 'Farnell'}.get(L['supplier'])
        snaprow = by.get((dist, L['stock_no'].replace('-', ''))) if dist else None
        m = manual.get(L['stock_no']) or manual.get(L['mpn'])
        q1 = L['qty']; q2 = spares(L['cls'], L['qty'])
        pack = int(L['pack'] or 1)
        n1 = math.ceil(q1 / pack); n2 = math.ceil(q2 / pack)
        p1 = p2 = None; stock = ''; breaks = ''
        if snaprow:
            p1 = unit_price(snaprow, n1 * pack); p2 = unit_price(snaprow, n2 * pack)
            stock = snaprow['stock']; breaks = ' '.join(f'{q}@£{float(v):.4g}' for q, cur, v in sorted(snaprow['price'], key=lambda x: int(x[0])))
        elif m:
            p1 = p2 = m['unit_gbp']; stock = m.get('stock', ''); breaks = m.get('breaks', '')
        elif L.get('price'):
            p1 = p2 = L['price']
        c1 = round(p1 * n1 * pack, 2) if p1 is not None else None
        c2 = round(p2 * n2 * pack, 2) if p2 is not None else None
        tot[('set1', L['supplier'])] += c1 or 0; tot[('set2', L['supplier'])] += c2 or 0
        rows.append(dict(line=lk if isinstance(lk, str) else lk[1], desc=L['desc'], mfr=L['mfr'], mpn=L['mpn'], supplier=L['supplier'],
                         stock_no=L['stock_no'], url=(catalog.RS.format(L['stock_no'].replace('-', '')) if L['supplier'] == 'RS' and L['stock_no']
                                                      else (snaprow or {}).get('url') or (m or {}).get('url') or L.get('url', '')),
                         pack=pack, qty_per_set=q1, qty_2sets_spares=q2, packs_1set=n1, packs_2sets=n2,
                         unit_gbp_1set=p1, unit_gbp_2sets=p2, cost_1set=c1, cost_2sets=c2, public_stock=stock, breaks=breaks,
                         stock_date=(snap['date'] if snaprow else (m or {}).get('date', '')), stock_source=('findchips' if snaprow else (m or {}).get('source', '')),
                         ds=L['ds'], check=L['check'], refs=' '.join(L['refs'])))
    (SRC / 'bom-sourced.json').write_text(json.dumps(dict(rows=rows, totals={f'{a}|{b}': round(v, 2) for (a, b), v in tot.items()}), indent=1) + '\n')
    with (SRC / 'bom-sourced.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    md = ['| Line | Mfr / MPN | Supplier, stock no | Pack | Per set | 2 sets + spares | £/pc (1 set) | £ 1 set | £ 2 sets | Public stock (date) |',
          '|---|---|---|---:|---:|---:|---:|---:|---:|---|']
    for r in rows:
        link = f'[{r["supplier"]} {r["stock_no"]}]({r["url"]})' if r['url'] else f'{r["supplier"]} {r["stock_no"]}'
        f2 = lambda v: '' if v is None else f'{v:.2f}'
        u = '' if r['unit_gbp_1set'] is None else f'{r["unit_gbp_1set"]:.3f}'
        md.append(f'| {r["desc"]} | {r["mfr"]} {r["mpn"]} | {link} | {r["pack"]} | {r["qty_per_set"]} ({r["packs_1set"]} pk) | '
                  f'{r["qty_2sets_spares"]} ({r["packs_2sets"]} pk) | {u} | '
                  f'{f2(r["cost_1set"])} | {f2(r["cost_2sets"])} | {r["public_stock"]} ({r["stock_date"]}) |')
    sup = sorted({b for (a, b) in tot})
    md.append('')
    md.append('| Supplier | 1 set (£ ex VAT) | 2 sets + spares (£ ex VAT) |')
    md.append('|---|---:|---:|')
    for s_ in sup:
        md.append(f'| {s_} | {tot[("set1", s_)]:.2f} | {tot[("set2", s_)]:.2f} |')
    md.append(f'| **All** | **{sum(v for (a, b), v in tot.items() if a == "set1"):.2f}** | **{sum(v for (a, b), v in tot.items() if a == "set2"):.2f}** |')
    (SRC / 'bom-sourced.md').write_text('\n'.join(md) + '\n')
    kb = ROOT.parent.parent / 'kb' / 'd34-sourcing.md'
    if kb.exists():
        t = kb.read_text(); b0 = '<!-- BEGIN bom-sourced.md (generated) -->'; b1 = '<!-- END bom-sourced.md -->'
        if b0 in t and b1 in t:
            kb.write_text(t[:t.index(b0) + len(b0)] + '\n' + '\n'.join(md) + '\n' + t[t.index(b1):])
    offcard(snap, by)
    missing = [r['line'] for r in rows if r['cost_1set'] is None]
    print(f'{len(rows)} lines; unpriced: {missing}')
    for s_ in sup:
        print(s_, round(tot[('set1', s_)], 2), round(tot[('set2', s_)], 2))


def offcard(snap, by):
    """Harness and off-card devices (sourcing/offcard.json, researched 2026-10-26): table + totals."""
    f = SRC / 'offcard.json'
    if not f.exists():
        return
    d = json.loads(f.read_text())
    md = ['| Item | Mfr / MPN | Supplier, stock no | Pack | Per build | £/pc ex VAT | £ per build | Verified | Crimp tool? |',
          '|---|---|---|---:|---:|---:|---:|---|---|']
    tot = collections.defaultdict(float)
    for r in d['rows']:
        q = r.get('qty_per_build') or 0; pack = int(r.get('pack') or 1); u = r.get('unit_gbp_ex_vat')
        n = math.ceil(q / pack) if q else 0
        cost = round(u * n * pack, 2) if (u is not None and q) else None
        tot[r.get('supplier', '?')] += cost or 0
        link = f'[{r.get("supplier","")} {r.get("stock_no","")}]({r["url"]})' if r.get('url') else f'{r.get("supplier","")} {r.get("stock_no","")}'
        md.append(f'| {r.get("item","")} | {r.get("mfr","")} {r.get("mpn","")} | {link} | {pack} | {q} | '
                  f'{"" if u is None else f"{u:.2f}"} | {"" if cost is None else f"{cost:.2f}"} | {r.get("verified","")} | '
                  f'{"yes" if r.get("needs_crimp_tool") else "no"} |')
    md += ['', '| Supplier (off-card) | £ per build ex VAT |', '|---|---:|']
    md += [f'| {k} | {v:.2f} |' for k, v in sorted(tot.items())]
    md.append(f'| **All off-card** | **{sum(tot.values()):.2f}** |')
    (SRC / 'bom-offcard.md').write_text('\n'.join(md) + '\n')
    kb = ROOT.parent.parent / 'kb' / 'd34-sourcing.md'
    if kb.exists():
        t = kb.read_text(); b0 = '<!-- BEGIN bom-offcard.md (generated) -->'; b1 = '<!-- END bom-offcard.md -->'
        if b0 in t and b1 in t:
            kb.write_text(t[:t.index(b0) + len(b0)] + '\n' + '\n'.join(md) + '\n' + t[t.index(b1):])
    print('off-card', {k: round(v, 2) for k, v in tot.items()})


if __name__ == '__main__':
    main()
