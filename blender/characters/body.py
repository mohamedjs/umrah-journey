"""Realistic anatomical faceless base body mesh generator for umrah-journey.

STRICT ART & RELIGIOUS RULES:
- ZERO facial features: smooth sculptural anatomical oval head with clean jaw/chin/cranium
  contour and smooth neck transition. NO eyes, NO orbital sockets, NO nose, NO mouth,
  NO eyebrows, NO eyelids, NO painted face details.
- Realistic adult proportions (1:7.2-7.4 head-to-height).
- Coordinate convention: +Z up, facing -Y (LEFT = +X, RIGHT = -X), origin at ground (0, 0, 0).
"""
import math
import sys

import bmesh
from mathutils import Vector

from blender.lib.common import bm_to_obj, loft_rings, smoothstep, uv_cylindrical

sys.dont_write_bytecode = True


def head_profile_at(u, sa, lm):
    """Return exact smooth anatomical head half-extents (rx, ry, y_center) for height fraction u in [0, 1].

    Shared by body.py and garments.py so hair, beard, and hijab fit with exact clearance and zero poke-through.
    u = 0 at chin_z, u = 1 at crown_z; sa = sin(ang) where -1 is front (-Y), +1 is back (+Y).
    """
    hw = lm['head_w'] * 0.5
    hd = lm['head_d'] * 0.5
    # Exact keyframe table matching _add_head_neck (u, rx_mul, ry_f_mul, ry_b_mul, y_center)
    table = [
        (0.00, 0.42, 0.54, 0.44, -0.006),
        (0.08, 0.68, 0.80, 0.58, -0.010),
        (0.18, 0.82, 0.91, 0.72, -0.010),
        (0.32, 0.93, 0.97, 0.86, -0.009),
        (0.50, 1.00, 1.00, 0.99, -0.007),
        (0.68, 1.00, 0.98, 1.05, -0.004),
        (0.82, 0.91, 0.89, 0.97, -0.001),
        (0.92, 0.70, 0.70, 0.76, 0.001),
        (0.98, 0.38, 0.38, 0.41, 0.002),
        (1.00, 0.10, 0.10, 0.10, 0.002),
    ]
    u = max(0.0, min(1.0, float(u)))
    for i in range(len(table) - 1):
        u0, rx0, rf0, rb0, yc0 = table[i]
        u1, rx1, rf1, rb1, yc1 = table[i + 1]
        if u <= u1 or i == len(table) - 2:
            t = (u - u0) / max(u1 - u0, 1e-6)
            rx = (rx0 + (rx1 - rx0) * t) * hw
            rf = (rf0 + (rf1 - rf0) * t) * hd
            rb = (rb0 + (rb1 - rb0) * t) * hd
            yc = yc0 + (yc1 - yc0) * t
            t_jaw = 1.0 - smoothstep(0.04, 0.42, u)
            x_taper = 1.0 - 0.14 * t_jaw * max(0.0, -sa)
            ry = rf if sa < 0.0 else rb
            return rx * x_taper, ry, yc
    return hw * 0.1, hd * 0.1, 0.002


def _add_head_neck(bm, lm, segs=20):
    """Add a smooth sculptural faceless adult head & neck (ZERO facial features)."""
    hh = lm['head_h']
    hw = lm['head_w'] * 0.5
    hd = lm['head_d'] * 0.5
    z_nb = lm['neck_bot'].z
    z_nt = lm['neck_top'].z
    z_chin = lm['chin_z']

    neck_rx = hw * 0.63
    neck_ry = hd * 0.57

    rings = []
    # Smooth neck base up to underside of jaw
    neck_stations = [
        (z_nb - 0.025, neck_rx * 1.20, neck_ry * 1.14, neck_ry * 1.16, 0.008),
        (z_nb + 0.006, neck_rx * 1.00, neck_ry * 0.96, neck_ry * 1.00, 0.006),
        (z_nb + (z_nt - z_nb) * 0.55, neck_rx * 0.94, neck_ry * 0.92, neck_ry * 0.96, 0.004),
        (z_chin - 0.004, neck_rx * 0.92, hd * 0.52, neck_ry * 0.94, -0.003),
    ]
    for z, rx, ry_f, ry_b, yc in neck_stations:
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            ry = ry_f if sa < 0.0 else ry_b
            ring.append(bm.verts.new((ca * rx, yc + sa * ry, z)))
        rings.append(ring)

    # Smooth sculptural faceless oval head using shared exact profile
    for u in (0.00, 0.08, 0.18, 0.32, 0.50, 0.68, 0.82, 0.92, 0.98, 1.00):
        z = z_chin + hh * u
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            rx, ry, yc = head_profile_at(u, sa, lm)
            ring.append(bm.verts.new((ca * rx, yc + sa * ry, z)))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)


