#!/usr/bin/env python3
"""Render selected real ngspice output samples as a dependency-free SVG."""
import argparse
import html
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "interfaces/results"
PANELS = [
    ("1-Wire release after 2 us", "Time (us)", 1e6, 0, 30, 3.6, "v(bus)",
     [("onewire_1000p_1.01R", "1 nF"), ("onewire_2000p_1.01R", "2 nF"),
      ("onewire_5000p_1.01R", "5 nF")], 2.475),
    ("Fan PWM: assumed 2 nF cable, generic NPN", "Time (us)", 1e6, 140, 200, 5.5, "v(pwm)",
     [("fan_R1050_C2000p_B100_T25", "1.05 kohm pull-up"),
      ("fan_R10000_C2000p_B100_T25", "10 kohm"),
      ("fan_R100000_C2000p_B100_T25", "100 kohm")], 2.1),
    ("ADC filter: 24 V input step", "Time (ms)", 1e3, 0, 8, 2.5, "v(adc)",
     [("adc_step_C0.8", "C8 = 80 nF"), ("adc_step_C1.2", "C8 = 120 nF")], None),
    ("EN capacitor response: ideal 3.3 V step", "Time (ms)", 1e3, 0, 40, 3.6, "v(en)",
     [("enable_RC_C0.8", "C5 = 0.8 uF"), ("enable_RC_C1.2", "C5 = 1.2 uF")], 2.475),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    out = parser.parse_args().output
    report = json.loads((out / "report.json").read_text())
    if report.get("run_status") != "COMPLETE":
        raise RuntimeError("Only COMPLETE interface runs may be plotted")
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="800" viewBox="0 0 1100 800">',
           '<rect width="1100" height="800" fill="white"/>',
           '<g font-family="sans-serif" font-size="13" fill="#243248">',
           '<text x="30" y="28" font-size="20">PCB interface simulations — modeled sensitivity, not measured hardware</text>']
    colours = ["#2266b0", "#d77418", "#9448a4"]
    for i, (title, xlabel, scale, xmin, xmax, ymax, vector, cases, threshold) in enumerate(PANELS):
        left, top, width, height = 70 + (i % 2) * 535, 85 + (i // 2) * 355, 445, 230
        x = lambda v: left + (v - xmin) * width / (xmax - xmin)
        y = lambda v: top + height - v * height / ymax
        svg.append(f'<text x="{left}" y="{top-20}" font-weight="bold">{html.escape(title)}</text>')
        for tick in range(5):
            xx, yy = left + tick * width / 4, top + tick * height / 4
            svg += [f'<path d="M {xx} {top} v {height} M {left} {yy} h {width}" stroke="#dde3ea" fill="none"/>',
                    f'<text x="{xx}" y="{top+height+20}" text-anchor="middle">{xmin+tick*(xmax-xmin)/4:g}</text>',
                    f'<text x="{left-8}" y="{yy+4}" text-anchor="end">{ymax*(1-tick/4):.2g}</text>']
        svg.append(f'<text x="{left-40}" y="{top+10}">V</text>')
        svg.append(f'<text x="{left+width/2}" y="{top+height+40}" text-anchor="middle">{xlabel}</text>')
        if threshold is not None:
            svg.append(f'<path d="M {left} {y(threshold)} h {width}" stroke="#333" stroke-dasharray="5 4"/>')
        for j, (case, label) in enumerate(cases):
            lines = (out / case / "wave.dat").read_text().splitlines()
            header = lines[0].split()
            rows = [[float(v) for v in row.split()] for row in lines[1:] if row.strip()]
            points = [(r[header.index("time")] * scale, r[header.index(vector)]) for r in rows]
            points = [(t, v) for t, v in points if xmin <= t <= xmax]
            stride = max(1, len(points) // 1200)
            selected = points[::stride] + points[-1:]
            coords = " ".join(f'{x(t):.3f},{y(v):.3f}' for t, v in selected)
            svg.append(f'<polyline points="{coords}" fill="none" stroke="{colours[j]}" stroke-width="1.8"/>')
            svg.append(f'<text x="{left+j*145}" y="{top+height+65}" fill="{colours[j]}">{html.escape(label)}</text>')
    svg += ['<text x="30" y="790">Dashed lines are screening thresholds. Full assumptions and unmodified numeric waveforms accompany the reports.</text>', '</g></svg>']
    (out / "waveforms.svg").write_text("\n".join(svg) + "\n")
    print(out / "waveforms.svg")


if __name__ == "__main__":
    main()
