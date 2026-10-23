# GrowPatch: requested bounds for unmasked resume growth

**PASS: 22/22 primary native processes and the separate 3/3 public-fixture forward-replay processes completed with exit zero and their required gates passed; inputs/binaries were unchanged. One earlier incomplete watchdog timeout is retained separately. Acceptance or an award is not implied.**

The small change enforces the already selected extra rows/columns at the shared candidate gate. It retains the 25-cell work-grid context for optimization. The product diff is six inserted lines and one removed declaration; no scheduling or border implementation from PR #2133 or #2134 is incorporated. #2133 already describes the rectangular-path limitation.

## Confirmed current observations

All three designated crops completed their six baseline/fixed processes and comparison gates. Each produced the following saved valid-point counts:

| Request | Unmodified baseline | Fixed | Endpoint |
|---|---:|---:|---|
| Zero extra rows/columns | 81 valid, 56 outside request | 25 valid, 0 outside | Fixed retains the original 25 XYZ values with matching dtype and bytes |
| Right only, one extra column, no extra rows | 40 valid: 15 new, of which 10 outside request | 30 valid: 5 permitted new, 0 outside | Permitted progress remains; larger counts are not a quality gain |
| Wider positive control | 81 valid, 56 permitted new, 0 outside | Same | Full decoded XYZ/generations arrays, including invalid cells, plus scale/grid offset match |

The 18 main processes (three crops × two variants × three profiles) and four supplemental controls all completed. The disable-grid-expansion positive-extra control retains the explicit one-column request: baseline 40 valid / 10 outside, fixed 30 valid / five permitted new / zero outside. Fresh-seed baseline and fixed each produced 36 valid points spanning generations 1–3 in explicit-seed mode; raw XYZ/generation TIFF bytes and decoded dtype/shape/bytes, plus scale, match. Incidental UUID/time/path metadata is not an equality target. The separate public artifact-forward replay also passed: 25, 30 and 81 valid points for fill-zero, right-one and wider control, respectively, with zero out-of-request points and unchanged fixture input bytes. It confirms native consumption of the shipped reconstruction recipe on the same development crop; it does not change the primary suite's identity.

“81 valid saved points” does not mean the TIFF file is 9×9: saved TIFFs also contain an invalid border. In the development baseline fill and wider control, the valid cells span original row/column coordinates `[-2,6] × [-2,6]`. The baseline fill failure establishes 56 additional valid cells outside the request. The checker's combined fill-preservation message does not separately establish movement of the original 25 XYZ points.

## Earlier incomplete attempt and the external time budget

The first attempt (`verification-runs/`) contained one baseline process. It was active (25→49 valid points) but did not finish within the 120-second watchdog. Its own child was killed and reaped, the suite reported `INFRASTRUCTURE_ERROR`, and no complete TIFF endpoint was available. Original protocol, summary, process receipt, parameters, captured output and unchanged-input snapshots are retained under `protocol-history/` and `first-attempt/`.

The next attempt uses a 600-second external watchdog. The target, inputs, numerical settings, losses, generations, thread count and seed were not relaxed. Protocol revision 2 is bound by SHA-256 `0159cb02b2c2e5655939e569f9edb2d942a3a3e9aea34dd524f5ab7de7a45fde`; the original revision remains available. The first r2 baseline fill completed in 103.687 seconds. The cause of runtime variation is **not established**; both compared builds used `-O0 -g0` and the same active loss/EDT configuration. Neither the timeout nor the timing differences are presented as a code defect, new numerical workload, or speedup. See [the scoped runtime comparison](runtime-timeout-review.json).

This incomplete process is counted separately from the planned 22 completed processes. The later three-profile public replay reuses the same carrier and is also counted separately: 25 successful native processes plus one earlier incomplete attempt, not 26 successful processes or independent scrolls. [Completion record](verification-completion.json).

## Source and build identity

The native build used upstream `e2254ebe0168a232e5ba7b94997c749b4e6a4544`. Main subsequently advanced to `6f2024569404a46b0f008eee292773945c07a684`, changing only `foundation/`. The entire relevant `volume-cartographer` subtree is identical at both pins: Git tree `c48bb8937fd96bc0a6852e13fccc8f4968301326`. This is source-subtree equality, not a claim that root-revision metadata was rebuilt at the later pin. [Source comparison](source/main-movement.json), [subtree identity](source/subproject-equivalence.json).

Fresh current core/tracer dependencies and official CLI source were built on Windows/UCRT64 GCC 16.1, Debug `-O0 -g0`. An existing third-party prefix was reused; this is an isolated headless native comparison, not a full GUI build or a Linux/macOS runtime test. The [actual build audit](build/actual-build-audit.json) records 79 observed C/C++ objects from 78 unique sources and repository dependency hashes. [Build instructions](build/README.txt), the [headless CMake adapter](build/verification-targets.cmake), executed adapter version and small configure/build logs are included. Large completion dumps and linkmaps remain local; their hashes/audit results are retained rather than silently replaced with a claim that those full files are bundled.

