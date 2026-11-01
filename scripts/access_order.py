#!/usr/bin/env python3
"""Choose a grip mode and unplug order per D34 card from the access diagnostic.

    bash scripts/openscad.sh ... -D 'part="access_report"' -o build/plenum/logs/access.echo
    python3 scripts/access_order.py build/plenum/logs/access.echo

For each plug and grip mode the report gives the volume its grip/approach
volume shares with fixed structure, devices, card bodies and every other
mated plug. A mode is usable when the first three are zero; another plug
that intrudes must be unplugged earlier. Prints OpenSCAD pl_unplug and
pl_grip_modes values, or the plugs that no mode and order can reach.
"""
import collections
import itertools
import re
import sys
from pathlib import Path

TOL = 0.01


def used_ports():
    """Card connectors that some harness lead uses; the rest are spare (unmated)."""
    import json
    spec = json.loads((Path(__file__).resolve().parent.parent / "cad/harness.json").read_text())
    return {e.partition(":")[2] for c in spec["cables"] for e in (c["from"], c["to"]) if e.startswith("port:d34-")}


def load(path):
    data = collections.defaultdict(lambda: collections.defaultdict(dict))
    for line in open(path):
        m = re.search(r'measure = "(\S+) (\S+) (\w+) \| (.+?)", mm3 = ([-\d.e+]+)', line)
        if m:
            card, ref, mode, what, v = m.groups()
            if f"{card}:{ref}" not in USED or (what.startswith("plug ") and f"{card}:{what[5:]}" not in USED):
                continue
            data[card][ref].setdefault(mode, {})[what] = float(v)
    return data


def solve(card, refs):
    """Per plug: modes clear of enclosure/devices (mandatory). Among those, prefer
    no card-body conflict; plug-plug conflicts become ordering constraints."""
    options, blocked = {}, []
    for ref, modes in refs.items():
        opts = []
        for mode, hits in modes.items():
            if any(hits.get(k, 0) > TOL for k in ("fixed", "devices")):
                continue
            body = hits.get("card bodies", 0)
            blockers = frozenset(w[5:] for w, v in hits.items() if w.startswith("plug ") and v > TOL)
            opts.append((body > TOL, len(blockers), mode != "pinch", mode, blockers, body))
        if not opts:
            blocked.append(ref)
        options[ref] = sorted(opts, key=lambda o: o[:3])
    free = [r for r in options if options[r]]
    # Greedy: take the plug whose best mode is blocked by the fewest still-mated
    # plugs (then: no card-body conflict, pinch first). Leftover blockers are
    # card-layout findings (two plugs too close to grip either first).
    order, done, choice, violations = [], set(blocked), {}, {}
    while len(order) < len(free):
        cands = []
        for r in free:
            if r in done:
                continue
            for o in options[r]:
                left = o[4] - done
                cands.append((len(left), o[0], o[2], r, o, left))
        n, _, _, r, o, left = min(cands)
        order.append(r); done.add(r); choice[r] = o
        if left:
            violations[r] = sorted(left)
    best = (0, order, choice, violations)
    return blocked, best


def main(path):
    """Criterion (2026-10-26): a plug is finger-removable if, in one grip mode,
    8 mm of clearance on both gripped faces, swept along the withdrawal path
    and up to the open top, is free of the enclosure, devices, other cards and
    its own card's parts, once the plugs listed before it are out. Otherwise:
    'extraction tool required' (XH/VH/fan: tweezers or an extraction tool on
    the housing; Mini-Fit: press the latch, pull by the housing)."""
    data = load(path)
    unplug, modes, rows, fail = [], [], [], 0
    for card in sorted(data):
        blocked, best = solve(card, data[card])
        for r in blocked:
            fail = 1
            rows.append((card, r, "-", "BLOCKED by enclosure/devices"))
        _, order, choice, violations = best
        unplug.append(f'["{card}",[{",".join(chr(34)+r+chr(34) for r in order)}]]')
        for i, r in enumerate(order):
            c = choice[r]
            if c[3] != "pinch":
                modes.append(f'["{card}","{r}","{c[3]}"]')
            if r in violations:
                verdict = "extraction tool required (neighbour plug " + ", ".join(violations[r]) + " in the way)"
            elif c[0]:
                verdict = f"extraction tool required (own card's parts within 8 mm, {c[5]:.0f} mm3)"
            else:
                verdict = "finger-removable (8 mm clear)"
            rows.append((card, r, f"{i + 1}. {c[3]}", verdict))
    print("Criterion: 8 mm on both gripped faces along the withdrawal path, approach from above, deck and caps off.")
    print("unplug order (card, plugs): [" + ",".join(unplug) + "]")
    print("pl_grip_modes = [" + ",".join(modes) + "];")
    params = (Path(__file__).resolve().parent.parent / "cad/parameters.scad").read_text()
    have = set(re.findall(r'\["(d34-\w+)","(J\d+)","(\w+)"\]', params))
    want = {tuple(re.findall(r'"([^"]+)"', m)) for m in modes}
    if have != want:
        print("NOTE: pl_grip_modes in cad/parameters.scad differs from this choice; the asserted "
              "check uses the parameter (copy the line above to adopt it)")
    for u in sorted(ALL - USED):
        rows.append((*u.split(":"), "-", "unused spare: no plug in this harness"))
    print("| Card | Plug | Order, grip | Result |")
    print("|---|---|---|---|")
    for row in rows:
        print("| " + " | ".join(row) + " |")
    return fail


USED = used_ports()
ALL = set()
if __name__ == "__main__":
    for line in open(sys.argv[1] if len(sys.argv) > 1 else "build/plenum/logs/access.echo"):
        m = re.search(r'measure = "(\S+) (\S+) ', line)
        if m:
            ALL.add(f"{m.group(1)}:{m.group(2)}")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "build/plenum/logs/access.echo"))
