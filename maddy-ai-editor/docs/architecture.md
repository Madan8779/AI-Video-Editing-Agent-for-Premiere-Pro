# Architecture

The requested product is a standalone Windows 11 x64 PySide6 application with
offline media processing and a separate Premiere UXP companion. Existing CEP
code in the parent repository is not used as a substitute for UXP capabilities.

The GUI owns user-selected folders, processing settings, cancellation, and
future operation approval. A QThread performs blocking media work. The local
FastAPI service runs on 127.0.0.1:8765 with a random per-launch bearer token.
The UXP panel reports active project/sequence observations through that service.
An independent stdio MCP process exposes the shared media contracts and calls
the authenticated bridge for Premiere observations. It cannot mint approvals.

`apps/desktop` contains the UI, `services/agent` contracts and security,
`services/media` bounded FFmpeg subprocess and optional local transcription,
`integrations/premiere_uxp` isolated Adobe adapter, `mcp` stdio entry point,
`tests` behavioral/security/media tests, `installer` Inno Setup, `scripts`
reproducible local workflows, `samples` generated fixtures, and `docs` evidence.

Media is read in place. JSON, EDL and caption files are separately saved by the
user. Edit plans carry source seconds, rationales, confidence, and an explicit
review strategy. Silence cuts are heuristics, not semantic quality judgments.
SRT is retimed to retained edit ranges. CMX3600 is limited to integer frame
rates; fractional-rate interchange remains JSON until verified alternatives exist.

Failure states are visible. A missing FFmpeg executable blocks analysis while
the GUI still runs. Missing Premiere blocks only connected features. Missing
local models does not fabricate transcripts. Disconnects expire after 12 seconds.
There are no automatic uploads, arbitrary command tools, or unattended project writes.

The first-run wizard introduces processing and Adobe prerequisites. A persistent
single-worker queue records queued/running/complete/failed/cancelled/interrupted
jobs, writes separate plan JSON files, and permits explicit retry. Completed jobs
can be reopened by double-clicking. Qt Multimedia provides source playback and a
preview that skips removed intervals. This is not a rendered video export and
may have decoder seeking latency.