The public checker is byte-identical to the executed canonical checker: SHA-256 `d5b2438df5ad213c705a8551571e9600b42aae33e126b56706457a395d0ebda9`. The packager rejects a stale copy and binds the published checker, raw summary, all selected process identities, actual binaries/parameters and equal input-before/after mappings.

## Real input and exact reconstruction

PHerc0139 volume `20250728140407`, 9.362 µm: public m7 surface prediction and published mesh `20260311000000-w023_202603112281`. Three real 5×5 crops have source centers `(157,177)`, `(147,177)`, `(157,187)`. They share one prediction carrier. This is not raw CT or three independent datasets.

Source XYZ points are retained under the exactly reversible integer XYZ translation `(3456,3456,4224)`. No geometry holes are inserted. The fixture generation channel is newly initialized to one, and UUID/bounding-box/provenance metadata is generated for this bounded test; it is not a preserved public original tracing history. Original download bytes, reconstructed fixture serialization and decoded XYZ identity are distinct checks.

The final frozen public fetch recipe completed in a new output directory: 43 original files / 10,919,380 bytes hash-verified, with all 15 reconstructed TIFF/meta files byte-identical to the historical fixtures. A separate direct file comparison confirmed those 15 matches. [Reconstruction summary](public-reproduction-summary.json), [final process](final-fetch-process.json), [final fetch receipt](fresh-fixture-final-validation/reconstruction-receipt.json).

Earlier preparation phases remain separately described in that summary: a local path-check rejection after 42 downloads, the one missing 24-byte object fetched followed by a CRLF serialization mismatch, and local-only corrected reconstruction. Those phases are not portrayed as one clean run. A later clean final run of the frozen script/spec independently passed. No old private archive is required or claimed to be publicly downloadable.

## Reproduce on an already built current official CLI

Use existing Python ≥3.9, NumPy and Pillow. The fetcher requests only the explicit public S3 objects in `fixture-sources.json`, at most four concurrently; it installs nothing and does not decode the full prediction volume. The checker starts no download or build.

```text
python fetch_real_fixture.py --output /new/path/real-fixture
python check_growpatch_requested_bounds.py --binary /path/to/vc_grow_seg_from_seed --fixture-root /new/path/real-fixture --output /another/new/path/results --timeout 600
```

The explicit `--timeout 600` changes the external process watchdog. The executed checker's default remains 120; its bound source is unchanged. Run baseline and fixed into separate new output directories. Caller-supplied matching real input is supported with `--volume`, `--resume`, `--params` instead of `--fixture-root`. Effective parameters and argv are saved; `--rng-seed 2104`, one thread, `growth_scale=0`, no rewind/inpaint and fixed small generation counts remain explicit.

The separate observer reads saved TIFFs and metadata grid offsets, not a candidate self-report. It checks requested-grid extents, original validity, exact fixed fill-zero coordinate preservation, positive progress, generations and unchanged inputs. Native exit zero alone is insufficient. The baseline checker reports the expected request violations while its native CLI processes exit zero; a passing comparison suite does not mean the baseline obeyed those requests. The [source patch](requested-resume-bounds.patch) and checker are included beside this README. The main PR description will pin the final evidence commit.

## Review material, scope and licenses

`native-results.zip` will contain only the explicit completed current 22-process members, with complete selected logs/parameters/XYZ/generations/metadata, CRC and extracted-byte SHA verification. The first timeout and the optional later three-profile public replay stay outside that ZIP. `MANIFEST.json` and `INPUT_MEMBER_PLAN.json` are the final member/byte authority; original-source and emitted hashes distinguish any path-only redaction. Downloaded fixture bytes, caches, binaries and old ZIPs are excluded.

The SVG shows actual saved raster-cell occupancy. [Captured CLI output](captured-cli-output.html) is provided as complete saved text/HTML. Original stdout hashes identify the source bytes; any emitted path-only redaction is separately bound in the manifest. The SVG was inspected through a saved PNG rendering, with rendering source/receipt supplied alongside that additional image. A policy block prevented local browser navigation; no browser screenshot, native terminal-window recording or GUI execution is claimed. The PR template personal-verification checkbox remains unconfirmed.

Existing nonempty allowed-growth masks already prevent the exterior growth. The added boundary protection concerns the reachable unmasked CLI path; normal GUI resume reachability was checked in source only, without executing the GUI. It enforces an existing requested geometry boundary, enabling localized bounded refinement without manually constructing a growth mask or post-cropping unwanted extra geometry. The existing masked workflow was already possible. Any reading benefit is indirect and unquantified. It is not a new reading method or a quantified improvement in text discovery, physical sheet accuracy, ink, anatomy, or readability. No runtime coarse-growth/inpaint, cross-platform, novelty, adoption or prize claim follows.

PR #2133's known limitation is credited; neither its scheduling changes nor #2134's border implementation is included. Data attribution and the separate root-MIT / volume-cartographer-GPLv3 texts are preserved in [DATA-ATTRIBUTION.md](DATA-ATTRIBUTION.md) and [LICENSE-NOTICE.md](LICENSE-NOTICE.md). Existing VC code is not relicensed. Implementation and reporting used AI assistance.
