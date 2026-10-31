#!/usr/bin/env python3
"""Probe a lecture recording and extract likely slide-change frames locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frame_signature(frame):
    height, width = frame.shape[:2]
    target_width = min(width, 320)
    target_height = max(1, round(height * target_width / width))
    resized = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (5, 5), 0)


def safe_fourcc(raw_value: float) -> str:
    value = int(raw_value)
    chars = [chr((value >> (8 * index)) & 0xFF) for index in range(4)]
    return "".join(char if 32 <= ord(char) <= 126 else "?" for char in chars)


def inspect_recording(
    input_path: Path,
    output_dir: Path,
    sample_interval: float,
    change_threshold: float,
    min_gap: float,
) -> dict:
    capture = cv2.VideoCapture(str(input_path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open recording: {input_path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = safe_fourcc(capture.get(cv2.CAP_PROP_FOURCC))
    if not math.isfinite(fps) or fps <= 0 or frame_count <= 0:
        raise RuntimeError("Recording metadata is invalid or unsupported")

    duration = frame_count / fps
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_dir = output_dir / "slide_candidates"
    frame_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    previous_kept = None
    previous_kept_time = -math.inf
    timestamp = 0.0

    while timestamp < duration:
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, frame = capture.read()
        if not ok:
            timestamp += sample_interval
            continue

        signature = frame_signature(frame)
        luminance_std = float(signature.std())
        if previous_kept is None:
            difference = None
            should_keep = True
        else:
            difference = float(cv2.absdiff(signature, previous_kept).mean())
            should_keep = difference >= change_threshold and timestamp - previous_kept_time >= min_gap

        if should_keep:
            filename = f"slide_{len(candidates) + 1:04d}_{timestamp:010.3f}s.jpg"
            destination = frame_dir / filename
            if not cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, 92]):
                raise RuntimeError(f"Failed to write frame: {destination}")
            candidates.append(
                {
                    "index": len(candidates) + 1,
                    "timestamp_seconds": round(timestamp, 3),
                    "difference_from_previous_kept": None if difference is None else round(difference, 3),
                    "luminance_std": round(luminance_std, 3),
                    "file": f"slide_candidates/{filename}",
                }
            )
            previous_kept = signature
            previous_kept_time = timestamp

        timestamp += sample_interval

    capture.release()
    manifest = {
        "schema_version": 1,
        "source": {
            "filename": input_path.name,
            "size_bytes": input_path.stat().st_size,
            "sha256": sha256_file(input_path),
        },
        "video": {
            "duration_seconds": round(duration, 3),
            "fps": round(fps, 6),
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "fourcc": fourcc,
        },
        "extraction": {
            "sample_interval_seconds": sample_interval,
            "change_threshold": change_threshold,
            "minimum_gap_seconds": min_gap,
            "candidate_count": len(candidates),
        },
        "slide_candidates": candidates,
    }
    manifest_path = output_dir / "recording_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local lecture recording")
    parser.add_argument("output_dir", type=Path, help="Private output directory")
    parser.add_argument("--sample-interval", type=float, default=2.0)
    parser.add_argument("--change-threshold", type=float, default=18.0)
    parser.add_argument("--min-gap", type=float, default=2.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        raise SystemExit(f"Input file does not exist: {args.input}")
    if args.sample_interval <= 0 or args.change_threshold < 0 or args.min_gap < 0:
        raise SystemExit("Intervals and thresholds must be non-negative; sample interval must be positive")
    manifest = inspect_recording(
        args.input.resolve(),
        args.output_dir.resolve(),
        args.sample_interval,
        args.change_threshold,
        args.min_gap,
    )
    print(json.dumps(manifest["video"], ensure_ascii=False))
    print(f"slide_candidates={manifest['extraction']['candidate_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
