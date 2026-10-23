Isolated current Windows native comparison

Purpose
  Build the e2254ebe0168a232e5ba7b94997c749b4e6a4544 native vc_core/vc_tracer
  dependency graph and current official CLI source twice: ordinary upstream and
  the complete candidate GrowPatch translation unit before the upstream archive.
  Product sources are not edited by these adapters. This is a headless comparison,
  not a complete GUI/application or supported-platform validation.

Initial execution (only once in this fresh work area)
  python -B -X utf8 build-tools/build_current.py

The existing installed full-cpp/prefix/ucrt64 is read as a third-party prefix.
The current declared vc_delta3d v0.2.0 is fetched in build-current/_deps and built
there; no bootstrap or installation is performed. All native jobs use --parallel 1,
GCC 16.1, Debug -O0 -g0 and current CMake target dependencies.

verification-targets.cmake creates a new headless CLI target from the official
current apps/src/vc_grow_seg_from_seed.cpp. The fixed alternative-TU archive is a
test overlay, not another product module. Linkmaps must establish that the fixed
link did not extract the original GrowPatch archive member a second time.

Receipts and command sources
  build-receipts/binding.json: initial source/environment/space snapshot.
  build-receipts/configure.json and build.json: complete invocation, PID, timing,
    exit code and retained-log hash; RUNNING is not a completion or failure.
  build-current/compile_commands.json and build.ninja: exact compile/link commands.
  build-receipts/candidate-precompile-normalization.json: parent EOF-only correction
    before candidate compilation; initial source hash is retained, not overwritten.
  build-receipts/completion.json: binary and map hashes plus vc_delta3d tag binding.
  build-receipts/compiled-source-inventory.json: sources appearing in the generated
    compile-command database; this inventory alone does not prove every target ran.
  build-receipts/GrowPatch-compile-argument-comparison.json: full paired arguments.
  build-receipts/memory-observations.jsonl: global memory samples; other activity can
    change them, so these are not isolated measurements of this build's memory use.

The adapters refuse to overwrite initial operation receipts. Do not rerun a build
because a tool observer returned no new output: first inspect its existing handle,
receipts and actual own process. A failed configure/build and any repaired adapter
need separately named continuation receipts and a specific new verification reason.

Bounded foreground observation
  python -B -X utf8 build-tools/observe_current.py
This appends status/memory samples every 20 seconds for at most 20 minutes and
stops on the observed build completion. It controls no processes and establishes
no timer or scheduled task. Runtime replay and its acceptance remain separate.
