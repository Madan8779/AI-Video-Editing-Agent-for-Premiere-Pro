# Maddy AI Video Editor

Windows desktop editing assistant built from the October 18, 2026 brief in `VE agent`.
This is the UXP successor application; the parent CEP project remains separate.

## Run

Use Python 3.12 x64. From this directory:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m apps.desktop.main
```

`scripts\bootstrap.ps1` creates the environment. `scripts\test.ps1` runs checks.
`scripts\build.ps1` creates a Windows one-folder executable and, when Inno Setup
is installed, `dist/MaddyAIEditor_Setup_v1.0.exe`.

Select a video, choose a preset, and analyze. Review the suggested kept ranges and
editable JSON. Save the plan or export a CMX3600 EDL for manual interchange.
FFmpeg and ffprobe are user-supplied command-line tools, configured in Settings;
they are not redistributed. Offline transcription requires a separately obtained
local faster-whisper model. The adapter is included. No cloud upload occurs.

Premiere project inspection uses the companion UXP panel and an authenticated
loopback bridge. Editing/export automation stays disabled until actual Premiere
capability and recovery tests pass. No installer or CCX should be described as
release-verified until the gates in `docs/acceptance-tests.md` pass.

See `docs/user-manual.md`, `docs/capability-matrix.md`, and `docs/qa-report.md`.
Source MCP client configuration is described in `docs/mcp-setup.md`.
