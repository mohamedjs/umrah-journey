"""Standalone CLI builder for all realistic faceless characters and crowd archetypes.

Usage:
    blender -b -P blender/characters/build_all.py
    blender -b -P blender/characters/build_all.py -- player mentor crowd

Exports all 6 GLBs to `public/models/characters/`, verifies every GLB binary JSON chunk
(exact mesh names, animation clip names, Draco compression, size & tri budgets),
writes `blender/_report_characters.json`, and renders inspection preview PNGs to
`blender/previews/chars_*.png`.
"""
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bmesh
import bpy
from mathutils import Vector

from blender.characters import anim as anim_mod
from blender.characters import cast, crowd
from blender.lib import preview
from blender.lib.common import (
    PREVIEWS,
    add_box,
    bm_to_obj,
    ensure_dirs,
    make_collection,
    make_pbr_material,
    reset_scene,
    save_report,
    srgb_to_linear,
)

sys.dont_write_bytecode = True

ALL_KEYS = ['player', 'mentor', 'attendant', 'guide', 'agent', 'crowd']


def inspect_glb(path):
    """Parse GLB binary header & JSON chunk and return verification summary."""
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError(f'GLB too small: {path}')
    magic, version, length = struct.unpack('<4sII', raw[:12])
    if magic != b'glTF' or version != 2:
        raise ValueError(f'Invalid GLB header in {path}: {magic!r} v{version}')
    chunk_len, chunk_type = struct.unpack('<II', raw[12:20])
    if chunk_type != 0x4E4F534A:  # JSON
        raise ValueError(f'First GLB chunk not JSON in {path}')
    gltf = json.loads(raw[20:20 + chunk_len].decode('utf-8'))

    nodes = [n.get('name', '') for n in gltf.get('nodes', [])]
    meshes = [m.get('name', '') for m in gltf.get('meshes', [])]
    anims = []
    for a in gltf.get('animations', []):
        anims.append({
            'name': a.get('name', ''),
            'channels': len(a.get('channels', [])),
            'samplers': len(a.get('samplers', [])),
        })
    exts = gltf.get('extensionsUsed', [])
    images = [im.get('mimeType', '') for im in gltf.get('images', [])]
    return {
        'nodes': nodes,
        'meshes': meshes,
        'animations': anims,
        'extensions': exts,
        'images': images,
        'draco': 'KHR_draco_mesh_compression' in exts,
    }


def verify_entry(entry):
    """Verify exported GLB satisfies exact contract: meshes, clips, Draco, tris & KB budgets."""
    info = inspect_glb(entry['path'])
    entry['glb_check'] = {
        'draco': info['draco'],
        'mesh_names': info['meshes'],
        'animations': info['animations'],
        'images': info['images'],
    }
    errors = []
    if not info['draco']:
        errors.append('Missing KHR_draco_mesh_compression')

    present_names = set(info['nodes']) | set(info['meshes'])
    missing_meshes = [m for m in entry['expected_meshes'] if m not in present_names]
    if missing_meshes:
        errors.append(f'Missing meshes: {missing_meshes}')

    anim_map = {a['name']: a['channels'] for a in info['animations']}
    for clip in entry['clips']:
        if clip not in anim_map:
            errors.append(f'Missing animation clip: {clip} (found: {list(anim_map.keys())})')
        elif anim_map[clip] == 0:
            errors.append(f'Animation clip {clip} has 0 channels')

    if entry['tris'] > entry['max_tris']:
        errors.append(f"Tri budget exceeded: {entry['tris']} > {entry['max_tris']}")
    if entry['size_kb'] > entry['max_kb']:
        errors.append(f"Size budget exceeded: {entry['size_kb']} KB > {entry['max_kb']} KB")

    entry['errors'] = errors
    return errors


def _add_studio_floor(col, size=10.0):
    bm = bmesh.new()
    add_box(bm, (0.0, 0.0, -0.025), (size, size, 0.05))
    mat = make_pbr_material('_StudioFloorMat', color='#d8d3c8', roughness=0.78)
    return bm_to_obj(bm, '_StudioFloor', col, mat=mat, smooth=False)


def _set_visible_outfit(meshes, visible_names):
    vis = set(visible_names)
    for name, obj in meshes.items():
        hide = name not in vis
        obj.hide_viewport = hide
        obj.hide_render = hide


def _apply_clip_frame(arm, clip_name, frame):
    """Apply a specific clip & frame from NLA tracks for crisp pose preview rendering."""
    ad = arm.animation_data
    if not ad:
        return
    target_act = None
    for tr in ad.nla_tracks:
        if tr.name == clip_name and tr.strips:
            target_act = tr.strips[0].action
            tr.mute = False
        else:
            tr.mute = True
    if target_act is not None:
        ad.action = target_act
        if hasattr(ad, 'action_slot') and getattr(target_act, 'slots', None):
            try:
                ad.action_slot = target_act.slots[0]
            except Exception:
                pass
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()


