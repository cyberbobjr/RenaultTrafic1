"""Build the export meshes of the Trafic I and generate its vehicle textures.

Run inside Blender (scene "Trafic_Ebauche"):
    exec(open(r"...\\Assets\\tools\\trafic_bake_textures.py").read())

What it does
- evaluates every part of TRF_parts at rest pose and joins them into one mesh per
  game part (collection EXPORT_trafic, objects TrafI_*), in world coordinates;
- UV1: orthographic box projection into a 1024 atlas (left, right, top, front and
  rear islands for the exterior, smaller islands for the cab interior). A face that
  is hidden from its projection direction (inner shell, door inner skin, underside)
  is mapped to a flat colour swatch of its material instead;
- UV2: tiled box projection for the vanilla generic rust / damage / blood sheets;
- writes, with the vanilla vehicle shader conventions (media/shaders/vehicle.frag):
    *_Shell.png  RGBA, alpha 0 = painted by the game (neutral grey underneath)
    *_Mask.png   zone colours (exact values of colZone1..27), no antialiasing
    *_Lights.png RGBA, lit colour where headlamps / tail / stop lamps are.
Blender has no PIL: this script writes Assets/build/trafic_draw.json and
trafic_raster.py (system Python + Pillow) draws the PNG files from it.
"""
import bpy, bmesh, math, os, colorsys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import json

PROJECT = r"C:\Users\cyber\Zomboid\Workshop\RenaultTrafic1"
TEXDIR = os.path.join(PROJECT, r"Contents\mods\batman_RenaultTrafic1\common\media\textures\Vehicles")
PREFIX = "Vehicles_batman_RenaultTraficI"
N = 1024
SC = bpy.data.scenes["Trafic_Ebauche"]

# ---------------------------------------------------------------- groups
GROUPS = {   # export mesh: (source collection, kind)
    "TrafI_body":       ("PART_body", "ext"),
    "TrafI_door_fl":    ("PART_DoorFrontLeft", "ext"),
    "TrafI_door_fr":    ("PART_DoorFrontRight", "ext"),
    "TrafI_window_fl":  ("PART_WindowFrontLeft", "ext"),
    "TrafI_window_fr":  ("PART_WindowFrontRight", "ext"),
    "TrafI_door_rr":    ("PART_DoorRearRight_slide", "ext"),
    "TrafI_trunkdoor":  ("PART_TrunkDoor", "ext"),
    "TrafI_windshield": ("PART_Windshield", "ext"),
    "TrafI_hood":       ("PART_EngineDoor", "ext"),
    "TrafI_seat_fl":    ("PART_SeatFrontLeft", "int"),
    "TrafI_seat_fr":    ("PART_SeatFrontRight", "int"),
    "TrafI_interior":   ("PART_interior", "int"),
}
SEAMED = {"TrafI_door_fl", "TrafI_door_fr", "TrafI_door_rr", "TrafI_trunkdoor", "TrafI_hood",
          "TrafI_window_fl", "TrafI_window_fr", "TrafI_windshield"}

# ---------------------------------------------------------------- islands
# view: (axis normal, right vector, up vector, a range, b range, pixel origin, px per metre)
S_EXT, S_INT = 150.0, 95.0
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
ISL = {
    "ext+X": (X, Y, Z, (-2.20, 2.20), (0.15, 2.00), (0, 0), S_EXT),
    "ext-X": (-X, -Y, Z, (-2.20, 2.20), (0.15, 2.00), (0, 282), S_EXT),
    "ext+Z": (Z, Y, X, (-2.20, 2.20), (-1.10, 1.10), (0, 564), S_EXT),
    "ext-Y": (-Y, X, Z, (-1.10, 1.10), (0.15, 2.00), (664, 0), S_EXT),
    "ext+Y": (Y, -X, Z, (-1.10, 1.10), (0.15, 2.00), (664, 282), S_EXT),
    "int+Z": (Z, X, Y, (-0.92, 0.92), (-1.75, -0.10), (664, 564), S_INT),
    "int-Y": (-Y, X, Z, (-0.92, 0.92), (0.60, 1.85), (664, 725), S_INT),
    "int+Y": (Y, -X, Z, (-0.92, 0.92), (0.60, 1.85), (843, 725), S_INT),
    "int+X": (X, Y, Z, (-1.75, -0.10), (0.60, 1.85), (843, 564), S_INT),
    "int-X": (-X, -Y, Z, (-1.75, -0.10), (0.60, 1.85), (664, 848), S_INT),
}
SW0, SW_SIZE = (843, 848), 16          # swatches (flat colours) start here
CLEAN_UV2 = (0.246, 0.363)              # empty in Veh_Rust, Veh_Damage1/2, Veh_Blood_Mask/Hvy (12 px margin)


def lin2srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


PAINT_GREY = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(0.0, 0.18, 0.45))
SEAM = (38, 38, 40)
GAP_GREY = tuple(int(round(v * 255)) for v in colorsys.hsv_to_rgb(0.0, 0.18, 0.27))


