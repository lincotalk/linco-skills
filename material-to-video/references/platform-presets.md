# Platform presets

Ask for a platform before editorial planning unless the request already states one. Record one of `douyin`, `xiaohongshu`, `wechat-channels`, or `universal` in `BRIEF.md`.

All video presets default to 1080x1920, 30 fps, H.264 video, AAC audio, burned-in captions, and no platform watermark. Video dimensions do not define cover dimensions. Read [cover-policy.md](cover-policy.md) and use the versioned `cover` block in the job config.

## Douyin

- Name the subject and central fact immediately; do not manufacture a dramatic hook.
- Use tighter pacing and stronger contrast between beats.
- Keep critical content away from the right interaction rail and lower UI region.
- Prefer large, concise captions over dense explanatory overlays.
- Deliver both the 3:4 vertical cover and the separately composed 4:3 horizontal cover. Do not derive one by blind center-cropping the other.

## Xiaohongshu

- Preserve the information value of 3:4 source cards; reconstruct their important points when the cards would be too small to read.
- Allow longer holds for genuine evidence, and use narration to explain relationships rather than duplicate visible text.
- Favor clear chapter progression, saves-worthy structure, and a useful cover.
- Keep essential content away from bottom descriptions and controls.
- Deliver one authored 3:4 primary cover. Keep the 9:16 video frame and the 3:4 cover as separate assets.

## WeChat Channels

- Use steady pacing, complete sentences, and conservative transitions.
- Favor legible subtitles and clear explanation over rapid novelty cuts.
- Keep the bottom interaction and description area clear.
- Do not equate the 6:7 feed display with one permanent upload-cover requirement. For the default 9:16 vertical job, deliver a 9:16 vertical cover master and validate a centered 6:7 feed preview. Use a supplied or explicitly runtime-verified uploader requirement when available.

## Universal

- Produce one file for all three platforms.
- Use the intersection of their safe areas and neutral pacing.
- Avoid platform-specific calls to action, UI imitations, music-library references, and watermarks.
- Treat platform-specific optimization as a separate future render, not part of this mode.
- Deliver the union of all platform cover variants and previews. A universal MP4 does not imply one universal cover.
