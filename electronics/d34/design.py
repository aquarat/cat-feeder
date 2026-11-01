"""D34 controller design: circuit connectivity and placement for three cards.

Each card is 81 x 47 mm and stands vertically in a printed floor slot in one
diagonal bay (plane tangential, components facing the axis). Coordinates are
millimetres from the card's top-left corner seen from the component side,
X right (along the bay), Y down: y = 0 is the top edge (printed clip), y = 47
sits in the floor slot. Both long edges keep a 3 mm band free of pads and
courtyards. Connectors sit in the top half or at the short ends.

  ctrl (45 deg)   ESP32-DevKitC-32E, lid/leak/home/UI/DPS-UART, TEC watchdog + defrost latch.
                  Only 5 V and 3.3 V reach this card.
  pwr  (225 deg)  24 V brick entry (grommet side), reverse FET, TVS, DPS fuse, aux PTC,
                  12 V and 5 V SIP bucks, DPS5005 feed, StepStick + motor, 1-Wire headers.
  tec  (315 deg)  K1 cut-off + K2 reversal relays, thermostat loop, DPS output in, TEC out,
                  ULN2003 coil/fan drivers, three fan headers.

Links (all keyed, unique pin counts, identical pin order both ends):
  ctrl J1 XH-11  <->  pwr J9  : 5 V, 3.3 V, GND, stepper, 1-Wire
  ctrl J2 XH-12  <->  tec J9  : 3.3 V, GND, relay drive, thermostat sense, fans
  pwr  J3 VH-3   ->   tec J1  : +12 V, GND, +12 V
"""
import catalog as C

W, H = 81.0, 47.0


class Part:
    def __init__(self, board, ref, kind, value, nets, x, y, rot=0, group='', pinnames=None, ref_at=None, note=''):
        self.board, self.ref, self.kind, self.value = board, ref, kind, value
        self.nets = {str(k): v for k, v in nets.items() if v}
        self.x, self.y, self.rot, self.group = x, y, rot, group
        self.pinnames, self.ref_at, self.note = pinnames, ref_at, note


class Board:
    band = 3.0
    default_track = 0.3
    origin = (50.0, 50.0)

    def __init__(self, name, title, title_short, width=W, height=H, bay=''):
        self.name, self.title, self.title_short = name, title, title_short
        self.width, self.height, self.bay = width, height, bay
        self.rev = 'D34-2'
        self.parts, self.silk, self.keepouts, self.preroutes = [], [], [], []
        self.connectors = {}
        self.netclasses = {}
        self.notes = []
        self.extra_pwr_flags = []
        self.solid_pads = set()
        self.comment1 = self.comment2 = ''
        self.version_at = (width / 2, height - 1.5)
        self.group = ''

    def add(self, ref, kind, value, nets, x, y, rot=0, **kw):
        kw.setdefault('group', self.group)
        p = Part(self.name, ref, kind, value, nets, x, y, rot, **kw)
        self.parts.append(p); return p

    def conn(self, ref, kind, value, roles, x, y, rot=0, label=None, **kw):
        """Connector or jumper. roles: (net, voltage-role) per pin in pin order.
        Roles: GND 3V3 5V 12V 24V LOGIC ANALOG MOTOR TEC FANGND NC."""
        nets = {i + 1: n for i, (n, r) in enumerate(roles) if n}
        names = [(n or 'NC') for n, r in roles]
        self.add(ref, kind, value, nets, x, y, rot, pinnames=names, **kw)
        self.connectors[ref] = dict(kind=kind, label=label or value, roles=[r for n, r in roles], nets=[n for n, r in roles])

    def R(self, ref, value, a, b, x, y, rot=0, **kw):
        return self.add(ref, 'R', value, {1: a, 2: b}, x, y, rot, **kw)

    def text(self, s, x, y, size=1.0, rot=0, back=False):
        self.silk.append((s, x, y, dict(size=size, rot=rot, back=back)))

    def track(self, net, layers, width, pts):
        for lay in layers:
            self.preroutes.append((net, lay, width, pts))


LINK_PWR = [('+5V', '5V'), ('+5V', '5V'), ('GND', 'GND'), ('GND', 'GND'), ('+3V3', '3V3'), ('STEP', 'LOGIC'),
            ('DIR', 'LOGIC'), ('MOT_EN', 'LOGIC'), ('TMC_UART', 'LOGIC'), ('OWA', 'LOGIC'), ('OWB', 'LOGIC')]
LINK_TEC = [('GND', 'GND'), ('GND', 'GND'), ('K1_ON', 'LOGIC'), ('K2_ON', 'LOGIC'), ('THERMO_OK', 'LOGIC'), ('GND', 'GND'),
            ('FAN1_PWM', 'LOGIC'), ('FAN2_PWM', 'LOGIC'), ('FAN3_PWM', 'LOGIC'), ('TACH1', 'LOGIC'), ('TACH2', 'LOGIC'), ('GND', 'GND')]
LINK_12V = [('+12V', '12V'), ('GND', 'GND'), ('+12V', '12V')]

