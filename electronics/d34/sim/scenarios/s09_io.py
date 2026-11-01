"""S09 - Sensor and I/O interfaces (ngspice, full system powered).

1-Wire rise time on both buses with all probe leads at maximum length; lid / home / leak input levels through
their series resistors and leads; ESD into a lid lead (HBM and IEC 61000-4-2 contact) vs the ESP32 pin clamps;
ESP32 strapping pin levels at reset; THERMO_OK and DEFROST_FB logic levels.
"""
import numpy as np

from d34sim import common, flows, report
from d34sim import models as M_
from d34sim.circuit import Ctx
from d34sim.netlist import spice_node

TITLE = '1-Wire timing, digital input levels, ESD into leads, ESP32 strapping pins'


def run(env):
    chk = report.Checks('s09_io', env.outdir('s09_io'))
    L = env.limit
    N, R = flows.names(env)
    ctrl = env.cards['ctrl']
    dk = R['devkit']
    io = {ctrl.pin_func[(dk, p)]: net for p, net in ctrl.pins(dk).items()}
    nio = lambda gpio: spice_node('ctrl', io[gpio]).lower()
    vdd = 3.3
    vih, s_vih = L('esp32_vih_frac')
    vil, s_vil = L('esp32_vil_frac')
    # ------------------------------------------------------------------ 1-Wire
    ow_leads = [k for k, v in env.harness['leads'].items() if v['b'] == 'ext:ds18b20' and env.cards['pwr'].pins(v['a'][1])]
    onewire = {k: dict(pull='DC 0', c_in=25e-12) for k in ow_leads}
    first = {}
    for k in ow_leads:   # one sensor per bus pulls low 100-110 us, then releases
        net = env.cards['pwr'].net(env.harness['leads'][k]['a'][1], '2')
        if net not in first:
            first[net] = k
            onewire[k]['pull'] = 'PWL(0 0 100u 0 100.02u 1 110u 1 110.02u 0)'
    rows = []
    for corner in ('nom', 'max'):
        def make(nv):
            ctx = Ctx(dict(temp_C=40.0, length=corner, C=corner), no_vendor=nv)
            return common.build(env, ctx, brick=dict(v=24.0, t_close=None), onewire=onewire)
        bus_gpio = {net: [g for g, n in io.items() if n == net] for net in first}
        vecs = [f'v({nio(g[0])})' for g in bus_gpio.values() if g]
        c, info, r = common.run_robust(make, f's09_ow_{corner}', vecs, 'tran 20n 140u 0 50n', chk)
        t = r['time']
        for (net, g), v in zip(bus_gpio.items(), vecs):
            t_ds = common.first_cross(t, r[v], L('ds18b20_vih')[0], after=110e-6) - 110e-6
            t_esp = common.first_cross(t, r[v], vih * vdd, after=110e-6) - 110e-6
            vol = r[v][(t > 105e-6) & (t < 109e-6)].mean()
            rows.append(dict(bus=net, gpio=g[0], corner=corner, rise_to_ds_vih_us=t_ds * 1e6, rise_to_esp_vih_us=t_esp * 1e6, vol=vol,
                             probes=sum(env.harness['leads'][k].get('probes', 1) for k in ow_leads
                                        if env.cards['pwr'].net(env.harness['leads'][k]['a'][1], '2') == net)))
    chk.csv('onewire.csv', rows)
    w = max(rows, key=lambda x: x['rise_to_esp_vih_us'])
    s_t = L('onewire_sample_us')
    chk.add('ow_rise', '1-Wire release to ESP32 VIH (0.75 VDD), worst bus, all probe leads 0.5 m', w['rise_to_esp_vih_us'], s_t[0] - 2.0, '<=', 'us',
            f'{s_t[1]}; master releases ~2 us after slot start', corner=f"{w['bus']} ({w['probes']} probes, lead {w['corner']})", severity='functional')
    w = max(rows, key=lambda x: x['vol'])
    chk.add('ow_vol', '1-Wire low level while a DS18B20 pulls down (vs ESP32 VIL)', w['vol'], vil * vdd, '<=', 'V', s_vil, severity='functional')
    # ------------------------------------------------------------------ inputs, strapping, status levels (DC)
    def make_dc(nv):
        ctx = Ctx(dict(temp_C=40.0), no_vendor=nv, boot_pulls=True)
        leads = [k for k in ('LID', 'HOME', 'LEAK') if k in env.harness['leads']]
        c, info = common.build(env, ctx, brick=dict(v=24.0, t_close=None), extra_leads=leads)
        lid, home, leak = (info[k][0] if k in info else {} for k in ('LID', 'HOME', 'LEAK'))
        c.add('* lid switch closed (0.1 ohm + lead), home sensor open collector on (VOL ~0.2 V @ 0.33 mA), leak probe 47 kohm (wet)')
        if lid:
            c.add(f'Rlid {lid["1"]} {lid["2"]} 0.1')
        if home:
            c.add(f'Rhome {home["2"]} home_x 400', f'Vhome home_x {home["1"]} 0.07')
        if leak:
            c.add(f'Rleak {leak["1"]} {leak["2"]} 47k')
        elif lid and '3' in lid and '4' in lid:   # D34-2: basin-full probe shares the lid XH-4 (pins 3/4)
            c.add(f'Rleak {lid["3"]} {lid["4"]} 47k')
        return c, info
    want = ['IO27', 'IO23', 'IO39', 'IO0', 'IO2', 'IO12', 'IO15', 'IO5', 'IO36', 'IO26']
    vecs = [f'v({nio(g)})' for g in want if g in io] + [f'v({N["v3v3"]})']
    c, info, r = common.run_robust(make_dc, 's09_dc', vecs, 'tran 1u 2m 0 10u', chk)
    V = {g: float(r[f'v({nio(g)})'][-1]) for g in want if g in io}
    v33 = float(r[f'v({N["v3v3"]})'][-1])
    chk.add('lid_closed', f'Lid switch closed: level at the ESP32 pin ({io.get("IO27")})', V.get('IO27', np.nan), vil * v33, '<=', 'V', s_vil)
    chk.add('home_on', 'Home sensor active (open collector 0.2 V): level at the ESP32 pin', V.get('IO23', np.nan), vil * v33, '<=', 'V', s_vil)
    chk.add('strap_io12', 'Strapping: GPIO12 (MTDI) at reset must read 0 for 3.3 V flash (WROOM-32E)', V.get('IO12', np.nan), vil * v33, '<=', 'V',
            'ESP32 datasheet strapping: MTDI = 0 -> VDD_SDIO 3.3 V; ' + s_vil, severity='functional')
    chk.add('strap_io0', 'Strapping: GPIO0 at reset reads 1 (SPI boot) with the panel button released', V.get('IO0', np.nan), vih * v33, '>=', 'V',
            s_vih, severity='functional')
    chk.note('Strap levels at reset: ' + ', '.join(f'{g} {V[g]:.2f} V' for g in ('IO0', 'IO2', 'IO5', 'IO12', 'IO15') if g in V) +
             '. GPIO5/GPIO15 only set SDIO timing / boot-log; GPIO2 is don\'t-care when GPIO0 = 1.')
    leak_net = io.get('IO39')
    rpu = [M_.parse_value(ctrl.comps[r]['value']) for r in ctrl.comps if r.startswith('R')
           for nets in [set(ctrl.pins(r).values())] if 'LEAK' in nets and N['v3v3'] and any(x.upper() == '+3V3' for x in nets)]
    rpu = rpu[0] if rpu else 100e3
    leak_rows = [dict(probe_ohm=rp, adc_V=3.3 * rp / (rpu + rp), pullup_ohm=rpu) for rp in (1e3, 10e3, 47e3, 100e3, 470e3, 1e6, 1e9)]
    chk.csv('leak_divider.csv', leak_rows)
    chk.note(f"Basin-full probe (ADC, {rpu / 1e3:.0f} k pull-up): 47 k wet -> {V.get('IO39', float('nan')):.2f} V simulated; dry -> 3.3 V. "
             'Divider table in leak_divider.csv.')
    # ------------------------------------------------------------------ ESD into an input lead (analytic)
    # A discharge into a lead reaches the ESP32 pin through the 1 k series resistor and the pin's clamp diodes; with no
    # TVS the peak pin current is bounded by V_esd / (R_gun + R_series). (A SPICE transient was not used: the pin
    # clamp and rail impedances of the ESP32 at ns time scales are not modelled credibly.)
    r_ser = [M_.parse_value(ctrl.comps[x]['value']) for x in ctrl.comps
             if x.startswith('R') and io.get('IO27') in ctrl.pins(x).values() and 'LID' in ctrl.pins(x).values()]
    r_ser = r_ser[0] if r_ser else 1e3
    esd_rows = []
    for name, (vesd, cesd, resd) in {'HBM 2 kV': (2000, 100e-12, 1500), 'IEC 61000-4-2 2 kV contact': (2000, 150e-12, 330),
                                     'IEC 61000-4-2 8 kV contact': (8000, 150e-12, 330)}.items():
        esd_rows.append(dict(event=name, i_pin_pk_est=vesd / (resd + r_ser), r_series=r_ser))
    chk.csv('esd.csv', esd_rows)
    lim, s = L('esp32_hbm_pin_current')
    hbm = esd_rows[0]
    chk.add('esd_hbm', 'HBM 2 kV on a lid lead: peak current into the ESP32 pin clamp (through the 1 k series resistor)', hbm['i_pin_pk_est'], lim, '<=',
            'A', s, severity='rating', detail='analytic bound V/(R_gun + R_series)')
    for row in esd_rows[1:]:
        chk.add(f"esd_iec_{row['event'].split()[-3]}", f"{row['event']} on a lid lead: peak current into the ESP32 pin clamp", row['i_pin_pk_est'], lim, '<=', 'A',
                s + '; no TVS on the inputs', severity='rating', advisory=True,
                detail='leads are inside the enclosure; exposure is only during servicing. Add a TVS array (e.g. per-input 5 V TVS) if leads are touchable')
    # ------------------------------------------------------------------ status levels
    th = V.get('IO36', np.nan)
    chk.add('thermo_ok_level', 'THERMO_OK (thermostats closed) at the ESP32 input vs VIH (digital read)', th, vih * v33, '>=', 'V', s_vih,
            severity='functional', detail='margin is small; reading IO36 with the ADC (threshold ~1.4 V) avoids it (see S11 Monte Carlo)')
    return chk
