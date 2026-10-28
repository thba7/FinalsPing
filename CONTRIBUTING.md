# Contributing to FinalsPing

Contributions and forks are welcome, including improvements to match detection, performance, UI, region classification, and measurement accuracy.

## Workflow

1. Fork the repository and create a branch for your change.
2. Keep changes focused, readable, and compatible with Windows without Npcap.
3. Build locally with `build.bat` and test before opening a pull request.
4. Describe what changed, why, and what was tested. Include relevant Windows/version information for bug fixes.

## Reporting issues

Please include your Windows version, FinalsPing release version, expected behavior, and actual behavior. **Do not publish packet captures, personal IP addresses, credentials, or private logs** in public issues. Sanitize any diagnostic output first.

## Measurement changes

Distinguish measured RTT from estimates, explain assumptions, and avoid presenting a heuristic as an authoritative in-game ping. Keep the no-extra-driver distribution goal intact unless a change explicitly proposes otherwise.

By submitting a contribution, you agree that it can be distributed under the project's MIT License.
