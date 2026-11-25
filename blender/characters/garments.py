"""Realistic draped & tailored PBR garment builders for umrah-journey characters.

Includes:
- Full sculpted short dark hair (player, guide, agent) & silver-grey hair + full neat rounded beard (mentor).
- Multi-layer ihram garments using woven white cotton terry (`tex_cotton_ihram`):
  - `outfit_ihram_izar`: draped lower wrap with overlapping front pleat, waist tuck/belt & sleek leather slip-on sandals.
  - `outfit_ihram_rida_covered`: draped upper shawl smoothly covering BOTH shoulders with zero skin poke-through.
  - `outfit_ihram_rida_idtiba`: diagonal upper shawl tucked under RIGHT armpit (-X) and draped smoothly over
    LEFT shoulder (+X), leaving RIGHT shoulder & upper arm 100% bare!
- Everyday travel street attire (`outfit_street`), airline attendant modest burgundy uniform + open-face hijab,
  Makkah hotel/Haram guide hospitality blazer uniform, and airport check-in agent uniform.
"""
import math
import sys

import bmesh
from mathutils import Vector

from blender.characters import body as body_mod
from blender.characters import rig as rig_mod
from blender.lib.common import (
    add_box,
    bm_to_obj,
    join_objects,
    loft_rings,
    smoothstep,
    uv_box_project,
    uv_cylindrical,
)

sys.dont_write_bytecode = True


def _torso_radius_at(z, ang, lm, female=False):
    """Return approximate anatomical body half-extent (rx, ry) + y-center at height z."""
    z_hip = lm['hip_z']
    z_wst = lm['waist_z']
    z_chs = lm['chest_z']
    z_sh = lm['sh_z']
    z_nb = lm['neck_bot'].z

    ca = math.cos(ang)
    sa = math.sin(ang)  # -1 front (-Y), +1 back (+Y)

    if z <= z_hip:
        rx = lm['pelvis_w']
        ry = lm['pelvis_d'] * (1.06 if (female and sa > 0.0) else 1.0)
        yc = 0.006
    elif z <= z_wst:
        t = smoothstep(z_hip, z_wst, z)
        rx = lm['pelvis_w'] * (1.0 - t) + lm['waist_w'] * t
        ry = lm['pelvis_d'] * (1.0 - t) + lm['waist_d'] * t
        yc = 0.006 * (1.0 - t)
    elif z <= z_chs:
        t = smoothstep(z_wst, z_chs, z)
        rx = lm['waist_w'] * (1.0 - t) + lm['torso_w'] * t
        ry = lm['waist_d'] * (1.0 - t) + lm['chest_d'] * (1.08 if sa < 0.0 else 1.0) * t
        yc = -0.003 * t
    elif z <= z_sh + 0.015:
        t = smoothstep(z_chs, z_sh + 0.015, z)
        rx = lm['torso_w'] * (1.0 - t) + lm['sh_x'] * 1.06 * t
        ry = lm['chest_d'] * (1.05 * (1.0 - t) + 0.84 * t)
        yc = -0.003 * (1.0 - t) + 0.005 * t
    else:
        t = smoothstep(z_sh + 0.015, z_nb + 0.012, z)
        nk_r = lm['head_w'] * 0.36
        rx = lm['sh_x'] * 1.02 * (1.0 - t) + nk_r * 1.15 * t
        ry = lm['chest_d'] * 0.80 * (1.0 - t) + nk_r * 1.05 * t
        yc = 0.006

    sq = 1.0 + 0.07 * (ca * ca * sa * sa)
    return rx * sq, ry * sq, yc


def _sweep_sleeve(bm, centers, radii, segs=12, cap_start=True, cap_end=True):
    n = len(centers)
    ref_fwd = Vector((0.0, -1.0, 0.0))
    tangents = []
    for i in range(n):
        t = centers[min(i + 1, n - 1)] - centers[max(i - 1, 0)]
        tangents.append(t.normalized() if t.length > 1e-6 else Vector((0.0, 0.0, -1.0)))
    rings = []
    for i, (c, (rx, ry)) in enumerate(zip(centers, radii)):
        ti = tangents[i]
        fy = ref_fwd - ti * ref_fwd.dot(ti)
        if fy.length < 1e-4:
            fy = Vector((1.0, 0.0, 0.0)) - ti * ti.x
        fy.normalize()
        fx = fy.cross(ti).normalized()
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ring.append(bm.verts.new(c + fx * (math.cos(ang) * rx) + fy * (math.sin(ang) * ry)))
        rings.append(ring)
    loft_rings(bm, rings, closed_u=True, cap_start=cap_start, cap_end=cap_end)


# ------------------------------------------------------------------ hair & beard
def build_short_hair(name, col, lm, mat_hair, beard=False, mat_beard=None):
    """Build lush sculpted short hair conforming exactly to body.head_profile_at() + optional full mentor beard."""
    hh = lm['head_h']
    z_chin = lm['chin_z']
    z_crown = lm['crown_z']

    bm = bmesh.new()
    segs = 24
    # Parameterize vertical levels from lower hairline (v=0) to crown apex (v=1)
    n_v = 10
    rings = []
    for i in range(n_v):
        v = i / (n_v - 1)  # 0 = lower hairline border, 1 = top crown center
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ca = math.cos(ang)
            sa = math.sin(ang)  # -1 = front (-Y), +1 = back (+Y)

            # Natural adult hairline height u_min(ang):
            # Back nape (+Y, sa=+1): u = 0.24
            # Sides/temples (sa=0): u = 0.50 with subtle sideburn dip to 0.44
            # Front forehead (-Y, sa=-1): u = 0.74 (clean natural forehead visible!)
            front_w = smoothstep(-0.15, 0.90, -sa)
            back_w = smoothstep(0.0, 0.85, sa)
            u_low = 0.52 + 0.22 * front_w - 0.26 * back_w
            # Gentle temple/sideburn notch
            side_w = (abs(ca) ** 4) * (1.0 - abs(sa))
            u_low -= 0.06 * side_w

            # Interpolate smoothly from hairline up to crown (u=1.0)
            u = u_low + (1.0 - u_low) * (v ** 0.88)
            rx, ry, yc = body_mod.head_profile_at(u, sa, lm)

            # Generous realistic short-hair volume (+10..15 mm outside skull, tapering smoothly to +2 mm at hairline)
            edge_fade = smoothstep(0.0, 0.22, v)
            crown_vol = 0.011 + 0.005 * smoothstep(0.55, 0.95, u)
            # Subtle natural sculpted wave/side-part thickness
            style_wave = 0.003 * (1.0 + math.sin(ang * 2.0 + 0.8)) * smoothstep(0.60, 0.95, u)
            thick = 0.002 + (crown_vol + style_wave) * edge_fade

            # Extra slight lift at crown apex so hair cleanly covers skull dome
            z = z_chin + hh * u + (0.012 + 0.004 * smoothstep(0.75, 1.0, u)) * smoothstep(0.45, 1.0, v)
            if i == n_v - 1:
                # Tight crown pole
                ring.append(bm.verts.new((ca * 0.012, yc + sa * 0.012, z_crown + 0.015)))
            else:
                ring.append(bm.verts.new((ca * (rx + thick), yc + sa * (ry + thick), min(z, z_crown + 0.016))))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=True)

    # Tuck hairline inner rim gently inside skull so zero floating shadow gap occurs at hairline
    inner_rim = []
    for v_vert in rings[0]:
        p = v_vert.co
        inner_rim.append(bm.verts.new((p.x * 0.92, p.y * 0.92, p.z + 0.002)))
    for k in range(segs):
        kn = (k + 1) % segs
        bm.faces.new((inner_rim[k], inner_rim[kn], rings[0][kn], rings[0][k]))

    hair_obj = bm_to_obj(bm, f'{name}_cap', col, mat=mat_hair, smooth=True)
    uv_cylindrical(hair_obj, scale_u=2.0, scale_v=2.0)
    parts = [hair_obj]

    if beard:
        # Full dignified neatly rounded silver-grey beard hugging chin & jawline (ZERO mouth opening!)
        # Curves gracefully down along the chin & jawline, blending into the sideburns cleanly.
        bm_b = bmesh.new()
        b_segs = 20
        n_b = 8
        b_rings = []
        for i in range(n_b):
            v = i / (n_b - 1)  # 0 = rounded beard bottom below chin -> 1 = upper cheek/jaw contour
            ring = []
            for k in range(b_segs):
                ang = (k / b_segs) * math.tau
                ca, sa = math.cos(ang), math.sin(ang)  # -1 front (-Y), +1 back (+Y)
                front = smoothstep(0.35, -0.55, sa)
                # Bottom hangs lowest right under chin (front), curves up cleanly under ears/jaw back
                u_bot = -0.15 * front + 0.08 * (1.0 - front)
                # Top cheek line: graceful curved beard cheek-line rising gently toward sideburns!
                u_top = 0.24 + 0.16 * (abs(ca) ** 1.6) * smoothstep(-0.7, 0.3, sa)
                u = u_bot + (u_top - u_bot) * v

                u_clamped = max(0.0, min(1.0, u))
                rx, ry, yc = body_mod.head_profile_at(u_clamped, sa, lm)
                # Taper softly to rounded bottom under chin
                bot_taper = smoothstep(0.0, 0.34, v)
                if i == 0:
                    rx_v = rx * 0.28
                    ry_v = ry * 0.34
                else:
                    # Generous rounded beard volume in front/jaw, tucked smoothly into jaw/neck at back
                    pad_f = (0.015 * math.sin(v * math.pi) + 0.004) * front
                    rx_v = rx * (0.48 + 0.56 * bot_taper) + pad_f * 0.75
                    ry_v = (ry * (0.52 + 0.54 * bot_taper) + pad_f) if sa < 0.0 else (ry * 0.42 * bot_taper)
                z = z_chin + hh * u
                ring.append(bm_b.verts.new((ca * rx_v, yc - 0.004 * front + sa * ry_v, z)))
            b_rings.append(ring)

        loft_rings(bm_b, b_rings, closed_u=True, cap_start=True, cap_end=True)
        beard_obj = bm_to_obj(bm_b, f'{name}_beard', col, mat=mat_beard or mat_hair, smooth=True)
        uv_cylindrical(beard_obj, scale_u=2.0, scale_v=2.0)
        parts.append(beard_obj)

    return join_objects(parts, name, col)


