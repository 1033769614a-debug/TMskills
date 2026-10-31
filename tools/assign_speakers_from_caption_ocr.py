#!/usr/bin/env python3
"""Assign transcript speakers from timestamped Zoom-caption OCR evidence."""

from __future__ import annotations

import argparse
import bisect
import json
import re
from pathlib import Path


TIMESTAMP_PATTERN = re.compile(r"_(\d+(?:\.\d+)?)s\.(?:jpg|jpeg|png)$", re.IGNORECASE)


def normalized(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_aliases(path: Path) -> dict[str, list[str]]:
    payload = load_json(path)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Speaker alias file must be a non-empty object")
    aliases: dict[str, list[str]] = {}
    for canonical, values in payload.items():
        if not isinstance(canonical, str) or not isinstance(values, list) or not values:
            raise ValueError("Each speaker must map to a non-empty alias list")
        aliases[canonical] = [normalized(str(value)) for value in [canonical, *values]]
    return aliases


def known_speaker(text: str, aliases: dict[str, list[str]]) -> str | None:
    candidate = normalized(text)
    matches: list[tuple[int, str]] = []
    for canonical, variants in aliases.items():
        for variant in variants:
            if variant and variant in candidate:
                matches.append((len(variant), canonical))
    return max(matches)[1] if matches else None


def sample_speaker(image: dict, aliases: dict[str, list[str]], previous: str | None) -> dict:
    filename = str(image.get("file", ""))
    timestamp_match = TIMESTAMP_PATTERN.search(filename)
    if not timestamp_match:
        raise ValueError(f"Cannot read timestamp from OCR filename: {filename}")
    timestamp = float(timestamp_match.group(1))
    lines = image.get("lines", [])

    caption_matches: list[tuple[float, str, str]] = []
    active_view_matches: list[tuple[float, str, str]] = []
    for line in lines:
        text = str(line.get("text", ""))
        box = line.get("bbox") or {}
        y = float(box.get("y", 0.0))
        speaker = known_speaker(text, aliases)
        if speaker is not None and y < 0.70:
            caption_matches.append((y, speaker, text))
        if y >= 0.70:
            active_view_matches.append((y, speaker or "", text))

    if caption_matches:
        y, speaker, evidence = min(caption_matches, key=lambda item: item[0])
        return {
            "timestamp_seconds": timestamp,
            "speaker": speaker,
            "method": "caption_name",
            "evidence_text": evidence,
            "evidence_y": round(y, 6),
        }

    known_active = [item for item in active_view_matches if item[1]]
    if known_active:
        y, speaker, evidence = max(known_active, key=lambda item: item[0])
        return {
            "timestamp_seconds": timestamp,
            "speaker": speaker,
            "method": "active_view_label",
            "evidence_text": evidence,
            "evidence_y": round(y, 6),
        }

    return {
        "timestamp_seconds": timestamp,
        "speaker": previous or "SPEAKER_UNKNOWN",
        "method": "carry_forward" if previous else "unresolved",
        "evidence_text": "",
        "evidence_y": None,
    }


def assign(transcript: dict, ocr: dict, aliases: dict[str, list[str]]) -> tuple[dict, list[dict]]:
    images = ocr.get("images")
    segments = transcript.get("segments")
    if not isinstance(images, list) or not isinstance(segments, list):
        raise ValueError("OCR images and transcript segments must be lists")

    samples: list[dict] = []
    previous: str | None = None
    for image in images:
        sample = sample_speaker(image, aliases, previous)
        if sample["speaker"] != "SPEAKER_UNKNOWN":
            previous = sample["speaker"]
        samples.append(sample)
    samples.sort(key=lambda item: item["timestamp_seconds"])
    sample_times = [float(item["timestamp_seconds"]) for item in samples]

    method_counts: dict[str, int] = {}
    for segment in segments:
        midpoint = (float(segment["start"]) + float(segment["end"])) / 2
        index = bisect.bisect_left(sample_times, midpoint)
        candidates = []
        if index < len(samples):
            candidates.append(samples[index])
        if index > 0:
            candidates.append(samples[index - 1])
        sample = min(candidates, key=lambda item: abs(item["timestamp_seconds"] - midpoint))
        segment["speaker"] = sample["speaker"]
        segment["speaker_assignment"] = {
            "method": sample["method"],
            "sample_timestamp_seconds": sample["timestamp_seconds"],
            "evidence_text": sample["evidence_text"],
        }
        method_counts[sample["method"]] = method_counts.get(sample["method"], 0) + 1

    turns: list[dict] = []
    for segment in segments:
        if not turns or turns[-1]["speaker"] != segment["speaker"]:
            turns.append(
                {
                    "turn": len(turns) + 1,
                    "speaker": segment["speaker"],
                    "start": segment["start"],
                    "end": segment["end"],
                    "start_anchor": segment["anchor"],
                    "end_anchor": segment["anchor"],
                    "segment_count": 1,
                }
            )
        else:
            turns[-1]["end"] = segment["end"]
            turns[-1]["end_anchor"] = segment["anchor"]
            turns[-1]["segment_count"] += 1

    transcript["speaker_assignment"] = {
        "source": "timestamped on-screen caption OCR",
        "sample_interval_seconds": 3.0,
        "method_counts": method_counts,
        "known_speakers": list(aliases),
    }
    transcript["speaker_turns"] = turns
    return transcript, samples


def write_markdown(path: Path, transcript: dict) -> None:
    lines = ["# Timestamped transcript with speaker assignments", ""]
    for segment in transcript["segments"]:
        flag = " [UNCERTAIN]" if segment.get("uncertain") else ""
        lines.extend(
            [
                f"[{segment['start_timestamp']}–{segment['end_timestamp']}] "
                f"[{segment['anchor']}] [{segment['speaker']}]{flag} {segment['text']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript_json", type=Path)
    parser.add_argument("caption_ocr_json", type=Path)
    parser.add_argument("speaker_aliases_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--samples-output", type=Path)
    args = parser.parse_args()

    try:
        transcript, samples = assign(
            load_json(args.transcript_json),
            load_json(args.caption_ocr_json),
            parse_aliases(args.speaker_aliases_json),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(str(error)) from error

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(args.output_json.with_suffix(".md"), transcript)
    if args.samples_output is not None:
        args.samples_output.parent.mkdir(parents=True, exist_ok=True)
        args.samples_output.write_text(
            json.dumps({"schema_version": 1, "samples": samples}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
    print(f"segments={len(transcript['segments'])}")
    print(f"speaker_turns={len(transcript['speaker_turns'])}")
    print(json.dumps(transcript["speaker_assignment"]["method_counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