def _rename_char_for_lineup(prefix, arm, meshes):
    """Give armature & child meshes unique names so multiple characters coexist in a preview scene."""
    arm.name = f'{prefix}_{arm.name}'
    for obj in meshes.values():
        obj.name = f'{prefix}_{obj.name}'


def _freeze_pose_meshes(arm, meshes, visible_names):
    """Bake currently evaluated armature pose into static mesh copies so multiple poses coexist cleanly."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    vis = set(visible_names)
    for name, obj in meshes.items():
        if name not in vis:
            obj.hide_viewport = True
            obj.hide_render = True
            continue
        ev = obj.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev)
        wmat = obj.matrix_world.copy()
        obj.modifiers.clear()
        obj.parent = None
        obj.matrix_world = wmat
        old_me = obj.data
        obj.data = me
        bpy.data.meshes.remove(old_me)
    arm.hide_viewport = True
    arm.hide_render = True


def render_previews(keys):
    """Render all inspection preview PNGs to `blender/previews/chars_*.png`."""
    ensure_dirs()
    key_set = set(keys)

    # 1 & 2. Player turntables (ihram idtiba' + street attire)
    if 'player' in key_set:
        reset_scene()
        col = make_collection('PreviewPlayer')
        _add_studio_floor(col, size=6.0)
        arm, meshes, _ = cast.build_character('player', col=col)
        _apply_clip_frame(arm, 'idle', 1)

        _set_visible_outfit(meshes, ['body_skin', 'hair', 'outfit_ihram_izar', 'outfit_ihram_rida_idtiba'])
        vis_objs = [meshes[k] for k in ('body_skin', 'hair', 'outfit_ihram_izar', 'outfit_ihram_rida_idtiba')]
        preview.render_turntable_grid(
            vis_objs,
            PREVIEWS / 'chars_player_ihram_idtiba.png',
            res=(1280, 640),
            views=4,
            lens=48,
        )

        _set_visible_outfit(meshes, ['body_skin', 'hair', 'outfit_street'])
        vis_objs = [meshes[k] for k in ('body_skin', 'hair', 'outfit_street')]
        preview.render_turntable_grid(
            vis_objs,
            PREVIEWS / 'chars_player_street.png',
            res=(1280, 640),
            views=4,
            lens=48,
        )

        # 6. Player action poses lineup: walk, run, gesture, pray (ruku'), pray (sujud) side by side!
        reset_scene()
        col = make_collection('PreviewPoses')
        _add_studio_floor(col, size=12.0)
        pose_specs = [
            ('walk', 7, -2.05),
            ('run', 5, -1.02),
            ('gesture', 18, 0.00),
            ('pray', 34, 1.02),
            ('pray', 70, 2.05),
        ]
        vis_list = ['body_skin', 'hair', 'outfit_ihram_izar', 'outfit_ihram_rida_idtiba']
        for idx, (clip_name, frame, x_off) in enumerate(pose_specs):
            sub_col = make_collection(f'Pose_{idx}')
            p_arm, p_meshes, _ = cast.build_character('player', col=sub_col)
            p_arm.location = Vector((x_off, 0.0, 0.0))
            _apply_clip_frame(p_arm, clip_name, frame)
            _freeze_pose_meshes(p_arm, p_meshes, vis_list)
            _rename_char_for_lineup(f'p{idx}', p_arm, p_meshes)
        bpy.context.view_layer.update()
        preview.render_shot(
            eye=(0.0, -6.2, 1.55),
            target=(0.0, 0.0, 0.85),
            out_path=PREVIEWS / 'chars_poses.png',
            res=(1440, 560),
            lens=42,
        )

    # 3. Mentor turntable (covered ihram)
    if 'mentor' in key_set:
        reset_scene()
        col = make_collection('PreviewMentor')
        _add_studio_floor(col, size=6.0)
        arm, meshes, _ = cast.build_character('mentor', col=col)
        _apply_clip_frame(arm, 'idle', 1)
        _set_visible_outfit(meshes, ['body_skin', 'hair', 'outfit_ihram_izar', 'outfit_ihram_rida_covered'])
        vis_objs = [meshes[k] for k in ('body_skin', 'hair', 'outfit_ihram_izar', 'outfit_ihram_rida_covered')]
        preview.render_turntable_grid(
            vis_objs,
            PREVIEWS / 'chars_mentor_ihram.png',
            res=(1280, 640),
            views=4,
            lens=48,
        )

    # 4. NPC lineup (attendant, guide, agent)
    if any(k in key_set for k in ('attendant', 'guide', 'agent')):
        reset_scene()
        col = make_collection('PreviewNPCs')
        _add_studio_floor(col, size=8.0)
        for npc_key, x_off in (('attendant', -1.05), ('guide', 0.0), ('agent', 1.05)):
            n_col = make_collection(f'NPC_{npc_key}')
            n_arm, n_meshes, _ = cast.build_character(npc_key, col=n_col)
            n_arm.location = Vector((x_off, 0.0, 0.0))
            _apply_clip_frame(n_arm, 'idle', 1)
            _freeze_pose_meshes(n_arm, n_meshes, list(n_meshes.keys()))
            _rename_char_for_lineup(npc_key, n_arm, n_meshes)
        preview.render_shot(
            eye=(0.0, -4.3, 1.32),
            target=(0.0, 0.0, 0.90),
            out_path=PREVIEWS / 'chars_npcs.png',
            res=(1200, 620),
            lens=45,
        )

    # 5. Crowd archetypes lineup (all 6 side by side with temporary tint colors for clear inspection!)
    if 'crowd' in key_set:
        reset_scene()
        col = make_collection('PreviewCrowd')
        _add_studio_floor(col, size=12.0)
        objs = crowd.build_crowd_archetypes(col=col)

        tint_map = {
            'crowd_ihram_idtiba_cloth': '#f4f2ec',
            'crowd_ihram_idtiba_skin': '#c99776',
            'crowd_ihram_covered_cloth': '#f4f2ec',
            'crowd_ihram_covered_skin': '#b88464',
            'crowd_man_street_cloth': '#4a688a',
            'crowd_man_street_skin': '#d4a98a',
            'crowd_woman_abaya_cloth': '#2a2833',
            'crowd_woman_abaya_hijab': '#734454',
            'crowd_woman_abaya_skin': '#d8b093',
            'crowd_seated_man_cloth': '#5e6b58',
            'crowd_seated_man_skin': '#c89878',
            'crowd_seated_woman_cloth': '#2b3240',
            'crowd_seated_woman_hijab': '#c4ae92',
            'crowd_seated_woman_skin': '#d5aa8c',
        }
        groups = [
            (-2.35, ['crowd_ihram_idtiba_cloth', 'crowd_ihram_idtiba_skin']),
            (-1.42, ['crowd_ihram_covered_cloth', 'crowd_ihram_covered_skin']),
            (-0.48, ['crowd_man_street_cloth', 'crowd_man_street_skin']),
            (0.46, ['crowd_woman_abaya_cloth', 'crowd_woman_abaya_hijab', 'crowd_woman_abaya_skin']),
            (1.42, ['crowd_seated_man_cloth', 'crowd_seated_man_skin']),
            (2.38, ['crowd_seated_woman_cloth', 'crowd_seated_woman_hijab', 'crowd_seated_woman_skin']),
        ]
        mat_seat = make_pbr_material('_SeatRef', color='#525a66', roughness=0.7)
        for sx in (1.42, 2.38):
            bm_st = bmesh.new()
            add_box(bm_st, (sx, 0.02, 0.275), (0.46, 0.44, 0.55))
            bm_to_obj(bm_st, f'_Seat_{sx}', col, mat=mat_seat, smooth=False)

        for x_off, names in groups:
            for nm in names:
                o = objs[nm]
                o.location = Vector((x_off, 0.0, 0.0))
                mat_p = make_pbr_material(f'_prev_{nm}', color=tint_map[nm], roughness=0.75, double_sided=True)
                o.data.materials.clear()
                o.data.materials.append(mat_p)

        preview.render_shot(
            eye=(0.0, -7.2, 1.50),
            target=(0.0, 0.0, 0.85),
            out_path=PREVIEWS / 'chars_crowd.png',
            res=(1440, 560),
            lens=42,
        )


def main():
    argv = sys.argv
    if '--' in argv:
        keys = [k for k in argv[argv.index('--') + 1:] if k in ALL_KEYS]
    else:
        keys = list(ALL_KEYS)
    if not keys:
        keys = list(ALL_KEYS)

    report = []
    all_errors = []

    for key in keys:
        print(f'=== Building character: {key} ===')
        if key == 'crowd':
            entry = crowd.export_crowd()
        else:
            entry = cast.export_character(key)
        errs = verify_entry(entry)
        report.append(entry)
        anim_names = [a['name'] for a in entry['glb_check']['animations']]
        print(
            f"  -> {key}.glb: {entry['tris']} tris (max {entry['max_tris']}), "
            f"{entry['size_kb']} KB (max {entry['max_kb']} KB), "
            f"bones={entry['bones']}, clips={anim_names}, draco={entry['glb_check']['draco']}"
        )
        if errs:
            print(f'  !! ERRORS in {key}: {errs}')
            all_errors.extend([f'{key}: {e}' for e in errs])

    save_report('_report_characters.json', report)
    print('=== Rendering inspection previews ===')
    render_previews(keys)

    if all_errors:
        print('FAILED VERIFICATION:')
        for e in all_errors:
            print('  -', e)
        sys.exit(1)
    print('ALL_CHARACTERS_OK')


if __name__ == '__main__':
    main()
