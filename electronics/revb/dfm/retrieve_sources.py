#!/usr/bin/env python3
"""Archive public official guidance only; no account/session or order access."""
import concurrent.futures
import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.request

SOURCES = {
    "fabrication": "https://jlcpcb.com/capabilities/pcb-capabilities",
    "assembly": "https://jlcpcb.com/capabilities/pcb-assembly-capabilities",
    "spacing": "https://jlcpcb.com/help/article/minimum-spacing-for-smd-components",
    "terms": "https://jlcpcb.com/help/article/terms-and-conditions-of-jlcpcb-assembly-service",
    "rails": "https://jlcpcb.com/help/article/specifications-for-adding-process-edges-and-positioning-holes",
    "tooling": "https://jlcpcb.com/help/article/common-pcba-after-sales-issues-and-faq",
    "stackup": "https://jlcpcb.com/impedance",
    "copper": "https://jlcpcb.com/help/article/jlcpcb-copper-weight",
    "calculator": "https://jlcpcb.com/help/article/user-guide-to-the-jlcpcb-impedance-calculator",
    "pofv": "https://jlcpcb.com/news/free-via-in-pad-6-20-layer-pcbs-pofv",
    "cpl": "https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly",
    "kicad": "https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad",
    "dfma": "https://jlcpcb.com/blog/design-for-manufacturing-and-assembly",
    "assembly_faq": "https://jlcpcb.com/help/article/pcb-assembly-faqs",
    "via_covering": "https://jlcpcb.com/help/article/pcb-via-covering",
    "fiducials": "https://jlcpcb.com/help/article/how-to-add-edge-rails-fiducials-for-pcb-assembly-order",
    "kicad9": "https://jlcpcb.com/help/article/how-to-generate-gerber-and-drill-files-in-kicad-9",
    "ordering": "https://jlcpcb.com/help/article/instructions-for-ordering",
    "assembly_price": "https://jlcpcb.com/help/article/pcb-assembly-price",
    "stencil": "https://jlcpcb.com/help/article/instructions-for-stencil-order",
}


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("p", "div", "tr", "h1", "h2", "h3", "li", "br"):
            self.parts.append("\n")
        if tag == "td":
            self.parts.append(" | ")
        if tag == "img":
            self.images.append(dict(attrs))

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, text):
        if not self.skip:
            self.parts.append(text)


def retrieve(item):
    name, url = item
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (public documentation research)"})
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read()
        final_url = response.url
    parser = Text()
    parser.feed(raw.decode("utf-8"))
    text = "\n".join(line for line in (" ".join(x.split()) for x in "".join(parser.parts).splitlines()) if line)
    out = Path(__file__).parent / "evidence"
    out.mkdir(exist_ok=True)
    (out / f"{name}.txt").write_text(text + "\n")
    return name, {"url": url, "final_url": final_url,
                  "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "retrieval": "direct_public_html_including_collapsed_tables",
                  "raw_html_sha256": hashlib.sha256(raw).hexdigest(),
                  "text_sha256": hashlib.sha256((text + "\n").encode()).hexdigest(),
                  "text_file": f"evidence/{name}.txt", "images": parser.images}


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        records = dict(pool.map(retrieve, SOURCES.items()))
    (Path(__file__).parent / "sources.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"Retrieved {len(records)} public official sources.")
