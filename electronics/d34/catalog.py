"""Part catalogue for the D34 boards: symbol, footprint, orderable part and
installed heights. Sourcing fields are filled from datasheet checks recorded in
README.md / kb/d34-controller.md; 'verify' marks anything not yet checked.
"""
import d34lib as L

# ----------------------------------------------------------- module geometry
# ESP32-DevKitC-32E (V4), Espressif dimension drawing esp32_devkitc_v4_dimensions.pdf:
# 2 x 19 pins, 2.54 mm pitch, rows 25.40 mm apart, PCB 27.94 x 48.26 mm,
# pin 1 centre 1.25 mm from the PCB end, antenna 6.04 mm beyond that end,
# pin 19 centre 1.29 mm from the USB end. 5V pin = EXT_5V (USB VBUS via BAT760 D3).
DEVKIT_ROW_SPACING = 25.40
DEVKIT_PINS = 19
DEVKIT_BODY = (54.30, 27.94)       # overall length incl. antenna x width
DEVKIT_PIN1_TO_ANTENNA_END = 7.29  # 1.25 + 6.04
DEVKIT_PIN19_TO_USB_END = 1.29
# StepStick (Pololu A4988 / BTT / FYSETC TMC2209): 2 x 8, rows 12.70 mm apart, 15.24 x 20.32 mm.
STEPSTICK_ROW_SPACING = 12.70
STEPSTICK_BODY = (15.24, 20.32)

# DevKitC V4 header pin names (Espressif user guide), pin 1 at the antenna end.
DEVKIT_J2 = ['3V3', 'EN', 'IO36', 'IO39', 'IO34', 'IO35', 'IO32', 'IO33', 'IO25', 'IO26',
             'IO27', 'IO14', 'IO12', 'GND', 'IO13', 'SD2', 'SD3', 'CMD', '5V']
DEVKIT_J3 = ['GND', 'IO23', 'IO22', 'TXD0', 'RXD0', 'IO21', 'GND', 'IO19', 'IO18', 'IO5',
             'IO17', 'IO16', 'IO4', 'IO0', 'IO2', 'IO15', 'SD1', 'SD0', 'CLK']
# StepStick rows viewed from the component side, VMOT at the top right (Pololu layout).
# Pin 4/5/6 differ: A4988 MS3/RESET/SLEEP; BTT TMC2209 PDN_UART/(PDN, NC)/CLK;
# FYSETC TMC2209 TX(1k to PDN)/RX(PDN)/(CLK, NC). See README for the jumper rules.
SS_LEFT = ['EN', 'MS1', 'MS2', 'MS3/PDN', 'RST/PDN', 'SLP/CLK', 'STEP', 'DIR']
SS_RIGHT = ['VMOT', 'GND', '2B', '2A', '1A', '1B', 'VDD', 'GND']


def devkit_fp():
    n = DEVKIT_PINS; L_ = (n - 1) * 2.54
    # Rows along +Y; pad k (row J2) and n+k (row J3). Body: antenna end at y<0.
    w = DEVKIT_BODY[1]; off = (w - DEVKIT_ROW_SPACING) / 2
    body = (-off, -DEVKIT_PIN1_TO_ANTENNA_END, DEVKIT_ROW_SPACING + off, L_ + DEVKIT_PIN19_TO_USB_END)
    return L.socket_rows_fp('ESP32-DevKitC-32E_Socket', 2, 2.54, n, DEVKIT_ROW_SPACING,
                            'Two 1x19 2.54 mm female headers for Espressif ESP32-DevKitC-32E (V4); row J2 = pads 1-19, J3 = pads 20-38; pin 1 at antenna end', body,
                            body_courtyard=False)


def stepstick_fp():
    return L.socket_rows_fp('StepStick_Socket_2x8_W12.70mm', 2, 2.54, 8, STEPSTICK_ROW_SPACING,
                            'Two 1x8 2.54 mm female headers, rows 12.70 mm apart (Pololu A4988 / TMC2209 StepStick); left = pads 1-8 top-down, right = pads 9-16 top-down',
                            (-1.27, -1.27, 13.97, 19.05))


def radial_box_fp(name, pitch, bl, W, drill, pad, descr):
    """Two-lead radial part with a rectangular body bl (along the leads) x W, centred between the pads."""
    cx = pitch / 2; x1, x2, y1, y2 = cx - bl / 2, cx + bl / 2, -W / 2, W / 2
    def rect(layer, a, b, c, d, w):
        return ' '.join(f'(fp_line (start {p[0]:.3f} {p[1]:.3f}) (end {q[0]:.3f} {q[1]:.3f}) (stroke (width {w}) (type solid)) (layer "{layer}"))'
                        for p, q in [((a, b), (c, b)), ((c, b), (c, d)), ((c, d), (a, d)), ((a, d), (a, b))])
    m = 0.12
    return (f'(footprint {L.q(name)} (version 20241229) (generator "d34lib") (layer "F.Cu") (descr {L.q(descr)}) (attr through_hole) '
            f'(fp_text reference "REF**" (at {cx:.2f} {y1 - 1.5:.2f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)))) '
            f'(fp_text value {L.q(name)} (at {cx:.2f} {y2 + 1.5:.2f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15)))) '
            f'{rect("F.Fab", x1, y1, x2, y2, 0.1)} {rect("F.SilkS", x1 - m, y1 - m, x2 + m, y2 + m, 0.12)} '
            f'{rect("F.CrtYd", x1 - 0.25, y1 - 0.25, x2 + 0.25, y2 + 0.25, 0.05)} '
            f'(pad "1" thru_hole rect (at 0 0) (size {pad} {pad}) (drill {drill}) (layers "*.Cu" "*.Mask")) '
            f'(pad "2" thru_hole circle (at {pitch:.3f} 0) (size {pad} {pad}) (drill {drill}) (layers "*.Cu" "*.Mask")))')


