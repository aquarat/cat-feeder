# Editable, UNSLICED Bambu Studio projects

From the project root, using Python 3.9+ (standard library only):

```sh
python3 slicer/make_plates.py
python3 slicer/make_plates.py --verify-only
```

Outputs: [`plates/`](plates/), six base single-plate `.3mf` projects, up to three
optional plates and a measured `plate-report.json`. Regeneration reads the
**current** eight required `build/stl/*.stl` exports, plus `lid_access_coupon.stl`
and `motor_bridge.stl`, `fan_inlet_coupon.stl` when present. Run after exports/mesh checks finish. Re-running replaces
generated deliverables; save manual Bambu edits elsewhere. `--output PATH` selects
a dedicated destination. No network, slicer executable or printer is used.

Open as **projects**, retaining their settings, in Bambu Studio; slice there and
inspect the preview. **These are not sliced or print-ready files.** GUI import,
actual toolpaths, bridges, extrusion, print time and mass remain unverified.
See [printing notes](../kb/printing.md) for the plate plan and physical trials.

For a final handoff that includes all current prototype coupons:

```sh
python3 slicer/make_plates.py --require-part lid_access_coupon --require-part motor_bridge --require-part fan_inlet_coupon
```

If an optional source disappears while its old plate exists, restore/re-export
the source before regeneration; verification rejects stale plate inventories.

## Implementation and provenance

- [`make_plates.py`](make_plates.py): explicit part allowlist, process settings,
  lossless binary-STL import, translation-only layout, ZIP/XML project writer and
  read-back verifier. STL inputs are never rewritten.
- [`profiles/`](profiles/): pinned, flattened official A1 mini 0.4 mm, 0.20 mm
  Standard and Generic PETG presets, including machine G-code **templates**.
  Templates are slicer settings, not generated printing G-code.
- [`fetch_profiles.py`](fetch_profiles.py): optional network refresh **from the
  same pinned commit**; resolves both inheritance and template includes. No need
  to run this to generate plates. Profile/source SHA-256 values and the upstream
  AGPL license are retained. Change the revision deliberately before updating.
- Rowing reference inspected read-only: the upstream rowing-computer project's
  `enclosure/sensor/slicer/`. Its macOS GUI/CLI workflow is
  unavailable on this Linux aarch64 host; the machine has Python but no Bambu,
  Orca, PrusaSlicer, NumPy or trimesh executable/module on the checked paths.

Schema was checked against Bambu's pinned
[`bbs_3mf.cpp`](https://github.com/bambulab/BambuStudio/blob/79df7ae309be398ed30c9f397c13c9911c2edc57/src/libslic3r/Format/bbs_3mf.cpp)
and [`PrintConfig.cpp`](https://github.com/bambulab/BambuStudio/blob/79df7ae309be398ed30c9f397c13c9911c2edc57/src/libslic3r/PrintConfig.cpp).
The archive contains standard 3MF meshes/components/build transforms,
`Metadata/model_settings.config`, `Metadata/project_settings.config`, and custom
provenance. Bambu's importer gates project recognition on the `Application`
metadata prefix `BambuStudio-`; the generator uses
`BambuStudio-2.8.0-catfeeder-unsliced` as a compatibility marker, with a separate
Designer field identifying the third-party generator. This is **not a claim that
Bambu Studio produced or opened these files**. Pattern tokens are `honeycomb`
and `zig-zag` (Bambu's rectilinear serialization), not invented display strings.

Verifier checks ZIP CRC, exact source hashes, every embedded vertex and triangle,
closed consistently wound edges, positive solid volume, settings equality,
object/part/plate relationships, no G-code payload, preserved orientation,
bed contact, 180 mm build bounds and conservative 5.6 mm brim allowances. It does
not test self-intersections, vertex-manifold topology, slicing, hardware or
thermal performance. Archives use fixed ZIP timestamps for reproducible bytes.
