---
name: meaning-led-photo-poster
description: Create standalone premium editorial posters from uploaded photos using CLI GPT Image 2 reference-image editing, with 3:4 format, exact 50/50 top-photo and bottom-reinterpretation layout, preserved real subjects, fine-line doodle people, and sparse witty copy.
---

# Meaning-Led Photo Poster

## Workflow

1. Create one output per uploaded image; never combine unrelated uploads.
2. For identifiable people, obtain explicit authorization before sending each new sensitive image to the configured external endpoint.
3. Use CLI GPT Image 2: `bun /Users/irenezhu/.codex/skills/baoyu-image-gen/scripts/main.ts --provider openai --model gpt-image-2 --prompt "..." --ref SOURCE --image OUTPUT --ar 3:4 --size 1200x1600 --quality 2k`.
4. Verify output exists, is non-empty, readable, and visually inspected before reporting success.
5. On failure or visibly wrong output, report it and stop. Never substitute local line drawings or claim completion without a real generated file.

## Prompt Template

```text
Create one single premium 3:4 vertical editorial poster from the attached photo, with an exact horizontal 50/50 split.
TOP HALF: preserve [identity, pose, key objects, environment, lighting and texture] as realistic photography; subtle magazine color grading only; never warp, replace, redesign, or add people.
BOTTOM HALF: keep [most important real subject/material] recognizable with believable detail on warm off-white background and generous negative space. Reinterpret [theme/action/relationship/emotion]. Add 4-6 context-driven tiny black fine-line doodle people whose actions respond to the subject. Use source-derived colors [palette]. Add sparse short handwritten copy [exact text]. No large headline, logos, watermark, collage, borders, excessive text, malformed faces/hands, or abstract line-art replacement of the real subject.
```

## Quality Gates

- 3:4 aspect ratio and exact 50/50 split.
- Top retains identity, pose, structure, and photographic realism.
- Bottom retains recognizable real subject/material cues; doodles remain secondary.
- Output path is verified before returning a clickable link.

See [prompt-examples.md](references/prompt-examples.md).