CUSTOM_FP = {'ESP32-DevKitC-32E_Socket': devkit_fp, 'StepStick_Socket_2x8_W12.70mm': stepstick_fp,
             # Littelfuse RXEF110: 12.8 x 3.0 mm max body, kinked leads 4.3-5.8 apart, 0.81 mm leads (RXEF p4/p6)
             'PTC_Radial_L13.0mm_W3.2mm_P5.08mm': lambda: radial_box_fp('PTC_Radial_L13.0mm_W3.2mm_P5.08mm', 5.08, 13.0, 3.2, 1.1, 1.9,
                                                                       'Littelfuse RXEF110 radial PTC, body 12.8 x 3.0 mm max'),
             # Murata RDE size 2, P1 lead code: 5.5 x 3.15 mm body, 2.5 mm lead spacing, 0.5 mm leads (RDE p2)
             'PTC_Radial_L8.0mm_W3.2mm_P5.08mm': lambda: radial_box_fp('PTC_Radial_L8.0mm_W3.2mm_P5.08mm', 5.08, 8.0, 3.2, 0.8, 1.5,
                                                                      'Littelfuse RXEF050 radial PTC, body 7.9 x 3.0 mm max'),
             'C_Rect_L5.5mm_W3.2mm_P2.50mm': lambda: radial_box_fp('C_Rect_L5.5mm_W3.2mm_P2.50mm', 2.5, 5.6, 3.25, 0.8, 1.5,
                                                                  'Murata RDE size 2 radial MLCC, 5.5 x 3.15 mm, 2.5 mm leads')}

DK = 'https://www.digikey.co.uk/en/products/result?keywords={}'
LC = 'https://www.lcsc.com/search?q={}'

