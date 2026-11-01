#!/usr/bin/env python3
"""Run with KiCad 9 /usr/bin/python3; prints report, never edits the image.

docker run --rm --network none --read-only \
  -v "$PWD/electronics/revb/pd:/pd:ro" cat-feeder-kicad:local \
  /usr/bin/python3 /pd/validate_footprints.py > electronics/revb/pd/footprint-check.json
"""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pcbnew

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "circuit.json").read_text())
rows = []
for component in data["components"]:
    library, name = component["footprint"].split(":")
    folder = ROOT / "PD.pretty" if library == "PD" else Path("/usr/share/kicad/footprints") / (library + ".pretty")
    footprint = pcbnew.FootprintLoad(str(folder), name)
    assert footprint is not None, component["footprint"]
    actual = {pad.GetNumber() for pad in footprint.Pads() if pad.GetNumber()}
    assert actual == set(component["pins"]), (component["ref"], actual, set(component["pins"]))
    rows.append({"ref": component["ref"], "footprint": component["footprint"],
                 "numbered_pads": sorted(actual),
                 "sha256": hashlib.sha256((folder / (name + ".kicad_mod")).read_bytes()).hexdigest()})

# Independent reference comparison: all seven MOSFET copper land rectangles,
# transformed from Eagle's upward Y to KiCad's downward Y, must be preserved.
eagle = ET.parse(ROOT / "reference/sparkfun-SparkFun_STUSB4500_USB-PD.sch")
pd_device = next(d for d in eagle.findall(".//deviceset") if d.get("name") == "STUSB4500")
pd_part = next(c for c in data["components"] if c["ref"] == "U201")
for connection in pd_device.findall("./devices/device/connects/connect"):
    for pad in connection.get("pad").split():
        number = pad.removeprefix("P$")
        actual_name = pd_part["pin_names"][number]
        assert actual_name == connection.get("pin") or (number == "25" and actual_name == "EP" and connection.get("pin") == "GND"), (number, actual_name, connection.attrib)
package = next(p for p in eagle.findall(".//package") if p.get("name") == "8-POWERVDFN-3X3")
expected = sorted((p.get("name").split("@")[0], float(p.get("x")), -float(p.get("y")),
                   float(p.get("dx")), float(p.get("dy"))) for p in package.findall("smd"))
fp = pcbnew.FootprintLoad(str(ROOT / "PD.pretty"), "ST_PowerFLAT_3.3x3.3_SparkFun")
actual = sorted((p.GetNumber(), round(pcbnew.ToMM(p.GetPosition().x), 6),
                 round(pcbnew.ToMM(p.GetPosition().y), 6), round(pcbnew.ToMM(p.GetSize().x), 6),
                 round(pcbnew.ToMM(p.GetSize().y), 6)) for p in fp.Pads() if p.GetNumber())
assert actual == expected, (actual, expected)

print(json.dumps({"tool": "pcbnew " + pcbnew.GetBuildVersion(), "status": "PASS",
                  "checks": ["All selected footprints load", "Exact numbered-pad coverage including NC and USB paired contacts",
                             "STUSB4500 physical pin names match actual SparkFun Eagle source",
                             "Custom FET copper pad geometry matches actual SparkFun source with Y-coordinate transformation"],
                  "circuit_sha256": hashlib.sha256((ROOT / "circuit.json").read_bytes()).hexdigest(),
                  "components": rows}, indent=2))
