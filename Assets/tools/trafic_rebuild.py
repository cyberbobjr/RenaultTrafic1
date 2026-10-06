"""Rebuild the Trafic I body and everything that depends on its surface.

Run inside Blender (scene "Trafic_Ebauche"):
    exec(open(r"...\\Assets\\tools\\trafic_rebuild.py", encoding="utf-8").read(), {"__name__": "trafic_rebuild"})

Profiles come from the 1985 orthographic sheets (docs/): side top line, plan width,
tumblehome. Units: metres, Z up, front towards -Y, x > 0 = vehicle left.
Rebuilt here: body loft, window / door / hood cutters, frozen door and hood pieces
(booleans applied at rest pose, left door mirrored from the right one), windscreen
and door glass, wipers, bonnet vent, mirrors on their A-pillar supports, nose-corner
indicators. The skeleton bones and the opening actions are kept.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

SC = bpy.data.scenes["Trafic_Ebauche"]
M = bpy.data.materials
K_SIDE = 0.004381          # side sheet: metres per pixel


def lerp_tab(tab, x):
    if x <= tab[0][0]:
        return tab[0][1]
    for (x0, y0), (x1, y1) in zip(tab, tab[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    (x0, y0), (x1, y1) = tab[-2], tab[-1]
    return y1 + (y1 - y0) * (x - x1) / (x1 - x0)


ZT = [(-2.100, 0.885), (-2.080, 0.910), (-2.05, 0.940), (-1.90, 1.083), (-1.75, 1.215), (-1.70, 1.262),
      (-1.13, 1.792), (-1.06, 1.862), (-0.99, 1.920), (-0.92, 1.942), (-0.50, 1.958), (0.50, 1.960),
      (1.50, 1.955), (1.95, 1.950), (2.07, 1.940), (2.12, 1.915), (2.148, 1.865)]
WF = [(-2.10, 0.885), (-2.00, 0.893), (-1.90, 0.912), (-1.75, 0.935), (-1.60, 0.940), (-1.25, 0.945),
      (-0.95, 0.950), (2.148, 0.950)]
DZ = [(0.75, 0.0), (1.15, 0.011), (1.40, 0.043), (1.58, 0.071), (1.70, 0.093), (1.79, 0.115),
      (1.862, 0.126), (1.90, 0.135)]
YF, RCF, YR, RCR = -2.100, 0.050, 2.148, 0.060
STATIONS = [-2.100, -2.080, -2.050, -1.90, -1.75, -1.70, -1.13, -1.06, -0.99, -0.92, 1.95, 2.07, 2.12, 2.148]
A_PILLAR_RX = 0.06         # corner radius between windscreen and side (narrow pillar)


def zt(y): return lerp_tab(ZT, y)
def zb(y): return 0.36 if y < -2.0 else (0.33 if y > 2.12 else 0.32)


def w(y):
    ww = lerp_tab(WF, y)
    if y < YF + RCF:
        u = RCF - (y - YF)
        return ww - RCF + math.sqrt(max(0.0, RCF * RCF - u * u))
    if y > YR - RCR:
        u = RCR - (YR - y)
        return ww - RCR + math.sqrt(max(0.0, RCR * RCR - u * u))
    return ww


def d(z): return 0.0 if z <= 0.75 else lerp_tab(DZ, z)


def edge(t):
    k = min(max((t - 1.80) / 0.14, 0), 1)
    rx = (A_PILLAR_RX + (0.26 - A_PILLAR_RX) * k) if t > 1.25 else 0.09
    return rx, 0.06 + 0.03 * k, (0.015 if t > 1.9 else (0.02 if t > 1.25 else 0.01))


def half(y):
    t = zt(y); b = zb(y); W = w(y); rx, rz, crown = edge(t)
    ze = t - rz; zs = min(1.15, ze - 0.06)
    P = [(W - 0.060, b), (W - 0.012, b + 0.075), (W, 0.75)]
    for f in (0, 0.5, 1):
        z = zs + (ze - zs) * f
        P.append((W - d(z), z))
    xe = W - d(ze); cx = xe - rx
    for a in (45, 90):
        r = math.radians(a)
        P.append((cx + rx * math.cos(r), ze + rz * math.sin(r)))
    return P, b, t + crown


def top_z(y, x):
    t = zt(y); rx, rz, crown = edge(t); xf = w(y) - d(t - rz) - rx
    return t + crown * (1 - abs(x) / xf) if abs(x) <= xf else t


def side_x(y, z): return w(y) - d(z)


def ws_half(y, inset=0.01):
    t = zt(y); rx, rz, _ = edge(t)
    return w(y) - d(t - rz) - rx - inset


def sd(px, py):
    """side-sheet pixel -> (Y, Z)"""
    return (-2.1685 + (px - 34) * K_SIDE, (502 - py) * K_SIDE)


# Front door (photo + side sheet): below the belt the front edge is the vertical seam at
# y=-1.42; above the belt the door frame runs forward along the A-pillar, parallel to the
# windscreen, leaving only a thin body pillar. The black mirror sail sits in that front corner.
DOOR_TOP = 1.80
BELT = 1.195
DOOR_EAR = (-1.594, BELT)             # front-lower corner of the window frame (sheet px 165)
DOOR_EAR_TOP = (-1.00, DOOR_TOP)      # stays under the roof-corner arc (ze ~ 1.83 there)
_slope = (DOOR_EAR_TOP[1] - DOOR_EAR[1]) / (DOOR_EAR_TOP[0] - DOOR_EAR[0])
GLASS_SETBACK = 0.06                  # glass front edge this far behind the door front edge (Y)


def _door_line_y(z, setback=0.0):
    return DOOR_EAR[0] + (z - DOOR_EAR[1]) / _slope + setback


DOOR_HINGE_Y = -1.42                  # hinges on the vertical front edge of the door (below the belt)
_z_hinge_top = DOOR_EAR[1] + (DOOR_HINGE_Y - DOOR_EAR[0]) * _slope     # where that edge meets the frame line
# glass: front edge on the frame line (set back), clipped at the hinge line; the black sail
# covers the corner in front of it
_zg = 1.215 + (DOOR_HINGE_Y - 0.005 - _door_line_y(1.215, GLASS_SETBACK)) * _slope
DOOR_GLASS = [(DOOR_HINGE_Y - 0.005, 1.215), (-0.355, 1.215), (-0.355, 1.76),
              (_door_line_y(1.76, GLASS_SETBACK) + 0.03, 1.76), (_door_line_y(1.745, GLASS_SETBACK), 1.745),
              (DOOR_HINGE_Y - 0.005, _zg)]
# black sail triangle at the foot of the A-pillar (body), in front of the hinge line; the mirror stands on it
SAIL = [(DOOR_EAR[0] + 0.004, BELT + 0.004), (DOOR_HINGE_Y - 0.002, BELT + 0.004), (DOOR_HINGE_Y - 0.002, _z_hinge_top)]


def _arch():
    yc, zc, ra = -1.384, 0.315, 0.378
    return [(y, max(zc + math.sqrt(max(0, ra * ra - (y - yc) ** 2)), 0.36)) for y in [-1.42 + 0.42 * i / 6 for i in range(7)]]


FRONT_DOOR = [(DOOR_HINGE_Y, _z_hinge_top)] + _arch() + [(-0.325, 0.36), (-0.325, DOOR_TOP), DOOR_EAR_TOP]
SLIDE_DOOR = [(-0.325, 0.36), (0.78, 0.36), (0.78, DOOR_TOP), (-0.325, DOOR_TOP)]
HOOD_SIDE = [(-2.20, 0.885), (-1.958, 0.885), (-1.72, 1.13), (-1.72, 1.45), (-2.20, 1.45)]


# ------------------------------------------------------------------ helpers
def mesh_obj(name, bm, mats, coll=None):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free(); me.update()
    o = bpy.data.objects.get(name) or bpy.data.objects.new(name, me)
    o.data = me
    if coll and o.name not in coll.objects:
        coll.objects.link(o)
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    return o


def remove(name):
    o = bpy.data.objects.get(name)
    if o:
        me = o.data; bpy.data.objects.remove(o)
        if me and me.users == 0:
            bpy.data.meshes.remove(me)


def addbox(bm, x0, x1, y0, y1, z0, z1):
    x0, x1 = min(x0, x1), max(x0, x1)
    v = [bm.verts.new(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        bm.faces.new([v[i] for i in f])


def prism_x(bm, poly, x0, x1):
    f = [bm.verts.new((x0, y, z)) for y, z in poly]
    b = [bm.verts.new((x1, y, z)) for y, z in poly]
    bm.faces.new(f); bm.faces.new(list(reversed(b)))
    for i in range(len(poly)):
        j = (i + 1) % len(poly)
        bm.faces.new((f[i], f[j], b[j], b[i]))


def prism_along(bm, pts, n, a, b):
    f = [bm.verts.new(Vector(q) + n * a) for q in pts]
    k = [bm.verts.new(Vector(q) + n * b) for q in pts]
    bm.faces.new(f); bm.faces.new(list(reversed(k)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((f[i], f[j], k[j], k[i]))


def side_strip(bm, y0, y1, z0, z1, proud, sides=(1, -1)):
    for s in sides:
        xa = side_x((y0 + y1) / 2, (z0 + z1) / 2) - 0.004
        addbox(bm, s * xa, s * (xa + 0.004 + proud), y0, y1, z0, z1)


# ------------------------------------------------------------------ steps
def rest_pose():
    arm = bpy.data.objects["trafic_skeleton"]
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix()
    if arm.animation_data:
        arm.animation_data.action = None
    bpy.context.view_layer.update()
    return arm


def build_body():
    body = bpy.data.objects["TRF_body"]
    bm = bmesh.new(); rings = []
    for y in STATIONS:
        P, b, top = half(y)
        loop = [(0, b)] + P + [(0, top)] + [(-x, z) for x, z in reversed(P)]
        rings.append([bm.verts.new((x, y, z)) for x, z in loop])
    n = len(rings[0])
    for A, B in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((A[i], A[j], B[j], B[i]))
    bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(body.data); bm.free()
    for p in body.data.polygons:
        p.use_smooth = True
    body.data.update()
    return body


def build_cutters():
    # windows: door glass prisms + windscreen prism (opening 3.5 cm inside the glass)
    bm = bmesh.new()
    cy = sum(p[0] for p in DOOR_GLASS) / len(DOOR_GLASS); cz = sum(p[1] for p in DOOR_GLASS) / len(DOOR_GLASS)
    door_in = [(y + (cy - y) * 0.04, z + (cz - z) * 0.06) for y, z in DOOR_GLASS]
    prism_x(bm, door_in, 0.79, 1.20)
    prism_x(bm, list(reversed(door_in)), -1.20, -0.79)
    y0, y1 = -1.67, -1.17
    p = [(-ws_half(y0, 0.045), y0, zt(y0)), (ws_half(y0, 0.045), y0, zt(y0)),
         (ws_half(y1, 0.045), y1, zt(y1)), (-ws_half(y1, 0.045), y1, zt(y1))]
    nrm = (Vector(p[3]) - Vector(p[0])).cross(Vector((1, 0, 0))).normalized()
    if nrm.z < 0:
        nrm = -nrm
    prism_along(bm, p, nrm, -0.10, 0.10)
    wc = mesh_obj("TRF_window_cutter", bm, [M["TRF_cutter"]])
    # doors and hood
    for name, poly, side in (("CUT_door_fl", FRONT_DOOR, 1), ("CUT_door_fr", FRONT_DOOR, -1), ("CUT_door_rr", SLIDE_DOOR, -1)):
        bm = bmesh.new()
        if side > 0:
            prism_x(bm, poly, 0.80, 1.25)
        else:
            prism_x(bm, list(reversed(poly)), -1.25, -0.80)
        mesh_obj(name, bm, [M["TRF_cutter"]])
    bm = bmesh.new(); prism_x(bm, list(reversed(HOOD_SIDE)), -1.3, 1.3)
    mesh_obj("CUT_hood", bm, [M["TRF_cutter"]])
    bpy.context.view_layer.update()
    return nrm


def frozen_piece(body, name, cutter):
    tmp = bpy.data.objects.new("_tmp_" + name, body.data); SC.collection.objects.link(tmp)
    for src in body.modifiers:
        if src.name in ("Arches", "Shell", "Windows"):
            m = tmp.modifiers.new(src.name, src.type)
            for attr in ("operation", "solver", "object", "material_mode", "thickness", "offset",
                         "use_even_offset", "use_self", "use_hole_tolerant"):
                if hasattr(src, attr):
                    try:
                        setattr(m, attr, getattr(src, attr))
                    except Exception:
                        pass
    mi = tmp.modifiers.new("Piece", 'BOOLEAN'); mi.operation = 'INTERSECT'; mi.solver = 'EXACT'
    mi.object = bpy.data.objects[cutter]
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp)
    o = bpy.data.objects[name]; old = o.data; o.data = me; me.name = name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return o


def mirror_x_into(src_name, dst_name):
    src, dst = bpy.data.objects[src_name], bpy.data.objects[dst_name]
    me = src.data.copy(); me.name = dst_name
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.transform(bm, matrix=Matrix.Scale(-1, 4, (1, 0, 0)), verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    old = dst.data; dst.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def build_glass(nrm):
    """Flat windscreen on the top surface (the Trafic I windscreen does not wrap round)."""
    bm = bmesh.new(); grid = []
    for y in (-1.70, -1.415, -1.13):
        xh = ws_half(y)
        grid.append([bm.verts.new((x, y, top_z(y, x) + 0.008)) for x in (-xh, 0.0, xh)])
    for A, B in zip(grid, grid[1:]):
        for i in range(2):
            bm.faces.new((A[i], A[i + 1], B[i + 1], B[i]))
    mesh_obj("TRF_windscreen", bm, [M["TRF_glass"]])
    for tag, s in (("L", 1), ("R", -1)):
        bm = bmesh.new()
        pts = [(s * (side_x(y, z) + 0.006), y, z) for y, z in DOOR_GLASS]
        if s < 0:
            pts = list(reversed(pts))
        bm.faces.new([bm.verts.new(p) for p in pts])
        mesh_obj("TRF_side_windows_" + tag, bm, [M["TRF_glass"]])
    # wipers on the glass
    def beam(bm, p0, p1, wd, h):
        p0 = Vector(p0); p1 = Vector(p1); dv = (p1 - p0).normalized()
        sv = dv.cross(nrm).normalized() * wd / 2; u = nrm * h
        q = [p0 - sv, p0 + sv, p1 + sv, p1 - sv]
        v = [bm.verts.new(x) for x in q] + [bm.verts.new(x + u) for x in q]
        for fc in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            bm.faces.new([v[i] for i in fc])
    og = lambda x, y: (x, y, top_z(y, x) + 0.016)
    bm = bmesh.new()
    beam(bm, og(-0.72, -1.655), og(-0.06, -1.685), 0.018, 0.012)
    beam(bm, og(0.02, -1.655), og(0.66, -1.685), 0.018, 0.012)
    mesh_obj("TRF_wipers", bm, [M["TRF_trim_black"]])
    # bonnet vent (on the hood)
    ys = [-1.950, -1.90, -1.795]                   # ~44 x 16 cm, as on the photo
    xv0, xv1 = 0.12, 0.56
    bm = bmesh.new()
    for a, b in zip(ys, ys[1:]):
        bm.faces.new([bm.verts.new(p) for p in [(xv0, a, top_z(a, xv0) + 0.006), (xv1, a, top_z(a, xv1) + 0.006),
                                                 (xv1, b, top_z(b, xv1) + 0.006), (xv0, b, top_z(b, xv0) + 0.006)]])
    mesh_obj("TRF_bonnet_vent", bm, [M["TRF_trim_black"]])


def build_mirrors():
    """Black plastic sail at the foot of the A-pillar, in front of the door hinge line, with the
    mirror standing on it. Both belong to the body, so the door edge stays against the body when open."""
    for n in ("TRF_sail_triangles", "TRF_mirror_feet_L", "TRF_mirror_feet_R", "TRF_mirror_arms", "TRF_mirror_support"):
        remove(n)

    def rrect(x0, x1, z0, z1, c):
        return [(x0 + c, z0), (x1 - c, z0), (x1, z0 + c), (x1, z1 - c), (x1 - c, z1), (x0 + c, z1), (x0, z1 - c), (x0, z0 + c)]

    def extrude_xz(bm, outline, y0, y1, s):
        f = [bm.verts.new((s * x, y0, z)) for x, z in outline]
        b = [bm.verts.new((s * x, y1, z)) for x, z in outline]
        faces = [bm.faces.new(f), bm.faces.new(list(reversed(b)))]
        for i in range(len(outline)):
            j = (i + 1) % len(outline)
            faces.append(bm.faces.new((f[i], b[i], b[j], f[j])))
        return faces

    HY0, HY1 = -1.505, -1.445
    xs = side_x(-1.47, 1.30) + 0.02
    for tag, s in (("L", 1), ("R", -1)):
        c = bpy.data.collections["PART_body"]
        bm = bmesh.new()
        v0 = [bm.verts.new((s * (side_x(y, z) - 0.003), y, z)) for y, z in SAIL]
        v1 = [bm.verts.new((s * (side_x(y, z) + 0.022), y, z)) for y, z in SAIL]
        bm.faces.new(v0); bm.faces.new(list(reversed(v1)))
        for i in range(3):
            j = (i + 1) % 3
            bm.faces.new((v0[i], v0[j], v1[j], v1[i]))
        sail = mesh_obj("TRF_mirror_support_" + tag, bm, [M["TRF_trim_black"]], c)
        bm = bmesh.new()
        extrude_xz(bm, rrect(xs + 0.015, 1.060, 1.225, 1.465, 0.03), HY0, HY1, s)
        glass = extrude_xz(bm, rrect(xs + 0.027, 1.048, 1.237, 1.453, 0.022), HY1, HY1 + 0.003, s)
        extrude_xz(bm, [(xs - 0.01, 1.245), (xs + 0.03, 1.245), (xs + 0.03, 1.272), (xs - 0.01, 1.272)], -1.49, -1.46, s)
        for f in bm.faces:
            f.material_index = 1 if f in glass else 0
        head = mesh_obj("TRF_mirror_heads_" + tag, bm, [M["TRF_trim_black"], M["TRF_glass"]], c)
        for o in (sail, head):
            o.parent = None
            o.matrix_world = Matrix()
            for uc in list(o.users_collection):
                if uc != c:
                    uc.objects.unlink(o)


def rig_front_doors():
    """Put the front-door hinges on the door's vertical front edge and rebuild their opening actions."""
    arm = bpy.data.objects["trafic_skeleton"]
    kids = {}
    for bn in ("door_fl_bone", "door_fr_bone"):
        kids[bn] = [o for o in bpy.data.objects if o.parent == arm and o.parent_bone == bn]
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm; arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for bn, s in (("door_fl_bone", 1), ("door_fr_bone", -1)):
        b = arm.data.edit_bones[bn]
        b.head = (s * 0.95, DOOR_HINGE_Y, 0.40); b.tail = (s * 0.95, DOOR_HINGE_Y, 1.20); b.roll = 0
    bpy.ops.object.mode_set(mode='OBJECT')
    for bn, objs in kids.items():
        for o in objs:
            o.parent = None
            o.matrix_world = Matrix()      # all pieces are modelled in world space at rest
            o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bn
            bpy.context.view_layer.update()
            o.matrix_world = Matrix()
    for an, bn, deg in (("door_fl_opening", "door_fl_bone", -70), ("door_fr_opening", "door_fr_bone", 70)):
        act = bpy.data.actions.get(an)
        if act:
            bpy.data.actions.remove(act)
        act = bpy.data.actions.new(an); act.use_fake_user = True
        if not arm.animation_data:
            arm.animation_data_create()
        arm.animation_data.action = act
        pb = arm.pose.bones[bn]; pb.rotation_mode = 'QUATERNION'
        x = 0.95 if deg < 0 else -0.95
        h = Vector((x, DOOR_HINGE_Y, 0))
        for fr, T in ((1, Matrix()), (20, Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, 'Z') @ Matrix.Translation(-h))):
            pb.matrix = T @ arm.data.bones[bn].matrix_local
            bpy.context.view_layer.update()
            pb.keyframe_insert("location", frame=fr, group=bn)
            pb.keyframe_insert("rotation_quaternion", frame=fr, group=bn)
        pb.matrix_basis = Matrix()
    arm.animation_data.action = None
    bpy.context.view_layer.update()