def _add_torso(bm, lm, female=False, segs=20):
    """Add sculpted realistic anatomical torso from pelvis floor to neck base."""
    z_hip = lm['hip_z']
    z_wst = lm['waist_z']
    z_chs = lm['chest_z']
    z_sh = lm['sh_z']
    z_nb = lm['neck_bot'].z

    sh_x = lm['sh_x']
    tw = lm['torso_w']
    ww = lm['waist_w']
    pw = lm['pelvis_w']
    cd = lm['chest_d']
    wd = lm['waist_d']
    pd = lm['pelvis_d']
    nk_r = lm['head_w'] * 0.34

    if female:
        stations = [
            (z_hip - 0.055, pw * 0.84, pd * 0.78, pd * 0.90, 0.006, 0.0),
            (z_hip - 0.015, pw * 1.02, pd * 0.94, pd * 1.08, 0.008, 0.0),
            (z_hip + (z_wst - z_hip) * 0.45, pw * 0.95, pd * 0.92, pd * 1.02, 0.004, 0.0),
            (z_wst, ww * 0.92, wd * 0.92, wd * 0.94, 0.000, 0.0),
            (z_wst + (z_chs - z_wst) * 0.48, ww * 1.02, cd * 0.96, wd * 0.98, -0.003, 0.3),
            (z_chs - 0.02, tw * 0.96, cd * 1.06, cd * 0.96, -0.004, 0.7),
            (z_chs + 0.045, tw * 1.02, cd * 0.96, cd * 0.98, 0.000, 0.4),
            (z_sh - 0.022, sh_x * 1.04, cd * 0.82, cd * 0.86, 0.005, 0.1),
            (z_sh + 0.012, sh_x * 0.92, cd * 0.64, cd * 0.70, 0.006, 0.0),
            (z_nb - 0.012, nk_r * 1.65, nk_r * 1.15, nk_r * 1.24, 0.007, 0.0),
            (z_nb + 0.014, nk_r * 1.04, nk_r * 0.95, nk_r * 1.02, 0.007, 0.0),
        ]
    else:
        stations = [
            (z_hip - 0.055, pw * 0.85, pd * 0.80, pd * 0.88, 0.005, 0.0),
            (z_hip - 0.012, pw * 1.00, pd * 0.94, pd * 1.02, 0.006, 0.0),
            (z_hip + (z_wst - z_hip) * 0.45, pw * 0.96, pd * 0.94, pd * 0.96, 0.003, 0.0),
            (z_wst, ww * 0.98, wd * 0.96, wd * 0.96, 0.001, 0.0),
            (z_wst + (z_chs - z_wst) * 0.45, ww * 1.06, cd * 0.94, cd * 0.95, -0.002, 0.3),
            (z_chs - 0.015, tw * 1.02, cd * 1.06, cd * 1.00, -0.004, 0.9),
            (z_chs + 0.055, tw * 1.08, cd * 1.02, cd * 1.02, -0.002, 0.7),
            (z_sh - 0.020, sh_x * 1.08, cd * 0.86, cd * 0.90, 0.004, 0.2),
            (z_sh + 0.016, sh_x * 0.94, cd * 0.68, cd * 0.74, 0.006, 0.0),
            (z_nb - 0.010, nk_r * 1.80, nk_r * 1.18, nk_r * 1.26, 0.007, 0.0),
            (z_nb + 0.014, nk_r * 1.06, nk_r * 0.98, nk_r * 1.04, 0.007, 0.0),
        ]

    rings = []
    for z, rx, ry_f, ry_b, yc, pec in stations:
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ca = math.cos(ang)
            sa = math.sin(ang)
            sq = 1.0 + 0.07 * (ca * ca * sa * sa)
            ry = ry_f if sa < 0.0 else ry_b
            if sa < 0.0 and pec > 0.0:
                pec_lobe = math.sin(abs(ca) * math.pi) * (-sa)
                ry *= 1.0 + 0.08 * pec * pec_lobe
            elif sa > 0.0 and pec > 0.0:
                ry *= 1.0 - 0.045 * pec * (sa ** 4)
            ring.append(bm.verts.new((ca * rx * sq, yc + sa * ry * sq, z)))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)


