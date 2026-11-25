"""Seamless 24 fps NLA animation clip generator for the 19-bone realistic human rig.

Clips:
- idle    (72 frames, 3.0s): natural breathing, subtle weight sway, relaxed arms
- walk    (24 frames, 1.0s): realistic human walk cycle (~1.35 m/cycle)
- run     (16 frames, 0.67s): brisk raml / green-lights jogging gait (~75 deg elbows)
- talk    (96 frames, 4.0s): calm respectful conversation with open-palm hand gestures
- gesture (36 frames, 1.5s): right-arm istilam / takbir gesture toward Black Stone / Qibla
- pray    (96 frames, 4.0s): qiyam -> ruku' -> i'tidal -> sujud -> qiyam prayer cycle

Zero face bones. Compatible with Blender 5.2 LTS slotted Actions & glTF NLA_TRACKS export.
"""
import math
import sys

import bpy
from mathutils import Matrix, Vector

from blender.characters.rig import BONE_NAMES
from blender.lib.common import smoothstep

sys.dont_write_bytecode = True

FPS = 24
X = Vector((1.0, 0.0, 0.0))
Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))


def _sin(t, k=1.0, phase=0.0):
    return math.sin((t * k + phase) * math.tau)


def _pulse(t, t0, dur, power=1.25):
    u = (t - t0) / max(dur, 1e-6)
    if u <= 0.0 or u >= 1.0:
        return 0.0
    return math.sin(math.pi * u) ** power


def _trap(t, t_in0, t_in1, t_out0, t_out1):
    """Smooth trapezoid envelope: 0 -> 1 over [t_in0, t_in1], hold 1, 1 -> 0 over [t_out0, t_out1]."""
    if t <= t_in0 or t >= t_out1:
        return 0.0
    if t < t_in1:
        return smoothstep(t_in0, t_in1, t)
    if t <= t_out0:
        return 1.0
    return 1.0 - smoothstep(t_out0, t_out1, t)


def reset_pose(rig):
    """Reset all pose bones to identity rest pose."""
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def _rot(rig, name, axis, deg):
    pb = rig.pose.bones.get(name)
    if not pb or abs(deg) < 1e-4:
        return
    m = pb.matrix.copy()
    h = m.to_translation()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h) @ m
    bpy.context.view_layer.update()


def _aim(rig, name, direction):
    pb = rig.pose.bones.get(name)
    if not pb:
        return
    cur = (pb.tail - pb.head).normalized()
    tgt = Vector(direction).normalized()
    q = cur.rotation_difference(tgt)
    axis, ang = q.to_axis_angle()
    if abs(ang) > 1e-4:
        _rot(rig, name, axis, math.degrees(ang))


def _twist(rig, name, deg):
    pb = rig.pose.bones.get(name)
    if not pb or abs(deg) < 1e-4:
        return
    axis = pb.tail - pb.head
    if axis.length < 1e-5:
        return
    _rot(rig, name, axis.normalized(), deg)


def _move(rig, name, offset):
    pb = rig.pose.bones.get(name)
    if not pb:
        return
    pb.matrix = Matrix.Translation(Vector(offset)) @ pb.matrix
    bpy.context.view_layer.update()


def _key_frame(rig, frame):
    for n in BONE_NAMES:
        pb = rig.pose.bones.get(n)
        if pb:
            pb.keyframe_insert('rotation_quaternion', frame=frame)
            if n == 'pelvis':
                pb.keyframe_insert('location', frame=frame)


def _make_clip(rig, key, clip_name, frames, pose_fn):
    act_name = f'{key}_{clip_name}'
    old = bpy.data.actions.get(act_name)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(act_name)
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act

    for f in range(frames + 1):
        t = f / frames
        reset_pose(rig)
        pose_fn(rig, t)
        _key_frame(rig, f + 1)

    act['clip'] = clip_name
    return act


def _push_nla(rig, acts):
    """Push all Actions to named NLA tracks compatible with Blender 5.2 glTF NLA_TRACKS export."""
    ad = rig.animation_data
    ad.action = None
    for tr in list(ad.nla_tracks):
        ad.nla_tracks.remove(tr)
    for act in acts:
        clip_name = act['clip']
        tr = ad.nla_tracks.new()
        tr.name = clip_name
        strip = tr.strips.new(clip_name, 1, act)
        if hasattr(strip, 'action_slot') and getattr(act, 'slots', None):
            if len(act.slots) > 0:
                try:
                    strip.action_slot = act.slots[0]
                except Exception:
                    pass
        tr.mute = False
    reset_pose(rig)


