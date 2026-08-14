#!/usr/bin/env python3
"""Validate an event-driven material-to-video AUDIO_PLAN.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EDITORIAL_MODES = {"general-explainer", "technical-single-point"}
MUSIC_MODES = {"none", "licensed", "generated", "user-supplied"}
EVENT_SOURCES = {"licensed", "generated", "user-supplied", "synthesized"}
BRIDGE_TYPES = {"j-cut", "l-cut", "continuous-bed", "silence-cut", "none"}


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


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def validate(plan: dict[str, Any], visual: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if plan.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")

    editorial_mode = str(plan.get("editorialMode", "")).strip()
    if editorial_mode not in EDITORIAL_MODES:
        errors.append("editorialMode must be general-explainer or technical-single-point")
    visual_mode = str(visual.get("editorialMode", "general-explainer")).strip()
    if editorial_mode and editorial_mode != visual_mode:
        errors.append("editorialMode does not match VISUAL_PLAN.json")

    narration = plan.get("narration")
    if not isinstance(narration, dict):
        errors.append("narration must be an object")
    else:
        if narration.get("priority") != "primary":
            errors.append("narration.priority must be primary")
        ducking = number(narration.get("duckingDb"))
        if ducking is None or ducking > 0 or ducking < -30:
            errors.append("narration.duckingDb must be between -30 and 0")

    music = plan.get("music")
    if not isinstance(music, dict):
        errors.append("music must be an object")
    else:
        music_mode = music.get("mode")
        if music_mode not in MUSIC_MODES:
            errors.append("music.mode is invalid")
        if music_mode != "none" and not text(music.get("provenanceId")):
            errors.append("music.provenanceId is required when music.mode is not none")

    raw_scenes = visual.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        errors.append("VISUAL_PLAN.json scenes must be a non-empty array")
        return errors, warnings
    scene_intervals: dict[str, float] = {}
    scene_order: list[str] = []
    expected_bridge_types: dict[tuple[str, str], str] = {}
    for scene in raw_scenes:
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("id", "")).strip()
        start = number(scene.get("startSec"))
        end = number(scene.get("endSec"))
        if not scene_id or start is None or end is None or end <= start:
            continue
        scene_order.append(scene_id)
        scene_intervals[scene_id] = end - start
    for left, right in zip(scene_order, scene_order[1:]):
        scene = next(
            item for item in raw_scenes if isinstance(item, dict) and item.get("id") == right
        )
        continuity = scene.get("transitionContinuity", {})
        if isinstance(continuity, dict):
            expected_bridge_types[(left, right)] = str(
                continuity.get("audioBridge", "")
            ).strip()

    event_cues = plan.get("eventCues")
    if not isinstance(event_cues, list):
        errors.append("eventCues must be an array")
        event_cues = []
    seen_event_ids: set[str] = set()
    for index, cue in enumerate(event_cues):
        label = f"eventCues[{index}]"
        if not isinstance(cue, dict):
            errors.append(f"{label} must be an object")
            continue
        cue_id = str(cue.get("id", "")).strip()
        if not cue_id:
            errors.append(f"{label}.id is required")
        elif cue_id in seen_event_ids:
            errors.append(f"duplicate event cue id: {cue_id}")
        seen_event_ids.add(cue_id)
        scene_id = str(cue.get("sceneId", "")).strip()
        at = number(cue.get("atSec"))
        if scene_id not in scene_intervals:
            errors.append(f"{label}.sceneId is unknown")
        elif at is None or at < 0 or at >= scene_intervals[scene_id]:
            errors.append(f"{label}.atSec must be inside the local scene interval")
        if not text(cue.get("event")) or not text(cue.get("purpose")):
            errors.append(f"{label}.event and purpose are required")
        source = cue.get("source")
        if source not in EVENT_SOURCES:
            errors.append(f"{label}.source is invalid")
        if source != "synthesized" and not text(cue.get("provenanceId")):
            errors.append(f"{label}.provenanceId is required for {source} audio")

    if editorial_mode == "technical-single-point" and not event_cues:
        errors.append("technical-single-point requires at least one event-bound sound cue")

    bridges = plan.get("bridges")
    if not isinstance(bridges, list):
        errors.append("bridges must be an array")
        bridges = []
    seen_pairs: set[tuple[str, str]] = set()
    for index, bridge in enumerate(bridges):
        label = f"bridges[{index}]"
        if not isinstance(bridge, dict):
            errors.append(f"{label} must be an object")
            continue
        left = str(bridge.get("fromSceneId", "")).strip()
        right = str(bridge.get("toSceneId", "")).strip()
        pair = (left, right)
        if pair not in expected_bridge_types:
            errors.append(f"{label} does not match an adjacent scene pair")
        elif pair in seen_pairs:
            errors.append(f"duplicate audio bridge for {left} -> {right}")
        seen_pairs.add(pair)
        bridge_type = bridge.get("type")
        if bridge_type not in BRIDGE_TYPES:
            errors.append(f"{label}.type is invalid")
        elif pair in expected_bridge_types and bridge_type != expected_bridge_types[pair]:
            errors.append(f"{label}.type does not match transitionContinuity.audioBridge")
        offset = number(bridge.get("offsetSec"))
        if offset is None or offset < 0 or offset > 2:
            errors.append(f"{label}.offsetSec must be between 0 and 2")
        if not text(bridge.get("purpose")):
            errors.append(f"{label}.purpose is required")

    missing_pairs = set(expected_bridge_types) - seen_pairs
    for left, right in sorted(missing_pairs):
        errors.append(f"missing audio bridge for {left} -> {right}")

    silences = plan.get("intentionalSilences", [])
    if not isinstance(silences, list):
        errors.append("intentionalSilences must be an array")
    else:
        for index, silence in enumerate(silences):
            label = f"intentionalSilences[{index}]"
            if not isinstance(silence, dict):
                errors.append(f"{label} must be an object")
                continue
            scene_id = str(silence.get("sceneId", "")).strip()
            at = number(silence.get("atSec"))
            duration = number(silence.get("durationSec"))
            if scene_id not in scene_intervals:
                errors.append(f"{label}.sceneId is unknown")
            elif (
                at is None
                or duration is None
                or at < 0
                or duration <= 0
                or at + duration > scene_intervals[scene_id]
            ):
                errors.append(f"{label} must fit inside the local scene interval")
            if not text(silence.get("purpose")):
                errors.append(f"{label}.purpose is required")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--visual-plan", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        errors, warnings = validate(load_json(args.input), load_json(args.visual_plan))
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
            print(f"Audio plan valid ({len(warnings)} warning(s)).")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
