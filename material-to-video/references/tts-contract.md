# VoxCPM TTS contract

## Service

- Provider: `voxcpm-gradio`.
- The open-source skill ships with no endpoint. `tts.endpoint` is `null` by default and the client must not guess, probe, or fall back to a bundled service URL.
- Endpoint precedence: `--endpoint`, then `VOXCPM_TTS_URL`, then `tts.endpoint` from the project config.
- Bearer-token precedence: `--auth-token`, then the environment variable named by `tts.authTokenEnv` (`VOXCPM_TTS_TOKEN` by default). Prefer the environment variable. Never store the token in the job config, endpoint URL, logs, or generation manifest.
- Named API: `/generate` through the Gradio 6 call endpoint `/gradio_api/call/v2/generate`.
- Completion: SSE at `/gradio_api/call/generate/<event_id>`.
- Modes: use `voice-design` only to create a short speaker sample; use `reference` with the approved sample for production narration.
- Current observed model: VoxCPM2. Always inspect `/config` and `/gradio_api/info` at runtime.
- Output: PCM WAV file without word timestamps.
- Default preset: `female`. Keep it when the user does not mention narrator gender.
- Default male preset: `male`. Select it when the user explicitly requests a male narrator without any more specific voice direction.
- User direction wins: when the user specifies age, timbre, emotion, pace, role, or delivery beyond gender, apply those details as job-local overrides. Do not force a default preset unchanged and do not infer narrator gender from the topic, audience, or platform.
- Default delivery baseline: for either gender, use calm, stable, natural standard Mandarin with low performance, medium or slightly slow pace, semantic rather than uniform stress, varied meaning-led pauses, and sentence endings that settle naturally.
- Anti-synthetic gate: reject fixed sentence arcs, equal-length pauses, repeated sentence-final rises, uniform emphasis, artificial smiling, over-articulation, fixed pitch, or any other obvious AI cadence. Keep this gate when age, gender, or timbre changes unless the user explicitly requests a stylized performance.

Use [generate_voxcpm_voice.py](../scripts/generate_voxcpm_voice.py). The script uses only the Python standard library, validates the live Gradio contract, rejects cross-origin results and redirects, downloads the result locally, validates the WAV, and writes a generation manifest.

## First-run onboarding

Run `--check-config` immediately after initializing the job config. It resolves only local arguments, environment variables, and config fields; it never contacts the endpoint. An unconfigured preflight exits zero with `configured: false`, `code: tts_not_configured`, the OpenBMB/VoxCPM repository URL, and the required API contract.

