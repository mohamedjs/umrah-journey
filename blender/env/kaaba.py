"""Hero Kaaba & Hijr Ismail (Al-Hatim) PBR environment for umrah-journey.

Generates `public/models/env/kaaba.glb` (containing `kaaba_LOD0` and `kaaba_LOD1`,
pre-rotated +45 deg around Blender +Z / Three.js +Y to match `src/game/mataf.js`)
and renders a 2-angle hero preview to `blender/previews/env_kaaba.png`.

Landmark world contract (Three.js Y-up, +x = East, -z = North):
- Footprint: 2*H = 11.6 m (H = 5.8), height KAABA_H = 13.0 m above 0.4 m Shadharwan
- Black Stone (Al-Hajar al-Aswad): local (+H, 1.5, +H) -> world (+8.202, 1.5, 0.0)
- Bab al-Kaaba (Gold Door): NE face local (+H, 4.0, H-2.6) -> facing Maqam Ibrahim
- Hijr Ismail (Al-Hatim): NW face local z = -H outward, a=5.0, b=8.0, t=0.9, h=1.32 m
  -> inner apex world (-9.758, 1.32, -9.758)
- Al-Rukn al-Yamani: local (-H, 1.2, +H) -> world (0.0, 1.2, +8.202)
- Mizab al-Rahmah: NW roof parapet local (0, 12.8, -H) projecting 1.1 m over Hijr
"""
import math
import os
from pathlib import Path
import struct
import sys
import tempfile

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
import numpy as np

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blender.lib import common, preview, textures  # noqa: E402

# ------------------------------------------------------------------ exact mataf.js constants
H = 5.8
R = H * math.sqrt(2.0)  # ~8.20243866 m
KAABA_H = 13.0
SHAD_H = 0.40
HIJR_A = 5.0
HIJR_B = 8.0
HIJR_T = 0.9
HIJR_H = 1.32
KAABA_ROT_Z = math.pi / 4.0  # +45 deg around Blender +Z == Three.js +Y


def _local_three_to_world_three(lx, ly, lz):
    """Apply Kaaba's +45 deg rotation around Blender +Z and return Three.js world Vector."""
    v_bl_local = common.three_to_bl(lx, ly, lz)
    v_bl_world = Matrix.Rotation(KAABA_ROT_Z, 4, 'Z') @ v_bl_local
    return common.bl_to_three(v_bl_world.x, v_bl_world.y, v_bl_world.z)


def _assert_landmark_orientation():
    """Assert every sacred landmark maps to exact `src/game/mataf.js` world coordinates."""
    bs = _local_three_to_world_three(H, 1.5, H)
    assert abs(bs.x - R) < 1e-4 and abs(bs.y - 1.5) < 1e-4 and abs(bs.z) < 1e-4, (
        f'Black Stone mismatch: {bs}, expected (+{R:.4f}, 1.5, 0.0)'
    )

    door = _local_three_to_world_three(H, 4.0, H - 2.6)
    assert door.x > 6.0 and door.z < -1.5 and abs(door.y - 4.0) < 1e-4, (
        f'Bab al-Kaaba must be on North-East face (+x, -z): got {door}'
    )

    hijr_apex = _local_three_to_world_three(0.0, HIJR_H, -(H + HIJR_B))
    exp_apex = -(H + HIJR_B) * math.sqrt(0.5)  # -9.75807
    assert (
        abs(hijr_apex.x - exp_apex) < 1e-3
        and abs(hijr_apex.y - HIJR_H) < 1e-4
        and abs(hijr_apex.z - exp_apex) < 1e-3
    ), f'Hijr apex mismatch: {hijr_apex}, expected ({exp_apex:.4f}, {HIJR_H}, {exp_apex:.4f})'

    yamani = _local_three_to_world_three(-H, 1.2, H)
    assert abs(yamani.x) < 1e-4 and abs(yamani.y - 1.2) < 1e-4 and abs(yamani.z - R) < 1e-4, (
        f'Yamani corner mismatch: {yamani}, expected (0.0, 1.2, +{R:.4f})'
    )

    mizab_tip = _local_three_to_world_three(0.0, 12.8, -(H + 1.1))
    assert mizab_tip.x < -4.5 and mizab_tip.z < -4.5 and abs(mizab_tip.y - 12.8) < 1e-4, (
        f'Mizab al-Rahmah must project North-West over Hijr: got {mizab_tip}'
    )
    return {
        'black_stone': [round(bs.x, 4), round(bs.y, 4), round(bs.z, 4)],
        'bab_al_kaaba': [round(door.x, 4), round(door.y, 4), round(door.z, 4)],
        'hijr_apex': [round(hijr_apex.x, 4), round(hijr_apex.y, 4), round(hijr_apex.z, 4)],
        'yamani': [round(yamani.x, 4), round(yamani.y, 4), round(yamani.z, 4)],
        'mizab_tip': [round(mizab_tip.x, 4), round(mizab_tip.y, 4), round(mizab_tip.z, 4)],
    }


