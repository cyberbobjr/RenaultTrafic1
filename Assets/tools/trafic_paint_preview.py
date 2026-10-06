"""Apply a paint colour to the Trafic shell the way the vanilla vehicle shader does.

media/shaders/vehicle.frag: where the shell alpha is 0, hue = paint hue,
saturation = tex_s + paint_s - 0.5, value = tex_v + paint_v - 0.5.
Usage: python trafic_paint_preview.py <shell.png> <out.png> <h> <s> <v>
"""
import colorsys
import sys
from PIL import Image


def main(src, out, h, s, v):
    img = Image.open(src).convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a == 255:
                continue
            _, ts, tv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            ps = min(max(ts + s - 0.5, 0.0), 0.9999)
            pv = min(max(tv + v - 0.5, 0.0), 0.9999)
            pr, pg, pb = colorsys.hsv_to_rgb(h, ps, pv)
            k = 1 - a / 255
            px[x, y] = (int(r * (1 - k) + pr * 255 * k), int(g * (1 - k) + pg * 255 * k),
                        int(b * (1 - k) + pb * 255 * k), 255)
    img.save(out)
    print("written", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *map(float, sys.argv[3:6]))
