"""Chapter 1 — Warm Egyptian Home Bedroom environment for umrah-journey.

Exports `public/models/env/home.glb` containing:
- `home_static_LOD0` + `home_static_LOD1` (architecture, rug, bed, open suitcase,
  bookcase, houseplant, dresser, framed mirror, ajar front door)
- 4 separate top-level named interactive objects (NOT merged, NO LOD suffix):
  `item_passport`, `item_ihram`, `item_sandals`, `item_perfume`
Also renders verification preview to `blender/previews/env_home.png`.
"""
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blender.lib import common, preview, textures
from blender.lib.common import (
    MODELS_ENV,
    PREVIEWS,
    bake_vertex_ao,
    bm_to_obj,
    ensure_dirs,
    export_glb,
    join_objects,
    make_collection,
    make_lod1,
    make_pbr_material,
    reset_scene,
    three_to_bl,
    tri_count,
    uv_box_project,
)


# ------------------------------------------------------------------ Three.js-space bmesh helpers
def _mat_three(center_t, rot_y=0.0, rot_x=0.0, rot_z=0.0):
    """Build a Blender 4x4 transform matrix from Three.js world position and Euler angles."""
    c_bl = three_to_bl(*center_t)
    # Three.js (rx, ry, rz) -> Blender (rx, -rz, ry)
    rot = (
        Matrix.Rotation(float(rot_y), 4, 'Z')
        @ Matrix.Rotation(float(rot_x), 4, 'X')
        @ Matrix.Rotation(float(-rot_z), 4, 'Y')
    )
    return Matrix.Translation(c_bl) @ rot


def _add_box_t(bm, center_t, size_t, rot_y=0.0, rot_x=0.0, bevel=0.0, bevel_segs=1):
    """Add a box specified in Three.js center (tx,ty,tz) and size (sx,sy,sz), optional bevel."""
    sx, sy, sz = float(size_t[0]), float(size_t[1]), float(size_t[2])
    m = _mat_three(center_t, rot_y=rot_y, rot_x=rot_x) @ Matrix.Diagonal((sx, sz, sy, 1.0))
    prev = set(bm.verts)
    ret = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    verts = ret['verts']
    if bevel > 0.0:
        vset = set(verts)
        edges = [e for e in bm.edges if e.verts[0] in vset and e.verts[1] in vset]
        bmesh.ops.bevel(
            bm,
            geom=edges,
            offset=float(bevel),
            offset_type='OFFSET',
            segments=int(bevel_segs),
            profile=0.5,
            affect='EDGES',
            clamp_overlap=True,
        )
        return [v for v in bm.verts if v not in prev]
    return verts


def _add_cyl_t(bm, center_t, r_bot, height, segs=16, r_top=None, rot_y=0.0, rot_x=0.0, cap=True):
    """Add a vertical (Three.js Y-axis) cylinder/frustum at Three.js center."""
    m = _mat_three(center_t, rot_y=rot_y, rot_x=rot_x)
    return bmesh.ops.create_cone(
        bm,
        cap_ends=cap,
        cap_tris=False,
        segments=int(segs),
        radius1=float(r_bot),
        radius2=float(r_bot if r_top is None else r_top),
        depth=float(height),
        matrix=m,
    )['verts']


def _set_white_vcol(obj):
    """Assign neutral white vertex color so un-occluded glass/emissive surfaces stay clean."""
    me = obj.data
    col_attr = me.color_attributes.get('Color')
    if col_attr is None:
        col_attr = me.color_attributes.new(name='Color', type='BYTE_COLOR', domain='POINT')
    for i in range(len(col_attr.data)):
        col_attr.data[i].color = (1.0, 1.0, 1.0, 1.0)
    idx = me.color_attributes.find('Color')
    if idx >= 0:
        me.color_attributes.active_color_index = idx
        me.color_attributes.render_color_index = idx


def _make_part(bm, name, col, mat, smooth=False, uv_scale=0.5, ao=True, ao_strength=0.28, ao_min=0.62):
    """Finalize a bmesh part with UVs and optional vertex AO."""
    obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
    uv_box_project(obj, scale=uv_scale)
    if ao:
        bake_vertex_ao(obj, strength=ao_strength, min_val=ao_min)
    else:
        _set_white_vcol(obj)
    return obj


# ------------------------------------------------------------------ Materials
def _create_materials():
    oak_alb, oak_nrm = textures.tex_wood_oak(size=512, name='home_oak_floor', planks=6, tint='#a87648')
    oak_furn_alb, oak_furn_nrm = textures.tex_wood_oak(size=256, name='home_oak_furn', planks=1, tint='#a67547')
    oak_dark_alb, oak_dark_nrm = textures.tex_wood_oak(size=256, name='home_oak_dark', planks=1, tint='#7a4f2d')
    plaster_back = textures.tex_plaster_wall(size=256, name='home_plaster_back', tint='#f0dfc2')
    plaster_left = textures.tex_plaster_wall(size=256, name='home_plaster_left', tint='#e6cfa9')
    rug_alb = textures.tex_persian_rug(size=512, name='home_persian_rug')
    ihram_alb, ihram_nrm = textures.tex_cotton_ihram(size=256, name='home_ihram_cotton')
    linen_alb = textures.tex_fabric_weave(size=256, name='home_linen_cream', color='#f4eee2', contrast=0.04)
    duvet_alb = textures.tex_fabric_weave(size=256, name='home_duvet_ochre', color='#c88f5a', contrast=0.05)

    return {
        'floor_oak': make_pbr_material(
            'mat_home_floor_oak',
            roughness=0.44,
            image=oak_alb,
            normal_image=oak_nrm,
            normal_strength=0.42,
            use_vcol=True,
            uv_scale=(0.85, 0.85),
        ),
        'wood_oak': make_pbr_material(
            'mat_home_wood_oak',
            roughness=0.42,
            image=oak_furn_alb,
            normal_image=oak_furn_nrm,
            normal_strength=0.30,
            use_vcol=True,
            uv_scale=(0.75, 0.75),
        ),
        'wood_dark': make_pbr_material(
            'mat_home_wood_dark',
            roughness=0.40,
            image=oak_dark_alb,
            normal_image=oak_dark_nrm,
            normal_strength=0.32,
            use_vcol=True,
            uv_scale=(0.75, 0.75),
        ),
        'wall_back': make_pbr_material(
            'mat_home_wall_back',
            roughness=0.86,
            image=plaster_back,
            use_vcol=True,
            uv_scale=(0.35, 0.35),
        ),
        'wall_left': make_pbr_material(
            'mat_home_wall_left',
            roughness=0.86,
            image=plaster_left,
            use_vcol=True,
            uv_scale=(0.35, 0.35),
        ),
        'trim_cream': make_pbr_material(
            'mat_home_trim_cream',
            color='#f3ead8',
            roughness=0.58,
            use_vcol=True,
        ),
        'window_glow': make_pbr_material(
            'mat_home_window_glow',
            color='#fff8e5',
            roughness=0.15,
            emissive='#ffe6ad',
            emissive_strength=1.55,
            use_vcol=False,
        ),
        'window_glass': make_pbr_material(
            'mat_home_window_glass',
            color='#eef7ff',
            roughness=0.06,
            metallic=0.05,
            alpha=0.22,
            use_vcol=False,
        ),
        'curtain': make_pbr_material(
            'mat_home_curtain',
            roughness=0.88,
            image=linen_alb,
            double_sided=True,
            use_vcol=True,
            uv_scale=(2.0, 2.0),
        ),
        'rug': make_pbr_material(
            'mat_home_rug',
            roughness=0.92,
            image=rug_alb,
            use_vcol=True,
        ),
        'rug_fringe': make_pbr_material(
            'mat_home_rug_fringe',
            color='#e4d5b7',
            roughness=0.95,
            use_vcol=True,
        ),
        'mattress': make_pbr_material(
            'mat_home_mattress',
            roughness=0.86,
            image=linen_alb,
            use_vcol=True,
            uv_scale=(1.5, 1.5),
        ),
        'pillow': make_pbr_material(
            'mat_home_pillow',
            color='#fbf8f2',
            roughness=0.84,
            use_vcol=True,
        ),
        'duvet': make_pbr_material(
            'mat_home_duvet',
            roughness=0.88,
            image=duvet_alb,
            use_vcol=True,
            uv_scale=(1.6, 1.6),
        ),
        'suitcase_shell': make_pbr_material(
            'mat_home_suitcase_teal',
            color='#265d78',
            roughness=0.34,
            metallic=0.08,
            use_vcol=True,
        ),
        'suitcase_trim': make_pbr_material(
            'mat_home_suitcase_trim',
            color='#1c2630',
            roughness=0.52,
            metallic=0.2,
            use_vcol=True,
        ),
        'suitcase_lining': make_pbr_material(
            'mat_home_suitcase_lining',
            color='#d5d8dc',
            roughness=0.88,
            use_vcol=True,
        ),
        'brass': make_pbr_material(
            'mat_home_brass',
            color='#cfa246',
            roughness=0.26,
            metallic=0.90,
            use_vcol=False,
        ),
        'aluminum': make_pbr_material(
            'mat_home_aluminum',
            color='#c2c8ce',
            roughness=0.28,
            metallic=0.88,
            use_vcol=False,
        ),
        'mirror_glass': make_pbr_material(
            'mat_home_mirror',
            color='#d2e3ea',
            roughness=0.06,
            metallic=0.92,
            use_vcol=False,
        ),
        'terracotta': make_pbr_material(
            'mat_home_terracotta',
            color='#b85c38',
            roughness=0.78,
            use_vcol=True,
        ),
        'soil': make_pbr_material(
            'mat_home_soil',
            color='#3a291e',
            roughness=0.96,
            use_vcol=True,
        ),
        'leaf_green': make_pbr_material(
            'mat_home_leaf',
            color='#3f763d',
            roughness=0.48,
            double_sided=True,
            use_vcol=True,
        ),
        'book_navy': make_pbr_material('mat_home_book_navy', color='#243b5a', roughness=0.62, use_vcol=True),
        'book_burgundy': make_pbr_material('mat_home_book_burg', color='#72242c', roughness=0.62, use_vcol=True),
        'book_emerald': make_pbr_material('mat_home_book_em', color='#225842', roughness=0.62, use_vcol=True),
        'book_pages': make_pbr_material('mat_home_book_pg', color='#efe8d6', roughness=0.85, use_vcol=True),
        # Takeable item materials
        'passport_leather': make_pbr_material(
            'mat_item_passport',
            color='#6e1d28',
            roughness=0.48,
            metallic=0.04,
            use_vcol=False,
        ),
        'visa_paper': make_pbr_material(
            'mat_item_visa',
            color='#f7f5ef',
            roughness=0.82,
            use_vcol=False,
        ),
        'visa_accent': make_pbr_material(
            'mat_item_visa_accent',
            color='#1f6d69',
            roughness=0.72,
            use_vcol=False,
        ),
        'ihram_cotton': make_pbr_material(
            'mat_item_ihram',
            roughness=0.92,
            image=ihram_alb,
            normal_image=ihram_nrm,
            normal_strength=0.45,
            use_vcol=False,
            uv_scale=(2.0, 2.0),
        ),
        'sandal_leather': make_pbr_material(
            'mat_item_sandal_leather',
            color='#6a4326',
            roughness=0.52,
            use_vcol=False,
        ),
        'sandal_sole': make_pbr_material(
            'mat_item_sandal_sole',
            color='#3a2618',
            roughness=0.74,
            use_vcol=False,
        ),
        'sandal_footbed': make_pbr_material(
            'mat_item_sandal_bed',
            color='#9e7147',
            roughness=0.78,
            use_vcol=False,
        ),
        'perfume_crystal': make_pbr_material(
            'mat_item_perfume_glass',
            color='#fff3dc',
            roughness=0.07,
            metallic=0.05,
            alpha=0.52,
            use_vcol=False,
        ),
        'perfume_amber': make_pbr_material(
            'mat_item_perfume_amber',
            color='#b8451e',
            roughness=0.14,
            emissive='#9c3410',
            emissive_strength=0.35,
            use_vcol=False,
        ),
    }


