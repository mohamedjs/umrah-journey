"""Low-poly realistic static crowd archetypes builder for Three.js InstancedMesh rendering.

Exports ALL 6 crowd archetypes into a single `public/models/characters/crowd.glb`
(<= 4,500 tris total, <= 180 KB Draco GLB):
1. crowd_ihram_idtiba_cloth  + crowd_ihram_idtiba_skin   (RIGHT shoulder -X bare, LEFT +X covered!)
2. crowd_ihram_covered_cloth + crowd_ihram_covered_skin  (both shoulders covered)
3. crowd_man_street_cloth    + crowd_man_street_skin     (shirt + trousers)
4. crowd_woman_abaya_cloth   + crowd_woman_abaya_hijab + crowd_woman_abaya_skin
5. crowd_seated_man_cloth    + crowd_seated_man_skin     (seated airline passenger, hips z=0.58 m)
6. crowd_seated_woman_cloth  + crowd_seated_woman_hijab + crowd_seated_woman_skin

Contract:
- Every mesh has origin at (0, 0, 0) on the floor between feet, facing -Y in Blender (+Z in Three.js).
- Smooth faceless anatomical heads (ZERO facial features).
- Neutral white Base Color (1, 1, 1) on every tintable cloth/skin/hijab material so
  Three.js InstancedMesh.setColorAt() multiplies accurately.
"""
import math
import sys

import bmesh
from mathutils import Vector

from blender.lib.common import (
    MODELS_CHAR,
    bm_to_obj,
    ensure_dirs,
    export_glb,
    loft_rings,
    make_collection,
    make_pbr_material,
    reset_scene,
    smoothstep,
    tri_count,
    uv_cylindrical,
)

sys.dont_write_bytecode = True

EXPECTED_CROWD_MESHES = [
    'crowd_ihram_idtiba_cloth',
    'crowd_ihram_idtiba_skin',
    'crowd_ihram_covered_cloth',
    'crowd_ihram_covered_skin',
    'crowd_man_street_cloth',
    'crowd_man_street_skin',
    'crowd_woman_abaya_cloth',
    'crowd_woman_abaya_hijab',
    'crowd_woman_abaya_skin',
    'crowd_seated_man_cloth',
    'crowd_seated_man_skin',
    'crowd_seated_woman_cloth',
    'crowd_seated_woman_hijab',
    'crowd_seated_woman_skin',
]


def _sweep(bm, pts, rads, segs=8, ref_fwd=Vector((0.0, -1.0, 0.0)), cap_s=True, cap_e=True):
    n = len(pts)
    tangents = []
    for i in range(n):
        t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        tangents.append(t.normalized() if t.length > 1e-6 else Vector((0.0, 0.0, -1.0)))
    rings = []
    for i, (c, (rx, ry)) in enumerate(zip(pts, rads)):
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
    loft_rings(bm, rings, closed_u=True, cap_start=cap_s, cap_end=cap_e)


def _add_lowpoly_head(bm, center_z, hh=0.236, y_off=-0.008, include_neck=True, segs=10):
    """Low-poly smooth faceless anatomical adult oval head (ZERO facial features)."""
    hw = hh * 0.32
    hd = hh * 0.38
    z_chin = center_z - hh * 0.50
    stations = []
    if include_neck:
        stations.extend([
            (z_chin - hh * 0.36, hw * 0.66, hd * 0.58, y_off + 0.012),
            (z_chin - hh * 0.08, hw * 0.58, hd * 0.52, y_off + 0.008),
        ])
    stations.extend([
        (z_chin, hw * 0.42, hd * 0.50, y_off - 0.002),
        (z_chin + hh * 0.22, hw * 0.88, hd * 0.92, y_off - 0.004),
        (z_chin + hh * 0.52, hw * 1.00, hd * 1.00, y_off - 0.002),
        (z_chin + hh * 0.78, hw * 0.92, hd * 0.95, y_off + 0.002),
        (z_chin + hh * 0.95, hw * 0.52, hd * 0.54, y_off + 0.003),
        (z_chin + hh * 1.02, hw * 0.14, hd * 0.14, y_off + 0.003),
    ])
    rings = [
        [bm.verts.new((math.cos(k / segs * math.tau) * rx, yc + math.sin(k / segs * math.tau) * ry, z)) for k in range(segs)]
        for z, rx, ry, yc in stations
    ]
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)


