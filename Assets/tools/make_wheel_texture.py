"""Generate the Trafic I wheel texture (256x256).

Layout (matches the UVs of TRF_wheel in RenaultTrafic1_ebauche.blend):
- rows 0..63   : tread band, u = around the circumference, v = across the tyre width
- disc centre (128,160), radius 92 px = tyre outer radius (0.295 m)
  sidewall 92..57 px, steel rim 57..0 px (8 slots, 4 nuts, black centre cap)
"""
import math
import sys
from PIL import Image, ImageDraw

SS = 4                     # supersampling
N = 256 * SS
CX, CY, R = 128 * SS, 160 * SS, 92 * SS


def px(v):
    return int(round(v * SS))


def ring(d, r_out, r_in, fill):
    d.ellipse([CX - r_out, CY - r_out, CX + r_out, CY + r_out], fill=fill)
    if r_in > 0:
        d.ellipse([CX - r_in, CY - r_in, CX + r_in, CY + r_in], fill=None)


def circle(d, cx, cy, r, fill, outline=None, width=1):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline, width=width)


def main(out):
    img = Image.new("RGB", (N, N), (30, 30, 32))
    d = ImageDraw.Draw(img)
    # ---- tread band (rows 0..63) ----
    d.rectangle([0, 0, N, px(64)], fill=(36, 36, 38))
    for x0 in range(0, N, px(16)):                       # transverse blocks
        d.rectangle([x0, px(4), x0 + px(11), px(60)], fill=(44, 44, 46))
    for v in (14, 27, 37, 50):                           # circumferential grooves
        d.rectangle([0, px(v), N, px(v + 3)], fill=(16, 16, 17))
    for x0 in range(0, N, px(8)):                        # sipes
        d.line([x0, px(17), x0 + px(4), px(27)], fill=(22, 22, 23), width=SS)
        d.line([x0 + px(4), px(40), x0, px(50)], fill=(22, 22, 23), width=SS)
    d.rectangle([0, 0, N, px(3)], fill=(28, 28, 30))      # shoulders
    d.rectangle([0, px(61), N, px(64)], fill=(28, 28, 30))
    # ---- sidewall ----
    circle(d, CX, CY, R, (33, 33, 35))
    for i, c in enumerate((38, 36, 34)):                  # soft bulge shading
        circle(d, CX, CY, R - px(6 + i * 8), (c, c, c + 2))
    circle(d, CX, CY, px(60), (24, 24, 25))               # bead seat shadow
    # ---- steel rim ----
    circle(d, CX, CY, px(57), (196, 198, 200))            # flange
    circle(d, CX, CY, px(52), (150, 152, 155))            # flange step shadow
    circle(d, CX, CY, px(50), (182, 184, 187))            # dish
    circle(d, CX, CY, px(34), (170, 172, 175))
    for k in range(8):                                    # ventilation slots
        a0 = math.radians(k * 45 - 11)
        a1 = math.radians(k * 45 + 11)
        pts = []
        for a in [a0 + (a1 - a0) * t / 6 for t in range(7)]:
            pts.append((CX + math.cos(a) * px(46), CY + math.sin(a) * px(46)))
        for a in [a1 - (a1 - a0) * t / 6 for t in range(7)]:
            pts.append((CX + math.cos(a) * px(39), CY + math.sin(a) * px(39)))
        d.polygon(pts, fill=(28, 28, 30))
    circle(d, CX, CY, px(25), (160, 162, 165))            # hub face
    for k in range(4):                                    # wheel nuts
        a = math.radians(45 + k * 90)
        x, y = CX + math.cos(a) * px(17), CY + math.sin(a) * px(17)
        circle(d, x, y, px(4.2), (120, 122, 125), outline=(60, 60, 62), width=SS)
        circle(d, x, y, px(1.8), (200, 202, 205))
    circle(d, CX, CY, px(9), (22, 22, 24))                # centre cap
    s = px(4)                                             # small diamond badge
    d.polygon([(CX, CY - s), (CX + s * 0.7, CY), (CX, CY + s), (CX - s * 0.7, CY)], outline=(200, 200, 200), width=SS)
    img = img.resize((256, 256), Image.LANCZOS)
    img.save(out)
    print("written", out)


if __name__ == "__main__":
    main(sys.argv[1])
