"""Controlled #2443 comparison; real source and real dependencies only.
Run with the pinned project's virtualenv Python after uv sync and Zarr selection.
Every pytest invocation gets a fresh process. No test assertions are changed.
"""
from __future__ import annotations
import hashlib, importlib.metadata, json, os, pathlib, platform, subprocess, sys, time
import xml.etree.ElementTree as ET

BASE = 'baf5e605bb42a3d55a62b7c5c728e0908137225c'
HEAD = '62327ddd67c48ece198dbb5ff0e25dc6af962025'
EXPECTED = {'vesuvius/src/vesuvius/ink_detection/inference/infer.py',
            'vesuvius/tests/ink_detection/test_roi_folder_identity.py'}
ROOT = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
ROI = 'tests/ink_detection/test_roi_folder_identity.py'
GEOM = [
    f'tests/neural_tracing/{f}::{t}'
    for f in ('test_fiber_trace_3d.py', 'test_sample_pipeline.py')
    for t in (
        'test_tiled_geometry_is_bitwise_identical_to_eager_geometry[1-none]',
        'test_tiled_geometry_is_bitwise_identical_to_eager_geometry[1-1d]',
        'test_tiled_geometry_is_bitwise_identical_to_eager_geometry[1-2d]',
        'test_tiled_geometry_is_bitwise_identical_to_eager_geometry[1-3d]',
        'test_tiled_geometry_is_bitwise_identical_for_training_patch_shape',
    )
]

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def installed():
    return sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions())

def xml_cases(path):
    if not path.exists():
        return None
    cases = []
    for c in ET.parse(path).getroot().iter('testcase'):
        failure, error, skipped = c.find('failure'), c.find('error'), c.find('skipped')
        state = 'failed' if failure is not None else 'error' if error is not None else 'skipped' if skipped is not None else 'passed'
        diagnostic = failure if failure is not None else error
        cases.append({'id': c.attrib.get('classname', '') + '::' + c.attrib.get('name', ''),
                      'outcome': state,
                      'message': diagnostic.attrib.get('message', '') if diagnostic is not None else ''})
    return cases

changed = set(git('diff', '--name-only', BASE, HEAD).splitlines())
if changed != EXPECTED:
    raise SystemExit(f'Unexpected source delta; refusing comparison: {sorted(changed)}')
import torch, zarr
if zarr.__version__ != '2.18.7':
    raise SystemExit(f'Wrong Zarr version: {zarr.__version__}')
if sys.version_info[:3] != (3, 14, 10):
    raise SystemExit(f'Wrong Python: {sys.version}')
packages = installed()
metadata = {'base': BASE, 'head': HEAD, 'delta': sorted(changed),
    'base_tree': git('rev-parse', BASE+'^{tree}'), 'head_tree': git('rev-parse', HEAD+'^{tree}'),
    'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
    'cpu': pathlib.Path('/proc/cpuinfo').read_text(), 'packages': packages,
    'torch': torch.__version__, 'torch_config': torch.__config__.show(),
    'torch_threads': torch.get_num_threads(), 'torch_interop_threads': torch.get_num_interop_threads(),
    'zarr': zarr.__version__, 'environment_controls': {'PYTHONHASHSEED': '0'},
    'note': 'No OMP/MKL/Torch thread override; default runtime is recorded. All arms share the same venv and runner.'}
save('environment-before.json', metadata)
results = []

def run(name, revision, args, expected_count=None):
    git('checkout', '--detach', '--force', revision)
    # Remove stale bytecode only. Do not modify sources, fixtures or test assertions.
    for d in (ROOT/'vesuvius').rglob('__pycache__'):
        for f in d.glob('*.pyc'):
            f.unlink(missing_ok=True)
    env = os.environ.copy()
    env['PYTHONHASHSEED'] = '0'
    env['PYTHONPATH'] = str(ROOT)
    env.pop('PYTEST_ADDOPTS', None)
    junit = OUT / f'{name}.xml'
    cmd = [sys.executable, '-m', 'pytest', *args, '-vv', '-rA', '-p', 'no:cacheprovider',
           '--junitxml='+str(junit), '--basetemp='+str(OUT/(name+'-tmp'))]
    start = time.time()
    print('BEGIN', name, revision, flush=True)
    with (OUT/f'{name}.log').open('w') as stream:
        try:
            p = subprocess.run(cmd, cwd=ROOT/'vesuvius', env=env, stdout=stream,
                               stderr=subprocess.STDOUT, timeout=1200)
            code = p.returncode
        except subprocess.TimeoutExpired:
            code = 124
    cases = xml_cases(junit)
    record = {'name': name, 'revision': git('rev-parse', 'HEAD'), 'command': cmd,
              'returncode': code, 'seconds': round(time.time()-start, 3), 'cases': cases,
              'expected_case_count': expected_count,
              'case_count_matches': (len(cases) == expected_count) if cases is not None and expected_count is not None else None}
    results.append(record)
    save('results.json', results)
    print('END', name, code, 'cases', None if cases is None else len(cases), flush=True)
    if installed() != packages:
        raise RuntimeError('Installed package set changed between arms; comparison invalid')
    return record

# ABBA order distinguishes consistent code effects from simple time/order drift.
for name, revision in [('base_geometry_1',BASE),('pr_geometry_1',HEAD),
                       ('pr_geometry_2',HEAD),('base_geometry_2',BASE)]:
    run(name,revision,GEOM,10)
# Same PR source, fresh process: only the eleven new ROI tests execute first.
run('pr_roi_then_geometry',HEAD,[ROI,*GEOM],21)
# Whole-suite arms preserve the original CI selection.
run('baseline_full',BASE,['tests','-m','not slow and not network'])
run('pr_full_without_new_roi',HEAD,['tests','-m','not slow and not network','--ignore='+ROI])
run('pr_full',HEAD,['tests','-m','not slow and not network'])
# Check installed environment stayed identical, and record checked-in lock bytes.
metadata['uv_lock_sha256'] = hashlib.sha256((ROOT/'vesuvius/uv.lock').read_bytes()).hexdigest()
save('environment-after.json', metadata)
lines = ['# Controlled CI comparison: #2443', '',
         'Same runner, Python 3.14.10, same installed environment, Zarr 2.18.7.', '',
         '| Arm | Exit | Passed | Failed | Errors | Skipped |', '|---|---:|---:|---:|---:|---:|']
for r in results:
    c = r['cases'] or []
    counts = {s: sum(x['outcome']==s for x in c) for s in ('passed','failed','error','skipped')}
    lines.append(f"| {r['name']} | {r['returncode']} | {counts['passed']} | {counts['failed']} | {counts['error']} | {counts['skipped']} |")
lines += ['', 'Nonzero pytest exits are recorded, not converted into passing source tests.',
          'A successful diagnostic workflow means collection completed, not that upstream CI is green.']
summary='\n'.join(lines)+'\n'
(OUT/'SUMMARY.md').write_text(summary)
print(summary,flush=True)
if 'GITHUB_STEP_SUMMARY' in os.environ:
    with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f: f.write(summary)
if any(r['returncode'] not in (0,1) or r['cases'] is None or r['case_count_matches'] is False for r in results):
    raise SystemExit('Incomplete/invalid experiment: inspect results.json and logs')
