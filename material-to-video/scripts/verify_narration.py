#!/usr/bin/env python3
"""Verify VoxCPM narration segments and build a junction-listening preview."""

from __future__ import annotations

import argparse
import array
import json
import math
import sys
import wave
from pathlib import Path
from typing import Any


class NarrationError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--junction-preview", type=Path)
    parser.add_argument("--concat-output", type=Path)
    parser.add_argument("--excerpt-seconds", type=float, default=1.5)
    parser.add_argument("--max-rms-delta-db", type=float)
    parser.add_argument("--max-clipped-sample-ratio", type=float)
    parser.add_argument(
        "--require-reference-for-multiple",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    return parser.parse_args()


def read_quality_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    quality = value.get("tts", {}).get("quality", {}) if isinstance(value, dict) else {}
    if not isinstance(quality, dict):
        raise NarrationError("Config tts.quality must be an object")
    return quality


def resolve_inputs(values: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    for value in values:
        path = value.resolve()
        if path.is_dir():
            resolved.extend(sorted(path.glob("*.wav")))
        elif path.is_file():
            resolved.append(path)
        else:
            raise NarrationError(f"Narration input does not exist: {path}")
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in resolved:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    if not unique:
        raise NarrationError("No WAV inputs found")
    return unique


def analyze_wav(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            sample_rate = audio.getframerate()
            frame_count = audio.getnframes()
            compression = audio.getcomptype()
            if sample_width != 2 or compression != "NONE":
                raise NarrationError(f"Only uncompressed 16-bit PCM WAV is supported: {path}")
            sample_count = 0
            square_sum = 0
            peak = 0
            clipped = 0
            while data := audio.readframes(65536):
                samples = array.array("h")
                samples.frombytes(data)
                if sys.byteorder != "little":
                    samples.byteswap()
                sample_count += len(samples)
                for sample in samples:
                    magnitude = abs(sample)
                    peak = max(peak, magnitude)
                    square_sum += sample * sample
                    if magnitude >= 32767:
                        clipped += 1
    except (wave.Error, OSError) as exc:
        raise NarrationError(f"Unreadable WAV {path}: {exc}") from exc
    if min(channels, sample_rate, frame_count, sample_count) <= 0:
        raise NarrationError(f"Empty WAV: {path}")
    rms = math.sqrt(square_sum / sample_count)
    rms_dbfs = 20 * math.log10(rms / 32768) if rms else float("-inf")
    peak_dbfs = 20 * math.log10(peak / 32768) if peak else float("-inf")
    return {
        "path": str(path),
        "channels": channels,
        "sampleWidthBytes": sample_width,
        "sampleRateHz": sample_rate,
        "frames": frame_count,
        "durationSeconds": round(frame_count / sample_rate, 6),
        "rmsDbfs": round(rms_dbfs, 3),
        "peakDbfs": round(peak_dbfs, 3),
        "clippedSampleRatio": clipped / sample_count,
    }


def read_manifest(path: Path) -> dict[str, Any] | None:
    manifest_path = path.with_suffix(path.suffix + ".generation.json")
    if not manifest_path.is_file():
        return None
    value = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise NarrationError(f"Generation manifest root is not an object: {manifest_path}")
    return value


def format_key(item: dict[str, Any]) -> tuple[int, int, int]:
    return (item["channels"], item["sampleWidthBytes"], item["sampleRateHz"])


def read_excerpt(path: Path, *, head: bool, seconds: float) -> tuple[wave._wave_params, bytes]:
    with wave.open(str(path), "rb") as audio:
        params = audio.getparams()
        count = min(audio.getnframes(), max(1, round(seconds * audio.getframerate())))
        if not head:
            audio.setpos(audio.getnframes() - count)
        return params, audio.readframes(count)


def params_format(params: wave._wave_params) -> tuple[int, int, int, str]:
    return (params.nchannels, params.sampwidth, params.framerate, params.comptype)


def build_junction_preview(inputs: list[Path], output: Path, seconds: float) -> None:
    if len(inputs) < 2:
        raise NarrationError("A junction preview requires at least two inputs")
    if seconds <= 0:
        raise NarrationError("--excerpt-seconds must be positive")
    first_params, _ = read_excerpt(inputs[0], head=True, seconds=seconds)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as target:
        target.setparams(first_params)
        short_gap = b"\x00" * (
            round(0.25 * first_params.framerate)
            * first_params.nchannels
            * first_params.sampwidth
        )
        long_gap = b"\x00" * (
            round(0.75 * first_params.framerate)
            * first_params.nchannels
            * first_params.sampwidth
        )
        for left, right in zip(inputs, inputs[1:]):
            left_params, tail = read_excerpt(left, head=False, seconds=seconds)
            right_params, head = read_excerpt(right, head=True, seconds=seconds)
            if (
                params_format(left_params) != params_format(first_params)
                or params_format(right_params) != params_format(first_params)
            ):
                raise NarrationError("All junction-preview WAV files must share one PCM format")
            target.writeframes(tail)
            target.writeframes(short_gap)
            target.writeframes(head)
            target.writeframes(long_gap)


def concatenate_wavs(inputs: list[Path], output: Path) -> None:
    resolved_output = output.resolve()
    if resolved_output in inputs:
        raise NarrationError("--concat-output must not overwrite an input segment")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with wave.open(str(inputs[0]), "rb") as first:
            expected = first.getparams()
        with wave.open(str(temporary), "wb") as target:
            target.setparams(expected)
            for path in inputs:
                with wave.open(str(path), "rb") as source:
                    if params_format(source.getparams()) != params_format(expected):
                        raise NarrationError("All concatenated WAV files must share one PCM format")
                    while data := source.readframes(65536):
                        target.writeframesraw(data)
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    args = parse_args()
    try:
        quality = read_quality_config(args.config)
        max_rms_delta = (
            args.max_rms_delta_db
            if args.max_rms_delta_db is not None
            else float(quality.get("maxRmsDeltaDb", 4.0))
        )
        max_clipped_ratio = (
            args.max_clipped_sample_ratio
            if args.max_clipped_sample_ratio is not None
            else float(quality.get("maxClippedSampleRatio", 0.0001))
        )
        require_reference = (
            args.require_reference_for_multiple
            if args.require_reference_for_multiple is not None
            else bool(quality.get("requireReferenceForMultipleSegments", True))
        )
        inputs = resolve_inputs(args.input)
        analysis = [analyze_wav(path) for path in inputs]
        manifests = [read_manifest(path) for path in inputs]
        errors: list[str] = []
        warnings: list[str] = []

        if len({format_key(item) for item in analysis}) != 1:
            errors.append("Narration segments do not share one PCM format")
        for item in analysis:
            if item["clippedSampleRatio"] > max_clipped_ratio:
                errors.append(
                    f"Clipping exceeds limit in {Path(item['path']).name}: "
                    f"{item['clippedSampleRatio']:.6f} > {max_clipped_ratio:.6f}"
                )
        finite_rms = [item["rmsDbfs"] for item in analysis if math.isfinite(item["rmsDbfs"])]
        rms_delta = max(finite_rms) - min(finite_rms) if finite_rms else float("inf")
        if rms_delta > max_rms_delta:
            errors.append(f"RMS level drift is {rms_delta:.3f} dB; limit is {max_rms_delta:.3f} dB")

        if len(inputs) > 1:
            missing = [inputs[index].name for index, value in enumerate(manifests) if value is None]
            if missing:
                errors.append("Missing generation manifests: " + ", ".join(missing))
            present = [value for value in manifests if value is not None]
            references = {
                value.get("request", {}).get("referenceAudioSha256")
                for value in present
                if isinstance(value.get("request"), dict)
            }
            references.discard(None)
            if require_reference and len(references) != 1:
                errors.append("Multiple narration segments must use one reference-audio SHA-256")
            controls = {
                value.get("request", {}).get("controlInstruction")
                for value in present
                if isinstance(value.get("request"), dict)
            }
            controls.discard(None)
            if len(controls) > 1:
                errors.append("Narration segments use different control instructions")
            modes = {value.get("mode") for value in present}
            modes.discard(None)
            if require_reference and modes != {"reference"}:
                errors.append("Multiple narration segments must all use reference mode")
        elif manifests[0] is None:
            warnings.append("Generation manifest is missing; speaker provenance was not verified")

        preview = None
        if args.junction_preview is not None:
            build_junction_preview(inputs, args.junction_preview.resolve(), args.excerpt_seconds)
            preview = str(args.junction_preview.resolve())

        concatenated = None
        if not errors and args.concat_output is not None:
            concatenate_wavs(inputs, args.concat_output.resolve())
            concatenated = str(args.concat_output.resolve())

        result = {
            "ok": not errors,
            "segmentCount": len(inputs),
            "segments": analysis,
            "rmsDeltaDb": round(rms_delta, 3) if math.isfinite(rms_delta) else None,
            "junctionPreview": preview,
            "concatenatedOutput": concatenated,
            "errors": errors,
            "warnings": warnings,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not errors else 2
    except (NarrationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
