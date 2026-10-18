"""Run as a script, not `python -m mcp.server` (which names the SDK package).

stdio transport only. Paths are configured by the local user, never by an agent tool.
"""
import os
import sys
from pathlib import Path

# Remove the script's mcp directory so it cannot shadow the installed SDK.
sys.path[0] = str(Path(__file__).resolve().parents[1])
import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from services.agent.models import EditPlan, Preset, create_plan
from services.agent.security import PathPolicy
from services.agent.bridge import capabilities
from services.media.engine import MediaEngine
from services.media.transcription import transcribe_local


def build_server(roots=None, engine=None, token=None, model=None):
    roots = roots if roots is not None else [p for p in os.getenv("MADDY_MEDIA_ROOTS", "").split(os.pathsep) if p]
    policy = PathPolicy(roots)
    engine = engine or MediaEngine(os.getenv("MADDY_FFMPEG", ""), os.getenv("MADDY_FFPROBE", ""))
    token = token if token is not None else os.getenv("MADDY_SESSION_TOKEN", "")
    model = model or os.getenv("MADDY_MODEL", "")
    server = FastMCP("Maddy AI Video Editor")
    readonly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)

    def bridge(method, route, payload=None):
        if not token:
            return {"error": "DESKTOP_SESSION_REQUIRED", "connected": False}
        with httpx.Client(base_url="http://127.0.0.1:8765", timeout=8, trust_env=False,
                          headers={"Authorization": "Bearer " + token}) as client:
            try:
                result = client.request(method, route, json=payload)
                result.raise_for_status()
                return result.json()
            except httpx.HTTPStatusError as exc:
                return {"error": "BRIDGE_REJECTED", "status": exc.response.status_code}
            except httpx.RequestError:
                return {"error": "DESKTOP_UNAVAILABLE", "connected": False}

    @server.tool(annotations=readonly)
    def list_capabilities() -> dict:
        """List available and explicitly gated operations."""
        return capabilities()

    @server.tool(annotations=readonly)
    def health_check() -> dict:
        """Report local tools; never imply Premiere is connected."""
        return {"status": "ok", "tools": engine.tools(), "allowed_roots": len(policy.roots)}

    @server.tool(annotations=readonly)
    def probe_media(path: str) -> dict:
        """Inspect allowlisted local video metadata without modifying its source."""
        return engine.probe(policy.check(path)).model_dump()

    @server.tool(annotations=readonly)
    def analyze_media(path: str) -> dict:
        """Detect silence and scene boundaries locally."""
        info = engine.probe(policy.check(path))
        silences, scenes = engine.analyze(info)
        return {"media": info.model_dump(), "silences": [s.model_dump() for s in silences], "scenes": scenes}

    @server.tool(annotations=readonly)
    def transcribe_media(path: str, language: str = "en") -> dict:
        """Transcribe locally using the user's configured existing model only."""
        if language not in ("en", "kn", "auto"):
            raise ValueError("Select en, kn, or auto")
        source = policy.check(path)
        if not model:
            return {"error": "LOCAL_MODEL_REQUIRED"}
        return {"segments": [s.model_dump() for s in transcribe_local(source, model, language)]}

    @server.tool(annotations=readonly)
    def get_premiere_connection() -> dict:
        """Get live UXP heartbeat status, with stale observations removed."""
        return bridge("GET", "/premiere")

    @server.tool(annotations=readonly)
    def get_active_project() -> dict:
        """Read the active project name reported by the UXP adapter."""
        state = get_premiere_connection()
        return {"project": (state.get("inspection") or {}).get("project_name"), "connected": state.get("connected", False)}

    @server.tool(annotations=readonly)
    def get_active_sequence() -> dict:
        """Read the active sequence name reported by the UXP adapter."""
        state = get_premiere_connection()
        return {"sequence": (state.get("inspection") or {}).get("sequence_name"), "connected": state.get("connected", False)}

    @server.tool(name="create_edit_plan", annotations=readonly)
    def make_plan(path: str, preset: Preset = Preset.CAR) -> dict:
        """Analyze an allowlisted source and propose conservative retained ranges."""
        info = engine.probe(policy.check(path))
        silences, _ = engine.analyze(info)
        return create_plan(info, silences, preset).model_dump()

    def checked_plan(plan):
        info = engine.probe(policy.check(plan.source_path))
        if abs(plan.source_duration - info.duration) > 0.001 or abs(plan.fps - info.fps) > 0.001:
            raise ValueError("Plan metadata does not match source")
        return plan

    @server.tool(annotations=readonly)
    def validate_edit_plan(plan: EditPlan) -> dict:
        """Validate ranges, paths, and source metadata."""
        checked_plan(plan)
        return {"valid": True, "digest": plan.digest()}

    @server.tool(annotations=readonly)
    def preview_edit_plan(plan: EditPlan) -> dict:
        """Return a source-to-output mapping for review; no timeline changes."""
        checked_plan(plan)
        cursor, ranges = 0.0, []
        for cut in plan.keeps:
            ranges.append({"source_in": cut.start, "source_out": cut.end,
                           "output_in": cursor, "output_out": cursor + cut.end - cut.start})
            cursor += cut.end - cut.start
        return {"duration": cursor, "ranges": ranges, "rendered_preview": False}

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def apply_approved_edit_plan(plan: EditPlan, approval_token: str) -> dict:
        """Requires a scoped desktop approval; currently disabled pending host QA."""
        checked_plan(plan)
        return bridge("POST", "/plans/apply", {"plan": plan.model_dump(), "approval_token": approval_token})

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def request_export(plan: EditPlan, approval_token: str) -> dict:
        """Requires desktop approval; use Premiere's manual export until host QA passes."""
        checked_plan(plan)
        return bridge("POST", "/export", {"plan": plan.model_dump(), "approval_token": approval_token})

    return server


if __name__ == "__main__":
    build_server().run(transport="stdio")