# ESP32 GPIO allocation (ESP32-DevKitC-32E pin names). Strapping pins carry only
# signals whose boot level is safe: IO0 button (pull-up on DevKit), IO2 LED
# (pull-down via LED), IO12 fan PWM with 10k pull-down (3.3 V flash), IO5 fan PWM,
# IO15 DIR (no external pull). TEC_EN/WDT_KICK use IO32/IO33, quiet at reset.
GPIO = {'3V3': '+3V3', 'EN': None, 'IO36': 'THERMO_OK_IN', 'IO39': 'LEAK_IN', 'IO34': 'TACH1_IN', 'IO35': 'TACH2_IN',
        'IO32': 'TEC_EN', 'IO33': 'WDT_KICK', 'IO25': 'DEFROST_REQ', 'IO26': 'DEFROST_FB', 'IO27': 'LID_IN',
        'IO14': 'FAN2_PWM', 'IO12': 'FAN1_PWM', 'GND': 'GND', 'IO13': 'OWB', 'SD2': None, 'SD3': None,
        'CMD': None, '5V': '+5V_DK',
        'IO23': 'HOME_IN', 'IO22': 'DPS_TX_G', 'TXD0': None, 'RXD0': None, 'IO21': 'DPS_RX_G',
        'IO19': 'MOT_EN', 'IO18': 'STEP', 'IO5': 'FAN3_PWM', 'IO17': 'TMC_TX_G', 'IO16': 'TMC_UART',
        'IO4': 'OWA', 'IO0': 'BTN_IN', 'IO2': 'LED_G', 'IO15': 'DIR', 'SD1': None, 'SD0': None, 'CLK': None}