R_FP = 'Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P7.62mm_Horizontal'
RS = 'https://uk.rs-online.com/web/p/{}'
FN = 'https://uk.farnell.com/{}'
# kind: sym, fp, mfr, mpn, desc, h = installed body height above the board (mm),
# rs = RS Components UK stock number (supplier='RS' unless stated), pack = RS sales pack (pieces),
# ds = datasheet file in datasheets/ (see datasheets/MANIFEST.json), check = what was verified and how.
# Sourcing snapshot (stock, price breaks, date) lives in sourcing/ and kb/d34-sourcing.md.
K = {
    # Vishay MRS25 (0207) was dropped: its datasheet minimum formed pitch is 10.0 mm, and the ctrl grid
    # only allows 7.62 mm. Yageo MF0204: body 3.4 x 1.9 mm, factory forming pitch 6.0 mm -> 7.62 is easy.
    'R': dict(sym='Device:R', fp=R_FP, mfr='Yageo', mpn='MF0204FTE52-{v}', h=2.1, rs='by value (see YAGEO_RS)', pack=100,
              ds='yageo_mf0.pdf', check='verified: body 3.4+-0.3 x 1.9+-0.2 mm, lead 0.45 mm, M-forming P 6.0 mm (Yageo MF0 spec p3, p9)',
              desc='Resistor, metal film MF0204, 0.4 W, 1 %, axial'),
    # Murata lead code P1 = 2.5 mm spacing (K1, first chosen, is 5.0 mm): RDE brochure p2.
    'C100n': dict(sym='Device:C', fp='Capacitor_THT:C_Rect_L4.0mm_W2.5mm_P2.50mm', mfr='Murata', mpn='RDER71H104K0P1H03B', h=6.5,
                  rs='190-2933', pack=10, ds='murata_rde.pdf',
                  check='verified: size 0 = 4.0 W x 2.5 T x 6.0 H mm, lead 0.5, P1 = 2.5 mm (RDE p2); h incl. coating allowance',
                  desc='100 nF 50 V X7R radial MLCC'),
    'C1u': dict(sym='Device:C', fp='d34:C_Rect_L5.5mm_W3.2mm_P2.50mm', mfr='Murata', mpn='RDER71H105K2P1H03B', h=6.5,
                rs='190-2943', pack=10, ds='murata_rde.pdf',
                check='verified: size 2 = 5.5 W x 3.15 T x 6.0 H mm, lead 0.5, P1 = 2.5 mm (RDE p2); custom footprint to that outline',
                desc='1 uF 50 V X7R radial MLCC'),
    'CP100u': dict(sym='Device:C_Polarized', fp='Capacitor_THT:CP_Radial_D8.0mm_P3.50mm', mfr='Panasonic', mpn='EEU-FR1H101', h=13.0,
                   rs='708-3894', pack=10, ds='panasonic_fr.pdf', check='verified: 8 x 11.5 mm (L+1.5 max), F 3.5 mm, lead 0.6 mm, straight leads (FR p1, p6)', desc='100 uF 50 V low-ESR electrolytic, 8 x 11.5 mm'),
    'CP22u': dict(sym='Device:C_Polarized', fp='Capacitor_THT:CP_Radial_D5.0mm_P2.00mm', mfr='Rubycon', mpn='50YXF22M5X11', h=12.5,
                  rs='224-4331', pack=5, ds='rubycon_yxf.pdf',
                  check='verified: 5 x 11 mm, 150 mA ripple (YXF p2); series marked obsolete by Rubycon but RS stock 1365 (2026-10-26); '
                        'drop-in: Panasonic EEU-FR1H220 (FR p1, F 2.0 mm)', desc='22 uF 50 V electrolytic, 5 x 11 mm'),
    'D_5817': dict(sym='Diode:1N5817', fp='Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal', mfr='onsemi', mpn='1N5817RLG', h=3.0,
                   rs='625-4972', pack=5, ds='1n5817-19.pdf', check='verified: VF max 0.32 V @ 0.1 A, 0.45 V @ 1 A; 20 V; DO-41 (onsemi p2)',
                   desc='Schottky 20 V 1 A, DO-41'),
    'D_5817S': dict(sym='Diode:1N5817', fp='Diode_THT:D_DO-41_SOD81_P7.62mm_Horizontal', mfr='onsemi', mpn='1N5817RLG', h=3.0,
                    rs='625-4972', pack=5, ds='1n5817-19.pdf', check='verified (onsemi p2); 7.62 mm bend on the DO-41 body (<= 5.2 mm)',
                    desc='Schottky 20 V 1 A, DO-41 (K1 coil flyback)'),
    'D_4148': dict(sym='Diode:1N4148', fp='Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal', mfr='Vishay', mpn='1N4148-TAP', h=2.0,
                   rs='700-3674', pack=250, ds='1n4148.pdf', check='verified: DO-35 3.4 x 1.75 mm, lead 0.55 (Vishay p3)', desc='Signal diode 100 V, DO-35'),
    'DZ15S': dict(sym='Device:D_Zener', fp='Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal', mfr='Nexperia', mpn='BZX79-C15,133', h=2.0,
                  rs='136-4852', pack=100, ds='bzx79.pdf', check='verified: Vz 13.8-15.6 V @ 5 mA; SOD27 4.25 x 1.85 mm (p5, p9)', desc='Zener 15 V 0.5 W, DO-35 (P-FET gate clamp)'),
    'TVS30': dict(sym='Device:D_Zener', fp='Diode_THT:D_DO-15_P12.70mm_Horizontal', mfr='STMicroelectronics', mpn='P6KE30A', h=3.6,
                  rs='485-9323', pack=10, ds='p6ke.pdf', check='verified: VRM 26 V, VBR 28.5-31.5 V @ 1 mA, Vc 41.5 V @ 14.5 A; DO-15 6.75 x 3.53 mm, lead 0.88 max (ST p3, p6)', desc='TVS 600 W unidirectional 25.6 V Vwm, DO-15'),
    'LED_G': dict(sym='Device:LED', fp='LED_THT:LED_D3.0mm', mfr='Broadcom', mpn='HLMP-1503', h=6.4, rs='180-8502', pack=10,
                  ds='hlmp-1503.pdf', check='verified: D 3.17, H 6.35 max, leads 2.54 nominal, cathode = short lead, hole 0.98-1.08 (p1, p11)',
                  desc='3 mm green LED'),
    'IRF4905': dict(sym='Transistor_FET:IRF4905', fp='Package_TO_SOT_THT:TO-220-3_Vertical', mfr='Infineon', mpn='IRF4905PBF', h=20.6,
                    rs='540-9799', pack=1, ds='irf4905.pdf', check='verified: 1 G 2 D(tab) 3 S, VGS +-20 V; TO-220 16.51 + lead shoulder -> ~20.6 mm seated (p1, p8)', desc='P-MOSFET -55 V, TO-220 (reverse-polarity switch)'),
    # Bulk (BU) 2N3904 has straight leads on 1.27 mm (onsemi p7). The 1.27 mm inline footprint cannot give the
    # 0.25 mm annular ring the DRC requires, so the 2.54 mm 'Wide' footprint stays: splay the two outer leads
    # by ~1.3 mm (as onsemi forms the TA/ammo version, 2.40-2.80 mm).
    '2N3904': dict(sym='Transistor_BJT:2N3904', fp='Package_TO_SOT_THT:TO-92_Inline_Wide', mfr='onsemi', mpn='2N3904BU', h=8.0,
                   rs='843-1575', pack=50, ds='2n3904.pdf',
                   check='verified: E-B-C facing the flat, straight leads 1.15-1.39 mm, body 5.2 x 4.2 x 5.33 (p1, p7); h incl. ~2.5 mm standoff',
                   desc='NPN 40 V 200 mA, TO-92'),
    'ULN2003': dict(sym='Transistor_Array:ULN2003A', fp='Package_DIP:DIP-16_W7.62mm', mfr='Texas Instruments', mpn='ULN2003AN', h=5.1,
                    rs='436-8451', pack=1, ds='uln2003a.pdf', check='verified: pinout p3, VCE(sat) 0.9 V @ 100 mA, N16 rows 7.62, 5.08 max (p3, p5, p41)', desc='7 x Darlington sink 50 V 500 mA, clamp diodes, DIP-16'),
    'HC123': dict(sym=('74HC123', [('1', '1~{A}', 'input'), ('2', '1B', 'input'), ('3', '1~{CLR}', 'input'),
                                   ('14', '1Cext', 'passive'), ('15', '1Rext/Cext', 'passive'),
                                   ('9', '2~{A}', 'input'), ('10', '2B', 'input'), ('11', '2~{CLR}', 'input'),
                                   ('6', '2Cext', 'passive'), ('7', '2Rext/Cext', 'passive')],
                       [('16', 'VCC', 'power_in'), ('13', '1Q', 'output'), ('4', '1~{Q}', 'output'),
                        ('5', '2Q', 'output'), ('12', '2~{Q}', 'output'), ('8', 'GND', 'power_in')]),
                  title='74HC123', fp='Package_DIP:DIP-16_W7.62mm', mfr='Toshiba', mpn='TC74HC123AP(F)', h=4.5,
                  rs='539-9456', pack=5, ds='tc74hc123ap.pdf',
                  check='verified: standard 74HC123 pinout, 2-6 V, tw ~= 1.0 Cx Rx (1 uF x 1 M ~ 1.0 s), Rx <= 1 M, DIP-16 4.15+-0.3 high (Toshiba JP sheet p1, p5-p10)', desc='Dual retriggerable monostable, DIP-16 (TEC watchdog)'),
    'HC573': dict(sym=('74HC573', [('2', 'D1', 'input'), ('3', 'D2', 'input'), ('4', 'D3', 'input'), ('5', 'D4', 'input'),
                                   ('6', 'D5', 'input'), ('7', 'D6', 'input'), ('8', 'D7', 'input'), ('9', 'D8', 'input'),
                                   ('11', 'LE', 'input'), ('1', '~{OE}', 'input')],
                       [('20', 'VCC', 'power_in'), ('19', 'Q1', 'tri_state'), ('18', 'Q2', 'tri_state'), ('17', 'Q3', 'tri_state'),
                        ('16', 'Q4', 'tri_state'), ('15', 'Q5', 'tri_state'), ('14', 'Q6', 'tri_state'), ('13', 'Q7', 'tri_state'),
                        ('12', 'Q8', 'tri_state'), ('10', 'GND', 'power_in')]),
                  title='74HC573', fp='Package_DIP:DIP-20_W7.62mm', mfr='Texas Instruments', mpn='SN74HC573AN', h=5.1,
                  rs='217-5667', pack=1, ds='sn74hc573a.pdf', check='verified: pinout p3, N20 rows 7.62, 5.08 max (p3, p31)', desc='Octal transparent latch, DIP-20 (defrost-relay interlock)'),
    'G2RL2': dict(sym='Relay:G2RL-2', fp='Relay_THT:Relay_DPDT_Omron_G2RL-2', mfr='Omron', mpn='G2RL-2 DC12', h=15.7,
                  rs='365-0585', pack=1, ds='omron_g2rl.pdf',
                  check='verified: 29 x 12.7 x 15.7 max, 1.3 mm holes on the KiCad grid, 33.3 mA / 360 ohm, 8 A 30 VDC (p2, p6); RS title says "Aratas" but listing is Omron, check marking on arrival', desc='DPDT relay 8 A, 12 V coil'),
    'TSR12': dict(sym='Regulator_Switching:TSR2-24120N', fp='Converter_DCDC:Converter_DCDC_TRACO_TSR2-24xxN_TSR2-24xxxN_THT',
                  mfr='TRACO Power', mpn='TSR 2-24120N', h=10.7, rs='608-891', pack=1, ds='tracopower_tsr2n.pdf',
                  check='verified: Vin 15-36 V, pins 1 Vin 2 GND 3 Vout at 2.54, 14 x 7.6 x 10.2 + 0.5 standoff, pins 1.44 mm from one face, no traces under the body (p1-p4)',
                  desc='12 V 2 A SIP-3 buck (fans, relays, StepStick VMOT)'),
    'TSR5': dict(sym='Regulator_Switching:TSR_1-2450', fp='Converter_DCDC:Converter_DCDC_TRACO_TSR-1_THT', mfr='TRACO Power',
                 mpn='TSR 1-2450', h=10.6, rs='666-4379', pack=1, ds='tracopower_tsr1.pdf',
                 check='verified: Vin 6.5-36 V, +-2 %, 11.7 x 7.5 x 10.1 mm (+0.5 standoff), pins 1 Vin 2 GND 3 Vout; 22 uF/50 V input cap above 32 V (p1, p4)', desc='5 V 1 A SIP-3 buck (ESP32 DevKit)'),
    'FUSE_MINI': dict(sym='Device:Fuse', fp='Fuse:Fuseholder_Blade_Mini_Keystone_3568', mfr='Keystone', mpn='3568', h=16.3,
                      supplier='Farnell', farnell='2504685', pack=1, ds='keystone_3568.pdf',
                      check='verified: 16.0 x 6.73 x 7.37 mm, four 1.60 mm holes on 9.9 x 3.40 (Keystone cat. p42); h = holder + fused blade (8.8 body over the clips, estimate)',
                      desc='PCB clip holder for MINI blade fuse (not stocked by RS)'),
    'MSTBVA2': dict(sym='box', fp='Connector_Phoenix_MSTB:PhoenixContact_MSTBVA_2,5_2-G-5,08_1x02_P5.08mm_Vertical', mfr='Phoenix Contact',
                    mpn='MSTBVA 2,5/2-G-5,08 (1755736)', h=12.0, mate_h=22.0, family='Phoenix MSTB 5.08', pluggable=True,
                    rs='189-6199', pack=5, ds='phoenix_mstbva.pdf', check='verified (Phoenix family sheet via mirror): pitch 5.08, hole 1.4, h 12, mated 22; plug reverse-insertion unverified', desc='2-pole pluggable header; plug MSTB 2,5/2-ST-5,08 (1757019)'),
    'PTC': dict(sym='Device:Polyfuse', fp='d34:PTC_Radial_L13.0mm_W3.2mm_P5.08mm', mfr='Littelfuse', mpn='RXEF110', h=17.5,
                rs='517-6685', pack=10, ds='littelfuse_rxef.pdf',
                check='verified: 1.10 A hold / 2.20 A trip, 72 V; 12.8 wide x 3.0 thick x 17.5 high max, spacing 4.3-5.8 (kinked), lead 0.81 (p2, p4, p6)', desc='Resettable PTC 1.1 A hold, 72 V (aux 24 V branch)'),
    'MF2': dict(sym='box', fp='Connector_Molex:Molex_Mini-Fit_Jr_5566-02A_2x01_P4.20mm_Vertical', mfr='Molex', mpn='39-28-1023 (5566-02A)',
                h=12.8, mate_h=31.5, family='Molex Mini-Fit Jr', pluggable=True, rs='484-1883', pack=5, ds='molex_5566_header.pdf',
                check='verified: SD-5566-002 hole 1.40, 4.20 x 5.50, h 12.8, mated 23.5', desc='2-pin Mini-Fit Jr vertical header'),
    'MF4': dict(sym='box', fp='Connector_Molex:Molex_Mini-Fit_Jr_5566-04A_2x02_P4.20mm_Vertical', mfr='Molex', mpn='39-28-1043 (5566-04A)',
                h=12.8, mate_h=31.5, family='Molex Mini-Fit Jr', pluggable=True, rs='484-1899', pack=5, ds='molex_5566_header.pdf',
                check='verified: SD-5566-002 (as 2-pin)', desc='4-pin Mini-Fit Jr vertical header'),
    'MF6': dict(sym='box', fp='Connector_Molex:Molex_Mini-Fit_Jr_5566-06A_2x03_P4.20mm_Vertical', mfr='Molex', mpn='39-28-1063 (5566-06A)',
                h=12.8, mate_h=31.5, family='Molex Mini-Fit Jr', pluggable=True, rs='484-1906', pack=5, ds='molex_5566_header.pdf',
                check='verified: SD-5566-002 (as 2-pin)', desc='6-pin Mini-Fit Jr vertical header'),
    'VH2': dict(sym='box', fp='Connector_JST:JST_VH_B2P-VH_1x02_P3.96mm_Vertical', mfr='JST', mpn='B2P-VH(LF)(SN)', h=10.9, mate_h=26.5,
                family='JST VH', pluggable=True, rs='820-1147', pack=5, ds='jst_vh.pdf', check='verified: eVH pitch 3.96, hole 1.65-1.75, h 10.9, mated 16.5', desc='2-pin JST VH header'),
    'VH3': dict(sym='box', fp='Connector_JST:JST_VH_B3P-VH_1x03_P3.96mm_Vertical', mfr='JST', mpn='B3P-VH(LF)(SN)', h=10.9, mate_h=26.5,
                family='JST VH', pluggable=True, rs='820-1150', pack=5, ds='jst_vh.pdf', check='verified: eVH pitch 3.96, hole 1.65-1.75, h 10.9, mated 16.5', desc='3-pin JST VH header'),
    'VH4': dict(sym='box', fp='Connector_JST:JST_VH_B4P-VH_1x04_P3.96mm_Vertical', mfr='JST', mpn='B4P-VH(LF)(SN)', h=10.9, mate_h=26.5,
                family='JST VH', pluggable=True, rs='820-1157', pack=5, ds='jst_vh.pdf', check='verified: eVH pitch 3.96, hole 1.65-1.75, h 10.9, mated 16.5', desc='4-pin JST VH header'),
    'FAN4': dict(sym='box', fp='Connector:FanPinHeader_1x04_P2.54mm_Vertical', mfr='Molex', mpn='47053-1000', h=10.0, mate_h=25.2,
                 family='PC fan 4-pin (KK 254)', pluggable=True, rs='144-8185', pack=10, ds='molex_47053.pdf', check='verified: SD-47053-001 pitch 2.54, holes 1.02, peg hole 1.25 (footprint corrected), pins 10.0 high',
                 desc='4-pin PC fan header'),
    'DEVKIT': dict(sym='box', fp='d34:ESP32-DevKitC-32E_Socket', mfr='Samtec', mpn='SSW-119-01-T-S',
                   h=16.0, rs='207-9240', pack=1, ds='samtec_ssw.pdf; esp32_devkitc_v4_dimensions.pdf',
                   check='verified: SSW body 8.51 high, 0.64 sq pins 3.68-6.35 deep; DevKitC rows 25.40, 48.26 x 27.94 + 6.04 antenna (Espressif drawing)',
                   desc='1x19 2.54 mm socket strip, 8.51 mm (2 per ESP32-DevKitC-32E)'),
    'STEPSTICK': dict(sym='box', fp='d34:StepStick_Socket_2x8_W12.70mm', mfr='Samtec',
                      mpn='SSW-108-01-T-S', h=22.0, rs='180-0422', pack=10,
                      ds='samtec_ssw.pdf; btt_tmc2209_v13_sch.pdf',
                      check='verified: SSW 8.51 high; BTT V1.3 board 15.24 x 20.32, pinout from BTT schematic; heatsink height not published (estimate)', desc='1x8 2.54 mm socket strip, 8.51 mm (2 per StepStick)'),
}
# ---- sim-round additions (2026-10-26) ----
_RV = 'Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical'
K['RV'] = dict(K['R'], fp=_RV, h=6.5, desc='Resistor, metal film MF0204, 0.4 W, 1 %, axial, mounted vertical (2.54 mm)')
K['R470'] = dict(sym='Device:R', fp=R_FP, mfr='Vishay', mpn='MBA02040C4703FRP00', h=2.1, supplier='Farnell', farnell='4177865', pack=10,
                 ds='', check='Farnell listing: MBA 0204, 470 k, 1 %, 0.4 W (same 0204 body as MF0204; RS has no 470 k 0204 in small packs)',
                 desc='Resistor 470 k 1 % 0204 (74HC123 timing)')
