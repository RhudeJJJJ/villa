"""Additional read-only build evidence; writes only new audit receipts."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent.parent
BUILD=ROOT/'build-current'
RECEIPTS=ROOT/'build-receipts'
OLD=Path('C:/Users/jonas/Documents/Codex/2026-10-16/hier-in-diesem-chat-wollen-wir/targets/VC-GROW-2104/full-cpp')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    assert not path.exists(), 'Retain earlier audit receipts'
    path.write_text(json.dumps(value,indent=2)+'\n')

completion=json.loads((RECEIPTS/'completion.json').read_text())
assert json.loads((RECEIPTS/'build.json').read_text())['exit_code']==0
correction=json.loads((RECEIPTS/'candidate-precompile-normalization.json').read_text())
assert sha(ROOT/'candidate/GrowPatch.cpp')==correction['candidate_sha256']==completion['candidate_sha256']
commands=json.loads((BUILD/'compile_commands.json').read_text())
built=set()
for line in (BUILD/'.ninja_log').read_text().splitlines():
    if line.startswith('#'): continue
    fields=line.split('\t')
    if len(fields)>=5: built.add(str((BUILD/fields[3]).resolve()).lower())
rows=[]
for command in commands:
    args=shlex.split(command['command'],posix=False)
    if '-o' not in args: continue
    obj=Path(command['directory'])/args[args.index('-o')+1]
    path=Path(command['file'])
    if str(obj.resolve()).lower() in built and path.suffix.lower() in {'.c','.cpp','.cc','.cxx'}:
        rows.append({'source':str(path),'source_sha256':sha(path),'object':str(obj.resolve()),'object_sha256':sha(obj)})
save(RECEIPTS/'actual-built-translation-units.json',rows)
def normalize(command):
    args=shlex.split(command,posix=False)
    for token in ['-o','-c']:
        i=args.index(token);del args[i:i+2]
    return [('-I'+str(Path(a[2:]).resolve()).lower()) if a.startswith('-I') else a for a in args]
pair=json.loads((RECEIPTS/'GrowPatch-compile-argument-comparison.json').read_text())
equivalent=normalize(pair['original']['command'])==normalize(pair['fixed']['command'])
assert equivalent,'Paired translation units use different resolved compile arguments'
map_checks={}
for variant,item in completion['binaries'].items():
    text=Path(item['map']).read_text(errors='replace')
    assert str(OLD/'build').replace('\\','/').lower() not in text.replace('\\','/').lower()
    map_checks[variant]={'no_old_build_graph_path_in_linkmap':True,'map_sha256':sha(Path(item['map']))}
dep=subprocess.run([str(OLD/'prefix/ucrt64/bin/ninja.exe'),'-C',str(BUILD),'-t','deps'],capture_output=True,text=True)
assert dep.returncode==0
deps_log=RECEIPTS/'ninja-deps.txt'
assert not deps_log.exists()
deps_log.write_text(dep.stdout,encoding='utf-8',newline='\n')
source=ROOT/'villa/volume-cartographer'
headers={}
for line in dep.stdout.splitlines():
    if not line.startswith('    '): continue
    p=Path(line.strip())
    try: rel=p.relative_to(source)
    except ValueError: continue
    headers[rel.as_posix()]={'bytes':p.stat().st_size,'sha256':sha(p)}
save(RECEIPTS/'actual-repository-dependency-inventory.json',headers)
result={'status':'PASS_ACTUAL_BUILD_AUDIT','actual_c_cpp_translation_unit_objects':len(rows),
        'unique_c_cpp_sources':len({r['source'] for r in rows}),
        'actual_repository_dependency_files':len(headers),
        'ninja_deps_exit_code':dep.returncode,'ninja_deps_full_output_sha256':sha(deps_log),
        'resolved_paired_compile_arguments_identical':equivalent,
        'include_path_equivalence_rule':'Resolve the sole core/../libs/edt versus libs/edt directory spelling; keep argument order and all other tokens.',
        'candidate_frozen_sha256':correction['candidate_sha256'],'map_checks':map_checks,
        'translation_unit_inventory_sha256':sha(RECEIPTS/'actual-built-translation-units.json'),
        'repository_dependency_inventory_sha256':sha(RECEIPTS/'actual-repository-dependency-inventory.json'),
        'own_directories_logical_bytes':{name:sum(p.stat().st_size for p in (ROOT/name).rglob('*') if p.is_file()) for name in ['build-current','build-tools','build-receipts']},
        'observed_free_bytes_after':shutil.disk_usage(ROOT).free,
        'storage_scope':'Logical own-file bytes and global observed free space; not allocated-byte measurements or attribution of concurrent foreign writes.',
        'scope':'Observed Ninja objects and dependencies after the successful current native build. Hash identity does not establish runtime correctness or supported-platform portability.'}
save(RECEIPTS/'actual-build-audit.json',result)
print(json.dumps(result),flush=True)
