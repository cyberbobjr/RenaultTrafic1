"""Draw the Trafic I vehicle textures from Assets/build/trafic_draw.json.

Usage (system Python with Pillow):  python trafic_raster.py <project dir>
The JSON is written by trafic_bake_textures.py inside Blender. Surface maps are
written by trafic_surface_bake.py using copies of the validated export meshes.
Polygons are drawn without antialiasing: the vehicle mask needs exact zone colours.
"""
import json
import os
import sys
from PIL import Image, ImageDraw, ImageChops, ImageFilter
import numpy as np


def surface_relief(shell, lights, project):
    """Keep paint/opaque alpha intact; only modulate the existing RGB values.

    AO gives contact shadows, Z normals give mild ambient relief without fixing
    a sun direction in the atlas. Shared hidden-face swatches stay flat because
    their UVs deliberately overlap. No rust, dirt, or invented damage is added.
    """
    data = np.asarray(shell).copy()
    base = data[:, :, :3].astype(np.float32)
    n = shell.width
    maps = os.path.join(project, "Assets", "build")
    ao = np.asarray(Image.open(os.path.join(maps, "trafic_ao.png"))
                    .convert("L").filter(ImageFilter.GaussianBlur(0.55)), dtype=np.float32) / 255
    normal = np.asarray(Image.open(os.path.join(maps, "trafic_normal_z.png"))
                        .convert("L"), dtype=np.float32) / 255 * 2 - 1
    if ao.shape != (n, n) or normal.shape != (n, n):
        raise ValueError("Surface maps must match the vehicle atlas dimensions")
    paint = data[:, :, 3] == 0
    # Roof/bent edges slightly lighter, lower-facing edges slightly darker.
    strength = np.where(paint, 0.20, 0.33)
    ambient = np.where(paint, 0.065, 0.14)
    factor = (1 - strength * (1 - ao)) * (1 + ambient * normal)
    rgb = base * factor[:, :, None]
    yy, xx = np.mgrid[:n, :n]
    # Clean, very fine moulded plastic grain, below one RGB step in amplitude.
    plastic = np.all(data[:, :, :3] == (56, 56, 60), axis=2)
    grain = np.random.default_rng(1985).normal(0, 0.45, (n, n))
    rgb += (grain * plastic)[:, :, None]
    # A quiet sky-to-cabin tonal gradient on opaque glass, not a specular shader.
    glass = np.all(data[:, :, :3] == (112, 122, 134), axis=2)
    glass_gradient = np.zeros((n, n), dtype=np.float32)
    for top in (0, 282):
        region = glass & (yy >= top) & (yy < top + 278) & (xx < 664)
        rows = yy[region]
        if rows.size:
            glass_gradient[region] = 7 - 14 * (rows - rows.min()) / max(1, rows.max() - rows.min())
    # The windshield uses the roof projection: its top is toward increasing X.
    region = glass & (yy >= 564) & (xx < 664)
    columns = xx[region]
    if columns.size:
        glass_gradient[region] = -7 + 14 * (columns - columns.min()) / max(1, columns.max() - columns.min())
    rgb += (glass_gradient * glass)[:, :, None]
    # Subtle fluting of clean lamp lenses; the Lights atlas stays unchanged.
    lens = np.zeros((n, n), dtype=bool)
    for colour in ((246, 246, 243), (252, 250, 239), (249, 179, 63), (211, 48, 48)):
        lens |= np.all(data[:, :, :3] == colour, axis=2)
    lit = np.asarray(lights)[:, :, 3] != 0
    amber = np.all(data[:, :, :3] == (249, 179, 63), axis=2)
    lens &= lit | amber  # Keep white registration plates smooth.
    flutes = np.where(xx % 3 == 0, -0.025, 0.0125)
    rgb *= (1 + flutes * lens)[:, :, None]
    # The flat colour tiles occupy this rectangle in trafic_bake_textures.py.
    rgb[848:, 843:] = base[848:, 843:]
    data[:, :, :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    return Image.fromarray(data)


def panel_shadow(shell, edge, glass):
    """Soft shoulder around a joint; original one-pixel seam remains readable."""
    data = np.asarray(shell).copy()
    rgb = data[:, :, :3].astype(np.float32)
    soft = np.asarray(edge.filter(ImageFilter.GaussianBlur(1.15)), dtype=np.float32) / 255
    eligible = np.ones(soft.shape, dtype=bool) if glass else data[:, :, 3] == 0
    rgb *= (1 - 0.12 * soft * eligible)[:, :, None]
    data[:, :, :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    return Image.fromarray(data)


def main(project):
    ops = json.load(open(os.path.join(project, "Assets", "build", "trafic_draw.json")))
    n = ops["size"]
    shell = Image.new("RGBA", (n, n), tuple(ops["paint_grey"]) + (0,))
    mask = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    lights = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    for img, key in ((shell, "shell"), (mask, "mask"), (lights, "lights")):
        d = ImageDraw.Draw(img)
        for poly, col in ops[key]:
            d.polygon([tuple(p) for p in poly], fill=tuple(col))
    shell = surface_relief(shell, lights, project)
    # 1 px outline of each moving part / glass (silhouette only, not its inner details).
    # Panel gaps stay under the paint (alpha 0) as a darker grey, so they follow the
    # vehicle colour (vehicle.frag: value = tex_v + paint_v - 0.5); glass seals are opaque.
    gap_col = Image.new("RGBA", (n, n), tuple(ops["gap_grey"]) + (0,))
    seal_col = Image.new("RGBA", (n, n), tuple(ops["seam"]) + (255,))
    for group, polys in ops["seams"].items():
        m = Image.new("L", (n, n), 0)
        dm = ImageDraw.Draw(m)
        for poly in polys:
            dm.polygon([tuple(p) for p in poly], fill=255)
        glass = "window" in group or "windshield" in group
        if not glass:
            # fill the window opening so only the outer edge of the door is drawn
            outside = m.copy()
            ImageDraw.floodfill(outside, (0, 0), 128)
            m = outside.point(lambda v: 0 if v == 128 else 255)
        edge = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(3)))
        shell = panel_shadow(shell, edge, glass)
        shell.paste(seal_col if glass else gap_col, (0, 0), edge)
    for img, key in ((shell, "shell"), (mask, "mask"), (lights, "lights")):
        os.makedirs(os.path.dirname(ops["out"][key]), exist_ok=True)
        path = ops["out"][key]
        if os.path.isfile(path) and Image.open(path).convert("RGBA").tobytes() == img.tobytes():
            print("unchanged", path)
        else:
            img.save(path)
            print("written", path)


if __name__ == "__main__":
    main(sys.argv[1])
