# Cat-feeder project working notes

- Read `kb/README.md`, `kb/decisions.md` and relevant evidence before changing
  architecture. The original brief is guidance; later owner decisions win.
- Maintain the project-local `kb/` with rationale, measured versus estimated
  results, outstanding questions and superseded decisions. Keep it linked.
- Prioritize simple construction, ordinary sourced parts, easy cleaning and
  tool-free daily servicing. No screws/bolts or added foam insulation.
- Electrical screw terminals are explicitly permitted by the latest PCB request;
  the no-screws rule applies to mechanical construction/daily servicing. PCB
  proposals should iterate against assembler stock, footprints and capabilities.
- Honeycomb belongs in Bambu print settings, not explicit CAD cells. Use one
  lid clip, a low sloped feeding approach, domed lid, thick walls and long slit
  vents. Internal equipment must have floor-supported, top-loaded bounded bays.
- Off-the-shelf metal cold plates are acceptable; avoid unnecessary custom
  fabrication. Keep purchase links and unresolved interface choices in the BOM.
- Latest prototype removes the small cold plates: test direct TEC ceramic to
  PETG contact. Treat wear/flatness as physical trial questions, not a proven
  reason to require protective metal. One bottom axial fan blows upward through
  the hot-side bay; distinguish airflow estimates from measured installed flow.
- When work is split between parallel agents, give them disjoint file
  ownership; avoid concurrent edits to CAD parameters or vendored code.
- `cad/lib/` is vendored from upstream projects; keep it unmodified and
  propose changes upstream.
- Manufacturer datasheets and SPICE models are not redistributed: add new ones
  to `references.json` (or the SPICE manifest) with URL and SHA-256, and fetch
  them with `scripts/fetch_references.py`; do not commit the files.
- Label geometry studies, simulation assumptions and physical test results
  distinctly. A rendered model is not a tested refrigerator or finished print.
- After CAD changes, export affected parts, check actual meshes and inspect
  relevant views. Do not publish STL/thermal numbers from an earlier revision.