# ------------------------------------------------------------------ Architecture builders
def _build_room_shell(col, mats):
    parts = []

    # 1. Oak hardwood floor: x in [-8, 8], z in [-7, 7], y in [-0.2, 0.0]
    bm = bmesh.new()
    _add_box_t(bm, (0.0, -0.10, 0.0), (16.0, 0.20, 14.0), bevel=0.015, bevel_segs=1)
    parts.append(_make_part(bm, '_floor', col, mats['floor_oak'], smooth=False, uv_scale=0.35, ao_strength=0.18, ao_min=0.76))

    # 2. Back wall (z = -7.05, h = 7.0) with real recessed cutout for window (x in [-0.1, 3.1], y in [2.5, 5.1])
    bm = bmesh.new()
    # Left section: x in [-8.15, -0.10], y in [0, 7.0]
    _add_box_t(bm, (-4.125, 3.5, -7.05), (8.05, 7.0, 0.22))
    # Right section: x in [3.10, 8.0], y in [0, 7.0]
    _add_box_t(bm, (5.55, 3.5, -7.05), (4.90, 7.0, 0.22))
    # Below window: x in [-0.10, 3.10], y in [0, 2.50]
    _add_box_t(bm, (1.50, 1.25, -7.05), (3.20, 2.50, 0.22))
    # Above window: x in [-0.10, 3.10], y in [5.10, 7.0]
    _add_box_t(bm, (1.50, 6.05, -7.05), (3.20, 1.90, 0.22))
    # Recessed window alcove cheek walls back to z = -7.26
    _add_box_t(bm, (-0.12, 3.80, -7.18), (0.08, 2.66, 0.26))
    _add_box_t(bm, (3.12, 3.80, -7.18), (0.08, 2.66, 0.26))
    _add_box_t(bm, (1.50, 5.12, -7.18), (3.32, 0.08, 0.26))
    _add_box_t(bm, (1.50, 2.48, -7.18), (3.32, 0.08, 0.26))
    parts.append(_make_part(bm, '_wall_back', col, mats['wall_back'], smooth=False, uv_scale=0.25, ao_strength=0.22, ao_min=0.72))

    # 3. Left wall (x = -8.05, z in [-7.15, 7.0], h = 7.0)
    bm = bmesh.new()
    _add_box_t(bm, (-8.05, 3.5, -0.075), (0.22, 7.0, 14.15))
    parts.append(_make_part(bm, '_wall_left', col, mats['wall_left'], smooth=False, uv_scale=0.25, ao_strength=0.22, ao_min=0.72))

    # 4. Oak baseboards (h = 0.16 m) + stepped upper cap bead along back & left walls
    bm = bmesh.new()
    _add_box_t(bm, (0.0, 0.08, -6.92), (16.0, 0.16, 0.04), bevel=0.008)
    _add_box_t(bm, (0.0, 0.175, -6.925), (16.0, 0.03, 0.05), bevel=0.006)
    _add_box_t(bm, (-7.92, 0.08, 0.0), (0.04, 0.16, 14.0), bevel=0.008)
    _add_box_t(bm, (-7.925, 0.175, 0.0), (0.05, 0.03, 14.0), bevel=0.006)
    parts.append(_make_part(bm, '_baseboards', col, mats['wood_dark'], smooth=False, uv_scale=0.7, ao_strength=0.25))

    # 5. Stepped crown molding at y = 6.85 m along back & left walls + subtle dado molding at y = 1.05
    bm = bmesh.new()
    # Back crown (2-tier cornice)
    _add_box_t(bm, (0.0, 6.84, -6.90), (16.0, 0.14, 0.10), bevel=0.012)
    _add_box_t(bm, (0.0, 6.94, -6.86), (16.0, 0.09, 0.18), bevel=0.012)
    # Left crown
    _add_box_t(bm, (-7.90, 6.84, 0.0), (0.10, 0.14, 14.0), bevel=0.012)
    _add_box_t(bm, (-7.86, 6.94, 0.0), (0.18, 0.09, 14.0), bevel=0.012)
    parts.append(_make_part(bm, '_crown', col, mats['trim_cream'], smooth=False, uv_scale=0.5, ao_strength=0.22))

    # 6. Window frame, mullions, windowsill, glowing morning backdrop, glass, rod & draped curtains
    # Window center: (1.5, 3.8, -6.92), size 3.2 x 2.6 m
    bm = bmesh.new()
    # Outer oak casing
    _add_box_t(bm, (1.50, 5.14, -6.89), (3.44, 0.14, 0.18), bevel=0.014)
    _add_box_t(bm, (-0.14, 3.80, -6.89), (0.14, 2.74, 0.18), bevel=0.014)
    _add_box_t(bm, (3.14, 3.80, -6.89), (0.14, 2.74, 0.18), bevel=0.014)
    # Projecting oak windowsill with bullnose front
    _add_box_t(bm, (1.50, 2.46, -6.82), (3.58, 0.10, 0.34), bevel=0.02, bevel_segs=2)
    _add_box_t(bm, (1.50, 2.36, -6.90), (3.40, 0.10, 0.12), bevel=0.012)
    # Center vertical mullion & horizontal transom + fine muntin bars
    _add_box_t(bm, (1.50, 3.80, -6.98), (0.11, 2.60, 0.14), bevel=0.01)
    _add_box_t(bm, (1.50, 3.80, -6.98), (3.20, 0.11, 0.14), bevel=0.01)
    for mx in (0.70, 2.30):
        _add_box_t(bm, (mx, 3.80, -7.02), (0.045, 2.58, 0.06), bevel=0.005)
    for my in (3.15, 4.45):
        _add_box_t(bm, (1.50, my, -7.02), (3.18, 0.045, 0.06), bevel=0.005)
    parts.append(_make_part(bm, '_win_frame', col, mats['wood_oak'], smooth=False, uv_scale=0.8, ao_strength=0.25))

    # Morning sunlit backdrop pane recessed inside alcove
    bm = bmesh.new()
    _add_box_t(bm, (1.50, 3.80, -7.22), (3.18, 2.58, 0.04))
    parts.append(_make_part(bm, '_win_glow', col, mats['window_glow'], smooth=False, uv_scale=0.4, ao=False))

    # Subtle glass pane in front of mullions
    bm = bmesh.new()
    _add_box_t(bm, (1.50, 3.80, -7.05), (3.16, 2.56, 0.02))
    parts.append(_make_part(bm, '_win_glass', col, mats['window_glass'], smooth=False, uv_scale=0.4, ao=False))

    # Curtain rod + brackets + finials (brass)
    bm = bmesh.new()
    m_rod = Matrix.Translation(three_to_bl(1.50, 5.42, -6.58)) @ Matrix.Rotation(math.pi / 2.0, 4, 'Y')
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.028, radius2=0.028, depth=4.24, matrix=m_rod)
    for sx in (-1.0, 1.0):
        bmesh.ops.create_uvsphere(
            bm, u_segments=10, v_segments=6, radius=0.055,
            matrix=Matrix.Translation(three_to_bl(1.50 + sx * 2.15, 5.42, -6.58)),
        )
        _add_box_t(bm, (1.50 + sx * 1.84, 5.42, -6.76), (0.05, 0.06, 0.38), bevel=0.006)
    parts.append(_make_part(bm, '_curtain_rod', col, mats['brass'], smooth=True, uv_scale=1.0, ao=False))

    # Draped pleated linen side curtains (left & right, cleanly clear of projecting windowsill)
    bm = bmesh.new()
    for side in (-1.0, 1.0):
        x_outer = 1.50 + side * 2.02
        x_inner = 1.50 + side * 1.08
        nx, ny = 14, 10
        grid = []
        for iy in range(ny):
            v = iy / (ny - 1)  # 0 top -> 1 bottom
            ty = 5.38 - v * 4.55  # hangs down to y=0.83
            tie = math.exp(-((v - 0.62) / 0.16) ** 2)
            row = []
            for ix in range(nx):
                u = ix / (nx - 1)
                u_pinched = u * (1.0 - 0.34 * tie)
                tx = x_outer + (x_inner - x_outer) * u_pinched
                pleat_amp = 0.075 * (0.65 + 0.35 * v) * (1.0 - 0.25 * tie)
                tz = -6.54 + math.sin(u * 4.5 * math.tau) * pleat_amp + 0.04 * tie
                row.append(bm.verts.new(three_to_bl(tx, ty, tz)))
            grid.append(row)
        for iy in range(ny - 1):
            for ix in range(nx - 1):
                if side < 0:
                    bm.faces.new((grid[iy][ix], grid[iy][ix + 1], grid[iy + 1][ix + 1], grid[iy + 1][ix]))
                else:
                    bm.faces.new((grid[iy][ix], grid[iy + 1][ix], grid[iy + 1][ix + 1], grid[iy][ix + 1]))
    parts.append(_make_part(bm, '_curtains', col, mats['curtain'], smooth=True, uv_scale=0.8, ao_strength=0.22, ao_min=0.74))

    # Subtle framed decorative geometric wall art on left wall (x = -7.91, y = 3.55, z = -2.4)
    bm_art = bmesh.new()
    _add_box_t(bm_art, (-7.91, 4.32, -2.40), (0.06, 0.09, 1.66), bevel=0.01)
    _add_box_t(bm_art, (-7.91, 2.78, -2.40), (0.06, 0.09, 1.66), bevel=0.01)
    _add_box_t(bm_art, (-7.91, 3.55, -3.19), (0.06, 1.60, 0.09), bevel=0.01)
    _add_box_t(bm_art, (-7.91, 3.55, -1.61), (0.06, 1.60, 0.09), bevel=0.01)
    parts.append(_make_part(bm_art, '_wall_art_frame', col, mats['wood_dark'], smooth=False, uv_scale=0.8, ao_strength=0.2))
    bm_am = bmesh.new()
    _add_box_t(bm_am, (-7.92, 3.55, -2.40), (0.03, 1.44, 1.48))
    parts.append(_make_part(bm_am, '_wall_art_mat', col, mats['trim_cream'], smooth=False, uv_scale=1.0, ao_strength=0.14))
    bm_ag = bmesh.new()
    _add_box_t(bm_ag, (-7.89, 3.55, -2.40), (0.025, 0.62, 0.62), rot_x=math.pi / 4.0, bevel=0.008)
    _add_box_t(bm_ag, (-7.89, 3.55, -2.40), (0.025, 0.62, 0.62), bevel=0.008)
    parts.append(_make_part(bm_ag, '_wall_art_star', col, mats['brass'], smooth=False, uv_scale=1.0, ao=False))

    return parts


