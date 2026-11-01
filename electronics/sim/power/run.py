#!/usr/bin/env python3
"""Offline, stdlib-only power study. Exit status is suite integrity, not qualification."""
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PCB = ROOT / 'electronics/pcb'
IQ = 80e-6
THETA = 184.0


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    """Same-filesystem atomic publication: never expose a partially written JSON."""
    text = json.dumps(value, indent=2, allow_nan=False) + '\n'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as f:
            temporary = Path(f.name)
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def schematic_check(root):
    components = root.findall('components/comp')
    require(len(components) == 54, 'Expected cleared 54-component schematic')
    comps = {c.attrib['ref']: c for c in components}
    require(len(comps) == 54, 'Duplicate component reference')
    nets = {}
    for net in root.findall('nets/net'):
        for node in net.findall('node'):
            key = (node.attrib['ref'], node.attrib['pin'])
            require(key not in nets, f'Duplicate pin {key}')
            nets[key] = net.attrib['name'].removeprefix('/')
    expected = {
        'U2': ('AP2112K-3.3TRG1', 'C51118', {'1': '+5V', '2': 'GND', '3': '+5V', '5': '+3V3'}),
        'C1': ('10u 25V', 'C15850', {'1': '+5V', '2': 'GND'}),
        'C2': ('10u 25V', 'C15850', {'1': '+3V3', '2': 'GND'}),
        'C4': ('10u 25V', 'C15850', {'1': '+3V3', '2': 'GND'}),
        'C10': ('100u 50V EEUFR1H101B', 'C713402', {'1': 'VMOT', '2': 'GND'}),
        'C11': ('10u 25V', 'C15850', {'1': '+12V', '2': 'GND'}),
    }
    for ref in ['C3', 'C6', 'C7', 'C9']:
        expected[ref] = ('100n', 'C14663', {'1': '+3V3', '2': 'GND'})
    result = {}
    for ref, (value, code, pins) in expected.items():
        comp = comps[ref]
        require(comp.findtext('value') == value, f'{ref} value changed')
        require(comp.findtext("fields/field[@name='LCSC']") == code, f'{ref} exact code changed')
        for pin, net in pins.items():
            require(nets.get((ref, pin)) == net, f'{ref}.{pin} connectivity changed')
        result[ref] = {'value': value, 'LCSC': code, 'pins': pins}
    for ref, pins in {'J1': {'1': 'VMOT', '2': 'GND'},
                      'J2': {'1': 'GND', '2': '+5V', '3': '+12V'},
                      'J15': {'1': 'VMOT', '2': 'GND', '7': '+3V3', '8': 'GND'},
                      'U1': {'2': '+3V3'}}.items():
        for pin, net in pins.items():
            require(nets.get((ref, pin)) == net, f'{ref}.{pin} rail changed')
    require('unconnected' in nets.get(('U2', '4'), ''), 'U2 NC now connected')
    return result


def source_checks():
    manifest = json.loads((PCB / 'checksums.json').read_text())
    # Frozen manifest digest is a deliberate review gate, not a hidden assumption.
    require(sha(PCB / 'checksums.json') ==
            '9fa46fefed298d092bc83b532faa0848905522ade1cb9342ddb9abefd91d803f',
            'Frozen review manifest changed; re-review source expectations')
    require(len(manifest) == 85, 'Expected 85 frozen manifest entries')
    for name, digest in manifest.items():
        require(sha(PCB/name) == digest, f'Frozen source hash mismatch: {name}')
    root = ET.parse(PCB / 'schematic-netlist.xml').getroot()
    parts = schematic_check(root)
    # Negative tests prove value and connectivity edits cannot silently pass.
    mutants = []
    for label in ('value', 'net'):
        changed = ET.fromstring(ET.tostring(root))
        if label == 'value':
            changed.find("components/comp[@ref='C10']/value").text = '47u 50V'
        else:
            for net in changed.findall('nets/net'):
                if net.find("node[@ref='U2'][@pin='5']") is not None:
                    net.attrib['name'] = '/WRONG_RAIL'
        try:
            schematic_check(changed)
        except RuntimeError:
            mutants.append(label)
        else:
            raise RuntimeError(f'Schema negative test accepted changed {label}')
    return parts, mutants


