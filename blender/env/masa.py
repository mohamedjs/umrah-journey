"""Chapter 7 — Al-Mas'a gallery environment builder (Blender 5.2 LTS -> public/models/env/masa.glb).

Builds the realistic Al-Mas'a gallery between As-Safa (z=+10.5) and Al-Marwa (z=-130.5):
veined cream marble floor with inlaid lane borders, sculpted central marble balustrade
with bronze handrail (|x| <= 0.6, z in [-117, -3]), arched marble gallery walls, coffered
ceiling, fluted marble colonnades with gilded capitals and transverse pointed Islamic arches,
24 ornate brass chandeliers, bright emerald-green Al-Milayn al-Akhdarayn LED beams/bands
(z in [-38, -55]), natural fractured Hijazi granite Safa & Marwa hills behind curved marble
and brushed-brass railings (r=8.0 m), marble approach aprons, and gilded Qibla plaques.

Every coordinate converts Three.js world space (tx, ty, tz) via three_to_bl().
"""
import math
import os
from pathlib import Path
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

from blender.lib import preview, textures  # noqa: E402
from blender.lib.common import (  # noqa: E402
    MODELS_ENV,
    PREVIEWS,
    add_box,
    add_cylinder,
    add_tube,
    bake_vertex_ao,
    bm_to_obj,
    ensure_dirs,
    export_glb,
    join_objects,
    loft_rings,
    make_collection,
    make_pbr_material,
    reset_scene,
    three_to_bl,
    tri_count,
    uv_box_project,
    uv_cylindrical,
)

# ------------------------------------------------------------------ exact game constants (src/game/masa.js)
LEN = 120.0
HALF_W = 10.0
GREEN = (-38.0, -55.0)
SAFA_Z = 1.5
MARWA_Z = -LEN - 1.5  # -121.5
Z_MID = -LEN * 0.5    # -60.0
FULL = LEN + 34.0     # 154.0 -> z in [-137.0, +17.0]
Z_MIN = Z_MID - FULL * 0.5  # -137.0
Z_MAX = Z_MID + FULL * 0.5  # +17.0

OUT_GLB = MODELS_ENV / 'masa.glb'
OUT_PREVIEW = PREVIEWS / 'env_masa.png'
BUDGET_LOD0_TRIS = 34000
BUDGET_LOD1_TRIS = 14000
BUDGET_KB = 700


# ------------------------------------------------------------------ Three.js space helpers
def _tbox(bm, x0, x1, y0, y1, z0, z1, rot_y=0.0):
    cx = (x0 + x1) * 0.5
    cy = (y0 + y1) * 0.5
    cz = (z0 + z1) * 0.5
    sx = abs(x1 - x0)
    sy = abs(z1 - z0)
    sz = abs(y1 - y0)
    return add_box(bm, three_to_bl(cx, cy, cz), (sx, sy, sz), rot_z=rot_y)


def _tcyl(bm, tx, y0, y1, tz, r1, r2=None, segs=12, cap_ends=True, rot_y=0.0):
    h = abs(y1 - y0)
    cy = (y0 + y1) * 0.5
    return add_cylinder(
        bm,
        center=three_to_bl(tx, cy, tz),
        radius=r1,
        radius_top=r1 if r2 is None else r2,
        height=h,
        segs=segs,
        cap_ends=cap_ends,
        rot_z=rot_y,
    )


def _tsphere(bm, tx, ty, tz, radius, segs=8, rings=6):
    mat = Matrix.Translation(three_to_bl(tx, ty, tz))
    return bmesh.ops.create_uvsphere(
        bm,
        u_segments=int(segs),
        v_segments=int(rings),
        radius=float(radius),
        matrix=mat,
    )


def _add_transverse_pointed_arch(bm, z_center, half_span, y_spring, y_apex, thick_y, depth_z, segs=8):
    """Add a graceful four-centered/pointed Islamic arch spanning X in [-half_span, +half_span]."""
    n = max(4, int(segs))
    arch_h = y_apex - y_spring
    pts_in = []
    pts_out = []
    # Left half: (-half_span, y_spring) -> (0, y_apex)
    for i in range(n + 1):
        t = i / n
        ang = t * (math.pi * 0.5)
        x_in = -half_span * math.cos(ang)
        y_in = y_spring + arch_h * (math.sin(ang) ** 0.78)
        y_out = min(12.22, y_in + thick_y * (1.0 + 0.35 * (1.0 - math.sin(ang))))
        pts_in.append((x_in, y_in))
        pts_out.append((x_in, y_out))
    # Right half: (0, y_apex) -> (+half_span, y_spring)
    for i in range(1, n + 1):
        t = i / n
        ang = (1.0 - t) * (math.pi * 0.5)
        x_in = half_span * math.cos(ang)
        y_in = y_spring + arch_h * (math.sin(ang) ** 0.78)
        y_out = min(12.22, y_in + thick_y * (1.0 + 0.35 * (1.0 - math.sin(ang))))
        pts_in.append((x_in, y_in))
        pts_out.append((x_in, y_out))

    z0 = z_center - depth_z * 0.5
    z1 = z_center + depth_z * 0.5
    rings = []
    for (ix, iy), (ox, oy) in zip(pts_in, pts_out):
        v0 = bm.verts.new(three_to_bl(ix, iy, z0))
        v1 = bm.verts.new(three_to_bl(ox, oy, z0))
        v2 = bm.verts.new(three_to_bl(ox, oy, z1))
        v3 = bm.verts.new(three_to_bl(ix, iy, z1))
        rings.append([v0, v1, v2, v3])
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)


