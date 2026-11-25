"""Headless studio preview renderer for inspecting umrah-journey characters & environments.

Renders warm sunlit PBR previews via Blender 5.2 EEVEE (with dynamic engine fallback)
into `blender/previews/*.png` without external PIL dependencies.
"""
import math
import os
from pathlib import Path
import sys
import tempfile

import bpy
from mathutils import Vector
import numpy as np

sys.dont_write_bytecode = True


def _pick_render_engine():
    """Select the best available Blender render engine dynamically."""
    avail = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    for pref in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT', 'CYCLES', 'BLENDER_WORKBENCH'):
        if pref in avail:
            return pref
    return avail[0] if avail else 'BLENDER_EEVEE'


def _ensure_preview_world(sc, world_color=(0.55, 0.68, 0.85)):
    """Create or update a clean sky world for realistic PBR illumination."""
    world = bpy.data.worlds.get('_PreviewWorld')
    if world is None:
        world = bpy.data.worlds.new('_PreviewWorld')
    sc.world = world
    if world.node_tree is None:
        world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (
        float(world_color[0]),
        float(world_color[1]),
        float(world_color[2]),
        1.0,
    )
    bg.inputs['Strength'].default_value = 0.75
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    return world


def _ensure_preview_lights(sc):
    """Ensure warm sun key light + cool sky fill light + subtle rim light exist."""
    col = bpy.data.collections.get('_PreviewRig')
    if col is None:
        col = bpy.data.collections.new('_PreviewRig')
        sc.collection.children.link(col)

    def _upsert_light(name, ltype, energy, color, loc, target):
        obj = bpy.data.objects.get(name)
        if obj is None:
            ldata = bpy.data.lights.new(name, type=ltype)
            obj = bpy.data.objects.new(name, ldata)
            col.objects.link(obj)
        else:
            obj.data.type = ltype
        obj.data.energy = energy
        obj.data.color = color
        if ltype == 'SUN' and hasattr(obj.data, 'angle'):
            obj.data.angle = math.radians(1.6)
        obj.location = Vector(loc)
        direction = Vector(target) - Vector(loc)
        obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        return obj

    # Warm Arabian daylight key sun
    _upsert_light(
        '_PrevKeySun',
        'SUN',
        energy=3.8,
        color=(1.0, 0.94, 0.84),
        loc=(6.0, -8.0, 10.0),
        target=(0.0, 0.0, 0.0),
    )
    # Soft cool sky fill sun
    _upsert_light(
        '_PrevFillSun',
        'SUN',
        energy=1.1,
        color=(0.76, 0.87, 1.0),
        loc=(-7.0, -4.0, 6.0),
        target=(0.0, 0.0, 0.0),
    )
    # Subtle warm rim sun from behind to define silhouettes
    _upsert_light(
        '_PrevRimSun',
        'SUN',
        energy=0.85,
        color=(1.0, 0.91, 0.76),
        loc=(-4.0, 9.0, 6.0),
        target=(0.0, 0.0, 0.0),
    )
    return col


def _ensure_preview_camera(sc, eye, target, lens=38):
    """Create or reposition the preview camera aimed from `eye` at `target`."""
    col = bpy.data.collections.get('_PreviewRig')
    if col is None:
        col = bpy.data.collections.new('_PreviewRig')
        sc.collection.children.link(col)

    cam = bpy.data.objects.get('_PreviewCam')
    if cam is None:
        cdata = bpy.data.cameras.new('_PreviewCam')
        cam = bpy.data.objects.new('_PreviewCam', cdata)
        col.objects.link(cam)
    cam.data.lens = float(lens)
    cam.data.clip_start = 0.05
    cam.data.clip_end = 500.0
    cam.location = Vector(eye)
    direction = Vector(target) - Vector(eye)
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    return cam


