# JLCPCB design rules

KiCad custom rule files from the 2026-10-25 review, derived from JLCPCB's
official capabilities pages retrieved that day (page copies in
`../revb/dfm/evidence/`, re-fetched by `../revb/dfm/retrieve_sources.py`). Copy one into a project as `<project>.kicad_dru`.

| File | Tier |
| --- | --- |
| `jlcpcb-2layer-minimum.kicad_dru` | Factory minima, 2-layer 1 oz — a hard floor, not a target |
| `jlcpcb-2layer-recommended.kicad_dru` | JLCPCB recommended values plus project margins — design to this |

Not covered by DRC and still to check by hand or script: PCBA component-to-edge
2.5 mm, fiducials/tooling holes, 4-layer inner hole-to-copper 0.3 mm, CPL
rotations against JLC's library footprints. See [the review](../../kb/review-2026-10-25.md).
