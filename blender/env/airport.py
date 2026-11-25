"""Chapter 2 — International Airport Departures Hall environment for umrah-journey.

Exports `public/models/env/airport.glb` containing:
- `airport_LOD0` + `airport_LOD1` (polished terrazzo floor, glass curtain wall with steel
  mullions, parked commercial jetliner on tarmac apron, vaulted steel-truss ceiling with
  LED strips, check-in counter island with monitors/scales/suitcases/conveyor, 4 clad
  structural columns, 3 rows of contoured waiting chairs, illuminated Gate 12 portal,
  and 3 recessed aluminum signboard housings for Three.js Arabic signs).
Also renders verification preview to `blender/previews/env_airport.png`.
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


def _add_cyl_t(bm, center_t, r_bot, height, segs=12, r_top=None, rot_y=0.0, rot_x=0.0, rot_z=0.0, cap=True):
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


def _make_part(bm, name, col, mat, smooth=False, uv_scale=0.35, ao=True, ao_strength=0.26, ao_min=0.65):
    obj = bm_to_obj(bm, name, col, mat=mat, smooth=smooth)
    uv_box_project(obj, scale=uv_scale)
    if ao:
        bake_vertex_ao(obj, strength=ao_strength, min_val=ao_min)
    else:
        _set_white_vcol(obj)
    return obj


# ------------------------------------------------------------------ Materials
def _create_materials():
    terrazzo_alb = textures.tex_terrazzo(size=512, name='air_terrazzo', tint='#e6ebef')
    wall_alb = textures.tex_plaster_wall(size=256, name='air_acoustic_wall', tint='#e5eaee')
    seat_alb = textures.tex_fabric_weave(size=256, name='air_chair_fabric', color='#304258', contrast=0.06)

    return {
        'terrazzo': make_pbr_material(
            'mat_air_terrazzo',
            roughness=0.24,
            image=terrazzo_alb,
            use_vcol=True,
            uv_scale=(0.45, 0.45),
        ),
        'tarmac': make_pbr_material(
            'mat_air_tarmac',
            color='#484e55',
            roughness=0.90,
            use_vcol=True,
        ),
        'tarmac_yellow': make_pbr_material(
            'mat_air_tarmac_yellow',
            color='#d9a834',
            roughness=0.72,
            use_vcol=False,
        ),
        'curtain_glass': make_pbr_material(
            'mat_air_glass',
            color='#bfe2f7',
            roughness=0.06,
            metallic=0.10,
            alpha=0.22,
            double_sided=False,
            use_vcol=False,
        ),
        'steel_mullion': make_pbr_material(
            'mat_air_steel_mullion',
            color='#4a5460',
            roughness=0.36,
            metallic=0.80,
            use_vcol=True,
        ),
        'aluminum_clad': make_pbr_material(
            'mat_air_aluminum',
            color='#d4dade',
            roughness=0.32,
            metallic=0.78,
            use_vcol=True,
        ),
        'steel_dark': make_pbr_material(
            'mat_air_steel_dark',
            color='#2c333c',
            roughness=0.42,
            metallic=0.72,
            use_vcol=True,
        ),
        'chrome': make_pbr_material(
            'mat_air_chrome',
            color='#dce2e6',
            roughness=0.16,
            metallic=0.95,
            use_vcol=False,
        ),
        'wall_panel': make_pbr_material(
            'mat_air_wall',
            roughness=0.68,
            image=wall_alb,
            use_vcol=True,
            uv_scale=(0.25, 0.25),
        ),
        'ceiling_white': make_pbr_material(
            'mat_air_ceiling',
            color='#edf1f4',
            roughness=0.62,
            use_vcol=True,
        ),
        'led_warm': make_pbr_material(
            'mat_air_led_warm',
            color='#fff8e8',
            roughness=0.2,
            emissive='#fff1d2',
            emissive_strength=1.5,
            use_vcol=False,
        ),
        'counter_navy': make_pbr_material(
            'mat_air_counter_navy',
            color='#233d5c',
            roughness=0.44,
            metallic=0.08,
            use_vcol=True,
        ),
        'counter_stone': make_pbr_material(
            'mat_air_counter_stone',
            color='#dde3e8',
            roughness=0.18,
            metallic=0.04,
            use_vcol=True,
        ),
        'screen_glow': make_pbr_material(
            'mat_air_screen',
            color='#cfe6fa',
            roughness=0.12,
            emissive='#6eaef0',
            emissive_strength=0.9,
            use_vcol=False,
        ),
        'belt_rubber': make_pbr_material(
            'mat_air_belt',
            color='#24272c',
            roughness=0.84,
            use_vcol=True,
        ),
        'chair_fabric': make_pbr_material(
            'mat_air_chair',
            roughness=0.78,
            image=seat_alb,
            use_vcol=True,
            uv_scale=(2.0, 2.0),
        ),
        'gate_glow': make_pbr_material(
            'mat_air_gate_glow',
            color='#ffe6b3',
            roughness=0.18,
            emissive='#ffc864',
            emissive_strength=1.35,
            use_vcol=False,
        ),
        'sign_housing': make_pbr_material(
            'mat_air_sign_housing',
            color='#1e2733',
            roughness=0.38,
            metallic=0.68,
            use_vcol=True,
        ),
        'gold_accent': make_pbr_material(
            'mat_air_gold',
            color='#cfa044',
            roughness=0.26,
            metallic=0.88,
            use_vcol=False,
        ),
        'jet_body': make_pbr_material(
            'mat_air_jet_body',
            color='#f2f5f8',
            roughness=0.24,
            metallic=0.18,
            use_vcol=True,
        ),
        'jet_wing': make_pbr_material(
            'mat_air_jet_wing',
            color='#d7dde2',
            roughness=0.30,
            metallic=0.35,
            use_vcol=True,
        ),
        'jet_teal': make_pbr_material(
            'mat_air_jet_teal',
            color='#176964',
            roughness=0.28,
            metallic=0.14,
            use_vcol=True,
        ),
        'jet_glass': make_pbr_material(
            'mat_air_jet_glass',
            color='#162230',
            roughness=0.08,
            metallic=0.35,
            use_vcol=False,
        ),
        'tire_rubber': make_pbr_material(
            'mat_air_tire',
            color='#1f2226',
            roughness=0.88,
            use_vcol=True,
        ),
        'lug_burgundy': make_pbr_material('mat_air_lug_burg', color='#843438', roughness=0.36, metallic=0.06, use_vcol=True),
        'lug_teal': make_pbr_material('mat_air_lug_teal', color='#276482', roughness=0.36, metallic=0.06, use_vcol=True),
        'lug_olive': make_pbr_material('mat_air_lug_olive', color='#39644a', roughness=0.38, metallic=0.05, use_vcol=True),
    }


# ------------------------------------------------------------------ Terminal Shell
def _build_terminal_shell(col, mats):
    parts = []

    # 1. Polished light terrazzo floor: 64x30 m centered at (1, 0, 0), top at y = 0
    bm = bmesh.new()
    _add_box_t(bm, (1.0, -0.10, 0.0), (64.0, 0.20, 30.0))
    parts.append(_make_part(bm, '_floor', col, mats['terrazzo'], smooth=False, uv_scale=0.32, ao_strength=0.14, ao_min=0.82))

    # Subtle inlaid brushed-steel guidance runner lines leading toward check-in and Gate 12
    bm = bmesh.new()
    _add_box_t(bm, (1.0, 0.006, -4.8), (52.0, 0.012, 0.14))
    _add_box_t(bm, (1.0, 0.006, 2.2), (52.0, 0.012, 0.14))
    parts.append(_make_part(bm, '_floor_strips', col, mats['aluminum_clad'], smooth=False, uv_scale=0.5, ao=False))

    # 2. Exterior tarmac apron outside glass curtain wall (z in [-36, -12.3], y = -0.15)
    bm = bmesh.new()
    _add_box_t(bm, (1.0, -0.25, -24.5), (78.0, 0.20, 24.5))
    parts.append(_make_part(bm, '_tarmac', col, mats['tarmac'], smooth=False, uv_scale=0.15, ao=False))

    # Yellow painted taxiway lead-in line on tarmac
    bm = bmesh.new()
    _add_box_t(bm, (22.0, -0.14, -18.0), (36.0, 0.02, 0.30))
    _add_box_t(bm, (32.0, -0.14, -18.0), (0.35, 0.02, 3.6))
    parts.append(_make_part(bm, '_tarmac_lines', col, mats['tarmac_yellow'], smooth=False, uv_scale=0.5, ao=False))

    # 3. Tall modern glass curtain wall along z = -12.2 (h = 9.0 m, x in [-31, 33])
    bm_gl = bmesh.new()
    # Left of Gate 12 portal (x in [-31, 22.8]) + right of Gate 12 (x in [27.2, 33]) + above Gate 12 (y in [4.1, 9.0])
    _add_box_t(bm_gl, (-4.1, 4.5, -12.22), (53.8, 9.0, 0.06))
    _add_box_t(bm_gl, (30.1, 4.5, -12.22), (5.8, 9.0, 0.06))
    _add_box_t(bm_gl, (25.0, 6.55, -12.22), (4.4, 4.9, 0.06))
    parts.append(_make_part(bm_gl, '_curtain_glass', col, mats['curtain_glass'], smooth=False, uv_scale=0.2, ao=False))

    # Steel curtain wall mullions every 4 m + horizontal transoms + interior wind-bracing fins
    # Positioned strictly behind z = -12.03 so signboard housings at z = -11.98 sit cleanly in front
    bm_mul = bmesh.new()
    for x in range(-30, 33, 4):
        mx = 27.2 if x == 26 else float(x)
        _add_box_t(bm_mul, (mx, 4.5, -12.18), (0.20, 9.0, 0.24), bevel=0.015)
        _add_box_t(bm_mul, (mx, 4.5, -12.08), (0.06, 8.8, 0.10))
    # Horizontal transoms
    for ty in (0.14, 3.20, 6.20, 8.88):
        if ty < 4.0:
            _add_box_t(bm_mul, (-4.1, ty, -12.18), (53.8, 0.18, 0.20), bevel=0.01)
            _add_box_t(bm_mul, (30.1, ty, -12.18), (5.8, 0.18, 0.20), bevel=0.01)
        else:
            _add_box_t(bm_mul, (1.0, ty, -12.18), (64.0, 0.18, 0.20), bevel=0.01)
    parts.append(_make_part(bm_mul, '_mullions', col, mats['steel_mullion'], smooth=False, uv_scale=0.4, ao_strength=0.24))

    # 4. Side walls (x = -28.1 and x = 30.1, h = 9.2 m, z in [-12.3, 15.0]) with acoustic panel ribs
    bm_w = bmesh.new()
    _add_box_t(bm_w, (-28.15, 4.6, 1.35), (0.24, 9.2, 27.3))
    _add_box_t(bm_w, (30.15, 4.6, 1.35), (0.24, 9.2, 27.3))
    parts.append(_make_part(bm_w, '_side_walls', col, mats['wall_panel'], smooth=False, uv_scale=0.22, ao_strength=0.20, ao_min=0.75))

    bm_wt = bmesh.new()
    for sx, wx in ((-1, -28.00), (1, 30.00)):
        # Dark baseboard & horizontal aluminum acoustic reveal strips
        _add_box_t(bm_wt, (wx, 0.22, 1.35), (0.06, 0.44, 27.2))
        for ry in (3.2, 6.2):
            _add_box_t(bm_wt, (wx, ry, 1.35), (0.06, 0.10, 27.2))
        for rz in range(-10, 15, 4):
            _add_box_t(bm_wt, (wx, 4.6, float(rz)), (0.08, 9.0, 0.12))
    parts.append(_make_part(bm_wt, '_wall_trim', col, mats['aluminum_clad'], smooth=False, uv_scale=0.4, ao_strength=0.22))

    # 5. Vaulted steel-truss terminal roof (y = 9.2..10.2) with recessed warm LED light strips
    bm_rf = bmesh.new()
    # Gentle vaulted arch roof deck spanning z in [-13.0, 15.0], x in [-30.0, 32.0]
    segs_z = 8
    z0, z1 = -13.0, 15.0
    xs_rf = (-30.0, 32.0)
    rings_rf = []
    for x in xs_rf:
        row_in = []
        row_out = []
        for i in range(segs_z + 1):
            u = i / segs_z
            z = z0 + u * (z1 - z0)
            arch = math.sin(u * math.pi) * 1.15
            row_in.append(bm_rf.verts.new(three_to_bl(x, 9.15 + arch, z)))
            row_out.append(bm_rf.verts.new(three_to_bl(x, 9.55 + arch, z)))
        rings_rf.append((row_in, row_out))
    for i in range(segs_z):
        # Inner ceiling face (facing down)
        bm_rf.faces.new((rings_rf[0][0][i], rings_rf[1][0][i], rings_rf[1][0][i + 1], rings_rf[0][0][i + 1]))
        # Outer roof face (facing up)
        bm_rf.faces.new((rings_rf[0][1][i], rings_rf[0][1][i + 1], rings_rf[1][1][i + 1], rings_rf[1][1][i]))
    parts.append(_make_part(bm_rf, '_roof_deck', col, mats['ceiling_white'], smooth=True, uv_scale=0.18, ao_strength=0.18, ao_min=0.78))

    # Exposed transverse steel arch trusses every 8 m + longitudinal purlins
    bm_tr = bmesh.new()
    for tx in (-24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0):
        for i in range(segs_z):
            u0 = i / segs_z
            u1 = (i + 1) / segs_z
            za, zb = z0 + u0 * (z1 - z0), z0 + u1 * (z1 - z0)
            ya, yb = 8.85 + math.sin(u0 * math.pi) * 1.10, 8.85 + math.sin(u1 * math.pi) * 1.10
            zm = 0.5 * (za + zb)
            ym = 0.5 * (ya + yb)
            dz = zb - za
            dy = yb - ya
            seg_len = math.hypot(dz, dy)
            pitch = math.atan2(dy, dz)
            _add_box_t(bm_tr, (tx, ym, zm), (0.28, 0.34, seg_len + 0.06), rot_x=-pitch)
    # 3 longitudinal roof purlin beams
    for u in (0.22, 0.50, 0.78):
        pz = z0 + u * (z1 - z0)
        py = 8.98 + math.sin(u * math.pi) * 1.12
        _add_box_t(bm_tr, (1.0, py, pz), (62.0, 0.22, 0.24))
    parts.append(_make_part(bm_tr, '_roof_trusses', col, mats['aluminum_clad'], smooth=False, uv_scale=0.35, ao_strength=0.22))

    # Recessed warm LED ceiling light strips
    bm_led = bmesh.new()
    for u in (0.16, 0.38, 0.62, 0.84):
        lz = z0 + u * (z1 - z0)
        ly = 9.08 + math.sin(u * math.pi) * 1.12
        _add_box_t(bm_led, (1.0, ly, lz), (56.0, 0.05, 0.34))
    parts.append(_make_part(bm_led, '_roof_leds', col, mats['led_warm'], smooth=False, uv_scale=0.3, ao=False))

    return parts


# ------------------------------------------------------------------ Parked Commercial Jetliner
def _build_parked_jet(col, mats):
    """Realistic parked commercial airliner outside glass wall at (22, 2.6, -19.2), nose +X, tail -X."""
    parts = []
    # Centered at z = -19.2 with 6.6 m swept half-span so wingtip stays cleanly outside z = -12.2 glass wall
    jx, jy, jz = 22.0, 2.6, -19.2
    m_jet = Matrix.Translation(three_to_bl(jx, jy, jz))

    # 1. Sculpted tapered fuselage via lofted cross-section rings along X
    bm_fus = bmesh.new()
    stations = [
        (-13.2, 0.12, 0.65),   # tailcone tip (raised slightly)
        (-11.2, 0.62, 0.42),
        (-8.6, 1.24, 0.16),
        (-5.5, 1.64, 0.0),
        (5.5, 1.64, 0.0),
        (8.4, 1.56, -0.02),
        (10.6, 1.16, -0.14),   # cockpit nose droop
        (12.2, 0.52, -0.32),
        (13.0, 0.10, -0.40),   # radome tip
    ]
    segs = 18
    rings = []
    for sx, r, y_off in stations:
        ring = []
        for k in range(segs):
            a = k / segs * math.tau
            ly = y_off + math.sin(a) * r * 1.06
            lz = math.cos(a) * r
            ring.append(bm_fus.verts.new(three_to_bl(sx, ly, lz)))
        rings.append(ring)
    loft_rings(bm_fus, rings, closed_u=True, cap_start=True, cap_end=True)
    bmesh.ops.transform(bm_fus, matrix=m_jet, verts=bm_fus.verts[:])
    parts.append(_make_part(bm_fus, '_jet_fuselage', col, mats['jet_body'], smooth=True, uv_scale=0.25, ao_strength=0.18, ao_min=0.78))

    # Teal belly/cheatline accent stripe along fuselage + vertical tail stabilizer
    bm_tl = bmesh.new()
    # Vertical tail fin (swept trapezoid) at local x in [-12.2, -7.2], y in [1.1, 6.2]
    fin_pts_l = [(-12.2, 1.0, -0.14), (-7.2, 1.2, -0.18), (-10.6, 6.2, -0.08), (-12.7, 6.0, -0.08)]
    fin_pts_r = [(-12.2, 1.0, 0.14), (-7.2, 1.2, 0.18), (-10.6, 6.2, 0.08), (-12.7, 6.0, 0.08)]
    vl = [bm_tl.verts.new(three_to_bl(*p)) for p in fin_pts_l]
    vr = [bm_tl.verts.new(three_to_bl(*p)) for p in fin_pts_r]
    bm_tl.faces.new((vl[0], vl[1], vl[2], vl[3]))
    bm_tl.faces.new((vr[3], vr[2], vr[1], vr[0]))
    for i in range(4):
        inext = (i + 1) % 4
        bm_tl.faces.new((vl[i], vr[i], vr[inext], vl[inext]))
    # Swept upturned winglets at wing tips (local z = ±6.65, x = -3.8)
    for sz in (-1.0, 1.0):
        _add_box_t(bm_tl, (-3.8, 0.56, sz * 6.65), (1.15, 1.25, 0.12), rot_x=sz * -0.18, rot_z=0.35, bevel=0.02)
    # Cheatline stripe on terminal-facing side (+Z)
    _add_box_t(bm_tl, (0.5, 0.05, 1.63), (16.4, 0.24, 0.06))
    bmesh.ops.transform(bm_tl, matrix=m_jet, verts=bm_tl.verts[:])
    parts.append(_make_part(bm_tl, '_jet_teal', col, mats['jet_teal'], smooth=False, uv_scale=0.3, ao_strength=0.20))

    # Gold airline tail accent band
    bm_g = bmesh.new()
    _add_box_t(bm_g, (-10.3, 3.6, 0.0), (2.8, 0.36, 0.30), rot_z=0.45)
    _add_box_t(bm_g, (0.5, -0.12, 1.63), (16.0, 0.10, 0.06))
    bmesh.ops.transform(bm_g, matrix=m_jet, verts=bm_g.verts[:])
    parts.append(_make_part(bm_g, '_jet_gold', col, mats['gold_accent'], smooth=False, uv_scale=0.5, ao=False))

    # Swept-back dihedral wings & horizontal stabilizers (cleanly clear of z = -12.2 curtain wall)
    bm_wg = bmesh.new()
    for sz in (-1.0, 1.0):
        r_pts = [(2.2, -0.35, sz * 1.35), (-2.4, -0.35, sz * 1.35), (-2.4, -0.76, sz * 1.35), (2.2, -0.76, sz * 1.35)]
        t_pts = [(-3.0, 0.08, sz * 6.60), (-4.4, 0.08, sz * 6.60), (-4.4, -0.10, sz * 6.60), (-3.0, -0.10, sz * 6.60)]
        vr = [bm_wg.verts.new(three_to_bl(*p)) for p in r_pts]
        vt = [bm_wg.verts.new(three_to_bl(*p)) for p in t_pts]
        if sz > 0:
            loft_rings(bm_wg, [vr, vt], closed_u=True, cap_start=True, cap_end=True)
        else:
            loft_rings(bm_wg, [vt, vr], closed_u=True, cap_start=True, cap_end=True)
        # Horizontal tailplane
        hr = [(-9.0, 0.85, sz * 0.4), (-11.6, 0.85, sz * 0.4), (-11.6, 0.62, sz * 0.4), (-9.0, 0.62, sz * 0.4)]
        ht = [(-11.4, 1.05, sz * 4.2), (-12.6, 1.05, sz * 4.2), (-12.6, 0.92, sz * 4.2), (-11.4, 0.92, sz * 4.2)]
        vhr = [bm_wg.verts.new(three_to_bl(*p)) for p in hr]
        vht = [bm_wg.verts.new(three_to_bl(*p)) for p in ht]
        if sz > 0:
            loft_rings(bm_wg, [vhr, vht], closed_u=True, cap_start=True, cap_end=True)
        else:
            loft_rings(bm_wg, [vht, vhr], closed_u=True, cap_start=True, cap_end=True)
        # Engine pylon + outer turbofan nacelle
        _add_box_t(bm_wg, (0.6, -0.72, sz * 3.4), (2.3, 0.60, 0.26), bevel=0.03)
        m_eng = Matrix.Translation(three_to_bl(0.9, -1.22, sz * 3.4)) @ Matrix.Rotation(math.pi / 2.0, 4, 'Y')
        bmesh.ops.create_cone(bm_wg, cap_ends=True, segments=14, radius1=0.66, radius2=0.74, depth=2.7, matrix=m_eng)
    bmesh.ops.transform(bm_wg, matrix=m_jet, verts=bm_wg.verts[:])
    parts.append(_make_part(bm_wg, '_jet_wings', col, mats['jet_wing'], smooth=True, uv_scale=0.25, ao_strength=0.22))

    # Cockpit windshield + terminal-facing passenger window strip + dark turbofan intakes
    bm_gl = bmesh.new()
    _add_box_t(bm_gl, (10.35, 0.42, 0.0), (1.10, 0.46, 1.56), rot_z=-0.25, bevel=0.06)
    for i in range(16):
        wx = -6.2 + i * 0.92
        _add_box_t(bm_gl, (wx, 0.42, 1.59), (0.28, 0.36, 0.08), bevel=0.04)
    for sz in (-1.0, 1.0):
        m_fan = Matrix.Translation(three_to_bl(2.21, -1.22, sz * 3.4)) @ Matrix.Rotation(math.pi / 2.0, 4, 'Y')
        bmesh.ops.create_cone(bm_gl, cap_ends=True, segments=12, radius1=0.62, radius2=0.62, depth=0.12, matrix=m_fan)
        m_ex = Matrix.Translation(three_to_bl(-0.70, -1.22, sz * 3.4)) @ Matrix.Rotation(math.pi / 2.0, 4, 'Y')
        bmesh.ops.create_cone(bm_gl, cap_ends=True, segments=12, radius1=0.36, radius2=0.50, depth=0.62, matrix=m_ex)
    bmesh.ops.transform(bm_gl, matrix=m_jet, verts=bm_gl.verts[:])
    parts.append(_make_part(bm_gl, '_jet_windows', col, mats['jet_glass'], smooth=True, uv_scale=0.5, ao=False))

    # Landing gear struts + rubber tires reaching tarmac (jy=2.6 -> local y=-2.75 touches y=-0.15)
    bm_lg = bmesh.new()
    bm_tr = bmesh.new()
    for gx, gz in ((8.8, 0.0), (-0.8, -2.5), (-0.8, 2.5)):
        _add_cyl_t(bm_lg, (gx, -1.75, gz), 0.12, 1.45, segs=8)
        for tz_off in (-0.24, 0.24):
            m_wh = Matrix.Translation(three_to_bl(gx, -2.36, gz + tz_off)) @ Matrix.Rotation(math.pi / 2.0, 4, 'X')
            bmesh.ops.create_cone(bm_tr, cap_ends=True, segments=12, radius1=0.40, radius2=0.40, depth=0.22, matrix=m_wh)
    bmesh.ops.transform(bm_lg, matrix=m_jet, verts=bm_lg.verts[:])
    bmesh.ops.transform(bm_tr, matrix=m_jet, verts=bm_tr.verts[:])
    parts.append(_make_part(bm_lg, '_jet_gear', col, mats['steel_dark'], smooth=True, uv_scale=0.5, ao=False))
    parts.append(_make_part(bm_tr, '_jet_tires', col, mats['tire_rubber'], smooth=True, uv_scale=0.5, ao=False))

    return parts


# ------------------------------------------------------------------ Check-in Counter, Suitcases & Belt
def _build_checkin_area(col, mats):
    """Check-in counter island [-12, 12, -9.2, -7.8], h=1.1, monitors, scales, suitcases & conveyor."""
    parts = []

    # 1. Dark navy paneled counter body + vertical dividers
    bm_cnt = bmesh.new()
    _add_box_t(bm_cnt, (0.0, 0.62, -8.50), (23.90, 0.94, 1.32), bevel=0.02)
    # Recessed lower front modesty panels & 4 desk bays
    for x in (-11.9, -9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0, 11.9):
        _add_box_t(bm_cnt, (x, 0.62, -7.83), (0.14, 0.94, 0.06), bevel=0.01)
    parts.append(_make_part(bm_cnt, '_counter_body', col, mats['counter_navy'], smooth=False, uv_scale=0.4, ao_strength=0.28))

    # Brushed steel toe-kick + warm under-counter LED strip
    bm_tk = bmesh.new()
    _add_box_t(bm_tk, (0.0, 0.08, -8.50), (23.70, 0.16, 1.18))
    # 4 recessed luggage weigh-scale plates in front of counter bays
    for sx in (-6.0, -1.5, 3.0, 7.5):
        _add_box_t(bm_tk, (sx, 0.04, -7.52), (1.15, 0.08, 0.56), bevel=0.01)
    parts.append(_make_part(bm_tk, '_counter_steel', col, mats['aluminum_clad'], smooth=False, uv_scale=0.5, ao_strength=0.22))

    bm_ul = bmesh.new()
    _add_box_t(bm_ul, (0.0, 0.16, -7.86), (23.60, 0.03, 0.04))
    parts.append(_make_part(bm_ul, '_counter_led', col, mats['led_warm'], smooth=False, uv_scale=0.5, ao=False))

    # Polished light stone counter top (y = 1.08..1.16) + raised agent privacy risers
    bm_top = bmesh.new()
    _add_box_t(bm_top, (0.0, 1.12, -8.50), (24.04, 0.09, 1.44), bevel=0.018, bevel_segs=2)
    # Low desk transaction ledges at the 4 agent desks
    for mx in (-8.5, -3.0, 3.0, 8.5):
        _add_box_t(bm_top, (mx, 1.24, -8.12), (2.40, 0.16, 0.36), bevel=0.015)
    parts.append(_make_part(bm_top, '_counter_top', col, mats['counter_stone'], smooth=False, uv_scale=0.4, ao_strength=0.18))

    # 4 check-in monitor workstations (angled screens + stands + keyboards)
    bm_mhw = bmesh.new()
    bm_scr = bmesh.new()
    for mx in (-8.5, -3.0, 3.0, 8.5):
        # Monitor stand + housing
        _add_box_t(bm_mhw, (mx + 0.55, 1.20, -8.58), (0.28, 0.04, 0.22), bevel=0.008)
        _add_box_t(bm_mhw, (mx + 0.55, 1.38, -8.62), (0.07, 0.34, 0.07))
        _add_box_t(bm_mhw, (mx + 0.55, 1.56, -8.54), (0.64, 0.42, 0.05), rot_y=-0.22, rot_x=-0.12, bevel=0.012)
        _add_box_t(bm_scr, (mx + 0.54, 1.56, -8.568), (0.58, 0.36, 0.02), rot_y=-0.22, rot_x=-0.12)
        # Keyboard & passport scanner pad
        _add_box_t(bm_mhw, (mx - 0.10, 1.18, -8.68), (0.48, 0.03, 0.18), bevel=0.006)
        _add_box_t(bm_mhw, (mx - 0.68, 1.19, -8.46), (0.26, 0.06, 0.22), bevel=0.008)
    parts.append(_make_part(bm_mhw, '_monitors_hw', col, mats['steel_dark'], smooth=False, uv_scale=1.0, ao_strength=0.2))
    parts.append(_make_part(bm_scr, '_monitors_scr', col, mats['screen_glow'], smooth=False, uv_scale=1.0, ao=False))

    # 2. Dark rubber slatted baggage conveyor belt behind counter at z = -10.8
    bm_bc = bmesh.new()
    _add_box_t(bm_bc, (0.0, 0.48, -10.80), (24.0, 0.16, 1.14), bevel=0.015)
    # Transverse rubber slats along belt
    for ix in range(-11, 12):
        _add_box_t(bm_bc, (float(ix), 0.57, -10.80), (0.06, 0.025, 1.10))
    parts.append(_make_part(bm_bc, '_conveyor_belt', col, mats['belt_rubber'], smooth=False, uv_scale=0.5, ao_strength=0.25))

    bm_bf = bmesh.new()
    # Steel conveyor side rails + legs + 2 baggage entry hoods
    _add_box_t(bm_bf, (0.0, 0.50, -10.18), (24.1, 0.24, 0.10), bevel=0.01)
    _add_box_t(bm_bf, (0.0, 0.50, -11.42), (24.1, 0.24, 0.10), bevel=0.01)
    for lx in range(-11, 12, 3):
        _add_box_t(bm_bf, (float(lx), 0.24, -10.22), (0.10, 0.48, 0.10))
        _add_box_t(bm_bf, (float(lx), 0.24, -11.38), (0.10, 0.48, 0.10))
    for hx in (-5.5, 5.5):
        _add_box_t(bm_bf, (hx, 1.15, -11.15), (1.80, 1.25, 0.80), bevel=0.03)
    parts.append(_make_part(bm_bf, '_conveyor_frame', col, mats['steel_mullion'], smooth=False, uv_scale=0.5, ao_strength=0.26))

    # 3. Five realistic wheeled suitcases standing in front of counter (z = -7.2, x = -10 + i * 4.6)
    lug_mats = ['lug_burgundy', 'lug_teal', 'lug_olive']
    lug_bms = {k: bmesh.new() for k in lug_mats}
    bm_lhw = bmesh.new()
    yaws = (0.14, -0.10, 0.08, -0.16, 0.12)
    for i in range(5):
        sx = -10.0 + i * 4.6
        sz = -7.2
        yaw = yaws[i]
        mkey = lug_mats[i % 3]
        h_case = 0.74 + (i % 2) * 0.10
        w_case = 0.52 + (i % 3) * 0.04
        d_case = 0.30
        bm_c = lug_bms[mkey]
        _add_box_t(bm_c, (sx, 0.06 + h_case * 0.5, sz), (w_case, h_case, d_case), rot_y=yaw, bevel=0.045, bevel_segs=2)
        # Telescopic pull handle + top grip + 4 caster wheels
        m_s = _mat_three((sx, 0.0, sz), rot_y=yaw)
        for rx in (-0.10, 0.10):
            v_r = _add_box_t(bm_lhw, (0.0, 0.0, 0.0), (0.03, 0.38, 0.03))
            bmesh.ops.transform(bm_lhw, matrix=m_s @ Matrix.Translation(three_to_bl(rx, 0.06 + h_case + 0.17, -0.04)), verts=v_r)
        v_bar = _add_box_t(bm_lhw, (0.0, 0.0, 0.0), (0.26, 0.04, 0.045), bevel=0.008)
        bmesh.ops.transform(bm_lhw, matrix=m_s @ Matrix.Translation(three_to_bl(0.0, 0.06 + h_case + 0.37, -0.04)), verts=v_bar)
        for wx in (-w_case * 0.36, w_case * 0.36):
            for wz in (-d_case * 0.32, d_case * 0.32):
                v_w = _add_cyl_t(bm_lhw, (0.0, 0.0, 0.0), 0.035, 0.05, segs=8)
                bmesh.ops.transform(bm_lhw, matrix=m_s @ Matrix.Translation(three_to_bl(wx, 0.035, wz)), verts=v_w)
    for mkey, bm_c in lug_bms.items():
        parts.append(_make_part(bm_c, f'_lug_{mkey}', col, mats[mkey], smooth=True, uv_scale=1.0, ao_strength=0.26))
    parts.append(_make_part(bm_lhw, '_lug_hw', col, mats['steel_dark'], smooth=True, uv_scale=1.0, ao=False))

    return parts


# ------------------------------------------------------------------ Structural Columns, Waiting Chairs, Gate 12 & Signs
def _build_columns_chairs_gate_signs(col, mats):
    parts = []

    # 1. Four clad structural columns matching collision x in {-18, -6, 6, 18}, z in [3.4, 4.6], h = 9
    bm_col = bmesh.new()
    bm_base = bmesh.new()
    for cx in (-18.0, -6.0, 6.0, 18.0):
        cz = 4.0
        # Protective dark-steel base plinth (h=0.48) + upper structural collar
        _add_box_t(bm_base, (cx, 0.24, cz), (1.18, 0.48, 1.18), bevel=0.06, bevel_segs=2)
        _add_box_t(bm_base, (cx, 8.75, cz), (1.36, 0.42, 1.36), bevel=0.06, bevel_segs=2)
        # Stacked brushed-aluminum clad drum segments with subtle horizontal shadow reveals
        for seg_i in range(4):
            y0 = 0.50 + seg_i * 2.02
            _add_box_t(bm_col, (cx, y0 + 0.98, cz), (1.10, 1.96, 1.10), bevel=0.12, bevel_segs=2)
        # Flared capital struts tying into roof truss
        _add_box_t(bm_col, (cx, 9.05, cz), (1.55, 0.24, 1.55), bevel=0.04)
    parts.append(_make_part(bm_col, '_columns_clad', col, mats['aluminum_clad'], smooth=False, uv_scale=0.4, ao_strength=0.25))
    parts.append(_make_part(bm_base, '_columns_base', col, mats['steel_dark'], smooth=False, uv_scale=0.5, ao_strength=0.25))

    # 2. Three rows of realistic airport waiting chairs matching collision x in [19.5, 28.5], z in {-5, -2, 1}
    # 3 rows x 9 chairs = 27 ergonomic chairs (kept clean within tri budget!)
    bm_beam = bmesh.new()
    bm_seat = bmesh.new()
    bm_arm = bmesh.new()
    for rz in (-5.0, -2.0, 1.0):
        # Horizontal structural steel beam
        _add_box_t(bm_beam, (24.0, 0.34, rz), (8.70, 0.08, 0.10), bevel=0.01)
        # 3 floor-mounted T-leg pedestals per row
        for lx in (20.2, 24.0, 27.8):
            _add_box_t(bm_beam, (lx, 0.17, rz), (0.08, 0.34, 0.10))
            _add_box_t(bm_beam, (lx, 0.03, rz), (0.10, 0.06, 0.64), bevel=0.01)
        # 9 contoured individual seats facing -Z (toward Gate 12!) along x in [19.8..28.2]
        n_seats = 9
        for i in range(n_seats):
            sx = 20.0 + i * 1.0
            # Contoured seat pan (tilted slightly back for comfort)
            _add_box_t(bm_seat, (sx, 0.44, rz - 0.04), (0.76, 0.07, 0.50), rot_x=0.07, bevel=0.022)
            # Ergonomic reclined backrest (at +Z side so passenger faces -Z toward Gate 12)
            _add_box_t(bm_seat, (sx, 0.78, rz + 0.22), (0.74, 0.56, 0.07), rot_x=-0.16, bevel=0.022)
            # Rear spine support bracket
            _add_box_t(bm_beam, (sx, 0.52, rz + 0.14), (0.07, 0.34, 0.06), rot_x=-0.16)
        # Chrome armrests between seats & ends (10 per row)
        for i in range(n_seats + 1):
            ax = 19.52 + i * 1.0 if i == 0 else (28.48 if i == n_seats else 19.50 + i * 1.0)
            _add_box_t(bm_arm, (ax, 0.58, rz - 0.02), (0.05, 0.04, 0.42), bevel=0.01)
            _add_box_t(bm_arm, (ax, 0.46, rz + 0.06), (0.04, 0.24, 0.06))
    parts.append(_make_part(bm_beam, '_chairs_beam', col, mats['steel_dark'], smooth=False, uv_scale=0.8, ao_strength=0.24))
    parts.append(_make_part(bm_seat, '_chairs_seat', col, mats['chair_fabric'], smooth=True, uv_scale=1.2, ao_strength=0.24))
    parts.append(_make_part(bm_arm, '_chairs_arm', col, mats['chrome'], smooth=True, uv_scale=1.0, ao=False))

    # 3. Illuminated Gate 12 portal frame & glass jetbridge doors at (25, 0, -11.7)
    gx, gz = 25.0, -11.70
    bm_gp = bmesh.new()
    # Architectural portal surround (w=4.4, h=4.1)
    _add_box_t(bm_gp, (gx - 1.95, 2.05, gz), (0.50, 4.10, 0.48), bevel=0.025)
    _add_box_t(bm_gp, (gx + 1.95, 2.05, gz), (0.50, 4.10, 0.48), bevel=0.025)
    _add_box_t(bm_gp, (gx, 3.85, gz), (4.40, 0.52, 0.48), bevel=0.025)
    # Double sliding door stiles & rails
    for dx in (-1.46, -0.04, 0.04, 1.46):
        _add_box_t(bm_gp, (gx + dx, 1.75, gz + 0.06), (0.07, 3.45, 0.08), bevel=0.008)
    _add_box_t(bm_gp, (gx, 0.14, gz + 0.06), (2.96, 0.24, 0.08))
    _add_box_t(bm_gp, (gx, 3.45, gz + 0.06), (2.96, 0.12, 0.08))
    parts.append(_make_part(bm_gp, '_gate_portal', col, mats['counter_navy'], smooth=False, uv_scale=0.5, ao_strength=0.24))

    # Warm illuminated jetbridge doorway backdrop + golden perimeter halo trim
    bm_gg = bmesh.new()
    _add_box_t(bm_gg, (gx, 1.78, gz - 0.10), (2.92, 3.42, 0.08))
    # Subtle warm portal reveal light strips
    _add_box_t(bm_gg, (gx - 1.66, 1.80, gz + 0.22), (0.05, 3.46, 0.05))
    _add_box_t(bm_gg, (gx + 1.66, 1.80, gz + 0.22), (0.05, 3.46, 0.05))
    _add_box_t(bm_gg, (gx, 3.56, gz + 0.22), (3.38, 0.05, 0.05))
    parts.append(_make_part(bm_gg, '_gate_glow', col, mats['gate_glow'], smooth=False, uv_scale=0.5, ao=False))

    # Brushed chrome vertical door pull bars + gold top accent bar
    bm_gh = bmesh.new()
    for dx in (-0.18, 0.18):
        _add_cyl_t(bm_gh, (gx + dx, 1.32, gz + 0.14), 0.022, 0.72, segs=10)
    parts.append(_make_part(bm_gh, '_gate_handles', col, mats['chrome'], smooth=True, uv_scale=1.0, ao=False))

    # 4. Sleek dark aluminum suspended signboard housings behind exact Three.js canvas signs
    # Sign positions in airport.js: (0, 5, -11.9) w=10 h=1.4, (25, 5, -11.9) w=5 h=1.2, (14, 6, -0.5) w=5 h=1.0
    # Place housings slightly recessed behind (-11.98, -11.98, -0.58) so zero Z-fighting!
    bm_sh = bmesh.new()
    bm_sr = bmesh.new()
    bm_sg = bmesh.new()
    sign_specs = [
        (0.0, 5.0, -11.98, 10.24, 1.56, False),
        (25.0, 5.0, -11.98, 5.24, 1.36, True),   # gold accent bezel for Gate 12
        (14.0, 6.0, -0.58, 5.24, 1.16, False),
    ]
    for sx, sy, sz, sw, sh, is_gold in sign_specs:
        # Slim dark aluminum housing box (depth 0.11 -> front face at sz + 0.055 = -11.925 / -0.525, cleanly behind -11.90 / -0.50!)
        _add_box_t(bm_sh, (sx, sy, sz), (sw, sh, 0.11), bevel=0.018)
        # Bezel trim bars around top & bottom
        target_bm = bm_sg if is_gold else bm_sr
        _add_box_t(target_bm, (sx, sy + sh * 0.5 + 0.02, sz + 0.01), (sw + 0.04, 0.06, 0.13), bevel=0.01)
        _add_box_t(target_bm, (sx, sy - sh * 0.5 - 0.02, sz + 0.01), (sw + 0.04, 0.06, 0.13), bevel=0.01)
        # Twin steel ceiling suspension rods rising up to roof truss (y = 9.2)
        rod_h = 9.25 - (sy + sh * 0.5)
        rod_y = sy + sh * 0.5 + rod_h * 0.5
        for rx in (-sw * 0.36, sw * 0.36):
            _add_cyl_t(bm_sr, (sx + rx, rod_y, sz), 0.032, rod_h, segs=8)
    parts.append(_make_part(bm_sh, '_sign_housings', col, mats['sign_housing'], smooth=False, uv_scale=0.6, ao_strength=0.22))
    parts.append(_make_part(bm_sr, '_sign_rods', col, mats['aluminum_clad'], smooth=True, uv_scale=0.8, ao=False))
    parts.append(_make_part(bm_sg, '_sign_gold', col, mats['gold_accent'], smooth=False, uv_scale=0.8, ao=False))

    return parts


# ------------------------------------------------------------------ Public API
def build_airport(col):
    """Build Chapter 2 Airport departures hall into `col` and return dict of exported objects."""
    mats = _create_materials()
    all_parts = []
    all_parts.extend(_build_terminal_shell(col, mats))
    all_parts.extend(_build_parked_jet(col, mats))
    all_parts.extend(_build_checkin_area(col, mats))
    all_parts.extend(_build_columns_chairs_gate_signs(col, mats))

    lod0 = join_objects(all_parts, 'airport_LOD0', col)
    lod1 = make_lod1(lod0, ratio=0.40, name='airport_LOD1')
    return {'lod0': lod0, 'lod1': lod1, 'all': [lod0, lod1]}


def export_airport():
    """Build, export `public/models/env/airport.glb`, and render `blender/previews/env_airport.png`."""
    ensure_dirs()
    reset_scene()
    col = make_collection('EnvAirport')
    built = build_airport(col)

    out_glb = MODELS_ENV / 'airport.glb'
    size_bytes = export_glb(built['all'], out_glb, vertex_colors=True)

    # Render interior-wide preview showing check-in counter, columns, waiting chairs, Gate 12, and jet outside
    built['lod1'].hide_render = True
    # Add soft interior fill lights in _PreviewRig (not exported) so terminal interior reads bright & realistic
    rig_col = bpy.data.collections.get('_PreviewRig') or bpy.data.collections.new('_PreviewRig')
    if rig_col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(rig_col)
    for idx, (lx, ly, lz, energy) in enumerate((
        (-6.0, 7.6, -2.0, 2200.0),
        (16.0, 7.6, -3.5, 2400.0),
        (4.0, 7.2, 6.0, 1500.0),
    )):
        ld = bpy.data.lights.new(f'_AirFill_{idx}', type='POINT')
        ld.energy = energy
        ld.shadow_soft_size = 2.0
        ld.use_shadow = False
        ld.color = (1.0, 0.96, 0.90)
        lo = bpy.data.objects.new(f'_AirFill_{idx}', ld)
        lo.location = three_to_bl(lx, ly, lz)
        rig_col.objects.link(lo)

    # Switch glass to DITHERED solely for fast headless EEVEE preview (GLB already exported with BLEND)
    glass_mat = bpy.data.materials.get('mat_air_glass')
    if glass_mat and hasattr(glass_mat, 'surface_render_method'):
        glass_mat.surface_render_method = 'DITHERED'

    out_png = PREVIEWS / 'env_airport.png'
    preview.render_shot(
        eye=three_to_bl(-13.5, 4.9, 9.8),
        target=three_to_bl(12.5, 2.7, -10.5),
        out_path=out_png,
        res=(1024, 640),
        lens=26,
        world_color=(0.78, 0.88, 0.96),
    )

    t0 = tri_count(built['lod0'])
    t1 = tri_count(built['lod1'])
    print(
        f'AIRPORT_OK: lod0={t0} tris, lod1={t1} tris, '
        f'glb={size_bytes / 1024:.1f}KB -> {out_glb}'
    )
    return {
        'name': 'airport',
        'glb': str(out_glb),
        'preview': str(out_png),
        'tris_lod0': t0,
        'tris_lod1': t1,
        'bytes': size_bytes,
    }


if __name__ == '__main__':
    export_airport()
