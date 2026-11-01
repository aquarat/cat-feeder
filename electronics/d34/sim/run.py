#!/usr/bin/env python3
"""D34 simulation suite entry point (runs inside cat-feeder-d34sim:local, no network).

    python3 run.py --netlists build/netlists --results results [--only s01,s05]

Reads the KiCad-exported netlists, cross-checks them against design.json, runs every
scenario module in scenarios/ and writes results/summary.json. Exit status 0 means the
suite ran; individual checks may FAIL (that is a design finding, not a suite error).
Exit status 2 means a scenario crashed or the netlist/model mapping is incomplete.
"""
import argparse
import hashlib
import importlib
import json
import os
import platform
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from d34sim import harness as H  # noqa: E402
from d34sim import models as M  # noqa: E402
from d34sim import netlist as N  # noqa: E402
from d34sim import report, spice  # noqa: E402

D34 = HERE.parent
SEED = 20261026


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Env:
    def __init__(self, cards, harness, results, seed):
        self.cards, self.harness, self.results, self.seed = cards, harness, Path(results), seed
        self.d34 = D34
        self.datasheets = load_json(HERE / 'datasheets' / 'datasheet_values.json')
        self.limits = load_json(HERE / 'limits.json')
        self.table = M.load_table()

    def outdir(self, scen):
        p = self.results / scen
        p.mkdir(parents=True, exist_ok=True)
        return p

    def limit(self, key):
        """Limit value from limits.json: returns (value, source string)."""
        L = self.limits['limits'][key]
        return L['value'], f"{L['source']}" + (f" [{L.get('status')}]" if L.get('status') else '')


def load_json(p):
    try:
        return json.loads(Path(p).read_text())
    except FileNotFoundError:
        return {}