def _configure_render(sc, res):
    sc.render.engine = _pick_render_engine()
    sc.render.resolution_x = int(res[0])
    sc.render.resolution_y = int(res[1])
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    if hasattr(sc, 'eevee'):
        if hasattr(sc.eevee, 'taa_render_samples'):
            sc.eevee.taa_render_samples = 24
        if hasattr(sc.eevee, 'use_shadows'):
            sc.eevee.use_shadows = True
    if sc.render.engine == 'CYCLES':
        sc.cycles.samples = 24
        sc.cycles.use_denoising = False
    try:
        sc.view_settings.view_transform = 'AgX'
    except Exception:
        try:
            sc.view_settings.view_transform = 'Filmic'
        except Exception:
            pass
    sc.view_settings.exposure = 0.0


def render_shot(eye, target, out_path, res=(960, 600), lens=38, world_color=(0.55, 0.68, 0.85)):
    """Render a single studio-lit preview PNG from `eye` looking at `target`."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene

    _ensure_preview_world(sc, world_color=world_color)
    _ensure_preview_lights(sc)
    _ensure_preview_camera(sc, eye=eye, target=target, lens=lens)
    _configure_render(sc, res=res)

    sc.render.filepath = str(out_path)
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    return out_path


def _world_bounds(objs):
    """Return (min_vec, max_vec) world-space bounding box enclosing `objs`."""
    pts = []
    for o in objs:
        if o is None or o.type not in ('MESH', 'ARMATURE'):
            continue
        for corner in o.bound_box:
            pts.append(o.matrix_world @ Vector(corner))
    if not pts:
        return Vector((-0.5, -0.5, 0.0)), Vector((0.5, 0.5, 1.8))
    mins = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    maxs = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mins, maxs


def render_turntable_grid(objs, out_path, res=(1200, 700), views=4, lens=45, world_color=(0.55, 0.68, 0.85)):
    """Render multiple turntable angles (front, 3/4, side, back) and composite side-by-side."""
    if isinstance(objs, bpy.types.Object):
        objs = [objs]
    objs = [o for o in objs if o is not None]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    views = max(1, int(views))
    total_w, total_h = int(res[0]), int(res[1])
    tile_w = max(64, total_w // views)
    tile_h = total_h

    mins, maxs = _world_bounds(objs)
    center = (mins + maxs) * 0.5
    span = maxs - mins
    radius = max(span.length * 0.5, 0.5)
    # Camera distance tuned so subject fills ~78% of tile height
    fov_scale = 36.0 / max(float(lens), 10.0)
    dist = max(radius * 2.55 * (1.0 / max(fov_scale, 0.5)), 1.6)
    elev = center.z + span.z * 0.14

    if views == 4:
        # Front (-Y), Front-Right 3/4, Side (+X), Back (+Y)
        angles_deg = [-90.0, -45.0, 0.0, 90.0]
    else:
        angles_deg = [-90.0 + (360.0 * i / views) for i in range(views)]

    tiles = []
    tmp_files = []
    try:
        for idx, deg in enumerate(angles_deg):
            rad = math.radians(deg)
            eye = (
                center.x + math.cos(rad) * dist,
                center.y + math.sin(rad) * dist,
                elev,
            )
            with tempfile.NamedTemporaryFile(suffix=f'_v{idx}.png', delete=False) as tf:
                tmp_png = tf.name
            tmp_files.append(tmp_png)
            render_shot(
                eye=eye,
                target=(center.x, center.y, center.z),
                out_path=tmp_png,
                res=(tile_w, tile_h),
                lens=lens,
                world_color=world_color,
            )
            img = bpy.data.images.load(tmp_png, check_existing=False)
            w, h = img.size[0], img.size[1]
            arr = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(arr)
            tiles.append(arr.reshape((h, w, 4)))
            bpy.data.images.remove(img)

        sheet = np.concatenate(tiles, axis=1)
        sh, sw = sheet.shape[:2]
        out_img = bpy.data.images.new('_TurntableSheet', sw, sh, alpha=True)
        out_img.pixels.foreach_set(sheet.ravel())
        out_img.filepath_raw = str(out_path)
        out_img.file_format = 'PNG'
        out_img.save()
        bpy.data.images.remove(out_img)
    finally:
        for f in tmp_files:
            if os.path.exists(f):
                os.remove(f)
    return out_path
