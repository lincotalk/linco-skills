# HyperFrames handoff

This skill owns local and researched source intake, content modeling, and editorial preparation. HyperFrames owns composition construction, animation runtime, preview, checks, and rendering.

## Required handoff

Initialize `<job-dir>/project` with HyperFrames before writing plan files. Put `BRIEF.md`, `STORYBOARD.md`, and `SCRIPT.md` at that project root. Keep `CONTENT_MODEL.json`, `VISUAL_PLAN.json`, and other material-to-video records at the job root and reference them from the brief using project-relative paths. Require `AUDIO_PLAN.json` when `editorialMode` is `technical-single-point`.

Set the brief workflow to `general-video`. Include the canonical HyperFrames fields `flow`, `storyboard`, `message`, `destination`, `aspect`, `language`, `audience`, and `length`, plus the platform preset, intake mode, editorial mode, coverage strategy, source mode, narration file, caption policy, approval mode, and job-root planning paths. Persist the derived interaction `mode` in storyboard frontmatter. Treat the normalized content model as the composition contract regardless of whether its source IDs came from local materials, researched sources, or both.

Set the working directory to `<job-dir>/project` and invoke the installed `hyperframes` entry skill. Because `BRIEF.md` exists at the project root, resume from project state and do not repeat its fresh-creation intent interview.

Use HyperFrames domain skills as routed by the entry skill:

- `hyperframes-core` for composition structure and deterministic timing.
- `hyperframes-creative` for typography, beats, and platform-aware visual direction.
- `hyperframes-animation` for a small set of seek-safe motion patterns.
- `media-use` for captions, transcription, audio operations, and media records.
- `hyperframes-cli` for initialization, checks, snapshots, preview, render, and diagnostics.

## Source-mode implementation

### Editorial recut

Build scenes from `contentIds`. Reconstruct central information with large typography, diagrams, comparisons, process flows, graphic primitives, icons, or clearly labeled simulations. Original files may appear as selective evidence, product identity, or contextual texture, but they do not define the layout.

Do not import every source page into the composition. Copy only source assets used for evidence or identity. Preserve claim-to-source traceability in project artifacts even when the source does not appear on screen.

### Faithful

Keep the original artifact as the evidence. For dense material, use `overview -> contextual detail or magnifier -> overview/context`. Do not hold a reduced full page and expect viewers to read it. Do not redraw legal wording, measured results, or product states as if the reconstruction were original evidence.

### Visual remix

Preserve selected identity-bearing photography, product renders, brand colors, logos, or distinctive graphic elements. Rebuild explanatory text and structure for mobile viewing. Do not let inherited brand assets reduce contrast or readability.

## Visual direction

Read [visual-quality.md](visual-quality.md) and treat `VISUAL_PLAN.json` as the visual timing contract.

- Make the first viewport name the subject and express the central thesis.
- Follow the declared typography, color logic, graphic language, and motion grammar.
- Implement the declared `fontPolicy`. Load one verified CJK family before layout measurement and keep ordinary Latin text, numbers, labels, and captions in that family. Use monospace only for declared code-like scopes.
- Use the representation that best fits each scene's cognitive job.
- Give one focal scene a stronger authored sequence; keep supporting scenes quieter.
- Keep primary reading text and captions above the configured size floors.
- Do not repeat one family or transition more than twice consecutively without a recorded exception.
- Give every scene a semantic subject beat within the configured hold limit.
- Remove decorative metadata, counters, and visual effects that do not improve comprehension or traceability.

### Technical single-point handoff

Read [technical-single-point.md](technical-single-point.md) and [audio-direction.md](audio-direction.md). Implement the declared proof object, not a decorative approximation. Preserve exact technical fields and visibly label simulations. Make the focal scene show the mechanism state change. Follow semantic color tokens across scene boundaries and implement each declared transition anchor or deliberate break. Bind sound cues to system events and match every `AUDIO_PLAN.json` bridge to `transitionContinuity.audioBridge`.

## Cover handoff

Read [cover-policy.md](cover-policy.md) and treat `COVER_PLAN.json` as an independent still-image contract. Build one static composition at each declared delivery size; do not capture a random video frame or stretch one platform bitmap into another aspect ratio. Use the same verified font family and material-backed content IDs as the video.