# ------------------------------------------------------------------ footwear
def build_shoes(name, col, lm, mat_upper, mat_sole=None, low_heel=False):
    """Build realistic sculpted closed travel/dress shoes enveloping both bare feet cleanly."""
    parts = []
    fl = lm['foot_len']
    fw = fl * 0.215
    for side in ('l', 'r'):
        s = 1.0 if side == 'l' else -1.0
        ank = lm[f'ankle_{side}']
        fx = ank.x
        y_heel = ank.y + lm['foot_y_heel'] + 0.012
        y_toe = ank.y - fl * 0.80

        bm = bmesh.new()
        z_bot = 0.010
        stations = [
            (y_heel + 0.008, fw * 0.56, z_bot + 0.056, 0.0),
            (y_heel - fl * 0.08, fw * 0.82, ank.z + 0.012, 0.0),
            (ank.y, fw * 0.86, ank.z + 0.010, 0.0),
            (ank.y - fl * 0.22, fw * 0.90, z_bot + 0.066, -s * 0.002),
            (ank.y - fl * 0.48, fw * 1.02, z_bot + 0.043, -s * 0.003),
            (ank.y - fl * 0.68, fw * 0.92, z_bot + 0.031, -s * 0.004),
            (y_toe, fw * 0.52, z_bot + 0.018, -s * 0.005),
        ]
        rings = []
        segs = 12
        for y, hw_s, z_top, x_off in stations:
            z_mid = (z_bot + z_top) * 0.5
            hz = (z_top - z_bot) * 0.5
            ring = []
            for k in range(segs):
                ang = (k / segs) * math.tau
                ca, sa = math.cos(ang), math.sin(ang)
                z = z_bot if sa < -0.55 else (z_mid + sa * hz)
                ring.append(bm.verts.new((fx + x_off + ca * hw_s, y, z)))
            rings.append(ring)
        loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)
        u_obj = bm_to_obj(bm, f'{name}_u_{side}', col, mat=mat_upper, smooth=True)
        uv_box_project(u_obj, scale=4.0)
        parts.append((side, u_obj))

        bm_s = bmesh.new()
        s_stations = [
            (y_heel + 0.010, fw * 0.60, 0.014, 0.0),
            (ank.y, fw * 0.88, 0.013, 0.0),
            (ank.y - fl * 0.45, fw * 1.05, 0.012, -s * 0.003),
            (ank.y - fl * 0.68, fw * 0.94, 0.012, -s * 0.004),
            (y_toe - 0.004, fw * 0.52, 0.011, -s * 0.005),
        ]
        s_rings = []
        for y, hw_s, zt, x_off in s_stations:
            ring = []
            for k in range(10):
                ang = (k / 10) * math.tau
                ca, sa = math.cos(ang), math.sin(ang)
                z = 0.000 if sa < 0.0 else zt
                ring.append(bm_s.verts.new((fx + x_off + ca * hw_s, y, z)))
            s_rings.append(ring)
        loft_rings(bm_s, s_rings, closed_u=True, cap_start=True, cap_end=True)
        s_obj = bm_to_obj(bm_s, f'{name}_s_{side}', col, mat=mat_sole or mat_upper, smooth=False)
        uv_box_project(s_obj, scale=4.0)
        parts.append((side, s_obj))

    return parts


