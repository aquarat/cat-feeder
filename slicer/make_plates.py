#!/usr/bin/env python3
"""Build and independently reopen editable UNSLICED Bambu projects (stdlib only)."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS = {"m": CORE}
IDENTITY = "1 0 0 0 1 0 0 0 1 0 0 0"
MATRIX = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"
MACHINE = "Bambu Lab A1 mini 0.4 nozzle"
FILAMENT = "Generic PETG @BBL A1M"
BED = 180.0
BRIM = 5.0
GAP = 14.0
MARGIN = 8.0
# Explicit allowlist: capacity is a measurement solid; full shell/lid are not plates.
PLAN = (
    ("01-insulation-coupon-unsliced", "insulated", ("insulation_coupon",)),
    ("02-closure-trials-unsliced", "solid", ("closure_coupon_base", "closure_coupon_lid", "clip")),
    ("03-drive-unsliced", "solid", ("drive",)),
    ("04-hub-unsliced", "robust", ("hub",)),
    ("05-tray-sector-unsliced", "tray", ("sector",)),
    ("06-deck-quarter-unsliced", "insulated", ("deck_quarter",)),
)
OPTIONAL_PLAN = (
    ("07-lid-access-coupon-unsliced", "insulated", ("lid_access_coupon",)),
    # kb/drop-in-layout.md: flat-side down, short blind socket roofs to inspect.
    ("08-motor-bridge-unsliced", "robust", ("motor_bridge",)),
    ("09-fan-inlet-coupon-unsliced", "robust", ("fan_inlet_coupon",)),
    ("10-pcb-cradle-unsliced", "robust", ("pcb_cradle",)),  # print two copies
    ("11-pcb-mount-coupon-unsliced", "robust", ("pcb_mount_coupon",)),
)
COMMON = {
    "layer_height": "0.2", "initial_layer_print_height": "0.2",
    "adaptive_layer_height": "0", "wall_generator": "arachne",
    "wall_loops": "6", "top_shell_layers": "6", "bottom_shell_layers": "6",
    "top_shell_thickness": "1.2", "bottom_shell_thickness": "1.2",
    "sparse_infill_density": "40%", "sparse_infill_pattern": "gyroid",
    "brim_type": "outer_only", "brim_width": "5", "brim_object_gap": "0.1",
    "curr_bed_type": "Textured PEI Plate", "enable_support": "0",
    "enable_prime_tower": "0", "skirt_loops": "0", "print_sequence": "by layer",
    "timelapse_type": "0", "only_one_wall_top": "0",
    "seam_slope_type": "none", "override_filament_scarf_seam_setting": "1",
    "initial_layer_speed": ["25"], "initial_layer_infill_speed": ["40"],
    "outer_wall_speed": ["60"], "inner_wall_speed": ["100"],
    "top_surface_speed": ["40"], "internal_solid_infill_speed": ["80"],
    "sparse_infill_speed": ["100"], "bridge_speed": ["25"],
}
PROCESS = {
    "insulated": {"wall_loops": "3", "top_shell_layers": "4", "bottom_shell_layers": "4",
                  "top_shell_thickness": "0.8", "bottom_shell_thickness": "0.8",
                  "sparse_infill_density": "8%", "sparse_infill_pattern": "honeycomb"},
    "solid": {"sparse_infill_density": "100%", "sparse_infill_pattern": "zig-zag"},
    "robust": {},
    "tray": {"wall_loops": "5", "sparse_infill_density": "100%",
             "sparse_infill_pattern": "zig-zag"},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(data):
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()


def read_stl(path):
    """Lossless float32 import: never repair, weld by tolerance, or rewrite source."""
    raw = path.read_bytes()
    require(len(raw) >= 84, f"Invalid STL: {path}")
    count = struct.unpack_from("<I", raw, 80)[0]
    require(count > 0 and len(raw) == 84 + count * 50, f"Expected binary STL: {path}")
    vertices, faces, ids = [], [], {}
    for row in struct.iter_unpack("<12fH", raw[84:]):
        face = []
        for point in (row[3:6], row[6:9], row[9:12]):
            require(all(math.isfinite(x) for x in point), f"Nonfinite vertex: {path}")
            if point not in ids:
                ids[point] = len(vertices)
                vertices.append(point)
            face.append(ids[point])
        faces.append(tuple(face))
    try:
        stats = measure(vertices, faces)
    except ValueError as error:
        raise ValueError(f"{path.name}: {error}") from error
    require(abs(stats["min_mm"][2]) < 0.025, f"Export not bed-oriented: {path}")
    return {"vertices": vertices, "faces": faces, "sha256": sha(raw), "stats": stats}


def measure(vertices, faces):
    edges, balance, parent = Counter(), Counter(), list(range(len(vertices)))
    volumes = []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for face in faces:
        a, b, c = (vertices[i] for i in face)
        ab, ac = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        cross = (ab[1]*ac[2] - ab[2]*ac[1], ab[2]*ac[0] - ab[0]*ac[2], ab[0]*ac[1] - ab[1]*ac[0])
        require(any(cross), "Degenerate triangle: run the project's export/mesh checks first")
        for i, j in zip(face, face[1:] + face[:1]):
            edge = tuple(sorted((i, j)))
            edges[edge] += 1
            balance[edge] += 1 if i < j else -1
            parent[find(i)] = find(j)
        volumes.append((face[0], sum(a[i] * cross[i] for i in range(3)) / 6))
    require(edges and all(n == 2 for n in edges.values()), "Open/nonmanifold STL edges")
    require(all(n == 0 for n in balance.values()), "Inconsistent mesh winding")
    shells = defaultdict(float)
    for i, volume in volumes:
        shells[find(i)] += volume
    require(sum(v > 0 for v in shells.values()) == 1 and sum(shells.values()) > 0,
            "Expected one positive-volume solid (inward cavity shells allowed)")
    low = [min(p[i] for p in vertices) for i in range(3)]
    high = [max(p[i] for p in vertices) for i in range(3)]
    return {"triangles": len(faces), "vertices": len(vertices), "min_mm": low, "max_mm": high,
            "size_mm": [high[i] - low[i] for i in range(3)], "volume_mm3": sum(shells.values()),
            "enclosed_mesh_voids": sum(v < 0 for v in shells.values())}


def profiles():
    folder = HERE / "profiles"
    provenance = json.loads((folder / "provenance.json").read_text())
    result = {}
    ignored = {"type", "name", "from", "instantiation", "setting_id", "description",
               "compatible_printers", "compatible_printers_condition", "filament_id"}
    for kind in ("machine", "process", "filament"):
        raw = (folder / f"{kind}.json").read_bytes()
        require(sha(raw) == provenance["flattened_sha256"][f"{kind}.json"], f"Profile hash changed: {kind}")
        data = json.loads(raw)
        require("inherits" not in data and "include" not in data, "Unresolved profile inheritance")
        result.update({k: v for k, v in data.items() if k not in ignored})
    require("machine: A1 mini" in result["machine_start_gcode"], "Missing A1 mini machine templates")
    result.update(COMMON)
    result.update({"printer_settings_id": MACHINE, "filament_settings_id": [FILAMENT],
                   "filament_colour": ["#D8E8E8"], "filament_ids": ["GFG99"]})
    return result, provenance


def settings(base, kind):
    return dict(base, **PROCESS[kind], print_settings_id=f"Cat feeder {kind} PETG 0.20 @A1M")


def layout(parts, meshes):
    """One centred row, no rotation/scaling; conservative separated brim rectangles."""
    width = sum(meshes[p]["stats"]["size_mm"][0] for p in parts) + GAP * (len(parts) - 1)
    require(width <= BED - 2*MARGIN, "Plate row too wide; review subdivision/layout")
    left, result = (BED - width)/2, {}
    for part in parts:
        s = meshes[part]["stats"]
        w, h, z = s["size_mm"]
        require(h <= BED - 2*MARGIN and z <= BED, f"Part too large for A1 mini: {part}")
        result[part] = [left - s["min_mm"][0], (BED - h)/2 - s["min_mm"][1], -s["min_mm"][2]]
        left += w + GAP
    return result


def xml_bytes(element):
    return ET.tostring(element, encoding="utf-8", xml_declaration=True)


def meta(parent, key, value):
    ET.SubElement(parent, "metadata", key=key, value=str(value))


def build_project(path, name, parts, meshes, config, provenance):
    offsets = layout(parts, meshes)
    model = ET.Element("model", {"unit": "millimeter", "xml:lang": "en-US", "xmlns": CORE})
    # Bambu gates its project metadata importer on this prefix. The custom
    # prerelease suffix and Designer explicitly identify our third-party writer.
    ET.SubElement(model, "metadata", name="Application").text = "BambuStudio-2.8.0-catfeeder-unsliced"
    ET.SubElement(model, "metadata", name="BambuStudio:3mfVersion").text = "1"
    ET.SubElement(model, "metadata", name="Designer").text = "cat-feeder stdlib project generator; not sliced by Bambu Studio"
    ET.SubElement(model, "metadata", name="Title").text = name
    resources, build = ET.SubElement(model, "resources"), ET.SubElement(model, "build")
    model_settings = ET.Element("config")
    plate = ET.Element("plate")
    for k, v in {"plater_id": "1", "plater_name": name, "locked": "false"}.items():
        meta(plate, k, v)
    source_info = {}
    for index, part in enumerate(parts):
        mesh_id, object_id = str(2*index+1), str(2*index+2)
        mesh = meshes[part]
        obj = ET.SubElement(resources, "object", id=mesh_id, type="model")
        geometry = ET.SubElement(obj, "mesh")
        verts, tris = ET.SubElement(geometry, "vertices"), ET.SubElement(geometry, "triangles")
        for point in mesh["vertices"]:
            ET.SubElement(verts, "vertex", dict(zip(("x", "y", "z"), (format(v, ".17g") for v in point))))
        for face in mesh["faces"]:
            ET.SubElement(tris, "triangle", dict(zip(("v1", "v2", "v3"), map(str, face))))
        assembly = ET.SubElement(resources, "object", id=object_id, type="model", name=part)
        ET.SubElement(ET.SubElement(assembly, "components"), "component", objectid=mesh_id, transform=IDENTITY)
        transform = "1 0 0 0 1 0 0 0 1 " + " ".join(format(v, ".17g") for v in offsets[part])
        ET.SubElement(build, "item", objectid=object_id, transform=transform, printable="1")
        obj_config = ET.SubElement(model_settings, "object", id=object_id)
        meta(obj_config, "name", part)
        meta(obj_config, "extruder", "1")
        ET.SubElement(obj_config, "metadata", face_count=str(len(mesh["faces"])))
        part_config = ET.SubElement(obj_config, "part", id=mesh_id, subtype="normal_part")
        for k, v in {"name": part, "matrix": MATRIX, "source_file": part + ".stl",
                     "source_object_id": "0", "source_volume_id": "0"}.items():
            meta(part_config, k, v)
        ET.SubElement(part_config, "mesh_stat", face_count=str(len(mesh["faces"])), edges_fixed="0",
                      degenerate_facets="0", facets_removed="0", facets_reversed="0", backwards_edges="0")
        instance = ET.SubElement(plate, "model_instance")
        for k, v in {"object_id": object_id, "instance_id": "0", "identify_id": str(index+1)}.items():
            meta(instance, k, v)
        source_info[part] = {"file": f"build/stl/{part}.stl", "sha256": mesh["sha256"], "mesh": mesh["stats"]}
    model_settings.append(plate)
    types = ET.Element("Types", xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
    for ext, content in {"rels": "application/vnd.openxmlformats-package.relationships+xml",
                         "model": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml",
                         "config": "application/octet-stream", "json": "application/json"}.items():
        ET.SubElement(types, "Default", Extension=ext, ContentType=content)
    rels = ET.Element("Relationships", xmlns="http://schemas.openxmlformats.org/package/2006/relationships")
    ET.SubElement(rels, "Relationship", Id="rel0", Target="/3D/3dmodel.model",
                  Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel")
    members = {"[Content_Types].xml": xml_bytes(types), "_rels/.rels": xml_bytes(rels),
               "3D/3dmodel.model": xml_bytes(model), "Metadata/model_settings.config": xml_bytes(model_settings),
               "Metadata/project_settings.config": json_bytes(config),
               "Metadata/cat-feeder-provenance.json": json_bytes({"status": "UNSLICED", "sources": source_info,
                    "generator_sha256": sha(Path(__file__).read_bytes()), "profiles": provenance})}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for key, value in sorted(members.items()):
            info = zipfile.ZipInfo(key, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, value)


def metadata(element):
    return {item.get("key"): item.get("value") for item in element.findall("metadata") if item.get("key")}


def verify(path, parts, meshes, expected):
    """Reopen serialized geometry/settings and compare every vertex, face and source."""
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, f"ZIP CRC failure: {path}")
        require(not any("gcode" in n.lower() or "slice_info" in n for n in archive.namelist()), "Expected UNSLICED archive")
        config = json.loads(archive.read("Metadata/project_settings.config"))
        require(config == expected, "Embedded settings differ from intended profiles/process")
        require(config["printer_model"] == "Bambu Lab A1 mini" and config["nozzle_diameter"] == ["0.4"], "Wrong machine")
        require(config["printable_area"] == ["0x0", "180x0", "180x180", "0x180"] and config["filament_type"] == ["PETG"], "Wrong bed/filament")
        source = json.loads(archive.read("Metadata/cat-feeder-provenance.json"))
        require(source["status"] == "UNSLICED", "Incorrect status")
        require(source["generator_sha256"] == sha(Path(__file__).read_bytes()), "Generator changed; regenerate projects")
        require(source["profiles"] == json.loads((HERE / "profiles/provenance.json").read_text()), "Profile provenance changed")
        cfg = ET.fromstring(archive.read("Metadata/model_settings.config"))
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
        require(root.get("unit") == "millimeter", "Wrong model units")
        tags = {m.get("name"): m.text for m in root.findall("m:metadata", NS)}
        require(tags.get("Application", "").startswith("BambuStudio-") and tags.get("BambuStudio:3mfVersion") == "1", "Missing Bambu project detection metadata")
        plate = cfg.findall("plate")
        require(len(plate) == 1 and metadata(plate[0])["plater_id"] == "1", "Wrong plate count/id")
        items = root.findall("m:build/m:item", NS)
        require(len(items) == len(parts) == len(plate[0].findall("model_instance")), "Wrong object count")
        records, boxes = {}, []
        for index, (part, item) in enumerate(zip(parts, items)):
            mesh = meshes[part]
            require(source["sources"][part]["sha256"] == mesh["sha256"], f"Stale source: {part}")
            object_id = item.get("objectid")
            obj = cfg.find(f"object[@id='{object_id}']")
            require(obj is not None and metadata(obj) == {"name": part, "extruder": "1"}, "Object identity/settings mismatch")
            assembly = root.find(f"m:resources/m:object[@id='{object_id}']", NS)
            component = assembly.find("m:components/m:component", NS)
            require(component.get("transform") == IDENTITY, "Unexpected component transform")
            mesh_id = component.get("objectid")
            require(obj.find("part").get("id") == mesh_id, "Part metadata mapping mismatch")
            part_config = obj.find("part")
            require(metadata(part_config) == {"name": part, "matrix": MATRIX, "source_file": part + ".stl",
                    "source_object_id": "0", "source_volume_id": "0"}, "Part settings/transform mismatch")
            stats = part_config.find("mesh_stat").attrib
            require(stats == {"face_count": str(len(mesh["faces"])), "edges_fixed": "0", "degenerate_facets": "0",
                             "facets_removed": "0", "facets_reversed": "0", "backwards_edges": "0"}, "Unexpected mesh repair metadata")
            instance = metadata(plate[0].findall("model_instance")[index])
            require(instance["object_id"] == object_id and instance["instance_id"] == "0", "Plate instance mismatch")
            geo = root.find(f"m:resources/m:object[@id='{mesh_id}']/m:mesh", NS)
            vertices = [tuple(float(v.get(a)) for a in ("x", "y", "z")) for v in geo.findall("m:vertices/m:vertex", NS)]
            faces = [tuple(int(t.get(a)) for a in ("v1", "v2", "v3")) for t in geo.findall("m:triangles/m:triangle", NS)]
            require(vertices == mesh["vertices"] and faces == mesh["faces"], f"Embedded geometry changed: {part}")
            t = [float(v) for v in item.get("transform").split()]
            require(len(t) == 12 and t[:9] == [1, 0, 0, 0, 1, 0, 0, 0, 1] and item.get("printable") == "1", "Orientation/scale/printability changed")
            s = mesh["stats"]
            low = [s["min_mm"][i] + t[9+i] for i in range(3)]
            high = [s["max_mm"][i] + t[9+i] for i in range(3)]
            require(abs(low[2]) < 1e-8 and high[2] <= BED, f"Not bed-seated: {part}")
            pad = BRIM + 0.1 + 0.5  # width + gap + conservative extrusion allowance
            box = [low[0]-pad, low[1]-pad, high[0]+pad, high[1]+pad]
            require(0 <= box[0] < box[2] <= BED and 0 <= box[1] < box[3] <= BED, f"Brim allowance outside bed: {part}")
            for other in boxes:
                require(box[2] <= other[0] or box[0] >= other[2] or box[3] <= other[1] or box[1] >= other[3], "Brim allowances overlap")
            boxes.append(box)
            records[part] = {"source_sha256": mesh["sha256"], "mesh": s, "placed_min_mm": low,
                             "placed_max_mm": high, "conservative_brim_bounds_xy_mm": box}
        return {"file": path.name, "sha256": sha(path.read_bytes()), "status": "UNSLICED",
                "process": {k: config[k] for k in sorted(set(COMMON) | set(PROCESS["insulated"]))}, "objects": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "plates")
    parser.add_argument("--verify-only", action="store_true", help="Recheck delivered archives against current STLs/settings")
    parser.add_argument("--require-part", action="append", default=[], choices=[p for _, _, parts in OPTIONAL_PLAN for p in parts],
                        help="Require an optional final export (repeatable)")
    args = parser.parse_args()
    base, provenance = profiles()
    for part in args.require_part:
        require((ROOT / "build/stl" / f"{part}.stl").is_file(), f"Missing required optional STL: {part}")
    plan = PLAN + tuple(entry for entry in OPTIONAL_PLAN
                        if all((ROOT / "build/stl" / f"{p}.stl").is_file() for p in entry[2]))
    meshes = {p: read_stl(ROOT / "build/stl" / f"{p}.stl") for _, _, parts in plan for p in parts}
    out = args.output.resolve()
    records = []
    if args.verify_only:
        require({p.name for p in out.glob("*.3mf")} == {f"{name}.3mf" for name, _, _ in plan},
                "Plate list differs from current exports; regenerate (restore any missing optional source first)")
        for name, kind, parts in plan:
            records.append(verify(out / f"{name}.3mf", parts, meshes, settings(base, kind)))
    else:
        out.mkdir(parents=True, exist_ok=True)
        expected_files = {f"{name}.3mf" for name, _, _ in plan} | {"plate-report.json", "README.md"}
        require(not (set(p.name for p in out.iterdir()) - expected_files), "Output contains unrelated files; select a dedicated output directory")
        with tempfile.TemporaryDirectory(prefix=".plates-", dir=out.parent) as temporary:
            stage = Path(temporary)
            for name, kind, parts in plan:
                path, config = stage / f"{name}.3mf", settings(base, kind)
                build_project(path, name, parts, meshes, config, provenance)
                records.append(verify(path, parts, meshes, config))
            for part, mesh in meshes.items():
                require(sha((ROOT / "build/stl" / f"{part}.stl").read_bytes()) == mesh["sha256"], f"STL changed during generation: {part}; rerun after export finishes")
            (stage / "plate-report.json").write_bytes(json_bytes({"status": "UNSLICED; no toolpath, print-time or filament-mass validation",
                        "profiles_revision": provenance["revision"], "plates": records}))
            (stage / "README.md").write_text("# UNSLICED cat-feeder prototype projects\n\nOpen each .3mf as a project in Bambu Studio.\n"
                "A1 mini / 0.4 mm / 0.20 mm / Generic PETG / Textured PEI.\n"
                "No G-code: slice and inspect before printing. Settings are editable.\n"
                "See ../../kb/printing.md for settings, quantities, limitations and validation.\n"
                "plate-report.json records source hashes, measured mesh dimensions and placement.\n"
                "Regenerate after STL exports change: python3 slicer/make_plates.py\n")
            for path in stage.iterdir():
                path.replace(out / path.name)
    print(f"PASS: {len(records)} UNSLICED projects, {len(meshes)} exact source meshes; settings/hashes/bed/brim allowances verified.")
    print(out)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        sys.exit(f"ERROR: {error}")
