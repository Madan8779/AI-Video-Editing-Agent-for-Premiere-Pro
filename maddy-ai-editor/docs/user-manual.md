# User manual

Start `MaddyAIEditor.exe` or run `python -m apps.desktop.main` from the source folder.
Open Settings and choose trusted ffmpeg.exe and ffprobe.exe files from an FFmpeg
Windows build. The header shows prerequisites. Premiere is optional for analysis.

Import a video and choose Car Review, Travel Vlog, Educational Video or Shorts.
These presets change silence padding; they do not yet make semantic creative
decisions. Analyze runs metadata, silence and scene detection locally. Cancel
stops the worker without changing the source. Check Activity for failures.
Use Job queue to add several videos and run them sequentially. Completed plans
are saved under the settings folder. Double-click a complete job to reopen its
plan. Select an interrupted, failed or cancelled job and Retry selected to queue
it again. A cancelled job stops automatic queue advancement.

Review retained source ranges in Cut review. In/out values are seconds. Edit the
table or JSON plan and select Validate plan. Save JSON for lossless plan storage.
Export EDL produces CMX3600 for integer-rate sources only. Import that EDL into
a new disposable Premiere project, relink the source and verify timecodes/audio
before relying on the result. Premiere EDL import has not yet been certified here.

For offline transcription, the adapter is included in this development build.
Obtain a licensed CTranslate2-compatible
faster-whisper model separately and select its folder in Settings. Choose English,
Kannada or Auto detect and enable transcription before analysis. No model or
media is uploaded automatically. Save SRT exports captions retimed to the current
reviewed retained ranges. If a cue straddles a cut, its text is repeated across the
surviving portions; review those cues manually. Human language QA is required.

For UXP development, install Adobe UXP Developer Tool through Creative Cloud,
enable Premiere Developer Mode in Plugins preferences, add the companion manifest
and load it. Choose Connect Premiere in the desktop app, copy the session key,
open Maddy Companion in Premiere and paste it. The panel reports project and
sequence names. An expired/disconnected session clears connected status.
This source panel is not a packaged CCX or verified timeline editing integration.

Apply and automated export remain disabled. Use Premiere's own export dialog
for completed edits. Background music, transitions, cloud transcription and
autonomous publishing are outside this build's enabled capabilities.

The installer supports per-user uninstall through Windows Installed apps. User
settings live under `%LOCALAPPDATA%/MaddyAIEditor` and are retained for reinstall.
Remove that folder manually after uninstall if you want to remove preferences.
Source files and separately saved edit plans/captions are never removed.