def build_sandals(name, col, lm, mat_leather, mat_sole):
    """Build sleek open slip-on leather ihram sandals exposing ankles & top of foot."""
    parts = []
    fl = lm['foot_len']
    fw = fl * 0.21
    for side in ('l', 'r'):
        s = 1.0 if side == 'l' else -1.0
        ank = lm[f'ankle_{side}']
        fx = ank.x
        y_heel = ank.y + lm['foot_y_heel'] + 0.010
        y_toe = ank.y - fl * 0.79

        bm_s = bmesh.new()
        s_stations = [
            (y_heel, fw * 0.64, 0.0),
            (ank.y, fw * 0.84, 0.0),
            (ank.y - fl * 0.24, fw * 0.88, -s * 0.002),
            (ank.y - fl * 0.48, fw * 1.03, -s * 0.003),
            (ank.y - fl * 0.68, fw * 0.94, -s * 0.004),
            (y_toe, fw * 0.56, -s * 0.006),
        ]
        rings = []
        for y, hw_s, x_off in s_stations:
            ring = []
            for k in range(10):
                ang = (k / 10) * math.tau
                ca, sa = math.cos(ang), math.sin(ang)
                z = 0.000 if sa < 0.0 else 0.012
                ring.append(bm_s.verts.new((fx + x_off + ca * hw_s, y, z)))
            rings.append(ring)
        loft_rings(bm_s, rings, closed_u=True, cap_start=True, cap_end=True)
        sole_obj = bm_to_obj(bm_s, f'{name}_sole_{side}', col, mat=mat_sole, smooth=False)
        uv_box_project(sole_obj, scale=5.0)
        parts.append((side, sole_obj))

        # Two sleek contoured leather vamp straps hugging the bare instep cleanly
        bm_l = bmesh.new()
        strap_specs = [
            (ank.y - fl * 0.28, ank.y - fl * 0.39, fw * 0.93, 0.044),
            (ank.y - fl * 0.44, ank.y - fl * 0.55, fw * 0.98, 0.035),
        ]
        for y0, y1, sw, arch_h in strap_specs:
            n_u = 10
            thick = 0.004
            inner_r = []
            outer_r = []
            for i in range(n_u + 1):
                u = i / n_u
                ang = u * math.pi
                x = fx - s * 0.003 + math.cos(ang) * sw
                z = 0.010 + math.sin(ang) * arch_h
                inner_r.append((bm_l.verts.new((x, y0, z)), bm_l.verts.new((x, y1, z))))
                xo = fx - s * 0.003 + math.cos(ang) * (sw + thick)
                zo = 0.010 + math.sin(ang) * (arch_h + thick)
                outer_r.append((bm_l.verts.new((xo, y0, zo)), bm_l.verts.new((xo, y1, zo))))
            for i in range(n_u):
                bm_l.faces.new((outer_r[i][0], outer_r[i + 1][0], outer_r[i + 1][1], outer_r[i][1]))
                bm_l.faces.new((inner_r[i][1], inner_r[i + 1][1], inner_r[i + 1][0], inner_r[i][0]))
                bm_l.faces.new((inner_r[i][0], inner_r[i + 1][0], outer_r[i + 1][0], outer_r[i][0]))
                bm_l.faces.new((outer_r[i][1], outer_r[i + 1][1], inner_r[i + 1][1], inner_r[i][1]))
        strap_obj = bm_to_obj(bm_l, f'{name}_strap_{side}', col, mat=mat_leather, smooth=True)
        uv_box_project(strap_obj, scale=6.0)
        parts.append((side, strap_obj))

    return parts


# ------------------------------------------------------------------ ihram garments
def build_ihram_izar(name, col, lm, rig, mat_ihram, mat_leather, mat_sole, mat_belt):
    """Build `outfit_ihram_izar`: draped cotton lower wrap + overlap panel + belt + leather sandals."""
    z_top = lm['waist_z'] + 0.036
    z_hem = lm['ankle_z'] + 0.165
    z_hip = lm['hip_z']
    z_knee = lm['knee_z']
    pw = lm['pelvis_w']
    pd = lm['pelvis_d']
    ww = lm['waist_w']
    wd = lm['waist_d']

    bm = bmesh.new()
    segs = 28
    n_rings = 14
    rings = []
    for i in range(n_rings):
        u = i / (n_rings - 1)
        z = z_top * (1.0 - u) + z_hem * u
        if z > z_hip:
            t = smoothstep(z_top, z_hip, z)
            rx = (ww + 0.017) * (1.0 - t) + (pw + 0.028) * t
            ry = (wd + 0.017) * (1.0 - t) + (pd + 0.028) * t
        else:
            t = smoothstep(z_hip, z_hem, z)
            rx = (pw + 0.028) * (1.0 + 0.14 * t)
            ry = (pd + 0.028) * (1.0 + 0.22 * t)
        if i == 0:
            rx *= 0.94
            ry *= 0.94
        elif i == 1:
            rx += 0.006
            ry += 0.006

        pleat_amp = 0.004 + 0.010 * (u ** 1.2)
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            fold = (
                math.sin(ang * 5.0 + 0.4 + u * 0.5) * 0.55
                + math.cos(ang * 9.0 - 0.8) * 0.30
                + math.sin(ang * 3.0 + 1.1) * 0.15
            ) * pleat_amp
            stride_pad = 0.008 * smoothstep(z_hip, z_knee, z) * (sa * sa)
            ring.append(bm.verts.new((ca * (rx + fold), 0.004 + sa * (ry + fold + stride_pad), z)))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=False)

    inner_hem = [bm.verts.new((v.co.x * 0.965, v.co.y * 0.965, v.co.z + 0.008)) for v in rings[-1]]
    n = len(inner_hem)
    for k in range(n):
        kn = (k + 1) % n
        bm.faces.new((rings[-1][k], rings[-1][kn], inner_hem[kn], inner_hem[k]))

    # Overlapping front vertical wrap pleat panel (starts cleanly below the waist belt!)
    n_p = 11
    p_cols = 7
    p_grid_out = []
    p_grid_in = []
    for i in range(n_p):
        u = i / (n_p - 1)
        z = (z_top - 0.044) * (1.0 - u) + (z_hem - 0.005) * u
        if z > z_hip:
            t = smoothstep(z_top, z_hip, z)
            rx = (ww + 0.017) * (1.0 - t) + (pw + 0.028) * t
            ry = (wd + 0.017) * (1.0 - t) + (pd + 0.028) * t
        else:
            t = smoothstep(z_hip, z_hem, z)
            rx = (pw + 0.028) * (1.0 + 0.14 * t)
            ry = (pd + 0.028) * (1.0 + 0.22 * t)
        row_o = []
        row_i = []
        a_start = -math.pi * 0.5 - 0.58
        a_end = -math.pi * 0.5 + 0.34 + 0.09 * u
        for j in range(p_cols):
            v = j / (p_cols - 1)
            ang = a_start + (a_end - a_start) * v
            ca, sa = math.cos(ang), math.sin(ang)
            lift = 0.007 + 0.009 * smoothstep(0.0, 0.85, v) + 0.003 * math.sin(v * math.pi * 2.0 + u * 2.0)
            spad = 0.008 * smoothstep(z_hip, z_knee, z)
            row_o.append(bm.verts.new((ca * (rx + lift), 0.004 + sa * (ry + lift + spad), z)))
            row_i.append(bm.verts.new((ca * (rx + lift - 0.004), 0.004 + sa * (ry + lift - 0.004 + spad), z)))
        p_grid_out.append(row_o)
        p_grid_in.append(row_i)

    for i in range(n_p - 1):
        for j in range(p_cols - 1):
            bm.faces.new((p_grid_out[i][j], p_grid_out[i][j + 1], p_grid_out[i + 1][j + 1], p_grid_out[i + 1][j]))
            bm.faces.new((p_grid_in[i][j + 1], p_grid_in[i][j], p_grid_in[i + 1][j], p_grid_in[i + 1][j + 1]))
    for i in range(n_p - 1):
        bm.faces.new((p_grid_out[i][-1], p_grid_in[i][-1], p_grid_in[i + 1][-1], p_grid_out[i + 1][-1]))
    for j in range(p_cols - 1):
        bm.faces.new((p_grid_out[-1][j], p_grid_out[-1][j + 1], p_grid_in[-1][j + 1], p_grid_in[-1][j]))

    izar_obj = bm_to_obj(bm, f'{name}_wrap', col, mat=mat_ihram, smooth=True)
    uv_cylindrical(izar_obj, scale_u=2.4, scale_v=1.8)
    rig_mod.skin_izar_robe(izar_obj, rig, lm, top_z=z_top, hem_z=z_hem, calf_follow=0.68)

    # Discreet pilgrim waist belt seated cleanly outside the izar waist tuck (zero Z-fighting with rida!)
    bm_belt = bmesh.new()
    b_rings = []
    for bz in (z_top - 0.040, z_top - 0.010):
        ring = []
        for k in range(24):
            ang = (k / 24) * math.tau
            rx_b = ww + 0.032
            ry_b = wd + 0.032
            ring.append(bm_belt.verts.new((math.cos(ang) * rx_b, 0.004 + math.sin(ang) * ry_b, bz)))
        b_rings.append(ring)
    loft_rings(bm_belt, b_rings, closed_u=True, cap_start=False, cap_end=False)
    add_box(bm_belt, (-ww * 0.42, -(wd + 0.036), z_top - 0.025), (0.064, 0.014, 0.032), rot_z=-0.22)
    belt_obj = bm_to_obj(bm_belt, f'{name}_belt', col, mat=mat_belt, smooth=False)
    uv_box_project(belt_obj, scale=4.0)
    rig_mod.skin_izar_robe(belt_obj, rig, lm, top_z=z_top, hem_z=z_hem, calf_follow=0.0)

    sandal_parts = build_sandals(f'{name}_sandals', col, lm, mat_leather, mat_sole)
    skinned_sandals = []
    for side, sobj in sandal_parts:
        rig_mod.skin_rigid(sobj, rig, f'foot_{side}')
        skinned_sandals.append(sobj)

    out = join_objects([izar_obj, belt_obj] + skinned_sandals, name, col)
    rig_mod.bind_armature(out, rig)
    rig_mod.validate_skinning(out, rig)
    return out


