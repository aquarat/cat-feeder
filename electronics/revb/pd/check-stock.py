#!/usr/bin/env python3
"""Public JLC page evidence only. No account, API credentials, cart or project.

Same hydration extraction pattern as ../../pcb/check-stock.py, without modifying
that frozen revision. Existing snapshots are preserved; use --refresh explicitly.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.request

from circuit import circuit

HERE = Path(__file__).resolve().parent
KEYS = {"componentCode", "componentModelEn", "componentBrandEn", "componentSpecificationEn",
        "assemblyMode", "componentLibraryType", "componentProductType", "xrayFlag",
        "moistureSensitivityLevelEn", "overseasStockCount", "canPresaleNumber", "initialPrice",
        "leastPatchNumber", "preMinPurchaseNum", "isBuyComponent", "noBuyReason",
        "dataManualOfficialLink", "dataManualUrl", "describe"}


def get(code):
    url = "https://jlcpcb.com/partdetail/" + code
    raw = urllib.request.urlopen(url, timeout=60).read()
    stream = "\n".join(json.loads(x) for x in re.findall(
        r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', raw.decode()))
    found = {}
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\{"component(?:Code|ModelEn)"', stream):
        try:
            obj, _ = decoder.raw_decode(stream[match.start():])
        except ValueError:
            continue
        if obj.get("componentCode") == code:
            found.update({k: v for k, v in obj.items() if k in KEYS})
    assert found.get("componentCode") == code, code
    return {"retrieved_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "url": url, "html_sha256": hashlib.sha256(raw).hexdigest(),
            "evidence": "Direct public JLC rendered-page hydration data; inventory not reserved", **found}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    path = HERE / "stock-evidence.json"
    data = json.loads(path.read_text()) if path.exists() else []
    if args.refresh and data:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (HERE / f"stock-evidence-before-{stamp}.json").write_text(json.dumps(data, indent=2) + "\n")
        data = []
    for code in sorted({p["lcsc"] for p in circuit()["components"] if p["lcsc"]}):
        if any(p["componentCode"] == code for p in data):
            continue
        data.append(get(code))
        path.write_text(json.dumps(data, indent=2) + "\n")
        time.sleep(3)
    for p in data:
        print(p["componentCode"], p["componentModelEn"], p.get("overseasStockCount"),
              p.get("canPresaleNumber"), p.get("assemblyMode"))
