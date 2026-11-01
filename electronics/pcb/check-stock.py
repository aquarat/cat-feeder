#!/usr/bin/env python3
"""Read-only JLC public-page evidence; no account, basket, upload or ordering."""
import datetime, hashlib, json, pathlib, re, time, urllib.request

IDS = ['C701341','C51118','C21404','C23654','C20526','C25804','C25803',
       'C23162','C21190','C14663','C15850','C15849','C5183929','C178702',
       'C724505','C713402','C27438','C49257','C5116481','C5116483','C27985187']
KEYS = ['componentCode','componentModelEn','componentBrandEn',
        'componentSpecificationEn','assemblyMode','componentLibraryType',
        'componentProductType','xrayFlag','moistureSensitivityLevelEn',
        'overseasStockCount','canPresaleNumber','initialPrice','leastPatchNumber',
        'preMinPurchaseNum','isBuyComponent','noBuyReason','dataManualOfficialLink',
        'dataManualUrl','describe']

def get(code):
    url = 'https://jlcpcb.com/partdetail/' + code
    raw = urllib.request.urlopen(url, timeout=60).read()
    html = raw.decode()
    stream = '\n'.join(json.loads(x) for x in re.findall(
        r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html))
    found = {}
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\{"component(?:Code|ModelEn)"', stream):
        try:
            obj, _ = decoder.raw_decode(stream[match.start():])
        except ValueError:
            continue
        if obj.get('componentCode') == code:
            found.update({k:v for k,v in obj.items() if k in KEYS})
    assert found.get('componentCode') == code, code
    return {'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'url':url, 'html_sha256':hashlib.sha256(raw).hexdigest(),
            'evidence':'Direct public JLC rendered-page hydration data; inventory not reserved',
            **found}

if __name__ == '__main__':
    path = pathlib.Path(__file__).parent/'stock-evidence.json'
    data = json.loads(path.read_text()) if path.exists() else []
    for code in IDS:
        if any(p['componentCode']==code for p in data): continue
        try:
            data.append(get(code))
            path.write_text(json.dumps(data, indent=2)+'\n')
        except Exception as e:
            print(code, str(e), flush=True)
        time.sleep(3)
    for p in data:
        print(p['componentCode'],p['componentModelEn'],p.get('overseasStockCount'),
              p.get('canPresaleNumber'),p.get('assemblyMode'))
