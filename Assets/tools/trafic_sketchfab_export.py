r"""Export display-only GLBs on isolated copies of the validated vehicle.

Run in the connected Blender instance:
    exec(open(r'<project>\Assets\tools\trafic_sketchfab_export.py', encoding='utf-8').read())

Static, closed-door presentation; no game scripts, armature, floor or camera in
the GLBs. Embedded PBR textures approximate the game's painted atlas and glass.
The source scene and game resources are not saved or modified.
"""
from pathlib import Path
import hashlib
import json
import bpy
from mathutils import Vector

PROJECT = Path(r'C:\Users\cyber\Zomboid\Workshop\RenaultTrafic1')
OUT = PROJECT / 'Assets' / 'sketchfab'
GLASS = {'TrafI_windshield', 'TrafI_window_fl', 'TrafI_window_fr'}


def fingerprint(objects):
    h = hashlib.sha256()
    for obj in sorted(objects, key=lambda o: o.name):
        h.update(obj.name.encode())
        h.update(repr([list(v.co) for v in obj.data.vertices]).encode())
        h.update(repr([list(p.vertices) for p in obj.data.polygons]).encode())
        h.update(repr([[list(v.uv) for v in uv.data] for uv in obj.data.uv_layers]).encode())
        h.update(repr([list(row) for row in obj.matrix_world]).encode())
    return h.hexdigest()


def material(name, image, alpha=False, roughness=.7):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    mat.surface_render_method = 'DITHERED'
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Metallic'].default_value = 0
    bsdf.inputs['Roughness'].default_value = roughness
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    tex.interpolation = 'Linear'
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'
    links.new(uv.outputs['UV'], tex.inputs['Vector'])
    links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    if alpha:
        links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
    return mat


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    original_scene = bpy.context.window.scene
    original_active = bpy.context.view_layer.objects.active
    original_selection = list(bpy.context.selected_objects)
    sources = [o for c in ('EXPORT_trafic', 'TRF_wheels')
               for o in bpy.data.collections[c].objects if o.type == 'MESH']
    before = fingerprint(sources)
    scene = bpy.data.scenes.new('Trafic_Sketchfab_TEMP')
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    objects, materials, images, meshes, cameras, lights = [], [], [], [], [], []
    reports = []
    world = bpy.data.worlds.new('Trafic_Sketchfab_TEMP')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.32, .37, .44, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
    scene.world = world
    try:
        bpy.context.window.scene = scene
        floor_z = min((o.matrix_world @ Vector(c)).z for o in sources for c in o.bound_box)
        for source in sources:
            mesh = source.data.copy()
            meshes.append(mesh)
            obj = bpy.data.objects.new(source.name + '_Sketchfab', mesh)
            scene.collection.objects.link(obj)
            objects.append(obj)
            obj.matrix_world = source.matrix_world.copy()
            obj.location.z -= floor_z
            # Only display UVs are needed. No modifiers or source material nodes.
            for uv in list(mesh.uv_layers):
                if uv.name != 'UVMap':
                    mesh.uv_layers.remove(uv)
            mesh.uv_layers['UVMap'].active_render = True
            for poly in mesh.polygons:
                poly.material_index = 0
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.context.view_layer.update()
        for colour in ('blue', 'white'):
            body_img = bpy.data.images.load(str(OUT / ('body_' + colour + '.png')), check_existing=False)
            glass_img = bpy.data.images.load(str(OUT / ('glass_' + colour + '.png')), check_existing=False)
            wheel_img = bpy.data.images.load(str(OUT / 'wheel.png'), check_existing=False)
            images.extend((body_img, glass_img, wheel_img))
            body_mat = material('Trafic_' + colour + '_body', body_img)
            glass_mat = material('Trafic_' + colour + '_glass', glass_img, alpha=True, roughness=.25)
            wheel_mat = material('Trafic_' + colour + '_wheel', wheel_img, roughness=.85)
            materials.extend((body_mat, glass_mat, wheel_mat))
            for obj, source in zip(objects, sources):
                obj.data.materials.clear()
                obj.data.materials.append(wheel_mat if source.name.startswith('TRF_wheel_')
                                         else glass_mat if source.name in GLASS else body_mat)
            path = OUT / ('RenaultTraficI_' + colour + '.glb')
            bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB',
                                     use_selection=True, use_active_scene=True,
                                     export_materials='EXPORT', export_image_format='AUTO',
                                     export_animations=False, export_cameras=False,
                                     export_lights=False, export_extras=False,
                                     export_yup=True, export_texcoords=True, export_normals=True)
            reports.append({'file':path.name, 'bytes':path.stat().st_size})
        # Thumbnail is a Blender presentation, not a screenshot of the game.
        camera_data = bpy.data.cameras.new('Trafic_Sketchfab_camera_TEMP')
        cameras.append(camera_data)
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        scene.collection.objects.link(camera)
        objects.append(camera)
        camera.location = (6, -8, 4.8)
        camera.rotation_euler = (Vector((0, 0, 1)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera_data.type = 'ORTHO'
        camera_data.ortho_scale = 5.9
        scene.camera = camera
        for name, location, energy, size in [('key',(3,-4,7),1000,5),
                                             ('fill',(-4,-1,4),650,4),
                                             ('rim',(0,5,6),950,4)]:
            data = bpy.data.lights.new('Trafic_Sketchfab_' + name + '_TEMP', 'AREA')
            lights.append(data)
            light = bpy.data.objects.new(data.name, data)
            scene.collection.objects.link(light)
            objects.append(light)
            light.location = location
            light.rotation_euler = (Vector((0,0,1)) - light.location).to_track_quat('-Z','Y').to_euler()
            data.energy, data.size = energy, size
        scene.render.engine = 'BLENDER_EEVEE'
        scene.render.resolution_x, scene.render.resolution_y = 1200, 900
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.film_transparent = True
        scene.view_settings.view_transform = 'Standard'
        for colour in ('blue', 'white'):
            for obj, source in zip(objects[:len(sources)], sources):
                kind = 'wheel' if source.name.startswith('TRF_wheel_') else 'glass' if source.name in GLASS else 'body'
                obj.data.materials[0] = next(m for m in materials if m.name == 'Trafic_' + colour + '_' + kind)
            scene.render.filepath = str(OUT / ('preview_' + colour + '.png'))
            bpy.ops.render.render(write_still=True)
        report = {'source':str(PROJECT/'Assets/RenaultTraficI.blend'), 'source_scene':original_scene.name,
                  'mesh_instances':len(sources), 'source_geometry_before':before,
                  'source_geometry_after':fingerprint(sources), 'files':reports,
                  'presentation':'static, closed doors, baked colour, PBR approximation',
                  'floor_shift_m':-floor_z, 'blender':bpy.app.version_string}
        (OUT/'export_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        return report
    finally:
        bpy.context.window.scene = original_scene
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.scenes.remove(scene)
        bpy.data.worlds.remove(world)
        for datablocks, entries in [(bpy.data.meshes,meshes),(bpy.data.materials,materials),
                                   (bpy.data.images,images),(bpy.data.cameras,cameras),(bpy.data.lights,lights)]:
            for item in entries:
                if item.users == 0:
                    datablocks.remove(item)
        for obj in original_selection:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = original_active


result = run()
