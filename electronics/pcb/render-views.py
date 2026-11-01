#!/usr/bin/env python3
"""Raster previews of current KiCad exports. Requires CairoSVG and Pillow."""
from pathlib import Path
import json,hashlib
import cairosvg
from PIL import Image
root=Path(__file__).parent/'views'
for name in ['top','bottom','assembly']:
    cairosvg.svg2png(url=str(root/(name+'.svg')),write_to=str(root/(name+'.png')),output_width=900)
cairosvg.svg2png(url=str(root/'feeder.svg'),write_to=str(root/'schematic.png'),output_width=3600)
im=Image.open(root/'schematic.png')
im.crop((80,750,1000,1400)).save(root/'schematic-detail.png')
if (root/'packaging.svg').exists():
    cairosvg.svg2png(url=str(root/'packaging.svg'),write_to=str(root/'packaging.png'),output_width=1485)
files=['top.svg','bottom.svg','assembly.svg','feeder.svg','packaging.svg',
       'top.png','bottom.png','assembly.png','schematic.png','schematic-detail.png','packaging.png']
(root/'render-provenance.json').write_text(json.dumps({f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files},indent=2)+'\n')