def _add_wall_pointed_niche_arch(bm, x_wall, side_sign, z_center, y_spring, span_z, arch_h, thick, proj, segs=5):
    """Add a projecting pointed Islamic arch surround on a side wall (x = +-10.0) facing inward."""
    half = span_z * 0.5
    n = max(3, int(segs))
    pts_in = []
    pts_out = []
    for i in range(n + 1):
        t = i / n
        ang = t * (math.pi * 0.5)
        dz = -half * math.cos(ang)
        dy = arch_h * (math.sin(ang) ** 0.82)
        nz = -math.cos(ang) * 0.85
        ny = math.sin(ang)
        ln = math.hypot(nz, ny) or 1.0
        pts_in.append((z_center + dz, y_spring + dy))
        pts_out.append((z_center + dz + (nz / ln) * thick, y_spring + dy + (ny / ln) * thick))
    for i in range(1, n + 1):
        t = i / n
        ang = (1.0 - t) * (math.pi * 0.5)
        dz = half * math.cos(ang)
        dy = arch_h * (math.sin(ang) ** 0.82)
        nz = math.cos(ang) * 0.85
        ny = math.sin(ang)
        ln = math.hypot(nz, ny) or 1.0
        pts_in.append((z_center + dz, y_spring + dy))
        pts_out.append((z_center + dz + (nz / ln) * thick, y_spring + dy + (ny / ln) * thick))

    x_back = x_wall
    x_front = x_wall - side_sign * proj
    xa, xb = (x_front, x_back) if x_front < x_back else (x_back, x_front)
    rings = []
    for (iz, iy), (oz, oy) in zip(pts_in, pts_out):
        v0 = bm.verts.new(three_to_bl(xa, iy, iz))
        v1 = bm.verts.new(three_to_bl(xa, oy, oz))
        v2 = bm.verts.new(three_to_bl(xb, oy, oz))
        v3 = bm.verts.new(three_to_bl(xb, iy, iz))
        rings.append([v0, v1, v2, v3])
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)


def _add_fluted_column(bm, tx, y0, y1, tz, radius, flutes=12):
    """Add a vertical column shaft with subtle architectural fluting grooves."""
    n_verts = max(8, int(flutes) * 2)
    rings = []
    for y in (y0, y1):
        ring = []
        for k in range(n_verts):
            ang = k / n_verts * math.tau
            r = radius * (0.955 if (k % 2 == 1) else 1.0)
            ring.append(bm.verts.new(three_to_bl(tx + math.cos(ang) * r, y, tz + math.sin(ang) * r)))
        rings.append(ring)
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)


def _add_granite_outcrop(bm, center_x, center_z, radius_x, radius_z, height, seed, subdiv=2):
    """Create a realistic jagged fractured Hijazi granite boulder/outcrop with angular strata.

    Uses deterministic multi-plane fracturing & stepped rock ledges rather than uniform
    spheres/dodecahedrons so As-Safa and Al-Marwa read as authentic Makkah granite.
    """
    rng = np.random.default_rng(int(seed))
    sub = bmesh.new()
    bmesh.ops.create_icosphere(sub, subdivisions=int(subdiv), radius=1.0)

    # Generate 5 deterministic rock fracture cleavage planes for crisp angular facets
    planes = []
    for _ in range(5):
        n = rng.normal(0.0, 1.0, size=3)
        n[2] = abs(n[2]) * 0.6 + 0.25  # bias strata slightly upward
        n /= (np.linalg.norm(n) + 1e-6)
        d = rng.uniform(0.38, 0.72)
        planes.append((Vector((float(n[0]), float(n[1]), float(n[2]))), float(d)))

    phase = rng.uniform(0.0, math.tau, size=6)
    for v in sub.verts:
        p = v.co.copy()
        # Flatten bottom cleanly so boulder embeds solidly into the marble terrace
        if p.z < -0.15:
            p.z = -0.15 + (p.z + 0.15) * 0.20

        # Jagged directional ridge displacement
        r_ang = math.atan2(p.y, p.x)
        ridge = (
            0.18 * math.sin(r_ang * 3.0 + phase[0])
            + 0.12 * math.cos(r_ang * 5.0 + p.z * 3.5 + phase[1])
            + 0.09 * math.sin(p.x * 4.2 - p.y * 3.8 + phase[2])
        )
        # Stepped horizontal sedimentary/granite fracture ledges
        strata = 0.08 * math.sin(p.z * 7.5 + phase[3]) + 0.05 * math.cos(p.x * 5.0 + p.z * 5.0 + phase[4])
        scale_r = 1.0 + ridge + strata
        p.x *= scale_r
        p.y *= scale_r
        p.z = (p.z + 0.18) * (0.95 + 0.20 * abs(math.sin(r_ang * 2.0 + phase[5])))

        # Clip against fracture planes to form sharp natural granite rock faces
        for pn, pd in planes:
            dot = p.dot(pn)
            if dot > pd:
                p -= pn * ((dot - pd) * 0.78)

        # Map local (x, y, z) -> Three.js (center_x + x*rx, max(-0.08, z*height), center_z + y*rz)
        tx = center_x + p.x * radius_x
        ty = max(-0.08, p.z * height)
        tz = center_z + p.y * radius_z
        v.co = three_to_bl(tx, ty, tz)

    # Copy displaced outcrop into target bmesh
    vert_map = {}
    for v in sub.verts:
        vert_map[v.index] = bm.verts.new(v.co)
    for f in sub.faces:
        try:
            bm.faces.new([vert_map[v.index] for v in f.verts])
        except ValueError:
            pass
    sub.free()


