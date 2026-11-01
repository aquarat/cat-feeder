"""Shared generator code for the D34 hand-soldered controller boards.

Run inside the cat-feeder-kicad:local image with /usr/bin/python3 (pcbnew).
Every generated file is derived from design.py; nothing is hand-edited.
"""
import copy, hashlib, json, math, pathlib, re, uuid

ROOT = pathlib.Path(__file__).resolve().parent
KSYM = pathlib.Path('/usr/share/kicad/symbols')
KFP = pathlib.Path('/usr/share/kicad/footprints')
NS = uuid.UUID('0b8c6f4e-2f8a-4f59-9d5e-3d34c0de0d34')


def uid(*s):
    return str(uuid.uuid5(NS, '/'.join(map(str, s))))


def q(s):
    return json.dumps(str(s))


# ---------------------------------------------------------------- S-expr
def parse(s):
    toks = re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+', s)
    stack = []; root = None
    for t in toks:
        if t == '(':
            a = []
            if stack: stack[-1].append(a)
            else: root = a
            stack.append(a)
        elif t == ')': stack.pop()
        else: stack[-1].append(t)
    return root


def dump(a):
    return '(' + ' '.join(dump(x) if isinstance(x, list) else x for x in a) + ')'


def kids(a, k): return [x for x in a if isinstance(x, list) and x and x[0] == k]
def kid(a, k): return next(iter(kids(a, k)), None)
def unq(s): return json.loads(s) if s.startswith('"') else s


LIBCACHE = {}


def libsymbol(libid):
    """Copy a stock KiCad 9 symbol, flattening 'extends' (as rev A did)."""
    lib, name = libid.split(':')
    if lib not in LIBCACHE:
        LIBCACHE[lib] = {unq(s[1]): s for s in kids(parse((KSYM / (lib + '.kicad_sym')).read_text()), 'symbol')}

    def resolve(n):
        s = copy.deepcopy(LIBCACHE[lib][n]); ext = kid(s, 'extends')
        if ext:
            base = resolve(unq(ext[1])); base[1] = q(n)
            for sub in kids(base, 'symbol'):
                sub[1] = q(unq(sub[1]).replace(unq(ext[1]) + '_', n + '_', 1))
            keys = {unq(x[1]) for x in kids(s, 'property')}
            base = [x for x in base if not (isinstance(x, list) and x[0] == 'property' and unq(x[1]) in keys)]
            base.extend(kids(s, 'property')); s = base
        return s
    s = resolve(name); s[1] = q(libid); return s


# ------------------------------------------------------- custom symbols
def box_symbol(name, left, right, title=None):
    """Rectangular symbol. left/right: lists of (number, name, type) or None gaps."""
    n = max(len(left), len(right)); h = (n + 1) * 2.54
    longest = max([len(p[1]) for p in left + right if p] + [4])
    w = max(15.24, round((longest * 1.27 * 2 + 5.08) / 2.54) * 2.54)
    top = h / 2
    pins = []
    for side, plist in (('L', left), ('R', right)):
        for i, p in enumerate(plist):
            if not p: continue
            num, pname, typ = p
            y = round(top - 2.54 * (i + 1), 2)
            x = -w / 2 - 2.54 if side == 'L' else w / 2 + 2.54
            ang = 0 if side == 'L' else 180
            pins.append(f'(pin {typ} line (at {x:.2f} {y:.2f} {ang}) (length 2.54) '
                        f'(name {q(pname)} (effects (font (size 1.0 1.0)))) '
                        f'(number {q(num)} (effects (font (size 1.0 1.0)))))')
    body = (f'(symbol {q(name + "_0_1")} (rectangle (start {-w/2:.2f} {top:.2f}) (end {w/2:.2f} {-top:.2f}) '
            '(stroke (width 0.254) (type default)) (fill (type background))))')
    sym = (f'(symbol {q("d34:" + name)} (pin_names (offset 0.762)) (exclude_from_sim no) (in_bom yes) (on_board yes) '
           f'(property "Reference" "U" (at 0 {top + 2.54:.2f} 0) (effects (font (size 1.27 1.27)))) '
           f'(property "Value" {q(title or name)} (at 0 {-top - 2.54:.2f} 0) (effects (font (size 1.27 1.27)))) '
           '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes))) '
           '(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes))) '
           f'{body} (symbol {q(name + "_1_1")} {" ".join(pins)}))')
    return parse(sym)


def conn_symbol(n, label):
    """Connector symbol with functional pin names (all passive)."""
    return box_symbol(f'CONN_{label}', [(str(i + 1), nm, 'passive') for i, nm in enumerate(n)], [])


# --------------------------------------------------- custom footprints
def socket_rows_fp(name, rows, pitch, n, spacing, descr, body=None, pin1_mark=True, body_courtyard=True):
    """Two parallel female-header rows. Pad 'L<k>'/'R<k>' numbering is mapped
    by design.py; KiCad pads are numbered 1..2n: left k -> k, right k -> n+k.
    Rows run along +Y; left row at x=0, right row at x=spacing."""
    pads = []
    for side, x in (('L', 0.0), ('R', spacing)):
        for k in range(n):
            num = k + 1 if side == 'L' else n + k + 1
            shape = 'rect' if num == 1 else 'circle'
            pads.append(f'(pad "{num}" thru_hole {shape} (at {x:.3f} {k * pitch:.3f}) (size 1.7 1.7) (drill 1.0) '
                        '(layers "*.Cu" "*.Mask"))')
    L = (n - 1) * pitch
    lines = []
    def rect(layer, x1, y1, x2, y2, w):
        for a, b in [((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))]:
            lines.append(f'(fp_line (start {a[0]:.3f} {a[1]:.3f}) (end {b[0]:.3f} {b[1]:.3f}) (stroke (width {w}) (type solid)) (layer "{layer}"))')
    # Socket bodies on silkscreen, 0.15 mm (JLC minimum) lines
    for x in (0.0, spacing):
        rect('F.SilkS', x - 1.4, -1.4, x + 1.4, L + 1.4, 0.15)
    if body:
        bx1, by1, bx2, by2 = body
        rect('F.Fab', bx1, by1, bx2, by2, 0.1)
    if body and body_courtyard:
        rect('F.CrtYd', min(bx1, -1.5), min(by1, -1.5), max(bx2, spacing + 1.5), max(by2, L + 1.5), 0.05)
    elif body:
        # Module stands 11 mm above the board on its sockets: only the socket
        # strips are courtyard; low parts (< 8 mm, test-checked) may sit beneath.
        for x in (0.0, spacing):
            rect('F.CrtYd', x - 1.5, -1.5, x + 1.5, L + 1.5, 0.05)
    else:
        rect('F.CrtYd', -1.5, -1.5, spacing + 1.5, L + 1.5, 0.05)
    if pin1_mark:
        lines.append('(fp_line (start -1.9 -1.4) (end -1.9 1.4) (stroke (width 0.15) (type solid)) (layer "F.SilkS"))')
    txt = (f'(fp_text reference "REF**" (at {spacing/2:.2f} {-3:.2f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)))) '
           f'(fp_text value {q(name)} (at {spacing/2:.2f} {L/2:.2f} 90) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))')
    return (f'(footprint {q(name)} (version 20241229) (generator "d34lib") (layer "F.Cu") (descr {q(descr)}) '
            f'(attr through_hole) {txt} {" ".join(lines)} {" ".join(pads)})')


def source_digest(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode()); h.update(p.read_bytes())
    return h.hexdigest()
