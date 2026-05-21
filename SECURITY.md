# Security Policy

## Supported Versions

Security fixes are made against the current `main` branch and the latest
published release.

## Reporting A Vulnerability

Please report security issues privately by opening a GitHub security advisory
for this repository or by contacting the maintainers through the publisher
profile at https://github.com/workersio.

Do not open a public issue for a vulnerability until the maintainers have had a
reasonable chance to investigate and prepare a fix.

## Scope

`@workersio/skills` is a skill and plugin package for coding agents. The
highest-risk areas are:

- Hook behavior.
- Agent instructions that could cause unsafe file or command handling.
- Packaging metadata that installs unexpected files.
- Documentation that encourages leaking secrets into prompts, logs, comments, or test fixtures.

`@workersio/skills` should never require production credentials in examples,
tests, workloads, or issue reports.
