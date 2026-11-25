"""Realistic 19-bone adult human skeleton and smooth analytical skinning for umrah-journey.

Coordinate convention:
- Blender Z-up, character faces -Y (so character LEFT = +X, character RIGHT = -X).
- Origin (0, 0, 0) on the floor between the feet.
- Strictly 19 deform bones (zero face bones).
- Every vertex receives <= 4 bone weights normalized to 1.0 (zero unskinned vertices).
"""
import math
import sys

import bpy
from mathutils import Vector

from blender.lib.common import smoothstep

sys.dont_write_bytecode = True

BONE_NAMES = (
    'pelvis', 'spine_01', 'spine_02', 'neck', 'head',
    'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l',
    'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r',
    'thigh_l', 'calf_l', 'foot_l',
    'thigh_r', 'calf_r', 'foot_r',
)


def compute_landmarks(spec):
    """Derive realistic adult anatomical landmarks (metres, Z-up, facing -Y).

    Uses realistic adult proportions (head-to-height ratio 1:7.2 to 1:7.4).
    """
    h = float(spec['height'])
    head_ratio = float(spec.get('head_ratio', 7.3))
    head_h = h / head_ratio
    head_w = head_h * float(spec.get('head_w_frac', 0.64))
    head_d = head_h * float(spec.get('head_d_frac', 0.78))
    head_r = head_h * 0.48

    crown_z = h
    chin_z = crown_z - head_h
    head_center_z = chin_z + head_h * 0.54
    neck_top_z = chin_z + head_h * 0.14
    neck_bot_z = chin_z - head_h * float(spec.get('neck_frac', 0.34))

    # Realistic adult torso landmarks
    sh_z = neck_bot_z - head_h * float(spec.get('sh_drop_frac', 0.14))
    hip_z = h * float(spec.get('hip_frac', 0.515))
    waist_z = hip_z + (sh_z - hip_z) * float(spec.get('waist_frac', 0.36))
    chest_z = hip_z + (sh_z - hip_z) * float(spec.get('chest_frac', 0.74))

    # Lower limb landmarks
    ankle_z = h * float(spec.get('ankle_frac', 0.050))
    knee_z = ankle_z + (hip_z - ankle_z) * float(spec.get('knee_frac', 0.495))

    # Widths & depths (half-extents from center plane)
    sh_x = h * float(spec.get('shoulder_w', 0.112))
    hip_x = h * float(spec.get('hip_w', 0.058))
    torso_w = sh_x * float(spec.get('torso_w_ratio', 0.86))
    waist_w = h * float(spec.get('waist_w', 0.082))
    pelvis_w = h * float(spec.get('pelvis_w', 0.094))
    chest_d = h * float(spec.get('chest_d', 0.068))
    waist_d = h * float(spec.get('waist_d', 0.058))
    pelvis_d = h * float(spec.get('pelvis_d', 0.066))

    # Arms in a natural relaxed A-pose (74 deg below horizontal) for clean shoulder deformation
    upper_len = h * float(spec.get('upperarm_frac', 0.172))
    lower_len = h * float(spec.get('lowerarm_frac', 0.148))
    hand_len = h * float(spec.get('hand_frac', 0.104))

    a_angle = math.radians(float(spec.get('arm_drop_deg', 73.0)))
    f_angle = math.radians(float(spec.get('arm_drop_deg', 73.0)) + 5.0)

    def clav_pos(s):
        return Vector((s * sh_x * 0.24, -0.008, neck_bot_z - 0.014))

    def sh_pos(s):
        return Vector((s * sh_x, 0.006, sh_z))

    def elb_pos(s):
        return sh_pos(s) + Vector((
            s * math.cos(a_angle) * upper_len,
            0.012,
            -math.sin(a_angle) * upper_len,
        ))

    def wri_pos(s):
        return elb_pos(s) + Vector((
            s * math.cos(f_angle) * lower_len,
            -0.024,
            -math.sin(f_angle) * lower_len,
        ))

    def hand_tip(s):
        return wri_pos(s) + Vector((
            s * math.cos(f_angle + 0.05) * hand_len,
            -0.016,
            -math.sin(f_angle + 0.05) * hand_len,
        ))

    foot_len = h * float(spec.get('foot_len', 0.145))
    foot_y_heel = foot_len * 0.24

    return {
        'height': h,
        'head_h': head_h,
        'head_w': head_w,
        'head_d': head_d,
        'head_r': head_r,
        'crown_z': crown_z,
        'chin_z': chin_z,
        'head_center': Vector((0.0, -0.008, head_center_z)),
        'neck_top': Vector((0.0, 0.004, neck_top_z)),
        'neck_bot': Vector((0.0, 0.006, neck_bot_z)),
        'pelvis': Vector((0.0, 0.0, hip_z)),
        'waist': Vector((0.0, 0.0, waist_z)),
        'chest': Vector((0.0, 0.0, chest_z)),
        'sh_z': sh_z,
        'sh_x': sh_x,
        'hip_z': hip_z,
        'hip_x': hip_x,
        'knee_z': knee_z,
        'ankle_z': ankle_z,
        'waist_z': waist_z,
        'chest_z': chest_z,
        'torso_w': torso_w,
        'waist_w': waist_w,
        'pelvis_w': pelvis_w,
        'chest_d': chest_d,
        'waist_d': waist_d,
        'pelvis_d': pelvis_d,
        'upper_len': upper_len,
        'lower_len': lower_len,
        'hand_len': hand_len,
        'foot_len': foot_len,
        'foot_y_heel': foot_y_heel,
        'clav_l': clav_pos(1.0), 'clav_r': clav_pos(-1.0),
        'sh_l': sh_pos(1.0), 'sh_r': sh_pos(-1.0),
        'elb_l': elb_pos(1.0), 'elb_r': elb_pos(-1.0),
        'wri_l': wri_pos(1.0), 'wri_r': wri_pos(-1.0),
        'hand_l': hand_tip(1.0), 'hand_r': hand_tip(-1.0),
        'hip_l': Vector((hip_x, 0.0, hip_z)),
        'hip_r': Vector((-hip_x, 0.0, hip_z)),
        'knee_l': Vector((hip_x * 0.96, -0.006, knee_z)),
        'knee_r': Vector((-hip_x * 0.96, -0.006, knee_z)),
        'ankle_l': Vector((hip_x * 0.94, 0.006, ankle_z)),
        'ankle_r': Vector((-hip_x * 0.94, 0.006, ankle_z)),
        'toe_l': Vector((hip_x * 0.96, -foot_len * 0.72, ankle_z * 0.34)),
        'toe_r': Vector((-hip_x * 0.96, -foot_len * 0.72, ankle_z * 0.34)),
    }


