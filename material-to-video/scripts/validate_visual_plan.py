#!/usr/bin/env python3
"""Validate a material-to-video VISUAL_PLAN.json without external dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULTS = {
    "longVideoSeconds": 45.0,
    "minLayoutFamiliesLongVideo": 3,
    "maxConsecutiveLayoutFamily": 2,
    "maxConsecutiveTransition": 2,
    "maxSubjectGapSeconds": 4.0,
    "denseFullCardMaxSeconds": 6.0,
    "maxCaptionLines": 2,
    "minPrimaryTextPx": 34,
    "minCaptionTextPx": 40,
    "containmentTolerancePx": 1.0,
}

NON_SUBJECT_KINDS = {"caption", "progress", "ambient"}
VALID_DENSITIES = {"low", "medium", "high"}
DETAIL_TREATMENTS = {"overview-detail-return", "detail-with-context"}
SOURCE_MODES = {"editorial-recut", "faithful", "visual-remix"}
READING_SURFACES = {"authored", "source", "mixed"}
FONT_SOURCES = {"bundled", "verified-system"}
MONOSPACE_SCOPES = {"code", "terminal", "aligned-data"}
REVIEW_PHASES = ("entrance", "development", "hold", "exit")
CONTAINMENT_MODES = {"strict", "unframed"}
EDITORIAL_MODES = {"general-explainer", "technical-single-point"}
TECHNICAL_VISUAL_MODES = {
    "trace-demo",
    "code-to-runtime",
    "state-machine",
    "before-after-run",
    "request-response",
    "error-repair",
    "metric-comparison",
    "system-zoom",
}
COLOR_ROLES = {"neutral", "request", "result", "warning", "error", "focus"}
TRANSITION_CONTINUITIES = {"opening", "continuous", "deliberate-break"}
MOTION_DIRECTIONS = {
    "left",
    "right",
    "up",
    "down",
    "inward",
    "outward",
    "depth-in",
    "depth-out",
    "stationary",
    "none",
}
AUDIO_BRIDGES = {"j-cut", "l-cut", "continuous-bed", "silence-cut", "none"}
INTEGER_THRESHOLDS = {
    "minLayoutFamiliesLongVideo",
    "maxConsecutiveLayoutFamily",
    "maxConsecutiveTransition",
    "maxCaptionLines",
    "minPrimaryTextPx",
    "minCaptionTextPx",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def load_thresholds(config_path: Path | None) -> dict[str, float | int]:
    thresholds = dict(DEFAULTS)
    if config_path is None:
        return thresholds
    config = load_json(config_path)
    overrides = config.get("visualQuality", {})
    if not isinstance(overrides, dict):
        raise ValueError("config.visualQuality must be an object")
    for key in thresholds:
        if key not in overrides:
            continue
        raw_value = overrides[key]
        value = number(raw_value)
        minimum = 0.0 if key == "maxCaptionLines" else 0.000001
        if value is None or value < minimum:
            raise ValueError(f"config.visualQuality.{key} must be a valid non-negative threshold")
        if key in INTEGER_THRESHOLDS and not value.is_integer():
            raise ValueError(f"config.visualQuality.{key} must be an integer")
        thresholds[key] = int(value) if key in INTEGER_THRESHOLDS else value
    return thresholds


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def content_model_ids(model: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for section in ("claims", "definitions", "relationships", "examples", "limitations"):
        values = model.get(section, [])
        if not isinstance(values, list):
            raise ValueError(f"content model {section} must be an array")
        for item in values:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", "")).strip()
            if item_id:
                ids.add(item_id)
    return ids


def content_model_proof_ids(model: dict[str, Any]) -> set[str]:
    contract = model.get("technicalContract")
    if not isinstance(contract, dict):
        return set()
    proof_objects = contract.get("proofObjects")
    if not isinstance(proof_objects, list):
        return set()
    return {
        str(item.get("id", "")).strip()
        for item in proof_objects
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }


def longest_run(values: list[str]) -> tuple[int, str | None]:
    best_length = 0
    best_value = None
    current_length = 0
    current_value = None
    for value in values:
        if value == current_value:
            current_length += 1
        else:
            current_value = value
            current_length = 1
        if current_length > best_length:
            best_length = current_length
            best_value = value
    return best_length, best_value


def max_uncovered_gap(duration: float, intervals: list[tuple[float, float]]) -> float:
    if not intervals:
        return duration
    merged: list[list[float]] = []
    for start, end in sorted(intervals):
        start = max(0.0, min(duration, start))
        end = max(start, min(duration, end))
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    cursor = 0.0
    gap = 0.0
    for start, end in merged:
        gap = max(gap, start - cursor)
        cursor = max(cursor, end)
    return max(gap, duration - cursor)


def validate(
    plan: dict[str, Any],
    thresholds: dict[str, float | int],
    known_content_ids: set[str] | None = None,
    content_source_mode: str | None = None,
    known_proof_ids: set[str] | None = None,
    content_editorial_mode: str | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    schema_version = plan.get("schemaVersion")
    if schema_version not in {1, 2, 3, 4}:
        errors.append("schemaVersion must be 1, 2, 3, or 4")
    is_v2_plus = schema_version in {2, 3, 4}
    is_v3 = schema_version in {3, 4}
    is_v4 = schema_version == 4

    editorial_mode = str(plan.get("editorialMode", "general-explainer")).strip()
    if is_v4 and editorial_mode not in EDITORIAL_MODES:
        errors.append(
            "editorialMode must be general-explainer or technical-single-point"
        )
    if is_v4 and content_editorial_mode and editorial_mode != content_editorial_mode:
        errors.append(
            f"editorialMode '{editorial_mode}' does not match content model "
            f"editorialMode '{content_editorial_mode}'"
        )
    if not str(plan.get("designRead", "")).strip():
        errors.append("designRead is required")
    if not str(plan.get("motionThesis", "")).strip():
        errors.append("motionThesis is required")

    source_mode = str(plan.get("sourceMode", "")).strip()
    if is_v2_plus:
        if source_mode not in SOURCE_MODES:
            errors.append(
                "sourceMode must be editorial-recut, faithful, or visual-remix"
            )
        elif content_source_mode and source_mode != content_source_mode:
            errors.append(
                f"sourceMode '{source_mode}' does not match content model "
                f"sourceMode '{content_source_mode}'"
            )
        for key in (
            "audienceThesis",
            "visualWorld",
            "typography",
            "colorLogic",
            "graphicLanguage",
            "motionGrammar",
            "openingFrame",
        ):
            if not str(plan.get(key, "")).strip():
                errors.append(f"{key} is required for schemaVersion 2, 3, or 4")

    if is_v3:
        font_policy = plan.get("fontPolicy")
        if not isinstance(font_policy, dict):
            errors.append("fontPolicy must be an object for schemaVersion 3 or 4")
        else:
            primary_family = str(font_policy.get("primaryCjkFamily", "")).strip()
            if not primary_family:
                errors.append("fontPolicy.primaryCjkFamily is required")

            font_source = str(font_policy.get("source", "")).strip()
            if font_source not in FONT_SOURCES:
                errors.append("fontPolicy.source must be bundled or verified-system")

            asset_path = font_policy.get("assetPath")
            if font_source == "bundled" and not str(asset_path or "").strip():
                errors.append("fontPolicy.assetPath is required when source is bundled")

            fallbacks = font_policy.get("fallbackFamilies")
            if (
                not isinstance(fallbacks, list)
                or not fallbacks
                or any(not isinstance(item, str) or not item.strip() for item in fallbacks)
            ):
                errors.append("fontPolicy.fallbackFamilies must be a non-empty string array")

            if font_policy.get("ordinaryTextUsesPrimary") is not True:
                errors.append("fontPolicy.ordinaryTextUsesPrimary must be true")

            monospace_scopes = font_policy.get("monospaceScopes")
            if not isinstance(monospace_scopes, list):
                errors.append("fontPolicy.monospaceScopes must be an array")
            else:
                for scope in monospace_scopes:
                    if scope not in MONOSPACE_SCOPES:
                        errors.append(
                            "fontPolicy.monospaceScopes may contain only code, terminal, "
                            "or aligned-data"
                        )
                        break

    dials = plan.get("dials")
    if not isinstance(dials, dict):
        errors.append("dials must be an object")
    else:
        for key in ("designVariance", "motionIntensity", "visualDensity"):
            value = number(dials.get(key))
            if value is None or value < 1 or value > 10:
                errors.append(f"dials.{key} must be a number from 1 to 10")

    if editorial_mode == "technical-single-point":
        if not is_v4:
            errors.append("technical-single-point visual plans require schemaVersion 4")
        if plan.get("technicalVisualMode") not in TECHNICAL_VISUAL_MODES:
            errors.append("technicalVisualMode is invalid")

        color_tokens = plan.get("colorTokens")
        if not isinstance(color_tokens, dict):
            errors.append("colorTokens must be an object for technical-single-point")
        else:
            missing_roles = sorted(COLOR_ROLES - set(color_tokens))
            if missing_roles:
                errors.append(
                    "colorTokens is missing roles: " + ", ".join(missing_roles)
                )
            for role in COLOR_ROLES & set(color_tokens):
                if not nonempty_color_token(color_tokens.get(role)):
                    errors.append(f"colorTokens.{role} must be a non-empty string")

        grammar = plan.get("transitionGrammar")
        if not isinstance(grammar, dict):
            errors.append("transitionGrammar must be an object for technical-single-point")
        else:
            if not str(grammar.get("primaryFamily", "")).strip():
                errors.append("transitionGrammar.primaryFamily is required")
            accents = grammar.get("accentFamilies")
            if not isinstance(accents, list) or len(accents) > 2 or any(
                not isinstance(item, str) or not item.strip() for item in accents
            ):
                errors.append(
                    "transitionGrammar.accentFamilies must contain at most two strings"
                )

        proof_ids = plan.get("proofObjectIds")
        if not isinstance(proof_ids, list) or not proof_ids or any(
            not isinstance(item, str) or not item.strip() for item in proof_ids
        ):
            errors.append("proofObjectIds must be a non-empty string array")
        elif known_proof_ids is not None:
            for proof_id in proof_ids:
                if proof_id not in known_proof_ids:
                    errors.append(f"proofObjectIds references unknown proof object '{proof_id}'")

    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must be a non-empty array")
        return errors, warnings

    seen_ids: set[str] = set()
    families: list[str] = []
    transitions: list[str] = []
    valid_scenes: list[tuple[dict[str, Any], str, float, float]] = []

    for index, raw_scene in enumerate(scenes):
        label = f"scenes[{index}]"
        if not isinstance(raw_scene, dict):
            errors.append(f"{label} must be an object")
            continue
        scene_id = str(raw_scene.get("id", "")).strip()
        if not scene_id:
            errors.append(f"{label}.id is required")
            scene_id = label
        elif scene_id in seen_ids:
            errors.append(f"duplicate scene id: {scene_id}")
        seen_ids.add(scene_id)

        start = number(raw_scene.get("startSec"))
        end = number(raw_scene.get("endSec"))
        if start is None or end is None or start < 0 or end <= start:
            errors.append(f"{scene_id}: startSec and endSec must define a positive interval")
            continue

        family = str(raw_scene.get("layoutFamily", "")).strip()
        transition = str(raw_scene.get("transitionIn", "")).strip()
        if not family:
            errors.append(f"{scene_id}: layoutFamily is required")
        if not transition:
            errors.append(f"{scene_id}: transitionIn is required")
        families.append(family)
        transitions.append(transition)
        valid_scenes.append((raw_scene, scene_id, start, end))

        if editorial_mode == "technical-single-point":
            continuity = raw_scene.get("transitionContinuity")
            if not isinstance(continuity, dict):
                errors.append(f"{scene_id}: transitionContinuity must be an object")
            else:
                continuity_type = str(continuity.get("type", "")).strip()
                expected_type = "opening" if index == 0 else None
                if continuity_type not in TRANSITION_CONTINUITIES:
                    errors.append(f"{scene_id}: transitionContinuity.type is invalid")
                elif expected_type and continuity_type != expected_type:
                    errors.append(f"{scene_id}: first scene continuity type must be opening")
                elif not expected_type and continuity_type == "opening":
                    errors.append(f"{scene_id}: only the first scene may use opening continuity")
                if not str(continuity.get("narrativePurpose", "")).strip():
                    errors.append(
                        f"{scene_id}: transitionContinuity.narrativePurpose is required"
                    )
                audio_bridge = str(continuity.get("audioBridge", "")).strip()
                if audio_bridge not in AUDIO_BRIDGES:
                    errors.append(f"{scene_id}: transitionContinuity.audioBridge is invalid")
                if continuity_type == "continuous":
                    for key in ("outgoingAnchor", "incomingAnchor"):
                        if not str(continuity.get(key, "")).strip():
                            errors.append(f"{scene_id}: transitionContinuity.{key} is required")
                    if continuity.get("motionDirection") not in MOTION_DIRECTIONS - {"none"}:
                        errors.append(
                            f"{scene_id}: continuous transition requires a motionDirection"
                        )
                if continuity_type == "deliberate-break" and not str(
                    continuity.get("breakReason", "")
                ).strip():
                    errors.append(
                        f"{scene_id}: deliberate-break requires transitionContinuity.breakReason"
                    )

    for left, right in zip(valid_scenes, valid_scenes[1:]):
        _, left_id, _, left_end = left
        _, right_id, right_start, _ = right
        if right_start < left_end - 0.05:
            errors.append(f"{left_id} overlaps {right_id}")
        elif right_start > left_end + 0.05:
            warnings.append(f"timeline gap of {right_start - left_end:.2f}s before {right_id}")

    timeline_duration = max((end for _, _, _, end in valid_scenes), default=0.0)
    if timeline_duration >= float(thresholds["longVideoSeconds"]):
        family_count = len({family for family in families if family})
        minimum = int(thresholds["minLayoutFamiliesLongVideo"])
        if family_count < minimum:
            errors.append(
                f"long video uses {family_count} layout families; at least {minimum} are required"
            )

    family_run, family_name = longest_run(families)
    family_limit = int(thresholds["maxConsecutiveLayoutFamily"])
    if family_run > family_limit:
        errors.append(
            f"layout family '{family_name}' repeats {family_run} times; limit is {family_limit}"
        )

    transition_run, transition_name = longest_run(transitions[1:])
    transition_limit = int(thresholds["maxConsecutiveTransition"])
    if transition_run > transition_limit:
        errors.append(
            f"transition '{transition_name}' repeats {transition_run} times; limit is {transition_limit}"
        )

    max_gap = float(thresholds["maxSubjectGapSeconds"])
    dense_limit = float(thresholds["denseFullCardMaxSeconds"])
    caption_limit = int(thresholds["maxCaptionLines"])
    min_primary_px = int(thresholds["minPrimaryTextPx"])
    min_caption_px = int(thresholds["minCaptionTextPx"])

    for scene, scene_id, start, end in valid_scenes:
        duration = end - start
        exception = str(scene.get("qualityException", "")).strip()
        density = str(scene.get("sourceDensity", "")).strip()
        treatment = str(scene.get("evidenceTreatment", "")).strip()
        reading_surface = str(scene.get("primaryReadingSurface", "")).strip()
        if density not in VALID_DENSITIES:
            errors.append(f"{scene_id}: sourceDensity must be low, medium, or high")
        if not treatment:
            errors.append(f"{scene_id}: evidenceTreatment is required")

        if is_v2_plus:
            for key in ("viewerQuestion", "cognitiveJob", "dominantTakeaway"):
                if not str(scene.get(key, "")).strip():
                    errors.append(f"{scene_id}: {key} is required")

            raw_content_ids = scene.get("contentIds")
            if not isinstance(raw_content_ids, list) or not raw_content_ids:
                errors.append(f"{scene_id}: contentIds must be a non-empty array")
            else:
                for content_id in raw_content_ids:
                    if not isinstance(content_id, str) or not content_id.strip():
                        errors.append(f"{scene_id}: contentIds must contain non-empty strings")
                    elif known_content_ids is not None and content_id not in known_content_ids:
                        errors.append(f"{scene_id}: unknown contentId '{content_id}'")

            if reading_surface not in READING_SURFACES:
                errors.append(
                    f"{scene_id}: primaryReadingSurface must be authored, source, or mixed"
                )
            if density == "high" and reading_surface == "source":
                message = f"{scene_id}: a dense source cannot be the primary reading surface"
                (warnings if exception else errors).append(message)
            if source_mode == "editorial-recut" and reading_surface == "source":
                message = (
                    f"{scene_id}: editorial-recut requires authored or mixed primary reading"
                )
                (warnings if exception else errors).append(message)

            primary_px = scene.get("minPrimaryTextPx")
            if (
                not isinstance(primary_px, int)
                or isinstance(primary_px, bool)
                or primary_px < min_primary_px
            ):
                errors.append(
                    f"{scene_id}: minPrimaryTextPx must be at least {min_primary_px}"
                )

            caption_px = scene.get("minCaptionTextPx")
            if (
                not isinstance(caption_px, int)
                or isinstance(caption_px, bool)
                or caption_px < min_caption_px
            ):
                errors.append(
                    f"{scene_id}: minCaptionTextPx must be at least {min_caption_px}"
                )

        if is_v3:
            containment = scene.get("containment")
            if not isinstance(containment, dict):
                errors.append(f"{scene_id}: containment must be an object")
            else:
                containment_mode = str(containment.get("mode", "")).strip()
                if containment_mode not in CONTAINMENT_MODES:
                    errors.append(
                        f"{scene_id}: containment.mode must be strict or unframed"
                    )

                container_ids = containment.get("containerIds")
                if not isinstance(container_ids, list) or any(
                    not isinstance(item, str) or not item.strip() for item in container_ids
                ):
                    errors.append(
                        f"{scene_id}: containment.containerIds must be a string array"
                    )
                elif len(container_ids) != len(set(container_ids)):
                    errors.append(
                        f"{scene_id}: containment.containerIds must not contain duplicates"
                    )
                elif containment_mode == "strict" and not container_ids:
                    errors.append(
                        f"{scene_id}: strict containment requires at least one containerId"
                    )
                elif containment_mode == "unframed" and container_ids:
                    errors.append(
                        f"{scene_id}: unframed containment cannot declare containerIds"
                    )

                overflow_ids = containment.get("intentionalOverflowIds")
                if not isinstance(overflow_ids, list) or any(
                    not isinstance(item, str) or not item.strip() for item in overflow_ids
                ):
                    errors.append(
                        f"{scene_id}: containment.intentionalOverflowIds must be a string array"
                    )
                elif len(overflow_ids) != len(set(overflow_ids)):
                    errors.append(
                        f"{scene_id}: containment.intentionalOverflowIds must not contain duplicates"
                    )

            review_moments = scene.get("reviewMoments")
            if not isinstance(review_moments, list):
                errors.append(f"{scene_id}: reviewMoments must be an array")
            else:
                found_phases: list[str] = []
                previous_review_at = -1.0
                for moment_index, moment in enumerate(review_moments):
                    moment_label = f"{scene_id}.reviewMoments[{moment_index}]"
                    if not isinstance(moment, dict):
                        errors.append(f"{moment_label} must be an object")
                        continue
                    phase = str(moment.get("phase", "")).strip()
                    at = number(moment.get("atSec"))
                    if phase not in REVIEW_PHASES:
                        errors.append(
                            f"{moment_label}.phase must be entrance, development, hold, or exit"
                        )
                    else:
                        found_phases.append(phase)
                    if at is None or at < 0 or at >= duration:
                        errors.append(
                            f"{moment_label}.atSec must be within the scene's local interval"
                        )
                    elif at <= previous_review_at:
                        errors.append(
                            f"{scene_id}: reviewMoments must be strictly ordered by atSec"
                        )
                    else:
                        previous_review_at = at

                if tuple(found_phases) != REVIEW_PHASES:
                    errors.append(
                        f"{scene_id}: reviewMoments must contain entrance, development, hold, "
                        "and exit exactly once in that order"
                    )

        caption_lines = scene.get("captionMaxLines")
        if not isinstance(caption_lines, int) or isinstance(caption_lines, bool) or caption_lines < 0:
            errors.append(f"{scene_id}: captionMaxLines must be a non-negative integer")
        elif caption_lines > caption_limit:
            message = f"{scene_id}: captionMaxLines {caption_lines} exceeds limit {caption_limit}"
            (warnings if exception else errors).append(message)

        source_is_reading_surface = not is_v2_plus or reading_surface in {"source", "mixed"}
        if (
            density == "high"
            and source_is_reading_surface
            and duration > dense_limit
            and treatment not in DETAIL_TREATMENTS
        ):
            message = (
                f"{scene_id}: dense source lasts {duration:.2f}s and needs overview-detail-return "
                "or detail-with-context"
            )
            (warnings if exception else errors).append(message)

        beats = scene.get("beats")
        if not isinstance(beats, list) or not beats:
            errors.append(f"{scene_id}: beats must be a non-empty array")
            continue

        subject_intervals: list[tuple[float, float]] = []
        previous_at = -1.0
        for beat_index, beat in enumerate(beats):
            beat_label = f"{scene_id}.beats[{beat_index}]"
            if not isinstance(beat, dict):
                errors.append(f"{beat_label} must be an object")
                continue
            at = number(beat.get("atSec"))
            beat_duration = number(beat.get("durationSec"))
            kind = str(beat.get("kind", "")).strip()
            actor = str(beat.get("actor", "")).strip()
            purpose = str(beat.get("purpose", "")).strip()
            motion = str(beat.get("motion", "")).strip()
            if at is None or beat_duration is None or at < 0 or beat_duration <= 0:
                errors.append(f"{beat_label}: atSec and durationSec must define a positive interval")
                continue
            if at < previous_at:
                errors.append(f"{scene_id}: beats must be ordered by atSec")
            previous_at = at
            if at + beat_duration > duration + 0.05:
                errors.append(f"{beat_label}: interval exceeds scene duration")
            if not kind or not actor or not purpose or not motion:
                errors.append(f"{beat_label}: kind, actor, purpose, and motion are required")
            if kind not in NON_SUBJECT_KINDS:
                subject_intervals.append((at, at + beat_duration))

        uncovered = max_uncovered_gap(duration, subject_intervals)
        if uncovered > max_gap + 0.05:
            message = (
                f"{scene_id}: subject has an uncovered gap of {uncovered:.2f}s; limit is {max_gap:.2f}s"
            )
            (warnings if exception else errors).append(message)

    focal_id = str(plan.get("focalSceneId", "")).strip()
    if not focal_id:
        errors.append("focalSceneId is required")
    elif focal_id not in seen_ids:
        errors.append(f"focalSceneId '{focal_id}' does not match a scene")

    if editorial_mode == "technical-single-point" and valid_scenes:
        state_kinds = {
            str(beat.get("kind", "")).strip()
            for scene, _, _, _ in valid_scenes
            for beat in scene.get("beats", [])
            if isinstance(beat, dict)
        }
        for required_kind in ("state-before", "mechanism", "state-after", "boundary"):
            if required_kind not in state_kinds:
                errors.append(
                    f"technical-single-point requires a '{required_kind}' beat"
                )

    return errors, warnings


def nonempty_color_token(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Path to VISUAL_PLAN.json")
    parser.add_argument("--content-model", type=Path, help="Optional CONTENT_MODEL.json")
    parser.add_argument("--config", type=Path, help="Optional material-to-video config")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable results")
    args = parser.parse_args()

    try:
        plan = load_json(args.input)
        thresholds = load_thresholds(args.config)
        content_model = load_json(args.content_model) if args.content_model else None
        known_content_ids = content_model_ids(content_model) if content_model else None
        known_proof_ids = content_model_proof_ids(content_model) if content_model else None
        content_source_mode = (
            str(content_model.get("sourceMode", "")).strip() if content_model else None
        )
        content_editorial_mode = (
            str(content_model.get("editorialMode", "general-explainer")).strip()
            if content_model
            else None
        )
        errors, warnings = validate(
            plan,
            thresholds,
            known_content_ids,
            content_source_mode,
            known_proof_ids,
            content_editorial_mode,
        )
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
            print(f"Visual plan valid ({len(warnings)} warning(s)).")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
