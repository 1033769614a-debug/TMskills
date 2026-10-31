#!/usr/bin/env python3
"""Transcribe a 16 kHz mono PCM WAV with OpenAI Whisper without FFmpeg."""

from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path

import numpy as np


def load_pcm16_mono(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        compression = source.getcomptype()
        frames = source.readframes(source.getnframes())

    if channels != 1 or sample_width != 2 or compression != "NONE":
        raise ValueError(
            "Input must be uncompressed mono 16-bit PCM WAV; "
            f"got channels={channels}, sample_width={sample_width}, compression={compression}"
        )
    if sample_rate != 16_000:
        raise ValueError(f"Input sample rate must be 16000 Hz; got {sample_rate}")

    audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    return audio, sample_rate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--model", default="base")
    parser.add_argument("--model-dir", type=Path, default=Path.home() / ".cache" / "whisper")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--language", default="en")
    parser.add_argument("--initial-prompt")
    parser.add_argument("--clip-start", type=float)
    parser.add_argument("--clip-end", type=float)
    parser.add_argument("--no-word-timestamps", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        raise SystemExit(f"Input does not exist: {args.input}")
    if (args.clip_start is None) != (args.clip_end is None):
        raise SystemExit("--clip-start and --clip-end must be supplied together")
    if args.clip_start is not None and not 0 <= args.clip_start < args.clip_end:
        raise SystemExit("Clip bounds must satisfy 0 <= start < end")

    try:
        import whisper
    except ImportError as error:
        raise SystemExit(
            "OpenAI Whisper is not importable; install it in an isolated runtime or add it to PYTHONPATH"
        ) from error

    audio, sample_rate = load_pcm16_mono(args.input)
    options: dict[str, object] = {
        "language": args.language,
        "task": "transcribe",
        "word_timestamps": not args.no_word_timestamps,
        "verbose": False,
        "condition_on_previous_text": True,
        "initial_prompt": args.initial_prompt,
    }
    if args.clip_start is not None:
        options["clip_timestamps"] = [args.clip_start, args.clip_end]

    model = whisper.load_model(args.model, device=args.device, download_root=str(args.model_dir))
    result = model.transcribe(audio, **options)
    payload = {
        "schema_version": 1,
        "source": {
            "filename": args.input.name,
            "sample_rate": sample_rate,
            "sample_count": int(audio.size),
            "duration_seconds": round(float(audio.size / sample_rate), 6),
        },
        "engine": {
            "name": "openai-whisper",
            "model": args.model,
            "device": args.device,
            "language": args.language,
            "word_timestamps": not args.no_word_timestamps,
        },
        "text": result["text"].strip(),
        "segments": result["segments"],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output_json.with_suffix(".txt").write_text(payload["text"] + "\n", encoding="utf-8")
    print(f"segments={len(payload['segments'])}")
    print(f"output={args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