def build_ihram_rida_covered(name, col, lm, rig, mat_ihram):
    """Build `outfit_ihram_rida_covered`: white cotton upper ihram shawl draping smoothly over BOTH shoulders."""
    z_nb = lm['neck_bot'].z + 0.010
    z_sh = lm['sh_z']
    z_chs = lm['chest_z']
    z_wst = lm['waist_z']
    # Tuck lower edge neatly right above waist belt (or drape cleanly over waist without Z-fighting!)
    z_bot = z_wst + 0.030
    nk_r = lm['head_w'] * 0.37

    bm = bmesh.new()
    segs = 28
    # Explicitly sculpt a soft gravity-draped shoulder mantle over BOTH shoulders (no stiff wings, zero skin peek!)
    # (z, extra_x, extra_y, arm_drape_x, neck_dip_front)
    stations = [
        (z_nb + 0.014, 0.008, 0.012, 0.000, 0.045),  # snug neck collar edge
        (z_nb - 0.002, 0.022, 0.022, 0.014, 0.032),  # upper trapezius
        (z_sh + 0.038, 0.030, 0.028, 0.028, 0.014),  # cleanly domes OVER bare deltoid top!
        (z_sh + 0.012, 0.028, 0.030, 0.038, 0.000),  # rounded outer shoulder curve
        (z_sh - 0.026, 0.026, 0.030, 0.042, 0.000),  # soft downward upper-arm drape
        (z_sh - 0.068, 0.024, 0.028, 0.034, 0.000),  # tapering gently back toward torso
        (z_chs + 0.010, 0.023, 0.028, 0.016, 0.000),
        (z_wst + (z_chs - z_wst) * 0.55, 0.023, 0.026, 0.004, 0.000),
        (z_wst + (z_chs - z_wst) * 0.25, 0.022, 0.024, 0.000, 0.000),
        (z_bot, 0.020, 0.022, 0.000, 0.000),
    ]

    rings = []
    for idx, (z, ex, ey, arm_x, ndip) in enumerate(stations):
        u = idx / (len(stations) - 1)
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            rx, ry, yc = _torso_radius_at(z, ang, lm, female=False)
            if idx == 0:
                rx = nk_r * 1.18
                ry = nk_r * 1.08
                yc = 0.006
            elif idx == 1:
                rx = max(rx, lm['sh_x'] * 0.72)
                ry = max(ry, lm['chest_d'] * 0.72)
            # Soft rounded shoulder drape hugging deltoids downward (zero stiff wings!)
            cap_x = arm_x * (abs(ca) ** 1.4)
            fold = (
                math.sin(ang * 4.0 + u * 3.2) * 0.0055
                + math.cos(ang * 7.0 - u * 2.0) * 0.0030
            ) * smoothstep(0.15, 0.55, u)
            z_v = z - ndip * (max(0.0, -sa) ** 1.8)
            ring.append(bm.verts.new((ca * (rx + ex + cap_x + fold), yc + sa * (ry + ey + fold), z_v)))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=False)

    # Rolled collar & hem thickness
    for r_idx, dz, sc_in in ((0, -0.008, 0.92), (-1, 0.008, 0.94)):
        inner = [bm.verts.new((v.co.x * sc_in, v.co.y * sc_in, v.co.z + dz)) for v in rings[r_idx]]
        n = len(inner)
        for k in range(n):
            kn = (k + 1) % n
            if r_idx == 0:
                bm.faces.new((inner[k], inner[kn], rings[0][kn], rings[0][k]))
            else:
                bm.faces.new((rings[-1][k], rings[-1][kn], inner[kn], inner[k]))

    # Natural overlapping diagonal front cloth fold across chest (stops cleanly above belt!)
    n_u = 12
    n_v = 7
    grid_o, grid_i = [], []
    for i in range(n_u):
        u = i / (n_u - 1)
        row_o, row_i = [], []
        for j in range(n_v):
            v = j / (n_v - 1)
            ang = (-math.pi * 0.76) * (1.0 - u) + 0.14 * u + (v - 0.5) * 0.36
            z = (z_bot + 0.025) * (1.0 - u) + (z_sh + 0.036) * u - (v - 0.5) * 0.12
            z = max(z_bot + 0.008, min(z_nb + 0.006, z))
            rx, ry, yc = _torso_radius_at(z, ang, lm, female=False)
            ca, sa = math.cos(ang), math.sin(ang)
            sh_b = smoothstep(z_chs, z_sh + 0.02, z)
            arch = math.sin(v * math.pi)
            off_x = 0.030 + 0.011 * arch + 0.048 * sh_b * (abs(ca) ** 1.4)
            off_y = 0.034 + 0.011 * arch
            row_o.append(bm.verts.new((ca * (rx + off_x), yc + sa * (ry + off_y), z)))
            row_i.append(bm.verts.new((ca * (rx + off_x - 0.006), yc + sa * (ry + off_y - 0.006), z)))
        grid_o.append(row_o)
        grid_i.append(row_i)

    for i in range(n_u - 1):
        for j in range(n_v - 1):
            bm.faces.new((grid_o[i][j], grid_o[i][j + 1], grid_o[i + 1][j + 1], grid_o[i + 1][j]))
            bm.faces.new((grid_i[i][j + 1], grid_i[i][j], grid_i[i + 1][j], grid_i[i + 1][j + 1]))

    obj = bm_to_obj(bm, name, col, mat=mat_ihram, smooth=True)
    uv_cylindrical(obj, scale_u=2.2, scale_v=1.8)
    rig_mod.skin_upper_garment(obj, rig, lm, mode='rida_covered')
    rig_mod.validate_skinning(obj, rig)
    return obj