def simulate(out, name, body, vectors, stop, step, keep=False):
    folder = out / 'models'
    folder.mkdir(exist_ok=True)
    path = folder / (name + '.cir')
    text = (f'{name}: generated sensitivity study; see README\n' + body +
            '\n.options reltol=1e-6 abstol=1e-10 vntol=1e-8\n.control\n'
            'set noaskquit\nset wr_singlescale\nset wr_vecnames\nset numdgt=12\n'
            f'tran {step:.12g} {stop:.12g} 0 {step:.12g}\n'
            f'wrdata {name}.dat ' + ' '.join(vectors) + '\nquit\n.endc\n.end\n')
    path.write_text(text)
    return solve_deck(path, len(vectors), stop, keep)


def solve_deck(path, vector_count, stop, keep=False, expected_peaks=None):
    """Shared validation for first solves AND retained representative reruns."""
    folder, name = path.parent, path.stem
    data = path.with_suffix('.dat')
    # A zero-exit failed analysis must not accidentally reuse an earlier waveform.
    data.unlink(missing_ok=True)
    if keep:
        path.with_suffix('.dat.gz').unlink(missing_ok=True)
    proc = subprocess.run(['ngspice', '-b', path.name], cwd=folder,
                          capture_output=True, text=True, timeout=60)
    log = proc.stdout + proc.stderr
    (folder / (name + '.log')).write_text(log)
    require(proc.returncode == 0 and not re.search(
        r'(?im)^\s*(?:error|fatal)|timestep too small|simulation interrupted|stepping failed', log),
        f'{name}: ngspice failed; inspect log')
    require(data.exists(), f'{name}: missing solver data')
    lines = data.read_text().splitlines()
    rows = [[float(x) for x in line.split()] for line in lines[1:] if line.strip()]
    require(len(rows) > 10 and all(len(r) == vector_count + 1 for r in rows),
            f'{name}: invalid data schema')
    require(all(math.isfinite(x) for r in rows for x in r), f'{name}: nonfinite data')
    require(rows[-1][0] >= stop * .999, f'{name}: incomplete transient')
    require(all(b[0] > a[0] for a, b in zip(rows, rows[1:])), f'{name}: nonmonotonic time')
    for column, expected in (expected_peaks or {}).items():
        require(math.isclose(max(r[column] for r in rows), expected,
                             rel_tol=1e-9, abs_tol=1e-9),
                f'{name}: retained waveform peak differs from first solve, column {column}')
    if keep:
        # Deterministic compressed raw solver waveform, full precision/time resolution.
        (folder / (name + '.dat.gz')).write_bytes(gzip.compress(data.read_bytes(), mtime=0))
    data.unlink()
    return rows


def lc_response(t, vin, inductance, capacitance, resistance):
    """Closed-form series RLC step: capacitor voltage and series current."""
    if t <= 0:
        return 0.0, 0.0
    alpha = resistance / (2 * inductance)
    omega0 = 1 / math.sqrt(inductance * capacitance)
    if alpha < omega0:
        wd = math.sqrt(omega0 ** 2 - alpha ** 2)
        decay = math.exp(-alpha * t)
        return (vin * (1 - decay * (math.cos(wd*t) + alpha/wd*math.sin(wd*t))),
                vin / (inductance * wd) * decay * math.sin(wd*t))
    if abs(alpha - omega0) < omega0 * 1e-9:
        return vin*(1-math.exp(-alpha*t)*(1+alpha*t)), vin/inductance*t*math.exp(-alpha*t)
    beta = math.sqrt(alpha**2 - omega0**2)
    p, q = -alpha + beta, -alpha - beta
    return (vin * (1 + (q*math.exp(p*t)-p*math.exp(q*t))/(p-q)),
            vin/inductance*(math.exp(p*t)-math.exp(q*t))/(p-q))