# ------------------------------------------------------------------ materials
def _make_materials():
    kiswa_alb, kiswa_nrm = textures.tex_kiswa(size=1024, name='tex_kaaba_kiswa')
    gold_alb, gold_nrm = textures.tex_gold_relief(size=512, name='tex_kaaba_gold_relief')
    marble_c_alb, marble_c_nrm = textures.tex_marble_cream(size=512, name='tex_kaaba_marble_cream', tiles=4)
    marble_w_alb, marble_w_nrm = textures.tex_marble_white(size=512, name='tex_kaaba_marble_white', tiles=4)

    mats = {
        'kiswa': common.make_pbr_material(
            'mat_kaaba_kiswa',
            color='#121318',
            roughness=0.58,
            metallic=0.06,
            image=kiswa_alb,
            normal_image=kiswa_nrm,
            normal_strength=0.72,
            use_vcol=False,
        ),
        'roof': common.make_pbr_material(
            'mat_kaaba_roof',
            color='#262523',
            roughness=0.82,
            metallic=0.0,
            use_vcol=True,
        ),
        'gold_trim': common.make_pbr_material(
            'mat_kaaba_gold_trim',
            color='#dfb44b',
            roughness=0.28,
            metallic=0.88,
            use_vcol=False,
        ),
        'gold_bright': common.make_pbr_material(
            'mat_kaaba_gold_bright',
            color='#edc65c',
            roughness=0.20,
            metallic=0.92,
            use_vcol=False,
        ),
        'gold_relief': common.make_pbr_material(
            'mat_kaaba_gold_relief',
            color='#d9ac43',
            roughness=0.26,
            metallic=0.88,
            image=gold_alb,
            normal_image=gold_nrm,
            normal_strength=0.85,
            use_vcol=False,
        ),
        'sitara_silk': common.make_pbr_material(
            'mat_kaaba_sitara_silk',
            color='#101218',
            roughness=0.52,
            metallic=0.08,
            use_vcol=False,
        ),
        'gold_dark': common.make_pbr_material(
            'mat_kaaba_gold_dark',
            color='#5c4217',
            roughness=0.38,
            metallic=0.76,
            use_vcol=False,
        ),
        'silver': common.make_pbr_material(
            'mat_kaaba_silver',
            color='#e0e3e8',
            roughness=0.18,
            metallic=0.95,
            use_vcol=False,
        ),
        'black_stone': common.make_pbr_material(
            'mat_kaaba_black_stone',
            color='#181417',
            roughness=0.24,
            metallic=0.08,
            use_vcol=False,
        ),
        'yamani_stone': common.make_pbr_material(
            'mat_kaaba_yamani_stone',
            color='#3a3530',
            roughness=0.52,
            metallic=0.02,
            use_vcol=True,
        ),
        'marble_cream': common.make_pbr_material(
            'mat_kaaba_marble_cream',
            color='#ebe1cf',
            roughness=0.26,
            metallic=0.0,
            image=marble_c_alb,
            normal_image=marble_c_nrm,
            normal_strength=0.35,
            use_vcol=True,
        ),
        'marble_white': common.make_pbr_material(
            'mat_kaaba_marble_white',
            color='#f3f2ee',
            roughness=0.22,
            metallic=0.0,
            image=marble_w_alb,
            normal_image=marble_w_nrm,
            normal_strength=0.30,
            use_vcol=True,
        ),
        'hijr_inlay': common.make_pbr_material(
            'mat_kaaba_hijr_inlay',
            color='#264538',
            roughness=0.30,
            metallic=0.08,
            use_vcol=True,
        ),
        'lantern_glow': common.make_pbr_material(
            'mat_kaaba_lantern_glow',
            color='#fff1cc',
            roughness=0.18,
            metallic=0.0,
            emissive='#ffd68a',
            emissive_strength=2.2,
            use_vcol=False,
        ),
    }
    return mats


# ------------------------------------------------------------------ geometry builders
def _build_kiswa_body(col, mats, lod='lod0'):
    """Build the 11.6 x 11.6 x 13.0 m Kaaba draped in silk Kiswa with real drape folds & roof."""
    nx = 20 if lod == 'lod0' else 10
    nz = 14 if lod == 'lod0' else 8
    z0 = SHAD_H
    z1 = SHAD_H + KAABA_H
    chamf = 0.045

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new('UVMap')

    # Four wall faces in local Blender space:
    # (name, p_start_xy, p_end_xy, outward_normal_xy)
    faces_spec = [
        # +X face (NE wall, contains Bab al-Kaaba): from (H, H) -> (H, -H) so u goes North -> East (Black Stone)
        ((H, H - chamf), (H, -H + chamf), (1.0, 0.0)),
        # -Y face (SE wall, Black Stone -> Yamani): from (H, -H) -> (-H, -H)
        ((H - chamf, -H), (-H + chamf, -H), (0.0, -1.0)),
        # -X face (SW wall, Yamani -> Shami): from (-H, -H) -> (-H, H)
        ((-H, -H + chamf), (-H, H - chamf), (-1.0, 0.0)),
        # +Y face (NW wall, Hijr Ismail side): from (-H, H) -> (H, H)
        ((-H + chamf, H), (H - chamf, H), (0.0, 1.0)),
    ]

    edge_cols = []  # store first & last vertical column of verts per face to stitch chamfered corners
    for p0, p1, nrm in faces_spec:
        grid = []
        for iz in range(nz + 1):
            v = iz / nz
            z = z0 + (z1 - z0) * v
            # Subtle vertical drape weighting (taut near top/Hizam, gentle softness lower down)
            drape_amp = 0.015 * math.sin(v * math.pi) * (1.0 - 0.35 * v)
            row = []
            for ix in range(nx + 1):
                u = ix / nx
                px = p0[0] + (p1[0] - p0[0]) * u
                py = p0[1] + (p1[1] - p0[1]) * u
                # 4 cloth panels across each wall + gentle vertical silk wave + seam tuck
                panel_wave = math.sin(u * 4.0 * math.tau + 0.3) * 0.65 + math.sin(u * 8.0 * math.tau) * 0.35
                seam_u = abs(((u * 4.0) % 1.0) - 0.5)
                seam_tuck = -0.008 * max(0.0, 1.0 - min(seam_u, 0.5 - seam_u) / 0.06)
                # Keep outer edges flush so chamfered corners close cleanly
                edge_fade = math.sin(u * math.pi) ** 0.35
                disp = (panel_wave * drape_amp + seam_tuck) * edge_fade
                vert = bm.verts.new((px + nrm[0] * disp, py + nrm[1] * disp, z))
                row.append((vert, u, v))
            grid.append(row)

        for iz in range(nz):
            for ix in range(nx):
                v00, u00, w00 = grid[iz][ix]
                v10, u10, w10 = grid[iz][ix + 1]
                v11, u11, w11 = grid[iz + 1][ix + 1]
                v01, u01, w01 = grid[iz + 1][ix]
                f = bm.faces.new((v00, v10, v11, v01))
                for lp, (uu, vv) in zip(f.loops, ((u00, w00), (u10, w10), (u11, w11), (u01, w01))):
                    lp[uv_layer].uv = (uu, vv)

        edge_cols.append(([grid[iz][0] for iz in range(nz + 1)], [grid[iz][-1] for iz in range(nz + 1)]))

    # Stitch the 4 chamfered vertical corners cleanly
    for idx in range(4):
        col_a = edge_cols[idx][1]
        col_b = edge_cols[(idx + 1) % 4][0]
        for iz in range(nz):
            va0, ua0, wa0 = col_a[iz]
            va1, ua1, wa1 = col_a[iz + 1]
            vb0, ub0, wb0 = col_b[iz]
            vb1, ub1, wb1 = col_b[iz + 1]
            f = bm.faces.new((va0, vb0, vb1, va1))
            for lp, (uu, vv) in zip(f.loops, ((0.99, wa0), (0.01, wb0), (0.01, wb1), (0.99, wa1))):
                lp[uv_layer].uv = (uu, vv)

    kiswa_obj = common.bm_to_obj(bm, f'kaaba_kiswa_{lod}', col, mat=mats['kiswa'], smooth=True)

    # Dark matte roof & low Kiswa-draped parapet lip + central roof hatch
    bm_roof = bmesh.new()
    # Recessed roof floor slab
    common.add_box(bm_roof, (0.0, 0.0, z1 - 0.06), (2 * H - 0.36, 2 * H - 0.36, 0.12))
    # Low parapet rim around perimeter (4 bars)
    rim_w = 0.24
    rim_h = 0.16
    rim_z = z1 + 0.02
    common.add_box(bm_roof, (0.0, H - rim_w * 0.5, rim_z), (2 * H, rim_w, rim_h))
    common.add_box(bm_roof, (0.0, -H + rim_w * 0.5, rim_z), (2 * H, rim_w, rim_h))
    common.add_box(bm_roof, (H - rim_w * 0.5, 0.0, rim_z), (rim_w, 2 * H - 2 * rim_w, rim_h))
    common.add_box(bm_roof, (-H + rim_w * 0.5, 0.0, rim_z), (rim_w, 2 * H - 2 * rim_w, rim_h))
    # Subtle historical roof hatch housing (Bab al-Tawbah roof access)
    common.add_box(bm_roof, (2.2, 2.2, z1 + 0.12), (1.35, 1.15, 0.24))
    roof_obj = common.bm_to_obj(bm_roof, f'kaaba_roof_{lod}', col, mat=mats['roof'], smooth=False)
    common.uv_box_project(roof_obj, scale=0.25)

    # Raised 3D Metallic Brushed-Gold Hizam Trim Rails (framing v in [0.68, 0.77] -> z in [9.24, 10.41])
    bm_hizam = bmesh.new()
    hz_bot = z0 + KAABA_H * 0.68
    hz_top = z0 + KAABA_H * 0.77
    rail_span = 2.0 * H + 0.045
    for hz in (hz_bot, hz_bot + 0.10, hz_top - 0.10, hz_top):
        thick = 0.055 if hz in (hz_bot, hz_top) else 0.032
        proj = 0.028 if hz in (hz_bot, hz_top) else 0.020
        for sgn in (1.0, -1.0):
            common.add_box(bm_hizam, (sgn * (H + proj * 0.5), 0.0, hz), (proj, rail_span, thick))
            common.add_box(bm_hizam, (0.0, sgn * (H + proj * 0.5), hz), (rail_span, proj, thick))

    if lod == 'lod0':
        # Vertical metallic gold panel dividers & corner medallions along the Hizam belt
        hz_mid = 0.5 * (hz_bot + hz_top)
        hz_h = hz_top - hz_bot - 0.14
        for frac in (-0.5, 0.0, 0.5):
            off = frac * (2.0 * H)
            for sgn in (1.0, -1.0):
                common.add_box(bm_hizam, (sgn * (H + 0.018), off, hz_mid), (0.024, 0.075, hz_h))
                common.add_box(bm_hizam, (off, sgn * (H + 0.018), hz_mid), (0.075, 0.024, hz_h))
        # Subtle metallic corner rosette bosses at the 4 corners inside Hizam band
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                common.add_box(
                    bm_hizam,
                    (sx * (H + 0.008), sy * (H + 0.008), hz_mid),
                    (0.11, 0.11, hz_h + 0.12),
                    rot_z=math.pi / 4.0,
                )

    hizam_obj = common.bm_to_obj(bm_hizam, f'kaaba_hizam_rails_{lod}', col, mat=mats['gold_trim'], smooth=False)
    common.uv_box_project(hizam_obj, scale=0.5)

    return [kiswa_obj, roof_obj, hizam_obj]


