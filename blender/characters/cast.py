"""Character cast specifications, builder orchestrator, and GLB exporter for umrah-journey.

Builds & exports:
- player.glb    (~1.76 m, <= 14k tris, <= 450 KB)
- mentor.glb    (~1.72 m, <= 14k tris, <= 450 KB)
- attendant.glb (~1.65 m, <= 8k tris,  <= 260 KB)
- guide.glb     (~1.75 m, <= 8k tris,  <= 260 KB)
- agent.glb     (~1.74 m, <= 7.5k tris, <= 240 KB)
"""
import sys

from blender.characters import anim as anim_mod
from blender.characters import body as body_mod
from blender.characters import garments as garm_mod
from blender.characters import rig as rig_mod
from blender.lib import textures
from blender.lib.common import (
    MODELS_CHAR,
    bone_count,
    ensure_dirs,
    export_glb,
    make_collection,
    make_pbr_material,
    reset_scene,
    tri_count,
)

sys.dont_write_bytecode = True

SPECS = {
    'player': {
        'height': 1.76,
        'head_ratio': 7.3,
        'shoulder_w': 0.114,
        'torso_w_ratio': 0.86,
        'waist_w': 0.082,
        'pelvis_w': 0.094,
        'chest_d': 0.068,
        'waist_d': 0.058,
        'pelvis_d': 0.066,
        'female': False,
        'beard': False,
        'skin': '#cfa181',
        'hair': '#261e1a',
        'shirt': '#3c6e99',
        'trousers': '#353b47',
        'shoe': '#2f2c29',
        'sole': '#d8d5ce',
        'belt': '#362a20',
        'ihram_belt': '#3a3834',
        'sandal_leather': '#6b472b',
        'sandal_sole': '#2c221b',
        'clips': ['idle', 'walk', 'run', 'talk', 'gesture', 'pray'],
        'style': {'energy': 1.0, 'stoop': 0.0, 'arm_out': 0.14, 'elbow': 15.0},
        'max_tris': 14000,
        'max_kb': 450,
        'expected_meshes': [
            'body_skin',
            'hair',
            'outfit_street',
            'outfit_ihram_izar',
            'outfit_ihram_rida_covered',
            'outfit_ihram_rida_idtiba',
        ],
    },
    'mentor': {
        'height': 1.72,
        'head_ratio': 7.2,
        'shoulder_w': 0.116,
        'torso_w_ratio': 0.89,
        'waist_w': 0.091,
        'pelvis_w': 0.098,
        'chest_d': 0.072,
        'waist_d': 0.067,
        'pelvis_d': 0.070,
        'female': False,
        'beard': True,
        'skin': '#c08f6e',
        'hair': '#9aa0a8',
        'beard_col': '#a7adb5',
        'shirt': '#c9b48a',
        'trousers': '#5c503e',
        'shoe': '#4a3525',
        'sole': '#261d17',
        'belt': '#3d2c1e',
        'ihram_belt': '#3e3a34',
        'sandal_leather': '#634128',
        'sandal_sole': '#292019',
        'clips': ['idle', 'walk', 'run', 'talk', 'gesture', 'pray'],
        'style': {'energy': 0.82, 'stoop': 3.2, 'arm_out': 0.15, 'elbow': 18.0},
        'max_tris': 14000,
        'max_kb': 450,
        'expected_meshes': [
            'body_skin',
            'hair',
            'outfit_street',
            'outfit_ihram_izar',
            'outfit_ihram_rida_covered',
            'outfit_ihram_rida_idtiba',
        ],
    },
    'attendant': {
        'height': 1.65,
        'head_ratio': 7.25,
        'shoulder_w': 0.100,
        'torso_w_ratio': 0.84,
        'waist_w': 0.073,
        'pelvis_w': 0.095,
        'chest_d': 0.064,
        'waist_d': 0.053,
        'pelvis_d': 0.067,
        'female': True,
        'skin': '#d4aa8c',
        'burgundy': '#6e2330',
        'cream': '#f0e4ce',
        'gold': '#d4a843',
        'shoe': '#231f20',
        'sole': '#191718',
        'clips': ['idle', 'talk'],
        'style': {'energy': 0.90, 'stoop': 0.0, 'arm_out': 0.13, 'elbow': 18.0},
        'max_tris': 8000,
        'max_kb': 260,
        'expected_meshes': ['body_skin', 'hijab', 'outfit_uniform'],
    },
    'guide': {
        'height': 1.75,
        'head_ratio': 7.3,
        'shoulder_w': 0.114,
        'torso_w_ratio': 0.87,
        'waist_w': 0.084,
        'pelvis_w': 0.095,
        'chest_d': 0.069,
        'waist_d': 0.060,
        'pelvis_d': 0.066,
        'female': False,
        'skin': '#c89979',
        'hair': '#231d19',
        'blazer': '#1f3049',
        'white': '#f2f2ee',
        'gold': '#d4a843',
        'trousers': '#252c38',
        'shoe': '#221d1a',
        'sole': '#171412',
        'belt': '#241c16',
        'clips': ['idle', 'talk'],
        'style': {'energy': 0.92, 'stoop': 0.0, 'arm_out': 0.14, 'elbow': 16.0},
        'max_tris': 8000,
        'max_kb': 260,
        'expected_meshes': ['body_skin', 'hair', 'outfit_uniform'],
    },
    'agent': {
        'height': 1.74,
        'head_ratio': 7.3,
        'shoulder_w': 0.113,
        'torso_w_ratio': 0.86,
        'waist_w': 0.083,
        'pelvis_w': 0.094,
        'chest_d': 0.068,
        'waist_d': 0.059,
        'pelvis_d': 0.065,
        'female': False,
        'skin': '#d2a687',
        'hair': '#2a221d',
        'shirt': '#254066',
        'tie': '#16243a',
        'badge': '#e9edf2',
        'trousers': '#272d38',
        'shoe': '#221f1e',
        'sole': '#161413',
        'belt': '#221b16',
        'clips': ['idle', 'talk'],
        'style': {'energy': 0.90, 'stoop': 0.0, 'arm_out': 0.14, 'elbow': 16.0},
        'max_tris': 7500,
        'max_kb': 240,
        'expected_meshes': ['body_skin', 'hair', 'outfit_uniform'],
    },
}