def build_corner_lamps():
    """Front indicator under each headlamp, up to the corner but not onto the side (photo), plus side repeater."""
    body_c = bpy.data.collections["PART_body"]
    for n in ("TRF_corner_band", "TRF_corner_lamps"):
        remove(n)
    z0, z1, proud = 0.565, 0.600, 0.012
    # plan path of the lens: along the flat front face only
    path = [(0.575, YF), (w(YF) - 0.004, YF)]
    bm = bmesh.new()
    for s in (1, -1):
        pts = []
        for i, (x, y) in enumerate(path):
            a = path[max(i - 1, 0)]; b = path[min(i + 1, len(path) - 1)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, ty) or 1.0
            nx, ny = ty / ln, -tx / ln          # outward normal of the path in plan (x>0 side)
            pts.append((x, y, nx, ny))
        inner = [((x - nx * 0.004) * s, y - ny * 0.004) for x, y, nx, ny in pts]
        outer = [((x + nx * proud) * s, y + ny * proud) for x, y, nx, ny in pts]
        ring = inner + list(reversed(outer))      # closed outline in plan
        if s < 0:
            ring = list(reversed(ring))
        lo = [bm.verts.new((x, y, z0)) for x, y in ring]
        hi = [bm.verts.new((x, y, z1)) for x, y in ring]
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
        k = len(pts)
        for i in range(k - 1):                     # caps, as quads along the strip
            bm.faces.new((hi[i], hi[i + 1], hi[n - 2 - i], hi[n - 1 - i]))
            bm.faces.new((lo[n - 1 - i], lo[n - 2 - i], lo[i + 1], lo[i]))
    mesh_obj("TRF_indicators", bm, [M["TRF_indicator"]])
    bm = bmesh.new()
    side_strip(bm, -1.739, -1.665, 0.810, 0.850, 0.012)        # side repeater
    mesh_obj("TRF_corner_indicators", bm, [M["TRF_indicator"]], body_c)


