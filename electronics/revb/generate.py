#!/usr/bin/env python3
"""Generate revision B's schematic and placement from explicit design inputs.

Run in the existing KiCad 9 container. Routing and release validation are
separate stages: this program never calls an unrouted placement a finished PCB.
"""
import copy
import csv
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

import pcbnew as p
import version
import project

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "pcb"
# Reuse the reviewed, read-only parser/library helpers and exact board outline.
sys.path.insert(0, str(LEGACY))
spec = importlib.util.spec_from_file_location("legacy_generator", LEGACY / "generate.py")
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
import outline

NAMESPACE = uuid.UUID("c1e69d14-780d-43d6-ae52-261a21a7b40b")
def uid(name): return str(uuid.uuid5(NAMESPACE, name))
SHEET = uid("sheet")
q, kids, kid, unq = legacy.q, legacy.kids, legacy.kid, legacy.unq
def xy(x, y): return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def load_symbol(libid):
    lib, name = libid.split(":")
    block_library = HERE / lib / (lib + ".kicad_sym")
    if block_library.exists():
        symbol = next(copy.deepcopy(s) for s in kids(legacy.parse(block_library.read_text()), "symbol")
                      if unq(s[1]) == name)
        symbol[1] = q(libid)
        return symbol
    custom = HERE / "symbols" / (libid.split(":")[-1] + ".kicad_sym")
    if custom.exists():
        symbol = copy.deepcopy(kids(legacy.parse(custom.read_text()), "symbol")[0])
        symbol[1] = q(libid)
        return symbol
    return legacy.libsymbol(libid)


def pins(symbol):
    return [pin for sub in kids(symbol, "symbol") for pin in kids(sub, "pin")]


def schematic(parts, ident, flags):
    libraries = {a["lib"]: load_symbol(a["lib"]) for a in parts}
    libraries["power:PWR_FLAG"] = load_symbol("power:PWR_FLAG")
    text = [f'''(kicad_sch (version 20250114) (generator "eeschema")
      (uuid "{SHEET}") (paper "A0")
      (title_block (title "Cat feeder — integrated USB-C PD controller")
        (rev {q(ident['silkscreen_identifier'])})
        (comment 1 "20V/5A PD, onboard stepper and switching regulators; external TEC regulator")
        (comment 2 "DESIGN IN DEVELOPMENT — see revision B validation and review records"))
      (lib_symbols {' '.join(legacy.dump(s) for s in libraries.values())})''']
    # Six functional columns. Global labels join blocks; every pin is wired or
    # explicitly marked no-connect. Oversize groups must be split by the caller.
    blocks = list(dict.fromkeys(a["block"] for a in parts))
    positions = {}
    for bindex, block in enumerate(blocks):
        if bindex >= 6:
            raise ValueError("Too many schematic blocks for A0")
        bx, by = 10 + bindex * 190, 0
        text.append(f'(text {q(block.upper())} (at {bx+60} {by+23} 0) (effects (font (size 3 3))) (uuid "{uid(block+"heading")}"))')
        devices = [a for a in parts if a["block"] == block]
        y = by + 45
        for a in devices:
            symbol_pins = pins(libraries[a["lib"]])
            ys = [float(kid(pin, "at")[2]) for pin in symbol_pins]
            span = max(ys) - min(ys)
            positions[a["ref"]] = (bx + 70, y + max(ys))
            y += max(24, span + 22)
        if y > 790:
            raise ValueError(f"Schematic block {block} exceeds its band; split it")
    for a in parts:
        x, y = [round(round(v / 1.27) * 1.27, 4) for v in positions[a["ref"]]]
        symbol = libraries[a["lib"]]
        symbol_pins = pins(symbol)
        actual = {unq(kid(pin, "number")[1]) for pin in symbol_pins}
        assert set(a["nets"]) <= actual, (a["ref"], set(a["nets"]) - actual)
        top = min(y - float(kid(pin, "at")[2]) for pin in symbol_pins)
        rx, ry, vx, vy = x, top - 6.35, x, top - 3.81
        if a["ref"][0] in "RCL":
            rx, ry, vx, vy = x + 14, y - 1.27, x + 14, y + 1.27
        props = [
            f'(property "Reference" {q(a["ref"])} (at {rx} {ry} 0) (effects (font (size 1.27 1.27))))',
            f'(property "Value" {q(a["value"])} (at {vx} {vy} 0) (effects (font (size 1 1))))',
            f'(property "Footprint" {q("feeder_b:"+a["fp"].split(":")[-1])} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))',
            f'(property "LCSC" {q(a["lcsc"])} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))',
        ]
        text.append(f'''(symbol (lib_id {q(a['lib'])}) (at {x} {y} 0) (unit 1)
          (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(a['ref'])}")
          {' '.join(props)}
          (instances (project "feeder-b" (path "/{SHEET}" (reference {q(a['ref'])}) (unit 1)))))''')
        for pin in symbol_pins:
            number = unq(kid(pin, "number")[1])
            at = kid(pin, "at")
            px, py, angle = x + float(at[1]), y - float(at[2]), float(at[3])
            net = a["nets"].get(number)
            if net is None:
                text.append(f'(no_connect (at {px} {py}) (uuid "{uid(a["ref"]+number+"NC")}"))')
                continue
            ex = round(px - 2.54 * math.cos(math.radians(angle)), 4)
            ey = round(py + 2.54 * math.sin(math.radians(angle)), 4)
            text.append(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(a["ref"]+number+"wire")}"))')
            la = 180 if angle == 180 else 0
            text.append(f'(global_label {q(net)} (shape input) (at {ex} {ey} {la}) (effects (font (size 0.9 0.9)) (justify left)) (uuid "{uid(a["ref"]+number+"label")}"))')
    for i, net in enumerate(flags):
        x, y, ref = 50 + i * 50, 810.26, f"#FLG0{i+1}"
        text.append(f'''(symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1)
          (in_bom no) (on_board yes) (dnp no) (uuid "{uid(ref)}")
          (property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
          (property "Value" "PWR_FLAG" (at {x} {y-4} 0) (effects (font (size 1 1))))
          (instances (project "feeder-b" (path "/{SHEET}" (reference "{ref}") (unit 1)))))
          (global_label {q(net)} (shape input) (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid(ref+'label')}"))''')
    text.append(")")
    (HERE / "feeder-b.kicad_sch").write_text("\n".join(text))
    names = sorted({a["lib"].split(":")[0] for a in parts} | {"power"})
    table = '(sym_lib_table (version 7)\n'
    for name in names:
        uri = f'${{KIPRJMOD}}/{name}/{name}.kicad_sym' if (HERE / name / (name + '.kicad_sym')).exists() else f'${{KICAD9_SYMBOL_DIR}}/{name}.kicad_sym'
        table += f'(lib (name "{name}") (type "KiCad") (uri "{uri}") (options "") (descr ""))\n'
    (HERE / "sym-lib-table").write_text(table + ')\n')
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o",
                    "schematic-netlist.xml", "feeder-b.kicad_sch"], cwd=HERE, check=True)


