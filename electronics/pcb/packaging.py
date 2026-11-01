#!/usr/bin/env python3
"""Inspect/mesh the actual KiCad outline polygon; no component-height inference.

Run after export.py in an isolated environment with trimesh, shapely, earcut.
"""
import json,math,pathlib,hashlib
import trimesh
from shapely.geometry import Polygon
root=pathlib.Path(__file__).parent
d=json.loads((root/'outline-study.json').read_text())
points=[(x+41,90-y) for x,y in d['outline_vertices_KiCad_mm']]
polygon=Polygon(points)
assert polygon.is_valid and not polygon.is_empty
mesh=trimesh.creation.extrude_polygon(polygon,height=1.6,engine='earcut')
path=root/'views/board-envelope.stl';mesh.export(path)
actual=trimesh.load(path,force='mesh')
assert actual.is_watertight and actual.is_winding_consistent and actual.volume>0
assert abs(actual.volume-polygon.area*1.6)<.1
report={'kind':'Packaging envelope of actual KiCad Edge.Cuts polygon, extruded 1.6mm; drills/components omitted',
        'outline_source_sha256':hashlib.sha256((root/'outline-study.json').read_bytes()).hexdigest(),
        'mesh_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'coordinate_system':'Enclosure-centred XY; nominal board bottom Z0; installed Z not assigned',
        'watertight':bool(actual.is_watertight),'winding_consistent':bool(actual.is_winding_consistent),
        'bounds_mm':actual.bounds.tolist(),'extents_mm':actual.extents.tolist(),
        'volume_mm3':float(actual.volume),'area_mm2':float(polygon.area),
        'area_change_vs_rectangle_percent':100*(polygon.area/d['rounded_rectangle_baseline_area_mm2']-1)}
(root/'mesh-check.json').write_text(json.dumps(report,indent=2)+'\n')
outline=' '.join(f'{x:.4f},{-y:.4f}' for x,y in points)
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-165 -175 495 350" width="1485" height="1050">
<rect x="-165" y="-175" width="495" height="350" fill="#f8fafc"/>
<g fill="none" stroke-width=".8">
<circle r="146" stroke="#334155"/><circle r="141" stroke="#94a3b8" stroke-dasharray="2 2"/>
<rect x="-60" y="-60" width="120" height="120" fill="#dbeafe" stroke="#2563eb"/>
<circle r="{math.hypot(60,60):.6f}" stroke="#60a5fa" stroke-dasharray="2 2"/>
<polygon points="{outline}" fill="#99f6e4" stroke="#0f766e"/>
<rect x="91" y="-40" width="50" height="80" rx="2" stroke="#f97316" stroke-dasharray="2 1"/>
<path d="M -150 0 H 150 M 0 -150 V 150" stroke="#94a3b8" stroke-width=".3"/>
</g>
<g font-family="sans-serif" font-size="5" fill="#0f172a">
<text x="-150" y="-160" font-size="7">Crescent controller — 2D packaging study</text>
<text x="-35" y="0">120 × 120 mm fan</text>
<text x="165" y="-110" font-size="6">Current outline</text>
<text x="165" y="-98">R141 outer / R91 inner</text>
<text x="165" y="-88">58.12 × 80 mm bounding box</text>
<text x="165" y="-78">50 mm radial band; 2 mm fillets</text>
<text x="165" y="-68">4083.21 mm² PCB area</text>
<text x="165" y="-58">+2.17% vs rounded 50 × 80 baseline</text>
<text x="165" y="-35">Bore R146: nominal 5 mm radial gap</text>
<text x="165" y="-25">Fan bounding circle: 6.15 mm gap</text>
<text x="165" y="-15">Orange: rectangular baseline overlay</text>
<text x="165" y="10" font-size="6">Not a housing fit approval</text>
<text x="165" y="22">Sink/post keepouts not included.</text>
<text x="165" y="32">Antenna/connector/harness space open.</text>
<text x="165" y="42">Floor Z28; PCB installed Z undecided.</text>
<text x="165" y="52">Board rotation around enclosure open.</text>
<text x="-150" y="165">Derived from current KiCad outline. STEP and STL are packaging aids; no populated 3D assembly.</text>
</g></svg>'''
(root/'views/packaging.svg').write_text(svg)
print(json.dumps(report,indent=2))
