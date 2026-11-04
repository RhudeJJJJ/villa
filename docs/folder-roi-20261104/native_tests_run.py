"""Run the actual flat-inference tests against staged native vc_reader bindings.

Invoke with the native environment's Python 3.14, for example:
    python -B -X utf8 work/native_tests_run.py fixed --label fixed-01
    python -B -X utf8 work/native_tests_run.py baseline --label baseline-01

Each label must be new. The baseline defaults to the new ROI-folder suite;
fixed defaults to that suite plus the two existing ROI suites. No native or
inference behavior is replaced. Full subprocess logs and both exit codes are
retained under work/native-test-evidence/<label>.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback


WORK = Path(__file__).resolve().parent
REPO = WORK / "villa-upstream"
BUILD = WORK / "native-build"
PACKAGE_PARENT = WORK / "native-package"
PACKAGE = PACKAGE_PARENT / "vc_reader"
PYTHON_SOURCE = REPO / "vc_reader/src/vc_reader"
INFER_SOURCE = REPO / "vesuvius/src/vesuvius/ink_detection/inference/infer.py"
BASELINE_SOURCE = WORK / "roi-replay-baseline/infer-source.py"
PIN = "baf5e605bb42a3d55a62b7c5c728e0908137225c"
INFER_RELATIVE = "vesuvius/src/vesuvius/ink_detection/inference/infer.py"
NATIVE_NAMES = ("_catalog", "_reader", "_transforms", "_thinning")
PREFIX_BIN = Path(
    "C:/Users/jonas/Documents/Codex/2026-10-16/"
    "hier-in-diesem-chat-wollen-wir/targets/VC-GROW-2104/full-cpp/prefix/ucrt64/bin"
)
DLL_DIRS = (PREFIX_BIN, BUILD)
NEW_SUITE = "vesuvius/tests/ink_detection/test_roi_folder_identity.py"
EXISTING_SUITES = (
    "vesuvius/tests/ink_detection/test_roi_inference.py",
    "vesuvius/tests/ink_detection/test_roi_output_metadata.py",
)


def sha256(path: Path) -> str:
    import hashlib
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def stage_native_package() -> dict:
    """Copy source bytes and the four completed builds, checking both sides."""
    sources = {
        path.relative_to(PYTHON_SOURCE): path
        for path in PYTHON_SOURCE.rglob("*")
        if path.is_file() and path.suffix in {".py", ".pyi"}
        and "__pycache__" not in path.parts
    }
    if not sources or Path("__init__.py") not in sources:
        raise RuntimeError(f"No complete Python source package at {PYTHON_SOURCE}")
    native = {
        Path(f"{name}.cp314-win_amd64.pyd"): BUILD / f"{name}.cp314-win_amd64.pyd"
        for name in NATIVE_NAMES
    }
    for path in native.values():
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Completed native binding required: {path}")
    expected = sources | native
    if PACKAGE.exists():
        unexpected = [
            str(path.relative_to(PACKAGE))
            for path in PACKAGE.rglob("*")
            if path.is_file() and path.suffix in {".py", ".pyi", ".pyd"}
            and "__pycache__" not in path.parts
            and path.relative_to(PACKAGE) not in expected
        ]
        if unexpected:
            raise RuntimeError(f"Unexpected staged code; not deleting it: {unexpected}")
    members = []
    for relative, source in sorted(expected.items(), key=lambda item: str(item[0])):
        before = sha256(source)
        target = PACKAGE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied = sha256(target)
        after = sha256(source)
        if not (before == copied == after):
            raise RuntimeError(f"Staging changed or mismatched source bytes: {source}")
        members.append({
            "relative_path": relative.as_posix(), "source": str(source),
            "staged": str(target), "bytes": source.stat().st_size,
            "source_sha256_before": before, "staged_sha256": copied,
            "source_sha256_after": after,
        })
    return {
        "status": "byte_identical_staging_verified",
        "source_package": str(PYTHON_SOURCE), "staged_package": str(PACKAGE),
        "python_source_members": len(sources), "native_members": len(native),
        "members": members,
    }


def run_child(args, evidence: Path) -> int:
    """Load the real native modules and dispatch pytest in this fresh process."""
    report = {
        "mode": args.mode, "python_executable": sys.executable,
        "python_version": sys.version, "native_imports": {},
        "pytest_exit_code": None, "collected_nodeids": [], "test_reports": [],
        "test_source_hashes": {},
    }
    started = time.monotonic()
    dll_handles = []
    try:
        if sys.version_info[:2] != (3, 14):
            raise RuntimeError("Native tests require the configured Python 3.14 interpreter")
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        if head != PIN:
            raise RuntimeError(f"Unexpected upstream HEAD: {head}")
        report["upstream_pin"] = head
        report["dll_directories"] = [str(path) for path in DLL_DIRS]
        for path in DLL_DIRS:
            if not path.is_dir():
                raise FileNotFoundError(f"Required DLL directory missing: {path}")
            dll_handles.append(os.add_dll_directory(str(path)))
        sys.path[:0] = [str(PACKAGE_PARENT), str(REPO / "vesuvius/src")]
        for name in NATIVE_NAMES:
            module = importlib.import_module(f"vc_reader.{name}")
            loaded = Path(module.__file__).resolve()
            expected = (PACKAGE / f"{name}.cp314-win_amd64.pyd").resolve()
            if loaded != expected:
                raise RuntimeError(f"Unexpected native binding loaded: {loaded}")
            report["native_imports"][name] = {
                "path": str(loaded), "sha256": sha256(loaded),
            }
        import vc_reader
        if Path(vc_reader.__file__).resolve() != (PACKAGE / "__init__.py").resolve():
            raise RuntimeError(f"Unexpected vc_reader source package: {vc_reader.__file__}")
        # CURL's matching native dependencies must load before hashlib on this
        # Windows host; otherwise CPython's earlier crypto DLL can shadow them.
        import hashlib
        import torch
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        report["torch"] = {
            "version": torch.__version__, "threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
        }
        canonical = "vesuvius.ink_detection.inference.infer"
        expected_source = BASELINE_SOURCE if args.mode == "baseline" else INFER_SOURCE
        pinned_blob = subprocess.check_output(
            ["git", "rev-parse", f"{PIN}:{INFER_RELATIVE}"], cwd=REPO, text=True
        ).strip()
        loaded_blob = subprocess.check_output(
            ["git", "hash-object", f"--path={INFER_RELATIVE}", str(expected_source)],
            cwd=REPO, text=True,
        ).strip()
        source_before = sha256(expected_source)
        report["inference_source"] = {
            "path": str(expected_source), "sha256": source_before,
            "sha256_before": source_before, "upstream_pin": head,
            "pinned_upstream_blob": pinned_blob, "loaded_filtered_blob": loaded_blob,
            "source_identity_rule": "Raw SHA-256 retained; git --path text identity allows repository CRLF normalization",
        }
        if args.mode == "baseline":
            pinned_bytes = subprocess.check_output(
                ["git", "show", f"{PIN}:{INFER_RELATIVE}"], cwd=REPO,
            )
            actual_bytes = expected_source.read_bytes()
            if loaded_blob != pinned_blob or actual_bytes.replace(b"\r\n", b"\n") != pinned_bytes.replace(b"\r\n", b"\n"):
                raise RuntimeError("Baseline differs from pinned source beyond CRLF-to-LF normalization")
            report["inference_source"].update({
                "baseline_pin_match": True, "normalization": "CRLF-to-LF only; actual file bytes are not rewritten",
                "pinned_raw_sha256": hashlib.sha256(pinned_bytes).hexdigest(),
                "canonical_lf_sha256": hashlib.sha256(actual_bytes.replace(b"\r\n", b"\n")).hexdigest(),
            })
        if args.mode == "baseline":
            parent = importlib.import_module("vesuvius.ink_detection.inference")
            spec = importlib.util.spec_from_file_location(canonical, BASELINE_SOURCE)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Cannot load baseline source: {BASELINE_SOURCE}")
            inference = importlib.util.module_from_spec(spec)
            sys.modules[canonical] = inference
            spec.loader.exec_module(inference)
            parent.infer = inference
        else:
            inference = importlib.import_module(canonical)
        if Path(inference.__file__).resolve() != expected_source.resolve():
            raise RuntimeError(f"Unexpected inference module: {inference.__file__}")
        report["inference_source"]["sha256_after_import"] = sha256(expected_source)
        if report["inference_source"]["sha256_after_import"] != source_before:
            raise RuntimeError("Inference source changed during import")
        print(json.dumps({
            "native_imports": report["native_imports"],
            "inference_source": report["inference_source"], "torch": report["torch"],
        }, indent=2), flush=True)
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        import pytest
        test_reports = report["test_reports"]

        class Collector:
            def pytest_collection_finish(self, session):
                report["collected_nodeids"] = [item.nodeid for item in session.items]

            def pytest_runtest_logreport(self, report):
                result = {
                    "nodeid": report.nodeid, "when": report.when,
                    "outcome": report.outcome, "duration": report.duration,
                }
                if report.failed:
                    result["longrepr"] = report.longreprtext
                test_reports.append(result)

        suites = [NEW_SUITE]
        if args.suite == "all":
            suites.extend(EXISTING_SUITES)
        bound_sources = set(suites) | {
            "vesuvius/tests/ink_detection/test_roi_output_metadata.py",
            "vesuvius/tests/ink_detection/fixtures/ink_roi_case.npz",
            "vesuvius/tests/ink_detection/fixtures/ink_roi_case.json",
        }
        report["test_source_hashes"] = {
            relative: {"sha256_before": sha256(REPO / relative)}
            for relative in sorted(bound_sources)
        }
        pytest_args = [
            "-vv", "--tb=long", "-p", "no:cacheprovider",
            "--basetemp", str(evidence / "pytest-tmp"),
            *(str(REPO / suite) for suite in suites),
        ]
        report["pytest_arguments"] = pytest_args
        code = int(pytest.main(pytest_args, plugins=[Collector()]))
        report["pytest_exit_code"] = code
        report["inference_source"]["sha256_after"] = sha256(expected_source)
        if report["inference_source"]["sha256_after"] != source_before:
            raise RuntimeError("Inference source changed during native tests")
        for relative, item in report["test_source_hashes"].items():
            item["sha256_after"] = sha256(REPO / relative)
            if item["sha256_before"] != item["sha256_after"]:
                raise RuntimeError(f"Test/helper/fixture changed during execution: {relative}")
        report["status"] = "passed" if code == 0 else "pytest_failed"
        return code
    except BaseException as error:
        report["status"] = "child_setup_or_execution_failed"
        report["exception"] = repr(error)
        traceback.print_exc()
        return 2
    finally:
        if "inference_source" in report:
            source = Path(report["inference_source"]["path"])
            report["inference_source"].setdefault("sha256_after", sha256(source) if source.is_file() else None)
        for relative, item in report["test_source_hashes"].items():
            source = REPO / relative
            item.setdefault("sha256_after", sha256(source) if source.is_file() else None)
        report["wall_seconds"] = time.monotonic() - started
        write_json(evidence / "child-result.json", report)
        for handle in reversed(dll_handles):
            handle.close()


def run_outer(args, evidence: Path) -> int:
    evidence.mkdir(parents=True, exist_ok=False)
    report = {
        "mode": args.mode, "suite": args.suite, "label": args.label,
        "evidence_directory": str(evidence), "inner_exit_code": None,
    }
    started = time.monotonic()
    try:
        write_json(evidence / "staging.json", stage_native_package())
        command = [
            sys.executable, "-B", "-X", "utf8", str(Path(__file__).resolve()),
            args.mode, "--label", args.label, "--suite", args.suite, "--child",
        ]
        report["command"] = command
        env = dict(
            os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1",
            PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        )
        with (evidence / "stdout.txt").open("wb") as stdout, (
            evidence / "stderr.txt"
        ).open("wb") as stderr:
            completed = subprocess.run(
                command, cwd=REPO, env=env, stdout=stdout, stderr=stderr,
                timeout=args.timeout_seconds, check=False,
            )
        report["inner_exit_code"] = completed.returncode
        report["status"] = "passed" if completed.returncode == 0 else "child_failed"
        return completed.returncode if 0 <= completed.returncode <= 255 else 2
    except subprocess.TimeoutExpired as error:
        report["status"] = "child_timed_out"
        report["exception"] = repr(error)
        return 2
    except BaseException as error:
        report["status"] = "runner_setup_or_execution_failed"
        report["exception"] = repr(error)
        traceback.print_exc()
        return 2
    finally:
        report["wall_seconds"] = time.monotonic() - started
        report["logs"] = {
            "stdout": str(evidence / "stdout.txt"),
            "stderr": str(evidence / "stderr.txt"),
            "child_result": str(evidence / "child-result.json"),
            "staging": str(evidence / "staging.json"),
        }
        write_json(evidence / "runner-result.json", report)
        print(json.dumps(report, indent=2), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("fixed", "baseline"))
    parser.add_argument("--label", required=True)
    parser.add_argument("--suite", choices=("new", "all"))
    parser.add_argument("--timeout-seconds", type=float, default=900)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", args.label):
        parser.error("--label must be a new plain alphanumeric label, at most 80 characters")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    args.suite = args.suite or ("new" if args.mode == "baseline" else "all")
    evidence = WORK / "native-test-evidence" / args.label
    return run_child(args, evidence) if args.child else run_outer(args, evidence)


if __name__ == "__main__":
    raise SystemExit(main())
