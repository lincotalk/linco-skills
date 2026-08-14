---
workflow: general-video
flow: companion
storyboard: yes
message: "State the one source-supported idea the video must communicate"
destination: xiaohongshu
aspect: 1080x1920
language: zh-CN
audience: AI technology viewers
length: auto
platform: xiaohongshu
intake_mode: provided-materials
editorial_mode: general-explainer
coverage_strategy: summary
source_mode: editorial-recut
narration_style: objective-explainer
---

## Intent

Explain one material-supported thesis as a legible narrated vertical video.

## Assets

- `public/assets/source/` - selected local evidence copied from the job manifest.
- `../CONTENT_MODEL.json` - normalized claims and source traceability.
- `../VISUAL_PLAN.json` - scene-level visual and review contract.
- `../COVER_PLAN.json` - platform cover contract.
- `../audio/narration.wav` - approved narration, when enabled.

## Customizations

- Burn in Chinese captions after aligning them to the approved narration.

## Notes

- Keep all factual statements traceable to the job-root source records.
- Render only after the final HyperFrames preview is approved.