def motor_cases(out):
    results = []
    for index, (vin, cap, lead, wire, esr) in enumerate(itertools.product(
            [20., 24.], [80e-6, 100e-6, 120e-6], [.5e-6, 2e-6, 10e-6],
            [.02, .1, .5], [.03, .061, .2])):
        name = f'vmot_{index:03d}'
        rows = simulate(out, name, f'''* C10 exact nominal 100u/50V; tolerance and all parasitics swept
* No load, no carrier ceramic, no clamp, no source current limit: sensitivity only
Vbus src 0 PULSE(0 {vin} 10u 1n 1n 5m 10m)
Rlead src lead {wire}
Llead lead vmot {lead}
Resr vmot cap {esr}
C10 cap 0 {cap}''', ['v(vmot)', 'v(cap)', 'i(Llead)'], .002, .2e-6)
        error = max(abs(row[1] - (lambda v, i: v + esr*i)(*lc_response(
            row[0]-10.0005e-6, vin, lead, cap, wire+esr))) for row in rows)
        require(error < .002 * vin, f'{name}: independent RLC oracle error {error}')
        peak = max(row[1] for row in rows)
        results.append(dict(case=name, vin_V=vin, C10_F=cap, lead_H=lead,
                            wire_ohm=wire, esr_ohm=esr, peak_vmot_V=peak,
                            peak_current_A=max(row[3] for row in rows),
                            oracle_max_error_V=error, margin_to_35V=35-peak,
                            criterion='FAIL' if peak >= 35 else 'CONDITIONAL'))
    # Independent near-lossless limit: Vpeak = 2 Vin, tpeak = pi sqrt(LC).
    rows = simulate(out, 'oracle_lossless', '''Vbus src 0 PULSE(0 24 10u 1n 1n 5m 10m)
Llead src cap 10u
C10 cap 0 100u''', ['v(cap)', 'i(Llead)'], .0003, .05e-6, keep=True)
    peak = max(rows, key=lambda row: row[1])
    expected_time = 10.0005e-6 + math.pi*math.sqrt(10e-6*100e-6)
    require(abs(peak[1]-48) < .005, 'Lossless LC 2Vin oracle failed')
    require(abs(peak[0]-expected_time) < .1e-6, 'Lossless LC peak-time oracle failed')
    # Retain full traces for min/max risk examples, generated with identical parameters.
    for item in [min(results, key=lambda r:r['peak_vmot_V']), max(results, key=lambda r:r['peak_vmot_V'])]:
        path = out / 'models' / (item['case']+'.cir')
        solve_deck(path, 3, .002, keep=True,
                   expected_peaks={1:item['peak_vmot_V'], 3:item['peak_current_A']})
    return results, dict(peak_V=peak[1], expected_peak_V=48,
                         peak_time_s=peak[0], expected_peak_time_s=expected_time)


def ldo_cases(out):
    results = []
    for index, (vin, rsource, derating, tau, ilim, high) in enumerate(itertools.product(
            [4.75, 5., 5.25], [.1, 2.], [.3, 1.], [2e-6, 20e-6, 100e-6],
            [.6, .8], [.5, .7])):
        name = f'ldo_{index:03d}'
        # Controlled pass current has first-order response, finite DC gain and a
        # hard current ceiling. It draws the same current from VIN as it supplies.
        # tau is an assumed control lag, NOT a measured AP2112 loop response.
        body = f'''* U2 BEHAVIORAL SENSITIVITY ONLY: not manufacturer AP2112 macromodel
Vsrc src 0 {vin}
Rsource src vin {rsource}
Resrin vin cin .02
C1 cin 0 {10e-6*derating}
Iq vin 0 {IQ}
Bcommand command 0 V=max(0,min({ilim},(3.3-v(out))*10))
Rlag command lag 1
Clag lag 0 {tau}
* 0.5 ohm pass headroom law is an assumption, not a guaranteed dropout model
Bpass vin out I=max(0,min(v(lag),(v(vin)-v(out))/.5))
Resrout out cout .02
* C2+C4+direct 100n C3,C6,C7,C9; ideal common rail, no PCB inductance
Cout cout 0 {20.4e-6*derating}
Vdemand demand 0 PULSE(.1 {high} 200u 1u 1u 400u 2m)
* Load rolls off below 0.5V to avoid unphysical negative supply in overload.
Bload out 0 I=v(demand)*max(0,min(1,v(out)/.5))
Rleak out 0 1G
.nodeset v(out)=3.29 v(cout)=3.29 v(lag)=.1 v(command)=.1 v(vin)={vin-rsource*(.1+IQ)}'''
        rows = simulate(out, name, body,
                        ['v(out)', 'v(vin)', 'i(Vsrc)', 'v(lag)'], .0015, .2e-6,
                        keep=index in (0, 143))
        # Steady-state branch current and droop verified independently from KCL.
        expected_initial = 3.3 - .1 / 10
        require(abs(rows[0][1]-expected_initial) < 1e-5, f'{name}: initial Vout KCL')
        require(abs(-rows[0][3]-(.1+IQ)) < 1e-6, f'{name}: source current KCL')
        # Input source loss is dissipated externally, not in U2.
        require(abs(rows[0][2]-(vin-rsource*(.1+IQ))) < 1e-5, f'{name}: VIN branch drop')
        vmin = min(r[1] for r in rows)
        vmax = max(r[1] for r in rows)
        results.append(dict(case=name, vin_V=vin, source_ohm=rsource,
                            cap_factor=derating, control_lag_s=tau, current_limit_A=ilim,
                            load_low_A=.1, load_high_A=high, min_3V3_V=vmin,
                            max_3V3_V=vmax, min_5V_pin_V=min(r[2] for r in rows),
                            peak_source_A=max(-r[3] for r in rows),
                            criterion='FAIL' if vmin < 3 or vmax > 3.6 else 'CONDITIONAL',
                            interpretation='assumed-model envelope, not AP2112 prediction'))
    return results


