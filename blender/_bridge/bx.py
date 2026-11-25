#!/usr/bin/env python3
"""Send a Python job to the running Blender bridge and wait for the result.

Usage:
    python3 bx.py job.py [timeout_s]
    python3 bx.py - [timeout_s]      # read job source from stdin
"""
import json
import os
import sys
import time
import uuid

_FALLBACK_ROOT = '/var/www/html/old/umrah-journey/blender/_bridge'
ROOT = (
    os.path.dirname(os.path.abspath(__file__))
    if '__file__' in globals() and __file__
    else _FALLBACK_ROOT
)
if not os.path.isdir(ROOT):
    ROOT = _FALLBACK_ROOT

if len(sys.argv) < 2:
    print('Usage: python3 bx.py <job.py | -> [timeout_s]', file=sys.stderr)
    sys.exit(2)

src = sys.stdin.read() if sys.argv[1] == '-' else open(sys.argv[1], encoding='utf-8').read()
tmo = float(sys.argv[2]) if len(sys.argv) > 2 else 170.0
name = time.strftime('%H%M%S') + '_' + uuid.uuid4().hex[:6]

os.makedirs(os.path.join(ROOT, 'in'), exist_ok=True)
os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)

tmp = os.path.join(ROOT, 'in', name + '.tmp')
with open(tmp, 'w', encoding='utf-8') as fh:
    fh.write(src)
os.rename(tmp, tmp[:-4] + '.py')

out = os.path.join(ROOT, 'out', name + '.json')
t0 = time.time()
while not os.path.exists(out):
    if time.time() - t0 > tmo:
        print('TIMEOUT (job may still be running):', name)
        sys.exit(2)
    time.sleep(0.3)

time.sleep(0.1)
with open(out, encoding='utf-8') as fh:
    r = json.load(fh)
print(r.get('stdout', ''))
print('status:', r['status'], r.get('seconds'), 's')
if r['status'] != 'success':
    print(r.get('error'))
    sys.exit(1)