def _build_shadharwan(col, mats, lod='lod0'):
    """Sloped polished cream-marble plinth (y in [0, 0.42]) + brass Kiswa tie-rings."""
    bm = bmesh.new()

    # Cross-section profile from ground up: (outward_offset_from_H, z)
    # Wraps cleanly around all 4 sides with chamfered marble coping
    prof = [
        (0.32, 0.00),
        (0.32, 0.14),
        (0.08, 0.36),
        (0.06, 0.42),
        (-0.02, 0.42),
    ]
    rings = []
    for off, z in prof:
        s = H + off
        # 4 corners CCW around Z
        ring = [
            bm.verts.new((s, -s, z)),
            bm.verts.new((s, s, z)),
            bm.verts.new((-s, s, z)),
            bm.verts.new((-s, -s, z)),
        ]
        rings.append(ring)

    common.loft_rings(bm, rings, closed_u=True, cap_start=False, cap_end=False)
    # Close bottom slightly so no open underside if viewed low
    shad_obj = common.bm_to_obj(bm, f'kaaba_shadharwan_{lod}', col, mat=mats['marble_cream'], smooth=False)
    common.uv_box_project(shad_obj, scale=0.45)

    objs = [shad_obj]

    if lod == 'lod0':
        # Small brass Kiswa tie-rings (Halaq) anchored along the sloped marble base
        bm_rings = bmesh.new()
        ring_positions = [
            # +X face (skip right beneath door at y = -3.2)
            (H + 0.24, 3.6, 0.20, 0.0),
            (H + 0.24, 0.6, 0.20, 0.0),
            (H + 0.24, -4.8, 0.20, 0.0),
            # -Y face
            (3.4, -(H + 0.24), 0.20, -math.pi / 2.0),
            (0.0, -(H + 0.24), 0.20, -math.pi / 2.0),
            (-3.4, -(H + 0.24), 0.20, -math.pi / 2.0),
            # -X face
            (-(H + 0.24), -3.4, 0.20, math.pi),
            (-(H + 0.24), 0.0, 0.20, math.pi),
            (-(H + 0.24), 3.4, 0.20, math.pi),
            # +Y face
            (-3.4, H + 0.24, 0.20, math.pi / 2.0),
            (0.0, H + 0.24, 0.20, math.pi / 2.0),
            (3.4, H + 0.24, 0.20, math.pi / 2.0),
        ]
        segs = 8
        for rx, ry, rz, rot_z in ring_positions:
            # Anchor lug
            common.add_box(bm_rings, (rx, ry, rz + 0.02), (0.07, 0.05, 0.05), rot_z=rot_z)
            # Mini brass tie-loop
            pts = []
            for k in range(segs + 1):
                a = k / segs * math.tau
                lx = 0.03 + 0.025 * math.cos(a)
                ly = 0.055 * math.sin(a)
                lz = -0.03 + 0.055 * math.cos(a)
                v = Matrix.Rotation(rot_z, 3, 'Z') @ Vector((lx, ly, lz))
                pts.append(Vector((rx, ry, rz)) + v)
            common.add_tube(bm_rings, pts, radius=0.011, segs=5, closed_caps=False)
        rings_obj = common.bm_to_obj(bm_rings, f'kaaba_tie_rings_{lod}', col, mat=mats['gold_trim'], smooth=True)
        objs.append(rings_obj)

    return objs


