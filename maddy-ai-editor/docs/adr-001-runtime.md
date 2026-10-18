# ADR 001 Runtime and integration boundary

Accepted: Python 3.12 x64, PySide6, FastAPI, Pydantic and stdio MCP. Retain the
existing CEP source while building the requested UXP application in a separate
subdirectory. Share Python contracts between the GUI, media workers and MCP.
Use external FFmpeg binaries initially to avoid silently creating redistribution
obligations. Require explicitly selected existing transcription models.

Rejected: treating old ExtendScript tools or desktop mouse automation as verified
UXP timeline support. A capability flag stays false until actual-host QA proves it.

The app has one cancellable active job, a persisted multi-job queue, integrated
playback and a first-run wizard. Interrupted jobs require explicit retry; they
are never automatically marked complete or resumed as partial results.

faster-whisper 1.2.1 with PyAV 19 failed a real speech test because metadata_errors
was removed by PyAV. Pin PyAV 18.1.0 in requirements.lock until a verified
faster-whisper release supports newer PyAV. Upstream evidence:
https://github.com/SYSTRAN/faster-whisper/issues/1589
