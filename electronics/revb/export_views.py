#!/usr/bin/env python3
"""Export views from current KiCad sources, with placement/routed names explicit."""
import argparse
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--placement", action="store_true")
    args = parser.parse_args()
    output = HERE / ("placement-views" if args.placement else "views")
    output.mkdir(exist_ok=True)
    board = "feeder-b-unrouted.kicad_pcb" if args.placement else "feeder-b.kicad_pcb"

    def run(*args):
        subprocess.run(["kicad-cli", *args], cwd=HERE, check=True)

    run("sch", "export", "svg", "-o", str(output), "feeder-b.kicad_sch")
    for name, layers in [("top", "F.Cu,F.SilkS,Edge.Cuts"),
                         ("bottom", "B.Cu,B.SilkS,Edge.Cuts"),
                         ("assembly", "F.Fab,F.SilkS,Edge.Cuts")]:
        run("pcb", "export", "svg", "--layers", layers, "--mode-single", "--page-size-mode", "2",
            "--exclude-drawing-sheet", "-o", str(output / (name + ".svg")), board)


if __name__ == "__main__":
    main()
