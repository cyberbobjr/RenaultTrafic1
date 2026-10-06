"""Export the Trafic I to FBX for Project Zomboid, the way the vanilla animated-door car is built.

Reference: media/models_X/vehicles/ModernCarWithDoors.blend (vanilla). In Blender the vehicle faces
+Y with its left side towards -X; one armature at the origin (root bone + one bone per moving
part); EVERY mesh, body included, is parented to the armature and skinned (the body to the root
bone); default FBX axes. The game applies node transforms to meshes
(jassimp/ProcessedAiScene.initMeshTransform), so nothing is baked (bake_space_transform is known
to break armatures).

Our working scene faces -Y with the left side towards +X and the mesh origin on the ground, so
the export works on COPIES: rotated 180 deg about Z, lowered by CHASSIS_HEIGHT (the game draws
wheels, parts and seats relative to the model origin, see BaseVehicle.updateTransform), turned
to the game axes (Y up), transforms applied to vertices and bones. The armature copy is named
VehicleSkeleton: ImportedSkeleton only recognises a vehicle skeleton by that node name and
otherwise takes the whole scene, mesh nodes included, as the skeleton. No FBX node may carry a
rotation or scale: the skinning already includes the skeleton node's keyed transform and the
renderer multiplies the skinned mesh by its node transform again
(ModelInstanceRenderData.postMultiplyMeshTransform), so animated parts would get it twice. Bone-local animation keys stay valid through that rigid move.
The game drops everything up to the first '|' of an animation name (ImportedSkeleton), so
"<armature>|door_fl_opening" loads as "door_fl_opening".

Run inside Blender after trafic_bake_textures.py:
    exec(open(r"...\\Assets\\tools\\trafic_export_fbx.py", encoding="utf-8").read(), {"__name__": "trafic_export"})
"""
import bpy, os, math, shutil
from mathutils import Matrix

PROJECT = r"C:\Users\cyber\Zomboid\Workshop\RenaultTrafic1"
OUTDIR = os.path.join(PROJECT, r"Contents\mods\batman_RenaultTrafic1\common\media\models_X\vehicles")
TEXDIR = os.path.join(PROJECT, r"Contents\mods\batman_RenaultTrafic1\common\media\textures\Vehicles")
BODY_FBX = os.path.join(OUTDIR, "Vehicles_batman_RenaultTraficI.fbx")
WHEEL_FBX = os.path.join(OUTDIR, "Vehicles_batman_RenaultTraficI_Wheel.fbx")
CHASSIS_HEIGHT = 1.0
ACTIONS = ["door_fl_opening", "door_fr_opening", "door_rr_opening", "trunk_opening",
           "hood_opening", "window_fl_opening", "window_fr_opening"]
SC = bpy.data.scenes["Trafic_Ebauche"]
ROOT_BONE = "trafic_root"
SKELETON_NODE = "VehicleSkeleton"     # the name the game looks for (jassimp/ImportedSkeleton)
# Blender (x, y, z) -> game (x, z, -y): what the default -Z/Y axis conversion did on the nodes,
# now applied to the data together with the 180 deg turn and the lowering to chassis height.
TO_GAME = Matrix.Rotation(-math.pi / 2, 4, 'X')
# Parts are masked to their bone (model script boneWeight) and a child part (window, parent =
# DoorFrontLeft) shares its parent's animation player (BaseVehicle.ModelInfo.getAnimationPlayer),
# so a window follows its door. Masked bones keep an identity local transform
# (AnimationPlayer.updateBoneAnimationTransform): the bones above the moving ones (VehicleSkeleton,
# root bone) must therefore rest at the identity, like the mesh nodes.
# Identity axes and no unit scaling: every FBX node keeps an identity transform and the vertices
# already hold the game's coordinates (Y up, metres). The game multiplies a skinned mesh by its
# node transform AFTER skinning, and the skinning itself already contains the skeleton node's
# keyed transform, so any rotation or scale on the nodes ends up applied twice to animated parts.
# Blender converts metres to FBX centimetres with a x100 node scale; exporting with the scene unit
# set to 0.01 makes that factor 1, so the raw vertex values stay in metres (script scale 1.0).
EXPORT_UNIT = 0.01
COMMON = dict(apply_unit_scale=True, global_scale=1.0, apply_scale_options='FBX_SCALE_NONE',
              bake_space_transform=False, axis_forward='Y', axis_up='Z', use_mesh_modifiers=True,
              mesh_smooth_type='FACE', use_tspace=False, add_leaf_bones=False, primary_bone_axis='Y',
              secondary_bone_axis='X', armature_nodetype='NULL', path_mode='STRIP', use_selection=True)


