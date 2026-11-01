#!/usr/bin/env python3
"""Direct-contact cold-face sweep versus a forced cold-air plenum (stdlib only).

Screening study, 2026-10-25. Reuses the historical finite-volume wedge solver
(model.py) without changing its defaults. Adds:
  1. direct40 at Tc = 0/-5/-10/-15 C under nominal and reviewer-realistic boundaries;
  2. plenum: whole bowl underside convectively cooled by air at T_air with h;
  3. channel Re/Nu estimate for a 10-15 mm annular duct;
  4. cold-chamber heat balance, TEC (alpha, R, K) fits and system sizing;
  5. lumped pull-down transients for 480 g of food.
Every number is a simulation or an estimate from stated inputs; nothing here is
a physical measurement. See kb/plenum-thermal.md.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import functools
import hashlib
import json
import math
from pathlib import Path

from model import Model, Parameters, write_csv

K0 = 273.15
BASE = replace(Parameters(), cap_width_mm=40.0, cap_thickness=0.0)  # direct40

# --------------------------------------------------------------------------
# Boundary sets. 'nominal' reproduces direct_contact.py; 'realistic' is the
# 2026-10-25 reviewer's set (22 C room, 32 C bay, lid U 2.5, 0.1 mm air gap).
# Open position keeps h = 5 W/m2K in both (existing convention).
# --------------------------------------------------------------------------
BOUNDARIES = {
    'nominal': dict(room=25.0, bay=30.0, top={'covered': 1.0, 'open': 5.0},
                    gap_R=0.0),
    'realistic': dict(room=22.0, bay=32.0, top={'covered': 2.5, 'open': 5.0},
                      gap_R=0.0001/0.026),
}
FREEZE_C = -1.0  # approximate initial freezing point of wet pet food

# Enclosure/plenum geometry (estimates from CAD parameters, see KB page)
BORE_D = 0.292            # m, constant enclosure bore
WALL_T = 0.012            # m, printed wall
DECK_T = 0.018            # m, printed deck
COLD_WALL_H = 0.035       # m, plenum 15 mm + tray/food zone 20 mm of side wall
CHANNEL_W = 0.080         # m, radial width of circumferential flow channel
PETG_RHO, PETG_CP = 1270.0, 1250.0
AIR_CP = 1006.0
H_SUBLIMATION = 2.834e6   # J/kg
H_BAY = 10.0              # W/m2K deck underside, fan-ventilated bay (estimate)
H_OUT = 8.0               # W/m2K outside wall, natural conv + radiation (estimate)


def air_props(t_c):
    """Dry air near 1 atm: rho, mu (Sutherland), k, Pr. Standard correlations."""
    t = t_c+K0
    rho = 101325/(287.05*t)
    mu = 1.716e-5*(t/273.15)**1.5*(273.15+110.4)/(t+110.4)
    k = 0.0241*(t/273.15)**0.81
    return rho, mu, k, 0.71


def p_sat(t_c):
    """Saturation vapour pressure, Pa (Magnus; over ice below 0 C)."""
    if t_c >= 0:
        return 611.2*math.exp(17.62*t_c/(243.12+t_c))
    return 611.2*math.exp(22.46*t_c/(272.62+t_c))


def humidity_ratio(t_c, rh):
    pv = rh*p_sat(t_c)
    return 0.622*pv/(101325-pv)


# --------------------------------------------------------------------------
# Food field helpers
# --------------------------------------------------------------------------
def solve(p):
    m = Model(p)
    t, it, res = m.solve()
    s = m.stats(t)
    assert abs(s['balance_W']) < 1e-7, s['balance_W']
    assert min(t) >= min(p.cold, p.ambient, p.underside)-1e-7
    assert max(t) <= max(p.cold, p.ambient, p.underside)+1e-7
    return m, t, s


def post(m, t, bottom_R):
    """Estimated top-surface and food-bottom temperatures from the FV node.

    The solver's node sits half a food depth above the floor and has no top
    half-depth resistance. Top surface (estimate) adds q_top*(d/2)/k_food.
    Food bottom (estimate) over the cooled area: T_cold + q*(bottom_R)."""
    p = m.p
    half = m.depth/(2*p.food_k)
    tops = [v+p.top_h*(p.ambient-v)*half for v in t]
    bottoms = [p.cold+m.cold_u*(v-p.cold)*bottom_R for v, f in zip(t, m.fraction) if f > 0]
    frozen_cells = sum(1 for v in t if v < FREEZE_C)/len(t)
    frozen_area = sum(f for v, f in zip(bottoms, [f for f in m.fraction if f > 0]) if v < FREEZE_C)
    return dict(top_surface_max_C=max(tops), top_surface_mean_C=sum(tops)/len(tops),
                food_bottom_min_C=min(bottoms) if bottoms else float('nan'),
                layer_cells_below_freeze_frac=frozen_cells,
                bottom_area_below_freeze_cm2=frozen_area*m.area_cell*1e4)


def direct_sweep(out):
    rows, params = [], {}
    for bname, b in BOUNDARIES.items():
        for pos, top_h in b['top'].items():
            for tc in (0.0, -5.0, -10.0, -15.0):
                p = replace(BASE, ambient=b['room'], underside=b['bay'], top_h=top_h,
                            cold=tc, contact_r=b['gap_R'])
                m, t, s = solve(p)
                e = post(m, t, p.contact_r+p.floor/p.petg_k)
                key = f'direct40__{bname}__{pos}__Tc{tc:g}'
                params[key] = asdict(p)
                rows.append(dict(case=key, boundary=bname, position=pos, cold_face_C=tc,
                                 layer_mean_C=s['mean_C'], layer_max_C=s['max_C'],
                                 layer_min_C=s['min_C'], **e,
                                 fraction_above_4C=s['fraction_above_4C'],
                                 coldface_W=s['cold_W'], deck_W=s['deck_W'], top_W=s['ambient_W']))
    write_csv(out/'direct_sweep.csv', rows)
    # monotonic: colder face never warms any food statistic
    for bname in BOUNDARIES:
        for pos in ('covered', 'open'):
            seq = [r for r in rows if r['boundary'] == bname and r['position'] == pos]
            assert all(a['layer_max_C'] >= b['layer_max_C'] for a, b in zip(seq, seq[1:]))
    return rows, params


# --------------------------------------------------------------------------
# Channel convection
# --------------------------------------------------------------------------
def gnielinski(re, pr):
    f = (0.790*math.log(re)-1.64)**-2
    return (f/8)*(re-1000)*pr/(1+12.7*math.sqrt(f/8)*(pr**(2/3)-1)), f


def channel_h(v, height, width=CHANNEL_W, t_c=-2.0):
    rho, mu, k, pr = air_props(t_c)
    dh = 2*height*width/(height+width)
    re = rho*v*dh/mu

    def nu_lam_dev(re_):
        # Laminar simultaneously developing flow between obstacles/fin banks: Stephan
        # correlation (parallel plates, both walls isothermal) scaled by 5.385/7.541 for
        # one heated wall. Segment = loop length at r105 / 3 fin banks (estimate).
        seg = 2*math.pi*0.105/3
        xs = seg/(dh*re_*pr)
        return (7.541+0.024*xs**-1.14/(1+0.0358*pr**0.17*xs**-0.64))*5.385/7.541

    nu_fd = 5.385  # fully developed laminar, one wall heated, other insulated (Shah & London)
    if re <= 2300:
        nu, nu_dev, regime, f = nu_fd, nu_lam_dev(re), 'laminar', 96/re
    elif re >= 4000:
        nu, f = gnielinski(re, pr)
        nu_dev, regime = nu, 'turbulent (Gnielinski)'
    else:
        nt, f = gnielinski(4000, pr)
        w = (re-2300)/1700
        nu = nu_fd*(1-w)+nt*w
        nu_dev = nu_lam_dev(2300)*(1-w)+nt*w
        regime = 'transitional (interpolated)'
    return dict(v_m_s=v, height_mm=height*1e3, width_mm=width*1e3, Dh_mm=dh*1e3, Re=re,
                regime=regime, Nu_lower=nu, h_lower_W_m2K=nu*k/dh,
                Nu_developing_est=max(nu, nu_dev), h_developing_est_W_m2K=max(nu, nu_dev)*k/dh,
                flow_L_s=v*height*width*1e3, friction_f=f, rho=rho)


def channel_table(out):
    rows = []
    for height in (0.010, 0.012, 0.015):
        for v in (0.5, 1.0, 1.5, 2.0, 3.0, 5.0):
            r = channel_h(v, height)
            # loop pressure drop: 0.7 m duct + ~6 dynamic heads (fin banks, turns, bumps)
            dyn = 0.5*r['rho']*v*v
            r['loop_dp_Pa_est'] = r['friction_f']*0.7/(r['Dh_mm']/1e3)*dyn+6*dyn
            r['air_power_mW_est'] = r['loop_dp_Pa_est']*r['flow_L_s']*1e-3*1e3
            rows.append(r)
    write_csv(out/'channel_convection.csv', rows)
    return rows


# --------------------------------------------------------------------------
# Plenum food field
# --------------------------------------------------------------------------
def plenum_params(boundary, pos, t_air, h):
    b = BOUNDARIES[boundary]
    return replace(BASE, ambient=b['room'], underside=b['bay'], top_h=b['top'][pos],
                   cold=t_air, contact_r=1.0/h, full_plate=True, deck_enabled=False)


def plenum_exact_1d(p, h):
    """Independent 1-D series check: air|1/h|floor|food d|top h -> room."""
    d = p.volume/Model(p).area
    r = 1/h+p.floor/p.petg_k+d/p.food_k+1/p.top_h
    q = (p.ambient-p.cold)/r
    top = p.ambient-q/p.top_h
    bottom = top-q*d/p.food_k
    return dict(exact_top_C=top, exact_mean_C=(top+bottom)/2, exact_bottom_C=bottom,
                exact_flux_W_m2=q)


def plenum_sweep(out):
    rows, params = [], {}
    for bname in BOUNDARIES:
        for pos in ('covered', 'open'):
            for t_air in (2.0, -2.0, -5.0, -10.0):
                for h in (10.0, 15.0, 20.0, 30.0, 50.0):
                    p = plenum_params(bname, pos, t_air, h)
                    m, t, s = solve(p)
                    e = post(m, t, 1/h+p.floor/p.petg_k)
                    x = plenum_exact_1d(p, h)
                    key = f'plenum__{bname}__{pos}__Tair{t_air:g}__h{h:g}'
                    params[key] = asdict(p)
                    rows.append(dict(case=key, boundary=bname, position=pos, T_air_C=t_air,
                                     h_W_m2K=h, layer_mean_C=s['mean_C'], layer_max_C=s['max_C'],
                                     **e, **x, wedge_air_W=s['cold_W']))
                    # uniform field: FV node vs analytic node (no top half resistance)
                    d = m.depth
                    rn = 1/h+p.floor/p.petg_k+d/(2*p.food_k)
                    node = (p.cold/rn+p.top_h*p.ambient)/(1/rn+p.top_h)
                    assert abs(s['max_C']-node) < 1e-6 and abs(s['min_C']-node) < 1e-6
    write_csv(out/'plenum_food.csv', rows)
    return rows, params


@functools.lru_cache(maxsize=None)
def wedge_flux(boundary, pos, t_air, h):
    p = plenum_params(boundary, pos, t_air, h)
    m, t, s = solve(p)
    return s['cold_W'], m


# --------------------------------------------------------------------------
# Cold-chamber heat balance
# --------------------------------------------------------------------------
# Air exchange with the room (estimates; chamber air volume ~3 L). 0.01 L/s = 12 air
# changes per hour. Plus OPEN_EXCHANGE through the permanently open feeding aperture.
LEAKS = {'tight_0.002Ls': 0.002e-3, 'nominal_0.01Ls': 0.01e-3, 'leaky_0.05Ls': 0.05e-3}
OPEN_EXCHANGE = 0.005e-3  # m3/s per open wedge (estimate; stratified cold air in a top opening)
DESIGN_LEAK = 'nominal_0.01Ls'


@functools.lru_cache(maxsize=None)
def velocity_for_h(h, height=0.012):
    """Invert the developing-flow channel estimate: loop velocity giving this h."""
    lo, hi = 0.05, 20.0
    for _ in range(80):
        mid = (lo+hi)/2
        if channel_h(mid, height)['h_developing_est_W_m2K'] < h:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def heat_balance(boundary, t_air, h, deck_k=0.065, fan_W=0.5, leak=DESIGN_LEAK,
                 open_wedges=1, n_tec=3, shaft_W=0.5, rh=0.5, frost_C=None, v=None,
                 height=0.012):
    b = BOUNDARIES[boundary]
    q_cov, m = wedge_flux(boundary, 'covered', t_air, h)
    q_open, _ = wedge_flux(boundary, 'open', t_air, h)
    a_lid = math.pi*BORE_D**2/4
    a_food = 12*m.area
    food = (12-open_wedges)*q_cov+open_wedges*q_open
    lid_nonfood = b['top']['covered']*(a_lid-a_food)*(b['room']-t_air)
    a_deck = a_lid-n_tec*0.040**2
    u_deck = 1/(1/h+DECK_T/deck_k+1/H_BAY)
    deck = u_deck*a_deck*(b['bay']-t_air)
    u_wall = 1/(1/h+WALL_T/deck_k+1/H_OUT)
    wall = u_wall*math.pi*BORE_D*COLD_WALL_H*(b['room']-t_air)
    mount = n_tec*0.010*(b['bay']-t_air)   # printed TEC retainer bridge, 0.01 W/K each (estimate)
    vdot = LEAKS[leak]+open_wedges*OPEN_EXCHANGE
    rho = air_props(b['room'])[0]
    sensible = rho*AIR_CP*vdot*(b['room']-t_air)
    frost_t = t_air-3.0 if frost_C is None else frost_C  # fin surface below mean air
    dw = max(0.0, humidity_ratio(b['room'], rh)-humidity_ratio(frost_t, 1.0))
    latent = rho*vdot*dw*H_SUBLIMATION
    frost_g_day = rho*vdot*dw*86400*1e3
    total = food+lid_nonfood+deck+wall+mount+fan_W+shaft_W+sensible+latent
    # air temperature sawtooth between fin banks (circumferential loop)
    v = velocity_for_h(h, height) if v is None else v
    vdot_loop = v*height*CHANNEL_W
    rho_c = air_props(t_air)[0]
    air_heat = total-fan_W  # heat picked up along the loop (fan heat at fan)
    saw = air_heat/(n_tec*rho_c*vdot_loop*AIR_CP)
    return dict(boundary=boundary, T_air_C=t_air, h_W_m2K=h, deck_k=deck_k, leak=leak,
                open_wedges=open_wedges, n_tec=n_tec, food_W=food, lid_nonfood_W=lid_nonfood,
                deck_W=deck, wall_W=wall, tec_mount_W=mount, fan_W=fan_W, shaft_W=shaft_W,
                leak_sensible_W=sensible, leak_latent_W=latent, frost_g_day=frost_g_day,
                total_W=total, loop_v_m_s=v, loop_flow_L_s=vdot_loop*1e3, air_sawtooth_K=saw)


# --------------------------------------------------------------------------
# TEC model: Qc = a I Tc - 0.5 I^2 R - K dT ; V = a dT + I R
# --------------------------------------------------------------------------
def fit_from_max(imax, vmax, dtmax, th_c):
    """Standard maximum-parameter fit (e.g. Lineykin & Ben-Yaakov; Luo)."""
    th = th_c+K0
    a = vmax/th
    r = vmax*(th-dtmax)/(imax*th)
    k = vmax*imax*(th-dtmax)/(2*th*dtmax)
    return dict(alpha_V_K=a, R_ohm=r, K_W_K=k)


def solve3(a, b):
    """Gaussian elimination for a 3x3 system."""
    m = [row[:]+[v] for row, v in zip(a, b)]
    for i in range(3):
        piv = max(range(i, 3), key=lambda r: abs(m[r][i]))
        m[i], m[piv] = m[piv], m[i]
        for r in range(3):
            if r != i:
                f = m[r][i]/m[i][i]
                m[r] = [x-f*y for x, y in zip(m[r], m[i])]
    return [m[i][3]/m[i][i] for i in range(3)]


def fit_lsq(points):
    """Linear least squares in (alpha, R, K) on Qc and V equations; equal weight per W/V."""
    rows, rhs = [], []
    for pt in points:
        tc, dt, i = pt['Tc']+K0, pt['Th']-pt['Tc'], pt['Current']
        rows.append([i*tc, -0.5*i*i, -dt]); rhs.append(pt['Qc'])
        if pt.get('Voltage') is not None:
            rows.append([dt, i, 0.0]); rhs.append(pt['Voltage'])
    ata = [[sum(r[i]*r[j] for r in rows) for j in range(3)] for i in range(3)]
    atb = [sum(r[i]*y for r, y in zip(rows, rhs)) for i in range(3)]
    a, r, k = solve3(ata, atb)
    return dict(alpha_V_K=a, R_ohm=r, K_W_K=k)


def tec_qc(f, i, tc_c, th_c):
    tc, dt = tc_c+K0, th_c-tc_c
    return f['alpha_V_K']*i*tc-0.5*i*i*f['R_ohm']-f['K_W_K']*dt


def tec_v(f, i, tc_c, th_c):
    return f['alpha_V_K']*(th_c-tc_c)+i*f['R_ohm']


def tec_fits(root):
    cp60 = fit_from_max(6.0, 15.4, 68.0, 27.0)
    cp60_pts = [dict(Th=27, Tc=7, Current=1.2, Voltage=3.3, Qc=6.0),
                dict(Th=27, Tc=-3, Current=1.2, Voltage=3.6, Qc=1.75),
                dict(Th=50, Tc=20, Current=1.2, Voltage=4.4, Qc=3.0)]
    tark_pts = json.loads((root/'electronics'/'tark-operating-points.json').read_text())['points']
    tark = fit_lsq(tark_pts)
    # Combined fit: graph readings + Qmax (dT 0, Imax) + dTmax (Qc 0, Imax, Vmax) at Th 27 C
    cp60_all = cp60_pts+[dict(Th=27, Tc=27, Current=6.0, Voltage=None, Qc=53.0),
                         dict(Th=27, Tc=-41, Current=6.0, Voltage=15.4, Qc=0.0)]
    cp60l = fit_lsq(cp60_all)
    checks = []
    for name, f, pts in (('CP60440_maxfit', cp60, cp60_all), ('CP60440_lsq', cp60l, cp60_all),
                         ('TARK_lsq', tark, tark_pts)):
        for pt in pts:
            checks.append(dict(module=name, Th=pt['Th'], Tc=pt['Tc'], I=pt['Current'],
                               Qc_ref=pt['Qc'], Qc_model=tec_qc(f, pt['Current'], pt['Tc'], pt['Th']),
                               V_ref=pt['Voltage'] if pt['Voltage'] is not None else '',
                               V_model=tec_v(f, pt['Current'], pt['Tc'], pt['Th'])))
    qmax_model = cp60['alpha_V_K']*6*(27+K0)-18*cp60['R_ohm']
    return dict(CP60440=dict(source='Same Sky product page/CP60 datasheet: Imax 6 A, Vmax 15.4 V, '
                             'dTmax 68 K, Qmax 53 W at Th 27 C; R 2.17 ohm', fit='max-parameter',
                             qmax_model_W=qmax_model, **cp60),
                CP60440_lsq=dict(source='least squares over CP60 page-10 graph readings (+/-1 W, '
                                 '+/-0.5 V) plus Qmax and dTmax conditions', fit='linear least squares',
                                 **cp60l),
                TARK=dict(source='TARK calculator excerpts, electronics/tark-operating-points.json '
                          '(all Tc 0 C; Th 30-40 C)', fit='linear least squares', **tark)), checks


def tec_operate(f, qc_req, t_fin_air, r_cs, t_hot_air, r_hs, imax):
    """Smallest current meeting qc_req per module with sink resistances.

    Tc = t_fin_air - qc_req*r_cs. Th from Qh = a I Th + I^2R/2 - K(Th-Tc),
    Th = t_hot_air + Qh*r_hs (closed form). Returns None if infeasible."""
    tc = t_fin_air-qc_req*r_cs
    a, r, k = f['alpha_V_K'], f['R_ohm'], f['K_W_K']
    best = None
    for n in range(1, int(imax*100)+1):
        i = n/100
        denom = 1-r_hs*a*i+r_hs*k
        if denom <= 0:
            break
        th = (t_hot_air+r_hs*(0.5*i*i*r-a*i*K0+k*tc))/denom  # deg C (a*i*Th uses K)
        # derivation in Kelvin: Th_K(1 - Rh a I + Rh K) = Ta_K + Rh(I^2R/2 + K Tc_K)
        th_k = (t_hot_air+K0+r_hs*(0.5*i*i*r+k*(tc+K0)))/denom
        th = th_k-K0
        qc = tec_qc(f, i, tc, th)
        if qc >= qc_req:
            v = tec_v(f, i, tc, th)
            p = i*v
            best = dict(I_A=i, V_V=v, P_W=p, Qc_W=qc, Qh_W=qc+p, Tc_C=tc, Th_C=th,
                        dT_K=th-tc, COP=qc/p)
            break
    return best


def sizing(balances, fits):
    rows = []
    for bal in balances:
        for module, f, imax in (('CP60440', fits['CP60440'], 6.0),
                                ('CP60440_lsq', fits['CP60440_lsq'], 6.0),
                                ('TARK', fits['TARK'], 3.9)):
            for n in (2, 3, 4):
                hb = bal[n]
                q = hb['total_W']/n
                t_fin = hb['T_air_C']-hb['air_sawtooth_K']/2
                t_hot = BOUNDARIES[hb['boundary']]['room']+5.0  # sink inlet air (estimate)
                for r_cs in (0.5, 1.0, 1.5, 2.0, 3.0):
                    for r_hs in (0.25, 0.4, 0.6, 1.0):
                        op = tec_operate(f, q, t_fin, r_cs, t_hot, r_hs, imax)
                        row = dict(boundary=hb['boundary'], T_air_C=hb['T_air_C'],
                                   h_W_m2K=hb['h_W_m2K'], deck_k=hb['deck_k'], leak=hb['leak'],
                                   module=module, n_tec=n, load_total_W=hb['total_W'],
                                   qc_per_tec_W=q, fin_air_C=t_fin, hot_air_C=t_hot,
                                   R_cold_K_W=r_cs, R_hot_K_W=r_hs, feasible=op is not None)
                        if op:
                            row.update(op)
                            row['tec_total_W'] = n*op['P_W']
                            row['heat_rejected_W'] = n*op['Qh_W']
                        rows.append(row)
    return rows


def brick(tec_W, aux_W=8.0, eff=0.90, margin=1.25):
    return (tec_W/eff+aux_W)*margin


# --------------------------------------------------------------------------
# Lumped pull-down transient
# --------------------------------------------------------------------------
def pulldown(boundary, t_air_set, h, n_tec, f, imax_pd, r_cs, r_hs, start_food, start_air,
             deck_k=0.065, leak=DESIGN_LEAK, fan_W=0.5, dt=5.0, hours=8.0):
    b = BOUNDARIES[boundary]
    m = Model(plenum_params(boundary, 'covered', t_air_set, h))
    d, kf = m.depth, BASE.food_k
    a_wedge = m.area
    ua_bot = 12*a_wedge/(1/h+BASE.floor/BASE.petg_k+d/(2*kf))
    ua_top = a_wedge*(11/(1/b['top']['covered']+d/(2*kf))+1/(1/b['top']['open']+d/(2*kf)))
    c_food = 0.480*3800+0.25*PETG_CP  # 480 g food + ~250 g tray (estimate)
    c_air = 500.0  # J/K: air, cold sinks, deck/wall surface layer (estimate)
    # parasitic UA/constant terms (from heat_balance, linear in T_air)
    hb0 = heat_balance(boundary, 0.0, h, deck_k, fan_W, leak, 1, n_tec)
    hb1 = heat_balance(boundary, -5.0, h, deck_k, fan_W, leak, 1, n_tec)
    nonfood0 = hb0['total_W']-hb0['food_W']
    nonfood1 = hb1['total_W']-hb1['food_W']
    slope = (nonfood0-nonfood1)/5.0
    t_hot = b['room']+5.0
    tf, ta, t = start_food, start_air, 0.0
    hist, t_mean4, t_mean5 = [], None, None
    while t <= hours*3600:
        q_food = ua_bot*(tf-ta)
        q_par = nonfood0+slope*(-ta)  # W at air temperature ta (linearised)
        q_in = q_food+q_par
        # TEC capacity at imax_pd with Tc = ta - Qc r_cs (fixed-point)
        qc = 0.0
        for _ in range(40):
            tc = ta-qc/n_tec*r_cs
            th = t_hot
            for _ in range(10):
                qh = tec_qc(f, imax_pd, tc, th)+imax_pd*tec_v(f, imax_pd, tc, th)
                th = t_hot+qh*r_hs
            qc_new = max(0.0, n_tec*tec_qc(f, imax_pd, tc, th))
            qc = 0.5*qc+0.5*qc_new
        if ta <= t_air_set and qc >= q_in:
            qc = q_in  # regulating: air held at setpoint
            ta_next = t_air_set
        else:
            ta_next = ta+(q_in-qc)*dt/c_air
        top_gain = ua_top*(b['room']-tf)
        tf += (top_gain-q_food)*dt/c_food
        ta = max(ta_next, t_air_set) if ta_next < t_air_set and qc == q_in else ta_next
        if t_mean4 is None and tf <= 4.0:
            t_mean4 = t/60
        if t_mean5 is None and tf <= 5.0:
            t_mean5 = t/60
        if abs(t % 900) < 1e-9:
            hist.append(dict(time_min=t/60, food_mean_C=tf, air_C=ta, qc_W=qc, q_in_W=q_in))
        t += dt
    within1 = next((x['time_min'] for x in hist if abs(x['food_mean_C']-tf) <= 1.0), None)
    return dict(food_mean_to_5C_min=t_mean5, food_mean_to_4C_min=t_mean4,
                within_1K_of_final_min=within1, final_food_C=tf, final_air_C=ta,
                tau_food_min=c_food/(ua_bot+ua_top)/60), hist


# --------------------------------------------------------------------------
def run(out):
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    direct_rows, direct_params = direct_sweep(out)
    chan = channel_table(out)
    plen_rows, plen_params = plenum_sweep(out)
    fits, fit_checks = tec_fits(root)
    write_csv(out/'tec_fit_checks.csv', fit_checks)

    # heat balance scenarios
    hb_rows, design_balances = [], []
    for bname in BOUNDARIES:
        for t_air in (2.0, -2.0, -5.0, -10.0):
            for h in (10.0, 15.0, 20.0, 30.0):
                for deck_k in (0.05, 0.065, 0.08, 0.12):
                    for leak in LEAKS:
                        for n in (2, 3, 4):
                            for fan in (0.3, 1.0):
                                hb_rows.append(heat_balance(bname, t_air, h, deck_k, fan, leak, 1, n))
    write_csv(out/'heat_balance.csv', hb_rows)

    # sizing: focus scenarios (fan 0.5 W, one open wedge)
    focus = []
    for bname in BOUNDARIES:
        for t_air in (-2.0, -5.0):
            for h in (10.0, 15.0, 20.0):
                for deck_k, leak in ((0.065, DESIGN_LEAK), (0.05, 'tight_0.002Ls'),
                                     (0.08, 'leaky_0.05Ls'), (0.12, DESIGN_LEAK)):
                    focus.append({n: heat_balance(bname, t_air, h, deck_k, 0.5, leak, 1, n)
                                  for n in (2, 3, 4)})
    size_rows = sizing(focus, fits)
    for r in size_rows:
        if r['feasible']:
            r['brick_W_incl_aux8_eff90_margin25'] = brick(r['tec_total_W'])
    write_csv(out/'tec_sizing.csv', size_rows)

    def pick(boundary, t_air, h, deck_k, leak, module, n, rcs, rhs):
        for r in size_rows:
            if (r['boundary'], r['T_air_C'], r['h_W_m2K'], r['deck_k'], r['leak'], r['module'],
                    r['n_tec'], r['R_cold_K_W'], r['R_hot_K_W']) == (boundary, t_air, h, deck_k,
                                                                     leak, module, n, rcs, rhs):
                return r
        raise KeyError((boundary, t_air, h, deck_k, leak, module, n, rcs, rhs))
    D = ('realistic', -5.0, 10.0)
    design = {}
    for label, args in {
        'A_CP60440maxfit_x3_Rcs1.0_Rhs0.4': (*D, 0.065, DESIGN_LEAK, 'CP60440', 3, 1.0, 0.4),
        'A_CP60440lsq_x3_Rcs1.0_Rhs0.4': (*D, 0.065, DESIGN_LEAK, 'CP60440_lsq', 3, 1.0, 0.4),
        'A_TARK_x3_Rcs1.0_Rhs0.4': (*D, 0.065, DESIGN_LEAK, 'TARK', 3, 1.0, 0.4),
        'B_CP60440maxfit_x4_Rcs1.0_Rhs0.4': (*D, 0.065, DESIGN_LEAK, 'CP60440', 4, 1.0, 0.4),
        'C_CP60440maxfit_x2_Rcs0.5_Rhs0.25': (*D, 0.065, DESIGN_LEAK, 'CP60440', 2, 0.5, 0.25),
        'D_CP60440maxfit_x3_Rcs2.0_Rhs0.6': (*D, 0.065, DESIGN_LEAK, 'CP60440', 3, 2.0, 0.6),
        'E_CP60440maxfit_x3_Rcs1.0_Rhs0.4_k0.12': (*D, 0.12, DESIGN_LEAK, 'CP60440', 3, 1.0, 0.4),
        'F_CP60440maxfit_x4_Rcs1.0_Rhs0.4_leaky_k0.08': (*D, 0.08, 'leaky_0.05Ls', 'CP60440', 4, 1.0, 0.4),
        'G_CP60440maxfit_x3_Rcs1.0_Rhs0.4_Tair-2_h15': ('realistic', -2.0, 15.0, 0.065, DESIGN_LEAK, 'CP60440', 3, 1.0, 0.4),
        'H_nominal_CP60440maxfit_x3_Rcs1.0_Rhs0.4': ('nominal', -5.0, 10.0, 0.065, DESIGN_LEAK, 'CP60440', 3, 1.0, 0.4),
    }.items():
        design[label] = pick(*args)

    # warmest wedge: mean plenum air + half the sawtooth between fin banks
    design_food = []
    for bname in BOUNDARIES:
        for t_air in (-2.0, -5.0):
            for h in (10.0, 15.0, 20.0):
                hb = heat_balance(bname, t_air, h, 0.065, 0.5, DESIGN_LEAK, 1, 3)
                for pos in ('covered', 'open'):
                    for label, ta in (('coldest_wedge', t_air-hb['air_sawtooth_K']/2),
                                      ('mean_air', t_air), ('warmest_wedge', t_air+hb['air_sawtooth_K']/2)):
                        p = plenum_params(bname, pos, t_air, h)
                        p = replace(p, cold=ta)
                        m, t, st = solve(p)
                        e = post(m, t, 1/h+p.floor/p.petg_k)
                        design_food.append(dict(boundary=bname, T_air_mean_C=t_air, h_W_m2K=h,
                                                loop_v_m_s=hb['loop_v_m_s'],
                                                sawtooth_K=hb['air_sawtooth_K'], position=pos,
                                                wedge=label, local_air_C=ta, layer_mean_C=st['mean_C'],
                                                top_surface_est_C=e['top_surface_max_C'],
                                                food_bottom_est_C=e['food_bottom_min_C']))
    write_csv(out/'plenum_design_food.csv', design_food)

    # open-position exposure: wedge starts at covered steady state, then sits open
    exposure = []
    for bname, t_air, h in (('realistic', -5.0, 10.0), ('realistic', -2.0, 15.0),
                            ('nominal', -5.0, 10.0)):
        pc = plenum_params(bname, 'covered', t_air, h)
        mc, tcov, _ = solve(pc)
        po = plenum_params(bname, 'open', t_air, h)
        mo = Model(po)
        dt = 60
        extra = mo.capacity/dt
        t = list(tcov)
        first5 = None
        for sec in range(0, 4*3600+1, dt):
            e = post(mo, t, 1/h+po.floor/po.petg_k)
            if first5 is None and e['top_surface_max_C'] > 5.0:
                first5 = sec/60
            if sec % 900 == 0:
                exposure.append(dict(boundary=bname, T_air_C=t_air, h_W_m2K=h, time_min=sec/60,
                                     layer_mean_C=sum(t)/len(t),
                                     top_surface_est_C=e['top_surface_max_C']))
            if sec < 4*3600:
                t, _, _ = mo.solve(rhs=[b+extra*v for b, v in zip(mo.rhs, t)], initial=t, extra=extra)
        exposure.append(dict(boundary=bname, T_air_C=t_air, h_W_m2K=h, time_min='top>5C at',
                             layer_mean_C='', top_surface_est_C=first5 if first5 is not None else 'never'))
    write_csv(out/'open_exposure.csv', exposure)

    # pull-down: realistic design point, 3 x CP60440 (conservative fit), Rcs 1.0, Rhs 0.4
    pd_rows, pd_hist = [], []
    for label, start_food, start_air in (('cold_start_food20_unit20', 20.0, 20.0),
                                         ('load_food20_running', 20.0, -5.0),
                                         ('load_food5_running', 5.0, -5.0),
                                         ('cold_start_food5_unit20', 5.0, 20.0)):
        for i_pd in (3.0, 4.0):
            res, hist = pulldown('realistic', -5.0, 10.0, 3, fits['CP60440'], i_pd, 1.0, 0.4,
                                 start_food, start_air)
            pd_rows.append(dict(case=label, I_pulldown_A=i_pd, **res))
            pd_hist.extend(dict(case=label, I_pulldown_A=i_pd, **x) for x in hist)
    write_csv(out/'pulldown.csv', pd_rows)
    write_csv(out/'pulldown_history.csv', pd_hist)

    # comparison table (warmest = estimated top surface max; mean = layer mean)
    comp = []
    for r in direct_rows:
        comp.append(dict(concept='direct40', boundary=r['boundary'], position=r['position'],
                         setting=f"Tc {r['cold_face_C']:g} C", mean_C=r['layer_mean_C'],
                         layer_max_C=r['layer_max_C'], warmest_top_est_C=r['top_surface_max_C'],
                         coldest_food_bottom_C=r['food_bottom_min_C'],
                         freeze_risk=r['food_bottom_min_C'] < FREEZE_C))
    for r in plen_rows:
        if r['h_W_m2K'] in (10.0, 15.0, 20.0, 30.0):
            comp.append(dict(concept='plenum', boundary=r['boundary'], position=r['position'],
                             setting=f"Tair {r['T_air_C']:g} C, h {r['h_W_m2K']:g}",
                             mean_C=r['layer_mean_C'], layer_max_C=r['layer_max_C'],
                             warmest_top_est_C=r['top_surface_max_C'],
                             coldest_food_bottom_C=r['food_bottom_min_C'],
                             freeze_risk=r['food_bottom_min_C'] < FREEZE_C))
    write_csv(out/'comparison.csv', comp)

    report = dict(
        status='Reduced-order simulation and estimates, 2026-10-25; no physical test.',
        provenance={'model_sha256': hashlib.sha256((Path(__file__).parent/'model.py').read_bytes()).hexdigest(),
                    'plenum_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        boundaries=BOUNDARIES, tec_fits=fits, design_points=design, open_exposure=exposure,
        pulldown=pd_rows, parameters=dict(direct=direct_params, plenum=plen_params),
        conventions={'layer_mean/max': 'FV thickness-averaged node (same as direct_contact.py)',
                     'top_surface_est': 'node + q_top*(d/2)/k_food; estimate of warmest point',
                     'food_bottom_est': 'cold boundary + q*(series R below food); ice indicator',
                     'heat_balance': 'W into cold chamber air at steady state',
                     'tec': 'Qc = a I Tc - I^2R/2 - K dT; V = a dT + I R; temperatures in K inside'})
    (out/'results.json').write_text(json.dumps(report, indent=2, default=str)+'\n')
    print(json.dumps(dict(tec_fits=fits, design={k: {x: v for x, v in d.items() if x in ('load_total_W','qc_per_tec_W','feasible','I_A','V_V','tec_total_W','Tc_C','Th_C','COP','heat_rejected_W','brick_W_incl_aux8_eff90_margin25')} for k, d in design.items()}, pulldown=pd_rows), indent=1, default=str))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=Path(__file__).parent/'plenum-output')
    run(ap.parse_args().output)
