"""S11 - Monte Carlo / worst case on the critical tolerance chains (python, seeded).

Watchdog timeout, latch re-open delay vs K1 release (the interlock margin), THERMO_OK digital level vs ESP32 VIH,
relay pick-up with a hot coil. Component values are read from the netlist; tolerance ranges are datasheet values or
labelled assumptions (see each check).
"""
import numpy as np

from d34sim import logic, models as M, report

TITLE = 'Monte Carlo / worst case: watchdog, interlock margin, THERMO_OK level, relay pick-up'

NMC = 200000


def run(env):
    chk = report.Checks('s11_montecarlo', env.outdir('s11_montecarlo'))
    L = env.limit
    rng = np.random.default_rng(env.seed + 11)
    P, probs = logic.extract(env)
    if P is None:
        chk.add('topology', 'safety chain found', 0, 1, '==', '', 'integrity', severity='integrity')
        return chk
    S = logic.Sample(P, NMC, rng)
    # ---------------------------------------------------------------- watchdog
    import json as _json
    FC = _json.loads((env.d34 / 'sim' / 'firmware_contract.json').read_text())
    tw = S.tw
    band = FC['wdt_band_s']
    ok_lo = chk.add('wdt_band_lo', f'Watchdog timeout minimum over tolerances vs the README band lower end {band[0]} s', float(tw.min()), band[0], '>=',
                    's', f"README D34-3 claim; {P['K_source']}; R 1 %, C +-10 %, -5 % bias, +-5 % temp, +-10 % pin-leakage allowance (assumed)",
                    severity='functional', advisory=True,
                    detail=f'p0.1 {np.percentile(tw, 0.1):.3f} s, median {np.median(tw):.3f} s, p99.9 {np.percentile(tw, 99.9):.3f} s')
    chk.add('wdt_band_hi', f'Watchdog timeout maximum over tolerances vs the README band upper end {band[1]} s', float(tw.max()), band[1], '<=', 's',
            'README D34-3 claim', severity='functional', advisory=True)
    kick = 1.0 / FC['kick_hz_min']
    chk.add('wdt_min', f'Watchdog timeout minimum vs the kick period ({FC["kick_hz_min"]} Hz -> {kick * 1e3:.0f} ms), 2x margin', float(tw.min()),
            2 * kick, '>', 's', 'README firmware contract (kick >= 10 Hz); project 2x margin for loop jitter', severity='functional')
    rext, s = L('hc123_rext_max')
    chk.add('wdt_rext', 'Watchdog REXT vs the largest recommended value', P['R_wd'], rext, '<=', 'ohm', s, severity='rating', advisory=True)
    # ---------------------------------------------------------------- latch re-open delay vs K1 release
    rel = P['relay']
    if P.get('le_mode') == 'hc123':
        t_le = S.tw2
        lb = FC['latch_delay_band_s']
        chk.add('latch_band_lo', f'Latch re-open delay (74HC123 half 2) minimum vs README band {lb[0]} s', float(t_le.min()), lb[0], '>=', 's',
                'README D34-3 claim', severity='functional', advisory=True)
        chk.add('latch_band_hi', f'Latch re-open delay maximum vs README band {lb[1]} s', float(t_le.max()), lb[1], '<=', 's', 'README D34-3 claim',
                severity='functional', advisory=True)
        chk.add('latch_vs_fw_wait', f'Latch re-open delay maximum vs the firmware wait of {FC["wait_after_tec_en_low_s"]} s before changing DEFROST_REQ',
                float(t_le.max()), FC['wait_after_tec_en_low_s'], '<=', 's', 'README firmware contract', severity='functional')
    else:
        t_le = S.tau_le * np.log(3.3 / (3.3 - S.vt_le))
    i0 = (12.0 * rng.uniform(0.97, 1.03, NMC) - S.vce) / S.rc
    t_dec = (S.L1 / S.rc) * np.log((i0 + S.vf1 / S.rc) / (S.irel1 + S.vf1 / S.rc))
    t_rel = t_dec + S.tm_rel1
    margin = t_le - t_rel
    chk.add('interlock_margin', 'Latch re-opens only after K1 has opened: min(latch delay - K1 release) over tolerances', float(margin.min()) * 1e3, 0.0,
            '>', 'ms', 'safety requirement (D34 interlock); K1 release = coil decay through its clamp to the drop-out current + armature travel',
            severity='safety', detail=f'latch delay {t_le.min() * 1e3:.1f}-{t_le.max() * 1e3:.1f} ms; K1 release {t_rel.min() * 1e3:.1f}-{t_rel.max() * 1e3:.1f} ms '
                                      f'(coil L {rel["L"][0]}-{rel["L"][2]} H assumed, clamp {"diode + zener" if P.get("k1_vz") else "diode"})')
    rel_i = 12.0 / rel['r_coil']
    rc_min = rel['r_coil'] * 0.9 * (1 + 0.00393 * (40 - 23))
    if P.get('le_mode') == 'hc123':
        t_le_wc = P['K_range'][0] * 0.98 * P['R_ld'] * 0.99 * P['C_ld'] * 0.9 * 0.9 * 0.95 * 0.9
        le_txt = f"latch {t_le_wc * 1e3:.0f} ms (K {P['K_range'][0]}, R -1 %, C -10 % -10 % -5 %, leakage -10 %)"
    else:
        t_le_wc = P['R_le'] * 0.99 * P['C_le'] * 0.9 * 0.95 * 0.95 * np.log(3.3 / (3.3 - 0.94))
        le_txt = f"latch {t_le_wc * 1e3:.1f} ms (RC, LE threshold 0.94 V)"
    i0_wc = (12.36 - 0.13) / rc_min
    vf_wc = (0.25 if (P.get('k1_flyback_mpn') or '').upper().startswith('1N58') else 0.6) + (13.8 if P.get('k1_vz') else 0.0)
    t_rel_wc = (rel['L'][2] / rc_min) * np.log((i0_wc + vf_wc / rc_min) / (0.10 * rel_i + vf_wc / rc_min)) + 4e-3
    chk.add('interlock_margin_wc', 'Worst case (all tolerances stacked): latch re-open delay minus K1 release', (t_le_wc - t_rel_wc) * 1e3, 0.0, '>',
            'ms', 'safety requirement; K1 release uses ASSUMED coil L 2 H and 4 ms armature travel (to be measured)', severity='safety',
            detail=f"{le_txt} vs K1 release {t_rel_wc * 1e3:.1f} ms (L 2 H, coil R -10 %, drop-out 10 %, clamp {vf_wc:.2f} V, 4 ms travel)")
    if P.get('uv'):
        chk.add('uv_trip_mc', 'UV cut-off trip threshold over tolerances (TL431A Vref 2.44-2.55 V, R 1 %, BC327 VCE(sat) 0.1-0.3 V): range',
                float(S.uv_trip.min()), 9.37 - 0.25, '>=', 'V', 'README claim 9.37 +-0.2 V (+0.05 V allowance)', severity='functional', advisory=True,
                detail=f'trip {S.uv_trip.min():.2f}-{S.uv_trip.max():.2f} V, recover {S.uv_rec.min():.2f}-{S.uv_rec.max():.2f} V, '
                       f'hysteresis >= {(S.uv_rec - S.uv_trip).min():.2f} V')
        chk.add('uv_trip_mc_hi', 'UV cut-off trip threshold, maximum over tolerances', float(S.uv_trip.max()), 9.37 + 0.25, '<=', 'V',
                'README claim 9.37 +-0.2 V (+0.05 V allowance)', severity='functional', advisory=True)
    # ---------------------------------------------------------------- THERMO_OK digital level
    tec = env.cards['tec']
    k1 = P['chain']['K1']['coil_hi']
    rt = [r for r, c in tec.comps.items() if r.startswith('R') and k1 in tec.pins(r).values()]
    mid = [n for n in tec.pins(rt[0]).values() if n != k1][0] if rt else None
    rb = [r for r, c in tec.comps.items() if r.startswith('R') and set(tec.pins(r).values()) == {mid, 'GND'}] if mid else []
    if rt and rb:
        r1 = M.parse_value(tec.comps[rt[0]]['value']) * rng.uniform(0.99, 1.01, NMC)
        r2 = M.parse_value(tec.comps[rb[0]]['value']) * rng.uniform(0.99, 1.01, NMC)
        v12 = 12.0 * rng.uniform(0.97, 1.03, NMC) - rng.uniform(0.0, 0.05, NMC)   # +-3 % regulation band, lead + 4 thermostat contacts
        vdd = 3.3 * rng.uniform(0.97, 1.03, NMC)                                    # AMS1117 full-temperature tolerance (3.201-3.399 V)
        vth = v12 * r2 / (r1 + r2)
        vih = L('esp32_vih_frac')[0] * vdd
        fail = vth < vih
        worst_v = 12.0 * 0.97 - 0.05
        wc = worst_v * M.parse_value(tec.comps[rb[0]]['value']) * 0.99 / (M.parse_value(tec.comps[rt[0]]['value']) * 1.01 +
                                                                         M.parse_value(tec.comps[rb[0]]['value']) * 0.99)
        chk.add('thermo_ok_vih_wc', 'THERMO_OK worst case (12 V -3 %, divider 1 %, VDD +3 %) vs ESP32 VIH = 0.75 VDD', wc - 0.75 * 3.399, 0.0, '>=', 'V',
                L('esp32_vih_frac')[1] + '; regulation bands: TRACO/Murata +-2-3 %, AMS1117 3.201-3.399 V', severity='functional',
                detail=f'Monte Carlo: {fail.mean() * 100:.2f} % of {NMC} below VIH; level {vth.min():.2f}-{vth.max():.2f} V; divider '
                       f'{rt[0]} {tec.comps[rt[0]]["value"]} / {rb[0]} {tec.comps[rb[0]]["value"]}' +
                       (f'. Fix: read IO36 as ADC (threshold ~1.4 V) or raise {rb[0]}' if fail.any() else ''))
        chk.add('thermo_ok_max', 'THERMO_OK maximum vs ESP32 pin limit VDD + 0.3 V', float((vth - vdd).max()), 0.3, '<=', 'V',
                L('esp32_pin_over')[1], severity='rating')
        # ---- at the ESP32 pin: series resistor to IO36 and the clamp diode's reverse leakage (plus ESP32 input leakage)
        ctrl = env.cards['ctrl']
        dk = P['refs']['devkit']
        io_nets = set(ctrl.pins(dk).values())
        rser = [r for r in ctrl.comps if (M.match(env.table, ctrl.comps[r]) or {}).get('model') == 'resistor'
                and mid in ctrl.pins(r).values() and (set(ctrl.pins(r).values()) - {mid}) & io_nets]
        if rser:
            pin_net = (set(ctrl.pins(rser[0]).values()) - {mid}).pop()
            clamp = [r for r in ctrl.comps if (M.match(env.table, ctrl.comps[r]) or {}).get('model') == 'diode'
                     and set(ctrl.pins(r).values()) == {pin_net, 'GND'}]
            r12 = M.parse_value(ctrl.comps[rser[0]]['value'])
            ds = env.datasheets.get('parts', {}).get('BAT42', {}).get('values', {})
            ir_typ = ds.get('IR_typ_curve_VR3V', {}).get('value', {'25C': 0.08, '50C': 0.65, '75C': 4.5})
            # max = 2 x typical (datasheet max 0.5 uA vs typ 0.25 uA at 25 C / 25 V), +30 % graph-reading allowance;
            # 40 C by log interpolation between the 25 and 50 C curve points
            ir40 = np.exp(np.log(ir_typ['25C']) + (40 - 25) / 25 * (np.log(ir_typ['50C']) - np.log(ir_typ['25C']))) * 2 * 1.3 * 1e-6
            ir75 = ir_typ['75C'] * 2 * 1.3 * 1e-6
            iesp = 50e-9
            vs_uv = 0.3 if P.get('uv') else 0.0      # BC327 VCE(sat) max in the loop feed
            r1n, r2n = M.parse_value(tec.comps[rt[0]]['value']), M.parse_value(tec.comps[rb[0]]['value'])
            v_wc = (12.0 * 0.97 - 0.05 - vs_uv) * r2n * 0.99 / (r1n * 1.01 + r2n * 0.99)
            rth = (r1n * r2n) / (r1n + r2n)
            vih_max = L('esp32_vih_frac')[0] * 3.399
            for tc, ir, adv in ((40, ir40, False), (75, ir75, True)):
                vin = v_wc - (ir + iesp) * (r12 + rth)
                chk.add(f'thermo_ok_in_high_{tc}C', f'THERMO_OK_IN high level at IO36 through {rser[0]} {ctrl.comps[rser[0]]["value"]} with '
                        f'{clamp[0] if clamp else "clamp"} leakage at {tc} C + ESP32 input leakage vs VIH (0.75 x VDD max 3.399 V)', vin, vih_max, '>=',
                        'V', 'ESP32 VIH 0.75 VDD; BAT42 IR (Vishay Fig. 3 typ x2 max, +30 %); 12 V -3 %, divider 1 %, BC327 0.3 V', severity='functional',
                        advisory=adv, detail=f'leakage {ir * 1e6:.2f} uA; drop {(ir + iesp) * (r12 + rth) * 1e3:.0f} mV; worst divider output {v_wc:.2f} V'
                        + ('; above the 40 C bay limit: shown for margin' if adv else ''))
    # ---------------------------------------------------------------- relay pick-up with hot coil
    vcoil = 12.0 * rng.uniform(0.97, 1.03, NMC) - S.vce - rng.uniform(0.0, 0.05, NMC)
    r_hot = rel['r_coil'] * rng.uniform(0.9, 1.1, NMC) * (1 + 0.00393 * (40 + rng.uniform(0, 35, NMC) - 23))
    i_coil = vcoil / r_hot
    i_op = L('g2rl_must_operate_frac')[0] * 12.0 / rel['r_coil']
    chk.add('relay_pickup_mc', 'Relay coil current (12 V band, ULN VCE(sat), coil R +-10 %, coil 40-75 C) vs must-operate current: fraction below',
            float((i_coil < i_op).mean()), 0.0, '<=', 'fraction', L('g2rl_must_operate_frac')[1], severity='functional',
            detail=f'min {i_coil.min() * 1e3:.1f} mA vs {i_op * 1e3:.1f} mA; must-operate is the guaranteed maximum, typical parts pick up lower')
    # ---------------------------------------------------------------- plots / CSV
    report.plot(chk.outdir / 'mc_histograms.png', 'S11 Monte Carlo distributions', [
        dict(ylabel='count', traces=[(np.histogram(tw, 60)[1][:-1], np.histogram(tw, 60)[0], 'watchdog timeout (s)')]),
        dict(ylabel='count', traces=[(np.histogram(margin * 1e3, 60)[1][:-1], np.histogram(margin * 1e3, 60)[0], 'latch delay - K1 release (ms)')]),
    ], xlabel='value', xscale=1.0)
    chk.csv('mc_summary.csv', [dict(quantity=q, p0=float(np.min(x)), p001=float(np.percentile(x, 0.1)), p50=float(np.median(x)),
                                    p999=float(np.percentile(x, 99.9)), p100=float(np.max(x)))
                               for q, x in (('watchdog_s', tw), ('latch_delay_ms', t_le * 1e3), ('k1_release_ms', t_rel * 1e3),
                                            ('interlock_margin_ms', margin * 1e3), ('relay_coil_mA', i_coil * 1e3))])
    chk.note(f'{NMC} samples, seed {env.seed + 11}. Distributions are uniform over the stated ranges (worst-case-leaning, not statistical claims).')
    return chk
