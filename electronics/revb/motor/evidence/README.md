# Evidence provenance — 2026-10-24

Third-party documents listed here are fetched with `scripts/fetch_references.py`.

- `a4988-datasheet.pdf`: directly downloaded from
  https://www.allegromicro.com/-/media/files/datasheets/a4988-datasheet.pdf .
  Allegro 4988-DS Rev. 8, 2022-04-05. `a4988-datasheet.txt` is an extraction;
  rotated headings are imperfect, so pages 18/19 were rendered and visually
  inspected (`a4988-page-18.png`, `a4988-page-19.png`).
- `TA-I-RL-series.pdf`: manufacturer-authored TA-I sheet TRL-XX0S001O,
  2014-08-06, retrieved from distributor mirror
  https://xonstorage.z8.web.core.windows.net/pdf/4138953_RL12FTNR300_link.pdf .
  Filename names R300; contents are the **RL series** covering the selected
  R330 value, size 12, F tolerance and TN packaging. This is not an exact-lot
  certificate. The exact selected JLC-linked PDF returned HTTP 403.
  Page 2 was rendered and inspected (`TA-I-RL-page-2.png`), confirming that the
  ±200 ppm/K table column includes RL12 (the ±300 ppm/K entry is for RL04).
- `Milliohm-HoLRT-series.pdf`: manufacturer-authored HoLRT Ho-A0,
  2020-04-27, retrieved from distributor mirror
  https://xonstorage.z8.web.core.windows.net/pdf/milliohm_holrt25122w1r1_apr22_xonlink.pdf .
  Electrical, dimension and land tables cover the selected 2512/2 W/1 Ω part.
  The five-second overload test is not a sub-millisecond pulse-energy rating.
  The exact selected JLC-linked PDF returned HTTP 403.
- `stock-evidence.json`: public JLC page hydration, exact-code matched using
  the project's established parser. Contains retrieval UTC/URL/raw HTML hash.
  `reused_evidence_from` records identify same-day revision-A snapshots reused
  without refreshing or modifying the frozen file. New parts were retrieved
  separately. The low-stock rejected C346765 is intentionally retained.
- Additional exact datasheet URLs for all fitted components are retained in
  `../circuit.json` and stock records. Direct requests for C22843 and C64705
  PDFs also returned HTTP 403; their values and metric packages are supported
  by the public exact-code catalogue. Earlier inherited parts use the original
  sourcing/drawing record in `electronics/pcb/SOURCING.md`.
- Motor manufacturer evidence:
  https://files.omc-stepperonline.com/17HS08-1004S_Full_Datasheet.pdf and
  https://www.omc-stepperonline.com/nema-17-bipolar-1-8deg-16ncm-22-6oz-in-1a-3-7v-42x42x20mm-4-wires-17hs08-1004s .
  Search-service extraction of the manufacturer drawing/product page was read;
  direct drawing download returned HTTP 403. No local motor PDF is claimed.
- TVS counterexample is manufacturer evidence, not a fitted BOM item:
  https://www.littelfuse.com/products/overvoltage-protection/tvs-diodes/surface-mount/smbj/smbj22a
  and SMBJ-series datasheet
  https://www.littelfuse.com/assetdocs/tvs-diodes-smbj-series-datasheet?assetguid=ba555e99-a12d-4f72-a0b6-86b06c67171e .

These sources distinguish downloaded primary documents, mirrored manufacturer
documents, public catalogue attributes and inherited evidence. Inventory and
package availability are not assembly approval or tested electrical performance.
