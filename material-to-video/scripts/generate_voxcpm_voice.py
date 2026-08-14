#!/usr/bin/env python3
"""Check or call the project's VoxCPM Gradio TTS service."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import secrets
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ENDPOINT: str | None = None
DEFAULT_AUTH_TOKEN_ENV = "VOXCPM_TTS_TOKEN"
PROVIDER = "voxcpm-gradio"
API_NAME = "/generate"
VOXCPM_REPOSITORY = "https://github.com/OpenBMB/VoxCPM"
DEFAULT_VOICE_PRESET = "female"
DEFAULT_SEED = 20260803
CANONICAL_REFERENCE_SAMPLE_TEXT = (
    "大模型并不是在数据库里寻找固定答案。它会根据上下文预测接下来最可能出现的内容，"
    "这也是理解生成式 AI 的第一步。"
)
FEMALE_CONTROL = (
    "年轻成年女性，使用自然、平稳的标准普通话，像在安静环境中向朋友介绍熟悉的工具。"
    "音色中性柔和，情绪稳定，整体唤醒度低，语速中等偏慢；重音克制但随语义变化，"
    "停顿长短跟随句意，句尾自然收住，不固定上扬。英文技术名词、缩写和数字发音清楚准确。"
    "避免幼态童声、甜腻夹子音、过度气声、鼻音、撒娇感、播音腔、广告腔、客服腔、"
    "夸张自媒体腔、人工笑意、固定音高、等间隔停顿、逐句同调、连续重读、过度咬字和明显 AI 合成节奏。"
)
MALE_CONTROL = (
    "25到40岁的中国男性科技创作者，使用标准普通话，以日常、平稳、自然的说话状态讲解 AI 知识。"
    "音色中性偏暖，音高正常，情绪稳定，整体唤醒度偏低，语速中等；重音适度且随语义变化，"
    "停顿长短跟随句意，句尾自然收住，不固定上扬。像真实的人在向同事分享熟悉的技术内容。"
    "避免明显笑意、抬高音量、连续重读、促销式句尾、表演感、播音腔、广告腔、夸张自媒体表达、"
    "固定音高、等间隔停顿、逐句同调、过度咬字和明显 AI 合成节奏。"
)
VOICE_PRESETS: dict[str, dict[str, Any]] = {
    "female": {
        "profileId": "ai-tech-female-calm-natural-v2",
        "controlInstruction": FEMALE_CONTROL,
        "referenceSampleText": CANONICAL_REFERENCE_SAMPLE_TEXT,
        "seedValue": DEFAULT_SEED,
    },
    "male": {
        "profileId": "ai-tech-male-blogger-natural-v1",
        "controlInstruction": MALE_CONTROL,
        "referenceSampleText": CANONICAL_REFERENCE_SAMPLE_TEXT,
        "seedValue": 20260817,
    },
}
DEFAULT_PROFILE_ID = VOICE_PRESETS[DEFAULT_VOICE_PRESET]["profileId"]
DEFAULT_CONTROL = VOICE_PRESETS[DEFAULT_VOICE_PRESET]["controlInstruction"]


class TtsError(Exception):
    pass


class TtsConfigError(TtsError):
    pass


class TtsNotConfiguredError(TtsConfigError):
    pass


def deployment_info() -> dict[str, Any]:
    return {
        "project": "OpenBMB/VoxCPM",
        "repository": VOXCPM_REPOSITORY,
        "requiredNamedApi": API_NAME,
        "endpointValue": (
            "The deployed Gradio service base URL, for example https://tts.example.com; "
            "do not append /generate or include credentials."
        ),
        "endpointOptions": ["VOXCPM_TTS_URL", "--endpoint", "tts.endpoint"],
        "authTokenOption": "VOXCPM_TTS_TOKEN",
    }


def url_origin(value: str) -> tuple[str, str, int]:
    parsed = urllib.parse.urlparse(value)
    if not parsed.hostname:
        raise TtsConfigError("TTS URL has no hostname")
    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise TtsConfigError("TTS URL has an invalid port") from exc
    return parsed.scheme.lower(), parsed.hostname.lower(), port


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, endpoint: str) -> None:
        super().__init__()
        self.expected_origin = url_origin(endpoint)

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        resolved = urllib.parse.urljoin(req.full_url, newurl)
        if url_origin(resolved) != self.expected_origin:
            raise TtsError("VoxCPM attempted a cross-origin redirect")
        return super().redirect_request(req, fp, code, msg, headers, resolved)


def open_same_origin(
    request: urllib.request.Request, *, endpoint: str, timeout: float
) -> Any:
    opener = urllib.request.build_opener(SameOriginRedirectHandler(endpoint))
    response = opener.open(request, timeout=timeout)
    if url_origin(response.geturl()) != url_origin(endpoint):
        response.close()
        raise TtsError("VoxCPM returned a response from an unexpected origin")
    return response


def request_headers(auth_token: str | None, *, accept: str) -> dict[str, str]:
    headers = {"Accept": accept}
    if auth_token:
        if "\r" in auth_token or "\n" in auth_token:
            raise TtsConfigError("TTS auth token contains an invalid newline")
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float,
    endpoint: str,
    auth_token: str | None,
) -> Any:
    data = None
    headers = request_headers(auth_token, accept="application/json")
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with open_same_origin(request, endpoint=endpoint, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise TtsError(f"VoxCPM HTTP {exc.code}: {body[-600:]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TtsError(f"Unable to reach VoxCPM at {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise TtsError(f"VoxCPM returned invalid JSON from {url}") from exc


def active_model(config: dict[str, Any]) -> str:
    for component in config.get("components", []):
        if not isinstance(component, dict):
            continue
        value = component.get("props", {}).get("value")
        if not isinstance(value, str):
            continue
        match = re.search(r"Active model:\*\*\s*`([^`]+)`", value, flags=re.I)
        if match:
            return match.group(1)
        match = re.search(r"\b(VoxCPM2(?:-[\w.]+)?)\b", value, flags=re.I)
        if match:
            return match.group(1)
    return "unknown"


def inspect_server(
    endpoint: str, timeout: float, auth_token: str | None
) -> dict[str, Any]:
    config = request_json(
        f"{endpoint}/config", timeout=timeout, endpoint=endpoint, auth_token=auth_token
    )
    api_info = request_json(
        f"{endpoint}/gradio_api/info",
        timeout=timeout,
        endpoint=endpoint,
        auth_token=auth_token,
    )
    endpoints = api_info.get("named_endpoints") if isinstance(api_info, dict) else None
    generate = endpoints.get(API_NAME) if isinstance(endpoints, dict) else None
    if not isinstance(config, dict) or not isinstance(generate, dict):
        raise TtsError(f"VoxCPM server does not expose {API_NAME}")
    parameters = generate.get("parameters")
    if not isinstance(parameters, list):
        raise TtsError("VoxCPM /generate has no parameter list")
    names = {item.get("parameter_name") for item in parameters if isinstance(item, dict)}
    required = {
        "text",
        "control_instruction",
        "ref_wav",
        "use_prompt_text",
        "prompt_text_value",
        "cfg_value",
        "do_normalize",
        "denoise",
        "dit_steps",
    }
    missing = sorted(required - names)
    if missing:
        raise TtsError("VoxCPM contract changed; missing: " + ", ".join(missing))
    return {
        "gradioVersion": config.get("version"),
        "activeModel": active_model(config),
        "parameterNames": sorted(name for name in names if isinstance(name, str)),
    }


def wait_for_job(
    endpoint: str,
    event_id: str,
    timeout: float,
    stall_timeout: float,
    auth_token: str | None,
) -> Any:
    url = f"{endpoint}/gradio_api/call/generate/{urllib.parse.quote(event_id)}"
    request = urllib.request.Request(
        url, headers=request_headers(auth_token, accept="text/event-stream")
    )
    current_event = None
    deadline = time.monotonic() + timeout
    try:
        with open_same_origin(
            request, endpoint=endpoint, timeout=min(timeout, stall_timeout)
        ) as response:
            for raw_line in response:
                if time.monotonic() >= deadline:
                    raise TtsError(
                        f"VoxCPM generation exceeded the {timeout:g}s total timeout"
                    )
                line = raw_line.decode("utf-8", errors="replace").strip()
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    if current_event == "error":
                        raise TtsError(f"VoxCPM generation failed: {data}")
                    if current_event == "complete":
                        return data
    except TtsError:
        raise
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        socket.timeout,
        json.JSONDecodeError,
    ) as exc:
        raise TtsError(f"VoxCPM job did not complete: {exc}") from exc
    raise TtsError("VoxCPM job ended without a complete event")


def generate_audio(
    endpoint: str,
    payload: dict[str, Any],
    timeout: float,
    stall_timeout: float,
    auth_token: str | None,
) -> tuple[str, str]:
    result = request_json(
        f"{endpoint}/gradio_api/call/v2/generate",
        method="POST",
        payload=payload,
        timeout=timeout,
        endpoint=endpoint,
        auth_token=auth_token,
    )
    event_id = result.get("event_id") if isinstance(result, dict) else None
    if not isinstance(event_id, str) or not event_id:
        raise TtsError("VoxCPM did not return an event_id")
    completed = wait_for_job(endpoint, event_id, timeout, stall_timeout, auth_token)
    if not isinstance(completed, list) or not completed or not isinstance(completed[0], dict):
        raise TtsError("VoxCPM did not return an audio file")
    audio_url = completed[0].get("url")
    if not isinstance(audio_url, str) or not audio_url:
        raise TtsError("VoxCPM audio result has no URL")
    resolved = urllib.parse.urljoin(endpoint + "/", audio_url)
    if url_origin(resolved) != url_origin(endpoint):
        raise TtsError("VoxCPM returned an audio URL on an unexpected host")
    return event_id, resolved


def uploaded_path(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict):
        path = value.get("path")
        if isinstance(path, str) and path:
            return path
        for key in ("files", "data"):
            found = uploaded_path(value.get(key))
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = uploaded_path(item)
            if found:
                return found
    return None


def upload_reference_audio(
    endpoint: str, path: Path, timeout: float, auth_token: str | None
) -> dict[str, Any]:
    boundary = f"----codex-material-video-{secrets.token_hex(12)}"
    mime_type = mimetypes.guess_type(path.name)[0] or "audio/wav"
    safe_name = path.name.replace('"', "")
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="{safe_name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode("utf-8")
    body = prefix + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("ascii")
    request = urllib.request.Request(
        f"{endpoint}/gradio_api/upload",
        data=body,
        headers={
            **request_headers(auth_token, accept="application/json"),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with open_same_origin(request, endpoint=endpoint, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise TtsError(f"Unable to upload reference audio: HTTP {exc.code}: {detail[-600:]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise TtsError(f"Unable to upload reference audio: {exc}") from exc
    server_path = uploaded_path(result)
    if not server_path:
        raise TtsError("VoxCPM upload did not return a server file path")
    return {
        "path": server_path,
        "url": None,
        "size": path.stat().st_size,
        "orig_name": path.name,
        "mime_type": mime_type,
        "is_stream": False,
        "meta": {"_type": "gradio.FileData"},
    }


def download_audio(
    url: str,
    output: Path,
    timeout: float,
    *,
    endpoint: str,
    auth_token: str | None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        request = urllib.request.Request(
            url, headers=request_headers(auth_token, accept="audio/wav,*/*")
        )
        with open_same_origin(request, endpoint=endpoint, timeout=timeout) as response:
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".tmp", dir=output.parent, delete=False
            ) as temporary:
                temporary_name = temporary.name
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)
        Path(temporary_name).replace(output)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        raise TtsError(f"Unable to download VoxCPM audio: {exc}") from exc
    finally:
        if temporary_name and Path(temporary_name).exists():
            Path(temporary_name).unlink()


def inspect_wav(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            sample_rate = audio.getframerate()
            frames = audio.getnframes()
    except (wave.Error, OSError) as exc:
        raise TtsError(f"Generated output is not a readable PCM WAV: {exc}") from exc
    if min(channels, sample_width, sample_rate, frames) <= 0:
        raise TtsError("Generated WAV is empty or invalid")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "format": "wav",
        "codec": f"pcm_s{sample_width * 8}le",
        "channels": channels,
        "sampleRateHz": sample_rate,
        "durationSeconds": round(frames / sample_rate, 6),
        "bytes": path.stat().st_size,
        "sha256": digest,
    }


def read_config(path: Path | None) -> tuple[dict[str, Any], Path]:
    if path is None:
        return {}, Path.cwd()
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise TtsError("Config root must be an object")
    tts = value.get("tts", {})
    if not isinstance(tts, dict):
        raise TtsError("Config tts field must be an object")
    return tts, path.resolve().parent


def normalized_endpoint(value: str | None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TtsNotConfiguredError(
            "TTS endpoint is not configured. Set VOXCPM_TTS_URL, pass --endpoint, "
            "or set tts.endpoint in the job config."
        )
    endpoint = value.strip().rstrip("/")
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise TtsConfigError(
            "TTS endpoint is invalid. Use an http:// or https:// URL in VOXCPM_TTS_URL, "
            "--endpoint, or tts.endpoint."
        )
    if parsed.username is not None or parsed.password is not None:
        raise TtsConfigError(
            "Do not put TTS credentials in the endpoint URL; use VOXCPM_TTS_TOKEN"
        )
    if parsed.query or parsed.fragment:
        raise TtsConfigError(
            "TTS endpoint must not contain a query string or fragment"
        )
    if parsed.path.rstrip("/").lower().endswith("/generate"):
        raise TtsConfigError(
            "TTS endpoint must be the Gradio service base URL; do not append /generate"
        )
    url_origin(endpoint)
    return endpoint


def read_optional_text(value: str | None, path: Path | None) -> str | None:
    if value is not None:
        return value.strip()
    if path is not None:
        return path.read_text(encoding="utf-8-sig").strip()
    return None


def resolve_local_path(value: str | Path | None, base: Path) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def normalized_mode(value: str | None, has_reference: bool) -> str:
    if value is None:
        return "reference" if has_reference else "voice-design"
    mode = value.strip().lower().replace("_", "-")
    if mode in {"voice-design", "design"}:
        return "voice-design"
    if mode in {"reference", "voice-reference", "clone"}:
        return "reference"
    raise TtsError("speaker mode must be voice-design or reference")


def resolve_voice_preset(
    config: dict[str, Any], speaker: dict[str, Any], requested: str | None
) -> tuple[str, dict[str, Any]]:
    preset_id = requested or speaker.get("preset") or config.get("defaultVoicePreset")
    if preset_id is None:
        preset_id = DEFAULT_VOICE_PRESET
    if not isinstance(preset_id, str) or not preset_id.strip():
        raise TtsError("voice preset must be a non-empty string")
    preset_id = preset_id.strip().lower()

    configured = config.get("voicePresets", {})
    if not isinstance(configured, dict):
        raise TtsError("Config tts.voicePresets must be an object")
    configured_preset = configured.get(preset_id, {})
    if not isinstance(configured_preset, dict):
        raise TtsError(f"Config voice preset {preset_id!r} must be an object")

    preset = dict(VOICE_PRESETS.get(preset_id, {}))
    preset.update(configured_preset)
    if not preset:
        available = sorted(set(VOICE_PRESETS) | set(configured))
        raise TtsError(
            f"Unknown voice preset {preset_id!r}; available presets: {', '.join(available)}"
        )
    return preset_id, preset


def resolve_generation_text(
    text_value: str | None,
    text_file: Path | None,
    *,
    preset_sample: bool,
    preset: dict[str, Any],
    mode: str,
) -> tuple[str, bool]:
    if preset_sample:
        if text_value is not None or text_file is not None:
            raise TtsError("--preset-sample cannot be combined with --text or --text-file")
        if mode != "voice-design":
            raise TtsError("--preset-sample requires voice-design speaker mode")
        sample_text = preset.get("referenceSampleText")
        if not isinstance(sample_text, str) or not sample_text.strip():
            raise TtsError("Selected voice preset has no non-empty referenceSampleText")
        return sample_text.strip(), True

    if text_value is None and text_file is None:
        raise TtsError("Generation requires --text, --text-file, or --preset-sample")
    resolved = (
        text_value
        if text_value is not None
        else text_file.read_text(encoding="utf-8-sig")
    )
    resolved = resolved.strip()
    if not resolved:
        raise TtsError("TTS text must not be empty")
    return resolved, False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    check = parser.add_mutually_exclusive_group()
    check.add_argument("--check", action="store_true", help="Check the live VoxCPM service")
    check.add_argument(
        "--check-config",
        action="store_true",
        help="Inspect endpoint configuration without making a network request",
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--endpoint")
    parser.add_argument(
        "--auth-token",
        help="Bearer token override; prefer VOXCPM_TTS_TOKEN to avoid process-list exposure",
    )
    parser.add_argument("--output", type=Path)
    text = parser.add_mutually_exclusive_group()
    text.add_argument("--text")
    text.add_argument("--text-file", type=Path)
    parser.add_argument(
        "--preset-sample",
        action="store_true",
        help="Generate the selected preset's canonical reference sample",
    )
    parser.add_argument("--speaker-mode")
    parser.add_argument("--voice-preset")
    parser.add_argument("--voice-profile-id")
    parser.add_argument("--ref-wav", type=Path)
    prompt = parser.add_mutually_exclusive_group()
    prompt.add_argument("--prompt-text")
    prompt.add_argument("--prompt-text-file", type=Path)
    parser.add_argument("--control-instruction")
    parser.add_argument("--cfg-value", type=float)
    parser.add_argument("--dit-steps", type=int)
    parser.add_argument("--seed-value", type=int)
    parser.add_argument("--normalize", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--denoise", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--stall-timeout", type=float)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config, config_base = read_config(args.config)
        endpoint_env = config.get("endpointEnv", "VOXCPM_TTS_URL")
        if not isinstance(endpoint_env, str) or not endpoint_env.strip():
            raise TtsConfigError("tts.endpointEnv must be a non-empty environment variable name")
        endpoint = normalized_endpoint(
            args.endpoint
            or os.environ.get(endpoint_env.strip())
            or config.get("endpoint")
            or DEFAULT_ENDPOINT
        )
        auth_token_env = config.get("authTokenEnv", DEFAULT_AUTH_TOKEN_ENV)
        if not isinstance(auth_token_env, str) or not auth_token_env.strip():
            raise TtsConfigError("tts.authTokenEnv must be a non-empty environment variable name")
        auth_token = args.auth_token or os.environ.get(auth_token_env.strip())
        if auth_token is not None:
            auth_token = auth_token.strip() or None
        if args.check_config:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "configured": True,
                        "code": "tts_configured",
                        "provider": PROVIDER,
                        "endpoint": endpoint,
                        "authConfigured": bool(auth_token),
                        "networkChecked": False,
                        "deployment": deployment_info(),
                        "action": "Run --check before narration generation to verify the live service contract.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        generation_timeout = args.timeout or float(
            config.get("generationTimeoutSeconds", config.get("timeoutSeconds", 180))
        )
        check_timeout = args.timeout or float(config.get("checkTimeoutSeconds", 10))
        stall_timeout = args.stall_timeout or float(config.get("stallTimeoutSeconds", 45))
        if min(generation_timeout, check_timeout, stall_timeout) <= 0:
            raise TtsError("TTS timeout values must be positive")
        if args.check:
            server = inspect_server(endpoint, check_timeout, auth_token)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "provider": PROVIDER,
                        "endpoint": endpoint,
                        "authConfigured": bool(auth_token),
                        "server": server,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.output is None:
            raise TtsError("Generation requires --output")
        output = args.output.resolve()
        if output.suffix.lower() != ".wav":
            raise TtsError("--output must end in .wav")

        speaker = config.get("speaker", {})
        if not isinstance(speaker, dict):
            raise TtsError("Config tts.speaker must be an object")
        preset_id, preset = resolve_voice_preset(config, speaker, args.voice_preset)
        reference_path = (
            args.ref_wav.resolve()
            if args.ref_wav is not None
            else resolve_local_path(speaker.get("referenceAudio"), config_base)
        )
        mode = normalized_mode(args.speaker_mode or speaker.get("mode"), reference_path is not None)
        text, used_preset_sample = resolve_generation_text(
            args.text,
            args.text_file,
            preset_sample=args.preset_sample,
            preset=preset,
            mode=mode,
        )
        profile_id = (
            args.voice_profile_id
            or speaker.get("profileId")
            or config.get("voiceProfileId")
            or preset.get("profileId")
            or DEFAULT_PROFILE_ID
        )
        prompt_text = read_optional_text(args.prompt_text, args.prompt_text_file)
        if prompt_text is None and isinstance(speaker.get("referenceText"), str):
            prompt_text = speaker["referenceText"].strip()

        server = inspect_server(endpoint, check_timeout, auth_token)
        reference_audio = None
        reference_meta = None
        if mode == "reference":
            if reference_path is None:
                raise TtsError("reference mode requires --ref-wav or tts.speaker.referenceAudio")
            if not reference_path.is_file():
                raise TtsError(f"Reference audio does not exist: {reference_path}")
            if not prompt_text:
                raise TtsError("reference mode requires exact --prompt-text or tts.speaker.referenceText")
            reference_meta = inspect_wav(reference_path)
            expected_audio_sha = speaker.get("referenceAudioSha256")
            if expected_audio_sha and reference_meta["sha256"] != expected_audio_sha:
                raise TtsError("Reference audio SHA-256 does not match the configured speaker profile")
            expected_text_sha = speaker.get("referenceTextSha256")
            actual_text_sha = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
            if expected_text_sha and actual_text_sha != expected_text_sha:
                raise TtsError("Reference transcript SHA-256 does not match the configured speaker profile")
            reference_audio = upload_reference_audio(
                endpoint, reference_path, check_timeout, auth_token
            )
        elif reference_path is not None:
            raise TtsError("Reference audio was provided while speaker mode is voice-design")
        elif prompt_text:
            raise TtsError("Reference text was provided while speaker mode is voice-design")

        control = (
            args.control_instruction
            or config.get("controlInstruction")
            or preset.get("controlInstruction")
            or DEFAULT_CONTROL
        )
        cfg_value = args.cfg_value if args.cfg_value is not None else float(config.get("cfgValue", 2.0))
        dit_steps = args.dit_steps if args.dit_steps is not None else int(config.get("ditSteps", 10))
        configured_seed = config.get("seedValue")
        preset_seed = preset.get("seedValue", DEFAULT_SEED)
        seed = (
            args.seed_value
            if args.seed_value is not None
            else int(configured_seed if configured_seed is not None else preset_seed)
        )
        normalize = args.normalize if args.normalize is not None else bool(config.get("normalize", False))
        denoise = args.denoise if args.denoise is not None else bool(config.get("denoise", False))
        if not 1.0 <= cfg_value <= 3.0 or not 1 <= dit_steps <= 50:
            raise TtsError("Invalid cfgValue or ditSteps")

        payload = {
            "text": text,
            "control_instruction": control,
            "ref_wav": reference_audio,
            "use_prompt_text": bool(prompt_text),
            "prompt_text_value": prompt_text or "",
            "cfg_value": cfg_value,
            "do_normalize": normalize,
            "denoise": denoise,
            "dit_steps": dit_steps,
        }
        if "seed_value" in server["parameterNames"]:
            payload["seed_value"] = seed
        event_id, audio_url = generate_audio(
            endpoint,
            payload,
            generation_timeout,
            stall_timeout,
            auth_token,
        )
        download_audio(
            audio_url,
            output,
            min(generation_timeout, 60),
            endpoint=endpoint,
            auth_token=auth_token,
        )
        audio = inspect_wav(output)
        generation = {
            "schemaVersion": 2,
            "provider": PROVIDER,
            "endpoint": endpoint,
            "authConfigured": bool(auth_token),
            "apiName": API_NAME,
            "mode": mode,
            "server": server,
            "request": {
                "eventId": event_id,
                "textSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "usedPresetSample": used_preset_sample,
                "presetSampleTextSha256": (
                    hashlib.sha256(text.encode("utf-8")).hexdigest()
                    if used_preset_sample
                    else None
                ),
                "controlInstruction": control,
                "cfgValue": cfg_value,
                "ditSteps": dit_steps,
                "seedValue": seed,
                "normalize": normalize,
                "denoise": denoise,
                "voicePresetId": preset_id,
                "voiceProfileId": profile_id,
                "referenceAudioSha256": reference_meta["sha256"] if reference_meta else None,
                "referenceAudioDurationSeconds": (
                    reference_meta["durationSeconds"] if reference_meta else None
                ),
                "referenceTextSha256": (
                    hashlib.sha256(prompt_text.encode("utf-8")).hexdigest() if prompt_text else None
                ),
                "usePromptText": bool(prompt_text),
                "generationTimeoutSeconds": generation_timeout,
                "stallTimeoutSeconds": stall_timeout,
            },
            "output": {"path": str(output), **audio},
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        generation_path = output.with_suffix(output.suffix + ".generation.json")
        generation_path.write_text(
            json.dumps(generation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "output": str(output),
                    "generationManifest": str(generation_path),
                    "mode": mode,
                    "server": server,
                    "audio": audio,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except (TtsError, OSError, ValueError, json.JSONDecodeError) as exc:
        endpoint_not_configured = isinstance(exc, TtsNotConfiguredError)
        config_invalid = isinstance(exc, TtsConfigError) and not endpoint_not_configured
        informational_preflight = endpoint_not_configured and args.check_config
        error_payload = {
            "ok": informational_preflight,
            "configured": False if endpoint_not_configured else None,
            "code": (
                "tts_not_configured"
                if endpoint_not_configured
                else (
                    "tts_config_invalid"
                    if config_invalid
                    else ("tts_unavailable" if args.check else "tts_generation_failed")
                )
            ),
            "errors": [str(exc)],
            "deployment": deployment_info(),
            "action": (
                "Deploy OpenBMB/VoxCPM from the repository above, or, if it is already "
                "deployed, provide the Gradio service base URL through VOXCPM_TTS_URL, "
                "--endpoint, or tts.endpoint. Do not append /generate. Then resume from "
                "generate-voiceover."
                if endpoint_not_configured
                else (
                    "Fix the endpoint configuration. Use the deployed Gradio service base "
                    "URL without credentials, a query string, a fragment, or /generate."
                    if config_invalid
                    else "Check the endpoint and speaker reference configuration, then "
                    "resume from generate-voiceover."
                )
            ),
        }
        if args.check_config:
            error_payload["networkChecked"] = False
        print(
            json.dumps(
                error_payload,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if informational_preflight else 2


if __name__ == "__main__":
    sys.exit(main())