# ======================================================================
# Controller card, 45 deg bay
# ======================================================================
def ctrl():
    B = Board('d34-ctrl', 'Cat feeder D34 controller card (logic, 45 deg bay)', 'D34-CTRL', bay='45 deg')
    B.comment1 = 'ESP32-DevKitC-32E in sockets; only 5 V and 3.3 V on this card; links to pwr (XH-11) and tec (XH-12).'
    B.comment2 = 'Hardware TEC watchdog (74HC123) and defrost-relay latch (74HC573) hold relays off unless firmware arms them.'
    B.netclasses = {'Power': dict(width=0.6, clearance=0.25, nets=['GND', '+3V3', '+5V', '+5V_DK'])}
    DX, DY = 8.0, 42.0   # DevKit J2 pin 1 (antenna end at x = 0.7); J3 row 25.40 mm above
    B.group = 'ESP32-DevKitC-32E (socketed) and supply'
    nets = {}
    for i, nm in enumerate(C.DEVKIT_J2): nets[i + 1] = GPIO[nm]
    for i, nm in enumerate(C.DEVKIT_J3): nets[C.DEVKIT_PINS + i + 1] = GPIO[nm]
    B.add('U1', 'DEVKIT', 'ESP32-DevKitC-32E', nets, DX, DY, 90, ref_at=(52.5, 1.6, 0))
    B.add('D1', 'D_5817', '1N5817', {1: '+5V_DK', 2: '+5V'}, 57.5, 16.6, 270, ref_at=(57.5, 21.68, 90),
          note='stops USB VBUS (via DevKit BAT760) back-feeding the 5 V buck; 1N5817 for the lowest VF (DevKit AMS1117 headroom)')
    B.add('C1', 'CP22u', '22u 50V', {1: '+5V_DK', 2: 'GND'}, 61.2, 19.5, 0, ref_at='hide')
    B.add('C2', 'CP22u', '22u 50V', {1: '+3V3', 2: 'GND'}, 61.2, 25.3, 0, ref_at='hide')
    B.add('D3', 'LED_G', 'STATUS', {1: 'GND', 2: 'LED_EXT'}, 60.0, 31.4, 0, ref_at=(65.3, 31.4, 0),
          note='on-board status LED in parallel with the panel LED, both via R33')
    # ---------------------------------------------------------- links (right end)
    B.group = 'Keyed links: XH-11 to pwr card, XH-12 to tec card (5 V, 3.3 V, GND and logic only)'
    B.conn('J1', 'XH11', 'LINK to D34-PWR', LINK_PWR, 70.5, 6.0, 270, label='LINK-PWR', ref_at=(70.0, 1.6, 0))
    B.conn('J2', 'XH12', 'LINK to D34-TEC', LINK_TEC, 77.5, 6.0, 270, label='LINK-TEC', ref_at=(77.0, 1.6, 0))
    B.conn('J11', 'XH4', 'DPS5005 UART (3.3 V TTL; DPS order GND TX RX 3V3)',
           [('GND', 'GND'), ('DPS_TXD', 'LOGIC'), ('DPS_RXD', 'LOGIC'), (None, 'NC')], 63.5, 6.0, 270, label='DPS', ref_at=(63.0, 1.6, 0))
    # ---------------------------------------------------------- safety logic (under the DevKit)
    B.group = 'TEC watchdog (74HC123) and defrost interlock latch (74HC573)'
    # Both DIPs are turned 270 deg so VCC (pin 16 / pin 20) sits at the bottom-right corner, next to its
    # own 100 nF (C6 in the resistor grid, C7 right of U3); GND pins are on the top row into the pours.
    B.add('U2', 'HC123', '74HC123', {1: 'GND', 2: 'WDT_KICK', 3: 'TEC_EN', 4: 'LATCH_RAW', 13: 'K1_ON',
                                     14: 'WD_C', 15: 'WD_RC', 16: '+3V3', 8: 'GND',
                                     9: 'GND', 10: 'LATCH_RAW', 11: 'LATCH_RAW', 6: 'LD_C', 7: 'LD_RC', 12: 'LATCH_DLY'},
          20.28, 19.88, 270, ref_at=(11.4, 23.7, 0),
          note='half 1: watchdog (1B rising edge retriggers; 1CLR = TEC_EN; 1Q drives K1). Half 2: latch-open delay - '
               'triggered when 1Q-bar rises (K1 commanded off), 2Q-bar low for ~0.47 s, then high = LE (fast CMOS edge)')
    B.add('U3', 'HC573', '74HC573', {1: 'GND', 2: 'DEFROST_REQ', 3: 'GND', 4: 'GND', 5: 'GND', 6: 'GND', 7: 'GND', 8: 'GND', 9: 'GND',
                                     10: 'GND', 11: 'LATCH_EN', 19: 'K2_ON', 20: '+3V3'},
          46.86, 19.88, 270, ref_at=(35.4, 23.7, 0), note='transparent only while K1 is commanded off (plus RC delay)')
    ux = [1.2, 11.1, 21.0, 30.9, 40.8]; uy = [31.0, 34.4, 37.8]

    def ur(ref, v, a, b, c, r, **kw):
        return B.R(ref, v, a, b, ux[c], uy[r], 0, ref_at=(ux[c] + 3.81, uy[r], 0), **kw)
    # Sim round 2026-10-26: 1 M is at the Toshiba 74HC123 noise limit; 470 k x 1 uF gives ~0.47 s nominal,
    # 0.32-0.65 s over K (0.69-1.36 at 3.3 V per the sim's Monte Carlo spread), C and R tolerance.
    B.add('R1', 'R470', '470k', {1: 'WD_RC', 2: '+3V3'}, ux[0], uy[0], 0, ref_at=(ux[0] + 3.81, uy[0], 0),
          note='watchdog timeout 0.32-0.65 s with 1 uF; firmware kicks at >= 10 Hz')
    ur('R2', '10k', 'TEC_EN', 'GND', 1, 0, note='TEC disarmed while the ESP32 boots or is absent')
    B.R('R3', '47k', 'WDT_KICK', 'GND', 53.5, 19.6, 270, ref_at='hide')
    B.add('C6', 'C100n', '100n', {1: '+3V3', 2: 'GND'}, ux[2], uy[0], 0, ref_at=(ux[2] + 6.0, uy[0], 0), note='U2 (74HC123) VCC decoupling')
    B.add('C7', 'C100n', '100n', {1: '+3V3', 2: 'GND'}, 50.3, 27.2, 90, ref_at='hide', note='U3 (74HC573) VCC decoupling')
    ur('R4', '10k', 'DEFROST_REQ', 'GND', 3, 0)
    # LE drive (sim round): LE = 2Q-bar through R5 1 k, clamped low through D2 (Schottky) while 1Q-bar is low (K1
    # commanded on). Both edges are CMOS-fast; the old 47 k / 1 uF ramp (41 ms through the LE threshold) and the
    # 61 mA C5 dump into the 74HC123 output are gone. Re-open delay = 2Q-bar width 0.32-0.65 s >> K1 release (<= 16.4 ms).
    ur('R5', '1k', 'LATCH_DLY', 'LATCH_EN', 4, 0, note='LE series resistor: D2 clamp current 3 mA')
    B.add('D2', 'D_5817V', '1N5817', {1: 'LATCH_RAW', 2: 'LATCH_EN'}, 3.0, uy[1], 0, ref_at='hide',
          note='holds LE low (<= 0.4 V) whenever 1Q-bar is low, i.e. while K1 is commanded on')
    B.add('R26', 'R470V', '470k', {1: 'LD_RC', 2: '+3V3'}, 57.3, 30.2, 270, ref_at='hide', note='latch-delay timing (74HC123 half 2)')
    ur('R6', '1k', 'TMC_TX_G', 'TMC_UART', 1, 1, note='TMC2209 single-wire UART: TX via 1k, RX (IO16) direct')
    ur('R7', '10k', 'FAN1_PWM', 'GND', 2, 1, note='GPIO12 strap must read low at boot (3.3 V flash)')
    ur('R8', '1k', 'K2_ON', 'DEFROST_FB', 3, 1, note='latched K2 state read back on IO26')
    ur('R9', '4.7k', '+3V3', 'OWA', 4, 1, note='1-Wire bus A pull-up (bus B pull-up is on the pwr card)')
    ur('R10', '1k', 'TACH1', 'TACH1_IN', 0, 2)
    ur('R11', '1k', 'TACH2', 'TACH2_IN', 1, 2)
    ur('R12', '47k', 'THERMO_OK', 'THERMO_OK_IN', 2, 2, note='sim round 3: 47 k + D9 BAT42 keep IO36 above -0.3 V (~-0.22 V) when a thermostat opens; IO36 leakage <= 50 nA -> 2.4 mV')
    B.add('D9', 'BAT42V', 'BAT42', {1: 'THERMO_OK_IN', 2: 'GND'}, 51.4, uy[1], 0, ref_at='hide', note='IO36 negative clamp (K1 flyback drags THERMO_RET to ~-15 V)')
    ur('R13', '330', 'LED_G', 'LED_EXT', 3, 2)
    ur('R14', '1k', 'BTN', 'BTN_IN', 4, 2, note='DevKit BOOT button is also IO0; external button in parallel')
    for ref, v, nets_, r in [('C4', '1u', {1: 'WD_C', 2: 'WD_RC'}, 0), ('C5', '1u', {1: 'LD_C', 2: 'LD_RC'}, 2)]:
        B.add(ref, 'C1u' if v == '1u' else 'C100n', v, nets_, 51.4, uy[r], 0, ref_at='hide')
    # ---------------------------------------------------------- sensors / UI / DPS
    B.group = 'Lid, leak, home, UI and DPS5005 UART (3.3 V, series-protected)'
    tx = [1.2, 11.1, 21.0, 30.9, 40.8, 50.7]
    for ref, v, a, b, i in [('R15', '10k', '+3V3', 'HOME', 0), ('R16', '1k', 'HOME', 'HOME_IN', 1), ('R17', '10k', '+3V3', 'LID', 2),
                            ('R18', '1k', 'LID', 'LID_IN', 3), ('R19', '47k', '+3V3', 'LEAK', 4), ('R20', '10k', 'LEAK', 'LEAK_IN', 5)]:
        B.R(ref, v, a, b, tx[i], 12.6, 0, ref_at=(tx[i] + 3.81, 12.6, 0))
    for ref, v, a, b, i in [('R21', '1k', 'DPS_TX_G', 'DPS_RXD', 0), ('R22', '1k', 'DPS_TXD', 'DPS_RX_G', 1), ('R23', '10k', '+3V3', 'DPS_TXD', 2),
                            ('R24', '10k', '+3V3', 'TACH1', 3), ('R25', '10k', '+3V3', 'TACH2', 4)]:
        x = 56.8 + 3.3 * i
        B.R(ref, v, a, b, x, 35.2, 270, ref_at=(x, 39.01, 90))
    s3 = [('GND', 'GND'), ('HOME', 'LOGIC'), ('+3V3', '3V3')]
    # Harness-access pass (2026-10-26): three plugs instead of four, spread to ~7 mm gaps. The lid reed and the
    # basin-full probe arrive on two cables that terminate in the same XHP-4 housing (J4 = GND, LID, LEAK, GND).
    B.conn('J3', 'XH3', 'HOME sensor (DRV5023 hall, 3.3 V, open drain)', s3, 3.5, 6.3, 0, label='HOME', ref_at=(1.5, 1.6, 0))
    B.conn('J4', 'XH4', 'LID reed + basin-full probe', [('GND', 'GND'), ('LID', 'LOGIC'), ('LEAK', 'ANALOG'), ('GND', 'GND')],
           20.9, 6.3, 0, label='SENSE', ref_at=(18.9, 1.6, 0))
    B.conn('J6', 'XH5', 'UI: panel LED + button', [('GND', 'GND'), ('+3V3', '3V3'), ('LED_EXT', 'LOGIC'), ('BTN', 'LOGIC'), ('GND', 'GND')],
           40.8, 6.3, 0, label='UI', ref_at=(38.8, 1.6, 0))
    for s, x in [('HOME', 6.0), ('LID LEAK', 26.0), ('UI', 45.5), ('DPS', 59.6), ('PWR', 66.6), ('TEC', 73.6)]:
        B.text(s, x, 1.6)
    return B


