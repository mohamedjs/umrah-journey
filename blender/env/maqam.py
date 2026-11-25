"""Maqam Ibrahim realistic PBR landmark for umrah-journey.

Generates `public/models/env/maqam.glb` centered at origin `(0, 0, 0)` (placed at
`maqamPos` in Three.js) and renders a studio preview to `blender/previews/env_maqam.png`.

Architectural breakdown:
- Tiered octagonal honed cream-marble base (r = 1.02 m -> 0.86 m, y in [0, 0.54])
  with molded step bevels & inlaid brushed-brass collar ring
- Delicate gilded hexagonal metal cage: 6 slender turned brass/gold columns with
  pointed Islamic mini-arches, lower balustrade ring & upper hexagonal cornice (y in [0.54, 2.15])
- Translucent warm crystal glass enclosure cylinder (r = 0.66 m, alpha = 0.35, roughness = 0.08)
- Inner sculpted marble-and-gold pedestal cradling the sacred stone silhouette softly illuminated
- Ribbed gleaming gold dome (y in [2.15, 2.95]) crowned by multi-sphere finial & crescent (y = 3.45 m)
"""
import math
import os
from pathlib import Path
import struct
import sys
import tempfile

import bmesh
import bpy
from mathutils import Matrix, Vector
import numpy as np

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blender.lib import common, preview, textures  # noqa: E402


def _make_materials():
    marble_alb, marble_nrm = textures.tex_marble_cream(size=512, name='tex_maqam_marble_cream', tiles=3)
    gold_alb, gold_nrm = textures.tex_gold_relief(size=256, name='tex_maqam_gold_relief')

    return {
        'marble': common.make_pbr_material(
            'mat_maqam_marble',
            color='#ede3d0',
            roughness=0.26,
            metallic=0.0,
            image=marble_alb,
            normal_image=marble_nrm,
            normal_strength=0.35,
            use_vcol=True,
        ),
        'gold_dome': common.make_pbr_material(
            'mat_maqam_gold_dome',
            color='#e7be56',
            roughness=0.22,
            metallic=0.90,
            use_vcol=False,
        ),
        'gold_cage': common.make_pbr_material(
            'mat_maqam_gold_cage',
            color='#d9ad42',
            roughness=0.26,
            metallic=0.88,
            image=gold_alb,
            normal_image=gold_nrm,
            normal_strength=0.45,
            use_vcol=False,
        ),
        'brass_dark': common.make_pbr_material(
            'mat_maqam_brass_dark',
            color='#8f6c28',
            roughness=0.34,
            metallic=0.84,
            use_vcol=False,
        ),
        'crystal_glass': common.make_pbr_material(
            'mat_maqam_crystal_glass',
            color='#f5f0e6',
            roughness=0.08,
            metallic=0.04,
            alpha=0.35,
            double_sided=True,
            use_vcol=False,
        ),
        'sacred_stone': common.make_pbr_material(
            'mat_maqam_stone',
            color='#8b775b',
            roughness=0.62,
            metallic=0.02,
            use_vcol=True,
        ),
        'inner_glow': common.make_pbr_material(
            'mat_maqam_inner_glow',
            color='#ffefc8',
            roughness=0.20,
            metallic=0.0,
            emissive='#ffd688',
            emissive_strength=1.6,
            use_vcol=False,
        ),
    }


def _build_octagonal_base(col, mats):
    """Tiered octagonal honed cream-marble plinth (r = 1.02 -> 0.86 m, z in [0, 0.54])."""
    bm = bmesh.new()
    segs = 8
    rot = math.pi / 8.0  # align flat faces cleanly with axes

    # Multi-step molded octagonal profile: (radius, z)
    profile = [
        (1.02, 0.00),
        (1.02, 0.13),
        (0.98, 0.16),
        (0.94, 0.16),
        (0.91, 0.41),
        (0.94, 0.44),
        (0.94, 0.50),
        (0.86, 0.54),
    ]
    rings = []
    for rad, z in profile:
        ring = []
        for k in range(segs):
            a = k / segs * math.tau + rot
            ring.append(bm.verts.new((math.cos(a) * rad, math.sin(a) * rad, z)))
        rings.append(ring)

    common.loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)
    base_obj = common.bm_to_obj(bm, 'maqam_base', col, mat=mats['marble'], smooth=False)
    common.uv_box_project(base_obj, scale=0.65)
    return base_obj


