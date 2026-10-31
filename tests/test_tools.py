#!/usr/bin/env python3
from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RecordingToolTests(unittest.TestCase):
    def test_slide_change_extraction(self):
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            video_path = temp / "synthetic_lecture.avi"
            output_dir = temp / "out"
            fps = 10
            size = (640, 360)
            writer = cv2.VideoWriter(
                str(video_path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                fps,
                size,
            )
            self.assertTrue(writer.isOpened())
            slides = [
                ((245, 245, 245), "Problem"),
                ((90, 160, 230), "Gap"),
                ((80, 190, 120), "Contribution"),
            ]
            for color, label in slides:
                for _ in range(fps * 2):
                    frame = np.full((size[1], size[0], 3), color, dtype=np.uint8)
                    cv2.putText(frame, label, (80, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (15, 25, 35), 4)
                    writer.write(frame)
            writer.release()

            command = [
                sys.executable,
                str(PROJECT_ROOT / "tools" / "inspect_recording.py"),
                str(video_path),
                str(output_dir),
                "--sample-interval", "0.5",
                "--change-threshold", "12",
                "--min-gap", "0.4",
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            manifest = json.loads((output_dir / "recording_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["extraction"]["candidate_count"], 3)
            self.assertEqual(len(list((output_dir / "slide_candidates").glob("*.jpg"))), 3)
            self.assertNotIn("/Users/", json.dumps(manifest))

    def test_release_guard_passes_verified_skill(self):
        command = [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "release_guard.py"),
            str(PROJECT_ROOT),
        ]
        verified = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        self.assertIn("release_guard=PASS", verified.stdout)

    def test_transcript_normalization_and_slide_alignment(self):
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            raw_path = temp / "raw_asr.json"
            normalized_dir = temp / "normalized"
            aligned_dir = temp / "aligned"
            raw_path.write_text(
                json.dumps(
                    {
                        "segments": [
                            {"start": 0.0, "end": 1.8, "text": " Opening argument. "},
                            {"start": 2.1, "end": 3.2, "text": "[听不清 00:00:02]"},
                            {"start": 4.2, "end": 6.1, "text": "Contribution claim", "speaker": "LECTURER"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "tools" / "normalize_transcript.py"), str(raw_path), str(normalized_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            normalized = json.loads((normalized_dir / "transcript.normalized.json").read_text(encoding="utf-8"))
            self.assertEqual([row["anchor"] for row in normalized["segments"]], ["T000001", "T000002", "T000003"])
            self.assertTrue(normalized["segments"][1]["uncertain"])
            self.assertNotIn("/Users/", json.dumps(normalized))

            recording_manifest = temp / "recording_manifest.json"
            recording_manifest.write_text(
                json.dumps(
                    {
                        "slide_candidates": [
                            {"index": 1, "timestamp_seconds": 0.0, "file": "slide_candidates/slide1.jpg"},
                            {"index": 2, "timestamp_seconds": 3.5, "file": "slide_candidates/slide2.jpg"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "tools" / "align_evidence.py"),
                    str(normalized_dir / "transcript.normalized.json"),
                    str(recording_manifest),
                    str(aligned_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            aligned = json.loads((aligned_dir / "evidence_index.json").read_text(encoding="utf-8"))
            self.assertEqual([row["slide_index"] for row in aligned["rows"]], [1, 1, 2])
            self.assertEqual(aligned["rows"][2]["speaker"], "LECTURER")

    def test_transcript_content_boundary_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            raw_path = temp / "raw.json"
            output_dir = temp / "normalized"
            raw_path.write_text(
                json.dumps(
                    {
                        "segments": [
                            {"start": 0.0, "end": 1.0, "text": "Lecture"},
                            {"start": 10.0, "end": 11.0, "text": "Post-event audio"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "tools" / "normalize_transcript.py"),
                    str(raw_path),
                    str(output_dir),
                    "--end-at",
                    "5",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads((output_dir / "transcript.normalized.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["content_end_seconds"], 5.0)
            self.assertEqual(payload["segment_count"], 1)
            self.assertIn("excluded 1 segment", payload["issues"][0])

    def test_caption_ocr_speaker_assignment_and_anonymization(self):
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            transcript = temp / "transcript.json"
            ocr = temp / "ocr.json"
            aliases = temp / "aliases.json"
            output = temp / "speakers.json"
            transcript.write_text(
                json.dumps(
                    {
                        "segments": [
                            {
                                "anchor": "T000001",
                                "start": 0.0,
                                "end": 1.0,
                                "start_timestamp": "00:00:00.000",
                                "end_timestamp": "00:00:01.000",
                                "speaker": "SPEAKER_UNKNOWN",
                                "text": "Opening",
                                "uncertain": False,
                            },
                            {
                                "anchor": "T000002",
                                "start": 3.0,
                                "end": 4.0,
                                "start_timestamp": "00:00:03.000",
                                "end_timestamp": "00:00:04.000",
                                "speaker": "SPEAKER_UNKNOWN",
                                "text": "Question",
                                "uncertain": False,
                            },
                            {
                                "anchor": "T000003",
                                "start": 6.0,
                                "end": 7.0,
                                "start_timestamp": "00:00:06.000",
                                "end_timestamp": "00:00:07.000",
                                "speaker": "SPEAKER_UNKNOWN",
                                "text": "Continued question",
                                "uncertain": False,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            ocr.write_text(
                json.dumps(
                    {
                        "images": [
                            {
                                "file": "caption_00001_000000.000s.jpg",
                                "lines": [{"text": "Speaker Alpha", "bbox": {"y": 0.3}}],
                            },
                            {
                                "file": "caption_00002_000003.000s.jpg",
                                "lines": [{"text": "account123", "bbox": {"y": 0.82}}],
                            },
                            {"file": "caption_00003_000006.000s.jpg", "lines": []},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            aliases.write_text(
                json.dumps(
                    {
                        "PANELIST": ["Speaker Alpha"],
                        "AUDIENCE_PARTICIPANT": ["account123"],
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_ROOT / "tools" / "assign_speakers_from_caption_ocr.py"),
                    str(transcript),
                    str(ocr),
                    str(aliases),
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                [segment["speaker"] for segment in payload["segments"]],
                ["PANELIST", "AUDIENCE_PARTICIPANT", "AUDIENCE_PARTICIPANT"],
            )
            self.assertEqual(len(payload["speaker_turns"]), 2)

    def test_pcm_wav_loader_without_ffmpeg(self):
        module_path = PROJECT_ROOT / "tools" / "transcribe_whisper_wav.py"
        spec = importlib.util.spec_from_file_location("transcribe_whisper_wav", module_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp_name:
            wav_path = Path(temp_name) / "sample.wav"
            samples = np.array([0, 16384, -16384, 32767], dtype="<i2")
            with wave.open(str(wav_path), "wb") as destination:
                destination.setnchannels(1)
                destination.setsampwidth(2)
                destination.setframerate(16000)
                destination.writeframes(samples.tobytes())
            audio, rate = module.load_pcm16_mono(wav_path)
            self.assertEqual(rate, 16000)
            self.assertEqual(audio.shape, (4,))
            self.assertAlmostEqual(float(audio[1]), 0.5)


if __name__ == "__main__":
    unittest.main()
