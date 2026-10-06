"""Prepare display textures for the Sketchfab GLBs with system Python.

Run before trafic_sketchfab_export.py. The game's paint alpha is converted to
an opaque baked colour; glass transparency is stored in a separate texture.
Source mod images are read only.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from trafic_paint_preview import main as paint


def main():
    project = Path(__file__).resolve().parents[2]
    output = project / 'Assets/sketchfab'
    output.mkdir(parents=True, exist_ok=True)
    textures = project / 'Contents/mods/batman_RenaultTrafic1/common/media/textures/Vehicles'
    for colour, hsv in [('blue', (.59, .94, .68)), ('white', (.15, .04, .76))]:
        path = output / ('body_' + colour + '.png')
        paint(str(textures / 'Vehicles_batman_RenaultTraficI_Shell.png'), str(path), *hsv)
        image = Image.open(path).convert('RGBA')
        image.putalpha(255)
        image.save(path)
        rgba = np.array(image)
        brightness = rgba[:, :, :3].max(axis=2) / 255
        blend = np.clip((brightness - .23) / .07, 0, 1)
        blend = blend * blend * (3 - 2 * blend)
        rgba[:, :, 3] = np.rint(255 * (1 - .72 * blend)).astype('uint8')
        Image.fromarray(rgba).save(output / ('glass_' + colour + '.png'))
    wheel = Image.open(textures / 'Vehicles_batman_RenaultTraficI_Wheel.png').convert('RGBA')
    wheel.putalpha(255)
    wheel.save(output / 'wheel.png')


if __name__ == '__main__':
    main()
