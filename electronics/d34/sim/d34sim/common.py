"""Shared scenario helpers."""
import numpy as np

from . import system


def integ(t, y):
    return float(np.trapz(y, t)) if len(t) > 1 else 0.0


def i2t(t, i):
    return integ(t, np.asarray(i) ** 2)


def default_externals():
    """Externals used when a scenario does not care: brick at 24 V already connected at t=1 us,
    DPS idle, TEC at dT 0, thermostats closed, both fans running, motor coils present."""
    return dict(brick=dict(v=24.0, c_out=1000e-6, esr=0.03, t_close=1e-6),
                dps_in=dict(c_in=470e-6, esr=0.05, p_load=0.0),
                dps_out=dict(enable='DC 0'),
                tec=dict(dT=0.0),
                thermo=dict(),
                fans={'FAN1': dict(i_run=0.14), 'FAN2': dict(i_run=0.10, pwm_pullup_v=0.0)},
                motor=True)


def build(env, ctx, **over):
    kw = default_externals()
    kw.update(over)
    return system.build(env.cards, env.harness, ctx, **kw)


def edges(x, thr):
    """Indices where x crosses thr upward."""
    x = np.asarray(x)
    return np.nonzero((x[:-1] < thr) & (x[1:] >= thr))[0] + 1


def first_cross(t, x, thr, rising=True, after=0.0):
    x = np.asarray(x)
    m = t >= after
    idx = np.nonzero(m & ((x >= thr) if rising else (x <= thr)))[0]
    return float(t[idx[0]]) if len(idx) else float('nan')


def run_robust(make, name, vecs, analysis, chk=None, fallback_keys=('IRF4905', 'IRLZ44N', 'TL431')):
    """make(no_vendor:set) -> (circuit, info). Runs with manufacturer models; if every solver option set
    fails, rebuilds with the listed manufacturer models swapped for behavioural fits and records that."""
    from . import spice as S
    try:
        c, info = make(set())
        r = S.run(name, c.text(), vecs, analysis)
        r['_fallback'] = ''
    except S.SpiceError as e:
        c, info = make(set(fallback_keys))
        r = S.run(name, c.text(), vecs, analysis)
        r['_fallback'] = f'manufacturer model(s) {",".join(fallback_keys)} replaced by behavioural fit after convergence failure'
        if chk is not None:
            chk.note(f'{name}: {r["_fallback"]} ({str(e).splitlines()[-1][:160]})')
    if chk is not None:
        chk.models.update(c.reg.provenance)
    return c, info, r
