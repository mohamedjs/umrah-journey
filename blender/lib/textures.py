"""Deterministic NumPy procedural PBR texture generators for umrah-journey.

All textures are generated in-memory with zero external image dependencies (no PIL)
and packed directly into Blender images via common.pack_image(). Normal maps use
OpenGL tangent-space convention (+X right, +Y up, +Z out) packed as 'Non-Color'.
"""
import math
import sys

import numpy as np

from .common import hex_rgb, pack_image

sys.dont_write_bytecode = True


# ------------------------------------------------------------------ noise & normal helpers
def _tileable_value_noise(size, freq, rng):
    """Generate a seamless tileable 2D value noise field in [0, 1] of shape (size, size)."""
    freq = max(1, int(freq))
    grid = rng.random((freq, freq), dtype=np.float32)

    coords = np.linspace(0.0, float(freq), size, endpoint=False, dtype=np.float32)
    i0 = np.floor(coords).astype(np.int32) % freq
    i1 = (i0 + 1) % freq
    f = coords - np.floor(coords)
    # Quintic smoothstep for artifact-free derivatives
    s = f * f * f * (f * (f * 6.0 - 15.0) + 10.0)

    sx = s[None, :]
    sy = s[:, None]

    c00 = grid[i0[:, None], i0[None, :]]
    c10 = grid[i0[:, None], i1[None, :]]
    c01 = grid[i1[:, None], i0[None, :]]
    c11 = grid[i1[:, None], i1[None, :]]

    nx0 = c00 * (1.0 - sx) + c10 * sx
    nx1 = c01 * (1.0 - sx) + c11 * sx
    return (nx0 * (1.0 - sy) + nx1 * sy).astype(np.float32)


