#!/usr/bin/env python3
"""Fetch only pinned public S3 files and reconstruct the small real GrowPatch input.

Requires existing NumPy and Pillow. No installs, recursive downloads, volume
decompression or tracing. Output must not exist unless --complete-existing is
explicitly used to finish a failed receipt without replacing verified files.
Every original download and
every reconstructed fixture file must match its expected byte hash. A separate
decoded XYZ hash makes the numerical-vs-serialization distinction explicit.

  python fetch_real_fixture.py --output /new/path/fixture
  python check_growpatch_requested_bounds.py --binary /path/vc_grow_seg_from_seed \
    --fixture-root /new/path/fixture --output /another/new/path/results
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image

HOST = "vesuvius-challenge-open-data.s3.amazonaws.com"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def target(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
        raise ValueError("Unsafe output member: " + name)
    path = root.joinpath(*relative.parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.parent.resolve(strict=True).is_relative_to(root) or path.is_symlink():
        raise ValueError("Output member escapes resolved root: " + name)
    return path


def verify_bytes(data, expected, label):
    if len(data) != expected["bytes"] or sha(data) != expected["sha256"]:
        raise ValueError("Byte/hash mismatch: " + label)


def write_exact(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("Existing output differs; refusing replacement: " + str(path))
    else:
        with path.open("xb") as stream:
            stream.write(data)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        raise ValueError("Redirect rejected: " + newurl)


def fetch(root, record, timeout):
    url = record["url"]
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != HOST or parsed.query or parsed.fragment:
        raise ValueError("Only the explicit public S3 URLs are allowed")
    path = target(root, record["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    checksum = hashlib.sha256()
    count = 0
    started = time.monotonic()
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "GrowPatch-real-fixture-replay/1"})
    with opener.open(request, timeout=timeout) as response, temporary.open("xb") as stream:
        if response.status != 200:
            raise ValueError("Unexpected HTTP status: " + str(response.status))
        headers = {key: response.headers.get(key) for key in ("Content-Length", "ETag", "Last-Modified")}
        while True:
            block = response.read(min(65536, record["bytes"] + 1 - count))
            if not block:
                break
            count += len(block)
            if count > record["bytes"]:
                raise ValueError("Download exceeds explicit byte limit: " + url)
            checksum.update(block)
            stream.write(block)
    if count != record["bytes"] or checksum.hexdigest() != record["sha256"]:
        raise ValueError("Original download byte/hash mismatch: " + url)
    temporary.rename(path)
    return {"path": record["path"], "url": url, "status": "FETCHED_HASH_VERIFIED", "bytes": count,
            "sha256": checksum.hexdigest(), "response_headers": headers,
            "wall_seconds": time.monotonic() - started}


def tiff_bytes(values, floating):
    """The pinned historical one-strip TIFF layout, independent of Pillow writing."""
    rows, cols = values.shape
    payload = np.asarray(values, dtype="<f4" if floating else "<u2").tobytes(order="C")
    bits, sample_format = (32, 3) if floating else (16, 1)
    tags = [(256, 4, cols), (257, 4, rows), (258, 3, bits), (259, 3, 1),
            (262, 3, 1), (273, 4, 160), (274, 3, 1), (277, 3, 1),
            (278, 4, rows), (279, 4, len(payload)), (284, 3, 1), (339, 3, sample_format)]
    directory = b"".join(struct.pack("<HHII", tag, kind, 1, value) for tag, kind, value in tags)
    prefix = b"II" + struct.pack("<HIH", 42, 8, len(tags)) + directory + struct.pack("<I", 0)
    return prefix + bytes(160 - len(prefix)) + payload


def selected_centers(full, offset, local_shape_xyz, development):
    local = full.astype(np.float64) - offset
    eligible = []
    for row in range(4, full.shape[0] - 4):
        for col in range(4, full.shape[1] - 4):
            if max(abs(row - development[0]), abs(col - development[1])) < 10:
                continue
            crop = local[row - 2:row + 3, col - 2:col + 3]
            if (np.all(full[row - 2:row + 3, col - 2:col + 3, 0] != -1) and
                    np.all(crop > 80) and np.all(crop < local_shape_xyz - 80)):
                eligible.append((abs(row - development[0]) + abs(col - development[1]), row, col))
    centers = [list(development)]
    for _, row, col in sorted(eligible):
        if all(max(abs(row - rr), abs(col - cc)) >= 10 for rr, cc in centers):
            centers.append([row, col])
            if len(centers) == 3:
                break
    return centers


def reconstruct(root, spec):
    for record in spec["generated_text_files"]:
        data = record["text"].encode("utf-8")
        verify_bytes(data, record, record["path"])
        path = target(root, record["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        write_exact(path, data)
    source_array = json.loads((root / "portable-data/source-metadata/0/.zarray").read_text())
    local_array = json.loads((root / "portable-data/prediction-roi.zarr/0/.zarray").read_text())
    if source_array["shape"] != spec["source_shape_zyx"] or local_array["shape"] != spec["local_shape_zyx"]:
        raise ValueError("Source/local array shape mismatch")
    for key in ("chunks", "compressor", "dtype", "fill_value", "filters", "order"):
        if source_array[key] != local_array[key]:
            raise ValueError("Local ROI changes source codec/layout: " + key)
    chunks = np.asarray(source_array["chunks"], dtype=np.int64)
    offset_zyx = np.asarray(spec["source_offset_zyx"], dtype=np.int64)
    if np.any(offset_zyx % chunks):
        raise ValueError("ROI source offset is not chunk-aligned")
    for record in spec["downloads"]:
        if "local_chunk_zyx" in record:
            if not np.array_equal(np.asarray(record["source_chunk_zyx"]), np.asarray(record["local_chunk_zyx"]) + offset_zyx // chunks):
                raise ValueError("Source/local chunk translation mismatch")
    mesh_root = root / "portable-data/published-mesh"
    bands = []
    for axis in "xyz":
        with Image.open(mesh_root / (axis + ".tif")) as image:
            bands.append(np.array(image))
    full = np.stack(bands, axis=-1)
    offset = np.asarray(spec["offset_source_xyz"], dtype=np.float64)
    if not np.array_equal(offset, offset_zyx[::-1]):
        raise ValueError("XYZ/ZYX offset disagreement")
    centers = selected_centers(full, offset, np.asarray(spec["local_shape_zyx"])[::-1], spec["crops"][0]["source_center_rc"])
    if centers != [crop["source_center_rc"] for crop in spec["crops"]]:
        raise ValueError("Pinned pre-trace crop selection did not reconstruct")
    source_meta = json.loads((mesh_root / "meta.json").read_text())
    results = []
    for crop in spec["crops"]:
        row, col = crop["source_center_rc"]
        original = full[row - 2:row + 3, col - 2:col + 3]
        points = (original.astype(np.float64) - offset).astype(np.float32)
        if points.shape != (5, 5, 3) or np.any(original[..., 0] == -1) or not np.array_equal(points.astype(np.float64) + offset, original):
            raise ValueError("Crop is invalid or integer translation is not exactly reversible")
        decoded = points.astype("<f4").tobytes(order="C")
        if sha(decoded) != crop["decoded_xyz"]["sha256"]:
            raise ValueError("Decoded XYZ hash mismatch: " + crop["label"])
        metadata = dict(source_meta)
        metadata["bbox"] = [points.reshape(-1, 3).min(0).astype(float).tolist(), points.reshape(-1, 3).max(0).astype(float).tolist()]
        metadata.update(uuid=crop["label"], vc_requested_limit_provenance={"source": spec["source_mesh"],
                        "source_center_rc": [row, col], "offset_xyz": offset.tolist()})
        payloads = {axis + ".tif": tiff_bytes(points[..., index], True) for index, axis in enumerate("xyz")}
        payloads["generations.tif"] = tiff_bytes(np.ones((5, 5), dtype=np.uint16), False)
        # Match the historical Windows writer's CRLF bytes on every platform.
        payloads["meta.json"] = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").replace("\n", "\r\n").encode("utf-8")
        folder = target(root, "fixtures/" + crop["label"])
        folder.mkdir(parents=True, exist_ok=True)
        for name, data in payloads.items():
            verify_bytes(data, crop["expected_files"][name], crop["label"] + "/" + name)
            write_exact(folder / name, data)
        results.append({"label": crop["label"], "source_center_rc": [row, col],
                        "decoded_xyz_sha256": sha(decoded), "exact_source_xyz_reconstruction": True,
                        "all_five_serialized_files_byteidentical": True})
    files = {}
    for path in sorted((root / "portable-data").rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            files[path.relative_to(root / "portable-data").as_posix()] = {"bytes": len(data), "sha256": sha(data)}
    save(root / "portable-data/manifest.json", {"scope": spec["scope"], "files": files})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("fixture-sources.json"))
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--complete-existing", action="store_true",
                        help="Explicitly finish one failed receipt; rehash existing originals without retransmission or overwrite")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    spec = json.loads(args.manifest.read_text(encoding="utf-8"))
    if spec["schema"] != "growpatch-public-real-fixture-v1":
        raise ValueError("Unsupported fixture manifest")
    if [crop["label"] for crop in spec["crops"]] != ["development", "new-crop-1", "new-crop-2"]:
        raise ValueError("Unexpected crop labels/order")
    records = spec["downloads"]
    if len(records) != 43 or sum(record["bytes"] for record in records) > 12 * 1024 * 1024:
        raise ValueError("Unexpected explicit download set/size")
    if len({record["path"] for record in records}) != len(records):
        raise ValueError("Duplicate download targets")
    output = args.output.absolute()
    previous_receipt = None
    if args.complete_existing:
        previous_receipt = json.loads((output / "reconstruction-receipt.json").read_text(encoding="utf-8"))
        if previous_receipt.get("status") != "FAILED" or previous_receipt["manifest_sha256"] != sha(args.manifest.read_bytes()):
            raise ValueError("Completion requires a failed receipt with the identical source manifest")
        previous_phase = previous_receipt.get("phase", 1)
        previous_name = "reconstruction-receipt.phase-" + str(previous_phase) + ".json"
        with (output / previous_name).open("xb") as stream:
            stream.write((output / "reconstruction-receipt.json").read_bytes())
    else:
        output.mkdir(parents=True, exist_ok=False)
    output = output.resolve(strict=True)
    report = {"status": "RUNNING", "manifest_sha256": sha(args.manifest.read_bytes()),
              "phase": previous_phase + 1 if args.complete_existing else 1,
              "previous_receipt": previous_name if args.complete_existing else None,
              "planned_download_files": len(records), "planned_download_bytes": sum(record["bytes"] for record in records),
              "download_results": [], "failures": [], "crop_results": [],
              "limits": "No prediction volume decoding or tracing; three crops share one carrier."}
    save(output / "reconstruction-receipt.json", report)
    started = time.monotonic()
    try:
        pending = []
        # Resolve existing parents sequentially before any download worker starts.
        # This also avoids concurrent non-strict Windows path canonicalization.
        for record in records:
            path = target(output, record["path"])
            if path.exists():
                if not args.complete_existing:
                    raise ValueError("Download output unexpectedly already exists")
                data = path.read_bytes()
                verify_bytes(data, record, record["path"])
                report["download_results"].append({"path": record["path"], "url": record["url"],
                       "status": "EXISTING_REHASH_VERIFIED", "bytes": len(data), "sha256": sha(data)})
            else:
                pending.append(record)
        with ThreadPoolExecutor(max_workers=4) as executor:
            tasks = {executor.submit(fetch, output, record, args.timeout): record for record in pending}
            for future in as_completed(tasks):
                record = tasks[future]
                try:
                    item = future.result()
                    report["download_results"].append(item)
                    print(json.dumps({"path": item["path"], "status": item["status"], "bytes": item["bytes"]}), flush=True)
                except Exception as error:
                    report["failures"].append({"path": record["path"], "url": record["url"], "error": str(error)})
                save(output / "reconstruction-receipt.json", report)
        if report["failures"]:
            raise RuntimeError("At least one original source could not be downloaded and hash-verified")
        report["crop_results"] = reconstruct(output, spec)
        report["status"] = "PASS"
    except BaseException as error:
        report["status"] = "FAILED"
        report["error"] = str(error)
        raise
    finally:
        report["wall_seconds"] = time.monotonic() - started
        downloaded = [item for item in report["download_results"] if item["status"] == "FETCHED_HASH_VERIFIED"]
        existing = [item for item in report["download_results"] if item["status"] == "EXISTING_REHASH_VERIFIED"]
        report["downloaded_hash_verified_files"] = len(downloaded)
        report["downloaded_hash_verified_bytes"] = sum(item["bytes"] for item in downloaded)
        report["existing_rehash_verified_files"] = len(existing)
        report["existing_rehash_verified_bytes"] = sum(item["bytes"] for item in existing)
        report["total_hash_verified_source_files"] = len(report["download_results"])
        report["total_hash_verified_source_bytes"] = sum(item["bytes"] for item in report["download_results"])
        save(output / "reconstruction-receipt.json", report)
    print(json.dumps({key: report[key] for key in ("status", "downloaded_hash_verified_files", "downloaded_hash_verified_bytes", "crop_results", "wall_seconds")}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print("FIXTURE ERROR: " + str(error), file=sys.stderr)
        sys.exit(2)