def layer(name, root=None):
    root = root or bpy.context.view_layer.layer_collection
    if root.name == name:
        return root
    for c in root.children:
        r = layer(name, c)
        if r:
            return r


def deselect_all():
    for o in bpy.context.selected_objects:
        o.select_set(False)


def ensure_root_bone(arm):
    if ROOT_BONE in arm.data.bones:
        return
    deselect_all()
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    root = eb.new(ROOT_BONE)
    root.head = (0, 0, 0); root.tail = (0, 0, 1.0); root.roll = 0
    for b in eb:
        if b is not root and b.parent is None:
            b.parent = root
    bpy.ops.object.mode_set(mode='OBJECT')


def reset_root_bone(arm_c):
    """Root bone at the identity (origin, along the game's up axis, no roll). Children keep their
    armature-space rest (not connected) and the clips are bone-relative, so nothing moves."""
    deselect_all()
    bpy.context.view_layer.objects.active = arm_c
    arm_c.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    root = arm_c.data.edit_bones[ROOT_BONE]
    for b in root.children:
        b.use_connect = False
    root.head = (0.0, 0.0, 0.0); root.tail = (0.0, 0.2, 0.0); root.roll = 0.0
    bpy.ops.object.mode_set(mode='OBJECT')


def make_copies(arm, parts, coll):
    """Clean-named copies: originals get a temporary suffix so the FBX nodes keep the part names."""
    renamed = []
    for o in [arm] + parts:
        renamed.append((o, o.name))
        o.name = o.name + "__src"
    arm_c = arm.copy(); arm_c.data = arm.data.copy(); arm_c.name = SKELETON_NODE
    coll.objects.link(arm_c)
    arm_c.animation_data_clear()
    arm_c.animation_data_create()
    copies = []
    for o in parts:
        c = o.copy(); c.data = o.data.copy(); c.name = o.name.replace("__src", "")
        coll.objects.link(c)
        for m in list(c.modifiers):
            c.modifiers.remove(m)
        if not c.vertex_groups:                       # fixed parts follow the root bone
            g = c.vertex_groups.new(name=ROOT_BONE)
            g.add([v.index for v in c.data.vertices], 1.0, 'REPLACE')
        md = c.modifiers.new("Armature", 'ARMATURE'); md.object = arm_c
        c.parent = arm_c
        c.matrix_parent_inverse = Matrix()
        copies.append(c)
    return arm_c, copies, renamed


def run():
    saved_unit = SC.unit_settings.scale_length
    SC.unit_settings.scale_length = EXPORT_UNIT
    try:
        return export()
    finally:
        SC.unit_settings.scale_length = saved_unit