def _add_lowpoly_foot(bm, x, y_ank, z_sole=0.004, length=0.24, hw=0.044, h=0.056):
    pts = [
        (y_ank + length * 0.24, hw * 0.68, h * 0.78),
        (y_ank, hw * 0.85, h),
        (y_ank - length * 0.42, hw * 1.00, h * 0.66),
        (y_ank - length * 0.76, hw * 0.56, h * 0.34),
    ]
    rings = []
    for y, rx, hz in pts:
        ring = []
        for k in range(6):
            ang = (k / 6) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            z = z_sole if sa < 0.0 else z_sole + sa * hz
            ring.append(bm.verts.new((x + ca * rx, y, z)))
        rings.append(ring)
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)


def _add_standing_man_skin(bm, h=1.74, bare_right_shoulder=False, bare_shins=True):
    """Add smooth faceless head, natural arms (with optional bare right shoulder -X), and optional bare shins/feet."""
    hh = h / 7.3
    sh_z = h * 0.812
    sh_x = h * 0.112

    _add_lowpoly_head(bm, center_z=h - hh * 0.50, hh=hh, include_neck=True, segs=10)

    if bare_right_shoulder:
        # Smooth anatomical upper torso & right shoulder slope
        t_levels = [
            (h * 0.68, sh_x * 0.92, 0.110),
            (h * 0.76, sh_x * 1.00, 0.114),
            (sh_z + 0.008, sh_x * 0.96, 0.092),
            (h * 0.848, hh * 0.28, 0.064),
        ]
        rings = [
            [bm.verts.new((math.cos(k / 10 * math.tau) * rx, math.sin(k / 10 * math.tau) * ry, z)) for k in range(10)]
            for z, rx, ry in t_levels
        ]
        loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)

    for side, s in (('l', 1.0), ('r', -1.0)):
        sh = Vector((s * sh_x, 0.004, sh_z))
        elb = Vector((s * (sh_x + 0.052), 0.014, sh_z - 0.30))
        wri = Vector((s * (sh_x + 0.068), -0.025, sh_z - 0.55))
        tip = Vector((s * (sh_x + 0.060), -0.048, sh_z - 0.72))
        if bare_right_shoulder and side == 'r':
            # Smooth downward deltoid cap (no upward fin!)
            u_dir = (elb - sh).normalized()
            pts = [sh - u_dir * 0.032 + Vector((0.012, 0, 0)), sh, elb, wri, tip]
            rads = [(0.024, 0.024), (0.052, 0.050), (0.037, 0.036), (0.026, 0.022), (0.015, 0.026)]
            _sweep(bm, pts, rads, segs=7)
        else:
            start_pt = sh.lerp(elb, 0.38)
            pts = [start_pt, elb, wri, tip]
            rads = [(0.042, 0.042), (0.036, 0.036), (0.026, 0.022), (0.015, 0.026)]
            _sweep(bm, pts, rads, segs=7)

    if bare_shins:
        for s in (1.0, -1.0):
            x = s * h * 0.058
            pts = [
                Vector((x, 0.0, h * 0.24)),
                Vector((x, 0.004, h * 0.13)),
                Vector((x, 0.006, 0.022)),
            ]
            rads = [(0.044, 0.046), (0.035, 0.037), (0.030, 0.033)]
            _sweep(bm, pts, rads, segs=7)
            _add_lowpoly_foot(bm, x, 0.006, z_sole=0.002, length=h * 0.145, hw=0.044, h=0.052)


