"""Al-Masjid al-Haram Mataf Courtyard, Multi-Tiered Colonnade & 6 Hijazi Minarets.

Generates `public/models/env/haram_mataf.glb` (containing `haram_mataf_LOD0` and
`haram_mataf_LOD1`) matching `src/game/mataf.js` (`MATAF_R = 45.0 m`, `colR = 48.0 m`,
6 minarets at `r = 64.0 m`, Green Line Marker Lamp at world `(47.3, 5.0, 0)`), and
renders a panoramic preview to `blender/previews/env_haram_mataf.png`.
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

# ------------------------------------------------------------------ exact mataf.js constants
MATAF_R = 45.0
COL_R = 48.0          # MATAF_R + 3
FLOOR_R = 53.5        # Mataf marble floor radius
OUTER_WALL_R = 59.5   # Recessed outer arcade wall
MINARET_R = 64.0      # colR + 16
MINARET_H = 44.0
GREEN_LAMP_WORLD = (47.3, 5.0, 0.0)  # Three.js world (x, y, z) facing Black Stone


def _make_materials():
    thassos_alb, thassos_nrm = textures.tex_marble_white(size=1024, name='tex_haram_thassos', tiles=4)
    cream_alb, cream_nrm = textures.tex_marble_cream(size=512, name='tex_haram_marble_cream', tiles=4)
    stone_alb = textures.tex_stone_haram(size=512, name='tex_haram_stone', tint='#ece4d5')

    return {
        'thassos': common.make_pbr_material(
            'mat_haram_thassos',
            color='#f3f4f6',
            roughness=0.22,
            metallic=0.0,
            image=thassos_alb,
            normal_image=thassos_nrm,
            normal_strength=0.28,
            use_vcol=False,
        ),
        'guide_inlay': common.make_pbr_material(
            'mat_haram_guide_inlay',
            color='#dcd1ba',
            roughness=0.28,
            metallic=0.04,
            use_vcol=False,
        ),
        'marble_col': common.make_pbr_material(
            'mat_haram_marble_col',
            color='#efe7d8',
            roughness=0.28,
            metallic=0.0,
            image=cream_alb,
            normal_image=cream_nrm,
            normal_strength=0.30,
            use_vcol=True,
        ),
        'stone': common.make_pbr_material(
            'mat_haram_stone',
            color='#ece4d5',
            roughness=0.52,
            metallic=0.0,
            image=stone_alb,
            use_vcol=True,
        ),
        'stone_warm': common.make_pbr_material(
            'mat_haram_stone_warm',
            color='#dfd3be',
            roughness=0.58,
            metallic=0.0,
            image=stone_alb,
            use_vcol=True,
        ),
        'gold': common.make_pbr_material(
            'mat_haram_gold',
            color='#dfb54e',
            roughness=0.24,
            metallic=0.88,
            use_vcol=False,
        ),
        'bronze': common.make_pbr_material(
            'mat_haram_bronze',
            color='#695027',
            roughness=0.38,
            metallic=0.78,
            use_vcol=False,
        ),
        'window_dark': common.make_pbr_material(
            'mat_haram_window_dark',
            color='#26231e',
            roughness=0.45,
            metallic=0.10,
            use_vcol=False,
        ),
        'lantern_glow': common.make_pbr_material(
            'mat_haram_lantern_glow',
            color='#fff0cc',
            roughness=0.18,
            metallic=0.0,
            emissive='#ffcf86',
            emissive_strength=2.2,
            use_vcol=False,
        ),
        'green_led': common.make_pbr_material(
            'mat_haram_green_led',
            color='#26e07a',
            roughness=0.18,
            metallic=0.0,
            emissive='#18e070',
            emissive_strength=2.8,
            use_vcol=False,
        ),
    }


def _pointed_arch_norm(s):
    """Two-center pointed Islamic arch height in [0, 1] for symmetric parameter s in [0, 1]."""
    # s = 0 at pointed crown, s = 1 at springline
    val = max(0.0, 1.0 - ((s + 0.35) / 1.35) ** 2)
    return math.sqrt(val) / 0.965828


def _add_ring_band(bm, r_in, r_out, z0, z1, segs):
    """Add a closed cylindrical annular ring band (r_in..r_out, z0..z1) with outward normals."""
    rings = []
    for rad, z in ((r_in, z0), (r_out, z0), (r_out, z1), (r_in, z1)):
        ring = []
        for i in range(segs):
            q = i / segs * math.tau
            ring.append(bm.verts.new((math.cos(q) * rad, math.sin(q) * rad, z)))
        rings.append(ring)
    # Connect 4 profile edges around the ring
    for p in range(4):
        r0 = rings[p]
        r1 = rings[(p + 1) % 4]
        for i in range(segs):
            inext = (i + 1) % segs
            bm.faces.new((r0[i], r0[inext], r1[inext], r1[i]))


def _add_pointed_arch_bay(bm, q0, q1, r_in, r_out, z_spring, z_apex, z_top, arch_segs=8, pad_u=0.09):
    """Add one closed curved pointed Islamic arch spandrel block spanning angles [q0, q1]."""
    # Sample u across the bay (from pad_u to 1 - pad_u so piers stay solid)
    us = [pad_u + (1.0 - 2.0 * pad_u) * (k / arch_segs) for k in range(arch_segs + 1)]
    # Add outer pier wings at u = 0 and u = 1 down to z_spring so bays stitch cleanly into columns
    full_u = [0.0] + us + [1.0]
    full_z_bot = [z_spring]
    for k in range(arch_segs + 1):
        u_local = k / arch_segs
        s = abs(2.0 * u_local - 1.0)
        full_z_bot.append(z_spring + (z_apex - z_spring) * _pointed_arch_norm(s))
    full_z_bot.append(z_spring)

    # Create 4-vertex cross-section slices along the bay and loft them as a closed manifold
    slices = []
    for u, zb in zip(full_u, full_z_bot):
        q = q0 + (q1 - q0) * u
        cq, sq = math.cos(q), math.sin(q)
        # 4 corners: inner-bot, outer-bot, outer-top, inner-top
        slices.append([
            bm.verts.new((cq * r_in, sq * r_in, zb)),
            bm.verts.new((cq * r_out, sq * r_out, zb)),
            bm.verts.new((cq * r_out, sq * r_out, z_top)),
            bm.verts.new((cq * r_in, sq * r_in, z_top)),
        ])

    common.loft_rings(bm, slices, closed_u=True, cap_start=True, cap_end=True)


def _build_floor_and_rings(col, mats, lod='lod0'):
    """Cool white Thassos marble circular floor (r = 53.5 m) + subtle inlaid guide rings."""
    segs = 64 if lod == 'lod0' else 24
    radii = [0.0, 12.0, 22.0, 32.0, 42.0, FLOOR_R] if lod == 'lod0' else [0.0, 26.0, FLOOR_R]

    bm_fl = bmesh.new()
    uv_f = bm_fl.loops.layers.uv.new('UVMap')
    uv_scale = 1.0 / 6.0  # 1.5 m realistic Thassos marble slabs (4 tiles per 6 m)

    c_v = bm_fl.verts.new((0.0, 0.0, 0.0))
    rings = []
    for r in radii[1:]:
        ring = []
        for i in range(segs):
            q = i / segs * math.tau
            ring.append(bm_fl.verts.new((math.cos(q) * r, math.sin(q) * r, 0.0)))
        rings.append(ring)

    # Inner fan
    for i in range(segs):
        inext = (i + 1) % segs
        f = bm_fl.faces.new((c_v, rings[0][i], rings[0][inext]))
        for lp in f.loops:
            lp[uv_f].uv = (lp.vert.co.x * uv_scale, lp.vert.co.y * uv_scale)
    # Outer annular rings
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(segs):
            inext = (i + 1) % segs
            f = bm_fl.faces.new((r0[i], r1[i], r1[inext], r0[inext]))
            for lp in f.loops:
                lp[uv_f].uv = (lp.vert.co.x * uv_scale, lp.vert.co.y * uv_scale)

    floor_obj = common.bm_to_obj(bm_fl, f'haram_mataf_floor_{lod}', col, mat=mats['thassos'], smooth=False)

    # Subtle concentric inlaid pale-gold travertine/marble guide rings at r = 16, 26, 36, 45 m
    bm_inlay = bmesh.new()
    ring_segs = 64 if lod == 'lod0' else 24
    half_w = 0.13
    z_in = 0.008
    for r_g in (16.0, 26.0, 36.0, 45.0):
        ri = [bm_inlay.verts.new((math.cos(i / ring_segs * math.tau) * (r_g - half_w),
                                  math.sin(i / ring_segs * math.tau) * (r_g - half_w), z_in))
              for i in range(ring_segs)]
        ro = [bm_inlay.verts.new((math.cos(i / ring_segs * math.tau) * (r_g + half_w),
                                  math.sin(i / ring_segs * math.tau) * (r_g + half_w), z_in))
              for i in range(ring_segs)]
        for i in range(ring_segs):
            inext = (i + 1) % ring_segs
            bm_inlay.faces.new((ri[i], ro[i], ro[inext], ri[inext]))

    inlay_obj = common.bm_to_obj(bm_inlay, f'haram_guide_rings_{lod}', col, mat=mats['guide_inlay'], smooth=False)
    common.uv_box_project(inlay_obj, scale=0.25)

    return [floor_obj, inlay_obj]


def _build_colonnade(col, mats, lod='lod0'):
    """2-storey Haram colonnade ring (colR = 48 m), pointed arches, merlons, outer wall & chandeliers."""
    bays = 48 if lod == 'lod0' else 32
    col_segs = 8 if lod == 'lod0' else 6
    arch_segs = 6 if lod == 'lod0' else 4

    bm_cols = bmesh.new()
    bm_gold = bmesh.new()
    bm_stone = bmesh.new()
    bm_warm = bmesh.new()
    bm_bronze = bmesh.new()
    bm_glow = bmesh.new()

    for i in range(bays):
        q0 = i / bays * math.tau
        q1 = (i + 1) / bays * math.tau
        cq, sq = math.cos(q0), math.sin(q0)
        cx, cy = cq * COL_R, sq * COL_R

        # --- Ground-level sculpted marble column (h = 8.4 m) ---
        if lod == 'lod0':
            common.add_cylinder(bm_cols, (cx, cy, 0.24), 0.72, 0.48, segs=8, radius_top=0.68, rot_z=q0)
            common.add_cylinder(bm_cols, (cx, cy, 0.60), 0.62, 0.24, segs=col_segs, radius_top=0.52, cap_ends=False)
            common.add_cylinder(bm_cols, (cx, cy, 4.135), 0.50, 6.83, segs=col_segs, radius_top=0.47, cap_ends=False)
            common.add_cylinder(bm_gold, (cx, cy, 7.64), 0.53, 0.18, segs=col_segs, radius_top=0.50, cap_ends=False)
            common.add_cylinder(bm_gold, (cx, cy, 8.00), 0.49, 0.54, segs=8, radius_top=0.68, rot_z=q0, cap_ends=False)
            common.add_box(bm_cols, (cx, cy, 8.34), (1.28, 1.28, 0.18), rot_z=q0)
        else:
            common.add_cylinder(bm_cols, (cx, cy, 0.34), 0.70, 0.68, segs=6, radius_top=0.56, rot_z=q0, cap_ends=False)
            common.add_cylinder(bm_cols, (cx, cy, 4.135), 0.50, 6.83, segs=6, radius_top=0.47, cap_ends=False)
            common.add_cylinder(bm_gold, (cx, cy, 7.95), 0.49, 0.78, segs=6, radius_top=0.70, rot_z=q0, cap_ends=False)

        # --- Ground-level Pointed Islamic Arch & Dressed Stone Spandrel (z = 7.4..10.0) ---
        _add_pointed_arch_bay(
            bm_stone,
            q0=q0,
            q1=q1,
            r_in=COL_R - 0.52,
            r_out=COL_R + 0.58,
            z_spring=7.45,
            z_apex=9.55,
            z_top=10.05,
            arch_segs=arch_segs,
            pad_u=0.085,
        )

        # --- Second-Storey Open Arched Gallery (z = 10.2..16.2) ---
        if lod == 'lod0':
            # Slender paired upper marble columns at each pier (tangential offset +-0.34 m)
            tx, ty = -sq, cq  # tangential unit vector
            for sgn in (-1.0, 1.0):
                ux = cx + tx * 0.34 * sgn
                uy = cy + ty * 0.34 * sgn
                common.add_cylinder(bm_cols, (ux, uy, 12.95), 0.23, 3.20, segs=6, radius_top=0.21, cap_ends=False)
                common.add_cylinder(bm_gold, (ux, uy, 14.62), 0.22, 0.24, segs=6, radius_top=0.31, cap_ends=False)
        else:
            # LOD1: single clean upper column per bay
            common.add_cylinder(bm_cols, (cx, cy, 12.95), 0.34, 3.20, segs=6, radius_top=0.31, cap_ends=False)
            common.add_cylinder(bm_gold, (cx, cy, 14.62), 0.32, 0.24, segs=6, radius_top=0.42, cap_ends=False)

        # Upper storey pointed Islamic arches (z = 14.25..16.15)
        _add_pointed_arch_bay(
            bm_stone,
            q0=q0,
            q1=q1,
            r_in=COL_R - 0.42,
            r_out=COL_R + 0.48,
            z_spring=14.30,
            z_apex=15.68,
            z_top=16.15,
            arch_segs=4 if lod == 'lod0' else 2,
            pad_u=0.09,
        )

        # Crenelated Islamic merlons along roofline (z = 16.35..17.05)
        merlons_per_bay = 2 if lod == 'lod0' else 1
        for m in range(merlons_per_bay):
            qm = q0 + (q1 - q0) * ((m + 0.5) / merlons_per_bay)
            mx, my = math.cos(qm) * (COL_R - 0.15), math.sin(qm) * (COL_R - 0.15)
            common.add_box(bm_stone, (mx, my, 16.62), (0.34, 0.88, 0.44), rot_z=qm)
            if lod == 'lod0':
                common.add_box(bm_stone, (mx, my, 16.96), (0.30, 0.46, 0.26), rot_z=qm)

        # --- Ornate Warm-Glowing Brass Islamic Chandeliers (24 in LOD0, 16 in LOD1) ---
        if i % 2 == 0:
            ql = 0.5 * (q0 + q1)
            lr = COL_R - 1.20  # 46.8 m
            lx, ly = math.cos(ql) * lr, math.sin(ql) * lr
            if lod == 'lod0':
                common.add_cylinder(bm_bronze, (lx, ly, 8.92), 0.025, 1.32, segs=5, cap_ends=False)
                common.add_cylinder(bm_gold, (lx, ly, 8.15), 0.34, 0.22, segs=8, radius_top=0.10)
                common.add_cylinder(bm_bronze, (lx, ly, 7.22), 0.30, 0.16, segs=8, radius_top=0.34)
                common.add_cylinder(bm_gold, (lx, ly, 7.04), 0.10, 0.22, segs=6, radius_top=0.01)
                bmesh.ops.create_uvsphere(
                    bm_glow,
                    u_segments=10,
                    v_segments=6,
                    radius=0.31,
                    matrix=Matrix.Translation((lx, ly, 7.68)) @ Matrix.Diagonal((1.0, 1.0, 1.25, 1.0)),
                )
            else:
                common.add_cylinder(bm_gold, (lx, ly, 8.15), 0.34, 0.24, segs=6, radius_top=0.08, cap_ends=False)
                bmesh.ops.create_uvsphere(
                    bm_glow,
                    u_segments=6,
                    v_segments=4,
                    radius=0.31,
                    matrix=Matrix.Translation((lx, ly, 7.68)) @ Matrix.Diagonal((1.0, 1.0, 1.25, 1.0)),
                )

    # --- Continuous Molded Cornices, Second-Storey Balustrade & Arcade Enclosure ---
    ring_segs = bays
    # Mid cornice frieze belt (z = 9.98..10.42) with subtle overhang
    _add_ring_band(bm_stone, COL_R - 0.72, COL_R + 0.72, 10.02, 10.42, ring_segs)
    # Subtle gilded molding fillet beneath mid cornice
    _add_ring_band(bm_gold, COL_R - 0.64, COL_R - 0.52, 9.94, 10.04, ring_segs)
    # Second-storey stone balustrade parapet (z = 10.42..11.42)
    _add_ring_band(bm_warm, COL_R - 0.42, COL_R + 0.38, 10.42, 11.34, ring_segs)
    _add_ring_band(bm_cols, COL_R - 0.50, COL_R + 0.44, 11.34, 11.48, ring_segs)
    # Upper roofline cornice (z = 16.08..16.46)
    _add_ring_band(bm_stone, COL_R - 0.68, COL_R + 0.68, 16.08, 16.46, ring_segs)

    # Covered arcade floor (r = 47.4..59.6, z = 0.02), upper gallery slab (z = 10.2), roof deck (z = 16.2)
    _add_ring_band(bm_warm, COL_R - 0.4, OUTER_WALL_R + 0.2, -0.04, 0.02, ring_segs)
    _add_ring_band(bm_warm, COL_R + 0.35, OUTER_WALL_R + 0.2, 10.05, 10.45, ring_segs)
    _add_ring_band(bm_warm, COL_R + 0.35, OUTER_WALL_R + 0.2, 16.05, 16.45, ring_segs)

    # Recessed warm-lit outer Haram arcade backdrop wall (r = 59.5 m, h = 16.5 m)
    # Built as a solid wall shell facing inward so zero void gaps ever appear behind the colonnade
    _add_ring_band(bm_warm, OUTER_WALL_R, OUTER_WALL_R + 0.9, 0.0, 16.55, ring_segs)

    # Subtle recessed pilasters on inner face of outer backdrop wall (adds rich architectural depth)
    if lod == 'lod0':
        for i in range(bays):
            q = i / bays * math.tau
            px, py = math.cos(q) * (OUTER_WALL_R - 0.22), math.sin(q) * (OUTER_WALL_R - 0.22)
            common.add_box(bm_stone, (px, py, 8.2), (0.45, 0.95, 16.2), rot_z=q)

    cols_obj = common.bm_to_obj(bm_cols, f'haram_columns_{lod}', col, mat=mats['marble_col'], smooth=True)
    common.uv_box_project(cols_obj, scale=0.22)
    stone_obj = common.bm_to_obj(bm_stone, f'haram_arches_{lod}', col, mat=mats['stone'], smooth=False)
    common.uv_box_project(stone_obj, scale=0.18)
    warm_obj = common.bm_to_obj(bm_warm, f'haram_arcade_wall_{lod}', col, mat=mats['stone_warm'], smooth=False)
    common.uv_box_project(warm_obj, scale=0.15)
    gold_obj = common.bm_to_obj(bm_gold, f'haram_gold_trim_{lod}', col, mat=mats['gold'], smooth=True)
    common.uv_box_project(gold_obj, scale=0.5)
    bronze_obj = common.bm_to_obj(bm_bronze, f'haram_lantern_bronze_{lod}', col, mat=mats['bronze'], smooth=True)
    glow_obj = common.bm_to_obj(bm_glow, f'haram_lantern_glow_{lod}', col, mat=mats['lantern_glow'], smooth=True)

    return [cols_obj, stone_obj, warm_obj, gold_obj, bronze_obj, glow_obj]


def _build_minarets(col, mats, lod='lod0'):
    """6 Monumental Sculpted Hijazi Minarets at r = 64 m, theta = i/6*2pi + 0.3, rising 44 m."""
    bm_stone = bmesh.new()
    bm_marble = bmesh.new()
    bm_gold = bmesh.new()
    bm_win = bmesh.new()
    bm_glow = bmesh.new()

    mid_segs = 12 if lod == 'lod0' else 6
    cupola_segs = 12 if lod == 'lod0' else 6
    oct_segs = 8 if lod == 'lod0' else 6

    for i in range(6):
        q = i / 6.0 * math.tau + 0.3
        # Match mataf.js line 87: x = cos(q) * 64, z = sin(q) * 64 -> three_to_bl(tx, 0, tz)
        tx = math.cos(q) * MINARET_R
        tz = math.sin(q) * MINARET_R
        base_bl = common.three_to_bl(tx, 0.0, tz)
        mx, my = base_bl.x, base_bl.y

        # 1. Square dressed-stone plinth (z = 0..10.8 m) + chamfered transition collar (10.8..12.2)
        common.add_box(bm_stone, (mx, my, 5.4), (4.4, 4.4, 10.8), rot_z=-q)
        common.add_box(bm_marble, (mx, my, 10.95), (4.7, 4.7, 0.45), rot_z=-q)
        common.add_cylinder(bm_stone, (mx, my, 11.65), 2.55, 1.35, segs=oct_segs, radius_top=1.95, rot_z=math.pi / 8.0, cap_ends=False)

        # 2. Fluted octagonal lower shaft (z = 12.2..18.4 m)
        common.add_cylinder(bm_marble, (mx, my, 15.30), 1.90, 6.20, segs=oct_segs, radius_top=1.78, rot_z=math.pi / 8.0, cap_ends=False)

        # 3. Carved Muqarnas Lower Balcony (z = 18.4..20.8 m, centered ~19 m)
        common.add_cylinder(bm_stone, (mx, my, 18.85), 1.78, 0.90, segs=oct_segs, radius_top=2.58, rot_z=math.pi / 8.0, cap_ends=False)
        common.add_cylinder(bm_marble, (mx, my, 19.50), 2.66, 0.42, segs=oct_segs, radius_top=2.66, rot_z=math.pi / 8.0)
        common.add_cylinder(bm_stone, (mx, my, 20.15), 2.55, 0.96, segs=oct_segs, radius_top=2.55, rot_z=math.pi / 8.0)
        if lod == 'lod0':
            common.add_cylinder(bm_gold, (mx, my, 19.32), 2.68, 0.14, segs=8, radius_top=2.68, rot_z=math.pi / 8.0, cap_ends=False)

        # 4. Slender cylindrical mid shaft (z = 20.5..30.6 m) with arched window niches
        common.add_cylinder(bm_marble, (mx, my, 25.55), 1.48, 10.10, segs=mid_segs, radius_top=1.34, cap_ends=False)
        if lod == 'lod0':
            for k in range(4):
                wa = k * math.pi * 0.5 - q
                wx = mx + math.cos(wa) * 1.40
                wy = my + math.sin(wa) * 1.40
                common.add_box(bm_win, (wx, wy, 25.6), (0.16, 0.52, 1.85), rot_z=wa)
                common.add_box(bm_gold, (wx, wy, 26.62), (0.20, 0.62, 0.14), rot_z=wa)

        # 5. Upper Carved Balcony (z = 30.6..32.6 m, centered ~31 m)
        common.add_cylinder(bm_stone, (mx, my, 30.95), 1.34, 0.72, segs=oct_segs, radius_top=2.06, rot_z=math.pi / 8.0, cap_ends=False)
        common.add_cylinder(bm_marble, (mx, my, 31.48), 2.12, 0.36, segs=oct_segs, radius_top=2.12, rot_z=math.pi / 8.0)
        common.add_cylinder(bm_stone, (mx, my, 32.02), 2.02, 0.78, segs=oct_segs, radius_top=2.02, rot_z=math.pi / 8.0)
        if lod == 'lod0':
            common.add_cylinder(bm_gold, (mx, my, 31.34), 2.14, 0.12, segs=8, radius_top=2.14, rot_z=math.pi / 8.0, cap_ends=False)

        # 6. Open Arched Lantern Pavilion (Jawsaq, z = 32.4..36.6 m)
        n_pav = 6 if lod == 'lod0' else 4
        pav_r = 1.18
        for k in range(n_pav):
            pa = k / n_pav * math.tau
            px = mx + math.cos(pa) * pav_r
            py = my + math.sin(pa) * pav_r
            common.add_cylinder(bm_marble, (px, py, 34.45), 0.14, 4.10, segs=5, radius_top=0.13, cap_ends=False)
        common.add_cylinder(bm_stone, (mx, my, 36.55), 1.32, 0.56, segs=oct_segs, radius_top=1.36, rot_z=math.pi / 8.0)
        common.add_cylinder(bm_glow, (mx, my, 34.50), 0.78, 3.20, segs=oct_segs, radius_top=0.78, cap_ends=False)

        # 7. Tapered Ribbed Cupola (z = 36.8..40.5 m) & Gleaming Golden Crescent Spire (z = 40.5..44.0 m)
        cup_rings = []
        v_steps = 7 if lod == 'lod0' else 4
        for iv in range(v_steps):
            t = iv / (v_steps - 1)
            cz = 36.80 + 3.70 * (t ** 0.85)
            cr = 1.24 * ((1.0 - t) ** 0.72)
            cr = max(cr, 0.12)
            rib_a = 0.06 * math.sin(t * math.pi) if lod == 'lod0' else 0.0
            ring = []
            for k in range(cupola_segs):
                a = k / cupola_segs * math.tau
                rr = cr + (rib_a if (k % 2 == 0) else 0.0)
                ring.append(bm_marble.verts.new((mx + math.cos(a) * rr, my + math.sin(a) * rr, cz)))
            cup_rings.append(ring)
        common.loft_rings(bm_marble, cup_rings, closed_u=True, cap_start=False, cap_end=True)

        # Gleaming golden spire rod + Alem spheres + golden crescent reaching z = 44.0 m
        common.add_cylinder(bm_gold, (mx, my, 41.85), 0.10, 2.75, segs=5, radius_top=0.04)
        if lod == 'lod0':
            for sz, sr in ((40.75, 0.34), (41.55, 0.25), (42.20, 0.18)):
                bmesh.ops.create_uvsphere(
                    bm_gold,
                    u_segments=8,
                    v_segments=5,
                    radius=sr,
                    matrix=Matrix.Translation((mx, my, sz)),
                )
        n_cr = 10 if lod == 'lod0' else 5
        cres_pts = []
        for k in range(n_cr + 1):
            ang = math.radians(-130.0 + 260.0 * (k / n_cr))
            cr_r = 0.56
            dx_local = math.sin(ang) * cr_r
            dz_local = -math.cos(ang) * cr_r
            tx_c = -math.sin(-q) * dx_local
            ty_c = math.cos(-q) * dx_local
            cres_pts.append(Vector((mx + tx_c, my + ty_c, 43.42 + dz_local)))
        common.add_tube(bm_gold, cres_pts, radius=lambda u: 0.04 + 0.09 * math.sin(u * math.pi), segs=4, closed_caps=True)

    st_obj = common.bm_to_obj(bm_stone, f'haram_minaret_stone_{lod}', col, mat=mats['stone'], smooth=False)
    common.uv_box_project(st_obj, scale=0.14)
    mb_obj = common.bm_to_obj(bm_marble, f'haram_minaret_marble_{lod}', col, mat=mats['marble_col'], smooth=True)
    common.uv_box_project(mb_obj, scale=0.14)
    gd_obj = common.bm_to_obj(bm_gold, f'haram_minaret_gold_{lod}', col, mat=mats['gold'], smooth=True)
    wn_obj = common.bm_to_obj(bm_win, f'haram_minaret_win_{lod}', col, mat=mats['window_dark'], smooth=False)
    gl_obj = common.bm_to_obj(bm_glow, f'haram_minaret_glow_{lod}', col, mat=mats['lantern_glow'], smooth=True)
    return [st_obj, mb_obj, gd_obj, wn_obj, gl_obj]


def _build_green_line_lamp(col, mats, lod='lod0'):
    """Green Line Marker Lamp mounted on East colonnade facing the Black Stone at world (47.3, 5.0, 0)."""
    pos = common.three_to_bl(*GREEN_LAMP_WORLD)  # (47.3, 0.0, 5.0)
    bm_housing = bmesh.new()
    bm_led = bmesh.new()

    # Brass/bronze architectural wall sconce housing mounted back into column at x = 48.0
    common.add_box(bm_housing, (pos.x + 0.22, pos.y, pos.z), (0.48, 0.60, 0.55))  # mounting arm
    common.add_box(bm_housing, (pos.x + 0.05, pos.y, pos.z), (0.24, 1.76, 1.06))  # beveled frame body
    # Top & bottom bronze architectural hood lips
    common.add_box(bm_housing, (pos.x - 0.03, pos.y, pos.z + 0.54), (0.34, 1.86, 0.10))
    common.add_box(bm_housing, (pos.x - 0.03, pos.y, pos.z - 0.54), (0.34, 1.86, 0.10))

    # Bright glowing emerald-green LED indicator bar facing -X directly toward the Black Stone
    common.add_box(bm_led, (pos.x - 0.06, pos.y, pos.z), (0.10, 1.50, 0.78))

    h_obj = common.bm_to_obj(bm_housing, f'haram_green_lamp_housing_{lod}', col, mat=mats['bronze'], smooth=False)
    l_obj = common.bm_to_obj(bm_led, f'haram_green_lamp_led_{lod}', col, mat=mats['green_led'], smooth=False)
    return [h_obj, l_obj]


def _bake_and_join(parts, name, col):
    ao_mats = {'mat_haram_marble_col', 'mat_haram_stone', 'mat_haram_stone_warm'}
    for obj in parts:
        uses_ao = any(m and m.name in ao_mats for m in obj.data.materials)
        if uses_ao:
            common.bake_vertex_ao(obj, strength=0.20, min_val=0.75)
        else:
            me = obj.data
            if me.color_attributes.get('Color') is None:
                ca = me.color_attributes.new(name='Color', type='BYTE_COLOR', domain='POINT')
                for i in range(len(ca.data)):
                    ca.data[i].color = (1.0, 1.0, 1.0, 1.0)
    return common.join_objects(parts, name, col=col)


def build_haram_mataf(col):
    """Build `haram_mataf_LOD0` (48-bay) and `haram_mataf_LOD1` (32-bay) in `col`."""
    mats = _make_materials()

    parts_lod0 = []
    parts_lod0.extend(_build_floor_and_rings(col, mats, lod='lod0'))
    parts_lod0.extend(_build_colonnade(col, mats, lod='lod0'))
    parts_lod0.extend(_build_minarets(col, mats, lod='lod0'))
    parts_lod0.extend(_build_green_line_lamp(col, mats, lod='lod0'))
    lod0 = _bake_and_join(parts_lod0, 'haram_mataf_LOD0', col)

    parts_lod1 = []
    parts_lod1.extend(_build_floor_and_rings(col, mats, lod='lod1'))
    parts_lod1.extend(_build_colonnade(col, mats, lod='lod1'))
    parts_lod1.extend(_build_minarets(col, mats, lod='lod1'))
    parts_lod1.extend(_build_green_line_lamp(col, mats, lod='lod1'))
    lod1 = _bake_and_join(parts_lod1, 'haram_mataf_LOD1', col)

    return lod0, lod1


def _render_haram_preview(lod0, lod1, out_path):
    """Render 2-angle architectural preview: Mataf courtyard & colonnade/minarets + East Green Lamp."""
    lod1.hide_render = True
    lod1.hide_viewport = True

    shots = [
        # Shot 1: Sweeping elevated Mataf view showing white Thassos floor, guide rings, 2-tier arches & minarets
        (common.three_to_bl(-32.0, 18.0, 26.0), common.three_to_bl(36.0, 11.0, -18.0), 28),
        # Shot 2: Eye-level view across Mataf looking East directly at colonnade arches, chandeliers & Green Line Lamp
        (common.three_to_bl(14.0, 5.8, 12.0), common.three_to_bl(47.3, 8.0, -2.0), 32),
    ]

    tiles = []
    tmp_files = []
    try:
        for idx, (eye, tgt, lens) in enumerate(shots):
            with tempfile.NamedTemporaryFile(suffix=f'_haram_{idx}.png', delete=False) as tf:
                tmp_png = tf.name
            tmp_files.append(tmp_png)
            preview.render_shot(
                eye=eye,
                target=tgt,
                out_path=tmp_png,
                res=(720, 560),
                lens=lens,
                world_color=(0.54, 0.68, 0.88),
            )
            img = bpy.data.images.load(tmp_png, check_existing=False)
            w, h = img.size[0], img.size[1]
            arr = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(arr)
            tiles.append(arr.reshape((h, w, 4)))
            bpy.data.images.remove(img)

        sheet = np.concatenate(tiles, axis=1)
        sh, sw = sheet.shape[:2]
        out_img = bpy.data.images.new('_HaramSheet', sw, sh, alpha=True)
        out_img.pixels.foreach_set(sheet.ravel())
        out_img.filepath_raw = str(out_path)
        out_img.file_format = 'PNG'
        out_img.save()
        bpy.data.images.remove(out_img)
    finally:
        for f in tmp_files:
            if os.path.exists(f):
                os.remove(f)
        lod1.hide_render = False
        lod1.hide_viewport = False


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


def export_haram_mataf(render_preview=True):
    """Build, verify, export `public/models/env/haram_mataf.glb`, and render `env_haram_mataf.png`."""
    common.ensure_dirs()
    common.reset_scene()

    col = common.make_collection('HaramMataf')
    lod0, lod1 = build_haram_mataf(col)

    t0 = common.tri_count(lod0)
    t1 = common.tri_count(lod1)
    assert t0 <= 36000, f'haram_mataf_LOD0 tris {t0} > 36000'
    assert t1 <= 14000, f'haram_mataf_LOD1 tris {t1} > 14000'

    # Verify minaret spire height & overall courtyard radius
    zs = [v.co.z for v in lod0.data.vertices]
    rs = [math.hypot(v.co.x, v.co.y) for v in lod0.data.vertices]
    assert 43.0 <= max(zs) <= 45.0, f'Unexpected minaret height: {max(zs):.2f}'
    assert 65.0 <= max(rs) <= 69.0, f'Unexpected outer minaret extent: {max(rs):.2f}'

    out_glb = common.MODELS_ENV / 'haram_mataf.glb'
    size_bytes = common.export_glb([lod0, lod1], out_glb, vertex_colors=False)
    _verify_glb(out_glb, size_bytes, max_kb=750)

    out_png = common.PREVIEWS / 'env_haram_mataf.png'
    if render_preview:
        _render_haram_preview(lod0, lod1, out_png)

    info = {
        'name': 'haram_mataf',
        'glb': str(out_glb.relative_to(ROOT)),
        'tris_lod0': t0,
        'tris_lod1': t1,
        'size_kb': round(size_bytes / 1024.0, 1),
        'minaret_height_m': round(max(zs), 2),
    }
    print(f"HARAM_MATAF_OK tris={t0}/{t1} size={info['size_kb']}KB minarets_h={info['minaret_height_m']}m")
    return info


if __name__ == '__main__':
    export_haram_mataf(render_preview=True)
