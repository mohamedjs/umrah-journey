"""Master environment build dispatcher for umrah-journey.

Usage (from repository root):
    blender -b -P blender/env/build_all.py
    blender -b -P blender/env/build_all.py -- makkah masa

Lazily imports each requested environment module so partial builds run cleanly even
when sibling environment scripts are still being developed, writes `blender/_report_env.json`,
and prints `ENV_BUILD_OK` on success.
"""
import importlib
from pathlib import Path
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blender.lib.common import ensure_dirs, save_report  # noqa: E402

ALL_ENVS = (
    'home',
    'airport',
    'plane',
    'makkah',
    'kaaba',
    'maqam',
    'haram_mataf',
    'masa',
)


def _parse_cli_keys():
    if '--' not in sys.argv:
        return list(ALL_ENVS)
    idx = sys.argv.index('--')
    args = [a.strip() for a in sys.argv[idx + 1:] if a.strip() and not a.startswith('-')]
    return args if args else list(ALL_ENVS)


def _run_env(key):
    """Lazily import `blender.env.<key>` and invoke its `export_<key>()` entry point."""
    mod = importlib.import_module(f'blender.env.{key}')
    fn_name = f'export_{key}'
    fn = getattr(mod, fn_name, None)
    if fn is None:
        raise AttributeError(f'blender.env.{key} does not define {fn_name}()')
    res = fn()
    if isinstance(res, dict):
        res.setdefault('key', key)
        return res
    return {'key': key, 'result': res}


def main(keys=None):
    """Build requested environments, save `blender/_report_env.json`, and print `ENV_BUILD_OK`."""
    ensure_dirs()
    selected = list(keys) if keys is not None else _parse_cli_keys()
    unknown = [k for k in selected if k not in ALL_ENVS]
    if unknown:
        raise ValueError(f'Unknown environment key(s): {unknown}. Valid keys: {list(ALL_ENVS)}')

    results = []
    for key in selected:
        print(f'--- Building environment: {key} ---')
        stats = _run_env(key)
        results.append(stats)

    total_kb = round(sum(float(r.get('size_kb', 0.0)) for r in results), 1)
    all_ok = all(bool(r.get('within_budget', True)) for r in results)
    report = {
        'environments': results,
        'count': len(results),
        'total_kb': total_kb,
        'all_within_budget': all_ok,
    }
    report_path = save_report('_report_env.json', report)
    print(f'Saved environment report: {report_path} (total={total_kb:.1f}KB, within_budget={all_ok})')
    print('ENV_BUILD_OK')
    return report


if __name__ == '__main__':
    main()