def _build_gilded_cage(col, mats):
    """Hexagonal gilded brass cage: 6 turned columns, pointed mini-arches & upper cornice."""
    bm_cage = bmesh.new()
    bm_dark = bmesh.new()
    n_cols = 6
    cage_r = 0.74
    z_base = 0.54
    z_top = 2.15

    # Inlaid brass collar ring sitting atop the octagonal marble base
    common.add_cylinder(bm_dark, (0.0, 0.0, z_base + 0.025), 0.79, 0.05, segs=12, radius_top=0.77)
    common.add_cylinder(bm_cage, (0.0, 0.0, z_base + 0.06), 0.76, 0.03, segs=12, radius_top=0.75)

    # Lower filigree balustrade rail (z = 0.84) & vertical balusters between columns
    rail_z = 0.84
    col_pts = []
    for k in range(n_cols):
        a = k / n_cols * math.tau
        cx, cy = math.cos(a) * cage_r, math.sin(a) * cage_r
        col_pts.append((cx, cy, a))

        # Slender turned gilded column (plinth -> shaft -> mid-ring -> flared capital)
        common.add_cylinder(bm_dark, (cx, cy, z_base + 0.09), 0.062, 0.14, segs=8, radius_top=0.044)
        common.add_cylinder(bm_cage, (cx, cy, 1.24), 0.036, 1.18, segs=8, radius_top=0.034)
        # Decorative turned mid-band ring
        common.add_cylinder(bm_dark, (cx, cy, 1.20), 0.048, 0.06, segs=8, radius_top=0.048)
        # Flared acanthus/muqarnas gilded capital
        common.add_cylinder(bm_cage, (cx, cy, 1.88), 0.036, 0.14, segs=8, radius_top=0.068)
        common.add_cylinder(bm_dark, (cx, cy, 1.97), 0.072, 0.05, segs=8, radius_top=0.072)

    # Connect adjacent columns with lower railing bar, miniature balusters, and pointed Islamic mini-arches
    for k in range(n_cols):
        x0, y0, _ = col_pts[k]
        x1, y1, _ = col_pts[(k + 1) % n_cols]
        p0 = Vector((x0, y0, 0.0))
        p1 = Vector((x1, y1, 0.0))
        mid = (p0 + p1) * 0.5
        span = (p1 - p0).length
        ang_seg = math.atan2(y1 - y0, x1 - x0)

        # Lower decorative balustrade rail + 3 slender vertical spindles per bay
        common.add_box(bm_cage, (mid.x, mid.y, rail_z), (span - 0.06, 0.032, 0.032), rot_z=ang_seg)
        for frac in (0.25, 0.50, 0.75):
            bx = x0 + (x1 - x0) * frac
            by = y0 + (y1 - y0) * frac
            common.add_cylinder(bm_dark, (bx, by, 0.70), 0.012, 0.28, segs=6)

        # Pointed Islamic mini-arch spanning from column capital to column capital (z in [1.84, 2.10])
        n_arc = 10
        arch_pts = []
        for i in range(n_arc + 1):
            u = i / n_arc
            s = abs(2.0 * u - 1.0)
            # Two-center pointed arch profile
            t_h = math.sqrt(max(0.0, 1.0 - ((s + 0.35) / 1.35) ** 2)) / 0.965828
            ax = x0 + (x1 - x0) * u
            ay = y0 + (y1 - y0) * u
            az = 1.84 + 0.25 * t_h
            arch_pts.append(Vector((ax, ay, az)))
        common.add_tube(bm_cage, arch_pts, radius=0.024, segs=6, closed_caps=True)

        # Upper frieze beam above the pointed arch
        common.add_box(bm_dark, (mid.x, mid.y, z_top - 0.03), (span + 0.04, 0.065, 0.08), rot_z=ang_seg)

    # Molded upper hexagonal/circular entablature crown ring supporting the dome
    common.add_cylinder(bm_cage, (0.0, 0.0, z_top + 0.01), 0.79, 0.07, segs=12, radius_top=0.77)

    cage_obj = common.bm_to_obj(bm_cage, 'maqam_cage_gold', col, mat=mats['gold_cage'], smooth=True)
    common.uv_box_project(cage_obj, scale=1.4)
    dark_obj = common.bm_to_obj(bm_dark, 'maqam_cage_brass', col, mat=mats['brass_dark'], smooth=True)
    common.uv_box_project(dark_obj, scale=1.4)
    return [cage_obj, dark_obj]