def export():
    os.makedirs(OUTDIR, exist_ok=True)
    arm = bpy.data.objects["trafic_skeleton"]
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix()
    if arm.animation_data:
        arm.animation_data.action = None
    layer("PART_skeleton").hide_viewport = False
    layer("EXPORT_trafic").hide_viewport = False
    ensure_root_bone(arm)
    parts = [o for o in bpy.data.collections["EXPORT_trafic"].objects if o.type == 'MESH']

    tmp = bpy.data.collections.new("FBX_export_tmp")
    SC.collection.children.link(tmp)
    arm_c, copies, renamed = make_copies(arm, parts, tmp)
    vehicle_mat = bpy.data.materials.get("TrafI_vehicle") or bpy.data.materials.new("TrafI_vehicle")
    for c in copies:                                  # one material per node: no sub-mesh split
        c.data.materials.clear(); c.data.materials.append(vehicle_mat)
        for p in c.data.polygons:
            p.material_index = 0

    # rigid move to the game's layout, then apply it to vertices and bones
    arm_c.matrix_world = TO_GAME @ Matrix.Translation((0.0, 0.0, -CHASSIS_HEIGHT)) @ Matrix.Rotation(math.pi, 4, 'Z')
    bpy.context.view_layer.update()
    deselect_all()
    for o in [arm_c] + copies:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm_c
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    reset_root_bone(arm_c)

    ad = arm_c.animation_data
    for name in ACTIONS:
        tr = ad.nla_tracks.new(); tr.name = name
        st = tr.strips.new(name, 1, bpy.data.actions[name]); st.name = name
    bpy.context.view_layer.update()
    deselect_all()
    for o in [arm_c] + copies:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm_c
    bpy.ops.export_scene.fbx(filepath=BODY_FBX, object_types={'ARMATURE', 'MESH'}, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=True,
                             bake_anim_use_all_bones=True, bake_anim_force_startend_keying=True,
                             bake_anim_step=1.0, bake_anim_simplify_factor=0.0, **COMMON)
    summary = {c.name: [round(min(v.co.z for v in c.data.vertices), 3), round(max(v.co.z for v in c.data.vertices), 3),
                        round(min(v.co.y for v in c.data.vertices), 3), round(max(v.co.y for v in c.data.vertices), 3),
                        round(min(v.co.x for v in c.data.vertices), 3), round(max(v.co.x for v in c.data.vertices), 3)]
               for c in copies if c.name in ("TrafI_body", "TrafI_door_fl")}
    summary["note"] = "game axes: x, y=up, z (z = -Blender y)"
    summary["bones"] = {b.name: [round(x, 3) for x in b.head_local] for b in arm_c.data.bones}

    # clean up the copies, give the originals their names back
    for o in [arm_c] + copies:
        d = o.data
        bpy.data.objects.remove(o)
        if d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.armatures).remove(d)
    bpy.data.collections.remove(tmp)
    for o, n in renamed:
        o.name = n

    # wheel: same layout (turned round: outer face towards -X = the left side), origin at the hub
    wme = bpy.data.meshes["TRF_wheel"].copy()
    wme.transform(TO_GAME @ Matrix.Rotation(math.pi, 4, 'Z'))
    # Two identical UV sets: a static FBX mesh is laid out position, normal, then one attribute per
    # UV set from location 2 (jassimp/ImportedStaticMesh), but vehiclewheel_static.vert reads its
    # UVs at location 3 (location 2 is the tangent of the vanilla .txt wheel). With a single set
    # the wheel samples one texel and shows no texture.
    src_uv = wme.uv_layers.active
    dup = wme.uv_layers.new(name="UVWheelShader")
    for a, b in zip(src_uv.data, dup.data):
        b.uv = a.uv
    wo = bpy.data.objects.new("TrafI_wheel", wme)
    SC.collection.objects.link(wo)
    deselect_all(); wo.select_set(True); bpy.context.view_layer.objects.active = wo
    common_w = dict(COMMON); common_w["object_types"] = {'MESH'}
    bpy.ops.export_scene.fbx(filepath=WHEEL_FBX, bake_anim=False, **common_w)
    bpy.data.objects.remove(wo); bpy.data.meshes.remove(wme)

    shutil.copy2(os.path.join(PROJECT, r"Assets\textures\trafic_wheel.png"),
                 os.path.join(TEXDIR, "Vehicles_batman_RenaultTraficI_Wheel.png"))
    return {"body": BODY_FBX, "wheel": WHEEL_FBX, "summary": summary}


RESULT = run()
