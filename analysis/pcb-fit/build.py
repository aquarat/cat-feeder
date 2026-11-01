#!/usr/bin/env python3
"""Reproduce mechanical evidence without changing any upstream/electronics file."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def fixture():
    source = (ROOT / "cad/feeder.scad").read_text()
    start = source.index("module shell() {")
    end = source.index("\nfunction clamp01", start)
    shell = source[start:end]
    assert shell.count("    pcb_adapted_internals();") == 1
    assert shell.count("        pcb_shell_loading_notches();") == 1
    assert shell.count("        floor_intake_cutters();") == 1
    legacy = shell.replace("module shell() {", "module legacy_shell_fixture() {")
    legacy = legacy.replace("    pcb_adapted_internals();", "    internals();")
    legacy = legacy.replace("        pcb_shell_loading_notches();\n", "")
    (OUT / "shell-fixture.scad").write_text(
        "// Generated exact shell integration fixture; do not edit.\n"
        "include <../../cad/parameters.scad>\n"
        "use <../../cad/feeder.scad>\n"
        "use <../../cad/internals.scad>\n"
        "use <../../cad/pcb_mount.scad>\n"
        "use <../../cad/lib/edges.scad>\n"
        "use <../../cad/lib/sensor.scad>\n"
        "module adapted_shell_fixture() { shell(); }\n" + legacy)


def oscad(*args):
    subprocess.run(["bash", "scripts/openscad.sh", "--backend=Manifold", *args,
                    "analysis/pcb-fit/study.scad"], cwd=ROOT, check=True)


def report():
    spec = importlib.util.spec_from_file_location("mesh", ROOT / "scripts/check_mesh.py")
    mesh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mesh)
    measured = {name: mesh.measure(OUT / f"{name}.stl")
                for name in ("cradle", "coupon", "adapted-shell")}
    for name in ("cradle", "coupon"):
        assert max(measured[name]["size_mm"]) <= 170
        assert abs(measured[name]["min_mm"][2]) < 0.025
    log = (OUT / "checks.echo").read_text()
    assert not re.search(r"WARNING:|ERROR:", log), log
    checks = dict((name, float(value)) for name, value in re.findall(
        r'check = "([^"]+)", intersection_mm3 = ([\deE.+-]+)', log))
    assert len(checks) >= 21 and all(v < .001 for v in checks.values())
    measurements = dict((name, float(value)) for name, value in re.findall(
        r'metric = "([^"]+)", mm3 = ([\deE.+-]+)', log))
    paths = [ROOT / "cad" / f for f in
             ("parameters.scad", "internals.scad", "feeder.scad", "pcb_mount.scad")]
    paths += [OUT / "study.scad", OUT / "shell-fixture.scad", OUT / "build.py"]
    paths += [ROOT / "electronics/pcb" / f for f in
              ("views/board-envelope.stl", "outline-study.json", "design-bom.csv")]
    data = {"status": "Geometry only; provisional bought-part/harness envelopes",
            "mesh": measured, "intersections_mm3": checks,
            "diagnostic_volumes_mm3": measurements,
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in paths},
            "output_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(OUT.iterdir()) if p.suffix in (".stl", ".png", ".echo")}}
    (OUT / "report.json").write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(measured, indent=2))


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("fixture", "all"):
        fixture()
    if mode == "all":
        oscad("--enable=geometry-metrics", "-o", "analysis/pcb-fit/checks.echo")
        log = (OUT / "checks.echo").read_text()
        assert not re.search(r"WARNING:|ERROR:", log), log
        for part, name in (("cradle", "cradle"), ("coupon", "coupon"), ("shell", "adapted-shell")):
            oscad("--export-format", "binstl", "-D", f'part="{part}"',
                  "-o", f"analysis/pcb-fit/{name}.stl")
    if mode in ("views", "all"):
        for part, name, camera in (
            ("local", "local", "0,0,0,55,0,20,350"),
            ("section", "section", "0,0,0,90,0,0,350"),
            ("ledge", "ledge", "0,0,0,0,0,0,350"),
            ("view", "oblique", "0,0,0,45,0,25,350"),
            ("view", "top", "0,0,0,0,0,0,350")):
            oscad("--render", "--imgsize=1400,1000", "--autocenter", "--viewall",
                  f"--camera={camera}", "-D", f'part="{part}"',
                  "-o", f"analysis/pcb-fit/{name}.png")
    if mode in ("report", "all"):
        report()
