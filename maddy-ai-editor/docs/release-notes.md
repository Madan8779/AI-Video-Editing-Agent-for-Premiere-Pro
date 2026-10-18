# Maddy AI Video Editor development preview

First Windows implementation of the October 2026 build brief. The requested
installer filename is retained, but this artifact is a development preview.

Implemented: PySide6 desktop, first-run wizard, settings and prerequisite status,
video import, persistent cancellable job queue, FFmpeg metadata/silence/scenes,
conservative preset cut plans, editable range table and JSON, source/retained-range
playback preview, offline model adapter, retimed SRT, integer-rate CMX3600 EDL,
authenticated loopback bridge, and thirteen scoped stdio MCP tools.

Real speech testing found a faster-whisper/PyAV 19 incompatibility. The dependency
lock pins PyAV 18.1.0; no global monkey-patch is used. Models are not downloaded
or uploaded automatically. No cloud credentials are required for baseline analysis.

The UXP source adapter uses documented project/sequence inspection methods.
Real-host verification, CCX packaging, duplicate-sequence timeline edits and
export automation are pending. Disabled operations return explicit capability
errors; they never claim success. EDL import/relink accuracy is not yet certified
in Premiere. Caption quality in Kannada, very long media, update/uninstall on a
clean Windows VM, signatures and release compliance review remain open gates.

The installer does not include Premiere, speech models or the external FFmpeg
tools. Qt playback and PyAV include their own multimedia libraries; see notices.
