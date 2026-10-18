import time
import pytest
from fastapi.testclient import TestClient
from services.agent.security import PathPolicy, ApprovalStore
from services.agent.bridge import BridgeState, Inspection, create_app
from services.agent.models import create_plan, Preset


def test_allowlist_rejects_parent_and_sibling(tmp_path):
    root = tmp_path / "media"
    root.mkdir()
    inside = root / "a.mp4"
    inside.touch()
    outside = tmp_path / "secret.mp4"
    outside.touch()
    policy = PathPolicy([root])
    assert policy.check(inside) == inside.resolve()
    with pytest.raises(PermissionError):
        policy.check(root / ".." / outside.name)
    with pytest.raises(ValueError):
        policy.check(root)


def test_approval_expiry_scope_and_replay():
    store = ApprovalStore()
    token = store.issue("apply", "abc")
    store.consume(token, "apply", "abc")
    with pytest.raises(PermissionError):
        store.consume(token, "apply", "abc")
    token = store.issue("apply", "abc")
    with pytest.raises(PermissionError):
        store.consume(token, "export", "abc")
    token = store.issue("apply", "abc", ttl=-1)
    with pytest.raises(PermissionError):
        store.consume(token, "apply", "abc")


def test_bridge_auth_origin_host_payload_and_schema(tmp_path):
    state = BridgeState(roots=[tmp_path])
    with TestClient(create_app(state)) as client:
        assert client.get("/health").status_code == 401
        headers = {"Authorization": "Bearer " + state.token}
        assert client.get("/health", headers=headers).status_code == 200
        assert client.get("/health", headers={**headers, "Origin": "https://evil.example"}).status_code == 403
        assert client.get("/health", headers={**headers, "Host": "evil.example"}).status_code == 403
        assert client.post("/premiere/heartbeat", headers=headers, json={"shell": "whoami"}).status_code == 422
        assert client.post("/plans/validate", headers=headers, content=b"x" * (1024 * 1024 + 1)).status_code == 413
        assert client.get("/health", headers=headers).headers["X-Request-ID"]
        assert client.get("/capabilities", headers=headers).json()["apply_approved_edit_plan"] is False


def test_disconnected_state_hides_stale_inspection():
    state = BridgeState()
    state.receive(Inspection(plugin_version="0.1.0", project_name="Test"))
    assert state.connection()["connected"]
    state._seen -= 20
    assert not state.connection()["connected"]
    assert state.connection()["inspection"] is None


def test_approved_writes_still_blocked_until_host_verification(tmp_path, media_info):
    source = tmp_path / "a.mp4"
    source.touch()
    info = media_info.model_copy(update={"path": str(source)})
    plan = create_plan(info, [], Preset.CAR)
    state = BridgeState(roots=[tmp_path])
    with TestClient(create_app(state)) as client:
        headers = {"Authorization": "Bearer " + state.token}
        body = {"plan": plan.model_dump(), "approval_token": "x" * 32}
        assert client.post("/plans/apply", headers=headers, json=body).status_code == 403
        body["approval_token"] = state.approvals.issue("apply", plan.digest())
        assert client.post("/plans/apply", headers=headers, json=body).status_code == 409
        assert client.post("/plans/apply", headers=headers, json=body).status_code == 403
