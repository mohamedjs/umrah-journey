"""Shared headless Blender 5.2 PBR pipeline utilities for umrah-journey.

Provides deterministic scene reset, Three.js <-> Blender coordinate conversions,
PBR Principled material builders, in-memory image packing (sRGB & Non-Color),
bmesh geometry & UV helpers, geometric vertex AO baking, LOD1 decimation,
Draco-6 + WebP GLB export, and JSON budget reporting.
"""
import json
import math
import os
from pathlib import Path
import sys
import tempfile

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
import numpy as np

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
MODELS_CHAR = ROOT / 'public' / 'models' / 'characters'
MODELS_ENV = ROOT / 'public' / 'models' / 'env'
PREVIEWS = ROOT / 'blender' / 'previews'
BLENDER_DIR = ROOT / 'blender'


# ------------------------------------------------------------------ paths & scene
def ensure_dirs():
    """Ensure character/env model output dirs and preview dir exist."""
    for d in (MODELS_CHAR, MODELS_ENV, PREVIEWS):
        d.mkdir(parents=True, exist_ok=True)


def reset_scene():
    """Start from an empty Blender 5.2 scene with metric units and 24 fps."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    sc.render.fps = 24


# ------------------------------------------------------------------ coordinates & math
def three_to_bl(tx, ty, tz):
    """Convert Three.js Y-up coordinates (tx, ty, tz) to Blender Z-up Vector((tx, -tz, ty)).

    Matches glTF Y-up export (export_yup=True), where Blender (bx, by, bz) maps to
    Three.js (bx, bz, -by). Rotations around Three.js +Y map identically to Blender +Z.
    """
    return Vector((float(tx), float(-tz), float(ty)))


def bl_to_three(bx, by, bz):
    """Convert Blender Z-up coordinates (bx, by, bz) to Three.js Y-up Vector((bx, bz, -by)).

    Inverse of three_to_bl(), matching glTF export_yup=True axis conversion.
    """
    return Vector((float(bx), float(bz), float(-by)))


def hex_rgb(h):
    """Convert '#RRGGBB' (or 'RRGGBB') hex string to (r, g, b) sRGB floats in [0, 1]."""
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def srgb_to_linear(c):
    """Convert an sRGB hex string or 3-sequence (r, g, b) in [0, 1] to linear RGB."""
    if isinstance(c, str):
        c = hex_rgb(c)
    out = []
    for v in c[:3]:
        v = max(0.0, min(1.0, float(v)))
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def smoothstep(e0, e1, x):
    """Smooth Hermite interpolation in [0, 1]."""
    if abs(e1 - e0) < 1e-8:
        return 1.0 if x >= e1 else 0.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


# ------------------------------------------------------------------ collections & objects
def make_collection(name, parent=None):
    """Create or clear a Blender collection linked under parent (or scene root)."""
    col = bpy.data.collections.get(name)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def new_obj(name, mesh, col):
    """Create a mesh object linked to col, replacing any existing object of the same name."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def ensure_uv_layer(obj):
    """Ensure mesh object has a primary UV layer named 'UVMap'."""
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    else:
        me.uv_layers[0].name = 'UVMap'
    return me.uv_layers[0]


