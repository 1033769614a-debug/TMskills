#!/usr/bin/env python3
"""Normalize ASR segments into stable, timestamped private-source anchors."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


UNCERTAINTY_PATTERNS = (
    re.compile(r"\[\s*(?:inaudible|unclear|听不清|不清楚)", re.IGNORECASE),
    re.compile(r"<\?>"),
    re.compile("�"),
)


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def load_segments(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("segments"), list):
        return payload["segments"]
    if isinstance(payload, list):
        return payload
    raise ValueError("Expected a segment list or an object containing a 'segments' list")


def normalize_segments(raw_segments: list[dict]) -> tuple[list[dict], list[str]]:
    normalized = []
    issues = []
    previous_start = -1.0
    for position, raw in enumerate(raw_segments, start=1):
        try:
            start = float(raw["start"])
            end = float(raw["end"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Segment {position} has invalid start/end values") from error
        if start < 0 or end < start:
            raise ValueError(f"Segment {position} has an invalid time range: {start}–{end}")
        if start < previous_start:
            issues.append(f"segment {position} was reordered by start time")
        previous_start = start

        text = " ".join(str(raw.get("text", "")).split())
        if not text:
            issues.append(f"segment {position} has empty text")
        speaker = " ".join(str(raw.get("speaker", "SPEAKER_UNKNOWN")).split()) or "SPEAKER_UNKNOWN"
        uncertain = any(pattern.search(text) for pattern in UNCERTAINTY_PATTERNS)
        if raw.get("no_speech_prob") is not None:
            try:
                uncertain = uncertain or float(raw["no_speech_prob"]) >= 0.6
            except (TypeError, ValueError):
                issues.append(f"segment {position} has invalid no_speech_prob")
        if raw.get("avg_logprob") is not None:
            try:
                uncertain = uncertain or float(raw["avg_logprob"]) < -1.0
            except (TypeError, ValueError):
                issues.append(f"segment {position} has invalid avg_logprob")

        normalized.append(
            {
                "anchor": "",
                "start": round(start, 3),
                "end": round(end, 3),
                "start_timestamp": timestamp(start),
                "end_timestamp": timestamp(end),
                "speaker": speaker,
                "text": text,
                "uncertain": bool(uncertain),
            }
        )

    normalized.sort(key=lambda segment: (segment["start"], segment["end"]))
    for index, segment in enumerate(normalized, start=1):
        segment["anchor"] = f"T{index:06d}"
    return normalized, issues


def write_outputs(
    input_path: Path,
    output_dir: Path,
    segments: list[dict],
    issues: list[str],
    content_end_seconds: float | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "source_filename": input_path.name,
        "content_end_seconds": content_end_seconds,
        "segment_count": len(segments),
        "issues": issues,
        "segments": segments,
    }
    (output_dir / "transcript.normalized.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = ["# Timestamped transcript", "", f"Segments: {len(segments)}", ""]
    for segment in segments:
        flag = " [UNCERTAIN]" if segment["uncertain"] else ""
        lines.append(
            f"[{segment['start_timestamp']}–{segment['end_timestamp']}] "
            f"[{segment['anchor']}] [{segment['speaker']}]{flag} {segment['text']}"
        )
        lines.append("")
    if issues:
        lines.extend(["## Normalization issues", ""])
        lines.extend(f"- {issue}" for issue in issues)
        lines.append("")
    (output_dir / "transcript.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--end-at",
        type=float,
        help="Exclude segments beginning at or after this verified content boundary in seconds",
    )
    args = parser.parse_args()
    if not args.input_json.is_file():
        raise SystemExit(f"Input does not exist: {args.input_json}")
    try:
        raw_segments = load_segments(args.input_json)
        boundary_issues: list[str] = []
        if args.end_at is not None:
            if args.end_at <= 0:
                raise ValueError("--end-at must be positive")
            retained = []
            excluded = 0
            for position, segment in enumerate(raw_segments, start=1):
                try:
                    start = float(segment["start"])
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(f"Segment {position} has an invalid start value") from error
                if start < args.end_at:
                    retained.append(segment)
                else:
                    excluded += 1
            raw_segments = retained
            boundary_issues.append(
                f"excluded {excluded} segment(s) beginning at or after the verified "
                f"content boundary {args.end_at:.3f}s"
            )
        segments, issues = normalize_segments(raw_segments)
        issues = boundary_issues + issues
    except (json.JSONDecodeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    write_outputs(args.input_json, args.output_dir, segments, issues, args.end_at)
    print(f"segments={len(segments)}")
    print(f"uncertain={sum(segment['uncertain'] for segment in segments)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