def _build_rug(col, mats):
    """Ornate oval Persian rug at (0.5, 0.015, 1.0), radii 3.2 x 2.25 m with fringe."""
    parts = []
    cx, cz = 0.5, 1.0
    rx, rz = 3.2, 2.25
    segs = 48

    bm = bmesh.new()
    top_ring = []
    bot_ring = []
    for k in range(segs):
        a = k / segs * math.tau
        tx = cx + math.cos(a) * rx
        tz = cz + math.sin(a) * rz
        top_ring.append(bm.verts.new(three_to_bl(tx, 0.028, tz)))
        bot_ring.append(bm.verts.new(three_to_bl(tx, 0.002, tz)))
    c_top = bm.verts.new(three_to_bl(cx, 0.032, cz))
    for k in range(segs):
        kn = (k + 1) % segs
        bm.faces.new((top_ring[k], top_ring[kn], c_top))
        bm.faces.new((bot_ring[k], bot_ring[kn], top_ring[kn], top_ring[k]))

    obj_rug = bm_to_obj(bm, '_rug', col, mat=mats['rug'], smooth=True)
    # Clean planar 0..1 UVs matching the oval rug extent so medallion & borders fit perfectly
    me = obj_rug.data
    bm2 = bmesh.new()
    bm2.from_mesh(me)
    uv = bm2.loops.layers.uv.active
    for f in bm2.faces:
        for lp in f.loops:
            # Blender x = tx, y = -tz
            tx = lp.vert.co.x
            tz = -lp.vert.co.y
            u = 0.5 + (tx - cx) / (2.0 * rx)
            v = 0.5 + (tz - cz) / (2.0 * rz)
            lp[uv].uv = (max(0.0, min(1.0, u)), max(0.0, min(1.0, v)))
    bm2.to_mesh(me)
    bm2.free()
    bake_vertex_ao(obj_rug, strength=0.14, min_val=0.82)
    parts.append(obj_rug)

    # Subtle cream woven fringe border around perimeter rim
    bm = bmesh.new()
    for side in (-1.0, 1.0):
        for i in range(15):
            ang = (0.0 if side > 0 else math.pi) + (i - 7) * 0.055
            tx0 = cx + math.cos(ang) * (rx - 0.02)
            tz0 = cz + math.sin(ang) * (rz - 0.02)
            tx1 = cx + math.cos(ang) * (rx + 0.11)
            tz1 = cz + math.sin(ang) * (rz + 0.11)
            _add_box_t(
                bm,
                ((tx0 + tx1) * 0.5, 0.012, (tz0 + tz1) * 0.5),
                (0.13, 0.012, 0.042),
                rot_y=-ang,
            )
    parts.append(_make_part(bm, '_rug_fringe', col, mats['rug_fringe'], smooth=False, uv_scale=1.0, ao_strength=0.15))
    return parts