# ------------------------------------------------------------------ materials
def _make_materials():
    """Build shared PBR materials for Al-Mas'a."""
    marble_alb, marble_nrm = textures.tex_marble_cream(size=512, name='masa_marble_cream', tiles=4)
    wall_stone = textures.tex_stone_haram(size=512, name='masa_wall_stone', tint='#efe7d9')
    granite_alb, granite_nrm = textures.tex_granite_rock(size=512, name='masa_granite_rock')
    gold_alb, gold_nrm = textures.tex_gold_relief(size=256, name='masa_gold_relief')

    return {
        'marble_floor': make_pbr_material(
            'mat_masa_floor',
            roughness=0.22,
            metallic=0.0,
            image=marble_alb,
            normal_image=marble_nrm,
            normal_strength=0.32,
            use_vcol=False,
        ),
        'marble_inlay': make_pbr_material(
            'mat_masa_inlay',
            color='#b4935c',
            roughness=0.28,
            metallic=0.22,
        ),
        'marble_wall': make_pbr_material(
            'mat_masa_wall',
            roughness=0.42,
            metallic=0.0,
            image=wall_stone,
            use_vcol=True,
        ),
        'marble_column': make_pbr_material(
            'mat_masa_column',
            color='#f3ece0',
            roughness=0.28,
            metallic=0.0,
            image=marble_alb,
            normal_image=marble_nrm,
            normal_strength=0.22,
            use_vcol=True,
        ),
        'marble_niche': make_pbr_material(
            'mat_masa_niche',
            color='#dfd3be',
            roughness=0.48,
            metallic=0.0,
            use_vcol=True,
        ),
        'ceiling': make_pbr_material(
            'mat_masa_ceiling',
            color='#f2ece0',
            roughness=0.58,
            metallic=0.0,
            use_vcol=True,
        ),
        'brass': make_pbr_material(
            'mat_masa_brass',
            color='#cfa246',
            roughness=0.26,
            metallic=0.90,
        ),
        'bronze': make_pbr_material(
            'mat_masa_bronze',
            color='#4d3821',
            roughness=0.32,
            metallic=0.86,
        ),
        'gold_relief': make_pbr_material(
            'mat_masa_gold_relief',
            roughness=0.26,
            metallic=0.90,
            image=gold_alb,
            normal_image=gold_nrm,
            normal_strength=0.65,
        ),
        'chandelier_lamp': make_pbr_material(
            'mat_masa_chandelier_lamp',
            color='#fff4d8',
            roughness=0.18,
            metallic=0.0,
            emissive='#ffda8e',
            emissive_strength=2.8,
        ),
        'green_led': make_pbr_material(
            'mat_masa_green_led',
            color='#08b852',
            roughness=0.18,
            metallic=0.0,
            emissive='#00e85c',
            emissive_strength=3.6,
        ),
        'green_floor': make_pbr_material(
            'mat_masa_green_floor',
            color='#0cc45a',
            roughness=0.15,
            metallic=0.0,
            emissive='#00e05c',
            emissive_strength=0.65,
            alpha=0.14,
            double_sided=False,
        ),
        'granite': make_pbr_material(
            'mat_masa_granite',
            roughness=0.88,
            metallic=0.02,
            image=granite_alb,
            normal_image=granite_nrm,
            normal_strength=0.85,
            use_vcol=True,
        ),
        'qibla_glow': make_pbr_material(
            'mat_masa_qibla_glow',
            color='#ffe098',
            roughness=0.22,
            metallic=0.65,
            emissive='#ffbe44',
            emissive_strength=1.8,
        ),
    }


# ------------------------------------------------------------------ builders
def _build_floor_and_divider(col, mats, lod=0):
    """Veined cream marble floor (20x154 m), inlaid lane edges, and central marble balustrade."""
    objs = []
    # Main polished cream marble floor: x in [-10, 10], z in [-137, 17], top at y=0
    bm_fl = bmesh.new()
    _tbox(bm_fl, -HALF_W, HALF_W, -0.22, 0.0, Z_MIN, Z_MAX)
    fl_obj = bm_to_obj(bm_fl, f'_masa_floor_l{lod}', col, mat=mats['marble_floor'], smooth=False)
    uv_box_project(fl_obj, scale=0.25)
    objs.append(fl_obj)

    # Dark-gold inlaid marble lane border bands (y=0.001..0.009)
    bm_in = bmesh.new()
    for x in (-9.35, -8.75, -1.05, 1.05, 8.75, 9.35):
        w = 0.14 if abs(x) < 2 else 0.18
        _tbox(bm_in, x - w * 0.5, x + w * 0.5, 0.001, 0.009, Z_MIN + 10.0, Z_MAX - 10.0)
    # Transverse gold accent bands marking Safa/Marwa approach thresholds & Green Light lines
    for z in (SAFA_Z + 1.8, -3.0, GREEN[0], GREEN[1], -LEN + 3.0, MARWA_Z - 1.8):
        _tbox(bm_in, -8.75, 8.75, 0.001, 0.009, z - 0.12, z + 0.12)
    in_obj = bm_to_obj(bm_in, f'_masa_inlay_l{lod}', col, mat=mats['marble_inlay'], smooth=False)
    uv_box_project(in_obj, scale=0.5)
    objs.append(in_obj)

    # Sculpted low cream-marble central balustrade: strictly |x| <= 0.6, z in [-117, -3], h=1.05 m
    z0, z1 = -LEN + 3.0, -3.0  # -117.0 .. -3.0
    bm_bal = bmesh.new()
    bm_brz = bmesh.new()
    bm_brs = bmesh.new()

    # Molded base plinth (x in [-0.58, 0.58], y in [0, 0.16])
    _tbox(bm_bal, -0.58, 0.58, 0.0, 0.16, z0, z1)
    # Paneled marble dado core (x in [-0.46, 0.46], y in [0.16, 0.84])
    _tbox(bm_bal, -0.46, 0.46, 0.16, 0.84, z0 + 0.05, z1 - 0.05)
    # Beveled coping cap (x in [-0.55, 0.55], y in [0.84, 0.93])
    _tbox(bm_bal, -0.55, 0.55, 0.84, 0.93, z0, z1)
    # Molded marble pilasters along balustrade every 6 m (12 m on LOD1)
    pil_step = 6.0 if lod == 0 else 12.0
    z = z0
    while z <= z1 + 0.01:
        _tbox(bm_bal, -0.54, 0.54, 0.14, 0.86, z - 0.18, z + 0.18)
        if lod == 0:
            _tbox(bm_brs, -0.56, 0.56, 0.78, 0.82, z - 0.19, z + 0.19)
        z += pil_step
    # Rounded end bollards at z = -3 and z = -117
    for ez in (z0, z1):
        _tcyl(bm_bal, 0.0, 0.0, 0.94, ez, 0.56, 0.52, segs=12 if lod == 0 else 8)
        _tcyl(bm_brs, 0.0, 0.94, 1.06, ez, 0.16, 0.08, segs=10 if lod == 0 else 6)

    # Brushed-bronze top handrail at y=1.02..1.06 supported by short stanchions
    _tbox(bm_brz, -0.05, 0.05, 1.01, 1.06, z0 + 0.1, z1 - 0.1)
    post_step = 3.0 if lod == 0 else 9.0
    z = z0 + 1.5
    while z < z1 - 0.5:
        _tcyl(bm_brz, 0.0, 0.93, 1.03, z, 0.032, 0.032, segs=6)
        z += post_step

    for bm, name, mat, smooth, uv_s, ao in (
        (bm_bal, f'_masa_balustrade_l{lod}', mats['marble_column'], False, 0.45, True),
        (bm_brz, f'_masa_bal_bronze_l{lod}', mats['bronze'], True, 0.5, False),
        (bm_brs, f'_masa_bal_brass_l{lod}', mats['brass'], True, 0.5, False),
    ):
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_box_project(obj, scale=uv_s)
        if ao:
            bake_vertex_ao(obj, strength=0.24, min_val=0.66)
        objs.append(obj)
    return objs