K['R470V'] = dict(K['R470'], fp=_RV, h=6.5)
K['D_5817V'] = dict(K['D_5817'], fp='Diode_THT:D_DO-41_SOD81_P2.54mm_Vertical_AnodeUp', h=8.0,
                    desc='Schottky 20 V 1 A, DO-41, mounted vertical')
K['DZ15V'] = dict(K['DZ15S'], fp='Diode_THT:D_DO-35_SOD27_P2.54mm_Vertical_AnodeUp', h=6.5,
                  desc='Zener 15 V 0.5 W, DO-35, mounted vertical (K1 fast-release clamp)')
K['IRLZ44N'] = dict(sym='Transistor_FET:IRLZ44N', fp='Package_TO_SOT_THT:TO-220-3_Vertical', mfr='Infineon', mpn='IRLZ44NPBF', h=20.6,
                    supplier='Farnell', farnell='8651418', pack=1, ds='irlz44n.pdf',
                    check='Infineon datasheet saved: logic-level N-FET 55 V 47 A, VGS(th) 1.0-2.0 V, RDS(on) 35 mOhm at 4 V, TO-220 G-D-S '
                          '(PDF text not machine-readable: values read from the Infineon table, cross-checked with Farnell listing)',
                    desc='Logic-level N-MOSFET, TO-220 (fan low side; survives a PTC-limited short)')
