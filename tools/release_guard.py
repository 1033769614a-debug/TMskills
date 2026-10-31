#!/usr/bin/env python3
"""Reject a GitHub release that contains private sources or unverified attribution."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


FORBIDDEN_SUFFIXES = {
    ".mp4", ".mov", ".mkv", ".m4v", ".webm", ".mp3", ".m4a", ".wav",
}
FORBIDDEN_NAME_PARTS = ("transcript", "逐字稿", "未公开论文")
PRIVATE_TEXT_SUFFIXES = {".txt", ".md", ".docx", ".json", ".srt", ".vtt"}
SKIP_DIRS = {".git", "private-source", "work", "__pycache__"}
ABSOLUTE_HOME_PATTERN = re.compile(r"/Users/[A-Za-z0-9._-]+/")


def iter_release_files(root: Path):
    for current_root, directories, filenames in os.walk(root):
        directories[:] = [name for name in directories if name not in SKIP_DIRS]
        for filename in filenames:
            if filename == ".DS_Store" or filename.startswith("._"):
                continue
            yield Path(current_root) / filename


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--allow-unverified", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    failures = []

    source_register = root / "skills" / "tourism-intro-contribution" / "references" / "source-register.md"
    if not source_register.is_file():
        failures.append("missing source register")
    else:
        register_text = source_register.read_text(encoding="utf-8")
        if "Status: `VERIFIED`" not in register_text and not args.allow_unverified:
            failures.append("lecture source register is not VERIFIED")

    for path in iter_release_files(root):
        relative = path.relative_to(root)
        lowered = path.name.lower()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"forbidden media file: {relative}")
        if path.suffix.lower() in PRIVATE_TEXT_SUFFIXES and any(part in lowered for part in FORBIDDEN_NAME_PARTS):
            failures.append(f"forbidden private-source filename: {relative}")
        if path.suffix.lower() in {".md", ".txt", ".yaml", ".yml", ".json", ".py", ".sh"}:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                failures.append(f"text-like file is not UTF-8: {relative}")
                continue
            if ABSOLUTE_HOME_PATTERN.search(content):
                failures.append(f"absolute home path found: {relative}")

    if failures:
        for failure in sorted(set(failures)):
            print(f"FAIL: {failure}")
        return 1
    print("release_guard=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
