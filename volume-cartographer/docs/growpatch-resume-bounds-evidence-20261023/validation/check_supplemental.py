#!/usr/bin/env python3
"""Run four opt-in native controls for the requested GrowPatch resume bounds.

Requires two existing vc_grow_seg_from_seed binaries, numpy, Pillow, and the
archived attack_20261020 fixture root. This script does not build or download.
Exit 0: all declared gates passed; exit 1: a completed-output gate was unmet;
exit 2: input, execution, timeout, or output-decoding failure. A baseline bounds
violation is expected evidence, not a failure of the fixed implementation.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from PIL import Image


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def inventory(paths):
    result = {}
    for path in paths:
        files = sorted(path.rglob("*")) if path.is_dir() else [path]
        for file in files:
            if file.is_file():
                result[str(file)] = {
                    "bytes": file.stat().st_size, "sha256": digest(file)
                }
    return result


def read_surface(path):
    bands = {}
    for name in ("x", "y", "z", "generations"):
        with Image.open(path / (name + ".tif")) as image:
            bands[name] = np.array(image)
    shape = bands["x"].shape
    if len(shape) != 2 or any(value.shape != shape for value in bands.values()):
        raise ValueError("Expected matching 2-D xyz/generations TIFFs: " + str(path))
    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    if meta.get("format") != "tifxyz":
        raise ValueError("Expected tifxyz output: " + str(path))
    valid = bands["x"] != -1
    if not valid.any() or any(not np.isfinite(bands[name][valid]).all() for name in "xyz"):
        raise ValueError("Empty/non-finite surface: " + str(path))
    return bands, meta


def inspect_positive_extra(path, original, start_gen):
    bands, meta = read_surface(path)
    offset = meta.get("grid_offset")
    if not isinstance(offset, list) or len(offset) != 2 or any(type(v) is not int for v in offset):
        raise ValueError("Expected integer grid_offset [column,row]")
    rows, cols = original["x"].shape
    valid = bands["x"] != -1
    rr, cc = np.nonzero(valid)
    rr = rr - offset[1]
    cc = cc - offset[0]
    # Positive grow_extra_cols=1 is retained despite disabled expansion. The
    # larger grow_max_extra_{cols,rows}=4 must both be ignored. Right-only
    # directions narrow the symmetric permitted extra rectangle to its right.
    allowed = (rr >= 0) & (rr < rows) & (cc >= 0) & (cc < cols + 1)
    outside_original = (rr < 0) | (rr >= rows) | (cc < 0) | (cc >= cols)
    violations = []
    if not allowed.all():
        violations.append("valid point outside one permitted right column and zero extra rows")
    if not np.any(cc == cols):
        violations.append("positive grow_extra produced no permitted right-column growth")
    r0, c0 = offset[1], offset[0]
    if r0 < 0 or c0 < 0 or r0 + rows > valid.shape[0] or c0 + cols > valid.shape[1]:
        violations.append("original mesh rectangle missing from output")
    elif not valid[r0:r0 + rows, c0:c0 + cols].all():
        violations.append("original valid point missing from output")
    if np.any(bands["generations"][valid] == 0):
        violations.append("valid point has zero generation")
    if np.any(bands["generations"][valid][outside_original] <= start_gen):
        violations.append("new point does not have a later generation")
    if meta.get("vc_gsfs_mode") != "resume":
        violations.append("CLI metadata does not confirm resume mode")
    return {
        "valid_points": int(valid.sum()),
        "new_points": int(outside_original.sum()),
        "permitted_right_column_points": int((cc == cols).sum()),
        "outside_requested_grid": int((~allowed).sum()),
        "grid_offset": offset,
        "extent_in_original_rc": [int(rr.min()), int(rr.max()), int(cc.min()), int(cc.max())],
        "violations": violations,
        "passed": not violations,
    }


def inspect_fresh(path, seed):
    bands, meta = read_surface(path)
    valid = bands["x"] != -1
    generations = bands["generations"][valid]
    violations = []
    if int(valid.sum()) < 4:
        violations.append("fresh seed did not retain the initial four vertices")
    if np.any(generations == 0) or np.any(generations >= 4):
        violations.append("fresh valid-point generations are outside [1,4)")
    if meta.get("vc_gsfs_mode") != "explicit_seed":
        violations.append("CLI metadata does not confirm explicit fresh-seed mode")
    scale = meta.get("scale")
    if not isinstance(scale, list) or len(scale) != 2 or any(not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0 for v in scale):
        violations.append("fresh output has missing/invalid surface scale")
    if meta.get("seed") != seed:
        violations.append("output metadata does not preserve the requested seed")
    if "grid_offset" in meta:
        violations.append("fresh output unexpectedly carries resume grid_offset")
    return {
        "valid_points": int(valid.sum()),
        "growth_beyond_initial_four_observed": int(valid.sum()) > 4,
        "generation_range": [int(generations.min()), int(generations.max())],
        "mode": meta.get("vc_gsfs_mode"),
        "seed": meta.get("seed"),
        "scale": meta.get("scale"),
        "violations": violations,
        "passed": not violations,
    }


def execute(binary, volume, resume, params, seed, run, env, timeout):
    run.mkdir(parents=True, exist_ok=False)
    save(run / "params.json", params)
    cache = run / "cache"
    cache.mkdir()
    child_env = dict(env, TEMP=str(cache), TMP=str(cache), TMPDIR=str(cache))
    argv = [str(binary), "--volume", str(volume), "--target-dir", str(run / "surface"),
            "--params", str(run / "params.json"), "--segment-name", "supplemental-control"]
    if resume is not None:
        argv += ["--resume", str(resume), "--resume-opt", "skip"]
    else:
        argv += ["--seed", *(str(value) for value in seed)]
    record = {
        "argv": argv, "binary_sha256": digest(binary),
        "params_sha256": digest(run / "params.json"),
        "status": "STARTING", "rng_seed": 2104, "omp_threads": 1,
    }
    save(run / "process.json", record)
    started = time.monotonic()
    with (run / "stdout.txt").open("wb") as out, (run / "stderr.txt").open("wb") as err:
        child = subprocess.Popen(argv, cwd=run, env=child_env, stdout=out, stderr=err)
        try:
            record.update(status="RUNNING", pid=child.pid)
            save(run / "process.json", record)
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if child.poll() is None:
                child.kill()
            code = child.wait()
            record["timed_out_own_child_killed_and_reaped"] = True
        except BaseException:
            if child.poll() is None:
                child.kill()
            code = child.wait()
            record.update(status="INTERRUPTED", exit_code=code,
                          wall_seconds=time.monotonic() - started)
            save(run / "process.json", record)
            raise
    record.update(status="COMPLETED", exit_code=code,
                  wall_seconds=time.monotonic() - started)
    save(run / "process.json", record)
    if code != 0 or record.get("timed_out_own_child_killed_and_reaped"):
        raise RuntimeError("Native execution failed/timed out: " + str(run / "process.json"))
    save(run / "output-files.json", inventory([run / "surface"]))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-binary", required=True, type=Path)
    parser.add_argument("--fixed-binary", required=True, type=Path)
    parser.add_argument("--fixture-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--path-prepend", action="append", default=[])
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    root = args.fixture_root.resolve(strict=True)
    volume = (root / "portable-data/prediction-roi.zarr").resolve(strict=True)
    resume = (root / "fixtures/development").resolve(strict=True)
    params_path = (root / "fixtures/development-fill-zero.json").resolve(strict=True)
    manifest = (root / "portable-data/manifest.json").resolve(strict=True)
    for name, expected in json.loads(manifest.read_text(encoding="utf-8"))["files"].items():
        file = (manifest.parent / name).resolve(strict=True)
        if not file.is_relative_to(manifest.parent) or file.stat().st_size != expected["bytes"] or digest(file) != expected["sha256"]:
            raise ValueError("Fixture manifest mismatch: " + name)
    binaries = {
        "baseline": args.baseline_binary.resolve(strict=True),
        "fixed": args.fixed_binary.resolve(strict=True),
    }
    if not all(binary.is_file() for binary in binaries.values()):
        raise ValueError("Both binaries must already exist as regular files")
    if binaries["baseline"] == binaries["fixed"]:
        raise ValueError("Use separate baseline and fixed binaries")
    inputs = [volume, resume, params_path, manifest, *binaries.values()]
    output = args.output.resolve()
    if output.exists() or any(output == path or output.is_relative_to(path) or path.is_relative_to(output) for path in inputs):
        raise ValueError("Output must be new and separate from all inputs")
    original, _ = read_surface(resume)
    if np.any(original["x"] == -1) or np.any(original["generations"] == 0):
        raise ValueError("Expected fully valid rectangular fixture with nonzero generations")
    start_gen = int(original["generations"].max())
    if start_gen > 65530:
        raise ValueError("Generation counter too close to uint16 limit")
    rows, cols = original["x"].shape
    seed = [float(original[name][rows // 2, cols // 2]) for name in "xyz"]
    if seed != [310.347412109375, 244.2255859375, 383.3359375]:
        raise ValueError("Fixture center differs from the frozen development seed")
    base = json.loads(params_path.read_text(encoding="utf-8"))
    positive = dict(base)
    positive.update(mode="resume", growth_scale=0, inpaint=False, rewind_gen=-1,
                    resume_opt="skip", cell_reopt_mode=False, thread_limit=1,
                    generations=start_gen + 4, disable_grid_expansion=True,
                    grow_extra_cols=1, grow_extra_rows=0,
                    grow_max_extra_cols=4, grow_max_extra_rows=4,
                    growth_directions=["right"])
    positive["snapshot-interval"] = 0
    fresh = dict(positive)
    fresh.update(mode="seed", generations=4, grow_extra_cols=0, grow_extra_rows=0,
                 grow_max_extra_cols=0, grow_max_extra_rows=0,
                 growth_directions=["all"])
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", VC_GROWPATCH_RNG_SEED="2104")
    env["PATH"] = os.pathsep.join(args.path_prepend + [env.get("PATH", "")])
    before = inventory(inputs)
    output.mkdir(parents=True, exist_ok=False)
    save(output / "inputs-before.json", before)
    result = {
        "scope": "One real PHerc0139 fixture; four native processes; no independent-data, physical-accuracy, inpaint, coarse-scale, or full-platform claim.",
        "completed": False, "results": {}, "gates": {},
        "fresh_seed": seed, "rng_seed": 2104, "omp_threads": 1,
    }
    try:
        for profile, params in (("disabled-positive-extra", positive), ("fresh-seed", fresh)):
            result["results"][profile] = {}
            for variant, binary in binaries.items():
                run = output / profile / variant
                record = execute(binary, volume, resume if profile == "disabled-positive-extra" else None,
                                 params, seed, run, env, args.timeout)
                observed = inspect_positive_extra(run / "surface", original, start_gen) if profile == "disabled-positive-extra" else inspect_fresh(run / "surface", seed)
                observed["wall_seconds"] = record["wall_seconds"]
                result["results"][profile][variant] = observed
                print(json.dumps({"profile": profile, "variant": variant, **observed}), flush=True)
        baseline_path = output / "fresh-seed/baseline/surface"
        fixed_path = output / "fresh-seed/fixed/surface"
        baseline_bands, baseline_meta = read_surface(baseline_path)
        fixed_bands, fixed_meta = read_surface(fixed_path)
        raw_equal = {}
        decoded_equal = {}
        for name in ("x", "y", "z", "generations"):
            raw_equal[name] = digest(baseline_path / (name + ".tif")) == digest(fixed_path / (name + ".tif"))
            left, right = baseline_bands[name], fixed_bands[name]
            decoded_equal[name] = left.dtype == right.dtype and left.shape == right.shape and left.tobytes() == right.tobytes()
        result["fresh_comparison"] = {
            "raw_tiff_bytes_equal": raw_equal,
            "decoded_dtype_shape_and_bytes_equal": decoded_equal,
            "scale_equal": baseline_meta.get("scale") == fixed_meta.get("scale"),
            "metadata_not_compared_wholesale": "UUID, elapsed time, paths and other incidental metadata are not an equality target.",
        }
        positive_result = result["results"]["disabled-positive-extra"]
        fresh_result = result["results"]["fresh-seed"]
        result["gates"] = {
            "baseline_positive_extra_reproduces_bounds_overrun": positive_result["baseline"]["outside_requested_grid"] > 0,
            "fixed_positive_extra_contract": positive_result["fixed"]["passed"],
            "baseline_fresh_output_valid": fresh_result["baseline"]["passed"],
            "fixed_fresh_output_valid": fresh_result["fixed"]["passed"],
            "fresh_raw_tiff_bytes_identical": all(raw_equal.values()),
            "fresh_decoded_bytes_identical": all(decoded_equal.values()),
            "fresh_scale_identical": result["fresh_comparison"]["scale_equal"],
        }
        result["completed"] = True
        result["passed"] = all(result["gates"].values())
    finally:
        after = inventory(inputs)
        save(output / "inputs-after.json", after)
        result["input_bytes_unchanged"] = before == after
        if before != after:
            result["passed"] = False
        save(output / "results.json", result)
        if before != after:
            raise RuntimeError("Input/binary bytes changed during supplemental run")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print("CHECK ERROR: " + str(error), file=sys.stderr)
        sys.exit(2)