K['PTC050'] = dict(sym='Device:Polyfuse', fp='d34:PTC_Radial_L8.0mm_W3.2mm_P5.08mm', mfr='Littelfuse', mpn='RXEF050', h=13.7,
                   rs='517-6635', pack=10, ds='littelfuse_rxef.pdf',
                   check='verified: 0.50 A hold / 1.00 A trip, 72 V, 7.9 wide x 3.0 thick x 13.7 high max, spacing 4.3-5.8, lead 0.51 (RXEF p2, p4, p6)',
                   desc='Resettable PTC 0.5 A hold (per fan channel)')
K['CP220u'] = dict(K['CP100u'], mpn='EEU-FR1V221', rs='766-0078', pack=10,
                  check='Panasonic FR (same 8 x 11.5 mm case/3.5 mm pitch as EEU-FR1H101 per FR p1/p6): 220 uF 35 V',
                  desc='220 uF 35 V low-ESR electrolytic, 8 x 11.5 mm (K2 hold-up)')
K['TL431'] = dict(sym='Reference_Voltage:TL431LP', fp='Package_TO_SOT_THT:TO-92_Inline_Wide', mfr='onsemi', mpn='TL431AILPG', h=8.0,
                 rs='774-3697', pack=10, ds='tl431.pdf',
                 check='verified: TO-92 pin 1 Reference, 2 Anode, 3 Cathode (onsemi TL431/D, case 29); Vref 2.495 V +-1 % (A grade)',
                 desc='Shunt reference 2.495 V, TO-92 (12 V undervoltage cut-off for K1)')
K['BC327'] = dict(sym='Transistor_BJT:BC327', fp='Package_TO_SOT_THT:TO-92_Inline_Wide', mfr='onsemi', mpn='BC32725BU', h=8.0,
                  rs='765-315', pack=100, ds='bc327.pdf',
                  check='onsemi BC327: PNP -45 V -800 mA; TO-92 pin 1 C, 2 B, 3 E (case 29 style 17, as KiCad BC327); bulk leads splayed to 2.54 mm',
                  desc='PNP 45 V 0.8 A, TO-92 (thermostat-loop supply switch)')
K['BAT42V'] = dict(sym='Device:D_Schottky', fp='Diode_THT:D_DO-35_SOD27_P2.54mm_Vertical_AnodeUp', mfr='STMicroelectronics', mpn='BAT42',
                   h=6.5, rs='544-4758', pack=5, ds='bat42.pdf',
                   check='BAT42 small-signal Schottky 30 V, DO-35 (Vishay BAT42 sheet saved; ST part from RS): VF ~0.2-0.3 V at uA-mA',
                   desc='Schottky clamp, DO-35 vertical (IO36 negative clamp)')