def bm_to_obj(bm, name, col, mat=None, smooth=True, ensure_uv=True):
    """Convert bmesh into a Blender mesh object with consistent normals and UVs."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if ensure_uv and not bm.loops.layers.uv:
        uv_layer = bm.loops.layers.uv.new('UVMap')
        for f in bm.faces:
            for loop in f.loops:
                loop[uv_layer].uv = (0.0, 0.0)

    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if ensure_uv and me.uv_layers:
        me.uv_layers[0].name = 'UVMap'
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    else:
        for p in me.polygons:
            p.use_smooth = False
    obj = new_obj(name, me, col)
    if mat is not None:
        me.materials.append(mat)
    return obj


def join_objects(objs, name, col=None):
    """Join a list of mesh objects into one object named `name`."""
    objs = [o for o in objs if o is not None]
    if not objs:
        raise ValueError('join_objects requires at least one object')
    for obj in objs:
        ensure_uv_layer(obj)
    if len(objs) == 1:
        res = objs[0]
        res.name = name
        res.data.name = name
        if col and res.name not in col.objects:
            col.objects.link(res)
        return res

    mesh_objs = [o for o in objs if o.type == 'MESH']
    ref_attr = next(
        (o.data.color_attributes.get('Color') for o in mesh_objs if o.data.color_attributes.get('Color') is not None),
        None,
    )
    has_any_col = ref_attr is not None or any(len(o.data.color_attributes) > 0 for o in mesh_objs)
    if has_any_col:
        domain = ref_attr.domain if ref_attr is not None else 'POINT'
        data_type = ref_attr.data_type if ref_attr is not None else 'BYTE_COLOR'
        for obj in mesh_objs:
            me = obj.data
            ca = me.color_attributes.get('Color')
            if ca is None:
                ca = me.color_attributes.new(name='Color', type=data_type, domain=domain)
                n = len(ca.data)
                if n > 0:
                    ca.data.foreach_set('color', np.ones(n * 4, dtype=np.float32))
            idx = me.color_attributes.find('Color')
            if idx >= 0:
                me.color_attributes.active_color_index = idx
                me.color_attributes.render_color_index = idx

    for o in list(bpy.context.selected_objects):
        o.select_set(False)
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    with bpy.context.temp_override(
        active_object=objs[0],
        object=objs[0],
        selected_objects=objs,
        selected_editable_objects=objs,
    ):
        bpy.ops.object.join()
    res = objs[0]
    res.name = name
    res.data.name = name
    if res.type == 'MESH':
        idx = res.data.color_attributes.find('Color')
        if idx >= 0:
            res.data.color_attributes.active_color_index = idx
            res.data.color_attributes.render_color_index = idx
    if col and res.name not in col.objects:
        col.objects.link(res)
    return res


# ------------------------------------------------------------------ UVs & geometry builders
def uv_box_project(obj, scale=1.0):
    """Apply clean headless triplanar/box-projected UVs based on face normals."""
    me = obj.data
    ensure_uv_layer(obj)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    uv = bm.loops.layers.uv.active
    s = float(scale)
    for f in bm.faces:
        nx, ny, nz = abs(f.normal.x), abs(f.normal.y), abs(f.normal.z)
        if nz >= nx and nz >= ny:
            for loop in f.loops:
                p = loop.vert.co
                loop[uv].uv = (p.x * s, p.y * s)
        elif nx >= ny:
            for loop in f.loops:
                p = loop.vert.co
                loop[uv].uv = (p.y * s, p.z * s)
        else:
            for loop in f.loops:
                p = loop.vert.co
                loop[uv].uv = (p.x * s, p.z * s)
    bm.to_mesh(me)
    bm.free()


def uv_cylindrical(obj, center=(0.0, 0.0), scale_u=1.0, scale_v=1.0):
    """Apply clean cylindrical UVs around the Z axis without seam wrapping artifacts."""
    me = obj.data
    ensure_uv_layer(obj)
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    cx, cy = float(center[0]), float(center[1])
    for f in bm.faces:
        angs = [math.atan2(loop.vert.co.y - cy, loop.vert.co.x - cx) for loop in f.loops]
        if max(angs) - min(angs) > math.pi:
            angs = [a + math.tau if a < 0.0 else a for a in angs]
        for loop, a in zip(f.loops, angs):
            p = loop.vert.co
            loop[uv].uv = ((a / math.tau) * scale_u, p.z * scale_v)
    bm.to_mesh(me)
    bm.free()


def loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=False):
    """Connect a sequence of equal-length vertex rings into a smooth quad skin."""
    if len(rings) < 2:
        return
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        count = n if closed_u else n - 1
        for k in range(count):
            kn = (k + 1) % n
            bm.faces.new((r0[k], r0[kn], r1[kn], r1[k]))
    if cap_start and closed_u:
        c = sum((v.co for v in rings[0]), Vector()) / n
        cv = bm.verts.new(c)
        for k in range(n):
            bm.faces.new((rings[0][(k + 1) % n], rings[0][k], cv))
    if cap_end and closed_u:
        c = sum((v.co for v in rings[-1]), Vector()) / n
        cv = bm.verts.new(c)
        for k in range(n):
            bm.faces.new((rings[-1][k], rings[-1][(k + 1) % n], cv))


def add_tube(bm, pts, radius, segs=10, flat=1.0, closed_caps=True, ref_up=None):
    """Add a swept tube along 3D polyline `pts` using parallel-transport framing."""
    pts = [Vector(p) for p in pts]
    n_pts = len(pts)
    if n_pts < 2:
        return []
    up = Vector(ref_up).normalized() if ref_up is not None else Vector((0.0, 0.0, 1.0))
    tangents = []
    for i in range(n_pts):
        t = pts[min(i + 1, n_pts - 1)] - pts[max(i - 1, 0)]
        if t.length < 1e-6:
            t = Vector((0.0, 0.0, 1.0))
        tangents.append(t.normalized())

    t0 = tangents[0]
    ax = t0.cross(up)
    if ax.length < 1e-4:
        ax = t0.orthogonal()
    ax.normalize()
    bx = t0.cross(ax).normalized()

    rings = []
    for i, p in enumerate(pts):
        ti = tangents[i]
        if i > 0:
            q = tangents[i - 1].rotation_difference(ti)
            ax = q @ ax
            ax = (ax - ti * ax.dot(ti)).normalized()
            bx = ti.cross(ax).normalized()
        u = i / max(1, n_pts - 1)
        r = radius(u) if callable(radius) else radius
        if isinstance(r, (tuple, list)):
            rx, ry = float(r[0]), float(r[1])
        else:
            rx, ry = float(r), float(r) * float(flat)
        ring = []
        for k in range(segs):
            ang = k / segs * math.tau
            ring.append(bm.verts.new(p + ax * (math.cos(ang) * rx) + bx * (math.sin(ang) * ry)))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=closed_caps, cap_end=closed_caps)
    return rings


def add_box(bm, center, size, rot_z=0.0):
    """Add an oriented box of full dimensions `size=(sx, sy, sz)` centered at `center`."""
    if isinstance(size, (int, float)):
        sx = sy = sz = float(size)
    else:
        sx, sy, sz = float(size[0]), float(size[1]), float(size[2])
    mat = (
        Matrix.Translation(Vector(center))
        @ Matrix.Rotation(float(rot_z), 4, 'Z')
        @ Matrix.Diagonal((sx, sy, sz, 1.0))
    )
    return bmesh.ops.create_cube(bm, size=1.0, matrix=mat)


def add_cylinder(
    bm,
    center=(0.0, 0.0, 0.0),
    radius=0.5,
    height=1.0,
    segs=16,
    radius_top=None,
    cap_ends=True,
    rot_z=0.0,
):
    """Add a vertical cylinder/frustum centered at `center` with optional taper and Z rotation."""
    r1 = float(radius)
    r2 = r1 if radius_top is None else float(radius_top)
    mat = Matrix.Translation(Vector(center)) @ Matrix.Rotation(float(rot_z), 4, 'Z')
    return bmesh.ops.create_cone(
        bm,
        cap_ends=bool(cap_ends),
        cap_tris=False,
        segments=int(segs),
        radius1=r1,
        radius2=r2,
        depth=float(height),
        matrix=mat,
    )


# ------------------------------------------------------------------ images & PBR materials
def pack_image(name, rgb_float_hw3, alpha_hw=None, colorspace='sRGB'):
    """Pack an in-memory NumPy float image (HxWx3 in [0, 1], row 0 = bottom) as a Blender PNG.

    Supports colorspace='sRGB' for color/albedo maps and colorspace='Non-Color' for
    normal, roughness, and data maps.
    """
    arr = np.asarray(rgb_float_hw3, dtype=np.float32)
    if arr.ndim == 2:
        arr = np.repeat(arr[..., None], 3, axis=-1)
    h, w = arr.shape[:2]

    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)

    has_alpha = alpha_hw is not None
    img = bpy.data.images.new(name, w, h, alpha=has_alpha)
    img.colorspace_settings.name = colorspace

    if has_alpha:
        a = np.clip(np.asarray(alpha_hw, dtype=np.float32), 0.0, 1.0)[..., None]
    else:
        a = np.ones((h, w, 1), dtype=np.float32)
    rgba = np.concatenate([np.clip(arr, 0.0, 1.0), a], axis=-1)
    img.pixels.foreach_set(rgba.ravel())

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tf:
        tmp_path = tf.name
    try:
        img.filepath_raw = tmp_path
        img.file_format = 'PNG'
        img.save()
        img.filepath = tmp_path
        img.source = 'FILE'
        img.reload()
        img.colorspace_settings.name = colorspace
        img.pack()
        img.colorspace_settings.name = colorspace
        img.filepath = f'//{name}.png'
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return img


def make_pbr_material(
    name,
    color='#cccccc',
    roughness=0.7,
    metallic=0.0,
    image=None,
    normal_image=None,
    normal_strength=0.6,
    roughness_image=None,
    emissive=None,
    emissive_strength=0.0,
    alpha=1.0,
    double_sided=False,
    use_vcol=False,
    uv_scale=(1.0, 1.0),
):
    """Create a realistic Principled BSDF material ready for glTF 2.0 PBR export."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    mat.use_backface_culling = not double_sided

    nt = mat.node_tree
    nt.nodes.clear()

    def node(bl_type, x, y, nname=None):
        n = nt.nodes.new(bl_type)
        n.location = (x, y)
        if nname:
            n.name = nname
        return n

    out = node('ShaderNodeOutputMaterial', 620, 0, 'Output')
    pbr = node('ShaderNodeBsdfPrincipled', 260, 0, 'Principled')
    pbr.inputs['Roughness'].default_value = float(roughness)
    pbr.inputs['Metallic'].default_value = float(metallic)
    nt.links.new(pbr.outputs['BSDF'], out.inputs['Surface'])

    # Optional UV mapping shared across textures
    uv_vec = None
    sx, sy = (float(uv_scale), float(uv_scale)) if isinstance(uv_scale, (int, float)) else (float(uv_scale[0]), float(uv_scale[1]))
    if (abs(sx - 1.0) > 1e-6 or abs(sy - 1.0) > 1e-6) and any(
        im is not None for im in (image, normal_image, roughness_image)
    ):
        tc = node('ShaderNodeTexCoord', -720, 0, 'TexCoord')
        mp = node('ShaderNodeMapping', -520, 0, 'Mapping')
        mp.inputs['Scale'].default_value = (sx, sy, 1.0)
        nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
        uv_vec = mp.outputs['Vector']

    # Base color source
    base_lin = srgb_to_linear(color)
    if image is not None:
        tx = node('ShaderNodeTexImage', -240, 220, 'BaseColorTex')
        tx.image = image
        tx.interpolation = 'Linear'
        if uv_vec is not None:
            nt.links.new(uv_vec, tx.inputs['Vector'])
        base_sock = tx.outputs['Color']
    else:
        base_sock = None
        pbr.inputs['Base Color'].default_value = (*base_lin, 1.0)

    # Optional Vertex Color ('Color') multiplied into Base Color
    if use_vcol:
        vc = node('ShaderNodeVertexColor', -240, 440, 'VertexAO')
        vc.layer_name = 'Color'
        mul = node('ShaderNodeMix', 20, 260, 'BaseColorAO')
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        if base_sock is not None:
            nt.links.new(base_sock, mul.inputs[6])
        else:
            mul.inputs[6].default_value = (*base_lin, 1.0)
        nt.links.new(vc.outputs['Color'], mul.inputs[7])
        nt.links.new(mul.outputs[2], pbr.inputs['Base Color'])
    elif base_sock is not None:
        nt.links.new(base_sock, pbr.inputs['Base Color'])

    # Optional Roughness map
    if roughness_image is not None:
        if roughness_image.colorspace_settings.name != 'Non-Color':
            roughness_image.colorspace_settings.name = 'Non-Color'
        rtx = node('ShaderNodeTexImage', -240, -40, 'RoughnessTex')
        rtx.image = roughness_image
        if uv_vec is not None:
            nt.links.new(uv_vec, rtx.inputs['Vector'])
        nt.links.new(rtx.outputs['Color'], pbr.inputs['Roughness'])

    # Optional Normal map
    if normal_image is not None:
        if normal_image.colorspace_settings.name != 'Non-Color':
            normal_image.colorspace_settings.name = 'Non-Color'
        ntx = node('ShaderNodeTexImage', -240, -300, 'NormalTex')
        ntx.image = normal_image
        if uv_vec is not None:
            nt.links.new(uv_vec, ntx.inputs['Vector'])
        nm = node('ShaderNodeNormalMap', 20, -260, 'NormalMap')
        nm.inputs['Strength'].default_value = float(normal_strength)
        nt.links.new(ntx.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], pbr.inputs['Normal'])

    # Optional Emission (Blender 4/5 safe input lookup)
    if emissive is not None and float(emissive_strength) > 0.0:
        em_lin = srgb_to_linear(emissive)
        if 'Emission Color' in pbr.inputs:
            pbr.inputs['Emission Color'].default_value = (*em_lin, 1.0)
        elif 'Emission' in pbr.inputs:
            pbr.inputs['Emission'].default_value = (*em_lin, 1.0)
        if 'Emission Strength' in pbr.inputs:
            pbr.inputs['Emission Strength'].default_value = float(emissive_strength)

    # Optional Alpha transparency (Blender 5.2 safe)
    if float(alpha) < 0.999:
        if 'Alpha' in pbr.inputs:
            pbr.inputs['Alpha'].default_value = float(alpha)
        if hasattr(mat, 'surface_render_method'):
            mat.surface_render_method = 'BLENDED'
        if hasattr(mat, 'blend_method'):
            try:
                mat.blend_method = 'BLEND'
            except Exception:
                pass

    mat.diffuse_color = (*base_lin, float(alpha))
    return mat