def _add_ihram_cloth(bm, h=1.74, idtiba=False):
    """Add low-poly authentic ihram izar + smoothly draped rida (rounded shoulders, zero boxy flare!)."""
    sh_z = h * 0.812
    sh_x = h * 0.114
    wst_z = h * 0.615
    chs_z = h * 0.745
    hem_z = h * 0.145
    nb_z = h * 0.848

    # 1. Draped izar lower wrap
    iz_levels = [
        (wst_z + 0.025, sh_x * 0.88, 0.116),
        (h * 0.515, sh_x * 1.02, 0.130),
        (h * 0.34, sh_x * 1.08, 0.138),
        (hem_z, sh_x * 1.15, 0.146),
    ]
    rings = []
    segs = 14
    for i, (z, rx, ry) in enumerate(iz_levels):
        fold_a = 0.005 * i
        rings.append([
            bm.verts.new((math.cos(k / segs * math.tau) * (rx + math.sin(k / segs * math.tau * 5.0) * fold_a),
                          0.004 + math.sin(k / segs * math.tau) * (ry + math.sin(k / segs * math.tau * 5.0) * fold_a), z))
            for k in range(segs)
        ])
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)

    # 2. Upper rida shawl with natural rounded trapezius-to-shoulder slope!
    r_rings = []
    n_r = 7
    z_bot = wst_z - 0.025
    for i in range(n_r):
        u = i / (n_r - 1)  # 0 = top neck/diagonal edge -> 1 = waist hem
        ring = []
        for k in range(segs):
            ang = (k / segs) * math.tau
            ca = math.cos(ang)  # +1 = LEFT (+X), -1 = RIGHT (-X)
            sa = math.sin(ang)
            if idtiba:
                u_left = 0.5 + 0.5 * ca
                z_top = (chs_z - 0.055) + (nb_z + 0.002 - (chs_z - 0.055)) * smoothstep(0.08, 0.88, u_left)
                z = z_top * (1.0 - u) + (z_bot + 0.015 * (1.0 - u_left)) * u
                # Smoothly taper inward near neck (u=0) and curve cleanly around LEFT deltoid (+X)
                neck_taper = 0.52 + 0.48 * smoothstep(0.0, 0.24, u)
                left_cap = 0.044 * smoothstep(0.08, 0.30, u) * (1.0 - smoothstep(0.45, 0.85, u)) * (max(0.0, ca) ** 1.3)
                rx = sh_x * (0.94 + 0.08 * (1.0 - u)) * (neck_taper if ca > 0.0 else 1.0) + left_cap
                ry = 0.128 * (0.72 + 0.28 * smoothstep(0.0, 0.22, u))
            else:
                z_top = nb_z - 0.018 * max(0.0, -sa)
                z = z_top * (1.0 - u) + z_bot * u
                # Rounded shoulder yoke: narrow at neck (u=0), curving over shoulders (u=0.22), hugging torso below
                neck_taper = 0.48 + 0.52 * smoothstep(0.0, 0.24, u)
                sh_cap = 0.044 * smoothstep(0.10, 0.30, u) * (1.0 - smoothstep(0.45, 0.85, u)) * (abs(ca) ** 1.3)
                rx = sh_x * (0.95 + 0.08 * (1.0 - u)) * neck_taper + sh_cap
                ry = 0.130 * (0.68 + 0.32 * smoothstep(0.0, 0.24, u))
            fold = math.sin(ang * 4.0 + u * 2.5) * 0.005 * smoothstep(0.1, 0.4, u)
            ring.append(bm.verts.new((ca * (rx + fold), 0.003 + sa * (ry + fold), z)))
        r_rings.append(ring)
    loft_rings(bm, r_rings, closed_u=True, cap_start=True, cap_end=True)