def _tileable_fbm(size, base_freq=4, octaves=4, persistence=0.5, seed=101):
    """Seamless multi-octave fractal Brownian motion in [0, 1]."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((size, size), dtype=np.float32)
    amp = 1.0
    total_amp = 0.0
    freq = int(base_freq)
    for _ in range(octaves):
        acc += amp * _tileable_value_noise(size, min(freq, size), rng)
        total_amp += amp
        amp *= persistence
        freq *= 2
    return acc / max(total_amp, 1e-6)


def _height_to_normal(h, strength=2.0):
    """Convert a height field HxW (row 0 = bottom) to an OpenGL tangent-space RGB normal map."""
    h = np.asarray(h, dtype=np.float32)
    # Periodic central differences keep tileable maps seamless across edges
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5

    nx = -dx * float(strength)
    ny = -dy * float(strength)
    nz = np.ones_like(h, dtype=np.float32)

    inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-12)
    rgb = np.stack(
        [
            nx * inv_len * 0.5 + 0.5,
            ny * inv_len * 0.5 + 0.5,
            nz * inv_len * 0.5 + 0.5,
        ],
        axis=-1,
    )
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


def _uv_grid(size):
    """Return (u, v) float32 grids in [0, 1) with shape (size, size), row 0 = bottom."""
    lin = np.linspace(0.0, 1.0, size, endpoint=False, dtype=np.float32)
    u, v = np.meshgrid(lin, lin)
    return u, v


def _smoothstep_np(e0, e1, x):
    t = np.clip((x - e0) / max(e1 - e0, 1e-7), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _rgb_vec(color):
    if isinstance(color, str):
        return np.array(hex_rgb(color), dtype=np.float32)
    return np.array(color[:3], dtype=np.float32)


# ------------------------------------------------------------------ marble textures
def _make_marble_tiles(size, name, tiles, base_col, vein_col, warm_col, grout_col, seed):
    u, v = _uv_grid(size)
    n1 = _tileable_fbm(size, base_freq=3, octaves=5, persistence=0.52, seed=seed)
    n2 = _tileable_fbm(size, base_freq=7, octaves=4, persistence=0.50, seed=seed + 17)
    n3 = _tileable_fbm(size, base_freq=16, octaves=3, persistence=0.45, seed=seed + 31)

    # Organic domain-warped veins
    phase = (u * 2.0 + v * 1.0) * math.tau + (n1 - 0.5) * 5.2 + (n2 - 0.5) * 2.1
    vein_primary = np.power(1.0 - np.abs(np.sin(phase)), 7.0)
    phase2 = (u * 1.0 - v * 2.0) * math.tau + (n2 - 0.5) * 6.0
    vein_fine = np.power(1.0 - np.abs(np.sin(phase2)), 11.0) * 0.55

    # Tile grid with slight per-tile brightness variation
    tiles = max(1, int(tiles))
    tu = (u * tiles) % 1.0
    tv = (v * tiles) % 1.0
    ix = np.floor(u * tiles).astype(np.int32)
    iy = np.floor(v * tiles).astype(np.int32)
    tile_hash = np.sin(ix * 12.9898 + iy * 78.233 + seed * 0.37) * 43758.5453
    tile_var = (tile_hash - np.floor(tile_hash) - 0.5) * 0.032

    # Crisp subtle tile joints
    gw = 0.011
    dist_edge = np.minimum(np.minimum(tu, 1.0 - tu), np.minimum(tv, 1.0 - tv))
    grout = 1.0 - _smoothstep_np(gw * 0.45, gw * 1.35, dist_edge)

    rgb = np.ones((size, size, 3), dtype=np.float32) * base_col
    rgb += (n1[..., None] - 0.5) * 0.055 + tile_var[..., None]
    rgb = rgb * (1.0 - 0.25 * n2[..., None]) + warm_col * (0.25 * n2[..., None])
    vein_mix = np.clip(vein_primary * 0.48 + vein_fine * 0.35, 0.0, 0.72)[..., None]
    rgb = rgb * (1.0 - vein_mix) + vein_col * vein_mix
    rgb = rgb * (1.0 - grout[..., None] * 0.75) + grout_col * (grout[..., None] * 0.75)
    rgb = np.clip(rgb, 0.0, 1.0)

    # Height: subtle polish micro-undulation + depressed grout grooves + tiny vein relief
    h = 0.75 + (n3 - 0.5) * 0.02 - vein_primary * 0.015 - grout * 0.38
    nrm = _height_to_normal(h, strength=2.6)

    alb_img = pack_image(name, rgb, colorspace='sRGB')
    nrm_img = pack_image(f'{name}_nrm', nrm, colorspace='Non-Color')
    return alb_img, nrm_img


def tex_marble_white(size=512, name='tex_marble_white', tiles=4):
    """Cool white Thassos marble tiles with subtle grey/warm veins and crisp joints."""
    return _make_marble_tiles(
        size=size,
        name=name,
        tiles=tiles,
        base_col=_rgb_vec('#f3f4f6'),
        vein_col=_rgb_vec('#b8bdc4'),
        warm_col=_rgb_vec('#eae7e1'),
        grout_col=_rgb_vec('#c7ccd1'),
        seed=201,
    )


def tex_marble_cream(size=512, name='tex_marble_cream', tiles=4):
    """Warm Mecca cream/beige polished marble tiles with delicate golden-taupe veins."""
    return _make_marble_tiles(
        size=size,
        name=name,
        tiles=tiles,
        base_col=_rgb_vec('#eee4d2'),
        vein_col=_rgb_vec('#b99f7d'),
        warm_col=_rgb_vec('#e5d5ba'),
        grout_col=_rgb_vec('#b7a58d'),
        seed=211,
    )


# ------------------------------------------------------------------ Kiswa silk & gold embroidery
def tex_kiswa(size=1024, name='tex_kiswa'):
    """Authentic jet-black woven silk Kiswa with chevron damask brocade and gold Hizam.

    Features:
    - Rich jet-black woven silk with diagonal/chevron damask brocade texture
    - Subtle vertical cloth panel seam shadows
    - Embroidered metallic gold Hizam band (v in [0.68, 0.77]) with double ornamental borders
    - Purely geometric/calligraphic woven oval & rectangular cartouche medallions (no Latin text)
    - Lower geometric corner panels & decorative star filigree
    Returns (albedo_img, normal_img).
    """
    u, v = _uv_grid(size)

    # 1. Jet-black silk base + subtle chevron/diamond damask brocade weave
    chev_u = np.abs(((u * 36.0) % 1.0) - 0.5) * 2.0
    chev_wave = np.sin((v * 24.0 + chev_u * 0.5) * math.tau)
    damask_diamond = np.cos((u * 18.0 + v * 18.0) * math.tau) * np.cos((u * 18.0 - v * 18.0) * math.tau)
    micro_silk = _tileable_fbm(size, base_freq=32, octaves=3, persistence=0.55, seed=307)
    sheen_var = _tileable_fbm(size, base_freq=4, octaves=3, persistence=0.5, seed=311)

    brocade = 0.5 + 0.30 * chev_wave + 0.20 * damask_diamond
    # Vertical cloth panel seam shadows (4 panels across wall width)
    seam_u = np.abs(((u * 4.0) % 1.0) - 0.5)
    seam_dist = np.minimum(seam_u, 0.5 - seam_u)
    seam_shadow = 1.0 - _smoothstep_np(0.0, 0.018, seam_dist)
    # Soft vertical drape folds
    drape = np.sin(u * 4.0 * math.tau + 0.4) * 0.012 + np.sin(u * 12.0 * math.tau) * 0.006

    silk_base = np.array([0.042, 0.044, 0.052], dtype=np.float32)
    silk_hi = np.array([0.088, 0.092, 0.106], dtype=np.float32)
    silk_mix = np.clip(brocade * 0.55 + micro_silk * 0.25 + sheen_var * 0.20, 0.0, 1.0)
    rgb = silk_base * (1.0 - silk_mix[..., None]) + silk_hi * silk_mix[..., None]
    rgb *= (1.0 - seam_shadow[..., None] * 0.38)
    rgb = np.clip(rgb + drape[..., None], 0.015, 1.0)

    # Height map starts with fine damask & panel seams
    height = 0.30 + brocade * 0.05 + micro_silk * 0.02 - seam_shadow * 0.08 + drape * 0.5

    # Helper for geometric braided gold border + filigree stroke pattern
    gold_mask = np.zeros((size, size), dtype=np.float32)
    gold_detail = np.zeros((size, size), dtype=np.float32)
    silver_mask = np.zeros((size, size), dtype=np.float32)

    # 2. Hizam (embroidered golden belt, v in [0.68, 0.77])
    h0, h1 = 0.68, 0.77
    in_hizam = (v >= h0) & (v <= h1)
    hv = (v - h0) / (h1 - h0)  # 0..1 inside Hizam

    # Double ornamental border rails at top & bottom of Hizam
    rail_outer = ((np.abs(hv - 0.05) < 0.032) | (np.abs(hv - 0.95) < 0.032)) & in_hizam
    rail_inner = ((np.abs(hv - 0.14) < 0.022) | (np.abs(hv - 0.86) < 0.022)) & in_hizam
    # Braided chain ornament between inner and outer rails
    braid_zone = (((hv > 0.07) & (hv < 0.13)) | ((hv > 0.87) & (hv < 0.93))) & in_hizam
    braid_pat = (np.sin(u * 96.0 * math.tau) * np.sin(hv * 40.0 * math.tau)) > -0.15

    # 4 main Hizam panel frames with rhythmic woven geometric/calligraphic cadence (non-textual)
    panel_u = (u * 4.0) % 1.0
    in_panel_core = in_hizam & (hv > 0.20) & (hv < 0.80)
    panel_div = in_hizam & (hv > 0.14) & (hv < 0.86) & ((panel_u < 0.022) | (panel_u > 0.978))

    # Decorative geometric divider diamond at panel junctions
    du_div = np.minimum(panel_u, 1.0 - panel_u) * 4.0
    dv_div = np.abs(hv - 0.5) * 2.0
    div_diamond = in_hizam & ((du_div * 1.4 + dv_div * 0.9) < 0.42) & ((du_div * 1.4 + dv_div * 0.9) > 0.24)

    # Woven calligraphic-inspired rhythmic vertical stems + sweeping horizontal ligatures + dots
    pu_inner = np.clip((panel_u - 0.04) / 0.92, 0.0, 1.0)
    valid_pu = (panel_u > 0.04) & (panel_u < 0.96) & in_panel_core
    # Vertical alif-like rhythmic strokes (periodic geometric spacing)
    stem_freq = np.sin(pu_inner * 14.0 * math.tau)
    stem_mod = np.sin(pu_inner * 3.5 * math.tau + 0.5)
    stems = (stem_freq > 0.72) & (hv > 0.28 + 0.08 * np.maximum(0.0, stem_mod)) & (hv < 0.75)
    # Interlaced sweeping wave baseline + upper arch flourishes
    wave1 = np.abs(hv - (0.36 + 0.09 * np.sin(pu_inner * 6.0 * math.tau))) < 0.042
    wave2 = np.abs(hv - (0.58 + 0.08 * np.cos(pu_inner * 9.0 * math.tau + 0.7))) < 0.032
    # Small diamond vocalization-style geometric accents
    acc_u = ((pu_inner * 18.0) % 1.0) - 0.5
    acc_v = (hv - 0.71) * 6.5
    accents = (np.abs(acc_u) + np.abs(acc_v)) < 0.28
    hizam_motif = valid_pu & (stems | wave1 | wave2 | accents)

    # Subtle silver accent dots inside the Hizam rails
    silver_dots = in_hizam & (
        ((np.abs(hv - 0.10) < 0.022) | (np.abs(hv - 0.90) < 0.022))
        & (np.cos(u * 64.0 * math.tau) > 0.65)
    )

    hizam_gold = (rail_outer | rail_inner | (braid_zone & braid_pat) | panel_div | div_diamond | hizam_motif).astype(np.float32)
    gold_mask = np.maximum(gold_mask, hizam_gold)
    gold_detail = np.maximum(gold_detail, hizam_gold * (0.75 + 0.25 * np.sin(u * 180.0 * math.tau + v * 120.0 * math.tau)))
    silver_mask = np.maximum(silver_mask, silver_dots.astype(np.float32))

    # 3. Oval & rectangular cartouche medallions below Hizam
    # Row 1: 4 ornate oval cartouches at v = 0.555
    for k in range(4):
        cu = (k + 0.5) / 4.0
        cv = 0.555
        du = ((u - cu + 0.5) % 1.0) - 0.5
        dv = v - cv
        ell = np.sqrt((du / 0.072) ** 2 + (dv / 0.036) ** 2)
        outer_ring = (ell >= 0.84) & (ell <= 1.0)
        inner_ring = (ell >= 0.68) & (ell <= 0.76)
        # Geometric rosette & filigree inside oval
        ang = np.arctan2(dv / 0.036, du / 0.072)
        rosette = (ell < 0.62) & (
            (np.abs(ell - (0.34 + 0.14 * np.cos(8.0 * ang))) < 0.065)
            | (ell < 0.16)
        )
        oval_gold = (outer_ring | inner_ring | rosette).astype(np.float32)
        gold_mask = np.maximum(gold_mask, oval_gold)
        gold_detail = np.maximum(gold_detail, oval_gold * 0.9)

    # Row 2: Alternating rectangular cartouches & lantern medallions at v = 0.37
    for k in range(4):
        cu = (k + 0.5) / 4.0
        cv = 0.38
        du = np.abs(((u - cu + 0.5) % 1.0) - 0.5)
        dv = np.abs(v - cv)
        rect_outer = (du <= 0.088) & (dv <= 0.042) & ((du >= 0.078) | (dv >= 0.034))
        rect_inner = (du <= 0.070) & (dv <= 0.028) & ((du >= 0.064) | (dv >= 0.023))
        # Geometric octagram/lattice fill inside rectangle
        in_rect = (du < 0.060) & (dv < 0.021)
        lattice = in_rect & (
            (np.abs(np.sin(du * 120.0) * np.cos(dv * 220.0)) > 0.42)
            | (np.abs(dv) < 0.004)
        )
        rect_gold = (rect_outer | rect_inner | lattice).astype(np.float32)
        gold_mask = np.maximum(gold_mask, rect_gold)
        gold_detail = np.maximum(gold_detail, rect_gold * 0.85)

    # 4. Lower corner geometric arabesque panels & subtle lower hem border
    in_hem = (v >= 0.04) & (v <= 0.068)
    hem_pat = in_hem & (
        (np.abs(v - 0.043) < 0.003)
        | (np.abs(v - 0.065) < 0.003)
        | (np.abs(np.sin(u * 48.0 * math.tau)) > 0.72)
    )
    gold_mask = np.maximum(gold_mask, hem_pat.astype(np.float32) * 0.85)

    # Corner / seam geometric corner rosettes at v = 0.17
    for cu in (0.125, 0.875):
        cv = 0.17
        du = ((u - cu + 0.5) % 1.0) - 0.5
        dv = v - cv
        r = np.hypot(du, dv)
        ang = np.arctan2(dv, du)
        star = (r < 0.052) & (
            (np.abs(r - (0.042 + 0.006 * np.cos(8.0 * ang))) < 0.0045)
            | (np.abs(r - (0.024 + 0.007 * np.cos(8.0 * ang + 0.4))) < 0.004)
            | (r < 0.009)
        )
        gold_mask = np.maximum(gold_mask, star.astype(np.float32))

    # Rich embroidered metallic gold thread color with woven thread shimmer
    thread_grain = 0.84 + 0.16 * np.sin((u * 320.0 + v * 160.0) * math.tau)
    gold_dark = np.array([0.62, 0.45, 0.12], dtype=np.float32)
    gold_bright = np.array([0.96, 0.79, 0.30], dtype=np.float32)
    g_t = np.clip(0.35 + 0.45 * thread_grain + 0.20 * gold_detail, 0.0, 1.0)[..., None]
    gold_rgb = gold_dark * (1.0 - g_t) + gold_bright * g_t

    silver_rgb = np.array([0.82, 0.84, 0.86], dtype=np.float32) * thread_grain[..., None]

    # Blend embroidery over silk
    gm = np.clip(gold_mask, 0.0, 1.0)[..., None]
    sm = np.clip(silver_mask * (1.0 - gold_mask * 0.5), 0.0, 1.0)[..., None]
    rgb = rgb * (1.0 - gm) + gold_rgb * gm
    rgb = rgb * (1.0 - sm) + silver_rgb * sm
    rgb = np.clip(rgb, 0.0, 1.0)

    # Raised embroidery relief in height map
    height = height + gold_mask * (0.28 + 0.08 * thread_grain) + silver_mask * 0.20
    nrm = _height_to_normal(height, strength=3.4)

    alb_img = pack_image(name, rgb, colorspace='sRGB')
    nrm_img = pack_image(f'{name}_nrm', nrm, colorspace='Non-Color')
    return alb_img, nrm_img


# ------------------------------------------------------------------ fabric & cloth textures
def tex_cotton_ihram(size=512, name='tex_cotton_ihram'):
    """Realistic off-white woven terry-cotton ihram cloth with subtle border stripe weave."""
    u, v = _uv_grid(size)
    # Terry-loop micro-weave grid + organic cotton slub noise
    warp = np.sin(u * 96.0 * math.tau)
    weft = np.sin(v * 96.0 * math.tau)
    terry = 0.5 + 0.28 * warp * weft + 0.12 * np.sin((u + v) * 192.0 * math.tau)
    slub = _tileable_fbm(size, base_freq=10, octaves=4, persistence=0.55, seed=401)

    # Subtle woven jacquard border band near hem (v in [0.06, 0.14])
    band = (
        ((v > 0.065) & (v < 0.080))
        | ((v > 0.092) & (v < 0.118))
        | ((v > 0.128) & (v < 0.140))
    ).astype(np.float32)
    band_rib = band * (0.5 + 0.5 * np.sin(u * 48.0 * math.tau))

    base = _rgb_vec('#f3f1ea')
    shade = _rgb_vec('#dfdacf')
    mix = np.clip(0.25 * (1.0 - terry) + 0.25 * slub + 0.14 * band_rib, 0.0, 0.55)[..., None]
    rgb = np.clip(base * (1.0 - mix) + shade * mix, 0.0, 1.0)

    h = 0.5 + terry * 0.18 + (slub - 0.5) * 0.08 + band_rib * 0.14
    nrm = _height_to_normal(h, strength=2.4)

    alb_img = pack_image(name, rgb, colorspace='sRGB')
    nrm_img = pack_image(f'{name}_nrm', nrm, colorspace='Non-Color')
    return alb_img, nrm_img


def tex_fabric_weave(size=256, name='tex_fabric_weave', color='#3f5a78', contrast=0.06):
    """Fine woven cloth micro-grain for street clothes, abayas, and upholstered seats."""
    u, v = _uv_grid(size)
    c = float(contrast)
    base = _rgb_vec(color)

    # Twill / plain weave pattern + gentle organic mottling
    twill = np.sin((u * 64.0 + v * 64.0) * math.tau) * 0.5 + np.sin(u * 64.0 * math.tau) * np.cos(v * 64.0 * math.tau) * 0.5
    mottle = _tileable_fbm(size, base_freq=6, octaves=3, persistence=0.5, seed=421) - 0.5

    delta = (twill * c + mottle * c * 1.1)[..., None]
    rgb = np.clip(base + delta, 0.0, 1.0).astype(np.float32)
    return pack_image(name, rgb, colorspace='sRGB')


# ------------------------------------------------------------------ architectural surfaces
def tex_wood_oak(size=512, name='tex_wood_oak', planks=6, tint='#a87849'):
    """Realistic warm oak floorboards/furniture wood grain with plank seams & knots."""
    u, v = _uv_grid(size)
    planks = max(1, int(planks))
    base = _rgb_vec(tint)
    dark = base * np.array([0.62, 0.56, 0.50], dtype=np.float32)
    light = np.clip(base * np.array([1.16, 1.12, 1.06], dtype=np.float32), 0.0, 1.0)

    # Plank index along V (horizontal planks along U)
    pv = (v * planks) % 1.0
    p_idx = np.floor(v * planks).astype(np.int32)
    # Staggered vertical end joints per plank row
    pu_shift = (u + (p_idx % 2) * 0.5 + (p_idx * 0.23) % 1.0) % 1.0

    # Per-plank tone shift
    phash = np.sin(p_idx * 41.23 + 3.7) * 43758.5453
    pvar = (phash - np.floor(phash) - 0.5) * 0.10

    # Longitudinal wood rings warped by fBM + subtle knots
    warp = _tileable_fbm(size, base_freq=4, octaves=4, persistence=0.52, seed=503)
    fine = _tileable_fbm(size, base_freq=18, octaves=3, persistence=0.5, seed=509)

    ring_coord = (v * planks * 4.5 + p_idx * 1.7 + warp * 2.8) * math.tau
    rings = 0.5 + 0.5 * np.sin(ring_coord)
    rings = np.power(rings, 0.75)

    # Two subtle organic knots
    knot_mask = np.zeros((size, size), dtype=np.float32)
    for ku, kv, kr in ((0.28, 0.35, 0.032), (0.74, 0.72, 0.028)):
        du = ((u - ku + 0.5) % 1.0) - 0.5
        dv = ((v - kv + 0.5) % 1.0) - 0.5
        d = np.hypot(du * 0.7, dv * 2.4)
        knot_mask = np.maximum(knot_mask, np.exp(-((d / kr) ** 2)) * 0.65)

    # Plank seams
    seam_h = 1.0 - _smoothstep_np(0.008, 0.022, np.minimum(pv, 1.0 - pv))
    seam_v = 1.0 - _smoothstep_np(0.003, 0.009, np.minimum(pu_shift, 1.0 - pu_shift))
    seam = np.maximum(seam_h, seam_v * 0.85)

    grain_t = np.clip(rings * 0.65 + fine * 0.35, 0.0, 1.0)
    rgb = dark * (1.0 - grain_t[..., None]) + light * grain_t[..., None]
    rgb += pvar[..., None]
    rgb = rgb * (1.0 - knot_mask[..., None] * 0.55)
    rgb = rgb * (1.0 - seam[..., None] * 0.68)
    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)

    h = 0.65 + rings * 0.06 + (fine - 0.5) * 0.04 - seam * 0.36 - knot_mask * 0.08
    nrm = _height_to_normal(h, strength=2.8)

    alb_img = pack_image(name, rgb, colorspace='sRGB')
    nrm_img = pack_image(f'{name}_nrm', nrm, colorspace='Non-Color')
    return alb_img, nrm_img


def tex_plaster_wall(size=512, name='tex_plaster_wall', tint='#efe1c6'):
    """Warm subtle stucco/plaster wall micro-variation."""
    base = _rgb_vec(tint)
    broad = _tileable_fbm(size, base_freq=4, octaves=4, persistence=0.55, seed=601) - 0.5
    fine = _tileable_fbm(size, base_freq=24, octaves=3, persistence=0.5, seed=607) - 0.5
    var = (broad * 0.07 + fine * 0.035)[..., None]
    rgb = np.clip(base + var, 0.0, 1.0).astype(np.float32)
    return pack_image(name, rgb, colorspace='sRGB')


def tex_persian_rug(size=512, name='tex_persian_rug'):
    """Rich crimson, deep navy, and warm gold geometric Islamic medallion rug."""
    u, v = _uv_grid(size)
    crimson = _rgb_vec('#7f1f24')
    crimson_hi = _rgb_vec('#9c2b2e')
    navy = _rgb_vec('#172640')
    gold = _rgb_vec('#d4a74a')
    cream = _rgb_vec('#e9dcc2')

    # Symmetry coordinates relative to center (0.5, 0.5)
    dx = np.abs(u - 0.5) * 2.0  # 0 at center .. 1 at edge
    dy = np.abs(v - 0.5) * 2.0
    edge = np.maximum(dx, dy)

    # Woven carpet pile micro-grain
    pile = 0.92 + 0.08 * np.sin(u * 160.0 * math.tau) * np.cos(v * 160.0 * math.tau)
    noise = _tileable_fbm(size, base_freq=12, octaves=3, persistence=0.5, seed=701)

    rgb = np.ones((size, size, 3), dtype=np.float32) * crimson
    # Subtle inner field geometric floral diamond trellis
    trellis = (np.abs(np.sin((u + v) * 14.0 * math.tau)) < 0.09) | (np.abs(np.sin((u - v) * 14.0 * math.tau)) < 0.09)
    rgb = np.where(trellis[..., None], crimson_hi, rgb)

    # Concentric rectangular borders
    b_outer_navy = (edge >= 0.80) & (edge <= 0.94)
    b_gold_guard = ((edge >= 0.76) & (edge < 0.80)) | ((edge > 0.94) & (edge <= 0.97))
    b_cream_pin = (np.abs(edge - 0.78) < 0.008) | (np.abs(edge - 0.955) < 0.008)
    rgb = np.where(b_outer_navy[..., None], navy, rgb)
    rgb = np.where(b_gold_guard[..., None], gold, rgb)
    rgb = np.where(b_cream_pin[..., None], cream, rgb)

    # Repeating geometric star motifs inside the navy border
    b_pat = b_outer_navy & (
        (np.sin(u * 24.0 * math.tau) * np.sin(v * 24.0 * math.tau)) > 0.35
    )
    rgb = np.where(b_pat[..., None], gold, rgb)

    # Corner spandrels
    corner_d = (1.0 - dx) + (1.0 - dy)
    spandrel = (edge < 0.76) & (corner_d < 0.48)
    spandrel_rim = (edge < 0.76) & (corner_d >= 0.44) & (corner_d < 0.48)
    rgb = np.where(spandrel[..., None], navy, rgb)
    rgb = np.where(spandrel_rim[..., None], gold, rgb)

    # Central stepped diamond / 8-point Islamic medallion
    rad = np.hypot(dx * 1.15, dy * 0.95)
    ang = np.arctan2(dy, dx)
    star_r = 0.40 + 0.065 * np.cos(8.0 * ang)
    med_outer = rad < star_r
    med_gold = (rad >= star_r - 0.035) & (rad < star_r)
    med_inner_star = rad < (0.22 + 0.04 * np.cos(8.0 * ang + math.pi / 8.0))
    med_core = rad < 0.09

    rgb = np.where(med_outer[..., None], navy, rgb)
    rgb = np.where(med_gold[..., None], gold, rgb)
    rgb = np.where(med_inner_star[..., None], crimson_hi, rgb)
    rgb = np.where(med_core[..., None], cream, rgb)

    # Subtle gold filigree dots in medallion
    med_fil = med_outer & (~med_inner_star) & (np.abs(np.cos(16.0 * ang)) > 0.82) & (rad > 0.25) & (rad < star_r - 0.05)
    rgb = np.where(med_fil[..., None], gold, rgb)

    rgb = rgb * pile[..., None] * (0.94 + 0.12 * noise[..., None])
    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    return pack_image(name, rgb, colorspace='sRGB')


def tex_terrazzo(size=512, name='tex_terrazzo', tint='#e6eaee'):
    """Modern airport polished light terrazzo floor with aggregate flecks & expansion grid."""
    u, v = _uv_grid(size)
    base = _rgb_vec(tint)
    mottle = _tileable_fbm(size, base_freq=6, octaves=3, persistence=0.5, seed=801) - 0.5
    rgb = np.ones((size, size, 3), dtype=np.float32) * base + mottle[..., None] * 0.035

    # Scatter deterministic polished mineral aggregate chips (warm grey, slate, sand, white)
    rng = np.random.default_rng(809)
    chip_colors = [
        _rgb_vec('#8f959c'),
        _rgb_vec('#b8b0a2'),
        _rgb_vec('#666d75'),
        _rgb_vec('#f7f8fa'),
        _rgb_vec('#c7bba9'),
    ]
    n_chips = 420
    cx = rng.random(n_chips).astype(np.float32)
    cy = rng.random(n_chips).astype(np.float32)
    cr = rng.uniform(0.004, 0.014, n_chips).astype(np.float32)
    ca = rng.uniform(0.6, 1.5, n_chips).astype(np.float32)
    cidx = rng.integers(0, len(chip_colors), n_chips)

    # Fast local bounding-box stamping (seamless wrap)
    for i in range(n_chips):
        r_px = max(2, int(cr[i] * size * 1.6))
        px = int(cx[i] * size)
        py = int(cy[i] * size)
        ys = (np.arange(py - r_px, py + r_px + 1) % size)
        xs = (np.arange(px - r_px, px + r_px + 1) % size)
        yy, xx = np.meshgrid(ys, xs, indexing='ij')
        du = ((xx / size - cx[i] + 0.5) % 1.0) - 0.5
        dv = ((yy / size - cy[i] + 0.5) % 1.0) - 0.5
        dist = np.hypot(du * ca[i], dv / ca[i])
        mask = dist < cr[i]
        rgb[yy[mask], xx[mask]] = chip_colors[cidx[i]]

    # Fine metallic expansion joint grid (2x2 slabs)
    tu = (u * 2.0) % 1.0
    tv = (v * 2.0) % 1.0
    dist_edge = np.minimum(np.minimum(tu, 1.0 - tu), np.minimum(tv, 1.0 - tv))
    joint = 1.0 - _smoothstep_np(0.0025, 0.007, dist_edge)
    joint_col = _rgb_vec('#9fa6ad')
    rgb = rgb * (1.0 - joint[..., None] * 0.7) + joint_col * (joint[..., None] * 0.7)
    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    return pack_image(name, rgb, colorspace='sRGB')


def tex_stone_haram(size=512, name='tex_stone_haram', tint='#ece4d5'):
    """Warm dressed limestone/marble ashlar blocks for Haram facades, minarets & Makkah hotel."""
    u, v = _uv_grid(size)
    base = _rgb_vec(tint)
    grout_col = base * np.array([0.74, 0.71, 0.66], dtype=np.float32)

    rows = 8
    cols = 4
    rv = (v * rows) % 1.0
    r_idx = np.floor(v * rows).astype(np.int32)
    su = (u * cols + (r_idx % 2) * 0.5) % 1.0
    c_idx = np.floor((u * cols + (r_idx % 2) * 0.5) % cols).astype(np.int32)

    # Per-block warm/cool limestone tone shift
    bhash = np.sin(r_idx * 37.1 + c_idx * 91.7 + 1.3) * 43758.5453
    bvar = (bhash - np.floor(bhash) - 0.5) * 0.065

    grain = _tileable_fbm(size, base_freq=8, octaves=4, persistence=0.55, seed=901) - 0.5
    fine = _tileable_fbm(size, base_freq=28, octaves=3, persistence=0.5, seed=907) - 0.5

    mortar_h = 1.0 - _smoothstep_np(0.018, 0.042, np.minimum(rv, 1.0 - rv))
    mortar_v = 1.0 - _smoothstep_np(0.009, 0.022, np.minimum(su, 1.0 - su))
    mortar = np.maximum(mortar_h, mortar_v)

    rgb = np.ones((size, size, 3), dtype=np.float32) * base
    rgb += bvar[..., None] + grain[..., None] * 0.06 + fine[..., None] * 0.03
    rgb = rgb * (1.0 - mortar[..., None] * 0.65) + grout_col * (mortar[..., None] * 0.65)
    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    return pack_image(name, rgb, colorspace='sRGB')


def tex_granite_rock(size=512, name='tex_granite_rock'):
    """Dark grey-brown speckled Hijazi granite/basalt rock for Safa & Marwa hills."""
    broad = _tileable_fbm(size, base_freq=4, octaves=5, persistence=0.58, seed=1009)
    cracks = _tileable_fbm(size, base_freq=9, octaves=4, persistence=0.55, seed=1013)
    speck = _tileable_fbm(size, base_freq=48, octaves=2, persistence=0.6, seed=1019)

    dark_basalt = _rgb_vec('#36312d')
    warm_granite = _rgb_vec('#6a5d52')
    quartz_fleck = _rgb_vec('#9c9184')

    # Sharp dark fissure creases
    fissure = np.power(1.0 - np.abs(cracks * 2.0 - 1.0), 8.0)

    t = np.clip(broad * 0.75 + (speck - 0.5) * 0.35, 0.0, 1.0)[..., None]
    rgb = dark_basalt * (1.0 - t) + warm_granite * t
    fleck_m = _smoothstep_np(0.68, 0.85, speck)[..., None]
    rgb = rgb * (1.0 - fleck_m * 0.35) + quartz_fleck * (fleck_m * 0.35)
    rgb *= (1.0 - fissure[..., None] * 0.48)
    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)

    h = 0.55 + (broad - 0.5) * 0.45 + (speck - 0.5) * 0.14 - fissure * 0.38
    nrm = _height_to_normal(h, strength=4.2)

    alb_img = pack_image(name, rgb, colorspace='sRGB')
    nrm_img = pack_image(f'{name}_nrm', nrm, colorspace='Non-Color')
    return alb_img, nrm_img


def tex_gold_relief(size=512, name='tex_gold_relief'):
    """Brushed warm antique gold with Islamic 8-point star/octagram geometric relief bump."""
    u, v = _uv_grid(size)
    cells = 4
    cu = ((u * cells) % 1.0) - 0.5
    cv = ((v * cells) % 1.0) - 0.5

    # 8-point Islamic star (Rub el Hizb): union of axis-aligned square + 45-deg rotated square
    sq1 = np.maximum(np.abs(cu), np.abs(cv))
    ru = (cu + cv) * 0.70710678
    rv = (cu - cv) * 0.70710678
    sq2 = np.maximum(np.abs(ru), np.abs(rv))
    octagram = np.minimum(sq1, sq2)

    star_ring = (np.abs(octagram - 0.32) < 0.032) | (np.abs(octagram - 0.18) < 0.022)
    center_rosette = np.hypot(cu, cv) < 0.075
    corner_link = (np.abs(np.abs(cu) - 0.5) < 0.025) | (np.abs(np.abs(cv) - 0.5) < 0.025)
    relief = (star_ring | center_rosette | corner_link).astype(np.float32)

    # Brushed antique gold streaks + gentle patina
    brush = _tileable_fbm(size, base_freq=32, octaves=2, persistence=0.5, seed=1103)
    patina = _tileable_fbm(size, base_freq=6, octaves=3, persistence=0.5, seed=1109)
    brush_line = 0.5 + 0.5 * np.sin(u * 180.0 * math.tau + brush * 2.0)

    gold_recess = _rgb_vec('#8f6820')
    gold_mid = _rgb_vec('#cfa13e')
    gold_hi = _rgb_vec('#f2d06b')

    rgb = gold_recess * (1.0 - patina[..., None] * 0.5) + gold_mid * (patina[..., None] * 0.5)
    rgb = rgb * (1.0 - relief[..., None]) + (gold_mid * 0.4 + gold_hi * 0.6) * relief[..., None]
    rgb *= (0.92 + 0.12 * brush_line[..., None])
    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)

    h = 0.35 + relief * 0.45 + brush_line * 0.03 + (patina - 0.5) * 0.05
    nrm = _height_to_normal(h, strength=3.2)

    alb_img = pack_image(name, rgb, colorspace='sRGB')
    nrm_img = pack_image(f'{name}_nrm', nrm, colorspace='Non-Color')
    return alb_img, nrm_img