# ======================================================================
# Power card, 225 deg bay (brick grommet side)
# ======================================================================
def pwr():
    B = Board('d34-pwr', 'Cat feeder D34 power card (24 V entry, bucks, DPS feed, stepper; 225 deg bay)', 'D34-PWR', bay='225 deg')
    B.comment1 = '24 V brick: reverse P-FET, TVS, bulk, 7.5 A DPS fuse, 1.1 A PTC aux; 12 V/5 V SIP bucks; StepStick + motor; 1-Wire headers.'
    B.comment2 = '+12 V goes to the tec card on a JST VH-3 lead; 5 V/3.3 V and logic go to the ctrl card on XH-11.'
    HC = ['VIN_RAW', '+24V', '+24V_DPS']
    B.netclasses = {'TEC': dict(width=2.5, clearance=0.5, nets=HC),
                    'Power': dict(width=0.8, clearance=0.3, nets=['GND', 'VAUX', '+5V', '+3V3']),
                    # Sim round: TSR 2 current limit up to 7.2 A into a +12 V short heated 0.8 mm copper by 153 K.
                    'P12': dict(width=2.0, clearance=0.3, nets=['+12V']),
                    'Motor': dict(width=0.8, clearance=0.3, nets=['M1A', 'M1B', 'M2A', 'M2B'])}
    B.solid_pads = set(HC)
    B.group = '24 V entry: reverse-polarity P-FET, TVS, bulk, fuses'
    # J1 is turned 180 deg (pin 1 = +24 V at the bottom) so VIN_RAW runs 8 mm to the FET drain on both
    # layers without crossing the brick return; GND leaves upwards and runs above the VH/MSTB row.
    B.conn('J1', 'MF2', '24V IN (brick)', [('VIN_RAW', '24V'), ('GND', 'GND')], 4.0, 19.5, 180, label='24V IN', ref_at='hide')
    B.add('Q1', 'IRF4905', 'IRF4905PBF', {1: 'Q1_G', 2: 'VIN_RAW', 3: '+24V'}, 5.0, 27.0, 0, ref_at=(14.5, 24.0, 0),
          note='conducts only with correct input polarity; gate clamped to -15 V')
    B.add('DZ1', 'DZ15S', 'BZX79-C15', {1: '+24V', 2: 'Q1_G'}, 10.62, 30.0, 180, ref_at='hide')
    # Sim round: a reversed brick couples the -24 V drain step through Cgd and pulls VGS to -5.4 V (31 A for 22 us).
    # 100 nF gate-source holds the gate: simulated 0.81 A peak, rails above -0.84 V.
    B.add('C9', 'C100n', '100n', {1: '+24V', 2: 'Q1_G'}, 3.0, 37.0, 0, ref_at='hide', note='Q1 gate-source hold (reverse plug-in)')
    B.R('R1', '10k', 'Q1_G', 'GND', 3.0, 33.5, 0, ref_at=(6.81, 33.5, 0), note='gate pull-down; 0.9 mA keeps the 15 V zener in its knee')
    B.add('C1', 'CP100u', '100u 50V', {1: '+24V', 2: 'GND'}, 15.5, 31.0, 0)
    B.add('D1', 'TVS30', 'P6KE30A', {1: '+24V', 2: 'GND'}, 21.5, 41.8, 180, ref_at=(15.15, 41.8, 0))
    B.add('F1', 'FUSE_MINI', '7.5A ATM', {1: '+24V', 2: '+24V_DPS'}, 25.0, 26.0, 0, ref_at=(29.96, 26.9, 0),
          note='Littelfuse 029707.5WXNV mini blade, 32 V')
    B.add('F2', 'PTC', 'RXEF110', {1: '+24V', 2: 'VAUX'}, 26.0, 35.0, 0, ref_at=(28.54, 38.2, 0),
          note='1.1 A hold / 2.2 A trip resettable: 12 V and 5 V bucks only')
    B.add('C2', 'C100n', '100n', {1: '+24V', 2: 'GND'}, 30.0, 41.0, 0, ref_at=(31.25, 43.4, 0))
    B.conn('J2', 'MSTBVA2', 'DPS5005 input: 1 IN+ (fused) 2 IN-', [('+24V_DPS', '24V'), ('GND', 'GND')], 32.0, 16.2, 0,
           label='DPS IN', ref_at=(26.7, 16.2, 90))
    B.group = 'Logic, fan and motor supplies (TRACO TSR SIP bucks)'
    B.add('U1', 'TSR12', 'TSR 2-24120N', {1: 'VAUX', 2: 'GND', 3: '+12V'}, 60.8, 26.3, 0, ref_at=(56.0, 24.0, 90),
          note='12 V 2 A: fans, relay coils, thermostat loop and StepStick VMOT')
    # TRACO TSR 2N datasheet: no traces under the converter body (pins sit 1.44 mm from one face).
    B.keepouts.append((54.8, 22.0, 59.4, 35.7, 'no tracks under TSR 2N (TRACO)', 'tracks'))
    B.add('U2', 'TSR5', 'TSR 1-2450', {1: 'VAUX', 2: 'GND', 3: '+5V'}, 42.5, 30.0, 0, ref_at=(45.0, 26.0, 0))
    B.add('C3', 'CP22u', '22u 50V', {1: 'VAUX', 2: 'GND'}, 38.9, 37.8, 0)
    B.add('C4', 'CP22u', '22u 50V', {1: '+12V', 2: 'GND'}, 44.45, 37.8, 0)
    B.add('C5', 'CP22u', '22u 50V', {1: '+5V', 2: 'GND'}, 50.0, 37.8, 0)
    B.conn('J3', 'VH3', '+12 V to tec card', LINK_12V, 12.0, 15.6, 0, label='12V OUT', ref_at=(10.0, 10.65, 0))
    B.group = 'StepStick (BTT TMC2209 V1.3; A4988 compatible) and motor, VMOT = +12 V'
    # VMOT comes from the regulated 12 V rail, not the 24 V brick: the TVS clamp (30-33 V) can no
    # longer reach the TMC2209 (29 V operating, 32 V abs max VS, Trinamic datasheet 19). 17HS08-1004S: 3.7 ohm,
    # 4.5 mH, 1 A -> at a few rpm torque is current-limited, not voltage-limited.
    # Pads 5 and 6 are linked (Pololu A4988 convention RESET = SLEEP, pulled up on the A4988 carrier).
    # BTT V1.3: pad 5 not connected on the module, pad 6 = CLK with 20 k to GND (internal clock).
    B.add('U4', 'STEPSTICK', 'TMC2209 StepStick', {1: 'MOT_EN', 4: 'TMC_UART', 5: 'SS_RST_SLP', 6: 'SS_RST_SLP',
                                                   7: 'STEP', 8: 'DIR', 9: '+12V', 10: 'GND', 11: 'M2B', 12: 'M2A',
                                                   13: 'M1A', 14: 'M1B', 15: '+3V3', 16: 'GND'}, 65.0, 22.5, 0, ref_at=(71.35, 32.0, 90),
          note='pin 4 = TMC2209 PDN_UART (A4988 MS3: firmware holds the UART line low); pins 5-6 linked')
    B.add('C8', 'CP100u', '100u 50V', {1: '+12V', 2: 'GND'}, 73.0, 16.0, 0)
    B.conn('J8', 'VH4', 'MOTOR 2B 2A 1A 1B', [('M2B', 'MOTOR'), ('M2A', 'MOTOR'), ('M1A', 'MOTOR'), ('M1B', 'MOTOR')], 49.0, 15.6, 0,
           label='MOTOR', ref_at=(47.0, 10.65, 0))
    B.group = 'Link to ctrl card and 1-Wire sensor headers'
    B.conn('J9', 'XH11', 'LINK to D34-CTRL', LINK_PWR, 4.0, 6.3, 0, label='LINK-CTRL', ref_at=(2.0, 1.6, 0))
    s3 = lambda net: [('GND', 'GND'), (net, 'LOGIC'), ('+3V3', '3V3')]
    # Harness-access pass: one header per 1-Wire bus (was five), 12 mm gaps between plug bodies; the harness
    # Y-splices each bus to its probes (A: chamber air + near-serving food, B: hot sink + room).
    for ref, x, y, net, lab in [('J4', 46.0, 6.3, 'OWA', 'chamber + food probes'), ('J6', 68.0, 6.3, 'OWB', 'hot-sink + room probes')]:
        B.conn(ref, 'XH3', f'1-WIRE {"A" if net == "OWA" else "B"} ({lab})', s3(net), x, y, 0,
               label=f'1W-{net[-1]}', ref_at=((x - 2.0, 1.6, 0) if y < 10 else (x + 2.5, 20.2, 0)))
    B.R('R3', '4.7k', '+3V3', 'OWB', 54.6, 42.4, 0, ref_at=(58.41, 42.4, 0), note='1-Wire bus B pull-up')
    for s, x in [('LINK', 23.0), ('1W-A', 50.5), ('1W-B', 72.5)]:
        B.text(s, x, 1.6)
    # ---------------------------------------------------------- hand-placed high-current copper (locked)
    B.track('VIN_RAW', 'FB', 2.5, [(4.0, 19.5), (7.54, 23.04), (7.54, 25.4)])
    B.track('VIN_RAW', 'FB', 2.0, [(7.54, 25.4), (7.54, 27.0)])   # 2.0 mm between the TO-220 gate and source pads
    B.track('+24V', 'FB', 1.5, [(10.08, 27.0), (10.62, 30.0)])
    B.track('+24V', 'FB', 2.0, [(10.62, 30.0), (14.0, 30.7), (15.5, 31.0)])
    B.track('+24V', 'FB', 2.5, [(15.5, 31.0), (17.5, 25.0), (22.5, 25.0), (22.5, 41.8), (21.5, 41.8)])
    B.track('+24V', 'FB', 2.5, [(22.5, 26.0), (25.0, 26.0)])
    B.track('+24V', 'FB', 1.5, [(22.5, 35.0), (26.0, 35.0)])
    B.track('+24V', 'FB', 1.5, [(22.5, 41.0), (30.0, 41.0)])   # C2 (100 nF) on the 24 V rail
    B.track('+24V_DPS', 'F', 2.5, [(34.92, 26.0), (34.92, 23.5), (32.0, 20.6), (32.0, 16.2)])
    B.track('GND', 'B', 2.5, [(4.0, 14.0), (6.5, 11.5), (34.5, 11.5), (37.08, 14.08), (37.08, 16.2)])
    return B