def _sweep_limb(bm, centers, radii, segs=12, ref_fwd=Vector((0.0, -1.0, 0.0)), cap_start=True, cap_end=True):
    """Sweep an elliptical limb mesh smoothly along 3D joint centers."""
    n = len(centers)
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
            p = c + fx * (math.cos(ang) * rx) + fy * (math.sin(ang) * ry)
            ring.append(bm.verts.new(p))
        rings.append(ring)

    loft_rings(bm, rings, closed_u=True, cap_start=cap_start, cap_end=cap_end)
    return rings


def _add_arm_and_hand(bm, lm, side, female=False, segs=12):
    """Add sculpted anatomical arm with smooth rounded deltoid cap & articulated-silhouette hand."""
    s = 1.0 if side == 'l' else -1.0
    sh = lm[f'sh_{side}']
    elb = lm[f'elb_{side}']
    wri = lm[f'wri_{side}']
    htip = lm[f'hand_{side}']
    sc = lm['height'] / 1.76 * (0.86 if female else 1.0)

    u_dir = elb - sh
    l_dir = wri - elb
    h_dir = htip - wri
    u_unit = u_dir.normalized()

    # Smooth rounded deltoid dome along the downward arm axis (zero upward shoulder-pad wedge!)
    sh_c = sh + Vector((-s * 0.012, 0.002, -0.004))
    centers = [
        sh_c - u_unit * (0.044 * sc) + Vector((-s * 0.014, 0.0, 0.0)),   # dome apex seated flush on trapezius
        sh_c - u_unit * (0.024 * sc) + Vector((-s * 0.006, 0.0, 0.0)),   # upper rounded deltoid
        sh_c,                                                             # full deltoid belly
        sh + u_dir * 0.18,                                                # lower deltoid
        sh + u_dir * 0.44,                                                # mid bicep/tricep
        sh + u_dir * 0.74,                                                # lower upperarm
        elb,                                                              # elbow
        elb + l_dir * 0.24,                                               # upper forearm fullness
        elb + l_dir * 0.58,                                               # mid forearm
        elb + l_dir * 0.86,                                               # lower forearm
        wri,                                                              # wrist
    ]
    radii = [
        (0.014 * sc, 0.014 * sc),
        (0.042 * sc, 0.040 * sc),
        (0.052 * sc, 0.050 * sc),
        (0.048 * sc, 0.047 * sc),
        (0.043 * sc, 0.045 * sc),
        (0.039 * sc, 0.040 * sc),
        (0.037 * sc, 0.036 * sc),
        (0.040 * sc, 0.041 * sc),
        (0.033 * sc, 0.034 * sc),
        (0.027 * sc, 0.024 * sc),
        (0.025 * sc, 0.020 * sc),
    ]
    _sweep_limb(bm, centers, radii, segs=segs, cap_start=True, cap_end=False)

    # Sculpted anatomical hand: flattened palm + curved 4-finger silhouette + distinct thumb
    ax_d = h_dir.normalized()
    inward = Vector((-s, -0.18, 0.0)).normalized()
    inward = (inward - ax_d * inward.dot(ax_d)).normalized()
    fwd = ax_d.cross(inward).normalized()
    if fwd.y > 0.0:
        fwd = -fwd
    inward = fwd.cross(ax_d).normalized()
    if inward.x * (-s) < 0.0:
        inward = -inward

    hl = h_dir.length
    h_prof = [
        (0.00, 0.019 * sc, 0.027 * sc, 0.000),
        (0.18, 0.017 * sc, 0.037 * sc, 0.002),
        (0.44, 0.015 * sc, 0.040 * sc, 0.004),
        (0.66, 0.012 * sc, 0.035 * sc, 0.010),
        (0.86, 0.009 * sc, 0.026 * sc, 0.018),
        (1.00, 0.005 * sc, 0.014 * sc, 0.022),
    ]
    h_segs = 10
    h_rings = []
    for t, r_in, r_fw, curl in h_prof:
        c = wri + ax_d * (t * hl) + inward * curl
        ring = []
        for k in range(h_segs):
            ang = (k / h_segs) * math.tau
            p = c + inward * (math.cos(ang) * r_in) + fwd * (math.sin(ang) * r_fw)
            ring.append(bm.verts.new(p))
        h_rings.append(ring)
    loft_rings(bm, h_rings, closed_u=True, cap_start=True, cap_end=True)

    # Distinct anatomical thumb emerging on front-inner side
    th_base = wri + ax_d * (0.16 * hl) + fwd * (0.023 * sc) + inward * (0.008 * sc)
    th_dir = (ax_d * 0.72 + fwd * 0.56 + inward * 0.40).normalized()
    th_len = hl * 0.42
    th_pts = [
        th_base,
        th_base + th_dir * (th_len * 0.45),
        th_base + th_dir * (th_len * 0.85) + inward * (0.006 * sc),
        th_base + th_dir * th_len + inward * (0.010 * sc),
    ]
    th_rads = [
        (0.013 * sc, 0.014 * sc),
        (0.011 * sc, 0.011 * sc),
        (0.009 * sc, 0.009 * sc),
        (0.006 * sc, 0.006 * sc),
    ]
    _sweep_limb(bm, th_pts, th_rads, segs=8, cap_start=True, cap_end=True)