def build_rubstrip():
    """Body-coloured crease strip swept along the real side surface, cut at the door seams.
    Sections are dense only towards the nose, where the body narrows."""
    z0, z1, proud = 0.825, 0.850, 0.008
    ys = [-2.02, -1.95, -1.88, -1.80, -1.70, -1.60, -1.50, -1.42, -1.20, -0.95, -0.325, 0.78, 2.10]
    owner = {
        "TRF_rubstrip_body": lambda s, y: y < -1.42 or (s > 0 and y > -0.325) or (s < 0 and y > 0.78),
        "TRF_rubstrip_door_fl": lambda s, y: s > 0 and -1.42 < y < -0.325,
        "TRF_rubstrip_door_fr": lambda s, y: s < 0 and -1.42 < y < -0.325,
        "TRF_rubstrip_door_rr": lambda s, y: s < 0 and -0.325 < y < 0.78,
    }
    bms = {n: bmesh.new() for n in owner}

    def ring(bm, s, y):
        xi = side_x(y, (z0 + z1) / 2) - 0.002
        xo = xi + 0.002 + proud
        return [bm.verts.new(p) for p in [(s * xi, y, z0), (s * xo, y, z0), (s * xo, y, z1), (s * xi, y, z1)]]

    for s in (1, -1):
        runs = []                              # consecutive intervals with the same owner
        for y0, y1 in zip(ys, ys[1:]):
            n = next(k for k, f in owner.items() if f(s, (y0 + y1) / 2))
            if runs and runs[-1][0] == n:
                runs[-1][1].append(y1)
            else:
                runs.append((n, [y0, y1]))
        for n, yy in runs:
            bm = bms[n]
            rings = [ring(bm, s, y) for y in yy]
            for A, B in zip(rings, rings[1:]):
                for i in range(4):
                    j = (i + 1) % 4
                    bm.faces.new((A[i], A[j], B[j], B[i]))
            bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    for n, bm in bms.items():
        o = bpy.data.objects.get(n)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(o.data); bm.free(); o.data.update()


