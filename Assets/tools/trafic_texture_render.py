"""Render atlas previews on copies, using emission to show the baked relief alone.

Usage: blender -b <blend> --python trafic_texture_render.py -- <project> [backup]
These are Blender texture previews, not screenshots or a simulation of PZ lighting.
The live scene, original materials, geometry, UVs and exported FBX stay untouched.
"""
import os
import sys
import bpy
from mathutils import Vector


def run(project, backup=None):
    original_scene = bpy.context.window.scene
    scene = bpy.data.scenes.new("Trafic_texture_render_TEMP")
    objects, materials, images = [], [], []
    world = bpy.data.worlds.new("Trafic_texture_render_TEMP")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.65, .65, .65, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .8
    atlas = bpy.data.materials.new("Trafic_texture_emission_TEMP")
    materials.append(atlas)
    atlas.use_nodes = True
    nodes, links = atlas.node_tree.nodes, atlas.node_tree.links
    nodes.clear()
    texture = nodes.new("ShaderNodeTexImage")
    texture.interpolation = 'Linear'
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(texture.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs[0], output.inputs["Surface"])
    # Blender approximation of the authorised glass shader; not a PZ render.
    glass = bpy.data.materials.new("Trafic_texture_glass_TEMP")
    materials.append(glass)
    glass.use_nodes = True
    gn, gl = glass.node_tree.nodes, glass.node_tree.links
    gn.clear()
    glass_texture = gn.new("ShaderNodeTexImage")
    glass_emission = gn.new("ShaderNodeEmission")
    clear = gn.new("ShaderNodeBsdfTransparent")
    mix = gn.new("ShaderNodeMixShader")
    glass_output = gn.new("ShaderNodeOutputMaterial")
    gl.new(glass_texture.outputs['Color'], glass_emission.inputs['Color'])
    gl.new(clear.outputs[0], mix.inputs[1])
    gl.new(glass_emission.outputs[0], mix.inputs[2])
    # Make rubber seals opaque: their sRGB brightness is below the glass range.
    separate = gn.new("ShaderNodeSeparateColor")
    separate.mode = 'RGB'
    gl.new(glass_texture.outputs['Color'], separate.inputs['Color'])
    max_rg = gn.new("ShaderNodeMath"); max_rg.operation = 'MAXIMUM'
    max_rgb = gn.new("ShaderNodeMath"); max_rgb.operation = 'MAXIMUM'
    gl.new(separate.outputs[0], max_rg.inputs[0])
    gl.new(separate.outputs[1], max_rg.inputs[1])
    gl.new(max_rg.outputs[0], max_rgb.inputs[0])
    gl.new(separate.outputs[2], max_rgb.inputs[1])
    is_glass = gn.new("ShaderNodeMath"); is_glass.operation = 'GREATER_THAN'
    is_glass.inputs[1].default_value = .07324  # linear value of sRGB 0.30
    gl.new(max_rgb.outputs[0], is_glass.inputs[0])
    opacity = gn.new("ShaderNodeMath"); opacity.operation = 'MULTIPLY_ADD'
    opacity.inputs[1].default_value = -.72
    opacity.inputs[2].default_value = 1
    gl.new(is_glass.outputs[0], opacity.inputs[0])
    gl.new(opacity.outputs[0], mix.inputs[0])
    gl.new(mix.outputs[0], glass_output.inputs['Surface'])
    glass.surface_render_method = 'DITHERED'
    try:
        bpy.context.window.scene = scene
        scene.render.engine = 'BLENDER_EEVEE'
        scene.render.resolution_x, scene.render.resolution_y = 1000, 720
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.film_transparent = False
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
        scene.view_settings.exposure = 0
        scene.view_settings.gamma = 1
        for source in bpy.data.collections['EXPORT_trafic'].objects:
            if source.type != 'MESH':
                continue
            obj = bpy.data.objects.new(source.name + '_render_TEMP', source.data.copy())
            obj.matrix_world = source.matrix_world.copy()
            scene.collection.objects.link(obj)
            obj.data.materials.clear()
            obj.data.materials.append(glass if source.name in (
                'TrafI_windshield', 'TrafI_window_fl', 'TrafI_window_fr') else atlas)
            for poly in obj.data.polygons:
                poly.material_index = 0
            obj.data.uv_layers['UVMap'].active_render = True
            objects.append(obj)
        floor_z = -.008
        for source in bpy.data.collections['TRF_wheels'].objects:
            if source.type != 'MESH':
                continue
            obj = bpy.data.objects.new(source.name + '_render_TEMP', source.data.copy())
            obj.matrix_world = source.matrix_world.copy()
            scene.collection.objects.link(obj)
            objects.append(obj)
            floor_z = min(floor_z, min((obj.matrix_world @ Vector(corner)).z
                                      for corner in obj.bound_box) - .008)
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, floor_z))
        plane = bpy.context.object
        objects.append(plane)
        floor = bpy.data.materials.new('Trafic_texture_floor_TEMP')
        floor.diffuse_color = (.12, .14, .16, 1)
        materials.append(floor)
        plane.data.materials.append(floor)
        camera_data = bpy.data.cameras.new('Trafic_texture_camera_TEMP')
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        scene.collection.objects.link(camera)
        objects.append(camera)
        camera.location = (6, -8, 5.3)
        camera.rotation_euler = (Vector((0, 0, 1)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera_data.type = 'ORTHO'
        camera_data.ortho_scale = 5.8
        scene.camera = camera
        light_data = bpy.data.lights.new('Trafic_texture_light_TEMP', 'AREA')
        light = bpy.data.objects.new(light_data.name, light_data)
        scene.collection.objects.link(light)
        objects.append(light)
        light.location = (2, -3, 7)
        light.rotation_euler = (Vector((0, 0, 0)) - light.location).to_track_quat('-Z', 'Y').to_euler()
        light_data.energy, light_data.size = 800, 6
        build = os.path.join(project, 'Assets', 'build')
        variants = [('white', os.path.join(build, 'trafic_preview_white.png')),
                    ('blue', os.path.join(build, 'trafic_preview_blue.png'))]
        if backup:
            variants += [('before_white', os.path.join(build, 'trafic_before_white.png')),
                         ('before_blue', os.path.join(build, 'trafic_before_blue.png'))]
        for name, path in variants:
            image = bpy.data.images.load(path, check_existing=False)
            images.append(image)
            texture.image = image
            glass_texture.image = image
            scene.render.filepath = os.path.join(build, 'trafic_texture_' + name + '.png')
            bpy.ops.render.render(write_still=True)
            print('written', scene.render.filepath, flush=True)
    finally:
        bpy.context.window.scene = original_scene
        for obj in objects:
            data = obj.data
            kind = obj.type
            bpy.data.objects.remove(obj, do_unlink=True)
            if data.users == 0:
                {'MESH': bpy.data.meshes, 'CAMERA': bpy.data.cameras,
                 'LIGHT': bpy.data.lights}[kind].remove(data)
        bpy.data.scenes.remove(scene)
        bpy.data.worlds.remove(world)
        for material in materials:
            bpy.data.materials.remove(material)
        for image in images:
            bpy.data.images.remove(image)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    run(*args)