def _build_walls_and_ceiling(col, mats, lod=0):
    """Tall veined marble side walls (x=+-10.25), recessed arched niches, end walls & coffered ceiling."""
    objs = []
    bm_wall = bmesh.new()
    bm_niche = bmesh.new()
    bm_trim = bmesh.new()
    bm_ceil = bmesh.new()
    bm_gold = bmesh.new()

    # Main side walls at x = +-10.25 (inner face at +-10.0), h=12.2 m, full=154 m
    for side in (-1.0, 1.0):
        x_in = side * HALF_W
        x_out = side * (HALF_W + 0.5)
        xa, xb = (x_in, x_out) if x_in < x_out else (x_out, x_in)
        _tbox(bm_wall, xa, xb, 0.0, 12.2, Z_MIN, Z_MAX)
        # Warm cream marble wainscoting dado (y=0..2.25) with molded top rail
        wx_in = x_in - side * 0.14
        wxa, wxb = (wx_in, x_in) if wx_in < x_in else (x_in, wx_in)
        _tbox(bm_trim, wxa, wxb, 0.0, 2.20, Z_MIN, Z_MAX)
        _tbox(bm_gold, wxa - (0.03 if side > 0 else 0.0), wxb + (0.03 if side < 0 else 0.0), 2.18, 2.28, Z_MIN, Z_MAX)
        # Upper cornice frieze along ceiling junction (y=11.35..12.2)
        fx_in = x_in - side * 0.22
        fxa, fxb = (fx_in, x_in) if fx_in < x_in else (x_in, fx_in)
        _tbox(bm_trim, fxa, fxb, 11.45, 12.20, Z_MIN, Z_MAX)
        _tbox(bm_gold, fxa, fxb, 11.36, 11.46, Z_MIN, Z_MAX)

        # Rhythmic recessed pointed arched architectural bays between columns (z midpoints)
        col_zs = [8.0 - 9.0 * i for i in range(16)]
        for i in range(len(col_zs) - 1):
            zm = 0.5 * (col_zs[i] + col_zs[i + 1])
            # Recessed niche backing panel slightly proud of wall for crisp shadow relief
            nx_in = x_in - side * 0.06
            nxa, nxb = (nx_in, x_in) if nx_in < x_in else (x_in, nx_in)
            _tbox(bm_niche, nxa, nxb, 2.35, 8.65, zm - 2.6, zm + 2.6)
            # Side piers of the arched bay
            px_in = x_in - side * 0.22
            pxa, pxb = (px_in, x_in) if px_in < x_in else (x_in, px_in)
            _tbox(bm_trim, pxa, pxb, 2.25, 6.85, zm - 2.85, zm - 2.55)
            _tbox(bm_trim, pxa, pxb, 2.25, 6.85, zm + 2.55, zm + 2.85)
            if lod == 0:
                _add_wall_pointed_niche_arch(bm_trim, x_in, side, zm, 6.80, 5.1, 2.2, 0.26, 0.24, segs=5)
            else:
                _tbox(bm_trim, pxa, pxb, 8.55, 8.95, zm - 2.85, zm + 2.85)

    # Grand end walls closing the gallery behind As-Safa (z=+17.0) and Al-Marwa (z=-137.0)
    for ez, inward in ((Z_MAX, -1.0), (Z_MIN, 1.0)):
        za, zb = (ez, ez + 0.6) if inward < 0 else (ez - 0.6, ez)
        _tbox(bm_wall, -HALF_W - 0.5, HALF_W + 0.5, 0.0, 12.4, za, zb)
        # Decorative monumental arched apse niche centered on end wall behind hill
        nza, nzb = (ez + inward * 0.28, ez) if inward < 0 else (ez, ez + inward * 0.28)
        _tbox(bm_trim, -6.4, -5.6, 0.0, 7.6, nza, nzb)
        _tbox(bm_trim, 5.6, 6.4, 0.0, 7.6, nza, nzb)
        _tbox(bm_niche, -5.6, 5.6, 0.0, 10.2, ez + inward * 0.08 if inward < 0 else ez, ez if inward < 0 else ez + inward * 0.08)
        _add_transverse_pointed_arch(bm_trim, ez + inward * 0.22, 5.8, 7.2, 10.8, 0.45, 0.36, segs=6 if lod == 0 else 4)
        _tbox(bm_gold, -9.8, 9.8, 11.35, 11.50, ez + inward * 0.24 if inward < 0 else ez, ez if inward < 0 else ez + inward * 0.24)

    # Coffered ceiling slab (y=12.2..12.65) + longitudinal architectural beams + transverse ribs
    _tbox(bm_ceil, -HALF_W - 0.5, HALF_W + 0.5, 12.20, 12.65, Z_MIN - 0.5, Z_MAX + 0.5)
    for bx in (-5.0, 0.0, 5.0):
        _tbox(bm_ceil, bx - 0.28, bx + 0.28, 11.88, 12.22, Z_MIN, Z_MAX)
    rib_step = 4.5 if lod == 0 else 9.0
    z = 12.5
    while z >= Z_MIN + 2.0:
        _tbox(bm_ceil, -HALF_W, HALF_W, 11.92, 12.22, z - 0.22, z + 0.22)
        z -= rib_step

    parts = [
        (bm_wall, f'_masa_wall_l{lod}', mats['marble_wall'], False, 0.22, True),
        (bm_niche, f'_masa_niche_l{lod}', mats['marble_niche'], False, 0.28, True),
        (bm_trim, f'_masa_wall_trim_l{lod}', mats['marble_column'], False, 0.30, True),
        (bm_ceil, f'_masa_ceiling_l{lod}', mats['ceiling'], False, 0.20, True),
        (bm_gold, f'_masa_wall_gold_l{lod}', mats['brass'], False, 0.5, False),
    ]
    for bm, name, mat, smooth, uv_s, ao in parts:
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_box_project(obj, scale=uv_s)
        if ao:
            bake_vertex_ao(obj, strength=0.22, min_val=0.68)
        objs.append(obj)
    return objs


