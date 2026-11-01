"""Check registry, CSV/PNG helpers and the summary writer."""
import csv
import json
import math
from pathlib import Path

import numpy as np

RESULTS = Path('/results')
LABEL = 'SIMULATION (models + datasheet limits), not a hardware test'


class Checks:
    def __init__(self, scenario, outdir):
        self.scenario, self.outdir = scenario, Path(outdir)
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.items = []
        self.notes = []
        self.models = {}

    def add(self, check_id, desc, value, limit, op, unit, source, severity='rating', corner='', detail='', advisory=False):
        """op: '<=', '>=', '<', '>', '==', 'in' (limit = [lo, hi]) or 'true' (value is bool)."""
        if op == 'true':
            ok = bool(value)
        elif op == 'in':
            ok = limit[0] <= value <= limit[1]
        else:
            ok = {'<=': value <= limit, '>=': value >= limit, '<': value < limit, '>': value > limit,
                  '==': value == limit}[op]
        if isinstance(value, float) and not math.isfinite(value):
            ok = False
        rec = dict(id=f'{self.scenario}.{check_id}', scenario=self.scenario, description=desc,
                   value=_clean(value), limit=_clean(limit), op=op, unit=unit,
                   status='PASS' if ok else 'FAIL', severity=severity, advisory=advisory,
                   corner=corner, limit_source=source, detail=detail)
        self.items.append(rec)
        return ok

    def note(self, s):
        self.notes.append(s)

    def csv(self, name, rows):
        if not rows:
            return
        keys = list(rows[0].keys())
        for r in rows[1:]:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(self.outdir / name, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in rows:
                w.writerow({k: _fmt(r.get(k, '')) for k in keys})

    def write(self, extra=None):
        d = dict(scenario=self.scenario, label=LABEL, checks=self.items, notes=self.notes, models=self.models)
        if extra:
            d.update(extra)
        (self.outdir / 'checks.json').write_text(json.dumps(d, indent=1, default=_clean))
        return d


def _fmt(v):
    if isinstance(v, float):
        return f'{v:.6g}'
    return v


def _clean(v):
    if isinstance(v, (np.floating,)):
        v = float(v)
    if isinstance(v, (np.integer,)):
        v = int(v)
    if isinstance(v, (np.bool_,)):
        v = bool(v)
    if isinstance(v, float):
        if not math.isfinite(v):
            return str(v)
        return float(f'{v:.6g}')
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, np.ndarray):
        return [_clean(x) for x in v.tolist()]
    return v


def plot(path, title, panels, xlabel='time (ms)', xscale=1e3):
    """panels: list of dicts {ylabel, traces: [(x, y, label)], hlines: [(y, label)]}."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    n = len(panels)
    fig, axes = plt.subplots(n, 1, figsize=(9, 2.6 * n + 0.6), sharex=True, squeeze=False)
    for ax, p in zip(axes[:, 0], panels):
        for x, y, lab in p['traces']:
            ax.plot(np.asarray(x) * xscale, y, lw=1.1, label=lab)
        for y, lab in p.get('hlines', []):
            ax.axhline(y, ls='--', lw=0.8, color='0.35')
            ax.text(ax.get_xlim()[0], y, ' ' + lab, va='bottom', fontsize=7, color='0.25')
        ax.set_ylabel(p['ylabel'])
        ax.grid(alpha=0.3)
        if len(p['traces']) > 1:
            ax.legend(fontsize=7, loc='best')
    axes[-1, 0].set_xlabel(xlabel)
    fig.suptitle(f'{title}\n{LABEL}', fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
