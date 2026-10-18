# Capability and version matrix

Environment checked on 2026-10-18. Installed Premiere binary reports 26.5.2.
Python 3.12.10 x64 was installed from a PSF Authenticode-verified installer.
Node is 24.18.0. Exact Python packages are frozen in `requirements.lock`.

| Component | Tested version | Role |
|---|---|---|
| Windows | 11, build 26200 x64 | Build and development smoke host |
| Python | 3.12.10 x64 | Pinned runtime |
| PySide6 | 6.12.0 | Desktop, accessibility, multimedia preview |
| FastAPI / Uvicorn | 0.143.5 / 0.54.0 | Authenticated loopback bridge |
| Pydantic | 2.14.1 | Strict shared schemas |
| MCP Python SDK | 1.30.0 | stdio tools |
| FFmpeg / ffprobe | 9.0.2 essentials | External local development tools |
| faster-whisper / PyAV | 1.2.1 / 18.1.0 | Offline transcription; compatible dependency pin |
| CTranslate2 | 4.8.3 | CPU int8 inference |
| PyInstaller / Inno Setup | 6.22.3 / 6.7.3 | Windows EXE and installer |
| Premiere Pro | 26.5.2 installed binary | UXP real-host QA pending |
| UXP Developer Tool | Not found in installed-app inventory | Blocks CCX packaging and plugin host validation |

| Capability | Implementation | Validation gate |
|---|---|---|
| Desktop import, settings, progress, cancellation, editable plan | PySide6 | Automated UI and real Windows smoke test |
| Metadata, silence and scene detection | External ffprobe/FFmpeg | Generated video, Unicode path, source checksum test |
| Offline speech in English/Kannada | Optional faster-whisper adapter | Model installation and human language review pending |
| JSON plan and SRT | Strict Pydantic, source-to-output retiming | Range, overlap, Unicode and timing tests |
| EDL interchange | CMX3600 integer fps | Serialization tests; actual Premiere import pending |
| Active project | `Project.getActiveProject()`, `project.name` | Documented since 25.6; real-host test pending |
| Active sequence | `project.getActiveSequence()`, `sequence.name` | Documented since 25.6; real-host test pending |
| Duplicate sequence and timeline edits | Disabled | Actual version-specific capability, backup and recovery tests required |
| Premiere export automation | Disabled | Exact API and host verification required |
| MCP | SDK 1.x stdio | Tool schemas, allowlist and no arbitrary-shell contract tests |
| Windows executable/installer | PyInstaller + Inno Setup | Build and install/uninstall evidence recorded in QA report |
| CCX | Source panel only until Adobe packaging | UXP Developer Tool, plugin ID and real-host tests required |

Official documentation reviewed:

- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/project/
- https://developer.adobe.com/premiere-pro/uxp/ppro-reference/classes/sequence/
- https://developer.adobe.com/premiere-pro/uxp/plugins/concepts/manifest/
- https://developer.adobe.com/premiere-pro/uxp/plugins/distribution/install/
- https://github.com/modelcontextprotocol/python-sdk/tree/v1.x
- https://pyinstaller.org/en/stable/usage.html
- https://jrsoftware.org/isinfo.php
- https://ffmpeg.org/download.html

Adobe documents Creative Cloud and UPIA installation for CCX. This app does not
silently install plugins or change Developer Mode. Developer loading requires
Adobe UXP Developer Tool. Host license status is not inferred from binary presence.
