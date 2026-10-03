"""Tests for the new modules: business rules, subscription, folders/scans, guide, geo."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _login(u: str, p: str) -> dict:
    r = client.post("/api/auth/login", json={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_business_rules_view_vs_manage():
    officer = _login("officer", "Officer@123")
    assert client.get("/api/business-rules", headers=officer).status_code == 200
    # Officer can view but not change rules.
    cfg = client.get("/api/business-rules", headers=officer).json()
    assert client.put("/api/business-rules", headers=officer, json=cfg).status_code == 403

    tenant = _login("tenantadmin", "Tenant@123")
    r = client.put("/api/business-rules", headers=tenant, json=cfg)
    assert r.status_code == 200


def test_subscription_and_targets():
    tenant = _login("tenantadmin", "Tenant@123")
    assert client.get("/api/subscription", headers=tenant).status_code == 200
    officer = _login("officer", "Officer@123")
    assert client.get("/api/subscription", headers=officer).status_code == 403
    # Everyone who can view documents can see export targets.
    assert client.get("/api/subscription/targets", headers=officer).status_code == 200


def test_folders_and_scan_ownership():
    officer = _login("officer", "Officer@123")
    f = client.post("/api/folders", headers=officer, json={"name": "Shipment A"})
    assert f.status_code == 200
    fid = f.json()["id"]
    assert any(x["id"] == fid for x in client.get("/api/folders", headers=officer).json())

    # Process a document -> it becomes the officer's scan.
    scan = client.post("/api/assets/2.png", headers=officer)
    assert scan.status_code == 200
    doc_id = scan.json()["id"]
    mine = client.get("/api/scans", headers=officer).json()
    assert any(s["id"] == doc_id for s in mine)

    # Move to folder, then delete folder (scan survives, moves up).
    assert client.put(f"/api/scans/{doc_id}/folder", headers=officer, json={"folder_id": fid}).status_code == 200
    assert client.delete(f"/api/folders/{fid}", headers=officer).status_code == 200
    assert client.delete(f"/api/scans/{doc_id}", headers=officer).status_code == 200


def test_scans_are_private_per_user():
    officer = _login("officer", "Officer@123")
    scan = client.post("/api/assets/2.png", headers=officer)
    doc_id = scan.json()["id"]
    # A different user cannot fetch it.
    manager = _login("manager", "Manager@123")
    assert client.get(f"/api/documents/{doc_id}", headers=manager).status_code == 404
    client.delete(f"/api/scans/{doc_id}", headers=officer)


def test_user_guide_is_role_filtered():
    officer = _login("officer", "Officer@123")
    g = client.get("/api/guide", headers=officer).json()
    assert g["can_edit"] is False
    ids = {s["id"] for s in g["sections"]}
    assert "getting-started" in ids  # public section
    assert "access-control" not in ids  # officer lacks access_control.view

    tenant = _login("tenantadmin", "Tenant@123")
    gt = client.get("/api/guide", headers=tenant).json()
    assert gt["can_edit"] is True


def test_geo_analytics():
    officer = _login("officer", "Officer@123")
    r = client.get("/api/analytics/geo", headers=officer)
    assert r.status_code == 200
    assert len(r.json()["by_origin"]) > 0
    # Officer lacks analytics.analyze.
    assert client.post("/api/analytics/geo/analyze", headers=officer).status_code == 403
