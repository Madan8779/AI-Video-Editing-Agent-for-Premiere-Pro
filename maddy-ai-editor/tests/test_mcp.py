import asyncio
import os
import sys
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_stdio_handshake_tools_and_path_denial(tmp_path):
    root = Path(__file__).resolve().parents[1]
    async def check():
        parameters = StdioServerParameters(command=sys.executable,
            args=[str(root / "mcp" / "server.py")], cwd=str(root),
            env={**os.environ, "MADDY_MEDIA_ROOTS": str(tmp_path)})
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as session:
                await session.initialize()
                result = await session.list_tools()
                names = {tool.name for tool in result.tools}
                assert names == {"list_capabilities", "health_check", "probe_media", "analyze_media",
                    "transcribe_media", "get_premiere_connection", "get_active_project",
                    "get_active_sequence", "create_edit_plan", "validate_edit_plan", "preview_edit_plan",
                    "apply_approved_edit_plan", "request_export"}
                health = await session.call_tool("health_check", {})
                assert not health.isError
                # Existence is checked before allowlist; use a real outside file.
                denied = await session.call_tool("probe_media", {"path": str(root / "README.md")})
                assert denied.isError
                malformed = await session.call_tool("validate_edit_plan", {"plan": {"shell": "whoami"}})
                assert malformed.isError
                capabilities = await session.call_tool("list_capabilities", {})
                assert not capabilities.isError
    asyncio.run(check())
