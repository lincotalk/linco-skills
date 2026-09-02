---
name: journey-sticker-card
description: Turn a user-supplied travel, street, pet, family, landscape, or daily-life photo into a horizontal collectible paper sticker card. Use when the user asks to make a photo into a 3:2 memory card, travel postcard, sticker card, journal card, zine-like souvenir card, or quiet editorial keepsake with a main illustrated scene, six source-derived stickers, and three short English keywords.
---

# Journey Sticker Card

Create one finished bitmap image from one source photo. The output should feel like a quiet printed travel keepsake: selective memory, tactile paper, simple shapes, and a few sticker-like fragments pulled from the original scene.

## Workflow

1. Inspect the photo and identify the memory center: what the viewer should remember first.
2. Choose one identification anchor that makes the result clearly traceable to the source photo.
3. Decide whether any visible source text is essential to the location. Default to no retained text.
4. Choose exactly six sticker motifs from visible source elements.
5. Choose exactly three concise English keywords.
6. Read [references/style-recipe.md](references/style-recipe.md), then generate the image with an image generation or image editing tool.
7. Save the final image locally when possible, then report the saved path, anchor, stickers, and keywords.

## Card Rules

- Use one horizontal `3:2` canvas.
- Use warm off-white textured paper as the base, with a continuous outer margin.
- Make the left side the main image area, roughly two thirds of the card.
- Keep the main illustration unframed. Do not add an inner card, border, mat, shadow box, or title block.
- Put exactly three English keywords once beneath the main illustration, separated by centered dots.
- Place exactly six die-cut sticker motifs in a right-side column, with uneven sizes and relaxed spacing.
- Give each sticker a warm-white cut-paper edge and a subtle flat shadow.
- Do not add titles, captions, dates, postal marks, watermarks, signatures, or extra readable text.

## Source Handling

Preserve recognition through simplified structure, not photo collage. Rebuild the whole image in one visual medium. Never leave a photorealistic patch inside the final card.

Retain source text only when it is a genuine place anchor, such as a landmark name or station sign. Remove or abstract generic signs, ads, prices, license plates, timestamps, labels, and accidental text.

## Prompt Pattern

Use this structure when generating:

```text
Create one horizontal 3:2 collectible paper sticker card from the supplied photo.
Use warm off-white textured paper with a calm outer margin.

Main memory anchor: [one sentence naming the exact source-derived scene].

Left side: one large unframed matte gouache / cut-paper / risograph-like illustration.
Right side: exactly six separate die-cut stickers: [six motifs].
Footer keywords: [KEYWORD ONE] · [KEYWORD TWO] · [KEYWORD THREE].

Preserve the original scene through silhouette, spacing, color relationships, and the most memorable objects.
Rebuild everything as broad hand-cut matte color shapes with fine paper grain.
Use the source palette, simplified into 5-8 color families.
Keep the first read simple, quiet, and spacious.

No photorealistic patches. No extra readable text. No watermark. No signature.
No glossy 3D, anime, polished vector style, heavy gradients, watercolor wash, or decorative filler.
```

## Quality Check

Before delivering, verify:

- The card is horizontal `3:2`.
- The source photo is recognizable at a glance.
- The image reads first as large shapes and quiet space, not busy detail.
- The right column has exactly six stickers.
- The footer has exactly three English keywords.
- There is no unwanted readable text, watermark, signature, or photo patch.
