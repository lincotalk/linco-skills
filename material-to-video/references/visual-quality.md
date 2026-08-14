# Visual quality contract

Use this reference when creating or revising `BRIEF.md`, `STORYBOARD.md`, `VISUAL_PLAN.json`, or a HyperFrames composition. The goal is useful, mobile-first explanation with factual traceability and visible editorial intent.

When `editorialMode` is `technical-single-point`, also read [technical-single-point.md](technical-single-point.md). Its proposition, proof-object, semantic-color, and transition-continuity requirements are additional hard constraints.

## 1. Define the visual direction

Write one concise `designRead`:

`Reading this as: <video type> for <audience>, using <visual language>, with <source role>.`

Record these fields in `VISUAL_PLAN.json` before scene treatments:

- `audienceThesis`: what the viewer should understand or be able to do after watching.
- `visualWorld`: the concrete visual environment, not a vague mood.
- `typography`: display and reading hierarchy, including Chinese and Latin treatment.
- `colorLogic`: semantic roles for background, text, emphasis, evidence, and warnings.
- `graphicLanguage`: the recurring shapes, lines, containers, or spatial metaphors.
- `motionGrammar`: how motion expresses hierarchy, sequence, comparison, or transformation.
- `openingFrame`: the subject and thesis visible in the first viewport.

For `technical-single-point`, also record `technicalVisualMode`, `proofObjectIds`, semantic `colorTokens`, one `transitionGrammar`, and a `transitionContinuity` contract for every scene.

Record a structured `fontPolicy` as well as the prose typography direction:

- Choose one primary CJK family for titles, body text, captions, ordinary Latin words, labels, and numbers.
- Set `source` to `bundled` when the font file is copied into the project, or `verified-system` only after confirming that the exact render environment has the family.
- Record `assetPath` for a bundled font and a deterministic fallback stack for unavailable glyphs.
- Use PingFang only when it is licensed and either bundled or verified in the actual render environment. Do not assume it exists on Windows or a cloud renderer.
- Restrict monospace to code, terminal output, or aligned tabular data. Product names, English terms, numerals, tags, and mixed Chinese headings use the primary family unless they are genuinely code.
- Load the font before measuring or animating text. Fail the preview when the browser reports a font-load error or rendered glyphs unexpectedly fall back to a visually different family.

Record 1-10 dials for `designVariance`, `motionIntensity`, and `visualDensity`. Use 5-7, 4-6, and 4-6 respectively for a typical technology explainer.

Define one subject-specific `motionThesis`. "Cards fade in" is not a thesis. Choose one `focalSceneId` and give it the strongest authored visual sequence; keep supporting scenes quieter.

## 2. Design for comprehension

Choose the representation that best serves each cognitive job:

- `kinetic-type`: one concise definition, distinction, or conclusion.
- `authored-diagram`: a relationship, system, hierarchy, or causal structure.
- `process-flow`: a supported sequence or workflow.
- `split-compare`: two supported states, options, or concepts.
- `simulated-ui`: a conceptual interface demonstration; label it when it is not source evidence.
- `selective-evidence`: a focused source crop with enough context to remain credible.
- `hero-artifact`: a product, photograph, or original artifact that deserves the frame.
- `montage`: several sourced examples in a short, structured sequence.
- `recap`: prior points resolving into a useful summary.

Do not choose a layout merely because it matches the source aspect ratio. Redesign replaces weak presentation while source attribution preserves truth.

Make one authored visual moment prove the central idea through a transformation, comparison, reveal, or spatial relationship. Do not spread equal visual intensity across every scene.

## 3. Protect readability

- Never use a dense full-page image as the primary reading surface.
- In `editorial-recut`, reconstruct important text at mobile scale. Use source images as evidence inserts, context, or texture only when useful.
- In `faithful`, establish the full artifact, show a stable contextual detail, then return or retain enough context to preserve evidentiary meaning.
- Keep primary body text at least `visualQuality.minPrimaryTextPx`; keep captions at least `visualQuality.minCaptionTextPx` in a 1080x1920 composition.
- Keep captions to one or two lines. Rephrase or retime instead of shrinking them.
- Prefer one dominant takeaway and at most one supporting cluster per scene.
- Hold readable states long enough for comprehension. A progress bar or moving background does not turn an unreadable page into useful content.
- Inspect at phone scale. If the viewer must pause and zoom to read a primary point, reconstruct it or split the scene.

