"""Read-only electrical requirements; no PCB-generator imports or KiCad dependency."""

import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


PCB = Path(__file__).resolve().parents[1] / "pcb"
# Independent review §0, 2026-10-24; deliberately not learned from the manifest.
REVIEWED_MANIFEST_SHA256 = "9fa46fefed298d092bc83b532faa0848905522ade1cb9342ddb9abefd91d803f"
REVIEWED_SOURCES = {
    "feeder.kicad_sch": "e654d14f7e0a30f93cc36065ead615d0bef2af4178c14e23c3849ab7990fcace",
    "feeder.kicad_pcb": "d51e589d13a7a96097fe12be33ff051cb9bbc9b4033ba4c07ba581e1121458c9",
}


class RuleViolation(AssertionError):
    pass


def require(condition, message):
    if not condition:
        raise RuleViolation(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_provenance(read_bytes=None):
    """Verify all 85 artifacts including real schematic/board; never rewrite hashes."""
    if read_bytes is None:
        read_bytes = lambda name: (PCB / name).read_bytes()
    raw = read_bytes("checksums.json")
    require(sha256(raw) == REVIEWED_MANIFEST_SHA256, "reviewed manifest identity changed")
    manifest = json.loads(raw)
    require(len(manifest) == 85, "reviewed manifest must cover 85 files")
    for name, expected in manifest.items():
        require(sha256(read_bytes(name)) == expected, f"artifact hash mismatch: {name}")
    for name, expected in REVIEWED_SOURCES.items():
        require(manifest.get(name) == expected, f"reviewed source identity changed: {name}")
    return manifest


def normalize(net):
    return net.removeprefix("/")


def quantity(value):
    """First SI value token; remaining capacitor voltage/part description is retained elsewhere."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([pnumkM]?)", value.split()[0])
    require(match is not None, f"unsupported passive value: {value}")
    return float(match[1]) * {"": 1, "p": 1e-12, "n": 1e-9, "u": 1e-6,
                             "m": 1e-3, "k": 1e3, "M": 1e6}[match[2]]


class Netlist:
    """Actual exported XML nodes, including singleton NC nets."""

    def __init__(self, root):
        self.root = root
        components = root.findall("components/comp")
        self.components = {c.attrib["ref"]: c for c in components}
        require(len(components) == len(self.components), "duplicate component references")
        self.pins = {}
        self.nodes = {}
        for net in root.findall("nets/net"):
            name = normalize(net.attrib["name"])
            require(name not in self.nodes, f"duplicate net name: {name}")
            self.nodes[name] = set()
            for node in net.findall("node"):
                pin = (node.attrib["ref"], node.attrib["pin"])
                require(pin not in self.pins, f"duplicate netlist pin: {pin}")
                require(pin[0] in self.components, f"unknown component: {pin}")
                self.pins[pin] = name
                self.nodes[name].add(pin)

    @classmethod
    def load(cls):
        return cls(ET.parse(PCB / "schematic-netlist.xml").getroot())

    def net(self, pin):
        require(pin in self.pins, f"disconnected/missing pin: {pin}")
        return self.pins[pin]

    def same(self, *pins):
        names = {self.net(pin) for pin in pins}
        require(len(names) == 1, f"required connection broken: {pins}: {names}")
        return names.pop()

    def distinct(self, *pins):
        require(len({self.net(p) for p in pins}) == len(pins), f"unexpected short: {pins}")

    def members(self, pin, expected):
        require(self.nodes[self.net(pin)] == set(expected), f"unexpected nodes at {pin}")

    def part(self, ref, library, part):
        require(ref in self.components, f"missing component: {ref}")
        source = self.components[ref].find("libsource")
        require(source is not None and source.attrib.get("lib") == library
                and source.attrib.get("part") == part, f"incorrect device at {ref}")

    def passive(self, kind, a, b, value, ref=None):
        """Find an exact two-terminal device by endpoints, independent of ref/net labels."""
        ends = {self.net(a), self.net(b)}
        require(len(ends) == 2, f"short across passive endpoints: {a}, {b}")
        matches = []
        for name, comp in self.components.items():
            if kind != "R" and ref is not None and name != ref:
                continue
            source = comp.find("libsource")
            if source is None or source.attrib.get("lib") != "Device":
                continue
            if source.attrib.get("part") != kind:
                continue
            if {self.pins.get((name, "1")), self.pins.get((name, "2"))} == ends:
                matches.append(name)
        require(len(matches) == 1, f"expected one {kind} between {a} and {b}, got {matches}")
        found = matches[0]
        if ref is not None:
            require(found == ref, f"critical reference {ref} replaced with {found}")
        actual = quantity(self.components[found].findtext("value"))
        require(math.isclose(actual, value, rel_tol=1e-9), f"wrong {found} value: {actual}, expected {value}")
        return actual


GND = ("J2", "1")
V3 = ("U1", "2")
V5 = ("J2", "2")
V12 = ("J2", "3")
VMOT = ("J1", "1")


def check_rails(n):
    # Connector names here are an interface contract, not generator labels.
    for pin, name in ((GND, "GND"), (V3, "+3V3"), (V5, "+5V"),
                      (V12, "+12V"), (VMOT, "VMOT")):
        require(n.net(pin) == name, f"wrong rail at {pin}")
    n.distinct(GND, V3, V5, V12, VMOT)
    n.part("U2", "Regulator_Linear", "AP2112K-3.3")
    n.same(V5, ("U2", "1"), ("U2", "3"))  # VIN and EN
    n.same(V3, ("U2", "5"))
    n.same(GND, ("J1", "2"), ("U2", "2"), ("U1", "1"),
           ("U1", "15"), ("U1", "38"), ("U1", "39"))
    n.members(("U2", "4"), [("U2", "4")])
    n.members(V5, [V5, ("U2", "1"), ("U2", "3"), ("C1", "1")])
    n.members(V12, [V12, ("J3", "2"), ("C11", "1")])
    # Only carrier VMOT, bulk storage and high-impedance ADC spur get motor power.
    n.members(VMOT, [VMOT, ("J15", "1"), ("C10", "1"), ("R18", "1")])
    for ref, rail, cap in (("C1", V5, 10e-6), ("C2", V3, 10e-6),
                           ("C3", V3, 100e-9), ("C4", V3, 10e-6),
                           ("C11", V12, 10e-6)):
        n.passive("C", rail, GND, cap, ref)


def check_boot_and_programming(n):
    n.part("U1", "RF_Module", "ESP32-WROOM-32E")
    n.same(("U1", "3"), ("J13", "1"))
    n.same(("U1", "25"), ("J12", "1"))
    n.same(GND, ("J12", "2"), ("J13", "2"), ("J11", "1"))
    n.same(V3, ("J11", "4"))
    n.same(("U1", "35"), ("J11", "2"))  # GPIO1 TX0
    n.same(("U1", "34"), ("J11", "3"))  # GPIO3 RX0
    n.passive("R", V3, ("U1", "3"), 10e3, "R1")
    n.passive("C", ("U1", "3"), GND, 1e-6, "C5")
    n.passive("R", V3, ("U1", "25"), 10e3, "R2")
    # Unloaded boot straps GPIO2,12,5,15; unused flash/NC pins remain singleton.
    for pin in ("14", "23", "24", "29", "17", "18", "19", "20", "21", "22", "32"):
        n.members(("U1", pin), [("U1", pin)])


def check_fan(n):
    n.part("Q1", "Transistor_BJT", "MMBT3904")
    n.same(GND, ("J3", "1"), ("Q1", "2"))  # E
    n.same(V12, ("J3", "2"))
    n.same(("J3", "4"), ("Q1", "3"))  # C; fan motor current never enters Q1
    n.members(("J3", "4"), [("J3", "4"), ("Q1", "3")])
    n.passive("R", ("U1", "11"), ("Q1", "1"), 4.7e3, "R8")  # GPIO26 -> B
    n.passive("R", ("Q1", "1"), GND, 100e3, "R9")
    n.passive("R", V3, ("J3", "3"), 10e3, "R6")
    n.passive("R", ("J3", "3"), ("U1", "6"), 1e3, "R7")  # GPIO34 input
    n.distinct(("J3", "4"), ("J3", "3"), ("U1", "11"), V12, V3, GND)
    # This verifies the bias topology only. Full-speed reset requires the real
    # fan's internal pull-up, MCU high-Z and working 12 V supply.


def check_sensor_buses(n):
    n.same(GND, ("J4", "1"), ("J5", "1"), ("J6", "1"), ("J7", "1"), ("J8", "1"))
    n.same(V3, ("J4", "3"), ("J5", "3"), ("J6", "3"), ("J7", "3"), ("J8", "2"))
    n.same(("U1", "12"), ("J4", "2"), ("J5", "2"))  # GPIO27 shared bus
    n.passive("R", V3, ("J4", "2"), 4.7e3, "R3")
    n.members(("J4", "2"), [("J4", "2"), ("J5", "2"), ("U1", "12"), ("R3", "2")])
    for connector, pad, resistor in (("J6", "8", "R4"), ("J7", "9", "R5")):
        n.same((connector, "2"), ("U1", pad))  # GPIO32/33
        n.passive("R", V3, (connector, "2"), 10e3, resistor)
    for pin, pad, resistor in (("3", "33", "R16"), ("4", "36", "R17")):
        n.same(("J8", pin), ("U1", pad))  # GPIO21/22
        n.passive("R", V3, ("J8", pin), 4.7e3, resistor)
    n.distinct(("J4", "2"), ("J6", "2"), ("J7", "2"), ("J8", "3"), ("J8", "4"), V3, GND)


def check_uart(n):
    for ref in ("U3", "U4"):
        n.part(ref, "74xGxx", "74LVC1G125")
        n.same(GND, (ref, "3"))
        n.same(V3, (ref, "5"))
    n.same(GND, ("J9", "1"))
    n.same(("U1", "16"), ("U3", "1"), ("U4", "1"))  # GPIO13 /OE
    n.passive("R", V3, ("U3", "1"), 10e3, "R14")  # disabled at reset
    n.same(("U1", "28"), ("U3", "2"))  # GPIO17 -> A
    n.passive("R", V3, ("U3", "2"), 10e3, "R20")  # data idle high, not only OE
    n.passive("R", ("U3", "4"), ("J9", "2"), 1e3, "R15")  # Y -> DPS RX
    n.same(("J9", "3"), ("U4", "2"))  # DPS TX -> A
    n.passive("R", ("U4", "2"), GND, 10e3, "R21")  # absent/off input low
    n.same(("U4", "4"), ("U1", "27"))  # Y -> GPIO16
    n.distinct(("U3", "1"), ("U3", "2"), ("U3", "4"), ("J9", "2"),
               ("U4", "2"), ("U4", "4"), V3, GND)
    n.members(("J9", "3"), [("J9", "3"), ("U4", "2"), ("R21", "1")])
    for cap in ("C6", "C7"):
        n.passive("C", V3, GND, 100e-9, cap)


def check_motor(n):
    n.same(GND, ("J14", "1"), ("J15", "2"), ("J15", "8"))
    n.same(V3, ("J14", "2"), ("J14", "3"), ("J14", "4"), ("J15", "7"))
    n.same(VMOT, ("J15", "1"))
    n.same(("U1", "37"), ("J14", "5"), ("J14", "6"))  # GPIO23, RESET/SLEEP
    run_down = n.passive("R", ("J14", "5"), GND, 10e3, "R11")
    for carrier_pin, mcu_pin, resistor in (("7", "30", "R12"), ("8", "31", "R13")):
        n.same(("J14", carrier_pin), ("U1", mcu_pin))  # GPIO18 STEP / GPIO19 DIR
        n.passive("R", ("J14", carrier_pin), GND, 100e3, resistor)
    for pin, connector, output_pin in (("3", "J17", "2"), ("4", "J17", "1"),
                                      ("5", "J16", "1"), ("6", "J16", "2")):
        n.same(("J15", pin), (connector, output_pin))
        n.members(("J15", pin), [("J15", pin), (connector, output_pin)])
    n.same(VMOT, ("C10", "1"))  # polarity matters
    n.same(GND, ("C10", "2"))
    n.passive("C_Polarized", VMOT, GND, 100e-6, "C10")
    require("50V" in n.components["C10"].findtext("value"), "motor capacitor voltage rating changed")
    n.passive("C", V3, GND, 100e-9, "C9")
    # EXTERNAL assumption from Pololu carrier schematic, not a fitted PCB part.
    carrier_sleep_pullup = 100e3
    worst_ratio = run_down * 1.01 / (carrier_sleep_pullup * 0.95 + run_down * 1.01)
    require(worst_ratio < 0.3, "RESET/SLEEP not below A4988 0.3*VDD low threshold")


def check_adc(n):
    adc = ("U1", "7")  # GPIO35 / ADC1
    top = n.passive("R", VMOT, adc, 100e3, "R18")
    bottom = n.passive("R", adc, GND, 10e3, "R19")
    cap = n.passive("C", adc, GND, 100e-9, "C8")
    n.members(adc, [adc, ("R18", "2"), ("R19", "1"), ("C8", "1")])
    require(math.isclose(24 * bottom / (top + bottom), 24 / 11), "ADC divider transfer")
    require(24 * bottom * 1.01 / (top * 0.99 + bottom * 1.01) < 3.3, "24 V + resistor tolerance exceeds logic rail")
    require(0.0008 < (top * bottom / (top + bottom)) * cap < 0.001, "ADC RC outside reviewed nominal range")


def check_tec_logic_only(n):
    n.same(GND, ("J10", "1"))
    n.same(("J10", "2"), ("U1", "10"))  # GPIO25
    n.passive("R", ("J10", "2"), GND, 10e3, "R10")
    n.members(("J10", "2"), [("J10", "2"), ("U1", "10"), ("R10", "1")])
    n.distinct(("J10", "2"), VMOT, V12, V5, V3, GND)


DOMAIN_CHECKS = (check_rails, check_boot_and_programming, check_fan, check_sensor_buses,
                 check_uart, check_motor, check_adc, check_tec_logic_only)


def sexpr(text):
    """Small read-only parser for KiCad's parenthesized board syntax."""
    stack, roots = [], []
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text):
        if token == "(":
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            require(bool(stack), "unbalanced PCB syntax")
            stack.pop()
        else:
            require(bool(stack), "atom outside PCB root")
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    require(not stack and len(roots) == 1, "unbalanced/multiple PCB roots")
    return roots[0]


