"""Cable/harness parasitics. Every lead is parameterised as [min, nom, max]."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


CUTLIST = HERE.parents[2] / 'build' / 'plenum' / 'harness' / 'cutlist.csv'


def _rows_for(rows, lead_name, lead):
    """Cut-list rows belonging to one lead, by connector reference and chain keywords."""
    toks = []
    for end in (lead['a'], lead['b']):
        if isinstance(end, list):
            toks.append(f'{end[0]} {end[1]} ')
    hit = [r for r in rows if any(t in r['from_'] + ' ' or t in r['to'] + ' ' for t in toks)]
    if lead_name == 'THERMO':
        hit = [r for r in rows if r['name'].startswith('thermostat loop')]
    elif lead_name == 'TEC' and hit:
        extra = [r for r in rows if r['name'].startswith('TEC string 2')]
        pig = [r for r in rows if r['name'].endswith('pigtail') and r['name'].startswith('TEC')]
        hit = hit + extra[:1] + (sorted(pig, key=lambda r: -float(r['cut']))[:1])
    elif lead_name == 'FAN2' and hit:
        hit = hit + [r for r in rows if r['name'].startswith('blower deck pigtail')]
    elif lead_name.startswith('OW_') and hit:
        bus = '1-Wire A' if '1-Wire A' in hit[0]['to'] else '1-Wire B'
        hit = [r for r in rows if bus in r['to']]
        for r in list(hit):
            stem = r['name'].replace(' harness', '')
            hit += [t for t in rows if t['name'] == stem + ' tail']
    seen, out = set(), []
    for r in hit:
        if r['id'] not in seen:
            seen.add(r['id'])
            out.append(r)
    return out


def apply_cutlist(h, path=CUTLIST):
    import csv
    rows = list(csv.DictReader(open(path, newline='')))
    used = {}
    for name, lead in h['leads'].items():
        hit = _rows_for(rows, name, lead)
        if not hit:
            continue
        route = sum(float(r['route']) + float(r['slack']) * 0.0 for r in hit) / 1e3
        cut = sum(float(r['cut']) for r in hit) / 1e3
        awg = max(int(r['awg']) for r in hit)          # thinnest conductor in the chain (conservative R)
        seg = dict(name='CAD cut list: ' + ' + '.join(r['id'] for r in hit), awg=awg, length_m=[route, cut, cut * 1.1])
        if name == 'BRICK':      # keep the brick's own DC cord; replace only the internal pigtail
            lead['segments'] = [lead['segments'][0], seg]
        else:
            lead['segments'] = [seg]
        if name.startswith('OW_'):
            lead['probes'] = max(1, sum(1 for r in hit if 'probe' in r['name'] and 'tail' not in r['name']))
        used[name] = [r['id'] for r in hit]
    h['_cutlist'] = dict(path=str(path), leads=used)
    return h


def load(path=None, lengths_override=None):
    h = json.loads(Path(path or HERE / 'harness.json').read_text())
    if CUTLIST.exists():
        apply_cutlist(h)
    ov = lengths_override or HERE / 'harness_lengths.json'
    h['_length_source'] = (f"CAD cut list {CUTLIST.relative_to(HERE.parents[2])} (route .. cut .. 1.1 x cut) over harness.json"
                           if CUTLIST.exists() else 'harness.json (assumed ranges)')
    if Path(ov).exists():
        o = json.loads(Path(ov).read_text())
        for k, v in o.items():
            if k.startswith('_') or k not in h['leads']:
                continue
            segs = h['leads'][k]['segments']
            vals = v if isinstance(v, list) else [v, v, v]
            total_nom = sum(s['length_m'][1] for s in segs)
            for s in segs:  # scale all segments proportionally to the CAD total
                f = s['length_m'][1] / total_nom
                s['length_m'] = [vals[0] * f, vals[1] * f, vals[2] * f]
        h['_length_source'] = f'{Path(ov).name} (CAD harness model) over harness.json'
    return h


IDX = {'min': 0, 'nom': 1, 'max': 2}


def pick(triplet, which):
    if isinstance(which, (int, float)) and not isinstance(which, bool):
        return float(which)
    if not isinstance(triplet, list):
        return triplet
    return triplet[IDX[which]]


def conductor(h, lead_name, corner=None, temp_c=40.0, contacts_per_conductor=2):
    """Per-conductor R (ohm), L (H) and C (F, to the bundle) for one lead at a corner.

    corner: dict with optional keys length, L, C, contact in {'min','nom','max'} (default nom);
    'contact' min = 0.3x, nom = 0.6x, max = 1.0x the family end-of-life contact value.
    """
    corner = corner or {}
    lead = h['leads'][lead_name]
    cu = h['copper']
    R = L = C = 0.0
    length = 0.0
    for s in lead['segments']:
        ln = pick(s['length_m'], corner.get('length', 'nom'))
        length += ln
        r20 = cu['ohm_per_m_20C'][str(s['awg'])]
        R += r20 * ln * (1 + cu['tempco_per_K'] * (temp_c - 20.0))
    L = 0.5 * pick(lead['loop_L_uH_per_m'], corner.get('L', 'nom')) * 1e-6 * length
    C = pick(lead['C_pF_per_m'], corner.get('C', 'nom')) * 1e-12 * length
    cf = {'min': 0.3, 'nom': 0.6, 'max': 1.0}[corner.get('contact', 'nom')]
    rc = h['contact_ohm'][lead['family']] * cf * contacts_per_conductor
    for fam, n in lead.get('extra_contacts', {}).items():
        rc += h['contact_ohm'][fam] * cf * n
    return dict(R=R + rc, R_wire=R, R_contact=rc, L=L, C=C, length=length)


def loop_inductance_uH_per_m(d_mm, spacing_mm):
    """Two-wire loop inductance per metre (mu0/pi * acosh(D/d))."""
    return 0.4 * math.acosh(spacing_mm / d_mm)
