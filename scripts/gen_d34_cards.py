#!/usr/bin/env python3
"""Generate OpenSCAD/JSON models of the three D34 cards from their KiCad boards.

    python3 scripts/gen_d34_cards.py            # writes cad/generated/d34_cards*.{scad,json}

Inputs (read-only, owned by the electronics work):
  electronics/d34/d34-<card>/d34-<card>.kicad_pcb  footprints, pads, F.Fab/F.CrtYd, Edge.Cuts
  electronics/d34/d34-<card>/design.json           ref -> catalogue kind, connector roles
  electronics/d34/catalog.py                       installed heights (h), mated heights (mate_h)
  electronics/d34/parts3d.json (optional)          per-part 3D boxes; overrides the above

Board coordinates: u right, v down from the top-left corner seen from the
component side (as electronics/d34 README), w = height above the component face.
Plug heights and withdrawal travel are ESTIMATES (table PLUG below) unless
parts3d.json supplies them. Nothing here is a measured part.
"""
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D34 = ROOT / "electronics/d34"
OUT = ROOT / "cad/generated"
CARDS = ("d34-ctrl", "d34-pwr", "d34-tec")

# Mated plug geometry by connector family, ESTIMATES from catalogue drawings:
# plug_top = housing top above the board, engage = travel to withdraw the
# plug, straight = lead length leaving the housing before the first bend.
# The catalogue mate_h ("mated incl. cable bend") minus plug_top is the bend room.
PLUG = {
    "JST XH": dict(plug_top=12.0, engage=6.0, straight=3.0),
    "JST VH": dict(plug_top=17.0, engage=8.0, straight=4.0),
    "PC fan 4-pin (KK 254)": dict(plug_top=14.0, engage=6.5, straight=3.0),
    "Molex Mini-Fit Jr": dict(plug_top=19.0, engage=8.5, straight=5.0),
    "Phoenix MSTB 5.08": dict(plug_top=22.0, engage=9.0, straight=6.0),
}
COLOURS = {"R": "Tan", "C": "Goldenrod", "CP": "MidnightBlue", "D": "DimGray", "LED": "Lime",
           "J": "WhiteSmoke", "U": "Black", "K": "SteelBlue", "Q": "Black", "F": "Orange"}


# ------------------------------------------------------------------ s-expressions
def parse(text):
    toks = re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+', text)
    stack, root = [], None
    for t in toks:
        if t == "(":
            node = []
            (stack[-1].append(node) if stack else None)
            if not stack:
                root = node
            stack.append(node)
        elif t == ")":
            stack.pop()
        else:
            stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return root


def kids(node, name):
    return [n for n in node if isinstance(n, list) and n and n[0] == name]


def kid(node, name):
    k = kids(node, name)
    return k[0] if k else None


def xform(at, x, y):
    """Footprint-local point to board coordinates (KiCad, y down, angle in file)."""
    ax, ay = float(at[1]), float(at[2])
    a = math.radians(float(at[3])) if len(at) > 3 else 0.0
    return (ax + x * math.cos(a) + y * math.sin(a), ay - x * math.sin(a) + y * math.cos(a))


def graphic_points(g):
    pts = []
    for key in ("start", "end", "mid", "center"):
        k = kid(g, key)
        if k:
            pts.append((float(k[1]), float(k[2])))
    if g[0] == "fp_circle":
        c, e = kid(g, "center"), kid(g, "end")
        cx, cy, r = float(c[1]), float(c[2]), math.dist((float(c[1]), float(c[2])), (float(e[1]), float(e[2])))
        pts = [(cx + r * math.cos(t), cy + r * math.sin(t)) for t in (i * math.pi / 8 for i in range(16))]
    if g[0] == "fp_poly":
        pts = [(float(p[1]), float(p[2])) for p in kid(g, "pts")[1:] if p[0] == "xy"]
    return pts


