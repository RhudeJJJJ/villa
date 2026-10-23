"""Build current native core/tracer and official CLI source in an isolated graph.

No bootstrap or installation; existing installed third-party prefix is read.
The current vc_delta3d FetchContent pin is acquired inside build-current only.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'villa/volume-cartographer'
BUILD = ROOT / 'build-current'
RECEIPTS = ROOT / 'build-receipts'
OLD = Path('C:/Users/jonas/Documents/Codex/2026-10-16/hier-in-diesem-chat-wollen-wir/targets/VC-GROW-2104/full-cpp')
PREFIX = OLD / 'prefix/ucrt64'
CANDIDATE = ROOT / 'candidate/GrowPatch.cpp'
PIN = 'e2254ebe0168a232e5ba7b94997c749b4e6a4544'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def git(*args):
    p = subprocess.run(['git', *map(str, args)], capture_output=True, text=True)
    return {'argv': ['git', *map(str, args)], 'exit_code': p.returncode,
            'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}


def run(argv, label, env):
    receipt = RECEIPTS / (label + '.json')
    assert not receipt.exists(), 'Existing operation must be inspected, never overwritten'
    log = RECEIPTS / (label + '.log')
    record = {'status': 'STARTING', 'argv': list(map(str, argv)), 'cwd': str(ROOT),
              'started_utc': now(), 'owner_pid': os.getpid(), 'owner_parent_pid': os.getppid(),
              'log_path': str(log), 'exit_code': None}
    save(receipt, record)
    started = time.monotonic()
    with log.open('wb') as stream:
        process = subprocess.Popen(record['argv'], cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        record.update(status='RUNNING', process_pid=process.pid)
        save(receipt, record)
        print(json.dumps(record), flush=True)
        code = process.wait()
    record.update(status='COMPLETED', exit_code=code, wall_time_seconds=time.monotonic()-started,
                  completed_utc=now(), log_bytes=log.stat().st_size, log_sha256=sha(log))
    save(receipt, record)
    print(json.dumps(record), flush=True)
    if code:
        print(log.read_text(encoding='utf-8', errors='replace')[-7000:], flush=True)
    return code


def audit():
    current = git('-C', SOURCE, 'rev-parse', 'HEAD')
    assert current['exit_code'] == 0 and current['stdout'] == PIN
    delta = BUILD / '_deps/vc_delta3d-src'
    delta_head = git('-C', delta, 'rev-parse', 'HEAD')
    delta_tag = git('-C', delta, 'rev-parse', 'v0.2.0^{commit}')
    assert delta_head['exit_code'] == delta_tag['exit_code'] == 0
    assert delta_head['stdout'] == delta_tag['stdout']
    maps = {}
    for variant in ['baseline', 'fixed']:
        binary = BUILD / ('bin/vc_grow_seg_from_seed_' + variant + '.exe')
        linkmap = BUILD / ('vc_grow_seg_from_seed_' + variant + '.map')
        text = linkmap.read_text(errors='replace')
        extracted = re.findall(r'(?m)^([^\n]*libvc_tracer\.a\([^\n]*GrowPatch[^\n]*\))', text)
        if variant == 'fixed':
            assert not extracted, 'Original GrowPatch extracted alongside fixed complete TU'
            assert 'libvcgrow_requested_bounds.a(' in text
        else:
            assert extracted, 'Baseline lacks original full GrowPatch archive member'
        maps[variant] = {'binary': str(binary), 'binary_bytes': binary.stat().st_size,
                         'binary_sha256': sha(binary), 'map': str(linkmap), 'map_sha256': sha(linkmap),
                         'original_GrowPatch_archive_extraction_lines': extracted}
    commands = json.loads((BUILD / 'compile_commands.json').read_text())
    inputs = {}
    for command in commands:
        path = Path(command['file'])
        if path.is_file():
            inputs[str(path)] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
    save(RECEIPTS / 'compiled-source-inventory.json', inputs)
    result = {'status': 'BUILT_CURRENT_NATIVE_COMPARISON', 'observed_utc': now(),
              'source_pin': current, 'candidate_sha256': sha(CANDIDATE),
              'delta_head': delta_head, 'delta_v020_tag_commit': delta_tag,
              'delta_cmake_sha256': sha(delta / 'CMakeLists.txt'),
              'compile_commands_sha256': sha(BUILD / 'compile_commands.json'),
              'build_ninja_sha256': sha(BUILD / 'build.ninja'),
              'compile_command_entries': len(commands), 'compiled_source_inventory_sha256': sha(RECEIPTS / 'compiled-source-inventory.json'),
              'binaries': maps, 'free_bytes_after': shutil.disk_usage(ROOT).free,
              'scope': 'Current headless core/tracer and official CLI source; two isolated comparison targets. Installed third-party prefix reused. No full GUI, installation or runtime result implied.'}
    save(RECEIPTS / 'completion.json', result)
    print(json.dumps(result), flush=True)


def main():
    BUILD.mkdir(exist_ok=True)
    RECEIPTS.mkdir(exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == 'audit':
        audit()
        return 0
    source_pin = git('-C', SOURCE, 'rev-parse', 'HEAD')
    assert source_pin['exit_code'] == 0 and source_pin['stdout'] == PIN
    assert shutil.disk_usage(ROOT).free >= 16 * 1024**3
    env = os.environ.copy()
    env['AGENTS_AGENT_MODE'] = '1'
    env.pop('AGENTS_ALLOW_INSTALL', None)
    env['PATH'] = os.pathsep.join([str(PREFIX/'bin'), 'C:/msys64/ucrt64/bin', env.get('PATH', '')])
    env['PKG_CONFIG_PATH'] = str(PREFIX/'lib/pkgconfig')
    env['GIT_CONFIG_COUNT'] = '1'
    env['GIT_CONFIG_KEY_0'] = 'core.longpaths'
    env['GIT_CONFIG_VALUE_0'] = 'true'
    env['OPENBLAS_NUM_THREADS'] = env['OMP_NUM_THREADS'] = '1'
    cmake = PREFIX/'bin/cmake.exe'
    config = [cmake, '-S', SOURCE, '-B', BUILD, '-G', 'Ninja',
              '-DCMAKE_C_COMPILER=C:/msys64/ucrt64/bin/gcc.exe',
              '-DCMAKE_CXX_COMPILER=C:/msys64/ucrt64/bin/g++.exe',
              '-DCMAKE_MAKE_PROGRAM='+(PREFIX/'bin/ninja.exe').as_posix(),
              '-DCMAKE_PREFIX_PATH='+PREFIX.as_posix(),
              '-DCMAKE_BUILD_TYPE=Debug', '-DCMAKE_CXX_FLAGS_DEBUG=-O0 -g0', '-DCMAKE_C_FLAGS_DEBUG=-O0 -g0',
              '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DBUILD_SHARED_LIBS=OFF',
              '-DVC_BUILD_APPS=OFF', '-DVC_BUILD_UI_TRACER=OFF', '-DVC_BUILD_FIBERLETS=OFF',
              '-DVC_BUILD_FLATBOI=OFF', '-DVC_BUILD_PYTHON=OFF', '-DVC_USE_PCH=OFF',
              '-DVC_TESTING=OFF', '-DVC_WINDOWS_DEBUG_INFO=OFF',
              '-DCMAKE_PROJECT_VC3D_INCLUDE='+(ROOT/'build-tools/verification-targets.cmake').as_posix(),
              '-DVCGROW_CANDIDATE_FILE='+CANDIDATE.as_posix()]
    binding = {'created_utc': now(), 'source_pin': source_pin,
               'source_GrowPatch_sha256': sha(SOURCE/'core/src/GrowPatch.cpp'),
               'candidate_sha256': sha(CANDIDATE), 'cli_source_sha256': sha(SOURCE/'apps/src/vc_grow_seg_from_seed.cpp'),
               'injection_sha256': sha(ROOT/'build-tools/verification-targets.cmake'),
               'free_bytes_before': shutil.disk_usage(ROOT).free, 'expected_own_raw_bytes_max': 6*1024**3,
               'third_party_prefix': str(PREFIX), 'prefix_access': 'existing installed files read; no install or bootstrap',
               'environment_overrides': {k: env[k] for k in ['AGENTS_AGENT_MODE','PATH','PKG_CONFIG_PATH','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS']},
               'AGENTS_ALLOW_INSTALL_present': 'AGENTS_ALLOW_INSTALL' in env,
               'build_scope': 'Full current core/tracer dependency graph and official CLI source using new headless comparison targets; alternative full GrowPatch TU is a test overlay, not a copied product implementation.'}
    assert not (RECEIPTS/'binding.json').exists()
    save(RECEIPTS/'binding.json', binding)
    if run(config, 'configure', env):
        return 1
    if run([cmake, '--build', BUILD, '--parallel', '1', '--target',
            'vc_grow_seg_from_seed_baseline', 'vc_grow_seg_from_seed_fixed'], 'build', env):
        return 1
    audit()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
