# Current review note

The methods below describe the frozen v1 scientific experiment. The v2 metadata-only revision passed 59 tests and two additional complete checkpoint CLI processes. Jonas subsequently confirmed personal review on 20 October 2026. Historical pending-review statements below refer to v1, not the current attestation. The failed independent-IR endpoint remains unchanged. See README.md for current limits.

# Method, comparison and claim boundary

## Prespecified question

Can a small regional flat-ink query preserve the original parent inference while avoiding a full-frame output? The initial need came from an80×80 ink query during the prior real GrowPatch/CT test. Its negative ink gates remain negative. This experiment is a new, explicitly declared workflow target, not a reinterpretation of that geometric comparison.

The primary `fresh-protocol.json` was frozen before new CT/model outputs. Version2 adds the stock raw-empty skip and clarifies coordinate order, before acquisition. Neither cases, scoring, gates nor comparison choices changed. Protocolv2 SHA256: f5a3234ff24968ad4774c7fe60e39be4e357abcf63fbb2aefb34c829f504547f. Case receipt SHA256: 31c218ce9e584eeba8a2a66c603195d5716be431272d4bd439949230d4cba360.

## Units and exact equivalence

For fidelity, the unit is the ordered parent-global model tile with its17 CT layers,128×128 support, robust-normalization context, fixed weights and blend map. Equality of a selected CT subarray alone is insufficient: changing context changes robust statistics and InstanceNorm features. We preserve this full computational unit and crop only after each model forward, during output accumulation.

For scoring, the unit is each prespecified64×64 core, using the same qualified reference pixels for every method. For acquisition freshness, native source objects are identified by canonical bucket/key and byte hashes, including alias checks. These equalities do not establish physical sheet identity, calibrated probability, newly readable letters or human use.

The pure planner `faithful_roi.py` is the frozen experimental candidate. The upstream patch uses existing `iter_blocks`, the existing reader/model, and a shared block-clip helper for output counts/accumulation. Complete CLI comparisons bridge this integration to the frozen arrays. No private inference implementation was copied into a parallel production module.

## Sources and selection

PHerc0139 w035/w039: native9.362µm surface volumes and native20260918 public labels on volume20250728140407. PHerc0841 w00: published2.403µm surface volume20260319124803 at XY level2; mean-pool each four Z planes, discard the incomplete final block, select central17, round to uint8. Model sampling9.612µm. Labels pool4×4: all16 pixels supervised; positive ink fraction≥.75, negative fraction0, intermediate abstains. Their transfer metadata says annotated_on=unknown.

Only reference arrays and metadata select cases: stride128 centres, SHA256 rank with seed20261020,≥90% supervision and≥128 positive/negative pixels in the core. Every required CT object is absent from recorded prior acquisition ledgers and disjoint from the other seven chosen cases. The primary139 annotations had been downloaded before; their exposure is explicit. No CT-intensity, model-score, fitted XY/normal/depth or replacement selection occurred. Eight qualified cases were obtained; unavailable=[] in the frozen receipt.

The checkpoint is fixed seed42 step75000, no EMA,508 state keys. PHerc139 w035/w039 occur in its training config; PHerc841 is absent from recorded datasets/provenance. Public annotations are separate from our candidate, but are not a certified independent physical measurement or independent3D registration. Additional independent-IR follow-up: gate **FAILED**, two frozen Fragment1 contexts. Mean AUC parent-context 0.397427, naive 0.601932, prior-zero 0.726020. This result does not admit an independent physical ink improvement or a general detector benefit. Parent-inference fidelity remains exact. Raw fragment evidence remains local/private under the source server's distribution terms; see aggregate `independent-IR-admission.json`.

## Comparators and scoring

1. Exact current Main reader/dataset: raw80×80 padded to128 then robust normalization.
2. Exact PR1773 reader/dataset: normalize source-supported80×80, normalized padding0. PR1483 has the same standard no-depth-padding placement; PR1646/1773 source matches are recorded separately.
3. Main full-parent masked schedule and actual chunk accumulator, using identical tile probability arrays. It is the strong equivalence baseline; not an independent model or a claimed inferior detector.
4. All predeclared alternatives: normalized minimum padding, raw reflection padding, raw edge padding.

Actual Main functions are AST-selected without textual rewriting for the array experiment, from pinned full source files. The exact current normalization module is bound, including its float32-copy correction; the older module is not falsely claimed byte-identical. Complete Main CLI runs subsequently construct/load the checkpoint with zero missing/unexpected keys and reproduce encoded outputs.

AUC is tie-correct and checked twice: rank-sum and direct positive-negative pair counts. All eight rows, encoded AUC, half-width cyclic-reference and transposed-reference controls are retained. Spatial correlation is substantial: some null AUCs approach.98. These controls are not null p-values, and32768 core pixels are not32768 independent experimental replications. No threshold tuning, pixel-IID inference or population generalization is made.

Gate:≥6 cases including≥3PHerc841; mean gain≥.10 against naive and≥.05 against prior-zero; nonnegative scroll-wise mean gains; all parent/nesting/encoded fidelity checks. **Passed**. Mean gains+.335163 and+.319678. Relative to reflection, gain is+.035334 overall and+.060843 on841. PHerc841 case0 favors reflection(.873006) and edge(.919264) over faithful(.854941); it is preserved as a counterfinding.

## Integration, cost and validation

Eight candidate outputs match Main masked, stock minimal-context and nested96→80 outputs at **float32 bit equality and encoded uint8 equality**. Seventy-two actual parent-context model tiles plus40 control predictions were computed. New raw CT source bytes80,805,888. Full unmasked parent tiles64,932 are an analytic count, not an executed speed benchmark.

Ten complete CLI processes on the first frozen case of each scroll all exited0: naive, Main masked, proposed ROI, proposed without ROI+mask, stock real context. All outputs match their frozen encoded arrays and backwards-compatibility controls. Parent source replicas contain every required real chunk and omit unneeded chunks; these are not complete scan downloads or unmasked whole-scroll runs.

An80×80 output has6,400 raw pixel bytes and two float32 accumulators totaling51,200 bytes, versus parent outputs19,093,600–66,083,200 raw pixels and152,748,800–528,665,600 logical accumulation bytes. Stock already chunks its active buffers. These are shape/storage comparisons, not measured peak-RAM savings. Existing masks already save model tiles. CLI wall times are single-run diagnostics and variable, including one slower proposed run; no latency improvement is claimed.

57 tests pass, including current flat-inference and boundary suites, irregular tails, small parents, one-pixel ROIs, bad coordinate frames, actual assembly of a saved real prediction, raw-empty handling and ROI CLI units. An initial test launcher had missing parent-module binding and Windows main guard; it was corrected, failed XML retained. A CRLF unified diff initially failed Git application; transport was normalized to LF and checked in a fresh minimal Git directory. Product inference code was unchanged by both harness/transport repairs.

No Ubuntu/macOS/GPU/TTA/multiworker ROI performance certificate is claimed. The current CPU tests include one upstream spawned-worker case, but that is not exhaustive distributed ROI testing. Default no-ROI full output remains the tested backward-compatible behavior.

## What is and is not submission-ready

The contribution has code, a real-data need, exact before/after examples, strong prior-art comparison, source/weight pins, negative findings, full CLI checks, regression tests, reproducible artifacts and explicit limits. It is a technical submission candidate. External acceptance, community adoption, a papyrologist's reading and human-authored relevance/code/example review have not happened. The original cross-scan2.399→2.403µm anatomical reference goal remains OPEN.