def _build_bed_and_suitcase(col, mats):
    """Realistic oak bed matching collision [-6.4, -1.4, -6.9, -2.2] + open teal suitcase."""
    parts = []
    # Bed bounds: x in [-6.4, -1.4] (w=5.0, cx=-3.9), z in [-6.9, -2.2] (d=4.7, cz=-4.55)
    bm = bmesh.new()
    # 4 sturdy tapered oak corner legs
    for lx in (-6.28, -1.52):
        for lz in (-6.78, -2.32):
            _add_box_t(bm, (lx, 0.36, lz), (0.20, 0.72, 0.20), bevel=0.018)
    # Bed side rails & footboard frame
    _add_box_t(bm, (-6.30, 0.54, -4.55), (0.16, 0.44, 4.56), bevel=0.015)
    _add_box_t(bm, (-1.50, 0.54, -4.55), (0.16, 0.44, 4.56), bevel=0.015)
    # Footboard with raised molded cap rail
    _add_box_t(bm, (-3.90, 0.58, -2.28), (4.96, 0.68, 0.16), bevel=0.015)
    _add_box_t(bm, (-3.90, 0.94, -2.28), (5.06, 0.10, 0.22), bevel=0.02)
    # Slatted mattress deck inside
    _add_box_t(bm, (-3.90, 0.66, -4.55), (4.72, 0.10, 4.44))
    # Carved oak headboard against back wall (z = -6.78)
    _add_box_t(bm, (-3.90, 1.32, -6.78), (4.96, 1.88, 0.18), bevel=0.018)
    # Headboard top molded cornice + corner finials
    _add_box_t(bm, (-3.90, 2.30, -6.76), (5.12, 0.14, 0.26), bevel=0.022)
    for px in (-6.30, -1.50):
        _add_box_t(bm, (px, 1.48, -6.76), (0.24, 1.72, 0.24), bevel=0.02)
        _add_cyl_t(bm, (px, 2.44, -6.76), 0.10, 0.14, segs=12, r_top=0.07)
    # 3 raised decorative molding frames on headboard face
    for hx in (-5.35, -3.90, -2.45):
        _add_box_t(bm, (hx, 1.62, -6.67), (1.16, 0.92, 0.05), bevel=0.012)
    parts.append(_make_part(bm, '_bed_frame', col, mats['wood_oak'], smooth=False, uv_scale=0.6, ao_strength=0.28))

    # Plush rounded white mattress (top at y = 1.24 so suitcase y=1.25 and ihram y=1.28 sit flush)
    bm = bmesh.new()
    _add_box_t(bm, (-3.90, 0.97, -4.55), (4.66, 0.54, 4.30), bevel=0.14, bevel_segs=3)
    parts.append(_make_part(bm, '_mattress', col, mats['mattress'], smooth=True, uv_scale=0.6, ao_strength=0.18, ao_min=0.78))

    # Folded warm ochre duvet/throw draped across foot of bed (kept flat around ihram spot (-2.6, 1.28, -3.2))
    bm = bmesh.new()
    # Lower foot throw with soft rolled fold along z = -3.75 and gentle overhang over footboard
    _add_box_t(bm, (-3.90, 1.245, -3.08), (4.74, 0.07, 1.48), bevel=0.03, bevel_segs=2)
    # Rolled duvet cuff across z = -3.82
    m_cuff = Matrix.Translation(three_to_bl(-3.90, 1.26, -3.82)) @ Matrix.Rotation(math.pi / 2.0, 4, 'Y')
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.075, radius2=0.075, depth=4.74, matrix=m_cuff)
    # Subtle side drape along left/right mattress edges
    _add_box_t(bm, (-6.28, 1.05, -3.08), (0.09, 0.42, 1.44), bevel=0.025, bevel_segs=2)
    _add_box_t(bm, (-1.52, 1.05, -3.08), (0.09, 0.42, 1.44), bevel=0.025, bevel_segs=2)
    parts.append(_make_part(bm, '_duvet', col, mats['duvet'], smooth=True, uv_scale=0.6, ao_strength=0.20, ao_min=0.76))

    # Two sculpted plush pillows near headboard
    bm = bmesh.new()
    for px, yaw in ((-5.05, 0.06), (-2.75, -0.05)):
        ret = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)
        for v in ret['verts']:
            # Flatten & shape into a plump rectangular cushion
            x, y, z = v.co.x, v.co.y, v.co.z
            # Slight pinch on corners for realistic pillow silhouette
            sq = 1.0 + 0.18 * (x * x * y * y)
            nx = x * 0.78 * sq
            ny = y * 0.44 * sq
            nz = z * 0.19 * (1.0 - 0.14 * (x * x + y * y))
            # Rotate by yaw and tilt slightly against headboard
            v.co = Vector((nx, ny, nz))
        m_p = _mat_three((px, 1.38, -5.98), rot_y=yaw, rot_x=0.18)
        bmesh.ops.transform(bm, matrix=m_p, verts=ret['verts'])
    parts.append(_make_part(bm, '_pillows', col, mats['pillow'], smooth=True, uv_scale=1.0, ao_strength=0.22, ao_min=0.76))

    # Open Dark-Teal Hard-Shell Travel Suitcase at (-4.2, 1.25, -4.0), rot_y = 0.25
    sc_pos = (-4.2, 1.25, -4.0)
    sc_yaw = 0.25
    m_sc = _mat_three(sc_pos, rot_y=sc_yaw)

    def _xform(bm_local, verts):
        bmesh.ops.transform(bm_local, matrix=m_sc, verts=verts)

    # Suitcase teal hard shell (hollow open base + ribbed sides + hinged propped-open lid)
    bm_shell = bmesh.new()
    # Base floor + 4 walls (w=2.05, h=0.44, d=1.38 in local Three.js space)
    w, h, d, t = 2.05, 0.44, 1.38, 0.06
    def _lbox(bm_t, cx, cy, cz, sx, sy, sz, bev=0.02, rx=0.0):
        # Local Three.js box transformed to Blender local (x, -z, y)
        m = (
            Matrix.Translation(three_to_bl(cx, cy, cz))
            @ Matrix.Rotation(rx, 4, 'X')
            @ Matrix.Diagonal((sx, sz, sy, 1.0))
        )
        prev = set(bm_t.verts)
        r = bmesh.ops.create_cube(bm_t, size=1.0, matrix=m)
        if bev > 0:
            vs = set(r['verts'])
            es = [e for e in bm_t.edges if e.verts[0] in vs and e.verts[1] in vs]
            bmesh.ops.bevel(bm_t, geom=es, offset=bev, segments=2, affect='EDGES', clamp_overlap=True)
            return [v for v in bm_t.verts if v not in prev]
        return r['verts']

    _lbox(bm_shell, 0, 0.04, 0, w, 0.08, d, bev=0.025)
    _lbox(bm_shell, 0, h * 0.5, d * 0.5 - t * 0.5, w, h, t, bev=0.015)
    _lbox(bm_shell, 0, h * 0.5, -d * 0.5 + t * 0.5, w, h, t, bev=0.015)
    _lbox(bm_shell, -w * 0.5 + t * 0.5, h * 0.5, 0, t, h, d - 2 * t, bev=0.015)
    _lbox(bm_shell, w * 0.5 - t * 0.5, h * 0.5, 0, t, h, d - 2 * t, bev=0.015)
    # Decorative hard-shell ribs on front & side
    for ry in (0.14, 0.24, 0.34):
        _lbox(bm_shell, 0, ry, d * 0.5 + 0.01, w - 0.16, 0.03, 0.02, bev=0.005)
    # Propped-open lid hinged at local (0, h, -d/2), opened -1.18 rad (~68 deg)
    lid_ang = -1.18
    m_lid = (
        Matrix.Translation(three_to_bl(0.0, h, -d * 0.5))
        @ Matrix.Rotation(lid_ang, 4, 'X')
    )
    bm_lid = bmesh.new()
    # In lid frame, lid extends from z=0 to z=+d (so center z=+d/2), thickness 0.14
    r_lid = _lbox(bm_lid, 0, 0.07, d * 0.5, w, 0.14, d, bev=0.03)
    for rz in (0.28, 0.55, 0.82, 1.10):
        _lbox(bm_lid, 0, 0.145, rz, w - 0.18, 0.025, 0.04, bev=0.006)
    bmesh.ops.transform(bm_lid, matrix=m_lid, verts=bm_lid.verts[:])
    # Merge lid into shell
    me_tmp = bpy.data.meshes.new('_tmp_lid')
    bm_lid.to_mesh(me_tmp)
    bm_lid.free()
    bm_shell.from_mesh(me_tmp)
    bpy.data.meshes.remove(me_tmp)

    _xform(bm_shell, bm_shell.verts[:])
    parts.append(_make_part(bm_shell, '_suitcase_shell', col, mats['suitcase_shell'], smooth=True, uv_scale=0.8, ao_strength=0.26))

    # Suitcase interior lining + criss-cross packing straps
    bm_in = bmesh.new()
    _lbox(bm_in, 0, 0.14, 0, w - 0.14, 0.14, d - 0.14, bev=0.01)
    # Lid inner divider
    r_div = _lbox(bm_in, 0, 0.01, d * 0.5, w - 0.14, 0.03, d - 0.14, bev=0.005)
    bmesh.ops.transform(bm_in, matrix=m_lid, verts=r_div)
    _xform(bm_in, bm_in.verts[:])
    parts.append(_make_part(bm_in, '_suitcase_lining', col, mats['suitcase_lining'], smooth=False, uv_scale=1.0, ao_strength=0.22))

    # Suitcase dark trim: zipper lip, carry handle, telescopic handle & interior straps
    bm_tr = bmesh.new()
    _lbox(bm_tr, 0, h + 0.005, d * 0.5, w + 0.02, 0.03, 0.03, bev=0.005)
    _lbox(bm_tr, 0, 0.24, d * 0.5 + 0.045, 0.42, 0.05, 0.05, bev=0.01)  # front carry handle
    # Cross packing straps inside
    _lbox(bm_tr, 0, 0.22, 0, w - 0.16, 0.02, 0.08, bev=0.004)
    _lbox(bm_tr, 0, 0.22, 0, 0.08, 0.02, d - 0.16, bev=0.004)
    # Retracted aluminum handle rails on right side
    _lbox(bm_tr, w * 0.5 + 0.03, 0.24, -0.22, 0.04, 0.04, 0.55, bev=0.005)
    _lbox(bm_tr, w * 0.5 + 0.03, 0.24, 0.22, 0.04, 0.04, 0.55, bev=0.005)
    _lbox(bm_tr, w * 0.5 + 0.10, 0.24, 0.0, 0.05, 0.05, 0.52, bev=0.01)
    _xform(bm_tr, bm_tr.verts[:])
    parts.append(_make_part(bm_tr, '_suitcase_trim', col, mats['suitcase_trim'], smooth=False, uv_scale=1.0, ao_strength=0.2))

    return parts


