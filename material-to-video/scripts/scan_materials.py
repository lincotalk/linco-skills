#!/usr/bin/env python3
"""Scan local material paths into a stable, content-addressed manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import struct
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
    ".pdf": "document",
    ".docx": "document",
    ".pptx": "document",
    ".txt": "text",
    ".md": "text",
    ".html": "text",
    ".htm": "text",
    ".wav": "audio",
    ".mp3": "audio",
    ".m4a": "audio",
    ".mp4": "video",
    ".mov": "video",
    ".webm": "video",
}

IGNORED_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}
VARIANT_MARKERS = re.compile(r"(^|[\s._-])(final|old|new|draft|rev\d*|x)([\s._-]|$)|改|新版|旧版|终稿|定稿", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def natural_key(value: str) -> list[tuple[int, Any]]:
    parts = re.split(r"(\d+)", value.casefold())
    return [(1, int(part)) if part.isdigit() else (0, part) for part in parts if part]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sniff_mime(path: Path) -> str:
    with path.open("rb") as handle:
        head = handle.read(32)
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "image/gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
        return "audio/wav"
    if head.startswith(b"ID3") or head[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
        return "audio/mpeg"
    if head.startswith(b"PK\x03\x04") and path.suffix.lower() == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if head.startswith(b"PK\x03\x04") and path.suffix.lower() == ".pptx":
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def image_dimensions(path: Path, mime: str) -> dict[str, int] | None:
    try:
        with path.open("rb") as handle:
            if mime == "image/png":
                handle.seek(16)
                width, height = struct.unpack(">II", handle.read(8))
                return {"width": width, "height": height}
            if mime == "image/gif":
                handle.seek(6)
                width, height = struct.unpack("<HH", handle.read(4))
                return {"width": width, "height": height}
            if mime == "image/jpeg":
                handle.seek(2)
                while True:
                    byte = handle.read(1)
                    if not byte:
                        return None
                    if byte != b"\xff":
                        continue
                    marker = handle.read(1)
                    while marker == b"\xff":
                        marker = handle.read(1)
                    if marker in {bytes([value]) for value in range(0xC0, 0xC4)} | {bytes([value]) for value in range(0xC5, 0xC8)} | {bytes([value]) for value in range(0xC9, 0xCC)} | {bytes([value]) for value in range(0xCD, 0xD0)}:
                        handle.read(3)
                        height, width = struct.unpack(">HH", handle.read(4))
                        return {"width": width, "height": height}
                    length_bytes = handle.read(2)
                    if len(length_bytes) != 2:
                        return None
                    length = struct.unpack(">H", length_bytes)[0]
                    handle.seek(max(length - 2, 0), os.SEEK_CUR)
    except (OSError, struct.error):
        return None
    return None


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def is_excluded(path: Path, excluded_roots: list[Path]) -> bool:
    return any(is_within(path, root) for root in excluded_roots)


def iter_files(root: Path, max_depth: int, excluded_roots: list[Path]) -> list[Path]:
    if root.is_file():
        return [] if is_excluded(root, excluded_roots) else [root]
    root_depth = len(root.parts)
    files: list[Path] = []
    for current, directories, names in os.walk(root, followlinks=False):
        current_path = Path(current)
        if is_excluded(current_path, excluded_roots):
            directories[:] = []
            continue
        depth = len(current_path.parts) - root_depth
        directories[:] = sorted(
            [
                name
                for name in directories
                if not (current_path / name).is_symlink()
                and not is_excluded(current_path / name, excluded_roots)
                and depth < max_depth
            ],
            key=natural_key,
        )
        for name in sorted(names, key=natural_key):
            path = current_path / name
            if (
                name.casefold() in IGNORED_NAMES
                or path.is_symlink()
                or is_excluded(path, excluded_roots)
            ):
                continue
            files.append(path)
    return files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--exclude", action="append", default=[], type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-files", type=int, default=5000)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--max-file-mb", type=int, default=1024)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_files <= 0 or args.max_depth < 0 or args.max_file_mb <= 0:
        print(json.dumps({"ok": False, "errors": ["scan limits must be positive"]}, ensure_ascii=False, indent=2))
        return 2
    errors: list[str] = []
    roots: list[Path] = []
    for raw in args.input:
        path = raw.expanduser().resolve()
        if not path.exists():
            errors.append(f"Input does not exist: {path}")
        else:
            roots.append(path)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 2

    excluded_roots = [path.expanduser().resolve() for path in args.exclude]
    output_path = args.output.expanduser().resolve()
    if output_path not in excluded_roots:
        excluded_roots.append(output_path)

    discovered: list[tuple[int, Path, Path]] = []
    for index, root in enumerate(roots):
        base = root.parent if root.is_file() else root
        for path in iter_files(root, args.max_depth, excluded_roots):
            discovered.append((index, base, path))
            if len(discovered) > args.max_files:
                print(json.dumps({"ok": False, "errors": [f"Material count exceeds --max-files={args.max_files}"]}, ensure_ascii=False, indent=2))
                return 2

    items: list[dict[str, Any]] = []
    hash_groups: dict[str, list[str]] = defaultdict(list)
    max_bytes = args.max_file_mb * 1024 * 1024
    for root_index, base, path in discovered:
        stat = path.stat()
        extension = path.suffix.lower()
        category = SUPPORTED_EXTENSIONS.get(extension, "unsupported")
        warning: list[str] = []
        if stat.st_size > max_bytes:
            category = "unsupported"
            warning.append(f"file exceeds {args.max_file_mb} MB")
            digest = None
        else:
            digest = sha256(path)
        relative = path.relative_to(base).as_posix()
        occurrence_key = f"{root_index}:{relative}".encode("utf-8")
        occurrence_digest = hashlib.sha256(occurrence_key).hexdigest()[:8]
        if digest:
            item_id = f"m-{digest[:16]}-{occurrence_digest}"
        else:
            oversized_key = f"{root_index}:{relative}:{stat.st_size}:{stat.st_mtime_ns}".encode("utf-8")
            item_id = f"u-{hashlib.sha256(oversized_key).hexdigest()[:24]}"
        mime = sniff_mime(path)
        dimensions = image_dimensions(path, mime) if category == "image" else None
        if VARIANT_MARKERS.search(path.stem) or any(VARIANT_MARKERS.search(part) for part in path.parts):
            warning.append("possible version variant")
        item: dict[str, Any] = {
            "id": item_id,
            "rootIndex": root_index,
            "relativePath": relative,
            "name": path.name,
            "extension": extension,
            "category": category,
            "mime": mime,
            "bytes": stat.st_size,
            "sha256": digest,
            "modifiedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "warnings": warning,
        }
        if dimensions:
            item["dimensions"] = dimensions
        items.append(item)
        if digest:
            hash_groups[digest].append(item_id)

    duplicates = [ids for ids in hash_groups.values() if len(ids) > 1]
    duplicate_ids = {item_id for group in duplicates for item_id in group[1:]}
    for item in items:
        item["exactDuplicate"] = item["id"] in duplicate_ids

    category_counts = Counter(item["category"] for item in items)
    manifest = {
        "schemaVersion": 1,
        "generatedAt": utc_now(),
        "inputRoots": [str(root) for root in roots],
        "excludedRoots": [str(root) for root in excluded_roots],
        "summary": {
            "total": len(items),
            "supported": sum(count for category, count in category_counts.items() if category != "unsupported"),
            "unsupported": category_counts.get("unsupported", 0),
            "exactDuplicateGroups": len(duplicates),
            "categories": dict(sorted(category_counts.items())),
        },
        "duplicateGroups": duplicates,
        "items": items,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = manifest["summary"]["supported"] > 0
    print(json.dumps({"ok": ok, "output": str(args.output.resolve()), "summary": manifest["summary"]}, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
