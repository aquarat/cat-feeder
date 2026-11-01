"""Explicit KiCad rules for revision B; numerical factory evidence in dfm/."""
import json
from pathlib import Path


def write(root, classes):
    root = Path(root)
    definitions, patterns = [], []
    for name, spec in classes.items():
        definitions.append(dict(name=name, clearance=.2, track_width=spec["width_mm"],
                                via_diameter=.6, via_drill=.3, microvia_diameter=.3,
                                microvia_drill=.1, diff_pair_width=.2, diff_pair_gap=.25,
                                diff_pair_via_gap=.25, wire_width=6, bus_width=12))
        patterns.extend({"pattern": net, "netclass": name} for net in spec.get("nets", []))
    project = {
        "meta": {"filename": "feeder-b.kicad_pro", "version": 1},
        "board": {"design_settings": {
            "rules": {"min_clearance": .2, "min_track_width": .2, "min_via_diameter": .6,
                      "min_through_hole_diameter": .2, "min_copper_edge_clearance": .3,
                      "min_hole_clearance": .25, "min_silk_clearance": .15,
                      "min_text_height": 1.0, "min_text_thickness": .15},
            "rule_severities": {}, "drc_exclusions": [],
        }},
        "net_settings": {"classes": definitions, "netclass_patterns": patterns},
    }
    for stem in ("feeder-b", "feeder-b-unrouted"):
        (root / (stem + ".kicad_pro")).write_text(json.dumps(project, indent=2) + "\n")


def validate(root):
    data = json.loads((Path(root) / "feeder-b.kicad_pro").read_text())
    settings = data["board"]["design_settings"]
    if settings.get("drc_exclusions"):
        raise ValueError("Unreviewed DRC exclusions")
    for key, severity in settings.get("rule_severities", {}).items():
        if severity == "ignore":
            raise ValueError(f"DRC rule disabled: {key}")
    return data