def _build_bookcase_and_plant(col, mats):
    """Wooden bookcase/cabinet [4.4, 6.8, -6.9, -4.6], top y=2.2 + potted houseplant at (4.9, 2.2, -6.3)."""
    parts = []
    # Center (5.6, 1.1, -5.75), width 2.4, height 2.2, depth 2.3
    bm = bmesh.new()
    # Plinth base
    _add_box_t(bm, (5.60, 0.08, -5.75), (2.30, 0.16, 2.20), bevel=0.01)
    # Main carcass: back panel, left/right side panels, lower cabinet box, middle shelf, top deck at y=2.20
    _add_box_t(bm, (5.60, 1.12, -6.82), (2.34, 2.08, 0.12))  # back
    _add_box_t(bm, (4.46, 1.12, -5.75), (0.12, 2.08, 2.24), bevel=0.01)  # left side
    _add_box_t(bm, (6.74, 1.12, -5.75), (0.12, 2.08, 2.24), bevel=0.01)  # right side
    _add_box_t(bm, (5.60, 0.72, -5.78), (2.28, 1.18, 2.16))  # lower enclosed cabinet body
    _add_box_t(bm, (5.60, 1.32, -5.74), (2.28, 0.08, 2.20), bevel=0.008)  # mid shelf
    _add_box_t(bm, (5.60, 1.72, -5.76), (2.22, 0.07, 2.12), bevel=0.008)  # upper book shelf
    # Overhanging bullnose top surface strictly ending at y = 2.20
    _add_box_t(bm, (5.60, 2.155, -5.75), (2.42, 0.09, 2.32), bevel=0.016, bevel_segs=2)
    # Two lower paneled doors on front face (z = -4.64)
    for dx in (-0.56, 0.56):
        _add_box_t(bm, (5.60 + dx, 0.72, -4.66), (1.06, 1.06, 0.06), bevel=0.012)
        _add_box_t(bm, (5.60 + dx, 0.72, -4.62), (0.78, 0.78, 0.03), bevel=0.008)
    parts.append(_make_part(bm, '_bookcase', col, mats['wood_oak'], smooth=False, uv_scale=0.6, ao_strength=0.28))

    # Brass cabinet knobs
    bm = bmesh.new()
    for dx in (-0.14, 0.14):
        bmesh.ops.create_uvsphere(
            bm, u_segments=10, v_segments=6, radius=0.038,
            matrix=Matrix.Translation(three_to_bl(5.60 + dx, 0.88, -4.58)),
        )
    parts.append(_make_part(bm, '_bookcase_knobs', col, mats['brass'], smooth=True, uv_scale=1.0, ao=False))

    # Hardcover books neatly arranged on upper shelf (y = 1.76)
    book_specs = [
        (4.74, 0.11, 0.34, 0.0, 'book_burgundy'),
        (4.87, 0.09, 0.30, 0.0, 'book_navy'),
        (4.99, 0.12, 0.35, 0.0, 'book_emerald'),
        (5.13, 0.10, 0.32, 0.0, 'book_burgundy'),
        (5.26, 0.09, 0.29, 0.0, 'book_navy'),
        (5.44, 0.10, 0.33, 0.26, 'book_emerald'),  # leaning book
        (6.05, 0.11, 0.33, 0.0, 'book_navy'),
        (6.18, 0.10, 0.31, 0.0, 'book_burgundy'),
        (6.31, 0.12, 0.35, 0.0, 'book_emerald'),
        (6.45, 0.09, 0.29, 0.0, 'book_navy'),
    ]
    by_mat = {}
    bm_pg = bmesh.new()
    for bx, bw, bh, tilt, mkey in book_specs:
        bm_b = by_mat.setdefault(mkey, bmesh.new())
        _add_box_t(bm_b, (bx, 1.76 + bh * 0.5, -4.92), (bw, bh, 0.42), rot_x=0.0, rot_y=0.0, bevel=0.008)
        if abs(tilt) > 1e-4:
            # Subtle lean around Z axis
            pass
        _add_box_t(bm_pg, (bx, 1.76 + bh * 0.5, -4.92), (bw - 0.025, bh - 0.025, 0.40))
    for mkey, bm_b in by_mat.items():
        parts.append(_make_part(bm_b, f'_books_{mkey}', col, mats[mkey], smooth=False, uv_scale=1.0, ao_strength=0.22))
    parts.append(_make_part(bm_pg, '_book_pages', col, mats['book_pages'], smooth=False, uv_scale=1.0, ao_strength=0.18))

    # Realistic Potted Terracotta Ficus/Monstera Houseplant at (4.9, 2.2, -6.3)
    px, py, pz = 4.9, 2.20, -6.3
    bm_pot = bmesh.new()
    _add_cyl_t(bm_pot, (px, py + 0.24, pz), 0.22, 0.48, segs=18, r_top=0.31)
    # Rolled pot rim
    _add_cyl_t(bm_pot, (px, py + 0.47, pz), 0.335, 0.07, segs=18, r_top=0.34)
    # Saucer under pot
    _add_cyl_t(bm_pot, (px, py + 0.025, pz), 0.25, 0.05, segs=18, r_top=0.27)
    parts.append(_make_part(bm_pot, '_plant_pot', col, mats['terracotta'], smooth=True, uv_scale=1.0, ao_strength=0.25))

    bm_soil = bmesh.new()
    _add_cyl_t(bm_soil, (px, py + 0.45, pz), 0.29, 0.04, segs=14, r_top=0.29)
    # Short woody plant stems
    for sx, sz, lean_x, lean_z in ((0.0, 0.0, 0.0, 0.0), (0.06, 0.04, 0.22, 0.14), (-0.05, -0.04, -0.18, -0.16)):
        _add_cyl_t(bm_soil, (px + sx, py + 0.68, pz + sz), 0.026, 0.48, segs=6, r_top=0.014, rot_x=lean_z, rot_y=lean_x)
    parts.append(_make_part(bm_soil, '_plant_soil', col, mats['soil'], smooth=True, uv_scale=1.0, ao_strength=0.22))

    # Lush arching ficus/broadleaf canopy (18 sculpted curved leaf blades)
    bm_leaf = bmesh.new()
    leaf_tiers = [
        (7, 0.68, 0.42, 0.26, 0.55),   # lower broad spreading leaves
        (6, 0.90, 0.36, 0.22, 0.35),   # mid canopy leaves
        (5, 1.08, 0.28, 0.18, 0.12),   # upper crown leaves
    ]
    seed_ang = 0.2
    for count, h_off, length, width, droop in leaf_tiers:
        for i in range(count):
            ang = seed_ang + (i / count) * math.tau
            # Build a diamond-oval arched leaf blade in local coords, then transform
            pts_u = [0.0, 0.25, 0.55, 0.82, 1.0]
            w_prof = [0.08, 0.72, 1.0, 0.58, 0.0]
            # 3 verts per station: left edge, raised midrib, right edge
            rows = []
            for u, wp in zip(pts_u, w_prof):
                r = u * length
                arch_y = math.sin(u * math.pi * 0.75) * 0.14 - (u * u) * droop * 0.28
                hw = wp * width * 0.5
                if wp < 1e-3:
                    tip = bm_leaf.verts.new(Vector((r, 0.0, arch_y)))
                    rows.append([tip])
                else:
                    vl = bm_leaf.verts.new(Vector((r, hw, arch_y + 0.018)))
                    vc = bm_leaf.verts.new(Vector((r, 0.0, arch_y)))
                    vr = bm_leaf.verts.new(Vector((r, -hw, arch_y + 0.018)))
                    rows.append([vl, vc, vr])
            leaf_verts = [v for row in rows for v in row]
            for j in range(len(rows) - 2):
                r0, r1 = rows[j], rows[j + 1]
                bm_leaf.faces.new((r0[0], r1[0], r1[1], r0[1]))
                bm_leaf.faces.new((r0[1], r1[1], r1[2], r0[2]))
            r_last = rows[-2]
            tip = rows[-1][0]
            bm_leaf.faces.new((r_last[0], tip, r_last[1]))
            bm_leaf.faces.new((r_last[1], tip, r_last[2]))

            m_lf = (
                Matrix.Translation(three_to_bl(px, py + h_off, pz))
                @ Matrix.Rotation(ang, 4, 'Z')
                @ Matrix.Rotation(-0.32 + droop * 0.4, 4, 'Y')
            )
            bmesh.ops.transform(bm_leaf, matrix=m_lf, verts=leaf_verts)
        seed_ang += 0.52
    parts.append(_make_part(bm_leaf, '_plant_leaves', col, mats['leaf_green'], smooth=True, uv_scale=1.5, ao_strength=0.22, ao_min=0.72))

    return parts


