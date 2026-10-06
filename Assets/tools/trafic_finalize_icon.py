"""Package a generated transparent icon, preserving its native alpha.

Usage: python trafic_finalize_icon.py <source.png> <destination.png>
The generated master is kept unchanged; no colour-based background removal.
"""
from pathlib import Path
import sys
from PIL import Image


def main(source, destination):
    image = Image.open(source).convert("RGBA")
    alpha = image.getchannel("A")
    if alpha.getextrema()[0] == 255:
        raise ValueError("The source must have native background transparency")
    box = alpha.getbbox()
    if box is None:
        raise ValueError("The source icon is empty")
    image = image.crop(box)
    image.thumbnail((60, 60), Image.Resampling.LANCZOS)
    icon = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    icon.paste(image, ((64 - image.width) // 2, (64 - image.height) // 2))
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    icon.save(target, optimize=True)
    print(target, icon.size, icon.mode, target.stat().st_size, "bytes")


if __name__ == "__main__":
    main(*sys.argv[1:])