def build_armature(name, col, lm):
    """Build the exact 19-bone realistic human skeleton (zero face bones)."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    arm_data = bpy.data.armatures.new(name)
    arm_obj = bpy.data.objects.new(name, arm_data)
    col.objects.link(arm_obj)

    for o in list(bpy.context.selected_objects):
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones

    def add_bone(bname, head, tail, parent=None, connect=False):
        b = eb.new(bname)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.roll = 0.0
        b.use_deform = True
        if parent is not None:
            b.parent = eb[parent]
            b.use_connect = connect
        return b

    # Spine & head (5 bones)
    add_bone('pelvis', lm['pelvis'], lm['waist'])
    add_bone('spine_01', lm['waist'], lm['chest'], 'pelvis', connect=True)
    add_bone('spine_02', lm['chest'], lm['neck_bot'], 'spine_01', connect=True)
    add_bone('neck', lm['neck_bot'], lm['neck_top'], 'spine_02', connect=True)
    head_top = Vector((0.0, lm['head_center'].y, lm['crown_z']))
    add_bone('head', lm['neck_top'], head_top, 'neck', connect=True)

    # Arms (8 bones)
    for sd in ('l', 'r'):
        add_bone(f'clavicle_{sd}', lm[f'clav_{sd}'], lm[f'sh_{sd}'], 'spine_02', connect=False)
        add_bone(f'upperarm_{sd}', lm[f'sh_{sd}'], lm[f'elb_{sd}'], f'clavicle_{sd}', connect=True)
        add_bone(f'lowerarm_{sd}', lm[f'elb_{sd}'], lm[f'wri_{sd}'], f'upperarm_{sd}', connect=True)
        add_bone(f'hand_{sd}', lm[f'wri_{sd}'], lm[f'hand_{sd}'], f'lowerarm_{sd}', connect=True)

    # Legs (6 bones)
    for sd in ('l', 'r'):
        add_bone(f'thigh_{sd}', lm[f'hip_{sd}'], lm[f'knee_{sd}'], 'pelvis', connect=False)
        add_bone(f'calf_{sd}', lm[f'knee_{sd}'], lm[f'ankle_{sd}'], f'thigh_{sd}', connect=True)
        add_bone(f'foot_{sd}', lm[f'ankle_{sd}'], lm[f'toe_{sd}'], f'calf_{sd}', connect=True)

    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    assert len(arm_obj.data.bones) == 19, f'Expected 19 bones, got {len(arm_obj.data.bones)}'
    return arm_obj


# ------------------------------------------------------------------ skinning helpers
def bind_armature(obj, rig):
    """Parent obj cleanly to rig with Armature modifier."""
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    for m in list(obj.modifiers):
        if m.type == 'ARMATURE':
            m.object = rig
            return obj
    am = obj.modifiers.new('rig', 'ARMATURE')
    am.object = rig
    return obj


def _set_weights(obj, rig, weight_map, fallback_bone='pelvis'):
    """Assign normalized vertex weights (max 4 bones/vert, zero unskinned verts)."""
    for vg in list(obj.vertex_groups):
        obj.vertex_groups.remove(vg)
    groups = {}

    def get_vg(bname):
        if bname not in groups:
            groups[bname] = obj.vertex_groups.new(name=bname)
        return groups[bname]

    valid_bones = set(rig.data.bones.keys())
    for v in obj.data.vertices:
        bw = weight_map.get(v.index) or {}
        items = [(k, float(w)) for k, w in bw.items() if k in valid_bones and float(w) > 1e-4]
        items.sort(key=lambda kv: -kv[1])
        items = items[:4]
        total = sum(w for _, w in items)
        if total <= 1e-6:
            items = [(fallback_bone, 1.0)]
            total = 1.0
        for bname, w in items:
            get_vg(bname).add([v.index], w / total, 'REPLACE')
    return bind_armature(obj, rig)


def validate_skinning(obj, rig):
    """Verify every vertex has 1..4 weights summing to 1.0 with valid bone names."""
    valid = set(rig.data.bones.keys())
    vg_names = {vg.index: vg.name for vg in obj.vertex_groups}
    unskinned = 0
    over4 = 0
    for v in obj.data.vertices:
        ws = [
            (vg_names[g.group], g.weight)
            for g in v.groups
            if g.group in vg_names and vg_names[g.group] in valid and g.weight > 1e-5
        ]
        if not ws:
            unskinned += 1
        if len(ws) > 4:
            over4 += 1
    if unskinned or over4:
        raise ValueError(f'Skinning error on {obj.name}: unskinned={unskinned}, over4={over4}')


def _seg_t_dist(p, a, b):
    """Return parameter t in [0, 1] and Euclidean distance from point p to segment a-b."""
    ab = b - a
    l2 = ab.length_squared
    if l2 < 1e-10:
        return 0.0, (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / l2))
    proj = a + ab * t
    return t, (p - proj).length


def _spine_weights(z, lm, allow_neck=True, allow_head=False):
    z_pel = lm['hip_z']
    z_wst = lm['waist_z']
    z_chs = lm['chest_z']
    z_nb = lm['neck_bot'].z
    z_nt = lm['neck_top'].z

    if z <= z_pel:
        return {'pelvis': 1.0}
    if z <= z_wst:
        t = smoothstep(z_pel, z_wst, z)
        return {'pelvis': 1.0 - t, 'spine_01': t}
    if z <= z_chs:
        t = smoothstep(z_wst, z_chs, z)
        return {'spine_01': 1.0 - t, 'spine_02': t}
    if not allow_neck or z <= z_nb - 0.025:
        return {'spine_02': 1.0}
    t_nk = smoothstep(z_nb - 0.025, z_nb + 0.032, z)
    if not allow_head or z <= z_nt - 0.024:
        return {'spine_02': 1.0 - t_nk, 'neck': t_nk}
    t_hd = smoothstep(z_nt - 0.024, z_nt + 0.024, z)
    return {'spine_02': 1.0 - t_nk, 'neck': t_nk * (1.0 - t_hd), 'head': t_nk * t_hd}


def _arm_chain_weights(p, lm, sd, blend=0.22):
    segs = [
        (f'upperarm_{sd}', lm[f'sh_{sd}'], lm[f'elb_{sd}']),
        (f'lowerarm_{sd}', lm[f'elb_{sd}'], lm[f'wri_{sd}']),
        (f'hand_{sd}', lm[f'wri_{sd}'], lm[f'hand_{sd}']),
    ]
    best_i, best_t, best_d = 0, 0.0, 1e9
    for i, (_, a, b) in enumerate(segs):
        t, d = _seg_t_dist(p, a, b)
        if d < best_d:
            best_i, best_t, best_d = i, t, d
    name_i = segs[best_i][0]
    if best_i > 0 and best_t < blend:
        f = smoothstep(0.0, blend, best_t) * 0.5 + 0.5
        return {name_i: f, segs[best_i - 1][0]: 1.0 - f}, best_d
    if best_i < len(segs) - 1 and best_t > 1.0 - blend:
        f = smoothstep(1.0 - blend, 1.0, best_t) * 0.5
        return {name_i: 1.0 - f, segs[best_i + 1][0]: f}, best_d
    return {name_i: 1.0}, best_d


def _leg_chain_weights(p, lm, sd):
    z_hip = lm['hip_z']
    z_knee = lm['knee_z']
    z_ank = lm['ankle_z']
    if p.z > z_hip - 0.055:
        t = smoothstep(z_hip + 0.035, z_hip - 0.065, p.z)
        lat = smoothstep(0.0, lm['hip_x'] * 0.55, abs(p.x))
        w_th = t * (0.55 + 0.45 * lat)
        return {'pelvis': 1.0 - w_th, f'thigh_{sd}': w_th}
    if p.z > z_knee - 0.055:
        t_cf = smoothstep(z_knee + 0.048, z_knee - 0.048, p.z)
        return {f'thigh_{sd}': 1.0 - t_cf, f'calf_{sd}': t_cf}
    if p.z > z_ank - 0.015:
        t_ft = smoothstep(z_ank + 0.036, z_ank - 0.015, p.z)
        return {f'calf_{sd}': 1.0 - t_ft, f'foot_{sd}': t_ft}
    return {f'foot_{sd}': 1.0}


def skin_rigid(obj, rig, bone_name):
    """Bind every vertex of obj rigidly to a single bone."""
    wmap = {v.index: {bone_name: 1.0} for v in obj.data.vertices}
    return _set_weights(obj, rig, wmap, fallback_bone=bone_name)


def skin_limb_chain(obj, rig, bone_names, blend=0.22):
    """Smooth analytical weighting along an ordered sequential bone chain."""
    bones = [
        (n, rig.data.bones[n].head_local.copy(), rig.data.bones[n].tail_local.copy())
        for n in bone_names
    ]
    wmap = {}
    for v in obj.data.vertices:
        p = v.co
        best_i, best_t, best_d = 0, 0.0, 1e9
        for i, (_, a, b) in enumerate(bones):
            t, d = _seg_t_dist(p, a, b)
            if d < best_d:
                best_i, best_t, best_d = i, t, d
        name_i = bones[best_i][0]
        if best_i > 0 and best_t < blend:
            f = smoothstep(0.0, blend, best_t) * 0.5 + 0.5
            bw = {name_i: f, bones[best_i - 1][0]: 1.0 - f}
        elif best_i < len(bones) - 1 and best_t > 1.0 - blend:
            f = smoothstep(1.0 - blend, 1.0, best_t) * 0.5
            bw = {name_i: 1.0 - f, bones[best_i + 1][0]: f}
        else:
            bw = {name_i: 1.0}
        wmap[v.index] = bw
    return _set_weights(obj, rig, wmap, fallback_bone=bone_names[0])


def skin_body(obj, rig, lm):
    """Smooth analytical skinning for a complete anatomical body mesh."""
    sh_x = lm['sh_x']
    sh_z = lm['sh_z']
    hip_z = lm['hip_z']
    pelvis_w = lm['pelvis_w']
    wmap = {}

    for v in obj.data.vertices:
        p = v.co
        sd = 'l' if p.x >= 0.0 else 'r'
        ax = abs(p.x)

        aw, d_arm = _arm_chain_weights(p, lm, sd, blend=0.22)

        # Determine arm membership cleanly (A-pose arms & thumbs sit outside torso & thighs)
        t_sh_lat = smoothstep(sh_x * 0.72, sh_x * 1.06, ax)
        t_arm_prox = 1.0 - smoothstep(0.115, 0.165, d_arm)
        if p.z < hip_z + 0.04:
            # Below hip, include full hand & inward-pointing thumb cleanly
            t_arm_lat = smoothstep(pelvis_w * 0.85, pelvis_w * 1.05, ax)
            in_arm = t_arm_lat * t_arm_prox
        elif p.z > sh_z + 0.085:
            in_arm = 0.0
        else:
            in_arm = t_sh_lat * t_arm_prox

        if in_arm > 0.98:
            wmap[v.index] = aw
            continue

        if p.z < hip_z - 0.025 and in_arm < 0.5:
            base = _leg_chain_weights(p, lm, sd)
        else:
            base = _spine_weights(p.z, lm, allow_neck=True, allow_head=True)
            # Subtle clavicle blend across upper shoulder ridge
            if sh_z - 0.05 < p.z < lm['neck_bot'].z + 0.02 and ax > sh_x * 0.32:
                tc = smoothstep(sh_x * 0.32, sh_x * 0.88, ax) * 0.45
                sp2 = base.get('spine_02', 0.0)
                if sp2 > 0.0:
                    base['spine_02'] = sp2 * (1.0 - tc)
                    base[f'clavicle_{sd}'] = base.get(f'clavicle_{sd}', 0.0) + sp2 * tc

        if in_arm > 0.01:
            bw = {}
            for k, w in base.items():
                bw[k] = bw.get(k, 0.0) + w * (1.0 - in_arm)
            for k, w in aw.items():
                bw[k] = bw.get(k, 0.0) + w * in_arm
            wmap[v.index] = bw
        else:
            wmap[v.index] = base

    return _set_weights(obj, rig, wmap, fallback_bone='pelvis')


def skin_upper_garment(obj, rig, lm, mode='shirt'):
    """Skin tops, jackets, and draped ihram rida shawls smoothly across spine & arms.

    mode:
      - 'shirt': sleeved shirt/blazer (full arm tracking outside shoulder)
      - 'rida_covered': draped shawl over BOTH shoulders (softer shoulder/upperarm follow)
      - 'rida_idtiba': diagonal shawl under RIGHT armpit (-X) and over LEFT shoulder (+X)
    """
    sh_x = lm['sh_x']
    sh_z = lm['sh_z']
    wmap = {}

    for v in obj.data.vertices:
        p = v.co
        sd = 'l' if p.x >= 0.0 else 'r'
        ax = abs(p.x)
        sp = _spine_weights(p.z, lm, allow_neck=True, allow_head=False)

        if mode == 'rida_idtiba':
            # Right side (-X) passes under right armpit -> stays anchored to spine (never pulled by right arm)
            if p.x <= 0.0:
                wmap[v.index] = sp
                continue
            # Left shoulder (+X) follows clavicle_l + gentle upperarm_l over deltoid drape
            aw, d_arm = _arm_chain_weights(p, lm, 'l', blend=0.25)
            in_arm = smoothstep(sh_x * 0.78, sh_x * 1.24, ax) * (1.0 - smoothstep(0.08, 0.16, d_arm)) * 0.65
            t_clav = smoothstep(sh_x * 0.35, sh_x * 0.95, ax) * smoothstep(lm['chest_z'], sh_z, p.z) * 0.45
            bw = {}
            for k, w in sp.items():
                bw[k] = bw.get(k, 0.0) + w * (1.0 - in_arm - t_clav * 0.6)
            if t_clav > 0.01:
                bw['clavicle_l'] = bw.get('clavicle_l', 0.0) + t_clav * 0.6
            if in_arm > 0.01:
                for k, w in aw.items():
                    bw[k] = bw.get(k, 0.0) + w * in_arm
            wmap[v.index] = bw
            continue

        aw, d_arm = _arm_chain_weights(p, lm, sd, blend=0.22)
        if mode == 'rida_covered':
            # Draped shawl over both shoulders: smooth clavicle + moderate upperarm follow
            in_arm = smoothstep(sh_x * 0.80, sh_x * 1.22, ax) * (1.0 - smoothstep(0.08, 0.16, d_arm)) * 0.62
            t_clav = smoothstep(sh_x * 0.38, sh_x * 0.95, ax) * smoothstep(lm['chest_z'], sh_z, p.z) * 0.40
            bw = {}
            for k, w in sp.items():
                bw[k] = bw.get(k, 0.0) + w * (1.0 - in_arm - t_clav * 0.55)
            if t_clav > 0.01:
                bw[f'clavicle_{sd}'] = bw.get(f'clavicle_{sd}', 0.0) + t_clav * 0.55
            if in_arm > 0.01:
                for k, w in aw.items():
                    bw[k] = bw.get(k, 0.0) + w * in_arm
            wmap[v.index] = bw
            continue

        # Standard sleeved shirt / blazer
        if p.z < lm['hip_z'] + 0.03:
            in_arm = smoothstep(lm['pelvis_w'] * 1.15, lm['pelvis_w'] * 1.45, ax) * (1.0 - smoothstep(0.08, 0.14, d_arm))
        elif p.z > sh_z + 0.085:
            in_arm = 0.0
        else:
            in_arm = smoothstep(sh_x * 0.74, sh_x * 1.08, ax) * (1.0 - smoothstep(0.085, 0.145, d_arm))

        if in_arm > 0.01:
            bw = {}
            for k, w in sp.items():
                bw[k] = bw.get(k, 0.0) + w * (1.0 - in_arm)
            for k, w in aw.items():
                bw[k] = bw.get(k, 0.0) + w * in_arm
            wmap[v.index] = bw
        else:
            wmap[v.index] = sp

    return _set_weights(obj, rig, wmap, fallback_bone='spine_02')


def skin_izar_robe(obj, rig, lm, top_z=None, hem_z=None, calf_follow=0.68, sandal_z=None):
    """Skin a draped lower ihram wrap (izar) or long uniform skirt cleanly over pelvis/thighs/calves.

    If `sandal_z` is provided, vertices below `sandal_z` are cleanly bound to foot_l/foot_r
    so attached sandals deform with the feet while the izar follows the thighs & calves.
    """
    z_hip = lm['hip_z']
    z_knee = lm['knee_z']
    z_top = top_z if top_z is not None else lm['waist_z'] + 0.04
    hip_x = lm['hip_x']
    wmap = {}

    for v in obj.data.vertices:
        p = v.co
        z = p.z
        sd = 'l' if p.x >= 0.0 else 'r'

        if sandal_z is not None and z < sandal_z:
            wmap[v.index] = {f'foot_{sd}': 1.0}
            continue

        lr_span = hip_x * 1.35
        w_l = smoothstep(-lr_span, lr_span, p.x)
        w_r = 1.0 - w_l

        if z > z_hip + 0.04:
            t = smoothstep(z_hip + 0.04, z_top, z)
            bw = {'pelvis': 1.0 - t * 0.65, 'spine_01': t * 0.65}
        else:
            t_leg = smoothstep(z_hip + 0.04, z_hip - 0.14, z)
            t_calf = smoothstep(z_knee + 0.08, z_knee - 0.11, z) * calf_follow
            w_pel = 1.0 - t_leg * 0.90
            w_legs = 1.0 - w_pel
            w_th = w_legs * (1.0 - t_calf)
            w_cf = w_legs * t_calf
            bw = {
                'pelvis': w_pel,
                'thigh_l': w_th * w_l,
                'thigh_r': w_th * w_r,
                'calf_l': w_cf * w_l,
                'calf_r': w_cf * w_r,
            }
        wmap[v.index] = bw

    return _set_weights(obj, rig, wmap, fallback_bone='pelvis')


def skin_trousers(obj, rig, lm, include_shoes=True):
    """Skin split-leg trousers (and optional attached shoes) across pelvis, thigh, calf, foot."""
    z_hip = lm['hip_z']
    z_knee = lm['knee_z']
    z_ank = lm['ankle_z']
    wmap = {}

    for v in obj.data.vertices:
        p = v.co
        sd = 'l' if p.x >= 0.0 else 'r'
        if p.z > z_hip + 0.045:
            t = smoothstep(z_hip + 0.045, lm['waist_z'] + 0.04, p.z)
            bw = {'pelvis': 1.0 - t * 0.45, 'spine_01': t * 0.45}
        elif p.z > z_hip - 0.065:
            t = smoothstep(z_hip + 0.045, z_hip - 0.065, p.z)
            lat = smoothstep(0.0, lm['hip_x'] * 0.50, abs(p.x))
            w_th = t * (0.55 + 0.45 * lat)
            bw = {'pelvis': 1.0 - w_th, f'thigh_{sd}': w_th}
        elif p.z > z_ank + 0.032 or not include_shoes:
            t_cf = smoothstep(z_knee + 0.048, z_knee - 0.048, p.z)
            bw = {f'thigh_{sd}': 1.0 - t_cf, f'calf_{sd}': t_cf}
        elif p.z > z_ank - 0.015:
            t_ft = smoothstep(z_ank + 0.032, z_ank - 0.015, p.z)
            bw = {f'calf_{sd}': 1.0 - t_ft, f'foot_{sd}': t_ft}
        else:
            bw = {f'foot_{sd}': 1.0}
        wmap[v.index] = bw

    return _set_weights(obj, rig, wmap, fallback_bone='pelvis')


def skin_headwear(obj, rig, lm, drape_shoulders=False):
    """Skin hair/beard rigidly to head, or draped hijab smoothly from head -> neck -> chest."""
    if not drape_shoulders:
        return skin_rigid(obj, rig, 'head')

    sh_x = lm['sh_x']
    sh_z = lm['sh_z']
    z_nt = lm['neck_top'].z
    wmap = {}
    for v in obj.data.vertices:
        p = v.co
        t_head = smoothstep(sh_z + 0.055, z_nt + 0.02, p.z)
        t_neck = smoothstep(sh_z + 0.005, sh_z + 0.075, p.z) * (1.0 - t_head)
        t_body = max(0.0, 1.0 - t_head - t_neck)
        sd = 'l' if p.x >= 0.0 else 'r'
        t_cl = smoothstep(sh_x * 0.42, sh_x * 1.02, abs(p.x)) * t_body * 0.50
        wmap[v.index] = {
            'head': t_head,
            'neck': t_neck,
            'spine_02': max(0.0, t_body - t_cl),
            f'clavicle_{sd}': t_cl,
        }
    return _set_weights(obj, rig, wmap, fallback_bone='head')
