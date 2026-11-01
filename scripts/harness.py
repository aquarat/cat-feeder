#!/usr/bin/env python3
"""Plenum harness: resolve, bend, check and cut-list every lead.

    python3 scripts/harness.py            # runs OpenSCAD for ports, writes outputs
    python3 scripts/harness.py --cached   # reuse build/plenum/logs/ports.echo

Inputs:  cad/harness.json (cables, waypoints, inline bodies, policies)
         ports + geometry echoed by part="harness_ports" (cad/feeder.scad, plenum mode)
         cad/generated/d34_cards.json (plug straight-exit lengths, engagement)
Outputs: cad/generated/harness_routes.scad   centrelines for the solid checks/views
         build/plenum/harness/report.json      every check, per cable
         build/plenum/harness/cutlist.csv|.md  lengths, conductors, connectors
Exit status 1 if any check fails.

What is checked here (analytic, on the filleted centreline):
  bend radius >= policy x bundle diameter (by construction; a corner that
  cannot fit its fillet fails), straight lead-out at every plug, hot-sink
  clearance, fan-blade plane clearance, rotating-part clearance, hot leads
  below the deck underside, cold leads only inside their deck bores, wire
  height above basins and away from drain drip paths, floor clearance, and
  the fill of each baffle slot. Solid interference with every modelled part
  is checked in OpenSCAD (plenum_checks, "harness / ..."). Lengths are model
  lengths, not measurements of a built loom.
"""
import csv
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build/plenum/harness"
ECHO = ROOT / "build/plenum/logs/ports.echo"
DEBUG = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--debug=")]
DEBUG = DEBUG[0].split(",") if DEBUG else []

# Conductor outside diameters (mm) by insulation and AWG: typical UL1007 PVC and
# high-strand silicone hook-up wire [catalogue-class estimates].
# pvc = UL1007 (300 V), pvc_thin = UL1061 thin-wall (300 V, 80 °C) for signal leads.
WIRE_OD = {"pvc": {26: 1.3, 24: 1.4, 22: 1.6, 20: 1.9, 18: 2.3},
           "pvc_thin": {28: 0.85, 26: 0.95, 24: 1.05, 22: 1.2, 20: 1.4},
           "silicone": {26: 1.4, 24: 1.5, 22: 1.7, 20: 2.0, 18: 2.5}}
# Equal circles in a circle: enclosing diameter / circle diameter, plus 10 % looseness.
PACK = {1: 1.0, 2: 2.0, 3: 2.155, 4: 2.414, 5: 2.701, 6: 3.0, 7: 3.0, 8: 3.305,
        9: 3.613, 10: 3.813, 11: 3.923, 12: 4.029}
BEND = {"pvc": 4.0, "pvc_thin": 4.0, "silicone": 3.0, "sheathed": 4.0}   # minimum bend radius / diameter
AREA_FILL_MAX = 0.55      # slot fill: sum of bundle circle areas / free slot area


def v_add(a, b): return [a[i] + b[i] for i in range(3)]
def v_sub(a, b): return [a[i] - b[i] for i in range(3)]
def v_mul(a, k): return [a[i] * k for i in range(3)]
def v_dot(a, b): return sum(a[i] * b[i] for i in range(3))
def v_len(a): return math.sqrt(v_dot(a, a))
def v_unit(a):
    n = v_len(a)
    return [x / n for x in a]


def rot(a_deg, p):
    a = math.radians(a_deg)
    return [p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a), p[2]]


