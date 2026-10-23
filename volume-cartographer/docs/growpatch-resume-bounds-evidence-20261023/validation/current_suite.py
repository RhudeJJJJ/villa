#!/usr/bin/env python3
"""Execute the frozen current-Main comparison after the native build is approved.

Planned: three profiles x two binaries x three crops, plus four supplemental
native processes. No build, download, wait loop, scheduling or foreign process
control. Import existing checkers in this process so their own native-child
timeout/reaping logic remains responsible for the native children. Exit 0 means
all declared gates passed, 1 means completed-output gates failed, and 2 means
input/execution/infrastructure failure. Only development success admits the
neighboring-crop replication, as required by verification-protocol.json.
"""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import json
from pathlib import Path
import runpy
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = Path("<fixture>")
DEFAULT_PREFIX_BIN = "<toolchain>/bin"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def inventory(paths):
    observed = {}
    for path in paths:
        files = sorted(path.rglob("*")) if path.is_dir() else [path]
        for file in files:
            if file.is_file():
                observed[str(file)] = {"bytes": file.stat().st_size, "sha256": digest(file)}
    return observed


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def invoke_checker(script, args, receipt_dir):
    receipt_dir.mkdir(parents=True, exist_ok=False)
    receipt = {"script": str(script), "script_sha256": digest(script),
               "argv": [str(script), *args], "status": "STARTING",
               "execution": "in-process checker main(); native Popen children belong to checker"}
    save(receipt_dir / "invocation.json", receipt)
    print(json.dumps({"checker_start": str(script), "arguments": args}), flush=True)
    started = time.monotonic()
    old_argv = sys.argv
    try:
        with (receipt_dir / "stdout.txt").open("w", encoding="utf-8") as out, (receipt_dir / "stderr.txt").open("w", encoding="utf-8") as err:
            with redirect_stdout(Tee(out, sys.stdout)), redirect_stderr(Tee(err, sys.stderr)):
                try:
                    namespace = runpy.run_path(str(script), run_name="growpatch_suite_checker")
                    sys.argv = [str(script), *args]
                    receipt["status"] = "RUNNING"
                    save(receipt_dir / "invocation.json", receipt)
                    code = namespace["main"]()
                except SystemExit as error:
                    code = error.code if isinstance(error.code, int) else 2
                except Exception:
                    traceback.print_exc()
                    code = 2
        receipt.update(status="COMPLETED", exit_code=code,
                       wall_seconds=time.monotonic() - started)
        save(receipt_dir / "invocation.json", receipt)
        print(json.dumps({"checker_completed": str(receipt_dir), "exit_code": code}), flush=True)
        return code
    except BaseException:
        receipt.update(status="INTERRUPTED", wall_seconds=time.monotonic() - started)
        save(receipt_dir / "invocation.json", receipt)
        raise
    finally:
        sys.argv = old_argv


def wide_pair(baseline, fixed, observer):
    left_path = baseline / "wide-control/surface"
    right_path = fixed / "wide-control/surface"
    left, left_meta = observer["read_surface"](left_path)
    right, right_meta = observer["read_surface"](right_path)
    bands = {}
    for name in ("x", "y", "z", "generations"):
        a, b = left[name], right[name]
        bands[name] = {
            "baseline_dtype": str(a.dtype), "fixed_dtype": str(b.dtype),
            "baseline_shape": list(a.shape), "fixed_shape": list(b.shape),
            "baseline_decoded_sha256": hashlib.sha256(a.tobytes()).hexdigest(),
            "fixed_decoded_sha256": hashlib.sha256(b.tobytes()).hexdigest(),
            "identical_dtype_shape_and_bytes": a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes(),
            "baseline_tiff_sha256": digest(left_path / (name + ".tif")),
            "fixed_tiff_sha256": digest(right_path / (name + ".tif")),
        }
    return {
        "bands": bands,
        "grid_offset_equal": left_meta.get("grid_offset") == right_meta.get("grid_offset"),
        "scale_equal": left_meta.get("scale") == right_meta.get("scale"),
        "passed": all(item["identical_dtype_shape_and_bytes"] for item in bands.values())
                  and left_meta.get("grid_offset") == right_meta.get("grid_offset")
                  and left_meta.get("scale") == right_meta.get("scale"),
        "scope": "Complete decoded arrays including invalid cells; whole meta.json equality is not required.",
    }


