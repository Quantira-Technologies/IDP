# intel2doc — POC (Customs / Commercial Invoice + Certificate of Origin)

A runnable proof-of-concept for the **intel2doc** Intelligent Document Processing (IDP)
platform. It demonstrates the full **6-step pipeline** on real trade documents:

> **Classify → Segment → Select → Extract → Validate → Route**

and proves the three headline claims:

- **100% source traceability** — every extracted field carries a page + bounding box.
- **Confidence-based routing** — confident docs auto-approve; unsure ones go to a human review queue.
- **Business-rule validation** — not just "was the number read correctly" but "is it *factually right*"
  (e.g. the applied tax/duty rate matches the product's HS code, line totals sum to the grand total,
  amount-in-words matches the numeric total, and the Certificate of Origin cross-checks the invoice).

> This POC runs **with zero external API keys** using a deterministic *mock extractor* so you can
> demo the whole pipeline offline. A pluggable LLM extractor path is included for the real thing.

---

## Architecture

```
Upload (PDF/bundle)
   │
   ▼
[1 Classify] ─ what document is this?           app/pipeline/classify.py
[2 Segment ] ─ split bundle into sub-documents  app/pipeline/segment.py
[3 Select  ] ─ pick the best extraction engine  app/pipeline/select.py
[4 Extract ] ─ fields + confidence + bbox       app/extractors/*
[5 Validate] ─ business rules engine            app/rules/*
[6 Route   ] ─ auto-approve vs human review     app/pipeline/route.py
   │
   ▼
Structured JSON  +  Review queue (with field highlighted on the page)
```

One engine, many configurations: each **workflow** is just a different set of
**schemas** (`app/schemas/*.json`) and **rulesets** (`app/rules/rulesets.py`). All four
workflows from the product brief are implemented in this POC:

| Workflow | Documents | Headline factual check |
|---|---|---|
| **Customs** | Commercial Invoice, Certificate of Origin | HS-code ↔ duty-rate consistency; CoO ↔ invoice cross-check |
| **Po2Pay** | Purchase Order, Goods Receipt Note, Vendor Invoice | Three-way match / over-billing |
| **Contracts** | GST Certificate | GSTIN check-digit validation |
| **Finance** | Bank Statement | Running-balance reconciliation |

---

## Quick start (backend, no Docker required)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8020
```

Open the interactive API docs at http://localhost:8020/docs

### Try it

```powershell
# Process a single sample document (uses the mock extractor)
curl -X POST http://localhost:8020/api/documents/process -F "file=@..\assets\commercial_invoice.jpg"

# List and process a bundled sample image (from the assets/ folder)
curl http://localhost:8020/api/assets
curl -X POST http://localhost:8020/api/assets/commercial_invoice.jpg

# Run a specific workflow demo (no file needed): customs | po2pay | contracts | finance
curl -X POST http://localhost:8020/api/demo/po2pay

# List the available workflow demos
curl http://localhost:8020/api/workflows
```

### Run tests

```powershell
cd backend
pytest -q
```

---

## Quick start (frontend review UI)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3003 — click a **Demo** workflow, click a **Sample image**, or
**upload** a document, then inspect per-field confidence, see each field highlighted on
the page, correct values, and approve.

---

## Run everything with Docker

```powershell
copy .env.example .env
docker compose up --build
```

- API: http://localhost:8020/docs
- UI:  http://localhost:3003

---

## Real AI extraction with Ollama (qwen2.5vl:3b)

The default `EXTRACTOR=mock` runs fully offline. For real vision extraction from
images, use a local [Ollama](https://ollama.com) server:

```powershell
ollama pull qwen2.5vl:3b     # one-time (~3-4 GB)
# then set in .env:
#   EXTRACTOR=ollama
#   OLLAMA_MODEL=qwen2.5vl:3b
#   OLLAMA_HOST=http://localhost:11434
```

Restart the backend and process a **Sample image** or an upload. Check the connection
at http://localhost:8020/api/health (shows an `ollama` block when enabled). The
extractor interface (`app/extractors/base.py`) returns fields **with confidence and
optional bounding boxes**, so classify → validate → route are unchanged. If Ollama is
unreachable the backend degrades gracefully instead of crashing.

Sample document images live in **`assets/`** — drop your own JPEG/PNG scans there and
they appear automatically in the UI. Regenerate the built-in samples with
`python backend/scripts/generate_sample_assets.py`.

For a hosted/enterprise OCR path (Azure Document Intelligence / AWS Textract / Google
Document AI, or self-hosted PaddleOCR + LayoutLM) see
[docs/PRODUCTIZATION.md](docs/PRODUCTIZATION.md).

---

## What this POC intentionally does NOT do

Multi-tenancy, SSO/RBAC, model fine-tuning, HA, and audit-grade compliance are out of
scope here — they belong to the productization phase. An **optional API-key auth**
(`API_KEY` in `.env`) and configurable CORS (`CORS_ORIGINS`) are included as a first
hardening step. See [docs/PRODUCTIZATION.md](docs/PRODUCTIZATION.md) for the full
production requirements, target architecture, tech stack, and roadmap.