def _build_bab_al_kaaba(col, mats, lod='lod0'):
    """Sculpted gilded Bab al-Kaaba double doors + Sitara valance on NE face (+X, by=-3.2)."""
    cy = -(H - 2.6)  # local Three.js z = +3.2 -> Blender y = -3.2
    z_bot = 2.20
    z_top = 5.80
    cz = 0.5 * (z_bot + z_top)  # 4.0
    door_h = z_top - z_bot  # 3.60
    door_w = 1.96

    # 1. Dark antique-bronze/gold recessed outer architrave jamb & lintel
    bm_dark = bmesh.new()
    common.add_box(bm_dark, (H + 0.035, cy, cz), (0.07, door_w + 0.42, door_h + 0.36))
    # Threshold step plinth below door
    common.add_box(bm_dark, (H + 0.09, cy, z_bot - 0.11), (0.18, door_w + 0.48, 0.16))
    dark_obj = common.bm_to_obj(bm_dark, f'kaaba_door_frame_{lod}', col, mat=mats['gold_dark'], smooth=False)
    common.uv_box_project(dark_obj, scale=0.6)

    # Sitara (Burqu') jet-black silk backing drape above doorway (z in [5.86, 8.92])
    sit_z0, sit_z1 = 5.88, 8.92
    sit_cz = 0.5 * (sit_z0 + sit_z1)
    sit_h = sit_z1 - sit_z0
    sit_w = 2.34
    bm_sit = bmesh.new()
    common.add_box(bm_sit, (H + 0.024, cy, sit_cz), (0.036, sit_w, sit_h))
    sit_obj = common.bm_to_obj(bm_sit, f'kaaba_sitara_silk_{lod}', col, mat=mats['sitara_silk'], smooth=False)

    # 2. Gilded double door leaves & embroidered Sitara relief cartouches (`tex_gold_relief`)
    bm_leaves = bmesh.new()
    uv_l = bm_leaves.loops.layers.uv.new('UVMap')
    leaf_w = door_w * 0.485
    for sgn in (-1.0, 1.0):
        ly = cy + sgn * (door_w * 0.252)
        res = common.add_box(bm_leaves, (H + 0.075, ly, cz), (0.06, leaf_w, door_h - 0.08))
        for v in res['verts']:
            for f in v.link_faces:
                for lp in f.loops:
                    p = lp.vert.co
                    lp[uv_l].uv = ((p.y - (cy - door_w * 0.5)) / door_w * 2.0, (p.z - z_bot) / door_h * 3.0)
    # Embroidered Sitara gold-relief calligraphic panels & lower gilded valance band
    for bz, bh, bw in (
        (sit_z1 - 0.34, 0.42, sit_w - 0.24),
        (sit_z0 + 1.85, 0.38, sit_w - 0.32),
        (sit_z0 + 0.36, 0.44, sit_w - 0.22),
    ):
        res_s = common.add_box(bm_leaves, (H + 0.048, cy, bz), (0.022, bw, bh))
        for v in res_s['verts']:
            for f in v.link_faces:
                for lp in f.loops:
                    p = lp.vert.co
                    lp[uv_l].uv = ((p.y - (cy - bw * 0.5)) / bw * 2.0, (p.z - (bz - bh * 0.5)) / bh * 1.0)
    leaves_obj = common.bm_to_obj(bm_leaves, f'kaaba_door_leaves_{lod}', col, mat=mats['gold_relief'], smooth=False)

    # 3. Raised sculpted bright-gold moldings, stiles, medallions, ring knockers & Sitara embroidery
    bm_gold = bmesh.new()
    # Stepped gilded door architrave pilasters & lintel
    jamb_w = 0.13
    common.add_box(bm_gold, (H + 0.085, cy - door_w * 0.5 - jamb_w * 0.5, cz), (0.11, jamb_w, door_h + 0.22))
    common.add_box(bm_gold, (H + 0.085, cy + door_w * 0.5 + jamb_w * 0.5, cz), (0.11, jamb_w, door_h + 0.22))
    common.add_box(bm_gold, (H + 0.095, cy, z_top + 0.09), (0.13, door_w + 0.34, 0.18))
    common.add_box(bm_gold, (H + 0.095, cy, z_bot - 0.05), (0.14, door_w + 0.34, 0.10))
    # Central astragal meeting strip
    common.add_box(bm_gold, (H + 0.11, cy, cz), (0.045, 0.065, door_h - 0.06))

    # Recessed coffered panel moldings & medallions on each door leaf
    for sgn in (-1.0, 1.0):
        ly = cy + sgn * (door_w * 0.255)
        # 3 vertical coffer frames per leaf
        for pz, ph in ((z_bot + 0.62, 0.88), (cz, 1.02), (z_top - 0.62, 0.84)):
            pw = leaf_w - 0.18
            # Horizontal top/bottom rails of coffer
            common.add_box(bm_gold, (H + 0.112, ly, pz + ph * 0.5), (0.025, pw, 0.045))
            common.add_box(bm_gold, (H + 0.112, ly, pz - ph * 0.5), (0.025, pw, 0.045))
            # Vertical left/right stiles of coffer
            common.add_box(bm_gold, (H + 0.112, ly - pw * 0.5, pz), (0.025, 0.045, ph))
            common.add_box(bm_gold, (H + 0.112, ly + pw * 0.5, pz), (0.025, 0.045, ph))

        # Raised sculpted circular medallion in middle & upper panels
        for mz, mr in ((cz + 0.15, 0.22), (z_top - 0.62, 0.17)):
            m_segs = 14 if lod == 'lod0' else 8
            mat = Matrix.Translation((H + 0.118, ly, mz)) @ Matrix.Rotation(math.pi / 2.0, 4, 'Y')
            bmesh.ops.create_cone(
                bm_gold,
                cap_ends=True,
                cap_tris=False,
                segments=m_segs,
                radius1=mr,
                radius2=mr * 0.72,
                depth=0.04,
                matrix=mat,
            )

        # Sculpted brass ring knockers & mounting bosses at z = 3.55 m
        kz = 3.55
        ky = cy + sgn * 0.24
        mat_boss = Matrix.Translation((H + 0.125, ky, kz + 0.06)) @ Matrix.Rotation(math.pi / 2.0, 4, 'Y')
        bmesh.ops.create_cone(
            bm_gold,
            cap_ends=True,
            cap_tris=False,
            segments=10 if lod == 'lod0' else 6,
            radius1=0.068,
            radius2=0.042,
            depth=0.045,
            matrix=mat_boss,
        )
        r_segs = 12 if lod == 'lod0' else 8
        ring_pts = []
        for k in range(r_segs + 1):
            a = k / r_segs * math.tau
            ring_pts.append(Vector((H + 0.145, ky + 0.095 * math.cos(a), kz - 0.04 + 0.11 * math.sin(a))))
        common.add_tube(bm_gold, ring_pts, radius=0.017, segs=6 if lod == 'lod0' else 4, closed_caps=False)

    # Sitara (Burqu') embroidered gold valance panel framing above the doorway
    common.add_box(bm_gold, (H + 0.052, cy, sit_z1 - 0.05), (0.036, sit_w + 0.06, 0.085))
    common.add_box(bm_gold, (H + 0.052, cy, sit_z0 + 0.05), (0.036, sit_w + 0.06, 0.085))
    common.add_box(bm_gold, (H + 0.052, cy - sit_w * 0.5, sit_cz), (0.036, 0.08, sit_h))
    common.add_box(bm_gold, (H + 0.052, cy + sit_w * 0.5, sit_cz), (0.036, 0.08, sit_h))
    # Horizontal braided gold trim fillets framing the Sitara panels
    for bz in (sit_z0 + 0.64, sit_z0 + 1.56, sit_z0 + 2.14, sit_z1 - 0.60):
        common.add_box(bm_gold, (H + 0.056, cy, bz), (0.028, sit_w - 0.12, 0.055))
    # Graceful two-center pointed Islamic arch embroidery framing the Sitara centerpiece
    arch_pts = []
    n_arch = 14 if lod == 'lod0' else 8
    for k in range(n_arch + 1):
        t = k / n_arch
        u = (t - 0.5) * 2.0  # -1..1
        s = abs(u)
        ay = cy + u * (sit_w * 0.36)
        t_h = math.sqrt(max(0.0, 1.0 - ((s + 0.35) / 1.35) ** 2)) / 0.965828
        az = sit_z0 + 0.66 + t_h * 0.86
        arch_pts.append(Vector((H + 0.064, ay, az)))
    common.add_tube(bm_gold, arch_pts, radius=0.030, segs=6 if lod == 'lod0' else 4, closed_caps=True)
    # Central Sitara twin gilded medallions inside arch
    for mz, mr in ((sit_z0 + 1.08, 0.24), (sit_z1 - 0.34, 0.16)):
        mat_sm = Matrix.Translation((H + 0.062, cy, mz)) @ Matrix.Rotation(math.pi / 2.0, 4, 'Y')
        bmesh.ops.create_cone(
            bm_gold,
            cap_ends=True,
            cap_tris=False,
            segments=14 if lod == 'lod0' else 8,
            radius1=mr,
            radius2=mr * 0.72,
            depth=0.034,
            matrix=mat_sm,
        )

    gold_obj = common.bm_to_obj(bm_gold, f'kaaba_door_gold_{lod}', col, mat=mats['gold_bright'], smooth=True)
    common.uv_box_project(gold_obj, scale=0.8)

    return [dark_obj, sit_obj, leaves_obj, gold_obj]