def mat_rgb(m):
    if m is None:
        return (128, 128, 128)
    if m.name == "TRF_paint":
        return PAINT_GREY
    if m.name == "TRF_glass":
        return (112, 122, 134)
    return tuple(int(round(lin2srgb(m.diffuse_color[i]) * 255)) for i in range(3))


def to_px(isl, p):
    n, r, u, ar, br, org, s = ISL[isl]
    a, b = p.dot(r), p.dot(u)
    return (org[0] + (a - ar[0]) * s, org[1] + (br[1] - b) * s)


def in_island(isl, p):
    n, r, u, ar, br, org, s = ISL[isl]
    a, b = p.dot(r), p.dot(u)
    return ar[0] - 1e-4 <= a <= ar[1] + 1e-4 and br[0] - 1e-4 <= b <= br[1] + 1e-4


def build_export_meshes():
    arm = bpy.data.objects["trafic_skeleton"]
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()
    col = bpy.data.collections.get("EXPORT_trafic")
    if not col:
        col = bpy.data.collections.new("EXPORT_trafic")
        SC.collection.children.link(col)
    for o in list(col.objects):
        me = o.data
        bpy.data.objects.remove(o)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for gname, (cname, kind) in GROUPS.items():
        bm = bmesh.new()
        mats = []
        for src in bpy.data.collections[cname].objects:
            if src.type != 'MESH':
                continue
            me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
            me.transform(src.matrix_world)
            remap = []
            for m in me.materials:
                if m not in mats:
                    mats.append(m)
                remap.append(mats.index(m))
            nv = len(bm.verts)
            tmp = bmesh.new()
            tmp.from_mesh(me)
            vmap = [bm.verts.new(v.co) for v in tmp.verts]
            for f in tmp.faces:
                try:
                    nf = bm.faces.new([vmap[v.index] for v in f.verts])
                except ValueError:
                    continue
                nf.material_index = remap[f.material_index] if remap else 0
                nf.smooth = f.smooth
            tmp.free()
            bpy.data.meshes.remove(me)
        me = bpy.data.meshes.new(gname)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(gname, me)
        col.objects.link(o)
        o["kind"] = kind
        out[gname] = o
    return out