def native_process_inventory(output):
    processes = []
    for file in sorted(output.rglob("process.json")):
        record = json.loads(file.read_text(encoding="utf-8"))
        processes.append({"record": str(file), "status": record.get("status"),
                          "exit_code": record.get("exit_code"), "pid": record.get("pid"),
                          "timed_out": bool(record.get("timed_out_killed_and_reaped") or record.get("timed_out_own_child_killed_and_reaped"))})
    return processes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-binary", type=Path, default=ROOT / "build-current/bin/vc_grow_seg_from_seed_baseline.exe")
    parser.add_argument("--fixed-binary", type=Path, default=ROOT / "build-current/bin/vc_grow_seg_from_seed_fixed.exe")
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--path-prepend", action="append")
    args = parser.parse_args()
    protocol = (ROOT / "verification-protocol.json").resolve(strict=True)
    frozen = json.loads(protocol.read_text(encoding="utf-8"))
    if frozen.get("frozen_before_execution") is not True or frozen.get("source_commit") != "e2254ebe0168a232e5ba7b94997c749b4e6a4544":
        raise ValueError("Unexpected frozen verification protocol")
    if frozen["execution"] != {"threads": 1, "rng_seed": 2104, "native_timeout_seconds": 600,
                               "growth_scale": 0, "inpaint": False, "resume_opt": "skip"}:
        raise ValueError("Unexpected frozen execution parameters")
    timeout = str(frozen["execution"]["native_timeout_seconds"])
    fixture = args.fixture_root.resolve(strict=True)
    manifest = (fixture / "portable-data/manifest.json").resolve(strict=True)
    for name, expected in json.loads(manifest.read_text(encoding="utf-8"))["files"].items():
        file = (manifest.parent / name).resolve(strict=True)
        if not file.is_relative_to(manifest.parent) or file.stat().st_size != expected["bytes"] or digest(file) != expected["sha256"]:
            raise ValueError("Fixture manifest mismatch: " + name)
    volume = (fixture / "portable-data/prediction-roi.zarr").resolve(strict=True)
    main_checker = (ROOT / "candidate/check_growpatch_requested_bounds.py").resolve(strict=True)
    supplemental = (ROOT / "supplemental-tests/check_supplemental.py").resolve(strict=True)
    binaries = {"baseline": args.baseline_binary.resolve(strict=True),
                "fixed": args.fixed_binary.resolve(strict=True)}
    if not all(path.is_file() for path in binaries.values()) or binaries["baseline"] == binaries["fixed"]:
        raise ValueError("Need two separate, existing native binaries")
    crops = ["development", "new-crop-1", "new-crop-2"]
    meshes = {crop: (fixture / "fixtures" / crop).resolve(strict=True) for crop in crops}
    params = {crop: (fixture / "fixtures" / (crop + "-fill-zero.json")).resolve(strict=True) for crop in crops}
    inputs = [volume, manifest, protocol, main_checker, supplemental, Path(__file__).resolve(),
              *meshes.values(), *params.values(), *binaries.values()]
    output = args.output.resolve()
    if output.exists() or any(output == path or output.is_relative_to(path) or path.is_relative_to(output) for path in inputs):
        raise ValueError("Output must be new and separate from all inputs")
    path_prepend = args.path_prepend if args.path_prepend is not None else [DEFAULT_PREFIX_BIN, "C:/msys64/ucrt64/bin"]
    dll_args = [part for path in path_prepend for part in ("--path-prepend", path)]
    before = inventory(inputs)
    output.mkdir(parents=True, exist_ok=False)
    save(output / "inputs-before.json", before)
    summary = {
        "status": "RUNNING", "completed": False, "planned_native_processes": 22,
        "verification_protocol_sha256": digest(protocol), "cases": {}, "gates": {},
        "counting_rule": frozen["counting_rule"],
        "scope": "Three crops of one PHerc0139 mesh/prediction carrier; multiple processes are not independent datasets. No physical-accuracy claim.",
        "execution_parameters": frozen["execution"],
    }
    try:
        observer = runpy.run_path(str(supplemental), run_name="growpatch_output_observer")
        for crop in crops:
            case = {"variants": {}}
            summary["cases"][crop] = case
            for variant, binary in binaries.items():
                run_output = output / "main" / crop / variant
                command = ["--binary", str(binary), "--volume", str(volume), "--resume", str(meshes[crop]),
                           "--params", str(params[crop]), "--output", str(run_output), "--timeout", timeout, *dll_args]
                code = invoke_checker(main_checker, command, output / "invocations" / crop / variant)
                if code not in (0, 1):
                    raise RuntimeError("Infrastructure failure in " + crop + "/" + variant)
                checked = json.loads((run_output / "results.json").read_text(encoding="utf-8"))
                by_profile = {item["profile"]: item for item in checked["results"]}
                if set(by_profile) != {"fill-zero", "right-one", "wide-control"}:
                    raise RuntimeError("Incomplete main-checker result set")
                save(output / "invocations" / crop / variant / "output-files.json",
                     inventory([run_output / profile / "surface" for profile in by_profile]))
                case["variants"][variant] = {"exit_code": code, "input_bytes_unchanged": checked["input_bytes_unchanged"],
                                             "profiles": by_profile}
            baseline, fixed = case["variants"]["baseline"], case["variants"]["fixed"]
            pair = wide_pair(output / "main" / crop / "baseline", output / "main" / crop / "fixed", observer)
            case["wide_comparison"] = pair
            case["gates"] = {
                "baseline_expected_contract_failure": baseline["exit_code"] == 1,
                "baseline_reproduces_requested_grid_overrun": any(baseline["profiles"][profile]["outside_requested_grid"] > 0 for profile in ("fill-zero", "right-one")),
                "fixed_all_profiles_pass": fixed["exit_code"] == 0 and all(item["passed"] for item in fixed["profiles"].values()),
                "baseline_wide_control_pass": baseline["profiles"]["wide-control"]["passed"],
                "paired_wide_decoded_arrays_identical": pair["passed"],
                "checker_inputs_unchanged": baseline["input_bytes_unchanged"] and fixed["input_bytes_unchanged"],
            }
            case["passed"] = all(case["gates"].values())
            save(output / "summary.json", summary)
            print(json.dumps({"crop_completed": crop, "gates": case["gates"]}), flush=True)
            if crop == "development" and not case["passed"]:
                summary.update(status="DEVELOPMENT_GATE_FAILED_REPLICATION_NOT_STARTED", passed=False)
                return 1
        supplemental_output = output / "supplemental"
        code = invoke_checker(supplemental,
                              ["--baseline-binary", str(binaries["baseline"]), "--fixed-binary", str(binaries["fixed"]),
                               "--fixture-root", str(fixture), "--output", str(supplemental_output), "--timeout", timeout, *dll_args],
                              output / "invocations" / "supplemental")
        if code not in (0, 1):
            raise RuntimeError("Infrastructure failure in supplemental controls")
        supplemental_result = json.loads((supplemental_output / "results.json").read_text(encoding="utf-8"))
        summary["supplemental"] = {"exit_code": code, "results": supplemental_result}
        summary["gates"] = {"all_three_main_crops_pass": len(summary["cases"]) == 3 and all(case["passed"] for case in summary["cases"].values()),
                            "supplemental_controls_pass": code == 0 and supplemental_result.get("passed") is True}
        summary.update(completed=True, status="COMPLETED", passed=all(summary["gates"].values()))
    except BaseException as error:
        summary.update(status="INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "INFRASTRUCTURE_ERROR",
                       passed=False, error=type(error).__name__ + ": " + str(error))
        raise
    finally:
        after = inventory(inputs)
        save(output / "inputs-after.json", after)
        summary["input_bytes_unchanged"] = before == after
        processes = native_process_inventory(output)
        summary["native_processes"] = processes
        summary["actual_native_processes_recorded"] = len(processes)
        summary["actual_native_processes_completed_exit_0"] = sum(item["status"] == "COMPLETED" and item["exit_code"] == 0 and not item["timed_out"] for item in processes)
        summary["gates"]["inputs_and_binaries_unchanged"] = before == after
        if summary["completed"]:
            summary["gates"]["all_22_native_processes_completed_exit_0"] = len(processes) == 22 and summary["actual_native_processes_completed_exit_0"] == 22
            summary["passed"] = all(summary["gates"].values())
        if before != after:
            summary["passed"] = False
        save(output / "summary.json", summary)
        if before != after:
            raise RuntimeError("Input, script, protocol or binary bytes changed during suite")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print("SUITE ERROR: " + str(error), file=sys.stderr)
        sys.exit(2)