def _build_colonnade_and_arches(col, mats, lod=0):
    """Fluted marble columns (x=+-9.2, every 9 m from z=8 to -128), gilded capitals & pointed arches."""
    objs = []
    bm_col = bmesh.new()
    bm_cap = bmesh.new()
    bm_arch = bmesh.new()

    zs = [8.0 - 9.0 * i for i in range(16)]  # 8, -1, -10, ..., -127
    col_x = HALF_W - 0.8  # 9.2
    arch_segs = 8 if lod == 0 else 4
    c_segs = 12 if lod == 0 else 6

    for z in zs:
        for cx in (-col_x, col_x):
            # Stepped square marble plinth (stays cleanly outside walkable |x| <= 8.12)
            _tbox(bm_col, cx - 0.76, cx + 0.76, 0.0, 0.42, z - 0.76, z + 0.76)
            _tcyl(bm_col, cx, 0.42, 0.68, z, 0.76, 0.68, segs=c_segs)
            _tcyl(bm_cap, cx, 0.66, 0.76, z, 0.70, 0.70, segs=c_segs)
            # Fluted marble shaft (y=0.76..10.85)
            if lod == 0:
                _add_fluted_column(bm_col, cx, 0.76, 10.85, z, 0.64, flutes=8)
            else:
                _tcyl(bm_col, cx, 0.76, 10.85, z, 0.64, 0.64, segs=6)
            # Sculpted gilded capital (y=10.85..11.80)
            _tcyl(bm_cap, cx, 10.85, 11.02, z, 0.70, 0.72, segs=c_segs)
            _tcyl(bm_cap, cx, 11.02, 11.58, z, 0.68, 0.92, segs=c_segs)
            _tbox(bm_col, cx - 0.92, cx + 0.92, 11.58, 11.95, z - 0.92, z + 0.92)

        # Graceful transverse pointed Islamic arch spanning ceiling (intrados >= 9.0 m, apex 11.92 m)
        _add_transverse_pointed_arch(bm_arch, z, half_span=col_x - 0.35, y_spring=9.05, y_apex=11.90, thick_y=0.38, depth_z=0.52, segs=arch_segs)

    for bm, name, mat, smooth, uv_s, ao in (
        (bm_col, f'_masa_cols_l{lod}', mats['marble_column'], True, 0.35, True),
        (bm_cap, f'_masa_caps_l{lod}', mats['brass'], True, 0.5, False),
        (bm_arch, f'_masa_arches_l{lod}', mats['marble_wall'], False, 0.28, True),
    ):
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_box_project(obj, scale=uv_s)
        if ao:
            bake_vertex_ao(obj, strength=0.22, min_val=0.68)
        objs.append(obj)
    return objs


def _build_chandeliers(col, mats, lod=0):
    """24 ornate brass Islamic chandeliers at x=+-5.0, every 12 m from z=6 to -126, y=10.4 m."""
    objs = []
    bm_brass = bmesh.new()
    bm_lamp = bmesh.new()

    zs = [6.0 - 12.0 * i for i in range(12)]  # 6, -6, -18, ..., -126
    ring_segs = 10 if lod == 0 else 6

    for cz in zs:
        for cx in (-5.0, 5.0):
            # Ceiling rose & vertical suspension rod from ceiling y=12.2 down to y=10.35
            _tcyl(bm_brass, cx, 12.05, 12.22, cz, 0.24, 0.16, segs=ring_segs)
            _tcyl(bm_brass, cx, 10.05, 12.08, cz, 0.035, 0.035, segs=5)
            # Central tiered brass body & bottom finial drop
            _tcyl(bm_brass, cx, 10.12, 10.62, cz, 0.14, 0.22, segs=ring_segs)
            if lod == 0:
                _tcyl(bm_brass, cx, 9.78, 10.12, cz, 0.02, 0.14, segs=6)
                _tcyl(bm_brass, cx, 10.68, 10.78, cz, 0.38, 0.38, segs=ring_segs, cap_ends=False)
            # Main gilded ring hoop at y=10.35 (r=0.62)
            _tcyl(bm_brass, cx, 10.30, 10.44, cz, 0.62, 0.62, segs=ring_segs, cap_ends=False)
            # Central warm glowing diffuser globe
            _tsphere(bm_lamp, cx, 10.22, cz, 0.24, segs=8 if lod == 0 else 5, rings=5 if lod == 0 else 4)

            if lod == 0:
                # 6 delicate outer lantern globes & radial brass arms around the main ring
                for k in range(6):
                    ang = k * (math.tau / 6.0)
                    lx = cx + math.cos(ang) * 0.60
                    lz = cz + math.sin(ang) * 0.60
                    # Radial spoke from center to outer ring
                    mx = cx + math.cos(ang) * 0.30
                    mz = cz + math.sin(ang) * 0.30
                    add_box(bm_brass, three_to_bl(mx, 10.37, mz), (0.58, 0.035, 0.035), rot_z=-ang)
                    # Warm glowing lantern cup
                    _tcyl(bm_lamp, lx, 10.36, 10.64, lz, 0.075, 0.10, segs=6)

    for bm, name, mat in (
        (bm_brass, f'_masa_ch_brass_l{lod}', mats['brass']),
        (bm_lamp, f'_masa_ch_lamp_l{lod}', mats['chandelier_lamp']),
    ):
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=True)
        uv_cylindrical(obj, scale_u=1.0, scale_v=1.0)
        objs.append(obj)
    return objs