def thermal_cases(out):
    rows = []
    for vin, ambient, current in itertools.product([4.75, 5., 5.25], [25., 40., 50.], [.2, .24, .3, .5]):
        power = (vin-3.3)*current + vin*IQ
        junction = ambient + THETA*power
        rows.append(dict(vin_V=vin, ambient_C=ambient, load_A=current,
                         dissipation_W=power, estimated_Tj_C=junction,
                         margin_to_125C=125-junction,
                         criterion='FAIL' if junction > 125 else 'CONDITIONAL'))
    limits = []
    for vin, ambient in itertools.product([4.75, 5., 5.25], [25., 40., 50.]):
        limit = ((125-ambient)/THETA-vin*IQ)/(vin-3.3)
        # Additional 1.5% low-output sensitivity, not a full-temperature accuracy claim.
        lower_vout_limit = ((125-ambient)/THETA-vin*IQ)/(vin-3.3*.985)
        require(abs(ambient+THETA*((vin-3.3)*limit+vin*IQ)-125) < 1e-10,
                'Thermal inverse oracle failed')
        limits.append(dict(vin_V=vin, ambient_C=ambient, target_Tj_C=125,
                           theta_JA_C_per_W=THETA, nominal_vout_limit_A=limit,
                           low_output_sensitivity_limit_A=lower_vout_limit,
                           criterion='CONDITIONAL'))
    write_csv(out/'thermal.csv', rows)
    write_csv(out/'thermal-current-limits.csv', limits)
    return rows, limits


def charge_oracle(out):
    # Check cap hold-up law independently of the behavioral control model.
    rows = simulate(out, 'oracle_charge', '''Vref ref 0 3.3
Rinit ref out 1G
Cstore out 0 20.4u
Iload out 0 PULSE(0 .4 10u 1n 1n 100u 1m)''',
                    ['v(out)'], 20e-6, .01e-6, keep=True)
    final = rows[-1][1]
    expected = 3.3 - .4*(20e-6-10e-6-.5e-9)/20.4e-6
    require(abs(final-expected) < 1e-5, 'Charge conservation C dV/dt oracle failed')
    return {'final_V': final, 'analytic_final_V': expected}