## 4. Plan scene evidence and beats

Every scene in `VISUAL_PLAN.json` must reference `contentIds`, declare a `cognitiveJob`, and choose a `primaryReadingSurface` of `authored`, `source`, or `mixed`.

Give each scene timed beats with `atSec`, `durationSec`, `kind`, `actor`, `purpose`, and `motion`. Semantic subject kinds include `establish`, `focus`, `subject-motion`, `readable-hold`, `compare`, `transform`, and `recap`; `caption`, `progress`, and `ambient` do not count toward subject activity.

Give every scene four local `reviewMoments`: `entrance`, `development`, `hold`, and `exit`. Choose times that expose the most expanded or collision-prone state, not merely evenly spaced samples. Also declare `containment.mode`:

- Use `strict` when the scene contains cards, pills, chips, framed panels, evidence windows, or other bounded groups; list stable `containerIds` for every boundary that must contain its children.
- Use `unframed` only when no visible parent boundary implies containment.
- List an element in `intentionalOverflowIds` only when crossing its parent is part of the approved composition. Decorative or accidental overflow is never self-justifying.

- Keep the gap between semantic subject beats within `visualQuality.maxSubjectGapSeconds`.
- Treat a deliberate readable hold as a timed beat.
- Use entrance, development, and exit beats when a scene lasts longer than six seconds.
- Prefer exits faster than entrances. Use cuts or short transitions when continuity does not need explanation.
- Keep content IDs traceable to sources even when no original source image appears.

For videos longer than 45 seconds, use at least three layout families. Do not use one family or transition more than twice consecutively unless one narrow `qualityException` explains why comprehension requires it.

## 5. Avoid generic output

- Do not repeat the same header, counter, card frame, caption panel, and progress bar in every scene.
- Remove decorative issue numbers, build labels, metadata strips, and counters unless they aid navigation or traceability.
- Do not make every scene enter with the same fade, rise, and scale combination.
- Do not add perpetual floating, pulsing, shimmer, parallax, or glow as a substitute for explanation.
- Avoid generic AI visual signatures: arbitrary gradients, decorative grids, glowing chips, excessive glass panels, and unrelated futuristic imagery.
- Do not use a generated image when typography, a diagram, or real evidence communicates the point more precisely.
- Use icons as semantic shorthand, not decoration. Keep icon style consistent.

## 6. Review in bounded passes

Run the local content-model and visual-plan validators before composition and after retiming. Then use two visual-review passes at most:

1. Capture every declared `reviewMoment` plus representative transitions. At each moment, inspect the phone-scale frame and run the containment/overlap audit described in [hyperframes-workflow.md](hyperframes-workflow.md). Record screenshots and violations in `LAYOUT_REVIEW.json`, then fix all concrete defects in one batch.
2. Re-run the same moments and audit after fixes. Stop when every recorded violation is resolved and no concrete defect remains.

Review the opening frame, focal scene, and densest informational scene at full resolution. HyperFrames checks prove structural correctness; snapshots prove composition quality. Neither substitutes for the other.

## 7. Preflight

- The source mode and complete visual-direction contract are explicit.
- Every factual scene references valid content IDs.
- The first frame names the subject and communicates the thesis.
- Each scene has one viewer question, one cognitive job, and one dominant takeaway.
- No dense source page is the primary reading surface.
- Primary text and captions meet the configured size floor and safe area.
- One verified primary CJK family covers ordinary Chinese, Latin text, labels, and numbers; monospace appears only on code-like surfaces.
- A long video uses at least three layout families without mechanical repetition.
- Every scene has semantic subject beats within the configured gap.
- Every scene has four reviewed animation moments, and `LAYOUT_REVIEW.json` contains no unresolved containment, clipping, caption overlap, or safe-area violation.
- The sequence has one authored visual peak and quieter supporting scenes.
- A technical-single-point sequence proves one proposition with visible before, mechanism, after, and boundary states; its proof authenticity, color roles, and transition anchors remain clear.
- Simulations and conceptual illustrations cannot be mistaken for original evidence.
- The two-pass review ceiling was respected.