def _build_crystal_and_inner_pedestal(col, mats):
    """Translucent warm crystal glass cylinder + inner marble/gold pedestal & sacred stone."""
    # 1. Crystal glass cylinder enclosure (r = 0.66 m, z in [0.56, 2.13])
    bm_gl = bmesh.new()
    common.add_cylinder(
        bm_gl,
        center=(0.0, 0.0, 1.345),
        radius=0.66,
        radius_top=0.66,
        height=1.57,
        segs=24,
        cap_ends=False,
    )
    glass_obj = common.bm_to_obj(bm_gl, 'maqam_glass', col, mat=mats['crystal_glass'], smooth=True)

    # 2. Inner sculpted marble pedestal
    bm_ped = bmesh.new()
    ped_prof = [
        (0.45, 0.54),
        (0.45, 0.64),
        (0.38, 0.68),
        (0.35, 1.14),
        (0.40, 1.18),
        (0.40, 1.24),
        (0.32, 1.26),
    ]
    rings = []
    for rad, z in ped_prof:
        ring = []
        for k in range(12):
            a = k / 12 * math.tau
            ring.append(bm_ped.verts.new((math.cos(a) * rad, math.sin(a) * rad, z)))
        rings.append(ring)
    common.loft_rings(bm_ped, rings, closed_u=True, cap_start=True, cap_end=True)
    ped_obj = common.bm_to_obj(bm_ped, 'maqam_inner_pedestal', col, mat=mats['marble'], smooth=True)
    common.uv_box_project(ped_obj, scale=1.0)

    # 3. Gilded brass cradle frame holding the stone atop the pedestal
    bm_cradle = bmesh.new()
    common.add_cylinder(bm_cradle, (0.0, 0.0, 1.27), 0.34, 0.07, segs=12, radius_top=0.36)
    common.add_cylinder(bm_cradle, (0.0, 0.0, 0.90), 0.37, 0.04, segs=12, radius_top=0.37)
    cradle_obj = common.bm_to_obj(bm_cradle, 'maqam_inner_cradle', col, mat=mats['gold_dome'], smooth=True)

    # 4. Soft warm sanctuary glow collar inside the cradle rim
    bm_glow = bmesh.new()
    common.add_cylinder(bm_glow, (0.0, 0.0, 1.305), 0.30, 0.025, segs=12, radius_top=0.28)
    glow_obj = common.bm_to_obj(bm_glow, 'maqam_inner_glow', col, mat=mats['inner_glow'], smooth=True)

    # 5. Sacred stone silhouette (respectful sculpted Hijazi sandstone block with gentle rounded top)
    bm_st = bmesh.new()
    m_st = Matrix.Translation((0.0, 0.0, 1.43)) @ Matrix.Diagonal((0.22, 0.20, 0.155, 1.0))
    bmesh.ops.create_uvsphere(bm_st, u_segments=12, v_segments=8, radius=1.0, matrix=m_st)
    # Subtle natural flat top indentation contour
    for v in bm_st.verts:
        if v.co.z > 1.52:
            d = math.hypot(v.co.x, v.co.y)
            v.co.z -= 0.028 * max(0.0, 1.0 - (d / 0.16) ** 2)
    stone_obj = common.bm_to_obj(bm_st, 'maqam_sacred_stone', col, mat=mats['sacred_stone'], smooth=True)
    common.uv_box_project(stone_obj, scale=2.0)

    return [glass_obj, ped_obj, cradle_obj, glow_obj, stone_obj]


