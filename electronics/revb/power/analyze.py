#!/usr/bin/env python3
"""Analytical screening, not a switching/loop model or hardware qualification."""
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def check(circuit):
    p = {x['ref']: x for x in circuit['parts']}
    assert len(p) == len(circuit['parts']), 'duplicate reference'
    assert circuit['input']['net'] == 'SYS_20V'
    assert 'OFF for 5/9/12/15V' in circuit['input']['dependency']
    results = {}
    for rail, output, demand in [(1, '+3V3', 1.0), (2, '+12V', .5)]:
        u, l = p[f'UP{rail}'], p[f'LP{rail}']
        sw, bst = f'PWR_SW{rail}', f'PWR_BST{rail}'
        fb = output if rail == 1 else 'PWR_FB12'
        assert u['pins'] == {'1': fb, '2': 'SYS_20V', '3': 'SYS_20V', '4': 'GND', '5': sw, '6': bst}
        assert l['pins'] == {'1': sw, '2': output}
        b = (rail - 1) * 10
        assert p[f'CP{b+4}']['pins'] == {'1': bst, '2': sw}, 'bootstrap must float on SW'
        vin_max = max(circuit['input']['qualification_range_V'])
        assert vin_max < u['vin_operating_max_V']
        assert u['output_budget_A'] >= demand
        for i in [1, 2, 3]:
            cap = p[f'CP{b+i}']
            assert cap['pins'] == {'1': 'SYS_20V', '2': 'GND'}
            assert cap['voltage_V'] >= 1.5 * vin_max, 'input capacitor voltage margin'
        caps = [p[f'CP{b+i}'] for i in ((5, 6, 7, 8) if rail == 1 else (5, 6, 7))]
        vo = 3.3 if rail == 1 else .8 * (1 + p['RP1']['resistance_ohm'] / p['RP2']['resistance_ohm'])
        if rail == 2:
            assert 11.4 < vo < 12.6, 'fan feedback ratio outside 12V +/-5%'
        for c in caps:
            assert c['pins'] == {'1': output, '2': 'GND'}
            assert c['voltage_V'] >= 1.5 * vo
        # Bias and temperature factors below are assumptions, NOT guaranteed MPN minima.
        c_eff = sum(c['capacitance_F'] * (1 - c['tolerance']) for c in caps) * .5 * .85
        l_min = l['inductance_H'] * (1 - l['tolerance']) * .8
        # Additional 20% bias/temperature L loss and -6% frequency spread.
        f_min = u['switching_frequency_Hz'] * .94
        ripple = vo * (1 - vo / vin_max) / (l_min * f_min)
        startup_current = sum(c['capacitance_F'] * (1 + c['tolerance']) for c in caps) * vo / .004
        # 4ms is typical, not a guaranteed lower bound on soft start.
        i_peak = demand + ripple / 2
        startup_peak = i_peak + startup_current
        assert startup_peak < 2.5, 'minimum IC peak-current threshold exceeded in assumed startup'
        assert l['isat_A_typ'] * .8 > 3.1, '20% derated typical Isat lacks current-limit headroom'
        rms = math.sqrt(demand*demand + ripple*ripple / 12)
        assert rms < l['irms_A_typ'] * .8
        conduction = (demand*demand + ripple*ripple/12) * (.125*vo/20 + .068*(1-vo/20))
        inductor_loss = rms*rms*l['dcr_ohm']*(1+l['dcr_tolerance'])*1.3
        output_ripple = ripple * (.010 + 1/(8*f_min*c_eff))
        ton = vo/vin_max/(u['switching_frequency_Hz']*1.06)
        assert ton > 80e-9, 'typical minimum on-time screening failed'
        assert output_ripple < vo*.02, 'CCM ripple estimate exceeds 2%'
        cin_eff = sum(p[f'CP{b+i}']['capacitance_F']*.9 for i in (1, 2))*.7*.85
        assert cin_eff >= 10e-6
        droop = .7*10e-6/c_eff + .7*.010
        if rail == 1:
            assert 3.27 - droop - .03 > 3.0, '10us assumed response plus 30mV trace budget violates ESP32 minimum'
        results[output] = dict(
            nominal_V=vo, load_budget_A=demand, worst_assumed_ripple_A=ripple,
            peak_A=i_peak, startup_peak_typical_soft_start_A=startup_peak,
            inductor_rms_A=rms, assumed_effective_output_F=c_eff,
            assumed_effective_input_F=cin_eff, minimum_assumed_on_time_s=ton,
            ccm_ripple_estimate_V=output_ripple,
            typical_25C_MOS_conduction_W=conduction,
            hot_inductor_copper_estimate_W=inductor_loss,
            total_loss_assuming_80_to_90_percent_efficiency_W=[vo*demand*(1/.9-1), vo*demand*(1/.8-1)],
            instantaneous_step_0p7A_10us_droop_V=droop)
    assert p['RP1']['pins'] == {'1': '+12V', '2': 'PWR_FB12'}
    assert p['RP2']['pins'] == {'1': 'PWR_FB12', '2': 'GND'}
    assert p['CP18']['pins'] == p['RP1']['pins']
    # Include reference and both resistor tolerance corners, without hiding nominal offset.
    resistor_corners = [[p[r]['resistance_ohm']*(1+s*p[r]['tolerance']) for s in (-1, 1)]
                        for r in ('RP1', 'RP2')]
    volts = [v*(1+r1/r2) for v, r1, r2 in itertools.product([.792, .808], *resistor_corners)]
    assert min(volts) > 11.4 and max(volts) < 12.6
    results['fan_tolerance_range_V'] = [min(volts), max(volts)]
    results['maximum_rail_input_power_at_80_percent_W'] = sum(x['nominal_V']*x['load_budget_A']/.8 for x in [results['+3V3'], results['+12V']])
    results['limits'] = [
        'Inductor Isat/Irms are typical at 25C; 20% derating is an assumption, not a guarantee',
        'Capacitor bias retention is assumed 70% input and 50% output, plus tolerance and -15% temperature',
        'Oscillator absolute tolerance is not specified in cited datasheet; only published +/-6% spread included',
        'Soft-start, MOS resistances, 80ns minimum on time and thermal resistance are typical',
        'CCM ripple equations do not predict AP63203 PFM burst ripple at light ESP32 load; AP63201 is forced PWM',
        'No loop stability, fan startup waveform, PCB thermal, EMI, overshoot or PD transient validation',
    ]
    return results


if __name__ == '__main__':
    result = check(json.loads((HERE/'circuit.json').read_text()))
    (HERE/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