def build_ihram_rida_idtiba(name, col, lm, rig, mat_ihram):
    """Build `outfit_ihram_rida_idtiba`: diagonal shawl under RIGHT armpit (-X), smoothly over LEFT shoulder (+X).

    STRICT CHECK:
    - Character faces -Y, +Z up -> LEFT is +X, RIGHT is -X.
    - RIGHT shoulder (-X) & right upper arm are 100% BARE & UNCOVERED!
    - LEFT shoulder (+X) is smoothly covered by natural rounded cotton drape (no shoulder holes or flared wings!).
    """
    z_nb = lm['neck_bot'].z + 0.010
    z_sh = lm['sh_z']
    z_chs = lm['chest_z']
    z_wst = lm['waist_z']
    z_bot = z_wst + 0.030  # stops cleanly above belt (zero Z-fighting with belt!)

    # Under right armpit (-X): cleanly below the right axilla/deltoid
    z_under_right = z_chs - 0.040
    # Over left shoulder (+X): wraps cleanly over left trapezius & rounded left deltoid
    z_over_left = z_nb + 0.004

    bm = bmesh.new()
    segs = 32
    n_rings = 14
    rings = []

    for i in range(n_rings):
        u = i / (n_rings - 1)  # 0 = top diagonal edge, 1 = waist hem
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ca = math.cos(ang)  # +1 = LEFT (+X), -1 = RIGHT (-X)
            sa = math.sin(ang)  # -1 = front (-Y), +1 = back (+Y)

            u_left = 0.5 + 0.5 * ca  # 1.0 at LEFT (+X), 0.0 at RIGHT (-X)
            z_top_ang = z_under_right + (z_over_left - z_under_right) * smoothstep(0.06, 0.88, u_left)
            z_top_ang -= 0.018 * (sa * sa) * smoothstep(0.15, 0.78, u_left)

            z = z_top_ang * (1.0 - u) + z_bot * u
            rx, ry, yc = _torso_radius_at(z, ang, lm, female=False)

            # Soft downward left-shoulder drape cap ONLY on LEFT (+X) (hugs deltoid, zero stiff wing!)
            left_cap = 0.0
            if ca > 0.12:
                sh_dome = smoothstep(z_chs - 0.04, z_sh - 0.02, z) * (1.0 - smoothstep(z_sh + 0.020, z_nb + 0.012, z))
                left_cap = 0.036 * sh_dome * (max(0.0, ca) ** 1.35)

            diag_phase = (u * 5.0 - u_left * 3.0) * math.pi
            fold = (
                math.sin(diag_phase) * 0.0060
                + math.cos(ang * 6.0 + u * 4.0) * 0.0030
            ) * smoothstep(0.05, 0.30, u)

            edge_roll = 0.007 * (1.0 - smoothstep(0.0, 0.14, u))
            pad_x = 0.020 + left_cap + edge_roll + fold
            pad_y = 0.024 + 0.008 * (left_cap / 0.036) + edge_roll + fold
            ring.append(bm.verts.new((ca * (rx + pad_x), yc + sa * (ry + pad_y), z)))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=False)

    # Rolled top diagonal edge & lower waist hem
    for r_idx, dz, scale_in in ((0, -0.010, 0.935), (-1, 0.008, 0.95)):
        inner = [bm.verts.new((v.co.x * scale_in, v.co.y * scale_in, v.co.z + dz)) for v in rings[r_idx]]
        n = len(inner)
        for k in range(n):
            kn = (k + 1) % n
            if r_idx == 0:
                bm.faces.new((inner[k], inner[kn], rings[0][kn], rings[0][k]))
            else:
                bm.faces.new((rings[-1][k], rings[-1][kn], inner[kn], inner[k]))

    # Smooth solid left-shoulder cloth cap + diagonal chest sash hugging left deltoid softly
    n_u = 16
    n_v = 8
    grid_o, grid_i = [], []
    for i in range(n_u):
        u = i / (n_u - 1)
        ang_c = -math.pi * 0.92 * (1.0 - u) + (math.pi * 0.52) * u
        sh_peak = math.exp(-((u - 0.64) / 0.25) ** 2)
        z_c = (z_under_right - 0.018) + (z_sh + 0.034 - (z_under_right - 0.018)) * sh_peak
        if u > 0.70:
            z_c -= smoothstep(0.70, 1.0, u) * 0.16

        row_o, row_i = [], []
        for j in range(n_v):
            v = j / (n_v - 1)
            ang = ang_c + (v - 0.5) * 0.20
            ca, sa = math.cos(ang), math.sin(ang)
            z = z_c + (0.5 - v) * (0.120 - 0.035 * sh_peak)
            if ca < 0.0:
                max_z_right = z_under_right + 0.042 * (1.0 + ca)
                z = min(z, max_z_right)
            z = max(z_bot + 0.012, min(z_nb + 0.010, z))

            rx, ry, yc = _torso_radius_at(z, ang, lm, female=False)
            arch = math.sin(v * math.pi)
            sh_dome = smoothstep(z_chs - 0.04, z_sh - 0.02, z) * (1.0 - smoothstep(z_sh + 0.020, z_nb + 0.012, z))
            l_cap = 0.038 * sh_dome * (max(0.0, ca) ** 1.35)
            z_lift = 0.014 * sh_peak * (1.0 - v * 0.45)
            off_x = 0.028 + 0.009 * arch + l_cap
            off_y = 0.032 + 0.009 * arch
            row_o.append(bm.verts.new((ca * (rx + off_x), yc + sa * (ry + off_y), z + z_lift)))
            row_i.append(bm.verts.new((ca * (rx + off_x - 0.007), yc + sa * (ry + off_y - 0.007), z + z_lift - 0.005)))
        grid_o.append(row_o)
        grid_i.append(row_i)

    for i in range(n_u - 1):
        for j in range(n_v - 1):
            bm.faces.new((grid_o[i][j], grid_o[i][j + 1], grid_o[i + 1][j + 1], grid_o[i + 1][j]))
            bm.faces.new((grid_i[i][j + 1], grid_i[i][j], grid_i[i + 1][j], grid_i[i + 1][j + 1]))
    for i in range(n_u - 1):
        bm.faces.new((grid_o[i][0], grid_i[i][0], grid_i[i + 1][0], grid_o[i + 1][0]))
        bm.faces.new((grid_i[i][-1], grid_o[i][-1], grid_o[i + 1][-1], grid_i[i + 1][-1]))

    obj = bm_to_obj(bm, name, col, mat=mat_ihram, smooth=True)
    uv_cylindrical(obj, scale_u=2.2, scale_v=1.8)
    rig_mod.skin_upper_garment(obj, rig, lm, mode='rida_idtiba')
    rig_mod.validate_skinning(obj, rig)
    return obj