def build_character(key, col=None):
    """Build a single rigged & animated character in the current Blender scene.

    Returns (armature_obj, dict_of_mesh_objs, landmarks).
    """
    spec = SPECS[key]
    if col is None:
        col = make_collection(f'Char_{key}')

    lm = rig_mod.compute_landmarks(spec)
    arm = rig_mod.build_armature(f'rig_{key}', col, lm)

    mat_skin = make_pbr_material(f'{key}_skin', color=spec['skin'], roughness=0.58)
    female = bool(spec.get('female', False))

    # For player & mentor, keep complete anatomical body_skin (bare shoulders, torso, arms, legs, feet)
    # so idtiba' bare right shoulder & sandals look completely seamless.
    # For clothed NPCs, skip hidden legs inside skirt/trousers only if needed; here body_skin is lean
    # (~2.5k tris) so full body or torso+arms+head keeps us well under 7.5k tris!
    is_hero = key in ('player', 'mentor')
    body_obj = body_mod.build_body_skin(
        'body_skin',
        col,
        lm,
        mat_skin,
        female=female,
        include_legs=is_hero,
        include_torso=is_hero,
    )
    rig_mod.skin_body(body_obj, arm, lm)
    rig_mod.validate_skinning(body_obj, arm)

    meshes = {'body_skin': body_obj}

    if is_hero:
        # Shared woven white cotton terry ihram material (1 packed 512px albedo + normal map!)
        ihram_alb, ihram_nrm = textures.tex_cotton_ihram(size=512, name=f'{key}_ihram_tex')
        mat_ihram = make_pbr_material(
            f'{key}_ihram',
            color='#f3f1ea',
            roughness=0.88,
            image=ihram_alb,
            normal_image=ihram_nrm,
            normal_strength=0.45,
            double_sided=True,
            uv_scale=(2.0, 2.0),
        )
        shirt_tex = textures.tex_fabric_weave(size=256, name=f'{key}_shirt_tex', color=spec['shirt'], contrast=0.05)
        trouser_tex = textures.tex_fabric_weave(size=256, name=f'{key}_tr_tex', color=spec['trousers'], contrast=0.04)

        mat_hair = make_pbr_material(f'{key}_hair', color=spec['hair'], roughness=0.64)
        mat_beard = (
            make_pbr_material(f'{key}_beard', color=spec['beard_col'], roughness=0.68)
            if spec.get('beard')
            else None
        )
        mat_shirt = make_pbr_material(f'{key}_shirt', color=spec['shirt'], roughness=0.82, image=shirt_tex, uv_scale=(2.5, 2.5))
        mat_trousers = make_pbr_material(f'{key}_trousers', color=spec['trousers'], roughness=0.84, image=trouser_tex, uv_scale=(2.5, 2.5))
        mat_shoe = make_pbr_material(f'{key}_shoe', color=spec['shoe'], roughness=0.52)
        mat_sole = make_pbr_material(f'{key}_sole', color=spec['sole'], roughness=0.78)
        mat_belt = make_pbr_material(f'{key}_belt', color=spec['belt'], roughness=0.48)
        mat_ibelt = make_pbr_material(f'{key}_ibelt', color=spec['ihram_belt'], roughness=0.76)
        mat_s_leath = make_pbr_material(f'{key}_sandal_l', color=spec['sandal_leather'], roughness=0.54)
        mat_s_sole = make_pbr_material(f'{key}_sandal_s', color=spec['sandal_sole'], roughness=0.75)

        hair_obj = garm_mod.build_short_hair('hair', col, lm, mat_hair, beard=bool(spec.get('beard')), mat_beard=mat_beard)
        rig_mod.skin_headwear(hair_obj, arm, lm, drape_shoulders=False)
        rig_mod.validate_skinning(hair_obj, arm)
        meshes['hair'] = hair_obj

        meshes['outfit_street'] = garm_mod.build_street_outfit(
            'outfit_street', col, lm, arm, mat_shirt, mat_trousers, mat_shoe, mat_sole, mat_belt
        )
        meshes['outfit_ihram_izar'] = garm_mod.build_ihram_izar(
            'outfit_ihram_izar', col, lm, arm, mat_ihram, mat_s_leath, mat_s_sole, mat_ibelt
        )
        meshes['outfit_ihram_rida_covered'] = garm_mod.build_ihram_rida_covered(
            'outfit_ihram_rida_covered', col, lm, arm, mat_ihram
        )
        meshes['outfit_ihram_rida_idtiba'] = garm_mod.build_ihram_rida_idtiba(
            'outfit_ihram_rida_idtiba', col, lm, arm, mat_ihram
        )

    elif key == 'attendant':
        burg_tex = textures.tex_fabric_weave(size=256, name='att_burg_tex', color=spec['burgundy'], contrast=0.045)
        mat_burg = make_pbr_material('att_burgundy', color=spec['burgundy'], roughness=0.76, image=burg_tex, double_sided=True, uv_scale=(2.5, 2.5))
        mat_cream = make_pbr_material('att_cream', color=spec['cream'], roughness=0.62)
        mat_gold = make_pbr_material('att_gold', color=spec['gold'], roughness=0.28, metallic=0.88)
        mat_shoe = make_pbr_material('att_shoe', color=spec['shoe'], roughness=0.40)
        mat_sole = make_pbr_material('att_sole', color=spec['sole'], roughness=0.70)

        hijab_obj, uniform_obj = garm_mod.build_attendant_outfit(
            col, lm, arm, mat_burg, mat_cream, mat_gold, mat_shoe, mat_sole
        )
        meshes['hijab'] = hijab_obj
        meshes['outfit_uniform'] = uniform_obj

    elif key == 'guide':
        blz_tex = textures.tex_fabric_weave(size=256, name='guide_blz_tex', color=spec['blazer'], contrast=0.04)
        mat_hair = make_pbr_material('guide_hair', color=spec['hair'], roughness=0.62)
        mat_blazer = make_pbr_material('guide_blazer', color=spec['blazer'], roughness=0.76, image=blz_tex, uv_scale=(2.5, 2.5))
        mat_white = make_pbr_material('guide_white', color=spec['white'], roughness=0.72)
        mat_gold = make_pbr_material('guide_gold', color=spec['gold'], roughness=0.26, metallic=0.88)
        mat_tr = make_pbr_material('guide_trousers', color=spec['trousers'], roughness=0.80)
        mat_shoe = make_pbr_material('guide_shoe', color=spec['shoe'], roughness=0.36)
        mat_sole = make_pbr_material('guide_sole', color=spec['sole'], roughness=0.70)
        mat_belt = make_pbr_material('guide_belt', color=spec['belt'], roughness=0.42)

        hair_obj = garm_mod.build_short_hair('hair', col, lm, mat_hair, beard=False)
        rig_mod.skin_headwear(hair_obj, arm, lm, drape_shoulders=False)
        rig_mod.validate_skinning(hair_obj, arm)
        meshes['hair'] = hair_obj
        meshes['outfit_uniform'] = garm_mod.build_guide_outfit(
            col, lm, arm, mat_blazer, mat_white, mat_gold, mat_tr, mat_shoe, mat_sole, mat_belt
        )

    elif key == 'agent':
        sh_tex = textures.tex_fabric_weave(size=256, name='agent_sh_tex', color=spec['shirt'], contrast=0.04)
        mat_hair = make_pbr_material('agent_hair', color=spec['hair'], roughness=0.62)
        mat_shirt = make_pbr_material('agent_shirt', color=spec['shirt'], roughness=0.76, image=sh_tex, uv_scale=(2.5, 2.5))
        mat_tie = make_pbr_material('agent_tie', color=spec['tie'], roughness=0.58)
        mat_badge = make_pbr_material('agent_badge', color=spec['badge'], roughness=0.35, metallic=0.10)
        mat_tr = make_pbr_material('agent_trousers', color=spec['trousers'], roughness=0.82)
        mat_shoe = make_pbr_material('agent_shoe', color=spec['shoe'], roughness=0.38)
        mat_sole = make_pbr_material('agent_sole', color=spec['sole'], roughness=0.70)
        mat_belt = make_pbr_material('agent_belt', color=spec['belt'], roughness=0.44)

        hair_obj = garm_mod.build_short_hair('hair', col, lm, mat_hair, beard=False)
        rig_mod.skin_headwear(hair_obj, arm, lm, drape_shoulders=False)
        rig_mod.validate_skinning(hair_obj, arm)
        meshes['hair'] = hair_obj
        meshes['outfit_uniform'] = garm_mod.build_agent_outfit(
            col, lm, arm, mat_shirt, mat_tie, mat_badge, mat_tr, mat_shoe, mat_sole, mat_belt
        )

    # Generate 24 fps NLA animation clips
    anim_mod.animate(arm, key, spec['clips'], style=spec['style'])
    return arm, meshes, lm


def export_character(key):
    """Reset scene, build character `key`, export GLB, and return metrics dict."""
    ensure_dirs()
    reset_scene()
    arm, meshes, lm = build_character(key)

    export_objs = [arm] + list(meshes.values())
    out_path = MODELS_CHAR / f'{key}.glb'
    size_bytes = export_glb(export_objs, out_path, animations=True, draco_level=6, image_format='WEBP', image_quality=82)

    tris_by_mesh = {name: tri_count(obj) for name, obj in meshes.items()}
    total_tris = sum(tris_by_mesh.values())
    return {
        'key': key,
        'path': str(out_path),
        'bones': bone_count(arm),
        'tris': total_tris,
        'tris_by_mesh': tris_by_mesh,
        'size_bytes': size_bytes,
        'size_kb': round(size_bytes / 1024.0, 2),
        'clips': list(SPECS[key]['clips']),
        'expected_meshes': list(SPECS[key]['expected_meshes']),
        'max_tris': SPECS[key]['max_tris'],
        'max_kb': SPECS[key]['max_kb'],
    }
