#!/usr/bin/env python3
"""Read-only public JLC evidence. Reuses revision-A parser, never its output path."""
import json
from pathlib import Path
import runpy
import time

HERE = Path(__file__).resolve().parent
PCB = HERE.parents[1] / 'pcb'
NEW = ['C38437', 'C346765', 'C912788', 'C22843', 'C64705', 'C5127856']
REUSE = ['C21190', 'C14663', 'C15849', 'C713402', 'C25804', 'C25803', 'C5183929']

if __name__ == '__main__':
    out = HERE / 'evidence/stock-evidence.json'
    records = {r['componentCode']: r for r in json.loads(out.read_text())} if out.exists() else {}
    for r in json.loads((PCB / 'stock-evidence.json').read_text()):
        if r['componentCode'] in REUSE:
            records.setdefault(r['componentCode'], {**r, 'reused_evidence_from': 'electronics/pcb/stock-evidence.json'})
    get = runpy.run_path(str(PCB / 'check-stock.py'))['get']
    for code in NEW:
        if code not in records:
            try:
                records[code] = get(code)
            except Exception as exc:
                print(code, str(exc), flush=True)
            out.write_text(json.dumps(list(records.values()), indent=2) + '\n')
            time.sleep(8)
    for r in records.values():
        print(r['componentCode'], r['componentModelEn'], r.get('overseasStockCount'), flush=True)