def build_bulkhead():
    """Partition behind the seats, kept 4 cm inside the shell (the shell is 1.5 cm thick)."""
    P, b, top = half(-0.12)
    sec = [(0.0, b)] + P + [(0.0, top)]           # half section, bottom centre -> roof centre
    inset = 0.045
    pts = []
    for i, (x, z) in enumerate(sec):              # offset every point inward, normal to the wall
        x0, z0 = sec[max(i - 1, 0)]; x1, z1 = sec[min(i + 1, len(sec) - 1)]
        tx, tz = x1 - x0, z1 - z0
        ln = math.hypot(tx, tz) or 1.0
        nx, nz = -tz / ln, tx / ln                 # inward normal (section runs anticlockwise)
        pts.append((max(x + nx * inset, 0.0), z + nz * inset))
    loop = pts + [(-x, z) for x, z in reversed(pts[1:-1])]
    bm = bmesh.new()
    f = [bm.verts.new((x, -0.12, z)) for x, z in loop]
    k = [bm.verts.new((x, -0.095, z)) for x, z in loop]
    bm.faces.new(f); bm.faces.new(list(reversed(k)))
    for i in range(len(loop)):
        j = (i + 1) % len(loop)
        bm.faces.new((f[i], f[j], k[j], k[i]))
    mesh_obj("TRF_bulkhead", bm, [M["TRF_interior"]])