XH_RS = {2: '820-1554', 3: '820-1557', 4: '820-1551', 5: '820-1560', 11: '820-1535', 12: '820-1539'}
for n in XH_RS:
    K[f'XH{n}'] = dict(sym='box', fp=f'Connector_JST:JST_XH_B{n}B-XH-A_1x{n:02d}_P2.50mm_Vertical', mfr='JST', mpn=f'B{n}B-XH-A(LF)(SN)',
                       h=7.0, mate_h=19.8, family='JST XH', pluggable=True, rs=XH_RS[n], pack=10 if n > 10 else 5, ds='jst_xh.pdf',
                       check='verified: eXH pitch 2.5, length 2.5(n-1)+4.9, h 7.0, hole 0.9-1.0, mated 9.8', desc=f'{n}-pin JST XH shrouded header')
# Hole-size corrections to stock KiCad footprints, from the manufacturer drawings (pad number -> drill mm).
# Molex SD-47053-001: polarising peg 0.95 mm needs a 1.25 +-0.05 mm hole (KiCad stock: 1.1 mm).
FP_DRILL_FIX = {'FanPinHeader_1x04_P2.54mm_Vertical': {'': 1.25}}
# Yageo MF0204 values -> RS stock numbers (tape of 100), findchips snapshot 2026-10-26. Only values RS
# stocks in small packs are used (100 k and 30 k are not: 47 k and a 1 k/330 divider replace them).
YAGEO_RS = {'100': '199-7792', '330': '199-7821', '1k': '199-7806', '4.7k': '199-7830', '10k': '199-7794', '47k': '199-7828', '1M': '199-7811'}


def get(part):
    c = dict(K[part.kind])
    if c['sym'] == 'box':
        names = part.pinnames or [str(i + 1) for i in range(64)]
        c['sym'] = (f'{part.kind}_{part.board}_{part.ref}', [(str(i + 1), nm, 'passive') for i, nm in enumerate(names)], [])
        c['title'] = part.value
    if part.kind == 'DEVKIT':
        left = [(str(i + 1), nm, 'power_out' if nm == '3V3' else 'power_in' if nm in ('5V',) else 'passive')
                for i, nm in enumerate(DEVKIT_J2)]
        right = [(str(DEVKIT_PINS + i + 1), nm, 'passive') for i, nm in enumerate(DEVKIT_J3)]
        c['sym'] = ('ESP32_DevKitC_32E', left, right); c['title'] = 'ESP32-DevKitC-32E'
    if part.kind == 'STEPSTICK':
        left = [(str(i + 1), nm, 'passive') for i, nm in enumerate(SS_LEFT)]
        right = [(str(9 + i), nm, 'passive') for i, nm in enumerate(SS_RIGHT)]
        c['sym'] = ('StepStick', left, right); c['title'] = 'StepStick TMC2209/A4988'
    if '{v}' in c.get('mpn', ''):
        c['mpn'] = c['mpn'].format(v=yageo_code(part.value))
        c['rs'] = YAGEO_RS[part.value]
    return c


def yageo_code(v):
    """'330' -> '330R', '4.7k' -> '4K7', '10k' -> '10K', '1M' -> '1M'."""
    mult = v[-1].upper() if v[-1] in 'kM' else 'R'
    num = v[:-1] if mult != 'R' else v
    return num.replace('.', mult) if '.' in num else num + mult


def vishay_code(v):
    """Vishay 4-digit resistance code: '330' -> '3300', '4.7k' -> '4701', '10k' -> '1002', '1M' -> '1004'."""
    mult = {'k': 1e3, 'M': 1e6}.get(v[-1], 1.0)
    ohms = float(v[:-1] if v[-1] in 'kM' else v) * mult
    exp = 0
    while ohms >= 1000 - 1e-9:
        ohms /= 10; exp += 1
    while ohms < 100 - 1e-9:
        ohms *= 10; exp -= 1
    assert exp >= 0, v
    return f'{int(round(ohms)):03d}{exp}'