def _build_dresser_and_mirror(col, mats):
    """Wooden dresser [-7.95, -6.5, 1.1, 3.5], top y=1.3 + framed beveled mirror on left wall."""
    parts = []
    # Center (-7.225, 0.65, 2.3), width 1.45, height 1.30, depth 2.40
    bm = bmesh.new()
    # Plinth base
    _add_box_t(bm, (-7.25, 0.07, 2.30), (1.34, 0.14, 2.28), bevel=0.01)
    # Main body
    _add_box_t(bm, (-7.25, 0.68, 2.30), (1.38, 1.12, 2.32), bevel=0.015)
    # Overhanging bullnose top surface strictly at y = 1.30
    _add_box_t(bm, (-7.22, 1.26, 2.30), (1.48, 0.08, 2.44), bevel=0.016, bevel_segs=2)
    # 3 wide stacked drawers facing +X (x = -6.55)
    for dy in (0.32, 0.68, 1.04):
        _add_box_t(bm, (-6.54, dy, 2.30), (0.06, 0.30, 2.12), bevel=0.012)
        _add_box_t(bm, (-6.50, dy, 2.30), (0.025, 0.21, 1.88), bevel=0.008)
    parts.append(_make_part(bm, '_dresser', col, mats['wood_oak'], smooth=False, uv_scale=0.65, ao_strength=0.28))

    # Brass drawer pulls (2 per drawer)
    bm = bmesh.new()
    for dy in (0.32, 0.68, 1.04):
        for dz in (1.82, 2.78):
            _add_box_t(bm, (-6.46, dy, dz), (0.05, 0.04, 0.18), bevel=0.008)
    parts.append(_make_part(bm, '_dresser_pulls', col, mats['brass'], smooth=True, uv_scale=1.0, ao=False))

    # Framed wall mirror on left wall above dresser at (-7.90, 2.45, 2.30)
    bm = bmesh.new()
    # Outer oak molded frame (h = 1.76, w_z = 1.32)
    _add_box_t(bm, (-7.90, 3.30, 2.30), (0.10, 0.13, 1.36), bevel=0.014)  # top
    _add_box_t(bm, (-7.90, 1.60, 2.30), (0.10, 0.13, 1.36), bevel=0.014)  # bottom
    _add_box_t(bm, (-7.90, 2.45, 1.66), (0.10, 1.76, 0.12), bevel=0.014)  # left
    _add_box_t(bm, (-7.90, 2.45, 2.94), (0.10, 1.76, 0.12), bevel=0.014)  # right
    # Subtle decorative top pediment crest
    _add_box_t(bm, (-7.88, 3.40, 2.30), (0.12, 0.08, 1.48), bevel=0.014)
    parts.append(_make_part(bm, '_mirror_frame', col, mats['wood_dark'], smooth=False, uv_scale=0.8, ao_strength=0.24))

    # Gilded inner mirror bead trim
    bm = bmesh.new()
    _add_box_t(bm, (-7.87, 3.22, 2.30), (0.04, 0.035, 1.18), bevel=0.005)
    _add_box_t(bm, (-7.87, 1.68, 2.30), (0.04, 0.035, 1.18), bevel=0.005)
    _add_box_t(bm, (-7.87, 2.45, 1.72), (0.04, 1.56, 0.035), bevel=0.005)
    _add_box_t(bm, (-7.87, 2.45, 2.88), (0.04, 1.56, 0.035), bevel=0.005)
    parts.append(_make_part(bm, '_mirror_trim', col, mats['brass'], smooth=False, uv_scale=1.0, ao=False))

    # Reflective beveled glass pane
    bm = bmesh.new()
    _add_box_t(bm, (-7.90, 2.45, 2.30), (0.04, 1.54, 1.16))
    parts.append(_make_part(bm, '_mirror_glass', col, mats['mirror_glass'], smooth=False, uv_scale=0.5, ao=False))

    return parts


