#!/usr/bin/env python3
"""Align normalized transcript anchors with the active slide candidate."""

from __future__ import annotations

import argparse
import bisect
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def align(transcript: dict, recording: dict) -> list[dict]:
    segments = transcript.get("segments")
    slides = recording.get("slide_candidates")
    if not isinstance(segments, list) or not isinstance(slides, list):
        raise ValueError("Transcript segments and slide candidates must be lists")
    slide_times = [float(slide["timestamp_seconds"]) for slide in slides]
    if slide_times != sorted(slide_times):
        raise ValueError("Slide candidates are not ordered by timestamp")

    rows = []
    for segment in segments:
        start = float(segment["start"])
        slide_index = bisect.bisect_right(slide_times, start) - 1
        slide = slides[slide_index] if slide_index >= 0 else None
        rows.append(
            {
                "transcript_anchor": segment["anchor"],
                "start": start,
                "end": float(segment["end"]),
                "speaker": segment["speaker"],
                "uncertain": bool(segment["uncertain"]),
                "slide_index": None if slide is None else slide["index"],
                "slide_timestamp_seconds": None if slide is None else slide["timestamp_seconds"],
                "slide_file": None if slide is None else slide["file"],
                "text": segment["text"],
            }
        )
    return rows


def write_outputs(output_dir: Path, rows: list[dict]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "row_count": len(rows), "rows": rows}
    (output_dir / "evidence_index.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = ["# Transcript–slide evidence index", ""]
    for row in rows:
        slide = "no preceding slide" if row["slide_index"] is None else f"slide {row['slide_index']}"
        uncertainty = " — UNCERTAIN" if row["uncertain"] else ""
        lines.extend(
            [
                f"## {row['transcript_anchor']} · {row['start']:.3f}s · {slide}{uncertainty}",
                "",
                f"Speaker: {row['speaker']}",
                "",
                row["text"],
                "",
            ]
        )
    (output_dir / "evidence_index.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("normalized_transcript", type=Path)
    parser.add_argument("recording_manifest", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    try:
        rows = align(load_json(args.normalized_transcript), load_json(args.recording_manifest))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    write_outputs(args.output_dir, rows)
    print(f"evidence_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
