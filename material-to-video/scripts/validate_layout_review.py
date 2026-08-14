#!/usr/bin/env python3
"""Validate final temporal layout-review evidence against a VISUAL_PLAN.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


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


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        return None
    return value


def validate(review: dict[str, Any], plan: dict[str, Any], base: Path) -> list[str]:
    errors: list[str] = []
    if review.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")

    tolerance = number(review.get("containmentTolerancePx"))
    if tolerance is None or tolerance < 0:
        errors.append("containmentTolerancePx must be a non-negative number")

    primary_family = ""
    font_policy = plan.get("fontPolicy")
    if isinstance(font_policy, dict):
        primary_family = str(font_policy.get("primaryCjkFamily", "")).strip()

    expected: dict[tuple[str, str], tuple[float, set[str]]] = {}
    scenes = plan.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("visual plan scenes must be an array")
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("id", "")).strip()
        containment = scene.get("containment")
        container_ids: set[str] = set()
        if isinstance(containment, dict) and containment.get("mode") == "strict":
            raw_ids = string_list(containment.get("containerIds"))
            if raw_ids is not None:
                container_ids = set(raw_ids)
        moments = scene.get("reviewMoments")
        if not isinstance(moments, list):
            continue
        for moment in moments:
            if not isinstance(moment, dict):
                continue
            phase = str(moment.get("phase", "")).strip()
            at = number(moment.get("atSec"))
            if scene_id and phase and at is not None:
                expected[(scene_id, phase)] = (at, container_ids)

    checks = review.get("checks")
    if not isinstance(checks, list):
        errors.append("checks must be an array")
        return errors

    found: set[tuple[str, str]] = set()
    screenshot_paths: set[Path] = set()
    for index, check in enumerate(checks):
        label = f"checks[{index}]"
        if not isinstance(check, dict):
            errors.append(f"{label} must be an object")
            continue
        key = (
            str(check.get("sceneId", "")).strip(),
            str(check.get("phase", "")).strip(),
        )
        if key not in expected:
            errors.append(f"{label}: unexpected sceneId/phase {key!r}")
            continue
        if key in found:
            errors.append(f"{label}: duplicate sceneId/phase {key!r}")
            continue
        found.add(key)

        expected_at, expected_containers = expected[key]
        actual_at = number(check.get("atSec"))
        if actual_at is None or abs(actual_at - expected_at) > 0.01:
            errors.append(f"{label}: atSec does not match the visual plan")

        screenshot = str(check.get("screenshot", "")).strip()
        raw_screenshot_path = Path(screenshot) if screenshot else None
        screenshot_path = (
            (base / raw_screenshot_path).resolve()
            if raw_screenshot_path is not None and not raw_screenshot_path.is_absolute()
            else None
        )
        if screenshot_path is not None:
            try:
                screenshot_path.relative_to(base.resolve())
            except ValueError:
                screenshot_path = None
        if (
            screenshot_path is None
            or not screenshot_path.is_file()
            or screenshot_path.stat().st_size == 0
        ):
            errors.append(
                f"{label}: screenshot must point to a non-empty file inside the review directory"
            )
        elif screenshot_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            errors.append(f"{label}: screenshot must use a supported image extension")
        elif screenshot_path in screenshot_paths:
            errors.append(f"{label}: every review moment requires a unique screenshot")
        else:
            screenshot_paths.add(screenshot_path)

        checked_ids = string_list(check.get("checkedContainerIds"))
        if checked_ids is None or set(checked_ids) != expected_containers:
            errors.append(f"{label}: checkedContainerIds do not match the visual plan")

        font_result = check.get("fontResult")
        if not isinstance(font_result, dict):
            errors.append(f"{label}: fontResult must be an object")
        else:
            actual_family = str(font_result.get("primaryFamily", "")).strip()
            if primary_family and actual_family != primary_family:
                errors.append(f"{label}: primary font does not match fontPolicy")
            if font_result.get("loaded") is not True:
                errors.append(f"{label}: primary font was not loaded")
            if font_result.get("fallbackMismatch") is not False:
                errors.append(f"{label}: rendered glyphs have a fallback mismatch")

        if check.get("blankFrame") is not False:
            errors.append(f"{label}: frame is blank or blank-frame status is missing")
        if check.get("safeAreaOk") is not True:
            errors.append(f"{label}: safe-area check failed")
        if check.get("captionOverlap") is not False:
            errors.append(f"{label}: caption overlap detected")
        if check.get("clippedText") is not False:
            errors.append(f"{label}: clipped text detected")
        violations = check.get("violations")
        if not isinstance(violations, list) or violations:
            errors.append(f"{label}: violations must be an empty array")

    missing = sorted(set(expected) - found)
    for scene_id, phase in missing:
        errors.append(f"missing review check for {scene_id}/{phase}")

    editorial_mode = str(plan.get("editorialMode", "general-explainer")).strip()
    if editorial_mode == "technical-single-point":
        technical = review.get("technicalReview")
        if not isinstance(technical, dict):
            errors.append("technicalReview must be an object for technical-single-point")
        else:
            for key in (
                "singlePropositionOk",
                "proofReadable",
                "proofAuthenticityClear",
                "stateChainComplete",
                "semanticColorsConsistent",
                "boundaryVisible",
                "mutedComprehensionOk",
                "audioOnlyContinuityOk",
            ):
                if technical.get(key) is not True:
                    errors.append(f"technicalReview.{key} must be true")

        expected_transitions: dict[tuple[str, str], dict[str, Any]] = {}
        valid_scenes = [scene for scene in scenes if isinstance(scene, dict)]
        for left, right in zip(valid_scenes, valid_scenes[1:]):
            left_id = str(left.get("id", "")).strip()
            right_id = str(right.get("id", "")).strip()
            continuity = right.get("transitionContinuity")
            if left_id and right_id and isinstance(continuity, dict):
                expected_transitions[(left_id, right_id)] = continuity

        transition_checks = review.get("transitionChecks")
        if not isinstance(transition_checks, list):
            errors.append("transitionChecks must be an array for technical-single-point")
            transition_checks = []
        found_transitions: set[tuple[str, str]] = set()
        for index, check in enumerate(transition_checks):
            label = f"transitionChecks[{index}]"
            if not isinstance(check, dict):
                errors.append(f"{label} must be an object")
                continue
            pair = (
                str(check.get("fromSceneId", "")).strip(),
                str(check.get("toSceneId", "")).strip(),
            )
            if pair not in expected_transitions:
                errors.append(f"{label}: unexpected scene boundary {pair!r}")
                continue
            if pair in found_transitions:
                errors.append(f"{label}: duplicate scene boundary {pair!r}")
                continue
            found_transitions.add(pair)

            screenshot = str(check.get("midpointScreenshot", "")).strip()
            raw_path = Path(screenshot) if screenshot else None
            path = (
                (base / raw_path).resolve()
                if raw_path is not None and not raw_path.is_absolute()
                else None
            )
            if path is not None:
                try:
                    path.relative_to(base.resolve())
                except ValueError:
                    path = None
            if path is None or not path.is_file() or path.stat().st_size == 0:
                errors.append(
                    f"{label}: midpointScreenshot must be a non-empty file inside the review directory"
                )

            continuity = expected_transitions[pair]
            if check.get("continuityType") != continuity.get("type"):
                errors.append(f"{label}: continuityType does not match the visual plan")
            if check.get("audioBridge") != continuity.get("audioBridge"):
                errors.append(f"{label}: audioBridge does not match the visual plan")
            if check.get("anchorOrBreakOk") is not True:
                errors.append(f"{label}: transition anchor or deliberate break failed")
            if check.get("semanticColorOk") is not True:
                errors.append(f"{label}: semantic color continuity failed")
            if check.get("readableAtMidpoint") is not True:
                errors.append(f"{label}: transition midpoint is not readable")

        for left, right in sorted(set(expected_transitions) - found_transitions):
            errors.append(f"missing transition review for {left} -> {right}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="LAYOUT_REVIEW.json")
    parser.add_argument("--visual-plan", required=True, type=Path, help="VISUAL_PLAN.json")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable results")
    args = parser.parse_args()

    try:
        review = load_json(args.input)
        plan = load_json(args.visual_plan)
        errors = validate(review, plan, args.input.resolve().parent)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]

    result = {"ok": not errors, "errors": errors}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if not errors:
            print("Layout review valid.")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