def children(node, kind):
    return [item for item in node if isinstance(item, list) and item and item[0] == kind]


def board_data(text):
    """Actual footprint pads (all repeated EPAD lands checked) and placed row geometry."""
    root = sexpr(text)
    require(root[0] == "kicad_pcb", "not a KiCad PCB")
    footprints, pads, positions = {}, {}, {}
    for fp in children(root, "footprint"):
        props = {p[1]: p[2] for p in children(fp, "property")}
        ref = props["Reference"]
        require(ref not in footprints, f"duplicate PCB reference {ref}")
        footprints[ref] = props
        origin = children(fp, "at")[0]
        x, y = float(origin[1]), float(origin[2])
        angle = math.radians(float(origin[3]) if len(origin) > 3 else 0)
        for pad in children(fp, "pad"):
            if not pad[1]:
                continue
            key = (ref, pad[1])
            nets = children(pad, "net")
            name = normalize(nets[0][2]) if nets else ""
            if key in pads:
                require(pads[key] == name, f"split repeated pad net: {key}")
            pads[key] = name
            loc = children(pad, "at")[0]
            px, py = float(loc[1]), float(loc[2])
            positions.setdefault(key, (x + px * math.cos(angle) + py * math.sin(angle),
                                       y - px * math.sin(angle) + py * math.cos(angle)))
    return footprints, pads, positions