def build_drip_line():
    """Crease continuing the top edge of the front door towards the rear (photo, side sheet)."""
    z0, z1, proud = 1.790, 1.810, 0.006
    runs = {"TRF_drip_body": [(1, [-0.325, 0.50, 1.60, 2.10]), (-1, [0.78, 1.60, 2.10])],
            "TRF_drip_door_rr": [(-1, [-0.325, 0.78])]}
    colls = {"TRF_drip_body": ("PART_body", None), "TRF_drip_door_rr": ("PART_DoorRearRight_slide", "door_rr_bone")}
    arm = bpy.data.objects["trafic_skeleton"]
    for name, rr in runs.items():
        bm = bmesh.new()
        for s, ys in rr:
            rings = []
            for y in ys:
                xi = side_x(y, (z0 + z1) / 2) - 0.003
                xo = xi + 0.003 + proud
                rings.append([bm.verts.new(p) for p in [(s * xi, y, z0), (s * xo, y, z0), (s * xo, y, z1), (s * xi, y, z1)]])
            for A, B in zip(rings, rings[1:]):
                for i in range(4):
                    j = (i + 1) % 4
                    bm.faces.new((A[i], A[j], B[j], B[i]))
            bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
        cname, bone = colls[name]
        o = mesh_obj(name, bm, [M["TRF_paint"]], bpy.data.collections[cname])
        if bone and o.parent is None:
            o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bone
            bpy.context.view_layer.update(); o.matrix_world = Matrix()


