"""Render results/summary.json as a Markdown table (results/summary.md)."""
import json
import sys
from pathlib import Path


def fmt(v):
    if isinstance(v, float):
        return f'{v:.4g}'
    if isinstance(v, list):
        return '[' + ', '.join(fmt(x) for x in v) + ']'
    return str(v)


def render(summary):
    p = summary['provenance']
    t = summary['totals']
    out = [f"# D34 simulation summary ({p['label']})", '',
           f"git {p['git_rev']}, ngspice {p['ngspice']}, seed {p['seed']}, harness lengths: {p['harness_lengths']}", '',
           f"**{t['checks']} checks: {t['passed']} PASS, {t['failed']} FAIL ({t['failed_non_advisory']} non-advisory); crashed: {t['crashed'] or 'none'}**", '',
           '| | Check | Value | Limit | Severity | Corner / detail |', '|---|---|---|---|---|---|']
    for c in summary['checks']:
        mark = c['status'] + (' (adv.)' if c.get('advisory') else '')
        desc = c['description'].replace('|', '/')
        det = (c.get('corner') or '') + ((' - ' + c['detail']) if c.get('detail') else '')
        out.append(f"| {mark} | `{c['id']}` {desc} | {fmt(c['value'])} {c['unit']} | {c['op']} {fmt(c['limit'])} | {c['severity']} | "
                   f"{det.replace('|', '/')[:220]} |")
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    d = Path(sys.argv[1] if len(sys.argv) > 1 else 'results')
    (d / 'summary.md').write_text(render(json.loads((d / 'summary.json').read_text())))
