#!/usr/bin/env python3
"""Reproducible lumped airflow sizing; explicit design snapshots, not CFD/CAD.

Run from any directory. Writes analysis/outputs/airflow.json.
No flow split, operating point, heat-sink resistance or food temperature solved.
"""
import json
import math
from pathlib import Path


def slot_area(count, length, width, radius=0.7):
    """Analytic rounded-rectangle throat area in mm², excluding obstructions."""
    return count * (length * width - (4 - math.pi) * radius**2)


def main():
    areas = {
        "existing_inlet": slot_area(26, 50, 3),
        "existing_exhaust": slot_area(60, 44, 3),
        "proposed_inlet": slot_area(34, 50, 3.5),
        "proposed_exhaust": slot_area(120, 22, 3),
    }
    rho, cp = 1.2, 1005.0
    pressures = []
    for variant in ("existing", "proposed"):
        for flow in (20, 30, 40, 60):
            for cd in (0.6, 0.8):
                q = flow / 3600
                terms = {
                    end: rho / 2 * (q / (cd * areas[f"{variant}_{end}"] * 1e-6))**2
                    for end in ("inlet", "exhaust")
                }
                pressures.append({
                    "variant": variant, "flow_m3_h": flow, "assumed_Cd": cd,
                    "inlet_Pa": terms["inlet"], "exhaust_Pa": terms["exhaust"],
                    "vent_total_Pa": sum(terms.values()),
                })
    result = {
        "status": "Analytic sizing scenarios, 2026-10-24; no physical validation",
        "geometry_basis": "Original vents and proposed revision described in kb/airflow.md; not live CAD",
        "rounded_slot_area_mm2": areas,
        "fan_square_mm2": 120**2,
        "nominal_120mm_disc_mm2": math.pi * 60**2,
        "fan_unsealed_gap_upper_area_mm2": 4 * 120 * 2,
        "fan_catalogue": {
            "model": "Noctua NF-A12x25 PWM", "rpm": 2000,
            "free_air_m3_h": 102.1, "shutoff_pressure_Pa": 2.34 * 9.80665,
            "source": "https://www.noctua.at/en/products/nf-a12x25-pwm/specifications",
            "evidence": "Manufacturer search-index text; direct fetch returned HTTP 429",
        },
        "assumptions": {
            "rho_kg_m3": rho, "cp_J_kg_K": cp,
            "vent_pressure": "sum rho/2 * (Q/(Cd*A))^2; Cd sensitivity only",
            "omissions": "fan curve, fins, bridge, turning, frame blockage, leakage, dust, thermal bridges",
        },
        "vent_pressure_scenarios": pressures,
        "bulk_air_temperature_rise_K": [
            {"flow_m3_h": flow, "heat_W": heat,
             "rise_K": heat / (rho * cp * flow / 3600)}
            for flow in (20, 30, 40) for heat in (60, 100, 150)
        ],
    }
    output = Path(__file__).resolve().parent / "outputs" / "airflow.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
