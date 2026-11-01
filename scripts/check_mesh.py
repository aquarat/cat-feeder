#!/usr/bin/env python3
"""Check exported geometry, using only Python's standard library.

Checks actual binary STL topology, connectedness, volume and build envelope.
Removes only exactly zero-area float32 export triangles, then requires the
remaining mesh to pass topology checks before saving that lossless cleanup.
The capacity solid is the bowl's empty volume, not a bounding-box estimate.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
PRINTS = ("sector", "hub", "drive", "deck_quarter", "insulation_coupon", "clip",
          "lid_access_coupon", "motor_bridge", "fan_inlet_coupon", "pcb_cradle", "pcb_mount_coupon",
          "closure_coupon_base", "closure_coupon_lid")


def measure(path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + 50 * count, f"Not a binary STL: {path}"
    vertices, ids, edges = [], {}, collections.Counter()
    parent = []
    volume = 0.0
    signed_faces = []
    retained_records = []

    def vertex(p):
        # STL vertices are float32 already. Decimal rounding here can collapse
        # valid short edges created by intersecting chamfers into zero-area faces.
        key = tuple(p)
        if key not in ids:
            ids[key] = len(vertices)
            vertices.append(key)
            parent.append(len(parent))
        return ids[key]

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for offset in range(84, len(data), 50):
        values = struct.unpack_from("<12fH", data, offset)
        a, b, c = (values[3:6], values[6:9], values[9:12])
        assert all(math.isfinite(v) for p in (a, b, c) for v in p)
        ab = [b[i]-a[i] for i in range(3)]
        ac = [c[i]-a[i] for i in range(3)]
        cross = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2],
                 ab[0]*ac[1]-ab[1]*ac[0]]
        if cross == [0, 0, 0]:
            # Complex chamfer/cell intersections can collapse when converted
            # to binary STL's float32 coordinates. No tolerance-based welding.
            continue
        retained_records.append(data[offset:offset+50])
        tri = [vertex(p) for p in (a, b, c)]
        assert len(set(tri)) == 3, f"Degenerate triangle: {path}"
        for i, j in zip(tri, tri[1:] + tri[:1]):
            edges[tuple(sorted((i, j)))] += 1
            parent[find(i)] = find(j)
        signed = (a[0]*(b[1]*c[2]-b[2]*c[1]) +
                  a[1]*(b[2]*c[0]-b[0]*c[2]) +
                  a[2]*(b[0]*c[1]-b[1]*c[0])) / 6
        volume += signed
        signed_faces.append((tri[0], signed))
    assert all(n == 2 for n in edges.values()), f"Non-manifold/open mesh: {path}"
    assert volume > 0, f"Inside-out or empty mesh: {path}"
    components = len({find(i) for i in range(len(vertices))})
    surface_volumes = collections.defaultdict(float)
    for i, signed in signed_faces:
        surface_volumes[find(i)] += signed
    # Enclosed honeycomb voids legitimately have separate inward-facing shells.
    assert sum(v > 0 for v in surface_volumes.values()) == 1, f"Detached solids: {path}"
    low = [min(p[i] for p in vertices) for i in range(3)]
    high = [max(p[i] for p in vertices) for i in range(3)]
    removed = count - len(retained_records)
    if removed:
        # All remaining edges/surfaces passed above: reject rather than patch
        # holes or non-manifold intersections introduced by a real CAD defect.
        path.write_bytes(data[:80] + struct.pack("<I", len(retained_records)) +
                         b"".join(retained_records))
        print(f"{path.name}: removed {removed} exactly collapsed float32 triangles")
    return {"triangles": len(retained_records), "surface_components": components,
            "removed_zero_area_triangles": removed,
            "enclosed_voids": sum(v < 0 for v in surface_volumes.values()),
            "min_mm": low, "max_mm": high,
            "size_mm": [high[i]-low[i] for i in range(3)],
            "volume_ml": volume/1000}


def main_plenum():
    """D35 study: only the parts that differ from the direct-contact build."""
    base = ROOT / "build/plenum"
    report = {}
    for part in ("deck_quarter", "motor_bridge", "plenum_baffle", "plenum_basin", "plenum_card_cap",
                 "plenum_fin_clip", "plenum_fin_clip_66", "plenum_fin_clip_90", "plenum_sensor_clip", "plenum_leak_clip",
                 "plenum_panel_pod", "plenum_inlet_keeper", "plenum_drive"):
        result = measure(base / "stl" / f"{part}.stl")
        assert all(v <= 170 for v in result["size_mm"]), f"Bed envelope: {part}"
        assert abs(result["min_mm"][2]) < 0.025, f"Not on bed: {part}"
        report[part] = result
    for part in ("shell", "lid"):
        report[part] = measure(base / "checks" / f"{part}.stl")
    report["source_sha256"] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "cad").glob("*.scad")) + sorted((ROOT / "cad").glob("*.json"))
        + sorted((ROOT / "cad/generated").glob("*"))
    }
    output = base / "geometry-report.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("PASS: plenum deck quarter, motor bridge, baffle, basin, card cap, fin clips, sensor clip, inlet keeper, "
          "basin probe clip, panel pod and plenum drive are connected, closed and fit 170 mm.")
    print(output.relative_to(ROOT))


def main():
    report = {}
    for part in (*PRINTS, "capacity"):
        result = measure(ROOT / "build/stl" / f"{part}.stl")
        if part in PRINTS:
            assert all(v <= 170 for v in result["size_mm"]), f"Bed envelope: {part}"
            assert abs(result["min_mm"][2]) < 0.025, f"Not on bed: {part}"
        report[part] = result
    for part in ("shell", "lid"):
        report[part] = measure(ROOT / "build/checks" / f"{part}.stl")
    capacity = report["capacity"]["volume_ml"]
    assert 50 <= capacity <= 65, f"Capacity/headroom out of design range: {capacity}"
    report["portion"] = {"brim_ml": capacity, "working_fill_ml": 40,
                         "headroom_ml": capacity - 40}
    report["source_sha256"] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "cad").glob("*.scad"))
    }
    output = ROOT / "build/geometry-report.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {len(PRINTS)} connected, closed meshes; each fits 170 mm envelope.")
    print(f"Bowl: {capacity:.2f} mL brim; {capacity-40:.2f} mL headroom at 40 mL fill.")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    import sys
    main_plenum() if "--plenum" in sys.argv[1:] else main()
