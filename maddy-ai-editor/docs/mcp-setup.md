# MCP development setup

The source MCP process uses stdio and the same locked Python environment. It is
not installed as a separately runnable MCP executable in this desktop preview.
Configure an MCP-capable client with the absolute `.venv/Scripts/python.exe` as
its command, `mcp/server.py` as its argument, and the app directory as `cwd`.

Set MADDY_MEDIA_ROOTS to explicitly chosen media folders separated by the Windows
path separator `;`. No folder is permitted by default. Set MADDY_FFMPEG and
MADDY_FFPROBE to trusted executables, and optionally MADDY_MODEL to an existing
local CTranslate2 model folder. For Premiere observations, launch the desktop,
connect its companion, and supply the current session key as MADDY_SESSION_TOKEN
in the MCP client's private environment. Do not commit a key in configuration.
Restarting the desktop invalidates that session key.

Example read-only workflow: list_capabilities, health_check, probe_media on an
allowlisted video, analyze_media, create_edit_plan using a named preset,
validate_edit_plan and preview_edit_plan. The preview result is a time mapping;
the desktop provides actual playback. get_active_project and get_active_sequence
return only live UXP observations. Disconnected sessions return no stale names.

State-changing tools require desktop-issued approval scoped to a digest and
operation. This preview does not issue approvals for unverified timeline/export
operations, and the service keeps both capabilities disabled. No tool can mint
approval tokens, execute a shell command, or change the configured allowlist.
