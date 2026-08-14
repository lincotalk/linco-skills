#!/usr/bin/env python3
"""Create or validate a fixed material-to-video job workspace."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
DIRECTORIES = ("audio", "project", "review", "tmp", "logs", "final")
LAYOUT_NAME = "JOB_LAYOUT.json"


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
        raise ValueError("JOB_LAYOUT.json must contain an object")
    return value


def resolve_paths(workspace: Path, slug: str) -> tuple[Path, Path]:
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError(
            "job slug must be 1-64 lowercase ASCII letters, digits, or hyphens; "
            "it cannot start or end with a hyphen"
        )
    workspace = workspace.expanduser().resolve()
    if not workspace.is_dir():
        raise ValueError(f"workspace is not an existing directory: {workspace}")
    job_dir = (workspace / "jobs" / slug).resolve()
    try:
        job_dir.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("job directory escapes the workspace") from exc
    return workspace, job_dir


def expected_layout(workspace: Path, job_dir: Path, slug: str) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "jobSlug": slug,
        "workspaceRoot": str(workspace),
        "jobDir": str(job_dir),
        "paths": {name: name for name in DIRECTORIES},
    }


def validate_layout(
    layout: dict[str, Any], workspace: Path, job_dir: Path, slug: str
) -> list[str]:
    errors: list[str] = []
    expected = expected_layout(workspace, job_dir, slug)
    for key in ("schemaVersion", "jobSlug", "workspaceRoot", "jobDir", "paths"):
        if layout.get(key) != expected[key]:
            errors.append(f"{key} does not match the fixed job layout")
    if not job_dir.is_dir():
        errors.append(f"job directory is missing: {job_dir}")
    for name in DIRECTORIES:
        path = (job_dir / name).resolve()
        try:
            path.relative_to(job_dir)
        except ValueError:
            errors.append(f"{name} directory escapes the job directory")
            continue
        if not path.is_dir():
            errors.append(f"required directory is missing: {name}")
    return errors


def initialize(workspace: Path, job_dir: Path, slug: str) -> dict[str, Any]:
    jobs_root = job_dir.parent
    jobs_root.mkdir(parents=True, exist_ok=True)
    layout_path = job_dir / LAYOUT_NAME
    if job_dir.exists() and any(job_dir.iterdir()) and not layout_path.is_file():
        raise ValueError(
            f"refusing to reuse non-empty directory without {LAYOUT_NAME}: {job_dir}"
        )

    job_dir.mkdir(parents=True, exist_ok=True)
    for name in DIRECTORIES:
        (job_dir / name).mkdir(exist_ok=True)

    expected = expected_layout(workspace, job_dir, slug)
    if layout_path.is_file():
        errors = validate_layout(load_json(layout_path), workspace, job_dir, slug)
        if errors:
            raise ValueError("; ".join(errors))
    else:
        part_path = job_dir / "tmp" / f"{LAYOUT_NAME}.part"
        part_path.write_text(
            json.dumps(expected, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        part_path.replace(layout_path)
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--job-slug", required=True)
    parser.add_argument("--check", action="store_true", help="Validate without creating")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable results")
    args = parser.parse_args()

    try:
        workspace, job_dir = resolve_paths(args.workspace, args.job_slug)
        layout_path = job_dir / LAYOUT_NAME
        if args.check:
            errors = validate_layout(
                load_json(layout_path), workspace, job_dir, args.job_slug
            )
            if errors:
                raise ValueError("; ".join(errors))
            layout = load_json(layout_path)
        else:
            layout = initialize(workspace, job_dir, args.job_slug)
        result = {"ok": True, "layout": layout}
    except (OSError, ValueError) as exc:
        result = {"ok": False, "errors": [str(exc)]}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["ok"]:
        print(result["layout"]["jobDir"])
    else:
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
