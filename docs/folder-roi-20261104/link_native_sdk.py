"""Give byte-identical generated SDK headers their source file identity.

Local build adapter for NativeTargets.cmake's Windows copy fallback. Never edit
these headers while linked; recheck this receipt after the build. A reconfigure
may recreate copies, so rerun the check only after inspecting the actual state.
"""
from pathlib import Path
import hashlib
import json
import os

WORK=Path(__file__).resolve().parent
SOURCE=(WORK/"villa-upstream/vc_reader/src/cpp").resolve(strict=True)
SDK=(WORK/"native-build/include/vc_reader/native").resolve(strict=True)
assert SOURCE.is_relative_to(WORK.resolve()) and SDK.is_relative_to(WORK.resolve())
assert SOURCE.drive.lower()==SDK.drive.lower()
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
items=[]
for target in sorted(SDK.rglob("*")):
    if not target.is_file(): continue
    assert not target.is_symlink()
    source=(SOURCE/target.relative_to(SDK)).resolve(strict=True)
    assert source.is_relative_to(SOURCE) and target.resolve(strict=True).is_relative_to(SDK)
    first,second=digest(source),digest(target)
    assert first==second,(source,target)
    items.append(dict(source=str(source),target=str(target),bytes=source.stat().st_size,sha256=first,before_samefile=os.path.samefile(source,target)))
for item in items:
    source,target=Path(item["source"]),Path(item["target"])
    if not os.path.samefile(source,target):
        temporary=target.with_name(target.name+".identity-link")
        assert not temporary.exists()
        os.link(source,temporary)
        os.replace(temporary,target)
    assert os.path.samefile(source,target) and digest(source)==item["sha256"] and digest(target)==item["sha256"]
    item["after_samefile"]=True
receipt=dict(format="vc-reader-local-sdk-identity-adapter",status="applied_bytes_unchanged",count=len(items),
    reason="Current upstream NativeTargets expects one header identity; Windows symbolic-link fallback copied headers and GCC reported duplicate definitions.",
    limit="Generated build outputs only; no source edits. Recheck source hashes after build; a CMake reconfigure can recreate copies.",headers=items)
(WORK/"native-build-receipts/header-identity.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps(dict(status=receipt["status"],count=len(items),bytes=sum(x["bytes"] for x in items),all_samefile=True)))
