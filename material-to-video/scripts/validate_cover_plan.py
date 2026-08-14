#!/usr/bin/env python3
"""Validate a platform cover plan and optionally verify rendered image files."""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from pathlib import Path, PurePosixPath
from typing import Any


PLATFORMS = ("douyin", "xiaohongshu", "wechat-channels")
VERIFICATION_MODES = {"preset-fallback", "user-supplied", "runtime-verified"}
COMPOSITION_MODES = {"authored", "adapted-master"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def ratio_matches(value: Any, width: int, height: int) -> bool:
    if not isinstance(value, str) or ":" not in value:
        return False
    left, right = value.split(":", 1)
    try:
        ratio_width = int(left)
        ratio_height = int(right)
    except ValueError:
        return False
    return ratio_width > 0 and ratio_height > 0 and width * ratio_height == height * ratio_width


def expected_entries(
    cover_config: dict[str, Any], platform: str, key: str
) -> list[dict[str, Any]]:
    collection = cover_config.get(key)
    if not isinstance(collection, dict):
        raise ValueError(f"config.cover.{key} must be an object")
    platforms = PLATFORMS if platform == "universal" else (platform,)
    result: list[dict[str, Any]] = []
    for name in platforms:
        entries = collection.get(name)
        if not isinstance(entries, list):
            raise ValueError(f"config.cover.{key}.{name} must be an array")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"config.cover.{key}.{name} entries must be objects")
            result.append(entry)
    return result