def _build_ribbed_dome_and_finial(col, mats):
    """Ribbed gleaming gold dome (z in [2.15, 2.95]) + sculpted multi-sphere finial & crescent (z = 3.45 m)."""
    bm = bmesh.new()
    u_segs = 24  # 12 crisp raised gold ribs alternating around 24 segments
    v_rings = 10
    z0 = 2.18
    z_crown = 2.95

    # Drum molding collar
    common.add_cylinder(bm, (0.0, 0.0, z0 + 0.03), 0.74, 0.08, segs=24, radius_top=0.73)

    # Ribbed pointed Islamic dome loft
    rings = []
    for iv in range(v_rings):
        t = iv / (v_rings - 1)  # 0 at drum -> 1 near crown
        # Graceful pointed dome profile
        z = z0 + 0.06 + (z_crown - (z0 + 0.06)) * math.sin(t * math.pi * 0.5)
        r_base = 0.72 * (math.cos(t * math.pi * 0.5) ** 0.82)
        r_base = max(r_base, 0.06)
        rib_amp = 0.020 * math.sin(t * math.pi)
        ring = []
        for k in range(u_segs):
            a = k / u_segs * math.tau
            # 12 raised ribs
            rib = rib_amp if (k % 2 == 0) else 0.0
            r = r_base + rib
            ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, z)))
        rings.append(ring)

    common.loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=True)

    # Sculpted multi-sphere gilded Alem finial rising cleanly to z = 3.45 m
    common.add_cylinder(bm, (0.0, 0.0, 3.12), 0.022, 0.34, segs=8, radius_top=0.012)
    for sz, sr in ((2.99, 0.072), (3.11, 0.052), (3.21, 0.036)):
        bmesh.ops.create_uvsphere(
            bm,
            u_segments=10,
            v_segments=6,
            radius=sr,
            matrix=Matrix.Translation((0.0, 0.0, sz)),
        )

    # Graceful open golden crescent crowning the apex (top reaches z = 3.45 m)
    cres_pts = []
    n_cr = 12
    cz = 3.355
    cr = 0.095
    for i in range(n_cr + 1):
        # Open upward crescent arc from -130 deg to +130 deg around bottom
        ang = math.radians(-135.0 + 270.0 * (i / n_cr))
        # Crescent in XZ plane facing East/West
        cx = math.sin(ang) * cr
        cz_pt = cz - math.cos(ang) * cr
        cres_pts.append(Vector((cx, 0.0, cz_pt)))

    def _cres_rad(u):
        # Thickest at bottom belly (u = 0.5), tapering gracefully to sharp tips
        return 0.006 + 0.019 * math.sin(u * math.pi)

    common.add_tube(bm, cres_pts, radius=_cres_rad, segs=6, closed_caps=True, ref_up=Vector((0.0, 1.0, 0.0)))

    dome_obj = common.bm_to_obj(bm, 'maqam_dome_finial', col, mat=mats['gold_dome'], smooth=True)
    common.uv_box_project(dome_obj, scale=1.0)
    return dome_obj


def build_maqam(col):
    """Build complete Maqam Ibrahim mesh centered at origin `(0, 0, 0)`."""
    mats = _make_materials()

    parts = []
    parts.append(_build_octagonal_base(col, mats))
    parts.extend(_build_gilded_cage(col, mats))
    parts.extend(_build_crystal_and_inner_pedestal(col, mats))
    parts.append(_build_ribbed_dome_and_finial(col, mats))

    ao_mats = {'mat_maqam_marble', 'mat_maqam_stone'}
    for obj in parts:
        uses_ao = any(m and m.name in ao_mats for m in obj.data.materials)
        if uses_ao:
            common.bake_vertex_ao(obj, strength=0.22, min_val=0.72)
        else:
            me = obj.data
            if me.color_attributes.get('Color') is None:
                ca = me.color_attributes.new(name='Color', type='BYTE_COLOR', domain='POINT')
                for i in range(len(ca.data)):
                    ca.data[i].color = (1.0, 1.0, 1.0, 1.0)

    maqam_obj = common.join_objects(parts, 'maqam', col=col)
    return maqam_obj