# ------------------------------------------------------------------ tailored shirts, blazers, trousers, skirts, hijab
def _build_shirt_top(
    name,
    col,
    lm,
    rig,
    mat_shirt,
    mat_trim=None,
    female=False,
    blazer=False,
    tucked=False,
    tie_mat=None,
    badge_mat=None,
):
    """Build tailored collared shirt or blazer with closed shoulder yoke, smooth sleeves, zero Z-fighting."""
    z_nb = lm['neck_bot'].z
    z_sh = lm['sh_z']
    z_chs = lm['chest_z']
    z_wst = lm['waist_z']
    z_hip = lm['hip_z']
    # Tucked shirts stop neatly at waist inside trouser waistband; untucked/blazers flare cleanly outside hips!
    z_hem = (z_wst - 0.025) if tucked else (z_hip - (0.065 if blazer else 0.040))
    sc = lm['height'] / 1.76 * (0.86 if female else 1.0)
    nk_r = lm['head_w'] * 0.37

    parts = []

    # 1. Torso shirt/blazer shell with CLOSED shoulder yoke from collar out to shoulders!
    bm = bmesh.new()
    segs = 24
    pad = 0.013 if tucked else (0.025 if blazer else 0.025)
    z_stations = [
        z_nb + 0.012,
        z_nb - 0.006,
        z_sh + 0.020,
        z_sh - 0.015,
        z_chs + 0.045,
        z_chs - 0.015,
        z_wst + (z_chs - z_wst) * 0.45,
        z_wst,
    ]
    if not tucked:
        z_stations.extend([
            z_hip + (z_wst - z_hip) * 0.45,
            z_hip - 0.010,
            z_hem,
        ])
    else:
        z_stations.append(z_hem)

    rings = []
    for idx, z in enumerate(z_stations):
        u = idx / (len(z_stations) - 1)
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            rx, ry, yc = _torso_radius_at(z, ang, lm, female=female)
            if idx == 0:
                rx = nk_r * 1.06
                ry = nk_r * 1.02
                yc = 0.005
                ex, ey = 0.008, 0.008
            elif idx == 1:
                rx = max(rx, lm['sh_x'] * 0.72)
                ry = max(ry, lm['chest_d'] * 0.68)
                ex, ey = pad * 0.85, pad * 0.85
            else:
                if not tucked:
                    # Generous clean clearance outside trouser waistband & seat (zero back poke-through!)
                    hip_flare = 0.015 * smoothstep(z_chs - 0.06, z_hem, z)
                else:
                    # Tucked shirt tapers cleanly INSIDE trouser waistband below waist!
                    hip_flare = -0.008 * smoothstep(z_wst + 0.04, z_hem, z)
                ex = pad + hip_flare
                ey = pad + hip_flare
            fold = 0.0025 * math.sin(ang * 6.0) * smoothstep(0.35, 1.0, u)
            z_v = z
            if idx == 0 and sa < 0.0:
                z_v -= (0.032 if blazer else 0.018) * ((-sa) ** 2.2)
            ring.append(bm.verts.new((ca * (rx + ex + fold), yc + sa * (ry + ey + fold), z_v)))
        rings.append(ring)
    loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=True)

    # Crisp standing collar band hugging neck cleanly
    c_rings = []
    for cz, dr in ((z_nb + 0.002, 0.008), (z_nb + 0.032, 0.011), (z_nb + 0.038, 0.005)):
        ring = []
        for k in range(20):
            ang = (k / 20) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            z_v = cz - (0.022 if sa < 0.0 else 0.0) * ((-sa) ** 2.0)
            ring.append(bm.verts.new((ca * (nk_r + dr), 0.005 + sa * (nk_r + dr), z_v)))
        c_rings.append(ring)
    loft_rings(bm, c_rings, closed_u=True, cap_start=False, cap_end=False)

    # Smooth tailored long sleeves merging organically into rounded shoulder slope (zero step!)
    for side in ('l', 'r'):
        s = 1.0 if side == 'l' else -1.0
        sh = lm[f'sh_{side}']
        elb = lm[f'elb_{side}']
        wri = lm[f'wri_{side}']
        u_dir = elb - sh
        l_dir = wri - elb
        u_unit = u_dir.normalized()
        s_pad = 0.015 if blazer else 0.013
        sh_c = sh + Vector((-s * 0.012, 0.002, -0.001))

        centers = [
            sh_c - u_unit * (0.046 * sc) + Vector((-s * 0.018, 0.0, 0.004)),
            sh_c - u_unit * (0.022 * sc) + Vector((-s * 0.006, 0.0, 0.003)),
            sh_c,
            sh + u_dir * 0.22,
            sh + u_dir * 0.62,
            elb,
            elb + l_dir * 0.36,
            elb + l_dir * 0.78,
            wri - l_dir.normalized() * 0.014,
        ]
        radii = [
            (0.022 * sc, 0.022 * sc),
            (0.050 * sc + s_pad * 0.65, 0.048 * sc + s_pad * 0.65),
            (0.056 * sc + s_pad, 0.054 * sc + s_pad),
            (0.050 * sc + s_pad, 0.051 * sc + s_pad),
            (0.045 * sc + s_pad, 0.046 * sc + s_pad),
            (0.043 * sc + s_pad, 0.043 * sc + s_pad),
            (0.042 * sc + s_pad, 0.043 * sc + s_pad),
            (0.036 * sc + s_pad, 0.035 * sc + s_pad),
            (0.033 * sc + s_pad * 0.8, 0.029 * sc + s_pad * 0.8),
        ]
        _sweep_sleeve(bm, centers, radii, segs=12, cap_start=True, cap_end=True)

    shirt_obj = bm_to_obj(bm, f'{name}_body', col, mat=mat_shirt, smooth=True)
    uv_cylindrical(shirt_obj, scale_u=2.6, scale_v=2.0)
    rig_mod.skin_upper_garment(shirt_obj, rig, lm, mode='shirt')
    parts.append(shirt_obj)

    # Tailored inner shirt V-insert for blazers (clean V-shape tucked neatly at front chest)
    if blazer and mat_trim is not None:
        bm_t = bmesh.new()
        t_rings = []
        for tz, w_v in (
            (z_nb + 0.010, 0.038),
            (z_sh + 0.008, 0.044),
            (z_chs + 0.042, 0.030),
            (z_chs - 0.015, 0.005),
        ):
            _, ry, yc = _torso_radius_at(tz, -math.pi * 0.5, lm, female=female)
            yf = yc - (ry + pad + 0.004)
            t_rings.append([
                bm_t.verts.new((-w_v, yf + 0.005, tz)),
                bm_t.verts.new((0.0, yf - 0.002, tz)),
                bm_t.verts.new((w_v, yf + 0.005, tz)),
            ])
        loft_rings(bm_t, t_rings, closed_u=False, cap_start=False, cap_end=False)
        trim_obj = bm_to_obj(bm_t, f'{name}_trim', col, mat=mat_trim, smooth=True)
        uv_box_project(trim_obj, scale=5.0)
        rig_mod.skin_upper_garment(trim_obj, rig, lm, mode='shirt')
        parts.append(trim_obj)

    if tie_mat is not None:
        bm_tie = bmesh.new()
        tie_pts = [
            (z_nb - 0.004, 0.016),
            (z_sh - 0.010, 0.012),
            (z_chs + 0.020, 0.021),
            (z_wst + 0.055, 0.025),
            (z_wst + 0.015, 0.005),
        ]
        t_rings = []
        for tz, hw_t in tie_pts:
            _, ry, yc = _torso_radius_at(tz, -math.pi * 0.5, lm, female=female)
            yf = yc - (ry + pad + 0.005)
            t_rings.append([
                bm_tie.verts.new((-hw_t, yf + 0.004, tz)),
                bm_tie.verts.new((0.0, yf - 0.003, tz)),
                bm_tie.verts.new((hw_t, yf + 0.004, tz)),
            ])
        loft_rings(bm_tie, t_rings, closed_u=False, cap_start=False, cap_end=False)
        tie_obj = bm_to_obj(bm_tie, f'{name}_tie', col, mat=tie_mat, smooth=False)
        uv_box_project(tie_obj, scale=6.0)
        rig_mod.skin_upper_garment(tie_obj, rig, lm, mode='shirt')
        parts.append(tie_obj)

    if badge_mat is not None:
        bm_bg = bmesh.new()
        tz = z_chs + 0.032
        _, ry, yc = _torso_radius_at(tz, -math.pi * 0.5, lm, female=female)
        yf = yc - (ry + pad + 0.005)
        bx = lm['torso_w'] * 0.44
        size = (0.042, 0.007, 0.054) if not blazer else (0.034, 0.007, 0.016)
        add_box(bm_bg, (bx, yf, tz), size)
        bg_obj = bm_to_obj(bm_bg, f'{name}_badge', col, mat=badge_mat, smooth=False)
        uv_box_project(bg_obj, scale=8.0)
        rig_mod.skin_upper_garment(bg_obj, rig, lm, mode='shirt')
        parts.append(bg_obj)

    return parts


