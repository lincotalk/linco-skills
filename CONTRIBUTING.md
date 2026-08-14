# Contributing

Contributions that improve reliability, platform compatibility, source traceability, media handling, or output quality are welcome.

## Development

Use Python 3.10 or newer. Keep bundled scripts dependency-free unless an optional dependency is clearly isolated and the no-dependency path remains safe. Do not add service credentials, private endpoints, copyrighted source material, generated job folders, or rendered media to the repository.

Before opening a pull request, run:

```bash
python -m compileall -q material-to-video
python -m unittest discover -s tests -v
```

When changing `SKILL.md`, keep the frontmatter trigger description accurate, keep the body below 500 lines, and place detailed or conditional policy in `references/`. When changing a validator or schema, update its example or template and add a regression test in the same pull request.

## Pull requests

Explain the user-visible behavior, compatibility impact, and verification performed. Keep changes scoped. A pull request that changes the HyperFrames, TTS, privacy, or filesystem boundary must include a negative test for the failure mode it prevents.

By submitting a contribution, you license it under the MIT License.