For Douyin, compose the vertical and horizontal covers separately. For Xiaohongshu, keep the 3:4 cover independent from the 9:16 video canvas. For WeChat Channels, render every declared display preview from the planned master and check that critical content survives the crop. Store delivery images in `final/`, previews and the cover contact sheet in `review/`, then run `validate_cover_plan.py --check-files`.

## Clarity checks

Inspect the opening frame, focal scene, densest scene, and every evidence scene at phone scale. Confirm:

- primary points are readable without zooming;
- captions fit in one or two lines inside platform safe areas;
- no dense source page is used as the primary reading surface;
- evidence crops retain enough context;
- simulations and generated illustrations are not presented as real source evidence;
- inactive or background layers do not lower contrast or compete with the focal point.

### Temporal containment audit

Do not rely on `hyperframes check` sampling alone. It can miss a short-lived expanded state. Give every strict parent a stable `data-containment="strict"` marker and `data-container-id` matching `VISUAL_PLAN.json`. Mark approved overflow with `data-overflow="intentional"`; leave every other child unmarked.

At every declared `reviewMoment`, seek deterministically, wait for fonts and the current frame to settle, capture a screenshot, and inspect live DOM rectangles. Fail when a non-exempt descendant crosses a strict parent's border box by more than `visualQuality.containmentTolerancePx`. Also fail on clipped text, ellipsis that hides required meaning, caption/critical-content intersection, platform-safe-area violations, or a font-load/fallback mismatch. Hidden inactive scenes may be ignored only when they are outside their active interval.

Write `LAYOUT_REVIEW.json` from [layout-review.template.json](../assets/layout-review.template.json) with the scene ID, phase, exact time, screenshot path, checked container IDs, font result, and every violation. The template is intentionally incomplete until real screenshots and every declared review moment are recorded. For `technical-single-point`, also capture one midpoint frame for every scene boundary and complete `technicalReview` plus `transitionChecks`. An empty screenshot or a global contact sheet does not satisfy a declared moment. A visual fix is complete only after the same moment is recaptured and the violation is absent. Run `scripts/validate_layout_review.py` before preview approval.

Export or inspect at full 1080x1920 resolution before final render. Encoding quality cannot recover text that was composed too small.

## Gates

1. Storyboard approval before composition, unless autonomous completion was explicit.
2. `validate_content_model.py` with the manifests required by `intakeMode`, and `validate_visual_plan.py`, pass after narration timing is locked and again after source retiming.
3. For `technical-single-point`, `validate_audio_plan.py` passes and the proof object, state change, boundary, color roles, transition anchors, muted comprehension, and audio-only continuity are reviewed.
4. `hyperframes check` passes before final preview.
5. Capture all declared entrance, development, hold, and exit moments at phone scale. Run the temporal containment audit and review the sequence as a contact sheet so repeated layouts remain visible.
6. `LAYOUT_REVIEW.json` exists and contains no unresolved containment, clipping, caption overlap, safe-area, blank-frame, or font violation.
7. Use one batched correction pass and at most one confirmation pass. Do not continue subjective polishing after the confirmation pass unless a concrete defect remains.
8. Final composition preview approval before high-quality render, unless direct render was explicit.
9. Render a high-quality master before delivery; prefer CRF 14 or an equivalent visually lossless-quality setting when the renderer exposes the option.
10. Verify the rendered MP4 independently with the bundled verification script.

## Resilient render loop

- Treat an optional skill refresh or CLI upgrade as advisory. Attempt it once; when the network is unavailable, record the warning and continue with the installed version after `hyperframes info` or `doctor` and the required composition checks pass.
- Start only one high-quality render. Preserve its session ID, output path, frame total, and last observed frame in `run.json` or the task log.
- Poll a live render about every 30 seconds. Lack of new output for one poll is not failure; inspect the process after roughly 120 seconds without progress.
- After a tool, terminal, or service restart, poll the original session first. If the session is gone, check the exact output path and validate the artifact before rerendering.
- Restart rendering only when the original process has ended unsuccessfully and the expected MP4 is absent or fails verification. Never start a duplicate render merely because a poll timed out.

Static animation maps can report collision or offscreen elements from inactive stacked scene layers. Classify this as a false positive only when the flagged elements are outside their active time range and runtime, layout, motion, transition snapshots, and rendered-frame checks all pass. Otherwise fix the composition.

Never publish or upload the result.
