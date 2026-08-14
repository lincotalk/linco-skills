#!/usr/bin/env python3
"""Verify the basic delivery contract of a rendered MP4 with FFprobe."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--pixel-format", default="yuv420p")
    parser.add_argument("--require-audio", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    path = args.input.resolve()
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        errors.append("ffprobe is not installed or not on PATH")
    if path.suffix.lower() != ".mp4":
        errors.append(f"Expected an .mp4 file, found: {path.name}")
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f"Video is missing or empty: {path}")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 2
    command = [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(json.dumps({"ok": False, "errors": [result.stderr.strip() or "ffprobe failed"]}, ensure_ascii=False, indent=2))
        return 2
    try:
        probe: dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "errors": [f"ffprobe returned invalid JSON: {exc}"]}, ensure_ascii=False, indent=2))
        return 2
    streams = probe.get("streams", [])
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    audios = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(videos) != 1:
        errors.append(f"Expected one video stream, found {len(videos)}")
    else:
        video = videos[0]
        if video.get("width") != args.width or video.get("height") != args.height:
            errors.append(f"Expected {args.width}x{args.height}, found {video.get('width')}x{video.get('height')}")
        if video.get("codec_name") != "h264":
            errors.append(f"Expected H.264, found {video.get('codec_name')}")
        if video.get("pix_fmt") != args.pixel_format:
            errors.append(f"Expected pixel format {args.pixel_format}, found {video.get('pix_fmt')}")
        rate_value = video.get("avg_frame_rate") or video.get("r_frame_rate")
        try:
            frame_rate = float(Fraction(str(rate_value)))
        except (ValueError, ZeroDivisionError):
            frame_rate = 0.0
        if abs(frame_rate - args.fps) > 0.01:
            errors.append(f"Expected {args.fps:g} fps, found {rate_value}")
        sample_aspect_ratio = video.get("sample_aspect_ratio")
        if sample_aspect_ratio not in {None, "1:1", "0:1"}:
            errors.append(f"Expected square pixels, found SAR {sample_aspect_ratio}")
        rotation = video.get("tags", {}).get("rotate")
        for side_data in video.get("side_data_list", []):
            if isinstance(side_data, dict) and side_data.get("rotation") is not None:
                rotation = side_data["rotation"]
        try:
            rotation_value = float(rotation or 0)
        except (TypeError, ValueError):
            rotation_value = 0.0
        if rotation_value % 360 != 0:
            errors.append(f"Expected no rotation metadata, found {rotation_value:g} degrees")
    if args.require_audio and not audios:
        errors.append("Expected an audio stream")
    if audios and audios[0].get("codec_name") != "aac":
        errors.append(f"Expected AAC audio, found {audios[0].get('codec_name')}")
    try:
        format_info = probe.get("format", {})
        duration = float(format_info.get("duration", 0))
    except (TypeError, ValueError):
        duration = 0
        format_info = {}
    format_names = set(str(format_info.get("format_name", "")).split(","))
    if "mp4" not in format_names:
        errors.append(f"Expected MP4 container, found {format_info.get('format_name')}")
    if duration <= 0:
        errors.append("Video duration is missing or invalid")
    payload = {
        "ok": not errors,
        "input": str(path),
        "bytes": path.stat().st_size,
        "durationSeconds": duration,
        "video": videos[0] if videos else None,
        "audio": audios[0] if audios else None,
        "errors": errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