def _build_trousers(name, col, lm, rig, mat_trousers, mat_belt=None):
    """Build tailored split-leg trousers enveloping pelvis and legs cleanly down to ankles."""
    z_wst = lm['waist_z'] + 0.020
    z_hip = lm['hip_z']
    z_ank = lm['ankle_z'] + 0.002
    pw = lm['pelvis_w']
    pd = lm['pelvis_d']
    ww = lm['waist_w']
    wd = lm['waist_d']
    sc = lm['height'] / 1.76

    bm = bmesh.new()
    p_rings = []
    for z, rx, ry in (
        (z_wst, ww + 0.017, wd + 0.017),
        (z_hip + (z_wst - z_hip) * 0.45, pw + 0.016, pd + 0.016),
        (z_hip - 0.008, pw + 0.018, pd + 0.018),
        (z_hip - 0.055, pw * 0.96 + 0.016, pd * 0.96 + 0.016),
    ):
        ring = [bm.verts.new((math.cos(k / 20 * math.tau) * rx, 0.004 + math.sin(k / 20 * math.tau) * ry, z)) for k in range(20)]
        p_rings.append(ring)
    loft_rings(bm, p_rings, closed_u=True, cap_start=True, cap_end=True)

    for side in ('l', 'r'):
        hip = lm[f'hip_{side}']
        knee = lm[f'knee_{side}']
        ank = lm[f'ankle_{side}']
        t_dir = knee - hip
        c_dir = ank - knee
        centers = [
            hip + Vector((0.0, 0.004, 0.010)),
            hip + t_dir * 0.25,
            hip + t_dir * 0.62,
            knee,
            knee + c_dir * 0.30,
            knee + c_dir * 0.68,
            Vector((ank.x, ank.y, z_ank)),
        ]
        radii = [
            (0.086 * sc, 0.088 * sc),
            (0.080 * sc, 0.083 * sc),
            (0.070 * sc, 0.073 * sc),
            (0.064 * sc, 0.066 * sc),
            (0.062 * sc, 0.065 * sc),
            (0.056 * sc, 0.058 * sc),
            (0.051 * sc, 0.053 * sc),
        ]
        _sweep_sleeve(bm, centers, radii, segs=12, cap_start=True, cap_end=True)

    tr_obj = bm_to_obj(bm, f'{name}_legs', col, mat=mat_trousers, smooth=True)
    uv_cylindrical(tr_obj, scale_u=2.4, scale_v=1.8)
    rig_mod.skin_trousers(tr_obj, rig, lm, include_shoes=False)
    parts = [tr_obj]

    if mat_belt is not None:
        bm_b = bmesh.new()
        b_rings = []
        for bz in (z_wst - 0.032, z_wst + 0.008):
            ring = [
                bm_b.verts.new((math.cos(k / 20 * math.tau) * (ww + 0.024), 0.004 + math.sin(k / 20 * math.tau) * (wd + 0.024), bz))
                for k in range(20)
            ]
            b_rings.append(ring)
        loft_rings(bm_b, b_rings, closed_u=True, cap_start=False, cap_end=False)
        b_obj = bm_to_obj(bm_b, f'{name}_belt', col, mat=mat_belt, smooth=False)
        uv_box_project(b_obj, scale=5.0)
        rig_mod.skin_trousers(b_obj, rig, lm, include_shoes=False)
        parts.append(b_obj)

    return parts


def build_street_outfit(name, col, lm, rig, mat_shirt, mat_trousers, mat_shoe, mat_sole, mat_belt):
    """Build `outfit_street` (untucked collared travel shirt + tailored trousers + travel shoes)."""
    parts = []
    parts.extend(_build_shirt_top(f'{name}_sh', col, lm, rig, mat_shirt, female=False, blazer=False, tucked=False))
    parts.extend(_build_trousers(f'{name}_tr', col, lm, rig, mat_trousers, mat_belt=None))
    for side, sobj in build_shoes(f'{name}_shoe', col, lm, mat_shoe, mat_sole):
        rig_mod.skin_rigid(sobj, rig, f'foot_{side}')
        parts.append(sobj)
    out = join_objects(parts, name, col)
    rig_mod.bind_armature(out, rig)
    rig_mod.validate_skinning(out, rig)
    return out


