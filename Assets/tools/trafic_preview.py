"""Show the export meshes in Blender with the baked texture (paint preview applied).

Run inside Blender after trafic_bake_textures.py and trafic_paint_preview.py.
Glass is drawn see-through. The mod now uses the authorised glass shader in game;
Blender lighting/transparency are previews, not validation of the game renderer.
"""
import bpy

SC = bpy.data.scenes["Trafic_Ebauche"]
PREVIEW = r"C:\Users\cyber\Zomboid\Workshop\RenaultTrafic1\Assets\build\trafic_preview_white.png"


def layer(name, root=None):
    root = root or bpy.context.view_layer.layer_collection
    if root.name == name:
        return root
    for c in root.children:
        r = layer(name, c)
        if r:
            return r


def run(image_path=PREVIEW):
    for c in bpy.data.collections["TRF_parts"].children:
        if c.name.startswith("PART_"):
            layer(c.name).hide_viewport = True
    layer("EXPORT_trafic").hide_viewport = False
    SC.display.shading.color_type = 'TEXTURE'
    atlas = bpy.data.materials["TrafI_preview"]
    img = bpy.data.images.load(image_path, check_existing=True); img.reload()
    atlas.node_tree.nodes["Atlas"].image = img
    glass = bpy.data.materials.get("TrafI_preview_glass") or bpy.data.materials.new("TrafI_preview_glass")
    glass.diffuse_color = (0.10, 0.14, 0.17, 0.28)
    for o in bpy.data.collections["EXPORT_trafic"].objects:
        me = o.data
        src = [m.name if m else "" for m in me.materials]
        if "TrafI_preview" in src and "TrafI_preview_glass" in src:
            continue                      # already set
        is_glass = [n == "TRF_glass" for n in src]
        idx = [p.material_index for p in me.polygons]
        me.materials.clear(); me.materials.append(atlas); me.materials.append(glass)
        for p, i in zip(me.polygons, idx):
            p.material_index = 1 if (i < len(is_glass) and is_glass[i]) else 0
        if not any(md.type == 'NODES' for md in o.modifiers):
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
                bpy.ops.object.shade_auto_smooth(angle=0.61)
    for a in bpy.context.window.screen.areas:
        if a.type == 'VIEW_3D':
            a.spaces.active.shading.color_type = 'TEXTURE'


run()
