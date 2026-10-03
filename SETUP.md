# intel2doc — Local Setup Guide

A simple, step-by-step guide to run the intel2doc application on your laptop.
No prior experience needed — just follow along.

- **Frontend (the web UI):** http://localhost:3003
- **Backend (the API):** http://localhost:8020  (docs at http://localhost:8020/docs)

There are **two ways** to run it:

- **Option A — Docker** (easiest, one command).
- **Option B — Manual** (run backend + frontend yourself). Best for development.

The app works **fully offline** using a built-in mock extractor (no AI needed).
To use **real AI extraction**, follow the **Ollama** section — the chosen model is
`qwen2.5vl:3b`.

---

## What you're running

- **Backend** — the API + the 6-step document pipeline (Python / FastAPI).
- **Frontend** — the review screen in your browser (React / Vite).
- **assets/** — sample document images (JPEG) you can process with one click. Drop
  your own JPEG/PNG scans in here and they appear in the UI automatically.

---

## Before you start (install these once)

| Tool | Needed for | Check it's installed | Download |
|---|---|---|---|
| **Docker Desktop** | Option A | `docker --version` | https://www.docker.com/products/docker-desktop |
| **Python 3.12+** | Option B (backend) | `python --version` | https://www.python.org/downloads/ |
| **Node.js 20+** | Option B (frontend) | `node --version` | https://nodejs.org/ |
| **Ollama** | Real AI (optional) | `ollama --version` | https://ollama.com/download |

> Tip: after installing, close and reopen your terminal so the commands are found.

---

## Option A — Run with Docker (easiest)

1. Open a terminal in the project folder (the one with `docker-compose.yml`).

2. Create your config file from the example:

   **Windows (PowerShell):**
   ```powershell
   copy .env.example .env
   ```
   **macOS / Linux:**
   ```bash
   cp .env.example .env
   ```

3. Start everything:
   ```bash
   docker compose up --build
   ```
   Wait until the logs settle (first run takes a few minutes to download images).

4. Open in your browser:
   - **App (UI):** http://localhost:3003
   - **API docs:** http://localhost:8020/docs

5. In the UI, click a **Demo** button or a **Sample image** to run the pipeline.

**To stop:** press `Ctrl + C` in the terminal, then run `docker compose down`.

> Using Ollama with Docker? See the Ollama section below and set `EXTRACTOR=ollama`
> in `.env`. The compose file already points the backend at your host's Ollama
> (`http://host.docker.internal:11434`).

That's it. If you used Docker, you can skip Option B.

---

## Option B — Run manually (backend + frontend)

You'll use **two terminals**: one for the backend, one for the frontend.

### 1. Start the backend (Terminal 1) — port 8020

Go into the `backend` folder and create a virtual environment:

**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8020
```

**macOS / Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8020
```

✅ Backend is ready when you see: `Application startup complete.`
Check it: open http://localhost:8020/docs

> Leave this terminal running.

### 2. Start the frontend (Terminal 2) — port 3003

Open a **new** terminal in the project folder:

```bash
cd frontend
npm install
npm run dev
```

✅ Frontend is ready when it prints `http://localhost:3003/`.
Open **http://localhost:3003** in your browser.

> Leave this terminal running too.

### 3. Use it

In the browser at http://localhost:3003, click a **Demo** button, click a **Sample
image**, or **Upload** your own document. You'll see each field's confidence, the
business-rule checks, the routing decision (auto-approved vs. needs review), and
every field highlighted on the page.

**To stop:** press `Ctrl + C` in each terminal.

---

## Enable real AI extraction with Ollama (qwen2.5vl:3b)

By default the app uses the offline **mock** extractor (it does **not** read the
image — it returns demo data). To extract the **actual** values from your real
document images, use **Ollama** with the vision model `qwen2.5vl:3b`. Follow every
step below — you only do this once.

### Part A — Download & install Ollama

**Windows**
1. Go to **https://ollama.com/download** and click **Download for Windows**.
2. Run the downloaded `OllamaSetup.exe` and click through the installer.
3. When it finishes, Ollama starts automatically and shows a small icon in the
   system tray (bottom-right). It also runs a local server on port `11434`.
4. **Close and reopen** any PowerShell window so the `ollama` command is found.
5. Verify the install:
   ```powershell
   ollama --version
   ```

**macOS**
1. Download from **https://ollama.com/download** → **Download for macOS**.
2. Open the `.zip`, drag **Ollama** into **Applications**, and launch it once.
3. Verify in Terminal: `ollama --version`

**Linux**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Part B — Download (pull) the vision model

This downloads the model once (~**3–4 GB**, needs a few GB of free disk). In a
terminal run:
```bash
ollama pull qwen2.5vl:3b
```
Wait for it to reach **100% / success**. To confirm it's installed:
```bash
ollama list
```
You should see `qwen2.5vl:3b` in the list.

> Quick optional test (proves the model works on its own):
> ```bash
> ollama run qwen2.5vl:3b "Say hello in one word"
> ```
> Type `/bye` to exit.

### Part C — Make sure the Ollama server is running

- On Windows/macOS the Ollama app keeps the server running (tray/menubar icon).
- If needed, you can start it manually in a terminal with: `ollama serve`
- **Verify:** open **http://localhost:11434** in your browser — it should say
  **"Ollama is running"**.

### Part D — Point intel2doc at Ollama

Open `C:\Users\tunir.bhattacharya\intel2doc-poc\.env` (create it by copying
`.env.example` if it doesn't exist) and set:
```env
EXTRACTOR=ollama
OLLAMA_MODEL=qwen2.5vl:3b
OLLAMA_HOST=http://localhost:11434
```

### Part E — Restart the backend and confirm

1. In the **backend** terminal press `Ctrl + C`, then start it again:
   ```powershell
   uvicorn app.main:app --reload --port 8020
   ```
2. Open **http://localhost:8020/api/health** — you should see:
   ```json
   "extractor": "ollama",
   "ollama": { "reachable": true, "model_available": true, "model": "qwen2.5vl:3b" }
   ```
   The top-right pill in the UI will also read **"AI · qwen2.5vl:3b"**.
3. In the UI (**http://localhost:3003**) click a **Sample image** or **Upload** your
   own JPEG/PNG — the values now come from the model reading your document.

### Handy Ollama commands

```bash
ollama list                 # show installed models
ollama pull qwen2.5vl:3b    # (re)download the model
ollama rm qwen2.5vl:3b      # remove it to free disk space
ollama ps                   # show models currently loaded in memory
```

> Notes
> - The **first** AI request is slow while the model loads into memory; it's faster after.
> - A GPU makes it much faster, but it also works on CPU (just slower).
> - If Ollama is unreachable the backend won't crash — it falls back to the offline text path.
> - Business-rule checks (three-way match, duty rate, GSTIN, balance, air-waybill weight)
>   run the same way regardless of which extractor produced the values.
> - Your documents stay on your machine — nothing is uploaded to any cloud.

---

## What documents the app understands

Out of the box it classifies and extracts these types (drop a matching JPEG/PNG in
`assets/` and it just works):

- **Commercial Invoice**, **Certificate of Origin**, **House Air Waybill**,
  **Customs Declaration** (Customs workflow)
- **Purchase Order**, **Goods Receipt Note**, **Vendor Invoice** (Po2Pay)
- **GST Certificate** (Contracts)
- **Bank Statement** (Finance)

To teach it a new type, add a schema in `backend/app/schemas/<type>.json`, a rule in
`backend/app/rules/rulesets.py`, and a classifier keyword — no model retraining needed.

---

## Using your own document images

- Put any **JPEG/PNG** files into the `assets/` folder.
- They appear automatically as **Sample images** buttons and cards in the UI
  (refresh the page).
- Give them clear names (e.g. `acme_invoice.jpg`, `shipment_waybill.jpg`) — with AI
  the model reads the image, and with the offline mock the filename helps routing.
- Or use the **Upload document** button for a one-off file.
- To regenerate the built-in synthetic samples:
  `python backend/scripts/generate_sample_assets.py`.

---

## Try the API directly (optional)

With the backend running, you can call it from a terminal:

```bash
# Status, workflows, sample assets, and (if enabled) Ollama status
curl http://localhost:8020/api/health

# List sample images and process one
curl http://localhost:8020/api/assets
curl -X POST http://localhost:8020/api/assets/commercial_invoice.jpg

# Run a workflow demo: customs | po2pay | contracts | finance
curl -X POST http://localhost:8020/api/demo/po2pay
```

Or just use the interactive docs at http://localhost:8020/docs (click "Try it out").

---

## Run the tests (optional)

From the `backend` folder, with the virtual environment activated:
```bash
pytest -q
```
You should see all tests pass. (The AI tests run offline — they don't need Ollama.)

---

## Common problems & fixes

| Problem | Fix |
|---|---|
| `python` / `node` / `docker` / `ollama` "not recognized" | Install it (see the table above), then reopen your terminal. |
| PowerShell blocks `Activate.ps1` | Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry. |
| **Port already in use** (8020 or 3003) | Stop the other program, or change the port (e.g. `--port 8021`, and set `VITE_API_BASE`). |
| UI loads but buttons fail | Make sure the **backend** is running at http://localhost:8020. |
| Sample images don't appear | Confirm files exist in `assets/` and the backend is running; refresh the page. |
| Ollama: `model_available: false` | Run `ollama pull qwen2.5vl:3b`. |
| Ollama: `reachable: false` | Start Ollama (open the app or run `ollama serve`). |
| AI extraction is slow the first time | Normal — the model is loading into memory. Faster afterwards. |
| `pip install` errors | Confirm Python 3.12+ (`python --version`) and that the venv is activated. |
| Docker: "Cannot connect to the Docker daemon" | Start **Docker Desktop** and wait for it to say "running". |

---

## What's next

- Config options (auth, thresholds, AI) are in `.env` — see `.env.example` for comments.
- The plan to turn this into a live product is in [docs/PRODUCTIZATION.md](docs/PRODUCTIZATION.md).
- More detail on the architecture is in the [README](README.md).
