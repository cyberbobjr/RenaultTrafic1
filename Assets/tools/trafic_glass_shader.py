"""Build the authorised standalone glass shader from installed B42.21 shaders.

Only the fragment alpha changes. Preserve TextureRust and the vehicle shader
interface so DrawVehicle still uploads textures and the animated matrix palette.
Usage: python trafic_glass_shader.py <project> <installed media directory>
"""
from pathlib import Path
import sys

NAME = "batman_trafic_glass"
GLASS_ALPHA = "0.28"


def main(project, media):
    source = Path(media) / "shaders"
    target = Path(project) / "Contents/mods/batman_RenaultTrafic1/common/media/shaders"
    target.mkdir(parents=True, exist_ok=True)
    for suffix in (".vert", "_static.vert"):
        (target / (NAME + suffix)).write_bytes(
            (source / ("vehicle_multiuv_noreflect" + suffix)).read_bytes())
    fragment = (source / "vehicle_multiuv_noreflect.frag").read_text(encoding="utf-8")
    opaque = "gl_FragColor = vec4(col, TexturePainColor.a);"
    if fragment.count(opaque) != 1:
        raise ValueError("Unexpected vanilla fragment shader; recheck the target game build")
    replacement = """// Standalone glass shader: retain opaque rubber seals and all vehicle uniforms.
    // This texture already distinguishes grey-blue glass from dark rubber joints.
    // Transparency is independent of the Shell alpha used by vehicle paint.
    float glassBrightness = max(tex.r, max(tex.g, tex.b));
    float glassSurface = windowAlpha * smoothstep(0.23, 0.30, glassBrightness);
    float glassOpacity = mix(1.0, %s * (1.0 - t4en), glassSurface);
    gl_FragColor = vec4(col, TexturePainColor.a * glassOpacity);""" % GLASS_ALPHA
    (target / (NAME + ".frag")).write_text(
        fragment.replace(opaque, replacement), encoding="utf-8")
    print("written", target, "glass alpha", GLASS_ALPHA)


if __name__ == "__main__":
    main(*sys.argv[1:])
