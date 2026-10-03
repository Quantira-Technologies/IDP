"""API-surface tests: health, auth/RBAC enforcement, analytics, and workflows."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import rbac
from app.main import app

client = TestClient(app)


def _login(username: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health_is_open_and_reports_flags():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["auth_enabled"] is True
    assert set(body["workflows"]) >= {"customs", "po2pay", "contracts", "finance"}


def test_login_success_and_permissions():
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["role"] == "platform_admin"
    assert "access_control.manage" in user["permissions"]


def test_login_bad_credentials():
    assert client.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401


def test_protected_endpoint_requires_token():
    assert client.post("/api/demo/customs").status_code == 401
    token = _login("admin", "Admin@123")
    assert client.post("/api/demo/customs", headers=_auth(token)).status_code == 200


def test_officer_cannot_view_access_control():
    token = _login("officer", "Officer@123")
    assert client.get("/api/rbac", headers=_auth(token)).status_code == 403


def test_admin_can_read_and_update_rbac():
    token = _login("admin", "Admin@123")
    r = client.get("/api/rbac", headers=_auth(token))
    assert r.status_code == 200
    assert {m["id"] for m in r.json()["modules"]} >= {"dashboard", "access_control"}

    original = sorted(rbac.permissions_for_role("customs_officer"))
    try:
        updated = client.put(
            "/api/rbac/roles/customs_officer/permissions",
            headers=_auth(token),
            json={"permissions": original + ["analytics.analyze"]},
        )
        assert updated.status_code == 200
        assert "analytics.analyze" in updated.json()["permissions"]
    finally:
        client.put(
            "/api/rbac/roles/customs_officer/permissions",
            headers=_auth(token),
            json={"permissions": original},
        )


def test_system_role_cannot_lose_access_control():
    token = _login("admin", "Admin@123")
    original = sorted(rbac.permissions_for_role("platform_admin"))
    try:
        r = client.put(
            "/api/rbac/roles/platform_admin/permissions",
            headers=_auth(token),
            json={"permissions": ["dashboard.view"]},
        )
        assert r.status_code == 200
        assert "access_control.manage" in r.json()["permissions"]
    finally:
        client.put(
            "/api/rbac/roles/platform_admin/permissions",
            headers=_auth(token),
            json={"permissions": original},
        )


def test_analytics_overview_and_analyze_gating():
    admin = _login("admin", "Admin@123")
    assert client.get("/api/analytics/overview", headers=_auth(admin)).status_code == 200

    officer = _login("officer", "Officer@123")
    assert client.get("/api/analytics/overview", headers=_auth(officer)).status_code == 200
    assert client.post("/api/analytics/analyze", headers=_auth(officer)).status_code == 403


def test_sso_signin_returns_token():
    r = client.post("/api/auth/sso", json={"role": "manager"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "manager"


def test_unknown_workflow_returns_404():
    token = _login("admin", "Admin@123")
    assert client.post("/api/demo/nope", headers=_auth(token)).status_code == 404
