#!/usr/bin/env python3
"""Extract local material text and media metadata into a traceable job record."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


MATERIAL_ID_PATTERN = re.compile(r"^m-[0-9a-f]{16}-[0-9a-f]{8}$")
SLIDE_PATTERN = re.compile(r"^ppt/slides/slide(\d+)\.xml$")
TEXT_EXTENSIONS = {".txt", ".md"}
HTML_EXTENSIONS = {".html", ".htm"}
MEDIA_EXTENSIONS = {".wav", ".mp3", ".m4a", ".mp4", ".mov", ".webm"}


class ExtractionError(Exception):
    pass


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"}:
            self.hidden_depth += 1
        elif not self.hidden_depth and tag.lower() in {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "template"} and self.hidden_depth:
            self.hidden_depth -= 1
        elif not self.hidden_depth and tag.lower() in {"p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)

    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--selected-ids", type=Path)
    parser.add_argument("--max-text-chars", type=int, default=250_000)
    parser.add_argument("--max-archive-entry-mb", type=int, default=32)
    parser.add_argument("--max-archive-total-mb", type=int, default=128)
    parser.add_argument("--ffprobe-timeout", type=float, default=30.0)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in value.splitlines()]
    compact: list[str] = []
    blank = False
    for line in lines:
        if line:
            compact.append(line)
            blank = False
        elif compact and not blank:
            compact.append("")
            blank = True
    return "\n".join(compact).strip()


def decode_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ExtractionError("text encoding is not supported")


def bounded_text(value: str, max_chars: int) -> tuple[str, bool]:
    normalized = normalize_text(value)
    if len(normalized) <= max_chars:
        return normalized, False
    return normalized[:max_chars].rstrip(), True


def read_zip_xml(archive: zipfile.ZipFile, name: str, max_bytes: int) -> ElementTree.Element:
    info = archive.getinfo(name)
    if info.file_size > max_bytes:
        raise ExtractionError(f"archive entry exceeds limit: {name}")
    with archive.open(info) as handle:
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ExtractionError(f"archive entry exceeds limit: {name}")
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ExtractionError(f"invalid XML in {name}: {exc}") from exc


def element_text(element: ElementTree.Element) -> str:
    return "".join(node.text or "" for node in element.iter() if node.tag.endswith("}t"))


def extract_docx(path: Path, max_entry_bytes: int) -> tuple[str, dict[str, Any]]:
    try:
        with zipfile.ZipFile(path) as archive:
            root = read_zip_xml(archive, "word/document.xml", max_entry_bytes)
    except (KeyError, zipfile.BadZipFile, OSError) as exc:
        raise ExtractionError(f"invalid DOCX: {exc}") from exc
    paragraphs = [element_text(node).strip() for node in root.iter() if node.tag.endswith("}p")]
    paragraphs = [value for value in paragraphs if value]
    return "\n".join(paragraphs), {"paragraphCount": len(paragraphs)}


def extract_pptx(
    path: Path, max_entry_bytes: int, max_total_bytes: int
) -> tuple[str, dict[str, Any]]:
    try:
        with zipfile.ZipFile(path) as archive:
            slides = []
            for name in archive.namelist():
                match = SLIDE_PATTERN.fullmatch(name)
                if match:
                    slides.append((int(match.group(1)), name))
            slides.sort()
            total_bytes = sum(archive.getinfo(name).file_size for _, name in slides)
            if total_bytes > max_total_bytes:
                raise ExtractionError("PPTX slide XML exceeds the total extraction limit")
            output: list[str] = []
            for number, name in slides:
                root = read_zip_xml(archive, name, max_entry_bytes)
                text = normalize_text(" ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t")))
                if text:
                    output.append(f"[Slide {number}]\n{text}")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ExtractionError(f"invalid PPTX: {exc}") from exc
    return "\n\n".join(output), {"slideCount": len(slides)}


def extract_pdf(path: Path, timeout: float) -> tuple[str | None, dict[str, Any], str]:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\f\n".join(pages), {"pageCount": len(pages)}, "pypdf"
    except ImportError:
        pass
    except Exception as exc:
        raise ExtractionError(f"pypdf could not read PDF: {exc}") from exc

    executable = shutil.which("pdftotext")
    if not executable:
        return None, {}, "unavailable"
    try:
        result = subprocess.run(
            [executable, "-layout", str(path), "-"],
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExtractionError(f"pdftotext failed: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ExtractionError(f"pdftotext failed: {detail or result.returncode}")
    text = result.stdout.decode("utf-8", errors="replace")
    return text, {"pageCount": max(1, text.count("\f")) if text else None}, "pdftotext"


def probe_media(path: Path, timeout: float) -> dict[str, Any]:
    executable = shutil.which("ffprobe")
    if not executable:
        raise ExtractionError("ffprobe is not installed or not on PATH")
    try:
        result = subprocess.run(
            [executable, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExtractionError(f"ffprobe failed: {exc}") from exc
    if result.returncode != 0:
        raise ExtractionError(f"ffprobe failed: {result.stderr.strip() or result.returncode}")
    try:
        probe = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"ffprobe returned invalid JSON: {exc}") from exc
    streams = []
    for stream in probe.get("streams", []):
        if not isinstance(stream, dict):
            continue
        streams.append(
            {
                key: stream.get(key)
                for key in (
                    "index",
                    "codec_name",
                    "codec_type",
                    "width",
                    "height",
                    "sample_rate",
                    "channels",
                    "duration",
                    "avg_frame_rate",
                )
                if stream.get(key) is not None
            }
        )
    format_info = probe.get("format", {}) if isinstance(probe.get("format"), dict) else {}
    return {
        "durationSeconds": format_info.get("duration"),
        "formatName": format_info.get("format_name"),
        "streams": streams,
    }


def resolve_source(item: dict[str, Any], roots: list[Path]) -> Path:
    material_id = item.get("id")
    if not isinstance(material_id, str) or not MATERIAL_ID_PATTERN.fullmatch(material_id):
        raise ExtractionError(f"invalid material ID: {material_id!r}")
    root_index = item.get("rootIndex")
    if not isinstance(root_index, int) or not 0 <= root_index < len(roots):
        raise ExtractionError(f"invalid rootIndex for {material_id}")
    relative_path = item.get("relativePath")
    if not isinstance(relative_path, str) or not relative_path:
        raise ExtractionError(f"invalid relativePath for {material_id}")
    root = roots[root_index]
    base = root.parent if root.is_file() else root
    source = (base / relative_path).resolve()
    try:
        source.relative_to(base.resolve())
    except ValueError as exc:
        raise ExtractionError(f"material escapes its input root: {material_id}") from exc
    if not source.is_file():
        raise ExtractionError(f"material is missing: {material_id}")
    if sha256(source) != item.get("sha256"):
        raise ExtractionError(f"material changed after scan: {material_id}")
    return source


def extract_item(
    item: dict[str, Any],
    source: Path,
    *,
    max_chars: int,
    max_entry_bytes: int,
    max_total_bytes: int,
    ffprobe_timeout: float,
) -> dict[str, Any]:
    extension = source.suffix.lower()
    result: dict[str, Any] = {
        "id": item["id"],
        "relativePath": item.get("relativePath"),
        "category": item.get("category"),
        "sha256": item.get("sha256"),
        "status": "manual-review-required",
        "extractionMethod": None,
        "text": None,
        "textCharacters": 0,
        "truncated": False,
        "metadata": {},
        "reviewRequirements": [],
        "manualObservations": [],
    }
    text: str | None = None
    if extension in TEXT_EXTENSIONS:
        if source.stat().st_size > max_entry_bytes:
            raise ExtractionError("text source exceeds the extraction read limit")
        text = decode_text(source)
        result["extractionMethod"] = "plain-text"
    elif extension in HTML_EXTENSIONS:
        if source.stat().st_size > max_entry_bytes:
            raise ExtractionError("HTML source exceeds the extraction read limit")
        parser = VisibleTextParser()
        parser.feed(decode_text(source))
        text = parser.text()
        result["extractionMethod"] = "html-visible-text"
    elif extension == ".docx":
        text, result["metadata"] = extract_docx(source, max_entry_bytes)
        result["extractionMethod"] = "docx-xml"
    elif extension == ".pptx":
        text, result["metadata"] = extract_pptx(
            source, max_entry_bytes, max_total_bytes
        )
        result["extractionMethod"] = "pptx-xml"
    elif extension == ".pdf":
        text, result["metadata"], result["extractionMethod"] = extract_pdf(
            source, ffprobe_timeout
        )
        if text is None:
            result["reviewRequirements"].append("visual-inspection-or-pdf-extractor")
    elif extension in MEDIA_EXTENSIONS:
        result["metadata"] = probe_media(source, ffprobe_timeout)
        result["extractionMethod"] = "ffprobe"
        result["reviewRequirements"].append("transcription-or-listening-review")
    elif item.get("category") == "image":
        result["metadata"] = item.get("dimensions", {})
        result["extractionMethod"] = "image-metadata"
        result["reviewRequirements"].append("visual-inspection")
    else:
        result["status"] = "unsupported"
        result["reviewRequirements"].append("supported-extractor")

    if text is not None:
        text, truncated = bounded_text(text, max_chars)
        result["text"] = text or None
        result["textCharacters"] = len(text)
        result["truncated"] = truncated
        if text:
            result["status"] = "extracted"
        else:
            result["reviewRequirements"].append("visual-inspection-or-ocr")
    elif result["status"] != "unsupported" and not result["reviewRequirements"]:
        result["status"] = "metadata-only"
    return result


def main() -> int:
    args = parse_args()
    try:
        if (
            args.max_text_chars <= 0
            or args.max_archive_entry_mb <= 0
            or args.max_archive_total_mb <= 0
            or args.ffprobe_timeout <= 0
        ):
            raise ExtractionError("extraction limits must be positive")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        if not isinstance(manifest, dict):
            raise ExtractionError("manifest root must be an object")
        roots = [Path(value).resolve() for value in manifest.get("inputRoots", [])]
        if not roots:
            raise ExtractionError("manifest has no inputRoots")
        items = manifest.get("items", [])
        if not isinstance(items, list):
            raise ExtractionError("manifest items must be an array")
        selected = None
        if args.selected_ids:
            selected = {
                line.strip()
                for line in args.selected_ids.read_text(encoding="utf-8-sig").splitlines()
                if line.strip()
            }
            known = {
                item.get("id")
                for item in items
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            unknown = sorted(selected - known)
            if unknown:
                raise ExtractionError("unknown selected material IDs: " + ", ".join(unknown))

        records = []
        errors = []
        for item in items:
            if not isinstance(item, dict) or item.get("category") == "unsupported" or item.get("exactDuplicate"):
                continue
            if selected is not None and item.get("id") not in selected:
                continue
            try:
                source = resolve_source(item, roots)
                records.append(
                    extract_item(
                        item,
                        source,
                        max_chars=args.max_text_chars,
                        max_entry_bytes=args.max_archive_entry_mb * 1024 * 1024,
                        max_total_bytes=args.max_archive_total_mb * 1024 * 1024,
                        ffprobe_timeout=args.ffprobe_timeout,
                    )
                )
            except (ExtractionError, OSError, ValueError, zipfile.BadZipFile) as exc:
                errors.append({"id": item.get("id"), "error": str(exc)})
        if not records:
            raise ExtractionError("no selected supported materials were extracted")
        status_counts: dict[str, int] = {}
        for record in records:
            status = record["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        payload = {
            "schemaVersion": 1,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "manifestSha256": sha256(args.manifest),
            "items": records,
            "errors": errors,
            "summary": {"total": len(records), "statuses": status_counts, "errors": len(errors)},
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ok = not errors
        print(
            json.dumps(
                {"ok": ok, "output": str(args.output.resolve()), "summary": payload["summary"]},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if ok else 2
    except (ExtractionError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