# ------------------------------------------------------------------ AO, LOD, stats
def bake_vertex_ao(obj, strength=0.30, min_val=0.58):
    """Bake fast geometric concavity + ground-contact AO into 'Color' byte color attribute."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.normal_update()

    z_vals = [v.co.z for v in bm.verts]
    z_min, z_max = (min(z_vals), max(z_vals)) if z_vals else (0.0, 1.0)
    z_span = max(z_max - z_min, 1e-4)

    ao_per_vert = []
    for v in bm.verts:
        concav = 0.0
        n_edges = len(v.link_edges)
        if n_edges:
            for e in v.link_edges:
                other = e.other_vert(v)
                d = other.co - v.co
                ln = d.length
                if ln > 1e-5:
                    concav += max(0.0, d.dot(v.normal) / ln)
            concav /= n_edges
        ground_occ = max(0.0, 1.0 - (v.co.z - z_min) / min(z_span, 1.2)) * 0.35
        occ = max(float(min_val), 1.0 - float(strength) * (concav * 1.4 + ground_occ))
        ao_per_vert.append(occ)
    bm.free()

    col_attr = me.color_attributes.get('Color')
    if col_attr is None:
        col_attr = me.color_attributes.new(name='Color', type='BYTE_COLOR', domain='POINT')
        for i, occ in enumerate(ao_per_vert):
            col_attr.data[i].color = (occ, occ, occ, 1.0)
    elif col_attr.domain == 'POINT':
        for i, occ in enumerate(ao_per_vert):
            c = col_attr.data[i].color
            col_attr.data[i].color = (c[0] * occ, c[1] * occ, c[2] * occ, c[3])
    else:
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                occ = ao_per_vert[vi]
                c = col_attr.data[li].color
                col_attr.data[li].color = (c[0] * occ, c[1] * occ, c[2] * occ, c[3])

    idx = me.color_attributes.find('Color')
    if idx >= 0:
        me.color_attributes.active_color_index = idx
        me.color_attributes.render_color_index = idx


def make_lod1(obj, ratio=0.42, name=None):
    """Create a decimated LOD1 sibling copy preserving UVs and materials."""
    copy_obj = obj.copy()
    copy_obj.data = obj.data.copy()
    copy_obj.name = name or f'{obj.name}_LOD1'
    for col in obj.users_collection:
        col.objects.link(copy_obj)

    mod = copy_obj.modifiers.new('lod1_decimate', 'DECIMATE')
    mod.ratio = float(ratio)
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.update()

    dg = bpy.context.evaluated_depsgraph_get()
    ev = copy_obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    me.validate(clean_customdata=False)
    copy_obj.modifiers.clear()
    old = copy_obj.data
    copy_obj.data = me
    me.name = copy_obj.name
    bpy.data.meshes.remove(old)
    return copy_obj


def tri_count(obj):
    """Return total triangle count for a Blender mesh object."""
    if obj is None or obj.type != 'MESH':
        return 0
    return sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)


def bone_count(rig):
    """Return count of deform bones in an Armature object."""
    if rig is None or rig.type != 'ARMATURE':
        return 0
    return sum(1 for b in rig.data.bones if b.use_deform)


# ------------------------------------------------------------------ export & report
def export_glb(
    objs,
    path,
    animations=False,
    draco_level=6,
    image_format='WEBP',
    image_quality=82,
    vertex_colors=False,
):
    """Export selected objects cleanly to a Y-up Draco-compressed GLB and return size in bytes."""
    if isinstance(objs, bpy.types.Object):
        objs = [objs]
    objs = [o for o in objs if o is not None]
    if not objs:
        raise ValueError('export_glb requires at least one object')

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.view_layer.update()

    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.hide_viewport = False
        if o.type == 'MESH' and o.data.color_attributes:
            idx = o.data.color_attributes.find('Color')
            if idx < 0:
                idx = 0
            o.data.color_attributes.active_color_index = idx
            o.data.color_attributes.render_color_index = idx
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

    desired = {
        'filepath': str(path),
        'export_format': 'GLB',
        'use_selection': True,
        'export_yup': True,
        'export_apply': not animations,
        'export_texcoords': True,
        'export_normals': True,
        'export_materials': 'EXPORT',
        'export_image_format': image_format,
        'export_image_quality': int(image_quality),
        'export_image_webp_fallback': False,
        'export_draco_mesh_compression_enable': True,
        'export_draco_mesh_compression_level': int(draco_level),
        'export_draco_position_quantization': 14,
        'export_draco_normal_quantization': 10,
        'export_draco_texcoord_quantization': 12,
        'export_skins': bool(animations),
        'export_animations': bool(animations),
        'export_optimize_animation_size': True,
        'export_vertex_color': 'ACTIVE' if vertex_colors else 'MATERIAL',
        'export_all_vertex_colors': False,
        'export_attributes': False,
        'export_morph': False,
    }
    if animations:
        desired['export_animation_mode'] = 'NLA_TRACKS'

    valid_props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    kwargs = {k: v for k, v in desired.items() if k in valid_props}
    bpy.ops.export_scene.gltf(**kwargs)

    for o in objs:
        o.select_set(False)
    return os.path.getsize(path)


def save_report(name, entries):
    """Write a JSON budget/build report to `blender/<name>`."""
    BLENDER_DIR.mkdir(parents=True, exist_ok=True)
    out = BLENDER_DIR / name
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(entries, fh, indent=2)
    return out


# ------------------------------------------------------------------ smoke self-test
if __name__ == '__main__':
    import struct

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from blender.lib import preview, textures

    ensure_dirs()
    reset_scene()
    col = make_collection('SmokeTest')

    # Verify coordinate round-trip
    v_bl = three_to_bl(1.5, 2.0, -3.5)
    v_th = bl_to_three(v_bl.x, v_bl.y, v_bl.z)
    assert (v_th - Vector((1.5, 2.0, -3.5))).length < 1e-6, 'Coordinate round-trip mismatch'

    # Generate procedural Kiswa & White Marble textures
    kiswa_alb, kiswa_nrm = textures.tex_kiswa(size=512)
    marble_alb, marble_nrm = textures.tex_marble_white(size=256)

    mat_kiswa = make_pbr_material(
        'mat_smoke_kiswa',
        roughness=0.58,
        metallic=0.05,
        image=kiswa_alb,
        normal_image=kiswa_nrm,
        normal_strength=0.65,
        use_vcol=True,
    )
    mat_marble = make_pbr_material(
        'mat_smoke_marble',
        roughness=0.22,
        metallic=0.0,
        image=marble_alb,
        normal_image=marble_nrm,
        normal_strength=0.35,
        uv_scale=(2.0, 2.0),
    )

    # Build textured cube + marble plinth + LOD1
    bm = bmesh.new()
    add_box(bm, (0.0, 0.0, 0.75), (1.2, 1.2, 1.5))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
    cube = bm_to_obj(bm, 'SmokeCube', col, mat=mat_kiswa, smooth=False)
    uv_box_project(cube, scale=1.0 / 1.5)
    bake_vertex_ao(cube, strength=0.25, min_val=0.65)
    cube_lod1 = make_lod1(cube, ratio=0.45)

    bm_floor = bmesh.new()
    add_box(bm_floor, (0.0, 0.0, -0.05), (4.0, 4.0, 0.10))
    floor = bm_to_obj(bm_floor, 'SmokeFloor', col, mat=mat_marble, smooth=False)
    uv_box_project(floor, scale=0.5)

    assert tri_count(cube) > 0 and tri_count(cube_lod1) > 0, 'Empty geometry'

    # Export GLB & verify glTF 2.0 header + size
    tmp_glb = Path('/tmp/smoke_test.glb')
    size_bytes = export_glb([cube, cube_lod1, floor], tmp_glb, vertex_colors=True)
    assert size_bytes > 1000, f'Unexpectedly small GLB: {size_bytes}'
    with open(tmp_glb, 'rb') as fh:
        header = fh.read(12)
        magic, version, length = struct.unpack('<4sII', header)
        chunk_len, chunk_type = struct.unpack('<II', fh.read(8))
        gltf_json = fh.read(chunk_len).decode('utf-8')
    assert magic == b'glTF' and version == 2, f'Invalid GLB header: {magic} v{version}'
    assert length == size_bytes, f'GLB length mismatch: {length} != {size_bytes}'
    assert 'KHR_draco_mesh_compression' in gltf_json, 'Missing Draco extension'
    assert 'image/webp' in gltf_json, 'Expected packed WebP textures'

    # Render headless preview PNG
    cube_lod1.hide_render = True
    smoke_png = PREVIEWS / '_smoke.png'
    preview.render_shot(
        eye=(2.8, -3.2, 2.2),
        target=(0.0, 0.0, 0.65),
        out_path=smoke_png,
        res=(640, 400),
    )
    assert smoke_png.exists() and smoke_png.stat().st_size > 1000, 'Preview render failed'

    # Cleanup temp GLB
    if tmp_glb.exists():
        tmp_glb.unlink()

    print(
        f'SMOKE_OK (tris={tri_count(cube)}->{tri_count(cube_lod1)}, '
        f'glb={size_bytes / 1024:.1f}KB, preview={smoke_png.stat().st_size / 1024:.1f}KB)'
    )
