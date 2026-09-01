# Linco Skills

[English](README.md) | [简体中文](README.zh-CN.md)

Open-source agent skills maintained by Linco.

## Included skills

### `material-to-video`

Turns user-selected local materials, a researched topic, or both into a traceable narrated vertical video for Douyin, Xiaohongshu, WeChat Channels, or one cross-platform master.

The skill owns source intake, local extraction, research records, claim traceability, editorial planning, VoxCPM narration, cover planning, and bounded visual review. HyperFrames owns composition, preview, checks, and rendering.

Supported local inputs include PNG, JPEG, WebP, GIF, PDF, DOCX, PPTX, TXT, Markdown, HTML, WAV, MP3, M4A, MP4, MOV, and WebM. Text, HTML, DOCX, and PPTX are extracted locally. Audio and video metadata use FFprobe. PDF text uses optional `pypdf` or `pdftotext`; images and media requiring semantic interpretation remain hard-gated until visual review or transcription is recorded.

### `meaning-led-photo-poster`

Creates a standalone premium editorial poster from each uploaded photo using GPT Image 2 reference-image editing. The output is a 3:4 vertical poster with an exact horizontal 50/50 split: realistic photography on top and a recognizable reinterpretation of the subject below, with fine-line doodle people and sparse handwritten copy.

The workflow requires Bun and a configured GPT Image 2 CLI that supports reference images. It asks for authorization before sending identifiable people to the external image endpoint, and verifies each generated file before reporting success.

## Requirements

- Codex Desktop with access to the user-selected local paths
- Python 3.10 or newer
- Node.js 22 or newer
- FFmpeg and FFprobe
- HyperFrames for composition, preview, and rendering
- A compatible VoxCPM Gradio endpoint when narration is enabled
- Optional: `pypdf` or `pdftotext` for deterministic PDF text extraction

The Python scripts otherwise use only the standard library.

## Installation

### Install with the Skills CLI

Install `material-to-video` into the current project:

```bash
npx --yes skills add lincotalk/linco-skills@material-to-video -y
```

Install `meaning-led-photo-poster` into the current project:

```bash
npx --yes skills add lincotalk/linco-skills@meaning-led-photo-poster -y
```

On Windows PowerShell, use `npx.cmd` when script execution policy blocks `npx.ps1`:

```powershell
npx.cmd --yes skills add lincotalk/linco-skills@material-to-video -y
npx.cmd --yes skills add lincotalk/linco-skills@meaning-led-photo-poster -y
```

Project installation places the Skill under `.agents/skills/material-to-video` so it
travels with that project. Add `-g` for a user-level installation available across
projects:

```bash
npx --yes skills add lincotalk/linco-skills@material-to-video -g -y
```

For a user-level installation of the poster skill, use the same command with
`meaning-led-photo-poster` in place of `material-to-video`.

Install or update the HyperFrames skill pack required for composition and rendering:

```bash
npx hyperframes@latest skills
```

Reload Codex after installation so the new Skill is discovered.

### Install from source

Clone the repository, optionally check out a release tag, then copy the skills you need into the Codex skills directory.

PowerShell:

```powershell
git clone https://github.com/lincotalk/linco-skills.git
Set-Location .\linco-skills
# Optional: git checkout v0.1.0

$codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
New-Item -ItemType Directory -Force (Join-Path $codexRoot "skills") | Out-Null
$skillTarget = Join-Path $codexRoot "skills\material-to-video"
New-Item -ItemType Directory -Force $skillTarget | Out-Null
Copy-Item -Recurse -Force .\material-to-video\* $skillTarget
$posterTarget = Join-Path $codexRoot "skills\meaning-led-photo-poster"
New-Item -ItemType Directory -Force $posterTarget | Out-Null
Copy-Item -Recurse -Force .\meaning-led-photo-poster\* $posterTarget
```

Bash:

```bash
git clone https://github.com/lincotalk/linco-skills.git
cd linco-skills
# Optional: git checkout v0.1.0

mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/material-to-video"
cp -R ./material-to-video/. "${CODEX_HOME:-$HOME/.codex}/skills/material-to-video"
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/meaning-led-photo-poster"
cp -R ./meaning-led-photo-poster/. "${CODEX_HOME:-$HOME/.codex}/skills/meaning-led-photo-poster"
```