def build_bvh(objs):
    verts, polys = [], []
    for o in objs:
        base = len(verts)
        verts += [v.co.copy() for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def face_island(kind, normal):
    ax = max(range(3), key=lambda i: abs(normal[i]))
    sgn = 1 if normal[ax] > 0 else -1
    if ax == 2 and sgn < 0:
        return None                       # underside -> swatch
    return "%s%s%s" % (kind, "+" if sgn > 0 else "-", "XYZ"[ax])


def visible(tree, isl, pts, centre):
    n = ISL[isl][0]
    for p in pts:
        q = p + (centre - p) * 0.25
        hit = tree.ray_cast(q + n * 10.0, -n, 20.0)
        if hit[0] is not None and abs(hit[3] - 10.0) < 0.004:
            return True
    return False


def run():
    objs = build_export_meshes()
    ext = [o for o in objs.values() if o["kind"] == "ext"]
    itr = [o for o in objs.values() if o["kind"] == "int"]
    trees = {"ext": build_bvh(ext), "int": build_bvh(itr)}
    ops = {"shell": [], "mask": [], "lights": [], "seams": []}
    swatches = {}

    def swatch(m):
        key = m.name if m else "none"
        if key not in swatches:
            i = len(swatches)
            x0 = SW0[0] + (i % 11) * SW_SIZE
            y0 = SW0[1] + (i // 11) * SW_SIZE
            swatches[key] = (x0, y0)
            rgb = mat_rgb(m)
            a = 0 if (m and m.name == "TRF_paint") else 255
            ops["shell"].append(([(x0, y0), (x0 + SW_SIZE - 1, y0), (x0 + SW_SIZE - 1, y0 + SW_SIZE - 1),
                                  (x0, y0 + SW_SIZE - 1)], list(rgb) + [a]))
        x0, y0 = swatches[key]
        return ((x0 + SW_SIZE / 2) / N, 1 - (y0 + SW_SIZE / 2) / N)

    draw_list = []      # (depth, island, polygon px, material, group, face key)
    seams = []
    for gname, o in objs.items():
        kind = o["kind"]
        me = o.data
        uv1 = me.uv_layers.new(name="UVMap")
        uv2 = me.uv_layers.new(name="UVMap2")
        vis_faces = {}
        for p in me.polygons:
            m = me.materials[p.material_index] if me.materials else None
            pts = [me.vertices[i].co for i in p.vertices]
            c = p.center
            isl = face_island(kind, p.normal)
            ok = isl is not None and isl in ISL and all(in_island(isl, q) for q in pts) \
                and visible(trees[kind], isl, pts, c)
            if ok:
                poly = [to_px(isl, q) for q in pts]
                for li, vi in zip(p.loop_indices, p.vertices):
                    px = to_px(isl, me.vertices[vi].co)
                    uv1.data[li].uv = (px[0] / N, 1 - px[1] / N)
                depth = -c.dot(ISL[isl][0])
                draw_list.append((depth, isl, poly, m, gname, c))
                vis_faces[p.index] = isl
            else:
                s = swatch(m)
                for li in p.loop_indices:
                    uv1.data[li].uv = s
            # UV2 (generic rust / damage / blood sheets): each visible exterior panel covers the
            # sheet once, flipped so the rust (top rows of Veh_Rust) lands on the lower body;
            # cab interior and hidden faces point at a spot that is empty in every sheet.
            if ok and kind == "ext":
                n_, r_, u_, ar, br, org, s_ = ISL[isl]
                for li, vi in zip(p.loop_indices, p.vertices):
                    v = me.vertices[vi].co
                    uv2.data[li].uv = ((v.dot(r_) - ar[0]) / (ar[1] - ar[0]),
                                       1.0 - (v.dot(u_) - br[0]) / (br[1] - br[0]))
            else:
                for li in p.loop_indices:
                    uv2.data[li].uv = CLEAN_UV2
        if gname in SEAMED:
            # panel gaps / glass seals: outline of the whole part, drawn by trafic_raster.py
            seams.append((gname, [[to_px(isl, me.vertices[i].co) for i in me.polygons[fi].vertices]
                                  for fi, isl in vis_faces.items()]))
    # paint far to near so the nearest surface wins
    draw_list.sort(key=lambda t: -t[0])
    for depth, isl, poly, m, gname, c in draw_list:
        rgb = mat_rgb(m)
        alpha = 0 if (m and m.name == "TRF_paint") else 255
        ops["shell"].append((poly, list(rgb) + [alpha]))
        zone = zone_colour(gname, m, c)
        ops["mask"].append((poly, list(zone) + [255] if zone else [0, 0, 0, 0]))
        lc = light_colour(m, c)
        ops["lights"].append((poly, list(lc) if lc else [0, 0, 0, 0]))
    ops["seams"] = {g: polys for g, polys in seams}
    ops["size"], ops["paint_grey"], ops["seam"], ops["gap_grey"] = N, list(PAINT_GREY), list(SEAM), list(GAP_GREY)
    ops["out"] = {k: os.path.join(TEXDIR, PREFIX + "_" + k.capitalize() + ".png") for k in ("shell", "mask", "lights")}
    os.makedirs(os.path.join(PROJECT, "Assets", "build"), exist_ok=True)
    with open(os.path.join(PROJECT, "Assets", "build", "trafic_draw.json"), "w") as f:
        json.dump(ops, f)
    return objs, swatches


# zone colours = colZone* of media/shaders/vehicle.frag (x>0 is the vehicle's left)
def zone_colour(gname, m, c):
    name = m.name if m else ""
    left = c.x > 0
    if name == "TRF_headlamp":
        return (191, 0, 0) if left else (64, 0, 0)            # Lights L H / R H
    if name == "TRF_taillamp":
        if c.z > 0.705:
            return (0, 64, 0) if left else (0, 191, 0)        # Lights L T / R T
        return (128, 191, 0) if left else (128, 64, 0)        # StopLights L / R
    return {"TrafI_door_fl": (255, 0, 255), "TrafI_door_fr": (0, 255, 255),
            "TrafI_door_rr": (255, 255, 0), "TrafI_trunkdoor": (0, 255, 128), "TrafI_hood": (255, 0, 128),
            "TrafI_window_fl": (128, 0, 128), "TrafI_window_fr": (0, 128, 128),
            "TrafI_windshield": (0, 128, 0)}.get(gname)


def light_colour(m, c):
    name = m.name if m else ""
    if name == "TRF_headlamp":
        return (255, 248, 215, 255)
    if name == "TRF_taillamp":
        return (255, 40, 30, 255)
    return None


# moving parts follow their bone (whole part, weight 1): needed for the preview and the FBX export
SKIN = {"TrafI_door_fl": "door_fl_bone", "TrafI_door_fr": "door_fr_bone", "TrafI_window_fl": "window_fl_bone",
        "TrafI_window_fr": "window_fr_bone", "TrafI_door_rr": "door_rr_bone", "TrafI_hood": "hood_bone"}


def skin_export(objs):
    arm = bpy.data.objects["trafic_skeleton"]
    for name, o in objs.items():
        if name == "TrafI_trunkdoor":
            assign = lambda co: "trunk_l_bone" if co.x > 0 else "trunk_r_bone"
        elif name in SKIN:
            assign = lambda co, b=SKIN[name]: b
        else:
            continue
        groups = {}
        for v in o.data.vertices:
            b = assign(v.co)
            if b not in groups:
                groups[b] = o.vertex_groups.new(name=b)
            groups[b].add([v.index], 1.0, 'REPLACE')
        md = o.modifiers.new("Skeleton", 'ARMATURE')
        md.object = arm
        md.use_vertex_groups = True


RESULT = run()
skin_export(RESULT[0])
