"""Vectorised per-instance input schedules for the logic model."""
import numpy as np

PINS = ('en', 'wdt', 'dfr', 'thermo', 'dps', 'boot')


class Schedule:
    def __init__(self, n, init=None):
        self.n = n
        self.ev = {p: [[] for _ in range(n)] for p in PINS}
        self.init = dict(en=2, wdt=2, dfr=2, thermo=1, dps=0, boot=0)
        self.init.update(init or {})
        self.v33 = [[] for _ in range(n)]    # list of (t0, t1, v) windows; outside -> 3.3 V (v=0 window = loss)
        self.v12 = [[] for _ in range(n)]    # list of (t_loss, tau)

    def set(self, i, t, pin, val):
        self.ev[pin][i].append((t, val))

    def kicks(self, i, t0, t1, period):
        t = t0
        v = 1
        while t < t1:
            self.set(i, t, 'wdt', v)
            v = 1 - v
            t += period / 2
        self.set(i, t1, 'wdt', 0)

    def compile(self):
        self.arr = {}
        for p in PINS:
            m = max(1, max(len(e) for e in self.ev[p]))
            tt = np.full((self.n, m + 1), np.inf)
            vv = np.full((self.n, m + 1), self.init[p], dtype=np.int8)
            for i, e in enumerate(self.ev[p]):
                e = sorted(e, key=lambda x: x[0])
                for j, (t, v) in enumerate(e):
                    tt[i, j] = t
                    vv[i, j + 1] = v
            self.arr[p] = (tt, vv, np.zeros(self.n, int))
        m = max(1, max(len(w) for w in self.v33))
        self.w33 = np.full((self.n, m, 3), [np.inf, np.inf, 3.3])
        for i, w in enumerate(self.v33):
            for j, x in enumerate(w):
                self.w33[i, j] = x
        self.l12 = np.array([w[0] if w else (np.inf, 1.0) for w in self.v12])
        self.idx = np.arange(self.n)
        return self

    def __call__(self, t, s):
        out = {}
        for p, (tt, vv, ptr) in self.arr.items():
            while True:
                adv = tt[self.idx, ptr] <= t
                if not adv.any():
                    break
                ptr += adv
            out[p] = vv[self.idx, ptr]
        out['boot'] = out['boot'] == 1
        v33 = np.full(self.n, 3.3)
        for j in range(self.w33.shape[1]):
            t0, t1, v = self.w33[:, j, 0], self.w33[:, j, 1], self.w33[:, j, 2]
            inw = (t >= t0) & (t < t1)
            # a loss window decays exponentially (tau = 30 ms caps on the 3V3 rail) toward the window value
            v33 = np.where(inw, np.maximum(v, 3.3 * np.exp(-(t - t0) / 0.03)), v33)
        out['v33'] = v33
        tl, tau = self.l12[:, 0], self.l12[:, 1]
        out['v12'] = np.where(t >= tl, 12.0 * np.exp(-(t - tl) / tau), 12.0)
        return out
