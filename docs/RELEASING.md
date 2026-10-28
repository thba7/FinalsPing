# Publishing a FinalsPing release

A Windows runner builds the release EXE; no local Windows build machine is required for publishing.

## First-time repository setup

1. Create a **public** GitHub repository named `FinalsPing`.
2. Upload the files in this project directory to the repository root.
3. In GitHub **Settings → Actions → General**, ensure GitHub Actions is enabled and the workflow has permission to create releases (the workflow requests `contents: write`).
4. Review the source, license, README, and release workflow before publishing.

## Publish a version

From a local clone with Git installed:

```bash
git add .
git commit -m "Release FinalsPing v1.0.0"
git tag v1.0.0
git push origin main
git push origin v1.0.0
```

The workflow runs on the tag, builds `FinalsPing.exe` on `windows-latest`, and uploads the EXE to the associated GitHub Release. A release is created automatically if one does not exist.

Alternatively, create a tag called `v1.0.0` through GitHub's Releases interface. The tag push triggers the same workflow.

## Validation before announcing

- Download the EXE from the GitHub Release and launch it on Windows.
- Verify the administrator UAC prompt, tray icon/menu, overlay controls, and match state transitions.
- Test direct QLKN (EU/NA) and at least one fallback region if possible.
- Confirm `Details` shows region and city only, and `Colors` defaults to on.
- Confirm an application exit leaves no running processes.

Do not describe a release as tested until the downloaded artifact has been exercised on Windows.