def _add_street_man_cloth(bm, h=1.74):
    """Add low-poly tailored shirt + trousers + shoes with smooth shoulders and clean ankles."""
    sh_z = h * 0.812
    sh_x = h * 0.112
    wst_z = h * 0.615
    hip_z = h * 0.515

    t_levels = [
        (hip_z - 0.05, sh_x * 0.90, 0.116),
        (wst_z, sh_x * 0.84, 0.108),
        (h * 0.74, sh_x * 0.98, 0.124),
        (sh_z + 0.006, sh_x * 1.02, 0.100),
        (h * 0.850, h * 0.046, 0.062),
    ]
    rings = [
        [bm.verts.new((math.cos(k / 12 * math.tau) * rx, math.sin(k / 12 * math.tau) * ry, z)) for k in range(12)]
        for z, rx, ry in t_levels
    ]
    loft_rings(bm, rings, closed_u=True, cap_start=True, cap_end=True)

    # Smooth downward short sleeves (no boxy corners!)
    for s in (1.0, -1.0):
        sh = Vector((s * (sh_x - 0.010), 0.004, sh_z - 0.012))
        elb = Vector((s * (sh_x + 0.052), 0.014, sh_z - 0.30))
        u_dir = (elb - sh).normalized()
        pts = [sh - u_dir * 0.024 + Vector((-s * 0.016, 0, 0)), sh, sh.lerp(elb, 0.46)]
        rads = [(0.020, 0.020), (0.052, 0.050), (0.046, 0.046)]
        _sweep(bm, pts, rads, segs=7)

    # Trouser legs extending cleanly down into shoes (zero ankle gap!)
    for s in (1.0, -1.0):
        x = s * h * 0.058
        pts = [
            Vector((x, 0.0, hip_z + 0.01)),
            Vector((x, -0.005, h * 0.285)),
            Vector((x, 0.005, 0.032)),
        ]
        rads = [(0.084, 0.088), (0.066, 0.068), (0.052, 0.054)]
        _sweep(bm, pts, rads, segs=7)
        _add_lowpoly_foot(bm, x, 0.005, z_sole=0.000, length=h * 0.150, hw=0.048, h=0.062)


def _add_standing_woman_abaya(bm_cloth, bm_hijab, bm_skin, h=1.64):
    """Add low-poly modest flowing abaya + clean draped hijab + smooth faceless head & hands."""
    hh = h / 7.25
    sh_z = h * 0.808
    sh_x = h * 0.100

    _add_lowpoly_head(bm_skin, center_z=h - hh * 0.50, hh=hh, include_neck=False, segs=10)
    for s in (1.0, -1.0):
        wri = Vector((s * (sh_x + 0.070), -0.032, sh_z - 0.50))
        tip = Vector((s * (sh_x + 0.060), -0.055, sh_z - 0.66))
        _sweep(bm_skin, [wri, tip], [(0.024, 0.020), (0.014, 0.026)], segs=6)

    ab_levels = [
        (0.015, sh_x * 1.65, 0.205),
        (h * 0.26, sh_x * 1.44, 0.175),
        (h * 0.50, sh_x * 1.24, 0.148),
        (h * 0.64, sh_x * 1.06, 0.126),
        (h * 0.76, sh_x * 1.04, 0.118),
        (sh_z + 0.006, sh_x * 1.00, 0.096),
        (h * 0.848, hh * 0.30, 0.068),
    ]
    segs = 14
    rings = []
    for i, (z, rx, ry) in enumerate(ab_levels):
        pleat = 0.009 * (1.0 - i / len(ab_levels))
        rings.append([
            bm_cloth.verts.new((math.cos(k / segs * math.tau) * (rx + math.sin(k / segs * math.tau * 6.0) * pleat),
                                0.004 + math.sin(k / segs * math.tau) * (ry + math.sin(k / segs * math.tau * 6.0) * pleat), z))
            for k in range(segs)
        ])
    loft_rings(bm_cloth, rings, closed_u=True, cap_start=True, cap_end=True)

    # Smooth sleeves
    for s in (1.0, -1.0):
        sh = Vector((s * sh_x, 0.004, sh_z))
        elb = Vector((s * (sh_x + 0.052), 0.010, sh_z - 0.27))
        wri = Vector((s * (sh_x + 0.068), -0.030, sh_z - 0.49))
        u_dir = (elb - sh).normalized()
        _sweep(
            bm_cloth,
            [sh - u_dir * 0.024 + Vector((-s * 0.012, 0, 0)), sh, elb, wri],
            [(0.022, 0.022), (0.054, 0.054), (0.048, 0.048), (0.042, 0.042)],
            segs=7,
        )

    # Draped hijab cleanly outside abaya collar (zero Z-fighting on upper chest!)
    hw = hh * 0.33
    hd = hh * 0.39
    z_chin = h - hh
    hj_levels = [
        (sh_z - 0.065, sh_x * 1.18, 0.146, 0.004, False),
        (h * 0.845, hw * 1.24, hd * 1.14, 0.004, False),
        (z_chin + hh * 0.04, hw * 1.14, hd * 1.06, 0.002, True),
        (z_chin + hh * 0.44, hw * 1.18, hd * 1.16, 0.008, True),
        (z_chin + hh * 0.80, hw * 1.12, hd * 1.16, 0.008, False),
        (h + 0.024, hw * 0.30, hd * 0.32, 0.005, False),
    ]
    h_rings = []
    for idx, (z, rx, ry, yc, frame) in enumerate(hj_levels):
        ring = []
        for k in range(12):
            ang = (k / 12) * math.tau
            ca, sa = math.cos(ang), math.sin(ang)
            r_y = ry
            if frame and sa < -0.15:
                front = (-sa - 0.15) / 0.85
                r_y *= (1.0 - 0.56 * front)
            ring.append(bm_hijab.verts.new((ca * rx, yc + sa * r_y, z)))
        h_rings.append(ring)
    loft_rings(bm_hijab, h_rings, closed_u=True, cap_start=True, cap_end=True)