def _build_black_stone(col, mats, lod='lod0'):
    """Sculpted oval hammered sterling-silver frame & glossy volcanic Black Stone at East corner."""
    # Local Blender position for Three.js local (+H, 1.5, +H) is (+H, -H, 1.5)
    # Outward corner normal in local Blender is (+1, -1, 0)/sqrt(2), i.e., rot_z = -pi/4
    center = Vector((H - 0.02, -H + 0.02, 1.50))
    rot_m = Matrix.Rotation(-math.pi / 4.0, 4, 'Z')
    xform = Matrix.Translation(center) @ rot_m

    # 1. Sculpted beveled oval sterling-silver frame (height ~0.68 m, width ~0.48 m)
    bm_sil = bmesh.new()
    u_segs = 28 if lod == 'lod0' else 16
    # Cross-section profile of oval funnel bezel: (scale_radii, depth_along_local_x)
    # Local +X points outward from the East corner toward world +X East
    rx_outer, rz_outer = 0.245, 0.345
    # Profile from wall attachment -> outer rounded bevel -> crest -> inner concave funnel -> stone collar
    profile = [
        (1.06, -0.06),
        (1.04, 0.04),
        (0.95, 0.12),
        (0.80, 0.145),
        (0.64, 0.115),
        (0.54, 0.065),
        (0.50, 0.015),
    ]
    rings = []
    for sc, dx in profile:
        ring = []
        for k in range(u_segs):
            a = k / u_segs * math.tau
            # Subtle traditional slight pear/oval fullness
            y_loc = math.cos(a) * rx_outer * sc
            z_loc = math.sin(a) * rz_outer * sc
            # Slight convex curve wrapping around the corner
            x_loc = dx - 0.035 * (math.cos(a) ** 2)
            ring.append(bm_sil.verts.new(xform @ Vector((x_loc, y_loc, z_loc))))
        rings.append(ring)

    common.loft_rings(bm_sil, rings, closed_u=True, cap_start=False, cap_end=False)
    # Close inner back plate behind stone recess so no gap is ever visible
    back_c = bm_sil.verts.new(xform @ Vector((-0.02, 0.0, 0.0)))
    for k in range(u_segs):
        bm_sil.faces.new((rings[-1][k], rings[-1][(k + 1) % u_segs], back_c))

    # Ornamental silver top/bottom clasp studs on the bezel rim
    if lod == 'lod0':
        for sz in (-0.31, 0.31):
            m_stud = xform @ Matrix.Translation((0.125, 0.0, sz)) @ Matrix.Rotation(math.pi / 2.0, 4, 'Y')
            bmesh.ops.create_cone(
                bm_sil,
                cap_ends=True,
                cap_tris=False,
                segments=10,
                radius1=0.045,
                radius2=0.028,
                depth=0.04,
                matrix=m_stud,
            )

    sil_obj = common.bm_to_obj(bm_sil, f'kaaba_black_stone_silver_{lod}', col, mat=mats['silver'], smooth=True)

    # 2. Glossy dark volcanic Black Stone interior cluster
    bm_st = bmesh.new()
    # Main dark matrix dome recessed neatly inside silver opening
    m_main = xform @ Matrix.Translation((0.045, 0.0, 0.0)) @ Matrix.Diagonal((0.085, 0.13, 0.175, 1.0))
    bmesh.ops.create_uvsphere(
        bm_st,
        u_segments=14 if lod == 'lod0' else 8,
        v_segments=10 if lod == 'lod0' else 6,
        radius=1.0,
        matrix=m_main,
    )
    if lod == 'lod0':
        # Subtle sculpted glossy stone fragments nestled in the dark volcanic matrix
        lobes = [
            (0.085, -0.045, 0.075, 0.045, 0.048, 0.052),
            (0.092, 0.042, 0.062, 0.042, 0.046, 0.050),
            (0.098, 0.002, 0.005, 0.048, 0.055, 0.058),
            (0.088, -0.052, -0.042, 0.042, 0.044, 0.048),
            (0.090, 0.048, -0.048, 0.040, 0.045, 0.046),
            (0.082, -0.006, -0.092, 0.038, 0.046, 0.042),
            (0.080, 0.008, 0.115, 0.034, 0.042, 0.036),
        ]
        for lx, ly, lz, sx, sy, sz in lobes:
            ml = xform @ Matrix.Translation((lx, ly, lz)) @ Matrix.Diagonal((sx, sy, sz, 1.0))
            bmesh.ops.create_uvsphere(bm_st, u_segments=8, v_segments=6, radius=1.0, matrix=ml)

    st_obj = common.bm_to_obj(bm_st, f'kaaba_black_stone_{lod}', col, mat=mats['black_stone'], smooth=True)
    return [sil_obj, st_obj]


