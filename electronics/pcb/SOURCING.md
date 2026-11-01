# Supplier iteration and footprint record

Public sources checked 2026-10-24; no account operations, uploads, orders or supplier contact. Stock numbers below are JLC's exact `overseasStockCount` field, with the separate `canPresaleNumber` retained in [stock-evidence.json](stock-evidence.json). Neither proves inventory available for a particular assembly service or quantity.

| Use | Exact candidate / JLC code | Direct stock | Footprint and selection rationale |
|---|---|---:|---|
| U1 | ESP32-WROOM-32E-N4 [C701341](https://jlcpcb.com/partdetail/C701341) | 37,839 | Native WROOM-32E module footprint; 4 MB flash; module assembler-fitted, not a separate DevKit |
| U2 | AP2112K-3.3TRG1 [C51118](https://jlcpcb.com/partdetail/C51118) | 13,542 | SOT-23-5; thermal qualification remains necessary |
| U3/U4 | SN74LVC1G125DBVR [C23654](https://jlcpcb.com/partdetail/C23654) | 164,869 | SOT-23-5, independently gated TX/RX; input tolerance and Ioff features from TI data sheet |
| Q1 | MMBT3904 [C20526](https://jlcpcb.com/partdetail/C20526) | 2,047,043 | SOT-23, pins B/E/C 1/2/3; open-collector fan PWM, predictable base drive |
| J1/J16/J17 | Phoenix MKDS 1,5/2-5,08, **1715721**, [C5183929](https://jlcpcb.com/partdetail/C5183929) | 991 | Exact native 5.08 mm Phoenix footprint, 1.3 mm holes; 443 presale field; manual-weld metadata |
| C10 | Panasonic **EEUFR1H101B** [C713402](https://jlcpcb.com/partdetail/C713402) | 4,808 | 100 µF/50 V, Ø8 × 11.5 mm body, **5 mm formed/taped lead pitch**, 0.6 mm leads; native D8/P5 footprint, 0.8 mm holes |
| J14/J15 | BOOMELE 2.54-1×8P female [C27438](https://jlcpcb.com/partdetail/C27438) | 88,313 | 1×8 socket, 2.54 mm pitch, catalogue 8.5 mm height/3.2 mm tails/3 A; native socket footprint, 1 mm holes |
| J2/J4/J5/J6/J7/J9 | BOOMELE 2.54-1×3P male [C49257](https://jlcpcb.com/partdetail/C49257) | 196,922 | Native 1×3 header, 2.54 mm pitch/1 mm holes; catalogue 0.64 mm square pins, 3 mm tails, 6 mm mating pins |
| J3/J8/J11 | ZHOURI 2.54-1×4 [C5116483](https://jlcpcb.com/partdetail/C5116483) | 32,382 | Native 1×4 header, 2.54 mm pitch; exact housing/tail drawing remains quote-stage confirmation |
| J10/J12/J13 | Hong Cheng HC-PZ254-11.5L-1x2PZ [C27985187](https://jlcpcb.com/partdetail/C27985187) | 31,207 | Native 1×2 header, 2.54 mm pitch; catalogue 2.5 mm insulation, 6 mm mating pins/3 mm tails, 3 A |
| R1–R21 | UNI-ROYAL 0603: [10k C25804](https://jlcpcb.com/partdetail/C25804), [100k C25803](https://jlcpcb.com/partdetail/C25803), [4.7k C23162](https://jlcpcb.com/partdetail/C23162), [1k C21190](https://jlcpcb.com/partdetail/C21190) | millions each | Native 0603 resistor footprint; R20/R21 use existing 0603WAF1002T5E/C25804 selection |
| C1–C9/C11 | [100n C14663](https://jlcpcb.com/partdetail/C14663), [10µ/25V C15850](https://jlcpcb.com/partdetail/C15850), [1µ/50V C15849](https://jlcpcb.com/partdetail/C15849) | millions each | 100 nF/1 µF: 0603; 10 µF: 0805. Effective ceramic capacitance under bias remains an electrical design consideration |

### Capacitor substitution was a footprint change

[Panasonic's exact EEUFR1H101B product page](https://industrial.panasonic.com/ww/products/pt/aluminum-cap-lead/models/EEUFR1H101B) confirms 5.0 mm lead pitch, 8.0 mm body diameter, 11.5 mm body length, 870 mArms ripple at 100 kHz, and 61 mΩ maximum **impedance** at 100 kHz. This impedance is not a frequency-independent ESR. [Series data sheet](https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ast-ind-152839.pdf) distinguishes the 3.5 mm straight-lead version from 5 mm B-taped form; it lists 6000 h at 105°C for this size/rating. Actual motor ripple and voltage spikes remain unmeasured.

Earlier candidate **EEUFR1H101 / C178702** had only 5 in stock and zero presale field; superseded. AISHI **ERF1HM101F12OT / C724505** had 8556 in stock and catalogue-compatible D8/P3.5 dimensions. However, the accessible [manufacturer RF-series sheet](https://www.aishi.com/files/RF.pdf) ([cached evidence](datasheets/AISHI-RF.pdf); fetch with `scripts/fetch_references.py`) listed a nearby F11 size rather than exact F12; no exact ripple/impedance qualification was established. Superseded by the documented Panasonic B variant instead of silently transferring a nearby part's ratings.

### Other iterations and evidence limits

- Review B1 adds two existing-family 10 kΩ resistors, bringing assembly to **54 parts: 36 SMT + 18 THT**. No new catalogue research or stock refresh was needed; the snapshot remains historical inventory evidence. Review B2 now exports body centroids for all THT parts and preserves centred SMT origins. [Exact-code reconciliation](assembly-reconciliation.json) records pin 1, polarity, antenna/wire entry and explicitly pending supplier zero angles. [Fix provenance](REVIEW-FIXES.md); D25 HOLD remains until focused independent recheck.

- A 2N7002 fan stage was rejected in favour of the bipolar transistor: low gate-threshold voltage alone does not establish an adequate low on-resistance at 3.3 V. The selected stage has 4.7 kΩ base drive and 100 kΩ base-emitter pull-down. Validate actual fan pull-up current and switching waveform.
- The dual SN74LVC2G125DCUR **C21404** showed direct JLC stock 4668, superseding an indexed out-of-stock impression. Two single gates were retained for their ordinary SOT-23-5 pitch, larger direct stock and layout flexibility, not because the dual was unavailable.
- ZHOURI 1×2 **C5116481** showed zero stock; replaced by **C27985187**.
- Phoenix's public page labels a soldering category differently from its `manualWeld` hydration metadata. Confirm mixed-process line eligibility; the electrical screw-terminal allowance does not imply every assembly tier fits it automatically.
- Header pitch/count/envelope checks use [LCSC C27438](https://www.lcsc.com/product-detail/C27438.html), [C49257](https://www.lcsc.com/product-detail/C49257.html), [C5116483](https://www.lcsc.com/product-detail/C5116483.html) and [C27985187](https://www.lcsc.com/product-detail/C27985187.html). Linked LCSC PDF downloads returned HTTP 403 in this environment. Exact terminal profiles, hole tolerances and bought-module mating fit require the supplier drawings/samples; catalogue checks are not a physical fit test.
- Native KiCad 9 symbols/footprints provide pad-number mappings; local copies preserve exact geometry. The ESP32 footprint's layer keepout was specialized to the two enabled copper layers, without altering pads. Original 3D-model library references remain optional dependencies; no complete 3D assembly is claimed.

Device references: [Espressif WROOM-32E data sheet](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf), [TI SN74LVC1G125](https://www.ti.com/lit/ds/symlink/sn74lvc1g125.pdf), [Diodes AP2112](https://www.diodes.com/assets/Datasheets/AP2112.pdf), [Pololu A4988 carrier](https://www.pololu.com/product/1182). External regulator/TEC purchase rationale remains in [TEC control](../../kb/tec-control.md) and the [main BOM](../../BOM.md).
