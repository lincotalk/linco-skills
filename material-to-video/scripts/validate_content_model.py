#!/usr/bin/env python3
"""Validate a sourced material-to-video CONTENT_MODEL.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SOURCE_MODES = {"editorial-recut", "faithful", "visual-remix"}
INTAKE_MODES = {"provided-materials", "topic-research", "hybrid"}
EDITORIAL_MODES = {"general-explainer", "technical-single-point"}
PROOF_KINDS = {
    "trace",
    "code",
    "json",
    "terminal",
    "state-machine",
    "metric",
    "error-repair",
    "runtime-ui",
}
PROOF_AUTHENTICITY = {"real", "source-derived", "labeled-simulation"}
SECTIONS = {
    "claims": ("text",),
    "definitions": ("term", "explanation"),
    "relationships": ("from", "relation", "to", "explanation"),
    "examples": ("text",),
    "limitations": ("text",),
}


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


def source_ids(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    normalized = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return normalized if len(normalized) == len(value) else None


def material_ids(materials: dict[str, Any]) -> set[str]:
    items = materials.get("items")
    if not isinstance(items, list):
        raise ValueError("materials.items must be an array")
    return {
        str(item.get("id", "")).strip()
        for item in items
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }


def research_source_ids(research: dict[str, Any]) -> set[str]:
    sources = research.get("sources")
    if not isinstance(sources, list):
        raise ValueError("research sources.sources must be an array")
    return {
        str(source.get("id", "")).strip()
        for source in sources
        if isinstance(source, dict)
        and str(source.get("id", "")).strip()
        and source.get("selection") in {"selected", "supporting"}
    }


def validate(
    model: dict[str, Any], known_source_ids: set[str] | None = None
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    schema_version = model.get("schemaVersion")
    if schema_version not in {1, 2, 3}:
        errors.append("schemaVersion must be 1, 2, or 3")
    if schema_version in {2, 3}:
        intake_mode = str(model.get("intakeMode", "")).strip()
        if intake_mode not in INTAKE_MODES:
            errors.append(
                "intakeMode must be provided-materials, topic-research, or hybrid"
            )

    editorial_mode = str(model.get("editorialMode", "general-explainer")).strip()
    if schema_version == 3 and editorial_mode not in EDITORIAL_MODES:
        errors.append(
            "editorialMode must be general-explainer or technical-single-point"
        )

    mode = str(model.get("sourceMode", "")).strip()
    if mode not in SOURCE_MODES:
        errors.append(
            "sourceMode must be editorial-recut, faithful, or visual-remix"
        )

    thesis = model.get("centralThesis")
    if not isinstance(thesis, dict):
        errors.append("centralThesis must be an object")
    else:
        if not nonempty_text(thesis.get("text")):
            errors.append("centralThesis.text is required")
        ids = source_ids(thesis.get("sourceIds"))
        if ids is None:
            errors.append("centralThesis.sourceIds must be a non-empty string array")
        elif known_source_ids is not None:
            for source_id in ids:
                if source_id not in known_source_ids:
                    errors.append(
                        f"centralThesis references unknown sourceId '{source_id}'"
                    )

    audience = model.get("audienceValue")
    if not isinstance(audience, dict):
        errors.append("audienceValue must be an object")
    else:
        for key in ("viewerNeed", "promisedTakeaway"):
            if not nonempty_text(audience.get(key)):
                errors.append(f"audienceValue.{key} is required")

    seen_ids: set[str] = set()
    section_ids: dict[str, set[str]] = {section: set() for section in SECTIONS}
    core_claim_ids: set[str] = set()
    item_count = 0
    for section, required_fields in SECTIONS.items():
        raw_items = model.get(section)
        if not isinstance(raw_items, list):
            errors.append(f"{section} must be an array")
            continue
        for index, item in enumerate(raw_items):
            label = f"{section}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{label} must be an object")
                continue
            item_count += 1
            item_id = str(item.get("id", "")).strip()
            if not item_id:
                errors.append(f"{label}.id is required")
            elif item_id in seen_ids:
                errors.append(f"duplicate content id: {item_id}")
            else:
                seen_ids.add(item_id)
                section_ids[section].add(item_id)
            for field in required_fields:
                if not nonempty_text(item.get(field)):
                    errors.append(f"{label}.{field} is required")
            ids = source_ids(item.get("sourceIds"))
            if ids is None:
                errors.append(f"{label}.sourceIds must be a non-empty string array")
            elif known_source_ids is not None:
                for source_id in ids:
                    if source_id not in known_source_ids:
                        errors.append(f"{label} references unknown sourceId '{source_id}'")

            if section == "claims":
                importance = str(item.get("importance", "")).strip()
                if importance not in {"core", "supporting"}:
                    errors.append(f"{label}.importance must be core or supporting")
                elif importance == "core" and item_id:
                    core_claim_ids.add(item_id)

    if item_count == 0:
        errors.append("content model must contain at least one factual item")
    if not model.get("limitations"):
        warnings.append(
            "limitations is empty; confirm that the source truly contains no conditions or caveats"
        )

    if editorial_mode == "technical-single-point":
        if schema_version != 3:
            errors.append("technical-single-point requires schemaVersion 3")
        if len(core_claim_ids) != 1:
            errors.append(
                "technical-single-point requires exactly one claim with importance 'core'"
            )

        contract = model.get("technicalContract")
        if not isinstance(contract, dict):
            errors.append("technicalContract must be an object for technical-single-point")
        else:
            proposition_id = str(contract.get("propositionId", "")).strip()
            if proposition_id not in core_claim_ids:
                errors.append(
                    "technicalContract.propositionId must reference the single core claim"
                )

            mechanism = contract.get("mechanism")
            if not isinstance(mechanism, dict):
                errors.append("technicalContract.mechanism must be an object")
            else:
                for key in ("inputState", "transformation", "outputState"):
                    if not nonempty_text(mechanism.get(key)):
                        errors.append(f"technicalContract.mechanism.{key} is required")
                relationship_id = str(mechanism.get("relationshipId", "")).strip()
                if relationship_id not in section_ids["relationships"]:
                    errors.append(
                        "technicalContract.mechanism.relationshipId must reference a relationship"
                    )

            proof_objects = contract.get("proofObjects")
            if not isinstance(proof_objects, list) or not proof_objects:
                errors.append("technicalContract.proofObjects must be a non-empty array")
            else:
                proof_ids: set[str] = set()
                for index, proof in enumerate(proof_objects):
                    label = f"technicalContract.proofObjects[{index}]"
                    if not isinstance(proof, dict):
                        errors.append(f"{label} must be an object")
                        continue
                    proof_id = str(proof.get("id", "")).strip()
                    if not proof_id:
                        errors.append(f"{label}.id is required")
                    elif proof_id in proof_ids:
                        errors.append(f"duplicate proof object id: {proof_id}")
                    proof_ids.add(proof_id)
                    if proof.get("kind") not in PROOF_KINDS:
                        errors.append(f"{label}.kind is invalid")
                    if proof.get("authenticity") not in PROOF_AUTHENTICITY:
                        errors.append(f"{label}.authenticity is invalid")
                    if not nonempty_text(proof.get("description")):
                        errors.append(f"{label}.description is required")
                    raw_content_ids = proof.get("contentIds")
                    if not isinstance(raw_content_ids, list) or not raw_content_ids:
                        errors.append(f"{label}.contentIds must be a non-empty array")
                    else:
                        for content_id in raw_content_ids:
                            if content_id not in seen_ids:
                                errors.append(
                                    f"{label} references unknown contentId '{content_id}'"
                                )
                    ids = source_ids(proof.get("sourceIds"))
                    if ids is None:
                        errors.append(f"{label}.sourceIds must be a non-empty string array")
                    elif known_source_ids is not None:
                        for source_id in ids:
                            if source_id not in known_source_ids:
                                errors.append(
                                    f"{label} references unknown sourceId '{source_id}'"
                                )

            boundary_ids = contract.get("boundaryContentIds")
            if not isinstance(boundary_ids, list) or not boundary_ids:
                errors.append(
                    "technicalContract.boundaryContentIds must be a non-empty array"
                )
            else:
                for boundary_id in boundary_ids:
                    if boundary_id not in section_ids["limitations"]:
                        errors.append(
                            "technicalContract.boundaryContentIds must reference limitations"
                        )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--materials", type=Path)
    parser.add_argument("--research-sources", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        model = load_json(args.input)
        manifest_errors: list[str] = []
        source_contract_ready = True
        local_ids = material_ids(load_json(args.materials)) if args.materials else set()
        researched_ids = (
            research_source_ids(load_json(args.research_sources))
            if args.research_sources
            else set()
        )
        duplicate_source_ids = local_ids & researched_ids
        if duplicate_source_ids:
            manifest_errors.append(
                "source IDs overlap across manifests: "
                + ", ".join(sorted(duplicate_source_ids))
            )

        schema_version = model.get("schemaVersion")
        intake_mode = str(model.get("intakeMode", "")).strip()
        if schema_version in {2, 3}:
            if intake_mode in {"provided-materials", "hybrid"} and not args.materials:
                manifest_errors.append(f"{intake_mode} requires --materials")
                source_contract_ready = False
            if intake_mode in {"topic-research", "hybrid"} and not args.research_sources:
                manifest_errors.append(f"{intake_mode} requires --research-sources")
                source_contract_ready = False
            if intake_mode == "provided-materials" and args.research_sources:
                manifest_errors.append(
                    "provided-materials must not include --research-sources; use hybrid"
                )
            if intake_mode == "topic-research" and args.materials:
                manifest_errors.append(
                    "topic-research must not include --materials; use hybrid"
                )

        known = (
            local_ids | researched_ids
            if source_contract_ready
            and (args.materials or args.research_sources or schema_version == 2)
            else None
        )
        errors, warnings = validate(model, known)
        errors = manifest_errors + errors
    except ValueError as exc:
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
            print(f"Content model valid ({len(warnings)} warning(s)).")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
