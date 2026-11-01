"""Minimal S-expression reader for KiCad netlists (.net) and boards (.kicad_pcb)."""


def tokenize(text):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in ' \t\r\n':
            i += 1
        elif c in '()':
            yield c
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n and text[j] != '"':
                if text[j] == '\\' and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                buf.append(text[j])
                j += 1
            yield ('s', ''.join(buf))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()':
                j += 1
            yield ('a', text[i:j])
            i = j


def parse(text):
    stack, cur = [], []
    for t in tokenize(text):
        if t == '(':
            stack.append(cur)
            cur = []
        elif t == ')':
            done = cur
            cur = stack.pop()
            cur.append(done)
        else:
            cur.append(t[1])
    if len(cur) != 1:
        raise ValueError('unbalanced S-expression')
    return cur[0]


def head(node):
    return node[0] if isinstance(node, list) and node and isinstance(node[0], str) else None


def children(node, name):
    return [c for c in node[1:] if isinstance(c, list) and head(c) == name]


def child(node, name):
    for c in node[1:]:
        if isinstance(c, list) and head(c) == name:
            return c
    return None


def value(node, name, default=None):
    c = child(node, name)
    if c is None or len(c) < 2:
        return default
    return c[1]
