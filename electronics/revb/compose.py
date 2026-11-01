#!/usr/bin/env python3
"""Combine independently sourced circuit blocks into one revision B contract."""
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "pcb"


def main():
    base = json.loads((LEGACY / "connectivity.json").read_text())
    excluded = {"U2", "C1", "J2", "J14", "J15"}
    blocks = {name: json.loads((HERE / name / "circuit.json").read_text()) for name in ("motor", "power", "pd")}
    counters = {}
    for a in base:
        prefix, number = re.fullmatch(r"([A-Z]+)(\d+)", a["ref"]).groups()
        counters[prefix] = max(counters.get(prefix, 0), int(number))
    mappings, additions = {}, []
    for block, contract in blocks.items():
        components = contract.get("components", contract.get("parts"))
        if components is None:
            raise ValueError(f"Missing {block} component list")
        mappings[block] = {}
        for a in components:
            old_ref = a.get("replaces_ref")
            if old_ref:
                ref = old_ref
                excluded.add(old_ref)
            else:
                prefix = a["ref"][0]
                counters[prefix] = counters.get(prefix, 0) + 1
                ref = prefix + str(counters[prefix])
            mappings[block][a["ref"]] = ref
            lib = a.get("symbol")
            if not lib:
                lib = {"R": "Device:R", "C": "Device:C", "L": "Device:L"}.get(ref[0])
                if ref[0] == "C" and a["footprint"].startswith("Capacitor_THT:CP_"):
                    lib = "Device:C_Polarized"
                if ref[0] == "J" and set(a["pins"]) == {str(i) for i in range(1, len(a["pins"]) + 1)}:
                    lib = f'Connector_Generic:Conn_01x{len(a["pins"]):02d}'
            if not lib:
                raise ValueError(f"Missing symbol: {block}/{a['ref']}")
            nets = {str(pin): ("SYS_20V" if net == "MOTOR_SUPPLY" else net)
                    for pin, net in a["pins"].items() if net is not None}
            additions.append(dict(ref=ref, value=a["value"], lib=lib, fp=a["footprint"],
                                  nets=nets, lcsc=a["lcsc"],
                                  assembly="THT" if a["assembly"] == "manualWeld" else "SMT",
                                  block=block, block_ref=a["ref"], mpn=a.get("mpn", a["value"])))
    parts = []
    for a in base:
        if a["ref"] in excluded:
            continue
        a = {key: a[key] for key in ("ref", "value", "lib", "fp", "nets", "lcsc", "assembly")}
        if a["ref"].startswith("J"):
            a["block"] = "connectors"
        elif a["ref"] in {"U1", "R1", "R2", "R3", "R4", "R5", "R16", "R17", "R18", "R19", "C2", "C3", "C4", "C5", "C8"}:
            a["block"] = "mcu and sensors"
        else:
            a["block"] = "interfaces"
        if a["ref"] == "J1":
            a["value"] = "20V OUTPUT TO DPS INPUT"
            a["nets"] = {"1": "SYS_20V", "2": "GND"}
        parts.append(a)
    parts += additions
    assert len({a["ref"] for a in parts}) == len(parts)
    design = {
        "revision": "B", "status": "IN_DEVELOPMENT",
        "architecture": "USB-C PD with integrated stepper and 3.3V/12V switching regulators",
        "parts": parts,
        "power_flags": ["GND", "SYS_20V", "VMOT", "+3V3", "+12V"],
        "netclasses": {
            "Default": {"width_mm": .25, "nets": []},
            "Motor": {"width_mm": .8, "nets": ["VMOT", "M1A", "M1B", "M2A", "M2B", "M_SENSE1", "M_SENSE2"]},
            "Power": {"width_mm": .5, "nets": ["+3V3", "+12V", "PWR_SW1", "PWR_SW2"]},
            "PD_BUS": {"width_mm": 3.0, "nets": ["SYS_20V"]},
        },
        "block_reference_map": mappings,
        "removed_legacy_references": sorted(excluded),
    }
    (HERE / "design.json").write_text(json.dumps(design, indent=2) + "\n")
    print(f"Composed {len(parts)} fitted parts")


if __name__ == "__main__":
    main()
