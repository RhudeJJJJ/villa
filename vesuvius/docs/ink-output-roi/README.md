# Context-preserving regional output for flat ink inference

Use `--roi ROW_START ROW_STOP COL_START COL_STOP` to write only a selected rectangle without changing its parent CT tiles or normalization. Coordinates are half-open rows/columns at the selected resolution, not XYZ or physical micrometers.

```bash
python -m vesuvius.ink_detection.inference.infer surface.zarr step-075000.pth roi.tif \
  --roi 2328 2408 2712 2792 --stride 64 --blend-mode hann \
  --batch-size 1 --num-workers 0 --no-compile
```

The TIFF is 80×80. `roi.tif.roi.json` records parent dimensions, resolution, ROI bounds, selected layers and tiling. Original global tile origins, surrounding CT and per-tile normalization are retained; contributions are clipped only when accumulated into the output. Reusing the path for full-frame output invalidates the previous ROI sidecar before replacing the TIFF.

## Fair comparison and measured usefulness

The current full-parent `--mask-path` workflow already produces the same regional pixels and uses the same number of model tiles. This opt-in addition avoids constructing a full-frame mask and writing/cropping a full-frame result. Manual equivalents were already possible.

| Completed real CLI example | Masked full TIFF | ROI TIFF | ROI sidecar | Reduction including sidecar |
|---|---:|---:|---:|---:|
| PHerc.139 w035 | 415,490 bytes | 4,571 bytes | 562 bytes | 80.94× |
| PHerc.841 w00 | 270,633 bytes | 4,696 bytes | 562 bytes | 51.47× |

These are stored compressed-file sizes, not peak RAM or speed measurements. Existing masks already save model tiles. No latency advantage is claimed.

## Frozen real-data evidence

Eight reference-qualified regions were fixed before new CT/model predictions: four PHerc.139 w035/w039 and four PHerc.841 w00. The unchanged public ink_9um seed42 step75000 checkpoint gives mean AUC 0.972882 with parent context, 0.637719 with naive input cropping, and 0.653204 with the existing normalization/zero-padding fix. Parent-context outputs match Main masked inference exactly in the recorded float32 and encoded checks. Reflection padding is a strong control (mean 0.937549), and edge padding wins one PHerc.841 case. See [every case](results.csv), [all-case panels](all-cases.png), [all controls](padding-controls.png), and [methods and limitations](methods.md).

**Independent physical ink improvement is not established.** PHerc.139 occurs in recorded model training material. PHerc.841 is absent from that recorded provenance, but its transferred labels have unknown original annotation-scan provenance. A separately prespecified two-region Fragment1 independent-IR test FAILED: mean parent-context AUC 0.397427 versus 0.726020 for the existing normalization fix. Its aggregate result and exact frozen protocol are retained here. No new letters, universal context advantage, new detector or SOTA superiority is claimed.

## Validation and reproduction

Base: `ScrollPrize/villa@d99d1e978fcc4bf6fb4681f20fe6348450898453`.

The original v1 experiment includes 10 complete checkpoint CLI processes, 57 tests and a fresh extraction/forward replay. A later technical review reproduced stale ROI metadata when overwriting a prior ROI TIFF with a full-frame result, then fixed the lifecycle. **59 v2 tests and two additional complete checkpoint CLI processes pass**, with unchanged ROI/full pixels and no stale sidecar. These two processes reuse one already-frozen context and are regression checks, not new independent efficacy evidence. Total recorded checkpoint predictions: 254, below the original cap of 256. No training.

```bash
pytest -q tests/ink_detection/test_flat_inference.py \
  tests/ink_detection/test_inference_boundaries.py \
  tests/ink_detection/test_roi_inference.py \
  tests/ink_detection/test_roi_output_metadata.py
```

The real-CT regression fixture and source metadata are in `tests/ink_detection/fixtures/ink_roi_case.{npz,json}`. The metadata test uses its saved logits; it is not a new checkpoint efficacy test. Complete checkpoint replay was separately executed with 0 missing/unexpected weights in both additional processes. Recorded environment: Python 3.12, NumPy 2.3.5, PyTorch 2.9.1 CPU, Windows. These results do not certify all GPUs, TTA, distributed batches or supported-platform CI.

Public checkpoint: [ink_9um](https://huggingface.co/scrollprize/ink_9um/tree/7109667e2607db1b90c37c8b09cb876ea7fe7bb1/hybrid_3d2d-seed42), revision `7109667e2607db1b90c37c8b09cb876ea7fe7bb1`, SHA256 `e635558ae6a1a807a7e5ec1e83adfd45bc3c0ac53883ea43f1d4e085d62a9cab`. Weights are not included.

The full versioned local evidence package has SHA256 `d331cdf54f639190549be38b5b91baa95ca71df287e0140e8f406c24aad63688` (91,296,168 bytes; all 719 member hashes/CRCs verified). It is not uploaded by this source branch; the public source branch includes the real regression fixture, complete case/control scores, figures, protocols, source metadata and aggregate receipts. Do not treat the package hash as a public download or independent review. Sources/commands below allow a reviewer to inspect the real example; the full offline evidence archive remains separately retained.

## Prior work and terms

Padding normalization was already reported in [#1481](https://github.com/ScrollPrize/villa/issues/1481) and implemented in [#1483](https://github.com/ScrollPrize/villa/pull/1483), [#1646](https://github.com/ScrollPrize/villa/pull/1646), [#1773](https://github.com/ScrollPrize/villa/pull/1773). Global-grid ROI preservation already appears in [#1247](https://github.com/ScrollPrize/villa/pull/1247). This change integrates coordinate-aware output ROIs into the current flat ink CLI; it claims neither first discovery of those principles nor a new model.

Software changes use the repository MIT license. The real fixture and derived public-scroll panels retain Vesuvius Challenge attribution and source terms, CC-BY-NC 4.0 unless an individual asset says otherwise: [data formats](https://scrollprize.org/data_segments). They are not relicensed as MIT software. Exact native CT source URLs and hashes are in the fixture metadata and fresh case receipts. Raw/derived legacy Fragment1 CT/IR/labels are excluded under [the source server's distribution restrictions](https://dl.ash2txt.org/LICENSE.txt); only aggregate scores/protocol metadata are published. EduceLab-Scrolls/University of Kentucky and Parsons et al. (2023), [arXiv:2304.02084](https://doi.org/10.48550/arXiv.2304.02084), are credited for that separate negative follow-up.

## Contributor motivation and review

Human-written motivation from Jonas, quoted from his original task:

> Ein belegter Toolfix kann für Progress Prizes relevant sein; entscheidend ist sein Vorteil gegenüber bestehenden Lösungen.

> Greife an: einen nachgewiesenen Zusatznutzen gegenüber bestehenden Lösungen auf realen Scroll-Daten.

After receiving the corrected v2 package and technical review, Jonas confirmed: **“Ich bestätige die Eigenprüfung”** (20 October 2026). This is the contributor’s personal review confirmation. Code, experiments, technical self-review and the surrounding English explanation were AI-assisted. The human quotations are not generated translations; no independent external review is asserted.