def mapping_checks(env, chk):
    unmapped = []
    rows = []
    for cname, card in env.cards.items():
        for ref, comp in sorted(card.comps.items()):
            r = M.match(env.table, comp)
            rows.append(dict(card=cname, ref=ref, mpn=comp['mpn'], value=comp['value'], model=r['model'] if r else 'UNMAPPED',
                             provenance=r['provenance'] if r else ''))
            if r is None:
                unmapped.append(f'{cname}:{ref} {comp["mpn"]}')
    chk.csv('part_model_map.csv', rows)
    chk.add('mapping', 'Every netlist part maps to a simulation model (part_models.csv)', len(unmapped), 0, '==', 'parts',
            'suite integrity', severity='integrity', detail='; '.join(unmapped))
    mism = []
    for cname, card in env.cards.items():
        dj = D34 / f'd34-{cname}' / 'design.json'
        if dj.exists():
            mism += N.crosscheck_design_json(card, dj)
    chk.add('netlist_vs_design_json', 'Exported KiCad netlist matches design.json pin-for-pin', len(mism), 0, '==', 'pins',
            'suite integrity', severity='integrity', detail='; '.join(mism[:20]))
    sysc = N.System(env.cards, env.harness)
    # Lead integrity: every inter-card lead joins same-named nets pin for pin.
    bad = []
    for name, lead in env.harness['leads'].items():
        if not isinstance(lead['b'], list):
            continue
        pa = env.cards[lead['a'][0]].pins(lead['a'][1])
        pb = env.cards[lead['b'][0]].pins(lead['b'][1])
        for pin in sorted(set(pa) | set(pb)):
            if pa.get(pin) != pb.get(pin):
                bad.append(f'{name} pin {pin}: {pa.get(pin)} vs {pb.get(pin)}')
    missing = [k for k, l in env.harness['leads'].items() if not env.cards[l['a'][0]].pins(l['a'][1])]
    covered = {tuple(l['a']) for l in env.harness['leads'].values()} | {tuple(l['b']) for l in env.harness['leads'].values() if isinstance(l['b'], list)}
    unled = [f'{c}:{r}' for c, card in env.cards.items() for r in card.comps
             if (M.match(env.table, card.comps[r]) or {}).get('model') == 'connector' and (c, r) not in covered]
    chk.add('harness_coverage', 'harness.json leads match the connectors in the design (missing connectors are skipped)',
            len(missing) + len(unled), 0, '==', 'items', 'suite integrity (update harness.json)', severity='integrity', advisory=True,
            detail=f'leads without a connector: {missing}; connectors without a lead model: {unled}')
    chk.add('lead_nets', 'Inter-card leads join identically named nets pin for pin', len(bad), 0, '==', 'pins',
            'suite integrity', severity='integrity', detail='; '.join(bad))
    return sysc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--netlists', default=str(HERE / 'build' / 'netlists'))
    ap.add_argument('--results', default=str(HERE / 'results'))
    ap.add_argument('--only', default='')
    ap.add_argument('--quick', action='store_true', help='reduced sweeps (development only)')
    a = ap.parse_args()
    t0 = time.time()
    results = Path(a.results)
    results.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('D34_SIM_WORK', str(results / '_work'))
    spice.WORK = Path(os.environ['D34_SIM_WORK'])
    cards = N.load_cards(a.netlists)
    harness = H.load()
    env = Env(cards, harness, results, SEED)
    env.quick = a.quick
    chk0 = report.Checks('s00_integrity', env.outdir('s00_integrity'))
    env.system = mapping_checks(env, chk0)
    all_checks = list(chk0.items)
    chk0.write()
    scen_dir = HERE / 'scenarios'
    mods = sorted(p.stem for p in scen_dir.glob('s[0-9][0-9]_*.py'))
    only = [x for x in a.only.split(',') if x]
    crashed = []
    scen_meta = {}
    for m in mods:
        if only and not any(m.startswith(o) for o in only):
            continue
        t1 = time.time()
        print(f'[{time.strftime("%H:%M:%S")}] {m} ...', flush=True)
        try:
            mod = importlib.import_module(f'scenarios.{m}')
            chk = mod.run(env)
            d = chk.write()
            all_checks += chk.items
            nf = sum(1 for c in chk.items if c['status'] == 'FAIL')
            scen_meta[m] = dict(title=getattr(mod, 'TITLE', m), checks=len(chk.items), fails=nf,
                                seconds=round(time.time() - t1, 1), notes=chk.notes, models=chk.models)
            print(f'    {len(chk.items)} checks, {nf} FAIL, {time.time() - t1:.1f} s', flush=True)
        except Exception:
            tb = traceback.format_exc()
            print(tb, flush=True)
            crashed.append(m)
            scen_meta[m] = dict(title=m, crashed=True, traceback=tb[-4000:])
            all_checks.append(dict(id=f'{m}.crash', scenario=m, description='scenario ran to completion', value=False,
                                   limit=True, op='true', unit='', status='FAIL', severity='integrity', advisory=False,
                                   corner='', limit_source='suite integrity', detail=tb.splitlines()[-1]))
    prov = dict(
        label=report.LABEL,
        generated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) if os.environ.get('D34_SIM_TIMESTAMP', '1') == '1' else '',
        git_rev=os.environ.get('GIT_REV', 'unknown'), seed=SEED, quick=a.quick,
        ngspice=spice.version(), python=platform.python_version(),
        image_id=os.environ.get('SIM_IMAGE_ID', 'unknown'), kicad_cli=os.environ.get('KICAD_CLI_VERSION', 'unknown'),
        netlists={p.name: sha(p) for p in sorted(Path(a.netlists).glob('*.net'))},
        boards={f'd34-{c}.kicad_pcb': sha(D34 / f'd34-{c}' / f'd34-{c}.kicad_pcb') for c in N.CARDS},
        part_models_csv=sha(HERE / 'part_models.csv'), harness_json=sha(HERE / 'harness.json'),
        harness_lengths=harness['_length_source'],
        limits_json=sha(HERE / 'limits.json') if (HERE / 'limits.json').exists() else None,
        datasheet_values=sha(HERE / 'datasheets' / 'datasheet_values.json') if (HERE / 'datasheets' / 'datasheet_values.json').exists() else None,
        vendor_manifest=load_json(HERE / 'models' / 'vendor' / 'manifest.json'),
        vendor_map=load_json(HERE / 'models' / 'vendor_map.json'),
        vendor_files_present={k: (HERE / 'models' / 'vendor' / v['file']).exists()
                              for k, v in load_json(HERE / 'models' / 'vendor_map.json').items() if isinstance(v, dict) and 'file' in v},
    )
    npass = sum(1 for c in all_checks if c['status'] == 'PASS')
    nfail = len(all_checks) - npass
    summary = dict(provenance=prov, totals=dict(checks=len(all_checks), passed=npass, failed=nfail,
                                               failed_non_advisory=sum(1 for c in all_checks if c['status'] == 'FAIL' and not c.get('advisory')),
                                               crashed=crashed, seconds=round(time.time() - t0, 1)),
                   scenarios=scen_meta, checks=all_checks)
    (results / 'summary.json').write_text(json.dumps(summary, indent=1, default=report._clean))
    from d34sim import summary_md
    (results / 'summary.md').write_text(summary_md.render(json.loads((results / 'summary.json').read_text())))
    print(f'TOTAL {len(all_checks)} checks: {npass} PASS, {nfail} FAIL; crashed: {crashed or "none"}')
    return 2 if crashed or any(c['severity'] == 'integrity' and c['status'] == 'FAIL' for c in all_checks) else 0


if __name__ == '__main__':
    sys.exit(main())