def content_model_ids(model: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for section in ("claims", "definitions", "relationships", "examples", "limitations"):
        values = model.get(section, [])
        if not isinstance(values, list):
            raise ValueError(f"content model {section} must be an array")
        for item in values:
            if isinstance(item, dict):
                item_id = str(item.get("id", "")).strip()
                if item_id:
                    ids.add(item_id)
    return ids


def validate_relative_output(value: Any, prefix: str, label: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return f"{label}.output is required"
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return f"{label}.output must be a safe job-relative path"
    if path.parts[0] != prefix:
        return f"{label}.output must be inside {prefix}/"
    return None


def validate_critical_area(
    value: Any, width: int, height: int, margin: int, label: str
) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{label}.criticalArea must be an object"]
    values: dict[str, int] = {}
    for key in ("x", "y", "width", "height"):
        raw = value.get(key)
        if key in {"x", "y"}:
            if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
                errors.append(f"{label}.criticalArea.{key} must be a non-negative integer")
                continue
        elif positive_int(raw) is None:
            errors.append(f"{label}.criticalArea.{key} must be a positive integer")
            continue
        values[key] = raw
    if len(values) != 4:
        return errors
    if values["x"] + values["width"] > width or values["y"] + values["height"] > height:
        errors.append(f"{label}.criticalArea exceeds the cover bounds")
    if (
        values["x"] < margin
        or values["y"] < margin
        or width - values["x"] - values["width"] < margin
        or height - values["y"] - values["height"] < margin
    ):
        errors.append(f"{label}.criticalArea must preserve at least {margin}px on every side")
    return errors


def png_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) >= 24 and header.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", header[16:24])
    return None


def jpeg_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            return None
        while True:
            marker_start = handle.read(1)
            if not marker_start:
                return None
            if marker_start != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if marker in {bytes([value]) for value in range(0xC0, 0xC4)} | {
                bytes([value]) for value in range(0xC5, 0xC8)
            } | {bytes([value]) for value in range(0xC9, 0xCC)} | {
                bytes([value]) for value in range(0xCD, 0xD0)
            }:
                handle.read(3)
                image_height, image_width = struct.unpack(">HH", handle.read(4))
                return image_width, image_height
            length_bytes = handle.read(2)
            if len(length_bytes) != 2:
                return None
            length = struct.unpack(">H", length_bytes)[0]
            handle.seek(max(length - 2, 0), os.SEEK_CUR)


def image_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        if path.suffix.lower() == ".png":
            return png_dimensions(path)
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            return jpeg_dimensions(path)
    except (OSError, struct.error):
        return None
    return None


def validate_entries(
    actual: Any,
    expected: list[dict[str, Any]],
    key: str,
    path_prefix: str,
    safe_margin: int,
    base: Path,
    check_files: bool,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(actual, list):
        return [f"{key} must be an array"]
    expected_by_id = {str(entry.get("id", "")): entry for entry in expected}
    actual_ids = [str(entry.get("id", "")) for entry in actual if isinstance(entry, dict)]
    if len(actual_ids) != len(set(actual_ids)):
        errors.append(f"{key} contains duplicate ids")
    if set(actual_ids) != set(expected_by_id):
        errors.append(
            f"{key} ids must be exactly {sorted(expected_by_id)}; got {sorted(actual_ids)}"
        )

    for index, entry in enumerate(actual):
        label = f"{key}[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        entry_id = str(entry.get("id", ""))
        expected_entry = expected_by_id.get(entry_id)
        if expected_entry is None:
            continue
        width = positive_int(entry.get("width"))
        height = positive_int(entry.get("height"))
        expected_width = expected_entry.get("width")
        expected_height = expected_entry.get("height")
        if width != expected_width or height != expected_height:
            errors.append(
                f"{label} must be {expected_width}x{expected_height} for {entry_id}"
            )
            continue
        if entry.get("ratio") != expected_entry.get("ratio") or not ratio_matches(
            entry.get("ratio"), width, height
        ):
            errors.append(f"{label}.ratio does not match its dimensions or preset")
        if entry.get("output") != expected_entry.get("output"):
            errors.append(f"{label}.output does not match the versioned preset")
        output_error = validate_relative_output(entry.get("output"), path_prefix, label)
        if output_error:
            errors.append(output_error)
        if key == "variants":
            errors.extend(
                validate_critical_area(
                    entry.get("criticalArea"), width, height, safe_margin, label
                )
            )
        elif entry.get("sourceVariantId") != expected_entry.get("sourceVariantId"):
            errors.append(f"{label}.sourceVariantId does not match the preset")

        if check_files and not output_error:
            output_path = (base / str(entry["output"])).resolve()
            try:
                output_path.relative_to(base.resolve())
            except ValueError:
                errors.append(f"{label}.output escapes the job directory")
                continue
            if not output_path.is_file() or output_path.stat().st_size == 0:
                errors.append(f"{label}.output is missing or empty")
            elif image_dimensions(output_path) != (width, height):
                errors.append(f"{label}.output dimensions do not match the plan")
    return errors


def validate(
    plan: dict[str, Any],
    config: dict[str, Any],
    visual_plan: dict[str, Any] | None,
    content_model: dict[str, Any] | None,
    base: Path,
    check_files: bool,
) -> list[str]:
    errors: list[str] = []
    if plan.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    platform = str(plan.get("platform", "")).strip()
    if platform not in {*PLATFORMS, "universal"}:
        errors.append("platform must be douyin, xiaohongshu, wechat-channels, or universal")
        return errors

    video_config = config.get("video")
    cover_config = config.get("cover")
    if not isinstance(video_config, dict) or not isinstance(cover_config, dict):
        raise ValueError("config.video and config.cover must be objects")
    configured_platform = video_config.get("platform")
    if configured_platform is not None and platform != configured_platform:
        errors.append("platform does not match config.video.platform")
    if plan.get("specRevision") != cover_config.get("specRevision"):
        errors.append("specRevision does not match config.cover.specRevision")

    verification_mode = str(plan.get("verificationMode", "")).strip()
    if verification_mode not in VERIFICATION_MODES:
        errors.append(
            "verificationMode must be preset-fallback, user-supplied, or runtime-verified"
        )
    if not str(plan.get("verificationNote", "")).strip():
        errors.append("verificationNote is required")

    canvas = plan.get("videoCanvas")
    if not isinstance(canvas, dict):
        errors.append("videoCanvas must be an object")
    else:
        width = positive_int(canvas.get("width"))
        height = positive_int(canvas.get("height"))
        if width != video_config.get("width") or height != video_config.get("height"):
            errors.append("videoCanvas dimensions do not match config.video")
        elif canvas.get("ratio") != video_config.get("aspectRatio") or not ratio_matches(
            canvas.get("ratio"), width, height
        ):
            errors.append("videoCanvas.ratio does not match its dimensions or config.video")

    if not str(plan.get("title", "")).strip():
        errors.append("title is required")
    raw_content_ids = plan.get("contentIds")
    if (
        not isinstance(raw_content_ids, list)
        or not raw_content_ids
        or any(not isinstance(item, str) or not item.strip() for item in raw_content_ids)
    ):
        errors.append("contentIds must be a non-empty string array")
    elif content_model is not None:
        known_ids = content_model_ids(content_model)
        for content_id in raw_content_ids:
            if content_id not in known_ids:
                errors.append(f"unknown contentId '{content_id}'")
    title_lines = positive_int(plan.get("titleLineCount"))
    max_title_lines = positive_int(cover_config.get("maxTitleLines"))
    if title_lines is None or max_title_lines is None or title_lines > max_title_lines:
        errors.append(f"titleLineCount must be from 1 to {max_title_lines or 0}")
    if plan.get("compositionMode") not in COMPOSITION_MODES:
        errors.append("compositionMode must be authored or adapted-master")

    font_family = str(plan.get("fontFamily", "")).strip()
    if not font_family:
        errors.append("fontFamily is required")
    if visual_plan is not None:
        font_policy = visual_plan.get("fontPolicy")
        expected_family = (
            str(font_policy.get("primaryCjkFamily", "")).strip()
            if isinstance(font_policy, dict)
            else ""
        )
        if expected_family and font_family != expected_family:
            errors.append("fontFamily does not match VISUAL_PLAN.fontPolicy.primaryCjkFamily")

    safe_margin = positive_int(cover_config.get("minSafeMarginPx"))
    if safe_margin is None:
        raise ValueError("config.cover.minSafeMarginPx must be a positive integer")
    variants = expected_entries(cover_config, platform, "platformVariants")
    previews = expected_entries(cover_config, platform, "platformPreviews")
    errors.extend(
        validate_entries(
            plan.get("variants"), variants, "variants", "final", safe_margin, base, check_files
        )
    )
    errors.extend(
        validate_entries(
            plan.get("displayPreviews"),
            previews,
            "displayPreviews",
            "review",
            safe_margin,
            base,
            check_files,
        )
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="COVER_PLAN.json")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--visual-plan", type=Path)
    parser.add_argument("--content-model", type=Path)
    parser.add_argument("--check-files", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        plan = load_json(args.input)
        config = load_json(args.config)
        visual_plan = load_json(args.visual_plan) if args.visual_plan else None
        content_model = load_json(args.content_model) if args.content_model else None
        errors = validate(
            plan,
            config,
            visual_plan,
            content_model,
            args.input.resolve().parent,
            args.check_files,
        )
    except (OSError, ValueError) as exc:
        errors = [str(exc)]

    result = {"ok": not errors, "errors": errors}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if not errors:
            print("Cover plan valid.")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