def build_attendant_outfit(col, lm, rig, mat_burgundy, mat_cream, mat_gold, mat_shoe, mat_sole):
    """Build flight attendant's modest burgundy blazer, long A-line skirt, draped open-face hijab & low shoes."""
    hh = lm['head_h']
    hw = lm['head_w'] * 0.5
    hd = lm['head_d'] * 0.5
    z_chin = lm['chin_z']
    z_crown = lm['crown_z']
    z_sh = lm['sh_z']
    z_nb = lm['neck_bot'].z

    # 1. Draped burgundy hijab cleanly framing the smooth faceless oval head (open front face window!)
    # Built as a smooth hood wrapping back, crown, temples, under-chin & neck/collar drape.
    bm_h = bmesh.new()
    # Part A: Clean hijab neck wrap tucking neatly into blazer neckline (zero Z-fighting with cream silk V-trim!)
    segs_n = 22
    n_rings = []
    neck_levels = [
        (z_nb - 0.022, hw * 1.10, hd * 1.02, 0.004, 0.012),
        (z_nb + 0.010, hw * 0.98, hd * 0.88, 0.003, 0.000),
        (z_chin - 0.008, hw * 0.92, hd * 0.88, -0.003, 0.000),
    ]
    for z, rx, ry, yc, front_dip in neck_levels:
        ring = []
        for k in range(segs_n):
            ang = (k / segs_n) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            z_v = z - front_dip * (max(0.0, -sa) ** 1.6)
            ring.append(bm_h.verts.new((ca * rx, yc + sa * ry, z_v)))
        n_rings.append(ring)
    loft_rings(bm_h, n_rings, closed_u=True, cap_start=False, cap_end=False)

    # Part B: Open-front hijab hood hugging temples, cheeks, crown & occiput (leaves oval face 100% visible!)
    # Sweep open arc around head from front-right cheek (-pi*0.5 + gap) around back (+pi/2) to front-left (-pi*0.5 - gap)
    n_u = 10
    n_a = 19
    hood_o, hood_i = [], []
    for i in range(n_u):
        v = i / (n_u - 1)  # 0 = under-chin / jaw base -> 1 = top crown
        u = 0.02 + 0.98 * v
        row_o, row_i = [], []
        # Face opening half-angle widest across mid-face (u=0.25..0.75), narrowing cleanly at chin (0) & forehead (0.85)
        face_open = 0.98 * math.sin(min(1.0, max(0.0, (u - 0.02) / 0.86)) * math.pi) ** 0.72
        if u > 0.86:
            face_open = 0.0
        a_start = -math.pi * 0.5 + face_open
        a_end = math.pi * 1.5 - face_open
        for j in range(n_a):
            s_t = j / (n_a - 1)
            ang = a_start + (a_end - a_start) * s_t
            ca, sa = math.cos(ang), math.sin(ang)
            rx, ry, yc = body_mod.head_profile_at(u, sa, lm)
            # Plush draped hijab clearance (+12..18 mm over skull & back bun volume)
            back_drape = 0.016 * max(0.0, sa) * smoothstep(0.20, 0.75, u)
            pad_h = 0.012 + back_drape
            z = z_chin + hh * u + 0.015 * smoothstep(0.65, 1.0, u)
            xo, yo = ca * (rx + pad_h), yc + sa * (ry + pad_h)
            xi, yi = ca * (rx + 0.004), yc + sa * (ry + 0.004)
            if i == n_u - 1:
                xo, yo = ca * 0.015, yc + sa * 0.015
                xi, yi = ca * 0.010, yc + sa * 0.010
                z = z_crown + 0.020
            row_o.append(bm_h.verts.new((xo, yo, z)))
            row_i.append(bm_h.verts.new((xi, yi, z)))
        hood_o.append(row_o)
        hood_i.append(row_i)

    for i in range(n_u - 1):
        for j in range(n_a - 1):
            bm_h.faces.new((hood_o[i][j], hood_o[i][j + 1], hood_o[i + 1][j + 1], hood_o[i + 1][j]))
            bm_h.faces.new((hood_i[i][j + 1], hood_i[i][j], hood_i[i + 1][j], hood_i[i + 1][j + 1]))
    # Stitch clean rolled face-framing front hem edges!
    for i in range(n_u - 1):
        bm_h.faces.new((hood_o[i][0], hood_i[i][0], hood_i[i + 1][0], hood_o[i + 1][0]))
        bm_h.faces.new((hood_i[i][-1], hood_o[i][-1], hood_o[i + 1][-1], hood_i[i + 1][-1]))

    hijab_main = bm_to_obj(bm_h, 'hijab_main', col, mat=mat_burgundy, smooth=True)
    uv_cylindrical(hijab_main, scale_u=2.2, scale_v=1.8)
    rig_mod.skin_headwear(hijab_main, rig, lm, drape_shoulders=True)

    # Cream silk inner under-cap neatly visible across upper forehead arch
    bm_uc = bmesh.new()
    u_rings = []
    for u_val in (0.76, 0.86):
        ring = []
        for j in range(13):
            ang = -math.pi * 0.5 - 1.15 + (2.30 * j / 12)
            ca, sa = math.cos(ang), math.sin(ang)
            rx, ry, yc = body_mod.head_profile_at(u_val, sa, lm)
            z = z_chin + hh * u_val - 0.008 * max(0.0, -sa)
            ring.append(bm_uc.verts.new((ca * (rx + 0.007), yc + sa * (ry + 0.007), z)))
        u_rings.append(ring)
    loft_rings(bm_uc, u_rings, closed_u=False, cap_start=False, cap_end=False)
    uc_obj = bm_to_obj(bm_uc, 'hijab_trim', col, mat=mat_cream, smooth=True)
    uv_cylindrical(uc_obj, scale_u=2.0, scale_v=2.0)
    rig_mod.skin_rigid(uc_obj, rig, 'head')

    hijab_obj = join_objects([hijab_main, uc_obj], 'hijab', col)
    rig_mod.bind_armature(hijab_obj, rig)
    rig_mod.validate_skinning(hijab_obj, rig)

    # 2. Modest tailored burgundy blazer + cream silk collar accent + gold wing pin + long A-line skirt + shoes
    u_parts = []
    u_parts.extend(
        _build_shirt_top(
            'att_blazer', col, lm, rig, mat_burgundy,
            mat_trim=mat_cream, female=True, blazer=True, tucked=False, badge_mat=mat_gold,
        )
    )

    z_top = lm['waist_z'] + 0.015
    z_hem = lm['ankle_z'] + 0.025
    z_hip = lm['hip_z']
    bm_sk = bmesh.new()
    segs_s = 26
    n_r = 12
    sk_rings = []
    for i in range(n_r):
        u = i / (n_r - 1)
        z = z_top * (1.0 - u) + z_hem * u
        if z > z_hip:
            t = smoothstep(z_top, z_hip, z)
            rx = (lm['waist_w'] + 0.014) * (1.0 - t) + (lm['pelvis_w'] + 0.020) * t
            ry = (lm['waist_d'] + 0.014) * (1.0 - t) + (lm['pelvis_d'] + 0.022) * t
        else:
            t = smoothstep(z_hip, z_hem, z)
            rx = (lm['pelvis_w'] + 0.020) * (1.0 + 0.44 * t)
            ry = (lm['pelvis_d'] + 0.022) * (1.0 + 0.46 * t)
        pleat = 0.008 * (u ** 1.3)
        ring = []
        for k in range(segs_s):
            ang = (k / segs_s) * math.tau
            f = math.sin(ang * 6.0) * pleat
            ring.append(bm_sk.verts.new((math.cos(ang) * (rx + f), 0.004 + math.sin(ang) * (ry + f), z)))
        sk_rings.append(ring)
    loft_rings(bm_sk, sk_rings, closed_u=True, cap_start=True, cap_end=False)
    sk_obj = bm_to_obj(bm_sk, 'att_skirt', col, mat=mat_burgundy, smooth=True)
    uv_cylindrical(sk_obj, scale_u=2.5, scale_v=1.8)
    rig_mod.skin_izar_robe(sk_obj, rig, lm, top_z=z_top, hem_z=z_hem, calf_follow=0.65)
    u_parts.append(sk_obj)

    for side, sobj in build_shoes('att_shoe', col, lm, mat_shoe, mat_sole, low_heel=True):
        rig_mod.skin_rigid(sobj, rig, f'foot_{side}')
        u_parts.append(sobj)

    uniform_obj = join_objects(u_parts, 'outfit_uniform', col)
    rig_mod.bind_armature(uniform_obj, rig)
    rig_mod.validate_skinning(uniform_obj, rig)
    return hijab_obj, uniform_obj


def build_guide_outfit(col, lm, rig, mat_blazer, mat_white, mat_gold, mat_trousers, mat_shoe, mat_sole, mat_belt):
    """Build Makkah hotel/Haram hospitality guide uniform (navy blazer, white shirt, gold pin, trousers, dress shoes)."""
    parts = []
    parts.extend(
        _build_shirt_top(
            'guide_top', col, lm, rig, mat_blazer,
            mat_trim=mat_white, female=False, blazer=True, tucked=False, badge_mat=mat_gold,
        )
    )
    parts.extend(_build_trousers('guide_tr', col, lm, rig, mat_trousers, mat_belt=None))
    for side, sobj in build_shoes('guide_shoe', col, lm, mat_shoe, mat_sole):
        rig_mod.skin_rigid(sobj, rig, f'foot_{side}')
        parts.append(sobj)
    out = join_objects(parts, 'outfit_uniform', col)
    rig_mod.bind_armature(out, rig)
    rig_mod.validate_skinning(out, rig)
    return out


def build_agent_outfit(col, lm, rig, mat_shirt, mat_tie, mat_badge, mat_trousers, mat_shoe, mat_sole, mat_belt):
    """Build airport airline check-in agent uniform (tucked navy collared shirt, tie, chest badge, belt, trousers, shoes)."""
    parts = []
    parts.extend(
        _build_shirt_top(
            'agent_top', col, lm, rig, mat_shirt,
            female=False, blazer=False, tucked=True, tie_mat=mat_tie, badge_mat=mat_badge,
        )
    )
    parts.extend(_build_trousers('agent_tr', col, lm, rig, mat_trousers, mat_belt=mat_belt))
    for side, sobj in build_shoes('agent_shoe', col, lm, mat_shoe, mat_sole):
        rig_mod.skin_rigid(sobj, rig, f'foot_{side}')
        parts.append(sobj)
    out = join_objects(parts, 'outfit_uniform', col)
    rig_mod.bind_armature(out, rig)
    rig_mod.validate_skinning(out, rig)
    return out