def _build_yamani_corner(col, mats, lod='lod0'):
    """Subtle carved dark stone edge reveal at Al-Rukn al-Yamani (South corner, local (-H, -H))."""
    # Local Three.js (-H, 1.2, +H) -> local Blender (-H, -H, 1.2)
    bm = bmesh.new()
    # Chamfered dark basalt corner masonry flush with the Kaaba chamfer where Kiswa lifts slightly
    center = Vector((-H + 0.055, -H + 0.055, 1.28))
    common.add_box(bm, center, (0.20, 0.20, 1.66), rot_z=math.pi / 4.0)
    for zc in (0.76, 1.28, 1.80):
        common.add_box(bm, (-H + 0.050, -H + 0.050, zc), (0.215, 0.215, 0.035), rot_z=math.pi / 4.0)
    yam_obj = common.bm_to_obj(bm, f'kaaba_yamani_{lod}', col, mat=mats['yamani_stone'], smooth=False)
    common.uv_box_project(yam_obj, scale=0.8)
    return [yam_obj]


def _build_mizab(col, mats, lod='lod0'):
    """Gleaming gilded Mizab al-Rahmah rainspout projecting 1.1 m from NW parapet over Hijr."""
    # Local Three.js (0, 12.8, -H) -> local Blender (0, +H, 12.8), projecting along +Y to +H + 1.12
    bm = bmesh.new()
    length = 1.14
    w = 0.36
    h = 0.23
    wt = 0.045
    y0 = H - 0.08
    z0 = 12.82
    tilt = math.radians(-4.5)  # slight downward drainage slope toward +Y

    # Helper to transform spout-local (sx, sy_along, sz) into Kaaba local Blender space
    m_base = Matrix.Translation((0.0, y0, z0)) @ Matrix.Rotation(tilt, 4, 'X')

    def _add_spout_box(cx, cy, cz, sx, sy, sz):
        mat = m_base @ Matrix.Translation((cx, cy, cz)) @ Matrix.Diagonal((sx, sy, sz, 1.0))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mat)

    # Bottom trough floor
    _add_spout_box(0.0, length * 0.5, 0.0, w, length, wt)
    # Left & right side walls of the U-trough
    _add_spout_box(-w * 0.5 + wt * 0.5, length * 0.5, h * 0.5, wt, length, h)
    _add_spout_box(w * 0.5 - wt * 0.5, length * 0.5, h * 0.5, wt, length, h)
    # Top decorative rolled rim along both sides
    _add_spout_box(-w * 0.5 + wt * 0.5, length * 0.5, h + 0.02, wt * 1.5, length + 0.04, 0.045)
    _add_spout_box(w * 0.5 - wt * 0.5, length * 0.5, h + 0.02, wt * 1.5, length + 0.04, 0.045)
    # Flared downward curved drip tongue at the tip
    m_lip = m_base @ Matrix.Translation((0.0, length + 0.05, -0.035)) @ Matrix.Rotation(math.radians(-26.0), 4, 'X')
    bmesh.ops.create_cube(bm, size=1.0, matrix=m_lip @ Matrix.Diagonal((w * 0.92, 0.14, 0.035, 1.0)))
    # Wall mounting collar & decorative support corbel bracket beneath spout
    _add_spout_box(0.0, 0.06, h * 0.45, w + 0.18, 0.12, h + 0.18)
    _add_spout_box(0.0, 0.24, -0.14, w * 0.55, 0.36, 0.24)

    mizab_obj = common.bm_to_obj(bm, f'kaaba_mizab_{lod}', col, mat=mats['gold_bright'], smooth=False)
    common.uv_box_project(mizab_obj, scale=1.0)
    return [mizab_obj]


