# Technical single-point videos

Use this reference when `editorialMode` is `technical-single-point`. The episode must prove one engineering proposition, not survey a topic.

## 1. Scope one proposition

Choose one claim that can be demonstrated as a state change, causal mechanism, implementation behavior, failure, or measurable comparison. Supporting definitions may clarify it, but they must not become parallel lessons.

Use this arc when the evidence supports it:

`observable symptom or result -> internal mechanism -> proof in motion -> boundary -> concise resolution`

Prefer 20-40 seconds and 4-6 beats. Duration follows comprehension and narration; do not pad a narrow point or accelerate a dense proof.

## 2. Require a mechanism contract

Record in `CONTENT_MODEL.json`:

- one `propositionId` pointing to the only `core` claim;
- `inputState`, `transformation`, and `outputState`;
- a relationship ID that supports the transformation;
- one or more proof objects;
- at least one limitation ID as the boundary.

A definition, architecture overview, or product list is not a mechanism. The viewer must be able to identify what changed and why.

## 3. Use proof objects

Allowed proof-object kinds are `trace`, `code`, `json`, `terminal`, `state-machine`, `metric`, `error-repair`, and `runtime-ui`.

Set authenticity to:

- `real`: captured from an actual run or source artifact;
- `source-derived`: reconstructed from sourced behavior without changing factual fields;
- `labeled-simulation`: conceptual behavior that is visibly labeled as simulated.

Never use random code, fake logs, decorative HUDs, code rain, or meaningless telemetry as a technical texture. Every visible field must participate in the explained mechanism. Preserve exact product names, commands, field names, errors, versions, units, and conditions.

## 4. Direct one state change

Choose one technical visual mode: `trace-demo`, `code-to-runtime`, `state-machine`, `before-after-run`, `request-response`, `error-repair`, `metric-comparison`, or `system-zoom`.

Make the focal scene carry the proof object and strongest transformation. Supporting scenes establish context or hold the boundary. Keep code, JSON, metrics, and terminal text stable while the viewer reads them; animate selection, flow, and state rather than continuously moving the reading surface.

## 5. Use semantic color

Declare stable tokens for `neutral`, `request`, `result`, `warning`, `error`, and `focus`. A token follows the same semantic object across scenes. Change color only when state changes, such as a blue request becoming a green verified result. Red is reserved for error, rejection, or destructive risk; amber is reserved for pending, uncertainty, cost, or permission.

Do not default to neon blue-purple, arbitrary gradients, glass panels, glowing chips, or decorative grids. Technical credibility comes from meaningful state and legible structure.

## 6. Make transitions causal

Use one primary transition family for most boundaries and at most two accents. For every boundary after the opening, declare either:

- `continuous`: the outgoing anchor, incoming anchor, motion direction, audio bridge, and narrative purpose; or
- `deliberate-break`: a break reason, audio bridge, and narrative purpose.

Prefer object handoffs: a JSON field becomes a node, a trace cursor enters the next span, a return value travels back to context, or a function name matches its runtime state. Use a hard cut for error, contradiction, interruption, or a deliberate cognitive reset.

## 7. Review credibility

In addition to layout checks, confirm:

- the proposition remains singular after watching the full sequence;
- the proof object is readable at phone scale and its authenticity is clear;
- before, transformation, and after states are all visible;
- every transition preserves an anchor or declares a meaningful break;
- color roles remain stable across the sequence;
- the boundary is visible and not hidden in narration only;
- the mechanism remains understandable with sound muted;
- narration and event sounds remain coherent without looking at the screen.