def _add_seated_passenger(bm_cloth, bm_skin, bm_hijab=None, female=False):
    """Build genuinely seated airline passenger: hips at z=0.58 m, knees bent 90 deg, feet at z=0.02 m, hands on lap."""
    h = 1.64 if female else 1.74
    hh = h / (7.25 if female else 7.3)
    hip_z = 0.58
    sh_z = hip_z + (0.50 if female else 0.54)
    sh_x = 0.165 if female else 0.192
    head_cz = sh_z + 0.09 + hh * 0.52

    y_hip = 0.02
    y_sh = 0.075
    y_hd = 0.085

    _add_lowpoly_head(bm_skin, center_z=head_cz, hh=hh, y_off=y_hd - 0.008, include_neck=not female, segs=10)

    t_levels = [
        (hip_z - 0.04, y_hip, sh_x * 0.98, 0.124),
        (hip_z + 0.14, y_hip + 0.02, sh_x * 0.88, 0.110),
        (hip_z + 0.36, y_sh - 0.015, sh_x * 0.98, 0.118),
        (sh_z + 0.004, y_sh, sh_x * 0.96, 0.096),
        (sh_z + 0.068, y_sh + 0.005, hh * 0.32, 0.066),
    ]
    rings = [
        [bm_cloth.verts.new((math.cos(k / 12 * math.tau) * rx, yc + math.sin(k / 12 * math.tau) * ry, z)) for k in range(12)]
        for z, yc, rx, ry in t_levels
    ]
    loft_rings(bm_cloth, rings, closed_u=True, cap_start=True, cap_end=True)

    if female:
        lap_pts = [
            Vector((0.0, y_hip - 0.02, hip_z + 0.02)),
            Vector((0.0, -0.20, hip_z - 0.01)),
            Vector((0.0, -0.39, hip_z - 0.04)),
            Vector((0.0, -0.41, 0.30)),
            Vector((0.0, -0.41, 0.05)),
        ]
        lap_rads = [
            (sh_x * 1.06, 0.115),
            (sh_x * 1.12, 0.105),
            (sh_x * 1.10, 0.105),
            (sh_x * 1.16, 0.112),
            (sh_x * 1.24, 0.120),
        ]
        _sweep(bm_cloth, lap_pts, lap_rads, segs=12, ref_fwd=Vector((0.0, 0.0, 1.0)))
        for s in (1.0, -1.0):
            _add_lowpoly_foot(bm_cloth, s * 0.095, -0.42, z_sole=0.018, length=0.22, hw=0.042, h=0.048)
    else:
        for s in (1.0, -1.0):
            x = s * 0.105
            _sweep(
                bm_cloth,
                [Vector((x, y_hip, hip_z)), Vector((x, -0.20, hip_z - 0.015)), Vector((x, -0.39, hip_z - 0.04))],
                [(0.086, 0.086), (0.076, 0.078), (0.068, 0.068)],
                segs=7,
                ref_fwd=Vector((0.0, 0.0, 1.0)),
            )
            _sweep(
                bm_cloth,
                [Vector((x, -0.39, hip_z - 0.04)), Vector((x, -0.41, 0.30)), Vector((x, -0.41, 0.05))],
                [(0.066, 0.066), (0.060, 0.060), (0.050, 0.052)],
                segs=7,
            )
            _add_lowpoly_foot(bm_cloth, x, -0.41, z_sole=0.018, length=0.24, hw=0.046, h=0.058)

    for s in (1.0, -1.0):
        sh = Vector((s * sh_x, y_sh, sh_z))
        elb = Vector((s * (sh_x + 0.032), y_sh - 0.06, hip_z + 0.20))
        wri = Vector((s * 0.105, -0.24, hip_z + 0.115))
        hand = Vector((s * 0.075, -0.33, hip_z + 0.095))
        u_dir = (elb - sh).normalized()
        if female:
            _sweep(bm_cloth, [sh - u_dir * 0.022 + Vector((-s * 0.012, 0, 0)), sh, elb, wri], [(0.022, 0.022), (0.050, 0.050), (0.046, 0.046), (0.038, 0.038)], segs=7)
            _sweep(bm_skin, [wri, hand], [(0.022, 0.018), (0.015, 0.024)], segs=6)
        else:
            _sweep(bm_cloth, [sh - u_dir * 0.022 + Vector((-s * 0.012, 0, 0)), sh, elb], [(0.024, 0.024), (0.054, 0.052), (0.045, 0.045)], segs=7)
            _sweep(bm_skin, [elb, wri, hand], [(0.039, 0.039), (0.028, 0.024), (0.018, 0.028)], segs=7)

    if female and bm_hijab is not None:
        hw = hh * 0.33
        hd = hh * 0.39
        z_chin = head_cz - hh * 0.50
        hj_levels = [
            (sh_z - 0.055, sh_x * 1.16, 0.144, y_sh, False),
            (sh_z + 0.065, hw * 1.24, hd * 1.14, y_hd, False),
            (z_chin + hh * 0.04, hw * 1.14, hd * 1.06, y_hd, True),
            (z_chin + hh * 0.44, hw * 1.18, hd * 1.16, y_hd + 0.008, True),
            (z_chin + hh * 0.80, hw * 1.10, hd * 1.14, y_hd + 0.008, False),
            (z_chin + hh * 1.06, hw * 0.22, hd * 0.24, y_hd + 0.005, False),
        ]
        h_rings = []
        for idx, (z, rx, ry, yc, frame) in enumerate(hj_levels):
            ring = []
            for k in range(12):
                ang = (k / 12) * math.tau
                ca, sa = math.cos(ang), math.sin(ang)
                r_y = ry
                if frame and sa < -0.15:
                    front = (-sa - 0.15) / 0.85
                    r_y *= (1.0 - 0.56 * front)
                ring.append(bm_hijab.verts.new((ca * rx, yc + sa * r_y, z)))
            h_rings.append(ring)
        loft_rings(bm_hijab, h_rings, closed_u=True, cap_start=True, cap_end=True)


