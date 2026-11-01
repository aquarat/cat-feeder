#!/usr/bin/env python3
"""Restore the third-party documents listed in references.json.

    python3 scripts/fetch_references.py            # fetch missing/changed files, then regenerate extracts
    python3 scripts/fetch_references.py --check    # report only, no network, no writes
    python3 scripts/fetch_references.py --only 'thermal/*'

Manufacturer datasheets and our text/PNG extracts of them are not
redistributed. Missing or hash-different downloads are fetched and verified
against the recorded SHA-256; a publisher revision is saved anyway with a
MISMATCH warning. Derived entries are regenerated (only when missing or
their source was just fetched) if the
tool and its `requires` Python module are available; byte-identical output is
not guaranteed. `script` entries are only hinted. Exit status is non-zero
only with --strict and a network or tool error. Python stdlib only.
"""
import argparse
import fnmatch
import hashlib
import http.client
import json
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import urllib.parse

ROOT = Path(__file__).resolve().parent.parent
# Exact-case browser headers: Akamai-fronted hosts (Molex, Analog, Panasonic)
# stall urllib's default/capitalised headers; distributors block its User-Agent.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
    "Accept-Encoding": "identity",
    "Connection": "close",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}
MAGIC = {".pdf": b"%PDF", ".jpg": b"\xff\xd8\xff", ".png": b"\x89PNG"}


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def download(url, timeout=90):
    ctx = ssl.create_default_context()
    for _ in range(10):
        u = urllib.parse.urlsplit(url)
        if u.scheme == "https":
            c = http.client.HTTPSConnection(u.hostname, u.port, timeout=timeout, context=ctx)
        else:
            c = http.client.HTTPConnection(u.hostname, u.port, timeout=timeout)
        try:
            c.request("GET", (u.path or "/") + ("?" + u.query if u.query else ""), headers=HEADERS)
            r = c.getresponse()
            if r.status in (301, 302, 303, 307, 308) and r.getheader("Location"):
                url = urllib.parse.urljoin(url, r.getheader("Location"))
                continue
            if r.status != 200:
                raise OSError(f"HTTP {r.status}")
            return r.read()
        finally:
            c.close()
    raise OSError("too many redirects")


def fetch(e, path):
    if not e.get("url"):
        return "FAILED  ", "no url: " + e.get("notes", "")
    err = None
    for _ in range(2):
        try:
            data = download(e["url"])
            break
        except (OSError, http.client.HTTPException) as x:
            err = f"{type(x).__name__}: {x}"
    else:
        return "FAILED  ", err
    magic = MAGIC.get(path.suffix.lower())
    if magic and not data.startswith(magic):
        return "FAILED  ", f"not a {path.suffix} file ({data[:20]!r}...)"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    got = hashlib.sha256(data).hexdigest()
    if got != e["sha256"]:
        return "MISMATCH", f"saved anyway; publisher revision? got {got}"
    return "fetched ", ""


def regenerate(e, root, path):
    src = root / e["derived_from"]
    if not src.is_file():
        return "skip    ", "source missing: " + e["derived_from"]
    argv = e["regenerate"]
    if not shutil.which(argv[0]):
        return "skip    ", argv[0] + " not on PATH"
    mod = e.get("requires")
    if mod and subprocess.run([argv[0], "-c", f"import {mod}"], capture_output=True).returncode:
        return "skip    ", f"needs Python module {mod} (pip install {mod})"
    tmp = path.with_name(path.stem + ".tmp" + path.suffix)
    argv = [a.replace("{src}", str(src)).replace("{out}", str(tmp)) for a in argv]
    path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(argv, cwd=root, capture_output=True, text=True)
    if r.returncode or not tmp.is_file():
        tmp.unlink(missing_ok=True)
        return "FAILED  ", (r.stderr.strip().splitlines() or ["no output"])[-1]
    tmp.replace(path)
    same = sha256(path) == e["sha256"]
    return ("regen   ", "") if same else ("regen~  ", "differs from recorded sha256 (tool version)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="report only; no network, no writes")
    ap.add_argument("--only", metavar="GLOB", help="restrict to paths matching this glob")
    ap.add_argument("--strict", action="store_true", help="exit 1 on network or tool errors")
    ap.add_argument("--root", type=Path, default=ROOT, help="tree to operate on (default: this repo)")
    args = ap.parse_args()
    root = args.root.resolve()
    entries = json.loads((ROOT / "references.json").read_text())
    if args.only:
        entries = [e for e in entries if fnmatch.fnmatch(e["path"], args.only)]
    counts, fetched = {}, set()

    def report(tag, e, msg=""):
        counts[tag.strip()] = counts.get(tag.strip(), 0) + 1
        print(tag, e["path"], *([msg] if msg else []))

    for kind in ("download", "derived", "script"):
        for e in (e for e in entries if e["kind"] == kind):
            path = root / e["path"]
            if kind == "script":
                report("hint    ", e, "regenerate with: " + " ".join(e["regenerate"]))
                continue
            have = sha256(path)
            if have == e["sha256"]:
                report("ok      ", e)
                continue
            if args.check:
                report("missing " if have is None else "differs ", e)
                continue
            if kind == "derived" and have and e["derived_from"] not in fetched:
                report("differs ", e, "present, sha256 differs from record; left alone")
                continue
            tag, msg = fetch(e, path) if kind == "download" else regenerate(e, root, path)
            if kind == "download" and tag.strip() in ("fetched", "MISMATCH"):
                fetched.add(e["path"])
            report(tag, e, msg)
    print("summary:", ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return 1 if args.strict and counts.get("FAILED") else 0


if __name__ == "__main__":
    sys.exit(main())