def _build_green_lights(col, mats, lod=0):
    """Unmistakable Al-Milayn al-Akhdarayn emerald LED beams, column wraps & floor wash (z in [-38, -55])."""
    objs = []
    bm_led = bmesh.new()
    bm_housing = bmesh.new()
    bm_floor = bmesh.new()

    g0, g1 = GREEN  # -38.0, -55.0
    col_x = HALF_W - 0.8  # 9.2
    cyl_segs = 14 if lod == 0 else 8

    for gz in (g0, g1):
        # Prominent glowing emerald overhead transverse light beam across gallery at y=11.6 m
        _tbox(bm_housing, -col_x - 0.2, col_x + 0.2, 11.72, 11.96, gz - 0.52, gz + 0.52)
        _tbox(bm_led, -col_x, col_x, 11.38, 11.74, gz - 0.44, gz + 0.44)
        # Glowing emerald vertical LED wrap bands on side columns at z=-38 and z=-55 (x=+-9.2, y in [7.0, 10.2])
        for gx in (-col_x, col_x):
            _tcyl(bm_housing, gx, 6.88, 7.04, gz, 0.80, 0.80, segs=cyl_segs)
            _tcyl(bm_led, gx, 7.02, 10.22, gz, 0.75, 0.75, segs=cyl_segs)
            _tcyl(bm_housing, gx, 10.20, 10.36, gz, 0.80, 0.80, segs=cyl_segs)

    # Continuous longitudinal glowing green ceiling strips along x=+-5.0 spanning z in [-38, -55]
    for lx in (-5.0, 5.0):
        _tbox(bm_housing, lx - 0.30, lx + 0.30, 11.95, 12.15, g1 - 0.2, g0 + 0.2)
        _tbox(bm_led, lx - 0.24, lx + 0.24, 11.78, 11.96, g1, g0)

    # Soft translucent emerald floor reflection strip (y=0.02, alpha=0.14) spanning z in [-38, -55]
    v0 = bm_floor.verts.new(three_to_bl(-9.4, 0.02, g0))
    v1 = bm_floor.verts.new(three_to_bl(9.4, 0.02, g0))
    v2 = bm_floor.verts.new(three_to_bl(9.4, 0.02, g1))
    v3 = bm_floor.verts.new(three_to_bl(-9.4, 0.02, g1))
    bm_floor.faces.new((v0, v1, v2, v3))

    for bm, name, mat, smooth in (
        (bm_led, f'_masa_green_led_l{lod}', mats['green_led'], True),
        (bm_housing, f'_masa_green_house_l{lod}', mats['bronze'], False),
        (bm_floor, f'_masa_green_floor_l{lod}', mats['green_floor'], False),
    ):
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_box_project(obj, scale=0.35)
        objs.append(obj)
    return objs