def build_crowd_archetypes(col=None):
    """Build all 6 static crowd archetypes at origin (0, 0, 0) with neutral white tintable PBR materials."""
    if col is None:
        col = make_collection('Crowd')

    mat_ihram = make_pbr_material('crowd_ihram', color='#ffffff', roughness=0.88, double_sided=True)
    mat_cloth = make_pbr_material('crowd_cloth', color='#ffffff', roughness=0.84, double_sided=True)
    mat_hijab = make_pbr_material('crowd_hijab', color='#ffffff', roughness=0.82, double_sided=True)
    mat_skin = make_pbr_material('crowd_skin', color='#ffffff', roughness=0.60)

    objs = {}

    def finish(bm, name, mat):
        o = bm_to_obj(bm, name, col, mat=mat, smooth=True)
        uv_cylindrical(o, scale_u=2.0, scale_v=1.5)
        objs[name] = o
        return o

    bm_c, bm_s = bmesh.new(), bmesh.new()
    _add_ihram_cloth(bm_c, h=1.74, idtiba=True)
    _add_standing_man_skin(bm_s, h=1.74, bare_right_shoulder=True, bare_shins=True)
    finish(bm_c, 'crowd_ihram_idtiba_cloth', mat_ihram)
    finish(bm_s, 'crowd_ihram_idtiba_skin', mat_skin)

    bm_c, bm_s = bmesh.new(), bmesh.new()
    _add_ihram_cloth(bm_c, h=1.74, idtiba=False)
    _add_standing_man_skin(bm_s, h=1.74, bare_right_shoulder=False, bare_shins=True)
    finish(bm_c, 'crowd_ihram_covered_cloth', mat_ihram)
    finish(bm_s, 'crowd_ihram_covered_skin', mat_skin)

    bm_c, bm_s = bmesh.new(), bmesh.new()
    _add_street_man_cloth(bm_c, h=1.74)
    _add_standing_man_skin(bm_s, h=1.74, bare_right_shoulder=False, bare_shins=False)
    finish(bm_c, 'crowd_man_street_cloth', mat_cloth)
    finish(bm_s, 'crowd_man_street_skin', mat_skin)

    bm_c, bm_h, bm_s = bmesh.new(), bmesh.new(), bmesh.new()
    _add_standing_woman_abaya(bm_c, bm_h, bm_s, h=1.64)
    finish(bm_c, 'crowd_woman_abaya_cloth', mat_cloth)
    finish(bm_h, 'crowd_woman_abaya_hijab', mat_hijab)
    finish(bm_s, 'crowd_woman_abaya_skin', mat_skin)

    bm_c, bm_s = bmesh.new(), bmesh.new()
    _add_seated_passenger(bm_c, bm_s, bm_hijab=None, female=False)
    finish(bm_c, 'crowd_seated_man_cloth', mat_cloth)
    finish(bm_s, 'crowd_seated_man_skin', mat_skin)

    bm_c, bm_h, bm_s = bmesh.new(), bmesh.new(), bmesh.new()
    _add_seated_passenger(bm_c, bm_s, bm_hijab=bm_h, female=True)
    finish(bm_c, 'crowd_seated_woman_cloth', mat_cloth)
    finish(bm_h, 'crowd_seated_woman_hijab', mat_hijab)
    finish(bm_s, 'crowd_seated_woman_skin', mat_skin)

    return objs


def export_crowd():
    """Reset scene, build all 6 crowd archetypes, export `crowd.glb`, and return metrics."""
    ensure_dirs()
    reset_scene()
    objs = build_crowd_archetypes()
    out_path = MODELS_CHAR / 'crowd.glb'
    size_bytes = export_glb(list(objs.values()), out_path, animations=False, draco_level=6, image_format='WEBP', image_quality=82)
    tris_by_mesh = {name: tri_count(o) for name, o in objs.items()}
    total_tris = sum(tris_by_mesh.values())
    return {
        'key': 'crowd',
        'path': str(out_path),
        'bones': 0,
        'tris': total_tris,
        'tris_by_mesh': tris_by_mesh,
        'size_bytes': size_bytes,
        'size_kb': round(size_bytes / 1024.0, 2),
        'clips': [],
        'expected_meshes': list(EXPECTED_CROWD_MESHES),
        'max_tris': 4500,
        'max_kb': 180,
    }
