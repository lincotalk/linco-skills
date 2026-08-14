#!/usr/bin/env python3
"""Validate a traceable material-to-video RESEARCH_SOURCES.json."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


INTAKE_MODES = {"topic-research", "hybrid"}
SOURCE_TYPES = {
    "official",
    "documentation",
    "standard",
    "paper",
    "dataset",
    "news",
    "analysis",
    "other",
}
SELECTIONS = {"selected", "supporting", "rejected"}
EVIDENCE_KINDS = {"quote", "paraphrase", "data"}
VISUAL_STATUSES = {"cleared", "restricted", "not-cleared"}
CONFLICT_STATUSES = {"resolved", "requires-user"}
PRIMARY_TYPES = {"official", "documentation", "standard", "paper", "dataset"}


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


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_timestamp(value: Any) -> bool:
    if not nonempty_text(value):
        return False
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def valid_optional_date(value: Any) -> bool:
    if value is None:
        return True
    if not nonempty_text(value):
        return False
    raw = str(value).strip()
    try:
        if "T" in raw:
            datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            date.fromisoformat(raw)
    except ValueError:
        return False
    return True


def valid_http_url(value: Any) -> bool:
    if not nonempty_text(value):
        return False
    parsed = urlparse(str(value).strip())
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and parsed.username is None
        and parsed.password is None
    )


def string_ids(value: Any, minimum: int = 1) -> list[str] | None:
    if not isinstance(value, list) or len(value) < minimum:
        return None
    normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return normalized if len(normalized) == len(value) else None


def validate(record: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if record.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    intake_mode = str(record.get("intakeMode", "")).strip()
    if intake_mode not in INTAKE_MODES:
        errors.append("intakeMode must be topic-research or hybrid")
    for key in ("topic", "researchQuestion"):
        if not nonempty_text(record.get(key)):
            errors.append(f"{key} is required")
    if not valid_timestamp(record.get("researchedAt")):
        errors.append("researchedAt must be an ISO 8601 timestamp with timezone")
    cutoff = record.get("researchCutoff")
    try:
        date.fromisoformat(str(cutoff))
    except ValueError:
        errors.append("researchCutoff must be an ISO date (YYYY-MM-DD)")

    sources = record.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a non-empty array")
        sources = []

    seen_source_ids: set[str] = set()
    seen_urls: set[str] = set()
    included_count = 0
    selected_count = 0
    primary_count = 0
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label} must be an object")
            continue

        source_id = str(source.get("id", "")).strip()
        if not source_id.startswith("r-") or len(source_id) <= 2:
            errors.append(f"{label}.id must be a stable r- source ID")
        elif source_id in seen_source_ids:
            errors.append(f"duplicate source id: {source_id}")
        else:
            seen_source_ids.add(source_id)

        raw_url = str(source.get("url", "")).strip()
        if not valid_http_url(raw_url):
            errors.append(f"{label}.url must be an HTTP or HTTPS URL without credentials")
        elif raw_url in seen_urls:
            errors.append(f"duplicate source URL: {raw_url}")
        else:
            seen_urls.add(raw_url)
        for key in ("title", "publisher"):
            if not nonempty_text(source.get(key)):
                errors.append(f"{label}.{key} is required")

        source_type = str(source.get("sourceType", "")).strip()
        if source_type not in SOURCE_TYPES:
            errors.append(
                f"{label}.sourceType must be one of {', '.join(sorted(SOURCE_TYPES))}"
            )
        if not valid_optional_date(source.get("publishedAt")):
            errors.append(f"{label}.publishedAt must be null, an ISO date, or ISO timestamp")
        if not valid_timestamp(source.get("accessedAt")):
            errors.append(f"{label}.accessedAt must be an ISO 8601 timestamp with timezone")

        selection = str(source.get("selection", "")).strip()
        if selection not in SELECTIONS:
            errors.append(
                f"{label}.selection must be selected, supporting, or rejected"
            )
        included = selection in {"selected", "supporting"}
        if included:
            included_count += 1
            selected_count += selection == "selected"
            primary_count += source_type in PRIMARY_TYPES

        evidence = source.get("evidence", [] if not included else None)
        if not isinstance(evidence, list) or (included and not evidence):
            errors.append(f"{label}.evidence must be a non-empty array for included sources")
            evidence = []
        seen_evidence_ids: set[str] = set()
        for evidence_index, item in enumerate(evidence):
            evidence_label = f"{label}.evidence[{evidence_index}]"
            if not isinstance(item, dict):
                errors.append(f"{evidence_label} must be an object")
                continue
            evidence_id = str(item.get("id", "")).strip()
            if not evidence_id:
                errors.append(f"{evidence_label}.id is required")
            elif evidence_id in seen_evidence_ids:
                errors.append(f"{label} contains duplicate evidence id: {evidence_id}")
            else:
                seen_evidence_ids.add(evidence_id)
            if str(item.get("kind", "")).strip() not in EVIDENCE_KINDS:
                errors.append(f"{evidence_label}.kind must be quote, paraphrase, or data")
            for key in ("text", "locator"):
                if not nonempty_text(item.get(key)):
                    errors.append(f"{evidence_label}.{key} is required")

        visual_use = source.get("visualUse")
        if not isinstance(visual_use, dict):
            errors.append(f"{label}.visualUse must be an object")
        else:
            if str(visual_use.get("status", "")).strip() not in VISUAL_STATUSES:
                errors.append(
                    f"{label}.visualUse.status must be cleared, restricted, or not-cleared"
                )
            if not nonempty_text(visual_use.get("basis")):
                errors.append(f"{label}.visualUse.basis is required")

    if selected_count == 0:
        errors.append("at least one source must have selection 'selected'")
    if 0 < included_count < 2:
        warnings.append("only one included source; cross-check it when the claim is time-sensitive or consequential")
    if included_count and primary_count == 0:
        warnings.append("no primary or authoritative source type is included")

    conflicts = record.get("conflicts")
    if not isinstance(conflicts, list):
        errors.append("conflicts must be an array")
        conflicts = []
    for index, conflict in enumerate(conflicts):
        label = f"conflicts[{index}]"
        if not isinstance(conflict, dict):
            errors.append(f"{label} must be an object")
            continue
        if not nonempty_text(conflict.get("topic")):
            errors.append(f"{label}.topic is required")
        ids = string_ids(conflict.get("sourceIds"), minimum=2)
        if ids is None:
            errors.append(f"{label}.sourceIds must contain at least two source IDs")
        else:
            for source_id in ids:
                if source_id not in seen_source_ids:
                    errors.append(f"{label} references unknown sourceId '{source_id}'")
        status = str(conflict.get("status", "")).strip()
        if status not in CONFLICT_STATUSES:
            errors.append(f"{label}.status must be resolved or requires-user")
        elif status == "requires-user":
            errors.append(f"{label} requires user resolution")
        elif not nonempty_text(conflict.get("resolution")):
            errors.append(f"{label}.resolution is required when status is resolved")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        errors, warnings = validate(load_json(args.input))
    except (OSError, ValueError) as exc:
        errors, warnings = [str(exc)], []

    result = {"ok": not errors, "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for warning in warnings:
            print(f"WARNING: {warning}")
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if not errors:
            print(f"Research sources valid ({len(warnings)} warning(s)).")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