def _build_hijr_ismail(col, mats, lod='lod0'):
    """Exact elliptical marble Hijr Ismail (Al-Hatim) wall, inlaid floor & 3 gilded brass lanterns."""
    n_arc = 44 if lod == 'lod0' else 24
    # Start/end slightly clear of Shadharwan (q in [0.085, pi - 0.085] -> ~0.68 m entry gap on each side)
    q0 = 0.085
    q1 = math.pi - 0.085

    # Cross-section profile of curved wall in (s_offset_from_inner_edge, z)
    # Inner edge is at s=0 (semi-axes a, b), outer edge is at s=HIJR_T (semi-axes a+t, b+t)
    t = HIJR_T
    h = HIJR_H
    wall_prof = [
        (-0.04, 0.00),
        (-0.04, 0.16),
        (0.00, 0.20),
        (0.00, 1.12),
        (-0.04, 1.17),
        (0.06, 1.27),
        (t * 0.50, h),
        (t - 0.06, 1.27),
        (t + 0.04, 1.17),
        (t, 1.12),
        (t, 0.20),
        (t + 0.04, 0.16),
        (t + 0.04, 0.00),
    ]

    bm_wall = bmesh.new()
    rings = []
    for i in range(n_arc + 1):
        q = q0 + (q1 - q0) * (i / n_arc)
        cq, sq = math.cos(q), math.sin(q)
        ring = []
        for s_off, z in wall_prof:
            ra = HIJR_A + s_off
            rb = HIJR_B + s_off
            bx = cq * ra
            by = H + sq * rb
            ring.append(bm_wall.verts.new((bx, by, z)))
        rings.append(ring)

    # Loft along the arc (open_u=False -> actually each ring is a closed cross-section!)
    common.loft_rings(bm_wall, rings, closed_u=True, cap_start=True, cap_end=True)

    # Sculpted rounded end-pier finials at the two Hijr entrance ends
    for q_end in (q0, q1):
        cx = math.cos(q_end) * (HIJR_A + t * 0.5)
        cy = H + math.sin(q_end) * (HIJR_B + t * 0.5)
        common.add_cylinder(
            bm_wall,
            center=(cx, cy, h * 0.5),
            radius=t * 0.54,
            radius_top=t * 0.52,
            height=h,
            segs=12 if lod == 'lod0' else 8,
        )
        m_cap = Matrix.Translation((cx, cy, h)) @ Matrix.Diagonal((t * 0.50, t * 0.50, 0.14, 1.0))
        bmesh.ops.create_uvsphere(bm_wall, u_segments=12 if lod == 'lod0' else 8, v_segments=6, radius=1.0, matrix=m_cap)

    wall_obj = common.bm_to_obj(bm_wall, f'kaaba_hijr_wall_{lod}', col, mat=mats['marble_cream'], smooth=True)
    common.uv_box_project(wall_obj, scale=0.40)

    # Subtle inlaid green-marble fascia strip on inner & outer walls
    bm_inlay = bmesh.new()
    for s_off, n_sgn in ((-0.008, -1.0), (t + 0.008, 1.0)):
        inlay_rings = []
        for i in range(n_arc + 1):
            q = q0 + (q1 - q0) * (i / n_arc)
            ra = HIJR_A + s_off
            rb = HIJR_B + s_off
            bx = math.cos(q) * ra
            by = H + math.sin(q) * rb
            inlay_rings.append([
                bm_inlay.verts.new((bx, by, 0.78)),
                bm_inlay.verts.new((bx, by, 0.94)),
            ])
        for r0, r1 in zip(inlay_rings, inlay_rings[1:]):
            if n_sgn > 0:
                bm_inlay.faces.new((r0[0], r1[0], r1[1], r0[1]))
            else:
                bm_inlay.faces.new((r0[0], r0[1], r1[1], r1[0]))
    inlay_obj = common.bm_to_obj(bm_inlay, f'kaaba_hijr_inlay_{lod}', col, mat=mats['hijr_inlay'], smooth=True)
    common.uv_box_project(inlay_obj, scale=0.5)

    # Polished pale marble interior floor (z = 0.025, clearly above Mataf y=0 with zero Z-fighting)
    bm_fl = bmesh.new()
    uv_f = bm_fl.loops.layers.uv.new('UVMap')
    fl_segs = 40 if lod == 'lod0' else 24
    # Start cleanly just outside Shadharwan (by = H + 0.30) up to inner Hijr wall
    c_vert = bm_fl.verts.new((0.0, H + 0.32, 0.025))
    rim_verts = []
    for i in range(fl_segs + 1):
        q = math.pi * (i / fl_segs)
        bx = math.cos(q) * (HIJR_A + 0.06)
        by = max(H + 0.32, H + math.sin(q) * (HIJR_B + 0.06))
        rim_verts.append(bm_fl.verts.new((bx, by, 0.025)))
    for i in range(fl_segs):
        f = bm_fl.faces.new((c_vert, rim_verts[i], rim_verts[i + 1]))
        for lp in f.loops:
            lp[uv_f].uv = (lp.vert.co.x * 0.28, lp.vert.co.y * 0.28)
    floor_obj = common.bm_to_obj(bm_fl, f'kaaba_hijr_floor_{lod}', col, mat=mats['marble_white'], smooth=False)

    # 3 Delicate Gilded Brass Lanterns mounted atop the curved Hijr wall
    bm_lan_metal = bmesh.new()
    bm_lan_glow = bmesh.new()
    lan_segs = 10 if lod == 'lod0' else 6
    for q_l in (math.pi * 0.25, math.pi * 0.50, math.pi * 0.75):
        lx = math.cos(q_l) * (HIJR_A + t * 0.5)
        ly = H + math.sin(q_l) * (HIJR_B + t * 0.5)
        lz = h - 0.02
        # Turned brass pedestal foot
        common.add_cylinder(bm_lan_metal, (lx, ly, lz + 0.06), 0.16, 0.12, segs=lan_segs, radius_top=0.09)
        common.add_cylinder(bm_lan_metal, (lx, ly, lz + 0.18), 0.06, 0.14, segs=lan_segs, radius_top=0.11)
        # Lower & upper lantern rings
        common.add_cylinder(bm_lan_metal, (lx, ly, lz + 0.28), 0.15, 0.05, segs=6)
        common.add_cylinder(bm_lan_metal, (lx, ly, lz + 0.66), 0.17, 0.05, segs=6)
        # 6 slender vertical brass corner ribs around lantern glass
        n_ribs = 6 if lod == 'lod0' else 4
        for k in range(n_ribs):
            a = k / n_ribs * math.tau
            rx = lx + math.cos(a) * 0.135
            ry = ly + math.sin(a) * 0.135
            common.add_cylinder(bm_lan_metal, (rx, ry, lz + 0.47), 0.012, 0.38, segs=5)
        # Domed brass lantern cap & spire finial
        common.add_cylinder(bm_lan_metal, (lx, ly, lz + 0.76), 0.17, 0.15, segs=lan_segs, radius_top=0.03)
        common.add_cylinder(bm_lan_metal, (lx, ly, lz + 0.90), 0.022, 0.14, segs=6, radius_top=0.006)
        # Glowing warm frosted glass inner cylinder
        common.add_cylinder(bm_lan_glow, (lx, ly, lz + 0.47), 0.115, 0.35, segs=lan_segs, radius_top=0.125)

    lan_metal_obj = common.bm_to_obj(bm_lan_metal, f'kaaba_hijr_lanterns_{lod}', col, mat=mats['gold_bright'], smooth=True)
    lan_glow_obj = common.bm_to_obj(bm_lan_glow, f'kaaba_hijr_lantern_glow_{lod}', col, mat=mats['lantern_glow'], smooth=True)

    return [wall_obj, inlay_obj, floor_obj, lan_metal_obj, lan_glow_obj]


def _bake_and_join_lod(parts, name, col):
    """Bake gentle vertex AO onto marble/stone subparts, join into one mesh, and bake +45 deg Z rotation."""
    ao_mats = {'mat_kaaba_marble_cream', 'mat_kaaba_marble_white', 'mat_kaaba_roof', 'mat_kaaba_yamani_stone', 'mat_kaaba_hijr_inlay'}
    for obj in parts:
        # Ensure all joined subparts have a 'Color' attribute so join preserves AO cleanly
        uses_ao = any(m and m.name in ao_mats for m in obj.data.materials)
        if uses_ao:
            common.bake_vertex_ao(obj, strength=0.22, min_val=0.72)
        else:
            me = obj.data
            if me.color_attributes.get('Color') is None:
                ca = me.color_attributes.new(name='Color', type='BYTE_COLOR', domain='POINT')
                for i in range(len(ca.data)):
                    ca.data[i].color = (1.0, 1.0, 1.0, 1.0)

    joined = common.join_objects(parts, name, col=col)
    # Bake exact +45 deg rotation around Blender +Z directly into mesh geometry so world orientation is intrinsic!
    rot_mat = Matrix.Rotation(KAABA_ROT_Z, 4, 'Z')
    joined.data.transform(rot_mat)
    joined.data.update()
    return joined


