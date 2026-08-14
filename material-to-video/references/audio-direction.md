# Audio direction

Use this reference when creating `AUDIO_PLAN.json`, especially for `technical-single-point`.

## Hierarchy

Keep narration primary. Use music as a restrained bed only when its provenance is recorded. Use event sounds to express system behavior, not every visual movement. Intentional silence is a valid event.

Bind cues to meaningful events:

- request send: short outward transient;
- result return: complementary inward response;
- schema or component assembly: restrained sequential clicks;
- validation pass: compact lock or confirmation;
- permission block: low, dry interruption;
- error: discontinuity or brief removal of the bed;
- key conclusion: musical phrase landing, not a sound on every cut.

Avoid repeated whooshes, impacts on every edit, alarms, decorative typing sounds, and SFX that mask speech.

## Bridges

Declare one bridge for every adjacent scene pair:

- `j-cut`: the next scene's sound begins before its image;
- `l-cut`: the previous scene's sound continues after the visual cut;
- `continuous-bed`: ambience or music preserves continuity;
- `silence-cut`: sound intentionally drops to mark interruption;
- `none`: an explicit dry cut whose purpose is documented.

Keep bridge durations proportionate to the event. Do not force a fixed offset across the whole video.

## Provenance and mix

Set music to `none`, `licensed`, `generated`, or `user-supplied`. Record a provenance ID for every non-`none` music source. Set event sources to `licensed`, `generated`, `user-supplied`, or `synthesized`; record a provenance ID unless the cue is synthesized directly in the composition.

Review at phone-speaker level and with headphones. Confirm clear narration, no masked technical terms, no clipping, and no large perceived-loudness jumps across scene boundaries.
