#!/usr/bin/env python3
"""Validate actual revision B artifacts; never release an unrouted placement."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pcbnew as p
import version
import project

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--placement", action="store_true")
    args = parser.parse_args()
    report_path = HERE / ("placement-validation.json" if args.placement else "validation.json")
    report = {"status": "RUNNING", "release_status": "NOT_RELEASED", "physical_testing": "NOT_RUN"}
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    try:
        path = HERE / ("feeder-b-unrouted.kicad_pcb" if args.placement else "feeder-b.kicad_pcb")
        board = p.LoadBoard(str(path))
        project.validate(HERE)
        ident = json.loads((HERE / "version.json").read_text())
        sources = [version.ROOT / name for name in ident["source_files_sha256"]]
        current = version.identify(sources)
        require(current == ident, "Design/version metadata is stale: regenerate before checking")
        require(board.GetCopperLayerCount() == 4, "Expected four copper layers")
        labels = [item.GetText() for item in board.GetDrawings() if item.GetClass() == "PCB_TEXT"]
        require(ident["silkscreen_identifier"] in labels, "PCB lacks its actual source identifier")
        design = json.loads((HERE / "design.json").read_text())
        parts = {a["ref"]: a for a in design["parts"]}
        footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
        require(set(footprints) == set(parts), "Board references differ from design")
        require("J14" not in parts and "J15" not in parts and "U2" not in parts,
                "Legacy plug-in motor sockets or AP2112 remain fitted")
        tree = ET.parse(HERE / "schematic-netlist.xml")
        xml_parts = {a.attrib["ref"] for a in tree.findall("./components/comp")}
        require(xml_parts == set(parts), "Exported schematic references differ from design")
        nodes = {}
        for net in tree.findall("./nets/net"):
            for node in net.findall("node"):
                key = node.attrib["ref"], node.attrib["pin"]
                require(key not in nodes, f"Duplicate XML node {key}")
                nodes[key] = net.attrib["name"]
        actual = {}
        for ref, fp in footprints.items():
            for pad in fp.Pads():
                if not pad.GetNumber():
                    continue
                key = ref, pad.GetNumber()
                if key in nodes:
                    require(pad.GetNetname() == nodes[key], f"PCB/XML mismatch {key}")
                    actual[key] = pad.GetNetname()
                else:
                    require(not pad.GetNetname(), f"Undocumented PCB connection {key}")
        require(actual == nodes, "Some exported schematic nodes have no PCB pads")
        for ref, a in parts.items():
            for pin, net in a["nets"].items():
                require(nodes.get((ref, pin)) == net, f"Source/XML mismatch {ref}.{pin}")
        commands = [
            ["sch", "erc", "--format", "json", "--severity-all", "--exit-code-violations", "-o", "erc.json", "feeder-b.kicad_sch"],
            ["pcb", "drc", "--format", "json", "--severity-all", "--exit-code-violations", "-o", "drc-placement.json" if args.placement else "drc.json",
             *([] if args.placement else ["--schematic-parity"]), path.name],
        ]
        statuses = []
        for command in commands:
            result = subprocess.run(["kicad-cli", *command], cwd=HERE, capture_output=True, text=True)
            statuses.append(result.returncode)
            (HERE / (command[0] + "-check.log")).write_text(result.stdout + result.stderr)
        report.update(source_identifier=ident["silkscreen_identifier"], source_sha256=ident["source_sha256"],
                      components=len(parts), schematic_nodes=len(nodes), layers=4,
                      assembly_counts=dict(collections.Counter(a["assembly"] for a in parts.values())),
                      source_xml_pcb_pin_consistency="PASS", erc_exit_code=statuses[0], drc_exit_code=statuses[1],
                      artifact_sha256={path.name: sha(path), "feeder-b.kicad_sch": sha(HERE / "feeder-b.kicad_sch"),
                                       "schematic-netlist.xml": sha(HERE / "schematic-netlist.xml")})
        require(statuses[0] == 0, "ERC has findings; see erc.json")
        if args.placement:
            report.update(status="PLACEMENT_CHECKED", release_status="NOT_RELEASED: routing and DRC completion required")
        else:
            require(statuses[1] == 0, "DRC/parity has findings; see drc.json")
            report.update(status="CHECKS_PASS", release_status="INDEPENDENT_REVIEW_REQUIRED")
        print(json.dumps(report, indent=2))
    except BaseException as exc:
        report.update(status="FAILED", release_status="NOT_RELEASED", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