# ======================================================================
# TEC relay card, 315 deg bay
# ======================================================================
def tec():
    B = Board('d34-tec', 'Cat feeder D34 TEC relay card (K1 cut-off, K2 reversal, fans; 315 deg bay)', 'D34-TEC', bay='315 deg')
    B.comment1 = 'K1 coil current flows through the series hot-sink thermostats: an open thermostat drops TEC power without firmware.'
    B.comment2 = 'DPS OUT- is not ground (DPS low-side shunt): TEC nets stay isolated. K2 form C is break-before-make.'
    HC = ['DPS_OUT_P', 'DPS_OUT_N', 'K1_MID', 'TEC_P', 'TEC_A', 'TEC_B']
    B.netclasses = {'TEC': dict(width=2.5, clearance=0.5, nets=HC),
                    'Power': dict(width=0.8, clearance=0.3, nets=['GND', '+3V3', 'THERMO_RET', 'K2_SUP', 'FAN1_12', 'FAN2_12', 'FAN3_12',
                                                                  'FAN2_N', 'FAN3_N']),
                    'P12': dict(width=2.0, clearance=0.3, nets=['+12V'])}
    B.solid_pads = set(HC)
    B.group = 'TEC cut-off K1 (double-break, thermostat-fed coil) and polarity reversal K2'
    B.add('K1', 'G2RL2', 'G2RL-2 DC12', {'A1': 'THERMO_RET', 'A2': 'K1_COILN', '21': 'DPS_OUT_P', '24': 'K1_MID',
                                       '11': 'K1_MID', '14': 'TEC_P'}, 3.0, 41.2, 90, ref_at=(10.5, 37.45, 0),
          note='both poles in series on OUT+ for double-break DC interruption')
    B.add('K2', 'G2RL2', 'G2RL-2 DC12', {'A1': 'K2_SUP', 'A2': 'K2_COILN', '11': 'TEC_A', '12': 'TEC_P', '14': 'DPS_OUT_N',
                                       '21': 'TEC_B', '22': 'DPS_OUT_N', '24': 'TEC_P'}, 60.0, 33.7, 270, ref_at=(52.5, 37.45, 0),
          note='de-energised = cooling (A = OUT+); energised = defrost; form C is break-before-make')
    # K1 flyback = 1N5817 + 15 V zener: the coil field collapses against ~27 V, so K1 releases fast (sim what-if).
    B.add('D1', 'D_5817V', '1N5817', {1: 'K1_CLAMP', 2: 'K1_COILN'}, 65.2, 32.0, 270, ref_at='hide',
          note='K1 flyback with DZ2: clamp ~27.5 V (Q2 2N3904 VCEO 40 V)')
    B.add('DZ2', 'DZ15V', 'BZX79-C15', {1: 'K1_CLAMP', 2: 'THERMO_RET'}, 65.2, 37.2, 270, ref_at='hide')
    B.conn('J2', 'MF6', 'DPS5005 output: 1-3 OUT+, 4-6 OUT-',
           [('DPS_OUT_P', 'TEC'), ('DPS_OUT_P', 'TEC'), ('DPS_OUT_P', 'TEC'), ('DPS_OUT_N', 'TEC'), ('DPS_OUT_N', 'TEC'), ('DPS_OUT_N', 'TEC')],
           23.0, 20.5, 0, label='DPS OUT', ref_at=(16.8, 23.5, 90))
    B.conn('J3', 'MF4', 'TEC array 2S2P: 1 A 2 B 3 A 4 B', [('TEC_A', 'TEC'), ('TEC_B', 'TEC'), ('TEC_A', 'TEC'), ('TEC_B', 'TEC')],
           51.8, 20.5, 0, label='TEC', ref_at='hide')
    B.conn('J4', 'VH2', 'Hot-sink thermostats (series NC loop, 12 V / 35 mA)', [('LOOP12', '12V'), ('THERMO_RET', '12V')], 38.0, 21.0, 0,
           label='THERMO', ref_at=(39.98, 27.4, 0))
    B.add('R1', 'RV', '1k', {1: 'THERMO_RET', 2: 'THERMO_OK'}, 54.7, 12.0, 270, ref_at='hide')
    B.add('R2', 'RV', '330', {1: 'THERMO_OK', 2: 'GND'}, 57.1, 12.0, 270, ref_at='hide',
        note='12 V loop -> 2.98 V at the ESP32 input (2.83-3.13 V for 11.4-12.6 V); 9 mA, 81 mW in R1 (0.4 W part)')
    B.group = 'Coil drivers (2N3904), K2 hold-up, fan low sides (IRLZ44N) with per-channel PTCs'
    # Sim round 2026-10-26 (kb/d34-simulation.md): the ULN2003 is gone.
    #  - K1/K2 low sides are 2N3904 (VCE(sat) <= 0.2 V vs ~0.9 V): ~0.7 V more coil voltage (pick-up margin).
    #  - K2 hold-up: D5 feeds K2's coil (K2_SUP) and C1 220 uF sits directly across the coil. If +12 V or 3.3 V (K2_ON) is lost, C1 keeps K2 energised for tens of ms (tau ~79 ms) while K1, fed through the
    #    thermostats with a diode + 15 V zener clamp, releases within a few ms: K1 always breaks the TEC current.
    #  - Fans: switched DC (no 25 kHz PWM) through IRLZ44N low sides with a flyback diode each, and every fan feed
    #    through its own RXEF050 (0.5 A hold) so a shorted lead trips a PTC instead of killing a driver.
    yr, yq = 12.0, 13.3     # vertical resistors / TO-92 row in the band between the plug rows
    B.add('Q2', '2N3904', '2N3904', {1: 'GND', 2: 'Q2_B', 3: 'K1_COILN'}, 2.5, yq, 0, ref_at='hide', note='K1 coil low side')
    B.add('R4', 'RV', '1k', {1: 'K1_ON', 2: 'Q2_B'}, 11.0, yr, 270, ref_at='hide')
    B.add('R5', 'RV', '47k', {1: 'Q2_B', 2: 'GND'}, 13.4, yr, 270, ref_at='hide', note='K1 off if the ctrl lead is unplugged')
    B.add('Q3', '2N3904', '2N3904', {1: 'GND', 2: 'Q3_B', 3: 'K2_COILN'}, 47.4, yq, 0, ref_at='hide', note='K2 coil low side')
    B.add('R6', 'RV', '1k', {1: 'K2_ON', 2: 'Q3_B'}, 24.5, yr, 270, ref_at='hide')
    B.add('R7', 'RV', '47k', {1: 'Q3_B', 2: 'GND'}, 26.9, yr, 270, ref_at='hide')
    B.add('R9', 'RV', '47k', {1: 'FAN2_PWM', 2: 'GND'}, 29.3, yr, 270, ref_at='hide', note='FAN2 FET gate pull-down')
    B.add('R10', 'RV', '47k', {1: 'FAN3_PWM', 2: 'GND'}, 31.7, yr, 270, ref_at='hide', note='FAN3 FET gate pull-down')
    B.add('R3', 'RV', '4.7k', {1: 'FAN1_PWM', 2: 'FAN1_B'}, 34.1, yr, 270, ref_at='hide', note='FAN1 PWM open collector (inverted)')
    B.add('Q1', '2N3904', '2N3904', {1: 'GND', 2: 'FAN1_B', 3: 'FAN1_OD'}, 36.5, yq, 0, ref_at='hide', note='FAN1 PWM open collector, next to J5')
    B.add('D7', 'D_5817V', '1N5817', {1: 'FAN2_12', 2: 'FAN2_N'}, 44.6, yr, 270, ref_at='hide', note='FAN2 flyback')
    # K2 hold-up: C1 directly across the coil, fed through D5. Q3's limited collector current (beta x 2.5 mA)
    # charges C1 softly (~30 ms) when K2 is commanded on; firmware waits >= 0.4 s anyway.
    B.add('D5', 'D_5817V', '1N5817', {1: 'K2_SUP', 2: '+12V'}, 72.24, 21.5, 180, ref_at='hide', note='K2 hold-up isolation')
    B.add('D8', 'D_5817V', '1N5817', {1: 'FAN3_12', 2: 'FAN3_N'}, 76.4, 21.5, 0, ref_at='hide', note='FAN3 flyback')
    B.add('C1', 'CP220u', '220u 35V', {1: 'K2_SUP', 2: 'K2_COILN'}, 72.5, 15.5, 0, ref_at='hide', note='K2 hold-up (tau ~79 ms with the coil)')
    B.add('F1', 'PTC050', 'RXEF050', {1: '+12V', 2: 'FAN1_12'}, 61.2, 12.4, 0, ref_at='hide', note='FAN1 feed')
    B.add('F2', 'PTC050', 'RXEF050', {1: '+12V', 2: 'FAN2_12'}, 61.2, 16.2, 0, ref_at='hide', note='FAN2 (blower) feed')
    B.add('F3', 'PTC050', 'RXEF050', {1: '+12V', 2: 'FAN3_12'}, 61.2, 20.0, 0, ref_at='hide', note='FAN3 (spare) feed')
    B.add('Q4', 'IRLZ44N', 'IRLZ44N', {1: 'FAN2_PWM', 2: 'FAN2_N', 3: 'GND'}, 62.0, 26.9, 0, ref_at='hide', note='FAN2 low side')
    B.add('Q5', 'IRLZ44N', 'IRLZ44N', {1: 'FAN3_PWM', 2: 'FAN3_N', 3: 'GND'}, 72.7, 26.9, 0, ref_at='hide', note='FAN3 low side')
    B.conn('J5', 'FAN4', 'FAN1 12 V 4-pin PWM (NF-A12x25)', [('GND', 'GND'), ('FAN1_12', '12V'), ('TACH1', 'LOGIC'), ('FAN1_OD', 'LOGIC')],
           37.0, 6.4, 0, label='FAN1', ref_at=(35.0, 1.6, 0))
    B.conn('J6', 'FAN4', 'FAN2 12 V blower (switched DC low side), tach', [('FAN2_N', 'FANGND'), ('FAN2_12', '12V'), ('TACH2', 'LOGIC'), (None, 'NC')],
           48.5, 6.4, 0, label='FAN2', ref_at=(46.5, 1.6, 0))
    B.conn('J7', 'FAN4', 'FAN3 spare 12 V (switched low side: fan or external relay <= 0.4 A)', [('FAN3_N', 'FANGND'), ('FAN3_12', '12V'), (None, 'NC'), (None, 'NC')],
           60.0, 6.4, 0, label='FAN3', ref_at=(58.0, 1.6, 0))
    # Sim round 2 (defect A): 12 V undervoltage cut-off for K1, entirely in the 12 V domain (independent of 3.3 V).
    # The thermostat loop (and so K1's coil) is fed through Q6 (BC327). TL431 U1 holds Q6 on while
    # +12 V x 330/(1k + 330) > 2.495 V; R14 (10 k) from the switched loop feed to REF adds hysteresis:
    # K1 is cut below ~9.4 V and re-enabled above ~10.3 V. A slowly falling rail therefore opens K1 at
    # ~9.4 V, before either relay's drop-out, while K2 is still held by D5/C1.
    B.add('U1', 'TL431', 'TL431AILPG', {1: 'UV_REF', 2: 'GND', 3: 'UV_K'}, 69.6, 38.0, 90, ref_at='hide')
    B.add('Q6', 'BC327', 'BC327-25', {1: 'LOOP12', 2: 'Q6_B', 3: '+12V'}, 74.4, 38.0, 90, ref_at='hide',
          note='thermostat-loop supply switch (42 mA)')
    B.add('R11', 'RV', '1k', {1: '+12V', 2: 'UV_REF'}, 77.6, 32.0, 270, ref_at='hide')
    B.add('R13', 'RV', '330', {1: 'UV_REF', 2: 'GND'}, 79.8, 32.0, 270, ref_at='hide')
    B.add('R14', 'RV', '10k', {1: 'LOOP12', 2: 'UV_REF'}, 71.5, 41.5, 0, ref_at='hide', note='UV hysteresis')
    B.add('R15', 'RV', '4.7k', {1: 'Q6_B', 2: 'UV_K'}, 76.2, 41.5, 0, ref_at='hide', note='Q6 base drive (TL431 cathode ~2 mA)')
    B.group = 'Links: XH-12 to ctrl card, VH-3 +12 V from pwr card'
    B.conn('J9', 'XH12', 'LINK to D34-CTRL', LINK_TEC, 4.0, 6.3, 0, label='LINK-CTRL', ref_at=(2.0, 1.6, 0))
    # Harness-access pass: the tall second-row plugs (VH 16.5 mm, Mini-Fit 23.5 mm mated) sit 5 mm lower,
    # leaving ~9 mm between them and the fan plugs above.
    B.conn('J1', 'VH3', '+12 V from pwr card', LINK_12V, 4.0, 21.0, 0, label='12V IN', ref_at=(2.0, 15.65, 0))
    for s, x in [('LINK', 23.0), ('F1', 41.0), ('F2', 52.5), ('F3', 64.0)]:
        B.text(s, x, 1.6)
    # ---------------------------------------------------------- hand-placed TEC copper (locked)
    B.track('DPS_OUT_P', 'F', 2.5, [(23.0, 20.5), (31.4, 20.5)])
    B.track('DPS_OUT_P', 'F', 2.5, [(23.0, 20.5), (17.5, 20.5), (17.5, 29.0), (23.0, 33.7)])
    B.track('DPS_OUT_N', 'B', 2.5, [(23.0, 26.0), (31.4, 26.0)])
    B.track('DPS_OUT_N', 'F', 2.5, [(31.4, 26.0), (35.0, 29.6), (35.0, 33.7)])
    B.track('DPS_OUT_N', 'B', 2.5, [(35.0, 33.7), (37.5, 37.45), (42.5, 37.45), (45.0, 41.2)])
    B.track('K1_MID', 'F', 2.5, [(28.0, 33.7), (25.5, 36.2), (25.5, 38.7), (23.0, 41.2)])
    B.track('TEC_P', 'F', 2.5, [(28.0, 41.2), (35.0, 41.2), (37.5, 37.45), (42.5, 37.45), (45.0, 33.7)])
    B.track('TEC_A', 'F', 2.5, [(40.0, 33.7), (40.0, 30.5), (44.5, 26.0), (51.8, 26.0), (51.8, 20.5)])
    B.track('TEC_B', 'B', 2.5, [(40.0, 41.2), (40.0, 44.0), (48.5, 44.0)])
    # +12 V trunk, hand-laid 2.0 mm (sim round: the TSR 2 current limit is 7.2 A into a short): J1 -> band at y 17
    # (between the band parts and the second-row plugs) -> J4, D5 and the three fan PTCs.
    B.track('+12V', 'F', 2.0, [(4.0, 21.0), (4.0, 17.0), (59.2, 17.0), (61.2, 16.2)])
    B.track('+12V', 'F', 2.0, [(11.92, 21.0), (11.92, 17.0)])
    B.track('+12V', 'F', 1.5, [(61.2, 20.0), (61.2, 22.3), (68.9, 22.3), (69.7, 21.5)])   # to D5 (K2 hold-up feed)
    # +12 V branch to the UV cut-off (Q6 emitter, R11) between Q4 and Q5, hand-laid 1.5 mm.
    B.track('+12V', 'F', 1.5, [(69.7, 21.5), (69.9, 23.0), (69.9, 30.5), (77.6, 30.5), (77.6, 32.0)])
    B.track('+12V', 'F', 1.5, [(74.4, 30.5), (74.4, 32.92)])
    B.track('+12V', 'F', 2.0, [(61.2, 12.4), (61.2, 20.0)])
    B.track('TEC_B', 'B', 2.5, [(48.5, 44.0), (48.5, 31.0), (56.0, 31.0), (56.0, 20.5)])
    return B


BOARDS = {'ctrl': ctrl, 'pwr': pwr, 'tec': tec}
BAYS = {'d34-ctrl': '45 deg', 'd34-pwr': '225 deg', 'd34-tec': '315 deg'}