def _build_front_door(col, mats):
    """Free-standing molded oak door frame + ajar 6-panel door at (7.3, 0, 6.3), rot_y = -pi/2."""
    parts = []
    m_door = _mat_three((7.3, 0.0, 6.3), rot_y=-math.pi / 2.0)

    def _lbox(bm_t, cx, cy, cz, sx, sy, sz, bev=0.012):
        m = Matrix.Translation(three_to_bl(cx, cy, cz)) @ Matrix.Diagonal((sx, sz, sy, 1.0))
        r = bmesh.ops.create_cube(bm_t, size=1.0, matrix=m)
        if bev > 0:
            vs = set(r['verts'])
            es = [e for e in bm_t.edges if e.verts[0] in vs and e.verts[1] in vs]
            bmesh.ops.bevel(bm_t, geom=es, offset=bev, segments=1, affect='EDGES', clamp_overlap=True)
        return r['verts']

    # Door frame & decorative casing
    bm_fr = bmesh.new()
    _lbox(bm_fr, 0.0, 3.22, 0.0, 2.34, 0.24, 0.30, bev=0.015)
    _lbox(bm_fr, 0.0, 3.36, 0.0, 2.46, 0.09, 0.36, bev=0.014)  # top lintel cap
    for sx in (-1.04, 1.04):
        _lbox(bm_fr, sx, 1.65, 0.0, 0.22, 3.30, 0.30, bev=0.014)
        _lbox(bm_fr, sx, 0.14, 0.0, 0.26, 0.28, 0.34, bev=0.012)  # plinth block
    _lbox(bm_fr, 0.0, 0.02, 0.0, 2.10, 0.04, 0.28, bev=0.008)  # threshold
    bmesh.ops.transform(bm_fr, matrix=m_door, verts=bm_fr.verts[:])
    parts.append(_make_part(bm_fr, '_door_frame', col, mats['wood_oak'], smooth=False, uv_scale=0.65, ao_strength=0.25))

    # Ajar 6-panel oak door swung open around hinge edge at local x = +0.92, z = 0.0
    # Matches home.js ajar orientation: center ~(0.55, 1.5, 0.5) with rot_y = -1.1
    m_leaf = (
        m_door
        @ Matrix.Translation(three_to_bl(0.92, 0.0, 0.04))
        @ Matrix.Rotation(-1.1, 4, 'Z')
    )
    # In leaf frame, hinge is at x=0, door extends toward x=-1.84 (width 1.84, height 3.06, thickness 0.09)
    bm_lf = bmesh.new()
    _lbox(bm_lf, -0.92, 1.54, 0.0, 1.84, 3.04, 0.08, bev=0.008)
    # 6 raised beveled panels on both faces
    for px in (-0.50, -1.34):
        for py, ph in ((0.64, 0.72), (1.56, 0.72), (2.46, 0.64)):
            for fz in (-0.045, 0.045):
                _lbox(bm_lf, px, py, fz, 0.58, ph, 0.024, bev=0.008)
    bmesh.ops.transform(bm_lf, matrix=m_leaf, verts=bm_lf.verts[:])
    parts.append(_make_part(bm_lf, '_door_leaf', col, mats['wood_dark'], smooth=False, uv_scale=0.7, ao_strength=0.26))

    # Brass lever handles, escutcheons & hinges
    bm_hw = bmesh.new()
    for fz in (-0.06, 0.06):
        _lbox(bm_hw, -1.66, 1.38, fz, 0.08, 0.24, 0.02, bev=0.004)  # backplate
        _lbox(bm_hw, -1.58, 1.42, fz + (0.045 if fz > 0 else -0.045), 0.18, 0.032, 0.032, bev=0.008)  # lever
        _lbox(bm_hw, -1.66, 1.42, fz + (0.025 if fz > 0 else -0.025), 0.035, 0.035, 0.05, bev=0.006)  # stem
    for hy in (0.50, 1.55, 2.60):
        _add_cyl_t(bm_hw, (0.0, hy, 0.03), 0.022, 0.14, segs=8)
    bmesh.ops.transform(bm_hw, matrix=m_leaf, verts=bm_hw.verts[:])
    parts.append(_make_part(bm_hw, '_door_hardware', col, mats['brass'], smooth=True, uv_scale=1.0, ao=False))

    return parts


