# Editorial policy

## Truth and presentation

Treat selected evidence as the factual authority, not as a mandatory source sequence or visual template. Link every narration beat and visible factual statement to content IDs in `CONTENT_MODEL.json`; link every factual content item to source IDs in `MATERIALS.json`, `RESEARCH_SOURCES.json`, or both. Filenames, search rankings, and snippets are not evidence. Do not add current facts, statistics, quotes, product states, or recommendations that the selected sources do not support.

Choose one source mode:

- `editorial-recut`: default for articles, social cards, notes, and documents. Preserve meaning and attribution while replacing weak or unreadable source presentation with authored mobile-first visuals.
- `faithful`: use when the original artifact is itself the evidence, including product UI, reports, contracts, comparisons, demonstrations, or an explicit user request for faithful display.
- `visual-remix`: use when photographs, brand assets, product renders, or a distinctive visual language should remain recognizable while explanatory content is reconstructed.

Do not ask for permission to use `editorial-recut` when the fit is clear. Ask only when reconstruction could change legal, evidentiary, or brand meaning. In every mode, distinguish source-backed facts from editorial framing.

## Audience value

Make the video useful to the intended viewer, not merely complete relative to an input folder or search result set.

- State one `viewerNeed` and one concrete `promisedTakeaway` in `CONTENT_MODEL.json`.
- Give each scene one viewer question, one cognitive job, and one dominant takeaway.
- Prefer explanations that help viewers understand, compare, decide, or apply something.
- Preserve necessary definitions, mechanisms, conditions, limitations, and examples. Do not reduce the material to slogans.
- Omit repetition, decoration, and source-order transitions that add no understanding.
- Split into a series when enough useful content cannot remain legible and comprehensible in one video.

Use this default information arc when supported:

`subject and thesis -> why it matters -> key concepts -> mechanism or relationship -> evidence or example -> limitation or condition -> usable summary`

For `technical-single-point`, replace the broad arc with `observable symptom or result -> internal mechanism -> proof in motion -> boundary -> concise resolution`. Keep exactly one core claim; supporting content may explain that claim but may not introduce a second lesson. Read [technical-single-point.md](technical-single-point.md).

Open with the subject and a concrete thesis. Do not manufacture conflict, suspense, personal discovery, or exaggerated stakes. The opening frame must communicate what the video is about before relying on narration.

## Content model

Build `CONTENT_MODEL.json` before storyboarding. Extract only source-supported items:

- `claims`: factual propositions and conclusions.
- `definitions`: terms viewers need in order to follow the explanation.
- `relationships`: supported sequences, causes, dependencies, comparisons, or part-whole structures.
- `examples`: concrete cases that make an abstract point understandable.
- `limitations`: conditions, caveats, uncertainty, or boundaries.

Give every item a stable ID and at least one `sourceId`. Keep wording atomic enough that a scene can reference it without importing unrelated claims. If sources conflict, preserve the conflict in the appropriate source manifest and stop for user direction when it changes the thesis.

Storyboard scenes by content ID, not by image number. A scene may combine several compatible content items when they support one cognitive job. Do not combine unrelated facts merely to increase pacing.

## Coverage strategy

Choose coverage independently from source mode:

- `summary`: preserve the central thesis and highest-value support.
- `complete`: explain every necessary point, not necessarily every page.
- `series`: split excessive density or multiple topics into coherent episodes.

Do not promise that every supplied page or researched source will appear. Record omitted and supporting-only sources in `MATERIALS.json` or `RESEARCH_SOURCES.json` selection decisions.

## Narration style

Record one style in `BRIEF.md` and `material-to-video.config.json`:

- `objective-explainer`: default. Explain the product or topic directly with neutral, concise, information-first language for an AI technology audience.
- `conversational`: use only when explicitly requested; allow natural spoken transitions without adding personal experience, rhetorical questions, or unsupported opinions.

Narration should state facts, explain relationships, and clarify technical terms instead of reading visible text verbatim. Avoid invented first-person framing, rhetorical questions, exaggerated benefits, commands such as "you must", and influencer filler.

Keep provenance in review artifacts, not in audience-facing copy. Do not narrate or display production-language phrases such as "素材中的原始说法", "根据用户提供的素材", "根据网上资料", or "根据检索结果" merely to prove traceability. State the supported fact directly. Make provenance visible only when its identity or status changes how the viewer should interpret the claim, such as a named report, an attributed quote, conflicting evidence, material uncertainty, or a legal/evidentiary distinction. In those cases, name the meaningful source or uncertainty directly; do not refer generically to "the material" or "online research".

Before locking the storyboard or script, run `scripts/validate_audience_copy.py` on both artifacts. Treat a match as an error to rewrite, not as wording to soften. This lint is intentionally narrow; also review semantically equivalent production commentary that a phrase matcher cannot catch.

Preserve every English product name, model name, API, library, framework, acronym, command, and version token exactly in Latin characters in both `SCRIPT.md` and TTS input. Do not translate or transliterate it unless a selected source uses an official Chinese name and the user explicitly chooses it. Adjust punctuation or spacing for pronunciation without changing the token.

Show the selected narration style with the storyboard. Treat narration wording and voice performance as separate approvals: storyboard approval locks the text direction, while voice-sample approval locks the speaker and delivery. Use the real generated WAV duration as timing truth. Do not force a target duration with unnatural TTS speed.

## Visual evidence

Use original media when it materially proves or demonstrates a claim. Establish enough context to make the evidence credible, then direct attention to the relevant region. Do not use a screenshot as decoration when an authored explanation would be clearer.

For researched web sources, factual citation and media reuse are separate decisions. Do not place a page image, photograph, logo, chart, or clip into the video unless its reuse status is cleared and recorded. A generated or independently licensed explanatory visual may represent a sourced fact without pretending to be source evidence.

In `editorial-recut`, authored typography, diagrams, process flows, comparisons, UI simulations, icons, graphic primitives, and generated illustrations may carry the explanation. They must not introduce unsupported states, metrics, labels, or causal relationships. Label simulations or conceptual illustrations when viewers could mistake them for real source evidence.

In `faithful`, do not redraw legal wording, measured results, quoted text, or product states as if the reconstruction were the original. Use selective crops only with surrounding context before or after the detail.

## Timing and motion

Set timing from narration and comprehension load, not seconds per image. If a dense source cannot be read, reconstruct the important content, select a supported focus region, extend the hold, or move the point to another episode. Do not accelerate page changes until text becomes decorative noise.

Read [visual-quality.md](visual-quality.md) before visual planning. Use two to four motion materials across the piece, but vary their composition and narrative job. Motion must explain hierarchy, sequence, continuity, comparison, or transformation. Never continuously move dense text while viewers need to read it.

## Audio

Default to no background music for the cross-platform master unless the user supplies licensed audio or explicitly approves a reusable source. Duck approved music under narration. Do not use platform music catalogs in a universal baked master.
