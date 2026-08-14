# Security Policy

## Reporting a vulnerability

Use GitHub private vulnerability reporting from the repository's **Security** tab. Do not open a public issue for vulnerabilities involving path traversal, credential exposure, private-material disclosure, cross-origin requests, or unsafe handling of untrusted documents.

Include the affected script or workflow stage, reproduction steps, expected and actual behavior, and the smallest non-sensitive test artifact that demonstrates the problem. Remove local absolute paths, bearer tokens, narration text, and private source content from reports.

## Scope

Security-sensitive boundaries include:

- local input roots, symlinks, manifests, and generated output paths;
- untrusted PDF, Office, HTML, image, audio, video, and web content;
- research privacy and prompt-injection handling;
- TTS endpoint validation, authentication, redirects, uploads, and logs;
- media licensing and accidental publication.

Only the latest release is supported with security fixes.