def placement(parts, ident, positions):
    board = p.BOARD()
    board.SetCopperLayerCount(4)
    settings = board.GetDesignSettings()
    settings.m_MinClearance = p.FromMM(.2)
    settings.m_CopperEdgeClearance = p.FromMM(.3)
    netclass = settings.m_NetSettings.GetDefaultNetclass()
    netclass.SetClearance(p.FromMM(.2))
    netclass.SetTrackWidth(p.FromMM(.25))
    netclass.SetViaDiameter(p.FromMM(.6))
    netclass.SetViaDrill(p.FromMM(.3))
    by_pin, nets = {}, {}
    for element in ET.parse(HERE / "schematic-netlist.xml").findall("./nets/net"):
        name = element.attrib["name"]
        nets[name] = p.NETINFO_ITEM(board, name)
        board.Add(nets[name])
        for node in element.findall("node"):
            by_pin[node.attrib["ref"], node.attrib["pin"]] = name
    fpdir = HERE / "feeder_b.pretty"
    fpdir.mkdir(exist_ok=True)
    for a in parts:
        lib, name = a["fp"].split(":")
        source = HERE / "footprints" if lib == "feeder_b" else Path("/usr/share/kicad/footprints") / (lib + ".pretty")
        block_footprints = HERE / lib / "footprints" / (lib + ".pretty")
        if block_footprints.exists(): source = block_footprints
        fp = p.FootprintLoad(str(source), name)
        assert fp, a["fp"]
        # Exact geometry is copied to a project-local library for portability.
        for zone in fp.Zones():
            layers = p.LSET()
            for layer in (p.F_Cu, p.In1_Cu, p.In2_Cu, p.B_Cu): layers.AddLayer(layer)
            zone.SetLayerSet(layers)
        p.PCB_IO_KICAD_SEXPR().FootprintSave(str(fpdir), fp)
        fp.SetReference(a["ref"])
        fp.SetValue(a["value"])
        fp.SetFPID(p.LIB_ID("feeder_b", name))
        fp.SetPath(p.KIID_PATH("/" + SHEET + "/" + uid(a["ref"])))
        x, y, angle = positions[a["ref"]]
        fp.SetPosition(xy(x, y))
        fp.SetOrientationDegrees(angle)
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(xy(1, 1))
        fp.Reference().SetTextThickness(p.FromMM(.15))
        numbers = {pad.GetNumber() for pad in fp.Pads()}
        assert set(a["nets"]) <= numbers, (a["ref"], set(a["nets"]) - numbers)
        for pad in fp.Pads():
            net = by_pin.get((a["ref"], pad.GetNumber()))
            if net: pad.SetNet(nets[net])
        board.Add(fp)
    for start, end in outline.LINES:
        shape = p.PCB_SHAPE()
        shape.SetShape(p.SHAPE_T_SEGMENT)
        shape.SetStart(xy(*start)); shape.SetEnd(xy(*end))
        shape.SetLayer(p.Edge_Cuts); shape.SetWidth(p.FromMM(.05)); board.Add(shape)
    for start, middle, end in outline.ARCS:
        shape = p.PCB_SHAPE()
        shape.SetShape(p.SHAPE_T_ARC)
        shape.SetArcGeometry(xy(*start), xy(*middle), xy(*end))
        shape.SetLayer(p.Edge_Cuts); shape.SetWidth(p.FromMM(.05)); board.Add(shape)
    zone = p.ZONE(board)
    zone.SetIsRuleArea(True)
    layers = p.LSET()
    for layer in (p.F_Cu, p.In1_Cu, p.In2_Cu, p.B_Cu): layers.AddLayer(layer)
    zone.SetLayerSet(layers)
    zone.SetDoNotAllowTracks(True); zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowCopperPour(True); zone.SetDoNotAllowPads(True)
    zone.SetZoneName("ESP32 antenna — no copper on any layer")
    zone.Outline().NewOutline()
    for x, y in [(40, 50), (100, 50), (100, 56.7), (40, 56.7)]:
        zone.Outline().Append(p.FromMM(x), p.FromMM(y))
    board.Add(zone)
    for text, x, y, size in [("CAT FEEDER", 74, 116.8, 1.2),
                              (ident["silkscreen_identifier"], 74, 119, 1.0)]:
        item = p.PCB_TEXT(board)
        item.SetText(text); item.SetPosition(xy(x, y)); item.SetTextSize(xy(size, size))
        item.SetTextThickness(p.FromMM(.15)); item.SetLayer(p.B_SilkS)
        item.SetMirrored(True); board.Add(item)
    settings.SetAuxOrigin(xy(*outline.ORIGIN))
    p.SaveBoard(str(HERE / "feeder-b-unrouted.kicad_pcb"), board)
    (HERE / "fp-lib-table").write_text('(fp_lib_table (version 7) (lib (name "feeder_b") (type "KiCad") (uri "${KIPRJMOD}/feeder_b.pretty") (options "") (descr "Revision B exact footprint copies")))\n')
    p.ExportSpecctraDSN(board, str(HERE / "feeder-b.dsn"))
    return board


