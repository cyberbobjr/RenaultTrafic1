"""Bake geometry-derived surface relief without touching the validated export meshes.

Run in Blender (live or background) after trafic_bake_textures.py. The existing
UVMap stays unchanged. Only copies in an isolated scene are used for baking.
Then run trafic_raster.py and trafic_paint_preview.py with system Python.
"""
import os
import bpy
import numpy as np

PROJECT = r"C:\Users\cyber\Zomboid\Workshop\RenaultTrafic1"


def run(project=PROJECT):
    output = os.path.join(project, "Assets", "build")
    os.makedirs(output, exist_ok=True)
    original_scene = bpy.context.window.scene
    scene = bpy.data.scenes.new("Trafic_surface_bake_TEMP")
    objects, images, meshes = [], [], []
    material = bpy.data.materials.new("Trafic_surface_bake_TEMP")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    target = nodes.new("ShaderNodeTexImage")
    emission = nodes.new("ShaderNodeEmission")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(emission.outputs[0], out.inputs["Surface"])
    ao = nodes.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.16
    ao.samples = 32
    geometry = nodes.new("ShaderNodeNewGeometry")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geometry.outputs["Normal"], separate.inputs[0])
    normal = nodes.new("ShaderNodeMath")
    normal.operation = 'MULTIPLY_ADD'
    normal.inputs[1].default_value = 0.5
    normal.inputs[2].default_value = 0.5
    links.new(separate.outputs["Z"], normal.inputs[0])
    try:
        bpy.context.window.scene = scene
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = 16
        scene.render.bake.margin = 3
        scene.render.bake.use_clear = False
        for source in bpy.data.collections["EXPORT_trafic"].objects:
            if source.type != 'MESH':
                continue
            obj = bpy.data.objects.new(source.name + "_surface_TEMP", source.data.copy())
            meshes.append(obj.data)
            obj.matrix_world = source.matrix_world.copy()
            scene.collection.objects.link(obj)
            obj.data.materials.clear()
            obj.data.materials.append(material)
            for poly in obj.data.polygons:
                poly.material_index = 0
            obj.data.uv_layers.active = obj.data.uv_layers["UVMap"]
            obj.data.uv_layers["UVMap"].active_render = True
            objects.append(obj)
        # One mesh prevents per-object baking from clearing or dilating another
        # object's islands; all parts retain their original positions and UVs.
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        joined = bpy.context.view_layer.objects.active
        objects = [joined]
        for name, socket in (("trafic_ao", ao.outputs["AO"]),
                             ("trafic_normal_z", normal.outputs[0])):
            img = bpy.data.images.new(name + "_TEMP", width=1024, height=1024,
                                      alpha=False, float_buffer=True)
            images.append(img)
            img.colorspace_settings.name = 'Non-Color'
            img.pixels.foreach_set(np.ones(1024 * 1024 * 4, dtype=np.float32))
            target.image = img
            nodes.active = target
            links.new(socket, emission.inputs["Color"])
            bpy.ops.object.bake(type='EMIT')
            img.filepath_raw = os.path.join(output, name + ".png")
            img.file_format = 'PNG'
            img.save()
            print("written", img.filepath_raw, flush=True)
    finally:
        bpy.context.window.scene = original_scene
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        bpy.data.scenes.remove(scene)
        bpy.data.materials.remove(material)
        for img in images:
            bpy.data.images.remove(img)


if __name__ == "__main__":
    run()