WHEELS = {"front": -1.384, "rear": 1.416}
ARCH_ZC = 0.315
HOUSING_R = 0.39            # wheel housing, a little larger than the arch cut (0.365)


def build_floors():
    """Cab and cargo floors at full width, with arched wheel housings over the wheels
    (they close the wheel wells from the inside, so an open door no longer shows a void)."""
    XI, XW = 0.58, 0.935                          # housing inner face / inside of the side wall
    floors = {"TRF_cab_floor": (-1.72, -0.12, 0.62, 0.66, "front"),
              "TRF_cargo_floor": (-0.10, 2.12, 0.50, 0.54, "rear")}
    for name, (y0, y1, z0, z1, wheel) in floors.items():
        yc = WHEELS[wheel]
        dy = math.sqrt(HOUSING_R ** 2 - (z0 - ARCH_ZC) ** 2)    # housing meets the floor underside
        ha, hb = yc - dy, yc + dy                  # housing footprint along y at floor level
        bm = bmesh.new()
        addbox(bm, -XI, XI, y0, y1, z0, z1)        # centre strip, full length
        for s in (1, -1):
            for ya, yb in ((y0, max(y0, ha)), (min(y1, hb), y1)):
                if yb - ya > 0.01:
                    addbox(bm, s * XI, s * XW, ya, yb, z0, z1)
        mesh_obj(name, bm, [M["TRF_interior"]])
    # arched housings: arc in (y, z) above the floor, extruded across x from XI to the wall
    bm = bmesh.new()
    for wheel, zf in (("front", 0.62), ("rear", 0.50)):
        yc = WHEELS[wheel]
        a0 = math.asin((zf - ARCH_ZC) / HOUSING_R)
        arc = [(yc + HOUSING_R * math.cos(t), ARCH_ZC + HOUSING_R * math.sin(t))
               for t in [a0 + (math.pi - 2 * a0) * i / 10 for i in range(11)]]
        for s in (1, -1):
            inner = [bm.verts.new((s * XI, y, z)) for y, z in arc]
            outer = [bm.verts.new((s * XW, y, z)) for y, z in arc]
            for i in range(len(arc) - 1):
                bm.faces.new((inner[i], inner[i + 1], outer[i + 1], outer[i]))
            bm.faces.new(inner)                    # end cap towards the centre of the vehicle
    mesh_obj("TRF_wheel_housings", bm, [M["TRF_interior"]], bpy.data.collections["PART_interior"])


