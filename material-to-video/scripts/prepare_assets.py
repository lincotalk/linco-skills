#!/usr/bin/env python3
"""Copy selected manifest materials into stable HyperFrames asset paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MATERIAL_ID_PATTERN = re.compile(r"^m-[0-9a-f]{16}-[0-9a-f]{8}$")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--selected-ids", type=Path, help="Optional UTF-8 file with one material ID per line")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = read_json(args.manifest)
        roots = [Path(value).resolve() for value in manifest.get("inputRoots", [])]
        if not roots:
            raise ValueError("Manifest has no inputRoots")
        selected = None
        if args.selected_ids:
            selected = {line.strip() for line in args.selected_ids.read_text(encoding="utf-8-sig").splitlines() if line.strip()}
        items = manifest.get("items", [])
        if not isinstance(items, list):
            raise ValueError("Manifest items must be an array")
        manifest_ids = {
            item.get("id") for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if selected is not None:
            unknown = sorted(selected - manifest_ids)
            if unknown:
                raise ValueError("Unknown selected material IDs: " + ", ".join(unknown))
        project = args.project.resolve()
        destination = (project / "public" / "assets" / "source").resolve()
        try:
            destination.relative_to(project)
        except ValueError as exc:
            raise ValueError("Asset destination escapes the HyperFrames project") from exc
        destination.mkdir(parents=True, exist_ok=True)
        copied: list[dict[str, Any]] = []
        seen_hashes: dict[str, str] = {}
        for item in items:
            if not isinstance(item, dict) or item.get("category") == "unsupported" or item.get("exactDuplicate"):
                continue
            if selected is not None and item.get("id") not in selected:
                continue
            material_id = item.get("id")
            if not isinstance(material_id, str) or not MATERIAL_ID_PATTERN.fullmatch(material_id):
                raise ValueError(f"Invalid material ID: {material_id!r}")
            root_index = item.get("rootIndex")
            if not isinstance(root_index, int) or not 0 <= root_index < len(roots):
                raise ValueError(f"Invalid rootIndex for {item.get('id')}")
            root = roots[root_index]
            base = root.parent if root.is_file() else root
            source = (base / item["relativePath"]).resolve()
            try:
                source.relative_to(base.resolve())
            except ValueError as exc:
                raise ValueError(f"Material escapes its input root: {source}") from exc
            if not source.is_file():
                raise ValueError(f"Material is missing: {source}")
            digest = file_sha256(source)
            if digest != item.get("sha256"):
                raise ValueError(f"Material changed after scan: {source}")
            suffix = source.suffix.lower()
            target_name = seen_hashes.get(digest) or f"{material_id}{suffix}"
            target = (destination / target_name).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise ValueError(f"Asset target escapes its destination: {target_name}") from exc
            if digest not in seen_hashes:
                shutil.copy2(source, target)
                seen_hashes[digest] = target_name
            copied.append({
                "materialId": material_id,
                "sourceRelativePath": item["relativePath"],
                "projectPath": target.relative_to(project).as_posix(),
                "sha256": digest,
                "bytes": target.stat().st_size,
            })
        if not copied:
            raise ValueError("No selected supported assets were copied")
        payload = {
            "schemaVersion": 1,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "project": str(project),
            "assets": copied,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "copied": len(copied), "output": str(args.output.resolve())}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
