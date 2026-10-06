"""intel2doc POC API.

Endpoints:
  POST /api/documents/process   upload a file (image/PDF) -> run the 6-step pipeline
  POST /api/demo/bundle         run the built-in invoice+CoO demo bundle
  POST /api/demo/{workflow}     run a workflow demo (customs|po2pay|contracts|finance)
  GET  /api/assets              list the sample document images in assets/
  GET  /api/assets/{name}/image serve a sample image (for the UI overlay)
  POST /api/assets/{name}       run the pipeline on a sample image
  GET  /api/documents/{id}      fetch a processed result
  GET  /api/documents           list processed result ids
  POST /api/documents/{id}/correct   apply a reviewer correction + re-route
  GET  /api/health
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import assets as assets_mod
from . import routers
from .auth import current_user, require_permission
from .config import settings
from .db import store
from .extractors import ollama_client
from .extractors.ocr_extractor import available as ocr_available
from .models import CorrectionRequest, DocumentResult
from .pipeline.orchestrator import process_document
from .pipeline.route import route
from .pipeline.validate import validate
from .samples import DEMO_BUNDLES, demo_bundle, raw_from_upload


def _stamp(result: DocumentResult, user: dict) -> DocumentResult:
    from datetime import datetime, timezone

    result.owner = user["id"]
    result.created_at = datetime.now(timezone.utc).isoformat()
    return result

app = FastAPI(title="intel2doc", version="1.0.0")

# CORS: "*" by default for the local Vite dev server; override via CORS_ORIGINS.
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers.router)


@app.get("/api/health")
def health() -> dict:
    body = {
        "status": "ok",
        "extractor": settings.extractor,
        "threshold": settings.confidence_threshold,
        "auth_enabled": settings.auth_enabled,
        "sso_enabled": settings.sso_enabled,
        "ocr_available": ocr_available(),
        "workflows": list(DEMO_BUNDLES.keys()),
        "assets": assets_mod.list_assets(),
    }
    # Only probe Ollama when it's the selected engine (keeps mock demos fast).
    if settings.extractor in ("ollama", "ollama_text"):
        body["ollama"] = ollama_client.status()
    return body


@app.post("/api/documents/process", response_model=DocumentResult, dependencies=[Depends(require_permission("documents.upload"))])
async def process_upload(file: UploadFile = File(...), user: dict = Depends(current_user)) -> DocumentResult:
    content = await file.read()
    raw = raw_from_upload(file.filename or "upload", content, file.content_type)
    result = _stamp(process_document(raw), user)
    store.save(result)
    return result


@app.get("/api/assets", response_model=list[str], dependencies=[Depends(require_permission("documents.view"))])
def list_assets() -> list[str]:
    """Sample document images available in the assets/ folder."""
    return assets_mod.list_assets()


@app.get("/api/assets/{name}/image")
def get_asset_image(name: str) -> Response:
    # No auth dependency: served directly to <img> tags in the browser.
    try:
        data, content_type = assets_mod.read_asset(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="asset not found")
    return Response(content=data, media_type=content_type)


@app.post("/api/assets/{name}", response_model=DocumentResult, dependencies=[Depends(require_permission("documents.view"))])
def process_asset(name: str, user: dict = Depends(current_user)) -> DocumentResult:
    try:
        raw = assets_mod.raw_from_asset(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="asset not found")
    result = _stamp(process_document(raw), user)
    result.image_url = f"/api/assets/{name}/image"
    store.save(result)
    return result


@app.post("/api/demo/bundle", response_model=DocumentResult, dependencies=[Depends(require_permission("documents.view"))])
def process_demo_bundle(user: dict = Depends(current_user)) -> DocumentResult:
    result = _stamp(process_document(demo_bundle()), user)
    store.save(result)
    return result


@app.get("/api/workflows", response_model=list[str], dependencies=[Depends(require_permission("documents.view"))])
def list_workflows() -> list[str]:
    """The demo bundles available, one per workflow area."""
    return list(DEMO_BUNDLES.keys())


@app.post("/api/demo/{workflow}", response_model=DocumentResult, dependencies=[Depends(require_permission("documents.view"))])
def process_workflow_demo(workflow: str, user: dict = Depends(current_user)) -> DocumentResult:
    factory = DEMO_BUNDLES.get(workflow)
    if not factory:
        raise HTTPException(
            status_code=404,
            detail=f"unknown workflow '{workflow}'. Known: {list(DEMO_BUNDLES)}",
        )
    result = _stamp(process_document(factory()), user)
    store.save(result)
    return result


@app.get("/api/documents", response_model=list[dict], dependencies=[Depends(require_permission("documents.view"))])
def list_documents(user: dict = Depends(current_user)) -> list[dict]:
    return store.list_for_owner(user["id"])


@app.get("/api/documents/{doc_id}", response_model=DocumentResult, dependencies=[Depends(require_permission("documents.view"))])
def get_document(doc_id: str, user: dict = Depends(current_user)) -> DocumentResult:
    result = store.get(doc_id)
    if not result or (result.owner and result.owner != user["id"]):
        raise HTTPException(status_code=404, detail="document not found")
    return result


@app.post("/api/documents/{doc_id}/correct", response_model=DocumentResult, dependencies=[Depends(require_permission("review.correct"))])
def correct_document(doc_id: str, req: CorrectionRequest, user: dict = Depends(current_user)) -> DocumentResult:
    result = store.get(doc_id)
    if not result or (result.owner and result.owner != user["id"]):
        raise HTTPException(status_code=404, detail="document not found")
    if req.sub_index < 0 or req.sub_index >= len(result.sub_documents):
        raise HTTPException(status_code=400, detail="invalid sub_index")

    sub = result.sub_documents[req.sub_index]
    field = sub.extraction.fields.get(req.field_name)
    if not field:
        raise HTTPException(status_code=400, detail=f"unknown field '{req.field_name}'")

    # Apply the human correction: value set, confidence promoted to 1.0.
    field.value = req.new_value
    field.confidence = 1.0
    field.corrected = True

    # Re-validate and re-route with the corrected value.
    siblings = [s.extraction for s in result.sub_documents]
    sub.rule_results = validate(sub.extraction, siblings)
    decision, reasons, min_conf = route(sub.extraction, sub.rule_results)
    if req.approve:
        # Reviewer explicitly approves regardless of residual warnings.
        from .models import RouteDecision

        decision = RouteDecision.AUTO_APPROVED
        reasons = ["approved by reviewer"] if not reasons else ["approved by reviewer"] + reasons
        result.approved = True
    sub.route = decision
    sub.route_reasons = reasons
    sub.min_confidence = min_conf

    store.save(result)
    return result
