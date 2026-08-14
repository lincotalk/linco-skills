#!/usr/bin/env python3
"""Reject internal material-provenance commentary in audience-facing copy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PATTERNS = (
    ("original-material-wording", re.compile(r"素材中的原始说法")),
    ("provided-material", re.compile(r"(?:根据|依据)用户提供的素材")),
    ("material-shows", re.compile(r"从(?:这些|这份|用户提供的)?素材(?:中)?(?:可以)?(?:看出|看到)")),
    ("showing-material", re.compile(r"这里展示的是(?:用户提供的|原始)?素材")),
    ("material-says", re.compile(r"(?:原始)?素材(?:中|里)(?:说|提到|显示|表示)")),
    ("generic-web-research", re.compile(r"(?:根据|依据)(?:网上资料|网络资料|检索结果|搜索结果)")),
    ("research-shows", re.compile(r"(?:网上资料|网络资料|检索结果|搜索结果)(?:中)?(?:可以)?(?:看出|看到|显示|表明)")),
    (
        "generic-material-attribution",
        re.compile(r"(?:原始|用户提供的)?素材(?:中|里)?(?:给出(?:的)?|显示|表明)"),
    ),
)


def validate_text(text: str, label: str) -> list[dict[str, object]]:
    violations: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        matched_spans: list[tuple[int, int]] = []
        for rule, pattern in PATTERNS:
            for match in pattern.finditer(line):
                if any(match.start() < end and match.end() > start for start, end in matched_spans):
                    continue
                matched_spans.append((match.start(), match.end()))
                violations.append(
                    {
                        "input": label,
                        "line": line_number,
                        "column": match.start() + 1,
                        "rule": rule,
                        "match": match.group(0),
                    }
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", action="append", type=Path, help="Storyboard or script file")
    source.add_argument("--text", help="Literal text, useful for diagnostics")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable results")
    args = parser.parse_args()

    violations: list[dict[str, object]] = []
    try:
        if args.text is not None:
            violations.extend(validate_text(args.text, "<text>"))
        else:
            for path in args.input:
                violations.extend(validate_text(path.read_text(encoding="utf-8"), str(path)))
    except (OSError, UnicodeError) as exc:
        result = {"ok": False, "errors": [str(exc)], "violations": []}
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"ERROR: {exc}")
        return 1

    result = {"ok": not violations, "errors": [], "violations": violations}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif violations:
        for item in violations:
            print(
                f"ERROR: {item['input']}:{item['line']}:{item['column']}: "
                f"audience copy exposes internal provenance wording '{item['match']}' "
                f"({item['rule']})",
                file=sys.stderr,
            )
    else:
        print("Audience-facing copy valid.")
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
