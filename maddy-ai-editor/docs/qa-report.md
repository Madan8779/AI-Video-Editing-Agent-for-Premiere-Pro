# Verification report

Date: 2026-10-18. Host: Windows 11 build 26200, x64. Installed Premiere binary:
26.5.2. Python: 3.12.10. Exact libraries: requirements.lock. PyInstaller 6.22.3;
Inno Setup 6.7.3. Git source is in the connected repository's maddy-ai-editor folder.

## Automated evidence

- `python -m pytest -q --junitxml=artifacts/test-results.xml`: **30 passed**, no skips,
  with real FFmpeg and an existing local model configured for fixture tests.
- `node --test tests/uxp.test.cjs`: **3 passed**. These are mocked Adobe-adapter
  contracts and manifest checks; they are not actual Premiere integration tests.
- `python -m pip_audit --format json --output artifacts/dependency-audit.json`:
  **no known vulnerabilities** in the final pinned Python environment.
- Source GUI smoke with an 8-second generated video completed analysis and
  proposed 5.5 seconds of retained footage. Screenshot visually inspected for
  clipping, labels, status, source ranges, and disabled Premiere operations.
- Initial real-speech failure: PyAV 19 rejected metadata_errors from faster-whisper.
  Fixed by compatible dependency pin. Generated Windows English speech then passed
  recognition assertions for actual spoken content using the local small model.

Coverage includes strict time ranges, overlap/out-of-bounds/NaN rejection,
retimed Unicode SRT, EDL rate gating, canonical path allowlists, auth/origin/host
rejection, oversized/malformed input, expiring one-use scoped approvals, stale
heartbeat removal, actual MCP stdio handshake and all thirteen tool names,
missing tools, corrupt files, process cancellation/timeouts, real silence,
actual scene boundary, audio-free video, Unicode media paths, unchanged source
SHA256, persisted queue interruption recovery, and two real threaded queue jobs.

## Build and installation

Windows one-folder executable and Inno Setup installer were compiled. A frozen
executable analyzed the generated video successfully with exit code 0; the
rendered interface was visually reviewed. The final frozen executable also
transcribed the generated speech video offline with exit code 0, returning four
timestamped English segments and the expected engine/cabin phrase. Speech-model
assets are explicitly included in the build. Isolated installation results are
recorded separately after execution. Raw build log is artifacts/build.log;
generated files are in dist.

## Open release gates

Adobe UXP Developer Tool was not found in the installed-app inventory. No CCX
was fabricated. No real Premiere project/sequence inspection, EDL import,
timeline edits, export operation, or original-project recovery is claimed tested.
Premiere/Creative Cloud license status was not inferred from binary presence.

Kannada speech quality has not received human review. Unicode caption formatting
is tested but is not evidence of language accuracy. Long-footage performance,
large/corrupt-file corpus, constrained disk, antivirus scan, code signing and clean
Windows VM install/update/uninstall are still required before a public release.
The dependency inventory and copied license texts support review; redistribution
sign-off and a standardized release SBOM remain pending.

## Reproduction

From the application directory, configure MADDY_FFMPEG and MADDY_FFPROBE to trusted
executables. Set MADDY_TEST_MODEL to an existing local faster-whisper model folder
and MADDY_TEST_SPEECH to the generated English WAV fixture to run all tests.
Without these variables the corresponding integration checks intentionally skip.

Run `scripts/bootstrap.ps1` with Python 3.12, `scripts/test.ps1`,
`node --test tests/uxp.test.cjs`, then `scripts/build.ps1 -InnoCompiler <ISCC.exe>`.
PowerShell script execution must be allowed for the current build process.
The source README and user manual describe launch and local tool configuration.

## Final isolated installer result

`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-installer.ps1`
passed on the existing Windows 11 development host. Installation returned 0,
the installed executable analyzed the generated video and returned 0, and
uninstall returned 0. The installed executable and HKCU uninstall registration
were confirmed removed. Existing installations were checked before testing to
avoid replacement. This is not a clean-VM, update, or public-release qualification.

Final installer SHA256:
`560150AC6604A6734CBEE4ADFEF2C34E47D939468E2BA72CD6E0641BDBDB05B1`

Evidence is retained in docs/evidence, including JUnit, UXP adapter tests,
dependency audit, a frozen-app screenshot, generated-speech transcription and
installer-verification.json. The packaged manual reflects the preview's known
limitations; this report records the subsequent installation result.
