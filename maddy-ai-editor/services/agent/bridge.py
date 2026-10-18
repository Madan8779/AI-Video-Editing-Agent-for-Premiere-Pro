import secrets
import threading
import time
import uuid
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import Field
from services.agent.models import StrictModel, EditPlan
from services.agent.security import PathPolicy, ApprovalStore
from services.media.engine import MediaEngine


class Inspection(StrictModel):
    plugin_version: str = Field(max_length=32)
    project_name: Optional[str] = Field(default=None, max_length=1000)
    sequence_name: Optional[str] = Field(default=None, max_length=1000)
    host_version: str = Field(default="unreported", max_length=100)


class PathRequest(StrictModel):
    path: str = Field(max_length=32768)


class ApprovedPlan(StrictModel):
    plan: EditPlan
    approval_token: str = Field(min_length=20, max_length=200)


class BridgeState:
    def __init__(self, engine=None, roots=()):
        self.token = secrets.token_urlsafe(32)
        self.engine = engine or MediaEngine()
        self.policy = PathPolicy(roots)
        self.approvals = ApprovalStore()
        self._inspection = None
        self._seen = 0
        self._lock = threading.Lock()

    def receive(self, payload):
        with self._lock:
            self._inspection = payload.model_dump()
            self._seen = time.monotonic()

    def connection(self):
        with self._lock:
            connected = self._inspection is not None and time.monotonic() - self._seen < 12
            return {"connected": connected,
                    "inspection": self._inspection if connected else None,
                    "timeline_editing": False, "export_automation": False}


def capabilities():
    return {"probe_media": True, "analyze_media": True, "create_edit_plan": True,
            "validate_edit_plan": True, "preview_edit_plan": True,
            "transcribe_media": "optional local model and faster-whisper required",
            "get_premiere_connection": True, "get_active_project": "requires UXP heartbeat",
            "get_active_sequence": "requires UXP heartbeat", "apply_approved_edit_plan": False,
            "request_export": False, "edl_interchange": "integer fps; manual import verification required"}


def create_app(state):
    app = FastAPI(title="Maddy local bridge", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        request_id = str(uuid.uuid4())
        if request.headers.get("host") not in ("127.0.0.1:8765", "127.0.0.1", "testserver"):
            return JSONResponse({"error": "HOST_DENIED", "request_id": request_id}, 403)
        origin = request.headers.get("origin")
        if origin and origin != "http://127.0.0.1:8765":
            return JSONResponse({"error": "ORIGIN_DENIED", "request_id": request_id}, 403)
        expected = "Bearer " + state.token
        if not secrets.compare_digest(request.headers.get("authorization", ""), expected):
            return JSONResponse({"error": "UNAUTHENTICATED", "request_id": request_id}, 401)
        # Limit actual bytes, including clients omitting or lying about Content-Length.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 1024 * 1024:
                return JSONResponse({"error": "REQUEST_TOO_LARGE", "request_id": request_id}, 413)
        request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(PermissionError)
    async def denied(request, exc):
        return JSONResponse({"error": str(exc).split(":")[0]}, 403)

    @app.exception_handler(FileNotFoundError)
    async def missing(request, exc):
        return JSONResponse({"error": "FILE_OR_TOOL_MISSING"}, 422)

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "tools": state.engine.tools()}

    @app.get("/capabilities")
    def list_capabilities():
        return capabilities()

    @app.get("/premiere")
    def premiere():
        return state.connection()

    @app.post("/premiere/heartbeat")
    def heartbeat(payload: Inspection):
        state.receive(payload)
        return {"received": True, "writes_enabled": False}

    @app.post("/media/probe")
    def probe(payload: PathRequest):
        path = state.policy.check(payload.path)
        return state.engine.probe(path).model_dump()

    @app.post("/plans/validate")
    def validate(plan: EditPlan):
        state.policy.check(plan.source_path)
        return {"valid": True, "digest": plan.digest(), "duration": plan.output_duration}

    @app.post("/plans/apply")
    def apply(payload: ApprovedPlan):
        state.policy.check(payload.plan.source_path)
        state.approvals.consume(payload.approval_token, "apply", payload.plan.digest())
        return JSONResponse({"error": "UNVERIFIED_PREMIERE_CAPABILITY",
                             "alternative": "Save reviewed JSON or CMX3600 EDL"}, 409)

    @app.post("/export")
    def export(payload: ApprovedPlan):
        state.policy.check(payload.plan.source_path)
        state.approvals.consume(payload.approval_token, "export", payload.plan.digest())
        return JSONResponse({"error": "UNVERIFIED_EXPORT_CAPABILITY",
                             "alternative": "Use Premiere File > Export > Media"}, 409)

    return app