def _build_hills_and_qibla(col, mats, lod=0):
    """Authentic jagged Hijazi granite Safa & Marwa hills, curved marble/brass railings & Qibla plaques."""
    objs = []
    bm_rock = bmesh.new()
    bm_wall = bmesh.new()
    bm_brass = bmesh.new()
    bm_bronze = bmesh.new()
    bm_qibla = bmesh.new()
    bm_qglow = bmesh.new()

    # Hills configuration:
    # - As-Safa: player stops at z <= SAFA_Z + 7 = +8.5; back wall at z = +17.0.
    #   Semicircular retaining wall of radius 8.0 m centered at z_arc = +16.8 curves outward (-z)
    #   to apex z = +8.8 (just 0.3 m beyond player collision limit!), enclosing granite rocks at z ~ +10.0..+16.5.
    # - Al-Marwa: player stops at z >= MARWA_Z - 7 = -128.5; back wall at z = -137.0.
    #   Semicircular retaining wall of radius 8.0 m centered at z_arc = -136.8 curves outward (+z)
    #   to apex z = -128.8, enclosing granite rocks at z ~ -130.0..-136.5.
    hill_specs = [
        # (z_arc, face_dir, seed_base)
        # face_dir = -1 for As-Safa (faces -z toward corridor), +1 for Al-Marwa (faces +z)
        (16.8, -1.0, 4100),
        (-136.8, 1.0, 5200),
    ]

    arc_segs = 20 if lod == 0 else 12
    subdiv = 2 if lod == 0 else 1
    r_arc = 8.0

    for z_arc, face_dir, seed_base in hill_specs:
        # 1. Fractured layered Hijazi granite rock outcrop cluster rising ~2.2..2.8 m
        #    Distributed inside the semicircular retaining wall so rocks stay strictly behind the curved wall
        boulders = [
            # (x, dz_from_arc, rx, rz, h)  where actual z = z_arc + face_dir * dz
            (0.0, 2.2, 3.6, 2.6, 2.75),     # central tall summit crag
            (-3.2, 2.4, 2.8, 2.3, 2.35),    # left upper shoulder
            (3.1, 2.5, 2.9, 2.2, 2.45),     # right upper shoulder
            (-5.4, 1.8, 2.2, 1.9, 1.75),    # far left flank
            (5.3, 1.9, 2.2, 1.8, 1.85),     # far right flank
            (-1.5, 4.5, 2.6, 2.1, 1.70),    # mid-front fractured ledge left
            (1.7, 4.4, 2.5, 2.0, 1.65),     # mid-front fractured ledge right
            (0.1, 6.0, 2.3, 1.5, 1.15),     # front toe granite outcrop near railing
            (-3.8, 4.6, 1.9, 1.6, 1.25),    # lower front-left boulder
            (3.9, 4.5, 1.9, 1.6, 1.20),     # lower front-right boulder
        ]
        if lod == 1:
            boulders = boulders[:7]
        for idx, (bx, dz, rx, rz, bh) in enumerate(boulders):
            _add_granite_outcrop(
                bm_rock,
                center_x=bx,
                center_z=z_arc + face_dir * dz,
                radius_x=rx,
                radius_z=rz,
                height=bh,
                seed=seed_base + idx * 19,
                subdiv=subdiv,
            )

        # 2. Curved cream-marble low retaining wall (r=8.0 m, h=0.72 m, thickness 0.42 m)
        r_in = r_arc - 0.22
        r_out = r_arc + 0.20
        rings_wall = []
        rings_cope = []
        rail_pts_low = []
        rail_pts_hi = []
        for i in range(arc_segs + 1):
            t = i / arc_segs
            ang = t * math.pi  # 0 (x=+r) -> pi/2 (apex along face_dir) -> pi (x=-r)
            cx_u = math.cos(ang)
            cz_u = math.sin(ang) * face_dir
            # Wall cross-section (4 corners: bottom-in, top-in, top-out, bottom-out)
            v0 = bm_wall.verts.new(three_to_bl(cx_u * r_in, 0.0, z_arc + cz_u * r_in))
            v1 = bm_wall.verts.new(three_to_bl(cx_u * r_in, 0.66, z_arc + cz_u * r_in))
            v2 = bm_wall.verts.new(three_to_bl(cx_u * r_out, 0.66, z_arc + cz_u * r_out))
            v3 = bm_wall.verts.new(three_to_bl(cx_u * r_out, 0.0, z_arc + cz_u * r_out))
            rings_wall.append([v0, v1, v2, v3])

            # Beveled marble coping cap (slightly wider overhang, y=0.66..0.76)
            c0 = bm_wall.verts.new(three_to_bl(cx_u * (r_in - 0.05), 0.66, z_arc + cz_u * (r_in - 0.05)))
            c1 = bm_wall.verts.new(three_to_bl(cx_u * (r_in - 0.03), 0.76, z_arc + cz_u * (r_in - 0.03)))
            c2 = bm_wall.verts.new(three_to_bl(cx_u * (r_out + 0.03), 0.76, z_arc + cz_u * (r_out + 0.03)))
            c3 = bm_wall.verts.new(three_to_bl(cx_u * (r_out + 0.05), 0.66, z_arc + cz_u * (r_out + 0.05)))
            rings_cope.append([c0, c1, c2, c3])

            rail_pts_low.append(three_to_bl(cx_u * r_arc, 0.96, z_arc + cz_u * r_arc))
            rail_pts_hi.append(three_to_bl(cx_u * r_arc, 1.18, z_arc + cz_u * r_arc))

            # Vertical brushed-brass stanchions along the curved parapet
            if i % (2 if lod == 0 else 3) == 0 or i == arc_segs:
                _tcyl(bm_brass, cx_u * r_arc, 0.75, 1.20, z_arc + cz_u * r_arc, 0.032, 0.028, segs=6)

        loft_rings(bm_wall, rings_wall, closed_u=True, cap_start=True, cap_end=True)
        loft_rings(bm_wall, rings_cope, closed_u=True, cap_start=True, cap_end=True)
        # Curved twin brushed-brass protective railings atop the retaining wall
        add_tube(bm_brass, rail_pts_hi, 0.042, segs=6 if lod == 0 else 5, closed_caps=True)
        add_tube(bm_brass, rail_pts_low, 0.026, segs=6 if lod == 0 else 4, closed_caps=True)

        # 3. Marble approach apron leading smoothly up to each hill (flat safe y=0.025..0.035)
        z_apron_near = z_arc + face_dir * 7.8
        z_apron_far = z_arc + face_dir * 13.8
        za, zb = min(z_apron_near, z_apron_far), max(z_apron_near, z_apron_far)
        _tbox(bm_wall, -HALF_W + 0.1, HALF_W - 0.1, 0.0, 0.028, za, zb)
        # Brass threshold step strip along the outer apron edge
        _tbox(bm_brass, -HALF_W + 0.2, HALF_W - 0.2, 0.005, 0.034, z_apron_far - 0.10, z_apron_far + 0.10)

    # 4. Sculpted gilded Qibla directional pointer plaques on West wall (x=-9.75, y=4.0)
    #    Placed at z = SAFA_Z + 3 (+4.5) and z = MARWA_Z - 3 (-124.5), pointing toward Kaaba (-X / West)
    for qz in (SAFA_Z + 3.0, MARWA_Z - 3.0):
        # Ornate dark-bronze wall mounting medallion on West wall (x=-9.98..-9.86)
        mat_med = Matrix.Translation(three_to_bl(-9.92, 4.0, qz)) @ Matrix.Rotation(math.pi * 0.5, 4, 'Y')
        bmesh.ops.create_cone(
            bm_bronze,
            cap_ends=True,
            cap_tris=False,
            segments=8,
            radius1=0.92,
            radius2=0.88,
            depth=0.12,
            matrix=mat_med,
        )
        # Sculpted gilded inner decorative plaque ring
        mat_plq = Matrix.Translation(three_to_bl(-9.84, 4.0, qz)) @ Matrix.Rotation(math.pi * 0.5, 4, 'Y')
        bmesh.ops.create_cone(
            bm_qibla,
            cap_ends=True,
            cap_tris=False,
            segments=8,
            radius1=0.76,
            radius2=0.72,
            depth=0.08,
            matrix=mat_plq,
        )
        # Prominent glowing gilded 3D pointer cone/arrow centered at (-9.60, 4.0, qz) pointing West (-X)
        # Rotate cone -90 deg around Y so local +Z apex points along Blender -X (Three.js -X / West)
        mat_arr = Matrix.Translation(three_to_bl(-9.52, 4.0, qz)) @ Matrix.Rotation(-math.pi * 0.5, 4, 'Y')
        bmesh.ops.create_cone(
            bm_qglow,
            cap_ends=True,
            cap_tris=False,
            segments=4,
            radius1=0.38,
            radius2=0.02,
            depth=0.72,
            matrix=mat_arr,
        )
        # Bracket arm connecting glowing pointer cleanly to the wall medallion
        _tbox(bm_brass, -9.86, -9.20, 3.92, 4.08, qz - 0.08, qz + 0.08)

    parts = [
        (bm_rock, f'_masa_rock_l{lod}', mats['granite'], False, 0.32, True),
        (bm_wall, f'_masa_hill_wall_l{lod}', mats['marble_column'], False, 0.35, True),
        (bm_brass, f'_masa_hill_brass_l{lod}', mats['brass'], True, 0.5, False),
        (bm_bronze, f'_masa_qibla_bronze_l{lod}', mats['bronze'], False, 0.5, False),
        (bm_qibla, f'_masa_qibla_gold_l{lod}', mats['gold_relief'], False, 0.5, False),
        (bm_qglow, f'_masa_qibla_glow_l{lod}', mats['qibla_glow'], False, 0.5, False),
    ]
    for bm, name, mat, smooth, uv_s, ao in parts:
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_box_project(obj, scale=uv_s)
        if ao:
            bake_vertex_ao(obj, strength=0.30, min_val=0.58)
        objs.append(obj)
    return objs