Tell an unconfigured user that narration requires a self-hosted deployment of [OpenBMB/VoxCPM](https://github.com/OpenBMB/VoxCPM). If they already deployed it, ask for the Gradio service base URL, such as `https://tts.example.com`. The base URL must expose Gradio `/config`, `/gradio_api/info`, and the named `/generate` API; do not append `/generate` to the configured endpoint. Do not ask the user to paste bearer tokens into chat. Use `VOXCPM_TTS_TOKEN` locally when authentication is required.

The preflight is informational and does not block source analysis. Record whether an endpoint was configured, continue editorial work, and hard-stop only when narration is reached without a usable service.

## Availability check

Run `--check` before generating narration. Use `tts.checkTimeoutSeconds` (10 seconds by default); endpoint discovery must not inherit the longer generation timeout. When no endpoint is configured, the client exits with code `2`, returns `code: tts_not_configured`, and makes no network request. If the service is unconfigured, unreachable, or exposes a changed contract:

1. Preserve `SCRIPT.md` and all material analysis.
2. Set `run.json.status` to `awaiting_tts_config`.
3. Set `run.json.resumeFrom` to `generate-voiceover`.
4. Repeat the OpenBMB/VoxCPM repository link. If the service is already deployed, ask for its Gradio base URL and configure it through `VOXCPM_TTS_URL`, `--endpoint`, or `tts.endpoint`.
5. For a bearer-protected deployment, set `VOXCPM_TTS_TOKEN` or pass `--auth-token`; do not add credentials to the endpoint URL.
6. Do not fall back to HeyGen, OpenAI, or another external provider.

## Speaker lock

Choose the voice-design preset with this precedence:

1. Explicit user voice direction, recorded as job-local overrides.
2. `male` when the user explicitly requests a male narrator and gives no other voice direction.
3. `female` when narrator gender is unspecified.

Record explicit requests such as `声音平稳，不要有 AI 腔` in the job config as `tts.speaker.jobVoiceDirection`, and reinforce them in the effective control instruction. Do not treat a label such as `natural` as proof that the generated audio is natural; approval depends on listening to the sample.

The built-in presets are:

- `female` / `ai-tech-female-calm-natural-v2`: a young adult woman speaking standard Mandarin calmly and naturally, as if explaining familiar tools to a friend in a quiet room. Keep a neutral-soft timbre, low arousal, stable emotion, medium-slow pace, restrained semantic stress, varied pauses, and naturally settling sentence endings. Reject childish, cloying, cutesy, breathy, nasal, coquettish, dramatic, advertising, newsreader, exaggerated influencer, or synthetic delivery.
- `male` / `ai-tech-male-blogger-natural-v1`: a 25-40-year-old Chinese male technology creator speaking standard Mandarin naturally to camera about AI. Keep a neutral-warm timbre, normal pitch, low arousal, stable emotion, clear organization, medium pace, moderate stress, and natural pauses. Reject obvious smiling, raised volume, continuous heavy stress, upward or promotional sentence endings, performative delivery, newsreader delivery, advertising delivery, and excited influencer delivery.

The profile labels describe configured delivery but are not fixed speakers. Male and female presets use the same two-stage procedure: generate one canonical sample in `voice-design` mode, then generate production speech in `reference` mode. Their control instructions and seeds differ; their invocation does not. Generate one project-local reference WAV per video, record its exact transcript and audio/text SHA-256 values, and reuse that reference for every production segment in the video. Do not package a persistent reference WAV inside the skill.

Every built-in preset carries the same fixed, neutral `referenceSampleText`: `大模型并不是在数据库里寻找固定答案。它会根据上下文预测接下来最可能出现的内容，这也是理解生成式 AI 的第一步。` Do not derive the sample text from the current video's hook, title, list, or narration. VoxCPM conditions delivery on sample text, so changing that text can change energy, stress, and sentence endings even when the control instruction and seed are unchanged.

Generate the canonical sample with `--preset-sample`, which rejects `--text`, `--text-file`, and reference mode:

```bash
python <skill-dir>/scripts/generate_voxcpm_voice.py \
  --config <job-dir>/material-to-video.config.json \
  --voice-preset <female-or-male> \
  --speaker-mode voice-design \
  --preset-sample \
  --output <job-dir>/audio/voice-sample.wav
```

Approve the sample only after listening for naturalness, pronunciation, the selected preset's age and timbre, professional credibility, and pace. Explicitly reject fixed pitch, metronomic or equal-length pauses, repeated sentence contours, sentence-final lift, uniform heavy stress, artificial smiling, over-articulation, synthetic cadence, or unwanted performance. Technical WAV validation is necessary but never sufficient for voice approval. The generation manifest must report `usedPresetSample: true` and `presetSampleTextSha256`. Then set `tts.speaker.mode` to `reference`, set `referenceAudio` to that project-local WAV, and set `referenceText` to the exact canonical text spoken in the WAV. Keep the selected `tts.speaker.preset` for provenance and do not regenerate the sample between segments.

Generate reference-locked speech with:

```bash
python <skill-dir>/scripts/generate_voxcpm_voice.py \
  --config <job-dir>/material-to-video.config.json \
  --text-file <tts-input.txt> \
  --output <narration.wav>
```

The client uploads the reference audio to the configured Gradio host for the request. Do not send confidential reference audio to an unsecured deployment.

## Generation

Run the segmentation planner for every locked script:

```bash
python <skill-dir>/scripts/plan_tts_segments.py \
  --input <tts-input.txt> \
  --output-dir <job-dir>/audio/segments \
  --config <job-dir>/material-to-video.config.json
```

The defaults target about 30 seconds and cap each request at about 45 seconds using a conservative Mandarin character-rate estimate. Use one request only when the planner emits one segment. Otherwise submit the planned segments directly. Do not probe service capacity with the full narration first, and do not retry an unchanged request that already reached a timeout.

Use separate timeout classes:

- `checkTimeoutSeconds`: endpoint and API-contract checks; default 10 seconds.
- `generationTimeoutSeconds`: hard wall-clock budget for one bounded segment; default 180 seconds.
- `stallTimeoutSeconds`: maximum SSE silence while a job is running; default 45 seconds.

If a segment times out, run one short availability check. If healthy, retry only that segment once. If it fails again, split that segment at a natural boundary and continue; if unhealthy, preserve state and stop at `generate-voiceover`. Never launch concurrent retries against the same event.

Within one video, reuse the same reference-audio SHA-256, exact reference transcript, control instruction, and generation parameters for every segment. Never concatenate independently voice-designed segments or alternate speakers.

For multiple segments, run:

```bash
python <skill-dir>/scripts/verify_narration.py \
  --input <segment-01.wav> --input <segment-02.wav> \
  --junction-preview <narration-junctions.wav> \
  --concat-output <narration.wav>
```

The verifier requires one reference-audio SHA across segments, checks PCM format, clipping and RMS-level drift, creates a short boundary review file, and concatenates only after validation passes. Listen to the junction preview and then the complete narration. Wait for narration approval before transcription, caption timing, composition retiming, or final render unless autonomous completion was explicitly authorized.

Record endpoint, live model, mode, request parameters, text SHA-256, reference-audio SHA-256, reference-text SHA-256, output duration, audio SHA-256, and local path. Do not include full narration or reference text in the generation manifest.

The endpoint has no word timing. Run transcription or forced alignment on the generated audio before captions. Inspect English names, numbers, pauses, clipping, silence, and background noise before locking audio. Keep English technical tokens in their original Latin spelling in TTS input; never translate or transliterate them into Chinese to influence pronunciation.

Treat the configured service as an external data processor. Prefer HTTPS and bearer authentication, and do not send confidential or sensitive text unless the deployment is secured appropriately. The client sends credentials only to the configured origin and blocks cross-origin redirects.
