# Agent <-> Blender file bridge for umrah-journey.
# Run ONCE inside Blender (Scripting tab -> Open this file -> Run Script).
# Jobs dropped in _bridge/in/*.py are executed on Blender's main thread
# and results (stdout / error) are written to _bridge/out/<job>.json.
import contextlib
import io
import json
import os
import time
import traceback

import bpy

_FALLBACK_ROOT = '/var/www/html/old/umrah-journey/blender/_bridge'
ROOT = (
    os.path.dirname(os.path.abspath(__file__))
    if '__file__' in globals() and __file__
    else _FALLBACK_ROOT
)
if not os.path.isdir(ROOT):
    ROOT = _FALLBACK_ROOT

IN = os.path.join(ROOT, 'in')
OUT = os.path.join(ROOT, 'out')
os.makedirs(IN, exist_ok=True)
os.makedirs(OUT, exist_ok=True)


def viewport_shot(path, size=1200):
    """Save a screenshot of the largest 3D viewport (helper available to jobs)."""
    for w in bpy.context.window_manager.windows:
        areas = [a for a in w.screen.areas if a.type == 'VIEW_3D']
        if not areas:
            continue
        a = max(areas, key=lambda area: area.width * area.height)
        with bpy.context.temp_override(window=w, area=a):
            bpy.ops.screen.screenshot_area(filepath=path)
        return path
    return None


def _tick():
    try:
        jobs = sorted(f for f in os.listdir(IN) if f.endswith('.py'))
    except Exception:
        return 1.0
    for f in jobs:
        p = os.path.join(IN, f)
        with open(p, encoding='utf-8') as fh:
            code = fh.read()
        os.remove(p)
        buf = io.StringIO()
        t0 = time.time()
        res = {'job': f, 'status': 'success'}
        try:
            with contextlib.redirect_stdout(buf):
                exec(
                    compile(code, f, 'exec'),
                    {'__name__': '__bridge__', 'bpy': bpy, 'viewport_shot': viewport_shot},
                )
        except Exception:
            res['status'] = 'error'
            res['error'] = traceback.format_exc()
        res['stdout'] = buf.getvalue()[-20000:]
        res['seconds'] = round(time.time() - t0, 2)
        with open(os.path.join(OUT, f[:-3] + '.json'), 'w', encoding='utf-8') as o:
            json.dump(res, o, ensure_ascii=False)
    return 0.5


if hasattr(bpy.app.timers, 'is_registered') and bpy.app.timers.is_registered(_tick):
    bpy.app.timers.unregister(_tick)
bpy.app.timers.register(_tick, persistent=True)

with open(os.path.join(OUT, '_hello.json'), 'w', encoding='utf-8') as o:
    json.dump(
        {'status': 'bridge up', 'blender': bpy.app.version_string, 'file': bpy.data.filepath},
        o,
    )
print('Blender bridge running ->', ROOT)
