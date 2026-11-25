"""Chapter 4 — Makkah environment builder (Blender 5.2 LTS -> public/models/env/makkah.glb).

Builds the realistic Makkah hotel portico & lobby, veined cream marble plaza with
promenade borders and 12 ornate cast-bronze lamp posts, monumental Al-Masjid al-Haram
stone facade with pointed Islamic arches, grand bronze-and-gold ceremonial portal,
twin 65 m multi-tiered Hijazi minarets, and distant 125 m Makkah Clock Tower silhouette.

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

from blender.lib import common, preview, textures  # noqa: E402
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

# ------------------------------------------------------------------ budget & constants
OUT_GLB = MODELS_ENV / 'makkah.glb'
OUT_PREVIEW = PREVIEWS / 'env_makkah.png'
BUDGET_LOD0_TRIS = 32000
BUDGET_LOD1_TRIS = 14000
BUDGET_KB = 750


# ------------------------------------------------------------------ Three.js space helpers
def _tbox(bm, x0, x1, y0, y1, z0, z1, rot_y=0.0):
    """Add an axis-aligned box defined in Three.js world extents [x0..x1, y0..y1, z0..z1]."""
    cx = (x0 + x1) * 0.5
    cy = (y0 + y1) * 0.5
    cz = (z0 + z1) * 0.5
    sx = abs(x1 - x0)
    sy = abs(z1 - z0)  # Three.js Z maps to Blender -Y
    sz = abs(y1 - y0)  # Three.js Y maps to Blender +Z
    return add_box(bm, three_to_bl(cx, cy, cz), (sx, sy, sz), rot_z=rot_y)


def _tcyl(bm, tx, y0, y1, tz, r1, r2=None, segs=12, cap_ends=True, rot_y=0.0):
    """Add a vertical cylinder/frustum spanning Three.js y in [y0, y1] at (tx, tz)."""
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


def _tsphere(bm, tx, ty, tz, radius, segs=10, rings=7):
    """Add a UV sphere centered at Three.js (tx, ty, tz)."""
    mat = Matrix.Translation(three_to_bl(tx, ty, tz))
    return bmesh.ops.create_uvsphere(
        bm,
        u_segments=int(segs),
        v_segments=int(rings),
        radius=float(radius),
        matrix=mat,
    )


def _add_pointed_arch_profile(bm, cx, y_spring, z_center, span_w, arch_h, thick, depth, segs=6):
    """Add a 3D pointed Islamic archivolt arch spanning along X at Three.js z_center."""
    half = span_w * 0.5
    pts_in = []
    pts_out = []
    n = max(3, int(segs))
    # Left half: spring (-half, 0) up to pointed apex (0, arch_h)
    for i in range(n + 1):
        t = i / n
        ang = t * (math.pi * 0.5)
        # Pointed ogive curve blends circular arc with sharper apex pull
        x_in = -half * math.cos(ang)
        y_in = arch_h * (math.sin(ang) ** 0.82)
        nx = -math.cos(ang) * 0.85
        ny = math.sin(ang)
        ln = math.hypot(nx, ny) or 1.0
        nx /= ln
        ny /= ln
        pts_in.append((cx + x_in, y_spring + y_in))
        pts_out.append((cx + x_in + nx * thick, y_spring + y_in + ny * thick))
    # Right half: apex down to (+half, 0)
    for i in range(1, n + 1):
        t = i / n
        ang = (1.0 - t) * (math.pi * 0.5)
        x_in = half * math.cos(ang)
        y_in = arch_h * (math.sin(ang) ** 0.82)
        nx = math.cos(ang) * 0.85
        ny = math.sin(ang)
        ln = math.hypot(nx, ny) or 1.0
        nx /= ln
        ny /= ln
        pts_in.append((cx + x_in, y_spring + y_in))
        pts_out.append((cx + x_in + nx * thick, y_spring + y_in + ny * thick))

    z0 = z_center - depth * 0.5
    z1 = z_center + depth * 0.5
    rings = []
    for (ix, iy), (ox, oy) in zip(pts_in, pts_out):
        v0 = bm.verts.new(three_to_bl(ix, iy, z0))
        v1 = bm.verts.new(three_to_bl(ox, oy, z0))
        v2 = bm.verts.new(three_to_bl(ox, oy, z1))
        v3 = bm.verts.new(three_to_bl(ix, iy, z1))
        rings.append([v0, v1, v2, v3])
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)


def _add_pointed_arch_fill(bm, cx, y_base, y_spring, z_plane, span_w, arch_h, depth, segs=6):
    """Add a solid recessed backing slab shaped like a pointed Islamic arch."""
    half = span_w * 0.5
    n = max(3, int(segs))
    profile = [(cx - half, y_base)]
    for i in range(n + 1):
        t = i / n
        ang = t * (math.pi * 0.5)
        profile.append((cx - half * math.cos(ang), y_spring + arch_h * (math.sin(ang) ** 0.82)))
    for i in range(1, n + 1):
        t = i / n
        ang = (1.0 - t) * (math.pi * 0.5)
        profile.append((cx + half * math.cos(ang), y_spring + arch_h * (math.sin(ang) ** 0.82)))
    profile.append((cx + half, y_base))

    z0 = z_plane - depth * 0.5
    z1 = z_plane + depth * 0.5
    front = [bm.verts.new(three_to_bl(px, py, z1)) for px, py in profile]
    back = [bm.verts.new(three_to_bl(px, py, z0)) for px, py in profile]
    try:
        bm.faces.new(front)
        bm.faces.new(list(reversed(back)))
    except ValueError:
        pass
    m = len(profile)
    for i in range(m):
        inext = (i + 1) % m
        bm.faces.new((front[i], front[inext], back[inext], back[i]))


def _add_crescent_finial(bm, tx, y_base, tz, scale=1.0, segs=8):
    """Add a sculpted Islamic finial spire + gilded crescent moon at Three.js (tx, y_base, tz)."""
    s = float(scale)
    _tcyl(bm, tx, y_base, y_base + 2.6 * s, tz, 0.08 * s, 0.03 * s, segs=segs)
    for frac, rad in ((0.22, 0.24), (0.50, 0.19), (0.76, 0.14)):
        _tsphere(bm, tx, y_base + frac * 2.4 * s, tz, rad * s, segs=segs, rings=5)
    # Crescent arc centered above the top orb
    cy = y_base + 2.75 * s
    r_c = 0.55 * s
    pts = []
    n = max(6, segs)
    for i in range(n + 1):
        ang = math.radians(-140.0 + 280.0 * (i / n))
        # Open upward crescent in XY plane
        px = tx + math.sin(ang) * r_c
        py = cy - math.cos(ang) * r_c
        pts.append(three_to_bl(px, py, tz))

    def _rad(u):
        return (0.04 + 0.10 * math.sin(u * math.pi)) * s

    add_tube(bm, pts, _rad, segs=max(5, segs - 2), closed_caps=True, ref_up=(0.0, 1.0, 0.0))


# ------------------------------------------------------------------ materials
def _make_materials():
    """Build and cache shared realistic PBR materials for Makkah."""
    marble_alb, marble_nrm = textures.tex_marble_cream(size=512, name='makkah_marble_cream', tiles=4)
    stone_haram = textures.tex_stone_haram(size=512, name='makkah_stone_haram', tint='#ece2cf')
    stone_hotel = textures.tex_stone_haram(size=512, name='makkah_stone_hotel', tint='#dfd0b6')
    walnut_alb, walnut_nrm = textures.tex_wood_oak(size=256, name='makkah_walnut', planks=6, tint='#4f311d')
    gold_alb, gold_nrm = textures.tex_gold_relief(size=256, name='makkah_gold_relief')

    return {
        'marble_plaza': make_pbr_material(
            'mat_makkah_plaza_marble',
            roughness=0.26,
            metallic=0.0,
            image=marble_alb,
            normal_image=marble_nrm,
            normal_strength=0.35,
            use_vcol=False,
        ),
        'marble_inlay': make_pbr_material(
            'mat_makkah_plaza_inlay',
            color='#bfa378',
            roughness=0.30,
            metallic=0.08,
            use_vcol=False,
        ),
        'marble_trim': make_pbr_material(
            'mat_makkah_marble_trim',
            color='#e5d9c3',
            roughness=0.34,
            metallic=0.0,
            use_vcol=True,
        ),
        'stone_haram': make_pbr_material(
            'mat_makkah_stone_haram',
            roughness=0.56,
            metallic=0.0,
            image=stone_haram,
            use_vcol=True,
        ),
        'stone_hotel': make_pbr_material(
            'mat_makkah_stone_hotel',
            roughness=0.60,
            metallic=0.0,
            image=stone_hotel,
            use_vcol=True,
        ),
        'stone_clock': make_pbr_material(
            'mat_makkah_clock_stone',
            color='#cbc1af',
            roughness=0.62,
            metallic=0.04,
            use_vcol=True,
        ),
        'walnut': make_pbr_material(
            'mat_makkah_walnut',
            roughness=0.32,
            metallic=0.0,
            image=walnut_alb,
            normal_image=walnut_nrm,
            normal_strength=0.45,
        ),
        'bronze': make_pbr_material(
            'mat_makkah_bronze',
            color='#3b2d1f',
            roughness=0.34,
            metallic=0.86,
        ),
        'gold': make_pbr_material(
            'mat_makkah_gold',
            color='#d8b056',
            roughness=0.24,
            metallic=0.92,
        ),
        'gold_relief': make_pbr_material(
            'mat_makkah_gold_relief',
            roughness=0.28,
            metallic=0.88,
            image=gold_alb,
            normal_image=gold_nrm,
            normal_strength=0.7,
        ),
        'window_warm': make_pbr_material(
            'mat_makkah_window_warm',
            color='#9cb2bf',
            roughness=0.14,
            metallic=0.15,
            emissive='#ffda9c',
            emissive_strength=1.15,
        ),
        'haram_alcove': make_pbr_material(
            'mat_makkah_haram_alcove',
            color='#6e5c45',
            roughness=0.45,
            metallic=0.1,
            emissive='#ffd48e',
            emissive_strength=0.85,
        ),
        'portal_glow': make_pbr_material(
            'mat_makkah_portal_glow',
            color='#fff3d4',
            roughness=0.25,
            metallic=0.0,
            emissive='#ffd78c',
            emissive_strength=2.2,
        ),
        'lamp_glass': make_pbr_material(
            'mat_makkah_lamp_glass',
            color='#fff6e0',
            roughness=0.18,
            metallic=0.0,
            emissive='#ffe09c',
            emissive_strength=3.0,
        ),
        'clock_face': make_pbr_material(
            'mat_makkah_clock_face',
            color='#e4f6ea',
            roughness=0.22,
            metallic=0.0,
            emissive='#a6f0c4',
            emissive_strength=2.0,
        ),
    }


# ------------------------------------------------------------------ builders
def _build_plaza(col, mats, lod=0):
    """Grand 90x80 m marble plaza centered at (0, 0, -12) with promenade borders."""
    objs = []
    # Main marble slab: x in [-45, 45], z in [-52, 28], top at y=0
    bm_fl = bmesh.new()
    _tbox(bm_fl, -45.0, 45.0, -0.22, 0.0, -52.0, 28.0)
    fl_obj = bm_to_obj(bm_fl, f'_plaza_floor_l{lod}', col, mat=mats['marble_plaza'], smooth=False)
    uv_box_project(fl_obj, scale=0.18)
    objs.append(fl_obj)

    # Geometric stone promenade border strips & central axis runner leading to Haram gate
    bm_in = bmesh.new()
    y0, y1 = 0.001, 0.012
    # Longitudinal promenade runners flanking the central processional axis
    for x in (-14.6, -13.4, -7.2, -3.4, 3.4, 7.2, 13.4, 14.6):
        w = 0.36 if abs(x) < 10 else 0.24
        _tbox(bm_in, x - w * 0.5, x + w * 0.5, y0, y1, -39.2, 9.4)
    # Transverse plaza stone grid dividers
    for z in (8.0, 0.0, -8.0, -16.0, -24.0, -32.0, -38.8):
        _tbox(bm_in, -24.0, 24.0, y0, y1, z - 0.16, z + 0.16)
    # Hotel portico apron border
    _tbox(bm_in, -12.4, 12.4, y0, y1, 9.2, 9.55)
    if lod == 0:
        # Central geometric octagonal medallion along the axis at z=-16
        segs = 8
        for r_in, r_out in ((4.2, 4.55), (2.2, 2.45)):
            for i in range(segs):
                a0 = i / segs * math.tau + math.pi / 8.0
                a1 = (i + 1) / segs * math.tau + math.pi / 8.0
                mx = (math.cos(a0) + math.cos(a1)) * 0.5 * (r_in + r_out) * 0.5
                mz = -16.0 + (math.sin(a0) + math.sin(a1)) * 0.5 * (r_in + r_out) * 0.5
                seg_len = math.hypot(math.cos(a1) - math.cos(a0), math.sin(a1) - math.sin(a0)) * r_out
                rot = math.atan2(math.sin(a1) - math.sin(a0), math.cos(a1) - math.cos(a0))
                add_box(
                    bm_in,
                    three_to_bl(mx, (y0 + y1) * 0.5, mz),
                    (seg_len, r_out - r_in, y1 - y0),
                    rot_z=-rot,
                )
    in_obj = bm_to_obj(bm_in, f'_plaza_inlay_l{lod}', col, mat=mats['marble_inlay'], smooth=False)
    uv_box_project(in_obj, scale=0.4)
    objs.append(in_obj)
    return objs


def _build_hotel(col, mats, lod=0):
    """Makkah hotel facade (z>=18.5), grand portico (z in [9.5,18.5]), counter & signboard frame."""
    objs = []
    bm_stone = bmesh.new()
    bm_trim = bmesh.new()
    bm_win = bmesh.new()
    bm_bronze = bmesh.new()
    bm_gold = bmesh.new()
    bm_walnut = bmesh.new()
    bm_lamp = bmesh.new()

    # Main hotel tower mass: x in [-20, 20], z in [18.5, 24.5], y in [0, 30]
    _tbox(bm_stone, -20.0, 20.0, 0.0, 30.0, 18.5, 24.5)

    # Molded horizontal stone cornices & roofline parapet
    for cy, ch, proj in ((6.2, 0.45, 0.35), (13.2, 0.32, 0.25), (20.2, 0.32, 0.25), (27.2, 0.32, 0.25), (29.8, 0.65, 0.55)):
        _tbox(bm_trim, -20.4, 20.4, cy - ch * 0.5, cy + ch * 0.5, 18.5 - proj, 24.7)
    # Stepped crown parapet
    _tbox(bm_stone, -20.1, 20.1, 30.0, 31.1, 18.35, 19.0)
    _tbox(bm_trim, -20.3, 20.3, 31.05, 31.35, 18.25, 19.1)

    # Classical vertical pilasters across hotel front facade
    pilaster_xs = [-19.6, -13.2, -6.8, -0.4, 0.4, 6.8, 13.2, 19.6]
    for px in pilaster_xs:
        _tbox(bm_trim, px - 0.35, px + 0.35, 0.0, 30.0, 18.22, 18.55)

    # Recessed warm-lit arched hotel room windows (7 floors)
    win_xs = [-17.4, -15.2, -11.0, -8.8, -4.6, -2.4, 2.4, 4.6, 8.8, 11.0, 15.2, 17.4]
    floor_ys = [7.6, 10.8, 14.4, 17.6, 21.2, 24.4, 27.9] if lod == 0 else [8.2, 13.0, 17.8, 22.6, 27.4]
    arch_segs = 3
    for fy in floor_ys:
        for wx in win_xs:
            # Glowing recessed glass pane slightly in front of main wall z=18.5 (toward -z)
            _tbox(bm_win, wx - 0.72, wx + 0.72, fy - 0.85, fy + 0.75, 18.42, 18.50)
            # Stone surround jambs & sill
            _tbox(bm_trim, wx - 0.90, wx - 0.72, fy - 0.95, fy + 0.60, 18.30, 18.52)
            _tbox(bm_trim, wx + 0.72, wx + 0.90, fy - 0.95, fy + 0.60, 18.30, 18.52)
            _tbox(bm_trim, wx - 0.98, wx + 0.98, fy - 1.05, fy - 0.85, 18.24, 18.52)
            if lod == 0:
                _add_pointed_arch_profile(bm_trim, wx, fy + 0.52, 18.40, 1.48, 0.56, 0.18, 0.22, segs=arch_segs)
            else:
                _tbox(bm_trim, wx - 0.90, wx + 0.90, fy + 0.60, fy + 0.86, 18.30, 18.52)

    # Ground-floor hotel lobby entrance glass doors (centered x in [-4.0, 4.0], z=18.42)
    _tbox(bm_win, -3.8, 3.8, 0.05, 4.1, 18.42, 18.50)
    for mx in (-3.85, -1.9, 0.0, 1.9, 3.85):
        _tbox(bm_bronze, mx - 0.07, mx + 0.07, 0.0, 4.2, 18.34, 18.50)
    _tbox(bm_bronze, -3.95, 3.95, 4.1, 4.35, 18.30, 18.52)
    _tbox(bm_bronze, -3.95, 3.95, 2.55, 2.68, 18.34, 18.48)

    # Grand Entrance Portico: x in [-12, 12], z in [9.5, 18.5], roof y=5.3..5.95
    _tbox(bm_trim, -12.15, 12.15, 5.30, 5.95, 9.45, 18.55)
    # Molded overhanging cornice & decorative parapet
    _tbox(bm_stone, -12.40, 12.40, 5.88, 6.12, 9.28, 18.60)
    _tbox(bm_trim, -12.10, 12.10, 6.12, 6.50, 9.48, 9.85)
    _tbox(bm_trim, -12.10, -11.72, 6.12, 6.50, 9.48, 18.55)
    _tbox(bm_trim, 11.72, 12.10, 6.12, 6.50, 9.48, 18.55)
    # Gold fascia accent trim line on portico
    _tbox(bm_gold, -12.25, 12.25, 5.56, 5.66, 9.38, 9.48)

    # Coffered underside ribs & recessed warm soffit downlights
    if lod == 0:
        for bx in (-11.6, -6.0, 0.0, 6.0, 11.6):
            _tbox(bm_trim, bx - 0.22, bx + 0.22, 5.14, 5.32, 9.65, 18.45)
        for bz in (9.8, 14.0, 18.2):
            _tbox(bm_trim, -11.8, 11.8, 5.14, 5.32, bz - 0.22, bz + 0.22)
        for lx in (-9.0, -3.0, 3.0, 9.0):
            for lz in (11.9, 16.1):
                _tcyl(bm_lamp, lx, 5.26, 5.32, lz, 0.22, 0.22, segs=8)

    # Twin monumental stone portico pillars matching BOXES at x=+-11.5, z in [9.6, 10.6]
    for px in (-11.5, 11.5):
        # Stepped marble plinth base
        _tbox(bm_trim, px - 0.50, px + 0.50, 0.0, 0.55, 9.60, 10.60)
        _tbox(bm_trim, px - 0.44, px + 0.44, 0.55, 0.85, 9.66, 10.54)
        # Fluted/octagonal stone shaft
        _tcyl(bm_stone, px, 0.85, 4.65, 10.10, 0.41, 0.37, segs=12 if lod == 0 else 8)
        # Molded stone & gold capital
        _tcyl(bm_gold, px, 4.65, 4.82, 10.10, 0.39, 0.44, segs=12 if lod == 0 else 8)
        _tbox(bm_trim, px - 0.48, px + 0.48, 4.82, 5.30, 9.62, 10.58)
        # Engaged rear pilaster against hotel facade
        _tbox(bm_trim, px - 0.46, px + 0.46, 0.0, 5.30, 18.10, 18.55)

    # Sculpted bronze & gilded signboard frame above portico at (0, 6.6, 9.52..9.72)
    # Leaves z=9.45 completely clear for the Three.js Arabic canvas sign (w=8, h=1.2)
    _tbox(bm_bronze, -4.18, 4.18, 5.92, 7.28, 9.54, 9.74)
    # Protruding sculpted gilded outer border rails framing the 8.0 x 1.2 sign opening
    _tbox(bm_gold, -4.24, 4.24, 7.20, 7.36, 9.42, 9.76)  # top rail
    _tbox(bm_gold, -4.24, 4.24, 5.84, 6.00, 9.42, 9.76)  # bottom rail
    _tbox(bm_gold, -4.24, -4.04, 5.84, 7.36, 9.42, 9.76)  # left rail
    _tbox(bm_gold, 4.04, 4.24, 5.84, 7.36, 9.42, 9.76)   # right rail
    # Decorative top crest medallion & mounting legs to portico parapet
    _tbox(bm_gold, -0.70, 0.70, 7.36, 7.62, 9.52, 9.72)
    for sx in (-3.2, 0.0, 3.2):
        _tbox(bm_bronze, sx - 0.10, sx + 0.10, 5.95, 6.55, 9.64, 9.82)

    # Polished walnut & marble reception counter matching BOXES x in [-7.4, -2.6], z in [15.4, 16.4], h=1.1
    _tbox(bm_bronze, -7.36, -2.64, 0.0, 0.12, 15.46, 16.34)  # recessed kickplate
    _tbox(bm_walnut, -7.38, -2.62, 0.12, 1.02, 15.42, 16.38)  # walnut cabinet body
    _tbox(bm_gold, -7.40, -2.60, 0.34, 0.38, 15.39, 15.44)    # front brass trim lower
    _tbox(bm_gold, -7.40, -2.60, 0.84, 0.88, 15.39, 15.44)    # front brass trim upper
    _tbox(bm_trim, -7.42, -2.58, 1.02, 1.10, 15.38, 16.42)    # overhanging marble top
    # Small brass & glowing cream lobby desk lamp on right corner of counter
    _tcyl(bm_gold, -3.15, 1.10, 1.14, 15.88, 0.11, 0.09, segs=10)
    _tcyl(bm_gold, -3.15, 1.14, 1.44, 15.88, 0.025, 0.02, segs=8)
    _tcyl(bm_lamp, -3.15, 1.40, 1.62, 15.88, 0.16, 0.10, segs=10)

    parts = [
        (bm_stone, f'_hotel_stone_l{lod}', mats['stone_hotel'], False, 0.24, True),
        (bm_trim, f'_hotel_trim_l{lod}', mats['marble_trim'], False, 0.35, True),
        (bm_win, f'_hotel_win_l{lod}', mats['window_warm'], False, 0.5, False),
        (bm_bronze, f'_hotel_bronze_l{lod}', mats['bronze'], False, 0.5, False),
        (bm_gold, f'_hotel_gold_l{lod}', mats['gold'], True, 0.5, False),
        (bm_walnut, f'_hotel_walnut_l{lod}', mats['walnut'], False, 0.5, False),
        (bm_lamp, f'_hotel_lamp_l{lod}', mats['lamp_glass'], True, 0.5, False),
    ]
    for bm, name, mat, smooth, uv_s, ao in parts:
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_box_project(obj, scale=uv_s)
        if ao:
            bake_vertex_ao(obj, strength=0.26, min_val=0.64)
        objs.append(obj)
    return objs


def _build_haram_facade(col, mats, lod=0):
    """Monumental 100 m Masjid al-Haram exterior wall (z=-42.5), grand portal & open bronze doors."""
    objs = []
    bm_stone = bmesh.new()
    bm_trim = bmesh.new()
    bm_alcove = bmesh.new()
    bm_portal_glow = bmesh.new()
    bm_bronze = bmesh.new()
    bm_gold = bmesh.new()
    bm_gold_rel = bmesh.new()

    # Main Haram facade wall: x in [-50, 50], z in [-44.5, -40.5], y in [0, 16.5]
    _tbox(bm_stone, -50.0, 50.0, 0.0, 16.5, -44.5, -40.5)
    # Horizontal molded plinth, mid gallery cornice & upper frieze
    _tbox(bm_trim, -50.2, 50.2, 0.0, 0.75, -40.55, -40.25)
    _tbox(bm_trim, -50.3, 50.3, 8.35, 8.95, -40.55, -40.05)
    _tbox(bm_gold, -50.25, 50.25, 8.58, 8.72, -40.10, -39.98)
    _tbox(bm_trim, -50.3, 50.3, 15.65, 16.50, -40.55, -39.95)
    _tbox(bm_gold, -50.25, 50.25, 15.95, 16.12, -40.02, -39.90)

    # Crenelated Islamic merlon parapet along roofline (y=16.5..17.45)
    merlon_step = 2.5 if lod == 0 else 5.0
    x = -49.0
    while x <= 49.01:
        _tbox(bm_trim, x - 0.62, x + 0.62, 16.50, 17.35, -40.65, -40.12)
        x += merlon_step

    # Rhythmic recessed pointed Islamic arched alcoves (ground + upper clerestory gallery)
    arch_segs = 4 if lod == 0 else 3
    for bx in range(-48, 49, 4):
        if abs(bx) < 7:
            continue
        # Ground-floor tall pointed Islamic arched alcove
        _add_pointed_arch_fill(bm_alcove, bx, 0.75, 5.1, -40.42, 2.75, 1.95, 0.16, segs=arch_segs)
        _add_pointed_arch_profile(bm_trim, bx, 5.1, -40.32, 2.75, 1.95, 0.28, 0.34, segs=arch_segs)
        # Engaged flanking marble colonnettes
        for side in (-1.48, 1.48):
            _tcyl(bm_trim, bx + side, 0.75, 5.15, -40.32, 0.17, 0.15, segs=6)
            _tbox(bm_gold, bx + side - 0.20, bx + side + 0.20, 5.05, 5.25, -40.52, -40.12)

        # Upper clerestory gallery twin arches (y in [9.5, 14.3])
        if lod == 0:
            for sub in (-0.85, 0.85):
                _add_pointed_arch_fill(bm_alcove, bx + sub, 9.6, 12.6, -40.42, 1.28, 1.05, 0.14, segs=3)
                _add_pointed_arch_profile(bm_trim, bx + sub, 12.6, -40.34, 1.28, 1.05, 0.16, 0.24, segs=3)
            _tcyl(bm_trim, bx, 9.6, 12.65, -40.32, 0.12, 0.11, segs=6)
        else:
            _tbox(bm_alcove, bx - 1.25, bx + 1.25, 9.8, 13.6, -40.48, -40.34)
            _tbox(bm_trim, bx - 1.45, bx + 1.45, 13.6, 14.0, -40.50, -40.20)

    # Grand Haram Portal (Pishtaq): x in [-5.2, 5.2], z=-40.2, h=14.8 m
    # Left & right monumental portal piers
    _tbox(bm_trim, -5.25, -2.75, 0.0, 14.5, -41.0, -39.58)
    _tbox(bm_trim, 2.75, 5.25, 0.0, 14.5, -41.0, -39.58)
    # Upper pishtaq entablature above portal arch
    _tbox(bm_trim, -5.25, 5.25, 11.2, 14.8, -41.0, -39.58)
    # Stepped ornamental portal crown cornice & crest
    _tbox(bm_trim, -5.65, 5.65, 14.70, 15.30, -41.1, -39.32)
    _tbox(bm_gold, -5.45, 5.45, 14.20, 14.48, -39.62, -39.46)
    _tbox(bm_gold, -5.50, 5.50, 15.30, 15.65, -40.40, -39.48)
    # Sculpted gilded spandrel relief panel framing the grand pointed arch
    _tbox(bm_gold_rel, -3.50, 3.50, 9.5, 13.8, -39.68, -39.54)
    # Protruding grand pointed portal archivolt
    _add_pointed_arch_profile(bm_trim, 0.0, 6.2, -39.52, 5.6, 3.6, 0.55, 0.56, segs=8 if lod == 0 else 5)
    _add_pointed_arch_profile(bm_gold, 0.0, 6.2, -39.42, 5.2, 3.35, 0.16, 0.22, segs=8 if lod == 0 else 5)
    # Flanking portal columns
    for sx in (-4.85, -3.05, 3.05, 4.85):
        _tcyl(bm_trim, sx, 0.6, 13.8, -39.55, 0.26, 0.24, segs=10 if lod == 0 else 6)
        _tbox(bm_gold, sx - 0.32, sx + 0.32, 13.7, 14.1, -39.88, -39.24)

    # Warmly glowing golden arched entrance corridor (x in [-2.5, 2.5], y in [0, 9], z=-39.65..-40.6)
    _add_pointed_arch_fill(bm_portal_glow, 0.0, 0.02, 6.0, -40.25, 5.2, 3.2, 0.22, segs=8 if lod == 0 else 5)
    # Illuminated portal threshold carpet/glow floor & soffit reveals
    _tbox(bm_portal_glow, -2.55, 2.55, 0.01, 0.06, -40.30, -39.52)

    # Ornate dark-bronze & gilded geometric double ceremonial gate doors swung partly open (~40 deg)
    door_w = 2.25
    door_h = 6.70
    door_t = 0.18
    for side in (-1, 1):
        hinge_x = side * 2.60
        hinge_z = -39.62
        # Swing inward into corridor (-z) so doors stay strictly behind z <= -39.55
        ang = side * math.radians(40.0)
        # Door center offset along swung leaf toward center/inward
        dx = -side * (door_w * 0.5) * math.cos(abs(ang))
        dz = -(door_w * 0.5) * math.sin(abs(ang))
        dc = three_to_bl(hinge_x + dx, door_h * 0.5, hinge_z + dz)
        add_box(bm_bronze, dc, (door_w, door_t, door_h), rot_z=ang)
        # Gilded decorative relief panels inset on both faces of each leaf
        add_box(bm_gold_rel, dc + Vector((0.0, 0.0, 0.75)), (door_w * 0.72, door_t + 0.05, 2.3), rot_z=ang)
        add_box(bm_gold_rel, dc + Vector((0.0, 0.0, -1.65)), (door_w * 0.72, door_t + 0.05, 1.9), rot_z=ang)
        # Gilded knocker medallion
        add_box(bm_gold, dc + Vector((0.0, 0.0, -0.30)), (0.36, door_t + 0.10, 0.36), rot_z=ang)

    parts = [
        (bm_stone, f'_haram_stone_l{lod}', mats['stone_haram'], False, 0.22, True),
        (bm_trim, f'_haram_trim_l{lod}', mats['marble_trim'], False, 0.30, True),
        (bm_alcove, f'_haram_alcove_l{lod}', mats['haram_alcove'], False, 0.4, False),
        (bm_portal_glow, f'_haram_glow_l{lod}', mats['portal_glow'], False, 0.4, False),
        (bm_bronze, f'_haram_bronze_l{lod}', mats['bronze'], False, 0.5, False),
        (bm_gold, f'_haram_gold_l{lod}', mats['gold'], True, 0.5, False),
        (bm_gold_rel, f'_haram_gold_rel_l{lod}', mats['gold_relief'], False, 0.45, False),
    ]
    for bm, name, mat, smooth, uv_s, ao in parts:
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_box_project(obj, scale=uv_s)
        if ao:
            bake_vertex_ao(obj, strength=0.25, min_val=0.65)
        objs.append(obj)
    return objs


def _build_minarets(col, mats, lod=0):
    """Twin soaring 65 m sculpted multi-tiered Hijazi minarets at (+-9, 0, -42)."""
    objs = []
    bm_stone = bmesh.new()
    bm_trim = bmesh.new()
    bm_gold = bmesh.new()
    bm_glow = bmesh.new()

    oct_s = 8
    cyl_s = 12 if lod == 0 else 8

    for mx in (-9.0, 9.0):
        mz = -42.0
        # 1. Square stone base rising through Haram roofline (y=0..17.5)
        _tbox(bm_stone, mx - 2.35, mx + 2.35, 0.0, 17.2, mz - 2.35, mz + 2.35)
        _tbox(bm_trim, mx - 2.55, mx + 2.55, 16.8, 17.6, mz - 2.55, mz + 2.55)
        # Transition chamfer to octagonal shaft
        _tcyl(bm_trim, mx, 17.6, 19.2, mz, 2.45, 1.92, segs=oct_s, rot_y=math.pi / 8.0)

        # 2. First tall octagonal shaft (y=19.2..35.0)
        _tcyl(bm_stone, mx, 19.2, 35.0, mz, 1.88, 1.72, segs=oct_s, rot_y=math.pi / 8.0)
        # Subtle mid-shaft ornamental belt
        _tcyl(bm_gold, mx, 26.8, 27.3, mz, 1.88, 1.88, segs=oct_s, rot_y=math.pi / 8.0)

        # 3. First carved muqarnas balcony (y=35.0..38.4)
        _tcyl(bm_trim, mx, 35.0, 36.1, mz, 1.72, 2.08, segs=cyl_s)
        _tcyl(bm_trim, mx, 36.1, 37.0, mz, 2.08, 2.52, segs=cyl_s)
        _tcyl(bm_gold, mx, 36.9, 37.25, mz, 2.58, 2.58, segs=cyl_s)
        _tcyl(bm_trim, mx, 37.25, 38.45, mz, 2.48, 2.52, segs=cyl_s)
        # Warm illuminated gallery band inside first balcony
        _tcyl(bm_glow, mx, 38.45, 39.4, mz, 1.56, 1.56, segs=oct_s)

        # 4. Second octagonal shaft with glowing gallery windows (y=38.4..48.4)
        _tcyl(bm_stone, mx, 38.4, 48.4, mz, 1.54, 1.44, segs=oct_s, rot_y=math.pi / 8.0)
        if lod == 0:
            for k in range(8):
                ang = k * (math.tau / 8.0)
                wx = mx + math.cos(ang) * 1.46
                wz = mz + math.sin(ang) * 1.46
                add_box(bm_glow, three_to_bl(wx, 43.4, wz), (0.50, 0.16, 2.2), rot_z=-ang + math.pi * 0.5)

        # 5. Second carved muqarnas balcony (y=48.4..51.2)
        _tcyl(bm_trim, mx, 48.4, 49.4, mz, 1.44, 1.98, segs=cyl_s)
        _tcyl(bm_gold, mx, 49.35, 49.68, mz, 2.15, 2.15, segs=cyl_s)
        _tcyl(bm_trim, mx, 49.68, 50.85, mz, 2.08, 2.12, segs=cyl_s)

        # 6. Arched open lantern pavilion crown (y=50.8..56.8)
        _tcyl(bm_glow, mx, 50.85, 56.2, mz, 0.96, 0.96, segs=cyl_s)
        n_cols = 8 if lod == 0 else 6
        for k in range(n_cols):
            ang = k * (math.tau / n_cols)
            cx = mx + math.cos(ang) * 1.24
            cz = mz + math.sin(ang) * 1.24
            _tcyl(bm_trim, cx, 50.85, 56.2, cz, 0.13, 0.11, segs=6)
        _tcyl(bm_trim, mx, 56.1, 57.1, mz, 1.38, 1.44, segs=cyl_s)
        _tcyl(bm_gold, mx, 56.85, 57.20, mz, 1.48, 1.48, segs=cyl_s)

        # 7. Sculpted ribbed/ogive dome (y=57.2..62.0) built via lofted rings
        dome_steps = 6 if lod == 0 else 4
        rings = []
        for s in range(dome_steps + 1):
            t = s / dome_steps
            y = 57.2 + t * 4.8
            # Graceful pointed Hijazi ogive profile
            r = 1.32 * math.sin((1.0 - t) * math.pi * 0.5) ** 0.72 * (1.0 + 0.14 * math.sin(t * math.pi))
            r = max(0.08, r)
            ring = []
            for k in range(cyl_s):
                ang = k / cyl_s * math.tau
                rib = 1.0 + (0.04 if (lod == 0 and k % 2 == 0) else 0.0)
                ring.append(bm_gold.verts.new(three_to_bl(mx + math.cos(ang) * r * rib, y, mz + math.sin(ang) * r * rib)))
            rings.append(ring)
        loft_rings(bm_gold, rings, closed_u=True, cap_start=False, cap_end=True)

        # 8. Gleaming golden spire & crescent reaching y=65.5 m
        _add_crescent_finial(bm_gold, mx, 61.8, mz, scale=1.15, segs=8 if lod == 0 else 6)

    parts = [
        (bm_stone, f'_minaret_stone_l{lod}', mats['stone_haram'], False, 0.18, True),
        (bm_trim, f'_minaret_trim_l{lod}', mats['marble_trim'], True, 0.25, True),
        (bm_gold, f'_minaret_gold_l{lod}', mats['gold'], True, 0.4, False),
        (bm_glow, f'_minaret_glow_l{lod}', mats['window_warm'], True, 0.4, False),
    ]
    for bm, name, mat, smooth, uv_s, ao in parts:
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_box_project(obj, scale=uv_s)
        if ao:
            bake_vertex_ao(obj, strength=0.22, min_val=0.68)
        objs.append(obj)
    return objs


def _build_clock_tower(col, mats, lod=0):
    """Distant iconic Makkah Clock Tower silhouette at (42, 0, -95) rising 125+ m."""
    objs = []
    bm_stone = bmesh.new()
    bm_gold = bmesh.new()
    bm_clock = bmesh.new()
    bm_win = bmesh.new()

    cx, cz = 42.0, -95.0
    # Stepped classical granite/limestone tower tiers
    _tbox(bm_stone, cx - 10.5, cx + 10.5, 0.0, 42.0, cz - 10.5, cz + 10.5)     # lower podium
    _tbox(bm_stone, cx - 8.6, cx + 8.6, 42.0, 84.0, cz - 8.6, cz + 8.6)        # main shaft
    _tbox(bm_stone, cx - 7.4, cx + 7.4, 84.0, 108.5, cz - 7.4, cz + 7.4)       # clock housing
    # Decorative gold setback cornices
    for y, hw in ((42.0, 10.9), (84.0, 9.0), (108.5, 7.9)):
        _tbox(bm_gold, cx - hw, cx + hw, y - 0.55, y + 0.55, cz - hw, cz + hw)

    # Corner buttress turrets flanking the clock tier
    if lod == 0:
        for sx in (-7.4, 7.4):
            for sz in (-7.4, 7.4):
                _tbox(bm_stone, cx + sx - 1.1, cx + sx + 1.1, 42.0, 110.5, cz + sz - 1.1, cz + sz + 1.1)
                _tcyl(bm_gold, cx + sx, 110.5, 113.5, cz + sz, 1.0, 0.1, segs=6)

    # Glowing emerald-white circular clock face (r=5.2 m at (42, 100, -87.7)) facing +z toward plaza
    # Note: cylinder axis in Blender is Z; rotate around X by +90 deg so cylinder faces Blender -Y (Three.js +Z)
    dial_c = three_to_bl(cx, 100.0, -87.6)
    dial_segs = 24 if lod == 0 else 14
    mat_dial = Matrix.Translation(dial_c) @ Matrix.Rotation(math.pi * 0.5, 4, 'X')
    bmesh.ops.create_cone(
        bm_clock,
        cap_ends=True,
        cap_tris=False,
        segments=dial_segs,
        radius1=5.2,
        radius2=5.2,
        depth=0.45,
        matrix=mat_dial,
    )
    # Gilded bezel ring around clock face
    mat_ring = Matrix.Translation(three_to_bl(cx, 100.0, -87.75)) @ Matrix.Rotation(math.pi * 0.5, 4, 'X')
    bmesh.ops.create_cone(
        bm_gold,
        cap_ends=True,
        cap_tris=False,
        segments=dial_segs,
        radius1=5.75,
        radius2=5.75,
        depth=0.42,
        matrix=mat_ring,
    )
    # Gilded clock hands + 12 hour markers
    add_box(bm_gold, three_to_bl(cx, 101.6, -87.30), (0.36, 0.20, 3.6))  # minute hand (12 o'clock)
    add_box(bm_gold, three_to_bl(cx + 1.1, 100.4, -87.28), (2.4, 0.20, 0.42), rot_z=0.0)  # hour hand
    _tsphere(bm_gold, cx, 100.0, -87.25, 0.55, segs=8, rings=5)
    if lod == 0:
        for h in range(12):
            ang = h / 12.0 * math.tau
            hx = cx + math.sin(ang) * 4.45
            hy = 100.0 + math.cos(ang) * 4.45
            _tbox(bm_gold, hx - 0.18, hx + 0.18, hy - 0.18, hy + 0.18, -87.40, -87.25)

    # Upper jewel pavilion & glowing lantern crown (y=108.5..118.5)
    _tcyl(bm_stone, cx, 108.5, 114.5, cz, 5.4, 4.4, segs=8, rot_y=math.pi / 8.0)
    _tcyl(bm_win, cx, 114.5, 118.5, cz, 3.6, 3.0, segs=8, rot_y=math.pi / 8.0)
    _tcyl(bm_gold, cx, 118.5, 121.2, cz, 3.2, 0.6, segs=8, rot_y=math.pi / 8.0)
    # Tall gilded crescent spire reaching y=127 m
    _add_crescent_finial(bm_gold, cx, 120.8, cz, scale=2.1, segs=8 if lod == 0 else 6)

    parts = [
        (bm_stone, f'_clock_stone_l{lod}', mats['stone_clock'], False, 0.12, True),
        (bm_gold, f'_clock_gold_l{lod}', mats['gold'], True, 0.3, False),
        (bm_clock, f'_clock_face_l{lod}', mats['clock_face'], True, 0.2, False),
        (bm_win, f'_clock_win_l{lod}', mats['window_warm'], True, 0.2, False),
    ]
    for bm, name, mat, smooth, uv_s, ao in parts:
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_box_project(obj, scale=uv_s)
        if ao:
            bake_vertex_ao(obj, strength=0.20, min_val=0.70)
        objs.append(obj)
    return objs


def _build_lamp_posts(col, mats, lod=0):
    """12 ornate cast-bronze Islamic plaza lamp posts at x=+-14, z in {4, -4, -12, -20, -28, -36}."""
    objs = []
    bm_bronze = bmesh.new()
    bm_gold = bmesh.new()
    bm_glass = bmesh.new()

    zs = [4.0, -4.0, -12.0, -20.0, -28.0, -36.0]
    shaft_segs = 8 if lod == 0 else 6
    globe_segs = 8 if lod == 0 else 6
    globe_rings = 5 if lod == 0 else 4

    for lz in zs:
        for lx in (-14.0, 14.0):
            # Cast-bronze stepped pedestal (strictly within +-0.25 m collision footprint)
            _tbox(bm_bronze, lx - 0.24, lx + 0.24, 0.0, 0.45, lz - 0.24, lz + 0.24)
            _tcyl(bm_bronze, lx, 0.45, 1.15, lz, 0.22, 0.14, segs=6)
            _tcyl(bm_gold, lx, 1.12, 1.22, lz, 0.16, 0.16, segs=6)
            # Fluted tapered standard shaft up to y=5.85 m
            _tcyl(bm_bronze, lx, 1.22, 5.85, lz, 0.125, 0.075, segs=shaft_segs)
            _tcyl(bm_gold, lx, 5.20, 5.34, lz, 0.14, 0.14, segs=shaft_segs)
            _tcyl(bm_bronze, lx, 5.80, 6.02, lz, 0.13, 0.22, segs=shaft_segs)

            # Central top warm frosted glowing glass lantern globe (y=6.34)
            _tsphere(bm_glass, lx, 6.32, lz, 0.34, segs=globe_segs, rings=globe_rings)
            _tcyl(bm_gold, lx, 6.60, 6.82, lz, 0.18, 0.02, segs=6)

            if lod == 0:
                # Twin scrolled Islamic lantern bracket arms extending along +-Z
                for dir_z in (-1.0, 1.0):
                    pts = [
                        three_to_bl(lx, 5.25, lz + dir_z * 0.06),
                        three_to_bl(lx, 5.55, lz + dir_z * 0.42),
                        three_to_bl(lx, 5.72, lz + dir_z * 0.72),
                        three_to_bl(lx, 5.52, lz + dir_z * 0.78),
                    ]
                    add_tube(bm_bronze, pts, 0.032, segs=4, closed_caps=True, ref_up=(1.0, 0.0, 0.0))
                    _tcyl(bm_gold, lx, 5.42, 5.54, lz + dir_z * 0.78, 0.11, 0.14, segs=6)
                    _tsphere(bm_glass, lx, 5.74, lz + dir_z * 0.78, 0.23, segs=7, rings=5)
                    _tcyl(bm_gold, lx, 5.94, 6.10, lz + dir_z * 0.78, 0.11, 0.015, segs=5)

    for bm, name, mat, smooth in (
        (bm_bronze, f'_lamps_bronze_l{lod}', mats['bronze'], True),
        (bm_gold, f'_lamps_gold_l{lod}', mats['gold'], True),
        (bm_glass, f'_lamps_glass_l{lod}', mats['lamp_glass'], True),
    ):
        obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
        uv_cylindrical(obj, scale_u=1.0, scale_v=1.0)
        objs.append(obj)
    return objs


def _build_lod(col, mats, lod):
    """Build either LOD0 or LOD1 as one cleanly joined multi-material mesh."""
    parts = []
    parts.extend(_build_plaza(col, mats, lod=lod))
    parts.extend(_build_hotel(col, mats, lod=lod))
    parts.extend(_build_haram_facade(col, mats, lod=lod))
    parts.extend(_build_minarets(col, mats, lod=lod))
    parts.extend(_build_clock_tower(col, mats, lod=lod))
    parts.extend(_build_lamp_posts(col, mats, lod=lod))
    return join_objects(parts, f'makkah_LOD{lod}', col=col)


# ------------------------------------------------------------------ public API
def build_makkah(col):
    """Build `makkah_LOD0` and `makkah_LOD1` into `col` and return (lod0, lod1)."""
    mats = _make_materials()
    lod0 = _build_lod(col, mats, lod=0)
    lod1 = _build_lod(col, mats, lod=1)
    return lod0, lod1


def export_makkah():
    """Reset scene, build Makkah LOD0/LOD1, export Draco WebP GLB & render preview PNG."""
    ensure_dirs()
    reset_scene()
    col = make_collection('EnvMakkah')

    lod0, lod1 = build_makkah(col)
    tris0 = tri_count(lod0)
    tris1 = tri_count(lod1)

    size_bytes = export_glb([lod0, lod1], OUT_GLB, animations=False, vertex_colors=True)
    size_kb = round(size_bytes / 1024.0, 1)

    # Render 2-panel verification sheet: (L) Plaza, Haram Portal, Twin Minarets & Clock Tower; (R) Hotel Portico, Counter & Signboard Frame
    lod1.hide_render = True
    views = [
        (three_to_bl(-22.0, 14.0, 18.0), three_to_bl(8.0, 26.0, -44.0), 19),
        (three_to_bl(-16.5, 8.5, -5.5), three_to_bl(-1.5, 7.5, 16.5), 24),
    ]
    tiles = []
    tmp_files = []
    try:
        for idx, (eye, target, lens) in enumerate(views):
            with tempfile.NamedTemporaryFile(suffix=f'_makkah_{idx}.png', delete=False) as tf:
                tmp_png = tf.name
            tmp_files.append(tmp_png)
            preview.render_shot(
                eye=eye,
                target=target,
                out_path=tmp_png,
                res=(640, 520),
                lens=lens,
                world_color=(0.30, 0.39, 0.58),
            )
            img = bpy.data.images.load(tmp_png, check_existing=False)
            w, h = img.size[0], img.size[1]
            arr = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(arr)
            tiles.append(arr.reshape((h, w, 4)))
            bpy.data.images.remove(img)

        sheet = np.concatenate(tiles, axis=1)
        sh, sw = sheet.shape[:2]
        out_img = bpy.data.images.new('_MakkahPreviewSheet', sw, sh, alpha=True)
        out_img.pixels.foreach_set(sheet.ravel())
        out_img.filepath_raw = str(OUT_PREVIEW)
        out_img.file_format = 'PNG'
        out_img.save()
        bpy.data.images.remove(out_img)
    finally:
        for f in tmp_files:
            if os.path.exists(f):
                os.remove(f)

    stats = {
        'key': 'makkah',
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
        f"MAKKAH_OK tris0={tris0}/{BUDGET_LOD0_TRIS} tris1={tris1}/{BUDGET_LOD1_TRIS} "
        f"size={size_kb:.1f}/{BUDGET_KB}KB"
    )
    return stats


if __name__ == '__main__':
    export_makkah()
