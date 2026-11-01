#!/usr/bin/env python3
"""Read-only public JLC evidence, reusing the frozen PCB parser without editing it."""
import json
import pathlib
import runpy
import time

HERE = pathlib.Path(__file__).resolve().parent
get = runpy.run_path(str(HERE.parents[1] / 'pcb/check-stock.py'))['get']
CODES = ['C2071868', 'C780769', 'C2041503', 'C476261', 'C138687',
         'C12891', 'C14663', 'C705833', 'C25810', 'C282507',
         'C2041457', 'C2046332', 'C22918', 'C2071044']

if __name__ == '__main__':
    path = HERE / 'stock-evidence.json'
    records = json.loads(path.read_text()) if path.exists() else []
    for code in CODES:
        if any(x['componentCode'] == code for x in records):
            continue
        for delay in [0, 20, 60]:
            time.sleep(delay)
            try:
                record = get(code)
                records.append(record)
                path.write_text(json.dumps(records, indent=2) + '\n')
                print(code, record['componentModelEn'], record.get('overseasStockCount'),
                      record.get('canPresaleNumber'), flush=True)
                break
            except Exception as exc:
                print(code, str(exc), flush=True)
        time.sleep(8)