def _render_maqam_preview(maqam_obj, out_path):
    """Render 2-angle studio preview of Maqam Ibrahim showing base, cage, glass, stone & gold dome."""
    tmp_col = common.make_collection('_MaqamPreviewGround')
    bm_g = bmesh.new()
    common.add_cylinder(bm_g, center=(0.0, 0.0, -0.04), radius=8.0, height=0.08, segs=32)
    m_alb = bpy.data.images.get('tex_maqam_marble_cream')
    g_mat = common.make_pbr_material('_mat_prev_floor', color='#f0efe9', roughness=0.28, image=m_alb)
    g_obj = common.bm_to_obj(bm_g, '_PrevFloor', tmp_col, mat=g_mat, smooth=False)
    common.uv_box_project(g_obj, scale=0.35)

    shots = [
        # Full-height 3/4 architectural hero
        (common.three_to_bl(3.8, 2.2, 4.0), common.three_to_bl(0.0, 1.65, 0.0), 42),
        # Closer mid-level view highlighting glass enclosure, inner pedestal, arches & ribbed dome
        (common.three_to_bl(-2.7, 2.4, 2.5), common.three_to_bl(0.0, 1.75, 0.0), 44),
    ]

    tiles = []
    tmp_files = []
    try:
        for idx, (eye, tgt, lens) in enumerate(shots):
            with tempfile.NamedTemporaryFile(suffix=f'_maqam_{idx}.png', delete=False) as tf:
                tmp_png = tf.name
            tmp_files.append(tmp_png)
            preview.render_shot(
                eye=eye,
                target=tgt,
                out_path=tmp_png,
                res=(600, 640),
                lens=lens,
                world_color=(0.56, 0.70, 0.88),
            )
            img = bpy.data.images.load(tmp_png, check_existing=False)
            w, h = img.size[0], img.size[1]
            arr = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(arr)
            tiles.append(arr.reshape((h, w, 4)))
            bpy.data.images.remove(img)

        sheet = np.concatenate(tiles, axis=1)
        sh, sw = sheet.shape[:2]
        out_img = bpy.data.images.new('_MaqamSheet', sw, sh, alpha=True)
        out_img.pixels.foreach_set(sheet.ravel())
        out_img.filepath_raw = str(out_path)
        out_img.file_format = 'PNG'
        out_img.save()
        bpy.data.images.remove(out_img)
    finally:
        for f in tmp_files:
            if os.path.exists(f):
                os.remove(f)
        bpy.data.objects.remove(g_obj, do_unlink=True)
        bpy.data.collections.remove(tmp_col)


def _verify_glb(path, size_bytes, max_kb):
    with open(path, 'rb') as fh:
        magic, version, length = struct.unpack('<4sII', fh.read(12))
        chunk_len, _ = struct.unpack('<II', fh.read(8))
        gltf_json = fh.read(chunk_len).decode('utf-8')
    assert magic == b'glTF' and version == 2 and length == size_bytes, 'Invalid GLB header'
    assert 'KHR_draco_mesh_compression' in gltf_json, 'Missing Draco extension'
    assert 'image/webp' in gltf_json, 'Missing packed WebP textures'
    kb = size_bytes / 1024.0
    assert kb <= max_kb, f'GLB size {kb:.1f} KB exceeds budget {max_kb} KB'


def export_maqam(render_preview=True):
    """Build, verify, export `public/models/env/maqam.glb`, and render `env_maqam.png`."""
    common.ensure_dirs()
    common.reset_scene()

    col = common.make_collection('MaqamIbrahim')
    maqam_obj = build_maqam(col)

    tris = common.tri_count(maqam_obj)
    assert tris <= 4500, f'maqam tris {tris} > 4500'

    # Verify height & footprint match spec (r ~ 1.02 m, height ~ 3.45 m)
    zs = [v.co.z for v in maqam_obj.data.vertices]
    rs = [math.hypot(v.co.x, v.co.y) for v in maqam_obj.data.vertices]
    assert min(zs) >= -0.01 and 3.35 <= max(zs) <= 3.55, f'Unexpected Maqam height: {min(zs):.2f}..{max(zs):.2f}'
    assert 0.95 <= max(rs) <= 1.12, f'Unexpected Maqam radius: {max(rs):.2f}'

    out_glb = common.MODELS_ENV / 'maqam.glb'
    size_bytes = common.export_glb([maqam_obj], out_glb, vertex_colors=False)
    _verify_glb(out_glb, size_bytes, max_kb=180)

    out_png = common.PREVIEWS / 'env_maqam.png'
    if render_preview:
        _render_maqam_preview(maqam_obj, out_png)

    info = {
        'name': 'maqam',
        'glb': str(out_glb.relative_to(ROOT)),
        'tris': tris,
        'size_kb': round(size_bytes / 1024.0, 1),
        'height_m': round(max(zs), 2),
    }
    print(f"MAQAM_OK tris={tris} size={info['size_kb']}KB height={info['height_m']}m")
    return info


if __name__ == '__main__':
    export_maqam(render_preview=True)