def bbox(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def load_catalog():
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(D34))
    spec = importlib.util.spec_from_file_location("d34_catalog_ro", D34 / "catalog.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.path.pop(0)
    return mod.K


def load_parts3d():
    """electronics/d34/parts3d.json (schema d34-parts3d/1, written by the
    electronics work): per-part bodies, solder tails, mated plugs/modules and
    lead exits in card coordinates (x right, y down, z out of the component
    side = this script's u, v, w). Returns ({card: {ref: record}}, sha, stale)."""
    path = D34 / "parts3d.json"
    if not path.exists():
        return None, None, None
    raw = json.loads(path.read_text())
    if raw.get("schema") != "d34-parts3d/1":
        print(f"WARNING: parts3d.json schema {raw.get('schema')!r} not understood; using KiCad + catalogue")
        return None, None, None
    h = hashlib.sha256()
    for card in CARDS:
        h.update((D34 / card / f"{card}.kicad_pcb").read_bytes())
    stale = h.hexdigest() != raw.get("source_pcb_sha256")
    out = {card: {p["ref"]: p for p in c["parts"]} for card, c in raw["cards"].items()}
    return out, hashlib.sha256(path.read_bytes()).hexdigest(), stale


def bbox_of(shapes):
    """Union (u0,v0,u1,v1,w0,w1) of parts3d shapes."""
    lo, hi = [1e9] * 3, [-1e9] * 3
    for sh in shapes:
        if sh["type"] == "box":
            a, b = sh["min"], sh["max"]
        else:
            (cx, cy), r = sh["centre"], sh["r"]
            a, b = [cx - r, cy - r, sh["z"][0]], [cx + r, cy + r, sh["z"][1]]
        lo = [min(lo[i], a[i]) for i in range(3)]
        hi = [max(hi[i], b[i]) for i in range(3)]
    return lo, hi


def card_model(card, K, p3d):
    pcb_path = D34 / card / f"{card}.kicad_pcb"
    design = json.loads((D34 / card / "design.json").read_text())
    kinds = {p["ref"]: p["kind"] for p in design["parts"]}
    tree = parse(pcb_path.read_text())
    edge = []
    for g in tree:
        if isinstance(g, list) and g and g[0] in ("gr_line", "gr_arc", "gr_rect") and \
                kid(g, "layer") and kid(g, "layer")[1] == "Edge.Cuts":
            edge += graphic_points(g)
    ox, oy, x1, y1 = bbox(edge)
    size = [round(x1 - ox, 3), round(y1 - oy, 3)]
    parts, conns, solder, warn = [], [], [], []
    extra = (p3d or {}).get(card, {})
    for fp in kids(tree, "footprint"):
        at = kid(fp, "at")
        ref = next(p[2] for p in kids(fp, "property") if p[1] == "Reference")
        kind = kinds.get(ref)
        if kind is None:
            warn.append(f"{card} {ref}: not in design.json, skipped")
            continue
        layers = {"F.Fab": [], "F.CrtYd": []}
        for g in fp:
            if isinstance(g, list) and g and g[0] in ("fp_line", "fp_rect", "fp_circle", "fp_arc", "fp_poly"):
                lay = kid(g, "layer")[1]
                if lay in layers:
                    layers[lay] += [xform(at, *p) for p in graphic_points(g)]
        pads = []
        for p in kids(fp, "pad"):
            pa = kid(p, "at")
            pads.append((p[1], *xform(at, float(pa[1]), float(pa[2]))))
        to_board = lambda b: [round(b[0] - ox, 3), round(b[1] - oy, 3), round(b[2] - ox, 3), round(b[3] - oy, 3)]
        crt = to_board(bbox(layers["F.CrtYd"])) if layers["F.CrtYd"] else None
        fab = to_board(bbox(layers["F.Fab"])) if layers["F.Fab"] else \
            [crt[0] + 0.25, crt[1] + 0.25, crt[2] - 0.25, crt[3] - 0.25]
        pads_b = [(n, round(x - ox, 3), round(y - oy, 3)) for n, x, y in pads]
        c = K[kind]
        h = float(c.get("h") or 2.0)
        prefix = re.match(r"[A-Z]+", ref).group(0)
        colour = COLOURS.get("CP" if kind.startswith("CP") else "LED" if kind.startswith("LED") else prefix, "Gray")
        org = (round(float(at[1]) - ox, 3), round(float(at[2]) - oy, 3))
        rot_k = round(float(at[3]) if len(at) > 3 else 0.0) % 360
        e = extra.get(ref)
        if e and (e.get("kind") != kind or round(e.get("rotation_deg", 0)) % 360 != rot_k):
            warn.append(f"{card} {ref}: parts3d kind/rotation differs from the board; KiCad + catalogue used")
            e = None
        if e:
            du, dv = org[0] - e["origin"][0], org[1] - e["origin"][1]
            if abs(du) > 1e-3 or abs(dv) > 1e-3:
                warn.append(f"{card} {ref}: parts3d re-anchored by ({du:+.2f}, {dv:+.2f}) to the current footprint")
            def mv(sh):
                sh = json.loads(json.dumps(sh))
                if sh["type"] == "box":
                    sh["min"][0] += du; sh["min"][1] += dv; sh["max"][0] += du; sh["max"][1] += dv
                else:
                    sh["centre"][0] += du; sh["centre"][1] += dv
                return sh
            bodies = [mv(x) for x in e["bodies"]]
            mated = [mv(x) for x in e["mated"]]
            for x in e["solder"]:
                lo, hi = bbox_of([mv(x)])
                solder.append([[round(lo[0], 3), round(lo[1], 3), round(hi[0], 3), round(hi[1], 3)], lo[2], hi[2]])
            pluggable = bool(c.get("pluggable"))
            for i, x in enumerate(bodies + ([] if pluggable else mated)):
                lo, hi = bbox_of([x])
                shape = "cyl" if x["type"] == "cylinder" else "box"
                tag = "" if i == 0 and len(bodies) == 1 else f"-{i}"
                parts.append([ref + tag, kind, shape, [round(lo[0], 3), round(lo[1], 3), round(hi[0], 3), round(hi[1], 3)],
                              round(lo[2], 3), round(hi[2], 3), colour if i < len(bodies) else "DarkGreen",
                              "parts3d:" + x.get("src", "?")])
            if pluggable:
                fam = c["family"]
                pl = dict(PLUG[fam])
                blo, bhi = bbox_of(bodies)
                mlo, mhi = bbox_of(mated) if mated else (blo, [bhi[0], bhi[1], pl["plug_top"]])
                le = e.get("lead_exit") or {}
                fc = le.get("face_centre") or [(mlo[0] + mhi[0]) / 2 - du, (mlo[1] + mhi[1]) / 2 - dv, mhi[2]]
                ex = [round(fc[0] + du, 3), round(fc[1] + dv, 3)]
                exit_w = round(fc[2] if len(fc) > 2 else mhi[2], 3)
                exit_dir = [round(v, 4) for v in (le.get("direction") or [0.0, 0.0, 1.0])]
                # Side-entry plugs (e.g. MSTB): parts3d lists both wire sides when the
                # orientation is open. Use the side whose cable keep-clear is free.
                cabs = [mv(x) for x in e.get("cable", [])]
                if exit_dir[2] == 0 and len(cabs) == 2:
                    others = [bbox_of([mv(x)]) for o, rec in extra.items() if o != ref
                              for x in rec["bodies"]]
                    def hits(cb):
                        lo, hi = bbox_of([cb])
                        return sum(all(lo[i] < h[1][i] and hi[i] > h[0][i] for i in range(3)) for h in others)
                    free = [cb for cb in cabs if hits(cb) == 0]
                    if free:
                        lo, hi = bbox_of([free[0]])
                        up = hi[1] <= mlo[1] + 1e-3          # cable box above the plug (-v side)
                        exit_dir = [0.0, -1.0 if up else 1.0, 0.0]
                        ex = [round((mlo[0] + mhi[0]) / 2, 3), round(mlo[1] if up else mhi[1], 3)]
                        warn.append(f"{card} {ref}: wire entry side set to {'-v (toward the clip edge)' if up else '+v'}; "
                                    "the other side's keep-clear hits card parts")
                n_pads = sorted(pads_b, key=lambda t: int(t[0]) if t[0].isdigit() else 999)
                du_, dv_ = bhi[0] - blo[0], bhi[1] - blo[1]
                conns.append(dict(ref=ref, kind=kind, family=fam, body=[round(blo[0], 3), round(blo[1], 3), round(bhi[0], 3), round(bhi[1], 3)],
                                  header_h=round(bhi[2], 3), plug_top=round(mhi[2], 3), engage=pl["engage"], straight=pl["straight"],
                                  mate_h=c.get("mate_h"), pinch="v" if dv_ <= du_ else "u", exit=ex,
                                  pins=len(pads_b), pin1=[n_pads[0][1], n_pads[0][2]],
                                  label=design["connectors"].get(ref, {}).get("label", ""),
                                  nets=design["connectors"].get(ref, {}).get("nets", []), src="parts3d",
                                  exit_w=exit_w, exit_dir=exit_dir))
            continue
        src = "kicad+catalog"
        if kind == "DEVKIT":
            px, py = [x for _, x, _ in pads_b], [y for _, _, y in pads_b]
            # Two 1x19 sockets (8.5 mm) + male pin spacer: module PCB underside ~11 mm [estimate].
            for yy in sorted({round(y, 2) for _, _, y in pads_b}):
                parts.append([f"{ref}-socket", kind, "box", [min(px) - 1.27, yy - 1.27, max(px) + 1.27, yy + 1.27], 0, 8.5, "Black", src])
            parts.append([f"{ref}-module", kind, "box", fab, 11.0, h, "DarkGreen", src])
        elif kind == "STEPSTICK":
            px, py = [x for _, x, _ in pads_b], [y for _, _, y in pads_b]
            for xx in sorted({round(x, 2) for _, x, _ in pads_b}):
                parts.append([f"{ref}-socket", kind, "box", [xx - 1.27, min(py) - 1.27, xx + 1.27, max(py) + 1.27], 0, 8.5, "Black", src])
            parts.append([f"{ref}-module", kind, "box", fab, 11.0, 13.0, "Purple", src])
            cx, cy = (fab[0] + fab[2]) / 2, (fab[1] + fab[3]) / 2
            parts.append([f"{ref}-heatsink", kind, "box", [cx - 4.5, cy - 4.5, cx + 4.5, cy + 4.5], 13.0, h, "Silver", src])
        else:
            shape = "cyl" if (kind.startswith("CP") or kind.startswith("LED")) else "box"
            parts.append([ref, kind, shape, fab, 0, h, colour, src])
        if c.get("pluggable"):
            fam = c["family"]
            pl = dict(PLUG[fam])
            body = fab
            du, dv = body[2] - body[0], body[3] - body[1]
            n_pads = sorted(pads_b, key=lambda t: int(t[0]) if t[0].isdigit() else 999)
            uc = sum(x for _, x, _ in pads_b) / len(pads_b)
            vc = sum(y for _, _, y in pads_b) / len(pads_b)
            pinch = "v" if dv <= du else "u"
            conns.append(dict(ref=ref, kind=kind, family=fam, body=body, header_h=h,
                              plug_top=pl["plug_top"], engage=pl["engage"], straight=pl["straight"],
                              mate_h=c.get("mate_h"), pinch=pinch, exit=[round(uc, 3), round(vc, 3)],
                              pins=len(pads_b), pin1=[n_pads[0][1], n_pads[0][2]],
                              label=design["connectors"].get(ref, {}).get("label", ""),
                              nets=design["connectors"].get(ref, {}).get("nets", []), src="kicad+catalog",
                              exit_w=pl["plug_top"], exit_dir=[0.0, 0.0, 1.0]))
    for ref in extra:
        if ref not in kinds:
            warn.append(f"{card} parts3d {ref}: not in design.json")
    return dict(card=card, size=size, thickness=1.6, corner_r=1.0, parts=parts, connectors=conns, solder=solder,
                kicad_sha256=hashlib.sha256(pcb_path.read_bytes()).hexdigest()), warn


def scad_value(v):
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(scad_value(x) for x in v) + "]"
    if isinstance(v, float):
        return f"{v:.4g}" if abs(v) < 1e4 else str(v)
    return str(v)


def main():
    K = load_catalog()
    p3d, p3d_sha, p3d_stale = load_parts3d()
    if p3d_stale:
        print("NOTE: parts3d.json was generated from earlier board files; parts are re-anchored to the current footprints")
    models, warnings = [], []
    for card in CARDS:
        m, w = card_model(card, K, p3d)
        models.append(m)
        warnings += w
    OUT.mkdir(parents=True, exist_ok=True)
    meta = dict(generator="scripts/gen_d34_cards.py", parts3d_sha256=p3d_sha, parts3d_stale=p3d_stale,
                kicad_sha256={m["card"]: m["kicad_sha256"] for m in models},
                plug_table="estimates (see PLUG in generator)" if not p3d else "parts3d.json where given, else estimates")
    (OUT / "d34_cards.json").write_text(json.dumps(dict(meta=meta, cards=models, warnings=warnings), indent=1) + "\n")
    lines = ["// GENERATED by scripts/gen_d34_cards.py from electronics/d34 KiCad boards. Do not edit.",
             f"// parts3d.json: {p3d_sha or 'absent (catalogue heights + estimated plug table)'}",
             "// card: [name, [length, height], thickness, parts, connectors, solder boxes]",
             "// part: [ref, kind, shape, [u0,v0,u1,v1], w0, w1, colour, source]",
             "// connector: [ref, kind, family, [u0,v0,u1,v1], header_h, plug_top, engage, pinch, [u,v] exit, pins, straight, exit w, exit dir [du,dv,dw]]"]
    cards = []
    for m in models:
        conns = [[c["ref"], c["kind"], c["family"], c["body"], c["header_h"], c["plug_top"], c["engage"],
                  c["pinch"], c["exit"], c["pins"], c["straight"], c["exit_w"], c["exit_dir"]] for c in m["connectors"]]
        cards.append([m["card"], m["size"], m["thickness"], m["parts"], conns, m["solder"]])
    lines.append("d34_card_models = " + scad_value(cards) + ";")
    (OUT / "d34_cards_data.scad").write_text("\n".join(lines) + "\n")
    for w in warnings:
        print("WARNING:", w)
    print(f"wrote {len(models)} cards, {sum(len(m['parts']) for m in models)} bodies, "
          f"{sum(len(m['connectors']) for m in models)} connectors -> cad/generated/")


if __name__ == "__main__":
    main()
