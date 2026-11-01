"""ngspice batch runner and waveform reader."""
import hashlib
import os
import re
import subprocess
from pathlib import Path

import numpy as np

WORK = Path(os.environ.get('D34_SIM_WORK', '/tmp/d34sim-work'))


def version():
    try:
        out = subprocess.run(['ngspice', '-v'], capture_output=True, text=True, timeout=30).stdout
        m = re.search(r'ngspice-(\S+)', out)
        return m.group(1) if m else out.strip()[:60]
    except Exception as e:  # pragma: no cover
        return f'unknown ({e})'


class SpiceError(RuntimeError):
    pass


LADDER = ('reltol=1e-4 abstol=1e-10 vntol=1e-6 rshunt=1e9 method=trap itl4=200',
          'reltol=1e-3 abstol=1e-9 vntol=1e-5 rshunt=1e9 method=trap itl4=500',
          'reltol=1e-3 abstol=1e-9 vntol=1e-5 rshunt=1e9 method=gear maxord=2 itl4=500 gmin=1e-11')


def run(name, netlist, vectors, analysis, options=None, timeout=300):
    """Run one analysis, retrying down a ladder of solver options on convergence failure.
    Returns dict: 'time' (or sweep) + one array per requested vector, '_opts', '_hash', '_cir'."""
    errs = []
    for opts in ([options] if options else LADDER):
        try:
            r = _run(name, netlist, vectors, analysis, opts, timeout)
            r['_opts'] = opts
            r['_retries'] = len(errs)
            return r
        except SpiceError as e:
            errs.append(str(e)[:400])
    raise SpiceError(f'{name}: all solver option sets failed:\n' + '\n---\n'.join(errs))


def _run(name, netlist, vectors, analysis, options, timeout):
    WORK.mkdir(parents=True, exist_ok=True)
    cir = WORK / f'{name}.cir'
    out = WORK / f'{name}.dat'
    log = WORK / f'{name}.log'
    if out.exists():
        out.unlink()
    vec = ' '.join(vectors)
    text = (f'* {name}\n.options {options}\n'
            f'{netlist}\n.control\nset wr_singlescale\nset wr_vecnames\noption numdgt=9\n{analysis}\n'
            f'wrdata {out} {vec}\nquit\n.endc\n.end\n')
    cir.write_text(text)
    try:
        r = subprocess.run(['ngspice', '-b', '-o', str(log), str(cir)], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise SpiceError(f'{name}: ngspice timed out after {timeout} s')
    logtxt = log.read_text(errors='replace') if log.exists() else ''
    if not out.exists():
        raise SpiceError(f'{name}: ngspice produced no data (rc {r.returncode}).\n{logtxt[-1500:]}\n{r.stderr[-1000:]}')
    if 'simulation(s) aborted' in logtxt or re.search(r'(?i)timestep too small', logtxt):
        tr = re.findall(r'(?i)trouble with[^\n]*', logtxt)
        raise SpiceError(f'{name}: convergence failure: {tr[:1]}')
    lines = out.read_text().split('\n')
    head = lines[0].split()
    data = np.loadtxt(lines[1:], ndmin=2) if len(lines) > 2 else np.zeros((0, len(head)))
    if data.shape[1] != len(vectors) + 1:
        raise SpiceError(f'{name}: expected {len(vectors) + 1} columns, got {data.shape[1]} ({head[:5]}...)')
    res = {'time': data[:, 0]}
    for i, v in enumerate(vectors):
        res[v] = data[:, i + 1]
    res['_hash'] = hashlib.sha256(text.encode()).hexdigest()[:16]
    res['_cir'] = str(cir)
    return res
