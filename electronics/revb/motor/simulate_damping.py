#!/usr/bin/env python3
"""Executed passive RLC comparison only: no switching A4988 or PD source model."""
import json
import gzip
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'simulation'


def run_case(name, vin, rd, c=80e-6, source_r=.02, inductance=10e-6, esr=.03):
    # 1ns hotplug and original worst corner retained for an independent regression.
    net = f'''Motor supply passive damping study / {name}
Vsrc src 0 PWL(0 0 1n {vin})
Rwire src wire {source_r}
Lwire wire pre {inductance}
Rdamp pre vmot {max(rd,1e-9)}
Resr vmot cap {esr}
Cbulk cap 0 {c}
.options reltol=1e-6 abstol=1e-10
.control
set wr_singlescale
set wr_vecnames
tran 50n 2m
let damping_power = (v(pre)-v(vmot))*i(Lwire)
meas tran vmot_peak MAX v(vmot)
meas tran inrush_peak MAX i(Lwire)
meas tran damping_peak MAX damping_power
meas tran damping_energy INTEG damping_power
wrdata {name}.txt v(vmot) i(Lwire) damping_power
quit
.endc
.end
'''
    (OUT/(name+'.cir')).write_text(net)
    proc = subprocess.run(['ngspice','-b',name+'.cir'], cwd=OUT, capture_output=True, text=True)
    log=proc.stdout+proc.stderr
    (OUT/(name+'.log')).write_text(log)
    if proc.returncode or 'failed' in log.lower(): raise RuntimeError(log)
    waveform = OUT/(name+'.txt')
    with gzip.open(OUT/(name+'.txt.gz'), 'wb') as target:
        target.write(waveform.read_bytes())
    waveform.unlink()
    def number(key):
        m=re.search(r'^'+key+r'\s*=\s*([\d.eE+-]+)',log,re.M)
        if not m: raise ValueError(key+': '+log)
        return float(m[1])
    return dict(case=name, vin_V=vin, damping_ohm=rd, bulk_F=c,
        vmot_peak_V=number('vmot_peak'), inrush_peak_A=number('inrush_peak'),
        damping_peak_W=number('damping_peak'), damping_energy_J=number('damping_energy'))


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    cases=[run_case('original_24V',24,0), run_case('original_20V',20,0),
           run_case('damped_24V',24,.99), run_case('damped_21V',21,.99),
           run_case('damped_20V',20,.99), run_case('damped_21V_120u',21,.99,c=120e-6)]
    assert abs(cases[0]['vmot_peak_V']-43.27801)<.02
    assert abs(cases[1]['vmot_peak_V']-36.06503)<.02
    for c in cases[2:]: assert c['vmot_peak_V'] <= c['vin_V']*1.001
    summary=dict(status='PASS: passive model comparison; resistor pulse qualification OPEN',
        model='Original worst-case bulk-only RLC model plus motor-branch series resistor at -1%; source not current limited',
        unmodeled=['local ceramic resonances','contact bounce','PD renegotiation','motor switching','regeneration','resistor pulse survival'],
        cases=cases, tool=subprocess.check_output(['ngspice','--version'],text=True))
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(cases,indent=2))
