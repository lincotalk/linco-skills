#!/usr/bin/env python3
"""Split narration text into bounded VoxCPM requests at natural boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


class SegmentError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--chars-per-second", type=float)
    parser.add_argument("--target-seconds", type=float)
    parser.add_argument("--max-seconds", type=float)
    return parser.parse_args()


def read_segmentation_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    segmentation = value.get("tts", {}).get("segmentation", {}) if isinstance(value, dict) else {}
    if not isinstance(segmentation, dict):
        raise SegmentError("Config tts.segmentation must be an object")
    return segmentation


def speech_length(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def sentence_units(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text).strip()
    if not normalized:
        return []
    units = [
        value.strip()
        for value in re.split(r"(?<=[。！？!?；;])\s*|\n+", normalized)
        if value.strip()
    ]
    return units


def split_oversized(unit: str, max_chars: int) -> list[str]:
    if speech_length(unit) <= max_chars:
        return [unit]
    clauses = [
        value.strip()
        for value in re.split(r"(?<=[，,、：:])\s*", unit)
        if value.strip()
    ]
    parts: list[str] = []
    current = ""
    for clause in clauses:
        candidate = f"{current}{clause}" if current else clause
        if current and speech_length(candidate) > max_chars:
            parts.append(current)
            current = clause
        else:
            current = candidate
    if current:
        parts.append(current)

    bounded: list[str] = []
    for part in parts:
        if speech_length(part) <= max_chars:
            bounded.append(part)
            continue
        compact = re.sub(r"\s+", "", part)
        bounded.extend(compact[index : index + max_chars] for index in range(0, len(compact), max_chars))
    return bounded


def plan_segments(text: str, target_chars: int, max_chars: int) -> list[str]:
    units: list[str] = []
    for unit in sentence_units(text):
        units.extend(split_oversized(unit, max_chars))
    segments: list[str] = []
    current: list[str] = []
    for unit in units:
        candidate = "".join(current + [unit])
        if current and speech_length(candidate) > target_chars:
            segments.append("".join(current))
            current = [unit]
        else:
            current.append(unit)
    if current:
        segments.append("".join(current))
    return segments


def main() -> int:
    args = parse_args()
    try:
        config = read_segmentation_config(args.config)
        chars_per_second = args.chars_per_second or float(config.get("charsPerSecond", 4.0))
        target_seconds = args.target_seconds or float(config.get("targetSeconds", 30))
        max_seconds = args.max_seconds or float(config.get("maxSeconds", 45))
        if min(chars_per_second, target_seconds, max_seconds) <= 0:
            raise SegmentError("Segmentation values must be positive")
        if target_seconds > max_seconds:
            raise SegmentError("targetSeconds must not exceed maxSeconds")

        text = args.input.read_text(encoding="utf-8-sig").strip()
        if not text:
            raise SegmentError("Narration text is empty")
        target_chars = max(1, round(chars_per_second * target_seconds))
        max_chars = max(target_chars, round(chars_per_second * max_seconds))
        segments = plan_segments(text, target_chars, max_chars)
        if not segments:
            raise SegmentError("Narration could not be segmented")

        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        records = []
        for index, segment in enumerate(segments, start=1):
            path = output_dir / f"segment-{index:02d}.txt"
            path.write_text(segment + "\n", encoding="utf-8")
            length = speech_length(segment)
            records.append(
                {
                    "id": f"segment-{index:02d}",
                    "path": str(path),
                    "speechCharacters": length,
                    "estimatedSeconds": round(length / chars_per_second, 2),
                    "textSha256": hashlib.sha256(segment.encode("utf-8")).hexdigest(),
                }
            )

        manifest = {
            "schemaVersion": 1,
            "source": str(args.input.resolve()),
            "sourceTextSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "strategy": {
                "charsPerSecond": chars_per_second,
                "targetSeconds": target_seconds,
                "maxSeconds": max_seconds,
            },
            "segmentCount": len(records),
            "segments": records,
        }
        manifest_path = output_dir / "segments.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"ok": True, **manifest, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
        return 0
    except (SegmentError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
