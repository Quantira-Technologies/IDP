"""Auth, RBAC, users, analytics, scans, folders, rules, subscription & guide API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import analytics, auth, business_rules, rbac, subscription, user_guide
from .config import settings
from .db import store

router = APIRouter(prefix="/api")


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    username: str
    password: str


class SSORequest(BaseModel):
    role: str | None = None


@router.get("/auth/config")
def auth_config() -> dict:
    """Public info the login page needs (no secrets)."""
    return {
        "sso_enabled": settings.sso_enabled,
        "sso_provider_label": settings.sso_provider_label,
        "auth_enabled": settings.auth_enabled,
        "demo_users": [
            {"username": "admin", "role": "Platform Admin"},
            {"username": "tenantadmin", "role": "Tenant Admin"},
            {"username": "director", "role": "Director"},
            {"username": "manager", "role": "Manager"},
            {"username": "officer", "role": "Customs Officer"},
        ],
    }


@router.post("/auth/login")
def login(req: LoginRequest) -> dict:
    user = auth.authenticate(req.username, req.password)
    return {"token": auth.make_token(user["id"]), "user": auth.public_user(user)}


@router.post("/auth/sso")
def sso(req: SSORequest) -> dict:
    """Provisioned SSO sign-in (Nafath / Azure AD). Maps a federated identity to
    a role; here it resolves to a demo user for the requested role."""
    user = auth.sso_user(req.role)
    return {"token": auth.make_token(user["id"]), "user": auth.public_user(user)}


@router.get("/auth/me")
def me(user: dict = Depends(auth.current_user)) -> dict:
    return auth.public_user(user)


# --------------------------------------------------------------------------- #
# RBAC / Access Control
# --------------------------------------------------------------------------- #
class PermUpdate(BaseModel):
    permissions: list[str]


@router.get("/rbac")
def get_rbac(_: dict = Depends(auth.require_permission("access_control.view"))) -> dict:
    return rbac.config()


@router.put("/rbac/roles/{role_id}/permissions")
def update_role_permissions(
    role_id: str,
    body: PermUpdate,
    _: dict = Depends(auth.require_permission("access_control.manage")),
) -> dict:
    return rbac.set_role_permissions(role_id, body.permissions)


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
@router.get("/users")
def list_users(_: dict = Depends(auth.require_permission("users.view"))) -> list[dict]:
    return [auth.public_user(u) for u in auth._users()]


# --------------------------------------------------------------------------- #
# Analytics
# --------------------------------------------------------------------------- #
@router.get("/analytics/overview")
def analytics_overview(user: dict = Depends(auth.require_permission("dashboard.view"))) -> dict:
    return analytics.dashboard(user["id"])


@router.post("/analytics/analyze")
def analytics_analyze(user: dict = Depends(auth.require_permission("dashboard.analyze"))) -> dict:
    return {"insights": analytics.insights(user["id"])}


@router.get("/analytics/geo")
def analytics_geo(user: dict = Depends(auth.require_permission("analytics.view"))) -> dict:
    return analytics.geo(user["id"])


@router.post("/analytics/geo/analyze")
def analytics_geo_analyze(user: dict = Depends(auth.require_permission("analytics.analyze"))) -> dict:
    return {"insights": analytics.geo_insights(user["id"])}


# --------------------------------------------------------------------------- #
# Past scans (per user)
# --------------------------------------------------------------------------- #
class FolderMove(BaseModel):
    folder_id: str | None = None


@router.get("/scans")
def list_scans(
    folder_id: str | None = None,
    all: bool = False,
    user: dict = Depends(auth.require_permission("documents.view")),
) -> list[dict]:
    fid = "__any__" if all else folder_id
    return store.list_for_owner(user["id"], fid)


@router.delete("/scans/{doc_id}")
def delete_scan(doc_id: str, user: dict = Depends(auth.require_permission("documents.view"))) -> dict:
    if not store.delete(doc_id, user["id"]):
        raise HTTPException(status_code=404, detail="scan not found")
    return {"ok": True}


@router.put("/scans/{doc_id}/folder")
def move_scan(doc_id: str, body: FolderMove, user: dict = Depends(auth.require_permission("documents.view"))) -> dict:
    if not store.set_folder(doc_id, user["id"], body.folder_id):
        raise HTTPException(status_code=404, detail="scan not found")
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Folders (per user, Windows-like)
# --------------------------------------------------------------------------- #
class FolderCreate(BaseModel):
    name: str
    parent_id: str | None = None


class FolderRename(BaseModel):
    name: str


@router.get("/folders")
def list_folders(user: dict = Depends(auth.require_permission("documents.view"))) -> list[dict]:
    return store.list_folders(user["id"])


@router.post("/folders")
def create_folder(body: FolderCreate, user: dict = Depends(auth.require_permission("documents.view"))) -> dict:
    return store.create_folder(user["id"], body.name, body.parent_id)


@router.put("/folders/{folder_id}")
def rename_folder(folder_id: str, body: FolderRename, user: dict = Depends(auth.require_permission("documents.view"))) -> dict:
    if not store.rename_folder(user["id"], folder_id, body.name):
        raise HTTPException(status_code=404, detail="folder not found")
    return {"ok": True}


@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: str, user: dict = Depends(auth.require_permission("documents.view"))) -> dict:
    if not store.delete_folder(user["id"], folder_id):
        raise HTTPException(status_code=404, detail="folder not found")
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Business rules
# --------------------------------------------------------------------------- #
@router.get("/business-rules")
def get_business_rules(_: dict = Depends(auth.require_permission("business_rules.view"))) -> dict:
    return business_rules.config()


@router.put("/business-rules")
def update_business_rules(body: dict, _: dict = Depends(auth.require_permission("business_rules.manage"))) -> dict:
    return business_rules.update_config(body)


# --------------------------------------------------------------------------- #
# Subscription / API / connectors
# --------------------------------------------------------------------------- #
class KeyCreate(BaseModel):
    label: str


class ConnectorUpdate(BaseModel):
    status: str


class WebhookUpdate(BaseModel):
    url: str


class ExportRequest(BaseModel):
    target: str


@router.get("/subscription")
def get_subscription(_: dict = Depends(auth.require_permission("subscription.view"))) -> dict:
    return subscription.public()


@router.post("/subscription/keys")
def create_key(body: KeyCreate, _: dict = Depends(auth.require_permission("subscription.manage"))) -> dict:
    return subscription.generate_key(body.label)


@router.delete("/subscription/keys/{key_id}")
def revoke_key(key_id: str, _: dict = Depends(auth.require_permission("subscription.manage"))) -> dict:
    return subscription.revoke_key(key_id)


@router.put("/subscription/connectors/{connector_id}")
def update_connector(connector_id: str, body: ConnectorUpdate, _: dict = Depends(auth.require_permission("subscription.manage"))) -> dict:
    return subscription.set_connector(connector_id, body.status)


@router.put("/subscription/webhook")
def update_webhook(body: WebhookUpdate, _: dict = Depends(auth.require_permission("subscription.manage"))) -> dict:
    return subscription.set_webhook(body.url)


@router.get("/subscription/targets")
def export_targets(_: dict = Depends(auth.require_permission("documents.view"))) -> dict:
    """Connected targets a user can push an approved document to."""
    cfg = subscription.public()
    targets = [
        {"id": c["id"], "name": c["name"], "type": c["type"]}
        for c in cfg["connectors"] if c["status"] == "connected"
    ]
    if cfg.get("webhook_url"):
        targets.append({"id": "webhook", "name": "Webhook", "type": "webhook"})
    return {"targets": targets}


@router.post("/scans/{doc_id}/export")
def export_scan(doc_id: str, body: ExportRequest, user: dict = Depends(auth.require_permission("documents.view"))) -> dict:
    if not store.owns(doc_id, user["id"]):
        raise HTTPException(status_code=404, detail="scan not found")
    return subscription.export_document(doc_id, body.target)


# --------------------------------------------------------------------------- #
# User guide (role-aware)
# --------------------------------------------------------------------------- #
class GuideUpdate(BaseModel):
    title: str | None = None
    body: str | None = None


@router.get("/guide")
def get_guide(user: dict = Depends(auth.current_user)) -> dict:
    perms = set(auth.public_user(user)["permissions"])
    return {"sections": user_guide.sections_for(perms), "can_edit": "user_guide.manage" in perms}


@router.put("/guide/{section_id}")
def update_guide(section_id: str, body: GuideUpdate, _: dict = Depends(auth.require_permission("user_guide.manage"))) -> dict:
    return user_guide.update_section(section_id, body.title, body.body)
