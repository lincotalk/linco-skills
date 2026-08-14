#!/usr/bin/env python3
"""Validate extracted material records and optional manual-review completion."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--selected-ids", type=Path)
    parser.add_argument("--require-reviewed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        record = json.loads(args.input.read_text(encoding="utf-8-sig"))
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        if not isinstance(record, dict) or not isinstance(manifest, dict):
            raise ValueError("input and manifest roots must be objects")
        if record.get("manifestSha256") != file_sha256(args.manifest):
            errors.append("manifestSha256 does not match the current MATERIALS.json")
        source_ids = {
            item.get("id")
            for item in manifest.get("items", [])
            if isinstance(item, dict)
            and item.get("category") != "unsupported"
            and not item.get("exactDuplicate")
        }
        seen: set[str] = set()
        items = record.get("items")
        if not isinstance(items, list) or not items:
            errors.append("items must be a non-empty array")
            items = []
        for index, item in enumerate(items):
            label = f"items[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label} must be an object")
                continue
            material_id = item.get("id")
            if material_id not in source_ids:
                errors.append(f"{label}.id is not a current supported material ID")
            if material_id in seen:
                errors.append(f"duplicate extracted material ID: {material_id}")
            if isinstance(material_id, str):
                seen.add(material_id)
            status = item.get("status")
            if status not in {"extracted", "metadata-only", "manual-review-required", "unsupported"}:
                errors.append(f"{label}.status is invalid")
            text = item.get("text")
            observations = item.get("manualObservations")
            reviewed = isinstance(observations, list) and any(
                isinstance(value, str) and value.strip() for value in observations
            )
            has_text = isinstance(text, str) and bool(text.strip())
            requirements = item.get("reviewRequirements")
            needs_review = isinstance(requirements, list) and bool(requirements)
            if status == "extracted" and not has_text:
                errors.append(f"{label} is extracted but has no text")
            if needs_review and not reviewed:
                message = f"{label} still requires manual review: {', '.join(map(str, requirements))}"
                if args.require_reviewed:
                    errors.append(message)
                else:
                    warnings.append(message)
            if not has_text and not reviewed and args.require_reviewed:
                errors.append(f"{label} has neither extracted text nor a manual observation")
        if args.selected_ids:
            selected = {
                line.strip()
                for line in args.selected_ids.read_text(encoding="utf-8-sig").splitlines()
                if line.strip()
            }
            missing = sorted(selected - seen)
            unexpected = sorted(seen - selected)
            if missing:
                errors.append("selected materials missing from extraction: " + ", ".join(missing))
            if unexpected:
                errors.append("extraction contains unselected materials: " + ", ".join(unexpected))
        if record.get("errors"):
            errors.append("extraction record contains unresolved extractor errors")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    result: dict[str, Any] = {"ok": not errors, "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for warning in warnings:
            print(f"WARNING: {warning}")
        if not errors and not warnings:
            print("Extracted materials valid.")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