def main():
    design = json.loads((HERE / "design.json").read_text())
    positions = json.loads((HERE / "placement.json").read_text())
    parts = design["parts"]
    assert len({a["ref"] for a in parts}) == len(parts), "Duplicate references"
    assert set(positions) == {a["ref"] for a in parts}, "Incomplete placement"
    sources = [HERE / "design.json", HERE / "placement.json", HERE / "generate.py", HERE / "version.py", HERE / "project.py", HERE / "compose.py",
               LEGACY / "generate.py", LEGACY / "outline.py", LEGACY / "project_rules.py"]
    sources += list((HERE / "footprints").glob("*.kicad_mod")) + list((HERE / "symbols").glob("*.kicad_sym"))
    for block in ("motor", "pd", "power"):
        sources += list((HERE / block / "footprints").glob("**/*.kicad_mod"))
        sources += list((HERE / block).glob("*.kicad_sym"))
    ident = version.write(sources)
    schematic(parts, ident, design["power_flags"])
    board = placement(parts, ident, positions)
    project.write(HERE, design["netclasses"])
    with (HERE / "design-bom.csv").open("w") as f:
        writer = csv.writer(f)
        writer.writerow(["Reference", "Value", "Footprint", "LCSC", "Assembly", "X_mm", "Y_mm", "Rotation_deg"])
        for a in parts: writer.writerow([a["ref"], a["value"], a["fp"], a["lcsc"], a["assembly"], *positions[a["ref"]]])
    print(f"Generated {len(parts)} components; {ident['silkscreen_identifier']}; UNROUTED placement")


if __name__ == "__main__":
    main()
