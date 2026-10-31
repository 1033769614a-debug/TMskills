#!/bin/bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 INPUT_VIDEO OUTPUT_WAV" >&2
  exit 2
fi

input_video=$1
output_wav=$2

if [[ ! -f "$input_video" ]]; then
  echo "input does not exist: $input_video" >&2
  exit 2
fi

if [[ ! -x /usr/bin/avconvert || ! -x /usr/bin/afconvert ]]; then
  echo "required macOS media converters are unavailable" >&2
  exit 3
fi

output_parent=$(dirname "$output_wav")
mkdir -p "$output_parent"
temporary_m4a="$output_wav.source.m4a"
trap 'rm -f "$temporary_m4a"' EXIT

/usr/bin/avconvert \
  --source "$input_video" \
  --preset PresetAppleM4A \
  --output "$temporary_m4a" \
  --replace

/usr/bin/afconvert \
  "$temporary_m4a" \
  "$output_wav" \
  -f WAVE \
  -d LEI16@16000 \
  -c 1

if [[ ! -s "$output_wav" ]]; then
  echo "audio extraction produced an empty file" >&2
  exit 4
fi

echo "$output_wav"