def build_underbody():
    """Thin dark undertray under the floor, and the rear cross-member under the rear doors."""
    bm = bmesh.new(); addbox(bm, -0.58, 0.58, -1.95, 2.05, 0.26, 0.32)
    mesh_obj("TRF_underbody", bm, [M["TRF_trim_black"]])
    bm = bmesh.new(); addbox(bm, -0.72, 0.72, 1.98, 2.14, 0.265, 0.325)
    mesh_obj("TRF_rear_step", bm, [M["TRF_trim_black"]])


def build_seats():
    """Front seats, low enough for a full-size character: the vehicle is scaled 0.85 in game but
    the characters are not (headroom above the seat about 0.9 m once scaled, as on other vans)."""
    def quadbox(bm, P):
        v = [bm.verts.new(p) for p in P]
        for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            bm.faces.new([v[i] for i in f])
    for tag, cx in (("L", 0.45), ("R", -0.45)):
        bm = bmesh.new()
        addbox(bm, cx - 0.20, cx + 0.20, -0.74, -0.40, 0.66, 0.80)          # pedestal
        addbox(bm, cx - 0.23, cx + 0.23, -0.79, -0.36, 0.80, 0.90)          # cushion
        quadbox(bm, [(cx - 0.23, -0.40, 0.88), (cx + 0.23, -0.40, 0.88), (cx + 0.23, -0.28, 0.88), (cx - 0.23, -0.28, 0.88),
                     (cx - 0.22, -0.31, 1.46), (cx + 0.22, -0.31, 1.46), (cx + 0.22, -0.19, 1.46), (cx - 0.22, -0.19, 1.46)])
        quadbox(bm, [(cx - 0.13, -0.30, 1.46), (cx + 0.13, -0.30, 1.46), (cx + 0.13, -0.20, 1.46), (cx - 0.13, -0.20, 1.46),
                     (cx - 0.13, -0.28, 1.60), (cx + 0.13, -0.28, 1.60), (cx + 0.13, -0.18, 1.60), (cx - 0.13, -0.18, 1.60)])
        mesh_obj("TRF_seats_" + tag, bm, [M["TRF_seat_fabric"]])


def run():
    rest_pose()
    body = build_body()
    nrm = build_cutters()
    bpy.context.view_layer.update()
    frozen_piece(body, "trafic_door_fr", "CUT_door_fr")
    mirror_x_into("trafic_door_fr", "trafic_door_fl")
    frozen_piece(body, "trafic_door_rr", "CUT_door_rr")
    frozen_piece(body, "trafic_hood", "CUT_hood")
    build_glass(nrm)
    build_mirrors()
    rig_front_doors()
    build_corner_lamps()
    build_rubstrip()
    build_bulkhead()
    build_drip_line()
    build_floors()
    build_underbody()
    build_seats()
    bpy.app.driver_namespace['trf_body'] = {'zt': zt, 'w': w, 'd': d, 'half': half, 'top_z': top_z,
                                            'side_x': side_x, 'edge': edge}
    return {"door_glass": DOOR_GLASS, "hinge_y": DOOR_HINGE_Y}


RESULT = run()
