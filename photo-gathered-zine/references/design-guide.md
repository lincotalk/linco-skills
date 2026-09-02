# Design Guide

Use this reference when compiling the final image prompt or diagnosing a weak output.

## Scene Reading

- **Anchor:** one or two subjects that identify the photograph.
- **Invariant:** horizon, overlap, facing direction, path, scale, or silhouette that must survive.
- **Gesture:** the strongest diagonal, curve, vertical, gaze, or convergence.
- **Weight:** where darkness, texture, faces, saturation, or isolation pull attention.
- **Quiet region:** sky, water, wall, haze, or ground that can become breathing room.
- **Shared shape:** one source form that can cross photography, illustration, and color.

## Density Targets

- Let the illustration influence about 45–70% of the canvas while leaving most of that field blank.
- Keep active illustrated marks around 15–35% of the whole poster.
- For foliage or intricate organic scenes, omit roughly 85–95% of individual leaves, twigs, or repeated marks; keep active illustration closer to 10–25%.
- Use one dominant mass, one or two supporting marks, and no more than two neutral ink values besides paper and the accent hue.

## Structural Color

Choose one vivid hue through analogous intensification, near-complement, warm–cool contrast, or intensification of a meaningful minor source color.

Make the accent do at least two jobs: derive from a source contour or rhythm; touch or cross the photo boundary; redirect the eye; rebalance weight; clarify figure and ground; or emphasize a real subject.

- Opaque cut-paper or replacement: 2–6% of the poster.
- Translucent underprint: 8–20%.
- Directional repeated marks: sparse and visibly tied to a source path.

## Torn Edge

Describe an irregular hand-ripped contour with shallow notches, uneven rises, occasional longer fibers, a narrow warm-paper fringe, and selective pigment loss. Make it readable along 35–70% of the visible photo perimeter. Keep the active fiber band around 1–4% of the short edge. Do not apply the same tear equally around all sides.

## Prompt Template

```text
Use case: stylized-concept.
Asset type: vertical 3:5 editorial paper-collage poster.
Input image: Image 1 is the truthful photographic anchor and edit target.
Scene invariants: [subjects and spatial relationships to preserve].
Composition: [layout], photography about [range], spacious [paper tone] field, eye path follows [gesture].
Abstraction: use [one grammar]; retain [forms], merge [repetition], omit [detail], transform [source shape], expose blank paper around and inside forms.
Structural color: exact [vivid hue], derived from [source shape], [crosses/touches/replaces/passes behind] the photo boundary to [visual function].
Material handoff: visible asymmetric hand-torn contour, narrow exposed fibers, warm paper fringe, slight selective abrasion, flat scan with no lifted depth.
Texture: tactile paper fibers, restrained dry ink or halftone, subtle scan grain, flat lighting.
Text (verbatim): "[exact text]" or no text.
Avoid: clean rectangular mask, sticker outline, uniform deckled frame, drop shadow, curled paper, dense tracing, extra accent hues, generic decorative marks, watermark, mockup frame.
```

## Review Checklist

- Is the original scene recognizable without explanation?
- Is the illustration a large field rather than a small decorative echo?
- Is intricate detail substantially quieter than in the photograph?
- Does blank paper separate visual ideas?
- Is the accent hue visibly derived from the source and doing compositional work?
- Is the torn boundary legible, fibrous, asymmetric, and flat?
- Does the poster remain clear at thumbnail size?

Regenerate or make one focused revision when any answer is no.