def _build_lod(col, mats, lod):
    """Build either LOD0 or LOD1 as one cleanly joined multi-material mesh."""
    parts = []
    parts.extend(_build_floor_and_divider(col, mats, lod=lod))
    parts.extend(_build_walls_and_ceiling(col, mats, lod=lod))
    parts.extend(_build_colonnade_and_arches(col, mats, lod=lod))
    parts.extend(_build_chandeliers(col, mats, lod=lod))
    parts.extend(_build_green_lights(col, mats, lod=lod))
    parts.extend(_build_hills_and_qibla(col, mats, lod=lod))
    return join_objects(parts, f'masa_LOD{lod}', col=col)


# ------------------------------------------------------------------ interior preview helper
def _add_preview_interior_lights():
    """Add temporary warm & emerald interior preview lights (never exported to GLB)."""
    sc = bpy.context.scene
    col = bpy.data.collections.get('_PreviewRig')
    if col is None:
        col = bpy.data.collections.new('_PreviewRig')
        sc.collection.children.link(col)

    def _pt(name, pos_three, energy, color, radius=1.5):
        ld = bpy.data.lights.new(name, type='POINT')
        ld.energy = energy
        ld.color = color
        ld.shadow_soft_size = radius
        ld.use_shadow = False
        ob = bpy.data.objects.new(name, ld)
        ob.location = three_to_bl(*pos_three)
        col.objects.link(ob)

    # Warm gallery illumination along corridor and over As-Safa hill
    for z in (10.0, 2.0, -10.0, -24.0, -34.0, -60.0, -76.0):
        _pt(f'_MasaWarm_{int(z)}', (0.0, 8.8, z), energy=4200.0, color=(1.0, 0.93, 0.80), radius=2.2)
    # Bright emerald interior bounce lights inside the Green Lights stretch
    for z in (-39.0, -46.5, -54.0):
        _pt(f'_MasaGreen_{int(z)}', (0.0, 9.2, z), energy=4800.0, color=(0.06, 1.0, 0.36), radius=2.0)


def _render_masa_preview(out_path):
    """Render a crisp 2-panel interior inspection PNG: Green Lights gallery + As-Safa granite hill."""
    sc = bpy.context.scene
    _add_preview_interior_lights()
    views = [
        # Left panel: looking down the Mas'a gallery toward the Green Lights (z=-38..-55)
        (three_to_bl(-4.8, 3.8, -16.0), three_to_bl(0.2, 4.4, -52.0), 26),
        # Right panel: hero view of As-Safa granite hill, curved marble/brass railing & West Qibla plaque
        (three_to_bl(5.4, 3.3, -5.5), three_to_bl(-2.2, 2.4, 9.8), 23),
    ]
    tiles = []
    tmp_files = []
    try:
        preview._ensure_preview_world(sc, world_color=(0.88, 0.85, 0.78))
        preview._configure_render(sc, res=(640, 520))
        if hasattr(sc, 'eevee') and hasattr(sc.eevee, 'use_shadows'):
            # Disable exterior sun shadow maps inside the 154 m enclosed gallery to avoid shadow-pool overflow
            sc.eevee.use_shadows = False
        for idx, (eye, target, lens) in enumerate(views):
            with tempfile.NamedTemporaryFile(suffix=f'_masa_{idx}.png', delete=False) as tf:
                tmp_png = tf.name
            tmp_files.append(tmp_png)
            preview._ensure_preview_camera(sc, eye=eye, target=target, lens=lens)
            sc.render.filepath = str(tmp_png)
            bpy.context.view_layer.update()
            bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(tmp_png, check_existing=False)
            w, h = img.size[0], img.size[1]
            arr = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(arr)
            tiles.append(arr.reshape((h, w, 4)))
            bpy.data.images.remove(img)

        sheet = np.concatenate(tiles, axis=1)
        sh, sw = sheet.shape[:2]
        out_img = bpy.data.images.new('_MasaPreviewSheet', sw, sh, alpha=True)
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


# ------------------------------------------------------------------ public API
def build_masa(col):
    """Build `masa_LOD0` and `masa_LOD1` into `col` and return (lod0, lod1)."""
    mats = _make_materials()
    lod0 = _build_lod(col, mats, lod=0)
    lod1 = _build_lod(col, mats, lod=1)
    return lod0, lod1


def export_masa():
    """Reset scene, build Mas'a LOD0/LOD1, export Draco WebP GLB & render 2-panel preview PNG."""
    ensure_dirs()
    reset_scene()
    col = make_collection('EnvMasa')

    lod0, lod1 = build_masa(col)
    tris0 = tri_count(lod0)
    tris1 = tri_count(lod1)

    size_bytes = export_glb([lod0, lod1], OUT_GLB, animations=False, vertex_colors=True)
    size_kb = round(size_bytes / 1024.0, 1)

    lod1.hide_render = True
    _render_masa_preview(OUT_PREVIEW)

    stats = {
        'key': 'masa',
        'glb': str(OUT_GLB.relative_to(ROOT)),
        'preview': str(OUT_PREVIEW.relative_to(ROOT)),
        'tris_lod0': tris0,
        'tris_lod1': tris1,
        'budget_lod0': BUDGET_LOD0_TRIS,
        'budget_lod1': BUDGET_LOD1_TRIS,
        'size_kb': size_kb,
        'budget_kb': BUDGET_KB,
        'within_budget': (
            tris0 <= BUDGET_LOD0_TRIS
            and tris1 <= BUDGET_LOD1_TRIS
            and size_kb <= BUDGET_KB
        ),
    }
    print(
        f"MASA_OK tris0={tris0}/{BUDGET_LOD0_TRIS} tris1={tris1}/{BUDGET_LOD1_TRIS} "
        f"size={size_kb:.1f}/{BUDGET_KB}KB"
    )
    return stats


if __name__ == '__main__':
    export_masa()