def build_kaaba(col):
    """Build `kaaba_LOD0` and `kaaba_LOD1` in `col`, rotated cleanly to exact world orientation."""
    _assert_landmark_orientation()
    mats = _make_materials()

    parts_lod0 = []
    parts_lod0.extend(_build_kiswa_body(col, mats, lod='lod0'))
    parts_lod0.extend(_build_shadharwan(col, mats, lod='lod0'))
    parts_lod0.extend(_build_bab_al_kaaba(col, mats, lod='lod0'))
    parts_lod0.extend(_build_black_stone(col, mats, lod='lod0'))
    parts_lod0.extend(_build_yamani_corner(col, mats, lod='lod0'))
    parts_lod0.extend(_build_mizab(col, mats, lod='lod0'))
    parts_lod0.extend(_build_hijr_ismail(col, mats, lod='lod0'))
    lod0 = _bake_and_join_lod(parts_lod0, 'kaaba_LOD0', col)

    parts_lod1 = []
    parts_lod1.extend(_build_kiswa_body(col, mats, lod='lod1'))
    parts_lod1.extend(_build_shadharwan(col, mats, lod='lod1'))
    parts_lod1.extend(_build_bab_al_kaaba(col, mats, lod='lod1'))
    parts_lod1.extend(_build_black_stone(col, mats, lod='lod1'))
    parts_lod1.extend(_build_yamani_corner(col, mats, lod='lod1'))
    parts_lod1.extend(_build_mizab(col, mats, lod='lod1'))
    parts_lod1.extend(_build_hijr_ismail(col, mats, lod='lod1'))
    lod1 = _bake_and_join_lod(parts_lod1, 'kaaba_LOD1', col)

    return lod0, lod1


def _render_two_angle_preview(lod0, lod1, out_path):
    """Render 2-angle hero preview: Left = East/NE (Door + Black Stone), Right = NW (Hijr + Mizab)."""
    lod1.hide_render = True
    lod1.hide_viewport = True

    # Add temporary bright marble courtyard ground plane just for realistic preview bounce/shadow
    tmp_col = common.make_collection('_KaabaPreviewGround')
    bm_g = bmesh.new()
    common.add_cylinder(bm_g, center=(0.0, 0.0, -0.04), radius=36.0, height=0.08, segs=48)
    w_alb = bpy.data.images.get('tex_kaaba_marble_white')
    w_nrm = bpy.data.images.get('tex_kaaba_marble_white_nrm')
    g_mat = common.make_pbr_material(
        '_mat_prev_mataf',
        color='#f2f2ef',
        roughness=0.25,
        image=w_alb,
        normal_image=w_nrm,
        normal_strength=0.25,
        uv_scale=(12.0, 12.0),
    )
    g_obj = common.bm_to_obj(bm_g, '_PrevMatafFloor', tmp_col, mat=g_mat, smooth=False)
    common.uv_box_project(g_obj, scale=0.12)

    shots = [
        # Shot 1: East / North-East Hero — full Kaaba height, Black Stone corner, Gold Door & Sitara
        (common.three_to_bl(26.0, 10.5, -10.5), common.three_to_bl(0.8, 6.2, -0.8), 36),
        # Shot 2: North-West 3/4 Hijr Ismail Hero — curved marble wall, 3 brass lanterns & projecting Mizab
        (common.three_to_bl(-26.5, 12.0, -16.5), common.three_to_bl(-2.5, 5.6, -3.5), 35),
    ]

    tiles = []
    tmp_files = []
    try:
        for idx, (eye, tgt, lens) in enumerate(shots):
            with tempfile.NamedTemporaryFile(suffix=f'_kaaba_{idx}.png', delete=False) as tf:
                tmp_png = tf.name
            tmp_files.append(tmp_png)
            preview.render_shot(
                eye=eye,
                target=tgt,
                out_path=tmp_png,
                res=(720, 600),
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
        out_img = bpy.data.images.new('_KaabaHeroSheet', sw, sh, alpha=True)
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


def export_kaaba(render_preview=True):
    """Build, verify, export `public/models/env/kaaba.glb`, and render `env_kaaba.png`."""
    common.ensure_dirs()
    common.reset_scene()
    landmarks = _assert_landmark_orientation()

    col = common.make_collection('Kaaba')
    lod0, lod1 = build_kaaba(col)

    t0 = common.tri_count(lod0)
    t1 = common.tri_count(lod1)
    assert t0 <= 14000, f'kaaba_LOD0 tris {t0} > 14000'
    assert t1 <= 6500, f'kaaba_LOD1 tris {t1} > 6500'

    # Also verify world bounding box of rotated LOD0 covers East Black Stone (+8.2) & NW Hijr (-10.4)
    xs = [v.co.x for v in lod0.data.vertices]
    ys = [v.co.y for v in lod0.data.vertices]
    zs = [v.co.z for v in lod0.data.vertices]
    # Three.js world: tx = bx, ty = bz, tz = -by
    assert max(xs) > 8.1 and max(xs) < 9.0, f'Unexpected East extent: {max(xs):.2f}'
    assert min(xs) < -10.0 and max(ys) > 10.0, f'Unexpected NW Hijr extent: min_x={min(xs):.2f}, max_by={max(ys):.2f}'
    assert min(zs) >= -0.01 and max(zs) > 13.3, f'Unexpected height extent: {min(zs):.2f}..{max(zs):.2f}'

    out_glb = common.MODELS_ENV / 'kaaba.glb'
    size_bytes = common.export_glb([lod0, lod1], out_glb, vertex_colors=False)
    _verify_glb(out_glb, size_bytes, max_kb=550)

    out_png = common.PREVIEWS / 'env_kaaba.png'
    if render_preview:
        _render_two_angle_preview(lod0, lod1, out_png)

    info = {
        'name': 'kaaba',
        'glb': str(out_glb.relative_to(ROOT)),
        'tris_lod0': t0,
        'tris_lod1': t1,
        'size_kb': round(size_bytes / 1024.0, 1),
        'landmarks': landmarks,
    }
    print(f"KAABA_OK tris={t0}/{t1} size={info['size_kb']}KB landmarks={landmarks}")
    return info


if __name__ == '__main__':
    export_kaaba(render_preview=True)
