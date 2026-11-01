#!/usr/bin/env python3
"""Generate the exact Allegro land pattern, rather than mislabelling a TMC QFN."""
from pathlib import Path
from design import PIN_NAMES, DS

HERE = Path(__file__).resolve().parent
NAME = 'Allegro_A4988_ET_QFN28_5x5_P0.5_EP3.15'


def footprint():
    s = [f'(footprint "{NAME}" (version 20241229) (generator "motor-block") (layer "F.Cu")',
         '(descr "Allegro A4988 rev8 p19 DWG-0000378 rev3; 3.15mm EP; board thermal vias required separately")',
         '(attr smd)',
         '(property "Reference" "REF**" (at 0 -3.8) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
         f'(property "Value" "{NAME}" (at 0 3.8) (layer "F.Fab") (effects (font (size 0.7 0.7) (thickness 0.1))))',
         '(fp_rect (start -2.5 -2.5) (end 2.5 2.5) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
         '(fp_rect (start -3.25 -3.25) (end 3.25 3.25) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
         '(fp_circle (center -3.15 -2) (end -3.05 -2) (stroke (width 0.1) (type solid)) (fill solid) (layer "F.SilkS"))']
    for pin in range(1, 29):
        side, i = divmod(pin-1, 7)
        x, y = [(-2.4, -1.5 + i*.5), (-1.5+i*.5, 2.4),
                (2.4, 1.5-i*.5), (1.5-i*.5, -2.4)][side]
        w, h = (1.15, .30) if side % 2 == 0 else (.30, 1.15)
        s.append(f'(pad "{pin}" smd rect (at {x:g} {y:g}) (size {w:g} {h:g}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    s.append('(pad "29" smd rect (at 0 0) (size 3.15 3.15) (layers "F.Cu" "F.Mask") (zone_connect 2))')
    # 9 x 0.83^2 / 3.15^2 = 62.5% paste, no open via holes in footprint.
    for x in [-1.03, 0, 1.03]:
        for y in [-1.03, 0, 1.03]:
            s.append(f'(pad "" smd rect (at {x} {y}) (size .83 .83) (layers "F.Paste"))')
    return '\n'.join(s) + '\n)\n'


def symbol():
    s = ['(kicad_symbol_lib (version 20241209) (generator "motor-block")',
         '(symbol "A4988SETTR-T" (pin_names (offset 0.5)) (in_bom yes) (on_board yes)',
         '(property "Reference" "U" (at 0 22.86 0) (effects (font (size 1.27 1.27))))',
         '(property "Value" "A4988SETTR-T" (at 0 20.32 0) (effects (font (size 1.27 1.27))))',
         f'(property "Footprint" "motor:{NAME}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         f'(property "Datasheet" "{DS}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
         '(symbol "A4988SETTR-T_0_1" (rectangle (start -12.7 19.05) (end 12.7 -20.32) (stroke (width .254) (type default)) (fill (type background))))',
         '(symbol "A4988SETTR-T_1_1"']
    for pin, name in PIN_NAMES.items():
        left = pin <= 15
        x, y, angle = (-15.24, 17.78-(pin-1)*2.54, 0) if left else (15.24, 17.78-(pin-16)*2.54, 180)
        typ = ('no_connect' if name == 'NC' else 'power_in' if name in ['GND', 'EP_GND', 'VDD', 'VBB1', 'VBB2']
               else 'output' if name.startswith('OUT') or name == 'VREG' else 'passive' if name in ['CP1','CP2','VCP','ROSC','SENSE1','SENSE2'] else 'input')
        display = '~{' + name[1:] + '}' if name.startswith('~') else name
        s.append(f'(pin {typ} line (at {x:g} {y:g} {angle}) (length 2.54) (name "{display}" (effects (font (size 1.0 1.0)))) (number "{pin}" (effects (font (size 1.0 1.0)))))')
    return '\n'.join(s) + '\n)))\n'


def damping_footprint():
    # HoLRT manufacturer recommended land: inner gap 4.90, total 8.10,
    # width 3.40 mm. Native KiCad R2512 is smaller, so retain exact land here.
    return '''(footprint "Milliohm_HoLRT2512_ManufacturerLand" (version 20241229)
      (generator "motor-block") (layer "F.Cu") (attr smd)
      (descr "HoLRT rev Ho-A0 2020-04-27 recommended land A4.90 B8.10 C3.40mm")
      (property "Reference" "REF**" (at 0 -2.7) (layer "F.SilkS") (effects (font (size 1 1) (thickness .15))))
      (property "Value" "HoLRT2512" (at 0 2.7) (layer "F.Fab") (effects (font (size 1 1) (thickness .15))))
      (fp_rect (start -3.15 -1.6) (end 3.15 1.6) (stroke (width .1) (type solid)) (fill none) (layer "F.Fab"))
      (fp_rect (start -4.3 -1.95) (end 4.3 1.95) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))
      (pad "1" smd rect (at -3.25 0) (size 1.6 3.4) (layers "F.Cu" "F.Paste" "F.Mask"))
      (pad "2" smd rect (at 3.25 0) (size 1.6 3.4) (layers "F.Cu" "F.Paste" "F.Mask"))
    )\n'''


if __name__ == '__main__':
    target = HERE / 'footprints/motor.pretty'
    target.mkdir(exist_ok=True)
    (target / (NAME + '.kicad_mod')).write_text(footprint())
    (target / 'Milliohm_HoLRT2512_ManufacturerLand.kicad_mod').write_text(damping_footprint())
    (HERE / 'motor.kicad_sym').write_text(symbol())