# Mating parts, plug-in modules and consumables that are not PCB footprints (quantities per set).
# key: id; qty per set; supplier/stock no/pack; ds: datasheet; check: verification state.
EXTRAS = {
    'd34-ctrl': [
        dict(id='devkit', desc='ESP32-DevKitC-32E module (plugs into U1 sockets); not stocked by RS/Farnell/CPC', qty=1, mfr='Espressif',
             mpn='ESP32-DevKitC-32E', supplier='Rapid Electronics', rs='09-1099', url='https://www.rapidonline.com/', price=10.32,
             ds='esp32_devkitc_v4_dimensions.pdf; esp32_devkitc_v4_sch.pdf',
             check='verified: Espressif drawing + V4 schematic (5V pin after BAT760, AMS1117-3.3); DigiKey UK 1965-ESP32-DEVKITC-32E-ND GBP 7.47 is the alternative'),
        dict(id='xhp3c', desc='JST XH housing 3-way (home sensor lead)', qty=1, mfr='JST', mpn='XHP-3', rs='820-1614', pack=5, ds='jst_xh.pdf', merge='xhp3'),
        dict(id='sxh', desc='JST XH crimp contact SXH-001T-P0.6, AWG 28-22, for the three XH leads longer than any stocked pre-crimped '
             'lead: W01 ctrl-pwr link 335 mm (22), W28 lid reed 325 mm (2), W29 panel 300 mm (5); hand crimper Engineer PA-09', qty=29,
             mfr='JST', mpn='SXH-001T-P0.6', rs='123-5947', pack=250, ds='jst_xh.pdf'),
        dict(id='xhp4', desc='JST XH housing 4-way (DPS5005 UART lead; lid reed + basin probe SENSE lead)', qty=2, mfr='JST', mpn='XHP-4', rs='820-1618', pack=5, ds='jst_xh.pdf'),
        dict(id='xhp5', desc='JST XH housing 5-way (panel LED/button lead)', qty=1, mfr='JST', mpn='XHP-5', rs='820-1627', pack=5, ds='jst_xh.pdf'),
        dict(id='xhp11', desc='JST XH housing 11-way (ctrl-pwr link, both ends)', qty=2, mfr='JST', mpn='XHP-11', rs='820-1523', pack=10, ds='jst_xh.pdf'),
        dict(id='xhp12', desc='JST XH housing 12-way (ctrl-tec link, both ends)', qty=2, mfr='JST', mpn='XHP-12', rs='820-1532', pack=10, ds='jst_xh.pdf'),
        dict(id='xhlead', desc='JST XH pre-crimped lead, 300 mm 26 AWG, SXH contact both ends. W02 ctrl-tec link (12, both ends) and the '
             'single-ended leads W12, W30, W31, W33, W34 (14: each lead cut near ONE end, ~290 mm usable)', qty=26, mfr='JST', mpn='01SXHSXH-26L300', rs='820-1541', pack=10,
             ds='jst_xh.pdf', check='retailer data (RS/Farnell listing); contact = SXH-001T-P0.6 per eXH'),
    ],
    'd34-pwr': [
        dict(id='stepstick', desc='BIGTREETECH TMC2209 V1.3 StepStick (plugs into U4 sockets)', qty=1, mfr='BIGTREETECH', mpn='TMC2209 V1.3',
             supplier='3DJake UK', url='https://www.3djake.uk/bigtreetech/stepper-motor-driver', price=6.30, ds='btt_tmc2209_v13_sch.pdf', check='PENDING'),
        dict(id='fuse75', desc='MINI blade fuse 7.5 A 32 V (F1, DPS feed); RS sells it only in 50s', qty=1, mfr='Littelfuse', mpn='029707.5WXNV',
             supplier='Farnell', rs='9943854', pack=5, ds='littelfuse_297.pdf', check='verified: 7.5 A, 32 VDC (Littelfuse 297 p1)'),
        dict(id='mf2r', desc='Mini-Fit Jr receptacle housing 2-way (brick lead)', qty=1, mfr='Molex', mpn='39-01-2020', rs='484-1748', pack=5, ds='molex_5557_housing.pdf'),
        dict(id='mstbp', desc='Phoenix MSTB 2,5/2-ST-5,08 screw plug (DPS5005 input lead; no crimp)', qty=1, mfr='Phoenix Contact', mpn='1757019',
             rs='189-6010', pack=5, ds='phoenix_mstb_st.pdf'),
        dict(id='vhr3', desc='JST VH housing 3-way (12 V lead to tec card, both ends)', qty=2, mfr='JST', mpn='VHR-3N', rs='820-1175', pack=5, ds='jst_vh.pdf'),
        dict(id='vhr4', desc='JST VH housing 4-way (motor lead)', qty=1, mfr='JST', mpn='VHR-4N', rs='820-1179', pack=5, ds='jst_vh.pdf'),
        dict(id='xhp3p', desc='JST XH housing 3-way (1-Wire bus A and bus B leads)', qty=2, mfr='JST', mpn='XHP-3', rs='820-1614', pack=5, ds='jst_xh.pdf', merge='xhp3'),
    ],
    'd34-tec': [
        dict(id='snub_r', desc='Reverse-brick ring snubber, resistor: 2.2 ohm MRS25, in series with a 1 uF 50 V MLCC (Murata RDER71H105K2P1H03B, '
             'from the C1u pack) across the Kycon inlet socket (+24 V pins 1/4 to 0 V pins 2/3), heat-shrunk', qty=1, mfr='Vishay',
             mpn='MRS25000C2208FCT00', rs='683-3487', pack=25, ds='mrs25.pdf', check='Vishay MRS25 2R2 0.6 W (off-board: no bend-pitch limit)'),
        dict(id='mf4r', desc='Mini-Fit Jr receptacle housing 4-way (TEC lead)', qty=1, mfr='Molex', mpn='39-01-2040', rs='484-1754', pack=5, ds='molex_5557_housing.pdf'),
        dict(id='mf6r', desc='Mini-Fit Jr receptacle housing 6-way (DPS5005 output lead)', qty=1, mfr='Molex', mpn='39-01-2060', rs='484-1760', pack=5, ds='molex_5557_housing.pdf'),
        dict(id='mflead', desc='Molex Mini-Fit Jr pre-crimped lead, 225 mm 18 AWG, 39-00-0039-type socket one end, other end bare '
             '(W32 brick inlet 2 + W06 TEC feed 4); not stocked by RS', qty=6, mfr='Molex', mpn='215341-1113', supplier='Farnell', rs='3559249', pack=1,
             ds='molex_39000039.pdf', check='retailer data (Farnell listing)'),
        dict(id='mflead450', desc='Molex Mini-Fit Jr pre-crimped lead, 450 mm 18 AWG, one end bare (W05 DPS output, 290 mm needed: '
             'pins 1 and 4). Farnell showed 0 stock on 2026-10-26: if still out, use a 225 mm lead + soldered extension (heat-shrink RS 398-212)',
             qty=2, mfr='Molex', mpn='215341-1115', supplier='Farnell', rs='3559251', pack=1, ds='molex_39000039.pdf', check='retailer data (Farnell listing)'),
        dict(id='vhr2', desc='JST VH housing 2-way (thermostat loop lead)', qty=1, mfr='JST', mpn='VHR-2N', rs='820-1172', pack=5, ds='jst_vh.pdf'),
        dict(id='vhlead', desc='JST VH pre-crimped lead, 300 mm 20 AWG, SVH contact both ends (3 for the 12 V link W03; motor W13 (4) and '
             'thermostat W23, W27 (2) cut near one end)', qty=9, mfr='JST', mpn='01SVHSVH-20L-300', rs='820-1135', pack=5, ds='jst_vh.pdf',
             check='retailer data (RS listing)'),
        dict(id='thermo', desc='Bimetal thermostat NC, opens 60 C / closes 45 C, 16 A, 250 V AC/DC (one per hot sink, wired in series)', qty=4,
             mfr='RS PRO', mpn='T24A060ASF2-15', rs='222-8227', pack=1, ds='',
             check='RS product page only (no datasheet published): NC, opens 60 C / closes 45 C, 16 A 250 V AC/DC, 6.3 mm tabs assumed; '
                   'switches only 12 V / 35 mA here. Size and tab width UNVERIFIED until parts arrive'),
    ],
}
# ------------------------------------------------------------------ 3D envelopes (parts3d.py)
# Per kind: h = body height above the board (component side), h_src; 'cyl' = (radius, height, src) for radial
# cans; 'local' = list of (group, x0, y0, x1, y1, z0, z1, what, src) boxes in footprint-local coordinates
# (unrotated, as in the .kicad_mod); 'plug' = ('fab', top_z, src) or (x0, y0, x1, y1, top_z, src) mated plug;
# 'bend' = cable bend allowance above the plug; 'protrusion' = lead length below the solder side after trimming.
GEOM = {}
# Mated plug tops above the board (datasheets/MANIFEST.json): XH 9.8 (eXH p1), VH 16.5 (eVH p1),
# Mini-Fit Jr 23.5 (SD-5566-002 p1), fan 47054 plug on 47053 ~15.2 (12.7 plug + 2.5 base, estimate),
# MSTB 2,5-ST on MSTBVA 22 (Phoenix p5). Plug XY = header body outline + 0.5 mm.
for _k, _top, _bend, _src in [('XH', 9.8, 10.0, 'datasheet'), ('VH', 16.5, 10.0, 'datasheet'), ('MF', 23.5, 8.0, 'datasheet'),
                              ('FAN4', 15.2, 10.0, 'estimate')]:
    for _n in ([''] if _k == 'FAN4' else [2, 3, 4, 5, 6, 11, 12]):
        GEOM[f'{_k}{_n}'] = dict(plug=('fab', _top, _src), bend=_bend, service=15.0, h_src='datasheet', plug_margin=0.5)