class Animator:
    """Procedural realistic human animator for umrah-journey characters."""

    def __init__(self, rig, style=None):
        self.rig = rig
        self.st = style or {}
        b = rig.data.bones
        self.thigh_len = (b['thigh_l'].tail_local - b['thigh_l'].head_local).length
        self.calf_len = (b['calf_l'].tail_local - b['calf_l'].head_local).length
        self.leg_len = self.thigh_len + self.calf_len
        self.hip_z = b['thigh_l'].head_local.z
        self.knee_z = b['calf_l'].head_local.z
        self.ankle_z = b['foot_l'].head_local.z

    def _arms_relaxed(self, out=0.14, fwd=0.04, elbow=15.0):
        r = self.rig
        er = math.radians(elbow)
        for sd, s in (('l', 1.0), ('r', -1.0)):
            _aim(r, f'upperarm_{sd}', (s * out, -fwd, -1.0))
            _aim(r, f'lowerarm_{sd}', (s * out * 0.35, -fwd - math.sin(er), -math.cos(er)))
            _twist(r, f'hand_{sd}', -s * 10.0)
            _rot(r, f'hand_{sd}', X, 5.0)

    def _posture(self, k=1.0):
        stoop = float(self.st.get('stoop', 0.0)) * k
        if abs(stoop) > 1e-3:
            _rot(self.rig, 'spine_01', X, stoop * 0.45)
            _rot(self.rig, 'spine_02', X, stoop * 0.55)
            _rot(self.rig, 'neck', X, -stoop * 0.45)
            _rot(self.rig, 'head', X, -stoop * 0.25)

    def idle(self, rig, t):
        e = float(self.st.get('energy', 1.0))
        self._arms_relaxed(out=float(self.st.get('arm_out', 0.14)), elbow=float(self.st.get('elbow', 15.0)))
        self._posture()

        br = _sin(t, 1.0)
        _rot(rig, 'spine_01', X, -1.0 * br)
        _rot(rig, 'spine_02', X, -1.4 * br)
        for sd in ('l', 'r'):
            _rot(rig, f'clavicle_{sd}', X, 0.7 * br)
            _rot(rig, f'upperarm_{sd}', X, 1.4 * br)
            _rot(rig, f'lowerarm_{sd}', X, -2.0 * br)
            _rot(rig, f'hand_{sd}', X, 2.2 * _sin(t, 1.0, 0.14))

        sway = _sin(t, 1.0, 0.25)
        _rot(rig, 'pelvis', Y, 1.1 * e * sway)
        _rot(rig, 'spine_01', Y, -0.9 * e * sway)
        _move(rig, 'pelvis', (0.008 * e * sway, 0.0, 0.004 * br))
        _rot(rig, 'neck', Z, 1.8 * e * _sin(t, 1.0, 0.12))
        _rot(rig, 'head', Z, 3.2 * e * _sin(t, 1.0, 0.14))
        _rot(rig, 'head', X, 1.3 * _sin(t, 2.0))
        _rot(rig, 'head', Y, 1.5 * e * _sin(t, 1.0, 0.38))

    def gait(self, run=False):
        # Walk: 24 frames (1.0s), ~1.35 m/cycle -> half-stride ~0.675 m
        # Run:  16 frames (0.67s), brisk raml / green-lights jog (elbows ~75 deg)
        stride = 0.84 if run else 0.67
        raw_amp = math.degrees(math.asin(min(0.84, stride / max(0.4, 2.0 * self.leg_len))))
        amp = raw_amp * (0.94 if run else 0.88)
        lean = 10.5 if run else 3.2
        elbow_base = 75.0 if run else 18.0

        def pose(rig, t):
            self._arms_relaxed(out=0.14 if run else 0.15, fwd=0.06 if run else 0.03, elbow=elbow_base)
            self._posture(0.65)
            ph = _sin(t, 1.0)

            # Natural counter-rotation of pelvis vs ribcage
            _rot(rig, 'pelvis', Z, (7.0 if run else 5.2) * ph)
            _rot(rig, 'pelvis', Y, (2.2 if run else 1.8) * _sin(t, 1.0, 0.25))
            _rot(rig, 'spine_01', Z, -(4.5 if run else 3.5) * ph)
            _rot(rig, 'spine_02', Z, -(4.5 if run else 3.2) * ph)
            _rot(rig, 'spine_01', X, lean * 0.60)
            _rot(rig, 'spine_02', X, lean * 0.40)

            for sd, sign in (('l', 1.0), ('r', -1.0)):
                w = sign * ph  # +1 = forward swing, -1 = push-off back
                # Thigh swings forward (-X) and backward (+X)
                _rot(rig, f'thigh_{sd}', X, -amp * w - (8.0 if run else 2.0))
                # Swing-phase knee bend (+X bends calf backward cleanly!)
                sw = max(0.0, -_sin(t, 1.0, 0.10 if sign > 0 else 0.60))
                knee_max = 76.0 if run else 44.0
                _rot(rig, f'calf_{sd}', X, sw * knee_max + (10.0 if run else 4.0))
                # Ankle heel-strike dorsiflexion & toe-off plantarflexion
                _rot(rig, f'foot_{sd}', X, -10.0 * w - (10.0 * sw if run else 4.0 * sw))

                # Opposite arm swing (when left leg moves forward w>0, left arm swings back +X)
                arm_amp = 42.0 if run else 24.0
                _rot(rig, f'upperarm_{sd}', X, arm_amp * w)
                _rot(rig, f'lowerarm_{sd}', X, -(16.0 if run else 9.0) * max(0.0, -w))

            _rot(rig, 'neck', X, -lean * 0.45)
            _rot(rig, 'head', X, -lean * 0.35)
            _rot(rig, 'head', Z, 1.8 * ph)

            # Grounded vertical center-of-mass bob
            bob = (0.5 - 0.5 * _sin(t, 2.0, 0.25)) * (0.052 if run else 0.026) * self.leg_len
            _move(rig, 'pelvis', (0.0, 0.0, -bob))

        return pose

    def talk(self, rig, t):
        e = float(self.st.get('energy', 1.0))
        self._arms_relaxed(out=float(self.st.get('arm_out', 0.15)), elbow=22.0)
        self._posture()

        br = _sin(t, 1.0)
        _rot(rig, 'spine_01', X, -1.0 * br)
        _rot(rig, 'spine_02', X, -1.2 * br)
        _rot(rig, 'pelvis', Y, 1.0 * e * _sin(t, 1.0, 0.25))

        # Two respectful conversational open-palm hand beats
        b1 = _pulse(t, 0.06, 0.40, 1.25)
        b2 = _pulse(t, 0.50, 0.44, 1.25)
        r_g = min(1.0, b1 + 0.85 * b2)
        l_g = min(1.0, 0.25 * b1 + b2)

        # Right arm warm open-palm presentation
        _rot(rig, 'upperarm_r', X, -(28.0 * b1 + 22.0 * b2) * e)
        _rot(rig, 'upperarm_r', Y, -(8.0 * b1 + 12.0 * b2))
        _rot(rig, 'upperarm_r', Z, -(8.0 * b1 + 12.0 * b2))
        _rot(rig, 'lowerarm_r', X, -(58.0 * b1 + 52.0 * b2))
        _rot(rig, 'lowerarm_r', Z, -(14.0 * b1 + 18.0 * b2))
        _twist(rig, 'lowerarm_r', 44.0 * r_g)
        _twist(rig, 'hand_r', 36.0 * r_g)
        _rot(rig, 'hand_r', X, 16.0 * r_g + 5.0 * r_g * _sin(t, 5.0))

        # Left arm joins gently on Beat 2
        _rot(rig, 'upperarm_l', X, -(10.0 * b1 + 24.0 * b2) * e)
        _rot(rig, 'upperarm_l', Y, 12.0 * b2)
        _rot(rig, 'upperarm_l', Z, 12.0 * b2)
        _rot(rig, 'lowerarm_l', X, -(20.0 * b1 + 54.0 * b2))
        _rot(rig, 'lowerarm_l', Z, 18.0 * b2)
        _twist(rig, 'lowerarm_l', -44.0 * l_g)
        _twist(rig, 'hand_l', -36.0 * l_g)
        _rot(rig, 'hand_l', X, 14.0 * l_g + 4.0 * b2 * _sin(t, 5.0, 0.25))

        _rot(rig, 'spine_02', X, 2.2 * b1 + 1.8 * b2)
        _rot(rig, 'spine_01', Z, -2.8 * b1 + 2.0 * b2)
        _rot(rig, 'head', X, -4.5 * max(0.0, _sin(t, 4.0)) + 1.5)
        _rot(rig, 'head', Z, 5.5 * _sin(t, 1.0, 0.25))
        _rot(rig, 'head', Y, -2.2 * _sin(t, 2.0, 0.18))

    def gesture(self, rig, t):
        """Istilam / Takbir gesture: smoothly raises RIGHT arm forward-upward toward Black Stone / Qibla."""
        self._arms_relaxed(out=0.14, elbow=16.0)
        self._posture(0.8)

        # Smooth raise (0.05..0.38), respectful hold (0.38..0.64), smooth return (0.64..0.95)
        g = _trap(t, 0.05, 0.36, 0.64, 0.95)
        if g > 1e-4:
            # Slight respectful chest lift & gentle gaze alignment
            _rot(rig, 'spine_01', X, -2.5 * g)
            _rot(rig, 'spine_02', X, -3.5 * g)
            _rot(rig, 'spine_02', Z, 4.0 * g)
            _rot(rig, 'head', X, -4.0 * g)

            # Right clavicle elevates naturally with arm raise
            _rot(rig, 'clavicle_r', Y, -10.0 * g)
            _rot(rig, 'clavicle_r', Z, -6.0 * g)

            # Smoothly interpolate right arm from relaxed side to forward-upward istilam salute
            ua_relaxed = Vector((-0.14, -0.04, -1.0)).normalized()
            ua_raised = Vector((-0.24, -0.92, 0.34)).normalized()
            ua_dir = ua_relaxed.lerp(ua_raised, g).normalized()
            _aim(rig, 'upperarm_r', ua_dir)

            la_relaxed = Vector((-0.05, -0.28, -0.96)).normalized()
            la_raised = Vector((0.06, -0.66, 0.75)).normalized()
            la_dir = la_relaxed.lerp(la_raised, g).normalized()
            _aim(rig, 'lowerarm_r', la_dir)

            # Open right palm facing forward toward the Black Stone / Qibla
            _twist(rig, 'lowerarm_r', -22.0 * g)
            _twist(rig, 'hand_r', -18.0 * g)
            _rot(rig, 'hand_r', X, -14.0 * g)

            # Left arm stays calm and slightly steadied near side/waist
            _rot(rig, 'upperarm_l', X, -6.0 * g)
            _rot(rig, 'lowerarm_l', X, -14.0 * g)

    def pray(self, rig, t):
        """Respectful Islamic prayer sequence: Qiyam -> Ruku' -> I'tidal -> Sujud -> Qiyam."""
        self._arms_relaxed(out=0.14, elbow=16.0)

        # Phase weights (clean non-overlapping smooth trapezoids)
        # 1. Qiyam (hands folded respectfully over chest): [0.00..0.22] and returning [0.88..1.00]
        w_ruku = _trap(t, 0.18, 0.30, 0.40, 0.50)
        w_sujud = _trap(t, 0.52, 0.66, 0.80, 0.94)
        w_qiyam = max(0.0, 1.0 - max(w_ruku, w_sujud))

        # --- Standing Qiyam (folded hands over chest/upper abdomen) ---
        if w_qiyam > 1e-4:
            # Left arm folds first across lower chest, right hand rests gently over left wrist
            for sd, s, x_bias in (('l', 1.0, -0.02), ('r', -1.0, 0.02)):
                ua_0 = Vector((s * 0.14, -0.04, -1.0)).normalized()
                ua_q = Vector((s * 0.30, -0.34, -0.89)).normalized()
                _aim(rig, f'upperarm_{sd}', ua_0.lerp(ua_q, w_qiyam).normalized())

                la_0 = Vector((s * 0.05, -0.28, -0.96)).normalized()
                la_q = Vector((-s * 0.84, -0.46 + x_bias, 0.24)).normalized()
                _aim(rig, f'lowerarm_{sd}', la_0.lerp(la_q, w_qiyam).normalized())
                _rot(rig, f'hand_{sd}', Z, s * 14.0 * w_qiyam)
            _rot(rig, 'head', X, 7.0 * w_qiyam)  # humble downward gaze toward place of sujud

        # --- Ruku' (respectful bow at hips, straight back, hands on knees) ---
        if w_ruku > 1e-4:
            # Slight knee softness + forward hip flexion + flat straight back
            _move(rig, 'pelvis', (0.0, 0.06 * w_ruku, -0.05 * w_ruku))
            _rot(rig, 'pelvis', X, 54.0 * w_ruku)
            _rot(rig, 'spine_01', X, 16.0 * w_ruku)
            _rot(rig, 'spine_02', X, 12.0 * w_ruku)
            _rot(rig, 'neck', X, -14.0 * w_ruku)
            _rot(rig, 'head', X, -12.0 * w_ruku)

            # Legs stay planted upright (counter-rotate thighs against pelvis bow!)
            for sd in ('l', 'r'):
                _rot(rig, f'thigh_{sd}', X, -62.0 * w_ruku)
                _rot(rig, f'calf_{sd}', X, 14.0 * w_ruku)
                _rot(rig, f'foot_{sd}', X, -6.0 * w_ruku)

                # Arms reach straight down so hands rest cleanly on knees
                s = 1.0 if sd == 'l' else -1.0
                _aim(rig, f'upperarm_{sd}', Vector((s * 0.08, -0.06, -1.0)).normalized())
                _aim(rig, f'lowerarm_{sd}', Vector((s * 0.04, 0.08, -1.0)).normalized())

        # --- Sujud (respectful kneeling prostration) ---
        if w_sujud > 1e-4:
            # Lower pelvis cleanly to kneeling height (~0.36 m above ground)
            drop_z = (self.hip_z - 0.36) * w_sujud
            shift_y = 0.08 * w_sujud
            _move(rig, 'pelvis', (0.0, shift_y, -drop_z))

            # Hips & spine fold gently forward so forehead approaches ground cleanly
            _rot(rig, 'pelvis', X, 76.0 * w_sujud)
            _rot(rig, 'spine_01', X, 22.0 * w_sujud)
            _rot(rig, 'spine_02', X, 20.0 * w_sujud)
            _rot(rig, 'neck', X, 8.0 * w_sujud)
            _rot(rig, 'head', X, 6.0 * w_sujud)

            # Knees bent smoothly onto floor, shins folded back, feet tucked
            for sd in ('l', 'r'):
                _rot(rig, f'thigh_{sd}', X, -92.0 * w_sujud)
                _rot(rig, f'calf_{sd}', X, 118.0 * w_sujud)
                _rot(rig, f'foot_{sd}', X, -36.0 * w_sujud)

                # Arms reach down & forward with palms resting beside shoulders/head
                s = 1.0 if sd == 'l' else -1.0
                _aim(rig, f'upperarm_{sd}', Vector((s * 0.36, -0.45, -0.82)).normalized())
                _aim(rig, f'lowerarm_{sd}', Vector((s * 0.12, -0.78, -0.62)).normalized())
                _rot(rig, f'hand_{sd}', X, -38.0 * w_sujud)


def animate(rig, key, clips, style=None):
    """Build all requested 24 fps clips and push to Blender 5.2 NLA tracks."""
    mv = Animator(rig, style=style)
    acts = []
    for clip in clips:
        if clip == 'idle':
            acts.append(_make_clip(rig, key, 'idle', FPS * 3, mv.idle))           # 72 frames (3.0s)
        elif clip == 'walk':
            acts.append(_make_clip(rig, key, 'walk', FPS, mv.gait(False)))        # 24 frames (1.0s)
        elif clip == 'run':
            acts.append(_make_clip(rig, key, 'run', 16, mv.gait(True)))           # 16 frames (0.67s)
        elif clip == 'talk':
            acts.append(_make_clip(rig, key, 'talk', FPS * 4, mv.talk))           # 96 frames (4.0s)
        elif clip == 'gesture':
            acts.append(_make_clip(rig, key, 'gesture', 36, mv.gesture))          # 36 frames (1.5s)
        elif clip == 'pray':
            acts.append(_make_clip(rig, key, 'pray', FPS * 4, mv.pray))           # 96 frames (4.0s)
        else:
            raise ValueError(f'Unknown animation clip: {clip}')
    _push_nla(rig, acts)
    return acts
