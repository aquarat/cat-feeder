#!/usr/bin/env python3
"""Write datasheets/MANIFEST.json: file, SHA-256, source URL, retrieval date, parts covered, what was checked.

    python3 datasheets_manifest.py

SOURCES is edited by hand when a PDF is added; the hash is recomputed from the file on every run, and
the run fails if a listed file is missing or a PDF in the folder is not listed.
"""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
DS = ROOT / 'datasheets'

# file: (source URL, retrieved, parts, facts checked against our footprints / design)
SOURCES = {
    'jst_xh.pdf': ('https://www.jst-mfg.com/product/pdf/eng/eXH.pdf', '2026-10-26', 'B2B..B12B-XH-A, XHP-n, SXH-001T-P0.6',
                   'pitch 2.5; header length 2.5(n-1)+4.9, depth 5.75, height 7.0; hole 0.9-1.0; mated height 9.8 (p1-p5)'),
    'jst_vh.pdf': ('https://www.jst-mfg.com/product/pdf/eng/eVH.pdf', '2026-10-26', 'B2P/B3P/B4P-VH, VHR-nN, SVH-21T-P1.1',
                   'pitch 3.96; length 3.96(n-1)+3.9, depth 8.5, height 10.9; hole 1.65-1.75; mated 16.5; 10 A (p1-p4)'),
    'molex_5566_header.pdf': ('https://www.molex.com/pdm_docs/sd/039281023_sd.pdf', '2026-10-26', '39-28-1023/1043/1063',
                              'pitch 4.20 x row 5.50; hole 1.40; height 12.8; mated 23.5 REF; latch on the pin n/2+1..n row'),
    'molex_5557_housing.pdf': ('https://www.molex.com/pdm_docs/sd/039012020_sd.pdf', '2026-10-26', '39-01-2020/2040/2060',
                               'receptacle length 5.4/9.6/13.8, depth 9.6 (+latch), height 19.6'),
    'molex_39000039.pdf': ('https://www.molex.com/pdm_docs/sd/039000039_sd.pdf', '2026-10-26', '39-00-0039',
                           'AWG 18-24, insulation 1.3-3.1 mm'),
    'molex_47053.pdf': ('https://www.molex.com/pdm_docs/sd/470531000_sd.pdf', '2026-10-26', '47053-1000',
                        'pitch 2.54, holes 1.02, peg hole 1.25 (KiCad stock 1.1: corrected in catalog.FP_DRILL_FIX), pins 10.0 high'),
    'phoenix_mstbva.pdf': ('https://static.chipdip.ru/lib/711/DOC011711569.pdf', '2026-10-26', 'MSTBVA 2,5/..-G-5,08 family (1755736)',
                           'Phoenix-generated sheet via a reseller mirror (phoenixcontact.com blocks scripts): pitch 5.08, hole 1.4, '
                           'height 12, mated 22 with MSTB-ST plug'),
    'phoenix_mstb_st.pdf': ('https://www.farnell.com/datasheets/2309822.pdf', '2026-10-26', 'MSTB 2,5/2-ST-5,08 (1757019)',
                            'Phoenix sheet via Farnell: 0.2-2.5 mm2, 12 A, screw M3; horizontal wire entry'),
    'samtec_ssw.pdf': ('https://suddendocs.samtec.com/catalog_english/ssw_th.pdf', '2026-10-26', 'SSW-119-01-T-S, SSW-108-01-T-S',
                       'body height 8.51, length 2.54n+0.51, width 2.41, tail 2.64 (-01), accepts 0.64 sq pins 3.68-6.35 deep'),
    'tracopower_tsr1.pdf': ('https://www.tracopower.com/products/tsr1.pdf', '2026-10-26', 'TSR 1-2450',
                            'Vin 6.5-36 V (5 V model), +-2 % set point, 11.7 x 7.5 x 10.1 mm, pins 1 Vin 2 GND 3 Vout at 2.54; '
                            '22 uF/50 V external input capacitor required above 32 V (C3)'),
    '1n5817-19.pdf': ('https://www.onsemi.cn/download/data-sheet/pdf/1n5817-d.pdf', '2026-10-26', '1N5817RLG',
                      'VF max 0.32 V @ 0.1 A, 0.45 V @ 1 A (1N5817); 20 V; DO-41 axial (onsemi.com blocks scripts, onsemi.cn mirror is onsemi)'),
    'tmc2209.pdf': ('https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf', '2026-10-26',
                    'TMC2209 (on the BTT V1.3 StepStick)', 'Rev 1.09: VS 4.75-29 V operating, 32 V abs max with inductive load (section 19); '
                    'MS1/MS2 internal pull-downs. Copy fetched earlier in this session; the ADI URL timed out on re-check, hash not re-verified'),
    '17hs08-1004s.pdf': ('https://www.omc-stepperonline.com/download/17HS08-1004S.pdf', '2026-10-26', 'StepperOnline 17HS08-1004S',
                         '1.0 A/phase, 3.7 ohm, 4.5 mH, 0.16 N m holding; leads A BLK, A- GRN, B RED, B- BLU'),
    'esp32_devkitc_v4_dimensions.pdf': ('https://dl.espressif.com/dl/schematics/esp32_devkitc_v4_dimensions.pdf', '2026-10-26',
                                        'ESP32-DevKitC-32E (V4)', 'PCB 48.26 x 27.94, rows 25.40, pitch 2.54, antenna +6.04, pin 19 1.29 from USB end'),
    'esp32_devkitc_v4_sch.pdf': ('https://dl.espressif.com/dl/schematics/esp32_devkitc_v4_sch.pdf', '2026-10-26', 'ESP32-DevKitC V4',
                                 'USB VBUS -> BAT760 -> EXT_5V (header 5V pin) -> AMS1117-3.3; pin names/order'),
    'ams1117.pdf': ('http://www.advanced-monolithic.com/pdf/ds1117.pdf', '2026-10-26', 'AMS1117-3.3 (on the DevKit)',
                    'dropout 1.1 V typ / 1.3 V max at 0.8 A'),
    'btt_tmc2209_v13_sch.pdf': ('https://raw.githubusercontent.com/bigtreetech/BIGTREETECH-Stepper-Motor-Driver/master/TMC2209/V1.3/Schematic/TMC2209%20V1.3-SCH.pdf',
                                '2026-10-26', 'BTT TMC2209 V1.3', 'header pin functions: 4 PDN_UART (no series R), 5 NC (R10 not fitted), 6 CLK 20 k to GND, EN 20 k pull-up'),
    'btt_tmc2209_v13_size.pdf': ('https://raw.githubusercontent.com/bigtreetech/BIGTREETECH-Stepper-Motor-Driver/master/TMC2209/V1.3/Schematic/TMC2209%20V1.3-SIZE.pdf',
                                 '2026-10-26', 'BTT TMC2209 V1.3', 'board 15.24 x 20.32, heatsink pad 8.40 x 12.88'),
    'btt_tmc2209_v13_manual.pdf': ('https://raw.githubusercontent.com/bigtreetech/BIGTREETECH-Stepper-Motor-Driver/master/TMC2209/V1.3/manual/BIGTREETECH%20TMC2209%20V1.3%20User%20Manual.pdf',
                                   '2026-10-26', 'BTT TMC2209 V1.3', 'UART default mode; motor supply stated 12-28 V (VMOT here is 12 V, at that minimum; the IC is 4.75-29 V)'),
    'tc74hc123ap.pdf': ('https://akizukidenshi.com/goodsaffix/TC74HC123AP_datasheet_ja_20161202.pdf', '2026-10-26', 'Toshiba TC74HC123AP',
                        "Toshiba's Japanese sheet via Akizuki (toshiba.semicon-storage.com blocks scripts): pinout, 2-6 V, tw ~ 1.0 Cx Rx, Rx 1 k-1 M, DIP-16"),
    'sn74hc573a.pdf': ('https://www.ti.com/lit/ds/symlink/sn74hc573a.pdf', '2026-10-26', 'SN74HC573AN', 'pinout p3, N20 package p31'),
    'uln2003a.pdf': ('https://www.ti.com/lit/ds/symlink/uln2003a.pdf', '2026-10-26', 'ULN2003AN', 'pinout p3, VCE(sat) p5, N16 p41'),
    'irf4905.pdf': ('https://www.infineon.com/dgdl/irf4905pbf.pdf?fileId=5546d462533600a4015355e32165197c', '2026-10-26', 'IRF4905PbF',
                    'G-D-S, VGS +-20 V, TO-220 dimensions p8'),
    'p6ke.pdf': ('https://store.comet.bg/download-file.php?id=18955', '2026-10-26', 'ST P6KE30A', "ST's P6KE sheet Rev 7 via distributor mirror (st.com timed out): VBR, Vc, DO-15"),
    'bzx79.pdf': ('https://static.chipdip.ru/lib/051/DOC032051641.pdf', '2026-10-26', 'Nexperia BZX79-C15', 'NXP/Nexperia sheet via mirror: Vz, SOD27'),
    '1n4148.pdf': ('https://www.vishay.com/docs/81857/1n4148.pdf', '2026-10-26', 'Vishay 1N4148-TAP', 'DO-35 dimensions p3'),
    '2n3904.pdf': ('https://www.onsemi.cn/download/data-sheet/pdf/2n3903-d.pdf', '2026-10-26', 'onsemi 2N3904BU', 'E-B-C, bulk straight leads 1.27 mm, formed 2.54 (p1, p7)'),
    'mrs25.pdf': ('https://store.comet.bg/download-file.php?id=18978', '2026-10-26', 'Vishay MRS25 (REJECTED)',
                  'kept as the reason MRS25 was dropped: minimum formed pitch 10.0 mm vs the 7.62 mm footprints'),
    'yageo_mf0.pdf': ('https://media.onlinecomponents.com/productfiles/mf-yag/yag-mf0204fte5215r.pdf', '2026-10-26', 'Yageo MF0204FTE52-xx',
                      'Yageo MF0 spec (Mar 2022 V.0) via distributor mirror: body 3.4 x 1.9, lead 0.45, M-forming pitch 6.0'),
    'murata_rde.pdf': ('https://docs.rs-online.com/264c/0900766b8156ed4f.pdf', '2026-10-26', 'Murata RDER71H104K0P1H03B, RDER71H105K2P1H03B',
                       'Murata RDE brochure: P1 = 2.5 mm spacing (K1 = 5.0), size 0 4.0 x 2.5 x 6.0, size 2 5.5 x 3.15 x 6.0'),
    'rubycon_yxf.pdf': ('https://www.rubycon.co.jp/wp-content/uploads/catalog-aluminum/YXF.pdf', '2026-10-26', 'Rubycon 50YXF22M5X11',
                        '5 x 11 mm; series marked obsolete'),
    'panasonic_fr.pdf': ('https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1259.pdf', '2026-10-26', 'Panasonic EEU-FR1H101 (and FR1H220 alternative)',
                         '8 x 11.5, F 3.5, lead 0.6, straight leads without suffix'),
    'littelfuse_rxef.pdf': ('https://store.comet.bg/download-file.php?id=28452', '2026-10-26', 'Littelfuse RXEF110',
                            'Littelfuse sheet via mirror (littelfuse.com 403): hold/trip, 72 V, 12.8 x 3.0 x 17.5 max'),
    'hlmp-1503.pdf': ('https://datasheet.lcsc.com/lcsc/43ffa2668b24824b0ec00197749e9bdb.pdf', '2026-10-26', 'Broadcom HLMP-1503',
                      "Broadcom AV02-1555EN via LCSC mirror: 3.17 dia, 6.35 high, cathode short lead"),
    'tracopower_tsr2n.pdf': ('https://www.tracopower.com/sites/default/files/products/datasheets/tsr2n_datasheet.pdf', '2026-10-26',
                             'TSR 2-24120N', 'Vin 15-36 V, 14 x 7.6 x 10.2, pin 1 Vin 2 GND 3 Vout, no traces under the body'),
    'omron_g2rl.pdf': ('https://omronfs.omron.com/en_US/ecb/products/pdf/en-g2rl.pdf', '2026-10-26', 'Omron G2RL-2 DC12',
                       '29 x 12.7 x 15.7, holes 1.3, coil 33.3 mA / 360 ohm, 8 A 30 VDC'),
    'littelfuse_297.pdf': ('https://static.chipdip.ru/lib/458/DOC012458305.pdf', '2026-10-26', 'Littelfuse 029707.5WXNV',
                           'MINI 297 series via mirror: 7.5 A part exists, 32 VDC, blade dims'),
    'keystone_3568.pdf': ('https://www.keyelco.com/userAssets/file/M65p42.pdf', '2026-10-26', 'Keystone 3568',
                          'catalogue p42: 16.0 x 6.73 x 7.37, four 1.60 holes on 9.9 x 3.40'),
    'oc_meanwell_gst160a.pdf': ('https://www.meanwell.com/Upload/PDF/GST160A/GST160A-SPEC.PDF', '2026-10-26', 'MEAN WELL GST160A24-R7B',
                                '24 V 6.67 A 160 W, 175 x 72 x 35 mm, R7B = 4-pin power DIN (1,4 +V; 2,3 -V)'),
    'oc_meanwell_gst120a.pdf': ('https://www.meanwell.com/Upload/PDF/GST120A/GST120A-SPEC.PDF', '2026-10-26', 'MEAN WELL GST120A24 (rejected)',
                                '120 W fails D32 (>= 150 W)'),
    'oc_kycon_kpjx-pm-4s.pdf': ('https://www.kycon.com/Pub_Eng_Draw/KPJX-PM-4S.pdf', '2026-10-26', 'Kycon KPJX-PM-4S panel socket',
                                '4-pin power DIN socket, 7.5 A per pin; 2 x M2.5 mounting holes (conflicts with the no-screws rule: CAD to clip it)'),
    'oc_kycon_kppx-4p.pdf': ('https://www.kycon.com/Pub_Eng_Draw/KPPX-4P.pdf', '2026-10-26', 'Kycon KPPX-4P plug (brick side reference)', 'mating plug'),
    'oc_kycon_kpjx-cm_series.pdf': ('https://static.chipdip.ru/lib/535/DOC011535691.pdf', '2026-10-26', 'Kycon KPJX-CM (cable-mount alternative)',
                                    'Kycon sheet via mirror'),
    'oc_ti_drv5033.pdf': ('https://www.ti.com/lit/ds/symlink/drv5033.pdf', '2026-10-26', 'TI DRV5033AJQLPG hall switch',
                          '2.5-38 V, open drain, omnipolar, TO-92: 1 VCC 2 GND 3 OUT'),
    'oc_adaptive_adv-127-135200-s.pdf': ('https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/3607/ADV-127-135200-S.pdf', '2026-10-26',
                                         'Adaptive/European Thermodynamics ADV-127-135200-S TEC', '4 A, 34.2 W, 40 x 40 x 4.2 mm, 350 mm 20 AWG leads'),
    'oc_rspro_neodymium_disc.pdf': ('https://docs.rs-online.com/08d2/A700000007817383.pdf', '2026-10-26', 'RS PRO NdFeB disc magnets', 'dimensions, axial magnetisation, 80 C max'),
    'oc_multicomp_t23_thermal_switch.pdf': ('https://www.farnell.com/datasheets/4810951.pdf', '2026-10-26', 'Multicomp T23 (sibling family of the RS PRO T24 thermostat)',
                                            'reference only: code pattern, +-3 C tolerance; not the purchased part'),
    'irlz44n.pdf': ('https://www.infineon.com/dgdl/irlz44npbf.pdf?fileId=5546d462533600a40153567217c32725', '2026-10-26', 'Infineon IRLZ44NPBF',
                    'logic-level N-FET 55 V 47 A, VGS(th) 1-2 V, RDS(on) 35 mOhm at VGS 4 V, TO-220 G-D-S (PDF text is font-encoded: read manually)'),
    'tl431.pdf': ('https://www.onsemi.cn/download/data-sheet/pdf/tl431-d.pdf', '2026-10-26', 'onsemi TL431AILPG',
                  'TO-92 pin 1 Reference, 2 Anode, 3 Cathode; Vref 2.495 V; cathode current >= 1 mA'),
    'bc327.pdf': ('https://www.onsemi.cn/download/data-sheet/pdf/bc327-d.pdf', '2026-10-26', 'onsemi BC327-25 (BC32725BU)',
                  'PNP -45 V -800 mA, TO-92 (case 29)'),
    'bat42.pdf': ('https://www.vishay.com/docs/85660/bat42.pdf', '2026-10-26', 'BAT42 (RS stocks the ST part)', '30 V small-signal Schottky, DO-35'),
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    listed = set(SOURCES)
    present = {p.name for p in DS.glob('*.pdf')}
    man = []
    for name, (url, date, parts, checked) in sorted(SOURCES.items()):
        p = DS / name
        if not p.exists():
            sys.exit(f'missing {name}')
        man.append(dict(file=name, sha256=sha(p), bytes=p.stat().st_size, source_url=url, retrieved=date, parts=parts, checked=checked))
    (DS / 'MANIFEST.json').write_text(json.dumps(dict(note='Primary-source datasheets used to verify D34 parts. Hashes recomputed by '
                                                           'datasheets_manifest.py.', files=man), indent=1) + '\n')
    extra = sorted(present - listed)
    print(len(man), 'files listed;', 'UNLISTED:' if extra else '', ' '.join(extra))


if __name__ == '__main__':
    main()
