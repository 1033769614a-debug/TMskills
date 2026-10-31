#!/usr/bin/env python3
"""Extract timestamped lower-screen caption crops from a lecture recording."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--end-at", type=float)
    parser.add_argument("--left", type=float, default=0.24)
    parser.add_argument("--right", type=float, default=0.92)
    parser.add_argument("--top", type=float, default=0.76)
    parser.add_argument("--bottom", type=float, default=0.94)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        raise SystemExit(f"Input does not exist: {args.input}")
    if args.interval <= 0:
        raise SystemExit("--interval must be positive")
    if not 0 <= args.left < args.right <= 1 or not 0 <= args.top < args.bottom <= 1:
        raise SystemExit("Crop fractions must satisfy 0 <= left < right <= 1 and 0 <= top < bottom <= 1")

    capture = cv2.VideoCapture(str(args.input))
    if not capture.isOpened():
        raise SystemExit(f"Cannot open recording: {args.input}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not math.isfinite(fps) or fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        raise SystemExit("Recording metadata is invalid")
    duration = frame_count / fps
    end_at = min(duration, args.end_at) if args.end_at is not None else duration

    left = round(width * args.left)
    right = round(width * args.right)
    top = round(height * args.top)
    bottom = round(height * args.bottom)
    crop_dir = args.output_dir / "caption_crops"
    crop_dir.mkdir(parents=True, exist_ok=True)

    samples: list[dict] = []
    timestamp = 0.0
    while timestamp <= end_at:
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, frame = capture.read()
        if ok:
            crop = frame[top:bottom, left:right]
            filename = f"caption_{len(samples) + 1:05d}_{timestamp:010.3f}s.jpg"
            destination = crop_dir / filename
            if not cv2.imwrite(str(destination), crop, [cv2.IMWRITE_JPEG_QUALITY, 90]):
                raise RuntimeError(f"Failed to write crop: {destination}")
            samples.append(
                {
                    "index": len(samples) + 1,
                    "timestamp_seconds": round(timestamp, 3),
                    "file": f"caption_crops/{filename}",
                }
            )
        timestamp += args.interval
    capture.release()

    manifest = {
        "schema_version": 1,
        "source_filename": args.input.name,
        "video_duration_seconds": round(duration, 3),
        "content_end_seconds": round(end_at, 3),
        "sample_interval_seconds": args.interval,
        "crop_fraction": {
            "left": args.left,
            "right": args.right,
            "top": args.top,
            "bottom": args.bottom,
        },
        "crop_pixels": {"left": left, "right": right, "top": top, "bottom": bottom},
        "sample_count": len(samples),
        "samples": samples,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "caption_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"samples={len(samples)}")
    print(f"output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