Confirm that `<skills-directory>/material-to-video/SKILL.md` and `<skills-directory>/meaning-led-photo-poster/SKILL.md` exist, then reload Codex.
To update a source installation later, run `git pull` in the cloned repository and repeat
the copy command. HyperFrames scaffolds each generated project with a pinned CLI version,
keeping later preview and render commands reproducible.

## Usage

Example requests:

```text
Use $material-to-video to turn these selected slides into a Xiaohongshu video: D:\materials\deck.pptx
```

```text
Use $material-to-video to research how MCP tool discovery differs from permission, then make a Douyin technical single-point video.
```

```text
Use $material-to-video to combine these local notes with current official sources and produce one cross-platform version. Finish autonomously until the mandatory final render approval.
```

```text
Use $meaning-led-photo-poster to turn this uploaded photo into a premium 3:4 editorial poster with an exact 50/50 split.
```

Every job is isolated under `<workspace>/jobs/<job-slug>`. Source records and editorial models remain at the job root. The HyperFrames project lives in `project/`, with `BRIEF.md`, `STORYBOARD.md`, and `SCRIPT.md` at that project root as required by HyperFrames.

The skill never publishes or uploads the final result to a social platform.

## Narration service

The repository does not include, host, or default to a narration endpoint. Deploy [OpenBMB/VoxCPM](https://github.com/OpenBMB/VoxCPM), then configure the base URL of its compatible Gradio service. The base URL must expose `/config`, `/gradio_api/info`, and the named `/generate` API documented in [`tts-contract.md`](material-to-video/references/tts-contract.md).

Do not configure the concrete `/generate` route. For example, use `https://tts.example.com`, not `https://tts.example.com/generate`.

PowerShell:

```powershell
$env:VOXCPM_TTS_URL = "https://your-voxcpm-service.example.com"
$env:VOXCPM_TTS_TOKEN = "your-bearer-token" # only when required
python material-to-video/scripts/generate_voxcpm_voice.py --check `
  --config material-to-video/assets/config.example.json
```

Bash:

```bash
export VOXCPM_TTS_URL="https://your-voxcpm-service.example.com"
export VOXCPM_TTS_TOKEN="your-bearer-token" # only when required
python material-to-video/scripts/generate_voxcpm_voice.py --check \
  --config material-to-video/assets/config.example.json
```

You may instead pass `--endpoint` or set `tts.endpoint` in a job-local config. Prefer `VOXCPM_TTS_TOKEN` over `--auth-token`, which may be visible in a process list. Never put credentials in the endpoint URL or job config.

Check configuration without making a network request:

```bash
python material-to-video/scripts/generate_voxcpm_voice.py --check-config \
  --config material-to-video/assets/config.example.json
```

On first use, the Skill runs this offline preflight automatically. When no service is configured, it links to OpenBMB/VoxCPM and asks users who already deployed it to provide the Gradio service base URL. Content planning may continue, but narration remains a hard stop until the service is configured and passes the live `--check`.

When no endpoint is configured, the client returns `tts_not_configured`, makes no network request, and preserves the approved script for resume. Treat any configured TTS service as an external data processor. Do not send confidential narration or reference audio to an untrusted deployment.

## Validation

Run the repository checks before contributing or releasing:

```bash
python -m compileall -q material-to-video
python -m unittest discover -s tests -v
```

CI runs the same checks on Windows and Ubuntu with Python 3.10 and 3.12. A live VoxCPM call and a full HyperFrames render require external services and are intentionally not part of repository CI.

## Security and privacy

Local material is read only from paths selected by the user. The workflow does not disclose private local content to search services, rejects manifest path traversal, blocks cross-origin TTS redirects, and keeps bearer tokens out of generated manifests. See [SECURITY.md](SECURITY.md) for vulnerability reporting.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). By contributing, you agree that your contribution is licensed under the MIT License.

## License

Copyright 2026 Linco. Licensed under the [MIT License](LICENSE).