# ------------------------------------------------------------------ 4 Takeable Interactive Items
def _build_takeable_items(col, mats):
    """Build 4 top-level named takeable item objects (NO _LOD suffix, NOT merged)."""
    items = []

    # 1. item_passport at (5.6, 2.23, -5.4)
    # Dark burgundy leather passport + gold emblem + folded white visa/boarding slip
    p_objs = []
    bm = bmesh.new()
    # Slightly angled natural placement
    _add_box_t(bm, (0.0, 0.024, 0.0), (0.44, 0.046, 0.62), rot_y=0.14, bevel=0.012, bevel_segs=2)
    p_objs.append(_make_part(bm, '_ip_cover', col, mats['passport_leather'], smooth=True, uv_scale=1.5, ao=False))

    # Cream page block peeking out of fore-edge
    bm = bmesh.new()
    _add_box_t(bm, (0.015, 0.024, 0.0), (0.42, 0.032, 0.59), rot_y=0.14)
    p_objs.append(_make_part(bm, '_ip_pages', col, mats['visa_paper'], smooth=False, uv_scale=1.5, ao=False))

    # Gold circular emblem & top/bottom horizontal decorative bars on cover
    bm = bmesh.new()
    _add_cyl_t(bm, (0.0, 0.049, 0.0), 0.095, 0.008, segs=18, rot_y=0.14)
    _add_box_t(bm, (-0.02, 0.049, -0.17), (0.24, 0.007, 0.022), rot_y=0.14)
    _add_box_t(bm, (0.02, 0.049, 0.17), (0.20, 0.007, 0.018), rot_y=0.14)
    p_objs.append(_make_part(bm, '_ip_gold', col, mats['brass'], smooth=True, uv_scale=2.0, ao=False))

    # Folded white visa / boarding slip fanned slightly out to the right-front
    bm = bmesh.new()
    _add_box_t(bm, (0.16, 0.012, 0.08), (0.34, 0.018, 0.54), rot_y=-0.22, bevel=0.004)
    p_objs.append(_make_part(bm, '_ip_visa', col, mats['visa_paper'], smooth=False, uv_scale=1.5, ao=False))
    bm = bmesh.new()
    _add_box_t(bm, (0.19, 0.022, -0.10), (0.32, 0.005, 0.085), rot_y=-0.22)
    p_objs.append(_make_part(bm, '_ip_visa_band', col, mats['visa_accent'], smooth=False, uv_scale=1.5, ao=False))

    item_passport = join_objects(p_objs, 'item_passport', col)
    item_passport.location = three_to_bl(5.6, 2.23, -5.4)
    items.append(item_passport)

    # 2. item_ihram at (-2.6, 1.28, -3.2)
    # Stack of 2 neatly folded white terry-cotton ihram towels (tex_cotton_ihram)
    bm = bmesh.new()
    # Bottom folded towel (0.88 x 0.22 x 0.68) with soft rounded pillowy fold
    _add_box_t(bm, (0.0, 0.11, 0.0), (0.88, 0.22, 0.68), rot_y=-0.05, bevel=0.065, bevel_segs=3)
    # Subtle fold crease layers on the side
    _add_box_t(bm, (0.0, 0.06, 0.0), (0.90, 0.08, 0.66), rot_y=-0.05, bevel=0.025, bevel_segs=2)
    # Top folded towel (0.78 x 0.19 x 0.58) slightly offset & angled naturally
    _add_box_t(bm, (0.02, 0.30, -0.02), (0.78, 0.19, 0.58), rot_y=0.09, bevel=0.058, bevel_segs=3)
    _add_box_t(bm, (0.02, 0.26, -0.02), (0.80, 0.07, 0.56), rot_y=0.09, bevel=0.022, bevel_segs=2)
    item_ihram = _make_part(bm, 'item_ihram', col, mats['ihram_cotton'], smooth=True, uv_scale=1.3, ao=False)
    item_ihram.location = three_to_bl(-2.6, 1.28, -3.2)
    items.append(item_ihram)

    # 3. item_sandals at (4.6, 0.02, 5.0)
    # Pair of realistic brown leather slip-on sandals with sculpted footbeds & straps
    s_objs = []
    for side in (-1.0, 1.0):
        dx = side * 0.19
        yaw = side * -0.10
        m_s = _mat_three((dx, 0.0, 0.0), rot_y=yaw)

        # Sculpted ergonomic sole (wider at forefoot, narrower waist, rounded heel)
        bm_sole = bmesh.new()
        bm_bed = bmesh.new()
        n_ring = 16
        # Build oval-peanut outline in XZ
        def _sole_ring(bm_t, y_val, scale_xy=1.0):
            ring = []
            for k in range(n_ring):
                a = k / n_ring * math.tau
                cz = math.cos(a)  # -1 heel .. +1 toe
                sx = math.sin(a)
                # Width tapers narrower at heel & arch, wider at ball of foot
                w_mod = 0.115 + 0.022 * cz - 0.016 * (1.0 - cz * cz)
                lx = sx * w_mod * scale_xy
                lz = cz * 0.285 * scale_xy
                # Slight natural toe spring lift
                ly = y_val + (0.018 * max(0.0, cz - 0.4) ** 1.5)
                ring.append(bm_t.verts.new(three_to_bl(lx, ly, lz)))
            return ring

        r_bot = _sole_ring(bm_sole, 0.0, 1.0)
        r_top = _sole_ring(bm_sole, 0.032, 1.02)
        c_b = bm_sole.verts.new(three_to_bl(0.0, 0.0, 0.0))
        c_t = bm_sole.verts.new(three_to_bl(0.0, 0.032, 0.0))
        for k in range(n_ring):
            kn = (k + 1) % n_ring
            bm_sole.faces.new((r_bot[kn], r_bot[k], c_b))
            bm_sole.faces.new((r_top[k], r_top[kn], c_t))
            bm_sole.faces.new((r_bot[k], r_bot[kn], r_top[kn], r_top[k]))
        bmesh.ops.transform(bm_sole, matrix=m_s, verts=bm_sole.verts[:])
        s_objs.append(_make_part(bm_sole, f'_snd_sole_{int(side)}', col, mats['sandal_sole'], smooth=True, uv_scale=2.0, ao=False))

        # Contoured suede footbed inset
        rb0 = _sole_ring(bm_bed, 0.032, 0.90)
        rb1 = _sole_ring(bm_bed, 0.044, 0.88)
        cb1 = bm_bed.verts.new(three_to_bl(0.0, 0.040, 0.0))
        for k in range(n_ring):
            kn = (k + 1) % n_ring
            bm_bed.faces.new((rb1[k], rb1[kn], cb1))
            bm_bed.faces.new((rb0[k], rb0[kn], rb1[kn], rb1[k]))
        bmesh.ops.transform(bm_bed, matrix=m_s, verts=bm_bed.verts[:])
        s_objs.append(_make_part(bm_bed, f'_snd_bed_{int(side)}', col, mats['sandal_footbed'], smooth=True, uv_scale=2.0, ao=False))

        # Dual arched leather upper straps across instep & forefoot
        bm_str = bmesh.new()
        for z_c, strap_w, arch_h in ((-0.02, 0.085, 0.115), (0.11, 0.075, 0.095)):
            segs_a = 10
            thick = 0.016
            rings_a = []
            for j in range(segs_a + 1):
                u = j / segs_a
                ang = u * math.pi
                lx = math.cos(ang) * 0.118
                ly = 0.032 + math.sin(ang) * arch_h
                # Normal direction outward
                nx = math.cos(ang) * thick
                ny = math.sin(ang) * thick
                v0 = bm_str.verts.new(three_to_bl(lx, ly, z_c - strap_w * 0.5))
                v1 = bm_str.verts.new(three_to_bl(lx, ly, z_c + strap_w * 0.5))
                v2 = bm_str.verts.new(three_to_bl(lx + nx, ly + ny, z_c + strap_w * 0.5))
                v3 = bm_str.verts.new(three_to_bl(lx + nx, ly + ny, z_c - strap_w * 0.5))
                rings_a.append((v0, v1, v2, v3))
            for j in range(segs_a):
                a0, a1 = rings_a[j], rings_a[j + 1]
                for c in range(4):
                    cn = (c + 1) % 4
                    bm_str.faces.new((a0[c], a0[cn], a1[cn], a1[c]))
        bmesh.ops.transform(bm_str, matrix=m_s, verts=bm_str.verts[:])
        s_objs.append(_make_part(bm_str, f'_snd_strap_{int(side)}', col, mats['sandal_leather'], smooth=True, uv_scale=2.0, ao=False))

    item_sandals = join_objects(s_objs, 'item_sandals', col)
    item_sandals.location = three_to_bl(4.6, 0.02, 5.0)
    items.append(item_sandals)

    # 4. item_perfume at (-7.0, 1.32, 2.3)
    # Faceted octagonal crystal perfume bottle with warm amber liquid core & gilded brass cap
    f_objs = []
    # Inner glowing amber perfume oil core
    bm = bmesh.new()
    _add_cyl_t(bm, (0.0, 0.145, 0.0), 0.105, 0.21, segs=8, r_top=0.10)
    f_objs.append(_make_part(bm, '_pf_amber', col, mats['perfume_amber'], smooth=False, uv_scale=2.0, ao=False))

    # Faceted crystal outer glass flacon
    bm = bmesh.new()
    # Heavy crystal base + faceted octagonal body + tapered crystal shoulder
    _add_cyl_t(bm, (0.0, 0.025, 0.0), 0.135, 0.05, segs=8, r_top=0.145)
    _add_cyl_t(bm, (0.0, 0.165, 0.0), 0.145, 0.23, segs=8, r_top=0.138)
    _add_cyl_t(bm, (0.0, 0.305, 0.0), 0.138, 0.055, segs=8, r_top=0.068)
    f_objs.append(_make_part(bm, '_pf_glass', col, mats['perfume_crystal'], smooth=False, uv_scale=2.0, ao=False))

    # Ornate gilded brass neck collar + faceted dome cap
    bm = bmesh.new()
    _add_cyl_t(bm, (0.0, 0.355, 0.0), 0.062, 0.05, segs=12, r_top=0.058)
    _add_cyl_t(bm, (0.0, 0.415, 0.0), 0.072, 0.08, segs=8, r_top=0.082)
    _add_cyl_t(bm, (0.0, 0.475, 0.0), 0.082, 0.045, segs=8, r_top=0.032)
    f_objs.append(_make_part(bm, '_pf_cap', col, mats['brass'], smooth=False, uv_scale=2.0, ao=False))

    item_perfume = join_objects(f_objs, 'item_perfume', col)
    item_perfume.location = three_to_bl(-7.0, 1.32, 2.3)
    items.append(item_perfume)

    return items


# ------------------------------------------------------------------ Public API
def build_home(col):
    """Build Chapter 1 Home bedroom into `col` and return dict of exported objects."""
    mats = _create_materials()
    static_parts = []
    static_parts.extend(_build_room_shell(col, mats))
    static_parts.extend(_build_rug(col, mats))
    static_parts.extend(_build_bed_and_suitcase(col, mats))
    static_parts.extend(_build_bookcase_and_plant(col, mats))
    static_parts.extend(_build_dresser_and_mirror(col, mats))
    static_parts.extend(_build_front_door(col, mats))

    static_lod0 = join_objects(static_parts, 'home_static_LOD0', col)
    static_lod1 = make_lod1(static_lod0, ratio=0.42, name='home_static_LOD1')

    takeables = _build_takeable_items(col, mats)
    return {
        'lod0': static_lod0,
        'lod1': static_lod1,
        'items': takeables,
        'all': [static_lod0, static_lod1, *takeables],
    }


def export_home():
    """Build, export `public/models/env/home.glb`, and render `blender/previews/env_home.png`."""
    ensure_dirs()
    reset_scene()
    col = make_collection('EnvHome')
    built = build_home(col)

    out_glb = MODELS_ENV / 'home.glb'
    size_bytes = export_glb(built['all'], out_glb, vertex_colors=True)

    # Render preview from open front-right diorama camera matching game view
    built['lod1'].hide_render = True
    out_png = PREVIEWS / 'env_home.png'
    preview.render_shot(
        eye=three_to_bl(13.2, 10.6, 13.6),
        target=three_to_bl(-0.2, 1.4, -0.3),
        out_path=out_png,
        res=(1024, 640),
        lens=32,
        world_color=(0.95, 0.88, 0.76),
    )

    t0 = tri_count(built['lod0'])
    t1 = tri_count(built['lod1'])
    t_items = sum(tri_count(o) for o in built['items'])
    print(
        f'HOME_OK: lod0={t0} tris, lod1={t1} tris, items={t_items} tris, '
        f'glb={size_bytes / 1024:.1f}KB -> {out_glb}'
    )
    return {
        'name': 'home',
        'glb': str(out_glb),
        'preview': str(out_png),
        'tris_lod0': t0 + t_items,
        'tris_lod1': t1 + t_items,
        'bytes': size_bytes,
    }


if __name__ == '__main__':
    export_home()