def motor_plot(out, worst):
    """Small SVG of retained solver output; no plotting dependency or resimulation."""
    path = out/'models'/(worst['case']+'.dat.gz')
    lines = gzip.decompress(path.read_bytes()).decode().splitlines()[1:]
    rows = [[float(x) for x in line.split()] for line in lines]
    rows = [r for r in rows if r[0] <= .0005]
    points = ' '.join(f'{60+r[0]/.0005*680:.2f},{330-r[1]/50*260:.2f}' for r in rows[::4])
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="430" viewBox="0 0 800 430">',
           '<rect width="800" height="430" fill="white"/>',
           '<g font-family="sans-serif" font-size="13" fill="#172b4d">',
           '<text x="30" y="25">VMOT assumed hotplug network — ngspice result, not bench measurement</text>',
           f'<text x="30" y="48">{worst["case"]}: peak {worst["peak_vmot_V"]:.3f} V; C=80 µF, L=10 µH, Rlead=20 mΩ, ESR=30 mΩ</text>']
    for value in (0, 10, 20, 30, 35, 40, 50):
        y = 330-value/50*260
        color = '#c62828' if value == 35 else '#dddddd'
        svg.append(f'<path d="M60 {y} H740" stroke="{color}"/><text x="18" y="{y+4}">{value} V</text>')
    for us in (0, 100, 200, 300, 400, 500):
        x = 60+us/500*680
        svg.append(f'<text x="{x-10}" y="350">{us}</text>')
    svg += [f'<polyline points="{points}" fill="none" stroke="#1565c0" stroke-width="2"/>',
            '<text x="320" y="375">Time (µs); 35 V A4988 maximum in red</text>',
            '<text x="30" y="405">24 V ideal source; no proven clamp or source-current limit. FAIL for this assumed case.</text>',
            '</g></svg>']
    (out/'vmot-worst.svg').write_text('\n'.join(svg)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    require(not out.is_relative_to(PCB), 'Output must not modify frozen PCB')
    out.mkdir(parents=True, exist_ok=True)
    summary = {'run_id': uuid.uuid4().hex,
               'started_utc': datetime.now(timezone.utc).isoformat(),
               'suite_execution': 'RUNNING', 'run_state': 'RUNNING',
               'stage': 'initialize', 'circuit_qualification': 'CONDITIONAL',
               'physical_tests': 'NOT PERFORMED'}

    def stage(name):
        summary['stage'] = name
        write_json(out/'summary.json', summary)

    try:
        # Invalidate any previous PASS before touching sources or run artifacts.
        stage('source_validation')
        parts, mutants = source_checks()
        stage('provenance')
        version = subprocess.run(['ngspice', '--version'], capture_output=True,
                                 text=True, check=True).stdout
        write_json(out/'provenance.json', {
            'run_id': summary['run_id'],
            'python': platform.python_version(), 'ngspice': version,
            'container_image_id': os.environ.get('SIM_IMAGE_ID', 'not supplied'),
            'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in [
                PCB/'schematic-netlist.xml', PCB/'checksums.json', PCB/'stock-evidence.json',
                HERE/'run.py', HERE/'test_run.py', HERE/'README.md', ROOT/'electronics/sim/Dockerfile']},
            'asserted_parts': parts, 'schema_mutants_rejected': mutants})
        stage('thermal')
        thermal, limits = thermal_cases(out)
        stage('charge_oracle')
        charge = charge_oracle(out)
        stage('vmot')
        motor, lc = motor_cases(out)
        stage('vmot_publication')
        write_csv(out/'vmot.csv', motor)
        motor_plot(out, max(motor, key=lambda r:r['peak_vmot_V']))
        stage('ldo')
        ldo = ldo_cases(out)
        stage('ldo_publication')
        write_csv(out/'ldo-sensitivity.csv', ldo)
        summary.update(circuit_qualification='CONDITIONAL',
                       tested_envelope='FAIL', thermal_cases=len(thermal),
                       thermal_target_failures=sum(r['criterion']=='FAIL' for r in thermal),
                       vmot_cases=len(motor), vmot_35V_failures=sum(r['criterion']=='FAIL' for r in motor),
                       ldo_behavioral_cases=len(ldo),
                       ldo_behavioral_rail_failures=sum(r['criterion']=='FAIL' for r in ldo),
                       simulated_transients=len(motor)+len(ldo)+2,
                       worst_thermal=max(thermal,key=lambda r:r['estimated_Tj_C']),
                       worst_vmot=max(motor,key=lambda r:r['peak_vmot_V']),
                       worst_behavioral_droop=min(ldo,key=lambda r:r['min_3V3_V']),
                       worst_thermal_current_limit=min(limits,key=lambda r:r['nominal_vout_limit_A']),
                       max_rlc_oracle_error_V=max(r['oracle_max_error_V'] for r in motor),
                       independent_oracles={'lossless_LC':lc,'charge_conservation':charge},
                       note='FAIL rows are real criterion failures under stated assumptions; suite PASS only certifies execution and numerical checks.')
        stage('model_hash_publication')
        write_json(out/'model-hashes.json', {p.name:sha(p) for p in sorted((out/'models').glob('*.cir'))})
        stage('summary_publication')
        completed = dict(summary, suite_execution='PASS', run_state='COMPLETE',
                         stage='complete', finished_utc=datetime.now(timezone.utc).isoformat())
        write_json(out/'summary.json', completed)
        print(json.dumps(completed, indent=2))
    except (Exception, KeyboardInterrupt) as exc:
        summary.update(suite_execution='FAIL',
                       run_state='ABORTED' if isinstance(exc, KeyboardInterrupt) else 'FAILED',
                       error=str(exc) or type(exc).__name__,
                       finished_utc=datetime.now(timezone.utc).isoformat())
        try:
            write_json(out/'summary.json', summary)
        except (Exception, KeyboardInterrupt) as publication_error:
            print(f'Cannot publish failure status: {publication_error}', file=sys.stderr)
        print(f'Power suite FAIL: {exc}', file=sys.stderr)
        return 130 if isinstance(exc, KeyboardInterrupt) else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
