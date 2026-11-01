#!/usr/bin/env python3
"""Direct ceramic-to-PETG screening using the historical stdlib FV solver.

All cold boundaries are the OUTER cold ceramic face (or the historical ideal
boundary below the aluminium). There is no added aluminium in direct cases.
This does not solve a TEC, ceramic stress, chamber air or food-top temperature.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

from model import Model, Parameters, checks, heatmap, write_csv


ENVIRONMENTS = {
    'open': dict(ambient=25.0, top_h=5.0, underside=30.0),
    # Effective top heat gain through an unspecified cover; NOT predicted lid U.
    'covered_low_h': dict(ambient=25.0, top_h=1.0, underside=30.0),
}
CONTACTS = {
    'ideal': 0.0,
    'contact_R0.005': 0.005,
    'airgap_0.05mm': 0.00005/0.026,
    'airgap_0.2mm': 0.0002/0.026,
    'airgap_1mm': 0.001/0.026,
}
SHAPES = {
    'prior_cap41.28x3': dict(cap_width_mm=41.28, cap_thickness=0.003),
    'direct40': dict(cap_width_mm=40.0, cap_thickness=0.0),
    'direct30': dict(cap_width_mm=30.0, cap_thickness=0.0),
}


def case_id(shape, environment, cold, contact):
    return f'{shape}__{environment}__Tc{cold:g}__{contact}'


def steady(p):
    m = Model(p)
    t, it, residual = m.solve()
    stats = m.stats(t)
    assert abs(stats['balance_W']) < 1e-7
    assert min(t) >= min(p.cold, p.ambient, p.underside)-1e-7
    assert max(t) <= max(p.cold, p.ambient, p.underside)+1e-7
    assert abs(stats['volume_ml']-40) < 1e-9
    return m, t, dict(**stats, iterations=it, residual_l2_W=residual)


def transient(p, start, dt, duration=14400):
    m = Model(p)
    t = [float(start)]*m.n
    extra = m.capacity/dt
    samples = []
    boundary_J = cold_J = 0.0
    max_balance = 0.0
    for sec in range(0, duration+1, dt):
        if sec % 900 == 0:
            stored_J = m.capacity*sum(v-start for v in t)
            samples.append(dict(initial_C=start, dt_s=dt, time_min=sec/60,
                                **m.stats(t), cold_extracted_J=cold_J,
                                net_boundary_J=boundary_J, stored_change_J=stored_J,
                                cumulative_energy_error_J=boundary_J-stored_J))
        if sec == duration:
            break
        old = t
        t, _, _ = m.solve(rhs=[b+extra*v for b, v in zip(m.rhs, old)],
                          initial=old, extra=extra)
        stats = m.stats(t)
        storage_W = m.capacity*sum(v-w for v, w in zip(t, old))/dt
        error = abs(storage_W-stats['balance_W'])
        max_balance = max(max_balance, error)
        assert error < 1e-7
        boundary_J += stats['balance_W']*dt
        cold_J += stats['cold_W']*dt
        assert min(t) >= min(start, p.cold, p.ambient, p.underside)-1e-7
        assert max(t) <= max(start, p.cold, p.ambient, p.underside)+1e-7
    assert max(abs(s['cumulative_energy_error_J']) for s in samples) < 1e-3
    return samples, max_balance


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    base = Parameters()
    cases = {}
    rows = []
    states = {}
    # Matched contact assumptions isolate geometry; actual dry-contact resistance
    # need not be the same for ceramic and aluminium.
    for shape, dimensions in SHAPES.items():
        for environment, boundary in ENVIRONMENTS.items():
            for cold in (0.0, 2.0):
                for contact, resistance in CONTACTS.items():
                    name = case_id(shape, environment, cold, contact)
                    p = replace(base, **dimensions, **boundary, cold=cold,
                                contact_r=resistance)
                    cases[name] = p
                    m, t, stats = steady(p)
                    rows.append(dict(case=name, shape=shape, environment=environment,
                                     cold_C=cold, contact=contact, **stats))
                    states[name] = t
                    if shape == 'direct40' and contact == 'ideal' and cold == 0:
                        heatmap(out/f'{name}.svg', m, t,
                                f'Direct 40 mm, {environment}, ideal ceramic 0 C')
                        write_csv(out/f'{name}_field.csv',
                                  [dict(x_mm=x, y_mm=y, temperature_C=v, cold_fraction=f)
                                   for (x, y), v, f in zip(m.xy, t, m.fraction)])
    write_csv(out/'steady_cases.csv', rows)

    # Two paths decompose the small net change: remove Al at fixed footprint;
    # or reduce footprint retaining the old Al resistance. Neither is a new part.
    controls = []
    for environment, boundary in ENVIRONMENTS.items():
        for cold in (0.0, 2.0):
            for shape, dimensions in {
                'control41.28_noAl': dict(cap_width_mm=41.28, cap_thickness=0.0),
                'control40_withAl': dict(cap_width_mm=40.0, cap_thickness=0.003),
            }.items():
                name = case_id(shape, environment, cold, 'ideal')
                p = replace(base, **dimensions, **boundary, cold=cold)
                cases[name] = p
                _, _, stats = steady(p)
                controls.append(dict(case=name, shape=shape, environment=environment,
                                     cold_C=cold, **stats))
    write_csv(out/'decomposition_controls.csv', controls)

    # These sensitivities do not pretend to calculate the enclosure's air or U.
    sensitivities = []
    for name, changes in {
        'sheltered_top10_base30': dict(ambient=10.0, top_h=5.0),
        'open_top_h10': dict(top_h=10.0),
        'open_ambient30_base35': dict(ambient=30.0, underside=35.0),
        'open_deck_k0.03': dict(deck_k=0.03),
        'open_deck_k0.12': dict(deck_k=0.12),
        'open_food_k0.3': dict(food_k=0.3),
        'open_food_k0.6': dict(food_k=0.6),
    }.items():
        p = replace(base, **SHAPES['direct40'], **changes)
        key = f'direct40__{name}__Tc0__ideal'
        cases[key] = p
        _, _, stats = steady(p)
        sensitivities.append(dict(case=key, **stats))
    write_csv(out/'boundary_material_sensitivity.csv', sensitivities)

    convergence = []
    for row in rows:
        if row['contact'] != 'ideal':
            continue
        name = row['case']
        p = cases[name]
        convergence.append(dict(case=name, dx_mm=p.dx_mm,
                                **{k: v for k, v in row.items()
                                   if k not in ('case', 'shape', 'environment', 'cold_C', 'contact')}))
        spacings = [1.0]
        if row['cold_C'] == 0 and (row['shape'] == 'direct40' or row['environment'] == 'open'):
            spacings.append(0.5)
        for dx in spacings:
            _, _, stats = steady(replace(p, dx_mm=dx))
            convergence.append(dict(case=name, dx_mm=dx, **stats))
    write_csv(out/'grid_convergence.csv', convergence)

    histories = []
    time_convergence = []
    transient_checks = {}
    selections = [(case_id('direct40', env, cold, 'ideal'), start)
                  for env in ENVIRONMENTS for cold in (0.0, 2.0) for start in (4, 25)]
    selections += [(case_id('direct40', env, 0, 'airgap_0.2mm'), 25)
                   for env in ENVIRONMENTS]
    selections += [(case_id(shape, 'covered_low_h', 0, 'ideal'), 25)
                   for shape in ('prior_cap41.28x3', 'direct30')]
    for name, start in selections:
        samples, error = transient(cases[name], start, 60)
        histories.extend(dict(case=name, **sample) for sample in samples)
        transient_checks[f'{name}__start{start}__dt60'] = error
        if name.startswith('direct40__') and '__Tc0__ideal' in name:
            for dt in (30, 60, 300):
                if dt == 60:
                    comparison = samples
                else:
                    comparison, error = transient(cases[name], start, dt, duration=7200)
                    transient_checks[f'{name}__start{start}__dt{dt}'] = error
                time_convergence.extend(dict(case=name, **sample) for sample in comparison
                                        if sample['time_min'] in (15, 60, 120))
    write_csv(out/'transient.csv', histories)
    write_csv(out/'time_convergence.csv', time_convergence)

    # Sanity checks on physical trends, in addition to the historical independent
    # uniform/analytic/isolated-energy tests. Check pointwise, not just averages.
    for environment in ENVIRONMENTS:
        for shape in SHAPES:
            ideal0 = states[case_id(shape, environment, 0, 'ideal')]
            ideal2 = states[case_id(shape, environment, 2, 'ideal')]
            assert all(b >= a-1e-7 for a, b in zip(ideal0, ideal2))
            for contact in CONTACTS:
                impaired = states[case_id(shape, environment, 0, contact)]
                assert all(b >= a-1e-7 for a, b in zip(ideal0, impaired))
        direct40 = states[case_id('direct40', environment, 0, 'ideal')]
        direct30 = states[case_id('direct30', environment, 0, 'ideal')]
        assert all(b >= a-1e-7 for a, b in zip(direct40, direct30))
    numerical = dict(historical_solver=checks(),
                     steady_max_energy_imbalance_W=max(abs(r['balance_W'])
                         for r in rows+controls+sensitivities+convergence),
                     transient_max_step_energy_imbalance_W=max(transient_checks.values()),
                     transient_max_cumulative_energy_error_J=max(
                         abs(r['cumulative_energy_error_J']) for r in histories+time_convergence),
                     contact_coldface_footprint_monotonicity_passed=True,
                     all_steady_and_transient_temperature_bounds_passed=True)

    # A conditional aggregate useful to electronics sizing, not appliance load:
    # eleven covered sites plus one open, simultaneously stationary and equally filled.
    aggregate = []
    by_case = {row['case']: row for row in rows}
    for shape in SHAPES:
        for cold in (0.0, 2.0):
            open_row = by_case[case_id(shape, 'open', cold, 'ideal')]
            covered = by_case[case_id(shape, 'covered_low_h', cold, 'ideal')]
            m = Model(cases[case_id(shape, 'open', cold, 'ideal')])
            aggregate.append(dict(shape=shape, cold_C=cold,
                eleven_covered_one_open_foodpath_holding_W=11*covered['cold_W']+open_row['cold_W'],
                twelve_open_foodpath_holding_W=12*open_row['cold_W'],
                twelve_initial25C_foodpath_extraction_W=12*m.stats([25.0]*m.n)['cold_W'],
                twelve_initial4C_foodpath_extraction_W=12*m.stats([4.0]*m.n)['cold_W']))
    write_csv(out/'conditional_foodpath_loads.csv', aggregate)
    report = dict(
        provenance={'model_sha256': hashlib.sha256(Path(__file__).with_name('model.py').read_bytes()).hexdigest(),
                    'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        conventions={'temperature': 'thickness-averaged food deg C; not resolved top surface',
                     'cold_W': 'food-path heat extracted into imposed cold face, positive',
                     'balance_W': 'ambient + deck - cold; equals storage rate in transient',
                     'covered_low_h': 'assumed effective h=1 to 25 C; not solved chamber/lid',
                     'airgap': 'uniform conduction-only gap with k_air=0.026 W/(m K)',
                     'cold': 'fixed outer cold ceramic 0/2 C; no TEC feedback or ceramic model',
                     'transient_energy': 'backward-Euler endpoint flux quadrature, food mass only'},
        parameters={name: asdict(p) for name, p in cases.items()},
        checks=numerical, steady=rows, controls=controls, sensitivities=sensitivities,
        grid_convergence=convergence, time_convergence=time_convergence,
        conditional_foodpath_loads=aggregate)
    (out/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(checks=numerical, conditional_foodpath_loads=aggregate), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent/'direct-output')
    args = parser.parse_args()
    run(args.output)