def run_scad():
    ECHO.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["bash", "scripts/openscad.sh", "--backend=Manifold", "-D", 'cooling_concept="plenum"',
           "-D", 'part="harness_ports"', "-o", str(ECHO.relative_to(ROOT)), "cad/feeder.scad"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if out.returncode or "ERROR" in out.stdout + out.stderr or "ERROR" in ECHO.read_text() \
            or "undef" in ECHO.read_text():
        sys.exit("OpenSCAD port export failed:\n" + out.stdout + out.stderr)


def scad_json(text):
    return json.loads(text.replace("undef", "null").replace("true", "true"))


def load_ports():
    ports, hp = {}, {}
    for line in ECHO.read_text().splitlines():
        m = re.match(r"ECHO: port = (.*)$", line)
        if m:
            n, p, d = scad_json(m.group(1))
            ports[n] = dict(pos=p, dir=v_unit(d))
        m = re.match(r"ECHO: hparams = (.*)$", line)
        if m:
            hp = {k: v for k, v in scad_json(m.group(1))}
    return ports, hp


# ------------------------------------------------------------------ cables
def wire_od(c):
    if c.get("od"):
        return c["od"]
    return WIRE_OD[c["insulation"]][c["awg"]]


def bundle_d(c):
    if c.get("sheath_od"):
        return c["sheath_od"]
    n = c["conductors"]
    return round(wire_od(c) * PACK[n] * (1.0 if n == 1 else 1.1), 2)


def bend_r(c, d):
    """Policy: factor x bundle diameter. "loose": wires are not tied through the
    bends (separate twisted conductors), so the factor applies per wire."""
    if c.get("min_bend"):
        return c["min_bend"]
    kind = "sheathed" if c.get("sheath_od") else c["insulation"]
    return BEND[kind] * (wire_od(c) if c.get("loose") else d)


class Ctx:
    def __init__(self, spec, ports, hp, cards):
        self.spec, self.ports, self.hp = spec, ports, hp
        self.junctions = {}
        self.inline = {}
        self.straight = {}
        for card in cards["cards"]:
            for k in card["connectors"]:
                self.straight[f'{card["card"]}:{k["ref"]}'] = dict(straight=k["straight"], engage=k["engage"],
                                                                   family=k["family"], pins=k["pins"])
        for name, j in spec.get("junctions", {}).items():
            self.junctions[name] = self.point(j)
        for b in spec.get("inline", []):
            a, c = self.point(b["a"]), self.point(b["b"])
            self.inline[b["name"]] = dict(a=a, b=c, d=b["d"], desc=b.get("desc", ""))

    def point(self, p):
        """[angle, x, y, z] in a frame rotated by angle, or {"rel": ref, "f": angle, "off": [..]}."""
        if isinstance(p, list):
            return rot(p[0], p[1:4])
        base = self.endpoint(p["rel"])[0]
        return v_add(base, rot(p.get("f", 0), p.get("off", [0, 0, 0])))

    def endpoint(self, ref):
        """(position, leaving direction or None, straight length)."""
        kind, _, name = ref.partition(":")
        if kind == "port":
            pt = self.ports[name]
            s = self.straight.get(name, {}).get("straight", self.spec["device_straight"].get(name, 3.0))
            return pt["pos"], pt["dir"], s
        if kind == "junction":
            return self.junctions[name], None, 0.0
        if kind == "inline":
            nm, _, end = name.rpartition(":")
            b = self.inline[nm]
            p, q = (b["a"], b["b"]) if end == "a" else (b["b"], b["a"])
            return p, v_unit(v_sub(p, q)), 2.0
        raise KeyError(ref)


def lead_in(p0, d, s, nxt, R):
    """Corner on the exit axis so the fillet starts >= s from the port. None when
    the next waypoint already lies on the axis (it is then the first corner)."""
    w = v_sub(nxt, p0)
    proj = v_dot(w, d)
    perp = v_len(v_sub(w, v_mul(d, proj)))
    if proj > 0 and perp <= 0.1 * proj:
        return None
    L = s + R
    for _ in range(40):
        v = v_add(p0, v_mul(d, L))
        u = v_sub(nxt, v)
        if v_len(u) < 1e-6:
            break
        phi = math.acos(max(-1, min(1, v_dot(d, v_unit(u)))))
        L_new = s + R * math.tan(min(phi, math.radians(150)) / 2)
        if abs(L_new - L) < 0.01:
            break
        L = 0.5 * (L + L_new)
    return v_add(p0, v_mul(d, L))


def fillet(points, R, step=3.0, s0=0.0, s1=0.0):
    """Sample a polyline with circular fillets at every corner. Each corner gets
    radius R unless its neighbours leave too little room; then the largest radius
    that fits is drawn and reported. s0/s1: straight lead-out required at the
    first/last point. Returns (samples, length, problems, min radius drawn)."""
    n = len(points)
    phis = [0.0] * n
    want = [0.0] * n
    probs = []
    for i in range(1, n - 1):
        u = v_unit(v_sub(points[i], points[i - 1]))
        w = v_unit(v_sub(points[i + 1], points[i]))
        phi = math.acos(max(-1, min(1, v_dot(u, w))))
        phis[i] = phi
        want[i] = R * math.tan(phi / 2) if phi > 1e-4 else 0.0
        if phi > math.radians(170):
            probs.append(f"near-reversal ({math.degrees(phi):.0f} deg) at vertex {i}")
    seg = [v_len(v_sub(points[i + 1], points[i])) for i in range(n - 1)]
    tang = list(want)
    for j in range(n - 1):
        fixed = (s0 if j == 0 else 0.0) + (s1 if j == n - 2 else 0.0)
        need = want[j] * (j > 0) + want[j + 1] * (j + 1 < n - 1)
        room = seg[j] - fixed
        if need > room + 1e-6:
            k = max(room, 0.0) / need if need else 0.0
            if j > 0:
                tang[j] = min(tang[j], want[j] * k)
            if j + 1 < n - 1:
                tang[j + 1] = min(tang[j + 1], want[j + 1] * k)
    rmin = R
    for i in range(1, n - 1):
        if phis[i] > 1e-4 and tang[i] < want[i] - 1e-6:
            r_i = tang[i] / math.tan(phis[i] / 2)
            rmin = min(rmin, r_i)
            if r_i < 0.995 * R:
                probs.append(f"bend at vertex {i} ({math.degrees(phis[i]):.0f} deg) only fits R{r_i:.1f} < R{R:.1f}")
    out, length = [points[0]], 0.0
    prev = points[0]
    for i in range(1, n):
        if i < n - 1 and tang[i] > 1e-6:
            u = v_unit(v_sub(points[i], points[i - 1]))
            w = v_unit(v_sub(points[i + 1], points[i]))
            r_i = tang[i] / math.tan(phis[i] / 2)
            a = v_sub(points[i], v_mul(u, tang[i]))
            b = v_add(points[i], v_mul(w, tang[i]))
            length += v_len(v_sub(a, prev))
            out.append(a)
            bis = v_unit(v_sub(w, u))
            c = v_add(points[i], v_mul(bis, r_i / math.cos(phis[i] / 2)))
            ra, rb = v_sub(a, c), v_sub(b, c)
            k = max(2, int(math.ceil(r_i * phis[i] / step)))
            for j in range(1, k):
                t = j / k
                s0_ = math.sin((1 - t) * phis[i]) / math.sin(phis[i])
                s1_ = math.sin(t * phis[i]) / math.sin(phis[i])
                out.append(v_add(c, v_add(v_mul(ra, s0_), v_mul(rb, s1_))))
            out.append(b)
            length += r_i * phis[i]
            prev = b
        else:
            length += v_len(v_sub(points[i], prev))
            out.append(points[i])
            prev = points[i]
    return out, length, probs, rmin


def densify(samples, step=2.0):
    pts = [samples[0]]
    for a, b in zip(samples, samples[1:]):
        L = v_len(v_sub(b, a))
        k = max(1, int(math.ceil(L / step)))
        pts += [v_add(a, v_mul(v_sub(b, a), j / k)) for j in range(1, k + 1)]
    return pts


# ------------------------------------------------------------------ hazards
def box_dist(p, frame_angle, lo, hi):
    q = rot(-frame_angle, p)
    d = [max(lo[i] - q[i], 0, q[i] - hi[i]) for i in range(3)]
    return v_len(d)


def hazards_for(hp):
    hs = []
    hz = hp["hot_sink"]
    for a in hp["sites"]:
        lo = [hp["site_r"] - hz[0] / 2, -hz[1] / 2, hp["hot_top"] - hz[2]]
        hi = [hp["site_r"] + hz[0] / 2, hz[1] / 2, hp["hot_top"]]
        hs.append((f"hot sink {a}", a, lo, hi))
    return hs


def solids_for(hp, cards):
    """Approximate oriented boxes for the optimizer and an analytic pre-check:
    baffles (legs, web, slot), motor posts, bridge, hall post, motor, fan, DPS
    and every generated D34 part and mated plug. OpenSCAD checks the real solids."""
    out = []
    bx, bt, half, z_arm, z_top, bend = hp["baffle"]
    z_slot, z_arm0 = hp["slot_lower"]
    fl = hp["floor_z"]
    fz, fh, fw = hp["fan"]
    for a in hp["post_angles"]:
        x0, x1 = bx - bt / 2, bx + bt / 2
        for sg in (1, -1):
            lo_hi = [(12, bend), (half, 12)]
            out.append((f"baffle {a}", a, [x0, min(sg * 12, sg * bend), fl], [x1, max(sg * 12, sg * bend), z_top]))
            out.append((f"baffle {a}", a, [x0, min(sg * half, sg * 12), fz + fh + 1], [x1, max(sg * half, sg * 12), z_top]))
        out.append((f"baffle {a}", a, [x0, -half, fz + fh + 1], [x1, half, z_slot]))
        out.append((f"motor post {a}", a, [86.5, -4, fl], [91.5, 4, z_arm0 + 3]))
        out.append((f"bridge arm {a}", a, [20, -5, z_arm0], [91.5, 5, z_arm]))
    out.append(("bridge plate", 0, [-23.5, -23.5, z_arm0], [23.5, 23.5, z_arm0 + 6.8]))
    out.append(("hall post", 45, [34, -3, z_arm0], [41.5, 3, 106.4]))
    m0, m1 = hp["motor"]
    out.append(("motor", 0, [-21, -21, m0], [21, 21, m1]))
    out.append(("fan", 0, [-fw / 2, -fw / 2, fz], [fw / 2, fw / 2, fz + fh]))
    out.append(("DPS5005", 135, [94.5, -39.5, 29.5], [135.5, 39.5, 72.5]))
    cin, ctop, clen = hp["card"]
    angles = {c[0]: c[1] for c in hp["cards"]}
    for card in cards["cards"]:
        a = angles[card["card"]]
        out.append((f"{card['card']} board+posts", a, [cin, -clen / 2 - 4.8, fl], [cin + 4.1, clen / 2 + 4.8, ctop + 8.5]))
        boxes = [(p[0], p[3], p[4], p[5]) for p in card["parts"]]
        boxes += [(k["ref"] + " plug", k["body"], k["header_h"], k["plug_top"]) for k in card["connectors"]]
        for ref, b, w0, w1 in boxes:
            out.append((f"{card['card']} {ref}", a, [cin - w1, clen / 2 - b[2], ctop - b[3]],
                        [cin - w0, clen / 2 - b[0], ctop - b[1]]))
    return out


def check_cable(c, pts, d, hp, sinks, detail=False, solids=(), ends=()):
    """Analytic zone checks on densified centreline points. Returns a list of
    failure messages, or (detail=True) the clearance deficits in mm."""
    r = d / 2
    fails = []
    zone = c.get("zone", "hot")
    hot_margin = c.get("hot_margin", 3.0)
    fan_z, fan_h, fan_w = hp["fan"]
    floor = hp["floor_z"]
    bt = hp["basin"]
    drain_r, _, tube_z0 = hp["drain"]
    deck_z, deck_top = hp["deck_z"], hp["deck_top"]
    bores = [hp["blower_bore"][:2]] + hp["probe_bores"]
    worst = {}
    deficits = []

    def note(key, val, limit, msg):
        if val < limit - 1e-6:
            deficits.append(limit - val)
            if key not in worst or val < worst[key][0]:
                worst[key] = (val, msg)

    for p in pts:
        rr = math.hypot(p[0], p[1])
        # Approximate solids (skip the stretch leaving each end's own plug/device).
        if all(v_len(v_sub(p, e)) > r + 4 for e in ends):
            for name, a, lo, hi in solids:
                note("solid " + name, box_dist(p, a, lo, hi) - r, 0.3, f"near {name}")
        ang = math.degrees(math.atan2(p[1], p[0])) % 360
        # Hot-sink fins: keep the margin unless the lead is rated for the sink (TEC/thermostat).
        for name, a, lo, hi in sinks:
            note("hot sink", box_dist(p, a, lo, hi) - r, hot_margin, f"{name}")
        # Fan blades: open top face of the hot-side fan (no guard).
        # Fan blades (open top face, no guard): swept circle ~Ø115 under the bridge.
        if rr < fan_w / 2 - 2 + r + 3:
            note("fan", p[2] - r - (fan_z + fan_h), 3.0, "above the fan blades")
        # Rotating drive/hub/tray: everything above the drive inside the inner wall.
        if rr < hp["inner_wall"][1] + 1:
            note("rotating", hp["drive_z"] - 1 - (p[2] + r), 3.0, "below the drive/hub")
        # Floor: wires stay off the floor (spills, cleaning).
        note("floor", p[2] - r - floor, 3.0, "above the floor")
        # Basins and drip paths: wires above the water and away from the drips.
        for a in hp["sites"]:
            da = abs((ang - a + 180) % 360 - 180)
            if not c.get("basin_exempt") and bt[0] - 5 - r < rr < bt[1] + 5 + r and da < bt[2] + 3:
                note("basin", p[2] - r - (floor + bt[3]), 5.0, f"above basin {a}")
            dx, dy = p[0] - drain_r * math.cos(math.radians(a)), p[1] - drain_r * math.sin(math.radians(a))
            if p[2] < tube_z0 + 5:
                note("drip", math.hypot(dx, dy) - r, 6.0, f"drip path under drain {a}")
        # Hot leads stay below the deck; cold leads cross only inside a sealed bore.
        if zone == "hot":
            # Hot leads stay under the deck, except in the open drive bore (hall lead)
            # or a TEC pigtail in its deck-underside groove.
            if not c.get("deck_groove") and rr + r > hp["drive_bore_r"] - 1:
                note("deck", deck_z - 0.5 - (p[2] + r), 0.0, "below the deck underside")
        else:
            if deck_z - 0.5 < p[2] + r and p[2] - r < deck_top - 3:   # above: the blower lead slot
                inside = min(math.hypot(p[0] - b[0], p[1] - b[1]) for b in bores)
                note("bore", 0.5 - inside, 0.0, "inside its sealed deck bore")
    if detail:
        return deficits
    for key, (val, msg) in worst.items():
        fails.append(f"{key}: {msg}, clearance {val:.1f} mm")
    return fails


def slot_crossings(samples, d, hp):
    """Bundles crossing each baffle plane inside the slot rectangle."""
    bx, bt, half, z_arm, z_top, _ = hp["baffle"]
    out = []
    for a in hp["post_angles"]:
        q = [rot(-a, p) for p in samples]
        for p0, p1 in zip(q, q[1:]):
            if (p0[0] - bx) * (p1[0] - bx) < 0 and abs(p0[1]) < 40 and abs(p1[1]) < 40:
                t = (bx - p0[0]) / (p1[0] - p0[0])
                y = p0[1] + t * (p1[1] - p0[1])
                z = p0[2] + t * (p1[2] - p0[2])
                out.append(dict(slot=a, y=round(y, 1), z=round(z, 1), d=d,
                                level="upper" if z > z_arm else "lower"))
    return out


# ------------------------------------------------------------------ main
def main(argv):
    if "--cached" not in argv:
        run_scad()
    ports, hp = load_ports()
    spec = json.loads((ROOT / "cad/harness.json").read_text())
    cards = json.loads((ROOT / "cad/generated/d34_cards.json").read_text())
    ctx = Ctx(spec, ports, hp, cards)
    sinks = hazards_for(hp)
    solids = solids_for(hp, cards)
    routes, report, rows, fail = [], dict(cables={}, slots={}, inline={}), [], False
    all_cross = []
    resolved = {}
    for c in spec["cables"]:
        d = bundle_d(c)
        R = bend_r(c, d)
        p0, d0, s0 = ctx.endpoint(c["from"])
        p1, d1, s1 = ctx.endpoint(c["to"])
        # Only the solids near this cable's extent matter (speed).
        ext = [p0, p1] + [ctx.point([v["slot"], 97, v["y"], v["z"]]) for v in c.get("via", []) if isinstance(v, dict) and "slot" in v] \
            + [ctx.point(v["p"] if isinstance(v, dict) else v) for v in c.get("via", []) if not (isinstance(v, dict) and "slot" in v)]
        lo_ = [min(q[i] for q in ext) - 30 for i in range(3)]
        hi_ = [max(q[i] for q in ext) + 30 for i in range(3)]
        near = []
        for sd in solids:
            corners = [rot(sd[1], [x, y, z]) for x in (sd[2][0], sd[3][0]) for y in (sd[2][1], sd[3][1])
                       for z in (sd[2][2], sd[3][2])]
            if all(max(q[i] for q in corners) >= lo_[i] and min(q[i] for q in corners) <= hi_[i] for i in range(3)):
                near.append(sd)
        # Expand slot crossings: {"slot": a, "y":, "z":, "dir": "in"|"out", "bay": x}
        # -> a straight lane perpendicular to the baffle, bay side to centre side.
        vias_in = []
        for v in c.get("via", []):
            if isinstance(v, dict) and "slot" in v:
                bay_x = v.get("bay", 97)
                pair = [[v["slot"], bay_x, v["y"], v["z"]], [v["slot"], v.get("centre", 66), v["y"], v["z"]]]
                vias_in += [{"p": q, "fix": True} for q in (pair if v["dir"] == "in" else pair[::-1])]
            else:
                vias_in.append(v)
        c = dict(c, via=vias_in)
        via, free = [], []
        for v in c.get("via", []):
            fixed = isinstance(v, dict) and v.get("fix")
            if isinstance(v, dict) and "p" in v:
                v = v["p"]
            q = ctx.point(v)
            via.append(q)
            fixed = fixed or (isinstance(v, list) and v[0] in hp["post_angles"] and 74 <= v[1] <= 84)
            free.append(0.0 if fixed else c.get("tol", 6.0))

        def build(vs):
            pts = [p0]
            if d0:
                q = lead_in(p0, d0, s0, vs[0] if vs else p1, R)
                if q:
                    pts.append(q)
            pts += vs
            tail = []
            if d1:
                q = lead_in(p1, d1, s1, vs[-1] if vs else pts[-1], R)
                if q:
                    tail.append(q)
            pts += tail + [p1]
            samples, length, probs, rmin = fillet(pts, R, s0=s0 if d0 else 0, s1=s1 if d1 else 0)
            for end, d_, q in ((0, d0, pts[1]), (-1, d1, pts[-2])):
                if d_:
                    ang = math.degrees(math.acos(max(-1, min(1, v_dot(d_, v_unit(v_sub(q, pts[end])))))))
                    if ang > 10:
                        probs.append(f"lead-out at {'start' if end == 0 else 'end'} leaves {ang:.0f} deg off the plug axis")
            return pts, samples, length, probs, rmin

        def cost(vs):
            pts, samples, length, probs, rmin = build(vs)
            pen = 0.0
            # bend deficits
            n = len(pts)
            for i in range(1, n - 1):
                pass
            pen += 50 * max(0.0, R - rmin) ** 2 + 20 * sum("near-reversal" in p or "lead-out" in p for p in probs)
            fails = check_cable(c, densify(samples)[1:-1], d, hp, sinks, detail=True, solids=near, ends=(p0, p1))
            pen += 50 * sum(x * x for x in fails)
            return pen + 0.002 * length

        # Deterministic coordinate descent on the free waypoints.
        best = cost(via)
        step = 2.0
        while step > 0.2 and best > 0.002 * 1e4 * 0 + 1e-9 and any(free):
            improved = False
            for i, tol in enumerate(free):
                if not tol:
                    continue
                v_ = c["via"][i]
                orig = ctx.point(v_["p"] if isinstance(v_, dict) and "p" in v_ else v_)
                for ax in range(3):
                    for sgn in (1, -1):
                        trial = [list(v) for v in via]
                        trial[i][ax] += sgn * step
                        if abs(trial[i][ax] - orig[ax]) > tol:
                            continue
                        cst = cost(trial)
                        if cst < best - 1e-6:
                            best, via, improved = cst, trial, True
            if not improved:
                step /= 2
        resolved[c["id"]] = [[round(x, 2) for x in v] for v in via]
        if DEBUG and c["id"] in DEBUG:
            pts_, samples_, *_ = build(via)
            def loc(q):
                a = min(hp["post_angles"], key=lambda b: abs(((math.degrees(math.atan2(q[1], q[0])) - b + 180) % 360) - 180))
                l = rot(-a, q)
                return f"[{a}: {l[0]:6.1f} {l[1]:6.1f} {l[2]:5.1f}]"
            print(c["id"], "points:", " ".join(loc(q) for q in pts_))
            for q in densify(samples_)[1:-1]:
                for name, a, lo, hi in near:
                    dd = box_dist(q, a, lo, hi) - d / 2
                    if dd < 0.3 and all(v_len(v_sub(q, e)) > d / 2 + 4 for e in (p0, p1)):
                        print("   ", name, round(dd, 2), loc(q))
        pts, samples, length, probs, rmin = build(via)
        dense = densify(samples)
        fails = probs + check_cable(c, dense[1:-1], d, hp, sinks, solids=near, ends=(p0, p1))
        if c.get("max_route") and length > c["max_route"]:
            fails.append(f"route {length:.0f} mm exceeds the available {c['max_route']} mm")
        cross = slot_crossings(samples, d, hp)
        for x in cross:
            x["cable"] = c["id"]
        all_cross += cross
        # Slack and cut length.
        ends = [c["from"], c["to"]]
        slack = 0.0
        notes = []
        for e in ends:
            name = e.partition(":")[2]
            if name in ctx.straight:
                slack += ctx.straight[name]["engage"] + 15
        slack += c.get("service_slack", 0)
        slack += 0.03 * length
        extra = c.get("extra_length", 0)
        term = 10 * sum(1 for e in ends if not e.startswith("junction")) + c.get("termination", 0)
        cut = int(math.ceil((length + extra + slack + term) / 5.0) * 5)
        # Trim the drawn tube clear of the plug/device faces at directed ends.
        draw = list(samples)
        trim = d / 2 + 0.3
        if d0:
            draw = [v_add(p0, v_mul(d0, trim))] + [q for q in draw[1:] if v_len(v_sub(q, p0)) > trim + 0.05]
        if d1:
            draw = [q for q in draw[:-1] if v_len(v_sub(q, p1)) > trim + 0.05] + [v_add(p1, v_mul(d1, trim))]
        routes.append([c["id"], c.get("colour", "Gray"), d, c.get("zone", "hot"),
                       [[round(x, 2) for x in p] for p in draw]])
        ok = not fails
        fail |= not ok
        report["cables"][c["id"]] = dict(name=c["name"], ok=ok, failures=fails, bundle_d=d, bend_r=R, min_bend_drawn=round(rmin, 2),
                                         route_mm=round(length, 1), extra_mm=extra, slack_mm=round(slack, 1),
                                         cut_mm=cut, slots=cross, waypoints=len(pts))
        rows.append(dict(id=c["id"], name=c["name"], from_=c["from_desc"], to=c["to_desc"],
                         conductors=c["conductors"] if not c.get("sheath_od") else c.get("cores", c["conductors"]),
                         awg=c.get("awg", ""), insulation=("sheathed " if c.get("sheath_od") else "") + c.get("insulation", ""),
                         colours="/".join(c.get("colours", [])), bundle_d=d, bend_r=round(R, 1),
                         route=round(length), slack=round(slack), extra=extra, cut=cut,
                         service=c.get("service", ""), note=c.get("note", "")))
    # Pre-crimped / device lead lengths against the cut lengths (sourcing check).
    cuts = {cid: r["cut_mm"] for cid, r in report["cables"].items()}
    for row in rows:
        c = next(x for x in spec["cables"] if x["id"] == row["id"])
        pc = c.get("precrimp")
        if not pc:
            row["precrimp"], row["pc_status"] = "", ""
            continue
        need = cuts[c["id"]] + sum(cuts[w] - 10 for w in pc.get("with_", []))
        if pc["mode"] == "none" or not pc["len"]:
            status = "made to length (no pre-crimped lead)"
        elif need <= pc["len"]:
            status = f"OK: {need} of {pc['len']} mm"
        elif pc["mode"] == "both":
            status = f"TOO SHORT: needs {need} mm > {pc['len']} mm: custom length (or crimp loose contacts)"
        else:
            status = f"EXTEND: needs {need} mm > {pc['len']} mm: solder + heat-shrink {need - pc['len']} mm extension"
        row["precrimp"], row["pc_status"] = f"[{pc.get('source', '')}] {pc['part']}", status
        report["cables"][c["id"]]["precrimp"] = dict(part=pc["part"], source=pc.get("source", ""), length=pc["len"],
                                                     needed=need, status=status)
    # Slot fill.
    bx, bt, half, z_arm, z_top, _ = hp["baffle"]
    z_bot, z_arm_bot = hp["slot_lower"]
    for a in hp["post_angles"]:
        xs = [x for x in all_cross if x["slot"] == a]
        area = sum(math.pi * x["d"] ** 2 / 4 for x in xs)
        # Free slot area: above the arm, plus below it; the arm (10 mm) and the
        # post line (8 mm) are not available below the arm.
        free = 2 * half * (z_top - z_arm) + (2 * half - 8) * max(0.0, z_arm_bot - z_bot)
        fill = area / free if free else 0
        report["slots"][str(a)] = dict(cables=[x["cable"] for x in xs], bundle_area_mm2=round(area, 1),
                                       free_area_mm2=round(free, 1), fill=round(fill, 3), ok=fill <= AREA_FILL_MAX,
                                       open_area_mm2=round(free - area, 1))
        fail |= fill > AREA_FILL_MAX
    for name, b in ctx.inline.items():
        report["inline"][name] = dict(a=b["a"], b=b["b"], d=b["d"], desc=b["desc"])
    # Outputs.
    out = ROOT / "cad/generated/harness_routes.scad"
    lines = ["// GENERATED by scripts/harness.py from cad/harness.json. Do not edit.",
             "// [id, colour, bundle dia, zone, filleted centreline]",
             "harness_routes = " + json.dumps(routes) + ";",
             "// [name, end a, end b, dia]",
             "// card connectors used by a lead; others are modelled unmated (spare)",
             "harness_used_ports = " + json.dumps(sorted({e.partition(":")[2] for c in spec["cables"]
                                                          for e in (c["from"], c["to"]) if e.startswith("port:d34-")})) + ";",
             "harness_inline = " + json.dumps([[n, [round(x, 2) for x in b["a"]], [round(x, 2) for x in b["b"]], b["d"]]
                                               for n, b in ctx.inline.items()]) + ";"]
    out.write_text("\n".join(lines) + "\n")
    BUILD.mkdir(parents=True, exist_ok=True)
    report["policy"] = dict(wire_od=WIRE_OD, bend_factor=BEND, slot_fill_max=AREA_FILL_MAX,
                            slack="plug ends: engagement + 15 mm each; +3 % of route; service loops per cable; "
                                  "10 mm termination per terminated end")
    report["resolved_via"] = resolved
    (BUILD / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    cols = ["id", "name", "from_", "to", "conductors", "awg", "insulation", "colours", "bundle_d", "bend_r",
            "route", "slack", "extra", "cut", "precrimp", "pc_status", "service", "note"]
    with (BUILD / "cutlist.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    md = ["| Lead | From | To | Cond. | Wire | Bundle Ø | Bend R | Route | Slack | Cut | Pre-crimped source | Length check | Service |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['id']} {r['name']} | {r['from_']} | {r['to']} | {r['conductors']} | "
                  f"{r['awg']} AWG {r['insulation']} {r['colours']} | {r['bundle_d']} | {r['bend_r']} | "
                  f"{r['route']} | {r['slack']} | **{r['cut']}** | {r['precrimp']} | {r['pc_status']} | {r['service']} |")
    (BUILD / "cutlist.md").write_text("\n".join(md) + "\n")
    # Tracked copy for the BOM (build/ is not in git).
    (ROOT / "cad/generated/harness_cutlist.md").write_text(
        "<!-- GENERATED by scripts/harness.py from cad/harness.json. Do not edit. -->\n" + "\n".join(md) + "\n")
    # Console summary.
    for cid, r in report["cables"].items():
        status = "ok  " if r["ok"] else "FAIL"
        print(f"{status} {cid:5s} {r['name'][:38]:38s} D{r['bundle_d']:4.1f} R{r['bend_r']:5.1f} "
              f"route {r['route_mm']:6.1f} cut {r['cut_mm']:4d}")
        for f in r["failures"]:
            print("       -", f)
    for a, s in report["slots"].items():
        print(f"{'ok  ' if s['ok'] else 'FAIL'} slot {a:>3s}: {len(s['cables'])} bundles, "
              f"{s['bundle_area_mm2']} / {s['free_area_mm2']} mm2 = {s['fill']:.2f}")
    for r in rows:
        if r.get("pc_status") and not r["pc_status"].startswith(("OK", "made")):
            print(f"LENGTH {r['id']:5s} {r['pc_status']}")
    print("wrote cad/generated/{harness_routes.scad,harness_cutlist.md}, build/plenum/harness/{report.json,cutlist.csv,cutlist.md}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
