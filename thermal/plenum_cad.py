#!/usr/bin/env python3
"""D35 plenum re-run on the CAD study geometry, with hot- and cold-sink models.

Screening study, 2026-10-26. The 2026-10-25 run (plenum.py) assumed a 12 x 80 mm
channel and three modules; the CAD study (kb/plenum-cad.md) has 15 x 77.5 mm and
four sites with 70 x 70 x 45 mm hot-sink envelopes. This script reuses plenum.py
unchanged and adds:
  1. plate-fin sink model (Teertstra developing-flow Nu, fin efficiency, NTU
     referenced to inlet air, Song-Lee-Au base spreading, paste interfaces);
  2. fan/blower operating points from linear datasheet curves against estimated
     system resistance (sinks in parallel with a bypass, intake and vents);
  3. heat balance, food temperatures and TEC operating points per layout.
  4. (2026-10-26) the stocked trial sinks and cut-to-length candidates from drawings,
     explicit cold-side bypass slots, a current-capped (I_CAP) coldest-air check, and
     open-exposure/pull-down for each as-sourced layout.
Every number is an estimate or simulation; nothing here is measured.
See kb/plenum-sizing.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass, replace as dc_replace
from pathlib import Path

import plenum as P
from model import write_csv

K0 = P.K0
K_AL = 200.0            # W/mK, 6063-T5 extrusion (catalogue class)
R_PASTE = 1.5e-5        # m2K/W per pasted interface (0.15 K cm2/W, mid-range estimate)
SHELL_R = 0.146         # m, shell bore radius (body_r 158 - wall 12)
INTAKE_A = 2*17*50e-3*3.5e-3   # m2, floor intake slots (feeder.scad floor_intake_cutters)
VENT_A = 120*3e-3*22e-3        # m2, wall slits (vent_pitch 3 deg, vent_w 3, vent_h 22)
CD_SLOT = 0.6

# CAD study geometry (cad/parameters.scad, 2026-10-25)
CAD = dict(channel_h=0.015, channel_w=0.0775, site_r=0.100, n_sites=4,
           cold_sink=(0.050, 0.050), cold_fin_h=0.019, cold_base=0.003,
           spacer_t=0.0065, pocket_w=0.054, pocket_floor=0.008)


@dataclass(frozen=True)
class Sink:
    """Plate-fin sink. width across fins, length along flow, height incl. base."""
    width: float
    length: float
    height: float
    base: float
    fin_t: float
    pitch: float
    k: float = K_AL
    # Optional overrides for drawn (non-uniform) profiles; 0 keeps the uniform model.
    n_ch_fix: int = 0        # number of air channels between fins
    gap_fix: float = 0.0     # channel width, m
    solid_w: float = 0.0     # total metal width across the inlet face, m (contraction)
    faces: int = 0           # wetted fin faces counted as extended surface

    @property
    def n_fins(self):
        if self.n_ch_fix:
            return self.n_ch_fix+1
        return int((self.width-self.fin_t)/self.pitch)+1

    @property
    def n_ch(self):
        return self.n_ch_fix or self.n_fins-1

    @property
    def gap(self):
        return self.gap_fix or self.pitch-self.fin_t

    @property
    def fin_h(self):
        return self.height-self.base

    @property
    def free_area(self):
        return self.n_ch*self.gap*self.fin_h


def spreading_R(src_a, plate_a, t, k, h_eff):
    """Song, Lee & Au (1994) square source on square plate, equivalent circular radii."""
    a = math.sqrt(src_a/math.pi)
    b = math.sqrt(plate_a/math.pi)
    eps, tau = a/b, t/b
    bi = h_eff*b/k
    lam = math.pi+1/(math.sqrt(math.pi)*eps)
    phi = (math.tanh(lam*tau)+lam/bi)/(1+lam/bi*math.tanh(lam*tau))
    psi = eps*tau/math.sqrt(math.pi)+(1-eps)*phi/math.sqrt(math.pi)
    return psi/(math.sqrt(math.pi)*k*a)


def sink_perf(s: Sink, q_m3s, t_air_c, src=0.040):
    """R (K/W) from source face to INLET air, and pressure drop (Pa), at flow q."""
    rho, mu, k_air, pr = P.air_props(t_air_c)
    nu_k = mu/rho
    n_ch = s.n_ch
    u = q_m3s/(n_ch*s.gap*s.fin_h)
    b = s.gap
    re_b = u*b/nu_k
    re_star = re_b*b/s.length
    # Teertstra, Yovanovich & Culham (1999) composite for parallel-plate channels
    nu = ((re_star*pr/2)**-3+(0.664*math.sqrt(re_star)*pr**(1/3)
                              * math.sqrt(1+3.65/math.sqrt(re_star)))**-3)**(-1/3)
    h = nu*k_air/b
    m = math.sqrt(2*h/(s.k*s.fin_t))
    eta = math.tanh(m*s.fin_h)/(m*s.fin_h)
    area = (s.faces or s.n_fins*2)*s.fin_h*s.length*eta+n_ch*b*s.length
    ha = h*area
    mcp = rho*q_m3s*P.AIR_CP
    ntu = ha/mcp
    r_conv = 1/(mcp*(1-math.exp(-ntu)))
    plate = s.width*s.length
    r_spread = spreading_R(src*src, plate, s.base, s.k, ha/plate)
    r_base = s.base/(s.k*plate)
    r_tim = R_PASTE/(src*src)
    # pressure: Shah-London apparent friction (plates), plus contraction/expansion
    dh = 2*b
    re_dh = u*dh/nu_k
    xplus = s.length/(dh*re_dh)
    fapp = math.sqrt((3.44/math.sqrt(xplus))**2+24**2)/re_dh
    sigma = 1-(s.solid_w or s.n_fins*s.fin_t)/s.width
    kc, ke = 0.42*(1-sigma**2), (1-sigma)**2
    dp = (4*fapp*s.length/dh+kc+ke)*0.5*rho*u*u
    return dict(u_m_s=u, Re_b=re_b, h_W_m2K=h, fin_eff=eta, NTU=ntu, R_conv=r_conv,
                R_spread=r_spread, R_base=r_base, R_tim=r_tim,
                R_total=r_conv+r_spread+r_base+r_tim, dp_Pa=dp)


def orifice_q(dp, area, rho, cd=CD_SLOT):
    return 0.0 if area <= 0 or dp <= 0 else cd*area*math.sqrt(2*dp/rho)


def orifice_dp(q, area, rho, cd=CD_SLOT):
    return 0.5*rho*(q/(cd*area))**2


def bisect(f, lo, hi, n=100):
    flo = f(lo)
    assert (flo > 0) != (f(hi) > 0), 'root not bracketed'
    for _ in range(n):
        mid = (lo+hi)/2
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo+hi)/2


# Datasheet fan curves, linearised (conservative between endpoints)
FANS = {
    # Noctua NF-A12x25 PWM, already in BOM.md: 102.1 m3/h, 2.34 mm H2O
    'NF-A12x25': dict(q0=102.1/3600, p0=2.34*9.80665, W=1.68*0.6,
                      src='noctua.at specification; power ~60 % of 1.68 W max (estimate)'),
    # Sunon MF50151V2-1B00U-A99 5015 blower: 3.5 CFM, 0.400 in H2O (DigiKey listing)
    'MF50151V2-blower': dict(q0=3.5*0.000471947, p0=0.400*249.089, W=0.6,
                             src='DigiKey listing; input power assumed 0.6 W (estimate)'),
    'MF50151V1-blower': dict(q0=4.5*0.000471947, p0=0.670*249.089, W=1.0,
                             src='DigiKey listing; input power assumed 1.0 W (estimate)'),
    # Sourced 2026-10-26 (kb/d34-sourcing.md): RS PRO ODB5115-12HB, RS 144-4136,
    # 4.2 CFM, 0.5 inH2O (124 Pa), 12 V 120 mA; full input power assumed in the loop.
    'ODB5115-12HB': dict(q0=4.2*0.000471947, p0=0.5*249.089, W=12*0.120,
                         src='RS export spec; 1.44 W at 12 V (all into the cold loop)'),
}


def fan_q(fan, dp):
    return max(0.0, fan['q0']*(1-dp/fan['p0']))


def hot_side(fan, sink, n, bypass_a, t_in=24.0, area_scale=1.0):
    """Fan -> intake slots -> central zone -> n sinks || bypass -> wall vents."""
    rho = P.air_props(t_in)[0]
    s_in, s_vent = area_scale if isinstance(area_scale, tuple) else (area_scale, area_scale)

    def sink_q(dp):
        return bisect(lambda q: sink_perf(sink, q, t_in)['dp_Pa']-dp, 1e-14, 0.1)

    def residual(dp_mid):  # dp across sinks/bypass + vents equals fan rise - intake loss
        q_s = sink_q(dp_mid)
        q_tot = n*q_s+orifice_q(dp_mid, bypass_a, rho)
        dp_need = (dp_mid+orifice_dp(q_tot, VENT_A*s_vent, rho)
                   + orifice_dp(q_tot, INTAKE_A*s_in, rho))
        return fan_q(fan, dp_need)-q_tot

    dp_mid = bisect(residual, 1e-6, fan['p0'])
    assert abs(residual(dp_mid)) < 1e-6
    q_s = sink_q(dp_mid)
    q_tot = n*q_s+orifice_q(dp_mid, bypass_a, rho)
    perf = sink_perf(sink, q_s, t_in)
    return dict(fan_total_L_s=q_tot*1e3, per_sink_L_s=q_s*1e3,
                through_sinks_frac=n*q_s/q_tot, dp_sinks_Pa=dp_mid, **perf)


def cold_side(blower, sink, n, t_air=-5.0, bypass_frac_area=None):
    """Blower drives the loop; each site is a fin bank in parallel with a side gap.

    Channel friction from plenum.channel_h with the CAD width; 4 x 90-degree-equivalent
    dynamic heads for the turn into/out of the blower and the drop into each pocket."""
    rho = P.air_props(t_air)[0]
    hgt, wid = CAD['channel_h'], CAD['channel_w']
    slots = None
    if isinstance(bypass_frac_area, (tuple, list)):
        # 2026-10-26 (stocked-sink study): explicit bypass ducts beside/over/under the
        # fins, each (width, height) m, running the sink length in parallel with it.
        slots = [(w, h_) for w, h_ in bypass_frac_area if w > 0 and h_ > 0]
        gap_w, gap_a = 0.0, sum(w*h_ for w, h_ in slots)
    else:
        gap_w = wid-sink.width if bypass_frac_area is None else bypass_frac_area
        gap_w = max(gap_w, 0.0)
        gap_a = gap_w*hgt
    loop_len = 2*math.pi*0.1025

    mu = P.air_props(t_air)[1]

    def gap_dp(q):  # side slot beside the fins: laminar friction (96/Re) + one entry head
        if gap_a <= 0:
            return 0.0
        u = q/gap_a
        dh = 2*gap_w*hgt/(gap_w+hgt)
        return 96*mu*u*sink.length/(dh*dh)*2+1.0*0.5*rho*u*u

    def slot_dp(q, w, h_):
        """Laminar rectangular duct (Shah & London fRe, Darcy) + one entry head."""
        a_s, al = w*h_, min(w, h_)/max(w, h_)
        u = q/a_s
        dh = 2*a_s/(w+h_)
        fre = 96*(1-1.3553*al+1.9467*al**2-1.7012*al**3+0.9564*al**4-0.2537*al**5)
        return fre*mu*u*sink.length/(2*dh*dh)+1.0*0.5*rho*u*u

    def bank(dp):
        q_s = bisect(lambda q: sink_perf(sink, q, t_air)['dp_Pa']-dp, 1e-14, 0.1)
        if slots is not None:
            q_g = sum(bisect(lambda q, w=w, h_=h_: slot_dp(q, w, h_)-dp, 0.0, 0.1)
                      for w, h_ in slots)
        else:
            q_g = bisect(lambda q: gap_dp(q)-dp, 0.0, 0.1) if gap_a > 0 else 0.0
        return q_s, q_g

    def loop_dp(q):
        v = q/(hgt*wid)
        ch = P.channel_h(v, hgt, wid, t_air)
        dyn = 0.5*rho*v*v
        dp_bank = bisect(lambda d: sum(bank(d))-q, 1e-9, 2000.0)
        return ch['friction_f']*loop_len/(ch['Dh_mm']/1e3)*dyn+(2+n)*dyn+n*dp_bank

    q = bisect(lambda q: fan_q(blower, loop_dp(q))-q, 1e-7, blower['q0'])
    assert abs(fan_q(blower, loop_dp(q))-q) < 1e-7
    v = q/(hgt*wid)
    dp_bank = bisect(lambda d: sum(bank(d))-q, 1e-9, 2000.0)
    q_s, q_g = bank(dp_bank)
    perf = sink_perf(sink, q_s, t_air)
    # source-to-loop-air resistance: the gap flow rejoins downstream, so referencing
    # the fin-stream NTU to the bank inlet is the right local temperature.
    spacer = CAD['spacer_t']/(K_AL*0.040**2)+P_TIM_EXTRA
    ch = P.channel_h(v, hgt, wid, t_air)
    return dict(loop_L_s=q*1e3, loop_v_m_s=v, fins_frac=q_s/q, dp_bank_Pa=dp_bank,
                bypass_mm2=gap_a*1e6,
                h_tray_lower=ch['h_lower_W_m2K'], h_tray_dev=ch['h_developing_est_W_m2K'],
                R_cold_total=perf['R_total']+spacer, **{f'fin_{k}': x for k, x in perf.items()})


P_TIM_EXTRA = R_PASTE/(0.040**2)   # second pasted interface (spacer to cold sink)


def heat_balance_cad(boundary, t_air, h, n, v, fan_W, deck_k=0.065, leak=P.DESIGN_LEAK,
                     pocket=None):
    """plenum.heat_balance with CAD channel width/height, plus thin pocket floors."""
    old = P.CHANNEL_W
    P.CHANNEL_W = CAD['channel_w']
    try:
        hb = P.heat_balance(boundary, t_air, h, deck_k, fan_W, leak, 1, n, v=v,
                            height=CAD['channel_h'])
    finally:
        P.CHANNEL_W = old
    b = P.BOUNDARIES[boundary]
    # pockets minus the 40 mm window: thinner PETG floor than the 18 mm deck
    pw, pl_, pf = pocket or (CAD['pocket_w'], CAD['pocket_w'], CAD['pocket_floor'])
    a_p = n*(pw*pl_-0.040**2)
    u18 = 1/(1/h+P.DECK_T/deck_k+1/P.H_BAY)
    u8 = 1/(1/h+pf/deck_k+1/P.H_BAY)
    extra = (u8-u18)*a_p*(b['bay']-t_air)
    hb['pocket_extra_W'] = extra
    hb['total_W'] += extra
    hb['air_sawtooth_K'] *= hb['total_W']/(hb['total_W']-extra)
    return hb


SINKS = {
    # CAD envelope 70 tangential x 70 radial x 45, radial channels
    'hot70_p2.5': Sink(0.070, 0.070, 0.045, 0.006, 0.0010, 0.0025),
    'hot70_p3.0': Sink(0.070, 0.070, 0.045, 0.006, 0.0010, 0.0030),
    'hot70_p4.0': Sink(0.070, 0.070, 0.045, 0.006, 0.0012, 0.0040),
    # larger envelope for a two-site layout (sites at 90/270 have room tangentially)
    'hot100x70_p3.0': Sink(0.100, 0.070, 0.045, 0.006, 0.0010, 0.0030),
}
COLD = {
    # longer along the flow (tangential); pocket grows to 54 x 84 mm
    'cold50x80_p4': Sink(0.050, 0.080, 0.022, 0.003, 0.0010, 0.004),
    # CAD rev 2 (2026-10-26): 70 radial x 60 along flow; pocket 76 x 64, mean floor 7.25 mm
    'cold70x60_p4': Sink(0.070, 0.060, 0.022, 0.003, 0.0010, 0.004),
    'cold50_p4': Sink(0.050, 0.050, 0.022, 0.003, 0.0010, 0.004),
    'cold50_p5': Sink(0.050, 0.050, 0.022, 0.003, 0.0010, 0.005),
    'cold50_p6': Sink(0.050, 0.050, 0.022, 0.003, 0.0012, 0.006),
}
# --------------------------------------------------------------------------
# Stocked and candidate sinks (2026-10-26). Geometry from manufacturer drawings saved in
# thermal/datasheets/ (MANIFEST.json); 'est' marks dimensions read off a drawing or image
# by scale. Kept out of SINKS/COLD so the generic sweeps above stay unchanged.
# Hot sinks: width = tangential (across fins), length = radial (along the fins and flow).
SINKS_STOCK = {
    # Fischer SK 100 (drawing 001014624): 66 W x 40 H, 10 mm base, 7 tapered fins at
    # 10.2 mm pitch. Fin 2.2 tip / 4.15 root inner, outer 3.5/4.5 [est]: mean 3.2 mm,
    # mean gap 7.0 mm. As stocked: SK 100 75 SA (75 mm long; Farnell 4621827, RS 189-8088).
    'SK100_L75': Sink(0.066, 0.075, 0.040, 0.010, 0.0032, 0.0102, n_ch_fix=6, gap_fix=0.0070,
                      solid_w=0.024, faces=14),
    'SK100_L50': Sink(0.066, 0.050, 0.040, 0.010, 0.0032, 0.0102, n_ch_fix=6, gap_fix=0.0070,
                      solid_w=0.024, faces=14),
    # Alutronic PR 614 (spec table: 75 W x 45 H, 5 mm base); 22 fins at ~3.53 mm pitch
    # counted on the maker's profile image; fin ~1.0 tip / 1.7 root [est] -> mean 1.35 mm,
    # mean gap 2.2 mm [est]. Cut to 70 mm by Alutronic (sold by length).
    'PR614_L70': Sink(0.075, 0.070, 0.045, 0.005, 0.00135, 0.00353, n_ch_fix=21,
                      gap_fix=0.0022, solid_w=0.075-21*0.0022),
}
COLD_STOCK = {
    # TED TDEX6015/TH (RS 158-562): 60 x 60 x 16 per RS. Fin geometry from the end view of
    # the TDEX6015/TH12G fan-assembly sheet (same extrusion assumed) [est]: 15.8 mm high,
    # 4.3 mm base, 15 slots of 1.79 mm, 14 fins of 1.2 mm, two 8.2 mm solid end blocks
    # (tapped M3) that act as thick outer fins.
    'TDEX6015_L60': Sink(0.060, 0.060, 0.0158, 0.0043, 0.0012, 0.0030, n_ch_fix=15,
                         gap_fix=0.00179, solid_w=0.060-15*0.00179, faces=30),
    # Alutronic PR 411 (spec table 74.5 W x 22 H, 3 mm base); 13 serrated fins at 6.03 mm
    # pitch counted on the maker's profile; fin ~1.7 mm [est; 1.71 kg/m implies 1.66]. Cut to length.
    'PR411_L60': Sink(0.0745, 0.060, 0.022, 0.003, 0.0017, 0.00603, n_ch_fix=12),
    # 46 mm keeps the 74.5 mm-wide sink's outer corners inside the R140.5 lip clearance
    # with pl_cold_dr 1.25 (sqrt(138.5^2+23^2) = 140.4); 60 mm needs a lip relief in CAD.
    'PR411_L46': Sink(0.0745, 0.046, 0.022, 0.003, 0.0017, 0.00603, n_ch_fix=12),
    # Fischer SK 444 (drawing 001014249): 62.5 W x 20 H, 3.5 mm base, 12 fins at 5.5 mm
    # pitch; fin ~2.2 root / 1.6 tip [drawing, measured by scale] -> mean 1.9 mm.
    'SK444_L50': Sink(0.0625, 0.050, 0.020, 0.0035, 0.0019, 0.0055),
}
ALL_HOT = {**SINKS, **SINKS_STOCK}
ALL_COLD = {**COLD, **COLD_STOCK}

# Cold-site cross-section in CAD (cad/parameters.scad, read 2026-10-26; not edited here):
# tray underside Z117 (pl_cold_top + 1), deck top Z102, cold-sink base on the spacer at
# Z94 (pl_cold_bottom), pocket floor mean Z91.25 (8 mm, 1.5 mm fall), 45 x 45 mm collar
# round the window, pocket 76 mm radial, channel 77.5 mm (pl_inner/outer_wall).
Z_TRAY, Z_SINK, Z_POCKET_FLOOR, COLLAR_W = 0.117, 0.094, 0.09125, 0.045


def cold_slots(s, pocket_w=0.076, z_base=Z_SINK, ducted=False):
    """Bypass ducts round one cold sink: over the fin tips (full channel width), both
    sides (mean of pocket and channel width) and under the base outside the collar.
    ducted=True: printed fillers close the sides/pocket to 0.5 mm, 1 mm over the tips."""
    if ducted:
        return ((s.width, 0.001), (0.0005, s.height), (0.0005, s.height))
    top = Z_TRAY-(z_base+s.height)
    side = max(((pocket_w+CAD['channel_w'])/2-s.width)/2, 0.0)
    under = max(min(s.width, pocket_w)-COLLAR_W, 0.0)
    return tuple(x for x in ((CAD['channel_w'], top), (side, s.height), (side, s.height),
                             (under, z_base-Z_POCKET_FLOOR)) if x[0] > 0 and x[1] > 0)


def hot_dropin_bypass(s, env=(0.070, 0.045)):
    """Extra hot-side leakage per sink when a smaller sink drops into the unchanged
    70 x 45 bay: side gaps to the baffle ends over the fin height, plus the strip under
    the fin tips above the apron (apron top is set by pl_hot_sink height)."""
    return max(env[0]-s.width, 0)*s.height+max(env[1]-s.height, 0)*s.width


I_CAP = 2.2   # A, ADV127 steady-state current target (owner brief, 2026-10-26)
FOOD_MAX_C, FOOD_MIN_C = 4.0, 0.0   # covered warmest top / coldest bottom targets
BRICK_MAX_W = 110.0   # brick budget P.brick() (incl. 1.25 margin) on the 160 W GST160A24

OP_KEYS = ('I_A', 'V_V', 'P_W', 'Qc_W', 'Qh_W', 'Tc_C', 'Th_C', 'dT_K', 'COP',
           'tec_total_W', 'brick_W')
MODULES = {'CP60440': ('CP60440', 6.0), 'CP60440_lsq': ('CP60440_lsq', 6.0), 'TARK': ('TARK', 3.9),
           'ADV127': ('ADV127', 4.0)}


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    fits, _ = P.tec_fits(root)
    # Adaptive ADV-127-135200-S (sourced, RS 606-975): least squares over points read from
    # its datasheet charts at Th 25/50 C (adv127-operating-points.json). The max-parameter
    # fit (Imax 4 A, Vmax 15.4 V, dTmax 65 K) overstates K (0.37 against 0.33 W/K).
    adv = json.loads((Path(__file__).parent/'adv127-operating-points.json').read_text())
    fits['ADV127'] = dict(source=adv['source'], fit='linear least squares',
                          **P.fit_lsq(adv['points']))
    boundary = 'realistic'
    room = P.BOUNDARIES[boundary]['room']
    t_in = room+2.0   # fan inlet: room + fan, motor and electronics preheat (estimate)

    hot_rows = []
    for fan_name in ('NF-A12x25',):
        for sname, s in SINKS.items():
            for n in (2, 3, 4):
                if sname.startswith('hot100') and n > 2:
                    continue
                for byp in (0.0, 0.002, 0.006):
                    r = hot_side(FANS[fan_name], s, n, byp, t_in)
                    hot_rows.append(dict(fan=fan_name, sink=sname, n_sinks=n, n_fins=s.n_fins,
                                         bypass_mm2=byp*1e6, **r))
    write_csv(out/'hot_side.csv', hot_rows)

    cold_rows = []
    for bname in ('MF50151V2-blower', 'MF50151V1-blower'):
        for sname, s in COLD.items():
            for n in (2, 3, 4):
                for gap in (None, 0.010, 0.0):
                    r = cold_side(FANS[bname], s, n, -5.0, gap)
                    cold_rows.append(dict(blower=bname, sink=sname, n_sites=n,
                                          side_gap_mm=(CAD['channel_w']-s.width if gap is None
                                                       else gap)*1e3, **r))
    write_csv(out/'cold_side.csv', cold_rows)

    # Layouts: n sites, hot sink, hot bypass m2, vent/intake area scale, cold sink,
    # side gap beside the cold fins (m), blower
    layouts = {
        'CAD_4x70_open': (4, 'hot70_p3.0', 0.006, 1.0, 'cold50_p5', 0.0275, 'MF50151V2-blower'),
        'CAD_4x70_baffled': (4, 'hot70_p3.0', 0.0, 1.0, 'cold50_p5', 0.010, 'MF50151V2-blower'),
        '3x70_baffled': (3, 'hot70_p3.0', 0.0, 1.0, 'cold50_p5', 0.010, 'MF50151V2-blower'),
        '4x_vents1.5': (4, 'hot70_p3.0', 0.0, 1.5, 'cold50_p5', 0.010, 'MF50151V2-blower'),
        '4x_cold80_V1': (4, 'hot70_p3.0', 0.0, 1.0, 'cold50x80_p4', 0.0, 'MF50151V1-blower'),
        '4x_improved': (4, 'hot70_p3.0', 0.0, 1.5, 'cold50x80_p4', 0.0, 'MF50151V1-blower'),
        '3x_improved': (3, 'hot70_p3.0', 0.0, 1.5, 'cold50x80_p4', 0.0, 'MF50151V1-blower'),
        '2x100_improved': (2, 'hot100x70_p3.0', 0.0, 1.5, 'cold50x80_p4', 0.0, 'MF50151V1-blower'),
        # As modelled in CAD rev 2: intake slots x1.2, two slit rows (x2), drop-in
        # baffles with ~800 mm2 of slot/corner leakage, 6.5 mm total cold side gap.
        'CAD_rev2': (4, 'hot70_p3.0', 0.0008, (1.2, 2.0), 'cold70x60_p4', 0.0065,
                     'MF50151V1-blower'),
        # As sourced (2026-10-26): stocked RS PRO blower, baffle slots widened for the
        # harness (+~500 mm2), Adaptive ADV-127 modules.
        'CAD_rev3_sourced': (4, 'hot70_p3.0', 0.0013, (1.2, 2.0), 'cold70x60_p4', 0.0065,
                             'ODB5115-12HB'),
        # 2026-10-26 stocked-sink study. Same fans, vents, baffle leakage (1300 mm2) and
        # pockets as CAD_rev3_sourced; cold bypass as explicit slots (cold_slots).
        # Target sinks re-run with the slot accounting, for a like-for-like reference:
        'rev3_target_slots': (4, 'hot70_p3.0', 0.0013, (1.2, 2.0), 'cold70x60_p4',
                              cold_slots(COLD['cold70x60_p4']), 'ODB5115-12HB'),
        # Stocked trial parts dropped into the unchanged CAD (SK 100 75 needs 75 mm radial):
        'stocked_dropin': (4, 'SK100_L75', 0.0013+4*hot_dropin_bypass(SINKS_STOCK['SK100_L75']),
                           (1.2, 2.0), 'TDEX6015_L60', cold_slots(COLD_STOCK['TDEX6015_L60']),
                           'ODB5115-12HB'),
        # Stocked parts with the CAD fitted to them: aprons/baffles to 66 x 40 and printed
        # fillers ducting the 60 x 16 cold sink (upper bound for these parts):
        'stocked_fitted': (4, 'SK100_L75', 0.0013, (1.2, 2.0), 'TDEX6015_L60',
                           cold_slots(COLD_STOCK['TDEX6015_L60'], ducted=True), 'ODB5115-12HB'),
        # Candidates (cut-to-length extrusions, Alutronic direct):
        'PR614_PR411L46': (4, 'PR614_L70', 0.0013, (1.2, 2.0), 'PR411_L46',
                           cold_slots(COLD_STOCK['PR411_L46']), 'ODB5115-12HB'),
        'PR614_PR411L60': (4, 'PR614_L70', 0.0013, (1.2, 2.0), 'PR411_L60',
                           cold_slots(COLD_STOCK['PR411_L60']), 'ODB5115-12HB'),
        'PR614_SK444L50': (4, 'PR614_L70', 0.0013, (1.2, 2.0), 'SK444_L50',
                           cold_slots(COLD_STOCK['SK444_L50']), 'ODB5115-12HB'),
        # Which side limits: stocked hot sink with the recommended cold sink, and vice versa
        'SK100_PR411L46': (4, 'SK100_L75', 0.0013, (1.2, 2.0), 'PR411_L46',
                           cold_slots(COLD_STOCK['PR411_L46']), 'ODB5115-12HB'),
        'PR614_TDEX': (4, 'PR614_L70', 0.0013, (1.2, 2.0), 'TDEX6015_L60',
                       cold_slots(COLD_STOCK['TDEX6015_L60']), 'ODB5115-12HB'),
    }
    # 76 x 64 mm cold pocket, 7.25 mm mean PETG floor (CAD rev 2 on); earlier layouts use
    # the CAD-dict pocket. Every stocked/candidate sink here fits the 76 x 64 pocket.
    POCKETS = {k: (0.076, 0.064, 0.00725) for k in layouts
               if k not in ('CAD_4x70_open', 'CAD_4x70_baffled', '3x70_baffled', '4x_vents1.5',
                         '4x_cold80_V1', '4x_improved', '3x_improved', '2x100_improved')}
    EXPOSURE_LAYOUTS = ['CAD_rev3_sourced', 'rev3_target_slots', 'stocked_dropin',
                        'stocked_fitted', 'PR614_PR411L46', 'PR614_PR411L60',
                        'PR614_SK444L50', 'SK100_PR411L46', 'PR614_TDEX']
    layout_rows = []
    size_rows, food_rows, summary = [], [], {}
    for lname, (n, hs, byp, scale, cs, gap, bl) in layouts.items():
        hr = hot_side(FANS['NF-A12x25'], ALL_HOT[hs], n, byp, t_in, scale)
        cr = cold_side(FANS[bl], ALL_COLD[cs], n, -5.0, gap)
        layout_rows.append(dict(layout=lname, n=n, hot_sink=hs, hot_bypass_mm2=byp*1e6,
                                vent_intake_scale=str(scale), cold_sink=cs,
                                cold_gap_mm=gap*1e3 if isinstance(gap, float) else 'slots',
                                cold_bypass_mm2=cr['bypass_mm2'], cold_fins_frac=cr['fins_frac'],
                                hot_through_sinks_frac=hr['through_sinks_frac'],
                                blower=bl, fan_total_L_s=hr['fan_total_L_s'],
                                per_sink_L_s=hr['per_sink_L_s'], R_hot=hr['R_total'],
                                loop_L_s=cr['loop_L_s'], loop_v_m_s=cr['loop_v_m_s'],
                                h_tray_lower=cr['h_tray_lower'], h_tray_dev=cr['h_tray_dev'],
                                R_cold=cr['R_cold_total']))
        for h_label, h in (('lower', cr['h_tray_lower']), ('developing', cr['h_tray_dev'])):
            for t_air in (-2.0, -5.0):
                hb = heat_balance_cad(boundary, t_air, h, n, cr['loop_v_m_s'], FANS[bl]['W'],
                                      pocket=POCKETS.get(lname))
                warm = t_air+hb['air_sawtooth_K']/2
                foods = {}
                for pos in ('covered', 'open'):
                    p = dc_replace(P.plenum_params(boundary, pos, t_air, h), cold=warm)
                    m, t, st = P.solve(p)
                    e = P.post(m, t, 1/h+p.floor/p.petg_k)
                    p2 = dc_replace(p, cold=t_air-hb['air_sawtooth_K']/2)
                    m2, t2, st2 = P.solve(p2)
                    e2 = P.post(m2, t2, 1/h+p2.floor/p2.petg_k)
                    foods[pos] = dict(warmest_wedge_mean_C=st['mean_C'],
                                      warmest_top_est_C=e['top_surface_max_C'],
                                      coldest_bottom_est_C=e2['food_bottom_min_C'])
                    food_rows.append(dict(layout=lname, h_basis=h_label, h_W_m2K=h,
                                          T_air_C=t_air, sawtooth_K=hb['air_sawtooth_K'],
                                          position=pos, **foods[pos]))
                for mod, (fit, imax) in MODULES.items():
                    q = hb['total_W']/n
                    t_fin = t_air-hb['air_sawtooth_K']/2
                    op = P.tec_operate(fits[fit], q, t_fin, cr['R_cold_total'], t_in,
                                       hr['R_total'], imax)
                    row = dict(layout=lname, h_basis=h_label, h_W_m2K=h, T_air_C=t_air,
                               module=mod, n=n, load_W=hb['total_W'], deck_W=hb['deck_W'],
                               pocket_extra_W=hb['pocket_extra_W'], qc_per_W=q,
                               R_hot=hr['R_total'], R_cold=cr['R_cold_total'],
                               hot_inlet_C=t_in, per_sink_L_s=hr['per_sink_L_s'],
                               loop_v_m_s=cr['loop_v_m_s'], feasible=op is not None)
                    row.update(op or dict.fromkeys(OP_KEYS, ''))
                    if op:
                        row['tec_total_W'] = n*op['P_W']
                        row['brick_W'] = P.brick(row['tec_total_W'])
                    size_rows.append(row)
                    if h_label == 'lower' and t_air == -5.0:
                        summary.setdefault(lname, {})[mod] = {
                            k: row.get(k) for k in ('load_W', 'R_hot', 'R_cold', 'feasible', 'I_A',
                                                    'V_V', 'Th_C', 'Tc_C', 'COP', 'tec_total_W',
                                                    'brick_W')}
                        summary[lname]['food'] = foods
                        summary[lname]['h_tray'] = h
    write_csv(out/'layouts.csv', layout_rows)

    # Current-capped check (2026-10-26, stocked-sink study): coldest loop air each layout
    # can hold with ADV127 at I <= I_CAP steady, and the food temperatures at that air.
    cap_rows = []
    for lname in EXPOSURE_LAYOUTS:
        n, bl = layouts[lname][0], layouts[lname][6]
        lr = next(r for r in layout_rows if r['layout'] == lname)
        for h_label in ('h_tray_lower', 'h_tray_dev'):
            h = lr[h_label]

            def op_at(t_air):
                hb = heat_balance_cad(boundary, t_air, h, n, lr['loop_v_m_s'], FANS[bl]['W'],
                                      pocket=POCKETS.get(lname))
                return hb, P.tec_operate(fits['ADV127'], hb['total_W']/n,
                                         t_air-hb['air_sawtooth_K']/2, lr['R_cold'], t_in,
                                         lr['R_hot'], I_CAP)
            lo, hi = -12.0, 20.0      # lo infeasible / hi feasible (room 22 C)
            if op_at(lo)[1] is not None:
                hi = lo
            elif op_at(hi)[1] is None:
                lo = hi = float('nan')
            else:
                for _ in range(16):
                    mid = (lo+hi)/2
                    lo, hi = (lo, mid) if op_at(mid)[1] is not None else (mid, hi)
            row = dict(layout=lname, h_basis=h_label, h_W_m2K=h, I_cap_A=I_CAP,
                       coldest_air_C=hi)
            if not math.isnan(hi):
                hb, op = op_at(hi)
                warm = hi+hb['air_sawtooth_K']/2
                for pos in ('covered', 'open'):
                    pp = dc_replace(P.plenum_params(boundary, pos, hi, h), cold=warm)
                    m, t, st = P.solve(pp)
                    e = P.post(m, t, 1/h+pp.floor/pp.petg_k)
                    p2 = dc_replace(pp, cold=hi-hb['air_sawtooth_K']/2)
                    m2, t2, _ = P.solve(p2)
                    e2 = P.post(m2, t2, 1/h+p2.floor/p2.petg_k)
                    row[f'{pos}_warmest_top_C'] = e['top_surface_max_C']
                    row[f'{pos}_coldest_bottom_C'] = e2['food_bottom_min_C']
                row.update(load_W=hb['total_W'], I_A=op['I_A'], tec_total_W=n*op['P_W'],
                           brick_W=P.brick(n*op['P_W']))
            cap_rows.append(row)
    write_csv(out/'current_capped.csv', cap_rows)

    # Food-target check: the loop air at which the warmest covered food top reaches
    # FOOD_MAX_C, the TEC operating point needed there (ADV127, up to Imax 4 A) and the
    # coldest food bottom. Pass flags use the owner's targets (2026-10-26).
    tgt_rows = []
    for lname in EXPOSURE_LAYOUTS:
        n, bl = layouts[lname][0], layouts[lname][6]
        lr = next(r for r in layout_rows if r['layout'] == lname)
        for h_label in ('h_tray_lower', 'h_tray_dev'):
            h = lr[h_label]

            def foods(t_air):
                hb = heat_balance_cad(boundary, t_air, h, n, lr['loop_v_m_s'], FANS[bl]['W'],
                                      pocket=POCKETS.get(lname))
                pp = dc_replace(P.plenum_params(boundary, 'covered', t_air, h),
                                cold=t_air+hb['air_sawtooth_K']/2)
                m, t, _ = P.solve(pp)
                warm = P.post(m, t, 1/h+pp.floor/pp.petg_k)['top_surface_max_C']
                p2 = dc_replace(pp, cold=t_air-hb['air_sawtooth_K']/2)
                m2, t2, _ = P.solve(p2)
                cold = P.post(m2, t2, 1/h+p2.floor/p2.petg_k)['food_bottom_min_C']
                return hb, warm, cold
            lo, hi = -10.0, 4.0
            for _ in range(14):
                mid = (lo+hi)/2
                lo, hi = (mid, hi) if foods(mid)[1] < FOOD_MAX_C else (lo, mid)
            t_air = lo
            hb, warm, cold = foods(t_air)
            op = P.tec_operate(fits['ADV127'], hb['total_W']/n, t_air-hb['air_sawtooth_K']/2,
                               lr['R_cold'], t_in, lr['R_hot'], 4.0)
            row = dict(layout=lname, h_basis=h_label, h_W_m2K=h, air_for_target_C=t_air,
                       covered_warmest_top_C=warm, covered_coldest_bottom_C=cold,
                       load_W=hb['total_W'], feasible=op is not None)
            if op:
                tec = n*op['P_W']
                row.update(I_A=op['I_A'], V_V=op['V_V'], Th_C=op['Th_C'], Tc_C=op['Tc_C'],
                           COP=op['COP'], tec_total_W=tec, input_W=tec/0.9+8.0,
                           brick_W=P.brick(tec))
                row['pass'] = (cold >= FOOD_MIN_C and op['I_A'] <= I_CAP
                               and row['brick_W'] <= BRICK_MAX_W)
            else:
                row['pass'] = False
            tgt_rows.append(row)
    write_csv(out/'food_target.csv', tgt_rows)
    write_csv(out/'sizing.csv', size_rows)
    write_csv(out/'food.csv', food_rows)

    # Required hot-side resistance for each module count at the design point
    req_rows = []
    for n in (2, 3, 4):
        cr = cold_side(FANS['MF50151V2-blower'], COLD['cold50_p5'], n, -5.0, 0.010)
        hb = heat_balance_cad(boundary, -5.0, cr['h_tray_lower'], n, cr['loop_v_m_s'],
                              FANS['MF50151V2-blower']['W'])
        for mod, (fit, imax) in MODULES.items():
            for i_cap in (imax*0.5, imax*0.7):
                lo, hi = 0.01, 3.0
                for _ in range(40):
                    mid = (lo+hi)/2
                    op = P.tec_operate(fits[fit], hb['total_W']/n,
                                       -5.0-hb['air_sawtooth_K']/2, cr['R_cold_total'],
                                       t_in, mid, i_cap)
                    lo, hi = (mid, hi) if op else (lo, mid)
                op = P.tec_operate(fits[fit], hb['total_W']/n, -5.0-hb['air_sawtooth_K']/2,
                                   cr['R_cold_total'], t_in, lo, i_cap)
                req_rows.append(dict(n=n, module=mod, I_cap_A=i_cap, load_W=hb['total_W'],
                                     max_R_hot_K_W=lo, P_total_W=n*op['P_W'] if op else ''))
    write_csv(out/'required_r_hot.csv', req_rows)

    # Open-position exposure and pull-down (ADV127 at 2.5 A) for the as-sourced layouts
    exposure, pd_rows = [], []
    for lname in EXPOSURE_LAYOUTS:
        rec = layouts[lname]
        rec_hot = next(r for r in layout_rows if r['layout'] == lname)
        for h_label in ('h_tray_lower', 'h_tray_dev'):
            h = rec_hot[h_label]
            hb = heat_balance_cad(boundary, -5.0, h, 4, rec_hot['loop_v_m_s'], FANS[rec[6]]['W'],
                                  pocket=POCKETS[lname])
            warm = -5.0+hb['air_sawtooth_K']/2
            pc = dc_replace(P.plenum_params(boundary, 'covered', -5.0, h), cold=warm)
            _, tcov, _ = P.solve(pc)
            po = dc_replace(P.plenum_params(boundary, 'open', -5.0, h), cold=warm)
            mo = P.Model(po)
            dt = 60
            extra = mo.capacity/dt
            t, first5 = list(tcov), None
            for sec in range(0, 4*3600+1, dt):
                e = P.post(mo, t, 1/h+po.floor/po.petg_k)
                if first5 is None and e['top_surface_max_C'] > 5.0:
                    first5 = sec/60
                if sec % 900 == 0:
                    exposure.append(dict(layout=lname, h_basis=h_label, h_W_m2K=h, local_air_C=warm,
                                         time_min=sec/60,
                                         layer_mean_C=sum(t)/len(t),
                                         top_surface_est_C=e['top_surface_max_C']))
                if sec < 4*3600:
                    t, _, _ = mo.solve(rhs=[b+extra*v for b, v in zip(mo.rhs, t)], initial=t,
                                       extra=extra)
            exposure.append(dict(layout=lname, h_basis=h_label, h_W_m2K=h, local_air_C=warm,
                                 time_min='top>5C at', layer_mean_C='',
                                 top_surface_est_C=first5 if first5 is not None else 'never'))
            for label, food0, air0 in (('cold_start_food20_unit20', 20.0, 20.0),
                                       ('load_food20_running', 20.0, -5.0),
                                       ('cold_start_food5_unit20', 5.0, 20.0)):
                res, _ = P.pulldown(boundary, -5.0, h, 4, fits['ADV127'], 2.5, rec_hot['R_cold'],
                                    rec_hot['R_hot'], food0, air0, fan_W=FANS[rec[6]]['W'])
                pd_rows.append(dict(layout=lname, h_basis=h_label, h_W_m2K=h, case=label,
                                    I_pulldown_A=2.5,
                                    **res))
    write_csv(out/'open_exposure.csv', exposure)
    write_csv(out/'pulldown.csv', pd_rows)

    report = dict(status='Reduced-order estimates, 2026-10-26; no physical test.',
                  geometry=CAD, fans=FANS, sinks={k: v.__dict__ for k, v in SINKS.items()},
                  cold_sinks={k: v.__dict__ for k, v in COLD.items()},
                  stocked_hot_sinks={k: v.__dict__ for k, v in SINKS_STOCK.items()},
                  stocked_cold_sinks={k: v.__dict__ for k, v in COLD_STOCK.items()},
                  cold_slots_m={k: v[5] for k, v in layouts.items() if not isinstance(v[5], float)},
                  i_cap_A=I_CAP, hot_inlet_C=t_in,
                  summary=summary, required_r_hot=req_rows, layouts=layout_rows,
                  open_exposure=exposure, pulldown=pd_rows, current_capped=cap_rows, food_target=tgt_rows,
                  provenance={'plenum_cad_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                              'plenum_sha256': hashlib.sha256((Path(__file__).parent/'plenum.py').read_bytes()).hexdigest()})
    (out/'results.json').write_text(json.dumps(report, indent=2, default=str)+'\n')
    print(json.dumps(dict(summary=summary, required_r_hot=req_rows), indent=1, default=str))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=Path(__file__).parent/'plenum-cad-output')
    run(ap.parse_args().output)
