# Local input policy

## Scope

Apply this policy to the local-input portion of `provided-materials` and `hybrid` jobs. Accept only user-selected local files and directories. Never discover unrelated folders outside the explicit inputs. Treat the agent's current working directory at task start as `workspaceRoot`; do not substitute the skill installation directory, a material directory, the user's home directory, or the system temporary directory.

## Job workspace

Create every job at `<workspaceRoot>/jobs/<job-slug>`. Use a short lowercase ASCII slug made from the platform and topic. Initialize it with `scripts/init_job.py` before scanning materials. Reuse an existing directory only when its `JOB_LAYOUT.json` matches the same workspace and slug; otherwise stop instead of mixing jobs.

Keep all task-created files inside this tree:

```text
jobs/<job-slug>/
  JOB_LAYOUT.json
  MATERIALS.json              # provided-materials or hybrid
  SELECTED_MATERIAL_IDS.txt   # provided-materials or hybrid
  EXTRACTED_MATERIALS.json    # provided-materials or hybrid
  RESEARCH_SOURCES.json       # topic-research or hybrid
  CONTENT_MODEL.json
  VISUAL_PLAN.json
  COVER_PLAN.json
  ASSETS.json
  run.json
  material-to-video.config.json
  audio/
  project/
    BRIEF.md
    STORYBOARD.md
    SCRIPT.md
    hyperframes.json
  review/
  tmp/
  logs/
  final/
```

- Put narration and alignment artifacts in `audio/`.
- Initialize the complete HyperFrames project, including dependencies, in `project/` before writing its plan files. HyperFrames requires `BRIEF.md`, `STORYBOARD.md`, and `SCRIPT.md` at this project root.
- Keep `MATERIALS.json`, `EXTRACTED_MATERIALS.json`, research records, content models, and job state at the job root. Refer to them from the project-root brief using paths relative to `project/`; do not maintain editable duplicate copies.
- Put video snapshots, cover crop previews, contact sheets, and `LAYOUT_REVIEW.json` in `review/`.
- Put disposable intermediates in `tmp/`; point child-process `TEMP`, `TMP`, and equivalent configurable caches there.
- Put task logs in `logs/` and only delivery-ready MP4 and platform cover variants in `final/`.
- Do not place generated files in the workspace root, source directories, the skill directory, the home directory, or an arbitrary system-temp path. Tool-owned global caches are acceptable only when their location cannot be configured; never treat them as job artifacts or delivery paths.

Record `workspaceRoot`, `jobDir`, and the fixed subdirectories in `run.json`. Give every tool an explicit input and output path rooted in the job directory. Before delivery, run `scripts/init_job.py --check` and stop if the layout no longer matches.

Always exclude `<workspaceRoot>/jobs` when scanning. This prevents previous jobs, temporary files, rendered videos, and copied source assets from becoming input when a selected material directory contains the workspace.

## First-class material

- Images: PNG, JPEG, WebP, GIF.
- Documents: PDF, DOCX, PPTX, TXT, Markdown, HTML.
- Existing media: WAV, MP3, M4A, MP4, MOV, WebM.

Treat other types as unsupported without failing the entire scan. Do not automatically unpack archives or execute macros, scripts, HTML, or embedded document objects.

## Ordering and grouping

Use natural numeric order within a folder. Prefer an explicitly named cover before numbered pages. Directory structure is a grouping hint. Detect multiple topics from content before combining them.

Record exact duplicates by SHA-256 and use one copy. Treat names such as `改`, `新版`, `final`, `终稿`, `old`, `旧版`, and `X` as variant warnings, not automatic precedence rules. Ask when choosing a variant would change content.

## Material quantity

- Use `summary` when a short selection can preserve the central thesis.
- Use `complete` only when every necessary point can remain understandable at a readable pace.
- Recommend `series` when one video would require rushed narration or unreadable page timing.

Do not promise that every page will appear or remain readable in a fast short video. Record whether each selected source is on-screen evidence, identity-bearing media, supporting-only context, or omitted after extraction.

## Safety and privacy

- Do not modify, rename, or delete source files.
- Do not follow symlinks outside the selected roots.
- Do not expose absolute paths in public reports.
- Do not upload source content to any service except the explicitly configured TTS text endpoint when narration is enabled.
- In `hybrid`, do not paste or upload private local content to search, browser, or research services unless the user explicitly authorizes that disclosure.