GEOM['CP22u'] = dict(cyl=(2.75, 12.5, 'datasheet'))     # 5 x 11 mm can, D + 0.5 / L + 1.5 max (Rubycon YXF, Panasonic FR)
GEOM['CP100u'] = dict(cyl=(4.25, 13.0, 'datasheet'))    # 8 x 11.5 mm can (Panasonic FR p6)
GEOM['LED_G'] = dict(cyl=(1.95, 6.4, 'datasheet'))      # HLMP-1503: 3.17 dia lens, flange, 6.35 high max
for _k in ('R', 'C100n', 'C1u', 'D_5817', 'D_5817S', 'D_4148', 'DZ15S', 'TVS30', 'IRF4905', '2N3904', 'ULN2003', 'HC123', 'HC573',
           'G2RL2', 'TSR12', 'TSR5', 'PTC'):
    GEOM.setdefault(_k, {})['h_src'] = 'datasheet'
GEOM['FUSE_MINI'] = dict(h_src='estimate')
GEOM['MSTBVA2'] = dict(plug=('fab', 22.0, 'datasheet'), bend=0.0, h_src='datasheet', plug_margin=0.5, side_exit=(12.0, 20.0, 15.0),
                       service=25.0, note='MSTB plug: screws on top (+z, screwdriver access), wires enter horizontally (parallel to '
                       'the card) on one long face; which face depends on plug orientation (not verified) - both sides reserved.')
_dk = DEVKIT_BODY[1]; _dko = (_dk - DEVKIT_ROW_SPACING) / 2; _dkL = (DEVKIT_PINS - 1) * 2.54
GEOM['DEVKIT'] = dict(
    local=[('bodies', -1.27, -1.27, 1.27, _dkL + 1.27, 0.0, 8.5, '1x19 female socket strip (row J2)', 'estimate'),
           ('bodies', DEVKIT_ROW_SPACING - 1.27, -1.27, DEVKIT_ROW_SPACING + 1.27, _dkL + 1.27, 0.0, 8.5, '1x19 female socket strip (row J3)', 'estimate'),
           ('mated', -_dko, -DEVKIT_PIN1_TO_ANTENNA_END, DEVKIT_ROW_SPACING + _dko, _dkL + DEVKIT_PIN19_TO_USB_END, 8.5, 11.0, 'DevKit header pin spacers', 'estimate'),
           ('mated', -_dko, -DEVKIT_PIN1_TO_ANTENNA_END, DEVKIT_ROW_SPACING + _dko, _dkL + DEVKIT_PIN19_TO_USB_END, 11.0, 12.6, 'DevKit PCB', 'estimate'),
           ('mated', -_dko, -DEVKIT_PIN1_TO_ANTENNA_END, DEVKIT_ROW_SPACING + _dko, _dkL + DEVKIT_PIN19_TO_USB_END, 12.6, 16.0, 'DevKit top-side parts (WROOM-32E 3.1 mm, USB, buttons)', 'estimate'),
           ('service', DEVKIT_ROW_SPACING / 2 - 6.0, _dkL + DEVKIT_PIN19_TO_USB_END, DEVKIT_ROW_SPACING / 2 + 6.0, _dkL + DEVKIT_PIN19_TO_USB_END + 25.0, 10.0, 20.0, 'micro-USB plug for programming (module pulled or bench only)', 'estimate')],
    exit=(DEVKIT_ROW_SPACING / 2, _dkL + DEVKIT_PIN19_TO_USB_END, 0.0, 1.0, 13.5, 'micro-USB socket faces along the module axis (USB end); programming only'),
    protrusion=1.6, note='Module plugs into two 1x19 sockets; heights to be confirmed from socket and Espressif drawings.')
GEOM['STEPSTICK'] = dict(
    local=[('bodies', -1.27, -1.27, 1.27, 19.05, 0.0, 8.5, '1x8 female socket strip (left)', 'estimate'),
           ('bodies', STEPSTICK_ROW_SPACING - 1.27, -1.27, STEPSTICK_ROW_SPACING + 1.27, 19.05, 0.0, 8.5, '1x8 female socket strip (right)', 'estimate'),
           ('mated', -1.27, -1.27, 13.97, 19.05, 8.5, 12.6, 'StepStick pins, spacer and PCB (driver IC underneath)', 'estimate'),
           ('mated', -1.27, -1.27, 13.97, 19.05, 12.6, 22.0, 'heatsink and trimmer', 'estimate')],
    protrusion=1.6, note='Plug-in StepStick; heights pending module drawing.')


def geometry(kind):
    g = dict(GEOM.get(kind, {}))
    if 'h' not in g and 'local' not in g and 'cyl' not in g:
        g['h'] = K[kind].get('h', 0.0)
    if 'plug' not in g and K[kind].get('pluggable') and K[kind].get('mate_h'):
        g['plug'] = ('fab', K[kind]['mate_h'] - 10.0, 'estimate'); g.setdefault('bend', 10.0)
    return g
