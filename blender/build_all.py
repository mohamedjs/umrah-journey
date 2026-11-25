"""Master project build CLI for umrah-journey.

Regenerates every character GLB and every environment GLB from scratch by invoking
`blender.characters.build_all.main()` and `blender.env.build_all.main()`.

Usage (from repository root):
    blender -b -P blender/build_all.py
"""
import importlib
from pathlib import Path
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blender.lib.common import ensure_dirs  # noqa: E402


def main():
    """Run both character and environment master build pipelines."""
    ensure_dirs()

    print('=== [1/2] Building all character GLBs ===')
    char_mod = importlib.import_module('blender.characters.build_all')
    char_report = char_mod.main()

    print('=== [2/2] Building all environment GLBs ===')
    env_mod = importlib.import_module('blender.env.build_all')
    env_report = env_mod.main()

    print('ALL_BUILD_OK')
    return {'characters': char_report, 'environments': env_report}


if __name__ == '__main__':
    main()
