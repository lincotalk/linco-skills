# Cover policy

Use this reference when planning, composing, reviewing, or delivering cover images. Keep `videoCanvas`, delivery cover variants, and display-crop previews separate.

## Specification status

Treat `cover.specRevision` in the job config as a versioned production baseline, not a permanent platform promise. Record one `verificationMode` in `COVER_PLAN.json`:

- `preset-fallback`: default when no current uploader requirement was supplied. Use the versioned config exactly and explain the fallback in `verificationNote`.
- `user-supplied`: use when the user provides a current platform requirement or screenshot. Record the evidence in `verificationNote` and override only the job config.
- `runtime-verified`: use only when the user explicitly authorizes checking the current uploader and its visible requirement was verified. Record the date and observed requirement.

Do not browse, sign in, or open a publishing surface merely to validate a cover. This skill does not publish.

## Platform contract

- **Douyin:** produce both `douyin-vertical` at 3:4 and `douyin-horizontal` at 4:3. Recompose hierarchy and subject placement for each orientation.
- **Xiaohongshu:** produce one 3:4 `xiaohongshu-primary` cover. The 9:16 video canvas remains a separate asset.
- **WeChat Channels:** public guidance and display behavior vary by entry point. For the default 9:16 vertical video, produce a matching vertical master and a centered 6:7 feed preview. Treat the preview as review evidence, not a second delivery cover, unless current supplied requirements say otherwise.
- **Universal:** produce the union of the three platform contracts. Share art direction, not one bitmap.

Use exact IDs, dimensions, and output paths from `material-to-video.config.json`. Do not duplicate mutable pixel specifications elsewhere in job artifacts.

## Authored-cover rules

- Design the cover as an independent reading surface. Do not submit an unmodified video frame or random timeline snapshot.
- Make the literal subject or product name visible. State one concrete viewer value or thesis; avoid vague hooks. Link the title to valid `CONTENT_MODEL.json` IDs so it cannot introduce an unsupported claim.
- Limit the title to `cover.maxTitleLines`. Remove subtitles, progress bars, page numbers, captions, production metadata, and instructional copy.
- Use the same verified primary CJK family as `VISUAL_PLAN.json`. Ordinary Latin words and numbers stay in that family; monospace remains limited to genuine code.
- Keep the subject, title, brand mark, and key number inside each variant's `criticalArea`. Maintain at least `cover.minSafeMarginPx` on every side.
- Preserve contrast and hierarchy at phone-thumbnail size. Do not rely on fine strokes, dense labels, or low-contrast photography.
- Use the same content claim across platform variants, but recompose it for each aspect ratio. Do not stretch or mechanically crop text.

## Review and delivery

Create `COVER_PLAN.json` before composing covers. Store delivery covers in `final/` and crop previews in `review/`. Generate a phone-scale cover contact sheet in `review/cover-contact-sheet.png`.

Review every variant for text wrapping, font fallback, subject cropping, edge safety, and consistency with the video. Review every declared preview for crop loss. A delivery cover must be a non-empty PNG or JPEG with the exact planned dimensions.

Run `validate_cover_plan.py` once before composition and again with `--check-files` before delivery. Do not deliver an unplanned `cover.png`.