def _add_leg_and_foot(bm, lm, side, female=False, segs=12):
    """Add sculpted anatomical leg (thigh -> knee -> calf -> ankle) and realistic bare foot."""
    s = 1.0 if side == 'l' else -1.0
    hip = lm[f'hip_{side}']
    knee = lm[f'knee_{side}']
    ank = lm[f'ankle_{side}']
    sc = lm['height'] / 1.76 * (0.92 if female else 1.0)

    t_dir = knee - hip
    c_dir = ank - knee

    centers = [
        hip + Vector((-s * 0.005, 0.004, 0.032)),
        hip + t_dir * 0.14,
        hip + t_dir * 0.42,
        hip + t_dir * 0.74,
        knee + Vector((0.0, -0.004, 0.0)),
        knee + c_dir * 0.24 + Vector((0.0, 0.008, 0.0)),
        knee + c_dir * 0.54 + Vector((0.0, 0.004, 0.0)),
        knee + c_dir * 0.82,
        ank + Vector((0.0, 0.0, -0.008)),
    ]
    radii = [
        (0.072 * sc, 0.074 * sc),
        (0.069 * sc, 0.072 * sc),
        (0.060 * sc, 0.063 * sc),
        (0.050 * sc, 0.052 * sc),
        (0.046 * sc, 0.047 * sc),
        (0.049 * sc, 0.052 * sc),
        (0.041 * sc, 0.044 * sc),
        (0.033 * sc, 0.035 * sc),
        (0.031 * sc, 0.034 * sc),
    ]
    _sweep_limb(bm, centers, radii, segs=segs, cap_start=True, cap_end=True)

    # Realistic bare foot resting cleanly on z = 0.011 m (ready for 1.1 cm sandal footbed)
    fl = lm['foot_len']
    fw = fl * 0.185
    fx = ank.x
    y_heel = ank.y + lm['foot_y_heel']
    y_toe = ank.y - fl * 0.76
    z_sole = 0.011

    f_stations = [
        (y_heel + 0.006, fw * 0.55, z_sole + 0.036, 0.0),
        (y_heel - fl * 0.08, fw * 0.74, ank.z + 0.004, 0.0),
        (ank.y, fw * 0.78, ank.z + 0.002, 0.0),
        (ank.y - fl * 0.22, fw * 0.84, z_sole + 0.052, -s * 0.002),
        (ank.y - fl * 0.45, fw * 0.98, z_sole + 0.034, -s * 0.003),
        (ank.y - fl * 0.64, fw * 0.92, z_sole + 0.024, -s * 0.004),
        (y_toe, fw * 0.56, z_sole + 0.015, -s * 0.006),
    ]

    f_segs = 10
    f_rings = []
    for y, hw_f, z_top, x_off in f_stations:
        z_mid = (z_sole + z_top) * 0.5
        hz = max(0.004, (z_top - z_sole) * 0.5)
        ring = []
        for k in range(f_segs):
            ang = (k / f_segs) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            if sa < 0.0:
                z = z_sole + hz * (1.0 + sa * 0.96) * 0.18
            else:
                z = z_mid + sa * hz
            x = fx + x_off + ca * hw_f
            ring.append(bm.verts.new((x, y, z)))
        f_rings.append(ring)

    loft_rings(bm, f_rings, closed_u=True, cap_start=True, cap_end=True)


def build_body_skin(name, col, lm, mat_skin, female=False, include_legs=True, include_torso=True):
    """Build complete smooth faceless anatomical `body_skin` mesh object."""
    bm = bmesh.new()
    _add_head_neck(bm, lm, segs=20)
    if include_torso:
        _add_torso(bm, lm, female=female, segs=20)
    for side in ('l', 'r'):
        _add_arm_and_hand(bm, lm, side, female=female, segs=12)
        if include_legs:
            _add_leg_and_foot(bm, lm, side, female=female, segs=12)

    obj = bm_to_obj(bm, name, col, mat=mat_skin, smooth=True)
    uv_cylindrical(obj, scale_u=2.0, scale_v=1.5)
    return obj
