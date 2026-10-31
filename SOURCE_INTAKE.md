# Private source intake

All media and source-derived text must remain under ignored `private-source/` or `work/` directories. Do not add them to Git.

Preferred inputs:

- original recording rather than a chat-compressed copy;
- slides or handouts when authorized and available;
- event metadata or announcement;
- a note defining private-only versus publishable material.

If an external disk is FAT32, a recording larger than 4 GB cannot be copied to it as one file. Use a temporary local export only when necessary, create a verified sub-4-GB private proxy and derived evidence on the external disk, then remove the temporary copy after confirming that the Photos original remains intact.

## 1. Inspect video and candidate visual changes

```bash
python3 tools/inspect_recording.py \
  private-source/recording.m4v \
  work/recording/probe
```

## 2. Extract 16 kHz mono audio on macOS

```bash
bash tools/extract_audio_macos.sh \
  private-source/recording.m4v \
  work/recording/audio_16k_mono.wav
```

## 3. Transcribe a PCM WAV without FFmpeg

The script expects an isolated environment in which OpenAI Whisper and its dependencies are importable. Point `--model-dir` to a verified local model cache; do not silently download a model.

```bash
PYTHONPATH=work/runtime python3 tools/transcribe_whisper_wav.py \
  work/recording/audio_16k_mono.wav \
  work/transcript/raw/whisper.json \
  --model base \
  --model-dir /path/to/local/whisper-cache \
  --device mps \
  --language en \
  --no-word-timestamps
```

## 4. Normalize and bound lecture content

Determine the content boundary from the recording rather than from ASR alone. Preserve raw output and record all exclusions.

```bash
python3 tools/normalize_transcript.py \
  work/transcript/raw/whisper.json \
  work/transcript/normalized \
  --end-at CONTENT_END_SECONDS
```

## 5. Extract and OCR on-screen captions

```bash
python3 tools/extract_caption_crops.py \
  private-source/recording.m4v \
  work/recording/captions \
  --interval 3 \
  --end-at CONTENT_END_SECONDS

swift tools/ocr_frames_vision.swift \
  work/recording/captions/caption_crops \
  work/recording/captions/caption_ocr.json
```

## 6. Assign speakers and align evidence

Keep speaker aliases in an ignored private JSON file. Anonymize audience identities unless explicit reuse permission exists.

```bash
python3 tools/assign_speakers_from_caption_ocr.py \
  work/transcript/normalized/transcript.normalized.json \
  work/recording/captions/caption_ocr.json \
  work/source/speaker_aliases.json \
  work/transcript/verified/transcript.speakers.json

python3 tools/align_evidence.py \
  work/transcript/verified/transcript.speakers.json \
  work/recording/probe/recording_manifest.json \
  work/evidence_verified
```

## 7. Verify before release

```bash
python3 tests/test_tools.py -v
python3 tools/release_guard.py .
```

Change the distributable source register to `VERIFIED` only after complete ingestion, speaker separation, visual-evidence capture or limitation, uncertainty logging, source-anchored rules, and a recorded public/private boundary.
