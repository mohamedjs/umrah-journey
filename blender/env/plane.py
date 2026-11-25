"""Chapter 3 — Commercial Airliner Cabin environment for umrah-journey.

Exports `public/models/env/plane.glb` containing:
- `plane_LOD0` + `plane_LOD1` (curved composite fuselage shell with ribbed ceiling arch
  and warm cove lights, navy carpet & burgundy center aisle runner, 30 sculpted oval sunset
  windows, contoured curved overhead luggage bins with latches & under-bin LEDs, front
  bulkhead with draped burgundy divider curtain, rear bulkhead, 14 rows x 6 contoured
  airline seats with reclined backrests/headrests/antimacassars/armrests/leg frames,
  rear lavatory compartment matching LAV=[1.3,3.6,10.0,12.6] with bifold door & glowing
  plaque housing, and rear stainless-steel galley counter + rolling beverage cart).
Also renders verification preview to `blender/previews/env_plane.png`.
"""
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blender.lib import preview, textures
from blender.lib.common import (
    MODELS_ENV,
    PREVIEWS,
    bake_vertex_ao,
    bm_to_obj,
    ensure_dirs,
    export_glb,
    join_objects,
    loft_rings,
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
    c_bl = three_to_bl(*center_t)
    rot = (
        Matrix.Rotation(float(rot_y), 4, 'Z')
        @ Matrix.Rotation(float(rot_x), 4, 'X')
        @ Matrix.Rotation(float(-rot_z), 4, 'Y')
    )
    return Matrix.Translation(c_bl) @ rot


def _add_box_t(bm, center_t, size_t, rot_y=0.0, rot_x=0.0, rot_z=0.0, bevel=0.0, bevel_segs=1):
    sx, sy, sz = float(size_t[0]), float(size_t[1]), float(size_t[2])
    m = _mat_three(center_t, rot_y=rot_y, rot_x=rot_x, rot_z=rot_z) @ Matrix.Diagonal((sx, sz, sy, 1.0))
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


def _add_cyl_t(bm, center_t, r_bot, height, segs=10, r_top=None, rot_y=0.0, rot_x=0.0, rot_z=0.0, cap=True):
    m = _mat_three(center_t, rot_y=rot_y, rot_x=rot_x, rot_z=rot_z)
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


def _make_part(bm, name, col, mat, smooth=False, uv_scale=0.5, ao=True, ao_strength=0.24, ao_min=0.68):
    obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
    uv_box_project(obj, scale=uv_scale)
    if ao:
        bake_vertex_ao(obj, strength=ao_strength, min_val=ao_min)
    else:
        _set_white_vcol(obj)
    return obj


# ------------------------------------------------------------------ Materials
def _create_materials():
    carpet_alb = textures.tex_fabric_weave(size=256, name='plane_carpet_navy', color='#3e4a5e', contrast=0.07)
    runner_alb = textures.tex_fabric_weave(size=256, name='plane_runner_burg', color='#7a2c38', contrast=0.07)
    seat_alb = textures.tex_fabric_weave(size=256, name='plane_seat_navy', color='#243559', contrast=0.07)
    linen_alb = textures.tex_fabric_weave(size=128, name='plane_antimacassar', color='#f1ece2', contrast=0.04)

    return {
        'cabin_shell': make_pbr_material(
            'mat_plane_shell',
            color='#eceee9',
            roughness=0.52,
            double_sided=True,
            use_vcol=True,
        ),
        'cabin_cream': make_pbr_material(
            'mat_plane_cream',
            color='#e7e2d7',
            roughness=0.46,
            use_vcol=True,
        ),
        'cabin_trim': make_pbr_material(
            'mat_plane_trim',
            color='#c9c4b8',
            roughness=0.42,
            metallic=0.12,
            use_vcol=True,
        ),
        'carpet_navy': make_pbr_material(
            'mat_plane_carpet',
            roughness=0.92,
            image=carpet_alb,
            use_vcol=True,
            uv_scale=(1.2, 1.2),
        ),
        'runner_burgundy': make_pbr_material(
            'mat_plane_runner',
            roughness=0.88,
            image=runner_alb,
            double_sided=True,
            use_vcol=True,
            uv_scale=(1.4, 1.4),
        ),
        'seat_navy': make_pbr_material(
            'mat_plane_seat',
            roughness=0.82,
            image=seat_alb,
            use_vcol=True,
            uv_scale=(2.0, 2.0),
        ),
        'seat_shell': make_pbr_material(
            'mat_plane_seat_shell',
            color='#d8dce0',
            roughness=0.44,
            use_vcol=True,
        ),
        'antimacassar': make_pbr_material(
            'mat_plane_headrest',
            roughness=0.88,
            image=linen_alb,
            use_vcol=True,
            uv_scale=(2.0, 2.0),
        ),
        'metal_dark': make_pbr_material(
            'mat_plane_metal_dark',
            color='#2b313a',
            roughness=0.40,
            metallic=0.72,
            use_vcol=True,
        ),
        'stainless': make_pbr_material(
            'mat_plane_stainless',
            color='#c6ccd2',
            roughness=0.26,
            metallic=0.88,
            use_vcol=True,
        ),
        'gold_crest': make_pbr_material(
            'mat_plane_gold',
            color='#cfa246',
            roughness=0.28,
            metallic=0.88,
            use_vcol=False,
        ),
        'sunset_glow': make_pbr_material(
            'mat_plane_sunset',
            color='#ffc87d',
            roughness=0.12,
            emissive='#ff9644',
            emissive_strength=2.2,
            double_sided=True,
            use_vcol=False,
        ),
        'cove_led': make_pbr_material(
            'mat_plane_cove_led',
            color='#fff7e6',
            roughness=0.20,
            emissive='#ffefd0',
            emissive_strength=1.55,
            use_vcol=False,
        ),
        'lav_plaque': make_pbr_material(
            'mat_plane_lav_plaque',
            color='#ffe8b8',
            roughness=0.18,
            emissive='#ffc662',
            emissive_strength=1.45,
            use_vcol=False,
        ),
        'vacant_green': make_pbr_material(
            'mat_plane_vacant',
            color='#3ad16c',
            roughness=0.25,
            emissive='#24b856',
            emissive_strength=1.2,
            use_vcol=False,
        ),
    }


def _cabin_arch_xy(ang):
    """Parametric fuselage cross-section (r ~ 4.02 m at window line y=2.3, crown y=4.78)."""
    cx = math.cos(ang) * 4.02
    cy = 2.20 + math.sin(ang) * 3.15
    if cy > 4.20:
        cy = 4.20 + (cy - 4.20) * 0.54
    return cx, cy


# ------------------------------------------------------------------ Cabin Fuselage, Floor, Windows & Bins
def _build_cabin_shell_and_floor(col, mats):
    parts = []

    # 1. Curved composite airliner fuselage cabin shell (len = 30 m, centered (0, 2.2, -1.5))
    bm_sh = bmesh.new()
    segs_a = 24
    a_start = -math.radians(34.0)
    a_end = math.pi + math.radians(34.0)
    z_stations = [-16.2, -9.0, -1.5, 6.0, 13.4]
    rings = []
    for tz in z_stations:
        ring = []
        for k in range(segs_a + 1):
            ang = a_start + (k / segs_a) * (a_end - a_start)
            cx, cy = _cabin_arch_xy(ang)
            ring.append(bm_sh.verts.new(three_to_bl(cx, cy, tz)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(segs_a):
            bm_sh.faces.new((r0[k], r1[k], r1[k + 1], r0[k + 1]))
    parts.append(_make_part(bm_sh, '_cabin_shell', col, mats['cabin_shell'], smooth=True, uv_scale=0.25, ao_strength=0.18, ao_min=0.78))

    # Sculpted ceiling arch ribs (cleanly across ceiling crown y > 4.35, plus subtle window-pier vertical ribs)
    bm_rib = bmesh.new()
    for rz in [(-14.2 + i * 1.6) for i in range(16)]:
        # Ceiling arch panel ribs between overhead bins (ang from 56 deg to 124 deg)
        n_c = 6
        pts = [_cabin_arch_xy(math.radians(56.0 + (k / n_c) * 68.0)) for k in range(n_c + 1)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1) - 0.03
            seg_len = math.hypot(x1 - x0, y1 - y0)
            tilt = math.atan2(y1 - y0, x1 - x0)
            _add_box_t(bm_rib, (mx, my, rz), (seg_len + 0.02, 0.06, 0.07), rot_z=tilt)
        # Curved sidewall panel seam ribs between windows following fuselage arch (ang -18..+28 deg)
        for side in (-1.0, 1.0):
            s_angs = [math.radians(-18.0 + j * 15.0) for j in range(4)]
            s_pts = [(_cabin_arch_xy(a)[0] * side * 0.992, _cabin_arch_xy(a)[1]) for a in s_angs]
            for (x0, y0), (x1, y1) in zip(s_pts, s_pts[1:]):
                mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
                seg_len = math.hypot(x1 - x0, y1 - y0)
                tilt = math.atan2(y1 - y0, x1 - x0)
                _add_box_t(bm_rib, (mx, my, rz), (seg_len + 0.02, 0.05, 0.055), rot_z=tilt)
    # Lower dado / air-vent strip along both sidewalls
    for sx in (-1.0, 1.0):
        _add_box_t(bm_rib, (sx * 3.56, 0.16, -1.5), (0.14, 0.30, 29.0))
    parts.append(_make_part(bm_rib, '_cabin_ribs', col, mats['cabin_trim'], smooth=False, uv_scale=0.5, ao_strength=0.22))

    # Recessed warm ceiling center cove valance & linear LED strips
    bm_val = bmesh.new()
    for sx in (-0.70, 0.70):
        _add_box_t(bm_val, (sx, 4.58, -2.0), (0.14, 0.18, 26.8))
    parts.append(_make_part(bm_val, '_ceiling_valance', col, mats['cabin_cream'], smooth=False, uv_scale=0.4, ao_strength=0.18))

    bm_led = bmesh.new()
    _add_box_t(bm_led, (0.0, 4.56, -2.0), (1.14, 0.04, 26.4))
    # Under-bin warm LED strips along both sides (y = 3.58)
    for sx in (-1.0, 1.0):
        _add_box_t(bm_led, (sx * 2.40, 3.57, -3.5), (0.06, 0.04, 24.0))
    # Emergency floor aisle guide strips along x = ±0.57
    for sx in (-0.57, 0.57):
        _add_box_t(bm_led, (sx, 0.014, -2.8), (0.025, 0.012, 23.2))
    parts.append(_make_part(bm_led, '_cabin_leds', col, mats['cove_led'], smooth=False, uv_scale=0.4, ao=False))

    # 2. Cabin floor (y = 0) with textured navy carpet + burgundy center aisle runner (x in [-0.55, 0.55])
    bm_fl = bmesh.new()
    _add_box_t(bm_fl, (0.0, -0.05, -1.5), (7.6, 0.10, 30.0))
    parts.append(_make_part(bm_fl, '_cabin_floor', col, mats['carpet_navy'], smooth=False, uv_scale=0.5, ao_strength=0.18, ao_min=0.76))

    bm_rn = bmesh.new()
    _add_box_t(bm_rn, (0.0, 0.010, -2.8), (1.10, 0.020, 24.0))
    parts.append(_make_part(bm_rn, '_aisle_runner', col, mats['runner_burgundy'], smooth=False, uv_scale=0.6, ao_strength=0.14, ao_min=0.82))

    # 3. Front bulkhead (z = -15.6) + draped burgundy curtain + brass crest + rear bulkhead (z = 12.8)
    bm_bh = bmesh.new()
    _add_box_t(bm_bh, (-2.50, 2.45, -15.62), (3.00, 4.90, 0.20))
    _add_box_t(bm_bh, (2.50, 2.45, -15.62), (3.00, 4.90, 0.20))
    _add_box_t(bm_bh, (0.0, 4.05, -15.62), (2.20, 1.70, 0.20))
    _add_box_t(bm_bh, (0.0, 1.60, -15.78), (2.20, 3.20, 0.08))
    _add_box_t(bm_bh, (0.0, 2.45, 12.82), (8.00, 4.90, 0.22))
    parts.append(_make_part(bm_bh, '_bulkheads', col, mats['cabin_cream'], smooth=False, uv_scale=0.35, ao_strength=0.22))

    bm_bt = bmesh.new()
    _add_box_t(bm_bt, (-1.04, 1.60, -15.50), (0.12, 3.24, 0.10))
    _add_box_t(bm_bt, (1.04, 1.60, -15.50), (0.12, 3.24, 0.10))
    _add_box_t(bm_bt, (0.0, 3.22, -15.50), (2.20, 0.14, 0.10))
    _add_box_t(bm_bt, (0.0, 1.05, 12.68), (5.2, 0.10, 0.06))
    parts.append(_make_part(bm_bt, '_bulkhead_trim', col, mats['cabin_trim'], smooth=False, uv_scale=0.5, ao_strength=0.2))

    bm_cr = bmesh.new()
    _add_cyl_t(bm_cr, (0.0, 3.72, -15.49), 0.24, 0.04, segs=14, rot_x=math.pi / 2.0)
    _add_box_t(bm_cr, (0.0, 3.72, -15.48), (0.86, 0.07, 0.03))
    parts.append(_make_part(bm_cr, '_front_crest', col, mats['gold_crest'], smooth=True, uv_scale=1.0, ao=False))

    # Draped pleated burgundy divider curtain at z = -15.42
    bm_cur = bmesh.new()
    nx, ny = 14, 5
    grid = []
    for iy in range(ny):
        v = iy / (ny - 1)
        ty = 3.16 - v * 3.04
        row = []
        for ix in range(nx):
            u = ix / (nx - 1)
            tx = -0.98 + u * 1.96
            pleat = math.sin(u * 5.5 * math.tau) * (0.055 + 0.025 * v)
            tz = -15.42 + pleat
            row.append(bm_cur.verts.new(three_to_bl(tx, ty, tz)))
        grid.append(row)
    for iy in range(ny - 1):
        for ix in range(nx - 1):
            bm_cur.faces.new((grid[iy][ix], grid[iy][ix + 1], grid[iy + 1][ix + 1], grid[iy + 1][ix]))
    parts.append(_make_part(bm_cur, '_front_curtain', col, mats['runner_burgundy'], smooth=True, uv_scale=1.0, ao_strength=0.24))

    return parts


def _build_windows_and_bins(col, mats):
    """30 sculpted oval recessed sunset windows (x=±3.85, y=2.3) + curved overhead stowage bins."""
    parts = []

    # 1. Sculpted oval recessed passenger window frames + solid glowing sunset panes (15 pairs = 30)
    bm_wf = bmesh.new()
    bm_wg = bmesh.new()
    win_zs = [-15.0 + i * 1.6 for i in range(15)]
    n_oval = 12
    for wz in win_zs:
        for side in (-1.0, 1.0):
            # Sidewall at y=2.30 is at x = side * 4.01 -> place solid molded bezel proud from 4.00 inward to 3.84
            wx_wall = side * 4.00
            wx_front = side * 3.84
            wx_glass = side * 3.94
            wy = 2.30

            # Build closed manifold hollow oval frame (4 rings: outer_wall, outer_front, inner_front, inner_glass)
            r_ow, r_of, r_if, r_ig = [], [], [], []
            r_g0, r_g1 = [], []
            for k in range(n_oval):
                a = k / n_oval * math.tau
                dz = math.cos(a)
                dy = math.sin(a)
                oz, oy = dz * 0.31, dy * 0.43
                iz, iy = dz * 0.23, dy * 0.34
                r_ow.append(bm_wf.verts.new(three_to_bl(wx_wall, wy + oy, wz + oz)))
                r_of.append(bm_wf.verts.new(three_to_bl(wx_front, wy + oy * 0.94, wz + oz * 0.94)))
                r_if.append(bm_wf.verts.new(three_to_bl(wx_front, wy + iy * 1.04, wz + iz * 1.04)))
                r_ig.append(bm_wf.verts.new(three_to_bl(wx_glass, wy + iy, wz + iz)))

                # Solid thin oval sunset glass disc (2 rings -> manifold, never backface culled!)
                r_g0.append(bm_wg.verts.new(three_to_bl(wx_glass - side * 0.02, wy + iy * 1.02, wz + iz * 1.02)))
                r_g1.append(bm_wg.verts.new(three_to_bl(wx_glass + side * 0.02, wy + iy * 1.02, wz + iz * 1.02)))
            loft_rings(bm_wf, [r_ow, r_of, r_if, r_ig], closed_u=True, cap_start=False, cap_end=False)
            loft_rings(bm_wg, [r_g0, r_g1], closed_u=True, cap_start=True, cap_end=True)

    parts.append(_make_part(bm_wf, '_window_frames', col, mats['cabin_cream'], smooth=True, uv_scale=1.0, ao_strength=0.22))
    parts.append(_make_part(bm_wg, '_window_sunset', col, mats['sunset_glow'], smooth=True, uv_scale=1.0, ao=False))

    # 2. Contoured curved overhead luggage bins along both sides (x = ±2.75, y = 4.0, z in [-15.5, 8.5])
    bm_bin = bmesh.new()
    bm_lat = bmesh.new()
    prof_pos = [
        (1.66, 3.70),
        (2.05, 3.58),
        (2.85, 3.60),
        (3.56, 3.76),
        (3.26, 4.30),
        (2.38, 4.46),
        (1.76, 4.38),
    ]
    z_bins = [-15.5 + i * 1.6 for i in range(16)]
    for side in (-1.0, 1.0):
        rings_b = []
        for bz in z_bins:
            ring = []
            pts = prof_pos if side > 0 else [(-px, py) for px, py in reversed(prof_pos)]
            for px, py in pts:
                ring.append(bm_bin.verts.new(three_to_bl(px, py, bz)))
            rings_b.append(ring)
        loft_rings(bm_bin, rings_b, closed_u=True, cap_start=True, cap_end=True)

        # Clean recessed dark latch handles neatly on lower front contour (no poking above bins)
        for i in range(15):
            zc = -14.7 + i * 1.6
            _add_box_t(bm_lat, (side * 1.69, 3.84, zc), (0.05, 0.065, 0.24), rot_z=side * 0.14)
            _add_box_t(bm_lat, (side * 1.71, 3.96, z_bins[i]), (0.03, 0.34, 0.022), rot_z=side * -0.14)
    parts.append(_make_part(bm_bin, '_overhead_bins', col, mats['cabin_cream'], smooth=True, uv_scale=0.4, ao_strength=0.20, ao_min=0.74))
    parts.append(_make_part(bm_lat, '_bin_latches', col, mats['metal_dark'], smooth=False, uv_scale=1.0, ao=False))

    return parts


# ------------------------------------------------------------------ 14 Rows x 6 Contoured Airline Seats
def _add_sculpted_seat(bm_fab, bm_shl, bm_hd, sx, rz):
    """Build one contoured ergonomic airline seat facing -Z with low, clean poly budget (~148 tris)."""
    # 1. Lofted ergonomic cushion + reclined backrest + winged headrest in ONE sleek curved mesh (bm_fab)
    # Profile stations along the seat spine in local (dy, dz) + half-width hw + thickness th:
    # Front waterfall edge -> cushion mid -> lumbar curve -> mid back -> winged headrest top
    spine = [
        # (dy, dz, hw, th_perp_y, th_perp_z)
        (0.54, -0.34, 0.33, 0.07, 0.0),   # front waterfall tip
        (0.62, -0.22, 0.345, 0.10, 0.0),  # front cushion crest
        (0.60, 0.18, 0.34, 0.10, 0.0),    # rear cushion
        (0.84, 0.27, 0.335, 0.0, 0.08),   # lower lumbar
        (1.36, 0.35, 0.33, 0.0, 0.075),   # upper shoulder back
        (1.74, 0.40, 0.31, 0.0, 0.075),   # winged headrest base
        (1.88, 0.42, 0.27, 0.0, 0.06),    # headrest crown
    ]
    # Build closed 6-vert cross-section ring at each station (curved front cushion face + flat back)
    rings = []
    for idx, (dy, dz, hw, ty, tz) in enumerate(spine):
        if idx < 3:
            # Horizontal cushion section (extruded vertically by ±ty, rounded bolsters at ±hw)
            pts = [
                (-hw, dy + ty * 0.65, dz),
                (-hw * 0.7, dy + ty, dz),
                (hw * 0.7, dy + ty, dz),
                (hw, dy + ty * 0.65, dz),
                (hw * 0.92, dy - ty, dz),
                (-hw * 0.92, dy - ty, dz),
            ]
        else:
            # Vertical backrest section (forward face at dz - tz, rear at dz + tz, curved side bolsters)
            bolster = 0.045 if idx >= 5 else 0.025
            pts = [
                (-hw, dy, dz - tz - bolster),
                (-hw * 0.68, dy, dz - tz),
                (hw * 0.68, dy, dz - tz),
                (hw, dy, dz - tz - bolster),
                (hw * 0.92, dy, dz + tz),
                (-hw * 0.92, dy, dz + tz),
            ]
        ring = [bm_fab.verts.new(three_to_bl(sx + px, py, rz + pz)) for px, py, pz in pts]
        rings.append(ring)
    loft_rings(bm_fab, rings, closed_u=True, cap_start=True, cap_end=True)

    # 2. Rear molded composite shell + tray table recess outline (12 tris, crisp flat back)
    _add_box_t(bm_shl, (sx, 1.24, rz + 0.43), (0.60, 0.94, 0.04), rot_x=-0.15)
    # 3. Crisp white linen antimacassar headrest cover draped over top (12 tris)
    _add_box_t(bm_hd, (sx, 1.76, rz + 0.39), (0.46, 0.26, 0.16), rot_x=-0.15)


def _build_airline_seats(col, mats):
    """14 rows (z=-14.0..6.8 step 1.6) x 6 seats (x in {-3.0,-2.2,-1.4, 1.4,2.2,3.0})."""
    parts = []
    rows = [-14.0 + i * 1.6 for i in range(14)]
    xs = [-3.0, -2.2, -1.4, 1.4, 2.2, 3.0]

    bm_fab = bmesh.new()
    bm_shl = bmesh.new()
    bm_hd = bmesh.new()
    bm_arm = bmesh.new()

    for rz in rows:
        for side in (-1.0, 1.0):
            cx_bank = side * 2.20
            # Under-seat crossbeam + 2 sturdy A-frame leg struts per 3-seat bank
            _add_box_t(bm_arm, (cx_bank, 0.46, rz + 0.02), (2.22, 0.07, 0.08))
            for lx in (cx_bank - 0.85, cx_bank + 0.85):
                _add_box_t(bm_arm, (lx, 0.23, rz - 0.06), (0.06, 0.46, 0.07), rot_x=0.14)
                _add_box_t(bm_arm, (lx, 0.23, rz + 0.20), (0.06, 0.46, 0.07), rot_x=-0.16)
                _add_box_t(bm_arm, (lx, 0.025, rz + 0.07), (0.09, 0.05, 0.56))
            # 4 sleek folding armrests per 3-seat cluster (aisle edge at ±1.04 -> clear aisle |x| < 1.0)
            for ax in (side * 1.04, side * 1.80, side * 2.60, side * 3.36):
                _add_box_t(bm_arm, (ax, 0.86, rz + 0.04), (0.06, 0.065, 0.46))
                _add_box_t(bm_arm, (ax, 0.64, rz + 0.24), (0.05, 0.38, 0.06))

        for sx in xs:
            _add_sculpted_seat(bm_fab, bm_shl, bm_hd, sx, rz)

    parts.append(_make_part(bm_fab, '_seats_fabric', col, mats['seat_navy'], smooth=True, uv_scale=1.5, ao_strength=0.25))
    parts.append(_make_part(bm_shl, '_seats_shell', col, mats['seat_shell'], smooth=False, uv_scale=1.0, ao_strength=0.18))
    parts.append(_make_part(bm_hd, '_seats_headrest', col, mats['antimacassar'], smooth=True, uv_scale=1.8, ao_strength=0.14, ao_min=0.84))
    parts.append(_make_part(bm_arm, '_seats_frame', col, mats['metal_dark'], smooth=False, uv_scale=1.0, ao_strength=0.22))

    return parts


# ------------------------------------------------------------------ Rear Lavatory & Galley Cart
def _build_lavatory_and_galley(col, mats):
    """Rear lavatory matching LAV=[1.3, 3.6, 10.0, 12.6], h=3.4 + rear stainless galley & cart at (-2.6, 0, 11.0)."""
    parts = []

    # 1. Lavatory compartment enclosure: x in [1.3, 3.6], z in [10.0, 12.6], y in [0, 3.4]
    bm_lav = bmesh.new()
    _add_box_t(bm_lav, (2.45, 1.70, 11.30), (2.30, 3.40, 2.60), bevel=0.05, bevel_segs=2)
    # Recessed bifold lavatory door panels facing aisle at x = 1.30, z = 11.2
    _add_box_t(bm_lav, (1.28, 1.12, 10.97), (0.04, 2.16, 0.44), bevel=0.01)
    _add_box_t(bm_lav, (1.28, 1.12, 11.43), (0.04, 2.16, 0.44), bevel=0.01)
    _add_box_t(bm_lav, (1.27, 2.24, 11.20), (0.06, 0.08, 1.00), bevel=0.01)
    parts.append(_make_part(bm_lav, '_lavatory_body', col, mats['cabin_cream'], smooth=False, uv_scale=0.45, ao_strength=0.26))

    bm_lhw = bmesh.new()
    _add_box_t(bm_lhw, (1.26, 0.14, 11.20), (0.03, 0.24, 0.90))
    _add_box_t(bm_lhw, (1.255, 1.12, 11.20), (0.02, 2.14, 0.025))
    _add_box_t(bm_lhw, (1.25, 1.18, 10.84), (0.03, 0.30, 0.14), bevel=0.008)
    _add_box_t(bm_lhw, (1.22, 1.18, 10.84), (0.04, 0.16, 0.035), bevel=0.006)
    _add_box_t(bm_lhw, (1.27, 2.48, 11.20), (0.06, 0.26, 0.72), bevel=0.01)
    parts.append(_make_part(bm_lhw, '_lavatory_hw', col, mats['stainless'], smooth=False, uv_scale=1.0, ao_strength=0.2))

    # Warm glowing illuminated lavatory plaque housing (NO baked Arabic text) + green vacant indicator
    bm_lgl = bmesh.new()
    _add_box_t(bm_lgl, (1.235, 2.48, 11.20), (0.02, 0.20, 0.64))
    parts.append(_make_part(bm_lgl, '_lavatory_plaque', col, mats['lav_plaque'], smooth=False, uv_scale=1.0, ao=False))

    bm_vac = bmesh.new()
    _add_box_t(bm_vac, (1.24, 1.38, 10.84), (0.02, 0.07, 0.10))
    parts.append(_make_part(bm_vac, '_lavatory_vacant', col, mats['vacant_green'], smooth=False, uv_scale=1.0, ao=False))

    # 2. Rear stainless-steel galley counter & beverage service cart on wheels at (-2.6, 0, 11.0)
    bm_gst = bmesh.new()
    bm_gdk = bmesh.new()
    _add_box_t(bm_gst, (-3.15, 0.56, 11.45), (0.86, 1.12, 2.35), bevel=0.02)
    _add_box_t(bm_gst, (-3.22, 2.25, 11.45), (0.70, 1.18, 2.30), bevel=0.02)
    _add_box_t(bm_gdk, (-3.05, 1.38, 11.55), (0.48, 0.50, 0.85), bevel=0.015)
    for cz in (10.75, 11.45, 12.15):
        _add_box_t(bm_gdk, (-2.85, 2.05, cz), (0.04, 0.12, 0.08))

    cx, cz = -2.28, 10.95
    _add_box_t(bm_gst, (cx, 0.56, cz), (0.68, 0.94, 1.24), bevel=0.025)
    _add_box_t(bm_gst, (cx, 1.05, cz - 0.60), (0.68, 0.05, 0.04))
    _add_box_t(bm_gst, (cx, 1.05, cz + 0.60), (0.68, 0.05, 0.04))
    _add_box_t(bm_gst, (cx - 0.32, 1.05, cz), (0.04, 0.05, 1.24))
    _add_box_t(bm_gst, (cx + 0.32, 1.05, cz), (0.04, 0.05, 1.24))
    _add_cyl_t(bm_gst, (cx - 0.08, 1.17, cz - 0.25), 0.075, 0.24, segs=10, r_top=0.06)
    _add_cyl_t(bm_gst, (cx + 0.12, 1.13, cz + 0.22), 0.055, 0.16, segs=10, r_top=0.065)

    _add_box_t(bm_gdk, (cx, 0.11, cz), (0.72, 0.06, 1.28), bevel=0.015)
    _add_box_t(bm_gdk, (cx, 0.96, cz - 0.66), (0.46, 0.04, 0.05))
    _add_box_t(bm_gdk, (cx, 0.96, cz + 0.66), (0.46, 0.04, 0.05))
    for wx in (-0.24, 0.24):
        for wz in (-0.48, 0.48):
            _add_cyl_t(bm_gdk, (cx + wx, 0.045, cz + wz), 0.045, 0.06, segs=8, rot_z=math.pi / 2.0)

    parts.append(_make_part(bm_gst, '_galley_steel', col, mats['stainless'], smooth=False, uv_scale=0.6, ao_strength=0.24))
    parts.append(_make_part(bm_gdk, '_galley_dark', col, mats['metal_dark'], smooth=True, uv_scale=1.0, ao_strength=0.22))

    return parts


# ------------------------------------------------------------------ Public API
def build_plane(col):
    """Build Chapter 3 Airliner cabin into `col` and return dict of exported objects."""
    mats = _create_materials()
    all_parts = []
    all_parts.extend(_build_cabin_shell_and_floor(col, mats))
    all_parts.extend(_build_windows_and_bins(col, mats))
    all_parts.extend(_build_airline_seats(col, mats))
    all_parts.extend(_build_lavatory_and_galley(col, mats))

    lod0 = join_objects(all_parts, 'plane_LOD0', col)
    lod1 = make_lod1(lod0, ratio=0.40, name='plane_LOD1')
    return {'lod0': lod0, 'lod1': lod1, 'all': [lod0, lod1]}


def export_plane():
    """Build, export `public/models/env/plane.glb`, and render `blender/previews/env_plane.png`."""
    ensure_dirs()
    reset_scene()
    col = make_collection('EnvPlane')
    built = build_plane(col)

    out_glb = MODELS_ENV / 'plane.glb'
    size_bytes = export_glb(built['all'], out_glb, vertex_colors=True)

    # Render interior cabin preview from rear galley (showing lavatory door, galley cart, seats & sunset windows)
    built['lod1'].hide_render = True
    rig_col = bpy.data.collections.get('_PreviewRig') or bpy.data.collections.new('_PreviewRig')
    if rig_col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(rig_col)
    for idx, (lz, energy) in enumerate(((-10.0, 220.0), (-3.5, 240.0), (3.0, 240.0), (9.8, 260.0))):
        ld = bpy.data.lights.new(f'_PlaneFill_{idx}', type='POINT')
        ld.energy = energy
        ld.shadow_soft_size = 1.2
        ld.use_shadow = False
        ld.color = (1.0, 0.92, 0.80)
        lo = bpy.data.objects.new(f'_PlaneFill_{idx}', ld)
        lo.location = three_to_bl(0.0, 3.95, lz)
        rig_col.objects.link(lo)

    out_png = PREVIEWS / 'env_plane.png'
    preview.render_shot(
        eye=three_to_bl(-0.18, 2.00, 9.75),
        target=three_to_bl(0.05, 1.48, -6.5),
        out_path=out_png,
        res=(1024, 640),
        lens=21,
        world_color=(0.12, 0.16, 0.24),
    )

    t0 = tri_count(built['lod0'])
    t1 = tri_count(built['lod1'])
    print(
        f'PLANE_OK: lod0={t0} tris, lod1={t1} tris, '
        f'glb={size_bytes / 1024:.1f}KB -> {out_glb}'
    )
    return {
        'name': 'plane',
        'glb': str(out_glb),
        'preview': str(out_png),
        'tris_lod0': t0,
        'tris_lod1': t1,
        'bytes': size_bytes,
    }


if __name__ == '__main__':
    export_plane()
